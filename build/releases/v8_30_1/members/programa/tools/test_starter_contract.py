"""Exercise public CMD recovery on Windows PowerShell 5.1 with synthetic ZIPs only."""
from pathlib import Path
import json
import os
import re
import subprocess
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
STARTER = ROOT / ('packager/START_HERE.cmd' if (ROOT/'packager').is_dir() else 'installer/START_HERE.cmd')
POWERSHELL = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32/WindowsPowerShell/v1.0/powershell.exe'


def recovery_script(starter=STARTER):
    lines = starter.read_text(encoding='utf-8-sig').splitlines()
    start = next(i for i, line in enumerate(lines) if ' -Command ^' in line) + 1
    body = []
    for line in lines[start:]:
        line = line.strip()
        continued = line.endswith(' ^')
        if continued:
            line = line[:-2]
        if not (line.startswith('"') and line.endswith('"')):
            raise AssertionError('Recovery must be literal, auditable PowerShell arguments.')
        body.append(line[1:-1])
        if not continued:
            break
    return '\n'.join(body)


class StarterContract(unittest.TestCase):
    def test_no_self_interpretation_and_fits_native_command_limit(self):
        data = STARTER.read_text(encoding='utf-8-sig')
        for expression in (r'\[scriptblock\]\s*::\s*Create', r'\bInvoke-Expression\b',
                           r'-EncodedCommand\b', r'RADAI_BOOTSTRAP_SELF', r'RADAI_BOOTSTRAP_POWERSHELL'):
            self.assertIsNone(re.search(expression, data, re.I), expression)
        command = recovery_script()
        self.assertLess(len(command) + 1000, 7900)
        self.assertIn('-File "%RADAI_SETUP_ENTRY%"', data)
        self.assertNotIn('$env:RADAI_BOOTSTRAP_SELF', command)

    @unittest.skipUnless(os.name == 'nt', 'Windows PowerShell 5.1 test')
    def test_renamed_archive_in_arbitrary_folder_launches_without_picker(self):
        # Explorer may materialize only the CMD. Its ZIP can have been renamed
        # and the directory may be on a USB drive or under a project folder.
        with tempfile.TemporaryDirectory(prefix="local-suite-source-") as temp:
            suite = Path(temp)
            directory = suite / "downloads elsewhere & copies"
            directory.mkdir()
            original = directory / "pesquisa (edição 2).zip"
            launcher_name = "START_HERE_TO_INSTALL_LOCAL_SUITE.cmd"
            isolated = suite / "unrelated-holder" / launcher_name
            isolated.parent.mkdir()
            isolated.write_bytes(STARTER.read_bytes())
            version = re.search(r'set "RADAI_SETUP_VERSION=([^"]+)"', STARTER.read_text()).group(1)
            sentinel = suite / "ok.txt"
            with zipfile.ZipFile(original, "w") as z:
                z.writestr(launcher_name, isolated.read_bytes())
                z.writestr("programa/entrega.txt", f"PROJETO=LOCAL_SUITE\nVERSAO={version}\n")
                z.writestr("programa/packager/prepare.ps1",
                           "[IO.File]::WriteAllText($env:RADAI_TEST_SENTINEL,'opened')")
            # An NTFS local file origin is another path used by the Windows shell.
            Path(str(isolated) + ":Zone.Identifier").write_text(
                "[ZoneTransfer]\nZoneId=1\nHostUrl=" + original.as_uri() + "\n", encoding="ascii")
            env = dict(os.environ, RADAI_TEST_SENTINEL=str(sentinel))
            try:
                answer = subprocess.run(f'"{os.environ["ComSpec"]}" /d /s /c ""{isolated}""',
                                        env=env, cwd=isolated.parent, capture_output=True,
                                        input=b'\r\n', timeout=30)
            except subprocess.TimeoutExpired:
                self.fail("The launcher waited for a picker for a known source ZIP.")
            self.assertEqual(answer.returncode, 0, answer.stdout+answer.stderr)
            self.assertEqual(sentinel.read_text(), "opened")
            self.assertNotIn(b'Locate the original', answer.stdout)

    @unittest.skipUnless(os.name == 'nt', 'Windows Shell ZIP namespace test')
    def test_explorer_folder_recovers_matching_archive_with_other_zip_open(self):
        with tempfile.TemporaryDirectory(prefix="local-suite-Explorer-") as tmp:
            folder = Path(tmp)
            launcher = folder / "START_HERE_TO_INSTALL_LOCAL_SUITE.cmd"
            launcher.write_bytes(STARTER.read_bytes())
            correct = folder / "A case-sensitive (arbitrary) file.zip"
            other = folder / "Different release.zip"
            for filename, content in ((correct, launcher.read_bytes()), (other, b"old launcher")):
                with zipfile.ZipFile(filename, "w") as z:
                    z.writestr(launcher.name, content)
            body = recovery_script()
            start = body.index("function Find-InstallerZip {")
            stop = body.index("try {\nAdd-Type -AssemblyName System.IO.Compression.FileSystem", start)
            script = folder / "explorer-case.ps1"
            script.write_text(
                "$ErrorActionPreference='Stop'\nAdd-Type -AssemblyName System.IO.Compression.FileSystem\n"
                "function Explorer-Zips { $sh=New-Object -ComObject Shell.Application; "
                "$sh.NameSpace($env:OTHER_ARCHIVE).Self.Path; $sh.NameSpace($env:EXACT_ARCHIVE).Self.Path }\n"
                + body[start:stop]
                + "\n$r=Find-InstallerZip; if($null -eq $r){exit 2}; "
                "try{if($r.Path -ne $env:EXACT_ARCHIVE){exit 3}}finally{$r.Zip.Dispose()}",
                encoding="utf-8-sig")
            env = dict(os.environ, RADAI_SETUP_LAUNCHER=str(launcher), EXACT_ARCHIVE=str(correct),
                       OTHER_ARCHIVE=str(other))
            got = subprocess.run([str(POWERSHELL), "-NoProfile", "-STA", "-ExecutionPolicy", "Bypass",
                                  "-File", str(script)], env=env, capture_output=True, timeout=20)
            self.assertEqual(got.returncode, 0, got.stdout+got.stderr)

    @unittest.skipUnless(os.name == 'nt', 'Windows PowerShell 5.1 test')
    def test_real_cmd_and_zip_recovery_preserve_payload_output_and_exit(self):
        product = re.search(r'set "RADAI_SETUP_PRODUCT=([^"]+)"', STARTER.read_text()).group(1)
        version = re.search(r'set "RADAI_SETUP_VERSION=([^"]+)"', STARTER.read_text()).group(1)
        relative = re.search(r'set "RADAI_SETUP_RELATIVE=([^"]+)"', STARTER.read_text()).group(1)
        with tempfile.TemporaryDirectory(prefix="installer-'quote' & ") as temp:
            folder = Path(temp)
            root = folder/'extracted'; payload = root/'programa'
            payload.mkdir(parents=True)
            if product == 'local-suite':
                (payload/'entrega.txt').write_text(f'PROJETO=LOCAL_SUITE\nVERSAO={version}\n')
            else:
                (payload/'release-manifest.json').write_text(json.dumps({'schema': product+'/release-package/1', 'plugin_id': product}))
            entry = payload/relative.replace('\\', '/')
            entry.parent.mkdir(parents=True, exist_ok=True)
            entry.write_text("[IO.File]::WriteAllText($env:RADAI_TEST_SENTINEL,'native ran');Write-Host 'Visible native progress';[Console]::Error.WriteLine('Visible stderr progress');exit ([int]$env:RADAI_TEST_EXIT)")
            starter = root/'START_HERE.cmd'; starter.write_bytes(STARTER.read_bytes())
            sentinel = folder/'sentinel.txt'
            env = {**os.environ, 'RADAI_TEST_SENTINEL': str(sentinel), 'RADAI_TEST_EXIT': '0', 'RADAI_SETUP_PRODUCT': product, 'RADAI_SETUP_VERSION': version, 'RADAI_SETUP_RELATIVE': relative, 'RADAI_SETUP_POWERSHELL': str(POWERSHELL)}
            # The ordinary extracted route invokes the named .ps1 directly.
            result = subprocess.run(f'"{os.environ["ComSpec"]}" /d /s /c ""{starter}""', env=env, capture_output=True, text=True, input='\n', timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            self.assertEqual(sentinel.read_text(), 'native ran')
            self.assertIn('Visible native progress', result.stdout)
            self.assertIn('Visible stderr progress', result.stderr)
            # Execute the exact literal recovery command from a normal test .ps1.
            # Only the file-picker function is replaced; there is no production override.
            body = recovery_script()
            first = body.index('function Select-InstallerZip {')
            last = body.index('function SafePath(', first)
            def invoke(archive, code=0):
                picker = 'function Select-InstallerZip { ' + ('return $null' if archive is None else "return '"+str(archive).replace("'", "''")+"'") + ' }\n'
                script = folder/'recovery-test.ps1'; script.write_text(body[:first]+picker+body[last:], encoding='utf8')
                if sentinel.exists(): sentinel.unlink()
                return subprocess.run([str(POWERSHELL), '-NoLogo', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(script)], env={**env, 'RADAI_TEST_EXIT': str(code)}, capture_output=True, text=True, timeout=30)
            for wrapper, slash in (('', '/'), ('outer/', '\\')):
                archive = folder/('complete'+str(len(wrapper))+'.zip')
                with zipfile.ZipFile(archive, 'w') as z:
                    for path in root.rglob('*'):
                        if path.is_file(): z.write(path, (wrapper+path.relative_to(root).as_posix()).replace('/', slash))
                if not wrapper:
                    partial=folder/'isolated ZIP launcher';partial.mkdir()
                    cmdtext=STARTER.read_text(encoding='utf-8-sig')
                    firstcmd=cmdtext.index('  "function Select-InstallerZip {')
                    lastcmd=cmdtext.index('  "function SafePath(', firstcmd)
                    pickerline='  "function Select-InstallerZip { return '+"'"+str(archive).replace("'", "''")+"'"+' }" ^\n'
                    isolated=partial/'START_HERE.cmd'
                    isolated.write_text(cmdtext[:firstcmd]+pickerline+cmdtext[lastcmd:], encoding='utf8')
                    result=subprocess.run(f'"{os.environ["ComSpec"]}" /d /s /c ""{isolated}""', env=env, capture_output=True, text=True, input='\n', timeout=30)
                    self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                    self.assertEqual(sentinel.read_text(),'native ran')
                    self.assertEqual(result.stdout.count('Extracting:'),1)
                result = invoke(archive)
                self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
                self.assertEqual(sentinel.read_text(), 'native ran')
                self.assertEqual(result.stdout.count('Extracting:'), 1)
                self.assertIn('Visible stderr progress', result.stderr)
                result = invoke(archive, 17)
                self.assertEqual(result.returncode, 17, result.stdout+result.stderr)
            result = invoke(None)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            self.assertFalse(sentinel.exists())
            for invalid in ('../escape.ps1', 'code/CON.txt', 'code/a:stream', 'code/a/../b', '/absolute'):
                archive=folder/'invalid.zip'
                with zipfile.ZipFile(archive, 'w') as z: z.writestr(invalid, 'never execute')
                result=invoke(archive)
                self.assertEqual(result.returncode, 1, invalid+' '+result.stdout+result.stderr)
                self.assertFalse(sentinel.exists())
            archive=folder/'wrong.zip'
            with zipfile.ZipFile(archive,'w') as z: z.writestr('programa/release-manifest.json', '{}')
            result=invoke(archive)
            self.assertEqual(result.returncode,1,result.stdout+result.stderr)
            self.assertIn('This ZIP is not the selected installer', result.stdout)
            self.assertFalse(sentinel.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
