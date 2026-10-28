from dataclasses import replace

import numpy as np
import pytest

from sequin import GridSimulator, SolverError, load_case


def check_physical_balance(case, state):
    balance = state.injection - state.served
    np.add.at(balance, case.gen_bus, state.generation)
    np.add.at(balance, case.branch_from, -state.flow)
    np.add.at(balance, case.branch_to, state.flow)
    assert np.max(np.abs(balance)) < 2e-6
    assert np.all(np.abs(state.flow) <= case.rating + 2e-6)
    assert np.all(state.generation <= case.pmax + 2e-6)


def test_initial_balance_and_economic_dispatch(make_grid):
    case = make_grid(demand=(0, 80), generators=(0, 1), capacities=(100, 100), costs=(1, 20))
    initial = GridSimulator(case).initialize()
    assert initial.shed_mw < 1e-6
    assert initial.generation * 100 == pytest.approx([80, 0], abs=1e-5)
    check_physical_balance(case, initial)


def test_isolation_and_emergency_shutdown(make_grid):
    case = make_grid(demand=(0, 80))
    sim = GridSimulator(case, ramp_fraction=0)
    final = sim.respond(sim.initialize(), [1])
    assert final.shed_mw == pytest.approx(80, abs=1e-5)
    assert final.generation[0] == pytest.approx(0)
    assert not final.online[0]
    assert final.flow[0] == 0
    check_physical_balance(case, final)


def test_ramp_and_irreversible_load_shedding(make_grid):
    case = make_grid(generators=(0, 1), capacities=(100, 100), costs=(1, 20))
    sim = GridSimulator(case, ramp_fraction=0.1)
    initial = sim.initialize()
    final = sim.respond(initial, [1])
    assert final.shed_mw == pytest.approx(90, abs=1e-5)
    assert final.generation[1] * 100 == pytest.approx(10, abs=1e-5)
    later = sim.respond(final, [])
    assert later.shed_mw == pytest.approx(90, abs=1e-5)
    assert np.all(later.served <= final.served + 1e-8)
    assert not later.online[0]


def test_off_generator_cannot_restart(make_grid):
    case = make_grid(generators=(0, 1), capacities=(100, 100))
    sim = GridSimulator(case, 1)
    initial = sim.initialize()
    previous = replace(initial, online=np.array([False, True]), generation=np.zeros(2))
    final = sim.respond(previous, [])
    assert not final.online[0]
    assert final.generation[0] == 0


def test_parallel_lines_keep_separate_identity(make_grid):
    case = make_grid(demand=(0, 80), edges=((0, 1, 0.1, 100), (0, 1, 0.1, 100)))
    sim = GridSimulator(case, 1)
    initial = sim.initialize()
    final = sim.respond(initial, [1])
    assert final.shed_mw < 1e-5
    assert final.flow * 100 == pytest.approx([0, 80], abs=1e-5)
    assert abs(final.theta[0] - final.theta[1]) > 0.01


def test_transformer_phase_shift(make_grid):
    case = make_grid(demand=(0, 80), taps=(1.1,), shifts=(0.05,))
    state = GridSimulator(case).initialize()
    assert state.flow[0] == pytest.approx(0.8, abs=1e-6)
    assert state.theta[0] - state.theta[1] == pytest.approx(0.8 * 0.1 * 1.1 + 0.05, abs=1e-6)


def test_negative_reactance_supported(make_grid):
    case = make_grid(demand=(0, 80), edges=((0, 1, -0.1, 100),))
    state = GridSimulator(case).initialize()
    check_physical_balance(case, state)
    assert state.theta[0] - state.theta[1] < 0


def test_negative_load_injection_contributes_to_balance(make_grid):
    case = replace(make_grid(demand=(0, 80)), injection=np.array([0, 0.2]))
    sim = GridSimulator(case, 1)
    initial = sim.initialize()
    assert initial.generation[0] * 100 == pytest.approx(60, abs=1e-5)
    final = sim.respond(initial, [1])
    assert final.served[1] * 100 == pytest.approx(20, abs=1e-5)
    assert final.shed_mw == pytest.approx(60, abs=1e-5)
    check_physical_balance(case, final)


def test_shed_demand_never_decreases_over_a_sequence():
    sim = GridSimulator(load_case("39").scenario(3))
    state = sim.initialize()
    shed = [state.shed_mw]
    for line in [1, 2, 3, 4]:
        previous = state
        state = sim.respond(state, [line])
        assert np.all(state.served <= previous.served + 2e-6)
        online = state.online
        assert np.all(np.abs(state.generation[online] - previous.generation[online]) <=
                      0.1 * sim.case.pmax[online] + 2e-6)
        shed.append(state.shed_mw)
    assert all(b >= a - 1e-5 for a, b in zip(shed, shed[1:]))


def test_quadratic_initial_cost(make_grid):
    case = make_grid(demand=(0, 100), generators=(0, 1), capacities=(100, 100), costs=(0, 0))
    cost = np.array([[1, 0, 0], [1, 0, 0]], float)
    state = GridSimulator(replace(case, cost=cost)).initialize()
    assert state.generation * 100 == pytest.approx([50, 50], abs=0.01)


def test_infeasible_initial_demand_is_reported(make_grid):
    case = make_grid(demand=(0, 200), capacities=(100,))
    with pytest.raises(SolverError, match="not finish optimally"):
        GridSimulator(case).initialize()


def test_thermal_limit_can_require_shedding(make_grid):
    case = make_grid(demand=(0, 80), edges=((0, 1, 0.1, 100),))
    initial = GridSimulator(case).initialize()
    restricted = replace(case, rating=np.array([0.3]))
    state = GridSimulator(restricted, 1).respond(initial, [])
    assert state.shed_mw == pytest.approx(50, abs=1e-5)


@pytest.mark.parametrize("ramp", [-1, float("nan"), float("inf")])
def test_invalid_ramp(make_grid, ramp):
    with pytest.raises(ValueError):
        GridSimulator(make_grid(), ramp)


def test_invalid_and_repeated_outage(make_grid):
    sim = GridSimulator(make_grid())
    initial = sim.initialize()
    with pytest.raises(ValueError):
        sim.respond(initial, [2])
    with pytest.raises(ValueError):
        sim.respond(initial, [1, 1])
    state = sim.respond(initial, [1])
    with pytest.raises(ValueError):
        sim.respond(state, [1])


@pytest.mark.parametrize("name", ["14", "39", "60", "118", "162", "240"])
def test_supplied_case_initial_and_outage_balance(name):
    case = load_case(name).scenario(17)
    sim = GridSimulator(case)
    initial = sim.initialize()
    check_physical_balance(case, initial)
    final = sim.respond(initial, [case.line_ids[0]])
    check_physical_balance(case, final)
    assert final.shed_mw >= -1e-6


def test_failure_order_changes_result_on_ieee14():
    sim = GridSimulator(load_case("14"))
    initial = sim.initialize()
    forward = sim.respond(sim.respond(initial, [1]), [3])
    reverse = sim.respond(sim.respond(initial, [3]), [1])
    assert forward.failed == reverse.failed
    assert abs(forward.shed_mw - reverse.shed_mw) > 10


def test_zero_ramp_secondary_solve_regression():
    sim = GridSimulator(load_case("39").scenario(0), ramp_fraction=0)
    state = sim.respond(sim.respond(sim.initialize(), [9]), [33])
    check_physical_balance(sim.case, state)
    assert state.max_residual_pu < 2e-6
