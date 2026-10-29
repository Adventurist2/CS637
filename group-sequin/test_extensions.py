"""Run: python -m pytest test_extensions.py -q"""
from itertools import permutations
import numpy as np
import pytest
from grid_model import initial_state, defend, total_load, active_lines
from run_extensions import case_obj
from extensions import (Evaluator, OutageTable, enumerate_outages, protection,
                        defense_objective, critical_group, metrics, timed_trace)


def tiny():
    """Two parallel lines feeding unequal loads, for operator tradeoffs."""
    c=case_obj('14',0,0)
    # Use a real case for parser/data validity; comparisons below enumerate it.
    return c


def test_default_objective_compatibility():
    c=tiny();start=initial_state(c)
    a=defend(c,[3],start)
    b=defend(c,[3],start,service_weights=np.ones(len(c['bus'])))
    assert a is not None and b is not None
    assert abs(a['served'].sum()-b['served'].sum())<1e-5
    assert a['max_residual']<1e-5


def test_ordered_prefix_cache_and_irreversibility():
    c=tiny();e=Evaluator(c)
    a=e.evaluate((3,1));b=e.evaluate((1,3))
    assert (3,1) in e.cache and (1,3) in e.cache
    assert metrics(c,a)['shed_mw'] > metrics(c,b)['shed_mw'] + 1
    before=e.optimizer_calls
    assert e.evaluate((3,1)) is a
    assert e.optimizer_calls==before
    assert np.all(a['served']<=e.evaluate((3,))['served']+1e-6)


def test_table_filter_matches_fresh_defense():
    c=tiny();e=Evaluator(c);table=enumerate_outages(e)
    assert len(table.sequences)==380
    plan=protection([table],e.lines,2)
    value,seq=table.worst(plan)
    fresh=Evaluator(c,protected=plan)
    best=max(metrics(c,fresh.evaluate(s))['shed_mw'] for s in permutations(fresh.lines,2))
    assert abs(value-best)<1e-6
    assert not set(plan)&set(seq)


def test_outer_oracle_bounds_greedy():
    t=OutageTable(np.array([(1,2),(2,1),(1,3),(3,1),(2,3),(3,2)]),np.array([10,9,8,7,3,2.]),10.)
    exact=protection([t],(1,2,3),1,exact=True)
    greedy=protection([t],(1,2,3),1)
    assert exact==(1,) and greedy==exact
    assert defense_objective([t],exact)[0]==.3


@pytest.mark.parametrize('simultaneous',[False,True])
def test_time_accounting_and_equal_decisions(simultaneous):
    c=tiny();e=Evaluator(c)
    t=timed_trace(e,(3,1),[1.,9.],simultaneous=simultaneous)
    assert e.response_evaluations==2
    assert abs(t['snapshot_unserved_energy_mwh']-sum(w['shed_mw']*w['duration_minutes']/60 for w in t['windows']))<1e-9
    assert sum(w['duration_minutes'] for w in t['windows'])==10
    if simultaneous:
        assert t['windows'][1]['new_failures']==[]


@pytest.mark.parametrize('policy',['weight-2','weight-10','critical-first'])
def test_one_step_priority_never_reduces_its_own_objective(policy):
    c=case_obj('39',0,0);crit=critical_group(c)
    base=Evaluator(c,critical=crit);new=Evaluator(c,policy=policy,critical=crit,start=base.cache[()])
    a=base.evaluate((14,));b=new.evaluate((14,))
    if policy=='critical-first':
        assert b['served'][list(crit)].sum()>=a['served'][list(crit)].sum()-2e-4
    else:
        weights=np.ones(len(c['bus']));weights[list(crit)]=int(policy.split('-')[1])
        assert weights@b['served']>=weights@a['served']-2e-4
    assert b['max_residual']<2e-4


def test_group_shutdown_can_restart():
    # Documents the group's actual semantics; persistent shutdown differs.
    c=tiny();start=initial_state(c);start['pg'][:]=0;start['served'][:]=0
    # All load already lost, so inspect feasibility with fixed negative-free data.
    result=defend(c,[],start)
    assert result is not None
    # No online status is carried as an upper bound: explicit metadata does not
    # introduce a persistent-shutdown rule into the baseline.
    previous=initial_state(c);previous['online']=np.zeros(len(c['gen']))
    state=defend(c,[],previous)
    assert state['pg'].sum()>0


@pytest.mark.parametrize('sequence,durations', [((1,1),(5,5)),((1,2),(0,5)),((1,2),(float('nan'),5)),((999,2),(5,5))])
def test_invalid_time_inputs(sequence,durations):
    with pytest.raises(ValueError): timed_trace(Evaluator(tiny()),sequence,durations)


def test_enumeration_guard():
    with pytest.raises(ValueError): enumerate_outages(Evaluator(tiny()),k=4,max_sequences=100)


def test_group_criticality_and_cohort_search_are_distinct():
    c=case_obj('39',0,0);critical=critical_group(c)
    e=Evaluator(c,policy='critical-first',critical=critical)
    seq=e.guided(2,top_n=3,critical_score=True)
    assert len(set(seq))==2
    assert e.evaluate(seq)['max_residual']<2e-4
