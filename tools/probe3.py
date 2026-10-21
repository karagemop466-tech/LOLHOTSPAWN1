#!/usr/bin/env python3
"""Round 3 probe: bo3.gg API surface, Pinnacle LoL extraction, Leaguepedia alternatives."""
import json, os, time, urllib.request, urllib.error, gzip, io

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
OUT = "evidence/probe3"
os.makedirs(OUT, exist_ok=True)
summary = []


def get(url, headers=None, timeout=45):
    h = {"User-Agent": UA, "Accept": "*/*"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            if r.headers.get("Content-Encoding") == "gzip":
                raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
            return r.status, raw
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:  # noqa
        return -1, str(e).encode()


def save(name, data):
    with open(os.path.join(OUT, name), "wb") as f:
        f.write(data)


def note(label, url, status, body, preview=400, maxsize=250000):
    if len(body) > maxsize:
        body = body[:maxsize]
    save(label + ".txt", body)
    summary.append(f"===== {label}\nurl: {url}\nstatus: {status}\nsize: {len(body)}\npreview: {body[:preview].decode('utf-8', 'replace')}\n")


# ---------- Pinnacle: compact LoL extract ----------
st, body = get("https://guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups",
               {"x-api-key": "CmX2KcMrXuFmNg6YFbmTxE0y9CIrOi0R"})
lol = []
if st == 200:
    data = json.loads(body)
    for m in data:
        lg = m.get("league", {})
        name = (lg.get("name") or "") + " " + str((lg.get("sport") or {}).get("name") or "")
        if "league of legends" in name.lower():
            lol.append({
                "id": m["id"], "league": lg.get("name"), "league_id": lg.get("id"),
                "startTime": m.get("startTime"), "type": m.get("type"), "parent": m.get("parent"),
                "participants": [p.get("name") for p in m.get("participants", [])],
                "totalMarketCount": m.get("totalMarketCount"),
            })
note("pinnacle-lol-extract", "https://guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups", 200,
     json.dumps({"count": len(data), "lol": lol}, indent=1).encode(), preview=1500)

if lol:
    mid = [m for m in lol if m["type"] == "matchup"][0]["id"] if any(m["type"] == "matchup" for m in lol) else lol[0]["id"]
    st2, b2 = get(f"https://guest.api.arcadia.pinnacle.com/0.1/matchups/{mid}/markets/related/straight",
                  {"x-api-key": "CmX2KcMrXuFmNg6YFbmTxE0y9CIrOi0R"})
    note("pinnacle-markets-sample", f"https://guest.api.arcadia.pinnacle.com/0.1/matchups/{mid}/markets/related/straight",
         st2, b2, preview=2500)

# ---------- bo3.gg ----------
probes = {
    "bo3-tournaments-lol": "https://api.bo3.gg/api/v1/tournaments?filter%5Bgames%5D%5B%5D=league-of-legends&page=1&per_page=50&sort=-start_date",
    "bo3-matches-upcoming": "https://api.bo3.gg/api/v1/matches?filter%5Bgames%5D%5B%5D=league-of-legends&page=1&per_page=20&sort=start_date",
    "bo3-match-detail": "https://api.bo3.gg/api/v1/matches/1?with%5B%5D=teams&with%5B%5D=tournament",
    "bo3-team": "https://api.bo3.gg/api/v1/teams/667?with%5B%5D=players",
    "bo3-odds": "https://api.bo3.gg/api/v1/matches/1/bets",
    "bo3-odds2": "https://api.bo3.gg/api/v1/bets?match_id=1",
    "bo3-odds3": "https://api.bo3.gg/api/v1/matches/1/odds",
    "bo3-html-lol": "https://bo3.gg/league-of-legends/matches",
}
for label, url in probes.items():
    st, b = get(url)
    note(label, url, st, b, preview=600)
    time.sleep(1)

# ---------- Leaguepedia alternatives ----------
st, b = get("https://lol.fandom.com/wiki/Special:CargoExport?tables=MatchSchedule&fields=MatchSchedule.MatchId,MatchSchedule.Team1,MatchSchedule.Team2,MatchSchedule.DateTime_UTC,MatchSchedule.Winner&limit=3&order_by=MatchSchedule.DateTime_UTC+DESC&format=json")
note("leaguepedia-cargoexport", "https://lol.fandom.com/wiki/Special:CargoExport", st, b, preview=600)
time.sleep(5)
st, b = get("https://lol.fandom.com/api.php?action=cargoquery&format=json&tables=Tournaments&fields=Tournaments.Name,Tournaments.DateStart&limit=2",
            {"User-Agent": "LOLHotspawnResearch/1.0 (contact: repo owner)"})
note("leaguepedia-retry", "https://lol.fandom.com/api.php", st, b, preview=600)
time.sleep(2)
st, b = get("https://liquipedia.net/leagueoflegends/api.php?action=query&list=recentchanges&rclimit=2&format=json")
note("liquipedia-api", "https://liquipedia.net/leagueoflegends/api.php", st, b, preview=600)

with open(os.path.join(OUT, "summary.txt"), "w") as f:
    f.write("\n".join(summary))
print("\n".join(summary)[:6000])
