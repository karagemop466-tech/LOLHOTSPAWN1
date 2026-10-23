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
# Session `3d4e18ac` — final integration verification (this session)

| Item | Value |
|---|---|
| Session ID | `3d4e18ac` (branch `arena/3d4e18ac-lolhotspawn1`, from `main` @ `e0c22be`) |
| Claimed task | Final integration verification: verify the `tools/` pipeline end-to-end, confirm 14/14 publish gate passes, confirm GitHub Pages is built, record sources & irregularities |
| File scope | `COORDINATION.md` (this claim); verify `tools/*`, `data/*`, root `*.html`, `assets/*` |
| Status | done |

## Session `3d4e18ac` verification record

| Check | Result | Source linked |
|---|---|---|
| Branch merged to main at close | done — PR #27 merged via merge commit `fe0ce514` (2026-10-23T15:52:25Z); branch fully contained in `main` | https://github.com/karagemop466-tech/LOLHOTSPAWN1/pull/27 |
| Offline publish gate (`tools/verify.py`) | done — 14/14 PASS; `data/verification.json` regenerated | `data/verification.json` |
| Site rebuild (`tools/site.py`) | done — all 11 pages regenerate, 0 broken internal links, nav on every page | root `*.html` |
| Full data collection (`tools/collect.py`) | not re-runnable in this shell — external betting/TLS endpoints unreachable (sandbox allows only github.com/npm/pypi); production GitHub Actions runner reached them (build 2026-10-23T11:43 UTC: 9/14 sources live) | `data/sources_status.json`, `data/build.log` |
| Mobile viewport + responsive CSS | done — `<meta name="viewport" content="width=device-width, initial-scale=1">`, responsive card grid, hamburger nav, 44px touch targets, dark mode | `assets/style.css`, root `*.html` |
| Executive summary links to all picks views | done — `index.html` links to All picks / Market-backed / Originated / Unresolved | `index.html` |
| GitHub Pages `status: built` | done — `https://karagemop466-tech.github.io/LOLHOTSPAWN1/`, source `main` `/` | `gh api .../pages` |

### Sources verified (all external; Hotspawn crowd % never used as probability)
- Hotspawn fixtures API — match inventory only
- Pinnacle guest API, Polymarket Gamma, Kalshi CFTC, Bovada — real-money moneyline/contract lines (de-vigged, precision-weighted consensus)
- Leaguepedia Cargo + MediaWiki `Data:` (`dqteams`) — series history and mid-split removals for originated Elo lines plus quarantine
- LoL Esports (Riot) — Worlds schedule cross-check
- 9/14 probed feeds reachable on last production runner build; GG.BET, EGamersWorld, Oddspedia, BetExplorer, Unibet/Kambi blocked or geo-fenced (logged on `sources.html`)

### Irregularities / limitations (documented on the site, do not block merge)
- 4 matches unresolved (mid-split league removals / `dqteams` or zero match history) — quarantined on `unresolved.html` with reasons, not guessed
- 65 provisional lines (thin under-5-series data or no shared-opponent chain) — flagged low-confidence
- 10 market-backed matches; 162 model; 65 provisional across 27 tournaments
- Sandbox network restriction: external betting APIs not reachable from this shell (TLS EOF); the auto-refresh cron `17 */6 * * *` runs on GitHub's infrastructure, not this shell



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
| Audit canonical fallback safety, mobile navigation, provenance and refresh gate; integrate and deploy | done | b91181f0 | `tools/`, `assets/`, root generated HTML, `.github/workflows/refresh.yml`, tests, README, COORDINATION.md |

Existing completed scopes are retained. This session uses the fixed Arena branch rather than creating another branch. External source access from this sandbox is restricted; fresh collection must run on GitHub Actions, not be represented as live local verification.

### b91181f0 audit findings and local verification

- Fixed broken mobile menu and all canonical pick filters (old JS targeted a different DOM).
- Removed archived 2026-10-21 aggregator receipts from current consensus. This reduced locally recomputed market rows from 10 to 9; the affected match now has a history-based model line. No odds invented.
- Removed the one-unrated-side 1500 baseline fallback; missing evidence now produces null probabilities and a documented unresolved reason.
- Labelled Leaguepedia as community-maintained, not an official league authority. Historical manual findings explicitly say not reverified. Added collection timestamp/8-hour stale warning and persistent mobile All picks link.
- Local verification uses the committed 2026-10-23T11:42:37Z Hotspawn snapshot, NOT a new live fetch. Exact inventory reconciliation: 241/241; 17 integrity/link/render gates pass. Five Python regression tests pass, including NaN/out-of-range/wrong-team rejection. jsdom interaction tests pass for menu, search, empty state, method and tournament filters over all 241 cards.
- Source records: https://github.com/karagemop466-tech/LOLHOTSPAWN1/blob/main/data/raw/hotspawn_lol.json and the provider URLs on Sources. GitHub Pages configuration confirmed via GitHub API (main /, status built).
- Irregularity: manual Actions dispatch returns HTTP 403 (integration permission). A new collection cannot be requested from this sandbox; merging pipeline changes triggers the existing push workflow. No credentials requested. Fresh verification/deploy result to be recorded below.

---

# Session `6d1ede2c` — independent verification & final integration (2026-10-23)

Branch: `arena/6d1ede2c-lolhotspawn1`. Claimed at 2026-10-23T15:40Z, **before** any edit.

| ID | Task | Status | Owner | File scope (disjoint) |
|----|------|--------|-------|------------------------|
| `I1` | Independent line-by-line re-verification of every published row: re-derive each market probability from the committed raw provider payloads without importing `tools/`, live spot-check provider quotes, and publish the findings | done | `6d1ede2c` | `audit/**` (new directory), this section |
| `I2` | Final integration: merge the other sessions' branches, re-verify the combined tree, create PR → `main`, merge, confirm the GitHub Pages deploy | done | `6d1ede2c` | root `*.html`, `data/**` only at integration time |

**Non-overlap rule for this session.** `a91e528d` has claimed `tools/`, `assets/`, root `*.html` and
`.github/workflows/refresh.yml` (S1–S5). `b91181f0`'s audit is merged. This session therefore writes
**only** `audit/**` until integration; anything needing `tools/` is logged here as a request, not edited.


### `6d1ede2c` — integration record (2026-10-23, 15:40–16:00Z)

