#!/usr/bin/env python3
"""Build data/flags.json - the irregularities published on the Flagged for review page.

Derived flags are computed from the current dataset; curated flags live in
data/flags_manual.json so that a human statement is never overwritten by a rebuild.
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DATA, iso, load_json, log, now_utc, save_json

HOTSPAWN = "https://play.hotspawn.com/lol-pickems"
LEAGUEPEDIA = "https://lol.fandom.com/wiki/Special:CargoExport"
PINNACLE = "https://guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups"


def _host(url) -> str:
    """Readable source name for a receipt URL; never invents one when it is missing."""
    if not url:
        return "an unnamed source"
    name = str(url).split("//")[-1].split("/")[0]
    return name[4:] if name.startswith("www.") else name


def main() -> None:
    data = load_json(os.path.join(DATA, "matches.json")) or {}
    rows = data.get("matches") or []
    matching = load_json(os.path.join(DATA, "matching_report.json")) or {}
    sources = (load_json(os.path.join(DATA, "sources_status.json")) or {}).get("sources") or []
    manual = (load_json(os.path.join(DATA, "flags_manual.json")) or {}).get("flags") or []

    # Curated items that state how they were checked keep their own wording; anything that
    # cannot point at a verification is explicitly relabelled rather than silently trusted.
    #
    # A curated note usually quotes the fixture id it is about, and Hotspawn drops a card
    # from the list once it kicks off. That is time passing, not a defect, so the reference
    # is annotated here as a historical observation instead of stalling the build (the
    # publish gate asserts that this annotation happened - see tools/verify.py).
    listed_ids = {str(r.get("id")) for r in rows}
    flags: list[dict] = []
    for f in manual:
        refs = sorted(set(re.findall(r"#(\d{6,8})", f"{f.get('item', '')} {f.get('detail', '')}")))
        delisted = [i for i in refs if i not in listed_ids]
        entry = {**f}
        if delisted:
            declared = [str(x) for x in (f.get("delisted_refs") or [])]
            entry["delisted_refs"] = sorted(set(declared) | set(delisted))
            entry["delisted_refs_auto"] = sorted(set(delisted) - set(declared))
            entry["detail"] = (f.get("detail", "") +
                               " Fixture " + ", ".join(f"#{i}" for i in entry["delisted_refs_auto"]) +
                               " has since left the Hotspawn list (the card kicked off or was removed); the "
                               "statement is kept as a historical observation about that card.")
        if f.get("verification"):
            entry["item"] = f["item"] + " [" + f["verification"] + "]"
        else:
            entry["item"] = "Not reverified: " + f["item"]
            entry["detail"] = ("Prior statement, not checked against a live official source in this "
                               "build. " + entry["detail"])
        flags.append(entry)
    flags.append({
        "severity": "info",
        "item": "Leaguepedia is community-maintained, not an official league source",
        "detail": ("Every originated line is fitted on Leaguepedia's community-recorded series history and its "
                   "Data: page dqteams directives are used to quarantine removed teams. Leaguepedia is not an "
                   "official settlement authority; Kalshi's own rules, for example, resolve a pre-play forfeit at "
                   "the fair market price. Forfeit settlement picks on this site are therefore marked conditional."),
        "source": "https://lol.fandom.com/wiki/Leaguepedia:Community",
        "verification": "source role stated, not a value claim",
    })
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

    def _has_zero_rated(side: dict | None) -> bool:
        return isinstance(side, dict) and "rating_matches" in side and side.get("rating_matches") == 0

    zero_both = [r for r in rows if r.get("method") != "market" and r.get("method") != "unresolved"
                 and _has_zero_rated(r.get("team0")) and _has_zero_rated(r.get("team1"))]
    zero_one = [r for r in rows if r.get("method") != "market" and r.get("method") != "unresolved"
                and (_has_zero_rated(r.get("team0")) ^ _has_zero_rated(r.get("team1")))]
    if zero_both:
        examples = "; ".join(
            f"#{r['id']} {r['team0']['name']} vs {r['team1']['name']} ({r['competition']})"
            for r in zero_both[:6]
        )
        flags.append({
            "severity": "high",
            "item": f"{len(zero_both)} fixture(s) have 0 pre-kickoff rated series on BOTH sides (equal debut prior only)",
            "detail": ("Neither team had a completed Leaguepedia series before kick-off and no external bookmaker "
                       "price exists, so the published 50.0% / 50.0% split reflects identical division priors rather "
                       "than match evidence: " + examples + "."),
            "source": zero_both[0].get("hotspawn_url") or HOTSPAWN,
            "verification": "derived from pre-kickoff rating_matches == 0 on both sides",
        })
    if zero_one:
        examples = "; ".join(
            f"#{r['id']} {r['team0']['name']} ({r['team0'].get('rating_matches')}) vs "
            f"{r['team1']['name']} ({r['team1'].get('rating_matches')}) ({r['competition']})"
            for r in zero_one[:6]
        )
        flags.append({
            "severity": "medium",
            "item": f"{len(zero_one)} provisional fixture(s) include a debut side with 0 pre-kickoff rated series",
            "detail": ("One team enters with zero completed Leaguepedia series before kick-off and is anchored strictly "
                       "to its division prior while the opponent carries rated history: " + examples + "."),
            "source": zero_one[0].get("hotspawn_url") or LEAGUEPEDIA,
            "verification": "derived from pre-kickoff rating_matches == 0 on one side",
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
                      "published start time has already passed (earliest "
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
                      "Kalshi, Smarkets, Bovada, Unibet) or to our own Elo line. The receipts stay in the audit trail: "
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
                      + "; ".join(f"#{q.get('fixture_id')} {q.get('venue') or 'archived aggregator receipt'}: {q.get('reject')}" for q in rejected[:6]),
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
            "source": PINNACLE,
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
    market_comps = sorted({r["competition"] for r in rows if r["method"] == "market"})
    flags.append({
        "severity": "info",
        "item": f"Bookmaker coverage is {priced}/{len(rows)} matches",
        "detail": ("Priced competitions in this snapshot: " + (", ".join(market_comps) or "none") +
                   ". Every other national and academy league has no published market on any book reachable "
                   "from the runner, which is why those lines are originated from recorded series history "
                   "instead of guessed."),
        "source": PINNACLE,
    })

    retired = load_json(os.path.join(DATA, "retired_quotes.json")) or {}
    if retired.get("retired_count"):
        flags.append({
            "severity": "medium",
            "item": f"{retired['retired_count']} archived esportsbook quotes were retired as unverifiable",
            "detail": retired.get("reason", ""),
            "source": ("https://github.com/karagemop466-tech/LOLHOTSPAWN1/blob/"
                       "main/data/retired_quotes.json"),
        })

    # Per-fixture note: this match is now originated because its only external capture was retired.
    retired_by_fixture = {str(q.get("fixture_id")): q
                          for q in (retired.get("quotes") or [])}
    for m in rows:
        q = retired_by_fixture.get(str(m.get("id")))
        if not q or m.get("method") == "market":
            continue
        src = q.get("source_url") or ""
        note = (f"The only external capture for this fixture ({q.get('book_label') or 'aggregator'}, "
                f"{'/'.join(str(x) for x in (q.get('decimal') or []) or [])} on "
                f"{str(q.get('observed_at') or '')[:10]}) could not be re-verified and is retired; the published "
                f"line is originated from recorded results. Live page today shows symmetric 1.80 / 1.80 placeholder "
                f"prices, which are rejected by policy.")
        flags.append({
            "severity": "high",
            "item": f"Retired external quote on {m.get('team0', {}).get('name')} vs {m.get('team1', {}).get('name')}",
            "detail": note,
            "source": src or "data/retired_quotes.json",
        })

    hy = data.get("market_hygiene") or {}
    if hy.get("pinnacle_kills_derivatives_excluded"):
        flags.append({
            "severity": "info",
            "item": (f"{hy['pinnacle_kills_derivatives_excluded']} Pinnacle '(Kills)' derivative markets "
                     "excluded from the series consensus"),
            "detail": "Pinnacle lists a parallel kills market for each LoL series. Only series moneylines are "
                      "allowed to set a match-win probability; the derivative rows are filtered in collect.py "
                      "and again in model.py.",
            "source": "https://guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups",
        })

    walkover = [r for r in rows if r.get("resolution")]
    if walkover:
        flags.append({
            "severity": "info",
            "item": f"{len(walkover)} fixtures resolved only by official forfeit, not by a playing line",
            "detail": "; ".join(
                f"#{r['id']} {r['team0']['name']} vs {r['team1']['name']} -> {r['resolution']['winner']} "
                f"(official forfeit; {r['resolution']['source']})" for r in walkover),
            "source": walkover[0]["resolution"]["source"],
        })

    fetched = str(data.get("inventory_fetched_utc") or "")
    try:
        age_h = (now_utc() - datetime.strptime(fetched[:19], "%Y-%m-%dT%H:%M:%S").replace(
            tzinfo=timezone.utc)).total_seconds() / 3600
    except ValueError:
        age_h = None
    if age_h is not None and age_h > 8:
        flags.append({
            "severity": "high",
            "item": f"Hotspawn inventory snapshot is {age_h:.0f}h old (refresh window is 4–8h)",
            "detail": (f"Collected {fetched}. Scheduled refresh-picks runs after this timestamp did not "
                       "publish a new snapshot. Treat kick-off times and market lines as unverified until "
                       "the next successful collect. Live lobby: " + HOTSPAWN),
            "source": HOTSPAWN,
        })

    corr = load_json(os.path.join(DATA, "corroboration.json")) or {}
    unmatched = [r for r in (corr.get("rejected") or []) if r.get("status") == "unmatched"]
    if unmatched:
        flags.append({
            "severity": "low",
            "item": f"{len(unmatched)} corroboration receipt(s) refer to fixtures no longer on Hotspawn",
            "detail": ("Expected when Worlds BO1s roll off the scheduled feed. Receipts stay as audit "
                       "evidence and are never used as prices. "
                       + "; ".join(f"#{r.get('fixture_id')} {r.get('source')}" for r in unmatched[:8])),
            "source": "https://github.com/karagemop466-tech/LOLHOTSPAWN1/blob/main/data/corroboration.json",
        })
    diverged = [r for r in (corr.get("rows") or []) if r.get("verdict") == "diverges"]
    if diverged:
        flags.append({
            "severity": "medium",
            "item": f"{len(diverged)} external corroboration receipt(s) diverge from the published line",
            "detail": ("Corroboration only — the published pick is unchanged. "
                       + "; ".join(f"#{r.get('fixture_id')} {r.get('source_name')} {r.get('delta_pp')}pp"
                                   for r in diverged[:8])),
            "source": "https://github.com/karagemop466-tech/LOLHOTSPAWN1/blob/main/data/corroboration.json",
        })

    save_json(os.path.join(DATA, "flags.json"), {
        "generated_utc": iso(now_utc()),
        "count": len(flags),
        "flags": flags,
    })
    log(f"flags: {len(flags)} items")


if __name__ == "__main__":
    main()
