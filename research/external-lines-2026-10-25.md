# External line sources for unmatched matches — independent check, 2026-10-25

**Session** `63c67a23` · **Question** repeated from the brief: *for every Hotspawn League of Legends
match that is not resolved the way a featured pick is (because it is low tier, or because venues such
as Polymarket do not list it), is there an outside source that can resolve the pick?* Order tried, per
the brief: (1) established LoL betting sites, (2) esportsbooks and esports betting lines, (3)
exchanges and odds aggregators, (4) community/results sources that can guide but never price a pick.

**Companion memo:** [`LINE_SEARCH_2026-10-25.md`](LINE_SEARCH_2026-10-25.md) (session `cb84d7dc`, same day)
records what the consumer book **lobbies** showed — Thunderpick's whole LoL category, Cloudbet's per-league
Prime League 2nd Division page (present, empty), Betmonitor, OddsPortal, GG.BET/Vave (geo-refused) and
Rivalry (ceased trading) — and one tier-2 line that does exist (Thunderpick on `#1079080`). Receipts:
`data/receipts/external_odds/2026-10-25.json`, rendered on `unresolved.html#observed`.

This memo does not replace [`low-tier-sources-2026-10-24.md`](low-tier-sources-2026-10-24.md) (the
51-venue runner probe). It adds a **second vantage point on 2026-10-25**, because a single egress
can be blocked by a bot wall that another egress is not, and it records what changed since.

## Method (and its limits)

Two distinct vantage points, never mixed:

| Vantage point | What it is | Evidence |
|---|---|---|
| **GitHub Actions runner** | The only egress allowed to price a published row. `tools/collect.py` runs there every 6 h; the 44-venue probe and the 51-venue low-tier probe were executed there. | [`data/source_probes.json`](../data/source_probes.json) (checked 2026-10-24T16:41:31Z), [`data/probe/lowtier_20261024.json`](../data/probe/lowtier_20261024.json) |
| **This research session** | An agent sandbox whose egress differs from the runner's. It can *observe* what a venue publishes; it **cannot** price a row, because a number only enters the dataset through `collect.py` on the runner. | captures below, each with URL and UTC timestamp |

A capture from either vantage point is only ever **evidence about availability**. If a venue returned
a real price, the only path into a published probability is a parser in `tools/collect.py` writing a
receipt to `data/raw/`, followed by the de-vig in `tools/model.py`. An HTTP 200 with an HTML shell, or
a symmetric `1.80 / 1.80` placeholder, is recorded as *no line* — never as a price.

## What was checked on 2026-10-25 (live captures)

