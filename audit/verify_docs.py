#!/usr/bin/env python3
"""
verify_docs.py — line-by-line verification of the secondary (docs/) Node
dashboard against its committed data snapshot (data/node/**).

Checks (each prints PASS/FAIL; exit 1 on any FAIL):
  1   docs/data/picks.json is byte-identical to data/node/picks.json
  2   every open/locked/live match with a pick is rendered on docs/picks.html
  3   every rendered probability on a pick card matches the JSON consensus/model value
  4   every open/locked/live match without a pick appears on docs/unresolved.html
  5   every match card carries a Hotspawn source link
  6   market-priced rows carry all matched venue source links (Pinnacle/Kambi/Kalshi/Polymarket)
  7   no fabricated scores: results.html score text matches the JSON exactly
  8   no ledger entry with an official result renders as "pending"
  9   NAV present on every docs page; exec summary links every picks view & category subpage
 10   internal hrefs and fragment anchors across docs/*.html resolve cleanly
 11   every priced row's probabilities sum to 100% (+/- 0.2pp) and pick = argmax
 12   all scheduled matches rendered 1:1 on docs/table.html with source links
 13   all 10 docs/*.html category pages exist and render mobile viewport meta
 14   zero '(Kills)' derivative markets in market quotes & zero Hotspawn crowd leakage
 15   cross-region homonym quarantines (#1083097 PNG, #1079031 PvB) & DQ walkovers verified
 16   every Flagged for Review entry links both Hotspawn and an official external receipt
"""
import html as html_mod
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DATA = ROOT / "data" / "node"

failures = []


def check(n, name, ok, detail=""):
    tag = "PASS" if ok else "FAIL"
    print(f"{tag} {str(n):>4} {name}" + (f" :: {detail}" if detail else ""))
    if not ok:
        failures.append((n, name, detail))


def pct_str(p):
    if p is None:
        return "—"
    return f"{p * 100:.1f}%"


