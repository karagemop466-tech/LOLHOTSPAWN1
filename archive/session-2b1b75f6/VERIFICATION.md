# Verification log

Snapshot referenced: **2026-10-21T20:43:30Z** (see `data/meta.json` for the live timestamp).
Everything below was produced by `pipeline/` running on a GitHub Actions runner, then re-read from the
committed `data/*.json`. Anything that could not be checked against a primary source is listed under
*Flagged for review* and is also published on `flagged.html`.

---

## 1. Repository review (before any change)

| Item | Finding | Evidence |
|---|---|---|
| Default branch | `main` @ `464a318a489ad224d55b214d7bb86ed9b62af8fb` — "Initial commit" | `git log`, GitHub API `/repos/.../branches` |
| Files | exactly one: `README.md` (14 bytes) containing `# LOLHOTSPAWN1github.com` | `git ls-tree -r main` |
| Code / data / workflows / docs | none | same |
| GitHub Pages | enabled, `build_type: legacy`, source `main` / root, URL `https://karagemop466-tech.github.io/LOLHOTSPAWN1/` | `GET /repos/karagemop466-tech/LOLHOTSPAWN1/pages` |
| Branches during the session | `arena/8336fb7e-…`, `arena/b166e06b-…`, `arena/9d43092a-…` (parallel sessions), plus this one | `GET /repos/.../branches` |

**Irregularity #0 (flagged):** the initial `README.md` was a single malformed line (`# LOLHOTSPAWN1github.com`),
i.e. the repository contained no prior implementation to review or verify. Nothing was deleted; the README was
replaced with real documentation for this build.

---

## 2. Fixture source — Hotspawn Play (match list only)

| Check | Result |
|---|---|
| URL | <https://play.hotspawn.com/lol-pickems> (canonical advertised by the page: `https://www.hotspawn.com/league-of-legends/pickems`) |
| Delivery | Angular SSR; hydrated state embedded as `<script id="ng-state" type="application/json">` |
| Extraction | match list at `state["1214417440"]["b"]`; located by shape (`competition_name`, `participants0_name`, `participants1_name`) rather than by hard-coded key |
| Rows | **264** matches, **27** competitions |
| Integrity | 0 duplicate Hotspawn ids, 0 blank team names, 0 matches without a kickoff timestamp |
| Sanity check | the lobby's own tier filter prints "(264)" — matches the extracted count |
| Not used | `participants*_picked_percent` (crowd popularity) — stored for display only |

Permalinks: the same payload carries an id → `https://www.hotspawn.com/matches/…` map, parsed generically.
`https://www.hotspawn.com` itself returns **HTTP 403** to datacenter IPs, so pages are not re-fetched
(flagged, see §6).

---

## 3. Market sources (the only inputs to any probability)

| Source | Endpoint | Status this run | Used for |
|---|---|---|---|
| Bovada | `bovada.lv/services/sports/event/coupon/…/esports/league-of-legends` | **200, 9 events** | Head-to-Head moneyline, full series, per event page linked |
| Pinnacle | `guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups` + `/matchups/{id}/markets/related/straight` | **200, 9 LoL matchups** (World Championship 10 incl. props, EMEA Masters 2) | full-series moneyline |
| Polymarket | `gamma-api.polymarket.com/events?tag_slug=league-of-legends&closed=false` | **200, 13 LoL series markets** | traded price treated directly as probability |

**Protocol:** implied probability = `1/decimal`; two-way proportional de-vig
`p = implied / (implied_a + implied_b)`; multiple books combined by the **median**; dispersion (max − min)
sets the confidence label (≤5 pp high, ≤12 pp medium, otherwise low).

### Hand-check of the de-vig (values copied from `data/matches.json`)

| Match | Bovada (decimal) | Pinnacle (decimal) | Median published |
|---|---|---|---|
| Gen.G vs Invictus Gaming | 1.1818 / 4.50 → 84.62% / 22.22% → **79.20%** Gen.G | 1.2299 / 4.23 → 81.31% / 23.64% → **77.47%** Gen.G | **78.34% Gen.G** |
| G2 Esports vs Dplus KIA | 2.20 / 1.6452 → 45.45% / 60.78% → **42.79%** G2 | 2.26 / 1.6757 → 44.25% / 59.68% → **42.58%** G2 | **42.68% G2 → Dplus KIA 57.32%** |
| Galions vs Solary | 1.87 / 1.87 → 53.48% / 53.48% → **50.00%** Galions | 1.7874 / 2.05 → 55.95% / 48.78% → **53.42%** Galions | **51.71% Galions** (3.4 pp dispersion → high) |

