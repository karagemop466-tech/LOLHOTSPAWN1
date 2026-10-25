# Final independent audit — session `9b271aa4`

**Checked:** 2026-10-25 15:08 UTC  
**Main baseline:** `554faca` (PR #126, after PR #125's parity/source-verification integration).

## Live dashboard

- [Executive summary](https://karagemop466-tech.github.io/LOLHOTSPAWN1/)
- [All-picks table](https://karagemop466-tech.github.io/LOLHOTSPAWN1/table.html)
- [Card view](https://karagemop466-tech.github.io/LOLHOTSPAWN1/picks.html)
- [Market-backed picks](https://karagemop466-tech.github.io/LOLHOTSPAWN1/featured.html)
- [Model-originated picks](https://karagemop466-tech.github.io/LOLHOTSPAWN1/originated.html)
- [Unresolved picks and limitations](https://karagemop466-tech.github.io/LOLHOTSPAWN1/unresolved.html)
- [Flagged for Review](https://karagemop466-tech.github.io/LOLHOTSPAWN1/flagged.html)
- [Sources and runner probes](https://karagemop466-tech.github.io/LOLHOTSPAWN1/sources.html)
- [Verification page](https://karagemop466-tech.github.io/LOLHOTSPAWN1/verification.html)

GitHub Pages API reports `status: built`; latest build [`1313475860`](https://api.github.com/repos/karagemop466-tech/LOLHOTSPAWN1/pages/builds/1313475860) published `554faca` and completed at 15:03:33Z. The live index/table were fetched after deployment and show the 14:58Z snapshot, 234 fixtures, next kick-offs and links to the complete table and unresolved ledger.

## Coverage and refresh

- Canonical `data/matches.json`: generated `2026-10-25T14:58:31Z`; Hotspawn inventory fetched `14:56:39Z`; **234** fixtures across **29** competitions.
- Methods: **9 market-backed**, **150 model-originated**, **71 provisional**, **4 settlement-only**. Thus 230 have a competitive probability; four forfeiture/disqualification rows intentionally have no probability.
- Secondary Node snapshot: generated `2026-10-25T14:56:04.739Z`, Hotspawn feed fetched `14:55:57.349Z`; 234 scheduled rows, 157 active, 77 stale. `docs/data/canonical_snapshot.json` records the exact root capture used by the companion.
- Latest successful refreshes: [`refresh-picks` run 40204523315](https://github.com/karagemop466-tech/LOLHOTSPAWN1/actions/runs/40204523315) and [`refresh-docs` run 40204523291](https://github.com/karagemop466-tech/LOLHOTSPAWN1/actions/runs/40204523291). Both schedules are every six hours, best-effort rather than a live-odds SLA.
- The live Hotspawn feed and canonical inventory reconcile **234/234 IDs**. Hotspawn crowd percentages, tiers and offered points are not probability inputs.

## Verification on the merged tree

An isolated check on `main` at `554faca` reported:

| Check | Result |
|---|---|
| Python unit tests | **139/139 pass** |
| Canonical `tools/verify.py` | **57/57 publish gates pass** |
| `audit/mobile_audit.py` | **Pass**, all 14 canonical pages |
| `audit/check_site.py` | **24 pages, 0 failures, 0 warnings** |
| `audit/verify_docs.py` | **All checks pass**, 234 scheduled rows rendered 1:1 |
| `audit/verify_docs_parity.py` | **10/10 pass** against the persisted canonical-snapshot receipt |
| `audit/verify_independent.py` | **234 rows, 9 market rows, 50 venue checks, 0 failures / warnings** |
| Independent row/table audits | **234/234 rows**, 0 problems and 0 CSV mismatches |
| Secondary pipeline contract | **Pass**; 234 scheduled, 9 market rows, 50 venue quotes, OOS Brier 0.225 |

## External lines and limitations

- Current price feeds include Pinnacle, Bovada, Unibet/Kambi, Kalshi, Polymarket and Smarkets; quotes, capture times and provider links are shown on the [market page](https://karagemop466-tech.github.io/LOLHOTSPAWN1/featured.html) and match rows.
- Only 9 of 234 fixtures have external market prices in this snapshot. The low-tier remainder uses documented Elo estimates; 71 thin-history estimates are provisional and flagged.
- Four Komplettligaen disqualification/forfeit rows show an administrative side only, with no competitive percentage. Hotspawn's published rule says forfeited predictions are void, so these settlement sides are conditional.
- Research is published in [`research/LINE_SEARCH_2026-10-25.md`](../../research/LINE_SEARCH_2026-10-25.md), [`research/low-tier-sources-2026-10-24.md`](../../research/low-tier-sources-2026-10-24.md), [`research/external-lines-2026-10-25.md`](../../research/external-lines-2026-10-25.md), and on the [Sources](https://karagemop466-tech.github.io/LOLHOTSPAWN1/sources.html) / [Unresolved](https://karagemop466-tech.github.io/LOLHOTSPAWN1/unresolved.html) pages. The runner's 23 long-tail endpoints yielded no machine-readable price; manual checks keep dated venue readings and source links. Blocked/empty prices are never filled in.
- Leaguepedia match history is community-maintained, not an official league-result authority. The site labels this provenance. The secondary view is a companion audit; it does not replace or average the canonical pick.

## Integration decisions

- **R1 / parity:** PR [#125](https://github.com/karagemop466-tech/LOLHOTSPAWN1/pull/125) implemented `docs/data/canonical_snapshot.json` and refresh-workflow synchronization. A local alternative manifest prototype from this session was withdrawn before final integration to avoid duplicate code.
- **R2 / duplicate anchors:** fixed by PRs [#119](https://github.com/karagemop466-tech/LOLHOTSPAWN1/pull/119) and [#120](https://github.com/karagemop466-tech/LOLHOTSPAWN1/pull/120); current site check is green.
- **Kalshi provenance:** PR #125 added the audited “Rising Bees” alias and midpoint verification. The final independent audit reproduces the `#1079080` quote from raw bid/ask data and passes 50 venue checks; no pick or quote was changed in this session.
- Verify-bot branch commits `91d6bb5` / `e214e7e` were based on older generated files; the final close-out retains main's newer source receipts and 14:58Z data snapshot.

PR #105 is the final audit/coordination close-out and remains open while it is updated to current main, CI rerun, and its merge/Pages result recorded.
