"""Rebuild the evidence inventory without conflating cached and fresh results."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/reproduction"


def read(path):
    return json.loads((OUT / path).read_text(encoding="utf-8"))


def main():
    reference = read("author_reference/manifest.json")
    model_jobs = read("original_model_checks/results.json")["results"]
    trace_jobs = read("original_traces/results.json")["results"]
    controlled = read("controlled_comparison/comparison.json")
    comparison = controlled["comparisons"]
    native = read("native_license_probe/results.json")["results"]
    payload = {
        "reference_replotting": {"panels": reference["panels_regenerated"], "fresh_optimization": False,
            "figures": [4, 5, 6, 8, 9], "claims": reference["paper_claim_checks_from_author_data"],
            "figure_7": reference["figure_7_status"]},
        "fresh_original_model_exchange": {
            "successful_cases": [r["job"]["case"] for r in model_jobs if r["status"] == "ok"],
            "case_jobs": len(model_jobs), "successful_trace_jobs": sum(r["status"] == "ok" for r in trace_jobs),
            "trace_jobs": len(trace_jobs),
            "model_sizes": [{"case": r["job"]["case"], "variables": r["result"]["initial_variables"],
                "constraints": r["result"]["initial_constraints"]} for r in model_jobs if r["status"] == "ok"],
            "interface": "Original Julia model builders, MPS export, supported gurobipy solve",
            "native_original_search_executed_successfully": False},
        "controlled_python_highs_comparison": {
            "steps": len(comparison), "matching_steps": sum(r["within_0.001_mw"] for r in comparison),
            "tolerance_mw": 0.001, "maximum_absolute_difference_mw": max(abs(r["difference_mw"]) for r in comparison),
            "cases": sorted(set(r["case"] for r in comparison), key=int),
            "scope": controlled["scope"], "compatibility_model": controlled["model"]},
        "native_license_probe": [{"case": r["job"]["case"], "status": r["status"], "error": r.get("error")}
                                  for r in native],
        "full_paper_numerical_reproduction_complete": False,
        "remaining": ["Academic/full Gurobi license for native Julia execution", "Fresh native search and sweep runs",
                      "Runtime study with declared protocol and hardware", "Figure-wise fresh-vs-author comparisons"]}
    (OUT / "coverage.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"reference_panels": reference["panels_regenerated"],
                      "fresh_original_case_models": len(payload["fresh_original_model_exchange"]["successful_cases"]),
                      "controlled_steps": len(comparison), "all_match": controlled["all_match"],
                      "max_difference_mw": payload["controlled_python_highs_comparison"]["maximum_absolute_difference_mw"]}, indent=2))


if __name__ == "__main__":
    main()
