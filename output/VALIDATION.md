# Implementation validation, 23 October 2026

**Later reproduction audit:** the expanded suite now passes 51 tests. Original Julia model construction, supported Python/Gurobi solves, 36 controlled objective comparisons, reference replots and the native license blocker are documented in [reproduction/REPRODUCTION_REPORT.md](reproduction/REPRODUCTION_REPORT.md). The 49-test count below describes the original independent-implementation validation stage.

The independent Python/HiGHS implementation is executable. It imports no code from the authors' checkout. The prepared environment and commands are documented in the project README.

## Automated correctness checks

**49 tests passed.** Tests cover all six benchmark network sizes; valid initial operating points and one outage response on every case; analytic economic dispatch; convex quadratic starting costs; independent nodal power-balance checks; generator ramp limits; permanent shutdown; irreversible demand shedding; isolated loads; thermal limits; parallel lines; transformer taps and phase shifts; negative reactance; negative-demand injections; failure-order dependence; complete-prefix caching; exact sequence oracles; min-cut width; and budgeted-protection behavior. A numerical secondary-optimization regression at zero ramp is covered.

Command used: `.venv\Scripts\python.exe -m pytest -q --tb=short`.

## Measured experiment suites

| Suite | Completed runs | Scope |
|---|---:|---|
| Exact validation | 24 / 24 | Case 14, k=2, 3 scenario seeds, 8 methods including exhaustive sequence and simultaneous-set search. |
| Multi-case comparison | 54 / 54 | Cases 14/39/118, k=2/3, 3 seeds, guided search / flow screening / greedy flow. |
| Ramp sweep | 30 / 30 | Case 39, k=2, 3 seeds, ramp fractions 0/0.05/0.1/0.5/1, guided search and greedy flow. |

No skipped or failed rows remain in these completed suites. Raw CSV and JSON, scenario metadata, software versions, and plots are stored in each named folder. `validation.json` cross-checks the counts and exact comparisons.

All methods within a case/seed share sampled demand and an initial dispatch. Timed searches use fresh caches. These runs were made during development, sometimes concurrently; they establish functional behavior and comparative search outcomes, not publication-quality controlled hardware timings. Some suites precede the final numerical-tolerance/presolve retry adjustment; a current-version exact-validation suite and ramp sweep were rerun, and the final tests pass. See implementation notes for all modeling differences.

## Observations supported by the runs

- Guided search matched exhaustive two-line sequence enumeration in all three Case 14 demand samples, within 1e-4 MW.
- For the same three failed lines in unperturbed Case 14, the six orders produced final demand loss between **375 MW and 462.97 MW**. The simultaneous response to that same set shed approximately 375 MW. Sequential and simultaneous responses allow different aggregate redispatch opportunities, so the comparison is not a matched-time experiment.
- Guided and flow-screened search found higher two-line disruption than greedy flow in some Case 118 samples. On Case 39 the tested methods often tied. No claim of universal superiority is made.
- The prototype protection planner regenerates outage sequences after protection. A separate exhaustive re-evaluation of the selected Case 14 protection finds a worse surviving sequence than the heuristic does, demonstrating why heuristic coverage is not a robustness certificate. The exact re-evaluation is saved in `protection/protection.json` under `independent_validation`.

## Presentation outputs

`demo/viewer.html` is an offline, self-contained sequence viewer with step controls and component tooltips. Its JavaScript passed a syntax check; a live browser check could not reach the sandbox's local preview server. The scientific plots were rendered and visually inspected. The viewer can be opened directly as a local HTML file.

## Remaining scientific work

This is not a numerical reproduction of every original paper figure. Original-artifact comparison, agreed interpretations of ambiguous equations/properties, complete six-case k/ramp sweeps, additional scenario coverage, and controlled timing studies remain. The protection planner is a research prototype and has no global defense-optimality guarantee. AC and transient stability are outside the current DC model.
