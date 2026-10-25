#!/usr/bin/env python3
# Re-probe requested 2026-10-25 (session 2faec1ff, T1): fresh runner receipts.
"""Low-tier line-source probe (session e32a5c4b, task E2).

Question this answers: for the Hotspawn LoL matches that the featured
(market-backed) resolution cannot price -- the regional, academy and
2nd/3rd-division tail -- is there ANY reachable external bookmaker,
esportsbook, exchange or odds aggregator that publishes a real pre-match
moneyline we could use instead of (or to corroborate) our originated Elo?

Method (runner-only; the dev sandbox has no outbound HTTPS):
  1. Fetch the live Hotspawn LoL fixture list (public fixtures API) so the
     team/competition search terms are the *current* ones, not yesterday's.
  2. One honest GET per candidate venue (public URL only, no login, no
     credential, no bypass). Record HTTP status, final URL, content type,
     byte count.
  3. Search the response body for current low-tier team names and
     competition names. A venue only counts as "covering" a competition if
     at least two distinct current team names from it appear, or the
     competition name itself appears.
  4. Emit data/probe/lowtier_<date>.json with a per-venue verdict and a
     per-competition coverage matrix. Nothing here prices a match; a venue
     is only promoted to tools/collect.py after a parser + receipt exist.

Run:  python3 tools/probe_lowtier.py
"""
from __future__ import annotations

import gzip
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
PROBE_DIR = os.path.join(DATA, "probe")

UA = ("LOLHOTSPAWN1-lowtier-probe/1.0 (+https://github.com/karagemop466-tech/LOLHOTSPAWN1; "
      "public-endpoint availability check, 1 request per venue)")
HOTSPAWN_FIXTURES = ("https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/"
                     "fixtures?sport_alias=lol&status=scheduled&tenantId=1")

