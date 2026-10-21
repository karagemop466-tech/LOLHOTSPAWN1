# Hotspawn LoL Pick Desk

**Live dashboard:** <https://karagemop466-tech.github.io/LOLHOTSPAWN1/>

A self-running pipeline that mirrors the complete League of Legends pick'em list from
`play.hotspawn.com/lol-pickems` and publishes an independent win probability for **every** match on it.
Probabilities come from real bookmaker lines where they exist, and from a results-based Elo model
where they do not. Hotspawn's own crowd-pick percentages are never used as an input.

The site rebuilds itself every six hours from GitHub Actions; nothing here needs a laptop to stay current.

## What it produces

| Page | Contents |
| --- | --- |
| `index.html` | Executive summary, headline counts and in-site links to every list |
| `picks.html` | All 264 matches, one card each, next kick-off first, with the pick, both win probabilities and source links |
| `featured.html` | Matches with a real bookmaker price, the raw odds and the de-vig arithmetic |
| `originated.html` | Matches with no market price: our own line, the Elo inputs and the team records behind it |
| `unresolved.html` | Matches we refuse to price, why, and every limitation that applies to the rest of the list |
| `competitions.html` | Coverage, source quality and staleness per tournament |
| `teams.html` | Every team with its rating, record and competition |
| `flagged.html` | Irregularities and unverified items, published rather than hidden |
| `verification.html` | The publish gate, its results, and the evidence behind every non-exact team join |
| `sources.html` | Every source, what it provides, and whether the build runner could reach it |
| `methodology.html` | Sources, Elo specification, de-vig method, exclusions |

## How it works

```
tools/collect.py   Hotspawn fixtures API · Pinnacle guest API · Polymarket · Leaguepedia Cargo · LoL Esports
      ↓
tools/model.py     Elo over Leaguepedia series results, de-vig of bookmaker moneylines
      ↓
tools/report.py    per-tournament and per-team summaries
      ↓
tools/flags.py     derived irregularities + curated notes (data/flags_manual.json)
      ↓
tools/site.py      11 static pages, mobile-first, no framework
      ↓
tools/verify.py    14 assertions; a failure aborts the commit instead of publishing bad data
```

A single workflow (`.github/workflows/refresh.yml`, cron `17 */6 * * *`) runs that chain on `main`,
commits `data/` and the generated pages with `[skip ci]`, and lets GitHub Pages redeploy.
Only `tools/` writes the published pages.

### Inputs and rules

- **Inventory** — `https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=lol&status=scheduled&tenantId=1`
  returns every LoL card, including the long tail of national and academy leagues.
- **Market lines** — Pinnacle's public guest API (LoL moneylines), with Polymarket used as an
  independent cross-check. Bookmaker odds are converted to decimal, then de-vigged proportionally.
- **Originated lines** — Elo fitted on Leaguepedia series results, recency-weighted, with a
  connected-opponent graph guard; teams with too little recorded history are labelled *provisional*
  rather than silently given a confident number.
- **Never used** — Hotspawn's `picked_percent`, its tiers, or its points as probability inputs.
- **Blank beats wrong** — a value that cannot be confirmed from a primary source is left blank and
  listed on `flagged.html`; nothing is inferred to fill a gap.
- **Stale rows** — the API keeps returning `status:"scheduled"` for fixtures whose start time has
  passed. They stay on the list (so coverage matches Hotspawn exactly), are marked "start time passed"
  and are sorted after upcoming matches.

### Verification gate

`tools/verify.py` fails the build unless, at minimum: all 264 rows parse, every row carries a
Hotspawn match-card link, both probabilities sum to 100 %, the published pick is the higher-probability
side, ids are unique, `picks.csv` mirrors the dataset, all 11 pages exist, every internal link
resolves, no `None`/empty value is rendered, every match appears on `picks.html`, the executive
summary links to every view, and each source's availability is recorded.

## Manual review links

- `data/picks.csv` — one row per match: competition, teams, pick, probability, method, source URLs.
- `data/matches.json` — full record per match, including odds, Elo inputs and flags.
- `data/matching_report.json` — every team join that was not an exact string match, with its evidence.
- `data/verification.json` — the machine-readable result of the gate.
- `data/build.log` — the last automated run, verbatim.
- `COORDINATION.md` — task board, session log and the integration decisions taken across sessions.

## Repository layout

- `tools/` — the only publisher (collect → model → report → flags → site → verify)
- `data/` — generated dataset, CSV, flags, verification result and build log
- `assets/` — `style.css`, `app.js` (tabs, timezone conversion, no dependencies)
- `archive/` — superseded sessions, kept as audit evidence; nothing there runs
- `evidence/snapshot/` — frozen raw responses backing the published numbers

## Running it locally

```bash
python3 tools/collect.py && python3 tools/model.py && python3 tools/report.py \
  && python3 tools/flags.py && python3 tools/site.py && python3 tools/verify.py
```

The collector needs outbound HTTPS to the sources listed on `sources.html`; the rest runs offline on
the files in `data/`.
