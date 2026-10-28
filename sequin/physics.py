"""DC optimal power flow and myopic, stateful load-shedding MILPs."""

from dataclasses import dataclass
from time import perf_counter

import highspy
import networkx as nx
import numpy as np
from scipy.sparse import coo_matrix, csc_matrix

from .case import GridCase


class SolverError(RuntimeError):
    pass


@dataclass(frozen=True)
class GridState:
    failed: frozenset[int]
    generation: np.ndarray
    served: np.ndarray
    flow: np.ndarray
    theta: np.ndarray
    online: np.ndarray
    shed_mw: float
    max_residual_pu: float
    solver_seconds: float
    mip_gap: float
    injection: np.ndarray
    round: int = 0
    service_floor_tolerance_pu: float = 0.0

    def to_dict(self, case: GridCase):
        scale = case.base_mva
        return {"round": self.round, "failed_lines": sorted(self.failed),
                "shed_mw": self.shed_mw, "shed_fraction": self.shed_mw / max(case.total_demand_mw, 1e-12),
                "generation_mw": (self.generation * scale).tolist(),
                "negative_load_injection_mw": (self.injection * scale).tolist(),
                "served_mw": (self.served * scale).tolist(), "flow_mw": (self.flow * scale).tolist(),
                "angles_rad": self.theta.tolist(), "generator_online": self.online.tolist(),
                "max_residual_pu": self.max_residual_pu, "solver_seconds": self.solver_seconds,
                "mip_gap": self.mip_gap,
                "service_floor_tolerance_pu": self.service_floor_tolerance_pu}


class _Rows:
    def __init__(self, nvar):
        self.nvar, self.rows, self.cols, self.values, self.lo, self.hi = nvar, [], [], [], [], []

    def add(self, coefficients, lo, hi):
        r = len(self.lo)
        for c, v in coefficients.items():
            if v != 0:
                self.rows.append(r)
                self.cols.append(c)
                self.values.append(v)
        self.lo.append(lo)
        self.hi.append(hi)

    def matrix(self):
        return coo_matrix((self.values, (self.rows, self.cols)),
                          shape=(len(self.lo), self.nvar)).tocsc()