# (name, url, kind, why-we-care). Order = the brief's order: established LoL
# betting sites first, then esportsbooks / esports lines, then aggregators,
# exchanges, and finally results/community sources that can guide (never
# price) a pick when no line exists.
VENUES = [
    # --- controls: venues already integrated -------------------------------
    ("Pinnacle guest API (matchups)", "https://guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups",
     "established book", "control: sharp LoL moneylines (already integrated)"),
    ("Pinnacle league list", "https://guest.api.arcadia.pinnacle.com/0.1/sports/12/leagues",
     "established book", "which LoL leagues does the sharp book list at all?"),
    ("Unibet/Kambi ubse LoL feed",
     "https://eu-offering-api.kambicdn.com/offering/v2018/ubse/listView/esports/league_of_legends/all/all/matches.json?lang=en_GB&market=ZZ",
     "established book (Kambi)", "control: Kindred/Kambi JSON (already integrated); does it list ERLs?"),
    ("Bovada LoL coupon",
     "https://www.bovada.lv/services/sports/event/coupon/events/A/description/esports/league-of-legends?marketFilterId=def&preMatchOnly=true&lang=en",
     "established book", "control: US esportsbook coupon (already integrated)"),
    ("Polymarket Gamma (LoL tag)",
     "https://gamma-api.polymarket.com/events?closed=false&limit=100&tag_slug=league-of-legends",
     "prediction market", "control: CLOB series markets (already integrated)"),
    ("Kalshi KXLOLGAME",
     "https://api.elections.kalshi.com/trade-api/v2/events?series_ticker=KXLOLGAME&status=open&with_nested_markets=true&limit=100",
     "regulated exchange", "control: CFTC LoL contracts (already integrated)"),

    # --- established sportsbooks (brief step 1) ----------------------------
    ("Kambi 32Red operator (gb32)",
     "https://eu-offering-api.kambicdn.com/offering/v2018/gb32/listView/esports/league_of_legends/all/all/matches.json?lang=en_GB&market=GB",
     "established book (Kambi)", "second Kambi operator: same feed or wider ERL coupon?"),
    ("Kambi LeoVegas-group operator (lvg)",
     "https://eu-offering-api.kambicdn.com/offering/v2018/lvg/listView/esports/league_of_legends/all/all/matches.json?lang=en_GB&market=ZZ",
     "established book (Kambi)", "third Kambi operator check"),
    ("Betway esports", "https://sports.betway.com/en/sports/grp/sport/esports",
     "established book", "UK book with an esports hub"),
    ("Betsson sportsbook esports", "https://www.betsson.com/en/sportsbook/esports",
     "established book", "Nordic book; Komplettligaen is Norwegian"),
    ("NordicBet esports", "https://www.nordicbet.com/en/sportsbook/esports",
     "established book", "Nordic book (Betsson group)"),
    ("Bwin esports (Entain)", "https://sports.bwin.com/en/sports/esports-54",
     "established book", "Entain coupon; German PRM divisions are the biggest tail block"),
    ("Betano esports", "https://www.betano.com/sport/esports/league-of-legends/",
     "established book", "EU book reported to carry tier-2 LoL"),
    ("Marathonbet LoL", "https://www.marathonbet.com/en/betting/Esports/League+of+Legends+-+2777942",
     "established book", "long-tail EU coupon"),
    ("1xBet line feed (esports)", "https://1xbet.com/LineFeed/Get1x2_VZip?sports=249&count=50&mode=4&country=1&getEmpty=true",
     "established book API", "widest low-tier coupon in the market if reachable"),
    ("Melbet line feed (esports)", "https://melbet.com/LineFeed/Get1x2_VZip?sports=249&count=50&mode=4&country=1&getEmpty=true",
     "established book API", "1xBet-engine mirror; sometimes reachable when 1xBet is not"),
    ("William Hill esports", "https://sports.williamhill.com/betting/en-gb/esports",
     "established book", "UK high-street book"),
    ("888sport esports", "https://www.888sport.com/esports/",
     "established book", "Kambi-powered in several markets"),

    # --- esportsbooks / esports betting lines (brief step 2) ---------------
    ("GG.BET LoL", "https://gg.bet/en/esports/league-of-legends",
     "esportsbook", "specialist esportsbook; historically prices ERLs"),
    ("Thunderpick LoL", "https://thunderpick.io/esports/league-of-legends",
     "esportsbook", "crypto esportsbook with low-tier coupons"),
    ("Thunderpick public API", "https://thunderpick.io/api/v1/sports",
     "esportsbook API", "JSON feed check"),
    ("Rivalry LoL", "https://www.rivalry.com/esports/league-of-legends-betting",
     "esportsbook", "licensed esportsbook (PR #56 adds a parser; probed independently here)"),
    ("Rivalry API", "https://api.rivalry.com/api/v1/sport/league-of-legends",
     "esportsbook API", "JSON feed check"),
    ("Stake esports LoL", "https://stake.com/sports/esport/league-of-legends",
     "crypto esportsbook", "large crypto book"),
    ("BC.GAME esports", "https://bc.game/sports/esports/league-of-legends",
     "crypto esportsbook", "crypto book that sometimes carries regional LoL"),
    ("BetBoom LoL", "https://betboom.ru/sport/esports/league-of-legends",
     "esportsbook", "CIS book with tier-2 LoL history"),
    ("PARI esports", "https://pari.ru/sports/esports/",
     "esportsbook", "successor coupon to Parimatch CIS"),
    ("Midnite esports", "https://www.midnite.com/esports/league-of-legends",
     "esportsbook", "UKGC-licensed esports-first book"),
    ("Pixel.bet LoL", "https://pixel.bet/esports/league-of-legends",
     "esportsbook", "LeoVegas-group esports brand"),
    ("Duelbits esports", "https://duelbits.com/sportsbook/esports/league-of-legends",
     "crypto esportsbook", "crypto book with esports coupon"),
    ("Loot.bet LoL", "https://loot.bet/esports/league-of-legends",
     "esportsbook", "long-standing esportsbook; still operating?"),

    # --- odds aggregators / comparison engines -----------------------------
    ("EGamersWorld LoL matches", "https://egamersworld.com/lol/matches",
     "odds aggregator", "widest published LoL coupon incl. national divisions"),
    ("OddsPortal LoL", "https://www.oddsportal.com/esports/league-of-legends/",
     "odds aggregator", "multi-book comparison index"),
    ("Oddspedia LoL", "https://oddspedia.com/esports/league-of-legends",
     "odds aggregator", "multi-book comparison"),
    ("BetExplorer LoL", "https://www.betexplorer.com/esports/league-of-legends/",
     "odds aggregator", "multi-book comparison with league pages"),
    ("Flashscore LoL", "https://www.flashscore.com/esports/league-of-legends/",
     "odds aggregator", "scores + bookmaker odds tabs"),
    ("Sofascore esports scheduled-events API",
     "https://www.sofascore.com/api/v1/sport/esports/scheduled-events/2026-10-24",
     "odds aggregator API", "JSON schedule; per-event odds endpoints exist if listed"),
    ("bo3.gg API matches", "https://api.bo3.gg/api/v1/matches?page=1",
     "match centre API", "match centre reported to relay bookmaker quotes"),
    ("bo3.gg LoL matches", "https://bo3.gg/lol/matches",
     "match centre", "LoL match list"),
    ("Escorenews LoL", "https://escorenews.com/en/lol",
     "esports news + odds", "match pages carry book prices"),
    ("Cybersport.ru LoL matches", "https://www.cybersport.ru/match-center?disciplines=lol",
     "match centre", "CIS match centre with book odds widgets"),
    ("Strafe LoL", "https://www.strafe.com/en/league-of-legends/",
     "match centre", "esports companion app/web match pages"),

    # --- exchanges / prediction markets beyond the controls ----------------
    ("Smarkets event-types API", "https://api.smarkets.com/v3/event_types/",
     "exchange API", "public API; does an esports/LoL type exist?"),
    ("Betfair public catalogue", "https://www.betfair.com/exchange/plus/esports",
     "exchange", "largest exchange; API needs a key, web coupon checked here"),
    ("SX Bet sports API", "https://api.sx.bet/sports",
     "exchange API", "on-chain exchange public API"),

    # --- results / community sources that can guide (never price) ----------
    ("Leaguepedia Cargo (control)",
     "https://lol.fandom.com/wiki/Special:CargoExport?tables=MatchSchedule&fields=OverviewPage,Team1,Team2,Winner,DateTime_UTC&limit=5&format=json",
     "results database", "control: series results behind the Elo (already integrated)"),
    ("Liquipedia LoL portal matches", "https://liquipedia.net/leagueoflegends/Portal:Matches",
     "results database", "independent fixture/result cross-check for low tiers"),
    ("Games of Legends (gol.gg)", "https://gol.gg/esports/esports-stats/",
     "stats database", "pro-match stats; tier-1/2 only?"),
    ("Oracle's Elixir downloads", "https://oracleselixir.com/tools/downloads",
     "stats database", "pro-match CSV archive; which leagues are included?"),
    ("LoL Esports (official schedule API)",
     "https://esports-api.lolesports.com/persisted/gw/getSchedule?hl=en-US",
     "official", "official schedule cross-check (needs api-key header; 401 expected without it)"),
    ("Sheep Esports LoL", "https://www.sheepesports.com/league-of-legends",
     "esports news", "roster/news cross-check for ERL teams"),
    ("PandaScore free LoL matches", "https://api.pandascore.co/lol/matches/upcoming",
     "esports data API", "needs a token; 401 documents the paywall"),
]


