# SEQUIN implementation and extension blueprint

Prepared 23 October 2026 as a planning snapshot. Implementation has since started and is executable: see [README.md](README.md), [implementation notes](IMPLEMENTATION_NOTES.md), and the measured results under `output/`. Statements below about work not yet run describe the original planning stage.

## Recommendation

Build a verified sequential contingency simulator first, reproduce a scoped set of SEQUIN experiments, and then add one substantial extension. The preferred extension is **budgeted protection against sequential outages**, with explicit outage timing as a complementary experiment. Keep critical-load protection and storage as a second possible track after the simulator is stable.

The proposed project question is: **Can a sequence-aware protection policy reduce disruption more effectively than protection selected using static flow or simultaneous-outage analysis, under the same protection budget?**

This is an extension relative to the selected paper. It is not a claim that protection optimization is new to the research literature. Related defense and sequential-attack research already exists; specific novelty must be established for the final method and evaluation.

The attached course slides are project context. They list implementation, reproduction, extensions, and new experiments; they do not state the specific 50-mark rule mentioned in the conversation. Repository publication and presentation work are outside this planning scope, as requested.

## 1. What the paper does

Paper: Andrew Chio, Russell Bent, Kaarthik Sundar, and Nalini Venkatasubramanian, *SEQUIN: A Network Science and Physics-based Approach to Identify Sequential N-k Attacks in Electric Power Grids*, ICCPS 2025, DOI 10.1145/3716550.3722029.

The grid has N components, and k transmission lines are disabled one after another. After every failure, an operator model adjusts generation and sheds load to maintain feasible operation. The search seeks sequences causing high final load shed.

The central mechanism is state dependence. A preceding outage changes generator setpoints, available transmission paths, and which demand remains connected. Generators cannot change output arbitrarily fast. Demand already shed is not restored within the modeled sequence. Therefore, different orders of the same failed lines can have different consequences.

The model is a sequence of DC steady-state optimization problems. It does not simulate frequency, voltage transients, relay timing, or full electromechanical cascading dynamics. An infeasible operating point should not automatically be interpreted as a simulated physical cascade.

The paper contributes guided search using flow and network properties, a sequential operator-response model, and a prefix tree that aggregates observed consequences of explored sequences. It also already includes a visualization toolkit. A new dashboard alone would overlap with existing work.

## 2. Implementation strategy

### Reference and student implementation

Use three clearly labeled versions:

1. **Released reference:** run the authors' frozen repeatability package where possible. Record the exact artifact/version.
2. **Student implementation of the published method:** implement explicit sequential state handling and Algorithm 1 using documented interpretations of ambiguous definitions. Reuse PowerModels for electrical constraints rather than rebuilding a power-system library.
3. **Extension:** add protection decisions, timing, or other research changes only after the baseline is validated.

This makes the team's implementation visible and prevents changes intended to fix reproduction problems from being mistaken for innovations.

### Stack

Preferred: Julia + JuMP + PowerModels + Gurobi, with Python for plotting and later presentation. The authors used this optimization stack, and it minimizes differences caused by rewriting the electrical model.

The reference README provides a repeatability Docker image, `andrewgchio/iccps-sequin:v1.0.3`, and a separate general-use image. It requires a Gurobi WLS license for the documented container route. Eligible academics can obtain academic licenses from Gurobi; obtaining account-bound credentials remains a user/institution action.

The checked-out manifest records Julia 1.9.2. The public checkout does not contain a Project.toml, so a checkout should not be assumed to reproduce the packaged environment without additional dependency work. Prefer the frozen package first and capture its actual environment.

Fallback: use JuMP with HiGHS for a separately validated implementation. HiGHS supports linear/mixed-integer models and convex quadratic objectives, but the reference's Gurobi-specific initialization and lazy-constraint machinery need adaptation. This is not a one-flag solver replacement. A Python implementation is possible, but changes more things at once and makes reproducing the reference harder.

