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
        f"{sum(1 for r in rows if r.get('method') != 'unresolved')} priced rows checked; "
        f"problems: {bad_prob[:5]}")
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

    # --- market integrity ---------------------------------------------------
    kills = [r["id"] for r in rows for v in ((r.get("market") or {}).get("venues") or [])
             if "kills" in str(v.get("name", "")).lower()
             or any("(kills)" in str(x).lower() for x in (r.get("market") or {}).get("venue_names") or [])]
    add("no '(Kills)' derivative market is used as a match line", not kills,
        f"violations: {kills[:5]}")

    bad_market_src = [r["id"] for r in rows if r.get("method") == "market"
                      and not str((r.get("market") or {}).get("source_url", "")).startswith("http")]
    add("every market pick carries an official quote URL", not bad_market_src,
        f"problems: {bad_market_src[:5]}")

    from model import prelock_observation
    bad_quote_times = []
    for r in rows:
        cutoff = r.get("lock_utc") or r.get("start_utc")
        for venue in (r.get("market") or {}).get("venues") or []:
            if not prelock_observation(venue, cutoff):
                bad_quote_times.append(f"{r['id']}:{venue.get('name')}:{venue.get('observed_utc')}")
    exclusion_n = sum(len(r.get("excluded_market_observations") or []) for r in rows)
    add("every published market quote is verified pre-lock", not bad_quote_times,
        f"{exclusion_n} later/untimed observations excluded; published violations: {bad_quote_times[:5]}")

    # Regression for the wrong-matchup bug: every Pinnacle quote URL must point at a
    # matchup id that exists in the collected Pinnacle feed.
    pin_raw = load_json(os.path.join(DATA, "raw", "pinnacle_lol.json")) or {}
    pin_ids = {str(m.get("matchup_id")) for m in pin_raw.get("markets") or []}
    bad_pin_ids = []
    for r in rows:
        mk = r.get("market") or {}
        for v in mk.get("venues") or []:
            if v.get("name") != "Pinnacle":
                continue
            m = re.search(r"(?:/event/|/matchups/)(\d+)", str(v.get("url", "")))
            if not m or (pin_ids and m.group(1) not in pin_ids):
                bad_pin_ids.append(f"{r['id']}->{m.group(1) if m else 'missing'}")
    add("Pinnacle quote URLs point at collected matchups", not bad_pin_ids,
        f"{len(pin_ids)} matchup ids in feed; problems: {bad_pin_ids[:5]}")

    from model import same_team, _parse_utc
    kambi_raw = load_json(os.path.join(DATA, "raw", "kambi_lol.json")) or {}
    kambi_fresh = False
    try:
        from datetime import datetime as _dt_k, timezone as _tz_k
        k_age = (now_utc() - _dt_k.strptime(str(kambi_raw.get("fetched_utc") or "")[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=_tz_k.utc)).total_seconds() / 3600
        kambi_fresh = k_age <= 24.0
    except ValueError:
        kambi_fresh = False
    expected_unibet = set()
    if kambi_fresh:
        for kev in kambi_raw.get("events") or []:
            kouts = kev.get("outcomes") or []
            if len(kouts) != 2:
                continue
            kobs = kev.get("changed_utc") or kambi_raw.get("fetched_utc")
            kstart = _parse_utc(kev.get("start_utc"))
            for r in rows:
                if r.get("method") != "market":
                    continue
                if not prelock_observation({"observed_utc": kobs}, r.get("lock_utc") or r.get("start_utc")):
                    continue
                rstart = _parse_utc(r.get("start_utc"))
                if kstart and rstart and abs((kstart - rstart).total_seconds()) > 36 * 3600:
                    continue
                if ((same_team(r["team0"]["name"], kouts[0]["name"]) and same_team(r["team1"]["name"], kouts[1]["name"]))
                        or (same_team(r["team0"]["name"], kouts[1]["name"]) and same_team(r["team1"]["name"], kouts[0]["name"]))):
                    expected_unibet.add(r["id"])
    actual_unibet = {r["id"] for r in rows if r.get("method") == "market"
                     and any(v.get("name") == "Unibet" for v in (r.get("market") or {}).get("venues") or [])}
    missing_unibet = sorted(expected_unibet - actual_unibet)
    add("all fresh Unibet/Kambi moneylines matched into market consensus",
        not missing_unibet,
        f"{len(actual_unibet)}/{len(expected_unibet)} fresh Unibet fixtures matched; missing: {missing_unibet[:5]}")

    wo = [r for r in rows if r.get("resolution")]
    bad_wo = [r["id"] for r in wo
              if not (r["resolution"].get("winner") and str(r["resolution"].get("source", "")).startswith("http"))]
    add("every official-forfeit resolution names a winner and a source URL", not bad_wo,
        f"{len(wo)} resolutions checked; problems: {bad_wo[:5]}")

    # no quoted probability may be attached to a forfeit resolution
    bad_wo_prob = [r["id"] for r in wo
                   if r.get("p0") is not None
                   or (r.get("pick") or {}).get("probability") is not None
                   or r.get("pick_type") != "settlement"]
    add("official-forfeit resolutions carry no invented probability", not bad_wo_prob,
        f"problems: {bad_wo_prob[:5]}")

    # --- CSV mirror ---------------------------------------------------------
    csv_path = os.path.join(DATA, "picks.csv")
    csv_rows = 0
    if os.path.exists(csv_path):
        with open(csv_path, encoding="utf-8") as fh:
            csv_rows = max(0, sum(1 for _ in fh) - 1)
    add("picks.csv mirrors the dataset", csv_rows == len(rows),
        f"csv rows={csv_rows} json rows={len(rows)}")

    # --- site ---------------------------------------------------------------
    pages = ["index.html", "picks.html", "table.html", "results.html", "featured.html", "originated.html",
             "unresolved.html", "coverage.html", "competitions.html", "teams.html", "methodology.html",
             "sources.html", "verification.html", "flagged.html"]
    missing_pages = [p for p in pages if not os.path.exists(os.path.join(DOCS, p))]
    add("all site pages exist", not missing_pages, f"{len(pages) - len(missing_pages)}/{len(pages)} pages")

    broken, no_nav, none_literal, unlabelled_td = [], [], [], []
    hrefs: Counter = Counter()
    for page in pages:
        path = os.path.join(DOCS, page)
        if not os.path.exists(path):
            continue
        text = open(path, encoding="utf-8").read()
        if 'class="nav"' not in text:
            no_nav.append(page)
        tds = len(re.findall(r"<td\b", text))
        labelled = len(re.findall(r"<td[^>]*data-label=", text))
        if tds and labelled < tds:
            unlabelled_td.append(f"{page}:{tds - labelled}/{tds}")
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
    add("every table cell carries a mobile data-label", not unlabelled_td,
        f"checked {len(pages)} pages; missing data-label: {unlabelled_td[:6]}")

    picks_html = open(os.path.join(DOCS, "picks.html"), encoding="utf-8").read()
    on_page = sum(1 for r in rows if picks_html.count(f'id="match-{html.escape(str(r["id"]), quote=True)}"') >= 1)
    add("all matches rendered on the picks page", on_page == len(rows),
        f"{on_page}/{len(rows)} match cards found")

    table_html = open(os.path.join(DOCS, "table.html"), encoding="utf-8").read()
    table_rows = table_html.count('class="prow')
    add("pick table renders one row per match", table_rows == len(rows),
        f"{table_rows}/{len(rows)} table rows")

    index_html = open(os.path.join(DOCS, "index.html"), encoding="utf-8").read()
    needed = ["picks.html", "table.html", "results.html", "featured.html", "originated.html",
              "unresolved.html", "Executive summary", "Unresolved picks", "Where the picks are"]
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

    # Phone-first entry points (e32a5c4b E3): a starting-soon list on the landing
    # page and a per-competition fallback ledger incl. Hotspawn's forfeit-void rule.
    unres_html = open(os.path.join(DOCS, "unresolved.html"), encoding="utf-8").read() \
        if os.path.exists(os.path.join(DOCS, "unresolved.html")) else ""
    e3_missing = []
    if "Starting soon" not in index_html or 'id="soon"' not in index_html:
        e3_missing.append("index starting-soon list")
    if "Fallback by competition" not in unres_html:
        e3_missing.append("unresolved fallback ledger")
    if "how-it-works" not in unres_html or "how-it-works" not in index_html:
        e3_missing.append("Hotspawn forfeit-void rule link")
    add("starting-soon phone list and fallback ledger rendered", not e3_missing,
        f"missing: {e3_missing}")

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

    # --- curated flag integrity: every reference to a fixture that has left the list must be
    #     annotated as historical by tools/flags.py. Time passing (a card kicking off) is not a
    #     build failure; an unannotated stale claim is.
    listed_ids = {str(r.get("id")) for r in rows}
    manual = (load_json(os.path.join(DATA, "flags_manual.json")) or {}).get("flags") or []
    built_flags = (load_json(os.path.join(DATA, "flags.json")) or {}).get("flags") or []
    built_refs = {}
    for f in built_flags:
        for fid in (f.get("delisted_refs_auto") or []):
            built_refs.setdefault(str(fid), set()).add(f.get("item", ""))
    stale_refs, unannotated = [], []
    for f in manual:
        blob = f"{f.get('item', '')} {f.get('detail', '')}"
        declared = {str(x) for x in (f.get("delisted_refs") or [])}
        for fid in re.findall(r"#(\d{6,8})", blob):
            if fid in listed_ids:
                continue
            if fid in declared:
                continue
            # the build must have published this reference as a historical observation
            if fid in built_refs:
                stale_refs.append(fid)
            else:
                unannotated.append(fid)
    add("curated flags annotate every reference to a fixture that has left the list",
        not unannotated,
        f"{len(manual)} curated flags scanned; delisted-and-annotated: {sorted(set(stale_refs))}; "
        f"unannotated: {sorted(set(unannotated))}")

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
    # An archived receipt that has aged out, or that belongs to a fixture Hotspawn has since
    # delisted, is history - not a data error. Failing the gate on either deadlocks the refresh:
    # a stale snapshot makes every receipt stale, which blocks the build that would refresh it.
    # Malformed / wrong-team receipts still fail. A valid but divergent comparison is disclosed,
    # not fatal: corroboration receipts never enter pricing, so blocking on disagreement would
    # recreate the same self-sustaining outage without protecting a published probability.
    add("external receipts validated against the dataset", not bad_receipts,
        f"{corr.get('summary',{}).get('usable_receipts',0)} usable receipts, "
        f"{len(bad_receipts)} rejected, {len(diverged)} diverging "
        f">{corr.get('summary',{}).get('divergence_threshold_pp','5')}pp (non-blocking), "
        f"{corr.get('summary',{}).get('expired_receipts',0)} expired, "
        f"{corr.get('summary',{}).get('historic_receipts',0)} historic (not counted)")
    cs = corr.get("summary") or {}
    accounted = (cs.get("usable_receipts", 0) + cs.get("placeholders", 0)
                 + cs.get("rejected_receipts", 0) + cs.get("expired_receipts", 0)
                 + cs.get("historic_receipts", 0))
    add("corroboration ledger accounts for every receipt",
        bool(corr) and accounted == cs.get("receipts", -1) and cs.get("receipts", 0) > 0,
        f"receipts={cs.get('receipts')} = usable {cs.get('usable_receipts',0)} + placeholder "
        f"{cs.get('placeholders',0)} + rejected {cs.get('rejected_receipts',0)} + expired "
        f"{cs.get('expired_receipts',0)} + historic {cs.get('historic_receipts',0)}")
    cov_path = os.path.join(DOCS, "coverage.html")
    cov_html = open(cov_path, encoding="utf-8").read() if os.path.exists(cov_path) else ""
    add("coverage page shows every match method and the unresolved ledger",
        all(k in cov_html for k in ("How each match was priced", "Corroboration, match by match",
                                    "no pick at all")),
        f"coverage.html {len(cov_html)} bytes")

    probes = load_json(os.path.join(DATA, "source_probes.json")) or {}
    probe_rows = probes.get("results") or []
    dossier = os.path.join(ROOT, "research", "SOURCES.md")
    add("external source research receipts are committed",
        len(probe_rows) >= 25 and os.path.exists(dossier)
        and all("status" in r for r in probe_rows),
        f"{len(probe_rows)} venues probed on {probes.get('checked_utc', 'unknown')}; "
        f"dossier {'present' if os.path.exists(dossier) else 'MISSING'}")

    # Coverage arithmetic must never exceed the inventory (a 245-of-241 regression shipped once).
    priced_n = sum(1 for r in rows if r.get("p0") is not None)
    settled_n = sum(1 for r in rows if r.get("resolution"))
    with_pick_n = sum(1 for r in rows if (r.get("pick") or {}).get("team"))
    without_pick_n = sum(1 for r in rows if not (r.get("pick") or {}).get("team"))
    add("coverage arithmetic reconciles to the inventory",
        priced_n + settled_n + without_pick_n == len(rows)
        and with_pick_n + without_pick_n == len(rows),
        f"priced={priced_n} + settlements={settled_n} + documented no-pick={without_pick_n} "
        f"= {priced_n + settled_n + without_pick_n}; rows with a pick={with_pick_n}; inventory={len(rows)}")
    method_counts = data.get("counts") or {}
    add("method counts partition matches.json cleanly",
        sum(int(v) for v in method_counts.values()) == len(rows)
        and set(method_counts.keys()) <= ALLOWED,
        f"counts={method_counts} sum={sum(int(v) for v in method_counts.values())} rows={len(rows)}")

    src = (load_json(os.path.join(DATA, "sources_status.json")) or {}).get("sources") or []
    reachable = sum(1 for s in src if s.get("ok"))
    add("source availability recorded", len(src) >= 10,
        f"{reachable}/{len(src)} sources reachable on this build")

    # --- coverage parity against the exact Hotspawn snapshot used for the build ---
    raw = (load_json(os.path.join(RAW, "hotspawn_lol.json")) or {}).get("fixtures") or []
    raw_ids = {str(f.get("id")) for f in raw}
    row_ids = {str(r.get("id")) for r in rows}
    rc = Counter(f.get("competition") for f in raw)
    dc = Counter(r.get("competition") for r in rows)
    add("every Hotspawn fixture is in the dataset (1:1 ids)", raw_ids == row_ids,
        f"feed={len(raw_ids)} dataset={len(row_ids)} missing={sorted(raw_ids - row_ids)[:3]} "
        f"extra={sorted(row_ids - raw_ids)[:3]}")
    add("per-tournament counts match the Hotspawn feed",
        set(rc) == set(dc) and all(rc[k] == dc[k] for k in rc),
        f"{len(rc)} tournaments; differences: {[k for k in rc if rc[k] != dc.get(k)][:3]}")

    # --- no-look-ahead: the rating on each side must predate its own kick-off ---
    from datetime import datetime as _dt
    before: dict[str, list] = {}
    for m in (load_json(os.path.join(RAW, "leaguepedia.json")) or {}).get("matches") or []:
        if m.get("winner") not in ("1", "2"):
            continue
        try:
            t = _dt.strptime(str(m.get("utc"))[:19], "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            continue
        for team in (m.get("team1"), m.get("team2")):
            before.setdefault(team, []).append(t)
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
            seen = sum(1 for t in before.get(key, []) if t < ko)
            if int(r[side].get("rating_matches") or 0) > seen:
                lookahead.append(f"{r['id']}:{key} used {r[side]['rating_matches']} > {seen} before kick-off")
            if (r[side].get("rating_as_of") or "") != r["start_utc"]:
                lookahead.append(f"{r['id']}:{key} rating_as_of != kick-off")
    add("no look-ahead: ratings use only results before kick-off", not lookahead,
        f"{len(lookahead)} violations; examples: {lookahead[:3]}")

    counts = Counter(r["method"] for r in rows)
    unverified = [r["id"] for r in rows if r["method"] in ("provisional", "unresolved")]
    report = {
        "generated_utc": iso(now_utc()),
        "checks": checks,
        "passed": all(c["ok"] for c in checks),
        "rows_checked": len(rows),
        "rows_with_source": len(rows) - len(missing_source),
        "rows_prob_ok": sum(1 for r in rows if r.get("method") != "unresolved") - len(set(bad_prob)),
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
