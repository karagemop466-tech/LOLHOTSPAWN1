# refresh-docs verification output

run 42229260526 attempt 1 · commit `363ba0623a3a800f3fd59a64e4bcd809ef0372eb` · 2026-11-06T13:54:39Z

## freshly generated snapshot
```
generated_at 2026-11-06T13:54:38.765Z | raw feed 2026-11-06T13:54:29.000Z
counts {"total_rows":534,"scheduled_total":188,"active_open_locked":101,"stale_scheduled":87,"ended_recent":290,"forfeited_recent":12,"cancelled_recent":44,"active_market":2,"active_model":84,"active_unresolved":15,"scheduled_market":2,"scheduled_model":164,"scheduled_walkover_settlement":4,"scheduled_unresolved":18,"by_source_scheduled":{"model":113,"walkover_settlement":4,"model_provisional":51,"unresolved":18,"market_consensus":2},"by_source_active":{"model_provisional":19,"model":65,"market_consensus":2,"unresolved":15},"flags":26}
calibration {"n":22486,"brier":0.2251,"series":32674}
rows 534 | scheduled 188
market rows: 1075825:5[Pinnacle+Unibet (Kambi)+Polymarket+Smarkets (UKGC)+Kalshi CFTC] 1094932:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Smarkets (UKGC)]
scheduled rows with best_of != null: 0
flags 26 | dq-walkover-1071170 unverified-zero-history-1074627 dq-walkover-1071200 dq-walkover-1071206 dq-walkover-1071186 unverified-zero-history-1082002 unverified-zero-history-1083593 entity-collision-1079053 unverified-zero-history-1130130 unverified-zero-history-1130131 unverified-zero-history-1130132 unverified-zero-history-1130133 unverified-zero-history-1130134 unverified-zero-history-1130135 unverified-zero-history-1130136 unverified-zero-history-1130137 unverified-zero-history-1130138 unverified-zero-history-1130139 unverified-zero-history-1130140 unverified-zero-history-1130141 unverified-zero-history-1130142 entity-collision-1079057 unverified-zero-history-1130143 unverified-zero-history-1130144 org-pooling-rich-gang-prm3 series-format-not-published
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
 docs/data/picks.csv                        |   37 +-
 docs/data/picks.json                       | 9571 ++++++++++++++--------------
 docs/featured.html                         |   40 +-
 docs/flagged.html                          |    8 +-
 docs/index.html                            |   96 +-
 docs/methodology.html                      |   30 +-
 docs/originated.html                       |  651 +-
 docs/picks.html                            |  500 +-
 docs/results.html                          |  166 +-
 docs/table.html                            |  265 +-
 docs/tournaments.html                      |  160 +-
 docs/unresolved.html                       |    6 +-
 32 files changed, 11272 insertions(+), 10930 deletions(-)
```

## python3 audit/verify_docs.py
```
PASS    1 docs/data/picks.json mirrors data/node/picks.json :: 1271705 bytes
PASS    2 every active match with a pick rendered on picks.html :: 86 picked rows, missing: []
PASS    3 rendered probabilities match JSON :: bad: []
PASS    4 every active match without a pick is on unresolved.html and index.html :: 15 unresolved, missing: []
PASS    5 every rendered card links its Hotspawn match card :: missing: []
PASS    6 market rows carry all matched venue source links :: 2 market rows, missing: []
PASS    7 results.html renders only official scores (no fabricated fills) :: 302 ended/forfeited checked, bad: []
PASS    8 no ledger entry with an official result renders as pending :: bad: []
PASS    9 navigation on every docs page :: []
PASS  9.1 exec summary links every picks view & subpage :: []
PASS   10 no broken internal links or fragments in docs/ :: []
PASS   11 probabilities sum to 100% and pick = argmax :: bad: []
PASS   12 all scheduled matches rendered 1:1 on docs/table.html with source links :: 188 scheduled rows, missing: []
PASS   13 all 10 docs/*.html category pages exist with mobile viewport :: missing=[] no_vp=[]
PASS   14 no '(Kills)' derivative market used as a match line :: []
PASS   15 cross-region homonym quarantines (#1083097, #1079031) & Solid Gaming DQ walkovers verified :: []
PASS   16 every Flagged for Review item renders with Hotspawn + official source links :: 26 flags, bad=[]

rows: 534 total | scheduled 188 | active 101 (86 with pick, 15 unresolved) | ended/forfeited 302 | flags 26 | ledger 333 entries

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
PASS session_6669f798 test_node_pipeline.mjs: 188 scheduled, 2 market rows (10 venue quotes joined, 0 single-venue fallback), OOS Brier=0.2251
exit=0
```

## python3 audit/verify_docs_parity.py
```
PASS    1 no docs page reuses a canonical title and every docs title says 'secondary' :: reused: []; unmarked: []
PASS    2 secondary banner is first in <body> and every page links the canonical hub :: banner not first: []; no canonical link: []
PASS    3 reconciliation + overview numbers reproduce both committed snapshots :: reconcile section: True; missing: []; oos series rendered: 22,486
PASS    4 every scheduled row deep-links to a canonical anchor that exists :: 188 rows; missing link: []; dead anchor: []
PASS    5 fixtures absent from the canonical snapshot are explained, not silently dropped :: unexplained: []
PASS    6 canonical probabilities rendered in docs/ equal data/matches.json :: mismatched: []
PASS    7 divergences (>= 5 pp or opposite pick) are marked and listed :: 26 divergent fixtures; unmarked rows: []; missing from overview ledger: []
PASS    8 no series format is rendered that Hotspawn does not publish :: 188 rows have best_of=null in the feed; bad renders: []
PASS    9 internal links and fragments resolve (including ../ into the root site) :: broken: []
PASS   10 methodology documents the canonical relationship and the unpublished series format :: missing: []
WARN      canonical cards missing from the secondary snapshot :: 70

scheduled rows: 188 | shared with canonical: 142 | both priced: 135 | divergent: 26 | mean gap 2.61 pp | max gap 9.99 pp

ALL DOCS-PARITY CHECKS PASS
exit=0
```
