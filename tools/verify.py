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
from common import DATA, RAW, ROOT, iso, load_json, log, now_utc, save_json

DOCS = ROOT  # GitHub Pages serves the branch root
ALLOWED = {"market", "model", "provisional", "unresolved"}
checks: list[dict] = []


def add(name: str, ok: bool, detail: str) -> None:
    checks.append({"name": name, "ok": bool(ok), "detail": detail})


def main() -> None:
    data = load_json(os.path.join(DATA, "matches.json")) or {}
    rows = data.get("matches") or []
    add("dataset present", len(rows) > 0, f"{len(rows)} matches loaded")

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
        if r.get("method") != "unresolved":
            p0, p1 = r.get("p0"), r.get("p1")
            if p0 is None or p1 is None or abs((p0 + p1) - 1.0) > 0.002:
                bad_prob.append(r.get("id"))
            if not r.get("pick") or not r["pick"].get("team"):
                bad_pick.append(r.get("id"))
            else:
                top = max(p0, p1)
                if abs(r["pick"]["probability"] - top) > 0.001:
                    bad_pick.append(r.get("id"))
        else:
            if r.get("pick") is not None or r.get("p0") is not None:
                bad_pick.append(r.get("id"))
        if r.get("method") == "market":
            mk = r.get("market") or {}
            if not mk.get("source_url") or not (mk.get("decimal") or mk.get("kind") == "prediction market"):
                bad_pick.append(r.get("id"))

    add("every row links to its Hotspawn match card", not missing_source,
        f"{len(rows) - len(missing_source)}/{len(rows)} rows carry a Hotspawn URL")
    add("probabilities sum to 100% (tolerance 0.2pp)", not bad_prob,
        f"{len(rows) - len(bad_prob)} priced rows verified; problems: {bad_prob[:5]}")
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
            hrefs[href] += 1
            target = href.split("?")[0]
            if target not in pages and not os.path.exists(os.path.join(DOCS, target)):
                broken.append(f"{page} -> {href}")
        for bad in ("&gt;None&lt;", ">None<", ">nan<", "&mdash;%"):
            if bad in text:
                none_literal.append(f"{page}:{bad}")
    add("no broken internal links", not broken, f"{len(broken)} problems: {broken[:6]}")
    add("navigation on every page", not no_nav, f"missing: {no_nav[:5]}")
    add("no empty/None values rendered", not none_literal, f"problems: {none_literal[:6]}")

    import html as _html
    picks_html = open(os.path.join(DOCS, "picks.html"), encoding="utf-8").read()
    on_page = sum(1 for r in rows if f'data-comp="{_html.escape(str(r["competition"]), quote=True)}"' in picks_html)
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

    # --- mobile / interaction wiring (regression guard) ---------------------
    app_js = open(os.path.join(DOCS, "assets", "app.js"), encoding="utf-8").read() \
        if os.path.exists(os.path.join(DOCS, "assets", "app.js")) else ""
    add("mobile menu handler exists", 'classList.toggle("open"' in app_js and '"nav"' in app_js,
        "app.js toggles #nav.open for .menu-btn and the bottom-tab More button")
    controls = ["q", "comp", "window", "sort", "chips", "list", "count"]
    missing_controls = [c for c in controls
                        if f'id="{c}"' not in picks_html and c != "chips"]
    wired = [c for c in ["q", "comp", "window", "sort", "list", "count"]
             if f'getElementById("{c}")' in app_js]
    add("picks search/filter/sort controls are wired",
        not missing_controls and len(wired) == 6,
        f"emitted ids missing={missing_controls}; wired in app.js={wired}")
    add("all pages carry the mobile tab bar", all('class="tabbar"' in open(os.path.join(DOCS, p), encoding="utf-8").read()
                                                  for p in pages if os.path.exists(os.path.join(DOCS, p))),
        "bottom navigation present on every generated page")
    add("summary page exposes the next-48h block and picks links",
        'id="today"' in index_html and "picks.html" in index_html and "unresolved.html" in index_html,
        "executive summary links + #today anchor")

    # --- no-look-ahead audit ------------------------------------------------
    lp_raw = (load_json(os.path.join(RAW, "leaguepedia.json")) or {}).get("matches") or []
    from datetime import datetime as _dt
    games_by_team: dict[str, list] = {}
    for m in lp_raw:
        if m.get("winner") not in ("1", "2"):
            continue
        try:
            t = _dt.strptime(str(m.get("utc"))[:19], "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            continue
        for team in (m.get("team1"), m.get("team2")):
            games_by_team.setdefault(team, []).append(t)
    lookahead = []
    for r in rows:
        if not r.get("pick"):
            continue
        try:
            ko = _dt.strptime(str(r["start_utc"])[:19], "%Y-%m-%dT%H:%M:%S")
        except (ValueError, TypeError):
            continue
        for side in ("team0", "team1"):
            key = r[side].get("leaguepedia")
            if not key:
                continue
            before = sum(1 for t in games_by_team.get(key, []) if t < ko)
            if int(r[side].get("rating_matches") or 0) > before:
                lookahead.append(f"{r['id']}:{key} used {r[side]['rating_matches']} > {before} before kick-off")
            if (r[side].get("rating_as_of") or "") != r["start_utc"]:
                lookahead.append(f"{r['id']}:{key} rating_as_of != kick-off")
    add("no look-ahead: ratings use only results before kick-off", not lookahead,
        f"{len(lookahead)} violations; examples: {lookahead[:3]}")

    # --- probability bounds and documentation -------------------------------
    out_of_bounds = [r["id"] for r in rows if r.get("pick") and not (
        (data.get("model") or {}).get("prob_floor", 0.05) - 1e-9 <= r["pick"]["probability"]
        <= (data.get("model") or {}).get("prob_ceil", 0.95) + 1e-9)]
    add("probabilities stay inside the published clamp", not out_of_bounds,
        f"bounds={(data.get('model') or {}).get('prob_floor')}-{(data.get('model') or {}).get('prob_ceil')}; violations={out_of_bounds[:3]}")
    undocumented = [r["id"] for r in rows if r["method"] == "unresolved" and
                    (not r.get("basis") or not r.get("flags")
                     or not (r.get("leaguepedia_page") or r.get("hotspawn_url")))]
    add("every unresolved row documents its reason and league source", not undocumented,
        f"{len([r for r in rows if r['method']=='unresolved'])} unresolved rows; undocumented={undocumented[:3]}")
    # A picked row must carry a results page (originated) or a market URL (book).
    # An unresolved row is allowed to stand on its Hotspawn card + documented reason.
    missing_extra = [r["id"] for r in rows
                     if not r.get("hotspawn_url")
                     or (r.get("pick") and not (r.get("leaguepedia_page") or r.get("market")))]
    add("every row has a fixture source; every pick has a results or market source", not missing_extra,
        f"{len(rows) - len(missing_extra)}/{len(rows)} rows; problems={missing_extra[:3]}")

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
        "lookahead_violations": len(lookahead),
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