def _get(url: str, timeout: int = 25) -> dict:
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/json,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip",
    })
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            raw = r.read(2_500_000)
            status, final, ctype = r.status, r.geturl(), r.headers.get("Content-Type", "")
            enc = r.headers.get("Content-Encoding", "")
        if "gzip" in (enc or ""):
            try:
                raw = gzip.decompress(raw)
            except OSError:
                pass
        text = raw.decode("utf-8", "replace")
        return {"status": status, "final_url": final, "content_type": ctype,
                "bytes": len(raw), "body": text, "error": ""}
    except urllib.error.HTTPError as e:
        try:
            body = e.read(200_000).decode("utf-8", "replace")
        except Exception:
            body = ""
        return {"status": e.code, "final_url": url, "content_type": str(e.headers.get("Content-Type", "")),
                "bytes": len(body), "body": body, "error": f"HTTP {e.code} {e.reason}"}
    except Exception as e:  # DNS, TLS, timeout, reset -- all recorded verbatim
        return {"status": 0, "final_url": url, "content_type": "", "bytes": 0,
                "body": "", "error": f"{type(e).__name__}: {e}"}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def main() -> int:
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    day = now.strftime("%Y%m%d")
    print(f"[{stamp}] low-tier probe starting")

    hs = _get(HOTSPAWN_FIXTURES, timeout=40)
    fixtures = []
    if hs["status"] == 200 and hs["body"]:
        try:
            data = json.loads(hs["body"])
            if isinstance(data, list):
                fixtures = [f for f in data if f.get("sport_alias") == "lol"]
        except json.JSONDecodeError as e:
            hs["error"] = f"JSON parse failed: {e}"
    print(f"hotspawn fixtures: status={hs['status']} lol={len(fixtures)} err={hs['error'] or '-'}")

    # search terms: competition -> set of normalised team names (len>=4 to
    # avoid 3-letter false positives like "LØS"/"T1")
    comp_teams: dict[str, set[str]] = {}
    for f in fixtures:
        comp = f.get("competition_name") or "?"
        for k in ("participants0_name", "participants1_name"):
            t = _norm(f.get(k) or "")
            if len(t) >= 4:
                comp_teams.setdefault(comp, set()).add(t)
    # fall back to the committed snapshot if the live fetch failed
    if not comp_teams:
        snap = os.path.join(DATA, "raw", "hotspawn_lol.json")
        if os.path.exists(snap):
            d = json.load(open(snap, encoding="utf-8"))
            for f in d.get("fixtures", []):
                comp = f.get("competition") or "?"
                for side in ("team0", "team1"):
                    t = _norm((f.get(side) or {}).get("name") or "")
                    if len(t) >= 4:
                        comp_teams.setdefault(comp, set()).add(t)
            print(f"fell back to committed snapshot: {len(comp_teams)} competitions")

    rows = []
    matrix: dict[str, list[str]] = {c: [] for c in comp_teams}
    for name, url, kind, why in VENUES:
        r = _get(url)
        body_norm = _norm(r["body"])
        hits_by_comp, all_teams = {}, set()
        for comp, teams in comp_teams.items():
            found = sorted(t for t in teams if t in body_norm)
            comp_hit = _norm(comp) in body_norm and len(_norm(comp)) >= 8
            if len(found) >= 2 or comp_hit:
                hits_by_comp[comp] = {"teams_found": found[:12], "competition_name_found": bool(comp_hit)}
                matrix[comp].append(name)
            all_teams.update(found)
        is_json = r["body"].lstrip()[:1] in ("{", "[")
        odds_hint = bool(re.search(r'"(price|odds|decimal|american)"\s*:', r["body"][:500_000])) if is_json else False
        if r["status"] == 200 and hits_by_comp:
            verdict = "REACHABLE + mentions current low-tier teams/competitions (manual parser review required before any use)"
        elif r["status"] == 200 and is_json:
            verdict = "reachable JSON, no current low-tier fixture found in payload"
        elif r["status"] == 200:
            verdict = "reachable web page (HTML), no current low-tier fixture text found; no public JSON price feed identified"
        elif r["status"] in (401, 403):
            verdict = "auth/geo/bot wall from the runner -- not usable without credentials we do not hold"
        elif r["status"] in (404, 410):
            verdict = "gone / no such public page"
        elif r["status"] == 0:
            verdict = "unreachable from the runner (DNS/TLS/timeout -- see error)"
        else:
            verdict = f"HTTP {r['status']} -- see error"
        rows.append({
            "venue": name, "url": url, "kind": kind, "why": why,
            "status": r["status"], "final_url": r["final_url"],
            "content_type": r["content_type"], "bytes": r["bytes"],
            "is_json": bool(is_json), "odds_like_keys": odds_hint,
            "error": r["error"],
            "competitions_matched": hits_by_comp,
            "distinct_current_teams_found": sorted(all_teams)[:40],
            "verdict": verdict,
        })
        print(f"  {r['status']:>3} {name}: comps={len(hits_by_comp)} teams={len(all_teams)} json={is_json} err={r['error'] or '-'}")

    out = {
        "generated_utc": stamp,
        "runner": "GitHub Actions ubuntu-latest, python urllib, honest User-Agent, 1 GET per venue",
        "hotspawn_inventory": {
            "source_url": HOTSPAWN_FIXTURES, "status": hs["status"],
            "lol_fixtures": len(fixtures), "error": hs["error"],
            "competitions": {c: len(t) for c, t in sorted(comp_teams.items())},
        },
        "venues_probed": len(rows),
        "venues": rows,
        "coverage_matrix": {c: v for c, v in sorted(matrix.items())},
        "reading_guide": (
            "coverage_matrix lists, per Hotspawn competition, every probed venue whose public "
            "response mentioned >=2 current teams or the competition name. An empty list means no "
            "probed venue publicly lists that competition today, so the pick must be originated "
            "(Elo) or left as a settlement -- never copied from Hotspawn crowd percentages."
        ),
    }
    os.makedirs(PROBE_DIR, exist_ok=True)
    path = os.path.join(PROBE_DIR, f"lowtier_{day}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    print(f"wrote {path}")
    covered = {c: v for c, v in matrix.items() if v}
    print(f"competitions mentioned anywhere: {len(covered)}/{len(matrix)}")
    for c, v in sorted(matrix.items()):
        print(f"  {'SOME' if v else 'NONE'} {c}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
