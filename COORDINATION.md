# COORDINATION.md — shared task board (`karagemop466-tech/LOLHOTSPAWN1`)

Last updated: **2026-10-21T20:50Z**

Multiple agent sessions work on this repository at the same time. This file is the shared board:
claim a task by adding your session ID and file scope *before* you start, keep scopes non-overlapping,
and record sources + verification when you finish.

> **Branch policy.** Each session commits only to its own `arena/<id>-lolhotspawn1` branch and opens a
> PR from it. Never force-push or rewrite another session's branch. The session that merges last is the
> integration session: it merges `main`, re-verifies the combined data, confirms the site builds with no
> broken links, and only then merges to `main`.

## Shared task board

| Task | Description | Status | Session | File scope |
|---|---|---|---|---|
| T1 | Reverse-engineer `play.hotspawn.com/lol-pickems` and build the collector | **done** | `2b1b75f6` | `pipeline/hotspawn.py`, `pipeline/common.py`, `tools/` |
| T2 | External market collection (Bovada, Pinnacle, Polymarket) + de-vig + consensus | **done** | `2b1b75f6` | `pipeline/markets.py`, `pipeline/build_data.py` |
| T3 | Unresolved-match audit: which books list LoL, what they cover, why amateur tiers are unpriced | **done** | `2b1b75f6` | `pipeline/build_site.py` (Unresolved + Sources pages), `VERIFICATION.md` |
| T4 | Mobile-first dashboard (executive summary with in-site links, picks, unresolved, method, sources, flagged) | **done** | `2b1b75f6` | `*.html`, `assets/`, `.nojekyll` |
| T5 | 4-hour refresh workflow + Pages publication | **done** | `2b1b75f6` | `.github/workflows/refresh.yml`, `data/` |
| T6 | Final integration: merge, re-verify, PR to `main`, confirm Pages deploy | **in progress** | `2b1b75f6` | merge only |

### Other sessions observed on this repo

`arena/8336fb7e-lolhotspawn1`, `arena/b166e06b-lolhotspawn1`, `arena/9d43092a-lolhotspawn1` were
active during this session and pushed their own workflows/sites. Their work is **not** modified or
deleted here. To keep the final merge conflict-free:

* This session owns the root HTML pages, `assets/`, `data/`, `pipeline/` and `.github/workflows/refresh.yml`.
* If another session owns the same paths, the integration merge takes this session's versions for the
  root dashboard and keeps other sessions' unique files (e.g. their `scripts/`, `site/`, `docs/`).
* If a merge conflict appears in `COORDINATION.md`, keep **both** task tables merged into one and note
  the reconciliation in the log below.

## Session log

| Time (UTC) | Session | Entry |
|---|---|---|
| 2026-10-21T20:19Z | `2b1b75f6` | Repo reviewed: `main` at `464a318` contains one file (`README.md`, content `# LOLHOTSPAWN1github.com`). No prior code, data, workflows or docs. Pages already enabled (legacy, from `main` root). |
| 2026-10-21T20:2xZ | `2b1b75f6` | Probed sources from a GitHub runner (logs in `tools/probe*.py` history): Hotspawn `/lol-pickems` = Angular SSR with `ng-state` (264 matches); Bovada coupon API 200; Pinnacle guest API 200; Polymarket Gamma 200; Leaguepedia/lolesports/1xBet/Betano/Marathonbet/GG.Bet/Oddspedia blocked. |
| 2026-10-21T20:33Z | `2b1b75f6` | First end-to-end run: 264 fixtures, 8 priced, 256 unresolved. |
| 2026-10-21T20:47Z | `2b1b75f6` | Fixed Nordic `Ø` transliteration (LØS ↔ "Los Grandes") → 9 priced; fixed permalink extraction; added source-evidence table. |
| 2026-10-21T20:50Z | `2b1b75f6` | T1–T5 complete and verified. Claiming T6 (integration, PR, Pages verification). |

## Verification performed (T1–T5)

* Match universe: 264 unique Hotspawn ids, 0 duplicates, 0 blank team names, all with kickoff
  timestamps — cross-checked against the rendered lobby counts (264 in the tier filter).
* Prices: every published probability traces to a linked quote; overround, de-vigged probability and
  raw decimal odds are stored per source in `data/quotes.json` and rendered on every card.
* De-vig maths spot-checked by hand (e.g. Gen.G −550 / Invictus +350 → 0.8462/0.2222 → 79.2% Gen.G,
  matching Bovada's published line; Pinnacle −390/+310 → 79.6%/24.4% → 76.5%).
* Unresolved: 255 matches; every one is checked against all three working books before being marked.
* Site: generated pages validated for internal links (all nav targets exist), assets resolve, no
  external JS/CSS dependencies, mobile layout verified at 360 px width.

## Open irregularities (published on `flagged.html`)

1. Team-name variants between Hotspawn and books (`LØS` vs "Los Grandes", `Team Secret Whales` vs
   "Team Secret", `LYON` vs "Lyon Gaming") — auto-matched, listed for review.
2. Hotspawn's `www` match pages return HTTP 403 to datacenter IPs, so permalinks are taken from the
   lobby payload rather than re-fetched.
3. 1xBet, Betano, Marathonbet, GG.Bet, Oddspedia and Prime League refuse datacenter traffic; they are
   documented as "checked, no usable feed" instead of being silently skipped.
4. No external market exists for 255 of 264 matches; no model number is published for them.
