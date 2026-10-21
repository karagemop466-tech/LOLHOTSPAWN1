#!/usr/bin/env python3
"""Round 5: debug CargoExport query syntax variants."""
import json, os, urllib.request, urllib.error, urllib.parse, gzip, io

UA = "LOLHotspawnResearch/1.0 (github.com/karagemop466-tech/LOLHOTSPAWN1)"
OUT = "evidence/probe5"
os.makedirs(OUT, exist_ok=True)


def get(url, timeout=60):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=timeout) as r:
            raw = r.read()
            if r.headers.get("Content-Encoding") == "gzip":
                raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
            return r.status, raw
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:  # noqa
        return -1, str(e).encode()


variants = {
    "v1_no_where": {"tables": "MatchSchedule", "fields": "MatchSchedule.MatchId,MatchSchedule.Team1,MatchSchedule.Team2,MatchSchedule.Tournament", "limit": "3"},
    "v2_where_datetime": {"tables": "MatchSchedule", "fields": "MatchSchedule.MatchId,MatchSchedule.Team1,MatchSchedule.Team2,MatchSchedule.Tournament,MatchSchedule.DateTime_UTC", "limit": "3", "where": "MatchSchedule.DateTime_UTC >= '2026-05-01 00:00:00'"},
    "v3_where_like": {"tables": "MatchSchedule", "fields": "MatchSchedule.MatchId,MatchSchedule.Team1,MatchSchedule.Team2,MatchSchedule.Tournament", "limit": "3", "where": "MatchSchedule.Tournament LIKE '%Prime League%'"},
    "v4_where_like_rivals": {"tables": "MatchSchedule", "fields": "MatchSchedule.MatchId,MatchSchedule.Team1,MatchSchedule.Team2,MatchSchedule.Tournament", "limit": "5", "where": "MatchSchedule.Tournament LIKE '%RIVALS LEAGUE%'"},
    "v5_orderby": {"tables": "MatchSchedule", "fields": "MatchSchedule.MatchId,MatchSchedule.Tournament,MatchSchedule.DateTime_UTC", "limit": "3", "order_by": "MatchSchedule.DateTime_UTC DESC"},
    "v6_tournaments": {"tables": "Tournaments", "fields": "Tournaments.Name,Tournaments.DateStart", "limit": "5", "where": "Tournaments.DateStart >= '2026-08-01'"},
    "v7_scores": {"tables": "MatchSchedule", "fields": "MatchSchedule.MatchId,MatchSchedule.Team1Score,MatchSchedule.Team2Score,MatchSchedule.Winner,MatchSchedule.BestOf", "limit": "3"},
}
out = {}
for k, params in variants.items():
    url = "https://lol.fandom.com/wiki/Special:CargoExport?" + urllib.parse.urlencode(params)
    st, body = get(url)
    out[k] = {"url": url, "status": st, "body": body[:2000].decode("utf-8", "replace")}
with open(os.path.join(OUT, "cargo_variants.json"), "w") as f:
    json.dump(out, f, indent=1)
for k, v in out.items():
    print("=====", k, v["status"])
    print(v["body"][:500].replace("\n", " "))
    print()
