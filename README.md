# Hotspawn LoL Pick Desk

**Live dashboard:** <https://karagemop466-tech.github.io/LOLHOTSPAWN1/>

A self-running pipeline that mirrors the complete League of Legends pick'em list from
`play.hotspawn.com/lol-pickems` and publishes a pick for **every** match on it: an independent win
probability wherever one can be defended, and an explicit settlement pick with no probability where it
cannot. Probabilities come from real bookmaker lines where they exist, and from a results-based Elo model
where they do not. Hotspawn's own crowd-pick percentages are never used as an input.

The site rebuilds itself every six hours from GitHub Actions; nothing here needs a laptop to stay current.

## What is on the site

| Page | Contents |
| --- | --- |
| `index.html` | Executive summary: headline counts, a jump grid to every list, and a dedicated unresolved/limitations section with its own table |
| `picks.html` | All 241 matches grouped by UTC day, next kick-off first, with search, tournament, pick-type and kick-off-window filters, deep links and a per-row source list |
| `featured.html` | Matches with a real bookmaker price, the raw odds, the de-vig arithmetic and our model's cross-check value |
| `originated.html` | Matches with no market price: our own line, the Elo inputs and the team records behind it |
| `unresolved.html` | Why each unpriced match is unpriced, the settlement side, and every limitation that applies to the rest of the list |
| `competitions.html` | Coverage, source quality and staleness per tournament |
| `teams.html` | Every team with its rating, record and competition |
| `methodology.html` | Formulae, the walk-forward backtest, the calibration curve and the parameter-stability sweep |
| `sources.html` | Every endpoint that was probed, its HTTP status and whether it can move a pick |
| `verification.html` | The machine-readable publish gate, check by check |
| `flagged.html` | Irregularities and unverified items, published rather than hidden |

## Pipeline

```
tools/collect.py   Hotspawn fixtures, Pinnacle, Polymarket, Kalshi, Bovada, Leaguepedia,
                   LoL Esports + 24 source probes
      ↓
tools/model.py     market consensus first, Elo line for everything else, settlement picks,
                   quote/prop rejection, market-vs-model cross-check
      ↓
tools/report.py    picks.csv, matching report
      ↓
tools/flags.py     derived irregularities + curated notes (data/flags_manual.json)
      ↓
tools/site.py      11 static pages, mobile-first, no framework
      ↓
tools/verify.py    38 assertions; a failure aborts the commit instead of publishing bad data
```

`tools/sweep.py` re-runs the Elo hyper-parameter grid and writes `data/backtest_sweep.json`; it does not
touch the published picks.

A single workflow (`.github/workflows/refresh.yml`, cron `17 */6 * * *`) runs that chain on `main`,
re-runs the page build after committing (so the freshness stamp is accurate), and refuses to push when the
gate fails. A second workflow (`.github/workflows/refresh-docs.yml`) rebuilds the pages from the committed
data without collecting again.

Only `tools/` writes the published pages.

## Sources and how a number is produced

- **Inventory** — `https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=lol&status=scheduled&tenantId=1`
  returns every LoL card, including the long tail of national and academy leagues.
- **Market lines** — Pinnacle's public guest API, Polymarket, Kalshi (CFTC) and Bovada, converted to
  decimal, de-vigged proportionally per venue and precision-weighted. Archived esportsbook receipts expire
  after 24 hours; symmetric 1.80/1.80 placeholders and any quote implying more than 97% on one side are
  rejected before de-vigging; Pinnacle's kill/map/handicap props are dropped before team matching. Our own
  Elo probability is printed beside every market price as a cross-check, and a gap of 20 pp or more is
  flagged rather than hidden.
- **Originated lines** — Elo fitted on 33,000+ Leaguepedia series: K = 48 for best-of-one, K = 40 with a
  margin-of-victory multiplier for multi-game series, inactivity decay, and a connected-opponent graph
  guard. The update sizes were selected on a validation window (2025-07-01..2026-07-01) disjoint from the
  published test window; `methodology.html` prints the whole sweep and states plainly that the grid's
  Brier spread is inside sampling noise.
