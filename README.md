# Hotspawn LoL Pick Desk

**Live dashboard:** <https://karagemop466-tech.github.io/LOLHOTSPAWN1/>

A self-running pipeline that mirrors the complete League of Legends pick'em list from
`play.hotspawn.com/lol-pickems` and publishes a pick for **every** match on it: an independent win
probability wherever one can be defended, and an explicit settlement pick with no probability where it
cannot. Probabilities come from real bookmaker lines where they exist, and from a results-based Elo model
where they do not. Hotspawn's own crowd-pick percentages are never used as an input.

GitHub Actions schedules a refresh every six hours, but a schedule does not guarantee a successful run. Check the visible inventory timestamp and stale warning before treating any pick as current.

## What it produces

| Page | Contents |
| --- | --- |
| `index.html` | Executive summary, headline counts, in-site links to every list and a dedicated *Unresolved picks & limitations* section |
| `table.html` | **All matches in one responsive table** — kick-off, match, both win probabilities, pick, method and source links (the page to bookmark on a phone) |
| `results.html` | **Track record** — every started card graded hit/miss against the official series record, accuracy by method, forfeit settlements, and the started-but-ungraded list |
| `picks.html` | The same matches as cards, next kick-off first, with the reasoning behind each line |
| `featured.html` | Matches with a real bookmaker price, the raw odds and the de-vig arithmetic |
| `originated.html` | Matches with no market price: our own line, the Elo inputs and the team records behind it |
| `unresolved.html` | Matches we refuse to price, the official forfeit settlement where the league has ruled one, and every limitation that applies to the rest of the list |
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
tools/site.py      14 static pages, mobile-first, no framework
      ↓
tools/verify.py    42 publish-integrity gates (the count grows as checks are added); a failure
                   aborts the commit instead of publishing bad data
