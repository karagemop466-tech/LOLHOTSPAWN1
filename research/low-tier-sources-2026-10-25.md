# Low-tier LoL source review — 2026-10-25

## Scope and evidence standard

This review targeted listed matches outside the featured market feed, especially LCP 2027
Promotion and LGC Rising. Pages were retrieved through the browser fetch/search layer on
2026-10-25 UTC. These are point-in-time observations, not claims that a GitHub runner can
fetch the same pages. A number becomes a pricing input only when it is a named, two-sided
match-winner quote with a fixture/team/time join and a verifiable pre-lock observation.
Hotspawn crowd percentages are never inputs.

## New findings

| Match / source | What the source actually showed | Classification and action |
|---|---|---|
| Vitality Rising Bees vs Mental Rush — [Esports Insider match page](https://esportsinsider.com/betting-odds/lol/match/rising-bees-vs-mental-rush-1743342) | LGC Rising 2026, BO5, 2026-10-27 17:00 GMT. Match Winner Odds named **1xBet 1.43 / 2.78** and **GG.bet 1.43 / 2.63**. | Real bookmaker quotes displayed by an aggregator. Useful independent corroboration for a match that already has an integrated external line; not silently blended with the live consensus. A future automated integration needs a runner-reachable parser, raw receipt and pre-lock timestamp. |
| FENNEL vs Nothin'Here — [Esports Insider match page](https://esportsinsider.com/betting-odds/lol/match/fennel-league-of-legends-vs-nothin-here-1766739) | LCP Promotion 2027, BO5, 2026-11-10 05:00 GMT. Under Match Winner Odds: **“No bookmaker prices yet — None of the books we track are pricing this match. The ESI model view is in the sidebar.”** | Explicitly **no external bookmaker line**. The 62% / 38% shown on the [ESI board](https://esportsinsider.com/betting-odds/lol) is therefore not treated as a betting quote or independent real-money probability. The match remains on our disclosed originated/model path. |
| FENNEL vs Nothin'Here — [EGamersWorld match page](https://egamersworld.com/lol/match/eDTgthgYk/fennel-vs-nothinhere-Ud8jrB4zR) | Both sides displayed **1.8 / 1.8**, with 0% crowd widgets. | Symmetric placeholder, not a price. Rejected by the existing placeholder policy; the 0% crowd widget is not used either. |
| Ground Zero Gaming vs Frank Esports — [EGamersWorld match page](https://egamersworld.com/lol/match/eDTgthgYk/ground-zero-gaming-vs-frank-esports-wvOLKhrveF) | LCP 2027 Promotion, BO5; both sides displayed **1.8 / 1.8**, with 0% crowd widgets. | Symmetric placeholder, not a price. No probabilities or picks were inferred from it. |
| LCP 2027 Promotion — [Leaguepedia](https://lol.fandom.com/wiki/LCP/2027_Season/Promotion) and [Liquipedia](https://liquipedia.net/leagueoflegends/LCP/2027/Promotion) | Independent schedule/bracket pages list FENNEL–Nothin'Here and Ground Zero–Frank Esports. | Community-maintained schedule/results corroboration only, not betting evidence and not an official settlement authority. |
| PRM 2nd Division — [Leaguepedia season page](https://lol.fandom.com/wiki/Prime_League_2nd_Division/2027_Season/Fall_Split) | Current schedule and results are available. Search also surfaced a Betmonitor competition shell, but no verified matching two-team quote for a listed Hotspawn fixture. | Results can support the originated Elo. No bookmaker line was claimed from a competition landing page or search snippet. |

## Source-board limitation

The [Esports Insider LoL board](https://esportsinsider.com/betting-odds/lol) said it had 12
upcoming series on retrieval. It is a curated board, not proof that an unlisted match has no
price anywhere. “No line found” always means no usable line in the sources checked, not a
universal claim about every bookmaker.

The board's real decimal prices and its model-only percentages must be parsed differently.
In particular, a board value is not promoted to `method=market` unless the match page or
raw feed identifies a bookmaker and a two-sided match-winner price. ESI-only model output
can be documented as a community cross-check but does not replace our independent model or
become an external-market probability.

## Hotspawn rule recheck

[Hotspawn — How Pick'Ems Works](https://play.hotspawn.com/how-it-works) states:

- picks lock **5 minutes before the scheduled start**;
- if a match is forfeited, all predictions are **voided**, with no points awarded or deducted.

The collector stores `lock_time`; the model now requires every matched market observation
to be timestamped no later than that lock. Later or untimed observations are excluded and
listed in `data/market_exclusions.json`. Administrative forfeit outcomes remain separate
from competitive win probabilities.

## Changes resulting from this review

1. Added the Esports Insider board to `tools/probe_lowtier.py` so the scheduled research
   probe checks it alongside established books, esportsbooks, exchanges and aggregators.
2. Kept ESI model-only percentages and EGamersWorld 1.80/1.80 placeholders out of pricing.
3. Kept the real LGC book quotes as corroboration only until an automated, receipted,
   pre-lock parser exists; no manual number was mixed into the live consensus.
4. Preserved the originated-line fallback for LCP and documented the exact external-source
   limitation instead of filling the gap with an aggregator estimate.
