# refresh-docs verification output

run 41135265938 attempt 1 · commit `224d3ba20a8b4936e0b078c8796b7185ceb84461` · 2026-10-30T22:01:56Z

## freshly generated snapshot
```
generated_at 2026-10-30T22:01:56.396Z | raw feed 2026-10-30T22:01:48.474Z
counts {"total_rows":556,"scheduled_total":210,"active_open_locked":131,"stale_scheduled":79,"ended_recent":278,"forfeited_recent":21,"cancelled_recent":47,"active_market":2,"active_model":117,"active_unresolved":12,"scheduled_market":2,"scheduled_model":189,"scheduled_walkover_settlement":4,"scheduled_unresolved":15,"by_source_scheduled":{"model":136,"walkover_settlement":4,"model_provisional":53,"unresolved":15,"market_consensus":2},"by_source_active":{"model":95,"market_consensus":2,"unresolved":12,"model_provisional":22},"flags":25}
calibration {"n":22422,"brier":0.2251,"series":32592}
rows 556 | scheduled 210
market rows: 1094912:3[Pinnacle+Polymarket+Kalshi CFTC] 1094913:5[Pinnacle+Unibet (Kambi)+Polymarket+Smarkets (UKGC)+Kalshi CFTC]
scheduled rows with best_of != null: 0
flags 25 | dq-walkover-1071170 unverified-zero-history-1074627 dq-walkover-1071200 dq-walkover-1071206 dq-walkover-1071186 unverified-zero-history-1082002 unverified-zero-history-1083593 entity-collision-1079038 unverified-zero-history-1128817 unverified-zero-history-1126362 unverified-zero-history-1126363 unverified-zero-history-1128818 unverified-zero-history-1126364 unverified-zero-history-1126365 unverified-zero-history-1126366 unverified-zero-history-1126367 unverified-zero-history-1121690 unverified-zero-history-1121692 unverified-zero-history-1121693 unverified-zero-history-1121694 entity-collision-1082746 entity-collision-1079053 entity-collision-1079057 org-pooling-rich-gang-prm3 series-format-not-published
```

## git diff --stat of this run's output
```
 data/node/raw/bovada_lol.json              |   2 +-
 data/node/raw/collect_log.json             |  36 +-
 data/node/raw/hotspawn_lobby_check.json    |   2 +-
 data/node/raw/hotspawn_lol_fixtures.json   |   2 +-
 data/node/raw/kalshi_lol.json              |   2 +-
 data/node/raw/kambi_lol.json               |   2 +-
 data/node/raw/pinnacle_lol.json            |   2 +-
 data/node/raw/pinnacle_matchups_cache.json |   2 +-
 data/node/raw/polymarket_lol.json          |   2 +-
 data/node/raw/smarkets_lol.json            |   2 +-
 docs/data/canonical_snapshot.json          |   2 +-
 docs/data/flags.json                       |   6 +-
 docs/data/picks.csv                        |  23 +-
 docs/data/picks.json                       | 969 +++++++++++------------------
 docs/featured.html                         |  52 +-
 docs/flagged.html                          |  10 +-
 docs/index.html                            |  58 +-
 docs/methodology.html                      |  12 +-
 docs/originated.html                       | 127 +---
 docs/picks.html                            | 157 +----
 docs/results.html                          |  45 +-
 docs/table.html                            |  87 +--
 docs/tournaments.html                      |  64 +-
 docs/unresolved.html                       |   6 +-
 32 files changed, 1154 insertions(+), 1897 deletions(-)
```

## python3 audit/verify_docs.py
```
PASS    1 docs/data/picks.json mirrors data/node/picks.json :: 1326165 bytes
PASS    2 every active match with a pick rendered on picks.html :: 119 picked rows, missing: []
PASS    3 rendered probabilities match JSON :: bad: []
PASS    4 every active match without a pick is on unresolved.html and index.html :: 12 unresolved, missing: []
PASS    5 every rendered card links its Hotspawn match card :: missing: []
PASS    6 market rows carry all matched venue source links :: 2 market rows, missing: []
PASS    7 results.html renders only official scores (no fabricated fills) :: 299 ended/forfeited checked, bad: []
PASS    8 no ledger entry with an official result renders as pending :: bad: []
PASS    9 navigation on every docs page :: []
PASS  9.1 exec summary links every picks view & subpage :: []
PASS   10 no broken internal links or fragments in docs/ :: []
PASS   11 probabilities sum to 100% and pick = argmax :: bad: []
PASS   12 all scheduled matches rendered 1:1 on docs/table.html with source links :: 210 scheduled rows, missing: []
PASS   13 all 10 docs/*.html category pages exist with mobile viewport :: missing=[] no_vp=[]
PASS   14 no '(Kills)' derivative market used as a match line :: []
PASS   15 cross-region homonym quarantines (#1083097, #1079031) & Solid Gaming DQ walkovers verified :: []
PASS   16 every Flagged for Review item renders with Hotspawn + official source links :: 25 flags, bad=[]

rows: 556 total | scheduled 210 | active 131 (119 with pick, 12 unresolved) | ended/forfeited 299 | flags 25 | ledger 291 entries

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
WARNING: 1 market row(s) are priced from quotes observed after kick-off (in-play): 1094912(22:01Z vs kick-off 20:00Z) - disclosed on the pages, logged for the pipeline owner
note: #1079080 is no longer scheduled (kicked off or settled) — its Kalshi + Polymarket pair assertions are skipped
note: #1083097 is no longer scheduled — homonym quarantine assertions skipped
note: #1079031 is no longer scheduled — Swiss PvB homonym assertions skipped
PASS session_6669f798 test_node_pipeline.mjs: 210 scheduled, 2 market rows (8 venue quotes joined, 0 single-venue fallback), OOS Brier=0.2251
exit=0
```

## python3 audit/verify_docs_parity.py
```
PASS    1 no docs page reuses a canonical title and every docs title says 'secondary' :: reused: []; unmarked: []
PASS    2 secondary banner is first in <body> and every page links the canonical hub :: banner not first: []; no canonical link: []
PASS    3 reconciliation + overview numbers reproduce both committed snapshots :: reconcile section: True; missing: []; oos series rendered: 22,422
PASS    4 every scheduled row deep-links to a canonical anchor that exists :: 210 rows; missing link: []; dead anchor: []
PASS    5 fixtures absent from the canonical snapshot are explained, not silently dropped :: unexplained: []
PASS    6 canonical probabilities rendered in docs/ equal data/matches.json :: mismatched: []
PASS    7 divergences (>= 5 pp or opposite pick) are marked and listed :: 32 divergent fixtures; unmarked rows: []; missing from overview ledger: []
PASS    8 no series format is rendered that Hotspawn does not publish :: 210 rows have best_of=null in the feed; bad renders: []
PASS    9 internal links and fragments resolve (including ../ into the root site) :: broken: []
PASS   10 methodology documents the canonical relationship and the unpublished series format :: missing: []
WARN      canonical cards missing from the secondary snapshot :: 27

scheduled rows: 210 | shared with canonical: 185 | both priced: 178 | divergent: 32 | mean gap 2.413 pp | max gap 9.76 pp

ALL DOCS-PARITY CHECKS PASS
exit=0
```
