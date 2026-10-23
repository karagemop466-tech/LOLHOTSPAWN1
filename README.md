# Hotspawn LoL Pick Desk

**Live dashboard:** <https://karagemop466-tech.github.io/LOLHOTSPAWN1/>

A self-running pipeline that mirrors the complete League of Legends pick'em list from
`play.hotspawn.com/lol-pickems` and publishes an independent win probability for **every** match on it.
Probabilities come from live bookmaker and exchange lines where they exist, and from a results-based Elo
model where they do not. Hotspawn's own crowd-pick percentages are never used as an input.

The site rebuilds itself every six hours from GitHub Actions; nothing here needs a laptop to stay current.
Coverage is asserted against the exact Hotspawn API response the build fetched: match ids 1:1, all 27
tournaments, and 180 distinct teams.

## What it produces

| Page | Contents |
| --- | --- |
| `index.html` | Executive summary, coverage counts, **Next 48 hours** on one screen, and in-site links to every list |
| `picks.html` | All 241 matches, one compact row each, next kick-off first; working search, tournament filter, time window, method chips and sort, grouped by day |
| `featured.html` | Matches with a live bookmaker/exchange price, the raw odds, the de-vig arithmetic and the capture time |
| `originated.html` | Matches with no market price: our own Elo line, the kick-off rating inputs and the series counts behind it |
| `unresolved.html` | Matches we refuse to price, why, every limitation, and the **full line-source probe** with HTTP receipts |
| `competitions.html` | Coverage and line source per tournament; each tournament links to its filtered picks list |
| `teams.html` | Every team with its current rating, record, last match and join method |
| `flagged.html` | Irregularities and unverified items, published rather than hidden |
| `verification.html` | The 23-check publish gate, including the no-look-ahead audit |
| `sources.html` | Every source, what it provides, and whether the build runner could reach it |
| `methodology.html` | Sources, Elo specification, margin weighting, de-vig method, exclusions and the calibration curve |

## How it works

```
tools/collect.py        Hotspawn fixtures API · Pinnacle · Polymarket · Kalshi · Bovada · Leaguepedia · LoL Esports
        ↓
tools/model.py          chronological Elo, snapshot at each kick-off, margin-weighted; de-vigged multi-venue consensus
        ↓
tools/report.py         per-tournament and per-team summaries
        ↓
tools/flags.py          derived irregularities + curated notes (data/flags_manual.json)
        ↓
tools/site.py           11 static pages, mobile-first, no framework
        ↓
tools/verify.py         23 assertions; a failure aborts the commit instead of publishing bad data
```

`tools/probe_sources.py` is a separate, manually triggered probe (`.github/workflows/probe-sources.yml`)
that records what each candidate bookmaker, esportsbook and odds aggregator returns to a GitHub runner.
Its receipts are committed to `data/probe/sources_probe.json` and rendered on the Unresolved and Sources
pages. It never publishes a pick.

A single publishing workflow (`.github/workflows/refresh.yml`, cron `17 */6 * * *`) runs the chain on
`main`, commits `data/` and the generated pages with `[skip ci]`, and lets GitHub Pages redeploy.
Only `tools/` writes the published pages.

### Inputs and rules

- **Inventory** — `https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=lol&status=scheduled&tenantId=1`
  returns every LoL card, including the long tail of national and academy leagues. The list is mirrored
  exactly; a Hotspawn card that started hours ago but is still marked `scheduled` is kept and marked
  "started".
- **Market lines** — Pinnacle's public guest API, Polymarket's full-series CLOB, Kalshi's CFTC contract
  book and Bovada's pre-match coupon. Odds are converted to decimal and de-vigged proportionally, then
  weighted 0.36 / 0.24 / 0.18 / 0.12. A specialist esportsbook receipt is used only while it is less than
  24 hours old; an older receipt is rejected and the rejection is printed on the row.
