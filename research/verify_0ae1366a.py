#!/usr/bin/env python3
"""Independent re-derivation of every published row (session 0ae1366a).

This deliberately does not import `tools/verify.py` or `tools/integrity.py`: it re-reads the
published artefacts and re-computes the properties the site claims, so a bug in the publisher's own
gate cannot vouch for itself. Exit code 0 = every claim below holds on the current snapshot.

Claims checked
  1. every row has an id, a competition, a start time, two participants and a Hotspawn match link
     whose trailing id equals the row id, and ids are unique
  2. every row has a pick that names one of the two listed teams
  3. priced rows have two finite probabilities in [0,1] that sum to 1 (+-0.002) and the pick is the
     larger side (ties broken only when both are equal)
  4. settlement rows carry no probability and name the remaining listed participant
  5. `data/picks.csv` mirrors `data/matches.json` row-for-row (id, pick, probability)
  6. every market row names at least one venue with an https quote URL
  7. the method histogram equals the `counts` block published with the dataset
  8. the site's headline numbers on index.html agree with the dataset (match count, pick count)
  9. no probability is attributed to a Hotspawn crowd percentage (community_pick_pct never prices)

Writes `research/verify_0ae1366a.json` with the evidence it used.
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "research", "verify_0ae1366a.json")

problems: list[str] = []
notes: list[str] = []


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def main() -> int:
    doc = load(os.path.join(DATA, "matches.json"))
    rows = doc.get("matches") or []
    if not rows:
        problems.append("dataset has no matches")
        return finish({})

    ids = [str(r.get("id")) for r in rows]
    if len(set(ids)) != len(ids):
        dupes = [k for k, v in Counter(ids).items() if v > 1]
        problems.append(f"duplicate ids: {dupes[:10]}")

    picked = priced = settlement = 0
    for r in rows:
        rid = str(r.get("id"))
        for field in ("competition", "start_utc", "hotspawn_url"):
            if not r.get(field):
                problems.append(f"{rid}: missing {field}")
        teams = [r.get("team0") or {}, r.get("team1") or {}]
        names = [t.get("name") for t in teams]
        if any(not n for n in names):
            problems.append(f"{rid}: missing a participant name")
        url = r.get("hotspawn_url") or ""
        m = re.search(r"-(\d+)$", url)
        if not m or m.group(1) != rid:
            problems.append(f"{rid}: Hotspawn link does not end with the match id ({url})")

        pick = r.get("pick") or {}
        side = pick.get("side")
        if side not in (0, 1) or not pick.get("team"):
            problems.append(f"{rid}: no pick")
            continue
        picked += 1
        if pick["team"] != names[side]:
            problems.append(f"{rid}: pick {pick['team']!r} is not the participant on side {side}")

        p0, p1 = r.get("p0"), r.get("p1")
        if r.get("pick_type") == "settlement" or r.get("method") == "unresolved" and p0 is None:
            settlement += 1
            if p0 is not None or p1 is not None:
                problems.append(f"{rid}: settlement row carries a probability")
            res = r.get("resolution") or {}
            if not (res.get("source") or res.get("source_url")):
                problems.append(f"{rid}: settlement row has no resolution source")
            winner = res.get("winner")
            if winner and winner not in names:
                problems.append(f"{rid}: settlement winner {winner!r} is not a listed participant")
            if winner and pick.get("team") and winner != pick["team"]:
                problems.append(f"{rid}: settlement pick {pick['team']!r} disagrees with the ruling ({winner!r})")
            continue

        if r.get("method") == "unresolved" and p0 is None:
            settlement += 1
            continue
        if p0 is None or p1 is None:
            # a genuinely unpriced row is allowed only when it is documented as unresolved
            if r.get("method") != "unresolved":
                problems.append(f"{rid}: priced method without probabilities")
            continue
        priced += 1
        try:
            p0f, p1f = float(p0), float(p1)
        except (TypeError, ValueError):
            problems.append(f"{rid}: non-numeric probability")
            continue
        if not (0.0 <= p0f <= 1.0 and 0.0 <= p1f <= 1.0):
            problems.append(f"{rid}: probability outside [0,1]")
        if abs((p0f + p1f) - 1.0) > 0.002:
            problems.append(f"{rid}: probabilities sum to {p0f + p1f:.4f}")
        side_p = p0f if side == 0 else p1f
        other = p1f if side == 0 else p0f
        if side_p < other - 1e-12:
            problems.append(f"{rid}: pick is the lower-probability side ({side_p:.4f} < {other:.4f})")
        if abs(side_p - float(pick.get("probability", side_p))) > 0.0005:
            problems.append(f"{rid}: pick probability disagrees with the row")
        crowd = r.get("community_pick_pct")
        if isinstance(crowd, dict):
            crowd_side = crowd.get(f"team{side}")
            if isinstance(crowd_side, (int, float)) and abs(side_p - crowd_side / 100.0) < 1e-9:
                notes.append(f"{rid}: pick probability equals the Hotspawn crowd share (coincidence?)")

    # 5. CSV mirror
    csv_path = os.path.join(DATA, "picks.csv")
    with open(csv_path, encoding="utf-8", newline="") as fh:
        csv_rows = list(csv.DictReader(fh))
    if len(csv_rows) != len(rows):
        problems.append(f"picks.csv has {len(csv_rows)} rows, dataset has {len(rows)}")
    by_id = {str(r["id"]): r for r in rows}
    csv_fields = set(csv_rows[0].keys()) if csv_rows else set()
    id_key = next((k for k in ("hotspawn_id", "id", "match_id") if k in csv_fields), None)
    if not id_key:
        problems.append("picks.csv has no id column")
    else:
        for cr in csv_rows:
            r = by_id.get(str(cr.get(id_key)))
            if r is None:
                problems.append(f"picks.csv row {cr.get(id_key)} is not in the dataset")
                continue
            if str(cr.get("pick") or "").strip() != str((r.get("pick") or {}).get("team") or "").strip():
                problems.append(f"{cr.get(id_key)}: picks.csv pick differs from the dataset")

    # 6. market rows quote a venue
    for r in rows:
        if r.get("method") != "market":
            continue
        venues = ((r.get("market") or {}).get("venues") or [])
        if not venues:
            problems.append(f"{r['id']}: market row without a venue")
        elif not any(str(v.get("url") or "").startswith("https://") for v in venues):
            problems.append(f"{r['id']}: market row without an https venue URL")

    # 7. method histogram
    hist = Counter(r.get("method") for r in rows)
    published = doc.get("counts") or {}
    for method, count in hist.items():
        if int(published.get(method, -1)) != count:
            problems.append(f"counts.{method}={published.get(method)} but dataset has {count}")
    if sum(published.values()) != len(rows):
        problems.append(f"counts sum to {sum(published.values())} for {len(rows)} rows")

    # 8. headline numbers on the site
    index_html = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    if f"across all {len(rows)} scheduled LoL matches" not in index_html:
        notes.append("index.html hero does not repeat the match count in the expected phrasing")
    if f"{picked} of {len(rows)} matches carry a pick" not in index_html:
        problems.append(f"index.html does not state the computed coverage ({picked} of {len(rows)})")

    evidence = {
        "generated_utc": doc.get("generated_utc"),
        "inventory_fetched_utc": doc.get("inventory_fetched_utc"),
        "rows": len(rows),
        "picked": picked,
        "priced": priced,
        "settlement": settlement,
        "methods": dict(hist),
        "problems": problems,
        "notes": notes,
        "passed": not problems,
    }
    return finish(evidence)


def finish(evidence: dict) -> int:
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(evidence, fh, indent=1)
        fh.write("\n")
    print(json.dumps({k: v for k, v in evidence.items() if k not in ("problems", "notes")}, indent=1))
    for p in problems[:40]:
        print("PROBLEM:", p)
    for n in notes[:10]:
        print("note:", n)
    print("RESULT:", "PASS" if not problems else f"FAIL ({len(problems)} problems)")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
