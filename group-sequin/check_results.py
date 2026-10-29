from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
path = HERE / 'results' / 'results.csv'
if not path.exists():
    raise SystemExit('Run: python run_tests.py')
r = pd.read_csv(path)

expected = {'case14','case39','case60','case118','case162','case240'}
assert expected.issubset(set(r.case))
flow = r[(r.experiment == 'k_sweep_search') & (r.method == 'greedy_flow')]
assert flow.case.nunique() == 6
for case in expected:
    assert set(flow[flow.case == case].k) == set(range(2, 9))

g = r[(r.experiment == 'selected_search_reproduction') & (r.method == 'guided')]
for k in [2,3,4]:
    assert abs(g[(g.case == 'case14') & (g.k == k)].error_percent.iloc[0]) < 1e-6
for k in [2,3,4,6]:
    assert abs(g[(g.case == 'case39') & (g.k == k)].error_percent.iloc[0]) < 2.0
assert abs(g[(g.case == 'case162') & (g.k == 2)].error_percent.iloc[0]) < 5.0

rep = r[(r.experiment == 'author_sequence_replay') &
        (r.case == 'case240') & (r.method == 'replay_sequin')]
for k in [2,4,8]:
    assert abs(rep[rep.k == k].error_percent.iloc[0]) < 2.0

ramp = r[r.experiment == 'ramp_sequence_replay']
for case in ['case39','case162','case240']:
    assert ramp[ramp.case == case].error_percent.abs().median() < 1.0

ab = r[(r.experiment == 'model_ablation') & (r.method == 'simple_ramp_impact')]
assert abs(ab[ab.ramp == 0.1].error_percent.iloc[0]) > 40

p = r[r.experiment == 'load_perturbation_sensitivity']
assert p.our_load_shed.max() - p.our_load_shed.min() > 10

print('PASS: six-case coverage, key reproductions, expected divergences, and sensitivity tests are present.')
