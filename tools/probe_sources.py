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
    """Every team name on today's Hotspawn list that can be searched for as a substring.

    Earlier versions of this probe tested a 32-name sample (8 headline + 24 low-tier names),
    which meant "no venue carries a listed team" was really "no venue carries one of 32 names".
    The whole list is searched now. Names shorter than five characters (``T1``, ``B5``, ``LYON``
    is fine but ``T1`` is not) are excluded because a two-character needle matches everything;
    the competition-name test in the same receipt covers those leagues instead.
    """
    hs = load_json(os.path.join(RAW, "hotspawn_lol.json")) or {}
    names = set()
    for f in hs.get("fixtures") or []:
        for side in ("team0", "team1"):
            name = (f.get(side) or {}).get("name")
            if name and len(str(name)) >= 5:
                names.add(str(name))
    return sorted(names)


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


def _is_short_code(token: str) -> bool:
    """A competition's own abbreviation, e.g. PRM / LCP / POP / LIT."""
    return len(token) <= 6 and token.isalnum() and token.upper() == token


def _token_match(text: str, token: str):
    """Whole-token match, case-sensitive for short codes.

    Two failure modes were observed on the 2026-10-25 runner receipts and both are fixed here:

    * a substring test made "LIT" match every "split" and "POP" every "popular" (20 false
      positives on the first receipt) - so matching is word-bounded;
    * a case-insensitive word test still matched JavaScript and CSS (`s.pop()`, `lcp:{...}`)
      - so a 3-6 character competition code is matched only in its published upper case,
      which is how Hotspawn and the venues actually write it ("PRM", "LCP", "POP").
    """
    if _is_short_code(token):
        return re.search(r"(?<![A-Za-z0-9])" + re.escape(token) + r"(?![A-Za-z0-9])", text)
    return re.search(r"(?<![A-Za-z0-9])" + re.escape(token) + r"(?![A-Za-z0-9])", text, re.I)


def competition_hits(text: str, aliases: dict[str, list[str]]) -> list[tuple[str, str, int]]:
    """(competition, matched token, index) for every competition mentioned in text."""
    if not text:
        return []
    hits = []
    for comp, toks in aliases.items():
        # Longest token first: a full league name is stronger evidence than a 3-letter code.
        for tok in sorted(toks, key=len, reverse=True):
            m = _token_match(text, tok)
            if m:
                hits.append((comp, tok, m.start()))
                break
    return sorted(hits)


def match_competitions(text: str, aliases: dict[str, list[str]]) -> list[str]:
    """Competitions from the Hotspawn list that a venue response actually mentions."""
    return sorted({comp for comp, _tok, _at in competition_hits(text, aliases)})


