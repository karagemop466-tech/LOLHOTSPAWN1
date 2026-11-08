# refresh-docs verification output

run 42527075389 attempt 1 · commit `96ed0a312e0baba5f5037e38959825a3714a66a3` · 2026-11-08T21:49:26Z

## freshly generated snapshot
```
generated_at 2026-11-08T21:49:26.065Z | raw feed 2026-11-08T21:49:17.114Z
counts {"total_rows":508,"scheduled_total":189,"active_open_locked":96,"stale_scheduled":93,"ended_recent":279,"forfeited_recent":6,"cancelled_recent":34,"active_market":4,"active_model":72,"active_unresolved":20,"scheduled_market":4,"scheduled_model":157,"scheduled_walkover_settlement":4,"scheduled_unresolved":24,"by_source_scheduled":{"model":109,"walkover_settlement":4,"model_provisional":48,"unresolved":24,"market_consensus":4},"by_source_active":{"model":57,"model_provisional":15,"market_consensus":4,"unresolved":20},"flags":33}
calibration {"n":22549,"brier":0.2251,"series":32776}
rows 508 | scheduled 189
market rows: 1130194:5[Pinnacle+Unibet (Kambi)+Polymarket+Smarkets (UKGC)+Kalshi CFTC] 1081421:2[Polymarket+Kalshi CFTC] 1082007:2[Polymarket+Kalshi CFTC] 1081423:2[Polymarket+Kalshi CFTC]
scheduled rows with best_of != null: 0
flags 33 | dq-walkover-1071170 unverified-zero-history-1074627 dq-walkover-1071200 dq-walkover-1071206 dq-walkover-1071186 unverified-zero-history-1082002 unverified-zero-history-1083593 unverified-zero-history-1131164 entity-collision-1079053 venue-divergence-1130194 unverified-zero-history-1131166 unverified-zero-history-1130130 unverified-zero-history-1130131 unverified-zero-history-1130132 unverified-zero-history-1131170 unverified-zero-history-1130133 unverified-zero-history-1130134 unverified-zero-history-1130135 unverified-zero-history-1131172 unverified-zero-history-1130136 unverified-zero-history-1130137 unverified-zero-history-1130138 unverified-zero-history-1130139 unverified-zero-history-1131177 unverified-zero-history-1130140 unverified-zero-history-1130141 unverified-zero-history-1130142 unverified-zero-history-1130706 entity-collision-1079057 unverified-zero-history-1130143 unverified-zero-history-1130144 org-pooling-rich-gang-prm3 series-format-not-published
```

## git diff --stat of this run's output
```
 data/node/raw/bovada_lol.json              |     2 +-
 data/node/raw/collect_log.json             |    42 +-
 data/node/raw/hotspawn_lobby_check.json    |     2 +-
 data/node/raw/hotspawn_lol_fixtures.json   |     2 +-
 data/node/raw/kalshi_lol.json              |     2 +-
 data/node/raw/kambi_lol.json               |     2 +-
 data/node/raw/pinnacle_lol.json            |     2 +-
 data/node/raw/pinnacle_matchups_cache.json |     2 +-
 data/node/raw/polymarket_lol.json          |     2 +-
 data/node/raw/smarkets_lol.json            |     2 +-
 docs/data/canonical_snapshot.json          |     2 +-
 docs/data/flags.json                       |    80 +-
 docs/data/picks.csv                        |    90 +-
 docs/data/picks.json                       | 29086 +++++++++++++--------------
 docs/featured.html                         |    94 +-
 docs/flagged.html                          |    78 +-
 docs/index.html                            |   271 +-
 docs/methodology.html                      |    56 +-
 docs/originated.html                       |  1134 +-
 docs/picks.html                            |  1007 +-
 docs/results.html                          |   617 +-
 docs/table.html                            |   532 +-
 docs/tournaments.html                      |   541 +-
 docs/unresolved.html                       |   132 +-
 32 files changed, 32609 insertions(+), 32334 deletions(-)
```

