#!/usr/bin/env python3
"""Independent verification of the published dashboard (session 5ff8e6bf).

This is a *second opinion*, written from the published artefacts only. It does not
import anything from `tools/`, so a bug in the pipeline cannot hide here: every
number is re-derived from `data/matches.json`, `data/raw/hotspawn_lol.json`,
`data/picks.csv` and the generated HTML.

Usage:
    python3 audit/session_5ff8e6bf/verify_published.py [--out DIR]

Exit code 0 = every check passed, 1 = at least one check failed.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data")
RAW = os.path.join(DATA, "raw")
HERE = os.path.dirname(os.path.abspath(__file__))

PAGES = ["index.html", "table.html", "picks.html", "results.html", "featured.html", "originated.html",
         "unresolved.html", "competitions.html", "teams.html", "flagged.html",
         "coverage.html", "verification.html", "sources.html", "methodology.html"]
ALLOWED_METHODS = {"market", "model", "provisional", "unresolved"}
HOTSPAWN_CARD = re.compile(r"^https://www\.hotspawn\.com/matches/[a-z0-9-]+-(\d{6,8})$")

checks: list[dict] = []


def add(name: str, ok: bool, detail: str, severity: str = "fail") -> None:
    """severity="warn" records an observation that is published but does not fail the run."""
    checks.append({"name": name, "ok": bool(ok), "detail": detail, "severity": severity})
    tag = "PASS " if ok else ("WARN " if severity == "warn" else "FAIL ")
    print(tag + name + " :: " + detail)


def load(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def age_hours(iso_ts: str) -> float | None:
    try:
        dt = datetime.strptime(str(iso_ts)[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None
    return (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.ids: set[str] = set()
        self.meta_viewport = False
        self.rows = 0
        self.cards = 0
        self.text: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])
        if a.get("id"):
            self.ids.add(a["id"])
        if tag == "meta" and (a.get("name") or "").lower() == "viewport":
            self.meta_viewport = True
        cls = a.get("class") or ""
        if tag == "tr" and ("match-row" in cls or "prow" in cls.split() or a.get("data-method")):
            self.rows += 1
        if tag == "article" and "card" in cls:
            self.cards += 1

    def handle_data(self, data):
        self.text.append(data)


def parse_html(path: str) -> LinkParser:
    p = LinkParser()
    with open(path, encoding="utf-8") as fh:
        p.feed(fh.read())
    return p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=HERE)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    doc = load(os.path.join(DATA, "matches.json"))
    rows = doc.get("matches") or []
    raw = load(os.path.join(RAW, "hotspawn_lol.json"))
    fixtures = raw.get("fixtures") or []

    # ---------------------------------------------------------------- inventory
    raw_ids = [str(f.get("id")) for f in fixtures]
    pub_ids = [str(r.get("id")) for r in rows]
    add("inventory mirrors the collected Hotspawn feed 1:1",
        sorted(raw_ids) == sorted(pub_ids) and len(rows) > 0,
        f"feed={len(raw_ids)} dataset={len(pub_ids)} missing={sorted(set(raw_ids) - set(pub_ids))[:5]} "
        f"extra={sorted(set(pub_ids) - set(raw_ids))[:5]}")
    add("match ids are unique", len(set(pub_ids)) == len(pub_ids),
        f"{len(set(pub_ids))} unique of {len(pub_ids)}")

    # ---------------------------------------------------------------- arithmetic
    bad_sum, bad_pick, bad_name = [], [], []
    for r in rows:
        p0, p1 = r.get("p0"), r.get("p1")
        if p0 is None and p1 is None:
            continue
        if p0 is None or p1 is None:
            bad_sum.append(r["id"])
            continue
        if abs((p0 + p1) - 1.0) > 0.002:
            bad_sum.append(f"{r['id']}({p0}+{p1})")
        pick = r.get("pick") or {}
        true_side = 0 if p0 >= p1 else 1
        if pick.get("side") != true_side:
            bad_pick.append(r["id"])
        expected = r["team0"]["name"] if true_side == 0 else r["team1"]["name"]
        if pick.get("team") != expected:
            bad_name.append(f"{r['id']}:{pick.get('team')}!={expected}")
        if pick.get("probability") is None or abs(pick["probability"] - max(p0, p1)) > 0.0006:
            bad_pick.append(f"{r['id']}(prob)")
    add("both probabilities present and sum to 100% (+/-0.2pp)", not bad_sum, f"problems: {bad_sum[:5]}")
    add("published pick is the higher-probability side, named and quoted correctly",
        not bad_pick and not bad_name, f"side problems: {bad_pick[:5]} name problems: {bad_name[:5]}")

    # ---------------------------------------------------------------- settlements
    settled = [r for r in rows if r.get("resolution")]
    bad_settle = []
    for r in settled:
        pick = r.get("pick") or {}
        if pick.get("probability") is not None or pick.get("other_probability") is not None:
            bad_settle.append(f"{r['id']}: invented probability")
        if pick.get("team") not in (r["team0"]["name"], r["team1"]["name"]):
            bad_settle.append(f"{r['id']}: winner is not a listed participant")
        if not str((r.get("resolution") or {}).get("source", "")).startswith("https://"):
            bad_settle.append(f"{r['id']}: no source URL")
    add("settlement picks name a listed participant and claim no probability",
        not bad_settle, f"{len(settled)} settlements; problems: {bad_settle[:5]}")

    # ---------------------------------------------------------------- every row has a pick
    no_pick = [r["id"] for r in rows if not (r.get("pick") or {}).get("team")]
    add("every listed match carries a pick", not no_pick,
        f"{len(rows) - len(no_pick)}/{len(rows)} rows; missing: {no_pick[:5]}")

    # ---------------------------------------------------------------- methods
    methods = {}
    for r in rows:
        methods[r.get("method")] = methods.get(r.get("method"), 0) + 1
    add("method values are in the documented set", set(methods) <= ALLOWED_METHODS, f"methods: {methods}")
    declared = doc.get("counts") or {}
    add("published method counts reconcile with the rows",
        {k: int(v) for k, v in declared.items()} == methods and sum(methods.values()) == len(rows),
        f"declared={declared} recomputed={methods} rows={len(rows)}")

    # ---------------------------------------------------------------- market consensus re-derivation
    bad_consensus, bad_venues, no_url = [], [], []
    for r in rows:
        if r.get("method") != "market":
            continue
        venues = (r.get("market") or {}).get("venues") or []
        if not venues:
            bad_venues.append(r["id"])
            continue
        wsum = sum(float(v.get("weight") or 0) for v in venues)
        recomputed = sum(float(v.get("weight") or 0) * float(v["p0"]) for v in venues) / wsum if wsum else None
        if recomputed is None or abs(recomputed - float(r["p0"])) > 0.01:
            bad_consensus.append(f"{r['id']}({recomputed:.4f} vs {r['p0']})")
        if abs(wsum - 1.0) > 0.02:
            bad_venues.append(f"{r['id']}(weights={wsum:.3f})")
        for v in venues:
            if not str(v.get("url") or "").startswith("https://"):
                no_url.append(f"{r['id']}:{v.get('name')}")
            if not v.get("observed_utc"):
                no_url.append(f"{r['id']}:{v.get('name')}:no-timestamp")
    add("market rows re-derive from their own venue quotes (weights x prices)",
        not bad_consensus, f"problems: {bad_consensus[:5]}")
    add("every venue quote carries a URL and an observation timestamp",
        not no_url, f"problems: {no_url[:5]}")
    add("published venue weights sum to 1.0 on every market row (informational)",
        not bad_venues, f"rows whose weights do not sum to 1.0: {bad_venues[:5]}", severity="warn")

    # ---------------------------------------------------------------- Elo re-derivation
    bad_elo, elo_n = [], 0
    for r in rows:
        if r.get("method") not in ("model", "provisional"):
            continue
        e0, e1 = (r["team0"].get("elo"), r["team1"].get("elo"))
        if e0 is None or e1 is None or r.get("p0") is None:
            continue
        elo_n += 1
        expect = 1.0 / (1.0 + 10 ** ((float(e1) - float(e0)) / 400.0))
        if abs(expect - float(r["p0"])) > 0.02:
            bad_elo.append(f"{r['id']}(elo_expect={expect:.3f} published={r['p0']})")
    add("originated rows re-derive from their own published Elo ratings",
        not bad_elo, f"{elo_n} rows re-derived; deviations >2pp: {bad_elo[:5]}")

    # ---------------------------------------------------------------- Hotspawn independence
    mirrored, mentioned = [], []
    for r in rows:
        cp = r.get("community_pick_pct") or {}
        c0 = cp.get("team0")
        if c0 is not None and r.get("p0") is not None:
            if abs(float(c0) - float(r["p0"])) < 0.0005:
                mirrored.append(r["id"])
        basis = str(r.get("basis") or "").lower()
        if re.search(r"(hotspawn[^.]{0,60}(crowd|picked_percent|pickem %|community %))|((crowd|picked|community) %?[^.]{0,20}hotspawn)", basis):
            mentioned.append(r["id"])
    add("published probabilities are not Hotspawn crowd percentages", not mirrored,
        f"rows identical to the crowd share: {mirrored[:5]}")
    add("no row derives its probability from a Hotspawn crowd share", not mentioned,
        f"rows: {mentioned[:5]}")

    # ---------------------------------------------------------------- source links
    bad_card = []
    for r in rows:
        url = str(r.get("hotspawn_url") or "")
        m = HOTSPAWN_CARD.match(url)
        if not m or m.group(1) != str(r["id"]):
            bad_card.append(f"{r['id']}:{url}")
    add("every row links to its own Hotspawn match card (id in the URL)", not bad_card,
        f"{len(rows) - len(bad_card)}/{len(rows)}; problems: {bad_card[:5]}")

    hosts = {}
    for r in rows:
        urls = [r.get("hotspawn_url")]
        mk = r.get("market") or {}
        urls += [mk.get("source_url"), mk.get("market_url")]
        urls += [v.get("url") for v in (mk.get("venues") or [])]
        urls += [(r.get("resolution") or {}).get("source")]
        for u in urls:
            if not u:
                continue
            if not str(u).startswith("https://"):
                hosts.setdefault("non-https", []).append(f"{r['id']}:{u}")
                continue
            hosts.setdefault(re.sub(r"^https://([^/]+).*$", r"\1", str(u)), []).append(r["id"])
    insecure = hosts.pop("non-https", [])
    add("every rendered source URL is https on a named host", not insecure,
        f"{len(hosts)} hosts: {sorted(hosts)[:8]}{' ...' if len(hosts) > 8 else ''}; problems: {insecure[:5]}")

    # ---------------------------------------------------------------- csv mirror
    csv_path = os.path.join(DATA, "picks.csv")
    with open(csv_path, newline="", encoding="utf-8") as fh:
        csv_rows = list(csv.DictReader(fh))
    by_id = {str(r["id"]): r for r in rows}
    id_col = "hotspawn_id" if csv_rows and "hotspawn_id" in csv_rows[0] else "id"
    pick_col = "pick" if csv_rows and "pick" in csv_rows[0] else "pick_team"
    bad_csv = []
    for c in csv_rows:
        r = by_id.get(str(c.get(id_col)))
        if r is None:
            bad_csv.append(f"csv-only:{c.get(id_col)}")
            continue
        if c.get(pick_col) and c[pick_col] != (r.get("pick") or {}).get("team"):
            bad_csv.append(f"{r['id']}:pick")
        if c.get("p0") not in (None, "") and r.get("p0") is not None:
            if abs(float(c["p0"]) - float(r["p0"])) > 0.0006:
                bad_csv.append(f"{r['id']}:p0")
    add("picks.csv mirrors the dataset row for row",
        len(csv_rows) == len(rows) and not bad_csv,
        f"csv={len(csv_rows)} json={len(rows)} problems: {bad_csv[:5]}")

    # ---------------------------------------------------------------- html
    missing = [p for p in PAGES if not os.path.exists(os.path.join(ROOT, p))]
    add("all published pages exist", not missing, f"{len(PAGES) - len(missing)}/{len(PAGES)}; missing: {missing}")

    broken, no_viewport, no_nav, no_mobnav, rendered_none = [], [], [], [], []
    counts = {}
    for page in PAGES:
        path = os.path.join(ROOT, page)
        if not os.path.exists(path):
            continue
        html = open(path, encoding="utf-8").read()
        p = parse_html(path)
        counts[page] = {"rows": p.rows, "cards": p.cards, "links": len(p.links)}
        if not p.meta_viewport:
            no_viewport.append(page)
        if 'class="nav"' not in html and 'id="nav"' not in html:
            no_nav.append(page)
        if 'class="mobnav"' not in html:
            no_mobnav.append(page)
        text = " ".join(p.text)
        for token in ("None", "nan", "NaN"):
            if re.search(r"(^|\s)" + token + r"(\s|$)", text):
                rendered_none.append(f"{page}:{token}")
        for href in p.links:
            if href.startswith(("http://", "https://", "mailto:", "#", "javascript:")):
                continue
            target = href.split("#")[0].split("?")[0]
            if not target:
                continue
            if not os.path.exists(os.path.join(ROOT, target)):
                broken.append(f"{page}->{href}")
    add("every page declares a mobile viewport", not no_viewport, f"missing: {no_viewport}")
    add("every page carries the desktop nav and the mobile bottom bar", not no_nav and not no_mobnav,
        f"nav missing: {no_nav}; mobnav missing: {no_mobnav}")
    add("no page renders a literal None/nan value", not rendered_none, f"problems: {rendered_none[:5]}")
    add("no broken internal links", not broken, f"{sum(v['links'] for v in counts.values())} links parsed; problems: {broken[:5]}")
    add("the table page renders exactly one row per match", counts.get("table.html", {}).get("rows") == len(rows),
        f"table rows={counts.get('table.html',{}).get('rows')} matches={len(rows)}")
    add("the card page renders exactly one card per match", counts.get("picks.html", {}).get("cards") == len(rows),
        f"cards={counts.get('picks.html',{}).get('cards')} matches={len(rows)}")

    index = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    needed = ["table.html", "picks.html", "results.html", "featured.html", "originated.html",
              "unresolved.html", "flagged.html", "Unresolved picks", "Executive summary"]
    absent = [n for n in needed if n not in index]
    add("the executive summary links every picks view, the unresolved section and the flag page",
        not absent, f"missing: {absent}")

    # ---------------------------------------------------------------- freshness
    gen_age = age_hours(doc.get("generated_utc"))
    inv_age = age_hours(doc.get("inventory_fetched_utc"))
    add("the published snapshot is younger than the 8 h refresh ceiling",
        gen_age is not None and gen_age <= 8.0,
        f"generated_utc={doc.get('generated_utc')} age={gen_age:.1f}h" if gen_age is not None else "generated_utc missing")
    add("the Hotspawn inventory was fetched recently enough to be current",
        inv_age is not None and inv_age <= 8.0,
        f"inventory_fetched_utc={doc.get('inventory_fetched_utc')} age={inv_age:.1f}h" if inv_age is not None else "missing")

    # ---------------------------------------------------------------- backtest internal consistency
    bt = doc.get("backtest") or {}
    n, hits, acc = bt.get("n"), bt.get("hits"), bt.get("accuracy")
    bucket_n = sum(int(b.get("n") or 0) for b in (bt.get("buckets") or {}).values())
    bucket_hits = sum(int(b.get("hits") or 0) for b in (bt.get("buckets") or {}).values())
    ok = (n and hits is not None and acc is not None and bucket_n == n and bucket_hits == hits
          and abs(hits / n - acc) < 0.002 and 0.15 < float(bt.get("brier") or 0) < 0.30)
    add("the out-of-sample backtest is internally consistent", bool(ok),
        f"n={n} hits={hits} acc={acc} buckets n={bucket_n} hits={bucket_hits} brier={bt.get('brier')}")

    # ---------------------------------------------------------------- write receipts
    report = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "verifier": "audit/session_5ff8e6bf/verify_published.py (independent re-derivation; does not import tools/)",
        "inputs": {
            "data/matches.json": {"rows": len(rows), "generated_utc": doc.get("generated_utc"),
                                  "inventory_fetched_utc": doc.get("inventory_fetched_utc")},
            "data/raw/hotspawn_lol.json": {"fixtures": len(fixtures), "fetched_utc": raw.get("fetched_utc")},
            "data/picks.csv": {"rows": len(csv_rows)},
            "pages": counts,
        },
        "source_hosts": {h: len(set(v)) for h, v in sorted(hosts.items())},
        "checks": checks,
        "passed": all(c["ok"] for c in checks if c.get("severity") != "warn"),
        "summary": {"total": len(checks), "passed": sum(1 for c in checks if c["ok"]),
                    "warnings": [c["name"] for c in checks if not c["ok"] and c.get("severity") == "warn"],
                    "failed": [c["name"] for c in checks if not c["ok"] and c.get("severity") != "warn"]},
    }
    with open(os.path.join(args.out, "report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, sort_keys=False)
        fh.write("\n")

    lines = ["# Independent verification of the published dashboard", "",
             f"Run: {report['generated_utc']} · verifier: `audit/session_5ff8e6bf/verify_published.py`", "",
             f"**Result: {report['summary']['passed']}/{report['summary']['total']} checks pass.**", "",
             "| # | Check | Result | Detail |", "|---|---|---|---|"]
    for i, c in enumerate(checks, 1):
        detail = str(c["detail"]).replace("|", "\\|")
        label = "PASS" if c["ok"] else ("WARN" if c.get("severity") == "warn" else "**FAIL**")
        lines.append(f"| {i} | {c['name']} | {label} | `{detail}` |")
    lines += ["", "Inputs re-derived from:", ""]
    for k, v in report["inputs"].items():
        lines.append(f"- `{k}`: {v}")
    with open(os.path.join(args.out, "REPORT.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    print(f"\n{report['summary']['passed']}/{report['summary']['total']} checks pass")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
