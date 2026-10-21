#!/usr/bin/env python3
"""Fetch untruncated Leaguepedia `Data:<OverviewPage>` match schedules & roster aliases.

Leaguepedia stores every tournament's canonical structured schedule and scores inside the
MediaWiki `Data:` namespace (`ns=10008`), e.g. `Data:Prime League 2nd Division/2027 Season/Fall Split`,
containing verbatim `{{MatchSchedule|team1=...|team2=...|team1score=...|team2score=...|winner=...|bestof=...}}`
entries. Querying `action=query&prop=revisions&rvprop=content&rvslots=main` in 40-page batches has
zero Cargo rate limits, returns full untruncated data in ~3 seconds, and provides exact SHA-256 receipts.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

OUT = Path("data/sources")
OUT.mkdir(parents=True, exist_ok=True)

API = "https://lol.fandom.com/api.php"
UA = "LOLHotspawnResearchBot/1.0 (+https://github.com/karagemop466-tech/LOLHOTSPAWN1; read-only research)"

# Canonical Leaguepedia overview pages covering 100% of all 27 Hotspawn LoL competitions
# plus official 2026 prior splits for hierarchical team strength calibration.
CANONICAL_OVERVIEW_PAGES: dict[str, list[str]] = {
    "Worlds 2026 Main Event": [
        "2026 Season World Championship/Main Event",
        "2026 Season World Championship/Play-In",
    ],
    "EM 2026 Summer Main Event": [
        "EMEA Masters/2026 Season/Summer Main Event",
        "EMEA Masters/2026 Season/Summer Play-In",
        "LFL/2026 Season/Summer Playoffs",
        "LFL/2026 Season/Summer Split",
    ],
    "LCP 2027 Promotion": [
        "LCP/2027 Season/Promotion",
        "PCS/2026 Season/Summer Season",
        "PCS/2026 Season/Summer Playoffs",
        "LCP/2026 Season/Season Finals",
    ],
    "LGC Rising 2026 Playoffs": [
        "LoL Game Changers/2026 Season/Playoffs",
        "LoL Game Changers/2026 Season/Stage 5",
        "LoL Game Changers/2026 Season/Stage 4",
        "LoL Game Changers/2026 Season/Stage 3",
        "LoL Game Changers/2026 Season/Stage 2",
        "LoL Game Changers/2026 Season/Stage 1",
    ],
    "PRM 2nd Division 26-27 Fall": [
        "Prime League 2nd Division/2027 Season/Fall Split",
        "Prime League 1st Division/2026 Season/Summer Split",
        "Prime League 1st Division/2026 Season/Spring Split",
        "Prime League 2nd Division/2026 Season/Spring Split",
        "Prime League 2nd Division/2026 Season/Winter Split",
    ],
    "PRM 3rd Division 26-27 Fall": [
        "Prime League 3rd Division/2027 Season/Fall Split",
        "Prime League 3rd Division/2026 Season/Spring Split",
        "Prime League 3rd Division/2026 Season/Winter Split",
    ],
    "4 Nations 2026 Halloween Heist": [
        "4 Nations/2026 Season/Halloween Heist",
        "4 Nations/2026 Season/Summer Playoffs",
        "4 Nations/2026 Season/Summer Split",
        "4 Nations/2026 Season/Spring Playoffs",
        "4 Nations/2026 Season/Spring Split",
    ],
    "RIVALS LEAGUE Season 2": [
        "RIVALS LEAGUE/2026 Season/Season 2",
        "RIVALS LEAGUE/2026 Season/Season 2 Playoffs",
        "RIVALS LEAGUE/2026 Season/Season 1",
        "RIVALS LEAGUE/2026 Season/Season 1 Playoffs",
    ],
    "Superstrike League 2026": [
        "Superstrike League 2026",
    ],
    "Tunisian Super League 2026": [
        "Tunisian Super League/2026 Season",
        "Tunisian Super League/2025 Season",
    ],
    "Arabian League 2nd Division 2026 Summer": [
        "Arabian League 2nd Division/2026 Season/Summer Split",
        "Arabian League 2nd Division/2026 Season/Spring Split",
        "Arabian League/2026 Season/Summer Split",
    ],
    "Arabian Regional Championship 2026: Lebanon-Libya-Syria-Palestine": [
        "Arabian Regional Championship 2026/Qualifiers/LB-Li-SY-PS",
    ],
    "Arabian Regional Championship 2026: Qatar-Bahrain-Kuwait": [
        "Arabian Regional Championship 2026/Qualifiers/QA-BH-KW",
    ],
    "Komplettligaen 2026 Autumn": [
        "Komplettligaen/2026 Season/Autumn Split",
        "Komplettligaen/2026 Season/Spring Playoffs",
        "Komplettligaen/2026 Season/Spring Split",
        "Good Game-ligaen/2026 Season/Winter Split",
    ],
    "Icelandic Esports League 2026 Autumn": [
        "Icelandic Esports League/2026 Season/Autumn Split",
        "Icelandic Esports League/2026 Season/Spring Playoffs",
        "Icelandic Esports League/2026 Season/Spring Split",
    ],
    "LigaGG CELOL B 2026 Split 2 Playoffs": [
        "LigaGG/CELOL Série B/2026 Season/Split 2 Playoffs",
        "LigaGG/CELOL Série B/2026 Season/Split 2",
        "LigaGG/CELOL Série B/2026 Season/Split 1 Playoffs",
        "LigaGG/CELOL Série B/2026 Season/Split 1",
    ],
    "LigaGG CELOL B 2026 Split 2": [
        "LigaGG/CELOL Série B/2026 Season/Split 2",
    ],
    "LigaGG CELOL A 2026 Split 2": [
        "LigaGG/CELOL Série A/2026 Season/Split 2 Playoffs",
        "LigaGG/CELOL Série A/2026 Season/Split 2",
    ],
    "Benelux Ascend Series 2026 Summer Split": [
        "Benelux Ascend Series/2026 Season/Summer Split",
        "Benelux Ascend Series/2026 Season/Spring Split",
    ],
    "Benelux Ascend Series 2026 Summer Playoffs": [
        "Benelux Ascend Series/2026 Season/Summer Playoffs",
        "Benelux Ascend Series/2026 Season/Summer Split",
    ],
    "Benelux Ascend Series 2027 Winter Promotion": [
        "Benelux Ascend Series/2027 Season/Winter Promotion",
    ],
    "Benelux Ascend Series Rising 2026 Summer Playoffs": [
        "Benelux Ascend Series Rising/2026 Season/Summer Playoffs",
        "Benelux Ascend Series Rising/2026 Season/Summer Open Tournaments/Open 1",
        "Benelux Ascend Series Rising/2026 Season/Summer Open Tournaments/Open 2",
        "Benelux Ascend Series Rising/2026 Season/Summer Open Tournaments/Open 3",
    ],
    "FPL 2026 Summer Playoffs": [
        "Finnish Pro League/2026 Season/Summer Playoffs",
        "Finnish Pro League/2026 Season/Summer Split",
    ],
    "Hitpoint 2nd Div Challengers 2026 Summer Playoffs": [
        "Hitpoint 2nd Division Challengers/2026 Season/Summer Playoffs",
        "Hitpoint 2nd Division Challengers/2026 Season/Summer Split",
    ],
    "LIT 2027 Winter Promotion": [
        "LIT/2027 Season/Winter Promotion",
    ],
    "Legends Academy powered by Żabka Season 3 Playoffs": [
        "Legends Academy/2026/Season 3 Playoffs",
        "Legends Academy/2026/Season 3 Group Stage",
    ],
    "POP Esports Masters Season 7": [
        "POP Esports Masters/Season 7",
    ],
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def batch_revisions(session: requests.Session, titles: list[str], receipts: list[dict[str, Any]]) -> dict[str, str]:
    found: dict[str, str] = {}
    unique = sorted(set(titles))
    for i in range(0, len(unique), 40):
        chunk = unique[i : i + 40]
        resp = session.get(
            API,
            params={
                "action": "query",
                "prop": "revisions",
                "rvprop": "content",
                "rvslots": "main",
                "redirects": "1",
                "titles": "|".join(chunk),
                "format": "json",
            },
            headers={"User-Agent": UA},
            timeout=30,
        )
        receipts.append({
            "batch_index": i,
            "count": len(chunk),
            "http_status": resp.status_code,
            "observed_at": utc_now(),
            "sha256": hashlib.sha256(resp.content).hexdigest(),
        })
        if resp.status_code != 200:
            continue
        q = resp.json().get("query") or {}
        norm_map = {n["from"]: n["to"] for n in q.get("normalized") or []}
        redir_map = {r["from"]: r["to"] for r in q.get("redirects") or []}
        by_title = {}
        for pid, pinfo in (q.get("pages") or {}).items():
            if int(pid) > 0:
                revs = pinfo.get("revisions") or []
                if revs:
                    by_title[pinfo["title"]] = ((revs[0].get("slots") or {}).get("main") or {}).get("*") or ""
        for orig in chunk:
            t1 = norm_map.get(orig, orig)
            t2 = redir_map.get(t1, t1)
            if t2 in by_title:
                found[orig] = by_title[t2]
                found[t2] = by_title[t2]
        time.sleep(0.1)
    return found


def harvest_all_data_pages(session: requests.Session | None = None) -> dict[str, Any]:
    sess = session or requests.Session()
    receipts: list[dict[str, Any]] = []
    overview_titles = sorted({t for lst in CANONICAL_OVERVIEW_PAGES.values() for t in lst})

    # 1. Fetch untruncated overview wikitext first to discover navbox splits (e.g. Prime League 25-26 pages)
    overview_wt = batch_revisions(sess, overview_titles, receipts)
    extra_prm_titles: list[str] = []
    for k, wt in list(overview_wt.items()):
        if "Prime League" in k:
            # Discover navbox links to recent Prime League 1st/2nd/3rd Division seasons
            for m in re.finditer(r"\[\[(Prime League [123](?:st|nd|rd) Division/[^\]]+?)\]\]", wt):
                target = m.group(1).split("|")[0].strip()
                if any(yr in target for yr in ("2026", "2027", "25-26", "26-27")) and target not in overview_wt:
                    extra_prm_titles.append(target)
    if extra_prm_titles:
        overview_wt.update(batch_revisions(sess, extra_prm_titles[:25], receipts))

    # 2. Fetch ALL `Data:<OverviewPage>` schedules (+ `Data:<OverviewPage>/...` sub-tabs if referenced)
    all_overviews = sorted(set(overview_wt.keys()))
    data_titles = [f"Data:{t}" for t in all_overviews]
    data_wt = batch_revisions(sess, data_titles, receipts)

    # Check if any `Data:` page contains `{{DataTabs` pointing to child subpages
    sub_data_titles: list[str] = []
    for dt_title, content in list(data_wt.items()):
        for m in re.finditer(r"\[\[(Data:[^\]|]+)", content):
            st = m.group(1).strip()
            if st not in data_wt:
                sub_data_titles.append(st)
    if sub_data_titles:
        data_wt.update(batch_revisions(sess, sub_data_titles[:40], receipts))

    # 3. Also resolve canonical Leaguepedia Teamnames (`Module:Teamnames` / `TeamRoster` names) via team redirects
    team_inputs = set()
    for content in list(overview_wt.values()) + list(data_wt.values()):
        for m in re.finditer(r"\|team[12]?=\s*([^|\n\}]+)", content):
            val = m.group(1).strip()
            if val and val.upper() != "TBD" and len(val) < 80:
                team_inputs.add(val)
    # Also include every Hotspawn participant name
    hs_path = OUT / "hotspawn_lol_fixtures.json"
    if hs_path.exists():
        for row in json.loads(hs_path.read_text(encoding="utf-8")):
            for fld in ("participants0_name", "participants1_name"):
                if row.get(fld):
                    team_inputs.add(str(row[fld]).strip())

    # Batch resolve MediaWiki redirects for all team strings -> canonical wiki page title
    team_redirects: dict[str, str] = {}
    tlist = sorted(team_inputs)
    for i in range(0, len(tlist), 50):
        chunk = tlist[i : i + 50]
        resp = sess.get(
            API,
            params={"action": "query", "redirects": "1", "titles": "|".join(chunk), "format": "json"},
            headers={"User-Agent": UA},
            timeout=25,
        )
        if resp.status_code == 200:
            q = resp.json().get("query") or {}
            nmap = {n["from"]: n["to"] for n in q.get("normalized") or []}
            rmap = {r["from"]: r["to"] for r in q.get("redirects") or []}
            existing = {p["title"] for pid, p in (q.get("pages") or {}).items() if int(pid) > 0}
            for orig in chunk:
                c = rmap.get(nmap.get(orig, orig), nmap.get(orig, orig))
                if c in existing:
                    team_redirects[orig] = c

    payload = {
        "harvested_at": utc_now(),
        "overview_count": len(overview_wt),
        "data_pages_count": len(data_wt),
        "team_redirects_count": len(team_redirects),
        "canonical_map": CANONICAL_OVERVIEW_PAGES,
        "overview_wikitext": overview_wt,
        "data_wikitext": data_wt,
        "team_redirects": team_redirects,
        "receipts": receipts,
    }
    (OUT / "leaguepedia_data_pages.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"Saved leaguepedia_data_pages.json: {len(overview_wt)} overviews, "
        f"{len(data_wt)} Data: pages, {len(team_redirects)} canonical team redirects"
    )
    return payload


if __name__ == "__main__":
    harvest_all_data_pages()
