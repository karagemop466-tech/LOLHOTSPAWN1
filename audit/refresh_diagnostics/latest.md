# refresh-docs verification output

run 42919142681 attempt 1 · commit `efc101bf1c7aedc4dcd7991ed4f3efe7da02efca` · 2026-11-10T22:57:27Z

## freshly generated snapshot
```
generated_at 2026-11-10T22:57:27.112Z | raw feed 2026-11-10T22:57:18.658Z
counts {"total_rows":487,"scheduled_total":173,"active_open_locked":73,"stale_scheduled":100,"ended_recent":278,"forfeited_recent":5,"cancelled_recent":31,"active_market":3,"active_model":67,"active_unresolved":3,"scheduled_market":3,"scheduled_model":156,"scheduled_walkover_settlement":4,"scheduled_unresolved":10,"by_source_scheduled":{"model":98,"walkover_settlement":4,"model_provisional":58,"unresolved":10,"market_consensus":3},"by_source_active":{"model":46,"model_provisional":21,"market_consensus":3,"unresolved":3},"flags":18}
calibration {"n":22573,"brier":0.2251,"series":32809}
rows 487 | scheduled 173
market rows: 1081423:3[Unibet (Kambi)+Kalshi CFTC+Polymarket] 1081424:2[Polymarket+Kalshi CFTC] 1094982:5[Pinnacle+Unibet (Kambi)+Polymarket+Kalshi CFTC+Smarkets (UKGC)]
scheduled rows with best_of != null: 0
flags 18 | dq-walkover-1071170 unverified-zero-history-1074627 dq-walkover-1071200 dq-walkover-1071206 dq-walkover-1071186 unverified-zero-history-1082002 unverified-zero-history-1083593 unverified-zero-history-1131854 unverified-zero-history-1131855 unverified-zero-history-1131856 unverified-zero-history-1131857 venue-divergence-1081423 unverified-zero-history-1130706 entity-collision-1079057 unverified-zero-history-1131686 unverified-zero-history-1131687 org-pooling-rich-gang-prm3 series-format-not-published
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
 docs/data/flags.json                       |   242 +-
 docs/data/picks.csv                        |   148 +-
 docs/data/picks.json                       | 34027 +++++++++++++--------------
 docs/featured.html                         |   148 +-
 docs/flagged.html                          |   195 +-
 docs/index.html                            |   596 +-
 docs/methodology.html                      |    60 +-
 docs/originated.html                       |  2203 +-
 docs/picks.html                            |  2021 +-
 docs/results.html                          |  1341 +-
 docs/table.html                            |  1112 +-
 docs/tournaments.html                      |   998 +-
 docs/unresolved.html                       |   456 +-
 32 files changed, 39345 insertions(+), 43002 deletions(-)
```

## python3 audit/verify_docs.py
```
PASS    1 docs/data/picks.json mirrors data/node/picks.json :: 1159053 bytes
PASS    2 every active match with a pick rendered on picks.html :: 70 picked rows, missing: []
PASS    3 rendered probabilities match JSON :: bad: []
PASS    4 every active match without a pick is on unresolved.html and index.html :: 3 unresolved, missing: []
PASS    5 every rendered card links its Hotspawn match card :: missing: []
PASS    6 market rows carry all matched venue source links :: 3 market rows, missing: []
PASS    7 results.html renders only official scores (no fabricated fills) :: 283 ended/forfeited checked, bad: []
PASS    8 no ledger entry with an official result renders as pending :: bad: []
PASS    9 navigation on every docs page :: []
PASS  9.1 exec summary links every picks view & subpage :: []
PASS   10 no broken internal links or fragments in docs/ :: []
PASS   11 probabilities sum to 100% and pick = argmax :: bad: []
PASS   12 all scheduled matches rendered 1:1 on docs/table.html with source links :: 173 scheduled rows, missing: []
PASS   13 all 10 docs/*.html category pages exist with mobile viewport :: missing=[] no_vp=[]
PASS   14 no '(Kills)' derivative market used as a match line :: []
PASS   15 cross-region homonym quarantines (#1083097, #1079031) & Solid Gaming DQ walkovers verified :: []
PASS   16 every Flagged for Review item renders with Hotspawn + official source links :: 18 flags, bad=[]

rows: 487 total | scheduled 173 | active 73 (70 with pick, 3 unresolved) | ended/forfeited 283 | flags 18 | ledger 374 entries

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
PASS    4 every scheduled row deep-links to a canonical anchor that exists :: 173 rows; missing link: []; dead anchor: []
PASS    5 fixtures absent from the canonical snapshot are explained, not silently dropped :: unexplained: []
PASS    6 canonical probabilities rendered in docs/ equal data/matches.json :: mismatched: []
PASS    7 divergences (>= 5 pp or opposite pick) are marked and listed :: 23 divergent fixtures; unmarked rows: []; missing from overview ledger: []
PASS    8 no series format is rendered that Hotspawn does not publish :: 173 rows have best_of=null in the feed; bad renders: []
PASS    9 internal links and fragments resolve (including ../ into the root site) :: broken: []
PASS   10 methodology documents the canonical relationship and the unpublished series format :: missing: []
WARN      canonical cards missing from the secondary snapshot :: 92

scheduled rows: 173 | shared with canonical: 120 | both priced: 113 | divergent: 23 | mean gap 3.042 pp | max gap 56.05 pp

ALL DOCS-PARITY CHECKS PASS
exit=0
```
