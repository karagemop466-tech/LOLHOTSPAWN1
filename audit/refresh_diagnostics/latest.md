# refresh-docs verification output

run 41242314211 attempt 1 · commit `5caefe3eb898baaddba6f68e1723d43b4cc8c58c` · 2026-10-31T21:10:34Z

## freshly generated snapshot
```
generated_at 2026-10-31T21:10:33.615Z | raw feed 2026-10-31T21:10:25.517Z
counts {"total_rows":530,"scheduled_total":193,"active_open_locked":111,"stale_scheduled":82,"ended_recent":276,"forfeited_recent":15,"cancelled_recent":46,"active_market":3,"active_model":104,"active_unresolved":4,"scheduled_market":3,"scheduled_model":179,"scheduled_walkover_settlement":4,"scheduled_unresolved":7,"by_source_scheduled":{"model":127,"walkover_settlement":4,"model_provisional":52,"unresolved":7,"market_consensus":2,"market_polymarket":1},"by_source_active":{"model":83,"unresolved":4,"model_provisional":21,"market_consensus":2,"market_polymarket":1},"flags":17}
calibration {"n":22434,"brier":0.2251,"series":32609}
rows 530 | scheduled 193
market rows: 1094914:3[Pinnacle+Polymarket+Kalshi CFTC] 1094916:5[Pinnacle+Unibet (Kambi)+Polymarket+Smarkets (UKGC)+Kalshi CFTC] 1081423:1[Polymarket]
scheduled rows with best_of != null: 0
flags 17 | dq-walkover-1071170 unverified-zero-history-1074627 dq-walkover-1071200 dq-walkover-1071206 dq-walkover-1071186 unverified-zero-history-1082002 unverified-zero-history-1083593 unverified-zero-history-1121690 unverified-zero-history-1121692 unverified-zero-history-1121693 unverified-zero-history-1121694 venue-divergence-1094914 entity-collision-1082746 entity-collision-1079053 entity-collision-1079057 org-pooling-rich-gang-prm3 series-format-not-published
```

## git diff --stat of this run's output
```
 data/node/raw/bovada_lol.json              |    2 +-
 data/node/raw/collect_log.json             |   46 +-
 data/node/raw/hotspawn_lobby_check.json    |    2 +-
 data/node/raw/hotspawn_lol_fixtures.json   |    2 +-
 data/node/raw/kalshi_lol.json              |    2 +-
 data/node/raw/kambi_lol.json               |    2 +-
 data/node/raw/pinnacle_lol.json            |    2 +-
 data/node/raw/pinnacle_matchups_cache.json |    2 +-
 data/node/raw/polymarket_lol.json          |    2 +-
 data/node/raw/smarkets_lol.json            |    2 +-
 docs/data/canonical_snapshot.json          |    2 +-
 docs/data/flags.json                       |   78 +-
 docs/data/picks.csv                        |   29 +-
 docs/data/picks.json                       | 2592 +++-------------------------
 docs/featured.html                         |  142 +-
 docs/flagged.html                          |   76 +-
 docs/index.html                            |  194 +--
 docs/methodology.html                      |   24 +-
 docs/originated.html                       |  170 +-
 docs/picks.html                            |  193 +--
 docs/results.html                          |  171 +-
 docs/table.html                            |  167 +-
 docs/tournaments.html                      |  234 +--
 docs/unresolved.html                       |  132 +-
 32 files changed, 1259 insertions(+), 6214 deletions(-)
```

## python3 audit/verify_docs.py
```
PASS    1 docs/data/picks.json mirrors data/node/picks.json :: 1270107 bytes
PASS    2 every active match with a pick rendered on picks.html :: 107 picked rows, missing: []
PASS    3 rendered probabilities match JSON :: bad: []
PASS    4 every active match without a pick is on unresolved.html and index.html :: 4 unresolved, missing: []
PASS    5 every rendered card links its Hotspawn match card :: missing: []
PASS    6 market rows carry all matched venue source links :: 3 market rows, missing: []
PASS    7 results.html renders only official scores (no fabricated fills) :: 291 ended/forfeited checked, bad: []
PASS    8 no ledger entry with an official result renders as pending :: bad: []
PASS    9 navigation on every docs page :: []
PASS  9.1 exec summary links every picks view & subpage :: []
PASS   10 no broken internal links or fragments in docs/ :: []
PASS   11 probabilities sum to 100% and pick = argmax :: bad: []
PASS   12 all scheduled matches rendered 1:1 on docs/table.html with source links :: 193 scheduled rows, missing: []
PASS   13 all 10 docs/*.html category pages exist with mobile viewport :: missing=[] no_vp=[]
PASS   14 no '(Kills)' derivative market used as a match line :: []
PASS   15 cross-region homonym quarantines (#1083097, #1079031) & Solid Gaming DQ walkovers verified :: []
PASS   16 every Flagged for Review item renders with Hotspawn + official source links :: 17 flags, bad=[]

rows: 530 total | scheduled 193 | active 111 (107 with pick, 4 unresolved) | ended/forfeited 291 | flags 17 | ledger 294 entries

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
note: #1081423 is a single-venue fallback (Polymarket, quote 2026-10-31T21:10:27.542Z, 15110 min before kick-off) - no second venue was live once the card locked
WARNING: 1 market row(s) are priced from quotes observed after kick-off (in-play): 1094914(21:10Z vs kick-off 20:00Z) - disclosed on the pages, logged for the pipeline owner
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
PASS    3 reconciliation + overview numbers reproduce both committed snapshots :: reconcile section: True; missing: []; oos series rendered: 22,434
PASS    4 every scheduled row deep-links to a canonical anchor that exists :: 193 rows; missing link: []; dead anchor: []
PASS    5 fixtures absent from the canonical snapshot are explained, not silently dropped :: unexplained: []
PASS    6 canonical probabilities rendered in docs/ equal data/matches.json :: mismatched: []
PASS    7 divergences (>= 5 pp or opposite pick) are marked and listed :: 31 divergent fixtures; unmarked rows: []; missing from overview ledger: []
PASS    8 no series format is rendered that Hotspawn does not publish :: 193 rows have best_of=null in the feed; bad renders: []
PASS    9 internal links and fragments resolve (including ../ into the root site) :: broken: []
PASS   10 methodology documents the canonical relationship and the unpublished series format :: missing: []
WARN      canonical cards missing from the secondary snapshot :: 35

scheduled rows: 193 | shared with canonical: 177 | both priced: 170 | divergent: 31 | mean gap 2.659 pp | max gap 35.75 pp

ALL DOCS-PARITY CHECKS PASS
exit=0
```
