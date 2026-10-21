#!/usr/bin/env python3
"""Round 6: Leaguepedia coverage per Hotspawn competition using OverviewPage."""
import json, os, time, urllib.request, urllib.error, urllib.parse, gzip, io, collections, re, unicodedata

UA = "LOLHotspawnResearch/1.0 (github.com/karagemop466-tech/LOLHOTSPAWN1)"
OUT = "evidence/probe6"
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


def cargo(fields, where=None, limit=500, offset=0, order_by=None, tables="MatchSchedule"):
    p = {"tables": tables, "fields": fields, "limit": str(limit), "offset": str(offset), "format": "json"}
    if where:
        p["where"] = where
    if order_by:
        p["order_by"] = order_by
    st, body = get("https://lol.fandom.com/wiki/Special:CargoExport?" + urllib.parse.urlencode(p))
    if st != 200:
        return st, None, body[:300].decode("utf-8", "replace")
    try:
        return st, json.loads(body), ""
    except Exception:
        return st, None, body[:300].decode("utf-8", "replace")


# all matches since 2026-06-01 (series level)
rows, off = [], 0
while off < 6000:
    st, data, err = cargo(
        "MatchSchedule.MatchId,MatchSchedule.OverviewPage,MatchSchedule.Team1,MatchSchedule.Team2,"
        "MatchSchedule.Winner,MatchSchedule.Team1Score,MatchSchedule.Team2Score,MatchSchedule.DateTime_UTC,"
        "MatchSchedule.BestOf,MatchSchedule.Tab,MatchSchedule.Round",
        where="MatchSchedule.DateTime_UTC >= '2026-06-01 00:00:00'",
        limit=500, offset=off, order_by="MatchSchedule.DateTime_UTC DESC")
    if not data:
        print("stop at", off, "err:", err)
        break
    rows.extend(data)
    if len(data) < 500:
        break
    off += 500
    time.sleep(0.7)

with open(os.path.join(OUT, "matches_since_june.json"), "w") as f:
    json.dump(rows, f)

def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", s)).strip()

# Hotspawn fixtures
st, b = get("https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=lol&status=scheduled&tenantId=1")
fx = json.loads(b)
with open(os.path.join(OUT, "hotspawn_fixtures.json"), "w") as f:
    json.dump(fx, f)

lp_teams = collections.defaultdict(int)
for r in rows:
    for k in ("Team1", "Team2"):
        if r.get(k) and r[k] != "TBD":
            lp_teams[norm(r[k])] += 1

page_counts = collections.Counter(r.get("OverviewPage") or "" for r in rows)
report = {"rows": len(rows), "teams": len(lp_teams), "pages_top": page_counts.most_common(80),
          "per_competition": {}}
for comp in sorted({f["competition_name"] for f in fx}):
    sub = [f for f in fx if f["competition_name"] == comp]
    both = one = none = 0
    for f in sub:
        a, b2 = norm(f["participants0_name"]), norm(f["participants1_name"])
        ha, hb = lp_teams.get(a, 0), lp_teams.get(b2, 0)
        if ha and hb:
            both += 1
        elif ha or hb:
            one += 1
        else:
            none += 1
    report["per_competition"][comp] = {"matches": len(sub), "both_teams_in_lp": both,
                                       "one_team_in_lp": one, "no_team_in_lp": none}

# direct LIKE checks for the obscure competitions
checks = ["RIVALS LEAGUE", "Prime League", "Komplettligaen", "Tunisian", "Icelandic",
          "Arabian League", "4 Nations", "Superstrike", "Benelux", "LigaGG", "Worlds 2026"]
like = {}
for c in checks:
    st, data, err = cargo("MatchSchedule.OverviewPage,MatchSchedule.Team1,MatchSchedule.Team2,MatchSchedule.DateTime_UTC",
                          where=f"MatchSchedule.OverviewPage LIKE '%{c}%' AND MatchSchedule.DateTime_UTC >= '2026-06-01 00:00:00'",
                          limit=20, order_by="MatchSchedule.DateTime_UTC DESC")
    like[c] = {"status": st, "rows": len(data) if data else 0, "err": err,
               "sample": (data or [])[:3]}
    time.sleep(0.7)
report["like_checks"] = like

with open(os.path.join(OUT, "coverage2.json"), "w") as f:
    json.dump(report, f, indent=1)

print(json.dumps(report["per_competition"], indent=1))
print("rows:", len(rows))
print(json.dumps({k: (v["rows"], v["status"]) for k, v in like.items()}, indent=0))
print(json.dumps(report["pages_top"][:25], indent=0)[:2000])
