# Group reproduction versus the neighboring implementation

Group source: upstream commit `e03e8495fb67af50f00c52daa75908e34960f151` of [sequin-python-reproduction](https://github.com/AlankritGupta584/sequin-python-reproduction). The neighboring implementation is the existing `sequin/` package in the parent workspace. The paper authors' released code is a third implementation, written in Julia using PowerModels/JuMP/Gurobi.

## Source-level differences

| Aspect | Group reproduction | Neighboring implementation | Why it matters |
|---|---|---|---|
| Structure and solver | Flat Python modules, dense NumPy constraints, SciPy `linprog` and `milp` | Packaged modules, sparse constraints, direct `highspy` interface | Primarily organization and numerical behavior; solver APIs alone do not prove a speed advantage |
| Power units | MW internally, `shed_pu` divides by baseMVA | Per-unit internally, exports MW | Convert before comparing. 4.3997 p.u. at base 100 is 439.97 MW |
| Initial dispatch | Linear cost from `gencost[:, -2]`, 0-to-Pmax bounds | Parsed convex polynomial cost, including quadratic terms where supplied | All six supplied cases have zero quadratic terms, so quadratic support alone does not explain their differences |
| Response objective | Single maximum-total-service objective, no economic tie-break | Service optimum followed by economic tie-break, with small online preference | Two equally good immediate responses can have different later losses |
| MILP precision | Leaves relative gap at HiGHS default | Requests relative gap `1e-8` and checks feasibility | Early solver termination can also change intermediate states. The extension priority analysis includes a matched-precision total-service baseline |
| Generator shutdown | Creates fresh binary z each round but does not constrain it by previous z | Carries `online` and enforces no restart | A generator set to zero can return within its next ramp window in the group model. This differs from paper Eq. 2f |
| Ramp logic | Either off, or within the old-output +/- alpha Pmax interval | Same general recourse, with persistent online limits | Emergency shutoff need not obey a gradual downward ramp. This is model recourse, not a simulated physical transient |
| Negative Pd | Fixed injection after every failure | Initially fixed, then curtailable and nonrecoverable | Most relevant to cases 162/240. The new extensions use 14/39/118, which avoid this difference |
| Active shunt Gs | Positive Gs counts as shed-able demand; negative Gs as fixed injection | Rejects nonzero active shunts | All six supplied cases have Gs=0, so no numerical effect in these benchmarks |
| Absolute angles | Bounds every bus angle in [-pi,pi] and fixes one reference per island | Island reference and branch difference bounds, no universal absolute angle box | Can restrict the feasible region differently on some networks |
| Search | Top-N current-flow starts; at each later round, score the top-N flow candidates by immediate loss | Main SEQUIN uses multiple network properties; separate `sequin-release` flow-screening method | Compare algorithms at matching breadth and screening definition before attributing any result to implementation quality |
| Transmission width | Greedy removal of found edge-disjoint paths; load density is local Pd | Multi-source min-cut width, clustered load density | Group helper is a structural heuristic, and the group's guided method does not use it in its active shortlist |
| Criticality | Generator flexibility only, clipped by ramp allowance | Generator/branch margin construction | A method name shared across projects does not ensure the same score |
| Prefix caching | Original search recomputes prefixes and sometimes initial LPs | Caches full ordered prefixes | New group extension evaluator adds ordered-prefix caching without changing eligible-sequence physics |
| Failure handling | Original `defend` returns None; several searches/benchmarks skip failed candidates | Raises detailed exceptions and checks returned residuals | New extension runner refuses silent failed responses and labels initial infeasibility in stress tests |
| Random loads | Draws only for positive Pd entries | Draws a factor for every bus, also scales negative injections | Identical integer seeds do not create identical demand vectors across implementations. Nominal comparison avoids this confound |

## Matched empirical comparison

`results/extensions/implementation_comparison.csv` replays common fixed attack sequences on unperturbed, identical case files. It records the group default, group with opt-in cost tie-break/tighter precision, neighboring default, and neighboring policy without a cost tie-break. Repeated prefix rows can occur because different complete sequences share a prefix. Deduplicate on `(case, sequence, model)` before plotting.

Examples measured in this environment:

| Case and ordered attack | Group final shed MW | Neighboring default MW | Interpretation |
|---|---:|---:|---|
| Case 14, (3,1) | 439.970 | 462.970 | The same attack is 23 MW different under different response semantics |
| Case 39, (14,46) | 2,093.920 | 2,093.920 | Selected simple cases agree to numerical tolerance |
| Case 118, (104,97) | 531.398 | 1,192.347 | Intermediate response choices and model details can create large later differences |
| Case 240, (437,433,436) | 21,933.806 | 21,937.294 | A close selected replay does not establish complete model equivalence |

These are fixed-sequence probes, not a comprehensive ranking of either implementation. The cost-tie probe also requests tighter MIP precision, so it is not a clean attribution of every difference to cost selection alone. Initial dispatch agrees almost exactly on five cases. Case 60 differs by up to 720 MW for an individual generator despite identical linear cost coefficients; the experiment does not isolate a unique cause, and multiple optimal dispatch choices are a plausible contributor. See `initial_dispatch_comparison.json`.

`default_compatibility.json` compares the extended `grid_model.py` against the **untouched upstream source loaded from Git**. It checks generation and served-load arrays after each tested prefix. All 26 recorded state probes match exactly. This verifies backward compatibility on these probes, not all possible networks or solver versions.

## What changed in the group checkout

The existing physical formulation and default policy remain intact. `defend` gains optional weights, a critical-first service floor, and an optional cost tie-break used for comparison. It returns additional residual/call/tolerance metadata. The default call still uses the original single service objective and original solver options. No original group search method was replaced.

`extensions.py` adds reusable finite outage tables, adaptive protection evaluation, ordered-prefix caching, objective-aware attack sampling, service metrics, and matched timing traces. `run_extensions.py` adds fresh experiments and checkpoints. `audit_extensions.py` adds independently recomputed protection checks, pairing checks, and the matched-precision priority baseline. The report preserves failed or inconclusive findings rather than declaring every extension successful.
