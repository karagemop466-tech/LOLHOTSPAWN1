#!/usr/bin/env python3
"""Diagnostics round 4: book coverage + model-data coverage."""
import gzip
import json
import re
import time
import urllib.parse
import urllib.request

UA = "LOLHotspawnPicksBot/1.0 (https://github.com/karagemop466-tech/LOLHOTSPAWN1; contact: repo issues)"
PIN_KEY = "CmX2KcMrXuFmNg6YFbmTxE0y9CIrOi0R"


def get(url, headers=None, gz=False):
    h = {"User-Agent": UA, "Accept": "application/json", "Accept-Encoding": "gzip"}
    h.update(headers or {})
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=90) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        return raw


def j(url, headers=None):
    return json.loads(get(url, headers))


def main():
    print("=== PINNACLE with guest key ===")
    try:
        mus = j("https://guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups?brandId=0",
                {"X-API-Key": PIN_KEY})
        leagues = {}
        for m in mus:
            ln = (m.get("league") or {}).get("name", "")
            leagues[ln] = leagues.get(ln, 0) + 1
        lol = {k: v for k, v in leagues.items() if "league of legends" in k.lower()}
        print("sport12 leagues:", len(leagues), "| LoL leagues:", lol)
        if lol:
            mid = [m["id"] for m in mus if (m.get("league") or {}).get("name") in lol][0]
            mk = j(f"https://guest.api.arcadia.pinnacle.com/0.1/matchups/{mid}/markets/related/straight",
                   {"X-API-Key": PIN_KEY})
            print("market keys:", list(mk.keys())[:10])
            print("moneyline:", json.dumps(mk.get("moneyline"))[:700])
    except Exception as e:
        print("pinnacle err:", e)

    print("\n=== BOVADA all LoL events ===")
    try:
        b = j("https://www.bovada.lv/services/sports/event/coupon/events/A/description/esports/"
              "league-of-legends?marketFilterId=def&preMatchOnly=true&lang=en")
        n = 0
        for g in b:
            for e in g.get("events", []):
                n += 1
                if n <= 40:
                    print(f"  {e['description']} | {e['startTime']} | {e.get('numMarkets')} mkts | {e['link']}")
        print("total events:", n)
    except Exception as e:
        print("bovada err:", e)

    print("\n=== POLYMARKET open LoL match markets ===")
    try:
        seen = 0
        for off in (0, 100, 200):
            pm = j(f"https://gamma-api.polymarket.com/events?limit=100&offset={off}&closed=false&"
                   "tag_slug=league-of-legends")
            for e in pm:
                if not e["title"].startswith("LoL:"):
                    continue
                for m in (e.get("markets") or []):
                    if "vs" in (m.get("question") or "").lower() and not m.get("closed"):
                        seen += 1
                        print("  ", m.get("question")[:80], "|", m.get("outcomePrices"),
                              "| vol", m.get("volumeNum") or m.get("volume"))
                        break
        print("open match markets:", seen)
    except Exception as e:
        print("polymarket err:", e)

    print("\n=== LEAGUEPEDIA coverage test ===")
    lp = "https://lol.fandom.com/api.php?action=cargoquery&format=json&limit=100"
    q = lp + ("&tables=MatchSchedule&fields=MatchSchedule.Team1,MatchSchedule.Team2,"
              "MatchSchedule.StartTime,MatchSchedule.OverviewPage,MatchSchedule.Winner,"
              "MatchSchedule.BestOf,MatchSchedule.Tab&where="
              + urllib.parse.quote("MatchSchedule.StartTime >= '2026-09-01' AND MatchSchedule.StartTime <= '2026-10-22'"))
    try:
        d = j(q)
        rows = d.get("cargoquery", [])
        print("rows:", len(rows), "| err:", d.get("error"))
        pages = {}
        for r in rows:
            t = r["title"]
            pages[t["OverviewPage"]] = pages.get(t["OverviewPage"], 0) + 1
        for k, v in sorted(pages.items(), key=lambda x: -x[1])[:30]:
            print(f"   {v:4d}  {k}")
    except Exception as e:
        print("leaguepedia err:", e)

    print("\n=== LEAGUEPEDIA team existence sample ===")
    for team in ["Galions", "Solary", "Sissi State Punks", "Emperors Bremen", "Ascent Gaming",
                 "Volda E-Sport", "Zahrouni Esports", "VfB eSports", "Kanji Esports AKA"]:
        try:
            qq = lp.replace("limit=100", "limit=5") + ("&tables=MatchSchedule&fields=MatchSchedule.Team1,"
                                                       "MatchSchedule.Team2,MatchSchedule.StartTime&where="
                                                       + urllib.parse.quote(f"MatchSchedule.Team1='{team}' OR MatchSchedule.Team2='{team}'"))
            d = j(qq)
            print(f"   {team}: {len(d.get('cargoquery', []))} rows", d.get("error", ""))
        except Exception as e:
            print(f"   {team}: ERR {e}")
        time.sleep(1.2)

    print("\n=== LIQUIPEDIA gzip test ===")
    try:
        d = j("https://liquipedia.net/leagueoflegends/api.php?action=query&format=json&meta=siteinfo")
        print("ok:", d["query"]["general"]["sitename"])
    except Exception as e:
        print("liquipedia err:", e)


if __name__ == "__main__":
    main()
