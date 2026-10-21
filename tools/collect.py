#!/usr/bin/env python3
"""Collect raw data for every League of Legends pick'em match on Hotspawn.

Sources
-------
1. Hotspawn pick'em fixtures REST API (match inventory)      -> data/raw/hotspawn_lol.json
2. Pinnacle guest API (bookmaker moneylines, sharp book)     -> data/raw/pinnacle_lol.json
3. Leaguepedia CargoExport (series results, all leagues)     -> data/raw/leaguepedia.json
4. LoL Esports official API (Worlds schedule cross-check)    -> data/raw/lolesports.json
5. Polymarket Gamma API (prediction-market LoL markets)      -> data/raw/polymarket.json
6. Book source availability probe                            -> data/sources_status.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (CONTACT_UA, DATA, RAW, ensure_dirs, epoch_ms_to_iso, get_json, http_get,
                    iso, load_json, log, norm_name, now_utc, save_json)

HOTSPAWN_FIXTURES = ("https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/"
                     "fixtures?sport_alias=lol&status=scheduled&tenantId=1")
PINNACLE_KEY = {"x-api-key": "CmX2KcMrXuFmNg6YFbmTxE0y9CIrOi0R", "Accept": "application/json"}
LOLESPORTS_KEY = {"x-api-key": "0TvQnueqKa5mxJntVWt0w4LpLfEkrV1Ta8rQBb9Z"}
LEAGUEPEDIA_WINDOW_START = "2025-09-01 00:00:00"  # 13.5 months of series results


# --------------------------------------------------------------------------- hotspawn
def collect_hotspawn() -> dict:
    st, data, err = get_json(HOTSPAWN_FIXTURES, retries=3)
    if st != 200 or not isinstance(data, list):
        raise SystemExit(f"Hotspawn fixtures failed: status={st} err={err}")
    out = []
    for f in data:
        if f.get("sport_alias") != "lol":
            continue
        out.append({
            "id": str(f["id"]),
            "competition_id": str(f.get("competition_id")),
            "competition": f.get("competition_name"),
            "status": f.get("status"),
            "start_utc": epoch_ms_to_iso(f.get("scheduled_start_time")),
            "lock_utc": epoch_ms_to_iso(f.get("lock_time")),
            "tier": f.get("tier"),
            "stage": f.get("stage"),
            "best_of": f.get("best_of"),
            "series_format": f.get("series_format"),
            "points": f.get("offered_points"),
            "team0": {"id": str(f.get("participants0_id")), "name": f.get("participants0_name")},
            "team1": {"id": str(f.get("participants1_id")), "name": f.get("participants1_name")},
            # Community pick share is captured for transparency but is NEVER used by the model.
            "community_pick_pct": {
                "team0": f.get("participants0_picked_percent"),
                "team1": f.get("participants1_picked_percent"),
                "total_picks": f.get("total_picks"),
            },
            "pickem_url": "https://play.hotspawn.com/lol-pickems",
        })
    out.sort(key=lambda m: (m["start_utc"] or "", m["competition"], m["id"]))
    save_json(os.path.join(RAW, "hotspawn_lol.json"), {
        "fetched_utc": iso(now_utc()),
        "source_url": HOTSPAWN_FIXTURES,
        "count": len(out),
        "fixtures": out,
    })
    log(f"hotspawn: {len(out)} LoL fixtures")
    return {"count": len(out)}


# --------------------------------------------------------------------------- pinnacle
def american_to_decimal(price: float) -> float | None:
    try:
        p = float(price)
    except (TypeError, ValueError):
        return None
    if p == 0:
        return None
    return round(1 + (p / 100 if p > 0 else 100 / abs(p)), 4)


def collect_pinnacle() -> dict:
    st, matchups, err = get_json("https://guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups",
                                 headers=PINNACLE_KEY, retries=3)
    if st != 200 or not isinstance(matchups, list):
        save_json(os.path.join(RAW, "pinnacle_lol.json"),
                  {"fetched_utc": iso(now_utc()), "error": f"status={st} {err}", "matchups": []})
        log(f"pinnacle: FAILED status={st} {err}")
        return {"count": 0, "error": err}

    lol = [m for m in matchups
           if "league of legends" in (str(m.get("league", {}).get("name", "")) + " "
                                      + str((m.get("league", {}).get("sport") or {}).get("name", ""))).lower()]
    markets_out = []
    for m in lol:
        if m.get("type") != "matchup":
            continue
        st2, markets, err2 = get_json(
            f"https://guest.api.arcadia.pinnacle.com/0.1/matchups/{m['id']}/markets/related/straight",
            headers=PINNACLE_KEY, retries=2)
        time.sleep(0.25)
        if st2 != 200 or not isinstance(markets, list):
            continue
        ml = [x for x in markets if x.get("type") == "moneyline" and x.get("period") == 0
              and x.get("status") == "open"]
        if not ml:
            continue
        prices = ml[0].get("prices", [])
        row = {"matchup_id": m["id"], "league": m["league"]["name"],
               "start_utc": m.get("startTime"), "market_key": ml[0].get("key"),
               "prices": {}}
        for p in prices:
            des = p.get("designation")
            dec = american_to_decimal(p.get("price"))
            if des and dec:
                row["prices"][des] = {"american": p.get("price"), "decimal": dec}
        parts = m.get("participants", [])
        row["participants"] = [{"name": p.get("name"), "alignment": p.get("alignment")} for p in parts]
        if "home" in row["prices"] and "away" in row["prices"]:
            markets_out.append(row)

    save_json(os.path.join(RAW, "pinnacle_lol.json"), {
        "fetched_utc": iso(now_utc()),
        "source_url": "https://guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups",
        "source_note": ("Pinnacle guest API, sport 12 (E Sports), moneyline period 0, "
                        "markets/related/straight"),
        "lol_matchup_count": len(lol),
        "priced_count": len(markets_out),
        "markets": markets_out,
    })
    log(f"pinnacle: {len(lol)} LoL matchups, {len(markets_out)} with open moneylines")
    return {"count": len(markets_out)}


# --------------------------------------------------------------------------- leaguepedia
def cargo_export(fields: str, where: str | None, limit: int = 500, offset: int = 0,
                 order_by: str | None = None, tables: str = "MatchSchedule") -> tuple[list, str]:
    params = {"tables": tables, "fields": fields, "limit": str(limit), "offset": str(offset),
              "format": "json"}
    if where:
        params["where"] = where
    if order_by:
        params["order_by"] = order_by
    url = "https://lol.fandom.com/wiki/Special:CargoExport?" + urllib.parse.urlencode(params)
    st, data, err = get_json(url, headers={"User-Agent": CONTACT_UA}, retries=2)
    if st != 200 or not isinstance(data, list):
        return [], err or f"status={st}"
    return data, ""


def collect_leaguepedia(max_rows: int = 30000) -> dict:
    fields = ("MatchSchedule.MatchId,MatchSchedule.OverviewPage,MatchSchedule.Team1,"
              "MatchSchedule.Team2,MatchSchedule.Winner,MatchSchedule.Team1Score,"
              "MatchSchedule.Team2Score,MatchSchedule.DateTime_UTC,MatchSchedule.BestOf,"
              "MatchSchedule.Tab,MatchSchedule.Round,MatchSchedule.UniqueMatch")
    rows: list[dict] = []
    offset = 0
    err = ""
    while offset < max_rows:
        chunk, e = cargo_export(fields, f"MatchSchedule.DateTime_UTC >= '{LEAGUEPEDIA_WINDOW_START}'",
                                limit=500, offset=offset,
                                order_by="MatchSchedule.DateTime_UTC DESC")
        if not chunk:
            err = e
            break
        rows.extend(chunk)
        if len(chunk) < 500:
            break
        offset += 500
        time.sleep(0.6)

    clean = []
    seen = set()
    for r in rows:
        mid = r.get("MatchId") or ""
        if mid and mid in seen:
            continue
        seen.add(mid)
        t1, t2 = r.get("Team1"), r.get("Team2")
        if not t1 or not t2 or t1 == "TBD" or t2 == "TBD":
            continue
        winner = r.get("Winner")
        clean.append({
            "match_id": mid,
            "overview_page": r.get("OverviewPage") or "",
            "team1": t1,
            "team2": t2,
            "winner": str(winner) if winner not in (None, "") else None,
            "team1_score": r.get("Team1Score"),
            "team2_score": r.get("Team2Score"),
            "utc": r.get("DateTime UTC") or r.get("DateTime_UTC"),
            "best_of": r.get("BestOf"),
            "tab": r.get("Tab") or "",
            "round": r.get("Round") or "",
        })
    save_json(os.path.join(RAW, "leaguepedia.json"), {
        "fetched_utc": iso(now_utc()),
        "source_url": "https://lol.fandom.com/wiki/Special:CargoExport",
        "query": {"tables": "MatchSchedule", "fields": fields,
                  "where": f"MatchSchedule.DateTime_UTC >= '{LEAGUEPEDIA_WINDOW_START}'"},
        "row_count": len(clean),
        "error": err,
        "matches": clean,
    })
    log(f"leaguepedia: {len(clean)} series rows (err={err!r})")
    return {"count": len(clean), "error": err}


# --------------------------------------------------------------------------- lolesports
def collect_lolesports() -> dict:
    url = ("https://esports-api.lolesports.com/persisted/gw/getSchedule?hl=en-US"
           "&leagueId=98767975604431411")  # Worlds
    st, data, err = get_json(url, headers=LOLESPORTS_KEY, retries=2)
    events = []
    if st == 200 and isinstance(data, dict):
        for ev in data.get("data", {}).get("schedule", {}).get("events", []) or []:
            match = ev.get("match") or {}
            teams = [t.get("name") for t in match.get("teams", [])]
            events.append({
                "start_utc": ev.get("startTime"),
                "state": ev.get("state"),
                "block": ev.get("blockName"),
                "league": (ev.get("league") or {}).get("name"),
                "teams": teams,
                "id": match.get("id"),
            })
    save_json(os.path.join(RAW, "lolesports.json"), {
        "fetched_utc": iso(now_utc()),
        "source_url": url,
        "status": st,
        "error": err,
        "events": events,
    })
    log(f"lolesports: {len(events)} Worlds events (status={st})")
    return {"count": len(events), "status": st}


# --------------------------------------------------------------------------- polymarket
def collect_polymarket() -> dict:
    url = ("https://gamma-api.polymarket.com/events?closed=false&limit=100"
           "&tag_slug=league-of-legends")
    st, data, err = get_json(url, retries=2)
    markets = []
    if st == 200 and isinstance(data, list):
        for ev in data:
            for mk in ev.get("markets", []) or []:
                q = mk.get("question") or ""
                if not re.search(r"\bvs\.?\b", q, re.I):
                    continue
                try:
                    outcomes = json.loads(mk.get("outcomes") or "[]")
                    prices = json.loads(mk.get("outcomePrices") or "[]")
                except Exception:  # noqa: BLE001
                    continue
                markets.append({
                    "event": ev.get("title"), "question": q, "slug": mk.get("slug"),
                    "outcomes": outcomes, "prices": prices,
                    "volume": mk.get("volume"), "end": mk.get("endDate"),
                    "event_start": ev.get("startDate"),
                })
    save_json(os.path.join(RAW, "polymarket.json"), {
        "fetched_utc": iso(now_utc()),
        "source_url": url,
        "status": st,
        "error": err,
        "match_markets": markets,
    })
    log(f"polymarket: {len(markets)} match-level markets (status={st})")
    return {"count": len(markets), "status": st}


# --------------------------------------------------------------------------- availability
BOOK_PROBES = [
    ("Pinnacle", "https://guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups",
     "Sharp esportsbook; guest REST API", {"x-api-key": "CmX2KcMrXuFmNg6YFbmTxE0y9CIrOi0R"}),
    ("GG.BET", "https://gg.bet/en/esports/league-of-legends", "Established LoL betting site", None),
    ("BC.GAME", "https://bc.game/sports", "Crypto esportsbook", None),
    ("EGamersWorld", "https://egamersworld.com/lo-l/matches", "Esports odds aggregator", None),
    ("Oddspedia", "https://oddspedia.com/esports/league-of-legends", "Odds comparison engine", None),
    ("OddsPortal", "https://www.oddsportal.com/esports/league-of-legends/", "Odds comparison engine", None),
    ("BetExplorer", "https://www.betexplorer.com/esports/league-of-legends/", "Odds comparison engine", None),
    ("Unibet/Kambi", "https://eu-offering-api.kambicdn.com/offering/v2018/ubus/listView/esports.json",
     "Esportsbook API", None),
    ("Polymarket", "https://gamma-api.polymarket.com/events?closed=false&limit=5&tag_slug=league-of-legends",
     "Prediction market", None),
    ("Hotspawn fixtures API", "https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=lol&status=scheduled&tenantId=1",
     "Match inventory (not a probability source)", None),
    ("Leaguepedia", "https://lol.fandom.com/wiki/Special:CargoExport?tables=MatchSchedule&fields=MatchSchedule.MatchId&limit=1&format=json",
     "Community results database", {"User-Agent": CONTACT_UA}),
    ("LoL Esports (Riot)", "https://esports-api.lolesports.com/persisted/gw/getLeagues?hl=en-US",
     "Official Riot esports API", LOLESPORTS_KEY),
]


def collect_source_status() -> dict:
    rows = []
    for name, url, note, headers in BOOK_PROBES:
        st, body = http_get(url, headers=headers, timeout=20, retries=0)
        rows.append({
            "name": name, "url": url, "note": note, "status": st,
            "ok": st == 200, "bytes": len(body),
            "blocked_note": ("reachable" if st == 200 else
                             ("blocked by bot protection" if b"Just a moment" in body else
                              ("region blocked" if b"not accepting visitors" in body else "unavailable"))),
            "checked_utc": iso(now_utc()),
        })
    save_json(os.path.join(DATA, "sources_status.json"), {
        "checked_utc": iso(now_utc()), "sources": rows})
    log("sources: " + ", ".join(f"{r['name']}={r['status']}" for r in rows))
    return {"count": len(rows)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=None)
    args = ap.parse_args()
    ensure_dirs()
    steps = {
        "hotspawn": collect_hotspawn,
        "pinnacle": collect_pinnacle,
        "leaguepedia": collect_leaguepedia,
        "lolesports": collect_lolesports,
        "polymarket": collect_polymarket,
        "sources": collect_source_status,
    }
    for name, fn in steps.items():
        if args.only and name not in args.only:
            continue
        try:
            fn()
        except SystemExit:
            raise
        except Exception as exc:  # noqa: BLE001
            log(f"{name} ERROR: {exc}")


if __name__ == "__main__":
    main()
