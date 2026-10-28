"""Download public original-source/cache layers; optionally install portable Julia.

No Docker service, system installation, or academic credentials are required.
Downloaded archives are verified and extracted as ordinary files only.
"""

import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile
import urllib.request
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
REPO = "andrewgchio/iccps-sequin"


def fetch(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=120) as response:
        return response.read()


def safe_target(root, name):
    target = (root / name).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError(f"Unsafe archive path: {name}")
    return target


def prepare_sources():
    record = json.loads(fetch("https://zenodo.org/api/records/14836525"))
    archive = record["files"][0]
    data = fetch(archive["links"]["self"])
    expected = archive.get("checksum", "")
    if expected.startswith("md5:") and hashlib.md5(data).hexdigest() != expected[4:]:
        raise ValueError("Archived source checksum mismatch")
    archive_root = ROOT / "third_party/reference_artifact"
    archive_root.mkdir(parents=True, exist_ok=True)
    with ZipFile(io.BytesIO(data)) as zipped:
        for name in zipped.namelist():
            safe_target(archive_root, name)
        zipped.extractall(archive_root)
    manifest = next(archive_root.glob("*/Manifest.toml"))
    token = json.loads(fetch("https://auth.docker.io/token?service=registry.docker.io&scope=repository:" + REPO + ":pull"))["token"]
    headers = {"Authorization": "Bearer " + token,
               "Accept": "application/vnd.docker.distribution.manifest.v2+json, application/vnd.docker.distribution.manifest.list.v2+json, application/vnd.oci.image.index.v1+json"}
    base = "https://registry-1.docker.io/v2/" + REPO + "/"
    image = json.loads(fetch(base + "manifests/v1.0.3", headers))
    if "manifests" in image:
        chosen = next(x for x in image["manifests"] if x.get("platform", {}).get("architecture") == "amd64"
                      and x.get("platform", {}).get("os") == "linux")
        image = json.loads(fetch(base + "manifests/" + chosen["digest"], headers))
    config = json.loads(fetch(base + "blobs/" + image["config"]["digest"], headers))
    history = [x for x in config["history"] if not x.get("empty_layer")]
    out = ROOT / "reproduction/docker_reference"
    out.mkdir(parents=True, exist_ok=True)
    provenance = []
    for index, (layer, step) in enumerate(zip(image["layers"], history)):
        command = step.get("created_by", "")
        if not command.startswith("COPY ") or layer["size"] > 5_000_000:
            continue
        raw = fetch(base + "blobs/" + layer["digest"], headers)
        if "sha256:" + hashlib.sha256(raw).hexdigest() != layer["digest"]:
            raise ValueError("Docker layer digest mismatch")
        count = 0
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tar:
            for member in tar:
                name = member.name.lstrip("./")
                if not member.isfile() or not name.startswith("iccps-sequin/"):
                    continue
                relative = Path(name).relative_to("iccps-sequin")
                target = safe_target(out, relative)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(tar.extractfile(member).read())
                count += 1
        provenance.append({"layer": index, "digest": layer["digest"], "files": count})
    (out / "Manifest.toml").write_bytes(manifest.read_bytes())
    (out / "PROVENANCE.json").write_text(json.dumps({"image": REPO + ":v1.0.3", "layers": provenance,
         "zenodo_source_sha256": hashlib.sha256(data).hexdigest(),
         "manifest_source": "Zenodo archived v1.0.2 manifest; source/cache from Docker v1.0.3"}, indent=2), encoding="utf-8")
    print("Prepared", out)


def install_julia():
    name = "julia-1.9.2-win64.zip"
    checksum = fetch("https://julialang-s3.julialang.org/bin/checksums/julia-1.9.2.sha256").decode()
    expected = next(line.split()[0] for line in checksum.splitlines() if line.split()[-1] == name)
    out = ROOT / ".tools"
    out.mkdir(exist_ok=True)
    archive = out / name
    if not archive.exists():
        req = urllib.request.Request("https://julialang-s3.julialang.org/bin/winnt/x64/1.9/" + name)
        partial = archive.with_suffix(".part")
        with urllib.request.urlopen(req, timeout=120) as response, partial.open("wb") as target:
            size = 0
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > 500_000_000:
                    raise ValueError("Unexpected runtime archive size")
                target.write(chunk)
        partial.replace(archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
        raise ValueError("Julia checksum mismatch")
    with ZipFile(archive) as zipped:
        for name in zipped.namelist():
            safe_target(out, name)
        zipped.extractall(out)
    print("Prepared checksum-verified Julia 1.9.2")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--julia", action="store_true", help="Also download Windows Julia 1.9.2 locally")
    args = parser.parse_args()
    prepare_sources()
    if args.julia:
        install_julia()
