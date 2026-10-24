"""Regression tests for the receipt lifecycle in tools/corroborate.py.

Root cause of the 2026-10-23/24 refresh-picks outage: receipts citing the eight
Worlds 2026 fixtures (1067675-1067680, 1067878, 1067879) were classified
"rejected" the moment Hotspawn flipped those fixtures to `ended`, and the
publish gate treats any rejected receipt as fatal — so the pipeline could never
commit again. A concluded match is an expected lifecycle event, not a data
error: such receipts must retire (kept as historical evidence), while receipts
citing fixture ids that never existed, or carrying malformed prices for listed
fixtures, must stay rejected.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import corroborate  # noqa: E402


def _write(path: Path, obj) -> None:
    path.write_text(json.dumps(obj), encoding='utf-8')


class ReceiptLifecycleTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        data = tmp / 'data'
        (data / 'receipts' / 'external_odds').mkdir(parents=True)
        (data / 'node' / 'raw').mkdir(parents=True)
        self.data = data
        self._saved = (corroborate.DATA, corroborate.RECEIPT_DIR, corroborate.ROOT)
        corroborate.DATA = str(data)
        corroborate.RECEIPT_DIR = str(data / 'receipts' / 'external_odds')
        corroborate.ROOT = str(tmp)

        _write(data / 'matches.json', {
            'generated_utc': '2026-10-24T16:00:00Z',
            'matches': [{
                'id': '1', 'competition': 'Test Cup', 'start_utc': '2099-01-01T00:00:00Z',
                'method': 'model', 'p0': 0.64, 'p1': 0.36,
                'team0': {'name': 'Alpha'}, 'team1': {'name': 'Beta'},
                'pick': {'team': 'Alpha', 'probability': 0.64},
                'hotspawn_url': 'https://www.hotspawn.com/matches/alpha-vs-beta-test-cup-1',
            }],
        })
        _write(data / 'receipts' / 'external_odds' / '2026-10-23.json', {
            'sources': [{'key': 's1', 'name': 'Test Book', 'url': 'https://example.com',
                         'kind': 'test', 'runner_reachable': 'n/a', 'note': ''}],
            'captures': [
                {'source': 's1', 'captured_utc': '2026-10-23T15:00:00Z',
                 'page_url': 'https://example.com/m1', 'fixture_id': '1',
                 'competition': 'Test Cup', 'page_teams': ['Alpha', 'Beta'],
                 'decimal': [1.5, 2.7], 'verbatim': 'Alpha 1.50 Beta 2.70'},
                # fixture played and gone from the scheduled feed; all-status feed says ended
                {'source': 's1', 'captured_utc': '2026-10-23T15:00:00Z',
                 'page_url': 'https://example.com/m999', 'fixture_id': '999',
                 'competition': 'Test Cup', 'page_teams': ['Gamma', 'Delta'],
                 'decimal': [1.9, 1.95], 'verbatim': 'Gamma 1.90 Delta 1.95'},
                # collector lag: snapshot still scheduled, live dataset no longer lists it
                {'source': 's1', 'captured_utc': '2026-10-23T15:00:00Z',
                 'page_url': 'https://example.com/m777', 'fixture_id': '777',
                 'competition': 'Test Cup', 'page_teams': ['Eps', 'Zeta'],
                 'decimal': [1.7, 2.2], 'verbatim': 'Eps 1.70 Zeta 2.20'},
                # unknown fixture id: not in the dataset AND not in the all-status feed
                {'source': 's1', 'captured_utc': '2026-10-23T15:00:00Z',
                 'page_url': 'https://example.com/m888', 'fixture_id': '888',
                 'competition': 'Test Cup', 'page_teams': ['Eta', 'Theta'],
                 'decimal': [1.6, 2.4], 'verbatim': 'Eta 1.60 Theta 2.40'},
                # malformed price list for a fixture that IS listed
                {'source': 's1', 'captured_utc': '2026-10-23T15:00:00Z',
                 'page_url': 'https://example.com/m1b', 'fixture_id': '1',
                 'competition': 'Test Cup', 'page_teams': ['Alpha', 'Beta'],
                 'decimal': [1.5, 2.7, 3.0], 'verbatim': 'Alpha 1.50 Beta 2.70 ?'},
            ],
            'coverage_observations': [],
        })
        _write(data / 'node' / 'raw' / 'hotspawn_lol_fixtures.json', {
            'fetched_at': '2026-10-24T15:34:30.580Z',
            'fixtures': [
                {'id': '1', 'status': 'scheduled'},
                {'id': '999', 'status': 'ended'},
                {'id': '777', 'status': 'scheduled'},
            ],
        })

    def tearDown(self):
        corroborate.DATA, corroborate.RECEIPT_DIR, corroborate.ROOT = self._saved
        self._tmp.cleanup()

    def test_concluded_fixture_receipts_retire_and_do_not_reject(self):
        doc = corroborate.build()
        retired = {r['fixture_id']: r for r in doc['retired']}
        rejected = {r['fixture_id'] for r in doc['rejected']}
        self.assertEqual(set(retired), {'999', '777'})
        self.assertEqual(retired['999']['feed_status'], 'ended')
        self.assertIn('concluded or was voided', retired['999']['reason'])
        self.assertEqual(retired['777']['feed_status'], 'scheduled')
        self.assertIn('collector lag', retired['777']['reason'])
        # unknown id and malformed prices stay fatal
        self.assertEqual(rejected, {'888', '1'})
        self.assertEqual(doc['summary']['retired_receipts'], 2)
        self.assertEqual(doc['summary']['rejected_receipts'], 2)
        self.assertEqual(doc['summary']['receipts'], 5)
        usable = [r for r in doc['rows'] if r['status'] == 'usable']
        self.assertEqual(len(usable), 1)
        self.assertEqual(usable[0]['verdict'], 'agrees')

    def test_missing_all_status_snapshot_is_lenient(self):
        (self.data / 'node' / 'raw' / 'hotspawn_lol_fixtures.json').unlink()
        doc = corroborate.build()
        retired = {r['fixture_id'] for r in doc['retired']}
        rejected = {r['fixture_id'] for r in doc['rejected']}
        # Without a cross-check snapshot, delisted fixtures must not block publishing...
        self.assertEqual(retired, {'999', '777', '888'})
        # ...but a malformed price on a listed fixture is still a data error.
        self.assertEqual(rejected, {'1'})
        for r in doc['retired']:
            self.assertIn('historical evidence', r['reason'])

    def test_render_marks_retired_rows_without_rowbad(self):
        doc = corroborate.build()
        html_text = corroborate.render(doc)
        self.assertIn('retired &mdash; match concluded', html_text)
        # the retired fixture must not be styled as a hard failure
        self.assertNotIn('rowbad"><td data-label="Match"><span class="muted">999', html_text)


if __name__ == '__main__':
    unittest.main()
