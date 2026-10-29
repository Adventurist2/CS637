"""Reproducible three-extension study on the GROUP'S SciPy model.

Run: python run_extensions.py --phase all
No previous-project extension results are read. Only --phase comparison imports
the neighboring implementation, and it never supplies an extension response.
"""
import os
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
from pathlib import Path
from hashlib import sha256
from itertools import permutations
from concurrent.futures import ProcessPoolExecutor
from time import perf_counter
import argparse
import json
import platform
import subprocess
import sys

import numpy as np
import pandas as pd
import scipy
import networkx as nx

from grid_model import load_case, initial_state, active_lines, total_load
from extensions import (Evaluator, OutageTable, critical_group, demand, metrics,
                        enumerate_outages, protection, defense_objective, timed_trace)
from run_tests import CASES

ROOT = Path(__file__).resolve().parent
OUT = ROOT/'results'/'extensions'
DESIGN = (0,1,2)
TEST = (100,101,102,103,104)
POLICIES = ('total','weight-2','weight-10','critical-first')


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False,
                   default=lambda x: x.item() if isinstance(x, np.generic) else str(x)), encoding='utf-8')


def save_csv(name, rows):
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT/name, index=False)


def fingerprint():
    return sha256(b''.join((ROOT/name).read_bytes() for name in
                  ('grid_model.py','extensions.py','run_extensions.py'))).hexdigest()


def case_obj(name, seed=0, perturb=.05):
    return load_case(ROOT/'data'/CASES['case'+name], perturb=perturb, seed=seed)


def oracle_task(settings):
    name, seed, ramp, perturb, simultaneous = settings
    case = case_obj(name, seed, perturb)
    key = {'case': name, 'seed': seed, 'ramp': ramp, 'perturb': perturb,
           'simultaneous': simultaneous, 'source': fingerprint(), 'scipy': scipy.__version__,
           'case_sha256': sha256((ROOT/'data'/CASES['case'+name]).read_bytes()).hexdigest()}
    digest = sha256(json.dumps(key,sort_keys=True).encode()).hexdigest()[:20]
    file = OUT/'oracles'/f'{name}_{seed}_{digest}.npz'
    if file.exists():
        with np.load(file, allow_pickle=False) as z:
            return 'ok', settings, OutageTable(z['sequences'],z['shed_mw'],float(z['demand_mw'])), json.loads(str(z['stats']))
    start = perf_counter()
    try:
        evaluator = Evaluator(case, ramp)
    except RuntimeError as exc:
        if 'infeasible' in str(exc).lower():
            return 'initial-infeasible', settings, None, {'error': str(exc)}
        raise
    table = enumerate_outages(evaluator, simultaneous=simultaneous)
    stats = {'responses': evaluator.response_evaluations, 'optimizer_calls': evaluator.optimizer_calls,
             'max_residual': evaluator.max_residual, 'seconds': perf_counter()-start}
    file.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(file, sequences=table.sequences, shed_mw=table.shed_mw,
                        demand_mw=table.demand_mw, stats=json.dumps(stats), metadata=json.dumps(key))
    print('oracle', settings, stats, flush=True)
    return 'ok', settings, table, stats


