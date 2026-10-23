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

    flags: list[dict] = [{**f, "item": "Historical observation — not reverified: " + f["item"],
                          "detail": "Prior-session statement; not verified against a live official source in this audit. " + f["detail"]}
                         for f in manual]
    flags.append({"severity": "medium", "item": "Archived aggregator quotes excluded from current pricing",
                  "detail": "The previous pipeline reused fixed receipts observed on 2026-10-21 without refreshing them. These are now excluded. Only freshly collected provider feeds enter market consensus. Leaguepedia history remains community-maintained, not an official league source.",
                  "source": "https://github.com/karagemop466-tech/LOLHOTSPAWN1/blob/main/archive/session-8336fb7e/data/book_receipts.json"})
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
