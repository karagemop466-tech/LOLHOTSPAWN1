#!/usr/bin/env python3
"""Verification gate: assert the dataset and the generated site are publishable.

Any failure exits non-zero, which stops the refresh workflow from committing.
"""
from __future__ import annotations

import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from integrity import row_errors
from common import DATA, ROOT, iso, load_json, log, now_utc, save_json

DOCS = ROOT  # GitHub Pages serves the branch root
ALLOWED = {"market", "model", "provisional", "unresolved"}
checks: list[dict] = []


def add(name: str, ok: bool, detail: str) -> None:
    checks.append({"name": name, "ok": bool(ok), "detail": detail})


def main() -> None:
    data = load_json(os.path.join(DATA, "matches.json")) or {}
    rows = data.get("matches") or []
    add("dataset present", len(rows) > 0, f"{len(rows)} matches loaded")

    raw = load_json(os.path.join(DATA, "raw/hotspawn_lol.json")) or {}
    inventory_ids = [str(f["id"]) for f in raw.get("fixtures", [])]
    row_ids = [str(r.get("id")) for r in rows]
    add("complete inventory reconciliation", bool(inventory_ids) and sorted(inventory_ids) == sorted(row_ids),
        f"raw fixtures={len(inventory_ids)}, published rows={len(row_ids)}; exact ID multiset comparison")
    failures = [(r.get("id"), row_errors(r)) for r in rows if row_errors(r)]
    add("finite probabilities and correctly named picks", not failures, str(failures[:5]))

    # --- per-row checks -----------------------------------------------------
    missing_source, bad_prob, bad_method, bad_pick, dupes = [], [], [], [], []
    seen = set()
    for r in rows:
        if not r.get("hotspawn_url", "").startswith("https://www.hotspawn.com/"):
            missing_source.append(r.get("id"))
        if r.get("id") in seen:
            dupes.append(r["id"])
        seen.add(r.get("id"))
        if not r.get("team0", {}).get("name") or not r.get("team1", {}).get("name"):
            bad_pick.append(r.get("id"))
        if r.get("method") not in ALLOWED:
            bad_method.append(r.get("id"))
        if row_errors(r):
            bad_prob.append(r.get("id"))
            bad_pick.append(r.get("id"))
        if r.get("method") == "market":
            mk = r.get("market") or {}
            if not mk.get("source_url") or not (mk.get("decimal") or mk.get("kind") == "prediction market"):
                bad_pick.append(r.get("id"))

    add("every row links to its Hotspawn match card", not missing_source,
        f"{len(rows) - len(missing_source)}/{len(rows)} rows carry a Hotspawn URL")
    add("probabilities sum to 100% (tolerance 0.2pp)", not bad_prob,
        f"{sum(r.get('method') != 'unresolved' for r in rows)} priced rows checked; problems: {bad_prob[:5]}")
    add("pick matches the higher probability", not bad_pick,
        f"{len(rows) - len(set(bad_pick))} rows consistent; problems: {sorted(set(bad_pick))[:5]}")
    add("method values are known", not bad_method, f"methods used: {sorted(set(r['method'] for r in rows))}")
    add("no duplicate match ids", not dupes, f"{len(seen)} unique ids; duplicates: {dupes[:5]}")

    # --- CSV mirror ---------------------------------------------------------
    csv_path = os.path.join(DATA, "picks.csv")
    csv_rows = 0
    if os.path.exists(csv_path):
        with open(csv_path, encoding="utf-8") as fh:
            csv_rows = max(0, sum(1 for _ in fh) - 1)
    add("picks.csv mirrors the dataset", csv_rows == len(rows),
        f"csv rows={csv_rows} json rows={len(rows)}")

    # --- site ---------------------------------------------------------------
    pages = ["index.html", "picks.html", "featured.html", "originated.html", "unresolved.html",
             "competitions.html", "teams.html", "methodology.html", "sources.html",
             "verification.html", "flagged.html"]
    missing_pages = [p for p in pages if not os.path.exists(os.path.join(DOCS, p))]
    add("all site pages exist", not missing_pages, f"{len(pages) - len(missing_pages)}/{len(pages)} pages")

    broken, no_nav, none_literal = [], [], []
    hrefs: Counter = Counter()
    for page in pages:
        path = os.path.join(DOCS, page)
        if not os.path.exists(path):
            continue
        text = open(path, encoding="utf-8").read()
        if 'class="nav"' not in text:
            no_nav.append(page)
        for href in re.findall(r'href="([^"#]+)(?:#[^"]*)?"', text):
            if href.startswith(("http://", "https://", "mailto:")):
                continue
            href = href.split("?", 1)[0]
            hrefs[href] += 1
            if href not in pages and not os.path.exists(os.path.join(DOCS, href)):
                broken.append(f"{page} -> {href}")
        for bad in ("&gt;None&lt;", ">None<", ">nan<", "&mdash;%"):
            if bad in text:
                none_literal.append(f"{page}:{bad}")
    add("no broken internal links", not broken, f"{len(broken)} problems: {broken[:6]}")
    add("navigation on every page", not no_nav, f"missing: {no_nav[:5]}")
    add("no empty/None values rendered", not none_literal, f"problems: {none_literal[:6]}")

    picks_html = open(os.path.join(DOCS, "picks.html"), encoding="utf-8").read()
    import html
    on_page = sum(1 for r in rows if picks_html.count(f'id="match-{html.escape(str(r["id"]), quote=True)}"') == 1)
    add("all matches rendered on the picks page", on_page == len(rows),
        f"{on_page}/{len(rows)} match cards found")

    index_html = open(os.path.join(DOCS, "index.html"), encoding="utf-8").read()
    needed = ["picks.html", "featured.html", "originated.html", "unresolved.html", "Executive summary"]
    add("executive summary links to every picks view", all(n in index_html for n in needed),
        f"present: {[n for n in needed if n in index_html]}")

    meth_html = open(os.path.join(DOCS, "methodology.html"), encoding="utf-8").read()
    bt_n = (data.get("backtest") or {}).get("n") or 0
    add("out-of-sample backtest & SVG calibration rendered on methodology page",
        bt_n > 500 and f"{bt_n:,}" in meth_html and "<svg" in meth_html,
        f"backtest series rendered: {bt_n:,}")

    src = (load_json(os.path.join(DATA, "sources_status.json")) or {}).get("sources") or []
    reachable = sum(1 for s in src if s.get("ok"))
    add("source availability recorded", len(src) >= 10,
        f"{reachable}/{len(src)} sources reachable on this build")

    # --- executive summary -> picks navigation -------------------------------
    unresolved = [r for r in rows if r.get("method") == "unresolved"]
    jump_targets = ["picks.html", "picks.html#today", "picks.html#next7",
                    "featured.html", "originated.html", "unresolved.html"]
    missing_jumps = [t for t in jump_targets if f'href="{t}"' not in index_html]
    add("executive summary jump links resolve", not missing_jumps,
        f"missing jump links: {missing_jumps}")

    summary_block = ""
    if 'id="unresolved-summary"' in index_html:
        summary_block = index_html.split('id="unresolved-summary"', 1)[1].split("</section>", 1)[0]
    unresolved_on_summary = [r["id"] for r in unresolved if f"match-{r['id']}" not in summary_block]
    add("every unresolved fixture appears in the executive summary",
        bool(summary_block) and not unresolved_on_summary,
        f"{len(unresolved) - len(unresolved_on_summary)}/{len(unresolved)} unresolved rows in the summary table; "
        f"missing: {unresolved_on_summary[:5]}")
    unresolved_unsourced = [r["id"] for r in unresolved
                            if f"match-{r['id']}" in summary_block
                            and "<a href=" not in summary_block.split(f"match-{r['id']}", 1)[1][:1400]]
    add("every unresolved summary row carries a source link", not unresolved_unsourced,
        f"rows without a source link: {unresolved_unsourced[:5]}")

    # --- mobile structure ----------------------------------------------------
    tabbar_missing = [p for p in pages
                      if os.path.exists(os.path.join(DOCS, p))
                      and 'class="tabbar"' not in open(os.path.join(DOCS, p), encoding="utf-8").read()]
    add("mobile tab bar on every page", not tabbar_missing, f"missing: {tabbar_missing[:5]}")

    viewport_missing = [p for p in pages
                        if os.path.exists(os.path.join(DOCS, p))
                        and 'name="viewport" content="width=device-width, initial-scale=1"' not in
                        open(os.path.join(DOCS, p), encoding="utf-8").read()]
    add("every page declares a mobile viewport", not viewport_missing, f"missing: {viewport_missing[:5]}")

    missing_anchors = [a for a in ("today", "next7", "past")
                       if f'id="{a}"' not in picks_html]
    day_groups = picks_html.count('class="daygroup"')
    add("picks page exposes today / next-7 / past anchors and day groups",
        not missing_anchors and day_groups >= 1,
        f"day groups={day_groups}; missing anchors={missing_anchors}")

    dup_ids = []
    for page in pages:
        path = os.path.join(DOCS, page)
        if not os.path.exists(path):
            continue
        ids = re.findall(r'\sid="([^"]+)"', open(path, encoding="utf-8").read())
        dupes_page = sorted({i for i in ids if ids.count(i) > 1})
        if dupes_page:
            dup_ids.append(f"{page}: {dupes_page[:4]}")
    add("no duplicate element ids on generated pages", not dup_ids, f"problems: {dup_ids[:4]}")

    meth_has_params = all(str(v) in meth_html for v in (
        (data.get("model") or {}).get("k_opening", ""),
        (data.get("model") or {}).get("k_series", ""),
        (data.get("model") or {}).get("mov_weight", "")))
    add("method page documents the published Elo hyper-parameters", meth_has_params,
        f"k_opening/k_series/mov_weight rendered: {meth_has_params}")

    recorded = [r for r in rows if r.get("recorded_result")]
    unsourced_results = [r["id"] for r in recorded
                         if not str((r["recorded_result"] or {}).get("source", "")).startswith(
                             "https://lol.fandom.com/")]
    add("recorded results carry a Leaguepedia source link", not unsourced_results,
        f"{len(recorded)} rows carry a recorded result; without source: {unsourced_results[:5]}")

    counts = Counter(r["method"] for r in rows)
    unverified = [r["id"] for r in rows if r["method"] in ("provisional", "unresolved")]
    report = {
        "generated_utc": iso(now_utc()),
        "checks": checks,
        "passed": all(c["ok"] for c in checks),
        "rows_checked": len(rows),
        "rows_with_source": len(rows) - len(missing_source),
        "rows_prob_ok": len(rows) - len(set(bad_prob)),
        "unverified": len(unverified),
        "counts": dict(counts),
        "internal_links": sum(hrefs.values()),
    }
    save_json(os.path.join(DATA, "verification.json"), report)

    for c in checks:
        print(("PASS " if c["ok"] else "FAIL ") + c["name"] + " :: " + c["detail"])
    if not report["passed"]:
        log("verification FAILED")
        sys.exit(1)
    log("verification passed")


if __name__ == "__main__":
    main()
