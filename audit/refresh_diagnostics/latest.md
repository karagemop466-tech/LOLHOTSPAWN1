# refresh-docs verification output

run 42565942634 attempt 1 · commit `3117906334b598ac7d01bd65dfaa4552cc2b3e69` · 2026-11-09T05:12:52Z

## freshly generated snapshot
```
generated_at 2026-11-09T05:12:52.529Z | raw feed 2026-11-09T05:12:44.205Z
counts {"total_rows":465,"scheduled_total":182,"active_open_locked":75,"stale_scheduled":107,"ended_recent":246,"forfeited_recent":5,"cancelled_recent":32,"active_market":3,"active_model":56,"active_unresolved":16,"scheduled_market":3,"scheduled_model":156,"scheduled_walkover_settlement":4,"scheduled_unresolved":19,"by_source_scheduled":{"model":104,"walkover_settlement":4,"model_provisional":52,"unresolved":19,"market_consensus":3},"by_source_active":{"model_provisional":17,"unresolved":16,"model":39,"market_consensus":3},"flags":26}
calibration {"n":22554,"brier":0.2251,"series":32782}
rows 465 | scheduled 182
market rows: 1081421:2[Polymarket+Kalshi CFTC] 1082007:2[Polymarket+Kalshi CFTC] 1081423:2[Polymarket+Kalshi CFTC]
scheduled rows with best_of != null: 0
flags 26 | dq-walkover-1071170 unverified-zero-history-1074627 dq-walkover-1071200 dq-walkover-1071206 dq-walkover-1071186 unverified-zero-history-1082002 unverified-zero-history-1083593 unverified-zero-history-1130130 unverified-zero-history-1130131 unverified-zero-history-1130132 unverified-zero-history-1130133 unverified-zero-history-1130134 unverified-zero-history-1130135 unverified-zero-history-1130136 unverified-zero-history-1130137 unverified-zero-history-1130138 unverified-zero-history-1130139 unverified-zero-history-1130140 unverified-zero-history-1130141 unverified-zero-history-1130142 unverified-zero-history-1130706 entity-collision-1079057 unverified-zero-history-1130143 unverified-zero-history-1130144 org-pooling-rich-gang-prm3 series-format-not-published
```

## git diff --stat of this run's output
```
 data/node/raw/bovada_lol.json              |     2 +-
 data/node/raw/collect_log.json             |    40 +-
 data/node/raw/hotspawn_lobby_check.json    |     2 +-
 data/node/raw/hotspawn_lol_fixtures.json   |     2 +-
 data/node/raw/kalshi_lol.json              |     2 +-
 data/node/raw/kambi_lol.json               |     2 +-
 data/node/raw/pinnacle_lol.json            |     2 +-
 data/node/raw/pinnacle_matchups_cache.json |     2 +-
 data/node/raw/polymarket_lol.json          |     2 +-
 data/node/raw/smarkets_lol.json            |     2 +-
 docs/data/canonical_snapshot.json          |     2 +-
 docs/data/flags.json                       |    18 +-
 docs/data/picks.csv                        |    95 +-
 docs/data/picks.json                       | 31429 ++++++++++++---------------
 docs/featured.html                         |   104 +-
 docs/flagged.html                          |    21 +-
 docs/index.html                            |   180 +-
 docs/methodology.html                      |    60 +-
 docs/originated.html                       |  1563 +-
 docs/picks.html                            |  1430 +-
 docs/results.html                          |   975 +-
 docs/table.html                            |   611 +-
 docs/tournaments.html                      |   596 +-
 docs/unresolved.html                       |     6 +-
 32 files changed, 31693 insertions(+), 39459 deletions(-)
```

## python3 audit/verify_docs.py
```
PASS    1 docs/data/picks.json mirrors data/node/picks.json :: 1100313 bytes
PASS    2 every active match with a pick rendered on picks.html :: 59 picked rows, missing: []
PASS    3 rendered probabilities match JSON :: bad: []
PASS    4 every active match without a pick is on unresolved.html and index.html :: 16 unresolved, missing: []
PASS    5 every rendered card links its Hotspawn match card :: missing: []
PASS    6 market rows carry all matched venue source links :: 3 market rows, missing: []
PASS    7 results.html renders only official scores (no fabricated fills) :: 251 ended/forfeited checked, bad: []
PASS    8 no ledger entry with an official result renders as pending :: bad: []
PASS    9 navigation on every docs page :: []
PASS  9.1 exec summary links every picks view & subpage :: []
PASS   10 no broken internal links or fragments in docs/ :: []
PASS   11 probabilities sum to 100% and pick = argmax :: bad: []
PASS   12 all scheduled matches rendered 1:1 on docs/table.html with source links :: 182 scheduled rows, missing: []
PASS   13 all 10 docs/*.html category pages exist with mobile viewport :: missing=[] no_vp=[]
PASS   14 no '(Kills)' derivative market used as a match line :: []
PASS   15 cross-region homonym quarantines (#1083097, #1079031) & Solid Gaming DQ walkovers verified :: []
PASS   16 every Flagged for Review item renders with Hotspawn + official source links :: 26 flags, bad=[]

rows: 465 total | scheduled 182 | active 75 (59 with pick, 16 unresolved) | ended/forfeited 251 | flags 26 | ledger 359 entries

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
note: no Worlds 2026 Main Event row is pre-kickoff in this snapshot (3 market rows) — the >=4-venue assertion is skipped, not weakened
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
PASS    3 reconciliation + overview numbers reproduce both committed snapshots :: reconcile section: True; missing: []; oos series rendered: 22,554
PASS    4 every scheduled row deep-links to a canonical anchor that exists :: 182 rows; missing link: []; dead anchor: []
PASS    5 fixtures absent from the canonical snapshot are explained, not silently dropped :: unexplained: []
PASS    6 canonical probabilities rendered in docs/ equal data/matches.json :: mismatched: []
PASS    7 divergences (>= 5 pp or opposite pick) are marked and listed :: 26 divergent fixtures; unmarked rows: []; missing from overview ledger: []
PASS    8 no series format is rendered that Hotspawn does not publish :: 182 rows have best_of=null in the feed; bad renders: []
PASS    9 internal links and fragments resolve (including ../ into the root site) :: broken: []
PASS   10 methodology documents the canonical relationship and the unpublished series format :: missing: []
WARN      canonical cards missing from the secondary snapshot :: 81

scheduled rows: 182 | shared with canonical: 131 | both priced: 124 | divergent: 26 | mean gap 3.397 pp | max gap 58.05 pp

ALL DOCS-PARITY CHECKS PASS
exit=0
```
