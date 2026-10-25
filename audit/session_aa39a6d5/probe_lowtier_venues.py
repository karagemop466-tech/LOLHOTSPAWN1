#!/usr/bin/env python3
"""Session aa39a6d5 (U2): can any *additional* venue price the Hotspawn low-tier long tail?

Prior probes (tools/probe_lowtier.py, tools/probe_esportsbook_feeds.py, 2026-10-23/24)
established with runner-side evidence that the books we already poll (Pinnacle, Kalshi,
Bovada, Unibet/Kambi, Polymarket) plus 40+ other venues stop at international tier: 229 of
the 241 Hotspawn LoL cards sit in competitions nobody prices.

This probe asks the only question that decides whether a venue is worth integrating:

    Of the fixtures we currently price WITHOUT a market (method model/provisional),
    how many would this venue price, from a plain unauthenticated GET on a GitHub
    Actions runner, right now?

Method (single request per candidate; no auth, no session, no challenge-solving):
  1. pull the live Hotspawn LoL inventory from the public fixtures API;
  2. load the committed data/matches.json for each fixture's current method;
  3. for each candidate endpoint, record HTTP status / content type / size, extract every
     team-name-like string (JSON walk or HTML text), and join pairs against the live
     inventory using the same tolerant normalisation the pipeline uses;
  4. write every verdict, including the failures, to probe_results.json next to this file.

Run by .github/workflows/aa39a6d5-probe.yml on this session's branch only; the sandbox
has no outbound HTTPS to any of these hosts.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(HERE, "probe_results.json")
RAW = os.path.join(HERE, "raw")
os.makedirs(RAW, exist_ok=True)

HOTSPAWN = (
    "https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures"
    "?sport_alias=lol&status=scheduled&tenantId=1"
)

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/129.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept": "application/json,text/html;q=0.8,*/*;q=0.5"}

# name, url, note on why this candidate is worth one more dated attempt
CANDIDATES = [
    ("Rivalry REST events",
     "https://api.rivalry.com/api/v1/sports/league-of-legends/events?limit=200",
     "PR #56 built a Rivalry venue on this host; the 2026-10-24 probe hit Cloudflare 530 "
     "(tunnel down, retryable). Retest decides if the endpoint is real."),
    ("Rivalry GraphQL",
     "https://api.rivalry.com/graphql",
     "Rivalry's web client is GraphQL-driven; a minimal introspection-free query "
     "(sports list) tests whether the API is publicly readable at all."),
    ("GG.BET API matches",
     "https://gg.bet/api/v1/sports/esports/league-of-legends/matches?limit=200",
     "Review consensus (Oct 2026) calls GG.BET the deepest low-tier LoL book "
     "(academy / Challengers coverage). The guessed JSON path was probed once."),
    ("GG.BET LoL page",
     "https://gg.bet/en/esports/league-of-legends",
     "Server-rendered? If prices are in the HTML the team-name join will find them."),
    ("Thunderpick API sports",
     "https://thunderpick.io/api/v1/sports",
     "Thunderpick lists PRM (Prime League) coverage; our 2nd/3rd-division PRM cards "
     "are the single biggest unpriced block (98 cards)."),
    ("Thunderpick API LoL matches",
     "https://api.thunderpick.io/v1/sports/league-of-legends/matches",
     "Direct LoL match list on their api host - the shape their front-end consumed in 2024."),
    ("Midnite LoL page",
     "https://www.midnite.com/esports/league-of-legends",
     "UK esports-first book, prices NLC-level British/Nordic LoL - adjacent to our "
     "Komplettligaen / Icelandic tail."),
    ("bo3.gg API matches (discipline=lol)",
     "https://api.bo3.gg/api/v1/matches?page=1&discipline=lol",
     "The 2026-10-23 research found every filter shape ignored. One dated retest "
     "with the documented discipline parameter."),
    ("bo3.gg API matches (game=lol)",
     "https://api.bo3.gg/api/v1/matches?page=1&game=lol",
     "Alternate filter spelling, same question."),
    ("Esports Insider LoL odds index",
     "https://esportsinsider.com/betting-odds/lol",
     "Server-rendered odds comparison (Bet365/Betway/GG.bet/Stake prices in HTML); "
     "coverage depth into ERLs is the open question."),
    ("tips.gg LoL matches",
     "https://tips.gg/lol/matches/",
     "Community prediction site with unusually deep low-tier coverage - recorded as "
     "corroboration evidence only; its model percentages are NOT a bookmaker line and "
     "would never be priced from."),
    ("Shuffle esports",
     "https://shuffle.com/sports/esports",
     "Crypto esportsbook listed with LoL coverage; one GET for the record."),
    ("Vave LoL",
     "https://vave.com/sports/esports/league-of-legends",
     "Appears in EGamersWorld's Worlds odds comparison (Oct 2026); one GET for the record."),
    ("Rainbet esports",
     "https://rainbet.com/sports/esports",
     "Same - appears in the EGamersWorld comparison with live LoL prices."),
    ("gol.gg league stats index",
     "https://gol.gg/esports/esports-stats/",
     "Not a book: community results/stat depth per league. Checks whether our biggest "
     "unpriced competitions exist there at all (future model-enrichment evidence)."),
]

STOPWORDS = {"esports", "esport", "gaming", "team", "club", "academy2"}


def norm(name: str) -> str:
    s = unicodedata.normalize("NFKD", str(name or ""))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = re.sub(r"[\s\-_\.'’/]+", "", s)
    s = re.sub(r"[^a-z0-9]", "", s)
    for tail in ("esports", "esport", "gaming"):
        if s.endswith(tail) and len(s) > len(tail) + 2:
            s = s[: -len(tail)]
    return s


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_inventory() -> dict:
    r = requests.get(HOTSPAWN, headers=HEADERS, timeout=60)
    r.raise_for_status()
    doc = r.json()
    fixtures = doc if isinstance(doc, list) else (doc.get("data") or doc.get("fixtures") or [])
    pairs: dict[tuple[str, str], dict] = {}
    for f in fixtures:
        if not isinstance(f, dict) or f.get("sport_alias") not in (None, "lol"):
            continue
        # live feed shape (tools/collect.py): participants0_name / participants1_name
        names = [f.get("participants0_name"), f.get("participants1_name")]
        if not all(names):
            teams = f.get("participants") or f.get("teams") or []
            names = [t.get("name") for t in teams if isinstance(t, dict)]
        if len(names) < 2 or not names[0] or not names[1]:
            title = f.get("name") or ""
            if " vs " in title:
                names = [s.strip() for s in title.split(" vs ", 1)]
        if len(names) >= 2 and names[0] and names[1]:
            pairs[tuple(sorted((norm(names[0]), norm(names[1]))))] = {
                "fixture_id": str(f.get("id")),
                "teams": [names[0], names[1]],
                "competition": f.get("competition_name") or f.get("competition"),
            }
    with open(os.path.join(RAW, "hotspawn_inventory.json"), "w", encoding="utf-8") as fh:
        json.dump({"fetched_utc": now_iso(), "source_url": HOTSPAWN,
                   "pairs_extracted": len(pairs)}, fh)
    return pairs


def current_methods() -> dict[str, str]:
    path = os.path.join(ROOT, "data", "matches.json")
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except Exception:
        return {}
    return {str(m.get("id")): m.get("method") for m in doc.get("matches", [])}


def strings_from_json(obj, acc: list[str], depth: int = 0) -> None:
    if depth > 9 or len(acc) > 6000:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str) and any(t in k.lower() for t in ("name", "title", "team", "participant")):
                acc.append(v)
            strings_from_json(v, acc, depth + 1)
    elif isinstance(obj, list):
        for item in obj[:400]:
            strings_from_json(item, acc, depth + 1)


DECIMAL = re.compile(r"\b(?:1\.\d{2}|[2-9]\.\d{2}|\d{2}\.\d{2})\b")


def probe(name: str, url: str, note: str, pairs: dict, methods: dict) -> dict:
    row: dict = {"venue": name, "url": url, "note": note, "checked_utc": now_iso()}
    try:
        if name.endswith("GraphQL"):
            resp = requests.post(url, headers={**HEADERS, "Content-Type": "application/json"},
                                 json={"query": "{ sports { name slug } }"}, timeout=45)
        else:
            resp = requests.get(url, headers=HEADERS, timeout=45)
        row["http_status"] = resp.status_code
        row["content_type"] = resp.headers.get("content-type", "")
        body = resp.text or ""
        row["bytes"] = len(body)
        slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
        with open(os.path.join(RAW, f"{slug}.txt"), "w", encoding="utf-8") as fh:
            fh.write(body[:300000])
        names: list[str] = []
        try:
            strings_from_json(resp.json(), names)
            row["json"] = True
        except Exception:
            row["json"] = False
            text = re.sub(r"<[^>]+>", " ", body)
            names = [text]
        haystack = " | ".join(names)
        hay_norm = {norm(n) for n in names if n and len(n) <= 60}
        row["decimal_like_numbers"] = len(set(DECIMAL.findall(body)))
        hits = []
        for (a, b), info in pairs.items():
            in_json = a in hay_norm and b in hay_norm
            in_text = a in norm(haystack) and b in norm(haystack)
            if in_json or (not row["json"] and in_text):
                hits.append({**info, "current_method": methods.get(info["fixture_id"])})
        row["inventory_pairs_found"] = len(hits)
        row["would_newly_price"] = sum(
            1 for h in hits if h.get("current_method") in ("model", "provisional", None))
        row["hits"] = hits[:25]
        row["sample_team_strings"] = [n for n in names if n and len(n) <= 60][:40]
    except Exception as exc:  # never let one venue kill the probe
        row["error"] = f"{type(exc).__name__}: {exc}"[:240]
    return row


def main() -> int:
    started = now_iso()
    try:
        pairs = fetch_inventory()
    except Exception as exc:
        print(f"inventory fetch failed: {exc}")
        pairs = {}
    methods = current_methods()
    unpriced = sum(1 for info in pairs.values()
                   if methods.get(info["fixture_id"]) in ("model", "provisional", None))
    doc = {
        "probe": "session aa39a6d5 U2 - additional low-tier LoL line venues",
        "started_utc": started,
        "inventory_pairs": len(pairs),
        "inventory_pairs_currently_without_market_price": unpriced,
        "methods_snapshot_from": "data/matches.json committed on this branch",
        "question": "would_newly_price > 0 from one unauthenticated GET = integrate; "
                    "anything else is documented, not used",
        "rows": [],
    }
    for name, url, note in CANDIDATES:
        t0 = time.time()
        row = probe(name, url, note, pairs, methods)
        row["seconds"] = round(time.time() - t0, 2)
        doc["rows"].append(row)
        print(f"{name}: status={row.get('http_status')} json={row.get('json')} "
              f"pairs={row.get('inventory_pairs_found')} "
              f"would_newly_price={row.get('would_newly_price')} "
              f"err={row.get('error') or ''}")
        time.sleep(2)  # polite, and keeps us far from any rate limit
    doc["finished_utc"] = now_iso()
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
