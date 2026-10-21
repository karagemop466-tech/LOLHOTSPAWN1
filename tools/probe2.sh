#!/usr/bin/env bash
# Round 2 probe: odds APIs + results sources.
set -u
mkdir -p evidence/probe2
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
SUMMARY=evidence/probe2/summary.txt
: > "$SUMMARY"

probe() {
  local label="$1"; shift
  local url="$1"; shift
  local hdr=() max=${MAXSIZE:-300000}
  while [ "$#" -gt 0 ]; do hdr+=(-H "$1"); shift; done
  local fn="evidence/probe2/$label.txt"
  local meta
  meta=$(curl -sS -L --max-time 45 -A "$UA" "${hdr[@]}" -o "$fn.raw" -w '%{http_code}|%{content_type}|%{size_download}|%{url_effective}' "$url" 2>evidence/probe2/.err) || meta="CURLFAIL|$(cat evidence/probe2/.err)"
  head -c "$max" "$fn.raw" > "$fn" 2>/dev/null; rm -f "$fn.raw"
  {
    echo "===== $label"
    echo "url: $url"
    echo "result: $meta"
    echo "preview: $(head -c 400 "$fn" | tr -d '\000' | tr '\n' ' ')"
    echo
  } >> "$SUMMARY"
}

echo "run started: $(date -u)" >> "$SUMMARY"

probe pinnacle-esports "https://guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups" "x-api-key: CmX2KcMrXuFmNg6YFbmTxE0y9CIrOi0R"
probe pinnacle-leagues "https://guest.api.arcadia.pinnacle.com/0.1/sports/12/leagues" "x-api-key: CmX2KcMrXuFmNg6YFbmTxE0y9CIrOi0R"
probe kambi-ubus-esports "https://eu-offering-api.kambicdn.com/offering/v2018/ubus/listView/esports.json?lang=en_US&market=US&useCombined=true&useCombinedLive=true"
probe kambi-ubat-esports "https://eu-offering-api.kambicdn.com/offering/v2018/ubat/betoffer/group.json?lang=en_US&market=US&group=1000"
probe oddspedia-sports "https://oddspedia.com/api/v1/getSports"
probe bo3-api-matches "https://api.bo3.gg/api/v1/matches?filter%5Bgames%5D%5B%5D=league-of-legends&page=1&per_page=5"
probe bo3-gg-html "https://bo3.gg/league-of-legends/matches"
probe lolesports-leagues "https://esports-api.lolesports.com/persisted/gw/getLeagues?hl=en-US" "x-api-key: 0TvQnueqKa5mxJntVWt0w4LpLfEkrV1Ta8rQBb9Z"
sleep 3
probe leaguepedia-1 "https://lol.fandom.com/api.php?action=cargoquery&format=json&maxlag=5&tables=MatchSchedule&fields=MatchSchedule.MatchId,MatchSchedule.Team1,MatchSchedule.Team2,MatchSchedule.DateTime_UTC,MatchSchedule.Winner&limit=3&order_by=MatchSchedule.DateTime_UTC%20DESC" "User-Agent: LOLHotspawnResearch/1.0 (github.com/karagemop466-tech/LOLHOTSPAWN1)"
sleep 3
probe leaguepedia-2 "https://lol.fandom.com/api.php?action=cargoquery&format=json&maxlag=5&tables=Tournaments&fields=Tournaments.Name,Tournaments.DateStart,Tournaments.League&where=Tournaments.DateStart%20%3E%3D%20%272026-08-01%27&limit=10" "User-Agent: LOLHotspawnResearch/1.0 (github.com/karagemop466-tech/LOLHOTSPAWN1)"
probe betexplorer "https://www.betexplorer.com/esports/league-of-legends/"
probe odssapi "https://api.the-odds-api.com/v4/sports/esports_league_of_legends/odds/?regions=eu&markets=h2h&apiKey=REPLACE"
echo "run finished: $(date -u)" >> "$SUMMARY"
cat "$SUMMARY"
