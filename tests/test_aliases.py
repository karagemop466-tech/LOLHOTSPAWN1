"""Regression tests for explicit, evidence-backed aliases (data/aliases.json).

Covers the two cross-scope requests of integration session 6669f798 that session
7582f227 re-verified from the official sources and implemented:

1. Competition-scoped homonym override: inside the Bulgarian 'Logitech G
   SuperStrike Cup Qualifier', Hotspawn's 'paiN Gaming' slot is the amateur
   5-stack 'PNG' (Leaguepedia Participants + 'NON- 1 - PNG 0'), NOT the
   Brazilian CBLOL org 'paiN Gaming'. Outside that competition the global exact
   resolution to the Brazilian org must be unchanged.
2. Book-team alias: Kalshi event KXLOLGAME-26OCT271300RBMR names 'Rising Bees'
   for Hotspawn's 'Vitality Rising Bees' (#1079080, LGC Rising 2026 Playoffs),
   so the live CFTC contract joins the market consensus.
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from model import resolve_team, same_team, canon_book_team  # noqa: E402


EXACT = {'pain gaming': 'paiN Gaming', 'png': 'PNG', 'non toxic gaming': 'Non-toxic Gaming'}
BASE = {'pain gaming': {'paiN Gaming'}, 'png': {'PNG'}}
PAGE = 'Logitech G SuperStrike Cup/Qualifier'
PAGE_TEAMS = {PAGE: {'PNG', 'Non-toxic Gaming', 'Keep Yourself Positive', 'Ultim8'}}
COMP_ALIASES = {'logitech g superstrike cup qualifier': {'pain gaming': 'PNG'}}


class CompetitionScopedAliasTests(unittest.TestCase):
    def test_homonym_slot_resolves_to_png_inside_the_qualifier(self):
        team, how, notes = resolve_team(
            'paiN Gaming', EXACT, BASE, {}, PAGE, PAGE_TEAMS,
            'logitech g superstrike cup qualifier', COMP_ALIASES)
        self.assertEqual(team, 'PNG')
        self.assertEqual(how, 'alias')
        self.assertTrue(any('competition-scoped alias' in n for n in notes))

    def test_brazilian_org_unaffected_outside_the_qualifier(self):
        # A CBLOL competition (no scoped alias) must still resolve globally.
        team, how, _ = resolve_team(
            'paiN Gaming', EXACT, BASE, {}, 'CBLOL/2026 Season/Split 2', {},
            'cblol 2026 season split 2', COMP_ALIASES)
        self.assertEqual(team, 'paiN Gaming')
        self.assertEqual(how, 'exact')

    def test_backward_compatible_signature(self):
        # Existing callers (and tests) pass six positional args only.
        team, how, _ = resolve_team('paiN Gaming', EXACT, BASE, {}, PAGE, PAGE_TEAMS)
        self.assertEqual(team, 'paiN Gaming')
        self.assertEqual(how, 'exact')

    def test_unknown_alias_target_falls_through_instead_of_inventing(self):
        broken = {'logitech g superstrike cup qualifier': {'pain gaming': 'NoSuchTeam'}}
        team, how, _ = resolve_team(
            'paiN Gaming', EXACT, BASE, {}, PAGE, PAGE_TEAMS,
            'logitech g superstrike cup qualifier', broken)
        self.assertEqual(team, 'paiN Gaming')   # falls back to global exact
        self.assertEqual(how, 'exact')

    def test_opponent_on_the_same_card_still_resolves_normally(self):
        team, how, _ = resolve_team(
            'Non-toxic Gaming', EXACT, BASE, {}, PAGE, PAGE_TEAMS,
            'logitech g superstrike cup qualifier', COMP_ALIASES)
        self.assertEqual(team, 'Non-toxic Gaming')
        self.assertEqual(how, 'exact')


class KalshiRisingBeesAliasTests(unittest.TestCase):
    def test_same_team_matches_kalshi_short_name(self):
        self.assertTrue(same_team('Rising Bees', 'Vitality Rising Bees'))
        self.assertTrue(same_team('Vitality Rising Bees', 'Rising Bees'))
        self.assertEqual(canon_book_team('Rising Bees'), 'vitality rising bees')

    def test_mentalrush_name_is_untouched(self):
        self.assertTrue(same_team('Mental Rush', 'Mental Rush'))
        self.assertFalse(same_team('Rising Bees', 'Mental Rush'))


class AliasesFileEvidenceTests(unittest.TestCase):
    def test_every_competition_alias_has_named_evidence(self):
        doc = json.loads((ROOT / 'data' / 'aliases.json').read_text(encoding='utf-8'))
        evidence = doc.get('competition_aliases_evidence') or {}
        for comp, mapping in (doc.get('competition_aliases') or {}).items():
            for slot, target in mapping.items():
                key = f'{comp} | {slot} -> {target}'
                self.assertIn(key, evidence, f'missing evidence entry for {key!r}')
                text = evidence[key]
                self.assertIn('http', text, 'evidence must cite a source URL')
                self.assertIn(target, text)


if __name__ == '__main__':
    unittest.main()