## python3 audit/verify_docs.py
```
PASS    1 docs/data/picks.json mirrors data/node/picks.json :: 1205225 bytes
PASS    2 every active match with a pick rendered on picks.html :: 76 picked rows, missing: []
PASS    3 rendered probabilities match JSON :: bad: []
PASS    4 every active match without a pick is on unresolved.html and index.html :: 20 unresolved, missing: []
PASS    5 every rendered card links its Hotspawn match card :: missing: []
PASS    6 market rows carry all matched venue source links :: 4 market rows, missing: []
PASS    7 results.html renders only official scores (no fabricated fills) :: 285 ended/forfeited checked, bad: []
PASS    8 no ledger entry with an official result renders as pending :: bad: []
PASS    9 navigation on every docs page :: []
PASS  9.1 exec summary links every picks view & subpage :: []
PASS   10 no broken internal links or fragments in docs/ :: []
PASS   11 probabilities sum to 100% and pick = argmax :: bad: []
PASS   12 all scheduled matches rendered 1:1 on docs/table.html with source links :: 189 scheduled rows, missing: []
PASS   13 all 10 docs/*.html category pages exist with mobile viewport :: missing=[] no_vp=[]
PASS   14 no '(Kills)' derivative market used as a match line :: []
PASS   15 cross-region homonym quarantines (#1083097, #1079031) & Solid Gaming DQ walkovers verified :: []
PASS   16 every Flagged for Review item renders with Hotspawn + official source links :: 33 flags, bad=[]

rows: 508 total | scheduled 189 | active 96 (76 with pick, 20 unresolved) | ended/forfeited 285 | flags 33 | ledger 355 entries

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
note: #1079080 is no longer scheduled (kicked off or settled) — its Kalshi + Polymarket pair assertions are skipped
note: #1083097 is no longer scheduled — homonym quarantine assertions skipped
note: #1079031 is no longer scheduled — Swiss PvB homonym assertions skipped
node:internal/modules/run_main:123
    triggerUncaughtException(
    ^

AssertionError [ERR_ASSERTION]: #1081423 Frank Esports favored on pre-kickoff Elo
+ actual - expected

+ 'Ground Zero Gaming'
- 'Frank Esports'
    at file:///home/runner/work/LOLHOTSPAWN1/LOLHOTSPAWN1/audit/session_6669f798/test_node_pipeline.mjs:124:10 {
  generatedMessage: false,
  code: 'ERR_ASSERTION',
  actual: 'Ground Zero Gaming',
  expected: 'Frank Esports',
  operator: 'strictEqual'
}

Node.js v20.20.2
exit=1
```

## python3 audit/verify_docs_parity.py
```
PASS    1 no docs page reuses a canonical title and every docs title says 'secondary' :: reused: []; unmarked: []
PASS    2 secondary banner is first in <body> and every page links the canonical hub :: banner not first: []; no canonical link: []
PASS    3 reconciliation + overview numbers reproduce both committed snapshots :: reconcile section: True; missing: []; oos series rendered: 22,549
PASS    4 every scheduled row deep-links to a canonical anchor that exists :: 189 rows; missing link: []; dead anchor: []
PASS    5 fixtures absent from the canonical snapshot are explained, not silently dropped :: unexplained: []
PASS    6 canonical probabilities rendered in docs/ equal data/matches.json :: mismatched: []
PASS    7 divergences (>= 5 pp or opposite pick) are marked and listed :: 28 divergent fixtures; unmarked rows: []; missing from overview ledger: []
PASS    8 no series format is rendered that Hotspawn does not publish :: 189 rows have best_of=null in the feed; bad renders: []
PASS    9 internal links and fragments resolve (including ../ into the root site) :: broken: []
PASS   10 methodology documents the canonical relationship and the unpublished series format :: missing: []
WARN      canonical cards missing from the secondary snapshot :: 77

scheduled rows: 189 | shared with canonical: 135 | both priced: 128 | divergent: 28 | mean gap 3.449 pp | max gap 57.75 pp

ALL DOCS-PARITY CHECKS PASS
exit=0
```
