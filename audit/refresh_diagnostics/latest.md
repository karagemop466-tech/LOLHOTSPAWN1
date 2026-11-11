# refresh-docs verification output

run 42964345845 attempt 1 · commit `1174026a063039ef697d7a9d3f79bfe4b7e3a60a` · 2026-11-11T05:13:56Z

## freshly generated snapshot
```
generated_at 2026-11-11T05:13:55.642Z | raw feed 2026-11-11T05:13:48.495Z
counts {"total_rows":491,"scheduled_total":170,"active_open_locked":72,"stale_scheduled":98,"ended_recent":284,"forfeited_recent":6,"cancelled_recent":31,"active_market":3,"active_model":66,"active_unresolved":3,"scheduled_market":3,"scheduled_model":157,"scheduled_walkover_settlement":4,"scheduled_unresolved":6,"by_source_scheduled":{"model":99,"walkover_settlement":4,"model_provisional":58,"unresolved":6,"market_consensus":3},"by_source_active":{"model_provisional":24,"market_consensus":3,"model":42,"unresolved":3},"flags":14}
calibration {"n":22573,"brier":0.2251,"series":32815}
rows 491 | scheduled 170
market rows: 1081423:4[Pinnacle+Unibet (Kambi)+Kalshi CFTC+Polymarket] 1081424:3[Unibet (Kambi)+Polymarket+Kalshi CFTC] 1094982:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Smarkets (UKGC)]
scheduled rows with best_of != null: 0
flags 14 | dq-walkover-1071170 unverified-zero-history-1074627 dq-walkover-1071200 dq-walkover-1071206 dq-walkover-1071186 unverified-zero-history-1082002 unverified-zero-history-1083593 venue-divergence-1081423 unverified-zero-history-1130706 entity-collision-1079057 unverified-zero-history-1131686 unverified-zero-history-1131687 org-pooling-rich-gang-prm3 series-format-not-published
```

## git diff --stat of this run's output
```
 data/node/raw/bovada_lol.json              |     2 +-
 data/node/raw/collect_log.json             |    42 +-
 data/node/raw/hotspawn_lobby_check.json    |     2 +-
 data/node/raw/hotspawn_lol_fixtures.json   |     2 +-
 data/node/raw/kalshi_lol.json              |     2 +-
 data/node/raw/kambi_lol.json               |     2 +-
 data/node/raw/pinnacle_lol.json            |     2 +-
 data/node/raw/pinnacle_matchups_cache.json |     2 +-
 data/node/raw/polymarket_lol.json          |     2 +-
 data/node/raw/smarkets_lol.json            |     2 +-
 docs/data/canonical_snapshot.json          |     2 +-
 docs/data/flags.json                       |   218 +-
 docs/data/picks.csv                        |   145 +-
 docs/data/picks.json                       | 33951 +++++++++++++--------------
 docs/featured.html                         |   152 +-
 docs/flagged.html                          |   191 +-
 docs/index.html                            |   594 +-
 docs/methodology.html                      |    60 +-
 docs/originated.html                       |  2258 +-
 docs/picks.html                            |  2046 +-
 docs/results.html                          |  1390 +-
 docs/table.html                            |  1133 +-
 docs/tournaments.html                      |   990 +-
 docs/unresolved.html                       |   358 +-
 32 files changed, 39617 insertions(+), 42673 deletions(-)
```

## python3 audit/verify_docs.py
```
PASS    1 docs/data/picks.json mirrors data/node/picks.json :: 1171111 bytes
PASS    2 every active match with a pick rendered on picks.html :: 69 picked rows, missing: []
PASS    3 rendered probabilities match JSON :: bad: []
PASS    4 every active match without a pick is on unresolved.html and index.html :: 3 unresolved, missing: []
PASS    5 every rendered card links its Hotspawn match card :: missing: []
PASS    6 market rows carry all matched venue source links :: 3 market rows, missing: []
PASS    7 results.html renders only official scores (no fabricated fills) :: 290 ended/forfeited checked, bad: []
PASS    8 no ledger entry with an official result renders as pending :: bad: []
PASS    9 navigation on every docs page :: []
PASS  9.1 exec summary links every picks view & subpage :: []
PASS   10 no broken internal links or fragments in docs/ :: []
PASS   11 probabilities sum to 100% and pick = argmax :: bad: []
PASS   12 all scheduled matches rendered 1:1 on docs/table.html with source links :: 170 scheduled rows, missing: []
PASS   13 all 10 docs/*.html category pages exist with mobile viewport :: missing=[] no_vp=[]
PASS   14 no '(Kills)' derivative market used as a match line :: []
PASS   15 cross-region homonym quarantines (#1083097, #1079031) & Solid Gaming DQ walkovers verified :: []
PASS   16 every Flagged for Review item renders with Hotspawn + official source links :: 14 flags, bad=[]

rows: 491 total | scheduled 170 | active 72 (69 with pick, 3 unresolved) | ended/forfeited 290 | flags 14 | ledger 377 entries

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
node:internal/modules/run_main:123
    triggerUncaughtException(
    ^

AssertionError [ERR_ASSERTION]: #1081423 Frank Esports favored on pre-kickoff Elo
+ actual - expected

+ 'Ground Zero Gaming'
- 'Frank Esports'
    at file:///home/runner/work/LOLHOTSPAWN1/LOLHOTSPAWN1/audit/session_6669f798/test_node_pipeline.mjs:124:10 {
  generatedMessage: false,
  code: 'ERR_ASSERTION',
  actual: 'Ground Zero Gaming',
  expected: 'Frank Esports',
  operator: 'strictEqual'
}

Node.js v20.20.2
exit=1
```

## python3 audit/verify_docs_parity.py
```
PASS    1 no docs page reuses a canonical title and every docs title says 'secondary' :: reused: []; unmarked: []
PASS    2 secondary banner is first in <body> and every page links the canonical hub :: banner not first: []; no canonical link: []
PASS    3 reconciliation + overview numbers reproduce both committed snapshots :: reconcile section: True; missing: []; oos series rendered: 22,573
PASS    4 every scheduled row deep-links to a canonical anchor that exists :: 170 rows; missing link: []; dead anchor: []
PASS    5 fixtures absent from the canonical snapshot are explained, not silently dropped :: unexplained: []
PASS    6 canonical probabilities rendered in docs/ equal data/matches.json :: mismatched: []
PASS    7 divergences (>= 5 pp or opposite pick) are marked and listed :: 23 divergent fixtures; unmarked rows: []; missing from overview ledger: []
PASS    8 no series format is rendered that Hotspawn does not publish :: 170 rows have best_of=null in the feed; bad renders: []
PASS    9 internal links and fragments resolve (including ../ into the root site) :: broken: []
PASS   10 methodology documents the canonical relationship and the unpublished series format :: missing: []
WARN      canonical cards missing from the secondary snapshot :: 92

scheduled rows: 170 | shared with canonical: 120 | both priced: 113 | divergent: 23 | mean gap 3.066 pp | max gap 58.75 pp

ALL DOCS-PARITY CHECKS PASS
exit=0
```
