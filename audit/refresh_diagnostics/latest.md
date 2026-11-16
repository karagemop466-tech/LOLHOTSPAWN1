# refresh-docs verification output

run 43893286062 attempt 1 · commit `05c8f1048e67d27b6257bd064c557ac05fa52534` · 2026-11-16T15:09:30Z

## freshly generated snapshot
```
generated_at 2026-11-16T15:09:30.432Z | raw feed 2026-11-16T15:09:22.944Z
counts {"total_rows":290,"scheduled_total":125,"active_open_locked":29,"stale_scheduled":96,"ended_recent":150,"forfeited_recent":3,"cancelled_recent":12,"active_market":0,"active_model":28,"active_unresolved":1,"scheduled_market":0,"scheduled_model":117,"scheduled_walkover_settlement":4,"scheduled_unresolved":4,"by_source_scheduled":{"model":77,"walkover_settlement":4,"model_provisional":40,"unresolved":4},"by_source_active":{"unresolved":1,"model":23,"model_provisional":5},"flags":10}
calibration {"n":22635,"brier":0.2251,"series":32888}
rows 290 | scheduled 125
market rows: none
scheduled rows with best_of != null: 0
flags 10 | dq-walkover-1071170 unverified-zero-history-1074627 dq-walkover-1071200 dq-walkover-1071206 dq-walkover-1071186 unverified-zero-history-1082002 unverified-zero-history-1083593 unverified-zero-history-1132746 org-pooling-rich-gang-prm3 series-format-not-published
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
 docs/data/flags.json                       |    32 +-
 docs/data/picks.csv                        |    39 +-
 docs/data/picks.json                       | 22356 +++++++++------------------
 docs/featured.html                         |    56 +-
 docs/flagged.html                          |    34 +-
 docs/index.html                            |   118 +-
 docs/methodology.html                      |    46 +-
 docs/originated.html                       |  1010 +-
 docs/picks.html                            |   799 +-
 docs/results.html                          |  1287 +-
 docs/table.html                            |   389 +-
 docs/tournaments.html                      |   448 +-
 docs/unresolved.html                       |    58 +-
 32 files changed, 20244 insertions(+), 38930 deletions(-)
```

## python3 audit/verify_docs.py
```
PASS    1 docs/data/picks.json mirrors data/node/picks.json :: 689312 bytes
PASS    2 every active match with a pick rendered on picks.html :: 28 picked rows, missing: []
PASS    3 rendered probabilities match JSON :: bad: []
PASS    4 every active match without a pick is on unresolved.html and index.html :: 1 unresolved, missing: []
PASS    5 every rendered card links its Hotspawn match card :: missing: []
PASS    6 market rows carry all matched venue source links :: 0 market rows, missing: []
PASS    7 results.html renders only official scores (no fabricated fills) :: 153 ended/forfeited checked, bad: []
PASS    8 no ledger entry with an official result renders as pending :: bad: []
PASS    9 navigation on every docs page :: []
PASS  9.1 exec summary links every picks view & subpage :: []
PASS   10 no broken internal links or fragments in docs/ :: []
PASS   11 probabilities sum to 100% and pick = argmax :: bad: []
PASS   12 all scheduled matches rendered 1:1 on docs/table.html with source links :: 125 scheduled rows, missing: []
PASS   13 all 10 docs/*.html category pages exist with mobile viewport :: missing=[] no_vp=[]
PASS   14 no '(Kills)' derivative market used as a match line :: []
PASS   15 cross-region homonym quarantines (#1083097, #1079031) & Solid Gaming DQ walkovers verified :: []
PASS   16 every Flagged for Review item renders with Hotspawn + official source links :: 10 flags, bad=[]

rows: 290 total | scheduled 125 | active 29 (28 with pick, 1 unresolved) | ended/forfeited 153 | flags 10 | ledger 386 entries

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
PASS    3 reconciliation + overview numbers reproduce both committed snapshots :: reconcile section: True; missing: []; oos series rendered: 22,635
PASS    4 every scheduled row deep-links to a canonical anchor that exists :: 125 rows; missing link: []; dead anchor: []
PASS    5 fixtures absent from the canonical snapshot are explained, not silently dropped :: unexplained: []
PASS    6 canonical probabilities rendered in docs/ equal data/matches.json :: mismatched: []
PASS    7 divergences (>= 5 pp or opposite pick) are marked and listed :: 17 divergent fixtures; unmarked rows: []; missing from overview ledger: []
PASS    8 no series format is rendered that Hotspawn does not publish :: 125 rows have best_of=null in the feed; bad renders: []
PASS    9 internal links and fragments resolve (including ../ into the root site) :: broken: []
PASS   10 methodology documents the canonical relationship and the unpublished series format :: missing: []
WARN      canonical cards missing from the secondary snapshot :: 114

scheduled rows: 125 | shared with canonical: 98 | both priced: 91 | divergent: 17 | mean gap 2.501 pp | max gap 9.76 pp

ALL DOCS-PARITY CHECKS PASS
exit=0
```
