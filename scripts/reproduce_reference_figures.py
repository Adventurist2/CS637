"""Regenerate the authors' available plots, preserving their data provenance.

This is plot regeneration from supplied author results, NOT new solver execution.
The original plotting functions are used without changing their aggregation.
"""

from pathlib import Path
import csv
import hashlib
import importlib.util
import json
import os
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reproduction" / "docker_reference"
OUT = ROOT / "output" / "reproduction" / "author_reference"
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".mplconfig"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

CASES = ["pglib_opf_case14_ieee__api", "pglib_opf_case39_epri__api", "pglib_opf_case60_c",
         "pglib_opf_case118_ieee__api", "pglib_opf_case162_ieee_dtc", "pglib_opf_case240_pserc"]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    script = SOURCE / "src/experiments/REP_make_plots.py"
    spec = importlib.util.spec_from_file_location("authors_original_plotter", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = OUT / "original_plotter"
    original.mkdir(exist_ok=True)
    module.save_to_file = lambda fname, fig: fig.savefig(original / Path(fname).name, bbox_inches="tight", dpi=160)
    export_legend = module.export_legend
    module.export_legend = lambda legend, fname: export_legend(legend, str(original / Path(fname).name))
    # The supplied script expects paths relative to the artifact working directory.
    before = Path.cwd()
    try:
        os.chdir(SOURCE)
        module.make_experiment0_plots(save=True, show=False, cache_dir="cache-authors")
        module.make_experiment1_plots(save=True, show=False, cache_dir="cache-authors")
        for k in [4, 2, 3]:
            module.make_experiment2_plots(save=True, show=False, k=k, cache_dir="cache-authors")
    finally:
        os.chdir(before)
        plt.close("all")
    panels = []
    for fig, suffix in [(5, "exp1"), (6, "exp2_k4"), (8, "exp2_k2"), (9, "exp2_k3")]:
        for letter, case in zip("abcdef", CASES):
            name = f"figure_{fig}{letter}.png"
            shutil.copyfile(original / f"{case}_{suffix}.png", OUT / name)
            panels.append({"figure": f"{fig}{letter}", "image": name,
                           "cache": f"{case}_{suffix}.csv", "provenance": "author-supplied cached results"})
    for letter, case in zip("ab", [CASES[1], CASES[3]]):
        name = f"figure_4{letter}.png"
        shutil.copyfile(original / f"{case}_exp0.png", OUT / name)
        panels.append({"figure": f"4{letter}", "image": name,
                       "cache": f"{case}_exp0.csv", "provenance": "author-supplied cached results"})
    for figure in [4, 5, 6, 8, 9]:
        selected = sorted([p for p in panels if p["figure"].startswith(str(figure))], key=lambda p: p["figure"])
        rows, cols = (1, 2) if figure == 4 else (2, 3)
        fig, axes = plt.subplots(rows, cols, figsize=(cols * 5.5, rows * 3.8), squeeze=False)
        for ax, panel in zip(axes.flat, selected):
            ax.imshow(plt.imread(OUT / panel["image"]))
            ax.set_title(f"({panel['figure'][-1]})", fontsize=11)
            ax.axis("off")
        fig.suptitle(f"Figure {figure}: regenerated from authors' cached results", fontsize=15)
        fig.tight_layout()
        fig.savefig(OUT / f"figure_{figure}_combined.png", dpi=150)
        plt.close(fig)
    statistics = {}
    for case in [CASES[1], CASES[3]]:
        with (SOURCE / f"output/cache-authors/{case}_exp0.csv").open() as stream:
            rows = list(csv.DictReader(stream))
        std = next(float(r["load_shed"]) for r in rows if r["problem"] == "standard")
        permutation = [float(r["load_shed"]) for r in rows if r["problem"] == "permutation"]
        enumeration = [float(r["load_shed"]) for r in rows if r["problem"] == "enumeration"]
        statistics[case] = {"std_pu": std, "permutation_count": len(permutation),
            "permutation_max_pu": max(permutation), "permutation_max_increase_percent": 100 * (max(permutation) / std - 1),
            "permutations_at_or_above_std_percent": 100 * sum(x >= std for x in permutation) / len(permutation),
            "enumeration_count": len(enumeration),
            "enumeration_max_increase_percent": 100 * (max(enumeration) / std - 1) if enumeration else None}
    caches = [{"name": f.name, "bytes": f.stat().st_size, "sha256": hashlib.sha256(f.read_bytes()).hexdigest()}
              for f in sorted((SOURCE / "output/cache-authors").glob("*.csv"))]
    runtime_coverage = []
    for f in (SOURCE / "output/cache-authors").glob("*exp3.csv"):
        raw = f.read_bytes()
        cleaned = raw.decode().replace("\x00", "")
        rows = list(csv.DictReader(cleaned.splitlines()))
        runtime_coverage.append({"file": f.name, "ks": sorted(set(int(r["k"]) for r in rows)),
                                 "nul_bytes": raw.count(b"\x00")})
    manifest = {"source_image": "andrewgchio/iccps-sequin:v1.0.3", "plotter_sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
        "panels_regenerated": len(panels), "panels": panels, "paper_claim_checks_from_author_data": statistics,
        "cached_files": caches, "runtime_cache_coverage": runtime_coverage,
        "figure_7_status": "Not regenerated: only cases 39/118, k=3/4 ramp-based runtime records supplied; paper requires six cases over k=2..8",
        "fresh_optimization": False,
        "plotting_adaptations": "Agg backend, redirected save paths, DPI, figure-number mapping; original data/aggregation unchanged"}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (OUT / "README.md").write_text(
        "# Original reference plots\n\nThese 26 numerical panels were regenerated using the authors' plotting functions and cached results. "
        "They are reference-data replotting, not fresh optimization runs.\n\n"
        "Published Figure 7 cannot be regenerated from the supplied caches: runtime data covers two cases at k=3/4, "
        "rather than six cases across k=2..8. Raw input hashes and the precise mapping are in manifest.json. "
        "The artifact also numbers ramp sweeps differently: REP figure 7 commands correspond to published Figure 8, "
        "and REP figure 8 commands correspond to published Figure 9.\n", encoding="utf-8")
    print(f"Regenerated {len(panels)} author-reference panels in {OUT}")
    print(json.dumps(statistics, indent=2))


if __name__ == "__main__":
    main()
