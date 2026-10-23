#!/usr/bin/env python3
"""Build data/flags.json - the irregularities published on the Flagged for review page.

Derived flags are computed from the current dataset; curated flags live in
data/flags_manual.json so that a human statement is never overwritten by a rebuild.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DATA, iso, load_json, log, now_utc, save_json

HOTSPAWN = "https://play.hotspawn.com/lol-pickems"
LEAGUEPEDIA = "https://lol.fandom.com/wiki/Special:CargoExport"
PINNACLE = "https://www.pinnacle.com/en/esports/league-of-legends"


def main() -> None:
    data = load_json(os.path.join(DATA, "matches.json")) or {}
    rows = data.get("matches") or []
    matching = load_json(os.path.join(DATA, "matching_report.json")) or {}
    sources = (load_json(os.path.join(DATA, "sources_status.json")) or {}).get("sources") or []
    manual = (load_json(os.path.join(DATA, "flags_manual.json")) or {}).get("flags") or []

    def decorate(f: dict) -> dict:
        """Carry each curated flag's verification state to the page, honestly.

        A flag that was re-checked against a live source on this run says so; one that
        was not keeps an explicit "not reverified" banner instead of looking audited.
        """
        if f.get("verified_utc"):
            return {**f, "detail": f["detail"],
                    "verification": f"re-verified {f['verified_utc']} against "
                                    f"{f.get('verified_against') or 'the cited source'}"}
        return {**f, "item": "Historical observation — not reverified: " + f["item"],
                "detail": "Prior-session statement; not verified against a live source in this audit. "
                          + f["detail"]}

    flags: list[dict] = [decorate(f) for f in manual]
    flags.append({"severity": "medium", "item": "Archived aggregator quotes excluded from current pricing",
                  "detail": "The previous pipeline reused fixed receipts observed on 2026-10-21 without refreshing them. These are now excluded. Only freshly collected provider feeds enter market consensus. Leaguepedia history remains community-maintained, not an official league source.",
                  "source": "https://github.com/karagemop466-tech/LOLHOTSPAWN1/blob/main/archive/session-8336fb7e/data/book_receipts.json"})
    counts = Counter(r["method"] for r in rows)

    unresolved = [r for r in rows if r["method"] == "unresolved"]
    if unresolved:
        flags.append({
            "severity": "medium",
            "item": f"{len(unresolved)} match(es) have no win probability (settlement pick only)",
            "detail": "; ".join(f"{r['team0']['name']} vs {r['team1']['name']} ({r['competition']}): {r['basis']}"
                                for r in unresolved[:6]),
            "source": HOTSPAWN,
        })

    recorded = [r for r in rows if r.get("recorded_result")]
    if recorded:
        flags.append({
            "severity": "info",
            "item": f"{len(recorded)} Hotspawn cards already have a final result recorded in Leaguepedia",
            "detail": "Hotspawn keeps returning status='scheduled' for fixtures that have finished. Where the "
                      "same teams met within 36 hours on the same Leaguepedia overview page, the recorded result "
                      "is attached to the card and shown as 'result on record'. These rows stay on the list so "
                      "the inventory matches Hotspawn exactly, but they are not live bets.",
            "source": "https://lol.fandom.com/wiki/Special:CargoExport",
        })

    provisional = counts.get("provisional", 0)
    if provisional:
        flags.append({
            "severity": "low",
            "item": f"{provisional} provisional lines (thin data)",
            "detail": "At least one side has fewer than five rated series in the Leaguepedia window, "
                      "or the two teams share no opponent chain. A probability is still published but is "
                      "labelled provisional and shows the reason on the card.",
            "source": LEAGUEPEDIA,
        })

    non_exact = matching.get("non_exact_team_count", 0)
    if non_exact:
        flags.append({
            "severity": "low",
            "item": f"{non_exact} team names needed a non-exact Leaguepedia match",
            "detail": "Leaguepedia appends a region to duplicate team names (e.g. 'Fenrir (Icelandic Team)'). "
                      "Every non-exact join and its evidence is listed on the Verification page; ambiguous "
                      "names are left unmatched instead of guessed.",
            "source": LEAGUEPEDIA,
        })

    blocked = [s for s in sources if not s.get("ok")]
    if blocked:
        flags.append({
            "severity": "low",
            "item": f"{len(blocked)} betting/odds sources were unreachable from the build runner",
            "detail": "; ".join(f"{s['name']} HTTP {s['status']} ({s.get('blocked_note')})" for s in blocked),
            "source": "https://github.com/karagemop466-tech/LOLHOTSPAWN1/blob/main/data/sources_status.json",
        })

    stale = [r for r in rows if r.get("stale")]
    if stale:
        flags.append({
            "severity": "medium",
            "item": f"{len(stale)} fixtures still listed as 'scheduled' although their start time has passed",
            "detail": "Hotspawn's fixtures API returns status='scheduled' for these cards even though the "
                      "published start time is more than three hours in the past (earliest "
                      f"{min((r['start_utc'] or '') for r in stale)}). They are kept in the list to mirror "
                      "Hotspawn exactly, marked 'start time passed' on the card, and sorted after upcoming "
                      "matches. The reason is unverified.",
            "source": HOTSPAWN,
        })

    audit = data.get("receipt_audit") or {}
    expired = audit.get("expired") or []
    if expired:
        age = max([e.get("age_hours") or 0 for e in expired] or [0])
        flags.append({
            "severity": "medium",
            "item": f"{len(expired)} archived esportsbook receipts expired and are no longer used as market input",
            "detail": "A bookmaker quote captured from a match page is a line only while it is fresh. These "
                      f"receipts were captured on {min((str(e.get('observed_at') or '') for e in expired))[:10]} "
                      f"(up to {age:.0f} h old, limit {audit.get('max_age_hours')} h) and are now excluded from "
                      "the consensus; the affected fixtures fall back to the live venues (Pinnacle, Polymarket, "
                      "Kalshi, Bovada) or to our own Elo line. The receipts stay in the audit trail: "
                      + "; ".join(f"#{e['fixture_id']} {e.get('decimal')} ({e.get('observed_at')})" for e in expired[:6]),
            "source": "https://github.com/karagemop466-tech/LOLHOTSPAWN1/blob/main/archive/session-8336fb7e/data/book_receipts.json",
        })

    rejected = audit.get("rejected_quotes") or []
    if rejected:
        flags.append({
            "severity": "medium",
            "item": f"{len(rejected)} bookmaker quote(s) rejected as non-actionable",
            "detail": "Every quote is de-vigged only after an integrity test: symmetric 1.80/1.80 aggregator "
                      "placeholders, prices <= 1.00 and lines where one side implies more than 97% are dropped "
                      "rather than published. Rejected on this build: "
                      + "; ".join(f"#{q.get('fixture_id')} {q.get('venue')}: {q.get('reject')}" for q in rejected[:6]),
            "source": "https://github.com/karagemop466-tech/LOLHOTSPAWN1/blob/main/tools/model.py",
        })

    divergent = [r for r in rows if any("market and model disagree" in f for f in (r.get("flags") or []))]
    if divergent:
        flags.append({
            "severity": "medium",
            "item": f"{len(divergent)} market-priced match(es) disagree with our own model by 20 pp or more",
            "detail": "; ".join(f"{r['team0']['name']} vs {r['team1']['name']} ({r['competition']})" for r in divergent[:6])
                      + ". The market side is what the site publishes and the model value is printed next to it on "
                        "the Market page, so the gap is visible rather than hidden.",
            "source": "https://www.pinnacle.com/en/esports/league-of-legends",
        })

    thin = [r for r in rows if (r.get("market") or {}).get("thin")]
    if thin:
        flags.append({
            "severity": "medium",
            "item": f"{len(thin)} market row(s) rest on a single prediction market with almost no traded volume",
            "detail": "; ".join(f"{r['team0']['name']} vs {r['team1']['name']} ({r['competition']}): "
                                f"{r['market']['thin_note']}, priced {(r['p0'] or 0)*100:.1f}%/{(r['p1'] or 0)*100:.1f}%"
                                for r in thin[:5])
                      + ". The price is kept because it is the only external evidence for that match, but the row is "
                        "labelled low confidence and must not be read as a deep-market line.",
            "source": ((thin[0].get("market") or {}).get("market_url") or HOTSPAWN),
        })

    settlement = [r for r in rows if r.get("pick_type") == "settlement"]
    if settlement:
        listed = "; ".join("#{} {} vs {}".format(r["id"], r["team0"]["name"], r["team1"]["name"])
                           for r in settlement[:6])
        flags.append({
            "severity": "high",
            "item": f"{len(settlement)} match(es) carry a settlement pick only - no win probability is claimed",
            "detail": "For these cards the listed participant was removed mid-split by the league "
                      f"({listed}). We publish the administratively correct side (the active opponent, per the "
                      "official dqteams ruling) and publish no percentage at all, because a competitive "
                      "probability cannot be justified if the series is voided or awarded as a walkover.",
            "source": "https://lol.fandom.com/wiki/Komplettligaen/2026_Season/Autumn_Split",
        })

    kickoff = [r for r in rows if any("kick-off time differs" in f for f in r.get("flags") or [])]
    if kickoff:
        flags.append({
            "severity": "medium",
            "item": f"{len(kickoff)} bookmaker-priced matches disagree on kick-off time",
            "detail": "Pinnacle's start times differ from Hotspawn's by 2-5 hours on these fixtures. Because "
                      "Hotspawn and Leaguepedia agree with each other (recorded in each card's 'Why this line'), "
                      "the odds are treated as valid for the pairing; the card prints both times. Verify before "
                      "betting: " + "; ".join(f"{r['team0']['name']} vs {r['team1']['name']}" for r in kickoff[:8]),
            "source": PINNACLE,
        })

    # Kick-off cross-check against the official Leaguepedia series record (all rows, not just priced ones).
    lp_kickoff = [r for r in rows if any("kick-off differs from the official Leaguepedia" in f
                                         for f in r.get("flags") or [])]
    if lp_kickoff:
        upcoming = [r for r in lp_kickoff if not r.get("stale")]
        flags.append({
            "severity": "medium",
            "item": f"{len(lp_kickoff)} fixtures list a different kick-off than the official Leaguepedia record",
            "detail": "Hotspawn's published start time and the date/time in Leaguepedia's Data: schedule disagree by "
                      "1.5 hours or more on these cards (most differ by whole days, e.g. a Hotspawn card dated this "
                      f"week against a Leaguepedia record in November). {len(upcoming)} of them are still ahead of "
                      "their Hotspawn kick-off, so the date matters. Each affected card prints both times. Examples: "
                      + "; ".join(f"{r['team0']['name']} vs {r['team1']['name']} ({r['competition']})"
                                  for r in lp_kickoff[:6]),
            "source": "https://lol.fandom.com/wiki/Special:CargoExport",
        })

    crowd = []
    for r in rows:
        c = r.get("community_pick_pct") or {}
        total = c.get("total_picks") or 0
        if total >= 20 and r.get("p0") is not None and c.get("team0") is not None:
            gap = abs((c["team0"] / 100.0) - r["p0"])
            crowd.append((gap, r, c["team0"], total))
    if crowd:
        crowd.sort(key=lambda item: -item[0])
        gap, worst, crowd_pct, total = crowd[0]
        flags.append({
            "severity": "medium",
            "item": (f"Crowd vs real-money gap: {worst['team0']['name']} vs {worst['team1']['name']} "
                     f"({worst['competition']}) - crowd {crowd_pct}% on {worst['team0']['name']} "
                     f"against our {worst['p0']*100:.1f}%"),
            "detail": (f"{total} Hotspawn users have picked this card and {crowd_pct}% of them chose "
                       f"{worst['team0']['name']}; our line, built only from external sources "
                       f"({worst['method']}), puts that team at {worst['p0']*100:.1f}% - a "
                       f"{gap*100:.1f} pp gap. Recalculated on every build across all cards with at least "
                       "20 crowd picks: " + ", ".join(
                           f"{r['team0']['name']} vs {r['team1']['name']} {g*100:.0f} pp"
                           for g, r, _, _ in crowd[:4]) + "."),
            "source": worst["hotspawn_url"],
        })

    priced = counts.get("market", 0)
    flags.append({
        "severity": "info",
        "item": f"Bookmaker coverage is {priced}/{len(rows)} matches",
        "detail": "Pinnacle prices the World Championship and EMEA Masters fixtures from this list. The "
                  "remaining national and academy leagues have no published market on any book reachable from "
                  "the runner, which is why their lines are originated by our own model.",
        "source": PINNACLE,
    })

    save_json(os.path.join(DATA, "flags.json"), {
        "generated_utc": iso(now_utc()),
        "count": len(flags),
        "flags": flags,
    })
    log(f"flags: {len(flags)} items")


if __name__ == "__main__":
    main()
