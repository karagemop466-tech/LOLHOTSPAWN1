# Session `aca61f10` — Line-by-Line Verification Receipt

- **Dataset snapshot**: `2026-10-24T17:14:52Z`
- **Inventory parity**: `241` published matches == `241` Hotspawn scheduled fixtures (`100%` coverage across `29` tournaments)
- **Method breakdown**: `{'model': 150, 'unresolved': 4, 'provisional': 78, 'market': 9}`
- **Row-level verification problems**: `0`

## Live Primary-Source Checks Executed (`fetch_page`)

- **Team Reds Week 1 overturned forfeits (previously misattributed to 4 Nations)** (`corrected` — <https://lol.fandom.com/wiki/Data:Arabian_League_2nd_Division/2026_Season/Summer_Split>): 4 Nations 2026 Halloween Heist has no participant named Team Reds. Team Reds competes in Arabian League 2nd Division 2026 Summer, where Week 1 primary wikitext records JSK Academy 2-0 Team Reds (ff=2, 2026-10-02, originally 2-1 JSK Academy) and Team Reds 0-2 New Era Team (ff=1, 2026-10-03, originally 2-0 Team Reds), both overturned due to Team Reds fielding an ineligible roster.
- **PRM 2nd Division 'Phong Vũ Buffalo' slot -> PvB (Swiss Team)** (`verified` — <https://lol.fandom.com/wiki/Data:Prime_League_2nd_Division/2027_Season/Fall_Split>): Participant roster 'PvB Nation' (Shourdy / 1334mat / Kryzik / ray / Quentin) records Week 1 series against The Bandits Prime (LOLTMNT05_228449) and Locked In (Dutch Team) (LOLTMNT05_228512) under 'PvB (Swiss Team)', confirming Hotspawn's 'Phong Vũ Buffalo' label on #1079053 is a ticker-expansion error.
- **Logitech G SuperStrike Cup Qualifier debut & homonym rows (#1083096, #1083097)** (`verified` — <https://lol.fandom.com/wiki/Logitech_G_SuperStrike_Cup/Qualifier>): #1083096 (Keep Yourself Positive vs CRUEL FATE) had 0/0 pre-kickoff rated series and is explicitly flagged on Flagged for review as an equal-prior debut split; #1083097's 'paiN Gaming' slot on Hotspawn corresponds to Bulgarian amateur 5-stack 'PNG' (billy / Bla6ko / metko / ifo / anditobate).
- **EGamersWorld live index vs match-page check (#1081421, #1081423)** (`verified` — <https://egamersworld.com/lol/match/eDTgthgYk/ground-zero-gaming-vs-frank-esports-wvOLKhrveF>): Runner records HTTP 403 (bot protection). Independent live fetch shows /lol/matches index lists 8 Worlds cards, LGC Rising #1079080 (1.41/2.59), #1081421 (1.8/1.8 placeholder), and #1081423 (1.025/10.50), whereas both the LCP event page and the #1081423 match page itself render symmetric 1.8 / 1.8 placeholders (0% / 0% tips), confirming #1081423 should remain originated rather than market-priced.
