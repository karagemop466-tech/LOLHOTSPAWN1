# Published `table.html` vs the dataset — line-by-line re-derivation

* table rows rendered: **241**
* dataset fixtures: **241**
* fixtures matched to a rendered row: **241**
* fixtures with no rendered row: **0**
* problems: **0**
* `picks.csv` rows: **241**, mismatches vs JSON: **0**

Each rendered row is matched to the dataset by its Hotspawn card URL; team names,
both probabilities, the pick, the pick percentage, the method class and the source
links are then re-derived from `data/matches.json` without importing `tools/`.

## Result

All 241 rendered rows reproduce the dataset exactly: probabilities sum to
100.0 %, the pick is the higher-probability side, every row carries its Hotspawn
card link plus at least one further source, and every settlement row claims no
probability. No row is invented and no fixture is missing.