No Julia or Docker executable was found on the current command search path. Source inspection and dataset checks have been completed; simulator execution has not.

### Shared architecture

```text
Frozen benchmark + scenario seed
             |
       initial DC OPF
             |
       explicit grid state
             |
failure strategy -> next outage -> operator optimization -> next state
             |                                        |
             +--------------- repeated k rounds ------+
                                      |
                             traces and metrics
                                      |
                      reproduction / extension evaluation
```

The failure-search strategy and the operator-response model should be separate modules. Otherwise a search improvement can inadvertently change the physics it is being compared against.

Suggested interface:

```text
initialize(case, scenario) -> state
respond(case, previous_state, newly_failed_lines, settings) -> state, status
search(case, initial_state, response_model, search_settings) -> sequences
evaluate(sequence, scenario, defense_configuration) -> trace
```

Store a trace after every round, not just the final score. Include original demand, served demand, generator outputs and on/off status, branch flows, failed line IDs, objective, solver status, feasibility checks, and elapsed simulation interval.

### Operator response: the essential implementation

For every bus i and surviving branch e, enforce nodal active-power balance, DC branch flow, line ratings, and generator limits. Use PowerModels' treatment of transformer taps, phase shifts, and angle bounds instead of assuming every branch is an identical simple line. Preserve branch IDs and parallel lines.

The intended defender objective is to minimize total shed demand, equivalently maximize served demand. Carry the following between rounds:

- Generator outputs, which set the next ramp bounds.
- Generator availability/on-off decisions, if using the paper's irreversible shutdown assumption.
- Served demand or cumulative shed demand, enforcing that previously shed load cannot return.
- Failed components, which remain failed.

With a fixed ramp fraction alpha, the reference uses an allowance of alpha times each generator's maximum output. This is not alpha times its current output. An explicit-time extension can instead use a physical ramp rate multiplied by the interval duration.

For an online generator, bound the next output between the previous output minus the allowed ramp and the previous output plus the allowed ramp, clipped to physical limits. If emergency shutdown is allowed, model it explicitly with a binary status and gate both bounds appropriately. Enforce that an off generator cannot restart when following the paper's assumptions. Do not infer permanent shutdown solely from a floating-point output near zero.

For a disabled branch, fix its flow to zero and remove its active angle-flow relationship. Leaving that relationship in place incorrectly couples disconnected parts of the grid. Handle islands and reference angles consistently.

The defender responds to the current failure and current state. Giving it knowledge of future selected outages would change the paper's myopic response model.

Multiple equally good current-round dispatches can produce different next-round outcomes. Initially preserve reference behavior for comparison. Then test a documented deterministic secondary objective, such as minimum redispatch, as a separate sensitivity experiment.

### Guided search

Implement candidate screening from the published algorithm using absolute line flow, the stated criticality score, and load-density/transmission-width information. Explore multiple initial candidates, simulate each failure, refresh candidates using the new state, and evaluate candidate cut impact with the operator model.

Keep exploration breadth configurable and report the resulting number of optimization calls. Reset the initial state for each independent sequence. Cache complete prefixes or full physical states; caching only the unordered failed-line set is invalid because different orders can reach different dispatches and served loads.

For transmission width, distinguish the appendix's greedy path-removal procedure from an exact generator-to-load minimum cut. A super-source connected to generator buses is a useful exact implementation for a comparison, but it must be labeled as a different interpretation unless equivalence is established. Define behavior for generator-coincident loads and already isolated buses before dividing by width.

Construct a prefix trie keyed by the full preceding sequence. Its minimum/maximum outcomes describe explored continuations; they are not certified bounds for unexplored failures or probabilities of real events.

## 3. Source audit: issues to resolve before calling it reproduced

Inspected public repository commit: `d30f0c6528efe44c7cb5c82a1cd9dff0d6983296`. Local checkout: `third_party/SEQUIN/`.

These are static observations about that checkout, not measured failures or conclusions about the separate container artifact.

