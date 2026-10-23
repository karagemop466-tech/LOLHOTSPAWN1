# Independent verification — 2026-10-23 (session `6d1ede2c`)

Everything below was recomputed from the committed raw provider payloads and, where a
public endpoint is reachable, re-read live. No number on the site was taken on trust from
the build code.

Machine-readable receipts:

- `audit/receipts/live_spotcheck_2026-10-23T1558Z.json` — four live venue reads against the
  15:53Z snapshot.
- `audit/receipts/leaguepedia_ff_solid_gaming_2026-10-23.json` — the CargoExport forfeit query
  behind the four settlement cards.

Reproduce with:

```bash
python3 audit/verify_independent.py     # 0 failures, 10 warnings
python3 audit/check_site.py             # 20 pages, 0 failures
python3 tools/verify.py                 # 35 gates
```

## 1. Live re-read of the headline fixture (Gen.G v Invictus Gaming, Hotspawn `1067878`)

Snapshot 2026-10-23T15:53Z · live reads 15:57–15:58Z · kick-off 17:00Z (Hotspawn, agreeing with
Polymarket's `gameStartTime` and Pinnacle's `cutoffAt`).

| Venue | Committed | Live value | Source |
|---|---|---|---|
| Pinnacle | 1.298 / 3.61 → 73.6 % / 26.5 % | −335 / +261, period 0, `matchupId` 1638748200, max risk $10 000 | [matchups/1638748200/markets/related/straight](https://guest.api.arcadia.pinnacle.com/0.1/matchups/1638748200/markets/related/straight) · [public page](https://www.pinnacle.com/en/event/1638748200) |
| Polymarket | 76.5 ¢ / 23.5 ¢ | 0.765 / 0.235, volume $339 495, liquidity $317 051, updated 15:52:06Z | [gamma event](https://gamma-api.polymarket.com/events?slug=lol-gen-ig1-2026-10-23) · [public page](https://polymarket.com/event/lol-gen-ig1-2026-10-23) |
| Kalshi | 78 ¢ / 22 ¢ → 77.5 / 22.5 | Gen.G bid 0.77 / ask 0.78, IG 0.22 / 0.23 → midpoint 77.5 / 22.5 | [event API](https://api.elections.kalshi.com/trade-api/v2/events/KXLOLGAME-26OCT231300IGGEN?with_nested_markets=true) |
| Bovada | 1.24 / 3.80 → 75.3 / 24.7 | Gen.G −410 (1.243902), Invictus +280 (3.800) | [coupon API](https://www.bovada.lv/services/sports/event/coupon/events/A/description/esports/league-of-legends?marketFilterId=def&preMatchOnly=true&lang=en) · [public page](https://www.bovada.lv/esports/league-of-legends/world-championship-26/gen-g-invictus-gaming-202610231300) |

Weighted consensus recomputed by hand from the live decimals with the published weights
(0.36 Pinnacle / 0.24 Polymarket / 0.18 Kalshi / 0.22 Bovada): **0.7536**, published **0.7537**.
Difference 0.0001 — rounding.

### Pinnacle's kill market must not price a series

Pinnacle publishes a second matchup for the same series, `1638758865`, carrying the kill
markets. Live read at 15:57Z: moneyline −312 / +216 with a $3 000 risk limit, alongside
`team_total`, `spread` and `total` markets on the same `matchupId`; the series matchup
`1638748200` carries $10 000 limits and no kill lines.

The earlier published build cited 1.28 / 3.74 with the kills event URL. The current snapshot
excludes it: `collect.py` drops any matchup whose participants are labelled `(Kills)`, and
`data/raw/pinnacle_lol.json` contains 1638748200 only, at 1.298 / 3.61. Re-checked at
integration: the published `basis`, `decimal`, `american` and both URLs all now point to
1638748200, and `audit/verify_independent.py` flags a substitution if a kill-market price is
ever published as a series line (0 this build).

## 2. Arithmetic and provenance, every priced row

`audit/verify_independent.py` re-derives, without importing `tools/`:

- inventory identity between `data/raw/hotspawn_lol.json` (241 fixtures, all `scheduled`) and
  the 241 published rows, with no duplicate ids;
- every venue quote on all 9 market rows, re-found in the raw payload by team name and
  re-de-vigged (`0.36/0.24/0.18/0.22` weights), plus the published consensus;
- the whole 241-row probability surface: both sides sum to 1.000 within 0.002, the pick is the
  higher-probability side, and every model/provisional row reproduces the published value from
  the stored Elo inputs and the documented logit with the same clamp;
- every row carries at least one resolvable source URL and a `hotspawn_url` whose trailing id
  equals the row id.

Result: **0 failures, 10 warnings**. The warnings are the documented ones (thin samples,
one-sided history, model-vs-market divergence, the four settlement cards), not silent gaps.

## 3. Market-backed coverage, all nine rows

| Kick-off (UTC) | Match | p(favourite) | Venues |
|---|---|---|---|
| 10-23 17:00 | Gen.G v Invictus Gaming | 75.4 % | Pinnacle, Polymarket, Kalshi, Bovada |
| 10-23 18:00 | Hanwha Life Esports v Top Esports | 76.2 % | Pinnacle, Polymarket, Kalshi, Bovada |
| 10-23 19:00 | Bilibili Gaming v Movistar KOI | 79.1 % | Pinnacle, Polymarket, Kalshi, Bovada |
| 10-23 20:00 | Anyone's Legend v Karmine Corp | 63.8 % | Pinnacle, Polymarket, Kalshi, Bovada |
| 10-23 21:00 | G2 Esports v Dplus KIA | 41.2 % | Pinnacle, Polymarket, Kalshi, Bovada |
| 10-23 22:00 | Team Liquid v CTBC Flying Oyster | 71.3 % | Pinnacle, Polymarket, Kalshi, Bovada |
| 10-23 23:00 | LØS v T1 | 13.9 % | Pinnacle, Polymarket, Kalshi, Bovada |
| 10-24 00:00 | Team Secret Whales v LYON | 42.3 % | Pinnacle, Polymarket, Kalshi |
| 10-27 17:00 | Mental Rush v Vitality Rising Bees | 35.0 % | Polymarket only — thin, volume $5, low confidence |

The eight Worlds 2026 fixtures are exactly the eight LoL events on Bovada's coupon and on
Kalshi's `KXLOLGAME` series at the same timestamps. Everything else on Hotspawn's list
(232 of 241) has no reachable bookmaker line; those rows are labelled *originated* or
*provisional* and are never presented as market prices.

## 4. Irregularities recorded this round

1. **Kalshi stamps the wrong clock.** `occurrence_datetime` is `2026-10-23T21:00:00Z` while the
   match starts at 17:00Z per Hotspawn, Polymarket and Pinnacle's `cutoffAt`. Its ticker
   (`…26OCT231300…`) encodes 13:00 ET = 17:00Z, so the stamp is a four-hour offset, not a
   reschedule. Prices are used; the kick-off is not taken from Kalshi.
2. **Kalshi's displayed quote is a midpoint.** “78 ¢ / 22 ¢” is the rounded mid of a
   0.77 / 0.78 bid-ask. The published probability (77.5 / 22.5) is the midpoint, which is
   stated on the card.
3. **EGamersWorld receipts are excluded.** Eleven archived aggregator receipts (captured
   2026-10-21T20:36Z, 43.3 h before the build) are older than the 24-hour line-freshness limit
   and the domain now returns 403 to the runner. They influence nothing; the affected fixtures
   fall back to the live venues or an originated line. Flagged on *Flagged for review*.
4. **Four Komplettligaen cards have no probability.** Solid Gaming was removed mid-split; the
   Leaguepedia record carries `FF=1`/`FF=2` on those four series, so the site publishes the
   administratively correct side and no percentage. Hotspawn's own settlement of a void card is
   unverified.

## 5. What a reader can check without the build

Every row on `picks.html` links to the Hotspawn card and to the venue page or Leaguepedia page
used; the nine market rows add the exact provider endpoint (`api_url`). The block above links the
four live endpoints that reproduce the headline fixture, so the strongest claim on the site can be
checked by hand in under a minute.
