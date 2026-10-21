#!/usr/bin/env python3
"""Print a compact diagnostic report of the built dataset (used during development)."""
import json, os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DATA, iso, load_json, now_utc, save_json

d = load_json(os.path.join(DATA, "matches.json")) or {}
rows = d.get("matches") or []
rep = load_json(os.path.join(DATA, "matching_report.json")) or {}
out = {
    "generated_utc": iso(now_utc()),
    "total": len(rows),
    "counts": d.get("counts"),
    "per_competition": {},
    "non_exact_joins": (rep.get("non_exact_joins") or [])[:200],
    "unresolved": [],
    "provisional": [],
    "priced": [],
}
for r in rows:
    c = out["per_competition"].setdefault(r["competition"], collections.Counter())
    c[r["method"]] += 1
for r in rows:
    if r["method"] == "unresolved":
        out["unresolved"].append({"id": r["id"], "competition": r["competition"],
                                  "teams": [r["team0"]["name"], r["team1"]["name"]],
                                  "flags": r["flags"], "basis": r["basis"],
                                  "start": r["start_utc"]})
    if r["method"] == "provisional":
        out["provisional"].append({"id": r["id"], "competition": r["competition"],
                                   "teams": [r["team0"]["name"], r["team1"]["name"]],
                                   "p0": r["p0"], "flags": r["flags"]})
    if r["method"] == "market":
        out["priced"].append({"id": r["id"], "competition": r["competition"],
                              "teams": [r["team0"]["name"], r["team1"]["name"]],
                              "p0": r["p0"], "decimal": r["market"]["decimal"],
                              "start": r["start_utc"]})
out["per_competition"] = {k: dict(v) for k, v in out["per_competition"].items()}
save_json(os.path.join(DATA, "report.json"), out)
print(json.dumps({k: out[k] for k in ("total", "counts", "per_competition")}, indent=1)[:2500])
print("\nUNRESOLVED", len(out["unresolved"]))
for u in out["unresolved"][:20]:
    print(" ", u["competition"], "|", " vs ".join(u["teams"]), "|", u["basis"][:80])
print("\nNON-EXACT JOINS", rep.get("non_exact_count"))
for j in out["non_exact_joins"][:40]:
    print(" ", j["method"], j["score"], "|", j["team"], "->", j["resolved"])
print("\nPRICED", len(out["priced"]))
for p in out["priced"][:10]:
    print(" ", p["competition"], "|", p["teams"], p["p0"], p["decimal"])
