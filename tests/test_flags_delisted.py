#!/usr/bin/env python3
"""Regression test: a curated flag that quotes a fixture which has since left the
Hotspawn list must be published as a *historical observation*, not stall the build.

Hotspawn drops a card once it kicks off, so every curated note that quotes a fixture id
becomes "delisted" within days. The publish gate used to fail on that (time passing was
treated as a data defect and the refresh stopped), and the replacement gate asserts that
the annotation actually happened.
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


MATCH = {
    "id": "1001", "competition": "Test League", "start_utc": "2026-10-25T12:00:00Z",
    "team0": {"name": "Alpha"}, "team1": {"name": "Bravo"},
    "p0": 0.6, "p1": 0.4, "method": "model", "confidence": "medium", "flags": [],
    "pick": {"side": 0, "team": "Alpha", "probability": 0.6, "other_probability": 0.4},
    "hotspawn_url": "https://www.hotspawn.com/matches/alpha-vs-bravo-test-league-1001",
    "market": None, "resolution": None, "stale": True,
}

MANUAL = {"note": "test", "reviewed_utc": "2026-10-24T00:00:00Z", "flags": [
    {"severity": "medium", "item": "Live reference on #1001", "detail": "A note about a listed card.",
     "source": "https://www.hotspawn.com/matches/alpha-vs-bravo-test-league-1001",
     "verification": "checked 2026-10-24"},
    {"severity": "low", "item": "Historical reference on #9999999", "detail": "A note about a card that left.",
     "source": "https://www.hotspawn.com/matches/gone-vs-gone-test-league-9999999",
     "verification": "checked 2026-10-24"},
]}


class DelistedCuratedFlagTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data = self.tmp.name
        self._saved = flags.DATA
        flags.DATA = self.data
        self._write("matches.json", {"generated_utc": "2026-10-24T00:00:00Z", "matches": [MATCH]})
        self._write("flags_manual.json", MANUAL)
        self._write("matching_report.json", {"joins": []})
        self._write("sources_status.json", {"sources": []})

    def tearDown(self) -> None:
        flags.DATA = self._saved

    def _write(self, name: str, payload: dict) -> None:
        with open(os.path.join(self.data, name), "w", encoding="utf-8") as fh:
            json.dump(payload, fh)

    def test_delisted_reference_is_annotated_not_dropped(self) -> None:
        flags.main()
        out = json.load(open(os.path.join(self.data, "flags.json"), encoding="utf-8"))
        items = {f["item"]: f for f in out["flags"]}
        hist = [f for k, f in items.items() if k.startswith("Historical reference on #9999999")]
        self.assertEqual(len(hist), 1, "the curated note must still be published")
        self.assertEqual(hist[0]["delisted_refs_auto"], ["9999999"])
        self.assertIn("historical observation", hist[0]["detail"])
        self.assertIn("#9999999", hist[0]["detail"])

    def test_listed_reference_is_not_annotated(self) -> None:
        flags.main()
        out = json.load(open(os.path.join(self.data, "flags.json"), encoding="utf-8"))
        live = [f for f in out["flags"] if f["item"].startswith("Live reference on #1001")]
        self.assertEqual(len(live), 1)
        self.assertNotIn("delisted_refs_auto", live[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
