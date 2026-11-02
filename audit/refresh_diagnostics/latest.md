# refresh-docs verification output

run 41391351439 attempt 1 · commit `c8ab3b7298f9acff7e3d265ab879e190b44ce850` · 2026-11-02T04:58:56Z

## freshly generated snapshot
```
generated_at 2026-11-02T04:58:55.522Z | raw feed 2026-11-02T04:58:46.731Z
counts {"total_rows":516,"scheduled_total":178,"active_open_locked":81,"stale_scheduled":97,"ended_recent":284,"forfeited_recent":12,"cancelled_recent":42,"active_market":4,"active_model":77,"active_unresolved":0,"scheduled_market":4,"scheduled_model":167,"scheduled_walkover_settlement":4,"scheduled_unresolved":3,"by_source_scheduled":{"model":116,"walkover_settlement":4,"model_provisional":51,"unresolved":3,"market_consensus":4},"by_source_active":{"model":61,"model_provisional":16,"market_consensus":4},"flags":12}
calibration {"n":22457,"brier":0.2251,"series":32638}
rows 516 | scheduled 178
market rows: 1129387:4[Unibet (Kambi)+Polymarket+Kalshi CFTC+Smarkets (UKGC)] 1094919:4[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC] 1094917:3[Unibet (Kambi)+Polymarket+Kalshi CFTC] 1075825:3[Unibet (Kambi)+Polymarket+Kalshi CFTC]
scheduled rows with best_of != null: 0
flags 12 | dq-walkover-1071170 unverified-zero-history-1074627 dq-walkover-1071200 dq-walkover-1071206 dq-walkover-1071186 unverified-zero-history-1082002 unverified-zero-history-1083593 entity-collision-1082746 entity-collision-1079053 entity-collision-1079057 org-pooling-rich-gang-prm3 series-format-not-published
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
 docs/data/picks.csv                        |   78 +-
 docs/data/picks.json                       | 3457 ++++++++++------------------
 docs/featured.html                         |   16 +-
 docs/flagged.html                          |    8 +-
 docs/index.html                            |   86 +-
 docs/methodology.html                      |   36 +-
 docs/originated.html                       |  660 ++----
 docs/picks.html                            | 1022 ++------
 docs/results.html                          |  375 ++-
 docs/table.html                            |  328 +--
 docs/tournaments.html                      |  301 +--
 docs/unresolved.html                       |    6 +-
 32 files changed, 3860 insertions(+), 7356 deletions(-)
```

## python3 audit/verify_docs.py
```
PASS    1 docs/data/picks.json mirrors data/node/picks.json :: 1247445 bytes
PASS    2 every active match with a pick rendered on picks.html :: 81 picked rows, missing: []
PASS    3 rendered probabilities match JSON :: bad: []
PASS    4 every active match without a pick is on unresolved.html and index.html :: 0 unresolved, missing: []
PASS    5 every rendered card links its Hotspawn match card :: missing: []
PASS    6 market rows carry all matched venue source links :: 4 market rows, missing: []
PASS    7 results.html renders only official scores (no fabricated fills) :: 296 ended/forfeited checked, bad: []
PASS    8 no ledger entry with an official result renders as pending :: bad: []
PASS    9 navigation on every docs page :: []
PASS  9.1 exec summary links every picks view & subpage :: []
PASS   10 no broken internal links or fragments in docs/ :: []
PASS   11 probabilities sum to 100% and pick = argmax :: bad: []
PASS   12 all scheduled matches rendered 1:1 on docs/table.html with source links :: 178 scheduled rows, missing: []
PASS   13 all 10 docs/*.html category pages exist with mobile viewport :: missing=[] no_vp=[]
PASS   14 no '(Kills)' derivative market used as a match line :: []
PASS   15 cross-region homonym quarantines (#1083097, #1079031) & Solid Gaming DQ walkovers verified :: []
PASS   16 every Flagged for Review item renders with Hotspawn + official source links :: 12 flags, bad=[]

rows: 516 total | scheduled 178 | active 81 (81 with pick, 0 unresolved) | ended/forfeited 296 | flags 12 | ledger 306 entries

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
PASS session_6669f798 test_node_pipeline.mjs: 178 scheduled, 4 market rows (14 venue quotes joined, 0 single-venue fallback), OOS Brier=0.2251
exit=0
```

## python3 audit/verify_docs_parity.py
```
PASS    1 no docs page reuses a canonical title and every docs title says 'secondary' :: reused: []; unmarked: []
PASS    2 secondary banner is first in <body> and every page links the canonical hub :: banner not first: []; no canonical link: []
PASS    3 reconciliation + overview numbers reproduce both committed snapshots :: reconcile section: True; missing: []; oos series rendered: 22,457
PASS    4 every scheduled row deep-links to a canonical anchor that exists :: 178 rows; missing link: []; dead anchor: []
PASS    5 fixtures absent from the canonical snapshot are explained, not silently dropped :: unexplained: []
PASS    6 canonical probabilities rendered in docs/ equal data/matches.json :: mismatched: []
PASS    7 divergences (>= 5 pp or opposite pick) are marked and listed :: 29 divergent fixtures; unmarked rows: []; missing from overview ledger: []
PASS    8 no series format is rendered that Hotspawn does not publish :: 178 rows have best_of=null in the feed; bad renders: []
PASS    9 internal links and fragments resolve (including ../ into the root site) :: broken: []
PASS   10 methodology documents the canonical relationship and the unpublished series format :: missing: []
WARN      canonical cards missing from the secondary snapshot :: 46

scheduled rows: 178 | shared with canonical: 166 | both priced: 159 | divergent: 29 | mean gap 2.546 pp | max gap 9.76 pp

ALL DOCS-PARITY CHECKS PASS
exit=0
```
