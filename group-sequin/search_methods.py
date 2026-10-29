from itertools import combinations, permutations
from grid_model import initial_state, defend, shed_pu
from network_metrics import generator_criticality


def run_sequence(case, sequence, ramp=0.1, simple_ramp=False, start_state=None):
    state = initial_state(case) if start_state is None else start_state
    failed = []
    history = []
    for line in sequence:
        failed.append(int(line))
        state = defend(case, failed, state, ramp, simple_ramp=simple_ramp)
        if state is None:
            return None
        history.append(shed_pu(case, state))
    return history[-1], history, state


def exact_simultaneous(case, k=2, ramp=0.1):
    start = initial_state(case)
    best = (-1, None)
    evaluations = 0
    for lines in combinations(range(1, len(case['branch']) + 1), k):
        state = defend(case, list(lines), start, ramp)
        evaluations += 1
        if state is None:
            continue
        score = shed_pu(case, state)
        if score > best[0]:
            best = (score, lines)
    return best + ({'defender_solves': evaluations},)


def exact_sequential(case, k=2, ramp=0.1):
    best = (-1, None, None)
    evaluations = 0
    for seq in permutations(range(1, len(case['branch']) + 1), k):
        state = initial_state(case)
        failed = []
        hist = []
        ok = True
        for line in seq:
            failed.append(line)
            state = defend(case, failed, state, ramp)
            evaluations += 1
            if state is None:
                ok = False
                break
            hist.append(shed_pu(case, state))
        if ok and hist[-1] > best[0]:
            best = (hist[-1], seq, hist)
    return best + ({'defender_solves': evaluations},)


def greedy_flow(case, k, ramp=0.1):
    state = initial_state(case)
    failed, hist = [], []
    evaluations = 0
    for _ in range(k):
        candidates = [(abs(f), i) for i, f in state['flows'].items() if i not in failed]
        if not candidates:
            break
        _, line = max(candidates)
        failed.append(line)
        state = defend(case, failed, state, ramp)
        evaluations += 1
        if state is None:
            return None
        hist.append(shed_pu(case, state))
    return hist[-1], tuple(failed), hist, {'defender_solves': evaluations}


def greedy_impact(case, k, ramp=0.1, simple_ramp=False, candidate_lines=None):
    state = initial_state(case)
    failed, hist = [], []
    evaluations = 0
    all_lines = list(range(1, len(case['branch']) + 1))
    for _ in range(k):
        pool = candidate_lines(state, failed) if callable(candidate_lines) else all_lines
        best = (-1, None, None)
        for line in pool:
            if line in failed:
                continue
            cand = defend(case, failed + [line], state, ramp, simple_ramp=simple_ramp)
            evaluations += 1
            if cand is None:
                continue
            score = shed_pu(case, cand)
            if score > best[0] + 1e-10 or (abs(score - best[0]) <= 1e-10 and (best[1] is None or line < best[1])):
                best = (score, line, cand)
        if best[1] is None:
            return None
        failed.append(best[1])
        state = best[2]
        hist.append(best[0])
    return hist[-1], tuple(failed), hist, {'defender_solves': evaluations}


def greedy_criticality(case, k, ramp=0.1):
    state = initial_state(case)
    failed, hist = [], []
    evaluations = 0
    for _ in range(k):
        best = (float('inf'), None, None)
        for line in range(1, len(case['branch']) + 1):
            if line in failed:
                continue
            cand = defend(case, failed + [line], state, ramp)
            evaluations += 1
            if cand is None:
                continue
            crit = generator_criticality(case, cand, ramp)
            if crit < best[0] - 1e-12 or (abs(crit - best[0]) <= 1e-12 and (best[1] is None or line < best[1])):
                best = (crit, line, cand)
        if best[1] is None:
            return None
        failed.append(best[1])
        state = best[2]
        hist.append(shed_pu(case, state))
    return hist[-1], tuple(failed), hist, {'defender_solves': evaluations}


def guided_search(case, k, ramp=0.1, top_n=10):
    """Active released ours.jl path: top-N current-flow shortlist + cut impact."""
    start = initial_state(case)
    first = sorted(start['flows'], key=lambda i: (-abs(start['flows'][i]), i))[:top_n]
    overall = (-1, None, None)
    evaluations = 0

    for first_line in first:
        failed = [first_line]
        state = defend(case, failed, start, ramp)
        evaluations += 1
        if state is None:
            continue
        hist = [shed_pu(case, state)]

        while len(failed) < k:
            candidates = [i for i in sorted(state['flows'], key=lambda i: (-abs(state['flows'][i]), i))
                          if i not in failed][:top_n]
            best = (-1, None, None)
            for line in candidates:
                cand = defend(case, failed + [line], state, ramp)
                evaluations += 1
                if cand is None:
                    continue
                score = shed_pu(case, cand)
                if score > best[0] + 1e-10 or (abs(score - best[0]) <= 1e-10 and (best[1] is None or line < best[1])):
                    best = (score, line, cand)
            if best[1] is None:
                break
            failed.append(best[1])
            state = best[2]
            hist.append(best[0])

        if len(failed) == k and hist[-1] > overall[0]:
            overall = (hist[-1], tuple(failed), hist)

    return overall + ({'defender_solves': evaluations},)


def best_permutation(case, line_set, ramp=0.1, max_permutations=None):
    best = (-1, None, None)
    evaluations = 0
    for j, seq in enumerate(permutations(line_set)):
        if max_permutations is not None and j >= max_permutations:
            break
        state = initial_state(case)
        failed, hist = [], []
        ok = True
        for line in seq:
            failed.append(int(line))
            state = defend(case, failed, state, ramp)
            evaluations += 1
            if state is None:
                ok = False
                break
            hist.append(shed_pu(case, state))
        if ok and hist[-1] > best[0]:
            best = (hist[-1], tuple(seq), hist)
    return best + ({'defender_solves': evaluations},)


def greedy_criticality_author_style(case, k, ramp=0.1):
    """Preserve the state-update order of released greedy-criticality.jl."""
    initial = initial_state(case)
    evaluations = 0
    best = (float('inf'), None, None)
    for line in range(1, len(case['branch']) + 1):
        cand = defend(case, [line], initial, ramp)
        evaluations += 1
        if cand is None:
            continue
        crit = generator_criticality(case, cand, ramp)
        if crit < best[0] - 1e-12 or (abs(crit - best[0]) <= 1e-12 and (best[1] is None or line < best[1])):
            best = (crit, line, cand)
    if best[1] is None:
        return None
    failed = [best[1]]
    hist = []
    state = initial
    if k == 1:
        state = best[2]
        hist.append(shed_pu(case, state))
        return hist[-1], tuple(failed), hist, {'defender_solves': evaluations}

    for _ in range(2, k + 1):
        choose = (float('inf'), None, None)
        for line in range(1, len(case['branch']) + 1):
            if line in failed:
                continue
            cand = defend(case, failed + [line], state, ramp)
            evaluations += 1
            if cand is None:
                continue
            crit = generator_criticality(case, cand, ramp)
            if crit < choose[0] - 1e-12 or (abs(crit - choose[0]) <= 1e-12 and (choose[1] is None or line < choose[1])):
                choose = (crit, line, cand)
        if choose[1] is None:
            return None
        failed.append(choose[1])
        state = choose[2]
        hist.append(shed_pu(case, state))

    return hist[-1], tuple(failed), hist, {'defender_solves': evaluations}
