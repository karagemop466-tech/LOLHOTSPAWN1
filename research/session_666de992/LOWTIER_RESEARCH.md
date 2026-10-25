# Low-tier line research — 2026-10-25 (session `666de992`)

**Question.** Hotspawn's LoL list is mostly national/academy leagues that the featured
(market) resolution cannot price. Before originating our own line, does *any* reachable
established LoL betting site, esportsbook, odds-comparison engine, aggregator, prediction
market or bookmaker feed publish a price for those specific fixtures?

**Answer (measured 2026-10-25T14:12Z).** No — with one already-covered exception.
A runner probe searched 36 venue responses for the **226 live low-tier team pairs**
Hotspawn listed at probe time. The only priced tail fixture anywhere was
Mental Rush vs Vitality Rising Bees (LGC Rising), which the site already prices from
Polymarket. Two LCP 2027 Promotion fixtures appear as *schedule listings without odds*
(Strafe, EsportBet — PandaScore-sourced), and EGamersWorld shows that tie at the
symmetric `1.8 / 1.8` aggregator placeholder, which is never a price. Every other
tail competition — PRM 2nd Division (36), PRM 3rd Division (60), Tunisian Super League (24),
RIVALS LEAGUE (24), Icelandic Esports League (12), Arabian 2nd Division and regionals,
Benelux Ascend, LigaGG CELOL, Komplettligaen, and the rest — appears in **no** venue payload.
Those matches therefore keep an originated Elo line (or provisional / settlement), exactly as
the site's order of trust requires. Nothing was wired into `tools/collect.py`, because the
rule is: a new feed is wired only when it returns a real matched quote.

## Method (why this negative is credible)

1. **Pair search, not homepage checks.** `tools/probe_lowtier_666de992.py` (GitHub Actions
   `probe-666de992-lowtier`, evidence commit `817567d`) fetched the live Hotspawn scheduled
   feed (234 fixtures: 8 Worlds control pairs + 226 tail pairs), then searched each venue
   response (accent-normalised) for **both team names** of every pair. Receipts:
   `data/probe/session_666de992/probe.json` + bounded previews in `.../raw/`.
2. **Positive controls passed.** Unibet/Kambi (`ubse`, `paf`, `ubdk`, `ubbe`, `ubuk`) each
   returned all 8 Worlds pairs; BMBets' Worlds page returned 6/8 server-side; Pinnacle's
   matchup feed hit control pairs (undercounted only where Pinnacle truncates names, e.g.
   "Invictus" for Invictus Gaming). Egress and search both work; the tail is simply absent.
3. **Browser path independently agrees.** Venues that block the runner were read through a
   browser-grade fetch in the same session: EGamersWorld's full priced LoL list was
   Worlds + LGC Rising only; Cloudbet's Prime League 2nd Division page states verbatim
   *"No Prime League 2nd Division events available"* on a day PRM2 played four series;
   BMBets' PRM2 page lists no fixtures (its LoL sidebar is Worlds, Game Changers Rising,
   LCP). SEO tournament pages are not evidence of a market.

## Venue ledger (runner, 2026-10-25T14:12Z)

`ctl` = Worlds control pairs found · `tail` = low-tier pairs found. Full snippets in the receipt.

| Venue | HTTP | ctl | tail | Verdict |
|---|---|---|---|---|
| Pinnacle matchups (control) | 200 | 3 | 0 | Worlds only; leagues list confirms one LoL league (World Championship) |
| Unibet/Kambi `ubse` (control) | 200 | 8 | 0 | Worlds only |
| Kambi `paf` / `ubdk` / `ubbe` / `ubuk` | 200 | 8 each | 0 | Byte-identical 14,115-byte book — same offering, never double-counted |
| Kambi `coolbet` / `ubit` | 200 | 0 | 0 | Empty LoL offering (633 bytes) |
| Kambi `ubfi` / `ubes` | 400 | — | — | `Unable to resolve customer for extApiEndpoint` |
| Kambi `betsson` | 429 | — | — | Rate-limited / no access from runner |
| Polymarket Gamma census (58 events) | 200 | 8 | 1 | Tail hit is LGC Rising only (already priced); other leagues are Worlds outrights + stale ERL-1st remnants (Nexus, Hitpoint Masters, Road Of Legends, NACL) with settled `1/0` prices |
| Cloudbet PRM2 + LoL index | 200 | 0 | 0 | *"No Prime League 2nd Division events available"* (browser-verified) |
| BMBets PRM2 / Worlds | 200 | 0 / 6 | 0 | Comparison engine has a PRM2 shell with no fixtures |
| Betmonitor PRM2 | 200 | 1 | 0 | No PRM2 fixtures; control hit is site-wide highlights chrome |
| EGamersWorld bets/matches | 403 runner | — | — | Browser path: Worlds + LGC Rising only; LCP at `1.8/1.8` placeholder |
| Strafe odds / LoL hub | 200 | 3 / 8 | 0 / 3 | Hub *lists* LGC + 2× LCP fixtures (schedule, PandaScore); odds page has zero tail pairs |
| EsportBet LoL | 200 | 1 | 3 | Same schedule-only LGC/LCP listings; no decimal odds near the pairs |
| LOOT.BET LoL | transport error | — | — | `SSL: CERTIFICATE_VERIFY_FAILED` (self-signed) from runner — recorded, not worked around |
| Stake LoL | 403 | — | — | Bot protection (search-index copy lists PRM *1st* Division only) |
| BC.GAME sports | 200 | 0 | 0 | SPA shell, no pairs server-side |
| OddsPortal Prime League | 200 | 0 | 0 | 1st-Division page; no pairs in payload |
| Flashscore LoL | 200 | 0 | 0 | No tail pairs server-side (results coverage check) |
| bo3.gg current/tournaments | 200 | 0 | 0 | 12.8 KB JS shell — inconclusive from runner; 2026-10-24 browser check: s-tier only |
| PrimeLeague.gg Liga2/3 (official) | 403 runner | — | — | Schedule/results source (not odds); browser/search copy confirms the PRM2/3 fixtures exist there |
| Liquipedia Prime League | 403 runner | — | — | Results wiki; covers PRM 1st Division (browser-verified) |
| Odds-API.io `/v3/leagues` | 401 | — | — | `You need to provide a valid apiKey` — owner credential required |
| OddsPapi `/v4/tournaments?sportId=18` | 401 | — | — | `MISSING_API_KEY` — owner credential required |

