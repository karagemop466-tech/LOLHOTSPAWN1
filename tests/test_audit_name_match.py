#!/usr/bin/env python3
"""Tests for the independent verifier's short-form team-name acceptance.

The verifier reproduces every published market quote from the raw provider payloads.
Books print short forms of an organisation name (Kalshi lists "Rising Bees" for
Hotspawn's "Vitality Rising Bees"), so an exact-only comparison produced a false
"quote not found" failure on a real, correctly priced row (#1079080, 40c/64c).

The fix accepts a short form only when it is a *whole-token suffix* of the full
normalised name, at least six characters long, on both sides of the pairing, and
unique in the feed. Anything else still fails. These tests pin those boundaries.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    "verify_independent", os.path.join(ROOT, "audit", "verify_independent.py"))
vi = importlib.util.module_from_spec(_spec)
sys.modules["verify_independent"] = vi
_spec.loader.exec_module(vi)


class ShortFormTests(unittest.TestCase):
    def test_book_short_form_is_accepted(self):
        # Kalshi "Rising Bees" for Hotspawn "Vitality Rising Bees" (fixture 1079080).
        short = vi.norm("Rising Bees")
        full = vi.norm("Vitality Rising Bees")
        self.assertTrue(vi.is_documented_short_form(short, full))

    def test_exact_name_is_not_a_short_form(self):
        self.assertFalse(vi.is_documented_short_form(vi.norm("LOS"), vi.norm("LOS")))

    def test_short_forms_under_six_characters_are_never_accepted(self):
        # "T1" must not be stretched onto "T1 Academy", nor "MR" onto "Mental Rush".
        self.assertFalse(vi.is_documented_short_form(vi.norm("T1"), vi.norm("T1 Academy")))
        self.assertFalse(vi.is_documented_short_form(vi.norm("MR"), vi.norm("Mental Rush")))

    def test_a_prefix_is_not_a_short_form(self):
        # Only a truncated *suffix* counts. norm() already strips the word "team", so
        # "Heretics" is an exact match for "Team Heretics" rather than a short form,
        # while the reverse direction (a prefix that leaves trailing tokens) is refused.
        self.assertEqual(vi.norm("Heretics"), vi.norm("Team Heretics"))
        self.assertFalse(vi.is_documented_short_form(vi.norm("Heretics"),
                                                     vi.norm("Heretics Academy")))

    def test_generic_tokens_are_normalised_away_before_the_test(self):
        # norm() drops "esports"/"gaming"/"club", so these two collide exactly.
        self.assertEqual(vi.norm("Team Secret Whales"), vi.norm("Secret Whales"))

    def test_empty_side_never_matches(self):
        self.assertFalse(vi.is_documented_short_form("", vi.norm("Vitality Rising Bees")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
