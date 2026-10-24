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
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DATA, RAW, ROOT, iso, load_json, log, norm_name, now_utc, save_json

ELO_START = 1500.0
ELO_K = 26.0
ELO_MOV_SLOPE = 0.18          # margin-of-victory multiplier: 1 + 0.18 * max(0, score_diff - 1)
ELO_SHRINK = 5.0              # r_eff = prior + (r - prior) * n / (n + 5)
MIN_MATCHES_CONFIDENT = 5     # rated series per team required for "medium" confidence
PROB_FLOOR, PROB_CEIL = 0.05, 0.95
DECAY_START_DAYS = 45
DECAY_FULL_DAYS = 450
RECEIPT_MAX_AGE_HOURS = 24    # an archived bookmaker receipt is a line only while it is fresh
EXTREME_DECIMAL_MIN = 1.03    # implied >= ~97.1% on one side is not an actionable line
MARKET_MODEL_GAP = 0.20       # flag when our Elo line and the market disagree by >= 20 pp
THIN_VOLUME_USD = 1000.0      # a prediction market below this traded volume is labelled thin
GENERIC_TOKENS = {"team", "teams", "esports", "esport", "gaming", "club", "gg", "lol", "e", "v"}

VENUE_WEIGHTS = {
    "Pinnacle": 0.36,
    "Polymarket": 0.24,
    "Kalshi": 0.18,
    "Bovada": 0.12,
    "Unibet": 0.10,
}

