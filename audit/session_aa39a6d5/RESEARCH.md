# U2 — where would an extra price for the low-tier tail come from? (2026-10-25)

Session `aa39a6d5` · evidence: [`probe_results.json`](probe_results.json) ·
raw captures: [`raw/`](raw/) · script: [`probe_lowtier_venues.py`](probe_lowtier_venues.py)

## The question

Every Hotspawn LoL card already carries a pick on this site (market, originated Elo,
provisional, or official-forfeit settlement). The open question the owner keeps asking is
whether the **226 live fixtures without a market price** — overwhelmingly national,
academy and 2nd/3rd-division leagues — can be priced from *some* outside book the way the
featured picks are, instead of from our own model.

## Method

One unauthenticated GET per candidate from a GitHub Actions runner at
`2026-10-25T14:17Z` (the sandbox has no egress to these hosts; the runner is the same
network path the six-hourly refresh uses). Unlike the 2026-10-23/24 probes, which
recorded per-venue HTTP verdicts, every response here was **joined against the live
Hotspawn inventory** (231 fixture pairs at probe time), so the deciding number is
*how many of our unpriced cards this venue would newly price*. Candidates were chosen
from October-2026 review consensus on the deepest LoL books (GG.BET "covers every regional
league", Thunderpick "Challengers Korea … and the Prime League", Rivalry, Midnite) plus
aggregators observed carrying LoL prices (bo3.gg, Esports Insider, tips.gg, Vave/Rainbet
via EGamersWorld's comparison) plus gol.gg as a possible results-depth source.

## Result: none of the 15 candidates prices a single unpriced card

| Candidate | Runner verdict | Would newly price |
|---|---|---|
| Rivalry REST `api.rivalry.com/api/v1/sports/league-of-legends/events` | HTTP 502 | 0 |
| Rivalry GraphQL `api.rivalry.com/graphql` | HTTP 502 | 0 |
| GG.BET API `gg.bet/api/v1/sports/esports/league-of-legends/matches` | 403 | 0 |
| GG.BET LoL page `gg.bet/en/esports/league-of-legends` | 403 | 0 |
| Thunderpick `thunderpick.io/api/v1/sports` | 404 | 0 |
| Thunderpick `api.thunderpick.io/v1/sports/league-of-legends/matches` | DNS failure | 0 |
| Midnite `midnite.com/esports/league-of-legends` | 200 HTML shell, 0 listed pairs | 0 |
| bo3.gg API `api.bo3.gg/api/v1/matches?discipline=lol` / `?game=lol` | 200 JSON, byte-identical both ways, first row is a 2020 CS:GO match — filters ignored | 0 |
| Esports Insider `esportsinsider.com/betting-odds/lol` | 200; 10 per-match odds links; literal names for 7 new Worlds cards + 1 already-market card | 0 low-tier |
| tips.gg `tips.gg/lol/matches/` | 403 | 0 |
| Shuffle `shuffle.com/sports/esports` | 200 JS shell, no prices | 0 |
| Vave `vave.com/sports/esports/league-of-legends` | 200 JS shell | 0 (see false-positive note) |
| Rainbet `rainbet.com/sports/esports` | 404 | 0 |
| gol.gg `gol.gg/esports/esports-stats/` | 404 (JS framework body); not an odds source, inconclusive as results depth | n/a |

This replicates, on a fresh date and against a fresh inventory, the structural finding of
[`research/LONGTAIL_VENUES.md`](../../research/LONGTAIL_VENUES.md) (2026-10-24): books
stop at international tier, and the Hotspawn long tail (PRM 2nd/3rd Division, Tunisian
Super League, Icelandic Esports League, Komplettligaen, LigaGG CELOL, Arabian 2nd
Division, …) is priced by nobody reachable. The review-site claims of "regional coverage"
mean VCS/PCS/CBLOL/LJL-class leagues — still two tiers above the cards in question.

### Two apparent hits, both verified false

The tolerant substring join initially flagged 1 Vave pair and several gol.gg pairs.
Literal re-checks against the raw captures killed both: on Vave, neither "REH Gaming"
nor "Cloud eSport" appears — `cloud` matched `cloudfront.net` CDN hosts; on the gol.gg
404 page, none of the low-tier team names appears literally either. They are recorded
here so nobody re-chases them.

### Esports Insider is real — and still tier-1 only

It publishes server-rendered per-match odds pages (Bet365/Betway/GG.bet/Stake prices),
and its index named 7 Worlds 2026 fixtures Hotspawn added after our 2026-10-24 snapshot
(ids `1075816`–`1075822`). That corroborates the same matches Pinnacle/Kalshi/Bovada/
Kambi/Polymarket already price, so scraping it would add fragility without adding a
single newly priced card. It is logged in
[`data/line_source_research.json`](../../data/line_source_research.json) as a candidate
for the existing *manual receipt* corroboration channel on market rows
(`data/receipts/external_odds/`), per-match URL pattern
`esportsinsider.com/betting-odds/lol/match/<slug>-<id>`.

## What therefore prices the tail (and its limitations)

1. **Originated Elo line** (`model`) — series results from Leaguepedia
   (community-maintained, <https://lol.fandom.com/wiki/Special:CargoExport>),
   recency-weighted, no look-ahead (gated). Limitation: a model estimate, not a market.
2. **Provisional Elo** — same model where a side has <5 rated series; explicitly labelled
   low confidence everywhere it renders, including the new home-page method tags.
3. **Official-forfeit settlement** — Leaguepedia `dqteams` + Hotspawn's published void
   rule (<https://play.hotspawn.com/how-it-works>); shown with no percentage, never
   counted as a forecast.
4. **Not used, on principle**: Hotspawn crowd percentages (would be circular);
   tips.gg-style community model percentages (someone else's unexplained number cannot
   become our probability); placeholder 1.80/1.80 aggregator defaults (quarantined by
   both `model.py` and `corroborate.py`).

## Note on PR #56 (Rivalry venue, session 4106ce94)

Not merged this session: its premise currently fails empirically — `api.rivalry.com`
answered 502 to both REST and GraphQL probes from the runner today (and Cloudflare 530
to the 2026-10-24 probe). If Rivalry's public API returns, the retest is one dispatch of
this probe (workflow YAML preserved in git history on this branch).

## Manual-review links

- Hotspawn inventory (live): <https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=lol&status=scheduled&tenantId=1>
- Hotspawn pick'em + rules: <https://play.hotspawn.com/lol-pickems> · <https://play.hotspawn.com/how-it-works>
- Esports Insider LoL odds: <https://esportsinsider.com/betting-odds/lol>
- EGamersWorld LoL odds comparison: <https://egamersworld.com/lol/bets>
- bo3.gg LoL match centre: <https://bo3.gg/lol/matches/current>
- Leaguepedia (results corpus): <https://lol.fandom.com/wiki/Leaguepedia>