- **Originated lines** — Elo fitted on Leaguepedia series results since 2024-09-01, margin-weighted
  (K = 48, margin weight 0.45), with inactivity decay. Every fixture is priced from the rating state **at
  its own kick-off**, using only results recorded before it, so an already-played card cannot see its own
  result. Teams with fewer than five rated series are labelled *provisional*.
- **Never used** — Hotspawn's `picked_percent`, its tiers, or its points as probability inputs.
- **Blank beats wrong** — a value that cannot be confirmed from a primary source is left blank and listed
  on `flagged.html`; nothing is inferred to fill a gap.

### Verification gate

`tools/verify.py` fails the build unless, at minimum: all 241 rows parse, every row carries a Hotspawn
match-card link plus a results or market source, both probabilities sum to 100 %, the published pick is the
higher-probability side, ids are unique, `picks.csv` mirrors the dataset, all 11 pages exist, every
internal link resolves, no `None`/empty value is rendered, every match appears on `picks.html`, the
executive summary links to every view, the mobile menu and picks filters are actually wired, every page
carries the mobile tab bar, and **no row uses more rated series than were played before its kick-off**.

Current result: **26/26 pass**, 0 look-ahead violations (`data/verification.json`).

### Mobile

- One row = time, tournament, both teams with a percentage, and the pick. No horizontal scrolling.
- A fixed bottom tab bar (Picks · Next up · Unresolved · Method · More) on screens under 760 px.
- The Menu button now opens the navigation; it previously had no JavaScript behind it.
- Rows are `<details>` elements: tap to expand the rating snapshot, caveats and source links.

## Manual review links

- `data/picks.csv` — one row per match: competition, teams, pick, probability, method, source URLs.
- `data/matches.json` — full record per match, including odds, kick-off ratings and flags.
- `data/matching_report.json` — every team join that was not an exact string match, with its evidence.
- `data/verification.json` — the machine-readable result of the gate.
- `data/probe/sources_probe.json` — line-source availability receipts.
- `data/build.log` — the last automated run, verbatim.
- `COORDINATION.md` — task board, session log and the integration decisions taken across sessions.

## Repository layout

- `tools/` — the only publisher of the root pages (collect → model → report → flags → site → verify)
- `data/` — generated dataset, CSV, flags, verification result and build log (`tools/` scope)
- `assets/` — `style.css`, `app.js` (menu, filters, sort, timezone conversion, no dependencies)
- `scripts/` — secondary Node pipeline (zero dependencies), publishes only `docs/` + `data/node/`
- `docs/` — the secondary dashboard, served at <https://karagemop466-tech.github.io/LOLHOTSPAWN1/docs/>
- `data/node/` — the Node pipeline's data scope (`picks.json`, `flags.json`, `model/`, `raw/`, `history/`)
- `archive/` — superseded sessions, kept as audit evidence; nothing there runs
- `evidence/snapshot/` — frozen raw responses backing the published numbers

## Running it locally

```bash
python3 tools/collect.py && python3 tools/model.py && python3 tools/report.py \
  && python3 tools/flags.py && python3 tools/site.py && python3 tools/verify.py
```

The collector needs outbound HTTPS to the sources listed on `sources.html`; the rest runs offline on the
files in `data/`. `python3 tools/probe_sources.py` is the optional runner-side source probe.

## Current state (2026-10-23)

| Metric | Value |
| --- | --- |
| Hotspawn LoL cards | 241 (27 tournaments) |
| Cards with a pick | 237 |
| Live bookmaker/exchange lines | 9 |
| Originated lines | 149 model + 79 provisional |
| Quarantined (mid-split DQ) | 4 |
| Out-of-sample backtest | 3,854 series, 65.5 % accuracy, 0.2144 Brier, 0.6178 log-loss |
| Toss-ups (identical kick-off ratings) | 3, marked on the row instead of pretending an edge |
| Publish gate | 26/26 checks pass |
