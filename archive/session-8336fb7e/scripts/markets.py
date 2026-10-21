#!/usr/bin/env python3
"""Tier-1 external real-money sportsbooks, esportsbooks, and prediction markets engine.

Ingests and cross-validates five independent real-money external pricing sources:
  1. Pinnacle Guest API (`guest.api.arcadia.pinnacle.com`) — sharp full-match moneyline (`period=0`)
  2. Bovada Sportsbook API (`www.bovada.lv/services/sports/...`) — full-series moneyline + match deep links
  3. Polymarket Gamma CLOB (`gamma-api.polymarket.com`) — active two-way full-match LoL contracts
  4. Kalshi v2 CFTC Exchange (`api.elections.kalshi.com`) — regulated `KXLOLGAME` binary contracts
  5. Verified Specialist LoL Esportsbook Quotes (`data/book_receipts.json`) — strictly rejecting
     symmetric `1.80 / 1.80` aggregator unpriced placeholders.

Strict invariants enforced:
  - Hotspawn crowd pick percentages (`participants{0,1}_picked_percent`) are NEVER read or referenced.
  - Every two-way market line is normalized so `p0 + p1 == 1.0`.
  - Symmetric placeholder quotes (`d0 == d1 == 1.80` or `placeholder=True`) raise / are rejected.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MARKET_TEAM_TOKENS: dict[str, set[str]] = {
    "gen.g": {"geng", "gen", "gengesports"},
    "invictus gaming": {"invictusgaming", "invictus", "ig"},
    "hanwha life esports": {"hanwhalife", "hanwhalifeesports", "hle"},
    "top esports": {"topesports", "tes"},
    "bilibili gaming": {"bilibiligaming", "bilibili", "blg"},
    "movistar koi": {"movistarkoi", "mkoi", "koi"},
    "anyone's legend": {"anyoneslegend", "al"},
    "karmine corp": {"karminecorp", "kc"},
    "g2 esports": {"g2esports", "g2"},
    "dplus kia": {"dpluskia", "dk", "dplus"},
    "team liquid": {"teamliquid", "liquid", "tl"},
    "ctbc flying oyster": {"ctbcflyingoyster", "flyingoyster", "cfo"},
    "løs": {"los", "losgrandes"},
    "t1": {"t1"},
    "team secret whales": {"teamsecretwhales", "secretwhales", "tsw"},
    "lyon": {"lyon", "lyongaming"},
    "galions": {"galions"},
    "solary": {"solary"},
    "ground zero gaming": {"groundzerogaming", "groundzero", "gz"},
    "frank esports": {"frankesports", "fak"},
}


def _slug(s: str) -> str:
    s_clean = (
        (s or "")
        .lower()
        .replace("ø", "o")
        .replace("é", "e")
        .replace("á", "a")
        .replace("ã", "a")
        .replace("ü", "u")
        .replace("ö", "o")
    )
    return re.sub(r"[^a-z0-9]+", "", s_clean)


def team_tokens(name: str) -> set[str]:
    low = (name or "").strip().lower()
    base = _slug(name)
    out = {base} if base else set()
    if low in MARKET_TEAM_TOKENS:
        out |= MARKET_TEAM_TOKENS[low]
    for k, vals in MARKET_TEAM_TOKENS.items():
        if base in vals or _slug(k) == base:
            out |= vals
    return out


def same_team(name_a: str, name_b: str) -> bool:
    ta = team_tokens(name_a)
    tb = team_tokens(name_b)
    if not ta or not tb:
        return False
    return bool(ta & tb)


def american_to_decimal(am: float | int) -> float:
    a = float(am)
    if a == 0:
        raise ValueError("Invalid American odds 0")
    return 1.0 + (a / 100.0) if a > 0 else 1.0 + (100.0 / abs(a))


def devig_decimal_pair(d0: float, d1: float, reject_placeholder_180: bool = True) -> tuple[float, float, float]:
    """Proportional vig removal on two-way decimal odds -> `(p0, p1, overround)`."""
    if d0 <= 1.0 or d1 <= 1.0:
        raise ValueError(f"Decimal odds must exceed 1.0, got ({d0}, {d1})")
    if reject_placeholder_180 and abs(d0 - 1.80) < 1e-6 and abs(d1 - 1.80) < 1e-6:
        raise ValueError("Rejected symmetric 1.80 / 1.80 unpriced aggregator placeholder")
    imp0 = 1.0 / d0
    imp1 = 1.0 / d1
    overround = imp0 + imp1
    return imp0 / overround, imp1 / overround, overround


def parse_pinnacle_quotes(pinnacle_raw: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract full-match (`period=0`, `type=moneyline`) quotes from Pinnacle Guest API payload."""
    matchup_by_id: dict[int, dict[str, Any]] = {}
    for m in (pinnacle_raw.get("lol_matchups") or pinnacle_raw.get("matchups") or []):
        if m.get("type") != "matchup" or m.get("parentId") is not None:
            continue
        parts = m.get("participants") or []
        home = next((p for p in parts if p.get("alignment") == "home"), None)
        away = next((p for p in parts if p.get("alignment") == "away"), None)
        if home and away and home.get("name") and away.get("name"):
            matchup_by_id[int(m["id"])] = {
                "matchup_id": int(m["id"]),
                "league_name": (m.get("league") or {}).get("name") or "",
                "start_time": m.get("startTime") or "",
                "home_name": home["name"],
                "away_name": away["name"],
            }

    quotes: list[dict[str, Any]] = []
    seen: set[int] = set()
    markets_map = pinnacle_raw.get("lol_straight_markets") or pinnacle_raw.get("markets_by_league") or {}
    for _, lg_markets in markets_map.items():
        for mk in lg_markets:
            mid = mk.get("matchupId")
            if mid not in matchup_by_id or mid in seen:
                continue
            if mk.get("type") != "moneyline" or int(mk.get("period", -1)) != 0 or mk.get("isAlternate"):
                continue
            prices = mk.get("prices") or []
            ph = next((p.get("price") for p in prices if p.get("designation") == "home"), None)
            pa = next((p.get("price") for p in prices if p.get("designation") == "away"), None)
            if ph is None or pa is None:
                continue
            info = matchup_by_id[mid]
            dh = american_to_decimal(ph)
            da = american_to_decimal(pa)
            p_home, p_away, overround = devig_decimal_pair(dh, da, reject_placeholder_180=False)
            seen.add(mid)
            quotes.append({
                "venue": "Pinnacle",
                "venue_key": "pinnacle",
                "matchup_id": mid,
                "league": info["league_name"],
                "start_time": info["start_time"],
                "team_a": info["home_name"],
                "team_b": info["away_name"],
                "american_a": int(ph),
                "american_b": int(pa),
                "decimal_a": round(dh, 4),
                "decimal_b": round(da, 4),
                "prob_a": p_home,
                "prob_b": p_away,
                "overround": round(overround, 4),
                "source_url": "https://www.pinnacle.com/en/esports/league-of-legends/matchups",
            })
    return quotes


