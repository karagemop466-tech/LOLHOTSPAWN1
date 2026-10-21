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
