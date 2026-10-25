#!/usr/bin/env python3
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
from collections import Counter
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DATA, RAW, ROOT, get_json, iso, load_json, log, now_utc, save_json  # noqa: E402

# Pinnacle's public guest API is the one sharp book the runner can read without a key.
# The league list answers a question the row-level probe cannot: does this book open the
# *competition* at all, or only the international event? Same key the collector uses.
try:  # single source of truth for the guest key
    from collect import PINNACLE_KEY  # noqa: E402
except Exception:  # pragma: no cover - probe still runs, the endpoint then returns 401
    PINNACLE_KEY = {}
PINNACLE_LEAGUES_URL = "https://guest.api.arcadia.pinnacle.com/0.1/sports/12/leagues"
PINNACLE_MATCHUPS_URL = "https://guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups"

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

    # --- added 2026-10-25 (session 1773543b) ---------------------------------
    # Five more operators on the Kambi platform. collect.py already reads ubse/paf; the
    # others share the same CDN path, so a second brand can only add evidence, never a
    # duplicate price. A 200 with zero LoL events is recorded as zero, not as coverage.
    ("Kambi leovegas LoL",
     "https://eu-offering-api.kambicdn.com/offering/v2018/leovegas/listView/esports/league_of_legends/all/all/matches.json?lang=en_GB&market=ZZ",
     "established book (Kambi)", "brand-level LoL coupon, incl. tier-2?"),
    ("Kambi nordicbet LoL",
     "https://eu-offering-api.kambicdn.com/offering/v2018/nordicbet/listView/esports/league_of_legends/all/all/matches.json?lang=en_GB&market=ZZ",
     "established book (Kambi)", "brand-level LoL coupon, incl. tier-2?"),
    ("Kambi coolbet LoL",
     "https://eu-offering-api.kambicdn.com/offering/v2018/coolbet/listView/esports/league_of_legends/all/all/matches.json?lang=en_GB&market=ZZ",
     "established book (Kambi)", "brand-level LoL coupon, incl. tier-2?"),
    ("Kambi 888sport LoL",
     "https://eu-offering-api.kambicdn.com/offering/v2018/888sport/listView/esports/league_of_legends/all/all/matches.json?lang=en_GB&market=ZZ",
     "established book (Kambi)", "brand-level LoL coupon, incl. tier-2?"),
    ("Kambi paf LoL",
     "https://eu-offering-api.kambicdn.com/offering/v2018/paf/listView/esports/league_of_legends/all/all/matches.json?lang=en_GB&market=ZZ",
     "established book (Kambi)", "control: second operator on the same CDN"),
    # Aggregators whose LoL board can be read as text even when the runner is blocked elsewhere.
    ("bo3.gg LoL today", "https://bo3.gg/lol/matches/current", "odds aggregator",
     "which tiers carry a price on today's board"),
    ("bo3.gg Worlds 2026 tournament", "https://bo3.gg/lol/tournaments/worlds-2026",
     "odds aggregator", "does the tournament page price the same ties"),
    # Documented esports odds APIs. No key is configured for this repository, so an
    # unauthenticated call is the honest test: a 401 is recorded as key-gated, never as a price.
    ("odds-api.io sports list", "https://api.odds-api.io/v3/sports", "odds API",
     "public sports list - does it carry esports at all?"),
    ("odds-api.io esports events (key required)",
     "https://api.odds-api.io/v3/events?sport=esports", "odds API",
     "documented key-gated aggregate feed"),
    ("PandaScore LoL (token required)", "https://api.pandascore.co/lol/matches?per_page=1",
     "esports data API", "documented token-gated API"),
    ("Abios series (key required)", "https://api.abiosgaming.com/v2/series",
     "esports data API", "documented key-gated API"),

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


def competition_aliases() -> dict[str, list[str]]:
    """Alias tokens per competition on today's Hotspawn list.

    Two sources only, both recorded in the repository:

    * the Hotspawn competition name itself, with the season/year stripped;
    * the Leaguepedia page the model already joined that competition to (matches.json
      ``leaguepedia_page``), plus its parent without a division suffix.

    So an alias such as "Prime League" is not a guess: it is the page the dataset itself
    resolved "PRM 3rd Division 26-27 Fall" to. The aliases exist only to ask a venue
    "do you mention this competition"; they never price anything.
    """
    hs = load_json(os.path.join(RAW, "hotspawn_lol.json")) or {}
    comps = sorted({(f.get("competition") or "").strip()
                    for f in (hs.get("fixtures") or []) if (f.get("competition") or "").strip()})
    page_by_comp: dict[str, set] = {}
    for m in (load_json(os.path.join(DATA, "matches.json")) or {}).get("matches") or []:
        page = (m.get("leaguepedia_page") or "").strip()
        if page and m.get("competition"):
            page_by_comp.setdefault(m["competition"], set()).add(page.split("/")[0])
    out: dict[str, list[str]] = {}
    for comp in comps:
        toks = {comp}
        base = re.sub(r"\b(?:19|20)\d{2}\b|\b\d{2}-\d{2}\b", " ", comp)
        base = re.sub(r"\s+", " ", base).strip(" -:")
        if len(base) >= 4:
            toks.add(base)
        for page in page_by_comp.get(comp) or ():
            toks.add(page)
            parent = re.sub(r"\s+\d(?:st|nd|rd|th)\s+Division$", "", page)
            if len(parent) >= 4:
                toks.add(parent)
            # Leaguepedia writes the World Championship as "2026 Season World Championship";
            # venues write "League of Legends - World Championship". Drop the season prefix so
            # the two names can be compared without inventing a synonym.
            stripped = re.sub(r"^(?:19|20)\d{2}\s+Season\s+", "", page)
            if len(stripped) >= 4:
                toks.add(stripped)
        # The competition's own short code when the name starts with one ("PRM 3rd Division",
        # "LCP 2027 Promotion"): the first token as Hotspawn publishes it, not an invention.
        first = comp.split()[0] if comp.split() else ""
        if 3 <= len(first) <= 7 and first.isalnum() and first.upper() == first:
            toks.add(first)
        out[comp] = sorted({t for t in toks if len(t) >= 4 or t.isalnum() and len(t) >= 3})
    return out


