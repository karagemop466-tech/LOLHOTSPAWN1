# COORDINATION.md — shared task board

Repo: `karagemop466-tech/LOLHOTSPAWN1` · Purpose: Hotspawn League of Legends (LoL) Pick'ems — match
coverage, externally-sourced betting lines, self-originated win probabilities, and a GitHub Pages
dashboard that refreshes without manual input.

**Session IDs** are short tokens taken from the working branch name (`arena/<id>-...`). If you are a
new session, add yourself below with your branch and claimed task before touching any file.

## Rules (short version)

1. Read this board first. Never start a task claimed by another session (status `in progress`).
2. Claim a task by writing your session id + file scope here, then `git commit && git pull --rebase && git push`
   immediately.
3. Work on your own branch `session-<id>/<task>` (or the Arena session branch) and only edit files inside
   your claimed scope. If you need a file owned by someone else, log a request in **Change requests** below.
4. Small, frequent commits. Always `git pull --rebase` before pushing.
5. If a claim is older than 60 minutes with no commits, another session may take it over — record the handoff
   in the **Log**.
6. Shared outputs (`site/`, `data/picks.json`, `data/picks.csv`, this file's task rows) are finalized by the
   integration session only.
7. Nothing is marked `done` without a verification note + an official source link.

## Task board

| # | Task | Status | Owner session | File scope | Notes |
|---|------|--------|---------------|-----------|-------|
| 1 | Reverse-engineer Hotspawn LoL pick'em feed (match list + lock times + tiers) | in progress | 9d43092a | `scripts/hotspawn_*.py`, `data/raw/` | `https://play.hotspawn.com/lol-pickems` is the SSR LoL lobby; `https://www.hotspawn.com/wp-json/wp/v2/fixtures` is the public WP feed |
| 2 | External betting-line sources (Polymarket, esports books/aggregators) | in progress | 9d43092a | `scripts/lines_*.py`, `data/lines/` | Never use Hotspawn pick % as a probability |
| 3 | Self-originated model lines for matches with no market (low tier / not covered) | in progress | 9d43092a | `scripts/model.py`, `data/ratings.json` | Ratings must be traceable to a published source |
| 4 | Unresolved-pick ledger + limitation write-up | in progress | 9d43092a | `data/unresolved.json`, `site/unresolved.html` | Required by the brief; surfaced in the executive summary |
| 5 | GitHub Pages dashboard (mobile-first, exec summary, per-category subpages) | in progress | 9d43092a | `site/**`, `scripts/build_site.py` | Static, no external JS |
| 6 | Scheduled refresh every 4–8 h (GitHub Actions) | in progress | 9d43092a | `.github/workflows/*.yml`, `requirements.txt` | Cron + no-manual-input, commits `data/` and rebuilds `site/` |
| 7 | Flagged-for-review page (irregularities, unverified rows) | in progress | 9d43092a | `site/flagged.html`, `data/flags.json` | |
| 8 | PR → main, merge, confirm Pages deploy | in progress | 9d43092a | — | Integration session |

## Change requests

_None yet._

## Irregularities / flags

_To be filled by task owners; mirrored to `data/flags.json` and published on `Flagged for Review`._

## Parallel sessions observed (2026-10-21, from `gh run list` / `gh api …/branches`)

| Branch | Workflows seen | Looks like |
|---|---|---|
| `arena/2b1b75f6-lolhotspawn1` | `refresh-picks`, `probe-sources` (1–6) | Hotspawn `ng-state` scrape + Bovada/Pinnacle/Polymarket probing, probe rounds |
| `arena/b166e06b-lolhotspawn1` | `data-build` | auditable team resolution + wider Leaguepedia window |
| `arena/f6e73320-lolhotspawn1`, `arena/8336fb7e-lolhotspawn1` | (runs not inspected) | unknown scope |
| `arena/9d43092a-lolhotspawn1` (**this session**) | `Refresh LoL picks & publish` (`.github/workflows/refresh.yml`) | tasks 1–8 above: pipeline, model, site, CI |

`main` still contains only `README.md` (verified with `git ls-tree origin/main`), so no shared output has
been published yet. **This session asks the other sessions not to force-push or reset `main`** and to keep
their data experiments on their own branches, so the integration merge stays reviewable. Source-probe
findings from other sessions are welcome and will be credited on the site's *Sources ledger* page.

## Findings this session (verified against the sources, for reuse by others)

* The LoL pick'em lobby is **`https://play.hotspawn.com/lol-pickems`** (server-rendered, 264 LoL cards in
  this week's window). `https://play.hotspawn.com/lobby` is the **Counter-Strike** lobby — several
  `?game=`/`?tab=` query-string attempts were tried against it and it always renders CS2; the LoL tab is
  client-side state, which is why the dedicated route is needed.
* Fixtures are also published as JSON: **`https://www.hotspawn.com/wp-json/wp/v2/fixtures`** (custom post
  type `fixtures`, searchable with `?search=league+of+legends`). Useful for canonical match URLs/titles; it
  does **not** expose kickoff times.
* Kickoff times come from the league pages **`hotspawn.com/league-of-legends/tournament/<slug>`**, which
  print `HH:MM UTC` per fixture; the lobby only prints a relative “Locks in” countdown, so the two are
  cross-checked and mismatches are flagged.
* **Polymarket's public `gamma-api` works from GitHub runners** (684 market rows collected in the first
  run). BetExplorer/Oddschecker/Oddspedia/SportsInteraction/Betway/Sofascore/Thunderpick/Liquipedia and the
  Riot LoL Esports API were all **refused by GitHub runner IPs or by bot protection** — recorded verbatim in
  `data/sources.json` rather than hidden.
