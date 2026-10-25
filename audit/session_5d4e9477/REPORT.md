# Independent verification and source audit — session `5d4e9477`

**Audit time:** 2026-10-25 15:03 UTC
**Canonical snapshot audited:** generated `2026-10-25T14:58:31Z`; Hotspawn inventory fetched `2026-10-25T14:56:39Z`; 234 fixtures.
**Main tree:** `554faca` (after PR #126 / Smarkets and the latest refresh).
**Live dashboard:** <https://karagemop466-tech.github.io/LOLHOTSPAWN1/>
**Latest Pages build:** run `40205095579`, built successfully at 15:03:07Z for `main` @ `554faca`.

## Executive result

The canonical root dashboard covers the current Hotspawn LoL inventory **234/234**. The row-level audit compares every published ID with the runner's raw Hotspawn response; finds **234 table rows, 234 pick cards, and 234 CSV rows**; and confirms that every table row links to its exact Hotspawn match card. CSV picks, method, start time, source URL and probabilities match the dataset. There are **230 probability lines** (9 market, 150 model, 71 provisional) and **4 administrative settlements without probabilities**. Those four are forfeits, not forecast probabilities; Hotspawn's published rule says forfeited Pick'ems are void.

The six-hour refresh pipeline has published fresh rows: the current inventory was fetched at `14:56:39Z` and regenerated at `14:58:31Z`. A cache-busted fetch of the live landing page at about 15:04Z showed a 14:58 snapshot, 234 cards, next-kickoff shortcuts, source-linked pick-table links, a separate unresolved section and the phone quick-nav. Pages is currently built. PR #126 added Smarkets as a sixth market venue; the current 9 match-market rows cover 8 Worlds fixtures plus LGC #1079080. Smarkets' captured quotes are on Worlds, not the low-tier tail.

## Line-by-line row verification

See **[`ROWS.md`](ROWS.md)** for a source-linked row for every fixture and **[`rows.json`](rows.json)** for machine-readable results. Re-run with:

```bash
python3 audit/session_5d4e9477/verify_rows.py
```

Results on the 14:58:31Z canonical snapshot:

- Raw Hotspawn feed IDs = dataset IDs = table rows = pick cards = CSV rows = **234**.
- **234/234** rows link to their exact Hotspawn match card; **234/234** table rows have source links; **234/234** cards render on `picks.html`.
- **230/230** probability rows have finite p0/p1 that sum to 100% within the project tolerance. Picks match the higher-probability side where there is a strict edge. Four official-forfeit settlements have both probabilities blank and cite the settlement source.
- Market rows link to venue quote URLs. Model/provisional rows link to Leaguepedia results and publish an Elo basis. CSV pick, probabilities, method, start time and Hotspawn URL are checked against the dataset.
- The row audit returned **0 structural, source-link or arithmetic errors**. It separately identifies **six rows displayed as 50.0% / 50.0% that still name a side**; these are review findings, not a supported favourite (see below).

## Verification gates

Executed locally on the post-PR-#126 tree and 14:58Z snapshot:

| Check | Result |
|---|---|
| Unit tests | **139/139 pass** |
| `tools/verify.py` | **57/57 pass** |
| `audit/verify_independent.py` | 234 rows, 9 market rows, 50 venue checks; **0 failures, 0 warnings** |
| `audit/live_source_verify.py` (run `40204533849` on this session branch) | **FAIL — Smarkets event-page checks**: 8/50 venue receipt URLs returned 401/403 from the runner, 9 were rate-limited, and 32 resolved. All 234 Hotspawn cards and 29 Leaguepedia pages resolved; 234/234 rows still had at least one resolving evidence link. The separate Smarkets quote API endpoint is readable, but the market rows link to event pages. See `audit/session_c0a05820/source_verify.json`. |
| `audit/mobile_audit.py` | **PASS across all 14 root pages** (viewport, fixed-width/360px, table wrappers and labels, bottom nav, summary links) |
| `audit/verify_docs.py` | **ALL DOCS CHECKS PASS** |
| `audit/verify_docs_parity.py` | **10/10 pass**; 234 canonical/secondary fixtures are shared, quote differences are disclosed, and internal anchors resolve |
| `node audit/session_6669f798/test_node_pipeline.mjs` | **PASS** (234 scheduled, 9 market rows, 50 venue quotes joined) |
| `audit/check_site.py` | **24 pages, 0 failures, 0 warnings**. The duplicate “Starting soon” IDs previously observed were removed in PR #119 before the 14:58 snapshot. |

An earlier independent run of `audit/verify_independent.py` returned a false negative for Kalshi's `Rising Bees` short label. After PR #122 added the source-specific alias, the independent raw-payload audit reproduced the Kalshi bid/ask midpoint and passed. This session made no code change for that issue.

## Mobile and pick findability

The live landing page puts the executive summary first, with a large link to the complete pick table, a next-24-hours shortcut, tournament filters and direct links to the card, results, market, model and unresolved views. The table presents kick-off, both probabilities, the selected side, method and row sources. A fixed mobile quick-nav appears on the bottom of each page. The static mobile audit passes all 14 canonical pages; the live root/table/unresolved pages were also fetched after deployment.

## External line research and current coverage

The source-linked receipts and calculations are in **[`LOW_TIER_LINE_CHECK_2026-10-25.md`](../../research/session_5d4e9477/LOW_TIER_LINE_CHECK_2026-10-25.md)** and its JSON companion. The current production market row for LGC Rising fixture **#1079080** is a **2-venue Polymarket + Kalshi consensus**, currently **37.45% Mental Rush / 62.55% Vitality Rising Bees**. A direct Thunderpick board was independently read at about 14:28Z (`+162` Mental Rush / `-238` Vitality Rising Bees), which de-vigs to **35.15% / 64.85%** and supports the same side. That manual observation is corroboration only; it is not a runner-collected venue and does not set the row's probability. BMBETS also captured a multi-book comparison price for this LGC match; it is explicitly attributed to the aggregator.

PR #122 added a third-party BMBETS comparison capture for **#1081423 Ground Zero Gaming vs Frank Esports** and an EsportsInsider/PandaScore odds-comparison figure for **#1081421 FENNEL vs Nothin'Here**. The 4-book BMBETS capture for #1081423 lists Ground Zero-favoring prices; one captured pair (`1.03 / 9.10`) de-vigs to **89.83% Ground Zero**. The current originated row instead selects Frank Esports at 75.25%, so this remains a large flagged conflict, not a production market price. BMBETS is a comparison portal—not four independently fetched first-party book pages—and a later BMBETS fetch in this session did not render its prices. EGamersWorld's direct #1081423 page at approximately 14:28Z showed the symmetric `1.80 / 1.80` placeholder. Those source states are not silently reconciled.

Most national/academy fixtures remain without a runner-readable book line; their rows remain labelled model/provisional estimates from community-maintained Leaguepedia results, not official Riot win probabilities. The site and source docs disclose this ceiling, the runner-side venue probes, the thin history, and the distinction between first-party market captures and manual aggregator observations.

## Review findings / cross-scope requests

1. **Six displayed ties remain on current main:** #1053095 (49.96/50.04 rounds to 50.0/50.0), #1082002 (49.99/50.01 rounds to 50.0/50.0), and exact 50/50 rows #1081369, #1082003, #1082005, #1082006. Each currently names a team; the side selection is not a demonstrated edge. PR #102's branch proposes explicit no-pick handling for ties, but it should be checked against the refreshed #1053095 row as well.
2. **#1081423 high-severity price conflict:** main shows a Frank Esports Elo pick at 75.25%; a BMBETS comparison capture lists four named book offers favoring Ground Zero. The BMBETS capture is not a direct first-party page observation. The EGamersWorld page currently showed a placeholder in our later read. Keep the discrepancy and provenance limits visible; do not silently overwrite either the model or the receipt.
3. **Liquidity disclosure for #1079080:** the 2-venue consensus is labelled high confidence, but `market.total_volume_usd` records Polymarket's `$58.47` only and the committed Kalshi raw payload has null volume fields. PR #122's separate research memo reports Kalshi volume and Polymarket CLOB liquidity, but those metrics are not carried into the canonical row. Two source venues should not be mistaken for a single aggregated liquidity figure.
4. **BMBETS probability wording:** the merged PR #122 memo says the four named sportsbook prices are all around `90.6%–91.2%`. Proportional de-vig of the recorded bet365 `1.03/9.10` pair gives **89.83%**, while the other three pairs give approximately 90.57%–91.15%. The summary range should include the bet365 result (about 89.8%–91.2%). The underlying calculation in this audit is linked and reproducible.
5. **Smarkets manual review links:** PR #126 added Smarkets as a sixth market venue. The raw Smarkets API payload reproduces the stored probabilities and the independent market audit passes, but the published Smarkets event-page URLs were not resolved by the live-source runner (8/50 venue URLs received 401/403). Two manually opened event pages displayed “No data available for the selected contracts” alongside percentages, while their public `/v3/markets/{id}/quotes/` endpoints returned order-book JSON. Request to the PR #126 owner: expose a first-party quote API URL alongside the event page or document the page-vs-API limitation, and teach the live-source check not to call a temporarily inaccessible event page a valid human-review link without qualification.

This session edited only new files under `audit/session_5d4e9477/` and `research/session_5d4e9477/`, plus its own coordination record. It did not change another session's model, site generator, raw payload, shared source receipt or generated production page. It did not change another session's model, site generator, raw payload, shared source receipt or generated production page.
