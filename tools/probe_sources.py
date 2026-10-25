#!/usr/bin/env python3
# Re-probe requested 2026-10-25 (session 2faec1ff, T1): fresh runner receipts.
"""Probe external League of Legends line sources from the build runner.

The published picks must never invent a bookmaker quote. This script only records
what each candidate source actually returned to the runner: HTTP status, final URL,
content type, byte count, the Hotspawn team names that were found in the response,
and (for JSON endpoints) whether odds-like keys are present.

Nothing here is used as a probability until a parser is added to tools/collect.py
and the source shows up with a live receipt in data/raw/.

Output: data/probe/sources_probe.json  (committed as evidence)

Run:  python3 tools/probe_sources.py
"""
from __future__ import annotations

import gzip
import json
import os
import re
import sys
import time
import zlib
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DATA, RAW, ROOT, iso, load_json, log, now_utc, save_json  # noqa: E402

try:
    import requests
except ImportError:  # pragma: no cover - the workflow installs requests
    requests = None

PROBE_DIR = os.path.join(DATA, "probe")
BROWSER_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"),
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
               "application/json;q=0.9,*/*;q=0.8"),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Cache-Control": "no-cache",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Upgrade-Insecure-Requests": "1",
}

# Candidate sources. `kind` is what the source is, `scope` says why we care.
SOURCES = [
    # --- established sportsbooks / exchanges already integrated ---------------
    ("Pinnacle guest API", "https://guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups",
     "established book", "control: sharp LoL moneylines"),
    ("Pinnacle league list", "https://guest.api.arcadia.pinnacle.com/0.1/sports/12/leagues",
     "established book", "does Pinnacle list tier-2 leagues at all?"),
    ("Polymarket gamma", "https://gamma-api.polymarket.com/events?closed=false&limit=20&tag_slug=league-of-legends",
     "prediction market", "control: full-series CLOB"),
    ("Kalshi KXLOLGAME", "https://api.elections.kalshi.com/trade-api/v2/events?series_ticker=KXLOLGAME&status=open&with_nested_markets=true&limit=50",
     "regulated exchange", "control: CFTC contract book"),
    ("Bovada LoL coupon", "https://www.bovada.lv/services/sports/event/coupon/events/A/description/esports/league-of-legends?marketFilterId=def&preMatchOnly=true&lang=en",
     "established book", "control: US esportsbook moneylines"),

    # --- esportsbooks / specialist books -------------------------------------
    ("GG.BET LoL", "https://gg.bet/en/esports/league-of-legends", "esportsbook", "broad LoL coverage incl. tier-2"),
    ("BC.GAME sports", "https://bc.game/sports/esports/league-of-legends", "crypto esportsbook", "low-tier LoL markets"),
    ("Thunderpick LoL", "https://thunderpick.io/esports/league-of-legends", "esportsbook", "low-tier LoL markets"),
    ("Thunderpick API", "https://api.thunderpick.io/api/v1/sports", "esportsbook API", "JSON odds feed"),
    ("Rivalry esports", "https://www.rivalry.com/esports/league-of-legends", "esportsbook", "low-tier LoL markets"),
    ("Rivalry API", "https://api.rivalry.com/api/v1/sport/league-of-legends", "esportsbook API", "JSON odds feed"),
    ("Stake esports", "https://stake.com/sports/esports/league-of-legends", "crypto esportsbook", "low-tier LoL markets"),
    ("1xBet line feed", "https://1xbet.com/LineFeed/Get1x2_VZip?sports=249&count=50&mode=4&country=1&getEmpty=true",
     "high-street book API", "the widest low-tier LoL coupon in the market"),
    ("Betboom LoL", "https://betboom.ru/sport/lol", "esportsbook", "CIS book with tier-2 LoL"),
    ("Marathonbet LoL", "https://www.marathonbet.com/en/betting/Esports/League+of+Legends", "established book", "EU book"),
    ("Betano LoL", "https://www.betano.com/sport/esports/league-of-legends/", "established book", "EU book"),
    ("Betway esports", "https://sports.betway.com/en/sports/grp/sport/esports", "established book", "UK book"),
    ("Unibet LoL", "https://www.unibet.com/betting/sports/filter/esports/league_of_legends", "established book", "EU book"),
    ("Betsson esports", "https://www.betsson.com/en/sportsbook/esports", "established book", "Nordic book"),

    # --- odds aggregators / comparison engines -------------------------------
    ("EGamersWorld LoL", "https://egamersworld.com/lol/matches", "odds aggregator",
     "the widest published LoL coupon, incl. national divisions"),
    ("EGamersWorld match page", "https://egamersworld.com/lol/match/q8qUtLA6g/geng-vs-invictus-gaming-x7EbSp5BR",
     "odds aggregator", "per-match bookmaker prices"),
    ("Oddspedia LoL", "https://oddspedia.com/esports/league-of-legends", "odds aggregator", "multi-book comparison"),
    ("OddsPortal LoL", "https://www.oddsportal.com/esports/league-of-legends/", "odds aggregator", "multi-book comparison"),
    ("Flashscore LoL", "https://www.flashscore.com/esports/league-of-legends/", "odds aggregator", "multi-book comparison"),
    ("Sofascore esports API", "https://www.sofascore.com/api/v1/sport/esports/scheduled-events/2026-10-23",
     "odds aggregator", "multi-book comparison"),
    ("bo3.gg LoL", "https://bo3.gg/lol/matches", "odds aggregator", "match list with odds"),
    ("Escorenews LoL", "https://escorenews.com/en/lol", "esports news + odds", "match pages carry book prices"),
    ("BetExplorer LoL", "https://www.betexplorer.com/esports/league-of-legends/", "odds aggregator", "multi-book comparison"),

    # --- added 2026-10-25 (session 63c67a23): US books with public JSON
    # sportscontent endpoints plus two keyed odds APIs, so the runner records
    # whether *any* of them exposes a tier-2 LoL price. A 200 HTML shell is
    # still not a line; only a parsed JSON price can ever become a number.
    ("DraftKings LoL (public content API)",
     "https://sportsbook-nash.draftkings.com/api/sportscontent/dkusoh/v1/leagues/19873",
     "US sportsbook", "does DK expose an esports LoL JSON coupon?"),
    ("FanDuel LoL (page API)",
     "https://sbapi.nj.sportsbook.fanduel.com/api/content-managed-page?page=CUSTOM&customPageId=lol",
     "US sportsbook", "does FanDuel expose an esports LoL JSON coupon?"),
    ("BetOnline esports lines",
     "https://www.betonline.ag/sportsbook/api/lines/esports",
     "US sportsbook", "JSON lines feed"),
    ("Betano LoL JSON API",
     "https://www.betano.com/api/sport/esports/league-of-legends/",
     "established book", "JSON coupon behind the HTML page"),
    ("The Odds API LoL (key required)",
     "https://api.the-odds-api.com/v4/sports/esports_league_of_legends/odds?regions=eu&markets=h2h",
     "odds API", "keyed aggregator - 401 expected, recorded for the audit trail"),
    ("OddsPapi LoL (key required)",
     "https://api.oddspapi.io/v4/fixtures?sportId=18",
     "odds API", "keyed aggregator - 401 expected, recorded for the audit trail"),

    # --- official / results sources (no odds, used for fixtures/results) -----
    ("Riot LoL Esports schedule", "https://esports-api.lolesports.com/persisted/gw/getSchedule?hl=en-US",
     "official", "official schedule cross-check (needs api key header)"),
    ("Leaguepedia Cargo", "https://lol.fandom.com/wiki/Special:CargoExport?tables=MatchSchedule&fields=OverviewPage,Team1,Team2,Winner,DateTime_UTC&limit=5&format=json",
     "results database", "control: series results used by the model"),
    ("Liquipedia LoL matches", "https://liquipedia.net/leagueoflegends/Portal:Matches",
     "results database", "cross-check for low-tier fixtures"),
]


