#!/usr/bin/env python3
"""Regression tests for canonical site rendering, mobile card-stacking, and flag generation
(session aca61f10).
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import tempfile
import unittest
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import flags as flags_mod  # noqa: E402

_site_spec = importlib.util.spec_from_file_location(
    "lol_site_test", os.path.join(ROOT, "tools", "site.py")
)
site_mod = importlib.util.module_from_spec(_site_spec)
_site_spec.loader.exec_module(site_mod)

_mob_spec = importlib.util.spec_from_file_location(
    "mobile_audit_test", os.path.join(ROOT, "audit", "mobile_audit.py")
)
mobile_audit = importlib.util.module_from_spec(_mob_spec)
_mob_spec.loader.exec_module(mobile_audit)


class SiteAndFlagsRegressionTests(unittest.TestCase):
    def test_mobile_audit_covers_all_14_root_pages_including_results(self) -> None:
        expected = {
            "index.html", "table.html", "picks.html", "results.html",
            "featured.html", "originated.html", "unresolved.html",
            "competitions.html", "teams.html", "flagged.html",
            "coverage.html", "verification.html", "sources.html",
            "methodology.html",
        }
        self.assertEqual(set(mobile_audit.PAGES), expected)

    def test_page_shell_omits_redundant_floating_picks_pill_on_table_page(self) -> None:
        on_table = site_mod.page_shell("All picks table", "table.html", "<p>body</p>")
        on_index = site_mod.page_shell("Summary", "index.html", "<p>body</p>")
        self.assertNotIn('class="mobile-picks"', on_table)
        self.assertIn('class="mobile-picks"', on_index)

    def test_next_up_rows_include_machine_readable_kickoff_for_live_filtering(self) -> None:
        row = {
            "id": "9001", "start_utc": "2026-10-25T12:00:00Z",
            "team0": {"name": "Alpha"}, "team1": {"name": "Bravo"},
            "pick": {"team": "Alpha", "probability": 0.6},
            "competition": "Cup A",
        }
        html_out = site_mod.next_strip([row])
        self.assertIn('class="nextrow" data-start="2026-10-25T12:00:00Z"', html_out)
        self.assertIn('href="picks.html#match-9001"', html_out)

    def test_results_page_every_td_has_data_label(self) -> None:
        with open(os.path.join(ROOT, "data", "matches.json"), encoding="utf-8") as fh:
            rows = (json.load(fh) or {}).get("matches") or []
        html_out = site_mod.build_results(rows)
        tds = len(re.findall(r"<td\b", html_out))
        labelled = len(re.findall(r"<td[^>]*data-label=", html_out))
        self.assertGreater(tds, 0)
        self.assertEqual(tds, labelled, "Every <td> on results.html must carry a mobile data-label")

    def test_methodology_has_no_duplicate_guardrail_and_uses_tier_priors(self) -> None:
        with open(os.path.join(ROOT, "data", "matches.json"), encoding="utf-8") as fh:
            doc = json.load(fh) or {}
        model_info = {**(doc.get("model") or {}), "backtest": doc.get("backtest") or {}}
        html_out = site_mod.build_methodology(model_info)
        self.assertEqual(html_out.count("Explicit quarantine over guesswork."), 1)
        self.assertNotIn("reaches 1500 at", html_out)
        self.assertIn("tier prior", html_out)

    def test_flagged_page_renders_fixture_table_with_probabilities_picks_and_sources(self) -> None:
        with open(os.path.join(ROOT, "data", "matches.json"), encoding="utf-8") as fh:
            rows = (json.load(fh) or {}).get("matches") or []
        with open(os.path.join(ROOT, "data", "flags.json"), encoding="utf-8") as fh:
            fl = (json.load(fh) or {}).get("flags") or []
        html_out = site_mod.build_flagged(fl, rows)
        self.assertIn('id="flagged-fixtures"', html_out)
        self.assertIn('data-label="Match &amp; Win %"', html_out)
        self.assertIn('data-label="Pick"', html_out)
        self.assertIn('data-label="Sources"', html_out)
        tds = len(re.findall(r"<td\b", html_out))
        labelled = len(re.findall(r"<td[^>]*data-label=", html_out))
        self.assertEqual(tds, labelled)

    def test_flags_detects_zero_history_debuts_without_false_positive_on_missing_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            matches = {
                "inventory_fetched_utc": "2026-10-24T17:00:00Z",
                "matches": [
                    {
                        "id": "9001", "competition": "Cup A", "start_utc": "2026-10-25T12:00:00Z",
                        "team0": {"name": "Alpha"}, "team1": {"name": "Bravo"},
                        "p0": 0.6, "p1": 0.4, "method": "model", "confidence": "medium", "flags": [],
                        "pick": {"side": 0, "team": "Alpha", "probability": 0.6, "other_probability": 0.4},
                        "hotspawn_url": "https://www.hotspawn.com/matches/a-vs-b-9001",
                    },
                    {
                        "id": "9002", "competition": "Cup B", "start_utc": "2026-10-25T13:00:00Z",
                        "team0": {"name": "Debut1", "rating_matches": 0},
                        "team1": {"name": "Debut2", "rating_matches": 0},
                        "p0": 0.5, "p1": 0.5, "method": "provisional", "confidence": "low", "flags": [],
                        "pick": {"side": 0, "team": "Debut1", "probability": 0.5, "other_probability": 0.5},
                        "hotspawn_url": "https://www.hotspawn.com/matches/d1-vs-d2-9002",
                    },
                    {
                        "id": "9003", "competition": "Cup B", "start_utc": "2026-10-25T14:00:00Z",
                        "team0": {"name": "Vet", "rating_matches": 10},
                        "team1": {"name": "Rookie", "rating_matches": 0},
                        "p0": 0.65, "p1": 0.35, "method": "provisional", "confidence": "low", "flags": [],
                        "pick": {"side": 0, "team": "Vet", "probability": 0.65, "other_probability": 0.35},
                        "hotspawn_url": "https://www.hotspawn.com/matches/vet-vs-rookie-9003",
                    },
                ],
            }
            with open(os.path.join(tmp, "matches.json"), "w", encoding="utf-8") as fh:
                json.dump(matches, fh)
            with open(os.path.join(tmp, "flags_manual.json"), "w", encoding="utf-8") as fh:
                json.dump({"flags": []}, fh)
            old_data = flags_mod.DATA
            flags_mod.DATA = tmp
            try:
                flags_mod.main()
            finally:
                flags_mod.DATA = old_data
            with open(os.path.join(tmp, "flags.json"), encoding="utf-8") as fh:
                built = json.load(fh)["flags"]
            items = [f["item"] for f in built]
            self.assertTrue(any("1 fixture(s) have 0 pre-kickoff rated series on BOTH sides" in x for x in items))
            self.assertTrue(any("1 provisional fixture(s) include a debut side with 0 pre-kickoff rated series" in x for x in items))


if __name__ == "__main__":
    unittest.main()
