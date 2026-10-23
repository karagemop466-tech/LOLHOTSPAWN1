# COORDINATION.md — shared task board

Repo: `karagemop466-tech/LOLHOTSPAWN1` — Hotspawn League of Legends pick'em coverage, externally
sourced betting lines, self-originated win probabilities, and a GitHub Pages dashboard.

**Session IDs** are the short token in the branch name (`arena/<id>-lolhotspawn1`). Read this board
before touching shared files, claim a task, and keep your scope disjoint.

## Live state

| Item | Value |
|---|---|
| Published site | https://karagemop466-tech.github.io/LOLHOTSPAWN1/ (GitHub Pages, legacy build from `main` `/`) |
| Active pipeline | `tools/` (`collect.py` → `model.py` → `flags.py` → `site.py` → `verify.py`) |
| Refresh | `.github/workflows/refresh.yml`, cron `17 */6 * * *` (every 6 h, inside the 4–8 h brief) |
| Gate | `tools/verify.py` fails the build instead of publishing bad data |
| Integration session | `b166e06b` |
| Current session | `64554333` (branch `arena/64554333-lolhotspawn1`) |

## Session `64554333` — claim (opened 2026-10-23T15:40Z)

Scope (disjoint from every earlier session; all earlier tasks are `done`):

| # | Task | Status | Owner | File scope |
|---|------|--------|-------|-----------|
| 9 | Fix mobile navigation + picks filter (dead `Menu` button, `#q`/`#comp` filter JS bound to non-existent ids) | done | 64554333 | `assets/app.js`, `assets/style.css`, `tools/site.py` |
| 10 | A pick for **every** listed match: settlement (walkover-default) picks for `dqteams` fixtures, plus an explicit unresolved/limitations section in the executive summary | done | 64554333 | `tools/model.py`, `tools/site.py`, `tools/verify.py`, `data/flags_manual.json` |
| 11 | Line-integrity audit: expire stale archived esportsbook receipts, reject non-actionable extreme quotes, flag market-vs-model divergence | done | 64554333 | `tools/model.py`, `tools/flags.py` |
| 12 | Verification pass: curated flags that reference fixtures no longer on Hotspawn, count drift in docs, new publish gates | done | 64554333 | `tools/flags.py`, `tools/verify.py`, `README.md`, `data/flags_manual.json` |
| 13 | PR → `main`, merge, confirm Pages deploy | in progress | 64554333 | — |

### Handoff / collision note (2026-10-23T15:44Z, session 64554333)

While this session was working, session `b91181f0` merged PRs #18 and #19 into `main`, touching the same
pipeline files (`tools/site.py`, `tools/model.py`, `tools/verify.py`, `tools/flags.py`, `assets/`). The
overlap was resolved by merging `origin/main` into this branch and keeping the **union**, never by
discarding their work:

