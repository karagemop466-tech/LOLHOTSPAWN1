"""Integrity tests for the published track record (data/matches.json `grade` / `result`).

The site now publishes a hit/miss record, so the dataset itself must be internally
consistent: a grade can only exist where a structured official result exists, a "hit"
must name the same side as the recorded winner, and a recorded score must agree with the
recorded winner. These tests read the committed dataset (no network).
"""
from __future__ import annotations

import json
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class GradingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with open(os.path.join(ROOT, "data", "matches.json"), encoding="utf-8") as fh:
            cls.doc = json.load(fh)
        cls.rows = cls.doc.get("matches") or []

    def test_grade_only_with_result(self) -> None:
        bad = [r["id"] for r in self.rows if r.get("grade") and not r.get("result")]
        self.assertEqual(bad, [], "rows graded without a structured official result")

    def test_grade_values(self) -> None:
        allowed = {None, "hit", "miss", "settled"}
        bad = [(r["id"], r.get("grade")) for r in self.rows if r.get("grade") not in allowed]
        self.assertEqual(bad, [], "unknown grade values")

    def test_hit_miss_matches_winner_side(self) -> None:
        problems = []
        for r in self.rows:
            g = r.get("grade")
            if g not in ("hit", "miss"):
                continue
            pick = r.get("pick") or {}
            side = pick.get("side")
            win = (r.get("result") or {}).get("winner_side")
            if side is None or win is None:
                problems.append((r["id"], "missing side/winner"))
                continue
            expected = "hit" if side == win else "miss"
            if expected != g:
                problems.append((r["id"], g, side, win))
        self.assertEqual(problems, [], f"grade disagrees with the result: {problems[:5]}")

    def test_result_scores_agree_with_winner(self) -> None:
        problems = []
        for r in self.rows:
            res = r.get("result") or {}
            if not res:
                continue
            s0, s1 = res.get("score0"), res.get("score1")
            try:
                i0, i1 = int(s0), int(s1)
            except (TypeError, ValueError):
                continue
            if i0 == i1:
                problems.append((r["id"], "tied score recorded for a series"))
                continue
            win = 0 if i0 > i1 else 1
            if res.get("winner_side") != win:
                problems.append((r["id"], res.get("winner_side"), i0, i1))
        self.assertEqual(problems, [], f"score/winner mismatch: {problems[:5]}")

    def test_settlement_picks_never_carry_probability(self) -> None:
        bad = [r["id"] for r in self.rows
               if r.get("grade") == "settled" and (r.get("pick") or {}).get("probability") is not None]
        self.assertEqual(bad, [], "settlement picks must not carry a probability")

    def test_track_record_matches_rows(self) -> None:
        tr = self.doc.get("track_record") or {}
        graded = [r for r in self.rows if r.get("grade") in ("hit", "miss")]
        hits = sum(1 for r in graded if r["grade"] == "hit")
        self.assertEqual(tr.get("graded"), len(graded), "track_record.graded != graded rows")
        self.assertEqual(tr.get("hits"), hits, "track_record.hits != hit rows")
        self.assertEqual(tr.get("misses"), len(graded) - hits, "track_record.misses != miss rows")
        if graded:
            self.assertAlmostEqual(tr.get("accuracy"), hits / len(graded), places=3)

    def test_every_graded_row_cites_its_source(self) -> None:
        bad = [r["id"] for r in self.rows
               if r.get("grade") and not str((r.get("result") or {}).get("source") or "").startswith("https://")]
        self.assertEqual(bad, [], "graded rows must cite the results source")


if __name__ == "__main__":
    unittest.main()
