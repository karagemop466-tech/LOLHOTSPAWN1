# Post-merge publication audit — session `9b271aa4`

**Checked:** 2026-10-25 14:22 UTC  
**Scope:** read-only verification of the merged LoL pick dashboard, data freshness, source links, mobile layout, and GitHub Pages publication. No source data, model, workflow, or generated page was edited.

## Live publication

- **Canonical dashboard:** [Hotspawn LoL Pick Desk](https://karagemop466-tech.github.io/LOLHOTSPAWN1/)
- **One-table picks list:** [Pick table](https://karagemop466-tech.github.io/LOLHOTSPAWN1/table.html)
- **Cards:** [Card view](https://karagemop466-tech.github.io/LOLHOTSPAWN1/picks.html)
- **Market lines:** [Market-backed picks](https://karagemop466-tech.github.io/LOLHOTSPAWN1/featured.html)
- **Model lines:** [Originated picks](https://karagemop466-tech.github.io/LOLHOTSPAWN1/originated.html)
- **Unresolved picks and limitations:** [Unresolved](https://karagemop466-tech.github.io/LOLHOTSPAWN1/unresolved.html)
- **Review items:** [Flagged for Review](https://karagemop466-tech.github.io/LOLHOTSPAWN1/flagged.html)
- **Source inventory:** [Sources](https://karagemop466-tech.github.io/LOLHOTSPAWN1/sources.html)
- **Audit:** [Verification page](https://karagemop466-tech.github.io/LOLHOTSPAWN1/verification.html)

GitHub Pages API reported `status: built`; latest Pages build `1313386237` published commit `84524fd8c028d4aadad75393c1c86f2a99855dd1` and completed at 14:19:20Z. The live summary and pick table were fetched after deployment: both show snapshot `2026-10-25 14:15 UTC`, 234 matches, and links to the per-match sources. The live unresolved page lists the four settlement-only records separately.

The merged work is on `main`: [PR #96](https://github.com/karagemop466-tech/LOLHOTSPAWN1/pull/96) adds complete coverage and the mobile tournament directory; [PR #97](https://github.com/karagemop466-tech/LOLHOTSPAWN1/pull/97) publishes bookmaker evidence; [PR #98](https://github.com/karagemop466-tech/LOLHOTSPAWN1/pull/98) expands the low-tier line search; [PR #99](https://github.com/karagemop466-tech/LOLHOTSPAWN1/pull/99) fixes the time-dependent tests blocking refresh; [PR #100](https://github.com/karagemop466-tech/LOLHOTSPAWN1/pull/100) fixes secondary-view anchors; [PR #101](https://github.com/karagemop466-tech/LOLHOTSPAWN1/pull/101) records the final integration and mobile update.

## Snapshot and coverage

- Canonical `data/matches.json`: generated `2026-10-25T14:15:13Z`; Hotspawn inventory fetched `2026-10-25T14:13:21Z`; **234** fixtures across **29** competitions.
- Canonical methods: **9 market-backed**, **150 model**, **71 provisional**, **4 unresolved/settlement-only**. Thus 230 rows have a probability; the four forfeiture settlements intentionally have no competitive percentage.
- Secondary companion snapshot: generated `2026-10-25T14:15:46.475Z`; Hotspawn feed fetched `14:15:39.076Z`; 234 scheduled rows, 157 active and 77 stale. It is explicitly marked as a companion, not the pick list to submit.
- Canonical refresh run [`40201021751`](https://github.com/karagemop466-tech/LOLHOTSPAWN1/actions/runs/40201021751) produced the 14:15Z root snapshot. Secondary refresh run [`40201363277`](https://github.com/karagemop466-tech/LOLHOTSPAWN1/actions/runs/40201363277) produced the 14:15:46Z companion snapshot.
- Both workflows use six-hour schedules (`refresh.yml`: `17 */6 * * *`; `refresh-docs.yml`: `5 */6 * * *`). This is an automated best-effort schedule, not a live-odds SLA; each page displays its capture time and staleness warning.

The live Hotspawn fixture feed and the canonical inventory reconciled **234/234 IDs**, with no new or missing fixtures during the independent audit. The canonical publish gate verified 1:1 coverage, pick/probability arithmetic, all 29 tournament counts, zero rating look-ahead, source links, unresolved reasons, and phone deep links. Hotspawn crowd-pick percentages, tiers, and offered points are not probability inputs.

## Verification run (isolated copy of commit `84524fd`)

| Check | Result |
|---|---|
| `python3 -m unittest discover -s tests -v` | **88/88 pass** |
| `python3 tools/verify.py` | **51/51 publish gates pass** |
| `python3 audit/mobile_audit.py` | **Pass**, all 14 canonical pages |
| `python3 audit/check_site.py` | **24 pages; 0 failures, 0 warnings** |
| `python3 audit/verify_docs.py` | **All checks pass**; 234 scheduled rows rendered 1:1; 15 companion flags linked |
| `python3 audit/verify_docs_parity.py` | **10/10 pass**; 234 scheduled/shared rows; 227 priced on both views; 33 disclosed divergences; mean gap 2.255 pp, max 18.89 pp |
| `node audit/session_6669f798/test_node_pipeline.mjs` | **Pass**; 234 scheduled, 9 market rows, 42 venue quotes, OOS Brier 0.225 |
| `python3 audit/verify_independent.py` | **234 rows; 9 market rows; 41 venue checks; 0 failures, 0 warnings**; no missing/extra Hotspawn IDs |
| `python3 audit/session_650571cf/verify_rows_vs_table.py` | **234/234** rows re-derived; 0 missing, 0 problems, 0 CSV mismatches |

The live-source audit found source evidence for all 234 rows. Eight old bookmaker-board URLs now return 401/403 because those markets have closed; the site identifies them as historical/closed rather than treating them as current prices. The current build reports 12 of 18 probed feeds reachable.

## Source and limitation boundary

- Inventory: [Hotspawn pick'em lobby](https://play.hotspawn.com/lobby) and its public [scheduled-fixtures feed](https://phpstack-1372681-6459848.cloudwaysapps.com/api/v1/fixtures?sport_alias=lol&status=scheduled&tenantId=1).
- External lines: Pinnacle, Bovada, Unibet/Kambi, Kalshi and Polymarket receipts are linked on the [market page](https://karagemop466-tech.github.io/LOLHOTSPAWN1/featured.html) and per fixture. These are market observations, not official match results.
- Low-tier search evidence: [`research/LINE_SEARCH_2026-10-25.md`](../../research/LINE_SEARCH_2026-10-25.md), [`research/low-tier-sources-2026-10-24.md`](../../research/low-tier-sources-2026-10-24.md), [`research/external-lines-2026-10-25.md`](../../research/external-lines-2026-10-25.md), and the committed [`data/esportsbook_probe.json`](../../data/esportsbook_probe.json). The probes do not invent prices when a venue blocks the runner, serves only HTML, or has an empty market. Only a small tier-one slice had usable external lines; the lower-tier remainder is explicitly model-priced.
- Model results use Leaguepedia match history, which is community-maintained—not an official league result authority. The methodology and every match row identify the source. The 71 thin-history picks are provisional and flagged.
- The four Komplettligaen disqualification/forfeit rows show an administrative winner only, no percentage. Hotspawn's published rule says forfeited predictions are void; therefore that settlement side is conditional and is not presented as a competitive forecast.
- The companion view has 33 model/market divergences versus the canonical view in this snapshot. Each is marked with links to both lines; the site instructs users to use the canonical pick and never averages the two.

## Transient verification issue resolved

On the intermediate root-only refresh (`19dc1a9`), the parity gate caught one stale embedded canonical percentage (`#1053095`) because `docs/` still reflected its 10:57Z snapshot. PR #99 refreshed the secondary snapshot at 14:15:46Z. On the final combined tree, the parity gate passes 10/10 and the live companion page shows the aligned 14:15Z snapshots. A brief Pages `building` state also resolved: the latest Pages API status is `built`, and the live pages were fetched successfully after deployment.
