# Low-tier line-source research — 2026-10-24 (session `e32a5c4b`, task E2)

**Question.** For every Hotspawn League of Legends match that *cannot* be resolved like a
featured (market-backed) pick — because it is a low-tier match or is not listed on venues
such as Polymarket — is there any other information source that can guide the pick?
Order tried, per the brief: (1) established LoL betting sites, (2) esportsbooks and esports
betting lines, (3) exchanges/aggregators, (4) results/community sources that can guide
(never price) a pick.

**Method.** `tools/probe_lowtier.py` on a GitHub Actions runner (the dev sandbox has no
outbound HTTPS), 2026-10-24T16:19:47Z. It first fetched the live Hotspawn LoL inventory
(public fixtures API, HTTP 200, **241 fixtures, 29 competitions**), then issued **one
honest GET per venue** (public URL only, no login, no credential, no bypass) to **51
venues**, and searched each response for the *current* team and competition names.
A competition only counts as "mentioned" if ≥2 distinct current team names or the
competition name appears. Full receipts: [`data/probe/lowtier_20261024.json`](../data/probe/lowtier_20261024.json).
Published picks snapshot reconciled against: `data/matches.json` generated
2026-10-24T16:21:25Z (**241 matches: 9 market, 150 originated, 78 provisional,
4 forfeit settlements**). Hotspawn crowd percentages were never used.

## Headline finding

> Of 29 competitions on Hotspawn, exactly **2 appear in any probed venue payload**:
> **Worlds 2026 Main Event** (Pinnacle, Unibet/Kambi, Bovada, Polymarket, Kalshi) and
> **LGC Rising 2026 Playoffs** (Polymarket only). The other **27 competitions — 232 of 241
> matches — are mentioned by no reachable book, esportsbook, exchange or aggregator.**
> There is therefore no external line to copy for them; the only honest resolutions are
> (a) an originated line from recorded results, (b) a provisional originated line with an
> explicit thin-data warning, or (c) an official-forfeit settlement with no probability.
> That is what the site publishes. Anything else would be invented.

Status mix across the 51 venues: 17× HTTP 200, 18× 403 (bot/geo wall), 6× 404, 2× 429
(Kambi alt-operators), 2× 202, 2× 203, 2× DNS/TLS failure, 1× 401, 1× 503, 1× 530.
An HTTP 200 HTML shell is **not** a line: Bwin, 888sport, Rivalry, BC.GAME, PARI,
Midnite, Flashscore and bo3.gg all answered 200 with **zero** current low-tier fixtures
in the payload (JavaScript-rendered coupons expose no public JSON price feed to a runner).

## What was tried, by group (receipts in the JSON)

| Group | Venues | Result for the low-tier tail |
|---|---|---|
| Controls (already integrated) | Pinnacle matchups + league list, Unibet/Kambi `ubse`, Bovada coupon, Polymarket Gamma, Kalshi `KXLOLGAME` | All HTTP 200 JSON. Together they price only Worlds (8 series) + LGC Rising (Polymarket, low-confidence single market). No ERL/academy coverage. |
| Established books | Kambi `gb32`/`lvg` (429), Betway (404), Betsson/NordicBet (202 shells), Bwin/Entain (200 shell), Betano/Marathonbet/William Hill (403), 1xBet/Melbet line feeds (203, no LoL fixture text), 888sport (200 shell) | None exposes a usable low-tier LoL price to the runner. Kambi remains usable only via the integrated `ubse` operator. |
| Esportsbooks | GG.BET, Thunderpick (+API), Stake, Duelbits (all 403); Rivalry page 200 shell / API 530; BC.GAME, PARI, Midnite (200 shells); BetBoom 401; Pixel.bet DNS failure; Loot.bet TLS failure | None usable. Third-party affiliate guides claim GG.BET prices regionals/academy LoL, but the runner is refused (403), so that claim is **unverified** and cannot back a pick. |
| Aggregators / match centres | EGamersWorld 403, OddsPortal 503, Oddspedia/Escorenews/Sofascore API 403, BetExplorer/Cybersport.ru/Strafe 404, Flashscore/bo3.gg 200 with no tail fixtures | None usable as an automated price source. EGamersWorld manual receipts remain corroboration-only (see `data/retired_quotes.json`); symmetric 1.80/1.80 quotes are placeholders and are rejected. |
| Exchanges | Smarkets API 404, Betfair 403, SX Bet API 200 JSON with no LoL low-tier markets | No additional LoL tail liquidity found. Betfair's real API needs an application key (see below). |
| Results / community (guide, never price) | Leaguepedia Cargo 200 (control, integrated); Liquipedia, Oracle's Elixir, Sheep Esports 403; gol.gg 404; LoL Esports API 403 without key header; PandaScore 403 without token | Leaguepedia remains the only runner-reachable results source covering the tail, which is why the originated Elo is built on it. It is a **community-maintained** source, labelled as such everywhere. |

