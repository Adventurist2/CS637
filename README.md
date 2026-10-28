# SEQUIN: sequential grid failures and resilience extensions

An independent Python implementation of SEQUIN-style sequential grid contingency analysis, plus **three evaluated extensions**: scenario-aware protection, variable response timing, and critical-load prioritization. The main implementation uses the open-source **HiGHS** optimizer and public PGLib benchmark networks; it does not require Gurobi.

**The basic question:** if transmission lines fail one after another, how does the grid respond, how much demand becomes unserved, and which interventions help?

**Recorded validation:** [69 passing tests](output/part2/validation.json) and a [passed independent experiment-data audit](output/part2/data_audit.json). The saved experiments include improvements, ties, tradeoffs, and failures. Results apply to the stated DC model and evaluation scope.

Original paper: Andrew Chio, Russell Bent, Kaarthik Sundar, and Nalini Venkatasubramanian. *SEQUIN: A Network Science and Physics-based Approach to Identify Sequential N-k Attacks in Electric Power Grids*, ICCPS 2025. [Paper DOI](https://doi.org/10.1145/3716550.3722029) · [Authors' code](https://github.com/andrewgchio/SEQUIN).

## Start here

| What you want to do | Where to start |
|---|---|
| Understand the project and navigate its files | This README |
| See what was already implemented and what was added | [PART2_STATUS.md](PART2_STATUS.md) |
| Understand the critique, extension objectives, assumptions, and experiment design | [PART2_METHODS.md](PART2_METHODS.md) |
| Read measured findings, comparisons, limitations, and future work | [Full results report](output/part2/PART2_REPORT.md) |
| Prepare a presentation or demonstrate the project | [PART2_DEMO_GUIDE.md](PART2_DEMO_GUIDE.md) |
| Understand differences from the paper and original program | [IMPLEMENTATION_NOTES.md](IMPLEMENTATION_NOTES.md) |
| Inspect original-program reproduction evidence | [Reproduction report](output/reproduction/REPRODUCTION_REPORT.md) |

GitHub renders the Markdown reports and PNG plots directly. The HTML viewers are offline artifacts: clone or download the repository, then open them in a local browser. GitHub's file view displays their source; this repository does not configure GitHub Pages hosting.

## 1. How the project works

The grid contains buses, generators, consumers, and transmission lines. When a line fails, the simulator adjusts generation and serves as much demand as the remaining system allows. Unserved demand is called **load shed**.

For one tested failure sequence:

```text
Benchmark network + sampled demand
               |
       Initial economic dispatch
               |
       Fail the next selected line
               |
       Optimize the operator response
               |
       Save the new operating state
               |
       Repeat until k failures occur
               |
       Export loss, trace, and metrics
```

Order matters because generator adjustment is limited, earlier load shedding persists, and generator/line availability is carried forward. Failing lines `1,3` can reach a different state from failing `3,1`.

The code separates **search** from **physics**: a search algorithm chooses which failures to examine; the simulator calculates the feasible response. Higher discovered load shed is a stronger failure-search result. Lower remaining loss is a better protection result.

| Parameter | Meaning |
|---|---|
| `--case` | Benchmark network; case 14 means 14 buses, not 14 lines |
| `-k` | Number of failed lines |
| `--budget` | Number of lines protected by the earlier protection command |
| `--ramp` | Generator adjustment fraction per reference response epoch, relative to maximum generation |
| `--breadth` | Heuristic search effort; SEQUIN combines candidates from several scores |
| `--seed` | Reproducible demand scenario |
| `--perturb` | Magnitude of buswise demand variation; `0.05` means +/-5% |

## 2. Repository structure

```text
CS637/
|
|-- sequin/                     Main Python implementation
|   |-- case.py                 Network parser and demand scenarios
|   |-- physics.py              Electrical model and operator response
|   |-- search.py               Failure search, baselines, caching, prefix tree
|   |-- defense.py              Earlier single-scenario protection planner
|   |-- extensions.py           Scenario-aware protection, timing, service metrics
|   |-- cli.py                  Command-line interface
|   |-- report.py               CSV/JSON exports, plots, and offline viewer
|   |-- reference_compat.py     Helpers for controlled original-model comparisons
|   |-- __main__.py             Entry point for python -m sequin
|   |-- __init__.py             Public imports
|   `-- data/
|       |-- PROVENANCE.md       Benchmark attribution
|       `-- cases/              Active packaged MATPOWER benchmark files
|
|-- scripts/                    Experiment, reporting, and packaging workflows
|   |-- run_part2.py            Runs the three extension studies and analysis
|   |-- build_part2_report.py   Builds the readable report and paired demo
|   |-- verify_part2.py         Independently audits results and replays examples
|   |-- package_part2.py        Creates the completed project ZIP
|   `-- ...                    Optional original-program reproduction helpers
|
|-- tests/                      Unit, integration, invariant, and regression tests
|
|-- output/                     Saved results, plots, and demonstrations
|   |-- part2/                  Completed extension-study outputs
|   |-- reproduction/           Inherited reference-reproduction evidence
|   |-- benchmarks/             Earlier multi-method comparisons
|   |-- exact_validation/       Earlier exact small-case comparisons
|   |-- order_effect/           Earlier permutations of a fixed failed set
|   |-- ramp_sweep/             Earlier ramp-sensitivity comparisons
|   |-- protection/             Earlier protection example
|   |-- demo/                   Earlier base-simulator demonstration
|   `-- ...                    Additional validation outputs
|
|-- reproduction/               Original Julia reference source and run plans
|   |-- README.md               Optional reference setup instructions
|   |-- docker_reference/       Frozen original source, dependencies, and caches
|   `-- plans/                  Original-program experiment configurations
|
|-- data/cases/                 Additional benchmark copies retained in the project
|-- README.md                   This project guide
|-- IMPLEMENTATION_NOTES.md     Model choices and reproduction boundaries
|-- PART2_STATUS.md              Before/after completion audit
|-- PART2_METHODS.md             Critique and extension methodology
|-- PART2_DEMO_GUIDE.md          Presentation and demonstration guide
|-- SEQUIN_PROJECT_BLUEPRINT.md Historical planning document
|-- pyproject.toml              Package definition and dependency ranges
|-- requirements-*.txt          Recorded dependency versions
|-- PACKAGE_MANIFEST.json       Inventory from an earlier packaged snapshot
|-- SEQUIN_Project.zip          Original supplied archive
`-- SEQUIN_Part2_Completed.zip  Completed-work archive
```

The alias-based Python loader uses **`sequin/data/cases/`**. The root `data/cases/` directory is a separate retained copy.

Local environments and working files such as `.venv/`, `.tools/`, `tmp/`, `.mplconfig/`, `.pytest_cache/`, and `__pycache__/` are ignored and are not uploaded. Credentials and private keys are also excluded by `.gitignore`.

## 3. Where the three extensions are implemented

### Extension 1: scenario-aware budgeted protection

**Question:** with a limited protection budget, which lines should be protected before sequential failures occur?

Protection keeps a line electrically available but excludes it from the modeled failure mechanism. The failure search adapts to the protected set. The planner designs against multiple demand scenarios, then tests the frozen decision on unused scenarios.

| What to inspect | Location |
|---|---|
| Exhaustive outage tables | [`enumerate_outages()` and `OutageTable`](sequin/extensions.py) |
| Multi-scenario greedy protection | [`robust_protection()`](sequin/extensions.py) |
| Exact small-budget protection comparison | [`exact_protection()`](sequin/extensions.py) |
| Design/test seeds, baselines, budgets, and stress settings | [`protection_study()`](scripts/run_part2.py) |
| Raw main comparisons | [protection.csv](output/part2/protection.csv) |
| Chosen protection sets | [defense_designs.json](output/part2/defense_designs.json) |
| Aggregated comparisons | [protection_summary.csv](output/part2/protection_summary.csv) |
| Demand/ramp stress tests | [protection_sensitivity.csv](output/part2/protection_sensitivity.csv) |
| Initial-infeasible stress scenarios | [stress_initial_failures.json](output/part2/stress_initial_failures.json) |
| Figures | [protection.png](output/part2/protection.png), [sensitivity.png](output/part2/sensitivity.png) |
| Offline demonstrations | [Case 14](output/part2/demo_protection_14.html), [case 39](output/part2/demo_protection_39.html) |

Evaluation uses cases 14 and 39, `k=2`, protection budgets 0-3, design seeds 0/1/2, and held-out seeds 100-104. Baselines include 20 random protection orderings, initial flow, betweenness, single-scenario design, simultaneous-outage design, and exact protection selection for budgets up to two. All eligible ordered failure pairs are evaluated under the model.

**Important distinction:** `python -m sequin protect` runs the **earlier single-scenario planner** in [`sequin/defense.py`](sequin/defense.py). The completed scenario-aware study runs through **`scripts/run_part2.py --phase protection`**, using `sequin/extensions.py`.

The protection-table shortcut is valid because protection changes failure eligibility only. An intervention that changes line capacity or impedance would require new physical response calculations.

### Extension 2: variable timing with matched observation horizons

**Question:** how do different response-window durations change service loss when the total observation horizon is fixed?

The study compares even, early-cluster, and late-cluster windows over horizons of 7.5, 15, and 30 minutes. The sequential and simultaneous comparators receive the same windows and number of response opportunities. Generator adjustment scales with the window duration using a declared reference epoch.

| What to inspect | Location |
|---|---|
| Window-based simulation and energy arithmetic | [`timed_trace()`](sequin/extensions.py) |
| Cases, fixed sequence cohorts, and timing patterns | [`timing_study()`](scripts/run_part2.py) |
| CLI command | [`timing()`](sequin/cli.py) |
| Raw results | [timing.csv](output/part2/timing.csv) |
| Figure | [timing.png](output/part2/timing.png) |
| Offline demonstration | [viewer.html](output/part2/demo_timing/viewer.html) |
| Durations, metrics, and physical snapshots | [timing.json](output/part2/demo_timing/timing.json) |

Cases 14/39/118 and seeds 0/1/2 are evaluated on a fixed common ordering cohort per scenario. These cohorts are not exhaustive searches over every possible triple.

**Energy interpretation:** final load shed is measured in MW. The MWh result is a **response-then-hold snapshot proxy**: each window's endpoint loss is charged over that whole window. Continuous ramp trajectories and intra-window service are not simulated. The derived rates are experimental assumptions, not measured equipment data.

### Extension 3: critical-service-aware operator response

**Question:** can operating priorities preserve important services, and what loss is shifted to other consumers?

Synthetic priority groups represent illustrative critical services. Compare total service, critical weights 2 and 10, and a critical-first policy that maximizes critical service before total service and cost. All policies begin from the same economic dispatch.

| What to inspect | Location |
|---|---|
| Weighted and critical-first optimization | [`GridSimulator.respond()`](sequin/physics.py) |
| Synthetic group selection | [`critical_loads()`](sequin/extensions.py) |
| Critical/noncritical service measurements | [`service_metrics()`](sequin/extensions.py) |
| Shared-cohort evaluation and sensitivity settings | [`priority_study()`](scripts/run_part2.py) |
| CLI priority arguments | [`prepare()` and `main()`](sequin/cli.py) |
| Raw results | [priority.csv](output/part2/priority.csv) |
| Aggregated worst-found service | [priority_summary.csv](output/part2/priority_summary.csv) |
| Original bus IDs for synthetic groups | [critical_groups.json](output/part2/critical_groups.json) |
| Figure | [priority.png](output/part2/priority.png) |
| Offline paired demonstration | [comparison.html](output/part2/demo_critical/comparison.html) |
| Paired trace data and selection explanation | [paired_comparison.json](output/part2/demo_critical/paired_comparison.json) |

Case 14 checks all 380 ordered pairs. Cases 39/118 use a common union of sequences discovered by SEQUIN-style, released-flow-screened, and greedy-flow searches. Every policy is evaluated on the same cohort. Sensitivity covers ramp flexibility, priority weight, and synthetic group definitions.

The groups are not actual facility data. A 25% group means 25% of positive-load buses, not 25% of demand MW. Different-sized groups need not be nested. Priority policies can increase noncritical loss, and an immediate critical-service benefit can be reversed by a later failure.

## 4. Recommended code-review order

| Order | File | What to understand |
|---|---|---|
| 1 | [case.py](sequin/case.py) | `GridCase`, `load_case()`, and `scenario()` define the inputs and sampled demand |
| 2 | [physics.py](sequin/physics.py) | `GridState` carries history; `_model()` builds constraints; `_solve()` invokes HiGHS; `initialize()` and `respond()` define operation |
| 3 | [search.py](sequin/search.py) | `Evaluator` caches ordered prefixes; `network_properties()` screens candidates; `search()` implements the methods; `prefix_tree()` summarizes explored outcomes |
| 4 | [defense.py](sequin/defense.py) | `plan_protection()` is the earlier single-scenario protection prototype |
| 5 | [extensions.py](sequin/extensions.py) | Outage tables, multi-scenario protection, timing windows, and service metrics |
| 6 | [run_part2.py](scripts/run_part2.py) | The actual experimental protocol, baselines, scenario splits, analysis, and plots |
| 7 | [tests/](tests/) | Read each implementation together with its corresponding tests |
| 8 | [report.py](sequin/report.py) and [build_part2_report.py](scripts/build_part2_report.py) | How raw outputs, figures, and demonstrations are generated |

There are two entry routes:

```text
Single CLI experiment:
python -m sequin
    -> __main__.py -> cli.main() -> requested command
    -> case / physics / search -> result exports

Completed extension suite:
python scripts/run_part2.py
    -> protection_study() / timing_study() / priority evaluation
    -> shared simulator and extension functions -> CSVs / analysis / plots
```

`reference_compat.py` and the Julia reference files support separate original-model comparisons; normal Python experiments use the independent model.

## 5. Installation and a small first run

Python 3.11 or later is required. From PowerShell:

```powershell
git clone https://github.com/Adventurist2/CS637.git
cd CS637
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe -m pytest -q

# Small guided search; use a new folder to preserve the saved study outputs.
.\.venv\Scripts\python.exe -m sequin run --case 14 -k 2 --breadth 3 --output output/local_demo
```

Open `output/local_demo/viewer.html` locally. `result.json` contains the physical trace and settings; `prefix_tree.json` summarizes explored continuations.

Linux/macOS use `.venv/bin/python` instead of `.venv\Scripts\python.exe`. Measured extension runs used Python 3.12; [requirements-part2-lock.txt](requirements-part2-lock.txt) pins their dependency versions. [requirements-lock.txt](requirements-lock.txt) describes the earlier implementation environment, and [requirements-reproduction-lock.txt](requirements-reproduction-lock.txt) covers optional reference dependencies.

The prepared `.venv` from the development machine is not part of the repository. A fresh clone needs its own environment. The normal Python implementation does not need Julia or Gurobi.

## 6. Run individual demonstrations

Run these from the repository root. Each example uses a separate output directory.

```powershell
# Replay the same failed set in different orders.
.\.venv\Scripts\python.exe -m sequin simulate --case 14 --perturb 0 --sequence 1,3 --output output/local_forward
.\.venv\Scripts\python.exe -m sequin simulate --case 14 --perturb 0 --sequence 3,1 --output output/local_reverse

# Compare all orderings of three selected lines.
.\.venv\Scripts\python.exe -m sequin order-study --case 14 --perturb 0 --sequence 1,3,4 --output output/local_order

# Earlier single-scenario protection planner, with exhaustive outage recheck.
.\.venv\Scripts\python.exe -m sequin protect --case 14 -k 2 --budget 1 --breadth 3 --verify-exact --output output/local_protection

# Matched-duration timing examples: sequential and simultaneous.
.\.venv\Scripts\python.exe -m sequin timing --case 14 --sequence 1,3,4 --durations-minutes 1,1,13 --output output/local_timing
.\.venv\Scripts\python.exe -m sequin timing --case 14 --sequence 1,3,4 --durations-minutes 1,1,13 --simultaneous --output output/local_simultaneous

# Illustrative priority group, using original MATPOWER bus IDs.
.\.venv\Scripts\python.exe -m sequin simulate --case 14 --sequence 1,3 --critical-buses 12,14 --critical-first --output output/local_critical
.\.venv\Scripts\python.exe -m sequin simulate --case 14 --sequence 1,3 --critical-buses 12,14 --priority-weight 10 --output output/local_weighted

# Exact small-case comparison against search baselines.
.\.venv\Scripts\python.exe -m sequin benchmark --cases 14 --ks 2 --seeds 0,1,2 --methods sequin,sequin-release,greedy-flow,greedy-shed,greedy-crit,std,perm,enum --breadth 3 --output output/local_exact
```

Supported aliases are `14`, `39`, `60`, `118`, `162`, and `240`; numeric MATPOWER `.m` file paths also work. Alias `14` is the stressed API benchmark. The ordinary IEEE-14 file is also supplied and can be loaded by file path. Use `python -m sequin --help` or command-specific `--help` for arguments.

## 7. Reproduce the completed extension suite

The full study performs many optimization solves. All saved reports and plots can be reviewed without rerunning it.

```powershell
# Recompute all three studies, analysis, and figures.
.\.venv\Scripts\python.exe scripts/run_part2.py

# Independently audit raw results and freshly recheck selected outcomes.
.\.venv\Scripts\python.exe scripts/verify_part2.py

# Build the readable Markdown/HTML report and paired demonstration.
.\.venv\Scripts\python.exe scripts/build_part2_report.py
```

The runner also supports separate phases:

```powershell
.\.venv\Scripts\python.exe scripts/run_part2.py --phase protection
.\.venv\Scripts\python.exe scripts/run_part2.py --phase timing
.\.venv\Scripts\python.exe scripts/run_part2.py --phase priority
.\.venv\Scripts\python.exe scripts/run_part2.py --phase report
```

`--phase report` rebuilds analysis and plots from existing raw CSVs. `build_part2_report.py` builds the readable report, rather than running the main experiments.

Exact outage tables are cached with scenario, source, and dependency fingerprints. Priority-worker checkpoints support resuming completed jobs. If changing the priority study's sampling protocol or search breadth in the runner, clear its corresponding checkpoint CSV/JSON files before reuse. Do not edit saved rows to remove unfavorable outcomes.

## 8. Where to find results and validation

| File or directory | What it contains |
|---|---|
| [output/part2/PART2_REPORT.md](output/part2/PART2_REPORT.md) | Full measured extension conclusions; readable on GitHub |
| [output/part2/index.html](output/part2/index.html) | Offline HTML version of the report |
| [output/part2/summary.json](output/part2/summary.json) | Aggregated and paired comparison metrics |
| [output/part2/run_manifest.json](output/part2/run_manifest.json) | Environment, source fingerprints, scenario seeds, counts, and numerical summaries |
| [output/part2/validation.json](output/part2/validation.json) | Recorded test and artifact checks; browser-preview limitation is disclosed |
| [output/part2/data_audit.json](output/part2/data_audit.json) | Independent completeness, pairing, arithmetic, fresh-replay checks, and raw-data hashes |
| [output/part2/oracles/](output/part2/oracles/) | Compressed exact outage tables (`.npz`) with metadata; retained files can include historical source fingerprints |
| [output/part2/checkpoints/](output/part2/checkpoints/) | Intermediate priority-worker CSVs and group definitions |
| [output/order_effect/](output/order_effect/) | Earlier fixed-set ordering experiment |
| [output/exact_validation/](output/exact_validation/) | Earlier small-case algorithm comparisons |
| [output/benchmarks/](output/benchmarks/) | Earlier multi-case algorithm comparisons |
| [output/reproduction/](output/reproduction/) | Separately labeled inherited original-model/reference evidence |

Recorded extension-study counts are **1,648 protection rows**, **144 stress requests** (126 feasible and 18 initial-infeasible policy rows), **1,620 timing rows**, and **24,788 priority rows**. Repeated sequence rows are not independent demand samples.

Selected findings:

- Case 14, protection budget two: mean worst-case loss falls from 100% without protection to **85.77%** with scenario-aware protection, versus **94.63%** with initial-flow protection. Severe residual loss remains.
- Case 39: protection budget two ties initial-flow selection; budget three improves loss, while other design methods can match it. The scenario-aware method is not universally superior.
- Frozen protection choices can lose to initial-flow protection under changed operating conditions. Some shifted demands cannot support a fully served initial state; these failures are recorded explicitly.
- Timing patterns can produce similar final MW losses but very different snapshot-weighted MWh losses.
- Critical priorities improve retained synthetic critical service on tested larger-case cohorts, with possible noncritical-service costs and later-sequence regressions. Exact case-14 outages can overwhelm all tested priority policies.

See the full report for settings, uncertainty summaries, selected-example disclosure, failures, and future work.

## 9. Tests and what they establish

| Test file | Coverage |
|---|---|
| [test_cases.py](tests/test_cases.py) | Benchmark parsing, dimensions, and input validation |
| [test_physics.py](tests/test_physics.py) | Power balance, ratings, ramp limits, islands, shutdown, irreversible shedding, and electrical details |
| [test_search.py](tests/test_search.py) | Search methods, ordered-prefix caching, exact-search guards, and original protection behavior |
| [test_extensions.py](tests/test_extensions.py) | Table filtering versus fresh search, defense checks, priority objectives, timing arithmetic, and numerical regressions |
| [test_extension_cli.py](tests/test_extension_cli.py) | Priority settings reach the simulator and exports; invalid timing is rejected |
| [test_reference_compat.py](tests/test_reference_compat.py) | Controlled original-model compatibility helpers |
| [conftest.py](tests/conftest.py) | Shared synthetic-grid fixtures |

The recorded suite has **69 passing tests**. `verify_part2.py` additionally audits experiment completeness and comparison pairing, and freshly rechecks selected results. Its exhaustive post-protection searches matched the saved case-14 and case-39 test-seed-100 losses exactly.

These checks validate software behavior and finite-model results. They do not establish real-grid operational safety or AC/transient feasibility. Runtime records collected during concurrent development runs are not controlled hardware performance comparisons with the paper.

## 10. Model assumptions and result interpretation

- **Stateful DC operation:** the model uses successive steady states, not AC voltages, frequency transients, relay dynamics, detailed overload cascades, or restoration.
- **Myopic response:** each response optimizes current service without knowing the actual future failure sequence. A current benefit can lead to a worse later state.
- **Persistent losses:** failed lines remain failed, shed demand cannot return, and the independent default persists generator shutdown status.
- **Explicit units:** internal powers are per-unit; exports use case `baseMVA` to report MW. MWh requires a declared timing convention.
- **Negative demands:** retained as separate injections, fixed initially and curtailable irreversibly afterward. Positive-consumption loss is not always the same as the reference's signed/net-load metric.
- **Electrical details:** the independent model preserves parallel-line IDs, generator/bus mapping, taps, phase shifts, angle limits, negative reactance, and initial availability. Unsupported inputs are rejected explicitly.
- **Tie policies and tolerances:** dispatch ties can affect later outcomes. Service-floor tolerances and physical residual checks are recorded; a non-optimal solver result is not silently accepted.
- **Heuristic versus exact:** `sequin` interprets the published method; `sequin-release` adapts released flow screening. Neither name means native Julia execution. Larger-case cohort maxima are worst-found results.
- **Exactness has a scope:** exact outage enumeration is over eligible sequences under the fixed simulator policy. Exact small-budget protection is over finite design scenarios. Neither certifies arbitrary real conditions or adversarial dispatch ties.
- **Baseline definitions differ:** `std` exhaustively checks simultaneous sets on small cases; it does not implement the authors' decomposition. `perm` orders the selected STD set; `enum` checks all eligible ordered sequences. Default exact-search guards refuse work above the configured limit and record skips explicitly.
- **Idealized interventions:** protection changes outage eligibility; critical groups are synthetic; timing energy is a snapshot proxy. The three extensions are evaluated as separate studies using a shared simulator, not as one jointly optimized intervention.

Detailed reasoning is in [IMPLEMENTATION_NOTES.md](IMPLEMENTATION_NOTES.md) and [PART2_METHODS.md](PART2_METHODS.md).

## 11. Original-paper reproduction and provenance

The original research used Julia/JuMP/PowerModels/Gurobi. The independent default uses Python/HiGHS with documented modeling and tie-breaking differences. Normal extension experiments do not import the original Julia implementation.

Inherited evidence includes 26 panels regenerated from author caches and 36/36 controlled original-compatible response-objective comparisons. Cache replots, controlled one-step checks, and a full fresh original search are different evidence. These retained files are not relabeled as newly executed reproduction runs.

Full native Julia/Gurobi outer-search reproduction remains separately license-dependent. See [the audit](output/reproduction/REPRODUCTION_REPORT.md), [coverage inventory](output/reproduction/coverage.json), [reference setup](reproduction/README.md), and [benchmark provenance](sequin/data/PROVENANCE.md). Original-program helper scripts in `scripts/` support this optional track.

The ZIPs are packaged snapshots, not the active source directory. The original supplied archive is preserved; `SEQUIN_Part2_Completed.zip` contains a completed-work snapshot. Review current source in `sequin/` and the current study artifacts in `output/part2/`.

## 12. Potential future work

- Design protection jointly across demand and ramp uncertainty, with both held out during testing.
- Search specifically for critical-service-damaging sequences on larger cases.
- Compare short-horizon operating policies that consider possible future outages.
- Model dispatch/service trajectories inside response windows for physical energy accounting.
- Add nonuniform protection costs, imperfect hardening, and storage with power/energy limits.
- Study restoration, more synthetic group assignments, larger outage budgets, and additional networks.
- Validate selected findings with richer AC or transient models.

These are proposed next steps beyond the completed bounded studies. The broader protection and resilience literature already exists; extensions here are relative to the selected SEQUIN workflow, not claims that these research areas are new.
