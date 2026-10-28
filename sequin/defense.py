"""Budgeted protection extension with adaptive failure-search re-evaluation."""

from dataclasses import dataclass
from .search import Evaluator, search


@dataclass
class ProtectionResult:
    protected: tuple[int, ...]
    baseline_shed_mw: float
    remaining_shed_mw: float
    adaptive_sequence: tuple[int, ...]
    history: list[dict]

    def to_dict(self):
        return {"protected_lines": list(self.protected), "baseline_shed_mw": self.baseline_shed_mw,
                "remaining_shed_mw": self.remaining_shed_mw,
                "reduction_mw": self.baseline_shed_mw - self.remaining_shed_mw,
                "adaptive_sequence": list(self.adaptive_sequence), "history": self.history,
                "guarantee": "heuristic worst-found disruption; not a certified worst-case bound"}


def plan_protection(simulator, initial, *, k=2, budget=1, method="sequin", breadth=5,
                    candidates=None, max_sequences=50_000):
    if not 0 <= budget <= len(simulator.case.line_ids) - k:
        raise ValueError("Protection budget leaves too few lines for the outage budget")
    protected, history = [], []
    candidate_ids = sorted(set(simulator.case.line_ids if candidates is None else candidates))
    if not set(candidate_ids).issubset(simulator.case.line_ids) or len(candidate_ids) < budget:
        raise ValueError("Invalid or insufficient protection candidates")

    def assess(lines):
        return search(Evaluator(simulator, initial, lines), method, k,
                      breadth=breadth, max_sequences=max_sequences)

    baseline = assess(())
    current = baseline
    for step in range(budget):
        options = []
        for line in candidate_ids:
            if line not in protected:
                result = assess(protected + [line])
                options.append((result.state.shed_mw, line, result))
        _, chosen, current = min(options, key=lambda item: (item[0], item[1]))
        protected.append(chosen)
        history.append({"step": step + 1, "protected_line": chosen,
                        "worst_found_shed_mw": current.state.shed_mw,
                        "adaptive_sequence": list(current.sequence), "candidates_evaluated": len(options)})
    return ProtectionResult(tuple(protected), baseline.state.shed_mw, current.state.shed_mw,
                            current.sequence, history)