Worked example (Gen.G, Bovada): `1/1.1818 = 84.62%`, `1/4.5 = 22.22%`, sum `106.84%` → de-vig
`84.62/106.84 = 79.20%`. Overround is stored per quote (`overround` field) and ranges 3.9%–6.9%,
which is normal for esports moneylines.

Prices move: the Bovada Galions line went 1.9524/1.80 → 1.87/1.87 between two runs 10 minutes apart, which is
exactly why the site is rebuilt from live prices instead of being hard-coded. All 9 published picks trace to a linked quote; raw decimal odds for **both** sides are stored per source and
shown on every card, so each row can be re-derived by hand. Pinnacle's public site exposes one league page
rather than per-match deep links, so its card links to the League of Legends matchups page.

---

## 4. Coverage audit — why 255 matches are unpriced

Books checked and what they returned for League of Legends this run (see `data/sources.json` and the
*Sources* page): Bovada 9 events, Pinnacle 9 matchups for real series, Polymarket 13 series markets.
Union after name matching: **9 distinct Hotspawn matches** — the 8 Worlds 2026 Swiss matches plus
EMEA Masters (Galions vs Solary).

Books/services that were tested and produced no usable feed (logged with the exact failure on the
*Sources* page): 1xBet (HTML bot gate), Betano (403), Marathonbet (403), GG.Bet (403, region),
Oddspedia (403/410), BetExplorer (404), bo3.gg (no odds endpoint), Prime League official site (403),
Leaguepedia/Fandom API (rate-limited), lolesports official API (403), OddsPortal (reachable but no API).

No bookmaker, exchange or prediction market in that list publishes a market for PRM 2nd/3rd Division,
Tunisian Super League, Icelandic Esports League, 4 Nations Halloween Heist, LigaGG CELOL, RIVALS League,
Komplettligaen, Arabian League 2nd Division, Superstrike, FPL, POP Esports Masters or the ERL promotion
events — therefore no probability is published for them. They are listed individually on
`unresolved.html`. **No number was inferred, interpolated or copied from Hotspawn's crowd poll.**

---

## 5. Site verification

| Check | Result |
|---|---|
| Internal links | every `href` in the nav resolves to a generated page (index, picks, unresolved, tournaments, methodology, sources, flagged) |
| Assets | only `assets/style.css` + `assets/app.js`, both local; no external fonts/CDNs |
| Mobile | single-column cards ≤620 px, sticky top nav with horizontally scrollable pills, 44 px tap targets, `viewport` meta present, kickoff times converted to device timezone by `app.js` |
| Data files | `data/matches.json`, `unresolved.json`, `quotes.json`, `sources.json`, `tournaments.json`, `meta.json`, `picks.csv` |
| Rebuild | `python3 pipeline/build_data.py && python3 pipeline/build_site.py` reproduces the pages deterministically from the same inputs |

---

## 6. Flagged for review (unverified or irregular)

1. **Team-name variants** — `LØS` (Hotspawn) vs `Los Grandes` (Bovada) vs `LOS` (Polymarket);
   `Team Secret Whales` vs `Team Secret`; `LYON` vs `Lyon Gaming`. Auto-matched on normalised names plus a
   48-hour kickoff check; listed on `flagged.html` for human confirmation.
2. **Hotspawn permalink reachability** — `www.hotspawn.com` returns HTTP 403 to the runner, so the
   permalinks were not re-fetched; they come from the lobby payload's own id→URL map.
3. **Hotspawn `www` match list vs lobby** — `www.hotspawn.com/matches?game=league-of-legends` is blocked
   (403) from the runner, so we cannot prove the lobby list is a superset of every LoL fixture on the site.
   The lobby is treated as the source of truth for "matches listed in the pick'em game".
4. **Polymarket prices are not bookmaker lines** — they are market mid/last prices; labelled per card.
5. **Single-source picks** — none this run (all 9 have two books). If one appears it is labelled low
   confidence and listed on `flagged.html`.
6. **Start-time drift** — Hotspawn kicks off hourly slots for the Worlds Swiss round while books are within
   the hour; the matcher allows ≤48 h and the pick card shows the Hotspawn time.
