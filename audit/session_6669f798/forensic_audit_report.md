# Forensic Entity-Resolution & Multi-Venue Audit Report (`session_6669f798`)

**Audit UTC:** `2026-10-24T16:40:00Z`  
**Scope:** Secondary Node pipeline (`scripts/*.mjs` -> `docs/*` & `data/node/**`) + cross-verification of all `241` scheduled Hotspawn League of Legends fixtures across `29` competitions.

## 1. Newly Discovered Cross-Region Homonym Contamination (`#1083097`)

- **Hotspawn Fixture:** `#1083097` — `Logitech G SuperStrike Cup Qualifier | paiN Gaming vs Non-toxic Gaming` (`2026-10-24T11:00:00Z`, Bo1).
- **Official Leaguepedia Evidence:** `https://lol.fandom.com/wiki/Logitech_G_SuperStrike_Cup/Qualifier` and `https://lol.fandom.com/wiki/Data:Logitech_G_SuperStrike_Cup/Qualifier?action=raw` prove that the team in Round 1 is **Bulgarian amateur roster `PNG`** (`billy`, `Bla6ko`, `metko`, `ifo`, `anditobate`), **NOT** Tier-1 Brazilian CBLOL organization `paiN Gaming`.
- **Empirical Falsification of Unscoped Global Join:** Unscoped global exact-name matching bound `paiN Gaming` to Brazilian `paiN Gaming` (`n = 62`, Elo `~1576.9`), emitting a fabricated `~60.9%` favorite pick on `paiN Gaming`. In reality, Bulgarian `PNG` had `0` prior official series and lost `0–1` to `Non-toxic Gaming`.
- **Resolution in `scripts/analyze.mjs`:** Added competition-scoped entity override `Logitech G SuperStrike Cup Qualifier::pain gaming -> PNG` (`n = 0`), leaving `#1083097` honestly `unresolved` (`p0 = null, p1 = null, pick = null`) and publishing the receipt on `docs/flagged.html` and `docs/unresolved.html`. Logged cross-scope fix request in `COORDINATION.md` for canonical `data/aliases.json` / `tools/model.py`.

## 2. Newly Recovered Regulated CFTC Market Line on `#1079080` (`LGC Rising 2026 Playoffs`)

- **Hotspawn Fixture:** `#1079080` — `LGC Rising 2026 Playoffs | Mental Rush vs Vitality Rising Bees` (`2026-10-27T17:00:00Z`, Bo5).
- **Official Kalshi CFTC Receipt:** `https://api.elections.kalshi.com/trade-api/v2/events/KXLOLGAME-26OCT271300RBMR?with_nested_markets=true` (`https://kalshi.com/markets/kxlolgame/kxlolgame-26oct271300rbmr`) quotes active binary contracts for `"Rising Bees"` (`0.58 / 0.65`) vs `"Mental Rush"` (`0.36 / 0.46`, `~$429` resting orderbook depth).
- **Resolution in `scripts/analyze.mjs`:** Added `"rising bees" -> "vitality rising bees"` market normalization and Polymarket slug-date matching (`lol-rb-mr-2026-10-27`), upgrading `#1079080` from a thin single-venue Polymarket quote to a **2-venue CFTC + CLOB consensus** (`Mental Rush 39.4% / Vitality Rising Bees 60.6%`, inter-venue spread `0.7 pp`). Also added `"løs" -> "los"` normalization so `#1067686` (`G2 Esports vs LØS`) joins all **4/4** live venues (`Pinnacle`, `Unibet/Kambi`, `Kalshi CFTC`, `Polymarket`).

## 3. Complete Scheduled Inventory Accounting (`241` Matches)

| Bucket | Count | Basis & Verification |
|---|---:|---|
| Active (`open` / `locked`) Multi-Venue Market Consensus | `9` | `8` Worlds 2026 Main Event Swiss R2 (`4` venues each: Pinnacle + Unibet/Kambi + Kalshi CFTC + Polymarket) + `1` LGC Rising (`2` venues: Kalshi CFTC + Polymarket) |
| Active (`open` / `locked`) Self-Originated Pre-Kickoff Elo | `163` | `115` established (`min(n0, n1) >= 5`, including `#1081423` `Ground Zero Gaming 19.1% vs Frank Esports 80.9%`) + `48` provisional (`1 <= min(n0, n1) <= 4`) |
| Active (`locked`) Unresolved Zero-History Debuts | `4` | `#1083096`, `#1083097`, `#1083098`, `#1083105` (`Logitech G SuperStrike Cup Qualifier`, `min(n0, n1) = 0` pre-kickoff — left blank `—`) |
| Stale (`>6h` past kickoff) Pre-Kickoff Elo | `59` | Regional cards still marked `scheduled` upstream; scored strictly `t < T_kickoff` |
| Stale Mid-Split Disqualification Walkovers | `4` | `#1071170`, `#1071200`, `#1071206`, `#1071186` (`Solid Gaming` removed from `Komplettligaen 2026 Autumn`; `settlement_pick` -> active opponent, `p = null`) |
| Stale Zero-History Debuts | `2` | `#1074627` (`Northern Wolves Esports` Sep-27 debut `n0 = 0`), `#1082002` (`DELETED` `n0 = 0`) |
| **Total Scheduled Hotspawn LoL Inventory** | **`241`** | **1:1 exact multiset match with live Hotspawn LoL feed** |