def match_competitions(text: str, aliases: dict[str, list[str]]) -> list[str]:
    """Competitions from the Hotspawn list whose name (or recorded alias) appears in text."""
    low = (text or "").lower()
    if not low:
        return []
    return sorted(comp for comp, toks in aliases.items()
                  if any(tok.lower() in low for tok in toks))


def pinnacle_league_inventory(aliases: dict[str, list[str]], retries: int = 2) -> dict:
    """Does the sharp book open the *competition*, or only the international event?

    Reads Pinnacle's public esports league list and records every League of Legends league
    it contains, with its matchup count. Nothing is inferred: a league absent from the
    response is reported as absent.
    """
    st, data, err = get_json(PINNACLE_LEAGUES_URL, headers=PINNACLE_KEY, retries=retries)
    doc = {"url": PINNACLE_LEAGUES_URL, "checked_utc": iso(now_utc()), "status": st,
           "error": err, "esports_leagues": None, "lol_leagues": [],
           "lol_competitions_listed": [], "hotspawn_competitions_not_listed": []}
    if st != 200 or not isinstance(data, list):
        return doc
    doc["esports_leagues"] = len(data)
    ct = Counter()
    for item in data:
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        ct[name] += 1
    lol = {name: int(n) for name, n in ct.items() if "league of legends" in name.lower()}
    doc["lol_leagues"] = [{"league": name, "matchup_count": n} for name, n in
                          sorted(lol.items(), key=lambda kv: -kv[1])]
    listed = sorted({comp for name in lol for comp in match_competitions(name, aliases)})
    doc["lol_competitions_listed"] = listed
    doc["hotspawn_competitions_not_listed"] = sorted(set(aliases) - set(listed))
    return doc


def main() -> None:
    os.makedirs(PROBE_DIR, exist_ok=True)
    names = known_names()
    aliases = competition_aliases()
    results = []
    for name, url, kind, why in SOURCES:
        headers_note = ""
        if name == "Riot LoL Esports schedule":
            headers_note = "no api key header on purpose: records the unauthenticated response"
        item = fetch(url)
        text = item.pop("text", "") or ""
        found = [n for n in names if n.lower() in text.lower()]
        comps = match_competitions(text, aliases)
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
            "found_competitions": comps,
            "found_competition_count": len(comps),
            "signals": odds_signals(text) if text else {},
            "snippet": re.sub(r"\s+", " ", text[:400]).strip() if text else "",
        }
        results.append(row)
        log(f"probe {name:32s} status={row.get('status')} bytes={row.get('bytes')} "
            f"teams={row['found_team_count']} comps={row['found_competition_count']}")

    inventory = pinnacle_league_inventory(aliases)
    payload = {
        "probed_utc": iso(now_utc()),
        "runner_note": ("Executed from a GitHub Actions runner (Linux, US egress). "
                        "Status/bytes are what the build runner actually received; a 403 from the "
                        "runner is recorded as blocked even if a browser can open the page."),
        "team_names_used": names,
        "competition_aliases": aliases,
        "pinnacle_league_inventory": inventory,
        "venues_mentioning_a_hotspawn_competition": [
            {"name": r["name"], "found_competitions": r["found_competitions"]}
            for r in results if r.get("found_competition_count")],
        "sources": results,
    }
    save_json(os.path.join(PROBE_DIR, "sources_probe.json"), payload)
    ok = [r for r in results if r.get("status") == 200]
    usable = [r for r in ok if r["found_team_count"] >= 2 and
              (r.get("signals") or {}).get("has_decimal_pair")]
    log(f"probe summary: {len(ok)}/{len(results)} HTTP 200, {len(usable)} show team names + decimal pairs")
    matched = [r["name"] for r in results if r.get("found_competition_count")]
    log(f"league-level: Pinnacle lists {len(inventory.get('lol_leagues') or [])} LoL league(s); "
        f"{len(matched)} venue(s) mention a Hotspawn competition by name")
    print(json.dumps({"http_200": [r["name"] for r in ok],
                      "line_candidates": [r["name"] for r in usable],
                      "venues_naming_a_hotspawn_competition": matched,
                      "pinnacle_lol_leagues": inventory.get("lol_leagues")}, indent=2))


if __name__ == "__main__":
    main()
