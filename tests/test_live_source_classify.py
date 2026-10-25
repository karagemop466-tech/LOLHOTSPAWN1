#!/usr/bin/env python3
"""Pins how `audit/live_source_verify.py` classifies an HTTP verdict.

Why this exists: the daily `verify-live-sources` run (40177686632, 2026-10-25T08:42Z)
failed with `no broken market quote URL :: 2/7 resolved this run; causes={'rate_limited': 1,
'auth_required': 4}`. Those four URLs were Pinnacle guest-API matchup boards for cards that
had already kicked off. Pinnacle answers 401/403 once a board is pulled, so the audit was
reporting a *closed market* as a *broken link* and stayed red forever.

The rule now: a 401/403 on `guest.api.arcadia.pinnacle.com` is `market_closed` **only when a
control request with the same headers resolved in the same run**. If the control fails, the
verdict stays `auth_required` and the check still fails - a genuinely rejected key must never
be explained away as "market closed".
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "live_source_verify", ROOT / "audit" / "live_source_verify.py")
assert _spec and _spec.loader
lsv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lsv)

PINNACLE = "https://guest.api.arcadia.pinnacle.com/0.1/matchups/1639127314/markets/related/straight"


class ClassifyTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = lsv._PINNACLE_API_OK
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        lsv._PINNACLE_API_OK = self._saved

    def test_2xx_is_resolved(self) -> None:
        self.assertEqual(lsv.classify("https://example.test/a", 200, ""), "resolved")

    def test_throttle_is_never_rot(self) -> None:
        self.assertEqual(lsv.classify("https://example.test/a", 429, "HTTP 429"), "rate_limited")

    def test_kambi_404_is_an_expired_event(self) -> None:
        self.assertEqual(
            lsv.classify("https://eu-offering-api.kambicdn.com/x/event/1.json", 404, ""),
            "expired_event")

    def test_pinnacle_401_is_auth_failure_when_the_control_did_not_resolve(self) -> None:
        lsv._PINNACLE_API_OK = False
        self.assertEqual(lsv.classify(PINNACLE, 401, "HTTP 401"), "auth_required")
        self.assertIn("auth_required", lsv.BROKEN_DEFAULT)

    def test_pinnacle_401_is_a_closed_market_when_the_control_resolved(self) -> None:
        lsv._PINNACLE_API_OK = True
        self.assertEqual(lsv.classify(PINNACLE, 403, "HTTP 403"), "market_closed")

    def test_a_closed_board_is_not_counted_as_broken(self) -> None:
        lsv._PINNACLE_API_OK = True
        self.assertNotIn(lsv.classify(PINNACLE, 401, ""), lsv.BROKEN_DEFAULT)

    def test_other_hosts_keep_their_auth_verdict_even_with_a_good_pinnacle_control(self) -> None:
        lsv._PINNACLE_API_OK = True
        self.assertEqual(lsv.classify("https://www.bovada.lv/x", 403, ""), "auth_required")

    def test_a_404_is_still_rot(self) -> None:
        self.assertEqual(lsv.classify("https://www.hotspawn.com/matches/x", 404, ""), "not_found")


if __name__ == "__main__":
    unittest.main()


class ProbeControlsTests(unittest.TestCase):
    """The probe informs the verdict; it must never be the verdict itself."""

    def setUp(self) -> None:
        self._saved = (lsv._PINNACLE_API_OK, lsv.fetch)
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        lsv._PINNACLE_API_OK, lsv.fetch = self._saved

    def test_a_resolving_control_arms_the_classification(self) -> None:
        lsv.fetch = lambda url, **kw: {"url": url, "status": 200, "ok": True, "cause": "resolved"}
        controls, checks = lsv.probe_controls({"market_quote": [PINNACLE]})
        self.assertTrue(lsv._PINNACLE_API_OK)
        self.assertIn("pinnacle_guest_api", controls)
        self.assertEqual([c["ok"] for c in checks], [True])
        self.assertIn("proven by control: True", checks[0]["detail"])

    def test_a_rejected_control_is_only_informational(self) -> None:
        # 2026-10-25T14:18Z: the leagues control returned 403 while all 10 published
        # boards resolved. The probe alone must not fail the audit.
        lsv.fetch = lambda url, **kw: {"url": url, "status": 403, "ok": False, "cause": "auth_required"}
        controls, checks = lsv.probe_controls({"market_quote": [PINNACLE]})
        self.assertFalse(lsv._PINNACLE_API_OK)
        self.assertEqual([c["ok"] for c in checks], [True])
        self.assertIn("proven by control: False", checks[0]["detail"])

    def test_no_pinnacle_urls_means_no_probe(self) -> None:
        lsv._PINNACLE_API_OK = False
        controls, checks = lsv.probe_controls({"market_quote": ["https://www.bovada.lv/x"]})
        self.assertEqual((controls, checks), ({}, []))
        self.assertFalse(lsv._PINNACLE_API_OK)

    def test_a_crashing_probe_is_reported_not_raised(self) -> None:
        def boom(url, **kw):
            raise RuntimeError("network down")
        lsv.fetch = boom
        controls, checks = lsv.probe_controls({"market_quote": [PINNACLE]})
        self.assertFalse(lsv._PINNACLE_API_OK)
        self.assertEqual(len(checks), 1)
        self.assertIn("transport_error", checks[0]["detail"])


def _verdicts(**causes):
    """Build a by_url map: URL -> verdict dict, from cause=url pairs."""
    return {url: {"url": url, "cause": cause, "ok": cause == "resolved"}
            for cause, url in causes.items()}


class ReclassifyClosedBoardTests(unittest.TestCase):
    """A closed board is proven by the control *or* by any sibling that resolved."""

    def setUp(self) -> None:
        self._saved = lsv._PINNACLE_API_OK
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        lsv._PINNACLE_API_OK = self._saved

    def test_control_proof_reclassifies_a_401(self) -> None:
        lsv._PINNACLE_API_OK = True
        by_url = _verdicts(auth_required=PINNACLE)
        closed, checks = lsv.reclassify_closed_boards(by_url)
        self.assertEqual(closed, [PINNACLE])
        self.assertEqual(by_url[PINNACLE]["cause"], "market_closed")
        self.assertEqual(by_url[PINNACLE]["closed_board_proof"], "control-endpoint")
        self.assertEqual([c["ok"] for c in checks], [True])

    def test_a_resolved_sibling_is_enough_when_the_control_is_refused(self) -> None:
        # the exact 2026-10-25T14:18Z situation, had boards been closed
        lsv._PINNACLE_API_OK = False
        other = "https://guest.api.arcadia.pinnacle.com/0.1/matchups/1/markets/related/straight"
        by_url = _verdicts(auth_required=PINNACLE, resolved=other)
        closed, checks = lsv.reclassify_closed_boards(by_url)
        self.assertEqual(closed, [PINNACLE])
        self.assertEqual(by_url[PINNACLE]["closed_board_proof"], "sibling-resolved")
        self.assertEqual([c["ok"] for c in checks], [True])

    def test_without_any_proof_a_401_still_fails(self) -> None:
        lsv._PINNACLE_API_OK = False
        by_url = _verdicts(auth_required=PINNACLE)
        closed, checks = lsv.reclassify_closed_boards(by_url)
        self.assertEqual(closed, [])
        self.assertEqual(by_url[PINNACLE]["cause"], "auth_required")
        self.assertIn("cause", by_url[PINNACLE])  # unchanged
        self.assertEqual([c["ok"] for c in checks], [False])
        self.assertIn("auth_required", lsv.BROKEN_DEFAULT)

    def test_no_401_means_no_check_at_all(self) -> None:
        # a refused control must not invent a failure when every board resolved
        lsv._PINNACLE_API_OK = False
        by_url = _verdicts(resolved=PINNACLE)
        self.assertEqual(lsv.reclassify_closed_boards(by_url), ([], []))

    def test_other_hosts_are_never_reclassified(self) -> None:
        lsv._PINNACLE_API_OK = True
        bovada = "https://www.bovada.lv/sports/esports/league-of-legends/x"
        by_url = _verdicts(auth_required=bovada)
        self.assertEqual(lsv.reclassify_closed_boards(by_url), ([], []))
        self.assertEqual(by_url[bovada]["cause"], "auth_required")


class LivePathSmokeTests(unittest.TestCase):
    """Run main() end to end with the network stubbed out.

    The first version of the closed-board fix referenced `role_of` before `main()` assigned
    it, so the daily run died with NameError (run 40200770214) instead of producing a
    verdict, and no unit test noticed because they only exercised `classify()`. This smoke
    test walks the real live path — inventory fetch, control probe, per-URL crawl, page
    checks, table parse, report writing — against canned responses.
    """

    def setUp(self) -> None:
        import shutil
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = pathlib.Path(self.tmp.name)
        self._saved = (lsv.fetch, lsv.fetch_json, lsv.OUT_DIR, lsv.SITE,
                       lsv.urllib.request.urlopen, lsv._PINNACLE_API_OK,
                       dict(lsv.HOST_POLICY), dict(lsv.DEFAULT_POLICY))
        self.addCleanup(self._restore)

        data = json.loads((ROOT / "data" / "matches.json").read_text(encoding="utf-8"))
        self.matches = data["matches"]
        fixtures = [{"id": m["id"], "sport_alias": "lol"} for m in self.matches]

        def fake_fetch(url, **kw):
            if url == lsv.PINNACLE_CONTROL_URL:
                return {"url": url, "status": 200, "ok": True, "cause": "resolved"}
            if "arcadia.pinnacle.com/0.1/matchups/" in url:
                return {"url": url, "status": 401, "ok": False,
                        "cause": lsv.classify(url, 401, "HTTP 401")}
            return {"url": url, "status": 200, "ok": True, "cause": "resolved", "bytes": 10}

        def fake_fetch_json(url):
            if url == lsv.LIVE_FEED:
                return ({"url": url, "status": 200, "ok": True, "cause": "resolved"}, fixtures)
            return ({"url": url, "status": 200, "ok": True, "cause": "resolved"},
                    {"query": {"pages": {"1": {"title": "Some Page"}}}})

        table_html = (ROOT / "table.html").read_text(encoding="utf-8")

        class Resp:
            def __init__(self, body: str) -> None:
                self._body = body.encode("utf-8")
                self.status = 200
                self.headers = {"Content-Type": "text/html"}

            def read(self) -> bytes:
                return self._body

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        lsv.fetch = fake_fetch
        lsv.fetch_json = fake_fetch_json
        lsv.OUT_DIR = self.out
        lsv.SITE = "https://example.test/"
        lsv.urllib.request.urlopen = lambda req, timeout=60: Resp(table_html)
        lsv._PINNACLE_API_OK = False
        # the crawl sleeps per host by design (politeness). The transport is stubbed here,
        # so zero the delays: 241 Hotspawn cards at 1.1 s each would just make the test slow.
        lsv.DEFAULT_POLICY = {**lsv.DEFAULT_POLICY, "delay": 0.0, "retries": 0}
        lsv.HOST_POLICY = {host: {**pol, "delay": 0.0, "retries": 0}
                           for host, pol in lsv.HOST_POLICY.items()}

    def _restore(self) -> None:
        (lsv.fetch, lsv.fetch_json, lsv.OUT_DIR, lsv.SITE,
         lsv.urllib.request.urlopen, lsv._PINNACLE_API_OK,
         lsv.HOST_POLICY, lsv.DEFAULT_POLICY) = self._saved

    def test_live_path_completes_and_files_a_report(self) -> None:
        sys_argv = sys.argv
        sys.argv = ["live_source_verify.py"]
        try:
            rc = lsv.main()
        finally:
            sys.argv = sys_argv
        report = json.loads((self.out / "source_verify.json").read_text(encoding="utf-8"))
        self.assertEqual(rc, 0, [c for c in report["checks"] if not c["ok"]])
        self.assertTrue(report["passed"])
        self.assertEqual(report["rows"], len(self.matches))
        self.assertEqual(report["table_rows_rendered"], len(self.matches))
        # the closed Pinnacle boards are classified, disclosed, and not counted as rot
        closed = report.get("market_closed_links", [])
        self.assertTrue(closed, "expected the Pinnacle 401s to be classified as market_closed")
        self.assertTrue(all("arcadia.pinnacle.com" in u for u in closed))
        names = [c["name"] for c in report["checks"]]
        self.assertIn("links to settled bookmaker boards are disclosed (not counted as rot)", names)
        self.assertTrue(all(c["ok"] for c in report["checks"] if c["name"].startswith("no broken")))
        self.assertTrue((self.out / "source_verify.md").exists())
