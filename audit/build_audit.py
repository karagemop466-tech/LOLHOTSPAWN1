#!/usr/bin/env python3
"""Session 0d48f265 — line-by-line audit of data/matches.json (read-only input).

Writes audit/audit.csv (one row per committed match) and audit/summary.json.
Internal checks run on every row. Live checks were performed by hand with fetch_page
on 2026-10-23 and are recorded in LIVE below, keyed by match id; nothing else is
asserted as live-verified.
"""
import csv, datetime as dt, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
AS_OF = dt.datetime(2026, 10, 23, 15, 50, tzinfo=dt.timezone.utc)
HOTSPAWN_API = ("https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures"
                "?sport_alias=lol&status=scheduled&tenantId=1")
LP_SCHEDULE = ("https://lol.fandom.com/wiki/Special:CargoExport?tables=MatchSchedule&fields=MatchSchedule.Team1,"
               "MatchSchedule.Team2,MatchSchedule.Winner,MatchSchedule.DateTime_UTC,MatchSchedule.OverviewPage,"
               "MatchSchedule.Team1Score,MatchSchedule.Team2Score&where=MatchSchedule.OverviewPage%3D%27Komplettligaen"
               "%2F2026+Season%2FAutumn+Split%27+AND+%28MatchSchedule.Team1%3D%27Solid+Gaming%27+OR+MatchSchedule.Team2%3D%27Solid+Gaming%27%29&limit=50&format=json")
POLY_GAMMA = "https://gamma-api.polymarket.com/markets?slug={}"

# Live receipts obtained by hand on 2026-10-23 (see audit/AUDIT.md for the exact observations).
LIVE_INVENTORY_CHUNK0 = {  # match id -> (team0, team1, start_utc) as served by Hotspawn chunk 0
    "1053095": ("Mind Blue eSports", "LAST DANCE", "2026-08-26T17:00:00Z"),
    "1053096": ("Nameless", "BiPOLAR", "2026-08-26T18:00:00Z"),
    "1066214": ("Epic Avalanche", "Finnish Red Mafia", "2026-08-27T15:00:00Z"),
    "1053111": ("Team VS Esport", "GALA Esports", "2026-09-05T11:00:00Z"),
    "1071584": ("P11 Esports", "HANGMEN", "2026-09-07T17:00:00Z"),
    "1070209": ("Triforce Esport", "Venus", "2026-09-12T11:00:00Z"),
    "1070210": ("GALA Esports", "The Bandits Academy", "2026-09-13T11:00:00Z"),
    "1069849": ("Docta Esports Club", "Viktus", "2026-09-13T15:00:00Z"),
    "1071167": ("DMG Esports Norway", "Playwell Rød Q", "2026-09-17T15:00:00Z"),
    "1071170": ("Solid Gaming", "VES Japan", "2026-09-17T15:00:00Z"),
}
LIVE_MARKETS = {
    "1067878": {"venues": "Polymarket gamma (lol-gen-ig1-2026-10-23): outcomePrices 0.775/0.225, gameStartTime 17:00Z; "
                          "Kalshi KXLOLGAME-26OCT231300IGGEN: yes bid 0.77 / ask 0.78 (mid 0.775); "
                          "Pinnacle -355/+274 served under matchup 1638748200 (NOT the stored 1638758865)",
                "verdict": "value verified; Pinnacle provenance mismatch flagged"},
    "1079080": {"venues": "Polymarket gamma (lol-rb-mr-2026-10-27, groupItemTitle Match Winner): outcomePrices "
                          "Vitality Rising Bees 0.675 / Mental Rush 0.325; volume $5; liquidity $4,226; gameStartTime 16:00Z",
                "verdict": "value verified (rounded 0.32/0.68); thin market and start-time mismatch flagged"},
}
LIVE_DQ = {  # Leaguepedia MatchSchedule (community wiki) rows for Solid Gaming in Komplettligaen 2026 Autumn
    "1071170": "Leaguepedia: VES Japan vs Solid Gaming 2026-10-01 16:00 UTC, VES Japan 2-0 (no 2026-09-17 row)",
    "1071200": "Leaguepedia: Solid Gaming vs Playwell Rød Q 2026-10-04 15:00 UTC, Playwell 2-0",
    "1071206": "Leaguepedia: Volda E-Sport vs Solid Gaming 2026-10-11 15:00 UTC, Volda 2-0",
    "1071186": "Leaguepedia: Solid Gaming vs NTNUI Kometkameratene 2026-10-13 17:00 UTC, NTNUI 2-0",
}

def parse(ts):
    return dt.datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else None

