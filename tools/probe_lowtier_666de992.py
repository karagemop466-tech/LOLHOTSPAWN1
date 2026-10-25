"""Session 666de992: does ANY reachable venue list today's low-tier Hotspawn pairs?

Earlier probes answered "does the venue answer / does it price Worlds?". This one
answers the question that actually decides coverage: for every candidate venue,
search the response body for the *specific team pairs* Hotspawn lists today in
the national/academy tail (PRM 2nd/3rd Division, Tunisian Super League, RIVALS,
LigaGG CELOL, Icelandic, Arabian 2nd, Benelux Ascend, ...). Worlds pairs are
searched as a positive control, and primeleague.gg (the official league site)
is a second positive control proving the pair-search itself works.

Report-only. Never prices a match, never edits data/matches.json. A venue is
flagged `pair_found_review_snippet` only when both team names of a live tail
fixture appear in its response; the surrounding snippet is saved for manual
review. Absence of a pair is recorded as measured evidence, not an error.

Output: data/probe/session_666de992/probe.json (+ bounded raw previews).
Run on a GitHub Actions runner via .github/workflows/probe-666de992.yml —
the session sandbox has no egress to these hosts.
"""
from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DATA, ROOT, get_json, http_get, iso, log, norm_name, now_utc, save_json

OUT_DIR = os.path.join(DATA, "probe", "session_666de992")
OUT = os.path.join(OUT_DIR, "probe.json")
RAW_DIR = os.path.join(OUT_DIR, "raw")

HOTSPAWN_FIXTURES = ("https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/"
                     "fixtures?sport_alias=lol&status=scheduled&tenantId=1")
PINNACLE_KEY = {"x-api-key": "CmX2KcMrXuFmNg6YFbmTxE0y9CIrOi0R", "Accept": "application/json"}
KAMBI = ("https://eu-offering-api.kambicdn.com/offering/v2018/{op}/listView/"
         "esports/league_of_legends/all/all/matches.json?lang=en_GB&market=ZZ")
CONTROL_COMPS = {"Worlds 2026 Main Event"}  # known-priced; pair hits here prove egress+search
MAX_BODY = 3_000_000
ODDS_TOKEN = re.compile(r"\b[1-9]\d?\.\d{2}\b")


def fixtures() -> tuple[list[dict], list[dict]]:
    """Return (control_pairs, tail_pairs) from the live Hotspawn scheduled feed."""
    st, data, err = get_json(HOTSPAWN_FIXTURES, retries=2)
    if st != 200 or not isinstance(data, list):
        raise SystemExit(f"hotspawn fixtures failed: status={st} err={err}")
    control, tail = [], []
    for f in data:
        if f.get("sport_alias") != "lol":
            continue
        pair = {
            "id": str(f.get("id")),
            "competition": f.get("competition_name"),
            "team0": f.get("participants0_name"),
            "team1": f.get("participants1_name"),
            "start_ms": f.get("scheduled_start_time"),
        }
        (control if pair["competition"] in CONTROL_COMPS else tail).append(pair)
    return control, tail


def pair_hits(body_text: str, pairs: list[dict]) -> list[dict]:
    """Fixtures whose BOTH team names appear in the (normalised) body text."""
    norm_body = " " + norm_name(body_text) + " "
    hits = []
    for p in pairs:
        n0, n1 = norm_name(p["team0"]), norm_name(p["team1"])
        # Very short names (e.g. "T1") false-positive in prose; require >=4 chars
        # on at least one side and an exact normalised token match on both.
        if len(n0) < 2 or len(n1) < 2 or (len(n0) < 4 and len(n1) < 4):
            continue
        if f" {n0} " in norm_body or n0 in norm_body:
            if f" {n1} " in norm_body or n1 in norm_body:
                # snippet around the rarer name, from the ORIGINAL text
                idx = body_text.lower().find((p["team0"] or "").lower())
                snippet = ""
                if idx >= 0:
                    snippet = body_text[max(0, idx - 200): idx + 400].replace("\n", " ")
                hits.append({**p, "snippet_has_decimal_odds": bool(ODDS_TOKEN.search(snippet)),
                             "snippet": snippet[:600]})
    return hits