| # | Venue / endpoint | Captured (UTC) | Result | What it means for the low-tier tail |
|---|---|---|---|---|
| 1 | Pinnacle — [`/0.1/sports/12/leagues`](https://guest.api.arcadia.pinnacle.com/0.1/sports/12/leagues) | 2026-10-25T14:06Z | **HTTP 200**; the list contains **exactly one LoL league**: `League of Legends - World Championship` (id 9587, `matchupCount: 10`). Every other league in the payload is Dota 2, CS2, Valorant or Rainbow Six. | Pinnacle — the sharpest esports book and the anchor of every market row here — publishes **no** tier-2/tier-3 LoL league at all, so there is no price to quote for the national divisions. |
| 2 | Pinnacle — [`/0.1/leagues/9587/matchups`](https://guest.api.arcadia.pinnacle.com/0.1/leagues/9587/matchups) | 2026-10-25T14:05Z | **HTTP 200**; e.g. matchup `1639229311` `LOS` vs `Secret Whales`, `startTime 2026-10-26T19:15:00Z`, `bestOfX: 3`, `hasMoneyline: true`. | Confirms the ceiling is structural, not a parse bug: the only LoL league priced is Worlds, and its moneyline is a **series** market (the `(Kills)` derivatives are rejected by design). |
| 3 | Polymarket gamma — [`?tag_slug=league-of-legends`](https://gamma-api.polymarket.com/events?closed=false&limit=20&tag_slug=league-of-legends) | 2026-10-25T14:02Z | **HTTP 200**; first event `Worlds 2026 Winning Region` (an outright, not a match market). | Polymarket prices the Worlds outright and selected series; it does not list the national/academy divisions, so it cannot resolve those picks either. |
| 4 | Sofascore — [`api.sofascore.com/api/v1/sport/esports/scheduled-events/2026-10-25`](https://api.sofascore.com/api/v1/sport/esports/scheduled-events/2026-10-25) | 2026-10-25T14:03Z | **HTTP 403** — body `{"error": {"code": 403, "reason": "Forbidden"}}`. | A bot wall from this egress; it is not a source of prices. (The runner probe of the www host also came back with no price feed.) |
| 5 | bo3.gg — [`/api/v1/matches?...discipline_id=2`](https://bo3.gg/api/v1/matches?filter%5Bmatches.discipline_id%5D%5Beq%5D=2&page%5Boffset%5D=0&page%5Blimit%5D=5) | 2026-10-25T14:05Z | **HTTP 200**, 15,385 LoL matches, fields `tier`, `tier_rank`, `bo_type`, `bet_updates`; **no price fields** in the payload. | A community statistics site: useful to corroborate tier and series format, **never** a price. |

Runner-side evidence already committed (not re-run here): of 29 competitions on Hotspawn, exactly
**2 appear in any probed venue payload** — Worlds 2026 Main Event (Pinnacle, Unibet/Kambi, Bovada,
Polymarket, Kalshi) and LGC Rising 2026 Playoffs (Polymarket only). The remaining **27 competitions
(232 of 241 matches at that snapshot) are mentioned by no reachable book, esportsbook, exchange or
aggregator** ([memo](low-tier-sources-2026-10-24.md), [receipts](../data/probe/lowtier_20261024.json)).

## Runner probe re-run on 2026-10-25 (the authoritative egress)

The same day, `tools/probe_sources.py` was re-run from a GitHub Actions runner — the only egress allowed
to price a row — against **37 venues**, including six new candidates added by this session (DraftKings and
FanDuel public content APIs, BetOnline lines, Betano's JSON coupon, and the two keyed aggregators).
Receipts: [`data/probe/sources_probe.json`](../data/probe/sources_probe.json), `probed_utc`
**2026-10-25T14:09:09Z**.

| Venue | Status | Current Hotspawn team names found | Reading |
|---|---|---|---|
| Pinnacle guest API | 200 `application/json` | **4** | Worlds ties only |
| Polymarket gamma | 200 `application/json` | **8** | Worlds ties only |
| Kalshi `KXLOLGAME` | 200 `application/json` | **8** | Worlds contracts only |
| Bovada LoL coupon | 200 `application/json` | **8** | Worlds ties only |
| BetOnline esports lines | 200 `text/html` | 0 | page shell, no current fixtures |
| Betano LoL / Betano JSON API | 200 `text/html` | 0 | HTML shell served on the API path too |
| Thunderpick, Rivalry, BC.GAME, OddsPortal, Flashscore, bo3.gg | 200 `text/html` | 0 | JS-rendered coupons; zero current fixtures in the payload |
| DraftKings content API | 403 | 0 | blocked from the runner |
| FanDuel page API | 400 | 0 | parameter/key contract rejected |
| GG.BET, Stake, Sofascore, EGamersWorld, Escorenews, Liquipedia, Riot schedule | 403 | 0 | bot/geo wall or key required |
| The Odds API, OddsPapi | 401 | 0 | key required — recorded as key-gated, never as a price |

**Only four sources named a single team that is on the current Hotspawn list, and the names are exactly
the Worlds 2026 bracket** — Pinnacle found `Anyone's Legend`, `CTBC Flying Oyster`, `Dplus KIA`, `Gen.G`;
Polymarket, Kalshi and Bovada each found those plus `Bilibili Gaming`, `G2 Esports`,
`Hanwha Life Esports`, `Invictus Gaming`. Not one esportsbook, exchange or aggregator returned a price for a national, academy or
benelux division. Combined with the 51-venue low-tier matrix from the day before (2 of 29 competitions
mentioned), the conclusion is stable across two independent probes and two egresses:

> Below the Worlds ceiling there is **no external line in existence that this pipeline can reach**, so a
> pick for those matches can only be originated from recorded results, or withheld with a stated reason.

## Conclusion — how a pick is resolved when no venue prices the match

The answer to "resolve a pick for matches we don't have one for" is **not** another book: below the
Worlds ceiling there is no external line to copy, and inventing one would be fabrication. The
defensible resolutions, in the order the pipeline applies them, are:

1. **Market line** — a real-money quote exists and is fresh (≤24 h). De-vigged across venues,
   precision-weighted, every quote URL published on the row. 6 rows at snapshot
   `2026-10-24T20:54:30Z`.
2. **Originated Elo line** — no market. Our own probability from recorded series results
   (recency-weighted Elo, division priors, margin-of-victory scaling, inactivity decay, empirical-Bayes
   shrinkage), priced strictly from the pre-kickoff rating state. 153 rows.
3. **Provisional originated line** — same model, but at least one side has fewer than five rated
   series in the 25-month window. Published with a low-confidence badge and a per-row flag. 78 rows.
4. **Official settlement, no probability** — a team was removed mid-split (`dqteams`), so the league
   itself awards the fixture; a competitive probability would be fiction. 4 rows, each naming the
   Leaguepedia page that records the forfeit, and each flagged as *not a forecast*.

Coverage at that snapshot: **241 / 241 matches carry a pick** (100 %), **237 carry a win probability**,
and the 4 without one are exactly the four DQ settlements. Hotspawn's own crowd-pick percentages are
captured for audit only and never used.

## Limitations that apply to every originated line

- **No external corroboration exists.** An originated line cannot be cross-checked against a book, so
  it is a model estimate, not a market observation. That is disclosed on every row and on
  [Methodology](https://karagemop466-tech.github.io/LOLHOTSPAWN1/methodology.html).
- **History is community-maintained.** Leaguepedia series records are the model's input; they are not
  an official league feed. Joins that are not exact string matches are published with their evidence in
  `data/matching_report.json` and on
  [Verification](https://karagemop466-tech.github.io/LOLHOTSPAWN1/verification.html).
- **Debut teams carry priors, not results.** A side with zero rated series is priced from a division
  prior (1500/1455 etc.) and labelled provisional; two debut sides meeting is close to a coin flip by
  construction, and the row says so.
- **Availability is a moving target.** Bot walls, geo-blocks and keyed APIs change hourly. This memo
  records a specific observation at a specific UTC time; it is not a permanent statement about a venue.
  The 44-venue probe (`data/source_probes.json`) is re-run on demand and its `checked_utc` is published.
- **Not legal or betting advice.** Prices are research observations; markets move after capture, and
  Hotspawn's own rule voids forfeited-match predictions.

## Reproduce

```bash
# runner-side (the authoritative egress), writes data/probe/sources_probe.json
python3 tools/probe_sources.py
# runner-side low-tier matrix, writes data/probe/lowtier_<date>.json
python3 tools/probe_lowtier.py
```

Candidate venues added to the probe on 2026-10-25, so the next runner capture records them with the
same evidence trail: DraftKings and FanDuel public content APIs, BetOnline lines, Betano's JSON coupon,
and the two keyed aggregators (The Odds API, OddsPapi) — the keyed ones are expected to answer 401 and
are recorded as *key-gated*, not as prices.
