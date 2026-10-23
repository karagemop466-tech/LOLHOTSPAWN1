# Research receipts (not part of the published pipeline)

This folder documents *how* the external betting lines were sourced and what could not be
sourced. It is evidence for the Sources page and for manual review; nothing here is
executed by the six-hour refresh.

| File | What it is |
|---|---|
| `probe_sources_runner.py` | Probes 32 candidate LoL odds endpoints from the runner; writes `data/source_probes.json`. |
| `probe_deep.py` | Checks whether the HTML pages that answered 200 embed prices in a hydration blob; writes `probe_deep.json`. |
| `market_ceiling.py` | Enumerates every LoL league on Pinnacle plus the Kalshi and Polymarket LoL inventory to measure the real external-market ceiling; writes `market_ceiling.json`. |
| `bovada_full.py` | Compares the filtered and unfiltered Bovada coupons to see whether extra LoL match moneylines exist; writes `bovada_full.json`. |
| `build_dossier.py` | Renders `SOURCES.md` from the JSON receipts above (no hand-typed numbers). |
| `audit.py` | Independent line-by-line audit of `data/matches.json` (inventory, probabilities, Elo reproduction, de-vig consensus, provenance, quarantine claims, CSV mirror); writes `AUDIT.json`. |
| `SOURCES.md` | The readable dossier: every venue tried, its HTTP verdict, and what it means. |
| `AUDIT.json` | Latest audit result. |

Regenerate:

```bash
python3 research/build_dossier.py   # needs the JSON receipts
python3 research/audit.py           # needs the committed data snapshot
```

The three `*-trigger` files exist only to fire the research-only GitHub workflows by path
push; they carry a timestamp and nothing else.
