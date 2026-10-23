#!/usr/bin/env python3
"""Measure the real external-market ceiling for League of Legends.

Question the brief asks: how many of the matches listed on Hotspawn can *any* external
book price? This script enumerates every LoL league on Pinnacle's guest API, counts the
matchups that carry an open two-sided moneyline, and lists the Kalshi and Polymarket LoL
inventory. The output is a factual coverage ceiling, not a pick.

Output: research/market_ceiling.json
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
from common import get_json, iso, now_utc, save_json, log  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "research", "market_ceiling.json")
PIN_KEY = {"x-api-key": "CmX2KcMrXuFmNg6YFbmTxE0y9CIrOi0R", "Accept": "application/json"}


def pinnacle() -> dict:
    st, leagues, err = get_json("https://guest.api.arcadia.pinnacle.com/0.1/sports/12/leagues",
                                headers=PIN_KEY, timeout=45, retries=2)
    if st != 200 or not isinstance(leagues, list):
        return {"status": st, "error": err, "leagues": []}
    lol = [lg for lg in leagues if "league of legends" in str(lg.get("name", "")).lower()]
    out = []
    for lg in lol:
        lid = lg["id"]
        st2, matchups, err2 = get_json(
            f"https://guest.api.arcadia.pinnacle.com/0.1/leagues/{lid}/matchups",
            headers=PIN_KEY, timeout=45, retries=1)
        priced, total = [], 0
        if st2 == 200 and isinstance(matchups, list):
            total = len(matchups)
            for m in matchups:
                if m.get("type") != "matchup" or m.get("parent") is not None:
                    continue
                st3, markets, _ = get_json(
                    f"https://guest.api.arcadia.pinnacle.com/0.1/matchups/{m['id']}/markets/related/straight",
                    headers=PIN_KEY, timeout=30, retries=1)
                if st3 != 200 or not isinstance(markets, list):
                    continue
                ml = [x for x in markets if x.get("type") == "moneyline" and x.get("period") == 0
                      and x.get("status") == "open"]
                if not ml:
                    continue
                parts = m.get("participants") or []
                names = [p.get("name") for p in parts]
                # Pinnacle also lists a separate "(Kills)" market family; those are not
                # match-winner prices and must never be used as one.
                if any("(Kills)" in str(n) for n in names):
                    continue
                priced.append({"matchup_id": m["id"], "start": m.get("startTime"),
                               "participants": names,
                               "prices": [{"designation": p.get("designation"),
                                           "price": p.get("price")} for p in ml[0].get("prices", [])]})
        out.append({"league_id": lid, "name": lg.get("name"), "matchup_count": lg.get("matchupCount"),
                    "matchups_returned": total, "priced_moneylines": len(priced),
                    "status": st2, "error": err2, "priced": priced})
        log(f"pinnacle {lg.get('name')}: {len(priced)} priced / {total} matchups")
    return {"status": st, "lol_league_count": len(lol), "leagues": out}


def kalshi() -> dict:
    url = ("https://api.elections.kalshi.com/trade-api/v2/events?series_ticker=KXLOLGAME"
           "&status=open&with_nested_markets=true&limit=200")
    st, data, err = get_json(url, timeout=45, retries=1)
    events = (data or {}).get("events") or []
    rows = []
    for ev in events:
        mk = ev.get("markets") or []
        yes = [m.get("yes_sub_title") for m in mk]
        rows.append({"ticker": ev.get("event_ticker"), "title": ev.get("title"),
                     "close": ev.get("close_time"), "outcomes": yes})
    return {"status": st, "error": err, "event_count": len(rows), "events": rows}


def polymarket() -> dict:
    url = ("https://gamma-api.polymarket.com/events?closed=false&limit=200"
           "&tag_slug=league-of-legends")
    st, data, err = get_json(url, timeout=60, retries=1)
    rows = []
    for ev in data if isinstance(data, list) else []:
        for mk in ev.get("markets") or []:
            q = mk.get("question") or ""
            if " vs" not in q.lower() or "winner" in q.lower() and "game" in q.lower():
                continue
            rows.append({"question": q, "slug": mk.get("slug"),
                         "prices": mk.get("outcomePrices"),
                         "volume": mk.get("volume"), "end": mk.get("endDate"),
                         "start": ev.get("startDate")})
    return {"status": st, "error": err, "match_market_count": len(rows), "markets": rows}


def main() -> None:
    doc = {"checked_utc": iso(now_utc()), "pinnacle": pinnacle(), "kalshi": kalshi(),
           "polymarket": polymarket()}
    save_json(OUT, doc)
    pin = doc["pinnacle"]
    summaries = {lg["name"]: {"priced": lg["priced_moneylines"], "matchups": lg["matchups_returned"]}
                 for lg in pin.get("leagues", [])}
    print(json.dumps({"pinnacle_leagues": summaries,
                      "kalshi_events": doc["kalshi"]["event_count"],
                      "polymarket_match_markets": doc["polymarket"]["match_market_count"]}, indent=1))


if __name__ == "__main__":
    main()
