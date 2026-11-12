# refresh-docs verification output

run 43241194632 attempt 1 · commit `84b59bbbfcffe6af30f26380d835adcdcfe133a1` · 2026-11-12T14:49:47Z

## freshly generated snapshot
```
generated_at 2026-11-12T14:49:47.351Z | raw feed 2026-11-12T14:49:39.389Z
counts {"total_rows":486,"scheduled_total":157,"active_open_locked":64,"stale_scheduled":93,"ended_recent":294,"forfeited_recent":4,"cancelled_recent":31,"active_market":2,"active_model":59,"active_unresolved":3,"scheduled_market":2,"scheduled_model":145,"scheduled_walkover_settlement":4,"scheduled_unresolved":6,"by_source_scheduled":{"model":94,"walkover_settlement":4,"model_provisional":51,"unresolved":6,"market_consensus":2},"by_source_active":{"model":42,"model_provisional":17,"market_consensus":2,"unresolved":3},"flags":14}
calibration {"n":22586,"brier":0.2251,"series":32834}
rows 486 | scheduled 157
market rows: 1081425:3[Unibet (Kambi)+Polymarket+Kalshi CFTC] 1094982:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Smarkets (UKGC)]
scheduled rows with best_of != null: 0
flags 14 | dq-walkover-1071170 unverified-zero-history-1074627 dq-walkover-1071200 dq-walkover-1071206 dq-walkover-1071186 unverified-zero-history-1082002 unverified-zero-history-1083593 venue-divergence-1081425 unverified-zero-history-1130706 entity-collision-1079057 unverified-zero-history-1131686 unverified-zero-history-1131687 org-pooling-rich-gang-prm3 series-format-not-published
```

## git diff --stat of this run's output
```
 data/node/raw/bovada_lol.json              |    2 +-
 data/node/raw/collect_log.json             |   40 +-
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
 docs/data/picks.csv                        |   37 +-
 docs/data/picks.json                       | 6309 ++++++++++++++--------------
 docs/featured.html                         |   68 +-
 docs/flagged.html                          |   18 +-
 docs/index.html                            |  100 +-
 docs/methodology.html                      |   28 +-
 docs/originated.html                       |  505 +--
 docs/picks.html                            |  513 ++-
 docs/results.html                          |  125 +-
 docs/table.html                            |  235 +-
 docs/tournaments.html                      |  150 +-
 docs/unresolved.html                       |    6 +-
 32 files changed, 7681 insertions(+), 7632 deletions(-)
```

## python3 audit/verify_docs.py
```
PASS    1 docs/data/picks.json mirrors data/node/picks.json :: 1155210 bytes
PASS    2 every active match with a pick rendered on picks.html :: 61 picked rows, missing: []
PASS    3 rendered probabilities match JSON :: bad: []
PASS    4 every active match without a pick is on unresolved.html and index.html :: 3 unresolved, missing: []
PASS    5 every rendered card links its Hotspawn match card :: missing: []
PASS    6 market rows carry all matched venue source links :: 2 market rows, missing: []
PASS    7 results.html renders only official scores (no fabricated fills) :: 298 ended/forfeited checked, bad: []
PASS    8 no ledger entry with an official result renders as pending :: bad: []
PASS    9 navigation on every docs page :: []
PASS  9.1 exec summary links every picks view & subpage :: []
PASS   10 no broken internal links or fragments in docs/ :: []
PASS   11 probabilities sum to 100% and pick = argmax :: bad: []
PASS   12 all scheduled matches rendered 1:1 on docs/table.html with source links :: 157 scheduled rows, missing: []
PASS   13 all 10 docs/*.html category pages exist with mobile viewport :: missing=[] no_vp=[]
PASS   14 no '(Kills)' derivative market used as a match line :: []
PASS   15 cross-region homonym quarantines (#1083097, #1079031) & Solid Gaming DQ walkovers verified :: []
PASS   16 every Flagged for Review item renders with Hotspawn + official source links :: 14 flags, bad=[]

rows: 486 total | scheduled 157 | active 64 (61 with pick, 3 unresolved) | ended/forfeited 298 | flags 14 | ledger 374 entries

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
note: #1081423 is no longer scheduled — LCP 2027 Promotion pick assertion skipped
PASS session_6669f798 test_node_pipeline.mjs: 157 scheduled, 2 market rows (8 venue quotes joined, 0 single-venue fallback), OOS Brier=0.2251
exit=0
```

## python3 audit/verify_docs_parity.py
```
PASS    1 no docs page reuses a canonical title and every docs title says 'secondary' :: reused: []; unmarked: []
PASS    2 secondary banner is first in <body> and every page links the canonical hub :: banner not first: []; no canonical link: []
PASS    3 reconciliation + overview numbers reproduce both committed snapshots :: reconcile section: True; missing: []; oos series rendered: 22,586
PASS    4 every scheduled row deep-links to a canonical anchor that exists :: 157 rows; missing link: []; dead anchor: []
PASS    5 fixtures absent from the canonical snapshot are explained, not silently dropped :: unexplained: []
PASS    6 canonical probabilities rendered in docs/ equal data/matches.json :: mismatched: []
PASS    7 divergences (>= 5 pp or opposite pick) are marked and listed :: 20 divergent fixtures; unmarked rows: []; missing from overview ledger: []
PASS    8 no series format is rendered that Hotspawn does not publish :: 157 rows have best_of=null in the feed; bad renders: []
PASS    9 internal links and fragments resolve (including ../ into the root site) :: broken: []
PASS   10 methodology documents the canonical relationship and the unpublished series format :: missing: []
WARN      canonical cards missing from the secondary snapshot :: 99

scheduled rows: 157 | shared with canonical: 113 | both priced: 106 | divergent: 20 | mean gap 2.512 pp | max gap 11.29 pp

ALL DOCS-PARITY CHECKS PASS
exit=0
```
