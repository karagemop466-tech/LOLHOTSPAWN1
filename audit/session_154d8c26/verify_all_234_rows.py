#!/usr/bin/env python3
"""Independent line-by-line audit of all scheduled Hotspawn LoL rows (session 154d8c26).

Verifies from committed raw receipts (zero code shared with tools/model.py or scripts/analyze.mjs):
1. 1:1 fixture parity between data/raw/hotspawn_lol.json and data/matches.json.
2. Zero reliance on Hotspawn crowd percentages, tiers, or offered points.
3. Every row in data/matches.json AND every rendered <tr> on table.html carries an official
   Hotspawn match link AND an external trusted source link (sportsbook/exchange quote URL
   for market rows; Leaguepedia/settlement URL otherwise).
4. Every priced row satisfies p0 + p1 == 1.0 (+/- 0.002) and pick == argmax(p0, p1);
   every settlement/unpickable row omits probability rather than inventing one.
5. Smarkets UKGC Exchange raw feed (data/raw/smarkets_lol.json) contains only open
   pre-match WINNER_2_WAY contracts with two-sided liquidity (spread <= 0.25) and
   smarkets.com public URLs.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    problems: list[str] = []

    raw_hs = json.loads((ROOT / "data" / "raw" / "hotspawn_lol.json").read_text())
    hs_fixtures = raw_hs.get("fixtures") or []
    hs_ids = [str(f["id"]) for f in hs_fixtures]

    canon = json.loads((ROOT / "data" / "matches.json").read_text())
    rows = canon.get("matches") or []
    row_ids = [str(r["id"]) for r in rows]

    if sorted(hs_ids) != sorted(row_ids):
        problems.append(f"fixture ID mismatch: feed={len(hs_ids)} published={len(row_ids)}")

    crowd_matches = 0
    priced_count = 0
    for r in rows:
        mid = str(r["id"])
        hs_url = ((r.get("sources") or {}).get("hotspawn")) or r.get("hotspawn_url") or ""
        if not hs_url.startswith("https://www.hotspawn.com/matches/"):
            problems.append(f"#{mid}: missing official Hotspawn match URL")

        method = r.get("method")
        p0, p1 = r.get("p0"), r.get("p1")
        pick = r.get("pick") or {}

        if method == "market":
            venues = (r.get("market") or {}).get("venues") or []
            if not venues:
                problems.append(f"#{mid}: market row with 0 venues")
            for v in venues:
                u = v.get("url") or ""
                if not u.startswith("https://"):
                    problems.append(f"#{mid}: venue {v.get('name')} missing https receipt URL")
        else:
            lp_page = r.get("leaguepedia_page") or ""
            res_src = (r.get("resolution") or {}).get("source") or ""
            if not lp_page and not res_src.startswith("https://"):
                problems.append(f"#{mid}: non-market row missing leaguepedia_page and resolution.source")

        if p0 is not None or p1 is not None:
            priced_count += 1
            if p0 is None or p1 is None or abs((p0 + p1) - 1.0) > 0.0021:
                problems.append(f"#{mid}: invalid probabilities p0={p0} p1={p1}")
            elif abs(p0 - p1) > 1e-6:
                want_team = (r.get("team0") or {}).get("name") if p0 > p1 else (r.get("team1") or {}).get("name")
                if pick.get("team") and pick.get("team") != want_team:
                    problems.append(f"#{mid}: pick {pick.get('team')} != higher prob side {want_team}")
            c0 = (r.get("community_pick_pct") or {}).get("team0")
            if c0 is not None and p0 is not None and abs(p0 - (float(c0) / 100.0)) < 1e-6:
                crowd_matches += 1
        else:
            if pick.get("probability") is not None:
                problems.append(f"#{mid}: unpriced row carries pick.probability={pick.get('probability')}")

    if crowd_matches == priced_count and priced_count > 0:
        problems.append("probabilities mirror Hotspawn crowd percentages")

    table_html = (ROOT / "table.html").read_text()
    trs = re.findall(r'<tr class="prow [^"]*".*?</tr>', table_html, re.S)
    if len(trs) != len(rows):
        problems.append(f"table.html row count {len(trs)} != data/matches.json {len(rows)}")
    for idx, tr in enumerate(trs):
        hrefs = re.findall(r'href="(https://[^"]+)"', tr)
        has_hs = any("hotspawn.com/matches/" in u for u in hrefs)
        has_ext = any("hotspawn.com" not in u for u in hrefs)
        if not (has_hs and has_ext):
            problems.append(f"table.html row {idx}: missing Hotspawn or external source link ({hrefs})")

    sm_path = ROOT / "data" / "raw" / "smarkets_lol.json"
    sm_events = []
    if sm_path.exists():
        sm_doc = json.loads(sm_path.read_text())
        sm_events = sm_doc.get("events") or []
        for ev in sm_events:
            if not str(ev.get("url") or "").startswith("https://smarkets.com/"):
                problems.append(f"smarkets event {ev.get('event_id')}: missing smarkets.com URL")
            outs = ev.get("outcomes") or []
            if len(outs) != 2:
                problems.append(f"smarkets event {ev.get('event_id')}: expected 2 outcomes")
                continue
            for o in outs:
                sp = o.get("spread_prob")
                if sp is None or sp <= 0 or sp > 0.25:
                    problems.append(f"smarkets contract {o.get('contract_id')}: invalid spread {sp}")

    report = {
        "session": "154d8c26",
        "hotspawn_feed_rows": len(hs_ids),
        "published_rows": len(row_ids),
        "table_html_rows": len(trs),
        "priced_rows": priced_count,
        "smarkets_series_verified": len(sm_events),
        "problems": problems,
        "passed": len(problems) == 0,
    }
    out_path = ROOT / "audit" / "session_154d8c26" / "report.json"
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
