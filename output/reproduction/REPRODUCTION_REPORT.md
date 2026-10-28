# SEQUIN reproduction audit

The course slides require implementation, reproduction of results, extensions and new examples. They do not explicitly require matching every figure or reproducing identical hardware timing. Reproducing the central scientific findings is part of the assignment. **Full fresh reproduction of all published experiments is not complete.**

## Completed evidence

| Check | Result | Meaning |
|---|---|---|
| Independent Python implementation | 51 tests pass | Includes physics/search checks and two original-model compatibility tests |
| Author reference charts | 26 panels regenerated | Figures 4a–b, 5a–f, 6a–f, 8a–f, 9a–f; saved author data, not new optimization |
| Fresh original Julia model construction and Gurobi solves | 6/6 network cases | Original initialization and one response model per case, exported as MPS and solved through gurobipy |
| Fresh three-step original-model traces | 12/12 traces, 36 response steps | Cases 14/39/60/118, three seeds, outages 1→3→4, ramp 10% |
| Controlled original-Gurobi vs compatible Python/HiGHS check | 36/36 within 0.001 MW | Maximum absolute difference 4.27×10⁻¹² MW |
| Native Julia/Gurobi execution | License error 10009 | Pip license permits its Python interface; native search remains blocked |
| Published Figure 7 runtime coverage | Incomplete author cache | Available files cover only cases 39/118 and k=3/4, not the full published sweep |

The previous independent implementation also retains its 108 completed benchmark runs in `../exact_validation`, `../benchmarks` and `../ramp_sweep`; these use its documented modeling choices and are not substituted for original-program results.

## Published claims recovered from author data

Using the authors' unchanged plotting/aggregation functions and 28 hashed cached CSVs from their public Docker image:

| Published example | Calculation from supplied data | Published rounded claim |
|---|---|---|
| 39 buses, k=3, ramp 10% | Maximum of 91,080 ENUM sequences is 19.3153% above STD | 19.3% |
| 118 buses, k=6, ramp 1% | Maximum of 720 PERM orderings is 47.4056% above STD | About 47% |
| Same 118-bus example | 81.3889% of PERM orderings are at/above STD | 81.4% |

See `author_reference/manifest.json` for the underlying values, SHA-256 input hashes, exact panel mappings and runtime-cache inventory. The script redirects file saves and uses a noninteractive plotting backend; it preserves original data and aggregation. Combined chart sheets are provided for convenient review. Figure 7 cannot be honestly reconstructed from the incomplete runtime caches. No runtime points were invented.

The artifact's command numbering differs from the paper: its REP figure-7 ramp sweep corresponds to published Figure 8 (k=2), and REP figure-8 commands correspond to published Figure 9 (k=3). Published Figure 6 uses k=4.

## Fresh original-model validation

The model exchange calls the original Julia/PowerModels OPF and SEQUIN response builders, writes their mathematical models to MPS, and solves them through the supported gurobipy interface. It carries original signed load and generator states into the next response. This executes fresh optimization while respecting the bundled license's ordinary restrictions. **It does not run the authors' native outer search/decomposition program.**

All six unperturbed probes succeeded. Initial model sizes were:

| Case | Variables | Constraints |
|---|---:|---:|
| 14 | 59 | 55 |
| 39 | 141 | 132 |
| 60 | 243 | 221 |
| 118 | 537 | 484 |
| 162 | 738 | 727 |
| 240 | 1,179 | 1,037 |

`original_model_checks/results.json` records the six probes. `original_traces/results.json` records 12 fresh perturbed traces. Each folder retains individual MPS files, Gurobi solutions, starting scenarios, prior states and solver metadata.

The compatibility check found a substantive implementation distinction: PowerModels 0.21.3 `DCPPowerModel` uses the imaginary part of line admittance, giving flow coefficient `x/(r²+x²)`, and ignores transformer tap/phase in its branch equation. The independent default uses MATPOWER's `1/(x*tap)` approximation and phase shift. The released response also does not persist binary shutdown status across rounds, whereas the independent default does. These choices can change results and must be disclosed.

`sequin/reference_compat.py` explicitly selects the original DCP coefficient, original starting dispatch and demand, per-round generator availability, and no secondary tie-break. It leaves the default implementation unchanged. For each of the 36 comparisons, HiGHS starts from the **exact prior state exported by the original-model trace**, then optimizes the same next response. All primary load-shedding objectives agree to numerical precision. This checks one-step objective equivalence for four nonnegative-load cases; it does not establish identical arbitrary multistep dispatch choices, native heuristic equivalence, or compatibility for negative-load cases 162/240. See `controlled_comparison/comparison.csv`.

## What prevents a complete figure-by-figure rerun

Native Gurobi 12.0.0 called from Julia returned: `Gurobi Error 10009: PIP license can only be used from gurobipy interface`. This was an observed failure, not an assumption. The user confirmed that no academic license is currently available. `native_license_probe/results.json` contains the sanitized failure record. Model exchange provides meaningful fresh evidence, but does not replace the native callback-based search required for complete reference execution.

A suitable [academic Gurobi license](https://support.gurobi.com/hc/en-us/articles/360040541251-How-do-I-obtain-a-free-academic-license) is the next prerequisite. The project-local Julia environment and resumable experiment plans are prepared; instructions are in `../../reproduction/README.md`. Only a local license-file path is needed when running; never put license contents in the repository.

After that, the remaining work is native search smoke tests, six-case k/ramp sweeps, appropriately scoped ENUM/PERM runs, curve comparisons with paired initialization, and a separately declared runtime protocol. Plans with short timeouts are validation configurations, not certified exhaustive results. Unknown original random states, multiple optimal dispatches, platform differences and source-version discrepancies mean exact equality to every plotted number is not guaranteed even with a license.

## Provenance and how to describe this project

Source/cache: [authors' repository](https://github.com/andrewgchio/SEQUIN) and public Docker `andrewgchio/iccps-sequin:v1.0.3`. Frozen dependency Manifest: [Zenodo v1.0.2 archive](https://doi.org/10.5281/zenodo.14836525). Julia 1.9.2 and the pinned PowerModels/JuMP versions were installed locally. This combines v1.0.3 source with the v1.0.2 dependency lock on Windows; it is not a bit-identical Linux container. Native Julia uses Gurobi 12.0.0; supported Python exchange uses 12.0.3. Original algorithm source files are unchanged; adaptation is confined to separately named wrappers.

An accurate project statement is: “We implemented an independent open-source SEQUIN workflow, reproduced the available published reference charts from author data, and validated 36 original-compatible response objectives against freshly solved original Julia models. Full native search and runtime reproduction remains pending a suitable Gurobi license.”

The protection planner, order exploration and timing hooks remain the separate extension work. Matching reference plots alone is not an innovation claim. `coverage.json` provides a machine-readable evidence inventory.
