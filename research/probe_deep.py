#!/usr/bin/env python3
"""Deep research probe: do any reachable LoL betting pages expose parseable prices?

Stage 1 (tools/probe_sources.py) established which endpoints answer at all. Several
answered HTTP 200 but with HTML, which may still embed the prices server-side or in a
hydration blob (`__NEXT_DATA__`, `__NUXT__`, JSON-LD). This script tests that, plus the
JSON APIs behind the venues that only answered on their landing page.

It never writes a pick and never touches the published pages. Output is evidence:
  research/probe_deep.json           verdicts, sizes, JSON keys found
  research/raw/<slug>.json           trimmed extract of any embedded JSON blob
  research/raw/<slug>.html           trimmed HTML (only when no JSON blob was found)

Run:  python3 research/probe_deep.py
"""
from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
from common import http_get, iso, now_utc, save_json, log  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "research")
RAW = os.path.join(OUT, "raw")
MAX_SNAPSHOT = 220_000  # bytes kept per page extract

UA = {"Accept": "application/json, text/html;q=0.9",
      "Accept-Language": "en-US,en;q=0.9"}

PAGES = [
    ("rivalry-lol", "https://www.rivalry.com/esports/league-of-legends"),
    ("draftkings-lol", "https://sportsbook.draftkings.com/leagues/esports/league-of-legends"),
    ("fanduel-lol", "https://sportsbook.fanduel.com/esports/league-of-legends"),
    ("betonline-esports", "https://www.betonline.ag/sportsbook/esports"),
    ("oddsportal-lol", "https://www.oddsportal.com/esports/league-of-legends/"),
    ("bcgame-sports", "https://bc.game/sports"),
]

# JSON endpoints behind those venues. Guessed paths are labelled "candidate" and are
# only recorded as evidence; a 404/401 is a factual result, not a failure to hide.
APIS = [
    ("odds-api.io sports", "https://api.odds-api.io/v3/sports"),
    ("odds-api.io leagues", "https://api.odds-api.io/v3/leagues?sport=esports"),
    ("odds-api.io events", "https://api.odds-api.io/v3/events?sport=esports&limit=5"),
    ("odds-api.io esports leagues", "https://api.odds-api.io/v3/leagues?sport=esports_lol"),
    ("draftkings sportscontent", "https://sportsbook-nash.draftkings.com/api/sportscontent/dkusoh/v1/sports"),
    ("draftkings leagues", "https://sportsbook-nash.draftkings.com/api/sportscontent/dkusoh/v1/leagues"),
    ("fanduel content page", "https://sportsbook.fanduel.com/api/content-managed-page?page=CUSTOM&customPageId=esports_league-of-legends"),
    ("rivalry graphql", "https://api.rivalry.com/graphql"),
    ("pinnacle lol leagues", "https://guest.api.arcadia.pinnacle.com/0.1/sports/12/leagues/9587/matchups"),
    ("polymarket clob", "https://clob.polymarket.com/markets?limit=5&tag_slug=league-of-legends"),
    ("kalshi exchange status", "https://api.elections.kalshi.com/trade-api/v2/exchange/status"),
    ("bovada lol coupon", "https://www.bovada.lv/services/sports/event/coupon/events/A/description/esports/league-of-legends"),
    ("betsson kambi listview", "https://eu-offering-api.kambicdn.com/offering/v2018/betsson/listView/esports.json"),
    ("coolbet esports", "https://www.coolbet.com/api/esports/v1/sports"),
    ("tonybet esports", "https://www.tonybet.com/api/esports/leagues"),
]

JSON_BLOB_PATTERNS = [
    ("__NEXT_DATA__", r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>'),
    ("__NUXT__", r'<script[^>]*>\s*window\.__NUXT__\s*=\s*(\{.*?\});?\s*</script>'),
    ("__APOLLO_STATE__", r'<script[^>]*>\s*window\.__APOLLO_STATE__\s*=\s*(\{.*?\});?\s*</script>'),
    ("__INITIAL_STATE__", r'<script[^>]*>\s*window\.__INITIAL_STATE__\s*=\s*(\{.*?\});?\s*</script>'),
    ("__PRELOADED_STATE__", r'<script[^>]*>\s*window\.__PRELOADED_STATE__\s*=\s*(\{.*?\});?\s*</script>'),
    ("json-ld", r'<script type="application/ld\+json"[^>]*>(.*?)</script>'),
]


def scan_odds_tokens(text: str) -> dict:
    """Count the signals that would let us derive a two-sided price."""
    low = text.lower()
    return {
        "has_decimal_word": low.count("decimal"),
        "has_odds_word": low.count("odds"),
        "has_moneyline": low.count("moneyline"),
        "has_price_word": low.count('"price"'),
        "has_american": low.count("american"),
        "has_league_of_legends": low.count("league of legends"),
        "has_teams_t1_geng": low.count("gen.g") + low.count("geng"),
        "has_teams_faker": low.count("t1"),
    }


def main() -> None:
    os.makedirs(RAW, exist_ok=True)
    evidence: list[dict] = []

    for slug, url in PAGES:
        st, body = http_get(url, headers=UA, timeout=30, retries=0)
        text = body.decode("utf-8", "replace")
        row = {"kind": "page", "name": slug, "url": url, "status": st, "bytes": len(body),
               "checked_utc": iso(now_utc()), "embedded_json": [], "tokens": scan_odds_tokens(text)}
        saved = False
        for label, pattern in JSON_BLOB_PATTERNS:
            m = re.search(pattern, text, re.S)
            if not m:
                continue
            blob = m.group(1)
            row["embedded_json"].append({"label": label, "chars": len(blob)})
            if not saved:
                path = os.path.join(RAW, f"{slug}.json")
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(blob[:MAX_SNAPSHOT])
                row["snapshot"] = os.path.relpath(path, ROOT)
                saved = True
        if not saved and st == 200 and body:
            path = os.path.join(RAW, f"{slug}.html")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text[:MAX_SNAPSHOT])
            row["snapshot"] = os.path.relpath(path, ROOT)
        evidence.append(row)
        log(f"page {slug}: {st} {len(body)}b blobs={[b['label'] for b in row['embedded_json']]}")

    for name, url in APIS:
        st, body = http_get(url, headers=UA, timeout=30, retries=0)
        text = body.decode("utf-8", "replace")
        snippet = text[:220].replace("\n", " ")
        keys: list[str] = []
        payload = None
        if text.lstrip()[:1] in "{[":
            try:
                payload = json.loads(text)
            except Exception:  # noqa: BLE001 - malformed JSON is a finding
                payload = None
        if isinstance(payload, dict):
            keys = list(payload)[:12]
        evidence.append({"kind": "api", "name": name, "url": url, "status": st,
                         "bytes": len(body), "json": payload is not None,
                         "top_level_keys": keys, "fingerprint": snippet,
                         "checked_utc": iso(now_utc())})
        log(f"api {name}: {st} json={payload is not None} {len(body)}b")

    save_json(os.path.join(OUT, "probe_deep.json"), {
        "checked_utc": iso(now_utc()),
        "note": ("Deep research probe. HTML 200 + no embedded hydration JSON means the prices are "
                 "fetched client-side by JavaScript after page load, which this pipeline cannot "
                 "consume; such a venue is recorded as unparseable instead of being scraped blindly."),
        "evidence": evidence,
    })
    print(f"deep probe: {len(evidence)} targets")


if __name__ == "__main__":
    main()
