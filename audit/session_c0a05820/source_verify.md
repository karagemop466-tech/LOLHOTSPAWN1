# Live source verification

- generated: `2026-10-25T08:42:32Z`
- dataset: `2026-10-24T20:54:30Z`
- rows: **241**
- result: **FAIL**

| Check | Result | Detail |
|---|---|---|
| every row carries a Hotspawn match card URL | PASS | 241/241 |
| priced rows sum to 100% (0.2pp) | PASS | [] |
| pick is the higher-probability side (ties may take either side) | PASS | [] |
| every row names a pick (priced or settlement/void) | PASS | 241/241 |
| published inventory == live Hotspawn feed (1:1 ids, freshness) | FAIL | live=236 dataset=241 new on feed since publish=12 gone from feed=17 - dataset is stale: the scheduled refresh has not published |
| no broken hotspawn card URL | PASS | 241/241 resolved this run; causes={'resolved': 241} |
| no broken market quote URL | FAIL | 2/7 resolved this run; causes={'rate_limited': 1, 'auth_required': 4, 'resolved': 2} |
| no broken venue receipt URL | FAIL | 9/22 resolved this run; causes={'rate_limited': 5, 'auth_required': 4, 'resolved': 9, 'expired_event': 4} |
| no broken leaguepedia page URL | PASS | 29/29 resolved this run; causes={'resolved': 29} |
| no broken pickem URL | PASS | 1/1 resolved this run; causes={'resolved': 1} |
| every row has at least one resolving piece of evidence (no broken links) | PASS | 241/241 rows; 0 unverified this run (throttle/expiry) |
| every published dashboard page resolves | PASS | 13/13 HTTP 2xx |
| table.html renders at least one row per match | PASS | rendered=241 rows=241 |
| every displayed win-probability pair adds to 100.0% | PASS | 0 row(s) off: [] |

## Resolution by evidence role

| Role | URLs | Resolved | Causes |
|---|---|---|---|
| hotspawn_card | 241 | 241 | `{'resolved': 241}` |
| market_quote | 7 | 2 | `{'rate_limited': 1, 'auth_required': 4, 'resolved': 2}` |
| venue_receipt | 22 | 9 | `{'rate_limited': 5, 'auth_required': 4, 'resolved': 9, 'expired_event': 4}` |
| leaguepedia_page | 29 | 29 | `{'resolved': 29}` |
| pickem | 1 | 1 | `{'resolved': 1}` |
