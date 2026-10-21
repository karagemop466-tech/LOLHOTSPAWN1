#!/usr/bin/env bash
# Endpoint reachability probe. Writes full responses to evidence/probe/ and a summary.
set -u
mkdir -p evidence/probe
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
SUMMARY=evidence/probe/summary.txt
: > "$SUMMARY"
i=0

probe() {
  local label="$1"; shift
  local url="$1"; shift
  local hdr=()
  while [ "$#" -gt 0 ]; do hdr+=(-H "$1"); shift; done
  i=$((i+1))
  local fn
  fn=$(printf "evidence/probe/%02d-%s.txt" "$i" "$(echo "$label" | tr -c 'a-zA-Z0-9._-' '-')")
  local meta
  meta=$(curl -sS -L --max-time 45 -A "$UA" "${hdr[@]}" -o "$fn" -w '%{http_code}|%{content_type}|%{size_download}|%{url_effective}' "$url" 2>evidence/probe/.err) || meta="CURLFAIL|$(cat evidence/probe/.err)"
  head -c 400000 "$fn" > "$fn.tmp" 2>/dev/null && mv "$fn.tmp" "$fn"
  {
    echo "===== $label"
    echo "url: $url"
    echo "result: $meta"
    echo "preview: $(head -c 500 "$fn" | tr -d '\000' | tr '\n' ' ')"
    echo
  } >> "$SUMMARY"
}

echo "run started: $(date -u)" >> "$SUMMARY"

probe hotspawn-fixtures-api "https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=lol&status=scheduled&tenantId=1"
probe hotspawn-fixtures-noparam "https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures"
probe hotspawn-play-ssr "https://play.hotspawn.com/lol-pickems"
probe hotspawn-wp-pickem-ids "https://www.hotspawn.com/wp-json/pickem/v1/fixtures?ids=1071214"
probe lolesports-schedule "https://esports-api.lolesports.com/persisted/gw/getSchedule?hl=en-US" "x-api-key: 0TvQnueqKa5mxJntVWt0w4LpLfEkrV1Ta8rQBb9Z"
probe pinnacle-sports "https://guest.api.arcadia.pinnacle.com/0.1/sports" "x-api-key: CmX2KcMrXuFmNg6YFbmTxE0y9CIrOi0R"
probe pinnacle-esports-matchups "https://guest.api.arcadia.pinnacle.com/0.1/sports/18/matchups" "x-api-key: CmX2KcMrXuFmNg6YFbmTxE0y9CIrOi0R"
probe polymarket-gamma-lol "https://gamma-api.polymarket.com/events?closed=false&limit=5&tag_slug=league-of-legends"
probe leaguepedia-cargo "https://lol.fandom.com/api.php?action=cargoquery&format=json&tables=MatchSchedule&fields=MatchSchedule.MatchId,MatchSchedule.Team1,MatchSchedule.Team2,MatchSchedule.DateTime_UTC&limit=3&order_by=MatchSchedule.DateTime_UTC%20DESC"
probe egamersworld-lol "https://egamersworld.com/lo-l/matches"
probe oddsportal-lol "https://www.oddsportal.com/esports/league-of-legends/"
probe gg-bet "https://gg.bet/en/esports/league-of-legends"
probe bo3gg "https://bo3.gg/matches/league-of-legends"
probe golgg "https://gol.gg/tournament/list/"
probe leaguepedia-prime-league "https://lol.fandom.com/api.php?action=cargoquery&format=json&tables=Tournaments&fields=Tournaments.Name,Tournaments.DateStart&where=Tournaments.Name%20LIKE%20%27Prime%20League%27&limit=5"

echo "run finished: $(date -u)" >> "$SUMMARY"
cat "$SUMMARY"