| Observation | Evidence | Action |
|---|---|---|
| The main approach uses ten initial high-flow candidates and refreshes a high-flow shortlist. Criticality and density/width initialization are commented out. | `src/outer/ours.jl`, especially lines 23, 27, 33, 36, and 60 | Compare released behavior with the full published Algorithm 1; label them separately. Check the frozen package before assuming it is identical. |
| Printed Eq. 2a minimizes served load even though the prose says minimize shed load; the code maximizes loadability. | Paper p. 4; `src/inner/pm_model.jl:34` | Implement the intended objective and document the discrepancy. |
| Printed Eq. 2c multiplies flow by the interdiction indicator despite defining 1 as failed; another constraint sets failed-line flow to zero. | Paper p. 4 | Follow consistent surviving-branch physics rather than transcribing the equation literally. |
| Shutdown persistence is stated in the paper, but explicit zero-setpoint handling is commented out and no cross-round status is passed through the inspected sequential interface. | `src/inner/pm_model.jl:17`; `src/inner/dc-ls-permutation.jl` | Test off/on persistence directly. Do not silently assume that zero output and irreversible shutdown are equivalent. |
| The criticality prose and formulas do not have an obvious consistent direction: larger distance from a limit ordinarily indicates greater margin. The helper also disables the branch contribution. | Paper p. 5; `src/network_properties/network-properties.jl` | Preserve the published/released variant, then evaluate a clearly defined margin/utilization variant separately. |
| The width helper passes a generator index as a bus endpoint, and the simple density helper sums load at individual buses rather than forming the paper's clusters. | `src/network_properties/network-properties.jl` | Verify generator-to-bus mapping and cluster construction with small hand-checkable graphs. |
| Secondary fuel-cost tie-breaking is present as commented code. | `src/inner/dc-ls-permutation.jl:22` | Quantify sensitivity to dispatch ties; keep baseline and modified policies distinct. |
| The CLI gap defaults to 0.01, while an outer helper divides by 100 before passing the tolerance to the solver. | `src/utils/cliparser.jl`; `src/utils/optimizationutils.jl:67` | Read the effective solver tolerance from logs. Do not infer it from the parameter's name or the paper alone. |
| Several REP baseline calls initialize models separately and can resample load perturbations. Some exceptions are swallowed by empty catch blocks. | `src/experiments/REP.jl`; `src/utils/optimizationutils.jl` | For controlled comparisons, freeze a perturbed case and initial dispatch per seed for all methods. Record every failed run explicitly. |

These findings support a useful evaluation contribution: explain how much results depend on implementation interpretation, common initial conditions, and tie-breaking. They do not by themselves establish a new algorithm.

## 4. Benchmarks and reproduction plan

The six supplied research cases were parsed locally. Bus, branch, and generator counts agree with the paper's Table 1. Below, demand is the unperturbed sum of active bus demands in per-unit, before any shunt accounting.

| Case file | Buses | Branches | Generators | Demand (p.u.) |
|---|---:|---:|---:|---:|
| `pglib_opf_case14_ieee__api.m` | 14 | 20 | 5 | 4.6297 |
| `pglib_opf_case39_epri__api.m` | 39 | 46 | 10 | 100.9350 |
| `pglib_opf_case60_c.m` | 60 | 88 | 23 | 89.4000 |
| `pglib_opf_case118_ieee__api.m` | 118 | 186 | 54 | 68.7482 |
| `pglib_opf_case162_ieee_dtc.m` | 162 | 284 | 12 | 72.3906 |
| `pglib_opf_case240_pserc.m` | 240 | 448 | 143 | 1441.797282 |

The ordinary `pglib_opf_case14_ieee.m` has 2.59 p.u. demand, so it is suitable for a smoke test but is not the paper's stressed Case 14. Freeze the exact supplied files or corresponding PGLib-OPF v23.07 files.

Start with Cases 14 and 39 for correctness, then Case 118 for scale. Add the other three for fuller coverage if the project schedule permits. Case 14 alone can saturate at total demand loss and hide differences between methods.

