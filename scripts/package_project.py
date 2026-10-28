"""Package reviewable sources/results without runtimes, caches or credentials."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = ["sequin", "tests", "scripts", "data", "reproduction", "output"]
DOCUMENTS = ["README.md", "IMPLEMENTATION_NOTES.md", "SEQUIN_PROJECT_BLUEPRINT.md", "pyproject.toml",
             "requirements-lock.txt", "requirements-reproduction-lock.txt", ".gitignore"]
EXCLUDED = {"__pycache__", ".pytest_cache", "original_probe", "original_quick_probe"}


def main():
    files = [ROOT / name for name in DOCUMENTS]
    for directory in DIRECTORIES:
        files.extend(p for p in (ROOT / directory).rglob("*") if p.is_file()
                     and not any(part in EXCLUDED for part in p.relative_to(ROOT).parts)
                     and p.suffix.lower() not in {".pyc", ".lic", ".log"})
    files = sorted(set(files))
    manifest = {"files": [{"path": p.relative_to(ROOT).as_posix(), "bytes": p.stat().st_size,
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in files],
                "excluded": "Python/Julia runtimes and caches, temporary logs, license files, early failed export trials",
                "scientific_status": "See output/reproduction/REPRODUCTION_REPORT.md; full native reproduction is incomplete"}
    target = ROOT / "SEQUIN_Project.zip"
    with ZipFile(target, "w", ZIP_DEFLATED, compresslevel=7) as archive:
        for p in files:
            archive.write(p, p.relative_to(ROOT).as_posix())
        archive.writestr("PACKAGE_MANIFEST.json", json.dumps(manifest, indent=2))
    with ZipFile(target) as archive:
        assert archive.testzip() is None, "Archive integrity failure"
        names = archive.namelist()
        assert "output/reproduction/coverage.json" in names
        assert not any(name.endswith(".lic") or name.startswith((".venv/", ".tools/", "tmp/")) for name in names)
        for panel in json.loads((ROOT / "output/reproduction/author_reference/manifest.json").read_text())["panels"]:
            assert "output/reproduction/author_reference/" + panel["image"] in names
    print(f"Packaged and verified {len(files)} files; {target.stat().st_size:,} bytes: {target}")


if __name__ == "__main__":
    main()