class GridSimulator:
    def __init__(self, case: GridCase, ramp_fraction=0.1, *, tie_break="cost",
                 mip_gap=1e-8, time_limit=60.0, service_weights=None, critical_buses=()):
        if not np.isfinite(ramp_fraction) or ramp_fraction < 0:
            raise ValueError("Ramp fraction must be finite and nonnegative")
        if tie_break not in ("cost", "none"):
            raise ValueError("tie_break must be cost or none")
        if not 0 <= mip_gap <= 1 or not np.isfinite(time_limit) or time_limit <= 0:
            raise ValueError("Invalid solver gap or time limit")
        self.case, self.ramp_fraction = case, float(ramp_fraction)
        self.tie_break, self.mip_gap, self.time_limit = tie_break, mip_gap, time_limit
        self.service_weights = np.ones(case.nbus) if service_weights is None else np.asarray(service_weights, float).copy()
        if self.service_weights.shape != (case.nbus,) or not np.isfinite(self.service_weights).all() or np.any(self.service_weights <= 0):
            raise ValueError("Use one finite positive service weight per bus")
        critical = tuple(critical_buses)
        if any(not isinstance(i, (int, np.integer)) or i < 0 or i >= case.nbus for i in critical):
            raise ValueError("Critical buses must be valid zero-based bus indices")
        self.critical_buses = tuple(sorted(set(critical)))
        self.solve_count = 0
        c = case
        self.th = np.arange(c.nbus)
        self.pg = np.arange(c.ngen) + c.nbus
        self.fl = np.arange(c.nbranch) + c.nbus + c.ngen
        self.ld = np.arange(c.nbus) + c.nbus + c.ngen + c.nbranch
        self.z = np.arange(c.ngen) + 2 * c.nbus + c.ngen + c.nbranch
        self.inj = np.arange(c.nbus) + 2 * c.nbus + 2 * c.ngen + c.nbranch
        self.nvar = 3 * c.nbus + 2 * c.ngen + c.nbranch

    def graph(self, failed=frozenset()):
        graph = nx.MultiGraph()
        graph.add_nodes_from(range(self.case.nbus))
        for line in self.case.line_ids:
            if line not in failed:
                i = line - 1
                graph.add_edge(int(self.case.branch_from[i]), int(self.case.branch_to[i]), key=line)
        return graph

    def _model(self, failed, previous, ramp_fraction):
        c = self.case
        lower, upper = np.full(self.nvar, -np.inf), np.full(self.nvar, np.inf)
        lower[self.pg], upper[self.pg] = np.minimum(c.pmin, 0), c.pmax
        lower[self.ld], upper[self.ld] = 0, c.demand if previous is None else previous.served
        lower[self.inj] = 0
        upper[self.inj] = c.injections if previous is None else previous.injection
        if previous is None:
            lower[self.ld] = c.demand
            lower[self.inj] = c.injections
        lower[self.z] = 0
        upper[self.z] = c.gen_available if previous is None else previous.online & c.gen_available
        lower[self.fl], upper[self.fl] = -c.rating, c.rating
        rows = _Rows(self.nvar)
        for i in range(c.nbus):
            coefficients = {int(self.ld[i]): -1.0, int(self.inj[i]): 1.0}
            for g in np.flatnonzero(c.gen_bus == i):
                coefficients[int(self.pg[g])] = 1.0
            for e in np.flatnonzero(c.branch_from == i):
                coefficients[int(self.fl[e])] = coefficients.get(int(self.fl[e]), 0) - 1
            for e in np.flatnonzero(c.branch_to == i):
                coefficients[int(self.fl[e])] = coefficients.get(int(self.fl[e]), 0) + 1
            rows.add(coefficients, 0, 0)
        for e in range(c.nbranch):
            if not c.branch_available[e] or e + 1 in failed:
                lower[self.fl[e]] = upper[self.fl[e]] = 0
                continue
            a, b = int(c.branch_from[e]), int(c.branch_to[e])
            susceptance = 1 / (c.reactance[e] * c.tap[e])
            # f = (theta_from - theta_to - phase_shift) / (x * tap).
            rows.add({int(self.fl[e]): 1, int(self.th[a]): -susceptance,
                      int(self.th[b]): susceptance}, -susceptance * c.shift[e], -susceptance * c.shift[e])
            rows.add({int(self.th[a]): 1, int(self.th[b]): -1}, c.angle_min[e], c.angle_max[e])
        for component in nx.connected_components(self.graph(failed)):
            reference = min(component)
            lower[self.th[reference]] = upper[self.th[reference]] = 0
        integrality = np.zeros(self.nvar, dtype=int)
        if previous is None:
            lower[self.pg] = c.pmin
            upper[self.pg] = np.where(c.gen_available, c.pmax, 0)
            lower[self.pg] = np.where(c.gen_available, lower[self.pg], 0)
            lower[self.z] = upper[self.z]
        else:
            integrality[self.z] = 1
            allowance = ramp_fraction * c.pmax
            for g in range(c.ngen):
                low = max(c.pmin[g], previous.generation[g] - allowance[g], 0)
                high = min(c.pmax[g], previous.generation[g] + allowance[g])
                rows.add({int(self.pg[g]): 1, int(self.z[g]): -max(high, 0)}, -np.inf, 0)
                rows.add({int(self.pg[g]): 1, int(self.z[g]): -low}, 0, np.inf)
        return rows, lower, upper, integrality

    def _solve(self, rows, lower, upper, integrality, objective, quadratic=None, *, presolve=True):
        h = highspy.Highs()
        for key, value in {"output_flag": False, "threads": 1, "random_seed": 0,
                           "mip_rel_gap": self.mip_gap, "time_limit": self.time_limit,
                           "primal_feasibility_tolerance": 1e-8,
                           "mip_feasibility_tolerance": 1e-8}.items():
            h.setOptionValue(key, value)
        if not presolve:
            h.setOptionValue("presolve", "off")
        model = highspy.HighsModel()
        lp = model.lp_
        lp.num_col_, lp.num_row_ = self.nvar, len(rows.lo)
        lp.col_cost_, lp.col_lower_, lp.col_upper_ = objective, lower, upper
        lp.row_lower_, lp.row_upper_ = np.array(rows.lo), np.array(rows.hi)
        matrix = rows.matrix()
        lp.a_matrix_.format_ = highspy.MatrixFormat.kColwise
        lp.a_matrix_.start_ = matrix.indptr.astype(np.int32)
        lp.a_matrix_.index_ = matrix.indices.astype(np.int32)
        lp.a_matrix_.value_ = matrix.data
        lp.integrality_ = [highspy.HighsVarType.kInteger if i else highspy.HighsVarType.kContinuous
                           for i in integrality]
        if quadratic is not None and np.any(quadratic):
            q = csc_matrix(np.diag(quadratic))
            model.hessian_.dim_ = self.nvar
            model.hessian_.format_ = highspy.HessianFormat.kTriangular
            model.hessian_.start_ = q.indptr.astype(np.int32)
            model.hessian_.index_ = q.indices.astype(np.int32)
            model.hessian_.value_ = q.data
        status = h.passModel(model)
        if status == highspy.HighsStatus.kError:
            raise SolverError("HiGHS rejected the optimization model")
        h.run()
        self.solve_count += 1
        if h.getModelStatus() != highspy.HighsModelStatus.kOptimal:
            raise SolverError(f"Optimization did not finish optimally: {h.modelStatusToString(h.getModelStatus())}")
        x = np.asarray(h.getSolution().col_value)
        activity = matrix @ x
        residual = max(float(np.maximum(lower - x, 0).max(initial=0)),
                       float(np.maximum(x - upper, 0).max(initial=0)),
                       float(np.maximum(np.array(rows.lo) - activity, 0).max(initial=0)),
                       float(np.maximum(activity - np.array(rows.hi), 0).max(initial=0)),
                       float(np.abs(x[integrality > 0] - np.rint(x[integrality > 0])).max(initial=0)))
        if residual > 2e-6 or not np.isfinite(x).all():
            raise SolverError(f"Invalid primal solution: residual={residual}")
        gap = h.getInfo().mip_gap
        return x, residual, float(gap) if np.isfinite(gap) and gap >= 0 else 0.0

    def _pack(self, x, failed, residual, seconds, gap, round_number, service_tolerance=0.0):
        c = self.case
        served = np.clip(x[self.ld], 0, c.demand)
        return GridState(frozenset(failed), x[self.pg].copy(), served, x[self.fl].copy(),
                         x[self.th].copy(), x[self.z] > 0.5,
                         max(0.0, float((c.demand - served).sum() * c.base_mva)),
                         residual, seconds, gap, np.clip(x[self.inj], 0, c.injections), round_number,
                         service_tolerance)

    def initialize(self):
        start = perf_counter()
        rows, lower, upper, integrality = self._model(frozenset(), None, 1)
        objective, quadratic = np.zeros(self.nvar), np.zeros(self.nvar)
        objective[self.pg] = self.case.cost[:, 1] * self.case.base_mva
        quadratic[self.pg] = 2 * self.case.cost[:, 0] * self.case.base_mva ** 2
        x, residual, gap = self._solve(rows, lower, upper, integrality, objective, quadratic)
        return self._pack(x, frozenset(), residual, perf_counter() - start, gap, 0)

    def respond(self, previous: GridState, newly_failed, *, ramp_fraction=None):
        new = tuple(int(i) for i in newly_failed)
        if len(set(new)) != len(new) or any(i in previous.failed for i in new):
            raise ValueError("A line may fail only once")
        if any(i not in self.case.line_ids for i in new):
            raise ValueError("Unknown or initially unavailable line ID")
        ramp = self.ramp_fraction if ramp_fraction is None else float(ramp_fraction)
        if not np.isfinite(ramp) or ramp < 0:
            raise ValueError("Ramp allowance must be finite and nonnegative")
        failed = previous.failed.union(new)
        start = perf_counter()
        rows, lower, upper, integrality = self._model(failed, previous, ramp)
        service_tolerance = 1e-8
        critical_row, critical_optimum = None, 0.0
        # Lexicographic critical service first; retain its optimum in all later solves.
        if self.critical_buses:
            critical_ld = self.ld[list(self.critical_buses)]
            priority_objective = np.zeros(self.nvar)
            priority_objective[critical_ld] = -1
            priority_x, _, _ = self._solve(rows, lower, upper, integrality, priority_objective)
            critical_optimum = float(priority_x[critical_ld].sum())
            critical_row = len(rows.lo)
            rows.add({int(i): 1 for i in critical_ld}, critical_optimum - service_tolerance, np.inf)
        objective = np.zeros(self.nvar)
        normalized_weights = self.service_weights / max(float(self.service_weights.max()), 1.0)
        objective[self.ld] = -normalized_weights
        try:
            x, residual, gap = self._solve(rows, lower, upper, integrality, objective)
        except SolverError as exc:
            if critical_row is None:
                raise SolverError(f"Primary response, failed={sorted(failed)}: {exc}") from exc
            service_tolerance = 1e-7 * max(1.0, abs(critical_optimum))
            rows.lo[critical_row] = critical_optimum - service_tolerance
            try:
                x, residual, gap = self._solve(rows, lower, upper, integrality, objective, presolve=False)
            except SolverError as retry_exc:
                raise SolverError(f"Priority-constrained response, failed={sorted(failed)}: {retry_exc}") from exc
        if self.tie_break == "cost":
            # Exact primary optimum, within a small absolute numerical tolerance.
            optimum = float(x[self.ld] @ normalized_weights)
            service_row = len(rows.lo)
            rows.add({int(i): float(w) for i, w in zip(self.ld, normalized_weights)}, optimum - service_tolerance, np.inf)
            secondary = np.zeros(self.nvar)
            costs = self.case.cost[:, 1]
            secondary[self.pg] = costs / max(float(np.abs(costs).max(initial=0)), 1)
            # Prefer retaining online generators where it does not affect service/cost.
            secondary[self.z] = -1e-7
            try:
                x, residual, gap = self._solve(rows, lower, upper, integrality, secondary)
            except SolverError as exc:
                # Frozen ramp bounds can make MIP presolve numerically reject an
                # almost-tight service floor. Retry the SAME model without it.
                try:
                    x, residual, gap = self._solve(rows, lower, upper, integrality, secondary, presolve=False)
                except SolverError as retry_exc:
                    # A proven service optimum plus nearly fixed ramp bounds can
                    # make the second MILP numerically infeasible. Only after
                    # both identical-model attempts fail, permit a bounded,
                    # recorded relative tolerance on the service floors.
                    service_tolerance = max(service_tolerance, 1e-7 * max(1.0, abs(optimum), abs(critical_optimum)))
                    rows.lo[service_row] = optimum - service_tolerance
                    if critical_row is not None:
                        rows.lo[critical_row] = critical_optimum - service_tolerance
                    try:
                        x, residual, gap = self._solve(rows, lower, upper, integrality, secondary, presolve=False)
                    except SolverError as final_exc:
                        raise SolverError(f"Secondary response, failed={sorted(failed)}, served optimum={optimum}: {final_exc}") from retry_exc
        state = self._pack(x, failed, residual, perf_counter() - start, gap, previous.round + 1,
                           service_tolerance)
        if np.any(state.served > previous.served + 2e-6):
            raise SolverError("Previously shed demand was restored")
        return state
