#!/usr/bin/env python3
"""Guard against wall-clock-dependent tests freezing the published snapshot.

Twice now a *test* has stopped the six-hourly refresh, and both times the site silently
aged instead of failing loudly in a way anyone noticed:

* 2026-10-24 — `tools/corroborate.py` counted every receipt whose fixture had left the
  Hotspawn feed as `rejected`, so the receipt gate failed once the archive was a day old
  and the build that would have refreshed the receipts could never run.
* 2026-10-25 — `tests/test_corroborate_history.py` and `tests/test_corroborate_offlist.py`
  hard-coded `captured_utc` dates (`2026-10-23/24`). The ledger correctly re-classified
  those captures as *expired* once they passed the 24 h pricing window, three
  `usable_receipts` assertions flipped, the `unit-tests` stage failed, and `refresh-picks`
  failed on 2026-10-25T04:44Z and 11:34Z (see `data/build_failed_steps.txt`).

The rule this test enforces: a receipt capture time in the test suite must be *computed*
(relative to now), never a literal date. Literal dates are fine for fixture data that the
ledger treats as timeless (`start_utc`), so only `captured_utc` is checked.
"""
from __future__ import annotations

import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"

# captured_utc = "YYYY-MM-DDTHH:MM:SSZ"  -> a literal date that will age out
_LITERAL_CAPTURE = re.compile(r'"captured_utc"\s*:\s*"(\d{4}-\d{2}-\d{2}T[^"]*)"')


class NoClockBombTests(unittest.TestCase):
    def test_no_test_pins_a_receipt_capture_to_a_literal_date(self) -> None:
        offenders: list[str] = []
        for path in sorted(TESTS.glob("*.py")):
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if _LITERAL_CAPTURE.search(line):
                    offenders.append(f"{path.name}:{lineno}: {line.strip()}")
        self.assertEqual(
            offenders, [],
            "captured_utc must be computed relative to now (e.g. `_iso(hours_ago)`), "
            "otherwise the receipt expires with the wall clock and fails the refresh: "
            + "; ".join(offenders),
        )

    def test_the_ledger_window_is_what_the_tests_believe_it_is(self) -> None:
        """The 24 h window is why the literals broke, so pin its value and both sides."""
        import importlib.util
        import sys
        from datetime import datetime, timedelta, timezone

        sys.path.insert(0, str(ROOT / "tools"))
        spec = importlib.util.spec_from_file_location(
            "lol_corroborate_guard", ROOT / "tools" / "corroborate.py")
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertEqual(mod.RECEIPT_MAX_AGE_HOURS, 24)

        fresh = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        old = (datetime.now(timezone.utc) - timedelta(hours=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.assertLess(mod.age_hours(fresh), mod.RECEIPT_MAX_AGE_HOURS)
        self.assertGreater(mod.age_hours(old), mod.RECEIPT_MAX_AGE_HOURS)


if __name__ == "__main__":
    unittest.main()
