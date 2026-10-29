# Three extensions on the group's reproduction

This checkout comes from [AlankritGupta584/sequin-python-reproduction](https://github.com/AlankritGupta584/sequin-python-reproduction), upstream commit `e03e8495fb67af50f00c52daa75908e34960f151`. The local branch is `extensions-study`. It is the group's independent Python reproduction, distinct from the paper authors' Julia repository. The extensions call this checkout's `grid_model.defend` for every physical response. The neighboring `sequin/` package is used only by the explicitly named implementation-comparison phase.

## What each extension does

| Extension | Question | Main implementation | Results |
|---|---|---|---|
| Scenario-aware protection | Which q lines should be made ineligible for failure before an attacker adapts? | `extensions.py`: `OutageTable`, `enumerate_outages`, `protection`, `defense_objective`; `run_extensions.py`: `protection_study` | `results/extensions/protection.csv`, `protection_summary.csv`, `defense_designs.json`, `protection_sensitivity.csv`, `protection.png`, `stress.png` |
| Variable response windows | How do outage spacing and the observation horizon change loss? | `extensions.py`: `timed_trace`; `run_extensions.py`: `timing_study`, `timing_task` | `results/extensions/timing.csv`, `timing_summary.csv`, `timing.png`, `demo_timing.json` |
| Critical-service response | Can the operator preserve a selected service group, and at what cost to other loads? | Optional objectives in `grid_model.defend`; `extensions.py`: `critical_group`, `policy_options`, `metrics`; `run_extensions.py`: `priority_task` | `results/extensions/priority.csv`, `priority_summary.csv`, `priority.png`, `critical_groups` encoded as original bus IDs in each row |

The first two use the original group's default response policy. The priority extension compares its original total-service policy, weighted service (2 and 10), and critical-first lexicographic service. `audit_extensions.py` also replays a **total-tight** baseline with the same `1e-8` relative MIP gap as the priority policies. Use `priority_precision_summary.csv`, `priority_precision_comparison.json`, and `priority_examples.json` for this numerical control. The original total-service policy uses HiGHS defaults. Solver precision and policy objectives are separate experimental choices.

## Folder and reading order

```text
group-sequin/
  grid_model.py              MATPOWER parser, initial LP, response MILP
  search_methods.py          original exact, greedy and top-flow guided searches
  network_metrics.py         original flexibility, flow margin and width heuristics
  reference_utils.py         parses released reference CSV sequences and errors
  run_tests.py               original benchmark driver, not a unit-test module
  check_results.py           original assertions on reproduction error thresholds
  make_plots.py              original reproduction plots
  extensions.py              new algorithms, prefix cache, priority and timing helpers
  run_extensions.py          new complete experiment driver and summaries
  audit_extensions.py        independent cohort/table checks and precision controls
  test_extensions.py         regression and extension unit tests
  build_deliverables.py      builds the report, slides content, and demonstration page
  build_presentation_session.mjs  editable slide builder for Artifact Session
  EXTENSIONS_README.md       this navigation and reproduction guide
  IMPLEMENTATION_COMPARISON.md  source-level comparison with neighboring project
  PRESENTATION_GUIDE.md      talk track, result interpretation, common questions
  data/                     unchanged six cases and author reference CSVs
  docs/implementation_notes.md  original group's notes, retained as historical claims
  results/
    results.csv             freshly rerun original benchmark output, if run
    extensions/
      *.csv                 complete rows and aggregate tables for extensions
      *.json                manifest, validation, plans and detailed trace examples
      *.png                 scientific plots
      oracles/*.npz         complete finite outage tables with source/scenario hashes
      priority_checkpoints/ intermediate deterministic priority task results
  output/
    pdf/                    standalone full project report
    presentation/           editable presentation export
    demonstration.html      offline explanation and trace demonstration
```

Start with `grid_model.load_case`, `initial_state`, and `defend`. Then follow one sequence through `search_methods.run_sequence`. Read `guided_search` to understand the group's attack heuristic. Next read the new `extensions.Evaluator`: it caches ordered prefixes and passes objective controls to the same defender. Finally follow each study in `run_extensions.py`, and check the saved CSV against its summary and report.

## Installation and execution

From this checkout, with Python 3.11 or newer:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements-extensions.txt
python -m pytest test_extensions.py -q
python run_extensions.py --phase all --workers 2
python audit_extensions.py --phase all --workers 2
python build_deliverables.py
```

The optional `comparison` phase expects the neighboring project's `sequin/` package. If you only have this checkout, run the self-contained phases separately:

```bash
python run_extensions.py --phase protection
python run_extensions.py --phase timing
python run_extensions.py --phase priority
python run_extensions.py --phase analyze
python audit_extensions.py --phase precision
```

`audit_extensions.py --phase verify` additionally checks the saved cross-implementation compatibility record when present. The original reproduction workflow remains:

```bash
python run_tests.py
python check_results.py
python make_plots.py
```

Its threshold checker may fail on a new runtime or a different input realization. A failed reproduction assertion is evidence to inspect, not a reason to replace measurements with the README's historical values. The original driver sometimes skips failed solver responses; the new extension driver raises on an unsuccessful defender response and explicitly records initially infeasible stress scenarios.

## Protocol and interpretation

- Protection: cases 14/39, complete ordered pairs, design demand seeds 0/1/2 and held-out seeds 100-104 at +/-5%, budgets 0-3. Compare 20 random plans, initial flow, betweenness, single-scenario design, simultaneous design, and exact outer design for budgets up to 2. Freeze plans before demand/ramp stress tests.
- Timing: cases 14/39/118, seeds 0/1/2, permutations of the union of guided/flow attack sets, k=3. Horizons 7.5/15/30 minutes. Even, early and late spacing. Both sequential and simultaneous comparators receive three redispatch windows.
- Priority: cases 14/39/118, seeds 0/1/2. Nominal critical group covers 25% of positive-demand bus count. Ramp sweep 0.025/0.1/0.5; group-size/composition sweep 10%/25%/50% at nominal ramp. Groups use seed 17, are synthetic, and need not be nested. Case 14 evaluates all 380 ordered pairs. Larger cases share the union of policy-specific guided attacks, including critical-loss-targeted attacks. These are worst-found results, not exhaustive guarantees.
- MW loss and MWh proxy loss have different meanings. Timing uses `sum(endpoint_shed_MW * window_minutes / 60)`, a response-then-hold snapshot proxy. Continuous generator trajectories and transient feasibility are not modeled.
- “Exact” outage enumeration means all finite sequences under this solver-selected operator policy. It does not resolve all equally optimal dispatch trajectories or remove MIP tolerances. Greedy protection has no universal optimality guarantee; exact outer checks cover only the small finite design instances.
- A policy can preserve more critical demand while losing more total MW. It can also make a myopic early choice that harms later critical service. Report both outcomes.
- All experiments retain the group's generator restart semantics. The paper describes persistent shutdown, and the neighboring project enforces it. This model difference remains explicit rather than being silently changed during the extension study.

## Where to find explanations and deliverables

Read `IMPLEMENTATION_COMPARISON.md` for the modeling differences and matched attack examples. Read `PRESENTATION_GUIDE.md` for a simple explanation, speaking order, and answers to likely questions. Open `output/demonstration.html` locally for the saved trace examples. The standalone full report is under `output/pdf/` and the presentation is under `output/presentation/`.

Completed deliverables: `output/pdf/SEQUIN_Group_Extensions_Full_Report.pdf` has 20 pages. `output/presentation/SEQUIN_Group_Extensions_Presentation.pptx` has 24 slides with editable tables/charts and speaker notes. The report builder regenerates the PDF, demo, speaking guide and slide data. The PPTX builder runs inside an Artifact Session callback using `build_presentation_session.mjs`; rebuilding the Python report alone does not refresh the exported PowerPoint.

Fresh results: case-14 q=2 scenario protection reduces mean held-out worst loss from 95.04% to 84.87%. Case-39 q=2 flow protection does slightly better than scenario protection (20.35% versus 20.47%). Nominal robust plans lose to flow in 10/36 feasible stress cells. The matched-precision critical-first comparison improves critical service in 2,916 paired sequence/configuration rows and harms it in 75, out of 5,824 pairs. These are deterministic paired counts, not independent scenario probabilities.

Verification: 16 new tests pass, 26 default state probes match untouched upstream exactly, and fresh exhaustive q=2 protection replays match the table maxima. The unchanged original reproduction checker fails on missing case-162 k=8 output. A fresh replay confirms an infeasible eighth response MILP; this is retained as a reproduction limitation. See `results/extensions/original_missing_case162_k8.json` and `original_benchmark_status.json`.

No extension result from the previous project is reused as a fresh result here. Checkpoints contain source fingerprints, scenario settings and data hashes. Reusing a checkpoint after changing physics or experiment definitions requires a new fingerprint and a fresh run.
