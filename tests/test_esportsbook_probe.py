"""Contract tests for the esportsbook probe receipt published on `sources.html`.

The site tells the reader that N esportsbook/aggregator endpoints were tried and 0 (or N) produced a
real LoL price. These tests keep that sentence honest: the receipt must parse, every row must carry
the HTTP result and a reason, and a row may only be `usable` if it actually contains a named fixture
with a decimal price.
"""

from __future__ import annotations

import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

RECEIPT = os.path.join(ROOT, "data", "esportsbook_probe.json")


class EsportsbookProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with open(RECEIPT, encoding="utf-8") as fh:
            cls.doc = json.load(fh)

    def test_receipt_shape(self):
        self.assertIn("rows", self.doc)
        self.assertGreater(len(self.doc["rows"]), 0)
        self.assertTrue(self.doc.get("generated_utc"))
        self.assertEqual(self.doc.get("candidates"), len(self.doc["rows"]))

    def test_every_row_records_what_came_back(self):
        for row in self.doc["rows"]:
            with self.subTest(slug=row.get("slug")):
                self.assertTrue(row.get("url", "").startswith("https://"))
                self.assertTrue(row.get("reason"), "a row without a reason is unusable as evidence")
                self.assertIn(row.get("usable"), (True, False))
                # status may be None only when the request itself failed
                if row.get("status") is None:
                    self.assertTrue(row.get("reason"))

    def test_usable_requires_a_named_fixture_with_a_price(self):
        for row in self.doc["rows"]:
            if row.get("usable"):
                with self.subTest(slug=row["slug"]):
                    fixtures = row.get("quoted_fixtures") or []
                    self.assertTrue(fixtures, "usable row must carry at least one quoted fixture")
                    for fixture in fixtures:
                        self.assertTrue(fixture.get("home"))
                        self.assertTrue(fixture.get("away"))
                        self.assertGreater(float(fixture.get("quote")), 1.0)
                        self.assertLess(float(fixture.get("quote")), 60.0)

    def test_summary_list_matches_rows(self):
        usable = [r["slug"] for r in self.doc["rows"] if r.get("usable")]
        self.assertEqual(sorted(usable), sorted(self.doc.get("usable") or []))

    def test_classifier_refuses_prices_it_cannot_see(self):
        import probe_esportsbook_feeds as probe

        got = {
            "status": 200,
            "ok": True,
            "content_type": "application/json",
            "bytes": 20,
            "text": json.dumps({"events": [{"name": "Team A vs Team B"}]}),
            "checked_utc": "2026-01-01T00:00:00Z",
        }
        record = probe.classify({"slug": "test", "url": "https://example.invalid"}, got)
        self.assertFalse(record["usable"])
        self.assertEqual(record["quoted_fixture_count"], 0)

    def test_classifier_accepts_an_observed_1xbet_style_quote(self):
        import probe_esportsbook_feeds as probe

        payload = {"Value": [{"O1": "Team A", "O2": "Team B", "O1X": 1.85, "L": "Test League"}]}
        got = {
            "status": 200,
            "ok": True,
            "content_type": "application/json",
            "bytes": 10,
            "text": json.dumps(payload),
            "checked_utc": "2026-01-01T00:00:00Z",
        }
        record = probe.classify({"slug": "test", "url": "https://example.invalid"}, got)
        self.assertTrue(record["usable"])
        self.assertEqual(record["quoted_fixture_count"], 1)


if __name__ == "__main__":
    unittest.main()
