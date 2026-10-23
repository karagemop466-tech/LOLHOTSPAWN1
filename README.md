# Hotspawn LoL Pick Desk

**Live dashboard:** <https://karagemop466-tech.github.io/LOLHOTSPAWN1/>

A self-running pipeline that mirrors the complete League of Legends pick'em list from
`play.hotspawn.com/lol-pickems` and publishes an independent win probability for **every** match on it.
Probabilities come from real bookmaker lines where they exist, and from a results-based Elo model
where they do not. Hotspawn's own crowd-pick percentages are never used as an input.

The site rebuilds itself every six hours from GitHub Actions; nothing here needs a laptop to stay current.

## What it produces

| Page | Contents |
| --- | --- |
| `index.html` | Executive summary, a jump grid to every picks view, and a dedicated unresolved/limitations section |
| `picks.html` | All 241 matches grouped by UTC day, one card each, next kick-off first, with search, method/tournament/window filters and a per-row source list |
| `featured.html` | Matches with a real bookmaker price, the raw odds and the de-vig arithmetic |
| `originated.html` | Matches with no market price: our own line, the Elo inputs and the team records behind it |
| `unresolved.html` | Matches we refuse to price, why, the walkover guidance, and every limitation that applies to the rest of the list |
| `competitions.html` | Coverage, source quality and staleness per tournament |
| `teams.html` | Every team with its rating, record and competition |
| `flagged.html` | Irregularities and unverified items, published rather than hidden |
| `verification.html` | The publish gate, its results, and the evidence behind every non-exact team join |
| `sources.html` | Every source, what it provides, and whether the build runner could reach it |
| `methodology.html` | Sources, Elo specification, de-vig method, exclusions |

## How it works

```
tools/collect.py   Hotspawn fixtures API · Pinnacle guest API · Polymarket · Leaguepedia Cargo · LoL Esports
      ↓
tools/model.py     Elo over Leaguepedia series results, de-vig of bookmaker moneylines
      ↓
tools/report.py    per-tournament and per-team summaries
      ↓
tools/flags.py     derived irregularities + curated notes (data/flags_manual.json)
      ↓
tools/site.py      11 static pages, mobile-first, no framework
      ↓
tools/verify.py    14 assertions; a failure aborts the commit instead of publishing bad data
```

A single workflow (`.github/workflows/refresh.yml`, cron `17 */6 * * *`) runs that chain on `main`,
commits `data/` and the generated pages with `[skip ci]`, and lets GitHub Pages redeploy.
Only `tools/` writes the published pages.

### Inputs and rules

- **Inventory** — `https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=lol&status=scheduled&tenantId=1`
  returns every LoL card, including the long tail of national and academy leagues.
- **Market lines** — Pinnacle's public guest API (LoL moneylines), with Polymarket used as an
  independent cross-check. Bookmaker odds are converted to decimal, then de-vigged proportionally.
- **Originated lines** — Elo fitted on Leaguepedia series results: K = 48 for best-of-one, K = 40 with a
  margin-of-victory multiplier for multi-game series, inactivity decay, and a connected-opponent graph
  guard; teams with too little recorded history are labelled *provisional* rather than silently given a
  confident number. The update sizes were selected on a validation window (2025-07-01..2026-07-01) that is
  disjoint from the published test window.
- **Never used** — Hotspawn's `picked_percent`, its tiers, or its points as probability inputs.
- **Blank beats wrong** — a value that cannot be confirmed from a primary source is left blank and
  listed on `flagged.html`; nothing is inferred to fill a gap.
- **Stale rows** — the API keeps returning `status:"scheduled"` for fixtures whose start time has
  passed. They stay on the list (so coverage matches Hotspawn exactly), are marked "start time passed"
  and are sorted after upcoming matches.

### Mobile

The published pages are mobile-first: a four-item bottom tab bar (Summary / All picks / Unresolved /
Sources) on every page, a collapsible top menu, a jump grid on the summary page, day-grouped pick cards
with `content-visibility` so long lists scroll cheaply, and `picks.html?window=today` /
`?window=next7` / `?method=market` deep links that drive the same filters as the on-page controls.
`tests/dashboard.cjs` exercises the menu, tab bar, search, empty state, all three filters, the reset
button and the deep links in jsdom.

### Verification gate

