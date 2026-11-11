"""Synthetic API regressions for immutable local code/weights selection.

Runs the real FastAPI handlers; no package is installed or downloaded.
"""
import contextlib
import os
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
CONTOUR = Path(os.environ.get('CONTOURLAB_TEST_SOURCE', str(ROOT.parent / 'CONTOURLAB')))
if (CONTOUR / 'app').is_dir():
    sys.path.append(str(CONTOUR / 'app'))

from fastapi import FastAPI
from fastapi.testclient import TestClient
import radai_lung_install as LSDK
import radai_lung_plugin as LUNG
import radai_neuro_install as NSDK
import radai_plugin_bootstrap as BOOT
import radai_plugin_setup as SETUP
import radai_plugins as NEURO
import radai_queue_state as QUEUE
import radai_atualizar as UPDATE


class OperationBinding(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.folder = Path(self.stack.enter_context(tempfile.TemporaryDirectory(prefix='plugin-binding-synthetic-')))
        self.root = self.folder / 'suite'
        self.root.mkdir()
        self.stack.enter_context(patch.object(BOOT, 'ensure_base', return_value=False))
        self.stack.enter_context(patch.object(BOOT, 'seed_for_install', return_value=self.root))
        self.stack.enter_context(patch.object(QUEUE, 'quem_tem_a_vez', return_value={}))
        self.stack.enter_context(patch.object(QUEUE, 'fechando_ao_fim', return_value=False))
        self.stack.enter_context(patch.object(QUEUE, 'pedir_fechar_ao_fim'))
        self.stack.enter_context(patch.object(UPDATE, 'etapa', return_value='idle'))

    def mount(self, slug):
        app = FastAPI()
        app.state.radai_reabertura = {'encerrar': lambda: None}
        if slug == 'neuro-rt':
            provider = SimpleNamespace(
                install=Mock(return_value={'state': 'external_install'}),
                request_plugin_update=Mock(return_value={'state': 'external_install'}),
                consent_status=lambda: {'installation_accepted': True},
                accept_consent=Mock(),
            )
            self.stack.enter_context(patch.object(NSDK, 'build_provider', return_value=provider))
            entry = NEURO.montar(app, {'suite_root': self.root, 'neuro_host_version': '8.19', 'arranque': {'PORT': '8777'}})
            self.prepare = self.stack.enter_context(patch.object(NSDK, 'prepare_external_plan',
                side_effect=lambda payload, **kwargs: dict(payload)))
            self.launch = provider.request_plugin_update
            self.legacy = provider.install
            self.inspect = self.stack.enter_context(patch.object(NSDK, 'inspect_local_source'))
        else:
            self.stack.enter_context(patch.object(NEURO, 'discover_plugin', return_value={'state': 'absent'}))
            self.stack.enter_context(patch.object(LSDK, 'check_latest', return_value={'state': 'current'}))
            self.stack.enter_context(patch.object(LUNG, '_accepted', return_value=True))
            entry = LUNG.montar(app, {'suite_root': self.root, 'neuro_host_version': '8.19', 'arranque': {'PORT': '8777'}})
            self.prepare = self.stack.enter_context(patch.object(LSDK, 'prepare_external_plan',
                side_effect=lambda payload, **kwargs: dict(payload)))
            installer = Mock()
            installer.launch.return_value = {'state': 'external_install'}
            self.stack.enter_context(patch.object(SETUP, 'ExternalInstaller', return_value=installer))
            self.launch = installer.launch
            self.inspect = self.stack.enter_context(patch.object(LSDK, 'inspect_local_source'))
        entry['installation'] = {'state': 'ready', 'active_version': '1.9.0'}
        self.entry, self.slug = entry, slug
        self.client = self.stack.enter_context(TestClient(app, base_url='http://localhost'))
        self.headers = {'origin': 'http://localhost', 'x-' + ('neuro' if slug == 'neuro-rt' else 'lung') + '-plugin-token': entry['token']}

    def source(self, purpose, version='1.9.0'):
        description = {'version': version, 'kind': 'offline_bundle' if purpose == 'weights' else 'setup',
                       'offline': purpose == 'weights', 'path': str(self.root), 'source_folder': str(self.root)}
        if self.slug == 'neuro-rt':
            self.entry['local_sources']['fixture-source'] = {'folder': str(self.root), 'description': description,
                'checked_at': time.monotonic(), 'operation': purpose}
        else:
            self.entry['sources']['fixture-source'] = {'description': description,
                'time': time.monotonic(), 'operation': purpose}

    def request_install(self, purpose=None, action='install', headers=None):
        payload = {'source_id': 'fixture-source'}
        payload.update({'confirm': True} if action == 'install' else {'action': 'comecar'})
        if purpose is not None:
            payload['operation'] = purpose
        return self.client.post('/api/plugins/' + self.slug + '/' + action,
            json=payload, headers=self.headers if headers is None else headers)

    def test_omitted_operation_inherits_bound_weights_for_both_plugins(self):
        for slug in ('neuro-rt', 'lung-rt'):
            with self.subTest(plugin=slug):
                self.mount(slug)
                self.source('weights', version='1.3.0')
                response = self.request_install()
                self.assertEqual(response.status_code, 202 if slug == 'neuro-rt' else 200, response.text)
                payload = self.prepare.call_args.args[0]
                self.assertIs(payload.get('resources_only'), True)
                self.assertFalse(payload.get('code_only', False))

    def test_old_code_source_cannot_trigger_code_installation(self):
        for slug in ('neuro-rt', 'lung-rt'):
            with self.subTest(plugin=slug):
                self.mount(slug)
                self.source('code')
                response = self.request_install()
                self.assertEqual(response.status_code, 400, response.text)
                self.prepare.assert_not_called()
                self.launch.assert_not_called()

    def test_explicit_cross_operation_mismatch_is_rejected_before_plan(self):
        for slug in ('neuro-rt', 'lung-rt'):
            for source_purpose, request_purpose in (('weights', 'code'), ('code', 'weights')):
                with self.subTest(plugin=slug, source=source_purpose):
                    self.mount(slug)
                    self.source(source_purpose)
                    response = self.request_install(request_purpose)
                    self.assertEqual(response.status_code, 400, response.text)
                    self.prepare.assert_not_called()
                    self.launch.assert_not_called()

    def test_neuro_update_without_operation_inherits_bound_weights(self):
        self.mount('neuro-rt')
        self.source('weights')
        response = self.request_install(action='update')
        self.assertEqual(response.status_code, 202, response.text)
        self.assertIs(self.prepare.call_args.args[0].get('resources_only'), True)

    def test_older_neuro_code_package_is_rejected_before_planning(self):
        self.mount('neuro-rt')
        self.source('code', version='1.3.0')
        response = self.request_install('code')
        self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(response.json()['detail']['code'], 'SUITE_CODE_UPDATE_REQUIRED')
        self.prepare.assert_not_called()
        self.launch.assert_not_called()

    def test_legacy_install_without_operation_prepares_only_weights(self):
        for slug in ('neuro-rt', 'lung-rt'):
            with self.subTest(plugin=slug):
                self.mount(slug)
                response = self.client.post('/api/plugins/' + slug + '/install',
                    json={'confirm': True}, headers=self.headers)
                self.assertEqual(response.status_code, 202 if slug == 'neuro-rt' else 200, response.text)
                self.assertIs(self.prepare.call_args.args[0].get('resources_only'), True)
                if slug == 'neuro-rt':
                    self.legacy.assert_not_called()

    def test_install_without_token_or_from_other_origin_is_rejected(self):
        for slug in ('neuro-rt', 'lung-rt'):
            with self.subTest(plugin=slug):
                self.mount(slug)
                self.source('weights')
                for headers in ({}, dict(self.headers, origin='https://external.invalid')):
                    response = self.request_install('weights', headers=headers)
                    self.assertEqual(response.status_code, 403, response.text)
                self.prepare.assert_not_called()
                self.launch.assert_not_called()

    def test_legacy_folder_inspection_classifies_bundle_as_weights(self):
        for slug in ('neuro-rt', 'lung-rt'):
            with self.subTest(plugin=slug):
                self.mount(slug)
                self.inspect.return_value = {'version': '1.3.0', 'kind': 'offline_bundle', 'offline': True,
                    'path': str(self.root), 'source_folder': str(self.root)}
                response = self.client.post('/api/plugins/' + slug + '/local/inspect',
                    json={'folder': str(self.root)}, headers=self.headers)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()['operation'], 'weights')


if __name__ == '__main__':
    unittest.main(verbosity=2)
