#!/usr/bin/env python3
"""Session ada2798c research probe (branch-only, never publishes a page).

Two questions this answers with committed evidence rather than assertion:

1. **Coverage** - is the published `data/matches.json` still the same inventory that
   Hotspawn serves right now? Hotspawn drops a card the moment it settles, so a dataset
   built a day ago is not a mirror of today's list.
2. **External lines** - which established LoL betting sites / esportsbooks / odds feeds
   can the build runner actually reach, and do any of them price the national and
   academy tail that Hotspawn lists? Every candidate is recorded with its HTTP verdict,
   whether or not it answers, so a blocked source is documented instead of forgotten.

Nothing here writes to `data/` or to a published page. Output lands in `audit/ada2798c/`
and is committed by the caller so a sandbox without egress can read it.
"""
from __future__ import annotations

import json
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.abspath(os.path.join(OUT, "..", ".."))
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")

HOTSPAWN = ("https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures"
            "?sport_alias=lol&status=scheduled&tenantId=1")

# Candidate external price sources. Grouped so the report reads as research, not a dump.
VENUES = [
    # --- already used by the pipeline (control group: these should answer 200) -------
    ("Pinnacle (guest API, in use)", "sharp book", "https://guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups"),
    ("Pinnacle league list", "sharp book", "https://guest.api.arcadia.pinnacle.com/0.1/sports/12/leagues"),
    ("Kalshi KXLOLGAME (in use)", "CFTC exchange", "https://api.elections.kalshi.com/trade-api/v2/events?series_ticker=KXLOLGAME&status=open&with_nested_markets=true&limit=100"),
    ("Bovada (in use)", "esportsbook", "https://www.bovada.lv/services/sports/event/coupon/events/A/description/esports/league-of-legends?marketFilterId=def&preMatchOnly=true&lang=en"),
    ("Unibet/Kambi ubse (in use)", "regulated book", "https://eu-offering-api.kambicdn.com/offering/v2018/ubse/listView/esports/league_of_legends/all/all/matches.json?lang=en_GB&market=ZZ"),
    ("Polymarket (in use)", "prediction market", "https://gamma-api.polymarket.com/events?closed=false&limit=5&tag_slug=league-of-legends"),

    # --- additional Kambi-powered books (same feed family, different books) ---------
    ("Kambi ubus", "regulated book", "https://eu-offering-api.kambicdn.com/offering/v2018/ubus/listView/esports/league_of_legends/all/all/matches.json?lang=en_GB&market=ZZ"),
    ("Kambi ubpl", "regulated book", "https://eu-offering-api.kambicdn.com/offering/v2018/ubpl/listView/esports/league_of_legends/all/all/matches.json?lang=en_GB&market=ZZ"),
    ("Kambi ubde", "regulated book", "https://eu-offering-api.kambicdn.com/offering/v2018/ubde/listView/esports/league_of_legends/all/all/matches.json?lang=en_GB&market=ZZ"),
    ("Kambi paf", "regulated book", "https://eu-offering-api.kambicdn.com/offering/v2018/paf/listView/esports/league_of_legends/all/all/matches.json?lang=en_GB&market=ZZ"),
    ("Kambi coolbet", "regulated book", "https://eu-offering-api.kambicdn.com/offering/v2018/coolbet/listView/esports/league_of_legends/all/all/matches.json?lang=en_GB&market=ZZ"),

    # --- esportsbooks ---------------------------------------------------------------
    ("Rivalry games", "esportsbook", "https://api.rivalry.com/api/v1/games"),
    ("Rivalry LoL matches", "esportsbook", "https://api.rivalry.com/api/v1/matches?game_id=24"),
    ("GG.BET LoL", "established book", "https://gg.bet/en/esports/league-of-legends"),
    ("Thunderpick esports", "esportsbook", "https://thunderpick.io/api/v1/sports/esports/matches"),
    ("Midnite esports", "esportsbook", "https://www.midnite.com/api/events?sport=league-of-legends"),
    ("Betway esports", "established book", "https://www.betway.com/sports/esports/league-of-legends"),
    ("1xBet LoL", "established book", "https://1xbet.com/Line/Esports/League-of-Legends"),
    ("Betano esports tree", "established book", "https://www.betano.com/api/sporttree/esports"),

    # --- esports odds feeds / aggregators -------------------------------------------
    ("bo3.gg matches API", "aggregator", "https://api.bo3.gg/api/v1/matches?page[limit]=5"),
    ("EGamersWorld LoL", "aggregator", "https://egamersworld.com/lol/matches"),
    ("OddsPortal LoL", "aggregator", "https://www.oddsportal.com/esports/league-of-legends/"),
    ("Oddspedia LoL", "aggregator", "https://oddspedia.com/esports/league-of-legends"),
    ("Sofascore LoL", "aggregator", "https://api.sofascore.com/api/v1/sport/esports/scheduled-events/2026-10-25"),
    ("escorenews LoL", "aggregator", "https://escorenews.com/en/league-of-legends"),

    # --- community / data sites that publish records but no prices -------------------
    ("Leaguepedia Cargo", "community wiki", "https://lol.fandom.com/wiki/Special:CargoExport?tables=MatchSchedule&fields=MatchSchedule.MatchId&limit=1&format=json"),
    ("Leaguepedia scoreboard players", "community wiki", "https://lol.fandom.com/wiki/Special:CargoExport?tables=ScoreboardPlayers&fields=ScoreboardPlayers.Name&limit=1&format=json"),
    ("LoL Esports (Riot) schedule", "official", "https://esports-api.lolesports.com/persisted/gw/getSchedule?hl=en-US"),
    ("LoL Esports (Riot) leagues", "official", "https://esports-api.lolesports.com/persisted/gw/getLeagues?hl=en-US"),
]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get(url: str, timeout: int = 30) -> tuple[int, bytes, str, float]:
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-GB,en;q=0.9",
    })
    ctx = ssl.create_default_context()
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            body = r.read()
            return r.status, body, r.headers.get("content-type", ""), time.time() - t0
    except urllib.error.HTTPError as e:
        try:
            body = e.read()
        except Exception:
            body = b""
        return e.code, body, e.headers.get("content-type", "") if e.headers else "", time.time() - t0
    except Exception as e:  # DNS, TLS, timeout, reset
        return 0, str(e).encode(), type(e).__name__, time.time() - t0