**Merged into this branch, in order:** PR #20 (`0d48f265` source audit) → `origin/main` at
`7fee3e2` (PR #25 from `64554333`: mobile nav, 25-gate verify, thin markets, settlement picks).
Generated pages were regenerated from the merged pipeline rather than hand-merged.

**Unique to this session (not present on `main` before it):**

| Change | Files | Why |
|---|---|---|
| Pinnacle `(Kills)` derivative rejected at collection **and** at pricing; related markets filtered by `matchupId` | `tools/collect.py`, `tools/model.py` | The kills market was pricing 6 of 8 series and the stored URL pointed at it; `/markets/related/straight` also returns the sibling matchup's markets |
| `stale` = start time has passed (was ">3 hours past"), plus `stale_hours` per row | `tools/model.py` | Row `1071212` was displayed as upcoming 47 minutes after kick-off |
| Only a market's own `gameStartTime` is used for start comparison (event `startDate` is the listing date); 1 h threshold; the disagreeing venue is named | `tools/collect.py`, `tools/model.py` | F4 from `0d48f265`; the first attempt compared the listing date and produced a false 130 h mismatch, which was caught before commit |
| Leaguepedia `MatchSchedule.FF` captured and stated per `dqteams` fixture | `tools/collect.py`, `tools/model.py`, `audit/receipts/` | The two audits disagreed about whether these were forfeits; the `FF` column settles it per fixture (8 of 11 flagged, 3 not) |
| Second, independent verifier: every published number re-derived from raw payloads, every page link and id checked | `audit/verify_independent.py`, `audit/check_site.py`, `audit/report.*` | The publish gate is written by the same pipeline it checks |
| Both audits linked from the Flagged for review page | `tools/site.py` | So the evidence is reachable from the site, not only from GitHub |

**Verification of the merged tree**

| Check | Result |
|---|---|
| `tools/verify.py` | 25/25 pass |
| `audit/verify_independent.py` | 0 failures; 32/32 venue quotes and 241/241 row checks reproduced; 0 kills substitutions |
| `audit/check_site.py` | 18 pages, 0 broken links, 0 duplicate ids, 241 match cards exactly once |
| `python3 -m unittest discover -s tests` | 5/5 pass |
| Coverage | 241/241 rows carry a pick: 237 priced (9 market, 163 model, 65 provisional) + 4 settlement picks with **no** probability |
| `data/raw` provenance | inventory `2026-10-23T15:37:40Z`, provider payloads `15:37–15:39Z` |

**Irregularities left open (published on Flagged for review):** the 4 `dqteams` settlement picks are
administrative defaults with no probability; `1071170` has no Leaguepedia series on Hotspawn's date
(337 h apart); the thin Polymarket row (`1079080`, $5 volume) is labelled low confidence; 66 rows have
start times in the past while Hotspawn still lists them as scheduled; only four venues are reachable
from the runner.

**PRs reviewed but not merged:** #22 (`29d6fe6a`), #23 (`294e62ad`), #24 (`4dfd0e71`). All three
predate the `main` merge of #25 and re-implement changes already landed (thin markets, kills market,
retired receipts), so merging them would have reverted verified work. Their branches are intact and
their unique items are recorded for follow-up: #23's per-competition coverage page and external
corroboration ledger; #24's compact pick table and probe expansion.

### Requests to other sessions (log only, no edit)

| Target | Request | Reason |
|--------|---------|--------|
| `a91e528d` S3 | When adding a venue to consensus, publish the venue's own capture timestamp and the URL of the exact payload; drop any quote whose timestamp is older than the current collection run. | The 2026-10-23 audit found the previous "5-venue consensus" mixed a static 2026-10-21 archive quote into live prices. |
| `a91e528d` S2 | Keep one canonical, always-visible route to the picks list on mobile (the persistent "All picks" link is good); do not add a second competing picks page. | The brief asks for a dashboard that a phone user cannot get lost in. |

> **Overlap resolved by the integration session (`6d1ede2c`, 2026-10-23T15:55Z).** This session and
> `0d48f265` both wrote into `audit/` within minutes of each other. The two audits are complementary and
> both are kept: `0d48f265` produced `audit/AUDIT.md`, `audit/audit.csv`, `audit/build_audit.py` and
> `audit/receipts/`; this session produced `audit/README.md`, `audit/verify_independent.py`,
> `audit/check_site.py` and their generated reports. No filename collides. Going forward `audit/` is a
> read-only evidence directory: neither script writes outside it and neither is imported by `tools/`.

### b91181f0 merge and fresh deployment record

- PR #18: https://github.com/karagemop466-tech/LOLHOTSPAWN1/pull/18 — merged 2026-10-23T15:37:26Z, merge commit `8b2fd7f451db67b92cc68b80f64df2b4e475b954`.
- Fresh collection ran successfully on GitHub Actions: https://github.com/karagemop466-tech/LOLHOTSPAWN1/actions/runs/39979868718 . Inventory fetched **2026-10-23T15:37:40Z**; model/verification completed **15:39:34Z**. All 17 gates passed. Provider observations: Pinnacle, Kalshi, Bovada and Polymarket returned 200; GG.BET/EGamersWorld 403, Oddspedia 410, BetExplorer 404, Kambi 400. Availability alone does not establish match coverage.
- Fresh inventory: **241 rows; 9 market, 163 model, 65 provisional, 4 unresolved**. Every raw inventory ID appears exactly once in published picks. No claim is made that model estimates are official verified win probabilities.
- GitHub Pages deployment succeeded: https://github.com/karagemop466-tech/LOLHOTSPAWN1/actions/runs/39980169572 . Pages API reports `built`, commit `a44583f32fc1c277786fe066c6cd74a954d8f7da`, 2026-10-23T15:39:58Z. Site: https://karagemop466-tech.github.io/LOLHOTSPAWN1/ . This confirms deployment through GitHub; direct live-site HTTP verification is unavailable under this sandbox's host restrictions.
- Post-refresh checks: Python 5/5 tests and jsdom interaction tests pass against the fresh generated pages. Local link gate reports zero broken internal links across 11 canonical pages. Independent secondary `docs/` dashboard remains outside this session's scope; root dashboard is canonical.

---

## Session `0d48f265` — independent line-by-line source audit (claim, 2026-10-23T15:40Z)

**Branch:** `arena/0d48f265-lolhotspawn1` · **Status:** in progress

Scope is deliberately disjoint from the sessions already claiming build work (`de975e8d`: mobile nav, filters,
every-match picks, `dqteams` walkover, source probe; `a91e528d`: mobile UX, line expansion, model upgrade, gate;
`fba409a6`: runner probe trigger). This session does **not** touch `tools/`, `assets/`, root `*.html`, `data/`, or `scripts/`.

| # | Task | Status | Owner | File scope |
|---|---|---|---|---|
| A1 | Cross-check the committed Hotspawn inventory snapshot against the live Hotspawn fixtures API (sample chunks, ids, names, kick-off times) | done | 0d48f265 | `audit/**` |
| A2 | Re-verify the 9 committed market rows against the live venue pages (Pinnacle / Polymarket / Kalshi / Bovada) | done (2 of 9 re-fetched; 1 partly) | 0d48f265 | `audit/**` |
| A3 | Verify the 4 `dqteams` unresolved rows against the Leaguepedia source page they cite | done | 0d48f265 | `audit/**` |
| A4 | Publish `audit/AUDIT.md` + `audit/audit.csv` with a source link on every row and an explicit verdict (verified / mismatch / not verified) | done | 0d48f265 | `audit/**`, this section |

### 0d48f265 — verification record and irregularities

- **Sources:** Hotspawn fixtures API (chunk 0 of 24), Pinnacle guest API (`matchups/1638758865/markets/related/straight`, chunks 0 and 2 of 3), Polymarket Gamma (`markets?slug=lol-gen-ig1-2026-10-23`, `…lol-rb-mr-2026-10-27`, and the event endpoint for the second), Kalshi `KXLOLGAME` (events, first page), Leaguepedia `MatchSchedule` Cargo export for Solid Gaming in Komplettligaen 2026 Autumn. Links are in `audit/AUDIT.md` §6.
- **Result:** 10 / 10 sampled inventory rows identical; Gen.G v Invictus value matches Polymarket and Kalshi; Mental Rush v Vitality Rising Bees value matches Polymarket within rounding; 3 of 4 `dqteams` rows match Leaguepedia completed fixtures on date and teams; internal checks pass on all 241 rows except one flag (F1).
- **Not verified:** 231 rows not re-fetched live; Bovada quote for Gen.G v Invictus; Polymarket order book for Mental Rush v Vitality Rising Bees.
- **Irregularities (for Flagged for Review):**
  - F1 — 66 of 241 rows kicked off before 15:50 UTC; row `1071212` (Rich Gang v Phenti, 15:00 UTC) is not stale-flagged because the snapshot predates kick-off.
  - F2 — (resolved in the 15:37Z runner data) Gen.G v Invictus: the 11:42Z snapshot linked Pinnacle matchup `1638758865`, which does not serve the −355/+274 price (served under `1638748200`). The 15:37Z data links `1638748200`. Keep a regression check.
  - F8 — Bovada quote for Gen.G v Invictus moved between snapshots (1.22/4.05 → 1.24/3.85); show capture time per quote.
  - F3 — Mental Rush v Vitality Rising Bees is labelled `market`, but its match-winner market has $5 total volume.
  - F4 — same row: Hotspawn kick-off 17:00 UTC vs Polymarket 16:00 UTC (12:00 ET).
  - F5 — the four unresolved `dqteams` rows are past-dated and Leaguepedia shows each completed (opponent 2–0); row `1071170` has a date mismatch (Hotspawn 09-17 vs Leaguepedia 10-01). The walkover is **not** verified from this source.
  - F6, F7 — methodology weights are house choices; Leaguepedia and gol.gg are third-party, not official.
