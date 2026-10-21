#!/usr/bin/env python3
"""Diagnostics round 6: more books + an official-ish results feed for tier-2/3."""
import gzip
import json
import urllib.parse
import urllib.request

UA = "LOLHotspawnPicks/1.0 (+https://github.com/karagemop466-tech/LOLHOTSPAWN1)"
BROWSER = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
           "Chrome/124.0.0.0 Safari/537.36")


def get(url, headers=None):
    h = {"User-Agent": BROWSER, "Accept": "application/json, text/html;q=0.9,*/*;q=0.8",
         "Accept-Encoding": "gzip", "Accept-Language": "en-US,en;q=0.9"}
    h.update(headers or {})
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=60) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        return r.status, raw


def probe(name, url, headers=None):
    try:
        code, body = get(url, headers)
        print(f"[{code}] {name}: {len(body)}b :: {body[:160]!r}")
        return body
    except Exception as e:
        print(f"[ERR] {name}: {e}")
        return None


print("=== extra books ===")
probe("22bet feed", "https://22bet.com/LineFeed/Get1x2_VZip?sports=61&count=50&lng=en&mode=4&country=1&partner=1")
probe("1xbet alt host", "https://1xbet.com/LineFeed/Get1x2_VZip?sports=61&count=50&lng=en&mode=4&country=1&partner=1&getEmpty=true", {"User-Agent": BROWSER})
probe("oddspedia html", "https://oddspedia.com/esports/league-of-legends")
probe("oddsportal json-ish", "https://www.oddsportal.com/esports/league-of-legends/")
probe("betexplorer esports", "https://www.betexplorer.com/esports/league-of-legends/")
probe("egamersworld lol", "https://egamersworld.com/lol/matches")
probe("marathonbet esports", "https://www.marathonbet.com/en/betting/Esports/")
probe("betway esports", "https://sports.betway.com/en/sports/grp/esports/league-of-legends")
probe("tipico esports", "https://www.tipico.de/en/esports/")
probe("betano", "https://www.betano.de/esports/league-of-legends/")
probe("loot.bet api", "https://loot.bet/api/sports/1/matchups")
probe("thunderpick", "https://thunderpick.io/api/v1/matches")
probe("esportsbattle", "https://esportsbattle.com/api/matches")

print("\n=== bo3.gg shapes ===")
b = "https://api.bo3.gg/api/v1"
for path in ["/matches/1", "/teams/667", "/tournaments/9", "/matches?filter%5Btournament_ids%5D%5B%5D=9&limit=1",
             "/tournaments?filter%5Bdisciplines%5D%5B%5D=3&filter%5Bname%5D=Prime%20League&limit=3"]:
    body = probe("bo3 " + path, b + path)
    if body and path.endswith("/matches/1"):
        try:
            print("   match detail:", json.dumps(json.loads(body))[:600])
        except Exception:
            pass

print("\n=== primeleague (official ERL Germany) ===")
probe("primeleague api", "https://www.primeleague.gg/api/v1/matches?limit=2")
probe("primeleague site", "https://www.primeleague.gg/en/leagues/prm/26-27/fall/3rd-division")

print("\n=== liquipedia recent results probe (ACL) ===")
try:
    q = ("https://liquipedia.net/leagueoflegends/api.php?action=parse&format=json&page="
         "Prime_League/2026_Season/Fall/2nd_Division&prop=text")
    code, body = get(q, {"User-Agent": UA, "Accept": "application/json"})
    print("status", code, "len", len(body))
    txt = body.decode("utf-8", "replace")
    print("has matchlist:", "matchlist" in txt, "| has brkts:", "brkts" in txt)
    print(txt[:300])
except Exception as e:
    print("liquipedia err", e)
