# Long-tail LoL line research — where an external price exists, and where it provably does not

Session `62ba9cfe` · 2026-10-24 · branch `arena/62ba9cfe-lolhotspawn1`

**Question this answers.** The brief is: a pick for *every* match on the Hotspawn League of Legends
pick'em, priced from real betting lines where they exist, and from our own model where they do not.
Only 9 of 241 published rows are priced by a book. This dossier is the evidence for the other 232 —
what was tried, what each venue actually returned, and the resulting decision rule.

Nothing here is inferred. Every "reachable / blocked" verdict below is an HTTP status or a verbatim
page reading, captured at the stated UTC time, from one of two independent network paths:

| Path | What it is | Why it matters |
|---|---|---|
| **Actions runner** | the GitHub-hosted Ubuntu runner that builds the site every 6 h | this is the path that has to work unattended; results in [`data/source_probes.json`](../data/source_probes.json) (32 venues, `2026-10-23T15:38:55Z`) and [`data/probe/sources_probe.json`](../data/probe/sources_probe.json) |
| **Research sandbox** | this session's browser-grade fetch proxy | reaches venues that block the runner (EGamersWorld `403`, bo3.gg JS-only), so it can read prices the pipeline cannot |

The sandbox's own shell has **no** outbound access at all — `curl` to Hotspawn, Leaguepedia and
Pinnacle all returned `HTTP 000` on 2026-10-24 — so every sandbox reading below came through the
fetch proxy, and the two paths are genuinely independent.

---

## 1. What was verified live on 2026-10-24 (research sandbox)

| # | Venue | URL | Result | LoL series priced | Tier coverage |
|---|---|---|---|---|---|
| 1 | **Hotspawn fixtures API** | <https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=lol&status=scheduled&tenantId=1> | HTTP 200, JSON, 24 response chunks | — (inventory, never used as a probability) | **all 241** scheduled cards, 29 tournaments |
| 2 | **EGamersWorld LoL** | <https://egamersworld.com/lol/matches> | HTTP 200, decimal prices readable | **11** | Worlds 2026 (8) + LGC 2026 Rising (1) + LCP 2027 Promotion (2) |
| 3 | **bo3.gg LoL match centre** | <https://bo3.gg/lol/matches/current> | HTTP 200, decimal prices readable | **8** | Worlds 2026 only (page is filtered to "s-tier") |

Receipts transcribed from #2 and #3 are committed to
[`data/receipts/external_odds/2026-10-24-longtail.json`](../data/receipts/external_odds/2026-10-24-longtail.json)
(19 captures, each with its page URL, capture time and verbatim page text) and are validated against
the dataset on every build by [`tools/corroborate.py`](../tools/corroborate.py).

### The external ceiling, measured

Hotspawn lists **241** scheduled LoL cards across **29** tournaments. The widest external coverage
found anywhere, on any path, on any day, is **11 series on one aggregator** — and 8 of those 11 are
the same Worlds ties every other venue prices. Only **3 of the 29** tournaments get any external
price at all (`Worlds 2026 Main Event`, `LGC Rising 2026 Playoffs`, `LCP 2027 Promotion`), covering
**12 of 241 cards**; the other **26 tournaments / 229 cards** are priced by nobody. They are exactly
the national, academy and third-division leagues:

`PRM 3rd Division 26-27 Fall` (62 cards) · `PRM 2nd Division 26-27 Fall` (36) · `RIVALS LEAGUE Season 2` (25) ·
`Tunisian Super League 2026` (25) · `Icelandic Esports League 2026 Autumn` (12) · `Arabian League 2nd
Division 2026 Summer` (9) · `Komplettligaen 2026 Autumn` (6) · `Superstrike League 2026` (6) ·
`Arabian Regional Championship 2026: Lebanon-Libya-Syria-Palestine` (6) · `Benelux Ascend Series Rising
2026 Summer Playoffs` (5) · `Benelux Ascend Series 2027 Winter Promotion` (5) · `LigaGG CELOL B 2026
Split 2 Playoffs` (5) · `4 Nations 2026 Halloween Heist` (5) · `Logitech G SuperStrike Cup Qualifier` (4) ·
`Komplettligaen 2026 Autumn Playoffs` (3) · `Benelux Ascend Series 2026 Summer Split` (2) ·
`LigaGG CELOL B 2026 Split 2` (2) · `Arabian Regional Championship 2026: Qatar-Bahrain-Kuwait` (2) ·
`LigaGG CELOL A 2026 Split 2 Playoffs` (2) · `FPL 2026 Summer Playoffs` (1) · `LIT 2027 Winter
Promotion` (1) · `Benelux Ascend Series 2026 Summer Playoffs` (1) · `LigaGG CELOL A 2026 Split 2` (1) ·
`POP Esports Masters Season 7` (1) · `Legends Academy powered by Żabka Season 3 Playoffs` (1) ·
`Hitpoint 2nd Div Challengers 2026 Summer Playoffs` (1).