def _decode(content: bytes, encoding: str) -> str:
    if (encoding or "").lower() == "gzip":
        try:
            content = gzip.decompress(content)
        except OSError:
            pass
    elif (encoding or "").lower() == "deflate":
        try:
            content = zlib.decompress(content)
        except zlib.error:
            pass
    for enc in ("utf-8", "latin-1"):
        try:
            return content.decode(enc, "replace")
        except (UnicodeDecodeError, LookupError):
            continue
    return content.decode("utf-8", "replace")


def fetch(url: str, timeout: int = 25) -> dict:
    started = time.time()
    if requests is None:
        return {"status": None, "error": "requests not installed", "bytes": 0, "text": ""}
    try:
        r = requests.get(url, headers=BROWSER_HEADERS, timeout=timeout, allow_redirects=True)
        body = r.content[:1_500_000]
        text = _decode(body, r.headers.get("Content-Encoding", ""))
        return {
            "status": r.status_code,
            "final_url": r.url,
            "content_type": r.headers.get("Content-Type", ""),
            "bytes": len(r.content),
            "text": text,
            "elapsed_ms": int((time.time() - started) * 1000),
            "server": r.headers.get("Server", ""),
        }
    except Exception as exc:  # noqa: BLE001 - probe records any failure verbatim
        return {"status": None, "error": f"{type(exc).__name__}: {exc}", "bytes": 0,
                "elapsed_ms": int((time.time() - started) * 1000), "text": ""}


