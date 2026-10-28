import numpy as np
import pytest

from sequin import GridSimulator
from sequin.reference_compat import OriginalDCPResponse, case_from_original_export


def test_reference_dcp_uses_series_susceptance_and_ignores_tap(make_grid):
    original = make_grid(demand=(0, 100), taps=(1.5,), shifts=(0.4,))
    export = {"loads": [{"id": 1, "bus": 2, "pd": 1}],
              "generators": [{"id": 1, "bus": 1, "pmin": 0, "pmax": 1}],
              "branches": [{"id": 1, "r": 0.1, "x": 0.1}]}
    case = case_from_original_export(original, export)
    state = GridSimulator(case).initialize()
    assert case.reactance[0] == pytest.approx(0.2)
    assert case.tap[0] == 1 and case.shift[0] == 0
    assert state.theta[0] - state.theta[1] == pytest.approx(0.2)


def test_reference_bridge_explicitly_rejects_negative_loads(make_grid):
    with pytest.raises(ValueError, match="nonnegative"):
        case_from_original_export(make_grid(), {"loads": [{"id": 1, "bus": 2, "pd": -1}]})
