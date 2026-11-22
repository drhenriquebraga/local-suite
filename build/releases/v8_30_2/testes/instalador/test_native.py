"""Exercise the native installer, its offline dialog, and its responsive layout."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def main():
    here = Path(__file__).resolve().parent
    program = here.parent.parent / "programa"
    powershell = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    with tempfile.TemporaryDirectory(prefix="local-suite-ui-") as tmp:
        root = Path(tmp)
        copied = root / "programa"
        shutil.copytree(program, copied)
        script = copied / "packager/prepare.ps1"
        source = script.read_text(encoding="utf-8-sig")
        marker = "            $esperadas = @($aba0,$aba2,$aba3,$aba4)"
        assert source.count(marker) == 1
        checks = (here / "layout.ps1").read_text(encoding="utf-8-sig")
        script.write_text(source.replace(marker, checks + "\n" + marker), encoding="utf-8-sig")
        env = dict(os.environ, PSModulePath="", RADAI_PREPARADOR_AUTOTESTE="1",
                   RADAI_PREPARADOR_IDIOMA_TESTE="pt-BR", RADAI_PREPARADOR_CAPTURA="")
        for key in ("LOCALAPPDATA", "APPDATA", "RADAI_RAIZES_BUSCA"):
            path = root / key
            path.mkdir()
            env[key] = str(path)
        subprocess.run([powershell, "-NoProfile", "-STA", "-ExecutionPolicy", "Bypass",
                        "-File", script], env=env, check=True, timeout=45)


if __name__ == "__main__":
    main()