Earlier rounds (kept as evidence, not repeated): 44-venue probe `data/source_probes.json`
(2026-10-24T16:41Z), 17-endpoint esportsbook probe `data/esportsbook_probe.json`, 51-venue
low-tier probe `research/low-tier-sources-2026-10-24.md`, browser long-tail dossier
`research/LONGTAIL_VENUES.md`. This round adds Cloudbet, BMBets, Betmonitor, Strafe,
EsportBet, LOOT.BET, Flashscore, five extra Kambi operators, and the pair-search method.

## The ceiling, stated precisely

The market does not stop at "tier 1". Polymarket/Kambi/Bovada demonstrably price
**ERL 1st divisions** (Prime League 1st, Nexus League, Hitpoint Masters, Road Of Legends)
when those leagues are in season — the collector already ingests them, so market share
rises automatically when Hotspawn lists them. This week's Hotspawn list contains **zero**
ERL 1st-division fixtures (off-season): it is 2nd/3rd divisions, non-ERL nationals and
amateur leagues, which no reachable venue prices at any point in the season. Hence
6/241 market-backed on the 2026-10-24 snapshot is a property of the calendar, not a
collector defect. Collector audit in this session: Polymarket paginates offsets 0–300
(census found 58 events total, so nothing is truncated); Kambi extras (`leovegas`,
`888sport`, `nordicbet`, `coolbet`) already run every build and return 400/429/empty.

## What would change the answer

1. **An owner-provided credential** for a deep odds API (Odds-API.io, OddsPapi, or an
   Oddin.gg-powered feed). Both APIs answered 401 without a key; depth below ERL-1st is
   *claimed* by vendors but unverified here. Flagged for the owner; never circumvented.
2. **ERL 1st divisions returning to season** — handled automatically by the existing
   Pinnacle/Kalshi/Bovada/Kambi/Polymarket ingestion; no code change needed.
3. **A book opening PRM2/3, Tunisian or LigaGG markets.** The probe is re-runnable in one
   dispatch (`probe-666de992-lowtier`); re-run it whenever the Hotspawn tail changes shape.

## Originating the rest (community sources)

With no external line to quote, non-featured picks are guided by recorded results:
Leaguepedia series history (Cargo `MatchSchedule`, 25-month window) fitted as a
pre-kickoff Elo with division priors, margin scaling, inactivity decay and shrinkage —
specification and out-of-sample backtest on `methodology.html`. Official league sites
(PrimeLeague.gg) and Liquipedia corroborate schedules/results but publish no odds and
duplicate Leaguepedia's results record, so they are review links, not model inputs.
Hotspawn crowd percentages are never an input — e.g. Babos Gaming vs Hannover
(2026-10-25): crowd 16%/84% (25 votes) vs our originated Babos 64.6% from
1635-vs-1531 Elo over 59/22 rated series. The pick follows the results record and will
be graded against it on `results.html`.

## Manual review links

- Probe receipt: [`data/probe/session_666de992/probe.json`](https://github.com/karagemop466-tech/LOLHOTSPAWN1/blob/main/data/probe/session_666de992/probe.json)
- Probe code: [`tools/probe_lowtier_666de992.py`](https://github.com/karagemop466-tech/LOLHOTSPAWN1/blob/main/tools/probe_lowtier_666de992.py)
- Cloudbet PRM2 (empty): <https://www.cloudbet.com/en/esports/league-of-legends/germany-t8205-prime-league-2nd-division>
- EGamersWorld priced list: <https://egamersworld.com/lol/bets> · LCP placeholder: <https://egamersworld.com/lol/match/eDTgthgYk/fennel-vs-nothinhere-Ud8jrB4zR>
- BMBets PRM2 shell: <https://www.bmbets.com/e-sports/world/lol---prime-league-2nd-division/>
- Polymarket LoL: <https://polymarket.com/esports/league-of-legends> · Kambi ubse feed: <https://eu-offering-api.kambicdn.com/offering/v2018/ubse/listView/esports/league_of_legends/all/all/matches.json?lang=en_GB&market=ZZ>
- Odds-API.io esports: <https://odds-api.io/esports-odds-api> · OddsPapi LoL: <https://oddspapi.io/sports/esports/lol> · Oddin feed: <https://oddin.gg/esports-odds-feed>
- Hotspawn inventory source: <https://play.hotspawn.com/lol-pickems> (fixtures API mirrors this lobby; crowd % ignored by design)
