# refresh-docs verification output

run 42341419776 attempt 1 · commit `0a8c3ca6ae7f5377b6eaf1427649b4a862a634c8` · 2026-11-07T05:08:28Z

## freshly generated snapshot
```
generated_at 2026-11-07T05:08:28.230Z | raw feed 2026-11-07T05:08:20.274Z
counts {"total_rows":525,"scheduled_total":183,"active_open_locked":95,"stale_scheduled":88,"ended_recent":287,"forfeited_recent":12,"cancelled_recent":42,"active_market":2,"active_model":78,"active_unresolved":15,"scheduled_market":2,"scheduled_model":159,"scheduled_walkover_settlement":4,"scheduled_unresolved":18,"by_source_scheduled":{"model":111,"walkover_settlement":4,"model_provisional":48,"unresolved":18,"market_pinnacle":1,"market_consensus":1},"by_source_active":{"model":62,"model_provisional":16,"market_pinnacle":1,"market_consensus":1,"unresolved":15},"flags":26}
calibration {"n":22490,"brier":0.2251,"series":32680}
rows 525 | scheduled 183
market rows: 1128533:1[Pinnacle] 1094932:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Smarkets (UKGC)]
scheduled rows with best_of != null: 0
flags 26 | dq-walkover-1071170 unverified-zero-history-1074627 dq-walkover-1071200 dq-walkover-1071206 dq-walkover-1071186 unverified-zero-history-1082002 unverified-zero-history-1083593 entity-collision-1079053 unverified-zero-history-1130130 unverified-zero-history-1130131 unverified-zero-history-1130132 unverified-zero-history-1130133 unverified-zero-history-1130134 unverified-zero-history-1130135 unverified-zero-history-1130136 unverified-zero-history-1130137 unverified-zero-history-1130138 unverified-zero-history-1130139 unverified-zero-history-1130140 unverified-zero-history-1130141 unverified-zero-history-1130142 entity-collision-1079057 unverified-zero-history-1130143 unverified-zero-history-1130144 org-pooling-rich-gang-prm3 series-format-not-published
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
 docs/data/flags.json                       |    4 +-
 docs/data/picks.csv                        |   25 +-
 docs/data/picks.json                       | 2751 +++++++++++++---------------
 docs/featured.html                         |  126 +-
 docs/flagged.html                          |    8 +-
 docs/index.html                            |  168 +-
 docs/methodology.html                      |   32 +-
 docs/originated.html                       |  225 +--
 docs/picks.html                            |  295 +--
 docs/results.html                          |  116 +-
 docs/table.html                            |  153 +-
 docs/tournaments.html                      |   94 +-
 docs/unresolved.html                       |    6 +-
 32 files changed, 3321 insertions(+), 4167 deletions(-)
```

## python3 audit/verify_docs.py
```
PASS    1 docs/data/picks.json mirrors data/node/picks.json :: 1245602 bytes
PASS    2 every active match with a pick rendered on picks.html :: 80 picked rows, missing: []
PASS    3 rendered probabilities match JSON :: bad: []
PASS    4 every active match without a pick is on unresolved.html and index.html :: 15 unresolved, missing: []
PASS    5 every rendered card links its Hotspawn match card :: missing: []
PASS    6 market rows carry all matched venue source links :: 2 market rows, missing: []
PASS    7 results.html renders only official scores (no fabricated fills) :: 299 ended/forfeited checked, bad: []
PASS    8 no ledger entry with an official result renders as pending :: bad: []
PASS    9 navigation on every docs page :: []
PASS  9.1 exec summary links every picks view & subpage :: []
PASS   10 no broken internal links or fragments in docs/ :: []
PASS   11 probabilities sum to 100% and pick = argmax :: bad: []
PASS   12 all scheduled matches rendered 1:1 on docs/table.html with source links :: 183 scheduled rows, missing: []
PASS   13 all 10 docs/*.html category pages exist with mobile viewport :: missing=[] no_vp=[]
PASS   14 no '(Kills)' derivative market used as a match line :: []
PASS   15 cross-region homonym quarantines (#1083097, #1079031) & Solid Gaming DQ walkovers verified :: []
PASS   16 every Flagged for Review item renders with Hotspawn + official source links :: 26 flags, bad=[]

rows: 525 total | scheduled 183 | active 95 (80 with pick, 15 unresolved) | ended/forfeited 299 | flags 26 | ledger 335 entries

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
note: #1128533 is a single-venue fallback (Pinnacle, quote 2026-11-07T05:08:22.617Z, 232 min before kick-off) - no second venue was live once the card locked
note: #1079080 is no longer scheduled (kicked off or settled) — its Kalshi + Polymarket pair assertions are skipped
note: #1083097 is no longer scheduled — homonym quarantine assertions skipped
note: #1079031 is no longer scheduled — Swiss PvB homonym assertions skipped
PASS session_6669f798 test_node_pipeline.mjs: 183 scheduled, 2 market rows (6 venue quotes joined, 1 single-venue fallback), OOS Brier=0.2251
exit=0
```

## python3 audit/verify_docs_parity.py
```
PASS    1 no docs page reuses a canonical title and every docs title says 'secondary' :: reused: []; unmarked: []
PASS    2 secondary banner is first in <body> and every page links the canonical hub :: banner not first: []; no canonical link: []
PASS    3 reconciliation + overview numbers reproduce both committed snapshots :: reconcile section: True; missing: []; oos series rendered: 22,490
PASS    4 every scheduled row deep-links to a canonical anchor that exists :: 183 rows; missing link: []; dead anchor: []
PASS    5 fixtures absent from the canonical snapshot are explained, not silently dropped :: unexplained: []
PASS    6 canonical probabilities rendered in docs/ equal data/matches.json :: mismatched: []
PASS    7 divergences (>= 5 pp or opposite pick) are marked and listed :: 27 divergent fixtures; unmarked rows: []; missing from overview ledger: []
PASS    8 no series format is rendered that Hotspawn does not publish :: 183 rows have best_of=null in the feed; bad renders: []
PASS    9 internal links and fragments resolve (including ../ into the root site) :: broken: []
PASS   10 methodology documents the canonical relationship and the unpublished series format :: missing: []
WARN      canonical cards missing from the secondary snapshot :: 74

scheduled rows: 183 | shared with canonical: 138 | both priced: 131 | divergent: 27 | mean gap 2.705 pp | max gap 9.99 pp

ALL DOCS-PARITY CHECKS PASS
exit=0
```
