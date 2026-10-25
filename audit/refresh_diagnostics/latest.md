# refresh-docs verification output

run 40159329373 attempt 1 · commit `9075cc29c2be994b3390a6580d26b33f2d4be9c5` · 2026-10-25T03:44:56Z

## freshly generated snapshot
```
generated_at 2026-10-25T03:44:55.889Z | raw feed 2026-10-25T03:44:48.627Z
counts {"total_rows":567,"scheduled_total":232,"active_open_locked":151,"stale_scheduled":81,"ended_recent":262,"forfeited_recent":26,"cancelled_recent":46,"active_market":3,"active_model":148,"active_unresolved":0,"scheduled_market":3,"scheduled_model":222,"scheduled_walkover_settlement":4,"scheduled_unresolved":3,"by_source_scheduled":{"model":149,"walkover_settlement":4,"model_provisional":73,"unresolved":3,"market_bovada":2,"market_consensus":1},"by_source_active":{"market_bovada":2,"model":106,"model_provisional":42,"market_consensus":1},"flags":14}
calibration {"n":22383,"brier":0.2251,"series":32547}
rows 567 | scheduled 232
market rows: 1067880:1[Bovada] 1067689:1[Bovada] 1079080:2[Polymarket+Kalshi CFTC]
scheduled rows with best_of != null: 0
flags 14 | dq-walkover-1071170 unverified-zero-history-1074627 dq-walkover-1071200 dq-walkover-1071206 dq-walkover-1071186 unverified-zero-history-1082002 unverified-zero-history-1083593 entity-collision-1079031 entity-collision-1079038 entity-collision-1082746 entity-collision-1079053 entity-collision-1079057 org-pooling-rich-gang-prm3 series-format-not-published
```

## git diff --stat of this run's output
```
 data/node/model/ratings.json               |  6413 +++---
 data/node/picks.csv                        |   107 +-
 data/node/picks.json                       | 28751 +++++++++++++--------------
 data/node/raw/collect_log.json             |    44 +-
 data/node/raw/hotspawn_lobby_check.json    |     2 +-
 data/node/raw/hotspawn_lol_fixtures.json   |     2 +-
 data/node/raw/kalshi_lol.json              |     2 +-
 data/node/raw/kambi_lol.json               |     2 +-
 data/node/raw/pinnacle_lol.json            |     2 +-
 data/node/raw/pinnacle_matchups_cache.json |     2 +-
 data/node/raw/polymarket_lol.json          |     2 +-
 docs/data/flags.json                       |    18 +-
 docs/data/picks.csv                        |   107 +-
 docs/data/picks.json                       | 28751 +++++++++++++--------------
 docs/featured.html                         |   344 +-
 docs/flagged.html                          |    25 +-
 docs/index.html                            |   402 +-
 docs/methodology.html                      |    66 +-
 docs/originated.html                       |   747 +-
 docs/picks.html                            |  1248 +-
 docs/results.html                          |   371 +-
 docs/table.html                            |   511 +-
 docs/tournaments.html                      |   282 +-
 docs/unresolved.html                       |    12 +-
 29 files changed, 32434 insertions(+), 36758 deletions(-)
```

## python3 audit/verify_docs.py
```
PASS    1 docs/data/picks.json mirrors data/node/picks.json :: 1332869 bytes
PASS    2 every active match with a pick rendered on picks.html :: 152 picked rows, missing: []
PASS    3 rendered probabilities match JSON :: bad: []
PASS    4 every active match without a pick is on unresolved.html and index.html :: 0 unresolved, missing: []
PASS    5 every rendered card links its Hotspawn match card :: missing: []
PASS    6 market rows carry all matched venue source links :: 3 market rows, missing: []
PASS    7 results.html renders only official scores (no fabricated fills) :: 288 ended/forfeited checked, bad: []
PASS    8 no ledger entry with an official result renders as pending :: bad: []
PASS    9 navigation on every docs page :: []
PASS  9.1 exec summary links every picks view & subpage :: []
PASS   10 no broken internal links or fragments in docs/ :: []
PASS   11 probabilities sum to 100% and pick = argmax :: bad: []
PASS   12 all scheduled matches rendered 1:1 on docs/table.html with source links :: 232 scheduled rows, missing: []
PASS   13 all 10 docs/*.html category pages exist with mobile viewport :: missing=[] no_vp=[]
PASS   14 no '(Kills)' derivative market used as a match line :: []
PASS   15 cross-region homonym quarantines (#1083097, #1079031) & Solid Gaming DQ walkovers verified :: []
PASS   16 every Flagged for Review item renders with Hotspawn + official source links :: 14 flags, bad=[]

rows: 567 total | scheduled 232 | active 152 (152 with pick, 0 unresolved) | ended/forfeited 288 | flags 14 | ledger 262 entries

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
note: #1067880 is a single-venue fallback (Bovada, quote 2026-10-24T16:29:32Z, 390 min before kick-off) - no second venue was live once the card locked
note: #1067689 is a single-venue fallback (Bovada, quote 2026-10-24T16:29:32Z, 450 min before kick-off) - no second venue was live once the card locked
note: no Worlds 2026 Main Event row is pre-kickoff in this snapshot (3 market rows) — the >=4-venue assertion is skipped, not weakened
note: #1083097 is no longer scheduled — homonym quarantine assertions skipped
PASS session_6669f798 test_node_pipeline.mjs: 232 scheduled, 3 market rows (4 venue quotes joined, 2 single-venue fallback), OOS Brier=0.2251
exit=0
```

## python3 audit/verify_docs_parity.py
```
PASS    1 no docs page reuses a canonical title and every docs title says 'secondary' :: reused: []; unmarked: []
PASS    2 secondary banner is first in <body> and every page links the canonical hub :: banner not first: []; no canonical link: []
PASS    3 reconciliation + overview numbers reproduce both committed snapshots :: reconcile section: True; missing: []; oos series rendered: 22,383
PASS    4 every scheduled row deep-links to a canonical anchor that exists :: 232 rows; missing link: []; dead anchor: []
PASS    5 fixtures absent from the canonical snapshot are explained, not silently dropped :: unexplained: []
PASS    6 canonical probabilities rendered in docs/ equal data/matches.json :: mismatched: []
PASS    7 divergences (>= 5 pp or opposite pick) are marked and listed :: 29 divergent fixtures; unmarked rows: []; missing from overview ledger: []
PASS    8 no series format is rendered that Hotspawn does not publish :: 232 rows have best_of=null in the feed; bad renders: []
PASS    9 internal links and fragments resolve (including ../ into the root site) :: broken: []
PASS   10 methodology documents the canonical relationship and the unpublished series format :: missing: []
WARN      canonical cards missing from the secondary snapshot :: 13

scheduled rows: 232 | shared with canonical: 228 | both priced: 221 | divergent: 29 | mean gap 2.206 pp | max gap 18.89 pp

ALL DOCS-PARITY CHECKS PASS
exit=0
```
