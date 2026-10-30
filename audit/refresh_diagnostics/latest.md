# refresh-docs verification output

run 41005274466 attempt 1 · commit `4d4d60ca2b615637a0b88713261ba3f4b3b996a1` · 2026-10-30T04:52:47Z

## freshly generated snapshot
```
generated_at 2026-10-30T04:52:46.792Z | raw feed 2026-10-30T04:52:35.137Z
counts {"total_rows":554,"scheduled_total":218,"active_open_locked":132,"stale_scheduled":86,"ended_recent":267,"forfeited_recent":21,"cancelled_recent":47,"active_market":2,"active_model":114,"active_unresolved":16,"scheduled_market":2,"scheduled_model":193,"scheduled_walkover_settlement":4,"scheduled_unresolved":19,"by_source_scheduled":{"model":141,"walkover_settlement":4,"model_provisional":52,"unresolved":19,"market_consensus":2},"by_source_active":{"unresolved":16,"model":94,"market_consensus":2,"model_provisional":20},"flags":29}
calibration {"n":22415,"brier":0.2251,"series":32579}
rows 554 | scheduled 218
market rows: 1094912:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Smarkets (UKGC)] 1094913:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Smarkets (UKGC)]
scheduled rows with best_of != null: 0
flags 29 | dq-walkover-1071170 unverified-zero-history-1074627 dq-walkover-1071200 dq-walkover-1071206 dq-walkover-1071186 unverified-zero-history-1082002 unverified-zero-history-1083593 unverified-zero-history-1126356 unverified-zero-history-1126357 unverified-zero-history-1126358 unverified-zero-history-1126359 unverified-zero-history-1126360 unverified-zero-history-1126361 entity-collision-1079038 unverified-zero-history-1126362 unverified-zero-history-1126363 unverified-zero-history-1126364 unverified-zero-history-1126365 unverified-zero-history-1126366 unverified-zero-history-1126367 unverified-zero-history-1121690 unverified-zero-history-1121692 unverified-zero-history-1121693 unverified-zero-history-1121694 entity-collision-1082746 entity-collision-1079053 entity-collision-1079057 org-pooling-rich-gang-prm3 series-format-not-published
```

## git diff --stat of this run's output
```
 data/node/raw/bovada_lol.json              |     2 +-
 data/node/raw/collect_log.json             |    50 +-
 data/node/raw/hotspawn_lobby_check.json    |     2 +-
 data/node/raw/hotspawn_lol_fixtures.json   |     2 +-
 data/node/raw/kalshi_lol.json              |     2 +-
 data/node/raw/kambi_lol.json               |     2 +-
 data/node/raw/pinnacle_lol.json            |     2 +-
 data/node/raw/pinnacle_matchups_cache.json |     2 +-
 data/node/raw/polymarket_lol.json          |     2 +-
 data/node/raw/smarkets_lol.json            |     2 +-
 docs/data/canonical_snapshot.json          |     2 +-
 docs/data/flags.json                       |   150 +-
 docs/data/picks.csv                        |    52 +-
 docs/data/picks.json                       | 10616 ++++++++++++++-------------
 docs/featured.html                         |    82 +-
 docs/flagged.html                          |   142 +-
 docs/index.html                            |   435 +-
 docs/methodology.html                      |    30 +-
 docs/originated.html                       |   409 +-
 docs/picks.html                            |   543 +-
 docs/results.html                          |   168 +-
 docs/table.html                            |   346 +-
 docs/tournaments.html                      |   364 +-
 docs/unresolved.html                       |   298 +-
 32 files changed, 13872 insertions(+), 11597 deletions(-)
```

## python3 audit/verify_docs.py
```
PASS    1 docs/data/picks.json mirrors data/node/picks.json :: 1323027 bytes
PASS    2 every active match with a pick rendered on picks.html :: 117 picked rows, missing: []
PASS    3 rendered probabilities match JSON :: bad: []
PASS    4 every active match without a pick is on unresolved.html and index.html :: 16 unresolved, missing: []
PASS    5 every rendered card links its Hotspawn match card :: missing: []
PASS    6 market rows carry all matched venue source links :: 2 market rows, missing: []
PASS    7 results.html renders only official scores (no fabricated fills) :: 288 ended/forfeited checked, bad: []
PASS    8 no ledger entry with an official result renders as pending :: bad: []
PASS    9 navigation on every docs page :: []
PASS  9.1 exec summary links every picks view & subpage :: []
PASS   10 no broken internal links or fragments in docs/ :: []
PASS   11 probabilities sum to 100% and pick = argmax :: bad: []
PASS   12 all scheduled matches rendered 1:1 on docs/table.html with source links :: 218 scheduled rows, missing: []
PASS   13 all 10 docs/*.html category pages exist with mobile viewport :: missing=[] no_vp=[]
PASS   14 no '(Kills)' derivative market used as a match line :: []
PASS   15 cross-region homonym quarantines (#1083097, #1079031) & Solid Gaming DQ walkovers verified :: []
PASS   16 every Flagged for Review item renders with Hotspawn + official source links :: 29 flags, bad=[]

rows: 554 total | scheduled 218 | active 133 (117 with pick, 16 unresolved) | ended/forfeited 288 | flags 29 | ledger 289 entries

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
PASS session_6669f798 test_node_pipeline.mjs: 218 scheduled, 2 market rows (10 venue quotes joined, 0 single-venue fallback), OOS Brier=0.2251
exit=0
```

## python3 audit/verify_docs_parity.py
```
PASS    1 no docs page reuses a canonical title and every docs title says 'secondary' :: reused: []; unmarked: []
PASS    2 secondary banner is first in <body> and every page links the canonical hub :: banner not first: []; no canonical link: []
PASS    3 reconciliation + overview numbers reproduce both committed snapshots :: reconcile section: True; missing: []; oos series rendered: 22,415
PASS    4 every scheduled row deep-links to a canonical anchor that exists :: 218 rows; missing link: []; dead anchor: []
PASS    5 fixtures absent from the canonical snapshot are explained, not silently dropped :: unexplained: []
PASS    6 canonical probabilities rendered in docs/ equal data/matches.json :: mismatched: []
PASS    7 divergences (>= 5 pp or opposite pick) are marked and listed :: 30 divergent fixtures; unmarked rows: []; missing from overview ledger: []
PASS    8 no series format is rendered that Hotspawn does not publish :: 218 rows have best_of=null in the feed; bad renders: []
PASS    9 internal links and fragments resolve (including ../ into the root site) :: broken: []
PASS   10 methodology documents the canonical relationship and the unpublished series format :: missing: []
WARN      canonical cards missing from the secondary snapshot :: 21

scheduled rows: 218 | shared with canonical: 191 | both priced: 184 | divergent: 30 | mean gap 2.394 pp | max gap 9.76 pp

ALL DOCS-PARITY CHECKS PASS
exit=0
```
