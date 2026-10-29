import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd

from grid_model import load_case
from search_methods import (
    run_sequence,
    greedy_flow,
    greedy_impact,
    greedy_criticality_author_style,
    guided_search,
    best_permutation,
)
from reference_utils import load_exp1, load_exp2, safe_percent, classify_error

HERE = Path(__file__).resolve().parent
DATA = HERE / 'data'
RESULTS = HERE / 'results'
PLOTS = HERE / 'plots'
RESULTS.mkdir(exist_ok=True)
PLOTS.mkdir(exist_ok=True)

CASES = {
    'case14': 'pglib_opf_case14_ieee__api.m',
    'case39': 'pglib_opf_case39_epri__api.m',
    'case60': 'pglib_opf_case60_c.m',
    'case118': 'pglib_opf_case118_ieee__api.m',
    'case162': 'pglib_opf_case162_ieee_dtc.m',
    'case240': 'pglib_opf_case240_pserc.m',
}


def case_obj(name, perturb=0.0, seed=None):
    return load_case(DATA / CASES[name], perturb=perturb, seed=seed)


def timed(call):
    t0 = time.perf_counter()
    out = call()
    return out, time.perf_counter() - t0


def add_result(rows, case, k, ramp, method, ours, author, sequence, elapsed, solves,
               experiment, note=''):
    err = safe_percent(ours, author)
    rows.append({
        'experiment': experiment,
        'case': case,
        'k': int(k),
        'ramp': float(ramp),
        'method': method,
        'our_load_shed': float(ours),
        'author_load_shed': float(author),
        'error_percent': float(err),
        'status': classify_error(err),
        'sequence': '-'.join(map(str, sequence)),
        'elapsed_seconds': float(elapsed),
        'defender_solves': int(solves),
        'note': note,
    })


def replay_author_sequences(exp1, rows):
    for case in CASES:
        c = case_obj(case)
        for k in range(2, 9):
            for problem in ['greedy_flow', 'greedy_impt', 'sequin']:
                g = exp1[(exp1.case == case) & (exp1.k == k) & (exp1.problem == problem)]
                if g.empty:
                    continue
                r = g.iloc[0]
                out, elapsed = timed(lambda: run_sequence(c, r.sequence, ramp=0.1))
                if out is None:
                    continue
                score, _, _ = out
                add_result(rows, case, k, 0.1, 'replay_' + problem, score, r.load_shed,
                           r.sequence, elapsed, len(r.sequence), 'author_sequence_replay',
                           'Same author sequence; isolates defender/model fidelity.')


def run_flow_sweep(exp1, rows):
    for case in CASES:
        c = case_obj(case)
        for k in range(2, 9):
            ref = exp1[(exp1.case == case) & (exp1.k == k) & (exp1.problem == 'greedy_flow')]
            if ref.empty:
                continue
            out, elapsed = timed(lambda: greedy_flow(c, k, ramp=0.1))
            if out is None:
                continue
            score, seq, _, stats = out
            add_result(rows, case, k, 0.1, 'greedy_flow', score, ref.iloc[0].load_shed,
                       seq, elapsed, stats['defender_solves'], 'k_sweep_search',
                       'Independent Greedy-FLOW search.')


