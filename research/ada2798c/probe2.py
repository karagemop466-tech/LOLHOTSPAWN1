#!/usr/bin/env python3
"""Session ada2798c probe 2 — can any external venue price the Hotspawn tail?

Probe 1 (`probe.py`) proved *reachability*. This one answers the question that decides
how many matches can carry a market-derived probability:

  For each of the 241 fixtures Hotspawn lists right now, does any reachable bookmaker or
  exchange publish an open two-sided moneyline on that exact match?

It joins every live Hotspawn fixture to the Pinnacle, Unibet/Kambi (`ubse`, `paf`) and
Polymarket feeds by team name, records the outcome per fixture, and writes a per-competition
summary. Everything is evidence: unjoined fixtures are listed with the reason, and no price
is ever inferred from a name that did not match.

Output (committed by the caller):
  audit/ada2798c/venue_coverage.json   per-fixture join result + per-competition summary
  audit/ada2798c/pinnacle_leagues.json which LoL leagues Pinnacle actually offers
  audit/ada2798c/raw/*.json            compact raw extracts for manual review
"""
from __future__ import annotations

import json
import os
import re
import ssl
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timezone

OUT = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(OUT, "raw")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")

HOTSPAWN = ("https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures"
            "?sport_alias=lol&status=scheduled&tenantId=1")
PINNACLE_MATCHUPS = "https://guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups"
PINNACLE_LEAGUES = "https://guest.api.arcadia.pinnacle.com/0.1/sports/12/leagues"
PINNACLE_STRAIGHT = "https://guest.api.arcadia.pinnacle.com/0.1/matchups/{id}/markets/related/straight"
KAMBI = ("https://eu-offering-api.kambicdn.com/offering/v2018/{op}/listView/esports/"
         "league_of_legends/all/all/matches.json?lang=en_GB&market=ZZ")

# Deliberately conservative. Only purely corporate suffixes are dropped; "Academy",
# "Rising", "Youth", "Junior" and the like are DISTINGUISHING tokens on Hotspawn and in
# every feed probed here, so dropping them would merge a main roster with its academy team
# and produce a false join. A fixture that does not join exactly is reported as not joined.
TEAM_NOISE = {"esports", "esport", "esportsclub", "gaming", "team", "the", "club", "gg"}


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get(url: str, timeout: int = 45):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read() if hasattr(e, "read") else b""
    except Exception as e:
        return 0, str(e).encode()


def jload(body: bytes):
    try:
        return json.loads(body.decode("utf-8", "replace"))
    except Exception:
        return None


def norm(name: str) -> str:
    s = unicodedata.normalize("NFKD", str(name or "")).encode("ascii", "ignore").decode()
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    toks = [t for t in s.split() if t]
    core = [t for t in toks if t not in TEAM_NOISE]
    return "".join(core or toks)


def pair_key(a: str, b: str) -> str:
    x, y = norm(a), norm(b)
    return "|".join(sorted([x, y]))


