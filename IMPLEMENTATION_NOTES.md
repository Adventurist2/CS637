# Implementation decisions and reproduction boundaries

Second-part additions are documented in [PART2_METHODS.md](PART2_METHODS.md) and [the measured extension report](output/part2/PART2_REPORT.md). The original 51-test suite was rerun before these additions. New numerical regressions expand the service-floor policy described below: weights are normalized; the usual 1e-8 p.u. floor is retried without presolve; only after numerical rejection can the service floor use a recorded bounded relative tolerance of 1e-7 times max(1, absolute objective values). `GridState.service_floor_tolerance_pu` discloses it. Physical residual/status checks remain mandatory. Older saved results retain their original provenance. No previously recorded result is relabeled as a new run.

This file distinguishes the runnable student implementation from the authors' original software. The independent implementation uses Python/HiGHS; original software used Julia/JuMP/PowerModels/Gurobi.

## Physical model

Internal powers are per-unit. For an available branch, `f = (theta_from - theta_to - shift)/(x*tap)`, using the standard MATPOWER DC approximation. Taps of zero in MATPOWER mean a ratio of one. Branch ratings and bus angle-difference limits are enforced. One reference angle is fixed per connected island. An unavailable branch has zero flow and no angle-flow coupling. Parallel branches remain separate variables and outage choices. This formulation is not asserted identical to every PowerModels DCP implementation/version.

The initial dispatch minimizes polynomial generator cost while serving the full scenario demand. Degree > 2, nonconvex quadratic costs, piecewise costs, active conductance shunts, zero-reactance active branches, and type-4 buses are explicitly rejected rather than silently approximated. The six supplied research cases contain no active conductance shunts. Reactive shunts are outside the DC active-power model.

At every subsequent round, maximize served positive demand subject to network constraints, upper-bounded by previously served demand at each bus. A generator that remains online can ramp by at most `ramp_fraction * Pmax`. It can instead shut down to zero immediately. Binary statuses enforce that a shut-down generator remains off. Generator minimums for positive-Pmax units are relaxed to zero as in the authors' preprocessing.

For equal-service solutions, the default second solve imposes a primary-service floor within 1e-8 p.u. of the optimum, minimizes a linear fuel-cost proxy, and weakly favors keeping generators online. This deterministic secondary policy is a deliberate interpretation; the inspected reference has its fuel-cost secondary solve commented out. Set `--tie-break none` to investigate its effect. Initial OPF supports quadratic costs, but response tie-breaking uses the linear coefficient only; response operation does not claim full quadratic economic optimality. A numerically rejected secondary solve is retried on the identical model with presolve disabled; it must still return optimal status and pass the residual checks. A zero-ramp regression case covers this behavior.

Primary and secondary solves must return HiGHS optimal status; a time-limited incumbent is not silently treated as optimal. Each primal is checked for constraint, bound, and integrality residuals. The reported residual is in per-unit. Default MIP relative gap is 1e-8, not the paper's 1% tolerance.

Negative Pd entries are retained as explicit injections, fixed at initialization and curtailable without recovery afterward. They are not counted as unmet positive demand. This avoids the infeasible initial 162-bus scenario produced by simply clipping all negative demand. The authors' preprocessing can clip negative demand when perturbing but also falls back to an unperturbed case after failed attempts. Their net-demand metric is not directly comparable with this project's positive-consumption loss on cases with negative Pd. Raw source files and gross injection totals are preserved.

## Published algorithm versus released implementation

The inspected authors' commit is `d30f0c6528efe44c7cb5c82a1cd9dff0d6983296`. Its main `ours.jl` uses ten flow-screened starts/candidates; criticality and density/width initialization are commented out.

- `sequin`: union the top `breadth` candidates by absolute flow, printed branch-margin score, and clustered remaining-demand/transmission-width score. Refresh the union after each failure; choose the next line by resulting load loss. Explore every distinct starting candidate.
- `sequin-release`: flow-only multistart and flow-only candidate screening with configurable breadth. This adapts the released screening idea, while retaining this implementation's physics/status/tie-breaking policies. Set breadth to ten for the released shortlist size.
- `greedy-flow`: adaptive absolute-flow choice, with starting alternatives from the top 10% of initial-flow lines.
- `greedy-shed`: evaluate every remaining line by immediate resulting load loss, with top-10% starting alternatives.
- `greedy-crit`: evaluate every remaining line by the sum of generator/branch margins, with top-10% starting alternatives.

The paper's criticality prose suggests that a larger score is more constrained, while its printed formulas measure distance from a limit. We retain the literal positive-margin direction and disclose the ambiguity. Margin normalization or utilization-based scoring would be a separate ablation, not a hidden correction.

