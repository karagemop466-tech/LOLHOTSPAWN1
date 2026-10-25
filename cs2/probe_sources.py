#!/usr/bin/env python3
"""Probe every candidate Counter-Strike 2 source from the runner and record the result.

Nothing here prices a match. The probe answers one question per source: *did this runner get
usable content, and of what kind?* The receipt it writes (`data/cs2/source_probe.json`) is
committed so the site can state availability instead of assuming it.

Run:  python3 cs2/probe_sources.py
"""
from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
from common import DATA, ROOT, http_get, iso, log, now_utc, save_json  # noqa: E402

CS2_DATA = os.path.join(DATA, "cs2")
PROBE_PATH = os.path.join(CS2_DATA, "source_probe.json")

HOTSPAWN_API = "https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures"
PINNACLE = "https://guest.api.arcadia.pinnacle.com/0.1"
KALSHI = "https://api.elections.kalshi.com/trade-api/v2"

# (slug, label, kind, url, headers, why it matters)
CANDIDATES = [
    # ---------------------------------------------------------------- inventory (required)
    ("hotspawn_cs2", "Hotspawn fixtures API — CS2 scheduled", "json",
     HOTSPAWN_API + "?sport_alias=cs2&status=scheduled&tenantId=1", None,
     "The list of matches the client asked us to cover."),
    ("hotspawn_cs2_finished", "Hotspawn fixtures API — CS2, non-scheduled status", "json",
     HOTSPAWN_API + "?sport_alias=cs2&status=completed&tenantId=1", None,
     "Would give us Hotspawn's own result records for grading."),
    ("hotspawn_lobby", "Hotspawn pick'em lobby (CS2 tab)", "html",
     "https://play.hotspawn.com/lobby", None,
     "Human-facing list; used only to cross-check the API inventory."),
    ("hotspawn_cs2_pickem_page", "Hotspawn CS2 pick'em page", "html",
     "https://play.hotspawn.com/cs2-pickems", None,
     "Deep-link target for each card."),
    # ---------------------------------------------------------------- external lines
    ("pinnacle_leagues", "Pinnacle guest API — esports league list", "json",
     PINNACLE + "/sports/12/leagues", {"x-api-key": "CmX2KcMrXuFmNg6YFbmTxE0y9CIrOi0R"},
     "Enumerates which CS2 competitions Pinnacle actually prices."),
    ("pinnacle_matchups", "Pinnacle guest API — esports matchups", "json",
     PINNACLE + "/sports/12/matchups", {"x-api-key": "CmX2KcMrXuFmNg6YFbmTxE0y9CIrOi0R"},
     "Sharp reference moneylines for any CS2 match it lists."),
    ("kalshi_cs2_game", "Kalshi — KXCS2GAME series", "json",
     KALSHI + "/events?series_ticker=KXCS2GAME&status=open&with_nested_markets=true&limit=100",
     None, "CFTC-regulated exchange; would be a second independent market."),
    ("kalshi_cs2_alt", "Kalshi — KXCS2 series (alternate ticker)", "json",
     KALSHI + "/events?series_ticker=KXCS2&status=open&with_nested_markets=true&limit=100",
     None, "Ticker discovery; a 404/empty here is not a failure of the venue."),
    ("kalshi_series_search", "Kalshi — series index", "json",
     KALSHI + "/series?category=Sports&limit=200", None,
     "Discovery endpoint for the CS2 series ticker."),
    ("polymarket_cs2", "Polymarket Gamma API — tag cs2", "json",
     "https://gamma-api.polymarket.com/events?closed=false&limit=100&tag_slug=cs2", None,
     "Prediction market; its match books are used with a spread/volume gate."),
    ("polymarket_cs2b", "Polymarket Gamma API — tag counter-strike-2", "json",
     "https://gamma-api.polymarket.com/events?closed=false&limit=100&tag_slug=counter-strike-2",
     None, "Second tag id; used to check the first tag is not missing markets."),
    ("bovada_cs2", "Bovada coupon API — counter-strike", "json",
     ("https://www.bovada.lv/services/sports/event/coupon/events/A/description/"
      "esports/counter-strike?marketFilterId=def&preMatchOnly=true&lang=en"), None,
     "US-facing book that prices some tier-2 CS2."),
    ("bovada_cs2_alt", "Bovada coupon API — cs2 path", "json",
     ("https://www.bovada.lv/services/sports/event/coupon/events/A/description/"
      "esports/cs2?marketFilterId=def&preMatchOnly=true&lang=en"), None,
     "Path discovery only."),
    ("kambi_cs2", "Kambi/unibet offering API — counter_strike", "json",
     ("https://eu-offering-api.kambicdn.com/offering/v2018/ubse/listView/esports/"
      "counter_strike/all/all/matches.json?lang=en_GB&market=ZZ"), None,
     "Unibet's public Kambi feed; sometimes lists tier-2 CS2."),
    ("kambi_cs2_alt", "Kambi/unibet offering API — csgo path", "json",
     ("https://eu-offering-api.kambicdn.com/offering/v2018/ubse/listView/esports/"
      "csgo/all/all/matches.json?lang=en_GB&market=ZZ"), None,
     "Kambi kept the legacy `csgo` path for CS2; checked so we do not miss it."),
    ("thunderpick", "Thunderpick (esports book)", "json",
     "https://thunderpick.io/api/v2/sports/events?discipline=counter-strike", None,
     "Esports-native book; historically blocks cloud IPs."),
    ("ggbet", "GG.BET (esports book)", "html", "https://gg.bet/en/counter-strike", None,
     "Esports-native book."),
    ("stake", "Stake (esports book)", "json",
     "https://stake.com/_api/graphql", None, "Esports-native book."),
    ("betexplorer", "BetExplorer (odds archive)", "html",
     "https://www.betexplorer.com/counter-strike/", None,
     "Would give historical closing lines for back-testing."),
    ("oddspedia", "Oddspedia (aggregator)", "json",
     "https://oddspedia.com/api/v1/getMatchList?sport=counter-strike&limit=50", None,
     "Aggregator that would widen tier-2 coverage."),
    ("escorenews", "Escorenews (esports odds table)", "html",
     "https://escorenews.com/en/csgo", None, "Esports odds and results listing."),
    ("egamersworld", "EGamersWorld (match/odds listing)", "html",
     "https://egamersworld.com/cs2/matches", None, "Esports odds listing."),
    # ---------------------------------------------------------------- results / ratings
    ("hltv_matches", "HLTV — upcoming matches", "html", "https://www.hltv.org/matches", None,
     "Canonical CS2 schedule; used to reconcile kick-off times."),
    ("hltv_results", "HLTV — results feed", "html", "https://www.hltv.org/results?offset=0", None,
     "Series results for a results-based rating (our own line)."),
    ("hltv_ranking", "HLTV — world ranking", "html", "https://www.hltv.org/ranking/teams", None,
     "Published rating points; an external, citable strength input."),
    ("hltv_stats_teams", "HLTV — team stats index", "html", "https://www.hltv.org/stats/teams", None,
     "Team-level stats pages for verification."),
    ("liquipedia_cs", "Liquipedia Counter-Strike API", "json",
     ("https://liquipedia.net/counterstrike/api.php?action=query&format=json&list=recentchanges"
      "&rclimit=5"), None, "Independent results/matches wiki."),
    ("bo3gg", "bo3.gg API — matches", "json",
     "https://api.bo3.gg/api/v1/matches?page[limit]=20&sort=start_date", None,
     "Third-party schedule/result feed with team ids."),
    ("pandascore", "PandaScore API (unauthenticated)", "json",
     "https://api.pandascore.co/csgo/matches?per_page=5", None,
     "Requires a token; recorded so the limitation is visible."),
    ("oddsapi_io", "Odds-API.io sports index", "json",
     "https://api.odds-api.io/v3/sports?apiKey=demo", None,
     "Line aggregator; needs a key."),
    # ---------------------------------------------------------------- cross-checks
    ("liquipedia_cs_teams", "Liquipedia CS team page sample", "html",
     "https://liquipedia.net/counterstrike/Portal:Teams", None,
     "Roster/org cross-check."),
    ("hltv_team_sample", "HLTV team page sample", "html",
     "https://www.hltv.org/team/6667/faze", None, "Roster/org cross-check."),
]


