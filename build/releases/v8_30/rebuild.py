"""Rebuild the Local Suite SETUP from its versioned public baseline plus source deltas."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tempfile
from zipfile import ZipFile, ZipInfo

HERE=Path(__file__).resolve().parent
def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def rebuild(baseline,output):
    baseline=Path(baseline)
    output=Path(output)
    m=json.loads((HERE/"manifest.json").read_bytes())
    if sha(baseline.read_bytes())!=m["baseline_sha256"]:
        raise ValueError("Incorrect baseline archive")
    if output.is_file():
        if sha(output.read_bytes())!=m["setup_sha256"]:
            raise FileExistsError(output)
        return
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as td:
        tmp=Path(td)/"result.zip"
        with ZipFile(baseline) as base, ZipFile(tmp,"w") as out:
            seen=set()
            for entry in m["members"]:
                name=entry["name"]
                rel=PurePosixPath(name)
                if not name or name in seen or rel.is_absolute() or '..' in rel.parts or '\\' in name or ':' in name:
                    raise ValueError("Invalid release member")
                seen.add(name)
                if entry["source"]=="baseline":
                    raw=base.read(name)
                elif entry["source"]=="delta":
                    raw=(HERE/"members"/rel).read_bytes()
                else:
                    raise ValueError("Unknown source")
                if sha(raw)!=entry["sha256"]:
                    raise ValueError("Incorrect release member "+name)
                x=ZipInfo(name,tuple(entry["time"]))
                x.create_system,x.external_attr,x.internal_attr=entry["system"],entry["external"],entry["internal"]
                x.create_version,x.extract_version=entry["create_version"],entry["extract_version"]
                out.writestr(x,raw,compress_type=entry["compression"],compresslevel=entry["level"])
        if sha(tmp.read_bytes())!=m["setup_sha256"]:
            raise ValueError("Rebuilt archive hash differs; check Python and zlib versions in the manifest")
        os.replace(tmp,output)
if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("baseline",type=Path)
    ap.add_argument("output",type=Path)
    args=ap.parse_args()
    rebuild(args.baseline,args.output)
