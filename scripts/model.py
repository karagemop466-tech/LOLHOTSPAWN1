"""Self-originated win probabilities (``basis = model``).

Why this exists: most matches in the Hotspawn LoL lobby are sub-tier (national 2nd/3rd
divisions, regional championships, academy leagues) and carry **no** published sportsbook or
prediction-market price.  To still produce a pick we originate our own line from the only
verifiable data that exists for those leagues: the completed series scorelines Hotspawn itself
lists on each league page (results, not pick percentages), converted into a series-level Elo
rating.

Model, in full:

``p_series = 1 / (1 + 10 ** -(R_A - R_B) / 420)``

* Ratings start at 1500 and are updated with K = 18 and a margin-of-victory multiplier of
  ``1 + 0.55 * (|series game diff| - 1)``.
* 4 relaxation passes over the result graph so that order of arrival does not matter.
* Every rating is shrunk toward 1500 by ``1500_weight / (1500_weight + n_games)`` — a team with
  two 2-0 sweeps cannot out-rank a team with thirty verified games.
* Results are only counted when both team labels and a scoreline were read from a Hotspawn
  league page; rows that fail that check are dropped and counted as ``skipped``.

This is a *form/strength* model: it deliberately ignores rosters, patch, side selection and
map vetoes because none of those are published for these leagues.  It is reported with an
explicit confidence band and every row links back to the scorelines it used.  It is never
presented as a betting line, and it is never seeded from Hotspawn's pick share.
"""

from __future__ import annotations

import math
from collections import defaultdict

from .common import canon_team, clamp, log

K = 18.0
SCALE = 420.0          # rating points per decade of odds (series level)
SHRINK_N = 8.0         # games at which a rating is halfway to the mean
MAX_EVIDENCE = 6       # how many source links are published per row


def _score_adjust(game_diff: int) -> float:
    return 1.0 + 0.55 * max(0, abs(game_diff) - 1)


def build_ratings(results: list[dict]) -> tuple[dict, dict]:
    """Return ``(ratings, meta)`` from verified series results.

    ``results`` rows: {team_home, team_away, score_home, score_away, source_url, league_slug}
    """
    clean: list[dict] = []
    skipped = 0
    for row in results:
        a, b = canon_team(row.get("team_home") or ""), canon_team(row.get("team_away") or "")
        sa, sb = row.get("score_home"), row.get("score_away")
        if not a or not b or a == b:
            skipped += 1
            continue
        if sa is None or sb is None or sa == sb:
            skipped += 1
            continue
        clean.append({"a": a, "b": b, "sa": int(sa), "sb": int(sb),
                      "url": row.get("source_url"), "league": row.get("league_slug")})

    names = sorted({r["a"] for r in clean} | {r["b"] for r in clean})
    rating = {n: 1500.0 for n in names}
    games = defaultdict(int)
    wins = defaultdict(int)
    h2h = defaultdict(lambda: defaultdict(int))
    for r in clean:
        h2h[r["a"]][r["b"]] += 1
        h2h[r["b"]][r["a"]] += 1

    for _ in range(4):
        delta = defaultdict(float)
        for r in clean:
            ra, rb = rating[r["a"]], rating[r["b"]]
            ea = 1.0 / (1.0 + 10 ** ((rb - ra) / 400.0))
            winner_is_a = r["sa"] > r["sb"]
            score = 1.0 if winner_is_a else 0.0
            adj = _score_adjust(r["sa"] - r["sb"])
            d = K * adj * (score - ea)
            delta[r["a"]] += d
            delta[r["b"]] -= d
        for name in names:
            rating[name] += delta[name]

    for r in clean:
        games[r["a"]] += 1
        games[r["b"]] += 1
        if r["sa"] > r["sb"]:
            wins[r["a"]] += 1
        else:
            wins[r["b"]] += 1

    evidence: dict[str, list[str]] = defaultdict(list)
    for r in clean:
        for name in (r["a"], r["b"]):
            if r.get("url") and len(evidence[name]) < MAX_EVIDENCE:
                evidence[name].append(r["url"])

    shrunk, meta = {}, {}
    for name in names:
        n = games[name]
        weight = SHRINK_N / (SHRINK_N + n)
        r0 = 1500.0 + (rating[name] - 1500.0) * weight
        shrunk[name] = round(r0, 1)
        meta[name] = {
            "games": n,
            "series_wins": wins[name],
            "win_rate": round(wins[name] / n, 3) if n else None,
            "raw_rating": round(rating[name], 1),
            "rating": round(r0, 1),
            "leagues": sorted({r["league"] for r in clean
                               if name in (r["a"], r["b"]) and r["league"]}),
            "evidence": evidence.get(name, []),
        }
    log(f"model: {len(names)} rated teams from {len(clean)} verified series ({skipped} rows skipped)")
    h2h_counts = {f"{a}|{b}": c for a, d in h2h.items() for b, c in d.items()}
    return shrunk, {"teams": meta, "h2h": h2h_counts, "results_used": len(clean),
                    "results_skipped": skipped,
                    "params": {"K": K, "scale": SCALE, "shrink_n": SHRINK_N, "passes": 4,
                               "mv_factor": "1 + 0.55 * (|series game diff| - 1)"}}


