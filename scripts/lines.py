"""External betting lines for Hotspawn LoL pick'ems (never Hotspawn's own pick share).

Sources are probed in the order the brief asks for:

1. Established sportsbooks / aggregators with machine-readable odds tables:
   * OddsPortal (odds comparison for LoL) — parsed.
   * Polymarket (public gamma API) — parsed.
2. Esports books / betting-line pages that are commonly used for LoL — *probed* and reported
   honestly (``probes``): if the response is a bot wall or has no parseable odds table, that is
   recorded as a limitation instead of pretending a line exists.

A line is attached to a pick'em only when both team labels match the fixture's team names
(:func:`scripts.common.team_match`).  Anything ambiguous is dropped and flagged.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from .common import (
    Fetcher, canon_team, devig_two_way, find_links, implied_prob, iso, log, pct, utcnow,
    write_debug,
)

ODDSPORT_INDEX = "https://www.oddsportal.com/esports/league-of-legends/"
POLYMARKET_SEARCH = "https://gamma-api.polymarket.com/public-search"

# Public pages that *should* carry LoL lines; tried for coverage, reported verbatim.
PROBES = [
    ("BetExplorer (esports book aggregator)", "https://www.betexplorer.com/esports/league-of-legends/"),
    ("Oddschecker (odds comparison)", "https://www.oddschecker.com/esports/league-of-legends"),
    ("Oddspedia (livescore + odds)", "https://en.oddspedia.com/league-of-legends"),
    ("SportsInteraction (odds comparison)", "https://www.sportsinteraction.com/esports/league-of-legends/odds"),
    ("Pinnacle (sportsbook)", "https://www.pinnacle.com/en/esports/matchups"),
    ("Betway Esports (sportsbook)", "https://sports.betway.com/en/bet/sport/40010572/cmp/123456"),
    ("Sofascore (LoL livescore API)", "https://api.sofascore.com/api/v1/sport/esports/season/9539/scheduled-categories"),
    ("Thunderpick (Hotspawn partner book)", "https://api.thunderpick.com/api/v1/sports-wallet/events?sportId=20"),
    ("Liquipedia LoL (schedule/results wiki)", "https://liquipedia.net/leagueoflegends/index.php?search=Worlds+2026&title=Special:Search"),
    ("LoL Esports official API (Riot)", "https://esports-api.lolesports.com/persisted/gw/getLeagues?hlsg=en"),
]

ODDS_NUM = re.compile(r"(?<![\d.])(\d{1,3}\.\d{2})(?![\d.])")
DAY_HEAD = re.compile(r"\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)(?:\s+(\d{4}))?\b")


def pair_key(a: str | None, b: str | None) -> str:
    ca, cb = sorted([canon_team(a or ""), canon_team(b or "")])
    return f"{ca}|{cb}"


# --------------------------------------------------------------------------- OddsPortal
def _oddsportal_tournaments(markup: str) -> list[str]:
    links = find_links(markup, r"/esports/league-of-legends/[a-z0-9\-]+/?$")
    out = []
    for href in links:
        if href.rstrip("/").endswith("/league-of-legends"):
            continue
        full = href if href.startswith("http") else "https://www.oddsportal.com" + href
        if full not in out:
            out.append(full)
    return out


def _row_teams(cell_text: str) -> list[str]:
    """Team labels inside an OddsPortal fixture cell (img alt or plain text)."""
    names = re.findall(r"""alt\s*=\s*["']([^"']{2,60})["']""", cell_text or "")
    cleaned = []
    for name in names:
        name = re.sub(r"\s+", " ", name).strip()
        if name and not re.search(r"logo|icon|flag", name, re.I) and name not in cleaned:
            cleaned.append(name)
    if len(cleaned) >= 2:
        return cleaned[:2]
    text = re.sub(r"(?s)<[^>]+>", "\n", cell_text or "")
    for raw in text.split("\n"):
        line = re.sub(r"\s+", " ", raw).strip()
        if not line or len(line) > 60:
            continue
        if re.fullmatch(r"\d{1,2}:\d{2}.*", line):
            continue
        if re.fullmatch(r"[\d\s:\-.+–]+", line):
            continue
        if line.lower() in ("vs", "-", "postponed", "cancelled"):
            continue
        if line not in cleaned:
            cleaned.append(line)
    return cleaned[:2]


def parse_oddsportal_page(markup: str, page_url: str) -> list[dict]:
    """Rows of ``[fixture cell][home odds][away odds]`` from an OddsPortal tournament page."""
    rows: list[dict] = []
    chunks = re.split(r"(?is)</tr>", markup or "")
    for chunk in chunks:
        chunk = chunk[-12000:]
        if "/esports/h2h/" not in chunk:
            continue
        m = re.search(r"""(?is)href\s*=\s*["']([^"']*/esports/h2h/[^"']+)["']""", chunk)
        if not m:
            continue
        href = m.group(1)
        full = href if href.startswith("http") else "https://www.oddsportal.com" + href
        anchor = re.search(r"(?is)<a\b[^>]*>(.*?)</a>", chunk[chunk.find(m.group(0)):][:2600])
        teams = _row_teams(anchor.group(1) if anchor else chunk)
        if len(teams) < 2:
            continue
        tail = chunk[chunk.find(m.group(0)) + len(m.group(0)):]
        tail = re.split(r"(?is)<tr\b", tail)[0]
        odds = ODDS_NUM.findall(re.sub(r"(?s)<[^>]+>", " ", tail))
        label_m = DAY_HEAD.search(re.sub(r"(?s)<[^>]+>", " ", chunk[-2600:]))
        time_m = re.search(r"\b(\d{1,2}):(\d{2})\b", re.sub(r"(?s)<[^>]+>", " ", chunk))
        if len(odds) < 2:
            rows.append({"teams": teams, "odds": [], "url": full,
                         "day_label": label_m.group(0) if label_m else None,
                         "time_label": time_m.group(0) if time_m else None,
                         "note": "no odds in row (market not open or blocked)"})
            continue
        rows.append({
            "teams": teams,
            "odds": [float(o) for o in odds[:2]],
            "odds_raw": odds[:4],
            "url": full,
            "page_url": page_url,
            "day_label": label_m.group(0) if label_m else None,
            "time_label": time_m.group(0) if time_m else None,
        })
    return rows


