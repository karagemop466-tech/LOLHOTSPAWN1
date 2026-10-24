"""Receipt-identity regression tests for the integrated corroboration ledger."""
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import corroborate


class ReceiptIdentityTests(unittest.TestCase):
    def test_missing_fixture_id_is_malformed_not_historic(self):
        """A blank ID is not evidence for a fixture that legitimately left the feed."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "data"
            receipts = data / "receipts" / "external_odds"
            receipts.mkdir(parents=True)
            (data / "matches.json").write_text(json.dumps({
                "generated_utc": "2026-10-24T00:00:00Z",
                "matches": [{
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
                }],
            }), encoding="utf-8")
            (receipts / "test.json").write_text(json.dumps({
                "sources": [{"key": "test-book", "name": "Synthetic test book"}],
                "captures": [{
                    "fixture_id": "",
                    "source": "test-book",
                    "page_url": "https://example.test/odds/receipt",
                    "captured_utc": datetime.now(timezone.utc).isoformat(),
                    "page_teams": ["Alpha", "Beta"],
                    "decimal": [1.5, 2.5],
                    "verbatim": "synthetic test receipt; never used as production evidence",
                }],
            }), encoding="utf-8")
            with mock.patch.object(corroborate, "ROOT", str(root)), \
                 mock.patch.object(corroborate, "DATA", str(data)), \
                 mock.patch.object(corroborate, "RECEIPT_DIR", str(receipts)):
                doc = corroborate.build()

        self.assertEqual(doc["rows"], [])
        self.assertEqual(doc["historic"], [])
        self.assertEqual(doc["expired"], [])
        self.assertEqual(len(doc["rejected"]), 1)
        self.assertEqual(doc["rejected"][0]["status"], "malformed")
        self.assertIn("fixture id", doc["rejected"][0]["reason"])
        self.assertEqual(doc["summary"]["receipts"], 1)
        self.assertEqual(doc["summary"]["rejected_receipts"], 1)
        self.assertEqual(doc["summary"]["historic_receipts"], 0)


if __name__ == "__main__":
    unittest.main()
