"""Compare one-step objectives on EXACT original prior dispatch/load states."""

from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sequin import load_case
from sequin.reference_compat import case_from_original_export, previous_state_from_export, OriginalDCPResponse
from sequin.report import write_json, write_csv


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="output/reproduction/original_traces/results.json")
    parser.add_argument("--output", default="output/reproduction/controlled_comparison")
    args = parser.parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    rows = []
    incomplete = []
    for entry in payload["results"]:
        if entry["status"] != "ok":
            incomplete.append(entry["id"])
            continue
        job = entry["job"]
        if job["method"] != "trace":
            continue
        if len(entry["result"]["trace"]) != len(job["sequence"]):
            incomplete.append(entry["id"])
        scenario = entry["result"]["scenario"]
        case = case_from_original_export(load_case(job["case"]), scenario)
        sim = OriginalDCPResponse(case, job.get("ramp", 0.1), tie_break="none")
        for i, step in enumerate(entry["result"]["trace"]):
            previous = previous_state_from_export(case, scenario, step)
            state = sim.respond(previous, [int(step["failed"][-1])])
            original = step["shed_pu"] * case.base_mva
            error = state.shed_mw - original
            rows.append({"job": entry["id"], "case": job["case"], "round": i + 1,
                         "failed": step["failed"], "original_gurobi_mw": original,
                         "python_highs_mw": state.shed_mw, "difference_mw": error,
                         "within_0.001_mw": abs(error) <= 0.001,
                         "max_residual_pu": state.max_residual_pu})
    out = Path(args.output)
    all_match = bool(rows) and not incomplete and all(r["within_0.001_mw"] for r in rows)
    write_csv(out / "comparison.csv", rows)
    write_json(out / "comparison.json", {"comparisons": rows, "all_match": all_match,
        "incomplete_jobs": incomplete,
        "scope": "One-step primary objective on original exported prior states; not equality of multi-step dispatch choices",
        "model": "PowerModels 0.21.3 DCP compatibility, no persistent shutdown, no secondary tie-break"})
    print(f"Compared {len(rows)} original response steps; {sum(r['within_0.001_mw'] for r in rows)} within 0.001 MW")
    return 0 if all_match else 1


if __name__ == "__main__":
    raise SystemExit(main())