### Sources that need an owner-provided credential (flagged, not circumvented)

These *might* widen coverage but cannot be used today without a key the project does not
hold. They are recorded so the owner can decide; no key was requested from the user in
chat and none must be committed to the repo (use a GitHub Actions secret if ever added):

- **OddsPapi** (multi-book odds API) — its public guide claims LoL coverage including
  Prime League Pro Division via books such as Pinnacle/Bet365/1xBet, but the API requires
  a key. Unverified for PRM 2nd/3rd Division specifically.
- **PandaScore / GRID / Abios** — esports data APIs; PandaScore returned 403 without a token.
- **Betfair Exchange API** — requires an application key + account; web coupon is 403 to the runner.
- **The Odds API** — keyed; esports coverage would need verifying per league.

Also **not yet probed** (honest gap, next probe): TonyBet and BetOnline (named in
third-party 2026 LoL betting guides), plus in-browser manual checks of GG.BET/Thunderpick
coupons, which a runner cannot render. A browser-visible price that no runner can fetch
still cannot power a 6-hourly automated site.

### False positives and traps (why word-search alone never prices a match)

- **888sport / Rivalry "hits" are generic words** (`arena`, `fame`, `torin`) in page
  chrome, not fixtures. Single-word team names collide with English; only a paired
  fixture with a two-way price counts.
- **Pinnacle lists, but does not price, the tail.** The matchups *listing* mentions a
  PRM team (Sissi State Punks), yet the collector found only 8 series moneylines
  (`s;0;m`), all Worlds. A listing without a moneyline price — including `(Kills)`
  derivative markets, which are explicitly excluded — is not a usable line.
- **Placeholder odds are not odds.** Symmetric 1.80/1.80 aggregator quotes carry no
  information and are rejected by the publish gate.
- **Hotspawn crowd % is never an input**, however one-sided it looks on the lobby cards.

## Official forfeit rule (verified 2026-10-24)

Hotspawn's own help page states: *"If a match is forfeited, all predictions for that match
are voided. No points are awarded or deducted…"* — <https://play.hotspawn.com/how-it-works>.
Consequence for the 4 Komplettligaen Solid Gaming cards: the site shows the official
forfeit winner (the remaining opponent) with **no probability**, and the expected Hotspawn
outcome is **void (0 points either way)**. The pick is therefore informational, not a
forecast; if Hotspawn instead grades a walkover, the shown side is the administratively
correct one. Picks also lock 5 minutes before the scheduled start (same source), which is
why the site sorts by kick-off and marks started cards as stale.

## Per-competition fallback ledger (snapshot 2026-10-24T16:21Z)

"External line?" = any of the 51 probed venues mentioning the competition (see matrix in
the receipts). "Pick basis" is how every match in that competition is actually resolved on
the site today. Originated = Elo over Leaguepedia series results (25-month window,
strictly pre-kickoff ratings; out-of-sample n=3,896, accuracy 64.96%, Brier 0.2185).
Provisional = same model with <5 rated series on at least one side (or one-sided history),
labelled low-confidence on every card.

