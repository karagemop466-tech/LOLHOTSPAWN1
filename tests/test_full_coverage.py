#!/usr/bin/env python3
"""Full-coverage contract (session 63c67a23).

The brief is "a pick for every League of Legends match listed on Hotspawn, and
never a number we cannot defend". Those two halves pull in opposite directions,
so the contract is pinned here in both directions:

* every published row carries a pick or an explicit, source-linked no-pick limitation;
* a row without a win probability is allowed only for a sourced administrative settlement
  or a quarantined no-pick with no eligible evidence - never a silent blank;
* the landing page gives every tournament an in-site deep link into a filtered
  pick table, so a phone user never has to hunt through the full list.

These are the assertions the publish gate also makes (`tools/verify.py`); the
tests keep the contract from regressing in the build that runs *before* the site
is regenerated, which is why they read the committed dataset and call the
renderer directly instead of asserting against the previous snapshot's HTML.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

# `import site` would return the standard library module (already in sys.modules), so load
# tools/site.py by path under its own name.
_spec = importlib.util.spec_from_file_location(
    "lol_site_full_coverage", os.path.join(ROOT, "tools", "site.py"))
site_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(site_mod)


def _row(fid: str, comp: str, t0: str, t1: str, *, p0=None, method="model",
         start="2026-10-26T12:00:00Z", resolution=None) -> dict:
    return {
        "id": fid, "competition": comp, "start_utc": start, "points": 10,
        "team0": {"name": t0}, "team1": {"name": t1},
        "p0": p0, "p1": None if p0 is None else round(1 - p0, 4),
        "method": method, "confidence": "medium",
        "pick": {"side": 0, "team": t0, "probability": p0,
                 "other_probability": None if p0 is None else round(1 - p0, 4)},
        "hotspawn_url": f"https://www.hotspawn.com/matches/{fid}",
        "resolution": resolution, "flags": [],
    }


class PublishedDatasetCoverage(unittest.TestCase):
    """The committed dataset must satisfy the coverage contract."""

    @classmethod
    def setUpClass(cls) -> None:
        with open(os.path.join(ROOT, "data", "matches.json"), encoding="utf-8") as fh:
            cls.rows = (json.load(fh) or {}).get("matches") or []

    def test_dataset_is_not_empty(self) -> None:
        self.assertGreater(len(self.rows), 0)

    def test_every_match_has_a_pick_or_documented_no_pick(self) -> None:
        missing = [r["id"] for r in self.rows
                   if not (r.get("pick") or {}).get("team")
                   and not (r.get("pick_type") == "no-pick"
                            and r.get("method") == "unresolved"
                            and str(r.get("basis") or "").strip())]
        self.assertEqual(missing, [], f"{len(missing)} rows have neither a pick nor a documented no-pick")

    def test_a_match_without_a_probability_names_its_evidence_source(self) -> None:
        bad = [r["id"] for r in self.rows
               if (r.get("pick") or {}).get("probability") is None
               and not ((r.get("resolution") or {}).get("source") or "").startswith("http")
               and not (r.get("pick_type") == "no-pick"
                        and (r.get("hotspawn_url") or "").startswith("http")
                        and str(r.get("basis") or "").strip())]
        self.assertEqual(bad, [], f"{len(bad)} unpriced rows without a settlement/no-pick source")

    def test_documented_no_pick_is_quarantined_with_blank_probabilities(self) -> None:
        rows = [r for r in self.rows if r.get("pick_type") == "no-pick"]
        bad = [r["id"] for r in rows
               if r.get("method") != "unresolved" or r.get("p0") is not None
               or r.get("p1") is not None or (r.get("pick") or {}).get("team")]
        self.assertEqual(bad, [])

    def test_settlement_picks_do_not_claim_a_probability(self) -> None:
        bad = [r["id"] for r in self.rows
               if (r.get("resolution") or {}).get("type") == "official-forfeit"
               and (r.get("pick") or {}).get("probability") is not None]
        self.assertEqual(bad, [])

    def test_every_row_carries_its_hotspawn_card(self) -> None:
        bad = [r["id"] for r in self.rows
               if not (r.get("hotspawn_url") or "").startswith("https://www.hotspawn.com/")]
        self.assertEqual(bad, [])

    def test_methods_are_known(self) -> None:
        unknown = sorted({r.get("method") for r in self.rows} - {"market", "model",
                                                                "provisional", "unresolved"})
        self.assertEqual(unknown, [])


class TournamentDirectory(unittest.TestCase):
    """The landing page must give every tournament a working deep link."""

    def test_every_competition_gets_one_linked_row(self) -> None:
        rows = [_row("1", "Alpha Cup", "A", "B", p0=0.6),
                _row("2", "Alpha Cup", "C", "D", p0=0.4),
                _row("3", "Beta League", "E", "F", method="provisional")]
        html = site_mod.tournament_directory(rows)
        self.assertEqual(html.count("<tr>"), 2)
        self.assertIn('href="table.html?comp=Alpha%20Cup"', html)
        self.assertIn('href="table.html?comp=Beta%20League"', html)
        # counts: Alpha Cup has two matches, both priced; Beta League has one, unpriced
        self.assertIn('data-label="Matches">2<', html)
        self.assertIn('data-label="With a win %">2<', html)
        self.assertIn('data-label="With a win %">0<', html)

    def test_query_strings_are_url_encoded(self) -> None:
        rows = [_row("9", "LigaGG CELOL B 2026 Split 2 Playoffs", "X", "Y", p0=0.5)]
        html = site_mod.tournament_directory(rows)
        self.assertIn("comp=LigaGG%20CELOL%20B%202026%20Split%202%20Playoffs", html)
        self.assertNotIn(" ", html.split('href="table.html?comp=')[1].split('"')[0])


class DeepLinkClient(unittest.TestCase):
    """The filter must honour the query string the directory generates."""

    def test_app_js_reads_the_query_string(self) -> None:
        with open(os.path.join(ROOT, "assets", "app.js"), encoding="utf-8") as fh:
            js = fh.read()
        self.assertIn("initDeepLinks", js)
        self.assertIn('params.get("comp")', js)
        self.assertIn('params.get("method")', js)
        self.assertIn("URLSearchParams", js)


if __name__ == "__main__":
    unittest.main()
