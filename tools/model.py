#!/usr/bin/env python3
"""Build our own win probabilities and picks for every Hotspawn LoL pick'em match.

Method order (documented on the site):
  1. MARKET   - de-vigged moneyline from Pinnacle (a sharp esportsbook).
  2. MODEL    - our own Elo line, fitted on Leaguepedia series results, when the
                two teams are connected by a shared-opponent chain and each has
                enough rated matches.
  3. PROVISIONAL - Elo line emitted with an explicit low-confidence flag when the
                data is thin (few rated matches or no shared-opponent chain).
  4. UNRESOLVED - no defensible probability (no rating for either side, or TBD).

Hotspawn's community pick percentages are deliberately excluded from all maths.
"""
from __future__ import annotations

import csv
import difflib
import itertools
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DATA, RAW, iso, load_json, log, norm_name, now_utc, save_json

ELO_START = 1500.0
ELO_K = 24.0
ELO_SHRINK = 5.0            # shrinkage: r_eff = 1500 + (r-1500) * n/(n+5)
MIN_MATCHES_CONFIDENT = 5   # rated matches per team for "medium" confidence
PROB_FLOOR, PROB_CEIL = 0.05, 0.95
SHRINK_DECAY_LIMIT_DAYS = 450  # ratings decay toward the mean over ~15 months

QUALIFIER_TOKENS = {
    "academy", "acad", "white", "black", "red", "blue", "uk", "sweden", "norway",
    "denmark", "finland", "rising", "prime", "hearts", "youth", "junior", "juniors",
    "2", "ii", "b", "a", "tbd", "ev", "esport", "esports", "gaming", "team", "club",
}


# --------------------------------------------------------------------------- aliases
def load_aliases() -> dict:
    data = load_json(os.path.join(DATA, "aliases.json"), default={}) or {}
    return {norm_name(k): v for k, v in (data.get("aliases") or {}).items()}


def canonical(name: str, index: dict[str, str], aliases: dict[str, str]) -> tuple[str | None, str, float]:
    """Resolve a raw team name to a Leaguepedia team key.

    Returns (resolved_key, method, score). method in {exact, alias, fuzzy, subset, none}.
    """
    key = norm_name(name)
    if not key:
        return None, "none", 0.0
    if key in index:
        return index[key], "exact", 1.0
    if key in aliases and norm_name(aliases[key]) in index:
        return index[norm_name(aliases[key])], "alias", 1.0

    # token-subset rule with qualifier guard
    tokens = set(key.split())
    best = None
    for cand_key, cand in index.items():
        ct = set(cand_key.split())
        if not tokens or not ct:
            continue
        if tokens < ct or ct < tokens:
            diff = (tokens ^ ct)
            if diff & QUALIFIER_TOKENS:
                continue
            short, long_ = (tokens, ct) if len(tokens) < len(ct) else (ct, tokens)
            if len("".join(short)) >= 4:
                score = len("".join(short)) / len("".join(long_))
                if score >= 0.45 and (best is None or score > best[2]):
                    best = (cand, "subset", round(score, 3))
    if best:
        return best[0], best[1], best[2]

    close = difflib.get_close_matches(key, list(index.keys()), n=2, cutoff=0.88)
    if len(close) == 1:
        return index[close[0]], "fuzzy", round(difflib.SequenceMatcher(None, key, close[0]).ratio(), 3)
    return None, "none", 0.0


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


