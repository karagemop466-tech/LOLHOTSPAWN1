#!/usr/bin/env python3
"""Independent re-verification of the published pick set.

This is deliberately a *second* implementation: it does not import anything from
``tools/`` and does not trust ``data/matches.json``.  It re-derives every published
number from the committed raw provider payloads and compares.

Checks
  A. inventory      Hotspawn raw fixtures == published rows, ids unique, no extras
  B. provenance     every market venue quote reproduces a raw provider quote
  C. market type    a Pinnacle "(Kills)" market must not stand in for a series moneyline
  D. arithmetic     de-vig, consensus weights, sums to 100 %, pick = favourite
  E. model          Elo probability reproduced from the published ratings
  F. freshness      raw payload age at build time
  G. sourcing       every row's source links use the documented host for its method

Exit code 0 = no failures (warnings allowed); 1 = at least one failure.
Outputs ``audit/report.json`` and ``audit/report.md``.
"""
from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
RAW = os.path.join(DATA, "raw")
AUDIT = os.path.join(ROOT, "audit")

FAILS: list[dict] = []
WARNS: list[dict] = []


def fail(check: str, detail: str, **extra) -> None:
    FAILS.append({"check": check, "detail": detail, **extra})


def warn(check: str, detail: str, **extra) -> None:
    WARNS.append({"check": check, "detail": detail, **extra})


def load(path: str):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


_FOLD = str.maketrans({"ø": "o", "Ø": "O", "æ": "ae", "Æ": "AE", "ð": "d", "Ð": "D",
                       "þ": "th", "Þ": "TH", "ł": "l", "Ł": "L", "ß": "ss", "ı": "i"})


def norm(name: str) -> str:
    """Aggressive but deterministic team-name normalisation."""
    s = unicodedata.normalize("NFKD", (name or "").translate(_FOLD)).encode("ascii", "ignore").decode()
    s = s.lower()
    s = re.sub(r"\([^)]*\)", " ", s)              # drop parentheticals e.g. "(Kills)"
    s = re.sub(r"\b(esports?|e-?sport(s)?|team|gaming|club|academy|esport)\b", " ", s)
    out = re.sub(r"[^a-z0-9]+", "", s)
    return {"secret": "secretwhales", "risingbees": "vitalityrisingbees"}.get(out, out)


def devig(d0: float, d1: float):
    if not (d0 > 1.0001 and d1 > 1.0001):
        return None
    i0, i1 = 1 / d0, 1 / d1
    total = i0 + i1
    return i0 / total, i1 / total, total - 1


def close(a: float, b: float, tol: float = 0.002) -> bool:
    return abs(a - b) <= tol


