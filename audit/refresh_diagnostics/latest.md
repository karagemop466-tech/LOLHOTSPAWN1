# refresh-docs verification output

run 40412220451 attempt 1 · commit `2be0bf5c5ae2ea012e66ff0375fe30b3eb747482` · 2026-10-26T22:25:09Z

## freshly generated snapshot
```
generated_at 2026-10-26T22:25:08.786Z | raw feed 2026-10-26T22:25:00.974Z
counts {"total_rows":545,"scheduled_total":212,"active_open_locked":132,"stale_scheduled":80,"ended_recent":264,"forfeited_recent":23,"cancelled_recent":46,"active_market":5,"active_model":127,"active_unresolved":0,"scheduled_market":5,"scheduled_model":200,"scheduled_walkover_settlement":4,"scheduled_unresolved":3,"by_source_scheduled":{"model":144,"walkover_settlement":4,"model_provisional":56,"unresolved":3,"market_bovada":3,"market_consensus":2},"by_source_active":{"market_bovada":3,"model":103,"model_provisional":24,"market_consensus":2},"flags":15}
calibration {"n":22431,"brier":0.225,"series":32595}
rows 545 | scheduled 212
market rows: 1075821:1[Bovada] 1075820:1[Bovada] 1075822:1[Bovada] 1075823:4[Pinnacle+Polymarket+Kalshi CFTC+Bovada] 1079080:2[Polymarket+Kalshi CFTC]
scheduled rows with best_of != null: 0
flags 15 | dq-walkover-1071170 unverified-zero-history-1074627 dq-walkover-1071200 dq-walkover-1071206 dq-walkover-1071186 unverified-zero-history-1082002 unverified-zero-history-1083593 venue-divergence-1075823 entity-collision-1079031 entity-collision-1079038 entity-collision-1082746 entity-collision-1079053 entity-collision-1079057 org-pooling-rich-gang-prm3 series-format-not-published
```

## git diff --stat of this run's output
```
 data/node/raw/bovada_lol.json              |    2 +-
 data/node/raw/collect_log.json             |   46 +-
 data/node/raw/hotspawn_lobby_check.json    |    2 +-
 data/node/raw/hotspawn_lol_fixtures.json   |    2 +-
 data/node/raw/kalshi_lol.json              |    2 +-
 data/node/raw/kambi_lol.json               |    2 +-
 data/node/raw/pinnacle_lol.json            |    2 +-
 data/node/raw/pinnacle_matchups_cache.json |    2 +-
 data/node/raw/polymarket_lol.json          |    2 +-
 data/node/raw/smarkets_lol.json            |    2 +-
 docs/data/canonical_snapshot.json          |    2 +-
 docs/data/flags.json                       |   16 +-
 docs/data/picks.csv                        |   18 +-
 docs/data/picks.json                       | 1601 +++++-----------------------
 docs/featured.html                         |  148 +--
 docs/flagged.html                          |   19 +-
 docs/index.html                            |  120 ++-
 docs/methodology.html                      |   30 +-
 docs/originated.html                       |   34 +-
 docs/picks.html                            |  106 +-
 docs/results.html                          |   38 +-
 docs/table.html                            |   80 +-
 docs/tournaments.html                      |   52 +-
 docs/unresolved.html                       |    6 +-
 32 files changed, 1169 insertions(+), 3280 deletions(-)
```

## python3 audit/verify_docs.py
```
PASS    1 docs/data/picks.json mirrors data/node/picks.json :: 1307296 bytes
PASS    2 every active match with a pick rendered on picks.html :: 132 picked rows, missing: []
PASS    3 rendered probabilities match JSON :: bad: []
PASS    4 every active match without a pick is on unresolved.html and index.html :: 0 unresolved, missing: []
PASS    5 every rendered card links its Hotspawn match card :: missing: []
PASS    6 market rows carry all matched venue source links :: 5 market rows, missing: []
PASS    7 results.html renders only official scores (no fabricated fills) :: 287 ended/forfeited checked, bad: []
PASS    8 no ledger entry with an official result renders as pending :: bad: []
PASS    9 navigation on every docs page :: []
PASS  9.1 exec summary links every picks view & subpage :: []
PASS   10 no broken internal links or fragments in docs/ :: []
PASS   11 probabilities sum to 100% and pick = argmax :: bad: []
PASS   12 all scheduled matches rendered 1:1 on docs/table.html with source links :: 212 scheduled rows, missing: []
PASS   13 all 10 docs/*.html category pages exist with mobile viewport :: missing=[] no_vp=[]
PASS   14 no '(Kills)' derivative market used as a match line :: []
PASS   15 cross-region homonym quarantines (#1083097, #1079031) & Solid Gaming DQ walkovers verified :: []
PASS   16 every Flagged for Review item renders with Hotspawn + official source links :: 15 flags, bad=[]

rows: 545 total | scheduled 212 | active 132 (132 with pick, 0 unresolved) | ended/forfeited 287 | flags 15 | ledger 274 entries

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
note: #1075821 is a single-venue fallback (Bovada, quote 2026-10-26T13:09:14Z, 231 min before kick-off) - no second venue was live once the card locked
note: #1075820 is a single-venue fallback (Bovada, quote 2026-10-26T13:09:14Z, 291 min before kick-off) - no second venue was live once the card locked
note: #1075822 is a single-venue fallback (Bovada, quote 2026-10-26T13:09:14Z, 351 min before kick-off) - no second venue was live once the card locked
note: no Worlds 2026 Main Event row is pre-kickoff in this snapshot (5 market rows) — the >=4-venue assertion is skipped, not weakened
note: #1083097 is no longer scheduled — homonym quarantine assertions skipped
PASS session_6669f798 test_node_pipeline.mjs: 212 scheduled, 5 market rows (9 venue quotes joined, 3 single-venue fallback), OOS Brier=0.225
exit=0
```

## python3 audit/verify_docs_parity.py
```
PASS    1 no docs page reuses a canonical title and every docs title says 'secondary' :: reused: []; unmarked: []
PASS    2 secondary banner is first in <body> and every page links the canonical hub :: banner not first: []; no canonical link: []
PASS    3 reconciliation + overview numbers reproduce both committed snapshots :: reconcile section: True; missing: []; oos series rendered: 22,431
PASS    4 every scheduled row deep-links to a canonical anchor that exists :: 212 rows; missing link: []; dead anchor: []
PASS    5 fixtures absent from the canonical snapshot are explained, not silently dropped :: unexplained: []
PASS    6 canonical probabilities rendered in docs/ equal data/matches.json :: mismatched: []
PASS    7 divergences (>= 5 pp or opposite pick) are marked and listed :: 33 divergent fixtures; unmarked rows: []; missing from overview ledger: []
PASS    8 no series format is rendered that Hotspawn does not publish :: 212 rows have best_of=null in the feed; bad renders: []
PASS    9 internal links and fragments resolve (including ../ into the root site) :: broken: []
PASS   10 methodology documents the canonical relationship and the unpublished series format :: missing: []

scheduled rows: 212 | shared with canonical: 212 | both priced: 205 | divergent: 33 | mean gap 2.405 pp | max gap 29.25 pp

ALL DOCS-PARITY CHECKS PASS
exit=0
```
