# refresh-docs verification output

run 41222216825 attempt 1 · commit `59cf357da0e7727605084a43f8e7cd02f89a8372` · 2026-10-31T16:58:47Z

## freshly generated snapshot
```
generated_at 2026-10-31T16:58:46.515Z | raw feed 2026-10-31T16:58:36.534Z
counts {"total_rows":557,"scheduled_total":200,"active_open_locked":115,"stale_scheduled":85,"ended_recent":287,"forfeited_recent":21,"cancelled_recent":49,"active_market":3,"active_model":107,"active_unresolved":5,"scheduled_market":3,"scheduled_model":181,"scheduled_walkover_settlement":4,"scheduled_unresolved":12,"by_source_scheduled":{"model":128,"walkover_settlement":4,"model_provisional":53,"unresolved":12,"market_consensus":3},"by_source_active":{"unresolved":5,"model":86,"market_consensus":3,"model_provisional":21},"flags":21}
calibration {"n":22432,"brier":0.2251,"series":32602}
rows 557 | scheduled 200
market rows: 1094915:5[Pinnacle+Unibet (Kambi)+Polymarket+Smarkets (UKGC)+Kalshi CFTC] 1094914:5[Pinnacle+Unibet (Kambi)+Polymarket+Smarkets (UKGC)+Kalshi CFTC] 1094916:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Smarkets (UKGC)]
scheduled rows with best_of != null: 0
flags 21 | dq-walkover-1071170 unverified-zero-history-1074627 dq-walkover-1071200 dq-walkover-1071206 dq-walkover-1071186 unverified-zero-history-1082002 unverified-zero-history-1083593 unverified-zero-history-1128817 unverified-zero-history-1126363 unverified-zero-history-1128818 unverified-zero-history-1126365 unverified-zero-history-1126367 unverified-zero-history-1121690 unverified-zero-history-1121692 unverified-zero-history-1121693 unverified-zero-history-1121694 entity-collision-1082746 entity-collision-1079053 entity-collision-1079057 org-pooling-rich-gang-prm3 series-format-not-published
```

## git diff --stat of this run's output
```
 data/node/raw/bovada_lol.json              |    2 +-
 data/node/raw/collect_log.json             |   28 +-
 data/node/raw/hotspawn_lobby_check.json    |    2 +-
 data/node/raw/hotspawn_lol_fixtures.json   |    2 +-
 data/node/raw/kalshi_lol.json              |    2 +-
 data/node/raw/kambi_lol.json               |    2 +-
 data/node/raw/pinnacle_lol.json            |    2 +-
 data/node/raw/pinnacle_matchups_cache.json |    2 +-
 data/node/raw/polymarket_lol.json          |    2 +-
 data/node/raw/smarkets_lol.json            |    2 +-
 docs/data/canonical_snapshot.json          |    2 +-
 docs/data/flags.json                       |   28 +-
 docs/data/picks.csv                        |   63 +-
 docs/data/picks.json                       | 1762 +++++++++++++---------------
 docs/featured.html                         |   60 +-
 docs/flagged.html                          |   32 +-
 docs/index.html                            |  232 +---
 docs/methodology.html                      |   32 +-
 docs/originated.html                       |  373 +++---
 docs/picks.html                            |  317 +++--
 docs/results.html                          |  123 +-
 docs/table.html                            |  211 ++--
 docs/tournaments.html                      |  126 +-
 docs/unresolved.html                       |  212 ++--
 32 files changed, 2851 insertions(+), 3335 deletions(-)
```

## python3 audit/verify_docs.py
```
PASS    1 docs/data/picks.json mirrors data/node/picks.json :: 1338416 bytes
PASS    2 every active match with a pick rendered on picks.html :: 110 picked rows, missing: []
PASS    3 rendered probabilities match JSON :: bad: []
PASS    4 every active match without a pick is on unresolved.html and index.html :: 5 unresolved, missing: []
PASS    5 every rendered card links its Hotspawn match card :: missing: []
PASS    6 market rows carry all matched venue source links :: 3 market rows, missing: []
PASS    7 results.html renders only official scores (no fabricated fills) :: 308 ended/forfeited checked, bad: []
PASS    8 no ledger entry with an official result renders as pending :: bad: []
PASS    9 navigation on every docs page :: []
PASS  9.1 exec summary links every picks view & subpage :: []
PASS   10 no broken internal links or fragments in docs/ :: []
PASS   11 probabilities sum to 100% and pick = argmax :: bad: []
PASS   12 all scheduled matches rendered 1:1 on docs/table.html with source links :: 200 scheduled rows, missing: []
PASS   13 all 10 docs/*.html category pages exist with mobile viewport :: missing=[] no_vp=[]
PASS   14 no '(Kills)' derivative market used as a match line :: []
PASS   15 cross-region homonym quarantines (#1083097, #1079031) & Solid Gaming DQ walkovers verified :: []
PASS   16 every Flagged for Review item renders with Hotspawn + official source links :: 21 flags, bad=[]

rows: 557 total | scheduled 200 | active 115 (110 with pick, 5 unresolved) | ended/forfeited 308 | flags 21 | ledger 294 entries

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
PASS session_6669f798 test_node_pipeline.mjs: 200 scheduled, 3 market rows (15 venue quotes joined, 0 single-venue fallback), OOS Brier=0.2251
exit=0
```

## python3 audit/verify_docs_parity.py
```
PASS    1 no docs page reuses a canonical title and every docs title says 'secondary' :: reused: []; unmarked: []
PASS    2 secondary banner is first in <body> and every page links the canonical hub :: banner not first: []; no canonical link: []
PASS    3 reconciliation + overview numbers reproduce both committed snapshots :: reconcile section: True; missing: []; oos series rendered: 22,432
PASS    4 every scheduled row deep-links to a canonical anchor that exists :: 200 rows; missing link: []; dead anchor: []
PASS    5 fixtures absent from the canonical snapshot are explained, not silently dropped :: unexplained: []
PASS    6 canonical probabilities rendered in docs/ equal data/matches.json :: mismatched: []
PASS    7 divergences (>= 5 pp or opposite pick) are marked and listed :: 31 divergent fixtures; unmarked rows: []; missing from overview ledger: []
PASS    8 no series format is rendered that Hotspawn does not publish :: 200 rows have best_of=null in the feed; bad renders: []
PASS    9 internal links and fragments resolve (including ../ into the root site) :: broken: []
PASS   10 methodology documents the canonical relationship and the unpublished series format :: missing: []
WARN      canonical cards missing from the secondary snapshot :: 35

scheduled rows: 200 | shared with canonical: 177 | both priced: 170 | divergent: 31 | mean gap 2.482 pp | max gap 9.76 pp

ALL DOCS-PARITY CHECKS PASS
exit=0
```
