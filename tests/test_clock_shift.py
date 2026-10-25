#!/usr/bin/env python3
"""Guard against the wall-clock time bomb that froze the six-hourly refresh twice.

`tools/corroborate.py` grades receipt freshness against the real clock
(`RECEIPT_MAX_AGE_HOURS = 24`). The receipt test suites originally pinned their
fixture `captured_utc` values to fixed calendar dates (2026-10-24). The tests
passed on the day they were written; a day later every "usable" fixture had
aged into "expired", the unit-tests step of `.github/workflows/refresh.yml`
failed, the workflow published nothing, and the site froze at the previous
snapshot (2026-10-25: `data/build_failed_steps.txt` = `unit-tests` on `main`).

These tests make that failure impossible to reintroduce silently:

1. With `corroborate`'s clock shifted 30 days into the future, a receipt that is
   fresh *relative to that clock* is still usable, and an aged one is `expired`
   (archival evidence) with an empty `rejected` list - i.e. an ageing receipt
   archive can never fail the publish gate again.
2. A literal-scan of the four receipt test modules fails if any of them feeds a
   hard-coded ISO timestamp to `captured_utc`, `captured=` or `start_utc`.
   (Far-future sentinel dates such as 2099 are exempt; they cannot age into
   the past.)
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TESTS_DIR)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import corroborate  # noqa: E402

RECEIPT_TEST_MODULES = [
    "test_corroborate.py",
    "test_corroborate_history.py",
    "test_corroborate_offlist.py",
    "test_corroboration.py",
]

SHIFT = timedelta(days=30)


class _FutureDateTime(datetime):
    """datetime whose now() is the real now + SHIFT (strptime/strftime inherit fine)."""

    @classmethod
    def now(cls, tz=None):  # type: ignore[override]
        return super().now(tz) + SHIFT


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ClockShiftTests(unittest.TestCase):
    def _build(self, captured: str) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            data = os.path.join(tmp, "data")
            receipts = os.path.join(data, "receipts", "external_odds")
            os.makedirs(receipts)
            with open(os.path.join(data, "matches.json"), "w", encoding="utf-8") as fh:
                json.dump({"generated_utc": captured, "matches": [{
                    "id": "4242", "competition": "Clock Test League",
                    "start_utc": "2099-01-01T00:00:00Z",
                    "team0": {"name": "Alpha"}, "team1": {"name": "Beta"},
                    "p0": 0.6, "p1": 0.4, "method": "model",
                    "pick": {"team": "Alpha", "probability": 0.6},
                    "hotspawn_url": "https://example.test/matches/alpha-vs-beta-4242",
                }]}, fh)
            with open(os.path.join(receipts, "clock.json"), "w", encoding="utf-8") as fh:
                json.dump({
                    "sources": [{"key": "book", "name": "Example Book",
                                 "url": "https://example.test/lol"}],
                    "captures": [{
                        "fixture_id": "4242", "source": "book",
                        "page_url": "https://example.test/m/4242",
                        "captured_utc": captured,
                        "page_teams": ["Alpha", "Beta"], "decimal": [1.65, 2.30],
                        "verbatim": "Alpha 1.65 / Beta 2.30",
                    }],
                    "coverage_observations": [],
                }, fh)
            with mock.patch.object(corroborate, "datetime", _FutureDateTime), \
                 mock.patch.object(corroborate, "DATA", data), \
                 mock.patch.object(corroborate, "RECEIPT_DIR", receipts):
                return corroborate.build()

    def test_fresh_receipt_stays_usable_under_a_future_clock(self) -> None:
        # "fresh" is computed against the *shifted* clock, exactly like the
        # wall-clock-relative fixtures in the receipt test modules.
        future_now = datetime.now(timezone.utc) + SHIFT
        doc = self._build(_iso(future_now - timedelta(hours=1)))
        self.assertEqual(doc["summary"]["usable_receipts"], 1)
        self.assertEqual(doc["rejected"], [])

    def test_aged_receipt_never_blocks_publication_under_a_future_clock(self) -> None:
        # The 2026-10-25 outage in miniature: a receipt captured before the
        # clock moved on must be archival (`expired`), never `rejected`.
        doc = self._build(_iso(datetime.now(timezone.utc) - timedelta(hours=2)))
        self.assertEqual(doc["summary"]["usable_receipts"], 0)
        self.assertEqual(doc["summary"]["expired_receipts"], 1)
        self.assertEqual(doc["rejected"], [],
                         "an ageing receipt must never fail the publish gate")

    def test_no_hard_coded_fixture_timestamps_in_receipt_test_modules(self) -> None:
        pattern = re.compile(
            r'(captured_utc["\']?\s*[:=]|captured=|start_utc["\']?\s*:)\s*["\']'
            r'(\d{4})-\d\d-\d\dT\d\d:\d\d')
        offenders: list[str] = []
        for name in RECEIPT_TEST_MODULES:
            path = os.path.join(TESTS_DIR, name)
            with open(path, encoding="utf-8") as fh:
                source = fh.read()
            for match in pattern.finditer(source):
                if int(match.group(2)) >= 2099:
                    continue  # far-future sentinel: cannot age into the past
                line = source[: match.start()].count("\n") + 1
                offenders.append(f"{name}:{line}: {match.group(0)}")
        self.assertEqual(offenders, [],
                         "hard-coded fixture timestamps age into expired receipts and "
                         "freeze the refresh; compute them relative to the wall clock")


if __name__ == "__main__":
    unittest.main(verbosity=2)
