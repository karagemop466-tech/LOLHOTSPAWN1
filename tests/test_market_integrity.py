"""Regression tests for pre-lock market evidence and non-arbitrary picks."""
from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import model  # noqa: E402
from integrity import row_errors  # noqa: E402


START = "2026-10-25T20:00:00Z"
LOCK = "2026-10-25T19:55:00Z"


def bovada(observed="2026-10-25T19:50:00Z", start=START):
    return {
        "names": ["Alpha", "Bravo"], "d0": 1.60, "d1": 2.30,
        "start": start, "observed_utc": observed,
        "url": "https://example.test/alpha-bravo",
    }


def lookup(bovada_index, pm_index=None, exclusions=None):
    return model.market_lookup(
        "1001", "Alpha", "Bravo", START,
        [], pm_index or [], [], bovada_index, [],
        lock=LOCK, exclusions=exclusions,
    )


class MarketIntegrityTests(unittest.TestCase):
    def test_second_division_prior_does_not_inherit_challenger_promotion_prior(self):
        for page in (
            "Prime League 2nd Division/2027 Season/Promotion",
            "Komplettligaen 2nd Divisjon/2026 Season/Promotion",
            "Arabian League Division 2/2026 Season/Promotion",
        ):
            with self.subTest(page=page):
                self.assertEqual(model.tier_prior(page), model.ELO_START)
        self.assertEqual(model.tier_prior("Prime League 1st Division/2026 Season"), 1575.0)
        self.assertEqual(model.tier_prior("Prime League 3rd Division/2026 Season"), 1455.0)

    def test_kalshi_event_date_uses_event_time_not_settlement_deadline(self):
        self.assertEqual(model.kalshi_event_start("KXLOLGAME-26OCT241600KCLY"),
                         "2026-10-24T16:00:00Z")
        self.assertIsNone(model.kalshi_event_start("not-an-event"))

    def test_post_lock_and_untimed_observations_fail_closed(self):
        self.assertTrue(model.prelock_observation(bovada(), LOCK))
        self.assertFalse(model.prelock_observation(bovada("2026-10-25T20:52:38Z"), LOCK))
        self.assertFalse(model.prelock_observation(bovada(None), LOCK))
        self.assertFalse(model.prelock_observation(bovada("not-a-time"), LOCK))

    def test_post_lock_quote_is_excluded_with_an_audit_receipt(self):
        exclusions = []
        result = lookup([bovada("2026-10-25T20:52:38Z")], exclusions=exclusions)
        self.assertIsNone(result)
        self.assertEqual(len(exclusions), 1)
        self.assertEqual(exclusions[0]["venue"], "Bovada")
        self.assertEqual(exclusions[0]["reason"], "observed after Hotspawn lock")
        self.assertEqual(exclusions[0]["source_url"], "https://example.test/alpha-bravo")

    def test_prelock_quote_still_produces_a_devigged_line(self):
        exclusions = []
        result = lookup([bovada()], exclusions=exclusions)
        self.assertIsNotNone(result)
        self.assertEqual(result["book"], "Bovada")
        self.assertAlmostEqual(result["p0"] + result["p1"], 1.0)
        self.assertEqual(exclusions, [])

    def test_only_eligible_venue_enters_a_mixed_consensus(self):
        exclusions = []
        pm = [{
            "names": ["Alpha", "Bravo"], "p0": 0.90, "p1": 0.12,
            "volume": 5000, "slug": "alpha-bravo", "start": START,
            "observed_utc": "2026-10-25T20:52:38Z",
        }]
        result = lookup([bovada()], pm_index=pm, exclusions=exclusions)
        self.assertEqual([v["name"] for v in result["venues"]], ["Bovada"])
        self.assertEqual([x["venue"] for x in exclusions], ["Polymarket"])

    def test_same_teams_on_a_different_week_cannot_join(self):
        exclusions = []
        pm = [{
            "names": ["Alpha", "Bravo"], "p0": 0.60, "p1": 0.45,
            "volume": 5000, "slug": "old-alpha-bravo",
            "start": "2026-10-01T20:00:00Z", "observed_utc": "2026-10-25T19:50:00Z",
        }]
        self.assertIsNone(lookup([], pm_index=pm, exclusions=exclusions))
        self.assertEqual(exclusions, [])

    def test_exact_tie_is_not_a_legal_priced_pick(self):
        row = {
            "method": "provisional", "p0": 0.5, "p1": 0.5,
            "team0": {"name": "Alpha"}, "team1": {"name": "Bravo"},
            "pick": {"team": "Alpha", "probability": 0.5},
        }
        self.assertTrue(model.exact_tie(0.5, 0.5))
        self.assertTrue(model.exact_tie(0.4999, 0.5001))
        self.assertFalse(model.exact_tie(0.49, 0.51))
        self.assertIn("displayed 50/50 has no defensible favourite", row_errors(row))
        row["p0"], row["p1"] = 0.4999, 0.5001
        row["pick"]["probability"] = 0.5001
        row["pick"]["team"] = "Bravo"
        self.assertIn("displayed 50/50 has no defensible favourite", row_errors(row))
        row["method"] = "unresolved"
        row["p0"] = row["p1"] = None
        row["pick"] = None
        self.assertEqual(row_errors(row), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
