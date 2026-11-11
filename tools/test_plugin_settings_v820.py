"""Final plugin settings and NEURO landing regressions with synthetic HTTP data."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
import radai_languages as LANG
import radai_lung_plugin as LUNG
import radai_plugin_setup_ui as UI
import radai_ui


class PluginSettings(unittest.TestCase):
    def pages(self):
        shell = ('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                 '<style>' + radai_ui.TOKENS + radai_ui.AJUDA + radai_ui.COMPONENTES + radai_ui.BOTOES +
                 'body{margin:0;padding:16px;background:var(--bg-0);color:var(--text);font-family:var(--font-display)}'
                 'main{max-width:1060px;margin:auto} .cfg-cards{display:flex;gap:12px;flex-wrap:wrap}.cfg-card{display:block;width:240px}'
                 '.cfg-card .cab{display:flex;justify-content:space-between}.ps-cab{display:flex;gap:8px;align-items:center;flex-wrap:wrap}'
                 'section.ps-cx{margin:16px 0}.ps-cx[hidden]{display:block}</style></head><body><main>'
                 '<nav class="cfg-cards"> <a class="cfg-card" href="#ps_limpar"></a></nav>'
                 '<section class="ps-cx fechado" id="ps_limpar" hidden></section></main>' + radai_ui.JS + radai_ui.COMPONENTES_JS + '</body></html>')
        settings = LUNG.config_page(UI.config_page(shell))
        landing = '<!doctype html><html><head><meta charset="utf-8"></head><body>' + UI.controls(False) + '</body></html>'
        landing = UI.assets(landing).replace('</body>', UI.scripts() + '</body>')
        return LANG.aplicar(settings), LANG.aplicar(landing)

    def test_plugin_card_icons_and_help_follow_existing_pattern(self):
        settings, _ = self.pages()
        for slug in ('neuro', 'lung'):
            card = re.search(r'<a class="cfg-card"[^>]*data-alvo="ps_' + slug + r'"[^>]*>(.*?)</a>', settings, re.S).group(1)
            self.assertIn('<span class="cab"><span class="ic">', card)
            self.assertLess(card.index('class="ic"'), card.index('class="n"'))
            title = re.search(r'<section[^>]*id="ps_' + slug + r'"[^>]*>\s*<h2[^>]*>(.*?)</h2>', settings, re.S).group(1)
            self.assertIn('class="ui-ajuda"', title)
            self.assertIn('class="ui-balao"', title)
            self.assertIn(UI.HINT, title)
            self.assertIn(UI.CODE_MANAGED, title)
        self.assertNotIn('data-pi-choice="zip"', settings)
        self.assertNotIn('class="pi-hint"', settings)

    def test_real_controllers_unify_errors_and_neuro_ignores_old_failure(self):
        node = shutil.which('node')
        module = Path(os.environ.get('RADAI_PLAYWRIGHT_MODULE', str(Path.home() / '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright')))
        chrome = Path(os.environ.get('RADAI_CHROME', r'C:\Program Files\Google\Chrome\Application\chrome.exe'))
        if not node or not module.is_dir() or not chrome.is_file():
            self.skipTest('Chrome and Playwright not installed')
        with tempfile.TemporaryDirectory(prefix='plugin-settings-820-') as folder:
            destination = Path(folder)
            settings, landing = self.pages()
            (destination / 'settings.html').write_text(settings, encoding='utf8')
            (destination / 'landing.html').write_text(landing, encoding='utf8')
            (destination / 'minipage.html').write_text(landing.replace('data-neuro-install="1"', 'data-neuro-install="0"'), encoding='utf8')
            (destination / 'languages.js').write_text(LANG.corpo_js(), encoding='utf8')
            words = {locale: {text: LANG.FRASES.get(locale, {}).get(text, text) for text in (
                'O ZIP excede o limite permitido para esta operação.', 'Pesos não instalados', 'Instalar ou atualizar os pesos')}
                for locale in ('pt-BR', *LANG.FRASES)}
            (destination / 'expected.json').write_text(json.dumps(words, ensure_ascii=False), encoding='utf8')
            result = subprocess.run([node, str(Path(__file__).with_name('plugin_settings_v820_browser.cjs')), folder, str(module), str(chrome)],
                                    capture_output=True, text=True, encoding='utf8', errors='replace', timeout=180)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('PASS 12 locales', result.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
