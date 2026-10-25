#!/usr/bin/env python3
"""Live-quote timing/extreme guards (session 2faec1ff).

Regression: on 2026-10-24 the build published LYON 99% / Karmine Corp 1%
(Worlds, Hotspawn id 1067684) from a single Kalshi print captured at
20:52:38Z - 52 minutes after the 20:00Z kick-off and 57 minutes after
Hotspawn locked picks at 19:55Z. The contract was settling after LYON's
upset win (bid/ask 0.99/1.00 vs 0.00/0.01 in data/raw/kalshi_lol.json),
while every pre-match source made LYON the underdog (~44-46%: bo3.gg,
Unibet/Kambi and OddsPortal receipts in data/corroboration.json; our Elo
39.7%). A post-kickoff or >=97% single prediction-market print must never
again become a published pre-match probability.
"""
from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import model  # noqa: E402

START = "2026-10-24T20:00:00Z"
BEFORE = "2026-10-24T19:00:00Z"
AFTER = "2026-10-24T20:52:38Z"  # the actual LYON/KC capture time


def kalshi(p0, p1, observed):
    return [{"names": ["LYON", "Karmine Corp"], "p0": p0, "p1": p1,
             "event_ticker": "KXLOLGAME-TEST", "observed_utc": observed}]


def pinnacle(observed):
    row = {"prices": {"home": {"decimal": 2.10, "american": 110},
                      "away": {"decimal": 1.80, "american": -125}},
           "participants": [{"name": "LYON", "alignment": "home"},
                            {"name": "Karmine Corp", "alignment": "away"}],
           "matchup_id": 1, "league": "League of Legends - World Championship"}
    return [{"names": ["LYON", "Karmine Corp"], "row": row,
             "start": START, "observed_utc": observed}]


class TestMarketGuards(unittest.TestCase):
    def setUp(self):
        model.QUOTE_REJECTIONS.clear()

    def test_lyon_replica_post_kickoff_kalshi_is_rejected(self):
        mk = model.market_lookup("1067684", "LYON", "Karmine Corp", START,
                                 [], [], kalshi(0.995, 0.01, AFTER), [], [])
        self.assertIsNone(mk)
        self.assertTrue(model.QUOTE_REJECTIONS)
        self.assertIn("kick-off", model.QUOTE_REJECTIONS[0]["reject"])
        self.assertEqual(model.QUOTE_REJECTIONS[0]["venue"], "Kalshi")

    def test_pre_kickoff_extreme_prediction_price_is_rejected(self):
        mk = model.market_lookup("1067684", "LYON", "Karmine Corp", START,
                                 [], [], kalshi(0.99, 0.01, BEFORE), [], [])
        self.assertIsNone(mk)
        self.assertIn("extreme", model.QUOTE_REJECTIONS[0]["reject"])

    def test_normal_pre_kickoff_kalshi_price_is_used(self):
        mk = model.market_lookup("1067684", "LYON", "Karmine Corp", START,
                                 [], [], kalshi(0.44, 0.56, BEFORE), [], [])
        self.assertIsNotNone(mk)
        self.assertAlmostEqual(mk["p0"], 0.44, places=3)
        self.assertEqual(mk["rejected_venues"], [])

    def test_post_kickoff_venue_does_not_poison_valid_consensus(self):
        mk = model.market_lookup("1067684", "LYON", "Karmine Corp", START,
                                 pinnacle(BEFORE), [], kalshi(0.995, 0.01, AFTER), [], [])
        self.assertIsNotNone(mk)
        self.assertEqual([v["name"] for v in mk["venues"]], ["Pinnacle"])
        self.assertEqual(mk["rejected_venues"], ["Kalshi"])
        self.assertLess(mk["p0"], 0.60)  # Pinnacle 2.10/1.80 prices LYON as underdog

    def test_post_kickoff_bookmaker_quote_is_rejected(self):
        mk = model.market_lookup("1067684", "LYON", "Karmine Corp", START,
                                 pinnacle(AFTER), [], [], [], [])
        self.assertIsNone(mk)
        self.assertIn("kick-off", model.QUOTE_REJECTIONS[0]["reject"])

    def test_stale_feed_is_not_fresh(self):
        self.assertFalse(model.feed_fresh("2020-01-01T00:00:00Z", "test"))
        self.assertFalse(model.feed_fresh(None, "test"))
        self.assertFalse(model.feed_fresh("not-a-date", "test"))


if __name__ == "__main__":
    unittest.main()
