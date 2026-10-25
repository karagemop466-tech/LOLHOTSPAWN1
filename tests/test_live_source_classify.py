#!/usr/bin/env python3
"""Pins how `audit/live_source_verify.py` classifies an HTTP verdict.

Why this exists: the daily `verify-live-sources` run (40177686632, 2026-10-25T08:42Z)
failed with `no broken market quote URL :: 2/7 resolved this run; causes={'rate_limited': 1,
'auth_required': 4}`. Those four URLs were Pinnacle guest-API matchup boards for cards that
had already kicked off. Pinnacle answers 401/403 once a board is pulled, so the audit was
reporting a *closed market* as a *broken link* and stayed red forever.

The rule now: a 401/403 on `guest.api.arcadia.pinnacle.com` is `market_closed` **only when a
control request with the same headers resolved in the same run**. If the control fails, the
verdict stays `auth_required` and the check still fails - a genuinely rejected key must never
be explained away as "market closed".
"""
from __future__ import annotations

import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "live_source_verify", ROOT / "audit" / "live_source_verify.py")
assert _spec and _spec.loader
lsv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lsv)

PINNACLE = "https://guest.api.arcadia.pinnacle.com/0.1/matchups/1639127314/markets/related/straight"


class ClassifyTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = lsv._PINNACLE_API_OK
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        lsv._PINNACLE_API_OK = self._saved

    def test_2xx_is_resolved(self) -> None:
        self.assertEqual(lsv.classify("https://example.test/a", 200, ""), "resolved")

    def test_throttle_is_never_rot(self) -> None:
        self.assertEqual(lsv.classify("https://example.test/a", 429, "HTTP 429"), "rate_limited")

    def test_kambi_404_is_an_expired_event(self) -> None:
        self.assertEqual(
            lsv.classify("https://eu-offering-api.kambicdn.com/x/event/1.json", 404, ""),
            "expired_event")

    def test_pinnacle_401_is_auth_failure_when_the_control_did_not_resolve(self) -> None:
        lsv._PINNACLE_API_OK = False
        self.assertEqual(lsv.classify(PINNACLE, 401, "HTTP 401"), "auth_required")
        self.assertIn("auth_required", lsv.BROKEN_DEFAULT)

    def test_pinnacle_401_is_a_closed_market_when_the_control_resolved(self) -> None:
        lsv._PINNACLE_API_OK = True
        self.assertEqual(lsv.classify(PINNACLE, 403, "HTTP 403"), "market_closed")

    def test_a_closed_board_is_not_counted_as_broken(self) -> None:
        lsv._PINNACLE_API_OK = True
        self.assertNotIn(lsv.classify(PINNACLE, 401, ""), lsv.BROKEN_DEFAULT)

    def test_other_hosts_keep_their_auth_verdict_even_with_a_good_pinnacle_control(self) -> None:
        lsv._PINNACLE_API_OK = True
        self.assertEqual(lsv.classify("https://www.bovada.lv/x", 403, ""), "auth_required")

    def test_a_404_is_still_rot(self) -> None:
        self.assertEqual(lsv.classify("https://www.hotspawn.com/matches/x", 404, ""), "not_found")


if __name__ == "__main__":
    unittest.main()
