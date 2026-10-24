# Independent verification of the published dashboard

Run: 2026-10-24T16:17:34Z · verifier: `audit/session_5ff8e6bf/verify_published.py`

**Result: 25/28 checks pass.**

| # | Check | Result | Detail |
|---|---|---|---|
| 1 | inventory mirrors the collected Hotspawn feed 1:1 | PASS | `feed=241 dataset=241 missing=[] extra=[]` |
| 2 | match ids are unique | PASS | `241 unique of 241` |
| 3 | both probabilities present and sum to 100% (+/-0.2pp) | PASS | `problems: []` |
| 4 | published pick is the higher-probability side, named and quoted correctly | PASS | `side problems: [] name problems: []` |
| 5 | settlement picks name a listed participant and claim no probability | PASS | `4 settlements; problems: []` |
| 6 | every listed match carries a pick | PASS | `241/241 rows; missing: []` |
| 7 | method values are in the documented set | PASS | `methods: {'model': 151, 'unresolved': 4, 'provisional': 77, 'market': 9}` |
| 8 | published method counts reconcile with the rows | PASS | `declared={'model': 151, 'unresolved': 4, 'provisional': 77, 'market': 9} recomputed={'model': 151, 'unresolved': 4, 'provisional': 77, 'market': 9} rows=241` |
| 9 | market rows re-derive from their own venue quotes (weights x prices) | PASS | `problems: []` |
| 10 | every venue quote carries a URL and an observation timestamp | PASS | `problems: []` |
| 11 | published venue weights sum to 1.0 on every market row (informational) | WARN | `rows whose weights do not sum to 1.0: ['1067878(weights=0.880)', '1079080(weights=0.240)']` |
| 12 | originated rows re-derive from their own published Elo ratings | PASS | `228 rows re-derived; deviations >2pp: []` |
| 13 | published probabilities are not Hotspawn crowd percentages | PASS | `rows identical to the crowd share: []` |
| 14 | no row derives its probability from a Hotspawn crowd share | PASS | `rows: []` |
| 15 | every row links to its own Hotspawn match card (id in the URL) | PASS | `241/241; problems: []` |
| 16 | every rendered source URL is https on a named host | PASS | `7 hosts: ['eu-offering-api.kambicdn.com', 'guest.api.arcadia.pinnacle.com', 'kalshi.com', 'lol.fandom.com', 'polymarket.com', 'www.bovada.lv', 'www.hotspawn.com']; problems: []` |
| 17 | picks.csv mirrors the dataset row for row | PASS | `csv=241 json=241 problems: []` |
| 18 | all published pages exist | PASS | `13/13; missing: []` |
| 19 | every page declares a mobile viewport | PASS | `missing: []` |
| 20 | every page carries the desktop nav and the mobile bottom bar | PASS | `nav missing: []; mobnav missing: []` |
| 21 | no page renders a literal None/nan value | PASS | `problems: []` |
| 22 | no broken internal links | PASS | `2989 links parsed; problems: []` |
| 23 | the table page renders exactly one row per match | PASS | `table rows=241 matches=241` |
| 24 | the card page renders exactly one card per match | PASS | `cards=241 matches=241` |
| 25 | the executive summary links every picks view, the unresolved section and the flag page | PASS | `missing: []` |
| 26 | the published snapshot is younger than the 8 h refresh ceiling | **FAIL** | `generated_utc=2026-10-23T17:13:12Z age=23.1h` |
| 27 | the Hotspawn inventory was fetched recently enough to be current | **FAIL** | `inventory_fetched_utc=2026-10-23T17:11:12Z age=23.1h` |
| 28 | the out-of-sample backtest is internally consistent | PASS | `n=3854 hits=2506 acc=0.6502 buckets n=3854 hits=2506 brier=0.2183` |

Inputs re-derived from:

- `data/matches.json`: {'rows': 241, 'generated_utc': '2026-10-23T17:13:12Z', 'inventory_fetched_utc': '2026-10-23T17:11:12Z'}
- `data/raw/hotspawn_lol.json`: {'fixtures': 241, 'fetched_utc': '2026-10-23T17:11:12Z'}
- `data/picks.csv`: {'rows': 241}
- `pages`: {'index.html': {'rows': 0, 'cards': 6, 'links': 103}, 'table.html': {'rows': 241, 'cards': 0, 'links': 518}, 'picks.html': {'rows': 0, 'cards': 241, 'links': 1039}, 'featured.html': {'rows': 0, 'cards': 9, 'links': 152}, 'originated.html': {'rows': 0, 'cards': 0, 'links': 254}, 'unresolved.html': {'rows': 0, 'cards': 77, 'links': 361}, 'competitions.html': {'rows': 0, 'cards': 0, 'links': 53}, 'teams.html': {'rows': 0, 'cards': 0, 'links': 207}, 'flagged.html': {'rows': 0, 'cards': 0, 'links': 60}, 'coverage.html': {'rows': 0, 'cards': 0, 'links': 111}, 'verification.html': {'rows': 0, 'cards': 0, 'links': 45}, 'sources.html': {'rows': 0, 'cards': 0, 'links': 53}, 'methodology.html': {'rows': 0, 'cards': 0, 'links': 33}}