def protection_study(workers):
    rows, sensitivity, designs = [], [], []
    for name in ('14','39'):
        settings = [(name,s,.1,.05,False) for s in DESIGN+TEST] + [(name,s,.1,.05,True) for s in DESIGN]
        with ProcessPoolExecutor(max_workers=workers) as pool:
            outcomes = list(pool.map(oracle_task,settings))
        if any(o[0] != 'ok' for o in outcomes):
            raise RuntimeError('Nominal scenario is initially infeasible; inspect settings')
        tables = [o[2] for o in outcomes[:3]]
        simultaneous = [o[2] for o in outcomes[8:]]
        case = case_obj(name)
        ids = tuple(i for i,_ in active_lines(case,()))
        starts = [initial_state(case_obj(name,s)) for s in DESIGN]
        flow = sorted(ids,key=lambda i:(-np.mean([abs(s['flows'][i]) for s in starts]),i))
        graph = nx.MultiGraph()
        graph.add_nodes_from(int(b) for b in case['bus'][:,0])
        for i,br in active_lines(case,()): graph.add_edge(int(br[0]),int(br[1]),key=i)
        centrality = {k[2]:v for k,v in nx.edge_betweenness_centrality(graph).items()}
        between = sorted(ids,key=lambda i:(-centrality[i],i))
        chosen = {}
        for budget in range(4):
            plans = {'robust-sequential': protection(tables,ids,budget),
                     'single-scenario': protection(tables[:1],ids,budget),
                     'simultaneous-design': protection(simultaneous,ids,budget),
                     'initial-flow': tuple(flow[:budget]),'betweenness': tuple(between[:budget])}
            if budget <= 2: plans['exact-design'] = protection(tables,ids,budget,exact=True)
            for j in range(20): plans[f'random-{j:02d}'] = tuple(np.random.default_rng(7000+j).permutation(ids)[:budget].tolist())
            chosen[budget] = plans['robust-sequential']
            designs.append({'case':name,'budget':budget,'policies':plans,
                            'robust_design_objective':defense_objective(tables,plans['robust-sequential']),
                            'exact_design_objective':defense_objective(tables,plans['exact-design']) if budget<=2 else None})
            for outcome in outcomes[:8]:
                _, (_,seed,_,_,_), table, stats = outcome
                baseline = table.worst()[0]
                for policy,protected in plans.items():
                    value, sequence = table.worst(protected)
                    rows.append({'case':name,'seed':seed,'split':'design' if seed in DESIGN else 'test',
                                 'budget':budget,'policy':policy,'protected':json.dumps(protected),
                                 'adaptive_sequence':json.dumps(sequence),'shed_mw':value,
                                 'shed_fraction':value/table.demand_mw,'reduction_mw':baseline-value,
                                 'reduction_pp':100*(baseline-value)/table.demand_mw,
                                 'max_residual':stats['max_residual']})
            save_csv('protection.csv',rows)
            save_json(OUT/'defense_designs.json',designs)
        settings = [(name,s,r,p,False) for r in (.025,.1,.5) for p in (0.,.15) for s in TEST[:2]]
        with ProcessPoolExecutor(max_workers=workers) as pool:
            for status,setting,table,stats in pool.map(oracle_task,settings):
                _,seed,ramp,perturb,_ = setting
                for budget in (1,2):
                    for policy,protected in [('robust-sequential',chosen[budget]),('initial-flow',flow[:budget]),('none',())]:
                        row = {'case':name,'seed':seed,'ramp':ramp,'perturb':perturb,'budget':budget,
                               'policy':policy,'status':status,'protected':json.dumps(protected)}
                        if status == 'ok':
                            value,seq = table.worst(protected)
                            row.update(shed_mw=value,shed_fraction=value/table.demand_mw,
                                       adaptive_sequence=json.dumps(seq),max_residual=stats['max_residual'])
                        else: row['error'] = stats['error']
                        sensitivity.append(row)
                save_csv('protection_sensitivity.csv',sensitivity)
    return len(rows)


def timing_task(setting):
    name, seed = setting
    case = case_obj(name,seed)
    e = Evaluator(case)
    sets = (e.guided(3),e.flow(3))
    cohort = sorted(set(s for attack in sets for s in permutations(attack)))
    rows = []
    for horizon in (7.5,15.,30.):
        for pattern,ratio in [('even',(1,1,1)),('early',(.2,.2,2.6)),('late',(2.6,.2,.2))]:
            durations = np.array(ratio)*horizon/3
            for seq in cohort:
                for simultaneous in (False,True):
                    ev = Evaluator(case,start=e.cache[()])
                    trace = timed_trace(ev,seq,durations,simultaneous=simultaneous)
                    rows.append({'case':name,'seed':seed,'horizon_minutes':horizon,'pattern':pattern,
                                 'simultaneous':simultaneous,'sequence':json.dumps(seq),
                                 'cohort_sequences':len(cohort),'final_shed_mw':trace['final_shed_mw'],
                                 'final_shed_fraction':trace['final_shed_mw']/total_load(case),
                                 'snapshot_unserved_energy_mwh':trace['snapshot_unserved_energy_mwh'],
                                 'snapshot_energy_fraction':trace['snapshot_unserved_energy_mwh']/(total_load(case)*horizon/60),
                                 'optimizer_calls':ev.optimizer_calls,'max_residual':ev.max_residual})
    print('timing',setting,len(rows),flush=True)
    return rows