CANDIDATES = [
    # ---- positive controls (must hit control or tail pairs if search works) ----
    {"slug": "ctl_pinnacle_matchups", "name": "Pinnacle guest API matchups (control)",
     "url": "https://guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups",
     "headers": PINNACLE_KEY, "kind": "control"},
    {"slug": "ctl_pinnacle_leagues", "name": "Pinnacle guest API leagues (control)",
     "url": "https://guest.api.arcadia.pinnacle.com/0.1/sports/12/leagues",
     "headers": PINNACLE_KEY, "kind": "control"},
    {"slug": "ctl_kambi_ubse", "name": "Unibet/Kambi ubse LoL (control)",
     "url": KAMBI.format(op="ubse"), "kind": "control"},
    {"slug": "ctl_primeleague_liga2", "name": "PrimeLeague.gg official 2. Liga (pair-search control)",
     "url": "https://www.primeleague.gg/en/liga2", "kind": "control"},
    {"slug": "ctl_primeleague_liga3", "name": "PrimeLeague.gg official 3. Liga (pair-search control)",
     "url": "https://www.primeleague.gg/en/liga3", "kind": "control"},
    # ---- new / re-check candidates found in 2026-10-25 web research ----
    {"slug": "cloudbet_prm2", "name": "Cloudbet Prime League 2nd Division page",
     "url": "https://www.cloudbet.com/en/esports/league-of-legends/germany-t8205-prime-league-2nd-division",
     "kind": "esportsbook"},
    {"slug": "cloudbet_lol", "name": "Cloudbet LoL index",
     "url": "https://www.cloudbet.com/en/esports/league-of-legends", "kind": "esportsbook"},
    {"slug": "bmbets_prm2", "name": "BMBets Prime League 2nd Division comparison",
     "url": "https://www.bmbets.com/e-sports/world/lol---prime-league-2nd-division/",
     "kind": "odds-comparison"},
    {"slug": "bmbets_worlds", "name": "BMBets LoL World Championship (server-render control)",
     "url": "https://www.bmbets.com/e-sports/world/lol---world-championship/",
     "kind": "odds-comparison"},
    {"slug": "betmonitor_prm2", "name": "Betmonitor Prime League 2nd Division comparison",
     "url": "https://www.betmonitor.com/odds-comparison/esports/prime-league-2nd-division/10024464",
     "kind": "odds-comparison"},
    {"slug": "egw_bets", "name": "EGamersWorld LoL bets (runner previously 403)",
     "url": "https://egamersworld.com/lol/bets", "kind": "aggregator"},
    {"slug": "egw_matches", "name": "EGamersWorld LoL matches",
     "url": "https://egamersworld.com/lol/matches", "kind": "aggregator"},
    {"slug": "strafe_odds", "name": "Strafe LoL odds",
     "url": "https://www.strafe.com/esports-betting/odds/league-of-legends/", "kind": "aggregator"},
    {"slug": "strafe_lol", "name": "Strafe LoL hub",
     "url": "https://www.strafe.com/lol/", "kind": "aggregator"},
    {"slug": "lootbet_lol", "name": "LOOT.BET LoL",
     "url": "https://loot.bet/sport/esports/league-of-legends", "kind": "esportsbook"},
    {"slug": "stake_lol", "name": "Stake LoL",
     "url": "https://stake.com/sports/league-of-legends", "kind": "esportsbook"},
    {"slug": "bcgame_sports", "name": "BC.GAME sports",
     "url": "https://bc.game/sports", "kind": "esportsbook"},
    {"slug": "oddsportal_prime", "name": "OddsPortal Prime League",
     "url": "https://www.oddsportal.com/esports/league-of-legends/league-of-legends-prime-league/",
     "kind": "odds-comparison"},
    {"slug": "flashscore_lol", "name": "Flashscore LoL (results coverage check)",
     "url": "https://www.flashscore.com/esports/league-of-legends/", "kind": "results"},
    {"slug": "bo3_current", "name": "bo3.gg LoL current matches",
     "url": "https://bo3.gg/lol/matches/current", "kind": "match-centre"},
    {"slug": "bo3_tournaments", "name": "bo3.gg LoL tournaments",
     "url": "https://bo3.gg/lol/tournaments", "kind": "match-centre"},
    {"slug": "esportbet_lol", "name": "EsportBet LoL (lists Arabian 2nd / PRM 2. Liga)",
     "url": "https://esportbet.com/league-of-legends/", "kind": "aggregator"},
    {"slug": "liquipedia_prime", "name": "Liquipedia Prime League (results coverage check)",
     "url": "https://liquipedia.net/leagueoflegends/Prime_League", "kind": "results"},
    # ---- credentialed odds APIs: record the gate, never circumvent it ----
    {"slug": "oddsapiio_sports", "name": "Odds-API.io sports index (no key)",
     "url": "https://api.odds-api.io/v3/sports", "kind": "odds-api"},
    {"slug": "oddsapiio_leagues", "name": "Odds-API.io esports leagues (no key)",
     "url": "https://api.odds-api.io/v3/leagues?sport=esports", "kind": "odds-api"},
    {"slug": "oddspapi_tournaments", "name": "OddsPapi LoL tournaments sportId=18 (no key)",
     "url": "https://api.oddspapi.io/v4/tournaments?sportId=18", "kind": "odds-api"},
] + [
    {"slug": f"kambi_{op}", "name": f"Kambi operator {op} LoL",
     "url": KAMBI.format(op=op), "kind": "kambi-operator"}
    for op in ("paf", "betsson", "coolbet", "ubdk", "ubfi", "ubbe", "ubit", "ubes", "ubuk")
]


