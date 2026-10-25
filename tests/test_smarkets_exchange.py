#!/usr/bin/env python3
"""Unit tests for UKGC-regulated Smarkets v3 exchange collector & soft-404 probe guard."""
from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import collect  # noqa: E402


class TestSmarketsExchangeCollector(unittest.TestCase):
    def test_filters_non_series_and_inplay_markets(self):
        events = [
            {
                "id": "1001",
                "name": "Top Esports vs G2 Esports",
                "type": "league_of_legends_match",
                "state": "upcoming",
                "bettable": True,
                "start_datetime": "2026-10-25T18:00:00Z",
                "full_slug": "/sport/esports/league-of-legends/worlds/2026/10/25/18-00/top-esports-vs-g2-esports",
            },
            {
                "id": "1002",
                "name": "In-play Series",
                "type": "league_of_legends_match",
                "state": "live",
                "bettable": True,
                "start_datetime": "2026-10-25T16:00:00Z",
                "full_slug": "/sport/esports/league-of-legends/live-series",
            },
        ]
        markets = [
            {"id": "2001", "event_id": "1001", "market_type": {"name": "WINNER_MAP", "param": "1"}, "state": "open", "hidden": False},
            {"id": "2002", "event_id": "1001", "market_type": {"name": "HANDICAP", "param": "1.5"}, "state": "open", "hidden": False},
            {"id": "2003", "event_id": "1001", "market_type": {"name": "OVER_UNDER", "param": "2.5"}, "state": "open", "hidden": False},
            {"id": "2004", "event_id": "1001", "market_type": {"name": "WINNER_2_WAY"}, "state": "open", "hidden": False},
            {"id": "2005", "event_id": "1002", "market_type": {"name": "WINNER_2_WAY"}, "state": "open", "hidden": False},
        ]
        contracts = [
            {"id": "3001", "market_id": "2004", "name": "Top Esports", "display_order": 0, "state_or_outcome": "open", "hidden": False},
            {"id": "3002", "market_id": "2004", "name": "G2 Esports", "display_order": 100, "state_or_outcome": "open", "hidden": False},
            {"id": "3003", "market_id": "2005", "name": "Live A", "display_order": 0, "state_or_outcome": "open", "hidden": False},
            {"id": "3004", "market_id": "2005", "name": "Live B", "display_order": 100, "state_or_outcome": "open", "hidden": False},
        ]
        quotes = {
            "3001": {"bids": [{"price": 4167, "quantity": 1439884}], "offers": [{"price": 5208, "quantity": 1252086}]},
            "3002": {"bids": [{"price": 4762, "quantity": 1259974}], "offers": [{"price": 5814, "quantity": 1433349}]},
            "3003": {"bids": [{"price": 9000, "quantity": 1000}], "offers": [{"price": 9500, "quantity": 1000}]},
            "3004": {"bids": [{"price": 500, "quantity": 1000}], "offers": [{"price": 1000, "quantity": 1000}]},
        }

        out = collect._smarkets_assemble_events(events, markets, contracts, quotes)
        self.assertEqual(len(out), 1)
        ev = out[0]
        self.assertEqual(ev["event_id"], "1001")
        self.assertEqual(ev["market_id"], "2004")
        self.assertEqual(
            ev["url"],
            "https://smarkets.com/sport/esports/league-of-legends/worlds/2026/10/25/18-00/top-esports-vs-g2-esports",
        )
        o0, o1 = ev["outcomes"]
        self.assertAlmostEqual(o0["mid_prob"], (4167 + 5208) / 20000.0, places=6)
        self.assertAlmostEqual(o1["mid_prob"], (4762 + 5814) / 20000.0, places=6)
        self.assertAlmostEqual(o0["spread_prob"], (5208 - 4167) / 10000.0, places=6)

    def test_rejects_kills_contracts(self):
        events = [{"id": "11", "name": "Gen.G vs LYON", "type": "league_of_legends_match", "state": "upcoming", "bettable": True}]
        markets = [{"id": "22", "event_id": "11", "market_type": {"name": "WINNER_2_WAY"}, "state": "open", "hidden": False}]
        contracts = [
            {"id": "31", "market_id": "22", "name": "Gen.G (Kills)", "display_order": 0, "state_or_outcome": "open", "hidden": False},
            {"id": "32", "market_id": "22", "name": "LYON (Kills)", "display_order": 100, "state_or_outcome": "open", "hidden": False},
        ]
        quotes = {"31": {"bids": [{"price": 8000}], "offers": [{"price": 8500}]}, "32": {"bids": [{"price": 1500}], "offers": [{"price": 2000}]}}
        self.assertEqual(collect._smarkets_assemble_events(events, markets, contracts, quotes), [])

    def test_soft_404_detects_midnite_retired_page(self):
        midnite_404 = b"<html><body><h1>Ooooooops!</h1><p>We can\xe2\x80\x99t find the page you\xe2\x80\x99re looking for.</p></body></html>"
        real_coupon = b"<html><body><h1>League of Legends Betting Odds</h1><div>Top Esports vs G2 Esports</div></body></html>"
        self.assertTrue(collect._is_soft_404(midnite_404))
        self.assertFalse(collect._is_soft_404(real_coupon))


if __name__ == "__main__":
    unittest.main()
