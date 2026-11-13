"""Exercise the actual shared picker DOM; no patient files are used."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'app'), str(ROOT/'tools')]


class SeriesPickerInteraction(unittest.TestCase):
    def test_folder_selection_starts_once_and_newest_is_default(self):
        import test_ui_shell_v814 as fixture
        import radai_languages
        with tempfile.TemporaryDirectory(prefix='picker824-') as folder:
            path = Path(folder)/'fixture.json'
            path.write_text(json.dumps({'html': fixture.fixture(),
                                        'languages': radai_languages.corpo_js()}), encoding='utf8')
            env = dict(os.environ, PICKER_FIXTURE=str(path))
            env.setdefault('NEURO_PLAYWRIGHT_MODULE', r'C:\Users\henri\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules\playwright')
            result = subprocess.run(['node', str(ROOT/'tests'/'series_picker_v824.cjs')],
                                    env=env, capture_output=True, text=True, encoding='utf8', timeout=90)
            self.assertEqual(result.returncode, 0, result.stdout+'\n'+result.stderr)
            print(result.stdout)


if __name__ == '__main__':
    unittest.main()
