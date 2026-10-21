# Hotspawn League of Legends (LoL) Pick'ems — Independent Line Origination & Quant Dashboard

**Live Mobile-First Dashboard:** <https://karagemop466-tech.github.io/LOLHOTSPAWN1/>

An automated, zero-crowd-bias data pipeline, probability origination engine, and mobile-first static dashboard covering **100% of all scheduled League of Legends Pick'em fixtures** on Hotspawn (`play.hotspawn.com/lol-pickems` and `play.hotspawn.com/lobby`).

---

## Executive Summary (Snapshot `2026-10-21T20:39Z`)

- **Strict Zero-Crowd Invariant:** Hotspawn crowd `picked_percent` values are **stripped before modeling** and unit-tested (`tests/test_pipeline.py::test_zero_hotspawn_crowd_sensitivity_across_all_264_matches`) for exact `0.0000` sensitivity across all 264 matches.
- **Full Board Coverage (`264` Scheduled LoL Rows Across `27` Competitions):**
  - **`195` Open Upcoming Pick'em Matches (`lock_time > now`, across `13` active competitions):**
    - **`10` Tier-1 External Real-Money Sportsbook & Exchange Picks (`featured.html`):**
      - **`9` Four-Venue Consensus Picks** (`Worlds 2026 Main Event` Swiss Stage Round 1 [8/8] + `EM 2026 Summer Main Event` Grand Final `Galions vs Solary` [1/1]) combining vig-removed **Pinnacle** moneylines, **Polymarket** two-way CLOB, **Kalshi** CFTC-regulated contracts, and specialist LoL esportsbooks.
      - **`1` Specialist Esportsbook Line** (`LCP 2027 Promotion`: `Ground Zero Gaming vs Frank Esports`, `91.1% vs 8.9%`), unlisted on Polymarket/Kalshi/Pinnacle and priced directly from live specialist esportsbook decimal odds (`1.025 vs 10.50`).
    - **`178` Tier-2 Originated Low-Tier Regional Picks (`originated.html`):**
      - Covers all 10 regional/amateur LoL circuits (`PRM 2nd Division`, `PRM 3rd Division`, `4 Nations Halloween Heist`, `RIVALS LEAGUE Season 2`, `Tunisian Super League`, `Arabian League 2nd Division`, `Komplettligaen`, `LigaGG CELOL B Playoffs`, `LGC Rising Playoffs`, `Arabian Regional Championship`) using **2,598 verified Leaguepedia `Data:` match records** (`2,393` completed series).
      - Chronological walk-forward validation (`train_date < match_date`, `N = 1,595` pre-match 2026 series) achieves **`64.9%` out-of-sample winner accuracy**, **Brier score `0.2145`** (**`−14.2%` MSE improvement** over `0.2500` coin-flip baseline), **Log-Loss `0.6175`** (vs `0.6931`), and **ECE `3.53%`** at global optimum `λ* = 1.50`.
    - **`7` Tier-3 Open Unresolved / Caveat Fixtures (`unresolved.html`):**
      - **`1` Removed-Team Phantom Fixture (`#1071216 Solid Gaming vs DMG Esports Norway`, `Komplettligaen 2026 Autumn`):** Official league records confirm `Solid Gaming` was removed in Round 10 (`dqteams=Solid Gaming`), and all 4 prior post-removal fixtures went unplayed—yet **72% of Hotspawn users picked `Solid Gaming`**. Defensive card lean: **Active `DMG Esports Norway` (never pick `Solid Gaming`)**.
      - **`6` Pure Statistical Dead Heats (`49.8% – 50.5%`, within `±0.5%` of `50/50`):** Explicitly quarantined rather than fabricating directional edge when zero bookmaker lines exist (`#1079030`, `#1079038`, `#1075770`, `#1075791`, `#1079053`, `#1075802`).
  - **`69` Past-Lock Orphaned Upstream Rows (`stale_locked`, `lock_time <= now`):**
    - Still served as `status="scheduled"` with `0–0` scores by Hotspawn's API; audited line-by-line against official Leaguepedia match results (**`64 / 69` completed official series scores recovered**).

---

## Site Pages

| Page | Purpose |
| :--- | :--- |
| [`index.html`](index.html) | Upfront **Executive Summary**, quick navigation, trap warnings, urgent lock slate, active leagues table |
| [`picks.html`](picks.html) | Master filterable open Pick'ems board (`195` open matches: cards + compact table + CSV/JSON download) |
| [`featured.html`](featured.html) | Side-by-side 4-venue market comparison (**Pinnacle**, **Polymarket**, **Kalshi**, **Esportsbooks** vs Crowd) |
| [`originated.html`](originated.html) | All `178` originated low-tier regional picks across 10 leagues with `90%` credible intervals & split W–L |
| [`unresolved.html`](unresolved.html) | Dedicated **Unresolved Picks**, **6 Structural Limitations**, and **69 Past-Lock Orphaned Rows** audit |
| [`tournaments.html`](tournaments.html) | Directory of all `27` competitions with region, verified format, match breakdown & official links |
| [`teams.html`](teams.html) | Directory of all `204` competition-scoped LoL team ratings (`θ̂ ± SE`), canonical aliases & split records |
| [`methodology.html`](methodology.html) | Mathematical specification, inline SVG walk-forward reliability curves, `λ` sweep & API architecture |
| [`flagged.html`](flagged.html) | **Flagged for Review** — 8 concrete upstream anomalies, league removals, misbindings & crowd distortions |

---

## Reverse-Engineered Hotspawn Architecture & Automated 4-Hour Refresh

1. **Primary Scheduled LoL Feed:** `GET https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=lol&status=scheduled&tenantId=1`
2. **Full Multi-Sport Lobby Feed:** `GET https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?status=scheduled&tenantId=1`
3. **Angular SSR State & Match Permalinks:** `script#ng-state` on `https://play.hotspawn.com/lol-pickems` and `/lobby` + `/api/v1/admin/gamification/fixtures/permalinks`
4. **Scheduled Automation (`.github/workflows/refresh-picks.yml`):** Runs automatically every **4 hours** (`17 */4 * * *`) plus `workflow_dispatch`, executing live multi-source ingestion (`scripts/refresh.py --fetch-live`), probability origination (`scripts/originate.py`), static HTML generation (`scripts/build.py`), line-by-line validation (`scripts/validate.py`), and `pytest -v`.

---

## Local Quickstart

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Deterministic rebuild + line-by-line HTML & JSON audit
.venv/bin/python scripts/refresh.py

# Run full pytest invariant suite
.venv/bin/pytest -v
```