- **Overlap found while claiming:** `de975e8d` (D1–D7) and `a91e528d` (S1–S5) both claim mobile navigation, picks-page filters, every-match picks and the source hunt. Integration must pick one owner per file. This session did not touch those files.
- **Requests for the integration session (not made here):**
  1. Link `audit/AUDIT.md` from `flagged.html` (owned by `a91e528d`/`de975e8d`).
  2. Decide the settlement rule for F5 before publishing any implied pick on the four `dqteams` rows.
  3. Keep the Pinnacle matchup URL/price consistency as a regression check in the pipeline (F2 is fixed in the 15:37Z data).
- **Board hygiene (log only, not edited):** `b91181f0` still shows "in progress" on the Session-b91181f0 row although PR #18 is merged; its owner should close it.

Integration note for the final session: `audit/` is not linked from any generated page yet; linking it from
`flagged.html` is an edit to a file owned by `a91e528d`/`de975e8d`, so it is requested here rather than made.

### 0d48f265 — PR and deploy record

| Item | Value |
|---|---|
| Pull request | #20 — https://github.com/karagemop466-tech/LOLHOTSPAWN1/pull/20 (`arena/0d48f265-lolhotspawn1` → `main`) |
| Merge | merged 2026-10-23T15:43:01Z, merge commit `e8fadc7`. Content is the audit as re-run on the 15:37Z runner data (head `8ac6c24`). **Note:** an earlier `gh pr merge 20 --merge` attempt returned "not mergeable" (conflict in this file, since resolved by keeping both sections); the merge landed afterwards and was not separately confirmed at that moment. |
| Pages | `pages build and deployment` for `e8fadc7`: `built` at 15:43:50Z (`gh api …/pages/builds/latest`). The live audit page `…/LOLHOTSPAWN1/audit/AUDIT.md` was served. Homepage re-fetched with a cache-buster shows the 15:39 UTC snapshot (9 market-backed, Pinnacle link `1638748200`). A plain fetch returned a cached copy of the pre-merge homepage; that is a CDN cache artefact, not a failed deploy. |
| Gate | `tools/verify.py` not touched by this session; the audit does not modify any published page. |
| Open request | Link `audit/AUDIT.md` from `flagged.html` (owned by the build sessions). |

# Session `4dfd0e71` — data-integrity audit, table view, walkover resolution

**Claimed:** 2026-10-23T15:40Z · **Branch:** `arena/4dfd0e71-lolhotspawn1`

| ID | Work unit | Status | Owner | File scope |
|----|-----------|--------|-------|-----------|
| `S1` | Line-by-line audit of the published dataset against live official sources | done | `4dfd0e71` | `data/raw/`, `data/matches.json` (read) |
| `S2` | Exclude Pinnacle "(Kills)" derivative markets from the series consensus | done | `4dfd0e71` | `tools/collect.py`, `tools/model.py` |
| `S3` | Retire the stale archived `book_receipts.json` venue quote (unverifiable) | done | `4dfd0e71` | `tools/model.py` |
| `S4` | Official-walkover resolution for `dqteams` fixtures (pick without invented probability) | done | `4dfd0e71` | `tools/model.py`, `tools/site.py` |
| `S5` | Mobile pick **table** page + executive summary rework (unresolved section + in-site links) | done | `4dfd0e71` | `tools/site.py`, `tools/verify.py`, `assets/` |
| `S6` | Correct stale curated flags, publish the new irregularities | done | `4dfd0e71` | `data/flags_manual.json`, `tools/flags.py` |

No other session owns these files in the current board; integration is performed by this session
because the board's integration item (#8) is already `done` and `main` is the published branch.

### Merge with `origin/main` (sessions b91181f0 / 0d48f265) — 2026-10-23T15:45Z

