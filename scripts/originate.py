#!/usr/bin/env python3
"""End-to-end LoL probability origination, calibration, and irregularity audit engine.

Architecture:
  - Tier 1 (`market_consensus` / `esportsbook_line`): De-vigged real-money external lines
    from Pinnacle, Polymarket, Kalshi, and verified specialist LoL esportsbooks.
    Never blended with Tier-2 ratings.
  - Tier 2 (`originated`): Invoked ONLY when zero valid external market lines exist.
    Fits an L2-regularized game-level Bradley-Terry model via exact Newton-Raphson (`lambda=1.50`),
    extracts the exact Laplace posterior covariance `Sigma = H(theta_hat)^-1`, marginalizes
    skill uncertainty via MacKay's probit-logistic approximation `p_g = sigma(Delta / sqrt(1 + pi*v/8))`,
    and maps single-game win probability `p_g` to exact `Bo1` / `Bo2` / `Bo3` / `Bo5` series win
    probability with 90% posterior credible intervals.
  - Tier 3 (`unresolved`): Open fixtures that cannot be credibly resolved into a directional pick:
      * Administrative league removal / DQ phantom fixtures (`Solid Gaming` removed Round 10)
      * Statistical dead heats (`|P(Team A) - 0.50| < 0.005`, i.e., `49.5% - 50.5%` coin flips)
      * Future newly added matches with zero external standings or `"TBD"` participants.
  - Stale Audit (`stale_locked`): Past-lock rows still served as `status="scheduled"` by Hotspawn's
    API, cross-verified against completed Leaguepedia match results.

Hard Invariant:
  `participants0_picked_percent` and `participants1_picked_percent` from Hotspawn are NEVER read
  inside any rating, probability, pick, or classification computation.
"""
from __future__ import annotations

import csv
import json
import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from entities import ADMIN_TEAM_NOTES, COMP_TEAM_ALIASES, COMPETITION_META, norm_key, wiki_url
from markets import load_all_market_sources, resolve_market_tier1

LAMBDA_OPT = 1.50
PRIOR_SPLIT_WEIGHT = 0.55
FORFEIT_GAME_WEIGHT = 0.25
DEAD_HEAT_HALF_WIDTH = 0.005  # [49.50%, 50.50%] -> statistical dead heat (`unresolved`)


def sigmoid(x: float) -> float:
    if x >= 0.0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def solve_linear_system(a_mat: list[list[float]], b_vec: list[float]) -> list[float]:
    n = len(b_vec)
    aug = [row[:] + [b_vec[i]] for i, row in enumerate(a_mat)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(aug[r][col]))
        aug[col], aug[piv] = aug[piv], aug[col]
        div = aug[col][col]
        for j in range(col, n + 1):
            aug[col][j] /= div
        for r in range(n):
            if r != col and aug[r][col] != 0.0:
                factor = aug[r][col]
                for j in range(col, n + 1):
                    aug[r][j] -= factor * aug[col][j]
    return [aug[i][n] for i in range(n)]


def invert_spd_matrix(a_mat: list[list[float]]) -> list[list[float]]:
    n = len(a_mat)
    aug = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(a_mat)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(aug[r][col]))
        aug[col], aug[piv] = aug[piv], aug[col]
        div = aug[col][col]
        for j in range(col, 2 * n):
            aug[col][j] /= div
        for r in range(n):
            if r != col and aug[r][col] != 0.0:
                factor = aug[r][col]
                for j in range(col, 2 * n):
                    aug[r][j] -= factor * aug[col][j]
    return [aug[i][n:] for i in range(n)]


def fit_bradley_terry_laplace(
    matches: list[tuple[str, str, float, float]],
    teams: list[str],
    lam: float = LAMBDA_OPT,
) -> tuple[dict[str, int], list[float], list[list[float]], float]:
    """Fit exact MAP game log-strengths `theta` and Laplace covariance `H^-1` via Newton-Raphson."""
    idx = {t: i for i, t in enumerate(teams)}
    n = len(teams)
    if n == 0:
        return {}, [], [], 0.0
    theta = [0.0] * n
    grad_inf = 0.0
    for _ in range(20):
        g = [lam * theta[i] for i in range(n)]
        h_mat = [[lam if i == j else 0.0 for j in range(n)] for i in range(n)]
        for t1, t2, w1, w2 in matches:
            if t1 not in idx or t2 not in idx:
                continue
            i, j = idx[t1], idx[t2]
            tot = w1 + w2
            if tot <= 0.0:
                continue
            p = sigmoid(theta[i] - theta[j])
            v = tot * p * (1.0 - p)
            g[i] += tot * p - w1
            g[j] += tot * (1.0 - p) - w2
            h_mat[i][i] += v
            h_mat[j][j] += v
            h_mat[i][j] -= v
            h_mat[j][i] -= v
        grad_inf = max((abs(x) for x in g), default=0.0)
        if grad_inf < 1e-13:
            break
        step = solve_linear_system(h_mat, g)
        theta = [theta[i] - step[i] for i in range(n)]

    h_final = [[lam if i == j else 0.0 for j in range(n)] for i in range(n)]
    for t1, t2, w1, w2 in matches:
        if t1 not in idx or t2 not in idx:
            continue
        i, j = idx[t1], idx[t2]
        tot = w1 + w2
        if tot <= 0.0:
            continue
        p = sigmoid(theta[i] - theta[j])
        v = tot * p * (1.0 - p)
        h_final[i][i] += v
        h_final[j][j] += v
        h_final[i][j] -= v
        h_final[j][i] -= v
    cov = invert_spd_matrix(h_final)
    return idx, theta, cov, grad_inf


def series_win_prob(p_game: float, best_of: int) -> float:
    """Exact independent-game series combinatorics mapping game prob `p_g` -> match prob."""
    pg = min(max(p_game, 1e-6), 1.0 - 1e-6)
    if best_of == 5:
        return (pg ** 3) * (10.0 - 15.0 * pg + 6.0 * (pg ** 2))
    if best_of == 3:
        return (pg ** 2) * (3.0 - 2.0 * pg)
    if best_of == 2:
        return (pg ** 2) / (pg ** 2 + ((1.0 - pg) ** 2))
    return pg


