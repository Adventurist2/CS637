from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pytest

from sequin.case import GridCase


@pytest.fixture
def make_grid():
    def make(demand=(0, 100), generators=(0,), capacities=(100,),
             edges=((0, 1, 0.1, 200),), costs=None, taps=None, shifts=None):
        n, g, m = len(demand), len(generators), len(edges)
        cost = np.zeros((g, 3))
        cost[:, 1] = np.arange(1, g + 1) if costs is None else costs
        return GridCase("synthetic", 100, np.arange(1, n + 1), np.array(demand, float) / 100,
                        np.array(generators), np.zeros(g), np.array(capacities, float) / 100,
                        np.ones(g, bool), np.array([e[0] for e in edges]),
                        np.array([e[1] for e in edges]), np.array([e[2] for e in edges]),
                        np.ones(m) if taps is None else np.array(taps),
                        np.zeros(m) if shifts is None else np.array(shifts),
                        np.array([e[3] for e in edges]) / 100,
                        np.full(m, -np.inf), np.full(m, np.inf), np.ones(m, bool), cost)
    return make
