"""Create the same local Downloads archive as the portable workstation tool."""
import os
from pathlib import Path
import re
import subprocess
import threading


_BUSY = threading.Lock()
_NAME = re.compile(r"LocalSuite-Diagnostico-\d{8}T\d{6}Z-[a-f0-9]{8}\.zip", re.ASCII | re.IGNORECASE)


def installation_root():
    here = Path(__file__).resolve().parent
    if here.name == "app" and (here.parent / "entrega.txt").is_file():
        return here.parent
    return here


def collect(root=None, downloads=None):
    if not _BUSY.acquire(blocking=False):
        return {"ok": False, "code": "BUSY"}
    try:
        from radai_bridge_entrada import pasta_downloads

        root = Path(root) if root is not None else installation_root()
        target = Path(downloads if downloads is not None else pasta_downloads())
        script = root / "tools" / "Diagnostico-Local-Suite.ps1"
        shell = Path(os.environ["SystemRoot"]) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
        result = subprocess.run(
            [str(shell), "-NoLogo", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-File", str(script), "-InstallRoot", str(root), "-OutputDir", str(target), "-Quiet"],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            timeout=75, creationflags=subprocess.CREATE_NO_WINDOW, check=False,
        )
        filename = result.stdout.decode("ascii", errors="replace").strip()
        if result.returncode or not _NAME.fullmatch(filename) or not (target / filename).is_file():
            return {"ok": False, "code": "WRITE_FAILED"}
        return {"ok": True, "file": filename}
    except (OSError, KeyError, subprocess.TimeoutExpired):
        return {"ok": False, "code": "WRITE_FAILED"}
    finally:
        _BUSY.release()

