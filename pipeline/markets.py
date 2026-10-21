"""External price sources for League of Legends matches.

Every adapter returns a list of two-way quotes (home/away) with a link the user
can open to verify. Hotspawn's own crowd percentages are never used here.

Sources implemented
  1. Bovada      - established US-facing sportsbook, public pre-match coupon feed.
  2. Pinnacle    - sharp bookmaker, public guest API (moneyline only).
  3. Polymarket  - regulated prediction market, Gamma API (price == probability).
  4. 1xBet       - European sportsbook with deep esports coverage (best effort;
                   the endpoint is geo-fenced for some runners).

Each adapter returns {"book": ..., "status": "ok|empty|error", "quotes": [...],
"error": ..., "url": ...} so the site can show, per match, which books were
actually queried.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from common import (UA, american_to_decimal, decimal_to_prob, http_get, iso,
                    now_utc)

TIMEOUT = 60


def _ms_to_iso(ms) -> str | None:
    try:
        return iso(datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc))
    except Exception:
        return None


def _quote(book, book_key, kind, url, home, away, dec_home, dec_away, extra=None):
    if not dec_home or not dec_away or dec_home <= 1.0 or dec_away <= 1.0:
        return None
    q = {
        "book": book,
        "book_key": book_key,
        "kind": kind,
        "url": url,
        "home": home,
        "away": away,
        "decimal_home": round(dec_home, 4),
        "decimal_away": round(dec_away, 4),
        "implied_home": round(decimal_to_prob(dec_home), 5),
        "implied_away": round(decimal_to_prob(dec_away), 5),
        "retrieved_at": iso(now_utc()),
    }
    if extra:
        q.update(extra)
    return q


# --------------------------------------------------------------------- Bovada
def bovada() -> dict:
    url = ("https://www.bovada.lv/services/sports/event/coupon/events/A/description/esports/"
           "league-of-legends?marketFilterId=def&preMatchOnly=true&lang=en")
    out = {"book": "Bovada", "book_key": "bovada", "kind": "sportsbook",
           "url": "https://www.bovada.lv/esports/league-of-legends", "status": "ok", "quotes": []}
    try:
        groups = json.loads(http_get(url, {"User-Agent": UA}))
    except Exception as e:
        out.update(status="error", error=f"{type(e).__name__}: {e}")
        return out

    for g in groups:
        for ev in g.get("events", []):
            comps = ev.get("competitors") or []
            if len(comps) != 2:
                continue
            home = next((c for c in comps if c.get("home")), comps[0])
            away = next((c for c in comps if not c.get("home")), comps[1])
            for dg in ev.get("displayGroups", []):
                for mk in dg.get("markets", []):
                    if mk.get("descriptionKey") != "Head To Head":
                        continue
                    per = mk.get("period") or {}
                    if not per.get("main"):
                        continue
                    outs = mk.get("outcomes") or []
                    if len(outs) != 2:
                        continue
                    dec = {}
                    for o in outs:
                        pr = (o.get("price") or {})
                        try:
                            dec[o.get("type")] = float(pr.get("decimal") or 0)
                        except (TypeError, ValueError):
                            dec[o.get("type")] = 0.0
                    q = _quote("Bovada", "bovada", "sportsbook",
                               "https://www.bovada.lv" + ev.get("link", ""),
                               home.get("name"), away.get("name"),
                               dec.get("H"), dec.get("A"),
                               {"start_utc": _ms_to_iso(ev.get("startTime")),
                                "market": "Moneyline (full series)"})
                    if q:
                        out["quotes"].append(q)
                    break
    if not out["quotes"]:
        out["status"] = "empty"
    return out


# -------------------------------------------------------------------- Pinnacle
PINNACLE_KEY = "CmX2KcMrXuFmNg6YFbmTxE0y9CIrOi0R"  # public guest key used by pinnacle.com
PINNACLE_BASE = "https://guest.api.arcadia.pinnacle.com/0.1"


def pinnacle() -> dict:
    out = {"book": "Pinnacle", "book_key": "pinnacle", "kind": "sportsbook",
           "url": "https://www.pinnacle.com/en/esports/league-of-legends/matchups",
           "status": "ok", "quotes": []}
    hdr = {"X-API-Key": PINNACLE_KEY, "User-Agent": UA}
    try:
        mus = json.loads(http_get(f"{PINNACLE_BASE}/sports/12/matchups?brandId=0", hdr))
    except Exception as e:
        out.update(status="error", error=f"{type(e).__name__}: {e}")
        return out

    lol = [m for m in mus
           if "league of legends" in ((m.get("league") or {}).get("name") or "").lower()
           and not m.get("special") and m.get("type") == "matchup"
           and len(m.get("participants") or []) == 2]
    for m in lol:
        try:
            mkts = json.loads(http_get(
                f"{PINNACLE_BASE}/matchups/{m['id']}/markets/related/straight", hdr))
        except Exception:
            continue
        if isinstance(mkts, dict):
            mkts = [x for v in mkts.values() for x in (v or [])]
        ml = [x for x in mkts if x.get("type") == "moneyline" and x.get("period") == 0]
        if not ml:
            continue
        prices = {p.get("designation"): p.get("price") for p in ml[0].get("prices", [])}
        parts = {p.get("alignment"): p.get("name") for p in m["participants"]}
        q = _quote("Pinnacle", "pinnacle", "sportsbook", out["url"],
                   parts.get("home"), parts.get("away"),
                   american_to_decimal(prices.get("home")),
                   american_to_decimal(prices.get("away")),
                   {"start_utc": m.get("startTime"),
                    "league": (m.get("league") or {}).get("name"),
                    "market": "Moneyline (full series)",
                    "external_id": str(m["id"])})
        if q:
            out["quotes"].append(q)
    if not out["quotes"]:
        out["status"] = "empty"
    return out


# ------------------------------------------------------------------ Polymarket
PM_BASE = "https://gamma-api.polymarket.com"
_PM_MATCH = re.compile(r"^LoL:\s*(.+?)\s+vs\.?\s+(.+?)(?:\s*\((?:BO\d)\))?\s*(?:-|$)", re.I)


def polymarket() -> dict:
    out = {"book": "Polymarket", "book_key": "polymarket", "kind": "prediction_market",
           "url": "https://polymarket.com/markets/league-of-legends", "status": "ok",
           "quotes": []}
    events = []
    try:
        for offset in (0, 100, 200):
            batch = json.loads(http_get(
                f"{PM_BASE}/events?limit=100&offset={offset}&closed=false&tag_slug=league-of-legends"))
            if not batch:
                break
            events.extend(batch)
    except Exception as e:
        out.update(status="error", error=f"{type(e).__name__}: {e}")
        return out

    for ev in events:
        for m in ev.get("markets") or []:
            if m.get("closed"):
                continue
            question = (m.get("question") or "").strip()
            mm = _PM_MATCH.match(question)
            if not mm:
                continue
            home, away = mm.group(1).strip(), mm.group(2).strip()
            try:
                outcomes = json.loads(m.get("outcomes") or "[]")
                prices = json.loads(m.get("outcomePrices") or "[]")
            except Exception:
                continue
            if len(outcomes) != 2 or len(prices) != 2:
                continue
            try:
                p_home, p_away = float(prices[0]), float(prices[1])
            except (TypeError, ValueError):
                continue
            if p_home <= 0 or p_away <= 0:
                continue
            out["quotes"].append({
                "book": "Polymarket",
                "book_key": "polymarket",
                "kind": "prediction_market",
                "url": f"https://polymarket.com/event/{ev.get('slug')}",
                "home": home,
                "away": away,
                "decimal_home": round(1 / p_home, 4),
                "decimal_away": round(1 / p_away, 4),
                "implied_home": p_home,
                "implied_away": p_away,
                "start_utc": ev.get("startDate") or ev.get("endDate"),
                "market": question,
                "volume_usd": m.get("volumeNum") or m.get("volume"),
                "liquidity_usd": m.get("liquidityNum") or m.get("liquidity"),
                "retrieved_at": iso(now_utc()),
            })
    if not out["quotes"]:
        out["status"] = "empty"
    return out


# ---------------------------------------------------------------------- 1xBet
ONEXBET = ("https://1xbet.com/LineFeed/Get1x2_VZip?sports=61&count=2000&lng=en&mode=4"
           "&country=1&partner=1&getEmpty=true")


def onexbet() -> dict:
    out = {"book": "1xBet", "book_key": "1xbet", "kind": "sportsbook",
           "url": "https://1xbet.com/en/line/esports", "status": "ok", "quotes": []}
    try:
        data = json.loads(http_get(ONEXBET, {"User-Agent": UA}))
    except Exception as e:
        out.update(status="error", error=f"{type(e).__name__}: {e}")
        return out
    values = data.get("Value") or []
    if not values:
        out["status"] = "empty"
        return out
    for ev in values:
        t1, t2 = ev.get("O1"), ev.get("O2")
        if not t1 or not t2:
            continue
        try:
            d1, d2 = float(ev.get("E") or 0), float(ev.get("T") or 0)
        except (TypeError, ValueError):
            continue
        q = _quote("1xBet", "1xbet", "sportsbook", out["url"], t1, t2,
                   d1 if d1 > 1 else None, d2 if d2 > 1 else None,
                   {"start_utc": _ms_to_iso(ev.get("S")),
                    "league": (ev.get("L") or ev.get("LE") or ""),
                    "market": "Moneyline (full series)",
                    "external_id": str(ev.get("I"))})
        if q:
            out["quotes"].append(q)
    if not out["quotes"]:
        out["status"] = "empty"
    return out


ADAPTERS = [bovada, pinnacle, polymarket, onexbet]


def collect_all() -> dict:
    results = []
    for fn in ADAPTERS:
        try:
            results.append(fn())
        except Exception as e:  # a broken adapter must not kill the run
            results.append({"book": fn.__name__, "book_key": fn.__name__, "kind": "unknown",
                            "url": "", "status": "error",
                            "error": f"{type(e).__name__}: {e}", "quotes": []})
    return {"retrieved_at": iso(now_utc()), "sources": results}
