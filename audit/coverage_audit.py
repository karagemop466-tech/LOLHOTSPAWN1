#!/usr/bin/env python3
"""
coverage_audit.py — session 7f76a03b (V1): live full-coverage audit.

Fetches the LIVE Hotspawn LoL pick'em inventory (the same public fixtures API
the pipeline collects from) and checks, line by line, that:

  1  every live scheduled fixture has a row in the canonical dataset
     (data/matches.json) served by the root dashboard
  2  every canonical row carries a probability pair that sums to 100%, or is
     explicitly listed as unresolved (no invented values)
  3  every canonical row links its Hotspawn match card
  4  every live scheduled fixture is represented in the docs/ dashboard
     (data/node/picks.json: picked, or explicitly unresolved/locked/stale)
  5  freshness: how many fixtures are new/changed since the last collect

Writes audit/coverage_report.json. Exit code 0 = report written (a freshness
gap between 4-8h refreshes is expected and is reported, not fatal);
exit 2 = a structural coverage hole (live fixture missing from BOTH datasets
with no row at all) so CI can surface it loudly.
"""
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIVE_URL = ("https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures"
            "?sport_alias=lol&status=scheduled&tenantId=1")


def fetch_live():
    req = urllib.request.Request(LIVE_URL, headers={"User-Agent": "coverage-audit/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def main():
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    live = fetch_live()
    live_by_id = {str(f["id"]): f for f in live}

    snap = json.loads((ROOT / "data" / "raw" / "hotspawn_lol.json").read_text())
    snap_ids = {str(f["id"]) for f in snap["fixtures"]}

    canon = json.loads((ROOT / "data" / "matches.json").read_text())
    canon_by_id = {str(m["id"]): m for m in canon["matches"]}

    docs = json.loads((ROOT / "data" / "node" / "picks.json").read_text())
    docs_by_id = {str(m["id"]): m for m in docs["matches"]}

    report = {"audit_utc": now, "live_url": LIVE_URL,
              "collect_snapshot_utc": snap.get("fetched_utc") or snap.get("fetched_at"),
              "canonical_generated_utc": canon.get("generated_utc"),
              "docs_generated_utc": docs.get("summary", {}).get("generated_at")}

    # 1 — every live fixture has a canonical row
    missing_canon = sorted(set(live_by_id) - set(canon_by_id))
    extra_canon = sorted(set(canon_by_id) - set(live_by_id))
    report["live_total"] = len(live_by_id)
    report["canonical_total"] = len(canon_by_id)
    report["live_missing_from_canonical"] = missing_canon
    report["canonical_not_live_scheduled"] = extra_canon  # stale/freshness drift, not a hole
    report["new_since_collect"] = sorted(set(live_by_id) - snap_ids)

    # 2/3 — canonical row integrity: probability pair or explicit unresolved + source link
    no_prob, no_link, bad_sum = [], [], []
    for fid, m in canon_by_id.items():
        p0, p1 = m.get("p0"), m.get("p1")
        if p0 is None or p1 is None:
            if m.get("method") != "unresolved":
                no_prob.append(fid)
        elif abs(p0 + p1 - 1.0) > 0.002:
            bad_sum.append(fid)
        if not m.get("hotspawn_url"):
            no_link.append(fid)
    report["canonical_rows_without_probability_or_unresolved"] = no_prob
    report["canonical_rows_bad_sum"] = bad_sum
    report["canonical_rows_without_hotspawn_link"] = no_link

    # 4 — every live fixture represented on the docs dashboard
    active_states = {"open", "locked", "live", "stale"}
    missing_docs = []
    for fid in live_by_id:
        m = docs_by_id.get(fid)
        if m is None:
            missing_docs.append(fid)
            continue
        if m["state"] not in active_states and m["state"] not in {"ended", "forfeited", "cancelled"}:
            missing_docs.append(fid + f" (state={m['state']})")
    report["live_missing_from_docs_dataset"] = missing_docs
    report["docs_total"] = len(docs_by_id)

    # hard structural hole: live fixture missing from BOTH datasets
    structural = sorted(set(live_by_id) - set(canon_by_id) - set(docs_by_id))

    out = ROOT / "audit" / "coverage_report.json"
    out.write_text(json.dumps(report, indent=1))

    print(f"audit_utc                {now}")
    print(f"live scheduled fixtures  {len(live_by_id)}")
    print(f"canonical rows           {len(canon_by_id)}  (snapshot {report['collect_snapshot_utc']})")
    print(f"docs rows                {len(docs_by_id)}  (built {report['docs_generated_utc']})")
    print(f"live missing canonical   {len(missing_canon)} {missing_canon[:8]}")
    print(f"new since last collect   {len(report['new_since_collect'])} {report['new_since_collect'][:8]}")
    print(f"canonical no-prob        {len(no_prob)} {no_prob[:8]}")
    print(f"canonical bad sum        {len(bad_sum)}")
    print(f"canonical no link        {len(no_link)}")
    print(f"live missing docs        {len(missing_docs)} {missing_docs[:8]}")
    print(f"structural holes         {len(structural)} {structural[:8]}")
    print(f"report -> {out.relative_to(ROOT)}")
    return 2 if structural else 0


if __name__ == "__main__":
    sys.exit(main())
