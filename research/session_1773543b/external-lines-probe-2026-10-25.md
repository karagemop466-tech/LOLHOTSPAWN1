# External-line research for the matches no featured book prices — 2026-10-25 run

Session `1773543b` · runner capture `2026-10-25T14:27:18Z` · branch `arena/1773543b-lolhotspawn1`

**The question.** The brief is: *a pick for every League of Legends match on the Hotspawn pick'em, priced from real betting lines where those exist, originated where they do not — and never invented.* This memo is the evidence for the second half of that sentence on today's list: which established LoL books, esportsbooks, exchanges and odds aggregators actually carry a price for a listed match, and what they returned when the build runner called them.

**The answer, in one line.** 48 endpoints were called from the GitHub runner that builds this site; 20 answered HTTP 200, and **five carried any team from today's Hotspawn list — Pinnacle, Polymarket, Kalshi, Bovada and Unibet/Kambi (via its `paf` brand) — and every one of those names is a Worlds 2026 card.** The sharp book's own league list contains **exactly one** League of Legends competition, the World Championship; the other 28 competitions on the list are not opened by it at all. The remaining cards are therefore priced by this repository's own Elo line, not by a borrowed or invented quote.

## 1. Provenance of the receipts

| Item | Value |
| --- | --- |
| Receipt file | [`data/probe/sources_probe.json`](../../data/probe/sources_probe.json) |
| Probe script | [`tools/probe_sources.py`](../../tools/probe_sources.py) |
| Runner | GitHub Actions, `Linux`, `GitHub Actions 1000004531` |
| Workflow run | `40202258657` (attempt 1), branch `arena/1773543b-lolhotspawn1` |
| Commit probed | `6c01003aa210` |
| Captured at | `2026-10-25T14:27:18Z` |
| Inventory compared against | `data/matches.json`, Hotspawn fixtures fetched `2026-10-25T14:13:21Z` (234 cards) |
| Workflow | [`.github/workflows/probe-sources.yml`](../../.github/workflows/probe-sources.yml) |

The runner is the authoritative egress: this session's sandbox has no outbound network at all, so every status below is what the *build machine* received, not what a laptop or a proxy could see. A venue that blocks the runner is recorded as blocked even when a browser can open it — that is the relevant fact for an unattended pipeline.

## 2. Today's coverage, measured from the published dataset

| Metric | Value | Source |
| --- | --- | --- |
| Cards on the Hotspawn LoL pick'em list | **234** | fixtures API, `2026-10-25T14:13:21Z` |
| Cards carrying a pick | **234 / 234** | `data/matches.json` `pick` |
| Cards with a win probability | **230** | `p0`/`p1` |
| Priced from real bookmaker / exchange lines | **9** (Worlds 2026 Main Event 8, LGC Rising 2026 Playoffs 1) | `method: market` |
| Originated from recorded series results | **221** (150 model + 71 provisional) | `method: model/provisional` |
| Resolved by league rule, no probability claimed | **4** | `method: unresolved` |
| Competitions with any external price | **2 of 29** | market rows above |

## 3. League-level test: does the sharp book open these competitions at all?

Team-name matching alone cannot answer "is this league priced?" — a book can price one Worlds tie and never open the German third division. Pinnacle's public guest API exposes its open league list, so the question is answerable structurally rather than by inference:

| Pinnacle league list (`sports/12/leagues`) | Result |
| --- | --- |
| HTTP status at capture | `200` |
| Open esports leagues in the response | **11** |
| League of Legends leagues in the response | **1** |

* `League of Legends - World Championship` — 1 matchup(s) open at capture.

| Consequences | |
| --- | --- |
| Hotspawn competitions Pinnacle opens | Worlds 2026 Main Event |
| Hotspawn competitions Pinnacle does **not** open | **28 of 29** |

## 4. Every endpoint called from the runner

`status` is the HTTP code the runner received (`None` = transport failure / no response). `Teams` counts how many names from today's Hotspawn list appear anywhere in the response; `Competition` reports a full-name match, and `code only` a short-code match, which is weaker evidence (a team can be called `LCP`, and Polymarket prints "LCP (Asia-Pacific)" as a region label).

