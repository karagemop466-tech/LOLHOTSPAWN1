#!/usr/bin/env python3
"""Phone-first landing strip (session 2faec1ff).

Between six-hourly refreshes, matches in the server-rendered "Starting
soon" strip kick off - and Hotspawn locks their picks. The strip must
therefore (a) stamp every row with its start time so the client can hide
started rows, and (b) the client must implement that hiding. The strip
also renders before the tournament directory so the next actual picks
are reachable without scrolling 29 directory cards on a phone.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

_spec = importlib.util.spec_from_file_location(
    "lol_site_next_strip", os.path.join(ROOT, "tools", "site.py"))
site_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(site_mod)


def _row(start="2026-10-26T12:00:00Z"):
    return {"id": "42", "competition": "Test League", "start_utc": start,
            "team0": {"name": "Alpha"}, "team1": {"name": "Beta"},
            "pick": {"team": "Alpha", "probability": 0.6}}


class NextStripTests(unittest.TestCase):
    def test_rows_carry_data_start_for_client_hiding(self):
        html = site_mod.next_strip([_row()])
        self.assertIn('data-start="2026-10-26T12:00:00Z"', html)
        self.assertIn("Pick: Alpha", html)
        self.assertIn("60%", html)

    def test_app_js_hides_started_rows(self):
        with open(os.path.join(ROOT, "assets", "app.js"), encoding="utf-8") as fh:
            js = fh.read()
        self.assertIn("initNextStrip", js)
        self.assertIn(".nextlist", js)
        self.assertIn(".nextrow[data-start]", js)

    def test_only_one_starting_soon_panel(self):
        # Two merged sessions each shipped a strip; duplicate id="soon"/id="next"
        # is invalid HTML and the second list rendered empty under the JS cap.
        with open(os.path.join(ROOT, "tools", "site.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertEqual(src.count('id="soon"'), 1)
        self.assertEqual(src.count('id="next"'), 1)

    def test_starting_soon_precedes_directory_in_builder(self):
        # Render order in build_index follows the body template order.
        with open(os.path.join(ROOT, "tools", "site.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertLess(src.find('<section class="panel" id="soon">'),
                        src.find('<section class="panel" id="directory">'))
        self.assertIn("upcoming[:16]", src)
        self.assertIn("table.html?upcoming=1", src)


if __name__ == "__main__":
    unittest.main()
