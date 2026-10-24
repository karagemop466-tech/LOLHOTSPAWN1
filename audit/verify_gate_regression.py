#!/usr/bin/env python3
"""Cross-pipeline coverage + freshness audit.

The canonical pipeline (`tools/`) and the secondary Node pipeline (`scripts/`) both fetch the Hotspawn
LoL fixtures API independently, on different cron schedules, and commit their raw snapshots side by
side:

    data/raw/hotspawn_lol.json            <- tools/collect.py    (canonical, published)
    data/node/raw/hotspawn_lol_fixtures.json <- scripts/collect.mjs (independent snapshot)

That is a free, already-running cross-check that nobody was reading. On 2026-10-24 it exposed a real
defect: `refresh-picks` had failed four scheduled runs in a row, so the published site was 23 h old
and was missing 20 live fixtures - including all eight of that day's Worlds cards. Nothing in the
existing gates could see it, because every gate only ever compares the site against the snapshot the
site itself built from.

This script makes the comparison explicit and prints it as a table. It is a *report*, not a publish
gate: a lag between two crons is normal, and the numbers are only meaningful next to the timestamps.
Exit code is 0 unless the published dataset cannot be read at all, so it is safe to run anywhere.

Usage:  python3 audit/verify_gate_regression.py [--max-age-hours N] [--json PATH]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANON = os.path.join(ROOT, "data", "raw", "hotspawn_lol.json")
CANON_DATASET = os.path.join(ROOT, "data", "matches.json")
NODE = os.path.join(ROOT, "data", "node", "raw", "hotspawn_lol_fixtures.json")


def load(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError) as exc:
        print(f"cannot read {os.path.relpath(path, ROOT)}: {exc}", file=sys.stderr)
        return None


def parse_utc(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def node_names(fixture):
    parts = fixture.get("participants") or []
    return [p.get("name") for p in parts]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-age-hours", type=float, default=8.0,
                    help="flag the published dataset as stale beyond this many hours (default 8, the "
                         "outer edge of the 4-8 h refresh window in the brief)")
    ap.add_argument("--json", dest="json_out", default=None, help="also write the report here")
    args = ap.parse_args()

    dataset = load(CANON_DATASET)
    if not dataset:
        return 1
    published = {str(m.get("id")): m for m in (dataset.get("matches") or [])}

    node = load(NODE)
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "published_dataset": os.path.relpath(CANON_DATASET, ROOT),
        "published_inventory_fetched_utc": dataset.get("inventory_fetched_utc"),
        "published_rows": len(published),
        "independent_snapshot": os.path.relpath(NODE, ROOT) if node else None,
    }

    now = datetime.now(timezone.utc)
    fetched = parse_utc(dataset.get("inventory_fetched_utc"))
    if fetched:
        age_h = (now - fetched).total_seconds() / 3600.0
        report["published_age_hours"] = round(age_h, 2)
        report["stale"] = age_h > args.max_age_hours
        print(f"published inventory  {dataset.get('inventory_fetched_utc')}  age {age_h:.1f} h "
              f"{'STALE (> %.0f h)' % args.max_age_hours if report['stale'] else 'fresh'}")
    else:
        report["published_age_hours"] = None
        report["stale"] = None
        print("published inventory  <no timestamp>")

    if not node:
        report["comparison"] = "unavailable"
        print("no independent snapshot to compare against")
        print(json.dumps(report, indent=1) if not args.json_out else "")
        if args.json_out:
            with open(args.json_out, "w", encoding="utf-8") as fh:
                json.dump(report, fh, indent=1)
        return 0

    live = {str(f["id"]): f for f in (node.get("fixtures") or []) if f.get("status") == "scheduled"}
    missing = sorted(set(live) - set(published))     # on Hotspawn now, not on our site
    ghost = sorted(set(published) - set(live))       # on our site, no longer on Hotspawn
    report["independent_snapshot_fetched_utc"] = node.get("fetched_at")
    report["live_scheduled"] = len(live)
    report["missing_from_published"] = [
        {"id": i, "competition": live[i].get("competition_name"),
         "teams": " vs ".join(n for n in node_names(live[i]) if n),
         "start_utc": live[i].get("scheduled_start_time")} for i in missing]
    report["no_longer_on_hotspawn"] = [
        {"id": i, "competition": published[i].get("competition"),
         "teams": f'{published[i]["team0"]["name"]} vs {published[i]["team1"]["name"]}'} for i in ghost]
    report["missing_by_competition"] = dict(Counter(
        live[i].get("competition_name") for i in missing).most_common())

    print(f"independent snapshot {node.get('fetched_at')}  scheduled {len(live)}")
    print(f"on Hotspawn but MISSING from the published site: {len(missing)}")
    for row in report["missing_from_published"]:
        print(f"  + {row['id']}  {row['competition']} | {row['teams']}")
    print(f"on the published site but NO LONGER on Hotspawn: {len(ghost)}")
    for row in report["no_longer_on_hotspawn"]:
        print(f"  - {row['id']}  {row['competition']} | {row['teams']}")

    # every published row must still carry a pick - the coverage claim the brief asks for
    no_pick = [i for i, m in published.items() if not (m.get("pick") or {}).get("team")]
    report["published_rows_without_a_pick"] = no_pick
    print(f"published rows without a pick: {len(no_pick)} {no_pick[:5]}")

    verdict = "OK" if not missing and not report.get("stale") and not no_pick else "DRIFT"
    report["verdict"] = verdict
    print(f"verdict: {verdict}")

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=1)
        print(f"wrote {os.path.relpath(args.json_out, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