- **Settlement picks** — a fixture whose participant was removed mid-split (`dqteams`) gets the
  administratively correct side (the remaining active opponent) and **no percentage**, because a
  competitive probability cannot be justified for a series that may be voided or awarded as a walkover.
- **Never used** — Hotspawn's `picked_percent`, its tiers, or its points as probability inputs.
- **Blank beats wrong** — a value that cannot be confirmed from a primary source is left blank and
  listed on `flagged.html`; nothing is inferred to fill a gap.

## Mobile

The published pages are mobile-first. A five-item bottom bar (Summary / All picks / Market / Unresolved /
Flags) is pinned to every page on phones, the header `Menu` button opens the full navigation, `picks.html`
has working search, tournament, pick-type and kick-off-window filters, and a sticky quick-filter strip
(Today / Next 7 days / Market-backed / Unresolved / Start time passed / Everything) that also works as
deep links (`?window=today`, `?window=next7`, `?method=market`, `?q=team`). `tests/dashboard.cjs`
exercises the menu, the tab bar, every filter, the reset button, the day groups and the deep links in
jsdom against the generated HTML.

## Verification gate

`tools/verify.py` fails the build unless, at minimum: the exact inventory ID multiset reconciles with the
raw Hotspawn snapshot, every row carries a Hotspawn match-card link, both probabilities sum to 100 %,
probabilities are finite and inside (0, 1), the published pick is the higher-probability side, **every
listed match has a pick**, settlement picks name a real participant and carry no probability, prop markets
never reach a published probability, every market row has a venue with a source URL, ids are unique,
`picks.csv` mirrors the dataset, all 11 pages exist, every internal link and anchor resolves, no
`None`/empty value is rendered, every match appears on `picks.html`, the executive summary carries the
coverage, unresolved and where-to-find-picks blocks and links to every view, the mobile nav has five
working destinations on every page and the menu/filter handlers are present, the pick filters exist in the
markup the script binds to, curated flags cite only currently listed fixtures, stale receipts are excluded
from the consensus, and each source's availability is recorded.

## Manual review links

- `data/picks.csv` — one row per match: competition, teams, pick, probability, method, source URLs.
- `data/matches.json` — full record per match, including odds, Elo inputs, the market/model cross-check and flags.
- `data/matching_report.json` — every team join that was not an exact string match, with its evidence.
- `data/backtest_sweep.json` — the Elo parameter grid, per-config validation and test scores, and which setting ships.
- `data/verification.json` — the machine-readable result of the gate (38 checks).
- `data/flags.json` — every irregularity published on `flagged.html`, curated + derived on each build.
- `data/sources_status.json` — HTTP status of every probed endpoint on the last build.
- `data/build.log` — the last automated run, verbatim.
- `COORDINATION.md` — task board, session log and the integration decisions taken across sessions.
- `audit/` — the independent line-by-line source audit (sessions `0d48f265` / `6d1ede2c`).

## Cross-check against Hotspawn's own dashboard

Where the two dashboards agree (Pinnacle-priced matches, same pick sides) is the strongest verification this
repo offers; where they differ, both presentations are one click apart and each row carries its source
links.

## Running it locally

```bash
python3 tools/model.py && python3 tools/report.py && \
python3 tools/flags.py && python3 tools/sweep.py && \
python3 tools/site.py && python3 tools/verify.py
```

`tools/collect.py` needs outbound network access to the providers above. Without it the pipeline runs
against the committed `data/raw/*` snapshots and says so in every staleness field.

Run `python3 -m unittest discover -s tests -v`, `NODE_PATH=<jsdom> node tests/dashboard.cjs` and
`python3 tools/verify.py`. The unit tests cover the integrity rules (NaN, out-of-range, wrong team,
settlement rows); the jsdom tests cover the mobile interactions; the gate covers the rest.

## Known limits, stated up front

If either team has no rated history and no collected market, probabilities and picks remain blank and the
row is published as unresolved with its reason. Recorded removals remain settlement-only pending the
league's decision. Historical manual findings are visibly marked as not reverified. Leaguepedia is
community-maintained. Model lines are estimates, not verified facts, and no page claims otherwise.