| # | Venue | What it is | HTTP | Teams | Competition named | Code only | URL |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Pinnacle guest API | established book | `200` | 4 | Worlds 2026 Main Event | LCP 2027 Promotion | <https://guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups> |
| 2 | Pinnacle league list | established book | `200` | 0 | Worlds 2026 Main Event | — | <https://guest.api.arcadia.pinnacle.com/0.1/sports/12/leagues> |
| 3 | Polymarket gamma | prediction market | `200` | 8 | Worlds 2026 Main Event | LCP 2027 Promotion | <https://gamma-api.polymarket.com/events?closed=false&limit=20&tag_slug=league-of-legends> |
| 4 | Kalshi KXLOLGAME | regulated exchange | `200` | 8 | — | LGC Rising 2026 Playoffs | <https://api.elections.kalshi.com/trade-api/v2/events?series_ticker=KXLOLGAME&status=open&with_nested_markets=true&limit=50> |
| 5 | Bovada LoL coupon | established book | `200` | 8 | Worlds 2026 Main Event | — | <https://www.bovada.lv/services/sports/event/coupon/events/A/description/esports/league-of-legends?marketFilterId=def&preMatchOnly=true&lang=en> |
| 6 | GG.BET LoL | esportsbook | `403` | 0 | — | — | <https://gg.bet/en/esports/league-of-legends> |
| 7 | BC.GAME sports | crypto esportsbook | `200` | 0 | — | — | <https://bc.game/sports/esports/league-of-legends> |
| 8 | Thunderpick LoL | esportsbook | `200` | 0 | — | — | <https://thunderpick.io/esports/league-of-legends> |
| 9 | Thunderpick API | esportsbook API | `None` | 0 | — | — | <https://api.thunderpick.io/api/v1/sports> |
| 10 | Rivalry esports | esportsbook | `200` | 0 | — | — | <https://www.rivalry.com/esports/league-of-legends> |
| 11 | Rivalry API | esportsbook API | `530` | 0 | — | — | <https://api.rivalry.com/api/v1/sport/league-of-legends> |
| 12 | Stake esports | crypto esportsbook | `403` | 0 | — | — | <https://stake.com/sports/esports/league-of-legends> |
| 13 | 1xBet line feed | high-street book API | `203` | 0 | — | — | <https://1xbet.com/LineFeed/Get1x2_VZip?sports=249&count=50&mode=4&country=1&getEmpty=true> |
| 14 | Betboom LoL | esportsbook | `401` | 0 | — | — | <https://betboom.ru/sport/lol> |
| 15 | Marathonbet LoL | established book | `403` | 0 | — | — | <https://www.marathonbet.com/en/betting/Esports/League+of+Legends> |
| 16 | Betano LoL | established book | `200` | 0 | — | — | <https://www.betano.com/sport/esports/league-of-legends/> |
| 17 | Betway esports | established book | `404` | 0 | — | — | <https://sports.betway.com/en/sports/grp/sport/esports> |
| 18 | Unibet LoL | established book | `503` | 0 | — | — | <https://www.unibet.com/betting/sports/filter/esports/league_of_legends> |
| 19 | Betsson esports | established book | `202` | 0 | — | — | <https://www.betsson.com/en/sportsbook/esports> |
| 20 | EGamersWorld LoL | odds aggregator | `403` | 0 | — | — | <https://egamersworld.com/lol/matches> |
| 21 | EGamersWorld match page | odds aggregator | `403` | 0 | — | — | <https://egamersworld.com/lol/match/q8qUtLA6g/geng-vs-invictus-gaming-x7EbSp5BR> |
| 22 | Oddspedia LoL | odds aggregator | `410` | 0 | — | — | <https://oddspedia.com/esports/league-of-legends> |
| 23 | OddsPortal LoL | odds aggregator | `200` | 0 | Worlds 2026 Main Event | — | <https://www.oddsportal.com/esports/league-of-legends/> |
| 24 | Flashscore LoL | odds aggregator | `200` | 0 | Worlds 2026 Main Event | — | <https://www.flashscore.com/esports/league-of-legends/> |
| 25 | Sofascore esports API | odds aggregator | `403` | 0 | — | — | <https://www.sofascore.com/api/v1/sport/esports/scheduled-events/2026-10-23> |
| 26 | bo3.gg LoL | odds aggregator | `200` | 0 | — | — | <https://bo3.gg/lol/matches> |
| 27 | Escorenews LoL | esports news + odds | `403` | 0 | — | — | <https://escorenews.com/en/lol> |
| 28 | BetExplorer LoL | odds aggregator | `404` | 0 | — | — | <https://www.betexplorer.com/esports/league-of-legends/> |
| 29 | DraftKings LoL (public content API) | US sportsbook | `403` | 0 | — | — | <https://sportsbook-nash.draftkings.com/api/sportscontent/dkusoh/v1/leagues/19873> |
| 30 | FanDuel LoL (page API) | US sportsbook | `400` | 0 | — | — | <https://sbapi.nj.sportsbook.fanduel.com/api/content-managed-page?page=CUSTOM&customPageId=lol> |
| 31 | BetOnline esports lines | US sportsbook | `200` | 0 | — | — | <https://www.betonline.ag/sportsbook/api/lines/esports> |
| 32 | Betano LoL JSON API | established book | `200` | 0 | — | — | <https://www.betano.com/api/sport/esports/league-of-legends/> |
| 33 | The Odds API LoL (key required) | odds API | `401` | 0 | — | — | <https://api.the-odds-api.com/v4/sports/esports_league_of_legends/odds?regions=eu&markets=h2h> |
| 34 | OddsPapi LoL (key required) | odds API | `401` | 0 | — | — | <https://api.oddspapi.io/v4/fixtures?sportId=18> |
| 35 | Kambi leovegas LoL | established book (Kambi) | `400` | 0 | — | — | <https://eu-offering-api.kambicdn.com/offering/v2018/leovegas/listView/esports/league_of_legends/all/all/matches.json?lang=en_GB&market=ZZ> |
| 36 | Kambi nordicbet LoL | established book (Kambi) | `429` | 0 | — | — | <https://eu-offering-api.kambicdn.com/offering/v2018/nordicbet/listView/esports/league_of_legends/all/all/matches.json?lang=en_GB&market=ZZ> |
| 37 | Kambi coolbet LoL | established book (Kambi) | `200` | 0 | — | — | <https://eu-offering-api.kambicdn.com/offering/v2018/coolbet/listView/esports/league_of_legends/all/all/matches.json?lang=en_GB&market=ZZ> |
| 38 | Kambi 888sport LoL | established book (Kambi) | `400` | 0 | — | — | <https://eu-offering-api.kambicdn.com/offering/v2018/888sport/listView/esports/league_of_legends/all/all/matches.json?lang=en_GB&market=ZZ> |
| 39 | Kambi paf LoL | established book (Kambi) | `200` | 8 | Worlds 2026 Main Event | — | <https://eu-offering-api.kambicdn.com/offering/v2018/paf/listView/esports/league_of_legends/all/all/matches.json?lang=en_GB&market=ZZ> |
| 40 | bo3.gg LoL today | odds aggregator | `200` | 0 | — | — | <https://bo3.gg/lol/matches/current> |
| 41 | bo3.gg Worlds 2026 tournament | odds aggregator | `200` | 0 | — | — | <https://bo3.gg/lol/tournaments/worlds-2026> |
| 42 | odds-api.io sports list | odds API | `200` | 0 | — | — | <https://api.odds-api.io/v3/sports> |
| 43 | odds-api.io esports events (key required) | odds API | `401` | 0 | — | — | <https://api.odds-api.io/v3/events?sport=esports> |
| 44 | PandaScore LoL (token required) | esports data API | `403` | 0 | — | — | <https://api.pandascore.co/lol/matches?per_page=1> |
| 45 | Abios series (key required) | esports data API | `None` | 0 | — | — | <https://api.abiosgaming.com/v2/series> |
| 46 | Riot LoL Esports schedule | official | `403` | 0 | — | — | <https://esports-api.lolesports.com/persisted/gw/getSchedule?hl=en-US> |
| 47 | Leaguepedia Cargo | results database | `200` | 0 | — | — | <https://lol.fandom.com/wiki/Special:CargoExport?tables=MatchSchedule&fields=OverviewPage,Team1,Team2,Winner,DateTime_UTC&limit=5&format=json> |
| 48 | Liquipedia LoL matches | results database | `403` | 0 | — | — | <https://liquipedia.net/leagueoflegends/Portal:Matches> |

