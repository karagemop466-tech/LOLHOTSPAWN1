#!/usr/bin/env python3
"""Probe bo3.gg's public API for LoL fixtures **and relayed bookmaker odds**.

Why this exists
---------------
bo3.gg is one of the few esports sites that answers an unauthenticated JSON API
from a datacentre IP (its HTML match centre is JavaScript-only, which is why the
HTML probe returned no prices). Reports from other projects say the API relays
bookmaker quotes per match. If that is true for LoL it would materially widen
market coverage beyond Pinnacle/Polymarket/Kalshi/Bovada, which only price the
tier-1 events.

What it does
------------
Runs a fixed list of candidate endpoints/parameter shapes, records the HTTP
status, byte count, content type and a bounded preview of the body, and writes
``data/probe/bo3.json``. It never invents a price and never writes to the
published dataset - it is evidence, not a collector. Promote it to a real
collector only after the shapes are known.

Usage:  python3 tools/probe_bo3.py
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DATA, iso, log, now_utc, save_json, http_get  # noqa: E402

BASE = "https://api.bo3.gg/api/v1"
SITE = "https://bo3.gg/api/v1"
HEADERS = {"Accept": "application/json", "Origin": "https://bo3.gg", "Referer": "https://bo3.gg/lol/matches"}

CANDIDATES = [
    # (label, url)
    ("disciplines", f"{BASE}/disciplines"),
    ("matches filter[discipline_id][eq]=3", f"{BASE}/matches?page%5Blimit%5D=3&filter%5Bdiscipline_id%5D%5Beq%5D=3"),
    ("matches filter[disciplines.in]=3", f"{BASE}/matches?page%5Blimit%5D=3&filter%5Bdisciplines.in%5D=3"),
    ("matches filter[game]=lol", f"{BASE}/matches?page%5Blimit%5D=3&filter%5Bgame%5D=lol"),
    ("matches discipline=lol", f"{BASE}/matches?page%5Blimit%5D=3&discipline=lol"),
    ("matches upcoming+start_date", f"{BASE}/matches?page%5Blimit%5D=5&sort=start_date&filter%5Bstatus%5D%5Beq%5D=upcoming"),
    # Kambi-powered book: the bare listView URL answers 400, so try the full public query shape.
    ("Kambi/Unibet esports (full params)",
     "https://eu-offering-api.kambicdn.com/offering/v2018/ubus/listView/esports.json"
     "?lang=en_GB&market=GB&client_id=2&channel_id=1&ncid=1&useCombined=true"),
    ("Kambi/Unibet LoL terms",
     "https://eu-offering-api.kambicdn.com/offering/v2018/ubus/group.json?lang=en_GB&market=GB&client_id=2&channel_id=1&ncid=1"),
    # Betfair public (read-only) endpoints need no key for the market list.
    ("Betfair sports list", "https://sports-api.betfair.com/exchange/v1.0/sports"),
    # Betano: Kaizen-powered, public JSON on the .com host
    ("Betano esports tree", "https://www.betano.com/api/sporttree/esports"),
    ("Betano LoL tree", "https://www.betano.com/api/sporttree/league-of-legends"),
    ("matches baseline (all games)", f"{BASE}/matches?page%5Blimit%5D=3&page%5Boffset%5D=0"),
    ("matches filter[disciplines][eq]=3", f"{BASE}/matches?page%5Blimit%5D=5&filter%5Bdisciplines%5D%5Beq%5D=3"),
    ("matches filter[discipline_id]=3", f"{BASE}/matches?page%5Blimit%5D=5&filter%5Bdiscipline_id%5D=3"),
    ("matches discipline_id=3", f"{BASE}/matches?page%5Blimit%5D=5&discipline_id=3"),
    ("matches discipline_id=3 upcoming", f"{BASE}/matches?page%5Blimit%5D=5&discipline_id=3&filter%5Bstatus%5D%5Beq%5D=upcoming"),
    ("matches sort=-start_date", f"{BASE}/matches?page%5Blimit%5D=5&sort=-start_date"),
    ("matches site origin", f"{SITE}/matches?page%5Blimit%5D=3"),
    ("tournaments (lol)", f"{BASE}/tournaments?page%5Blimit%5D=3&filter%5Bdisciplines%5D%5Beq%5D=3"),
]

PER_MATCH = [
    ("match_odds", f"{BASE}/match_odds?filter%5Bmatches%5D%5Beq%5D={{id}}"),
    ("odds", f"{BASE}/odds?filter%5Bmatches%5D%5Beq%5D={{id}}"),
    ("bets", f"{BASE}/bets?filter%5Bmatches%5D%5Beq%5D={{id}}"),
    ("match detail", f"{BASE}/matches/{{id}}"),
    ("match with odds include", f"{BASE}/matches/{{id}}?include=odds"),
]


def preview(raw: bytes) -> tuple[str, list[str]]:
    """Return (content-type guess, bounded text preview)."""
    text = raw.decode("utf-8", "replace")
    try:
        doc = json.loads(text)
        if isinstance(doc, dict):
            keys = sorted(doc.keys())
            return "json", f"keys={keys} preview={json.dumps(doc)[:1800]}"
        if isinstance(doc, list):
            head = doc[0] if doc else None
            keys = sorted(head.keys()) if isinstance(head, dict) else []
            return "json", f"list[{len(doc)}] keys={keys} preview={json.dumps(doc[:2])[:1800]}"
    except Exception:  # noqa: BLE001 - not JSON, that is the finding
        return "html/text", text[:600].replace("\n", " ")
    return "other", text[:300]


def main() -> None:
    os.makedirs(os.path.join(DATA, "probe"), exist_ok=True)
    out = {"generated_utc": iso(now_utc()), "base": BASE, "probes": [], "match_detail": []}
    first_id = None
    for label, url in CANDIDATES:
        st, body = http_get(url, headers=HEADERS, timeout=25, retries=0)
        kind, text = preview(body)
        out["probes"].append({"label": label, "url": url, "status": st, "bytes": len(body),
                              "kind": kind, "body": text})
        log(f"probe: {label} -> {st} ({len(body)} B, {kind})")
        if first_id is None and st == 200 and kind == "json":
            try:
                doc = json.loads(body.decode("utf-8", "replace"))
                results = doc.get("results") if isinstance(doc, dict) else doc
                if results:
                    first_id = (results[0].get("id") or results[0].get("match_id"))
            except Exception:  # noqa: BLE001
                first_id = None

    if first_id:
        for label, tpl in PER_MATCH:
            url = tpl.format(id=first_id)
            st, body = http_get(url, headers=HEADERS, timeout=25, retries=0)
            kind, text = preview(body)
            out["match_detail"].append({"label": label, "match_id": first_id, "url": url,
                                        "status": st, "bytes": len(body), "kind": kind, "body": text})
            log(f"probe: {label} match {first_id} -> {st} ({len(body)} B, {kind})")
    else:
        out["match_detail"].append({"note": "no match id parsed from the list probes"})

    save_json(os.path.join(DATA, "probe", "bo3.json"), out)
    log("bo3 probe: wrote data/probe/bo3.json")


if __name__ == "__main__":
    main()