def polymarket_census(control: list[dict], tail: list[dict]) -> dict:
    """Enumerate every open Polymarket LoL event title and join pairs decisively."""
    titles, questions = [], []
    pages = []
    for off in (0, 100, 200, 300, 400):
        url = (f"https://gamma-api.polymarket.com/events?closed=false&limit=100"
               f"&tag_slug=league-of-legends&offset={off}")
        st, data, err = get_json(url, retries=1)
        pages.append({"offset": off, "status": st,
                      "events": len(data) if isinstance(data, list) else None})
        if st != 200 or not isinstance(data, list) or not data:
            break
        for ev in data:
            titles.append(ev.get("title") or "")
            for mk in ev.get("markets") or []:
                questions.append(mk.get("question") or "")
    blob = "\n".join(titles + questions)
    # league census: suffix after the last " - " in event titles, counted
    leagues: dict[str, int] = {}
    for t in titles:
        league = t.rsplit(" - ", 1)[-1].strip() if " - " in t else t
        leagues[league] = leagues.get(league, 0) + 1
    return {
        "name": "Polymarket Gamma LoL census (offsets 0-400)",
        "pages": pages, "event_titles": len(titles), "markets": len(questions),
        "leagues_by_event_title": dict(sorted(leagues.items(), key=lambda kv: -kv[1])),
        "control_pair_hits": pair_hits(blob, control),
        "tail_pair_hits": pair_hits(blob, tail),
    }


def main() -> None:
    os.makedirs(RAW_DIR, exist_ok=True)
    control, tail = fixtures()
    log(f"hotspawn: {len(control)} control (Worlds) pairs, {len(tail)} tail pairs")
    tail_comps: dict[str, int] = {}
    for p in tail:
        tail_comps[p["competition"]] = tail_comps.get(p["competition"], 0) + 1

    rows = []
    for cand in CANDIDATES:
        st, body = http_get(cand["url"], headers=cand.get("headers"), timeout=25, retries=0)
        text = body[:MAX_BODY].decode("utf-8", "replace") if body else ""
        c_hits = pair_hits(text, control) if st == 200 else []
        t_hits = pair_hits(text, tail) if st == 200 else []
        # bounded raw preview for manual review (full bodies can be megabytes)
        with open(os.path.join(RAW_DIR, cand["slug"] + ".txt"), "w", encoding="utf-8") as fh:
            fh.write(text[:20000])
        verdict = ("pair_found_review_snippet" if t_hits else
                   "answered_no_tail_pairs" if st == 200 else "not_usable_http")
        rows.append({
            "slug": cand["slug"], "name": cand["name"], "kind": cand["kind"],
            "url": cand["url"], "status": st, "bytes": len(body or b""),
            "checked_utc": iso(now_utc()), "verdict": verdict,
            "control_pair_hits": [{"id": h["id"], "match": f'{h["team0"]} vs {h["team1"]}'}
                                  for h in c_hits],
            "tail_pair_hits": t_hits,
            "preview": text[:400].replace("\n", " "),
        })
        log(f"{cand['slug']}: HTTP {st} control={len(c_hits)} tail={len(t_hits)}")

    poly = polymarket_census(control, tail)
    log(f"polymarket census: {poly['event_titles']} events, "
        f"control={len(poly['control_pair_hits'])} tail={len(poly['tail_pair_hits'])}")

    doc = {
        "generated_utc": iso(now_utc()),
        "session": "666de992",
        "question": "Does any reachable venue list today's low-tier Hotspawn LoL pairs?",
        "method": ("Live Hotspawn scheduled feed split into Worlds control pairs vs tail pairs; "
                   "each venue response searched for BOTH team names (accent-normalised). "
                   "Pair found != price verified: snippets require manual review."),
        "inventory": {"control_pairs": len(control), "tail_pairs": len(tail),
                      "tail_competitions": dict(sorted(tail_comps.items(), key=lambda kv: -kv[1]))},
        "tail_pairs_searched": tail,
        "venues": rows,
        "polymarket_census": poly,
        "summary": {
            "venues_probed": len(rows) + 1,
            "venues_with_tail_pairs": [r["slug"] for r in rows if r["tail_pair_hits"]]
                                      + (["polymarket_census"] if poly["tail_pair_hits"] else []),
            "venues_with_control_pairs": [r["slug"] for r in rows if r["control_pair_hits"]],
        },
    }
    save_json(OUT, doc)
    log(f"wrote {OUT}: tail-pair venues = {doc['summary']['venues_with_tail_pairs'] or 'NONE'}")


if __name__ == "__main__":
    main()
