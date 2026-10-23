#!/usr/bin/env python3
"""Build our own win probabilities and picks for every Hotspawn LoL pick'em match.

Method order (documented on the site):
  1. MARKET      - precision-weighted de-vigged consensus across real-money books &
                   exchanges (Pinnacle, Polymarket full-series CLOB, Kalshi CFTC,
                   Bovada, and verified specialist esportsbook quotes).
  2. MODEL       - our own Elo line fitted on Leaguepedia series results, used when
                   the two teams are connected by a shared-opponent chain and each
                   side has enough rated series.
  3. PROVISIONAL - Elo line emitted with an explicit low-confidence flag because the
                   data is thin (few rated series, one unrated side, or no shared
                   opponent chain).
  4. UNRESOLVED  - no defensible competitive probability (mid-split league removal /
                   disqualification in official Leaguepedia `dqteams`, unrated teams,
                   or unannounced TBD slots).

Hotspawn's community pick percentages are stored for transparency but are NEVER
used by the model or by any pick.
"""
from __future__ import annotations

import csv
import math
import os
import re
import sys
import urllib.parse
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DATA, RAW, ROOT, iso, load_json, log, norm_name, now_utc, save_json

ELO_START = 1500.0
# Update sizes were selected on a validation window that is disjoint from the
# published test window (see BACKTEST_SELECTION / BACKTEST_CUTOFF below). A
# best-of-one series carries much less information than a multi-game series, so
# it gets a larger step; multi-game series are additionally scaled by the
# margin of victory because a 2-0 is more informative than a 2-1.
ELO_K_OPENING = 48.0          # best-of-one and best-of-two series
ELO_K_SERIES = 40.0           # best-of-three, -five and -seven series
MOV_WEIGHT = 0.5              # multiplier = 1 + 0.5 * ln(1 + |game margin|)
ELO_K = ELO_K_OPENING         # kept for the published model description page
RECEIPT_MAX_AGE_HOURS = 24    # an archived bookmaker receipt is a line only while it is fresh
EXTREME_DECIMAL_MIN = 1.03    # implied >= ~97.1% on one side is not an actionable line
MARKET_MODEL_GAP = 0.20       # flag when our Elo line and the market disagree by >= 20 pp
THIN_VOLUME_USD = 1000.0      # a prediction market below this traded volume is labelled thin
# Shrinkage towards 1500 was measured to make the out-of-sample probabilities
# *worse* (Brier 0.2176 with shrink=5 versus 0.2150 without, n=3,854), so it is
# off. Thin samples are still labelled "provisional" instead of being shrunk.
ELO_SHRINK = 0.0
MIN_MATCHES_CONFIDENT = 5     # rated series per team required for "medium" confidence
PROB_FLOOR, PROB_CEIL = 0.05, 0.95
DECAY_START_DAYS = 45
DECAY_FULL_DAYS = 450
GENERIC_TOKENS = {"team", "teams", "esports", "esport", "gaming", "club", "gg", "lol", "e", "v"}

VENUE_WEIGHTS = {
    "Pinnacle": 0.36,
    "Polymarket": 0.24,
    "Kalshi": 0.18,
    "Bovada": 0.12,
    "Esportsbook": 0.10,
}

BOOK_TEAM_ALIASES = {
    "los": "los",
    "l o s": "los",
    "loud": "loud",
    "lyon gaming": "lyon",
    "six karma": "lyon",
    "anyones legend": "anyones legend",
    "bilibili": "bilibili gaming",
    "hanwha life": "hanwha life esports",
    "dplus": "dplus kia",
    "invictus": "invictus gaming",
    "secret whales": "team secret whales",
    "flying oyster": "ctbc flying oyster",
    "cfo": "ctbc flying oyster",
    "movistar koi": "movistar koi",
    "koi": "movistar koi",
}


# --------------------------------------------------------------------------- helpers
def base_name(name: str) -> str:
    """Leaguepedia disambiguates with 'Name (Region Team)' - strip that suffix."""
    text = "" if name is None else str(name)
    return re.sub(r"\s*\([^)]*\)\s*$", "", text).strip()


def region_of(name: str) -> str:
    m = re.search(r"\(([^)]*)\)\s*$", "" if name is None else str(name))
    return m.group(1) if m else ""


def canon_book_team(name: str) -> str:
    n = norm_name(base_name(name))
    return BOOK_TEAM_ALIASES.get(n, n)


