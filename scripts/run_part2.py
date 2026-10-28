"""Run the second-part evaluation. No commercial solver or author cache needed.

Usage: .venv/Scripts/python.exe scripts/run_part2.py
Exact outage tables are checkpointed with source/scenario fingerprints. The
reported conclusions are built from freshly computed data, never assumed gains.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from collections import defaultdict
from hashlib import sha256
from itertools import permutations
import argparse
import html
import json
import os
from concurrent.futures import ProcessPoolExecutor
from time import perf_counter

import networkx as nx
import numpy as np

from sequin.case import load_case
from sequin.cli import environment
from sequin.extensions import (OutageTable, critical_loads, defense_objective, enumerate_outages,
                               exact_protection, robust_protection, service_metrics, timed_trace)
from sequin.physics import GridSimulator, SolverError
from sequin.report import write_csv, write_json, sequence_viewer
from sequin.search import Evaluator, search

OUT = ROOT / "output" / "part2"
DESIGN = (0, 1, 2)
TEST = (100, 101, 102, 103, 104)


class InitialScenarioInfeasible(RuntimeError):
    """A stress scenario has no fully served starting operating point."""


def fingerprint():
    return sha256(b"".join(p.name.encode() + p.read_bytes() for p in sorted((ROOT / "sequin").glob("*.py")))).hexdigest()


def oracle(case_name, seed, *, ramp=.1, perturb=.05, simultaneous=False):
    case = load_case(case_name).scenario(seed, perturb)
    sim = GridSimulator(case, ramp)
    try:
        initial = sim.initialize()
    except SolverError as exc:
        if "Infeasible" in str(exc):
            raise InitialScenarioInfeasible(f"case={case_name} seed={seed} perturb={perturb}: {exc}") from exc
        raise
    key = {"case": case.metadata(), "ramp": ramp, "simultaneous": simultaneous,
           "k": 2, "source": fingerprint(), "solver": environment()["packages"]}
    digest = sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()[:20]
    file = OUT / "oracles" / f"case{case_name}_seed{seed}_{digest}.npz"
    if file.exists():
        with np.load(file, allow_pickle=False) as data:
            stats = json.loads(str(data["stats"]))
            table = OutageTable(data["sequences"], data["shed_mw"], case.total_demand_mw,
                                stats["response_evaluations"], stats["optimizer_calls"], stats["seconds"],
                                stats["max_residual_pu"], data["critical_shed_mw"])
        print(f"oracle cached case={case_name} seed={seed} ramp={ramp} perturb={perturb} sim={simultaneous}", flush=True)
    else:
        table = enumerate_outages(sim, initial, k=2, simultaneous=simultaneous)
        file.parent.mkdir(parents=True, exist_ok=True)
        stats = {name: getattr(table, name) for name in
                 ("response_evaluations", "optimizer_calls", "seconds", "max_residual_pu")}
        np.savez_compressed(file, sequences=table.sequences, shed_mw=table.shed_mw,
                            critical_shed_mw=table.critical_shed_mw, stats=json.dumps(stats), metadata=json.dumps(key))
        print(f"oracle computed case={case_name} seed={seed} ramp={ramp} perturb={perturb} sim={simultaneous}: "
              f"{len(table.sequences)} choices in {table.seconds:.2f}s", flush=True)
    return case, sim, initial, table


def protection_study():
    rows, designs, sensitivity, stress_failures = [], [], [], []
    for name in ("14", "39"):
        with ProcessPoolExecutor(max_workers=3) as pool:
            training = list(pool.map(_oracle_task, [(name, seed, .1, .05, False) for seed in DESIGN]))
            testing = list(pool.map(_oracle_task, [(name, seed, .1, .05, False) for seed in TEST]))
            simultaneous = [item[3] for item in pool.map(_oracle_task, [(name, seed, .1, .05, True) for seed in DESIGN])]
        c, sim, initial, _ = training[0]
        ids = c.line_ids
        tables = [x[3] for x in training]
        flow_score = {i: np.mean([abs(t[2].flow[i-1]) for t in training]) for i in ids}
        flow = sorted(ids, key=lambda i: (-flow_score[i], i))
        centrality = nx.edge_betweenness_centrality(sim.graph())
        centrality_score = {key[2]: value for key, value in centrality.items()}
        between = sorted(ids, key=lambda i: (-centrality_score[i], i))
        random_orders = [np.random.default_rng(7000 + j).permutation(ids).tolist() for j in range(20)]
        selected = {}
        for budget in range(4):
            robust, history = robust_protection(tables, ids, budget)
            single, _ = robust_protection(tables[:1], ids, budget)
            std, _ = robust_protection(simultaneous, ids, budget)
            policies = {"robust-sequential": robust, "single-scenario": single,
                        "simultaneous-design": std, "initial-flow": tuple(flow[:budget]),
                        "betweenness": tuple(between[:budget])}
            if budget <= 2:
                exact = exact_protection(tables, ids, budget)
                policies["exact-design"] = exact
            for j, order in enumerate(random_orders):
                policies[f"random-{j:02d}"] = tuple(order[:budget])
            selected[budget] = robust
            designs.append({"case": name, "budget": budget, "policies": policies,
                            "robust_history": history,
                            "robust_design_objective": defense_objective(tables, robust),
                            "exact_design_objective": defense_objective(tables, policies["exact-design"])
                            if "exact-design" in policies else None})
            for split, scenarios in (("design", training), ("test", testing)):
                for case, _, _, table in scenarios:
                    baseline = table.worst()[0]
                    for policy, protected in policies.items():
                        value, sequence = table.worst(protected)
                        rows.append({"case": name, "seed": case.scenario_seed, "split": split,
                                     "budget": budget, "policy": policy, "protected": list(protected),
                                     "adaptive_sequence": list(sequence), "shed_mw": value,
                                     "shed_fraction": value / case.total_demand_mw,
                                     "no_defense_shed_mw": baseline, "reduction_mw": baseline - value,
                                     "reduction_pp": 100 * (baseline - value) / case.total_demand_mw,
                                     "oracle": "all ordered k=2 sequences", "max_residual_pu": table.max_residual_pu})
            write_csv(OUT / "protection.csv", rows)
            write_json(OUT / "defense_designs.json", designs)
        # Freeze design choices before stress testing new demand and ramp settings.
        stress_settings = [(name, seed, ramp, perturb, False) for ramp in (.025, .1, .5)
                           for perturb in (0., .15) for seed in TEST[:2]]
        with ProcessPoolExecutor(max_workers=3) as pool:
                for settings, outcome in zip(stress_settings, pool.map(_stress_oracle_task, stress_settings)):
                    _, seed, ramp, perturb, _ = settings
                    if outcome[0] == "infeasible_initial":
                        stress_failures.append({"case": name, "seed": seed, "ramp": ramp,
                                                "perturb": perturb, "status": outcome[0], "error": outcome[1]})
                        for budget in (1, 2):
                            for policy in ("robust-sequential", "initial-flow", "none"):
                                sensitivity.append({"case": name, "seed": seed, "ramp": ramp,
                                                    "perturb": perturb, "budget": budget, "policy": policy,
                                                    "status": outcome[0], "error": outcome[1]})
                        write_json(OUT / "stress_initial_failures.json", stress_failures)
                        write_csv(OUT / "protection_sensitivity.csv", sensitivity)
                        print(outcome[1], flush=True)
                        continue
                    result = outcome[1]
                    case, _, _, table = result
                    for budget in (1, 2):
                        for policy, protected in (("robust-sequential", selected[budget]),
                                                  ("initial-flow", flow[:budget]), ("none", ())):
                            value, sequence = table.worst(protected)
                            sensitivity.append({"case": name, "seed": seed, "ramp": ramp, "perturb": perturb,
                                                "budget": budget, "policy": policy, "protected": list(protected),
                                                "status": "ok",
                                                "shed_mw": value, "shed_fraction": value / case.total_demand_mw,
                                                "adaptive_sequence": list(sequence), "max_residual_pu": table.max_residual_pu})
                    write_csv(OUT / "protection_sensitivity.csv", sensitivity)
        # Demonstrate a held-out adaptive response after protection, independent of design seeds.
        case, test_sim, test_initial, table = testing[0]
        _, seq = table.worst(selected[1])
        evaluator = Evaluator(test_sim, test_initial, selected[1])
        sequence_viewer(OUT / f"demo_protection_{name}.html", case, evaluator.trace(seq), seq,
                        f"Held-out case {name}: protected {selected[1]}, exhaustive adaptive failure sequence")
    return rows, sensitivity, designs


def _oracle_task(settings):
    name, seed, ramp, perturb, simultaneous = settings
    return oracle(name, seed, ramp=ramp, perturb=perturb, simultaneous=simultaneous)


def _stress_oracle_task(settings):
    try:
        return "ok", _oracle_task(settings)
    except InitialScenarioInfeasible as exc:
        return "infeasible_initial", str(exc)


def timing_study():
    rows = []
    # All patterns sum to three reference epochs; rescale for horizon sensitivity.
    patterns = {"even": (1, 1, 1), "early-cluster": (.2, .2, 2.6), "late-cluster": (2.6, .2, .2)}
    for name in ("14", "39", "118"):
        for seed in DESIGN:
            case = load_case(name).scenario(seed)
            sim = GridSimulator(case, .1)
            initial = sim.initialize()
            evaluator = Evaluator(sim, initial)
            guided = search(evaluator, "sequin", 3, breadth=3)
            flow = search(Evaluator(sim, initial), "greedy-flow", 3, breadth=3)
            # Freeze a diverse common order cohort across timing/response policies.
            cohort = sorted(set(permutations(guided.sequence)) | set(permutations(flow.sequence)))
            for horizon in (7.5, 15., 30.):
                for label, pattern in patterns.items():
                    durations = np.asarray(pattern) * horizon / 3
                    for sequence in cohort:
                        for simultaneous in (False, True):
                            result, states = timed_trace(sim, initial, sequence, durations,
                                                         simultaneous=simultaneous)
                            rows.append({"case": name, "seed": seed, "pattern": label,
                                         "horizon_minutes": horizon, "sequence": list(sequence),
                                         "simultaneous": simultaneous,
                                         "final_shed_mw": result["final_shed_mw"],
                                         "shed_fraction": result["final_shed_mw"] / case.total_demand_mw,
                                         "snapshot_energy_mwh": result["snapshot_unserved_energy_mwh"],
                                         "energy_fraction": result["snapshot_unserved_energy_mwh"] /
                                         (case.total_demand_mw * horizon / 60),
                                         "max_residual_pu": result["max_residual_pu"]})
                            if name == "39" and seed == 0 and horizon == 15 and label == "early-cluster" and tuple(sequence) == guided.sequence and not simultaneous:
                                write_json(OUT / "demo_timing" / "timing.json", {"scenario": case.metadata(), "result": result,
                                           "trace": [s.to_dict(case) for s in states]})
                                sequence_viewer(OUT / "demo_timing" / "viewer.html", case, states, sequence,
                                                "Case 39: early-cluster timing, 15 minute snapshot proxy")
            write_csv(OUT / "timing.csv", rows)
            print(f"timing case={name} seed={seed}: {len(cohort)} common orderings", flush=True)
    return rows


def priority_study(case_names=("14", "39", "118"), seeds=DESIGN, checkpoint=None):
    rows, groups = [], []
    row_path = OUT / (f"checkpoints/priority_{checkpoint}.csv" if checkpoint else "priority.csv")
    group_path = OUT / (f"checkpoints/critical_groups_{checkpoint}.json" if checkpoint else "critical_groups.json")
    for name in case_names:
        for seed in seeds:
            case = load_case(name).scenario(seed)
            initial = GridSimulator(case).initialize()
            for fraction in (.1, .25, .5):
                critical = critical_loads(case, fraction, seed=17)
                groups.append({"case": name, "seed": seed, "critical_bus_fraction": fraction,
                               "bus_ids": case.bus_ids[list(critical)].tolist(),
                               "critical_demand_mw": float(case.demand[list(critical)].sum() * case.base_mva)})
                for ramp in (.025, .1, .5):
                    if fraction != .25 and ramp != .1:
                        continue  # Main ramp sweep plus group-size sensitivity at nominal ramp.
                    simulators, cohort, evaluator_by_policy = {}, set(), {}
                    for policy in ("total", "weight-2", "weight-10", "critical-first"):
                        weights = np.ones(case.nbus)
                        if policy.startswith("weight"):
                            weights[list(critical)] = float(policy.split("-")[1])
                        sim = GridSimulator(case, ramp, service_weights=weights,
                                            critical_buses=critical if policy == "critical-first" else ())
                        simulators[policy] = sim
                        e = Evaluator(sim, initial)
                        evaluator_by_policy[policy] = e
                        if name == "14":
                            result = search(e, "enum", 2)
                            cohort.update(result.sequences)
                        else:
                            methods = ("sequin", "sequin-release", "greedy-flow") if policy == "total" else ("sequin",)
                            for method in methods:
                                result = search(e, method, 2, breadth=2)
                                cohort.update(result.sequences)
                    # Every policy sees the UNION of all policies' discovered sequences.
                    for policy, sim in simulators.items():
                        e = evaluator_by_policy[policy]
                        for sequence in sorted(cohort):
                            state = e.evaluate(sequence)
                            rows.append({"case": name, "seed": seed, "critical_bus_fraction": fraction,
                                         "ramp": ramp, "policy": policy, "sequence": list(sequence),
                                         "cohort_size": len(cohort), "exhaustive": name == "14",
                                         "max_residual_pu": state.max_residual_pu,
                                         "service_floor_tolerance_pu": state.service_floor_tolerance_pu,
                                         **service_metrics(case, state, critical)})
                        if name == "39" and seed == 0 and fraction == .25 and ramp == .1 and policy == "critical-first":
                            worst = max(cohort, key=lambda s: service_metrics(case, e.evaluate(s), critical)["critical_shed_mw"])
                            sequence_viewer(OUT / "demo_critical" / "viewer.html", case, e.trace(worst), worst,
                                            f"Critical service first: SYNTHETIC priority buses {case.bus_ids[list(critical)].tolist()}")
                            write_json(OUT / "demo_critical" / "result.json", {"scenario": case.metadata(),
                                       "critical_bus_ids": case.bus_ids[list(critical)].tolist(),
                                       "sequence": list(worst), "metrics": service_metrics(case, e.evaluate(worst), critical),
                                       "trace": [s.to_dict(case) for s in e.trace(worst)]})
                    print(f"priority case={name} seed={seed} fraction={fraction} ramp={ramp}: {len(cohort)} shared sequences", flush=True)
                    write_csv(row_path, rows)
                    write_json(group_path, groups)
    return rows, groups


def _priority_task(settings):
    name, seed = settings
    key = f"{name}_{seed}_{fingerprint()[:12]}"
    row_path = OUT / f"checkpoints/priority_{key}.csv"
    group_path = OUT / f"checkpoints/critical_groups_{key}.json"
    if row_path.exists() and group_path.exists():
        import csv
        with row_path.open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        cells = {(r["critical_bus_fraction"], r["ramp"]) for r in rows}
        if len(cells) == 5:
            print(f"priority cached case={name} seed={seed}", flush=True)
            return rows, json.loads(group_path.read_text())
    return priority_study((name,), (seed,), checkpoint=key)


def priority_parallel():
    rows, groups = [], []
    with ProcessPoolExecutor(max_workers=3) as pool:
        for new_rows, new_groups in pool.map(_priority_task, [(name, seed) for name in ("14", "39", "118") for seed in DESIGN]):
            rows.extend(new_rows)
            groups.extend(new_groups)
            write_csv(OUT / "priority.csv", rows)
            write_json(OUT / "critical_groups.json", groups)
    return rows, groups


def grouped(rows, keys):
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row[k] for k in keys)].append(row)
    return groups


def bootstrap_mean_ci(values):
    values = np.asarray(values, float)
    means = np.random.default_rng(2026).choice(values, size=(5000, len(values)), replace=True).mean(axis=1)
    return np.quantile(means, (.025, .975)).tolist()


def analyze(protection, sensitivity, timing, priority, designs):
    summary = {"protection": [], "timing": [], "priority": [], "paired_priority": []}
    # Random draws are averaged WITHIN seed; they are not independent demand samples.
    collapsed = []
    for key, rs in grouped([r for r in protection if r["split"] == "test"], ("case", "budget", "seed")).items():
        for policy, ps in grouped(rs, ("policy",)).items():
            if not policy[0].startswith("random"):
                collapsed.extend(ps)
        random = [r for r in rs if r["policy"].startswith("random")]
        collapsed.append({**random[0], "policy": "random-mean",
                          **{k: float(np.mean([r[k] for r in random])) for k in ("shed_fraction", "reduction_mw", "reduction_pp")}})
    for key, rs in grouped(collapsed, ("case", "budget", "policy")).items():
        changes = [r["reduction_pp"] for r in rs]
        summary["protection"].append({"case": key[0], "budget": key[1], "policy": key[2], "n_test_seeds": len(rs),
            "mean_shed_fraction": float(np.mean([r["shed_fraction"] for r in rs])),
            "worst_shed_fraction": max(r["shed_fraction"] for r in rs),
            "mean_reduction_mw": float(np.mean([r["reduction_mw"] for r in rs])),
            "mean_reduction_pp": float(np.mean(changes)), "paired_bootstrap_95ci_pp": bootstrap_mean_ci(changes)})
    for key, rs in grouped(timing, ("case", "seed", "horizon_minutes", "pattern", "simultaneous")).items():
        summary["timing"].append(dict(zip(("case", "seed", "horizon_minutes", "pattern", "simultaneous"), key)) |
                                 {"cohort_max_final_fraction": max(r["shed_fraction"] for r in rs),
                                  "cohort_max_energy_fraction": max(r["energy_fraction"] for r in rs)})
    for key, rs in grouped(priority, ("case", "seed", "critical_bus_fraction", "ramp", "policy")).items():
        summary["priority"].append(dict(zip(("case", "seed", "critical_bus_fraction", "ramp", "policy"), key)) |
            {"worst_critical_retained_fraction": min(r["critical_retained_fraction"] for r in rs),
             "worst_total_shed_mw": max(r["shed_mw"] for r in rs), "cohort_size": rs[0]["cohort_size"],
             "exhaustive": rs[0]["exhaustive"]})
    for key, rs in grouped(priority, ("case", "seed", "critical_bus_fraction", "ramp", "sequence")).items():
        policies = {r["policy"]: r for r in rs}
        for policy in ("weight-2", "weight-10", "critical-first"):
            base, alternative = policies["total"], policies[policy]
            summary["paired_priority"].append(dict(zip(("case", "seed", "critical_bus_fraction", "ramp", "sequence"), key)) |
                {"policy": policy, "critical_gain_mw": base["critical_shed_mw"] - alternative["critical_shed_mw"],
                 "total_extra_shed_mw": alternative["shed_mw"] - base["shed_mw"]})
    write_json(OUT / "summary.json", summary)
    write_csv(OUT / "protection_summary.csv", summary["protection"])
    write_csv(OUT / "priority_summary.csv", summary["priority"])
    return summary


def plots(summary, sensitivity):
    sensitivity = [r for r in sensitivity if r.get("status", "ok") == "ok"]
    os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".mplconfig"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    for ax, name in zip(axes, ("14", "39")):
        for policy in ("robust-sequential", "single-scenario", "simultaneous-design", "initial-flow", "betweenness", "random-mean", "exact-design"):
            rs = sorted([r for r in summary["protection"] if r["case"] == name and r["policy"] == policy], key=lambda r: r["budget"])
            ax.plot([r["budget"] for r in rs], [r["mean_shed_fraction"] * 100 for r in rs], marker="o", label=policy)
        ax.set(title=f"Case {name}: five held-out demand seeds, exact k=2 outages", xlabel="Protected lines", ylabel="Mean final demand shed (%)", xticks=range(4))
        ax.grid(alpha=.2)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, fontsize=9)
    fig.tight_layout(rect=(0, .15, 1, 1))
    fig.savefig(OUT / "protection.png", dpi=160)
    plt.close(fig)
    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    for col, name in enumerate(("14", "39", "118")):
        for simultaneous, style in ((False, "-"), (True, "--")):
            for horizon in (7.5, 15., 30.):
                patterns = ("even", "early-cluster", "late-cluster")
                values = [[r for r in summary["timing"] if r["case"] == name and r["pattern"] == p and r["simultaneous"] == simultaneous and r["horizon_minutes"] == horizon] for p in patterns]
                for ax, metric in ((axes[0, col], "cohort_max_final_fraction"), (axes[1, col], "cohort_max_energy_fraction")):
                    ax.plot(range(3), [100*np.mean([r[metric] for r in rs]) for rs in values], style, marker="o",
                            label=f"{'simultaneous' if simultaneous else 'sequential'}, {horizon:g} min")
                    ax.set(xticks=range(3), xticklabels=("Even", "Early", "Late"))
                    ax.grid(alpha=.2)
        axes[0, col].set_title(f"Case {name}: common ordering cohort")
        axes[0, col].set_ylabel("Worst-found final shed (%)")
        axes[1, col].set_ylabel("Worst-found snapshot energy loss (%)")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3)
    fig.tight_layout(rect=(0, .1, 1, 1))
    fig.savefig(OUT / "timing.png", dpi=160)
    plt.close(fig)
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.7))
    for ax, name in zip(axes, ("14", "39", "118")):
        for policy in ("total", "weight-2", "weight-10", "critical-first"):
            xs = (.025, .1, .5)
            values = [[r["worst_critical_retained_fraction"] for r in summary["priority"] if r["case"] == name and r["critical_bus_fraction"] == .25 and r["policy"] == policy and r["ramp"] == x] for x in xs]
            ax.plot(xs, [100*np.mean(v) for v in values], marker="o", label=policy)
        ax.set(title=f"Case {name}: synthetic 25% load-bus group", xlabel="Ramp fraction per epoch", ylabel="Worst-found critical demand retained (%)")
        ax.grid(alpha=.2)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4)
    fig.tight_layout(rect=(0, .1, 1, 1))
    fig.savefig(OUT / "priority.png", dpi=160)
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for ax, name in zip(axes, ("14", "39")):
        for policy in ("none", "initial-flow", "robust-sequential"):
            for perturb, style in ((0., "-"), (.15, "--")):
                xs = (.025, .1, .5)
                ys = [np.mean([r["shed_fraction"] for r in sensitivity if r["case"] == name and r["budget"] == 2 and r["policy"] == policy and r["ramp"] == x and r["perturb"] == perturb]) * 100 for x in xs]
                ax.plot(xs, ys, style, marker="o", label=f"{policy}, demand +/-{perturb*100:g}%")
        counts = [len({r["seed"] for r in sensitivity if r["case"] == name and r["perturb"] == p}) for p in (0., .15)]
        ax.set(title=f"Case {name}: frozen design, budget=2\nFeasible seeds: 0%={counts[0]}, +/-15%={counts[1]}",
               xlabel="Test ramp fraction", ylabel="Mean final demand shed (%)")
        ax.grid(alpha=.2)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, fontsize=9)
    fig.tight_layout(rect=(0, .15, 1, 1))
    fig.savefig(OUT / "sensitivity.png", dpi=160)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("all", "protection", "timing", "priority", "report"), default="all")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    start = perf_counter()
    if args.phase in ("all", "protection"):
        protection_study()
    if args.phase in ("all", "timing"):
        timing_study()
    if args.phase in ("all", "priority"):
        priority_parallel()
    if args.phase in ("all", "report"):
        import csv
        def read(name):
            result = []
            with (OUT / name).open(encoding="utf-8", newline="") as f:
                for row in csv.DictReader(f):
                    parsed = {}
                    for key, value in row.items():
                        if key in ("case", "policy", "split", "oracle", "pattern"):
                            parsed[key] = value
                            continue
                        try:
                            parsed[key] = json.loads(value)
                        except (ValueError, TypeError):
                            parsed[key] = {"True": True, "False": False}.get(value, value)
                    # Tuples are hashable keys for paired comparisons.
                    if "sequence" in parsed:
                        parsed["sequence"] = tuple(parsed["sequence"])
                    result.append(parsed)
            return result
        p, s, t, c = [read(n) for n in ("protection.csv", "protection_sensitivity.csv", "timing.csv", "priority.csv")]
        valid_s = [r for r in s if r.get("status", "ok") == "ok"]
        designs = json.loads((OUT / "defense_designs.json").read_text())
        summary = analyze(p, s, t, c, designs)
        plots(summary, s)
        write_json(OUT / "run_manifest.json", {"environment": environment(), "source_sha256": fingerprint(),
                   "design_seeds": DESIGN, "heldout_seeds": TEST, "protection_rows": len(p),
                   "sensitivity_rows": len(s), "sensitivity_success_rows": len(valid_s),
                   "sensitivity_initial_infeasible_rows": len(s) - len(valid_s),
                   "timing_rows": len(t), "priority_rows": len(c),
                   "max_residual_pu": max(r["max_residual_pu"] for r in p+valid_s+t+c),
                   "max_priority_service_floor_tolerance_pu": max(r["service_floor_tolerance_pu"] for r in c),
                   "oracle_source_fingerprints": sorted({json.loads(str(np.load(file, allow_pickle=False)["metadata"]))["source"] for file in (OUT / "oracles").glob("*.npz")}),
                   "statistical_unit": "demand scenario, not outage sequence or random-defense draw",
                   "duration_this_invocation_seconds": perf_counter() - start})
    print(f"Completed phase {args.phase}: {OUT}", flush=True)


if __name__ == "__main__":
    main()
