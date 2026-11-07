# refresh-docs verification output

run 42416530745 attempt 1 · commit `1dc22b331c53883e34802a8af13455e4573b7a35` · 2026-11-07T21:35:07Z

## freshly generated snapshot
```
generated_at 2026-11-07T21:35:07.140Z | raw feed 2026-11-07T21:34:59.436Z
counts {"total_rows":517,"scheduled_total":185,"active_open_locked":95,"stale_scheduled":90,"ended_recent":282,"forfeited_recent":10,"cancelled_recent":40,"active_market":4,"active_model":75,"active_unresolved":16,"scheduled_market":4,"scheduled_model":158,"scheduled_walkover_settlement":4,"scheduled_unresolved":19,"by_source_scheduled":{"model":112,"walkover_settlement":4,"model_provisional":46,"unresolved":19,"market_consensus":3,"market_polymarket":1},"by_source_active":{"model":62,"model_provisional":13,"market_consensus":3,"unresolved":16,"market_polymarket":1},"flags":27}
calibration {"n":22496,"brier":0.2251,"series":32696}
rows 517 | scheduled 185
market rows: 1094932:5[Pinnacle+Unibet (Kambi)+Polymarket+Smarkets (UKGC)+Kalshi CFTC] 1130194:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Smarkets (UKGC)] 1081421:1[Polymarket] 1082007:2[Polymarket+Kalshi CFTC]
scheduled rows with best_of != null: 0
flags 27 | dq-walkover-1071170 unverified-zero-history-1074627 dq-walkover-1071200 dq-walkover-1071206 dq-walkover-1071186 unverified-zero-history-1082002 unverified-zero-history-1083593 entity-collision-1079053 unverified-zero-history-1130130 unverified-zero-history-1130131 unverified-zero-history-1130132 unverified-zero-history-1130133 unverified-zero-history-1130134 unverified-zero-history-1130135 unverified-zero-history-1130136 unverified-zero-history-1130137 unverified-zero-history-1130138 unverified-zero-history-1130139 unverified-zero-history-1130140 unverified-zero-history-1130141 unverified-zero-history-1130142 unverified-zero-history-1130706 entity-collision-1079057 unverified-zero-history-1130143 unverified-zero-history-1130144 org-pooling-rich-gang-prm3 series-format-not-published
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
 docs/data/picks.csv                        |   43 +-
 docs/data/picks.json                       | 2287 +++++++++-------------------
 docs/featured.html                         |  138 +-
 docs/flagged.html                          |    8 +-
 docs/index.html                            |  168 +-
 docs/methodology.html                      |   24 +-
 docs/originated.html                       |  283 ++--
 docs/picks.html                            |  374 ++---
 docs/results.html                          |  184 +--
 docs/table.html                            |  155 +-
 docs/tournaments.html                      |   96 +-
 docs/unresolved.html                       |    6 +-
 32 files changed, 2503 insertions(+), 4247 deletions(-)
```

## python3 audit/verify_docs.py
```
PASS    1 docs/data/picks.json mirrors data/node/picks.json :: 1235772 bytes
PASS    2 every active match with a pick rendered on picks.html :: 79 picked rows, missing: []
PASS    3 rendered probabilities match JSON :: bad: []
PASS    4 every active match without a pick is on unresolved.html and index.html :: 16 unresolved, missing: []
PASS    5 every rendered card links its Hotspawn match card :: missing: []
PASS    6 market rows carry all matched venue source links :: 4 market rows, missing: []
PASS    7 results.html renders only official scores (no fabricated fills) :: 292 ended/forfeited checked, bad: []
PASS    8 no ledger entry with an official result renders as pending :: bad: []
PASS    9 navigation on every docs page :: []
PASS  9.1 exec summary links every picks view & subpage :: []
PASS   10 no broken internal links or fragments in docs/ :: []
PASS   11 probabilities sum to 100% and pick = argmax :: bad: []
PASS   12 all scheduled matches rendered 1:1 on docs/table.html with source links :: 185 scheduled rows, missing: []
PASS   13 all 10 docs/*.html category pages exist with mobile viewport :: missing=[] no_vp=[]
PASS   14 no '(Kills)' derivative market used as a match line :: []
PASS   15 cross-region homonym quarantines (#1083097, #1079031) & Solid Gaming DQ walkovers verified :: []
PASS   16 every Flagged for Review item renders with Hotspawn + official source links :: 27 flags, bad=[]

rows: 517 total | scheduled 185 | active 95 (79 with pick, 16 unresolved) | ended/forfeited 292 | flags 27 | ledger 342 entries

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
note: #1081421 is a single-venue fallback (Polymarket, quote 2026-11-07T21:35:01.193Z, 3325 min before kick-off) - no second venue was live once the card locked
note: #1079080 is no longer scheduled (kicked off or settled) — its Kalshi + Polymarket pair assertions are skipped
note: #1083097 is no longer scheduled — homonym quarantine assertions skipped
note: #1079031 is no longer scheduled — Swiss PvB homonym assertions skipped
PASS session_6669f798 test_node_pipeline.mjs: 185 scheduled, 4 market rows (13 venue quotes joined, 1 single-venue fallback), OOS Brier=0.2251
exit=0
```

## python3 audit/verify_docs_parity.py
```
PASS    1 no docs page reuses a canonical title and every docs title says 'secondary' :: reused: []; unmarked: []
PASS    2 secondary banner is first in <body> and every page links the canonical hub :: banner not first: []; no canonical link: []
PASS    3 reconciliation + overview numbers reproduce both committed snapshots :: reconcile section: True; missing: []; oos series rendered: 22,496
PASS    4 every scheduled row deep-links to a canonical anchor that exists :: 185 rows; missing link: []; dead anchor: []
PASS    5 fixtures absent from the canonical snapshot are explained, not silently dropped :: unexplained: []
PASS    6 canonical probabilities rendered in docs/ equal data/matches.json :: mismatched: []
PASS    7 divergences (>= 5 pp or opposite pick) are marked and listed :: 27 divergent fixtures; unmarked rows: []; missing from overview ledger: []
PASS    8 no series format is rendered that Hotspawn does not publish :: 185 rows have best_of=null in the feed; bad renders: []
PASS    9 internal links and fragments resolve (including ../ into the root site) :: broken: []
PASS   10 methodology documents the canonical relationship and the unpublished series format :: missing: []
WARN      canonical cards missing from the secondary snapshot :: 75

scheduled rows: 185 | shared with canonical: 137 | both priced: 130 | divergent: 27 | mean gap 3.073 pp | max gap 27.86 pp

ALL DOCS-PARITY CHECKS PASS
exit=0
```
