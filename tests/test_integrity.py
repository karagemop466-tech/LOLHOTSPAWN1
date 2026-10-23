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

    def test_sum(self):
        r = self.row(); r['p1'] = .4
        self.assertTrue(row_errors(r))
