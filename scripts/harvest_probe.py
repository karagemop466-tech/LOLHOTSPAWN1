#!/usr/bin/env python3
"""Live multi-source discovery & harvest probe for Hotspawn League of Legends Pick'ems.

Collects verbatim, read-only public responses with full HTTP receipts & SHA-256 hashes from:
  1. Hotspawn scheduled LoL API, all-sports API, /lol-pickems SSR hydration, and /lobby SSR hydration
  2. Pinnacle public guest API (all League of Legends leagues, matchups, and straight moneylines)
  3. Polymarket Gamma public API (all open League of Legends events & match markets)
  4. Kalshi public Trade API v2 (open League of Legends match/series markets)
  5. Official Riot LoL Esports API (leagues, schedules, standings) + public esportsbook probes
  6. Leaguepedia (lol.fandom.com MediaWiki query/parse + polite Cargo probe) for all 27 tournaments & teams
  7. Prime League official portal (primeleague.gg Fall Split 2026/27 groups & division tables)
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode, urlparse

import requests
from bs4 import BeautifulSoup

OUT = Path("raw_harvest")
OUT.mkdir(parents=True, exist_ok=True)

UA = "LOLHotspawnResearchBot/1.0 (+https://github.com/karagemop466-tech/LOLHOTSPAWN1; read-only research)"
BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

RECEIPTS: list[dict[str, Any]] = []


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def fetch_raw(
    session: requests.Session,
    url: str,
    label: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    as_json: bool = False,
    timeout: int = 30,
) -> tuple[Any, dict[str, Any]]:
    t0 = time.monotonic()
    req_headers = {"User-Agent": UA, "Accept": "application/json,text/html;q=0.9,*/*;q=0.8"}
    if headers:
        req_headers.update(headers)
    rec: dict[str, Any] = {
        "label": label,
        "requested_url": url,
        "params": params,
        "observed_at": utc_now(),
        "http_status": None,
        "ok": False,
    }
    try:
        resp = session.get(url, headers=req_headers, params=params, timeout=timeout, allow_redirects=True)
        elapsed_ms = round((time.monotonic() - t0) * 1000)
        rec.update(
            final_url=resp.url,
            http_status=resp.status_code,
            content_type=resp.headers.get("Content-Type", ""),
            bytes=len(resp.content),
            sha256=hashlib.sha256(resp.content).hexdigest(),
            elapsed_ms=elapsed_ms,
            cache_status=resp.headers.get("X-Cache"),
            cache_age=resp.headers.get("Age"),
        )
        RECEIPTS.append(rec)
        if resp.status_code != 200:
            rec["error"] = f"HTTP {resp.status_code}: {resp.text[:240]}"
            return None, rec
        data = resp.json() if as_json else resp.text
        rec["ok"] = True
        return data, rec
    except Exception as exc:
        rec["error"] = f"{type(exc).__name__}: {exc}"
        RECEIPTS.append(rec)
        return None, rec


def save_json(name: str, obj: Any) -> None:
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_ng_state(html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    node = soup.find("script", id="ng-state")
    if not node or not node.string:
        return {"found": False, "entries": [], "permalinks": {}, "fixtures": []}
    state = json.loads(node.string)
    entries = []
    permalinks: dict[str, str] = {}
    fixtures: list[dict[str, Any]] = []
    for k, v in state.items():
        if isinstance(v, dict):
            u = v.get("u", "")
            b = v.get("b")
            entries.append({
                "key": k,
                "url": u,
                "status": v.get("s"),
                "body_type": type(b).__name__,
                "len": len(b) if isinstance(b, (list, dict, str)) else None,
            })
            if urlparse(u).path == "/api/v1/fixtures" and isinstance(b, list):
                fixtures = b
            if isinstance(b, dict) and isinstance(b.get("permalinks"), dict):
                permalinks.update({str(pk): str(pv) for pk, pv in b["permalinks"].items() if pv})
    return {
        "found": True,
        "entries": entries,
        "permalinks": permalinks,
        "fixture_count": len(fixtures),
        "lol_fixture_ids": sorted([str(x.get("id")) for x in fixtures if x.get("sport_alias") == "lol"]),
        "sports_counts": {
            sp: sum(1 for x in fixtures if x.get("sport_alias") == sp)
            for sp in sorted({str(x.get("sport_alias")) for x in fixtures})
        },
    }


def harvest_hotspawn(session: requests.Session) -> list[dict[str, Any]]:
    print("[1/7] Harvesting Hotspawn API + SSR hydration...")
    lol_api_url = "https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=lol&status=scheduled&tenantId=1"
    all_api_url = "https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?status=scheduled&tenantId=1"
    lol_fixtures, _ = fetch_raw(session, lol_api_url, "hotspawn_api_lol", headers={"User-Agent": BROWSER_UA}, as_json=True)
    all_fixtures, _ = fetch_raw(session, all_api_url, "hotspawn_api_all", headers={"User-Agent": BROWSER_UA}, as_json=True)

    cb = str(int(time.time()))
    lol_html, _ = fetch_raw(session, f"https://play.hotspawn.com/lol-pickems?cb={cb}", "hotspawn_page_lol", headers={"User-Agent": BROWSER_UA})
    lobby_html, _ = fetch_raw(session, f"https://play.hotspawn.com/lobby?cb={cb}", "hotspawn_page_lobby", headers={"User-Agent": BROWSER_UA})

    lol_state = parse_ng_state(lol_html or "")
    lobby_state = parse_ng_state(lobby_html or "")

    # Also test direct permalinks API if present in hydration URLs
    direct_permalinks = {}
    for entry in lol_state.get("entries", []) + lobby_state.get("entries", []):
        u = entry.get("url", "")
        if "permalinks" in u and u.startswith("http"):
            pdata, _ = fetch_raw(session, u, "hotspawn_api_permalinks", headers={"User-Agent": BROWSER_UA}, as_json=True)
            if isinstance(pdata, dict) and isinstance(pdata.get("permalinks"), dict):
                direct_permalinks.update({str(k): str(v) for k, v in pdata["permalinks"].items() if v})
            break

    merged_permalinks = {}
    merged_permalinks.update(lobby_state.get("permalinks", {}))
    merged_permalinks.update(lol_state.get("permalinks", {}))
    merged_permalinks.update(direct_permalinks)

    save_json("hotspawn_lol_fixtures.json", lol_fixtures or [])
    save_json("hotspawn_all_summary.json", {
        "total_all_scheduled": len(all_fixtures or []),
        "by_sport": {
            sp: sum(1 for r in (all_fixtures or []) if r.get("sport_alias") == sp)
            for sp in sorted({str(r.get("sport_alias")) for r in (all_fixtures or [])})
        },
        "lol_state": {k: v for k, v in lol_state.items() if k != "permalinks"},
        "lobby_state": {k: v for k, v in lobby_state.items() if k != "permalinks"},
        "permalinks_count": len(merged_permalinks),
    })
    save_json("hotspawn_permalinks.json", merged_permalinks)
    print(f"  -> {len(lol_fixtures or [])} LoL fixtures, {len(merged_permalinks)} permalinks")
    return lol_fixtures or []


def harvest_pinnacle(session: requests.Session) -> None:
    print("[2/7] Harvesting Pinnacle Guest Esports API...")
    base = "https://guest.api.arcadia.pinnacle.com/0.1"
    leagues, _ = fetch_raw(session, f"{base}/sports/12/leagues", "pinnacle_esports_leagues", headers={"User-Agent": BROWSER_UA}, as_json=True)
    matchups, _ = fetch_raw(session, f"{base}/sports/12/matchups", "pinnacle_esports_matchups", headers={"User-Agent": BROWSER_UA}, as_json=True)
    lol_leagues = []
    if isinstance(leagues, list):
        for lg in leagues:
            name = str(lg.get("name", ""))
            if any(tok in name.lower() for tok in ("league of legends", "lol", "worlds", "emea", "lck", "lpl", "lec", "lcs", "lcp", "prime league")):
                lol_leagues.append(lg)
    lol_markets: dict[str, Any] = {}
    for lg in lol_leagues:
        lid = lg.get("id")
        if lid and (lg.get("matchupCount", 0) > 0 or lg.get("matchupCountSE", 0) > 0):
            m, _ = fetch_raw(session, f"{base}/leagues/{lid}/markets/straight", f"pinnacle_straight_{lid}", headers={"User-Agent": BROWSER_UA}, as_json=True)
            lol_markets[str(lid)] = m
            time.sleep(0.2)
    # Also scan all matchups whose league name mentions LoL / League of Legends
    lol_matchups = []
    all_league_names = sorted({str((m.get("league") or {}).get("name", "")) for m in (matchups or []) if isinstance(m, dict)})
    for m in (matchups or []):
        if not isinstance(m, dict):
            continue
        lname = str((m.get("league") or {}).get("name", ""))
        if any(tok in lname.lower() for tok in ("league of legends", "lol")):
            lol_matchups.append(m)
            lid = (m.get("league") or {}).get("id")
            if lid and str(lid) not in lol_markets:
                mk, _ = fetch_raw(session, f"{base}/leagues/{lid}/markets/straight", f"pinnacle_straight_{lid}", headers={"User-Agent": BROWSER_UA}, as_json=True)
                lol_markets[str(lid)] = mk
    save_json("pinnacle_lol.json", {
        "all_esports_league_names_with_active_matchups": all_league_names,
        "lol_leagues": lol_leagues,
        "lol_matchups": lol_matchups,
        "lol_straight_markets": lol_markets,
    })
    print(f"  -> {len(lol_leagues)} Pinnacle LoL leagues, {len(lol_matchups)} LoL matchups across {len(lol_markets)} market feeds")


def harvest_polymarket_and_kalshi(session: requests.Session) -> None:
    print("[3/7] Harvesting Polymarket Gamma API & Kalshi Public API...")
    poly_events: dict[str, Any] = {}
    for tag in ("league-of-legends", "lol", "esports"):
        for offset in (0, 100, 200, 300):
            data, _ = fetch_raw(
                session,
                "https://gamma-api.polymarket.com/events",
                f"polymarket_{tag}_{offset}",
                params={"tag_slug": tag, "closed": "false", "limit": 100, "offset": offset},
                headers={"User-Agent": BROWSER_UA},
                as_json=True,
            )
            if not isinstance(data, list) or not data:
                break
            for ev in data:
                slug = str(ev.get("slug", ""))
                title = str(ev.get("title", ""))
                if tag in ("league-of-legends", "lol") or any(
                    k in (slug + " " + title).lower()
                    for k in ("lol-", "league of legends", "worlds", "emea masters", "galions", "solary", "lcp")
                ):
                    poly_events[str(ev.get("id"))] = {
                        "id": ev.get("id"),
                        "slug": slug,
                        "title": title,
                        "startDate": ev.get("startDate"),
                        "endDate": ev.get("endDate"),
                        "volume": ev.get("volume"),
                        "liquidity": ev.get("liquidity"),
                        "markets": [
                            {
                                "id": m.get("id"),
                                "question": m.get("question"),
                                "slug": m.get("slug"),
                                "outcomes": m.get("outcomes"),
                                "outcomePrices": m.get("outcomePrices"),
                                "bestBid": m.get("bestBid"),
                                "bestAsk": m.get("bestAsk"),
                                "lastTradePrice": m.get("lastTradePrice"),
                                "volumeNum": m.get("volumeNum"),
                                "liquidityNum": m.get("liquidityNum"),
                                "gameStartTime": m.get("gameStartTime"),
                                "sportsMarketType": m.get("sportsMarketType"),
                                "active": m.get("active"),
                                "closed": m.get("closed"),
                            }
                            for m in (ev.get("markets") or [])
                        ],
                    }
            if len(data) < 100:
                break
    save_json("polymarket_lol.json", list(poly_events.values()))

    # Kalshi public open events check
    kalshi_found = []
    for series in ("KXLOLGAME", "KXLOLMATCH", "KXLOLWORLDS", "KXLOL"):
        kd, _ = fetch_raw(
            session,
            "https://api.elections.kalshi.com/trade-api/v2/events",
            f"kalshi_{series}",
            params={"series_ticker": series, "status": "open", "with_nested_markets": "true", "limit": 100},
            headers={"User-Agent": BROWSER_UA},
            as_json=True,
        )
        if isinstance(kd, dict) and kd.get("events"):
            kalshi_found.extend(kd["events"])
    save_json("kalshi_lol.json", kalshi_found)
    print(f"  -> {len(poly_events)} Polymarket LoL events, {len(kalshi_found)} Kalshi LoL events")


def harvest_riot_and_esportsbooks(session: requests.Session) -> None:
    print("[4/7] Harvesting Official Riot LoL Esports API + probing esportsbooks...")
    riot_key = {"x-api-key": "0TvQnueqKa5mxJntVWt0w4LpLfEkrV1Ta8rQBb9Z", "User-Agent": BROWSER_UA}
    riot_leagues, _ = fetch_raw(
        session,
        "https://esports-api.lolesports.com/persisted/gw/getLeagues?hl=en-US",
        "riot_get_leagues",
        headers=riot_key,
        as_json=True,
    )
    riot_schedule = {}
    if isinstance(riot_leagues, dict):
        leagues_list = ((riot_leagues.get("data") or {}).get("leagues")) or []
        target_slugs = ("worlds", "emea_masters", "lcp", "arabian_league", "prime_league", "lit", "hitpoint_masters", "ultraliga", "nlc", "lfl")
        wanted_ids = [
            str(lg["id"])
            for lg in leagues_list
            if any(s in str(lg.get("slug", "")).lower() or s in str(lg.get("name", "")).lower() for s in target_slugs)
        ]
        if wanted_ids:
            sched, _ = fetch_raw(
                session,
                "https://esports-api.lolesports.com/persisted/gw/getSchedule",
                "riot_get_schedule",
                params={"hl": "en-US", "leagueId": ",".join(wanted_ids[:20])},
                headers=riot_key,
                as_json=True,
            )
            riot_schedule = sched or {}
    save_json("riot_esports.json", {"leagues": riot_leagues, "schedule": riot_schedule})

    # Read-only diagnostic probes of esportsbooks & odds boards
    probes = {}
    probe_targets = [
        ("egamersworld_lol", "https://egamersworld.com/lol/matches"),
        ("tipsgg_lol", "https://tips.gg/lol/matches/"),
        ("rdygg_lol_matches", "https://rdy.gg/en/lol/matches"),
        ("rdygg_lol_tournaments", "https://rdy.gg/en/lol/tournaments"),
        ("gosugamers_lol", "https://www.gosugamers.net/lol/matches"),
        ("strafe_lol", "https://www.strafe.com/esports-betting/lol/"),
        ("thunderpick_lol", "https://thunderpick.io/esports/league-of-legends"),
        ("ggbet_lol", "https://gg.bet/en/league-of-legends"),
        ("oddsportal_lol", "https://www.oddsportal.com/esports/league-of-legends/"),
        ("gamer_no_lol", "https://www.gamer.no/turneringer/spill/league-of-legends"),
    ]
    for name, url in probe_targets:
        text, rec = fetch_raw(session, url, f"probe_{name}", headers={"User-Agent": BROWSER_UA}, timeout=20)
        sample = ""
        odds_pairs = []
        if isinstance(text, str):
            sample = re.sub(r"\s+", " ", BeautifulSoup(text, "html.parser").get_text(" "))[:1500]
            odds_pairs = re.findall(r"(\d+\.\d{2})\s+Make a bet\s+(\d+\.\d{2})", sample)[:25]
        probes[name] = {
            "url": url,
            "http_status": rec.get("http_status"),
            "bytes": rec.get("bytes"),
            "error": rec.get("error"),
            "odds_pairs_sample": odds_pairs,
            "text_sample": sample,
            "raw_html_saved": False,
        }
        if isinstance(text, str) and rec.get("http_status") == 200 and len(text) < 2_500_000:
            (OUT / f"page_{name}.html").write_text(text, encoding="utf-8")
            probes[name]["raw_html_saved"] = True
        time.sleep(0.25)
    save_json("esportsbooks_probe.json", probes)


def harvest_leaguepedia(session: requests.Session, fixtures: list[dict[str, Any]]) -> None:
    print("[5/7] Harvesting Leaguepedia (lol.fandom.com) for all 27 tournaments & all 189 teams...")
    api = "https://lol.fandom.com/api.php"
    competitions = sorted({str(f.get("competition_name", "")).strip() for f in fixtures if f.get("competition_name")})
    teams = sorted({
        str(t).strip()
        for f in fixtures
        for t in (f.get("participants0_name"), f.get("participants1_name"))
        if t and str(t).strip()
    })

    # 1. Discover exact canonical page title for every competition via MediaWiki search + redirects
    comp_pages: dict[str, Any] = {}
    for comp in competitions:
        sdata, _ = fetch_raw(
            session,
            api,
            f"lp_search_{re.sub(r'[^a-zA-Z0-9]+', '_', comp)[:40]}",
            params={"action": "query", "list": "search", "srsearch": comp, "srlimit": 8, "format": "json"},
            as_json=True,
        )
        hits = [h["title"] for h in ((sdata or {}).get("query") or {}).get("search", [])]
        # Fetch full parsed text + wikitext of top candidate pages
        pages_fetched = []
        candidates = []
        for h in hits:
            if "/Scoreboards" in h or "/Picks and Bans" in h or "/Champion" in h or "/Statistics" in h:
                continue
            candidates.append(h)
            if len(candidates) >= 2:
                break
        if not candidates and hits:
            candidates = hits[:1]
        for title in candidates:
            pdata, _ = fetch_raw(
                session,
                api,
                f"lp_parse_{re.sub(r'[^a-zA-Z0-9]+', '_', title)[:40]}",
                params={"action": "parse", "page": title, "prop": "wikitext|text", "redirects": "1", "format": "json"},
                as_json=True,
            )
            pobj = (pdata or {}).get("parse") or {}
            if pobj:
                pages_fetched.append({
                    "title": pobj.get("title", title),
                    "pageid": pobj.get("pageid"),
                    "url": "https://lol.fandom.com/wiki/" + quote(str(pobj.get("title", title)).replace(" ", "_"), safe="/:"),
                    "wikitext": ((pobj.get("wikitext") or {}).get("*")) or "",
                    "text": BeautifulSoup(((pobj.get("text") or {}).get("*")) or "", "html.parser").get_text("\n"),
                })
            time.sleep(0.12)
        comp_pages[comp] = {"search_hits": hits, "pages": pages_fetched}
        print(f"  [LP comp] {comp} -> {[p['title'] for p in pages_fetched]}")

    save_json("leaguepedia_competitions.json", comp_pages)

    # 2. Batch query all 189 team pages + their "/Match History" or wikitext via 50-title batches!
    team_pages: dict[str, Any] = {}
    # Resolve exact titles / redirects in batches of 50
    for i in range(0, len(teams), 50):
        batch = teams[i : i + 50]
        qdata, _ = fetch_raw(
            session,
            api,
            f"lp_teams_batch_{i}",
            params={
                "action": "query",
                "titles": "|".join(batch),
                "redirects": "1",
                "prop": "revisions|info",
                "rvprop": "content",
                "rvslots": "main",
                "inprop": "url",
                "format": "json",
            },
            as_json=True,
        )
        qobj = (qdata or {}).get("query") or {}
        redirects_map = {r["from"]: r["to"] for r in qobj.get("redirects") or []}
        norm_map = {n["from"]: n["to"] for n in qobj.get("normalized") or []}
        pages_by_title = {}
        for pid, pinfo in (qobj.get("pages") or {}).items():
            if int(pid) > 0:
                revs = pinfo.get("revisions") or []
                content = ""
                if revs:
                    content = ((revs[0].get("slots") or {}).get("main") or {}).get("*") or ""
                pages_by_title[pinfo["title"]] = {
                    "pageid": int(pid),
                    "title": pinfo["title"],
                    "fullurl": pinfo.get("fullurl"),
                    "wikitext": content[:12000],
                }
        for t in batch:
            t1 = norm_map.get(t, t)
            t2 = redirects_map.get(t1, t1)
            team_pages[t] = pages_by_title.get(t2)
        time.sleep(0.15)

    # For any team missing direct exact title match, run search to catch "(Benelux Team)", "(Norwegian Team)", etc.!
    missing_teams = [t for t, v in team_pages.items() if v is None]
    print(f"  -> Direct Leaguepedia team hits: {len(teams) - len(missing_teams)}/{len(teams)}; searching remaining {len(missing_teams)}...")
    for t in missing_teams:
        sd, _ = fetch_raw(
            session,
            api,
            f"lp_tsearch_{re.sub(r'[^a-zA-Z0-9]+', '_', t)[:35]}",
            params={"action": "query", "list": "search", "srsearch": f'"{t}"', "srlimit": 5, "format": "json"},
            as_json=True,
        )
        hits = [h["title"] for h in ((sd or {}).get("query") or {}).get("search", [])]
        team_pages[t] = {"pageid": None, "title": None, "search_hits": hits}
        time.sleep(0.08)

    # Also fetch "<ResolvedTeamTitle>/Match History" in 50-title batches for every resolved Leaguepedia team!
    resolved_titles = sorted({
        v["title"]
        for v in team_pages.values()
        if isinstance(v, dict) and v.get("title")
    })
    match_histories: dict[str, str] = {}
    for i in range(0, len(resolved_titles), 25):
        batch = resolved_titles[i : i + 25]
        for title in batch:
            pdata, _ = fetch_raw(
                session,
                api,
                f"lp_mh_{re.sub(r'[^a-zA-Z0-9]+', '_', title)[:35]}",
                params={"action": "parse", "page": f"{title}/Match_History", "prop": "text", "redirects": "1", "format": "json"},
                as_json=True,
            )
            pobj = (pdata or {}).get("parse") or {}
            if pobj and (pobj.get("text") or {}).get("*"):
                txt = BeautifulSoup(pobj["text"]["*"], "html.parser").get_text("\n")
                match_histories[title] = txt[:15000]
            time.sleep(0.08)

    save_json("leaguepedia_teams.json", {"teams": team_pages, "match_histories": match_histories})
    print(f"  -> Saved {len(match_histories)} official Leaguepedia team Match History pages")


def harvest_primeleague(session: requests.Session) -> None:
    print("[6/7] Harvesting Prime League official Fall Split 2026/27 division pages...")
    overview_url = "https://www.primeleague.gg/en/leagues/prm/3227-fall-split-202627"
    html, rec = fetch_raw(session, overview_url, "primeleague_fall_overview", headers={"User-Agent": BROWSER_UA})
    groups: dict[str, Any] = {"overview_url": overview_url, "http_status": rec.get("http_status"), "group_links": [], "groups": {}}
    if isinstance(html, str):
        soup = BeautifulSoup(html, "html.parser")
        seen = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            txt = re.sub(r"\s+", " ", a.get_text(" ")).strip()
            if "/stages/" in href or "/groups/" in href:
                full = href if href.startswith("http") else "https://www.primeleague.gg" + href
                if full not in seen:
                    seen.add(full)
                    groups["group_links"].append({"text": txt, "url": full})
        # Fetch all 2nd & 3rd division group / stage pages (typically ~12-16 pages total)
        for item in groups["group_links"][:35]:
            u = item["url"]
            if any(k in (item["text"] + " " + u).lower() for k in ("2.", "3.", "group 2", "group 3", "gruppe 2", "gruppe 3", "league 2", "league 3", "2nd", "3rd", "stage")):
                ghtml, grec = fetch_raw(session, u, f"prm_{len(groups['groups'])}", headers={"User-Agent": BROWSER_UA})
                if isinstance(ghtml, str) and grec.get("http_status") == 200:
                    gsoup = BeautifulSoup(ghtml, "html.parser")
                    # Also look for sub-group links inside stage pages
                    for suba in gsoup.find_all("a", href=True):
                        shref = suba["href"]
                        if "/groups/" in shref:
                            sfull = shref if shref.startswith("http") else "https://www.primeleague.gg" + shref
                            if sfull not in seen and len(groups["group_links"]) < 80:
                                seen.add(sfull)
                                groups["group_links"].append({"text": re.sub(r"\s+", " ", suba.get_text(" ")).strip(), "url": sfull})
                    groups["groups"][u] = {
                        "label": item["text"],
                        "text": gsoup.get_text("\n")[:25000],
                    }
                time.sleep(0.15)
    save_json("primeleague_fall.json", groups)
    print(f"  -> Fetched {len(groups['groups'])} Prime League stage/group pages")


def main() -> None:
    session = requests.Session()
    fixtures = harvest_hotspawn(session)
    harvest_pinnacle(session)
    harvest_polymarket_and_kalshi(session)
    harvest_riot_and_esportsbooks(session)
    harvest_leaguepedia(session, fixtures)
    harvest_primeleague(session)
    print("[7/7] Writing audit receipt manifest...")
    save_json("receipts_manifest.json", {
        "harvested_at": utc_now(),
        "total_requests": len(RECEIPTS),
        "ok_requests": sum(1 for r in RECEIPTS if r.get("ok")),
        "receipts": RECEIPTS,
    })
    print("Harvest complete!")


if __name__ == "__main__":
    main()