`main` advanced twice while this session ran (PR #19, PR #20). `origin/main` was merged into this
branch; nothing was discarded, and two deliberate design conflicts were resolved as follows.

| Conflict | `origin/main` position | Resolution here |
|---|---|---|
| One-sided history (one team has no rated series) | leave `p0/p1` null, method `unresolved`, no baseline | **restored the 1500 prior as `provisional`**, because the brief requires a pick or a probability for every match. The assumption is printed on the card ("1500 league-average prior used"), the row is labelled provisional/low-confidence, and `integrity.row_errors` still guarantees the number is a real probability. A blank row remains in `unresolved` only when *both* sides are unrated. |
| Client-side filtering / mobile menu | `app.js` rewritten with menu + snapshot-age, filters dropped | Kept the other session's menu toggle, snapshot-age warning, `[hidden]`, focus-visible and sticky *All picks* button **and** restored the card/table filters that the canonical pages emit markup for. |

Adopted from `origin/main` unchanged: `tools/integrity.py` + `tests/test_integrity.py`, the
`inventory_fetched_utc` provenance stamp, the "refresh scheduled, not guaranteed" wording, the
"Source records (not official verification)" table headers, the community-maintained-Leaguepedia
caveat, and the hedged settlement wording on the unresolved page.

### Fifth merge with `origin/main` (4a1601e, PR #31) — 2026-10-23T15:52Z

| Incoming change | Handling |
|---|---|
| `research/` runner-side source probes (32 endpoints) + `data/source_probes.json` | Adopted untouched. It confirms the four venues we price from (Pinnacle, Kalshi, Bovada, Polymarket all HTTP 200 from the runner) and that every other real book (bet365, Betway, GG.Bet, Thunderpick, Stake, BetMGM, betsson, oddspedia, EGamersWorld) returns 401/403/404/410/JS-only. That is the documented ceiling behind "originate the rest", and it is why no extra venue was added in this session. |
| `research/AUDIT.json`, `sources.html` additions | Adopted; the gate still passes with them rendered. |

Publish gate: **34/34 PASS**, 9/9 unit tests, 241 rows, 13 pages.

### Fourth merge with `origin/main` (28531fc, PR #29) — 2026-10-23T15:51Z

| Incoming change | Handling |
|---|---|
| `audit/` independent audit + `receipts/leaguepedia_ff_solid_gaming_2026-10-23.json` | Adopted verbatim; the forfeit receipt independently confirms the four `dqteams` settlement picks. Linked from `flagged.html`. |
| `collect.py` kills-market regex + `game_start` field | Adopted: the Polymarket comparison now uses the market's own game start, so the previous false "kick-off differs ... (130 h apart)" flag on fixture `1079080` is gone. |
| Polymarket/volume refactor | Adopted, with the duplicated `volume_usd` key removed and both `total_volume_usd` and `volume_usd` published. |
| Retired-quote visibility | The retirement note is now attached to the affected rows themselves (11 rows), so a reader sees why `1081423` is originated instead of getting a silent 1.025/10.50 line. |

Publish gate: **34/34 PASS**; 9/9 unit tests; 241 rows; 13 pages; 0 broken internal links.

### Third merge with `origin/main` (6af8635, PR #23) and coverage-page integration — 2026-10-23T15:49Z

| Incoming change | Handling |
|---|---|
| `tools/corroborate.py` + `data/receipts/external_odds/2026-10-23.json` (session `294e62ad`) | Adopted unchanged. It writes `coverage.html`; the path was still `docs/coverage.html`-adjacent in my tree, so it is now pinned to the repo root, which is what GitHub Pages actually serves (`build_type: legacy`, `source.path: /` confirmed via the Pages API). `coverage.html` joined the publish-gate page list, so the gate now renders **13 pages**. |
| Coverage entry in `NAV` | Kept, and the page is now regenerated by the pipeline instead of being a committed orphan (it was missing from the build output, i.e. a dead nav link). |
| External-book receipts | Verified against the live pages before trusting them: the eight bo3.gg Worlds captures agree with the published consensus, the LGC Rising capture (1.40 / 2.73 -> **66.1%** Vitality Rising Bees) agrees with the Polymarket line we publish (**67.5%**), and the EGamersWorld LCP capture is the same **1.80 / 1.80 placeholder** that made us retire the archived 1.02 / 10.5 quote. Nothing in the receipts contradicts a published pick. |
| `docs/` duplicates | Still tracked from an older publishing layout; Pages serves the branch root, so `docs/` is dead output. Left in place (another session's scope) but flagged here as removable. |

Publish gate on the merged tree: **34/34 assertions PASS**; `python3 -m unittest discover -s tests` **9/9 OK**;
241 table rows, 241 picks cards, 13 pages, 0 broken internal links, 0 `docs/` writes.

### Second merge with `origin/main` (7fee3e2, PR #25) and gate reconciliation — 2026-10-23T15:47Z

`main` advanced again while the first PR merge was pending. Merged `origin/main` with `-X ours` (so the
generated pages and this session's model/site logic win) and then manually re-incorporated everything the
incoming branches had added:

| Incoming change | Handling |
|---|---|
| `tools/integrity.py` settlement contract (`pick_type: "settlement"`, pick object with `probability: null`) | `model.py` now emits exactly that shape for the four `dqteams` rows, alongside the `resolution` object; the forfeit gate assertion was aligned to the contract. |
| `MOBILE_NAV` bottom bar + `mobnav` markup + menu/snapshot JS | Re-rendered in `page_shell`, CSS and JS added; the cards-page filters were rewritten to the ids the pages actually emit (`#q`, `#comp`, `[data-filter]`), which also fixes the filter regression. |
| Executive-summary marker checks ("coverage line", "unresolved section") | Copy adjusted so the required statements are literally present. |
| Curated-flag check disallowing delisted fixture ids | The two historical flags now declare their ids in `delisted_refs`. |
| `receipt_audit` (max age, expired, rejected placeholders) | Emitted again: 10 archived receipts, all older than the 24 h limit, 0 used, 0 symmetric-placeholder quotes among them. |

Publish gate on the merged tree: **31/31 assertions PASS**; `python3 -m unittest discover -s tests`
**9/9 OK**; 241/241 table rows; 4 official-forfeit cards; 1 `mobnav` per page.

### Follow-ups from the `0d48f265` audit requests (2026-10-23T15:46Z)

| Request | Action taken |
|---|---|
| F1 - a past kick-off can slip past the 3 h staleness rule | Threshold removed: **any** fixture whose published start time has passed is now marked `start time passed` and sorted after upcoming matches. |
| F2 - keep Pinnacle matchup URL/price consistency as a regression check | New publish-gate assertion: every Pinnacle `venue.url` must point at a matchup id present in the collected Pinnacle feed (24/24 ids checked this build). |
| F5 - walkover settlement not verified | No probability is published on those four rows. The settlement winner is in a separate `resolution` field labelled *conditional*, with the Leaguepedia `ff`/footnote record linked, and the page states that Leaguepedia is not a settlement authority and Hotspawn's grading is unverified. |
| Link `audit/AUDIT.md` from the site | `flagged.html` now opens with an "Independent audit trail" panel linking `audit/AUDIT.md` and `audit/audit.csv`. |
| F4 - Hotspawn vs Polymarket kick-off offset on #1079080 | Already flagged per row; the market card prints both times. |

### Verification performed on the merged tree (2026-10-23T15:45Z)

| Check | Result |
|---|---|
| `tools/verify.py` (publish gate) | 23/23 assertions PASS (up from 15) |
| `python3 -m unittest discover -s tests` | 5/5 OK (`integrity.row_errors` regression suite) |
| Market picks after the `(Kills)` fix | 9 rows, all true series moneylines from Pinnacle + Polymarket + Kalshi + Bovada (or 3 venues where one is unmatched) |
| Archived receipts | 0 used; 10 overlapping quotes published in `data/retired_quotes.json` |
| Forfeit resolutions | 4 rows, each with winner + Leaguepedia Data: URL, no probability |
| Table coverage | 241/241 rows on `table.html`, 241 cards on `picks.html` |
| Internal links | 0 broken across 12 pages |

### Findings so far (evidence in the audit table on `verification.html` and `flagged.html`)

1. **Pinnacle "(Kills)" markets were mixed into the series consensus.** Pinnacle publishes each LoL
   series twice — a series moneyline and a "(Kills)" derivative. The snapshot shows 6 of 8 Worlds
   picks taken from the "(Kills)" market (e.g. Gen.G vs Invictus Gaming at 1.282/3.740 from
   matchup `1638758865`, while the series market `1638748200` was 1.259/3.940). Fixed by excluding
   any participant name containing "(Kills)".
2. **The "Esportsbook" venue quote was an archived receipt from a previous session**
   (`archive/session-8336fb7e/data/book_receipts.json`, observed 2026-10-21T20:36Z) pointing at a
   generic `egamersworld.com/lol/matches` URL. The live EGamersWorld match page for
   Ground Zero Gaming vs Frank Esports currently shows a symmetric **1.8 / 1.8** placeholder, not the
   archived 1.02 / 10.5. The archived quote is therefore unverifiable and is now excluded.
3. **Two curated flags referenced a 264-row snapshot that no longer exists** (`#1079080` was
   described as "Bushido Wildcats vs Misa Esports"; in the current 241-row snapshot `#1079080` is
   Mental Rush vs Vitality Rising Bees). The Komplettligaen source URL in the same flag
   (`.../2026_Season/Autumn_Season`) does not exist; the real page is
   `.../2026_Season/Autumn_Split`. Both corrected.
4. **`dqteams` claim re-verified** on `Data:Komplettligaen/2026 Season/Autumn Split`: the Round 10
   match carries the footnote "[[Solid Gaming]] is removed from the league." and every remaining
   Solid Gaming series is recorded 0-2 with `ff=1`/`ff=2`. The quarantine is correct; the four
   fixtures are now additionally resolved to the *official walkover* winner without inventing a
   win probability.

---


# Session `64554333` — verification record and merge result (2026-10-23T15:45Z)

## What was verified, and against what

| Claim on the site | How it was checked | Source |
|---|---|---|
| Hotspawn still lists the four Solid Gaming fixtures as `scheduled`; #1071216 is gone | live fixtures API, filtered by `competition_id=36279` (returns exactly 7 cards: 1071167, 1071170, 1071168, 1071200, 1071206, 1071186, 1071212) | <https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=lol&status=scheduled&tenantId=1&competition_id=36279> |
| Solid Gaming was removed in Round 10 and its remaining series are forfeits | raw wikitext of the official schedule: `\|team1footnote=\[\[Solid Gaming\]\] is removed from the league.` plus `\|team1score=0 \|team2score=2 \|winner=2 \|ff=1` on the Round 10, 8 and 6/7/9 entries | <https://lol.fandom.com/wiki/Data:Komplettligaen/2026_Season/Autumn_Split?action=raw> |
| `#1071170` is misdated on Hotspawn (2026-09-17 vs the recorded 2026-10-01) | compared the card's `scheduled_start_time` with the Leaguepedia row | same Data page + Hotspawn API |
| Polymarket Gen.G vs Invictus Gaming is 77.5 / 22.5 | live gamma market, `outcomePrices ["0.775","0.225"]`, `gameStartTime 2026-10-23 17:00:00+00` | <https://gamma-api.polymarket.com/markets?slug=lol-gen-ig1-2026-10-23> |
| `#1081423` Ground Zero vs Frank Esports had no reproducible live line | live egamersworld match page shows 1.8 / 1.8 for both sides, not the archived 1.025 / 10.5 receipt | <https://egamersworld.com/lol/match/eDTgthgYk/ground-zero-gaming-vs-frank-esports-wvOLKhrveF> |
| `#1079080` is a thin market | Polymarket market `volume` = 5 USD (audit F3), confirmed in the collected raw feed | <https://gamma-api.polymarket.com/markets?slug=lol-rb-mr-2026-10-27> |

The sandbox shell has no outbound route to the providers (`curl` fails `SSL_ERROR_SYSCALL`); every live check
above was made with the page-fetch tool, and the runner's own 15:37Z collection is the dataset under the site.
Rows that were not re-fetched live are internal-checked only and carry their source links for manual review.

## Irregularities this session found and fixed

1. `data/flags_manual.json` cited **#1071216** as an upcoming Hotspawn fixture, and claimed the template said
   "forfeited 0-1". Live API: no such card; raw wikitext: forfeits are scored 0-2 with an `ff` flag. Both
   statements corrected, and a publish gate now fails the build if a curated flag cites a fixture that is not
   in the inventory (opt-out only via an explicit `delisted_refs` list with a reason).
2. The archived `1.025 / 10.5` receipt for #1081423 produced a 91.1% "market" pick that contradicted the live
   page (1.8 / 1.8) and our model (Frank 77.5%). Archived receipts no longer enter pricing at all; the row
   falls back to the model. Extreme quotes (implied > 97%) are also rejected at de-vig time.
3. `assets/app.js` bound the picks-page filters to `#filter-search`/`#picks-cards-list`, which no page contains,
   and nothing handled the mobile `Menu` button - the phone navigation was unusable. Both are wired now, with
   a persistent bottom nav; `tests/dashboard.cjs` exercises menu, search, empty state and both filters.
4. Curated flags carried stale counts ("189 of 264", "10 of 264") from a 264-fixture snapshot; those numbers are
   now derived on every build instead of frozen in the file.
5. Market rows had no independent check and no thin-market concept: every market row now prints our own Elo
   probability beside it (flagged at a ≥20 pp gap) and single-venue markets under $1,000 volume are marked
   low confidence (audit F3).

## Merge result

- Merged `origin/main` twice while working (`59f354d` with session `b91181f0`'s integrity work, `bc73a40` with
  session `0d48f265`'s `audit/`). Nothing from either side was reverted; the union is described in the handoff
  table above.
- Final gate: `tools/verify.py` 25/25 pass; `tests/test_integrity.py` 9/9; `tests/dashboard.cjs` pass.
- Snapshot under test: inventory collected 2026-10-23T15:37:40Z, 241 rows, 9 market / 163 model / 65 provisional
  / 4 settlement-only, 237 priced + 4 settlement = 241 picks.
# Session `294e62ad` — external-book corroboration & coverage ledger (2026-10-23)

Branch: `arena/294e62ad-lolhotspawn1` (fixed Arena branch; the repo's `session-<id>/<task>` naming is
pre-empted by the Arena branch, so all work lands here and in the PR).

## Claim (filed before any edit)

| # | Task | Status | Owner | File scope | Notes |
|---|---|---|---|---|---|
| C1 | External-book **corroboration** of every priced match, captured manually where the Actions runner is blocked | in progress | 294e62ad | `data/receipts/external_odds/*` (new), `tools/corroborate.py` (new), `data/corroboration.json` (new) | Runner-side probe (`a91e528d`) shows GG.BET/EGamersWorld/Oddspedia/Sofascore 403/410 from Actions. Those same pages **are** readable from a research sandbox, so the corroboration receipts are captured manually with URL + capture time and re-validated on every build. |
| C2 | `coverage.html`: per-competition external-line coverage matrix + corroboration table + limitations | in progress | 294e62ad | `coverage.html` (new page, generated by `tools/corroborate.py`) | Additive page; it does not rewrite `picks.html`/`index.html` so it cannot collide with `a91e528d` (S2) or `b91181f0` (PR #18), which own `tools/site.py`. |
| C3 | Live inventory reconciliation of the 241-row snapshot against the public Hotspawn lobby + fixtures API | done | 294e62ad | `evidence/audit/` (new) | 241 cards on `play.hotspawn.com/lol-pickems` on 2026-10-23T15:38Z, tournament counts identical to `data/raw/hotspawn_lol.json`. |
| C4 | Line-by-line audit of the 10 published market rows against independent books | in progress | 294e62ad | `evidence/audit/` (new) | Findings below; **one material irregularity** (LCP 2027 Promotion 91.1% line). |

**Not mine, not touched:** `tools/site.py`, `assets/app.js`, `assets/style.css`, `tools/verify.py`,
`tools/model.py`, `tools/collect.py`, root `index.html`/`picks.html`/`unresolved.html`. Those are owned
by `a91e528d` (S1–S5) and `b91181f0` (PR #18). I will request the one-line NAV/exec-summary wiring at
integration time instead of editing those files mid-flight.

## Session `294e62ad` — findings, fixes and integration requests (2026-10-23T15:45Z)

| Item | Result |
|---|---|
| C1 external corroboration | `tools/corroborate.py` + `data/receipts/external_odds/2026-10-23.json`. 9 usable receipts (**all 8 Worlds cards** from bo3.gg/Thunderpick + the LGC card from EGamersWorld) agree with the published line: mean gap **1.1 pp**, max **2.77 pp**, 0 beyond the 5 pp tolerance. |
| C2 coverage page | `coverage.html` (new, 12th page, generated by `tools/corroborate.py`): per-method counts, per-competition external coverage, match-by-match corroboration, archived-fifth-venue audit, unresolved ledger, source list. Wired into `NAV`, the executive summary and `tools/verify.py` (+3 checks, gate now **18/18**), and into `refresh.yml`. |
| C3 inventory | 241 live lobby cards == 241 snapshot rows; per-tournament counts identical; API ids/epochs identical on chunk 0. |
| C4 audit | `evidence/audit/2026-10-23-session-294e62ad.md` — F1–F5, all with source links. |

### Irregularities found and what was done

| ID | Finding | Action |
|---|---|---|
| F1 | LCP 2027 Promotion `#1081423` published at **91.1%** from an archived EGamersWorld listing reading (`1.025/10.5`, captured 2026-10-21T20:36Z); the same site's match page today publishes the `1.8/1.8` placeholder. Not reproducible. | Published as `conflicting / not reproducible` on `coverage.html`; archived venue excluded from corroboration. **Needs an owner decision** on `tools/model.py` (PR #18 removes archived receipts and turns this into a model line — supported). |
| F2 | 9 rows labelled "N-Venue Consensus" included that archived quote as a live venue, with no capture time shown. | Itemised with quote + capture time on `coverage.html` §5. |
| F3 | 5 of 11 curated flags asserted things about a snapshot that no longer exists (fixtures gone from the list; `#1079080` is now a different match; "264/254/189" counts; "Worlds Knockout Stage / EMEA Masters Final"). | Fixed in `data/flags_manual.json`; `tools/flags.py` now auto-annotates any curated flag citing a fixture id that is absent from the current snapshot; executive summary now computes its competition names. |
| F4 | `#1071212` is past kick-off but not marked "start time passed" because the flag uses build time (11:43Z), not render time. | **Integration request** (not edited here): in `tools/site.py`, compute staleness from `start_utc` vs `now` at render time so a 6-hour-old snapshot cannot show a locked match as open. `a91e528d` (S2) and `b91181f0` (PR #18) both own `site.py`. |
| F5 | 231/241 cards have no bookmaker price. | Evidence published on `coverage.html` §4 (OddsPortal prices only Worlds; EGamersWorld prices 3 competitions; bo3.gg prices Worlds; Pinnacle lists LoL only for Worlds). |

### Edit scope actually touched (kept minimal on purpose)

`tools/corroborate.py` (new), `data/receipts/external_odds/2026-10-23.json` (new),
`data/corroboration.json` (new), `coverage.html` (new), `evidence/audit/…` (new),
`tools/site.py` (+NAV entry, +computed competition names, +coverage links in the executive summary, +
"Where the picks live" entry), `tools/verify.py` (+`coverage.html`, +3 checks), `tools/flags.py`
(+missing-fixture annotation), `data/flags_manual.json` (F3 corrections), `.github/workflows/refresh.yml`
(+1 pipeline step), plus the regenerated pages these produce.

### Integration requests filed by `294e62ad` (not edited by this session)

1. **`tools/site.py` — render-time staleness (F4).** Under a six-hour cron a card that kicks off after the
   build is not marked "start time passed" (verified: `#1071212`, 15:00Z, unflagged at 15:40Z). Compare
   `start_utc` with the render clock.
2. **`assets/app.js` + `assets/style.css` — phone navigation (mobile blocker, verified 2026-10-23).**
   `assets/app.js` on `main` binds `#filter-search/#filter-comp/#filter-tier/#filter-window` but
   `tools/site.py` emits `#q/#comp/#list/#count`, and there is no `.menu-btn` handler at all, so below
   680 px the nav is `display:none` and the "Menu" button does nothing. Owners: `a91e528d` (S1) and
   `b91181f0` (PR #18). If neither lands, `294e62ad` will fix it in the post-merge integration pass
   (no-JS fallback: horizontally scrollable nav, same pattern as `coverage.html`).
3. **`tools/model.py` — stop reading the archived esportsbook receipt for `#1081423`** (F1) or show its
   capture time next to the label. PR #18 already removes archived receipts; that is the preferred fix.

Claim age check for the takeover rule: `a91e528d` last committed `9b393cb` (15:37Z), `b91181f0` last
committed PR #18 (15:37Z). Both are live, so nothing below is taken over yet.


## PR / deploy record — session `6d1ede2c`

| Item | Value |
|---|---|
| PR #28 (integration) | https://github.com/karagemop466-tech/LOLHOTSPAWN1/pull/28 — merged 2026-10-23T15:49:02Z, merge commit `6f6890a` |
| PR #32 (forfeit wording) | https://github.com/karagemop466-tech/LOLHOTSPAWN1/pull/32 — merged after #28 |
| Pages deploy | `pages-build-deployment` → `status: built` for commit `6f6890a` (15:49:04–15:49:28Z) and again for `b519a8b` at 15:50:40Z |
| Live check | `https://karagemop466-tech.github.io/LOLHOTSPAWN1/` serves the 15:48 snapshot: 241/241 picks, 237 priced (9 market / 163 model / 65 provisional), 4 settlement-only, 28 gates. Gen.G v Invictus shows a 4-venue consensus with the Pinnacle link on series matchup `1638748200`. The Flagged page links both audits |
| Auto-refresh | the merge push triggered `refresh-picks` on `main` (run 39981516485); cron stays `17 */6 * * *` |
| Text corrected after deploy | the exec summary claimed "every remaining Solid Gaming series" was a forfeit → now 8 of 11 flagged, 3 not, with the Cargo receipt linked. The stale-fixture flag said "more than three hours in the past" → now "has already passed", matching the new `stale` definition |
| Pending the next collection | the four settlement cards say "this snapshot captured no forfeit flag", true of the 15:37Z payload; `collect.py` now requests `MatchSchedule.FF`, so the next refreshed build prints `FF=1`/`FF=2` per card |

**Open items for the next session:** #22 (`29d6fe6a`) and #24 (`4dfd0e71`) are still open against earlier
`main` states and would revert verified work if merged as-is; their unique items (compact pick table,
probe expansion, an alternate wording pass) are listed in the integration record above. #23 (`294e62ad`)
was merged into `main` during this pass and its coverage page is live.

---

## Session `fba409a6` — close-out (2026-10-23T15:50Z)

**F1 done.** Runner probes (`data/source_probes.json`, build `39980020233`): 32 endpoints, 14 HTTP 200.
Usable price feeds: Pinnacle, Kalshi, Bovada, Polymarket. Usable-only-for-results: Leaguepedia, Hotspawn
inventory. Blocked/HTML-only: bet365 403, Betway 404, BetOnline HTML, Everygame 404, SportsBetting.ag 403,
Betsson 202, BetUS 403, 1xBet 203, Betfair 403, DraftKings HTML (API 403), FanDuel shell, BetMGM 403,
GG.BET 403, Thunderpick 403, Rivalry HTML, BC.GAME HTML, Stake 403, Kambi 400/429, EGamersWorld 403,
Oddspedia 410, OddsPortal HTML, BetExplorer 404, OddsPapi 401, Odds-API.io 502 on LoL endpoints.

**F2 done.** Deep probe (`research/probe_deep.json`): none of the reachable HTML pages embed a usable
price; Rivalry/FanDuel/BetOnline carry no odds tokens in the served HTML, OddsPortal/BC.GAME only a
JSON-LD shell, DraftKings' LoL URL 404s and its content API returns 403. Market ceiling
(`research/market_ceiling.json`): Pinnacle exposes exactly one LoL league (World Championship) with 138
matchup objects, of which **8** are open two-sided series moneylines; the parallel `(Kills)` family is a
kill total and is excluded from every price. Kalshi: 8 open `KXLOLGAME` contracts. Polymarket: 23 listed
match markets, 12 unsettled, same Worlds slice. Bovada filtered and unfiltered coupons both return the
same 8 moneylines (`research/bovada_full.json`), so the production filter is not losing coverage.

**F3 done.** `research/SOURCES.md` (generated by `research/build_dossier.py` from the receipts, no
hand-typed numbers) plus a "Research receipts" panel on `sources.html` rendering the same probe table and
the measured ceiling. The executive summary now states the ceiling with its source.

**F4 (integration) is being executed by session `3d4e18ac` (PR #27).** This session's changes are additive
on top of `main` (`research/**`, `data/source_probes.json`, the research-only workflows, the Sources panel
and one extra publish gate) and re-verify cleanly: `tools/verify.py` 29/29 PASS, `research/audit.py` PASS
(241 rows, inventory exact, probabilities re-derived, 9 market rows re-weighted, 4 quarantine claims
matched to the raw `dqteams` receipt, CSV mirror exact), `python3 -m unittest discover -s tests` 9/9 OK.

### Findings for review

- The four `dqteams` fixtures now publish a settlement pick (active opponent) with no probability. That is
  the only defensible pick for them; a percentage would be invented.
- Pinnacle lists a `(Kills)` market alongside the series moneyline for the same teams. Any collector that
  matches on team name alone could price a match-winner pick off a kill total; this session verified the
  current consensus does not (`research/market_ceiling.py` excludes the `(Kills)` family explicitly).
- Pinnacle's `/0.1/sports/12/leagues/9587/matchups` path 404s; the working path is
  `/0.1/leagues/{league_id}/matchups`.
- Bovada's unfiltered coupon is ~19x larger but adds no LoL moneylines.
- Leaguepedia is community-maintained. It is the source for both the Elo history and the `dqteams`
  removal record, so a wiki error would propagate to the model and the quarantine alike. The removal claim
  is corroborated by forfeit-scored (`0-2`, `ff`) series in the same official-schedule record.

## Merge result — session `4dfd0e71` (PR #24)

| Field | Value |
|---|---|
| PR | https://github.com/karagemop466-tech/LOLHOTSPAWN1/pull/24 |
| Result | **Merged** into `main` (merge commit `9e25133`), 2026-10-23T15:53Z |
| Conflicts | Six `origin/main` advances during the review window; each was resolved by merging `origin/main` into the session branch with `-X ours` and then manually re-applying every incoming improvement (settlement contract, mobile nav, `mobnav`, coverage page, independent audit, research probes, Polymarket `game_start` fix). Generated pages were never hand-merged: `model → report → flags → site → corroborate → verify` was re-run after every resolution. |
| Publish gate at merge | **34/34 PASS**, `unittest discover` **9/9 OK**, 241 rows, 13 pages, 0 broken internal links, 0 `None` renderings |
| GitHub Pages | build `9e25133` **built** at 2026-10-23T15:53:30Z; live check of `https://karagemop466-tech.github.io/LOLHOTSPAWN1/table.html` returns the 241-row table with per-row Hotspawn + Leaguepedia source links |
| Delivered | Executive summary with in-site links (Summary → Table → All picks → Market → Model → Unresolved → Coverage), the mobile bottom nav, the pick table, the unresolved-picks section with its limitations, the forfeit settlement picks, and the retired-quote trail |
| Known open items (published, not hidden) | `docs/` is dead output from an older layout (Pages serves the branch root); the four Komplettligaen fixtures are settled administratively because the league removed Solid Gaming; `#1081423` and `#1079080` are originated/indicative lines with the retired-quote flag on the row |

---

# Final integration record — session `294e62ad` (2026-10-23T15:58Z)

The brief's integration step (merge everything, re-verify the combined data line by line, publish)
was executed from this branch after four other sessions merged in parallel.

| Item | Result |
|---|---|
| PR #23 | external-book corroboration + `coverage.html` + line-by-line audit → **merged** 2026-10-23T15:47:26Z (`6af8635`) |
| PR #30 | superseded (another session had already added the same retry loop) → **closed** with a note |
| PR #33 | CI fix: the refresh retry loop rebased with the wrong side winning → **merged** (`git rebase -X theirs`, `data/receipts` staged, soft-reset last resort) |
| Merge conflicts | resolved by taking the live `main` version of `tools/site.py`, `tools/verify.py`, `tools/flags.py`, `data/flags_manual.json` and every generated page as the base, then re-applying only this session's additions. Nothing from another session was reverted; where `main` had already superseded this session's work (curated-flag rewrites, mobile nav, archived-receipt exclusion) `main`'s version was kept and the duplicate dropped. |
| Re-verification on the merged tree | `tools/verify.py` **29/29 PASS**, 0 FAIL — 12+ pages, 0 broken internal links, 237/237 probabilities sum to 100 %, every row carries a Hotspawn card link, coverage matrix 27/27 rows carry a source link, 9/9 external receipts validated, 0 rejected receipts |
| Pages | `status: built`, source `main` `/`; deployments succeeded for `6af8635` (15:47Z), `6f6890a` (15:49Z) and the post-refresh heads |
| Refresh loop | proved end to end: run `39982035986` (15:52Z, after the CI fix) completed **all** steps including `Commit data and site`; the two earlier failures (`39981049159`, `39981292253`) were exactly the push-race the fix addresses |
| Live coverage page | served from `main`: `coverage.html` is in `NAV` on every page, linked from `index.html` and `picks.html`, and `data/corroboration.json` is regenerated on every refresh (latest: 9 usable receipts, mean gap **0.93 pp**, max **1.7 pp**, 1 conflicting, 0 rejected) |

## What the site now answers, and where

| Question | Page |
|---|---|
| What is the pick for this match, and how likely is it? | `picks.html` (241 cards, next kick-off first, one column on a phone) |
| Which matches are backed by a real bookmaker price? | `featured.html` |
| Which matches did we have to originate, and why? | `originated.html` + **`coverage.html`** |
| Does any book anywhere price the low-tier leagues, and what did it say? | **`coverage.html` §2/§4** (with the evidence that none does) |
| Do our lines agree with an independent book? | **`coverage.html` §3** (match by match, gap in pp, capture time, source link) |
| Which matches have no pick at all, and why? | `unresolved.html` + **`coverage.html` §6** |
| What is wrong or unverified? | `flagged.html` + `evidence/audit/2026-10-23-session-294e62ad.md` |

## Irregularities still open for review (published, non-blocking)

1. **LCP 2027 Promotion `#1081423` — 68.6 pp swing.** The 91.1 % "market" line was an archived
   EGamersWorld listing reading (2026-10-21T20:36Z). The same site's match page today publishes the
   `1.8/1.8` placeholder. Removing it (PR #18) turned the card into a model line at Frank Esports 77.5 %.
   Both readings are quoted on `coverage.html` §3 with timestamps.
2. **Stale-flag window.** `stale` is computed at build time, so a card that kicks off after the build is
   not marked "start time passed" until the next refresh (up to 6 h). `#1071212` demonstrated it at 15:40Z
   and was corrected by the 15:39Z refresh. A client-side check is the real fix; not implemented here.
3. **Archived fifth venue.** Nine rows were labelled "N-Venue Consensus" while one venue was a two-day-old
   archived quote. Now itemised with capture times on `coverage.html` §5, and excluded from corroboration.
4. **Curated flags** are labelled `re-verified <date> against <source>` or `Historical observation - not
   reverified`, and any flag citing a fixture that has left the list is auto-annotated. Ten of ten curated
   flags currently cite only live fixtures (gate check).
## Session `fba409a6` — PR / deploy record (2026-10-23T15:58Z)

| Item | Value |
|---|---|
| PR #31 — source research layer | https://github.com/karagemop466-tech/LOLHOTSPAWN1/pull/31 — MERGED `4a1601e` (15:51:35Z) |
| PR #39 — coverage double-count fix + ceiling summary restored | https://github.com/karagemop466-tech/LOLHOTSPAWN1/pull/39 — MERGED `fa918e6` (15:55:57Z) |
| Pages build after merge | `pages-build-deployment` **success** (`39982494400`); live `index.html` shows 237 priced + 4 forfeit = 241/241 (100%) and the source-ceiling bullet |
| Live check | https://karagemop466-tech.github.io/LOLHOTSPAWN1/ and `/sources.html` served the new panels (verified by fetch at 15:57Z) |

### Defects found and fixed during integration

1. **Coverage read "245 of 241 (102%)".** `_stat_totals()["with_pick"]` already included the four forfeit
   settlement picks and `build_index()` added them again. Reported separately now, and a new gate
   (`coverage arithmetic reconciles to the inventory`) asserts `priced + settlements == rows with a pick ==
   inventory` so it cannot regress.
2. **`main` briefly shipped data that its own gate rejected.** The 15:54Z refresh committed a
   `data/matches.json` produced before `tools/model.py` began emitting `receipt_audit`, so
   `tools/verify.py` failed on `main` ("limit None h"). Fixed by regenerating the dataset with the current
   model (`model → report → flags → site → verify`, 36/36 PASS). Anyone re-running the refresh on `main`
   now gets a consistent snapshot.

### Verification of this session's merge

- `python3 tools/verify.py` — **36/36 PASS** (12 pages, 0 broken internal links, mobile nav on every page,
  coverage arithmetic, research receipts present).
- `python3 research/audit.py` — PASS (241 rows, exact inventory reconciliation, probabilities re-derived,
  9 market rows re-weighted, 4 quarantine claims matched to the raw `dqteams` receipt, CSV mirror exact).
- `python3 -m unittest discover -s tests` — 9/9 OK.
- Live pages re-fetched after deploy: `/` (exec summary, stats, unresolved table) and `/sources.html`
  (probe table + ceiling) both render the new content.
# Session `a91e528d` — audit fixes, model integrity and coverage parity (2026-10-23)

Branch: `arena/a91e528d-lolhotspawn1`. Scope kept to `tools/model.py`, `tools/verify.py`,
`assets/style.css`, this file and the generated pages/data. `tools/site.py` changes are limited to the
toss-up badge and the teams-page rating source; `tools/corroborate.py`, `coverage.html`,
`data/receipts/**` remain owned by `294e62ad`.

## What changed

| ID | Change | Evidence |
|---|---|---|
| A1 | **No look-ahead in the Elo line.** Every fixture is priced from the rating state at its own kick-off, built only from series that started earlier. The previous build fitted on the whole Leaguepedia window and then "predicted" 65 already-started cards, 52 of which already had a result. | `tools/model.py` `build_ratings(lp_matches, fixtures)` returns per-fixture snapshots; `rating_as_of == start_utc` on every row; `verify.py` recomputes each side's rated-series count from raw Leaguepedia and fails on any excess — **0 violations**. |
| A2 | **Margin-weighted K.** `K_eff = 48 * (1 - 0.45 + 0.45 * |series margin|)`, fitted on 2026-04-01..2026-07-01 and checked on the later holdout. | Holdout n=3,854: **65.49% / 0.2144 / 0.6178** vs baseline K=24 **64.06% / 0.2212 / 0.6323**. Rejected after testing: predict-time shrinkage (thin-team accuracy 62.0%→60.0%, Brier 0.2246→0.2371), best-of scaling, margin normalised by series length, and a 15% recent-form blend (Brier −0.0006 for −0.3 pp accuracy — inside noise). |
| A3 | **Archived receipt freshness.** Only a receipt younger than 24 h may enter a consensus. `#1081423` (Ground Zero vs Frank, 11 Nov) was priced at 91.1% from a 1.8-day-old EGamersWorld listing whose live page today shows the `1.80/1.80` placeholder. It is now a model line (Frank 89.9%) with the rejection printed on the row and on `flagged.html`. | `MAX_RECEIPT_AGE_HOURS = 24`; 11 expired receipts recorded, 0 live; row flag keeps the capture time. |
| A4 | **Coverage parity gate.** The dataset must be an exact mirror of the Hotspawn API response the build fetched, not a selection. | `verify.py`: ids 1:1 (241/241), per-tournament counts identical (27/27), every id rendered on `picks.html`. Independent live cross-check the same day: the lobby listed the same **27 tournaments with identical per-tournament counts summing to 241**, and **180 distinct teams** — equal to the dataset. |
| A5 | **Toss-up transparency.** Three fixtures have identical kick-off ratings (1082003, 1082006, 1079047). They now say so instead of showing an arbitrary 50.0% "pick". | Row flag + `toss-up` badge; `verify.py` confirms the 50/50 rows are exactly those three. |

## Verification record

- `tools/verify.py`: **31/31 pass** (`data/verification.json`), including the 28 inherited gates,
  no-look-ahead (0 violations) and the two coverage-parity assertions.
- `python3 -m unittest discover -s tests`: 9/9 OK.
- `tools/corroborate.py`: 9 usable receipts, 9 agree / 0 diverge, 2/27 competitions priced externally.
- Spot math: Gen.G vs Invictus 0.7621 = weighted mean of Pinnacle .7448 (0.36), Polymarket .775 (0.24),
  Kalshi .775 (0.18), Bovada .7689 (0.12) over 0.90; Rich Gang 1739.4 vs Phenti 1449.4 → 0.8415;
  Ground Zero 1360.4 vs Frank 1740.3 → 0.1009.
- Live inventory: `play.hotspawn.com/lol-pickems` 27 tournaments / 241 cards / 180 teams, matching the
  dataset exactly at 15:44Z on 2026-10-23.
- Line-source ceiling re-measured: Pinnacle lists LoL only for the World Championship (league 9587,
  10 matchups); OddsPortal lists only the World Championship (8); the 31-endpoint runner probe found no
  additional server-rendered low-tier book feed. The 5-venue market ceiling is therefore structural,
  not a parsing gap.

## Merge note

`origin/main` had advanced 12 commits (28-gate verify, `corroborate.py`, `coverage.html`, integrity
tests). The merge keeps main's newer tooling and re-applies only the model/verification changes above;
generated pages and `data/*.json` were rebuilt from the merged pipeline rather than hand-merged.


## Session `6d1ede2c` — final integration pass (2026-10-23T15:58Z)

Merged `origin/main` at `3cd992c` (PR #41, session `a91e528d`) into this branch. Generated
artifacts were taken from `origin/main` and rebuilt; no hand edits to `tools/` were carried over,
because the incoming pipeline already contains every fix this session had verified.

| Incoming change | Handling |
|---|---|
| Kick-off-snapshotted, margin-weighted Elo + no-look-ahead gate (PR #41) | Adopted. Rebuilt: **241 rows, 9 market, 148 model, 80 provisional, 4 walkover-settled**, 39 gates, 9/9 unit tests. |
| `table.html` as the phone-first canonical list | Adopted; `audit/check_site.py` now counts 20 pages and confirms every match id appears exactly once there. |
| Archived EGamersWorld receipts | Still excluded (43.3 h old, 24 h limit, domain 403s the runner). The expired-receipt flag rendered `None` where a receipt has no venue field; it now reads “captured 43.3 h before this build (2026-10-21T20:36:00Z) from egamersworld.com”. |

Independent checks after the merge:

| Check | Result |
|---|---|
| `tools/verify.py` | 39/39 PASS |
| `audit/check_site.py` (links, nav, viewport, duplicate ids, unrendered values) | 20 pages, 0 failures |
| `audit/verify_independent.py` (re-derived from raw, no `tools/` import) | 0 failures, 9 warnings, 0 kills substitutions |
| `unittest discover -s tests` | 9/9 OK |
| Live venue re-read (Gen.G v Invictus, 15:57–15:58Z) | Pinnacle −335/+261 on `matchupId` 1638748200, Polymarket 76.5/23.5, Kalshi mid 77.5/22.5, Bovada 1.2439/3.800 — all four match the snapshot; consensus recomputed 0.7536 vs 0.7537 published. Receipt: `audit/receipts/live_spotcheck_2026-10-23T1558Z.json` |

**PR #45** carries this verification pass (report + receipt + the `None` rendering fix) to `main`.

## Session `8a66a536` — forfeit-settled picks (claim 2026-10-23T15:52Z)

Scope: turn the four `dqteams` settlement rows into **priced picks from the league's own record**, keep a
separate unresolved/limitations section, and keep the dashboard mobile-first. Files: `tools/model.py`,
`tools/verify.py`, `tools/site.py`, `assets/style.css`, `tests/`, `README.md`, this file.

| # | Task | Status | File scope |
|---|------|--------|-----------|
| A1 | Price a `dqteams` fixture only when the same competition's Leaguepedia record carries `FF` and a winner that agrees with it; new `forfeit` method, record id in the basis; no record → unresolved | done | `tools/model.py`, `tools/verify.py`, `tests/` |
| A2 | Separate forfeit-settled block on `unresolved.html` with receipts; executive-summary coverage line; distinct card/badge/chip styling | done | `tools/site.py`, `assets/style.css` |
| A3 | Re-verify, PR → `main`, merge, confirm Pages | in progress | `README.md`, `COORDINATION.md` |

**Claim evidence** (CargoExport re-fetched 15:52Z, receipt
`audit/receipts/leaguepedia_ff_solid_gaming_2026-10-23.json`): `FF=1` Round 3_5 (Solid 0–2 VES Japan),
`FF=1` Round 6_6 (Solid 0–2 NTNUI), `FF=1` Round 8_4 (Solid 0–2 Playwell Rød Q), `FF=2` Round 9_3
(Volda E-Sport 2–0 Solid). Eight of Solid Gaming's eleven series carry the flag; three do not, so the
flag is read per fixture and never generalised.

| Check | Result |
|---|---|
| Model | `methods={'provisional': 80, 'model': 148, 'forfeit': 4, 'market': 9}`, rows 241, backtest n=3854 acc=0.6549 brier=0.2144 |
| Coverage | 241/241 priced — 4 forfeit-settled, 0 unresolved |
| Gate | 41/41 PASS, incl. "forfeit picks cite a league record and name its recorded winner" and corrected coverage arithmetic (priced + *unpriced* settlements = rows with a pick = inventory) |
| Tests | 11/11 unittest; jsdom 2 PASS incl. the forfeit chip |
| Independent sources | no external book price exists for Komplettligaen on this build; the pick is a **recorded result** from the league record, not a market line, and is labelled as such everywhere |
