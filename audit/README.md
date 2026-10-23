# Independent audit — 2026-10-23 (session `6d1ede2c`)

Two scripts in this directory re-check the published dataset **without importing `tools/`**:

| Script | What it proves | Result on the committed tree |
|---|---|---|
| `verify_independent.py` | every published number is reproduced from the committed raw provider payloads | **0 failures**, 10 warnings, 0 kills-market substitutions |
| `check_site.py` | every internal link, id, mobile viewport and match card on the 18 published pages | **0 failures** |

Run them with `python3 audit/verify_independent.py && python3 audit/check_site.py`.
Machine-readable output lands in `audit/report.json`, `audit/report.md` and `audit/site_check.json`.

## What was verified, line by line

| Check | Method | Result |
|---|---|---|
| Inventory | id multiset, Hotspawn raw fixtures vs published rows | 241 = 241, unique, no extras |
| Team names / start times | published row vs raw Hotspawn fixture | 241/241 identical |
| Elo probabilities | recomputed `1/(1+10^((elo1-elo0)/400))`, clamped to the published floor/ceiling | 228/228 model + provisional rows reproduce within 0.0015 |
| Market quotes | each of the 32 venue quotes re-derived from `data/raw/*.json` | 32/32 reproduce |
| De-vig | proportional margin removal recomputed per venue | 32/32 within 0.002 |
| Consensus | published weights re-applied to the venue probabilities | 8/8 multi-venue rows within 0.001 |
| Pick | pick == argmax of the published probabilities | 237/237 priced rows |
| Sum to 100 % | p0 + p1 | 237/237 |
| Unresolved rows | must carry no probability and no pick | 4/4 correctly blank |
| Sourcing | Hotspawn match-card URL ends with the row id | 241/241 |
| Site | internal links, anchors, duplicate ids, viewport, match-card count | 18 pages, 0 failures |

## Live spot checks (2026-10-23, 15:35–15:41 UTC)

| Source | Live value observed | Committed value | Verdict |
|---|---|---|---|
| Polymarket `lol-gen-ig1-2026-10-23` (updated 15:34:19Z) | 0.775 / 0.225 | 77.5¢ / 22.5¢ | matches |
| Kalshi `KXLOLGAME-26OCT231300IGGEN` | Gen.G bid 0.77 / ask 0.78, IG 0.22 / 0.23 | mid 77.5 / 22.5 | matches |
| Pinnacle series matchup `1638748200` | −355 / +274, max risk 10,000 | 1.26 / 3.94 | matches |
| Pinnacle kills matchup `1638758865` | −324 / +223, max risk 3,000, plus team-total kills 17.5 / 9.5, kill spread ±8.5, kill total 27.5 | — | distinct market, **not** a series line |
| Hotspawn fixtures API | not re-fetched here: this sandbox has no egress to Hotspawn. Inventory evidence is the committed `data/raw/hotspawn_lol.json` (`fetched_utc` 2026-10-23T11:42:37Z) plus the 6-hourly Actions run | 241 rows | provenance stated, not claimed live |

Sources: <https://gamma-api.polymarket.com/events?slug=lol-gen-ig1-2026-10-23> ·
<https://api.elections.kalshi.com/trade-api/v2/events/KXLOLGAME-26OCT231300IGGEN?with_nested_markets=true> ·
<https://guest.api.arcadia.pinnacle.com/0.1/matchups/1638748200/markets/related/straight> ·
<https://guest.api.arcadia.pinnacle.com/0.1/matchups/1638758865/markets/related/straight>

## Defects found and fixed here

| # | Defect | Evidence | Fix |
|---|---|---|---|
| D1 | Pinnacle's **"most kills" market was used as the series moneyline** on 6 of the 8 matched rows. The published Pinnacle link pointed at the kills matchup, and for Gen.G vs Invictus Gaming the site published 1.28/3.74 (kills, 74.5 %) instead of the series 1.26/3.94 (75.8 %). | `pinnacle_lol.json` holds 8 records named `<team> (Kills)` with different prices and 3,000 stake limits vs 10,000 for the series lines; live API confirms the kills matchup carries kill totals/spreads. | `collect.py` skips `(Kills)` matchups; `model.py` refuses to price from one even if an old snapshot contains it. The audit now fails if a kills line is ever used. |
| D2 | `/markets/related/straight` returns the **sibling matchup's markets too**; the collector did not filter by `matchupId`, so a price could be attached to the wrong matchup. | The response for `1638758865` lists markets whose `matchupId` is `1638748200`. | Collector keeps only markets whose `matchupId` is the matchup being priced. |
| D3 | `tools/__pycache__/common.cpython-311.pyc` was committed although `.gitignore` excludes it. | `git ls-files | grep pycache` | Untracked. |
| D4 | Build log said pages were written "to docs/" while they are written to the repository root. | `tools/site.py` (`DOCS = ROOT`) | Wording corrected. |

After the fix the Gen.G row is 76.7 % / 23.3 % from a 4-venue consensus; the Pinnacle link now points at
series matchup `1638748200`. All 17 publish gates still pass.

## Irregularities flagged, not resolved (for review)

1. **Four fixtures have no pick.** All four are `Solid Gaming` fixtures in Komplettligaen 2026 Autumn,
   removed mid-split under Leaguepedia's community-maintained `dqteams` directive. They are 6–36 days
   past their listed start and Hotspawn still shows them as scheduled, so a card may be void or settled
   as a walkover. No probability is published; the unresolved section states the conditional outcome.
2. **Leaguepedia is not an official league authority.** It is a community wiki; the removal directive and
   all historical results come from it. The site labels it as such.
3. **Only four venues are reachable from the build runner.** Pinnacle, Bovada, Kalshi and Polymarket
   returned HTTP 200; GG.BET (403 region), Stake (403 Cloudflare), EGamersWorld (403 Cloudflare),
   Liquipedia (403) and BetExplorer (404) did not. Runner-side receipts: `data/probe/sources_probe.json`
   (session `a91e528d`, probed 2026-10-23T15:37Z).
4. **Tier-2/tier-3 coverage is therefore model-originated, not market-derived.** 228 of 241 rows have no
   bookmaker price from any reachable venue; they carry an Elo line with a stated confidence level.
5. **Stale fixtures.** Hotspawn keeps `status=scheduled` after kick-off; the rows are kept to mirror the
   inventory exactly and are marked "start time passed".
6. **Kalshi expiry convention.** `expected_expiration_time` is 21:00Z while the match starts 17:00Z; the
   ticker (`26OCT231300`) and the market rules both say 13:00 ET = 17:00Z, so this is an expiry offset,
   not a start-time conflict.
7. **Collection age.** The committed inventory was collected at 11:42Z and the pages were rebuilt at
   15:41Z. The site shows the collection timestamp and warns when it is more than 8 hours old.

## Limits of this audit

- This sandbox can only reach `github.com`, `codeload.github.com`, `api.github.com`,
  `registry.npmjs.org`, `pypi.org` and `files.pythonhosted.org` from the shell. Provider calls that need
  a socket were made through the browsing layer (URL + timestamp recorded above); everything else was
  re-derived from committed evidence.
- The Elo backtest (3,854 series, 64.1 % accuracy, Brier 0.221) is reproduced by re-running
  `tools/model.py`; its out-of-sample construction was read but not independently re-implemented.
