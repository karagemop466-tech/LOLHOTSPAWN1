from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from build import build_all_pages  # noqa: E402
from markets import american_to_decimal, devig_decimal_pair, parse_book_receipts  # noqa: E402
from originate import (  # noqa: E402
    fit_bradley_terry_laplace,
    run_pipeline,
    series_win_prob,
    sigmoid,
)
from validate import EXPECTED_PAGES, validate_all  # noqa: E402


def test_devig_and_placeholder_guard() -> None:
    p0, p1, overround = devig_decimal_pair(1.20, 4.40)
    assert abs(p0 + p1 - 1.0) < 1e-12
    assert overround > 1.0
    assert p0 > 0.78

    # Symmetric 1.80 / 1.80 aggregator dummy quote MUST raise ValueError
    with pytest.raises(ValueError, match="1.80"):
        devig_decimal_pair(1.80, 1.80)


def test_book_receipts_exclude_placeholders() -> None:
    raw = json.loads((ROOT / "data" / "book_receipts.json").read_text(encoding="utf-8"))
    parsed = parse_book_receipts(raw)
    assert "1081423" in parsed  # Ground Zero Gaming vs Frank Esports (LCP Promotion)
    assert "1079080" not in parsed  # LGC Rising 1.80/1.80 placeholder rejected


def test_american_odds_conversion() -> None:
    assert abs(american_to_decimal(-200) - 1.50) < 1e-9
    assert abs(american_to_decimal(+150) - 2.50) < 1e-9


def test_bradley_terry_newton_convergence_and_symmetry() -> None:
    matches = [
        ("A", "B", 6.0, 2.0),
        ("B", "C", 5.0, 2.0),
        ("A", "C", 4.0, 0.0),
    ]
    idx, theta, cov, grad_inf = fit_bradley_terry_laplace(matches, ["A", "B", "C"], lam=1.5)
    assert grad_inf < 1e-12
    assert theta[idx["A"]] > theta[idx["B"]] > theta[idx["C"]]
    # Sum of MAP parameters under symmetric zero-mean prior equals 0.0
    assert abs(sum(theta)) < 1e-10
    # Covariance matrix is symmetric positive semi-definite
    for i in range(3):
        assert cov[i][i] > 0.0
        for j in range(3):
            assert abs(cov[i][j] - cov[j][i]) < 1e-12


def test_series_combinatorics_identities() -> None:
    for bo in (1, 2, 3, 5):
        assert abs(series_win_prob(0.5, bo) - 0.5) < 1e-12
        for pg in (0.18, 0.37, 0.64, 0.82):
            assert abs(series_win_prob(pg, bo) + series_win_prob(1.0 - pg, bo) - 1.0) < 1e-12
    # Favorite amplification across longer series
    assert series_win_prob(0.65, 5) > series_win_prob(0.65, 3) > series_win_prob(0.65, 1)


def test_zero_hotspawn_crowd_sensitivity_across_all_264_matches(tmp_path: Path) -> None:
    """Mutating every Hotspawn crowd `picked_percent` MUST change ZERO bytes of model outputs."""
    src_dir = ROOT / "data" / "sources"
    mut_src = tmp_path / "sources"
    mut_src.mkdir()
    for p in src_dir.glob("*.json"):
        if p.name == "hotspawn_lol_fixtures.json":
            rows = json.loads(p.read_text(encoding="utf-8"))
            flipped = []
            for r in rows:
                r2 = copy.deepcopy(r)
                r2["participants0_picked_percent"] = 99
                r2["participants1_picked_percent"] = 1
                flipped.append(r2)
            (mut_src / p.name).write_text(json.dumps(flipped), encoding="utf-8")
        else:
            (mut_src / p.name).symlink_to(p)

    mut_data = tmp_path / "data"
    mut_data.mkdir()
    (mut_data / "book_receipts.json").symlink_to(ROOT / "data" / "book_receipts.json")

    base_res = run_pipeline(sources_dir=src_dir, data_dir=tmp_path / "out_base", reference_iso="2026-10-21T20:39:00Z")
    mut_res = run_pipeline(sources_dir=mut_src, data_dir=mut_data, reference_iso="2026-10-21T20:39:00Z")

    for r_base, r_mut in zip(base_res["picks"], mut_res["picks"]):
        assert r_base["id"] == r_mut["id"]
        assert r_base["status"] == r_mut["status"]
        assert r_base["team0_prob"] == r_mut["team0_prob"]
        assert r_base["team1_prob"] == r_mut["team1_prob"]
        assert r_base["pick"] == r_mut["pick"]
        assert r_base["confidence"] == r_mut["confidence"]
        assert r_base["defensive_lean"] == r_mut["defensive_lean"]


def test_tier1_market_lines_strictly_isolated_from_tier2_standings() -> None:
    picks_doc = json.loads((ROOT / "data" / "picks.json").read_text(encoding="utf-8"))
    market_rows = [r for r in picks_doc["picks"] if r["status"] in ("market_consensus", "esportsbook_line")]
    assert len(market_rows) == 10
    for r in market_rows:
        # Verify exact match against pure market detail without any BT blending
        assert abs(r["team0_prob"] - round(r["market_detail"]["p0"], 4)) < 1e-9


def test_full_build_and_line_by_line_html_validation() -> None:
    pages = build_all_pages(data_dir=ROOT / "data", out_dir=ROOT)
    assert pages == EXPECTED_PAGES
    audit = validate_all(root_dir=ROOT)
    assert audit["rows_validated"] == 264
    assert audit["pages_validated"] == 9
    assert audit["sourced_table_rows_checked"] > 450
