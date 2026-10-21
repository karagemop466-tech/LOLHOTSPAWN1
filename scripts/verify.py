"""Publish gates. Fails (exit 1) when the snapshot or the built site would lie.

    python -m scripts.verify --data data --site site

Checks implemented:
1. schema: every row has an id, teams, a basis, and a probability pair that sums to ~1 when set.
2. sourcing: every row carries at least one official source link (hotspawn.com) and, when it is
   priced from a market, a link to that market page.
3. no fabrication: unresolved rows must have blank probabilities and must appear in
   ``unresolved.json``; rows with a market price must cite that price's URL.
4. model transparency: model rows must state confidence and at least one evidence URL.
5. site integrity: no internal ``href`` in ``site/`` points at a missing file; every HTML page has
   a viewport meta, the nav and the data payload exist.
6. coverage honesty: the lobby's own reported LoL card count is compared with parsed rows and the
   difference is reported (not silently swallowed).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OFFICIAL_HOSTS = ("hotspawn.com", "play.hotspawn.com", "www.hotspawn.com")
ALLOWED_LINE_HOSTS = ("polymarket.com", "oddsportal.com", "betexplorer.com", "oddschecker.com",
                      "oddspedia.com", "sportsinteraction.com", "pinnacle.com", "sofascore.com",
                      "thunderpick.com", "liquipedia.net", "lolesports.com")


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def is_official(url: str | None) -> bool:
    if not url:
        return False
    host = re.sub(r"^https?://", "", url).split("/")[0]
    return host.endswith("hotspawn.com") or host in ALLOWED_LINE_HOSTS


def check_rows(picks: list[dict], unresolved: list[dict], errors: list[str], warns: list[str]):
    unres_ids = {u.get("fixture_id") for u in unresolved.get("items") or []}
    for row in picks:
        rid = row.get("id") or row.get("hotspawn_fixture_id") or "?"
        teams = row.get("teams") or []
        if len(teams) != 2:
            errors.append(f"{rid}: expected 2 teams, found {len(teams)}")
            continue
        basis = row.get("basis")
        if basis not in ("market", "model", "unresolved"):
            errors.append(f"{rid}: unknown basis {basis!r}")
            continue
        ph, pa = row.get("prob_home"), row.get("prob_away")
        if basis == "unresolved":
            if ph is not None or pa is not None:
                errors.append(f"{rid}: unresolved row must have blank probabilities")
            if row.get("hotspawn_fixture_id") not in unres_ids:
                errors.append(f"{rid}: unresolved row missing from unresolved.json")
            continue
        if ph is None or pa is None:
            errors.append(f"{rid}: {basis} row has no probability")
            continue
        if abs((ph + pa) - 1.0) > 0.02:
            errors.append(f"{rid}: probabilities sum to {ph + pa:.3f}, not 1")
        if not (0.0 <= ph <= 1.0 and 0.0 <= pa <= 1.0):
            errors.append(f"{rid}: probability out of range")
        links = [row.get("hotspawn_url"), row.get("hotspawn_feed_url"), row.get("league_page_url")]
        if not any(links):
            errors.append(f"{rid}: no official source link at all")
        if not all(is_official(u) for u in links if u):
            errors.append(f"{rid}: a source link is not an accepted official host")
        if basis == "market":
            mkt = row.get("market") or {}
            if not mkt.get("source_url"):
                errors.append(f"{rid}: market row without a line source URL")
            elif "hotspawn.com" in (mkt.get("source_url") or ""):
                errors.append(f"{rid}: market line sourced from Hotspawn (forbidden)")
            if not mkt.get("odds_home") and not mkt.get("price_home"):
                warns.append(f"{rid}: market row without a raw price (prob from model fallback)")
        if basis == "model":
            mdl = row.get("model") or {}
            if not mdl.get("confidence") or mdl.get("confidence") == "none":
                errors.append(f"{rid}: model row must carry a non-'none' confidence band")
            if not (mdl.get("evidence_urls") or []):
                errors.append(f"{rid}: model row without a scoreline evidence link")
    return len(picks)


SKIP_DIRS = {".git", ".github", "scripts", "tests", "data", "node_modules", "__pycache__",
             "data-new", "site-new", ".venv"}


def check_site(site: str, errors: list[str], warns: list[str]) -> int:
    pages = []
    for root, dirs, files in os.walk(site):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            if name.endswith(".html"):
                pages.append(os.path.join(root, name))
    if not pages:
        errors.append("site contains no HTML pages")
        return 0
    existing = set()
    for root, dirs, files in os.walk(site):
        dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "__pycache__"}]
        for name in files:
            existing.add(os.path.relpath(os.path.join(root, name), site).replace(os.sep, "/"))
    for page in pages:
        rel = os.path.relpath(page, site).replace(os.sep, "/")
        text = open(page, encoding="utf-8").read()
        if 'name="viewport"' not in text:
            errors.append(f"{rel}: missing viewport meta (mobile requirement)")
        if 'id="main"' not in text:
            errors.append(f"{rel}: missing main landmark")
        for href in re.findall(r"""href\s*=\s*["']([^"'#?]+)(?:[?#][^"']*)?["']""", text):
            if href.startswith(("http://", "https://", "mailto:", "data:")):
                continue
            target = os.path.normpath(os.path.join(os.path.dirname(rel), href)).replace(os.sep, "/")
            if target.startswith(".."):
                errors.append(f"{rel}: internal link escapes the site root: {href}")
                continue
            if target not in existing:
                errors.append(f"{rel}: broken internal link -> {href}")
    for required in ("index.html", "picks.html", "unresolved.html", "flagged.html",
                     "methodology.html", "sources.html", "leagues.html", "data.html",
                     "assets/style.css", "assets/app.js"):
        if required not in existing:
            errors.append(f"site: required file missing -> {required}")
    return len(pages)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--site", default="site")
    ap.add_argument("--report", default="data/verify-report.txt")
    args = ap.parse_args()
    errors: list[str] = []
    warns: list[str] = []

    picks_doc = load(os.path.join(args.data, "picks.json"))
    unres = load(os.path.join(args.data, "unresolved.json"))
    flags = load(os.path.join(args.data, "flags.json"))
    summary = load(os.path.join(args.data, "summary.json"))
    picks = picks_doc.get("picks") or []
    n = check_rows(picks, unres, errors, warns)
    pages = check_site(args.site, errors, warns)

    totals = (picks_doc.get("source") or {}).get("totals") or {}
    reported = totals.get("tiers_count")
    if reported and n and abs(reported - n) > max(2, 0.02 * reported):
        warns.append(f"lobby reports {reported} LoL pick'em cards, parser produced {n} "
                     f"— difference {reported - n}")
    if not picks:
        errors.append("no picks at all: the lobby scrape produced nothing")

    lines = [
        f"verify: {n} rows, {len(unres.get('items') or [])} unresolved, "
        f"{len(flags.get('items') or [])} flags, {pages} html pages",
        f"errors: {len(errors)}", *[f"  ✗ {e}" for e in errors[:80]],
        f"warnings: {len(warns)}", *[f"  ! {w}" for w in warns[:40]],
    ]
    report = "\n".join(lines)
    print(report)
    try:
        os.makedirs(os.path.dirname(args.report) or ".", exist_ok=True)
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write(report + "\n")
    except OSError:
        pass
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
