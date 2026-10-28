"""Read numeric MATPOWER data without executing MATLAB code."""

from dataclasses import dataclass, replace
from hashlib import sha256
from pathlib import Path
import re

import numpy as np


CASE_FILES = {
    "14": "pglib_opf_case14_ieee__api.m",
    "39": "pglib_opf_case39_epri__api.m",
    "60": "pglib_opf_case60_c.m",
    "118": "pglib_opf_case118_ieee__api.m",
    "162": "pglib_opf_case162_ieee_dtc.m",
    "240": "pglib_opf_case240_pserc.m",
}
DATA_DIR = Path(__file__).resolve().parent / "data" / "cases"


def _matrix(text: str, name: str, required: bool = True) -> np.ndarray:
    match = re.search(r"mpc\." + re.escape(name) + r"\s*=\s*\[(.*?)\];", text, re.S)
    if match is None:
        if required:
            raise ValueError(f"Missing MATPOWER matrix: {name}")
        return np.empty((0, 0))
    rows = []
    for row in match[1].replace("...", "").split(";"):
        if row.strip():
            try:
                rows.append([float(x) for x in row.split()])
            except ValueError as exc:
                raise ValueError(f"Only numeric MATPOWER matrices are supported ({name})") from exc
    if not rows or len({len(row) for row in rows}) != 1:
        raise ValueError(f"Empty or ragged MATPOWER matrix: {name}")
    return np.asarray(rows, dtype=float)


@dataclass(frozen=True)
class GridCase:
    """Power arrays use per-unit; bus/gen/branch IDs retain MATPOWER identities."""

    name: str
    base_mva: float
    bus_ids: np.ndarray
    demand: np.ndarray
    gen_bus: np.ndarray
    pmin: np.ndarray
    pmax: np.ndarray
    gen_available: np.ndarray
    branch_from: np.ndarray
    branch_to: np.ndarray
    reactance: np.ndarray
    tap: np.ndarray
    shift: np.ndarray
    rating: np.ndarray
    angle_min: np.ndarray
    angle_max: np.ndarray
    branch_available: np.ndarray
    cost: np.ndarray
    source_sha256: str = "synthetic"
    clipped_negative_load_mw: float = 0.0
    scenario_seed: int | None = None
    perturbation: float = 0.0
    injection: np.ndarray | None = None

    @property
    def nbus(self):
        return len(self.bus_ids)

    @property
    def ngen(self):
        return len(self.pmax)

    @property
    def nbranch(self):
        return len(self.rating)

    @property
    def line_ids(self):
        return tuple(int(i + 1) for i in np.flatnonzero(self.branch_available))

    @property
    def total_demand_mw(self):
        return float(self.demand.sum() * self.base_mva)

    @property
    def injections(self):
        return np.zeros(self.nbus) if self.injection is None else self.injection

    def scenario(self, seed: int, perturb: float = 0.05):
        if not 0 <= perturb <= 1:
            raise ValueError("Demand perturbation must be in [0, 1]")
        rng = np.random.default_rng(seed)
        factors = rng.uniform(1 - perturb, 1 + perturb, self.nbus)
        return replace(self, demand=self.demand * factors, injection=self.injections * factors,
                       scenario_seed=seed, perturbation=perturb)

    def metadata(self):
        return {"case": self.name, "base_mva": self.base_mva, "buses": self.nbus,
                "branches": self.nbranch, "generators": self.ngen,
                "demand_mw": self.total_demand_mw, "source_sha256": self.source_sha256,
                "negative_load_clipped_mw": self.clipped_negative_load_mw,
                "negative_load_injection_mw": float(self.injections.sum() * self.base_mva),
                "negative_load_policy": "fixed injection at initialization, curtailable and nonrecoverable thereafter",
                "seed": self.scenario_seed, "perturbation": self.perturbation}


def load_case(case: str | Path) -> GridCase:
    path = DATA_DIR / CASE_FILES[str(case)] if str(case) in CASE_FILES else Path(case)
    raw = path.read_bytes()
    # Comments are stripped before extraction. No eval or MATLAB execution.
    text = re.sub(r"%[^\n]*", "", raw.decode("utf-8-sig"))
    base_match = re.search(r"mpc\.baseMVA\s*=\s*([0-9.eE+\-]+)", text)
    if base_match is None:
        raise ValueError("Missing baseMVA")
    base = float(base_match[1])
    if not np.isfinite(base) or base <= 0:
        raise ValueError("baseMVA must be positive and finite")
    bus, gen, branch = (_matrix(text, x) for x in ("bus", "gen", "branch"))
    costs = _matrix(text, "gencost", required=False)
    if bus.shape[1] < 13 or gen.shape[1] < 10 or branch.shape[1] < 13:
        raise ValueError("MATPOWER bus/gen/branch matrices have too few columns")
    if not all(np.isfinite(a).all() for a in (bus, gen, branch, costs)):
        raise ValueError("Non-finite MATPOWER input")
    if np.any(bus[:, 1] == 4):
        raise ValueError("Isolated type-4 buses must be removed before loading")
    if np.any(np.abs(bus[:, 4]) > 1e-12):
        raise ValueError("Active shunts (Gs) are not supported; supplied six benchmarks have Gs=0")
    ids = bus[:, 0].astype(int)
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate bus IDs")
    lookup = {int(v): i for i, v in enumerate(ids)}
    try:
        gb = np.array([lookup[int(i)] for i in gen[:, 0]])
        bf = np.array([lookup[int(i)] for i in branch[:, 0]])
        bt = np.array([lookup[int(i)] for i in branch[:, 1]])
    except KeyError as exc:
        raise ValueError(f"Unknown bus referenced: {exc}") from exc
    if np.any((branch[:, 10] > 0) & (np.abs(branch[:, 3]) < 1e-12)):
        raise ValueError("Zero-reactance active branches are unsupported")
    if np.any(gen[:, 8] < 0):
        raise ValueError("Negative generator Pmax is unsupported")
    polynomial = np.zeros((len(gen), 3))
    if costs.size:
        if len(costs) not in (len(gen), 2 * len(gen)):
            raise ValueError("Generator cost row count does not match generators")
        for i, row in enumerate(costs[:len(gen)]):
            n = int(row[3])
            if row[0] != 2 or n < 1 or n > 3 or len(row) < 4 + n:
                raise ValueError("Only polynomial costs of degree <= 2 are supported")
            polynomial[i, -n:] = row[4:4 + n]
        if np.any(polynomial[:, 0] < 0):
            raise ValueError("Initial DC OPF requires convex generation costs")
    # Relax positive generation lower limits as in the reference. Negative loads
    # remain explicit injections: clipping them makes case 162 initially infeasible.
    return GridCase(path.stem, base, ids, np.maximum(bus[:, 2], 0) / base,
                    gb, np.where(gen[:, 8] > 0, 0, gen[:, 9]) / base, gen[:, 8] / base,
                    gen[:, 7] > 0, bf, bt, branch[:, 3],
                    np.where(branch[:, 8] == 0, 1, branch[:, 8]),
                    np.deg2rad(branch[:, 9]),
                    np.where(branch[:, 5] > 0, branch[:, 5] / base, np.inf),
                    np.where(branch[:, 11] <= -360, -np.inf, np.deg2rad(branch[:, 11])),
                    np.where(branch[:, 12] >= 360, np.inf, np.deg2rad(branch[:, 12])),
                    branch[:, 10] > 0, polynomial, source_sha256=sha256(raw).hexdigest(),
                    injection=-np.minimum(bus[:, 2], 0) / base)
