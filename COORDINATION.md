# COORDINATION.md — Shared Task Board (`karagemop466-tech/LOLHOTSPAWN1`)

Last updated: `2026-10-21T20:20:00Z`

## Branch & Session Policy
- Active session branch: `arena/8336fb7e-lolhotspawn1` (session ID: `8336fb7e`, status: `active`).
- Per session environment binding, all commits, pushes, and pull requests from session `8336fb7e` occur on `arena/8336fb7e-lolhotspawn1` and merge cleanly into `main`.

## Shared Task Board

| Task ID | Task Description | Status | Owning Session | Branch | File Scope |
|---|---|---|---|---|---|
| `T1` | Reverse-engineer `play.hotspawn.com/lobby` & `/lol-pickems` SSR + backend REST API (`phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=lol&status=scheduled&tenantId=1` + permalinks) and build automated 4-hour GitHub Actions collector | `in progress` | `8336fb7e` | `arena/8336fb7e-lolhotspawn1` | `scripts/hotspawn.py`, `scripts/refresh.py`, `.github/workflows/` |
| `T2` | Tier-1 External Bookmaker & Prediction Market Line Collection (Pinnacle Arcadia API, Polymarket Gamma API, established LoL esportsbooks) — strict vig-removed win probabilities, zero Hotspawn crowd-pick input | `in progress` | `8336fb7e` | `arena/8336fb7e-lolhotspawn1` | `scripts/markets.py`, `data/market_quotes.json` |
| `T3` | Tier-2/3 Official LoL League Standings, Match History & Line Origination Research for non-market low-tier LoL leagues (Prime League 2nd/3rd Div, Komplettligaen, Icelandic Esports League, Benelux Ascend, Arabian League/ARC, Tunisian Super League, 4 Nations, RIVALS League, LigaGG CELOL, Superstrike, ERL promotions/playoffs) + explicit Unresolved & Limitations audit | `in progress` | `8336fb7e` | `arena/8336fb7e-lolhotspawn1` | `scripts/standings.py`, `scripts/originate.py`, `data/team_records.json`, `data/aliases.json` |
| `T4` | Line-by-line Verification, Irregularities & Flagged-for-Review Audit (`data/matches.json`, `data/picks.csv`, `data/flagged.json`, `scripts/validate.py`, `tests/`) | `in progress` | `8336fb7e` | `arena/8336fb7e-lolhotspawn1` | `data/`, `scripts/validate.py`, `tests/`, `VERIFICATION.md` |
| `T5` | Mobile-First GitHub Pages Dashboard (`index.html` with top Executive Summary & direct links, `picks.html`, `featured.html`, `originated.html`, `unresolved.html`, `tournaments.html`, `teams.html`, `methodology.html`, `flagged.html`), PR, Merge & Live GitHub Pages Verification | `in progress` | `8336fb7e` | `arena/8336fb7e-lolhotspawn1` | `index.html`, `*.html`, `assets/`, `.nojekyll`, `README.md` |

## Session Log
- `2026-10-21T20:20:00Z` (`8336fb7e`): Audited repository `karagemop466-tech/LOLHOTSPAWN1` (`main` at `464a318`, single `README.md`). Confirmed no other branches or PRs open on `LOLHOTSPAWN1`. Claimed `T1`–`T5` on `arena/8336fb7e-lolhotspawn1` and pushed claim immediately.