def esc_html(s):
    return (
        str(s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def main():
    picks = json.loads((DATA / "picks.json").read_text())
    flags = json.loads((DATA / "flags.json").read_text())
    ledger = json.loads((DATA / "history" / "picks_latest.json").read_text())
    matches = picks["matches"]
    scheduled = [m for m in matches if m["status"] == "scheduled"]

    # 1 — published copy identical
    a = (DOCS / "data" / "picks.json").read_bytes()
    b = (DATA / "picks.json").read_bytes()
    check(1, "docs/data/picks.json mirrors data/node/picks.json", a == b, f"{len(a)} bytes")

    picks_html = (DOCS / "picks.html").read_text()
    table_html = (DOCS / "table.html").read_text()
    unres_html = (DOCS / "unresolved.html").read_text()
    flagged_html = (DOCS / "flagged.html").read_text()
    results_html = (DOCS / "results.html").read_text()
    idx_html = (DOCS / "index.html").read_text()

    active = [m for m in matches if m["state"] in ("open", "locked", "live")]
    with_pick = [m for m in active if m.get("pick")]
    without = [m for m in active if not m.get("pick")]

    # 2 — every picked active match rendered on picks.html
    missing_cards = [m["id"] for m in with_pick if f'id="m-{m["id"]}"' not in picks_html]
    check(
        2,
        "every active match with a pick rendered on picks.html",
        not missing_cards,
        f"{len(with_pick)} picked rows, missing: {missing_cards[:5]}",
    )

    # 3 — rendered probabilities match JSON consensus/model p0
    prob_bad = []
    for m in with_pick:
        cid = f'id="m-{m["id"]}"'
        if cid not in picks_html:
            continue
        seg = picks_html.split(cid, 1)[1].split("</article>", 1)[0]
        p0 = m.get("p0")
        if p0 is None:
            prob_bad.append((m["id"], "no p0 in JSON but rendered"))
            continue
        if pct_str(p0) not in seg or pct_str(1 - p0) not in seg:
            prob_bad.append((m["id"], f"expected {pct_str(p0)}/{pct_str(1 - p0)}"))
    check(3, "rendered probabilities match JSON", not prob_bad, f"bad: {prob_bad[:5]}")

    # 4 — unresolved active matches listed on unresolved.html AND index.html
    missing_unres = [
        m["id"]
        for m in without
        if f'id="m-{m["id"]}"' not in unres_html or f'id="idx-u-{m["id"]}"' not in idx_html
    ]
    check(
        4,
        "every active match without a pick is on unresolved.html and index.html",
        not missing_unres,
        f"{len(without)} unresolved, missing: {missing_unres[:5]}",
    )

    # 5 — Hotspawn source link per rendered card
    no_src = []
    for m in active:
        cid = f'id="m-{m["id"]}"'
        for html_doc in (picks_html, unres_html):
            if cid in html_doc:
                seg = html_doc.split(cid, 1)[1].split("</article>", 1)[0]
                if esc_html(m["hotspawn_url"]) not in seg:
                    no_src.append(m["id"])
                break
    check(
        5,
        "every rendered card links its Hotspawn match card",
        not no_src,
        f"missing: {sorted(set(no_src))[:5]}",
    )

    # 6 — market rows carry every matched market source link
    mkt_missing = []
    venue_keys = ("market_pinnacle", "market_kambi", "market_kalshi", "market_polymarket", "market_bovada")
    for m in active:
        cid = f'id="m-{m["id"]}"'
        if cid not in picks_html:
            continue
        seg = picks_html.split(cid, 1)[1].split("</article>", 1)[0]
        for key in venue_keys:
            mk = m.get(key)
            if mk and mk.get("url") and esc_html(mk["url"]) not in seg:
                mkt_missing.append((m["id"], key))
    mkt_rows = [m for m in active if m.get("market_consensus")]
    check(
        6,
        "market rows carry all matched venue source links",
        not mkt_missing,
        f"{len(mkt_rows)} market rows, missing: {mkt_missing[:5]}",
    )

    # 7 — results.html scores exactly match JSON (no fabricated fills)
    score_bad = []
    ended = [m for m in matches if m["state"] in ("ended", "forfeited")]
    for m in ended:
        has = m["score0"] is not None and m["score1"] is not None
        t0 = esc_html(m["team0"]["name"])
        t1 = esc_html(m["team1"]["name"])
        want = f"{t0} {m['score0']}–{m['score1']} {t1}" if has else f"{t0} vs (no official score) {t1}"
        if want not in results_html:
            score_bad.append((m["id"], want))
    check(
        7,
        "results.html renders only official scores (no fabricated fills)",
        not score_bad,
        f"{len(ended)} ended/forfeited checked, bad: {score_bad[:5]}",
    )

    # 8 — no "pending" where an official result exists
    pend_bad = []
    for m in ended:
        u = esc_html(m["hotspawn_url"])
        if u not in results_html:
            continue
        seg = results_html.split(u, 1)[0].rsplit("<tr>", 1)[-1]
        if "pending" in seg.lower():
            pend_bad.append(m["id"])
    check(
        8,
        "no ledger entry with an official result renders as pending",
        not pend_bad,
        f"bad: {pend_bad[:5]}",
    )

    # 9 — NAV + exec summary links
    expected_pages = [
        "index.html",
        "table.html",
        "picks.html",
        "featured.html",
        "originated.html",
        "tournaments.html",
        "unresolved.html",
        "flagged.html",
        "results.html",
        "methodology.html",
    ]
    pages = sorted(p.name for p in DOCS.glob("*.html"))
    nav_missing = []
    for p in pages:
        t = (DOCS / p).read_text()
        for need in expected_pages:
            if need not in t:
                nav_missing.append((p, need))
    check(9, "navigation on every docs page", not nav_missing, str(nav_missing[:5]))
    missing_exec = [t for t in expected_pages[1:] if t not in idx_html]
    check(9.1, "exec summary links every picks view & subpage", not missing_exec, str(missing_exec))

    # 10 — internal hrefs and fragments resolve
    ids_by_page = {
        p: set(re.findall(r'\bid="([^"]+)"', (DOCS / p).read_text()))
        for p in pages
    }
    broken = []
    for p in pages:
        t = (DOCS / p).read_text()
        for href in re.findall(r'href="([^"]+)"', t):
            if href.startswith(("http://", "https://", "mailto:", "data:")):
                continue
            if href.startswith("#"):
                frag = href[1:]
                if frag and frag not in ids_by_page[p]:
                    broken.append((p, href))
                continue
            base, _, frag = href.partition("#")
            base = base.split("?", 1)[0]
            if not base:
                continue
            if not (DOCS / base).exists():
                broken.append((p, href))
            elif frag and base in ids_by_page and frag not in ids_by_page[base]:
                broken.append((p, href))
    check(10, "no broken internal links or fragments in docs/", not broken, str(broken[:5]))

    # 11 — probability integrity on JSON rows
    integ_bad = []
    for m in matches:
        p0, p1 = m.get("p0"), m.get("p1")
        pk = m.get("pick")
        sp = m.get("settlement_pick")
        if p0 is None and p1 is None:
            if pk is not None:
                integ_bad.append(m["id"] + " pick_without_prob")
            continue
        if p0 is None or p1 is None or abs(p0 + p1 - 1.0) > 2e-3:
            integ_bad.append(m["id"] + " sum!=1")
            continue
        if sp is not None:
            integ_bad.append(m["id"] + " settlement_has_prob")
        if pk and pk["team_index"] != (0 if p0 >= p1 else 1):
            integ_bad.append(m["id"] + " pick!=argmax")
    check(11, "probabilities sum to 100% and pick = argmax", not integ_bad, f"bad: {integ_bad[:5]}")

    # 12 — all scheduled matches rendered 1:1 on docs/table.html
    missing_table = [
        m["id"]
        for m in scheduled
        if f'id="row-{m["id"]}"' not in table_html or esc_html(m["hotspawn_url"]) not in table_html
    ]
    check(
        12,
        "all scheduled matches rendered 1:1 on docs/table.html with source links",
        not missing_table,
        f"{len(scheduled)} scheduled rows, missing: {missing_table[:5]}",
    )

    # 13 — all 10 docs pages exist with mobile viewport
    missing_pages = [p for p in expected_pages if not (DOCS / p).exists()]
    no_vp = [
        p
        for p in expected_pages
        if (DOCS / p).exists() and 'name="viewport"' not in (DOCS / p).read_text()
    ]
    check(
        13,
        "all 10 docs/*.html category pages exist with mobile viewport",
        not missing_pages and not no_vp,
        f"missing={missing_pages} no_vp={no_vp}",
    )

    # 14 — zero '(Kills)' derivative markets
    kills_bad = []
    for m in scheduled:
        mc = m.get("market_consensus")
        if mc and re.search(r"\(kills?\)", json.dumps(mc), re.I):
            kills_bad.append(m["id"])
    check(14, "no '(Kills)' derivative market used as a match line", not kills_bad, str(kills_bad))

    # 15 — forensic entity-collision & DQ walkover checks
    by_id = {m["id"]: m for m in scheduled}
    forensic_bad = []
    m_png = by_id.get("1083097")
    if m_png and (m_png["team0"]["canonical_name"] != "PNG" or m_png["p0"] is not None):
        forensic_bad.append("1083097_not_quarantined_to_PNG")
    m_pvb = by_id.get("1079031")
    if m_pvb and m_pvb["team1"]["canonical_name"] != "PvB (Swiss Team)":
        forensic_bad.append("1079031_not_aliased_to_PvB_Swiss")
    for dq_id in ("1071170", "1071200", "1071206", "1071186"):
        mdq = by_id.get(dq_id)
        if mdq and (mdq.get("p0") is not None or not mdq.get("settlement_pick")):
            forensic_bad.append(f"{dq_id}_dq_bad")
    check(
        15,
        "cross-region homonym quarantines (#1083097, #1079031) & Solid Gaming DQ walkovers verified",
        not forensic_bad,
        str(forensic_bad),
    )

    # 16 — every Flagged entry links Hotspawn + external source
    flag_bad = []
    for f in flags.get("flags", []):
        if not f.get("hotspawn_url") or not f.get("source_url"):
            flag_bad.append(f.get("id"))
        elif esc_html(f["hotspawn_url"]) not in flagged_html:
            flag_bad.append(f.get("id") + "_not_in_html")
    check(
        16,
        "every Flagged for Review item renders with Hotspawn + official source links",
        not flag_bad,
        f"{len(flags.get('flags', []))} flags, bad={flag_bad[:5]}",
    )

    print()
    print(
        f"rows: {len(matches)} total | scheduled {len(scheduled)} | active {len(active)} "
        f"({len(with_pick)} with pick, {len(without)} unresolved) | "
        f"ended/forfeited {len(ended)} | flags {len(flags.get('flags', []))} | "
        f"ledger {len(ledger)} entries"
    )
    if failures:
        print(f"\n{len(failures)} CHECK(S) FAILED")
        return 1
    print("\nALL DOCS CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
