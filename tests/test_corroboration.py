import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import corroborate


class CorroborationLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.match = {
            "id": "current-1",
            "competition": "Synthetic test league",
            "start_utc": "2099-01-01T00:00:00Z",
            "team0": {"name": "Alpha"},
            "team1": {"name": "Beta"},
            "method": "market",
            "p0": 0.6,
            "p1": 0.4,
            "pick": {"team": "Alpha"},
            "hotspawn_url": "https://example.test/hotspawn/current-1",
        }

    def receipt(self, fixture_id="current-1", teams=None, decimal=None):
        return {
            "fixture_id": fixture_id,
            "source": "test-book",
            "page_url": "https://example.test/odds/receipt",
            "captured_utc": "2026-10-24T00:00:00Z",
            "page_teams": ["Alpha", "Beta"] if teams is None else teams,
            "decimal": [1.5, 2.5] if decimal is None else decimal,
            "verbatim": "synthetic test receipt; never used as production evidence",
        }

    def build(self, captures, matches=None):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "data"
            receipts = data / "receipts" / "external_odds"
            receipts.mkdir(parents=True)
            (data / "matches.json").write_text(json.dumps({
                "generated_utc": "2026-10-24T00:00:00Z",
                "matches": [self.match] if matches is None else matches,
            }), encoding="utf-8")
            (receipts / "test.json").write_text(json.dumps({
                "sources": [{"key": "test-book", "name": "Synthetic test book"}],
                "captures": captures,
            }), encoding="utf-8")
            with mock.patch.object(corroborate, "ROOT", str(root)), \
                 mock.patch.object(corroborate, "DATA", str(data)), \
                 mock.patch.object(corroborate, "RECEIPT_DIR", str(receipts)):
                return corroborate.build()

    def test_departed_fixture_receipt_is_archived_not_rejected(self):
        doc = self.build([self.receipt("departed-1")])
        self.assertEqual(doc["rejected"], [])
        self.assertEqual(doc["rows"], [])
        self.assertEqual(len(doc["stale"]), 1)
        self.assertEqual(doc["stale"][0]["status"], "stale")
        self.assertEqual(doc["summary"]["receipts"], 1)
        self.assertEqual(doc["summary"]["stale_receipts"], 1)
        self.assertEqual(doc["summary"]["rejected_receipts"], 0)
        self.assertEqual(doc["summary"]["competitions_with_external_price"], 0)

    def test_listed_fixture_team_mismatch_still_fails_validation(self):
        doc = self.build([self.receipt(teams=["Alpha", "Different team"])])
        self.assertEqual(doc["stale"], [])
        self.assertEqual(len(doc["rejected"]), 1)
        self.assertEqual(doc["rejected"][0]["status"], "unmatched")
        self.assertEqual(doc["summary"]["rejected_receipts"], 1)

    def test_missing_fixture_id_is_malformed_not_stale(self):
        doc = self.build([self.receipt("")])
        self.assertEqual(doc["stale"], [])
        self.assertEqual(len(doc["rejected"]), 1)
        self.assertEqual(doc["rejected"][0]["status"], "malformed")

    def test_current_receipt_still_compares_probabilities(self):
        doc = self.build([self.receipt(), self.receipt("departed-1")])
        self.assertEqual(len(doc["rows"]), 1)
        self.assertEqual(doc["rows"][0]["status"], "usable")
        self.assertIn(doc["rows"][0]["verdict"], {"agrees", "diverges"})
        self.assertEqual(doc["summary"]["receipts"], 2)
        self.assertEqual(doc["summary"]["usable_receipts"], 1)
        self.assertEqual(doc["summary"]["stale_receipts"], 1)
        self.assertEqual(doc["summary"]["rejected_receipts"], 0)


if __name__ == "__main__":
    unittest.main()
