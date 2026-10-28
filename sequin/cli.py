"""Reproducible command-line entry points; all output stays in the chosen folder."""

import argparse
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from itertools import permutations
from math import factorial
import platform
import sys
from time import perf_counter

import numpy as np

from .case import load_case
from .defense import plan_protection
from .extensions import timed_trace, service_metrics
from .physics import GridSimulator, SolverError
from .report import write_json, write_csv, comparison_plot, sequence_viewer, order_plot
from .search import Evaluator, SearchLimitError, search, prefix_tree


def _csv(text, convert=str):
    return [convert(x.strip()) for x in text.split(",") if x.strip()]


def environment():
    return {"python": sys.version, "platform": platform.platform(),
            "packages": {p: version(p) for p in ("numpy", "scipy", "highspy", "networkx", "matplotlib")},
            "created_utc": datetime.now(timezone.utc).isoformat()}


def prepare(args, case_name=None, seed=None, ramp=None):
    case = load_case(case_name or args.case).scenario(args.seed if seed is None else seed, args.perturb)
    bus_ids = _csv(args.critical_buses, int)
    if not set(bus_ids).issubset(set(case.bus_ids)):
        raise ValueError("Unknown critical bus ID")
    critical = [i for i, bus in enumerate(case.bus_ids) if bus in bus_ids]
    if (args.critical_first or args.priority_weight != 1) and not critical:
        raise ValueError("Choose --critical-buses for a service priority policy")
    weights = np.ones(case.nbus)
    weights[critical] = args.priority_weight
    sim = GridSimulator(case, args.ramp if ramp is None else ramp, tie_break=args.tie_break,
                        mip_gap=args.mip_gap, time_limit=args.solver_timeout,
                        service_weights=weights, critical_buses=critical if args.critical_first else ())
    sim.priority_group = tuple(critical)
    return case, sim, sim.initialize()


def run(args):
    case, sim, initial = prepare(args)
    evaluator = Evaluator(sim, initial)
    result = search(evaluator, args.method, args.k, breadth=args.breadth, max_sequences=args.max_sequences)
    out = Path(args.output)
    payload = {"environment": environment(), "scenario": case.metadata(), "settings": vars(args),
               "result": result.summary(), "initial": initial.to_dict(case),
               "final": result.state.to_dict(case)}
    if sim.priority_group:
        payload["service_metrics"] = service_metrics(case, result.state, sim.priority_group)
    payload["settings"] = {k: v for k, v in payload["settings"].items() if k != "handler"}
    if not result.simultaneous:
        trace = evaluator.trace(result.sequence)
        payload["trace"] = [s.to_dict(case) for s in trace]
        write_json(out / "prefix_tree.json", prefix_tree(evaluator, result.sequences))
        sequence_viewer(out / "viewer.html", case, trace, result.sequence,
                        f"SEQUIN · {case.name} · {args.method}")
    write_json(out / "result.json", payload)
    print(f"{args.method}: sequence {result.sequence}, shed {result.state.shed_mw:.3f} MW, "
          f"{result.seconds:.2f}s; results: {out.resolve()}")


def simulate(args):
    case, sim, initial = prepare(args)
    sequence = tuple(_csv(args.sequence, int))
    if not sequence:
        raise ValueError("Specify at least one line in --sequence")
    multipliers = _csv(args.interval_multipliers, float) if args.interval_multipliers else [1.0] * len(sequence)
    if len(multipliers) != len(sequence) or any(not np.isfinite(t) or t <= 0 for t in multipliers):
        raise ValueError("Use one positive interval multiplier per failure")
    trace = [initial]
    for line, multiplier in zip(sequence, multipliers):
        trace.append(sim.respond(trace[-1], [line], ramp_fraction=args.ramp * multiplier))
    out = Path(args.output)
    write_json(out / "trace.json", {"environment": environment(), "scenario": case.metadata(),
               "settings": {k: v for k, v in vars(args).items() if k != "handler"},
               "ramp_fraction": args.ramp, "interval_multipliers": multipliers,
               "timing_semantics": "Multiplier scales redispatch allowance after the current failure; not physical seconds",
               "service_metrics": service_metrics(case, trace[-1], sim.priority_group) if sim.priority_group else None,
               "trace": [s.to_dict(case) for s in trace]})
    sequence_viewer(out / "viewer.html", case, trace, sequence)
    print(f"Sequence {sequence}: final shed {trace[-1].shed_mw:.3f} MW; {out.resolve()}")


