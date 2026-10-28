"""Independently audit experiment completeness, pairing, arithmetic and replays."""

from pathlib import Path
import csv
from collections import defaultdict
from hashlib import sha256
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np

from sequin import GridSimulator, SolverError, load_case
from sequin.extensions import critical_loads, service_metrics, timed_trace
from sequin.report import write_json
from sequin.search import Evaluator, search

OUT = ROOT / "output" / "part2"


def read(name):
    with (OUT / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main():
    checks, fresh = [], []
    p, s, t, c = [read(n) for n in ("protection.csv", "protection_sensitivity.csv", "timing.csv", "priority.csv")]
    assert len(p) == 1648, "Incomplete main protection matrix"
    assert len(s) == 144, "Incomplete stress request matrix"
    assert {r["case"] for r in p} == {"14", "39"}
    assert {r["seed"] for r in p if r["split"] == "design"} == {"0", "1", "2"}
    assert {r["seed"] for r in p if r["split"] == "test"} == {"100", "101", "102", "103", "104"}
    for r in p:
        protected, seq = json.loads(r["protected"]), json.loads(r["adaptive_sequence"])
        assert len(protected) == int(r["budget"])
        assert len(seq) == len(set(seq)) == 2 and not set(seq) & set(protected)
        assert 0 <= float(r["shed_fraction"]) <= 1 + 1e-7
        assert float(r["reduction_mw"]) >= -1e-4
        assert abs(float(r["no_defense_shed_mw"]) - float(r["shed_mw"]) - float(r["reduction_mw"])) < 1e-5
    checks.append("Complete protection matrix; design/test separation; equal budgets; adaptive sequence eligibility; monotonic finite-choice loss")
    valid_s = [r for r in s if r["status"] == "ok"]
    infeasible_s = [r for r in s if r["status"] == "infeasible_initial"]
    assert len(valid_s) + len(infeasible_s) == len(s)
    for r in infeasible_s:
        assert "Infeasible" in r["error"] and not r.get("shed_mw")
    for name, seed, perturb in {(r["case"], r["seed"], r["perturb"]) for r in infeasible_s}:
        try:
            GridSimulator(load_case(name).scenario(int(seed), float(perturb))).initialize()
        except SolverError as exc:
            assert "Infeasible" in str(exc)
        else:
            raise AssertionError("Recorded infeasible stress scenario now initializes feasibly")
    checks.append("Every stress request is either feasible or explicitly initial-infeasible, with no invented loss metric")
    # Fresh exact searches with the CURRENT model independently check checkpointed worst cases.
    for name in ("14", "39"):
        selected = next(r for r in p if r["case"] == name and r["seed"] == "100" and
                        r["budget"] == "2" and r["policy"] == "robust-sequential")
        case = load_case(name).scenario(100)
        sim = GridSimulator(case)
        result = search(Evaluator(sim, sim.initialize(), json.loads(selected["protected"])), "enum", 2)
        difference = abs(result.state.shed_mw - float(selected["shed_mw"]))
        assert difference < 1e-3
        fresh.append({"case": name, "test_seed": 100, "policy": "robust-sequential", "budget": 2,
                      "fresh_exact_shed_mw": result.state.shed_mw, "saved_shed_mw": float(selected["shed_mw"]),
                      "difference_mw": difference, "sequence": list(result.sequence),
                      "optimizer_calls": result.optimizer_calls})
        print(f"fresh protection exact verification case={name}: difference={difference:.3g} MW", flush=True)
    checks.append("Fresh current-model exhaustive post-protection searches agree with stored case-14 and case-39 held-out worst loss within 0.001 MW")
    # Each timing combination must replay the identical sequence cohort.
    cohorts = defaultdict(lambda: defaultdict(set))
    for r in t:
        assert r["simultaneous"] in ("True", "False")
        key = (r["case"], r["seed"])
        setting = (r["pattern"], r["horizon_minutes"], r["simultaneous"])
        cohorts[key][setting].add(tuple(json.loads(r["sequence"])))
        assert -1e-8 <= float(r["energy_fraction"]) <= float(r["shed_fraction"]) + 1e-6
        assert 0 <= float(r["shed_fraction"]) <= 1+1e-7
    assert len(cohorts) == 9
    for groups in cohorts.values():
        assert len(groups) == 18
        assert all(value == next(iter(groups.values())) for value in groups.values())
    # Recompute actual window arithmetic, response traces, MW and proxy MWh.
    for name in ("14", "39", "118"):
        r = next(r for r in t if r["case"] == name and r["pattern"] == "early-cluster" and
                 r["horizon_minutes"] == "15.0" and r["simultaneous"] == "False")
        case = load_case(name).scenario(int(r["seed"]))
        sim = GridSimulator(case)
        result, states = timed_trace(sim, sim.initialize(), json.loads(r["sequence"]), (1, 1, 13))
        assert abs(result["snapshot_unserved_energy_mwh"] - float(r["snapshot_energy_mwh"])) < 1e-3
        assert abs(sum(w["snapshot_energy_mwh"] for w in result["windows"]) - result["snapshot_unserved_energy_mwh"]) < 1e-8
        assert states[-1].failed == frozenset(json.loads(r["sequence"]))
        assert all(a.shed_mw <= b.shed_mw + 1e-3 for a, b in zip(states, states[1:]))
    checks.append("Timing has all 9 case/seed combinations, all 18 pattern/horizon/comparator cells, identical per-scenario sequence cohorts, and fresh energy/trace arithmetic checks")
    priority = defaultdict(lambda: defaultdict(set))
    for r in c:
        key = tuple(r[k] for k in ("case", "seed", "critical_bus_fraction", "ramp"))
        priority[key][r["policy"]].add(tuple(json.loads(r["sequence"])))
        assert -1e-7 <= float(r["critical_retained_fraction"]) <= 1+1e-7
        assert abs(float(r["critical_shed_mw"]) + float(r["noncritical_shed_mw"]) - float(r["shed_mw"])) < 1e-3
        assert float(r["service_floor_tolerance_pu"]) <= 1e-5
    assert len(priority) == 45
    expected_settings = {("0.1", "0.1"), ("0.25", "0.025"), ("0.25", "0.1"),
                         ("0.25", "0.5"), ("0.5", "0.1")}
    for case in ("14", "39", "118"):
        for seed in ("0", "1", "2"):
            assert {(key[2], key[3]) for key in priority if key[:2] == (case, seed)} == expected_settings
    for key, policies in priority.items():
        assert set(policies) == {"total", "weight-2", "weight-10", "critical-first"}
        assert all(value == next(iter(policies.values())) for value in policies.values())
        if key[0] == "14":
            assert len(next(iter(policies.values()))) == 380
    for name in ("14", "39", "118"):
        r = next(r for r in c if r["case"] == name and r["policy"] == "critical-first" and
                 r["critical_bus_fraction"] == "0.25" and r["ramp"] == "0.1")
        case = load_case(name).scenario(int(r["seed"]))
        critical = critical_loads(case, .25)
        initial = GridSimulator(case).initialize()
        e = Evaluator(GridSimulator(case, .1, critical_buses=critical), initial)
        state = e.evaluate(json.loads(r["sequence"]))
        metrics = service_metrics(case, state, critical)
        assert abs(metrics["critical_shed_mw"] - float(r["critical_shed_mw"])) < 1e-3
        assert abs(metrics["shed_mw"] - float(r["shed_mw"])) < 1e-3
    checks.append("Priority covers 45 scenario/settings cells, all four policies on identical cohorts, exact case-14 pairs, bounded service floors, consistent service metrics and fresh policy replays")
    manifest = json.loads((OUT / "run_manifest.json").read_text())
    assert manifest["protection_rows"] == len(p)
    assert manifest["sensitivity_rows"] == len(s)
    assert manifest["timing_rows"] == len(t)
    assert manifest["priority_rows"] == len(c)
    assert manifest["max_residual_pu"] <= 2e-6
    output = {"status": "passed", "checks": checks, "fresh_protection_verifications": fresh,
              "rows": {"protection": len(p), "stress_feasible": len(valid_s),
                       "stress_initial_infeasible": len(infeasible_s), "timing": len(t), "priority": len(c)},
              "raw_sha256": {n: sha256((OUT / n).read_bytes()).hexdigest() for n in
                             ("protection.csv", "protection_sensitivity.csv", "timing.csv", "priority.csv")}}
    write_json(OUT / "data_audit.json", output)
    print("Passed all independent data audits", flush=True)


if __name__ == "__main__":
    main()