def same_team(a: str, b: str) -> bool:
    """Loose equality used only for bookmaker-vs-Hotspawn name alignment."""
    na, nb = canon_book_team(a), canon_book_team(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    ta, tb = na.split(), nb.split()
    if ta == tb:
        return True
    short, long_ = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    short_text = " ".join(short)
    long_enough = len(short_text) >= 4 or (len(short_text) >= 2 and any(c.isdigit() for c in short_text))
    return (set(long_) - set(short)) <= GENERIC_TOKENS and long_enough


def leaguepedia_url(page: str | None) -> str:
    """Canonical Leaguepedia wiki URL for an overview page name."""
    if not page:
        return "https://lol.fandom.com/wiki/League_of_Legends"
    return "https://lol.fandom.com/wiki/" + urllib.parse.quote(str(page).replace(" ", "_"),
                                                               safe="()_',!.")


QUOTE_REJECTIONS: list[dict] = []
PROP_MARKETS_EXCLUDED: list[dict] = []
# A prop market is never a win probability. Pinnacle marks them in the participant name.
PROP_RE = re.compile(r"\((kills?|maps?|games?|handicap|total|props?)\)|"
                     r"\b(kills?|kill handicap|map handicap|total maps?|total kills?)\b",
                     re.I)


def devig_decimal(d0: float, d1: float, ctx: dict | None = None) -> tuple[float, float, float] | None:
    """Proportionally de-vig a two-way decimal quote, rejecting unusable prices.

    Rejected, and recorded in ``QUOTE_REJECTIONS`` so the build can publish them:
      * non-positive / <=1.00 decimal prices (no payout),
      * symmetric 1.80 / 1.80 aggregator default placeholders,
      * extreme quotes where either side implies more than 97% (decimal < 1.03).
        Those are win-market prices that no retail book offers as an actionable
        line; in this pipeline they have only ever come from scraped aggregator
        widgets or a mis-parsed page element, and publishing them produced a
        91.1% "market" pick that contradicted both the model and the live page.
    """
    note = None
    if d0 <= 1.0 or d1 <= 1.0:
        note = f"decimal price at or below 1.00 ({d0}/{d1})"
    elif abs(d0 - 1.80) < 1e-4 and abs(d1 - 1.80) < 1e-4:
        note = "symmetric 1.80/1.80 aggregator placeholder"
    elif min(d0, d1) < EXTREME_DECIMAL_MIN:
        note = (f"extreme quote {d0}/{d1}: one side implies "
                f"{100.0 / min(d0, d1):.1f}% before vig (threshold 97.0%)")
    if note:
        QUOTE_REJECTIONS.append({"reject": note, **(ctx or {})})
        return None
    inv = 1.0 / d0 + 1.0 / d1
    return (1.0 / d0) / inv, (1.0 / d1) / inv, inv - 1.0


# --------------------------------------------------------------------------- elo
class UnionFind:
    def __init__(self):
        self.parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


BACKTEST_CUTOFF = datetime(2026, 7, 1, tzinfo=timezone.utc)
# Hyper-parameters were chosen on this earlier, disjoint window; the published
# scores below are measured only on pairs that start after BACKTEST_CUTOFF.
BACKTEST_SELECTION = datetime(2025, 7, 1, tzinfo=timezone.utc)


def build_ratings(lp_matches: list[dict]) -> tuple[dict, dict, dict, UnionFind, dict]:
    ratings: dict[str, float] = {}
    counts: dict[str, int] = {}
    last_seen: dict[str, datetime] = {}
    uf = UnionFind()
    games: list[tuple[datetime, str, str, int, int, int | None, int | None]] = []

    for m in lp_matches:
        if m.get("winner") not in ("1", "2"):
            continue
        try:
            dt = datetime.strptime(str(m.get("utc"))[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
        try:
            best_of = int(m.get("best_of") or 1)
        except (TypeError, ValueError):
            best_of = 1
        s1, s2 = m.get("team1_score"), m.get("team2_score")
        games.append((dt, m["team1"], m["team2"], 1 if m["winner"] == "1" else 2, best_of,
                      int(s1) if isinstance(s1, (int, float)) else None,
                      int(s2) if isinstance(s2, (int, float)) else None))
        uf.union(m["team1"], m["team2"])

    games.sort(key=lambda g: g[0])
    bt = {"cutoff": BACKTEST_CUTOFF.strftime("%Y-%m-%d"), "n": 0, "hits": 0,
          "brier_sum": 0.0, "logloss_sum": 0.0, "buckets": {},
          "selection_window": f"{BACKTEST_SELECTION:%Y-%m-%d}..{BACKTEST_CUTOFF:%Y-%m-%d}",
          "selection": {"k_opening": ELO_K_OPENING, "k_series": ELO_K_SERIES,
                        "mov_weight": MOV_WEIGHT, "shrink": ELO_SHRINK},
          "validation": {"n": 0, "hits": 0, "brier_sum": 0.0, "logloss_sum": 0.0}}
    for dt, t1, t2, winner, best_of, s1, s2 in games:
        r1 = ratings.get(t1, ELO_START)
        r2 = ratings.get(t2, ELO_START)
        exp1 = 1 / (1 + 10 ** ((r2 - r1) / 400))
        y = 1.0 if winner == 1 else 0.0
        if dt >= BACKTEST_CUTOFF:
            fav_p = max(exp1, 1 - exp1)
            hit = (exp1 >= 0.5) == (winner == 1)
            bt["n"] += 1
            bt["hits"] += 1 if hit else 0
            bt["brier_sum"] += (exp1 - y) ** 2
            eps = 1e-9
            bt["logloss_sum"] += -(y * math.log(max(exp1, eps)) +
                                   (1 - y) * math.log(max(1 - exp1, eps)))
            bucket = ("50-60%" if fav_p < 0.60 else "60-70%" if fav_p < 0.70 else
                      "70-80%" if fav_p < 0.80 else "80%+")
            b = bt["buckets"].setdefault(bucket, {"n": 0, "hits": 0, "sum_p": 0.0})
            b["n"] += 1
            b["hits"] += 1 if hit else 0
            b["sum_p"] += fav_p
        elif dt >= BACKTEST_SELECTION:
            v = bt["validation"]
            v["n"] += 1
            v["hits"] += 1 if (exp1 >= 0.5) == (winner == 1) else 0
            v["brier_sum"] += (exp1 - y) ** 2
            eps = 1e-9
            v["logloss_sum"] += -(y * math.log(max(exp1, eps)) +
                                  (1 - y) * math.log(max(1 - exp1, eps)))

        if best_of >= 3 and s1 is not None and s2 is not None:
            k = ELO_K_SERIES * (1.0 + MOV_WEIGHT * math.log1p(abs(s1 - s2)))
        else:
            k = ELO_K_OPENING
        s1w = 1.0 if winner == 1 else 0.0
        ratings[t1] = r1 + k * (s1w - exp1)
        ratings[t2] = r2 + k * ((1 - s1w) - (1 - exp1))
        counts[t1] = counts.get(t1, 0) + 1
        counts[t2] = counts.get(t2, 0) + 1
        last_seen[t1] = dt
        last_seen[t2] = dt

    today = datetime.now(timezone.utc)
    for team in ratings:
        days = max(0.0, (today - last_seen[team]).total_seconds() / 86400)
        if days > DECAY_START_DAYS:
            factor = max(0.0, 1 - (days - DECAY_START_DAYS) / DECAY_FULL_DAYS)
            ratings[team] = ELO_START + (ratings[team] - ELO_START) * factor

    if bt["n"]:
        bt["accuracy"] = round(bt["hits"] / bt["n"], 4)
        bt["brier"] = round(bt["brier_sum"] / bt["n"], 4)
        bt["logloss"] = round(bt["logloss_sum"] / bt["n"], 4)
        ordered_buckets = {}
        for name in ("50-60%", "60-70%", "70-80%", "80%+"):
            if name in bt["buckets"]:
                b = bt["buckets"][name]
                b["accuracy"] = round(b["hits"] / b["n"], 4) if b["n"] else None
                b["mean_predicted"] = round(b["sum_p"] / b["n"], 4) if b["n"] else None
                b.pop("sum_p", None)
                ordered_buckets[name] = b
        bt["buckets"] = ordered_buckets
    v = bt["validation"]
    if v["n"]:
        v["accuracy"] = round(v["hits"] / v["n"], 4)
        v["brier"] = round(v["brier_sum"] / v["n"], 4)
        v["logloss"] = round(v["logloss_sum"] / v["n"], 4)
    v.pop("brier_sum", None)
    v.pop("logloss_sum", None)
    bt.pop("brier_sum", None)
    bt.pop("logloss_sum", None)
    return ratings, counts, last_seen, uf, bt


def effective_rating(team: str, ratings: dict, counts: dict) -> float | None:
    if team not in ratings:
        return None
    n = counts.get(team, 0)
    if not ELO_SHRINK:
        return ratings[team]
    return ELO_START + (ratings[team] - ELO_START) * (n / (n + ELO_SHRINK))


def win_probability(r_a: float, r_b: float) -> float:
    return 1 / (1 + 10 ** ((r_b - r_a) / 400))


def clamp(p: float) -> float:
    return max(PROB_FLOOR, min(PROB_CEIL, p))


# --------------------------------------------------------------------------- team index
def build_result_index(lp_matches: list[dict]) -> dict:
    """Completed series keyed by the unordered pair of team names."""
    idx: dict[frozenset, list] = {}
    for m in lp_matches:
        if m.get("winner") not in ("1", "2"):
            continue
        idx.setdefault(frozenset((str(m["team1"]), str(m["team2"]))), []).append(m)
    return idx


def recorded_result(idx: dict, k0: str | None, k1: str | None, start_utc: str | None,
                    page: str | None, within_hours: int = 36) -> dict | None:
    """Return the Leaguepedia result for this fixture when one is already recorded."""
    if not k0 or not k1 or not start_utc:
        return None
    try:
        start = datetime.strptime(start_utc[:19], "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None
    best = None
    for m in idx.get(frozenset((k0, k1)), []):
        try:
            when = datetime.strptime(str(m.get("utc"))[:19], "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            continue
        if abs((start - when).total_seconds()) <= within_hours * 3600:
            best = m
            break
    if not best:
        return None
    winner = str(best["team1"]) if best.get("winner") == "1" else str(best["team2"])
    loser = str(best["team2"]) if best.get("winner") == "1" else str(best["team1"])
    s1, s2 = best.get("team1_score"), best.get("team2_score")
    score = None
    if isinstance(s1, (int, float)) and isinstance(s2, (int, float)):
        score = f"{int(s1)}-{int(s2)}" if best.get("winner") == "1" else f"{int(s2)}-{int(s1)}"
    return {
        "winner": winner,
        "loser": loser,
        "score": score,
        "played_utc": str(best.get("utc")),
        "source": leaguepedia_url(best.get("overview_page") or page or ""),
        "note": ("The league record already shows a result for this card. It is kept for inventory "
                 "completeness and must not be treated as a live bet."),
    }


def _display_result(res: dict | None, k0: str | None, k1: str | None,
                    n0: str, n1: str) -> dict | None:
    """Swap Leaguepedia team keys for the names Hotspawn displays."""
    if not res:
        return None
    mapping = {k0: n0, k1: n1}
    return {**res, "winner": mapping.get(res["winner"], res["winner"]),
            "loser": mapping.get(res["loser"], res["loser"])}


def build_index(lp_matches: list[dict]) -> tuple[dict, dict, dict]:
    """exact index, base-name index, page -> teams."""
    exact: dict[str, str] = {}
    base: dict[str, set] = {}
    page_teams: dict[str, set] = {}
    for m in lp_matches:
        page = m.get("overview_page") or ""
        for t in (m["team1"], m["team2"]):
            exact.setdefault(norm_name(t), t)
            base.setdefault(norm_name(base_name(t)), set()).add(t)
            page_teams.setdefault(page, set()).add(t)
    return exact, base, page_teams


def map_competitions(fixtures: list[dict], page_teams: dict, base: dict) -> dict:
    """Map each Hotspawn competition to the Leaguepedia page that shares the most teams."""
    mapping = {}
    for comp in sorted({f["competition"] for f in fixtures}):
        comp_fixtures = [f for f in fixtures if f["competition"] == comp]
        wanted = set()
        for f in comp_fixtures:
            for side in ("team0", "team1"):
                wanted.add(norm_name(base_name(f[side]["name"])))
        best, best_score = None, 0
        for page, teams in page_teams.items():
            keys = {norm_name(base_name(t)) for t in teams}
            score = len(wanted & keys)
            if score > best_score:
                best, best_score = page, score
        mapping[comp] = {"page": best, "teams_in_common": best_score,
                         "fixtures": len(comp_fixtures)}
    return mapping


def resolve_team(name: str, exact: dict, base: dict, aliases: dict,
                 page: str | None, page_teams: dict) -> tuple[str | None, str, list]:
    """Resolve a Hotspawn team name to an exact Leaguepedia team name."""
    key = norm_name(name)
    if not key:
        return None, "none", []
    if key in exact:
        return exact[key], "exact", []
    if key in aliases:
        target = aliases[key]
        if norm_name(target) in exact:
            return exact[norm_name(target)], "alias", [f"explicit alias to '{target}' recorded in "
                                                       f"data/aliases.json with fixture-level evidence "
                                                       f"(see Flagged for review)"]
        if target in page_teams.get(page or "", set()):
            return target, "alias", [f"explicit alias to '{target}' recorded in data/aliases.json "
                                     f"with fixture-level evidence (see Flagged for review)"]

    candidates = sorted(base.get(norm_name(base_name(name)), set()))
    if len(candidates) == 1:
        return candidates[0], "base-name", [f"Leaguepedia lists this team as '{candidates[0]}'"]
    if len(candidates) > 1:
        page_set = page_teams.get(page or "", set())
        narrowed = [c for c in candidates if c in page_set]
        if len(narrowed) == 1:
            return narrowed[0], "competition-page", [
                f"ambiguous in Leaguepedia ({', '.join(candidates)}); resolved by the "
                f"'{page}' page listing"]
        return None, "ambiguous", [f"ambiguous in Leaguepedia: {', '.join(candidates)}"]
    return None, "none", []


# --------------------------------------------------------------------------- multi-venue market consensus
def market_lookup(fixture_id: str, name0: str, name1: str, start: str | None,
                  pin_index: list, pm_index: list, kalshi_index: list,
                  bovada_index: list, esportsbook_map: dict, within_hours: int = 36):
    """Combine all independent real-money venues covering this fixture."""
    def close_in_time(a: str | None, b: str | None) -> bool:
        if not a or not b:
            return True
        try:
            da = datetime.strptime(a[:19], "%Y-%m-%dT%H:%M:%S")
            db = datetime.strptime(b[:19], "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            return True
        return abs((da - db).total_seconds()) <= within_hours * 3600

    venues = []
    primary_decimal = None
    primary_american = None
    primary_start = None
    primary_league = None
    primary_api_url = ""

    # 1. Pinnacle
    for item in pin_index:
        a, b = item["names"]
        if close_in_time(start, item["start"]) and (
                (same_team(name0, a) and same_team(name1, b)) or
                (same_team(name0, b) and same_team(name1, a))):
            row = item["row"]
            home_dec = row["prices"]["home"]["decimal"]
            away_dec = row["prices"]["away"]["decimal"]
            dv = devig_decimal(home_dec, away_dec,
                               {"fixture_id": fixture_id, "venue": "Pinnacle"})
            if dv:
                p_home, p_away, overround = dv
                home_name = next((p["name"] for p in row["participants"]
                                  if p.get("alignment") == "home"), a)
                aligned = same_team(name0, home_name)
                p0_v = p_home if aligned else p_away
                p1_v = p_away if aligned else p_home
                d0_v = home_dec if aligned else away_dec
                d1_v = away_dec if aligned else home_dec
                primary_decimal = {"home": round(d0_v, 3), "away": round(d1_v, 3)}
                primary_american = {k: v.get("american") for k, v in row["prices"].items()}
                primary_start = item["start"]
                primary_league = row.get("league")
                primary_api_url = f"https://guest.api.arcadia.pinnacle.com/0.1/matchups/{row['matchup_id']}/markets/related/straight"
                venues.append({
                    "name": "Pinnacle",
                    "weight": VENUE_WEIGHTS["Pinnacle"],
                    "p0": round(p0_v, 4),
                    "p1": round(p1_v, 4),
                    "quote": f"{d0_v:.2f}/{d1_v:.2f}",
                    "overround": round(overround, 4),
                    "url": f"https://www.pinnacle.com/en/event/{row['matchup_id']}",
                })
                break

    # 2. Polymarket CLOB (highest-volume full-series market only)
    pm_start = None
    for item in pm_index:
        a, b = item["names"]
        if (same_team(name0, a) and same_team(name1, b)) or (same_team(name0, b) and same_team(name1, a)):
            pa = item["p0"] if same_team(name0, a) else item["p1"]
            pb = item["p1"] if same_team(name0, a) else item["p0"]
            pm_start = item.get("start") or pm_start
            tot = pa + pb
            if tot > 0:
                p0_v, p1_v = pa / tot, pb / tot
                venues.append({
                    "name": "Polymarket",
                    "weight": VENUE_WEIGHTS["Polymarket"],
                    "p0": round(p0_v, 4),
                    "p1": round(p1_v, 4),
                    "quote": f"{p0_v*100:.1f}¢/{p1_v*100:.1f}¢",
                    "overround": round(tot - 1.0, 4),
                    "volume_usd": round(float(item.get("volume") or 0.0), 2),
                    "url": f"https://polymarket.com/event/{item['slug']}",
                    "volume_usd": round(float(item.get("volume") or 0.0), 2),
                })
                if primary_start is None:
                    primary_start = item.get("start")
                if primary_api_url == "":
                    primary_api_url = f"https://gamma-api.polymarket.com/events?slug={item['slug']}"
                break

    # 3. Kalshi CFTC Regulated Exchange
    for item in kalshi_index:
        a, b = item["names"]
        if (same_team(name0, a) and same_team(name1, b)) or (same_team(name0, b) and same_team(name1, a)):
            pa = item["p0"] if same_team(name0, a) else item["p1"]
            pb = item["p1"] if same_team(name0, a) else item["p0"]
            tot = pa + pb
            if tot > 0:
                p0_v, p1_v = pa / tot, pb / tot
                venues.append({
                    "name": "Kalshi",
                    "weight": VENUE_WEIGHTS["Kalshi"],
                    "p0": round(p0_v, 4),
                    "p1": round(p1_v, 4),
                    "quote": f"{pa*100:.0f}¢/{pb*100:.0f}¢",
                    "overround": round(tot - 1.0, 4),
                    "url": f"https://kalshi.com/markets/kxlolgame/{item['event_ticker'].lower()}",
                })
                break

    # 4. Bovada Sportsbook
    for item in bovada_index:
        a, b = item["names"]
        if close_in_time(start, item["start"]) and (
                (same_team(name0, a) and same_team(name1, b)) or
                (same_team(name0, b) and same_team(name1, a))):
            d0_v = item["d0"] if same_team(name0, a) else item["d1"]
            d1_v = item["d1"] if same_team(name0, a) else item["d0"]
            dv = devig_decimal(d0_v, d1_v, {"fixture_id": fixture_id, "venue": "Bovada"})
            if dv:
                p0_v, p1_v, overround = dv
                if primary_decimal is None:
                    primary_decimal = {"home": round(d0_v, 3), "away": round(d1_v, 3)}
                venues.append({
                    "name": "Bovada",
                    "weight": VENUE_WEIGHTS["Bovada"],
                    "p0": round(p0_v, 4),
                    "p1": round(p1_v, 4),
                    "quote": f"{d0_v:.2f}/{d1_v:.2f}",
                    "overround": round(overround, 4),
                    "url": item["url"],
                })
                break

    # Archived aggregator receipts are not refreshed, so they must never enter a current line.

    if not venues:
        return None
    if primary_start is None:
        # Only the market's own stated kick-off (gameStartTime) is comparable; the event
        # startDate is the listing date and would produce false mismatches.
        primary_start = pm_start

    wsum = sum(v["weight"] for v in venues)
    p0 = sum(v["weight"] * v["p0"] for v in venues) / wsum
    p1 = round(1.0 - round(p0, 4), 4)
    p0 = round(p0, 4)
    # Never present derived fair odds as an observed bookmaker quote.

    book_label = (f"{len(venues)}-Venue Consensus" if len(venues) >= 2 else venues[0]["name"])
    # A single prediction market with almost no traded volume is a price, not a market.
    thin = len(venues) == 1 and venues[0]["name"] == "Polymarket" \
        and float(venues[0].get("volume_usd") or 0.0) < THIN_VOLUME_USD
    return {
        "thin": thin,
        "thin_note": (f"single Polymarket venue with ${float(venues[0].get('volume_usd') or 0):,.0f} "
                      f"traded volume (thin-market threshold ${THIN_VOLUME_USD:,.0f})") if thin else "",
        "book": book_label,
        "kind": "bookmaker" if any(v["name"] in ("Pinnacle", "Bovada", "Esportsbook") for v in venues) else "prediction market",
        "source_url": venues[0]["url"],
        "api_url": primary_api_url or venues[0]["url"],
        "market_url": venues[0]["url"],
        "decimal": primary_decimal,
        "american": primary_american,
        "p0": p0,
        "p1": p1,
        "overround": venues[0]["overround"],
        "start_utc": primary_start,
        "league": primary_league,
        "venue_count": len(venues),
        "volume_usd": (max(v["volume_usd"] for v in venues if v.get("volume_usd") is not None)
                       if any(v.get("volume_usd") is not None for v in venues) else None),
        "venues": venues,
    }


# --------------------------------------------------------------------------- main
def main() -> None:
    hs = load_json(os.path.join(RAW, "hotspawn_lol.json")) or {}
    lp = load_json(os.path.join(RAW, "leaguepedia.json")) or {}
    lp_dq = (load_json(os.path.join(RAW, "leaguepedia_dq.json")) or {}).get("dq_by_page") or {}
    pin = load_json(os.path.join(RAW, "pinnacle_lol.json")) or {}
    pmkt = load_json(os.path.join(RAW, "polymarket.json")) or {}
    kalshi = load_json(os.path.join(RAW, "kalshi_lol.json")) or {}
    bovada = load_json(os.path.join(RAW, "bovada_lol.json")) or {}
    receipts_doc = load_json(os.path.join(ROOT, "archive", "session-8336fb7e", "data", "book_receipts.json")) or {}
    receipts_all = receipts_doc.get("quotes") or receipts_doc.get("receipts") or {}
    # An archived receipt is a snapshot taken at `observed_at`. It is never a live
    # pricing input, but it is recorded in the audit trail so the exclusion is visible.
    expired_receipts = []
    for fid, rec in receipts_all.items():
        obs = rec.get("observed_at")
        age_h = None
        if obs:
            try:
                age_h = (now_utc() - datetime.strptime(str(obs)[:19], "%Y-%m-%dT%H:%M:%S")
                         .replace(tzinfo=timezone.utc)).total_seconds() / 3600
            except ValueError:
                age_h = None
        expired_receipts.append({"fixture_id": fid, "observed_at": obs,
                                 "age_hours": round(age_h, 1) if age_h is not None else None,
                                 "decimal": [rec.get("decimal0"), rec.get("decimal1")],
                                 "placeholder": rec.get("placeholder"),
                                 "source_url": rec.get("source_url")})
    receipts = {}
    sources = load_json(os.path.join(DATA, "sources_status.json")) or {}

    fixtures = hs.get("fixtures") or []
    lp_matches = lp.get("matches") or []
    if not fixtures:
        raise SystemExit("no hotspawn fixtures - run collect.py first")

    exact, base, page_teams = build_index(lp_matches)
    aliases_raw = (load_json(os.path.join(DATA, "aliases.json"), default={}) or {}).get("aliases") or {}
    aliases = {norm_name(k): v for k, v in aliases_raw.items()}
    comp_map = map_competitions(fixtures, page_teams, base)

    # Kick-off times per (competition page, team pair). A list, because the same pair
    # can meet twice in a split; a multi-entry key cannot be used for a time cross-check.
    lp_times: dict[tuple, list] = {}
    for m in lp_matches:
        key = (m.get("overview_page"), frozenset((str(m.get("team1")), str(m.get("team2")))))
        if m.get("utc"):
            lp_times.setdefault(key, []).append(m.get("utc"))
    ratings, counts, last_seen, uf, backtest = build_ratings(lp_matches)
    result_idx = build_result_index(lp_matches)

    lp_by_pair: dict[frozenset, list] = {}
    for m in lp_matches:
        lp_by_pair.setdefault(frozenset((norm_name(str(m.get("team1"))),
                                         norm_name(str(m.get("team2"))))), []).append(m)

    def leaguepedia_row(n0: str, n1: str, start: str | None):
        """The Leaguepedia record for this fixture: same team pair, closest kick-off."""
        cands = lp_by_pair.get(frozenset((norm_name(n0), norm_name(n1)))) or []
        if not cands:
            return None
        if not start:
            return cands[0]
        try:
            want = datetime.strptime(start, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            return cands[0]
        def gap(m):
            try:
                return abs((datetime.strptime(str(m.get("utc"))[:19], "%Y-%m-%d %H:%M:%S")
                            - want).total_seconds())
            except ValueError:
                return float("inf")
        return min(cands, key=gap)

    lp_by_pair: dict[frozenset, list] = {}
    for m in lp_matches:
        lp_by_pair.setdefault(frozenset((norm_name(str(m.get("team1"))),
                                         norm_name(str(m.get("team2"))))), []).append(m)

    def leaguepedia_row(n0: str, n1: str, start: str | None):
        """The Leaguepedia record for this fixture: same team pair, closest kick-off."""
        cands = lp_by_pair.get(frozenset((norm_name(n0), norm_name(n1)))) or []
        if not cands:
            return None
        if not start:
            return cands[0]
        try:
            want = datetime.strptime(start, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            return cands[0]

        def gap(m):
            try:
                return abs((datetime.strptime(str(m.get("utc"))[:19], "%Y-%m-%d %H:%M:%S")
                            - want).total_seconds())
            except ValueError:
                return float("inf")
        return min(cands, key=gap)

    pin_index = []
    for mk in pin.get("markets") or []:
        names = [p["name"] for p in mk.get("participants", [])]
        if len(names) != 2:
            continue
        # Pinnacle returns prop markets (kills, maps, handicaps, totals) with the same
        # `market_key` as the moneyline and only the participant name marking the prop
        # ("G2 (Kills)"). Matching on team names alone would publish a kill-handicap
        # price as a win probability, so any prop is dropped before matching and the
        # drop is counted in MARKET_FILTERS for the audit trail.
        if any(PROP_RE.search(n) for n in names):
            PROP_MARKETS_EXCLUDED.append({"participants": names,
                                          "market_key": mk.get("market_key"),
                                          "start_utc": mk.get("start_utc")})
            continue
        pin_index.append({"names": names, "row": mk, "start": mk.get("start_utc")})

    pm_candidates = []
    for mk in pmkt.get("match_markets") or []:
        outcomes = mk.get("outcomes") or []
        prices = mk.get("prices") or []
        if len(outcomes) != 2 or len(prices) != 2:
            continue
        try:
            pa, pb = float(prices[0]), float(prices[1])
            vol = float(mk.get("volume") or 0.0)
        except (TypeError, ValueError):
            continue
        if not (0.01 < pa < 0.99 and 0.01 < pb < 0.99):
            continue
        q = mk.get("question", "")
        if re.search(r"\b(game|map)\s*\d\b|\bhandicap\b|\btotal\b|\bkills?\b|\bprops?\b", q, re.I):
            continue
        pm_candidates.append({"names": outcomes, "p0": pa, "p1": pb, "volume": vol,
                              "slug": mk.get("slug"),
                              "start": mk.get("game_start")})
    pm_index = sorted(pm_candidates, key=lambda x: -x["volume"])

    kalshi_index = []
    for ev in kalshi.get("events") or []:
        mkts = ev.get("markets") or []
        if len(mkts) != 2:
            continue
        mids = []
        for m in mkts:
            try:
                bid = float(m.get("yes_bid_dollars") or 0)
                ask = float(m.get("yes_ask_dollars") or 0)
                last = float(m.get("last_price_dollars") or 0)
                mid = 0.5 * (bid + ask) if (bid > 0 and ask > 0) else last
            except (TypeError, ValueError):
                mid = 0.0
            mids.append((m.get("yes_sub_title") or "", mid))
        if mids[0][0] and mids[1][0] and mids[0][1] > 0 and mids[1][1] > 0:
            kalshi_index.append({
                "names": [mids[0][0], mids[1][0]],
                "p0": mids[0][1],
                "p1": mids[1][1],
                "event_ticker": ev.get("event_ticker") or "",
            })

    bovada_index = []
    for ev in bovada.get("events") or []:
        outs = ev.get("outcomes") or []
        if len(outs) == 2:
            bovada_index.append({
                "names": [outs[0]["name"], outs[1]["name"]],
                "d0": float(outs[0]["decimal"]),
                "d1": float(outs[1]["decimal"]),
                "start": ev.get("start_utc"),
                "url": ev.get("url") or "https://www.bovada.lv/sports/esports/league-of-legends",
            })

    rows, join_log = [], []
    for f in fixtures:
        n0, n1 = f["team0"]["name"], f["team1"]["name"]
        page = (comp_map.get(f["competition"]) or {}).get("page")
        k0, m0, note0 = resolve_team(n0, exact, base, aliases, page, page_teams)
        k1, m1, note1 = resolve_team(n1, exact, base, aliases, page, page_teams)
        for name, key, method, notes in ((n0, k0, m0, note0), (n1, k1, m1, note1)):
            if method not in ("exact",):
                join_log.append({"hotspawn_id": f["id"], "team": name, "resolved": key,
                                 "method": method, "notes": notes})

        er0 = effective_rating(k0, ratings, counts) if k0 else None
        er1 = effective_rating(k1, ratings, counts) if k1 else None
        n0c = counts.get(k0, 0) if k0 else 0
        n1c = counts.get(k1, 0) if k1 else 0
        connected = bool(k0 and k1 and uf.find(k0) == uf.find(k1))

        dq_norms = {norm_name(t): t for t in (lp_dq.get(page or "") or [])}
        dq0 = dq_norms.get(norm_name(k0 or n0))
        dq1 = dq_norms.get(norm_name(k1 or n1))

        market = market_lookup(f["id"], n0, n1, f.get("start_utc"),
                               pin_index, pm_index, kalshi_index, bovada_index, receipts)
        row = {
            "id": f["id"],
            "competition": f["competition"],
            "start_utc": f["start_utc"],
            "tier": f["tier"],
            "stage": f["stage"],
            "best_of": f["best_of"],
            "points": f["points"],
            "hotspawn_url": hotspawn_url(f),
            "pickem_url": f["pickem_url"],
            "leaguepedia_page": page,
            "team0": {"name": n0, "leaguepedia": k0, "join": m0, "join_notes": note0,
                      "rating_matches": n0c,
                      "last_played": last_seen.get(k0).strftime("%Y-%m-%d") if k0 in last_seen else None,
                      "elo_raw": round(ratings[k0], 1) if k0 in ratings else None,
                      "elo": round(er0, 1) if er0 is not None else None},
            "team1": {"name": n1, "leaguepedia": k1, "join": m1, "join_notes": note1,
                      "rating_matches": n1c,
                      "last_played": last_seen.get(k1).strftime("%Y-%m-%d") if k1 in last_seen else None,
                      "elo_raw": round(ratings[k1], 1) if k1 in ratings else None,
                      "elo": round(er1, 1) if er1 is not None else None},
        }

        flags: list[str] = []
        expected = None
        pick_type = "probability"
        active_side = None
        if dq0 or dq1:
            removed = dq0 or dq1
            active_opp = n1 if dq0 else n0
            active_side = 1 if dq0 else 0
            pick_type = "settlement"
            p0 = p1 = None
            method, confidence = "unresolved", "none"
            lp_row = leaguepedia_row(n0, n1, f.get("start_utc"))
            ff = (lp_row or {}).get("ff")
            if str(ff) in ("1", "2"):
                forfeit_note = (f"Leaguepedia records this series with its forfeit flag (FF={ff}, i.e. "
                                f"{removed} forfeited), 0-2 in favour of {active_opp}. ")
            elif lp_row:
                forfeit_note = (f"Leaguepedia records the series as a 0-2 loss for {removed}, but this "
                                f"snapshot captured no forfeit flag for it. ")
            else:
                forfeit_note = (f"Leaguepedia records no series between these teams on this date. ")
            basis = (f"Participant removed mid-split: community-maintained Leaguepedia Data:{page} records "
                     f"'dqteams={removed}'. " + forfeit_note +
                     f"Hotspawn may void this card or settle the walkover for opponent {active_opp}; the "
                     f"settlement is unverified, so no competitive probability is claimed.")
            flags.append(f"Leaguepedia-reported league removal: {removed} listed in Data:{page} dqteams "
                         f"(if not voided by Hotspawn, active opponent is {active_opp})")
            expected = {
                "team": active_opp,
                "kind": "administrative walkover",
                "note": ("Guidance only, not a betting pick: if Hotspawn settles this card instead of "
                         f"voiding it, the active opponent ({active_opp}) receives the forfeit win."),
                "source": leaguepedia_url(page),
            }
        elif market:
            p0, p1 = market["p0"], market["p1"]
            method, confidence = "market", "high"
            if market.get("thin"):
                confidence = "low"
                flags.append("thin market: " + market["thin_note"]
                             + " - published as the only external evidence, not as a high-confidence line")
            v_summary = ", ".join(f"{v['name']} {v['p0']*100:.1f}%/{v['p1']*100:.1f}% ({v['quote']})"
                                  for v in market.get("venues") or [])
            basis = f"{market['book']} de-vigged line ({p0*100:.1f}% / {p1*100:.1f}%): {v_summary}."
            # Independent cross-check: what does our own Elo line say about the same match?
            if er0 is not None and er1 is not None:
                elo_p = clamp(win_probability(er0, er1))
                market["model_cross_check"] = round(elo_p, 4)
                gap = abs(p0 - elo_p)
                if gap >= MARKET_MODEL_GAP:
                    flags.append(
                        f"market and model disagree by {gap*100:.0f} pp "
                        f"(market {max(p0, p1)*100:.1f}% vs our Elo {max(elo_p, 1-elo_p)*100:.1f}%) "
                        f"- the market side is published, the gap is disclosed")
            if market.get("start_utc") and f.get("start_utc"):
                try:
                    a = datetime.strptime(f["start_utc"], "%Y-%m-%dT%H:%M:%SZ")
                    b = datetime.strptime(str(market["start_utc"])[:19], "%Y-%m-%dT%H:%M:%S")
                    hours = abs((a - b).total_seconds()) / 3600
                    market["start_mismatch_hours"] = round(hours, 1)
                    if hours >= 1.0:
                        lp_list = lp_times.get((page, frozenset((str(k0), str(k1))))) if k0 and k1 else None
                        lp_utc = lp_list[0] if lp_list and len(lp_list) == 1 else None
                        corroborated = False
                        if lp_utc:
                            try:
                                c = datetime.strptime(str(lp_utc)[:19], "%Y-%m-%d %H:%M:%S")
                                corroborated = abs((a - c).total_seconds()) <= 3600
                            except ValueError:
                                corroborated = False
                        flags.append(
                            f"kick-off time differs between sources: Hotspawn"
                            f"{' and Leaguepedia say ' if corroborated else ' says '}{f['start_utc']} "
                            f"while {market.get('book', 'the bookmaker')} lists {str(market['start_utc'])[:16]}Z "
                            f"({hours:.1f}h apart) "
                            f"- confirm before betting")
                except ValueError:
                    pass
        elif er0 is not None and er1 is not None:
            p0 = clamp(win_probability(er0, er1))
            p1 = round(1 - p0, 4)
            thin = n0c < MIN_MATCHES_CONFIDENT or n1c < MIN_MATCHES_CONFIDENT or not connected
            method = "provisional" if thin else "model"
            confidence = "low" if thin else "medium"
            basis = (f"Elo line: {k0} {er0:.0f} vs {k1} {er1:.0f} "
                     f"({n0c}/{n1c} rated series).")
            if not connected:
                flags.append("no shared-opponent chain between the two teams")
            if n0c < MIN_MATCHES_CONFIDENT or n1c < MIN_MATCHES_CONFIDENT:
                flags.append("fewer than 5 rated series for at least one team")
        elif er0 is not None or er1 is not None:
            p0 = p1 = None
            method, confidence = "unresolved", "none"
            missing = n1 if er0 is not None else n0
            basis = (f"No collected external market and no rated series for {missing}. "
                     "A baseline rating would be an unsupported assumption; probability left blank.")
            flags.append(f"{missing} has no rated series in Leaguepedia")
        else:
            p0 = p1 = None
            method, confidence = "unresolved", "none"
            basis = "No bookmaker line and no rated series for either team."
            if "tbd" in norm_name(n0).split() or "tbd" in norm_name(n1).split():
                basis = "Participants not yet decided (TBD) on the Hotspawn card."
                flags.append("participants not announced")
            else:
                flags.append("no match history for either team in Leaguepedia")

        if market and p0 is not None:
            venues = market.get("venues") or []
            vol = market.get("volume_usd")
            if {v["name"] for v in venues} == {"Polymarket"} and vol is not None and vol < 1000:
                confidence = "low"
                market["thin"] = True
                flags.append(f"thin market: one Polymarket venue, ${vol:,.0f} total traded volume "
                             f"- indicative only, not a deep bookmaker line")

        for side, notes in ((row["team0"], note0), (row["team1"], note1)):
            flags.extend(notes)
        stale = False
        stale_hours = 0.0
        if f.get("start_utc"):
            try:
                start_dt = datetime.strptime(f["start_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                stale_hours = round(
                    (datetime.now(timezone.utc) - start_dt).total_seconds() / 3600, 1)
                stale = stale_hours > 0
            except ValueError:
                stale = False
        if stale:
            flags.append("start time has passed but Hotspawn still lists the fixture as scheduled "
                         "(reason unverified)")
        if row["team0"]["join"] == "ambiguous" or row["team1"]["join"] == "ambiguous":
            flags.append("team name could not be matched unambiguously")

        pick = None
        if p0 is not None:
            side = 0 if p0 >= p1 else 1
            pick = {"side": side,
                    "team": row["team0"]["name"] if side == 0 else row["team1"]["name"],
                    "probability": round(max(p0, p1), 4),
                    "other_probability": round(min(p0, p1), 4)}
        elif method == "unresolved" and pick_type == "settlement":
            pick = {"side": active_side,
                    "team": row["team0"]["name"] if active_side == 0 else row["team1"]["name"],
                    "probability": None, "other_probability": None,
                    "settlement": "administrative default (walkover / forfeit)"}
        row.update({"p0": round(p0, 4) if p0 is not None else None,
                    "p1": round(p1, 4) if p1 is not None else None,
                    "method": method, "confidence": confidence, "basis": basis,
                    "flags": sorted(set(flags)), "pick": pick, "pick_type": pick_type,
                    "market": market,
                    "expected_resolution": expected,
                    "recorded_result": _display_result(
                        recorded_result(result_idx, k0, k1, f.get("start_utc"), page), k0, k1, n0, n1),
                    "connected": connected, "stale": stale, "stale_hours": stale_hours,
                    "community_pick_pct": f["community_pick_pct"]})
        rows.append(row)

    counts_by_method: dict[str, int] = {}
    for r in rows:
        counts_by_method[r["method"]] = counts_by_method.get(r["method"], 0) + 1

    save_json(os.path.join(DATA, "matches.json"), {
        "generated_utc": iso(now_utc()),
        "inventory_fetched_utc": hs.get("fetched_utc"),
        "model": {"name": "LOLHOTSPAWN Elo", "k": ELO_K,
                  "k_opening": ELO_K_OPENING, "k_series": ELO_K_SERIES,
                  "mov_weight": MOV_WEIGHT,
                  "start": ELO_START,
                  "shrink": ELO_SHRINK, "min_matches_confident": MIN_MATCHES_CONFIDENT,
                  "prob_floor": PROB_FLOOR, "prob_ceil": PROB_CEIL,
                  "decay_start_days": DECAY_START_DAYS, "decay_full_days": DECAY_FULL_DAYS,
                  "window_start": lp.get("query", {}).get("where")},
        "sources": {"hotspawn": hs.get("source_url"), "pinnacle": pin.get("source_url"),
                    "kalshi": kalshi.get("source_url"), "bovada": bovada.get("source_url"),
                    "leaguepedia": lp.get("source_url"), "polymarket": pmkt.get("source_url"),
                    "source_status_utc": sources.get("checked_utc")},
        "counts": counts_by_method,
        "coverage": {
            "matches": len(rows),
            "with_pick": sum(1 for r in rows if r.get("pick")),
            "priced": sum(1 for r in rows if r.get("p0") is not None),
            "settlement_only": sum(1 for r in rows if r.get("pick_type") == "settlement"),
        },
        "market_filters": {
            "rule": "prop markets (kills/maps/handicap/total) are excluded before team matching",
            "excluded_pinnacle_props": PROP_MARKETS_EXCLUDED,
        },
        "receipt_audit": {
            "max_age_hours": RECEIPT_MAX_AGE_HOURS,
            "used": [],
            "expired": expired_receipts,
            "rejected_quotes": QUOTE_REJECTIONS,
        },
        "backtest": backtest,
        "total": len(rows),
        "matches": rows,
    })

    save_json(os.path.join(DATA, "matching_report.json"), {
        "generated_utc": iso(now_utc()),
        "competition_pages": comp_map,
        "non_exact_joins": join_log,
        "non_exact_team_count": len({(j["team"], j["resolved"]) for j in join_log}),
        "leaguepedia_teams": len(exact),
        "ratings": len(ratings),
    })

    with open(os.path.join(DATA, "picks.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["hotspawn_id", "start_utc", "competition", "tier", "team0", "p0", "team1", "p1",
                    "pick", "pick_probability", "method", "confidence", "basis", "flags",
                    "hotspawn_url", "market_source"])
        for r in rows:
            w.writerow([r["id"], r["start_utc"], r["competition"], r["tier"],
                        r["team0"]["name"], r["p0"], r["team1"]["name"], r["p1"],
                        r["pick"]["team"] if r["pick"] else "",
                        r["pick"]["probability"] if r["pick"] else "",
                        r["method"], r["confidence"], r["basis"], "; ".join(r["flags"]),
                        r["hotspawn_url"], (r["market"] or {}).get("api_url", "")])
    log(f"rows={len(rows)} methods={counts_by_method} joins={len(join_log)}")
    log(f"backtest n={backtest.get('n')} acc={backtest.get('accuracy')} brier={backtest.get('brier')}")


def slugify(value: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", value or "")
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-")


def hotspawn_url(f: dict) -> str:
    return (f"https://www.hotspawn.com/matches/{slugify(f['team0']['name'])}-vs-"
            f"{slugify(f['team1']['name'])}-{slugify(f['competition'])}-{f['id']}")


if __name__ == "__main__":
    main()
