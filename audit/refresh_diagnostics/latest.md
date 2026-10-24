# refresh-docs verification output

run 40129686965 attempt 1 · commit `ce015bd27abbe94910c9273f50d55c32c69fad6e` · 2026-10-24T20:25:28Z

## freshly generated snapshot
```
generated_at 2026-10-24T20:25:27.802Z | raw feed 2026-10-24T20:25:20.814Z
counts {"total_rows":572,"scheduled_total":241,"active_open_locked":172,"stale_scheduled":69,"ended_recent":256,"forfeited_recent":29,"cancelled_recent":46,"active_market":9,"active_model":163,"active_unresolved":0,"scheduled_market":9,"scheduled_model":225,"scheduled_walkover_settlement":4,"scheduled_unresolved":3,"by_source_scheduled":{"model":149,"walkover_settlement":4,"model_provisional":76,"unresolved":3,"market_bovada":3,"market_consensus":6},"by_source_active":{"model_provisional":49,"model":114,"market_bovada":3,"market_consensus":6},"flags":15}
calibration {"n":22344,"brier":0.2251,"series":32509}
rows 572 | scheduled 241
market rows: 1067688:1[Bovada] 1067881:1[Bovada] 1067686:1[Bovada] 1067684:3[Polymarket+Kalshi CFTC+Bovada] 1067687:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Bovada] 1067683:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Bovada] 1067880:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Bovada] 1067689:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Bovada] 1079080:2[Polymarket+Kalshi CFTC]
scheduled rows with best_of != null: 0
flags 15 | dq-walkover-1071170 unverified-zero-history-1074627 dq-walkover-1071200 dq-walkover-1071206 dq-walkover-1071186 unverified-zero-history-1082002 unverified-zero-history-1083593 venue-divergence-1067684 entity-collision-1079031 entity-collision-1079038 entity-collision-1082746 entity-collision-1079053 entity-collision-1079057 org-pooling-rich-gang-prm3 series-format-not-published
```

## git diff --stat of this run's output
```
 data/node/model/ratings.json               |    2 +-
 data/node/picks.csv                        |   20 +-
 data/node/picks.json                       | 1110 ++++++----------------------
 data/node/raw/collect_log.json             |   36 +-
 data/node/raw/hotspawn_lobby_check.json    |    2 +-
 data/node/raw/hotspawn_lol_fixtures.json   |    2 +-
 data/node/raw/kalshi_lol.json              |    2 +-
 data/node/raw/kambi_lol.json               |    2 +-
 data/node/raw/pinnacle_lol.json            |    2 +-
 data/node/raw/pinnacle_matchups_cache.json |    2 +-
 data/node/raw/polymarket_lol.json          |    2 +-
 docs/data/flags.json                       |   16 +-
 docs/data/picks.csv                        |   20 +-
 docs/data/picks.json                       | 1110 ++++++----------------------
 docs/featured.html                         |   94 +--
 docs/flagged.html                          |   19 +-
 docs/index.html                            |   92 +--
 docs/methodology.html                      |    8 +-
 docs/originated.html                       |   24 +-
 docs/picks.html                            |  175 +----
 docs/results.html                          |   52 +-
 docs/table.html                            |   66 +-
 docs/tournaments.html                      |   40 +-
 docs/unresolved.html                       |    6 +-
 29 files changed, 885 insertions(+), 2461 deletions(-)
```

## python3 audit/verify_docs.py
```
PASS    1 docs/data/picks.json mirrors data/node/picks.json :: 1378812 bytes
PASS    2 every active match with a pick rendered on picks.html :: 172 picked rows, missing: []
PASS    3 rendered probabilities match JSON :: bad: []
PASS    4 every active match without a pick is on unresolved.html and index.html :: 0 unresolved, missing: []
PASS    5 every rendered card links its Hotspawn match card :: missing: []
PASS    6 market rows carry all matched venue source links :: 9 market rows, missing: []
PASS    7 results.html renders only official scores (no fabricated fills) :: 285 ended/forfeited checked, bad: []
PASS    8 no ledger entry with an official result renders as pending :: bad: []
PASS    9 navigation on every docs page :: []
PASS  9.1 exec summary links every picks view & subpage :: []
PASS   10 no broken internal links or fragments in docs/ :: []
PASS   11 probabilities sum to 100% and pick = argmax :: bad: []
PASS   12 all scheduled matches rendered 1:1 on docs/table.html with source links :: 241 scheduled rows, missing: []
PASS   13 all 10 docs/*.html category pages exist with mobile viewport :: missing=[] no_vp=[]
PASS   14 no '(Kills)' derivative market used as a match line :: []
PASS   15 cross-region homonym quarantines (#1083097, #1079031) & Solid Gaming DQ walkovers verified :: []
PASS   16 every Flagged for Review item renders with Hotspawn + official source links :: 15 flags, bad=[]

rows: 572 total | scheduled 241 | active 172 (172 with pick, 0 unresolved) | ended/forfeited 285 | flags 15 | ledger 259 entries

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
note: #1067688 is a single-venue fallback (Bovada, quote 2026-10-24T16:29:32Z, 30 min before kick-off) - no second venue was live once the card locked
note: #1067881 is a single-venue fallback (Bovada, quote 2026-10-24T16:29:32Z, 90 min before kick-off) - no second venue was live once the card locked
note: #1067686 is a single-venue fallback (Bovada, quote 2026-10-24T16:29:32Z, 150 min before kick-off) - no second venue was live once the card locked
note: #1083097 is no longer scheduled — homonym quarantine assertions skipped
PASS session_6669f798 test_node_pipeline.mjs: 241 scheduled, 9 market rows (28 venue quotes joined, 3 single-venue fallback), OOS Brier=0.2251
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
PASS    7 divergences (>= 5 pp or opposite pick) are marked and listed :: 35 divergent fixtures; unmarked rows: []; missing from overview ledger: []
PASS    8 no series format is rendered that Hotspawn does not publish :: 241 rows have best_of=null in the feed; bad renders: []
PASS    9 internal links and fragments resolve (including ../ into the root site) :: broken: []
PASS   10 methodology documents the canonical relationship and the unpublished series format :: missing: []
WARN      canonical cards missing from the secondary snapshot :: 4

scheduled rows: 241 | shared with canonical: 237 | both priced: 231 | divergent: 35 | mean gap 2.434 pp | max gap 30.04 pp

ALL DOCS-PARITY CHECKS PASS
exit=0
```
