"""Prepare costly native reference experiments; never execute them implicitly."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def write(name, jobs, scope):
    payload = {"output": f"output/reproduction/fresh_{name}", "resume": True,
               "scope": scope, "jobs": jobs}
    (ROOT / f"reproduction/plans/{name}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(name, len(jobs), "jobs prepared, not executed")


def main():
    jobs = []
    for case, k, ramp, methods in [("39", 3, 0.1, ["std", "perm", "enum"]),
                                   ("118", 6, 0.01, ["std", "perm"])]:
        for method in methods:
            jobs.append({"id": f"fig4_{case}_{method}", "case": case, "k": k, "ramp": ramp,
                         "seed": 0, "perturb": True, "method": method, "solver_timeout": 86400})
    write("figure_4", jobs, "Paper settings; new seeded scenarios, not recovery of unknown original RNG state")
    jobs = []
    for case in ["14", "39", "60", "118", "162", "240"]:
        for seed in range(3):
            for k in range(2, 9):
                for step in range(21):
                    ramp = step / 20
                    for method in ["std", "sequin", "flow", "shed", "crit"] + (["perm"] if k <= 4 else []):
                        jobs.append({"id": f"fig7_{case}_s{seed}_k{k}_r{step}_{method}", "case": case,
                                     "seed": seed, "k": k, "ramp": ramp, "method": method,
                                     "perturb": True, "solver_timeout": 86400})
    write("figure_7", jobs, "Six cases, k=2..8, 21 ramps, 3 seeds. New single-run search timings; "
          "not the original hardware or BenchmarkTools belapsed protocol. ENUM excluded; PERM limited to k<=4.")


if __name__ == "__main__":
    main()
