# refresh-docs verification output

run 41554796930 attempt 1 · commit `d3ffea646e7a0b4d2c48461c115f65bf91f70f7e` · 2026-11-03T00:43:15Z

## freshly generated snapshot
```
generated_at 2026-11-03T00:43:15.268Z | raw feed 2026-11-03T00:43:06.312Z
counts {"total_rows":517,"scheduled_total":179,"active_open_locked":88,"stale_scheduled":91,"ended_recent":285,"forfeited_recent":12,"cancelled_recent":41,"active_market":4,"active_model":84,"active_unresolved":0,"scheduled_market":4,"scheduled_model":168,"scheduled_walkover_settlement":4,"scheduled_unresolved":3,"by_source_scheduled":{"model":117,"walkover_settlement":4,"model_provisional":51,"unresolved":3,"market_consensus":4},"by_source_active":{"model":68,"model_provisional":16,"market_consensus":4},"flags":12}
calibration {"n":22465,"brier":0.2251,"series":32646}
rows 517 | scheduled 179
market rows: 1129387:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Smarkets (UKGC)] 1094919:4[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC] 1094917:4[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC] 1075825:4[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC]
scheduled rows with best_of != null: 0
flags 12 | dq-walkover-1071170 unverified-zero-history-1074627 dq-walkover-1071200 dq-walkover-1071206 dq-walkover-1071186 unverified-zero-history-1082002 unverified-zero-history-1083593 entity-collision-1082746 entity-collision-1079053 entity-collision-1079057 org-pooling-rich-gang-prm3 series-format-not-published
```

## git diff --stat of this run's output
```
 data/node/raw/bovada_lol.json              |    2 +-
 data/node/raw/collect_log.json             |   30 +-
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
 docs/data/picks.json                       | 1567 +++++++++++++++-------------
 docs/featured.html                         |   78 +-
 docs/flagged.html                          |    8 +-
 docs/index.html                            |   82 +-
 docs/methodology.html                      |   20 +-
 docs/originated.html                       |  273 ++++-
 docs/picks.html                            |  348 ++++--
 docs/results.html                          |   76 +-
 docs/table.html                            |  157 ++-
 docs/tournaments.html                      |  106 +-
 docs/unresolved.html                       |    6 +-
 32 files changed, 2843 insertions(+), 2116 deletions(-)
```

## python3 audit/verify_docs.py
```
PASS    1 docs/data/picks.json mirrors data/node/picks.json :: 1253926 bytes
PASS    2 every active match with a pick rendered on picks.html :: 88 picked rows, missing: []
PASS    3 rendered probabilities match JSON :: bad: []
PASS    4 every active match without a pick is on unresolved.html and index.html :: 0 unresolved, missing: []
PASS    5 every rendered card links its Hotspawn match card :: missing: []
PASS    6 market rows carry all matched venue source links :: 4 market rows, missing: []
PASS    7 results.html renders only official scores (no fabricated fills) :: 297 ended/forfeited checked, bad: []
PASS    8 no ledger entry with an official result renders as pending :: bad: []
PASS    9 navigation on every docs page :: []
PASS  9.1 exec summary links every picks view & subpage :: []
PASS   10 no broken internal links or fragments in docs/ :: []
PASS   11 probabilities sum to 100% and pick = argmax :: bad: []
PASS   12 all scheduled matches rendered 1:1 on docs/table.html with source links :: 179 scheduled rows, missing: []
PASS   13 all 10 docs/*.html category pages exist with mobile viewport :: missing=[] no_vp=[]
PASS   14 no '(Kills)' derivative market used as a match line :: []
PASS   15 cross-region homonym quarantines (#1083097, #1079031) & Solid Gaming DQ walkovers verified :: []
PASS   16 every Flagged for Review item renders with Hotspawn + official source links :: 12 flags, bad=[]

rows: 517 total | scheduled 179 | active 88 (88 with pick, 0 unresolved) | ended/forfeited 297 | flags 12 | ledger 315 entries

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
PASS session_6669f798 test_node_pipeline.mjs: 179 scheduled, 4 market rows (17 venue quotes joined, 0 single-venue fallback), OOS Brier=0.2251
exit=0
```

## python3 audit/verify_docs_parity.py
```
PASS    1 no docs page reuses a canonical title and every docs title says 'secondary' :: reused: []; unmarked: []
PASS    2 secondary banner is first in <body> and every page links the canonical hub :: banner not first: []; no canonical link: []
PASS    3 reconciliation + overview numbers reproduce both committed snapshots :: reconcile section: True; missing: []; oos series rendered: 22,465
PASS    4 every scheduled row deep-links to a canonical anchor that exists :: 179 rows; missing link: []; dead anchor: []
PASS    5 fixtures absent from the canonical snapshot are explained, not silently dropped :: unexplained: []
PASS    6 canonical probabilities rendered in docs/ equal data/matches.json :: mismatched: []
PASS    7 divergences (>= 5 pp or opposite pick) are marked and listed :: 28 divergent fixtures; unmarked rows: []; missing from overview ledger: []
PASS    8 no series format is rendered that Hotspawn does not publish :: 179 rows have best_of=null in the feed; bad renders: []
PASS    9 internal links and fragments resolve (including ../ into the root site) :: broken: []
PASS   10 methodology documents the canonical relationship and the unpublished series format :: missing: []
WARN      canonical cards missing from the secondary snapshot :: 53

scheduled rows: 179 | shared with canonical: 159 | both priced: 152 | divergent: 28 | mean gap 2.566 pp | max gap 9.76 pp

ALL DOCS-PARITY CHECKS PASS
exit=0
```
