"""Visible feedback for a deliberate weight check, independent of downloads."""
import os
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))


class WeightFeedbackBrowser(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node') and Path(os.environ.get('NEURO_BROWSER_EXECUTABLE', 'C:/Program Files/Google/Chrome/Application/chrome.exe')).is_file(), 'Node/Chrome unavailable')
    def test_checking_ready_missing_and_failure(self):
        import radai_plugin_setup_ui as ui
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder) / 'weights.html'
            fixture.write_text('<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><style>' + ui.CSS
                               + '</style></head><body>' + ui.controls(plugin='neuro')
                               + '<script>' + ui.SCRIPT + '</script></body></html>', encoding='utf-8')
            env = dict(os.environ, WEIGHTS_CHECK_HTML=str(fixture))
            env.setdefault('NEURO_PLAYWRIGHT_MODULE', str(Path.home() / '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'))
            result = subprocess.run(['node', str(ROOT/'tests/plugin_weights_check_browser.cjs')],
                                    env=env, capture_output=True, text=True, timeout=45)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            print(result.stdout.strip())


if __name__ == '__main__': unittest.main()
