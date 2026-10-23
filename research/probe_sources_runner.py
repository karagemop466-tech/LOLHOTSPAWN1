#!/usr/bin/env python3
"""Probe candidate League of Legends betting / esportsbook endpoints.

The research sandbox used to build this repo has no outbound access to bookmakers,
so this script exists to be run by GitHub Actions (see `.github/workflows/probe-sources.yml`).
It records, for every candidate source, the real HTTP status, content type, payload
size, a short body fingerprint, and whether the response looks like machine-readable
JSON. Nothing is inferred: an endpoint that returns HTML or a block page is recorded
as such and is *not* used to price matches.

Output: data/source_probes.json (committed, timestamped, reviewable).
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
from common import CONTACT_UA, DATA, ensure_dirs, http_get, iso, now_utc, save_json, log  # noqa: E402

PINNACLE_KEY = {"x-api-key": "CmX2KcMrXuFmNg6YFbmTxE0y9CIrOi0R", "Accept": "application/json"}

# (name, category, url, headers)
CANDIDATES: list[tuple[str, str, str, dict | None]] = [
    # --- baseline venues already in the consensus -------------------------------
    ("Pinnacle (guest API)", "sharp book", "https://guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups", PINNACLE_KEY),
    ("Kalshi (CFTC)", "regulated exchange",
     "https://api.elections.kalshi.com/trade-api/v2/events?series_ticker=KXLOLGAME&status=open&with_nested_markets=true&limit=100", None),
    ("Bovada", "esportsbook",
     "https://www.bovada.lv/services/sports/event/coupon/events/A/description/esports/league-of-legends?marketFilterId=def&preMatchOnly=true&lang=en", None),
    ("Polymarket (gamma)", "prediction market",
     "https://gamma-api.polymarket.com/events?closed=false&limit=20&tag_slug=league-of-legends", None),
    # --- established general sportsbooks with LoL -----------------------------
    ("Betway esports", "established book", "https://sports.betway.com/en/sports/grp/esports", None),
    ("bet365 esports", "established book", "https://www.bet365.com/#/AC/B18/C20464932/D1/E1/", None),
    ("BetOnline esports", "established book", "https://www.betonline.ag/sportsbook/esports", None),
    ("Everygame esports", "established book", "https://www.everygame.eu/en/sportsbook/esports", None),
    ("SportsBetting.ag esports", "established book", "https://www.sportsbetting.ag/sportsbook/esports", None),
    ("Betsson esports", "established book", "https://www.betsson.com/en/sportsbook", None),
    ("BetUS esports", "established book", "https://www.betus.com.pa/sportsbook/esports/", None),
    ("1xBet esports", "established book", "https://1xbet.com/en/line/esports/", None),
    ("Betfair Exchange esports", "exchange", "https://www.betfair.com/exchange/plus/esports", None),
    ("DraftKings esports", "US book", "https://sportsbook.draftkings.com/leagues/esports/league-of-legends", None),
    ("FanDuel esports", "US book", "https://sportsbook.fanduel.com/esports/league-of-legends", None),
    ("BetMGM esports", "US book", "https://sports.betmgm.com/en/sports/esports-6", None),
    # --- esports-native books -------------------------------------------------
    ("GG.BET LoL", "esports specialist", "https://gg.bet/en/esports/league-of-legends", None),
    ("Thunderpick LoL", "esports specialist", "https://thunderpick.io/esports/league-of-legends", None),
    ("Rivalry LoL", "esports specialist", "https://www.rivalry.com/esports/league-of-legends", None),
    ("BC.GAME sports", "crypto esportsbook", "https://bc.game/sports", None),
    ("Stake LoL", "crypto esportsbook", "https://stake.com/sports/esports/league-of-legends", None),
    ("Unibet/Kambi esports", "esportsbook API",
     "https://eu-offering-api.kambicdn.com/offering/v2018/ubus/listView/esports.json", None),
    # --- odds comparison engines ----------------------------------------------
    ("EGamersWorld LoL bets", "odds aggregator", "https://egamersworld.com/lol/bets", None),
    ("Oddspedia LoL", "odds aggregator", "https://oddspedia.com/esports/league-of-legends", None),
    ("OddsPortal LoL", "odds aggregator", "https://www.oddsportal.com/esports/league-of-legends/", None),
    ("BetExplorer LoL", "odds aggregator", "https://www.betexplorer.com/esports/league-of-legends/", None),
    ("OddsPapi LoL (key required)", "odds API", "https://api.oddspapi.io/v4/fixtures?sportId=18", None),
    ("Odds-API.io sports index", "odds API", "https://api.odds-api.io/v3/sports", None),
    # --- community / results references (never used as a probability input) ---
    ("Leaguepedia Cargo", "community results",
     "https://lol.fandom.com/wiki/Special:CargoExport?tables=MatchSchedule&fields=MatchSchedule.MatchId&limit=1&format=json",
     {"User-Agent": CONTACT_UA}),
    ("gol.gg", "community stats", "https://gol.gg/esports/home/", None),
    ("Oracle's Elixir", "community data", "https://oracleselixir.com/", None),
    # --- inventory source ------------------------------------------------------
    ("Hotspawn fixtures API", "inventory",
     "https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=lol&status=scheduled&tenantId=1", None),
]


def classify(body: bytes) -> str:
    head = body[:400].lstrip()
    if head.startswith(b"{") or head.startswith(b"["):
        return "json"
    low = body[:6000].lower()
    if b"just a moment" in low or b"cf-challenge" in low or b"captcha" in low:
        return "bot-challenge"
    if b"not accepting visitors" in low or b"restricted" in low:
        return "region-block"
    if b"<html" in low or b"<!doctype" in low:
        return "html"
    return "other"


def main() -> None:
    ensure_dirs()
    rows = []
    for name, category, url, headers in CANDIDATES:
        st, body = http_get(url, headers=headers, timeout=25, retries=0)
        kind = classify(body) if body else "empty"
        rows.append({
            "name": name,
            "category": category,
            "url": url,
            "status": st,
            "ok": st == 200,
            "kind": kind,
            "bytes": len(body),
            "fingerprint": body[:180].decode("utf-8", "replace").replace("\n", " ").strip(),
            "checked_utc": iso(now_utc()),
        })
        log(f"{name}: {st} {kind} {len(body)}b")
    save_json(os.path.join(DATA, "source_probes.json"), {
        "checked_utc": iso(now_utc()),
        "probe_user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "note": ("Live HTTP probe results from a GitHub Actions ubuntu-latest runner. "
                 "A non-200 status means the venue could not be verified on that run and was "
                 "not used to price any match."),
        "results": rows,
    })
    print(f"probed {len(rows)} candidates; {sum(1 for r in rows if r['ok'])} HTTP 200")


if __name__ == "__main__":
    main()
