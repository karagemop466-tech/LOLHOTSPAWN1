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
        for html_file in root.glob('*.html'):
            txt = html_file.read_text(encoding='utf-8')
            self.assertNotIn('www.pinnacle.com/en/', txt, html_file.name)

    def test_preserve_recent_on_http_error_respects_ttl(self):
        import json
        import tempfile
        import collect as col_mod
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'kambi_lol.json'
            fresh_ts = col_mod.iso(col_mod.now_utc())
            p.write_text(json.dumps({
                'fetched_utc': fresh_ts,
                'events': [{'event_id': 1, 'outcomes': [{'name': 'A', 'decimal': 1.5}, {'name': 'B', 'decimal': 2.5}]}],
            }), encoding='utf-8')
            kept = col_mod._preserve_recent_on_http_error(str(p), 'events', 429, 'kambi', max_age_h=24.0)
            self.assertIsNotNone(kept)
            self.assertEqual(kept['count'], 1)
            stale = {
                'fetched_utc': '2026-10-20T00:00:00Z',
                'events': [{'event_id': 1}],
            }
            p.write_text(json.dumps(stale), encoding='utf-8')
            expired = col_mod._preserve_recent_on_http_error(str(p), 'events', 429, 'kambi', max_age_h=24.0)
            self.assertIsNone(expired)

    def test_kambi_parse_events_reads_match_odds(self):
        from collect import _kambi_parse_events
        payload = {
            "events": [{
                "event": {"id": 9, "englishName": "A - B", "name": "A - B",
                          "group": "World Championship", "start": "2026-10-24T17:10:00Z"},
                "betOffers": [{
                    "betOfferType": {"id": 2},
                    "criterion": {"englishLabel": "Match Odds"},
                    "outcomes": [
                        {"status": "OPEN", "odds": 1420, "participant": "Anyone's Legend",
                         "oddsAmerican": "-240", "changedDate": "2026-10-24T01:40:46Z"},
                        {"status": "OPEN", "odds": 2650, "participant": "TOP Esports",
                         "oddsAmerican": "165", "changedDate": "2026-10-24T01:40:46Z"},
                    ],
                }],
            }]
        }
        rows = _kambi_parse_events(payload, "ubse")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["event_id"], 9)
        self.assertEqual(rows[0]["operator"], "ubse")
        names = {o["name"] for o in rows[0]["outcomes"]}
        self.assertEqual(names, {"Anyone's Legend", "TOP Esports"})
        dec = {o["name"]: o["decimal"] for o in rows[0]["outcomes"]}
        self.assertEqual(dec["Anyone's Legend"], 1.42)
        self.assertEqual(dec["TOP Esports"], 2.65)