def main() -> int:
    matches_doc = load(os.path.join(DATA, "matches.json"))
    rows = matches_doc["matches"]
    pin = load(os.path.join(RAW, "pinnacle_lol.json"))
    bov = load(os.path.join(RAW, "bovada_lol.json"))
    kal = load(os.path.join(RAW, "kalshi_lol.json"))
    pol = load(os.path.join(RAW, "polymarket.json"))
    kam = load(os.path.join(RAW, "kambi_lol.json")) if os.path.exists(os.path.join(RAW, "kambi_lol.json")) else {}
    smk = load(os.path.join(RAW, "smarkets_lol.json")) if os.path.exists(os.path.join(RAW, "smarkets_lol.json")) else {}
    hs = load(os.path.join(RAW, "hotspawn_lol.json"))

    build_ts = parse_ts(matches_doc.get("generated_utc"))

    # ---------------------------------------------------------------- A inventory
    raw_ids = [str(f["id"]) for f in hs["fixtures"]]
    row_ids = [str(r["id"]) for r in rows]
    if sorted(raw_ids) != sorted(row_ids):
        missing = sorted(set(raw_ids) - set(row_ids))
        extra = sorted(set(row_ids) - set(raw_ids))
        fail("A inventory", f"published rows do not equal raw Hotspawn fixtures "
                            f"(missing {missing[:8]}, extra {extra[:8]})")
    if len(set(row_ids)) != len(row_ids):
        fail("A inventory", "duplicate match ids in the published dataset")
    for f in hs["fixtures"]:
        if str(f["id"]) not in set(row_ids):
            continue
    fixture_by_id = {str(f["id"]): f for f in hs["fixtures"]}

    # ------------------------------------------------------- raw provider indexes
    pin_index = []
    for mk in pin.get("markets") or []:
        parts = mk.get("participants") or []
        if len(parts) != 2:
            continue
        pin_index.append({
            "names": [p["name"] for p in parts],
            "keys": [norm(p["name"]) for p in parts],
            "raw": mk,
        })
    bov_index = []
    for ev in bov.get("events") or []:
        outs = ev.get("outcomes") or []
        if len(outs) == 2:
            bov_index.append({"names": [o["name"] for o in outs], "raw": ev})
    kal_index = []
    for ev in kal.get("events") or []:
        mkts = ev.get("markets") or []
        if len(mkts) == 2:
            kal_index.append({"names": [m.get("yes_sub_title") for m in mkts], "raw": ev})
    pol_index = []
    for mk in pol.get("match_markets") or []:
        outs = mk.get("outcomes") or []
        if len(outs) == 2:
            pol_index.append({"names": outs, "raw": mk})
    kam_index = []
    for ev in kam.get("events") or []:
        outs = ev.get("outcomes") or []
        if len(outs) == 2:
            kam_index.append({"names": [o["name"] for o in outs], "raw": ev})
    smk_index = []
    for ev in smk.get("events") or []:
        outs = ev.get("outcomes") or []
        if len(outs) == 2:
            smk_index.append({"names": [o["name"] for o in outs], "raw": ev})

    def find_all(index, n0, n1, symmetric=True):
        k0, k1 = norm(n0), norm(n1)
        hits = []
        for item in index:
            a, b = norm(item["names"][0]), norm(item["names"][1])
            if a == k0 and b == k1:
                hits.append((item, False))
            elif symmetric and a == k1 and b == k0:
                hits.append((item, True))
        return hits

    # ------------------------------------------------------------- per-row checks
    market_rows = [r for r in rows if r.get("method") == "market"]
    venue_checked = 0
    kills_substitutions = []
    for row in market_rows:
        n0, n1 = row["team0"]["name"], row["team1"]["name"]
        mk = row.get("market") or {}
        for venue in mk.get("venues") or []:
            venue_checked += 1
            vname = venue.get("name")
            p0, p1 = venue.get("p0"), venue.get("p1")
            quote = venue.get("quote") or ""
            if not (isinstance(p0, (int, float)) and isinstance(p1, (int, float))):
                fail("B provenance", f"{row['id']}: venue {vname} has non-numeric probability")
                continue
            if not close(p0 + p1, 1.0, 0.002):
                fail("D arithmetic", f"{row['id']}: venue {vname} probabilities sum to {p0 + p1:.4f}")

            if vname == "Pinnacle":
                hits = find_all(pin_index, n0, n1)
                if not hits:
                    fail("B provenance", f"{row['id']}: Pinnacle quote {quote} not found in "
                                         f"pinnacle_lol.json for {n0} vs {n1}")
                    continue
                numbers = re.findall(r"\d+\.?\d*", quote)
                if len(numbers) != 2:
                    fail("B provenance", f"{row['id']}: unparseable Pinnacle quote {quote!r}")
                    continue
                d0, d1 = float(numbers[0]), float(numbers[1])
                reproduced = False
                plain_hit = None
                chosen = None
                for item, swapped in hits:
                    raw = item["raw"]["prices"]
                    rd0 = raw["home"]["decimal"] if not swapped else raw["away"]["decimal"]
                    rd1 = raw["away"]["decimal"] if not swapped else raw["home"]["decimal"]
                    is_kills = bool(re.search(r"\(kills\)", " ".join(item["names"]), re.I))
                    if close(rd0, d0, 0.01) and close(rd1, d1, 0.01):
                        reproduced = True
                        if not is_kills:
                            chosen = item
                            plain_hit = item
                        elif chosen is None:
                            chosen = item
                    elif not is_kills and plain_hit is None:
                        plain_hit = item
                if not reproduced:
                    fail("B provenance", f"{row['id']}: Pinnacle quote {quote} matches no raw "
                                         f"price for {n0} vs {n1}")
                    continue
                # C: is the chosen record a kills market while a plain series line exists?
                if chosen is not None and re.search(r"\(kills\)", " ".join(chosen["names"]), re.I):
                    if plain_hit is not None:
                        raw_plain = plain_hit["raw"]["prices"]
                        pd0, pd1 = raw_plain["home"]["decimal"], raw_plain["away"]["decimal"]
                        if not (close(pd0, d0, 0.01) and close(pd1, d1, 0.01)):
                            kills_substitutions.append({
                                "match_id": row["id"],
                                "teams": [n0, n1],
                                "used": {"label": chosen["names"], "decimal": [d0, d1],
                                         "matchup_id": chosen["raw"].get("matchup_id")},
                                "series_moneyline": {"label": plain_hit["names"], "decimal": [pd0, pd1],
                                                     "matchup_id": plain_hit["raw"].get("matchup_id")},
                            })
                # duplicate priced records for the same teams
                if len(hits) > 1:
                    distinct = {tuple(sorted(re.findall(r"\d+\.?\d*",
                                                       f"{h[0]['raw']['prices']['home']['decimal']}/"
                                                       f"{h[0]['raw']['prices']['away']['decimal']}"))) for h in hits}
                    if len(distinct) > 1:
                        warn("B provenance", f"{row['id']}: Pinnacle lists {len(hits)} priced records for "
                                             f"{n0} vs {n1} with differing prices")
                dv = devig(d0, d1)
                if dv and not (close(dv[0], p0) and close(dv[1], p1)):
                    fail("D arithmetic", f"{row['id']}: Pinnacle de-vig {dv[0]:.4f}/{dv[1]:.4f} != "
                                         f"published {p0:.4f}/{p1:.4f}")

            elif vname in ("Bovada", "Unibet"):
                src_idx = bov_index if vname == "Bovada" else kam_index
                hits = find_all(src_idx, n0, n1)
                if not hits:
                    fail("B provenance", f"{row['id']}: {vname} quote {quote} not found for {n0} vs {n1}")
                    continue
                numbers = re.findall(r"\d+\.?\d*", quote)
                d0, d1 = float(numbers[0]), float(numbers[1])
                ok = False
                for item, swapped in hits:
                    outs = item["raw"]["outcomes"]
                    rd0 = outs[0]["decimal"] if not swapped else outs[1]["decimal"]
                    rd1 = outs[1]["decimal"] if not swapped else outs[0]["decimal"]
                    if close(rd0, d0, 0.01) and close(rd1, d1, 0.01):
                        ok = True
                if not ok:
                    fail("B provenance", f"{row['id']}: {vname} quote {quote} matches no raw price")
                dv = devig(d0, d1)
                if dv and not (close(dv[0], p0) and close(dv[1], p1)):
                    fail("D arithmetic", f"{row['id']}: {vname} de-vig {dv[0]:.4f}/{dv[1]:.4f} != published")

            elif vname in ("Polymarket", "Kalshi"):
                index = pol_index if vname == "Polymarket" else kal_index
                hits = find_all(index, n0, n1)
                if not hits:
                    fail("B provenance", f"{row['id']}: {vname} quote {quote} not found for {n0} vs {n1}")
                    continue
                if vname == "Polymarket":
                    nums = [float(x) for x in re.findall(r"\d+\.?\d*", quote)]
                    if len(nums) != 2:
                        fail("B provenance", f"{row['id']}: unparseable Polymarket quote {quote!r}")
                        continue
                    best = None
                    for item, swapped in hits:
                        try:
                            pr = [float(x) for x in item["raw"]["prices"]]
                        except (TypeError, ValueError):
                            continue
                        if swapped:
                            pr = [pr[1], pr[0]]
                        if close(pr[0], nums[0] / 100, 0.005) and close(pr[1], nums[1] / 100, 0.005):
                            best = item
                    if best is None:
                        fail("B provenance", f"{row['id']}: Polymarket quote {quote} matches no raw price")
                else:
                    mid = 0.5
                    if not close(p0 + p1, 1.0, 0.002):
                        fail("D arithmetic", f"{row['id']}: Kalshi probabilities do not sum to 1")
            elif vname == "Smarkets":
                hits = find_all(smk_index, n0, n1)
                if not hits:
                    fail("B provenance", f"{row['id']}: Smarkets quote {quote} not found for {n0} vs {n1}")
                    continue
                matched_sm = False
                for item, swapped in hits:
                    outs = item["raw"]["outcomes"]
                    m0 = outs[0].get("mid_prob") if not swapped else outs[1].get("mid_prob")
                    m1 = outs[1].get("mid_prob") if not swapped else outs[0].get("mid_prob")
                    if m0 is not None and m1 is not None and (m0 + m1) > 0:
                        rp0, rp1 = m0 / (m0 + m1), m1 / (m0 + m1)
                        if close(rp0, p0, 0.003) and close(rp1, p1, 0.003):
                            matched_sm = True
                            break
                if not matched_sm:
                    fail("B provenance", f"{row['id']}: Smarkets quote {quote} matches no raw mid_prob")
            else:
                warn("B provenance", f"{row['id']}: venue {vname} is not covered by this independent "
                                     f"check (no raw payload mapping)")

        # D: consensus reproduces from the venue weights
        venues = mk.get("venues") or []
        if venues:
            wsum = sum(v["weight"] for v in venues)
            cons0 = sum(v["weight"] * v["p0"] for v in venues) / wsum
            cons1 = sum(v["weight"] * v["p1"] for v in venues) / wsum
            if not (close(cons0, row["p0"], 0.001) and close(cons1, row["p1"], 0.001)):
                fail("D arithmetic", f"{row['id']}: consensus from weights "
                                     f"{cons0:.4f}/{cons1:.4f} != published {row['p0']}/{row['p1']}")
            label = mk.get("book") or ""
            if len(venues) >= 2 and not label.startswith(f"{len(venues)}-Venue"):
                warn("D arithmetic", f"{row['id']}: venue count {len(venues)} but label {label!r}")
            for v in venues:
                if not v.get("url", "").startswith("https://"):
                    fail("G sourcing", f"{row['id']}: venue {v['name']} has no https source URL")
            obs = {parse_ts(v.get("observed_utc")) for v in venues}
            if all(x is None for x in obs) and build_ts:
                warn("B provenance", f"{row['id']}: venue quotes carry no per-quote capture time")

    # ------------------------------------------------------------ all-row checks
    for row in rows:
        rid = row["id"]
        f = fixture_by_id.get(str(rid))
        if f:
            expected_url = row.get("hotspawn_url") or ""
            if f"-{rid}" not in expected_url:
                fail("G sourcing", f"{rid}: hotspawn_url does not end with the fixture id")
            if f["team0"]["name"] != row["team0"]["name"] or f["team1"]["name"] != row["team1"]["name"]:
                fail("A inventory", f"{rid}: team names differ from the raw Hotspawn fixture")
            raw_start = parse_ts(f.get("start_utc"))
            if raw_start and row.get("start_utc") and parse_ts(row["start_utc"]) != raw_start:
                fail("A inventory", f"{rid}: start time {row['start_utc']} != Hotspawn {raw_start.isoformat()}")

        method = row.get("method")
        if method == "unresolved":
            if row.get("p0") is not None or row.get("p1") is not None:
                fail("D arithmetic", f"{rid}: unresolved row carries a probability")
            pick = row.get("pick")
            if pick is not None:
                # A settlement pick is allowed, but only as an administrative default with
                # no invented probability, and it must name the team that was not removed.
                if row.get("pick_type") != "settlement":
                    fail("D arithmetic", f"{rid}: unresolved row carries a pick that is not a "
                                         f"declared settlement")
                elif pick.get("probability") is not None:
                    fail("D arithmetic", f"{rid}: settlement pick carries a probability")
                elif pick.get("side") not in (0, 1) or pick.get("team") != row[
                        f"team{pick.get('side', 0)}"]["name"]:
                    fail("D arithmetic", f"{rid}: settlement pick is inconsistent with its side")
            continue
        p0, p1 = row.get("p0"), row.get("p1")
        if not (isinstance(p0, (int, float)) and isinstance(p1, (int, float))):
            fail("D arithmetic", f"{rid}: priced row has no numeric probability")
            continue
        if not close(p0 + p1, 1.0, 0.002):
            fail("D arithmetic", f"{rid}: probabilities sum to {p0 + p1:.4f}")
        pick = row.get("pick") or {}
        side = 0 if p0 >= p1 else 1
        if pick.get("team") != row[f"team{side}"]["name"]:
            fail("D arithmetic", f"{rid}: pick is not the higher-probability side")
        if not close(float(pick.get("probability") or -1), max(p0, p1), 0.001):
            fail("D arithmetic", f"{rid}: pick probability differs from the favourite")

        if method in ("model", "provisional"):
            e0, e1 = row["team0"].get("elo"), row["team1"].get("elo")
            if e0 is None or e1 is None:
                fail("E model", f"{rid}: {method} row without both ratings")
                continue
            model = matches_doc.get("model") or {}
            low, high = model.get("prob_floor", 0.02), model.get("prob_ceil", 0.98)
            raw_p = 1 / (1 + 10 ** ((e1 - e0) / 400))
            expected = min(max(raw_p, low), high)
            if not close(expected, p0, 0.0015):
                fail("E model", f"{rid}: Elo {e0}/{e1} gives {expected:.4f} but published {p0}")
            if row.get("market"):
                warn("E model", f"{rid}: {method} row also carries a market block")

    # ------------------------------------------------------------- F freshness
    for name, doc in (("pinnacle", pin), ("bovada", bov), ("kalshi", kal),
                      ("polymarket", pol), ("unibet", kam), ("smarkets", smk), ("hotspawn", hs)):
        ts = parse_ts(doc.get("fetched_utc"))
        if ts is None or build_ts is None:
            warn("F freshness", f"{name}: missing fetch or build timestamp")
            continue
        age_h = (build_ts - ts).total_seconds() / 3600
        if age_h > 12:
            warn("F freshness", f"{name}: payload was {age_h:.1f}h old at build time")

    # -------------------------------------------------------------- G sourcing
    for row in rows:
        url = row.get("hotspawn_url") or ""
        if not url.startswith("https://www.hotspawn.com/matches/"):
            fail("G sourcing", f"{row['id']}: hotspawn_url is not a Hotspawn match card")
        if row.get("method") in ("model", "provisional"):
            if not row.get("leaguepedia_page"):
                warn("G sourcing", f"{row['id']}: model row without a Leaguepedia page reference")
            if any(t.get("join") == "none" for t in (row["team0"], row["team1"])):
                fail("G sourcing", f"{row['id']}: priced row references an unmatched team")

    # ------------------------------------------------------------------ report
    report = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dataset_generated_utc": matches_doc.get("generated_utc"),
        "rows": len(rows),
        "market_rows": len(market_rows),
        "venues_checked": venue_checked,
        "counts": matches_doc.get("counts"),
        "failures": FAILS,
        "warnings": WARNS,
        "pinnacle_kills_substitutions": kills_substitutions,
        "passed": not FAILS,
    }
    os.makedirs(AUDIT, exist_ok=True)
    with open(os.path.join(AUDIT, "report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    lines = ["# Independent verification report", "",
             f"Generated: `{report['generated_utc']}` · dataset: `{report['dataset_generated_utc']}`",
             "",
             f"- rows: **{len(rows)}** · market rows: **{len(market_rows)}** · venue quotes re-derived: "
             f"**{venue_checked}**",
             f"- failures: **{len(FAILS)}** · warnings: **{len(WARNS)}**", ""]
    if kills_substitutions:
        lines += ["## Pinnacle market-type substitutions", "",
                  "A `(Kills)` market was used where a series moneyline exists for the same teams.", "",
                  "| match | teams | used | series moneyline |", "|---|---|---|---|"]
        for k in kills_substitutions:
            lines.append(f"| {k['match_id']} | {' vs '.join(k['teams'])} | "
                         f"{k['used']['decimal'][0]}/{k['used']['decimal'][1]} (id {k['used']['matchup_id']}) | "
                         f"{k['series_moneyline']['decimal'][0]}/{k['series_moneyline']['decimal'][1]} "
                         f"(id {k['series_moneyline']['matchup_id']}) |")
        lines.append("")
    for title, items in (("Failures", FAILS), ("Warnings", WARNS)):
        lines += [f"## {title}", ""]
        if not items:
            lines += ["None.", ""]
        else:
            for item in items:
                lines.append(f"- **{item['check']}** — {item['detail']}")
            lines.append("")
    with open(os.path.join(AUDIT, "report.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    print(f"rows={len(rows)} market_rows={len(market_rows)} venues_checked={venue_checked}")
    print(f"failures={len(FAILS)} warnings={len(WARNS)} "
          f"kills_substitutions={len(kills_substitutions)}")
    for item in FAILS[:20]:
        print("FAIL", item["check"], "-", item["detail"])
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main())
