# refresh-docs verification output

run 42373436671 attempt 1 · commit `687e3a783dfc04159ee492c31c45188efa7fbecf` · 2026-11-07T12:39:35Z

## freshly generated snapshot
```
generated_at 2026-11-07T12:39:35.264Z | raw feed 2026-11-07T12:39:28.220Z
counts {"total_rows":530,"scheduled_total":186,"active_open_locked":99,"stale_scheduled":87,"ended_recent":290,"forfeited_recent":12,"cancelled_recent":42,"active_market":2,"active_model":81,"active_unresolved":16,"scheduled_market":2,"scheduled_model":161,"scheduled_walkover_settlement":4,"scheduled_unresolved":19,"by_source_scheduled":{"model":113,"walkover_settlement":4,"model_provisional":48,"unresolved":19,"market_consensus":2},"by_source_active":{"model":65,"model_provisional":16,"market_consensus":2,"unresolved":16},"flags":27}
calibration {"n":22495,"brier":0.2251,"series":32687}
rows 530 | scheduled 186
market rows: 1094932:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Smarkets (UKGC)] 1130194:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Smarkets (UKGC)]
scheduled rows with best_of != null: 0
flags 27 | dq-walkover-1071170 unverified-zero-history-1074627 dq-walkover-1071200 dq-walkover-1071206 dq-walkover-1071186 unverified-zero-history-1082002 unverified-zero-history-1083593 entity-collision-1079053 unverified-zero-history-1130130 unverified-zero-history-1130131 unverified-zero-history-1130132 unverified-zero-history-1130133 unverified-zero-history-1130134 unverified-zero-history-1130135 unverified-zero-history-1130136 unverified-zero-history-1130137 unverified-zero-history-1130138 unverified-zero-history-1130139 unverified-zero-history-1130140 unverified-zero-history-1130141 unverified-zero-history-1130142 unverified-zero-history-1130706 entity-collision-1079057 unverified-zero-history-1130143 unverified-zero-history-1130144 org-pooling-rich-gang-prm3 series-format-not-published
```

## git diff --stat of this run's output
```
 data/node/raw/bovada_lol.json              |    2 +-
 data/node/raw/collect_log.json             |   38 +-
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
 docs/data/picks.csv                        |   27 +-
 docs/data/picks.json                       | 2126 +++++++++++++++++-----------
 docs/featured.html                         |  100 +-
 docs/flagged.html                          |   21 +-
 docs/index.html                            |  184 +--
 docs/methodology.html                      |   30 +-
 docs/originated.html                       |  356 +++--
 docs/picks.html                            |  393 +++--
 docs/results.html                          |  167 ++-
 docs/table.html                            |  195 +--
 docs/tournaments.html                      |  330 +++--
 docs/unresolved.html                       |   32 +-
 32 files changed, 4255 insertions(+), 2774 deletions(-)
```

## python3 audit/verify_docs.py
```
PASS    1 docs/data/picks.json mirrors data/node/picks.json :: 1261908 bytes
PASS    2 every active match with a pick rendered on picks.html :: 83 picked rows, missing: []
PASS    3 rendered probabilities match JSON :: bad: []
PASS    4 every active match without a pick is on unresolved.html and index.html :: 16 unresolved, missing: []
PASS    5 every rendered card links its Hotspawn match card :: missing: []
PASS    6 market rows carry all matched venue source links :: 2 market rows, missing: []
PASS    7 results.html renders only official scores (no fabricated fills) :: 302 ended/forfeited checked, bad: []
PASS    8 no ledger entry with an official result renders as pending :: bad: []
PASS    9 navigation on every docs page :: []
PASS  9.1 exec summary links every picks view & subpage :: []
PASS   10 no broken internal links or fragments in docs/ :: []
PASS   11 probabilities sum to 100% and pick = argmax :: bad: []
PASS   12 all scheduled matches rendered 1:1 on docs/table.html with source links :: 186 scheduled rows, missing: []
PASS   13 all 10 docs/*.html category pages exist with mobile viewport :: missing=[] no_vp=[]
PASS   14 no '(Kills)' derivative market used as a match line :: []
PASS   15 cross-region homonym quarantines (#1083097, #1079031) & Solid Gaming DQ walkovers verified :: []
PASS   16 every Flagged for Review item renders with Hotspawn + official source links :: 27 flags, bad=[]

rows: 530 total | scheduled 186 | active 99 (83 with pick, 16 unresolved) | ended/forfeited 302 | flags 27 | ledger 340 entries

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
PASS session_6669f798 test_node_pipeline.mjs: 186 scheduled, 2 market rows (10 venue quotes joined, 0 single-venue fallback), OOS Brier=0.2251
exit=0
```

## python3 audit/verify_docs_parity.py
```
PASS    1 no docs page reuses a canonical title and every docs title says 'secondary' :: reused: []; unmarked: []
PASS    2 secondary banner is first in <body> and every page links the canonical hub :: banner not first: []; no canonical link: []
PASS    3 reconciliation + overview numbers reproduce both committed snapshots :: reconcile section: True; missing: []; oos series rendered: 22,495
PASS    4 every scheduled row deep-links to a canonical anchor that exists :: 186 rows; missing link: []; dead anchor: []
PASS    5 fixtures absent from the canonical snapshot are explained, not silently dropped :: unexplained: []
PASS    6 canonical probabilities rendered in docs/ equal data/matches.json :: mismatched: []
PASS    7 divergences (>= 5 pp or opposite pick) are marked and listed :: 26 divergent fixtures; unmarked rows: []; missing from overview ledger: []
PASS    8 no series format is rendered that Hotspawn does not publish :: 186 rows have best_of=null in the feed; bad renders: []
PASS    9 internal links and fragments resolve (including ../ into the root site) :: broken: []
PASS   10 methodology documents the canonical relationship and the unpublished series format :: missing: []
WARN      canonical cards missing from the secondary snapshot :: 75

scheduled rows: 186 | shared with canonical: 137 | both priced: 130 | divergent: 26 | mean gap 2.729 pp | max gap 9.99 pp

ALL DOCS-PARITY CHECKS PASS
exit=0
```
