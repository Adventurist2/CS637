"""Guided search, comparison strategies, exact small-case oracles, and prefix trees."""

from dataclasses import dataclass, field
from itertools import combinations, permutations
from math import comb, perm, ceil
from time import perf_counter

import networkx as nx
import numpy as np

from .physics import GridSimulator, GridState


class SearchLimitError(ValueError):
    pass


@dataclass
class SearchResult:
    method: str
    sequence: tuple[int, ...]
    state: GridState
    sequences: list[tuple[int, ...]]
    seconds: float
    response_evaluations: int
    optimizer_calls: int
    exhaustive: bool = False
    simultaneous: bool = False

    def summary(self):
        return {"method": self.method, "sequence": list(self.sequence), "shed_mw": self.state.shed_mw,
                "seconds": self.seconds, "response_evaluations": self.response_evaluations,
                "optimizer_calls": self.optimizer_calls, "exhaustive": self.exhaustive,
                "simultaneous": self.simultaneous, "sequences_explored": len(self.sequences),
                "max_residual_pu": self.state.max_residual_pu}


class Evaluator:
    """An evaluator is bound to ONE scenario, initial state, and response policy."""

    def __init__(self, simulator: GridSimulator, initial: GridState, protected=()):
        self.simulator, self.initial = simulator, initial
        self.protected = frozenset(int(i) for i in protected)
        if not self.protected.issubset(simulator.case.line_ids):
            raise ValueError("Unknown protection line ID")
        self.cache = {(): initial}
        self.simultaneous_cache = {}
        self.response_evaluations = 0
        self.topology_cache = {}

    @property
    def eligible(self):
        return tuple(i for i in self.simulator.case.line_ids if i not in self.protected)

    def evaluate(self, prefix):
        prefix = tuple(prefix)
        if prefix not in self.cache:
            if prefix[-1] not in self.eligible:
                raise ValueError("Cannot fail a protected or unknown line")
            previous = self.evaluate(prefix[:-1])
            self.cache[prefix] = self.simulator.respond(previous, (prefix[-1],))
            self.response_evaluations += 1
        return self.cache[prefix]

    def simultaneous(self, lines):
        key = tuple(sorted(lines))
        if len(set(lines)) != len(lines) or not set(lines).issubset(self.eligible):
            raise ValueError("Invalid simultaneous outage set")
        if key not in self.simultaneous_cache:
            self.simultaneous_cache[key] = self.simulator.respond(self.initial, key)
            self.response_evaluations += 1
        return self.simultaneous_cache[key]

    def trace(self, sequence):
        return [self.evaluate(sequence[:i]) for i in range(len(sequence) + 1)]

    def network_properties(self, state):
        """Exact generator-to-load cut width, clustered load density, literal margins.

        Width implements the minimum-cut interpretation of Eq. 6, not the
        appendix's order-dependent greedy path deletion. Local generator buses
        have infinite width; already isolated buses have zero width.
        """
        c = self.simulator.case
        key = (state.failed, tuple(state.online))
        if key not in self.topology_cache:
            graph = self.simulator.graph(state.failed)
            generators = set(int(b) for b in c.gen_bus[state.online])
            directed = nx.DiGraph()
            directed.add_nodes_from(graph.nodes)
            for a, b in graph.edges():
                capacity = directed.get_edge_data(a, b, {}).get("capacity", 0) + 1
                directed.add_edge(a, b, capacity=capacity)
                directed.add_edge(b, a, capacity=capacity)
            source = c.nbus
            directed.add_node(source)
            for bus in sorted(generators):
                directed.add_edge(source, bus, capacity=c.nbranch + 1)
            widths = np.zeros(c.nbus)
            for bus in range(c.nbus):
                widths[bus] = np.inf if bus in generators else nx.minimum_cut_value(directed, source, bus)
            groups = nx.Graph()
            groups.add_nodes_from(graph.nodes)
            groups.add_edges_from((a, b) for a, b in graph.edges() if widths[a] == widths[b])
            clusters = [tuple(sorted(x)) for x in nx.connected_components(groups)]
            self.topology_cache[key] = widths, clusters
        widths, clusters = self.topology_cache[key]
        density = np.zeros(c.nbus)
        for cluster in clusters:
            density[list(cluster)] = state.served[list(cluster)].sum()
        ratio = np.divide(density, widths, out=np.zeros_like(density), where=(widths > 0) & np.isfinite(widths))
        flow = {i: abs(float(state.flow[i - 1])) for i in self.eligible if i not in state.failed}
        margins = {i: max(float(c.rating[i - 1] - abs(state.flow[i - 1])), 0)
                   if np.isfinite(c.rating[i - 1]) else 0 for i in flow}
        density_width = {i: float(ratio[c.branch_from[i - 1]] + ratio[c.branch_to[i - 1]]) for i in flow}
        return {"flow": flow, "margin": margins, "density_width": density_width, "width": widths}

    def criticality(self, state):
        c = self.simulator.case
        finite = np.isfinite(c.rating) & c.branch_available
        finite[list(i - 1 for i in state.failed)] = False
        branch_margin = np.maximum(c.rating[finite] - np.abs(state.flow[finite]), 0).sum()
        gen_margin = np.minimum(np.abs(state.generation - c.pmin), np.abs(c.pmax - state.generation))
        return float(branch_margin + gen_margin[state.online].sum())


def _top(scores, n):
    return sorted(scores, key=lambda i: (-scores[i], i))[:n]


