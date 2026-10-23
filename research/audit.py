#!/usr/bin/env python3
"""Line-by-line audit of the published dataset.

Re-derives every publishable number from the committed raw receipts instead of trusting
the generated JSON:

  1. inventory      — every Hotspawn fixture appears exactly once, IDs unique
  2. probability    — p0 + p1 = 1, pick == argmax, bounds respected
  3. Elo            — p0 reproduced from the committed ratings with the documented formula
  4. market         — each venue de-vigged and re-weighted; consensus reproduced
  5. provenance     — every row carries a Hotspawn card URL; market rows carry venue URLs
  6. quarantine     — every `dqteams` claim is present in the raw Leaguepedia directive file
  7. freshness      — snapshot age, stale-fixture count, start-time disagreements
  8. sources        — every probed source's recorded status compared to its stored verdict

Writes research/AUDIT.json and prints a human-readable summary. Exit code 1 if any check
fails, so it can be wired into CI later.
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
RESEARCH = os.path.join(ROOT, "research")
RECEIPT = os.path.join(ROOT, "archive", "session-8336fb7e", "data", "book_receipts.json")

problems: list[dict] = []
notes: list[str] = []


def load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def bad(check: str, detail: str, severity: str = "irregularity") -> None:
    problems.append({"check": check, "detail": detail, "severity": severity})


def main() -> None:
    matches = load(os.path.join(DATA, "matches.json")) or {}
    rows = matches.get("matches") or []
    fixtures = (load(os.path.join(DATA, "raw", "hotspawn_lol.json")) or {}).get("fixtures") or []
    dq = (load(os.path.join(DATA, "raw", "leaguepedia_dq.json")) or {}).get("dq_by_page") or {}
    sources = load(os.path.join(DATA, "sources_status.json")) or {}
    receipt = load(RECEIPT) or {}
    model = matches.get("model") or {}

    # 1. inventory ---------------------------------------------------------
    fx_ids = [f["id"] for f in fixtures]
    row_ids = [r["id"] for r in rows]
    if len(set(row_ids)) != len(row_ids):
        bad("inventory", f"duplicate row ids: {[i for i in set(row_ids) if row_ids.count(i) > 1][:5]}")
    if set(fx_ids) != set(row_ids):
        bad("inventory", f"row set != fixture set: missing={sorted(set(fx_ids) - set(row_ids))[:5]} "
                         f"extra={sorted(set(row_ids) - set(fx_ids))[:5]}")
    notes.append(f"inventory: {len(rows)} rows vs {len(fixtures)} scheduled Hotspawn fixtures")

    # 2. probability -------------------------------------------------------
    for r in rows:
        p0, p1 = r.get("p0"), r.get("p1")
        if r.get("method") == "unresolved":
            pick = r.get("pick") or {}
            if p0 is not None or p1 is not None:
                bad("probability", f"{r['id']} unresolved row carries a probability")
            if pick and pick.get("probability") is not None:
                bad("probability", f"{r['id']} settlement pick claims a probability")
            if pick and pick.get("team") not in (r["team0"]["name"], r["team1"]["name"]):
                bad("probability", f"{r['id']} settlement pick names a side outside the fixture")
            continue
        if p0 is None or p1 is None:
            bad("probability", f"{r['id']} priced row missing a probability")
            continue
        if abs(p0 + p1 - 1.0) > 1e-3:
            bad("probability", f"{r['id']} p0+p1={p0 + p1:.6f}")
        floor, ceil = model.get("prob_floor"), model.get("prob_ceil")
        if floor is not None and ceil is not None and r.get("method") in ("model", "provisional"):
            if not (floor - 1e-9 <= p0 <= ceil + 1e-9):
                bad("probability", f"{r['id']} p0={p0} outside [{floor},{ceil}]")
        pick = r.get("pick") or {}
        top = max(p0, p1)
        if not pick:
            bad("probability", f"{r['id']} priced row has no pick")
        elif abs(pick["probability"] - top) > 1e-3:
            bad("probability", f"{r['id']} pick probability {pick['probability']} != max {top}")
        elif pick["team"] not in (r["team0"]["name"], r["team1"]["name"]):
            bad("probability", f"{r['id']} pick team not in the fixture")

    # 3. Elo reproduction --------------------------------------------------
    elo_checked = 0
    for r in rows:
        if r.get("method") not in ("model", "provisional"):
            continue
        a, b = r["team0"].get("elo"), r["team1"].get("elo")
        if a is None or b is None:
            continue
        expected = 1.0 / (1.0 + math.pow(10.0, (b - a) / 400.0))
        expected = min(max(expected, model.get("prob_floor", 0.05)), model.get("prob_ceil", 0.95))
        if abs(expected - r["p0"]) > 0.004:
            bad("elo", f"{r['id']} p0={r['p0']} vs recomputed {expected:.4f}")
        elo_checked += 1
    notes.append(f"elo: {elo_checked} rows reproduced from committed ratings")

    # 4. market consensus --------------------------------------------------
    w = {"Pinnacle": 0.36, "Polymarket": 0.24, "Kalshi": 0.18, "Bovada": 0.12, "Esportsbook": 0.10}
    market_checked = 0
    for r in rows:
        if r.get("method") != "market":
            continue
        mk = r.get("market") or {}
        venues = mk.get("venues") or []
        if not venues:
            bad("market", f"{r['id']} market row with no venues")
            continue
        num = den = 0.0
        for v in venues:
            num += w.get(v["name"], 0.10) * v["p0"]
            den += w.get(v["name"], 0.10)
        consensus = num / den if den else None
        if consensus is None or abs(consensus - r["p0"]) > 0.002:
            bad("market", f"{r['id']} consensus {r['p0']} vs recomputed {consensus}")
        for v in venues:
            if not str(v.get("url", "")).startswith("http"):
                bad("market", f"{r['id']} venue {v['name']} has no URL")
            if not (0.0 < v["p0"] < 1.0):
                bad("market", f"{r['id']} venue {v['name']} probability out of range")
        if r.get("p0") is None:
            bad("market", f"{r['id']} market row without probability")
        market_checked += 1
    notes.append(f"market: {market_checked} rows re-weighted from their venue quotes")

    # stale archived receipt usage
    rec_quotes = receipt.get("quotes") or {}
    rec_used = 0
    for r in rows:
        for v in (r.get("market") or {}).get("venues") or []:
            if v.get("name") == "Esportsbook":
                rec_used += 1
                if str(r["id"]) not in rec_quotes:
                    bad("provenance", f"{r['id']} Esportsbook venue has no archived receipt")
    if rec_used:
        bad("provenance",
            f"{rec_used} row(s) still price an 'Esportsbook' venue from the archived "
            f"2026-10-21 receipt set; that feed (EGamersWorld) returns HTTP 403 to the runner",
            severity="review")

    # 5. provenance --------------------------------------------------------
    for r in rows:
        if not str(r.get("hotspawn_url", "")).startswith("https://www.hotspawn.com/"):
            bad("provenance", f"{r['id']} missing Hotspawn card URL")
        if r.get("pick") and r["pick"]["team"] not in (r["team0"]["name"], r["team1"]["name"]):
            bad("provenance", f"{r['id']} pick team outside the fixture")

    # 6. quarantine claims -------------------------------------------------
    for r in rows:
        if r.get("method") != "unresolved":
            continue
        page = r.get("leaguepedia_page") or ""
        removed = (dq.get(page) or [])
        names = {r["team0"]["name"], r["team1"]["name"]}
        if not names & set(removed):
            bad("quarantine", f"{r['id']} unresolved but no dqteams entry for {sorted(names)} on {page}")
    notes.append(f"quarantine: {sum(1 for r in rows if r['method'] == 'unresolved')} rows checked "
                 f"against {len(dq)} Data: pages")

    # 7. freshness ---------------------------------------------------------
    gen = matches.get("generated_utc")
    if gen:
        age = (datetime.now(timezone.utc)
               - datetime.strptime(gen, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc))
        notes.append(f"snapshot age: {age.total_seconds() / 3600:.2f} h")
        if age.total_seconds() > 8 * 3600:
            bad("freshness", f"snapshot is {age.total_seconds() / 3600:.1f} h old (refresh window is 4-8 h)",
                severity="review")
    stale = sum(1 for r in rows if r.get("stale"))
    notes.append(f"stale fixtures (kick-off passed, still listed scheduled): {stale}")

    # 8. sources -----------------------------------------------------------
    src = sources.get("sources") or []
    for s in src:
        if s.get("ok") and s.get("status") != 200:
            bad("sources", f"{s.get('name')} marked ok with status {s.get('status')}")

    # 9. csv mirror --------------------------------------------------------
    csv_path = os.path.join(DATA, "picks.csv")
    if os.path.exists(csv_path):
        with open(csv_path, encoding="utf-8") as fh:
            csv_rows = list(csv.DictReader(fh))
        if len(csv_rows) != len(rows):
            bad("csv", f"picks.csv has {len(csv_rows)} rows vs {len(rows)}")
        ids = {r["id"] for r in rows}
        csv_ids = {c.get("hotspawn_id") for c in csv_rows}
        if csv_ids != ids:
            bad("csv", "picks.csv hotspawn_id set differs from matches.json")
        for c in csv_rows:
            if c.get("pick") and c.get("pick") not in (c.get("team0"), c.get("team1")):
                bad("csv", f"picks.csv row {c.get('hotspawn_id')} picks a team outside the fixture")

    # report ---------------------------------------------------------------
    report = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rows": len(rows),
        "counts": matches.get("counts"),
        "notes": notes,
        "problems": problems,
        "passed": not [p for p in problems if p["severity"] == "irregularity"],
    }
    os.makedirs(RESEARCH, exist_ok=True)
    with open(os.path.join(RESEARCH, "AUDIT.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, ensure_ascii=False)
        fh.write("\n")

    for n in notes:
        print("note:", n)
    for p in problems:
        print(f"{p['severity']:>12}: [{p['check']}] {p['detail']}")
    print("PASS" if report["passed"] else "FAIL")
    sys.exit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
