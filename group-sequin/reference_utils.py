import math
import pandas as pd


def parse_sequence(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ()
    s = str(value).strip()
    if not s:
        return ()
    # Author outputs use ';' between rounds and sometimes '/' inside a round.
    out = []
    for token in s.replace('/', ';').split(';'):
        token = token.strip()
        if token:
            out.append(int(float(token)))
    return tuple(out)


def classify_error(percent):
    a = abs(float(percent))
    if a <= 1.0:
        return 'MATCH'
    if a <= 5.0:
        return 'CLOSE'
    return 'DIVERGED'


def safe_percent(ours, ref):
    if abs(ref) < 1e-12:
        return 0.0 if abs(ours) < 1e-12 else float('inf')
    return 100.0 * (ours - ref) / ref


def load_exp1(path):
    d = pd.read_csv(path)
    d['sequence'] = d['permutation'].map(parse_sequence)
    return d


def load_exp2(path):
    d = pd.read_csv(path)
    d['sequence'] = d['permutation'].map(parse_sequence)
    return d