def main():
    data = json.loads((ROOT / "data/matches.json").read_text())
    rows = data["matches"]
    out, summary = [], {"rows": len(rows), "as_of": AS_OF.isoformat(), "checks": {}, "by_method": {}}
    fails = {}
    def bump(k): fails[k] = fails.get(k, 0) + 1
    for m in rows:
        notes, checks = [], []
        t0, t1 = (m.get("team0") or {}).get("name"), (m.get("team1") or {}).get("name")
        start = parse(m.get("start_utc"))
        p0, p1, pick = m.get("p0"), m.get("p1"), m.get("pick")
        meth = m.get("method")
        summary["by_method"][meth] = summary["by_method"].get(meth, 0) + 1
        if not t0 or not t1: checks.append("teams-missing"); bump("teams-missing")
        if start is None: checks.append("start-missing"); bump("start-missing")
        if meth in ("market", "model", "provisional"):
            if p0 is None or p1 is None or abs((p0 + p1) - 1.0) > 0.002:
                checks.append("prob-sum"); bump("prob-sum")
            elif pick and pick.get("probability") is not None:
                hi = 0 if p0 >= p1 else 1
                if pick.get("side") != hi: checks.append("pick-not-higher-side"); bump("pick-not-higher-side")
        elif meth == "unresolved":
            if p0 is not None or p1 is not None or pick is not None:
                checks.append("unresolved-has-value"); bump("unresolved-has-value")
        if not m.get("hotspawn_url"): checks.append("no-hotspawn-link"); bump("no-hotspawn-link")
        past = start is not None and start < AS_OF
        stale_flag = any("start time has passed" in f for f in (m.get("flags") or []))
        if past and not stale_flag:
            checks.append("past-start-not-flagged"); bump("past-start-not-flagged")
        if stale_flag and not past:
            checks.append("stale-flag-but-upcoming"); bump("stale-flag-but-upcoming")
        mid = m["id"]
        live = "no"
        verdict = "internal checks pass; not re-fetched live" if not checks else "FLAG: " + ", ".join(checks)
        mk_url = (m.get("market") or {}).get("market_url") or ""
        if mid in LIVE_INVENTORY_CHUNK0:
            exp = LIVE_INVENTORY_CHUNK0[mid]
            ok = (t0, t1, m["start_utc"]) == exp
            live = "inventory-match" if ok else "inventory-MISMATCH"
            verdict = ("live inventory match (Hotspawn chunk 0)" if ok else "MISMATCH vs live Hotspawn") + \
                      ("" if not checks else "; FLAG: " + ", ".join(checks))
        if mid in LIVE_MARKETS:
            live = "market-recheck"
            verdict = LIVE_MARKETS[mid]["verdict"] + ("" if not checks else "; FLAG: " + ", ".join(checks))
        if mid in LIVE_DQ:
            live = (live + "+leaguepedia-recheck") if live != "no" else "leaguepedia-recheck"
            verdict = (verdict + "; " if live.startswith("inventory") else "") + \
                      "FLAG: unresolved; " + LIVE_DQ[mid] + ("" if not checks else "; " + ", ".join(checks))
        if mid == "1079080":
            notes.append("Hotspawn 17:00Z vs Polymarket 16:00Z (12:00 ET)")
        out.append({
            "match_id": mid, "competition": m["competition"], "team0": t0, "team1": t1,
            "start_utc": m.get("start_utc"), "method": meth,
            "p_team0": "" if p0 is None else f"{p0:.4f}", "p_team1": "" if p1 is None else f"{p1:.4f}",
            "pick": (pick or {}).get("team", "") if pick else "",
            "past_start": "yes" if past else "no", "snapshot_stale_flag": "yes" if stale_flag else "no",
            "hotspawn_card": m.get("hotspawn_url") or "", "hotspawn_api": HOTSPAWN_API,
            "market_source": mk_url, "live_check": live, "verdict": verdict,
            "notes": "; ".join(notes),
        })
    summary["checks"] = fails or {"all_internal": "pass"}
    summary["past_start_rows"] = sum(1 for r in out if r["past_start"] == "yes")
    summary["live_inventory_rows_matched"] = sum(1 for r in out if r["live_check"].startswith("inventory-match"))
    summary["live_market_rows_rechecked"] = sum(1 for r in out if r["live_check"] == "market-recheck")
    summary["live_leaguepedia_rows_rechecked"] = sum(1 for r in out if "leaguepedia-recheck" in r["live_check"])
    summary["past_start_not_flagged_ids"] = [r["match_id"] for r in out if r["past_start"] == "yes" and r["snapshot_stale_flag"] == "no"]
    with open(ROOT / "audit/audit.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader(); w.writerows(out)
    (ROOT / "audit/summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(summary, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