def build_ratings(lp_matches: list[dict]) -> tuple[dict, dict, UnionFind]:
    ratings: dict[str, float] = {}
    counts: dict[str, int] = {}
    last_seen: dict[str, datetime] = {}
    uf = UnionFind()
    games: list[tuple[datetime, str, str, int]] = []

    for m in lp_matches:
        win = m.get("winner")
        if win not in ("1", "2"):
            continue
        try:
            dt = datetime.strptime(str(m.get("utc"))[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
        t1, t2 = m["team1"], m["team2"]
        games.append((dt, t1, t2, 1 if win == "1" else 2))
        uf.union(t1, t2)

    games.sort(key=lambda g: g[0])
    for dt, t1, t2, winner in games:
        r1 = ratings.get(t1, ELO_START)
        r2 = ratings.get(t2, ELO_START)
        exp1 = 1 / (1 + 10 ** ((r2 - r1) / 400))
        s1 = 1.0 if winner == 1 else 0.0
        ratings[t1] = r1 + ELO_K * (s1 - exp1)
        ratings[t2] = r2 + ELO_K * ((1 - s1) - (1 - exp1))
        counts[t1] = counts.get(t1, 0) + 1
        counts[t2] = counts.get(t2, 0) + 1
        last_seen[t1] = dt
        last_seen[t2] = dt

    # time decay toward the mean for teams that have not played recently
    today = datetime.now(timezone.utc)
    for team in list(ratings):
        days = max(0.0, (today - last_seen[team]).total_seconds() / 86400)
        if days > 45:
            factor = max(0.0, 1 - (days - 45) / SHRINK_DECAY_LIMIT_DAYS)
            ratings[team] = ELO_START + (ratings[team] - ELO_START) * factor

    return ratings, counts, uf


def effective_rating(team: str, ratings: dict, counts: dict) -> float | None:
    if team not in ratings:
        return None
    n = counts.get(team, 0)
    return ELO_START + (ratings[team] - ELO_START) * (n / (n + ELO_SHRINK))


def win_probability(r_a: float, r_b: float) -> float:
    return 1 / (1 + 10 ** ((r_b - r_a) / 400))


def clamp(p: float) -> float:
    return max(PROB_FLOOR, min(PROB_CEIL, p))


# --------------------------------------------------------------------------- main
def main() -> None:
    hs = load_json(os.path.join(RAW, "hotspawn_lol.json")) or {}
    lp = load_json(os.path.join(RAW, "leaguepedia.json")) or {}
    pin = load_json(os.path.join(RAW, "pinnacle_lol.json")) or {}
    pm = load_json(os.path.join(RAW, "polymarket.json")) or {}
    sources = load_json(os.path.join(DATA, "sources_status.json")) or {}

    fixtures = hs.get("fixtures") or []
    lp_matches = lp.get("matches") or []
    if not fixtures:
        raise SystemExit("no hotspawn fixtures - run collect.py first")

    # index leaguepedia teams
    index: dict[str, str] = {}
    for m in lp_matches:
        for t in (m["team1"], m["team2"]):
            index.setdefault(norm_name(t), t)
    aliases = load_aliases()
    ratings, counts, uf = build_ratings(lp_matches)

    # competition -> leaguepedia pages mapping evidence
    page_teams: dict[str, set] = {}
    for m in lp_matches:
        page = m.get("overview_page") or ""
        page_teams.setdefault(page, set()).update([m["team1"], m["team2"]])

    # ---- market index (pinnacle) ----
    pin_index = []
    for mk in pin.get("markets") or []:
        names = [p["name"] for p in mk.get("participants", [])]
        if len(names) != 2:
            continue
        pin_index.append({"names": names, "norm": [norm_name(n) for n in names],
                          "row": mk, "start": mk.get("start_utc")})

    def match_market(name0: str, name1: str, start: str | None):
        n0, n1 = norm_name(name0), norm_name(name1)
        for item in pin_index:
            a, b = item["norm"]
            if {a, b} == {n0, n1}:
                return item, "exact"
            # alias-aware
            c0 = canonical(name0, index, aliases)[0]
            c1 = canonical(name1, index, aliases)[0]
            if c0 and c1 and {norm_name(c0), norm_name(c1)} == {a, b}:
                return item, "alias"
            # subset/fuzzy on each side
            if (n0 in a or a in n0) and (n1 in b or b in n1) and min(len(n0), len(n1)) >= 3:
                return item, "subset"
        return None, "none"

    def market_pick(name0: str, name1: str, start: str | None):
        """Return dict with de-vigged probabilities aligned to (name0, name1)."""
        item, how = match_market(name0, name1, start)
        if not item:
            return None
        row = item["row"]
        home = row["prices"]["home"]["decimal"]
        away = row["prices"]["away"]["decimal"]
        inv = 1 / home + 1 / away
        p_home = (1 / home) / inv
        p_away = (1 / away) / inv
        # align to fixture order using participant names
        p0_name = norm_name(name0)
        home_name = None
        for p in row.get("participants", []):
            if p.get("alignment") == "home":
                home_name = norm_name(p.get("name"))
        if home_name is None:
            home_name = item["norm"][0]
        aligned = (home_name == p0_name) or (home_name in p0_name) or (p0_name in home_name)
        return {
            "book": "Pinnacle",
            "source_url": f"https://www.pinnacle.com/en/event/{row['matchup_id']}",
            "api_url": f"https://guest.api.arcadia.pinnacle.com/0.1/matchups/{row['matchup_id']}/markets/related/straight",
            "league": row.get("league"),
            "start_utc": row.get("start_utc"),
            "decimal": {"home": home, "away": away},
            "american": {k: v.get("american") for k, v in row["prices"].items()},
            "p0": round(p_home if aligned else p_away, 4),
            "p1": round(p_away if aligned else p_home, 4),
            "join": how,
            "overround": round(inv - 1, 4),
        }

    # ---- build rows ----
    rows = []
    joins = []
    for f in fixtures:
        n0, n1 = f["team0"]["name"], f["team1"]["name"]
        k0, m0, s0 = canonical(n0, index, aliases)
        k1, m1, s1 = canonical(n1, index, aliases)
        if m0 not in ("exact",) or m1 not in ("exact",):
            joins.append({"hotspawn": f["id"], "team": n0, "resolved": k0, "method": m0, "score": s0})
            joins.append({"hotspawn": f["id"], "team": n1, "resolved": k1, "method": m1, "score": s1})

        er0 = effective_rating(k0, ratings, counts) if k0 else None
        er1 = effective_rating(k1, ratings, counts) if k1 else None
        n0c = counts.get(k0, 0) if k0 else 0
        n1c = counts.get(k1, 0) if k1 else 0

        market = market_pick(n0, n1, f.get("start_utc"))
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
            "team0": {"name": n0, "leaguepedia": k0, "join": m0, "join_score": s0,
                      "rating_matches": n0c,
                      "elo_raw": round(ratings[k0], 1) if k0 in ratings else None,
                      "elo": round(er0, 1) if er0 is not None else None},
            "team1": {"name": n1, "leaguepedia": k1, "join": m1, "join_score": s1,
                      "rating_matches": n1c,
                      "elo_raw": round(ratings[k1], 1) if k1 in ratings else None,
                      "elo": round(er1, 1) if er1 is not None else None},
        }

        connected = bool(k0 and k1 and uf.find(k0) == uf.find(k1))

        if market:
            p0, p1 = market["p0"], market["p1"]
            method = "market"
            confidence = "high"
            basis = (f"De-vigged Pinnacle moneyline ({market['decimal']['home']} / "
                     f"{market['decimal']['away']}, overround {market['overround']:.2%}).")
            flags = [] if market["join"] == "exact" else [f"team-name join via {market['join']}"]
        elif er0 is not None and er1 is not None:
            p0 = clamp(win_probability(er0, er1))
            p1 = round(1 - p0, 4)
            method = "model"
            thin = (n0c < MIN_MATCHES_CONFIDENT or n1c < MIN_MATCHES_CONFIDENT or not connected)
            confidence = "low" if thin else "medium"
            basis = (f"Elo line: {n0} {er0:.0f} vs {n1} {er1:.0f} "
                     f"({n0c}/{n1c} rated series)")
            flags = []
            if not connected:
                flags.append("no shared-opponent chain between the two teams")
            if n0c < MIN_MATCHES_CONFIDENT or n1c < MIN_MATCHES_CONFIDENT:
                flags.append("fewer than 5 rated series for at least one team")
            if thin:
                method = "provisional"
        elif er0 is not None or er1 is not None:
            rated_is_0 = er0 is not None
            # unrated side is assigned the 1500 baseline, so no arbitrary constant is introduced
            p0 = clamp(win_probability(er0 if rated_is_0 else ELO_START,
                                       ELO_START if rated_is_0 else er1))
            p1 = round(1 - p0, 4)
            method = "provisional"
            confidence = "low"
            unrated = n1 if rated_is_0 else n0
            basis = (f"Elo line with one unrated side: {unrated} has no rated series in the "
                     f"Leaguepedia window; unrated teams are assigned the 1500 baseline.")
            flags = [f"{unrated} has no recorded series since 2025-09-01",
                     "one-sided data - treat as a weak signal"]
        else:
            p0 = p1 = None
            method = "unresolved"
            confidence = "none"
            basis = "No bookmaker line and no rated series for either team."
            flags = ["no data for either team"]
            if "tbd" in norm_name(n0) or "tbd" in norm_name(n1):
                basis = "Participant not yet decided (TBD) on the Hotspawn card."
                flags = ["participants not announced"]

        if method != "unresolved":
            pick_side = 0 if p0 >= p1 else 1
            pick = {"side": pick_side, "team": row["team0"]["name"] if pick_side == 0 else row["team1"]["name"],
                    "probability": round(max(p0, p1), 4),
                    "other_probability": round(min(p0, p1), 4)}
        else:
            pick = None

        row.update({
            "p0": round(p0, 4) if p0 is not None else None,
            "p1": round(p1, 4) if p1 is not None else None,
            "method": method,
            "confidence": confidence,
            "basis": basis,
            "flags": flags,
            "pick": pick,
            "market": market,
            "connected": connected,
            "community_pick_pct": f.get("community_pick_pct"),
        })
        rows.append(row)

    # ---- accountability + persistence ----
    counts_by_method: dict[str, int] = {}
    for r in rows:
        counts_by_method[r["method"]] = counts_by_method.get(r["method"], 0) + 1

    save_json(os.path.join(DATA, "matches.json"), {
        "generated_utc": iso(now_utc()),
        "model": {"name": "LOLHOTSPAWN Elo", "k": ELO_K, "start": ELO_START,
                  "shrink": ELO_SHRINK, "min_matches_confident": MIN_MATCHES_CONFIDENT,
                  "prob_floor": PROB_FLOOR, "prob_ceil": PROB_CEIL},
        "sources": {
            "hotspawn": hs.get("source_url"),
            "pinnacle": pin.get("source_url"),
            "leaguepedia": lp.get("source_url"),
            "polymarket": pm.get("source_url"),
            "source_status_utc": sources.get("checked_utc"),
        },
        "counts": counts_by_method,
        "total": len(rows),
        "matches": rows,
    })

    save_json(os.path.join(DATA, "matching_report.json"), {
        "generated_utc": iso(now_utc()),
        "non_exact_joins": joins,
        "non_exact_count": len(joins),
        "leaguepedia_teams": len(index),
        "ratings": len(ratings),
    })

    # CSV for line-by-line review
    csv_path = os.path.join(DATA, "picks.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["hotspawn_id", "start_utc", "competition", "tier", "team0", "p0", "team1", "p1",
                    "pick", "pick_probability", "method", "confidence", "basis", "flags",
                    "hotspawn_url", "market_source"])
        for r in rows:
            w.writerow([r["id"], r["start_utc"], r["competition"], r["tier"],
                        r["team0"]["name"], r["p0"], r["team1"]["name"], r["p1"],
                        r["pick"]["team"] if r["pick"] else "", r["pick"]["probability"] if r["pick"] else "",
                        r["method"], r["confidence"], r["basis"], "; ".join(r["flags"]),
                        r["hotspawn_url"],
                        (r["market"] or {}).get("api_url", "")])

    log(f"rows={len(rows)} methods={counts_by_method} non_exact_joins={len(joins)}")


def slugify(value: str) -> str:
    import re
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
