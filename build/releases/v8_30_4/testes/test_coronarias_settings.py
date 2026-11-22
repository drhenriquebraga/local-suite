"""Exercise the production settings markup in Chromium with synthetic station responses."""
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from playwright.sync_api import expect, sync_playwright

from pastas_teste_coronarias import PROGRAMA
sys.path.insert(0, str(PROGRAMA / 'app'))
import radai_coronarias_ui as ui
import radai_batch
import radai_languages
import radai_panel
import radai_plugin_coronarias as policy
import radai_ui


class Settings(unittest.TestCase):
    def test_disabled_task_help(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(policy, 'REGISTRO', Path(tmp)):
            config = radai_batch.opcoes_da_tela('CT')
        task, = [item for item in config['tasks'] if item['task'] == 'rocards_lad']
        self.assertTrue(task['plugin_bloqueado'])
        # The demo uses the real card and interactions, with no scan or DICOM data.
        task['figuras'] = []
        html = radai_ui.aplicar(radai_batch._pagina())
        with sync_playwright() as playwright:
            chrome = Path(os.environ.get('RADAI_CHROME', r'C:\Program Files\Google\Chrome\Application\chrome.exe'))
            browser = playwright.chromium.launch(executable_path=str(chrome) if chrome.is_file() else None)
            page = browser.new_page(viewport={'width': 1360, 'height': 850}, reduced_motion='reduce')
            page.route('**/*', lambda route: route.fulfill(content_type='text/html; charset=utf-8',body=html)
                       if route.request.url.endswith('/lote') else route.fulfill(status=404, json={}))
            page.goto('http://fixture.test/lote')
            page.evaluate("""d=>{
              window.uiPopupSerie('cx1').fechar();
              SERIES=[{uid:'synthetic',pasta:'fixture',modalidade:'CT'}]; OPC.CT=d;
              document.body.replaceChildren();
              const main=document.createElement('main'); document.body.append(main);
              main.innerHTML=painelPerso(0);
            }""", config)
            row = page.locator('[data-ln-task=rocards_lad]')
            expect(row.locator('input')).to_be_disabled()
            expect(row.locator('input')).not_to_be_checked()
            help_button = row.locator('button[data-p4-aj=task]')
            expect(help_button).to_be_enabled()
            dest = os.environ.get('RADAI_CORONARY_QA_VISUALS')
            if dest:
                Path(dest).mkdir(parents=True, exist_ok=True)
                row.screenshot(path=str(Path(dest) / 'chave-desativada.png'), animations='disabled')
            help_button.click()
            dialog = page.get_by_role('dialog')
            expect(dialog).to_contain_text('Configurações > Plugins > Coronárias')
            if dest:
                dialog.screenshot(path=str(Path(dest) / 'ajuda-rodar-agora.png'), animations='disabled')
            browser.close()

    def test_workstation_consent(self):
        page_html = radai_ui.aplicar(ui.config_page(radai_panel.PAGINA_CONFIG))
        record = dict(ativado=False, disponivel=False, preparando=False, erro=None,
                      termos_versao=policy.VERSAO, termos_sha256=policy.IMPRESSAO,
                      termos_texto=policy.TEXTO)
        posts = []
        imports = []
        fail = False

        def route_http(route):
            url = route.request.url
            if url.endswith('/config'):
                route.fulfill(content_type='text/html; charset=utf-8', body=page_html)
            elif url.endswith('/api/plugins/coronarias/ativar'):
                posts.append(route.request.post_data_json)
                if fail:
                    route.fulfill(status=409, json={'ok': False})
                else:
                    record['preparando'] = True
                    route.fulfill(json={'ok': True, 'ativado': False, 'preparando': True})
            elif url.endswith('/api/plugins/coronarias/importar'):
                imports.append((route.request.headers, route.request.post_data_buffer))
                if fail:
                    route.fulfill(status=422, json={'erro': r'Hash incorreto LAD.pb: C:\private\path with spaces'})
                else:
                    record.update(ativado=True, disponivel=True, preparando=False)
                    route.fulfill(json={'ok': True, **record})
            elif url.endswith('/api/plugins/coronarias'):
                route.fulfill(json=record)
            else:
                route.fulfill(status=404, json={})

        with sync_playwright() as playwright:
            chrome = Path(os.environ.get('RADAI_CHROME', r'C:\Program Files\Google\Chrome\Application\chrome.exe'))
            browser = playwright.chromium.launch(executable_path=str(chrome) if chrome.is_file() else None)
            page = browser.new_page(viewport={'width': 1120, 'height': 860}, reduced_motion='reduce')
            page.route('**/*', route_http)
            page.goto('http://fixture.test/config#ps_neuro')
            expect(page.locator('#neuro-update')).to_be_visible()
            expect(page.locator('a.cfg-card[data-alvo=ps_plugins]')).to_have_count(1)
            expect(page.locator('a.cfg-card:is([data-alvo=ps_neuro],[data-alvo=ps_lung])')).to_have_count(0)
            tiles = page.locator('#ps_plugins [data-plug]')
            expect(tiles).to_have_count(3)
            page.goto('http://fixture.test/config#ps_lung')
            expect(page.locator('#lung-plugin-setup')).to_be_visible()
            page.locator('[data-plug=coronarias]').click()
            msg = page.locator('#cor-message')
            button = page.locator('#cor-review')
            expect(button).to_be_visible()
            self.assertEqual(set(ui.STRINGS), {code for code, *_ in radai_languages.IDIOMAS})
            for loc, strings in ui.STRINGS.items():
                page.evaluate('(loc) => {document.documentElement.lang = loc;}', loc)
                expect(tiles.last).to_have_text(strings['coronary'])
                expect(msg).to_have_text(strings['inactive'])
            page.evaluate("document.documentElement.lang = 'pt-BR'")
            page.locator('.cor-help summary').click()
            images = os.environ.get('RADAI_CORONARY_QA_VISUALS')
            if images:
                dest = Path(images)
                dest.mkdir(parents=True, exist_ok=True)
                page.locator('#ps_plugins').screenshot(path=str(dest / 'plugins-inativos.png'), animations='disabled')
            button.click()
            dialog = page.get_by_role('dialog')
            if images:
                dialog.screenshot(path=str(dest / 'aceite-coronarias.png'), animations='disabled')
            check = dialog.get_by_role('checkbox')
            submit = dialog.locator('[type=submit]')
            expect(submit).to_be_disabled()
            expect(check).not_to_be_checked()
            dialog.locator('summary').click()
            expect(dialog.locator('.cor-original')).to_have_text(record['termos_texto'])
            page.keyboard.press('Escape')
            expect(dialog).to_have_count(0)
            expect(button).to_be_focused()
            self.assertEqual(posts, [])
            fail = True
            button.click()
            check.check()
            submit.click()
            expect(page.locator('#cor-state')).to_have_attribute('data-phase', 'error')
            expect(button).not_to_be_visible()
            page.locator('#cor-retry').click()
            expect(button).to_be_visible()
            fail = False
            button.click()
            check.check()
            submit.click()
            expect(page.locator('#cor-state')).to_have_attribute('data-phase', 'preparing')
            expect(page.locator('#cor-transcript')).not_to_be_visible()
            self.assertEqual(posts[-1], {'aceito': True, 'termos_versao': policy.VERSAO, 'termos_sha256': policy.IMPRESSAO})
            page.reload()
            expect(page.locator('#cor-state')).to_have_attribute('data-phase', 'preparing')
            record.update(ativado=True, disponivel=True, preparando=False)
            expect(page.locator('#cor-state')).to_have_attribute('data-phase', 'active')
            expect(button).not_to_be_visible()
            page.reload()
            expect(page.locator('#cor-state')).to_have_attribute('data-phase', 'active')
            expect(page.locator('#cor-transcript')).to_be_visible()
            self.assertEqual(len(posts), 2)
            page.evaluate("document.documentElement.lang = 'pt-BR'")
            if images:
                page.locator('#ps_plugins').screenshot(path=str(dest / 'plugins-coronarias.png'), animations='disabled')
            record.update(disponivel=False)
            page.reload()
            expect(page.locator('#cor-state')).to_have_attribute('data-phase', 'restricted')
            expect(button).to_be_visible()
            button.click()
            expect(submit).to_be_disabled()
            page.keyboard.press('Escape')
            source = BytesIO()
            with ZipFile(source, 'w') as archive:
                archive.writestr('synthetic-resource.txt', 'Synthetic resource')
            chosen = {'name':'Coronarias-ROCardS.zip', 'mimeType':'application/zip', 'buffer':source.getvalue()}
            picker = page.locator('#cor-file')
            def choose_file():
                with page.expect_file_chooser() as file_chooser:
                    page.locator('#cor-import').click()
                file_chooser.value.set_files(chosen)
                expect(dialog.locator('[data-cor-filename]')).to_have_text(chosen['name'])
                expect(submit).to_be_disabled()
            picker.set_input_files({'name':'invalid.txt', 'mimeType':'text/plain', 'buffer':b'dummy'})
            expect(page.locator('#cor-file-error')).to_be_visible()
            choose_file()
            if images:
                page.evaluate("document.documentElement.lang = 'pt-BR'")
                dialog.screenshot(path=str(dest / 'importar-coronarias.png'), animations='disabled')
            page.keyboard.press('Escape')
            self.assertEqual(imports, [])
            fail = True
            choose_file()
            check.check()
            submit.click()
            expect(page.locator('#cor-state')).to_have_attribute('data-phase', 'error')
            expect(page.locator('#cor-diagnostic')).to_have_text('Hash incorreto LAD.pb:  […]')
            page.locator('#cor-retry').click()
            expect(page.locator('#cor-state')).to_have_attribute('data-phase', 'restricted')
            fail = False
            choose_file()
            check.check()
            submit.click()
            expect(page.locator('#cor-state')).to_have_attribute('data-phase', 'active')
            headers, body = imports[-1]
            self.assertEqual(body, source.getvalue())
            self.assertEqual(headers['content-type'], 'application/zip')
            self.assertEqual(headers['x-radai-aceito'], '1')
            self.assertEqual(headers['x-radai-termos-versao'], policy.VERSAO)
            self.assertEqual(headers['x-radai-termos-sha256'], policy.IMPRESSAO)
            self.assertEqual(len(imports), 2)
            page.set_viewport_size({'width': 360, 'height': 720})
            self.assertLessEqual(page.locator('#ps_plugins').evaluate('el=>el.scrollWidth'), 360)
            browser.close()


if __name__ == '__main__':
    unittest.main(verbosity=2)
