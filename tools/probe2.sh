#!/usr/bin/env bash
# Round 2 diagnostics: ng-state structure + market source reachability.
set -u
UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'

echo "=== A. ng-state structure ==="
python3 tools/inspect_state.py 2>&1 | head -c 9000
echo
echo "=== B. market sources ==="
H=(-H "User-Agent: $UA" -H "Accept: application/json")
probe () { printf '%-72s ' "$1"; curl -sS -m 30 -o /tmp/o -w '%{http_code} %{size_download}\n' -A "$UA" "$1" || echo ERR; head -c 220 /tmp/o; echo; }

probe "https://guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups?brandId=0"
probe "https://guest.api.arcadia.pinnacle.com/0.1/sports"
probe "https://api.bo3.gg/api/v1/matches?page=1&limit=2&sort=start_time&filter%5Bdisciplines%5D%5B%5D=2"
probe "https://api.bo3.gg/api/v1/disciplines"
probe "https://gamma-api.polymarket.com/events?limit=5&closed=false&tag_slug=league-of-legends"
probe "https://gamma-api.polymarket.com/public-search?q=Worlds%202026&limit_per_type=3"
probe "https://esports-api.lolesports.com/persisted/gw/getLeagues?hl=en-US"
probe "https://liquipedia.net/leagueoflegends/api.php?action=query&format=json&meta=siteinfo&formatversion=2"
probe "https://www.betexplorer.com/esports/league-of-legends/worlds/"
probe "https://www.oddsportal.com/esports/league-of-legends/"
probe "https://www.gg.bet/en/league-of-legends"
probe "https://sportsbook.draftkings.com/leagues/esports"
probe "https://www.bovada.lv/services/sports/event/coupon/events/A/description/esports/league-of-legends"
probe "https://api.b365api.com/v1/event/list?sport_id=151&token=0"
probe "https://www.pinnacle.com/en/esports/league-of-legends/matchups"
