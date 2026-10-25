#!/usr/bin/env python3
"""Regression tests for session be974159 model, market-hygiene, alias & grading fixes."""
from __future__ import annotations

import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import model as m  # noqa: E402


class TestModelBe974159(unittest.TestCase):
    def test_rising_bees_book_alias_matches_vitality_rising_bees(self) -> None:
        """Kalshi abbreviates 'Vitality Rising Bees' to 'Rising Bees' on KXLOLGAME-26OCT271300RBMR."""
        self.assertTrue(m.same_team("Vitality Rising Bees", "Rising Bees"))
        self.assertTrue(m.same_team("Rising Bees", "Vitality Rising Bees"))
        self.assertFalse(m.same_team("Mental Rush", "Rising Bees"))

    def test_competition_scoped_alias_quarantines_bulgarian_png_without_touching_cblol(self) -> None:
        """('Logitech G SuperStrike Cup Qualifier', 'paiN Gaming') -> 'PNG', leaving CBLOL 'paiN Gaming' intact."""
        lp_matches = [
            {"overview_page": "CBLOL/2026 Season/Split 2", "team1": "paiN Gaming", "team2": "LOUD", "winner": "1"},
            {"overview_page": "Logitech G SuperStrike Cup/Qualifier", "team1": "Non-toxic Gaming", "team2": "CRUEL FATE", "winner": "1"},
        ]
        exact, base, page_teams = m.build_index(lp_matches)
        with open(os.path.join(ROOT, "data", "aliases.json"), encoding="utf-8") as fh:
            aliases_doc = json.load(fh)
        aliases = {m.norm_name(k): v for k, v in (aliases_doc.get("aliases") or {}).items()}
        comp_aliases = {
            m.norm_name(ck): {m.norm_name(tk): tv for tk, tv in (tm or {}).items()}
            for ck, tm in (aliases_doc.get("competition_aliases") or {}).items()
        }

        # Bulgarian qualifier slot resolves to 'PNG', never CBLOL 'paiN Gaming', even with 0 prior PNG series.
        k_bg, how_bg, notes_bg = m.resolve_team(
            "paiN Gaming", exact, base, aliases,
            "Logitech G SuperStrike Cup/Qualifier", page_teams,
            comp_aliases=comp_aliases, competition="Logitech G SuperStrike Cup Qualifier",
        )
        self.assertEqual(k_bg, "PNG")
        self.assertEqual(how_bg, "alias")
        self.assertTrue(any("PNG" in n for n in notes_bg))

        # CBLOL / Worlds 'paiN Gaming' still resolves to 'paiN Gaming'.
        k_br, how_br, _ = m.resolve_team(
            "paiN Gaming", exact, base, aliases,
            "CBLOL/2026 Season/Split 2", page_teams,
            comp_aliases=comp_aliases, competition="CBLOL 2026 Split 2",
        )
        self.assertEqual(k_br, "paiN Gaming")
        self.assertEqual(how_br, "exact")

    def test_tier_prior_excludes_wildcard_and_online_qualifiers_from_tier1(self) -> None:
        """LCP Wildcard regional qualifiers and EWC online qualifiers must not receive Tier-1 1700 priors."""
        self.assertEqual(m.tier_prior("LCP/2026 Season/Split 1"), 1700.0)
        self.assertEqual(m.tier_prior("2026 Season World Championship/Main Event"), 1700.0)
        self.assertLess(m.tier_prior("LCP Wildcard/2026 Season/Regional Qualifiers/Thailand"), 1700.0)
        self.assertLess(m.tier_prior("LCP Wildcard/2026 Season/Playoffs"), 1700.0)
        self.assertLess(m.tier_prior("Esports World Cup 2026/Online Qualifiers/Asia-Pacific"), 1700.0)
        self.assertEqual(m.tier_prior("LJL/2026 Season/Summer Championship"), 1575.0)

    def test_kalshi_event_ticker_parses_edt_and_est_kickoff_utc(self) -> None:
        """Kalshi tickers encode US-Eastern start time (EDT UTC-4 in Oct, EST UTC-5 after DST ends Nov 1, 2026)."""
        self.assertEqual(m.parse_kalshi_start_utc("KXLOLGAME-26OCT271300RBMR"), "2026-10-27T17:00:00Z")
        self.assertEqual(m.parse_kalshi_start_utc("KXLOLGAME-26OCT251800MKOIDK"), "2026-10-25T22:00:00Z")
        self.assertEqual(m.parse_kalshi_start_utc("KXLOLGAME-26NOV051300T1GEN"), "2026-11-05T18:00:00Z")
        self.assertIsNone(m.parse_kalshi_start_utc(""))

    def test_market_lookup_rejects_stale_month_polymarket_and_kalshi_contracts(self) -> None:
        """Polymarket space-formatted game_start and Kalshi tickers >36h from kick-off must not bind."""
        pm_index = [{
            "names": ["The Bandits", "Dynasty"],
            "p0": 0.72, "p1": 0.28, "volume": 44218.0,
            "slug": "lol-ban2-dyn1-2026-08-25",
            "start": "2026-08-25 18:10:00+00",
            "observed_utc": "2026-10-25T14:00:00Z",
        }]
        kalshi_index = [{
            "names": ["Rising Bees", "Mental Rush"],
            "p0": 0.64, "p1": 0.38,
            "event_ticker": "KXLOLGAME-26SEP151300RBMR",
            "start": m.parse_kalshi_start_utc("KXLOLGAME-26SEP151300RBMR"),
            "observed_utc": "2026-10-25T14:00:00Z",
        }]
        self.assertIsNone(m.market_lookup(
            "999001", "The Bandits", "Dynasty", "2026-10-28T18:00:00Z",
            [], pm_index, [], [], [],
        ))
        self.assertIsNone(m.market_lookup(
            "999002", "Mental Rush", "Vitality Rising Bees", "2026-10-27T17:00:00Z",
            [], [], kalshi_index, [], [],
        ))

    def test_market_lookup_rejects_post_kickoff_in_play_quotes(self) -> None:
        """Quotes observed after scheduled start_utc are in-play prices and must not price pre-match picks."""
        pm_index = [{
            "names": ["Gen.G", "Hanwha Life Esports"],
            "p0": 0.16, "p1": 0.84, "volume": 120000.0,
            "slug": "lol-gen-hle-2026-10-24",
            "start": "2026-10-24 17:00:00+00",
            "observed_utc": "2026-10-24T17:35:00Z",
        }]
        kambi_index = [{
            "names": ["Gen.G", "Hanwha Life Esports"],
            "d0": 5.50, "d1": 1.12,
            "start": "2026-10-24T17:00:00Z",
            "url": "https://eu-offering-api.kambicdn.com/test",
            "observed_utc": "2026-10-24T17:35:00Z",
        }]
        self.assertIsNone(m.market_lookup(
            "1067688", "Gen.G", "Hanwha Life Esports", "2026-10-24T17:00:00Z",
            [], pm_index, [], [], kambi_index,
        ))

        # Pre-kickoff quotes on #1079080 join both Polymarket and Kalshi into a 2-venue consensus.
        pm_ok = [{
            "names": ["Vitality Rising Bees", "Mental Rush"],
            "p0": 0.635, "p1": 0.365, "volume": 58.47,
            "slug": "lol-rb-mr-2026-10-27",
            "start": "2026-10-27 16:00:00+00",
            "observed_utc": "2026-10-25T14:14:26Z",
        }]
        kal_ok = [{
            "names": ["Rising Bees", "Mental Rush"],
            "p0": 0.645, "p1": 0.38,
            "event_ticker": "KXLOLGAME-26OCT271300RBMR",
            "start": m.parse_kalshi_start_utc("KXLOLGAME-26OCT271300RBMR"),
            "observed_utc": "2026-10-25T14:13:24Z",
        }]
        res = m.market_lookup(
            "1079080", "Mental Rush", "Vitality Rising Bees", "2026-10-27T17:00:00Z",
            [], pm_ok, kal_ok, [], [],
        )
        self.assertIsNotNone(res)
        self.assertEqual(res["venue_count"], 2)
        self.assertEqual({v["name"] for v in res["venues"]}, {"Polymarket", "Kalshi"})
        self.assertLess(res["p0"], 0.5)
        self.assertGreater(res["p1"], 0.5)

    def test_published_hub_links_companion_docs_and_grades_disambiguated_results(self) -> None:
        """Canonical index.html links docs/index.html, and disambiguated completed series carry result records."""
        with open(os.path.join(ROOT, "index.html"), encoding="utf-8") as fh:
            index_html = fh.read()
        self.assertIn('href="docs/index.html"', index_html)
        with open(os.path.join(ROOT, "data", "matches.json"), encoding="utf-8") as fh:
            matches = json.load(fh)["matches"]
        by_id = {str(r["id"]): r for r in matches}
        if "1079080" in by_id:
            self.assertGreaterEqual((by_id["1079080"].get("market") or {}).get("venue_count", 0), 2)
        if "1081421" in by_id:
            self.assertEqual((by_id["1081421"].get("pick") or {}).get("team"), "FENNEL")
        if "1053095" in by_id and by_id["1053095"].get("stale"):
            self.assertIsNotNone(by_id["1053095"].get("result"))


if __name__ == "__main__":
    unittest.main()
