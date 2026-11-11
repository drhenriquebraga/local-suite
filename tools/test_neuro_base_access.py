"""Synthetic code readiness is independent of a previous weights failure."""
import contextlib
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'app'), r'C:\AI_PROJETOS\CONTOURLAB\app']
from fastapi import FastAPI
from fastapi.testclient import TestClient
import radai_plugins as P
import radai_neuro_install as SDK
import radai_plugin_bootstrap as BOOT
import radai_queue_state as QUEUE


class NeuroBaseAccess(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory(prefix='neuro-base-synthetic-')))
        self.plugin = self.root / 'Plugins/NEURO RT'
        self.code = self.plugin / 'versions/1.3.4'
        self.code.mkdir(parents=True)
        module = {'schema': 'neuro-rt/plugin-manifest/1', 'id': 'neuro-rt',
                  'version': '1.3.4', 'host_contract': P.HOST_CONTRACT,
                  'host_min_version': '8.20', 'python': '>=3.10',
                  'adapter': 'adapter.py:mount', 'base_tools': ['nidus']}
        (self.code / 'module.json').write_text(json.dumps(module), encoding='utf8')
        (self.code / 'adapter.py').write_text(
            'def mount(app, code, host_services=None):\n'
            '    from fastapi.responses import HTMLResponse\n'
            '    @app.get("/neuro/")\n'
            "    def mini(): return HTMLResponse('<h1>NEURO RT</h1><a href=/neuro/nidus>NIDUS</a>')\n"
            '    return host_services\n', encoding='utf8')
        files = [{'path': 'code/' + path.name, 'size': path.stat().st_size,
                  'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                 for path in self.code.iterdir()]
        (self.code / 'release-manifest.json').write_text(json.dumps({
            'schema': 'neuro-rt/release-package/1', 'plugin_id': 'neuro-rt',
            'version': '1.3.4', 'files': files}), encoding='utf8')
        self.pointer = self.plugin / 'installation.json'
        self.state = {'schema': 'neuro-rt/installation/1', 'state': 'ready',
                      'active_version': '1.3.4', 'execution_mode': 'host',
                      'runtime': None, 'resources': None}
        self.save()
        self.info = {'contract': P.HOST_CONTRACT, 'version': '8.20'}

    def save(self):
        self.pointer.write_text(json.dumps(self.state), encoding='utf8')

    def test_failed_weights_state_can_discover_valid_base_code(self):
        self.state.update(state='failed', error_code='INSTALL_FAILED')
        self.save()
        result = P.discover_plugin(self.root, host_info=self.info)
        self.assertEqual(result['state'], 'ready', result)
        self.assertEqual(result['active_version'], '1.3.4')

    def test_recovery_still_rejects_modified_code(self):
        self.state.update(state='failed', error_code='INSTALL_FAILED')
        self.save()
        (self.code / 'adapter.py').write_text('# changed, never execute\n')
        self.assertEqual(P.discover_plugin(self.root, host_info=self.info)['state'], 'failed')

    def test_first_home_navigation_opens_mini_despite_historical_failure(self):
        provider = SimpleNamespace(
            consent_status=lambda: {'installation_accepted': True, 'first_use_accepted': True},
            consent_policy=lambda: {}, status=lambda: {'state': 'failed', 'error_code': 'INSTALL_FAILED'},
            check_plugin_release=lambda *args: {'state': 'current'},
            install=Mock(), request_plugin_update=Mock())
        service = SimpleNamespace(settings=SimpleNamespace(plugin_paths=SimpleNamespace(active_version='1.3.4')),
                                  weights_status=lambda: {'state': 'missing', 'version': None,
                                      'recipe_sha256': None, 'missing_components': ['extras']})
        self.stack.enter_context(patch.object(BOOT, 'ensure_base', return_value=True))
        self.stack.enter_context(patch.object(SDK, 'build_provider', return_value=provider))
        self.stack.enter_context(patch.object(QUEUE, 'quem_tem_a_vez', return_value={'dono': 'lote'}))
        self.stack.enter_context(patch.object(QUEUE, 'fechando_ao_fim', return_value=True))
        app = FastAPI()
        P.montar(app, {'suite_root': self.root, 'neuro_host_version': '8.20',
                      'neuro_host_services': service, 'arranque': {'PORT': '8777'}})
        with TestClient(app, base_url='http://localhost') as client:
            response = client.get('/neuro', follow_redirects=False)
            self.assertEqual(response.status_code, 307, response.text[:200])
            self.assertEqual(response.headers['location'], '/neuro/')
            self.assertIn('NIDUS', client.get('/neuro/').text)
            status = client.get('/api/plugins/neuro-rt').json()
            self.assertTrue(status['code_ready'])
            self.assertTrue(status['base_ready'])
            self.assertEqual(status['weights']['state'], 'missing')
            self.assertEqual(status['update']['error_code'], 'INSTALL_FAILED')
            self.assertEqual(client.get('/neuro/nidus', follow_redirects=False).headers['location'], '/nidus/projecao')
        provider.install.assert_not_called()
        provider.request_plugin_update.assert_not_called()

    def test_legacy_plugin_actions_prepare_only_weights_and_reject_code(self):
        provider = SimpleNamespace(
            consent_status=lambda: {'installation_accepted': True, 'first_use_accepted': True},
            consent_policy=lambda: {}, status=lambda: {'state': 'idle'},
            check_plugin_release=lambda *args: {'state': 'current'}, install=Mock(),
            request_plugin_update=Mock(return_value={'state': 'preparing'}))
        self.stack.enter_context(patch.object(BOOT, 'ensure_base', return_value=True))
        self.stack.enter_context(patch.object(BOOT, 'seed_for_install', return_value=self.root))
        self.stack.enter_context(patch.object(SDK, 'build_provider', return_value=provider))
        prepare = self.stack.enter_context(patch.object(SDK, 'prepare_external_plan',
            side_effect=lambda payload, **kwargs: dict(payload, version='1.3.4')))
        app = FastAPI()
        entry = P.montar(app, {'suite_root': self.root, 'neuro_host_version': '8.20'})
        headers = {'origin': 'http://localhost', 'x-neuro-plugin-token': entry['token']}
        with TestClient(app, base_url='http://localhost') as client:
            for path, payload in (('install', {'confirm': True}), ('update', {'action': 'comecar'})):
                with self.subTest(path=path):
                    response = client.post('/api/plugins/neuro-rt/' + path, json=payload, headers=headers)
                    self.assertEqual(response.status_code, 202, response.text)
                    self.assertIs(prepare.call_args.args[0]['resources_only'], True)
                    provider.install.assert_not_called()
                    before = prepare.call_count
                    response = client.post('/api/plugins/neuro-rt/' + path,
                                           json=dict(payload, operation='code'), headers=headers)
                    self.assertEqual(response.status_code, 400)
                    self.assertEqual(response.json()['detail']['code'], 'SUITE_CODE_UPDATE_REQUIRED')
                    self.assertEqual(prepare.call_count, before)


if __name__ == '__main__':
    unittest.main(verbosity=2)
