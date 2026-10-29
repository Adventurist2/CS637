from collections import deque


def load_density(case):
    """Active real-power demand at each bus (MW)."""
    return {int(row[0]): max(float(row[2]), 0.0) for row in case['bus']}


def generator_criticality(case, state, ramp):
    """Paper-code style remaining generator flexibility.

    The released Julia code currently sums only generator criticality
    (branch criticality is disabled there). Smaller value means less flexibility.
    """
    total = 0.0
    for gi, g in enumerate(case['gen']):
        pmax = float(g[8])
        if int(g[7]) == 0 or pmax <= 0:
            continue
        pg = float(state['pg'][gi])
        total += min(abs(pmax - pg), abs(ramp * pmax))
    return total / case['base']


def branch_margin(case, state):
    """Return thermal margin for active lines in MW."""
    out = {}
    for line_id, flow in state['flows'].items():
        br = case['branch'][line_id - 1]
        rate = float(br[5])
        if rate > 0:
            out[line_id] = rate - abs(float(flow))
    return out


def _adjacency(case, removed_edges=None):
    removed_edges = removed_edges or set()
    adj = {int(b[0]): [] for b in case['bus']}
    for idx, br in enumerate(case['branch'], start=1):
        if int(br[10]) == 0 or idx in removed_edges:
            continue
        a, b = int(br[0]), int(br[1])
        adj[a].append((b, idx))
        adj[b].append((a, idx))
    return adj


def _find_path_edges(adj, start, goal, blocked):
    q = deque([start])
    parent = {start: (None, None)}
    while q:
        u = q.popleft()
        if u == goal:
            break
        for v, eid in adj[u]:
            if eid in blocked or v in parent:
                continue
            parent[v] = (u, eid)
            q.append(v)
    if goal not in parent:
        return []
    path = []
    v = goal
    while parent[v][0] is not None:
        u, eid = parent[v]
        path.append(eid)
        v = u
    return path


def transmission_width(case):
    """A compact version of the paper code's path-removal width heuristic.

    For every bus, repeatedly find an edge-disjoint path from each generator bus
    and remove that path's edges. The resulting count is a structural resilience
    indicator, not a max-flow capacity calculation.
    """
    adj = _adjacency(case)
    gen_buses = [int(g[0]) for g in case['gen'] if int(g[7]) != 0 and float(g[8]) > 0]
    widths = {}
    for bus in adj:
        blocked = set()
        width = 0
        for gb in gen_buses:
            while True:
                p = _find_path_edges(adj, gb, bus, blocked)
                if not p:
                    break
                blocked.update(p)
                width += 1
        widths[bus] = width
    return widths


def line_ldtw_score(case):
    """Load-density / transmission-width score used by the paper prototype."""
    ld = load_density(case)
    tw = transmission_width(case)
    score = {}
    for i, br in enumerate(case['branch'], start=1):
        a, b = int(br[0]), int(br[1])
        wa, wb = max(tw.get(a, 0), 1), max(tw.get(b, 0), 1)
        score[i] = ld.get(a, 0.0) / wa + ld.get(b, 0.0) / wb
    return score
