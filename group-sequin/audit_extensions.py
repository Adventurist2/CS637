"""Independent audits and solver-precision controls for saved extensions.

Run after run_extensions.py --phase all. Does not change the group defaults.
"""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from itertools import permutations
import json
import argparse
import numpy as np
import pandas as pd
from extensions import Evaluator, critical_group, metrics, enumerate_outages
from run_extensions import ROOT,OUT,case_obj,save_json,save_csv,fingerprint


def tight_baseline_task(setting):
    name,seed,fraction,ramp,sequences=setting
    case=case_obj(name,seed);critical=critical_group(case,fraction)
    e=Evaluator(case,ramp,critical=critical)
    # Ones preserve total-service objective, while explicitly requesting the
    # same 1e-8 relative gap as all priority policies.
    e.options['service_weights']=np.ones(len(case['bus']))
    rows=[]
    for sequence in sequences:
        seq=tuple(json.loads(sequence));state=e.evaluate(seq)
        rows.append({'case':name,'seed':seed,'fraction':fraction,'ramp':ramp,
                     'sequence':sequence,'policy':'total-tight',**metrics(case,state,critical)})
    print('tight baseline',name,seed,fraction,ramp,len(rows),flush=True)
    return rows


def precision_controls(workers):
    c=pd.read_csv(OUT/'priority.csv',dtype={'case':str})
    settings=[]
    for key,g in c[c.policy=='total'].groupby(['case','seed','fraction','ramp']):
        settings.append((*key,g.sequence.tolist()))
    rows=[]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for batch in pool.map(tight_baseline_task,settings):
            rows+=batch
            save_csv('priority_tight_baseline.csv',rows)
    summarize_priority()


def summarize_priority():
    c=pd.read_csv(OUT/'priority.csv',dtype={'case':str})
    b=pd.read_csv(OUT/'priority_tight_baseline.csv',dtype={'case':str})
    keys=['case','seed','fraction','ramp','sequence']
    paired=c.merge(b[keys+['critical_shed_mw','shed_mw']],on=keys,suffixes=('','_tight'),validate='many_to_one')
    assert len(paired)==len(c)
    paired['critical_gain_mw']=paired.critical_shed_mw_tight-paired.critical_shed_mw
    paired['extra_total_shed_mw']=paired.shed_mw-paired.shed_mw_tight
    out=[]
    for policy,g in paired.groupby('policy'):
        out.append({'policy':policy,'pairs':len(g),'critical_improves':int((g.critical_gain_mw>.001).sum()),
                    'critical_worsens':int((g.critical_gain_mw<-.001).sum()),
                    'extra_total_shed':int((g.extra_total_shed_mw>.001).sum()),
                    'maximum_critical_gain_mw':float(g.critical_gain_mw.max()),
                    'maximum_critical_harm_mw':float(-g.critical_gain_mw.min())})
    save_json(OUT/'priority_precision_comparison.json',out)
    full=pd.concat([c,b],ignore_index=True)
    cs=full.groupby(['case','seed','fraction','ramp','policy']).agg(
        critical_retained_fraction=('critical_retained_fraction','min'),shed_mw=('shed_mw','max')).reset_index()
    cs.groupby(['case','fraction','ramp','policy'])[['critical_retained_fraction','shed_mw']].mean().reset_index().to_csv(OUT/'priority_precision_summary.csv',index=False)
    # Most dramatic positive and most harmful examples against matched precision.
    g=paired[paired.policy=='critical-first']
    save_json(OUT/'priority_examples.json',{'largest_gain':g.loc[g.critical_gain_mw.idxmax()].to_dict(),
               'largest_harm':g.loc[g.critical_gain_mw.idxmin()].to_dict()})


def verify():
    p=pd.read_csv(OUT/'protection.csv',dtype={'case':str})
    t=pd.read_csv(OUT/'timing.csv',dtype={'case':str})
    c=pd.read_csv(OUT/'priority.csv',dtype={'case':str})
    s=pd.read_csv(OUT/'protection_sensitivity.csv',dtype={'case':str})
    assert len(p)==1648
    assert len(s)==144
    assert not p.duplicated(['case','seed','split','budget','policy']).any()
    # Every matched comparison must cover exactly the same sequence set.
    cells=0
    for key,g in c.groupby(['case','seed','fraction','ramp']):
        sets=[set(a.sequence) for _,a in g.groupby('policy')]
        assert len(sets)==4 and all(a==sets[0] for a in sets)
        if key[0]=='14': assert len(sets[0])==380
        assert not g.duplicated(['policy','sequence']).any()
        cells+=1
    assert cells==45
    for key,g in t.groupby(['case','seed']):
        sets=[set(a.sequence) for _,a in g.groupby(['horizon_minutes','pattern','simultaneous'])]
        assert len(sets)==18 and all(a==sets[0] for a in sets)
    # Filtered oracle maximum equals a fresh complete post-protection replay.
    replay=[]
    for name in ('14','39'):
        row=p[(p.case==name)&(p.seed==100)&(p.budget==2)&(p.policy=='robust-sequential')].iloc[0]
        protected=json.loads(row.protected)
        e=Evaluator(case_obj(name,100),protected=protected)
        fresh=enumerate_outages(e).worst()[0]
        assert abs(fresh-row.shed_mw)<1e-6
        replay.append({'case':name,'seed':100,'protected':protected,'saved_mw':row.shed_mw,
                       'fresh_mw':fresh,'responses':e.response_evaluations})
    stats=[]
    for file in (OUT/'oracles').glob('*.npz'):
        with np.load(file,allow_pickle=False) as z:
            meta=json.loads(str(z['metadata']))
            assert meta['source']==fingerprint()
            expected=190 if meta['case']=='14' else 1035
            if not meta['simultaneous']: expected*=2
            assert len(z['sequences'])==expected
            stats.append(json.loads(str(z['stats'])))
    compatibility=json.loads((OUT/'default_compatibility.json').read_text())
    assert compatibility['max_state_difference_mw']==0
    result={'status':'PASS','priority_configuration_cells':cells,'priority_rows':len(c),'timing_rows':len(t),
            'protection_rows':len(p),'stress_rows':len(s),'oracle_tables':len(stats),
            'oracle_optimizer_calls':sum(r['optimizer_calls'] for r in stats),
            'fresh_exact_replays':replay,'default_compatibility_probes':len(compatibility['probes']),
            'max_default_state_difference_mw':compatibility['max_state_difference_mw'],
            'max_residual':float(max(p.max_residual.max(),t.max_residual.max(),c.max_residual.max())),
            'max_priority_floor_mw':float(c.service_floor_tolerance_mw.max())}
    save_json(OUT/'validation.json',result)
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--phase',choices=['all','precision','verify'],default='all');ap.add_argument('--workers',type=int,default=2);a=ap.parse_args()
    if a.phase in ('all','precision'): precision_controls(a.workers)
    if a.phase in ('all','verify'): verify()
