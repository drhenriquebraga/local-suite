"""Exercise the actual packaged START from the Explorer ZIP route on Windows.

Usage: python -B test_starter_public_zip.py <verified-suite-setup.zip>
The preparer runs only its offline UI self-test, with scratch user settings.
"""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile

from test_starter_contract import POWERSHELL, recovery_script


LAUNCHER = "START_HERE_TO_INSTALL_LOCAL_SUITE.cmd"
SUITE = "RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_"
APP = Path(__file__).resolve().parents[1]
PUBLIC_8315_SHA = "fc0bd3dc84f6f436dc4bc0e61a87e7259db41a8bce191f48cdf8f11a9d3cbc0f"


def run_process(command, env, cwd):
    with subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT) as child:
        try:
            stdout = child.communicate(b"\r\n", timeout=75)[0]
        except subprocess.TimeoutExpired:
            # A picker left open is a failure. Close the isolated test's process tree.
            if child.poll() is None:
                subprocess.run(["taskkill", "/pid", str(child.pid), "/t", "/f"], capture_output=True)
            child.communicate()
            raise AssertionError("The ZIP launcher waited for input instead of opening the test preparer.") from None
    return child.returncode, stdout.decode("mbcs", errors="replace")


@contextlib.contextmanager
def isolated(setup):
    with tempfile.TemporaryDirectory(prefix="Local Suite ZIP test ") as temporary:
        root = Path(temporary)
        shipping = root / "offline media & copies"
        shipping.mkdir()
        isolated_dir = root / "Temp1_clicked.zip"
        isolated_dir.mkdir()
        with zipfile.ZipFile(setup) as z:
            launcher = isolated_dir / LAUNCHER
            launcher.write_bytes(z.read(LAUNCHER))
            entrega = dict(line.split("=", 1) for line in z.read("programa/entrega.txt")
                           .decode("utf-8-sig").splitlines() if "=" in line)
        paths = {name: str(root / name) for name in ("TEMP", "TMP", "APPDATA", "LOCALAPPDATA")}
        for name in paths.values():
            Path(name).mkdir()
        env = dict(os.environ, **paths, RADAI_SETUP_OFFLINE="1", RADAI_URL_VERSOES="0",
                   RADAI_PREPARADOR_AUTOTESTE="1", RADAI_PREPARADOR_IDIOMA_TESTE="pt-BR",
                   RADAI_LOG_PREPARADOR="bateria")
        for name in ("RADAI_PREPARADOR_CAPTURA", "RADAI_ATUALIZAR_APP", "RADAI_ATUALIZAR_APP_DE"):
            env.pop(name, None)
        yield root, shipping, launcher, entrega["VERSAO"], env


def cmd_from_explorer(launcher, source, env):
    # The local shell can carry the original ZIP path in an NTFS origin stream.
    Path(str(launcher) + ":Zone.Identifier").write_text(
        "[ZoneTransfer]\nZoneId=1\nHostUrl=" + source.as_uri() + "\n", encoding="ascii")
    return run_process(f'"{os.environ["ComSpec"]}" /d /s /c ""{launcher}""', env, launcher.parent)


def expect_opened(result, filename):
    code, output = result
    if code != 0 or "PASS: Native installer flow and layout" not in output:
        raise AssertionError(output)
    selected = [line.strip() for line in output.splitlines() if line.startswith("Extracting: ")]
    if len(selected) != 1 or Path(selected[0][len("Extracting: "):]).name != filename:
        raise AssertionError("Expected the clicked ZIP to be extracted once: " + repr(selected))


