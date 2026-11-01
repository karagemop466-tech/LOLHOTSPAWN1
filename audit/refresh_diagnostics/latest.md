# refresh-docs verification output

run 41275053000 attempt 1 · commit `f27d88d911fe0af4d858c79a80be8246a0265526` · 2026-11-01T04:58:04Z

## freshly generated snapshot
```
generated_at 2026-11-01T04:58:03.650Z | raw feed 2026-11-01T04:57:54.699Z
counts {"total_rows":496,"scheduled_total":190,"active_open_locked":91,"stale_scheduled":99,"ended_recent":246,"forfeited_recent":15,"cancelled_recent":45,"active_market":0,"active_model":91,"active_unresolved":0,"scheduled_market":0,"scheduled_model":179,"scheduled_walkover_settlement":4,"scheduled_unresolved":7,"by_source_scheduled":{"model":127,"walkover_settlement":4,"model_provisional":52,"unresolved":7},"by_source_active":{"model":72,"model_provisional":19},"flags":16}
calibration {"n":22436,"brier":0.2251,"series":32611}
rows 496 | scheduled 190
market rows: none
scheduled rows with best_of != null: 0
flags 16 | dq-walkover-1071170 unverified-zero-history-1074627 dq-walkover-1071200 dq-walkover-1071206 dq-walkover-1071186 unverified-zero-history-1082002 unverified-zero-history-1083593 unverified-zero-history-1121690 unverified-zero-history-1121692 unverified-zero-history-1121693 unverified-zero-history-1121694 entity-collision-1082746 entity-collision-1079053 entity-collision-1079057 org-pooling-rich-gang-prm3 series-format-not-published
```

## git diff --stat of this run's output
```
 data/node/raw/bovada_lol.json              |    2 +-
 data/node/raw/collect_log.json             |   48 +-
 data/node/raw/hotspawn_lobby_check.json    |    2 +-
 data/node/raw/hotspawn_lol_fixtures.json   |    2 +-
 data/node/raw/kalshi_lol.json              |    2 +-
 data/node/raw/kambi_lol.json               |    2 +-
 data/node/raw/pinnacle_lol.json            |    2 +-
 data/node/raw/pinnacle_matchups_cache.json |    2 +-
 data/node/raw/polymarket_lol.json          |    2 +-
 data/node/raw/smarkets_lol.json            |    2 +-
 docs/data/canonical_snapshot.json          |    2 +-
 docs/data/flags.json                       |   82 +-
 docs/data/picks.csv                        |   50 +-
 docs/data/picks.json                       | 5115 +---------------------------
 docs/featured.html                         |  148 +-
 docs/flagged.html                          |   81 +-
 docs/index.html                            |  277 +-
 docs/methodology.html                      |   30 +-
 docs/originated.html                       |  148 +-
 docs/picks.html                            |  653 +---
 docs/results.html                          |  417 +--
 docs/table.html                            |  220 +-
 docs/tournaments.html                      |  277 +-
 docs/unresolved.html                       |  201 +-
 32 files changed, 817 insertions(+), 12840 deletions(-)
```

## python3 audit/verify_docs.py
```
PASS    1 docs/data/picks.json mirrors data/node/picks.json :: 1178035 bytes
PASS    2 every active match with a pick rendered on picks.html :: 91 picked rows, missing: []
PASS    3 rendered probabilities match JSON :: bad: []
PASS    4 every active match without a pick is on unresolved.html and index.html :: 0 unresolved, missing: []
PASS    5 every rendered card links its Hotspawn match card :: missing: []
PASS    6 market rows carry all matched venue source links :: 0 market rows, missing: []
PASS    7 results.html renders only official scores (no fabricated fills) :: 261 ended/forfeited checked, bad: []
PASS    8 no ledger entry with an official result renders as pending :: bad: []
PASS    9 navigation on every docs page :: []
PASS  9.1 exec summary links every picks view & subpage :: []
PASS   10 no broken internal links or fragments in docs/ :: []
PASS   11 probabilities sum to 100% and pick = argmax :: bad: []
PASS   12 all scheduled matches rendered 1:1 on docs/table.html with source links :: 190 scheduled rows, missing: []
PASS   13 all 10 docs/*.html category pages exist with mobile viewport :: missing=[] no_vp=[]
PASS   14 no '(Kills)' derivative market used as a match line :: []
PASS   15 cross-region homonym quarantines (#1083097, #1079031) & Solid Gaming DQ walkovers verified :: []
PASS   16 every Flagged for Review item renders with Hotspawn + official source links :: 16 flags, bad=[]

rows: 496 total | scheduled 190 | active 91 (91 with pick, 0 unresolved) | ended/forfeited 261 | flags 16 | ledger 294 entries

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
PASS    3 reconciliation + overview numbers reproduce both committed snapshots :: reconcile section: True; missing: []; oos series rendered: 22,436
PASS    4 every scheduled row deep-links to a canonical anchor that exists :: 190 rows; missing link: []; dead anchor: []
PASS    5 fixtures absent from the canonical snapshot are explained, not silently dropped :: unexplained: []
PASS    6 canonical probabilities rendered in docs/ equal data/matches.json :: mismatched: []
PASS    7 divergences (>= 5 pp or opposite pick) are marked and listed :: 31 divergent fixtures; unmarked rows: []; missing from overview ledger: []
PASS    8 no series format is rendered that Hotspawn does not publish :: 190 rows have best_of=null in the feed; bad renders: []
PASS    9 internal links and fragments resolve (including ../ into the root site) :: broken: []
PASS   10 methodology documents the canonical relationship and the unpublished series format :: missing: []
WARN      canonical cards missing from the secondary snapshot :: 35

scheduled rows: 190 | shared with canonical: 177 | both priced: 170 | divergent: 31 | mean gap 2.482 pp | max gap 9.76 pp

ALL DOCS-PARITY CHECKS PASS
exit=0
```
