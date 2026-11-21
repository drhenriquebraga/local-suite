"""Exercise the installer using a disposable copy of an older application and existing test weights.

Run with --previous-zip and --runtime-root pointing to a verified, offline test assembly.
No user station or user license receipt is used.
"""
import argparse
from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch
from zipfile import ZipFile


PROGRAM = Path(__file__).resolve().parents[1] / "programa"
sys.path.insert(0, str(PROGRAM / "build"))
import configurar_ambiente as install
import consentimento_instalador


def unpack_old(archive, station):
    with ZipFile(archive) as previous:
        for name in previous.namelist():
            if name.startswith("programa/app/"):
                rel = Path(name.removeprefix("programa/app/"))
            elif name in ("programa/entrega.txt", "programa/VERSION.txt"):
                rel = Path(name).name
            else:
                continue
            if name.endswith("/"):
                continue
            target = station / rel
            assert target.resolve().is_relative_to(station)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(previous.read(name))


def require(condition, text):
    if not condition:
        raise AssertionError(text)
    print("PASS", text, flush=True)


def run(previous, runtime):
    cache_root = Path(tempfile.gettempdir()).resolve()
    with tempfile.TemporaryDirectory(dir=cache_root, prefix="upgrade-") as temp:
        station = Path(temp).resolve()
        assert station.parent == cache_root
        links = []
        try:
            unpack_old(previous, station)
            for name in ("python", "ts_weights", "modelos"):
                src, dst = (runtime / name).resolve(), station / name
                assert src.is_dir() and not dst.exists()
                subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", dst, src],
                               check=True, stdout=subprocess.DEVNULL)
                links.append(dst)
            py = station / "python" / "python.exe"
            identities = ("entrega.txt", "VERSION.txt", "_requisitos.json", "plugins.txt")
            settings = {"nomes_proprios.json": b'{"active":true}', "protocolos_proprios.json": b'{"user":"qa"}',
                        "radai_watcher.config.json": b'{"port":7142}', "idioma.txt": b"de"}
            for key, value in settings.items():
                (station / key).write_bytes(value)
            for key in identities:
                if not (station / key).exists():
                    (station / key).write_bytes(b"old receipt")
            old_stamps = {k: (station / k).read_bytes() for k in identities}
            probe = ("import sys; sys.path.insert(0,sys.argv[1]); "
                     "import radai_batch, radai_rocards_worker")
            old = subprocess.run([py, "-B", "-c", probe, str(station)], capture_output=True)
            require(old.returncode and b"No module named 'radai_rocards_worker'" in old.stderr,
                    "reproduced exact 8.30 validation failure from the released old app")

            # Force a destination-import failure after publishing the code. Stamps, code and old
            # data must survive, and additions including a new worker must disappear.
            work = station / install.OFICINA_NO_LUGAR
            work.mkdir()
            project, version, product = install.ler_entrega(PROGRAM)
            ctx = dict(bundle=station, py=py, destino=work, projeto=project, versao=version,
                       produto=product, instalar=str(station), profile="full", cache=work / "cache",
                       so_cpu=False, cuda="cu121", modelos_omitidos=())
            old_batch = (station / "radai_batch.py").read_bytes()
            help_asset = station / "data" / "ajuda-tasks" / install._FIGURAS_ANTIGAS[0]
            help_asset.parent.mkdir(parents=True, exist_ok=True)
            help_asset.write_bytes(b"old asset")
            with patch.object(install, "validar_codigo_instalado", side_effect=[None, OSError("injected")]), \
                    redirect_stdout(io.StringIO()):
                try:
                    install.etapa_app(ctx)
                except OSError as exc:
                    assert str(exc) == "injected"
                else:
                    raise AssertionError("injected destination failure was ignored")
            require(not (station / "radai_rocards_worker.py").exists() and
                    (station / "radai_batch.py").read_bytes() == old_batch and help_asset.read_bytes() == b"old asset",
                    "an import failure rolls back code additions, replacements and removed help assets")
            with patch.object(install, "conferir_recorte_no_corpo"), patch.object(install, "conferir_modelos_exigidos"), \
                    patch.object(install, "_escrever_manifesto", side_effect=OSError("injected")), \
                    redirect_stdout(io.StringIO()):
                try:
                    install.etapa_finalizar_no_lugar(ctx)
                except OSError as exc:
                    assert str(exc) == "injected"
                else:
                    raise AssertionError("injected manifest failure was ignored")
            require(all((station / k).read_bytes() == v for k, v in old_stamps.items()),
                    "a failed manifest leaves all previous version receipts intact")
            # Simulate authorization only inside this test process. The real full install stages
            # below use the production motor and run its real subprocesses and integrity checks.
            with patch.object(consentimento_instalador, "exigir", return_value=set()), \
                    patch.object(install, "etapa_runtime", side_effect=AssertionError("attempted download")), \
                    patch.object(install, "etapa_pesos", side_effect=AssertionError("attempted download")):
                rc = install.main(["--instalar", str(station), "--etapas", "5"])
            require(rc == 0, "the old log's --etapas 5 completes the real installation recovery")
            require(all((station / k).read_bytes() == v for k, v in settings.items()),
                    "custom names, protocols, configuration and language are preserved byte for byte")
            require((station / "VERSION.txt").read_bytes() == (PROGRAM / "VERSION.txt").read_bytes() and
                    install.ler_entrega(station) == install.ler_entrega(PROGRAM) and
                    (station / "MANIFESTO.txt").stat().st_size > 1024,
                    "new application version and model manifest are consistent")
            require((station / "radai_rocards_worker.py").read_bytes() ==
                    (PROGRAM / "app" / "radai_rocards_worker.py").read_bytes() and not help_asset.exists(),
                    "the exact worker from the setup and current help assets are installed")
        finally:
            if install.LOG:
                install.LOG.close()
                install.LOG = None
            for junction in links:
                assert junction.parent == station
                os.rmdir(junction)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--previous-zip", type=Path, required=True)
    p.add_argument("--runtime-root", type=Path, required=True)
    args = p.parse_args()
    run(args.previous_zip, args.runtime_root)