def timing_study(workers):
    rows=[]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for batch in pool.map(timing_task,[(n,s) for n in ('14','39','118') for s in DESIGN]):
            rows += batch
            save_csv('timing.csv',rows)


def priority_task(setting):
    name,seed,fraction,ramp = setting
    key = {'setting':setting,'source':fingerprint(),'scipy':scipy.__version__}
    digest = sha256(json.dumps(key,sort_keys=True).encode()).hexdigest()[:20]
    checkpoint = OUT/'priority_checkpoints'/f'{name}_{digest}.json'
    if checkpoint.exists(): return json.loads(checkpoint.read_text())
    case = case_obj(name,seed)
    critical = critical_group(case,fraction)
    start = initial_state(case)
    evs = {p:Evaluator(case,ramp,policy=p,critical=critical,start=start) for p in POLICIES}
    if name == '14':
        cohort = list(permutations(evs['total'].lines,2))
        scope = 'exhaustive ordered pairs'
    else:
        # Attack search must target the service being protected, too.
        cohort = {evs['total'].guided(2), evs['total'].flow(2)}
        for p,e in evs.items():
            cohort.add(e.guided(2))
            cohort.add(e.guided(2,critical_score=True))
        cohort = sorted(cohort)
        scope = 'shared union, includes critical-loss-targeted guided search'
    rows=[]
    for p,e in evs.items():
        for seq in cohort:
            m = metrics(case,e.evaluate(seq),critical)
            rows.append({'case':name,'seed':seed,'fraction':fraction,'ramp':ramp,'policy':p,
                         'sequence':json.dumps(seq),'critical_bus_ids':json.dumps(case['bus'][list(critical),0].astype(int).tolist()),
                         'cohort_sequences':len(cohort),'scope':scope,**m})
    save_json(checkpoint,rows)
    print('priority',setting,len(rows),'cohort',len(cohort),flush=True)
    return rows


def priority_study(workers):
    settings = [(n,s,f,r) for n in ('14','39','118') for s in DESIGN
                for f,r in ((.25,.025),(.25,.1),(.25,.5),(.1,.1),(.5,.1))]
    rows=[]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for batch in pool.map(priority_task,settings):
            rows += batch
            save_csv('priority.csv',rows)


def comparison():
    # Only this optional phase uses the neighboring independent implementation.
    sys.path.insert(0,str(ROOT.parent))
    from dataclasses import replace
    from sequin.case import load_case as prior_load
    from sequin.physics import GridSimulator
    from sequin.search import Evaluator as PriorEvaluator, search
    from search_methods import guided_search, greedy_flow, run_sequence
    import importlib.util
    pristine = subprocess.check_output(['git','show','e03e8495fb67af50f00c52daa75908e34960f151:grid_model.py'],cwd=ROOT)
    baseline_path = OUT/'original_grid_model.py'
    baseline_path.write_bytes(pristine)
    spec = importlib.util.spec_from_file_location('pristine_grid_model',baseline_path)
    baseline = importlib.util.module_from_spec(spec); spec.loader.exec_module(baseline)
    rows,initials,regression=[] ,[],[]
    for name in ('14','39','60','118','162','240'):
        case = case_obj(name,0,0)
        other = prior_load(ROOT/'data'/CASES['case'+name])
        sim = GridSimulator(other)
        prior_start,group_start = sim.initialize(),initial_state(case)
        initials.append({'case':name,'group_demand_mw':total_load(case),'prior_demand_mw':other.total_demand_mw,
                         'initial_pg_max_abs_difference_mw':float(np.abs(group_start['pg']-prior_start.generation*other.base_mva).max()),
                         'positive_gs_mw':float(np.maximum(case['bus'][:,4],0).sum()),
                         'negative_pd_mw':float(-np.minimum(case['bus'][:,2],0).sum()),
                         'nonzero_quadratic_costs':int(np.count_nonzero(other.cost[:,0]))})
        seqs={greedy_flow(case,3)[1]}
        if name in ('14','39','118'):
            seqs.add(guided_search(case,2)[1])
            pe=PriorEvaluator(sim,prior_start)
            for method in ('sequin','sequin-release'):
                seqs.add(tuple(search(pe,method,2,breadth=3).sequence))
        for seq in sorted(seqs):
            pristine_state = baseline.initial_state(case)
            previous = group_start
            prior_ev=PriorEvaluator(sim,prior_start)
            prior_none=GridSimulator(other,tie_break='none')
            prior_none_ev=PriorEvaluator(prior_none,prior_none.initialize())
            cost=Evaluator(case,start=group_start,cost_tiebreak=True)
            for j in range(len(seq)):
                prefix=seq[:j+1]
                pristine_state=baseline.defend(case,prefix,pristine_state)
                previous=Evaluator(case,start=previous).response(previous,prefix)
                if pristine_state is None: raise RuntimeError('Original baseline response failed')
                delta=max(float(np.abs(pristine_state['pg']-previous['pg']).max()),float(np.abs(pristine_state['served']-previous['served']).max()))
                regression.append({'case':name,'sequence':json.dumps(prefix),'state_max_difference_mw':delta})
                for model,state in [('group',previous),('group-cost-tie',cost.evaluate(prefix))]:
                    rows.append({'case':name,'sequence':json.dumps(prefix),'model':model,'shed_mw':metrics(case,state)['shed_mw']})
                for model,e in [('prior',prior_ev),('prior-no-tie',prior_none_ev)]:
                    rows.append({'case':name,'sequence':json.dumps(prefix),'model':model,'shed_mw':e.evaluate(prefix).shed_mw})
    save_csv('implementation_comparison.csv',rows)
    save_json(OUT/'initial_dispatch_comparison.json',initials)
    save_json(OUT/'default_compatibility.json',{'upstream_commit':'e03e8495fb67af50f00c52daa75908e34960f151',
               'probes':regression,'max_state_difference_mw':max(r['state_max_difference_mw'] for r in regression)})
    print('comparison',len(rows),'rows',flush=True)