def competition_evidence(text: str, aliases: dict[str, list[str]],
                         limit: int = 4, width: int = 120) -> list[dict]:
    """The matched token plus the surrounding text, so a reader can judge the match.

    This is what makes "Flashscore mentions RIVALS LEAGUE" reviewable instead of a claim: the
    receipt carries the words the venue actually printed.
    """
    out = []
    flat = re.sub(r"\s+", " ", text or "")
    for comp, tok, at in competition_hits(flat, aliases)[:limit]:
        lo = max(0, at - width // 2)
        out.append({"competition": comp, "token": tok,
                    "token_kind": "code" if _is_short_code(tok) else "name",
                    "context": flat[lo:at + width].strip()})
    return out


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

    # The league list above is the authoritative "what is open", but the matchups payload is
    # what the collector actually prices from. Enumerate the leagues *there* too, with the
    # participants, so a league that exists in the matchups but not in the league list is
    # visible instead of silently missing.
    st2, matchups, err2 = get_json(PINNACLE_MATCHUPS_URL, headers=PINNACLE_KEY, retries=retries)
    doc["matchups_status"] = st2
    doc["matchups_error"] = err2
    doc["matchup_leagues"] = []
    if st2 == 200 and isinstance(matchups, list):
        per_league: Counter = Counter()
        people: dict[str, set] = {}
        for m in matchups:
            league = str(((m.get("league") or {}).get("name")) or "").strip()
            sport = str((((m.get("league") or {}).get("sport")) or {}).get("name") or "")
            if not league:
                continue
            is_lol = "league of legends" in (league + " " + sport).lower()
            if not is_lol and not match_competitions(league, aliases):
                continue
            per_league[league] += 1
            bucket = people.setdefault(league, set())
            for part in m.get("participants") or []:
                name = part.get("name")
                if name:
                    bucket.add(str(name))
        for league, n in per_league.most_common():
            doc["matchup_leagues"].append({
                "league": league,
                "matchups": n,
                "hotspawn_competitions": match_competitions(league, aliases),
                "sample_participants": sorted(people.get(league) or [])[:8],
            })
        doc["lol_matchups_total"] = sum(per_league.values())
    return doc


def fixtures_from_inventory() -> list[dict]:
    """Every fixture on today's Hotspawn list, as the pair of names a venue would print."""
    hs = load_json(os.path.join(RAW, "hotspawn_lol.json")) or {}
    out = []
    for f in hs.get("fixtures") or []:
        t0 = (f.get("team0") or {}).get("name")
        t1 = (f.get("team1") or {}).get("name")
        if t0 and t1:
            out.append({"id": str(f.get("id") or ""),
                        "competition": (f.get("competition") or "").strip(),
                        "team0": str(t0), "team1": str(t1)})
    return out


def _name_match(text: str, name: str):
    if len(name) < 5:
        # Two- and three-letter org names are unusable as substrings; require a whole word.
        return re.search(r"(?<![A-Za-z0-9])" + re.escape(name) + r"(?![A-Za-z0-9])", text, re.I)
    return re.search(re.escape(name), text, re.I)


def matched_fixtures(text: str, fixtures: list[dict], limit: int = 10) -> list[dict]:
    """Fixtures for which a response names **both** sides.

    A single team name is weak evidence: the 2026-10-25 receipts matched "DELETED" inside page
    CSS, "Arena" inside Rivalry's chrome and "Venus" inside BetOnline's bundle. A real coupon
    prints both opponents, so requiring both sides of the same fixture removes that class of
    false positive without adding any judgement about prices.
    """
    if not text:
        return []
    out = []
    for f in fixtures:
        if _name_match(text, f["team0"]) and _name_match(text, f["team1"]):
            out.append(f)
            if len(out) >= limit:
                break
    return out


def main() -> None:
    os.makedirs(PROBE_DIR, exist_ok=True)
    names = known_names()
    aliases = competition_aliases()
    fixtures = fixtures_from_inventory()
    results = []
    for name, url, kind, why in SOURCES:
        headers_note = ""
        if name == "Riot LoL Esports schedule":
            headers_note = "no api key header on purpose: records the unauthenticated response"
        item = fetch(url)
        text = item.pop("text", "") or ""
        found = [n for n in names if n.lower() in text.lower()]
        comps = match_competitions(text, aliases)
        evidence = competition_evidence(text, aliases)
        pairs = matched_fixtures(text, fixtures)
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
            "found_competitions_by_name": sorted(
                {e["competition"] for e in evidence if e["token_kind"] == "name"}),
            "found_competitions_by_code": sorted(
                {e["competition"] for e in evidence if e["token_kind"] == "code"}),
            "found_competition_evidence": evidence,
            "found_fixtures": [{"id": f["id"], "competition": f["competition"],
                                "match": f"{f['team0']} vs {f['team1']}"} for f in pairs],
            "found_fixture_count": len(pairs),
            "signals": odds_signals(text) if text else {},
            "snippet": re.sub(r"\s+", " ", text[:400]).strip() if text else "",
        }
        results.append(row)
        log(f"probe {name:32s} status={row.get('status')} bytes={row.get('bytes')} "
            f"teams={row['found_team_count']} comps={row['found_competition_count']}")

    inventory = pinnacle_league_inventory(aliases)
    payload = {
        "probed_utc": iso(now_utc()),
        # Provenance of the receipt itself: which runner, which commit, which branch. Without
        # this a reader cannot tell a scheduled runner capture from a laptop capture.
        "runner_env": {k: os.environ.get(k, "") for k in
                       ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_SHA", "GITHUB_REF_NAME",
                        "RUNNER_OS", "RUNNER_NAME")},
        "runner_note": ("Executed from a GitHub Actions runner (Linux, US egress). "
                        "Status/bytes are what the build runner actually received; a 403 from the "
                        "runner is recorded as blocked even if a browser can open the page."),
        "team_names_used": names,
        "fixtures_tested": len(fixtures),
        # The decisive row-level test: a venue that prints both sides of a fixture has a market
        # on that fixture. Single-name hits are reported but never described as coverage.
        "venues_quoting_both_sides_of_a_listed_fixture": [
            {"name": r["name"], "fixtures": r["found_fixtures"]}
            for r in results if r.get("found_fixture_count")],
        "competition_aliases": aliases,
        "pinnacle_league_inventory": inventory,
        # Split by evidence strength: a competition's full published name (or the Leaguepedia
        # page it was joined to) is strong evidence; a 3-6 letter code can also be a team name
        # ("LCP" is a Pinnacle participant) or a region label ("LCP (Asia-Pacific)" on
        # Polymarket), so code-only hits are reported separately and never counted as coverage.
        "venues_mentioning_a_hotspawn_competition": [
            {"name": r["name"],
             "found_competitions": r["found_competitions_by_name"],
             "code_only_competitions": r["found_competitions_by_code"]}
            for r in results
            if r.get("found_competitions_by_name") or r.get("found_competitions_by_code")],
        "sources": results,
    }
    save_json(os.path.join(PROBE_DIR, "sources_probe.json"), payload)
    ok = [r for r in results if r.get("status") == 200]
    usable = [r for r in ok if r["found_team_count"] >= 2 and
              (r.get("signals") or {}).get("has_decimal_pair")]
    log(f"probe summary: {len(ok)}/{len(results)} HTTP 200, {len(usable)} show team names + decimal pairs")
    matched = [r["name"] for r in results if r.get("found_competitions_by_name")]
    quoting = [r["name"] for r in results if r.get("found_fixture_count")]
    log(f"league-level: Pinnacle lists {len(inventory.get('lol_leagues') or [])} LoL league(s); "
        f"{len(matched)} venue(s) mention a Hotspawn competition by name; "
        f"{len(quoting)} venue(s) print both sides of a listed fixture")
    print(json.dumps({"venues_quoting_both_sides": quoting}, indent=2))
    print(json.dumps({"http_200": [r["name"] for r in ok],
                      "line_candidates": [r["name"] for r in usable],
                      "venues_naming_a_hotspawn_competition": matched,
                      "pinnacle_lol_leagues": inventory.get("lol_leagues")}, indent=2))


if __name__ == "__main__":
    main()
