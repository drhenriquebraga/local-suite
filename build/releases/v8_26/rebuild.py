"""Rebuild the published Local Suite 8.26 SETUP from its 8.25.1 baseline."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


HERE = Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def rebuild(base_path, output_path):
    manifest = json.loads((HERE / "manifest.json").read_bytes())
    if digest(base_path.read_bytes()) != manifest["baseline_sha256"]:
        raise ValueError("The supplied ZIP is not the published 8.25.1 SETUP.")
    if output_path.exists():
        if digest(output_path.read_bytes()) == manifest["setup_sha256"]:
            return
        raise FileExistsError(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output_path.parent) as temporary:
        assembled = Path(temporary) / "setup.zip"
        with ZipFile(base_path) as baseline, ZipFile(assembled, "w") as result:
            for name, source in sorted(manifest["files"].items()):
                rel = PurePosixPath(name)
                if rel.is_absolute() or ".." in rel.parts or "\\" in name or ":" in name:
                    raise ValueError("Unsafe release member")
                if source["from"] == "baseline":
                    data = baseline.read(name)
                elif source["from"] == "delta":
                    data = (HERE / "members" / rel).read_bytes()
                else:
                    raise ValueError("Unknown source for " + name)
                if digest(data) != source["sha256"]:
                    raise ValueError("Digest mismatch for " + name)
                entry = ZipInfo(name, (2026, 11, 18, 0, 0, 0))
                entry.create_system = 3
                entry.external_attr = 0o100644 << 16
                result.writestr(entry, data, ZIP_DEFLATED, compresslevel=6)
        if digest(assembled.read_bytes()) != manifest["setup_sha256"]:
            raise ValueError("Rebuilt archive differs from the published archive. Use the compression library listed in manifest.json.")
        assembled.replace(output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    rebuild(arguments.baseline, arguments.output)