def run_guided_and_impact(exp1, rows, full=False):
    guided_plan = {
        'case14': [2, 3, 4, 6, 8],
        'case39': [2, 3, 4, 6],
        'case60': [2, 3, 4],
        'case118': [2, 3, 4],
        'case162': [2] if not full else [2, 3],
        'case240': [] if not full else [2],
    }
    impact_plan = {
        'case14': [2, 3, 4],
        'case39': [2, 3, 4],
        'case60': [2, 3],
        'case118': [2],
    }
    crit_plan = {'case14': [2, 3], 'case39': [2, 3]}

    for case, ks in guided_plan.items():
        c = case_obj(case)
        for k in ks:
            ref = exp1[(exp1.case == case) & (exp1.k == k) & (exp1.problem == 'sequin')]
            if ref.empty:
                continue
            out, elapsed = timed(lambda: guided_search(c, k, ramp=0.1, top_n=10))
            score, seq, _, stats = out
            add_result(rows, case, k, 0.1, 'guided', score, ref.iloc[0].load_shed,
                       seq, elapsed, stats['defender_solves'], 'selected_search_reproduction',
                       'Active released ours.jl path: top-10 flow shortlist + cut impact.')

    for case, ks in impact_plan.items():
        c = case_obj(case)
        for k in ks:
            ref = exp1[(exp1.case == case) & (exp1.k == k) & (exp1.problem == 'greedy_impt')]
            if ref.empty:
                continue
            out, elapsed = timed(lambda: greedy_impact(c, k, ramp=0.1))
            score, seq, _, stats = out
            add_result(rows, case, k, 0.1, 'greedy_impact', score, ref.iloc[0].load_shed,
                       seq, elapsed, stats['defender_solves'], 'selected_search_reproduction',
                       'Expensive baseline: test every remaining line each round.')

    for case, ks in crit_plan.items():
        c = case_obj(case)
        for k in ks:
            ref = exp1[(exp1.case == case) & (exp1.k == k) & (exp1.problem == 'greedy_crit')]
            if ref.empty:
                continue
            out, elapsed = timed(lambda: greedy_criticality_author_style(c, k, ramp=0.1))
            score, seq, _, stats = out
            add_result(rows, case, k, 0.1, 'greedy_criticality_author_style',
                       score, ref.iloc[0].load_shed, seq, elapsed, stats['defender_solves'],
                       'exploratory_criticality_baseline',
                       'Mirrors released state-update order; highly sensitive to randomized equilibrium.')


def permutation_reproduction(exp1, rows):
    for case in ['case14', 'case39', 'case60', 'case118']:
        c = case_obj(case)
        for k in [2, 3, 4]:
            s = exp1[(exp1.case == case) & (exp1.k == k) & (exp1.problem == 'standard')]
            p = exp1[(exp1.case == case) & (exp1.k == k) & (exp1.problem == 'permutation')]
            if s.empty or p.empty:
                continue
            out, elapsed = timed(lambda: best_permutation(c, s.iloc[0].sequence, ramp=0.1))
            score, seq, _, stats = out
            add_result(rows, case, k, 0.1, 'permutation_of_author_std', score,
                       p.iloc[0].load_shed, seq, elapsed, stats['defender_solves'],
                       'permutation_reproduction',
                       'Same author STD line set; independently enumerate all orders.')


def ramp_sequence_replay(exp2, rows):
    for case in CASES:
        c = case_obj(case)
        for k in [2, 3, 4]:
            for ramp in [0.0, 0.1, 0.25, 0.5, 1.0]:
                g = exp2[(exp2.case == case) & (exp2.k == k) &
                         (np.isclose(exp2.ramp, ramp)) & (exp2.problem == 'sequin')]
                if g.empty:
                    continue
                r = g.iloc[0]
                out, elapsed = timed(lambda: run_sequence(c, r.sequence, ramp=ramp))
                if out is None:
                    continue
                score, _, _ = out
                add_result(rows, case, k, ramp, 'replay_sequin_ramp', score, r.load_shed,
                           r.sequence, elapsed, len(r.sequence), 'ramp_sequence_replay',
                           'Same author sequence at same ramp; isolates defender fidelity.')


def full_vs_simple_ramp(exp2, rows):
    case, k = 'case39', 3
    c = case_obj(case)
    for ramp in [0.0, 0.1, 0.25, 0.5, 1.0]:
        ref = exp2[(exp2.case == case) & (exp2.k == k) &
                   (np.isclose(exp2.ramp, ramp)) & (exp2.problem == 'greedy_impt')]
        if ref.empty:
            continue
        r = ref.iloc[0]
        out, elapsed = timed(lambda: greedy_impact(c, k, ramp=ramp, simple_ramp=True))
        if out is not None:
            score, seq, _, stats = out
            add_result(rows, case, k, ramp, 'simple_ramp_impact', score, r.load_shed, seq,
                       elapsed, stats['defender_solves'], 'model_ablation',
                       'No generator on/off binary: intentionally simplified model.')
        full, elapsed2 = timed(lambda: run_sequence(c, r.sequence, ramp=ramp, simple_ramp=False))
        if full is not None:
            score, _, _ = full
            add_result(rows, case, k, ramp, 'full_defender_replay_impact', score, r.load_shed,
                       r.sequence, elapsed2, len(r.sequence), 'model_ablation',
                       'Full binary defender; same author sequence.')