def parse_bovada_quotes(quotes_raw: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract live Bovada full-series moneyline quotes from `data/quotes.json`."""
    quotes: list[dict[str, Any]] = []
    for src in (quotes_raw.get("sources") or []):
        if (src.get("book_key") or "").lower() != "bovada" and (src.get("book") or "").lower() != "bovada":
            continue
        for q in (src.get("quotes") or []):
            dh = float(q.get("decimal_home") or 0.0)
            da = float(q.get("decimal_away") or 0.0)
            if dh <= 1.0 or da <= 1.0:
                continue
            p_home, p_away, overround = devig_decimal_pair(dh, da, reject_placeholder_180=True)
            quotes.append({
                "venue": "Bovada",
                "venue_key": "bovada",
                "start_time": q.get("start_utc") or "",
                "team_a": str(q.get("home") or "").strip(),
                "team_b": str(q.get("away") or "").strip(),
                "decimal_a": round(dh, 4),
                "decimal_b": round(da, 4),
                "prob_a": p_home,
                "prob_b": p_away,
                "overround": round(overround, 4),
                "source_url": q.get("url") or "https://www.bovada.lv/esports/league-of-legends",
            })
    return quotes


def parse_polymarket_quotes(poly_raw: list[dict[str, Any]] | dict[str, Any]) -> list[dict[str, Any]]:
    """Extract live two-way full-match moneyline markets from Polymarket Gamma CLOB."""
    quotes: list[dict[str, Any]] = []
    seen_slugs: set[str] = set()
    events_iter = poly_raw if isinstance(poly_raw, list) else (poly_raw.get("events") or [])
    for ev in events_iter:
        slug = ev.get("slug") or ""
        if not slug.startswith("lol-") or slug in seen_slugs or ev.get("closed"):
            continue
        markets = ev.get("markets") or []
        chosen = None
        for m in markets:
            if m.get("closed"):
                continue
            smt = (m.get("sportsMarketType") or "").lower()
            q = (m.get("question") or "").lower()
            if smt == "moneyline" or ("vs." in q and "game " not in q and "handicap" not in q and "total" not in q):
                chosen = m
                break
        if not chosen:
            continue
        outcomes = json.loads(chosen["outcomes"]) if isinstance(chosen.get("outcomes"), str) else (chosen.get("outcomes") or [])
        prices = json.loads(chosen["outcomePrices"]) if isinstance(chosen.get("outcomePrices"), str) else (chosen.get("outcomePrices") or [])
        if len(outcomes) != 2 or len(prices) != 2:
            continue
        raw_a, raw_b = float(prices[0]), float(prices[1])
        tot = raw_a + raw_b
        if tot <= 0.05:
            continue
        seen_slugs.add(slug)
        quotes.append({
            "venue": "Polymarket",
            "venue_key": "polymarket",
            "slug": slug,
            "start_time": chosen.get("gameStartTime") or ev.get("startDate") or "",
            "team_a": str(outcomes[0]).strip(),
            "team_b": str(outcomes[1]).strip(),
            "raw_price_a": round(raw_a, 4),
            "raw_price_b": round(raw_b, 4),
            "prob_a": raw_a / tot,
            "prob_b": raw_b / tot,
            "volume_usd": round(float(ev.get("volume") or chosen.get("volume") or 0.0), 2),
            "source_url": f"https://polymarket.com/event/{slug}",
        })
    return quotes


def parse_kalshi_quotes(kalshi_raw: list[dict[str, Any]] | dict[str, Any]) -> list[dict[str, Any]]:
    """Extract live CFTC-regulated two-way match quotes from Kalshi v2 `KXLOLGAME` events."""
    quotes: list[dict[str, Any]] = []
    events_iter = kalshi_raw if isinstance(kalshi_raw, list) else (kalshi_raw.get("events") or [])
    for ev in events_iter:
        ticker = ev.get("event_ticker") or ""
        if not ticker.startswith("KXLOLGAME-"):
            continue
        mkts = ev.get("markets") or []
        if len(mkts) != 2:
            continue
        parsed_sides = []
        vol_total = 0.0
        for m in mkts:
            name = (m.get("yes_sub_title") or "").strip()
            bid = float(m.get("yes_bid_dollars") or 0.0)
            ask = float(m.get("yes_ask_dollars") or 0.0)
            last = float(m.get("last_price_dollars") or 0.0)
            mid = 0.5 * (bid + ask) if (bid > 0 and ask > 0) else last
            vol_total += float(m.get("volume_fp") or 0.0)
            parsed_sides.append((name, mid, bid, ask))
        if any(not s[0] or s[1] <= 0.01 for s in parsed_sides):
            continue
        tot = parsed_sides[0][1] + parsed_sides[1][1]
        quotes.append({
            "venue": "Kalshi",
            "venue_key": "kalshi",
            "event_ticker": ticker,
            "team_a": parsed_sides[0][0],
            "team_b": parsed_sides[1][0],
            "mid_a": round(parsed_sides[0][1], 4),
            "mid_b": round(parsed_sides[1][1], 4),
            "spread_cents": round((parsed_sides[0][3] - parsed_sides[0][2]) * 100.0, 1),
            "prob_a": parsed_sides[0][1] / tot,
            "prob_b": parsed_sides[1][1] / tot,
            "volume_contracts": round(vol_total, 2),
            "source_url": f"https://kalshi.com/markets/kxlolgame/{ticker.lower()}",
        })
    return quotes


def parse_book_receipts(receipts_raw: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Validate specialist esportsbook quotes by `fixture_id`, filtering out any placeholders."""
    valid: dict[str, dict[str, Any]] = {}
    for fid, q in (receipts_raw.get("quotes") or {}).items():
        if q.get("placeholder"):
            continue
        d0 = float(q["decimal0"])
        d1 = float(q["decimal1"])
        p0, p1, overround = devig_decimal_pair(d0, d1, reject_placeholder_180=True)
        valid[str(fid)] = {
            "venue": "Esportsbook",
            "venue_key": "esportsbook",
            "fixture_id": str(fid),
            "team_a": q["team0"],
            "team_b": q["team1"],
            "decimal_a": d0,
            "decimal_b": d1,
            "prob_a": p0,
            "prob_b": p1,
            "overround": round(overround, 4),
            "book_label": q.get("book_label") or "Specialist Esportsbook",
            "source_url": q["source_url"],
            "observed_at": q["observed_at"],
            "note": q.get("note") or "",
        }
    return valid


def _align_quote_to_fixture(
    quote: dict[str, Any], team0: str, team1: str, sched_ms: int
) -> dict[str, Any] | None:
    qa, qb = quote["team_a"], quote["team_b"]
    direct = same_team(qa, team0) and same_team(qb, team1)
    flipped = same_team(qa, team1) and same_team(qb, team0)
    if not direct and not flipped:
        return None

    st = quote.get("start_time") or ""
    if st:
        try:
            q_dt = datetime.fromisoformat(st.replace("Z", "+00:00").replace(" ", "T"))
            f_dt = datetime.fromtimestamp(sched_ms / 1000.0, tz=timezone.utc)
            if abs((q_dt - f_dt).total_seconds()) > 7 * 86400:
                return None
        except ValueError:
            pass

    aligned = dict(quote)
    if direct:
        aligned["p0"] = float(quote["prob_a"])
        aligned["p1"] = float(quote["prob_b"])
        if "decimal_a" in quote:
            aligned["dec0"] = quote["decimal_a"]
            aligned["dec1"] = quote["decimal_b"]
        if "american_a" in quote:
            aligned["am0"] = quote["american_a"]
            aligned["am1"] = quote["american_b"]
    else:
        aligned["p0"] = float(quote["prob_b"])
        aligned["p1"] = float(quote["prob_a"])
        if "decimal_a" in quote:
            aligned["dec0"] = quote["decimal_b"]
            aligned["dec1"] = quote["decimal_a"]
        if "american_a" in quote:
            aligned["am0"] = quote["american_b"]
            aligned["am1"] = quote["american_a"]
    return aligned


# Institutional sharp-venue weights when combining simultaneous real-money markets
VENUE_WEIGHTS: dict[str, float] = {
    "pinnacle": 0.36,
    "polymarket": 0.24,
    "kalshi": 0.18,
    "bovada": 0.12,
    "esportsbook": 0.10,
}


def resolve_market_tier1(
    fixture: dict[str, Any],
    pinnacle_quotes: list[dict[str, Any]],
    polymarket_quotes: list[dict[str, Any]],
    kalshi_quotes: list[dict[str, Any]],
    book_receipts: dict[str, dict[str, Any]],
    bovada_quotes: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Resolve Tier-1 external market line for `fixture` if covered by >=1 real-money book/exchange."""
    fid = str(fixture["id"])
    t0 = fixture["participants0_name"]
    t1 = fixture["participants1_name"]
    sched_ms = int(fixture["scheduled_start_time"])

    matched: list[dict[str, Any]] = []
    for pool in (pinnacle_quotes, bovada_quotes or [], polymarket_quotes, kalshi_quotes):
        for q in pool:
            aligned = _align_quote_to_fixture(q, t0, t1, sched_ms)
            if aligned is not None:
                matched.append(aligned)
                break

    if fid in book_receipts:
        aligned_bk = _align_quote_to_fixture(book_receipts[fid], t0, t1, sched_ms)
        if aligned_bk is not None:
            matched.append(aligned_bk)

    if not matched:
        return None

    w_sum = sum(VENUE_WEIGHTS[m["venue_key"]] for m in matched)
    p0 = sum(VENUE_WEIGHTS[m["venue_key"]] * m["p0"] for m in matched) / w_sum
    p1 = 1.0 - p0

    p0_list = [m["p0"] for m in matched]
    p_low = min(p0_list)
    p_high = max(p0_list)

    tier_kind = "market_consensus" if len(matched) >= 2 else "esportsbook_line"
    return {
        "pricing_tier": tier_kind,
        "venue_count": len(matched),
        "p0": p0,
        "p1": p1,
        "ci90_p0": [round(min(p_low, p0), 4), round(max(p_high, p0), 4)],
        "venues": matched,
    }


def load_all_market_sources(
    sources_dir: Path, data_dir: Path
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, Any]], list[dict[str, Any]]]:
    pin_path = sources_dir / "pinnacle_lol.json"
    poly_path = sources_dir / "polymarket_lol.json"
    kal_path = sources_dir / "kalshi_lol.json"
    bk_path = data_dir / "book_receipts.json"
    if not bk_path.exists():
        bk_path = Path("data/book_receipts.json")
    q_path = data_dir / "quotes.json"
    if not q_path.exists():
        q_path = Path("data/quotes.json")

    pin = parse_pinnacle_quotes(json.loads(pin_path.read_text(encoding="utf-8"))) if pin_path.exists() else []
    poly = parse_polymarket_quotes(json.loads(poly_path.read_text(encoding="utf-8"))) if poly_path.exists() else []
    kal = parse_kalshi_quotes(json.loads(kal_path.read_text(encoding="utf-8"))) if kal_path.exists() else []
    bks = parse_book_receipts(json.loads(bk_path.read_text(encoding="utf-8"))) if bk_path.exists() else {}
    bov = parse_bovada_quotes(json.loads(q_path.read_text(encoding="utf-8"))) if q_path.exists() else []
    return pin, poly, kal, bks, bov
