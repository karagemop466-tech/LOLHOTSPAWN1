"""Regression tests for the receipt lifecycle that bricked the six-hourly refresh on 2026-10-24.

The outage
----------
``refresh-picks`` failed on ``main`` on four consecutive scheduled runs
(``40026767003``, ``40063260000``, ``40088464687``, ``40109474033``) and the published dataset was
frozen at ``2026-10-23T17:13:12Z``. The runner-side diagnostic (``data/diag/refresh.log``) isolated it
to one of the publish gates::

    FAIL external receipts validated against the dataset :: 1 usable receipts, 16 rejected, ...

Cause: Hotspawn's fixtures API only returns cards that are still ``status=scheduled``. As soon as a
series is played its id leaves the feed, so every manually captured book receipt stops matching within
about a day. ``tools/corroborate.py`` filed those receipts as *rejected* and ``tools/verify.py`` treated
any rejected receipt as a hard build failure - so committing a receipt guaranteed a self-inflicted
outage. Receipts are corroboration only and can never change a pick, so historic/expired receipts and
valid divergence must not block one; malformed or wrong-fixture evidence still fails closed.

Two sessions fixed this independently on 2026-10-24 (``80c624cd`` / ``1a46a678`` on main, ``62ba9cfe``
on its own branch); main's naming won the merge - a de-listed receipt is ``historic``. These tests pin
the merged behaviour so the class of failure cannot come back:

* a receipt whose fixture has left the feed is **historic**, never **rejected**;
* only genuinely malformed or wrong-fixture evidence (price <= 1.0, missing price/ID/teams) can block a publish;
* the ``AG.AL`` / ``Anyone's Legend`` alias is load-bearing, not cosmetic.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import corroborate  # noqa: E402


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
             source="bo3gg", captured=None):
    # Default to a wall-clock-relative stamp: a listed-fixture receipt is "usable" only
    # inside corroborate.RECEIPT_MAX_AGE_HOURS (24 h). A hard-coded 2026-10-24 date crossed
    # that window on 2026-10-25 and would turn this test into the next refresh outage.
    if captured is None:
        captured = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "fixture_id": fixture_id,
        "source": source,
        "page_url": "https://bo3.gg/lol/matches/current",
        "captured_utc": captured,
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

    def write_dataset(self, matches):
        with open(os.path.join(self.data, "matches.json"), "w", encoding="utf-8") as fh:
            json.dump({"generated_utc": "2026-10-24T16:00:00Z", "matches": matches}, fh)

    def write_receipts(self, captures, name="2026-10-24-test.json"):
        doc = {
            "sources": [{"key": "bo3gg", "name": "bo3.gg LoL match centre",
                         "url": "https://bo3.gg/lol/matches/current",
                         "kind": "esports odds display", "runner_reachable": "HTTP 200"}],
            "captures": captures,
            "coverage_observations": [],
        }
        with open(os.path.join(self.receipt_dir, name), "w", encoding="utf-8") as fh:
            json.dump(doc, fh)

    # --- tests ------------------------------------------------------------
    def test_receipt_for_a_listed_fixture_is_usable(self):
        self.write_dataset([_match("1000001")])
        self.write_receipts([_capture("1000001")])
        doc = corroborate.build()
        self.assertEqual(len(doc["rows"]), 1)
        self.assertEqual(doc["rows"][0]["status"], "usable")
        self.assertEqual(doc["rejected"], [])
        self.assertEqual(doc["historic"], [])
        self.assertEqual(doc["summary"]["usable_receipts"], 1)
        self.assertEqual(doc["summary"]["historic_receipts"], 0)

    def test_receipt_for_a_delisted_fixture_is_historic_not_rejected(self):
        """The exact 2026-10-24 failure: the fixture was played and left the scheduled feed."""
        self.write_dataset([_match("1000001")])
        self.write_receipts([_capture("9999999")])
        doc = corroborate.build()
        self.assertEqual(doc["rejected"], [],
                         "a de-listed fixture must never be reported as a defective receipt")
        self.assertEqual(len(doc["historic"]), 1)
        self.assertEqual(doc["historic"][0]["fixture_id"], "9999999")
        self.assertEqual(doc["historic"][0]["status"], "historic")
        self.assertIn("no longer listed", doc["historic"][0]["reason"])
        self.assertEqual(doc["summary"]["rejected_receipts"], 0)
        self.assertEqual(doc["summary"]["historic_receipts"], 1)
        self.assertEqual(doc["summary"]["receipts"], 1, "historic receipts still count towards the total")

    def test_every_receipt_delisted_still_leaves_the_publish_gate_green(self):
        """All 16 real receipts going historic at once must not fail the blocking receipt check."""
        self.write_dataset([_match("1000001"), _match("1000002")])
        self.write_receipts([_capture("9000001"), _capture("9000002"), _capture("9000003")])
        doc = corroborate.build()
        self.assertEqual(doc["rejected"], [])
        self.assertEqual(len(doc["historic"]), 3)
        # no rejected receipt means the exact blocking list used by tools/verify.py is empty
        self.assertEqual(doc["rejected"], [], "no rejected receipt, so the refresh must publish")

    def test_malformed_and_wrong_team_receipts_are_rejected(self):
        self.write_dataset([_match("1000001"), _match("1000003", "Charlie", "Delta")])
        self.write_receipts([
            _capture("1000001", decimal=(0.95, 2.10)),      # price <= 1.0
            _capture("1000003", decimal=(1.7,)),            # only one price
            _capture("1000003", page_teams=("Wrong Side", "Other Wrong Side")),
        ])
        doc = corroborate.build()
        self.assertEqual(doc["historic"], [])
        malformed = [r for r in doc["rejected"] if r.get("status") != "unmatched"]
        unmatched = [r for r in doc["rejected"] if r.get("status") == "unmatched"]
        self.assertEqual(len(malformed), 2, "price <= 1.0 and a single price are both malformed")
        self.assertEqual(len(unmatched), 1, "wrong teams is rejected separately from malformed prices")
        self.assertEqual(doc["summary"]["rejected_receipts"], 3)

    def test_placeholder_quote_is_quarantined_neither_historic_nor_rejected(self):
        """Symmetric 1.80/1.80 is the aggregator's 'no price yet' default, never a line."""
        self.write_dataset([_match("1000001")])
        self.write_receipts([_capture("1000001", decimal=(1.80, 1.80))])
        doc = corroborate.build()
        self.assertEqual(doc["rows"][0]["status"], "placeholder")
        self.assertEqual(doc["rejected"], [])
        self.assertEqual(doc["historic"], [])
        self.assertEqual(doc["summary"]["placeholders"], 1)

    def test_egamersworld_ticker_ag_al_matches_hotspawns_full_name(self):
        """EGamersWorld writes 'AG.AL' where Hotspawn writes "Anyone's Legend" (fixture 1067688).

        Without the alias the receipt is filed as unmatched and drops out of the corroboration
        table, so the alias is load-bearing, not cosmetic.
        """
        self.assertTrue(corroborate.same("AG.AL", "Anyone's Legend"))
        self.assertTrue(corroborate.same("Anyone's Legend", "AG.AL"))
        self.write_dataset([_match("1067688", "Top Esports", "Anyone's Legend")])
        self.write_receipts([_capture("1067688", decimal=(2.51, 1.45),
                                      page_teams=("Top Esports", "AG.AL"), source="egamersworld")])
        doc = corroborate.build()
        self.assertEqual(doc["rejected"], [])
        self.assertEqual(doc["rows"][0]["status"], "usable")

    def test_coverage_page_publishes_the_historic_ledger(self):
        self.write_dataset([_match("1000001")])
        self.write_receipts([_capture("9999999")])
        html = corroborate.render(corroborate.build())
        self.assertIn("9999999", html)
        self.assertIn("historic", html)
        # the strings the publish gate requires from coverage.html must all still be there
        for needle in ("How each match was priced", "Corroboration, match by match", "no pick at all"):
            self.assertIn(needle, html)


