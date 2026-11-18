# refresh-docs verification output

run 44210039450 attempt 1 · commit `497783c77d5e7e6d8d37a5a3f0dbb39f94fe74e2` · 2026-11-18T00:43:02Z

## freshly generated snapshot
```
generated_at 2026-11-18T00:43:01.962Z | raw feed 2026-11-18T00:42:53.913Z
counts {"total_rows":293,"scheduled_total":126,"active_open_locked":29,"stale_scheduled":97,"ended_recent":152,"forfeited_recent":3,"cancelled_recent":12,"active_market":0,"active_model":29,"active_unresolved":0,"scheduled_market":0,"scheduled_model":119,"scheduled_walkover_settlement":4,"scheduled_unresolved":3,"by_source_scheduled":{"model":78,"walkover_settlement":4,"model_provisional":41,"unresolved":3},"by_source_active":{"model":23,"model_provisional":6},"flags":9}
calibration {"n":22640,"brier":0.2251,"series":32895}
rows 293 | scheduled 126
market rows: none
scheduled rows with best_of != null: 0
flags 9 | dq-walkover-1071170 unverified-zero-history-1074627 dq-walkover-1071200 dq-walkover-1071206 dq-walkover-1071186 unverified-zero-history-1082002 unverified-zero-history-1083593 org-pooling-rich-gang-prm3 series-format-not-published
```

## git diff --stat of this run's output
```
 data/node/raw/bovada_lol.json              |     2 +-
 data/node/raw/collect_log.json             |    46 +-
 data/node/raw/hotspawn_lobby_check.json    |     2 +-
 data/node/raw/hotspawn_lol_fixtures.json   |     2 +-
 data/node/raw/kalshi_lol.json              |     2 +-
 data/node/raw/kambi_lol.json               |     2 +-
 data/node/raw/pinnacle_lol.json            |     2 +-
 data/node/raw/pinnacle_matchups_cache.json |     2 +-
 data/node/raw/polymarket_lol.json          |     2 +-
 data/node/raw/smarkets_lol.json            |     2 +-
 docs/data/canonical_snapshot.json          |     2 +-
 docs/data/flags.json                       |    42 +-
 docs/data/picks.csv                        |    56 +-
 docs/data/picks.json                       | 19007 ++++++++-------------------
 docs/featured.html                         |    56 +-
 docs/flagged.html                          |    43 +-
 docs/index.html                            |   147 +-
 docs/methodology.html                      |    46 +-
 docs/originated.html                       |  1414 +-
 docs/picks.html                            |  1212 +-
 docs/results.html                          |  1407 +-
 docs/table.html                            |   542 +-
 docs/tournaments.html                      |   504 +-
 docs/unresolved.html                       |    83 +-
 32 files changed, 15061 insertions(+), 32983 deletions(-)
```

## python3 audit/verify_docs.py
```
PASS    1 docs/data/picks.json mirrors data/node/picks.json :: 696599 bytes
PASS    2 every active match with a pick rendered on picks.html :: 29 picked rows, missing: []
PASS    3 rendered probabilities match JSON :: bad: []
PASS    4 every active match without a pick is on unresolved.html and index.html :: 0 unresolved, missing: []
PASS    5 every rendered card links its Hotspawn match card :: missing: []
PASS    6 market rows carry all matched venue source links :: 0 market rows, missing: []
PASS    7 results.html renders only official scores (no fabricated fills) :: 155 ended/forfeited checked, bad: []
PASS    8 no ledger entry with an official result renders as pending :: bad: []
PASS    9 navigation on every docs page :: []
PASS  9.1 exec summary links every picks view & subpage :: []
PASS   10 no broken internal links or fragments in docs/ :: []
PASS   11 probabilities sum to 100% and pick = argmax :: bad: []
PASS   12 all scheduled matches rendered 1:1 on docs/table.html with source links :: 126 scheduled rows, missing: []
PASS   13 all 10 docs/*.html category pages exist with mobile viewport :: missing=[] no_vp=[]
PASS   14 no '(Kills)' derivative market used as a match line :: []
PASS   15 cross-region homonym quarantines (#1083097, #1079031) & Solid Gaming DQ walkovers verified :: []
PASS   16 every Flagged for Review item renders with Hotspawn + official source links :: 9 flags, bad=[]

rows: 293 total | scheduled 126 | active 29 (29 with pick, 0 unresolved) | ended/forfeited 155 | flags 9 | ledger 392 entries

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

AssertionError [ERR_ASSERTION]: expected at least one market-backed series, got 0
    at file:///home/runner/work/LOLHOTSPAWN1/LOLHOTSPAWN1/audit/session_6669f798/test_node_pipeline.mjs:41:8 {
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
PASS    3 reconciliation + overview numbers reproduce both committed snapshots :: reconcile section: True; missing: []; oos series rendered: 22,640
PASS    4 every scheduled row deep-links to a canonical anchor that exists :: 126 rows; missing link: []; dead anchor: []
PASS    5 fixtures absent from the canonical snapshot are explained, not silently dropped :: unexplained: []
PASS    6 canonical probabilities rendered in docs/ equal data/matches.json :: mismatched: []
PASS    7 divergences (>= 5 pp or opposite pick) are marked and listed :: 17 divergent fixtures; unmarked rows: []; missing from overview ledger: []
PASS    8 no series format is rendered that Hotspawn does not publish :: 126 rows have best_of=null in the feed; bad renders: []
PASS    9 internal links and fragments resolve (including ../ into the root site) :: broken: []
PASS   10 methodology documents the canonical relationship and the unpublished series format :: missing: []
WARN      canonical cards missing from the secondary snapshot :: 116

scheduled rows: 126 | shared with canonical: 96 | both priced: 89 | divergent: 17 | mean gap 2.47 pp | max gap 9.76 pp

ALL DOCS-PARITY CHECKS PASS
exit=0
```
