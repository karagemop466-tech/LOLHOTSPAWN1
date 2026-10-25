# External line search for the unpriced matches — 2026-10-25

Session `cb84d7dc` · branch `arena/cb84d7dc-lolhotspawn1` · research window
**2026-10-25T14:04Z – 14:08Z**

> **Companion memo.** [`external-lines-2026-10-25.md`](external-lines-2026-10-25.md) (session `63c67a23`)
> covers the *same* question from the other end of the pipe on the same day: the GitHub Actions runner's
> 37-venue probe (added 2026-10-25T14:09:09Z), plus exchange/API reads (Pinnacle leagues, Polymarket gamma,
> Sofascore 403, bo3.gg API with no price fields). This file covers what a **reader sees on the consumer
> book pages themselves** — lobbies, per-league market pages, odds-comparison indexes — and it is the first
> pass in which one tier-2 line was actually found. The two do not contradict each other; together they show
> the ceiling is structural (only Worlds plus one LGC Rising tie) from both vantage points.

## The question

The brief: *"We need to originate our own lines for all matches… Look for information sources to guide
pick selections only for any matches that cannot be resolved in the same way as the featured picks.
Try established LOL betting sites, then try looking at esportsbooks and esports betting lines."*

So this is not "is there a book for Worlds?" — the featured resolution already prices those. This is a
directed search for a **price on the matches below that ceiling**: the PRM 2nd/3rd Divisions, RIVALS
LEAGUE, the Tunisian Super League, Komplettligaen, LigaGG CELOL, the Arabian League 2nd Division,
4 Nations and the rest of the national/academy tail that makes up most of the Hotspawn list.

## How the checks were made, and the two network paths

| Path | What it can reach | Used for |
|---|---|---|
| **GitHub Actions runner** (the pipeline) | Pinnacle guest API, Kalshi, Bovada, Unibet/Kambi, Polymarket, Leaguepedia, Hotspawn | the prices that actually set a pick — receipts in `data/raw/` and `data/source_probes.json` |
| **Research sandbox fetch** (this session) | the public web, including venues that 403 the runner | the checks below, recorded as receipts in `data/receipts/external_odds/2026-10-25.json` |

The sandbox's own shell has no HTTPS egress to these hosts (verified again this session: `curl` to the
Hotspawn API, Pinnacle and Leaguepedia returned HTTP `000`), so every reading below came through the
separate fetch path. That keeps the evidence independent of the runner, and it is why the readings can
show something the pipeline cannot fetch itself.

## What each venue showed — 2026-10-25

Every row is one page actually opened. The verbatim column is the sentence the page printed; the
receipt file carries the same text, the URL and the capture time.

| # | Venue (kind) | Page | Verdict for the unpriced leagues | Verbatim |
|---|---|---|---|---|
| 1 | **Thunderpick** (esportsbook) | <https://thunderpick.io/esports/league-of-legends> | Its **entire** LoL category was 11 markets on two competitions: Worlds 2026 (10) and LGC Rising 2026 Playoffs (1). No PRM division, RIVALS, Tunisian, Komplettligaen, LigaGG, Arabian or 4 Nations market exists there today. | `League of Legends 11 · Worlds 2026 10 · LGC Rising 2026 Playoffs 1` |
| 2 | **Cloudbet** (esportsbook) | <https://www.cloudbet.com/en/esports/league-of-legends?tab=today> | The LoL lobby listed **one** competition with events: the LoL World Championship. | `International — LoL World Championship` |
| 3 | **Cloudbet**, Prime League 2nd Division page | <https://www.cloudbet.com/en/esports/league-of-legends/germany-t8205-prime-league-2nd-division> | The book **has** a dedicated PRM 2nd Division market page — but it carried **no event**. This league supplies 36 of the 241 Hotspawn cards. | `No Prime League 2nd Division events availableCheck back later for the latest updates on upcoming matches.` |
| 4 | **EGamersWorld** (aggregator of 5 books) | <https://egamersworld.com/lol/bets> | The today's-upcoming block carried only 2026 World Championship cards, each compared across Vave, Thunderpick, Rainbet, Underdog and CocoBet. | `Vave 1.2 4.4 · Thunderpick 1.3 3.2 · Rainbet 1.24 3.54 · Underdog 1.23 3.53 · CocoBet 1.26 3.49` |
| 5 | **bo3.gg** (aggregator) | <https://bo3.gg/lol/matches/current> | Four LoL cards for the day, all `Worlds 2026`, each with a two-sided decimal pair. | `13:00 Hanwha Life Esports Bo1 Invictus Gaming 1.25 3.50 … 18:00 Gen.G Esports Bo3 LYON 1.04 8.00` |
| 6 | **Betmonitor** (24–27-book comparison) | <https://www.betmonitor.com/odds-comparison/esport/today> | Four LoL events for the day, all World Championship, each quoted by 24–27 bookmakers. No tier-2/national LoL event anywhere in the day's esports schedule. | `World Championship Today 25 Oct 13:00 · Hanwha Life – Invictus Gaming · 26 Bookmakers, 164 odds` |
| 7 | **OddsPortal** (comparison engine) | <https://www.oddsportal.com/esports/league-of-legends/> | The **whole** League of Legends index contains one competition, with 10 priced events. | `League of Legends World Championship (10)` |
| 8 | **GG.BET** (established LoL book) | <https://gg.bet/en/esports/league-of-legends> | Refused this location outright — no lobby, no price. (The runner separately gets HTTP 403 from the same host; the two verdicts are recorded separately.) | `This internet site is not accepting visitors from your region.` |
| 9 | **Vave** (esportsbook) | <https://vave.com/esports/league-of-legends> | Refused this location. Vave's prices are only visible through the aggregator that mirrors them. | `Vave is currently not available in your region` |
| 10 | **Rivalry** (former esportsbook) | <https://rivalry.com/esports/league-of-legends> | **Closed.** The LoL URL redirects to an operational-closure notice, so it should be dropped from the candidate-venue list rather than retried. | `Rivalry's operations have now ceased. Player access is no longer available through this site.` |

