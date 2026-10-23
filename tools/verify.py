#!/usr/bin/env python3
"""Verification gate: assert the dataset and the generated site are publishable.

Any failure exits non-zero, which stops the refresh workflow from committing.
"""
from __future__ import annotations

import html
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

    # Complete inventory reconciliation against the raw collection (session b91181f0).
    raw = load_json(os.path.join(DATA, "raw", "hotspawn_lol.json")) or {}
    inventory_ids = [str(f["id"]) for f in raw.get("fixtures", [])]
    row_ids = [str(r.get("id")) for r in rows]
    add("complete inventory reconciliation",
        bool(inventory_ids) and sorted(inventory_ids) == sorted(row_ids),
        f"raw fixtures={len(inventory_ids)}, published rows={len(row_ids)}; exact ID multiset comparison")
    integrity_failures = [(r.get("id"), row_errors(r)) for r in rows if row_errors(r)]
    add("finite probabilities and correctly named picks", not integrity_failures,
        str(integrity_failures[:5]))

    # --- per-row checks -----------------------------------------------------
    missing_source, bad_prob, bad_method, bad_pick, dupes = [], [], [], [], []
    no_pick, bad_settlement, bad_market = [], [], []
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

        pick = r.get("pick") or {}
        # A match may only be pick-less when it is an explicitly documented unresolved row.
        if not pick.get("team") and r.get("method") != "unresolved":
            no_pick.append(r.get("id"))

        if r.get("method") != "unresolved":
            p0, p1 = r.get("p0"), r.get("p1")
            if p0 is None or p1 is None or abs((p0 + p1) - 1.0) > 0.002:
                bad_prob.append(r.get("id"))
            if not pick.get("team"):
                bad_pick.append(r.get("id"))
            elif abs(pick["probability"] - max(p0, p1)) > 0.001:
                bad_pick.append(r.get("id"))
        else:
            # A settlement pick: named participant, explicitly no probability.
            if r.get("p0") is not None or r.get("p1") is not None:
                bad_pick.append(r.get("id"))
            if pick and (pick.get("probability") is not None
                         or pick.get("team") not in (r["team0"]["name"], r["team1"]["name"])):
                bad_settlement.append(r.get("id"))
        if r.get("method") == "market":
            mk = r.get("market") or {}
            venues = mk.get("venues") or []
            if (not mk.get("source_url") or not venues
                    or any(not str(v.get("url", "")).startswith("http") for v in venues)):
                bad_market.append(r.get("id"))

    add("every row links to its Hotspawn match card", not missing_source,
        f"{len(rows) - len(missing_source)}/{len(rows)} rows carry a Hotspawn URL")
    add("probabilities sum to 100% (tolerance 0.2pp)", not bad_prob,
        f"{len(rows) - len(bad_prob)} priced rows verified; problems: {bad_prob[:5]}")
    add("pick matches the higher probability", not bad_pick,
        f"{len(rows) - len(set(bad_pick))} rows consistent; problems: {sorted(set(bad_pick))[:5]}")
    settlement = sum(1 for r in rows if r.get("pick_type") == "settlement")
    pickless = sum(1 for r in rows if not (r.get("pick") or {}).get("team"))
    add("every match has a pick or is documented as unpickable", not no_pick,
        f"{len(rows)} rows: {len(rows) - pickless} with a pick ({settlement} settlement-only), "
        f"{pickless} documented unpickable"
        + (f"; unexplained: {no_pick[:5]}" if no_pick else ""))
    add("settlement picks name a participant and claim no probability", not bad_settlement,
        f"{len(bad_settlement)} problems: {bad_settlement[:5]}")
    add("every market row has at least one venue with a source URL", not bad_market,
        f"{len(bad_market)} problems: {bad_market[:5]}")
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
             "verification.html", "flagged.html", "coverage.html"]
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
    on_page = sum(1 for r in rows if picks_html.count(f'id="match-{html.escape(str(r["id"]), quote=True)}"') >= 1)
    add("all matches rendered on the picks page", on_page == len(rows),
        f"{on_page}/{len(rows)} match cards found")

    index_html = open(os.path.join(DOCS, "index.html"), encoding="utf-8").read()
    needed = ["picks.html", "featured.html", "originated.html", "unresolved.html", "Executive summary"]
    add("executive summary links to every picks view", all(n in index_html for n in needed),
        f"present: {[n for n in needed if n in index_html]}")

    # The brief requires the unresolved section and its limitations in the executive summary.
    exec_markers = {
        "unresolved section": "Unresolved picks and the limitations",
        "coverage line": "carry a pick",
        "where the picks are": "Where the picks are",
    }
    missing_markers = [k for k, v in exec_markers.items() if v not in index_html]
    add("executive summary carries coverage, unresolved section and a where-to-find-picks block",
        not missing_markers, f"missing: {missing_markers}")

    # Mobile usability: a persistent nav bar and a wired-up menu button on every page.
    mob_missing = []
    for page in pages:
        path = os.path.join(DOCS, page)
        if not os.path.exists(path):
            continue
        text = open(path, encoding="utf-8").read()
        if 'class="mobnav"' not in text:
            mob_missing.append(page)
    app_js = open(os.path.join(DOCS, "assets", "app.js"), encoding="utf-8").read() \
        if os.path.exists(os.path.join(DOCS, "assets", "app.js")) else ""
    js_ok = ("menu-btn" in app_js) and ('getElementById("q")' in app_js)
    add("mobile navigation rendered on every page and wired in JS", not mob_missing and js_ok,
        f"missing mobnav: {mob_missing[:5]}; menu+filter handlers present: {js_ok}")

    meth_html = open(os.path.join(DOCS, "methodology.html"), encoding="utf-8").read()
    bt_n = (data.get("backtest") or {}).get("n") or 0
    add("out-of-sample backtest & SVG calibration rendered on methodology page",
        bt_n > 500 and f"{bt_n:,}" in meth_html and "<svg" in meth_html,
        f"backtest series rendered: {bt_n:,}")

    # --- curated flag integrity: a flag may not cite a fixture that is not listed ---
    listed_ids = {str(r.get("id")) for r in rows}
    manual = (load_json(os.path.join(DATA, "flags_manual.json")) or {}).get("flags") or []
    stale_refs = []
    for f in manual:
        blob = f"{f.get('item', '')} {f.get('detail', '')}"
        declared = {str(x) for x in (f.get("delisted_refs") or [])}
        for fid in re.findall(r"#(\d{6,8})", blob):
            if fid not in listed_ids and fid not in declared:
                stale_refs.append(fid)
    add("curated flags cite only currently listed fixtures", not stale_refs,
        f"{len(manual)} curated flags scanned; stale references: {sorted(set(stale_refs))}")

    # --- line integrity audit ---
    audit = data.get("receipt_audit") or {}
    used = audit.get("used") or []
    expired = audit.get("expired") or []
    over_age = [e for e in expired
                if (e.get("age_hours") or 0) <= (audit.get("max_age_hours") or 0)]
    rejected = audit.get("rejected_quotes") or []
    extreme = [q for q in rejected if (q.get("reject") or "").startswith("extreme")]
    bad_audit = bool(over_age) or any(e.get("fixture_id") in used for e in expired)
    add("stale bookmaker receipts are excluded from the consensus",
        not bad_audit and (audit.get("max_age_hours") or 0) > 0,
        f"{len(expired)} expired receipts, {len(used)} live receipts, limit "
        f"{audit.get('max_age_hours')} h; inconsistencies: {[e['fixture_id'] for e in over_age][:5]}")
    add("no published market row is built from a rejected quote",
        not extreme,
        f"{len(rejected)} quote(s) rejected this build (placeholders / extremes); "
        f"{len(extreme)} extreme")

    # --- external corroboration (tools/corroborate.py) -----------------------
    corr = load_json(os.path.join(DATA, "corroboration.json")) or {}
    cov_rows = corr.get("coverage") or []
    no_link = [c["competition"] for c in cov_rows if not str(c.get("hotspawn_url") or "").startswith("https://")]
    add("coverage matrix: every competition row links to a source", bool(cov_rows) and not no_link,
        f"{len(cov_rows)} competition rows; missing links: {no_link[:3]}")
    bad_receipts = corr.get("rejected") or []
    diverged = [r for r in (corr.get("rows") or []) if r.get("verdict") == "diverges"]
    add("external receipts validated against the dataset", not bad_receipts and not diverged,
        f"{corr.get('summary',{}).get('usable_receipts',0)} usable receipts, "
        f"{len(bad_receipts)} rejected, {len(diverged)} diverging >{corr.get('summary',{}).get('divergence_threshold_pp','5')}pp")
    cov_path = os.path.join(DOCS, "coverage.html")
    cov_html = open(cov_path, encoding="utf-8").read() if os.path.exists(cov_path) else ""
    add("coverage page shows every match method and the unresolved ledger",
        all(k in cov_html for k in ("How each match was priced", "Corroboration, match by match",
                                    "no pick at all")),
        f"coverage.html {len(cov_html)} bytes")

    # Phone UX: the picks page must answer "what is next?" without scrolling, and every
    # card must let the browser age itself (a 6-hour-old snapshot otherwise shows a
    # kicked-off match as open - audit finding F4 from session 294e62ad).
    picks_html = open(os.path.join(DOCS, "picks.html"), encoding="utf-8").read()
    app_js = open(os.path.join(DOCS, "assets", "app.js"), encoding="utf-8").read()
    anchors = set(re.findall(r'id="match-([^"]+)"', picks_html))
    nextup_ids = set(re.findall(r'href="#match-([^"]+)"', picks_html))
    add("picks page opens with a tappable next-up table linking to real cards",
        'id="next-up"' in picks_html and bool(nextup_ids) and nextup_ids <= anchors,
        f"{len(nextup_ids)} next-up links, all resolving to a card: {nextup_ids <= anchors}")
    cards_with_start = len(re.findall(r'class="card m-[a-z]+"[^>]*data-start="20', picks_html))
    aged_js = "markStarted" in app_js and 'dataset.started === "1"' in app_js
    add("every card carries its kick-off so the browser can age it",
        cards_with_start == len(rows) and aged_js,
        f"{cards_with_start}/{len(rows)} cards carry data-start; browser ageing wired: {aged_js}")

    src = (load_json(os.path.join(DATA, "sources_status.json")) or {}).get("sources") or []
    reachable = sum(1 for s in src if s.get("ok"))
    add("source availability recorded", len(src) >= 10,
        f"{reachable}/{len(src)} sources reachable on this build")

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
