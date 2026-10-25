# refresh-docs verification output

run 40231205280 attempt 1 · commit `5264ea28b1149de56499fbc493bd1b69f74471d0` · 2026-10-25T20:32:16Z

## freshly generated snapshot
```
generated_at 2026-10-25T20:32:15.407Z | raw feed 2026-10-25T20:32:07.392Z
counts {"total_rows":551,"scheduled_total":233,"active_open_locked":156,"stale_scheduled":77,"ended_recent":251,"forfeited_recent":22,"cancelled_recent":45,"active_market":9,"active_model":147,"active_unresolved":0,"scheduled_market":9,"scheduled_model":217,"scheduled_walkover_settlement":4,"scheduled_unresolved":3,"by_source_scheduled":{"model":146,"walkover_settlement":4,"model_provisional":71,"unresolved":3,"market_bovada":2,"market_consensus":7},"by_source_active":{"model_provisional":41,"model":106,"market_bovada":2,"market_consensus":7},"flags":15}
calibration {"n":22396,"brier":0.225,"series":32560}
rows 551 | scheduled 233
market rows: 1075817:1[Bovada] 1075816:1[Bovada] 1075819:2[Pinnacle+Bovada] 1075818:6[Pinnacle+Unibet (Kambi)+Polymarket+Smarkets (UKGC)+Kalshi CFTC+Bovada] 1075821:6[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Bovada+Smarkets (UKGC)] 1075820:6[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Bovada+Smarkets (UKGC)] 1075822:6[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Bovada+Smarkets (UKGC)] 1075823:6[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Bovada+Smarkets (UKGC)] 1079080:2[Kalshi CFTC+Polymarket]
scheduled rows with best_of != null: 0
flags 15 | dq-walkover-1071170 unverified-zero-history-1074627 dq-walkover-1071200 dq-walkover-1071206 dq-walkover-1071186 unverified-zero-history-1082002 unverified-zero-history-1083593 venue-divergence-1075819 entity-collision-1079031 entity-collision-1079038 entity-collision-1082746 entity-collision-1079053 entity-collision-1079057 org-pooling-rich-gang-prm3 series-format-not-published
```

## git diff --stat of this run's output
```
 data/node/picks.json                       | 3140 ++++++----------------------
 data/node/raw/collect_log.json             |   48 +-
 data/node/raw/hotspawn_lobby_check.json    |    2 +-
 data/node/raw/hotspawn_lol_fixtures.json   |    2 +-
 data/node/raw/kalshi_lol.json              |    2 +-
 data/node/raw/kambi_lol.json               |    2 +-
 data/node/raw/pinnacle_lol.json            |    2 +-
 data/node/raw/pinnacle_matchups_cache.json |    2 +-
 data/node/raw/polymarket_lol.json          |    2 +-
 data/node/raw/smarkets_lol.json            |    2 +-
 docs/data/canonical_snapshot.json          |    2 +-
 docs/data/flags.json                       |   18 +-
 docs/data/picks.csv                        |   67 +-
 docs/data/picks.json                       | 3140 ++++++----------------------
 docs/featured.html                         |  172 +-
 docs/flagged.html                          |   18 +-
 docs/index.html                            |  154 +-
 docs/methodology.html                      |   36 +-
 docs/originated.html                       |   95 +-
 docs/picks.html                            |  181 +-
 docs/results.html                          |  160 +-
 docs/table.html                            |  153 +-
 docs/tournaments.html                      |  106 +-
 docs/unresolved.html                       |    6 +-
 31 files changed, 2516 insertions(+), 6719 deletions(-)
```

## python3 audit/verify_docs.py
```
PASS    1 docs/data/picks.json mirrors data/node/picks.json :: 1358741 bytes
PASS    2 every active match with a pick rendered on picks.html :: 156 picked rows, missing: []
PASS    3 rendered probabilities match JSON :: bad: []
PASS    4 every active match without a pick is on unresolved.html and index.html :: 0 unresolved, missing: []
PASS    5 every rendered card links its Hotspawn match card :: missing: []
PASS    6 market rows carry all matched venue source links :: 9 market rows, missing: []
PASS    7 results.html renders only official scores (no fabricated fills) :: 273 ended/forfeited checked, bad: []
PASS    8 no ledger entry with an official result renders as pending :: bad: []
PASS    9 navigation on every docs page :: []
PASS  9.1 exec summary links every picks view & subpage :: []
PASS   10 no broken internal links or fragments in docs/ :: []
PASS   11 probabilities sum to 100% and pick = argmax :: bad: []
PASS   12 all scheduled matches rendered 1:1 on docs/table.html with source links :: 233 scheduled rows, missing: []
PASS   13 all 10 docs/*.html category pages exist with mobile viewport :: missing=[] no_vp=[]
PASS   14 no '(Kills)' derivative market used as a match line :: []
PASS   15 cross-region homonym quarantines (#1083097, #1079031) & Solid Gaming DQ walkovers verified :: []
PASS   16 every Flagged for Review item renders with Hotspawn + official source links :: 15 flags, bad=[]

rows: 551 total | scheduled 233 | active 156 (156 with pick, 0 unresolved) | ended/forfeited 273 | flags 15 | ledger 271 entries

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
note: #1075817 is a single-venue fallback (Bovada, quote 2026-10-25T14:13:24Z, 167 min before kick-off) - no second venue was live once the card locked
note: #1075816 is a single-venue fallback (Bovada, quote 2026-10-25T14:13:24Z, 227 min before kick-off) - no second venue was live once the card locked
note: #1083097 is no longer scheduled — homonym quarantine assertions skipped
PASS session_6669f798 test_node_pipeline.mjs: 233 scheduled, 9 market rows (36 venue quotes joined, 2 single-venue fallback), OOS Brier=0.225
exit=0
```

## python3 audit/verify_docs_parity.py
```
PASS    1 no docs page reuses a canonical title and every docs title says 'secondary' :: reused: []; unmarked: []
PASS    2 secondary banner is first in <body> and every page links the canonical hub :: banner not first: []; no canonical link: []
PASS    3 reconciliation + overview numbers reproduce both committed snapshots :: reconcile section: True; missing: []; oos series rendered: 22,396
PASS    4 every scheduled row deep-links to a canonical anchor that exists :: 233 rows; missing link: []; dead anchor: []
PASS    5 fixtures absent from the canonical snapshot are explained, not silently dropped :: unexplained: []
PASS    6 canonical probabilities rendered in docs/ equal data/matches.json :: mismatched: []
PASS    7 divergences (>= 5 pp or opposite pick) are marked and listed :: 35 divergent fixtures; unmarked rows: []; missing from overview ledger: []
PASS    8 no series format is rendered that Hotspawn does not publish :: 233 rows have best_of=null in the feed; bad renders: []
PASS    9 internal links and fragments resolve (including ../ into the root site) :: broken: []
PASS   10 methodology documents the canonical relationship and the unpublished series format :: missing: []
WARN      canonical cards missing from the secondary snapshot :: 1

scheduled rows: 233 | shared with canonical: 233 | both priced: 226 | divergent: 35 | mean gap 2.286 pp | max gap 12.97 pp

ALL DOCS-PARITY CHECKS PASS
exit=0
```
