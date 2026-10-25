"""Session 666de992 independent verification (imports nothing from tools/).

Re-derives the published contract from data/matches.json + data/picks.csv +
rendered HTML: picks for every row, probability arithmetic, settlement rules,
market source URLs, CSV mirror, executive-summary/unresolved rendering,
internal-link resolution, and internal consistency of the pair-search receipt.
Exits 1 on any failure. Output: audit/session_666de992/report.json
"""
from __future__ import annotations

import csv
import json
import math
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
checks = []


def add(name, ok, detail):
    checks.append({"name": name, "ok": bool(ok), "detail": str(detail)[:500]})


def main():
    doc = json.load(open(os.path.join(ROOT, "data", "matches.json")))
    rows = doc["matches"]
    add("dataset loads with rows", len(rows) > 0, f"{len(rows)} rows, generated {doc.get('generated_utc')}")
    add("total field matches row count", doc.get("total") == len(rows), f"total={doc.get('total')} rows={len(rows)}")

    ids = [r["id"] for r in rows]
    add("ids unique", len(ids) == len(set(ids)), f"{len(set(ids))} unique / {len(ids)}")

    hist = Counter(r["method"] for r in rows)
    add("method histogram == counts field", dict(hist) == doc.get("counts"),
        f"hist={dict(hist)} counts={doc.get('counts')}")
    add("methods are known", set(hist) <= {"market", "model", "provisional", "unresolved"}, str(set(hist)))

    bad_sum, bad_pick, bad_url, bad_market, bad_settle, no_pick = [], [], [], [], [], []
    for r in rows:
        url = r.get("hotspawn_url") or ""
        if not (url.startswith("https://www.hotspawn.com/matches/") and url.rstrip("/").split("-")[-1] == str(r["id"])):
            bad_url.append(r["id"])
        pick = r.get("pick") or {}
        if not pick.get("team"):
            no_pick.append(r["id"])
            continue
        if pick["team"] not in (r["team0"]["name"], r["team1"]["name"]):
            bad_pick.append((r["id"], "pick not a participant"))
        p0, p1 = r.get("p0"), r.get("p1")
        if r["method"] == "unresolved":
            # settlement contract: named winner + source, no probability anywhere
            res = r.get("resolution") or {}
            if p0 is not None or p1 is not None or pick.get("probability") is not None:
                bad_settle.append((r["id"], "probability on settlement row"))
            if res.get("winner") != pick.get("team") or not str(res.get("source") or "").startswith("https://"):
                bad_settle.append((r["id"], "resolution winner/source mismatch"))
        else:
            if p0 is None or p1 is None or not (math.isfinite(p0) and math.isfinite(p1)):
                bad_sum.append((r["id"], "missing/non-finite probability"))
            elif abs((p0 + p1) - 1.0) > 0.002:
                bad_sum.append((r["id"], f"sum={p0+p1:.4f}"))
            exp_team = r["team0"]["name"] if (p0 or 0) >= (p1 or 0) else r["team1"]["name"]
            if pick.get("team") != exp_team:
                bad_pick.append((r["id"], f"pick {pick.get('team')} != argmax {exp_team}"))
            if abs((pick.get("probability") or -1) - max(p0 or 0, p1 or 0)) > 1e-9:
                bad_pick.append((r["id"], "pick probability != max(p0,p1)"))
        if r["method"] == "market":
            venues = ((r.get("market") or {}).get("venues")) or []
            if not venues or not all(str(v.get("url") or "").startswith("https://") for v in venues):
                bad_market.append((r["id"], "venue without https url"))
            if any("(Kills)" in str(v) for v in venues):
                bad_market.append((r["id"], "(Kills) derivative in venues"))
    add("every row links to its own Hotspawn card", not bad_url, f"bad={bad_url[:5]}")
    add("every row has a pick (incl. settlements)", not no_pick, f"missing={no_pick[:5]}")
    add("probabilities finite and sum to 1 (±0.002)", not bad_sum, f"bad={bad_sum[:5]}")
    add("pick == higher-probability participant", not bad_pick, f"bad={bad_pick[:5]}")
    add("settlement rows: winner+source, no probability", not bad_settle, f"bad={bad_settle[:5]}")
    add("market rows carry https venue URLs, no (Kills)", not bad_market, f"bad={bad_market[:5]}")

    # track record recomputation
    graded = [r for r in rows if r.get("grade") in ("hit", "miss")]
    hits = [r for r in graded if r["grade"] == "hit"]
    tr = doc.get("track_record") or {}
    add("track record == graded rows",
        tr.get("graded") == len(graded) and tr.get("hits") == len(hits)
        and tr.get("misses") == len(graded) - len(hits),
        f"graded={len(graded)} hits={len(hits)} track={tr.get('graded')}/{tr.get('hits')}")
    grade_bad = []
    for r in graded:
        res = r.get("result") or {}
        win_team = r["team0"]["name"] if res.get("winner_side") == 0 else r["team1"]["name"]
        if (r["grade"] == "hit") != ((r.get("pick") or {}).get("team") == win_team):
            grade_bad.append(r["id"])
    add("hit/miss agrees with recorded winner", not grade_bad, f"bad={grade_bad[:5]}")

    # CSV mirror
    with open(os.path.join(ROOT, "data", "picks.csv"), newline="", encoding="utf-8") as fh:
        csv_rows = list(csv.DictReader(fh))
    add("picks.csv row count == dataset", len(csv_rows) == len(rows),
        f"csv={len(csv_rows)} json={len(rows)}")

    # rendered pages: every match present, exec-summary contract, internal links
    def read(p):
        path = os.path.join(ROOT, p)
        return open(path, encoding="utf-8").read() if os.path.exists(path) else ""

    picks_html, table_html, index_html = read("picks.html"), read("table.html"), read("index.html")
    n_cards = sum(1 for r in rows if ('id="match-' + str(r["id"]) + '"') in picks_html)
    add("every match card on picks.html", n_cards == len(rows), f"{n_cards}/{len(rows)}")
    n_prows = table_html.count('class="prow')
    add("table.html renders one prow per match", n_prows == len(rows),
        f"prows={n_prows} rows={len(rows)}")
    for marker in ["Executive summary", "Where the picks are", "Unresolved picks and the limitations",
                   "Starting soon", "pair-search receipt", "Treat those named cards as the weakest"]:
        add(f"index marker: {marker}", marker in index_html, "")
    debut_ids = [r["id"] for r in rows if r["method"] == "provisional"
                 and ((r.get("team0") or {}).get("rating_matches") == 0
                      or (r.get("team1") or {}).get("rating_matches") == 0)]
    add("zero-history debuts named on index with card links",
        all(f'picks.html#match-{i}' in index_html for i in debut_ids),
        f"debuts={debut_ids}")
    # The nextrow data-start/live-hide behaviour shipped by session b1e5557f (PR #95);
    # this session yielded its duplicate implementation during integration. The audit
    # only asserts the strip itself renders.
    n_next = index_html.count('class="nextrow')
    add("starting-soon strip renders on index", n_next >= 1, f"nextrows={n_next}")
    add("canonical/companion labelling in footer",
        "canonical pick list" in index_html and 'href="docs/index.html"' in index_html, "")

    pages = ["index.html", "table.html", "picks.html", "results.html", "featured.html",
             "originated.html", "unresolved.html", "competitions.html", "teams.html",
             "methodology.html", "verification.html", "sources.html", "flagged.html", "coverage.html"]
    broken = []
    for page in pages:
        body = read(page)
        for href in re.findall(r'href="([^"]+)"', body):
            if href.startswith(("http://", "https://", "#", "mailto:")):
                continue
            target = href.split("#")[0].split("?")[0]
            if target and not os.path.exists(os.path.join(ROOT, target)):
                broken.append(f"{page} -> {href}")
    add("no broken internal links (14 root pages)", not broken, f"broken={broken[:6]}")

    # pair-search receipt internal consistency (not vs matches.json: different day)
    probe = json.load(open(os.path.join(ROOT, "data", "probe", "session_666de992", "probe.json")))
    venues = probe.get("venues") or []
    inv = probe.get("inventory") or {}
    add("pair probe: inventory partitions (control+tail == searched+control)",
        inv.get("tail_pairs") == len(probe.get("tail_pairs_searched") or []),
        f"tail={inv.get('tail_pairs')} searched={len(probe.get('tail_pairs_searched') or [])} control={inv.get('control_pairs')}")
    listed_tail = [v["slug"] for v in venues if v.get("tail_pair_hits")]
    summ_tail = [s for s in (probe.get("summary") or {}).get("venues_with_tail_pairs", [])
                 if s != "polymarket_census"]
    add("pair probe: summary tail venues == rows", listed_tail == summ_tail,
        f"rows={listed_tail} summary={summ_tail}")
    tail_hits = [(v["slug"], h["competition"]) for v in venues for h in v.get("tail_pair_hits") or []]
    add("pair probe: tail hits confined to LGC/LCP listings",
        all(c in ("LGC Rising 2026 Playoffs", "LCP 2027 Promotion") for _, c in tail_hits),
        f"hits={tail_hits}")
    ctl_ok = [v["slug"] for v in venues if v.get("control_pair_hits")]
    add("pair probe: positive controls found Worlds pairs", len(ctl_ok) >= 5, f"controls={ctl_ok}")

    passed = all(c["ok"] for c in checks)
    report = {"session": "666de992", "passed": passed, "checks": checks,
              "dataset_generated_utc": doc.get("generated_utc"),
              "probe_generated_utc": probe.get("generated_utc")}
    out = os.path.join(ROOT, "audit", "session_666de992", "report.json")
    json.dump(report, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for c in checks:
        print(("PASS " if c["ok"] else "FAIL ") + c["name"] + " :: " + c["detail"])
    print(f"\n{'PASS' if passed else 'FAIL'}: {sum(c['ok'] for c in checks)}/{len(checks)} checks -> {out}")
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
