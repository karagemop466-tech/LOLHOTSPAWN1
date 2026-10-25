#!/usr/bin/env python3
"""Competition-level line research helpers (session 1773543b).

The brief asks for a pick on every listed match, and for evidence about *why* a match has
no external line. Team-name matching alone cannot answer that: a book may price "Hanwha Life
Esports" in one event and never open the competition at all. These tests pin the two pieces
of evidence that answer it:

* `competition_aliases()` builds the alias tokens for every competition on today's Hotspawn
  list from the inventory plus the Leaguepedia page the dataset itself joined the
  competition to - so an alias is a recorded join, never a guess;
* `match_competitions()` reports which of those competitions a venue response actually
  mentions.

They are pure functions over committed files, so the test is deterministic and needs no
network. If the alias builder ever stops recognising the Worlds page (Leaguepedia writes
"2026 Season World Championship", Pinnacle writes "League of Legends - World Championship"),
the probe would silently under-report venue coverage - which is exactly the failure mode this
test prevents.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

_spec = importlib.util.spec_from_file_location(
    "probe_sources_under_test", os.path.join(ROOT, "tools", "probe_sources.py"))
probe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(probe)


class CompetitionAliases(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.aliases = probe.competition_aliases()

    def test_every_listed_competition_has_aliases(self) -> None:
        self.assertGreater(len(self.aliases), 0)
        for comp, toks in self.aliases.items():
            self.assertTrue(toks, f"{comp} has no alias tokens")
            self.assertIn(comp, toks, f"{comp} is not its own alias")

    def test_worlds_matches_the_page_leaguepedia_joined_it_to(self) -> None:
        # The dataset resolves "Worlds 2026 Main Event" to Leaguepedia's
        # "2026 Season World Championship/Main Event"; the venue spelling drops the season.
        self.assertIn("World Championship", self.aliases["Worlds 2026 Main Event"])
        hits = probe.match_competitions("League of Legends - World Championship", self.aliases)
        self.assertEqual(hits, ["Worlds 2026 Main Event"])

    def test_prime_league_alias_comes_from_the_join(self) -> None:
        prm = [c for c in self.aliases if c.startswith("PRM ")]
        self.assertTrue(prm)
        for comp in prm:
            self.assertIn("Prime League", self.aliases[comp])

    def test_unrelated_esports_text_matches_nothing(self) -> None:
        text = "CS2 - PGL Masters Bucharest | Dota 2 - EPL Masters | Valorant - Game Changers"
        self.assertEqual(probe.match_competitions(text, self.aliases), [])

    def test_matching_is_case_insensitive_and_safe_on_empty_input(self) -> None:
        hits = probe.match_competitions("komplettligaen 2026 autumn", self.aliases)
        self.assertIn("Komplettligaen 2026 Autumn", hits)
        self.assertEqual(probe.match_competitions("", self.aliases), [])


class ShortCodeMatching(unittest.TestCase):
    """Short competition codes must match as words, not inside unrelated English words.

    The first runner receipt produced "LIT 2027 Winter Promotion" on 20 of 46 venues because
    a bare substring test matched the letters l-i-t inside "split". The receipt has to be
    believable, so the token match is word-bounded and the evidence is recorded.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.aliases = {"LIT 2027 Winter Promotion": ["LIT", "LIT Winter Promotion"],
                       "RIVALS LEAGUE Season 2": ["RIVALS LEAGUE Season 2", "RIVALS"],
                       "Worlds 2026 Main Event": ["World Championship"]}

    def test_short_code_does_not_match_inside_a_word(self) -> None:
        text = "Best of 3 split quality elite popular"
        self.assertEqual(probe.match_competitions(text, self.aliases), [])

    def test_short_code_still_matches_as_a_standalone_word(self) -> None:
        text = "Upcoming: LIT 2027 Winter Promotion playoff fixture"
        self.assertEqual(probe.match_competitions(text, self.aliases),
                         ["LIT 2027 Winter Promotion"])

    def test_evidence_records_the_matched_token_and_context(self) -> None:
        ev = probe.competition_evidence("Watch the RIVALS LEAGUE Season 2 match today",
                                        self.aliases)
        self.assertEqual(len(ev), 1)
        self.assertEqual(ev[0]["competition"], "RIVALS LEAGUE Season 2")
        self.assertIn("RIVALS", ev[0]["context"])
        self.assertLessEqual(len(ev[0]["context"]), 200)


class PinnacleInventoryShape(unittest.TestCase):
    """A failed fetch must be recorded as a failure, never as 'the book has no LoL leagues'."""

    def test_unreachable_endpoint_reports_status_and_empty_lists(self) -> None:
        """A blocked or failed fetch must not be readable as "the book opens no LoL league".

        The network is stubbed so the assertion is the same on a laptop with no egress and on
        the build runner, where the endpoint does answer.
        """
        original = probe.get_json
        probe.get_json = lambda *a, **k: (403, None, "stubbed block")  # type: ignore[assignment]
        try:
            doc = probe.pinnacle_league_inventory({}, retries=0)
        finally:
            probe.get_json = original  # type: ignore[assignment]
        self.assertEqual(doc["status"], 403)
        self.assertEqual(doc["lol_leagues"], [])
        self.assertEqual(doc["lol_competitions_listed"], [])
        self.assertIn("url", doc)

    def test_league_list_is_parsed_into_per_league_matchup_counts(self) -> None:
        payload = [
            {"name": "League of Legends - World Championship", "matchupCount": 10},
            {"name": "CS2 - PGL Masters Bucharest", "matchupCount": 11},
            {"name": "League of Legends - World Championship", "matchupCount": 1},
        ]
        original = probe.get_json
        probe.get_json = lambda *a, **k: (200, payload, "")  # type: ignore[assignment]
        try:
            doc = probe.pinnacle_league_inventory(
                {"Worlds 2026 Main Event": ["World Championship"]}, retries=0)
        finally:
            probe.get_json = original  # type: ignore[assignment]
        self.assertEqual(doc["esports_leagues"], 3)
        self.assertEqual(doc["lol_leagues"],
                         [{"league": "League of Legends - World Championship", "matchup_count": 2}])
        self.assertEqual(doc["lol_competitions_listed"], ["Worlds 2026 Main Event"])
        self.assertEqual(doc["hotspawn_competitions_not_listed"], [])


if __name__ == "__main__":
    unittest.main()
