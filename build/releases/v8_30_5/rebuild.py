"""Rebuild the public Windows SETUP using its versioned baseline and manifest."""

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tempfile
from zipfile import ZipFile, ZipInfo


RELEASE = Path(__file__).resolve().parent


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def rebuild(baseline, output):
    manifest = json.loads((RELEASE / "manifest.json").read_bytes())
    if digest(baseline) != manifest["baseline_sha256"]:
        raise ValueError("The baseline archive differs from the version in the manifest")
    if output.exists():
        if digest(output) != manifest["setup_sha256"]:
            raise FileExistsError(output)
        return

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as work:
        temporary = Path(work) / "rebuilt.zip"
        with ZipFile(baseline) as original, ZipFile(temporary, "w") as target:
            seen = set()
            for entry in manifest["members"]:
                name = entry["name"]
                relative = PurePosixPath(name)
                if (not name or name in seen or relative.is_absolute() or ".." in relative.parts
                        or "\\" in name or ":" in name):
                    raise ValueError(f"Invalid release member: {name}")
                seen.add(name)
                if entry["source"] == "baseline":
                    data = original.read(name)
                elif entry["source"] == "delta":
                    data = (RELEASE / "members" / relative).read_bytes()
                else:
                    raise ValueError(f"Unknown source for {name}")
                if hashlib.sha256(data).hexdigest() != entry["sha256"]:
                    raise ValueError(f"Incorrect member digest for {name}")

                member = ZipInfo(name, tuple(entry["time"]))
                member.create_system = entry["system"]
                member.create_version = entry["create_version"]
                member.extract_version = entry["extract_version"]
                member.external_attr = entry["external"]
                member.internal_attr = entry["internal"]
                target.writestr(member, data, compress_type=entry["compression"], compresslevel=entry["level"])

        if digest(temporary) != manifest["setup_sha256"] or temporary.stat().st_size != manifest["bytes"]:
            raise ValueError(f"Rebuild with Python {manifest['python']} and zlib {manifest['zlib']}")
        os.replace(temporary, output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    rebuild(args.baseline, args.output)
