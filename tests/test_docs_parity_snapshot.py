#!/usr/bin/env python3
"""Regression test for Cross-Scope Request R1: docs/ parity snapshot tracking."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestDocsParitySnapshot(unittest.TestCase):
    def test_canonical_snapshot_file_written_and_parity_passes_across_inter_cron_skew(self):
        snap_path = ROOT / "docs" / "data" / "canonical_snapshot.json"
        matches_path = ROOT / "data" / "matches.json"
        parity_receipt = ROOT / "audit" / "9f16f9ad" / "docs_parity.json"
        self.assertTrue(snap_path.exists(), "docs/data/canonical_snapshot.json must exist")
        snap = json.loads(snap_path.read_text())
        self.assertTrue(snap.get("generated_utc"))
        self.assertGreater(len(snap.get("matches") or []), 0)

        orig_matches = matches_path.read_bytes()
        orig_receipt = parity_receipt.read_bytes() if parity_receipt.exists() else None
        try:
            mutated = json.loads(orig_matches.decode("utf-8"))
            mutated["generated_utc"] = "2099-01-01T00:00:00Z"
            if mutated.get("matches"):
                for r in mutated["matches"]:
                    if r.get("p0") is not None and (r.get("pick") or {}).get("probability") is not None:
                        r["p0"] = 0.5432
                        r["p1"] = 0.4568
                        r["pick"]["probability"] = 0.5432
                        r["pick"]["other_probability"] = 0.4568
                        break
            matches_path.write_text(json.dumps(mutated, indent=1) + "\n", encoding="utf-8")

            proc = subprocess.run(
                [sys.executable, str(ROOT / "audit" / "verify_docs_parity.py")],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + "\n" + proc.stderr)
            self.assertIn("WARN      canonical snapshot advanced since docs build", proc.stdout)
            self.assertIn("ALL DOCS-PARITY CHECKS PASS", proc.stdout)
        finally:
            matches_path.write_bytes(orig_matches)
            if orig_receipt is not None:
                parity_receipt.write_bytes(orig_receipt)


if __name__ == "__main__":
    unittest.main()
