# Session `be974159` — Primary-Source Verification & Low-Tier External-Line Research (2026-10-25)

## 1. Scope & Research Question

Per user instructions:
1. Never use Hotspawn community pick percentages as a probability input.
2. Originate probabilities from established LoL sportsbooks, esportsbooks, and CFTC/CLOB prediction markets first; for matches below the commercial bookmaker ceiling, investigate external information sources and originate strictly pre-kickoff ratings from verified match history.
3. Audit every published row, alias, settlement, and irregularity against official/primary sources; never guess or fill unverified values, and publish all irregularities on `flagged.html` with source links.

Capture window: **2026-10-25T14:10Z–14:25Z**.

---

## 2. Live Multi-Book & Exchange Verification Across All 29 Hotspawn Competitions

| Source / Feed | URL Checked (`2026-10-25`) | Competitions Priced | Key Verbatim / Quantitative Findings |
|---|---|---|---|
| **Kalshi CFTC Exchange API** | <https://api.elections.kalshi.com/trade-api/v2/events?series_ticker=KXLOLGAME&status=open&with_nested_markets=true&limit=100> | `Worlds 2026 Main Event` (8), `LGC Rising 2026 Playoffs` (1) | `KXLOLGAME-26OCT271300RBMR` (`Rising Bees vs. Mental Rush (Oct 27)`): `Rising Bees` `$0.63/$0.66` (`$221` vol), `Mental Rush` `$0.36/$0.40` (`$43` vol). Previously missed by `tools/model.py` because Kalshi drops `"Vitality"` from `"Vitality Rising Bees"`; now joined into `#1079080` 2-venue consensus. |
| **Unibet / Kambi JSON API** | <https://eu-offering-api.kambicdn.com/offering/v2018/ubse/listView/esports/league_of_legends/all/all/matches.json?lang=en_GB&market=ZZ> | `Worlds 2026 Main Event` (8) | All 8 Swiss Round 3 series live (`TOP Esports - G2 Esports`, `Hanwha Life Esports - Invictus Gaming`, `Gen.G Esports - Lyon Gaming`, `Dplus KIA - Movistar KOI`, `T1 - CTBC Flying Oyster`, `Karmine Corp - Bilibili Gaming`, `LØS - Team Secret Whales`, `Team Liquid - Anyone's Legend`); 0 lower-tier LoL leagues. |
| **Polymarket Gamma API** | <https://gamma-api.polymarket.com/events?slug=lol-rb-mr-2026-10-27> | `Worlds 2026 Main Event` (8), `LGC Rising 2026 Playoffs` (1) | `LoL: Vitality Rising Bees vs Mental Rush (BO5) - LGC Rising Playoffs`, `$58.47` traded volume, `$1,496.28` CLOB liquidity, `gameStartTime: 2026-10-27 16:00:00+00` (1.0 h earlier than Hotspawn & Kalshi `17:00Z`). |
| **BMBETS (60-Bookmaker Index)** | <https://www.bmbets.com/e-sports/world/lol---lcp/ground-zero-gaming-(lol)-v-frank-esports-(lol)-9910334/> | `Worlds 2026` (9), `LGC Rising` (1), `LCP 2027 Promotion` (1) | **New 4-bookmaker finding on `#1081423` (`Ground Zero Gaming vs Frank Esports`, `2026-11-11 09:00Z`)**: **bet365** (`1.03 / 9.10`), **TotoGaming** (`1.03 / 10.50`), **1xBet** (`1.02 / 10.50`), and **BetOlimp** (`1.02 / 9.80`) all price Tier-1 LCP incumbent `Ground Zero Gaming` at `~90.6%–91.2%`. Dedicated `LoL - Prime League 2nd Division` index (<https://www.bmbets.com/e-sports/world/lol---prime-league-2nd-division/>) returned `"Data not available"` (0 events across 60 books). |
| **EsportsInsider (PandaScore US Feed)** | <https://esportsinsider.com/betting-odds/lol> | `Worlds 2026` (8), `LCP 2027 Promotion` (1) | Quotes `#1081421` (`FENNEL vs Nothin'Here`, `Nov 10, 2026, 5:00 AM UTC`) at **`FENNEL 62% / Nothin'Here 38%`**, corroborating our `FENNEL 67.7%` line after fixing `tier_prior()` (`"wildcard"` excluded from Tier-1 `1700` prior). Zero national/academy/MENA/Nordic/CELOL leagues listed. |
| **EGamersWorld (5-Book Aggregator)** | <https://egamersworld.com/lol/bets> | `Worlds 2026` (8), `LGC Rising` (1) | Quotes `#1079080` across Vave (`1.40/2.73`), Thunderpick (`1.43/2.57`), and Rainbet (`1.44/2.55`); zero ERL 2nd/3rd division, Arabian, Tunisian, Nordic, or CELOL markets. |

