"""Explicit compatibility helpers for controlled original-PowerModels checks.

The normal simulator remains a MATPOWER DC model. PowerModels 0.21.3's
DCPPowerModel instead uses imag(1/(r+jx)) and ignores transformer tap/shift.
This module makes that difference explicit; it is not a silent model change.
"""

from dataclasses import replace

import numpy as np

from .physics import GridSimulator, GridState


def case_from_original_export(case, scenario):
    by_bus = {int(bus): i for i, bus in enumerate(case.bus_ids)}
    demand = np.zeros(case.nbus)
    for load in scenario["loads"]:
        if load["pd"] < -1e-12:
            raise ValueError("Controlled bridge currently supports nonnegative original loads only")
        demand[by_bus[int(load["bus"])]] += load["pd"]
    effective_x = case.reactance.copy()
    for branch in scenario["branches"]:
        i = int(branch["id"]) - 1
        r, x = branch["r"], branch["x"]
        effective_x[i] = (r * r + x * x) / x
    available = np.zeros(case.ngen, dtype=bool)
    pmin, pmax = np.zeros(case.ngen), np.zeros(case.ngen)
    for gen in scenario["generators"]:
        i = int(gen["id"]) - 1
        available[i] = True
        pmin[i], pmax[i] = gen["pmin"], gen["pmax"]
    return replace(case, demand=demand, injection=np.zeros(case.nbus), reactance=effective_x,
                   tap=np.ones(case.nbranch), shift=np.zeros(case.nbranch),
                   gen_available=available, pmin=pmin, pmax=pmax)


class OriginalDCPResponse(GridSimulator):
    """Replicate the released code's absence of cross-round on/off persistence."""

    def respond(self, previous, newly_failed, *, ramp_fraction=None):
        # In the released code, generator status is not carried between rounds.
        previous = replace(previous, online=self.case.gen_available.copy())
        return super().respond(previous, newly_failed, ramp_fraction=ramp_fraction)


def previous_state_from_export(case, scenario, step):
    by_bus = {int(bus): i for i, bus in enumerate(case.bus_ids)}
    served, generation = np.zeros(case.nbus), np.zeros(case.ngen)
    load_bus = {int(v["id"]): by_bus[int(v["bus"])] for v in scenario["loads"]}
    for key, value in step["previous"]["loads"].items():
        served[load_bus[int(key)]] += value
    for key, value in step["previous"]["generation"].items():
        generation[int(key) - 1] = value
    previous_failed = frozenset(int(i) for i in step["failed"][:-1])
    return GridState(previous_failed, generation, served, np.zeros(case.nbranch), np.zeros(case.nbus),
                     case.gen_available.copy(), float((case.demand - served).sum() * case.base_mva),
                     0, 0, 0, np.zeros(case.nbus), len(previous_failed))