class PublishGateRegressionTests(unittest.TestCase):
    """Pin the shape of the gate that froze the site, so it cannot silently become blocking again."""

    def test_the_blocking_condition_only_looks_at_rejected_receipts(self):
        src = (ROOT / "tools" / "verify.py").read_text(encoding="utf-8")
        gate = src.split('add("external receipts validated against the dataset", ', 1)[1]
        condition = gate.split(",", 1)[0].strip()
        self.assertEqual(condition, "not bad_receipts",
                         "historic and expired receipts plus valid corroboration divergence must "
                         "never stop a publish; malformed and wrong-fixture evidence still must")
        self.assertIn("non-blocking", gate, "the gate detail must disclose non-blocking divergence")
        self.assertNotIn("not bad_receipts and not diverged", gate)

    def test_corroborate_separates_historic_from_rejected_in_its_output(self):
        src = (ROOT / "tools" / "corroborate.py").read_text(encoding="utf-8")
        self.assertIn('"historic": historic', src)
        self.assertIn('"rejected": off_list', src)
        self.assertIn('"historic_receipts"', src)

    def test_published_verification_report_is_consistent(self):
        with open(ROOT / "data" / "verification.json", encoding="utf-8") as fh:
            report = json.load(fh)
        self.assertIn("checks", report)
        self.assertIn("passed", report)
        self.assertTrue(report["passed"], "the committed verification report must be passing")
        self.assertGreaterEqual(len(report["checks"]), 20,
                                "the refresh workflow requires at least 20 publish gates")
        receipt_gate = [c for c in report["checks"]
                        if c["name"] == "external receipts validated against the dataset"]
        self.assertEqual(len(receipt_gate), 1)
        self.assertTrue(receipt_gate[0]["ok"], receipt_gate[0]["detail"])

    def test_committed_corroboration_has_no_blocking_receipt_defect(self):
        with open(ROOT / "data" / "corroboration.json", encoding="utf-8") as fh:
            corr = json.load(fh)
        blocking = corr.get("rejected") or []
        self.assertEqual(blocking, [], "a malformed or wrong-fixture committed receipt would block every refresh")
        self.assertGreaterEqual(corr["summary"]["receipts"], 1)


