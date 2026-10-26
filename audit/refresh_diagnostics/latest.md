# refresh-docs verification output

run 40322844002 attempt 1 · commit `f16c592a890b1d6ae88f1711e4fff74bb3a6cc33` · 2026-10-26T12:29:12Z

## freshly generated snapshot
```
generated_at 2026-10-26T12:29:11.874Z | raw feed 2026-10-26T12:29:03.171Z
counts {"total_rows":549,"scheduled_total":212,"active_open_locked":132,"stale_scheduled":80,"ended_recent":268,"forfeited_recent":23,"cancelled_recent":46,"active_market":5,"active_model":127,"active_unresolved":0,"scheduled_market":5,"scheduled_model":200,"scheduled_walkover_settlement":4,"scheduled_unresolved":3,"by_source_scheduled":{"model":144,"walkover_settlement":4,"model_provisional":56,"unresolved":3,"market_consensus":5},"by_source_active":{"market_consensus":5,"model":103,"model_provisional":24},"flags":14}
calibration {"n":22429,"brier":0.225,"series":32593}
rows 549 | scheduled 212
market rows: 1075821:6[Pinnacle+Unibet (Kambi)+Polymarket+Smarkets (UKGC)+Kalshi CFTC+Bovada] 1075820:6[Pinnacle+Unibet (Kambi)+Polymarket+Smarkets (UKGC)+Kalshi CFTC+Bovada] 1075822:6[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Bovada+Smarkets (UKGC)] 1075823:6[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Bovada+Smarkets (UKGC)] 1079080:2[Kalshi CFTC+Polymarket]
scheduled rows with best_of != null: 0
flags 14 | dq-walkover-1071170 unverified-zero-history-1074627 dq-walkover-1071200 dq-walkover-1071206 dq-walkover-1071186 unverified-zero-history-1082002 unverified-zero-history-1083593 entity-collision-1079031 entity-collision-1079038 entity-collision-1082746 entity-collision-1079053 entity-collision-1079057 org-pooling-rich-gang-prm3 series-format-not-published
```

## git diff --stat of this run's output
```
 data/node/raw/bovada_lol.json              |     2 +-
 data/node/raw/collect_log.json             |    32 +-
 data/node/raw/hotspawn_lobby_check.json    |     2 +-
 data/node/raw/hotspawn_lol_fixtures.json   |     2 +-
 data/node/raw/kalshi_lol.json              |     2 +-
 data/node/raw/kambi_lol.json               |     2 +-
 data/node/raw/pinnacle_lol.json            |     2 +-
 data/node/raw/pinnacle_matchups_cache.json |     2 +-
 data/node/raw/polymarket_lol.json          |     2 +-
 data/node/raw/smarkets_lol.json            |     2 +-
 docs/data/canonical_snapshot.json          |     2 +-
 docs/data/flags.json                       |    10 +-
 docs/data/picks.csv                        |    96 +-
 docs/data/picks.json                       | 14042 ++++++++++++++-------------
 docs/featured.html                         |    96 +-
 docs/flagged.html                          |    12 +-
 docs/index.html                            |   240 +-
 docs/methodology.html                      |    56 +-
 docs/originated.html                       |   816 +-
 docs/picks.html                            |   516 +-
 docs/results.html                          |   357 +-
 docs/table.html                            |   410 +-
 docs/tournaments.html                      |   269 +-
 docs/unresolved.html                       |     6 +-
 32 files changed, 16683 insertions(+), 16312 deletions(-)
```

## python3 audit/verify_docs.py
```
PASS    1 docs/data/picks.json mirrors data/node/picks.json :: 1339622 bytes
PASS    2 every active match with a pick rendered on picks.html :: 132 picked rows, missing: []
PASS    3 rendered probabilities match JSON :: bad: []
PASS    4 every active match without a pick is on unresolved.html and index.html :: 0 unresolved, missing: []
PASS    5 every rendered card links its Hotspawn match card :: missing: []
PASS    6 market rows carry all matched venue source links :: 5 market rows, missing: []
PASS    7 results.html renders only official scores (no fabricated fills) :: 291 ended/forfeited checked, bad: []
PASS    8 no ledger entry with an official result renders as pending :: bad: []
PASS    9 navigation on every docs page :: []
PASS  9.1 exec summary links every picks view & subpage :: []
PASS   10 no broken internal links or fragments in docs/ :: []
PASS   11 probabilities sum to 100% and pick = argmax :: bad: []
PASS   12 all scheduled matches rendered 1:1 on docs/table.html with source links :: 212 scheduled rows, missing: []
PASS   13 all 10 docs/*.html category pages exist with mobile viewport :: missing=[] no_vp=[]
PASS   14 no '(Kills)' derivative market used as a match line :: []
PASS   15 cross-region homonym quarantines (#1083097, #1079031) & Solid Gaming DQ walkovers verified :: []
PASS   16 every Flagged for Review item renders with Hotspawn + official source links :: 14 flags, bad=[]

rows: 549 total | scheduled 212 | active 132 (132 with pick, 0 unresolved) | ended/forfeited 291 | flags 14 | ledger 274 entries

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
PASS session_6669f798 test_node_pipeline.mjs: 212 scheduled, 5 market rows (26 venue quotes joined, 0 single-venue fallback), OOS Brier=0.225
exit=0
```

## python3 audit/verify_docs_parity.py
```
PASS    1 no docs page reuses a canonical title and every docs title says 'secondary' :: reused: []; unmarked: []
PASS    2 secondary banner is first in <body> and every page links the canonical hub :: banner not first: []; no canonical link: []
PASS    3 reconciliation + overview numbers reproduce both committed snapshots :: reconcile section: True; missing: []; oos series rendered: 22,429
PASS    4 every scheduled row deep-links to a canonical anchor that exists :: 212 rows; missing link: []; dead anchor: []
PASS    5 fixtures absent from the canonical snapshot are explained, not silently dropped :: unexplained: []
PASS    6 canonical probabilities rendered in docs/ equal data/matches.json :: mismatched: []
PASS    7 divergences (>= 5 pp or opposite pick) are marked and listed :: 33 divergent fixtures; unmarked rows: []; missing from overview ledger: []
PASS    8 no series format is rendered that Hotspawn does not publish :: 212 rows have best_of=null in the feed; bad renders: []
PASS    9 internal links and fragments resolve (including ../ into the root site) :: broken: []
PASS   10 methodology documents the canonical relationship and the unpublished series format :: missing: []
WARN      canonical cards missing from the secondary snapshot :: 11

scheduled rows: 212 | shared with canonical: 211 | both priced: 204 | divergent: 33 | mean gap 2.286 pp | max gap 9.76 pp

ALL DOCS-PARITY CHECKS PASS
exit=0
```
