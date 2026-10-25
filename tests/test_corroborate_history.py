#!/usr/bin/env python3
"""Regression test for the 2026-10-24 refresh outage (session 5ff8e6bf).

The Hotspawn fixtures feed drops a card once it kicks off. External odds receipts are
static captures, so within a day every receipt points at a fixture that is no longer on
the list. `tools/corroborate.py` used to classify those as *rejected*, and the publish
gate `external receipts validated against the dataset` then failed - which stopped every
scheduled `refresh-picks` run from 2026-10-23T17:13Z onward and froze the published site
at that snapshot.

A receipt whose fixture has left the list is historical evidence: it must not price a
match, it must not count as rejected, and it must not block the build. A receipt that
claims a fixture id we still list but names different teams is a real defect and must
still fail the gate.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import corroborate  # noqa: E402


def _recent(hours: float) -> str:
    """A capture timestamp inside the freshness window, relative to the wall clock.

    The receipt classes under test are time-based (`RECEIPT_MAX_AGE_HOURS` = 24 h), so a
    hard-coded date makes the suite start failing one day after it was written - which is
    what halted `refresh-picks` on 2026-10-25: the three failures were this fixture data
    expiring, not a regression in the pipeline. Keep the contract identical and only move
    the capture time with the clock.
    """
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _kickoff(hours: float = 12.0) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _match(fid: str, t0: str, t1: str, p0: float) -> dict:
    return {
        "id": fid, "competition": "Test League", "start_utc": _kickoff(),
        "team0": {"name": t0}, "team1": {"name": t1},
        "p0": p0, "p1": round(1 - p0, 4), "method": "market", "confidence": "high",
        "pick": {"side": 0, "team": t0, "probability": p0, "other_probability": round(1 - p0, 4)},
        "hotspawn_url": f"https://www.hotspawn.com/matches/{t0.lower().replace(' ', '-')}-vs-"
                        f"{t1.lower().replace(' ', '-')}-test-league-{fid}",
        "market": {"book": "Pinnacle", "venues": [{"name": "Pinnacle", "weight": 1.0,
                                                   "p0": p0, "p1": round(1 - p0, 4),
                                                   "url": "https://example.test/m",
                                                   "observed_utc": _recent(2)}]},
        "resolution": None, "flags": [],
    }


class ReceiptHistoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data = os.path.join(self.tmp.name, "data")
        self.receipts = os.path.join(self.data, "receipts", "external_odds")
        os.makedirs(self.receipts, exist_ok=True)
        self._saved = (corroborate.DATA, corroborate.RECEIPT_DIR, corroborate.OUT_JSON, corroborate.OUT_HTML)

    def tearDown(self) -> None:
        corroborate.DATA, corroborate.RECEIPT_DIR, corroborate.OUT_JSON, corroborate.OUT_HTML = self._saved

    def _write(self, matches: list[dict], captures: list[dict]) -> None:
        with open(os.path.join(self.data, "matches.json"), "w", encoding="utf-8") as fh:
            json.dump({"generated_utc": _recent(1), "matches": matches}, fh)
        doc = {
            "sources": [{"key": "pinnacle", "name": "Pinnacle", "kind": "bookmaker", "url": "https://example.test"}],
            "captures": captures,
            "coverage_observations": [],
        }
        with open(os.path.join(self.receipts, "test.json"), "w", encoding="utf-8") as fh:
            json.dump(doc, fh)
        corroborate.DATA = self.data
        corroborate.RECEIPT_DIR = self.receipts
        corroborate.OUT_JSON = os.path.join(self.data, "corroboration.json")
        corroborate.OUT_HTML = os.path.join(self.data, "coverage.html")

    @staticmethod
    def _capture(fid: str, teams: list[str], dec: list[float]) -> dict:
        return {"fixture_id": fid, "source": "pinnacle", "page_url": "https://example.test/m",
                "captured_utc": _recent(2), "verbatim": "1.60 / 2.30",
                "page_teams": teams, "decimal": dec}

    def test_receipt_for_a_delisted_fixture_is_historical_not_rejected(self) -> None:
        # Only 1001 is still on the Hotspawn list; 1002 kicked off and left the feed.
        self._write(
            matches=[_match("1001", "Alpha", "Bravo", 0.62)],
            captures=[self._capture("1001", ["Alpha", "Bravo"], [1.60, 2.30]),
                      self._capture("1002", ["Charlie", "Delta"], [1.90, 1.90])],
        )
        doc = corroborate.build()
        self.assertEqual(doc["rejected"], [], "a delisted fixture must not be reported as a rejected receipt")
        self.assertEqual(len(doc["historic"]), 1)
        self.assertEqual(doc["historic"][0]["fixture_id"], "1002")
        self.assertEqual(doc["summary"]["historic_receipts"], 1)
        self.assertEqual(doc["summary"]["rejected_receipts"], 0)
        self.assertEqual(doc["summary"]["usable_receipts"], 1)
        self.assertEqual([r["verdict"] for r in doc["rows"]], ["agrees"])
        # ... and the historical row never contributes a probability
        self.assertNotIn("ext_p0", doc["historic"][0])

    def test_receipt_naming_the_wrong_teams_still_fails_the_gate(self) -> None:
        # 1001 is listed, but the receipt names a different pair of teams: a real defect.
        self._write(
            matches=[_match("1001", "Alpha", "Bravo", 0.62)],
            captures=[self._capture("1001", ["Echo", "Foxtrot"], [1.60, 2.30])],
        )
        doc = corroborate.build()
        self.assertEqual(len(doc["rejected"]), 1, "a mismatched receipt on a live fixture must still be rejected")
        self.assertEqual(doc["rejected"][0]["status"], "unmatched")
        self.assertEqual(doc["historic"], [])

    def test_malformed_receipt_still_fails_the_gate(self) -> None:
        self._write(
            matches=[_match("1001", "Alpha", "Bravo", 0.62)],
            captures=[self._capture("1001", ["Alpha", "Bravo"], [0.0, 2.30])],
        )
        doc = corroborate.build()
        self.assertEqual(len(doc["rejected"]), 1)
        self.assertEqual(doc["rejected"][0]["status"], "malformed")

    def test_the_stats_still_reconcile(self) -> None:
        self._write(
            matches=[_match("1001", "Alpha", "Bravo", 0.62)],
            captures=[self._capture("1001", ["Alpha", "Bravo"], [1.60, 2.30]),
                      self._capture("1002", ["Charlie", "Delta"], [1.80, 1.80]),
                      self._capture("1003", ["Golf", "Hotel"], [2.10, 1.75])],
        )
        doc = corroborate.build()
        s = doc["summary"]
        self.assertEqual(s["receipts"], 3)
        # Full five-bucket partition, matching the ledger tools/verify.py reconciles:
        # receipts = usable + placeholders + rejected + expired + historic. (Session
        # aa39a6d5, merged with 650571cf's wall-clock-relative fixtures.)
        self.assertEqual(s["usable_receipts"] + s["placeholders"] + s["rejected_receipts"]
                         + s["expired_receipts"] + s["historic_receipts"], 3)
        self.assertEqual(s["expired_receipts"], 0, "fresh captures must not expire")

    def test_coverage_page_renders_the_historical_receipts(self) -> None:
        self._write(
            matches=[_match("1001", "Alpha", "Bravo", 0.62)],
            captures=[self._capture("1002", ["Charlie", "Delta"], [1.90, 1.95])],
        )
        doc = corroborate.build()
        html = corroborate.render(doc)
        self.assertIn("historic", html)
        self.assertIn("1002", html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