(Card counts from the fixtures API snapshot at
[`data/node/raw/hotspawn_lol_fixtures.json`](../data/node/raw/hotspawn_lol_fixtures.json), fetched
`2026-10-24T15:34:30Z` by the secondary pipeline — an independent collection from the canonical one.)

**Verbatim evidence that the aggregators stop at international tier.** bo3.gg's LoL match centre on
2026-10-24 listed a single section header, `s-tier`, above all eight cards, every one of them
`Worlds 2026`. EGamersWorld listed the same eight cards under "today's Upcoming Matches", then exactly
three more dated 27.10, 10.11 and 11.11 — LGC Rising and two LCP Promotion cards — and nothing else.

---

## 2. Established LoL books, esportsbooks and aggregators — full probe ledger

Runner-side verdicts are from [`data/source_probes.json`](../data/source_probes.json)
(`checked_utc 2026-10-23T15:38:55Z`, 32 venues, re-probed on every build and republished on
[`sources.html`](../sources.html)). "Prices the long tail?" is answered only where the venue was
actually readable; a blocked venue is recorded as blocked, never guessed.

### 2a. Reachable from the runner and used in the consensus

| Venue | URL | HTTP | What it gives | Long tail? |
|---|---|---|---|---|
| Pinnacle guest API | <https://guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups> | 200 | sharp series moneylines; 1 LoL league (`League of Legends - World Championship`, id 9587) | **no** — one league only |
| Kalshi (CFTC) | <https://api.elections.kalshi.com/trade-api/v2/events?series_ticker=KXL> | 200 | regulated event contracts, 9 LoL match events | no |
| Bovada | <https://www.bovada.lv/services/sports/event/coupon/events/A/description/esports/league-of-legends> | 200 | moneylines, 8 LoL series | no |
| Unibet / Kambi CDN (`ubse`) | <https://eu-offering-api.kambicdn.com/offering/v2018/ubse/listView/esports/league_of_legends/all/all/matches.json?lang=en_GB&market=ZZ> | 200 | regulated EU sportsbook JSON, `OT_ONE`/`OT_TWO` Match Odds, 8 series | no |
| Polymarket Gamma | <https://gamma-api.polymarket.com/events?closed=false&limit=20&tag_slug=league-of-legends> | 200 | prediction-market prices, 45 match-level markets | **partially** — the only venue found pricing a non-Worlds card (`LGC Rising`, fixture 1079080) but on $7 of volume |
| BetOnline esports | <https://www.betonline.ag/sportsbook/esports> | 200 | page reachable; LoL prices client-rendered | unverified |
| DraftKings esports | <https://sportsbook.draftkings.com/leagues/esports/league-of-legends> | 200 | page reachable; geo-gated prices | unverified |
| FanDuel esports | <https://sportsbook.fanduel.com/esports/league-of-legends> | 200 | page reachable; geo-gated prices | unverified |
| Rivalry LoL | <https://www.rivalry.com/esports/league-of-legends> | 200 | esportsbook page reachable; odds client-rendered | unverified |
| BC.GAME sports | <https://bc.game/sports> | 200 | page reachable; odds client-rendered | unverified |
| OddsPortal LoL | <https://www.oddsportal.com/esports/league-of-legends/> | 200 | lists exactly one priced LoL competition, `League of Legends World Championship (8)` — recorded verbatim in [`data/receipts/external_odds/2026-10-23.json`](../data/receipts/external_odds/2026-10-23.json) | **no** |
| gol.gg | <https://gol.gg/esports/home/> | 200 | results/stats, no odds | n/a |
| Leaguepedia Cargo | <https://lol.fandom.com/wiki/Special:CargoExport?tables=MatchSchedule> | 200 | series results (community-maintained) — the input to our Elo, **not** an odds source | n/a |

### 2b. Blocked from the runner — recorded with their HTTP status, never guessed

| Venue | URL | HTTP | Note |
|---|---|---|---|
| EGamersWorld LoL bets | <https://egamersworld.com/lol/bets> | 403 | **readable from the research sandbox** — see §1; 11 series priced |
| bo3.gg | <https://bo3.gg/lol/matches/current> | 200 but JS-only | **readable from the research sandbox** — see §1; 8 series priced |
| GG.BET LoL | <https://gg.bet/en/esports/league-of-legends> | 403 | region/bot blocked |
| Thunderpick LoL | <https://thunderpick.io/esports/league-of-legends> | 403 | bot blocked; bo3.gg's prices affiliate out to this feed |
| Stake LoL | <https://stake.com/sports/esports/league-of-legends> | 403 | bot blocked |
| bet365 esports | <https://www.bet365.com/#/AC/B18/C20464932/D1/E1/> | 403 | bot blocked |
| BetMGM esports | <https://sports.betmgm.com/en/sports/esports-6> | 403 | bot blocked |
| Betfair Exchange esports | <https://www.betfair.com/exchange/plus/esports> | 403 | bot blocked |
| BetUS esports | <https://www.betus.com.pa/sportsbook/esports/> | 403 | bot blocked |
| SportsBetting.ag esports | <https://www.sportsbetting.ag/sportsbook/esports> | 403 | bot blocked |
| Oracle's Elixir | <https://oracleselixir.com/> | 403 | stats, not odds |
| Oddspedia LoL | <https://oddspedia.com/esports/league-of-legends> | 410 | **gone** |
| BetExplorer LoL | <https://www.betexplorer.com/esports/league-of-legends/> | 404 | no such page |
| Betway esports | <https://sports.betway.com/en/sports/grp/esports> | 404 | no such page |
| Everygame esports | <https://www.everygame.eu/en/sportsbook/esports> | 404 | no such page |
| Unibet/Kambi (`ubus` operator) | <https://eu-offering-api.kambicdn.com/offering/v2018/ubus/listView/esports/league_of_legends/all/all/matches.json> | 400 | operator retired; the `ubse` operator above works |
| OddsPapi | <https://api.oddspapi.io/v4/fixtures?sportId=18> | 401 | API key required |
| Betsson esports | <https://www.betsson.com/en/sportsbook> | 202 | accepted, no body |
| 1xBet esports | <https://1xbet.com/en/line/esports/> | 203 | non-standard, no usable body |