def classify(status: int, body: bytes) -> tuple[str, int, str]:
    text = body[:4000].decode("utf-8", "replace")
    kind = "empty"
    if status == 200 and body:
        stripped = text.lstrip()
        if stripped.startswith(("[", "{")):
            kind = "json"
        elif "<html" in text.lower() or "<!doctype" in text.lower():
            kind = "html"
        else:
            kind = "text"
    elif status != 200 and body:
        kind = "error_body"
    return kind, len(body), text


def probe_one(slug: str, url: str, headers: dict | None) -> dict:
    st, body = http_get(url, headers=headers, timeout=45, retries=1)
    kind, size, sample = classify(st, body)
    return {
        "slug": slug,
        "url": url,
        "status": st,
        "kind": kind,
        "bytes": size,
        "ok": st == 200 and size > 0,
        "sample": re.sub(r"\s+", " ", sample)[:400],
    }


def main() -> int:
    rows = []
    for slug, label, kind_wanted, url, headers, why in CANDIDATES:
        try:
            r = probe_one(slug, url, headers)
        except Exception as exc:  # noqa: BLE001
            r = {"slug": slug, "url": url, "status": -1, "kind": "exception", "bytes": 0,
                 "ok": False, "sample": str(exc)[:300]}
        r.update({"label": label, "wanted": kind_wanted, "why": why})
        rows.append(r)
        log(f"{slug:26s} status={r['status']:<4} kind={r['kind']:<10} bytes={r['bytes']}")

    doc = {
        "generated_utc": iso(now_utc()),
        "runner": {
            "github_run_id": os.environ.get("GITHUB_RUN_ID", ""),
            "github_run_url": (f"https://github.com/{os.environ.get('GITHUB_REPOSITORY', '')}"
                               f"/actions/runs/{os.environ.get('GITHUB_RUN_ID', '')}")
            if os.environ.get("GITHUB_RUN_ID") else "",
            "python": sys.version.split()[0],
        },
        "tested": len(rows),
        "answered": sum(1 for r in rows if r["ok"]),
        "usable_json": sum(1 for r in rows if r["ok"] and r["kind"] == "json"),
        "usable_html": sum(1 for r in rows if r["ok"] and r["kind"] == "html"),
        "rows": rows,
    }
    save_json(PROBE_PATH, doc)
    with open(os.path.join(CS2_DATA, "source_probe.md"), "w", encoding="utf-8") as fh:
        fh.write(f"# CS2 source probe — {doc['generated_utc']}\n\n")
        fh.write(f"{doc['answered']}/{doc['tested']} candidates answered from the runner "
                 f"(run {doc['runner']['github_run_id']}).\n\n")
        fh.write("| Source | Status | Kind | Bytes | URL |\n|---|---|---|---|---|\n")
        for r in rows:
            fh.write(f"| {r['label']} | {r['status']} | {r['kind']} | {r['bytes']} | "
                     f"<{r['url']}> |\n")
    log(f"probe: {doc['answered']}/{doc['tested']} answered -> {PROBE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
