#!/usr/bin/env python3
"""Diagnostics round 7: can we read official/community match results at scale?
That is the prerequisite for originating our own lines on unpriced matches."""
import gzip
import json
import time
import urllib.parse
import urllib.request

UA = "LOLHotspawnPicks/1.0 (+https://github.com/karagemop466-tech/LOLHOTSPAWN1)"


def get(url, headers=None):
    h = {"User-Agent": UA, "Accept": "application/json, text/html;q=0.9,*/*;q=0.8",
         "Accept-Encoding": "gzip"}
    h.update(headers or {})
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=60) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        return r.status, raw


def probe(name, url, headers=None):
    try:
        code, body = get(url, headers)
        print(f"[{code}] {name} ({len(body)}b): {body[:300]!r}")
        return body
    except Exception as e:
        print(f"[ERR] {name}: {e}")
        return None


print("=== Leaguepedia: CargoExport (bypasses the API rate limiter?) ===")
q = ("https://lol.fandom.com/index.php?title=Special:CargoExport&tables=MatchSchedule"
     "&fields=MatchSchedule.OverviewPage,MatchSchedule.Team1,MatchSchedule.Team2,"
     "MatchSchedule.StartTime,MatchSchedule.Winner,MatchSchedule.BestOf"
     "&where=" + urllib.parse.quote("MatchSchedule.StartTime >= '2026-09-15'") +
     "&order_by=" + urllib.parse.quote("MatchSchedule.StartTime") +
     "&limit=5&format=json")
probe("CargoExport", q)
time.sleep(3)

print("\n=== Leaguepedia: api.php with maxlag + delay ===")
probe("cargoquery maxlag",
      "https://lol.fandom.com/api.php?action=cargoquery&format=json&maxlag=5&limit=2"
      "&tables=MatchSchedule&fields=MatchSchedule.Team1,MatchSchedule.Team2")
time.sleep(4)

print("\n=== lolesports official API with the public web key ===")
probe("getLeagues",
      "https://esports-api.lolesports.com/persisted/gw/getLeagues?hl=en-US",
      {"X-API-Key": "0TvQnueqKa5mxJntVWt0w4LpLssiF19a8wLoPLD9x7gGSFh6aGZRpw",
       "Referer": "https://lolesports.com/"})

print("\n=== Liquipedia search for the German divisions ===")
try:
    s = ("https://liquipedia.net/leagueoflegends/api.php?action=query&format=json&list=search"
         "&srsearch=" + urllib.parse.quote("Prime League 2026 Fall 2nd Division") + "&srlimit=5")
    code, body = get(s)
    d = json.loads(body)
    for r in d.get("query", {}).get("search", []):
        print("  -", r["title"])
except Exception as e:
    print("search err", e)

print("\n=== Liquipedia: does a tournament page contain parseable results? ===")
for page in ["Prime_League/2026_Season/Fall/2nd_Division",
             "Prime_League/2026/Fall/2nd_Division",
             "Prime_League/2026_Season/Fall"]:
    try:
        code, body = get("https://liquipedia.net/leagueoflegends/api.php?action=parse&format=json"
                         "&prop=text&page=" + urllib.parse.quote(page))
        d = json.loads(body)
        if "error" in d:
            print(f"  {page}: {d['error']['code']}")
            continue
        text = d["parse"]["text"]["*"]
        print(f"  {page}: {len(text)}b, matchlist={'matchlist' in text}, "
              f"brkts={'brkts' in text}, opponent={text.count('brkts-opponent')}")
        idx = text.find("brkts-opponent")
        if idx > 0:
            print("    snippet:", text[idx - 300:idx + 500].replace("\n", " ")[:700])
        break
    except Exception as e:
        print("  parse err", page, e)
    time.sleep(3)
