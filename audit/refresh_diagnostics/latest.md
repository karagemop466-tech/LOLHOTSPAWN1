# refresh-docs verification output

run 42449144788 attempt 1 · commit `e30a0173373cc90f8d66b8ef2d51624a29968bfe` · 2026-11-08T05:02:23Z

## freshly generated snapshot
```
generated_at 2026-11-08T05:02:22.920Z | raw feed 2026-11-08T05:02:15.181Z
counts {"total_rows":515,"scheduled_total":179,"active_open_locked":83,"stale_scheduled":96,"ended_recent":287,"forfeited_recent":9,"cancelled_recent":39,"active_market":3,"active_model":64,"active_unresolved":16,"scheduled_market":3,"scheduled_model":153,"scheduled_walkover_settlement":4,"scheduled_unresolved":19,"by_source_scheduled":{"model":107,"walkover_settlement":4,"model_provisional":46,"unresolved":19,"market_consensus":3},"by_source_active":{"model":52,"model_provisional":12,"market_consensus":3,"unresolved":16},"flags":27}
calibration {"n":22502,"brier":0.2251,"series":32702}
rows 515 | scheduled 179
market rows: 1130194:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Smarkets (UKGC)] 1081421:2[Polymarket+Kalshi CFTC] 1082007:2[Polymarket+Kalshi CFTC]
scheduled rows with best_of != null: 0
flags 27 | dq-walkover-1071170 unverified-zero-history-1074627 dq-walkover-1071200 dq-walkover-1071206 dq-walkover-1071186 unverified-zero-history-1082002 unverified-zero-history-1083593 entity-collision-1079053 unverified-zero-history-1130130 unverified-zero-history-1130131 unverified-zero-history-1130132 unverified-zero-history-1130133 unverified-zero-history-1130134 unverified-zero-history-1130135 unverified-zero-history-1130136 unverified-zero-history-1130137 unverified-zero-history-1130138 unverified-zero-history-1130139 unverified-zero-history-1130140 unverified-zero-history-1130141 unverified-zero-history-1130142 unverified-zero-history-1130706 entity-collision-1079057 unverified-zero-history-1130143 unverified-zero-history-1130144 org-pooling-rich-gang-prm3 series-format-not-published
```

## git diff --stat of this run's output
```
 data/node/raw/bovada_lol.json              |    2 +-
 data/node/raw/collect_log.json             |   40 +-
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
 docs/data/picks.csv                        |   28 +-
 docs/data/picks.json                       | 1878 ++++++++++++----------------
 docs/featured.html                         |  110 +-
 docs/flagged.html                          |    8 +-
 docs/index.html                            |  127 +-
 docs/methodology.html                      |   32 +-
 docs/originated.html                       |  269 +---
 docs/picks.html                            |  524 +-------
 docs/results.html                          |  182 +--
 docs/table.html                            |  158 +--
 docs/tournaments.html                      |  106 +-
 docs/unresolved.html                       |    6 +-
 32 files changed, 2390 insertions(+), 3768 deletions(-)
```

## python3 audit/verify_docs.py
```
PASS    1 docs/data/picks.json mirrors data/node/picks.json :: 1225494 bytes
PASS    2 every active match with a pick rendered on picks.html :: 67 picked rows, missing: []
PASS    3 rendered probabilities match JSON :: bad: []
PASS    4 every active match without a pick is on unresolved.html and index.html :: 16 unresolved, missing: []
PASS    5 every rendered card links its Hotspawn match card :: missing: []
PASS    6 market rows carry all matched venue source links :: 3 market rows, missing: []
PASS    7 results.html renders only official scores (no fabricated fills) :: 296 ended/forfeited checked, bad: []
PASS    8 no ledger entry with an official result renders as pending :: bad: []
PASS    9 navigation on every docs page :: []
PASS  9.1 exec summary links every picks view & subpage :: []
PASS   10 no broken internal links or fragments in docs/ :: []
PASS   11 probabilities sum to 100% and pick = argmax :: bad: []
PASS   12 all scheduled matches rendered 1:1 on docs/table.html with source links :: 179 scheduled rows, missing: []
PASS   13 all 10 docs/*.html category pages exist with mobile viewport :: missing=[] no_vp=[]
PASS   14 no '(Kills)' derivative market used as a match line :: []
PASS   15 cross-region homonym quarantines (#1083097, #1079031) & Solid Gaming DQ walkovers verified :: []
PASS   16 every Flagged for Review item renders with Hotspawn + official source links :: 27 flags, bad=[]

rows: 515 total | scheduled 179 | active 83 (67 with pick, 16 unresolved) | ended/forfeited 296 | flags 27 | ledger 343 entries

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
PASS session_6669f798 test_node_pipeline.mjs: 179 scheduled, 3 market rows (9 venue quotes joined, 0 single-venue fallback), OOS Brier=0.2251
exit=0
```

## python3 audit/verify_docs_parity.py
```
PASS    1 no docs page reuses a canonical title and every docs title says 'secondary' :: reused: []; unmarked: []
PASS    2 secondary banner is first in <body> and every page links the canonical hub :: banner not first: []; no canonical link: []
PASS    3 reconciliation + overview numbers reproduce both committed snapshots :: reconcile section: True; missing: []; oos series rendered: 22,502
PASS    4 every scheduled row deep-links to a canonical anchor that exists :: 179 rows; missing link: []; dead anchor: []
PASS    5 fixtures absent from the canonical snapshot are explained, not silently dropped :: unexplained: []
PASS    6 canonical probabilities rendered in docs/ equal data/matches.json :: mismatched: []
PASS    7 divergences (>= 5 pp or opposite pick) are marked and listed :: 27 divergent fixtures; unmarked rows: []; missing from overview ledger: []
PASS    8 no series format is rendered that Hotspawn does not publish :: 179 rows have best_of=null in the feed; bad renders: []
PASS    9 internal links and fragments resolve (including ../ into the root site) :: broken: []
PASS   10 methodology documents the canonical relationship and the unpublished series format :: missing: []
WARN      canonical cards missing from the secondary snapshot :: 75

scheduled rows: 179 | shared with canonical: 137 | both priced: 130 | divergent: 27 | mean gap 3.066 pp | max gap 27.56 pp

ALL DOCS-PARITY CHECKS PASS
exit=0
```
