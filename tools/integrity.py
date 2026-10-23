"""Pure, fail-closed checks shared by the publish gate and regression tests.

Three row shapes are legal:

* ``market`` / ``model`` / ``provisional`` - a priced row: p0 + p1 == 1, and the pick
  names the higher-probability side with exactly that probability.
* ``unresolved`` with ``pick: None`` - nothing can be defended at all (no market, no
  rated history). The row must not carry a probability.
* ``unresolved`` with ``pick_type: "settlement"`` - a league removal where the
  administratively correct side is known but no competitive probability is. The pick
  must name a real participant and must not carry a probability.
"""
import math


def _probability(value):
    return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1


def row_errors(row):
    errors = []
    p0, p1, pick = row.get('p0'), row.get('p1'), row.get('pick')
    names = {row.get('team0', {}).get('name'), row.get('team1', {}).get('name')}

    if row.get('method') == 'unresolved':
        if p0 is not None or p1 is not None:
            return ['unresolved row contains a probability']
        if pick is None:
            return []
        if not isinstance(pick, dict):
            return ['unresolved pick must be an object or null']
        if pick.get('team') not in names:
            errors.append('settlement pick does not name a listed participant')
        if pick.get('probability') is not None:
            errors.append('settlement pick must not carry a probability')
        if row.get('pick_type') != 'settlement':
            errors.append('unresolved pick must be typed as a settlement pick')
        return errors

    if not _probability(p0) or not _probability(p1):
        return ['probabilities must be finite numbers in [0,1]']
    if abs(p0 + p1 - 1) > .002:
        errors.append('probabilities do not sum to one')
    side = 0 if p0 >= p1 else 1
    if not isinstance(pick, dict):
        return errors + ['missing pick']
    if pick.get('team') != row.get('team' + str(side), {}).get('name'):
        errors.append('pick names the wrong team')
    if not _probability(pick.get('probability')) or abs(pick['probability'] - max(p0, p1)) > .001:
        errors.append('pick probability differs from favourite')
    return errors