**Conclusion across 60+ sportsbooks & exchanges:** Outside `Worlds 2026 Main Event` (8 matches, 5/5 automated live venues), `LGC Rising 2026 Playoffs` (`#1079080`, 2 automated live venues: Polymarket + CFTC Kalshi, corroborated by Thunderpick/Vave/Rainbet/BMBETS), and `LCP 2027 Promotion` (`#1081421` corroborated by EsportsInsider `62%/38%`; `#1081423` quoted on bet365/1xBet/TotoGaming/BetOlimp via reCAPTCHA-gated BMBETS and flagged on `flagged.html` + `coverage.html`), **none of the remaining 26 regional, academy, MENA, Nordic, Benelux, Bulgarian, or Brazilian Série A/B competitions have open commercial betting markets anywhere**.

---

## 3. Primary-Source Wiki & Roster Verifications (`?action=raw`)

1. **`Data:LCP/2027_Season/Promotion` & Liquipedia `LCP/2027/Promotion`**:
   - URLs: <https://lol.fandom.com/wiki/Data:LCP/2027_Season/Promotion?action=raw>, <https://liquipedia.net/leagueoflegends/LCP/2027/Promotion>
   - Confirms all stages are `bestof=5` (whereas Hotspawn's API returns `best_of: null`).
   - Confirms `#1081421` (`2026-11-10 05:00Z`) pits LJL Summer champion `FENNEL` against Thai LCP Wildcard qualifier `Nothin'Here` (`first_page = LCP Wildcard/2026 Season/Regional Qualifiers/Thailand`).
   - Confirms `#1081423` (`2026-11-11 09:00Z`) pits Tier-1 LCP Regional Merit incumbent `Ground Zero Gaming` (`1Jiang / Husha / Uniboy / Betty / Kaiwing`) against Tier-2 PCS challenger `Frank Esports`.
2. **`Data:Arabian_League_2nd_Division/2026_Season/Summer_Split`**:
   - URL: <https://lol.fandom.com/wiki/Data:Arabian_League_2nd_Division/2026_Season/Summer_Split?action=raw>
   - Verifies the exact primary source for `Team Reds`'s Week 1 administrative forfeits (ineligible roster): `2026-10-02` `JSK Academy vs Team Reds` (`2-1` -> `2-0`, `ff=2`) and `2026-10-03` `Team Reds vs New Era Team` (`2-0` win overturned to `0-2`, `ff=1`). Corrected the stale `data/flags_manual.json` note that had cited `4 Nations 2026 Halloween Heist`.
3. **`Data:Logitech_G_SuperStrike_Cup/Qualifier`**:
   - URL: <https://lol.fandom.com/wiki/Data:Logitech_G_SuperStrike_Cup/Qualifier?action=raw>
   - Confirms Bulgarian amateur team `PNG` (`0-1` vs `Non-toxic Gaming` on `#1083097`, `0-1` vs `Cruel Fate`), quarantined via `competition_aliases` in `data/aliases.json` so Hotspawn's `'paiN Gaming'` label never inherits Brazilian Tier-1 CBLOL `paiN Gaming` Elo.
4. **`Data:Prime_League_2nd_Division/2027_Season/Fall_Split`**:
   - URL: <https://lol.fandom.com/wiki/Data:Prime_League_2nd_Division/2027_Season/Fall_Split?action=raw>
   - Re-verifies `'Phong Vũ Buffalo' -> 'PvB (Swiss Team)'` (`PvB Nation` in Division 2.1).
