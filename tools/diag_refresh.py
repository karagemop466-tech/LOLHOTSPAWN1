"""Run the canonical publisher sequence one command at a time and record what happened.

The canonical publisher is `.github/workflows/refresh.yml`; it wraps the whole sequence in
`set -euo pipefail`, so the first non-zero exit aborts the job and GitHub only reports "Run
pipeline (captured log) failed". This script reproduces the same sequence, in the same order,
without `set -e`, so the exact step that fails and its stderr are visible.

Output (committed by `.github/workflows/diag-refresh.yml`):

    data/diag/refresh_diag.json   one record per step: name, argv, exit code, duration, tail
    data/diag/refresh_diag.log    the same information as plain text

This script never writes a published page and never edits `data/matches.json`; it only runs the
existing tools and records their output. Nothing here invents a value.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "data", "diag")

# Exactly the sequence in .github/workflows/refresh.yml, in order.
STEPS = [
    ("unit tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]),
    ("collect", [sys.executable, "tools/collect.py"]),
    ("model", [sys.executable, "tools/model.py"]),
    ("report", [sys.executable, "tools/report.py"]),
    ("flags", [sys.executable, "tools/flags.py"]),
    ("site", [sys.executable, "tools/site.py"]),
    ("corroborate", [sys.executable, "tools/corroborate.py"]),
    ("verify", [sys.executable, "tools/verify.py"]),
]

TAIL_LINES = 60


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(name: str, argv: list[str]) -> dict:
    started = time.time()
    env = dict(os.environ)
    env.setdefault("PYTHONUNBUFFERED", "1")
    proc = subprocess.run(
        argv,
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=1800,
    )
    lines = (proc.stdout or "").splitlines()
    record = {
        "step": name,
        "argv": " ".join(argv[1:]),
        "exit_code": proc.returncode,
        "ok": proc.returncode == 0,
        "duration_s": round(time.time() - started, 1),
        "output_lines": len(lines),
        "tail": lines[-TAIL_LINES:],
        "logged_utc": utcnow(),
    }
    return record


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    records = []
    for name, argv in STEPS:
        print(f"=== {name}: {' '.join(argv)} ===", flush=True)
        try:
            record = run(name, argv)
        except Exception as exc:  # noqa: BLE001 - a crash is a result, not a reason to hide the run
            record = {
                "step": name,
                "argv": " ".join(argv[1:]),
                "exit_code": None,
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
                "logged_utc": utcnow(),
            }
        records.append(record)
        for line in record.get("tail", []):
            print(line, flush=True)
        print(f"--- {name} exit={record['exit_code']}", flush=True)
        if not record["ok"] and name in {"collect", "model"}:
            # Downstream steps consume the files these two write; running them on a broken
            # input would only produce a cascade of unrelated errors.
            print("stopping: a producer failed", flush=True)
            break

    payload = {
        "generated_utc": utcnow(),
        "runner": {
            "python": sys.version.split()[0],
            "platform": sys.platform,
            "github_run_id": os.environ.get("GITHUB_RUN_ID", ""),
            "github_sha": os.environ.get("GITHUB_SHA", ""),
            "github_workflow": os.environ.get("GITHUB_WORKFLOW", ""),
            "runner_name": os.environ.get("RUNNER_NAME", ""),
        },
        "steps": records,
        "first_failure": next((r["step"] for r in records if not r["ok"]), None),
    }
    with open(os.path.join(OUT_DIR, "refresh_diag.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)
        fh.write("\n")
    with open(os.path.join(OUT_DIR, "refresh_diag.log"), "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(f"=== {rec['step']} exit={rec['exit_code']} ({rec.get('duration_s','?')}s) ===\n")
            for line in rec.get("tail", []):
                fh.write(line + "\n")
            fh.write("\n")
    print(json.dumps({"first_failure": payload["first_failure"]}), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
