# Live source verification

- generated: `2026-10-24T16:40:08Z`
- dataset: `2026-10-24T16:36:17Z`
- rows: **241**
- result: **FAIL**

| Check | Result | Detail |
|---|---|---|
| every row carries a Hotspawn match card URL | PASS | 241/241 |
| priced rows sum to 100% (0.2pp) | PASS | [] |
| pick is the higher-probability side (ties may take either side) | PASS | [] |
| every row names a pick (priced or settlement/void) | PASS | 241/241 |
| published inventory == live Hotspawn feed (1:1 ids, freshness) | PASS | live=241 dataset=241 new on feed since publish=0 gone from feed=0 |
| no broken hotspawn card URL | FAIL | 0/241 resolved this run; causes={'auth_required': 241} |
| no broken market quote URL | PASS | 10/10 resolved this run; causes={'resolved': 10} |
| no broken venue receipt URL | PASS | 33/41 resolved this run; causes={'resolved': 33, 'rate_limited': 8} |
| no broken leaguepedia page URL | FAIL | 0/29 resolved this run; causes={'blocked_by_wiki': 29} |
| no broken pickem URL | PASS | 1/1 resolved this run; causes={'resolved': 1} |
| every row has at least one resolving piece of evidence (no broken links) | FAIL | 9/241 rows; 0 unverified this run (throttle/expiry) |
| every published dashboard page resolves | PASS | 13/13 HTTP 2xx |
| table.html renders at least one row per match | PASS | rendered=241 rows=241 |

## Resolution by evidence role

| Role | URLs | Resolved | Causes |
|---|---|---|---|
| hotspawn_card | 241 | 0 | `{'auth_required': 241}` |
| market_quote | 10 | 10 | `{'resolved': 10}` |
| venue_receipt | 41 | 33 | `{'resolved': 33, 'rate_limited': 8}` |
| leaguepedia_page | 29 | 0 | `{'blocked_by_wiki': 29}` |
| pickem | 1 | 1 | `{'resolved': 1}` |

## Rows whose evidence is actually broken

