"""Exercise Continue and the installer home while station discovery is blocked."""
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest


@unittest.skipUnless(os.name == "nt", "requires the Windows desktop")
class PreparerStartup(unittest.TestCase):
    def test_operator_can_open_home_before_inventory_finishes(self):
        user32 = ctypes.windll.user32
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
        user32.GetWindow.restype = wintypes.HWND

        def window(parent, prefix):
            matches = []

            @callback_type
            def visit(hwnd, _):
                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value == process.pid and user32.IsWindowVisible(hwnd):
                    title = ctypes.create_unicode_buffer(256)
                    user32.GetWindowTextW(hwnd, title, len(title))
                    if title.value.startswith(prefix):
                        matches.append(hwnd)
                return True

            if parent:
                user32.EnumChildWindows(parent, visit, 0)
            else:
                user32.EnumWindows(visit, 0)
            return matches[0] if matches else None

        def wait_for(label, predicate):
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                value = predicate()
                if value:
                    return value
                self.assertIsNone(process.poll(), label + ": installer exited")
                time.sleep(0.05)
            self.fail(label + ": timed out")

        program = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix="suite startup ") as tmp:
            root = Path(tmp)
            shutil.copytree(program / "packager", root / "packager")
            script = root / "packager/prepare.ps1"
            source = script.read_text(encoding="utf-8-sig")
            entry = "function AcharInstalacao {"
            self.assertEqual(source.count(entry), 1)
            # Block only the filesystem operation in the temporary test copy.
            gate = """
                [IO.File]::WriteAllText((Join-Path $env:TEMP 'probe-started'), '')
                while (-not [IO.File]::Exists((Join-Path $env:TEMP 'release'))) {
                    Start-Sleep -Milliseconds 40
                }
                return $null
            """
            script.write_text(source.replace(entry, entry + gate), encoding="utf-8-sig")
            env = {key: val for key, val in os.environ.items() if not key.startswith("RADAI_")}
            env.update({key: tmp for key in ("TEMP", "TMP", "LOCALAPPDATA", "APPDATA")})
            env.update(RADAI_SETUP_OFFLINE="1", RADAI_RAIZES_BUSCA=tmp, PSModulePath="")
            process = subprocess.Popen(
                ["powershell.exe", "-NoProfile", "-STA", "-ExecutionPolicy", "Bypass", "-File", str(script)],
                env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            )
            try:
                language = wait_for("visible language selector", lambda: window(None, "Select language"))
                self.assertTrue(user32.GetWindow(language, 4), "language selector must have an owner")
                button = wait_for("Continue", lambda: window(language, "Continue"))
                started = root / "probe-started"
                self.assertFalse(started.exists(), "inventory began before the language choice")
                self.assertTrue(user32.PostMessageW(button, 0x00F5, 0, 0))  # BM_CLICK
                home = wait_for("visible installer home", lambda: window(None, "Local Suite"))
                install = wait_for("install button", lambda: window(home, "Install / Update"))
                wait_for("background inventory", started.exists)
                self.assertFalse(user32.IsWindowEnabled(install))
                (root / "release").touch()
                wait_for("install button enabled", lambda: user32.IsWindowEnabled(install))
                self.assertTrue(user32.PostMessageW(home, 0x0010, 0, 0))  # WM_CLOSE
                self.assertEqual(process.wait(timeout=10), 0)
            finally:
                (root / "release").touch()
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=10)


if __name__ == "__main__":
    unittest.main()
