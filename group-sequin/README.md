# SEQUIN Python Implementation

## Final presentation and speaking script

- [Final PowerPoint](output/presentation/SEQUIN_Final_Presentation.pptx): 31 slides, matching the uploaded template, with nine editable charts and original slides retained.
- [Matching presentation PDF](output/pdf/SEQUIN_Final_Presentation.pdf): the same 31 slides, exported from PowerPoint.
- [Three-speaker script](output/documents/SEQUIN_15_Minute_Three_Speaker_Script.docx): Chandan slides 15–19, Saksham slides 20–24, Tejas slides 25–30. Approximately five minutes each.
- [Separate full report](output/pdf/SEQUIN_Group_Extensions_Full_Report.pdf): the detailed scientific report.

The speaking text and visual cues are editable in `output/documents/presentation_script.json`. Run `build_speaking_script_docx.py` to regenerate the Word script. The script follows the final presentation's titles, charts and demonstration screenshot.

`build_elegant_part2.mjs` defines the 16 added slides using the measured results. `append_template_deck.py` calls `assemble_final_presentation.ps1` to combine an exported section with the original template through Microsoft PowerPoint on Windows. It replaces the previous ZIP-only assembly method. Supply the source template and exported section with `--source` and `--section`. Chart workbook values use 14 significant digits for Excel compatibility; raw experiment CSV files retain their recorded precision.

## Evaluated extensions and project report

The local `extensions-study` branch adds scenario-aware line protection, matched-horizon response timing, and critical-service objectives on this repository's own SciPy defender. See [the extension guide](EXTENSIONS_README.md) for the complete file map, commands and result locations, [the implementation comparison](IMPLEMENTATION_COMPARISON.md) for differences from the neighboring implementation, and [the presentation guide](PRESENTATION_GUIDE.md) for explanations and speaking notes. Fresh raw results are in `results/extensions/`, with the standalone report in `output/pdf/` and presentation in `output/presentation/`.

The original description below is retained. Historical numbers in it should be compared with the freshly generated results rather than assumed to be current measurements.

A standalone Python/SciPy implementation of the sequential N-k attack framework studied in:

> Andrew Chio, Russell Bent, Kaarthik Sundar, and Nalini Venkatasubramanian, **“SEQUIN: A Network Science and Physics-based Approach to Identify Sequential N-k Attacks in Electric Power Grids,”** ACM/IEEE ICCPS 2025.

This repository builds the core model and search pipeline from scratch in Python, evaluates it on the six PGLib cases used in the paper, and compares the resulting behavior with released reference outputs.

## Features

### Grid and defender model

- MATPOWER/PGLib case parser.
- DC bus power balance.
- DC branch-flow equations.
- Branch thermal limits.
- Phase-angle limits.
- Line-outage handling.
- Connected-island reference angles.
- Load shedding.
- Sequential state propagation.
- Generator ramp constraints.
- Binary generator on/off recourse.
- Negative MATPOWER loads handled as fixed net injections.
- Optional ±5% load perturbation with explicit random seed.

### Attack and search methods

- Exact simultaneous N-k search for small cases.
- Exact ordered sequential enumeration for small cases.
- Greedy-FLOW.
- Greedy-IMPACT.
- Generator-criticality baseline.
- SEQUIN-style guided search using current-flow shortlisting followed by cut-impact evaluation.
- Permutation search over a fixed line set.
- Replay of reference attack sequences for model-fidelity analysis.

### Network metrics

- Power flow.
- Generator criticality.
- Branch thermal margin.
- Load density.
- Transmission-width heuristic.
- Load-density / transmission-width score.

## Benchmark cases

The implementation includes all six networks used in the paper:

| Case | Buses | Branches |
|---|---:|---:|
| Case 14 | 14 | 20 |
| Case 39 | 39 | 46 |
| Case 60 | 60 | 88 |
| Case 118 | 118 | 186 |
| Case 162 | 162 | 284 |
| Case 240 | 240 | 448 |

## Installation

```bash
python -m venv .venv
pip install -r requirements.txt
```

The implementation uses SciPy/HiGHS and does not require a Gurobi license.

## Run

Run the complete default test suite:

```bash
python run_tests.py
python check_results.py
python make_plots.py
```

For the most expensive large-grid guided searches:

```bash
python run_tests.py --full
```

## Test coverage

The test suite includes:

- six-network Greedy-FLOW sweep for `k = 2...8`;
- selected independent Guided and Greedy-IMPACT runs;
- exact simultaneous and sequential search on small cases;
- permutation tests;
- reference-sequence replay;
- generator-ramp sensitivity;
- full-vs-simplified defender ablation;
- ±5% load-perturbation sensitivity;
- runtime and defender-solve counts;
- automatic diagnosis of search-vs-model divergence.

## Results

Some parts reproduce the released reference outputs very closely, while others diverge.

Examples observed in the current implementation:

- **Case 14, k=2**
  - exact simultaneous: `3.7500`
  - exact sequential: `4.3997`
  - guided: `4.3997`

- **Case 14 guided search**
  - exact agreement for several tested values of `k`.

- **Case 39 guided search**
  - very close agreement for tested `k=2,3,4,6`, typically within about 1–2%.

- **Case 162 guided, k=2**
  - within roughly 5%.

- **Case 240 same-sequence replay**
  - close agreement for tested attack budgets, generally within a few percent.

The implementation does **not fully reproduce every paper/reference result**. The main causes observed are:

1. **Randomized load perturbation**  
   The released experiments perturb loads by ±5%. The original random state is not stored, so different load realizations can change both the attack sequence and final load shed.

2. **Search sensitivity**  
   Small changes in the initial operating point can change the top-flow shortlist and therefore the path followed by Guided Exploration.

3. **Model-detail differences**  
   The Python model captures the core DC, ramp, generator on/off, line-limit, island, and load-shed constraints, but numerical details can still differ from PowerModels/JuMP/Gurobi.

4. **Generator recourse**  
   Removing binary generator on/off behavior causes large errors under tight ramp limits. This is visible in the defender-ablation tests.

5. **Combinatorial cost**  
   Exact enumeration and full Greedy-IMPACT become expensive on large networks because they require many repeated optimization solves.

These discrepancies are retained as part of the analysis rather than tuned away.

## Output files

Running `run_tests.py` produces:

```text
results/results.csv
results/divergence_diagnosis.csv
results/status_summary.csv
results/limitations.csv
```

Running `make_plots.py` produces:

```text
plots/01_author_sequence_replay_error.png
plots/02_flow_k_sweep_all_cases.png
plots/03_selected_search_errors.png
plots/04_ramp_replay_error.png
plots/05_full_vs_simple_ramp.png
plots/06_search_cost_runtime.png
plots/07_load_perturbation_sensitivity.png
```

## Repository structure

```text
.
├── grid_model.py
├── search_methods.py
├── network_metrics.py
├── reference_utils.py
├── run_tests.py
├── check_results.py
├── make_plots.py
├── requirements.txt
├── data/
│   ├── pglib_opf_case14_ieee__api.m
│   ├── pglib_opf_case39_epri__api.m
│   ├── pglib_opf_case60_c.m
│   ├── pglib_opf_case118_ieee__api.m
│   ├── pglib_opf_case162_ieee_dtc.m
│   ├── pglib_opf_case240_pserc.m
│   ├── author_exp1.csv
│   └── author_exp2.csv
├── docs/
│   └── implementation_notes.md
├── results/
└── plots/
```

## Reference

Original SEQUIN implementation:

https://github.com/andrewgchio/SEQUIN
