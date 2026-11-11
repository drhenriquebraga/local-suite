import io
import json
from pathlib import Path
import sys
import threading
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
import radai_version as V
import radai_atualizar as A
import radai_delivery as D


class Response(io.BytesIO):
    def __init__(self, url, version='8.19'):
        super().__init__(json.dumps({'schema': 'local-suite-update/1', 'version': version,
                                    'size': 7000000, 'sha256': 'a' * 64}).encode())
        self.url = url

    def geturl(self):
        return self.url


class UpdateSources(unittest.TestCase):
    def setUp(self):
        self.consultation = dict(V._CONSULTA)
        self.thread = V._THREAD_CONSULTA
        self.patches = [patch.object(V, '_entrega_txt', return_value='8.18'),
                        patch.object(D, 'carimbo', return_value={'versao': '8.18'}),
                        patch.object(V, 'nome_do_instalador_latest', return_value='RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_LATEST.zip')]
        for item in self.patches:
            item.start()
        V._THREAD_CONSULTA = None

    def tearDown(self):
        worker = V._THREAD_CONSULTA
        if worker and worker.is_alive():
            worker.join(5)
        V._CONSULTA.clear()
        V._CONSULTA.update(self.consultation)
        V._THREAD_CONSULTA = self.thread
        for item in reversed(self.patches):
            item.stop()

    def test_official_url_variants_and_historical_alias_keep_mirror_fallback(self):
        for url in (V.URL_VERSOES, V.URL_VERSOES + '/',
                    'https://github.com/drhenriquebraga/local-suite/releases/latest',
                    'https://api.github.com/repos/drhenriquebraga/local-suite/releases/latest',
                    'https://github.com/radioterapia-ai/local-suite/releases'):
            with self.subTest(url=url), patch.object(V, '_consultar_primario', return_value={'estado': 'erro', 'erro': 'blocked'}), \
                    patch.object(V, 'consultar_espelho', return_value={'estado': 'nova', 'versao': '8.19', 'fonte': 'espelho'}) as mirror:
                result = V.consultar(url, forcar=True)
                self.assertEqual(result['fonte'], 'espelho')
                mirror.assert_called_once()

    def test_custom_repository_and_disabled_check_do_not_use_author_mirror(self):
        for url in ('https://github.com/example/another-suite/releases', ''):
            with patch.object(V, '_consultar_primario', return_value={'estado': 'erro'}), patch.object(V, 'consultar_espelho') as mirror:
                V.consultar(url)
                mirror.assert_not_called()

    def test_api_endpoint_is_not_misread_as_a_github_web_repository(self):
        url = 'https://api.github.com/repos/drhenriquebraga/local-suite/releases/latest'
        self.assertEqual(V._api_de(url), url)
        self.assertEqual(V._api_de(V.URL_VERSOES), url)
        self.assertEqual(V.link_do_instalador(url), V.link_do_instalador(V.URL_VERSOES))

    def test_secure_canonical_redirect_allowed_but_other_hosts_or_paths_rejected(self):
        for final, valid in ((V.ESPELHO_LATEST.replace('://dr', '://www.dr'), True),
                             (V.ESPELHO_LATEST.replace('https:', 'http:'), False),
                             ('https://example.invalid/latest.json', False),
                             (V.ESPELHO_LATEST.replace('latest.json', 'login'), False)):
            with self.subTest(final=final), patch('urllib.request.urlopen', return_value=Response(final)):
                result = V.consultar_espelho(forcar=True)
                self.assertEqual(result['estado'] == 'nova', valid)

    def test_settings_refresh_uses_same_real_fallback_and_exposes_both_sources(self):
        calls = []
        def network(request, **kwargs):
            url = request.full_url
            calls.append(url)
            if 'api.github.com' in url:
                raise URLError('SYNTHETIC NETWORK BLOCK')
            return Response(url)
        with patch('urllib.request.urlopen', side_effect=network):
            response = A.agir('consultar')
            worker = V._THREAD_CONSULTA
            self.assertIsNotNone(worker)
            worker.join(5)
            response = A.agir('estado')
        self.assertFalse(response['consultando'])
        self.assertTrue(response['nova'])
        self.assertEqual(response['consulta_fonte'], 'espelho')
        self.assertEqual(response['consulta_origens']['github']['estado'], 'erro')
        self.assertEqual(response['consulta_origens']['espelho']['estado'], 'nova')
        self.assertIn('consulta=', calls[0])
        self.assertIn('consulta=', calls[1])

    def test_real_settings_post_contract_and_origin_guard(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        app = FastAPI()
        with patch.object(A, 'limpar_o_baixado'):
            A.montar(app, ler_vigia=lambda: {})
        def network(request, **kwargs):
            if 'github.com' in request.full_url:
                raise URLError('SYNTHETIC NETWORK BLOCK')
            return Response(request.full_url)
        with patch('urllib.request.urlopen', side_effect=network), TestClient(app) as client:
            rejected = client.post('/api/atualizar', headers={'Origin': 'https://elsewhere.invalid'}, json={'acao': 'consultar'})
            self.assertEqual(rejected.status_code, 403)
            checked = client.post('/api/atualizar', headers={'Origin': 'http://testserver'}, json={'acao': 'consultar'})
            self.assertEqual(checked.status_code, 200)
            V._THREAD_CONSULTA.join(5)
            result = client.post('/api/atualizar', headers={'Origin': 'http://testserver'}, json={'acao': 'estado'}).json()
        self.assertEqual(result['consulta_estado'], 'nova')
        self.assertEqual(result['consulta_fonte'], 'espelho')
        self.assertTrue(result['nova'])
        self.assertFalse(result['consultando'])

    def test_refresh_button_renders_source_and_both_failure_details(self):
        node = shutil.which('node')
        module = Path(os.environ.get('RADAI_PLAYWRIGHT_MODULE', str(Path.home() / '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright')))
        chrome = Path(os.environ.get('RADAI_CHROME', r'C:\Program Files\Google\Chrome\Application\chrome.exe'))
        if not node or not module.is_dir() or not chrome.is_file():
            self.skipTest('Chrome/Playwright runtime not available')
        with tempfile.TemporaryDirectory(prefix='update-settings-browser-') as folder:
            path = Path(folder)
            page = '''<!doctype html><meta charset="utf-8"><button id="btConsultarVersao" onclick="radaiConsultarVersao()">Verificar atualizações</button><span id="subAtu"></span><button id="btAtuAgora" hidden>Atualizar agora</button><p id="consultaVersaoOrigens" hidden></p><pre id="consultaVersaoErro" hidden></pre>''' + A.PARA_A_CASCA
            (path / 'config.html').write_text(page, encoding='utf8')
            run = subprocess.run([node, str(Path(__file__).with_name('update_sources_v819_browser.cjs')), str(path), str(module), str(chrome)], capture_output=True, text=True, encoding='utf8', errors='replace', timeout=60)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertIn('PASS source-aware settings refresh', run.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