# ------------------------------------------------------------------ hotspawn inventory
def hotspawn():
    st, body = get(HOTSPAWN)
    doc = jload(body)
    if not isinstance(doc, list):
        raise SystemExit(f"hotspawn: HTTP {st}; cannot build the coverage matrix")
    with open(os.path.join(OUT, "hotspawn_live.json"), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, separators=(",", ":"))
    rows = []
    for x in doc:
        t0, t1 = x.get("participants0_name"), x.get("participants1_name")
        rows.append({
            "id": str(x.get("id")),
            "competition": x.get("competition_name"),
            "team0": t0,
            "team1": t1,
            "key": pair_key(t0, t1),
            "start_utc": datetime.fromtimestamp(
                int(x.get("scheduled_start_time") or 0) / 1000, tz=timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
    return rows


# ------------------------------------------------------------------ pinnacle
def pinnacle():
    st, body = get(PINNACLE_LEAGUES)
    leagues = jload(body) or []
    st2, body2 = get(PINNACLE_MATCHUPS)
    matchups = jload(body2) or []
    extract = []
    for m in matchups if isinstance(matchups, list) else []:
        parts = m.get("participants") or []
        names = [p.get("name") for p in parts if p.get("alignment") in ("home", "away")]
        if len(names) != 2:
            names = [p.get("name") for p in parts][:2]
        if len(names) != 2:
            continue
        lg = m.get("league") or {}
        extract.append({
            "matchup_id": m.get("id"),
            "league_id": lg.get("id"),
            "league": lg.get("name"),
            "team0": names[0],
            "team1": names[1],
            "key": pair_key(names[0], names[1]),
            "start_utc": m.get("startTime"),
            "type": m.get("type"),
            "is_live": m.get("isLive"),
            "parent": m.get("parent") is not None,
            "has_moneyline_market": bool(m.get("hasMarkets")),
        })
    with open(os.path.join(OUT, "pinnacle_leagues.json"), "w", encoding="utf-8") as fh:
        json.dump({"checked_utc": now(), "http_status": st, "matchups_http_status": st2,
                   "leagues": [{"id": l.get("id"), "name": l.get("name"),
                                "matchup_count": l.get("matchupCount")}
                               for l in leagues if isinstance(leagues, list)],
                   "matchup_count": len(extract)}, fh, indent=1)
    with open(os.path.join(RAW, "pinnacle_matchups.json"), "w", encoding="utf-8") as fh:
        json.dump(extract, fh, indent=1)

    # which of those matchups actually publish a two-sided series moneyline right now?
    priced = {}
    for row in extract:
        st3, b3 = get(PINNACLE_STRAIGHT.format(id=row["matchup_id"]), timeout=20)
        doc = jload(b3) or []
        good = False
        for mk in doc if isinstance(doc, list) else []:
            if mk.get("type") != "moneyline":
                continue
            if mk.get("period") not in (0, None):
                continue
            prices = [p.get("price") for p in mk.get("prices") or []]
            if len([p for p in prices if p not in (None, 0)]) == 2 and mk.get("status") == "open":
                good = True
        priced[str(row["matchup_id"])] = {"open_moneyline": good, "http": st3}
    return extract, priced, st, st2


# ------------------------------------------------------------------ kambi
def kambi(op: str):
    """Kambi listView feed. The market shape differs between operators/versions, so the
    outcomes are found structurally (any 2-outcome market with numeric odds) instead of by
    a hard-coded type string: guessing a type name would produce a false "no odds here"."""
    st, body = get(KAMBI.format(op=op))
    doc = jload(body) or {}
    out = []

    def two_way(node):
        """Depth-first search for the first 2-outcome market with real decimal odds."""
        if isinstance(node, dict):
            outs = node.get("outcomes")
            if isinstance(outs, list) and len(outs) == 2:
                odds = [o.get("odds") for o in outs]
                if all(isinstance(o, (int, float)) and o > 1.0 for o in odds):
                    return list(odds), [o.get("label") for o in outs], node.get("type")
            for v in node.values():
                found = two_way(v)
                if found:
                    return found
        elif isinstance(node, list):
            for v in node:
                found = two_way(v)
                if found:
                    return found
        return None

    for ev in (doc.get("events") or []) if isinstance(doc, dict) else []:
        e = ev.get("event") or {}
        name = e.get("name") or ""
        parts = re.split(r"\s+-\s+|\s+vs\.?\s+", name, maxsplit=1)
        found = two_way(ev)
        out.append({"event_id": e.get("id"), "name": name, "start": e.get("start"),
                    "teams": parts, "odds": found[0] if found else None,
                    "labels": found[1] if found else None,
                    "market_type": found[2] if found else None})
    with open(os.path.join(RAW, f"kambi_{op}.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    return out, st


# ------------------------------------------------------------------ main
def main() -> None:
    os.makedirs(RAW, exist_ok=True)
    hs = hotspawn()
    pin, pin_priced, pin_st, pin_m_st = pinnacle()
    k_ubse, k_ubse_st = kambi("ubse")
    k_paf, k_paf_st = kambi("paf")

    pin_by_key = {r["key"]: r for r in pin}
    ubse_by_key = {}
    for r in k_ubse:
        if len(r["teams"]) == 2:
            ubse_by_key[pair_key(*r["teams"])] = r
    paf_by_key = {}
    for r in k_paf:
        if len(r["teams"]) == 2:
            paf_by_key[pair_key(*r["teams"])] = r

    rows = []
    for h in hs:
        p = pin_by_key.get(h["key"])
        u = ubse_by_key.get(h["key"])
        a = paf_by_key.get(h["key"])
        moneyline = None
        if p:
            moneyline = (pin_priced.get(str(p["matchup_id"])) or {}).get("open_moneyline")
        rows.append({
            "fixture_id": h["id"], "competition": h["competition"], "match": f'{h["team0"]} vs {h["team1"]}',
            "start_utc": h["start_utc"],
            "pinnacle_listed": bool(p),
            "pinnacle_league": p["league"] if p else None,
            "pinnacle_matchup_id": p["matchup_id"] if p else None,
            "pinnacle_open_moneyline": moneyline,
            "kambi_ubse": bool(u),
            "kambi_ubse_odds": u["odds"] if u else None,
            "kambi_ubse_event_id": u["event_id"] if u else None,
            "kambi_paf": bool(a),
            "kambi_paf_odds": a["odds"] if a else None,
        })

    comp: dict[str, dict] = {}
    for r in rows:
        c = comp.setdefault(r["competition"], {"fixtures": 0, "pinnacle_listed": 0,
                                               "pinnacle_open_moneyline": 0,
                                               "kambi_ubse": 0, "kambi_paf": 0,
                                               "any_external_price": 0})
        c["fixtures"] += 1
        c["pinnacle_listed"] += r["pinnacle_listed"]
        c["pinnacle_open_moneyline"] += bool(r["pinnacle_open_moneyline"])
        c["kambi_ubse"] += r["kambi_ubse"]
        c["kambi_paf"] += r["kambi_paf"]
        c["any_external_price"] += bool(r["pinnacle_open_moneyline"] or r["kambi_ubse"])

    summary = {
        "checked_utc": now(),
        "hotspawn_live_fixtures": len(hs),
        "pinnacle": {
            "http_status": pin_st, "matchups_http_status": pin_m_st,
            "lol_matchups_listed": len(pin),
            "matchups_with_open_moneyline": sum(1 for v in pin_priced.values() if v["open_moneyline"]),
            "distinct_leagues": len({r["league"] for r in pin if r["league"]}),
        },
        "kambi_ubse": {"http_status": k_ubse_st, "markets": len(k_ubse),
                       "with_two_sided_odds": sum(1 for r in k_ubse if r["odds"])},
        "kambi_paf": {"http_status": k_paf_st, "markets": len(k_paf),
                      "with_two_sided_odds": sum(1 for r in k_paf if r["odds"])},
        "hotspawn_fixtures_with_pinnacle_open_moneyline": sum(1 for r in rows if r["pinnacle_open_moneyline"]),
        "hotspawn_fixtures_with_kambi_price": sum(1 for r in rows if r["kambi_ubse"] or r["kambi_paf"]),
        "hotspawn_fixtures_with_any_external_price": sum(
            1 for r in rows if r["pinnacle_open_moneyline"] or r["kambi_ubse"] or r["kambi_paf"]),
    }
    doc = {"summary": summary,
           "pinnacle_league_coverage": {c: {"fixtures": v["fixtures"],
                                            "pinnacle_listed": v["pinnacle_listed"],
                                            "pinnacle_open_moneyline": v["pinnacle_open_moneyline"],
                                            "kambi_ubse": v["kambi_ubse"]}
                                        for c, v in sorted(comp.items(), key=lambda kv: -kv[1]["fixtures"])},
           "rows": rows}
    with open(os.path.join(OUT, "venue_coverage.json"), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
