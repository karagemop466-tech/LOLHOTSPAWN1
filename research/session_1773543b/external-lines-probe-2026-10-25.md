# External-line research for the matches no featured book prices — 2026-10-25 runner capture

Session `1773543b`. Captured **2026-10-25T14:38:07Z** by workflow run `40203073209` on the GitHub runner that builds this site. Raw receipt: [`data/probe/sources_probe.json`](../../data/probe/sources_probe.json).

## 1. What was asked, and the short answer

The brief: **a pick for every League of Legends match on the Hotspawn pick'em — priced from real betting lines where a book offers one, originated from recorded results where no book does, and never invented.** This memo is the evidence for the second half: which established LoL books, esportsbooks, exchanges and odds aggregators carry a price for a match on today's list, what they returned when the *build* runner called them, and what remains unpriced as a result.

**48 endpoints were called; 20 answered HTTP 200; 4 printed both opponents of a listed fixture, and every one of those fixtures is a Worlds 2026 card.** Pinnacle — the sharp benchmark — shows **11 open esports leagues and exactly one of them is League of Legends**, and all **80** of its LoL matchups in the same capture belong to that one league. Of the **29** competitions on the Hotspawn list, exactly **1** is opened by Pinnacle at all. The other cards are therefore priced by this repository's own Elo line over recorded series results — an originated line, labelled as such, not a quote from a book that does not quote them.

## 2. Provenance

| Item | Value |
| --- | --- |
| Captured at (UTC) | `2026-10-25T14:38:07Z` |
| Runner | `Linux` / `GitHub Actions 1000004636` (GitHub Actions; the machine that builds and publishes the site) |
| Workflow run | `40203073209`, branch `arena/1773543b-lolhotspawn1`, commit `5947f5d628c8` |
| Probe code | [`tools/probe_sources.py`](../../tools/probe_sources.py) |
| Workflow | [`.github/workflows/probe-sources.yml`](../../.github/workflows/probe-sources.yml) |
| Team names searched | **184** of the 234 cards (every name of 5+ characters; shorter ones are unusable as substring needles) |
| Fixtures tested as a pair | **234** |
| Inventory compared against | Hotspawn fixtures API, fetched `2026-10-25T14:13:21Z` |
| Coverage of the published dataset at this build | 234 cards, 230 priced, 9 market rows, 4 rule settlements |

The sandbox that wrote this memo has **no outbound network**; every status below is what the build runner received. A venue that blocks the runner is recorded as blocked even where a browser can open it — that is the relevant fact for an unattended six-hourly pipeline.

## 3. The evidence that matters: venues that printed both sides of a listed fixture

A single team name is not evidence of a market. "DELETED" is a team on the Arabian qualifier and also a CSS keyword; "Arena" is a team name and also page furniture; both appeared in raw responses this session. A venue is counted as pricing a match here only when **both opponents of the same fixture** appear in its response.

| Venue | Fixtures where both sides appear | Example |
| --- | --- | --- |
| Pinnacle guest API | 3 | Dplus KIA vs Movistar KOI |
| Polymarket gamma | 8 | Invictus Gaming vs Hanwha Life Esports |
| Kalshi KXLOLGAME | 7 | Invictus Gaming vs Hanwha Life Esports |
| Kambi paf LoL | 8 | Invictus Gaming vs Hanwha Life Esports |

Every fixture in that table is `Worlds 2026 Main Event`. Polymarket, Kalshi and the Kambi platform (`paf` brand; the pipeline reads the same board through its `ubse` brand) print the full eight-card Worlds board; Pinnacle's payload includes the same ties among its matchup set. **No reachable venue printed both sides of any tier-2, academy or national-league fixture on today's list.**

Two observations that are easy to misread:

- **Bovada answered with an empty coupon** (`{}`) at this capture while the pipeline's own 14:13:21Z collection recorded **8** Bovada Worlds fixtures in `data/raw/bovada_lol.json`. An empty coupon at probe time means the board was between markets, not that Bovada never prices LoL. This is why the published market consensus is built from the collection, not from the probe.
- **Pinnacle lists small-org names inside its payload** (for example a PRM side) because its Esports futures and derivative markets name organisations. The structural enumeration in section 4 shows those names do not correspond to a tier-2 league being open.

