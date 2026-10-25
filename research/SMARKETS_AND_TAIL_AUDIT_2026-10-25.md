# Smarkets UKGC Exchange Integration & Line-by-Line Tail Audit (2026-10-25 · Session `154d8c26`)

## 1. New Regulated Real-Money Venue: Smarkets Exchange (`api.smarkets.com/v3/`)

While prior venue probes surveyed Kambi operators, Cloudbet, Thunderpick, GG.BET, OddsPortal, and Betmonitor, **Smarkets** (UK Gambling Commission License `#039826-R-319372`, MGA licensed) exposes an unauthenticated public REST v3 JSON API that works cleanly without API keys or Cloudflare challenges:

1. **Event discovery:** `https://api.smarkets.com/v3/events/?state=new&state=upcoming&type=league_of_legends_match&limit=50`
2. **Series-winner market selection:** `https://api.smarkets.com/v3/events/<csv_ids>/markets/` filtered strictly to `market_type.name == "WINNER_2_WAY"`, `state == "open"`, `hidden == false` (excluding `WINNER_MAP`, `HANDICAP`, `OVER_UNDER`).
3. **Contract & orderbook quotes:** `https://api.smarkets.com/v3/markets/<csv_mids>/contracts/` and `/quotes/`, where prices are basis points of implied probability (`10000 == 100%`). Mid-quotes `(best_bid + best_offer) / 20000` are accepted only when two-sided liquidity is present and `spread <= 0.25`.

### Live Smarkets Captures (`2026-10-25T14:25:00Z`, all pre-kickoff)

| Smarkets Event | Match | Kickoff (UTC) | Bid / Offer (A bps) | Bid / Offer (B bps) | De-vigged Implied | Public Event Receipt |
|---|---|---|---|---|---|---|
| `45400319` (`173458049`) | Top Esports vs G2 Esports | `2026-10-25T18:00Z` | `4167 / 5208` | `4762 / 5814` | **46.99% / 53.01%** | <https://smarkets.com/sport/esports/league-of-legends/worlds/group-stage/2026/10/25/18-00/top-esports-vs-g2-esports> |
| `45400320` (`173455842`) | Hanwha Life Esports vs Invictus Gaming | `2026-10-25T17:00Z` | `6944 / 7752` | `2083 / 3125` | **73.83% / 26.17%** | <https://smarkets.com/sport/esports/league-of-legends/worlds/group-stage/2026/10/25/17-00/hanwha-life-esports-vs-invictus-gaming> |
| `45400321` (`173455130`) | Gen.G vs LYON | `2026-10-25T22:00Z` | `8547 / 9804` | `769 / 1429` | **89.30% / 10.70%** | <https://smarkets.com/sport/esports/league-of-legends/worlds/group-stage/2026/10/25/22-00/gen-g-vs-lyon> |
| `45400322` (`173455158`) | Dplus KIA vs Movistar KOI | `2026-10-25T19:00Z` | `7143 / 8197` | `1818 / 2857` | **76.64% / 23.36%** | <https://smarkets.com/sport/esports/league-of-legends/worlds/group-stage/2026/10/25/19-00/dplus-kia-vs-movistar-koi> |
| `45400323` (`173455372`) | Karmine Corp vs Bilibili Gaming | `2026-10-26T18:00Z` | `2174 / 3817` | `6173 / 7812` | **29.99% / 70.01%** | <https://smarkets.com/sport/esports/league-of-legends/worlds/group-stage/2026/10/26/18-00/karmine-corp-vs-bilibili-gaming> |
| `45400324` (`173455583`) | T1 vs CTBC Flying Oyster | `2026-10-26T17:00Z` | `7692 / 9434` | `645 / 2273` | **85.44% / 14.56%** | <https://smarkets.com/sport/esports/league-of-legends/worlds/group-stage/2026/10/26/17-00/t1-vs-ctbc-flying-oyster> |
| `45400325` (`173456019`) | Team Liquid vs Anyone's Legend | `2026-10-26T22:00Z` | `2326 / 4000` | `6024 / 7634` | **31.66% / 68.34%** | <https://smarkets.com/sport/esports/league-of-legends/worlds/group-stage/2026/10/26/22-00/team-liquid-vs-anyone-s-legend> |
| `45400326` (`173457304`) | LOS vs Team Secret Whales | `2026-10-26T19:00Z` | `2817 / 4464` | `5556 / 7194` | **36.35% / 63.65%** | <https://smarkets.com/sport/esports/league-of-legends/worlds/group-stage/2026/10/26/19-00/los-vs-team-secret-whales> |

