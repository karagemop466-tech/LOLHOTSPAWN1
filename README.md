# LOLHOTSPAWN1 — Hotspawn League of Legends Pick'ems: lines, probabilities and coverage

Live site: **https://karagemop466-tech.github.io/LOLHOTSPAWN1/** (GitHub Pages, published from `main`)

## What this repo does

1. Collects **every League of Legends match Hotspawn currently offers a pick'em for** — the LoL tab of
   the pick'em lobby (`https://play.hotspawn.com/lol-pickems`), not the default Counter-Strike lobby.
2. Verifies each match against **Hotspawn's own public fixture feed**
   (`https://www.hotspawn.com/wp-json/wp/v2/fixtures`) and against the **league page** that prints the
   kickoff as `HH:MM UTC`.
3. Attaches **external betting lines** — Polymarket and esports odds-comparison pages — and converts
   them to no-vig win probabilities for both teams.
4. **Originates its own line** (series-level Elo over verified finished scorelines) for every match no
   book covers, i.e. the low-tier / regional / academy leagues that never appear on betting sites.
5. Publishes anything it cannot resolve as an **unresolved pick**, with the concrete reason, on its own
   page and inside the executive summary.
6. Rebuilds the mobile-first dashboard and redeploys it **every 6 hours with no manual input**
   (`.github/workflows/refresh.yml`).

Hotspawn's own "X% picked" crowd share is displayed for comparison and is **never** used as a
probability input — see `scripts/verify.py`, which fails a run if a probability is ever sourced from
Hotspawn.

## Repo layout

| Path | Purpose |
|---|---|
| `scripts/hotspawn.py` | lobby + fixture-feed + league-page collectors and parsers |
| `scripts/lines.py` | Polymarket + odds-comparison parsers, esports-book probes, line joining |
| `scripts/model.py` | self-originated series-Elo model (formula, shrinkage, confidence bands) |
| `scripts/pipeline.py` | orchestrates collect → lines → model → resolve → `data/*.json` + CSV |
| `scripts/build_site.py` | renders `site/` (exec summary, all picks, league/tier subpages, unresolved, flagged, methodology, sources, data) |
| `scripts/verify.py` | publish gates: schema, source links, no fabricated values, no broken links |
| `tests/` | offline regression tests (parser shapes, odds maths, joining rules, gates) |
| `data/` | machine-readable snapshot (`picks.json`, `picks.csv`, `unresolved.json`, `flags.json`, `ratings.json`, `sources.json`, `summary.json`) |
| `site/` | the published static site |
| `COORDINATION.md` | shared task board for concurrent agent sessions |

## Run it

```bash
pip install -r requirements.txt
python -m unittest discover -s tests        # offline checks
python -m scripts.pipeline --out data       # needs internet access (GitHub runner has it)
python -m scripts.build_site --data data --site site
python -m scripts.verify --data data --site site
```

## Honesty rules enforced by code

* Every row links to at least one official source; a value that could not be confirmed is left blank
  and written to `data/flags.json` (published on *Flagged for review*).
* A price is attached to a match only when **both** team labels match; if a source lists several
  fixtures for the same pair, nothing is attached and the row is flagged.
* A market probability is never replaced by a guess: matches with no price and no verifiable results
  land in `data/unresolved.json` with the reason.
* If a refresh cannot scrape or a gate fails, the previous snapshot stays published.

Unofficial research project. No wagers are placed here and nothing here is betting advice.
