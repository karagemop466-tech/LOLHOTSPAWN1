#!/usr/bin/env bash
# Endpoint reachability probe. Prints status code, content-type, size and a preview.
set -u
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'

probe() {
  local label="$1"; shift
  local url="$1"; shift
  local hdr=()
  while [ "$#" -gt 0 ]; do hdr+=(-H "$1"); shift; done
  echo "===== $label"
  echo "URL: $url"
  local out code
  out=$(mktemp)
  code=$(curl -sS -L --max-time 40 -A "$UA" "${hdr[@]}" -o "$out" -w '%{http_code} %{content_type} %{size_download}' "$url" 2>&1) || echo "curl_error=$?"
  echo "RESULT: $code"
  head -c 700 "$out" | tr -d '\000' | tr '\n' ' '
  echo
  echo
  rm -f "$out"
}

echo "### RUN CONTEXT"; date -u; echo

probe "hotspawn-fixtures-api" "https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=lol&status=scheduled&tenantId=1"
probe "hotspawn-fixtures-api-noparam" "https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures"
probe "hotspawn-play-ssr" "https://play.hotspawn.com/lol-pickems"
probe "lolesports-schedule" "https://esports-api.lolesports.com/persisted/gw/getSchedule?hl=en-US" "x-api-key: 0TvQnueqKa5mxJntVWt0w4LpLfEkrV1Ta8rQBb9Z"
probe "pinnacle-sports" "https://guest.api.arcadia.pinnacle.com/0.1/sports" "x-api-key: CmX2KcMrXuFmNg6YFbmTxE0y9CIrOi0R"
probe "polymarket-gamma-lol" "https://gamma-api.polymarket.com/events?closed=false&limit=5&tag_slug=league-of-legends"
probe "polymarket-gamma-search" "https://gamma-api.polymarket.com/public-search?q=league%20of%20legends&limit_per_type=5"
probe "leaguepedia-cargo" "https://lol.fandom.com/api.php?action=cargoquery&format=json&tables=MatchSchedule&fields=MatchSchedule.MatchId,MatchSchedule.Team1,MatchSchedule.Team2,MatchSchedule.DateTime_UTC&limit=3&order_by=MatchSchedule.DateTime_UTC%20DESC"
probe "egamersworld-lol" "https://egamersworld.com/lo-l/matches"
probe "oddsportal-lol" "https://www.oddsportal.com/esports/league-of-legends/"
probe "ggbet" "https://gg.bet/en/esports/league-of-legends"
probe "bcgame" "https://bc.game/sports"
probe "bo3gg" "https://bo3.gg/matches/league-of-legends"
probe "golgg" "https://gol.gg/tournament/list/"
probe "leaguepedia-leagues" "https://lol.fandom.com/api.php?action=cargoquery&format=json&tables=Tournaments&fields=Tournaments.Name,Tournaments.DateStart&where=Tournaments.Name%20LIKE%20%27Prime%20League%27&limit=5"
probe "theoddsapi" "https://api.the-odds-api.com/v4/sports/?apiKey=DEMO"
