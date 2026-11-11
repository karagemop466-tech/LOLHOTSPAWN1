# refresh-docs verification output

run 43032053457 attempt 1 · commit `767811e822a07ba76e2c604e387349270c98fdce` · 2026-11-11T13:46:07Z

## freshly generated snapshot
```
generated_at 2026-11-11T13:46:06.685Z | raw feed 2026-11-11T13:45:58.684Z
counts {"total_rows":493,"scheduled_total":167,"active_open_locked":73,"stale_scheduled":94,"ended_recent":289,"forfeited_recent":6,"cancelled_recent":31,"active_market":3,"active_model":67,"active_unresolved":3,"scheduled_market":3,"scheduled_model":154,"scheduled_walkover_settlement":4,"scheduled_unresolved":6,"by_source_scheduled":{"model":96,"walkover_settlement":4,"model_provisional":58,"unresolved":6,"market_consensus":3},"by_source_active":{"market_consensus":3,"model":44,"model_provisional":23,"unresolved":3},"flags":14}
calibration {"n":22578,"brier":0.2251,"series":32820}
rows 493 | scheduled 167
market rows: 1081423:2[Polymarket+Kalshi CFTC] 1081424:3[Unibet (Kambi)+Polymarket+Kalshi CFTC] 1094982:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Smarkets (UKGC)]
scheduled rows with best_of != null: 0
flags 14 | dq-walkover-1071170 unverified-zero-history-1074627 dq-walkover-1071200 dq-walkover-1071206 dq-walkover-1071186 unverified-zero-history-1082002 unverified-zero-history-1083593 venue-divergence-1081424 unverified-zero-history-1130706 entity-collision-1079057 unverified-zero-history-1131686 unverified-zero-history-1131687 org-pooling-rich-gang-prm3 series-format-not-published
```

## git diff --stat of this run's output
```
 data/node/raw/bovada_lol.json              |     2 +-
 data/node/raw/collect_log.json             |    48 +-
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
 docs/data/picks.csv                        |   150 +-
 docs/data/picks.json                       | 34645 +++++++++++++--------------
 docs/featured.html                         |   150 +-
 docs/flagged.html                          |   191 +-
 docs/index.html                            |   622 +-
 docs/methodology.html                      |    64 +-
 docs/originated.html                       |  2179 +-
 docs/picks.html                            |  1985 +-
 docs/results.html                          |  1481 +-
 docs/table.html                            |  1192 +-
 docs/tournaments.html                      |  1012 +-
 docs/unresolved.html                       |   358 +-
 32 files changed, 40410 insertions(+), 43511 deletions(-)
```

## python3 audit/verify_docs.py
```
PASS    1 docs/data/picks.json mirrors data/node/picks.json :: 1173061 bytes
PASS    2 every active match with a pick rendered on picks.html :: 70 picked rows, missing: []
PASS    3 rendered probabilities match JSON :: bad: []
PASS    4 every active match without a pick is on unresolved.html and index.html :: 3 unresolved, missing: []
PASS    5 every rendered card links its Hotspawn match card :: missing: []
PASS    6 market rows carry all matched venue source links :: 3 market rows, missing: []
PASS    7 results.html renders only official scores (no fabricated fills) :: 295 ended/forfeited checked, bad: []
PASS    8 no ledger entry with an official result renders as pending :: bad: []
PASS    9 navigation on every docs page :: []
PASS  9.1 exec summary links every picks view & subpage :: []
PASS   10 no broken internal links or fragments in docs/ :: []
PASS   11 probabilities sum to 100% and pick = argmax :: bad: []
PASS   12 all scheduled matches rendered 1:1 on docs/table.html with source links :: 167 scheduled rows, missing: []
PASS   13 all 10 docs/*.html category pages exist with mobile viewport :: missing=[] no_vp=[]
PASS   14 no '(Kills)' derivative market used as a match line :: []
PASS   15 cross-region homonym quarantines (#1083097, #1079031) & Solid Gaming DQ walkovers verified :: []
PASS   16 every Flagged for Review item renders with Hotspawn + official source links :: 14 flags, bad=[]

rows: 493 total | scheduled 167 | active 73 (70 with pick, 3 unresolved) | ended/forfeited 295 | flags 14 | ledger 374 entries

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
WARNING: 1 market row(s) are priced from quotes observed after kick-off (in-play): 1081423(13:46Z vs kick-off 09:00Z) - disclosed on the pages, logged for the pipeline owner
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
PASS    3 reconciliation + overview numbers reproduce both committed snapshots :: reconcile section: True; missing: []; oos series rendered: 22,578
PASS    4 every scheduled row deep-links to a canonical anchor that exists :: 167 rows; missing link: []; dead anchor: []
PASS    5 fixtures absent from the canonical snapshot are explained, not silently dropped :: unexplained: []
PASS    6 canonical probabilities rendered in docs/ equal data/matches.json :: mismatched: []
PASS    7 divergences (>= 5 pp or opposite pick) are marked and listed :: 21 divergent fixtures; unmarked rows: []; missing from overview ledger: []
PASS    8 no series format is rendered that Hotspawn does not publish :: 167 rows have best_of=null in the feed; bad renders: []
PASS    9 internal links and fragments resolve (including ../ into the root site) :: broken: []
PASS   10 methodology documents the canonical relationship and the unpublished series format :: missing: []
WARN      canonical cards missing from the secondary snapshot :: 95

scheduled rows: 167 | shared with canonical: 117 | both priced: 110 | divergent: 21 | mean gap 2.945 pp | max gap 43.55 pp

ALL DOCS-PARITY CHECKS PASS
exit=0
```
