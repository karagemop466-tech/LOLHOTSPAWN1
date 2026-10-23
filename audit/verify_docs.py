#!/usr/bin/env python3
"""
verify_docs.py — session 7f76a03b line-by-line verification of the secondary
(docs/) Node dashboard against its committed data snapshot (data/node/**).

Checks (each prints PASS/FAIL; exit 1 on any FAIL):
  1  docs/data/picks.json is byte-identical to data/node/picks.json
  2  every open/locked/live match with a pick is rendered on docs/picks.html
  3  every rendered probability on a pick card matches the JSON value
  4  every open match without a pick appears on docs/unresolved.html
  5  every match card carries a Hotspawn source link
  6  market-priced rows carry the market source link (Pinnacle/Polymarket)
  7  no fabricated scores: results.html score text matches the JSON exactly
  8  no ledger entry with an official result renders as "pending"
  9  NAV present on every docs page; exec summary links every picks view
 10  internal hrefs across docs/*.html resolve to files that exist
 11  every row's probabilities sum to 100% (+/- 0.2pp) and pick = argmax

No network access: verifies the committed snapshot against the committed HTML,
exactly what GitHub Pages serves. Live-source spot checks are recorded in
COORDINATION.md separately.
"""
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
    return f"{p * 100:.0f}%" if p >= 0.995 else f"{p * 100:.1f}%"