Transmission width uses an exact unit-capacity minimum cut from all online generator buses to a load bus, with a super-source. Generator-coincident buses have infinite width. Width zero for an isolated bus gives a zero density/width score to avoid division by zero. All online generator buses, including zero-Pmax synchronous units, count as generator buses in this topological property. This is the minimum-cut interpretation of the paper's definition, not its appendix's order-dependent path-removal algorithm. Adjacent equal-width buses form density clusters, using remaining served demand. Edge scores add endpoint density/width values. These choices should be ablated if matching exact numerical paper curves is required.

`beam` is an optional algorithmic extension, retaining several prefixes after expanding every remaining line. All caching uses complete ordered prefixes, not just unordered failed sets.

## Baselines and exactness

`std` evaluates all k-line sets with a single response from the common initial state. It does not use the paper's outer-level decomposition algorithm, so its runtime should not be presented as that algorithm's runtime. `perm` computes that simultaneous solution and evaluates all its orderings. `enum` evaluates every ordered k-line sequence. All exact searches refuse work exceeding `--max-sequences` before starting.

Exactness is only over finite outage choices under this implementation's deterministic, myopic response policy and solver tolerances. It is not global multilevel optimization over adversarial tie-breaking choices. A prefix tree's min/max ranges cover only continuations searched.

## Experiment controls

For every case/seed, load perturbation is drawn once and the economic starting dispatch is solved once. All methods and ramp settings then use the same immutable-in-practice inputs and initial state. Each timed search uses a fresh prefix cache and topology cache. Initialization is excluded from search timing. Timings can vary with process startup, OS load, and other concurrent runs; raw results include exact software versions and source hashes. Runs produced concurrently during development are functional validation, not a controlled hardware performance study.

The default perturbation is ±5% of both positive demand and negative injection magnitudes. Seeds use NumPy's generator and will not match Julia's random-number stream. No unsuccessful initial scenario is silently replaced with another scenario.

`skipped_limit` means a configured combinatorial guard was reached, not a completed exact result. Solver/model errors produce `error` rows and a nonzero benchmark exit code. Setup failures fail the command. Results are checkpointed to CSV after each search.

## Extension boundaries

Budgeted protection idealizes a protected line as unavailable for the modeled outage mechanism. For each tentative protection decision, outage search is regenerated over remaining eligible lines; old sequences are not merely replayed. The planner uses greedy equal-cost selection and reports random/initial-flow controls. It gives no robust-optimality certificate. Tests compare it with exact outage enumeration on a small analytic grid.

`simulate --interval-multipliers` scales the redispatch allowance after each current failure. The interval is associated with response to that failure, including the last failure. It is a useful time-variation hook, not calibrated seconds, a matched-horizon experiment, or an unserved-energy calculation. A future timing study must define physical ramp rates and an observation horizon explicitly.

## Original-model checks completed after implementation

The frozen Julia environment is prepared. The original OPF and response model builders were executed for all six cases, exported as MPS, and solved through the supported gurobipy interface. Twelve three-step traces were also freshly solved on cases 14/39/60/118, across three Julia seeds. A controlled comparison reproduced all 36 one-step primary response objectives with HiGHS (maximum error 4.27e-12 MW), starting each from the exact original prior state. This is not native original search execution or proof that arbitrary multistep tie-breaking matches.

Inspection of pinned PowerModels 0.21.3 confirms a physical-model distinction: `DCPPowerModel` uses `f = x/(r^2+x^2) * (theta_from-theta_to)` and ignores tap/phase in that branch equation. The MATPOWER-style `DCMPPowerModel` is a different class. `sequin/reference_compat.py` explicitly selects the original coefficient, no secondary tie-break, and absence of cross-round shutdown persistence for these controlled checks. It currently rejects negative original loads, so objective-equivalence checks cover four cases; all-six-case original-model solves are separate evidence. Normal CLI defaults retain their documented MATPOWER model and state policy.

Additionally, the authors' plotting functions regenerated 26 panels from their cached results. These are reference replots, not fresh solver results. Rounded headline claims of 19.3%, about 47%, and 81.4% agree with the supplied cache calculations. See [the full audit](output/reproduction/REPRODUCTION_REPORT.md) and machine-readable `output/reproduction/coverage.json`.

## What remains for full paper reproduction

Native Julia Gurobi returned error 10009 because the available pip license is restricted to the gurobipy interface. An academic/full license is needed to execute the original callback-based outer searches. The original six-case k=2..8 and 0..100% ramp sweeps, complete native exhaustive/permutation comparisons and fresh curve matching remain pending. Runtime cache coverage is insufficient for Figure 7, and new timing runs must declare hardware and measurement protocol. Resumable plans and setup instructions are in `reproduction/README.md`. No figure-by-figure fresh match or statistically significant superiority claim is made.
