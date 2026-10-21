#!/usr/bin/env python3
"""Canonical LoL competition, organizer link, team alias, and administrative ruling registry.

Isolates cross-region homonyms strictly by `(competition_name, participant_name)` so distinct
regional squads sharing organization names (`Rich Gang` NO/DACH/UK/SE/FI, `DMG Esports` NO/SE,
`Invictus`, `Arena`, `OverPower`, `BiPOLAR`, `Last Dance`, `Nameless`, `Venus`, `Fenrir`)
never contaminate one another's ratings or records.
"""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote

LEAGUEPEDIA_WIKI = "https://lol.fandom.com/wiki/"


def wiki_url(title: str) -> str:
    return LEAGUEPEDIA_WIKI + quote(title.replace(" ", "_"), safe="/:()-'.")


def norm_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


# Official non-Leaguepedia primary organizer / league portals per competition
COMPETITION_META: dict[str, dict[str, Any]] = {
    "Worlds 2026 Main Event": {
        "region": "International",
        "circuit": "LoL Esports Tier-1 Global Championship",
        "ecosystem": "Worlds",
        "organizer_name": "Riot Games LoL Esports",
        "organizer_url": "https://lolesports.com/en-US/tournament/113486371866172919/overview",
        "default_format_note": "Swiss Stage Round 1 (Bo1)",
    },
    "EM 2026 Summer Main Event": {
        "region": "EMEA",
        "circuit": "EMEA Masters Tier-2 Championship",
        "ecosystem": "EMEA_ERL",
        "organizer_name": "Riot EMEA / LoL Esports",
        "organizer_url": "https://lolesports.com/",
        "default_format_note": "Grand Final (Bo5)",
    },
    "LCP 2027 Promotion": {
        "region": "APAC (PCS / VCS / LJL / Oceania)",
        "circuit": "League of Legends Championship Pacific Promotion",
        "ecosystem": "LCP",
        "organizer_name": "Riot APAC / LoL Esports",
        "organizer_url": "https://lolesports.com/",
        "default_format_note": "Guest Slot Promotion Series (Bo5)",
    },
    "LGC Rising 2026 Playoffs": {
        "region": "EMEA",
        "circuit": "LoL Game Changers EMEA Rising",
        "ecosystem": "LGC_EMEA",
        "organizer_name": "Riot EMEA / Toornament Circuit",
        "organizer_url": "https://play.toornament.com/en_US/circuits/2466809817314095103",
        "default_format_note": "Grand Finals (Bo5)",
    },
    "PRM 2nd Division 26-27 Fall": {
        "region": "DACH (Germany / Austria / Switzerland)",
        "circuit": "Prime League 2nd Division (Div 2.1 & Div 2.2)",
        "ecosystem": "Prime_League",
        "organizer_name": "Prime League Official Portal",
        "organizer_url": "https://www.primeleague.gg/en/leagues/prm/3227-fall-split-202627",
        "default_format_note": "Regular Season Double Round-Robin (Bo3 Game-Points)",
    },
    "PRM 3rd Division 26-27 Fall": {
        "region": "DACH (Germany / Austria / Switzerland)",
        "circuit": "Prime League 3rd Division (Div 3.1 – Div 3.4)",
        "ecosystem": "Prime_League",
        "organizer_name": "Prime League Official Portal",
        "organizer_url": "https://www.primeleague.gg/en/leagues/prm/3227-fall-split-202627",
        "default_format_note": "Regular Season Group Stage (2-Game Series)",
    },
    "4 Nations 2026 Halloween Heist": {
        "region": "United Kingdom & Ireland",
        "circuit": "UKEL / 4 Nations Off-Season Cup",
        "ecosystem": "UKEL_4Nations",
        "organizer_name": "UK Esports League (UKEL)",
        "organizer_url": "https://www.twitch.tv/theukel",
        "default_format_note": "Group Stage 2 (Bo1 Double Round-Robin)",
    },
    "RIVALS LEAGUE Season 2": {
        "region": "Sweden / Nordics",
        "circuit": "RIVALS League Division 1",
        "ecosystem": "Sweden_National",
        "organizer_name": "RIVALS League Sweden / Challengermode",
        "organizer_url": "https://www.rivalsleague.gg/lol/standings",
        "default_format_note": "Group A & Group B Regular Season (Bo3)",
    },
    "Superstrike League 2026": {
        "region": "Sweden / Nordics",
        "circuit": "Superstrike Swedish National Circuit",
        "ecosystem": "Sweden_National",
        "organizer_name": "Superstrike League",
        "organizer_url": wiki_url("Superstrike League 2026"),
        "default_format_note": "Playoffs (Completed — Stale Hotspawn Rows)",
    },
    "Tunisian Super League 2026": {
        "region": "Tunisia / North Africa (MENA)",
        "circuit": "Tunisian Super League National Division",
        "ecosystem": "MENA_NorthAfrica",
        "organizer_name": "Tunisian Super League",
        "organizer_url": wiki_url("Tunisian Super League/2026 Season"),
        "default_format_note": "Double Round-Robin Regular Season (Bo1)",
    },
    "Arabian League 2nd Division 2026 Summer": {
        "region": "MENA (Arabian Region)",
        "circuit": "Arabian League 2nd Division",
        "ecosystem": "MENA_Arabian",
        "organizer_name": "Riot MENA / Arabian League",
        "organizer_url": wiki_url("Arabian League 2nd Division/2026 Season/Summer Split"),
        "default_format_note": "Regular Season (Bo1 / Bo3)",
    },
    "Arabian Regional Championship 2026: Lebanon-Libya-Syria-Palestine": {
        "region": "Levant & Libya (LB-LY-SY-PS)",
        "circuit": "Arabian Regional Championship Qualifier",
        "ecosystem": "MENA_ARC_Levant",
        "organizer_name": "Arabian Regional Championship",
        "organizer_url": wiki_url("Arabian Regional Championship 2026/Qualifiers/LB-Li-SY-PS"),
        "default_format_note": "Grand Finals (Bo5)",
    },
    "Arabian Regional Championship 2026: Qatar-Bahrain-Kuwait": {
        "region": "Gulf (QA-BH-KW)",
        "circuit": "Arabian Regional Championship Qualifier",
        "ecosystem": "MENA_ARC_Gulf",
        "organizer_name": "Arabian Regional Championship",
        "organizer_url": wiki_url("Arabian Regional Championship 2026/Qualifiers/QA-BH-KW"),
        "default_format_note": "Qualifier Bracket (Completed — Stale Hotspawn Rows)",
    },
    "Komplettligaen 2026 Autumn": {
        "region": "Norway",
        "circuit": "Komplettligaen 1st Division LoL",
        "ecosystem": "Norway_Komplettligaen",
        "organizer_name": "GGArena / Gamer.no Official Standings",
        "organizer_url": "https://www.ggarena.no/competitions/komplettligaen-league-of-legends-hosten-2026/13909",
        "default_format_note": "Round-Robin Regular Season (Bo3)",
    },
    "Icelandic Esports League 2026 Autumn": {
        "region": "Iceland",
        "circuit": "Icelandic Esports League",
        "ecosystem": "Iceland_IEL",
        "organizer_name": "Rafíþróttasamtök Íslands / IEL",
        "organizer_url": wiki_url("Icelandic Esports League/2026 Season/Autumn Split"),
        "default_format_note": "Regular Season (Past-Lock Hotspawn Rows)",
    },
    "LigaGG CELOL B 2026 Split 2 Playoffs": {
        "region": "Brazil",
        "circuit": "LigaGG Circuito Estudantil / CELOL Série B",
        "ecosystem": "Brazil_LigaGG",
        "organizer_name": "LigaGG Brasil",
        "organizer_url": wiki_url("LigaGG/CELOL Série B/2026 Season/Split 2 Playoffs"),
        "default_format_note": "Double-Elimination Playoffs (Bo3)",
    },
    "LigaGG CELOL B 2026 Split 2": {
        "region": "Brazil",
        "circuit": "LigaGG CELOL Série B Regular Season",
        "ecosystem": "Brazil_LigaGG",
        "organizer_name": "LigaGG Brasil",
        "organizer_url": wiki_url("LigaGG/CELOL Série B/2026 Season/Split 2"),
        "default_format_note": "Regular Season (Completed — Stale Hotspawn Rows)",
    },
    "LigaGG CELOL A 2026 Split 2": {
        "region": "Brazil",
        "circuit": "LigaGG CELOL Série A",
        "ecosystem": "Brazil_LigaGG_A",
        "organizer_name": "LigaGG Brasil",
        "organizer_url": wiki_url("LigaGG/CELOL Série A/2026 Season/Split 2"),
        "default_format_note": "Regular Season / Playoffs (Stale Hotspawn Rows)",
    },
    "Benelux Ascend Series 2026 Summer Split": {
        "region": "Benelux (BE / NL / LU)",
        "circuit": "Benelux Ascend Series",
        "ecosystem": "Benelux_Ascend",
        "organizer_name": "Benelux Ascend Series",
        "organizer_url": wiki_url("Benelux Ascend Series/2026 Season/Summer Split"),
        "default_format_note": "Summer Split (Completed — Stale Hotspawn Rows)",
    },
    "Benelux Ascend Series 2026 Summer Playoffs": {
        "region": "Benelux (BE / NL / LU)",
        "circuit": "Benelux Ascend Series Playoffs",
        "ecosystem": "Benelux_Ascend",
        "organizer_name": "Benelux Ascend Series",
        "organizer_url": wiki_url("Benelux Ascend Series/2026 Season/Summer Playoffs"),
        "default_format_note": "Summer Playoffs (Completed — Stale Hotspawn Rows)",
    },
    "Benelux Ascend Series 2027 Winter Promotion": {
        "region": "Benelux (BE / NL / LU)",
        "circuit": "Benelux Ascend Series Promotion",
        "ecosystem": "Benelux_Ascend",
        "organizer_name": "Benelux Ascend Series",
        "organizer_url": wiki_url("Benelux Ascend Series/2027 Season/Winter Promotion"),
        "default_format_note": "Winter Promotion (Completed — Stale Hotspawn Rows)",
    },
    "Benelux Ascend Series Rising 2026 Summer Playoffs": {
        "region": "Benelux (BE / NL / LU)",
        "circuit": "Benelux Ascend Series Rising",
        "ecosystem": "Benelux_Rising",
        "organizer_name": "Benelux Ascend Series",
        "organizer_url": wiki_url("Benelux Ascend Series Rising/2026 Season/Summer Playoffs"),
        "default_format_note": "Rising Playoffs (Completed — Stale Hotspawn Rows)",
    },
    "FPL 2026 Summer Playoffs": {
        "region": "Finland",
        "circuit": "Finnish Pro League",
        "ecosystem": "Finland_FPL",
        "organizer_name": "Finnish Pro League",
        "organizer_url": wiki_url("Finnish Pro League/2026 Season/Summer Playoffs"),
        "default_format_note": "Summer Playoffs (Completed — Stale Hotspawn Row)",
    },
    "Hitpoint 2nd Div Challengers 2026 Summer Playoffs": {
        "region": "Czechia & Slovakia",
        "circuit": "Hitpoint 2nd Division Challengers",
        "ecosystem": "Czech_Hitpoint",
        "organizer_name": "Hitpoint Challengers",
        "organizer_url": wiki_url("Hitpoint 2nd Division Challengers/2026 Season/Summer Playoffs"),
        "default_format_note": "Summer Playoffs (Completed — Stale Hotspawn Row)",
    },
    "LIT 2027 Winter Promotion": {
        "region": "Italy",
        "circuit": "League of Legends Italian Tournament Promotion",
        "ecosystem": "Italy_LIT",
        "organizer_name": "LIT Official",
        "organizer_url": wiki_url("LIT/2027 Season/Winter Promotion"),
        "default_format_note": "Winter Promotion (Completed — Stale Hotspawn Row)",
    },
    "Legends Academy powered by Żabka Season 3 Playoffs": {
        "region": "Poland",
        "circuit": "Legends Academy Season 3",
        "ecosystem": "Poland_LA",
        "organizer_name": "Legends Academy Poland",
        "organizer_url": wiki_url("Legends Academy/2026/Season 3 Playoffs"),
        "default_format_note": "Season 3 Finals (Completed — Stale Hotspawn Row)",
    },
    "POP Esports Masters Season 7": {
        "region": "France / Benelux",
        "circuit": "POP Esports Masters",
        "ecosystem": "France_POP",
        "organizer_name": "POP Esports Masters",
        "organizer_url": wiki_url("POP Esports Masters/Season 7"),
        "default_format_note": "Grand Final (Completed — Stale Hotspawn Row)",
    },
}


