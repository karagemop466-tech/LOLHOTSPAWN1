# Independent source audit — session `0d48f265`

**As of:** 2026-10-23 ~15:50 UTC · **Subject:** `data/matches.json` as merged from `main` (PR #19 runner collection: `inventory_fetched_utc` 2026-10-23T15:37:40Z, `generated_utc` 15:39:34Z; 241 rows). An earlier draft of this audit read the 11:42:37Z snapshot; the 15:37Z data was re-checked, and the differences are recorded below.
**Scope:** `audit/**` only. Nothing in `tools/`, `data/`, `assets/`, or the root pages was changed by this audit.
**Machine-readable:** [`audit.csv`](audit.csv) (one row per match, 241 rows) · [`summary.json`](summary.json) · [`build_audit.py`](build_audit.py) (re-runnable) · [`receipts/`](receipts/)

## 1. Method and limits (read this first)

- The build sandbox's shell has no outbound route to the data providers (`curl` fails with `SSL_ERROR_SYSCALL` for Hotspawn, Pinnacle, Polymarket, Kalshi). Live checks in this audit were made with a separate page-fetch tool, which does reach them. Each live receipt below names the exact URL and what it returned.
- **Every row was checked internally** (team names present, kick-off parseable, probabilities sum to 1, pick = higher side, unresolved rows carry no number, Hotspawn card link present, stale-flag consistent with kick-off time). These checks are reproducible from `build_audit.py`.
- **Live re-checks were sampled, not exhaustive.** The Hotspawn fixtures API returns 24 chunks; I read chunk 0 (10 rows). Two of nine market rows and four of four unresolved rows were re-fetched against their venue or Leaguepedia. The other 231 rows are *not* re-verified against a live source in this audit; `audit.csv` says so per row. I did not fill in any value I could not see.
- Leaguepedia is community-maintained, not an official league or Riot source. Polymarket resolves through gol.gg, a third-party stats site. Both are labelled as such.

## 2. Results summary

| Check | Rows | Result | Verdict |
|---|---|---|---|
| Internal consistency (all fields, all methods) | 241 | 1 finding: row `1071212` past kick-off but not stale-flagged (see F1) | pass with 1 flag |
| Live Hotspawn inventory, chunk 0 (ids, teams, competition, kick-off UTC) | 10 | 10 / 10 identical to committed snapshot | **verified (sample)** |
| Market re-check, Gen.G v Invictus Gaming (`1067878`) | 1 | Polymarket and Kalshi match; Pinnacle price and (in 15:37Z data) source URL match; Bovada moved between snapshots and was not re-checked live (F2 resolved, F8 added) | **partly verified** |
| Market re-check, Mental Rush v Vitality Rising Bees (`1079080`) | 1 | Polymarket 67.5 / 32.5 live; stored 67.5 / 32.5 in 15:37Z data: match. Volume $5 (F3); start time differs (F4) | **value verified, quality flagged** |
| Unresolved `dqteams` rows (`1071170`, `1071200`, `1071206`, `1071186`) | 4 | Teams and dates match Leaguepedia completed fixtures for 3 of 4; 1 date mismatch (F5) | **flagged** |
| All other rows (231) | 231 | Not re-fetched live; internal checks only | not verified live |

## 3. Row-level evidence

### 3.1 Hotspawn inventory, chunk 0 (10 / 10 identical)

Source: <https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=lol&status=scheduled&tenantId=1> (chunk 0 of 24, retrieved 2026-10-23 ~15:44Z). Transcription: [`receipts/hotspawn_live_chunk0_2026-10-23.csv`](receipts/hotspawn_live_chunk0_2026-10-23.csv).

| Match id | Competition | Teams | Kick-off UTC | Result |
|---|---|---|---|---|
| 1053095 | Benelux Ascend Series 2026 Summer Split | Mind Blue eSports v LAST DANCE | 2026-08-26 17:00 | identical |
| 1053096 | Benelux Ascend Series 2026 Summer Split | Nameless v BiPOLAR | 2026-08-26 18:00 | identical |
| 1066214 | FPL 2026 Summer Playoffs | Epic Avalanche v Finnish Red Mafia | 2026-08-27 15:00 | identical |
| 1053111 | Benelux Ascend Series Rising 2026 Summer Playoffs | Team VS Esport v GALA Esports | 2026-09-05 11:00 | identical |
| 1071584 | LIT 2027 Winter Promotion | P11 Esports v HANGMEN | 2026-09-07 17:00 | identical |
| 1070209 | Benelux Ascend Series Rising 2026 Summer Playoffs | Triforce Esport v Venus | 2026-09-12 11:00 | identical |
| 1070210 | Benelux Ascend Series Rising 2026 Summer Playoffs | GALA Esports v The Bandits Academy | 2026-09-13 11:00 | identical |
| 1069849 | LigaGG CELOL B 2026 Split 2 | Docta Esports Club v Viktus | 2026-09-13 15:00 | identical |
| 1071167 | Komplettligaen 2026 Autumn | DMG Esports Norway v Playwell Rød Q | 2026-09-17 15:00 | identical |
| 1071170 | Komplettligaen 2026 Autumn | Solid Gaming v VES Japan | 2026-09-17 15:00 | identical (see F5) |

### 3.2 Market rows re-checked

**1067878 — Worlds 2026 Main Event: Gen.G v Invictus Gaming** (stored: Gen.G 76.2 % / Invictus 23.8 %, method `market`)

- Polymarket: <https://gamma-api.polymarket.com/markets?slug=lol-gen-ig1-2026-10-23> — `outcomePrices` `["0.775","0.225"]`, `gameStartTime` 2026-10-23 17:00:00+00. Stored: 77.5 / 22.5 ✔. Resolution source: gol.gg (third party).
- Kalshi: <https://api.elections.kalshi.com/trade-api/v2/events?series_ticker=KXLOLGAME&status=open&with_nested_markets=true&limit=100> — `KXLOLGAME-26OCT231300IGGEN-GEN` yes bid 0.77 / ask 0.78 / last 0.78 (midpoint 0.775). Stored: 77.5 / 22.5 ✔.
- Pinnacle: <https://guest.api.arcadia.pinnacle.com/0.1/matchups/1638758865/markets/related/straight> — the full-match moneyline `−355 / +274` (stored decimal 1.282 / 3.74 ✔) is served under `matchupId 1638748200`, **not** `1638758865`. Matchup `1638758865` returns a **game-1 (period 1)** moneyline of `−324 / +223`. In the 11:42Z snapshot the row linked `1638758865`; in the 15:37Z data it links `https://www.pinnacle.com/en/event/1638748200` and `api_url …/matchups/1638748200/…`, which is where the price is served. See F2 (resolved in the fresh data).
- Bovada: the quote in the 11:42Z snapshot was 1.22 / 4.05 (76.9 %); in the 15:37Z data it is 1.24 / 3.85 (75.7 %). Not re-checked live in this audit. See F8.
- Stored 76.05 % → displayed "76.0 %" in the 15:37Z `basis` text; the value 0.7605 itself is internally consistent with the venue weights (recomputed 0.7605).

**1079080 — LGC Rising 2026 Playoffs: Mental Rush v Vitality Rising Bees** (stored: Mental Rush 32 % / Vitality 68 %, method `market`, single venue)

- Polymarket: <https://gamma-api.polymarket.com/markets?slug=lol-rb-mr-2026-10-27> — match-winner market (`groupItemTitle` "Match Winner"): `outcomePrices` Vitality Rising Bees `0.675` / Mental Rush `0.325`, `volume` **5** (USD), `liquidity` 4,225.78, `gameStartTime` 2026-10-27 16:00:00+00.
- Event page context: <https://gamma-api.polymarket.com/events?slug=lol-rb-mr-2026-10-27> — the first market returned is *Game 1 Winner* at `0.5 / 0.5` with `bestBid 0.04 / bestAsk 0.96` (spread 0.92).
- The stored 32 / 68 is the match-winner price rounded to the nearest percent ✔. The quality of the quote is the issue (F3, F4).

### 3.3 Unresolved `dqteams` rows

Source: Leaguepedia `MatchSchedule` rows for `Solid Gaming` in `Komplettligaen/2026 Season/Autumn Split` — <https://lol.fandom.com/wiki/Special:CargoExport?tables=MatchSchedule&fields=MatchSchedule.Team1,MatchSchedule.Team2,MatchSchedule.Winner,MatchSchedule.DateTime_UTC,MatchSchedule.OverviewPage,MatchSchedule.Team1Score,MatchSchedule.Team2Score&where=MatchSchedule.OverviewPage%3D%27Komplettligaen%2F2026+Season%2FAutumn+Split%27+AND+%28MatchSchedule.Team1%3D%27Solid+Gaming%27+OR+MatchSchedule.Team2%3D%27Solid+Gaming%27%29&limit=50&format=json>. Page: <https://lol.fandom.com/wiki/Komplettligaen/2026_Season/Autumn_Split>.

| Match id | Hotspawn kick-off UTC | Leaguepedia row (community) | Note |
|---|---|---|---|
| 1071170 Solid Gaming v VES Japan | 2026-09-17 15:00 | 2026-10-01 16:00, VES Japan 2–0 Solid | **no 09-17 row**; date mismatch (F5) |
| 1071200 Solid Gaming v Playwell Rød Q | 2026-10-04 15:00 | 2026-10-04 15:00, Playwell 2–0 Solid | same date; completed |
| 1071206 Volda E-Sport v Solid Gaming | 2026-10-11 15:00 | 2026-10-11 15:00, Volda 2–0 Solid | same date; completed |
| 1071186 Solid Gaming v NTNUI Kometkameratene | 2026-10-13 17:00 | 2026-10-13 17:00, NTNUI 2–0 Solid | same date; completed |

Leaguepedia lists 11 `Solid Gaming` rows in this split (2026-09-08 to 2026-10-22). In all 11, Solid Gaming is on the losing side of the recorded winner, with a 0–2 or 2–0 score. The wiki rows do not say "forfeit", so a walkover is **not verified** from this source. A 0–2 score is consistent with one but does not prove it.

## 4. Irregularities for review (published on Flagged for Review)

| ID | Severity | Finding | Evidence | Suggested action |
|---|---|---|---|---|
| F1 | medium | 66 of 241 rows have a kick-off before the audit time; 65 carry the stale flag. Row `1071212` (Rich Gang v Phenti, kick-off 2026-10-23 15:00 UTC) does not, because the snapshot (11:42Z) predates kick-off. Its pick is still shown as upcoming. | `audit.csv` (`past_start`, `snapshot_stale_flag`); `summary.json` → `past_start_not_flagged_ids` | Re-collect; flag any row whose kick-off has passed at publish time |
| F2 | resolved in 15:37Z data (was high) | Gen.G v Invictus: in the 11:42Z snapshot the Pinnacle `source_url` / `api_url` pointed to matchup `1638758865`, which does not serve the `−355 / +274` price (served under `1638748200`; `1638758865` returns a game-1 price `−324 / +223`). The 15:37Z data stores `1638748200` for both fields. | Pinnacle URLs above | Keep a regression check that the stored matchup serves the stored price |
| F3 | high (quality) | Mental Rush v Vitality Rising Bees is labelled `market` on a single venue whose match-winner market has **$5 total volume** and $4,226 liquidity. A line this thin should not be presented with the same weight as a deep market. | `volume` `5` on `lol-rb-mr-2026-10-27` | Keep the quote, but label it "thin market" and never weight it as high confidence |
| F4 | medium | Start-time mismatch on `1079080`: Hotspawn 2026-10-27 17:00 UTC; Polymarket `gameStartTime` 16:00 UTC (stated as 12:00 PM ET, which is 16:00 UTC under EDT). | Polymarket URL above; committed `start_utc` | Use the source with the official kick-off, record both, flag |
| F5 | high (pick gap) | The four `dqteams` unresolved rows are all in the past, and Leaguepedia already shows each as completed with the opponent winning. Hotspawn still lists them as `scheduled`. Row `1071170` has no Leaguepedia row on its Hotspawn date (09-17); the Solid–VES Japan game is recorded on 10-01. | §3.3 | Decide and document the settlement rule before publishing an implied pick. This audit publishes no pick. |
| F8 | info (price movement) | The Bovada quote for Gen.G v Invictus changed between the 11:42Z and 15:37Z snapshots (1.22 / 4.05 → 1.24 / 3.85), and the consensus moved from 76.2 % to 76.0 %. Prices are time-stamped by snapshot, not by live view. Not re-checked live. | `data/matches.json` `market.venues[3]` in both snapshots | Show the capture time next to every market quote |
| F6 | info (methodology) | The 4-venue consensus uses fixed house weights (Pinnacle 0.36, Polymarket 0.24, Kalshi 0.18, Bovada 0.12). They are a methodology choice, not an external figure, and are not sourced. | `data/matches.json` `market.venues[].weight` | Document as a method choice on the methodology page |
| F7 | info (sources) | Leaguepedia (community wiki) and gol.gg (Polymarket's resolution source) are third-party, not official league or Riot sources. | Sources above | Keep the "community-maintained" labelling |

## 5. What this audit does not establish

- It does not establish that any of the 231 non-sampled rows is correct on the live Hotspawn feed, nor that their model probabilities are calibrated (the calibration numbers are the model's own backtest, not an external check).
- It does not establish the Bovada quote for `1067878`, nor the full Polymarket order book for `1079080`.
- It does not confirm that `1071170`'s Hotspawn card and the Leaguepedia 10-01 game are the same fixture. Only team names and the opponent's date pattern support that.
- Nothing here changes a published value. Corrections belong to the pipeline owners (see `COORDINATION.md`).

## 6. Sources used

| Source | URL | Type | Used for |
|---|---|---|---|
| Hotspawn fixtures API | https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=lol&status=scheduled&tenantId=1 | Hotspawn (pick'em host) | inventory, chunk 0 |
| Hotspawn LoL pick'em lobby | https://play.hotspawn.com/lol-pickems | Hotspawn | card links used in the dataset |
| Pinnacle guest API (matchups) | https://guest.api.arcadia.pinnacle.com/0.1/matchups/1638758865/markets/related/straight | Pinnacle (licensed bookmaker) | Gen.G v Invictus moneyline provenance |
| Polymarket Gamma (market) | https://gamma-api.polymarket.com/markets?slug=lol-gen-ig1-2026-10-23 · …?slug=lol-rb-mr-2026-10-27 | Polymarket (prediction market) | two market re-checks |
| Polymarket Gamma (event) | https://gamma-api.polymarket.com/events?slug=lol-gen-ig1-2026-10-23 · …?slug=lol-rb-mr-2026-10-27 | Polymarket | game markets, start times |
| Kalshi KXLOLGAME | https://api.elections.kalshi.com/trade-api/v2/events?series_ticker=KXLOLGAME&status=open&with_nested_markets=true&limit=100 | Kalshi (CFTC-regulated exchange) | Gen.G v Invictus quote |
| Leaguepedia MatchSchedule (Cargo) | https://lol.fandom.com/wiki/Special:CargoExport?tables=MatchSchedule&… (see §3.3) | Community wiki | unresolved rows |
| Leaguepedia Autumn Split page | https://lol.fandom.com/wiki/Komplettligaen/2026_Season/Autumn_Split | Community wiki | context for the DQ rows |

## 7. Manual review links

- Committed data: <https://github.com/karagemop466-tech/LOLHOTSPAWN1/blob/main/data/matches.json>
- This audit's row table: <https://github.com/karagemop466-tech/LOLHOTSPAWN1/blob/arena/0d48f265-lolhotspawn1/audit/audit.csv>
- Re-run: `python3 audit/build_audit.py`