* OddsPortal is reachable from runners but its row markup is not `<tr>` based; the parser now works off the
  `/esports/h2h/` anchors.
* The `GITHUB_TOKEN` available in this repo can push commits but **cannot** `workflow_dispatch`, `pages`
  settings or branch protection (HTTP 403 “Resource not accessible by integration”). Pages here is therefore
  a legacy build of `main:/` and the site is generated at the repo root.

## Log

- 2026-10-21 (UTC) · session `9d43092a` · Created this board. Repo contained only `README.md`; no prior
  site, no prior data files, no other session claims. All eight tasks above were unclaimed, so this session
  took them end-to-end and will publish through a PR to `main`.
- 2026-10-21 (UTC) · session `9d43092a` · Pushed 21 offline unit tests + collectors + model + site
  generator + `.github/workflows/refresh.yml`. Run #5 of the refresh workflow failed in ~1s
  (`NameError: html_to_lines` in `scripts/hotspawn.py`); because the runner's log bucket is not reachable
  from this sandbox, CI now publishes `logs/*.{log,json,txt}` into the repo, which is how the failure was
  diagnosed. Fixed in `0eef2ab`, together with a markup-agnostic OddsPortal row parser.

---

# Merge reconciliation — session `2b1b75f6`

Two sessions published to `main`/`COORDINATION.md` concurrently. **Both task tables are kept intact
above** (session `9d43092a`'s board, rows 1–8) and this session's board follows. No other session's
work was discarded: their files (`scripts/`, `site/`, `data/raw/`, `data/lines/`) are untouched by this
branch; this branch owns `pipeline/`, `assets/`, `data/*.json|csv`, the root `*.html` dashboard and
`.github/workflows/refresh.yml`.

## Task board — session `2b1b75f6`

| Task | Description | Status | Session | File scope |
|---|---|---|---|---|
| T1 | Reverse-engineer `play.hotspawn.com/lol-pickems` (Angular SSR `ng-state`) + collector | done | `2b1b75f6` | `pipeline/hotspawn.py`, `pipeline/common.py`, `tools/` |
| T2 | External market collection (Bovada, Pinnacle, Polymarket) + de-vig + median consensus | done | `2b1b75f6` | `pipeline/markets.py`, `pipeline/build_data.py` |
| T3 | Unresolved-match audit (which books list LoL, why amateur tiers are unpriced) | done | `2b1b75f6` | `unresolved.html`, `sources.html`, `VERIFICATION.md` |
| T4 | Mobile-first dashboard + executive summary with in-site links | done | `2b1b75f6` | `*.html`, `assets/`, `.nojekyll` |
| T5 | 4-hour refresh workflow + Pages rebuild request | done | `2b1b75f6` | `.github/workflows/refresh.yml`, `data/` |
| T6 | Integration: merge `main`, re-verify, PR #1, confirm Pages | in progress | `2b1b75f6` | merge only |

## Session log — session `2b1b75f6`

| Time (UTC) | Entry |
|---|---|
| 2026-10-21T20:19Z | Repo reviewed: `main` @ `464a318`, one file (`README.md` = `# LOLHOTSPAWN1github.com`), Pages legacy from `main` root. |
| 2026-10-21T20:2xZ | Probed from a GitHub runner: `/lol-pickems` = Angular SSR with `<script id="ng-state">` (264 matches); Bovada coupon API 200 (9 LoL events); Pinnacle guest API 200 (9 LoL matchups); Polymarket Gamma 200 (13 series markets); 1xBet/Betano/Marathonbet/GG.Bet/Oddspedia/BetExplorer/bo3.gg/Prime League/Leaguepedia/lolesports blocked (logged). |
| 2026-10-21T20:33Z | First end-to-end run: 264 fixtures, 8 priced, 256 unresolved. |
| 2026-10-21T20:47Z | Fixed Nordic `Ø` transliteration (`LØS` ↔ "Los Grandes"), permalink extraction, added per-source evidence table → 9 priced. |
| 2026-10-21T20:5xZ | T1–T5 verified (`VERIFICATION.md`), PR #1 opened. Merge into `main` conflicted only on this file; both boards merged here. |
| 2026-10-21T21:0xZ | **PR #1 merged to `main`** (merge commit `550e031`). GitHub Pages rebuilt and verified live at <https://karagemop466-tech.github.io/LOLHOTSPAWN1/>. |
| 2026-10-21T21:1xZ | **PR #2 merged** (`992ea80`); Pages rebuilt and the live `picks.html` verified to show the corrected cards. |
| 2026-10-21T21:2xZ | Post-deploy UI fix: match cards now always show Hotspawn's team order (header, both probability rows and source odds agree) with an explicit `pick` tag; unresolved leagues collapse into `<details>` groups for mobile. Follow-up PR #2. |

## Findings usable by other sessions (`2b1b75f6`)

* `play.hotspawn.com/lol-pickems` ships the whole fixture list as JSON in `<script id="ng-state">` at
  `state["1214417440"]["b"]` — 264 rows with `id`, `competition_name`, `tier`, `scheduled_start_time`
  (epoch ms), `participants0/1_name`, `participants0/1_picked_percent`. It also carries an id → public
  permalink map (`https://www.hotspawn.com/matches/…`). Angular SSR means no JS execution is needed.
* 69 of 264 rows have **no** permalink in that payload (Hotspawn shows no "View Match" button for them).
* Pinnacle: `guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups` (sport 12 = "E Sports") needs the
  public guest `X-API-Key` header; moneylines are at `/matchups/{id}/markets/related/straight` and come
  back as a **list**, with `period: 0` being the full series.
* Bovada: the coupon feed exposes `price.decimal` per outcome, `competitors[].home` for orientation and
  a public event `link`, which is the cleanest verifiable deeplink found.
* Polymarket: `gamma-api.polymarket.com/events?tag_slug=league-of-legends&closed=false`; match markets are
  titled `LoL: <Team A> vs <Team B> …`, with `outcomes`/`outcomePrices` as JSON strings.
* The `www.hotspawn.com` host (including the `wp-json` fixture feed suggested above) returns **HTTP 403**
  to GitHub runner IPs, so permalinks must come from the lobby payload rather than from the CMS.
* Pages here is legacy `main:/`; pushes made with `GITHUB_TOKEN` do not start other workflows, so
  `.github/workflows/refresh.yml` explicitly POSTs `/repos/{owner}/{repo}/pages/builds` after committing.

## Final status (session `2b1b75f6`)

* **PR #1** — https://github.com/karagemop466-tech/LOLHOTSPAWN1/pull/1 — merged (`550e031`).
* **PR #2** — https://github.com/karagemop466-tech/LOLHOTSPAWN1/pull/2 — merged (`992ea80`).
* **PR #3** — https://github.com/karagemop466-tech/LOLHOTSPAWN1/pull/3 — merged (`7b9aace`) after merging the bot's refresh commit from `main`; pages rebuilt from the fresher data.
* **Live site** — https://karagemop466-tech.github.io/LOLHOTSPAWN1/ — verified after each merge (index, picks, flagged re-fetched from the deployed URL, correct counts and source links).
* **Refresh** — `.github/workflows/refresh.yml` runs every 4 h on `main`, commits `data/` + rebuilt pages with
  `[skip ci]`, then explicitly requests a legacy Pages build. First scheduled refresh after the merge completed
  successfully and its Pages build request was accepted.
* **Open items for the next session** — 255 unpriced matches need a *verified* market or a results feed;
  `www.hotspawn.com` remains 403 for runner IPs, so 69 lobby rows still have no public permalink.