```

A single canonical workflow (`.github/workflows/refresh.yml`, cron `17 */6 * * *`) attempts that
chain on `main`, commits `data/` and the generated pages with `[skip ci]`, and lets GitHub Pages
redeploy. A cron schedule is an attempt, not a guarantee: every page shows the inventory timestamp,
warns after 12 hours, and marks the snapshot stale after 30 hours. Check the timestamp and linked
sources before relying on a pick. Only `tools/` writes the canonical published pages;
`tools/corroborate.py` writes `coverage.html` and `data/corroboration.json`.

### Inputs and rules

- **Inventory** — `https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=lol&status=scheduled&tenantId=1`
  returns the scheduled LoL cards at collection time, including the long tail of national and academy leagues. The API can retain past-start cards as `scheduled`; these remain visible and are labeled stale rather than silently removed.
- **Market lines** — Pinnacle's public guest API (series moneylines only — the parallel `(Kills)`
  derivative markets are rejected), Kalshi, Bovada, Unibet via its public Kambi feed, and Polymarket.
  Odds are converted to decimal, then de-vigged proportionally and precision-weighted. A single
  prediction market with negligible traded volume is kept but labelled low confidence. Actual venue
  availability varies by match; see `coverage.html` and `sources.html` rather than assuming every book
  prices every competition.
- **Originated lines** — Elo fitted on Leaguepedia series results, recency-weighted, with a
  connected-opponent graph guard; teams with too little recorded history are labelled *provisional*
  rather than silently given a confident number.
- **Settlement picks** — a fixture whose participant was removed mid-split (`dqteams`) gets the
  administratively correct side (the remaining active opponent) and **no percentage**, because a
  competitive probability cannot be justified for a series that may be voided or awarded as a walkover.
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

## Track record (graded picks)

Every card whose start time has passed is graded against the official series record once one exists:
the pick counts as a **hit** if the recorded winner is the published side, a **miss** otherwise. A pick
is graded only when the record matches the fixture's team pair and kick-off (within 12 hours) and the
recorded winner is consistent with the recorded score; anything less stays ungraded instead of being
guessed. Forfeit settlements are reported as *settled* and are never counted as forecast wins.
`data/matches.json` carries the per-row `result` / `grade` and a `track_record` summary; `results.html`
renders it. `tests/test_grading.py` enforces the rules (no grade without a result, no hit that
contradicts the winner, no settled pick with a probability, track record equal to the rows).

## Reliability of the six-hourly refresh

`refresh-picks` failed on three consecutive scheduled runs on 2026-10-24 and left the published data a
day stale. The cause was a self-sustaining gate, not the sources: `tools/corroborate.py` counted every
archived receipt whose fixture Hotspawn had delisted as "rejected", and once the 17 archived captures
aged past the 24 h window the `external receipts validated against the dataset` gate failed. Because
the failing build was the only thing that could refresh the receipts, the failure could never clear.

- Receipts are now bucketed **usable / expired / historic / rejected**. Only malformed, wrong-team and
  diverging receipts fail the gate; every capture is accounted for exactly once (42nd gate).
- `refresh.yml` captures each stage separately, uploads the log as an artifact, and commits
  `data/build_failure.log` when the gate fails, so the next failure is diagnosable from the repository.
- `tests/test_corroborate.py` locks the classification in.

## External line coverage (measured, not assumed)

`data/source_probes.json` is a runner-executed probe of every candidate venue (44 on 2026-10-24T16:22Z),
kept as evidence. The last run answered **HTTP 200** for Pinnacle, Kalshi, Bovada, Polymarket, Unibet
(Kambi `ubse`), Pinnacle's LoL league list, Leaguepedia and Odds-API.io's sports index; **blocked**:
GG.BET 403, Thunderpick 403, Stake 403, Rivalry API 403/530, Tips.GG 403, BetMGM 403, Betfair 403,
Bet365 403, 1xBet 203, Betway 404, BetExplorer 404, Oddspedia 410, OddsPapi 401. Books that answer in
HTML without a public price feed are recorded as such and are never parsed into a number.

Two conclusions are published on the site rather than assumed: Kambi-powered operators share one LoL
offering (the `ubse` and `paf` payloads were byte-identical, so `paf` is used only as a fallback and can
never double-count), and every reachable venue quotes the same tier-1 slice of the calendar. Below that
ceiling there is no external line to quote, which is exactly why the model originates one.

## Manual review links

- `data/picks.csv` — one row per match: competition, teams, pick, probability, method, source URLs.
- `data/matches.json` — full record per match, including odds, Elo inputs and flags.
- `data/matching_report.json` — every team join that was not an exact string match, with its evidence.
- `data/verification.json` — machine-readable publish-gate results (the current check count is recorded in the file).
- `data/flags.json` — irregularities published on `flagged.html`, curated and derived on each build.
- `data/audit.json` — the manual source audit rendered on `verification.html`.
- `data/retired_quotes.json` — archived quotes excluded as unverifiable, with the reason.
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
  listing them; matches with no market and insufficient connected model history are left **unresolved**
  rather than assigned an unsupported probability; flags start-time discrepancies between Hotspawn and
  Pinnacle/Polymarket per match. See `docs/unresolved.html` for the live count and per-match reasons.
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

### Integrity and freshness review (2026-10-24)

The canonical mobile controls are wired to the current HTML (search, tournament,
method chips, menu); a permanent mobile **All picks** link is available on every page.
Inventory collection time is separate from model build time. The browser warns after
12 hours and marks snapshots hard-stale after 30 hours. Six-hour Actions scheduling
is best effort, not a live-odds SLA.

At this review, the committed canonical inventory was collected at 2026-10-23T17:11:12Z,
and the four latest scheduled canonical refresh runs had failed. Pages was built, but
that is not proof the canonical data refreshed. See `COORDINATION.md` for the official
run links and the unresolved failure cause; no cause is guessed.

Archived aggregator receipts are **not** current quotes and are excluded from pricing.
Leaguepedia is a community source; its results are not labelled official league
verification. Model probabilities are estimates, never confirmed facts. If either team
has no matched rated history and no collected market, probabilities and picks remain
blank. Recorded removals remain quarantined pending settlement. Historical manual
findings are visibly marked as not reverified.

Run `python3 -m unittest discover -s tests -v`, `NODE_PATH=<jsdom> node tests/dashboard.cjs`
and `python3 tools/verify.py`. The gate reconciles the exact inventory ID multiset, checks
finite probabilities via `tools/integrity.py`, checks the actual named favourite, checks each
match card's unique ID, asserts that the dataset is a 1:1 mirror of the Hotspawn feed the build
fetched (ids, and per-tournament counts), asserts that **no fixture uses a rating from after its
own kick-off**, and enforces the settlement-pick contract (a settlement pick names a listed
participant and carries no probability).

The Elo model is margin-weighted (K=48, 2-0 counts more than 2-1) and every fixture is priced
from the rating state at its own kick-off, so an already-played card cannot see its own result.
Out-of-sample (3,854 series from 2026-07-01): **65.5% accuracy, 0.2144 Brier, 0.6178 log-loss**.
Three fixtures whose kick-off ratings are identical are labelled `toss-up` rather than pretending
an edge exists.