def analyze():
    p=pd.read_csv(OUT/'protection.csv',dtype={'case':str})
    t=pd.read_csv(OUT/'timing.csv',dtype={'case':str})
    c=pd.read_csv(OUT/'priority.csv',dtype={'case':str})
    s=pd.read_csv(OUT/'protection_sensitivity.csv',dtype={'case':str})
    # Random draws average inside each scenario before averaging scenarios.
    p['policy_group']=p.policy.where(~p.policy.str.startswith('random-'),'random')
    a=p[p.split=='test'].groupby(['case','budget','policy_group','seed'])[['shed_fraction','shed_mw','reduction_pp']].mean().reset_index()
    ps=a.groupby(['case','budget','policy_group'])[['shed_fraction','shed_mw','reduction_pp']].mean().reset_index()
    ps.to_csv(OUT/'protection_summary.csv',index=False)
    ts=t.groupby(['case','seed','horizon_minutes','pattern','simultaneous'])[['final_shed_fraction','snapshot_energy_fraction']].max().reset_index()
    ts.groupby(['case','horizon_minutes','pattern','simultaneous'])[['final_shed_fraction','snapshot_energy_fraction']].mean().reset_index().to_csv(OUT/'timing_summary.csv',index=False)
    cs=c.groupby(['case','seed','fraction','ramp','policy']).agg(critical_retained_fraction=('critical_retained_fraction','min'),shed_mw=('shed_mw','max')).reset_index()
    cs.groupby(['case','fraction','ramp','policy'])[['critical_retained_fraction','shed_mw']].mean().reset_index().to_csv(OUT/'priority_summary.csv',index=False)
    keys=['case','seed','fraction','ramp','sequence']
    paired=c.merge(c[c.policy=='total'][keys+['critical_shed_mw','shed_mw']],on=keys,suffixes=('','_baseline'),validate='many_to_one')
    paired['critical_gain_mw']=paired.critical_shed_mw_baseline-paired.critical_shed_mw
    paired['extra_total_shed_mw']=paired.shed_mw-paired.shed_mw_baseline
    counts=[]
    for policy,g in paired[paired.policy!='total'].groupby('policy'):
        counts.append({'policy':policy,'paired_rows':len(g),'critical_improves':int((g.critical_gain_mw>.001).sum()),
                       'critical_worsens':int((g.critical_gain_mw<-.001).sum()),
                       'extra_total_shed':int((g.extra_total_shed_mw>.001).sum()),
                       'maximum_critical_gain_mw':float(g.critical_gain_mw.max()),
                       'maximum_critical_harm_mw':float(-g.critical_gain_mw.min())})
    ss=s[s.status=='ok'].pivot(index=['case','seed','ramp','perturb','budget'],columns='policy',values='shed_fraction')
    summary={'source_sha256':fingerprint(),'upstream_commit':'e03e8495fb67af50f00c52daa75908e34960f151',
             'rows':{'protection':len(p),'timing':len(t),'priority':len(c),'stress':len(s),
                     'stress_ok':int((s.status=='ok').sum()),'stress_initial_infeasible':int((s.status!='ok').sum())},
             'stress_comparisons':len(ss),'stress_robust_worse_than_flow':int(((ss['robust-sequential']-ss['initial-flow'])>1e-8).sum()),
             'stress_worst_excess_pp':float(100*(ss['robust-sequential']-ss['initial-flow']).max()),
             'priority_paired_counts':counts,'max_residual':max(p.max_residual.max(),t.max_residual.max(),c.max_residual.max(),s.max_residual.max()),
             'max_service_floor_tolerance_mw':float(c.service_floor_tolerance_mw.max()),
             'environment':{'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__,'pandas':pd.__version__},
             'statistical_unit':'demand scenario, not deterministic sequence rows'}
    # Paired seed bootstrap, descriptive with only five held-out scenarios.
    intervals=[]
    for name in ('14','39'):
        for q in (1,2,3):
            v=a[(a.case==name)&(a.budget==q)&(a.policy_group=='robust-sequential')].reduction_pp.to_numpy()
            means=np.random.default_rng(123).choice(v,size=(10000,len(v))).mean(axis=1)
            intervals.append({'case':name,'budget':q,'reduction_pp':float(v.mean()),'bootstrap95_pp':np.quantile(means,[.025,.975]).tolist()})
    summary['protection_intervals']=intervals
    save_json(OUT/'summary.json',summary)
    demos(paired)
    plots()
    print(json.dumps(summary,indent=2),flush=True)


def state_trace(name,seed,sequence,policy='total',fraction=.25,ramp=.1):
    case=case_obj(name,seed)
    critical=critical_group(case,fraction)
    e=Evaluator(case,ramp,policy=policy,critical=critical)
    states=[]
    for j in range(len(sequence)+1):
        state=e.evaluate(sequence[:j])
        states.append({'round':j,'failed':list(sequence[:j]),'pg_mw':state['pg'].tolist(),
                       'served_mw':state['served'].tolist(),'flows_mw':{str(k):float(v) for k,v in state['flows'].items()},
                       **metrics(case,state,critical)})
    return {'case':name,'seed':int(seed),'ramp':ramp,'fraction':fraction,'policy':policy,
            'sequence':sequence,'critical_bus_ids':case['bus'][list(critical),0].astype(int).tolist(),'states':states}


def demos(paired):
    best=paired[paired.policy=='critical-first'].sort_values('critical_gain_mw',ascending=False).iloc[0]
    seq=json.loads(best.sequence)
    demo={'selection':'Largest observed critical gain, deliberately selected example',
          'baseline':state_trace(best['case'],int(best.seed),seq,'total',float(best.fraction),float(best.ramp)),
          'priority':state_trace(best['case'],int(best.seed),seq,'critical-first',float(best.fraction),float(best.ramp))}
    save_json(OUT/'demo_priority.json',demo)
    protection_demo=[]
    p=pd.read_csv(OUT/'protection.csv',dtype={'case':str})
    for name in ('14','39'):
        r=p[(p.case==name)&(p.seed==100)&(p.budget==2)&(p.policy=='robust-sequential')].iloc[0]
        protection_demo.append({'protected':json.loads(r.protected),**state_trace(name,100,json.loads(r.adaptive_sequence))})
    save_json(OUT/'demo_protection.json',protection_demo)
    name='39';case=case_obj(name,0);e=Evaluator(case);seq=e.guided(3)
    timing=[]
    for pattern,durations in [('even',[5,5,5]),('early',[1,1,13]),('late',[13,1,1])]:
        for simultaneous in (False,True):
            timing.append({'pattern':pattern,**timed_trace(Evaluator(case,start=e.cache[()]),seq,durations,simultaneous=simultaneous)})
    save_json(OUT/'demo_timing.json',timing)


def plots():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    colors=['#087f8c','#cf5c36','#6554a4','#8a8d91','#c6a15b']
    p=pd.read_csv(OUT/'protection_summary.csv',dtype={'case':str})
    fig,axes=plt.subplots(1,2,figsize=(11,4.5),constrained_layout=True)
    for ax,name in zip(axes,('14','39')):
        for color,policy in zip(colors,('robust-sequential','initial-flow','single-scenario','simultaneous-design','random')):
            g=p[(p.case==name)&(p.policy_group==policy)]
            ax.plot(g.budget,100*g.shed_fraction,'o-',label=policy,color=color)
        ax.set(title=f'Case {name}',xlabel='Protected lines q',ylabel='Mean held-out worst shed (%)',xticks=[0,1,2,3])
        ax.grid(alpha=.2)
    axes[1].legend(fontsize=8);fig.savefig(OUT/'protection.png',dpi=180);plt.close(fig)
    t=pd.read_csv(OUT/'timing_summary.csv',dtype={'case':str})
    fig,axes=plt.subplots(2,3,figsize=(12,6.8),constrained_layout=True)
    for col,name in enumerate(('14','39','118')):
        for color,pattern in zip(colors,('even','early','late')):
            for sim,ls in ((False,'-'),(True,'--')):
                g=t[(t.case==name)&(t.pattern==pattern)&(t.simultaneous==sim)]
                for row,metric in enumerate(('final_shed_fraction','snapshot_energy_fraction')):
                    axes[row,col].plot(g.horizon_minutes,100*g[metric],ls+'o',color=color,label=f'{pattern} '+('sim' if sim else 'seq'))
        axes[0,col].set_title(f'Case {name}');axes[1,col].set_xlabel('Horizon (minutes)')
        for row in range(2): axes[row,col].grid(alpha=.2)
    axes[0,0].set_ylabel('Cohort-worst final loss (%)');axes[1,0].set_ylabel('Snapshot energy proxy (%)')
    axes[0,2].legend(fontsize=7,ncol=2);fig.savefig(OUT/'timing.png',dpi=180);plt.close(fig)
    c=pd.read_csv(OUT/'priority_summary.csv',dtype={'case':str})
    fig,axes=plt.subplots(1,3,figsize=(12,4.4),constrained_layout=True)
    for ax,name in zip(axes,('14','39','118')):
        for color,policy in zip(colors,POLICIES):
            g=c[(c.case==name)&(c.fraction==.25)&(c.policy==policy)]
            ax.plot(g.ramp,100*g.critical_retained_fraction,'o-',color=color,label=policy)
        ax.set(title=f'Case {name}',xlabel='Ramp fraction per response',ylim=(-3,103));ax.grid(alpha=.2)
    axes[0].set_ylabel('Mean worst critical service retained (%)');axes[-1].legend(fontsize=8)
    fig.savefig(OUT/'priority.png',dpi=180);plt.close(fig)
    s=pd.read_csv(OUT/'protection_sensitivity.csv',dtype={'case':str})
    g=s[s.status=='ok'].pivot(index=['case','seed','ramp','perturb','budget'],columns='policy',values='shed_fraction').reset_index()
    fig,ax=plt.subplots(figsize=(10.5,4),constrained_layout=True)
    for name,color in zip(('14','39'),colors):
        subset=g[g.case==name]
        ax.scatter(range(len(subset)),100*(subset['robust-sequential']-subset['initial-flow']),label=f'Case {name}',color=color,alpha=.75)
    ax.axhline(0,color='#333333',lw=1);ax.set(xlabel='Feasible stress cell within each case',ylabel='Robust loss minus flow loss (pp)',title='Positive values: nominal robust plan loses more than flow protection')
    ax.legend();fig.savefig(OUT/'stress.png',dpi=180);plt.close(fig)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--phase',default='all',choices=['all','comparison','protection','timing','priority','analyze']);ap.add_argument('--workers',type=int,default=2)
    args=ap.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    if args.phase in ('all','comparison'): comparison()
    if args.phase in ('all','protection'): protection_study(args.workers)
    if args.phase in ('all','timing'): timing_study(args.workers)
    if args.phase in ('all','priority'): priority_study(args.workers)
    if args.phase in ('all','analyze'): analyze()


if __name__=='__main__': main()
