# refresh-docs verification output

run 41467563540 attempt 1 · commit `d43e6178b292a3f31840bbc007a79dd3f7469c84` · 2026-11-02T15:02:14Z

## freshly generated snapshot
```
generated_at 2026-11-02T15:02:13.710Z | raw feed 2026-11-02T15:02:04.121Z
counts {"total_rows":517,"scheduled_total":174,"active_open_locked":84,"stale_scheduled":90,"ended_recent":289,"forfeited_recent":12,"cancelled_recent":42,"active_market":4,"active_model":80,"active_unresolved":0,"scheduled_market":4,"scheduled_model":163,"scheduled_walkover_settlement":4,"scheduled_unresolved":3,"by_source_scheduled":{"model":113,"walkover_settlement":4,"model_provisional":50,"unresolved":3,"market_consensus":4},"by_source_active":{"model":64,"model_provisional":16,"market_consensus":4},"flags":12}
calibration {"n":22464,"brier":0.2251,"series":32645}
rows 517 | scheduled 174
market rows: 1129387:4[Unibet (Kambi)+Polymarket+Kalshi CFTC+Smarkets (UKGC)] 1094919:4[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC] 1094917:3[Unibet (Kambi)+Polymarket+Kalshi CFTC] 1075825:3[Unibet (Kambi)+Polymarket+Kalshi CFTC]
scheduled rows with best_of != null: 0
flags 12 | dq-walkover-1071170 unverified-zero-history-1074627 dq-walkover-1071200 dq-walkover-1071206 dq-walkover-1071186 unverified-zero-history-1082002 unverified-zero-history-1083593 entity-collision-1082746 entity-collision-1079053 entity-collision-1079057 org-pooling-rich-gang-prm3 series-format-not-published
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
 docs/data/flags.json                       |    4 +-
 docs/data/picks.csv                        |   48 +-
 docs/data/picks.json                       | 1980 +++++++++++++++-------------
 docs/featured.html                         |   40 +-
 docs/flagged.html                          |    8 +-
 docs/index.html                            |  146 +-
 docs/methodology.html                      |   32 +-
 docs/originated.html                       |  510 +++----
 docs/picks.html                            |  309 +++--
 docs/results.html                          |  207 +--
 docs/table.html                            |  246 ++--
 docs/tournaments.html                      |  138 +-
 docs/unresolved.html                       |    6 +-
 32 files changed, 3431 insertions(+), 3323 deletions(-)
```

## python3 audit/verify_docs.py
```
PASS    1 docs/data/picks.json mirrors data/node/picks.json :: 1250197 bytes
PASS    2 every active match with a pick rendered on picks.html :: 84 picked rows, missing: []
PASS    3 rendered probabilities match JSON :: bad: []
PASS    4 every active match without a pick is on unresolved.html and index.html :: 0 unresolved, missing: []
PASS    5 every rendered card links its Hotspawn match card :: missing: []
PASS    6 market rows carry all matched venue source links :: 4 market rows, missing: []
PASS    7 results.html renders only official scores (no fabricated fills) :: 301 ended/forfeited checked, bad: []
PASS    8 no ledger entry with an official result renders as pending :: bad: []
PASS    9 navigation on every docs page :: []
PASS  9.1 exec summary links every picks view & subpage :: []
PASS   10 no broken internal links or fragments in docs/ :: []
PASS   11 probabilities sum to 100% and pick = argmax :: bad: []
PASS   12 all scheduled matches rendered 1:1 on docs/table.html with source links :: 174 scheduled rows, missing: []
PASS   13 all 10 docs/*.html category pages exist with mobile viewport :: missing=[] no_vp=[]
PASS   14 no '(Kills)' derivative market used as a match line :: []
PASS   15 cross-region homonym quarantines (#1083097, #1079031) & Solid Gaming DQ walkovers verified :: []
PASS   16 every Flagged for Review item renders with Hotspawn + official source links :: 12 flags, bad=[]

rows: 517 total | scheduled 174 | active 84 (84 with pick, 0 unresolved) | ended/forfeited 301 | flags 12 | ledger 309 entries

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
PASS session_6669f798 test_node_pipeline.mjs: 174 scheduled, 4 market rows (14 venue quotes joined, 0 single-venue fallback), OOS Brier=0.2251
exit=0
```

## python3 audit/verify_docs_parity.py
```
PASS    1 no docs page reuses a canonical title and every docs title says 'secondary' :: reused: []; unmarked: []
PASS    2 secondary banner is first in <body> and every page links the canonical hub :: banner not first: []; no canonical link: []
PASS    3 reconciliation + overview numbers reproduce both committed snapshots :: reconcile section: True; missing: []; oos series rendered: 22,464
PASS    4 every scheduled row deep-links to a canonical anchor that exists :: 174 rows; missing link: []; dead anchor: []
PASS    5 fixtures absent from the canonical snapshot are explained, not silently dropped :: unexplained: []
PASS    6 canonical probabilities rendered in docs/ equal data/matches.json :: mismatched: []
PASS    7 divergences (>= 5 pp or opposite pick) are marked and listed :: 28 divergent fixtures; unmarked rows: []; missing from overview ledger: []
PASS    8 no series format is rendered that Hotspawn does not publish :: 174 rows have best_of=null in the feed; bad renders: []
PASS    9 internal links and fragments resolve (including ../ into the root site) :: broken: []
PASS   10 methodology documents the canonical relationship and the unpublished series format :: missing: []
WARN      canonical cards missing from the secondary snapshot :: 52

scheduled rows: 174 | shared with canonical: 160 | both priced: 153 | divergent: 28 | mean gap 2.561 pp | max gap 9.76 pp

ALL DOCS-PARITY CHECKS PASS
exit=0
```
