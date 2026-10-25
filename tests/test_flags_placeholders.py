#!/usr/bin/env python3
"""Regression tests for two derived flags on the Flagged for review page.

1. A card whose Hotspawn participant field holds a literal placeholder ("DELETED",
   "TBD", ...) must be called out, because the card still receives a pick for full
   coverage but the opponent cannot be identified as a team.
2. A card whose start time has passed *and* whose series is already recorded on
   Leaguepedia must be called out, because the published grade rests on that record
   while Hotspawn has not closed the card yet.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import flags  # noqa: E402


def _match(**over):
    base = {
        "id": "2001", "competition": "Test League", "start_utc": "2026-10-16T15:00:00Z",
        "team0": {"name": "Alpha", "rating_matches": 3},
        "team1": {"name": "Bravo", "rating_matches": 3},
        "p0": 0.55, "p1": 0.45, "method": "model", "confidence": "medium", "flags": [],
        "pick": {"side": 0, "team": "Alpha", "probability": 0.55, "other_probability": 0.45},
        "hotspawn_url": "https://www.hotspawn.com/matches/alpha-vs-bravo-test-league-2001",
        "market": None, "resolution": None, "stale": False, "result": None,
    }
    base.update(over)
    return base


class DerivedFlagTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data = self.tmp.name
        self._saved = flags.DATA
        flags.DATA = self.data
        self._write("flags_manual.json", {"flags": []})
        self._write("matching_report.json", {"joins": []})
        self._write("sources_status.json", {"sources": []})

    def tearDown(self) -> None:
        flags.DATA = self._saved

    def _write(self, name: str, payload: dict) -> None:
        with open(os.path.join(self.data, name), "w", encoding="utf-8") as fh:
            json.dump(payload, fh)

    def _run(self, rows):
        self._write("matches.json", {"generated_utc": "2026-10-25T00:00:00Z",
                                     "inventory_fetched_utc": "2026-10-25T00:00:00Z",
                                     "matches": rows})
        flags.main()
        with open(os.path.join(self.data, "flags.json"), encoding="utf-8") as fh:
            return json.load(fh)["flags"]

    def test_placeholder_participant_is_flagged(self):
        rows = [_match(team0={"name": "DELETED", "rating_matches": 0})]
        out = self._run(rows)
        hits = [f for f in out if "placeholder instead of a team name" in f["item"]]
        self.assertEqual(len(hits), 1)
        self.assertIn("#2001", hits[0]["detail"])
        self.assertIn("DELETED", hits[0]["detail"])
        self.assertTrue(hits[0]["source"].startswith("https://www.hotspawn.com/matches/"))

    def test_placeholder_check_is_case_insensitive_and_whole_name_only(self):
        rows = [
            _match(id="2002", team0={"name": "tbd", "rating_matches": 0}),
            _match(id="2003", team0={"name": "Deleted Esports", "rating_matches": 3}),
        ]
        out = self._run(rows)
        hits = [f for f in out if "placeholder instead of a team name" in f["item"]]
        self.assertEqual(len(hits), 1)
        self.assertIn("#2002", hits[0]["detail"])
        self.assertNotIn("#2003", hits[0]["detail"])

    def test_decided_but_still_listed_is_flagged(self):
        rows = [_match(stale=True, result={"score0": 0, "score1": 1, "winner_side": 1})]
        out = self._run(rows)
        hits = [f for f in out if "already decided in the official series record" in f["item"]]
        self.assertEqual(len(hits), 1)
        self.assertIn("#2001", hits[0]["detail"])
        self.assertIn("0-1", hits[0]["detail"])

    def test_stale_without_recorded_result_is_not_flagged_as_decided(self):
        rows = [_match(stale=True, result=None)]
        out = self._run(rows)
        self.assertFalse([f for f in out if "already decided in the official series record" in f["item"]])

    def test_clean_card_produces_no_placeholder_or_decided_flag(self):
        out = self._run([_match()])
        self.assertFalse([f for f in out if "placeholder instead of a team name" in f["item"]])
        self.assertFalse([f for f in out if "already decided in the official series record" in f["item"]])


if __name__ == "__main__":
    unittest.main(verbosity=2)
