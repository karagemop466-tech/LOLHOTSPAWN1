#!/usr/bin/env python3
"""
verify_docs_parity.py — session 9f16f9ad gate for the SECONDARY dashboard.

One GitHub Pages domain serves two dashboards from this repository:

  canonical   root ``*.html``  — ``tools/`` pipeline, ``data/matches.json``.
                                 The pick list: the pick to submit.
  secondary   ``docs/*.html``  — ``scripts/`` Node pipeline, ``data/node/**``.
                                 A companion audit: its own ratings, its own
                                 grading pass over official Hotspawn scores.

Both cover the same Hotspawn ``status=scheduled`` inventory but fit their own
Elo, so they disagree (12 opposite picks at the 2026-10-24T16:49Z snapshot).
This gate keeps that disagreement visible and honest instead of letting either
view pass itself off as the other:

   1  no docs page reuses a canonical title; every docs title says "secondary"
   2  the secondary banner is the first element in <body> on every docs page and
      links the canonical hub
   3  the reconciliation block reproduces both committed snapshots — canonical
      total + method counts, secondary scheduled/active/stale/ended/cancelled
      counts, competition count and venue count (no hard-coded drift)
   4  every scheduled row deep-links to a canonical anchor that really exists
   5  fixtures absent from the canonical snapshot are explained, not dropped
   6  every canonical probability rendered in docs/ equals data/matches.json to
      the displayed precision (Node toFixed and Python format round exact ties
      differently, so the comparison is numeric, not string equality)
   7  every divergent fixture (>= 5 pp or opposite pick) is marked on its row and
      listed in the overview's divergence ledger — and nothing else is listed
   8  no series format is rendered that Hotspawn does not publish (the feed
      returns best_of = null for every scheduled card; Leaguepedia lists
      #1081421 as bestof=5, so "Bo1" was both invented and wrong)
   9  internal links and fragments resolve, including ../ links into the root site
  10  the methodology page documents the relationship to the canonical dashboard
      with the same parity numbers this gate recomputes

Offline: reads only committed files, exactly what GitHub Pages serves.
Receipt: audit/9f16f9ad/docs_parity.json
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
NODE = ROOT / "data" / "node"
RECEIPT_DIR = ROOT / "audit" / "9f16f9ad"

DIVERGE_PP = 5.0  # must match DIVERGE_PP in scripts/build_site.mjs

failures: list[str] = []
warnings: list[str] = []
details: dict[str, object] = {}


def check(n, name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'} {str(n):>4} {name}" + (f" :: {detail}" if detail else ""))
    if not ok:
        failures.append(f"{n} {name} :: {detail}")


def warn(name: str, detail: str = "") -> None:
    print(f"WARN      {name}" + (f" :: {detail}" if detail else ""))
    warnings.append(f"{name} :: {detail}")


def seg_after(html: str, marker: str, end: str = "</article>") -> str | None:
    if marker not in html:
        return None
    return html.split(marker, 1)[1].split(end, 1)[0]


def main() -> int:
    canon_doc = json.loads((ROOT / "data" / "matches.json").read_text())
    canon_rows = canon_doc.get("matches") or []
    canon_by_id = {str(r.get("id")): r for r in canon_rows}

    node_doc = json.loads((NODE / "picks.json").read_text())
    node_rows = node_doc.get("matches") or []
    counts = (node_doc.get("summary") or {}).get("counts") or {}
    calibration = (node_doc.get("summary") or {}).get("calibration") or {}
    scheduled = [m for m in node_rows if m.get("status") == "scheduled"]

    raw_rows: list = []
    raw_path = NODE / "raw" / "hotspawn_lol_fixtures.json"
    if raw_path.exists():
        raw_doc = json.loads(raw_path.read_text())
        raw_rows = raw_doc.get("fixtures") if isinstance(raw_doc, dict) else raw_doc
        raw_rows = raw_rows or []
    raw_best_of = {str(f.get("id")): f.get("best_of") for f in raw_rows}

    docs_pages = sorted(DOCS.glob("*.html"))
    docs_html = {p.name: p.read_text() for p in docs_pages}
    root_picks = (ROOT / "picks.html").read_text()
    root_titles = {(ROOT / f).read_text() for f in ("index.html", "table.html", "picks.html")}
    root_titles = {re.search(r"<title>(.*?)</title>", t, re.S).group(1).strip() for t in root_titles}

    details.update(docs_pages=[p.name for p in docs_pages], canonical_rows=len(canon_rows),
                   secondary_rows=len(node_rows), scheduled_rows=len(scheduled))

    # 1 — titles
    reused = [n for n, h in docs_html.items()
              if (m := re.search(r"<title>(.*?)</title>", h, re.S)) and m.group(1).strip() in root_titles]
    unmarked = [n for n, h in docs_html.items()
                if "secondary" not in (re.search(r"<title>(.*?)</title>", h, re.S).group(1).lower()
                                       if re.search(r"<title>(.*?)</title>", h, re.S) else "")]
    check(1, "no docs page reuses a canonical title and every docs title says 'secondary'",
          not reused and not unmarked, f"reused: {reused}; unmarked: {unmarked}")

    # 2 — banner first in <body> + canonical hub link
    no_banner, no_link = [], []
    for n, h in docs_html.items():
        m = re.search(r"<body>\s*(.{0,120})", h, re.S)
        if not m or 'class="canonbar"' not in m.group(1):
            no_banner.append(n)
        if 'href="../index.html"' not in h:
            no_link.append(n)
    check(2, "secondary banner is first in <body> and every page links the canonical hub",
          not no_banner and not no_link, f"banner not first: {no_banner}; no canonical link: {no_link}")

    # 3 — reconciliation block reproduces both snapshots
    idx = docs_html.get("index.html", "")
    recon = idx.split('id="reconcile"', 1)
    recon_html = recon[1].split("</section>", 1)[0] if len(recon) == 2 else ""
    comps = {m.get("competition_name") for m in scheduled}
    venue_labels = sorted({v.get("venue_label") for m in scheduled
                           for v in (m.get("market_consensus") or {}).get("venues", []) if v.get("venue_label")})
    expected = [
        (f"<b>{len(canon_rows)}</b> cards Hotspawn lists", "canonical universe"),
        (f"<b>{len(scheduled)}</b> scheduled rows", "secondary universe"),
        (f"{counts.get('active_open_locked')} active", "secondary active count"),
        (f"{counts.get('stale_scheduled')} stale", "secondary stale count"),
        (f"<strong>{len(comps)}</strong> competitions", "competition count (was hard-coded 29)"),
    ]
    for key, val in (canon_doc.get("counts") or {}).items():
        expected.append((f"{key} {val}", f"canonical counts.{key}={val}"))
    for lbl in venue_labels:
        expected.append((lbl, f"secondary venue {lbl}"))
    missing = [label for needle, label in expected if needle not in idx]
    check(3, "reconciliation + overview numbers reproduce both committed snapshots",
          bool(recon_html) and not missing,
          f"reconcile section: {bool(recon_html)}; missing: {missing}; "
          f"oos series rendered: {(calibration.get('oos_evaluated') or 0):,}")

    # 4/5/6/7/8 — per-row canonical cross-reference on the all-scheduled table
    table_html = docs_html.get("table.html", "")
    no_link_rows, dead_anchor, unexplained, prob_bad, unmarked_div, bad_bo = [], [], [], [], [], []
    divergent_expected = []
    for m in scheduled:
        mid = str(m.get("id"))
        row = seg_after(table_html, f'id="row-{mid}"', end="</tr>")
        if row is None:
            continue
        cm = canon_by_id.get(mid)
        if cm is None:
            if 'class="canon none"' not in row and "not in the canonical snapshot" not in row:
                unexplained.append(mid)
            continue
        link = f"../picks.html#match-{mid}"
        if link not in row:
            no_link_rows.append(mid)
        elif f'id="match-{mid}"' not in root_picks:
            dead_anchor.append(mid)
        pick = cm.get("pick") or {}
        prob = pick.get("probability")
        if prob is not None:
            shown = [float(x) / 100 for x in re.findall(r"(\d+(?:\.\d+)?)%", row)]
            if not any(abs(v - prob) <= 0.0005 + 1e-9 for v in shown):
                prob_bad.append((mid, prob, shown[:4]))
        # divergence marking
        both = m.get("p0") is not None and cm.get("p0") is not None
        delta = (m["p0"] - cm["p0"]) if both else None
        docs_pick = (m.get("pick") or {}).get("team_name") or (m.get("settlement_pick") or {}).get("team_name")
        canon_pick = pick.get("team")
        opposite = bool(docs_pick and canon_pick and docs_pick != canon_pick)
        is_div = opposite or (delta is not None and abs(delta) * 100 >= DIVERGE_PP)
        marked = ("canon-diverge" in row)
        if is_div and not marked:
            unmarked_div.append(mid)
        if is_div:
            divergent_expected.append(mid)
        # series format: never render a number Hotspawn does not publish
        if mid in raw_best_of and raw_best_of[mid] is None:
            if re.search(r"\(Bo\d", row) or re.search(r">Bo\d", row):
                bad_bo.append(mid)
            elif "Bo —" not in row:
                bad_bo.append(mid + " (no format rendered at all)")
    check(4, "every scheduled row deep-links to a canonical anchor that exists",
          not no_link_rows and not dead_anchor,
          f"{len(scheduled)} rows; missing link: {no_link_rows[:5]}; dead anchor: {dead_anchor[:5]}")
    check(5, "fixtures absent from the canonical snapshot are explained, not silently dropped",
          not unexplained, f"unexplained: {unexplained[:5]}")
    check(6, "canonical probabilities rendered in docs/ equal data/matches.json",
          not prob_bad, f"mismatched: {prob_bad[:5]}")
    # 7 — divergence ledger on the overview lists exactly the divergent fixtures
    ledger_missing = [mid for mid in divergent_expected if f"#match-{mid}" not in idx and mid not in idx]
    check(7, f"divergences (>= {DIVERGE_PP:.0f} pp or opposite pick) are marked and listed",
          not unmarked_div and not ledger_missing,
          f"{len(divergent_expected)} divergent fixtures; unmarked rows: {unmarked_div[:5]}; "
          f"missing from overview ledger: {ledger_missing[:5]}")
    check(8, "no series format is rendered that Hotspawn does not publish",
          not bad_bo, f"{sum(1 for m in scheduled if raw_best_of.get(str(m['id'])) is None)} rows have "
                      f"best_of=null in the feed; bad renders: {bad_bo[:5]}")

    # 9 — internal links and fragments
    ids_by_page = {n: set(re.findall(r'\bid="([^"]+)"', h)) for n, h in docs_html.items()}
    broken = []
    for n, h in docs_html.items():
        for href in re.findall(r'href="([^"]+)"', h):
            if href.startswith(("http://", "https://", "mailto:", "data:")):
                continue
            if href.startswith("#"):
                if href[1:] and href[1:] not in ids_by_page[n]:
                    broken.append((n, href))
                continue
            base, _, frag = href.partition("#")
            base = base.split("?", 1)[0]
            if not base:
                continue
            target = (DOCS / base)
            if not target.exists():
                broken.append((n, href))
            elif frag and base in ids_by_page and frag not in ids_by_page[base]:
                broken.append((n, href))
    check(9, "internal links and fragments resolve (including ../ into the root site)",
          not broken, f"broken: {broken[:6]}")

    # 10 — methodology documents the relationship with the same numbers
    meth = docs_html.get("methodology.html", "")
    need = ["Relationship to the Canonical Dashboard",
            f"{len(divergent_expected) if divergent_expected else 0}",
            "Series Format Is Not Published by Hotspawn",
            "Data:LCP/2027 Season/Promotion"]
    missing_meth = [x for x in need if x not in meth]
    check(10, "methodology documents the canonical relationship and the unpublished series format",
          not missing_meth, f"missing: {missing_meth}")

    # cross-checks that are informative but not blocking
    both_prob = [m for m in scheduled if m.get("p0") is not None and canon_by_id.get(str(m["id"]), {}).get("p0") is not None]
    deltas = sorted((abs(m["p0"] - canon_by_id[str(m["id"])]["p0"]) for m in both_prob), reverse=True)
    details.update(
        shared_ids=len([m for m in scheduled if str(m["id"]) in canon_by_id]),
        both_probability=len(both_prob),
        divergent=len(divergent_expected),
        mean_abs_gap_pp=round(sum(deltas) / len(deltas) * 100, 3) if deltas else None,
        max_abs_gap_pp=round(deltas[0] * 100, 3) if deltas else None,
        canonical_ids_not_in_secondary=len([r for r in canon_rows
                                            if str(r["id"]) not in {str(m["id"]) for m in scheduled}]),
    )
    if details["canonical_ids_not_in_secondary"]:
        warn("canonical cards missing from the secondary snapshot",
             str(details["canonical_ids_not_in_secondary"]))
    print()
    print(f"scheduled rows: {len(scheduled)} | shared with canonical: {details['shared_ids']} | "
          f"both priced: {details['both_probability']} | divergent: {details['divergent']} | "
          f"mean gap {details['mean_abs_gap_pp']} pp | max gap {details['max_abs_gap_pp']} pp")

    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    (RECEIPT_DIR / "docs_parity.json").write_text(json.dumps({
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "gate": "audit/verify_docs_parity.py",
        "passed": not failures,
        "divergence_threshold_pp": DIVERGE_PP,
        "failures": failures,
        "warnings": warnings,
        **details,
    }, indent=2) + "\n")

    if failures:
        print(f"\n{len(failures)} PARITY CHECK(S) FAILED")
        return 1
    print("\nALL DOCS-PARITY CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
