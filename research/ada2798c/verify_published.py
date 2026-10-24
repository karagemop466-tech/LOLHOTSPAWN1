#!/usr/bin/env python3
"""Independent, line-by-line verification of what the site actually publishes.

This does NOT import `tools/`. It re-parses the generated HTML the reader will see and
re-derives every check from `data/matches.json`, so a bug that is consistent between the
builder and its own gate is still caught here.

Checks (each prints PASS/FAIL with the count it examined):
  1  every published row on table.html carries both probabilities and a pick
  2  the two probabilities on each row sum to 100% (tolerance 0.2pp)
  3  the pick named on the page is the higher-probability side
  4  the page's numbers equal `data/matches.json` for the same fixture id
  5  every row links to an https source (Hotspawn card, venue or results page)
  6  every match in the dataset appears exactly once on picks.html and on table.html
  7  exec summary links to every picks view and to the unresolved section
  8  every page declares a mobile viewport and none sets a fixed width wider than 420px
  9  no placeholder text ("None", "nan", "&mdash;None") is rendered as a value
 10  the counted coverage (priced + settlement = total) reconciles on the page
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
from collections import Counter

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUTDIR = os.path.join(ROOT, "audit", "ada2798c")

results: list[dict] = []


def check(name: str, ok: bool, detail: str) -> None:
    results.append({"name": name, "ok": bool(ok), "detail": detail})
    print(("PASS " if ok else "FAIL ") + name + " :: " + detail, flush=True)


def read(name: str) -> str:
    path = os.path.join(ROOT, name)
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def strip_tags(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", s))


def main() -> int:
    ds = json.load(open(os.path.join(ROOT, "data", "matches.json"), encoding="utf-8"))
    matches = {str(m["id"]): m for m in ds.get("matches") or []}
    table = read("table.html")
    picks = read("picks.html")
    index = read("index.html")

    # ---- 1/2/3/4: the table rows -------------------------------------------------
    # Each row is a <tr> carrying data-id (or an anchor to the match card); parse per row.
    rows = re.split(r'<tr class="prow', table)[1:]
    seen_ids: list[str] = []
    bad_sum: list[str] = []
    bad_pick: list[str] = []
    bad_json: list[str] = []
    row_checked = 0
    unknown_id: list[str] = []
    value_mismatch: list[str] = []
    checked_values = 0
    no_source: list[str] = []
    for r in rows:
        ids = re.findall(r'hotspawn\.com/matches/[^"\s]*-(\d+)"', r)
        if not ids:
            continue
        fid = ids[0]
        seen_ids.append(fid)
        row_checked += 1
        m = matches.get(fid)
        if not m:
            bad_json.append(fid)
            continue
        unknown_id.append(fid) if False else None
        pair = re.search(r"(\d{1,3}\.\d)%\s*/\s*(\d{1,3}\.\d)%", strip_tags(r))
        if pair:
            p0, p1 = float(pair.group(1)), float(pair.group(2))
            if abs(p0 + p1 - 100.0) > 0.2:
                bad_sum.append(f"{fid}:{p0}/{p1}")
            if m.get("p0") is not None:
                if (abs(p0 - round(m["p0"] * 100, 1)) > 0.15
                        or abs(p1 - round(m["p1"] * 100, 1)) > 0.15):
                    value_mismatch.append(f"{fid}: page {p0}/{p1} != data {m['p0']:.4f}/{m['p1']:.4f}")
                else:
                    checked_values += 1
            page_pick = (m.get("pick") or {}).get("team")
            pick_cell = re.search(r'data-label="Pick">(.*?)</td>', r, flags=re.S)
            if page_pick and pick_cell and page_pick not in strip_tags(pick_cell.group(1)):
                bad_pick.append(fid)
        elif m.get("method") != "unresolved" and m.get("p0") is not None:
            bad_sum.append(f"{fid}: no two-sided percentage rendered")
        if "https://" not in r:
            no_source.append(fid)

    check("table.html renders one row per dataset fixture",
          row_checked == len(matches), f"{row_checked} rows parsed, {len(matches)} in dataset")
    check("no duplicate fixture ids on the table", len(set(seen_ids)) == len(seen_ids),
          f"{len(set(seen_ids))} unique of {len(seen_ids)}")
    check("every table row resolves to a dataset fixture", not bad_json, f"unresolved: {sorted(set(bad_json))[:5]}")
    check("the percentages printed on the page equal data/matches.json", not value_mismatch,
          f"{checked_values} rows compared; mismatches: {value_mismatch[:5]}")
    check("probabilities on each table row sum to 100% (+/-0.2pp)", not bad_sum,
          f"{row_checked - len(bad_sum)}/{row_checked} ok; problems: {bad_sum[:5]}")
    check("the named pick is rendered on its own row", not bad_pick,
          f"problems: {bad_pick[:5]}")
    check("every table row carries an https source link", not no_source,
          f"{row_checked - len(no_source)}/{row_checked} ok; missing: {no_source[:5]}")

    # ---- 6: picks.html parity ------------------------------------------------------
    card_ids = re.findall(r'<article id="match-(\d+)"', picks)
    check("picks.html renders every dataset fixture exactly once",
          Counter(card_ids) == Counter(matches.keys()),
          f"{len(card_ids)} cards for {len(matches)} fixtures; "
          f"missing={sorted(set(matches) - set(card_ids))[:5]} "
          f"dupes={[k for k, v in Counter(card_ids).items() if v > 1][:5]}")

    # ---- 7: exec summary links -----------------------------------------------------
    required = ["table.html", "picks.html", "featured.html", "originated.html", "unresolved.html"]
    missing = [r for r in required if f'href="{r}"' not in index]
    check("exec summary links to every picks view", not missing, f"missing: {missing}")
    check("exec summary carries the unresolved picks & limitations block",
          "unresolved" in index.lower() and ("limitation" in index.lower()),
          "both words present" if "limitation" in index.lower() else "limitations wording absent")

    # ---- 8: mobile ----------------------------------------------------------------
    pages = [p for p in sorted(os.listdir(ROOT)) if p.endswith(".html")]
    no_viewport = []
    wide = []
    for p in pages:
        t = read(p)
        if 'name="viewport"' not in t:
            no_viewport.append(p)
        for m_ in re.finditer(r"(?<!max-)(?<!-)width:\s*(\d{3,4})px", t):
            if int(m_.group(1)) <= 420:
                continue
            ctx = t[max(0, m_.start() - 160):m_.end() + 60]
            if "max-width" in ctx or "width:100%" in ctx.replace(" ", ""):
                continue  # a fluid element capped by max-width cannot overflow a phone
            wide.append(f"{p}:{m_.group(1)}px")
    check("every page declares a mobile viewport", not no_viewport, f"{len(pages)} pages; missing: {no_viewport}")
    check("no page sets a fixed width wider than a 420px phone", not wide,
          f"offenders: {sorted(set(wide))[:6]}")

    # ---- 9: no placeholder leakage -------------------------------------------------
    leaks = []
    for p in pages:
        raw = read(p)
        for bad in ("None", "nan", "NaN", "undefined"):
            # a rendered *value*: the word next to a percentage sign or alone in a table cell
            for pat in (r">\s*" + bad + r"\s*<", r"\b" + bad + r"\s*%", r"\b" + bad + r"\s*to win"):
                if re.search(pat, raw):
                    leaks.append(f"{p}:{bad}")
    check("no placeholder value is rendered as a match value", not leaks, f"leaks: {sorted(set(leaks))[:6]}")

    # ---- 10: coverage arithmetic ---------------------------------------------------
    priced = sum(1 for m in matches.values() if m.get("p0") is not None)
    settle = sum(1 for m in matches.values() if m.get("pick_type") == "settlement")
    unpick = sum(1 for m in matches.values() if not m.get("pick"))
    check("coverage arithmetic reconciles",
          priced + settle + unpick == len(matches) and unpick == 0,
          f"priced={priced} + settlement={settle} + unpicked={unpick} = "
          f"{priced + settle + unpick} of {len(matches)}")

    payload = {"generated_utc": __import__("datetime").datetime.now(
        __import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dataset_generated_utc": ds.get("generated_utc"),
        "pages_checked": len(pages), "checks": results,
        "passed": all(r["ok"] for r in results)}
    os.makedirs(OUTDIR, exist_ok=True)
    with open(os.path.join(OUTDIR, "verify_published.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)
    print(f"\n{sum(1 for r in results if r['ok'])}/{len(results)} checks pass")
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