### Required comparisons

- **STD:** choose a simultaneous set, with the corresponding single-response model.
- **PERM:** evaluate orderings of the set returned by STD; this does not search all possible line sets.
- **Greedy-FLOW, Greedy-SHED, Greedy-CRIT:** match the reference's exploration conventions, including the extra starting candidates described in the paper.
- **ENUM:** all ordered sequences without replacement, only where it can finish.
- **SEQUIN:** distinguish released-code and published-algorithm variants if they differ.

ENUM searches m!/(m-k)! sequences. Case 14 has 6,840 sequences at k=3 and 116,280 at k=4, with multiple operator solves per sequence. Begin with k=2 or 3 and prefix reuse. The default figure scripts include configurations that are much more expensive than a classroom smoke test.

### Experiments

1. Reproduce the order-effect experiment using the same failed set in different orders. Follow the paper's Case 39, k=3, alpha=0.10 setting first. The larger illustrative setting is Case 118, k=6, alpha=0.01.
2. Reproduce a scoped version of Fig. 5: alpha=0.10 and k=2,3,4 initially; later extend toward k=8 where practical.
3. Reproduce a scoped version of Fig. 6: k=4 and a coarse ramp sweep, then the paper's 0 to 1 sweep in steps of 0.05.
4. Measure search time and operator-solve count. Separate environment startup/JIT compilation from steady-state runs; include preprocessing and failed runs consistently.
5. Match the paper's three repetitions for the initial reproduction. For extension claims, use more paired seeds where affordable and report dispersion. The reference default is one repeat, so specify this explicitly.

Use the same seed, perturbed demand, and initial equilibrium for every method within a comparison. Demand perturbation is sampled once per scenario from 95% to 105% of each bus demand. Record solver version, tolerances, stopping status, case checksum, effective exploration breadth, and hardware.

Report final shed MW, fraction of original demand, and runtime. Keep incremental and cumulative shed separate. Convert p.u. using the case's baseMVA. Do not call a final MW value unserved energy; energy requires interval durations and integration.

The paper notes that sequential and simultaneous cases allow different aggregate redispatch opportunities. Preserve that setup when reproducing it; add matched elapsed-time comparisons as an additional evaluation. Do not present the original difference as proof that ordering alone explains the entire gap.

### Correctness gate

Before extension work, check a no-outage state, generator-to-load isolation, branch outage handling, parallel branches, power balance, thermal limits, ramp limits, monotone shed load, and explicit shutdown persistence. For a tiny synthetic network, compare every sequence with direct enumeration. Every result needs a feasible solver status and constraint-residual checks.

Accept agreement on primary objectives within documented tolerances; identical dispatch is not always possible when multiple optima exist. Describe mismatches rather than forcing results to match a figure.

## 5. Extension backlog

The following are research hypotheses to test, not guaranteed improvements.

| Track | Concrete addition | Evaluation | Effort / priority |
|---|---|---|---|
| A. Budgeted defense | Choose q branches to protect against the modeled outage mechanism, then rerun sequence search on remaining eligible lines. | Worst-found shed versus protection budget; compare no protection, random, flow, betweenness, and simultaneous-analysis-based protection. | Medium; preferred main extension. |
| B. Explicit event timing | Vary intervals and use physical ramp-rate times interval; compare equal-total-time schedules. | Final shed and unserved energy versus interval pattern; compare fixed-epoch assumptions. | Medium; best companion evaluation. |
| C. Critical-service protection | Add synthetic priority groups and weighted or lexicographic load service. | Critical demand retained, total shed, and distributional tradeoffs. | Low-medium; useful second track. |
| D. Storage support | Add a limited number of batteries with power, energy, efficiency, and state-of-charge constraints. | Energy not served versus battery size, location, initial charge, and control policy. | Medium-high; after explicit timing. |
| E. Better search | Keep several promising prefixes using beam search and reuse prefix results. | Best-found disruption versus equal solve budget and runtime; exact gap on tiny cases. | Medium; algorithmic alternative. |
| F. Uncertainty-aware protection | Optimize on several demand/generation scenarios, evaluate on held-out scenarios. | Mean, tail, and worst-found disruption; generalization beyond the design scenarios. | Medium; builds on A. |
| G. Calibrated prefix warning | Learn/estimate whether an observed prefix leads to severe outcomes under a defined continuation sampler. | Held-out calibration, false alarms, and warning lead time. | Medium-high; requires coverage and careful probability claims. |
| H. Restoration scheduling | Add line repair and controlled demand reconnection over a longer horizon. | Restoration time and unserved energy versus repair-resource budget. | High; separate longer project. |