def with_sources(launcher, paths, manual, env):
    # Run the real recovery logic extracted from the release. Substitute only the
    # two desktop input providers so ordering and a manual choice are deterministic.
    body = recovery_script(launcher)
    picker_start = body.index("function Select-InstallerZip {")
    picker_end = body.index("function SafePath(", picker_start)
    body = body[:picker_start] + "function Select-InstallerZip { return $env:SUITE_TEST_MANUAL }\n" + body[picker_end:]
    shell_start = body.index("function Explorer-Zips {")
    shell_end = body.index("function Find-InstallerZip {", shell_start)
    # Preserve all helper functions between the Explorer provider and the matcher.
    shell_body = body[shell_start:shell_end]
    first_end = shell_body.index("\n}\n") + len("\n}\n")
    body = (body[:shell_start] + "function Explorer-Zips { Get-Content -LiteralPath $env:SUITE_TEST_SOURCES -Encoding UTF8 }\n"
            + shell_body[first_end:] + body[shell_end:])
    src = launcher.parent / "candidates.txt"
    src.write_text("\n".join(map(str, paths)), encoding="utf-8-sig")
    script = launcher.parent / "verify recovery.ps1"
    script.write_text(body, encoding="utf-8-sig")
    variables = dict(re.findall(r'^set "(RADAI_SETUP_(?:VERSION|RELATIVE|PRODUCT))=([^"\r\n]+)"',
                                launcher.read_text(encoding="utf-8-sig"), flags=re.M | re.I))
    env = dict(env, **variables, RADAI_SETUP_LAUNCHER=str(launcher), RADAI_SETUP_POWERSHELL=str(POWERSHELL),
               SUITE_TEST_SOURCES=str(src), SUITE_TEST_MANUAL=str(manual or ""))
    # A manual-picker test has no active shell paths or other real filesystem hints.
    if not paths:
        body = script.read_text(encoding="utf-8-sig")
        marker = "$located=Find-InstallerZip;"
        if body.count(marker) != 1:
            raise AssertionError("Recovery entry point changed. Update the picker-only test.")
        script.write_text(body.replace(marker, "$located=$null;"), encoding="utf-8-sig")
    return run_process([str(POWERSHELL), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-STA",
                        "-File", str(script)], env, launcher.parent)


def check(setup, reproduce):
    if os.name != "nt":
        raise SystemExit("Windows PowerShell 5.1 and NTFS are required.")
    if reproduce:
        if hashlib.sha256(setup.read_bytes()).hexdigest() != PUBLIC_8315_SHA:
            raise AssertionError("The baseline is not the public 8.30.15 artifact.")
    else:
        with zipfile.ZipFile(setup) as z:
            if z.read("programa/packager/prepare.ps1") != (APP / "packager/prepare.ps1").read_bytes():
                raise AssertionError("Verify the final ZIP from the source tree of the same release.")
    with isolated(setup) as (root, media, launcher, version, env):
        named = media / f"{SUITE}v{version}.zip"
        shutil.copyfile(setup, named)
        result = cmd_from_explorer(launcher, named, env)
        if reproduce:
            code, output = result
            if code == 0 or "This ZIP is not the selected installer" not in output or "Opening Local Suite" in output:
                raise AssertionError(output)
            print("PASS: reproduced the published 8.30.15 ZIP rejection before extraction.")
            return
        expect_opened(result, named.name)
        print("PASS: native versioned ZIP opened offline from its extracted CMD.")
        latest = media / f"{SUITE}LATEST.zip"
        shutil.copyfile(named, latest)
        expect_opened(cmd_from_explorer(launcher, latest, env), latest.name)
        renamed = media / "Local Suite (copia 2).zip"
        shutil.copyfile(named, renamed)
        expect_opened(cmd_from_explorer(launcher, renamed, env), renamed.name)
        print("PASS: native LATEST and a renamed copy opened offline in paths with spaces.")
        wrong = media / "another version with same launcher.zip"
        with zipfile.ZipFile(wrong, "w") as z:
            z.writestr(LAUNCHER, launcher.read_bytes())
            z.writestr("programa/entrega.txt", "PROJETO=LOCAL_SUITE\nVERSAO=0.0.1\n")
            z.writestr("programa/packager/prepare.ps1", "throw 'Wrong candidate was executed'")
        unrelated = media / "NEURO RT.zip"
        with zipfile.ZipFile(unrelated, "w") as z:
            z.writestr("programa/release-manifest.json", json.dumps({"plugin_id": "neuro-rt"}))
        for correct in (named, latest):
            expect_opened(with_sources(launcher, [wrong, unrelated, correct], None, env), correct.name)
        print("PASS: wrong version (identical CMD bytes) and unrelated plugin skipped before both matching aliases.")
        for candidate in (wrong, unrelated):
            code, out = with_sources(launcher, [], candidate, env)
            if code == 0 or "Opening Local Suite" in out or "Extracting:" in out or "Setup stopped:" not in out:
                raise AssertionError(out)
        print("PASS: wrong version and unrelated package rejected before extraction in manual mode.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("setup", type=Path)
    parser.add_argument("--reproduce-8315", action="store_true")
    args = parser.parse_args()
    check(args.setup.resolve(strict=True), args.reproduce_8315)