# Explicit competition-scoped alias resolution (`(competition_name, hotspawn_team_name) -> [Data: aliases]`)
COMP_TEAM_ALIASES: dict[tuple[str, str], list[str]] = {
    ("4 Nations 2026 Halloween Heist", "Bulldog Esports"): ["BDG", "Bulldog Esports"],
    ("4 Nations 2026 Halloween Heist", "Inari Esports"): ["Inari UK", "Inari Esports"],
    ("4 Nations 2026 Halloween Heist", "Rich Gang UK"): ["Rich UK", "Rich Gang UK"],
    ("Arabian League 2nd Division 2026 Summer", "Team VDS"): ["Victorious Demons", "Team VDS", "VDS"],
    ("Arabian Regional Championship 2026: Qatar-Bahrain-Kuwait", "Arena"): ["Arena (Kuwaiti Team)"],
    ("Arabian Regional Championship 2026: Qatar-Bahrain-Kuwait", "OverPower"): ["Overpower (Kuwaiti Team)"],
    ("Benelux Ascend Series 2026 Summer Playoffs", "LAST DANCE"): ["Last Dance (Benelux Team)"],
    ("Benelux Ascend Series 2026 Summer Split", "BiPOLAR"): ["BiPOLAR (Benelux Team)"],
    ("Benelux Ascend Series 2026 Summer Split", "LAST DANCE"): ["Last Dance (Benelux Team)"],
    ("Benelux Ascend Series 2026 Summer Split", "Nameless"): ["Nameless (Benelux Team)"],
    ("Benelux Ascend Series 2027 Winter Promotion", "Nameless"): ["Nameless (Benelux Team)"],
    ("Benelux Ascend Series 2027 Winter Promotion", "The Bandits Academy"): ["Bandits Academy", "The Bandits Academy"],
    ("Benelux Ascend Series Rising 2026 Summer Playoffs", "Venus"): ["Venus (Benelux Team)"],
    ("FPL 2026 Summer Playoffs", "Epic Avalanche"): ["EA", "Epic Avalanche"],
    ("Hitpoint 2nd Div Challengers 2026 Summer Playoffs", "EXILE esports Academy"): ["EXILE esports Academy", "EXE.A"],
    ("Icelandic Esports League 2026 Autumn", "Cool Beans Team"): ["CBT", "Cool Beans Team"],
    ("Icelandic Esports League 2026 Autumn", "Fenrir"): ["Fenrir (Icelandic Team)"],
    ("Komplettligaen 2026 Autumn", "DMG Esports Norway"): ["DMG NO", "DMG Esports Norway"],
    ("Komplettligaen 2026 Autumn", "Playwell Rød Q"): ["Playwell", "Playwell Rød Q"],
    ("Komplettligaen 2026 Autumn", "Rich Gang"): ["Rich NO", "Rich Gang (Norwegian Team)"],
    ("LCP 2027 Promotion", "Frank Esports"): ["Frank Esports", "FAK HK"],
    ("LCP 2027 Promotion", "Ground Zero Gaming"): ["GZ", "Ground Zero Gaming"],
    ("LigaGG CELOL A 2026 Split 2", "Smoke Tram Ascension"): ["Smoke Tram", "Smoke Tram Ascension"],
    ("LigaGG CELOL B 2026 Split 2 Playoffs", "Final Level eSports Academy"): ["Final Level Academy", "Final Level eSports Academy"],
    ("LigaGG CELOL B 2026 Split 2 Playoffs", "Infinity Gaming"): ["Infinity Gaming (Brazilian Team)"],
    ("PRM 2nd Division 26-27 Fall", "404 Multigaming e.V."): ["404", "404 Multigaming e.V."],
    ("PRM 2nd Division 26-27 Fall", "Babos Gaming"): ["BABO", "Babos Gaming"],
    ("PRM 2nd Division 26-27 Fall", "DKB XPERION NXT"): ["DKBX", "DKB XPERION NXT"],
    ("PRM 2nd Division 26-27 Fall", "Locked IN"): ["Locked In", "Locked IN"],
    ("PRM 2nd Division 26-27 Fall", "MT1 Esports"): ["MT1", "MT1 Esports"],
    ("PRM 2nd Division 26-27 Fall", "No Need Orga"): ["NNO", "No Need Orga"],
    ("PRM 2nd Division 26-27 Fall", "Phong Vũ Buffalo"): ["PvB Nation"],
    ("PRM 2nd Division 26-27 Fall", "Reveal Multigaming"): ["Reveal", "Reveal Multigaming"],
    ("PRM 2nd Division 26-27 Fall", "Team 300"): ["300", "Team 300", "Team 300 Black", "300 Black"],
    ("PRM 2nd Division 26-27 Fall", "VfB eSports"): ["VFB", "VfB eSports"],
    ("PRM 2nd Division 26-27 Fall", "reGOLD eSport"): ["REGO", "reGOLD eSport"],
    ("PRM 2nd Division 26-27 Fall", "regnum4games"): ["R4G", "regnum4games"],
    ("PRM 3rd Division 26-27 Fall", "1. Esport Club Frankfurt e.V."): ["ECF", "1. Esport Club Frankfurt e.V."],
    ("PRM 3rd Division 26-27 Fall", "Black Lion"): ["BLion", "Black Lion"],
    ("PRM 3rd Division 26-27 Fall", "Eintracht Spandau Zwei"): ["ZWEI", "Eintracht Spandau Zwei"],
    ("PRM 3rd Division 26-27 Fall", "Kanji Esports AKA"): ["Kanji AKA", "Kanji Esports AKA"],
    ("PRM 3rd Division 26-27 Fall", "Kanji Esports KIN"): ["Kanji KIN", "Kanji Esports KIN"],
    ("PRM 3rd Division 26-27 Fall", "Neko Elite Kittens"): ["Neko Elite", "Neko Elite Kittens"],
    ("PRM 3rd Division 26-27 Fall", "Packmiko E-Sports DACH"): ["Packmiko DACH", "Packmiko E-Sports DACH"],
    ("PRM 3rd Division 26-27 Fall", "Rich Gang"): ["Rich NO", "Rich Gang"],
    ("PRM 3rd Division 26-27 Fall", "Second Time Alive Revival"): ["2TA Revival", "2TA", "Second Time Alive Revival"],
    ("PRM 3rd Division 26-27 Fall", "Team 300 White"): ["300 White", "Team 300 White"],
    ("PRM 3rd Division 26-27 Fall", "TeamOrangeGaming Academy"): ["TOG.A", "TeamOrangeGaming Academy"],
    ("PRM 3rd Division 26-27 Fall", "spongecord prime"): ["SPNG", "spongecord prime"],
    ("RIVALS LEAGUE Season 2", "DMG Esports Sweden"): ["DMG SE", "DMG Esports Sweden"],
    ("RIVALS LEAGUE Season 2", "FlameHard"): ["FlameHard", "Flamehard"],
    ("RIVALS LEAGUE Season 2", "Karolinerna"): ["K5", "Karolinerna"],
    ("RIVALS LEAGUE Season 2", "Lund Esports Organization OGs"): ["LEO OGs", "Lund Esports Organization OGs"],
    ("RIVALS LEAGUE Season 2", "Rich Gang Sweden"): ["Rich SE", "Rich Gang Sweden"],
    ("RIVALS LEAGUE Season 2", "Team cd"): ["Team CD", "Team cd"],
    ("Superstrike League 2026", "Crazy Kittens E-Sport Academy"): ["Crazy Kittens Esport Academy"],
    ("Superstrike League 2026", "Karolinerna"): ["K5", "Karolinerna"],
    ("Superstrike League 2026", "Karolinerna Black"): ["K5B", "Karolinerna Black"],
    ("Superstrike League 2026", "Lund Esports Organization"): ["LEO Esports", "Lund Esports Organization"],
    ("Superstrike League 2026", "Lundqvist Lightside"): ["LLS", "Lundqvist Lightside"],
    ("Worlds 2026 Main Event", "Anyone's Legend"): ["AL CN", "Anyone's Legend"],
    ("Worlds 2026 Main Event", "Bilibili Gaming"): ["BLG", "Bilibili Gaming"],
    ("Worlds 2026 Main Event", "CTBC Flying Oyster"): ["CFO", "CTBC Flying Oyster"],
    ("Worlds 2026 Main Event", "Dplus KIA"): ["DPLUS", "Dplus KIA"],
    ("Worlds 2026 Main Event", "G2 Esports"): ["G2", "G2 Esports"],
    ("Worlds 2026 Main Event", "Gen.G"): ["GEN", "Gen.G"],
    ("Worlds 2026 Main Event", "Hanwha Life Esports"): ["HLE", "Hanwha Life Esports"],
    ("Worlds 2026 Main Event", "Invictus Gaming"): ["IG", "Invictus Gaming"],
    ("Worlds 2026 Main Event", "Karmine Corp"): ["KCORP", "Karmine Corp"],
    ("Worlds 2026 Main Event", "LYON"): ["LYON24", "LYON"],
    ("Worlds 2026 Main Event", "LØS"): ["LOS", "LØS"],
    ("Worlds 2026 Main Event", "Movistar KOI"): ["MKOI", "Movistar KOI"],
    ("Worlds 2026 Main Event", "Top Esports"): ["TES", "Top Esports"],
    ("Worlds 2026 Main Event", "Team Liquid"): ["TL", "Team Liquid"],
    ("Worlds 2026 Main Event", "Team Secret Whales"): ["TSTW", "Team Secret Whales"],
}


