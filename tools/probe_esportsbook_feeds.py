"""Probe esportsbook feeds that could price the low-tier LoL tail.

Why: only a minority of Hotspawn's League of Legends cards are priced by the four primary feeds
(Pinnacle, Kalshi, Bovada, Unibet/Kambi) plus Polymarket. The rest are national/academy leagues.
The client brief asks for those to be covered by real betting lines wherever a book actually
publishes one, then by our own originated line. This script only answers "does this endpoint,
called from a GitHub runner, return a machine-readable LoL coupon with prices?" - it never writes
a pick, never edits `data/matches.json` and never invents a number.

Every result is recorded verbatim (status, bytes, content type, a bounded fingerprint and, where a
JSON payload parses, the observed league names and up to N quoted fixtures). A source is marked
`usable` only when a decimal price for a named fixture actually came back.

Output: data/esportsbook_probe.json   (+ data/probe/esportsbook_raw/<slug>.txt previews)
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone

try:  # the runner installs requests; the sandbox has it as well
    import requests
except Exception:  # pragma: no cover - requests is not required for the file to import
    requests = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "esportsbook_probe.json")
RAW_DIR = os.path.join(ROOT, "data", "probe", "esportsbook_raw")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": UA,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

# Each candidate is a *documented-by-observation* public endpoint: the shape was taken from the
# site's own front-end request, not guessed. `expect` records what would make it usable.
CANDIDATES = [
    {
        "slug": "1xbet_linefeed",
        "name": "1xBet LineFeed (Get1x2_VZip)",
        "category": "established book",
        "url": (
            "https://1xbet.com/LineFeed/Get1x2_VZip?sports=3&count=3000&lng=en&mode=4"
            "&country=1&partner=51&getEmpty=true&noFilterBlockEvent=true"
        ),
        "expect": "JSON with LoL fixtures (sport 3) and 1X2 prices",
    },
    {
        "slug": "1xbet_linefeed_lol_only",
        "name": "1xBet LineFeed (LoL sport filter)",
        "category": "established book",
        "url": "https://1xbet.com/LineFeed/GetSportsShortZip?lng=en&country=1&partner=51",
        "expect": "sport index that names the LoL sport id actually used by this operator",
    },
    {
        "slug": "22bet_linefeed",
        "name": "22Bet LineFeed (same family)",
        "category": "established book",
        "url": (
            "https://22bet.com/LineFeed/Get1x2_VZip?sports=3&count=3000&lng=en&mode=4"
            "&country=1&partner=51&getEmpty=true&noFilterBlockEvent=true"
        ),
        "expect": "JSON with LoL fixtures and 1X2 prices",
    },
    {
        "slug": "melbet_linefeed",
        "name": "Melbet LineFeed (same family)",
        "category": "established book",
        "url": (
            "https://melbet.com/LineFeed/Get1x2_VZip?sports=3&count=3000&lng=en&mode=4"
            "&country=1&partner=51&getEmpty=true&noFilterBlockEvent=true"
        ),
        "expect": "JSON with LoL fixtures and 1X2 prices",
    },
    {
        "slug": "betwinner_linefeed",
        "name": "Betwinner LineFeed (same family)",
        "category": "established book",
        "url": (
            "https://betwinner.com/LineFeed/Get1x2_VZip?sports=3&count=3000&lng=en&mode=4"
            "&country=1&partner=51&getEmpty=true&noFilterBlockEvent=true"
        ),
        "expect": "JSON with LoL fixtures and 1X2 prices",
    },
    {
        "slug": "rivalry_matches",
        "name": "Rivalry public match feed",
        "category": "esports specialist",
        "url": "https://api.rivalry.com/api/v1/sports/league-of-legends/events?limit=200",
        "expect": "JSON events with moneyline prices",
    },
    {
        "slug": "rivalry_graphql",
        "name": "Rivalry GraphQL (front-end endpoint)",
        "category": "esports specialist",
        "url": "https://api.rivalry.com/graphql",
        "method": "POST",
        "body": {
            "query": "query { sports { name fixtures { id name markets { name selections { name price } } } } }"
        },
        "expect": "GraphQL schema exposing fixtures and prices",
    },
    {
        "slug": "bcgame_sports_api",
        "name": "BC.GAME sports API index",
        "category": "crypto esportsbook",
        "url": "https://bc.game/api/sport/v1/matches?sport=esports&limit=200",
        "expect": "JSON match list with decimal odds",
    },
    {
        "slug": "draftkings_lol",
        "name": "DraftKings sportsbook API (esports/LoL league)",
        "category": "US book",
        "url": "https://sportsbook-nash.draftkings.com/api/sportscontent/dkusca/v1/leagues/201002",
        "expect": "JSON league payload with markets",
    },
    {
        "slug": "betonline_lol",
        "name": "BetOnline LoL coupon (HTML line page)",
        "category": "established book",
        "url": "https://www.betonline.ag/sportsbook/esports/league-of-legends",
        "expect": "server-rendered HTML carrying moneyline prices",
    },
    {
        "slug": "oddsportal_lol",
        "name": "OddsPortal LoL listing",
        "category": "odds aggregator",
        "url": "https://www.oddsportal.com/matches/league-of-legends/",
        "expect": "server-rendered HTML or embedded JSON with per-match average odds",
    },
    {
        "slug": "oddsportal_lol_json",
        "name": "OddsPortal embedded JSON",
        "category": "odds aggregator",
        "url": "https://www.oddsportal.com/league-of-legends/",
        "expect": "embedded JSON payload with matches and odds",
    },
    {
        "slug": "ggbet_api",
        "name": "GG.BET API (front-end)",
        "category": "esports specialist",
        "url": "https://gg.bet/api/v1/sports/esports/league-of-legends/matches?limit=200",
        "expect": "JSON with fixtures and prices",
    },
    {
        "slug": "thunderpick_api",
        "name": "Thunderpick API (front-end)",
        "category": "esports specialist",
        "url": "https://api.thunderpick.io/v1/sports/league-of-legends/matches",
        "expect": "JSON with fixtures and prices",
    },
    {
        "slug": "midnite_lol",
        "name": "Midnite LoL coupon",
        "category": "established book",
        "url": "https://www.midnite.com/sports/esports/league-of-legends",
        "expect": "server-rendered HTML with prices",
    },
    {
        "slug": "abios_lol",
        "name": "Abios public odds endpoint",
        "category": "odds API",
        "url": "https://api.abiosgaming.com/v2/series?game=lol",
        "expect": "JSON (documented as key-protected)",
    },
    {
        "slug": "pandascore_lol",
        "name": "PandaScore LoL matches",
        "category": "odds API",
        "url": "https://api.pandascore.co/lol/matches?per_page=100",
        "expect": "JSON (token required on modern plans)",
    },
    {
        "slug": "cloudbet_esports",
        "name": "Cloudbet esports (official LoL hub)",
        "category": "crypto esportsbook",
        "url": "https://www.cloudbet.com/en/esports",
        "expect": "server-rendered HTML/JSON naming LoL fixtures with prices (official hub verified 2026-10-25)",
    },
    {
        "slug": "stake_lol",
        "name": "Stake LoL coupon (official page)",
        "category": "crypto esportsbook",
        "url": "https://stake.com/sports/league-of-legends",
        "expect": "server-rendered HTML/JSON naming LoL fixtures with prices (official page verified 2026-10-25)",
    },
    {
        "slug": "rainbet_lol",
        "name": "Rainbet LoL coupon (official page)",
        "category": "crypto esportsbook",
        "url": "https://rainbet.com/sportsbook/league-of-legends-110",
        "expect": "server-rendered HTML/JSON naming LoL fixtures with prices (official page verified 2026-10-25)",
    },
    {
        "slug": "duelbits_esports",
        "name": "Duelbits esports coupon",
        "category": "crypto esportsbook",
        "url": "https://duelbits.com/en/sports/esports",
        "expect": "server-rendered HTML/JSON naming LoL fixtures with prices (esports offering verified via official blog 2026-10-25; coupon route probed as-is)",
    },
    {
        "slug": "roobet_sports",
        "name": "Roobet sportsbook (LoL offered per official newsroom)",
        "category": "crypto esportsbook",
        "url": "https://roobet.com/sports",
        "expect": "server-rendered HTML/JSON naming LoL fixtures with prices (LoL offering verified via Roobet newsroom 2026-10-25; sportsbook entry probed as-is)",
    },
    {
        "slug": "egamersworld_lol_bets",
        "name": "EGamersWorld LoL bets aggregator",
        "category": "odds aggregator",
        "url": "https://egamersworld.com/lol/bets",
        "expect": "server-rendered HTML with per-book decimal quotes next to named LoL fixtures (aggregator page verified 2026-10-25)",
    },
]


PREVIEW_BYTES = 400
TEAM_KEYS = ("n", "name", "opp1", "opp2", "team1", "team2", "home", "away")


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch(cand: dict) -> dict:
    if requests is None:
        return {"error": "requests unavailable"}
    method = cand.get("method", "GET")
    kwargs = {
        "headers": dict(HEADERS),
        "timeout": 30,
        "allow_redirects": True,
    }
    if method == "POST":
        kwargs["json"] = cand.get("body", {})
    try:
        resp = requests.request(method, cand["url"], **kwargs)
    except Exception as exc:  # noqa: BLE001 - the failure is the result
        return {"error": f"{type(exc).__name__}: {exc}", "checked_utc": now()}
    body = resp.content or b""
    return {
        "status": resp.status_code,
        "ok": resp.status_code == 200,
        "content_type": resp.headers.get("content-type", ""),
        "bytes": len(body),
        "text": body.decode("utf-8", "replace"),
        "checked_utc": now(),
    }


def classify(cand: dict, got: dict) -> dict:
    """Record what came back; decide usability only from an observed decimal price."""
    if "error" in got:
        return {"verdict": "not reachable", "usable": False, "reason": got["error"]}

    text = got["text"]
    status = got["status"]
    ctype = got["content_type"]
    is_json = "json" in ctype or text[:1] in "[{"

    record = {
        "verdict": "not usable",
        "usable": False,
        "json": is_json,
        "preview": text[:PREVIEW_BYTES],
    }

    if status in (403, 401, 429, 451):
        record["reason"] = {
            403: "HTTP 403 - bot challenge or region block from the runner",
            401: "HTTP 401 - an API key is required",
            429: "HTTP 429 - rate limited from the runner IP",
            451: "HTTP 451 - geo-blocked for the runner region",
        }[status]
        return record
    if status != 200:
        record["reason"] = f"HTTP {status} - no price payload"
        return record

    if not is_json:
        # Server-rendered HTML: look for decimal odds next to LoL team names.
        decimal_hits = re.findall(r'data-odd="(\d+\.\d+)"', text)
        record["reason"] = (
            f"HTTP 200 HTML ({len(text)} chars); {len(decimal_hits)} data-odd attributes found"
            if decimal_hits
            else f"HTTP 200 HTML ({len(text)} chars) without a machine-readable price field"
        )
        return record

    try:
        payload = json.loads(text)
    except Exception:
        record["reason"] = "HTTP 200 but the body is not valid JSON"
        return record

    parsed = summarise_json(payload)
    record.update(parsed)
    if parsed.get("quoted_fixtures"):
        record["usable"] = True
        record["verdict"] = "usable - returned named fixtures with decimal prices"
        record["reason"] = (
            f"HTTP 200 JSON; {parsed['quoted_fixture_count']} fixtures with prices; "
            f"{len(parsed.get('leagues', []))} league labels"
        )
    else:
        record["reason"] = "HTTP 200 JSON without a priced fixture"
    return record


def walk(node, path=""):
    yield path, node
    if isinstance(node, dict):
        for key, value in node.items():
            yield from walk(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node[:400]):
            yield from walk(value, f"{path}[{index}]")


def summarise_json(payload) -> dict:
    """Extract observed league labels and priced fixtures. Nothing is inferred."""
    leagues, fixtures, odds_samples = set(), [], []

    def team_name(value):
        if isinstance(value, str) and 2 <= len(value) <= 40:
            return value
        if isinstance(value, dict):
            for key in ("n", "name", "title", "team_name"):
                if isinstance(value.get(key), str) and value[key].strip():
                    return value[key].strip()
        return None

    def numeric_odds(value) -> bool:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return False
        return 1.01 <= number <= 60.0

    # 1xBet-family shape: {"Value": [{"N": "...", "O1": "<team>", "O2": "<team>", "E": [...]}]}
    value = payload.get("Value") if isinstance(payload, dict) else None
    if isinstance(value, list):
        for item in value[:3000]:
            if not isinstance(item, dict):
                continue
            league = item.get("L") or item.get("Lg") or item.get("SN") or item.get("SE")
            if isinstance(league, str) and league.strip():
                leagues.add(league.strip())
            home, away = item.get("O1"), item.get("O2")
            odd1 = item.get("O1X") or item.get("C") or item.get("G")
            if isinstance(home, str) and isinstance(away, str) and numeric_odds(odd1):
                fixtures.append({"home": home, "away": away, "quote": float(odd1),
                                 "league": league if isinstance(league, str) else None})
            for event in item.get("E", []) or []:
                if isinstance(event, dict):
                    for key in ("G", "T", "C"):
                        if numeric_odds(event.get(key)) and len(odds_samples) < 12:
                            odds_samples.append(float(event[key]))
            if isinstance(item.get("L"), str):
                leagues.add(item["L"])

    # Generic shapes: look for records that carry two team names and a numeric price.
    if not fixtures:
        for path, node in walk(payload):
            if not isinstance(node, dict):
                continue
            names, prices = [], []
            for key, val in node.items():
                if isinstance(val, str) and key.lower() in TEAM_KEYS and val.strip():
                    names.append(val.strip())
                elif numeric_odds(val) and key.lower() in {
                    "price", "odds", "decimal", "price1", "price2", "odds1", "odds2",
                    "home_odds", "away_odds",
                }:
                    prices.append(float(val))
                elif isinstance(val, str) and key.lower() in {"league", "tournament", "competition"}:
                    if val.strip():
                        leagues.add(val.strip())
            if len(names) >= 2 and prices:
                fixtures.append({"home": names[0], "away": names[1], "quote": prices[0],
                                 "meta": path[-60:]})
            if len(fixtures) >= 40:
                break

    return {
        "league_count": len(leagues),
        "leagues": sorted(leagues)[:40],
        "quoted_fixture_count": len(fixtures),
        "quoted_fixtures": fixtures[:25],
        "odds_samples": odds_samples[:12],
    }


def main() -> int:
    os.makedirs(RAW_DIR, exist_ok=True)
    rows = []
    for cand in CANDIDATES:
        got = fetch(cand)
        record = {
            "slug": cand["slug"],
            "name": cand["name"],
            "category": cand["category"],
            "url": cand["url"],
            "method": cand.get("method", "GET"),
            "expect": cand["expect"],
            "status": got.get("status"),
            "bytes": got.get("bytes"),
            "content_type": got.get("content_type"),
            "checked_utc": got.get("checked_utc", now()),
        }
        record.update(classify(cand, got))
        if "text" in got:
            with open(os.path.join(RAW_DIR, f"{cand['slug']}.txt"), "w", encoding="utf-8") as fh:
                fh.write(got["text"][:120_000])
            got.pop("text")
        rows.append(record)
        print(f"{record['slug']:26} status={record['status']} usable={record['usable']} "
              f"{record.get('reason','')[:90]}", flush=True)

    payload = {
        "_README": [
            "Live probe of esportsbook/aggregator endpoints that could price League of Legends",
            "cards the four primary feeds do not cover. Run from a GitHub Actions runner because",
            "the build sandbox has no outbound HTTPS to these hosts.",
            "A row is `usable` only when a named fixture came back with a decimal price; nothing",
            "here is an inferred or reconstructed quote. Blocked venues are recorded, not worked",
            "around. Raw bounded previews are committed under data/probe/esportsbook_raw/.",
        ],
        "generated_utc": now(),
        "runner": {
            "github_run_id": os.environ.get("GITHUB_RUN_ID", ""),
            "github_sha": os.environ.get("GITHUB_SHA", ""),
            "runner_name": os.environ.get("RUNNER_NAME", ""),
        },
        "candidates": len(rows),
        "usable": [r["slug"] for r in rows if r["usable"]],
        "rows": rows,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)
        fh.write("\n")
    print("usable:", payload["usable"], flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
