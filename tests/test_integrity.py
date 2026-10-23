import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from integrity import row_errors


class IntegrityTests(unittest.TestCase):
    def row(self):
        return dict(method='model', p0=.7, p1=.3, team0={'name':'A'}, team1={'name':'B'}, pick={'team':'A', 'probability':.7})

    def test_valid(self):
        self.assertEqual(row_errors(self.row()), [])

    def test_wrong_team_same_probability(self):
        r = self.row(); r['pick']['team'] = 'B'
        self.assertTrue(row_errors(r))

    def test_invalid_probabilities(self):
        for value in (None, float('nan'), float('inf'), -0.1, 1.1, '0.7', True):
            r = self.row(); r['p0'] = value
            self.assertTrue(row_errors(r), repr(value))

    def test_unresolved_both_sides_blank(self):
        r = self.row(); r.update(method='unresolved', p0=None, p1=None, pick=None)
        self.assertEqual(row_errors(r), [])
        r['p1'] = .5
        self.assertTrue(row_errors(r))

    def test_settlement_pick_is_valid_without_probability(self):
        r = self.row()
        r.update(method='unresolved', p0=None, p1=None, pick_type='settlement',
                 pick={'team': 'A', 'probability': None, 'settlement': 'administrative default'})
        self.assertEqual(row_errors(r), [])

    def test_settlement_pick_rejects_probability(self):
        r = self.row()
        r.update(method='unresolved', p0=None, p1=None, pick_type='settlement',
                 pick={'team': 'A', 'probability': .7})
        self.assertTrue(row_errors(r))

    def test_settlement_pick_rejects_unknown_team(self):
        r = self.row()
        r.update(method='unresolved', p0=None, p1=None, pick_type='settlement',
                 pick={'team': 'Nobody', 'probability': None})
        self.assertTrue(row_errors(r))

    def test_settlement_pick_must_be_typed(self):
        r = self.row()
        r.update(method='unresolved', p0=None, p1=None,
                 pick={'team': 'A', 'probability': None})
        self.assertTrue(row_errors(r))

    def test_sum(self):
        r = self.row(); r['p1'] = .4
        self.assertTrue(row_errors(r))

    def test_competition_page_disambiguates_homonyms_before_global_exact(self):
        from model import resolve_team
        exact = {'last dance': 'Last Dance'}
        base = {'last dance': {'Last Dance', 'Last Dance (Benelux Team)'}}
        page_teams = {'Benelux Ascend Series/2026 Season/Summer Split': {'Last Dance (Benelux Team)'}}
        team, how, _ = resolve_team(
            'LAST DANCE', exact, base, {},
            'Benelux Ascend Series/2026 Season/Summer Split', page_teams,
        )
        self.assertEqual(team, 'Last Dance (Benelux Team)')
        self.assertEqual(how, 'competition-page')

    def test_live_venue_name_aliases(self):
        from model import same_team
        self.assertTrue(same_team('LØS', 'LOS'))
        self.assertTrue(same_team('Team Secret', 'Team Secret Whales'))
        self.assertTrue(same_team('Lyon Gaming', 'LYON'))

    def test_published_dataset_and_html_invariants(self):
        import json
        root = Path(__file__).resolve().parents[1]
        doc = json.loads((root / 'data' / 'matches.json').read_text(encoding='utf-8'))
        counts = doc['counts']
        self.assertEqual(sum(counts.values()), doc['total'])
        five_venue = [
            r for r in doc['matches']
            if r['method'] == 'market'
            and {v['name'] for v in (r.get('market') or {}).get('venues') or []}
            == {'Pinnacle', 'Polymarket', 'Kalshi', 'Bovada', 'Unibet'}
        ]
        self.assertGreaterEqual(len(five_venue), 8)
        for html_file in root.glob('*.html'):
            txt = html_file.read_text(encoding='utf-8')
            self.assertNotIn('www.pinnacle.com/en/', txt, html_file.name)

