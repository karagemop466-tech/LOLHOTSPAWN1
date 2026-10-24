# refresh-docs verification output

run 40122190234 attempt 1 · commit `d562de1284c983731901320a9038d72f0440d7f1` · 2026-10-24T18:46:07Z

## freshly generated snapshot
```
generated_at 2026-10-24T18:46:07.330Z | raw feed 2026-10-24T18:45:59.815Z
counts {"total_rows":578,"scheduled_total":241,"active_open_locked":175,"stale_scheduled":66,"ended_recent":259,"forfeited_recent":32,"cancelled_recent":46,"active_market":9,"active_model":166,"active_unresolved":0,"scheduled_market":9,"scheduled_model":225,"scheduled_walkover_settlement":4,"scheduled_unresolved":3,"by_source_scheduled":{"model":149,"walkover_settlement":4,"model_provisional":76,"unresolved":3,"market_bovada":2,"market_consensus":7},"by_source_active":{"model":115,"model_provisional":51,"market_bovada":2,"market_consensus":7},"flags":14}
calibration {"n":22344,"brier":0.2251,"series":32509}
rows 578 | scheduled 241
market rows: 1067688:1[Bovada] 1067881:1[Bovada] 1067686:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Bovada] 1067684:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Bovada] 1067687:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Bovada] 1067683:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Bovada] 1067880:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Bovada] 1067689:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Bovada] 1079080:2[Polymarket+Kalshi CFTC]
scheduled rows with best_of != null: 0
flags 14 | dq-walkover-1071170 unverified-zero-history-1074627 dq-walkover-1071200 dq-walkover-1071206 dq-walkover-1071186 unverified-zero-history-1082002 unverified-zero-history-1083593 entity-collision-1079031 entity-collision-1079038 entity-collision-1082746 entity-collision-1079053 entity-collision-1079057 org-pooling-rich-gang-prm3 series-format-not-published
```

## git diff --stat of this run's output
```
 data/node/model/ratings.json               |    2 +-
 data/node/picks.csv                        |   20 +-
 data/node/picks.json                       | 2386 +++++++++++++++++-----------
 data/node/raw/collect_log.json             |   38 +-
 data/node/raw/hotspawn_lobby_check.json    |    2 +-
 data/node/raw/hotspawn_lol_fixtures.json   |    2 +-
 data/node/raw/kalshi_lol.json              |    2 +-
 data/node/raw/kambi_lol.json               |    2 +-
 data/node/raw/pinnacle_lol.json            |    2 +-
 data/node/raw/pinnacle_matchups_cache.json |    2 +-
 data/node/raw/polymarket_lol.json          |    2 +-
 docs/data/flags.json                       |   62 +-
 docs/data/picks.csv                        |   20 +-
 docs/data/picks.json                       | 2386 +++++++++++++++++-----------
 docs/featured.html                         |  114 +-
 docs/flagged.html                          |   60 +-
 docs/index.html                            |  112 +-
 docs/methodology.html                      |    8 +-
 docs/originated.html                       |  115 +-
 docs/picks.html                            |  175 +-
 docs/results.html                          |   94 +-
 docs/table.html                            |  130 +-
 docs/tournaments.html                      |   72 +-
 docs/unresolved.html                       |   94 +-
 29 files changed, 3647 insertions(+), 2728 deletions(-)
```

## python3 audit/verify_docs.py
```
PASS    1 docs/data/picks.json mirrors data/node/picks.json :: 1400948 bytes
PASS    2 every active match with a pick rendered on picks.html :: 175 picked rows, missing: []
PASS    3 rendered probabilities match JSON :: bad: []
PASS    4 every active match without a pick is on unresolved.html and index.html :: 0 unresolved, missing: []
PASS    5 every rendered card links its Hotspawn match card :: missing: []
PASS    6 market rows carry all matched venue source links :: 9 market rows, missing: []
PASS    7 results.html renders only official scores (no fabricated fills) :: 291 ended/forfeited checked, bad: []
PASS    8 no ledger entry with an official result renders as pending :: bad: []
PASS    9 navigation on every docs page :: []
PASS  9.1 exec summary links every picks view & subpage :: []
PASS   10 no broken internal links or fragments in docs/ :: []
PASS   11 probabilities sum to 100% and pick = argmax :: bad: []
PASS   12 all scheduled matches rendered 1:1 on docs/table.html with source links :: 241 scheduled rows, missing: []
PASS   13 all 10 docs/*.html category pages exist with mobile viewport :: missing=[] no_vp=[]
PASS   14 no '(Kills)' derivative market used as a match line :: []
PASS   15 cross-region homonym quarantines (#1083097, #1079031) & Solid Gaming DQ walkovers verified :: []
PASS   16 every Flagged for Review item renders with Hotspawn + official source links :: 14 flags, bad=[]

rows: 578 total | scheduled 241 | active 175 (175 with pick, 0 unresolved) | ended/forfeited 291 | flags 14 | ledger 259 entries

ALL DOCS CHECKS PASS
exit=0
```

## python3 audit/check_site.py
```
pages=24 failures=0 warnings=0
exit=0
```

## node audit/session_6669f798/test_node_pipeline.mjs
```
node:internal/modules/run_main:123
    triggerUncaughtException(
    ^

AssertionError [ERR_ASSERTION]: #1067688 market row must join >= 2 independent venues, got 1
    at file:///home/runner/work/LOLHOTSPAWN1/LOLHOTSPAWN1/audit/session_6669f798/test_node_pipeline.mjs:46:10 {
  generatedMessage: false,
  code: 'ERR_ASSERTION',
  actual: false,
  expected: true,
  operator: '=='
}

Node.js v20.20.2
exit=1
```

## python3 audit/verify_docs_parity.py
```
PASS    1 no docs page reuses a canonical title and every docs title says 'secondary' :: reused: []; unmarked: []
PASS    2 secondary banner is first in <body> and every page links the canonical hub :: banner not first: []; no canonical link: []
PASS    3 reconciliation + overview numbers reproduce both committed snapshots :: reconcile section: True; missing: []; oos series rendered: 22,344
PASS    4 every scheduled row deep-links to a canonical anchor that exists :: 241 rows; missing link: []; dead anchor: []
PASS    5 fixtures absent from the canonical snapshot are explained, not silently dropped :: unexplained: []
PASS    6 canonical probabilities rendered in docs/ equal data/matches.json :: mismatched: []
PASS    7 divergences (>= 5 pp or opposite pick) are marked and listed :: 34 divergent fixtures; unmarked rows: []; missing from overview ledger: []
PASS    8 no series format is rendered that Hotspawn does not publish :: 241 rows have best_of=null in the feed; bad renders: []
PASS    9 internal links and fragments resolve (including ../ into the root site) :: broken: []
PASS   10 methodology documents the canonical relationship and the unpublished series format :: missing: []
WARN      canonical cards missing from the secondary snapshot :: 4

scheduled rows: 241 | shared with canonical: 237 | both priced: 231 | divergent: 34 | mean gap 2.37 pp | max gap 30.04 pp

ALL DOCS-PARITY CHECKS PASS
exit=0
```
