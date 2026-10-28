from itertools import combinations

import numpy as np
import pytest

from sequin import GridSimulator
from sequin import load_case
from sequin.extensions import (critical_loads, defense_objective, enumerate_outages,
                               exact_protection, robust_protection, timed_trace)
from sequin.search import Evaluator, SearchLimitError, search


def test_filtered_oracle_equals_new_adaptive_search(make_grid):
    c = make_grid(demand=(0, 70, 30), capacities=(100,),
                  edges=((0, 1, .1, 200), (0, 2, .1, 200), (1, 2, .2, 50)))
    sim = GridSimulator(c, .1)
    initial = sim.initialize()
    table = enumerate_outages(sim, initial, k=2)
    for line in c.line_ids:
        value, sequence = table.worst((line,))
        direct = search(Evaluator(sim, initial, (line,)), "enum", 2)
        assert value == pytest.approx(direct.state.shed_mw, abs=1e-5)
        assert line not in sequence
    with pytest.raises(ValueError):
        table.worst((1, 2))


def test_robust_plan_and_outer_oracle(make_grid):
    c = make_grid(demand=(0, 70, 30), capacities=(120,),
                  edges=((0, 1, .1, 200), (0, 2, .1, 200), (1, 2, .2, 50)))
    tables = []
    for seed in (0, 1):
        sim = GridSimulator(c.scenario(seed), .1)
        tables.append(enumerate_outages(sim, sim.initialize(), k=1))
    plan, history = robust_protection(tables, c.line_ids, 1)
    exact = exact_protection(tables, c.line_ids, 1)
    assert plan == exact
    assert history[0]["design_worst_fraction"] == defense_objective(tables, plan)[0]
    assert defense_objective(tables, exact) == min(defense_objective(tables, p) for p in combinations(c.line_ids, 1))
    with pytest.raises(SearchLimitError):
        exact_protection(tables, c.line_ids, 1, max_defenses=1)


def test_table_guard_precedes_solver_calls(make_grid):
    sim = GridSimulator(make_grid(edges=((0, 1, .1, 100), (0, 1, .1, 100))))
    initial = sim.initialize()
    before = sim.solve_count
    with pytest.raises(SearchLimitError):
        enumerate_outages(sim, initial, k=2, max_sequences=1)
    assert sim.solve_count == before


def test_critical_first_preserves_analytic_priority_and_total(make_grid):
    c = make_grid(demand=(0, 40, 60, 0), generators=(0, 3), capacities=(100, 50), costs=(1, 20),
                  edges=((0, 3, .1, 200), (3, 1, .1, 200), (3, 2, .1, 200)))
    sim = GridSimulator(c, 1, critical_buses=(1,))
    state = sim.respond(sim.initialize(), (1,))
    assert state.served[1] * 100 == pytest.approx(40, abs=5e-6)
    assert state.served.sum() * 100 == pytest.approx(50, abs=5e-6)
    assert state.max_residual_pu < 2e-6
    assert np.allclose(sim.service_weights, 1)


def test_weighted_service_and_validation(make_grid):
    c = make_grid(demand=(0, 40, 60, 0), generators=(0, 3), capacities=(100, 50), costs=(1, 20),
                  edges=((0, 3, .1, 200), (3, 1, .1, 200), (3, 2, .1, 200)))
    sim = GridSimulator(c, 1, service_weights=(1, 10, 1, 1))
    state = sim.respond(sim.initialize(), (1,))
    assert state.served[1] * 100 == pytest.approx(40, abs=5e-6)
    for weights in [(1,), (1, 0, 1, 1), (1, np.nan, 1, 1)]:
        with pytest.raises(ValueError):
            GridSimulator(c, service_weights=weights)
    with pytest.raises(ValueError):
        GridSimulator(c, critical_buses=(4,))
    assert critical_loads(c, .25) == critical_loads(c, .25)


def test_weighted_secondary_floor_respects_primal_scale():
    case = load_case("14").scenario(0)
    weights = np.ones(case.nbus)
    weights[list(critical_loads(case, .1))] = 10
    sim = GridSimulator(case, service_weights=weights)
    state = sim.respond(sim.respond(sim.initialize(), (3,)), (10,))
    assert state.max_residual_pu < 2e-6
    assert 0 <= state.shed_mw <= case.total_demand_mw


@pytest.mark.parametrize("policy", ["weight-2", "weight-10", "critical-first"])
def test_priority_near_fixed_service_floor_regression(policy):
    case = load_case("14").scenario(0)
    critical = critical_loads(case, .1)
    weights = np.ones(case.nbus)
    if policy.startswith("weight"):
        weights[list(critical)] = int(policy.split("-")[1])
    sim = GridSimulator(case, service_weights=weights,
                        critical_buses=critical if policy == "critical-first" else ())
    for sequence in ((6, 7), (7, 6), (3, 10)):
        state = sim.initialize()
        for line in sequence:
            state = sim.respond(state, (line,))
        assert state.max_residual_pu < 2e-6
        assert state.service_floor_tolerance_pu <= 1e-5


def test_large_case_secondary_floor_regression():
    sim = GridSimulator(load_case("118").scenario(1))
    for sequence in ((7, 8, 104), (8, 7, 104), (104, 7, 8)):
        state = sim.initialize()
        for line in sequence:
            state = sim.respond(state, (line,))
        assert state.max_residual_pu < 2e-6
        assert state.service_floor_tolerance_pu <= 1e-5


def test_timing_matches_equal_epochs_and_energy_accounting(make_grid):
    c = make_grid(demand=(0, 100), generators=(0, 1), capacities=(100, 100),
                  edges=((0, 1, .1, 200), (0, 1, .1, 200)))
    sim = GridSimulator(c, .1)
    initial = sim.initialize()
    result, states = timed_trace(sim, initial, (1, 2), (5, 5))
    expected = sim.respond(sim.respond(initial, (1,)), (2,))
    assert states[-1].shed_mw == pytest.approx(expected.shed_mw, abs=1e-5)
    assert result["snapshot_unserved_energy_mwh"] == pytest.approx(sum(s.shed_mw * 5 / 60 for s in states[1:]))
    assert result["horizon_minutes"] == 10
    simultaneous, sstates = timed_trace(sim, initial, (1, 2), (1, 9), simultaneous=True)
    assert simultaneous["horizon_minutes"] == 10
    assert len(sstates) == 3
    assert sstates[1].failed == frozenset((1, 2))
    assert simultaneous["windows"][1]["new_failures"] == []


@pytest.mark.parametrize("durations", [(0, 5), (-1, 11), (float("nan"), 5), (5,)])
def test_invalid_timing(make_grid, durations):
    c = make_grid(edges=((0, 1, .1, 200), (0, 1, .1, 200)))
    sim = GridSimulator(c)
    with pytest.raises(ValueError):
        timed_trace(sim, sim.initialize(), (1, 2), durations)
