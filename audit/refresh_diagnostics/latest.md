# refresh-docs verification output

run 42734652957 attempt 1 · commit `e095d13820ba8827680b8fdc1a140c9ad3e2a1a3` · 2026-11-10T01:17:18Z

## freshly generated snapshot
```
generated_at 2026-11-10T01:17:18.014Z | raw feed 2026-11-10T01:17:07.435Z
counts {"total_rows":491,"scheduled_total":176,"active_open_locked":80,"stale_scheduled":96,"ended_recent":277,"forfeited_recent":5,"cancelled_recent":33,"active_market":4,"active_model":69,"active_unresolved":7,"scheduled_market":4,"scheduled_model":157,"scheduled_walkover_settlement":4,"scheduled_unresolved":11,"by_source_scheduled":{"model":101,"walkover_settlement":4,"model_provisional":56,"unresolved":11,"market_consensus":4},"by_source_active":{"market_consensus":4,"model":47,"model_provisional":22,"unresolved":7},"flags":18}
calibration {"n":22569,"brier":0.2251,"series":32801}
rows 491 | scheduled 176
market rows: 1081421:3[Unibet (Kambi)+Polymarket+Kalshi CFTC] 1082007:4[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC] 1081423:2[Polymarket+Kalshi CFTC] 1094982:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Smarkets (UKGC)]
scheduled rows with best_of != null: 0
flags 18 | dq-walkover-1071170 unverified-zero-history-1074627 dq-walkover-1071200 dq-walkover-1071206 dq-walkover-1071186 unverified-zero-history-1082002 unverified-zero-history-1083593 unverified-zero-history-1130132 unverified-zero-history-1130133 unverified-zero-history-1130136 unverified-zero-history-1130139 unverified-zero-history-1130706 entity-collision-1079057 unverified-zero-history-1130143 unverified-zero-history-1131686 unverified-zero-history-1131687 org-pooling-rich-gang-prm3 series-format-not-published
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
 docs/data/flags.json                       |   170 +-
 docs/data/picks.csv                        |   133 +-
 docs/data/picks.json                       | 34169 +++++++++++++--------------
 docs/featured.html                         |   176 +-
 docs/flagged.html                          |   157 +-
 docs/index.html                            |   539 +-
 docs/methodology.html                      |    58 +-
 docs/originated.html                       |  2128 +-
 docs/picks.html                            |  1964 +-
 docs/results.html                          |  1180 +-
 docs/table.html                            |  1017 +-
 docs/tournaments.html                      |   903 +-
 docs/unresolved.html                       |   326 +-
 32 files changed, 39597 insertions(+), 41990 deletions(-)
```

## python3 audit/verify_docs.py
```
PASS    1 docs/data/picks.json mirrors data/node/picks.json :: 1174009 bytes
PASS    2 every active match with a pick rendered on picks.html :: 73 picked rows, missing: []
PASS    3 rendered probabilities match JSON :: bad: []
PASS    4 every active match without a pick is on unresolved.html and index.html :: 7 unresolved, missing: []
PASS    5 every rendered card links its Hotspawn match card :: missing: []
PASS    6 market rows carry all matched venue source links :: 4 market rows, missing: []
PASS    7 results.html renders only official scores (no fabricated fills) :: 282 ended/forfeited checked, bad: []
PASS    8 no ledger entry with an official result renders as pending :: bad: []
PASS    9 navigation on every docs page :: []
PASS  9.1 exec summary links every picks view & subpage :: []
PASS   10 no broken internal links or fragments in docs/ :: []
PASS   11 probabilities sum to 100% and pick = argmax :: bad: []
PASS   12 all scheduled matches rendered 1:1 on docs/table.html with source links :: 176 scheduled rows, missing: []
PASS   13 all 10 docs/*.html category pages exist with mobile viewport :: missing=[] no_vp=[]
PASS   14 no '(Kills)' derivative market used as a match line :: []
PASS   15 cross-region homonym quarantines (#1083097, #1079031) & Solid Gaming DQ walkovers verified :: []
PASS   16 every Flagged for Review item renders with Hotspawn + official source links :: 18 flags, bad=[]

rows: 491 total | scheduled 176 | active 80 (73 with pick, 7 unresolved) | ended/forfeited 282 | flags 18 | ledger 375 entries

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
PASS    3 reconciliation + overview numbers reproduce both committed snapshots :: reconcile section: True; missing: []; oos series rendered: 22,569
PASS    4 every scheduled row deep-links to a canonical anchor that exists :: 176 rows; missing link: []; dead anchor: []
PASS    5 fixtures absent from the canonical snapshot are explained, not silently dropped :: unexplained: []
PASS    6 canonical probabilities rendered in docs/ equal data/matches.json :: mismatched: []
PASS    7 divergences (>= 5 pp or opposite pick) are marked and listed :: 25 divergent fixtures; unmarked rows: []; missing from overview ledger: []
PASS    8 no series format is rendered that Hotspawn does not publish :: 176 rows have best_of=null in the feed; bad renders: []
PASS    9 internal links and fragments resolve (including ../ into the root site) :: broken: []
PASS   10 methodology documents the canonical relationship and the unpublished series format :: missing: []
WARN      canonical cards missing from the secondary snapshot :: 89

scheduled rows: 176 | shared with canonical: 123 | both priced: 116 | divergent: 25 | mean gap 3.478 pp | max gap 55.75 pp

ALL DOCS-PARITY CHECKS PASS
exit=0
```
