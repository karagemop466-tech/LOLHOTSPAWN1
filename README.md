# Hotspawn LoL Pick'em Board

A self-refreshing dashboard that mirrors **every League of Legends match in the Hotspawn Play
pick'em lobby** and publishes a pick plus a bookmaker-derived win probability for every match that
an external sportsbook or prediction market actually prices.

**Live site:** https://karagemop466-tech.github.io/LOLHOTSPAWN1/
(Executive summary → Picks → Unresolved → Leagues → Method → Sources → Flagged.)

## What it does

| Step | Detail |
|---|---|
| Fixtures | `https://play.hotspawn.com/lol-pickems` — Angular SSR page, match list read from the embedded `<script id="ng-state">` JSON. 264 matches / 27 competitions in the reference snapshot. |
| Prices | Bovada (US sportsbook), Pinnacle (sharp book), Polymarket (prediction market). Two-way moneylines only, de-vigged proportionally, blended by median. |
| Output | Pick, win probability, confidence, every source with a link, or an explicit "no external market" reason. |
| Cadence | GitHub Actions cron `17 */4 * * *` (every 4 hours) + manual dispatch + push. |
| Pages | Static HTML in the repo root, styled mobile-first, published by GitHub Pages. |

**Hotspawn crowd pick percentages are stored for display only and never enter a probability.** If no
external market exists, the match is published on the *Unresolved* page — we do not invent a number.

## Repository layout

```
pipeline/           collector, market adapters, data builder, static-site builder (stdlib only)
  hotspawn.py       ng-state parser for the LoL pick'em lobby
  markets.py        Bovada / Pinnacle / Polymarket adapters (+ unused 1xBet attempt)
  build_data.py     matching, de-vigging, consensus, picks, unresolved reasons
  build_site.py     renders the dashboard pages from data/
data/               generated JSON/CSV snapshots (committed so the site is static)
assets/             site CSS + small progressive-enhancement JS
tools/              one-off diagnostics used to reverse-engineer the sources
.github/workflows/  refresh.yml (collect → build → commit → Pages), probe.yml (diagnostics)
*.html              generated dashboard pages
COORDINATION.md     shared task board for parallel agent sessions
VERIFICATION.md     line-by-line verification notes and open irregularities
```

## Run locally

```bash
python3 pipeline/build_data.py     # hits Hotspawn + the three market APIs
python3 pipeline/build_site.py     # regenerates the HTML in the repo root
python3 -m http.server 8000        # preview at http://localhost:8000
```

Python 3.10+ standard library only — no pip installs, no API keys. Pinnacle's guest key is the
public one their website uses; Bovada and Polymarket endpoints are public.

## Known limits

* Only tier-1/tier-2 competitions are traded by regulated books. Amateur and semi-pro leagues
  (PRM 2nd/3rd Division, Tunisian Super League, Icelandic Esports League, 4 Nations, LigaGG, …)
  are listed but unpriced — see the *Unresolved* page for the per-league reason.
* Books post lines close to kickoff, so the priced count is lowest right after a daily rollover.
* Polymarket quotes are market mid/last prices, not bookmaker lines; they are labelled as such.

See `VERIFICATION.md` for the source-by-source verification trail and the irregularities that are
flagged for human review.
