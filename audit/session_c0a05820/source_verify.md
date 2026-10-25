# Live source verification

- generated: `2026-10-25T15:20:33Z`
- dataset: `2026-10-25T14:58:31Z`
- rows: **234**
- result: **FAIL**

| Check | Result | Detail |
|---|---|---|
| every row carries a Hotspawn match card URL | PASS | 234/234 |
| priced rows sum to 100% (0.2pp) | PASS | [] |
| pick is the higher-probability side (ties may take either side) | PASS | [] |
| every row names a pick (priced or settlement/void) | PASS | 234/234 |
| published inventory == live Hotspawn feed (1:1 ids, freshness) | PASS | live=234 dataset=234 new on feed since publish=0 gone from feed=0 |
| control: Pinnacle guest endpoint probed (supplements, never replaces, the sibling-success proof) | PASS | status=403 cause=auth_required -> key proven by control: False |
| closed bookmaker boards are separated from auth failures | PASS | 1 board(s) answered 401/403 while the same key resolved elsewhere on the host; classified market_closed, disclosed below |
| no broken hotspawn card URL | PASS | 234/234 resolved this run; causes={'resolved': 234} |
| no broken market quote URL | PASS | 9/10 resolved this run; causes={'resolved': 9, 'market_closed': 1} |
| no broken venue receipt URL | FAIL | 32/50 resolved this run; causes={'resolved': 32, 'rate_limited': 9, 'auth_required': 8, 'market_closed': 1} |
| no broken leaguepedia page URL | PASS | 29/29 resolved this run; causes={'resolved': 29} |
| no broken pickem URL | PASS | 1/1 resolved this run; causes={'resolved': 1} |
| links to settled bookmaker boards are disclosed (not counted as rot) | PASS | 1 URL(s) answered 401/403 while the same credential resolved in this run: the market is closed, the link is historical |
| every row has at least one resolving piece of evidence (no broken links) | PASS | 234/234 rows; 0 unverified this run (throttle/expiry) |
| every published dashboard page resolves | PASS | 13/13 HTTP 2xx |
| table.html renders at least one row per match | PASS | rendered=234 rows=234 |
| every displayed win-probability pair adds to 100.0% | PASS | 0 row(s) off: [] |

## Resolution by evidence role

| Role | URLs | Resolved | Causes |
|---|---|---|---|
| hotspawn_card | 234 | 234 | `{'resolved': 234}` |
| market_quote | 10 | 9 | `{'resolved': 9, 'market_closed': 1}` |
| venue_receipt | 50 | 32 | `{'resolved': 32, 'rate_limited': 9, 'auth_required': 8, 'market_closed': 1}` |
| leaguepedia_page | 29 | 29 | `{'resolved': 29}` |
| pickem | 1 | 1 | `{'resolved': 1}` |
