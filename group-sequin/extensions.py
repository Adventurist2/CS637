"""Preparedness, response timing and service-priority extensions.

All physical responses use this repository's grid_model.defend, not the other
project's simulator. Default dispatch preserves the group's restart semantics
and single-objective tie selection. Line IDs are one-based branch rows.
"""
from dataclasses import dataclass
from itertools import combinations, permutations
from math import comb, perm
import numpy as np

from grid_model import active_lines, defend, initial_state, total_load


def demand(case):
    return np.maximum(case['bus'][:, 2], 0) + np.maximum(case['bus'][:, 4], 0)


def critical_group(case, fraction=.25, seed=17):
    if not 0 < fraction <= 1:
        raise ValueError('fraction must be in (0,1]')
    positive = np.flatnonzero(demand(case) > 0)
    return tuple(sorted(np.random.default_rng(seed).choice(
        positive, max(1, int(np.ceil(len(positive) * fraction))), replace=False).tolist()))


def policy_options(case, policy='total', critical=()):
    if policy == 'total':
        return {}
    if policy == 'critical-first':
        return {'critical_buses': tuple(critical)}
    if policy not in ('weight-2', 'weight-10'):
        raise ValueError('unknown policy')
    weights = np.ones(len(case['bus']))
    weights[list(critical)] = int(policy.split('-')[1])
    return {'service_weights': weights}


def metrics(case, state, critical=()):
    loss = demand(case) - state['served']
    critical_demand = float(demand(case)[list(critical)].sum())
    critical_shed = max(0., float(loss[list(critical)].sum()))
    return {'shed_mw': max(0., float(loss.sum())),
            'critical_shed_mw': critical_shed, 'critical_demand_mw': critical_demand,
            'critical_retained_fraction': 1 - critical_shed / max(critical_demand, 1e-12),
            'max_residual': state.get('max_residual', 0.),
            'service_floor_tolerance_mw': state.get('service_floor_tolerance_mw', 0.)}


class Evaluator:
    """Cache complete ordered prefixes, never merely the failed-line set."""
    def __init__(self, case, ramp=.1, *, policy='total', critical=(), start=None,
                 protected=(), cost_tiebreak=False):
        self.case, self.ramp = case, ramp
        self.critical = tuple(critical)
        self.options = policy_options(case, policy, critical)
        self.options['cost_tiebreak'] = cost_tiebreak
        self.lines = tuple(i for i, _ in active_lines(case, ()) if i not in protected)
        self.cache = {(): initial_state(case) if start is None else start}
        self.response_evaluations = self.optimizer_calls = 0
        self.max_residual = self.max_service_floor = 0.

    def response(self, previous, failed, ramp=None):
        state = defend(self.case, failed, previous, self.ramp if ramp is None else ramp, **self.options)
        if state is None:
            raise RuntimeError(f'Defender did not return an optimum: failures={failed}')
        self.response_evaluations += 1
        self.optimizer_calls += state['optimizer_calls']
        self.max_residual = max(self.max_residual, state['max_residual'])
        self.max_service_floor = max(self.max_service_floor, state['service_floor_tolerance_mw'])
        if np.any(state['served'] > previous['served'] + 2e-4):
            raise RuntimeError('Irreversible service constraint violated')
        return state

    def evaluate(self, sequence):
        sequence = tuple(int(i) for i in sequence)
        if len(sequence) != len(set(sequence)) or not set(sequence).issubset(self.lines):
            raise ValueError('sequence must contain distinct eligible line IDs')
        if sequence not in self.cache:
            self.cache[sequence] = self.response(self.evaluate(sequence[:-1]), sequence)
        return self.cache[sequence]

    def guided(self, k=2, top_n=10, *, critical_score=False):
        """Group's released-style search, with optional critical-loss scoring."""
        if not 1 <= k <= len(self.lines) or top_n < 1:
            raise ValueError('invalid attack budget or shortlist')
        def shortlist(state, failed):
            return sorted((i for i in state['flows'] if i in self.lines and i not in failed),
                          key=lambda i: (-abs(state['flows'][i]), i))[:top_n]
        def score(seq):
            m = metrics(self.case, self.evaluate(seq), self.critical)
            return m['critical_shed_mw' if critical_score else 'shed_mw']
        sequences = []
        for first in shortlist(self.cache[()], ()):
            seq = (first,)
            self.evaluate(seq)
            while len(seq) < k:
                options = [seq + (i,) for i in shortlist(self.evaluate(seq), seq)]
                # Original group's cut-impact tolerance and smaller-ID tie rule.
                best, value = None, -1.
                for option in options:
                    v = score(option)
                    if v > value + 1e-8 or (abs(v-value) <= 1e-8 and (best is None or option[-1] < best[-1])):
                        best, value = option, v
                seq = best
            sequences.append(seq)
        return max(sequences, key=score)

    def flow(self, k=2):
        seq = ()
        for _ in range(k):
            state = self.evaluate(seq)
            line = max((i for i in state['flows'] if i in self.lines and i not in seq),
                       key=lambda i: (abs(state['flows'][i]), i))
            seq += (line,)
        self.evaluate(seq)
        return seq