### A. Preferred main contribution: sequence-aware budgeted defense

Assume protection makes a branch unavailable for the chosen outage mechanism. This is an idealized intervention; it does not mean the branch is immune to every hazard. Under equal costs, allow q protected branches. Under nonuniform costs, impose a cost budget.

Build a greedy protection planner: tentatively protect each candidate, rerun the failure search, and choose the action producing the largest reduction in worst-found disruption per unit cost. Repeat until the budget is exhausted. Compare with static policies and exhaustive protection search on tiny instances.

The objective is conceptually to minimize the worst disruption over sequences still possible after protection. Since SEQUIN is a heuristic search, its reported worst-found disruption is a lower bound on the true worst-case disruption for that defense. Failure to find a bad sequence does not certify the defense.

Always regenerate outage sequences after protecting components. Merely replaying the original highest-impact sequence can exaggerate the benefit because the outage search should adapt to protection. Evaluate using an independent, stronger search where feasible and held-out demand scenarios. For a protection baseline derived from simultaneous outages, evaluate the selected protection against the same sequential test procedure.

Useful research questions:

- Does protecting a frequently vulnerable line outperform protecting the line with the largest initial flow?
- Do the best protection choices change with the time available for redispatch?
- Does protection based on simultaneous contingencies leave vulnerabilities under sequential outages?
- How much additional budget is needed to keep disruption below a specified threshold on the tested scenarios?

### B. Timing as a complementary extension

For ramp rates R_g and intervals delta_t, use ramp allowance R_g times delta_t. If using rates derived from the paper's dimensionless alpha, choose and disclose a reference epoch; do not present assumed minutes as measured equipment data.

Compare evenly spaced, early-clustered, and late-clustered failures with the same number of failures and total analysis horizon. Specify event times, operating intervals, the period after the last failure, and the operator's response schedule. Include intermediate redispatch opportunities for the simultaneous comparator over the same horizon.

For piecewise-constant load loss L_t over an interval, unserved energy is the sum of L_t times interval length. A zero-duration final state contributes no energy, so include a declared post-event observation interval when appropriate.

This can test a limitation the authors explicitly identify: variable time epochs. Avoid assuming in advance that additional time always reduces observed loss under irreversible shedding and differing operator policies; measure the result.

### C-D. Critical services and storage

Use a transmission benchmark with clearly labeled synthetic critical-load groups representing hospitals, water pumping, or communications. These are illustrative demands, not claims about actual facilities at benchmark buses. Prefer a lexicographic objective (serve critical demand first, then minimize remaining shed) or disclose chosen weights and show their sensitivity.

A battery must track state of charge across intervals, respect MW and MWh limits, and use charging/discharging efficiencies. Compare no battery, equal distributed storage, simple priority dispatch, and the proposed siting/dispatch policy under equal total capacity. A battery cannot inject unlimited power every round or recharge without an energy source.

Hospital resilience, campus backup planning, EV charging management, and water-service continuity are useful use cases. Moving directly to a detailed distribution microgrid may require voltage/reactive-power constraints or AC validation beyond this DC transmission model.

### E-G. Search and warning alternatives

