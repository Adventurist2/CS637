"""Build the readable second-part report and paired demonstration from measured data."""

from pathlib import Path
import csv
import html
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np

from sequin import GridSimulator, load_case
from sequin.extensions import critical_loads, service_metrics
from sequin.report import sequence_viewer, write_json
from sequin.search import Evaluator

OUT = ROOT / "output" / "part2"


def table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)] +
                     ["| " + " | ".join(str(x) for x in r) + " |" for r in rows])


def mean(rows, key):
    return float(np.mean([r[key] for r in rows]))


def paired_demo(summary):
    # Choose an explicitly labeled illustrative benefit, not an unbiased average.
    candidate = max((r for r in summary["paired_priority"] if r["policy"] == "critical-first"),
                    key=lambda r: r["critical_gain_mw"])
    case = load_case(candidate["case"]).scenario(candidate["seed"])
    critical = critical_loads(case, candidate["critical_bus_fraction"])
    initial = GridSimulator(case).initialize()
    sequence = tuple(candidate["sequence"])
    traces = {}
    for policy in ("total", "critical-first"):
        sim = GridSimulator(case, candidate["ramp"], critical_buses=critical if policy == "critical-first" else ())
        e = Evaluator(sim, initial)
        states = e.trace(sequence)
        sequence_viewer(OUT / "demo_critical" / f"{policy}.html", case, states, sequence,
                        f"{policy}: synthetic critical buses {case.bus_ids[list(critical)].tolist()}")
        traces[policy] = {"metrics": service_metrics(case, states[-1], critical),
                          "trace": [s.to_dict(case) for s in states]}
    payload = {"selection": "Largest observed paired critical-service gain; illustrative, not representative",
               "settings": candidate, "critical_bus_ids": case.bus_ids[list(critical)].tolist(),
               "scenario": case.metadata(), "policies": traces}
    write_json(OUT / "demo_critical" / "paired_comparison.json", payload)
    base = traces["total"]["metrics"]
    priority = traces["critical-first"]["metrics"]
    (OUT / "demo_critical" / "comparison.html").write_text(f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Critical service: paired comparison</title><style>body{{font:16px/1.6 system-ui;margin:24px;background:#edf2f5;color:#183347}}h1{{line-height:1.2}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:15px}}article{{background:white;padding:18px;border-radius:10px}}iframe{{width:100%;height:1000px;border:0}}strong{{color:#00635e}}@media(max-width:900px){{.grid{{grid-template-columns:1fr}}}}</style>
<h1>Same outages, different service priorities</h1><p>Illustrative largest observed gain: case {candidate['case']}, seed {candidate['seed']}, ramp {candidate['ramp']}, sequence {list(sequence)}. Synthetic critical buses: {case.bus_ids[list(critical)].tolist()}. This example is deliberately selected and is not a representative average.</p>
<div class="grid"><article><h2>Total-service baseline</h2><p>Critical shed: <strong>{base['critical_shed_mw']:.2f} MW</strong>; total shed: {base['shed_mw']:.2f} MW.</p><iframe title="Total-service trace" src="total.html"></iframe></article>
<article><h2>Critical-first operation</h2><p>Critical shed: <strong>{priority['critical_shed_mw']:.2f} MW</strong>; total shed: {priority['shed_mw']:.2f} MW.</p><iframe title="Critical-first trace" src="critical-first.html"></iframe></article></div><p>Step both viewers through the same sequence. These are myopic DC states with irreversible shedding, not transient dynamics.</p></html>''', encoding="utf-8")
    return payload


def html_from_markdown(source):
    """Small offline renderer for this generated report's limited Markdown."""
    import re
    def inline(text):
        text = html.escape(text)
        text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
        text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
        return text
    result, in_table, in_list = [], False, False
    for line in source.splitlines():
        if line.startswith("|"):
            if not in_table:
                result.append('<div class="scroll"><table>')
                in_table = True
            cells = [x.strip() for x in line.strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells):
                continue
            result.append("<tr>" + "".join("<td>"+inline(c)+"</td>" for c in cells) + "</tr>")
            continue
        if in_table:
            result.append("</table></div>")
            in_table = False
        if line.startswith("- "):
            if not in_list:
                result.append("<ul>")
                in_list = True
            result.append("<li>" + inline(line[2:]) + "</li>")
            continue
        if in_list:
            result.append("</ul>")
            in_list = False
        if line.startswith("!["):
            match = re.match(r"!\[([^]]*)\]\(([^)]+)\)", line)
            result.append(f'<figure><img alt="{html.escape(match[1])}" src="{html.escape(match[2])}"></figure>')
        elif line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            result.append(f"<h{level}>" + inline(line[level:].strip()) + f"</h{level}>")
        elif line.strip():
            result.append("<p>" + inline(line) + "</p>")
    if in_table:
        result.append("</table></div>")
    if in_list:
        result.append("</ul>")
    return "\n".join(result)


def main():
    summary = json.loads((OUT / "summary.json").read_text())
    manifest = json.loads((OUT / "run_manifest.json").read_text())
    designs = json.loads((OUT / "defense_designs.json").read_text())
    demo = paired_demo(summary)
    sections = ["# SEQUIN: second-part evaluation report", "",
        "Completed 27 October 2026. Scope: critique, three extensions, comparisons, sensitivity/robustness tests, demonstrations, measured conclusions and future work.", "",
        "## 1. What was already accomplished and what was missing", "",
        table(["Requirement", "Before this work", "Completed in this work"], [
            ["Critique / limitations", "Detailed source and modeling critique in notes/blueprint", "Paper-linked critique, implications and extension mapping"],
            ["2-3 implemented extensions", "One greedy protection prototype; timing multipliers; beam option", "Scenario-aware protection, variable timing, critical-load response"],
            ["Multiple baselines", "One protection example with random/flow controls", "Equal-budget random, flow, betweenness, simultaneous, single-scenario and exact designs; four service policies"],
            ["Sensitivity / robustness", "No complete extension study", "Held-out demand seeds; shifted demand/ramp; budgets; timing horizons; priority/group-size sensitivity"],
            ["Demonstration / explanation", "Generic sequence viewer", "Protection and timing traces; paired priority comparison; speaking guide"],
            ["Conclusions / future work", "Hypotheses, no consolidated extension findings", "Measured improvements, ties, failures, limits and future work"]]), "",
        "All 51 inherited tests passed before changes. New tests add exact-table equivalence, robust/outer-defense oracles, analytic priority service, timing accounting and a weighted-objective numerical regression. See the test record for the final suite result.", "",
        "Inherited first-part reproduction outputs are preserved and labeled separately. Native Julia/Gurobi search remains license-dependent according to the saved audit; it is not required by any extension here. Full fresh paper reproduction is not claimed.", "",
        "## 2. Critique and motivation", "",
        "SEQUIN makes a useful contribution by identifying order-sensitive outages with stateful DC operator response and guided network screening. Its model does not select preparedness investments, treats served MW uniformly, and uses fixed response epochs. Candidate screening is heuristic; a prefix range is not a certificate over unseen continuations. Irreversible shedding and myopic dispatch can lock in choices that are poor for future failures. DC steady states also omit AC voltages, reactive power, relay/frequency behavior and transient stability.", "",
        "These points motivate the three extensions below. Exact paper-page references, mathematical objectives, baseline definitions, sampling policies and novelty boundaries are in [the methods document](../../PART2_METHODS.md). Protection is already a topic in the broader literature; these are extensions relative to the selected SEQUIN workflow, not claims of entirely new research fields.", "",
        "## 3. Extension 1: scenario-aware budgeted protection", "",
        "Design on demand seeds 0/1/2; freeze decisions before testing seeds 100-104. Use cases 14/39, k=2, and budgets 0-3. Evaluate every eligible ordered pair exactly under the deterministic DC response policy, including an adaptive post-protection maximum. Greedy robust design minimizes the maximum design-scenario loss fraction; exact outer design verifies budgets 0-2. Twenty random defense orderings are averaged within each scenario, preserving demand scenario as the statistical unit.", "",
        "The table reports five-test-seed means. Reduction is in percentage points of original demand, relative to no protection on the same scenario. Bootstrap intervals are descriptive with only five seeds.", ""]
    ptable = []
    for name in ("14", "39"):
        for budget in (1, 2, 3):
            for policy in ("robust-sequential", "initial-flow", "betweenness", "random-mean", "single-scenario", "simultaneous-design", "exact-design"):
                rs = [r for r in summary["protection"] if r["case"] == name and r["budget"] == budget and r["policy"] == policy]
                if rs:
                    r = rs[0]
                    lo, hi = r["paired_bootstrap_95ci_pp"]
                    ptable.append([name, budget, policy, f"{100*r['mean_shed_fraction']:.2f}%",
                                   f"{r['mean_reduction_pp']:.2f}", f"[{lo:.2f}, {hi:.2f}]"])
    sections += [table(["Case", "Budget", "Policy", "Mean shed", "Reduction pp", "95% bootstrap interval pp"], ptable), "",
                 "![Protection across budgets](protection.png)", ""]
    for name in ("14", "39"):
        r = next(r for r in summary["protection"] if r["case"] == name and r["budget"] == 2 and r["policy"] == "robust-sequential")
        flow = next(r for r in summary["protection"] if r["case"] == name and r["budget"] == 2 and r["policy"] == "initial-flow")
        design = next(d for d in designs if d["case"] == name and d["budget"] == 2)
        gap = 100 * (design["robust_design_objective"][0] - design["exact_design_objective"][0])
        sections += [f"Case {name}, budget 2: robust design protects {design['policies']['robust-sequential']}, reduces held-out mean loss by {r['mean_reduction_pp']:.2f} percentage points ({r['mean_reduction_mw']:.2f} MW), versus {flow['mean_reduction_pp']:.2f} points for initial-flow protection. Its worst-design-scenario greedy gap to the exact outer optimum is {gap:.6f} percentage points.", ""]
    with (OUT / "protection_sensitivity.csv").open(newline="", encoding="utf-8") as f:
        stress = [r for r in csv.DictReader(f) if r.get("status", "ok") == "ok"]
    pairs = {}
    for row in stress:
        key = tuple(row[k] for k in ("case", "seed", "ramp", "perturb", "budget"))
        pairs.setdefault(key, {})[row["policy"]] = row
    losses = [(key, 100*(float(ps["robust-sequential"]["shed_fraction"]) - float(ps["initial-flow"]["shed_fraction"])))
              for key, ps in pairs.items()]
    worse = [(key, delta) for key, delta in losses if delta > 1e-4]
    worst = max(losses, key=lambda x: x[1])
    sections += ["### Stress test and negative result", "",
        f"With design choices frozen, robust protection is worse than initial-flow protection in {len(worse)} of {len(losses)} feasible paired stress cells (cells are not independent samples). The largest excess loss is {max(0,worst[1]):.2f} percentage points at case/seed/ramp/perturbation/budget = {worst[0]}. Scenario-aware design at one ramp setting does not establish robustness to changed operating flexibility. Separately, {manifest['sensitivity_initial_infeasible_rows']} requested stress policy rows have an infeasible fully served starting scenario; these are recorded explicitly and excluded from loss averages, without resampling or inventing a dispatch.", "",
        "![Protection stress sensitivity](sensitivity.png)", "",
        "## 4. Extension 2: variable timing with matched observation horizons", "",
        "Cases 14/39/118, three demand seeds, k=3, horizons 7.5/15/30 minutes, and even/early/late patterns. For each scenario, freeze the union of permutations of SEQUIN and flow-greedy outage sets. Both sequential and simultaneous comparators use the same windows, horizon and number of dispatch opportunities. The simultaneous set fails in the first window. Derived rates assume alpha=0.1 per five-minute reference epoch; they are experimental rates, not equipment measurements.", "",
        "**The MWh result is a snapshot unserved-energy proxy.** Each response receives its window's ramp allowance, and its endpoint shed is charged over that whole window: sum(shed MW * window minutes / 60). No continuous ramp trajectory or intra-window service is simulated. This is a bounded discrete extension, not exact physical energy not served. Final MW and the MWh proxy answer different questions.", ""]
    ttable = []
    for name in ("14", "39", "118"):
        for pattern in ("even", "early-cluster", "late-cluster"):
            for simultaneous in (False, True):
                rs = [r for r in summary["timing"] if r["case"] == name and r["horizon_minutes"] == 15 and r["pattern"] == pattern and r["simultaneous"] == simultaneous]
                ttable.append([name, pattern, "simultaneous" if simultaneous else "sequential",
                               f"{100*mean(rs,'cohort_max_final_fraction'):.2f}%",
                               f"{100*mean(rs,'cohort_max_energy_fraction'):.2f}%"])
    sections += [table(["Case", "15-minute pattern", "Comparator", "Mean cohort-worst final loss", "Mean cohort-worst snapshot energy loss"], ttable), "",
        "The final-loss maximum and energy-loss maximum can occur on different sequences. Values above average each scenario's cohort maximum across three seeds. Larger-case cohort maxima are not global worst-case certificates. Simultaneous and sequential event placement differs even after matching control opportunities; no universal ordering claim follows.", "",
        "![Timing and snapshot-energy sensitivity](timing.png)", "",
        "## 5. Extension 3: critical-service-aware response", "",
        "Groups are synthetic random subsets of positive-load buses, fixed with group seed 17 and exported as original bus IDs. Compare total MW service, critical weights 2 and 10, and lexicographic critical-first service. All policies start from the same economic dispatch. The main ramp sweep uses a 25% group; 10% and 50% groups test size/composition sensitivity at nominal ramp. Different-size groups need not be nested, and only one assignment per size is tested. Three demand seeds per case are used.", "",
        "Case 14 checks all 380 ordered pairs. Larger cases use a common union of sequences from three total-service searches plus SEQUIN under each priority policy (breadth 2); every policy is replayed on the full union. This is stronger than comparing separate policy-specific samples, but does not certify the worst critical-targeted attack in those larger networks.", ""]
    ctable = []
    for name in ("14", "39", "118"):
        for policy in ("total", "weight-2", "weight-10", "critical-first"):
            rs = [r for r in summary["priority"] if r["case"] == name and r["critical_bus_fraction"] == .25 and r["ramp"] == .1 and r["policy"] == policy]
            ctable.append([name, policy, f"{100*mean(rs,'worst_critical_retained_fraction'):.2f}%",
                           f"{mean(rs,'worst_total_shed_mw'):.2f}", "exact pairs" if name == "14" else "shared cohort"])
    sections += [table(["Case", "Policy", "Mean worst critical demand retained", "Mean worst total shed MW", "Coverage"], ctable), "",
                 "![Priority and ramp sensitivity](priority.png)", ""]
    for policy in ("weight-2", "weight-10", "critical-first"):
        rs = [r for r in summary["paired_priority"] if r["policy"] == policy]
        gains = sum(r["critical_gain_mw"] > 1e-3 for r in rs)
        regressions = sum(r["critical_gain_mw"] < -1e-3 for r in rs)
        extra = sum(r["total_extra_shed_mw"] > 1e-3 for r in rs)
        sections += [f"Across {len(rs):,} paired sequence/configuration rows, {policy} improves critical service in {gains:,}, worsens final critical service in {regressions:,}, and increases total shed in {extra:,}, using a 0.001 MW change threshold. These counts describe deterministic repeated evaluations, not independent statistical observations. Myopic priority choices are not a guarantee about later service.", ""]
    setting = demo["settings"]
    sections += [f"The illustrative paired demo uses case {setting['case']}, demand seed {setting['seed']}, ramp {setting['ramp']}, sequence {setting['sequence']}, and synthetic critical buses {demo['critical_bus_ids']}. Critical-first retains {setting['critical_gain_mw']:.2f} MW more critical service; total shed changes by {setting['total_extra_shed_mw']:+.2f} MW. This example was selected for its largest observed critical gain and is explicitly not a representative average.", "",
        "[Open the paired comparison](demo_critical/comparison.html), [total-service trace](demo_critical/total.html), or [critical-first trace](demo_critical/critical-first.html).", "",
        "## 6. Validation, reproducibility and artifacts", "",
        f"Saved rows: {manifest['protection_rows']:,} main protection, {manifest['sensitivity_rows']:,} requested protection stress ({manifest['sensitivity_success_rows']} feasible), {manifest['timing_rows']:,} timing, and {manifest['priority_rows']:,} priority evaluations. Maximum reported primal/bound/integrality residual over the exported feasible evaluation rows is {manifest['max_residual_pu']:.3g} per-unit, below the simulator acceptance threshold of 2e-6. The largest recorded normalized priority-service floor tolerance is {manifest['max_priority_service_floor_tolerance_pu']:.3g} p.u. A full raw-data audit independently replays selected results and checks cohort pairing and energy arithmetic.", "",
        "Run `.venv/Scripts/python.exe -m pytest -q`, then `.venv/Scripts/python.exe scripts/run_part2.py`, then `.venv/Scripts/python.exe scripts/build_part2_report.py`. The suite supports separate protection/timing/priority/report phases and checkpoints exact oracle tables. Dependencies and source/scenario fingerprints are saved. Timings collected with concurrent processes are functional compute measurements, not controlled runtime comparisons with the paper.", "",
        "Raw files: [protection](protection.csv), [defense designs](defense_designs.json), [stress tests](protection_sensitivity.csv), [timing](timing.csv), [priority](priority.csv), [critical groups](critical_groups.json), [analysis](summary.json), [run manifest](run_manifest.json), and exact tables in `oracles/`. See [the demonstration guide](../../PART2_DEMO_GUIDE.md), [test record](validation.json), and [independent data audit](data_audit.json). Core and transitive dependency versions are pinned in [the extension lock file](../../requirements-part2-lock.txt).", "",
        "[Protection demo: case 14](demo_protection_14.html), [protection demo: case 39](demo_protection_39.html), [timing demo](demo_timing/viewer.html), and [critical-service paired comparison](demo_critical/paired_comparison.json).", "",
        "## 7. Conclusions and future work", "",
        "The second-part work is implemented and evaluated within the stated scope. Adaptive protection can improve tested resilience, but nominal scenario robustness does not imply robustness to changed ramp flexibility. Timing patterns and observation windows change the measured consequences, so MW and snapshot-weighted MWh must be kept separate. Critical-first operation can retain important synthetic service while shifting loss to other consumers; myopic operation and severe isolation still limit what priorities can achieve. Saturation and ties are valid negative results.", "",
        "Next steps are joint demand/ramp scenario design; nonuniform protection costs and imperfect hardening; larger-k independent outage searches; physical ramp trajectories and calibrated observation times; critical-demand fractions within a bus; storage with state of charge; restoration and reconnection; and AC/transient validation. Stronger claims require more held-out scenarios, actual critical-facility data and operational validation.", "",
        "## Sources and attribution", "",
        "Selected paper: Chio et al., ICCPS 2025, [DOI](https://doi.org/10.1145/3716550.3722029). [Authors' implementation](https://github.com/andrewgchio/SEQUIN). Related protection model: Mastin et al., [Best Response Intersection](https://pubsonline.informs.org/doi/abs/10.1287/ijoo.2022.0081). The full critique and source interpretation are documented in [PART2_METHODS](../../PART2_METHODS.md). All measured extension results are from the independent Python/HiGHS model.", ""]
    markdown = "\n".join(sections)
    (OUT / "PART2_REPORT.md").write_text(markdown, encoding="utf-8")
    content = html_from_markdown(markdown)
    (OUT / "index.html").write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SEQUIN: second-part evaluation</title><style>
body{margin:0;background:#edf2f5;color:#172b3a;font:16px/1.6 system-ui,sans-serif}main{max-width:1160px;margin:28px auto;padding:38px;background:white;border-top:7px solid #14676d;border-radius:8px}h1{font-size:32px;line-height:1.2}h2{margin-top:45px;border-bottom:1px solid #cbd7df;padding-bottom:8px}h3{margin-top:30px}a{color:#06617d}code{background:#eef3f6;padding:2px 5px;border-radius:3px;font-size:13px}table{border-collapse:collapse;min-width:700px;width:100%;font-size:13px}td{padding:9px;border-bottom:1px solid #d7e0e7;vertical-align:top}tr:first-child{background:#173d51;color:white;font-weight:600}tr:nth-child(even){background:#f4f7f9}.scroll{overflow-x:auto;margin:20px 0}figure{margin:24px 0}img{width:100%;height:auto}p{max-width:100ch}@media print{body{background:white}main{margin:0;padding:0;border:0}h2{break-after:avoid}figure{break-inside:avoid}}@media(max-width:650px){main{padding:20px;margin:0}h1{font-size:25px}}
</style><main>''' + content + "</main></html>", encoding="utf-8")
    print(f"Built {OUT / 'index.html'}")


if __name__ == "__main__":
    main()
