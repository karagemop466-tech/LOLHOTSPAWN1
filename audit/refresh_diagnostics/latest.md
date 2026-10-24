# refresh-docs verification output

run local (offline rehearsal) · commit `e9154a5c767296732fa639407b042aaa629731c9` · 2026-10-24T18:43:44Z

## freshly generated snapshot
```
generated_at 2026-10-24T18:29:16.968Z | raw feed 2026-10-24T16:49:38.078Z
counts {"total_rows":566,"scheduled_total":241,"active_open_locked":172,"stale_scheduled":69,"ended_recent":247,"forfeited_recent":32,"cancelled_recent":46,"active_market":9,"active_model":163,"active_unresolved":0,"scheduled_market":9,"scheduled_model":222,"scheduled_walkover_settlement":4,"scheduled_unresolved":6,"by_source_scheduled":{"model":149,"walkover_settlement":4,"model_provisional":73,"unresolved":6,"market_consensus":9},"by_source_active":{"model":115,"model_provisional":48,"market_consensus":9},"flags":18}
calibration {"n":22344,"brier":0.2251,"series":32509}
rows 566 | scheduled 241
market rows: 1067688:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Bovada] 1067881:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Bovada] 1067686:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Bovada] 1067684:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Bovada] 1067687:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Bovada] 1067683:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Bovada] 1067880:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Bovada] 1067689:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Bovada] 1079080:2[Polymarket+Kalshi CFTC]
scheduled rows with best_of != null: 0
flags 18 | dq-walkover-1071170 unverified-zero-history-1074627 dq-walkover-1071200 dq-walkover-1071206 dq-walkover-1071186 unverified-zero-history-1082002 unverified-zero-history-1083096 entity-collision-1083097 unverified-zero-history-1083097 unverified-zero-history-1083098 unverified-zero-history-1083105 entity-collision-1079031 entity-collision-1079038 entity-collision-1082746 entity-collision-1079053 entity-collision-1079057 org-pooling-rich-gang-prm3 series-format-not-published
```

## git diff --stat of this run's output
```
 .github/workflows/refresh-docs.yml | 74 ++++++++++++++++++++++++++++++++++++--
 1 file changed, 71 insertions(+), 3 deletions(-)
```

## python3 audit/verify_docs.py
```
PASS    1 docs/data/picks.json mirrors data/node/picks.json :: 1384884 bytes
PASS    2 every active match with a pick rendered on picks.html :: 172 picked rows, missing: []
PASS    3 rendered probabilities match JSON :: bad: []
PASS    4 every active match without a pick is on unresolved.html and index.html :: 0 unresolved, missing: []
PASS    5 every rendered card links its Hotspawn match card :: missing: []
PASS    6 market rows carry all matched venue source links :: 9 market rows, missing: []
PASS    7 results.html renders only official scores (no fabricated fills) :: 279 ended/forfeited checked, bad: []
PASS    8 no ledger entry with an official result renders as pending :: bad: []
PASS    9 navigation on every docs page :: []
PASS  9.1 exec summary links every picks view & subpage :: []
PASS   10 no broken internal links or fragments in docs/ :: []
PASS   11 probabilities sum to 100% and pick = argmax :: bad: []
PASS   12 all scheduled matches rendered 1:1 on docs/table.html with source links :: 241 scheduled rows, missing: []
PASS   13 all 10 docs/*.html category pages exist with mobile viewport :: missing=[] no_vp=[]
PASS   14 no '(Kills)' derivative market used as a match line :: []
PASS   15 cross-region homonym quarantines (#1083097, #1079031) & Solid Gaming DQ walkovers verified :: []
PASS   16 every Flagged for Review item renders with Hotspawn + official source links :: 18 flags, bad=[]

rows: 566 total | scheduled 241 | active 172 (172 with pick, 0 unresolved) | ended/forfeited 279 | flags 18 | ledger 259 entries

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
PASS session_6669f798 test_node_pipeline.mjs: 241 scheduled, 9 market (42 venue quotes joined), OOS Brier=0.2251
exit=0
```

## python3 audit/verify_docs_parity.py
```
PASS    1 no docs page reuses a canonical title and every docs title says 'secondary' :: reused: []; unmarked: []
PASS    2 secondary banner is first in <body> and every page links the canonical hub :: banner not first: []; no canonical link: []
PASS    3 reconciliation + overview numbers reproduce both committed snapshots :: reconcile section: True; missing: []; oos series rendered: 22,344
PASS    4 every scheduled row deep-links to a canonical anchor that exists :: 241 rows; missing link: []; dead anchor: []
PASS    5 fixtures absent from the canonical snapshot are explained, not silently dropped :: unexplained: []
PASS    6 canonical probabilities rendered in docs/ equal data/matches.json :: mismatched: []
PASS    7 divergences (>= 5 pp or opposite pick) are marked and listed :: 34 divergent fixtures; unmarked rows: []; missing from overview ledger: []
PASS    8 no series format is rendered that Hotspawn does not publish :: 241 rows have best_of=null in the feed; bad renders: []
PASS    9 internal links and fragments resolve (including ../ into the root site) :: broken: []
PASS   10 methodology documents the canonical relationship and the unpublished series format :: missing: []

scheduled rows: 241 | shared with canonical: 241 | both priced: 231 | divergent: 34 | mean gap 2.353 pp | max gap 28.04 pp

ALL DOCS-PARITY CHECKS PASS
exit=0
```
