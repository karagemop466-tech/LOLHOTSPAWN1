#!/usr/bin/env python3
"""Build our own win probabilities and picks for every Hotspawn LoL pick'em match.

Method order (documented on the site):
  1. MARKET      - de-vigged moneyline from a bookmaker / prediction market.
  2. MODEL       - our own Elo line fitted on Leaguepedia series results, used when
                   the two teams are connected by a shared-opponent chain and each
                   side has enough rated series.
  3. PROVISIONAL - Elo line emitted with an explicit low-confidence flag because the
                   data is thin (few rated series, one unrated side, or no shared
                   opponent chain).
  4. UNRESOLVED  - no defensible probability (no rating for either side, TBD card).

Hotspawn's community pick percentages are stored for transparency but are NEVER
used by the model or by any pick.
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DATA, RAW, iso, load_json, log, norm_name, now_utc, save_json

ELO_START = 1500.0
ELO_K = 24.0
ELO_SHRINK = 5.0              # r_eff = 1500 + (r - 1500) * n / (n + 5)
MIN_MATCHES_CONFIDENT = 5     # rated series per team required for "medium" confidence
PROB_FLOOR, PROB_CEIL = 0.05, 0.95
DECAY_START_DAYS = 45
DECAY_FULL_DAYS = 450
GENERIC_TOKENS = {"team", "teams", "esports", "esport", "gaming", "club", "gg", "lol", "e", "v"}


# --------------------------------------------------------------------------- helpers
def base_name(name: str) -> str:
    """Leaguepedia disambiguates with 'Name (Region Team)' - strip that suffix."""
    text = "" if name is None else str(name)
    return re.sub(r"\s*\([^)]*\)\s*$", "", text).strip()


def region_of(name: str) -> str:
    m = re.search(r"\(([^)]*)\)\s*$", "" if name is None else str(name))
    return m.group(1) if m else ""


def same_team(a: str, b: str) -> bool:
    """Loose equality used only for bookmaker-vs-Hotspawn name alignment."""
    na, nb = norm_name(a), norm_name(b)
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


def build_ratings(lp_matches: list[dict]) -> tuple[dict, dict, dict, UnionFind, dict]:
    ratings: dict[str, float] = {}
    counts: dict[str, int] = {}
    last_seen: dict[str, datetime] = {}
    uf = UnionFind()
    games: list[tuple[datetime, str, str, int]] = []

    for m in lp_matches:
        if m.get("winner") not in ("1", "2"):
            continue
        try:
            dt = datetime.strptime(str(m.get("utc"))[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
        games.append((dt, m["team1"], m["team2"], 1 if m["winner"] == "1" else 2))
        uf.union(m["team1"], m["team2"])

    games.sort(key=lambda g: g[0])
    bt = {"cutoff": BACKTEST_CUTOFF.strftime("%Y-%m-%d"), "n": 0, "hits": 0,
          "brier_sum": 0.0, "logloss_sum": 0.0, "buckets": {}}
    for dt, t1, t2, winner in games:
        r1 = ratings.get(t1, ELO_START)
        r2 = ratings.get(t2, ELO_START)
        exp1 = 1 / (1 + 10 ** ((r2 - r1) / 400))
        if dt >= BACKTEST_CUTOFF:
            # predict-then-update: this is an out-of-sample prediction
            y = 1.0 if winner == 1 else 0.0
            fav_p = max(exp1, 1 - exp1)
            hit = (exp1 >= 0.5) == (winner == 1)
            bt["n"] += 1
            bt["hits"] += 1 if hit else 0
            bt["brier_sum"] += (exp1 - y) ** 2
            eps = 1e-9
            bt["logloss_sum"] += -(y * __import__("math").log(max(exp1, eps)) +
                                   (1 - y) * __import__("math").log(max(1 - exp1, eps)))
            bucket = ("50-60%" if fav_p < 0.60 else "60-70%" if fav_p < 0.70 else
                      "70-80%" if fav_p < 0.80 else "80%+")
            b = bt["buckets"].setdefault(bucket, {"n": 0, "hits": 0, "sum_p": 0.0})
            b["n"] += 1
            b["hits"] += 1 if hit else 0
            b["sum_p"] += fav_p
        s1 = 1.0 if winner == 1 else 0.0
        ratings[t1] = r1 + ELO_K * (s1 - exp1)
        ratings[t2] = r2 + ELO_K * ((1 - s1) - (1 - exp1))
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
        for name, b in bt["buckets"].items():
            b["accuracy"] = round(b["hits"] / b["n"], 4) if b["n"] else None
            b["mean_predicted"] = round(b["sum_p"] / b["n"], 4) if b["n"] else None
            b.pop("sum_p", None)
    bt.pop("brier_sum", None)
    bt.pop("logloss_sum", None)
    return ratings, counts, last_seen, uf, bt


def effective_rating(team: str, ratings: dict, counts: dict) -> float | None:
    if team not in ratings:
        return None
    n = counts.get(team, 0)
    return ELO_START + (ratings[team] - ELO_START) * (n / (n + ELO_SHRINK))


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
    """Resolve a Hotspawn team name to an exact Leaguepedia team name."""
    key = norm_name(name)
    if not key:
        return None, "none", []
    if key in exact:
        return exact[key], "exact", []
    if key in aliases:
        target = aliases[key]
        if norm_name(target) in exact:
            return exact[norm_name(target)], "alias", []
        if target in page_teams.get(page or "", set()):
            return target, "alias", []

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


# --------------------------------------------------------------------------- market
def american_to_decimal(price) -> float | None:
    try:
        p = float(price)
    except (TypeError, ValueError):
        return None
    if p == 0:
        return None
    return round(1 + (p / 100 if p > 0 else 100 / abs(p)), 4)


def market_lookup(name0: str, name1: str, start: str | None, pin_index: list,
                  pm_index: list, within_hours: int = 18):
    """Find a bookmaker/prediction-market price pair for this fixture."""
    def close_in_time(a: str | None, b: str | None) -> bool:
        if not a or not b:
            return True
        try:
            da = datetime.strptime(a[:19], "%Y-%m-%dT%H:%M:%S")
            db = datetime.strptime(b[:19], "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            return True
        return abs((da - db).total_seconds()) <= within_hours * 3600

    for item in pin_index:
        a, b = item["names"]
        if close_in_time(start, item["start"]) and (
                (same_team(name0, a) and same_team(name1, b)) or
                (same_team(name0, b) and same_team(name1, a))):
            row = item["row"]
            home_dec = row["prices"]["home"]["decimal"]
            away_dec = row["prices"]["away"]["decimal"]
            inv = 1 / home_dec + 1 / away_dec
            p_home = (1 / home_dec) / inv
            p_away = (1 / away_dec) / inv
            home_name = next((p["name"] for p in row["participants"]
                              if p.get("alignment") == "home"), a)
            aligned = same_team(name0, home_name)
            return {
                "book": "Pinnacle",
                "kind": "bookmaker",
                "source_url": "https://www.pinnacle.com/en/esports/league-of-legends",
                "api_url": f"https://guest.api.arcadia.pinnacle.com/0.1/matchups/{row['matchup_id']}/markets/related/straight",
                "market_url": f"https://www.pinnacle.com/en/event/{row['matchup_id']}",
                "decimal": {"home": home_dec, "away": away_dec},
                "american": {k: v.get("american") for k, v in row["prices"].items()},
                "p0": round(p_home if aligned else p_away, 4),
                "p1": round(p_away if aligned else p_home, 4),
                "overround": round(inv - 1, 4),
                "start_utc": item["start"],
                "league": row.get("league"),
            }

    for item in pm_index:
        a, b = item["names"]
        if (same_team(name0, a) and same_team(name1, b)) or (same_team(name0, b) and same_team(name1, a)):
            p0 = item["p0"] if same_team(name0, a) else item["p1"]
            p1 = round(1 - p0, 4)
            return {
                "book": "Polymarket",
                "kind": "prediction market",
                "source_url": "https://polymarket.com/markets/league-of-legends",
                "market_url": f"https://polymarket.com/event/{item['slug']}",
                "decimal": None,
                "american": None,
                "p0": round(p0, 4),
                "p1": p1,
                "overround": 0.0,
                "start_utc": item.get("start"),
            }
    return None


# --------------------------------------------------------------------------- main
def main() -> None:
    hs = load_json(os.path.join(RAW, "hotspawn_lol.json")) or {}
    lp = load_json(os.path.join(RAW, "leaguepedia.json")) or {}
    pin = load_json(os.path.join(RAW, "pinnacle_lol.json")) or {}
    pmkt = load_json(os.path.join(RAW, "polymarket.json")) or {}
    sources = load_json(os.path.join(DATA, "sources_status.json")) or {}

    fixtures = hs.get("fixtures") or []
    lp_matches = lp.get("matches") or []
    if not fixtures:
        raise SystemExit("no hotspawn fixtures - run collect.py first")

    exact, base, page_teams = build_index(lp_matches)
    aliases_raw = (load_json(os.path.join(DATA, "aliases.json"), default={}) or {}).get("aliases") or {}
    aliases = {norm_name(k): v for k, v in aliases_raw.items()}
    comp_map = map_competitions(fixtures, page_teams, base)

    # (page, unordered team pair) -> recorded kick-off, used to corroborate times
    lp_times = {}
    for m in lp_matches:
        lp_times[(m.get("overview_page"), frozenset(
            (str(m.get("team1")), str(m.get("team2")))))] = m.get("utc")
    ratings, counts, last_seen, uf, backtest = build_ratings(lp_matches)

    pin_index = []
    for mk in pin.get("markets") or []:
        names = [p["name"] for p in mk.get("participants", [])]
        if len(names) == 2:
            pin_index.append({"names": names, "row": mk, "start": mk.get("start_utc")})

    pm_index = []
    for mk in pmkt.get("match_markets") or []:
        outcomes = mk.get("outcomes") or []
        prices = mk.get("prices") or []
        if len(outcomes) != 2 or len(prices) != 2:
            continue
        try:
            pa, pb = float(prices[0]), float(prices[1])
        except (TypeError, ValueError):
            continue
        if not (0 < pa < 1 and 0 < pb < 1):   # resolved or degenerate markets are not prices
            continue
        if re.search(r"game \d", mk.get("question", ""), re.I):
            continue
        pm_index.append({"names": outcomes, "p0": pa, "p1": pb,
                         "slug": mk.get("slug"), "start": mk.get("event_start")})

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

        market = market_lookup(n0, n1, f.get("start_utc"), pin_index, pm_index)
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
        if market:
            p0, p1 = market["p0"], market["p1"]
            method, confidence = "market", "high"
            if market["kind"] == "bookmaker":
                basis = (f"De-vigged {market['book']} moneyline: {market['decimal']['home']} / "
                         f"{market['decimal']['away']} (overround {market['overround']:.2%}).")
                if market.get("start_utc") and f.get("start_utc"):
                    try:
                        a = datetime.strptime(f["start_utc"], "%Y-%m-%dT%H:%M:%SZ")
                        b = datetime.strptime(str(market["start_utc"])[:19], "%Y-%m-%dT%H:%M:%S")
                        hours = abs((a - b).total_seconds()) / 3600
                        if hours >= 1.5:
                            lp_utc = lp_times.get((page, frozenset((str(k0), str(k1))))) if k0 and k1 else None
                            corroborated = False
                            if lp_utc:
                                try:
                                    c = datetime.strptime(str(lp_utc)[:19], "%Y-%m-%d %H:%M:%S")
                                    corroborated = abs((a - c).total_seconds()) <= 3600
                                except ValueError:
                                    corroborated = False
                            if corroborated:
                                flags.append(
                                    f"kick-off time differs between sources: Hotspawn and Leaguepedia say "
                                    f"{f['start_utc']} but {market['book']} lists "
                                    f"{str(market['start_utc'])[:16]}Z ({hours:.0f}h apart) - the odds are "
                                    f"for this pairing, but confirm the start time before betting")
                            else:
                                flags.append(
                                    f"kick-off time differs between sources: Hotspawn says {f['start_utc']} "
                                    f"and {market['book']} lists {str(market['start_utc'])[:16]}Z "
                                    f"({hours:.0f}h apart) - confirm before betting")
                            basis += (f" Kick-off: Hotspawn {f['start_utc']}"
                                      f"{' (Leaguepedia agrees)' if corroborated else ''}, "
                                      f"{market['book']} {str(market['start_utc'])[:16]}Z.")
                    except ValueError:
                        pass
            else:
                basis = f"{market['book']} prices {p0:.1%} / {p1:.1%} (no vig)."
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
            rated_is_0 = er0 is not None
            p0 = clamp(win_probability(er0 if rated_is_0 else ELO_START,
                                       ELO_START if rated_is_0 else er1))
            p1 = round(1 - p0, 4)
            method, confidence = "provisional", "low"
            missing = n1 if rated_is_0 else n0
            basis = (f"Elo line with one unrated side: {missing} has no rated series on "
                     f"record, so the 1500 baseline is used for that side.")
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

        for side, notes in ((row["team0"], note0), (row["team1"], note1)):
            flags.extend(notes)
        stale = False
        if f.get("start_utc"):
            try:
                start_dt = datetime.strptime(f["start_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                stale = (datetime.now(timezone.utc) - start_dt).total_seconds() > 3 * 3600
            except ValueError:
                stale = False
        if stale:
            flags.append("start time has passed but Hotspawn still lists the fixture as scheduled "
                         "(likely postponed or awaiting a result)")
        if row["team0"]["join"] == "ambiguous" or row["team1"]["join"] == "ambiguous":
            flags.append("team name could not be matched unambiguously")

        pick = None
        if p0 is not None:
            side = 0 if p0 >= p1 else 1
            pick = {"side": side,
                    "team": row["team0"]["name"] if side == 0 else row["team1"]["name"],
                    "probability": round(max(p0, p1), 4),
                    "other_probability": round(min(p0, p1), 4)}
        row.update({"p0": round(p0, 4) if p0 is not None else None,
                    "p1": round(p1, 4) if p1 is not None else None,
                    "method": method, "confidence": confidence, "basis": basis,
                    "flags": sorted(set(flags)), "pick": pick, "market": market,
                    "connected": connected, "stale": stale,
                    "community_pick_pct": f["community_pick_pct"]})
        rows.append(row)

    counts_by_method: dict[str, int] = {}
    for r in rows:
        counts_by_method[r["method"]] = counts_by_method.get(r["method"], 0) + 1

    save_json(os.path.join(DATA, "matches.json"), {
        "generated_utc": iso(now_utc()),
        "model": {"name": "LOLHOTSPAWN Elo", "k": ELO_K, "start": ELO_START,
                  "shrink": ELO_SHRINK, "min_matches_confident": MIN_MATCHES_CONFIDENT,
                  "prob_floor": PROB_FLOOR, "prob_ceil": PROB_CEIL,
                  "decay_start_days": DECAY_START_DAYS, "decay_full_days": DECAY_FULL_DAYS,
                  "window_start": lp.get("query", {}).get("where")},
        "sources": {"hotspawn": hs.get("source_url"), "pinnacle": pin.get("source_url"),
                    "leaguepedia": lp.get("source_url"), "polymarket": pmkt.get("source_url"),
                    "source_status_utc": sources.get("checked_utc")},
        "counts": counts_by_method,
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
