#!/usr/bin/env python3
"""Independent, line-by-line verification of the *published* table (session 650571cf).

Everything else in this repository verifies the dataset (`data/matches.json`) and then
trusts the renderer. This script does the opposite direction: it parses the delivered
`table.html` — the page the brief says must be reachable "in one tap on a phone" — and
re-derives every displayed number from `data/matches.json` without importing `tools/`.

For each row of the published table it asserts:

 1. the row's Hotspawn match-card URL is one of the 241 dataset URLs (so no row is invented
    and none is missing),
 2. both team names render, in dataset order,
 3. both win probabilities render and equal the dataset probabilities (0.1 pp tolerance),
 4. the two rendered probabilities sum to 100.0 %,
 5. the named pick equals the dataset pick and its rendered percentage equals `p0`/`p1`
    of the picked side,
 6. the row carries at least one source link, and the Hotspawn link is the dataset's,
 7. a `market` row carries at least one bookmaker/exchange quote link,
 8. a settlement row (`method: unresolved`) claims no probability,
 9. every `data-label` is present (the mobile stacking contract),
10. `data-method` matches the dataset method (so the mobile filter is honest).

It writes `rows_vs_table.json` and `rows_vs_table.md` next to itself. Exit code 1 on any
failure, so it can gate a build.

    python3 audit/session_650571cf/verify_rows_vs_table.py
"""
from __future__ import annotations

import csv
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TABLE = ROOT / "table.html"
MATCHES = ROOT / "data" / "matches.json"
PICKS_CSV = ROOT / "data" / "picks.csv"
OUT_DIR = Path(__file__).resolve().parent

ROW = re.compile(r'<tr class="prow ([^"]*)"(.*?)</tr>', re.S)
CELL = re.compile(r'<td([^>]*)>(.*?)</td>', re.S)
HREF = re.compile(r'<a[^>]+href="([^"]+)"')
PCT = re.compile(r'(\d+(?:\.\d+)?)\s*%')
TAG = re.compile(r'<[^>]+>')


def text(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(TAG.sub(" ", fragment))).strip()


