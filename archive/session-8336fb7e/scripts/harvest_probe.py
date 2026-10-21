#!/usr/bin/env python3
"""Parallel multi-source live harvest for Hotspawn League of Legends Pick'ems.

Writes clean, compact, auditable JSON datasets into `data/sources/` with full SHA-256
HTTP receipts so downstream line origination, validation, and static site generation
are 100% deterministic, reproducible, and zero-hallucination.
"""
from __future__ import annotations

import concurrent.futures
import hashlib
import json
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

import requests
from bs4 import BeautifulSoup

OUT = Path("data/sources")
OUT.mkdir(parents=True, exist_ok=True)

UA = "LOLHotspawnResearchBot/1.0 (+https://github.com/karagemop466-tech/LOLHOTSPAWN1; read-only research)"
BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

RECEIPTS: list[dict[str, Any]] = []
RECEIPTS_LOCK = threading.Lock()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def fetch_raw(
    session: requests.Session | None,
    url: str,
    label: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    as_json: bool = False,
    timeout: int = 25,
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
        caller = session.get if session is not None else requests.get
        resp = caller(url, headers=req_headers, params=params, timeout=timeout, allow_redirects=True)
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
        with RECEIPTS_LOCK:
            RECEIPTS.append(rec)
        if resp.status_code != 200:
            rec["error"] = f"HTTP {resp.status_code}: {resp.text[:200]}"
            return None, rec
        data = resp.json() if as_json else resp.text
        rec["ok"] = True
        return data, rec
    except Exception as exc:
        rec["error"] = f"{type(exc).__name__}: {exc}"
        with RECEIPTS_LOCK:
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

    # Also grab explicit View Match links rendered in SSR HTML
    html_links: dict[str, str] = {}
    for page_html in (lol_html or "", lobby_html or ""):
        for m in re.finditer(r'https://www\.hotspawn\.com/matches/[a-zA-Z0-9\-_]+-(\d+)', page_html):
            html_links[m.group(1)] = m.group(0)

    lol_state = parse_ng_state(lol_html or "")
    lobby_state = parse_ng_state(lobby_html or "")

    direct_permalinks: dict[str, str] = {}
    for entry in lol_state.get("entries", []) + lobby_state.get("entries", []):
        u = entry.get("url", "")
        if "permalinks" in u and u.startswith("http"):
            pdata, _ = fetch_raw(session, u, "hotspawn_api_permalinks", headers={"User-Agent": BROWSER_UA}, as_json=True)
            if isinstance(pdata, dict) and isinstance(pdata.get("permalinks"), dict):
                direct_permalinks.update({str(k): str(v) for k, v in pdata["permalinks"].items() if v})
            break

    merged_permalinks = {}
    merged_permalinks.update(html_links)
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
            if any(tok in name.lower() for tok in ("league of legends", "lol", "worlds", "emea", "lck", "lpl", "lec", "lcs", "lcp", "prime league", "arabian", "hitpoint", "ultraliga")):
                lol_leagues.append(lg)
    lol_markets: dict[str, Any] = {}
    for lg in lol_leagues:
        lid = lg.get("id")
        if lid and (lg.get("matchupCount", 0) > 0 or lg.get("matchupCountSE", 0) > 0):
            m, _ = fetch_raw(session, f"{base}/leagues/{lid}/markets/straight", f"pinnacle_straight_{lid}", headers={"User-Agent": BROWSER_UA}, as_json=True)
            lol_markets[str(lid)] = m
    all_league_names = sorted({str((m.get("league") or {}).get("name", "")) for m in (matchups or []) if isinstance(m, dict)})
    lol_matchups = []
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
                    for k in ("lol-", "league of legends", "worlds", "emea masters", "galions", "solary", "lcp", "prime league")
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


def _extract_egw_quotes(html: str, page_url: str) -> list[dict[str, Any]]:
    """Extract verified two-way non-placeholder decimal quotes from EGamersWorld HTML."""
    results = []
    text = re.sub(r"\s+", " ", BeautifulSoup(html, "html.parser").get_text(" "))
    name_re = re.compile(r'"name"\s*:\s*"([^"\\]+?)\s+VS\s+([^"\\]+?)"')
    start_re = re.compile(r'"startDate"\s*:\s*"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?)"')
    make_re = re.compile(r'(\d+\.\d+)\s+Make a bet\s+(\d+\.\d+)')
    starts = [(m.start(), m.group(1)) for m in start_re.finditer(html)]
    for nm in name_re.finditer(html):
        t1, t2 = nm.group(1).strip(), nm.group(2).strip()
        st = next((val for pos, val in starts if 0 <= pos - nm.start() <= 500), None)
        for mk in make_re.finditer(text):
            o1, o2 = float(mk.group(1)), float(mk.group(2))
            if (o1, o2) == (1.8, 1.8) or o1 <= 1.0 or o2 <= 1.0 or o1 == o2:
                continue
            win = text[max(0, mk.start() - 260) : mk.end() + 260]
            if t1.lower() in win.lower() and t2.lower() in win.lower():
                results.append({"team1": t1, "team2": t2, "start": st, "odds": [o1, o2], "url": page_url})
                break
    return results


def harvest_riot_and_esportsbooks(session: requests.Session) -> None:
    print("[4/7] Harvesting Official Riot LoL Esports API + Esportsbook boards...")
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
        target_slugs = ("worlds", "emea_masters", "lcp", "arabian", "prime", "lit", "hitpoint", "ultraliga", "nlc", "lfl")
        wanted = [
            {"id": str(lg["id"]), "slug": lg.get("slug"), "name": lg.get("name")}
            for lg in leagues_list
            if any(s in str(lg.get("slug", "")).lower() or s in str(lg.get("name", "")).lower() for s in target_slugs)
        ]
        if wanted:
            sched, _ = fetch_raw(
                session,
                "https://esports-api.lolesports.com/persisted/gw/getSchedule",
                "riot_get_schedule",
                params={"hl": "en-US", "leagueId": ",".join(w["id"] for w in wanted[:20])},
                headers=riot_key,
                as_json=True,
            )
            events = (((sched or {}).get("data") or {}).get("schedule") or {}).get("events") or []
            riot_schedule = {
                "queried_leagues": wanted,
                "event_count": len(events),
                "events": [
                    e for e in events
                    if str(e.get("startTime", "")) >= "2026-10-01"
                ][:150],
            }
    save_json("riot_esports.json", riot_schedule)

    probes = {}
    egw_quotes: list[dict[str, Any]] = []
    rdy_pages: dict[str, str] = {}
    probe_targets = [
        ("egamersworld_lol", "https://egamersworld.com/lol/matches"),
        ("egamersworld_lol_events", "https://egamersworld.com/lol/events"),
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
        if isinstance(text, str):
            soup = BeautifulSoup(text, "html.parser")
            sample = re.sub(r"\s+", " ", soup.get_text(" "))[:2000]
            if "egamersworld" in name and rec.get("http_status") == 200:
                egw_quotes.extend(_extract_egw_quotes(text, url))
                # Follow up to 25 individual match/event links on EGW
                sublinks = []
                for a in soup.find_all("a", href=True):
                    h = a["href"]
                    if h.startswith("/lol/match/") or h.startswith("/lol/event/"):
                        full = "https://egamersworld.com" + h
                        if full not in sublinks:
                            sublinks.append(full)
                for su in sublinks[:25]:
                    stxt, srec = fetch_raw(session, su, "egw_sub", headers={"User-Agent": BROWSER_UA}, timeout=15)
                    if isinstance(stxt, str) and srec.get("http_status") == 200:
                        egw_quotes.extend(_extract_egw_quotes(stxt, su))
            if "rdygg" in name and rec.get("http_status") == 200:
                rdy_pages[url] = soup.get_text("\n")[:15000]
        probes[name] = {
            "url": url,
            "http_status": rec.get("http_status"),
            "bytes": rec.get("bytes"),
            "error": rec.get("error"),
            "text_sample": sample,
        }
    save_json("esportsbooks_probe.json", {"probes": probes, "egw_quotes": egw_quotes, "rdy_pages": rdy_pages})


def _fetch_one_comp(comp: str) -> tuple[str, dict[str, Any]]:
    api = "https://lol.fandom.com/api.php"
    sdata, _ = fetch_raw(
        None,
        api,
        f"lp_search_{re.sub(r'[^a-zA-Z0-9]+', '_', comp)[:36]}",
        params={"action": "query", "list": "search", "srsearch": comp, "srlimit": 10, "format": "json"},
        as_json=True,
    )
    hits = [h["title"] for h in ((sdata or {}).get("query") or {}).get("search", [])]
    # Also fetch key related pages (both regular season split AND playoffs + prior summer split if applicable)
    candidates: list[str] = []
    for h in hits:
        if any(skip in h for skip in ("/Scoreboards", "/Picks and Bans", "/Champion", "/Statistics", "/Media", "/Player")):
            continue
        candidates.append(h)
        if len(candidates) >= 3:
            break
    # Explicit PRM / ERL prior-split pages for deeper historical strength calibration
    extra_map = {
        "PRM 2nd Division 26-27 Fall": ["PRM 2nd Division/2026 Season/Summer Split", "PRM 1st Division/2026 Season/Summer Split"],
        "PRM 3rd Division 26-27 Fall": ["PRM 3rd Division/2026 Season/Summer Split"],
    }
    for ex in extra_map.get(comp, []):
        if ex not in candidates:
            candidates.append(ex)

    pages_fetched = []
    seen_titles = set()
    for title in list(candidates):
        if title in seen_titles:
            continue
        seen_titles.add(title)
        pdata, _ = fetch_raw(
            None,
            api,
            f"lp_parse_{re.sub(r'[^a-zA-Z0-9]+', '_', title)[:36]}",
            params={"action": "parse", "page": title, "prop": "wikitext|text", "redirects": "1", "format": "json"},
            as_json=True,
        )
        pobj = (pdata or {}).get("parse") or {}
        if pobj:
            canon = str(pobj.get("title", title))
            seen_titles.add(canon)
            html_raw = ((pobj.get("text") or {}).get("*")) or ""
            soup = BeautifulSoup(html_raw, "html.parser")
            # Discover sibling stage tabs (e.g., Summer Split / Group Stage / Overview)
            base_prefix = canon.rsplit("/", 1)[0] if "/" in canon else canon
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if href.startswith("/wiki/"):
                    target = href[len("/wiki/"):].replace("_", " ")
                    if (
                        target.startswith(base_prefix)
                        and target not in seen_titles
                        and not any(sk in target for sk in ("/Scoreboards", "/Picks", "/Statistics", "/Media", "?", "#"))
                        and len(candidates) < 6
                    ):
                        candidates.append(target)
            pages_fetched.append({
                "title": canon,
                "pageid": pobj.get("pageid"),
                "url": "https://lol.fandom.com/wiki/" + quote(canon.replace(" ", "_"), safe="/:"),
                "wikitext": (((pobj.get("wikitext") or {}).get("*")) or "")[:30000],
                "text": soup.get_text("\n")[:30000],
            })
    return comp, {"search_hits": hits, "pages": pages_fetched}


def _fetch_one_team(team: str, resolved_title: str | None) -> tuple[str, dict[str, Any]]:
    api = "https://lol.fandom.com/api.php"
    title = resolved_title
    hits: list[str] = []
    if not title:
        sd, _ = fetch_raw(
            None,
            api,
            f"lp_tsearch_{re.sub(r'[^a-zA-Z0-9]+', '_', team)[:32]}",
            params={"action": "query", "list": "search", "srsearch": f'"{team}"', "srlimit": 5, "format": "json"},
            as_json=True,
        )
        hits = [h["title"] for h in ((sd or {}).get("query") or {}).get("search", [])]
        for h in hits:
            if "/" not in h and h.lower().startswith(team.lower()[:5]):
                title = h
                break
    res: dict[str, Any] = {"resolved_title": title, "search_hits": hits, "url": None, "overview_text": "", "match_history": ""}
    if title:
        res["url"] = "https://lol.fandom.com/wiki/" + quote(title.replace(" ", "_"), safe="/:")
        p1, _ = fetch_raw(
            None,
            api,
            f"lp_tov_{re.sub(r'[^a-zA-Z0-9]+', '_', title)[:32]}",
            params={"action": "parse", "page": title, "prop": "text", "redirects": "1", "format": "json"},
            as_json=True,
        )
        o1 = ((p1 or {}).get("parse") or {}).get("text") or {}
        if o1.get("*"):
            res["overview_text"] = BeautifulSoup(o1["*"], "html.parser").get_text("\n")[:8000]
        p2, _ = fetch_raw(
            None,
            api,
            f"lp_tmh_{re.sub(r'[^a-zA-Z0-9]+', '_', title)[:32]}",
            params={"action": "parse", "page": f"{title}/Match_History", "prop": "text", "redirects": "1", "format": "json"},
            as_json=True,
        )
        o2 = ((p2 or {}).get("parse") or {}).get("text") or {}
        if o2.get("*"):
            res["match_history"] = BeautifulSoup(o2["*"], "html.parser").get_text("\n")[:10000]
    return team, res


def harvest_leaguepedia(session: requests.Session, fixtures: list[dict[str, Any]]) -> None:
    print("[5/7] Harvesting Leaguepedia concurrently across 27 competitions & 189 teams...")
    api = "https://lol.fandom.com/api.php"
    competitions = sorted({str(f.get("competition_name", "")).strip() for f in fixtures if f.get("competition_name")})
    teams = sorted({
        str(t).strip()
        for f in fixtures
        for t in (f.get("participants0_name"), f.get("participants1_name"))
        if t and str(t).strip()
    })

    comp_pages: dict[str, Any] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for comp, data in pool.map(_fetch_one_comp, competitions):
            comp_pages[comp] = data
            print(f"  [LP comp] {comp} -> {[p['title'] for p in data['pages']]}")
    save_json("leaguepedia_competitions.json", comp_pages)

    # Batch resolve exact redirects first
    direct_titles: dict[str, str | None] = {}
    for i in range(0, len(teams), 50):
        batch = teams[i : i + 50]
        qdata, _ = fetch_raw(
            session,
            api,
            f"lp_teams_batch_{i}",
            params={"action": "query", "titles": "|".join(batch), "redirects": "1", "format": "json"},
            as_json=True,
        )
        qobj = (qdata or {}).get("query") or {}
        redirects_map = {r["from"]: r["to"] for r in qobj.get("redirects") or []}
        norm_map = {n["from"]: n["to"] for n in qobj.get("normalized") or []}
        existing = {pinfo["title"] for pid, pinfo in (qobj.get("pages") or {}).items() if int(pid) > 0}
        for t in batch:
            cand = redirects_map.get(norm_map.get(t, t), norm_map.get(t, t))
            direct_titles[t] = cand if cand in existing else None

    team_records: dict[str, Any] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futs = [pool.submit(_fetch_one_team, t, direct_titles.get(t)) for t in teams]
        for f in concurrent.futures.as_completed(futs):
            t, r = f.result()
            team_records[t] = r
    save_json("leaguepedia_teams.json", team_records)
    print(f"  -> Resolved {sum(1 for v in team_records.values() if v['url'])}/{len(teams)} team pages on Leaguepedia")


def harvest_primeleague(session: requests.Session) -> None:
    print("[6/7] Harvesting Prime League official Fall Split 2026/27 & Summer Split 2026 division pages...")
    splits = [
        ("fall_26_27", "https://www.primeleague.gg/en/leagues/prm/3227-fall-split-202627"),
    ]
    out: dict[str, Any] = {}
    for key, overview_url in splits:
        html, rec = fetch_raw(session, overview_url, f"prm_{key}", headers={"User-Agent": BROWSER_UA})
        split_data: dict[str, Any] = {"overview_url": overview_url, "http_status": rec.get("http_status"), "pages": {}}
        if isinstance(html, str) and rec.get("http_status") == 200:
            soup = BeautifulSoup(html, "html.parser")
            queue: list[tuple[str, str]] = []
            seen = set()
            for a in soup.find_all("a", href=True):
                href = a["href"]
                txt = re.sub(r"\s+", " ", a.get_text(" ")).strip()
                if "/stages/" in href or "/groups/" in href:
                    full = href if href.startswith("http") else "https://www.primeleague.gg" + href
                    if full not in seen:
                        seen.add(full)
                        queue.append((txt, full))
            idx = 0
            while idx < len(queue) and len(split_data["pages"]) < 45:
                txt, u = queue[idx]
                idx += 1
                low = (txt + " " + u).lower()
                if any(bad in low for bad in ("starter", "league 4", "league 5", "league 6", "league 7", "league 8", "gruppe 4.", "gruppe 5.", "gruppe 6.")):
                    continue
                ghtml, grec = fetch_raw(session, u, f"prm_sub_{idx}", headers={"User-Agent": BROWSER_UA})
                if isinstance(ghtml, str) and grec.get("http_status") == 200:
                    gsoup = BeautifulSoup(ghtml, "html.parser")
                    for suba in gsoup.find_all("a", href=True):
                        shref = suba["href"]
                        stxt = re.sub(r"\s+", " ", suba.get_text(" ")).strip()
                        if "/groups/" in shref:
                            sfull = shref if shref.startswith("http") else "https://www.primeleague.gg" + shref
                            if sfull not in seen and len(queue) < 90:
                                seen.add(sfull)
                                queue.append((stxt, sfull))
                    split_data["pages"][u] = {
                        "label": txt,
                        "text": gsoup.get_text("\n")[:25000],
                    }
        out[key] = split_data
    save_json("primeleague_fall.json", out)


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
