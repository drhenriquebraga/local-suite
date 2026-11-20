"""Create the same local Downloads archive as the portable workstation tool."""
import os
from pathlib import Path
import re
import subprocess
import threading


import json
import time
import uuid


PROFILE_ROOT = Path("C:/RADIOTERAPIA_AI")
START_ID = "RADAI_PERFIL_ABERTURA"
START_NS = "RADAI_PERFIL_ABERTURA_NS"
_USE_LOCK = threading.Lock()
_USE_EVENTS = ("clique", "janela_aberta", "painel_pronto", "selecao_aceita", "primeira_imagem", "motor_apto")


def _use_folder():
    value = os.environ.get("RADAI_DESEMPENHO_DIR")
    path = Path(value) if value else PROFILE_ROOT / "LOCAL_SUITE/calibracao/desempenho"
    path = path.resolve()
    if not path.is_relative_to(PROFILE_ROOT.resolve()) or path == PROFILE_ROOT.resolve():
        raise ValueError("Invalid local performance folder")
    import radai_archive
    if radai_archive.em_pasta_sincronizada(str(path))[0]:
        raise ValueError("Synchronized performance folder")
    return path


def start_profile(start_ns=None):
    return {START_ID: uuid.uuid4().hex, START_NS: str(start_ns or time.monotonic_ns())}


def use_event(event, environment=None, now_ns=None):
    """Record the first occurrence only. A missing event stays missing on failure."""
    environment = os.environ if environment is None else environment
    token = environment.get(START_ID, "")
    if event not in _USE_EVENTS or not re.fullmatch(r"[0-9a-f]{32}", token):
        return False
    try:
        elapsed = (time.monotonic_ns() if now_ns is None else now_ns) - int(environment[START_NS])
        if elapsed < 0:
            return False
        with _USE_LOCK:
            path = _use_folder() / ("abertura-" + token + ".json")
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.is_file():
                old = json.loads(path.read_bytes())
                marks = {k: old["marcos_ms"][k] for k in _USE_EVENTS
                         if type(old.get("marcos_ms", {}).get(k)) is int}
            else:
                marks = {}
            if event in marks:
                return True
            marks[event] = 0 if event == "clique" else round(elapsed / 1_000_000)
            tmp = path.with_suffix(".json." + uuid.uuid4().hex + ".part")
            try:
                with tmp.open("x", encoding="ascii") as output:
                    json.dump({"schema": "local-suite.abertura/1", "marcos_ms": marks}, output)
                os.replace(tmp, path)
            finally:
                tmp.unlink(missing_ok=True)
        return True
    except (OSError, ValueError, TypeError, KeyError, ImportError, RuntimeError):
        return False


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

