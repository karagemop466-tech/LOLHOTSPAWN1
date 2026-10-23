# Forfeit / walkover evidence

Audit snapshots behind the `official-forfeit` settlement picks published on
[unresolved.html](../../unresolved.html). These files are evidence only; the live
pipeline re-harvests the same Cargo tables every six hours via `tools/collect.py`
(`MatchSchedule.FF`, `IsNullified` and the Data-page footnotes).

## `komplettligaen_solid.json`

Raw Leaguepedia CargoExport rows (fetched 2026-10-23) for every
`Komplettligaen/2026 Season/Autumn Split` series involving **Solid Gaming**, the
participant removed mid-split (`dqteams=Solid Gaming` on the Data page).

- 11 series in total; the 8 series after the removal carry an `FF` flag
  (`FF=1` = Team1 forfeited, `FF=2` = Team2 forfeited), all scored 0-2,
  `IsNullified=0` (none voided in the official record).
- The 2026-10-18 card carries the footnote
  `[[Solid Gaming]] is removed from the league.`
- The four Solid Gaming cards still listed on Hotspawn map to these records, and
  the publish gate `forfeit settlements agree with Leaguepedia FF records`
  (in `tools/verify.py`, rule `ff_winner_name` in `tools/model.py`) checks the
  mapping on every build:

  | Hotspawn id | Card (Hotspawn order)            | Cargo row FF | Settlement winner        |
  |-------------|----------------------------------|--------------|--------------------------|
  | 1071170     | Solid Gaming vs VES Japan        | FF=1         | VES Japan                |
  | 1071200     | Solid Gaming vs Playwell Rød Q   | FF=1         | Playwell Rød Q           |
  | 1071206     | Volda E-Sport vs Solid Gaming    | FF=2         | Volda E-Sport            |
  | 1071186     | Solid Gaming vs NTNUI Kometkameratene | FF=1    | NTNUI Kometkameratene    |

Per the no-hallucination rule these picks publish **no probability**: Hotspawn may
still void the cards, so a 0-2 administrative default is never presented as a
100% competitive line. The Data page itself is linked from every published
resolution: <https://lol.fandom.com/wiki/Data:Komplettligaen/2026_Season/Autumn_Split>
