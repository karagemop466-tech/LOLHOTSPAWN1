#!/usr/bin/env python3
"""Session 5d4e9477: independent line-by-line verification of the published tree.

Reads only committed artifacts; writes only into audit/session_5d4e9477/.
For every Hotspawn fixture it checks:
  * exact 1:1 reconciliation with the runner's raw Hotspawn receipt;
  * a Hotspawn match-card URL (the official source for the fixture);
  * probabilities sum to 100% (or both are blank on an official settlement);
  * the published pick is the higher-probability side (or a typed settlement);
  * market rows carry at least one venue quote URL;
  * model/provisional rows name their Leaguepedia results page;
  * data/picks.csv mirrors the row;
  * the row is rendered in table.html with an external source link and in picks.html;
  * unresolved rows are named on unresolved.html;
  * the executive summary links to every pick view (phone findability).
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
DATA = ROOT / "data"

def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def external_links(fragment: str) -> list[str]:
    return re.findall(r'href="(https?://[^"]+)"', fragment or "")

def main() -> int:
    checked = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    dataset = load(DATA / "matches.json")
    raw = load(DATA / "raw/hotspawn_lol.json")
    rows = dataset["matches"]
    raw_ids = [str(f["id"]) for f in raw["fixtures"]]
    row_ids = [str(m["id"]) for m in rows]
    table = (ROOT / "table.html").read_text(encoding="utf-8")
    picks = (ROOT / "picks.html").read_text(encoding="utf-8")
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    unresolved = (ROOT / "unresolved.html").read_text(encoding="utf-8")
    csv_rows = {r["hotspawn_id"]: r for r in csv.DictReader((DATA / "picks.csv").open(encoding="utf-8", newline=""))}

    table_rows = re.findall(r'<tr class="prow[^>]*>.*?</tr>', table, re.S)
    table_by_id: dict[str, str] = {}
    for tr in table_rows:
        m = re.search(r'hotspawn\.com/matches/[^"]*?-(\d+)"', tr)
        if m:
            table_by_id[m.group(1)] = tr
    pick_anchors = set(re.findall(r'id="match-(\d+)"', picks))

    errors: list[str] = []
    review_findings: list[dict] = []
    if sorted(raw_ids) != sorted(row_ids):
        errors.append(f"raw/dataset ID multiset differs: raw={len(raw_ids)} dataset={len(row_ids)} "
                      f"missing={sorted(set(raw_ids)-set(row_ids))[:8]} extra={sorted(set(row_ids)-set(raw_ids))[:8]}")
    if len(row_ids) != len(set(row_ids)):
        errors.append("duplicate match ids in dataset")
    if len(table_rows) != len(rows):
        errors.append(f"table.html has {len(table_rows)} rows, dataset has {len(rows)}")
    if set(csv_rows) != set(row_ids):
        errors.append("picks.csv ids do not match dataset ids")

    required_index_links = ["table.html", "picks.html", "results.html", "featured.html",
                            "originated.html", "unresolved.html", "flagged.html", "coverage.html",
                            "sources.html", "methodology.html"]
    missing_index_links = [h for h in required_index_links if f'href="{h}"' not in index]
    if missing_index_links:
        errors.append(f"executive summary missing links: {missing_index_links}")

    out_rows = []
    for m in rows:
        mid = str(m["id"])
        t0 = m["team0"]["name"]
        t1 = m["team1"]["name"]
        method = m.get("method")
        p0, p1 = m.get("p0"), m.get("p1")
        pick = m.get("pick") or {}
        hs = m.get("hotspawn_url") or ""
        problems: list[str] = []

        if not hs.startswith("https://www.hotspawn.com/matches/"):
            problems.append("missing official Hotspawn match-card URL")
        if mid not in hs:
            problems.append("Hotspawn URL does not name this fixture id")

        if method == "unresolved":
            if p0 is not None or p1 is not None:
                problems.append("unresolved row claims a probability")
            res = m.get("resolution") or {}
            if not res.get("winner") or not (res.get("source_url") or res.get("source")):
                problems.append("settlement lacks winner or source URL")
            if pick.get("probability") is not None:
                problems.append("settlement pick claims a probability")
            if mid not in unresolved:
                problems.append("unresolved row absent from unresolved.html")
            prob_ok = True
        else:
            if not isinstance(p0, (int, float)) or not isinstance(p1, (int, float)):
                problems.append("priced row missing probability")
                prob_ok = False
            else:
                prob_ok = math.isfinite(p0) and math.isfinite(p1) and abs((p0 + p1) - 1.0) <= 0.002
                if not prob_ok:
                    problems.append(f"probabilities sum to {(p0+p1)*100:.2f}%")
                # A 50/50 line has no higher side: the published card calls it a
                # "toss-up" and picks team0 by convention. Only a strict edge is checked.
                if abs(p0 - p1) > 0.002:
                    higher = t0 if p0 > p1 else t1
                    if pick.get("team") != higher:
                        problems.append(f"pick {pick.get('team')!r} is not higher side {higher!r}")
                elif pick.get("team") not in (t0, t1):
                    problems.append("toss-up pick does not name a participant")
                if abs(float(pick.get("probability") or -1) - max(p0, p1)) > 0.002:
                    problems.append("pick probability does not equal max(p0,p1)")

        if method == "market":
            venues = ((m.get("market") or {}).get("venues") or [])
            if not venues or not all(v.get("url") and v.get("quote") for v in venues):
                problems.append("market row lacks a venue quote URL")
            if any("kills" in (str(v.get("quote")) + str(v.get("name"))).lower() for v in venues):
                problems.append("(Kills) derivative used as match line")
        elif method in ("model", "provisional"):
            if not m.get("leaguepedia_page"):
                problems.append("originated row lacks its Leaguepedia results page")
            if not m.get("basis"):
                problems.append("originated row lacks its Elo basis")
        elif method != "unresolved":
            problems.append(f"unknown method {method!r}")

        c = csv_rows.get(mid)
        if not c:
            problems.append("row absent from picks.csv")
        else:
            if c["pick"] != pick.get("team"):
                problems.append("picks.csv pick differs")
            if c.get("hotspawn_url") != hs:
                problems.append("picks.csv Hotspawn source URL differs")
            if c.get("method") != method:
                problems.append("picks.csv method differs")
            if c.get("start_utc") != m.get("start_utc"):
                problems.append("picks.csv kick-off differs")
            if method != "unresolved":
                try:
                    if abs(float(c["p0"]) - p0) > 0.002 or abs(float(c["p1"]) - p1) > 0.002:
                        problems.append("picks.csv probabilities differ")
                except (TypeError, ValueError):
                    problems.append("picks.csv probabilities unreadable")

        tr = table_by_id.get(mid)
        links = external_links(tr or "")
        if not tr:
            problems.append("row absent from table.html")
        elif hs not in links:
            problems.append("table row does not link to this fixture's exact Hotspawn card")
        if method == "market" and tr:
            venue_urls = {v.get("url") for v in ((m.get("market") or {}).get("venues") or []) if v.get("url")}
            if not venue_urls.intersection(links):
                problems.append("market table row does not link to any listed venue quote")
        if method in ("model", "provisional") and tr and not any("lol.fandom.com/wiki/" in u for u in links):
            problems.append("originated table row lacks its Leaguepedia results link")
        if mid not in pick_anchors:
            problems.append("card absent from picks.html")

        if method != "unresolved" and isinstance(p0, (int, float)) and isinstance(p1, (int, float)):
            displayed_tie = round(float(p0) * 100, 1) == round(float(p1) * 100, 1)
            exact_tie = abs(float(p0) - float(p1)) < 1e-12
            if exact_tie or displayed_tie:
                review_findings.append({
                    "id": mid,
                    "teams": [t0, t1],
                    "p0": p0,
                    "p1": p1,
                    "displayed_as": f"{p0*100:.1f}% / {p1*100:.1f}%",
                    "published_pick": pick.get("team"),
                    "kind": "exact probability tie" if exact_tie else "tie after one-decimal display rounding",
                    "source": hs,
                    "note": "No displayed favourite; a team-side selection is a tie-break, not evidence of an edge. Review PR #102, which is changing these to explicit no-pick rows.",
                })

        out_rows.append({
            "id": mid, "competition": m.get("competition"), "teams": [t0, t1],
            "start_utc": m.get("start_utc"), "method": method,
            "p0": p0, "p1": p1, "pick": pick.get("team"),
            "probability_sum_ok": prob_ok,
            "official_source": hs,
            "extra_sources": sorted(set(links) - {hs}),
            "all_sources": sorted(set(links)),
            "in_table": bool(tr), "in_picks": mid in pick_anchors,
            "problems": problems,
        })
        if problems:
            errors.append(f"{mid}: " + "; ".join(problems))

    summary = {
        "checked_utc": checked,
        "dataset_generated_utc": dataset.get("generated_utc"),
        "inventory_fetched_utc": dataset.get("inventory_fetched_utc"),
        "raw_feed_fetched_utc": raw.get("fetched_utc"),
        "raw_feed_source": raw.get("source_url"),
        "rows": len(rows),
        "raw_fixtures": len(raw_ids),
        "table_rows": len(table_rows),
        "picks_cards": len(pick_anchors),
        "csv_rows": len(csv_rows),
        "methods": {k: sum(1 for r in out_rows if r["method"] == k)
                    for k in sorted({r["method"] for r in out_rows})},
        "rows_with_official_source": sum(1 for r in out_rows if r["official_source"].startswith("https://www.hotspawn.com/")),
        "rows_with_table_source_link": sum(1 for r in out_rows if r["in_table"] and (r["official_source"] or r["extra_sources"])),
        "rows_with_probability": sum(1 for r in out_rows if r["p0"] is not None),
        "unresolved_rows": sum(1 for r in out_rows if r["method"] == "unresolved"),
        "review_findings": review_findings,
        "errors": errors,
        "passed": not errors,
        "limitations": [
            "This script verifies that every row carries an official Hotspawn match-card link and (where applicable) a book/results link; it does not crawl every external URL. Live URL reachability is checked separately by audit/live_source_verify.py in CI and by the dated fetch receipts in EXTERNAL_LINES.md.",
            "Probabilities on model/provisional rows are our own Elo estimates from community-maintained Leaguepedia results; they are not official league statements.",
            "Market quotes are observations at collection time; a closed board may later answer 401/403. Those are historical receipts, not current prices.",
        ],
    }
    (OUT / "rows.json").write_text(json.dumps({"summary": summary, "rows": out_rows}, ensure_ascii=False, indent=2), encoding="utf-8")

    def esc(x) -> str:
        return str(x).replace("|", "\\|").replace("\n", " ")

    md = [
        "# Line-by-line verification — session `5d4e9477`", "",
        f"Checked **{checked}** against committed snapshot `{dataset.get('generated_utc')}` "
        f"(Hotspawn inventory `{dataset.get('inventory_fetched_utc')}`).", "",
        f"- **{len(rows)} rows** · raw feed **{len(raw_ids)}** fixtures · `{len(table_rows)}` table rows · "
        f"`{len(pick_anchors)}` cards · `{len(csv_rows)}` CSV rows.",
        f"- Method mix: {json.dumps(summary['methods'])}.",
        f"- Every row carries an official Hotspawn match-card source: "
        f"**{summary['rows_with_official_source']}/{len(rows)}**.",
        f"- Rows with a win probability: **{summary['rows_with_probability']}**; "
        f"official settlements with no invented probability: **{summary['unresolved_rows']}**.",
        f"- Structural/provenance checks: **{'PASS' if not errors else 'FAIL'}** ({len(errors)} row errors).",
        f"- **Review required:** {len(review_findings)} rows display a 50.0% / 50.0% tie at one decimal "
        f"({sum(1 for x in review_findings if x['kind'] == 'exact probability tie')} exact; "
        f"{sum(1 for x in review_findings if x['kind'] != 'exact probability tie')} rounded). "
        "The current canonical dashboard chooses a side on these tied rows; that choice is not a demonstrated "
        "edge. PR #102 is open and documents the planned explicit no-pick handling; re-run this audit after it merges.", "",
        "## Every row (source link on every line)", "",
        "| Hotspawn id | Source links | Tournament | Teams | Kick-off (UTC) | Method | p0 / p1 | Pick | Table | Card | Verdict |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in out_rows:
        source_links = []
        for url in r.get("all_sources", []):
            if url == r["official_source"]:
                label = "Hotspawn card"
            elif "lol.fandom.com/wiki/" in url:
                label = "Leaguepedia results"
            elif r["method"] == "market":
                label = "market quote"
            else:
                label = "source"
            source_links.append(f"[{label}]({url})")
        src = " &middot; ".join(source_links) or "—"
        probs = "— / —" if r["p0"] is None else f"{r['p0']*100:.1f}% / {r['p1']*100:.1f}%"
        md.append("| {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
            esc(r["id"]), src, esc(r["competition"]), esc(" vs ".join(r["teams"])),
            esc(r["start_utc"]), esc(r["method"]), esc(probs), esc(r["pick"]),
            "yes" if r["in_table"] else "NO", "yes" if r["in_picks"] else "NO",
            "OK" if not r["problems"] else "**" + esc("; ".join(r["problems"])) + "**"))
    md += ["", "## Review required: displayed 50/50 ties", "",
           "These rows meet the structural checks but the current data snapshot still publishes a team-side "
           "selection when the two displayed win percentages are equal. A pick in this state is a tie-break, "
           "not a supported favourite. The working branch for PR #102 documents explicit no-pick handling; "
           "the current published snapshot had not yet incorporated that change at this audit timestamp.", "",
           "| Hotspawn id | Teams | Method | Stored p0 / p1 | Published pick | Finding | Source |",
           "|---|---|---|---|---|---|---|"]
    for f in review_findings:
        md.append("| {} | {} | {} | {:.4f} / {:.4f} | {} | {} | [{}]({}) |".format(
            esc(f["id"]), esc(" vs ".join(f["teams"])), esc(next(r["method"] for r in out_rows if r["id"] == f["id"])),
            f["p0"], f["p1"], esc(f["published_pick"]), esc(f["kind"]), f["id"], f["source"]))
    md += ["", "## Limitations", ""] + [f"- {x}" for x in summary["limitations"]] + [
        "", "Raw Hotspawn feed receipt (official API response saved by the runner): "
        f"`data/raw/hotspawn_lol.json`, fetched `{raw.get('fetched_utc')}`, source "
        f"<{raw.get('source_url')}>.", ""]
    (OUT / "ROWS.md").write_text("\n".join(md), encoding="utf-8")
    print(f"{'PASS' if not errors else 'FAIL'}: {len(rows)} rows, {len(errors)} errors, "
          f"{summary['rows_with_official_source']} official source links")
    for e in errors[:20]:
        print(" -", e)
    return 0 if not errors else 1

if __name__ == "__main__":
    raise SystemExit(main())
