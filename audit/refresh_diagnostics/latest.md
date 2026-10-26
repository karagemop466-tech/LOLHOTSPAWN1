# refresh-docs verification output

run 40265845604 attempt 1 · commit `31ab765ce86014e31ebb98d8ce13863cbaad1677` · 2026-10-26T03:48:29Z

## freshly generated snapshot
```
generated_at 2026-10-26T03:48:28.992Z | raw feed 2026-10-26T03:48:21.270Z
counts {"total_rows":544,"scheduled_total":222,"active_open_locked":131,"stale_scheduled":91,"ended_recent":253,"forfeited_recent":23,"cancelled_recent":45,"active_market":5,"active_model":126,"active_unresolved":0,"scheduled_market":5,"scheduled_model":210,"scheduled_walkover_settlement":4,"scheduled_unresolved":3,"by_source_scheduled":{"model":153,"walkover_settlement":4,"model_provisional":57,"unresolved":3,"market_consensus":5},"by_source_active":{"market_consensus":5,"model":102,"model_provisional":24},"flags":14}
calibration {"n":22418,"brier":0.225,"series":32582}
rows 544 | scheduled 222
market rows: 1075821:6[Pinnacle+Unibet (Kambi)+Polymarket+Smarkets (UKGC)+Kalshi CFTC+Bovada] 1075820:6[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Bovada+Smarkets (UKGC)] 1075822:6[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Bovada+Smarkets (UKGC)] 1075823:6[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Bovada+Smarkets (UKGC)] 1079080:2[Polymarket+Kalshi CFTC]
scheduled rows with best_of != null: 0
flags 14 | dq-walkover-1071170 unverified-zero-history-1074627 dq-walkover-1071200 dq-walkover-1071206 dq-walkover-1071186 unverified-zero-history-1082002 unverified-zero-history-1083593 entity-collision-1079031 entity-collision-1079038 entity-collision-1082746 entity-collision-1079053 entity-collision-1079057 org-pooling-rich-gang-prm3 series-format-not-published
```

## git diff --stat of this run's output
```
 data/node/raw/bovada_lol.json              |     2 +-
 data/node/raw/collect_log.json             |    52 +-
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
 docs/data/picks.csv                        |   135 +-
 docs/data/picks.json                       | 29052 +++++++++++++--------------
 docs/featured.html                         |   274 +-
 docs/flagged.html                          |    21 +-
 docs/index.html                            |   334 +-
 docs/methodology.html                      |    40 +-
 docs/originated.html                       |   909 +-
 docs/picks.html                            |  1496 +-
 docs/results.html                          |   379 +-
 docs/table.html                            |   567 +-
 docs/tournaments.html                      |   300 +-
 docs/unresolved.html                       |     6 +-
 32 files changed, 30514 insertions(+), 34014 deletions(-)
```

## python3 audit/verify_docs.py
```
PASS    1 docs/data/picks.json mirrors data/node/picks.json :: 1327837 bytes
PASS    2 every active match with a pick rendered on picks.html :: 132 picked rows, missing: []
PASS    3 rendered probabilities match JSON :: bad: []
PASS    4 every active match without a pick is on unresolved.html and index.html :: 0 unresolved, missing: []
PASS    5 every rendered card links its Hotspawn match card :: missing: []
PASS    6 market rows carry all matched venue source links :: 5 market rows, missing: []
PASS    7 results.html renders only official scores (no fabricated fills) :: 276 ended/forfeited checked, bad: []
PASS    8 no ledger entry with an official result renders as pending :: bad: []
PASS    9 navigation on every docs page :: []
PASS  9.1 exec summary links every picks view & subpage :: []
PASS   10 no broken internal links or fragments in docs/ :: []
PASS   11 probabilities sum to 100% and pick = argmax :: bad: []
PASS   12 all scheduled matches rendered 1:1 on docs/table.html with source links :: 222 scheduled rows, missing: []
PASS   13 all 10 docs/*.html category pages exist with mobile viewport :: missing=[] no_vp=[]
PASS   14 no '(Kills)' derivative market used as a match line :: []
PASS   15 cross-region homonym quarantines (#1083097, #1079031) & Solid Gaming DQ walkovers verified :: []
PASS   16 every Flagged for Review item renders with Hotspawn + official source links :: 14 flags, bad=[]

rows: 544 total | scheduled 222 | active 132 (132 with pick, 0 unresolved) | ended/forfeited 276 | flags 14 | ledger 273 entries

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
PASS session_6669f798 test_node_pipeline.mjs: 222 scheduled, 5 market rows (26 venue quotes joined, 0 single-venue fallback), OOS Brier=0.225
exit=0
```

## python3 audit/verify_docs_parity.py
```
PASS    1 no docs page reuses a canonical title and every docs title says 'secondary' :: reused: []; unmarked: []
PASS    2 secondary banner is first in <body> and every page links the canonical hub :: banner not first: []; no canonical link: []
PASS    3 reconciliation + overview numbers reproduce both committed snapshots :: reconcile section: True; missing: []; oos series rendered: 22,418
PASS    4 every scheduled row deep-links to a canonical anchor that exists :: 222 rows; missing link: []; dead anchor: []
PASS    5 fixtures absent from the canonical snapshot are explained, not silently dropped :: unexplained: []
PASS    6 canonical probabilities rendered in docs/ equal data/matches.json :: mismatched: []
PASS    7 divergences (>= 5 pp or opposite pick) are marked and listed :: 32 divergent fixtures; unmarked rows: []; missing from overview ledger: []
PASS    8 no series format is rendered that Hotspawn does not publish :: 222 rows have best_of=null in the feed; bad renders: []
PASS    9 internal links and fragments resolve (including ../ into the root site) :: broken: []
PASS   10 methodology documents the canonical relationship and the unpublished series format :: missing: []
WARN      canonical cards missing from the secondary snapshot :: 13

scheduled rows: 222 | shared with canonical: 220 | both priced: 213 | divergent: 32 | mean gap 2.308 pp | max gap 11.81 pp

ALL DOCS-PARITY CHECKS PASS
exit=0
```
