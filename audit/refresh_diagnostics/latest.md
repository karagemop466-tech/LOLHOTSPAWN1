# refresh-docs verification output

run 40779067942 attempt 1 · commit `b6d179e03f56ef89e1b0741e4c40cdaff8b89f4e` · 2026-10-28T22:19:50Z

## freshly generated snapshot
```
generated_at 2026-10-28T22:19:50.218Z | raw feed 2026-10-28T22:19:41.859Z
counts {"total_rows":546,"scheduled_total":212,"active_open_locked":132,"stale_scheduled":80,"ended_recent":264,"forfeited_recent":22,"cancelled_recent":48,"active_market":5,"active_model":123,"active_unresolved":4,"scheduled_market":5,"scheduled_model":196,"scheduled_walkover_settlement":4,"scheduled_unresolved":7,"by_source_scheduled":{"model":143,"walkover_settlement":4,"model_provisional":53,"unresolved":7,"market_consensus":5},"by_source_active":{"model":102,"model_provisional":21,"market_consensus":5,"unresolved":4},"flags":18}
calibration {"n":22408,"brier":0.2251,"series":32572}
rows 546 | scheduled 212
market rows: 1094909:3[Pinnacle+Polymarket+Kalshi CFTC] 1094911:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Smarkets (UKGC)] 1094908:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Smarkets (UKGC)] 1094912:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Smarkets (UKGC)] 1094913:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Smarkets (UKGC)]
scheduled rows with best_of != null: 0
flags 18 | dq-walkover-1071170 unverified-zero-history-1074627 dq-walkover-1071200 dq-walkover-1071206 dq-walkover-1071186 unverified-zero-history-1082002 unverified-zero-history-1083593 venue-divergence-1094909 entity-collision-1079038 unverified-zero-history-1121690 unverified-zero-history-1121692 unverified-zero-history-1121693 unverified-zero-history-1121694 entity-collision-1082746 entity-collision-1079053 entity-collision-1079057 org-pooling-rich-gang-prm3 series-format-not-published
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
 docs/data/flags.json                       |   66 +-
 docs/data/picks.csv                        |   26 +-
 docs/data/picks.json                       | 1878 ++++++++++++----------------
 docs/featured.html                         |  124 +-
 docs/flagged.html                          |   65 +-
 docs/index.html                            |  220 ++--
 docs/methodology.html                      |   10 +-
 docs/originated.html                       |  189 ++-
 docs/picks.html                            |  214 +++-
 docs/results.html                          |   54 +-
 docs/table.html                            |  164 ++-
 docs/tournaments.html                      |  213 +++-
 docs/unresolved.html                       |  105 +-
 32 files changed, 3014 insertions(+), 2830 deletions(-)
```

## python3 audit/verify_docs.py
```
PASS    1 docs/data/picks.json mirrors data/node/picks.json :: 1326784 bytes
PASS    2 every active match with a pick rendered on picks.html :: 128 picked rows, missing: []
PASS    3 rendered probabilities match JSON :: bad: []
PASS    4 every active match without a pick is on unresolved.html and index.html :: 4 unresolved, missing: []
PASS    5 every rendered card links its Hotspawn match card :: missing: []
PASS    6 market rows carry all matched venue source links :: 5 market rows, missing: []
PASS    7 results.html renders only official scores (no fabricated fills) :: 286 ended/forfeited checked, bad: []
PASS    8 no ledger entry with an official result renders as pending :: bad: []
PASS    9 navigation on every docs page :: []
PASS  9.1 exec summary links every picks view & subpage :: []
PASS   10 no broken internal links or fragments in docs/ :: []
PASS   11 probabilities sum to 100% and pick = argmax :: bad: []
PASS   12 all scheduled matches rendered 1:1 on docs/table.html with source links :: 212 scheduled rows, missing: []
PASS   13 all 10 docs/*.html category pages exist with mobile viewport :: missing=[] no_vp=[]
PASS   14 no '(Kills)' derivative market used as a match line :: []
PASS   15 cross-region homonym quarantines (#1083097, #1079031) & Solid Gaming DQ walkovers verified :: []
PASS   16 every Flagged for Review item renders with Hotspawn + official source links :: 18 flags, bad=[]

rows: 546 total | scheduled 212 | active 132 (128 with pick, 4 unresolved) | ended/forfeited 286 | flags 18 | ledger 287 entries

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
PASS session_6669f798 test_node_pipeline.mjs: 212 scheduled, 5 market rows (23 venue quotes joined, 0 single-venue fallback), OOS Brier=0.2251
exit=0
```

## python3 audit/verify_docs_parity.py
```
PASS    1 no docs page reuses a canonical title and every docs title says 'secondary' :: reused: []; unmarked: []
PASS    2 secondary banner is first in <body> and every page links the canonical hub :: banner not first: []; no canonical link: []
PASS    3 reconciliation + overview numbers reproduce both committed snapshots :: reconcile section: True; missing: []; oos series rendered: 22,408
PASS    4 every scheduled row deep-links to a canonical anchor that exists :: 212 rows; missing link: []; dead anchor: []
PASS    5 fixtures absent from the canonical snapshot are explained, not silently dropped :: unexplained: []
PASS    6 canonical probabilities rendered in docs/ equal data/matches.json :: mismatched: []
PASS    7 divergences (>= 5 pp or opposite pick) are marked and listed :: 30 divergent fixtures; unmarked rows: []; missing from overview ledger: []
PASS    8 no series format is rendered that Hotspawn does not publish :: 212 rows have best_of=null in the feed; bad renders: []
PASS    9 internal links and fragments resolve (including ../ into the root site) :: broken: []
PASS   10 methodology documents the canonical relationship and the unpublished series format :: missing: []
WARN      canonical cards missing from the secondary snapshot :: 17

scheduled rows: 212 | shared with canonical: 195 | both priced: 188 | divergent: 30 | mean gap 2.368 pp | max gap 9.76 pp

ALL DOCS-PARITY CHECKS PASS
exit=0
```
