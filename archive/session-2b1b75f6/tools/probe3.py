#!/usr/bin/env python3
"""Diagnostics round 3: shape of Pinnacle / Bovada / Polymarket / bo3.gg LoL payloads."""
import json
import re
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def get(url, headers=None):
    h = {"User-Agent": UA, "Accept": "application/json"}
    h.update(headers or {})
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()


def j(url, headers=None):
    return json.loads(get(url, headers))


def main():
    print("=== PINNACLE sports list (esports) ===")
    sports = j("https://guest.api.arcadia.pinnacle.com/0.1/sports")
    for s in sports:
        if "league" in s["name"].lower() or "esport" in s["name"].lower():
            print(" ", s["id"], s["name"], s["matchupCount"])

    print("\n=== PINNACLE sport 12 sample matchups ===")
    mus = j("https://guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups?brandId=0")
    print("count:", len(mus))
    print("sample keys:", list(mus[0].keys()))
    print("first 3 parent/league:", [(m.get("parent"), m.get("league"), m.get("type"), m.get("units"))
                                     for m in mus[:3]])
    lol = [m for m in mus if "league" in json.dumps(m.get("league", {})).lower()
           or "legend" in json.dumps(m.get("league", {})).lower()]
    print("with 'legend' in league:", len(lol))
    one = mus[0]
    print("one:", json.dumps({k: one.get(k) for k in
                              ("id", "type", "parent", "startTime", "participants", "league", "special")})[:1200])
    mid = one["id"]
    try:
        mk = j(f"https://guest.api.arcadia.pinnacle.com/0.1/matchups/{mid}/markets/related/straight")
        print("markets keys:", list(mk.keys()))
        print("markets sample:", json.dumps(mk.get("moneyline") and mk["moneyline"][:2])[:900])
    except Exception as e:
        print("markets err", e)

    print("\n=== BOVADA esports LoL coupon ===")
    b = j("https://www.bovada.lv/services/sports/event/coupon/events/A/description/esports/"
          "league-of-legends?marketFilterId=def&preMatchOnly=true&lang=en")
    print("groups:", len(b))
    ev = b[0]["events"][0]
    print("event keys:", list(ev.keys()))
    print("event:", json.dumps({k: ev.get(k) for k in ("id", "description", "link", "startTime", "competitors")})[:800])
    print("displayGroups:", json.dumps(ev.get("displayGroups"))[:800])

    print("\n=== POLYMARKET LoL events (open) ===")
    pm = j("https://gamma-api.polymarket.com/events?limit=100&closed=false&tag_slug=league-of-legends")
    print("events:", len(pm))
    for e in pm[:12]:
        print(" -", e["title"][:90], "| markets:", len(e.get("markets") or []))
    for e in pm:
        for m in (e.get("markets") or []):
            if " vs" in (m.get("question") or "").lower() or "vs." in (m.get("question") or "").lower():
                print("  MATCH MARKET:", m.get("question"), "| outcomes:", m.get("outcomes"),
                      "| prices:", m.get("outcomePrices"), "| closed:", m.get("closed"))
                break

    print("\n=== BO3.GG LoL matches ===")
    d = j("https://api.bo3.gg/api/v1/disciplines")
    print("disciplines:", [(x["id"], x["slug"]) for x in d["results"]])
    try:
        m = j("https://api.bo3.gg/api/v1/matches?filter%5Bdisciplines%5D%5B%5D=2&page=1&limit=1")
        print("matches meta:", m.get("total"))
        r = m["results"][0]
        print("match keys:", list(r.keys()))
        print("match sample:", json.dumps({k: r.get(k) for k in
                                          ("id", "name", "status", "start_time", "tournament", "teams")})[:900])
    except Exception as e:
        print("bo3 err", e)

    print("\n=== NG-STATE competitions ===")
    html = get("https://play.hotspawn.com/lol-pickems").decode("utf-8", "replace")
    state = json.loads(re.search(r'id="ng-state"[^>]*>(.*?)</script>', html, re.S).group(1))
    lst = state["1214417440"]["b"]
    print("matches:", len(lst))
    comps = {}
    for x in lst:
        comps.setdefault((x["competition_name"], x["tier"]), 0)
        comps[(x["competition_name"], x["tier"])] += 1
    for (c, t), n in sorted(comps.items()):
        print(f"  {n:3d}  {c}  [{t}]")
    print("one full record:", json.dumps(lst[0]))


if __name__ == "__main__":
    main()
