# refresh-docs verification output

run 40186836305 attempt 1 · commit `5d8ec7c586afc6430af09136e53ff944f3130421` · 2026-10-25T10:57:12Z

## freshly generated snapshot
```
generated_at 2026-10-25T10:57:11.482Z | raw feed 2026-10-25T10:57:04.753Z
counts {"total_rows":575,"scheduled_total":236,"active_open_locked":156,"stale_scheduled":80,"ended_recent":266,"forfeited_recent":26,"cancelled_recent":47,"active_market":9,"active_model":147,"active_unresolved":0,"scheduled_market":9,"scheduled_model":220,"scheduled_walkover_settlement":4,"scheduled_unresolved":3,"by_source_scheduled":{"model":147,"walkover_settlement":4,"model_provisional":73,"unresolved":3,"market_consensus":9},"by_source_active":{"model_provisional":42,"model":105,"market_consensus":9},"flags":14}
calibration {"n":22386,"brier":0.225,"series":32550}
rows 575 | scheduled 236
market rows: 1075816:4[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC] 1075817:4[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC] 1075818:4[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC] 1075819:4[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC] 1075820:4[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC] 1075821:4[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC] 1075822:4[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC] 1075823:4[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC] 1079080:2[Polymarket+Kalshi CFTC]
scheduled rows with best_of != null: 0
flags 14 | dq-walkover-1071170 unverified-zero-history-1074627 dq-walkover-1071200 dq-walkover-1071206 dq-walkover-1071186 unverified-zero-history-1082002 unverified-zero-history-1083593 entity-collision-1079031 entity-collision-1079038 entity-collision-1082746 entity-collision-1079053 entity-collision-1079057 org-pooling-rich-gang-prm3 series-format-not-published
```

## git diff --stat of this run's output
```
 data/node/picks.csv                        |   14 +-
 data/node/picks.json                       | 3628 +++++++++++++++++++++-------
 data/node/raw/bovada_lol.json              |    2 +-
 data/node/raw/collect_log.json             |   36 +-
 data/node/raw/hotspawn_lobby_check.json    |    2 +-
 data/node/raw/hotspawn_lol_fixtures.json   |    2 +-
 data/node/raw/kalshi_lol.json              |    2 +-
 data/node/raw/kambi_lol.json               |    2 +-
 data/node/raw/pinnacle_lol.json            |    2 +-
 data/node/raw/pinnacle_matchups_cache.json |    2 +-
 data/node/raw/polymarket_lol.json          |    2 +-
 docs/data/flags.json                       |    4 +-
 docs/data/picks.csv                        |   14 +-
 docs/data/picks.json                       | 3628 +++++++++++++++++++++-------
 docs/featured.html                         |  358 ++-
 docs/flagged.html                          |    8 +-
 docs/index.html                            |  302 ++-
 docs/methodology.html                      |   28 +-
 docs/originated.html                       |   78 +-
 docs/picks.html                            |  422 ++--
 docs/results.html                          |  138 +-
 docs/table.html                            |  160 +-
 docs/tournaments.html                      |  114 +-
 docs/unresolved.html                       |    8 +-
 30 files changed, 7292 insertions(+), 2622 deletions(-)
```

## python3 audit/verify_docs.py
```
PASS    1 docs/data/picks.json mirrors data/node/picks.json :: 1392595 bytes
PASS    2 every active match with a pick rendered on picks.html :: 156 picked rows, missing: []
PASS    3 rendered probabilities match JSON :: bad: []
PASS    4 every active match without a pick is on unresolved.html and index.html :: 0 unresolved, missing: []
PASS    5 every rendered card links its Hotspawn match card :: missing: []
PASS    6 market rows carry all matched venue source links :: 9 market rows, missing: []
PASS    7 results.html renders only official scores (no fabricated fills) :: 292 ended/forfeited checked, bad: []
PASS    8 no ledger entry with an official result renders as pending :: bad: []
PASS    9 navigation on every docs page :: []
PASS  9.1 exec summary links every picks view & subpage :: []
PASS   10 no broken internal links or fragments in docs/ :: []
PASS   11 probabilities sum to 100% and pick = argmax :: bad: []
PASS   12 all scheduled matches rendered 1:1 on docs/table.html with source links :: 236 scheduled rows, missing: []
PASS   13 all 10 docs/*.html category pages exist with mobile viewport :: missing=[] no_vp=[]
PASS   14 no '(Kills)' derivative market used as a match line :: []
PASS   15 cross-region homonym quarantines (#1083097, #1079031) & Solid Gaming DQ walkovers verified :: []
PASS   16 every Flagged for Review item renders with Hotspawn + official source links :: 14 flags, bad=[]

rows: 575 total | scheduled 236 | active 156 (156 with pick, 0 unresolved) | ended/forfeited 292 | flags 14 | ledger 270 entries

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
PASS session_6669f798 test_node_pipeline.mjs: 236 scheduled, 9 market rows (34 venue quotes joined, 0 single-venue fallback), OOS Brier=0.225
exit=0
```

## python3 audit/verify_docs_parity.py
```
PASS    1 no docs page reuses a canonical title and every docs title says 'secondary' :: reused: []; unmarked: []
PASS    2 secondary banner is first in <body> and every page links the canonical hub :: banner not first: []; no canonical link: []
PASS    3 reconciliation + overview numbers reproduce both committed snapshots :: reconcile section: True; missing: []; oos series rendered: 22,386
PASS    4 every scheduled row deep-links to a canonical anchor that exists :: 236 rows; missing link: []; dead anchor: []
PASS    5 fixtures absent from the canonical snapshot are explained, not silently dropped :: unexplained: []
PASS    6 canonical probabilities rendered in docs/ equal data/matches.json :: mismatched: []
PASS    7 divergences (>= 5 pp or opposite pick) are marked and listed :: 29 divergent fixtures; unmarked rows: []; missing from overview ledger: []
PASS    8 no series format is rendered that Hotspawn does not publish :: 236 rows have best_of=null in the feed; bad renders: []
PASS    9 internal links and fragments resolve (including ../ into the root site) :: broken: []
PASS   10 methodology documents the canonical relationship and the unpublished series format :: missing: []
WARN      canonical cards missing from the secondary snapshot :: 17

scheduled rows: 236 | shared with canonical: 224 | both priced: 217 | divergent: 29 | mean gap 2.223 pp | max gap 18.89 pp

ALL DOCS-PARITY CHECKS PASS
exit=0
```
