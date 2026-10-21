#!/usr/bin/env python3
"""Round 4 probe: Leaguepedia coverage of the exact Hotspawn LoL competitions + Polymarket match markets."""
import json, os, time, urllib.request, urllib.error, urllib.parse, gzip, io, collections, re, unicodedata

UA = "LOLHotspawnResearch/1.0 (github.com/karagemop466-tech/LOLHOTSPAWN1)"
OUT = "evidence/probe4"
os.makedirs(OUT, exist_ok=True)


def get(url, headers=None, timeout=60):
    h = {"User-Agent": UA, "Accept": "*/*"}
    if headers:
        h.update(headers)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout) as r:
            raw = r.read()
            if r.headers.get("Content-Encoding") == "gzip":
                raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
            return r.status, raw
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:  # noqa
        return -1, str(e).encode()


def cargo(tables, fields, where=None, limit=500, offset=0, order_by=None):
    params = {
        "tables": tables,
        "fields": fields,
        "limit": str(limit),
        "offset": str(offset),
        "format": "json",
    }
    if where:
        params["where"] = where
    if order_by:
        params["order_by"] = order_by
    url = "https://lol.fandom.com/wiki/Special:CargoExport?" + urllib.parse.urlencode(params)
    st, body = get(url)
    if st != 200:
        return st, None
    try:
        return st, json.loads(body)
    except Exception:
        return st, None


# 1) Hotspawn fixtures
st, b = get("https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=lol&status=scheduled&tenantId=1")
fixtures = json.loads(b)
with open(os.path.join(OUT, "hotspawn_fixtures.json"), "w") as f:
    json.dump(fixtures, f)
comps = sorted({f["competition_name"] for f in fixtures})

# 2) Leaguepedia recent matches (since 2026-05-01), paged
rows = []
offset = 0
for _ in range(20):
    st, data = cargo(
        "MatchSchedule",
        "MatchSchedule.MatchId,MatchSchedule.Tournament,MatchSchedule.Team1,MatchSchedule.Team2,"
        "MatchSchedule.Winner,MatchSchedule.Team1Score,MatchSchedule.Team2Score,MatchSchedule.DateTime_UTC,"
        "MatchSchedule.BestOf,MatchSchedule.OverviewPage",
        where="MatchSchedule.DateTime_UTC >= '2026-05-01'",
        limit=500, offset=offset,
        order_by="MatchSchedule.DateTime_UTC DESC",
    )
    if not data:
        break
    rows.extend(data)
    if len(data) < 500:
        break
    offset += 500
    time.sleep(1)

with open(os.path.join(OUT, "leaguepedia_recent.json"), "w") as f:
    json.dump(rows, f)

# 3) coverage stats
def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

lp_teams = collections.Counter()
for r in rows:
    for k in ("Team1", "Team2"):
        if r.get(k) and r[k] != "TBD":
            lp_teams[norm(r[k])] += 1

report = {"fixtures": len(fixtures), "competitions": comps, "leaguepedia_rows": len(rows),
          "leaguepedia_teams": len(lp_teams), "per_competition": {}}
match_lp = collections.Counter()
for r in rows:
    t = r.get("Tournament") or ""
    match_lp[t] += 1
report["leaguepedia_tournaments_sample"] = sorted(match_lp.items(), key=lambda x: -x[1])[:60]

for comp in comps:
    fx = [f for f in fixtures if f["competition_name"] == comp]
    hit = 0
    exact_titles = set()
    for f in fx:
        a, b2 = norm(f["participants0_name"]), norm(f["participants1_name"])
        if lp_teams.get(a) or lp_teams.get(b2):
            hit += 1
    report["per_competition"][comp] = {"matches": len(fx), "with_any_leaguepedia_team": hit}

with open(os.path.join(OUT, "coverage.json"), "w") as f:
    json.dump(report, f, indent=1)

# 4) Polymarket match-level LoL markets
st, b = get("https://gamma-api.polymarket.com/events?closed=false&limit=100&tag_slug=league-of-legends")
try:
    pm = json.loads(b)
except Exception:
    pm = []
keep = []
for e in pm:
    for m in e.get("markets", []):
        q = m.get("question", "")
        if re.search(r"\bvs\b|\bBO\d\b", q, re.I):
            keep.append({"event": e.get("title"), "question": q, "outcomes": m.get("outcomes"),
                         "prices": m.get("outcomePrices"), "slug": m.get("slug"),
                         "startDate": m.get("startDate"), "volume": m.get("volume")})
with open(os.path.join(OUT, "polymarket_match_markets.json"), "w") as f:
    json.dump(keep, f, indent=1)

print(json.dumps({k: v for k, v in report.items() if k != "leaguepedia_tournaments_sample"}, indent=1)[:3000])
print("polymarket match-level markets:", len(keep))
print("leaguepedia sample tournaments:", json.dumps(report["leaguepedia_tournaments_sample"][:25], indent=0)[:1500])
