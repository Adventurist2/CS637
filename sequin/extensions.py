"""Three bounded, reproducible research extensions to the SEQUIN DC model.

Protection changes outage eligibility only. A complete outage table can therefore
be filtered without re-solving identical physical responses for each defense.
"""

from dataclasses import dataclass
from itertools import combinations, permutations
from math import perm
from time import perf_counter

import numpy as np

from .search import Evaluator, SearchLimitError


@dataclass
class OutageTable:
    sequences: np.ndarray
    shed_mw: np.ndarray
    demand_mw: float
    response_evaluations: int
    optimizer_calls: int
    seconds: float
    max_residual_pu: float
    critical_shed_mw: np.ndarray

    def worst(self, protected=(), *, critical=False):
        mask = ~np.isin(self.sequences, tuple(protected)).any(axis=1)
        indices = np.flatnonzero(mask)
        if not len(indices):
            raise ValueError("Protection leaves no eligible outage sequence")
        values = self.critical_shed_mw if critical else self.shed_mw
        index = indices[np.argmax(values[indices])]
        return float(values[index]), tuple(int(i) for i in self.sequences[index])

    def rows(self):
        return [{"sequence": s.tolist(), "shed_mw": float(v), "critical_shed_mw": float(c)}
                for s, v, c in zip(self.sequences, self.shed_mw, self.critical_shed_mw)]


def enumerate_outages(simulator, initial, *, k=2, max_sequences=50_000,
                      simultaneous=False, critical_buses=()):
    """Exact finite-choice oracle under one fixed operator policy and scenario."""
    ids = simulator.case.line_ids
    if not isinstance(k, int) or not 1 <= k <= len(ids):
        raise ValueError("Invalid outage budget")
    count = perm(len(ids), k)  # Conservative guard also for simultaneous tables.
    if count > max_sequences:
        raise SearchLimitError(f"Outage table requires up to {count} sequences; limit {max_sequences}")
    start, before = perf_counter(), simulator.solve_count
    evaluator = Evaluator(simulator, initial)
    sequences = list(combinations(ids, k) if simultaneous else permutations(ids, k))
    states = [(evaluator.simultaneous if simultaneous else evaluator.evaluate)(s) for s in sequences]
    c = simulator.case
    critical = list(critical_buses)
    return OutageTable(np.asarray(sequences, dtype=int), np.array([s.shed_mw for s in states]),
                       c.total_demand_mw, evaluator.response_evaluations,
                       simulator.solve_count - before, perf_counter() - start,
                       max(s.max_residual_pu for s in evaluator.cache.values())
                       if not simultaneous else max(s.max_residual_pu for s in states),
                       np.array([float((c.demand[critical] - s.served[critical]).sum() * c.base_mva)
                                 for s in states]))


def defense_objective(tables, protected):
    fractions = [t.worst(protected)[0] / t.demand_mw for t in tables]
    return max(fractions), float(np.mean(fractions))


def robust_protection(tables, line_ids, budget=1):
    """Greedily minimize maximum design-scenario loss fraction, then its mean."""
    ids = tuple(sorted(set(line_ids)))
    if not tables or not isinstance(budget, int) or not 0 <= budget <= len(ids) - tables[0].sequences.shape[1]:
        raise ValueError("Invalid design scenarios or protection budget")
    if any(set(t.sequences.flat) != set(ids) for t in tables):
        raise ValueError("Design tables must cover the same line identities")
    protected, history = [], []
    for step in range(budget):
        options = [(defense_objective(tables, protected + [i]), i) for i in ids if i not in protected]
        score, chosen = min(options)
        protected.append(chosen)
        history.append({"step": step + 1, "line": chosen, "design_worst_fraction": score[0],
                        "design_mean_fraction": score[1], "candidates": len(options)})
    return tuple(protected), history