### One tier-2 line that does exist

Thunderpick *does* price one lower-tier competition that Hotspawn also lists. On the LGC Rising 2026
Playoffs page it had the series that Hotspawn schedules as `#1079080` (`Mental Rush vs Vitality Rising
Bees`, BO5, 2026-10-27T17:00Z):

> `Tuesday, October 27th · BO5 · Oct 27, 13:00 · LGC Rising 2026 Playoffs · Vitality Rising Bees -238 vs +162 Mental Rush`
> — <https://thunderpick.io/esports/league-of-legends/lgc-rising-2026-playoffs/11363/vitality-rising-bees-vs-mental-rush/2876675>

-238 → **1.42** decimal, +162 → **2.62** decimal. De-vigged: Mental Rush **35.2 %** / Vitality Rising
Bees **64.8 %**. Our published row (a live Polymarket/Pinnacle read) says Mental Rush **38.5 %**, a gap
of **−3.4 pp** — inside the 8 pp agreement threshold, so it is filed as `agrees` in the corroboration
ledger. It is a **cross-check, not the price of record**: a hand-transcribed book page is not a live
feed, and the pipeline's own rule is that only a fresh, machine-read quote may set a probability.

## What this means for the picks

1. **The tail is unpriced by everybody, not by us.** On 2026-10-25 the widest external coverage of the
   Hotspawn list was 11 series (Thunderpick) and 10 events (OddsPortal), all Worlds plus one LGC Rising
   tie. The other **26 of 29 competitions** had no open price at any venue checked, on either path.
2. **So those matches are originated, not quoted.** Their probability is our Elo line from recorded
   Leaguepedia series results (or *provisional* where a side has fewer than five rated series), and the
   site labels every row with its method and links its source. Nothing is borrowed from an aggregator
   placeholder, and Hotspawn's own crowd percentage is never an input.
3. **The leagues are not permanently unbettable — they are just not on the board today.** Cloudbet keeps
   a PRM 2nd Division page that was empty today; Thunderpick will price an LGC Rising tie but not the
   German divisions. That is exactly the kind of gap a keyed odds API (e.g. a paid esports odds feed
   covering Prime League Pro/2nd Division) would close, and no credential is used or circumvented here.
4. **Nothing in this document is a probability input.** These are coverage checks. The rule that keeps
   the numbers honest is unchanged: a match is priced from a book only when a machine-readable, fresh,
   two-sided quote exists for *that* match, otherwise it carries an originated line and says so.

## Limitations of this evidence (published, not hidden)

- **One snapshot, one location.** Each row is what the page served to this reader at that minute. Prices
  open and close during a matchday; a league page that was empty at 14:05Z can carry events later.
- **Geo-restriction is not the same as "the book has no line".** GG.BET and Vave refused this location.
  That is recorded as *unreadable from here*, never as *no market exists*.
- **Aggregators are not books.** EGamersWorld, bo3.gg, OddsPortal and Betmonitor mirror prices from
  books (Vave, Thunderpick, Rainbet, Underdog, CocoBet, and 20+ others). A price read on an aggregator
  is attributed to the aggregator in the ledger, not to the underlying book.
- **A page existing is not a market existing.** Cloudbet's PRM 2D page is a permanent marketing page; the
  market list inside it was empty. Only the empty event list is cited, never the page's existence.
- **The runner cannot reproduce these reads.** All the venues in this file except those already in the
  pipeline are blocked or JavaScript-only from GitHub Actions, so these are manual, dated captures whose
  validity expires with the 24-hour window in `tools/corroborate.py`.

## Files

| File | Contents |
|---|---|
| `data/receipts/external_odds/2026-10-25.json` | the machine-readable receipts: 9 sources, 10 observations, 1 capture, every reading verbatim with URL and capture time |
| `data/corroboration.json` | produced by `tools/corroborate.py`; validates every capture against the dataset and lists each observation |
| `coverage.html` | the published per-competition coverage matrix plus the observation ledger |
| `unresolved.html#observed` | the same checks rendered for a reader, linked from the executive summary |
| `research/LONGTAIL_VENUES.md` | the earlier (2026-10-24) 32-venue dossier this session re-checked |