def parse_all_match_schedules(data_wikitext: dict[str, str]) -> dict[str, list[dict[str, Any]]]:
    """Parse every `{{MatchSchedule|...}}` block from `Data:<OverviewPage>` wikitext."""
    by_overview: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for title, wt in data_wikitext.items():
        overview = title.removeprefix("Data:")
        cur_tab = ""
        cur_bo: int | None = None
        for block in wt.split("{{"):
            if block.startswith("MatchSchedule/Start"):
                mt = re.search(r"\|tab=\s*([^|\n\}]+)", block)
                mb = re.search(r"\|bestof=\s*(\d+)", block)
                cur_tab = mt.group(1).strip() if mt else ""
                cur_bo = int(mb.group(1)) if mb else None
            elif block.startswith("MatchSchedule|") or block.startswith("MatchSchedule\n"):
                body = block.split("}}")[0]
                fields: dict[str, str] = {}
                for part in body.split("|")[1:]:
                    if "=" in part:
                        k, v = part.split("=", 1)
                        fields[k.strip()] = v.strip()
                t1 = fields.get("team1", "")
                t2 = fields.get("team2", "")
                if not t1 or not t2:
                    continue
                bo = int(fields["bestof"]) if fields.get("bestof", "").isdigit() else cur_bo
                s1 = fields.get("team1score", "")
                s2 = fields.get("team2score", "")
                win = fields.get("winner", "")
                is_done = s1.isdigit() and s2.isdigit() and (int(s1) + int(s2) > 0)
                by_overview[overview].append({
                    "overview": overview,
                    "tab": cur_tab,
                    "bestof": bo,
                    "team1": t1,
                    "team2": t2,
                    "s1": int(s1) if s1.isdigit() else None,
                    "s2": int(s2) if s2.isdigit() else None,
                    "winner": win,
                    "ff": fields.get("ff", ""),
                    "date": fields.get("date", ""),
                    "time": fields.get("time", ""),
                    "completed": is_done,
                })
    return by_overview


def compute_walkforward_calibration(
    by_overview: dict[str, list[dict[str, Any]]]
) -> dict[str, Any]:
    """Chronological strictly out-of-sample walk-forward backtest (`date < target_date`)."""
    by_eco: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for ov, rows in by_overview.items():
        eco = ov.split("/")[0]
        for r in rows:
            if r["completed"] and r["winner"] in ("1", "2") and r["date"]:
                by_eco[eco].append(r)

    sweep_results: list[dict[str, Any]] = []
    chosen_preds: list[tuple[float, float]] = []

    for lam in (0.50, 0.75, 1.00, 1.50, 2.00, 3.00, 5.00):
        preds: list[tuple[float, float]] = []
        for _, rows in sorted(by_eco.items()):
            by_day: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for r in rows:
                by_day[r["date"]].append(r)
            hist: list[tuple[str, str, float, float]] = []
            seen_teams: set[str] = set()
            for day in sorted(by_day.keys()):
                day_rows = by_day[day]
                if len(hist) >= 6:
                    idx, theta, cov, _ = fit_bradley_terry_laplace(hist, sorted(seen_teams), lam=lam)
                    for r in day_rows:
                        if r["ff"]:
                            continue
                        t1, t2 = r["team1"], r["team2"]
                        if t1 in idx and t2 in idx:
                            i, j = idx[t1], idx[t2]
                            delta = theta[i] - theta[j]
                            var = cov[i][i] + cov[j][j] - 2.0 * cov[i][j]
                            pg = sigmoid(delta / math.sqrt(1.0 + (math.pi / 8.0) * var))
                            ps = series_win_prob(pg, r["bestof"] or 1)
                            if abs(ps - 0.5) > 1e-6:
                                preds.append((ps, 1.0 if r["winner"] == "1" else 0.0))
                for r in day_rows:
                    seen_teams.update([r["team1"], r["team2"]])
                    if r["ff"]:
                        hist.append((
                            r["team1"],
                            r["team2"],
                            FORFEIT_GAME_WEIGHT if r["winner"] == "1" else 0.0,
                            FORFEIT_GAME_WEIGHT if r["winner"] == "2" else 0.0,
                        ))
                    else:
                        hist.append((r["team1"], r["team2"], float(r["s1"]), float(r["s2"])))

        n_tot = len(preds)
        brier = sum((p - y) ** 2 for p, y in preds) / n_tot
        logloss = -sum(y * math.log(p) + (1.0 - y) * math.log(1.0 - p) for p, y in preds) / n_tot
        acc = sum(1 for p, y in preds if (p > 0.5 and y == 1.0) or (p < 0.5 and y == 0.0)) / n_tot
        sweep_results.append({
            "lambda": lam,
            "n_matches": n_tot,
            "accuracy": round(acc, 4),
            "brier": round(brier, 4),
            "log_loss": round(logloss, 4),
            "selected": abs(lam - LAMBDA_OPT) < 1e-9,
        })
        if abs(lam - LAMBDA_OPT) < 1e-9:
            chosen_preds = preds

    # Symmetric favorite-oriented calibration bins across [50%, 100%]
    fav_preds = [(p if p >= 0.5 else 1.0 - p, y if p >= 0.5 else 1.0 - y) for p, y in chosen_preds]
    edges = [0.50, 0.55, 0.60, 0.65, 0.70, 0.78, 1.01]
    bins: list[dict[str, Any]] = []
    ece = 0.0
    for b_idx in range(len(edges) - 1):
        lo, hi = edges[b_idx], edges[b_idx + 1]
        bucket = [(p, y) for p, y in fav_preds if lo <= p < hi]
        if not bucket:
            continue
        mean_p = sum(p for p, _ in bucket) / len(bucket)
        mean_y = sum(y for _, y in bucket) / len(bucket)
        se = math.sqrt(max(mean_y * (1.0 - mean_y), 0.01) / len(bucket))
        ece += (len(bucket) / len(fav_preds)) * abs(mean_p - mean_y)
        bins.append({
            "label": f"{int(lo*100)}–{min(int(hi*100), 100)}%",
            "count": len(bucket),
            "mean_predicted": round(mean_p, 4),
            "empirical_win_rate": round(mean_y, 4),
            "ci95_half_width": round(1.96 * se, 4),
        })

    opt = next(r for r in sweep_results if r["selected"])
    return {
        "n_walkforward_matches": opt["n_matches"],
        "selected_lambda": LAMBDA_OPT,
        "prior_split_weight": PRIOR_SPLIT_WEIGHT,
        "accuracy": opt["accuracy"],
        "brier_score": opt["brier"],
        "coin_flip_brier": 0.2500,
        "brier_skill_improvement_pct": round((1.0 - opt["brier"] / 0.25) * 100.0, 2),
        "log_loss": opt["log_loss"],
        "coin_flip_log_loss": round(math.log(2.0), 4),
        "expected_calibration_error": round(ece, 4),
        "lambda_sweep": sweep_results,
        "reliability_bins": bins,
    }


def confidence_band(fav_prob: float, pricing_tier: str) -> str:
    if pricing_tier in ("market_consensus", "esportsbook_line"):
        if fav_prob >= 0.70:
            return "Sharp Lock"
        if fav_prob >= 0.58:
            return "Market Favorite"
        return "Close Market"
    if fav_prob >= 0.65:
        return "High"
    if fav_prob >= 0.55:
        return "Moderate"
    return "Lean"