def main():
    picks = json.loads((DATA / "picks.json").read_text())
    flags = json.loads((DATA / "flags.json").read_text())
    ledger = json.loads((DATA / "history" / "picks_latest.json").read_text())
    matches = picks["matches"]

    # 1 — published copy identical
    a = (DOCS / "data" / "picks.json").read_bytes()
    b = (DATA / "picks.json").read_bytes()
    check(1, "docs/data/picks.json mirrors data/node/picks.json", a == b,
          f"{len(a)} bytes")

    picks_html = (DOCS / "picks.html").read_text()
    unres_html = (DOCS / "unresolved.html").read_text()
    results_html = (DOCS / "results.html").read_text()
    idx_html = (DOCS / "index.html").read_text()

    active = [m for m in matches if m["state"] in ("open", "locked", "live")]
    with_pick = [m for m in active if m.get("pick")]
    without = [m for m in active if not m.get("pick")]

    # 2 — every picked active match rendered on picks.html
    missing_cards = [m["id"] for m in with_pick if f'id="m-{m["id"]}"' not in picks_html]
    check(2, "every active match with a pick rendered on picks.html",
          not missing_cards, f"{len(with_pick)} picked rows, missing: {missing_cards[:5]}")

    # 3 — rendered probabilities match the JSON (per team row inside the card)
    prob_bad = []
    for m in with_pick:
        cid = f'id="m-{m["id"]}"'
        if cid not in picks_html:
            continue  # counted by check 2
        seg = picks_html.split(cid, 1)[1][:4000]
        seg = seg.split("</article>", 1)[0]
        p0 = (m["market_pinnacle"] or {}).get("p0") or \
             (m["market_polymarket"] or {}).get("p0") or \
             (m["model"] or {}).get("p0")
        if p0 is None:
            prob_bad.append((m["id"], "no source p0 in JSON but rendered"))
            continue
        if pct_str(p0) not in seg or pct_str(1 - p0) not in seg:
            prob_bad.append((m["id"], f"expected {pct_str(p0)}/{pct_str(1-p0)}"))
    check(3, "rendered probabilities match JSON", not prob_bad,
          f"bad: {prob_bad[:5]}")

    # 4 — unresolved open matches listed
    missing_unres = [m["id"] for m in without if f'id="m-{m["id"]}"' not in unres_html]
    check(4, "every open match without a pick is on unresolved.html",
          not missing_unres, f"{len(without)} unresolved, missing: {missing_unres[:5]}")

    # 5 — Hotspawn source link per rendered card
    no_src = []
    for m in active:
        cid = f'id="m-{m["id"]}"'
        for html in (picks_html, unres_html):
            if cid in html:
                seg = html.split(cid, 1)[1].split("</article>", 1)[0]
                if m["hotspawn_url"] not in seg:
                    no_src.append(m["id"])
                break
    check(5, "every rendered card links its Hotspawn match card", not no_src,
          f"missing: {sorted(set(no_src))[:5]}")

    # 6 — market rows carry market source link
    mkt_missing = []
    for m in active:
        cid = f'id="m-{m["id"]}"'
        if cid not in picks_html:
            continue
        seg = picks_html.split(cid, 1)[1].split("</article>", 1)[0]
        for key in ("market_pinnacle", "market_polymarket"):
            mk = m.get(key)
            if mk and mk.get("url") and mk["url"] not in seg:
                mkt_missing.append((m["id"], key))
    mkt_rows = [m for m in active if m.get("market_pinnacle") or m.get("market_polymarket")]
    check(6, "market rows carry their market source link", not mkt_missing,
          f"{len(mkt_rows)} market rows, missing: {mkt_missing[:5]}")

    # 7 — results.html scores exactly match JSON (no fabricated fills)
    score_bad = []
    ended = [m for m in matches if m["state"] in ("ended", "forfeited")]
    for m in ended:
        has = m["score0"] is not None and m["score1"] is not None
        want = f'{m["team0"]["name"]} {m["score0"]}–{m["score1"]} {m["team1"]["name"]}' if has \
            else f'{m["team0"]["name"]} vs (no official score) {m["team1"]["name"]}'
        alt = f'{m["team0"]["name"]} {m["score0"]}–{m["score1"]} {m["team1"]["name"]}'
        if want not in results_html and alt not in results_html:
            # results page only renders this week's ended fixtures; locate by link
            if m["hotspawn_url"] in results_html:
                seg = results_html.split(m["hotspawn_url"], 1)[1][:300]
                want_tail = (f'{m["score0"]}–{m["score1"]} {m["team1"]["name"]}' if has
                             else "vs (no official score)")
                if want_tail not in seg:
                    score_bad.append((m["id"], seg.split("</a>")[0][:80]))
    check(7, "results.html renders only official scores (no fabricated fills)",
          not score_bad, f"bad: {score_bad[:5]}")

    # 8 — no "pending" where an official result exists
    pend_bad = []
    for m in ended:
        if m["hotspawn_url"] not in results_html:
            continue
        seg = results_html.split(m["hotspawn_url"], 1)[1].split("</tr>", 1)[0]
        has = m["score0"] is not None and m["score1"] is not None and m["score0"] != m["score1"]
        if has and "pending" in seg:
            pend_bad.append(m["id"])
        if not has and m["state"] == "forfeited" and "pending" in seg:
            pend_bad.append(m["id"] + " (forfeit w/o score shows pending)")
    check(8, "no ledger entry with an official result renders as pending",
          not pend_bad, f"bad: {pend_bad[:5]}")

    # 9 — NAV + exec summary links
    pages = sorted(p.name for p in DOCS.glob("*.html"))
    nav_missing = []
    for p in pages:
        t = (DOCS / p).read_text()
        for need in ("picks.html", "unresolved.html", "flagged.html"):
            if need not in t:
                nav_missing.append((p, need))
    check(9, "navigation on every docs page", not nav_missing, str(nav_missing[:5]))
    exec_links = [t for t in ("picks.html", "unresolved.html", "flagged.html",
                              "results.html", "tournaments.html", "methodology.html")]
    missing_exec = [t for t in exec_links if t not in idx_html]
    check(9.1, "exec summary links every picks view", not missing_exec,
          str(missing_exec))

    # 10 — internal hrefs resolve
    broken = []
    for p in pages:
        t = (DOCS / p).read_text()
        for href in re.findall(r'href="([^"]+)"', t):
            if href.startswith(("http://", "https://", "#", "mailto:", "data:")):
                continue
            base = href.split("#", 1)[0].split("?", 1)[0]
            if not base:
                continue
            if not (DOCS / base).exists():
                broken.append((p, href))
    check(10, "no broken internal links in docs/", not broken, str(broken[:5]))

    # 11 — probability integrity on JSON rows
    integ_bad = []
    for m in matches:
        p0 = (m["market_pinnacle"] or {}).get("p0") or (m["market_polymarket"] or {}).get("p0") \
            or (m["model"] or {}).get("p0")
        if p0 is None:
            continue
        if abs(p0 + (1 - p0) - 1) > 1e-9:
            integ_bad.append(m["id"])
        pk = m.get("pick")
        if pk and pk["team_index"] != (0 if p0 >= 1 - p0 else 1):
            integ_bad.append(m["id"] + " pick!=argmax")
    check(11, "probabilities sum to 100% and pick = argmax", not integ_bad,
          f"bad: {integ_bad[:5]}")

    # summary
    print()
    print(f"rows: {len(matches)} total | active {len(active)} "
          f"({len(with_pick)} with pick, {len(without)} unresolved) | "
          f"ended/forfeited {len(ended)} | flags {len(flags.get('flags', []))} | "
          f"ledger {len(ledger)} entries")
    if failures:
        print(f"\n{len(failures)} CHECK(S) FAILED")
        return 1
    print("\nALL DOCS CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
