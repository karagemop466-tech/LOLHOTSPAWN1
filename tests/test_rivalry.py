import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))

import collect  # noqa: E402
import model  # noqa: E402


GAMES_DOC = {"data": [{"id": 24, "name": "League of Legends"},
                      {"id": 12, "name": "Counter-Strike"}]}

MATCHES_DOC = {
    "data": [
        {
            "id": 901,
            "url": "https://rivalry.com/match/901",
            "scheduled_at": "2026-10-24T10:00:00Z",
            "tournament": {"name": "LCK Cup"},
            "competitors": [{"name": "T1"}, {"name": "Gen.G"}],
            "markets": [
                {"name": "match winner", "outcomes": []},
                {"name": "Winner", "outcomes": [
                    {"odds": 1.50, "competitor": {"name": "T1"}},
                    {"odds": 2.60, "competitor": {"name": "Gen.G"}},
                ]},
            ],
        },
        # no winner market -> skipped without raising
        {"id": 902, "scheduled_at": "2026-10-24T11:00:00Z",
         "competitors": [{"name": "X"}, {"name": "Y"}], "markets": []},
        # non-numeric odds -> skipped
        {"id": 903, "scheduled_at": "2026-10-24T12:00:00Z",
         "competitors": [{"name": "A"}, {"name": "B"}],
         "markets": [{"name": "Winner", "outcomes": [
             {"odds": "suspended", "competitor": {"name": "A"}},
             {"odds": 2.1, "competitor": {"name": "B"}},
         ]}]},
    ],
    "links": {"next": None},
}


class CollectRivalryTests(unittest.TestCase):
    def _run(self, responses):
        saved = {}

        def fake_save_json(path, obj):
            saved['path'] = path
            saved['doc'] = obj

        calls = {'n': 0}

        def fake_get_json(url, retries=None):
            i = calls['n']
            calls['n'] += 1
            return responses[min(i, len(responses) - 1)]

        with mock.patch.object(collect, 'get_json', fake_get_json), \
                mock.patch.object(collect, 'save_json', fake_save_json):
            result = collect.collect_rivalry()
        return result, saved

    def test_parses_winner_markets_in_competitor_order(self):
        result, saved = self._run([
            (200, GAMES_DOC, None),
            (200, MATCHES_DOC, None),
        ])
        self.assertEqual(result, {"count": 1, "status": 200})
        doc = saved['doc']
        self.assertTrue(str(saved['path']).endswith('rivalry_lol.json'))
        self.assertEqual(doc['event_count'], 1)
        event = doc['events'][0]
        self.assertEqual(event['match_id'], 901)
        self.assertEqual(event['tournament'], 'LCK Cup')
        self.assertEqual([o['name'] for o in event['outcomes']], ['T1', 'Gen.G'])
        self.assertEqual([o['decimal'] for o in event['outcomes']], [1.50, 2.60])
        self.assertIn('game_id=24', doc['source_url'])

    def test_api_failure_is_recorded_not_fatal(self):
        result, saved = self._run([
            (502, None, 'bad gateway'),
            (502, None, 'bad gateway'),
        ])
        self.assertEqual(result['count'], 0)
        self.assertEqual(result['status'], 502)
        self.assertEqual(saved['doc']['events'], [])
        self.assertIn('bad gateway', saved['doc']['error'])


class RivalryVenueTests(unittest.TestCase):
    def _index(self, d0=1.50, d1=2.60):
        return [{"names": ["T1", "Gen.G"], "d0": d0, "d1": d1,
                 "start": "2026-10-24T10:00:00Z",
                 "url": "https://rivalry.com/match/901"}]

    def test_rivalry_only_consensus_is_bookmaker_kind(self):
        out = model.market_lookup("f1", "T1", "Gen.G", "2026-10-24T10:00:00Z",
                                  [], [], [], [], {}, self._index())
        self.assertIsNotNone(out)
        self.assertEqual(out['kind'], 'bookmaker')
        self.assertEqual(out['venue_count'], 1)
        venue = out['venues'][0]
        self.assertEqual(venue['name'], 'Rivalry')
        self.assertEqual(venue['quote'], '1.50/2.60')
        self.assertGreater(venue['p0'], venue['p1'])
        # de-vigged probabilities sum to 1 and stay inside the valid range
        self.assertAlmostEqual(venue['p0'] + venue['p1'], 1.0, places=4)

    def test_orientation_flips_with_fixture_order(self):
        out = model.market_lookup("f1", "Gen.G", "T1", "2026-10-24T10:00:00Z",
                                  [], [], [], [], {}, self._index())
        venue = out['venues'][0]
        self.assertLess(venue['p0'], venue['p1'])
        self.assertEqual(venue['quote'], '2.60/1.50')

    def test_placeholder_180_180_is_rejected(self):
        # symmetric placeholder must never become a priced venue
        self.assertIsNone(model.market_lookup(
            "f1", "T1", "Gen.G", "2026-10-24T10:00:00Z",
            [], [], [], [], {}, self._index(1.80, 1.80)))

    def test_extreme_quote_is_rejected(self):
        self.assertIsNone(model.market_lookup(
            "f1", "T1", "Gen.G", "2026-10-24T10:00:00Z",
            [], [], [], [], {}, self._index(1.02, 12.0)))

    def test_consensus_with_prediction_market_renormalises_weights(self):
        pm = [{"names": ["T1", "Gen.G"], "p0": 0.62, "p1": 0.38,
               "volume": 5000.0, "slug": "t1-geng", "start": "2026-10-24T10:00:00Z"}]
        out = model.market_lookup("f1", "T1", "Gen.G", "2026-10-24T10:00:00Z",
                                  [], pm, [], [], {}, self._index())
        self.assertEqual(out['venue_count'], 2)
        self.assertEqual({v['name'] for v in out['venues']}, {'Rivalry', 'Polymarket'})
        self.assertAlmostEqual(out['p0'] + out['p1'], 1.0, places=4)


class ForfeitWinnerTests(unittest.TestCase):
    def test_ff_sides(self):
        self.assertEqual(model.ff_winner_name({'ff': 1, 'team1': 'Solid Gaming',
                                               'team2': 'VES Japan'}), 'VES Japan')
        self.assertEqual(model.ff_winner_name({'ff': 2, 'team1': 'Volda E-Sport',
                                               'team2': 'Solid Gaming'}), 'Volda E-Sport')

    def test_missing_or_bad_flag(self):
        self.assertIsNone(model.ff_winner_name({'ff': None, 'team1': 'A', 'team2': 'B'}))
        self.assertIsNone(model.ff_winner_name({'ff': '0', 'team1': 'A', 'team2': 'B'}))
        self.assertIsNone(model.ff_winner_name({'team1': 'A', 'team2': 'B'}))


if __name__ == '__main__':
    unittest.main()