class ReceiptIdentityTests(unittest.TestCase):
    def test_missing_fixture_id_is_malformed_not_historic(self):
        """A blank ID is not evidence for a fixture that legitimately left the feed."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "data"
            receipts = data / "receipts" / "external_odds"
            receipts.mkdir(parents=True)
            (data / "matches.json").write_text(json.dumps({
                "generated_utc": "2026-10-24T00:00:00Z",
                "matches": [{
                    "id": "current-1",
                    "competition": "Synthetic test league",
                    "start_utc": "2099-01-01T00:00:00Z",
                    "team0": {"name": "Alpha"},
                    "team1": {"name": "Beta"},
                    "method": "market",
                    "p0": 0.6,
                    "p1": 0.4,
                    "pick": {"team": "Alpha"},
                    "hotspawn_url": "https://example.test/hotspawn/current-1",
                }],
            }), encoding="utf-8")
            (receipts / "test.json").write_text(json.dumps({
                "sources": [{"key": "test-book", "name": "Synthetic test book"}],
                "captures": [{
                    "fixture_id": "",
                    "source": "test-book",
                    "page_url": "https://example.test/odds/receipt",
                    "captured_utc": datetime.now(timezone.utc).isoformat(),
                    "page_teams": ["Alpha", "Beta"],
                    "decimal": [1.5, 2.5],
                    "verbatim": "synthetic test receipt; never used as production evidence",
                }],
            }), encoding="utf-8")
            with mock.patch.object(corroborate, "ROOT", str(root)), \
                 mock.patch.object(corroborate, "DATA", str(data)), \
                 mock.patch.object(corroborate, "RECEIPT_DIR", str(receipts)):
                doc = corroborate.build()

        self.assertEqual(doc["rows"], [])
        self.assertEqual(doc["historic"], [])
        self.assertEqual(doc["expired"], [])
        self.assertEqual(len(doc["rejected"]), 1)
        self.assertEqual(doc["rejected"][0]["status"], "malformed")
        self.assertIn("fixture id", doc["rejected"][0]["reason"])
        self.assertEqual(doc["summary"]["receipts"], 1)
        self.assertEqual(doc["summary"]["rejected_receipts"], 1)
        self.assertEqual(doc["summary"]["historic_receipts"], 0)


if __name__ == "__main__":
    unittest.main()
