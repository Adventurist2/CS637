# Presenting the second part

Open `output/part2/index.html` for the report, plots, raw-data links and demonstrations. Read `PART2_METHODS.md` for exact assumptions and scope. The assignment's second part is critique -> extensions -> comparisons/sensitivity -> demonstration -> conclusions/future work.

## Suggested 10-12 minute speaking order

1. **Motivation and critique (2 minutes).** The first group explains/reproduces SEQUIN. Start here: finding vulnerable sequences does not choose a preparedness investment; fixed epochs hide response timing; total MW ignores critical service. Acknowledge the useful stateful physics/search contribution. Mention DC steady-state and heuristic-search limits.
2. **Extension 1: protection (3 minutes).** Show `protection.png`. Explain design seeds versus held-out seeds, equal budgets, adaptive outage evaluation, and multiple baselines. Use the measured numbers in the final report. Show the ramp/demand stress plot and a case where nominal design loses to a simpler baseline. Distinguish an exact finite-outage oracle from a globally robust real-grid guarantee.
3. **Extension 2: timing (2 minutes).** Show `timing.png`. Every even/early/late schedule has the same horizon within its comparison. The simultaneous comparator also gets three dispatch opportunities. Keep final MW separate from the MWh snapshot proxy. State the response-then-hold approximation; do not claim continuous ramp integration.
4. **Extension 3: critical service (2 minutes).** Show `priority.png`. Compare total service, weights 2/10, and critical-first service. Groups are synthetic, not actual hospital locations. Case 14 enumerates all ordered pairs; larger cases use a common searched cohort. Explain noncritical-service tradeoffs and possible future-state regressions.
5. **Demonstration and conclusion (2-3 minutes).** Open the paired priority demo, then a protection or timing trace. Finish with one improvement, one failure/limitation, and one concrete future step. The report supplies measured conclusions; do not replace them with a universal improvement claim.

## Offline demonstration

- `output/part2/demo_protection_14.html`: a held-out scenario after one protected line, attacked using exhaustive adaptive k=2 search.
- `output/part2/demo_protection_39.html`: the larger protection example, with the same exact outage-choice scope.
- `output/part2/demo_timing/viewer.html`: case-39 early-cluster response windows; `timing.json` gives durations and energy arithmetic.
- `output/part2/demo_critical/total.html` and `critical-first.html`: identical starting dispatch and outage order under two response policies. `paired_comparison.json` gives group bus IDs, critical-service gain and total-service tradeoff. This example is deliberately selected for its largest observed gain, not as an unbiased average.
- `output/part2/demo_critical/viewer.html`: the cohort-worst critical-loss example at nominal case-39 settings. It may illustrate a failure that priorities cannot prevent.

Use Previous/Next or the slider. Hover over a line for its ID, endpoints and MW; hover over a bus for demand and shed. The schematic layout is not geographic. The viewer illustrates successive DC states, not a physical blackout animation.

## Reproduce the work

From the project directory in PowerShell:

```powershell
# Validate implementation and the numerical regressions.
.\.venv\Scripts\python.exe -m pytest -q

# Run all extension evaluations, checkpoints and plots.
.\.venv\Scripts\python.exe scripts/run_part2.py
.\.venv\Scripts\python.exe scripts/build_part2_report.py

# Optional separate phases (each writes its own output family).
.\.venv\Scripts\python.exe scripts/run_part2.py --phase protection
.\.venv\Scripts\python.exe scripts/run_part2.py --phase timing
.\.venv\Scripts\python.exe scripts/run_part2.py --phase priority
.\.venv\Scripts\python.exe scripts/run_part2.py --phase report

# Small live timing demo, three response/observation windows.
.\.venv\Scripts\python.exe -m sequin timing --case 14 --sequence 1,3,4 --durations-minutes 1,1,13 --output output/live_timing
.\.venv\Scripts\python.exe -m sequin timing --case 14 --sequence 1,3,4 --durations-minutes 1,1,13 --simultaneous --output output/live_simultaneous

# Explicit illustrative priority group (MATPOWER bus IDs).
.\.venv\Scripts\python.exe -m sequin simulate --case 14 --sequence 1,3 --critical-buses 12,14 --critical-first --output output/live_priority
.\.venv\Scripts\python.exe -m sequin simulate --case 14 --sequence 1,3 --critical-buses 12,14 --priority-weight 10 --output output/live_weighted
```

The prepared local environment uses the bundled Python installation and locally installed solver/test dependencies. For another computer, follow the fresh-install instructions in `README.md`; do not copy `.venv` between machines. Exact evaluation is intentionally bounded to practical cases/settings. Full first-part native Julia/Gurobi reproduction remains separately documented in `output/reproduction/REPRODUCTION_REPORT.md`.

`requirements-part2-lock.txt` pins the versions used for the new experiments; the older lock files describe the inherited implementation/reproduction runs. Oracle cache keys include source, scenario and package versions. If changing the priority study's sampling protocol or search breadth in the runner, clear its `output/part2/checkpoints/priority_*` CSV/JSON checkpoints before reusing that phase.

## Likely questions and accurate answers

**What is new relative to SEQUIN?** Choosing scenario-aware protection decisions, controlled variable-window timing evaluation, and critical-service response objectives with paired comparisons. General hardening, timing and service priorities already have related literature; this project does not claim to invent them.

**Why not just protect the highest-flow line?** Initial flow is a baseline. Sequential outages change dispatch and reroute flows; the worst remaining sequence adapts to protection. The measured comparison and its stress failures show where sequence-aware design helps and where it does not.

**How do you know protection worked?** On cases 14/39 at k=2, enumerate every ordered pair and take the maximum avoiding protected lines. Check design decisions on unused demand seeds. Test table filtering against independent fresh post-protection exhaustive search. The guarantee is limited to that model/scenario/outage budget.

**Are MWh values physically exact?** No. They are a clearly defined response-then-hold snapshot proxy. Real energy not served needs a physically calibrated within-window trajectory and outage/dispatch timing model.

**Does critical-first always help?** It maximizes immediate critical service within numerical tolerances. Future outages, irreversible shedding and dispatch choices can reverse a short-term advantage. The report explicitly counts final critical-service regressions and total-service tradeoffs.

**Are the larger-case maxima exact?** Protection's k=2 outage tables are exact finite-choice oracles for cases 14/39. Priority case 14 is also exhaustive. Larger priority cases and timing use declared common cohorts and report worst-found outcomes.

**What remains future work?** Joint demand/ramp training, larger k, variable costs/imperfect hardening, real critical-demand data, physical trajectories, storage/restoration, and AC/transient validation. These are extensions beyond the completed bounded second-part study.
