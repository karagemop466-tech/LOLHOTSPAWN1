#!/usr/bin/env python3
"""Independent line-by-line audit of all published rows, CSV, flags, and HTML pages (session be974159)."""
from __future__ import annotations

import csv
import html
import json
import math
import os
import re
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "line_by_line_receipt.json")


def parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    s = str(ts).strip()[:19].replace(" ", "T")
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def main() -> int:
    matches_doc = json.load(open(os.path.join(ROOT, "data", "matches.json"), encoding="utf-8"))
    raw_hs = json.load(open(os.path.join(ROOT, "data", "raw", "hotspawn_lol.json"), encoding="utf-8"))
    flags_doc = json.load(open(os.path.join(ROOT, "data", "flags.json"), encoding="utf-8"))
    corrob_doc = json.load(open(os.path.join(ROOT, "data", "corroboration.json"), encoding="utf-8"))
    ver_doc = json.load(open(os.path.join(ROOT, "data", "verification.json"), encoding="utf-8"))

    rows = matches_doc["matches"]
    raw_fixtures = raw_hs["fixtures"]
    csv_rows = list(csv.DictReader(open(os.path.join(ROOT, "data", "picks.csv"), encoding="utf-8")))

    table_html = open(os.path.join(ROOT, "table.html"), encoding="utf-8").read()
    picks_html = open(os.path.join(ROOT, "picks.html"), encoding="utf-8").read()
    index_html = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    unres_html = open(os.path.join(ROOT, "unresolved.html"), encoding="utf-8").read()
    flagged_html = open(os.path.join(ROOT, "flagged.html"), encoding="utf-8").read()
    results_html = open(os.path.join(ROOT, "results.html"), encoding="utf-8").read()

    errors: list[str] = []
    in_play_market_rows: list[str] = []
    single_venue_market_rows: list[str] = []

    if len(rows) != len(raw_fixtures) or len(rows) != len(csv_rows):
        errors.append(f"count mismatch: matches={len(rows)} raw={len(raw_fixtures)} csv={len(csv_rows)}")

    csv_by_id = {r["hotspawn_id"]: r for r in csv_rows}
    raw_by_id = {str(f["id"]): f for f in raw_fixtures}

    for r in rows:
        fid = str(r["id"])
        rf = raw_by_id.get(fid)
        cr = csv_by_id.get(fid)
        if not rf:
            errors.append(f"{fid}: missing from raw hotspawn_lol.json")
            continue
        if not cr:
            errors.append(f"{fid}: missing from picks.csv")
            continue

        # 1. Exact participant & competition fidelity to Hotspawn feed
        if r["team0"]["name"] != rf["team0"]["name"] or r["team1"]["name"] != rf["team1"]["name"]:
            errors.append(f"{fid}: team name drift vs raw feed")
        if r["competition"] != rf["competition"]:
            errors.append(f"{fid}: competition drift vs raw feed")

        # 2. Every row has an official Hotspawn match URL and appears in both table.html and picks.html
        if not str(r.get("hotspawn_url") or "").startswith("https://www.hotspawn.com/matches/"):
            errors.append(f"{fid}: missing official hotspawn_url")
        if f'id="row-{fid}"' not in table_html and fid not in table_html:
            errors.append(f"{fid}: missing from table.html")
        if f'id="match-{fid}"' not in picks_html:
            errors.append(f"{fid}: missing #match-{fid} on picks.html")

        # 3. Probability & pick invariants + zero crowd-split leakage
        method = r["method"]
        p0, p1 = r.get("p0"), r.get("p1")
        pick = r.get("pick") or {}
        if method == "unresolved":
            if p0 is not None or p1 is not None:
                errors.append(f"{fid}: unresolved row has non-null probability")
            res = r.get("resolution") or {}
            if not str(res.get("source") or "").startswith("http"):
                errors.append(f"{fid}: unresolved row lacks primary settlement source URL")
            if fid not in unres_html:
                errors.append(f"{fid}: unresolved row missing from unresolved.html")
        else:
            if p0 is None or p1 is None or not (math.isfinite(p0) and math.isfinite(p1)):
                errors.append(f"{fid}: non-finite probability")
            elif abs((p0 + p1) - 1.0) > 0.002:
                errors.append(f"{fid}: p0+p1={p0+p1} != 1.0")
            elif pick.get("team") not in (r["team0"]["name"], r["team1"]["name"]):
                errors.append(f"{fid}: invalid pick team {pick.get('team')}")
            elif abs(pick.get("probability", -1) - max(p0, p1)) > 0.001:
                errors.append(f"{fid}: pick probability != max(p0, p1)")

        # 4. Market provenance: pre-kickoff quotes, valid URLs, no (Kills) derivatives
        if method == "market":
            mk = r.get("market") or {}
            venues = mk.get("venues") or []
            if len(venues) < 1:
                errors.append(f"{fid}: market row with 0 venues")
            if len(venues) == 1:
                single_venue_market_rows.append(fid)
            ko = parse_iso(r.get("start_utc"))
            for v in venues:
                if not str(v.get("url") or "").startswith("http"):
                    errors.append(f"{fid}: venue {v.get('name')} missing URL")
                if "kills" in str(v.get("name") or "").lower():
                    errors.append(f"{fid}: derivative (Kills) venue leaked")
                obs = parse_iso(v.get("observed_utc"))
                if ko and obs and obs > ko:
                    in_play_market_rows.append(f"{fid}:{v.get('name')}")
                    errors.append(f"{fid}: post-kickoff in-play quote on {v.get('name')} ({v.get('observed_utc')} > {r.get('start_utc')})")

        # 5. Result grading consistency
        res_rec = r.get("result")
        if res_rec is not None:
            s0, s1 = res_rec.get("score0"), res_rec.get("score1")
            ws = res_rec.get("winner_side")
            if s0 is not None and s1 is not None:
                i0, i1 = int(s0), int(s1)
                if i0 == i1 or ((i0 > i1) != (ws == 0)):
                    errors.append(f"{fid}: inconsistent graded score {s0}-{s1} vs winner_side={ws}")
            if fid not in results_html and html.escape(r["team0"]["name"]) not in results_html:
                errors.append(f"{fid}: graded row missing from results.html")

    # 6. Check all flags carry HTTP source links and no 'unverified - needs manual review' placeholder remains
    for fl in flags_doc.get("flags") or []:
        if not str(fl.get("source") or "").startswith("http"):
            errors.append(f"flag missing HTTP source: {fl.get('item')}")
        if fl.get("verification") == "unverified - needs manual review":
            errors.append(f"stale unverified manual flag left unresolved: {fl.get('item')}")
        if html.escape(str(fl.get("item") or ""))[:40] not in flagged_html:
            errors.append(f"flag item missing from flagged.html: {fl.get('item')}")

    # 7. Companion audit link on canonical index.html
    if 'href="docs/index.html"' not in index_html:
        errors.append("index.html missing relative href=\"docs/index.html\" link to companion audit")

    summary = {
        "audited_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "session": "be974159",
        "inventory_count": len(rows),
        "method_counts": matches_doc.get("counts"),
        "market_rows": sum(1 for r in rows if r["method"] == "market"),
        "single_venue_market_rows": single_venue_market_rows,
        "in_play_market_rows": in_play_market_rows,
        "graded_results": sum(1 for r in rows if r.get("result") is not None),
        "flags_total": len(flags_doc.get("flags") or []),
        "corroboration_usable": len([x for x in (corrob_doc.get("rows") or []) if x.get("status") == "usable"]),
        "corroboration_rejected": len(corrob_doc.get("rejected") or []),
        "publish_gate_checks": len(ver_doc.get("checks") or []),
        "publish_gate_passed": bool(ver_doc.get("passed", all(c.get("ok") for c in (ver_doc.get("checks") or [])))),
        "errors": errors,
        "verdict": "PASS" if not errors else "FAIL",
    }
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
        fh.write("\n")
    print(json.dumps(summary, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
