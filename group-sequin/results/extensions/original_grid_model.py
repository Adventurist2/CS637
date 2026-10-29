import math
import re
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, linprog, milp


def _matrix(text, name):
    """Read one [ ... ] matrix from a MATPOWER .m file."""
    block = re.search(r"mpc\.%s\s*=\s*\[(.*?)\];" % name, text, re.S)
    if block is None:
        raise ValueError("matrix not found: " + name)
    rows = []
    for line in block.group(1).splitlines():
        line = line.split('%')[0].strip().rstrip(';')
        if line:
            rows.append([float(x) for x in line.split()])
    return np.array(rows, dtype=float)


def load_case(filename, perturb=0.0, seed=None):
    """Load a MATPOWER case.

    perturb is a fractional uniform load perturbation, e.g. 0.05 means
    each positive Pd is multiplied by U(0.95, 1.05). This mirrors the
    paper/released experiment setup when requested; default is deterministic.
    """
    text = open(filename, encoding='utf-8').read()
    base = float(re.search(r"mpc\.baseMVA\s*=\s*([0-9.eE+\-]+)", text).group(1))
    case = {
        'name': str(filename).replace('\\', '/').split('/')[-1].replace('.m', ''),
        'base': base,
        'bus': _matrix(text, 'bus'),
        'gen': _matrix(text, 'gen'),
        'branch': _matrix(text, 'branch'),
        'gencost': _matrix(text, 'gencost'),
    }
    if perturb > 0:
        rng = np.random.default_rng(seed)
        pd = case['bus'][:, 2]
        mask = pd > 0
        pd[mask] *= rng.uniform(1.0 - perturb, 1.0 + perturb, size=mask.sum())
    return case


def total_load(case):
    return np.maximum(case['bus'][:, 2], 0).sum() + np.maximum(case['bus'][:, 4], 0).sum()


def active_lines(case, failed):
    failed = set(failed)
    out = []
    for i, br in enumerate(case['branch'], start=1):
        if i not in failed and int(br[10]) != 0:
            out.append((i, br))
    return out


def components(case, failed):
    """Small DFS instead of using a graph library."""
    buses = [int(x) for x in case['bus'][:, 0]]
    nbr = {b: [] for b in buses}
    for _, br in active_lines(case, failed):
        a, b = int(br[0]), int(br[1])
        nbr[a].append(b)
        nbr[b].append(a)
    seen = set()
    comps = []
    for start in buses:
        if start in seen:
            continue
        stack = [start]
        comp = set()
        while stack:
            u = stack.pop()
            if u in seen:
                continue
            seen.add(u)
            comp.add(u)
            stack.extend(nbr[u])
        comps.append(comp)
    return comps


def initial_state(case):
    """Least-cost DC OPF for the intact grid using scipy.linprog."""
    bus, gen, base = case['bus'], case['gen'], case['base']
    lines = active_lines(case, [])
    ids = [int(x) for x in bus[:, 0]]
    pos = {b: i for i, b in enumerate(ids)}
    nb, ng, nl = len(bus), len(gen), len(lines)

    pg0 = nb
    f0 = nb + ng
    n = f0 + nl
    c = np.zeros(n)
    c[pg0:pg0 + ng] = case['gencost'][:, -2]

    bounds = [(-math.pi, math.pi)] * nb
    for g in gen:
        pmax = float(g[8])
        status = int(g[7])
        bounds.append((0, pmax) if status and pmax > 0 else (0, 0))
    for _, br in lines:
        rate = float(br[5])
        bounds.append((-rate, rate) if rate > 0 else (None, None))

    Aeq, beq = [], []
    for j, (_, br) in enumerate(lines):
        a, b = int(br[0]), int(br[1])
        x = float(br[3])
        tap = float(br[8]) if float(br[8]) != 0 else 1.0
        shift = math.radians(float(br[9]))
        B = base / (x * tap)
        row = np.zeros(n)
        row[f0 + j] = 1
        row[pos[a]] -= B
        row[pos[b]] += B
        Aeq.append(row)
        beq.append(-B * shift)

    for bi, b in enumerate(ids):
        row = np.zeros(n)
        for gi, g in enumerate(gen):
            if int(g[0]) == b:
                row[pg0 + gi] += 1
        for j, (_, br) in enumerate(lines):
            if int(br[0]) == b:
                row[f0 + j] -= 1
            if int(br[1]) == b:
                row[f0 + j] += 1
        demand = float(bus[bi, 2]) + float(bus[bi, 4])
        Aeq.append(row)
        beq.append(demand)

    for comp in components(case, []):
        row = np.zeros(n)
        row[pos[min(comp)]] = 1
        Aeq.append(row)
        beq.append(0)

    Aub, bub = [], []
    for _, br in lines:
        row = np.zeros(n)
        row[pos[int(br[0])]] = 1
        row[pos[int(br[1])]] = -1
        Aub.append(row)
        bub.append(math.radians(float(br[12])))
        Aub.append(-row)
        bub.append(-math.radians(float(br[11])))

    ans = linprog(c, A_ub=np.array(Aub), b_ub=np.array(bub),
                  A_eq=np.array(Aeq), b_eq=np.array(beq), bounds=bounds, method='highs')
    if not ans.success:
        raise RuntimeError(ans.message)

    flows = {line_id: ans.x[f0 + j] for j, (line_id, _) in enumerate(lines)}
    served = np.maximum(bus[:, 2], 0) + np.maximum(bus[:, 4], 0)
    return {'pg': ans.x[pg0:pg0 + ng].copy(), 'served': served.copy(), 'flows': flows}


