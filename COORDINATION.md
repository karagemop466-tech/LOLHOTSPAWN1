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

## Log

- 2026-10-21 (UTC) · session `9d43092a` · Created this board. Repo contained only `README.md`; no prior
  site, no prior data files, no other session claims. All eight tasks above were unclaimed, so this session
  took them end-to-end and will publish through a PR to `main`.
