#!/usr/bin/env python3
"""Diagnostics round 5: bo3.gg LoL coverage/ratings, Pinnacle moneyline shape."""
import json
import urllib.request

UA = "LOLHotspawnPicksBot/1.0 (https://github.com/karagemop466-tech/LOLHOTSPAWN1)"
PIN_KEY = "CmX2KcMrXuFmNg6YFbmTxE0y9CIrOi0R"


def get(url, headers=None):
    h = {"User-Agent": UA, "Accept": "application/json"}
    h.update(headers or {})
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=90) as r:
        return r.read()


def j(url, headers=None):
    return json.loads(get(url, headers))


B = "https://api.bo3.gg/api/v1"
print("=== bo3.gg LoL tournaments (upcoming/ongoing) ===")
try:
    t = j(B + "/tournaments?filter%5Bdisciplines%5D%5B%5D=3&page=1&limit=25&sort=-start_date")
    print("total:", t.get("total"))
    for x in t["results"][:25]:
        print(f"  {x['id']} {x['name'][:55]:55s} tier={x.get('tier')} status={x.get('status')} priz={x.get('prize_pool')}")
except Exception as e:
    print("err", e)

print("\n=== bo3.gg LoL matches (upcoming) ===")
for params in ["?filter%5Bdisciplines%5D%5B%5D=3&page=1&limit=5",
               "?filter%5Bdisciplines%5D%5B%5D=3&filter%5Bstatus%5D=upcoming&page=1&limit=5",
               "?filter%5Bdisciplines%5D%5B%5D=3&sort=-start_date&page=1&limit=5"]:
    try:
        m = j(B + "/matches" + params)
        print(params, "->", m.get("total"))
        if m.get("results"):
            r = m["results"][0]
            print("   keys:", list(r.keys()))
            print("   ", json.dumps({k: r.get(k) for k in
                                     ("id", "tournament_id", "team1_id", "team2_id", "start_date",
                                      "status", "tier", "rating", "stars", "bo_type")})[:500])
    except Exception as e:
        print(params, "err", e)

print("\n=== bo3.gg team shape ===")
try:
    mm = j(B + "/matches?filter%5Bdisciplines%5D%5B%5D=3&page=1&limit=1")
    r = mm["results"][0]
    t1 = j(B + f"/teams/{r['team1_id']}")
    print("team keys:", list((t1.get("results") or [t1])[0].keys()))
    print(json.dumps((t1.get("results") or [t1])[0])[:800])
except Exception as e:
    print("err", e)

print("\n=== bo3.gg odds endpoints ===")
for path in ["/matches/1/odds", "/odds?match_id=1", "/matches/1/bet_updates"]:
    try:
        print(path, "->", get(B + path)[:200])
    except Exception as e:
        print(path, "err", e)

print("\n=== PINNACLE moneyline (Worlds) ===")
try:
    mus = j("https://guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups?brandId=0",
            {"X-API-Key": PIN_KEY})
    lol = [m for m in mus if "League of Legends" in (m.get("league") or {}).get("name", "")]
    print("lol matchups:", len(lol))
    m0 = lol[0]
    print("participants:", [(p["name"], p.get("alignment")) for p in m0["participants"]])
    mk = j(f"https://guest.api.arcadia.pinnacle.com/0.1/matchups/{m0['id']}/markets/related/straight",
           {"X-API-Key": PIN_KEY})
    print("type:", type(mk).__name__, "len:", len(mk))
    ml = [x for x in mk if x.get("type") == "moneyline"]
    print("moneyline:", json.dumps(ml)[:800])
except Exception as e:
    print("err", e)
