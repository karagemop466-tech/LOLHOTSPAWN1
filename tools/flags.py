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

    # Curated items that state how they were checked keep their own wording; anything that
    # cannot point at a verification is explicitly relabelled rather than silently trusted.
    flags: list[dict] = []
    for f in manual:
        if f.get("verification"):
            flags.append({**f, "item": f["item"] + " [" + f["verification"] + "]"})
        else:
            flags.append({**f,
                          "item": "Not reverified: " + f["item"],
                          "detail": ("Prior statement, not checked against a live official source in this "
                                     "build. " + f["detail"])})
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
            "item": f"{len(unresolved)} match(es) could not be priced",
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
                       "arena/4dfd0e71-lolhotspawn1/data/retired_quotes.json"),
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

    save_json(os.path.join(DATA, "flags.json"), {
        "generated_utc": iso(now_utc()),
        "count": len(flags),
        "flags": flags,
    })
    log(f"flags: {len(flags)} items")


if __name__ == "__main__":
    main()
