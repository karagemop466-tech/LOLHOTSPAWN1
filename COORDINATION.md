# COORDINATION.md — Shared Task Board

Repo: `karagemop466-tech/LOLHOTSPAWN1` — LoL Hotspawn pick'em analytics (picks + probabilities for every
League of Legends match listed on https://play.hotspawn.com/lobby / https://play.hotspawn.com/lol-pickems).

Protocol: claim a task by writing your session ID + file scope below, commit & push the claim immediately.
Never start a task claimed by another session. Keep scopes non-overlapping. Small frequent commits.
`git pull --rebase` before every push. `needs review` = published on the Flagged for Review page, non-blocking.

## Sessions

| Session ID | Branch | Active since |
|---|---|---|
| arena-f6e73320 | `arena/f6e73320-lolhotspawn1` (fixed by Arena platform; the `session-<id>/<task>` convention is not usable here) | 2026-10-21 |

## Task board

| # | Task | Status | Owner | Files touched |
|---|------|--------|-------|---------------|
| T1 | Reverse-engineer Hotspawn data sources (lobby, fixtures API) + odds sources (Pinnacle, Polymarket) | done | arena-f6e73320 | `docs/methodology.html`, `README.md` |
| T2 | Collector scripts: hotspawn fixtures, Pinnacle guest API, Polymarket gamma API | in progress | arena-f6e73320 | `scripts/collect.mjs`, `data/raw/*` |
| T3 | Analysis engine: devig, team-name matching, own Elo model, pick generation, flags | in progress | arena-f6e73320 | `scripts/analyze.mjs`, `data/picks.json`, `data/model/*` |
| T4 | Site build: mobile-first dashboard, executive summary, picks, unresolved, flagged, methodology, results pages | in progress | arena-f6e73320 | `scripts/build_site.mjs`, `docs/*` |
| T5 | Automation: GitHub Actions refresh every 6h (within the 4–8h requirement), commit + Pages deploy | in progress | arena-f6e73320 | `.github/workflows/refresh.yml`, `scripts/run_all.mjs` |
| T6 | Verification pass: line-by-line checks, source links per row, flag irregularities | unclaimed | — | `data/flags.json`, `docs/flagged.html` |
| T7 | Final integration: build check, no broken links, enable Pages, PR → main, merge, record PR link | unclaimed | — | everything above (integration only) |

## Log

- 2026-10-21 ~20:20 UTC — arena-f6e73320: created board, claimed T1 (in progress). Recon findings (all verified live this session):
  - Hotspawn lobby: `https://play.hotspawn.com/lol-pickems` (SSR HTML; "This week" counter, tier/tournament filters, match cards with `View Match` permalinks to `www.hotspawn.com/matches/...`).
  - Hotspawn fixtures API (embedded public API, no auth): `https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures` — supports `?sport_alias=lol`, `?status=scheduled`. Fields: id, competition_name, tier, stage, scheduled_start_time, lock_time, offered_points, status, participants0/1 (id, name, picked_percent, score). Full history of ended LoL fixtures is also served (usable as *results* input for our own Elo model — results are facts, not Hotspawn opinions; Hotspawn crowd `% picked` is explicitly NOT used for probabilities per requirements).
  - WordPress API `https://www.hotspawn.com/wp-json/` exposes namespaces `fixtures/v1`, `pickem/v1` (`/pickem/v1/fixtures` requires `ids` param — bulk fetch by id), `tournaments/v1`, `participants/v1`.
  - Pinnacle guest API (no auth on bulk endpoints): `https://guest.api.arcadia.pinnacle.com/0.1/sports/12/leagues` → LoL leagues live now: `League of Legends - World Championship` (id 9587), `League of Legends - EMEA Masters` (id 225201). Odds: `/0.1/leagues/{id}/markets/straight` (American-odds moneylines, period 0 = series) + `/0.1/leagues/{id}/matchups` (teams, startTime). `?withNested=true` requires auth (401) — avoid.
  - Polymarket gamma API: `https://gamma-api.polymarket.com/events?closed=false&tag_slug=league-of-legends` — live LoL events incl. Worlds 2026 markets (`outcomePrices`, `bestBid/bestAsk`, volume).
  - Sandbox bash cannot reach these hosts (egress restricted to github/npm/pypi) → all live fetching runs in GitHub Actions (full egress); local iteration uses committed raw snapshots.
- 2026-10-21 — arena-f6e73320: claiming T2–T7 as well (single active session; scopes above). Will update statuses as work lands.
- 2026-10-21 ~21:00 UTC — arena-f6e73320: T1 done (sources verified live, see registry). T2–T5 code written and smoke-tested locally against synthetic fixtures mimicking the verified API shapes (exact/fuzzy name matching, devig, Elo model, unresolved + flag paths, static site render, internal-link check — all exercised; synthetic data deleted before push). Pushing now; the `push` trigger of `.github/workflows/refresh.yml` performs the first LIVE run on this branch (collect → analyze → build → commit real data + docs). After merge to main the schedule (`5 */6 * * *` UTC = every 6h) keeps the site fresh.

## Sources registry (append per task with links used)

| Source | URL | Used for | Verified |
|---|---|---|---|
| Hotspawn LoL pick'em lobby | https://play.hotspawn.com/lol-pickems | match inventory (SSR cross-check) | 2026-10-21 (live fetch) |
| Hotspawn fixtures API | https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=lol | match inventory + results history | 2026-10-21 (live fetch) |
| Hotspawn match permalinks | https://www.hotspawn.com/matches/{slug} | per-row source link | 2026-10-21 (live fetch) |
| Pinnacle guest API — leagues | https://guest.api.arcadia.pinnacle.com/0.1/sports/12/leagues | LoL league discovery | 2026-10-21 (live fetch) |
| Pinnacle guest API — matchups | https://guest.api.arcadia.pinnacle.com/0.1/leagues/9587/matchups | teams/start times (Worlds) | 2026-10-21 (live fetch) |
| Pinnacle guest API — straight markets | https://guest.api.arcadia.pinnacle.com/0.1/leagues/9587/markets/straight | moneyline odds (devig → probabilities) | 2026-10-21 (live fetch) |
| Polymarket gamma API | https://gamma-api.polymarket.com/events?closed=false&tag_slug=league-of-legends | LoL market prices (secondary line) | 2026-10-21 (live fetch) |
| Polymarket event pages | https://polymarket.com/esports/league-of-legends/... | per-row source link for Polymarket lines | 2026-10-21 (search result) |
| bo5.gg LoL odds board (Polymarket+Thunderpick derived) | https://bo5.gg/lol/betting/odds/ | corroboration only | 2026-10-21 (search result) |
| egamersworld LoL odds comparison | https://egamersworld.com/lol/bets | corroboration only | 2026-10-21 (search result) |