def exact_protection(tables, line_ids, budget=1, *, max_defenses=10_000):
    """Small-instance outer defense oracle; greedy selection has no such guarantee."""
    from math import comb
    if not tables or not isinstance(budget, int) or not 0 <= budget <= len(line_ids) - tables[0].sequences.shape[1]:
        raise ValueError("Invalid protection budget")
    if comb(len(line_ids), budget) > max_defenses:
        raise SearchLimitError("Too many defense sets for exact outer verification")
    return min(combinations(sorted(line_ids), budget), key=lambda p: (defense_objective(tables, p), p))


def critical_loads(case, fraction=0.25, *, seed=17):
    """Reproducible SYNTHETIC group: random positive-demand buses, at least one."""
    if not 0 < fraction <= 1:
        raise ValueError("Critical bus fraction must be in (0, 1]")
    positive = np.flatnonzero(case.demand > 0)
    if not len(positive):
        raise ValueError("No positive loads")
    chosen = np.random.default_rng(seed).choice(positive, max(1, int(np.ceil(len(positive) * fraction))), replace=False)
    return tuple(sorted(int(i) for i in chosen))


def service_metrics(case, state, critical_buses):
    indices = list(critical_buses)
    critical_demand = float(case.demand[indices].sum() * case.base_mva)
    critical_shed = max(0.0, float((case.demand[indices] - state.served[indices]).sum() * case.base_mva))
    return {"shed_mw": state.shed_mw, "critical_demand_mw": critical_demand,
            "critical_shed_mw": critical_shed,
            "critical_retained_fraction": 1 - critical_shed / max(critical_demand, 1e-12),
            "noncritical_shed_mw": max(0.0, state.shed_mw - critical_shed)}


def timed_trace(simulator, initial, sequence, durations_minutes, *, reference_minutes=5.0,
                simultaneous=False):
    """Response-then-hold discrete windows, with a declared snapshot energy proxy.

    Each window has one endpoint response using R_g * duration, R_g derived from
    ramp_fraction * Pmax / reference_minutes. Its endpoint shed is charged over
    the whole window. This is a discrete proxy, not integration of a trajectory
    during ramping. Intra-window service and transient feasibility are unmodeled.
    Both sequential and simultaneous runs have the SAME decision windows.
    """
    sequence = tuple(sequence)
    durations = np.asarray(durations_minutes, dtype=float)
    if (not sequence or len(sequence) != len(set(sequence)) or
        not set(sequence).issubset(simulator.case.line_ids)):
        raise ValueError("Use a nonempty sequence of distinct available lines")
    if (durations.shape != (len(sequence),) or not np.isfinite(durations).all() or
        np.any(durations <= 0) or not np.isfinite(reference_minutes) or reference_minutes <= 0):
        raise ValueError("Use one positive finite duration per event and a positive reference epoch")
    states, windows, energy, elapsed = [initial], [], 0.0, 0.0
    for step, (line, minutes) in enumerate(zip(sequence, durations)):
        failures = sequence if simultaneous and step == 0 else (() if simultaneous else (line,))
        state = simulator.respond(states[-1], failures,
                                  ramp_fraction=simulator.ramp_fraction * minutes / reference_minutes)
        contribution = state.shed_mw * minutes / 60
        windows.append({"window": step + 1, "start_min": elapsed, "duration_min": float(minutes),
                        "new_failures": list(failures), "shed_mw": state.shed_mw,
                        "snapshot_energy_mwh": contribution})
        energy += contribution
        elapsed += float(minutes)
        states.append(state)
    return {"sequence": list(sequence), "simultaneous": simultaneous, "horizon_minutes": elapsed,
            "reference_minutes": reference_minutes, "final_shed_mw": states[-1].shed_mw,
            "snapshot_unserved_energy_mwh": energy, "windows": windows,
            "energy_semantics": "Response-then-hold snapshot proxy; intra-window ramp trajectories are not simulated",
            "max_residual_pu": max(s.max_residual_pu for s in states)}, states