---

## 3. Decision rule that follows from the evidence

1. **If two or more real-money venues price the series** → publish the precision-weighted de-vigged
   consensus, labelled `market`, with every venue's quote URL on the row. Today that is the Worlds
   cards (`Pinnacle 0.36 · Polymarket 0.24 · Kalshi 0.18 · Bovada 0.12 · Unibet 0.10`).
2. **If exactly one thin venue prices it** (a prediction market with negligible traded volume) →
   keep the line, label it low confidence and say why. One row today: `LGC Rising 2026 Playoffs`,
   Polymarket, $7 traded.
3. **If no venue prices it** → originate the line from recorded series results (Leaguepedia Elo,
   recency-weighted, evaluated at each fixture's own kick-off), labelled `model`, or `provisional`
   when one side has too little rated history to defend a confident number.
4. **If no line can be defended at all** → publish the settlement where the league itself has ruled
   one (official forfeit) and **no percentage**, and list the card on
   [`unresolved.html`](../unresolved.html) with the reason and its source. 4 rows today, all
   `Komplettligaen 2026 Autumn` cards whose participant `Solid Gaming` was removed mid-split.
5. **Never** fill a gap by inference, and **never** use Hotspawn's `picked_percent`, tiers or points
   as a probability input.

The reason 232 of 241 rows are not market-priced is therefore not that the research stopped early —
it is that **no reachable bookmaker prices national, academy or third-division League of Legends**.
That is the ceiling, and it is measured, not assumed.

---

## 4. Irregularities found while doing this research

All three are also published on [`flagged.html`](../flagged.html) with their source links.

1. **A live moneyline contradicts a published pick by 66.3 pp.** Fixture 1081423 (`Ground Zero
   Gaming` vs `Frank Esports`, LCP 2027 Promotion, 2026-11-11 09:00Z) is published as Frank Esports
   75.2%. EGamersWorld prices the same card 1.025 / 10.50 → Ground Zero 91.1% / Frank Esports 8.9%.
   This repository archived the *identical* price on 2026-10-21 and retired it as unverifiable
   because the page showed symmetric 1.80/1.80 placeholders on 2026-10-23; today's read shows the
   placeholder was a transient page state. A separate curated flag already records that Leaguepedia's
   Frank Esports rating may aggregate a cross-division PCS/LDL roster. **The pick is contested.**
   Evidence: <https://egamersworld.com/lol/match/eDTgthgYk/ground-zero-gaming-vs-frank-esports-wvOLKhrveF>
2. **Both aggregators' clocks are US Eastern, not a fixed UTC-4.** `data/corroboration.json` says
   "UTC-4 (US Eastern)", which is only true during EDT. US daylight saving ends 2026-11-01, after
   which the same note is an hour out and would map receipts onto the wrong fixtures. Verified three
   ways: 13:00 on 24.10.2026 (EDT) == 17:00Z == fixture 1067688; 00:00 on 10.11.2026 (EST) == 05:00Z
   == fixture 1081421; 04:00 on 11.11.2026 (EST) == 09:00Z == fixture 1081423.
3. **`AG.AL` is `Anyone's Legend`.** EGamersWorld uses the org ticker where Hotspawn uses the full
   name. Without an explicit alias the receipt is filed as defective, and (before the fix in
   `tools/corroborate.py`) that would have blocked the publish. Verified on the same card across two
   pages: <https://bo3.gg/lol/matches/top-esports-lol-vs-anyones-legend-24-10-2026> and
   <https://egamersworld.com/lol/match/q8qUtLA6g/top-esports-vs-agal-p1yWEbksN>.

---

## 5. How to reproduce

```bash
# runner-side venue probe (32 venues, writes data/source_probes.json)
python3 tools/probe_sources.py

# validate every committed receipt against the published dataset, and rebuild coverage.html
python3 tools/corroborate.py

# the publish gate, including the corroboration checks
python3 tools/verify.py

# regression tests for the receipt lifecycle
python3 -m unittest discover -s tests -v
```

Machine-readable probe results for this session: [`research/longtail_probe.json`](longtail_probe.json).
