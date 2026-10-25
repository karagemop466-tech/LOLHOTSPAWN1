"""Regression tests for archived external receipts whose Hotspawn card has rolled off.

Hotspawn drops a fixture from `status=scheduled` as soon as it settles. Every manually
captured external receipt therefore eventually points at an id that is no longer in
`data/matches.json`. Until 2026-10-24 `tools/corroborate.py` filed those as `rejected`,
and `tools/verify.py` fails the publish gate on any rejected receipt, so the six-hourly
refresh died four times in a row (2026-10-23T21:26Z - 2026-10-24T15:59Z) purely because
time had passed.

The contract these tests pin down:

* a receipt for a fixture no longer listed is **historical evidence** (`off-list`) -
  published, linked, excluded from pricing, and never counted as a failure;
* a receipt for a fixture that IS listed but whose teams do not match is still
  **rejected**, so a real transcription error cannot hide behind the retirement rule;
* a malformed receipt (bad price, wrong arity) is still **rejected**.
"""
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import corroborate  # noqa: E402


MATCHES = {
    "generated_utc": "2026-10-24T00:00:00Z",
    "matches": [
        {
            "id": "1111",
            "competition": "Test Cup",
            "start_utc": "2026-10-25T12:00:00Z",
            "team0": {"name": "Alpha"},
            "team1": {"name": "Bravo"},
            "p0": 0.6,
            "p1": 0.4,
            "method": "model",
            "pick": {"team": "Alpha", "probability": 0.6},
            "hotspawn_url": "https://www.hotspawn.com/matches/alpha-vs-bravo-1111",
        }
    ],
}

# one receipt that matches a listed fixture, one for a card that has since rolled off
RECEIPT = {
    "sources": [{"key": "book", "name": "Example Book", "url": "https://example.com/lol",
                 "kind": "esportsbook", "runner_reachable": "yes"}],
    "captures": [
        {"fixture_id": "1111", "source": "book", "page_url": "https://example.com/m/1111",
         "captured_utc": "2026-10-24T00:00:00Z", "page_teams": ["Alpha", "Bravo"],
         "decimal": [1.65, 2.30], "verbatim": "Alpha 1.65 / Bravo 2.30"},
        {"fixture_id": "9999", "source": "book", "page_url": "https://example.com/m/9999",
         "captured_utc": "2026-10-23T00:00:00Z", "page_teams": ["Gone", "Also Gone"],
         "decimal": [1.90, 1.95], "verbatim": "Gone 1.90 / Also Gone 1.95"},
    ],
    "coverage_observations": [],
}


class OffListReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        (base / "data" / "receipts" / "external_odds").mkdir(parents=True)
        self.matches_path = base / "data" / "matches.json"
        self.matches_path.write_text(json.dumps(MATCHES), encoding="utf-8")
        self.receipt = json.loads(json.dumps(RECEIPT))
        # Keep the listed receipt inside the real 24-hour corroboration window. Fixed
        # 2026-10-24 captures made this test time-bomb the six-hour publisher.
        for hours, capture in enumerate(self.receipt["captures"], start=1):
            capture["captured_utc"] = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime(
                "%Y-%m-%dT%H:%M:%SZ")
        self.receipt_path = base / "data" / "receipts" / "external_odds" / "2026-10-23.json"
        self.receipt_path.write_text(json.dumps(self.receipt), encoding="utf-8")
        self.base = base
        self._saved = (corroborate.DATA, corroborate.RECEIPT_DIR, corroborate.ROOT)
        corroborate.DATA = str(base / "data")
        corroborate.RECEIPT_DIR = str(base / "data" / "receipts" / "external_odds")
        corroborate.ROOT = str(base)
        self.addCleanup(self._restore)

    def _restore(self):
        corroborate.DATA, corroborate.RECEIPT_DIR, corroborate.ROOT = self._saved

    def test_rolled_off_fixture_is_historical_not_rejected(self):
        doc = corroborate.build()
        self.assertEqual([r["fixture_id"] for r in doc["historic"]], ["9999"])
        self.assertEqual(doc["rejected"], [])
        self.assertEqual(doc["summary"]["historic_receipts"], 1)
        self.assertEqual(doc["summary"]["rejected_receipts"], 0)
        self.assertEqual(doc["summary"]["usable_receipts"], 1)
        self.assertEqual(doc["summary"]["receipts"], 2)

    def test_off_list_receipt_carries_its_source_link(self):
        doc = corroborate.build()
        row = doc["historic"][0]
        self.assertEqual(row["status"], "historic")
        self.assertEqual(row["page_url"], "https://example.com/m/9999")
        self.assertEqual(row["captured_utc"], self.receipt["captures"][1]["captured_utc"])
        self.assertIn("no longer listed by Hotspawn", row["reason"])
        self.assertEqual(row["status"], "historic")

    def test_listed_fixture_with_wrong_teams_is_still_rejected(self):
        rec = json.loads(json.dumps(self.receipt))
        rec["captures"][0]["page_teams"] = ["Charlie", "Delta"]
        self.receipt_path.write_text(json.dumps(rec), encoding="utf-8")
        doc = corroborate.build()
        self.assertEqual([r["fixture_id"] for r in doc["rejected"]], ["1111"])
        self.assertEqual(doc["rejected"][0]["status"], "unmatched")

    def test_malformed_price_is_still_rejected(self):
        rec = json.loads(json.dumps(self.receipt))
        rec["captures"][0]["decimal"] = [1.65, 1.0]
        self.receipt_path.write_text(json.dumps(rec), encoding="utf-8")
        doc = corroborate.build()
        self.assertEqual([r["fixture_id"] for r in doc["rejected"]], ["1111"])
        self.assertEqual(doc["rejected"][0]["status"], "malformed")

    def test_publish_gate_condition_holds_with_only_off_list_receipts(self):
        """The exact expression tools/verify.py evaluates for this gate."""
        doc = corroborate.build()
        bad = doc.get("rejected") or []
        diverged = [r for r in (doc.get("rows") or []) if r.get("verdict") == "diverges"]
        self.assertTrue(not bad and not diverged,
                        f"gate would fail: rejected={bad} diverged={diverged}")


if __name__ == "__main__":
    unittest.main()