`tools/verify.py` fails the build unless, at minimum: all 241 rows parse, every row carries a
Hotspawn match-card link, both probabilities sum to 100 %, the published pick is the higher-probability
side, ids are unique, `picks.csv` mirrors the dataset, all 11 pages exist, every internal link
resolves, no `None`/empty value is rendered, every match appears on `picks.html`, the executive
summary links to every view, and each source's availability is recorded.

## Manual review links

- `data/picks.csv` — one row per match: competition, teams, pick, probability, method, source URLs.
- `data/matches.json` — full record per match, including odds, Elo inputs and flags.
- `data/matching_report.json` — every team join that was not an exact string match, with its evidence.
- `data/verification.json` — the machine-readable result of the gate.
- `data/build.log` — the last automated run, verbatim.
- `COORDINATION.md` — task board, session log and the integration decisions taken across sessions.

## Repository layout

- `tools/` — the only publisher of the root pages (collect → model → report → flags → site → verify)
- `data/` — generated dataset, CSV, flags, verification result and build log (`tools/` scope)
- `assets/` — `style.css`, `app.js` (tabs, timezone conversion, no dependencies)
- `scripts/` — secondary Node pipeline (zero dependencies), publishes only `docs/` + `data/node/`
- `docs/` — the secondary dashboard, served at <https://karagemop466-tech.github.io/LOLHOTSPAWN1/docs/>
- `data/node/` — the Node pipeline's data scope (`picks.json`, `flags.json`, `model/`, `raw/`, `history/`)
- `archive/` — superseded sessions, kept as audit evidence; nothing there runs
- `evidence/snapshot/` — frozen raw responses backing the published numbers

## Secondary dashboard (`docs/`, session `f6e73320`)

A second, fully independent implementation of the same brief runs alongside the canonical site. It is
an **audit companion, not a competitor**: it never writes root pages, and it refreshes on its own
workflow (`.github/workflows/refresh-docs.yml`, cron `5 */6 * * *`) inside the shared `refresh-picks`
concurrency group, so the two bots serialize and cannot race.

- **Pipeline**: `scripts/collect.mjs` → `scripts/analyze.mjs` → `scripts/build_site.mjs` (Node ≥ 18, no
  dependencies). Data scope: `data/node/**`; published pages: `docs/**` (7 pages, mobile-first).
- **Lines**: Pinnacle guest API moneylines (devigged; with retry + persistent listing cache + odds-line
  reconstruction against the intermittent `/matchups` 401), Polymarket series markets (mid-price when
  spread ≤ 6¢, else renormalized last prices; game-level submarkets filtered out), then an own Elo model
  over the Hotspawn results archive (1,102 ended fixtures, 462 teams) for everything else.
- **Differences by design**: quarantines stale fixtures (>24 h past start, never settled) instead of
  listing them; 12 matches are left **unresolved** (no market + no history) rather than priced
  provisionally; flags start-time discrepancies between Hotspawn and Pinnacle/Polymarket per match.
- **Entry point**: `docs/index.html` — executive summary, all-picks list, unresolved, flagged,
  methodology, results, models.

Where the two dashboards agree (9 Pinnacle-priced matches, same pick sides, same irregularity classes
found independently) is the strongest verification this repo offers; where they differ, both
presentations are one click apart and each row carries its source links.

## Running it locally

```bash
python3 tools/collect.py && python3 tools/model.py && python3 tools/report.py \
  && python3 tools/flags.py && python3 tools/site.py && python3 tools/verify.py
```

The collector needs outbound HTTPS to the sources listed on `sources.html`; the rest runs offline on
the files in `data/`.

### 2026-10-23 integrity audit

The canonical mobile controls are wired to the current HTML (search, tournament,
method chips, menu); a permanent mobile **All picks** link is available on every page.
Inventory collection time is separate from model build time, with a browser warning
after eight hours. Six-hour Actions scheduling is best effort, not a live-odds SLA.

Archived 2026-10-21 aggregator receipts are **not** current quotes and are excluded
from pricing. Leaguepedia is a community source; its results are not labelled official
league verification. Model probabilities are estimates, never confirmed facts.
If either team has no matched rated history and no collected market, probabilities
and picks remain blank. Recorded removals remain quarantined pending settlement.
Historical manual findings are visibly marked as not reverified.

Run `python3 -m unittest discover -s tests -v` and `python3 tools/verify.py`.
The gate reconciles the exact inventory ID multiset, checks finite probabilities,
checks the actual named favourite, and checks each match card's unique ID.
