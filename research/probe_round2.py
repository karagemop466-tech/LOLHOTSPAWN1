#!/usr/bin/env python3
"""Round-2 availability probe for LoL odds endpoints.

The first probe (tools/probe_sources.py / data/source_probes.json) established which
*bookmaker landing pages* answer.  Several answered with HTML but no odds, so this
round targets the public JSON/GraphQL endpoints those same books use to hydrate their
pages, plus a few comparison sites that publish prices server-side.

Nothing here writes to the published dataset.  Output is research/probe_round2.json
and, for the endpoints that answer with a body, a trimmed copy under
research/raw/round2/ so a parser can be written against real bytes rather than a guess.
"""
from __future__ import annotations

import json
import pathlib
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "research" / "raw" / "round2"
OUT = ROOT / "research" / "probe_round2.json"

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
)

# (name, url, extra headers, keep raw body?)
TARGETS: list[tuple[str, str, dict, bool]] = [
    # --- DraftKings: public sportscontent API used by the web client -------------
    ("dk:leagues-index", "https://sportsbook-nash.draftkings.com/api/sportscontent/dkusoh/v1/leagues?format=json", {}, True),
    ("dk:sports", "https://sportsbook-nash.draftkings.com/api/sportscontent/dkusoh/v1/sports", {}, True),
    ("dk:esports-page", "https://sportsbook.draftkings.com/leagues/esports/league-of-legends", {}, True),
    # --- FanDuel: content-managed page with the public web key -------------------
    (
        "fd:lol-page",
        "https://sportsbook.fanduel.com/api/content-managed-page?page=CUSTOM&customPageId=league-of-legends"
        "&_ak=FhMFpcPWXMeyZxOxGExQFdENwDQ&timezone=America%2FNew_York",
        {},
        True,
    ),
    ("fd:esports-menu", "https://sportsbook.fanduel.com/api/navigation/esports?_ak=FhMFpcPWXMeyZxOxGExQFdENwDQ", {}, True),
    # --- Kambi / Unibet: offering API needs a full parameter set ------------------
    (
        "kambi:esports",
        "https://eu-offering-api.kambicdn.com/offering/v2018/ubus/listView/esports.json"
        "?lang=en_GB&market=GB&client_id=2&channel_id=1&ncid=1",
        {},
        True,
    ),
    ("kambi:lol", "https://eu-offering-api.kambicdn.com/offering/v2018/ubus/group.json?lang=en_GB&market=GB&client_id=2&channel_id=1&path=esports", {}, True),
    # --- Rivalry: GraphQL endpoint behind the LoL page ---------------------------
    ("rivalry:graphql", "https://rivalry.com/graphql", {}, False),
    # --- 1xBet: line feed used by the SPA ---------------------------------------
    (
        "1xbet:linefeed",
        "https://1xbet.com/LineFeed/Get1x2_VZip?sports=1&count=50&lng=en&mode=4&country=190&getEmpty=true",
        {},
        True,
    ),
    # --- BetOnline / SportsBetting.ag: the odds API behind the coupon ------------
    ("betonline:coupon", "https://www.betonline.ag/sportsbook/esports", {}, True),
    # --- Comparison sites that sometimes publish server-side prices --------------
    ("oddsportal:lol-fr", "https://www.oddsportal.com/esports/league-of-legends/results/", {}, False),
    ("egamersworld:bets", "https://egamersworld.com/lol/bets", {}, False),
    ("oddspedia:api", "https://oddspedia.com/api/v1/getMatchList?language=en&sport=league-of-legends", {}, True),
    # --- Prediction markets: look for LoL series beyond the one ticker -----------
    ("kalshi:lol-series", "https://api.elections.kalshi.com/trade-api/v2/series?category=Esports", {}, True),
    ("kalshi:search", "https://api.elections.kalshi.com/trade-api/v2/events?status=open&limit=200&with_nested_markets=false", {}, True),
    ("polymarket:lol-search", "https://gamma-api.polymarket.com/public-search?q=league%20of%20legends&limit_per_type=20", {}, True),
    ("polymarket:lol-tag", "https://gamma-api.polymarket.com/events?closed=false&limit=100&tag_slug=league-of-legends", {}, True),
    # --- Community/stat sites: can they feed the model rather than the market? ---
    ("golgg:lol", "https://gol.gg/esports/home/", {}, False),
    ("lolesports:schedule", "https://esports-api.lolesports.com/persisted/gw/getSchedule?hl=en-US", {"x-api-key": "0TvQnueqKa5mxJntVWt0w4LpLssiF19a8wLoPLdDzR2q8VcR9dVkTv2Q"}, True),
]


def fetch(name: str, url: str, headers: dict, keep: bool) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*", **headers})
    rec: dict = {"name": name, "url": url}
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read()
            rec.update(status=r.status, bytes=len(body), ctype=r.headers.get("content-type", ""))
            head = body[:400].decode("utf-8", "replace")
            rec["snippet"] = " ".join(head.split())[:240]
            markers = []
            for m in ("__NEXT_DATA__", "__APOLLO_STATE__", "__INITIAL_STATE__", "application/json", "odds", "moneyline"):
                if m.encode() in body[:400000]:
                    markers.append(m)
            rec["markers"] = markers
            rec["has_lol"] = b"League of Legends" in body or b"league-of-legends" in body
            if keep:
                RAW.mkdir(parents=True, exist_ok=True)
                safe = name.replace(":", "_")
                ext = "json" if "json" in rec["ctype"] else "html"
                (RAW / f"{safe}.{ext}").write_bytes(body[:1_500_000])
                rec["saved"] = f"research/raw/round2/{safe}.{ext}"
    except urllib.error.HTTPError as e:
        rec.update(status=e.code, error="HTTPError", bytes=0)
        try:
            rec["snippet"] = " ".join(e.read()[:200].decode("utf-8", "replace").split())
        except Exception:
            pass
    except Exception as e:  # noqa: BLE001 - any transport failure is just "unreachable"
        rec.update(status=None, error=type(e).__name__, detail=str(e)[:160], bytes=0)
    return rec


def main() -> int:
    results = [fetch(*t) for t in TARGETS]
    OUT.write_text(json.dumps({"probed_utc": __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                               "targets": len(results), "results": results}, indent=1) + "\n")
    for r in results:
        print(f"{str(r.get('status')):>5} {r['name']:26} {r.get('bytes', 0):>8} {r.get('ctype','')[:28]:28} "
              f"{'LOL' if r.get('has_lol') else '   '} {r.get('error','')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
