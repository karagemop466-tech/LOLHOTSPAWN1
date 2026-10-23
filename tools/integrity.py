"""Pure, fail-closed checks shared by the publish gate and regression tests."""
import math


def row_errors(row):
    errors = []
    p0, p1, pick = row.get('p0'), row.get('p1'), row.get('pick')
    if row.get('method') == 'unresolved':
        return ['unresolved row contains a probability or pick'] if any(v is not None for v in (p0, p1, pick)) else []
    def probability(value):
        return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1
    if not probability(p0) or not probability(p1):
        return ['probabilities must be finite numbers in [0,1]']
    if abs(p0 + p1 - 1) > .002:
        errors.append('probabilities do not sum to one')
    side = 0 if p0 >= p1 else 1
    if not isinstance(pick, dict):
        return errors + ['missing pick']
    if pick.get('team') != row.get('team' + str(side), {}).get('name'):
        errors.append('pick names the wrong team')
    if not probability(pick.get('probability')) or abs(pick['probability'] - max(p0, p1)) > .001:
        errors.append('pick probability differs from favourite')
    return errors