def benchmark(args):
    out = Path(args.output)
    rows, manifest = [], []
    failures = 0
    for case_name in _csv(args.cases):
        for seed in _csv(args.seeds, int):
            # Freeze the sampled demand AND initial dispatch once for all methods/ramp values.
            case, initial_sim, initial = prepare(args, case_name, seed)
            manifest.append({**case.metadata(), "initial": initial.to_dict(case)})
            for ramp in _csv(args.ramps, float):
                for k in _csv(args.ks, int):
                    for method in _csv(args.methods):
                        row = {"case": case.name, "seed": seed, "k": k, "ramp_fraction": ramp,
                               "method": method, "demand_mw": case.total_demand_mw}
                        try:
                            sim = GridSimulator(case, ramp, tie_break=args.tie_break,
                                                mip_gap=args.mip_gap, time_limit=args.solver_timeout,
                                                service_weights=initial_sim.service_weights,
                                                critical_buses=initial_sim.critical_buses)
                            evaluator = Evaluator(sim, initial)
                            result = search(evaluator, method, k, breadth=args.breadth,
                                            max_sequences=args.max_sequences)
                            row.update(result.summary())
                            row.update(status="ok", shed_fraction=result.state.shed_mw / case.total_demand_mw)
                            if initial_sim.priority_group:
                                row.update(service_metrics(case, result.state, initial_sim.priority_group))
                        except SearchLimitError as exc:
                            row.update(status="skipped_limit", error=str(exc))
                        except (ValueError, SolverError) as exc:
                            row.update(status="error", error=str(exc))
                            failures += 1
                        rows.append(row)
                        print(f"{case_name} seed={seed} ramp={ramp:g} k={k} {method}: "
                              f"{row.get('shed_mw', row.get('error'))}", flush=True)
                        write_csv(out / "results.csv", rows)
    write_json(out / "results.json", {"environment": environment(), "scenarios": manifest,
               "settings": {k: v for k, v in vars(args).items() if k != "handler"}, "results": rows,
               "scope": "Independent implementation; not a numerical reproduction claim for the Julia artifact"})
    comparison_plot(rows, out / "comparison.png")
    successful = sum(r["status"] == "ok" for r in rows)
    lines = ["# Measured benchmark results", "", f"Successful runs: {successful}/{len(rows)}. Errors: {failures}.", "",
             "All methods within a case/seed share identical sampled demand and initial dispatch.",
             "Each search starts with a fresh prefix cache. Initialization is excluded from search time.",
             "Exhaustive methods are exact only over outage choices under this deterministic response policy.", "",
             "| Case | Seed | Ramp | k | Method | Shed MW | Time s | Status |",
             "|---|---:|---:|---:|---|---:|---:|---|"]
    for r in rows:
        lines.append(f"| {r['case']} | {r['seed']} | {r['ramp_fraction']} | {r['k']} | {r['method']} | "
                     f"{r.get('shed_mw', '')} | {r.get('seconds', '')} | {r['status']} |")
    (out / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved {successful} successful runs to {out.resolve()}")
    return 1 if failures else 0


def protect(args):
    case, sim, initial = prepare(args)
    start = perf_counter()
    result = plan_protection(sim, initial, k=args.k, budget=args.budget,
                            method=args.method, breadth=args.breadth, max_sequences=args.max_sequences)
    rng = np.random.default_rng(args.seed)
    policies = {"random": tuple(sorted(rng.choice(case.line_ids, args.budget, replace=False).tolist())),
                "initial-flow": tuple(sorted(sorted(case.line_ids,
                    key=lambda i: (-abs(initial.flow[i - 1]), i))[:args.budget]))}
    baselines = {}
    for name, protected in policies.items():
        trial = search(Evaluator(sim, initial, protected), args.method, args.k,
                       breadth=args.breadth, max_sequences=args.max_sequences)
        baselines[name] = {"protected_lines": list(protected), "shed_mw": trial.state.shed_mw,
                           "adaptive_sequence": list(trial.sequence)}
    out = Path(args.output)
    payload = {"environment": environment(), "scenario": case.metadata(),
               "settings": {k: v for k, v in vars(args).items() if k != "handler"},
               "result": result.to_dict(), "baselines": baselines}
    final_sequence = result.adaptive_sequence
    if args.verify_exact:
        verification = search(Evaluator(sim, initial, result.protected), "enum", args.k,
                              max_sequences=args.max_sequences)
        payload["independent_validation"] = {"method": "exhaustive ordered sequences under the same response policy",
                                              "result": verification.summary()}
        final_sequence = verification.sequence
    payload["seconds"] = perf_counter() - start
    write_json(out / "protection.json", payload)
    evaluator = Evaluator(sim, initial, result.protected)
    trace = evaluator.trace(final_sequence)
    sequence_viewer(out / "viewer.html", case, trace, final_sequence,
                    "Adaptive outages after budgeted protection")
    print(f"Protected {result.protected}: {result.baseline_shed_mw:.3f} -> "
          f"{result.remaining_shed_mw:.3f} MW worst-found shed; {out.resolve()}")


def order_study(args):
    case, sim, initial = prepare(args)
    lines = tuple(_csv(args.sequence, int))
    if not lines or len(set(lines)) != len(lines):
        raise ValueError("Use distinct line IDs for the order study")
    if factorial(len(lines)) > args.max_sequences:
        raise SearchLimitError("Too many permutations for the configured limit")
    evaluator = Evaluator(sim, initial)
    simultaneous = evaluator.simultaneous(lines)
    rows = [{"sequence": list(sequence), "shed_mw": evaluator.evaluate(sequence).shed_mw}
            for sequence in permutations(lines)]
    out = Path(args.output)
    write_csv(out / "order_effect.csv", rows)
    write_json(out / "order_effect.json", {"environment": environment(), "scenario": case.metadata(),
               "ramp_fraction": args.ramp, "tie_break": args.tie_break, "lines": list(lines),
               "simultaneous_shed_mw": simultaneous.shed_mw, "orderings": rows,
               "comparison_limit": "Single simultaneous response and multiple sequential responses allow different redispatch opportunities"})
    order_plot(rows, simultaneous.shed_mw, out / "order_effect.png")
    print(f"{len(rows)} orderings: {min(r['shed_mw'] for r in rows):.3f} to "
          f"{max(r['shed_mw'] for r in rows):.3f} MW shed; simultaneous {simultaneous.shed_mw:.3f} MW")


def timing(args):
    case, sim, initial = prepare(args)
    result, states = timed_trace(sim, initial, _csv(args.sequence, int),
                                _csv(args.durations_minutes, float),
                                reference_minutes=args.reference_minutes,
                                simultaneous=args.simultaneous)
    out = Path(args.output)
    write_json(out / "timing.json", {"environment": environment(), "scenario": case.metadata(),
               "settings": {k: v for k, v in vars(args).items() if k != "handler"},
               "result": result, "trace": [s.to_dict(case) for s in states]})
    sequence_viewer(out / "viewer.html", case, states, tuple(_csv(args.sequence, int)),
                    "Variable response windows: snapshot energy proxy")
    print(f"{result['horizon_minutes']:g} min: {result['final_shed_mw']:.3f} MW final shed; "
          f"{result['snapshot_unserved_energy_mwh']:.3f} MWh snapshot proxy; {out.resolve()}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="SEQUIN: public-benchmark sequential DC grid analysis")
    subs = parser.add_subparsers(dest="command", required=True)
    for name, handler in (("run", run), ("simulate", simulate), ("benchmark", benchmark),
                          ("protect", protect), ("order-study", order_study), ("timing", timing)):
        p = subs.add_parser(name)
        p.set_defaults(handler=handler)
        p.add_argument("--case", default="14", help="14,39,60,118,162,240 or a MATPOWER file")
        p.add_argument("--seed", type=int, default=0)
        p.add_argument("--perturb", type=float, default=0.05)
        p.add_argument("--ramp", type=float, default=0.1)
        p.add_argument("--tie-break", choices=("cost", "none"), default="cost")
        p.add_argument("--mip-gap", type=float, default=1e-8)
        p.add_argument("--solver-timeout", type=float, default=60)
        p.add_argument("--output", default=f"output/{name}")
        p.add_argument("--critical-buses", default="", help="Synthetic priority group: original MATPOWER bus IDs")
        p.add_argument("--priority-weight", type=float, default=1, help="Positive service weight for critical buses")
        p.add_argument("--critical-first", action="store_true", help="Lexicographic critical service before weighted total service")
        if name not in ("simulate", "timing"):
            p.add_argument("-k", type=int, default=2)
            p.add_argument("--method", default="sequin")
            p.add_argument("--breadth", type=int, default=5)
            p.add_argument("--max-sequences", type=int, default=50_000)
        if name == "simulate":
            p.add_argument("--sequence", required=True, help="One-based MATPOWER line IDs, comma separated")
            p.add_argument("--interval-multipliers", help="Relative response intervals, one per failure")
        if name == "timing":
            p.add_argument("--sequence", required=True)
            p.add_argument("--durations-minutes", required=True, help="One response/observation window per event")
            p.add_argument("--reference-minutes", type=float, default=5)
            p.add_argument("--simultaneous", action="store_true", help="Fail all selected lines in first window; redispatch in every window")
        if name == "order-study":
            p.add_argument("--sequence", required=True, help="A fixed set of line IDs to permute")
        if name == "benchmark":
            p.add_argument("--cases", default="14,39,118")
            p.add_argument("--seeds", default="0,1,2")
            p.add_argument("--ks", default="2,3")
            p.add_argument("--ramps", default="0.1")
            p.add_argument("--methods", default="sequin,sequin-release,greedy-flow,greedy-shed,greedy-crit")
        if name == "protect":
            p.add_argument("--budget", type=int, default=1)
            p.add_argument("--verify-exact", action="store_true", help="Exhaustively recheck selected protection on small cases")
    args = parser.parse_args(argv)
    try:
        return args.handler(args) or 0
    except (ValueError, OSError, SolverError) as exc:
        parser.exit(2, f"Error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
