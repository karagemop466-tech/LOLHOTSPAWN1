# refresh-docs verification output

run 41169396220 attempt 1 · commit `bdf7c26d608ef6a8dc85e92666c355eea0b8f756` · 2026-10-31T04:38:51Z

## freshly generated snapshot
```
generated_at 2026-10-31T04:38:51.397Z | raw feed 2026-10-31T04:38:43.703Z
counts {"total_rows":556,"scheduled_total":206,"active_open_locked":122,"stale_scheduled":84,"ended_recent":280,"forfeited_recent":22,"cancelled_recent":47,"active_market":0,"active_model":110,"active_unresolved":12,"scheduled_market":0,"scheduled_model":187,"scheduled_walkover_settlement":4,"scheduled_unresolved":15,"by_source_scheduled":{"model":134,"walkover_settlement":4,"model_provisional":53,"unresolved":15},"by_source_active":{"model":88,"unresolved":12,"model_provisional":22},"flags":25}
calibration {"n":22424,"brier":0.2251,"series":32594}
rows 556 | scheduled 206
market rows: none
scheduled rows with best_of != null: 0
flags 25 | dq-walkover-1071170 unverified-zero-history-1074627 dq-walkover-1071200 dq-walkover-1071206 dq-walkover-1071186 unverified-zero-history-1082002 unverified-zero-history-1083593 entity-collision-1079038 unverified-zero-history-1128817 unverified-zero-history-1126362 unverified-zero-history-1126363 unverified-zero-history-1128818 unverified-zero-history-1126364 unverified-zero-history-1126365 unverified-zero-history-1126366 unverified-zero-history-1126367 unverified-zero-history-1121690 unverified-zero-history-1121692 unverified-zero-history-1121693 unverified-zero-history-1121694 entity-collision-1082746 entity-collision-1079053 entity-collision-1079057 org-pooling-rich-gang-prm3 series-format-not-published
```

## git diff --stat of this run's output
```
 data/node/raw/bovada_lol.json              |    2 +-
 data/node/raw/collect_log.json             |   44 +-
 data/node/raw/hotspawn_lobby_check.json    |    2 +-
 data/node/raw/hotspawn_lol_fixtures.json   |    2 +-
 data/node/raw/kalshi_lol.json              |    2 +-
 data/node/raw/kambi_lol.json               |    2 +-
 data/node/raw/pinnacle_lol.json            |    2 +-
 data/node/raw/pinnacle_matchups_cache.json |    2 +-
 data/node/raw/polymarket_lol.json          |    2 +-
 data/node/raw/smarkets_lol.json            |    2 +-
 docs/data/canonical_snapshot.json          |    2 +-
 docs/data/flags.json                       |    6 +-
 docs/data/picks.csv                        |   34 +-
 docs/data/picks.json                       | 1272 ++++++++++------------------
 docs/featured.html                         |  102 +--
 docs/flagged.html                          |   10 +-
 docs/index.html                            |  129 +--
 docs/methodology.html                      |   28 +-
 docs/originated.html                       |  260 +++---
 docs/picks.html                            |  427 ++--------
 docs/results.html                          |   91 +-
 docs/table.html                            |  152 ++--
 docs/tournaments.html                      |   96 +--
 docs/unresolved.html                       |    6 +-
 32 files changed, 1603 insertions(+), 2970 deletions(-)
```

## python3 audit/verify_docs.py
```
PASS    1 docs/data/picks.json mirrors data/node/picks.json :: 1314661 bytes
PASS    2 every active match with a pick rendered on picks.html :: 110 picked rows, missing: []
PASS    3 rendered probabilities match JSON :: bad: []
PASS    4 every active match without a pick is on unresolved.html and index.html :: 12 unresolved, missing: []
PASS    5 every rendered card links its Hotspawn match card :: missing: []
PASS    6 market rows carry all matched venue source links :: 0 market rows, missing: []
PASS    7 results.html renders only official scores (no fabricated fills) :: 302 ended/forfeited checked, bad: []
PASS    8 no ledger entry with an official result renders as pending :: bad: []
PASS    9 navigation on every docs page :: []
PASS  9.1 exec summary links every picks view & subpage :: []
PASS   10 no broken internal links or fragments in docs/ :: []
PASS   11 probabilities sum to 100% and pick = argmax :: bad: []
PASS   12 all scheduled matches rendered 1:1 on docs/table.html with source links :: 206 scheduled rows, missing: []
PASS   13 all 10 docs/*.html category pages exist with mobile viewport :: missing=[] no_vp=[]
PASS   14 no '(Kills)' derivative market used as a match line :: []
PASS   15 cross-region homonym quarantines (#1083097, #1079031) & Solid Gaming DQ walkovers verified :: []
PASS   16 every Flagged for Review item renders with Hotspawn + official source links :: 25 flags, bad=[]

rows: 556 total | scheduled 206 | active 122 (110 with pick, 12 unresolved) | ended/forfeited 302 | flags 25 | ledger 291 entries

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
PASS    3 reconciliation + overview numbers reproduce both committed snapshots :: reconcile section: True; missing: []; oos series rendered: 22,424
PASS    4 every scheduled row deep-links to a canonical anchor that exists :: 206 rows; missing link: []; dead anchor: []
PASS    5 fixtures absent from the canonical snapshot are explained, not silently dropped :: unexplained: []
PASS    6 canonical probabilities rendered in docs/ equal data/matches.json :: mismatched: []
PASS    7 divergences (>= 5 pp or opposite pick) are marked and listed :: 33 divergent fixtures; unmarked rows: []; missing from overview ledger: []
PASS    8 no series format is rendered that Hotspawn does not publish :: 206 rows have best_of=null in the feed; bad renders: []
PASS    9 internal links and fragments resolve (including ../ into the root site) :: broken: []
PASS   10 methodology documents the canonical relationship and the unpublished series format :: missing: []
WARN      canonical cards missing from the secondary snapshot :: 30

scheduled rows: 206 | shared with canonical: 182 | both priced: 175 | divergent: 33 | mean gap 2.46 pp | max gap 9.76 pp

ALL DOCS-PARITY CHECKS PASS
exit=0
```
