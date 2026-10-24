"""Regression tests for the corroboration receipt ledger (tools/corroborate.py).

The ledger must keep four buckets strictly separate, because conflating them once deadlocked
the six-hourly refresh: every archived receipt aged past the 24 h window, the ledger counted
them as "rejected", the publish gate failed, and the build that would have refreshed the
receipts could therefore never run.

  usable    fresh capture, matched fixture, real price            -> counts, corroborates
  expired   matched fixture, older than the window                -> shown, never counted
  historic  fixture no longer listed by Hotspawn                  -> shown, never counted
  rejected  malformed / wrong teams / invalid price               -> fails the gate
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

_spec = importlib.util.spec_from_file_location(
    "lol_corroborate", os.path.join(ROOT, "tools", "corroborate.py"))
corroborate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(corroborate)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class ReceiptLedgerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data = self.tmp.name
        self.receipts = os.path.join(self.data, "receipts")
        os.makedirs(self.receipts, exist_ok=True)

        # Two fixtures are on the current Hotspawn list; the third receipt is for a delisted one.
        matches = {
            "generated_utc": _iso(datetime.now(timezone.utc)),
            "matches": [
                {"id": "1001", "competition": "Comp A", "start_utc": "2026-10-25T10:00:00Z",
                 "team0": {"name": "Alpha"}, "team1": {"name": "Beta"},
                 "p0": 0.60, "p1": 0.40, "method": "model", "hotspawn_url": "https://www.hotspawn.com/matches/x-1001",
                 "pick": {"team": "Alpha"}},
                {"id": "1002", "competition": "Comp A", "start_utc": "2026-10-25T11:00:00Z",
                 "team0": {"name": "Gamma"}, "team1": {"name": "Delta"},
                 "p0": 0.55, "p1": 0.45, "method": "model", "hotspawn_url": "https://www.hotspawn.com/matches/y-1002",
                 "pick": {"team": "Gamma"}},
            ],
        }
        with open(os.path.join(self.data, "matches.json"), "w", encoding="utf-8") as fh:
            json.dump(matches, fh)

        now = datetime.now(timezone.utc)
        doc = {
            "sources": [{"key": "book", "name": "Test Book", "url": "https://example.com/lol"}],
            "captures": [
                # fresh + matched -> usable
                {"fixture_id": "1001", "source": "book", "page_url": "https://example.com/a",
                 "captured_utc": _iso(now - timedelta(hours=2)),
                 "page_teams": ["Alpha", "Beta"], "decimal": [1.72, 2.10]},
                # matched but older than the window -> expired
                {"fixture_id": "1002", "source": "book", "page_url": "https://example.com/b",
                 "captured_utc": _iso(now - timedelta(hours=48)),
                 "page_teams": ["Gamma", "Delta"], "decimal": [1.80, 2.00]},
                # fixture no longer listed -> historic
                {"fixture_id": "9999", "source": "book", "page_url": "https://example.com/c",
                 "captured_utc": _iso(now - timedelta(hours=1)),
                 "page_teams": ["Old", "Team"], "decimal": [1.50, 2.50]},
                # wrong teams -> rejected
                {"fixture_id": "1001", "source": "book", "page_url": "https://example.com/d",
                 "captured_utc": _iso(now - timedelta(hours=1)),
                 "page_teams": ["Someone", "Else"], "decimal": [1.90, 1.90]},
            ],
        }
        with open(os.path.join(self.receipts, "2026-10-24.json"), "w", encoding="utf-8") as fh:
            json.dump(doc, fh)

        self._old_data = corroborate.DATA
        self._old_dir = corroborate.RECEIPT_DIR
        corroborate.DATA = self.data
        corroborate.RECEIPT_DIR = self.receipts

    def tearDown(self) -> None:
        corroborate.DATA = self._old_data
        corroborate.RECEIPT_DIR = self._old_dir

    def test_buckets(self) -> None:
        doc = corroborate.build()
        s = doc["summary"]
        self.assertEqual(s["receipts"], 4, s)
        self.assertEqual(s["usable_receipts"], 1, s)
        self.assertEqual(s["expired_receipts"], 1, s)
        self.assertEqual(s["historic_receipts"], 1, s)
        self.assertEqual(s["rejected_receipts"], 1, s)
        self.assertEqual(len(doc["rejected"]), 1)
        self.assertEqual(doc["rejected"][0]["fixture_id"], "1001")
        self.assertEqual(len(doc["expired"]), 1)
        self.assertEqual(doc["expired"][0]["fixture_id"], "1002")
        self.assertEqual(len(doc["historic"]), 1)
        self.assertEqual(doc["historic"][0]["fixture_id"], "9999")

    def test_ledger_accounts_for_every_receipt(self) -> None:
        doc = corroborate.build()
        s = doc["summary"]
        accounted = (s["usable_receipts"] + s["placeholders"] + s["rejected_receipts"]
                     + s["expired_receipts"] + s["historic_receipts"])
        self.assertEqual(accounted, s["receipts"], s)

    def test_expired_is_never_counted_as_usable_evidence(self) -> None:
        doc = corroborate.build()
        expired = doc["expired"][0]
        self.assertEqual(expired["status"], "expired")
        self.assertIn("archival", expired["verdict"])
        usable_ids = {r["fixture_id"] for r in doc["rows"] if r["status"] == "usable"}
        self.assertEqual(usable_ids, {"1001"})

    def test_historic_receipt_is_not_a_rejection(self) -> None:
        doc = corroborate.build()
        self.assertNotIn("9999", {r["fixture_id"] for r in doc["rejected"]})
        # ... and it never contributes to the coverage matrix as a priced competition
        for c in doc["coverage"]:
            if c["competition"] == "Comp A":
                self.assertEqual(c["external_priced"], 1)

    def test_age_hours(self) -> None:
        self.assertIsNone(corroborate.age_hours(None))
        self.assertIsNone(corroborate.age_hours("not-a-date"))
        self.assertAlmostEqual(corroborate.age_hours(_iso(datetime.now(timezone.utc))), 0.0, places=1)


if __name__ == "__main__":
    unittest.main()