def odds_signals(text: str) -> dict:
    """Look for evidence of real priced markets rather than page chrome."""
    lowered = text.lower()
    signals = {
        "has_decimal_pair": bool(re.search(r"\b1\.\d{2}\b.{0,40}\b[2-9]\.\d{2}\b", text)),
        "mentions_bookmaker": any(b in lowered for b in
                                  ("pinnacle", "bet365", "1xbet", "gg.bet", "betway",
                                   "bovada", "unibet", "betano", "thunderpick", "rivalry")),
        "mentions_odds": any(w in lowered for w in ("odds", "moneyline", "money line", "decimal")),
        "mentions_league_of_legends": "league of legends" in lowered,
    }
    return signals


def known_names() -> list[str]:
    """Team names from today's Hotspawn list, split into headline and low-tier."""
    hs = load_json(os.path.join(RAW, "hotspawn_lol.json")) or {}
    fixtures = hs.get("fixtures") or []
    worlds, low = set(), set()
    for f in fixtures:
        pair = (f.get("team0", {}).get("name"), f.get("team1", {}).get("name"))
        if not all(pair):
            continue
        bucket = worlds if "Worlds" in (f.get("competition") or "") else low
        bucket.update(pair)
    # Prefer compact, distinctive names for substring tests.
    return (sorted({n for n in worlds if len(n) >= 5})[:8] +
            sorted({n for n in low if len(n) >= 6})[:24])


def main() -> None:
    os.makedirs(PROBE_DIR, exist_ok=True)
    names = known_names()
    results = []
    for name, url, kind, why in SOURCES:
        headers_note = ""
        if name == "Riot LoL Esports schedule":
            headers_note = "no api key header on purpose: records the unauthenticated response"
        item = fetch(url)
        text = item.pop("text", "") or ""
        found = [n for n in names if n.lower() in text.lower()]
        row = {
            "name": name,
            "url": url,
            "kind": kind,
            "why": why,
            "note": headers_note,
            "checked_utc": iso(now_utc()),
            **item,
            "found_team_names": found[:10],
            "found_team_count": len(found),
            "signals": odds_signals(text) if text else {},
            "snippet": re.sub(r"\s+", " ", text[:400]).strip() if text else "",
        }
        results.append(row)
        log(f"probe {name:32s} status={row.get('status')} bytes={row.get('bytes')} "
            f"teams={row['found_team_count']}")

    payload = {
        "probed_utc": iso(now_utc()),
        "runner_note": ("Executed from a GitHub Actions runner (Linux, US egress). "
                        "Status/bytes are what the build runner actually received; a 403 from the "
                        "runner is recorded as blocked even if a browser can open the page."),
        "team_names_used": names,
        "sources": results,
    }
    save_json(os.path.join(PROBE_DIR, "sources_probe.json"), payload)
    ok = [r for r in results if r.get("status") == 200]
    usable = [r for r in ok if r["found_team_count"] >= 2 and
              (r.get("signals") or {}).get("has_decimal_pair")]
    log(f"probe summary: {len(ok)}/{len(results)} HTTP 200, {len(usable)} show team names + decimal pairs")
    print(json.dumps({"http_200": [r["name"] for r in ok],
                      "line_candidates": [r["name"] for r in usable]}, indent=2))


if __name__ == "__main__":
    main()