Status histogram: 200×20, 202×1, 203×1, 400×3, 401×4, 403×11, 404×2, 410×1, 429×1, 503×1, 530×1, no response×2.

### 4a. The five feeds that carried a listed team

| Venue | Teams from today's list | Competitions named | What the price is |
| --- | --- | --- | --- |
| Pinnacle guest API | 4 | Worlds 2026 Main Event | control: sharp LoL moneylines |
| Polymarket gamma | 8 | Worlds 2026 Main Event | control: full-series CLOB |
| Kalshi KXLOLGAME | 8 | — | control: CFTC contract book |
| Bovada LoL coupon | 8 | Worlds 2026 Main Event | control: US esportsbook moneylines |
| Kambi paf LoL | 8 | Worlds 2026 Main Event | control: second operator on the same CDN |

The fixtures these names refer to are the eight Worlds 2026 cards. On the published dataset those eight are the `market` rows (plus one `LGC Rising 2026 Playoffs` card that Polymarket quotes), which is exactly the set the site labels **market-backed**. No other competition on the list was named by any reachable venue during this capture.

### 4b. Venues that answer but expose no machine-readable LoL price

| Venue | HTTP | Bytes | Why it is not a usable line |
| --- | --- | --- | --- |
| Pinnacle league list | `200` | 6141 | does Pinnacle list tier-2 leagues at all? |
| BC.GAME sports | `200` | 11871 | low-tier LoL markets |
| Thunderpick LoL | `200` | 14971 | low-tier LoL markets |
| Rivalry esports | `200` | 61219 | low-tier LoL markets |
| Betano LoL | `200` | 29842 | EU book |
| OddsPortal LoL | `200` | 335280 | multi-book comparison |
| Flashscore LoL | `200` | 765224 | multi-book comparison |
| bo3.gg LoL | `200` | 13188 | match list with odds |
| BetOnline esports lines | `200` | 366109 | JSON lines feed |
| Betano LoL JSON API | `200` | 29842 | JSON coupon behind the HTML page |
| Kambi coolbet LoL | `200` | 633 | brand-level LoL coupon, incl. tier-2? |
| bo3.gg LoL today | `200` | 13188 | which tiers carry a price on today's board |
| bo3.gg Worlds 2026 tournament | `200` | 13188 | does the tournament page price the same ties |
| odds-api.io sports list | `200` | 1351 | public sports list - does it carry esports at all? |
| Leaguepedia Cargo | `200` | 1213 | control: series results used by the model |

