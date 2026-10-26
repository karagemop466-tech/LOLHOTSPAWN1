# Live source verification

- generated: `2026-10-26T09:20:12Z`
- dataset: `2026-10-26T04:53:15Z`
- rows: **222**
- result: **FAIL**

| Check | Result | Detail |
|---|---|---|
| every row carries a Hotspawn match card URL | PASS | 222/222 |
| priced rows sum to 100% (0.2pp) | PASS | [] |
| pick is the higher-probability side (ties may take either side) | PASS | [] |
| every row names a pick (priced or settlement/void) | PASS | 222/222 |
| published inventory == live Hotspawn feed (1:1 ids, freshness) | FAIL | live=222 dataset=222 new on feed since publish=1 gone from feed=1 - dataset is stale: the scheduled refresh has not published |
| control: Pinnacle guest endpoint probed (supplements, never replaces, the sibling-success proof) | PASS | status=403 cause=auth_required -> key proven by control: False |
| no broken hotspawn card URL | PASS | 222/222 resolved this run; causes={'resolved': 222} |
| no broken market quote URL | PASS | 6/6 resolved this run; causes={'resolved': 6} |
| no broken venue receipt URL | FAIL | 17/26 resolved this run; causes={'resolved': 17, 'rate_limited': 5, 'auth_required': 4} |
| no broken leaguepedia page URL | PASS | 29/29 resolved this run; causes={'resolved': 29} |
| no broken pickem URL | PASS | 1/1 resolved this run; causes={'resolved': 1} |
| every row has at least one resolving piece of evidence (no broken links) | PASS | 222/222 rows; 0 unverified this run (throttle/expiry) |
| every published dashboard page resolves | PASS | 13/13 HTTP 2xx |
| table.html renders at least one row per match | PASS | rendered=222 rows=222 |
| every displayed win-probability pair adds to 100.0% | PASS | 0 row(s) off: [] |

## Resolution by evidence role

| Role | URLs | Resolved | Causes |
|---|---|---|---|
| hotspawn_card | 222 | 222 | `{'resolved': 222}` |
| market_quote | 6 | 6 | `{'resolved': 6}` |
| venue_receipt | 26 | 17 | `{'resolved': 17, 'rate_limited': 5, 'auth_required': 4}` |
| leaguepedia_page | 29 | 29 | `{'resolved': 29}` |
| pickem | 1 | 1 | `{'resolved': 1}` |
