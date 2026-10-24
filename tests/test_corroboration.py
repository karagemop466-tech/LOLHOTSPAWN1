"""Regression tests for the receipt lifecycle that bricked the six-hourly refresh on 2026-10-24.

The outage
----------
``refresh-picks`` failed on ``main`` on four consecutive scheduled runs and the published dataset was
frozen at ``2026-10-23T17:13:12Z``. The runner-side diagnostic (``data/diag/refresh.log``) isolated it to
one of the 41 publish gates::

    FAIL external receipts validated against the dataset :: 1 usable receipts, 16 rejected, ...

Cause: Hotspawn's fixtures API only returns cards that are still ``status=scheduled``. As soon as a
series is played its id leaves the feed, so every manually captured book receipt stops matching within
about a day. ``tools/corroborate.py`` filed those receipts as *rejected* and ``tools/verify.py`` treated
any rejected receipt as a hard build failure - so committing a receipt guaranteed a self-inflicted
outage. Receipts are corroboration only and can never change a pick, so they must never block one.

These tests pin the fixed behaviour:

* a receipt whose fixture has left the feed is **retired** (expected lifecycle, not an error);
* a genuinely defective receipt (price <= 1.0, wrong teams, malformed quote) is still **rejected**;
* the publish gate keeps ``critical`` and ``advisory`` gates in separate lists, and only a critical
  failure can stop a refresh.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import corroborate  # noqa: E402
import verify  # noqa: E402


def _match(fid, t0="Alpha Esports", t1="Bravo Gaming", p0=0.62):
    return {
        "id": fid,
        "competition": "Test League 2026 Split 1",
        "start_utc": "2026-10-30T18:00:00Z",
        "hotspawn_url": f"https://www.hotspawn.com/matches/alpha-vs-bravo-test-league-{fid}",
        "team0": {"name": t0},
        "team1": {"name": t1},
        "p0": p0,
        "p1": round(1 - p0, 4),
        "method": "model",
        "pick": {"team": t0, "probability": p0},
    }


def _capture(fixture_id, decimal=(1.80, 2.00), page_teams=("Alpha Esports", "Bravo Gaming"),
             source="bo3gg"):
    return {
        "fixture_id": fixture_id,
        "source": source,
        "page_url": "https://bo3.gg/lol/matches/current",
        "captured_utc": "2026-10-24T15:00:00Z",
        "page_teams": list(page_teams),
        "decimal": list(decimal),
        "verbatim": "{} {} {}".format(page_teams[0], " / ".join(str(d) for d in decimal), page_teams[1]),
    }


class CorroborationReceiptLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="lolhotspawn-corr-")
        self.data = os.path.join(self.tmp, "data")
        self.receipt_dir = os.path.join(self.data, "receipts", "external_odds")
        os.makedirs(self.receipt_dir)
        self._saved = (corroborate.DATA, corroborate.RECEIPT_DIR)
        corroborate.DATA = self.data
        corroborate.RECEIPT_DIR = self.receipt_dir

    def tearDown(self):
        corroborate.DATA, corroborate.RECEIPT_DIR = self._saved
        shutil.rmtree(self.tmp, ignore_errors=True)

    # --- fixtures ---------------------------------------------------------
    def write_dataset(self, matches):
        with open(os.path.join(self.data, "matches.json"), "w", encoding="utf-8") as fh:
            json.dump({"generated_utc": "2026-10-24T16:00:00Z", "matches": matches}, fh)

    def write_receipts(self, captures, name="2026-10-24.json"):
        doc = {
            "sources": [{"key": "bo3gg", "name": "bo3.gg LoL match centre",
                         "url": "https://bo3.gg/lol/matches/current",
                         "kind": "esports odds display", "runner_reachable": "HTTP 200"}],
            "captures": captures,
            "coverage_observations": [],
        }
        with open(os.path.join(self.receipt_dir, name), "w", encoding="utf-8") as fh:
            json.dump(doc, fh)

    def run_build(self):
        return corroborate.build()

    # --- tests ------------------------------------------------------------
    def test_receipt_for_a_listed_fixture_is_usable(self):
        self.write_dataset([_match("1000001")])
        self.write_receipts([_capture("1000001")])
        doc = self.run_build()
        self.assertEqual(len(doc["rows"]), 1)
        self.assertEqual(doc["rows"][0]["status"], "usable")
        self.assertEqual(doc["rejected"], [])
        self.assertEqual(doc["retired"], [])
        self.assertEqual(doc["summary"]["usable_receipts"], 1)
        self.assertEqual(doc["summary"]["retired_receipts"], 0)

    def test_receipt_for_a_delisted_fixture_is_retired_not_rejected(self):
        """The exact 2026-10-24 failure: the fixture was played and left the scheduled feed."""
        self.write_dataset([_match("1000001")])
        self.write_receipts([_capture("9999999")])
        doc = self.run_build()
        self.assertEqual(doc["rejected"], [],
                         "a de-listed fixture must never be reported as a defective receipt")
        self.assertEqual(len(doc["retired"]), 1)
        self.assertEqual(doc["retired"][0]["fixture_id"], "9999999")
        self.assertEqual(doc["retired"][0]["status"], "retired")
        self.assertIn("no longer listed", doc["retired"][0]["reason"])
        self.assertEqual(doc["summary"]["rejected_receipts"], 0)
        self.assertEqual(doc["summary"]["retired_receipts"], 1)
        self.assertEqual(doc["summary"]["receipts"], 1, "retired receipts still count towards the total")

    def test_every_receipt_delisted_still_leaves_the_publish_gate_green(self):
        """All 17 real receipts going stale at once must not fail the critical receipt check."""
        self.write_dataset([_match("1000001"), _match("1000002")])
        self.write_receipts([_capture("9000001"), _capture("9000002"), _capture("9000003")])
        doc = self.run_build()
        self.assertEqual(doc["rejected"], [])
        self.assertEqual(len(doc["retired"]), 3)
        # this is the boolean the critical publish gate is built from
        self.assertFalse(bool(doc.get("rejected")),
                         "corroborate must leave `rejected` empty so verify.py can publish")

    def test_defective_receipt_is_still_rejected(self):
        self.write_dataset([_match("1000001"), _match("1000003", "Charlie", "Delta")])
        self.write_receipts([
            _capture("1000001", decimal=(0.95, 2.10)),                       # price <= 1.0
            _capture("1000003", page_teams=("Wrong Side", "Other Wrong Side")),
            _capture("1000003", decimal=(1.7,)),                            # malformed: one price
        ])
        doc = self.run_build()
        self.assertEqual(len(doc["rejected"]), 3)
        self.assertEqual(doc["retired"], [])
        self.assertTrue(all(r["status"] in ("malformed", "unmatched") for r in doc["rejected"]))
        self.assertEqual(doc["summary"]["rejected_receipts"], 3)

    def test_egamersworld_ticker_ag_al_matches_hotspawns_full_name(self):
        """EGamersWorld writes 'AG.AL' where Hotspawn writes "Anyone's Legend" (fixture 1067688).

        Without the alias the receipt is filed as defective and the publish gate blocks the refresh,
        so the alias is load-bearing, not cosmetic.
        """
        self.assertTrue(corroborate.same("AG.AL", "Anyone's Legend"))
        self.assertTrue(corroborate.same("Anyone's Legend", "AG.AL"))
        self.write_dataset([_match("1067688", "Top Esports", "Anyone's Legend")])
        self.write_receipts([_capture("1067688", decimal=(2.51, 1.45),
                                      page_teams=("Top Esports", "AG.AL"))])
        doc = self.run_build()
        self.assertEqual(doc["rejected"], [])
        self.assertEqual(doc["rows"][0]["status"], "usable")

    def test_placeholder_quote_is_quarantined_neither_retired_nor_rejected(self):
        self.write_dataset([_match("1000001")])
        self.write_receipts([_capture("1000001", decimal=(1.80, 1.80))])
        doc = self.run_build()
        self.assertEqual(doc["rows"][0]["status"], "placeholder")
        self.assertEqual(doc["rejected"], [])
        self.assertEqual(doc["retired"], [])
        self.assertEqual(doc["summary"]["placeholders"], 1)

    def test_coverage_page_publishes_the_retired_ledger(self):
        self.write_dataset([_match("1000001")])
        self.write_receipts([_capture("9999999")])
        html = corroborate.render(self.run_build())
        self.assertIn("Retired receipts", html)
        self.assertIn("#9999999", html)
        # the strings the publish gate requires from coverage.html must all still be there
        for needle in ("How each match was priced", "Corroboration, match by match", "no pick at all"):
            self.assertIn(needle, html)


class PublishGateSeverityTests(unittest.TestCase):
    def setUp(self):
        self._saved = (list(verify.checks), list(verify.advisory))
        verify.checks.clear()
        verify.advisory.clear()

    def tearDown(self):
        verify.checks[:] = self._saved[0]
        verify.advisory[:] = self._saved[1]

    def test_add_defaults_to_critical(self):
        verify.add("a critical gate", True, "detail")
        self.assertEqual([c["name"] for c in verify.checks], ["a critical gate"])
        self.assertEqual(verify.advisory, [])
        self.assertEqual(verify.checks[0]["severity"], "critical")

    def test_advisory_gates_are_kept_out_of_the_blocking_list(self):
        verify.add("data integrity", True, "detail")
        verify.add("corroboration detail", False, "detail", severity="advisory")
        self.assertEqual([c["name"] for c in verify.checks], ["data integrity"])
        self.assertEqual([c["name"] for c in verify.advisory], ["corroboration detail"])
        self.assertFalse(verify.advisory[0]["ok"])
        self.assertTrue(all(c["ok"] for c in verify.checks),
                        "an advisory warning must never look like a critical failure")

    def test_published_report_partitions_the_two_severities(self):
        with open(ROOT / "data" / "verification.json", encoding="utf-8") as fh:
            report = json.load(fh)
        for key in ("checks", "advisory", "passed", "passed_strict",
                    "critical_checks", "advisory_checks"):
            self.assertIn(key, report, f"data/verification.json is missing '{key}'")
        self.assertEqual({c["severity"] for c in report["checks"]}, {"critical"})
        self.assertEqual({c["severity"] for c in report["advisory"]}, {"advisory"})
        self.assertEqual(report["critical_checks"], len(report["checks"]))
        self.assertEqual(report["advisory_checks"], len(report["advisory"]))
        self.assertEqual(report["passed"], all(c["ok"] for c in report["checks"]))
        self.assertGreaterEqual(len(report["checks"]), 20,
                                "the refresh workflow requires at least 20 blocking gates")

    def test_the_2026_10_24_outage_class_is_not_a_blocking_gate(self):
        """The gate that froze the site must now be built only from defective receipts."""
        src = (ROOT / "tools" / "verify.py").read_text(encoding="utf-8")
        gate = src.split('add("external receipts validated against the dataset", ', 1)[1]
        condition = gate.split(",", 1)[0]
        self.assertEqual(condition.strip(), "not bad_receipts",
                         "the blocking condition may only look at defective receipts; divergence and "
                         "retirement are corroboration-only and must never stop a publish")
        self.assertIn('severity="advisory"', src)
        self.assertIn("curated flags cite only currently listed fixtures", src)
        flag_gate = src.split('add("curated flags cite only currently listed fixtures"', 1)[1]
        self.assertIn('severity="advisory"', flag_gate.split(")", 2)[-1])



if __name__ == "__main__":
    unittest.main()
