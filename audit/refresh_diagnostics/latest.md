# refresh-docs verification output

run 40201363277 attempt 1 · commit `795f0765e57c03f9d85139e27b307499356f0172` · 2026-10-25T14:15:47Z

## freshly generated snapshot
```
generated_at 2026-10-25T14:15:46.475Z | raw feed 2026-10-25T14:15:39.076Z
counts {"total_rows":576,"scheduled_total":234,"active_open_locked":157,"stale_scheduled":77,"ended_recent":269,"forfeited_recent":26,"cancelled_recent":47,"active_market":9,"active_model":148,"active_unresolved":0,"scheduled_market":9,"scheduled_model":218,"scheduled_walkover_settlement":4,"scheduled_unresolved":3,"by_source_scheduled":{"model":147,"walkover_settlement":4,"model_provisional":71,"unresolved":3,"market_consensus":9},"by_source_active":{"model":107,"model_provisional":41,"market_consensus":9},"flags":15}
calibration {"n":22395,"brier":0.225,"series":32559}
rows 576 | scheduled 234
market rows: 1075817:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Bovada] 1075816:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Bovada] 1075819:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Bovada] 1075818:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Bovada] 1075821:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Bovada] 1075820:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Bovada] 1075822:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Bovada] 1075823:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Bovada] 1079080:2[Polymarket+Kalshi CFTC]
scheduled rows with best_of != null: 0
flags 15 | dq-walkover-1071170 unverified-zero-history-1074627 dq-walkover-1071200 dq-walkover-1071206 dq-walkover-1071186 unverified-zero-history-1082002 unverified-zero-history-1083593 venue-divergence-1075817 entity-collision-1079031 entity-collision-1079038 entity-collision-1082746 entity-collision-1079053 entity-collision-1079057 org-pooling-rich-gang-prm3 series-format-not-published
```

## git diff --stat of this run's output
```
 data/node/picks.csv                        |   86 +-
 data/node/picks.json                       | 3601 ++++++++++++++++------------
 data/node/raw/bovada_lol.json              |    2 +-
 data/node/raw/collect_log.json             |   32 +-
 data/node/raw/hotspawn_lobby_check.json    |    2 +-
 data/node/raw/hotspawn_lol_fixtures.json   |    2 +-
 data/node/raw/kalshi_lol.json              |    2 +-
 data/node/raw/kambi_lol.json               |    2 +-
 data/node/raw/pinnacle_lol.json            |    2 +-
 data/node/raw/pinnacle_matchups_cache.json |    2 +-
 data/node/raw/polymarket_lol.json          |    2 +-
 docs/data/flags.json                       |   18 +-
 docs/data/picks.csv                        |   86 +-
 docs/data/picks.json                       | 3601 ++++++++++++++++------------
 docs/featured.html                         |  306 +--
 docs/flagged.html                          |   23 +-
 docs/index.html                            |  362 ++-
 docs/methodology.html                      |   58 +-
 docs/originated.html                       |  736 +++---
 docs/picks.html                            |  837 +++----
 docs/results.html                          |  135 +-
 docs/table.html                            |  454 ++--
 docs/tournaments.html                      |  242 +-
 docs/unresolved.html                       |    8 +-
 30 files changed, 6550 insertions(+), 5777 deletions(-)
```

## python3 audit/verify_docs.py
```
PASS    1 docs/data/picks.json mirrors data/node/picks.json :: 1405906 bytes
PASS    2 every active match with a pick rendered on picks.html :: 157 picked rows, missing: []
PASS    3 rendered probabilities match JSON :: bad: []
PASS    4 every active match without a pick is on unresolved.html and index.html :: 0 unresolved, missing: []
PASS    5 every rendered card links its Hotspawn match card :: missing: []
PASS    6 market rows carry all matched venue source links :: 9 market rows, missing: []
PASS    7 results.html renders only official scores (no fabricated fills) :: 295 ended/forfeited checked, bad: []
PASS    8 no ledger entry with an official result renders as pending :: bad: []
PASS    9 navigation on every docs page :: []
PASS  9.1 exec summary links every picks view & subpage :: []
PASS   10 no broken internal links or fragments in docs/ :: []
PASS   11 probabilities sum to 100% and pick = argmax :: bad: []
PASS   12 all scheduled matches rendered 1:1 on docs/table.html with source links :: 234 scheduled rows, missing: []
PASS   13 all 10 docs/*.html category pages exist with mobile viewport :: missing=[] no_vp=[]
PASS   14 no '(Kills)' derivative market used as a match line :: []
PASS   15 cross-region homonym quarantines (#1083097, #1079031) & Solid Gaming DQ walkovers verified :: []
PASS   16 every Flagged for Review item renders with Hotspawn + official source links :: 15 flags, bad=[]

rows: 576 total | scheduled 234 | active 157 (157 with pick, 0 unresolved) | ended/forfeited 295 | flags 15 | ledger 271 entries

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
note: #1083097 is no longer scheduled — homonym quarantine assertions skipped
PASS session_6669f798 test_node_pipeline.mjs: 234 scheduled, 9 market rows (42 venue quotes joined, 0 single-venue fallback), OOS Brier=0.225
exit=0
```

## python3 audit/verify_docs_parity.py
```
PASS    1 no docs page reuses a canonical title and every docs title says 'secondary' :: reused: []; unmarked: []
PASS    2 secondary banner is first in <body> and every page links the canonical hub :: banner not first: []; no canonical link: []
PASS    3 reconciliation + overview numbers reproduce both committed snapshots :: reconcile section: True; missing: []; oos series rendered: 22,395
PASS    4 every scheduled row deep-links to a canonical anchor that exists :: 234 rows; missing link: []; dead anchor: []
PASS    5 fixtures absent from the canonical snapshot are explained, not silently dropped :: unexplained: []
PASS    6 canonical probabilities rendered in docs/ equal data/matches.json :: mismatched: []
PASS    7 divergences (>= 5 pp or opposite pick) are marked and listed :: 33 divergent fixtures; unmarked rows: []; missing from overview ledger: []
PASS    8 no series format is rendered that Hotspawn does not publish :: 234 rows have best_of=null in the feed; bad renders: []
PASS    9 internal links and fragments resolve (including ../ into the root site) :: broken: []
PASS   10 methodology documents the canonical relationship and the unpublished series format :: missing: []

scheduled rows: 234 | shared with canonical: 234 | both priced: 227 | divergent: 33 | mean gap 2.255 pp | max gap 18.89 pp

ALL DOCS-PARITY CHECKS PASS
exit=0
```