BOOK_TEAM_ALIASES = {
    "los": "los",
    "l o s": "los",
    "l s": "los",
    "loud": "loud",
    "lyon gaming": "lyon",
    "six karma": "lyon",
    "anyones legend": "anyones legend",
    "bilibili": "bilibili gaming",
    "hanwha life": "hanwha life esports",
    "dplus": "dplus kia",
    "invictus": "invictus gaming",
    "secret whales": "team secret whales",
    "team secret": "team secret whales",
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


QUOTE_REJECTIONS: list[dict] = []


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


def tier_prior(overview_page: str) -> float:
    """Division-calibrated starting rating when a team first enters the chronology."""
    p = (overview_page or "").lower()
    if any(k in p for k in ("world championship", "worlds", "mid-season invitational",
                            "first stand", "esports world cup")):
        return 1700.0
    if re.search(r"^(lck|lpl|lec|lcs|lta|lcp|cblol)(\s|/|$)", p) and not any(
            sub in p for sub in ("cl", "challengers", "academy", "promotion", "stars")):
        return 1700.0
    if any(k in p for k in ("emea masters", "lck cl", "challengers league", "ldl",
                            "pcs/", "vcs/", "ljl/", "lfl/", "lvp superliga",
                            "prime league 1st division", "prm 1st division",
                            "north american challengers", "nacl", "tcl/", "nlc/",
                            "lit/", "ultraliga", "promotion")):
        return 1575.0
    if any(k in p for k in ("3rd division", "division 3", "div 3", "open qualifier",
                            "lgc rising", "tunisian", "arabian")):
        return 1455.0
    return ELO_START


def parse_lp_time(raw) -> datetime | None:
    try:
        return datetime.strptime(str(raw)[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def parse_chronology(lp_matches: list[dict]) -> list[tuple[datetime, str, str, int, int, str]]:
    games: list[tuple[datetime, str, str, int, int, str]] = []
    for m in lp_matches:
        if m.get("winner") not in ("1", "2"):
            continue
        dt = parse_lp_time(m.get("utc"))
        if dt is None:
            continue
        try:
            s1 = int(m.get("team1_score"))
            s2 = int(m.get("team2_score"))
            diff = max(1, abs(s1 - s2))
        except (TypeError, ValueError):
            diff = 1
        games.append((dt, m["team1"], m["team2"], 1 if m["winner"] == "1" else 2,
                      diff, m.get("overview_page") or ""))
    games.sort(key=lambda g: g[0])
    return games


def snapshot_ratings(games: list[tuple[datetime, str, str, int, int, str]],
                     cutoff: datetime) -> tuple[dict, dict, dict, dict, UnionFind]:
    """Compute strictly pre-cutoff ratings, counts, last_seen, priors and graph."""
    ratings: dict[str, float] = {}
    priors: dict[str, float] = {}
    counts: dict[str, int] = {}
    last_seen: dict[str, datetime] = {}
    uf = UnionFind()
    for dt, t1, t2, winner, diff, page in games:
        if dt >= cutoff:
            break
        p1_prior = priors.setdefault(t1, tier_prior(page))
        p2_prior = priors.setdefault(t2, tier_prior(page))
        r1 = ratings.get(t1, p1_prior)
        r2 = ratings.get(t2, p2_prior)
        exp1 = 1 / (1 + 10 ** ((r2 - r1) / 400))
        s1 = 1.0 if winner == 1 else 0.0
        k_eff = ELO_K * (1.0 + ELO_MOV_SLOPE * max(0, diff - 1))
        ratings[t1] = r1 + k_eff * (s1 - exp1)
        ratings[t2] = r2 + k_eff * ((1 - s1) - (1 - exp1))
        counts[t1] = counts.get(t1, 0) + 1
        counts[t2] = counts.get(t2, 0) + 1
        last_seen[t1] = dt
        last_seen[t2] = dt
        uf.union(t1, t2)
    for team in list(ratings.keys()):
        base_r = priors.get(team, ELO_START)
        days = max(0.0, (cutoff - last_seen[team]).total_seconds() / 86400)
        if days > DECAY_START_DAYS:
            factor = max(0.0, 1 - (days - DECAY_START_DAYS) / DECAY_FULL_DAYS)
            ratings[team] = base_r + (ratings[team] - base_r) * factor
    return ratings, priors, counts, last_seen, uf


def build_ratings(lp_matches: list[dict]) -> tuple[dict, dict, dict, dict, UnionFind, dict, list]:
    games = parse_chronology(lp_matches)
    ratings: dict[str, float] = {}
    priors: dict[str, float] = {}
    counts: dict[str, int] = {}
    last_seen: dict[str, datetime] = {}
    uf = UnionFind()

    bt = {"cutoff": BACKTEST_CUTOFF.strftime("%Y-%m-%d"), "n": 0, "hits": 0,
          "brier_sum": 0.0, "logloss_sum": 0.0, "buckets": {}}
    for dt, t1, t2, winner, diff, page in games:
        p1_prior = priors.setdefault(t1, tier_prior(page))
        p2_prior = priors.setdefault(t2, tier_prior(page))
        r1 = ratings.get(t1, p1_prior)
        r2 = ratings.get(t2, p2_prior)
        exp1 = 1 / (1 + 10 ** ((r2 - r1) / 400))
        if dt >= BACKTEST_CUTOFF:
            y = 1.0 if winner == 1 else 0.0
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
        s1 = 1.0 if winner == 1 else 0.0
        k_eff = ELO_K * (1.0 + ELO_MOV_SLOPE * max(0, diff - 1))
        ratings[t1] = r1 + k_eff * (s1 - exp1)
        ratings[t2] = r2 + k_eff * ((1 - s1) - (1 - exp1))
        counts[t1] = counts.get(t1, 0) + 1
        counts[t2] = counts.get(t2, 0) + 1
        last_seen[t1] = dt
        last_seen[t2] = dt
        uf.union(t1, t2)

    today = datetime.now(timezone.utc)
    for team in ratings:
        base_r = priors.get(team, ELO_START)
        days = max(0.0, (today - last_seen[team]).total_seconds() / 86400)
        if days > DECAY_START_DAYS:
            factor = max(0.0, 1 - (days - DECAY_START_DAYS) / DECAY_FULL_DAYS)
            ratings[team] = base_r + (ratings[team] - base_r) * factor

    if bt["n"]:
        bt["accuracy"] = round(bt["hits"] / bt["n"], 4)
        bt["brier"] = round(bt["brier_sum"] / bt["n"], 4)
        bt["logloss"] = round(bt["logloss_sum"] / bt["n"], 4)
        ordered = {}
        for name in ("50-60%", "60-70%", "70-80%", "80%+"):
            if name in bt["buckets"]:
                b = bt["buckets"][name]
                b["accuracy"] = round(b["hits"] / b["n"], 4) if b["n"] else None
                b["mean_predicted"] = round(b["sum_p"] / b["n"], 4) if b["n"] else None
                b.pop("sum_p", None)
                ordered[name] = b
        bt["buckets"] = ordered
    bt.pop("brier_sum", None)
    bt.pop("logloss_sum", None)
    return ratings, priors, counts, last_seen, uf, bt, games


def effective_rating(team: str | None, ratings: dict, counts: dict,
                     priors: dict | None = None, page: str | None = None) -> float | None:
    if not team:
        return None
    n = counts.get(team, 0)
    base_r = (priors or {}).get(team) or tier_prior(page or "")
    r = ratings.get(team, base_r)
    return base_r + (r - base_r) * (n / (n + ELO_SHRINK))


def win_probability(r_a: float, r_b: float) -> float:
    return 1 / (1 + 10 ** ((r_b - r_a) / 400))


def clamp(p: float) -> float:
    return max(PROB_FLOOR, min(PROB_CEIL, p))


# --------------------------------------------------------------------------- team index
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
    """Resolve a Hotspawn team name to an exact Leaguepedia team name.

    Competition-scoped matching runs BEFORE global exact lookup so a homonymous
    regional team (e.g. 'Last Dance (Benelux Team)' vs Portuguese 'Last Dance', or
    'Team Gromp (Australian Team)' vs European 'Team Gromp') never silently binds to
    the wrong continent's team record.
    """
    key = norm_name(name)
    if not key:
        return None, "none", []
    if key in aliases:
        target = aliases[key]
        if norm_name(target) in exact:
            return exact[norm_name(target)], "alias", [f"explicit alias to '{target}' recorded in "
                                                       f"data/aliases.json with fixture-level evidence "
                                                       f"(see Flagged for review)"]
        if target in page_teams.get(page or "", set()):
            return target, "alias", [f"explicit alias to '{target}' recorded in data/aliases.json "
                                     f"with fixture-level evidence (see Flagged for review)"]

    page_set = page_teams.get(page or "", set())
    if page_set:
        bkey = norm_name(base_name(name))
        in_page = sorted(c for c in page_set if norm_name(base_name(c)) == bkey)
        if len(in_page) == 1:
            chosen = in_page[0]
            if norm_name(chosen) == key:
                return chosen, "exact", []
            other = exact.get(key)
            extra = f" rather than homonymous '{other}'" if other and other != chosen else ""
            return chosen, "competition-page", [
                f"resolved within '{page}' to '{chosen}'{extra}"]

    if key in exact:
        return exact[key], "exact", []

    candidates = sorted(base.get(norm_name(base_name(name)), set()))
    if len(candidates) == 1:
        return candidates[0], "base-name", [f"Leaguepedia lists this team as '{candidates[0]}'"]
    if len(candidates) > 1:
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
                  bovada_index: list, kambi_index: list, within_hours: int = 36):
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
                pin_receipt_url = f"https://guest.api.arcadia.pinnacle.com/0.1/matchups/{row['matchup_id']}/markets/related/straight"
                primary_api_url = pin_receipt_url
                venues.append({
                    "name": "Pinnacle",
                    "weight": VENUE_WEIGHTS["Pinnacle"],
                    "p0": round(p0_v, 4),
                    "p1": round(p1_v, 4),
                    "quote": f"{d0_v:.2f}/{d1_v:.2f}",
                    "overround": round(overround, 4),
                    "observed_utc": item.get("observed_utc"),
                    "url": pin_receipt_url,
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
                    "observed_utc": item.get("observed_utc"),
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
                    "observed_utc": item.get("observed_utc"),
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
                bov_url = item["url"]
                if bov_url.startswith("https://www.bovada.lv/esports/"):
                    bov_url = bov_url.replace("https://www.bovada.lv/esports/",
                                              "https://www.bovada.lv/sports/esports/", 1)
                venues.append({
                    "name": "Bovada",
                    "weight": VENUE_WEIGHTS["Bovada"],
                    "p0": round(p0_v, 4),
                    "p1": round(p1_v, 4),
                    "quote": f"{d0_v:.2f}/{d1_v:.2f}",
                    "overround": round(overround, 4),
                    "observed_utc": item.get("observed_utc"),
                    "url": bov_url,
                })
                break

    # 5. Unibet / Kambi European Regulated Sportsbook JSON Feed
    for item in kambi_index:
        a, b = item["names"]
        if close_in_time(start, item["start"]) and (
                (same_team(name0, a) and same_team(name1, b)) or
                (same_team(name0, b) and same_team(name1, a))):
            d0_v = item["d0"] if same_team(name0, a) else item["d1"]
            d1_v = item["d1"] if same_team(name0, a) else item["d0"]
            dv = devig_decimal(d0_v, d1_v, {"fixture_id": fixture_id, "venue": "Unibet"})
            if dv:
                p0_v, p1_v, overround = dv
                if primary_decimal is None:
                    primary_decimal = {"home": round(d0_v, 3), "away": round(d1_v, 3)}
                venues.append({
                    "name": "Unibet",
                    "weight": VENUE_WEIGHTS["Unibet"],
                    "p0": round(p0_v, 4),
                    "p1": round(p1_v, 4),
                    "quote": f"{d0_v:.2f}/{d1_v:.2f}",
                    "overround": round(overround, 4),
                    "observed_utc": item.get("observed_utc"),
                    "url": item["url"],
                })
                break

    # Archives are evidence, not a live line: no archived esportsbook receipt enters a
    # current consensus. The esportsbook venue is therefore left empty here on purpose.

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

    total_volume = sum(float(v.get("volume_usd") or 0) for v in venues) or None
    book_label = (f"{len(venues)}-Venue Consensus" if len(venues) >= 2 else venues[0]["name"])
    # A single prediction market with almost no traded volume is a price, not a market.
    # It stays published (it is the only external evidence) but never at high confidence.
    thin = len(venues) == 1 and venues[0]["name"] == "Polymarket" \
        and float(venues[0].get("volume_usd") or 0.0) < THIN_VOLUME_USD
    return {
        "thin": thin,
        "thin_note": (f"single Polymarket venue with ${float(venues[0].get('volume_usd') or 0):,.0f} "
                      f"traded volume (thin-market threshold ${THIN_VOLUME_USD:,.0f})") if thin else "",
        "book": book_label,
        "kind": "bookmaker" if any(v["name"] in ("Pinnacle", "Bovada", "Unibet") for v in venues) else "prediction market",
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
        "total_volume_usd": total_volume,
        "volume_usd": (max((v.get("volume_usd") or 0.0) for v in venues) if total_volume else None),
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
    kambi = load_json(os.path.join(RAW, "kambi_lol.json")) or {}
    # Historical archive is evidence only, never a live pricing input: it cannot be
    # re-verified on the build machine, so it is excluded and reported instead.
    receipts = {}
    receipts_doc = load_json(os.path.join(ROOT, "archive", "session-8336fb7e", "data", "book_receipts.json")) or {}
    archived_receipts = receipts_doc.get("quotes") or receipts_doc.get("receipts") or {}
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
    ratings, priors, counts, last_seen, uf, backtest, chrono_games = build_ratings(lp_matches)
    snap_cache: dict[str, tuple[dict, dict, dict, dict, UnionFind]] = {}

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

    pin_obs = pin.get("fetched_utc")
    pm_obs = pmkt.get("fetched_utc")
    kalshi_obs = kalshi.get("fetched_utc")
    bovada_obs = bovada.get("fetched_utc")
    kambi_obs = kambi.get("fetched_utc")

    pin_index = []
    pin_kills_excluded = 0
    for mk in pin.get("markets") or []:
        names = [p["name"] for p in mk.get("participants", [])]
        # A "(Kills)" participant market is a derivative on total kills in the series,
        # not the series winner: it must never be treated as the match moneyline.
        if any("(kills)" in str(n).lower() for n in names):
            pin_kills_excluded += 1
            continue
        if len(names) == 2:
            pin_index.append({"names": names, "row": mk, "start": mk.get("start_utc"),
                              "observed_utc": pin_obs})

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
        if re.search(r"\b(game|map)\s*\d\b|\bhandicap\b|\btotal\b", q, re.I):
            continue
        pm_candidates.append({"names": outcomes, "p0": pa, "p1": pb, "volume": vol,
                              "slug": mk.get("slug"),
                              "start": mk.get("game_start"),
                              "observed_utc": pm_obs})
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
                "observed_utc": kalshi_obs,
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
                "observed_utc": bovada_obs,
            })

    kambi_index = []
    kambi_fresh = False
    if kambi_obs:
        try:
            kambi_age_h = (now_utc() - datetime.strptime(str(kambi_obs)[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)).total_seconds() / 3600
            kambi_fresh = kambi_age_h <= RECEIPT_MAX_AGE_HOURS
        except ValueError:
            kambi_fresh = False
    if kambi_fresh:
        for ev in kambi.get("events") or []:
            outs = ev.get("outcomes") or []
            if len(outs) == 2:
                kambi_index.append({
                    "names": [outs[0]["name"], outs[1]["name"]],
                    "d0": float(outs[0]["decimal"]),
                    "d1": float(outs[1]["decimal"]),
                    "start": ev.get("start_utc"),
                    "url": ev.get("url") or kambi.get("source_url") or "",
                    "observed_utc": ev.get("changed_utc") or kambi_obs,
                })

    now_dt_eval = now_utc()
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

        # Strictly pre-kickoff ratings for every fixture (dt < start_utc), preventing any
        # look-ahead leakage into published win probabilities and decaying to kick-off date.
        use_r, use_p, use_c, use_ls, use_uf = ratings, priors, counts, last_seen, uf
        fix_start_dt = None
        if f.get("start_utc"):
            try:
                fix_start_dt = datetime.strptime(f["start_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                skey = f["start_utc"]
                if skey not in snap_cache:
                    snap_cache[skey] = snapshot_ratings(chrono_games, fix_start_dt)
                use_r, use_p, use_c, use_ls, use_uf = snap_cache[skey]
            except ValueError:
                fix_start_dt = None

        er0_raw = effective_rating(k0, use_r, use_c, use_p, page) if k0 else None
        er1_raw = effective_rating(k1, use_r, use_c, use_p, page) if k1 else None
        er0_now = effective_rating(k0, ratings, counts, priors, page) if k0 else None
        er1_now = effective_rating(k1, ratings, counts, priors, page) if k1 else None
        er0 = round(er0_raw, 1) if er0_raw is not None else None
        er1 = round(er1_raw, 1) if er1_raw is not None else None
        n0c = use_c.get(k0, 0) if k0 else 0
        n1c = use_c.get(k1, 0) if k1 else 0
        connected = bool(k0 and k1 and use_uf.find(k0) == use_uf.find(k1))

        dq_norms = {norm_name(t): t for t in (lp_dq.get(page or "") or [])}
        dq0 = dq_norms.get(norm_name(k0 or n0))
        dq1 = dq_norms.get(norm_name(k1 or n1))

        market = market_lookup(f["id"], n0, n1, f.get("start_utc"),
                               pin_index, pm_index, kalshi_index, bovada_index, kambi_index)
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
                      "rating_as_of": f["start_utc"],
                      "last_played": use_ls.get(k0).strftime("%Y-%m-%d") if k0 in use_ls else None,
                      "elo_raw": round(use_r[k0], 1) if k0 in use_r else None,
                      "elo_now": round(er0_now, 1) if er0_now is not None else None,
                      "elo": er0},
            "team1": {"name": n1, "leaguepedia": k1, "join": m1, "join_notes": note1,
                      "rating_matches": n1c,
                      "rating_as_of": f["start_utc"],
                      "last_played": use_ls.get(k1).strftime("%Y-%m-%d") if k1 in use_ls else None,
                      "elo_raw": round(use_r[k1], 1) if k1 in use_r else None,
                      "elo_now": round(er1_now, 1) if er1_now is not None else None,
                      "elo": er1},
        }

        flags: list[str] = []
        resolution = None
        if dq0 or dq1:
            removed = dq0 or dq1
            active_opp = n1 if dq0 else n0
            active_side = 1 if dq0 else 0
            p0 = p1 = None
            method, confidence = "unresolved", "none"
            pick_type = "settlement"
            lp_row = leaguepedia_row(n0, n1, f.get("start_utc"))
            ff = (lp_row or {}).get("ff")
            if ff in (1, 2):
                forfeit_note = (f"Leaguepedia records this series with its forfeit flag (FF={ff}, i.e. "
                                f"{removed} forfeited), 0-2 in favour of {active_opp}. ")
            elif lp_row:
                forfeit_note = (f"Leaguepedia records the series as a 0-2 loss for {removed}, but this "
                                f"snapshot captured no forfeit flag for it. ")
            else:
                forfeit_note = (f"Leaguepedia records no series between these teams on this date. ")
            basis = (f"Participant removed mid-split: community-maintained Leaguepedia Data:{page} records "
                     f"'dqteams={removed}'. " + forfeit_note +
                     f"Hotspawn's published rule voids all predictions on a forfeited match "
                     f"(play.hotspawn.com/how-it-works), so expect 0 points either way; if graded as a "
                     f"walkover instead, the winner is {active_opp}. No competitive probability is claimed.")
            flags.append(f"Leaguepedia-reported league removal: {removed} listed in Data:{page} dqteams "
                         f"(if not voided by Hotspawn, active opponent is {active_opp})")
            resolution = {
                "type": "official-forfeit",
                "winner": active_opp,
                "loser": removed,
                "note": (f"Leaguepedia records every remaining {removed} fixture as a 0-2 forfeit "
                         f"(ff flag), so the official settlement pick is {active_opp}. Hotspawn's "
                         f"published rule voids forfeited-match predictions (0 points either way); "
                         f"the pick matters only if Hotspawn grades a walkover instead."),
                "source": f"https://lol.fandom.com/wiki/Data:{page.replace(' ', '_')}",
            }
        elif market:
            p0, p1 = market["p0"], market["p1"]
            method, confidence = "market", "high"
            if (market.get("venue_count") or 0) == 1 and (market.get("total_volume_usd") or 0) < 1000:
                confidence = "low"
                flags.append(
                    f"single thin prediction market: only ${market.get('total_volume_usd') or 0:,.0f} "
                    f"traded volume on {market.get('book')} - treat as an indicative line")
            v_summary = ", ".join(f"{v['name']} {v['p0']*100:.1f}%/{v['p1']*100:.1f}% ({v['quote']})"
                                  for v in market.get("venues") or [])
            basis = f"{market['book']} de-vigged line ({p0*100:.1f}% / {p1*100:.1f}%): {v_summary}."
            # Independent cross-check: what does our own Elo line say about the same match?
            # Published next to the market number, and flagged when the gap is large.
            if er0 is not None and er1 is not None:
                elo_p = clamp(win_probability(er0, er1))
                market["model_cross_check"] = round(elo_p, 4)
                gap = abs(p0 - elo_p)
                if gap >= MARKET_MODEL_GAP:
                    strong = market["p0"] > market["p1"]
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
            # Full-coverage brief: publish an explicit low-confidence line rather than a blank,
            # with the 1500 prior stated on the card so the assumption is visible, never hidden.
            rated_is_0 = er0 is not None
            p0 = clamp(win_probability(er0 if rated_is_0 else ELO_START,
                                       ELO_START if rated_is_0 else er1))
            p1 = round(1 - p0, 4)
            method, confidence = "provisional", "low"
            missing = n1 if rated_is_0 else n0
            basis = (f"Elo line with one unrated side: {missing} has no rated series on record, "
                     f"so the 1500 league-average prior is used for that side. Low confidence.")
            flags.append(f"{missing} has no rated series in Leaguepedia (1500 prior used)")
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
        if fix_start_dt is not None:
            # Any fixture whose published start time has passed is marked, so a card can
            # never look like an upcoming pick after kick-off. Pre-kickoff ratings above ensure
            # post-start outcomes never leak into p0/p1.
            stale = (now_dt_eval - fix_start_dt).total_seconds() > 0
        result = None
        if stale:
            lp_done = leaguepedia_row(k0 or n0, k1 or n1, f.get("start_utc"))
            done_note = None
            if lp_done and lp_done.get("winner") in ("1", "2") and lp_done.get("utc"):
                try:
                    lp_dt_done = datetime.strptime(str(lp_done["utc"])[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                    if abs((lp_dt_done - fix_start_dt).total_seconds()) <= 12 * 3600:
                        s_a, s_b = lp_done.get("team1_score"), lp_done.get("team2_score")
                        done_note = (f"{lp_done.get('team1')} {s_a}-{s_b} {lp_done.get('team2')} "
                                     f"(Leaguepedia Data:{lp_done.get('overview_page')})")
                        # Structured, gradable result. Only accepted when the recorded pair is
                        # this fixture's pair and the record is within 12 h of kick-off; the
                        # winner must also be consistent with the recorded score, so a partial
                        # or contradictory row is left blank rather than graded on a guess.
                        lp_a, lp_b = str(lp_done.get("team1") or ""), str(lp_done.get("team2") or "")
                        same_order = (norm_name(lp_a) == norm_name(row["team0"]["name"])
                                      and norm_name(lp_b) == norm_name(row["team1"]["name"]))
                        swap_order = (norm_name(lp_a) == norm_name(row["team1"]["name"])
                                      and norm_name(lp_b) == norm_name(row["team0"]["name"]))
                        if same_order or swap_order:
                            win_raw = str(lp_done.get("winner"))
                            win_side = 0 if (win_raw == "1") == same_order else 1
                            sc0 = s_a if same_order else s_b
                            sc1 = s_b if same_order else s_a
                            score_ok = None
                            try:
                                if sc0 is not None and sc1 is not None:
                                    i0, i1 = int(sc0), int(sc1)
                                    score_ok = (i0 > i1) == (win_side == 0) if i0 != i1 else False
                            except (TypeError, ValueError):
                                score_ok = None
                            if score_ok is not False:
                                result = {
                                    "winner_side": win_side,
                                    "score0": sc0, "score1": sc1,
                                    "leaguepedia_winner": win_raw,
                                    "leaguepedia_match_id": lp_done.get("match_id") or "",
                                    "leaguepedia_page": lp_done.get("overview_page") or "",
                                    "utc": f"{str(lp_done['utc'])[:19].replace(' ', 'T')}Z",
                                    "forfeit_flag": lp_done.get("ff"),
                                    "source": ("https://lol.fandom.com/wiki/Data:"
                                               + str(lp_done.get("overview_page") or "").replace(" ", "_")),
                                    "note": "league result from community-maintained Leaguepedia",
                                }
                except ValueError:
                    done_note = None
            if done_note and method != "unresolved":
                flags.append(f"start time has passed and Leaguepedia records completed series {done_note}; "
                             f"probability reflects strictly pre-kickoff ratings while Hotspawn card remains open")
            else:
                flags.append("start time has passed but Hotspawn still lists the fixture as scheduled "
                             "(reason unverified)")
        # Cross-check the published kick-off against the official Leaguepedia series record.
        if f.get("start_utc") and page and k0 and k1:
            lp_list = lp_times.get((page, frozenset((str(k0), str(k1))))) or []
            # Only when the official record holds exactly one series for this pair, so a
            # double round-robin can never produce a false mismatch.
            lp_utc = lp_list[0] if len(lp_list) == 1 else None
            if lp_utc:
                try:
                    hs_dt = datetime.strptime(f["start_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                    lp_dt = datetime.strptime(str(lp_utc)[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                    hours = abs((hs_dt - lp_dt).total_seconds()) / 3600
                    if hours >= 1.5:
                        flags.append(
                            f"kick-off differs from the official Leaguepedia record: Hotspawn lists "
                            f"{f['start_utc']} while Data:{page} records {str(lp_utc)[:16]}Z "
                            f"({hours:.0f}h apart) - confirm before relying on the time")
                except ValueError:
                    pass
        if row["team0"]["join"] == "ambiguous" or row["team1"]["join"] == "ambiguous":
            flags.append("team name could not be matched unambiguously")

        pick = None
        pick_type = None
        if p0 is None and resolution:
            # Settlement pick: names the administrative winner, claims no probability.
            pick = {"team": resolution["winner"], "probability": None}
            pick_type = "settlement"
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
        # Grade the published pick against the official series record, when one exists. A pick
        # is graded only where the result is structured and internally consistent (see above);
        # settlement picks are reported as settled, never as a forecast that "won".
        grade = None
        if result and pick:
            if pick.get("probability") is not None and pick.get("side") is not None:
                grade = "hit" if pick["side"] == result["winner_side"] else "miss"
            elif pick_type == "settlement":
                grade = "settled"
                result["settlement_matched"] = (pick.get("team") == resolution.get("winner")
                                                if resolution else None)
        row.update({"p0": round(p0, 4) if p0 is not None else None,
                    "p1": round(p1, 4) if p1 is not None else None,
                    "method": method, "confidence": confidence, "basis": basis,
                    "flags": sorted(set(flags)), "pick": pick, "pick_type": pick_type,
                    "market": market, "resolution": resolution,
                    "connected": connected, "stale": stale,
                    "result": result, "grade": grade,
                    "community_pick_pct": f["community_pick_pct"]})
        rows.append(row)

    counts_by_method: dict[str, int] = {}
    for r in rows:
        counts_by_method[r["method"]] = counts_by_method.get(r["method"], 0) + 1

    # ---- published track record -------------------------------------------------------
    # Every card that has kicked off and has an official series record is graded, so the site
    # can show whether the picks it published were right instead of only asserting coverage.
    graded = [r for r in rows if r.get("grade") in ("hit", "miss")]
    hits = sum(1 for r in graded if r["grade"] == "hit")
    briers, by_method = [], {}
    for r in graded:
        mname = r.get("method") or "unknown"
        b = by_method.setdefault(mname, {"graded": 0, "hits": 0})
        b["graded"] += 1
        b["hits"] += 1 if r["grade"] == "hit" else 0
        if r.get("p0") is not None and (r.get("result") or {}).get("winner_side") is not None:
            p_win = r["p0"] if r["result"]["winner_side"] == 0 else r["p1"]
            briers.append((float(p_win) - 1.0) ** 2)
    for b in by_method.values():
        b["accuracy"] = round(b["hits"] / b["graded"], 4) if b["graded"] else None
    track_record = {
        "graded": len(graded),
        "hits": hits,
        "misses": len(graded) - hits,
        "accuracy": round(hits / len(graded), 4) if graded else None,
        "brier": round(sum(briers) / len(briers), 4) if briers else None,
        "settled_forfeits": sum(1 for r in rows if r.get("grade") == "settled"),
        "ungraded_started": sum(1 for r in rows if r.get("stale") and not r.get("grade")),
        "by_method": by_method,
        "result_source": "Leaguepedia MatchSchedule (community-maintained), matched on team pair and kick-off within 12 h",
        "grading_rule": ("hit = the published pick is the recorded series winner; miss = the other side won; "
                         "settled = an official-forfeit settlement pick, never counted as a forecast win. "
                         "Rows without a consistent official record stay ungraded."),
    }

    live_ids = {r["id"] for r in rows}
    retired = []
    for fid, q in (archived_receipts or {}).items():
        if str(fid) in live_ids:
            retired.append({
                "fixture_id": str(fid),
                "team0": q.get("team0"), "team1": q.get("team1"),
                "decimal": [q.get("decimal0"), q.get("decimal1")],
                "book_label": q.get("book_label"),
                "source_url": q.get("source_url"),
                "observed_at": q.get("observed_at"),
            })
    retired_by_fixture = {}
    for entry in retired:
        retired_by_fixture.setdefault(str(entry["fixture_id"]), entry)
    for row in rows:
        entry = retired_by_fixture.get(str(row["id"]))
        if not entry or row.get("method") == "market":
            continue
        dec = "/".join(f'{d:.3f}' if d and d < 2 else f'{d:.2f}' for d in (entry.get("decimal") or []) if d)
        row.setdefault("flags", []).append(
            f"archived external quote retired as unverifiable: {entry.get('book_label') or 'aggregator'} "
            f"{dec or 'n/a'} captured {str(entry.get('observed_at') or '')[:10]}; that page now shows symmetric "
            f"1.80 / 1.80 placeholder prices, so this line is originated instead")

    save_json(os.path.join(DATA, "retired_quotes.json"), {
        "generated_utc": iso(now_utc()),
        "reason": ("Archived third-party quotes from archive/session-8336fb7e/data/book_receipts.json are "
                   "not re-verifiable: the aggregator returns HTTP 403 to the build runner and its live "
                   "match pages currently show symmetric 1.8/1.8 placeholders. Excluded from every "
                   "probability so that no unverifiable price can influence a pick."),
        "retired_count": len(retired),
        "quotes": retired,
    })

    now_dt = now_utc()
    expired, rejected_quotes = [], []
    for fid, q in (archived_receipts or {}).items():
        try:
            obs = datetime.strptime(str(q.get("observed_at"))[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
            age_h = round((now_dt - obs).total_seconds() / 3600, 1)
        except (TypeError, ValueError):
            age_h = None
        d0, d1 = q.get("decimal0"), q.get("decimal1")
        entry = {"fixture_id": str(fid), "decimal": [d0, d1], "observed_at": q.get("observed_at"),
                 "age_hours": age_h, "source_url": q.get("source_url")}
        if age_h is None or age_h > RECEIPT_MAX_AGE_HOURS:
            expired.append(entry)
        if d0 and d1 and abs(float(d0) - 1.8) < 1e-9 and abs(float(d1) - 1.8) < 1e-9:
            rejected_quotes.append({"fixture_id": str(fid),
                                    "venue": q.get("book_label") or "archived aggregator",
                                    "reject": "symmetric 1.80/1.80 placeholder"})
    receipt_audit = {
        "max_age_hours": RECEIPT_MAX_AGE_HOURS,
        "used": [],
        "expired": expired,
        "rejected_quotes": rejected_quotes,
        "policy": ("Archived aggregator receipts are evidence only. A receipt may only be priced while it is "
                   "younger than max_age_hours and re-fetchable; none qualified on this build, so the venue is "
                   "empty and every affected fixture falls back to an originated line."),
    }

    save_json(os.path.join(DATA, "matches.json"), {
        "generated_utc": iso(now_utc()),
        "inventory_fetched_utc": hs.get("fetched_utc"),
        "receipt_audit": receipt_audit,
        "model": {"name": "LOLHOTSPAWN Elo", "k": ELO_K, "start": ELO_START,
                  "margin_weight": ELO_MOV_SLOPE, "shrink": ELO_SHRINK,
                  "rating_as_of": "kick-off", "min_matches_confident": MIN_MATCHES_CONFIDENT,
                  "prob_floor": PROB_FLOOR, "prob_ceil": PROB_CEIL,
                  "decay_start_days": DECAY_START_DAYS, "decay_full_days": DECAY_FULL_DAYS,
                  "window_start": lp.get("query", {}).get("where")},
        "sources": {"hotspawn": hs.get("source_url"), "pinnacle": pin.get("source_url"),
                    "kalshi": kalshi.get("source_url"), "bovada": bovada.get("source_url"),
                    "unibet": kambi.get("source_url"),
                    "leaguepedia": lp.get("source_url"), "polymarket": pmkt.get("source_url"),
                    "source_status_utc": sources.get("checked_utc")},
        "counts": counts_by_method,
        "market_hygiene": {
            "pinnacle_kills_derivatives_excluded": pin_kills_excluded,
            "archived_receipts_retired": len(retired),
            "esportsbook_venue_active": bool(receipts),
            "walkover_settlement_count": sum(1 for r in rows if r.get("pick_type") == "settlement"),
        },
        "backtest": backtest,
        "track_record": track_record,
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
                    "hotspawn_url", "market_source", "grade", "result_winner", "result_score",
                    "result_source"])
        for r in rows:
            res = r.get("result") or {}
            w.writerow([r["id"], r["start_utc"], r["competition"], r["tier"],
                        r["team0"]["name"], r["p0"], r["team1"]["name"], r["p1"],
                        r["pick"]["team"] if r["pick"] else "",
                        r["pick"]["probability"] if r["pick"] else "",
                        r["method"], r["confidence"], r["basis"], "; ".join(r["flags"]),
                        r["hotspawn_url"], (r["market"] or {}).get("api_url", ""),
                        r.get("grade") or "",
                        (r["team0"]["name"] if res.get("winner_side") == 0 else
                         (r["team1"]["name"] if res.get("winner_side") == 1 else "")),
                        (f'{res.get("score0")}-{res.get("score1")}' if res else ""),
                        res.get("source", "")])
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
