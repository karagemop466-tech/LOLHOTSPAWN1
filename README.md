# Hotspawn LoL Pick Desk

**Live dashboard:** <https://karagemop466-tech.github.io/LOLHOTSPAWN1/>

A self-running pipeline that mirrors the complete League of Legends pick'em list from
`play.hotspawn.com/lol-pickems` and publishes a pick **with both win probabilities for every match on it**:
9 from real bookmaker / exchange lines, 148 from a results-based Elo model, 80 provisional lines and
4 settled from a **forfeit the league itself recorded** (match id, `FF` flag and recorded 0–2 score cited
on the card — a settled result, never an invented percentage). Nothing is unresolved on the current list;
anything that ever is gets its own section with the reason. Hotspawn's own crowd-pick percentages are
never used as an input.

The site rebuilds itself every six hours from GitHub Actions; nothing here needs a laptop to stay current.

## What it produces

| Page | Contents |
| --- | --- |
| `index.html` | Executive summary, headline counts, in-site links to every list and a dedicated *Unresolved picks & limitations* section |
| `table.html` | **All matches in one responsive table** — kick-off, match, both win probabilities, pick, method and source links (the page to bookmark on a phone) |
| `picks.html` | The same matches as cards, next kick-off first, with the reasoning behind each line |
| `featured.html` | Matches with a real bookmaker price, the raw odds and the de-vig arithmetic |
| `originated.html` | Matches with no market price: our own line, the Elo inputs and the team records behind it |
| `unresolved.html` | Forfeit-settled cards with their league receipt, any genuinely unresolved pick and why, and every limitation that applies to the rest of the list |
| `competitions.html` | Coverage, source quality and staleness per tournament |
| `teams.html` | Every team with its rating, record and competition |
| `flagged.html` | Irregularities and unverified items, published rather than hidden |
| `coverage.html` | Line-coverage ledger: every competition, how each match was priced, and the external-book receipts captured for corroboration |
| `verification.html` | The publish gate, its results, the manual source audit, and the evidence behind every non-exact team join |
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
tools/site.py      13 static pages, mobile-first, no framework
      ↓
tools/verify.py    25 assertions; a failure aborts the commit instead of publishing bad data
```

A single workflow (`.github/workflows/refresh.yml`, cron `17 */6 * * *`) runs that chain on `main`,
commits `data/` and the generated pages with `[skip ci]`, and lets GitHub Pages redeploy.
Only `tools/` writes the published pages; `tools/corroborate.py` writes `coverage.html` and
`data/corroboration.json`.

### Inputs and rules

- **Inventory** — `https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=lol&status=scheduled&tenantId=1`
  returns every LoL card, including the long tail of national and academy leagues.
- **Market lines** — Pinnacle's public guest API (series moneylines only — the parallel `(Kills)`
  derivative markets are rejected), Kalshi, Bovada and Polymarket. Odds are converted to decimal, then
  de-vigged proportionally and precision-weighted. A single prediction market with negligible traded
  volume is kept but labelled low confidence.
- **Originated lines** — Elo fitted on Leaguepedia series results, recency-weighted, with a
  connected-opponent graph guard; teams with too little recorded history are labelled *provisional*
  rather than silently given a confident number.
- **Forfeit-settled picks** — a fixture whose participant was removed mid-split (`dqteams`) is priced
  **only** when the same competition's Leaguepedia record shows the series with its forfeit flag
  (`FF=1` / `FF=2`) and a winner that agrees with it: the pick is that winner at a settled 100 %, and the
  basis carries the record id, score and source URL. A flag that disagrees with the recorded winner is
  rejected, and a card with no record stays unresolved rather than being filled in. Eight of Solid
  Gaming's eleven Komplettligaen series carry the flag — it is read per match, never assumed. A Hotspawn
  void would score the card for neither side, and that risk is printed on every forfeit card.
- **Never used** — Hotspawn's `picked_percent`, its tiers, or its points as probability inputs.
- **Blank beats wrong** — a value that cannot be confirmed from a primary source is left blank and
  listed on `flagged.html`; nothing is inferred to fill a gap.
- **Stale rows** — the API keeps returning `status:"scheduled"` for fixtures whose start time has
  passed. They stay on the list (so coverage matches Hotspawn exactly), are marked "start time passed"
  and are sorted after upcoming matches.

### Verification gate

`tools/verify.py` fails the build unless, at minimum: the dataset parses, every row carries a
Hotspawn match-card link, both probabilities sum to 100 %, the published pick is the higher-probability
side, ids are unique, no `(Kills)` derivative market is used as a match line, every market pick carries
an official quote URL, every official-forfeit resolution names a winner and a source URL without
inventing a probability, `picks.csv` mirrors the dataset, all 13 pages exist, every internal link
resolves, no `None`/empty value is rendered, every match appears on `picks.html` **and** in the table on
`table.html`, the executive summary links to every view, and each source's availability is recorded.

## Manual review links

- `data/picks.csv` — one row per match: competition, teams, pick, probability, method, source URLs.
- `data/matches.json` — full record per match, including odds, Elo inputs and flags.
- `data/matching_report.json` — every team join that was not an exact string match, with its evidence.
<<<<<<< HEAD
- `data/verification.json` — the machine-readable result of the gate (41 checks).
- `data/flags.json` — every irregularity published on `flagged.html`, curated + derived on each build.
=======
- `data/verification.json` — the machine-readable result of the gate.
- `data/audit.json` — the manual, line-by-line source audit rendered on `verification.html`.
- `data/retired_quotes.json` — archived quotes that were excluded as unverifiable, with the reason.
>>>>>>> origin/main
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

## Mobile use

The dashboard is mobile-first. A persistent bottom bar (Summary · All picks · Market · Unresolved ·
Flags) is fixed to the bottom of every page on phones, the header `Menu` button now actually opens the
full 11-page navigation, and `picks.html` has a working search box, tournament filter and pick-type
chips that filter instantly client-side with no page reload.

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
and picks remain blank. A mid-split removal is settled only from the league's recorded
forfeit (match id + `FF` flag + recorded score); without that record it stays unresolved.
Historical manual findings are visibly marked as not reverified.

Run `python3 -m unittest discover -s tests -v`, `NODE_PATH=<jsdom> node tests/dashboard.cjs`
and `python3 tools/verify.py`. The gate reconciles the exact inventory ID multiset, checks
finite probabilities via `tools/integrity.py`, checks the actual named favourite, checks each
match card's unique ID, asserts that the dataset is a 1:1 mirror of the Hotspawn feed the build
fetched (ids, and per-tournament counts), asserts that **no fixture uses a rating from after its
own kick-off**, enforces the settlement-pick contract (a settlement pick names a listed
participant and carries no probability), and requires every forfeit pick to cite a Leaguepedia record
whose flag agrees with its recorded winner.

The Elo model is margin-weighted (K=48, 2-0 counts more than 2-1) and every fixture is priced
from the rating state at its own kick-off, so an already-played card cannot see its own result.
Out-of-sample (3,854 series from 2026-07-01): **65.5% accuracy, 0.2144 Brier, 0.6178 log-loss**.
Three fixtures whose kick-off ratings are identical are labelled `toss-up` rather than pretending
an edge exists.
