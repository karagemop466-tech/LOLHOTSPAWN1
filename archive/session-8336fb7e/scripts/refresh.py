#!/usr/bin/env python3
"""End-to-end automated refresh orchestrator for Hotspawn LoL Pick'ems.

Usage:
  - `python3 scripts/refresh.py --fetch-live`  (Scheduled q4h GitHub Actions run: fetches fresh
    Hotspawn API + SSR pages, Pinnacle, Polymarket, Kalshi, Riot Esports & Leaguepedia `Data:`
    pages, recomputes probabilities, rebuilds all 9 static HTML pages, and runs full audit.)
  - `python3 scripts/refresh.py`               (Deterministic local rebuild & audit from current
    `data/sources/` snapshots without external network calls.)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

from build import build_all_pages
from leaguepedia_data import CANONICAL_OVERVIEW_PAGES, harvest_all_data_pages
from originate import run_pipeline
from validate import validate_all

SOURCES_DIR = Path("data/sources")
DATA_DIR = Path("data")
UA = "LOLHotspawnResearchBot/1.0 (+https://github.com/karagemop466-tech/LOLHOTSPAWN1; read-only research)"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def safe_get_json(session: requests.Session, url: str, params: dict[str, Any] | None = None, timeout: int = 25) -> Any | None:
    try:
        resp = session.get(url, params=params, headers={"User-Agent": UA}, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:
        print(f"[warn] Live fetch warning on {url}: {exc}")
    return None


def fetch_live_sources() -> dict[str, Any]:
    """Refresh all primary Hotspawn, sportsbook/exchange, and Leaguepedia `Data:` snapshots."""
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    sess = requests.Session()
    now_iso = utc_now()
    status_log: dict[str, str] = {}

    # 1. Hotspawn scheduled LoL & multi-sport feeds + permalinks + SSR reconciliation
    lol_fx = safe_get_json(
        sess,
        "https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures",
        params={"sport_alias": "lol", "status": "scheduled", "tenantId": "1"},
    )
    if isinstance(lol_fx, list) and len(lol_fx) > 0:
        (SOURCES_DIR / "hotspawn_lol_fixtures.json").write_text(
            json.dumps(lol_fx, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        status_log["hotspawn_lol_fixtures"] = f"ok ({len(lol_fx)} rows)"

    all_fx = safe_get_json(
        sess,
        "https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures",
        params={"status": "scheduled", "tenantId": "1"},
    )
    permalinks = safe_get_json(
        sess,
        "https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/admin/gamification/fixtures/permalinks",
    )
    if isinstance(permalinks, dict):
        (SOURCES_DIR / "hotspawn_permalinks.json").write_text(
            json.dumps(permalinks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    # Reconcile SSR hydration (`script#ng-state`) on `/lol-pickems` and `/lobby`
    ssr_lol_ids: list[str] = []
    try:
        r_ssr = sess.get(f"https://play.hotspawn.com/lol-pickems?cb={int(time.time())}", headers={"User-Agent": UA}, timeout=25)
        if r_ssr.status_code == 200:
            soup = BeautifulSoup(r_ssr.text, "html.parser")
            st = soup.find("script", id="ng-state")
            if st and st.string:
                blob = json.loads(st.string)
                for entry in blob.values():
                    if isinstance(entry, dict) and isinstance(entry.get("b"), list):
                        for item in entry["b"]:
                            if isinstance(item, dict) and item.get("sport_alias") == "lol" and item.get("id"):
                                ssr_lol_ids.append(str(item["id"]))
    except Exception as exc:
        print(f"[warn] SSR check warning: {exc}")

    if isinstance(all_fx, list) and len(all_fx) > 0:
        by_sport: dict[str, int] = {}
        for x in all_fx:
            sp = str(x.get("sport_alias") or "unknown")
            by_sport[sp] = by_sport.get(sp, 0) + 1
        summary_payload = {
            "harvested_at": now_iso,
            "total_all_scheduled": len(all_fx),
            "by_sport": by_sport,
            "ssr_reconciled_lol_count": len(ssr_lol_ids),
            "permalinks_count": len((permalinks or {}).get("permalinks") or (permalinks or {})),
        }
        (SOURCES_DIR / "hotspawn_all_summary.json").write_text(
            json.dumps(summary_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        status_log["hotspawn_all_summary"] = f"ok ({len(all_fx)} all-sports)"

    # 2. Pinnacle Guest Esports API (`sports/12` = League of Legends)
    pin_leagues = safe_get_json(sess, "https://guest.api.arcadia.pinnacle.com/0.1/sports/12/leagues", params={"all": "false"})
    pin_matchups = safe_get_json(sess, "https://guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups", params={"withSpecials": "false"})
    if isinstance(pin_leagues, list) and isinstance(pin_matchups, list):
        active_lg_ids = sorted({
            int((m.get("league") or {}).get("id"))
            for m in pin_matchups
            if (m.get("league") or {}).get("id") and m.get("type") == "matchup"
        })
        markets_map: dict[str, Any] = {}
        for lid in active_lg_ids:
            mk = safe_get_json(sess, f"https://guest.api.arcadia.pinnacle.com/0.1/leagues/{lid}/markets/straight")
            if isinstance(mk, list):
                markets_map[str(lid)] = mk
        (SOURCES_DIR / "pinnacle_lol.json").write_text(
            json.dumps(
                {
                    "harvested_at": now_iso,
                    "lol_leagues": pin_leagues,
                    "lol_matchups": pin_matchups,
                    "lol_straight_markets": markets_map,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        status_log["pinnacle_lol"] = f"ok ({len(pin_matchups)} matchups)"

    # 3. Polymarket Gamma CLOB API
    poly_events = safe_get_json(
        sess,
        "https://gamma-api.polymarket.com/events",
        params={"tag_slug": "league-of-legends", "closed": "false", "limit": "100"},
    )
    if isinstance(poly_events, list):
        (SOURCES_DIR / "polymarket_lol.json").write_text(
            json.dumps(poly_events, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        status_log["polymarket_lol"] = f"ok ({len(poly_events)} events)"

    # 4. Kalshi v2 Regulated Exchange API (`KXLOLGAME`)
    kal_events = safe_get_json(
        sess,
        "https://api.elections.kalshi.com/trade-api/v2/events",
        params={"series_ticker": "KXLOLGAME", "status": "open", "with_nested_markets": "true", "limit": "100"},
    )
    if isinstance(kal_events, dict) and "events" in kal_events:
        (SOURCES_DIR / "kalshi_lol.json").write_text(
            json.dumps(kal_events, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        status_log["kalshi_lol"] = f"ok ({len(kal_events['events'])} events)"

    # 5. Auto-discover any newly added Hotspawn competition on Leaguepedia before harvesting `Data:` pages
    current_fx = json.loads((SOURCES_DIR / "hotspawn_lol_fixtures.json").read_text(encoding="utf-8"))
    for comp_name in sorted({r["competition_name"] for r in current_fx}):
        if comp_name not in CANONICAL_OVERVIEW_PAGES:
            srch = safe_get_json(
                sess,
                "https://lol.fandom.com/api.php",
                params={"action": "query", "list": "search", "srsearch": comp_name, "srlimit": "3", "format": "json"},
            )
            hits = ((srch or {}).get("query") or {}).get("search") or []
            if hits:
                CANONICAL_OVERVIEW_PAGES[comp_name] = [h["title"] for h in hits[:2]]

    harvest_all_data_pages(session=sess)
    status_log["leaguepedia_data_pages"] = "ok"
    return status_log


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh Hotspawn LoL Pick'ems probabilities and static site")
    parser.add_argument("--fetch-live", action="store_true", help="Fetch fresh live API snapshots before rebuilding")
    args = parser.parse_args()

    if args.fetch_live:
        live_status = fetch_live_sources()
        print("Live fetch status:", json.dumps(live_status))

    res = run_pipeline(sources_dir=SOURCES_DIR, data_dir=DATA_DIR)
    pages = build_all_pages(data_dir=DATA_DIR, out_dir=Path("."))
    audit = validate_all(root_dir=Path("."))

    c = res["summary"]["counts"]
    print(
        f"Refresh complete -> {len(pages)} HTML pages built | "
        f"{c['open_total']} open ({c['tier1_market_total']} market + {c['tier2_originated_total']} originated + "
        f"{c['tier3_unresolved_open_total']} unresolved) + {c['stale_past_lock_total']} stale | "
        f"audit={json.dumps(audit)}"
    )


if __name__ == "__main__":
    main()
