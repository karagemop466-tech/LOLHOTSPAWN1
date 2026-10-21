"""Join Hotspawn's LoL pick'em match list with external market prices.

Output (all under data/):
  matches.json    one record per Hotspawn match: teams, kickoff, tier, pick,
                  probability, the exact quotes it was built from, or the reason
                  it could not be priced.
  picks.csv       flat table of resolved picks (for spreadsheets).
  unresolved.json matches with no external market + the limitation code.
  quotes.json     every raw two-way quote pulled this run.
  sources.json    per-source fetch status (ok / empty / error + message).
  meta.json       run timestamp, counts, pipeline version.

Rules baked in here (see METHODOLOGY.md):
  * Only external two-way prices ever produce a probability. Hotspawn crowd
    percentages are stored for display only and are never mixed in.
  * A pair of team names must match on both sides (normalised equality, token
    containment, or - when names differ - an unambiguous kickoff-time match).
  * Every quote is de-vigged proportionally before being combined (median).
  * If no external price exists, the match is reported as unresolved with a
    machine-readable reason instead of inventing a number.
"""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timedelta, timezone

import hotspawn
import markets
from common import (devig_two_way, iso, median, name_similarity, norm_team,
                    now_utc, pct)

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
VERSION = "1.0.0"


def _parse(ts):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _side_match(a: str, b: str) -> str:
    """'exact' when normalised names are equal, 'variant' when one contains the other."""
    if norm_team(a) == norm_team(b):
        return "exact"
    sim = name_similarity(a, b)
    return "variant" if sim >= 0.85 else "none"


def pair_quotes(match: dict, quotes: list[dict]) -> list[dict]:
    """Quotes that describe this match, oriented so that home == team1."""
    t1, t2 = match["team1"]["name"], match["team2"]["name"]
    hs_start = _parse(match["start_utc"])
    found = []
    for q in quotes:
        s1, s2 = _side_match(t1, q["home"]), _side_match(t2, q["away"])
        reversed_ = False
        if s1 == "none" or s2 == "none":
            s1r, s2r = _side_match(t1, q["away"]), _side_match(t2, q["home"])
            if s1r != "none" and s2r != "none":
                s1, s2, reversed_ = s1r, s2r, True
        if s1 == "none" or s2 == "none":
            continue
        # Kickoff sanity check (48h) when both sides carry a timestamp.
        qs = _parse(q.get("start_utc"))
        if hs_start and qs:
            delta = abs((hs_start - qs).total_seconds())
            if delta > 48 * 3600:
                continue
        p_home = q["implied_home"] if not reversed_ else q["implied_away"]
        p_away = q["implied_away"] if not reversed_ else q["implied_home"]
        p1, p2 = devig_two_way(p_home, p_away)
        names = ("exact" if s1 == "exact" and s2 == "exact" else "variant")
        found.append({
            "book": q["book"],
            "book_key": q["book_key"],
            "kind": q["kind"],
            "url": q["url"],
            "market": q.get("market"),
            "home": q["home"],
            "away": q["away"],
            "decimal_team1": q["decimal_home"] if not reversed_ else q["decimal_away"],
            "decimal_team2": q["decimal_away"] if not reversed_ else q["decimal_home"],
            "prob_team1_raw": round(p_home, 5),
            "prob_team1": round(p1, 5),
            "prob_team2": round(p2, 5),
            "overround": round(p_home + p_away - 1, 5),
            "name_match": names,
            "reversed": reversed_,
            "start_utc": q.get("start_utc"),
            "volume_usd": q.get("volume_usd"),
        })
    return found


