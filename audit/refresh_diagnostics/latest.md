# refresh-docs verification output

run 40590817981 attempt 1 · commit `70c3dca0198c53615f1627ef35c97da4f30d223b` · 2026-10-27T21:56:26Z

## freshly generated snapshot
```
generated_at 2026-10-27T21:56:25.352Z | raw feed 2026-10-27T21:56:18.084Z
counts {"total_rows":552,"scheduled_total":211,"active_open_locked":131,"stale_scheduled":80,"ended_recent":269,"forfeited_recent":23,"cancelled_recent":49,"active_market":6,"active_model":125,"active_unresolved":0,"scheduled_market":6,"scheduled_model":198,"scheduled_walkover_settlement":4,"scheduled_unresolved":3,"by_source_scheduled":{"model":145,"walkover_settlement":4,"model_provisional":53,"unresolved":3,"market_consensus":6},"by_source_active":{"model":104,"model_provisional":21,"market_consensus":6},"flags":14}
calibration {"n":22401,"brier":0.2251,"series":32565}
rows 552 | scheduled 211
market rows: 1094910:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Smarkets (UKGC)] 1094909:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Smarkets (UKGC)] 1094911:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Smarkets (UKGC)] 1094908:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Smarkets (UKGC)] 1094912:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Smarkets (UKGC)] 1094913:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Smarkets (UKGC)]
scheduled rows with best_of != null: 0
flags 14 | dq-walkover-1071170 unverified-zero-history-1074627 dq-walkover-1071200 dq-walkover-1071206 dq-walkover-1071186 unverified-zero-history-1082002 unverified-zero-history-1083593 entity-collision-1079031 entity-collision-1079038 entity-collision-1082746 entity-collision-1079053 entity-collision-1079057 org-pooling-rich-gang-prm3 series-format-not-published
```

## git diff --stat of this run's output
```
 data/node/raw/bovada_lol.json              |   2 +-
 data/node/raw/collect_log.json             |  36 +-
 data/node/raw/hotspawn_lobby_check.json    |   2 +-
 data/node/raw/hotspawn_lol_fixtures.json   |   2 +-
 data/node/raw/kalshi_lol.json              |   2 +-
 data/node/raw/kambi_lol.json               |   2 +-
 data/node/raw/pinnacle_lol.json            |   2 +-
 data/node/raw/pinnacle_matchups_cache.json |   2 +-
 data/node/raw/polymarket_lol.json          |   2 +-
 data/node/raw/smarkets_lol.json            |   2 +-
 docs/data/canonical_snapshot.json          |   2 +-
 docs/data/flags.json                       |  16 +-
 docs/data/picks.csv                        |  16 +-
 docs/data/picks.json                       | 662 ++++++++++++-----------------
 docs/featured.html                         | 106 ++---
 docs/flagged.html                          |  19 +-
 docs/index.html                            | 109 ++---
 docs/methodology.html                      |   8 +-
 docs/originated.html                       |  55 ++-
 docs/picks.html                            |  58 +--
 docs/results.html                          |   6 +-
 docs/table.html                            |  52 +--
 docs/tournaments.html                      |  28 +-
 docs/unresolved.html                       |   6 +-
 32 files changed, 907 insertions(+), 1357 deletions(-)
```

## python3 audit/verify_docs.py
```
PASS    1 docs/data/picks.json mirrors data/node/picks.json :: 1352773 bytes
PASS    2 every active match with a pick rendered on picks.html :: 131 picked rows, missing: []
PASS    3 rendered probabilities match JSON :: bad: []
PASS    4 every active match without a pick is on unresolved.html and index.html :: 0 unresolved, missing: []
PASS    5 every rendered card links its Hotspawn match card :: missing: []
PASS    6 market rows carry all matched venue source links :: 6 market rows, missing: []
PASS    7 results.html renders only official scores (no fabricated fills) :: 292 ended/forfeited checked, bad: []
PASS    8 no ledger entry with an official result renders as pending :: bad: []
PASS    9 navigation on every docs page :: []
PASS  9.1 exec summary links every picks view & subpage :: []
PASS   10 no broken internal links or fragments in docs/ :: []
PASS   11 probabilities sum to 100% and pick = argmax :: bad: []
PASS   12 all scheduled matches rendered 1:1 on docs/table.html with source links :: 211 scheduled rows, missing: []
PASS   13 all 10 docs/*.html category pages exist with mobile viewport :: missing=[] no_vp=[]
PASS   14 no '(Kills)' derivative market used as a match line :: []
PASS   15 cross-region homonym quarantines (#1083097, #1079031) & Solid Gaming DQ walkovers verified :: []
PASS   16 every Flagged for Review item renders with Hotspawn + official source links :: 14 flags, bad=[]

rows: 552 total | scheduled 211 | active 131 (131 with pick, 0 unresolved) | ended/forfeited 292 | flags 14 | ledger 283 entries

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

AssertionError [ERR_ASSERTION]: LGC Rising #1079080 should match Kalshi CFTC + Polymarket
    at file:///home/runner/work/LOLHOTSPAWN1/LOLHOTSPAWN1/audit/session_6669f798/test_node_pipeline.mjs:95:10 {
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
PASS    3 reconciliation + overview numbers reproduce both committed snapshots :: reconcile section: True; missing: []; oos series rendered: 22,401
PASS    4 every scheduled row deep-links to a canonical anchor that exists :: 211 rows; missing link: []; dead anchor: []
PASS    5 fixtures absent from the canonical snapshot are explained, not silently dropped :: unexplained: []
PASS    6 canonical probabilities rendered in docs/ equal data/matches.json :: mismatched: []
PASS    7 divergences (>= 5 pp or opposite pick) are marked and listed :: 30 divergent fixtures; unmarked rows: []; missing from overview ledger: []
PASS    8 no series format is rendered that Hotspawn does not publish :: 211 rows have best_of=null in the feed; bad renders: []
PASS    9 internal links and fragments resolve (including ../ into the root site) :: broken: []
PASS   10 methodology documents the canonical relationship and the unpublished series format :: missing: []
WARN      canonical cards missing from the secondary snapshot :: 10

scheduled rows: 211 | shared with canonical: 202 | both priced: 195 | divergent: 30 | mean gap 2.269 pp | max gap 9.76 pp

ALL DOCS-PARITY CHECKS PASS
exit=0
```
