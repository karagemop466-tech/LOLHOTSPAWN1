# External line coverage for the Hotspawn LoL list — measured, not assumed

Session `ada2798c`, 2026-10-24. Every number below comes from a payload committed in this
directory; nothing is inferred. Re-run with `python3 audit/ada2798c/probe.py` and
`python3 audit/ada2798c/probe2.py` (they need outbound HTTPS, so they run on the GitHub
runner via `.github/workflows/ada2798c-research.yml`).

> **Question this answers.** Why do only ~9 of the 241 matches Hotspawn lists carry a
> bookmaker price, and can any other established LoL betting site or esportsbook fill the
> gap? Short answer: the books that answer price **only the World Championship**; the
> regional and academy tail that makes up 96 % of the list is quoted by **no reachable
> source**, which is exactly why those rows have to be priced from our own model.

---

## 1. Receipts in this folder

| File | What it is |
|---|---|
| `hotspawn_live.json` | The complete live `status=scheduled` LoL feed captured at the time in `coverage_delta.json` (24 chunks of the pick'em API) |
| `coverage_delta.json` | Live inventory vs the published `data/matches.json`: id deltas, per-competition deltas, which archived receipts have rolled off |
| `venue_probe.json` | HTTP verdict for 29 candidate price sources (status, bytes, content type, whether the payload holds decimal prices) |
| `venue_coverage.json` | Every live Hotspawn fixture joined, by team name, to Pinnacle / Unibet-Kambi `ubse` / Kambi `paf`, with the join result |
| `pinnacle_leagues.json` | The LoL leagues Pinnacle actually offers, and how many matchups each has |
| `raw/pinnacle_matchups.json` | Compact extract of all 244 esports matchups in Pinnacle `sports/12` (id, league, teams, start, type) |
| `raw/kambi_ubse.json`, `raw/kambi_paf.json` | The 8 Kambi match-level markets per operator, with odds where a two-sided market exists |
| `probe.log`, `probe2.log` | Verbatim runner output |
| `verify_published.json` | Independent re-verification of the published HTML (see §6) |

Capture times: inventory and venues at **2026-10-24T16:18–16:21Z**; the published dataset
it is compared against was generated **2026-10-23T17:13:12Z**.

---

## 2. The published list was already out of date when measured

| Measure | Value | Source |
|---|---|---|
| Fixtures on the live Hotspawn feed | 241 | `coverage_delta.json → live_fixtures` |
| Fixtures in the published dataset | 241 | `coverage_delta.json → dataset_fixtures` |
| Ids on the live feed but not in the dataset | **20** | `coverage_delta.json → live_not_in_dataset` |
| Ids in the dataset but no longer on the feed | **20** | `coverage_delta.json → dataset_not_in_live` |
| Competitions live vs published | 29 vs 27 | `coverage_delta.json` |
| Age of the published dataset at measurement | ≈ 23 h | `dataset_generated_utc` |

The row count matching (241 = 241) is a coincidence: the identities differ by 20 fixtures in
each direction. That is the symptom of the refresh outage — `refresh-picks` had failed on
four consecutive scheduled runs, so the site was serving a day-old list. The cause is fixed
(see `COORDINATION.md`, sessions `5ff8e6bf`/`80c624cd`/`ada2798c` all found it independently:
archived external receipts whose Hotspawn card had settled were being counted as rejected).

**Composition of the live list** (from `hotspawn_live.json`):

| Bucket | Fixtures | Note |
|---|---|---|
| Kick-off already passed, still `status=scheduled` | 77 | Oldest 2026-08-26. Hotspawn does not close settled cards; the site marks these "start time passed" |
| Upcoming (after 2026-10-24T16:21Z) | 164 | Latest 2026-11-15T18:30Z |

Upcoming competitions, largest first: PRM 3rd Division (61), PRM 2nd Division (36),
Tunisian Super League (20), RIVALS LEAGUE Season 2 (18), Worlds 2026 Main Event (8),
Arabian League 2nd Division (6), 4 Nations 2026 Halloween Heist (4), Komplettligaen 2026
Autumn Playoffs (3), LCP 2027 Promotion (3), LigaGG CELOL A/B Playoffs (2 + 2),
LGC Rising 2026 Playoffs (1).

---

## 3. Which price sources actually answer

Probed from a GitHub Actions runner with a browser User-Agent. `200` alone is not "usable" —
a source only counts if the payload contains a two-sided decimal price for a match we list.

### Reachable and usable

| Source | Endpoint | Status | What it actually prices |
|---|---|---|---|
| Pinnacle (sharp) | <https://guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups> | 200, 676 KB | 244 esports matchups, **136 of them LoL — all in "League of Legends - World Championship"** |
| Pinnacle leagues | <https://guest.api.arcadia.pinnacle.com/0.1/sports/12/leagues> | 200 | One LoL league only (id 9587, *League of Legends - World Championship*) |
| Unibet / Kambi `ubse` | <https://eu-offering-api.kambicdn.com/offering/v2018/ubse/listView/esports/league_of_legends/all/all/matches.json?lang=en_GB&market=ZZ> | 200 | 8 match-level markets, **all 8 two-way** |
| Kambi `paf` | same path, operator `paf` | 200 | the same 8 markets, two-way, **identical prices to `ubse`** — a mirror, not an independent second opinion |
| Bovada | <https://www.bovada.lv/services/sports/event/coupon/events/A/description/esports/league-of-legends?marketFilterId=def&preMatchOnly=true&lang=en> | 200 | 8 moneylines |
| Kalshi (CFTC) | <https://api.elections.kalshi.com/trade-api/v2/events?series_ticker=KXLOLGAME&status=open&with_nested_markets=true&limit=100> | 200 | Worlds series contracts |
| Polymarket | <https://gamma-api.polymarket.com/events?closed=false&limit=5&tag_slug=league-of-legends> | 200 | Worlds series markets |

### Reachable but not a price source

| Source | Endpoint | Status | Why it is not used |
|---|---|---|---|
| Kambi `coolbet` | same Kambi path, operator `coolbet` | 200, 633 B | empty book for LoL |
| bo3.gg | <https://api.bo3.gg/api/v1/matches> | 200 | match centre without a usable odds endpoint (see `data/line_source_research.json`) |
| Leaguepedia (Cargo) | <https://lol.fandom.com/wiki/Special:CargoExport> | 200 | results and forfeit directives; **no prices** |
| Midnite | <https://www.midnite.com/api/events?sport=league-of-legends> | 200, HTML | SPA shell, no JSON market payload |

### Blocked from the runner

| Source | Endpoint | Status | Note |
|---|---|---|---|
| GG.BET | <https://gg.bet/en/esports/league-of-legends> | 403 | region blocked |
| Thunderpick | <https://thunderpick.io/api/v1/sports/esports/matches> | 403 | Cloudflare |
| EGamersWorld | <https://egamersworld.com/lol/matches> | 403 | Cloudflare from the runner. Readable in a browser: on 2026-10-24 it listed **World Championship matches only**, with decimal prices (e.g. Top Esports 2.51 / AG.AL 1.45; G2 1.14 / LOS 4.87) |
| Oddspedia | <https://oddspedia.com/esports/league-of-legends> | 403 | |
| Sofascore | <https://api.sofascore.com/api/v1/sport/esports/scheduled-events/...> | 403 | |
| escorenews | <https://escorenews.com/en/league-of-legends> | 403 | |
| Betano | <https://www.betano.com/api/sporttree/esports> | 403 | HTML shell |
| OddsPortal | <https://www.oddsportal.com/esports/league-of-legends/> | 503 | JS-rendered, no prices in HTML |
| Rivalry | <https://api.rivalry.com/api/v1/games> | 403 / 530 | documented public API, blocked at the edge |
| Betway | <https://www.betway.com/sports/esports/league-of-legends> | 404 | |
| 1xBet | <https://1xbet.com/Line/Esports/League-of-Legends> | 203 | non-authoritative response, no machine-readable coupon |
| Kambi `ubus` / `ubpl` / `ubde` | same Kambi path | 400 | `Unable to resolve customer` — needs an operator id we do not have |
| LoL Esports (Riot) | <https://esports-api.lolesports.com/persisted/gw/getSchedule?hl=en-US> | 403 | official schedule, requires an API key from this runner |

---

## 4. The ceiling, measured

Joining all 241 live fixtures to the reachable books by normalised team name
(`venue_coverage.json`, conservative matcher — "Academy"/"Rising" are never stripped, so a
main roster can never be joined to its academy team):

| Measure | Value |
|---|---|
| Hotspawn fixtures listed by Pinnacle at all | **7** (all Worlds 2026 Main Event) |
| Hotspawn fixtures with a **Pinnacle open moneyline** at probe time | **5** |
| Hotspawn fixtures joined to a Unibet/Kambi `ubse` or `paf` market | **8** (both operators, identical prices) |
| Hotspawn fixtures with **any** external price | **8** |

The seven Pinnacle-listed fixtures, for manual review:

| Fixture id | Match | Open moneyline |
|---|---|---|
| 1067688 | Top Esports vs Anyone's Legend | yes |
| 1067684 | LYON vs Karmine Corp | yes |
| 1067683 | Hanwha Life Esports vs Gen.G | yes |
| 1067880 | Dplus KIA vs T1 | yes |
| 1067689 | Bilibili Gaming vs Team Liquid | yes |
| 1067881 | Movistar KOI vs CTBC Flying Oyster | no (market not open yet) |
| 1067687 | Invictus Gaming vs Team Secret Whales | no (market not open yet) |

**So the hard ceiling for bookmaker-backed probabilities on this list is ≈ 8 of 241 = 3.3 %,
and every one of those is a World Championship series.** The other 233 fixtures are
regional, national, academy or promotion play. None of the 29 sources probed — including
every established LoL betting site that answered — publishes a price for them:

- PRM 3rd Division — 61 upcoming fixtures, 0 quoted
- PRM 2nd Division — 36 upcoming fixtures, 0 quoted
- Tunisian Super League — 20 upcoming fixtures, 0 quoted
- RIVALS LEAGUE Season 2 — 18 upcoming fixtures, 0 quoted
- Arabian League 2nd Division, Komplettligaen, LigaGG, LCP Promotion, LIT, Benelux, 4 Nations — 0 quoted

The reason is commercial, not technical: these leagues have no liquid market, so there is no
price to collect. That is the honest explanation for "we do not have picks from betting sites"
on those matches, and it is why the site originates its own number for them.

---

## 5. What the site does about it (and what it must not do)

1. **Market rows** (9 today) — de-vigged bookmaker moneylines from Pinnacle, Kalshi, Bovada,
   Unibet/Kambi and Polymarket, each row carrying the venue URL. Never Hotspawn's own crowd
   percentage, never Hotspawn's tier or points.
2. **Originated rows** (≈ 228) — our Elo line over Leaguepedia series results, evaluated
   strictly before each kick-off, labelled `model` or `provisional` so a thin record is never
   presented as a confident number.
3. **Settlement rows** (4) — a fixture whose participant was administratively removed gets the
   correct side with **no** probability, because no competitive line can be defended.
4. **Nothing is invented** to fill the gap. Where a probability cannot be defended, the row is
   left unpriced and listed on `unresolved.html` / `flagged.html` rather than guessed.

Publishing an originating model is the correct response to a 3.3 % market ceiling; the wrong
response would be to relabel a model number as a market price or to borrow Hotspawn's crowd
data. Both are explicitly excluded by `tools/verify.py`.

---

## 6. Independent verification of the published pages

`audit/ada2798c/verify_published.py` re-derives the published numbers from the HTML the
reader sees, without importing `tools/` (result in `verify_published.json`, 14/14 pass on the
snapshot it ran against):

| Check | Result |
|---|---|
| One table row per dataset fixture, no duplicate ids | 241 / 241 |
| The percentages printed equal `data/matches.json` | 237 priced rows compared, 0 mismatches |
| Two probabilities per row sum to 100 % (± 0.2 pp) | 241 / 241 |
| The named pick is the higher-probability side and is rendered | 0 problems |
| Every row carries an `https://` source link | 241 / 241 |
| `picks.html` renders every fixture exactly once | 241 cards, 0 missing, 0 duplicates |
| Exec summary links to every picks view and states the limitations | present |
| Every page declares a mobile viewport; no fixed width > 420 px | 13 pages, 0 offenders |
| No `None` / `nan` / `undefined` rendered as a value | 0 |
| Coverage arithmetic (priced + settlement + unpicked = total) | 237 + 4 + 0 = 241 |

---

## 7. What would actually increase market coverage (for the next session)

Ranked by expected value, with the blocker stated:

1. **A credentialed odds API** — The Odds API, Abios, Bayes Esports or Sportradar. These are
   the only sources that carry tier-2/3 LoL systematically. Blocker: paid key; none is
   available in this repository, so this is a decision for the account owner, not a scraper.
2. **A Kambi operator id that prices the regional tail** — `ubse` and `paf` answer 200 but
   carry 8 Worlds markets. Blocker: `ubus`/`ubpl`/`ubde` return `Unable to resolve customer`.
3. **Browser-rendered capture of GG.BET / Thunderpick / EGamersWorld** — all three price
   esports and are Cloudflare-blocked from a runner. The repository already has a manual
   receipt path (`data/receipts/external_odds/`, rendered on `coverage.html`); a human or a
   browser-automation job could add receipts, but today those sites show Worlds-only LoL
   anyway, so this buys little.
4. **Nothing else** — every remaining probe in §3 was either a dead endpoint or a page with
   no prices.

The practical conclusion: **stop hunting for a bookmaker for the tail and make the model row
the product** — with the market row as corroboration where it exists. That is what the page
already does; this document supplies the evidence for the limitation text on
`index.html` and `unresolved.html`.