A small beam search with breadth 1, 5, and 10 is a practical alternative extension if optimization methods interest the team more than planning. Compare methods on equal operator-solve budgets, not just the largest scores each can find with different compute. Prefix caching is helpful engineering, while the research claim requires an improved quality/runtime tradeoff.

Treat GNN/RL acceleration as a stretch goal: labeled scenarios, training cost, topology generalization, and comparison with simple non-neural ranking are substantial extra work.

For prefix warnings, the existing attack tree already provides ranges over explored continuations. A real extension needs an explicit continuation distribution, held-out sequences/prefixes, and calibrated predictive performance. A range from selected high-impact sequences is not a probability forecast for natural outages.

## 6. Suggested project scope and work split

Illustrative schedule, assuming roughly six weeks and a small team; revise once the actual deadline and team size are known.

| Stage | Target |
|---|---|
| Week 1 | Establish frozen reference environment, smoke test, scenario format, and source audit. |
| Week 2 | Implement/validate stateful operator response and tiny-case sequence tests. |
| Week 3 | Reproduce order effects and selected k/ramp/runtime curves on Cases 14, 39, and 118. |
| Week 4 | Implement budgeted protection and static/random comparison policies. |
| Week 5 | Evaluate adaptive failures, held-out scenarios, timing sensitivity, and ablations. |
| Week 6 | Resolve discrepancies and finish experimental analysis; optional presentation interface only after results are stable. |

Once the shared response interface and scenario files are frozen, work can proceed independently on: reproduction/search, protection planning, timing/critical-service scenarios, and analysis. Do not give each track a different physics implementation.

Smallest convincing scope: validated student implementation; Cases 14/39/118; scoped reproduction against the specified baselines; sequence-aware protection versus equal-budget controls; adaptive re-evaluation after protection; and one clear ablation explaining why the added method helps or fails.

## 7. Completion criteria and current status

The implementation phase is complete only when sequential traces pass the physical/state checks, small-case results are verified, and baseline comparisons share identical scenario inputs. The innovation phase is complete only when the new method has a defined objective, budget, comparison methods, reproducible evaluation, and honest limits.

Completed now: read the paper; visually inspect the model and algorithm pages; inspect the authors' public implementation; preserve its commit ID; verify all six benchmark sizes and active demands; identify modeling/reproduction issues; design extension hypotheses and evaluation plans.

Not completed: dependency setup, reference execution, student implementation, numerical reproduction, or measured extension results. No performance improvements are claimed.

## Sources

- [SEQUIN paper](https://doi.org/10.1145/3716550.3722029), especially Sections 3-6, Table 1, Algorithms 1-2, and Appendix B.
- [Authors' repository and repeatability instructions](https://github.com/andrewgchio/SEQUIN).
- [Inspected source commit](https://github.com/andrewgchio/SEQUIN/tree/d30f0c6528efe44c7cb5c82a1cd9dff0d6983296).
- [PGLib-OPF benchmarks](https://github.com/power-grid-lib/pglib-opf).
- [Gurobi academic licensing](https://www.gurobi.com/academics).
- [JuMP HiGHS interface](https://jump.dev/JuMP.jl/stable/packages/HiGHS/).
- [Ong et al., Faster solutions to the interdiction defense problem using suboptimal solutions](https://doi.org/10.1016/j.orl.2025.107399), 2026. Related work establishing that general protection/interdiction-defense optimization is already studied.
- [Li et al., Multi-stage robust optimization of reliability improvement for power transmission cyber-physical systems under sequential coordinated attacks](https://doi.org/10.1016/j.ress.2026.112319), 2026. Relevant sequential defense work identified from the publisher's abstract; the full paper was not reviewed.
- [Sandia, Optimal mitigation and control over power system dynamics for stochastic grid resilience](https://www.sandia.gov/research/publications/details/optimal-mitigation-and-control-over-power-system-dynamics-for-stochastic-gr-2024-06-01/), 2024. Related hardening and operating-control optimization.

This was a targeted feasibility and extension review, not an exhaustive novelty survey.