## 4. League-level test: what the sharp book actually opens

Team matching cannot answer "is this league priced?". Pinnacle publishes both its league list and its matchups, so the question is answerable structurally:

| Test | Result at `2026-10-25T14:38:07Z` |
| --- | --- |
| `sports/12/leagues` status | `200` |
| Open esports leagues in that response | **11** |
| League of Legends leagues among them | **1** |
| — name and open matchups | `League of Legends - World Championship` (1) |
| `sports/12/matchups` status | `200` |
| LoL matchups in the matchups payload | **80**, all in ``League of Legends - World Championship`` |
| Hotspawn competitions Pinnacle opens | Worlds 2026 Main Event |
| Hotspawn competitions Pinnacle does not open | **28 of 29** |

The competitions it does not open (the whole tier-2 and national tail on today's list): `4 Nations 2026 Halloween Heist`, `Arabian League 2nd Division 2026 Summer`, `Arabian Regional Championship 2026: Lebanon-Libya-Syria-Palestine`, `Arabian Regional Championship 2026: Qatar-Bahrain-Kuwait`, `Benelux Ascend Series 2026 Summer Playoffs`, `Benelux Ascend Series 2026 Summer Split`, `Benelux Ascend Series 2027 Winter Promotion`, `Benelux Ascend Series Rising 2026 Summer Playoffs`, `FPL 2026 Summer Playoffs`, `Hitpoint 2nd Div Challengers 2026 Summer Playoffs`, `Icelandic Esports League 2026 Autumn`, `Komplettligaen 2026 Autumn`, `Komplettligaen 2026 Autumn Playoffs`, `LCP 2027 Promotion`, `LGC Rising 2026 Playoffs`, `LIT 2027 Winter Promotion`, `Legends Academy powered by Żabka Season 3 Playoffs`, `LigaGG CELOL A 2026 Split 2`, `LigaGG CELOL A 2026 Split 2 Playoffs`, `LigaGG CELOL B 2026 Split 2`, `LigaGG CELOL B 2026 Split 2 Playoffs`, `Logitech G SuperStrike Cup Qualifier`, `POP Esports Masters Season 7`, `PRM 2nd Division 26-27 Fall`, `PRM 3rd Division 26-27 Fall`, `RIVALS LEAGUE Season 2`, `Superstrike League 2026`, `Tunisian Super League 2026`.

## 5. Every endpoint called, with what it returned

`HTTP` is the code the runner received (`—` = transport failure, no response). `Teams` counts distinct Hotspawn team names found anywhere in the body; `Both sides` counts fixtures where both opponents were found (the only column that means "this venue prices this match"); `Competition named` is a full-name league match, and `Code only` is a short-code match such as `LCP`, which is weaker — `LCP` is also a Pinnacle participant name and Polymarket's Asia-Pacific region label.

| # | Venue | Kind | HTTP | Bytes | Teams | Both sides | Competition named | Code only | URL |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Pinnacle guest API | established book | `200` | 692428 | 9 | 3 | Worlds 2026 Main Event | LCP 2027 Promotion | <https://guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups> |
| 2 | Pinnacle league list | established book | `200` | 6141 | 0 | 0 | Worlds 2026 Main Event | — | <https://guest.api.arcadia.pinnacle.com/0.1/sports/12/leagues> |
| 3 | Polymarket gamma | prediction market | `200` | 1439734 | 13 | 8 | Worlds 2026 Main Event | LCP 2027 Promotion | <https://gamma-api.polymarket.com/events?closed=false&limit=20&tag_slug=league-of-legends> |
| 4 | Kalshi KXLOLGAME | regulated exchange | `200` | 51781 | 14 | 7 | — | LGC Rising 2026 Playoffs | <https://api.elections.kalshi.com/trade-api/v2/events?series_ticker=KXLOLGAME&status=open&with_nested_markets=true&limit=50> |
| 5 | Bovada LoL coupon | established book | `200` | 2 | 0 | 0 | — | — | <https://www.bovada.lv/services/sports/event/coupon/events/A/description/esports/league-of-legends?marketFilterId=def&preMatchOnly=true&lang=en> |
| 6 | GG.BET LoL | esportsbook | `403` | 126 | 0 | 0 | — | — | <https://gg.bet/en/esports/league-of-legends> |
| 7 | BC.GAME sports | crypto esportsbook | `200` | 11871 | 0 | 0 | — | — | <https://bc.game/sports/esports/league-of-legends> |
| 8 | Thunderpick LoL | esportsbook | `200` | 14971 | 0 | 0 | — | — | <https://thunderpick.io/esports/league-of-legends> |
| 9 | Thunderpick API | esportsbook API | `None` | 0 | 0 | 0 | — | — | <https://api.thunderpick.io/api/v1/sports> |
| 10 | Rivalry esports | esportsbook | `200` | 61219 | 1 | 0 | — | — | <https://www.rivalry.com/esports/league-of-legends> |
| 11 | Rivalry API | esportsbook API | `530` | 7681 | 0 | 0 | — | — | <https://api.rivalry.com/api/v1/sport/league-of-legends> |
| 12 | Stake esports | crypto esportsbook | `403` | 5933 | 0 | 0 | — | — | <https://stake.com/sports/esports/league-of-legends> |
| 13 | 1xBet line feed | high-street book API | `203` | 2634 | 0 | 0 | — | — | <https://1xbet.com/LineFeed/Get1x2_VZip?sports=249&count=50&mode=4&country=1&getEmpty=true> |
| 14 | Betboom LoL | esportsbook | `401` | 1800 | 0 | 0 | — | — | <https://betboom.ru/sport/lol> |
| 15 | Marathonbet LoL | established book | `403` | 5849 | 0 | 0 | — | — | <https://www.marathonbet.com/en/betting/Esports/League+of+Legends> |
| 16 | Betano LoL | established book | `200` | 29842 | 0 | 0 | — | — | <https://www.betano.com/sport/esports/league-of-legends/> |
| 17 | Betway esports | established book | `404` | 6687 | 0 | 0 | — | — | <https://sports.betway.com/en/sports/grp/sport/esports> |
| 18 | Unibet LoL | established book | `503` | 592 | 0 | 0 | — | — | <https://www.unibet.com/betting/sports/filter/esports/league_of_legends> |
| 19 | Betsson esports | established book | `202` | 2597 | 0 | 0 | — | — | <https://www.betsson.com/en/sportsbook/esports> |
| 20 | EGamersWorld LoL | odds aggregator | `403` | 5944 | 0 | 0 | — | — | <https://egamersworld.com/lol/matches> |
| 21 | EGamersWorld match page | odds aggregator | `403` | 6113 | 0 | 0 | — | — | <https://egamersworld.com/lol/match/q8qUtLA6g/geng-vs-invictus-gaming-x7EbSp5BR> |
| 22 | Oddspedia LoL | odds aggregator | `410` | 341189 | 1 | 0 | — | — | <https://oddspedia.com/esports/league-of-legends> |
| 23 | OddsPortal LoL | odds aggregator | `200` | 335280 | 2 | 0 | Worlds 2026 Main Event | — | <https://www.oddsportal.com/esports/league-of-legends/> |
| 24 | Flashscore LoL | odds aggregator | `200` | 765224 | 1 | 0 | Worlds 2026 Main Event | — | <https://www.flashscore.com/esports/league-of-legends/> |
| 25 | Sofascore esports API | odds aggregator | `403` | 48 | 0 | 0 | — | — | <https://www.sofascore.com/api/v1/sport/esports/scheduled-events/2026-10-23> |
| 26 | bo3.gg LoL | odds aggregator | `200` | 13188 | 0 | 0 | — | — | <https://bo3.gg/lol/matches> |
| 27 | Escorenews LoL | esports news + odds | `403` | 5804 | 0 | 0 | — | — | <https://escorenews.com/en/lol> |
| 28 | BetExplorer LoL | odds aggregator | `404` | 0 | 0 | 0 | — | — | <https://www.betexplorer.com/esports/league-of-legends/> |
| 29 | DraftKings LoL (public content API) | US sportsbook | `403` | 449 | 0 | 0 | — | — | <https://sportsbook-nash.draftkings.com/api/sportscontent/dkusoh/v1/leagues/19873> |
| 30 | FanDuel LoL (page API) | US sportsbook | `400` | 14 | 0 | 0 | — | — | <https://sbapi.nj.sportsbook.fanduel.com/api/content-managed-page?page=CUSTOM&customPageId=lol> |
| 31 | BetOnline esports lines | US sportsbook | `200` | 366111 | 1 | 0 | — | — | <https://www.betonline.ag/sportsbook/api/lines/esports> |
| 32 | Betano LoL JSON API | established book | `200` | 29842 | 0 | 0 | — | — | <https://www.betano.com/api/sport/esports/league-of-legends/> |
| 33 | The Odds API LoL (key required) | odds API | `401` | 152 | 0 | 0 | — | — | <https://api.the-odds-api.com/v4/sports/esports_league_of_legends/odds?regions=eu&markets=h2h> |
| 34 | OddsPapi LoL (key required) | odds API | `401` | 158 | 0 | 0 | — | — | <https://api.oddspapi.io/v4/fixtures?sportId=18> |
| 35 | Kambi leovegas LoL | established book (Kambi) | `400` | 91 | 0 | 0 | — | — | <https://eu-offering-api.kambicdn.com/offering/v2018/leovegas/listView/esports/league_of_legends/all/all/matches.json?lang=en_GB&market=ZZ> |
| 36 | Kambi nordicbet LoL | established book (Kambi) | `429` | 9 | 0 | 0 | — | — | <https://eu-offering-api.kambicdn.com/offering/v2018/nordicbet/listView/esports/league_of_legends/all/all/matches.json?lang=en_GB&market=ZZ> |
| 37 | Kambi coolbet LoL | established book (Kambi) | `200` | 633 | 0 | 0 | — | — | <https://eu-offering-api.kambicdn.com/offering/v2018/coolbet/listView/esports/league_of_legends/all/all/matches.json?lang=en_GB&market=ZZ> |
| 38 | Kambi 888sport LoL | established book (Kambi) | `400` | 91 | 0 | 0 | — | — | <https://eu-offering-api.kambicdn.com/offering/v2018/888sport/listView/esports/league_of_legends/all/all/matches.json?lang=en_GB&market=ZZ> |
| 39 | Kambi paf LoL | established book (Kambi) | `200` | 14115 | 13 | 8 | Worlds 2026 Main Event | — | <https://eu-offering-api.kambicdn.com/offering/v2018/paf/listView/esports/league_of_legends/all/all/matches.json?lang=en_GB&market=ZZ> |
| 40 | bo3.gg LoL today | odds aggregator | `200` | 13188 | 0 | 0 | — | — | <https://bo3.gg/lol/matches/current> |
| 41 | bo3.gg Worlds 2026 tournament | odds aggregator | `200` | 13188 | 0 | 0 | — | — | <https://bo3.gg/lol/tournaments/worlds-2026> |
| 42 | odds-api.io sports list | odds API | `200` | 1351 | 0 | 0 | — | — | <https://api.odds-api.io/v3/sports> |
| 43 | odds-api.io esports events (key required) | odds API | `401` | 46 | 0 | 0 | — | — | <https://api.odds-api.io/v3/events?sport=esports> |
| 44 | PandaScore LoL (token required) | esports data API | `403` | 28 | 0 | 0 | — | — | <https://api.pandascore.co/lol/matches?per_page=1> |
| 45 | Abios series (key required) | esports data API | `None` | 0 | 0 | 0 | — | — | <https://api.abiosgaming.com/v2/series> |
| 46 | Riot LoL Esports schedule | official | `403` | 23 | 0 | 0 | — | — | <https://esports-api.lolesports.com/persisted/gw/getSchedule?hl=en-US> |
| 47 | Leaguepedia Cargo | results database | `200` | 1213 | 0 | 0 | — | — | <https://lol.fandom.com/wiki/Special:CargoExport?tables=MatchSchedule&fields=OverviewPage,Team1,Team2,Winner,DateTime_UTC&limit=5&format=json> |
| 48 | Liquipedia LoL matches | results database | `403` | 2059 | 0 | 0 | — | — | <https://liquipedia.net/leagueoflegends/Portal:Matches> |

Status histogram: 200×20, 202×1, 203×1, 400×3, 401×4, 403×11, 404×2, 410×1, 429×1, 503×1, 530×1, no response×2.

### 5a. Venues that answered but expose no machine-readable LoL price

| Venue | HTTP | Bytes | Why it is not a usable line |
| --- | --- | --- | --- |
| Pinnacle league list | `200` | 6141 | does Pinnacle list tier-2 leagues at all? |
| Bovada LoL coupon | `200` | 2 | control: US esportsbook moneylines |
| BC.GAME sports | `200` | 11871 | low-tier LoL markets |
| Thunderpick LoL | `200` | 14971 | low-tier LoL markets |
| Rivalry esports | `200` | 61219 | low-tier LoL markets |
| Betano LoL | `200` | 29842 | EU book |
| OddsPortal LoL | `200` | 335280 | multi-book comparison |
| Flashscore LoL | `200` | 765224 | multi-book comparison |
| bo3.gg LoL | `200` | 13188 | match list with odds |
| BetOnline esports lines | `200` | 366111 | JSON lines feed |
| Betano LoL JSON API | `200` | 29842 | JSON coupon behind the HTML page |
| Kambi coolbet LoL | `200` | 633 | brand-level LoL coupon, incl. tier-2? |
| bo3.gg LoL today | `200` | 13188 | which tiers carry a price on today's board |
| bo3.gg Worlds 2026 tournament | `200` | 13188 | does the tournament page price the same ties |
| odds-api.io sports list | `200` | 1351 | public sports list - does it carry esports at all? |
| Leaguepedia Cargo | `200` | 1213 | control: series results used by the model |

### 5b. Venues that block the runner or require a key

| Venue | HTTP | Consequence |
| --- | --- | --- |
| GG.BET LoL | `403` | no price retrievable from the build runner |
| Thunderpick API | `None` | no price retrievable from the build runner |
| Rivalry API | `530` | no price retrievable from the build runner |
| Stake esports | `403` | no price retrievable from the build runner |
| Betboom LoL | `401` | no price retrievable from the build runner |
| Marathonbet LoL | `403` | no price retrievable from the build runner |
| Betway esports | `404` | no price retrievable from the build runner |
| Unibet LoL | `503` | no price retrievable from the build runner |
| EGamersWorld LoL | `403` | no price retrievable from the build runner |
| EGamersWorld match page | `403` | no price retrievable from the build runner |
| Oddspedia LoL | `410` | no price retrievable from the build runner |
| Sofascore esports API | `403` | no price retrievable from the build runner |
| Escorenews LoL | `403` | no price retrievable from the build runner |
| BetExplorer LoL | `404` | no price retrievable from the build runner |
| DraftKings LoL (public content API) | `403` | no price retrievable from the build runner |
| FanDuel LoL (page API) | `400` | no price retrievable from the build runner |
| The Odds API LoL (key required) | `401` | no price retrievable from the build runner |
| OddsPapi LoL (key required) | `401` | no price retrievable from the build runner |
| Kambi leovegas LoL | `400` | no price retrievable from the build runner |
| Kambi nordicbet LoL | `429` | no price retrievable from the build runner |
| Kambi 888sport LoL | `400` | no price retrievable from the build runner |
| odds-api.io esports events (key required) | `401` | no price retrievable from the build runner |
| PandaScore LoL (token required) | `403` | no price retrievable from the build runner |
| Abios series (key required) | `None` | no price retrievable from the build runner |
| Riot LoL Esports schedule | `403` | no price retrievable from the build runner |
| Liquipedia LoL matches | `403` | no price retrievable from the build runner |

Key-gated APIs are recorded as key-gated, never as "no market exists". Configuring a key for any of `the-odds-api.com`, `oddspapi.io`, `odds-api.io` or `api.pandascore.co` would be the cheapest way to widen coverage beyond this ceiling; none is configured for this repository, so none can be claimed.

## 6. What today's published dataset does with that ceiling

| Metric | Value | Field |
| --- | --- | --- |
| Cards on the Hotspawn LoL list | **234** | fixtures API, `2026-10-25T14:13:21Z` |
| Cards carrying a pick | **234 / 234** | `pick.team` |
| Cards carrying a win probability | **230** | `p0`/`p1` |
| Priced from real bookmaker / exchange lines | **9** | `method: market` |
| — of which | Worlds 2026 Main Event 8; LGC Rising 2026 Playoffs 1 | `competition` |
| Originated from recorded series results | **221** (150 model + 71 provisional) | `method` |
| Resolved by league rule, no probability claimed | **4** | `method: unresolved` |
| Competitions with any external price | **2 of 29** | market rows above |
| Graded picks against official results so far | **39** (23 hits, 58.97% accuracy) | `track_record` |

## 7. What would overturn this

This memo claims *"no reachable venue priced the tier-2 tail at 2026-10-25T14:38:07Z"* — not *"nobody prices tier-2 LoL"*. Any of the following would overturn it, and each is re-tested automatically:

1. a venue response containing both opponents of a non-Worlds fixture (the `Both sides` column is computed on every run);
2. Pinnacle's league list, or its matchup enumeration, gaining a second League of Legends league;
3. an odds API key being configured (currently 401 for four documented APIs);
4. a Kambi brand opening a national league — five operators were called and only `paf` returned a coupon, which is the same Worlds board the pipeline already reads.

## 8. Limitations, including the ones this session found by being wrong

- **Three earlier captures of this same session produced false positives, and this memo does not hide them.** First, a substring test matched the code `LIT` inside "spl**it**" and `POP` inside "**pop**ular" (20 venues wrongly flagged). Second, a case-insensitive word test matched JavaScript `s.pop()` and `lcp:{...}`. Third, searching all 184 team names matched ordinary words — `DELETED` in CSS, `Arena` in page furniture, `Venus` in a bundle. The final rules are: word-bounded matching, competition codes only in their published upper case, and a fixture counts only when **both** opponents appear. `tests/test_probe_competitions.py` pins each of the three fixes.
- **Snapshot, not a standing fact.** A book that opens a market after 2026-10-25T14:38:07Z is not reflected here. The probe re-runs whenever `tools/probe_sources.py` changes and can be re-run on demand; each run is committed with its runner id, commit and timestamp.
- **Marketing pages are not evidence.** Affiliate reviews claim tier-2 coverage for several books. A page counts only if it returns a parseable price naming a listed fixture; Thunderpick's page, for example, returned 14971 bytes containing none of the 184 team names searched.
- **Leaguepedia is community-maintained.** It is the source of the results behind the originated lines and of the forfeit records behind the four settlement picks. It is not an official Riot feed, and every row links to the page it used.
- **Four cards carry no probability by design.** They are Komplettligaen fixtures involving `Solid Gaming`, recorded by Leaguepedia as removed mid-split. They keep an administrative settlement pick and no percentage: a probability for a series that may be voided or awarded as a walkover would be fiction. They are published on the Unresolved page and inside the executive summary.
- **The originated lines are estimates.** They are Elo probabilities over recorded series results, backtested out-of-sample in `data/matches.json:backtest`, and labelled `model` or `provisional` on every row. They are not bookmaker prices and the site never presents them as such.

## 9. Links for manual review

| What | Where |
| --- | --- |
| Raw receipt for this capture | [`data/probe/sources_probe.json`](../../data/probe/sources_probe.json) |
| Probe code | [`tools/probe_sources.py`](../../tools/probe_sources.py) |
| Pinnacle open esports league list | <https://guest.api.arcadia.pinnacle.com/0.1/sports/12/leagues> |
| Pinnacle LoL matchups | <https://guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups> |
| Hotspawn pick'em list | <https://play.hotspawn.com/lol-pickems> |
| Hotspawn fixtures API (inventory) | <https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=lol&status=scheduled&tenantId=1> |
| Kalshi LoL series | <https://api.elections.kalshi.com/trade-api/v2/events?series_ticker=KXLOLGAME&status=open&with_nested_markets=true> |
| Polymarket LoL tag | <https://gamma-api.polymarket.com/events?closed=false&tag_slug=league-of-legends> |
| Bovada LoL coupon (page) | <https://www.bovada.lv/sports/esports/league-of-legends> |
| Kambi LoL coupon (`paf` brand) | <https://eu-offering-api.kambicdn.com/offering/v2018/paf/listView/esports/league_of_legends/all/all/matches.json?lang=en_GB&market=ZZ> |
| Leaguepedia Cargo endpoint used by the model | <https://lol.fandom.com/wiki/Special:CargoExport> |
| Published site | <https://karagemop466-tech.github.io/LOLHOTSPAWN1/> |