@dataclass
class OutageTable:
    sequences: np.ndarray
    shed_mw: np.ndarray
    demand_mw: float

    def worst(self, protected=()):
        keep = np.flatnonzero(~np.isin(self.sequences, tuple(protected)).any(axis=1))
        if not len(keep):
            raise ValueError('no eligible outage sequence')
        i = keep[np.argmax(self.shed_mw[keep])]
        return float(self.shed_mw[i]), tuple(int(i) for i in self.sequences[i])


def enumerate_outages(evaluator, k=2, simultaneous=False, max_sequences=50000):
    ids = evaluator.lines
    if not 1 <= k <= len(ids):
        raise ValueError('invalid outage budget')
    count = comb(len(ids), k) if simultaneous else perm(len(ids), k)
    if count > max_sequences:
        raise ValueError(f'{count} sequences exceed limit {max_sequences}')
    sequences = list(combinations(ids, k) if simultaneous else permutations(ids, k))
    losses = []
    for sequence in sequences:
        state = evaluator.response(evaluator.cache[()], sequence) if simultaneous else evaluator.evaluate(sequence)
        losses.append(metrics(evaluator.case, state)['shed_mw'])
    return OutageTable(np.array(sequences, int), np.array(losses), float(total_load(evaluator.case)))


def defense_objective(tables, protected):
    values = [t.worst(protected)[0] / t.demand_mw for t in tables]
    return max(values), float(np.mean(values))


def protection(tables, lines, budget=2, exact=False, max_defenses=10000):
    ids = tuple(sorted(lines))
    if not tables or not 0 <= budget <= len(ids)-tables[0].sequences.shape[1]:
        raise ValueError('invalid defense budget')
    if exact:
        if comb(len(ids), budget) > max_defenses:
            raise ValueError('too many exact defense sets')
        return min(combinations(ids, budget), key=lambda p: (defense_objective(tables, p), p))
    protected = ()
    for _ in range(budget):
        line = min((i for i in ids if i not in protected),
                   key=lambda i: (defense_objective(tables, protected+(i,)), i))
        protected += (line,)
    return protected


def timed_trace(evaluator, sequence, durations, reference_minutes=5., simultaneous=False):
    sequence, durations = tuple(sequence), np.asarray(durations, float)
    if (not sequence or len(sequence) != len(set(sequence)) or not set(sequence).issubset(evaluator.lines)
        or durations.shape != (len(sequence),) or not np.isfinite(durations).all()
        or np.any(durations <= 0) or not np.isfinite(reference_minutes) or reference_minutes <= 0):
        raise ValueError('distinct eligible lines and positive finite time windows are required')
    previous, windows, failed = evaluator.cache[()], [], ()
    for j, (line, minutes) in enumerate(zip(sequence, durations)):
        failed = sequence if simultaneous else failed + (line,)
        previous = evaluator.response(previous, failed, evaluator.ramp*minutes/reference_minutes)
        windows.append({'window': j+1, 'duration_minutes': float(minutes),
                        'new_failures': list(sequence if simultaneous and j == 0 else (() if simultaneous else (line,))),
                        **metrics(evaluator.case, previous, evaluator.critical),
                        'pg_mw': previous['pg'].tolist(), 'served_mw': previous['served'].tolist()})
    return {'sequence': list(sequence), 'durations': durations.tolist(), 'simultaneous': simultaneous,
            'final_shed_mw': windows[-1]['shed_mw'],
            'snapshot_unserved_energy_mwh': sum(w['shed_mw']*w['duration_minutes']/60 for w in windows),
            'max_residual': evaluator.max_residual,
            'energy_semantics': 'Response-then-hold snapshot proxy, not continuous physical energy',
            'windows': windows}