def build() -> dict:
    hs = hotspawn.fetch_matches()
    mk = markets.collect_all()
    all_quotes = [q for s in mk["sources"] for q in s["quotes"]]

    matches = []
    for m in hs["matches"]:
        qs = pair_quotes(m, all_quotes)
        probs = [q["prob_team1"] for q in qs]
        record = {
            "hotspawn_id": m["hotspawn_id"],
            "tournament": m["tournament"],
            "competition_id": m["competition_id"],
            "tier": m["tier"] or "unrated",
            "stage": m["stage"] or None,
            "start_utc": m["start_utc"],
            "best_of": m["best_of"],
            "offered_points": m["offered_points"],
            "team1": m["team1"],
            "team2": m["team2"],
            "hotspawn_url": m["hotspawn_url"],
            "quotes": qs,
            "sources_used": sorted({q["book"] for q in qs}),
        }

        if qs:
            p1 = median(probs)
            dispersion = round(max(probs) - min(probs), 4)
            pick_team1 = p1 >= 0.5
            prob = p1 if pick_team1 else 1 - p1
            if len(qs) >= 2 and dispersion <= 0.05:
                conf = "high"
            elif len(qs) >= 2 and dispersion <= 0.12:
                conf = "medium"
            elif len(qs) == 1 and qs[0]["kind"] == "sportsbook":
                conf = "medium"
            else:
                conf = "low"
            record.update({
                "status": "resolved",
                "prob_team1": round(p1, 4),
                "prob_team2": round(1 - p1, 4),
                "pick": {
                    "team": m["team1"]["name"] if pick_team1 else m["team2"]["name"],
                    "side": "team1" if pick_team1 else "team2",
                    "probability": round(prob, 4),
                    "probability_display": pct(prob),
                    "basis": "external_market",
                    "confidence": conf,
                    "dispersion": dispersion,
                    "source_count": len(qs),
                },
                "unresolved_reason": None,
            })
        else:
            record.update({
                "status": "unresolved",
                "prob_team1": None,
                "prob_team2": None,
                "pick": None,
                "unresolved_reason": "NO_EXTERNAL_MARKET",
            })
        matches.append(record)

    matches.sort(key=lambda x: (x["start_utc"] or "9999", x["tournament"] or "",
                                x["team1"]["name"] or ""))

    resolved = [m for m in matches if m["status"] == "resolved"]
    unresolved = [m for m in matches if m["status"] == "unresolved"]

    tournaments = {}
    for m in matches:
        t = tournaments.setdefault(m["tournament"], {
            "tournament": m["tournament"], "tier": m["tier"], "matches": 0,
            "resolved": 0, "unresolved": 0,
        })
        t["matches"] += 1
        t["resolved" if m["status"] == "resolved" else "unresolved"] += 1

    source_status = [{
        "book": s["book"], "book_key": s["book_key"], "kind": s["kind"],
        "url": s["url"], "status": s["status"], "error": s.get("error"),
        "quotes": len(s.get("quotes") or []),
    } for s in mk["sources"]]

    meta = {
        "pipeline_version": VERSION,
        "generated_at": iso(now_utc()),
        "hotspawn_source": hs["source"],
        "hotspawn_retrieved_at": hs["retrieved_at"],
        "markets_retrieved_at": mk["retrieved_at"],
        "counts": {
            "matches": len(matches),
            "resolved": len(resolved),
            "unresolved": len(unresolved),
            "tournaments": len(tournaments),
            "quotes": len(all_quotes),
        },
        "sources": source_status,
    }

    os.makedirs(OUT_DIR, exist_ok=True)
    _write_json("matches.json", {"meta": meta, "matches": matches})
    _write_json("unresolved.json", {"meta": meta, "matches": unresolved})
    _write_json("quotes.json", {"retrieved_at": mk["retrieved_at"], "sources": mk["sources"]})
    _write_json("sources.json", meta["sources"])
    _write_json("tournaments.json", sorted(tournaments.values(),
                                           key=lambda x: (-x["matches"], x["tournament"])))
    _write_json("meta.json", meta)
    _write_csv(matches)
    return meta


def _write_json(name, payload):
    with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1, ensure_ascii=False)


def _write_csv(matches):
    path = os.path.join(OUT_DIR, "picks.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["hotspawn_id", "start_utc", "tournament", "tier", "team1", "team2",
                    "status", "pick", "pick_probability", "prob_team1", "prob_team2",
                    "basis", "confidence", "sources", "unresolved_reason", "hotspawn_url"])
        for m in matches:
            p = m.get("pick") or {}
            w.writerow([m["hotspawn_id"], m["start_utc"], m["tournament"], m["tier"],
                        m["team1"]["name"], m["team2"]["name"], m["status"],
                        p.get("team", ""), p.get("probability", ""),
                        m["prob_team1"] if m["prob_team1"] is not None else "",
                        m["prob_team2"] if m["prob_team2"] is not None else "",
                        p.get("basis", ""), p.get("confidence", ""),
                        "|".join(m["sources_used"]), m["unresolved_reason"] or "",
                        m["hotspawn_url"] or ""])


if __name__ == "__main__":
    print(json.dumps(build(), indent=1))