| Overlapping area | Who was kept |
|---|---|
| Archived esportsbook receipts | `b91181f0` (excluded from pricing entirely - stricter than this branch's 24 h expiry, which was dropped) |
| One-sided history (no rated series on one side) | `b91181f0` (left blank and marked unresolved; this branch's 1500-baseline fallback removed) |
| `tools/integrity.py`, `tests/`, exact ID reconciliation, per-card anchors, fetch timestamp, "community-maintained Leaguepedia" wording, focus-visible CSS | `b91181f0` |
| Settlement picks, market-vs-Elo cross-check, Leaguepedia kick-off cross-check, curated-flag reference gate, mobile bottom nav, working menu/filters, exec-summary restructure | `64554333` |

`tools/integrity.py` was extended by this session so a settlement pick is a legal third row shape, with
regression tests for all three shapes. Merge commit `fe7feb6`; nothing from either side was reverted.


## Task board

| # | Task | Status | Owner | File scope | Notes |
|---|------|--------|-------|-----------|-------|
| 1 | Reverse-engineer the Hotspawn LoL pick'em inventory | done | 2b1b75f6, 9d43092a, b166e06b | `tools/collect.py` | Public fixtures API `…/api/v1/fixtures?sport_alias=lol&status=scheduled&tenantId=1` returns all 264 LoL cards. Confirmed independently by three sessions. |
| 2 | External betting lines (never Hotspawn probabilities) | done | b166e06b | `tools/collect.py`, `tools/model.py` | Pinnacle guest API (9 LoL moneylines), Polymarket Gamma (cross-check), LoL Esports official schedule (Worlds cross-check). Blocked books recorded on `sources.html`. |
| 3 | Originate lines for matches with no market | done | b166e06b | `tools/model.py` | Elo on 34,616 Leaguepedia series (since 2024-09-01), decay + shrinkage, connected-graph guard. Out-of-sample: n=3,823, acc 64.1%, Brier 0.221. |
| 4 | Unresolved ledger + limitations in the executive summary | done | b166e06b | `unresolved.html`, `index.html` | 0 fully unresolved, 68 provisional; every limitation listed with scope. |
| 5 | Mobile-first Pages dashboard, exec summary + in-site links | done | b166e06b | root `*.html`, `assets/` | 11 pages, one card per match, per-row source links, filters, local-time conversion. |
| 6 | Automatic refresh every 4–8 h | done | b166e06b | `.github/workflows/refresh.yml` | Cron 6 h + manual dispatch. |
| 7 | Flagged-for-review page | done | b166e06b | `flagged.html`, `data/flags_manual.json`, `tools/flags.py` | 12 items (curated + derived). |
| 8 | PR → main, merge, confirm Pages | done | b166e06b | — | PR #8 merged 2026-10-21T21:10:21Z (merge commit `e0904df`); Pages rebuild succeeded and the live site serves the new dashboard. |

## Session log

- `2026-10-21T20:20Z` — `8336fb7e` opened the board and claimed T1–T5.
- `2026-10-21T20:45Z`–`20:55Z` — `2b1b75f6` merged PRs #1–#6 (pipeline + dashboard) into `main`; the live site was theirs at that point.
- `2026-10-21T21:09Z` — `b166e06b`: merged `origin/main` into `arena/b166e06b-lolhotspawn1` and took over the published site as the integration session.

## Integration decision (2026-10-21T21:09Z, session `b166e06b`)

`main` already carried session `2b1b75f6`'s generated site (PRs #1–#6) and session `8336fb7e` has an
open PR (#7). Three pipelines publishing the same root HTML means the last workflow to run wins, which
is not a stable site. Resolution:

1. **One pipeline owns the published files**: `tools/`. It regenerates every page from
   `data/matches.json` and cannot commit unless `tools/verify.py` passes.
2. **The other session's work is preserved, not deleted**: `pipeline/`, its data snapshots,
   `VERIFICATION.md` and its probe scripts moved to `archive/session-2b1b75f6/` with a README. It is
   also intact in the history of `main` up to `cfee3e5`.
3. **No competing scheduler**: the archived pipeline's workflow is not kept active, so a second cron
   cannot overwrite the site between refreshes.
4. **Findings adopted rather than duplicated**:
   - `2b1b75f6`/`8336fb7e` identified Hotspawn's "Phong Vũ Buffalo" label as a mislabelled German slot.
     Independently verified here: the five Hotspawn fixtures (27 Oct 17:00 vs DKB XPERION NXT, 30 Oct
     19:30 vs VfB eSports, 3 Nov 17:00 vs 404 Multigaming, 8 Nov 18:30 vs MT1 Esports, 13 Nov 18:30 vs
     regnum4games) match Leaguepedia's five `PvB (Swiss Team)` fixtures on date, time and opponent.
     Recorded as an explicit alias with that evidence in `data/aliases.json`.
   - The stale-fixture observation (Hotspawn keeps `status=scheduled` after kick-off) is published as a
     derived flag and marked on every affected card.

## Verification performed by the integration session

| Check | Result |
|---|---|
| `tools/verify.py` on the merged tree | 14/14 checks pass (`data/verification.json`) |
| Match inventory vs Hotspawn API | 264/264 rows, no duplicates |
| Probability integrity | 264/264 rows sum to 100% (±0.2pp); pick = higher side |
| Source links | 264/264 rows carry a Hotspawn match-card URL; market rows also carry the Pinnacle market URL |
| Team joins | 12 non-exact joins, each with evidence, listed on `verification.html` |
| Internal links | 0 broken across 11 pages |
| Hotspawn permalink scheme | Spot-checked live: `/matches/<team-a>-vs-<team-b>-<competition>-<id>` resolves |

## PR / deploy record

| Item | Value |
|---|---|
| Pull request | #8 — https://github.com/karagemop466-tech/LOLHOTSPAWN1/pull/8 |
| Merge commit | `e0904df` (2026-10-21T21:10:21Z) |
| Pages build | `pages-build-deployment` succeeded on `main` after the merge |
| Live verification | `https://karagemop466-tech.github.io/LOLHOTSPAWN1/` served the new dashboard (264 matches, 9 market / 187 model / 68 provisional) |
| Auto-refresh on `main` | the merge push triggered `data-build` on `main`, confirming the refresh job runs from the default branch |

## Open items for the next session

- PR #7 (`8336fb7e`) is still open and overlaps this work; its content is superseded by the merged
  pipeline, but its Kalshi and calibration material is worth reviewing before it is closed.
- `archive/session-2b1b75f6/` can be deleted once the owner confirms nothing else is needed from it.
- Pinnacle is the only bookmaker that returned usable LoL prices from the runner. GG.BET (403 region),
  EGamersWorld (Cloudflare), Oddspedia (410), BetExplorer (404) and Unibet/Kambi (400) are retried on
  every build and reported on `sources.html`; if one becomes reachable, add it to `BOOK_PROBES` and
  `market_lookup`.

---

# Full Low-Tier Origination, 5-Venue Consensus & Forensic Audit Integration — session `8336fb7e`

## Task board — session `8336fb7e` (`arena/8336fb7e-lolhotspawn1`)

| ID | Work Unit | Status | Owner | Artifacts & Verification |
| :--- | :--- | :--- | :--- | :--- |
| `T1` | Hotspawn API + SSR reconciliation (`195` open + `69` past-lock stale rows) | `done` | `8336fb7e` | `scripts/refresh.py`, `data/sources/hotspawn_*.json` |
| `T2` | **5-Venue Real-Money Market Consensus** (`Pinnacle + Bovada + Polymarket full-series + Kalshi CFTC + Specialist Esportsbooks`) + `LCP 2027 Promotion` (`91.1% / 8.9%`) | `done` | `8336fb7e` | `scripts/markets.py`, `featured.html`, `data/book_receipts.json` (hard-rejects `1.80/1.80` aggregator placeholders) |
| `T3` | **Low-Tier Regional Origination (`178` decisive open picks across 10 leagues)** via untruncated MediaWiki `Data:<OverviewPage>` schedules (`2,598` match records, `0` rate limits on runners) | `done` | `8336fb7e` | `scripts/leaguepedia_data.py`, `scripts/entities.py`, `scripts/originate.py`, `originated.html` — Chronological walk-forward (`N = 1,595`): **Accuracy `64.9%`, Brier `0.2145` (`−14.2%` MSE), Log-Loss `0.6175`, ECE `3.53%`** |
| `T4` | **Unresolved Quarantine (`7` open caveats + `64/69` stale scores recovered) & Flagged Forensic Audit (`8` alerts)** | `done` | `8336fb7e` | `unresolved.html`, `flagged.html` — Uncovered **`#1071216 Solid Gaming`** removed in Round 10 (`72%` crowd trap!), **`PvB Nation` misbound as `Phong Vũ Buffalo`**, **`Team Reds` Week 1 ineligible-roster forfeits**, and `+33 pp` `Galions vs Solary` crowd distortion |
| `T5` | Unified 4-hour cron (`.github/workflows/refresh.yml`), PR #7 merge to `main`, live GitHub Pages HTTP 200 verification | `done` | `8336fb7e` | **PR #7**: <https://github.com/karagemop466-tech/LOLHOTSPAWN1/pull/7> (`MERGED` to `main`) · **Live Dashboard**: <https://karagemop466-tech.github.io/LOLHOTSPAWN1/> (`HTTP 200` verified across all pages & feeds) |

---

# Integration record — session `b166e06b`, second pass

`8336fb7e`'s PR #7 merged into `main` at 2026-10-21T21:17Z while the first integration pass was
already live. That left **two publishers**: `tools/` (this session, PRs #8–#11) and
`scripts/refresh.py` (PR #7). Both wrote the same root HTML on the same 6-hour cron, so whichever
workflow finished second would silently overwrite the other's pages.

| Item | Resolution |
|---|---|
| Publisher | `tools/` only (`collect` → `model` → `report` → `flags` → `site` → `verify`) |
| Scheduler | one workflow, `.github/workflows/refresh.yml`, cron `17 */6 * * *` |
| Removed cron jobs | `data.yml` (manual-only duplicate) and `pages-verify.yml` (ran `scripts/refresh.py` + `pytest`); deleted, history keeps them |
| Superseded pipeline | `scripts/`, `tests/`, `requirements.txt`, `data/summary.json`, `data/picks.json`, `data/teams_index.json`, `data/calibration.json`, `data/book_receipts.json`, `data/flagged.json` and the `data/sources/` snapshots moved to `archive/session-8336fb7e/` |
| Why archive, not delete | PR #7's Kalshi/Bovada receipts, the `2598`-match Leaguepedia `Data:` harvest and the `1,595`-match walk-forward backtest are audit evidence for the same task; nothing is lost, but nothing in `archive/` runs |
| Gate | `tools/verify.py` still fails the build (14 checks) before any commit |

Live-site verification after each of PRs #8, #9, #10, #11: `pages-build-deployment` succeeded and
`https://karagemop466-tech.github.io/LOLHOTSPAWN1/` served the new snapshot. PR #10 fixed the
archived-data link, the PvB alias evidence column and the verification stat label; PR #11 replaced
the placeholder "0-3 matches" scope with a computed count and sorted provisional cards by kick-off.

---

# Final record — session `b166e06b`

| Item | Result |
|---|---|
| PR #9 | merge-back of the auto-refresh commit; merged 2026-10-21T21:12:22Z |
| PR #10 | archived-data link, PvB alias evidence, verification stat label; merged 21:14:23Z |
| PR #11 | computed disconnected-opponent count, provisional cards sorted by kick-off; merged 21:16:08Z |
| PR #12 | single-publisher integration after PR #7; second pipeline archived; merged 21:18:54Z |
| PR #13 | README rewritten for the live pipeline, stale `tournaments.html` / `assets/styles.css` removed; merged 21:22:17Z |
| Unattended refresh | `refresh-picks` run 39677771451 on `main` completed successfully and pushed `f73e401` (264 rows, 14/14 checks, fresh Pinnacle lines) — the cron loop is verified end to end, not just dispatched |
| Pages | `pages-build-deployment` succeeded after every merge; `gh api .../pages` reports `status: built` |
| Publish gate | 14/14 on the merged tree, on the bot's own commit, and on every PR above |

## Branch inventory at close

| Branch | State |
|---|---|
| `main` | published site; single workflow `refresh.yml`; 11 pages generated by `tools/` |
| `arena/b166e06b-lolhotspawn1` | this session; merged to `main` via PRs #8–#13 |
| `arena/8336fb7e-lolhotspawn1` | merged as PR #7, then superseded; work preserved in `archive/session-8336fb7e/` |
| `arena/2b1b75f6-lolhotspawn1` | superseded; work preserved in `archive/session-2b1b75f6/` and in history up to `cfee3e5` |
| `arena/9d43092a-lolhotspawn1`, `arena/f6e73320-lolhotspawn1` | other active session branches; not merged — `main` takes one publisher only, so their work needs review against the live pipeline before any merge |

## What the next session should check first

1. `tools/verify.py` — if it fails, the site is intentionally not updated; read `data/build.log`.
2. `flagged.html` — 13 items; the kick-off-time disagreements and the 69 past-start fixtures are the
   two that most affect a bettor.
3. Pinnacle coverage — 9 of 264 fixtures. If GG.BET, EGamersWorld, Oddspedia, BetExplorer or
   Unibet/Kambi start responding from the runner, add them to `BOOK_PROBES` in `tools/collect.py`
   and to `market_lookup` in `tools/model.py`; that is the only way the market share rises.

---

# Final enhancement pass into single-publisher `tools/` — session `8336fb7e` (PR #16)

Preserving `b166e06b`'s single-publisher layout (`tools/` + `.github/workflows/refresh.yml`, `11` HTML pages,
`archive/` untouched), PR #16 resolves the remaining open items and two live defects directly inside `tools/`:

| Item | Upgrade in `tools/` |
|---|---|
| **5-venue real-money consensus (`10` market matches)** | Added live `collect_kalshi()` (`KXLOLGAME` CFTC contract book) and `collect_bovada()` (`Head To Head` full-series moneylines) to `tools/collect.py` + `BOOK_PROBES` (`9/14` live HTTP 200 feeds), plus multi-venue de-vigged consensus (`Pinnacle 0.36`, `Polymarket full-series 0.24`, `Kalshi CFTC 0.18`, `Bovada 0.12`, `Specialist Esportsbook 0.10`) in `tools/model.py`, pricing `#1081423 Ground Zero Gaming vs Frank Esports` (`LCP 2027 Promotion`, `91.1% / 8.9%`) and rejecting symmetric `1.80 / 1.80` aggregator placeholders |
| **Mid-split league removal quarantine (`dqteams`)** | Added live MediaWiki `|dqteams=` harvesting (`data/raw/leaguepedia_dq.json`), quarantining all `5` disqualified `Solid Gaming` fixtures in `Komplettligaen 2026 Autumn` (including upcoming `#1071216 Solid Gaming vs DMG Esports Norway`, where `72%` of Hotspawn's crowd picked disqualified `Solid Gaming`) into `unresolved` (`p0=None`, `pick=None`) with explicit walkover/void notes |
| **Methodology backtest bug fix + SVG calibration curve** | Fixed `tools/site.py` omitting `data['backtest']` from `model` (which rendered `0` series and `—` on live `methodology.html`); now renders all `3,823` out-of-sample series (`64.1%` accuracy, `0.2213` Brier, `0.6317` log-loss) plus an inline SVG reliability plot, enforced permanently by Check #15 in `tools/verify.py` (`15/15 PASS`) |
| **Pull requests** | PR #7 (<https://github.com/karagemop466-tech/LOLHOTSPAWN1/pull/7>, merged `e2073b9`) and PR #16 (<https://github.com/karagemop466-tech/LOLHOTSPAWN1/pull/16>, merged to `main`) |

---
# Integration record — session `f6e73320` (third pass), 2026-10-21T21:45Z

Session `f6e73320` (branch `arena/f6e73320-lolhotspawn1`, PR #15) built an **independent second
implementation** of the same brief in parallel: a zero-dependency Node pipeline (`scripts/*.mjs`) and a
7-page mobile-first dashboard under `docs/`, with its own verification record (below). It was listed in
the branch inventory as "needs review against the live pipeline before any merge". That review happened
in this pass; the result is a **scope-disjoint dual layout**, not a second root publisher.

## Integration decision (third pass)

1. **Canonical published site stays exactly as `b166e06b` left it**: root `*.html` generated by
   `tools/` only, gated by `tools/verify.py`, refreshed by `.github/workflows/refresh.yml`
   (cron `17 */6 * * *`). Nothing in this merge writes root pages.
2. **The Node pipeline is quarantined to disjoint paths** and published alongside at
   `https://karagemop466-tech.github.io/LOLHOTSPAWN1/docs/`:
   | Owner | Paths written |
   |---|---|
   | `tools/` (Python, canonical) | root `*.html`, `assets/`, `data/*` (top level), `data/raw/{hotspawn_lol,leaguepedia,lolesports,pinnacle_lol,polymarket}.json`, `data/build.log` |
   | `scripts/` (Node, secondary) | `docs/*`, `data/node/**` (its picks/flags/model/raw/history), nothing else |
3. **Two schedulers, one concurrency group**: the Node pipeline runs from
   `.github/workflows/refresh-docs.yml` (cron `5 */6 * * *`, different minute) but shares the
   `refresh-picks` concurrency group, so the two bots can never run — or push — at the same time.
   The Node commit step adds only `data/node docs` (never `git add -A`), rebases with `-X theirs`
   and replays via soft-reset on conflict, so even a manual push race cannot lose the other
   pipeline's commits. `tools/`' `git add -A` is safe under the shared group because runs serialize.
4. **Conflicts resolved without discarding either side**: `data/flags.json` and
   `data/raw/pinnacle_lol.json` (same path, different schemas — a hard collision between the two
   bots) resolved in favour of `tools/`; the Node pipeline's equivalents moved to
   `data/node/flags.json` and `data/node/raw/pinnacle_lol.json`. `refresh.yml` kept the `tools/`
   version verbatim; the Node scheduler lives in its own file. `README.md` and this file are unions.
5. **Independent corroboration kept, not merged**: the two pipelines disagree by design on a few
   presentation choices (264 rows incl. past-start marked, vs 195 open + 64 stale quarantined;
   Leaguepedia-trained Elo over 34,616 series vs Hotspawn-archive Elo over 1,102 series; 0 unresolved
   + 68 provisional vs 12 unresolved). Both views stay published — they are independent audits of the
   same fixtures and their agreement (9 Pinnacle lines, same picks, same start-time-discrepancy and
   stale-fixture irregularities found separately) is stronger evidence than either alone.

## Task board — session `f6e73320`

| # | Task | Status | Owner | Files |
|---|---|---|---|---|
| T1 | Source discovery + verification (Hotspawn API, Pinnacle guest API, Polymarket) | done | f6e73320 | `COORDINATION.md` sources registry |
| T2 | Collector (`scripts/collect.mjs`) | done | f6e73320 | `data/node/raw/*` |
| T3 | Analyzer: devig, name matching, Elo, flags, ledger (`scripts/analyze.mjs`) | done | f6e73320 | `data/node/picks.json`, `data/node/flags.json`, `data/node/model/*` |
| T4 | Site builder, 7 mobile-first pages (`scripts/build_site.mjs`) | done | f6e73320 | `docs/*` |
| T5 | 6-hourly refresh automation | done | f6e73320 | `.github/workflows/refresh-docs.yml` |
| T6 | Line-by-line verification pass | done | f6e73320 | record below + `docs/flagged.html` |
| T7 | Integration: merge main, resolve conflicts, PR #15 → main, confirm Pages | done (this pass) | f6e73320 | this file, `README.md` |

## Verification record — session `f6e73320` (T6)

- Math re-derived for every row of `data/node/picks.json`: Pinnacle devig within 0.2pp, pick side ==
  argmax, Elo+shrinkage formula reproduced within 0.4pp, Polymarket renormalization to 1.0 — all OK.
- Live spot checks (2026-10-21): Pinnacle straight-markets JSON for Gen.G–Invictus (−435/+323 →
  77.5/22.5) == committed data; Polymarket event `lol-gen-ig1-2026-10-23` live at 78¢/23¢ ($72.1K vol),
  rules text states start Oct 23 1:00 PM ET == 17:00 UTC == our row; Polymarket rules for
  `lol-hle1-tes-2026-10-23` state 5:00 PM ET == Pinnacle 21:00 UTC, while Hotspawn lists 18:00 UTC
  (flagged as start-time discrepancy; `b166e06b`'s flagged.html carries the same finding independently).
- Lobby SSR cross-check: 195 scraped permalinks == 195 open API fixtures; all displayed permalinks
  scraped, none constructed.
- Irregularities auto-flagged with source links (`docs/flagged.html`): 12 unresolved matches (no market
  line anywhere + no recorded history for ≥1 side), 4 start-time discrepancies Hotspawn vs Pinnacle
  (>90 min; up to 300 min on BLG–MKOI), 3 large Pinnacle-vs-own-model divergences (thin tier-1 history
  in the Hotspawn archive), 64 stale fixtures quarantined (info), 104 low-confidence model picks
  aggregated (info).
- Pipeline resilience verified live: Pinnacle `/matchups` returned HTTP 401 on the 21:14Z run
  (transient); mitigations added — 3× retry with backoff, persistent matchups-listing cache with
  recorded provenance (`listing: live|cache@…` per row), and line reconstruction from odds rows when
  both fail. The 21:25Z run recovered 9/9 Pinnacle lines, all `listing: live`.

## Sources registry — session `f6e73320`

| Source | URL | Used for | Verified |
|---|---|---|---|
| Hotspawn LoL pick'em lobby (SSR) | https://play.hotspawn.com/lol-pickems | inventory cross-check + permalinks | 2026-10-21 live |
| Hotspawn fixtures API | https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=lol | inventory + results archive (1501 fixtures) | 2026-10-21 live |
| Pinnacle guest API | https://guest.api.arcadia.pinnacle.com/0.1/sports/12/leagues · /leagues/{9587,225201}/matchups · /markets/straight | moneylines (devigged) | 2026-10-21 live |
| Polymarket gamma API | https://gamma-api.polymarket.com/events?closed=false&tag_slug=league-of-legends | prediction-market lines | 2026-10-21 live |
| Polymarket event pages | https://polymarket.com/esports/league-of-legends/… | per-row source links + official start times | 2026-10-21 live |
| egamersworld odds comparison | https://egamersworld.com/lol/bets | corroboration only (not ingested) | 2026-10-21 live |

## PR / deploy record — session `f6e73320`

| Item | Value |
|---|---|
| Pull request | #15 — https://github.com/karagemop466-tech/LOLHOTSPAWN1/pull/15 |
| Merge | executed via `gh pr merge 15 --merge` immediately after the integration commit, without waiting for review (per task protocol) |
| Pages | source unchanged: `main` `/` (already `status: built`); the Node dashboard is served at `/LOLHOTSPAWN1/docs/` from the same deployment — no second Pages config exists |
| Post-merge verification | recorded as a comment on PR #15 (root dashboard HTTP 200 + 14/14 gate data intact + `/docs/` HTTP 200 + both refresh workflows present) |

### Cross-reference: PRs #16/#17 (session `8336fb7e`, merged into `main` during this pass)

`tools/` gained Kalshi/Bovada consensus (10 market matches), a Leaguepedia `dqteams` disqualification
quarantine (all 5 `Solid Gaming` fixtures in Komplettligaen 2026 Autumn → unresolved on the canonical
site, incl. `#1071216` which the Node dashboard still prices from its Elo model — the Node pipeline
will adopt the dq quarantine in a future pass; until then the canonical root site's treatment is the
authoritative one), and the backtest rendering fix (gate now 15/15).

## Session b91181f0 — 2026-10-23

| Task | Status | Owner | Scope |
|---|---|---|---|
| Audit canonical fallback safety, mobile navigation, provenance and refresh gate; integrate and deploy | in progress | b91181f0 | `tools/`, `assets/`, root generated HTML, `.github/workflows/refresh.yml`, tests, README, COORDINATION.md |

Existing completed scopes are retained. This session uses the fixed Arena branch rather than creating another branch. External source access from this sandbox is restricted; fresh collection must run on GitHub Actions, not be represented as live local verification.

### b91181f0 audit findings and local verification

- Fixed broken mobile menu and all canonical pick filters (old JS targeted a different DOM).
- Removed archived 2026-10-21 aggregator receipts from current consensus. This reduced locally recomputed market rows from 10 to 9; the affected match now has a history-based model line. No odds invented.
- Removed the one-unrated-side 1500 baseline fallback; missing evidence now produces null probabilities and a documented unresolved reason.
- Labelled Leaguepedia as community-maintained, not an official league authority. Historical manual findings explicitly say not reverified. Added collection timestamp/8-hour stale warning and persistent mobile All picks link.
- Local verification uses the committed 2026-10-23T11:42:37Z Hotspawn snapshot, NOT a new live fetch. Exact inventory reconciliation: 241/241; 17 integrity/link/render gates pass. Five Python regression tests pass, including NaN/out-of-range/wrong-team rejection. jsdom interaction tests pass for menu, search, empty state, method and tournament filters over all 241 cards.
- Source records: https://github.com/karagemop466-tech/LOLHOTSPAWN1/blob/main/data/raw/hotspawn_lol.json and the provider URLs on Sources. GitHub Pages configuration confirmed via GitHub API (main /, status built).
- Irregularity: manual Actions dispatch returns HTTP 403 (integration permission). A new collection cannot be requested from this sandbox; merging pipeline changes triggers the existing push workflow. No credentials requested. Fresh verification/deploy result to be recorded below.

## Session 1f377d7a — 2026-10-23 (pick-coverage + mobile dashboard pass)

| Task | Status | Owner | File scope |
|---|---|---|---|
| T1 External-line source probe (established books → esportsbooks), live reachability evidence from a runner | in progress | 1f377d7a | `.github/workflows/source-probe.yml` (new, manual-only), `tools/collect.py` probes only |
| T2 Price every fixture: competition-anchored prior for sides with no rated series; explicit walkover/void guidance for the DQ rows | in progress | 1f377d7a | `tools/model.py` |
| T3 Executive summary with in-site jump links + a dedicated unresolved/limitations section on `index.html` | in progress | 1f377d7a | `tools/site.py`, `assets/style.css`, `assets/app.js` |
| T4 Mobile picks UX: day anchors, sticky filter row, readable cards, back-to-top | in progress | 1f377d7a | `tools/site.py`, `assets/*` |
| T5 Gate + integrity tests for the new sections | in progress | 1f377d7a | `tools/verify.py`, `tools/integrity.py`, `tests/*` |
| T6 Integration: rebuild, re-verify line by line, PR → main, merge, confirm Pages | in progress | 1f377d7a | shared outputs (this session is the integration session) |

Starting point: `main` at `8b2fd7f` (session `b91181f0` merged its audit pass). That session's scope is
retained; this session does not revert its changes. Overlap is limited to `tools/site.py`, `assets/*` and
`tools/model.py`, and it is additive: the mobile menu/filter fixes and the removal of archived receipts
stay in place.

### 1f377d7a — work completed, verification record

| Task | Status | Evidence |
|---|---|---|
| T1 External-line source probe | done (code) / pending runner evidence | `tools/collect.py` now probes **28** endpoints: Pinnacle, Kalshi, Bovada, Polymarket, DraftKings, FanDuel, BetMGM, Betway, Unibet/Kambi, BetOnline, BetUS, MyBookie, GG.BET, BC.GAME, Thunderpick, Rivalry, Luckbox, EGamersWorld, Oddspedia, OddsPortal, BetExplorer, EsportsBets, VegasInsider, Action Network, The Odds API, plus inventory/reference feeds. Nothing is parsed unless a dedicated collector produced verified numbers; `sources.html` now separates "prices picks" from "probe only". Reachability for the new endpoints is recorded in `data/sources_status.json` by the first refresh after merge. |
| T2 Price every fixture | done | 237/241 rows carry a pick. The 4 blanks are all `dqteams=Solid Gaming` fixtures in Komplettligaen; each now carries `expected_resolution` (walkover guidance, Leaguepedia source, explicitly "not a betting pick"). No baseline rating was invented for an unrated side. |
| T3 Exec summary + unresolved section | done | `index.html` gains a jump grid (`#where`), an executive summary and a dedicated `#unresolved-summary` block listing every unresolved fixture with its reason, its settlement guidance and source links, plus a limitations table. |
| T4 Mobile picks UX | done | Day-grouped cards, sticky day headers, `content-visibility` on cards, query-driven filters (`?window=today`, `?window=next7`, `?method=...`), reset control, and a 4-item bottom tab bar on every page. `tests/dashboard.cjs` covers all of it in jsdom. |
| T5 Gate + tests | done | `tools/verify.py` now runs **26** assertions (was 17), all passing; `python3 -m unittest discover -s tests` 5/5; `NODE_PATH=… node tests/dashboard.cjs` passes. |
| T6 Integration | in progress | this file, PR, merge, Pages check |

**Model change and its provenance (line-by-line verification).**

| Item | Value |
|---|---|
| Selection window (used to choose hyper-parameters) | 2025-07-01 → 2026-07-01, n = 16,289 series, Brier 0.2217 |
| Test window (published) | series after 2026-07-01, n = 3,854 |
| Previous settings (K=24, no margin term) | 64.14% accuracy, Brier 0.2211, log-loss 0.6322 |
| Current settings (K=48 bo1 / K=40 multi-game × (1 + 0.5·ln(1+margin))) | 65.26% accuracy, Brier 0.2149, log-loss 0.6182 |
| Shrinkage toward 1500 | removed; measured Brier 0.2176 with it versus 0.2150 without |

Recomputation is reproducible from `data/raw/leaguepedia.json` with `python3 tools/model.py`
(offline, no network); every number above is printed by that run.

**New irregularity flagged (verified this session).** Hotspawn fixture `#1082002` in the Arabian
Regional Championship qualifier has a participant literally named `DELETED`. Leaguepedia records
`DELETED 0-1 S7raa` for the same page and kick-off time. Published on `flagged.html` with both sources;
the original organisation is **not** inferred.

**Settled cards.** 53 of the 65 stale cards have a final result already recorded in Leaguepedia; the
result, score and league-page link are now attached to the card and marked `result on record`, so a
historical card cannot be mistaken for a live bet.

**Local verification limits (stated, not papered over).** This sandbox cannot reach Hotspawn, Pinnacle,
Polymarket, Kalshi or Leaguepedia (TLS egress is blocked for everything except GitHub). All numbers above
were recomputed from the committed `data/raw/*` snapshots; the new probes and any new market coverage can
only be observed on the GitHub Actions runner, and that result is recorded below once the merge triggers
`refresh.yml`.
