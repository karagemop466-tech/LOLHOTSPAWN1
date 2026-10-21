#!/usr/bin/env bash
# One-off diagnostics: understand how play.hotspawn.com/lol-pickems is delivered
# and which external odds endpoints are reachable from a GitHub runner.
set -u
UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'

echo "=== 1. lol-pickems raw fetch ==="
code=$(curl -sS -A "$UA" -m 60 -o /tmp/lol.html -w '%{http_code}' https://play.hotspawn.com/lol-pickems)
echo "status=$code bytes=$(wc -c </tmp/lol.html)"
echo "--- head ---"
head -c 1200 /tmp/lol.html
echo
echo "--- markers ---"
for m in '__NEXT_DATA__' 'window.__' 'application/ld+json' 'data-reactroot' '1081205' 'api/' 'self.__next_f' '__NUXT__'; do
  printf '%-22s %s\n' "$m" "$(grep -o "$m" /tmp/lol.html | wc -l)"
done
echo "--- script/link srcs ---"
grep -oE '<(script|link)[^>]{0,200}' /tmp/lol.html | head -40
echo "--- api-ish strings ---"
grep -oE '"/[a-zA-Z0-9_/-]*api[a-zA-Z0-9_/-]*"' /tmp/lol.html | sort -u | head -40
echo "--- snippet around a known match id ---"
grep -o '.\{600\}1081205.\{900\}' /tmp/lol.html | head -c 3000
echo
echo "=== 2. next data json if present ==="
python3 - <<'PY'
import re,sys
h=open('/tmp/lol.html',encoding='utf-8',errors='replace').read()
m=re.search(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>',h,re.S)
print('NEXT_DATA found:', bool(m), len(m.group(1)) if m else 0)
for name in ['__NUXT__','__INITIAL_STATE__','__APOLLO_STATE__']:
    print(name, name in h)
PY
echo
echo "=== 3. external source reachability ==="
probe () { printf '%-52s ' "$1"; curl -sS -A "$UA" -m 30 -o /tmp/p.out -w '%{http_code} %{size_download}\n' "$1" || echo "ERR"; }
probe "https://gamma-api.polymarket.com/events?limit=1&closed=false"
probe "https://gamma-api.polymarket.com/markets?limit=1"
probe "https://lol.fandom.com/api.php?action=cargoquery&format=json&limit=1&tables=ScoreboardGames&fields=OverviewPage"
probe "https://liquipedia.net/leagueoflegends/api.php?action=query&format=json&meta=siteinfo"
probe "https://api.bo3.gg/api/v1/matches?page=1&limit=1&sort=start_time&filter%5Bdisciplines%5D%5B%5D=lol"
probe "https://www.oddspedia.com/api/v1/getMatchList?excludeColumns=&sport=esports"
probe "https://www.betexplorer.com/esports/"
probe "https://esport.betsson.com/"
probe "https://www.hotspawn.com/matches?game=league-of-legends"
probe "https://play.hotspawn.com/lol-pickems"
echo
echo "=== 4. polymarket LoL search ==="
curl -sS -A "$UA" -m 30 "https://gamma-api.polymarket.com/public-search?q=League%20of%20Legends&limit_per_type=5" -o /tmp/pm.json -w 'search=%{http_code}\n'
head -c 800 /tmp/pm.json
echo
echo "=== 5. leaguepedia sample row ==="
curl -sS -A "$UA" -m 30 "https://lol.fandom.com/api.php?action=cargoquery&format=json&limit=3&tables=MatchSchedule&fields=MatchSchedule.OverviewPage,MatchSchedule.Team1,MatchSchedule.Team2,MatchSchedule.StartTime,MatchSchedule.BestOf&where=MatchSchedule.StartTime%3E%272026-10-20%27&order_by=MatchSchedule.StartTime" -o /tmp/lp.json -w 'lp=%{http_code}\n'
head -c 1200 /tmp/lp.json
