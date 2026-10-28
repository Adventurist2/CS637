# Running the original reference artifact

Read `../output/reproduction/REPRODUCTION_REPORT.md` for measured results and remaining limitations. The independent Python implementation runs without this environment.

## Sources and versions

The public Docker artifact `andrewgchio/iccps-sequin:v1.0.3` supplies original Julia source, cases, and 28 cached result files. Only its small COPY layers were extracted; Docker is not required. Each downloaded layer was checked against its registry SHA-256 digest. `docker_reference/PROVENANCE.json` records them.

The dependency Manifest comes from the [archived Zenodo v1.0.2 source](https://doi.org/10.5281/zenodo.14836525). Therefore this environment combines Docker v1.0.3 source/data with the archived v1.0.2 dependency lock; it is not a bit-identical recreation of the Linux Docker runtime. The original Julia algorithm files have not been edited. Wrapper scripts are under `../scripts/`.

Prepared versions: Julia 1.9.2, PowerModels 0.21.3, JuMP 1.24.0, Gurobi.jl 1.6.2 / native Gurobi 12.0.0. Model exchange uses gurobipy 12.0.3. New scenarios use explicit Julia seeds; the authors' original RNG states are not recoverable from the caches.

## Prepare on Windows

The current workspace is already prepared. For another machine, from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test,reproduction]"
.\.venv\Scripts\python.exe scripts/prepare_original_assets.py --julia
$env:JULIA_DEPOT_PATH = Join-Path (Get-Location) '.tools\julia-depot'
$env:JULIA_NUM_PRECOMPILE_TASKS = '2'
& .\.tools\julia-1.9.2\bin\julia.exe --project=reproduction/docker_reference -e 'using Pkg; Pkg.instantiate()'
```

This downloads a project-local Julia runtime and packages; it can take several minutes. The Julia installer verifies the official runtime checksum. Runtime/depot, Python environment and solver license files are intentionally absent from the distributable ZIP.

## Rebuild reference charts and verify existing evidence

```powershell
.\.venv\Scripts\python.exe scripts/reproduce_reference_figures.py
.\.venv\Scripts\python.exe scripts/compare_original_traces.py
.\.venv\Scripts\python.exe scripts/summarize_reproduction.py
```

The first command uses saved author results, not new optimization. The second reruns HiGHS on exact prior states recorded from fresh original-model solves. The third inventories those separate evidence sources.

## Fresh original-model solves through Python Gurobi

```powershell
.\scripts\run_model_checks.ps1 -Plan reproduction/plans/model_checks.json
.\scripts\run_model_checks.ps1 -Plan reproduction/plans/traces.json
```

Julia calls the authors' unchanged OPF and load-service model builders, writes MPS models, and invokes the officially supported gurobipy interface. Ordinary license/model-size limits are enforced. This route solved the included six-case probes and 12 three-step traces; it does not execute the original native search/decomposition callbacks. Models, solutions and exact prior states are saved in the corresponding `output/reproduction/` directories. Successful jobs resume from saved results; set `"resume": false` in a copied plan to force fresh runs and give that plan a new output folder.

## Native original Julia/Gurobi searches

The bundled pip license was rejected by native Julia with `Gurobi Error 10009: PIP license can only be used from gurobipy interface`. Obtain a [free academic Gurobi license](https://support.gurobi.com/hc/en-us/articles/360040541251-How-do-I-obtain-a-free-academic-license) if eligible, using Gurobi's official process. Keep its contents private.

```powershell
.\scripts\run_original.ps1 -Plan reproduction/plans/native_license_probe.json -LicenseFile 'C:\path\to\gurobi.lic'
.\scripts\run_original.ps1 -Plan reproduction/plans/figure_5_case14.json -LicenseFile 'C:\path\to\gurobi.lic'
```

Only the native license failure has been executed so far; the search branches await a suitable license and may expose additional artifact/runtime issues. Plans for Figures 5/6/8/9 use six cases and three seeds; they omit ENUM and limit PERM where configured. Their default per-outer-solve timeout is 120 seconds, a scoped validation setting, not the authors' full runtime allowance. Set `solver_timeout` explicitly for longer runs. A timeout incumbent is not an exact optimum; inspect reported bounds/gaps.

`make_additional_reference_plans.py` prepares Figure 4 and Figure 7 plans. Figure 4 includes all 91,080 ordered 39-bus sequences and the 720 permutations of the 118-bus STD set; it may be expensive. Figure 7 has 14,364 jobs across all six cases, k=2..8, 21 ramp values and three seeds; ENUM is excluded, PERM stops at k=4. These are **prepared, not executed**. Its single-run search timings are a new protocol: the original artifact used BenchmarkTools `@belapsed` around initialization plus search. They cannot be presented as a direct reproduction of published seconds.

Every native job checkpoints separately. Failed jobs are retried on resume, successful jobs are reused, and the wrapper returns a failure exit code when any job fails. Full native output should be inspected before comparing curves. Identical objective values do not imply identical dispatches when multiple optima exist.
