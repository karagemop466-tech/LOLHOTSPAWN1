# refresh-docs verification output

run 40208369271 attempt 1 · commit `0ee7fd0f3edca4e4ba138f6ee283957e3bbe00e2` · 2026-10-25T15:44:52Z

## freshly generated snapshot
```
generated_at 2026-10-25T15:44:51.608Z | raw feed 2026-10-25T15:44:40.183Z
counts {"total_rows":570,"scheduled_total":234,"active_open_locked":157,"stale_scheduled":77,"ended_recent":263,"forfeited_recent":26,"cancelled_recent":47,"active_market":9,"active_model":148,"active_unresolved":0,"scheduled_market":9,"scheduled_model":218,"scheduled_walkover_settlement":4,"scheduled_unresolved":3,"by_source_scheduled":{"model":147,"walkover_settlement":4,"model_provisional":71,"unresolved":3,"market_consensus":9},"by_source_active":{"model":107,"model_provisional":41,"market_consensus":9},"flags":15}
calibration {"n":22395,"brier":0.225,"series":32559}
rows 570 | scheduled 234
market rows: 1075817:6[Pinnacle+Unibet (Kambi)+Polymarket+Smarkets (UKGC)+Kalshi CFTC+Bovada] 1075816:6[Pinnacle+Unibet (Kambi)+Polymarket+Smarkets (UKGC)+Kalshi CFTC+Bovada] 1075819:6[Pinnacle+Unibet (Kambi)+Polymarket+Smarkets (UKGC)+Kalshi CFTC+Bovada] 1075818:6[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Bovada+Smarkets (UKGC)] 1075821:6[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Bovada+Smarkets (UKGC)] 1075820:6[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Bovada+Smarkets (UKGC)] 1075822:6[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Bovada+Smarkets (UKGC)] 1075823:6[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Bovada+Smarkets (UKGC)] 1079080:2[Polymarket+Kalshi CFTC]
scheduled rows with best_of != null: 0
flags 15 | dq-walkover-1071170 unverified-zero-history-1074627 dq-walkover-1071200 dq-walkover-1071206 dq-walkover-1071186 unverified-zero-history-1082002 unverified-zero-history-1083593 venue-divergence-1075817 entity-collision-1079031 entity-collision-1079038 entity-collision-1082746 entity-collision-1079053 entity-collision-1079057 org-pooling-rich-gang-prm3 series-format-not-published
```

## git diff --stat of this run's output
```
 data/node/picks.json                       | 998 ++++++++---------------------
 data/node/raw/collect_log.json             |  24 +-
 data/node/raw/hotspawn_lobby_check.json    |   2 +-
 data/node/raw/hotspawn_lol_fixtures.json   |   2 +-
 data/node/raw/kalshi_lol.json              |   2 +-
 data/node/raw/kambi_lol.json               |   2 +-
 data/node/raw/pinnacle_lol.json            |   2 +-
 data/node/raw/pinnacle_matchups_cache.json |   2 +-
 data/node/raw/polymarket_lol.json          |   2 +-
 data/node/raw/smarkets_lol.json            |   2 +-
 docs/data/canonical_snapshot.json          |   2 +-
 docs/data/flags.json                       |   2 +-
 docs/data/picks.csv                        |   8 +-
 docs/data/picks.json                       | 998 ++++++++---------------------
 docs/featured.html                         |  58 +-
 docs/flagged.html                          |   4 +-
 docs/index.html                            |  42 +-
 docs/methodology.html                      |  34 +-
 docs/originated.html                       |   4 +-
 docs/picks.html                            |  36 +-
 docs/results.html                          |  50 +-
 docs/table.html                            |  28 +-
 docs/tournaments.html                      |  12 +-
 docs/unresolved.html                       |   4 +-
 31 files changed, 1144 insertions(+), 2157 deletions(-)
```

## python3 audit/verify_docs.py
```
PASS    1 docs/data/picks.json mirrors data/node/picks.json :: 1421612 bytes
PASS    2 every active match with a pick rendered on picks.html :: 157 picked rows, missing: []
PASS    3 rendered probabilities match JSON :: bad: []
PASS    4 every active match without a pick is on unresolved.html and index.html :: 0 unresolved, missing: []
PASS    5 every rendered card links its Hotspawn match card :: missing: []
PASS    6 market rows carry all matched venue source links :: 9 market rows, missing: []
PASS    7 results.html renders only official scores (no fabricated fills) :: 289 ended/forfeited checked, bad: []
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

rows: 570 total | scheduled 234 | active 157 (157 with pick, 0 unresolved) | ended/forfeited 289 | flags 15 | ledger 271 entries

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
PASS session_6669f798 test_node_pipeline.mjs: 234 scheduled, 9 market rows (50 venue quotes joined, 0 single-venue fallback), OOS Brier=0.225
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

scheduled rows: 234 | shared with canonical: 234 | both priced: 227 | divergent: 33 | mean gap 2.202 pp | max gap 11.81 pp

ALL DOCS-PARITY CHECKS PASS
exit=0
```
