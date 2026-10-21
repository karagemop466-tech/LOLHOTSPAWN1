# Hotspawn LoL Pick Desk

Independent win probabilities and picks for **every League of Legends match listed in the Hotspawn
pick'em** (`https://play.hotspawn.com/lol-pickems`).

**Live site:** https://karagemop466-tech.github.io/LOLHOTSPAWN1/

## What it does

* Pulls the exact fixture list from Hotspawn's own pick'em fixtures API (264 LoL matches at the
  time of writing).
* Prices the featured matches from a real bookmaker feed (Pinnacle moneylines, de-vigged), with
  Polymarket as a prediction-market cross-check.
* Originates its own Elo line for every other match from Leaguepedia series results.
* Publishes a mobile-first dashboard where every row links to its source, and flags every
  limitation instead of hiding it.
* Refreshes automatically every 6 hours through GitHub Actions (`17 */6 * * *`).

## Pages

| Page | Purpose |
|---|---|
| `index.html` | Executive summary with in-site links to every picks view |
| `picks.html` | Every match, filterable and searchable |
| `featured.html` | Market-backed picks with odds and the de-vig maths |
| `originated.html` | Our own Elo lines with the inputs shown |
| `unresolved.html` | Unresolved matches, provisional lines and every limitation |
| `competitions.html` | Coverage by tournament |
| `teams.html` | Ratings and name-join evidence |
| `methodology.html` | Formulas, sources, backtest, exclusions |
| `verification.html` | The checks every build must pass |
| `sources.html` | Every source and its HTTP status on the last run |
| `flagged.html` | Irregularities and unverified items |

## Pipeline

```
tools/collect.py   # Hotspawn fixtures, Pinnacle, Leaguepedia, LoL Esports, Polymarket, source probe
tools/model.py     # team resolution, Elo, picks, data/matches.json + data/picks.csv
tools/report.py    # diagnostics
tools/flags.py     # data/flags.json (curated + derived)
tools/site.py      # static site at the repository root
tools/verify.py    # hard gate: fails the build instead of publishing bad data
```

Run locally with `python3 tools/collect.py && python3 tools/model.py && python3 tools/flags.py
&& python3 tools/site.py && python3 tools/verify.py`. No third-party Python packages are used.

## Data notes

* Hotspawn's community pick percentages are captured in the raw feed but **never** used by the
  model or by any published probability.
* Raw source dumps are not committed (`data/raw/`); every value used in the outputs is preserved in
  `data/matches.json`, and the exact endpoints are listed in `data/sources_status.json`.
