# LOLHOTSPAWN1 — LoL Hotspawn Pick'em Analytics

Independent win probabilities and picks for **every League of Legends match listed on the
Hotspawn pick'em lobby** (https://play.hotspawn.com/lol-pickems), refreshed every 6 hours.

**Live site (GitHub Pages):** https://karagemop466-tech.github.io/LOLHOTSPAWN1/

## What this project does

1. **Collects** the full LoL match inventory from Hotspawn's own embedded public fixtures API
   (`phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=lol`), cross-checked
   against the server-rendered lobby page.
2. **Prices every match** with external betting lines — Hotspawn crowd "% picked" is never used:
   - **Pinnacle** guest odds API (sharp moneylines, devigged to probabilities)
   - **Polymarket** gamma API (prediction-market prices)
   - **Own Elo-style model** built from the full archive of real results (originated line for
     matches no book prices)
3. **Publishes** a mobile-first static dashboard: executive summary, full pick list, unresolved
   picks with limitations, flagged-for-review irregularities, results/accuracy, per-tournament
   views, and methodology with source links for every row.
4. **Automates** the whole pipeline via GitHub Actions every 6 hours (schedule `5 */6 * * *` UTC),
   committing fresh data + rebuilt pages.

## Pages

| Page | Purpose |
|---|---|
| `docs/index.html` | Executive summary + links to every picks list |
| `docs/picks.html` | All open matches: probability per team, the pick, line sources (filterable) |
| `docs/unresolved.html` | Matches with no possible pick + the specific limitation for each |
| `docs/flagged.html` | "Flagged for Review" — irregularities with source links (non-blocking) |
| `docs/results.html` | Settled matches this week + tracked-pick accuracy |
| `docs/tournaments.html` | Picks organized by tournament/category |
| `docs/methodology.html` | Sources, formulas, precedence, verification policy |

## Pipeline

```
scripts/collect.mjs   → data/raw/*.json      (Hotspawn API + lobby, Pinnacle, Polymarket)
scripts/analyze.mjs   → data/picks.json      (Elo model, market matching, picks, flags, ledger)
scripts/build_site.mjs→ docs/*.html          (static mobile-first site + internal link check)
scripts/run_all.mjs   → orchestration        (used by .github/workflows/refresh.yml)
```

Node.js ≥ 18, zero npm dependencies.

## Verification rules

- Every match row links to its official Hotspawn match page; every market line links to the exact
  Pinnacle matchup / Polymarket event.
- Values that cannot be confirmed from a source are left blank and the match is listed under
  Unresolved or Flagged — never inferred, never filled by hand.
- Fuzzy cross-source name matches, market/model divergences, thin markets, and inventory
  discrepancies are auto-flagged on the Flagged page.

## Coordination

Multiple agent sessions may work here — see [COORDINATION.md](COORDINATION.md) (shared task board,
claims, sources registry, log).

## Disclaimer

Independent analytics project. Not affiliated with Hotspawn, Riot Games, Pinnacle, or Polymarket.
Nothing here is betting advice.