def perturbation_test(exp1, rows, full=False):
    seeds = [11, 22, 33] if not full else [11, 22, 33, 44, 55]
    case, k = 'case39', 3
    ref = exp1[(exp1.case == case) & (exp1.k == k) & (exp1.problem == 'sequin')].iloc[0]
    for seed in seeds:
        c = case_obj(case, perturb=0.05, seed=seed)
        out, elapsed = timed(lambda: guided_search(c, k, ramp=0.1, top_n=10))
        score, seq, _, stats = out
        add_result(rows, case, k, 0.1, f'guided_perturb_seed_{seed}', score, ref.load_shed,
                   seq, elapsed, stats['defender_solves'], 'load_perturbation_sensitivity',
                   'Independent ±5% load draw; exact author RNG state is unavailable.')


def write_outputs(rows):
    df = pd.DataFrame(rows)
    df.to_csv(RESULTS / 'results.csv', index=False)
    replay = df[df.experiment == 'author_sequence_replay'].copy()
    replay['base_method'] = replay.method.str.replace('replay_', '', regex=False)
    search = df[df.experiment.isin(['k_sweep_search', 'selected_search_reproduction'])].copy()
    method_map = {'greedy_flow':'greedy_flow', 'greedy_impact':'greedy_impt', 'guided':'sequin'}
    search['base_method'] = search.method.map(method_map)
    merged = search.merge(replay[['case','k','base_method','error_percent','status']],
                          on=['case','k','base_method'], how='left',
                          suffixes=('_search','_replay'))
    def diagnose(r):
        se = abs(r.error_percent_search)
        re = abs(r.error_percent_replay) if pd.notna(r.error_percent_replay) else np.nan
        if pd.notna(re) and re <= 5 and se > 5:
            return 'SEARCH/INITIAL-STATE SENSITIVITY'
        if pd.notna(re) and re > 5:
            return 'MODEL/INPUT FIDELITY DIFFERENCE'
        if se <= 5:
            return 'REPRODUCED OR CLOSE'
        return 'NO SAME-SEQUENCE DIAGNOSTIC'
    if len(merged):
        merged['diagnosis'] = merged.apply(diagnose, axis=1)
        merged.to_csv(RESULTS / 'divergence_diagnosis.csv', index=False)
    df.groupby(['experiment','status']).size().unstack(fill_value=0).to_csv(
        RESULTS / 'status_summary.csv')
    pd.DataFrame([
        ['case14 exact sequential k=3','NOT RUN BY DEFAULT',
         '6,840 ordered sequences and >20k defender solves; k=2 exact enumeration is retained as ground truth.'],
        ['case240 independent guided','FULL MODE ONLY',
         'Top-10 guided search requires many large MILPs; same-sequence replay and Greedy-FLOW still evaluate Case 240 by default.'],
        ['large-case Greedy-IMPACT','SELECTIVE',
         'Every remaining line is solved each round, so 162/240 full sweeps are intentionally not forced.'],
        ['exact author randomized loads','UNAVAILABLE',
         'Released experiments use fresh ±5% random load perturbations without storing the RNG state.'],
        ['PowerModels feature parity','PARTIAL',
         'Core DC/ramp/on-off/island constraints are implemented, but this is not a complete PowerModels reimplementation.'],
    ], columns=['test','status','reason']).to_csv(RESULTS / 'limitations.csv', index=False)
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--full', action='store_true',
                    help='Also run the most expensive large-grid guided searches.')
    args = ap.parse_args()
    exp1 = load_exp1(DATA / 'author_exp1.csv')
    exp2 = load_exp2(DATA / 'author_exp2.csv')
    rows = []
    replay_author_sequences(exp1, rows)
    run_flow_sweep(exp1, rows)
    run_guided_and_impact(exp1, rows, full=args.full)
    permutation_reproduction(exp1, rows)
    ramp_sequence_replay(exp2, rows)
    full_vs_simple_ramp(exp2, rows)
    perturbation_test(exp1, rows, full=args.full)
    df = write_outputs(rows)
    print(df.groupby(['experiment', 'status']).size().unstack(fill_value=0))


if __name__ == '__main__':
    main()
