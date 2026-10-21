#!/usr/bin/env python3
"""Strict line-by-line audit validator for JSON artifacts and all 9 HTML pages."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup

EXPECTED_PAGES = [
    "index.html",
    "picks.html",
    "featured.html",
    "originated.html",
    "unresolved.html",
    "tournaments.html",
    "teams.html",
    "methodology.html",
    "flagged.html",
]


def validate_all(root_dir: Path = Path(".")) -> dict[str, int]:
    errors: list[str] = []
    data_dir = root_dir / "data"

    for req_file in ("picks.json", "summary.json", "calibration.json", "teams_index.json", "flagged.json", "picks.csv"):
        if not (data_dir / req_file).exists():
            errors.append(f"Missing required artifact: data/{req_file}")
    if errors:
        raise AssertionError("\n".join(errors))

    picks_doc = json.loads((data_dir / "picks.json").read_text(encoding="utf-8"))
    summary = picks_doc["summary"]
    counts = summary["counts"]
    rows = picks_doc["picks"]

    # 1. Exact partition arithmetic checks
    if counts["open_total"] + counts["stale_past_lock_total"] != counts["lol_scheduled_total"]:
        errors.append("Open + stale counts do not sum to lol_scheduled_total")
    if (
        counts["tier1_market_total"] + counts["tier2_originated_total"] + counts["tier3_unresolved_open_total"]
        != counts["open_total"]
    ):
        errors.append("Tier1 + Tier2 + Tier3 counts do not sum to open_total")
    if counts["tier1_market_total"] + counts["tier2_originated_total"] != counts["actionable_open_picks"]:
        errors.append("Actionable open picks count mismatch")

    # 2. Line-by-line audit across all 264 fixture rows
    seen_ids: set[str] = set()
    for r in rows:
        fid = r["id"]
        if fid in seen_ids:
            errors.append(f"Duplicate fixture ID #{fid}")
        seen_ids.add(fid)

        # Every single row MUST carry verified `https://` official primary source links
        srcs = r.get("sources") or []
        if not srcs:
            errors.append(f"Fixture #{fid} has zero source links")
        for s in srcs:
            u = s.get("url") or ""
            if not u.startswith("https://"):
                errors.append(f"Fixture #{fid} has invalid source URL: {u!r}")

        # Zero crowd usage flag check
        if r["hotspawn_crowd_display_only"].get("used_in_model") is not False:
            errors.append(f"Fixture #{fid} violated used_in_model=False")

        # Unconfirmed upstream metadata must never be invented
        if str(r.get("raw_hotspawn_tier", "")).lower() == "waiting for information" and r.get("tier_display") != "":
            errors.append(f"Fixture #{fid} invented tier_display={r.get('tier_display')!r}")

        st = r["status"]
        if st in ("market_consensus", "esportsbook_line", "originated"):
            p0, p1 = r["team0_prob"], r["team1_prob"]
            if p0 is None or p1 is None:
                errors.append(f"Resolved fixture #{fid} missing probabilities")
            else:
                if not (0.001 < p0 < 0.999 and 0.001 < p1 < 0.999):
                    errors.append(f"Out-of-bounds probability on #{fid}: {p0}, {p1}")
                if abs((p0 + p1) - 1.0) > 1e-3:
                    errors.append(f"Probabilities do not sum to 1.0 on #{fid}: {p0} + {p1}")
                expected_pick = r["team0"] if p0 >= p1 else r["team1"]
                if r["pick"] != expected_pick:
                    errors.append(f"Pick direction mismatch on #{fid}: got {r['pick']}, expected {expected_pick}")

            if st in ("market_consensus", "esportsbook_line"):
                md = r.get("market_detail") or {}
                for v in md.get("venues") or []:
                    if v.get("venue_key") == "esportsbook":
                        if abs(float(v["dec0"]) - 1.80) < 1e-6 and abs(float(v["dec1"]) - 1.80) < 1e-6:
                            errors.append(f"Placeholder 1.80/1.80 leaked into #{fid}")

    # 3. Validate all 9 HTML pages, anchors, assets, and per-row source links
    page_anchors: dict[str, set[str]] = {}
    parsed_pages: dict[str, BeautifulSoup] = {}
    for pname in EXPECTED_PAGES:
        pfile = root_dir / pname
        if not pfile.exists():
            errors.append(f"Missing expected HTML page: {pname}")
            continue
        raw_html = pfile.read_text(encoding="utf-8")
        for bad_tok in ("NaN%", "None%", "undefined"):
            if bad_tok in raw_html:
                errors.append(f"{pname} contains forbidden rendering token {bad_tok!r}")
        soup = BeautifulSoup(raw_html, "html.parser")
        parsed_pages[pname] = soup
        page_anchors[pname] = {el["id"] for el in soup.find_all(attrs={"id": True})}
        vp = soup.find("meta", attrs={"name": "viewport"})
        if not vp or "width=device-width" not in (vp.get("content") or ""):
            errors.append(f"{pname} missing responsive viewport meta tag")

    checked_links = 0
    checked_table_rows = 0
    for pname, soup in parsed_pages.items():
        # Verify internal & external links
        for tag in soup.find_all(["a", "link", "script"]):
            attr = "href" if tag.name in ("a", "link") else "src"
            ref = tag.get(attr)
            if not ref:
                continue
            checked_links += 1
            parsed = urlparse(ref)
            if parsed.scheme in ("http", "https"):
                if not parsed.netloc:
                    errors.append(f"{pname}: malformed external link {ref!r}")
            elif parsed.scheme == "":
                target_path = parsed.path or pname
                local_target = root_dir / target_path
                if not local_target.exists():
                    errors.append(f"{pname}: broken relative link {ref!r}")
                if parsed.fragment and target_path in page_anchors:
                    if parsed.fragment not in page_anchors[target_path]:
                        errors.append(f"{pname}: broken fragment #{parsed.fragment} in {ref!r}")

        # Verify every pick card has at least one `https://` source chip
        for idx_c, card in enumerate(soup.select(".pick-card")):
            ext_links = [a["href"] for a in card.find_all("a", href=True) if a["href"].startswith("https://")]
            if not ext_links:
                errors.append(f"{pname}: pick-card #{idx_c} has zero external https:// source links")

        # Verify every match/audit table row (except calibration decile summary table) has source links
        for tbl in soup.select("table.data-table"):
            headers = [th.get_text(strip=True).lower() for th in tbl.select("thead th")]
            if any("source" in h or "links" in h for h in headers):
                for idx_tr, tr in enumerate(tbl.select("tbody tr")):
                    checked_table_rows += 1
                    ext_links = [
                        a["href"]
                        for a in tr.find_all("a", href=True)
                        if a["href"].startswith("https://")
                    ]
                    if not ext_links:
                        errors.append(f"{pname}: table row #{idx_tr} missing https:// source link")

    if errors:
        raise AssertionError("Validation failed:\n  - " + "\n  - ".join(errors[:30]))

    return {
        "rows_validated": len(rows),
        "pages_validated": len(parsed_pages),
        "links_checked": checked_links,
        "sourced_table_rows_checked": checked_table_rows,
    }


if __name__ == "__main__":
    stats = validate_all()
    print(f"VALIDATION PASSED: {json.dumps(stats)}")
    sys.exit(0)
