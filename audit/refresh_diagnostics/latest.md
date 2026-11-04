# refresh-docs verification output

run 41778867975 attempt 1 · commit `1d4b61f00562714fb9f92b2c46a10fa1e79f3f22` · 2026-11-04T05:23:02Z

## freshly generated snapshot
```
generated_at 2026-11-04T05:23:01.954Z | raw feed 2026-11-04T05:22:53.258Z
counts {"total_rows":508,"scheduled_total":169,"active_open_locked":76,"stale_scheduled":93,"ended_recent":283,"forfeited_recent":12,"cancelled_recent":43,"active_market":3,"active_model":73,"active_unresolved":0,"scheduled_market":3,"scheduled_model":159,"scheduled_walkover_settlement":4,"scheduled_unresolved":3,"by_source_scheduled":{"model":111,"walkover_settlement":4,"model_provisional":48,"unresolved":3,"market_consensus":3},"by_source_active":{"model":60,"market_consensus":3,"model_provisional":13},"flags":11}
calibration {"n":22469,"brier":0.2251,"series":32651}
rows 508 | scheduled 169
market rows: 1094919:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Smarkets (UKGC)] 1094917:4[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC] 1075825:4[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC]
scheduled rows with best_of != null: 0
flags 11 | dq-walkover-1071170 unverified-zero-history-1074627 dq-walkover-1071200 dq-walkover-1071206 dq-walkover-1071186 unverified-zero-history-1082002 unverified-zero-history-1083593 entity-collision-1079053 entity-collision-1079057 org-pooling-rich-gang-prm3 series-format-not-published
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
 docs/data/flags.json                       |  18 +-
 docs/data/picks.csv                        |  31 +-
 docs/data/picks.json                       | 965 +++++++++++++----------------
 docs/featured.html                         |  86 +--
 docs/flagged.html                          |  21 +-
 docs/index.html                            | 143 ++---
 docs/methodology.html                      |  18 +-
 docs/originated.html                       | 194 ++----
 docs/picks.html                            | 375 +++--------
 docs/results.html                          |  66 +-
 docs/table.html                            | 139 ++---
 docs/tournaments.html                      |  78 +--
 docs/unresolved.html                       |   6 +-
 32 files changed, 1501 insertions(+), 2208 deletions(-)
```

## python3 audit/verify_docs.py
```
PASS    1 docs/data/picks.json mirrors data/node/picks.json :: 1227463 bytes
PASS    2 every active match with a pick rendered on picks.html :: 76 picked rows, missing: []
PASS    3 rendered probabilities match JSON :: bad: []
PASS    4 every active match without a pick is on unresolved.html and index.html :: 0 unresolved, missing: []
PASS    5 every rendered card links its Hotspawn match card :: missing: []
PASS    6 market rows carry all matched venue source links :: 3 market rows, missing: []
PASS    7 results.html renders only official scores (no fabricated fills) :: 295 ended/forfeited checked, bad: []
PASS    8 no ledger entry with an official result renders as pending :: bad: []
PASS    9 navigation on every docs page :: []
PASS  9.1 exec summary links every picks view & subpage :: []
PASS   10 no broken internal links or fragments in docs/ :: []
PASS   11 probabilities sum to 100% and pick = argmax :: bad: []
PASS   12 all scheduled matches rendered 1:1 on docs/table.html with source links :: 169 scheduled rows, missing: []
PASS   13 all 10 docs/*.html category pages exist with mobile viewport :: missing=[] no_vp=[]
PASS   14 no '(Kills)' derivative market used as a match line :: []
PASS   15 cross-region homonym quarantines (#1083097, #1079031) & Solid Gaming DQ walkovers verified :: []
PASS   16 every Flagged for Review item renders with Hotspawn + official source links :: 11 flags, bad=[]

rows: 508 total | scheduled 169 | active 76 (76 with pick, 0 unresolved) | ended/forfeited 295 | flags 11 | ledger 316 entries

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
PASS session_6669f798 test_node_pipeline.mjs: 169 scheduled, 3 market rows (13 venue quotes joined, 0 single-venue fallback), OOS Brier=0.2251
exit=0
```

## python3 audit/verify_docs_parity.py
```
PASS    1 no docs page reuses a canonical title and every docs title says 'secondary' :: reused: []; unmarked: []
PASS    2 secondary banner is first in <body> and every page links the canonical hub :: banner not first: []; no canonical link: []
PASS    3 reconciliation + overview numbers reproduce both committed snapshots :: reconcile section: True; missing: []; oos series rendered: 22,469
PASS    4 every scheduled row deep-links to a canonical anchor that exists :: 169 rows; missing link: []; dead anchor: []
PASS    5 fixtures absent from the canonical snapshot are explained, not silently dropped :: unexplained: []
PASS    6 canonical probabilities rendered in docs/ equal data/matches.json :: mismatched: []
PASS    7 divergences (>= 5 pp or opposite pick) are marked and listed :: 29 divergent fixtures; unmarked rows: []; missing from overview ledger: []
PASS    8 no series format is rendered that Hotspawn does not publish :: 169 rows have best_of=null in the feed; bad renders: []
PASS    9 internal links and fragments resolve (including ../ into the root site) :: broken: []
PASS   10 methodology documents the canonical relationship and the unpublished series format :: missing: []
WARN      canonical cards missing from the secondary snapshot :: 62

scheduled rows: 169 | shared with canonical: 150 | both priced: 143 | divergent: 29 | mean gap 2.658 pp | max gap 9.99 pp

ALL DOCS-PARITY CHECKS PASS
exit=0
```
