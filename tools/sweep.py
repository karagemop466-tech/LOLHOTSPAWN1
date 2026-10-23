"""Parameter-stability sweep for the published Elo model.

The site ships one fixed set of update sizes (ELO_K_OPENING, ELO_K_SERIES,
MOV_WEIGHT). This script re-runs the same walk-forward evaluation for a grid of
nearby settings and writes ``data/backtest_sweep.json`` so a reader can see how
much the choice actually matters instead of taking "we tuned it" on trust.

Nothing here feeds the published picks: it only reports what each setting would
have scored on the disjoint validation window (BACKTEST_SELECTION ..
BACKTEST_CUTOFF) and on the frozen test window (>= BACKTEST_CUTOFF).

Run:  python3 tools/sweep.py
"""
from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model  # noqa: E402

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

GRID_K1 = (32.0, 40.0, 48.0, 56.0)
GRID_K3 = (24.0, 32.0, 40.0)
GRID_MOV = (0.0, 0.5, 1.0)


def load_games() -> list[tuple]:
    raw = model.load_json(os.path.join(DATA, "raw", "leaguepedia.json")) or {}
    games = []
    for m in raw.get("matches") or []:
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
    games.sort(key=lambda g: g[0])
    return games


def evaluate(games: list[tuple], k1: float, k3: float, mov: float) -> dict:
    ratings: dict[str, float] = {}
    val = {"n": 0, "brier": 0.0, "logloss": 0.0, "hits": 0}
    test = {"n": 0, "brier": 0.0, "logloss": 0.0, "hits": 0}
    for dt, t1, t2, winner, best_of, s1, s2 in games:
        r1 = ratings.get(t1, model.ELO_START)
        r2 = ratings.get(t2, model.ELO_START)
        exp1 = 1 / (1 + 10 ** ((r2 - r1) / 400))
        y = 1.0 if winner == 1 else 0.0
        if dt >= model.BACKTEST_SELECTION:
            target = test if dt >= model.BACKTEST_CUTOFF else val
            target["n"] += 1
            target["brier"] += (exp1 - y) ** 2
            eps = 1e-9
            target["logloss"] += -(y * math.log(max(exp1, eps)) + (1 - y) * math.log(max(1 - exp1, eps)))
            target["hits"] += 1 if (exp1 >= 0.5) == (winner == 1) else 0
        if best_of >= 3 and s1 is not None and s2 is not None:
            k = k3 * (1.0 + mov * math.log1p(abs(s1 - s2)))
        else:
            k = k1
        ratings[t1] = r1 + k * (y - exp1)
        ratings[t2] = r2 + k * ((1 - y) - (1 - exp1))
    out = {}
    for name, agg in (("validation", val), ("test", test)):
        n = agg["n"] or 1
        out[name] = {"n": agg["n"], "accuracy": round(agg["hits"] / n, 4),
                     "brier": round(agg["brier"] / n, 4), "logloss": round(agg["logloss"] / n, 4)}
    return out


def main() -> None:
    games = load_games()
    configs = []
    for k1 in GRID_K1:
        for k3 in GRID_K3:
            for mov in GRID_MOV:
                res = evaluate(games, k1, k3, mov)
                configs.append({"k_opening": k1, "k_series": k3, "mov_weight": mov, **res,
                                "shipped": (k1 == model.ELO_K_OPENING and k3 == model.ELO_K_SERIES
                                            and mov == model.MOV_WEIGHT)})
    ranked = sorted(configs, key=lambda c: c["validation"]["brier"])
    shipped = next((c for c in configs if c["shipped"]), None)
    shipped_rank = ranked.index(shipped) + 1 if shipped else None
    spread = (max(c["validation"]["brier"] for c in configs)
              - min(c["validation"]["brier"] for c in configs))
    doc = {
        "generated_utc": model.iso(model.now_utc()),
        "series": len(games),
        "grid": {"k_opening": list(GRID_K1), "k_series": list(GRID_K3), "mov_weight": list(GRID_MOV)},
        "validation_window": f"{model.BACKTEST_SELECTION:%Y-%m-%d}..{model.BACKTEST_CUTOFF:%Y-%m-%d}",
        "test_window": f"{model.BACKTEST_CUTOFF:%Y-%m-%d}..",
        "configs": len(configs),
        "validation_brier_spread": round(spread, 4),
        "best_validation": ranked[0],
        "shipped": shipped,
        "shipped_rank_on_validation": shipped_rank,
        "top10": ranked[:10],
    }
    with open(os.path.join(DATA, "backtest_sweep.json"), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, sort_keys=False)
        fh.write("\n")
    print(f"sweep: {len(configs)} configs, validation Brier spread {spread:.4f}, "
          f"shipped rank {shipped_rank}/{len(configs)}, best {ranked[0]['validation']['brier']:.4f} "
          f"at k1={ranked[0]['k_opening']} k3={ranked[0]['k_series']} mov={ranked[0]['mov_weight']}")


if __name__ == "__main__":
    main()
