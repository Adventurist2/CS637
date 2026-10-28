"""Package the completed work without replacing the user's original archive."""

from pathlib import Path
from hashlib import sha256
from zipfile import ZipFile, ZIP_DEFLATED
import json

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main():
    report = ROOT / "output" / "part2"
    manifest = json.loads((report / "run_manifest.json").read_text())
    assert json.loads((report / "data_audit.json").read_text())["status"] == "passed"
    assert json.loads((report / "validation.json").read_text())["tests"]["failed"] == 0
    files = [p for p in ROOT.iterdir() if p.is_file() and p.suffix in (".md", ".toml", ".txt")]
    files.append(ROOT / ".gitignore")
    for directory in ("sequin", "tests", "scripts", "data", "reproduction", "output"):
        for p in (ROOT / directory).rglob("*"):
            if not p.is_file() or any(part in {"__pycache__", "checkpoints", "original_probe", "original_quick_probe"}
                                      for part in p.relative_to(ROOT).parts):
                continue
            if p.suffix.lower() in {".pyc", ".lic", ".log"}:
                continue
            if p.parent.name == "oracles" and p.suffix == ".npz":
                with np.load(p, allow_pickle=False) as data:
                    if json.loads(str(data["metadata"]))["source"] != manifest["source_sha256"]:
                        continue
            files.append(p)
    files = sorted(set(files))
    inventory = {"files": [{"path": p.relative_to(ROOT).as_posix(), "bytes": p.stat().st_size,
                             "sha256": sha256(p.read_bytes()).hexdigest()} for p in files],
                 "entry_point": "output/part2/index.html", "methods": "PART2_METHODS.md",
                 "scope": "Completed bounded second-part extension study; native paper search reproduction remains separate",
                 "excluded": "Runtimes, credentials, temporary files, legacy oracle duplicates, partial worker checkpoints; original user archive preserved"}
    target = ROOT / "SEQUIN_Part2_Completed.zip"
    with ZipFile(target, "w", ZIP_DEFLATED, compresslevel=7) as z:
        for p in files:
            z.write(p, p.relative_to(ROOT).as_posix())
        z.writestr("PART2_PACKAGE_MANIFEST.json", json.dumps(inventory, indent=2))
    with ZipFile(target) as z:
        assert z.testzip() is None
        assert all(name in z.namelist() for name in ("output/part2/index.html", "output/part2/data_audit.json",
                                                   "sequin/extensions.py", "PART2_DEMO_GUIDE.md"))
        assert not any(name.endswith(".lic") for name in z.namelist())
    print(f"Packaged and verified {len(files)} files, {target.stat().st_size:,} bytes: {target}")


if __name__ == "__main__":
    main()
