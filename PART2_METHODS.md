# Second-part contribution: critique and three evaluated extensions

This document describes the methods for the second-part extension study: paper critique, three implemented extensions, evaluation against multiple baselines, sensitivity and robustness tests, demonstrations, measured conclusions, and future work.

## Baseline implementation

The baseline provides an independent Python/HiGHS implementation, physical and state validation, exact and heuristic outage search, saved reproduction evidence, an offline viewer, a greedy budgeted-protection prototype, and response-interval multipliers. All 51 original tests passed in the baseline validation before extension changes.

The protection prototype had one recorded case-14, budget-1 example and random/initial-flow controls. Its heuristic reported 393.728459 MW remaining loss; separate exact checking reported 398.000001 MW. This difference is a measured search gap, not a protection guarantee. The previous timing command only scaled ramp bounds. No completed critical-service objective, equal-horizon timing study, held-out defense study, or consolidated second-part conclusion existed in the archive.

Saved author-cache charts, original-model MPS solves, and original-compatible comparisons are inherited evidence. This work does not reclassify those files as fresh executions. Native author-program reproduction and its license limitation belong to the first group's reproduction track; the present extension suite uses HiGHS and does not require Gurobi.

## Critique grounded in the paper

The paper is Andrew Chio et al., *SEQUIN: A Network Science and Physics-based Approach to Identify Sequential N-k Attacks in Electric Power Grids*, ICCPS 2025, DOI [10.1145/3716550.3722029](https://doi.org/10.1145/3716550.3722029). Page numbers below refer to the supplied 12-page PDF.

| Limitation | Evidence and consequence | Response in this project |
|---|---|---|
| Vulnerability discovery does not choose a preparedness investment | Sections 3-4 optimize outage sequences. Section 6, p.10, identifies ruggedization as future work. A high-impact line is not automatically the best line to protect, because subsequent outages adapt. | Extension 1 chooses a protection set under a fixed budget and reevaluates all eligible sequential outages. |
| Fixed response epochs obscure timing effects | Section 3, pp.3-4, represents dynamics by steady-state rounds with fixed ramp allowances. Section 6 proposes variable time epochs. | Extension 2 varies response-window durations at the same total horizon, with the same number of decisions for sequential and simultaneous runs. |
| Total MW treats all consumers alike | Defender model, Eq.2 and accompanying text on p.4, optimizes aggregate load service. Equal total loss can have very different effects on a hospital or communication service. | Extension 3 introduces synthetic priority groups and compares total service, weights, and strict critical-first service. |
| Guided search is heuristic and candidate-limited | Algorithm 1, p.5, screens components before evaluating cut impact. Prefix-tree ranges describe sampled continuations, not all possible continuations. | Exact k=2 oracles for protection; exact case-14 priority evaluation; explicit shared-cohort scope on larger priority/timing cases. |
| Scenario robustness is not established by a few perturbed repetitions | Section 5 varies benchmark/ramp/outage settings. This does not show that a protection decision selected on one scenario generalizes. | Freeze protection using seeds 0/1/2, then test on previously unused seeds 100-104 and shifted demand/ramp conditions. |
| Sequential and simultaneous comparisons have different control opportunities | A one-shot simultaneous response and k sequential responses allow different total ramp opportunity. Order effects alone do not explain every difference. | Give both timing comparators identical duration vectors, total horizon, and dispatch decision count. Report remaining differences in event placement. |
| DC steady states omit important physics | Footnote 1, p.3, explicitly defines dynamics as a sequence of steady-state models. AC voltages, reactive power, frequency, relay trips and transient stability are outside this model. | The study retains the DC scope. Its results do not establish protection against actual blackouts or validate continuous operational trajectories. |
| Myopic, irreversible operation can lock in poor decisions | Eq.2h disallows restoration. Dispatch that maximizes current service need not preserve service after a later outage. | Carry state explicitly; evaluate priority policies over complete sequences and report possible losses as well as gains. |

The paper's strengths remain meaningful: it makes outage order explicit, combines network screening with constrained operator response, validates on multiple public networks, and provides useful impact visualization. The limitations above bound its conclusions; they do not invalidate the contribution.

Two transcription/interpretation issues also matter for implementation: the printed objective in Eq.2a conflicts with the prose's intended loadability maximization, and the failed-line indicator in Eq.2c conflicts with the surviving-line interpretation. The independent implementation follows feasible load-service maximization and removes failed-line angle coupling. Published versus released screening, criticality-score direction, shutdown persistence, and PowerModels versus MATPOWER coefficients are disclosed in `IMPLEMENTATION_NOTES.md`. These are reproducibility issues, not claimed innovations.

## Extension 1: scenario-aware budgeted protection

Use case 14 and case 39, outage budget k=2, protection budget q=0,1,2,3, equal protection costs, and ramp fraction 0.1. A protected line remains electrically in service and is excluded from the modeled outage mechanism. For each design scenario s and ordered outage sequence a, define D_s(a) as final positive-consumption loss in MW, and L_s as initial positive demand.

The design objective is:

`min over protected P, |P| <= q: max over design scenarios s [max over a disjoint from P D_s(a) / L_s]`.

The implemented greedy planner adds the line with the lowest resulting maximum design loss fraction. Ties are broken by mean design loss fraction, then original line ID. At each step every remaining line is a candidate. Greedy selection is not claimed globally optimal. Enumerating all protection sets for q<=2 supplies a separate outer-design oracle and a measured greedy gap.

Exact ordered k=2 outage tables make defense evaluation efficient. Protection changes eligibility, not the physics of an eligible sequence; therefore the post-protection maximum equals the maximum over table rows avoiding the protected set. Every physical prefix is initially solved with full ordered state. Filtering is tested against fresh post-protection exhaustive searches. This is mathematically equivalent to regenerating the finite eligible outage set, and is different from replaying only the original worst sequence.

Baselines use the same protection budget and the same adaptive evaluation:

- No protection, providing the per-scenario loss reference.
- Twenty random nested protection orderings, fixed with seeds 7000-7019.
- Mean initial absolute flow across design scenarios.
- Unweighted edge betweenness on the multigraph, preserving parallel line identity.
- Single-scenario sequential greedy protection, designed on seed 0.
- Simultaneous-outage design, using exact unordered k=2 simultaneous tables on all design scenarios, then tested against sequential outages.
- Exact outer design for q<=2 on the same sequential training objective.

Training uses demand seeds 0,1,2 with +/-5% buswise variation; testing uses 100-104. No test outcome selects a protection set. Stress tests freeze those decisions and use ramp fractions 0.025,0.1,0.5 and demand perturbations 0% and +/-15% on test seeds 100,101. Report mean, worst test loss and paired per-seed reductions. Bootstrap intervals resample five demand seeds, averaging random-defense draws within each seed. These small-sample descriptive intervals are not proof of broad statistical superiority.

Idealized protection and equal costs are limitations. The scenario ensemble is synthetic and small. Exact outage enumeration is only at k=2, and the physics/dispatch policy is still the independent deterministic DC model. An exact design optimum applies only to its finite design scenarios and tested model; it is not a certificate on real grids or arbitrary demand.

Related work already studies defender-attacker-defender protection. [Mastin et al., Best Response Intersection](https://pubsonline.informs.org/doi/abs/10.1287/ijoo.2022.0081) formalizes protection followed by adaptive attack and operating recourse. Our contribution is a course-project extension of the selected SEQUIN workflow and its sequential scenario evaluation; we do not claim to invent grid hardening.

## Extension 2: matched-horizon variable response windows

Use cases 14,39,118 and demand seeds 0,1,2. Generate one SEQUIN and one flow-greedy k=3 outage set per scenario; take all distinct permutations of both sets. Freeze that common ordering cohort across timing patterns and comparators. The reported maximum covers this finite cohort, not every ordered triple of the entire network.

Use horizon H=7.5,15,30 minutes. Duration proportions are even `(1,1,1)`, early-cluster `(0.2,0.2,2.6)`, and late-cluster `(2.6,0.2,0.2)`, scaled to sum to H. There is an explicit final observation/response window. The same lines and their order are replayed for every policy. The simultaneous comparator fails the whole set in its first window, then has no new failures but does redispatch in the other two windows. It has the same durations, horizon, and number of optimization opportunities as its paired sequential comparator.

Assume reference epoch tau=5 minutes and nominal alpha=0.1. Derived ramp rate is `R_g = alpha * Pmax_g / tau` MW/minute; allowance in window j is `R_g * dt_j`. These are declared experimental rates derived from the paper's dimensionless setting, not measured generator data.

The model uses response-then-hold snapshots. Within each window it solves a response with that window's allowance, then charges its endpoint shed L_j across the whole window. The reported **snapshot unserved-energy proxy** is `sum_j L_j * dt_j / 60` MWh. This gives reproducible time weighting, but does not simulate the continuous dispatch trajectory, intra-window service, AC feasibility, or transient ramping. It approximates time-weighted loss rather than exact physical energy not served. Final MW and this MWh proxy are separate metrics. Cross-case plots normalize the proxy by `initial demand MW * H / 60`.

This extension addresses fixed-epoch comparisons in an explicitly bounded discrete model. A physically calibrated trajectory/energy model remains future work; it requires explicit dispatch and service dynamics inside each interval.

## Extension 3: critical-service-aware operator response

Use cases 14,39,118, demand seeds 0,1,2, ramp fractions 0.025,0.1,0.5, and synthetic groups covering 10%,25%,50% of positive-load buses (rounded up). A fixed group seed 17 draws bus indices; the same group is used across demand seeds, response policies, and ramps. Groups of different sizes are not guaranteed nested, so this varies size and membership together, not size alone. One group assignment per size is tested; more group assignments remain a generalization check. Actual original bus IDs and critical demand MW are exported. They are illustrative priority labels, not real hospital or water-system locations.

Compare four operating objectives:

- `total`: maximize total served demand, the independent baseline.
- `weight-2`: maximize service with critical buses weighted 2 and others 1.
- `weight-10`: use weights 10 and 1.
- `critical-first`: first maximize critical MW service; constrain it to its optimum within the recorded numerical service tolerance; next maximize total service; then apply the existing cost tie-break while keeping both service floors.

Service weights are normalized by their maximum (or one, if larger), which leaves the exact weighted optimum unchanged and improves numerical conditioning. Service floors normally use 1e-8 p.u. If identical-model secondary solves fail both with and without presolve, a final solve permits a bounded tolerance of `1e-7 * max(1, absolute service optimum, absolute critical optimum)` on the service floors. A critical-floor-induced primary failure receives the same bounded numerical treatment. The actual tolerance is exported as `service_floor_tolerance_pu`; physical feasibility and optimal-status checks remain mandatory. This is a disclosed approximate lexicographic policy, not an exact arithmetic assertion. Regression tests cover the observed case-14 weighted/critical sequences and case-118 three-step sequence.

Weights and critical-first priorities affect response after outages. Every policy starts from the identical economic initial dispatch for its scenario. Branch flow, generator bounds, ramp bounds, demand non-recovery and shutdown persistence remain enforced. A priority policy can trade noncritical MW for critical service, and myopic early choices can also harm later critical service. Both must be reported.

For case 14 enumerate every ordered pair (380 sequences) for every policy. For cases 39 and 118, union the sequences discovered by SEQUIN, released flow screening, and greedy flow (breadth 2) under total-service operation, plus SEQUIN under each priority policy. Evaluate **every policy on that same union**, preventing a policy from appearing better because it was tested on fewer sequences. These larger cases have cohort worst-found results, not exhaustive or targeted critical-loss certificates.

Report the minimum critical demand retained over the cohort, maximum total shed, and paired per-sequence critical gain/extra total shed relative to total-service operation. The main ramp sweep uses the 25% group, and group-size sensitivity uses nominal ramp 0.1; this is a structured sensitivity design, not every cell of a full factorial. Sequence rows are repeated deterministic scenarios, not independent statistical samples.

## Reproducibility and demonstration

Run `.venv/Scripts/python.exe scripts/run_part2.py` for the complete suite. Phases `protection`, `timing`, `priority`, and `report` can be run separately. Exact oracle tables checkpoint to compressed NumPy files with scenario, case checksum, source fingerprint, software versions and solver statistics. A solver failure stops a phase; it is never turned into a success row. Fresh runs may vary at dispatch ties across solver/platform versions.

The final report, raw CSVs, analysis JSON, figure PNGs, scenario group IDs, and offline demonstrations are in `output/part2/`. `PART2_DEMO_GUIDE.md` supplies the speaking order and runnable commands. The original source ZIP and inherited first-part results are retained.

Each extension has a concrete implementation, multiple comparison policies, sensitivity/robustness settings, and inspectable traces. Conclusions must come from the saved results, including ties, saturation and failures. Completion of this bounded study does not imply six-case large-k native paper reproduction or operational grid validation.
