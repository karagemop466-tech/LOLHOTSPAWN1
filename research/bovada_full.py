#!/usr/bin/env python3
"""Check whether Bovada's *unfiltered* LoL coupon carries more match moneylines than
the filtered `marketFilterId=def&preMatchOnly=true` feed used in production.

The production collector requests a filtered coupon (~11 KB). The unfiltered coupon is
~215 KB. If the extra payload contains additional League of Legends series with a
two-sided moneyline, that is real, verifiable market coverage we are currently missing.

Output: research/bovada_full.json (compact: one row per LoL moneyline found) and a
console summary. No picks are written here.
"""
from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
from common import get_json, http_get, iso, now_utc, save_json, log  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "research", "bovada_full.json")

URLS = {
    "filtered": ("https://www.bovada.lv/services/sports/event/coupon/events/A/description/"
                 "esports/league-of-legends?marketFilterId=def&preMatchOnly=true&lang=en"),
    "unfiltered": ("https://www.bovada.lv/services/sports/event/coupon/events/A/description/"
                   "esports/league-of-legends"),
    "prematch": ("https://www.bovada.lv/services/sports/event/coupon/events/A/description/"
                 "esports/league-of-legends?preMatchOnly=true"),
}


def walk_events(node, path=None, out=None):
    """Bovada nests events under path[] groups; collect dicts that look like events."""
    if path is None:
        path = []
    if out is None:
        out = []
    if isinstance(node, list):
        for item in node:
            walk_events(item, path, out)
        return out
    if not isinstance(node, dict):
        return out
    if "path" in node and isinstance(node["path"], list):
        labels = [p.get("description") for p in node["path"] if isinstance(p, dict)]
        if "events" in node:
            for ev in node.get("events") or []:
                ev = dict(ev)
                ev["_group"] = labels
                out.append(ev)
    return out


def moneyline_from(ev: dict) -> dict | None:
    for dg in ev.get("displayGroups") or []:
        for mk in dg.get("markets") or []:
            desc = (mk.get("description") or "").lower()
            if "money" not in desc and "head to head" not in desc:
                continue
            outs = [o for o in mk.get("outcomes") or [] if o.get("price", {}).get("decimal")]
            if len(outs) != 2:
                continue
            return {
                "description": ev.get("description"),
                "start": ev.get("startTime"),
                "link": ev.get("link"),
                "market": mk.get("description"),
                "outcomes": [{"name": o.get("description"),
                              "decimal": o.get("price", {}).get("decimal")} for o in outs],
                "group": ev.get("_group"),
            }
    return None


def main() -> None:
    rows, summary = [], {}
    for label, url in URLS.items():
        st, payload, err = get_json(url, timeout=45, retries=1)
        events = walk_events(payload) if st == 200 else []
        found = [m for m in (moneyline_from(e) for e in events) if m]
        summary[label] = {"status": st, "bytes": len(json.dumps(payload or {})),
                          "events": len(events), "moneylines": len(found), "error": err}
        for m in found:
            m["feed"] = label
            rows.append(m)
        log(f"{label}: status={st} events={len(events)} moneylines={len(found)}")

    # de-duplicate across feeds by description + start
    seen, unique = set(), []
    for m in rows:
        key = (m["description"], str(m["start"])[:16])
        if key in seen:
            continue
        seen.add(key)
        unique.append(m)

    save_json(OUT, {"checked_utc": iso(now_utc()), "feeds": summary, "moneylines": unique})
    print(json.dumps({"feeds": summary, "unique_moneylines": len(unique)}, indent=1))
    for m in unique:
        print(" ", m["start"], "|", m["description"], "|", m["outcomes"], "|", m.get("group"))


if __name__ == "__main__":
    main()