def search(evaluator: Evaluator, method="sequin", k=2, *, breadth=5,
           max_sequences=50_000) -> SearchResult:
    """Run one method, refusing expensive exact searches before starting them."""
    start = perf_counter()
    before = evaluator.response_evaluations
    before_solves = evaluator.simulator.solve_count
    if not isinstance(k, int) or k < 1 or k > len(evaluator.eligible):
        raise ValueError("k must be between 1 and the number of eligible lines")
    if breadth < 1 or max_sequences < 1:
        raise ValueError("breadth and max_sequences must be positive")
    methods = {"sequin", "sequin-release", "greedy-flow", "greedy-shed", "greedy-crit", "enum", "std", "perm", "beam"}
    if method not in methods:
        raise ValueError(f"Unknown method: {method}")
    sequences = []
    simultaneous = method == "std"
    exhaustive = method in ("enum", "std")
    if method == "std":
        count = comb(len(evaluator.eligible), k)
        if count > max_sequences:
            raise SearchLimitError(f"STD requires {count:,} sets, exceeding limit {max_sequences:,}")
        sequences = list(combinations(evaluator.eligible, k))
        for seq in sequences:
            evaluator.simultaneous(seq)
    elif method == "enum":
        count = perm(len(evaluator.eligible), k)
        if count > max_sequences:
            raise SearchLimitError(f"ENUM requires {count:,} sequences, exceeding limit {max_sequences:,}")
        sequences = list(permutations(evaluator.eligible, k))
        for seq in sequences:
            evaluator.evaluate(seq)
    elif method == "perm":
        if perm(k, k) > max_sequences:
            raise SearchLimitError("PERM exceeds the permutation limit")
        base = search(evaluator, "std", k, breadth=breadth, max_sequences=max_sequences)
        sequences = list(permutations(base.sequence))
        for seq in sequences:
            evaluator.evaluate(seq)
    elif method == "beam":
        beam = [()]
        for _ in range(k):
            expanded = []
            for prefix in beam:
                for line in evaluator.eligible:
                    if line not in prefix:
                        seq = prefix + (line,)
                        evaluator.evaluate(seq)
                        expanded.append(seq)
            beam = sorted(expanded, key=lambda p: (-evaluator.evaluate(p).shed_mw, p))[:breadth]
        sequences = beam
    else:
        properties = evaluator.network_properties(evaluator.initial) if method == "sequin" else None
        initial_flow = {i: abs(evaluator.initial.flow[i - 1]) for i in evaluator.eligible}
        if method == "sequin":
            starts = sorted(set(sum((_top(properties[x], breadth) for x in ("flow", "margin", "density_width")), [])))
        elif method == "sequin-release":
            starts = _top(initial_flow, breadth)
        else:
            n = max(1, ceil(len(evaluator.eligible) * 0.1))
            if method == "greedy-flow":
                initial_scores = initial_flow
            else:
                initial_scores = {}
                for i in evaluator.eligible:
                    state = evaluator.evaluate((i,))
                    initial_scores[i] = state.shed_mw if method == "greedy-shed" else evaluator.criticality(state)
            starts = _top(initial_scores, n)
        for first in starts:
            prefix = (first,)
            evaluator.evaluate(prefix)
            while len(prefix) < k:
                state = evaluator.evaluate(prefix)
                eligible = [i for i in evaluator.eligible if i not in state.failed]
                if method == "sequin":
                    props = evaluator.network_properties(state)
                    candidates = sorted(set(sum((_top(props[x], breadth) for x in ("flow", "margin", "density_width")), [])))
                elif method == "sequin-release":
                    candidates = _top({i: abs(state.flow[i - 1]) for i in eligible}, breadth)
                else:
                    candidates = eligible
                if method == "greedy-flow":
                    line = _top({i: abs(state.flow[i - 1]) for i in eligible}, 1)[0]
                else:
                    scores = {}
                    for line in candidates:
                        trial = evaluator.evaluate(prefix + (line,))
                        scores[line] = evaluator.criticality(trial) if method == "greedy-crit" else trial.shed_mw
                    line = _top(scores, 1)[0]
                prefix += (line,)
                evaluator.evaluate(prefix)
            sequences.append(prefix)
        sequences = sorted(set(sequences))
    get_state = evaluator.simultaneous if simultaneous else evaluator.evaluate
    best = min(sequences, key=lambda p: (-get_state(p).shed_mw, p))
    return SearchResult(method, best, get_state(best), sequences, perf_counter() - start,
                        evaluator.response_evaluations - before,
                        evaluator.simulator.solve_count - before_solves, exhaustive, simultaneous)


def prefix_tree(evaluator: Evaluator, sequences):
    """Ranges refer only to explored continuations, never certified future bounds."""
    root = {"prefix": [], "min_final_shed_mw": None, "max_final_shed_mw": None, "children": {}}
    for sequence in sorted(set(tuple(x) for x in sequences)):
        final = evaluator.evaluate(sequence).shed_mw
        node = root
        for depth in range(len(sequence) + 1):
            node["min_final_shed_mw"] = final if node["min_final_shed_mw"] is None else min(final, node["min_final_shed_mw"])
            node["max_final_shed_mw"] = final if node["max_final_shed_mw"] is None else max(final, node["max_final_shed_mw"])
            if depth < len(sequence):
                line = str(sequence[depth])
                node = node["children"].setdefault(line, {"prefix": list(sequence[:depth + 1]),
                    "min_final_shed_mw": None, "max_final_shed_mw": None, "children": {}})
    return {"coverage": "explored sequences only", "tree": root}