## 2. Line-by-Line Model & Source-Integrity Fixes Discovered

1. **Dropped CFTC Kalshi line on `#1079080` (`Mental Rush vs Vitality Rising Bees`, LGC Rising 2026 Playoffs):**
   - `data/raw/kalshi_lol.json` contains active CFTC contract `KXLOLGAME-26OCT271300RBMR` (`Rising Bees vs. Mental Rush (Oct 27)`). Adding `"rising bees": "vitality rising bees"` to `BOOK_TEAM_ALIASES` upgrades `#1079080` in the canonical pipeline from a thin single-venue Polymarket quote (`$5` volume, `confidence=low`) to a 2-venue real-money consensus (`Polymarket` + `Kalshi CFTC`, de-vigged `37.07% / 62.93%` on Kalshi).
2. **`tier_prior()` false-positive `1700.0` Tier-1 seeding on Wildcard / Open Qualifiers (`#1081421` `FENNEL vs Nothin'Here`):**
   - Verified against Leaguepedia (<https://lol.fandom.com/wiki/LCP/2027_Season/Promotion>) and Liquipedia (<https://liquipedia.net/leagueoflegends/LCP/2027/Promotion>): `FENNEL` qualified as the LJL 2026 Summer Champion (`71.2%` WR over 59 games), whereas `Nothin'Here` qualified via the `$5,000` online `LCP Wild Card Playoffs` (`LCP Wildcard/2026 Season/Regional Qualifiers/Thailand`).
   - `tools/model.py` `tier_prior()` matched `"lcp"` before checking `"wildcard"` / `"opq"` / `"qualifier"` / `"showmatch"`, mistakenly assigning `1700.0` (Worlds/LCK/LPL franchise prior!) to `LCP Wildcard/...`, `LCP OPQ/...`, `LEC VIP Türkiye Qualifier`, and `Esports World Cup 2026/Online Qualifiers/...`. Excluding qualifier/wildcard/showmatch pages restores regional `1475.0` priors and aligns `#1081421` with the independent Node companion model (`FENNEL` favored).
3. **`#1082002` (`DELETED vs S7raa`, Arabian Regional Championship 2026: LB-Li-SY-PS):**
   - Verified against official raw wikitext (<https://lol.fandom.com/wiki/Arabian_Regional_Championship_2026/Qualifiers/LB-Li-SY-PS?action=raw>): `DELETED` has no roster block in `== Participants ==` and appears only in `TournamentResults` (`place=NQ|team=DELETED|lastresult=0 : 1|lastopponent=S7raa`), representing a withdrawn/deleted GBArena open-qualifier entry that Hotspawn still lists as `scheduled`.
4. **Midnite HTTP 200 Soft-404 (`https://www.midnite.com/esports/league-of-legends`):**
   - Previously marked `ok: true, blocked_note: "reachable"` in `data/sources_status.json` because the SPA shell answered HTTP `200`, even though the rendered page says `"Ooooooops! We can’t find the page you’re looking for."`. Fixed via `_is_soft_404()` in `tools/collect.py`.
5. **Secondary `/docs/` Parity Gate (`audit/verify_docs_parity.py`, Request `R1`):**
   - Fixed by persisting `docs/data/canonical_snapshot.json` in `scripts/build_site.mjs` and verifying `docs/` against the canonical snapshot it was built from (plus rebuilding `docs/` directly inside `.github/workflows/refresh.yml`).

Cross-references: `research/LINE_SEARCH_2026-10-25.md`, `research/external-lines-2026-10-25.md`, `data/receipts/external_odds/2026-10-25-session-154d8c26.json`.