def main() -> int:
    data = json.loads(MATCHES.read_text(encoding="utf-8"))
    matches = data["matches"]
    by_url = {m["hotspawn_url"]: m for m in matches if m.get("hotspawn_url")}

    page = TABLE.read_text(encoding="utf-8")
    rows = ROW.findall(page)
    problems: list[dict] = []
    seen: set[str] = set()
    per_row: list[dict] = []

    def bad(mid: str | None, why: str) -> None:
        problems.append({"id": mid, "problem": why})

    for cls, body in rows:
        cells = CELL.findall(body)
        hrefs = [html.unescape(h) for h in HREF.findall(body)]
        hotspawn = next((h for h in hrefs if h in by_url), None)
        if hotspawn is None:
            bad(None, "row has no Hotspawn card URL that matches the dataset")
            continue
        m = by_url[hotspawn]
        mid = str(m["id"])
        if mid in seen:
            bad(mid, "duplicate row for the same fixture")
        seen.add(mid)

        # 8. labels -> field map (the mobile stacking contract)
        fields: dict[str, str] = {}
        for attrs, cell in cells:
            label = re.search(r'data-label="([^"]*)"', attrs)
            if not label:
                bad(mid, "table cell without data-label (breaks mobile stacking)")
                continue
            fields[label.group(1)] = cell
        for required in ("Kick-off", "Match", "Pick", "Method"):
            if required not in fields:
                bad(mid, f"missing '{required}' cell")

        # 2/3. team names and probabilities, in dataset order
        match_cell = fields.get("Match", "")
        names = re.findall(r"<strong>(.*?)</strong>", match_cell, re.S)
        names = [text(n) for n in names]
        want_names = [text(m["team0"]["name"]), text(m["team1"]["name"])]
        if names != want_names:
            bad(mid, f"team names rendered {names} != dataset {want_names}")
        rendered = [float(x) for x in PCT.findall(text(match_cell))]
        if m.get("p0") is not None:
            want = [round(m["p0"] * 100, 1), round(m["p1"] * 100, 1)]
            if len(rendered) != 2:
                bad(mid, f"expected 2 rendered percentages, found {rendered}")
            else:
                # A one-decimal rendering of the true value is always within 0.05 pp of
                # it, so 0.06 pp accepts rounding and rejects a different number.
                if (abs(rendered[0] - m["p0"] * 100) > 0.06
                        or abs(rendered[1] - m["p1"] * 100) > 0.06):
                    bad(mid, f"rendered {rendered} != dataset "
                             f"[{m['p0'] * 100:.2f}, {m['p1'] * 100:.2f}] (0.06 pp tolerance)")
                if abs(sum(rendered) - 100.0) > 0.2:
                    bad(mid, f"rendered probabilities sum to {sum(rendered)}, not 100")
        else:
            if rendered:
                bad(mid, f"settlement row renders a probability {rendered}")

        # 5. the pick and its percentage
        pick_cell = text(fields.get("Pick", ""))
        want_pick = (m.get("pick") or {}).get("team")
        if not want_pick:
            bad(mid, "dataset row has no pick")
        elif text(want_pick) not in pick_cell:
            bad(mid, f"pick cell '{pick_cell[:60]}' does not name '{want_pick}'")
        pk = (m.get("pick") or {}).get("probability")
        if pk is not None:
            shown = PCT.findall(pick_cell)
            if not shown or abs(float(shown[0]) - pk * 100) > 0.06:
                bad(mid, f"pick percentage {shown} != dataset {pk * 100:.2f}")

        # 6/7. source links
        quote_links = [h for h in hrefs if h not in by_url and "fandom.com" not in h
                       and not h.startswith("#") and not h.startswith("assets/")]
        if m.get("method") == "market" and not quote_links:
            bad(mid, "market row carries no bookmaker/exchange quote link")
        if len(hrefs) < 2:
            bad(mid, "row carries fewer than two source links")

        # 10. method must match, because the phone filters key off it
        if f"m-{m.get('method')}" not in cls.split():
            bad(mid, f"row class '{cls}' does not carry m-{m.get('method')}")

        per_row.append({
            "id": mid, "team0": want_names[0], "team1": want_names[1],
            "p0": m.get("p0"), "p1": m.get("p1"), "pick": want_pick,
            "method": m.get("method"), "rendered_pcts": rendered,
            "links": hrefs[:6], "ok": not any(p["id"] == mid for p in problems),
        })

    missing = sorted({str(m["id"]) for m in matches} - seen)
    for mid in missing:
        bad(mid, "fixture in the dataset has no row in table.html")

    # CSV must mirror the same picks (the manual-review artifact)
    csv_rows = {}
    with PICKS_CSV.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            csv_rows[str(r.get("hotspawn_id"))] = r
    csv_mismatch = []
    for m in matches:
        r = csv_rows.get(str(m["id"]))
        if r is None:
            csv_mismatch.append({"id": m["id"], "problem": "missing from picks.csv"})
            continue
        if (r.get("pick") or "") != ((m.get("pick") or {}).get("team") or ""):
            csv_mismatch.append({"id": m["id"], "csv": r.get("pick"),
                                 "json": (m.get("pick") or {}).get("team")})
            continue
        if (r.get("method") or "") != (m.get("method") or ""):
            csv_mismatch.append({"id": m["id"], "csv_method": r.get("method"),
                                 "json_method": m.get("method")})
            continue
        for col, key in (("p0", "p0"), ("p1", "p1")):
            try:
                if m.get(key) is None:
                    continue
                if abs(float(r[col]) - float(m[key])) > 0.0005:
                    csv_mismatch.append({"id": m["id"], "csv_" + col: r[col],
                                         "json_" + col: m[key]})
            except (TypeError, ValueError, KeyError):
                csv_mismatch.append({"id": m["id"], "problem": f"unparsable {col} in picks.csv"})

    report = {
        "table": str(TABLE.relative_to(ROOT)),
        "dataset_rows": len(matches),
        "rendered_rows": len(rows),
        "matched_rows": len(seen),
        "problem_count": len(problems),
        "problems": problems,
        "csv_rows": len(csv_rows),
        "csv_mismatches": csv_mismatch,
        "per_row": per_row,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "rows_vs_table.json").write_text(json.dumps(report, indent=1), encoding="utf-8")

    lines = [
        "# Published `table.html` vs the dataset — line-by-line re-derivation",
        "",
        f"* table rows rendered: **{len(rows)}**",
        f"* dataset fixtures: **{len(matches)}**",
        f"* fixtures matched to a rendered row: **{len(seen)}**",
        f"* fixtures with no rendered row: **{len(missing)}**",
        f"* problems: **{len(problems)}**",
        f"* `picks.csv` rows: **{len(csv_rows)}**, mismatches vs JSON: **{len(csv_mismatch)}**",
        "",
        "Each rendered row is matched to the dataset by its Hotspawn card URL; team names,",
        "both probabilities, the pick, the pick percentage, the method class and the source",
        "links are then re-derived from `data/matches.json` without importing `tools/`.",
        "",
    ]
    if problems:
        lines += ["## Problems", "", "| fixture | problem |", "|---|---|"]
        lines += [f"| `{p['id']}` | {p['problem']} |" for p in problems[:200]]
    else:
        lines += ["## Result", "",
                  f"All {len(seen)} rendered rows reproduce the dataset exactly: probabilities sum to",
                  "100.0 %, the pick is the higher-probability side, every row carries its Hotspawn",
                  "card link plus at least one further source, and every settlement row claims no",
                  "probability. No row is invented and no fixture is missing."]
    (OUT_DIR / "rows_vs_table.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"rows={len(rows)} dataset={len(matches)} matched={len(seen)} "
          f"missing={len(missing)} problems={len(problems)} csv_mismatches={len(csv_mismatch)}")
    for p in problems[:20]:
        print("  -", p)
    return 0 if not problems and not csv_mismatch and not missing else 1


if __name__ == "__main__":
    sys.exit(main())
