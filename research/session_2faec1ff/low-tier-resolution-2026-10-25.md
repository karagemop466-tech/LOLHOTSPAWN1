# Resolving a pick for every Hotspawn LoL match without a market line — 2026-10-25

**Session** `2faec1ff` (tasks T1/T2) · **Question from the brief:** matches that are
low-tier, or simply not listed by venues such as Polymarket, currently risk having
no pick. Find information sources that can guide a pick for those matches — first
established LoL betting sites, then esportsbooks and esports betting lines — and
document any picks that stay unresolved, with the limitations, as a separate
section tied to the executive summary.

**Short answer.** Every listed match already carries a pick after this session's
fix (241/241 in the 2026-10-24 snapshot; 234/234 in the fresh 2026-10-25 runner
build), but only 5–9 of them can be priced from an external line, because below
Worlds 2026 there is no reachable external line to copy. That finding was tested
three independent ways on 2026-10-25 (below). The defensible resolution for the
tail is therefore originated probabilities from recorded results — never a
borrowed placeholder, never Hotspawn's crowd vote — plus a documented settlement
where the league itself has removed a team. The separate unresolved section lives
on the site at [Unresolved & limitations](https://karagemop466-tech.github.io/LOLHOTSPAWN1/unresolved.html)
and is summarised, with counts and links, inside the executive summary on the
[landing page](https://karagemop466-tech.github.io/LOLHOTSPAWN1/).

## Method — how this was checked (no invented prices)

A number only ever becomes a published probability through `tools/collect.py`
(writing a dated receipt to `data/raw/`) and the de-vig in `tools/model.py`, on
the GitHub Actions runner. Everything below is evidence about *availability*;
an HTTP 200 HTML shell, a JS-rendered coupon with no fixtures in the payload, or
a symmetric `1.80 / 1.80` aggregator default is recorded as **no line**.

| # | Check (all 2026-10-25) | Receipt |
|---|---|---|
| 1 | **52-venue low-tier probe** from the runner against the *live* Hotspawn inventory (234 fixtures, 29 competitions), 14:20:27Z | [`data/probe/lowtier_20261025.json`](../../data/probe/lowtier_20261025.json) (bot commit `9811ff7`) |
| 2 | **37-source availability probe** from the runner, 14:20:51Z | [`data/probe/sources_probe.json`](../../data/probe/sources_probe.json) (bot commit `de9ed13`) |
| 3 | **Full pipeline diagnostic** on this branch (live collect → model → site → 52-gate verify) | [`data/diag/refresh.log`](../../data/diag/refresh.log) (bot commit `b45d88d`): 234/234 fixtures, methods `{model 150, provisional 71, market 9, unresolved 4}`, all gates pass |
| 4 | **Browser captures** (second egress, can observe but never price): bo3.gg and EGamersWorld LoL match centres | dated fetches in session log (URLs below) |
| 5 | **Web falsification searches** for low-tier odds (PRM 3rd Division, Komplettligaen, Tunisian Super League) + B2B feed review (Oddin.gg, OddsPapi coverage docs) | URLs below |

## What the venues actually returned

Runner probe, 37 sources (`found` = current Hotspawn team names present in payload):

| Venue (established book / exchange, already integrated) | HTTP | Teams found |
|---|---|---|
| Pinnacle guest API — https://guest.api.arcadia.pinnacle.com/0.1/sports/12/matchups | 200 JSON | 4 — Worlds only |
| Polymarket gamma — https://gamma-api.polymarket.com | 200 JSON | 8 — Worlds only |
| Kalshi `KXLOLGAME` — https://api.elections.kalshi.com | 200 JSON | 8 — Worlds only |
| Bovada LoL coupon — https://www.bovada.lv | 200 JSON | 8 — Worlds only |

Everything else returned nothing usable for *any* current fixture: GG.BET 403,
Stake 403, EGamersWorld 403, Sofascore 403, DraftKings 403, FanDuel 400,
Rivalry API 502, Betway 404, Unibet web 503 (the Kambi JSON feed used by the
pipeline *did* answer — see low-tier matrix), Betano/BetOnline/Thunderpick/
BC.GAME/Flashscore/OddsPortal 200 but HTML with zero current fixtures,
The Odds API and OddsPapi 401 (key-gated — recorded as key-gated, never as a price).

Low-tier matrix (52 venues × 29 competitions; a competition counts as covered
only if a venue payload mentions ≥2 of its current teams or its name):

| Competition group | Venues listing it |
|---|---|
| Worlds 2026 Main Event | Pinnacle, Unibet/Kambi, Bovada, Polymarket, Kalshi (5) |
| LGC Rising 2026 Playoffs | Polymarket only (thin: $28 traded at last pricing) |
| **Other 27 competitions** — PRM 2nd/3rd Division, RIVALS LEAGUE, Tunisian Super League, Arabian League 2nd Div + Regionals, Icelandic Esports League, Komplettligaen (+Playoffs), Benelux Ascend Series (+Rising, Promotion), LigaGG CELOL A/B (+Playoffs), Superstrike (+Logitech qualifier), 4 Nations, LCP Promotion, LIT Promotion, FPL, Hitpoint 2nd, Legends Academy, POP Esports Masters | **none** |

Verdict distribution across the 52 probed venues: 19 auth/geo/bot-walled,
9 reachable HTML with no low-tier fixture text, 6 gone/no public page,
5 reachable mentioning current teams (the integrated five above),
4 reachable JSON with no low-tier fixture, remainder 202/203/429/502/unreachable.
Note on precision: Pinnacle's payload contains single-name substring hits
(e.g. "sissi state punks", "fennel"); they do not form a priced fixture pair for
any Hotspawn card — the pipeline's pair+time matching prices Worlds and LGC
Rising only — so they are reported as *no line*, not coverage.

Independent browser captures the same day agree: bo3.gg's LoL match centre
(https://bo3.gg/lol/matches/current) and EGamersWorld's LoL list
(https://egamersworld.com/lol/matches) each show **Worlds 2026 fixtures only**
for 25–26 Oct, although Hotspawn lists dozens of PRM/Tunisian/RIVALS/etc. cards
on those dates. Web searches for "PRM Prime League 3rd Division betting odds",
"Komplettligaen LoL betting odds" and "Tunisian Super League LoL betting odds"
return Leaguepedia/wiki pages and unrelated football content — no book, tipster
line or odds page for those leagues was found.

B2B feeds deserve an explicit line because they are the usual "surely someone
prices it" candidate: Oddin.gg advertises an esports odds feed covering LoL
(https://oddin.gg/esports-odds-feed) but sells it to operators (Betway/Yolo/
Altenar/Softswiss per its own materials) under contract — there is no public,
per-fixture URL this project could cite on a row. OddsPapi's published LoL
coverage (https://oddspapi.io/blog/esports-odds-api-guide-how-to-get-pinnacle-cs2-lol-data-for-free/)
lists Worlds, LEC, LCS, LCK, LPL, CBLOL, LJL and *Prime League Pro Division*
(1st Division) — i.e. it stops above every PRM division Hotspawn lists — and its
API returned 401 without a key. Keyed/B2B routes are therefore logged as
**owner-credential options**, not sources, consistent with prior flags.

## How a pick is resolved when no venue prices the match

In pipeline order (`tools/model.py`), unchanged in structure this session:

1. **Market line** — fresh (≤24 h) real-money quotes, de-vigged and
   precision-weighted across venues; every quote URL published on the row.
   5 rows in the corrected 2026-10-24 snapshot (6 before the LYON fix below);
   9 rows in the fresh 2026-10-25 runner build.
2. **Originated Elo line** — our own win probability from recorded series
   results (Leaguepedia MatchSchedule): recency/inactivity decay, division
   priors, margin scaling, shrinkage; ratings strictly pre-kickoff
   (no look-ahead, gated). 154 rows (150 fresh).
3. **Provisional originated line** — same model, but <5 rated series for a side
   (or no shared-opponent chain); published low-confidence with a per-row flag.
   78 rows (71 fresh). Only 3 team-sides in the whole snapshot have zero rated
   series; they are priced from the stated division prior, on the card.
4. **Official settlement, no probability** — the league removed a team
   mid-split (Leaguepedia `dqteams`: Solid Gaming, Komplettligaen 2026 Autumn),
   so a competitive probability would be fiction. 4 rows, each naming the
   settlement winner and linking `https://lol.fandom.com/wiki/Data:Komplettligaen/2026_Season/Autumn_Split`,
   with Hotspawn's void rule (https://play.hotspawn.com/how-it-works) disclosed.

Coverage: **241/241 picks (237 with a win probability + 4 settlements)** in the
corrected snapshot; **234/234 (230 + 4)** live. Community/guide material that can
*inform a human* but must never price a row: Leaguepedia standings/results (already
the model's input), Liquipedia (403 from the runner), bo3.gg/EGW results pages.
Hotspawn's crowd-pick percentages are captured for audit and carry zero weight —
the brief forbids Hotspawn as a probability indicator, and the LYON card shows
why crowd/in-play signals mislead (91% crowd for Karmine Corp pre-lock vs a 99%
settling print for LYON after lock; neither is a pre-match line).

## Defect found and fixed while auditing the tail (T2)

LYON vs Karmine Corp (Worlds, id `1067684`) was published as **LYON 99%** from a
single Kalshi print captured **52 min after kick-off** (feed fetched
2026-10-24T20:52:38Z; kick-off 20:00Z; Hotspawn lock 19:55Z; Kalshi bid/ask
0.99/1.00 vs 0.00/0.01 — `data/raw/kalshi_lol.json`,
`data/raw/hotspawn_lol.json`). Pre-match books had LYON at 44.0–45.7% (receipts
in `data/corroboration.json`); LYON won 1–0
(https://liquipedia.net/leagueoflegends/World_Championship/2026), so the winner
name coincided while the probability and usability were false. Fixes in
`tools/model.py` (commit `6ee259a`): reject any venue quote observed at/after
kick-off; reject prediction-market sides ≥97% (mirror of the decimal-extreme
rule Kalshi/Polymarket bypassed); require every live feed ≤24 h old (previously
Kambi-only); disclose rejections per row and in `market_hygiene`. Three new
publish gates (52/52 pass) and `tests/test_market_guards.py` (80/80 suite) pin
the behaviour; the corrected row uses the originated line (Karmine Corp 60.3%)
and is the *only* row whose pick changed. Published as a high-severity curated
flag on https://karagemop466-tech.github.io/LOLHOTSPAWN1/flagged.html.

## Unresolved picks & limitations (the separate section)

Site locations: executive-summary block + unresolved table on
https://karagemop466-tech.github.io/LOLHOTSPAWN1/ (`#unresolved-summary`), full
ledger + per-competition fallback matrix on
https://karagemop466-tech.github.io/LOLHOTSPAWN1/unresolved.html, irregularities on
https://karagemop466-tech.github.io/LOLHOTSPAWN1/flagged.html. Currently
unresolved-as-probability: the 4 Solid Gaming settlements above; nothing else —
every other card carries a probability or would fail the publish gate
("silently unpriced" is gated impossible).

Limitations that apply to originated/provisional picks, stated plainly:

- **No external corroboration exists** below the Worlds ceiling; an originated
  line is a model estimate (backtest: 3,903 series, 64.95% accuracy, Brier
  0.2185 — https://karagemop466-tech.github.io/LOLHOTSPAWN1/methodology.html),
  not a market observation.
- **History is community-maintained** (Leaguepedia), including kick-off times
  that sometimes disagree with Hotspawn by hours; mismatches are flagged per row.
- **Debut/thin teams** are priced substantially from division priors; two debut
  sides meeting is near a coin-flip by construction and labelled provisional.
- **Thin single-venue markets** (e.g. LGC Rising on Polymarket, $28) are
  indicative only and downgraded to low confidence.
- **Snapshot drift:** Hotspawn added/removed cards between snapshots
  (241 on 2026-10-24 → 234 live on 2026-10-25); the 6-hourly refresh
  (`.github/workflows/refresh.yml`, cron `17 */6 * * *`) plus the on-page
  staleness banner (warn 12 h / hard-stale 30 h) bound, but do not eliminate,
  that lag. Started matches also disappear from Hotspawn's scheduled feed,
  while some past-start cards linger as "scheduled" (flagged per row).
- **Availability is volatile:** bot walls/geo-blocks change hourly; each probe
  is a dated observation, re-runnable via `tools/probe_sources.py` /
  `tools/probe_lowtier.py`. In-browser coupons (e.g. GG.BET/Thunderpick web
  apps) cannot be rendered by the runner and remain unprobed beyond HTTP status.
- **What would change the conclusion:** any venue returning a machine-readable
  team-pair + price for a low-tier fixture. The integration path already
  exists (parser in `collect.py` → receipt → weighted consensus), and the
  probes above are the tripwire that would detect it.
- Not betting advice; Hotspawn voids forfeited-match predictions.

## Reproduce

```bash
python3 tools/probe_sources.py    # runner: data/probe/sources_probe.json
python3 tools/probe_lowtier.py    # runner: data/probe/lowtier_<date>.json
python3 -m unittest discover -s tests -v   # 80 tests
python3 tools/verify.py                    # 52 publish gates
```
