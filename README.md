# SEQUIN: sequential grid contingency analysis

A working independent Python implementation of the central SEQUIN model and search workflow, with an open-source HiGHS optimizer. It runs on the public PGLib benchmark cases without a Gurobi license.

**Status:** executable, with 69 passing tests. The second-part work adds three evaluated extensions: scenario-aware budgeted protection, matched-horizon variable response windows, and critical-service-aware operation. Start with [the second-part report](output/part2/index.html), [methods and before/after audit](PART2_METHODS.md), and [demonstration guide](PART2_DEMO_GUIDE.md). Raw results, plots and independent data verification are under `output/part2/`.

The inherited reference audit includes 26 panels rebuilt from author caches, saved original Julia model solves on all six cases through gurobipy, and 36/36 original-compatible response comparisons against HiGHS. These are retained prior results. Full native Julia/Gurobi search reproduction remains separately license-dependent. See [the reproduction report](output/reproduction/REPRODUCTION_REPORT.md) and [reference setup instructions](reproduction/README.md).

Original research: Andrew Chio, Russell Bent, Kaarthik Sundar, Nalini Venkatasubramanian. *SEQUIN: A Network Science and Physics-based Approach to Identify Sequential N-k Attacks in Electric Power Grids*, ICCPS 2025. [Paper DOI](https://doi.org/10.1145/3716550.3722029), [authors' code](https://github.com/andrewgchio/SEQUIN).

## Run locally

From the project directory, the prepared Windows environment can be used directly:

```powershell
.\.venv\Scripts\python.exe -m sequin run --case 39 -k 3 --breadth 3 --output output/demo
```

Open `output/demo/viewer.html` in a browser to step through failures. `result.json` contains the full physical trace; `prefix_tree.json` contains ranges over the explored continuations.

For a fresh installation (Python 3.11 or later):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe -m pytest -q
```

Linux/macOS use `.venv/bin/python` in place of the Windows interpreter path. `requirements-lock.txt` records the versions used for the checked results; platform-specific wheels are selected by pip.

## Commands

```powershell
# Replay a specified order (one-based MATPOWER branch row IDs).
.\.venv\Scripts\python.exe -m sequin simulate --case 14 --perturb 0 --sequence 1,3 --output output/forward
.\.venv\Scripts\python.exe -m sequin simulate --case 14 --perturb 0 --sequence 3,1 --output output/reverse

# Search for a three-line sequential outage.
.\.venv\Scripts\python.exe -m sequin run --case 118 -k 3 --breadth 3

# Compare every ordering of the same three outages.
.\.venv\Scripts\python.exe -m sequin order-study --case 14 --perturb 0 --sequence 1,3,4 --output output/order_effect

# Compare against exact small-case outage choices and all comparison strategies.
.\.venv\Scripts\python.exe -m sequin benchmark --cases 14 --ks 2 --seeds 0,1,2 --methods sequin,sequin-release,greedy-flow,greedy-shed,greedy-crit,std,perm,enum --breadth 3 --output output/exact_validation

# Scoped multi-case experiment with paired scenarios.
.\.venv\Scripts\python.exe -m sequin benchmark --cases 14,39,118 --ks 2,3 --seeds 0,1,2 --methods sequin,sequin-release,greedy-flow --breadth 3 --output output/benchmarks

# Ramp flexibility sweep. This can take longer for larger networks.
.\.venv\Scripts\python.exe -m sequin benchmark --cases 39 --ks 2 --seeds 0,1,2 --ramps 0,0.05,0.1,0.5,1 --methods sequin,greedy-flow --breadth 3 --output output/ramp_sweep

# Experimental extension: choose one component to protect and rerun the failure search.
.\.venv\Scripts\python.exe -m sequin protect --case 14 -k 2 --budget 1 --breadth 3 --verify-exact --output output/protection

# Timing hook: relative post-failure response intervals, not calibrated seconds.
.\.venv\Scripts\python.exe -m sequin simulate --case 39 --sequence 1,2 --interval-multipliers 0.5,1.5

# Three extension studies and the readable report.
.\.venv\Scripts\python.exe scripts/run_part2.py
.\.venv\Scripts\python.exe scripts/build_part2_report.py
.\.venv\Scripts\python.exe scripts/verify_part2.py

# Variable windows with explicit horizon and a snapshot energy proxy.
.\.venv\Scripts\python.exe -m sequin timing --case 14 --sequence 1,3,4 --durations-minutes 1,1,13

# Synthetic critical-service group: original MATPOWER bus IDs.
.\.venv\Scripts\python.exe -m sequin simulate --case 14 --sequence 1,3 --critical-buses 12,14 --critical-first --output output/critical_demo
```

Supported case aliases: `14`, `39`, `60`, `118`, `162`, and `240`; a numeric MATPOWER `.m` filepath also works. Use `python -m sequin --help` and command-specific `--help` for settings.

## Implemented components

- Safe numeric MATPOWER parser, preserving distinct parallel branches, generator/bus mapping, transformer taps, phase shifts, angle limits, negative reactance, and initial availability.
- Initial economic DC OPF with linear or convex quadratic generator costs.
- Myopic load-service maximization after each outage, generator ramp bounds, optional emergency shutdown, permanent shutdown status, persistent failed lines, and irreversible demand shedding.
- Open-source LP/QP/MILP optimization with explicit status and feasibility checks.
- Guided SEQUIN-style screening from flow, printed margin/criticality, and clustered demand-to-width scores.
- Flow-only released-code screening variant, greedy flow/shed/criticality comparisons, beam search, exact small-case sequence enumeration, exact simultaneous-set enumeration, and permutations of the simultaneous solution.
- Prefix caching keyed by the entire ordered history; prefix-tree consequence ranges.
- Repeatable experiments with common demand and starting dispatch per seed, fresh search caches per method, raw JSON/CSV, plots, and an offline sequence viewer.
- An experimental budgeted-protection planner that reruns outage search after every candidate intervention.
- Scenario-aware protection with exact finite-outage tables, held-out testing, multiple equal-budget controls and exact small-budget outer-defense checks.
- Matched-horizon timing comparisons with derived ramp rates and an explicitly labeled response-then-hold snapshot MWh proxy.
- Weighted/lexicographic synthetic critical-load service with shared-cohort evaluation, priority/ramp/group-size sensitivity and paired trace demonstrations.

## Interpreting results

All physical variables are optimized in per-unit and exported in MW using the case baseMVA. `shed_mw` measures unmet positive consumption. Negative demands are represented as separate injections; they are fixed during initialization and can be curtailed irreversibly afterward. This policy is important for the 162-bus case and is a documented difference from the reference's conditional clipping/fallback preprocessing.

`sequin` is the published-method interpretation described in `IMPLEMENTATION_NOTES.md`. `sequin-release` means a flow-screened adaptation of the released approach; it is not execution of the original Julia program. Both share this project's explicit state and tie-breaking policies.

`std` exhaustively evaluates simultaneous line sets on small cases. It is exact over those choices under the current operator model, not an implementation of the authors' decomposition algorithm. `enum` exhaustively evaluates ordered sequences. The default 50,000-sequence limit prevents an accidental multi-day job and produces an explicit skipped record in benchmark runs.

Higher disruption is a stronger outage-search result; lower disruption is a better defense result. A heuristic's worst-found disruption is not a certified maximum. Protection results must be reevaluated using independent/stronger search and additional scenarios before making robustness claims.

The simulator models successive DC operating states. It does not model AC voltage/reactive-power feasibility, frequency transients, relay dynamics, automatic overload cascades, physical damage, or restoration. Timing multipliers scale response opportunity and are not real-time dynamics or energy calculations.

## Project layout

```text
sequin/case.py          MATPOWER input and paired scenarios
sequin/physics.py       DC OPF and sequential operator-response model
sequin/search.py        properties, algorithms, exact oracles, prefix trees
sequin/defense.py       budgeted protection extension
sequin/cli.py           runnable experiments
sequin/report.py        raw exports, plots, and offline viewer
sequin/data/cases/      six research benchmarks plus ordinary IEEE 14
tests/                 physical invariants, analytic examples, search checks
output/                generated experiment results
```

The original source checkout under `third_party/` is retained for reference and is not imported by this implementation. `reproduction/docker_reference/` holds the separately executed original source and author caches, with provenance. Optional reference dependencies use `pip install -e ".[reproduction]"`; Gurobi is not required by the independent implementation. See `SEQUIN_PROJECT_BLUEPRINT.md` for the broader project and innovation plan.
