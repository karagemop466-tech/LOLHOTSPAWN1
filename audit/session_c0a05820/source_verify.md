# Live source verification

- generated: `2026-10-29T10:23:37Z`
- dataset: `2026-10-26T22:44:33Z`
- rows: **212**
- result: **FAIL**

| Check | Result | Detail |
|---|---|---|
| every row carries a Hotspawn match card URL | PASS | 212/212 |
| priced rows sum to 100% (0.2pp) | PASS | [] |
| pick is the higher-probability side (ties may take either side) | PASS | [] |
| every row names a pick (priced or settlement/void) | PASS | 212/212 |
| published inventory == live Hotspawn feed (1:1 ids, freshness) | FAIL | live=210 dataset=212 new on feed since publish=15 gone from feed=17 - dataset is stale: the scheduled refresh has not published |
| no broken hotspawn card URL | PASS | 212/212 resolved this run; causes={'resolved': 212} |
| no broken market quote URL | PASS | 2/2 resolved this run; causes={'resolved': 2} |
| no broken venue receipt URL | PASS | 1/2 resolved this run; causes={'resolved': 1, 'rate_limited': 1} |
| no broken leaguepedia page URL | PASS | 30/30 resolved this run; causes={'resolved': 30} |
| no broken pickem URL | PASS | 1/1 resolved this run; causes={'resolved': 1} |
| every row has at least one resolving piece of evidence (no broken links) | PASS | 212/212 rows; 0 unverified this run (throttle/expiry) |
| every published dashboard page resolves | PASS | 13/13 HTTP 2xx |
| table.html renders at least one row per match | PASS | rendered=212 rows=212 |
| every displayed win-probability pair adds to 100.0% | PASS | 0 row(s) off: [] |

## Resolution by evidence role

| Role | URLs | Resolved | Causes |
|---|---|---|---|
| hotspawn_card | 212 | 212 | `{'resolved': 212}` |
| market_quote | 2 | 2 | `{'resolved': 2}` |
| venue_receipt | 2 | 1 | `{'resolved': 1, 'rate_limited': 1}` |
| leaguepedia_page | 30 | 30 | `{'resolved': 30}` |
| pickem | 1 | 1 | `{'resolved': 1}` |