| Competition | Matches | Market | Originated | Provisional | Settlement | External line? | Main limitation / what would upgrade it |
|---|---:|---:|---:|---:|---:|---|---|
| Worlds 2026 Main Event | 8 | 8 | 0 | 0 | 0 | Yes — 5 venues | Featured resolution. Lines move; refreshed 6-hourly. |
| LGC Rising 2026 Playoffs | 1 | 1 | 0 | 0 | 0 | Yes — Polymarket only | Single prediction market, labelled low confidence. A second venue would upgrade it. |
| PRM 3rd Division 26-27 Fall | 62 | 0 | 46 | 16 | 0 | No | Largest tail block; German 3rd division unpriced by every probed book incl. Entain/Kambi. More recorded series shrink the 16 provisionals. |
| PRM 2nd Division 26-27 Fall | 36 | 0 | 32 | 4 | 0 | No | As above, one division higher; still no public coupon found. |
| RIVALS LEAGUE Season 2 | 25 | 0 | 16 | 9 | 0 | No | Community league; thin/new teams drive provisionals. |
| Tunisian Super League 2026 | 25 | 0 | 5 | 20 | 0 | No | Weakest data: 20/25 provisional. Needs more Leaguepedia-recorded series; treat % as directional only. |
| Icelandic Esports League 2026 Autumn | 12 | 0 | 5 | 7 | 0 | No | Small scene, homonym risk (e.g. Fenrir) handled by competition-scoped joins. |
| Arabian League 2nd Division 2026 Summer | 9 | 0 | 5 | 4 | 0 | No | Regional 2nd division; academy rosters churn between splits. |
| Arabian Regional Ch. — Lebanon-Libya-Syria-Palestine | 6 | 0 | 0 | 6 | 0 | No | All provisional: little recorded history. Directional only. |
| Arabian Regional Ch. — Qatar-Bahrain-Kuwait | 2 | 0 | 0 | 2 | 0 | No | All provisional, same cause. |
| Komplettligaen 2026 Autumn | 6 | 0 | 2 | 0 | 4 | No | Solid Gaming removed mid-split (`dqteams`): 4 cards settled to the official forfeit winner, no probability; expected Hotspawn void (see rule above). |
| Komplettligaen 2026 Autumn Playoffs | 3 | 0 | 3 | 0 | 0 | No | Playoff cards priced by Elo; Norwegian books (Betsson/NordicBet) expose no feed. |
| Superstrike League 2026 | 6 | 0 | 5 | 1 | 0 | No | Originated; one thin-history card. |
| Logitech G SuperStrike Cup Qualifier | 4 | 0 | 0 | 4 | 0 | No | New qualifier, all provisional (new/open-bracket teams). |
| 4 Nations 2026 Halloween Heist | 5 | 0 | 4 | 1 | 0 | No | Short invitational; limited cross-pool history. |
| Benelux Ascend 2027 Winter Promotion | 5 | 0 | 5 | 0 | 0 | No | Promotion bracket; ratings from Ascend splits. |
| Benelux Ascend Rising 2026 Summer Playoffs | 5 | 0 | 5 | 0 | 0 | No | Originated. |
| Benelux Ascend 2026 Summer Split / Playoffs | 3 | 0 | 3 | 0 | 0 | No | Originated; homonym joins evidenced in `data/matching_report.json`. |
| LigaGG CELOL A/B 2026 (splits + playoffs) | 10 | 0 | 8 | 2 | 0 | No | Brazilian collegiate/amateur tiers; two thin-history cards. |
| LCP 2027 Promotion | 3 | 0 | 2 | 1 | 0 | No | APAC promotion; books price LCP proper sporadically but no probed venue listed these cards. |
| FPL 2026 Summer Playoffs | 1 | 0 | 1 | 0 | 0 | No | Single remaining card, originated. |
| Hitpoint 2nd Div Challengers 2026 Summer Playoffs | 1 | 0 | 1 | 0 | 0 | No | Single card, originated. |
| LIT 2027 Winter Promotion | 1 | 0 | 1 | 0 | 0 | No | Single card, originated. |
| Legends Academy (Żabka) S3 Playoffs | 1 | 0 | 1 | 0 | 0 | No | Polish academy, single card, originated. |
| POP Esports Masters Season 7 | 1 | 0 | 0 | 1 | 0 | No | Single provisional card (thin history). |

**How to read a non-featured pick on your phone:** Market = de-vigged book consensus
(trust most) → Originated = our Elo (backtested ~65% out-of-sample) → Provisional = same
Elo on thin data (use with caution; the % is shrunk toward 50%) → Settlement = official
forfeit winner, no % (expected void). Every card shows its basis, both teams' rated-series
counts, and source links; the pick is always the higher-% side (gate-enforced).

## Limitations of this probe

1. One GET per venue from a US GitHub runner at one instant. Geo-fenced EU books may show
   more to an EU browser; that does not make them automatable here.
2. JavaScript-rendered coupons (most 200 shells) may display prices in a browser that are
   invisible to a runner. No headless-browser scraping, login, or bot-wall bypass was
   attempted — by design.
3. Coverage changes as tournaments start/finish. Re-run
   `python3 tools/probe_lowtier.py` (workflow: `probe-lowtier-lines`) before citing this
   memo after a split change.
4. Affiliate "best LoL betting sites" pages are marketing, not evidence; they were used
   only to *find* candidate venues, never to assert coverage.

## Manual review links

- Receipts: [`data/probe/lowtier_20261024.json`](../data/probe/lowtier_20261024.json) ·
  earlier probes: [`data/probe/sources_probe.json`](../data/probe/sources_probe.json),
  [`data/line_source_research.json`](../data/line_source_research.json)
- Picks data: [`data/matches.json`](../data/matches.json) · [`data/picks.csv`](../data/picks.csv)
- Hotspawn rules: <https://play.hotspawn.com/how-it-works> · Lobby: <https://play.hotspawn.com/lobby>
- Live site: <https://karagemop466-tech.github.io/LOLHOTSPAWN1/> (Unresolved & limitations page carries this ledger in summary form)