## 5. What would change this answer

The claim is *"no reachable venue priced the tier-2 tail at `2026-10-25T14:27:18Z`"*, not *"nobody prices tier-2 LoL"*. It would be overturned by any one of the following, each of which the pipeline can re-test without new code:

1. a venue in section 4 returning a decimal pair alongside a Hotspawn team name (the probe already records the signal);
2. Pinnacle's league list gaining a second League of Legends league (the probe records every league name, not just the count);
3. a key being configured for a documented odds API — `the-odds-api.com`, `oddspapi.io`, `odds-api.io`, `api.pandascore.co` — each currently returns 401 to an unauthenticated runner, and a 401 is recorded as key-gated, never as "no market";
4. a brand on the Kambi platform opening a national league (five operators were probed; only `paf` returned a LoL coupon, and it is the same Worlds board as Unibet).

## 6. Limitations of this memo

- Coverage is a snapshot: a book that opens a market later today is not reflected here. The probe re-runs every time `tools/probe_sources.py` changes and can be re-run at any time; each run is committed with its runner id and timestamp.
- Affiliate and review pages (for example the marketing claim that Thunderpick covers "PRM") are **not** treated as evidence. A page must return a parseable price naming a listed team to count, and Thunderpick's page returned 14,971 bytes with none of the 32 team names in it.
- Two false-positive classes were found and fixed while producing this receipt, because the first two captures of this session were wrong: a substring test matched the code `LIT` inside "split" and `POP` inside "popular"; a case-insensitive word test matched JavaScript `s.pop()` and `lcp:{...}`. Matching is now word-bounded, and a 3–6 character code matches only in its published upper case. `tests/test_probe_competitions.py` pins both fixes.
- Leaguepedia is community-maintained. It is the source of the results that drive the originated lines and of the forfeit records behind the four settlement picks; it is not an official Riot feed.
- The four unpriced cards are Komplettligaen fixtures involving `Solid Gaming`, recorded by Leaguepedia as removed mid-split. They keep a settlement pick and no percentage: a probability for a series that may be voided would be fiction.

## 7. Links for manual review

| What | Where |
| --- | --- |
| This probe's raw receipt (48 venues, evidence snippets) | [`data/probe/sources_probe.json`](../../data/probe/sources_probe.json) |
| Pinnacle open league list | <https://guest.api.arcadia.pinnacle.com/0.1/sports/12/leagues> |
| Pinnacle LoL matchups | <https://guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups> |
| Hotspawn fixture inventory (what the list is) | <https://play.hotspawn.com/lol-pickems> |
| Hotspawn public fixtures API used by the pipeline | <https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=lol&status=scheduled&tenantId=1> |
| Kalshi LoL series | <https://api.elections.kalshi.com/trade-api/v2/events?series_ticker=KXLOLGAME&status=open&with_nested_markets=true> |
| Polymarket LoL tag | <https://gamma-api.polymarket.com/events?closed=false&tag_slug=league-of-legends> |
| Bovada LoL coupon | <https://www.bovada.lv/sports/esports/league-of-legends> |
| Kambi (paf) LoL coupon | <https://eu-offering-api.kambicdn.com/offering/v2018/paf/listView/esports/league_of_legends/all/all/matches.json?lang=en_GB&market=ZZ> |
| Live site | <https://karagemop466-tech.github.io/LOLHOTSPAWN1/> |