def defend(case, failed, prev, ramp=0.1, simple_ramp=False):
    """Maximise served load after a set of line failures.

    The normal mode uses one binary variable per generator so a unit can either
    shut down or stay inside its ramp window. simple_ramp=True intentionally
    removes that binary recourse for an ablation experiment.
    """
    bus, gen, base = case['bus'], case['gen'], case['base']
    lines = active_lines(case, failed)
    ids = [int(x) for x in bus[:, 0]]
    pos = {b: i for i, b in enumerate(ids)}
    nb, ng, nl = len(bus), len(gen), len(lines)

    if simple_ramp:
        pg0 = nb
        s0 = pg0 + ng
        f0 = s0 + nb
        n = f0 + nl
        z0 = None
    else:
        pg0 = nb
        z0 = pg0 + ng
        s0 = z0 + ng
        f0 = s0 + nb
        n = f0 + nl

    c = np.zeros(n)
    c[s0:s0 + nb] = -1
    lo = np.full(n, -np.inf)
    hi = np.full(n, np.inf)
    integer = np.zeros(n, dtype=int)
    lo[:nb], hi[:nb] = -math.pi, math.pi

    for gi, g in enumerate(gen):
        pmax = float(g[8])
        old = float(prev['pg'][gi])
        low = max(0.0, old - ramp * pmax)
        high = min(pmax, old + ramp * pmax)
        if int(g[7]) == 0 or pmax <= 0:
            low = high = 0.0
        if simple_ramp:
            lo[pg0 + gi], hi[pg0 + gi] = low, high
        else:
            lo[pg0 + gi], hi[pg0 + gi] = 0, pmax
            lo[z0 + gi], hi[z0 + gi] = 0, 1
            integer[z0 + gi] = 1

    for bi in range(nb):
        lo[s0 + bi] = 0
        hi[s0 + bi] = prev['served'][bi]

    for j, (_, br) in enumerate(lines):
        rate = float(br[5])
        if rate > 0:
            lo[f0 + j], hi[f0 + j] = -rate, rate

    rows, lows, highs = [], [], []

    for j, (_, br) in enumerate(lines):
        a, b = int(br[0]), int(br[1])
        tap = float(br[8]) if float(br[8]) != 0 else 1.0
        B = base / (float(br[3]) * tap)
        shift = math.radians(float(br[9]))
        row = np.zeros(n)
        row[f0 + j] = 1
        row[pos[a]] -= B
        row[pos[b]] += B
        rhs = -B * shift
        rows.append(row); lows.append(rhs); highs.append(rhs)

    for bi, b in enumerate(ids):
        row = np.zeros(n)
        for gi, g in enumerate(gen):
            if int(g[0]) == b:
                row[pg0 + gi] += 1
        row[s0 + bi] -= 1
        for j, (_, br) in enumerate(lines):
            if int(br[0]) == b:
                row[f0 + j] -= 1
            if int(br[1]) == b:
                row[f0 + j] += 1
        fixed_negative_load = min(float(bus[bi, 2]), 0.0)
        fixed_shunt = min(float(bus[bi, 4]), 0.0)
        rhs = fixed_negative_load + fixed_shunt
        rows.append(row); lows.append(rhs); highs.append(rhs)

    for comp in components(case, failed):
        row = np.zeros(n)
        row[pos[min(comp)]] = 1
        rows.append(row); lows.append(0); highs.append(0)

    if not simple_ramp:
        for gi, g in enumerate(gen):
            pmax = float(g[8])
            old = float(prev['pg'][gi])
            low = max(0.0, old - ramp * pmax)
            high = min(pmax, old + ramp * pmax)
            if int(g[7]) == 0 or pmax <= 0:
                low = high = 0.0
            row = np.zeros(n)
            row[pg0 + gi] = 1
            row[z0 + gi] = -high
            rows.append(row); lows.append(-np.inf); highs.append(0)
            row = np.zeros(n)
            row[pg0 + gi] = -1
            row[z0 + gi] = low
            rows.append(row); lows.append(-np.inf); highs.append(0)

    for _, br in lines:
        row = np.zeros(n)
        row[pos[int(br[0])]] = 1
        row[pos[int(br[1])]] = -1
        rows.append(row)
        lows.append(math.radians(float(br[11])))
        highs.append(math.radians(float(br[12])))

    cons = LinearConstraint(np.array(rows), np.array(lows), np.array(highs))
    ans = milp(c, integrality=integer, bounds=Bounds(lo, hi), constraints=cons,
               options={'disp': False})
    if not ans.success:
        return None

    flows = {line_id: ans.x[f0 + j] for j, (line_id, _) in enumerate(lines)}
    return {'pg': ans.x[pg0:pg0 + ng].copy(),
            'served': ans.x[s0:s0 + nb].copy(),
            'flows': flows}


def shed_pu(case, state):
    return (total_load(case) - state['served'].sum()) / case['base']
