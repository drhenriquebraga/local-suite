"""Verify provenance recorded by offline, online and code-only maintenance on Windows."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "build"))
import configurar_ambiente as cfg


def run_install_helpers(station, action):
    script = r"""
$ErrorActionPreference = 'Stop'
$tokens = $null
$errors = $null
$ast = [Management.Automation.Language.Parser]::ParseFile($env:INSTALL_SCRIPT,[ref]$tokens,[ref]$errors)
if ($errors.Count) { throw ($errors | Out-String) }
$need = @('GravarOrigemDoBundle','ConcluirOrigemDoBundle')
foreach ($d in $ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst]},$false)) {
    if ($d.Name -in $need) { . ($d.Extent.Text | ForEach-Object { [ScriptBlock]::Create($_) }) }
}
. $env:READER_SCRIPT
$p = $env:STATION
"""
    result = subprocess.run(
        ["powershell.exe","-NoProfile","-NonInteractive","-Command", script + action],
        env={**os.environ,"STATION":str(station),"INSTALL_SCRIPT":str(ROOT/"installer/INSTALL.ps1"),
             "READER_SCRIPT":str(ROOT/"packager/BUNDLES_ESTACAO.ps1")},
        capture_output=True, text=True, errors="replace", timeout=25,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr[-1800:])
    return result.stdout.splitlines()


@unittest.skipUnless(os.name == "nt", "Windows installer")
class InstalledBundleOrigin(unittest.TestCase):
    def test_offline_pending_and_commit_record_the_original_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            station = Path(tmp)
            states = run_install_helpers(station, """
GravarOrigemDoBundle $p 'pending'
EstadoBundlePrincipal $p
ConcluirOrigemDoBundle $p $false '8.30.6'
EstadoBundlePrincipal $p
ConcluirOrigemDoBundle $p $false '8.30.6'
EstadoBundlePrincipal $p
""")
            self.assertEqual(states, ["unknown","8.30.6","8.30.6"])
            receipt = json.loads((station/"bundle-origem.json").read_bytes())
            self.assertEqual(receipt, {"schema":"local-suite/installed-bundle/1","product":"principal",
                                       "source":"offline","version":"8.30.6"})
            self.assertEqual(len(list(station.iterdir())), 1)

    def test_online_validation_and_interrupted_maintenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            station = Path(tmp)
            run_install_helpers(station, "ConcluirOrigemDoBundle $p $false '8.30.6'")
            cfg.marcar_preparo_de_dependencias(station, {5, 6, 7})
            self.assertEqual(run_install_helpers(station, "ConcluirOrigemDoBundle $p $true '8.30.16'; EstadoBundlePrincipal $p"), ["8.30.6"])
            cfg.marcar_preparo_de_dependencias(station, {4})
            self.assertEqual(run_install_helpers(station, "EstadoBundlePrincipal $p"), ["unknown"])
            self.assertEqual(run_install_helpers(station, "ConcluirOrigemDoBundle $p $true '8.30.16'; EstadoBundlePrincipal $p"), ["online"])
            receipt = json.loads((station/"bundle-origem.json").read_bytes())
            self.assertNotIn("version",receipt)
            # A portable package assembled for another station supplies no installation target.
            cfg.marcar_preparo_de_dependencias(None,None)
            self.assertEqual(json.loads((station/"bundle-origem.json").read_bytes()),receipt)

    def test_normal_entry_points(self):
        prepare = (ROOT/"packager/prepare.ps1").read_text(encoding="utf-8-sig")
        installer = (ROOT/"installer/INSTALL.ps1").read_text(encoding="utf-8-sig")
        update = (ROOT/"packager/UPDATE.ps1").read_text(encoding="utf-8-sig")
        bridge = prepare[prepare.index("function InstalarAqui {"):]
        self.assertLess(bridge.index("$versaoCarga = "),bridge.index("& $pyCarga -B $atualizarCarga"))
        self.assertLess(bridge.index("['RADAI_BUNDLE_ORIGEM'] = $versaoCarga.Trim()"),
                        bridge.index("[Diagnostics.Process]::Start($psi)"))
        self.assertIn("$versaoBundleOrigem = $env:RADAI_BUNDLE_ORIGEM",installer)
        self.assertIn('"/XF", "bundle-origem.json"',installer)
        self.assertIn('$rel -in @("bundle-origem.json"',update)
        self.assertLess(installer.index('GravarOrigemDoBundle $DESTINO \'pending\''),
                        installer.index('Start-Process -FilePath "robocopy.exe"'))
        self.assertLess(installer.index('Passo "Registrando em _instalados.json"'),
                        installer.index("ConcluirOrigemDoBundle $DESTINO"))


if __name__ == "__main__":
    unittest.main()