# Explicit verified administrative rulings & feed anomalies keyed by `(competition_name, team_name)`
ADMIN_TEAM_NOTES: dict[tuple[str, str], dict[str, str]] = {
    ("Komplettligaen 2026 Autumn", "Solid Gaming"): {
        "severity": "critical_removed",
        "badge": "Removed from League (Round 10)",
        "summary": (
            "Official Leaguepedia & GGArena standings record `dqteams=Solid Gaming` "
            "(\"Round 10: Solid Gaming is removed from the league\"). All prior post-removal "
            "Hotspawn rows (#1071170, #1071200, #1071206, #1071186) went unplayed."
        ),
        "source_url": wiki_url("Komplettligaen/2026 Season/Autumn Split"),
    },
    ("PRM 2nd Division 26-27 Fall", "Phong Vũ Buffalo"): {
        "severity": "entity_misbinding",
        "badge": "Hotspawn Name Misbinding -> PvB Nation (DE)",
        "summary": (
            "Hotspawn's upstream feed misbinds German Prime League Division 2.1 squad `PvB Nation` "
            "(tag `PVB`) to defunct 2019 Vietnamese VCS organization `Phong Vũ Buffalo`. "
            "Resolved directly to `PvB Nation`'s official Prime League 2nd Division roster and results."
        ),
        "source_url": wiki_url("Prime League 2nd Division/2027 Season/Fall Split"),
    },
    ("Arabian League 2nd Division 2026 Summer", "Team Reds"): {
        "severity": "forfeit_ruling",
        "badge": "2x Week 1 Admin Forfeit Ruling",
        "summary": (
            "Official Arabian League 2nd Division footnotes 1 & 2 document that two Week 1 matches "
            "won on the Rift by Team Reds were overturned to forfeit losses for fielding an ineligible player."
        ),
        "source_url": wiki_url("Arabian League 2nd Division/2026 Season/Summer Split"),
    },
    ("PRM 2nd Division 26-27 Fall", "reGOLD eSport"): {
        "severity": "slot_transfer",
        "badge": "Acquired Slot (ex-All for One Gaming)",
        "summary": "Per official Prime League 2nd Division footnote 1, All for One Gaming disbanded and reGOLD eSport acquired the Division 2 slot.",
        "source_url": wiki_url("Prime League 2nd Division/2027 Season/Fall Split"),
    },
    ("PRM 2nd Division 26-27 Fall", "Team 300"): {
        "severity": "rename",
        "badge": "Renamed (ex-Team 300 Black)",
        "summary": "Per official Prime League 2nd Division footnote 2, Team 300 Black renamed to Team 300.",
        "source_url": wiki_url("Prime League 2nd Division/2027 Season/Fall Split"),
    },
    ("PRM 2nd Division 26-27 Fall", "The Bandits Prime"): {
        "severity": "slot_transfer",
        "badge": "Acquired Slot (ex-Team Rift)",
        "summary": "Per official Prime League 2nd Division footnote 3, Team Rift disbanded and The Bandits Prime acquired the slot.",
        "source_url": wiki_url("Prime League 2nd Division/2027 Season/Fall Split"),
    },
    ("Benelux Ascend Series 2026 Summer Playoffs", "LAST DANCE"): {
        "severity": "disqualified",
        "badge": "Disqualified (Playoffs DQ)",
        "summary": "Official Benelux Ascend Series Summer Playoffs page records Last Dance as disqualified (`DQ`).",
        "source_url": wiki_url("Benelux Ascend Series/2026 Season/Summer Playoffs"),
    },
    ("Benelux Ascend Series Rising 2026 Summer Playoffs", "Venus"): {
        "severity": "disqualified",
        "badge": "Disqualified (Playoffs DQ)",
        "summary": "Official Benelux Ascend Series Rising Summer Playoffs page records Venus as disqualified (`DQ`).",
        "source_url": wiki_url("Benelux Ascend Series Rising/2026 Season/Summer Playoffs"),
    },
}
