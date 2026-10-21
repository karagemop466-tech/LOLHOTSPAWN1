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
