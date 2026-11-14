# refresh-docs verification output

run 43646231261 attempt 1 · commit `23e6691acf252eb6d5cda65b929f21baec268b32` · 2026-11-14T22:05:54Z

## freshly generated snapshot
```
generated_at 2026-11-14T22:05:54.191Z | raw feed 2026-11-14T22:05:45.645Z
counts {"total_rows":401,"scheduled_total":148,"active_open_locked":44,"stale_scheduled":104,"ended_recent":229,"forfeited_recent":3,"cancelled_recent":21,"active_market":1,"active_model":42,"active_unresolved":1,"scheduled_market":1,"scheduled_model":137,"scheduled_walkover_settlement":4,"scheduled_unresolved":6,"by_source_scheduled":{"model":91,"walkover_settlement":4,"model_provisional":46,"unresolved":6,"market_consensus":1},"by_source_active":{"model":33,"model_provisional":9,"market_consensus":1,"unresolved":1},"flags":12}
calibration {"n":22604,"brier":0.2251,"series":32853}
rows 401 | scheduled 148
market rows: 1094982:3[Pinnacle+Polymarket+Kalshi CFTC]
scheduled rows with best_of != null: 0
flags 12 | dq-walkover-1071170 unverified-zero-history-1074627 dq-walkover-1071200 dq-walkover-1071206 dq-walkover-1071186 unverified-zero-history-1082002 unverified-zero-history-1083593 unverified-zero-history-1131686 unverified-zero-history-1131687 unverified-zero-history-1132746 org-pooling-rich-gang-prm3 series-format-not-published
```

## git diff --stat of this run's output
```
 data/node/raw/bovada_lol.json              |    2 +-
 data/node/raw/collect_log.json             |   36 +-
 data/node/raw/hotspawn_lobby_check.json    |    2 +-
 data/node/raw/hotspawn_lol_fixtures.json   |    2 +-
 data/node/raw/kalshi_lol.json              |    2 +-
 data/node/raw/kambi_lol.json               |    2 +-
 data/node/raw/pinnacle_lol.json            |    2 +-
 data/node/raw/pinnacle_matchups_cache.json |    2 +-
 data/node/raw/polymarket_lol.json          |    2 +-
 data/node/raw/smarkets_lol.json            |    2 +-
 docs/data/canonical_snapshot.json          |    2 +-
 docs/data/flags.json                       |   10 +-
 docs/data/picks.csv                        |   28 +-
 docs/data/picks.json                       | 2093 ++--------------------------
 docs/featured.html                         |   34 +-
 docs/flagged.html                          |   14 +-
 docs/index.html                            |   92 +-
 docs/methodology.html                      |    6 +-
 docs/originated.html                       |   46 +-
 docs/picks.html                            |  310 +---
 docs/results.html                          |  143 +-
 docs/table.html                            |   66 +-
 docs/tournaments.html                      |   42 +-
 docs/unresolved.html                       |  108 +-
 32 files changed, 498 insertions(+), 4864 deletions(-)
```

## python3 audit/verify_docs.py
```
PASS    1 docs/data/picks.json mirrors data/node/picks.json :: 950931 bytes
PASS    2 every active match with a pick rendered on picks.html :: 43 picked rows, missing: []
PASS    3 rendered probabilities match JSON :: bad: []
PASS    4 every active match without a pick is on unresolved.html and index.html :: 1 unresolved, missing: []
PASS    5 every rendered card links its Hotspawn match card :: missing: []
PASS    6 market rows carry all matched venue source links :: 1 market rows, missing: []
PASS    7 results.html renders only official scores (no fabricated fills) :: 232 ended/forfeited checked, bad: []
PASS    8 no ledger entry with an official result renders as pending :: bad: []
PASS    9 navigation on every docs page :: []
PASS  9.1 exec summary links every picks view & subpage :: []
PASS   10 no broken internal links or fragments in docs/ :: []
PASS   11 probabilities sum to 100% and pick = argmax :: bad: []
PASS   12 all scheduled matches rendered 1:1 on docs/table.html with source links :: 148 scheduled rows, missing: []
PASS   13 all 10 docs/*.html category pages exist with mobile viewport :: missing=[] no_vp=[]
PASS   14 no '(Kills)' derivative market used as a match line :: []
PASS   15 cross-region homonym quarantines (#1083097, #1079031) & Solid Gaming DQ walkovers verified :: []
PASS   16 every Flagged for Review item renders with Hotspawn + official source links :: 12 flags, bad=[]

rows: 401 total | scheduled 148 | active 44 (43 with pick, 1 unresolved) | ended/forfeited 232 | flags 12 | ledger 383 entries

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
WARNING: 1 market row(s) are priced from quotes observed after kick-off (in-play): 1094982(22:05Z vs kick-off 19:00Z) - disclosed on the pages, logged for the pipeline owner
note: no Worlds 2026 Main Event row is pre-kickoff in this snapshot (1 market rows) — the >=4-venue assertion is skipped, not weakened
note: #1079080 is no longer scheduled (kicked off or settled) — its Kalshi + Polymarket pair assertions are skipped
note: #1083097 is no longer scheduled — homonym quarantine assertions skipped
note: #1079031 is no longer scheduled — Swiss PvB homonym assertions skipped
note: #1081423 is no longer scheduled — LCP 2027 Promotion pick assertion skipped
PASS session_6669f798 test_node_pipeline.mjs: 148 scheduled, 1 market rows (3 venue quotes joined, 0 single-venue fallback), OOS Brier=0.2251
exit=0
```

## python3 audit/verify_docs_parity.py
```
PASS    1 no docs page reuses a canonical title and every docs title says 'secondary' :: reused: []; unmarked: []
PASS    2 secondary banner is first in <body> and every page links the canonical hub :: banner not first: []; no canonical link: []
PASS    3 reconciliation + overview numbers reproduce both committed snapshots :: reconcile section: True; missing: []; oos series rendered: 22,604
PASS    4 every scheduled row deep-links to a canonical anchor that exists :: 148 rows; missing link: []; dead anchor: []
PASS    5 fixtures absent from the canonical snapshot are explained, not silently dropped :: unexplained: []
PASS    6 canonical probabilities rendered in docs/ equal data/matches.json :: mismatched: []
PASS    7 divergences (>= 5 pp or opposite pick) are marked and listed :: 19 divergent fixtures; unmarked rows: []; missing from overview ledger: []
PASS    8 no series format is rendered that Hotspawn does not publish :: 148 rows have best_of=null in the feed; bad renders: []
PASS    9 internal links and fragments resolve (including ../ into the root site) :: broken: []
PASS   10 methodology documents the canonical relationship and the unpublished series format :: missing: []
WARN      canonical cards missing from the secondary snapshot :: 105

scheduled rows: 148 | shared with canonical: 107 | both priced: 100 | divergent: 19 | mean gap 2.463 pp | max gap 9.76 pp

ALL DOCS-PARITY CHECKS PASS
exit=0
```
