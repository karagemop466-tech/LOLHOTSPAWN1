# Live source verification

- generated: `2026-10-25T14:31:56Z`
- dataset: `2026-10-25T14:27:11Z`
- rows: **234**
- result: **FAIL**

| Check | Result | Detail |
|---|---|---|
| every row carries a Hotspawn match card URL | PASS | 234/234 |
| priced rows sum to 100% (0.2pp) | PASS | [] |
| pick is the higher-probability side (ties may take either side) | PASS | [] |
| every row names a pick or documented no-pick | PASS | 234/234 |
| published inventory == live Hotspawn feed (1:1 ids, freshness) | PASS | live=234 dataset=234 new on feed since publish=0 gone from feed=0 |
| control: Pinnacle guest key accepted this run (separates a closed board from an auth failure) | PASS | status=403 cause=auth_required -> matchup boards answering 401/403 are classified 'auth_required' |
| control: Pinnacle guest key could not be proven | FAIL | status=403 cause=auth_required; closed-board classification disabled, 401/403 stays a failure |
| no broken hotspawn card URL | PASS | 234/234 resolved this run; causes={'resolved': 234} |
| no broken market quote URL | PASS | 10/10 resolved this run; causes={'resolved': 10} |
| no broken venue receipt URL | PASS | 33/41 resolved this run; causes={'resolved': 33, 'rate_limited': 8} |
| no broken leaguepedia page URL | PASS | 29/29 resolved this run; causes={'resolved': 29} |
| no broken pickem URL | PASS | 1/1 resolved this run; causes={'resolved': 1} |
| every row has at least one resolving piece of evidence (no broken links) | PASS | 234/234 rows; 0 unverified this run (throttle/expiry) |
| every published dashboard page resolves | PASS | 13/13 HTTP 2xx |
| table.html renders at least one row per match | PASS | rendered=234 rows=234 |
| every displayed win-probability pair adds to 100.0% | PASS | 0 row(s) off: [] |

## Resolution by evidence role

| Role | URLs | Resolved | Causes |
|---|---|---|---|
| hotspawn_card | 234 | 234 | `{'resolved': 234}` |
| market_quote | 10 | 10 | `{'resolved': 10}` |
| venue_receipt | 41 | 33 | `{'resolved': 33, 'rate_limited': 8}` |
| leaguepedia_page | 29 | 29 | `{'resolved': 29}` |
| pickem | 1 | 1 | `{'resolved': 1}` |