def json_or_none(body: bytes):
    try:
        return json.loads(body.decode("utf-8", "replace"))
    except Exception:
        return None


# --------------------------------------------------------------------------- 1. coverage
def coverage() -> dict:
    status, body, _, _ = get(HOTSPAWN, timeout=45)
    report: dict = {"checked_utc": now(), "source_url": HOTSPAWN, "http_status": status}
    live = json_or_none(body) if status == 200 else None
    if not isinstance(live, list):
        report["error"] = "live fixture feed did not return a JSON list"
        return report
    with open(os.path.join(OUT, "hotspawn_live.json"), "w", encoding="utf-8") as fh:
        json.dump(live, fh, ensure_ascii=False, separators=(",", ":"))

    live_ids = [str(x.get("id")) for x in live]
    report["live_fixtures"] = len(live_ids)
    report["live_unique_ids"] = len(set(live_ids))

    ds_path = os.path.join(ROOT, "data", "matches.json")
    with open(ds_path, encoding="utf-8") as fh:
        ds = json.load(fh)
    pub_ids = [str(m.get("id")) for m in ds.get("matches") or []]
    report["dataset_fixtures"] = len(pub_ids)
    report["dataset_generated_utc"] = ds.get("generated_utc")
    report["dataset_inventory_fetched_utc"] = ds.get("inventory_fetched_utc")
    report["live_not_in_dataset"] = sorted(set(live_ids) - set(pub_ids))
    report["dataset_not_in_live"] = sorted(set(pub_ids) - set(live_ids))

    live_by_id = {str(x.get("id")): x for x in live}
    report["live_not_in_dataset_detail"] = [
        {"id": i,
         "competition": (live_by_id.get(i) or {}).get("competition_name"),
         "match": f'{(live_by_id.get(i) or {}).get("participants0_name")} vs '
                  f'{(live_by_id.get(i) or {}).get("participants1_name")}',
         "starts_utc": datetime.fromtimestamp(
             int((live_by_id.get(i) or {}).get("scheduled_start_time") or 0) / 1000,
             tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        for i in report["live_not_in_dataset"]
    ]

    # per-competition parity, the same shape the publish gate uses
    pub_counts: dict[str, int] = {}
    for m in ds.get("matches") or []:
        pub_counts[m.get("competition")] = pub_counts.get(m.get("competition"), 0) + 1
    live_counts: dict[str, int] = {}
    for x in live:
        k = x.get("competition_name")
        live_counts[k] = live_counts.get(k, 0) + 1
    diffs = {k: {"live": live_counts.get(k, 0), "dataset": pub_counts.get(k, 0)}
             for k in set(pub_counts) | set(live_counts)
             if live_counts.get(k, 0) != pub_counts.get(k, 0)}
    report["competitions_live"] = len(live_counts)
    report["competitions_dataset"] = len(pub_counts)
    report["competition_count_differences"] = dict(sorted(diffs.items()))

    # are the archived external receipts still addressable on the live schedule?
    rec_ids: set[str] = set()
    rec_dir = os.path.join(ROOT, "data", "receipts", "external_odds")
    for name in sorted(os.listdir(rec_dir)) if os.path.isdir(rec_dir) else []:
        if not name.endswith(".json"):
            continue
        with open(os.path.join(rec_dir, name), encoding="utf-8") as fh:
            doc = json.load(fh)
        for cap in doc.get("captures") or []:
            rec_ids.add(str(cap.get("fixture_id")))
    report["archived_receipt_fixture_ids"] = sorted(rec_ids)
    report["archived_receipt_ids_still_listed"] = sorted(rec_ids & set(live_ids))
    report["archived_receipt_ids_rolled_off"] = sorted(rec_ids - set(live_ids))
    return report


# --------------------------------------------------------------------------- 2. venues
def odds_signal(doc) -> dict:
    """Best-effort: does this payload contain a two-sided decimal price for a LoL match?"""
    out = {"json": doc is not None, "decimal_like_values": 0, "mentions_team_pair": False}
    if doc is None:
        return out

    def walk(node):
        if isinstance(node, dict):
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
        elif isinstance(node, (int, float)) and not isinstance(node, bool):
            if 1.01 <= float(node) <= 30.0:
                out["decimal_like_values"] += 1

    walk(doc)
    txt = json.dumps(doc)[:400000].lower()
    out["mentions_team_pair"] = ("home" in txt and "away" in txt) or ("moneyline" in txt)
    return out


def venues() -> dict:
    rows = []
    for name, kind, url in VENUES:
        status, body, ctype, elapsed = get(url)
        doc = json_or_none(body) if body and body[:1] in (b"{", b"[") else None
        rows.append({
            "name": name,
            "kind": kind,
            "url": url,
            "http_status": status,
            "content_type": ctype,
            "bytes": len(body),
            "seconds": round(elapsed, 2),
            "verdict": ("reachable JSON paying load" if status == 200 and doc is not None
                        else "reachable but not JSON" if status == 200
                        else "blocked" if status in (401, 403, 429)
                        else "unavailable" if status in (404, 410)
                        else "not reachable" if status == 0 else f"http {status}"),
            "signal": odds_signal(doc),
            "excerpt": body[:180].decode("utf-8", "replace") if doc is None else "",
        })
        print(f"{status:>4} {len(body):>8}B  {name}", flush=True)
    return {"checked_utc": now(), "user_agent": UA, "rows": rows}


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    cov = coverage()
    with open(os.path.join(OUT, "coverage_delta.json"), "w", encoding="utf-8") as fh:
        json.dump(cov, fh, indent=1, ensure_ascii=False)
    print("coverage:", json.dumps({k: cov.get(k) for k in
                                   ("http_status", "live_fixtures", "dataset_fixtures",
                                    "dataset_generated_utc")}), flush=True)
    print("live not in dataset:", len(cov.get("live_not_in_dataset") or []),
          "dataset not in live:", len(cov.get("dataset_not_in_live") or []), flush=True)
    print("receipt ids rolled off:", len(cov.get("archived_receipt_ids_rolled_off") or []), flush=True)

    ven = venues()
    with open(os.path.join(OUT, "venue_probe.json"), "w", encoding="utf-8") as fh:
        json.dump(ven, fh, indent=1, ensure_ascii=False)
    ok = [r for r in ven["rows"] if r["http_status"] == 200]
    print(f"venues: {len(ok)}/{len(ven['rows'])} answered 200", flush=True)


if __name__ == "__main__":
    main()
