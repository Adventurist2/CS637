from itertools import permutations

import numpy as np
import pytest

from sequin import GridSimulator, load_case
from sequin.defense import plan_protection
from sequin.search import Evaluator, SearchLimitError, prefix_tree, search


@pytest.fixture
def evaluator(make_grid):
    case = make_grid(demand=(0, 100, 10), capacities=(110,),
                     edges=((0, 1, 0.1, 200), (0, 2, 0.1, 200), (1, 2, 0.2, 40)))
    sim = GridSimulator(case, 1)
    return Evaluator(sim, sim.initialize())


def test_enum_matches_independent_direct_simulation(evaluator):
    sim, initial = evaluator.simulator, evaluator.initial
    scores = []
    for sequence in permutations(sim.case.line_ids, 2):
        state = initial
        for line in sequence:
            state = sim.respond(state, [line])
        scores.append(state.shed_mw)
    result = search(evaluator, "enum", 2)
    assert result.exhaustive
    assert len(result.sequences) == 6
    assert result.state.shed_mw == pytest.approx(max(scores), abs=1e-5)


@pytest.mark.parametrize("method", ["sequin", "sequin-release", "greedy-flow", "greedy-shed", "greedy-crit", "beam", "std", "perm"])
def test_searches_return_valid_sequences(evaluator, method):
    result = search(evaluator, method, 2, breadth=2)
    assert len(set(result.sequence)) == 2
    assert result.state.max_residual_pu < 2e-6
    assert result.state.shed_mw <= evaluator.simulator.case.total_demand_mw + 1e-5


def test_exact_search_guard_is_not_silent(evaluator):
    with pytest.raises(SearchLimitError):
        search(evaluator, "enum", 2, max_sequences=5)
    assert evaluator.response_evaluations == 0


def test_prefix_cache_preserves_order():
    sim = GridSimulator(load_case("14"))
    e = Evaluator(sim, sim.initialize())
    a, b = e.evaluate((1, 3)), e.evaluate((3, 1))
    count = e.response_evaluations
    assert e.evaluate((1, 3)) is a
    assert e.response_evaluations == count
    assert a.failed == b.failed
    assert a.shed_mw != pytest.approx(b.shed_mw)


def test_prefix_tree_aggregates_full_prefix(evaluator):
    sequences = [(1, 2), (1, 3), (2, 1)]
    tree = prefix_tree(evaluator, sequences)
    node = tree["tree"]["children"]["1"]
    values = [evaluator.evaluate(s).shed_mw for s in sequences[:2]]
    assert node["min_final_shed_mw"] == min(values)
    assert node["max_final_shed_mw"] == max(values)
    assert tree["tree"]["children"]["2"]["children"]["1"]["prefix"] == [2, 1]


def test_protection_reoptimizes_remaining_failures(make_grid):
    case = make_grid(demand=(0, 100, 10), capacities=(110,),
                     edges=((0, 1, 0.1, 200), (0, 2, 0.1, 200)))
    sim = GridSimulator(case, 1)
    result = plan_protection(sim, sim.initialize(), k=1, budget=1, method="enum")
    assert result.protected == (1,)
    assert result.baseline_shed_mw == pytest.approx(100, abs=1e-5)
    assert result.remaining_shed_mw == pytest.approx(10, abs=1e-5)
    assert result.adaptive_sequence == (2,)


def test_parallel_line_min_cut_width(make_grid):
    case = make_grid(edges=((0, 1, 0.1, 100), (0, 1, 0.1, 100)))
    sim = GridSimulator(case)
    props = Evaluator(sim, sim.initialize()).network_properties(sim.initialize())
    assert props["width"][1] == 2
    assert np.isinf(props["width"][0])


def test_heuristic_does_not_exceed_exhaustive_oracle(evaluator):
    optimum = search(evaluator, "enum", 2).state.shed_mw
    for method in ["sequin", "sequin-release", "greedy-flow", "greedy-shed", "beam"]:
        assert search(evaluator, method, 2, breadth=1).state.shed_mw <= optimum + 1e-5
