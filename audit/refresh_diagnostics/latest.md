# refresh-docs verification output

run 43561756420 attempt 1 · commit `e5521bbd1f9273ece87a0e710f859dbf9f9ac785` · 2026-11-14T05:29:44Z

## freshly generated snapshot
```
generated_at 2026-11-14T05:29:43.862Z | raw feed 2026-11-14T05:29:35.516Z
counts {"total_rows":437,"scheduled_total":149,"active_open_locked":54,"stale_scheduled":95,"ended_recent":258,"forfeited_recent":3,"cancelled_recent":27,"active_market":1,"active_model":50,"active_unresolved":3,"scheduled_market":1,"scheduled_model":138,"scheduled_walkover_settlement":4,"scheduled_unresolved":6,"by_source_scheduled":{"model":92,"walkover_settlement":4,"model_provisional":46,"unresolved":6,"market_consensus":1},"by_source_active":{"model_provisional":12,"model":38,"unresolved":3,"market_consensus":1},"flags":12}
calibration {"n":22603,"brier":0.2251,"series":32852}
rows 437 | scheduled 149
market rows: 1094982:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Smarkets (UKGC)]
scheduled rows with best_of != null: 0
flags 12 | dq-walkover-1071170 unverified-zero-history-1074627 dq-walkover-1071200 dq-walkover-1071206 dq-walkover-1071186 unverified-zero-history-1082002 unverified-zero-history-1083593 unverified-zero-history-1131686 unverified-zero-history-1131687 unverified-zero-history-1132746 org-pooling-rich-gang-prm3 series-format-not-published
```

## git diff --stat of this run's output
```
 data/node/raw/bovada_lol.json              |    2 +-
 data/node/raw/collect_log.json             |   28 +-
 data/node/raw/hotspawn_lobby_check.json    |    2 +-
 data/node/raw/hotspawn_lol_fixtures.json   |    2 +-
 data/node/raw/kalshi_lol.json              |    2 +-
 data/node/raw/kambi_lol.json               |    2 +-
 data/node/raw/pinnacle_lol.json            |    2 +-
 data/node/raw/pinnacle_matchups_cache.json |    2 +-
 data/node/raw/polymarket_lol.json          |    2 +-
 data/node/raw/smarkets_lol.json            |    2 +-
 docs/data/canonical_snapshot.json          |    2 +-
 docs/data/flags.json                       |   30 +-
 docs/data/picks.csv                        |   20 +-
 docs/data/picks.json                       | 5746 ++++++++++++++--------------
 docs/featured.html                         |   22 +-
 docs/flagged.html                          |   32 +-
 docs/index.html                            |   60 +-
 docs/methodology.html                      |   30 +-
 docs/originated.html                       |  329 +-
 docs/picks.html                            |  308 +-
 docs/results.html                          |  207 +-
 docs/table.html                            |  156 +-
 docs/tournaments.html                      |  114 +-
 docs/unresolved.html                       |   32 +-
 32 files changed, 6729 insertions(+), 7029 deletions(-)
```

## python3 audit/verify_docs.py
```
PASS    1 docs/data/picks.json mirrors data/node/picks.json :: 1035811 bytes
PASS    2 every active match with a pick rendered on picks.html :: 51 picked rows, missing: []
PASS    3 rendered probabilities match JSON :: bad: []
PASS    4 every active match without a pick is on unresolved.html and index.html :: 3 unresolved, missing: []
PASS    5 every rendered card links its Hotspawn match card :: missing: []
PASS    6 market rows carry all matched venue source links :: 1 market rows, missing: []
PASS    7 results.html renders only official scores (no fabricated fills) :: 261 ended/forfeited checked, bad: []
PASS    8 no ledger entry with an official result renders as pending :: bad: []
PASS    9 navigation on every docs page :: []
PASS  9.1 exec summary links every picks view & subpage :: []
PASS   10 no broken internal links or fragments in docs/ :: []
PASS   11 probabilities sum to 100% and pick = argmax :: bad: []
PASS   12 all scheduled matches rendered 1:1 on docs/table.html with source links :: 149 scheduled rows, missing: []
PASS   13 all 10 docs/*.html category pages exist with mobile viewport :: missing=[] no_vp=[]
PASS   14 no '(Kills)' derivative market used as a match line :: []
PASS   15 cross-region homonym quarantines (#1083097, #1079031) & Solid Gaming DQ walkovers verified :: []
PASS   16 every Flagged for Review item renders with Hotspawn + official source links :: 12 flags, bad=[]

rows: 437 total | scheduled 149 | active 54 (51 with pick, 3 unresolved) | ended/forfeited 261 | flags 12 | ledger 383 entries

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
PASS session_6669f798 test_node_pipeline.mjs: 149 scheduled, 1 market rows (5 venue quotes joined, 0 single-venue fallback), OOS Brier=0.2251
exit=0
```

## python3 audit/verify_docs_parity.py
```
PASS    1 no docs page reuses a canonical title and every docs title says 'secondary' :: reused: []; unmarked: []
PASS    2 secondary banner is first in <body> and every page links the canonical hub :: banner not first: []; no canonical link: []
PASS    3 reconciliation + overview numbers reproduce both committed snapshots :: reconcile section: True; missing: []; oos series rendered: 22,603
PASS    4 every scheduled row deep-links to a canonical anchor that exists :: 149 rows; missing link: []; dead anchor: []
PASS    5 fixtures absent from the canonical snapshot are explained, not silently dropped :: unexplained: []
PASS    6 canonical probabilities rendered in docs/ equal data/matches.json :: mismatched: []
PASS    7 divergences (>= 5 pp or opposite pick) are marked and listed :: 19 divergent fixtures; unmarked rows: []; missing from overview ledger: []
PASS    8 no series format is rendered that Hotspawn does not publish :: 149 rows have best_of=null in the feed; bad renders: []
PASS    9 internal links and fragments resolve (including ../ into the root site) :: broken: []
PASS   10 methodology documents the canonical relationship and the unpublished series format :: missing: []
WARN      canonical cards missing from the secondary snapshot :: 105

scheduled rows: 149 | shared with canonical: 107 | both priced: 100 | divergent: 19 | mean gap 2.463 pp | max gap 9.76 pp

ALL DOCS-PARITY CHECKS PASS
exit=0
```