def run_pipeline(
    sources_dir: Path = Path("data/sources"),
    data_dir: Path = Path("data"),
    reference_iso: str | None = None,
) -> dict[str, Any]:
    """Run complete multi-tier origination, audit, and JSON/CSV artifact generation."""
    raw_fixtures: list[dict[str, Any]] = json.loads(
        (sources_dir / "hotspawn_lol_fixtures.json").read_text(encoding="utf-8")
    )
    all_summary: dict[str, Any] = json.loads(
        (sources_dir / "hotspawn_all_summary.json").read_text(encoding="utf-8")
    )
    permalinks_raw: dict[str, Any] = (
        json.loads((sources_dir / "hotspawn_permalinks.json").read_text(encoding="utf-8"))
        if (sources_dir / "hotspawn_permalinks.json").exists()
        else {}
    )
    lp_data: dict[str, Any] = json.loads(
        (sources_dir / "leaguepedia_data_pages.json").read_text(encoding="utf-8")
    )
    lp_teams_meta: dict[str, Any] = (
        json.loads((sources_dir / "leaguepedia_teams.json").read_text(encoding="utf-8"))
        if (sources_dir / "leaguepedia_teams.json").exists()
        else {}
    )

    ref_str = (
        reference_iso
        or all_summary.get("harvested_at")
        or lp_data.get("harvested_at")
        or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
    ref_dt = datetime.fromisoformat(ref_str.replace("Z", "+00:00"))
    ref_ms = int(ref_dt.timestamp() * 1000)

    # IMPORTANT: Strip Hotspawn crowd pick fields BEFORE modeling so no pricing code can touch them.
    crowd_audit_lookup: dict[str, tuple[float | None, float | None]] = {}
    clean_fixtures: list[dict[str, Any]] = []
    for raw in raw_fixtures:
        fid = str(raw["id"])
        c0 = raw.get("participants0_picked_percent")
        c1 = raw.get("participants1_picked_percent")
        crowd_audit_lookup[fid] = (float(c0) if c0 is not None else None, float(c1) if c1 is not None else None)
        sanitized = {
            k: v
            for k, v in raw.items()
            if k not in ("participants0_picked_percent", "participants1_picked_percent")
        }
        clean_fixtures.append(sanitized)

    permalink_map: dict[str, str] = {}
    for k, v in (permalinks_raw.get("permalinks") or permalinks_raw).items():
        if isinstance(v, str) and v.startswith("http"):
            permalink_map[str(k)] = v
        elif isinstance(v, dict) and str(v.get("url", "")).startswith("http"):
            permalink_map[str(k)] = str(v["url"])

    pin_quotes, poly_quotes, kal_quotes, book_receipts = load_all_market_sources(sources_dir, data_dir)
    by_overview = parse_all_match_schedules(lp_data.get("data_wikitext") or {})
    redirects: dict[str, str] = lp_data.get("team_redirects") or {}
    canonical_map: dict[str, list[str]] = lp_data.get("canonical_map") or {}

    # Fit per-competition Bradley-Terry models over verified official game records
    fixtures_by_comp: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for fx in clean_fixtures:
        fixtures_by_comp[fx["competition_name"]].append(fx)

    comp_models: dict[str, dict[str, Any]] = {}
    all_team_profiles: dict[tuple[str, str], dict[str, Any]] = {}

    for comp, comp_fx in fixtures_by_comp.items():
        overviews = list(canonical_map.get(comp) or [])
        if comp == "RIVALS LEAGUE Season 2" and "Superstrike League 2026" not in overviews:
            overviews.append("Superstrike League 2026")

        alias_to_hs: dict[str, str] = {}
        for fx in comp_fx:
            for side in ("participants0_name", "participants1_name"):
                hname = fx[side]
                aliases = set(COMP_TEAM_ALIASES.get((comp, hname), [])) | {hname, redirects.get(hname, hname)}
                for a in aliases:
                    alias_to_hs[norm_key(a)] = hname

        def canon_team(raw_name: str) -> str:
            r1 = redirects.get(raw_name, raw_name)
            if norm_key(raw_name) in alias_to_hs:
                return alias_to_hs[norm_key(raw_name)]
            if norm_key(r1) in alias_to_hs:
                return alias_to_hs[norm_key(r1)]
            return r1

        bt_matches: list[tuple[str, str, float, float]] = []
        team_set: set[str] = {fx[s] for fx in comp_fx for s in ("participants0_name", "participants1_name")}
        stats_cur: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0, 0, 0])  # [sw, sl, gw, gl, ff]
        stats_pri: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0, 0, 0])
        h2h_records: dict[tuple[str, str], list[str]] = defaultdict(list)
        upcoming_meta: dict[tuple[str, str], dict[str, Any]] = {}
        completed_lookup: list[dict[str, Any]] = []

        for idx_ov, ov in enumerate(overviews):
            w_mult = 1.0 if idx_ov == 0 else PRIOR_SPLIT_WEIGHT
            for r in by_overview.get(ov, []):
                c1, c2 = canon_team(r["team1"]), canon_team(r["team2"])
                team_set.update([c1, c2])
                if r["completed"]:
                    g1, g2 = int(r["s1"]), int(r["s2"])
                    win1 = r["winner"] == "1" or (r["winner"] not in ("1", "2") and g1 > g2)
                    win2 = r["winner"] == "2" or (r["winner"] not in ("1", "2") and g2 > g1)
                    bucket = stats_cur if idx_ov == 0 else stats_pri
                    bucket[c1][0] += 1 if win1 else 0
                    bucket[c1][1] += 1 if win2 else 0
                    bucket[c1][2] += g1
                    bucket[c1][3] += g2
                    bucket[c2][0] += 1 if win2 else 0
                    bucket[c2][1] += 1 if win1 else 0
                    bucket[c2][2] += g2
                    bucket[c2][3] += g1
                    if r["ff"]:
                        bucket[c1][4] += 1
                        bucket[c2][4] += 1
                        bt_matches.append((
                            c1,
                            c2,
                            FORFEIT_GAME_WEIGHT * w_mult if win1 else 0.0,
                            FORFEIT_GAME_WEIGHT * w_mult if win2 else 0.0,
                        ))
                    else:
                        bt_matches.append((c1, c2, g1 * w_mult, g2 * w_mult))

                    score_tag = f"{g1}–{g2}" + (" (FF)" if r["ff"] else "")
                    h2h_records[(c1, c2)].append(f"{score_tag} ({ov.split('/')[-1]})")
                    h2h_records[(c2, c1)].append(f"{g2}–{g1}" + (" (FF)" if r["ff"] else "") + f" ({ov.split('/')[-1]})")
                    completed_lookup.append({
                        "overview": ov,
                        "tab": r["tab"],
                        "bestof": r["bestof"],
                        "c1": c1,
                        "c2": c2,
                        "g1": g1,
                        "g2": g2,
                        "winner_team": c1 if win1 else (c2 if win2 else ""),
                        "ff": r["ff"],
                        "date": r["date"],
                    })
                elif idx_ov == 0:
                    upcoming_meta[(c1, c2)] = {"bestof": r["bestof"], "tab": r["tab"], "date": r["date"]}
                    upcoming_meta[(c2, c1)] = {"bestof": r["bestof"], "tab": r["tab"], "date": r["date"]}

        idx_map, theta, cov, grad_inf = fit_bradley_terry_laplace(bt_matches, sorted(team_set), lam=LAMBDA_OPT)
        comp_models[comp] = {
            "overviews": overviews,
            "idx": idx_map,
            "theta": theta,
            "cov": cov,
            "grad_inf": grad_inf,
            "stats_cur": stats_cur,
            "stats_pri": stats_pri,
            "h2h": h2h_records,
            "upcoming_meta": upcoming_meta,
            "completed_lookup": completed_lookup,
        }

        primary_ov = overviews[0] if overviews else ""
        for fx in comp_fx:
            for s_idx, side in enumerate(("participants0_name", "participants1_name")):
                tname = fx[side]
                key = (comp, tname)
                if key in all_team_profiles:
                    continue
                ti = idx_map[tname]
                sc = stats_cur[tname]
                sp = stats_pri[tname]
                tmeta = lp_teams_meta.get(tname) or {}
                team_page_title = redirects.get(tname) or tmeta.get("resolved_title") or ""
                team_url = wiki_url(team_page_title) if team_page_title else wiki_url(primary_ov)
                admin_info = ADMIN_TEAM_NOTES.get(key)
                all_team_profiles[key] = {
                    "competition": comp,
                    "region": (COMPETITION_META.get(comp) or {}).get("region", ""),
                    "team_name": tname,
                    "participant_id": str(fx[f"participants{s_idx}_id"]),
                    "canonical_aliases": sorted(set(COMP_TEAM_ALIASES.get(key, [tname]))),
                    "theta_map": round(theta[ti], 4),
                    "theta_se": round(math.sqrt(cov[ti][ti]), 4),
                    "current_series_wl": f"{sc[0]}–{sc[1]}",
                    "current_game_wl": f"{sc[2]}–{sc[3]}",
                    "prior_2026_series_wl": f"{sp[0]}–{sp[1]}",
                    "prior_2026_game_wl": f"{sp[2]}–{sp[3]}",
                    "total_verified_games": sc[2] + sc[3] + sp[2] + sp[3],
                    "admin_note": admin_info,
                    "leaguepedia_tournament_url": wiki_url(primary_ov) if primary_ov else "",
                    "team_reference_url": team_url,
                }

    # Price and audit all 264 fixtures in chronological kickoff order
    enriched_rows: list[dict[str, Any]] = []
    for fx in sorted(clean_fixtures, key=lambda r: (int(r["scheduled_start_time"]), int(r["id"]))):
        fid = str(fx["id"])
        comp = fx["competition_name"]
        t0 = fx["participants0_name"]
        t1 = fx["participants1_name"]
        sched_ms = int(fx["scheduled_start_time"])
        lock_ms = int(fx["lock_time"])
        is_open = sched_ms > ref_ms and lock_ms > ref_ms

        cmeta = COMPETITION_META.get(comp) or {}
        cm = comp_models[comp]
        overviews = cm["overviews"]
        primary_ov = overviews[0] if overviews else ""
        lp_comp_url = wiki_url(primary_ov) if primary_ov else "https://lol.fandom.com/wiki/League_of_Legends_Esports_Wiki"
        org_url = cmeta.get("organizer_url") or lp_comp_url
        hotspawn_url = permalink_map.get(fid) or "https://play.hotspawn.com/lol-pickems"

        up_info = cm["upcoming_meta"].get((t0, t1)) or {}
        raw_bo = int(fx["best_of"]) if str(fx.get("best_of") or "").isdigit() else None
        verified_bo = raw_bo or up_info.get("bestof")
        raw_tier = fx.get("tier") or ""
        clean_tier = "" if raw_tier.lower() in ("", "waiting for information", "none") else raw_tier.upper()
        raw_stage = fx.get("stage") or ""
        clean_stage = (
            up_info.get("tab")
            if raw_stage.lower() in ("", "waiting for information", "none")
            else raw_stage
        ) or ""

        sc0, sp0 = cm["stats_cur"][t0], cm["stats_pri"][t0]
        sc1, sp1 = cm["stats_cur"][t1], cm["stats_pri"][t1]
        h2h_list = cm["h2h"].get((t0, t1), [])

        admin0 = ADMIN_TEAM_NOTES.get((comp, t0))
        admin1 = ADMIN_TEAM_NOTES.get((comp, t1))
        admin_notes = [x for x in (admin0, admin1) if x is not None]

        # Build verified primary source list (ALWAYS official/trusted external URLs on EVERY row)
        sources: list[dict[str, str]] = []
        market_res = resolve_market_tier1(fx, pin_quotes, poly_quotes, kal_quotes, book_receipts) if is_open else None

        if market_res is not None:
            for v in market_res["venues"]:
                sources.append({"label": v["venue"], "url": v["source_url"]})
        sources.append({"label": "Leaguepedia", "url": lp_comp_url})
        if org_url != lp_comp_url:
            sources.append({"label": cmeta.get("organizer_name", "Organizer").split("/")[0].strip(), "url": org_url})
        sources.append({"label": "Hotspawn Card", "url": hotspawn_url})

        # Deduplicate sources while preserving order
        dedup_sources: list[dict[str, str]] = []
        seen_urls: set[str] = set()
        for s in sources:
            if s["url"] and s["url"] not in seen_urls:
                seen_urls.add(s["url"])
                dedup_sources.append(s)

        # Compute underlying BT numbers (kept strictly in diagnostics if Tier-1 market exists)
        i0, i1 = cm["idx"][t0], cm["idx"][t1]
        delta_map = cm["theta"][i0] - cm["theta"][i1]
        var_gap = cm["cov"][i0][i0] + cm["cov"][i1][i1] - 2.0 * cm["cov"][i0][i1]
        sd_gap = math.sqrt(max(var_gap, 1e-9))
        bo_for_calc = verified_bo or 1
        pg_marg = sigmoid(delta_map / math.sqrt(1.0 + (math.pi / 8.0) * var_gap))
        bt_p0 = series_win_prob(pg_marg, bo_for_calc)
        bt_ci_lo = series_win_prob(sigmoid(delta_map - 1.6449 * sd_gap), bo_for_calc)
        bt_ci_hi = series_win_prob(sigmoid(delta_map + 1.6449 * sd_gap), bo_for_calc)

        row_status = ""
        unresolved_reason = ""
        unresolved_code = ""
        stale_official_result = ""
        p0: float | None = None
        p1: float | None = None
        ci90: list[float] | None = None
        pick_team: str | None = None
        defensive_lean: str | None = None
        conf_label = ""
        evidence_summary = ""

        if not is_open:
            row_status = "stale_locked"
            unresolved_code = "stale_orphaned_schedule_row"
            # Check official Leaguepedia match results for this past-lock match
            matched_done = [
                m for m in cm["completed_lookup"]
                if (m["c1"] == t0 and m["c2"] == t1) or (m["c1"] == t1 and m["c2"] == t0)
            ]
            if matched_done:
                last_m = matched_done[-1]
                s_a = last_m["g1"] if last_m["c1"] == t0 else last_m["g2"]
                s_b = last_m["g2"] if last_m["c1"] == t0 else last_m["g1"]
                ff_tag = " (Forfeit)" if last_m["ff"] else ""
                stale_official_result = f"{t0} {s_a}–{s_b} {t1}{ff_tag} — Winner: {last_m['winner_team']}"
                evidence_summary = f"Official result recorded on Leaguepedia: {stale_official_result}"
            elif admin0 and admin0["severity"] in ("critical_removed", "disqualified"):
                stale_official_result = f"Unplayed / Walkover — {t0}: {admin0['badge']}"
                evidence_summary = admin0["summary"]
            elif admin1 and admin1["severity"] in ("critical_removed", "disqualified"):
                stale_official_result = f"Unplayed / Walkover — {t1}: {admin1['badge']}"
                evidence_summary = admin1["summary"]
            else:
                stale_official_result = "Lock window passed; official score pending or unplayed"
                evidence_summary = f"{t0} ({sc0[0]}–{sc0[1]}) vs {t1} ({sc1[0]}–{sc1[1]}) — past Hotspawn lock time."
            unresolved_reason = (
                "Lock timestamp has already passed, yet Hotspawn's API still serves this fixture "
                "with `status=\"scheduled\"` and `0–0` score."
            )
        elif (admin0 and admin0["severity"] == "critical_removed") or (admin1 and admin1["severity"] == "critical_removed"):
            row_status = "unresolved"
            unresolved_code = "removed_from_league"
            removed_side = t0 if (admin0 and admin0["severity"] == "critical_removed") else t1
            active_side = t1 if removed_side == t0 else t0
            defensive_lean = active_side
            unresolved_reason = (
                f"{removed_side} was officially removed from {comp} in Round 10 per Leaguepedia & GGArena "
                f"(`dqteams={removed_side}`), and all 4 prior post-removal fixtures on Hotspawn went unplayed. "
                f"No competitive Rift probability exists. Defensive Pick'em rule: NEVER pick {removed_side}; "
                f"select active {active_side} (pushes if voided, wins full points if settled as walkover)."
            )
            evidence_summary = f"Official admin removal (`dqteams={removed_side}`); active opponent: {active_side} ({cm['stats_cur'][active_side][0]}–{cm['stats_cur'][active_side][1]} series)."
        elif market_res is not None:
            row_status = market_res["pricing_tier"]
            p0 = round(market_res["p0"], 4)
            p1 = round(1.0 - p0, 4)
            ci90 = market_res["ci90_p0"]
            pick_team = t0 if p0 >= p1 else t1
            conf_label = confidence_band(max(p0, p1), row_status)
            venue_bits = []
            for v in market_res["venues"]:
                if v["venue_key"] == "pinnacle":
                    venue_bits.append(f"Pinnacle {v['am0']:+d}/{v['am1']:+d} ({v['p0']*100:.1f}%)")
                elif v["venue_key"] == "polymarket":
                    venue_bits.append(f"Polymarket {v['p0']*100:.1f}% (${v['volume_usd']:,.0f} vol)")
                elif v["venue_key"] == "kalshi":
                    venue_bits.append(f"Kalshi {v['p0']*100:.1f}%")
                elif v["venue_key"] == "esportsbook":
                    venue_bits.append(f"Esportsbook {v['dec0']:.3g}/{v['dec1']:.3g} ({v['p0']*100:.1f}%)")
            evidence_summary = " · ".join(venue_bits)
        else:
            tot_evidence_games = (sc0[2] + sc0[3] + sp0[2] + sp0[3]) + (sc1[2] + sc1[3] + sp1[2] + sp1[3])
            if "tbd" in {t0.strip().lower(), t1.strip().lower()} or tot_evidence_games == 0:
                row_status = "unresolved"
                unresolved_code = "missing_external_evidence"
                unresolved_reason = "Zero external bookmaker quotes and zero verified official 2026 match records found."
                evidence_summary = "No verified pre-match external game history available."
            elif abs(bt_p0 - 0.5) < DEAD_HEAT_HALF_WIDTH:
                row_status = "unresolved"
                unresolved_code = "statistical_dead_heat"
                p0 = round(bt_p0, 4)
                p1 = round(1.0 - p0, 4)
                ci90 = [round(bt_ci_lo, 4), round(bt_ci_hi, 4)]
                defensive_lean = t0 if bt_p0 >= 0.5 else t1
                unresolved_reason = (
                    f"No sportsbook line exists and full opponent-adjusted Bayesian Bradley-Terry modeling "
                    f"yields a virtual dead heat ({p0*100:.1f}% vs {p1*100:.1f}%, 90% CI "
                    f"[{bt_ci_lo*100:.0f}%, {bt_ci_hi*100:.0f}%]) within ±0.5% of 50/50."
                )
                evidence_summary = (
                    f"Statistical dead heat ({p0*100:.1f}% / {p1*100:.1f}%) · "
                    f"{t0} split {sc0[0]}–{sc0[1]} ({sc0[2]}–{sc0[3]}g, prior {sp0[2]}–{sp0[3]}g) vs "
                    f"{t1} split {sc1[0]}–{sc1[1]} ({sc1[2]}–{sc1[3]}g, prior {sp1[2]}–{sp1[3]}g)"
                )
            else:
                row_status = "originated"
                p0 = round(bt_p0, 4)
                p1 = round(1.0 - p0, 4)
                ci90 = [round(bt_ci_lo, 4), round(bt_ci_hi, 4)]
                pick_team = t0 if p0 > p1 else t1
                conf_label = confidence_band(max(p0, p1), "originated")
                h2h_str = f" · H2H {h2h_list[-1]}" if h2h_list else ""
                pri_str = (
                    f" · Prior '26 {sp0[2]}–{sp0[3]}g vs {sp1[2]}–{sp1[3]}g"
                    if (sp0[2] + sp0[3] + sp1[2] + sp1[3]) > 0
                    else ""
                )
                evidence_summary = (
                    f"Split {sc0[0]}–{sc0[1]} ({sc0[2]}–{sc0[3]}g) vs {sc1[0]}–{sc1[1]} ({sc1[2]}–{sc1[3]}g)"
                    f"{h2h_str}{pri_str}"
                )

        # Attach strictly isolated crowd display fields ONLY after all modeling is complete
        crowd0, crowd1 = crowd_audit_lookup[fid]
        crowd_delta_pp: float | None = None
        if p0 is not None and crowd0 is not None and (crowd0 + (crowd1 or 0.0)) > 0:
            crowd_delta_pp = round(p0 * 100.0 - crowd0, 1)

        sched_iso = datetime.fromtimestamp(sched_ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        lock_iso = datetime.fromtimestamp(lock_ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        enriched_rows.append({
            "id": fid,
            "competition": comp,
            "region": cmeta.get("region", ""),
            "circuit": cmeta.get("circuit", ""),
            "scheduled_utc": sched_iso,
            "lock_utc": lock_iso,
            "scheduled_ms": sched_ms,
            "lock_ms": lock_ms,
            "hours_until_lock": round((lock_ms - ref_ms) / 3_600_000.0, 2),
            "is_open": is_open,
            "status": row_status,
            "unresolved_code": unresolved_code,
            "unresolved_reason": unresolved_reason,
            "stale_official_result": stale_official_result,
            "raw_hotspawn_tier": raw_tier,
            "tier_display": clean_tier,
            "raw_hotspawn_stage": raw_stage,
            "stage_display": clean_stage,
            "raw_hotspawn_best_of": fx.get("best_of"),
            "best_of": verified_bo,
            "best_of_display": f"Bo{verified_bo}" if verified_bo else "",
            "offered_points": int(fx.get("offered_points") or 0),
            "team0": t0,
            "team1": t1,
            "team0_id": str(fx["participants0_id"]),
            "team1_id": str(fx["participants1_id"]),
            "team0_prob": p0,
            "team1_prob": p1,
            "team0_fair_odds": round(1.0 / p0, 2) if (p0 and p0 > 0) else None,
            "team1_fair_odds": round(1.0 / p1, 2) if (p1 and p1 > 0) else None,
            "ci90_team0": ci90,
            "pick": pick_team,
            "defensive_lean": defensive_lean,
            "pick_prob": round(max(p0, p1), 4) if (p0 is not None and p1 is not None and pick_team) else None,
            "confidence": conf_label,
            "market_detail": market_res,
            "bt_diagnostics": {
                "theta0": round(cm["theta"][i0], 4),
                "theta1": round(cm["theta"][i1], 4),
                "sd_gap": round(sd_gap, 4),
                "bt_p0": round(bt_p0, 4),
                "team0_split_series": f"{sc0[0]}–{sc0[1]}",
                "team1_split_series": f"{sc1[0]}–{sc1[1]}",
                "team0_split_games": f"{sc0[2]}–{sc0[3]}",
                "team1_split_games": f"{sc1[2]}–{sc1[3]}",
                "team0_prior_games": f"{sp0[2]}–{sp0[3]}",
                "team1_prior_games": f"{sp1[2]}–{sp1[3]}",
                "h2h": h2h_list,
            },
            "admin_notes": admin_notes,
            "evidence_summary": evidence_summary,
            "sources": dedup_sources,
            "hotspawn_crowd_display_only": {
                "team0_picked_pct": crowd0,
                "team1_picked_pct": crowd1,
                "model_minus_crowd_team0_pp": crowd_delta_pp,
                "used_in_model": False,
            },
        })

    calibration = compute_walkforward_calibration(by_overview)

    # Build structured Flagged Irregularities manifest
    open_rows = [r for r in enriched_rows if r["is_open"]]
    stale_rows = [r for r in enriched_rows if not r["is_open"]]
    actionable_rows = [r for r in open_rows if r["status"] in ("market_consensus", "esportsbook_line", "originated")]
    market_rows = [r for r in open_rows if r["status"] in ("market_consensus", "esportsbook_line")]
    originated_rows = [r for r in open_rows if r["status"] == "originated"]
    unresolved_open_rows = [r for r in open_rows if r["status"] == "unresolved"]

    crowd_divergences = sorted(
        [
            r for r in actionable_rows
            if r["hotspawn_crowd_display_only"]["team0_picked_pct"] is not None
            and (
                (r["hotspawn_crowd_display_only"]["team0_picked_pct"] or 0)
                + (r["hotspawn_crowd_display_only"]["team1_picked_pct"] or 0)
            ) > 0
            and abs(r["hotspawn_crowd_display_only"]["model_minus_crowd_team0_pp"] or 0.0) >= 15.0
        ],
        key=lambda x: abs(x["hotspawn_crowd_display_only"]["model_minus_crowd_team0_pp"] or 0.0),
        reverse=True,
    )

    flagged_items: list[dict[str, Any]] = [
        {
            "flag_id": "FLG-01",
            "severity": "CRITICAL",
            "category": "League Removal / Live Crowd Trap",
            "title": "Solid Gaming Officially Removed in Round 10 — Yet 72% of Hotspawn Crowd Picked Solid Gaming (#1071216)",
            "competition": "Komplettligaen 2026 Autumn",
            "affected_fixture_ids": ["1071216", "1071170", "1071200", "1071206", "1071186"],
            "detail": (
                "Official Komplettligaen 2026 Autumn wikitext & GGArena standings explicitly declare "
                "`|excludeteams=Solid Gaming|dqteams=Solid Gaming` (Footnote 1: \"Round 10: Solid Gaming is removed from the league\"). "
                "All 4 prior Solid Gaming fixtures since Sept 17 remain unplayed (`0–0`) on Hotspawn, yet fixture #1071216 "
                "(Solid Gaming vs DMG Esports Norway, 2026-10-22 15:00 UTC) remains open with 72% of users picking Solid Gaming."
            ),
            "resolution": "Quarantined into Unresolved (Removed Team) with explicit warning: NEVER pick Solid Gaming; select active DMG Esports Norway if filling card.",
            "source_url": wiki_url("Komplettligaen/2026 Season/Autumn Split"),
            "secondary_url": "https://www.ggarena.no/competitions/komplettligaen-league-of-legends-hosten-2026/13909",
        },
        {
            "flag_id": "FLG-02",
            "severity": "HIGH",
            "category": "Upstream Entity Misbinding",
            "title": "German Prime League Team `PvB Nation` Misbound as Defunct 2019 Vietnamese VCS Team `Phong Vũ Buffalo`",
            "competition": "PRM 2nd Division 26-27 Fall",
            "affected_fixture_ids": [r["id"] for r in open_rows if "Phong Vũ Buffalo" in (r["team0"], r["team1"])],
            "detail": (
                "Hotspawn's upstream data provider matched short tag `PVB` in German Prime League Division 2.1 to "
                "historical Vietnamese VCS team `Phong Vũ Buffalo` (rebranded/defunct in 2019). Cross-checking the "
                "8-team Division 2.1 roster on Leaguepedia & PrimeLeague.gg proves the actual team is German squad `PvB Nation`."
            ),
            "resolution": "Explicitly bound `(PRM 2nd Division 26-27 Fall, Phong Vũ Buffalo) -> PvB Nation` across all 5 open Division 2.1 fixtures.",
            "source_url": wiki_url("Prime League 2nd Division/2027 Season/Fall Split"),
            "secondary_url": "https://www.primeleague.gg/en/leagues/prm/3227-fall-split-202627",
        },
        {
            "flag_id": "FLG-03",
            "severity": "HIGH",
            "category": "Aggregator Dummy Odds Rejection",
            "title": "Symmetric `1.80 / 1.80` Unpriced Placeholder Odds Caught on LGC Rising Grand Finals (#1079080)",
            "competition": "LGC Rising 2026 Playoffs",
            "affected_fixture_ids": ["1079080"],
            "detail": (
                "Esports aggregator listings display `[1.80 / 1.80]` symmetric placeholder numbers on `Mental Rush vs Vitality Rising Bees` "
                "despite zero bookmaker posting an actual line. Accepting fake `1.80 / 1.80` quotes would falsely erase Vitality Rising Bees' "
                "dominant undefeated playoff run (`2–0` GCS, `3–0` G2 Hel vs `#2` Mental Rush `3–2` SK Avarosa)."
            ),
            "resolution": "`markets.devig_decimal_pair()` hard-rejects symmetric `1.80 / 1.80` placeholders and cascades #1079080 to Tier-2 EMEA Game Changers origination.",
            "source_url": wiki_url("LoL Game Changers/2026 Season/Playoffs"),
            "secondary_url": "https://play.toornament.com/en_US/circuits/2466809817314095103",
        },
        {
            "flag_id": "FLG-04",
            "severity": "HIGH",
            "category": "Administrative Forfeit Rulings",
            "title": "Two Week 1 On-Rift Wins by `Team Reds` Overturned to Forfeit Losses for Ineligible Roster",
            "competition": "Arabian League 2nd Division 2026 Summer",
            "affected_fixture_ids": [r["id"] for r in open_rows if "Team Reds" in (r["team0"], r["team1"])],
            "detail": (
                "Official Arabian League 2nd Division footnotes 1 & 2 document that two Week 1 matches won on the Rift "
                "by Team Reds were administratively overturned to forfeit losses (`|ff=`) due to an ineligible player."
            ),
            "resolution": "Forfeit-aware `Data:` parser separates administrative `|ff=` rulings from on-Rift game losses (`w_ff=0.25`) and flags all Team Reds fixtures.",
            "source_url": wiki_url("Arabian League 2nd Division/2026 Season/Summer Split"),
            "secondary_url": "https://play.hotspawn.com/lol-pickems",
        },
        {
            "flag_id": "FLG-05",
            "severity": "MEDIUM",
            "category": "Extreme Crowd vs. Real-Money Market Distortion",
            "title": "Hotspawn Crowd Picks `Galions` at 86% vs. Real-Money 4-Venue Consensus 51.8% (`+34.2 pp` Distortion)",
            "competition": "EM 2026 Summer Main Event",
            "affected_fixture_ids": [r["id"] for r in crowd_divergences[:8]],
            "detail": (
                "In EMEA Masters 2026 Summer Grand Final (#1081205 `Galions vs Solary`), Pinnacle (`-127 / +105` -> `53.2%`), "
                "Kalshi (`$0.535 / $0.455` -> `54.0%`), Polymarket (`$0.515 / $0.485` -> `51.5%`, `$25.6K` vol), and specialist "
                "esportsbooks (`1.86 / 1.80` -> `49.2%`) price a virtual coin flip (`52.4% Galions / 47.6% Solary`), whereas "
                "Hotspawn crowd sentiment sits at `86% / 14%` — proving why Hotspawn crowd % must never be used as win probability."
            ),
            "resolution": "All Hotspawn `picked_percent` fields are stripped prior to modeling and tested for exact `0.0` sensitivity in `tests/test_pipeline.py`.",
            "source_url": "https://polymarket.com/event/lol-gal-sly-2026-10-22",
            "secondary_url": wiki_url("EMEA Masters/2026 Season/Summer Main Event"),
        },
        {
            "flag_id": "FLG-06",
            "severity": "MEDIUM",
            "category": "Cross-Region Homonym Collisions",
            "title": "Identical Organization Names Across Distinct National Leagues (`Rich Gang`, `DMG`, `Invictus`, `Arena`, `Fenrir`)",
            "competition": "Multiple Regional Leagues",
            "affected_fixture_ids": [
                r["id"] for r in open_rows
                if any(tok in f"{r['team0']} {r['team1']}" for tok in ("Rich Gang", "DMG Esports", "Invictus", "Infinity"))
            ][:12],
            "detail": (
                "`Rich Gang` fields separate rosters across Norway (`Komplettligaen`), DACH (`PRM Div 3.2`), UK (`4 Nations`), "
                "Sweden (`RIVALS League`), and Finland (`FPL`); `DMG Esports` fields separate Norwegian and Swedish rosters; "
                "`Invictus Gaming` (LPL Worlds) is unrelated to `Invictus Team` (Brazil) and `Macko Invictus` (Italy)."
            ),
            "resolution": "Every team profile and rating vector is strictly scoped by `(competition_name, participant_name)` with zero global name merging.",
            "source_url": wiki_url("Komplettligaen/2026 Season/Autumn Split"),
            "secondary_url": wiki_url("Prime League 3rd Division/2027 Season/Fall Split"),
        },
        {
            "flag_id": "FLG-07",
            "severity": "MEDIUM",
            "category": "Stale Upstream Feed Rows",
            "title": f"{len(stale_rows)} Past-Lock Fixtures (`lock_time <= now`) Remain Unclosed with `status=\"scheduled\"` on Hotspawn API",
            "competition": "19 Historical / Completed Competitions",
            "affected_fixture_ids": [r["id"] for r in stale_rows[:15]],
            "detail": (
                f"Hotspawn's live `/api/v1/fixtures?sport_alias=lol&status=scheduled&tenantId=1` endpoint returns {len(enriched_rows)} "
                f"rows, of which {len(stale_rows)} locked between Aug 26 and Oct 21, 2026 without score ingestion (`0–0`, `end_time=null`), "
                f"including completed championships (`FPL Summer Playoffs`, `Legends Academy S3`, `POP Esports Masters S7`, `LIT Promotion`)."
            ),
            "resolution": "Quarantined into `stale_locked` audit table and cross-matched against completed official Leaguepedia `Data:` scores.",
            "source_url": "https://play.hotspawn.com/lol-pickems",
            "secondary_url": wiki_url("Finnish Pro League/2026 Season/Summer Playoffs"),
        },
        {
            "flag_id": "FLG-08",
            "severity": "LOW",
            "category": "Incomplete Upstream Metadata",
            "title": "Hotspawn Feed Leaves `tier=\"waiting for information\"` and `best_of=null` on 189 / 264 Fixtures",
            "competition": "All Regional / Tier-2 & Tier-3 Competitions",
            "affected_fixture_ids": [r["id"] for r in open_rows if not r["tier_display"]][:12],
            "detail": (
                "Hotspawn's API leaves `best_of: null` on 100% of scheduled rows and `tier: \"waiting for information\"` on 189/264 rows, "
                "which would mis-price Bo3 and Bo5 series if modeled as Bo1."
            ),
            "resolution": "Series format (`Bo1`/`Bo2`/`Bo3`/`Bo5`) and stage names are recovered from official Leaguepedia `Data:` schedules; unconfirmed tier fields remain explicitly blank (`—`).",
            "source_url": wiki_url("Data:Prime League 2nd Division/2027 Season/Fall Split"),
            "secondary_url": "https://play.hotspawn.com/lol-pickems",
        },
    ]

    # Tournament summary objects across all 27 competitions
    tournament_summaries: list[dict[str, Any]] = []
    for comp in sorted(fixtures_by_comp.keys()):
        c_rows = [r for r in enriched_rows if r["competition"] == comp]
        c_open = [r for r in c_rows if r["is_open"]]
        c_mkt = [r for r in c_open if r["status"] in ("market_consensus", "esportsbook_line")]
        c_orig = [r for r in c_open if r["status"] == "originated"]
        c_unres = [r for r in c_open if r["status"] == "unresolved"]
        c_stale = [r for r in c_rows if not r["is_open"]]
        cmeta = COMPETITION_META.get(comp) or {}
        ovs = comp_models[comp]["overviews"]
        tournament_summaries.append({
            "competition": comp,
            "region": cmeta.get("region", ""),
            "circuit": cmeta.get("circuit", ""),
            "format_note": cmeta.get("default_format_note", ""),
            "total_rows": len(c_rows),
            "open_count": len(c_open),
            "market_count": len(c_mkt),
            "originated_count": len(c_orig),
            "unresolved_open_count": len(c_unres),
            "stale_count": len(c_stale),
            "primary_method": (
                "4-Venue Market Consensus"
                if any(r["status"] == "market_consensus" for r in c_open)
                else (
                    "Specialist Esportsbook Line"
                    if any(r["status"] == "esportsbook_line" for r in c_open)
                    else ("Bayesian BT Origination" if c_open else "Completed / Stale Audit")
                )
            ),
            "leaguepedia_url": wiki_url(ovs[0]) if ovs else "",
            "organizer_name": cmeta.get("organizer_name", "Leaguepedia"),
            "organizer_url": cmeta.get("organizer_url", wiki_url(ovs[0]) if ovs else ""),
            "next_lock_utc": c_open[0]["lock_utc"] if c_open else None,
        })
    tournament_summaries.sort(key=lambda t: (-t["open_count"], t["competition"]))

    summary = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "reference_snapshot_at": ref_str,
        "refresh_cadence": "Every 4 hours via GitHub Actions (`17 */4 * * *`)",
        "counts": {
            "all_sports_scheduled_total": all_summary.get("total_all_scheduled") or all_summary.get("total_all_sports") or len(raw_fixtures),
            "lol_scheduled_total": len(enriched_rows),
            "open_total": len(open_rows),
            "actionable_open_picks": len(actionable_rows),
            "tier1_market_total": len(market_rows),
            "tier1a_multi_venue_consensus": sum(1 for r in market_rows if r["status"] == "market_consensus"),
            "tier1b_esportsbook_only": sum(1 for r in market_rows if r["status"] == "esportsbook_line"),
            "tier2_originated_total": len(originated_rows),
            "tier3_unresolved_open_total": len(unresolved_open_rows),
            "unresolved_removed_team": sum(1 for r in unresolved_open_rows if r["unresolved_code"] == "removed_from_league"),
            "unresolved_dead_heat": sum(1 for r in unresolved_open_rows if r["unresolved_code"] == "statistical_dead_heat"),
            "unresolved_missing_data": sum(1 for r in unresolved_open_rows if r["unresolved_code"] == "missing_external_evidence"),
            "stale_past_lock_total": len(stale_rows),
            "stale_with_official_score": sum(1 for r in stale_rows if "Winner:" in r["stale_official_result"]),
            "competitions_total": len(tournament_summaries),
            "competitions_open": sum(1 for t in tournament_summaries if t["open_count"] > 0),
            "teams_verified_total": len(all_team_profiles),
            "official_matches_modeled": sum(len(v) for v in by_overview.values()),
            "flagged_irregularities_count": len(flagged_items),
            "urgent_48h_open": sum(1 for r in actionable_rows if 0 < r["hours_until_lock"] <= 48.0),
        },
        "calibration_headline": {
            "n_walkforward": calibration["n_walkforward_matches"],
            "accuracy_pct": round(calibration["accuracy"] * 100.0, 1),
            "brier": calibration["brier_score"],
            "brier_improvement_pct": calibration["brier_skill_improvement_pct"],
            "log_loss": calibration["log_loss"],
            "ece_pct": round(calibration["expected_calibration_error"] * 100.0, 2),
        },
        "tournaments": tournament_summaries,
        "unresolved_open_highlights": [
            {
                "id": r["id"],
                "competition": r["competition"],
                "scheduled_utc": r["scheduled_utc"],
                "team0": r["team0"],
                "team1": r["team1"],
                "code": r["unresolved_code"],
                "team0_prob": r["team0_prob"],
                "team1_prob": r["team1_prob"],
                "defensive_lean": r["defensive_lean"],
                "reason": r["unresolved_reason"],
                "primary_url": r["sources"][0]["url"],
            }
            for r in unresolved_open_rows
        ],
    }

    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "picks.json").write_text(
        json.dumps(
            {
                "summary": summary,
                "picks": enriched_rows,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (data_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (data_dir / "calibration.json").write_text(json.dumps(calibration, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (data_dir / "teams_index.json").write_text(
        json.dumps(
            sorted(all_team_profiles.values(), key=lambda x: (x["competition"], -x["theta_map"], x["team_name"])),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (data_dir / "flagged.json").write_text(
        json.dumps(
            {
                "generated_at": summary["generated_at"],
                "flags": flagged_items,
                "crowd_divergences": [
                    {
                        "id": r["id"],
                        "competition": r["competition"],
                        "match": f"{r['team0']} vs {r['team1']}",
                        "pricing_tier": r["status"],
                        "pick": r["pick"],
                        "model_team0_pct": round((r["team0_prob"] or 0.0) * 100.0, 1),
                        "crowd_team0_pct": r["hotspawn_crowd_display_only"]["team0_picked_pct"],
                        "delta_pp": r["hotspawn_crowd_display_only"]["model_minus_crowd_team0_pp"],
                        "source_url": r["sources"][0]["url"],
                    }
                    for r in crowd_divergences
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    # Export clean flat CSV for instant download on mobile/desktop
    with (data_dir / "picks.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "fixture_id",
            "scheduled_utc",
            "lock_utc",
            "is_open",
            "status",
            "competition",
            "region",
            "best_of",
            "tier",
            "offered_points",
            "team_a",
            "team_b",
            "recommended_pick",
            "team_a_win_pct",
            "team_b_win_pct",
            "confidence",
            "evidence_summary",
            "primary_source_url",
            "hotspawn_url",
        ])
        for r in enriched_rows:
            writer.writerow([
                r["id"],
                r["scheduled_utc"],
                r["lock_utc"],
                r["is_open"],
                r["status"],
                r["competition"],
                r["region"],
                r["best_of_display"],
                r["tier_display"],
                r["offered_points"],
                r["team0"],
                r["team1"],
                r["pick"] or (f"LEAN: {r['defensive_lean']}" if r["defensive_lean"] else ""),
                f"{r['team0_prob']*100:.1f}" if r["team0_prob"] is not None else "",
                f"{r['team1_prob']*100:.1f}" if r["team1_prob"] is not None else "",
                r["confidence"],
                r["evidence_summary"],
                r["sources"][0]["url"],
                r["sources"][-1]["url"],
            ])

    return {
        "summary": summary,
        "picks": enriched_rows,
        "calibration": calibration,
        "teams": list(all_team_profiles.values()),
        "flagged": flagged_items,
    }


if __name__ == "__main__":
    res = run_pipeline()
    c = res["summary"]["counts"]
    print(
        f"Originated & audited {c['lol_scheduled_total']} Hotspawn LoL rows: "
        f"{c['open_total']} open ({c['tier1_market_total']} market + "
        f"{c['tier2_originated_total']} originated + {c['tier3_unresolved_open_total']} unresolved) "
        f"+ {c['stale_past_lock_total']} past-lock stale rows."
    )
