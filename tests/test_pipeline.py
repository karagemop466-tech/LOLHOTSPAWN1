"""Offline regression tests for the collectors, maths and the honesty gates.

Run: ``python -m unittest discover -s tests -v``  (no network needed)

The lobby sample below is deliberately shaped like Hotspawn's server-rendered LoL lobby
(verified 2026-10-21 at https://play.hotspawn.com/lol-pickems): a date line, the tournament,
"Points available / N pts / Tier X / Stage …", the "Locks in" countdown, an optional match-page
link and two "<team> N% picked" lines.  Cards without a link and cards whose tier is still
"WAITING FOR INFORMATION" are included because both occur in the real page.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scripts import hotspawn as hs                          # noqa: E402
from scripts import lines as LN                              # noqa: E402
from scripts import model as MD                              # noqa: E402
from scripts.common import (                                 # noqa: E402
    bo_n_prob, canon_team, devig_two_way, html_to_lines, implied_prob, parse_countdown,
    team_match,
)
from scripts.pipeline import resolve, norm_slug_names        # noqa: E402

FETCHED = datetime(2026, 10, 21, 16, 0, 0, tzinfo=timezone.utc)

LOBBY_SAMPLE = """
Hotspawn Play
This week
138 matches this week
Resets in 4d 00h 00s
Sign in to track your picks this week.
Tier
All tiers (3)
A (1)
WAITING FOR INFORMATION (2)
Closing Soon
Oct 22, 08:00
EM 2026 Summer Main Event
Points available
20 pts
Tier
A ×2
Stage
Waiting For Information
Sign in for streaks
Locks in
15:40:45
View Match
https://www.hotspawn.com/matches/galions-vs-solary-em-2026-summer-main-event-1081205
Who will win?
Galions
86% picked
Solary
14% picked
Oct 22, 11:00
Komplettligaen 2026 Autumn
Points available
10 pts
Tier
C
Stage
Waiting For Information
Sign in for streaks
Locks in
18:40:45
View Match
https://www.hotspawn.com/matches/ascent-gaming-vs-ntnui-kometkameratene-komplettligaen-2026-autumn-1071214
Who will win?
Ascent Gaming
93% picked
NTNUI Kometkameratene
7% picked
Oct 25, 21:00
RIVALS LEAGUE Season 2
Points available
5 pts
Tier
WAITING FOR INFORMATION
Stage
Group Stage
Sign in for streaks
Locks in
4d 5h 0m
Who will win?
Turbo Gaming
10% picked
Fritt Fall
90% picked
Create an account to play and win prizes
Leaderboard
"""


class LobbyParser(unittest.TestCase):
    def setUp(self):
        self.cards = hs.parse_lobby(html_to_lines(LOBBY_SAMPLE), FETCHED)

    def test_all_cards_found(self):
        self.assertEqual(len(self.cards), 3, [c.get("parse_notes") for c in self.cards])

    def test_fields(self):
        first = self.cards[0]
        self.assertEqual(first["teams"], ["Galions", "Solary"])
        self.assertEqual(first["hotspawn_pick_pct"], [86, 14])
        self.assertEqual(first["tier"], "A")
        self.assertEqual(first["multiplier"], 2.0)
        self.assertEqual(first["points"], 20)
        self.assertEqual(first["lobby_tournament"], "EM 2026 Summer Main Event")
        self.assertEqual(first["fixture_id"], 1081205)
        self.assertTrue(first["match_url"].startswith("https://www.hotspawn.com/matches/"))

    def test_kickoff_is_the_displayed_utc_time_not_the_cached_countdown(self):
        # The card prints "Oct 22, 08:00"; the "Locks in" countdown is measured from whenever the
        # cached lobby render was produced, so it must not be used as the kickoff (run 6 evidence:
        # countdown-derived time was 70 min later than the printed time on the same card).
        card = self.cards[0]
        self.assertEqual(card["kickoff_utc"], "2026-10-22T08:00:00Z")
        self.assertEqual(card["lock_countdown_s"], 15 * 3600 + 40 * 60 + 45)
        # countdown-derived instant is 19 min before the printed time in this sample, i.e. the two
        # do not agree — which is exactly why the printed (UTC) time wins.
        self.assertEqual(card["lock_vs_displayed_min"], -19)

    def test_feed_ids_are_provider_ids_not_post_ids(self):
        slug = ("galions-vs-solary-league-of-legends-match-at-"
                "em-2026-summer-main-event-1081205")
        self.assertEqual(hs.provider_id_from_slug(slug), 1081205)
        self.assertEqual(hs.tournament_slug_from_fixture_slug(slug), "em-2026-summer-main-event")
        self.assertIsNone(hs.provider_id_from_slug(None))
        self.assertIsNone(hs.provider_id_from_slug("no-trailing-number"))

    def test_league_rows_are_found_without_assuming_anchor_rows(self):
        page = (
            '<html><head><title>Komplettligaen 2026 Autumn Live Scores | Hotspawn</title></head>'
            '<body><div class="day">21 Oct 2026</div><div class="row">'
            '<span class="t">16:00 UTC</span>'
            '<a href="/matches/levelers-vs-mtn-esports-team-komplettligaen-2026-autumn-1082839">'
            '<img alt="Levelers"/>Levelers<span>vs</span>MTN ESPORTS TEAM</a>'
            '<span class="s">2 : 0</span><span class="st">Finished</span></div></body></html>')
        rows = hs._league_rows_from_lines(page, "https://www.hotspawn.com/x")
        self.assertEqual(len(rows), 1, rows)
        row = rows[0]
        self.assertEqual(row["fixture_id"], 1082839)
        self.assertEqual(row["league_kickoff_utc"], "2026-10-21T16:00:00Z")
        self.assertEqual(row["league_score"], [2, 0])
        self.assertEqual(row["league_status"], "finished")
        self.assertEqual(row["league_away_display"], "MTN ESPORTS TEAM")
        res = hs.harvest_results_from_league(page, "https://www.hotspawn.com/x")
        self.assertEqual([(r["team_home"], r["team_away"], r["score_home"]) for r in res],
                         [("Levelers", "MTN ESPORTS TEAM", 2)])

    def test_waiting_tier_and_missing_link(self):
        third = self.cards[2]
        self.assertEqual(third["tier"], "WAITING")
        self.assertIsNone(third["fixture_id"])
        self.assertTrue(any("match-page" in n for n in third["parse_notes"]))

    def test_totals(self):
        totals = hs.lobby_totals(html_to_lines(LOBBY_SAMPLE))
        self.assertEqual(totals["matches_this_week"], 138)
        self.assertEqual(totals["tiers_count"], 3)



class FeedJoin(unittest.TestCase):
    """The id in a Hotspawn match URL is a provider id, not the WordPress post id."""

    ROWS = [
        {"id": 203708,
         "slug": "galions-vs-solary-league-of-legends-match-at-em-2026-summer-main-event-1081205",
         "link": "https://www.hotspawn.com/matches/galions-vs-solary-em-2026-summer-main-event-1081205",
         "date": "2026-10-20T09:00:00", "modified": "2026-10-21T10:00:00",
         "title": {"rendered": ("Galions vs Solary League of Legends match at "
                                "EM 2026 Summer Main Event &#8211; 1081205")}},
        {"id": 204696,
         "slug": ("levelers-vs-mtn-esports-team-league-of-legends-match-at-arabian-regional-"
                  "championship-2026-lebanon-libya-syria-palestine-1082839"),
         "link": "https://www.hotspawn.com/matches/levelers-vs-mtn-esports-team-arabian-"
                 "regional-championship-2026-lebanon-libya-syria-palestine-1082839",
         "date": "2026-10-19T09:00:00", "modified": "2026-10-21T09:00:00",
         "title": {"rendered": ("Levelers vs MTN ESPORTS TEAM League of Legends match at "
                                "Arabian Regional Championship 2026: Lebanon-Libya-Syria-"
                                "Palestine &#8211; 1082839")}},
    ]

    class Stub:
        def __init__(self, rows):
            self.rows = rows

        def get_json(self, url, attempts=3, headers=None):
            return list(self.rows)

    def test_feed_records_are_keyed_by_provider_id_and_carry_tournament_slug(self):
        feed = hs.search_lol_fixtures(self.Stub(self.ROWS))
        self.assertEqual(len(feed), 2, feed)
        idx = hs.index_by_provider_id(feed)
        self.assertEqual(sorted(idx), [1081205, 1082839])
        self.assertEqual(idx[1081205]["tournament_slug"], "em-2026-summer-main-event")
        self.assertEqual(idx[1081205]["wp_post_id"], 203708)
        self.assertEqual(idx[1082839]["tournament_slug"],
                         "arabian-regional-championship-2026-lebanon-libya-syria-palestine")

    def test_feed_title_names_are_extracted_for_name_check(self):
        feed = hs.search_lol_fixtures(self.Stub(self.ROWS))
        by_id = {r["provider_id"]: r for r in feed}
        m = hs.FIXTURE_TITLE_TEAMS.match(by_id[1082839]["wp_title"])
        self.assertEqual((m.group("a"), m.group("b")), ("Levelers", "MTN ESPORTS TEAM"))
        self.assertNotIn("1082839", by_id[1082839]["wp_title"])
        self.assertNotIn("&#8211;", by_id[1082839]["wp_title"])


class LeaguePage(unittest.TestCase):
    HTML = """
    <html><head><title>Komplettligaen 2026 Autumn Live Scores, Fixtures - Hotspawn</title></head>
    <body><div class="hs-fixtures">
      <a href="https://www.hotspawn.com/league-of-legends/tournament/komplettligaen-2026-autumn/x">
        <div class="row">
          <a class="fixture" href="/matches/ascent-gaming-vs-ntnui-kometkameratene-komplettligaen-2026-autumn-1071214">
            <span>11:00 UTC</span><span>22 Oct</span><span>11:00 UTC</span>
            <span class="t">Ascent Gaming</span><img alt="" src="/l.svg"><span class="s">UPCOMING</span>
            <img alt="" src="/l.svg"><span class="t">NTNUI Kometkameratene</span>
          </a>
          <a class="fixture" href="/matches/solid-gaming-vs-dmg-esports-norway-komplettligaen-2026-autumn-1071216">
            <span>13:00 UTC</span><span>21 Oct</span><span>13:00 UTC</span>
            <span class="t">Solid Gaming</span><span class="sc">2 : 0</span>
            <span class="t">DMG Esports Norway</span>
          </a>
        </div>
      </a>
    </body></html>
    """

    def test_parse(self):
        out = hs.parse_league_page(self.HTML, "https://x/league-of-legends/tournament/komplettligaen")
        fx = {f["fixture_id"]: f for f in out["fixtures"]}
        self.assertIn(1071214, fx)
        self.assertEqual(fx[1071214]["league_kickoff_utc"], "2026-10-22T11:00:00Z")
        self.assertEqual(fx[1071214]["league_display"],
                         ["Ascent Gaming", "NTNUI Kometkameratene"])
        # league_teams is the canonical join key; pin the invariant, not the suffix dictionary
        self.assertEqual(fx[1071214]["league_teams"],
                         [hs.canon_team(x) for x in fx[1071214]["league_display"]])
        self.assertEqual(fx[1071214]["league_status"], "scheduled")
        self.assertEqual(fx[1071216]["league_score"], [2, 0])

    def test_results_harvest(self):
        rows = hs.harvest_results_from_league(self.HTML)
        self.assertEqual(len(rows), 1, rows)
        self.assertEqual(rows[0]["team_home"], "Solid Gaming")
        self.assertEqual(rows[0]["score_home"], 2)
        self.assertTrue(rows[0]["source_url"].endswith("1071216"))


class OddsMaths(unittest.TestCase):
    def test_implied_and_devig(self):
        self.assertAlmostEqual(implied_prob(decimal=2.0), 0.5)
        self.assertAlmostEqual(implied_prob(american=-200), 2 / 3)
        a, b = devig_two_way(implied_prob(decimal=1.30), implied_prob(decimal=3.60))
        self.assertAlmostEqual(a + b, 1.0)
        self.assertGreater(a, 0.7)

    def test_bo(self):
        self.assertAlmostEqual(bo_n_prob(0.5, 5), 0.5)
        self.assertGreater(bo_n_prob(0.6, 5), 0.6)
        self.assertAlmostEqual(bo_n_prob(0.6, 3), 0.648, places=3)

    def test_countdown_forms(self):
        self.assertEqual(parse_countdown("4d 5h 0m"), 4 * 86400 + 5 * 3600)
        self.assertEqual(parse_countdown("00:02:30"), 150)
        self.assertIsNone(parse_countdown("soon"))


class Joining(unittest.TestCase):
    def test_aliases_but_not_rosters(self):
        self.assertTrue(team_match("Hanwha Life Esports", "Hanwha Life"))
        self.assertTrue(team_match("DMG Esports Norway", "dmg norway"))
        # academy / youth rosters must never inherit the parent club's line
        self.assertFalse(team_match("KT Rolster Academy", "KT Rolster"))
        self.assertFalse(team_match("T1", "T1 Academy"))

    def test_slug_names(self):
        self.assertEqual(
            norm_slug_names("galions-vs-solary-em-2026-summer-main-event-1081205",
                            "EM 2026 Summer Main Event"),
            ["galions", "solary"])

    def test_feed_title_is_authoritative(self):
        from scripts.pipeline import title_teams
        self.assertEqual(
            title_teams("Levelers vs MTN ESPORTS TEAM League of Legends match at Arabian Regional "
                        "Championship 2026: Lebanon-Libya-Syria-Palestine \u2013 1082839"),
            ["Levelers", "MTN ESPORTS TEAM"])

    def test_ambiguous_line_is_flagged_not_guessed(self):
        rows = [
            {"teams": ["Alpha", "Beta"], "odds": [1.5, 2.5], "url": "u1"},
            {"teams": ["Alpha", "Beta"], "odds": [1.9, 1.9], "url": "u2"},
        ]
        cards = [{"teams": ["Alpha", "Beta"], "fixture_id": 1, "parse_notes": []}]
        attach, flags = LN.attach([], rows, cards)
        self.assertEqual(attach, {})
        self.assertTrue(flags and "uniquely" in flags[0]["reason"])

    def test_single_line_attaches(self):
        rows = [{"teams": ["Alpha", "Beta"], "odds": [1.5, 2.5], "url": "u1",
                 "tournament_url": "t1", "day_label": "22 Oct 2026"}]
        cards = [{"teams": ["Alpha", "Beta"], "fixture_id": 1, "parse_notes": []}]
        attach, flags = LN.attach([], rows, cards)
        key = LN.pair_key("Alpha", "Beta")
        self.assertIn(key, attach)
        prim = attach[key]["primary"]
        self.assertAlmostEqual(prim["devig_home"] + prim["devig_away"], 1.0)


class Model(unittest.TestCase):
    RESULTS = [
        {"team_home": "BvP", "team_away": "Team 300", "score_home": 2, "score_away": 0,
         "source_url": "https://www.hotspawn.com/matches/a-900001", "league_slug": "prm"},
        {"team_home": "Team 300", "team_away": "Reveal Multigaming", "score_home": 2, "score_away": 1,
         "source_url": "https://www.hotspawn.com/matches/b-900002", "league_slug": "prm"},
        {"team_home": "Reveal Multigaming", "team_away": "BvP", "score_home": 2, "score_away": 1,
         "source_url": "https://www.hotspawn.com/matches/c-900003", "league_slug": "prm"},
    ]

    def test_ratings_and_prob(self):
        ratings, meta = MD.build_ratings(self.RESULTS)
        self.assertEqual(set(ratings), {"bvp", "300", "reveal multigaming"})
        # BvP beat Team 300 2-0 head-to-head, so it must be rated above them
        self.assertGreater(ratings["bvp"], ratings["300"])
        # every rating stays inside a sane band for 3-game samples (shrinkage toward 1500)
        for name, value in ratings.items():
            self.assertTrue(1350 < value < 1650, (name, value))
        probs, notes = MD.predict([{"teams": ["Reveal Multigaming", "BvP"], "fixture_id": 1}],
                                 ratings, meta)
        key = LN.pair_key("Reveal Multigaming", "BvP")
        row = probs[key]
        # the published probability must agree with the rating order (that is the invariant)
        self.assertEqual(row["prob_home"] > 0.5,
                         ratings["reveal multigaming"] > ratings["bvp"])
        self.assertAlmostEqual(row["prob_home"] + row["prob_away"], 1.0)
        self.assertIn(row["confidence"], ("low", "very low", "medium", "high"))
        self.assertTrue(row["evidence_urls"])

    def test_unrateable_team_is_reported(self):
        ratings, meta = MD.build_ratings(self.RESULTS)
        probs, notes = MD.predict([{"teams": ["Ghost Squad", "BvP"], "fixture_id": 7}], ratings, meta)
        self.assertEqual(probs, {})
        self.assertEqual(notes["unrateable_count"], 1)
        self.assertIn("Ghost Squad", notes["unrateable"][0]["reason"])


class ResolveAndGates(unittest.TestCase):
    def collected(self):
        return {
            "lobby_url": "https://play.hotspawn.com/lol-pickems",
            "totals": {"matches_this_week": 138, "tiers_count": 2},
            "matches": [
                {"lobby_index": 0, "lobby_tournament": "EM 2026 Summer Main Event",
                 "teams": ["Galions", "Solary"], "hotspawn_pick_pct": [86, 14], "tier": "A",
                 "points": 20, "multiplier": 2.0, "stage": "Waiting For Information",
                 "fixture_id": 1081205, "fixture_slug": "galions-vs-solary-em-2026-summer-main-event",
                 "match_url": "https://www.hotspawn.com/matches/galions-vs-solary-em-2026-summer-main-event-1081205",
                 "kickoff_utc": "2026-10-22T07:40:00Z", "parse_notes": []},
                {"lobby_index": 1, "lobby_tournament": "Nowhere League",
                 "teams": ["Ghost Squad", "Nobody FC"], "hotspawn_pick_pct": [50, 50], "tier": "D",
                 "points": 5, "multiplier": None, "stage": "Group Stage",
                 "fixture_id": 1081999, "fixture_slug": "ghost-squad-vs-nobody-fc-nowhere-league",
                 "match_url": "https://www.hotspawn.com/matches/ghost-squad-vs-nobody-fc-nowhere-league-1081999",
                 "kickoff_utc": "2026-10-23T09:00:00Z", "parse_notes": []},
            ],
            "fixture_records": {"1081205": {"fixture_id": 1081205,
                                          "wp_link": "https://www.hotspawn.com/matches/galions-vs-solary-em-2026-summer-main-event-1081205",
                                          "wp_title": "Galions vs Solary League of Legends match"}},
            "leagues": {"em": {"tournament_name": "EM 2026 Summer Main Event",
                              "fixtures": [{"fixture_id": 1081205,
                                            "league_url": "https://www.hotspawn.com/league-of-legends/tournament/em",
                                            "league_kickoff_utc": "2026-10-22T07:40:00Z",
                                            "league_teams": ["Galions", "Solary"],
                                            "league_status": "upcoming", "league_score": None}],
                              "results": []}},
            "feed_fixture_count": 2, "feed_only_fixtures": [],
        }

    def test_market_row_and_unresolved_row(self):
        rows = self.collected()["matches"]
        attach, attach_flags = LN.attach([], [{"teams": ["Galions", "Solary"], "odds": [1.25, 3.9],
                                              "url": "https://www.oddsportal.com/esports/h2h/a/b/",
                                              "tournament_url": "t", "day_label": "22 Oct 2026"}], rows)
        out = resolve(self.collected(), {"attach": attach, "attach_flags": attach_flags,
                                        "probes": [], "rows": [], "markets": []}, {})
        picks = out["picks"]
        market = [p for p in picks if p["basis"] == "market"][0]
        self.assertAlmostEqual(market["prob_home"] + market["prob_away"], 1.0)
        self.assertEqual(market["pick_team"], "Galions")
        unres = [p for p in picks if p["basis"] == "unresolved"]
        self.assertEqual(len(unres), 1)
        self.assertIsNone(unres[0]["prob_home"])
        self.assertEqual(len(out["unresolved"]), 1)
        # the fixture with no feed record must be flagged, not silently trusted
        self.assertTrue(any(f["field"] == "fixture_exists" for f in out["flags"]))

    def test_verify_refuses_fabricated_unresolved_probability(self):
        from scripts.verify import check_rows
        fabricated = {
            "id": "hs-1081999", "hotspawn_fixture_id": 1081999, "basis": "unresolved",
            "teams": [{"name": "Ghost Squad"}, {"name": "Nobody FC"}],
            "prob_home": 0.5, "prob_away": 0.5,
            "hotspawn_url": "https://www.hotspawn.com/matches/x-1081999",
        }
        errors: list[str] = []
        check_rows([fabricated], {"items": []}, errors, [])
        self.assertTrue(any("unresolved row must have blank probabilities" in e for e in errors), errors)

    def test_verify_requires_official_source_host(self):
        from scripts.verify import check_rows
        row = {
            "id": "hs-1", "hotspawn_fixture_id": 1, "basis": "market",
            "teams": [{"name": "A"}, {"name": "B"}], "prob_home": 0.6, "prob_away": 0.4,
            "hotspawn_url": "https://evil.example/matches/a-vs-b-1",
            "market": {"source_url": "https://oddsportal.com/x", "odds_home": 1.6},
        }
        errors: list[str] = []
        check_rows([row], {"items": []}, errors, [])
        self.assertTrue(any("not an accepted official host" in e for e in errors), errors)

    def test_verify_rejects_hotspawn_sourced_probability(self):
        from scripts.verify import check_rows
        row = {
            "id": "hs-2", "hotspawn_fixture_id": 2, "basis": "market",
            "teams": [{"name": "A"}, {"name": "B"}], "prob_home": 0.6, "prob_away": 0.4,
            "hotspawn_url": "https://www.hotspawn.com/matches/a-vs-b-2",
            "market": {"source_url": "https://www.hotspawn.com/matches/a-vs-b-2", "odds_home": 1.6},
        }
        errors: list[str] = []
        check_rows([row], {"items": []}, errors, [])
        self.assertTrue(any("sourced from Hotspawn (forbidden)" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main(verbosity=2)