def collect_oddsportal(fetcher: Fetcher) -> tuple[list[dict], dict]:
    meta = {"index_url": ODDSPORT_INDEX, "tournaments": [], "rows": 0, "status": "unreachable"}
    index = fetcher.get(ODDSPORT_INDEX)
    if not index:
        return [], meta
    tourneys = _oddsportal_tournaments(index)
    meta["status"] = "ok" if tourneys else "ok (no LoL tournaments listed right now)"
    meta["tournaments"] = tourneys
    rows: list[dict] = []
    for url in tourneys[:24]:
        body = fetcher.get(url)
        if not body:
            meta.setdefault("failed_pages", []).append(url)
            continue
        found = parse_oddsportal_page(body, url)
        for row in found:
            row["source"] = "OddsPortal"
            row["tournament_url"] = url
        rows.extend(found)
        log(f"  oddsportal {url.rsplit('/', 2)[-2]}: {len(found)} rows")
    meta["rows"] = len(rows)
    return rows, meta


# --------------------------------------------------------------------------- Polymarket
def _pm_list(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return [x.strip().strip('"') for x in value.strip("[]").split(",")]
    return value or []


def collect_polymarket(fetcher: Fetcher, queries: list[str]) -> tuple[list[dict], dict]:
    """Two-outcome Polymarket markets for the given search queries (LoL events)."""
    out: list[dict] = []
    meta = {"queries": [], "events": 0, "markets": 0, "status": "unreachable"}
    seen_events = set()
    for q in queries:
        url = f"{POLYMARKET_SEARCH}?q={requests_quote(q)}&limit_per_type=25&events_status=active"
        data = fetcher.get_json(url)
        entry = {"query": q, "url": url, "events": 0, "error": None}
        if not isinstance(data, dict):
            entry["error"] = "no JSON response"
            meta["queries"].append(entry)
            continue
        events = data.get("events") or []
        entry["events"] = len(events)
        meta["queries"].append(entry)
        meta["status"] = "ok"
        for ev in events:
            ev_id = ev.get("id") or ev.get("slug")
            if ev_id in seen_events:
                continue
            seen_events.add(ev_id)
            meta["events"] += 1
            title = re.sub(r"\s+", " ", ev.get("title") or "")
            for mk in ev.get("markets") or []:
                question = re.sub(r"\s+", " ", mk.get("question") or "")
                outcomes = [str(x) for x in _pm_list(mk.get("outcomes"))]
                prices = []
                for x in _pm_list(mk.get("outcomePrices")):
                    try:
                        prices.append(float(x))
                    except Exception:
                        prices.append(None)
                if len(outcomes) != 2 or len(prices) != 2 or any(p is None for p in prices):
                    continue
                total = sum(prices)
                if total <= 0:
                    continue
                slug = mk.get("slug") or ev.get("slug") or ""
                out.append({
                    "source": "Polymarket",
                    "question": question,
                    "event_title": title,
                    "outcomes": outcomes,
                    "prices": prices,
                    "devig": [p / total for p in prices],
                    "url": f"https://polymarket.com/event/{ev.get('slug') or slug}",
                    "active": mk.get("closed") in (False, None, "false"),
                    "end_date": mk.get("endDate") or ev.get("endDate"),
                    "volume": mk.get("volumeNum") or mk.get("volume"),
                })
                meta["markets"] += 1
    if not meta["queries"]:
        meta["status"] = "not attempted"
    elif meta["status"] != "ok":
        meta["status"] = "blocked/unreachable"
    return out, meta


def requests_quote(text: str) -> str:
    from urllib.parse import quote
    return quote(text)


# --------------------------------------------------------------------------- attach lines
def attach(lines_pm: list[dict], lines_op: list[dict], matches: list[dict]) -> tuple[dict, list[dict]]:
    """Map external prices onto pick'em cards by team pair, refusing ambiguous joins."""
    by_pair: dict[str, list[dict]] = {}

    def add(pair, payload):
        by_pair.setdefault(pair, []).append(payload)

    for row in lines_op:
        teams = row.get("teams") or []
        if len(teams) < 2 or not row.get("odds"):
            continue
        o_a, o_b = row["odds"][0], row["odds"][1]
        p_a, p_b = implied_prob(decimal=o_a), implied_prob(decimal=o_b)
        dv = devig_two_way(p_a, p_b) if p_a and p_b else None
        add(pair_key(teams[0], teams[1]), {
            "source": "OddsPortal",
            "source_label": f"OddsPortal — {teams[0]} vs {teams[1]} (comparison of {len(row.get('odds_raw') or [])} listed books)",
            "url": row.get("url") or row.get("tournament_url"),
            "page_url": row.get("tournament_url"),
            "market": "Series winner (1X2 without draw)",
            "teams": teams,
            "odds_home": o_a,
            "odds_away": o_b,
            "implied_home_raw": round(p_a, 4) if p_a else None,
            "implied_away_raw": round(p_b, 4) if p_b else None,
            "devig_home": round(dv[0], 4) if dv else None,
            "devig_away": round(dv[1], 4) if dv else None,
            "klyuchenko_note": "proportional (multiplicative) devig; two-way market",
            "as_of": row.get("day_label"),
            "fetched_utc": iso(utcnow()),
        })

    for row in lines_pm:
        outs = row.get("outcomes") or []
        home = "Team " + outs[0] if len(outs) > 0 else None
        add(pair_key(outs[0], outs[1]) if len(outs) == 2 else "", {
            "source": "Polymarket",
            "source_label": f"Polymarket — {row.get('question')}",
            "url": row.get("url"),
            "market": "binary market price",
            "teams": outs,
            "devig_home": round(row["devig"][0], 4),
            "devig_away": round(row["devig"][1], 4),
            "price_home": row["prices"][0],
            "price_away": row["prices"][1],
            "volume": row.get("volume"),
            "fetched_utc": iso(utcnow()),
        })

    attached, flags = {}, []
    for match in matches:
        teams = match.get("teams") or []
        if len(teams) < 2:
            continue
        key = pair_key(teams[0], teams[1])
        cands = by_pair.get(key) or []
        if not cands:
            continue
        # de-duplicate identical fixtures from the same source (e.g. duplicate rows in a table)
        uniq = {}
        for c in cands:
            uniq.setdefault((c["source"], c.get("url"), c.get("devig_home")), c)
        cands = list(uniq.values())
        per_source: dict[str, list[dict]] = {}
        for c in cands:
            per_source.setdefault(c["source"], []).append(c)
        chosen = {}
        for src, group in per_source.items():
            if len(group) > 1:
                probs = {round(g.get("devig_home") or -1, 3) for g in group}
                if len(probs) > 1:
                    flags.append({
                        "match": f"{teams[0]} vs {teams[1]}",
                        "fixture_id": match.get("fixture_id"),
                        "field": f"line:{src}",
                        "reason": ("more than one market for this team pair with different prices — "
                                   "line NOT attached because the fixture could not be identified "
                                   "uniquely from the source page alone"),
                        "candidates": [g.get("url") for g in group],
                    })
                    continue
            chosen[src] = group[0]
        if not chosen:
            continue
        probs = [g.get("devig_home") for g in chosen.values() if g.get("devig_home") is not None]
        spread = round(max(probs) - min(probs), 4) if len(probs) > 1 else None
        best = chosen.get("OddsPortal") or list(chosen.values())[0]
        attached[key] = {
            "primary": best,
            "all_sources": list(chosen.values()),
            "source_spread": spread,
        }
    return attached, flags


def probe_sources(fetcher: Fetcher) -> list[dict]:
    """Attempt the esports-book sources and report exactly what came back."""
    results = []
    for label, url in PROBES:
        body = fetcher.get(url, attempts=1)
        entry = {"label": label, "url": url, "http": None, "bytes": 0,
                 "odds_table_found": False, "verdict": ""}
        if body is None:
            entry["verdict"] = ("unreachable from this runner (bot protection, geo-block or DNS). "
                                "No line collected.")
        else:
            entry["bytes"] = len(body)
            entry["http"] = 200
            text = re.sub(r"(?s)<[^>]+>", " ", body)
            entry["odds_table_found"] = bool(len(ODDS_NUM.findall(text)) > 12)
            low = text.lower()
            if any(k in low for k in ("access denied", "are you a human", "captcha", "cf-browser-verification")):
                entry["verdict"] = "bot wall returned; no parseable odds table"
            elif not entry["odds_table_found"]:
                entry["verdict"] = "page reached but no machine-readable LoL odds table"
            else:
                entry["verdict"] = "page reached with odds-like numbers (not parsed by this pipeline)"
        results.append(entry)
        log(f"  probe {label}: {entry['verdict']}")
    return results
