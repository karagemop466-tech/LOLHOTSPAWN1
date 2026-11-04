# refresh-docs verification output

run 41933100672 attempt 1 · commit `1c21499101aaaf233c25620910827cc84a480ca0` · 2026-11-04T23:22:03Z

## freshly generated snapshot
```
generated_at 2026-11-04T23:22:03.329Z | raw feed 2026-11-04T23:21:56.094Z
counts {"total_rows":536,"scheduled_total":192,"active_open_locked":102,"stale_scheduled":90,"ended_recent":288,"forfeited_recent":12,"cancelled_recent":44,"active_market":3,"active_model":79,"active_unresolved":20,"scheduled_market":3,"scheduled_model":162,"scheduled_walkover_settlement":4,"scheduled_unresolved":23,"by_source_scheduled":{"model":114,"walkover_settlement":4,"model_provisional":48,"unresolved":23,"market_consensus":3},"by_source_active":{"model":66,"unresolved":20,"market_consensus":3,"model_provisional":13},"flags":31}
calibration {"n":22476,"brier":0.2252,"series":32658}
rows 536 | scheduled 192
market rows: 1094919:2[Polymarket+Kalshi CFTC] 1094917:4[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC] 1075825:4[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC]
scheduled rows with best_of != null: 0
flags 31 | dq-walkover-1071170 unverified-zero-history-1074627 dq-walkover-1071200 dq-walkover-1071206 dq-walkover-1071186 unverified-zero-history-1082002 unverified-zero-history-1083593 unverified-zero-history-1130159 unverified-zero-history-1083141 unverified-zero-history-1083142 unverified-zero-history-1083143 unverified-zero-history-1083144 entity-collision-1079053 unverified-zero-history-1130130 unverified-zero-history-1130131 unverified-zero-history-1130132 unverified-zero-history-1130133 unverified-zero-history-1130134 unverified-zero-history-1130135 unverified-zero-history-1130136 unverified-zero-history-1130137 unverified-zero-history-1130138 unverified-zero-history-1130139 unverified-zero-history-1130140 unverified-zero-history-1130141 unverified-zero-history-1130142 entity-collision-1079057 unverified-zero-history-1130143 unverified-zero-history-1130144 org-pooling-rich-gang-prm3 series-format-not-published
```

## git diff --stat of this run's output
```
 data/node/raw/bovada_lol.json              |    2 +-
 data/node/raw/collect_log.json             |   42 +-
 data/node/raw/hotspawn_lobby_check.json    |    2 +-
 data/node/raw/hotspawn_lol_fixtures.json   |    2 +-
 data/node/raw/kalshi_lol.json              |    2 +-
 data/node/raw/kambi_lol.json               |    2 +-
 data/node/raw/pinnacle_lol.json            |    2 +-
 data/node/raw/pinnacle_matchups_cache.json |    2 +-
 data/node/raw/polymarket_lol.json          |    2 +-
 data/node/raw/smarkets_lol.json            |    2 +-
 docs/data/canonical_snapshot.json          |    2 +-
 docs/data/flags.json                       |    6 +-
 docs/data/picks.csv                        |   14 +-
 docs/data/picks.json                       | 2719 +++++++++++++---------------
 docs/featured.html                         |   62 +-
 docs/flagged.html                          |   10 +-
 docs/index.html                            |   66 +-
 docs/methodology.html                      |   10 +-
 docs/originated.html                       |   88 +-
 docs/picks.html                            |  151 +-
 docs/results.html                          |  194 +-
 docs/table.html                            |   76 +-
 docs/tournaments.html                      |  103 +-
 docs/unresolved.html                       |    8 +-
 32 files changed, 3214 insertions(+), 3424 deletions(-)
```

## python3 audit/verify_docs.py
```
PASS    1 docs/data/picks.json mirrors data/node/picks.json :: 1277026 bytes
PASS    2 every active match with a pick rendered on picks.html :: 82 picked rows, missing: []
PASS    3 rendered probabilities match JSON :: bad: []
PASS    4 every active match without a pick is on unresolved.html and index.html :: 20 unresolved, missing: []
PASS    5 every rendered card links its Hotspawn match card :: missing: []
PASS    6 market rows carry all matched venue source links :: 3 market rows, missing: []
PASS    7 results.html renders only official scores (no fabricated fills) :: 300 ended/forfeited checked, bad: []
PASS    8 no ledger entry with an official result renders as pending :: bad: []
PASS    9 navigation on every docs page :: []
PASS  9.1 exec summary links every picks view & subpage :: []
PASS   10 no broken internal links or fragments in docs/ :: []
PASS   11 probabilities sum to 100% and pick = argmax :: bad: []
PASS   12 all scheduled matches rendered 1:1 on docs/table.html with source links :: 192 scheduled rows, missing: []
PASS   13 all 10 docs/*.html category pages exist with mobile viewport :: missing=[] no_vp=[]
PASS   14 no '(Kills)' derivative market used as a match line :: []
PASS   15 cross-region homonym quarantines (#1083097, #1079031) & Solid Gaming DQ walkovers verified :: []
PASS   16 every Flagged for Review item renders with Hotspawn + official source links :: 31 flags, bad=[]

rows: 536 total | scheduled 192 | active 102 (82 with pick, 20 unresolved) | ended/forfeited 300 | flags 31 | ledger 323 entries

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
WARNING: 1 market row(s) are priced from quotes observed after kick-off (in-play): 1094919(23:21Z vs kick-off 22:00Z) - disclosed on the pages, logged for the pipeline owner
note: #1079080 is no longer scheduled (kicked off or settled) — its Kalshi + Polymarket pair assertions are skipped
note: #1083097 is no longer scheduled — homonym quarantine assertions skipped
note: #1079031 is no longer scheduled — Swiss PvB homonym assertions skipped
PASS session_6669f798 test_node_pipeline.mjs: 192 scheduled, 3 market rows (10 venue quotes joined, 0 single-venue fallback), OOS Brier=0.2252
exit=0
```

## python3 audit/verify_docs_parity.py
```
PASS    1 no docs page reuses a canonical title and every docs title says 'secondary' :: reused: []; unmarked: []
PASS    2 secondary banner is first in <body> and every page links the canonical hub :: banner not first: []; no canonical link: []
PASS    3 reconciliation + overview numbers reproduce both committed snapshots :: reconcile section: True; missing: []; oos series rendered: 22,476
PASS    4 every scheduled row deep-links to a canonical anchor that exists :: 192 rows; missing link: []; dead anchor: []
PASS    5 fixtures absent from the canonical snapshot are explained, not silently dropped :: unexplained: []
PASS    6 canonical probabilities rendered in docs/ equal data/matches.json :: mismatched: []
PASS    7 divergences (>= 5 pp or opposite pick) are marked and listed :: 28 divergent fixtures; unmarked rows: []; missing from overview ledger: []
PASS    8 no series format is rendered that Hotspawn does not publish :: 192 rows have best_of=null in the feed; bad renders: []
PASS    9 internal links and fragments resolve (including ../ into the root site) :: broken: []
PASS   10 methodology documents the canonical relationship and the unpublished series format :: missing: []
WARN      canonical cards missing from the secondary snapshot :: 66

scheduled rows: 192 | shared with canonical: 146 | both priced: 139 | divergent: 28 | mean gap 2.651 pp | max gap 9.99 pp

ALL DOCS-PARITY CHECKS PASS
exit=0
```
