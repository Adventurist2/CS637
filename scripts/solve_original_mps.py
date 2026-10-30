"""Solve an unmodified Julia-exported model through licensed gurobipy only."""

import json
from pathlib import Path
import sys

import gurobipy as gp

ROOT = Path(__file__).resolve().parents[1]


def project_reference(path):
    """Record a portable reference without exporting machine-specific parents."""
    path = Path(path).resolve()
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        # Inputs outside the project are identified by filename only.
        return path.name


def main():
    model_path, result_path = map(Path, sys.argv[1:3])
    payload = {"model": project_reference(model_path), "interface": "gurobipy", "gurobi": list(gp.gurobi.version())}
    try:
        with gp.Env(params={"OutputFlag": 0}) as env:
            with gp.read(str(model_path), env=env) as model:
                # Default inner-solver settings match the authors' unconfigured
                # Gurobi inner optimizer. No model-size restriction is altered.
                payload.update(variables=model.NumVars, constraints=model.NumConstrs)
                model.optimize()
                payload["status_code"] = model.Status
                if model.Status != gp.GRB.OPTIMAL:
                    raise RuntimeError(f"Original model did not solve optimally, status={model.Status}")
                payload.update(status="ok", objective=model.ObjVal, seconds=model.Runtime,
                               objective_bound=model.ObjBound if model.IsMIP else model.ObjVal,
                               mip_gap=model.MIPGap if model.IsMIP else 0.0, sense=model.ModelSense,
                               values={v.VarName: v.X for v in model.getVars()})
    except (gp.GurobiError, RuntimeError) as exc:
        payload.update(status="error", error=str(exc))
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
    return 0 if payload["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