def series_prob(rating_a: float, rating_b: float) -> float:
    return clamp(1.0 / (1.0 + 10 ** ((rating_b - rating_a) / SCALE)), 0.02, 0.98)


def confidence(n_a: int, n_b: int, direct: int) -> str:
    """Confidence band: driven by verified sample size, not by opinion."""
    weakest = min(n_a, n_b)
    if weakest == 0:
        return "none"
    if weakest >= 6 and direct >= 1:
        return "high"
    if weakest >= 6:
        return "medium"
    if weakest >= 3:
        return "low"
    return "very low"


def predict(matches: list[dict], ratings: dict, model_meta: dict) -> tuple[dict, dict]:
    """Produce ``pair_key -> model prediction`` for every pick'em card."""
    from .lines import pair_key

    team_meta = model_meta.get("teams", {})
    h2h = model_meta.get("h2h", {})
    out: dict[str, dict] = {}
    unrateable = []
    for match in matches:
        teams = match.get("teams") or []
        if len(teams) < 2:
            continue
        ca, cb = canon_team(teams[0]), canon_team(teams[1])
        ra, rb = ratings.get(ca), ratings.get(cb)
        if ra is None or rb is None:
            missing = [t for t, r in ((teams[0], ra), (teams[1], rb)) if r is None]
            unrateable.append({
                "teams": teams,
                "fixture_id": match.get("fixture_id"),
                "unrated_teams": missing,
                "reason": ("no completed series with a verifiable scoreline for "
                           + " / ".join(missing)
                           + " on the Hotspawn league pages that cover this fixture"),
            })
            continue
        meta_a, meta_b = team_meta.get(ca, {}), team_meta.get(cb, {})
        direct = max(h2h.get(f"{ca}|{cb}", 0), h2h.get(f"{cb}|{ca}", 0))
        p = series_prob(ra, rb)
        evidence = list(dict.fromkeys((meta_a.get("evidence", [])[:3]
                                       + meta_b.get("evidence", [])[:3])))
        out[pair_key(teams[0], teams[1])] = {
            "prob_home": round(p, 4),
            "prob_away": round(1 - p, 4),
            "rating_home": ra,
            "rating_away": rb,
            "rating_diff": round(ra - rb, 1),
            "games_home": meta_a.get("games", 0),
            "games_away": meta_b.get("games", 0),
            "win_rate_home": meta_a.get("win_rate"),
            "win_rate_away": meta_b.get("win_rate"),
            "head_to_head_series": direct,
            "confidence": confidence(meta_a.get("games", 0), meta_b.get("games", 0), direct),
            "method": "series-level Elo over verified Hotspawn scorelines (methodology page)",
            "evidence_urls": evidence[:MAX_EVIDENCE],
            "league_evidence": sorted(set(meta_a.get("leagues", [])) | set(meta_b.get("leagues", []))),
        }
    return out, {"unrateable": unrateable, "unrateable_count": len(unrateable)}
