from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
RESULTS, PLOTS = HERE / 'results', HERE / 'plots'
PLOTS.mkdir(exist_ok=True)
path = RESULTS / 'results.csv'
if not path.exists():
    raise SystemExit('Run: python run_tests.py')
df = pd.read_csv(path)

d = df[(df.experiment == 'author_sequence_replay') & (df.method == 'replay_sequin')]
fig, ax = plt.subplots(figsize=(8.5, 4.8))
for case, g in d.groupby('case'):
    g = g.sort_values('k'); ax.plot(g.k, g.error_percent.abs(), marker='o', label=case)
ax.axhline(5, linestyle='--', linewidth=1)
ax.set(xlabel='Attack budget k', ylabel='Absolute error (%)',
       title='Same author SEQUIN sequence replay: defender/model fidelity')
ax.legend(ncol=3, fontsize=8); fig.tight_layout()
fig.savefig(PLOTS / '01_author_sequence_replay_error.png', dpi=180); plt.close(fig)

d = df[(df.experiment == 'k_sweep_search') & (df.method == 'greedy_flow')]
fig, axes = plt.subplots(2, 3, figsize=(12, 7), sharex=True)
for ax, case in zip(axes.flat, ['case14','case39','case60','case118','case162','case240']):
    g = d[d.case == case].sort_values('k')
    ax.plot(g.k, g.our_load_shed, marker='o', label='Python')
    ax.plot(g.k, g.author_load_shed, marker='s', label='Author')
    ax.set_title(case); ax.set_xlabel('k'); ax.set_ylabel('load shed (p.u.)')
axes.flat[0].legend(fontsize=8)
fig.suptitle('Greedy-FLOW k-sweep across all six paper networks')
fig.tight_layout(); fig.savefig(PLOTS / '02_flow_k_sweep_all_cases.png', dpi=180); plt.close(fig)

d = df[(df.experiment == 'selected_search_reproduction') &
       (df.method.isin(['guided','greedy_impact']))].sort_values(['method','case','k'])
fig, ax = plt.subplots(figsize=(9, max(4.5, 0.32 * len(d))))
y = np.arange(len(d)); ax.barh(y, d.error_percent)
ax.axvline(0, linewidth=1); ax.axvline(5, linestyle='--', linewidth=1); ax.axvline(-5, linestyle='--', linewidth=1)
ax.set_yticks(y)
ax.set_yticklabels([f'{r.case} k={int(r.k)} {r.method}' for r in d.itertuples()], fontsize=8)
ax.set(xlabel='Error vs author reference (%)', title='Independent Guided / Greedy-IMPACT reproduction')
fig.tight_layout(); fig.savefig(PLOTS / '03_selected_search_errors.png', dpi=180); plt.close(fig)

d = df[df.experiment == 'ramp_sequence_replay']
fig, ax = plt.subplots(figsize=(8.5, 4.8))
for case, g in d.groupby('case'):
    z = g.groupby('ramp').error_percent.apply(lambda x: x.abs().median()).reset_index().sort_values('ramp')
    ax.plot(z.ramp, z.error_percent, marker='o', label=case)
ax.set(xlabel='Generator ramp fraction', ylabel='Median absolute error (%) over k=2,3,4',
       title='Ramp sensitivity replay using author attack sequences')
ax.legend(ncol=3, fontsize=8); fig.tight_layout()
fig.savefig(PLOTS / '04_ramp_replay_error.png', dpi=180); plt.close(fig)

d = df[df.experiment == 'model_ablation']
fig, ax = plt.subplots(figsize=(7.2, 4.6))
for method, g in d.groupby('method'):
    g = g.sort_values('ramp'); ax.plot(g.ramp, g.our_load_shed, marker='o', label=method)
ref = d.groupby('ramp').author_load_shed.first().reset_index().sort_values('ramp')
ax.plot(ref.ramp, ref.author_load_shed, marker='s', linewidth=2, label='author reference')
ax.set(xlabel='Generator ramp fraction', ylabel='Load shed (p.u.)',
       title='Case 39 k=3: defender-model ablation')
ax.legend(fontsize=8); fig.tight_layout()
fig.savefig(PLOTS / '05_full_vs_simple_ramp.png', dpi=180); plt.close(fig)

d = df[df.experiment.isin(['k_sweep_search','selected_search_reproduction'])]
fig, ax = plt.subplots(figsize=(8, 5))
for method, g in d.groupby('method'):
    ax.scatter(g.defender_solves, g.elapsed_seconds, label=method, alpha=0.8)
ax.set(xlabel='Defender optimization calls', ylabel='Measured Python runtime (s)',
       title='Search cost: optimizer calls vs runtime')
ax.legend(fontsize=8); fig.tight_layout()
fig.savefig(PLOTS / '06_search_cost_runtime.png', dpi=180); plt.close(fig)

d = df[df.experiment == 'load_perturbation_sensitivity']
fig, ax = plt.subplots(figsize=(6.8, 4.4))
seeds = d.method.str.extract(r'(\d+)$')[0]
ax.bar(seeds, d.our_load_shed)
ax.axhline(d.author_load_shed.iloc[0], linestyle='--', label='author cached reference')
ax.set(xlabel='Random seed', ylabel='Guided load shed (p.u.)',
       title='Case 39 k=3: ±5% load perturbation sensitivity')
ax.legend(); fig.tight_layout()
fig.savefig(PLOTS / '07_load_perturbation_sensitivity.png', dpi=180); plt.close(fig)

print('Wrote plots/01 through plots/07.')