- `1053095` Mind Blue eSports vs LAST DANCE (model) - causes `['auth_required']`
- `1053096` Nameless vs BiPOLAR (model) - causes `['auth_required']`
- `1066214` Epic Avalanche vs Finnish Red Mafia (model) - causes `['auth_required']`
- `1053111` Team VS Esport vs GALA Esports (model) - causes `['auth_required']`
- `1071584` P11 Esports vs HANGMEN (model) - causes `['auth_required']`
- `1070209` Triforce Esport vs Venus (model) - causes `['auth_required']`
- `1070210` GALA Esports vs The Bandits Academy (model) - causes `['auth_required']`
- `1069849` Docta Esports Club vs Viktus (model) - causes `['auth_required']`
- `1071167` DMG Esports Norway vs Playwell Rød Q (model) - causes `['auth_required']`
- `1071170` Solid Gaming vs VES Japan (unresolved) - causes `['auth_required']`
- `1071168` Mixlag fra Trondheim vs CNG Royal (model) - causes `['auth_required']`
- `1061779` Frost Tails vs LAST DANCE (model) - causes `['auth_required']`
- `1069680` Team VS Esport vs Les Ravagés (model) - causes `['auth_required']`
- `1069857` Marere Academy vs Torin (provisional) - causes `['auth_required']`
- `1073030` Invictus Team vs Smoke Tram Ascension (provisional) - causes `['auth_required']`
- `1053536` LANdits vs Frites Esports Club (provisional) - causes `['auth_required']`
- `1069681` The Bandits Academy vs Triforce Esport (model) - causes `['auth_required']`
- `1073172` Lund Esports Organization vs Karolinerna Black (model) - causes `['auth_required']`
- `1070823` Dziady cz.67 vs Adam West Corp (model) - causes `['auth_required']`
- `1073177` Karolinerna Black vs Lundqvist Lightside (model) - causes `['auth_required']`
- `1074627` Northern Wolves Esports vs Lundqvist Darkside (provisional) - causes `['auth_required']`
- `1075850` EXILE esports Academy vs Mighty Eagles (model) - causes `['auth_required']`
- `1077722` Chuds vs Smá Nibu (provisional) - causes `['auth_required']`
- `1077723` Fenrir vs Grísirnir (model) - causes `['auth_required']`
- `1077724` Rift Runners vs Whisky (provisional) - causes `['auth_required']`
- `1076564` Triforce Esport vs RED OUAT (model) - causes `['auth_required']`
- `1076565` Les Ravagés vs Nameless (model) - causes `['auth_required']`
- `1071200` Solid Gaming vs Playwell Rød Q (unresolved) - causes `['auth_required']`
- `1073183` Team Lucidity Esports vs Lund Esports Organization (model) - causes `['auth_required']`
- `1077726` Fenrir vs Cool Beans Team (model) - causes `['auth_required']`
- `1077727` Rift Runners vs Grísirnir (provisional) - causes `['auth_required']`
- `1077728` Whisky vs Smá Nibu (provisional) - causes `['auth_required']`
- `1076566` Team VS Esport vs Meavedron Benelux (model) - causes `['auth_required']`
- `1077729` Chuds vs Cool Beans Team (provisional) - causes `['auth_required']`
- `1077730` Rift Runners vs Fenrir (provisional) - causes `['auth_required']`
- `1077731` Smá Nibu vs Grísirnir (provisional) - causes `['auth_required']`
- `1079556` Team Lucidity Esports vs Lund Esports Organization (model) - causes `['auth_required']`
- `1073186` OnlyWinByFF vs B2U (model) - causes `['auth_required']`
- `1073184` Karolinerna vs Crazy Kittens E-Sport Academy (provisional) - causes `['auth_required']`
- `1079321` NextGeneration Esports vs Slam Dunk (provisional) - causes `['auth_required']`
- `1071206` Volda E-Sport vs Solid Gaming (unresolved) - causes `['auth_required']`
- `1074636` 2 Massive vs Team Lucidity Esports (model) - causes `['auth_required']`
- `1074642` Northern Wolves Esports vs B2U (provisional) - causes `['auth_required']`
- `1074643` Team cd vs Karolinerna (model) - causes `['auth_required']`
- `1074639` Lund Esports Organization OGs vs Turbo Gaming (provisional) - causes `['auth_required']`
- `1074640` Lundqvist Darkside vs DMG Esports Sweden (model) - causes `['auth_required']`
- `1077744` Rift Runners vs Cool Beans Team (model) - causes `['auth_required']`
- `1077745` Smá Nibu vs Fenrir (model) - causes `['auth_required']`
- `1077746` Whisky vs Chuds (model) - causes `['auth_required']`
- `1071186` Solid Gaming vs NTNUI Kometkameratene (unresolved) - causes `['auth_required']`
- `1076570` Meavedron Benelux vs The Bandits Academy (model) - causes `['auth_required']`
- `1076571` Nameless vs Triforce Esport (model) - causes `['auth_required']`
- `1081365` Arena vs TeamBah (provisional) - causes `['auth_required']`
- `1081369` Inquisitors vs OverPower (provisional) - causes `['auth_required']`
- `1079132` Void Walkers vs Pegasus Esports (provisional) - causes `['auth_required']`
- `1079922` Fritt Fall vs Tung Sahur Mid (provisional) - causes `['auth_required']`
- `1082001` Syrian Rift Masters vs B7 (provisional) - causes `['auth_required']`
- `1082002` DELETED vs S7raa (provisional) - causes `['auth_required']`
- `1082003` Levelers vs Team Fifty Fifty (provisional) - causes `['auth_required']`
- `1082004` MTN ESPORTS TEAM vs RATCLUB (provisional) - causes `['auth_required']`
- `1082005` SYR T1 vs Ravagers (provisional) - causes `['auth_required']`
- `1082006` X-Funkass vs التريس (provisional) - causes `['auth_required']`
- `1081079` Docta Esports Club vs BaronX (model) - causes `['auth_required']`
- `1082061` Glorp Cat vs Impel (provisional) - causes `['auth_required']`
- `1082105` Team VDS vs Pegasus Esports (model) - causes `['auth_required']`
- `1083096` Keep Yourself Positive vs CRUEL FATE (provisional) - causes `['auth_required']`
- `1083097` paiN Gaming vs Non-toxic Gaming (provisional) - causes `['auth_required']`
- `1083098` TUPKACHI NA KORICI vs FAME (provisional) - causes `['auth_required']`
- `1083105` КАПИБАРА vs Ultim8 (provisional) - causes `['auth_required']`
- `1075719` Berlin 5 vs AceGaming Hearts (model) - causes `['auth_required']`
- `1081085` BaronX vs Marere Academy (model) - causes `['auth_required']`
- `1081086` Final Level eSports Academy vs Infinity Gaming (model) - causes `['auth_required']`
- `1080923` Jendouba Esports vs Enfida Esports (provisional) - causes `['auth_required']`
- `1080924` JSK Esports vs El Menzah Esports (provisional) - causes `['auth_required']`
- `1080925` Olympique Mnihla vs Supreme Leaders (provisional) - causes `['auth_required']`
- `1080926` Simplicity Gaming vs JSK Academy (model) - causes `['auth_required']`
- `1080927` Zahrouni Esports vs Olympique Mnihla Academy (provisional) - causes `['auth_required']`
- `1074655` Karolinerna vs Turbo Gaming (model) - causes `['auth_required']`
- `1074657` OnlyWinByFF vs Rich Gang Sweden (model) - causes `['auth_required']`
- `1074658` Team cd vs Tung Sahur Mid (provisional) - causes `['auth_required']`
- `1074659` Team Lucidity Esports vs Fritt Fall (model) - causes `['auth_required']`
- `1075731` Whalepower Humpbacks vs 1. Esport Club Frankfurt e.V. (model) - causes `['auth_required']`
- `1079141` JSK Academy vs New Era Team (model) - causes `['auth_required']`
- `1079142` Void Walkers vs Slam Dunk (provisional) - causes `['auth_required']`
- `1082914` Clã NKZ VÓRAX vs Neon eSports (model) - causes `['auth_required']`
- `1082915` LØS Academy vs Marere E-Sports (model) - causes `['auth_required']`
- `1081083` Docta Esports Club vs Clã NKZ Revengers (model) - causes `['auth_required']`
- `1081084` Maze GG vs Viktus (model) - causes `['auth_required']`
- `1079027` Babos Gaming vs Hannover Esports e.V. (model) - causes `['auth_required']`
- `1079028` Reveal Multigaming vs AceGaming (model) - causes `['auth_required']`
- `1075747` AceGaming Hearts vs Emperors Bremen (provisional) - causes `['auth_required']`
- `1075748` AIX eSports vs MT1 Vision (model) - causes `['auth_required']`
- `1075752` Defiance eSports vs REH Gaming (provisional) - causes `['auth_required']`
- `1075753` Duplex Silva Pigeons Edition vs Sissi State Punks (model) - causes `['auth_required']`
- `1075754` Eintracht Spandau Zwei vs Team 300 White (model) - causes `['auth_required']`
- `1075755` Neko Elite Kittens vs spongecord prime (model) - causes `['auth_required']`
- `1075758` Rich Gang vs LOOKSMAXXER (model) - causes `['auth_required']`
- `1075761` Whalepower Humpbacks vs Socken und Sandalen (provisional) - causes `['auth_required']`
- `1075750` Black Lion vs Glacial Guardians (model) - causes `['auth_required']`
- `1075759` Second Time Alive Revival vs Berlin 5 (model) - causes `['auth_required']`
- `1080928` JSK Esports vs Enfida Esports (model) - causes `['auth_required']`
- `1080929` Olympique Mnihla vs Jendouba Esports (provisional) - causes `['auth_required']`
- `1080930` Olympique Mnihla Academy vs El Menzah Esports (provisional) - causes `['auth_required']`
- `1080931` Simplicity Gaming vs Supreme Leaders (provisional) - causes `['auth_required']`
- `1080932` Zahrouni Esports vs JSK Academy (provisional) - causes `['auth_required']`
- `1074660` 2 Massive vs Tung Sahur Mid (provisional) - causes `['auth_required']`
- `1074664` OnlyWinByFF vs Mazepa (model) - causes `['auth_required']`
- `1074666` Team Lucidity Esports vs Team cd (model) - causes `['auth_required']`
- `1075751` BlackDivision vs Kanji Esports KIN (provisional) - causes `['auth_required']`
- `1079029` 404 Multigaming e.V. vs VfB eSports (model) - causes `['auth_required']`
- `1079030` Locked IN vs DKB XPERION NXT (model) - causes `['auth_required']`
- `1074663` Lundqvist Darkside vs B2U (model) - causes `['auth_required']`
- `1082938` Mazepa vs B2U (model) - causes `['auth_required']`
- `1081700` Inari Esports vs Bulldog Esports (model) - causes `['auth_required']`
- `1081831` Lund Esports Organization OGs vs Tung Sahur Mid (provisional) - causes `['auth_required']`
- `1075756` Packmiko E-Sports DACH vs Atruvia Münster Esports (model) - causes `['auth_required']`
- `1079031` DKB XPERION NXT vs Phong Vũ Buffalo (model) - causes `['auth_required']`
- `1079032` No Need Orga vs AceGaming (model) - causes `['auth_required']`
- `1083162` Karolinerna vs Turbo Gaming (model) - causes `['auth_required']`
- `1079033` Hannover Esports e.V. vs No Need Orga (model) - causes `['auth_required']`
- `1079034` VfB eSports vs regnum4games (model) - causes `['auth_required']`
- `1083035` FlameHard vs B2U (model) - causes `['auth_required']`
- `1082615` DMG Esports Sweden vs Northern Wolves Esports (model) - causes `['auth_required']`
- `1082616` Lundqvist Darkside vs Mazepa (model) - causes `['auth_required']`
- `1075734` Atruvia Münster Esports vs Defiance eSports (model) - causes `['auth_required']`
- `1079144` Slam Dunk vs New Era Team (provisional) - causes `['auth_required']`
- `1075749` Babos Gaming Academy vs VfB x Engines Stuttgart (model) - causes `['auth_required']`
- `1075737` Purple Emperor Lizards - Atomic vs Cloud eSport (model) - causes `['auth_required']`
- `1081701` Crownless vs Absolved (model) - causes `['auth_required']`
- `1079145` Pegasus Esports vs JSK Academy (model) - causes `['auth_required']`
- `1083039` Playwell Rød Q vs Your Saviours (model) - causes `['auth_required']`
- `1083040` VES Japan vs Rich Gang (model) - causes `['auth_required']`
- `1083041` Volda E-Sport vs Ascent Gaming (model) - causes `['auth_required']`
- `1079036` Reveal Multigaming vs Team 300 (model) - causes `['auth_required']`
- `1079851` AceGaming vs reGOLD eSport (model) - causes `['auth_required']`
- `1079147` Team Reds vs NextGeneration Esports (model) - causes `['auth_required']`
- `1079037` DKB XPERION NXT vs regnum4games (model) - causes `['auth_required']`
- `1079038` VfB eSports vs Phong Vũ Buffalo (model) - causes `['auth_required']`
- `1080933` JSK Academy vs Supreme Leaders (provisional) - causes `['auth_required']`
- `1080934` JSK Esports vs Olympique Mnihla (model) - causes `['auth_required']`
- `1080935` Olympique Mnihla Academy vs Enfida Esports (provisional) - causes `['auth_required']`
- `1080936` Simplicity Gaming vs Jendouba Esports (provisional) - causes `['auth_required']`
- `1080937` Zahrouni Esports vs El Menzah Esports (provisional) - causes `['auth_required']`
- `1082107` Void Walkers vs Team VDS (model) - causes `['auth_required']`
- `1079039` Babos Gaming vs No Need Orga (model) - causes `['auth_required']`
- `1079040` Team 300 vs Hannover Esports e.V. (model) - causes `['auth_required']`
- `1075762` 1. Esport Club Frankfurt e.V. vs Rich Gang (model) - causes `['auth_required']`
- `1075763` Berlin 5 vs Sissi State Punks (model) - causes `['auth_required']`
- `1075764` Black Lion vs BlackDivision (provisional) - causes `['auth_required']`
- `1075765` Cloud eSport vs Defiance eSports (model) - causes `['auth_required']`
- `1075766` Eintracht Spandau Zwei vs TeamOrangeGaming Academy (model) - causes `['auth_required']`
- `1075767` Emperors Bremen vs Neko Elite Kittens (provisional) - causes `['auth_required']`
- `1075768` Glacial Guardians vs MT1 Vision (model) - causes `['auth_required']`
- `1075769` REH Gaming vs Kanji Esports AKA (provisional) - causes `['auth_required']`
- `1075770` Kanji Esports KIN vs Babos Gaming Academy (model) - causes `['auth_required']`
- `1075771` LOOKSMAXXER vs Whalepower Humpbacks (model) - causes `['auth_required']`
- `1075772` Purple Emperor Lizards - Atomic vs Packmiko E-Sports DACH (model) - causes `['auth_required']`
- `1075773` Second Time Alive Revival vs AceGaming Hearts (model) - causes `['auth_required']`
- `1075774` spongecord prime vs Duplex Silva Pigeons Edition (model) - causes `['auth_required']`
- `1075775` Team 300 White vs Socken und Sandalen (provisional) - causes `['auth_required']`
- `1075776` VfB x Engines Stuttgart vs AIX eSports (model) - causes `['auth_required']`
- `1082748` DMG Esports Sweden vs FlameHard (model) - causes `['auth_required']`
- `1080938` El Menzah Esports vs Enfida Esports (provisional) - causes `['auth_required']`
- `1080939` JSK Academy vs Jendouba Esports (provisional) - causes `['auth_required']`
- `1080940` Olympique Mnihla Academy vs Olympique Mnihla (provisional) - causes `['auth_required']`
- `1080941` Simplicity Gaming vs JSK Esports (model) - causes `['auth_required']`
- `1080942` Zahrouni Esports vs Supreme Leaders (provisional) - causes `['auth_required']`
- `1083036` Karolinerna vs Lund Esports Organization OGs (provisional) - causes `['auth_required']`
- `1083037` Rich Gang Sweden vs Northern Wolves Esports (model) - causes `['auth_required']`
- `1079041` MT1 Esports vs Locked IN (model) - causes `['auth_required']`
- `1079042` The Bandits Prime vs 404 Multigaming e.V. (model) - causes `['auth_required']`
- `1081702` Ruddy Ultras vs Rich Gang UK (model) - causes `['auth_required']`
- `1079043` BvP vs No Need Orga (provisional) - causes `['auth_required']`
- `1082746` Phong Vũ Buffalo vs 404 Multigaming e.V. (model) - causes `['auth_required']`
- `1083038` 2 Massive vs Lund Esports Organization OGs (provisional) - causes `['auth_required']`
- `1079045` MT1 Esports vs DKB XPERION NXT (model) - causes `['auth_required']`
- `1079046` regnum4games vs The Bandits Prime (model) - causes `['auth_required']`
- `1081703` Brod n Friends vs PNS (model) - causes `['auth_required']`
- `1079047` 404 Multigaming e.V. vs DKB XPERION NXT (model) - causes `['auth_required']`
- `1079048` Locked IN vs VfB eSports (model) - causes `['auth_required']`
- `1079049` BvP vs Babos Gaming (provisional) - causes `['auth_required']`
- `1079050` Team 300 vs AceGaming (model) - causes `['auth_required']`
- `1080943` El Menzah Esports vs Olympique Mnihla (provisional) - causes `['auth_required']`
- `1080944` JSK Academy vs JSK Esports (model) - causes `['auth_required']`
- `1080945` Olympique Mnihla Academy vs Simplicity Gaming (provisional) - causes `['auth_required']`
- `1080946` Supreme Leaders vs Jendouba Esports (provisional) - causes `['auth_required']`
- `1080947` Zahrouni Esports vs Enfida Esports (provisional) - causes `['auth_required']`
- `1079051` AceGaming vs BvP (provisional) - causes `['auth_required']`
- `1079852` reGOLD eSport vs Babos Gaming (model) - causes `['auth_required']`
- `1075777` AIX eSports vs BlackDivision (provisional) - causes `['auth_required']`
- `1075778` Babos Gaming Academy vs Glacial Guardians (model) - causes `['auth_required']`
- `1075779` Defiance eSports vs Kanji Esports AKA (model) - causes `['auth_required']`
- `1075780` Duplex Silva Pigeons Edition vs AceGaming Hearts (model) - causes `['auth_required']`
- `1075781` LOOKSMAXXER vs 1. Esport Club Frankfurt e.V. (model) - causes `['auth_required']`
- `1075782` MT1 Vision vs Black Lion (model) - causes `['auth_required']`
- `1075783` Neko Elite Kittens vs Berlin 5 (model) - causes `['auth_required']`
- `1075784` Packmiko E-Sports DACH vs Cloud eSport (model) - causes `['auth_required']`
- `1075785` REH Gaming vs Atruvia Münster Esports (provisional) - causes `['auth_required']`
- `1075786` Rich Gang vs Team 300 White (model) - causes `['auth_required']`
- `1075787` Sissi State Punks vs Second Time Alive Revival (model) - causes `['auth_required']`
- `1075788` Socken und Sandalen vs Eintracht Spandau Zwei (provisional) - causes `['auth_required']`
- `1075789` spongecord prime vs Emperors Bremen (provisional) - causes `['auth_required']`
- `1075790` VfB x Engines Stuttgart vs Kanji Esports KIN (model) - causes `['auth_required']`
- `1075791` Whalepower Humpbacks vs TeamOrangeGaming Academy (model) - causes `['auth_required']`
- `1079053` Phong Vũ Buffalo vs MT1 Esports (model) - causes `['auth_required']`
- `1079054` The Bandits Prime vs VfB eSports (model) - causes `['auth_required']`
- `1081421` FENNEL vs Nothin'Here (model) - causes `['auth_required']`
- `1082007` Saigon Warriors vs Team Gromp (provisional) - causes `['auth_required']`
- `1081423` Ground Zero Gaming vs Frank Esports (model) - causes `['auth_required']`
- `1079055` Locked IN vs 404 Multigaming e.V. (model) - causes `['auth_required']`
- `1079056` MT1 Esports vs The Bandits Prime (model) - causes `['auth_required']`
- `1079057` Phong Vũ Buffalo vs regnum4games (model) - causes `['auth_required']`
- `1079058` VfB eSports vs DKB XPERION NXT (model) - causes `['auth_required']`
- `1075792` AceGaming Hearts vs Sissi State Punks (model) - causes `['auth_required']`
- `1075793` Atruvia Münster Esports vs Kanji Esports AKA (model) - causes `['auth_required']`
- `1075794` Babos Gaming Academy vs AIX eSports (model) - causes `['auth_required']`
- `1075795` Berlin 5 vs Emperors Bremen (provisional) - causes `['auth_required']`
- `1075796` Black Lion vs VfB x Engines Stuttgart (model) - causes `['auth_required']`
- `1075797` BlackDivision vs MT1 Vision (provisional) - causes `['auth_required']`
- `1075798` Defiance eSports vs Purple Emperor Lizards - Atomic (model) - causes `['auth_required']`
- `1075799` Eintracht Spandau Zwei vs LOOKSMAXXER (model) - causes `['auth_required']`
- `1075800` Glacial Guardians vs Kanji Esports KIN (model) - causes `['auth_required']`
- `1075801` Duplex Silva Pigeons Edition vs Neko Elite Kittens (model) - causes `['auth_required']`
- `1075802` REH Gaming vs Cloud eSport (provisional) - causes `['auth_required']`
- `1075803` Rich Gang vs Whalepower Humpbacks (model) - causes `['auth_required']`
- `1075804` Second Time Alive Revival vs spongecord prime (model) - causes `['auth_required']`
- `1075805` Team 300 White vs 1. Esport Club Frankfurt e.V. (model) - causes `['auth_required']`
- `1075806` TeamOrangeGaming Academy vs Socken und Sandalen (provisional) - causes `['auth_required']`
- `1079059` AceGaming vs Hannover Esports e.V. (model) - causes `['auth_required']`
- `1079060` Babos Gaming vs Reveal Multigaming (model) - causes `['auth_required']`
- `1079062` Team 300 vs No Need Orga (model) - causes `['auth_required']`
- `1079853` BvP vs reGOLD eSport (provisional) - causes `['auth_required']`
