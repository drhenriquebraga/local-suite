import ast
import hashlib
import json
import tempfile
import os
import sys
import threading
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _componentes
_componentes.ligar_caminho()
import _cleanup
_cleanup.adotar_prefixo('radai_neuro_restart_')
BASE = Path(_cleanup.temporaria('radai_neuro_restart_'))
os.environ['RADAI_CALIB_DIR'] = str(BASE / 'calib')
os.environ['RADAI_REGISTRO_DIR'] = str(BASE / 'registro')
os.environ['RADAI_NAVEGADOR'] = '0'
from fastapi import FastAPI
import radai_shutdown as S
import radai_plugins as P


class Restart(unittest.TestCase):
    def app(self, successor):
        self.closed = threading.Event()
        app = FastAPI()
        S.montar(app, self.closed.set, sucessor=successor)
        return app

    def test_sucessor_pronto_antes_de_encerrar_e_pedido_idempotente(self):
        calls = []
        process = types.SimpleNamespace(pid=456, poll=lambda: None)
        app = self.app(lambda port: calls.append(port) or process)
        with patch.object(S.time, 'sleep', return_value=None):
            result = S.reabrir_para_plugin(app, 8791)
        self.assertTrue(result['ok'])
        self.assertTrue(result['scheduled'])
        self.assertTrue(self.closed.wait(2))
        self.assertEqual(calls, [8791])
        self.assertEqual(S.reabrir_para_plugin(app, 8791), result)
        self.assertEqual(calls, [8791])

    def test_falha_do_sucessor_preserva_motor_aberto(self):
        def fail(port):
            raise OSError('fixture')
        app = self.app(fail)
        with self.assertRaises(OSError):
            S.reabrir_para_plugin(app, 8791)
        self.assertFalse(self.closed.is_set())

    def test_sucessor_que_ja_saiu_nao_encerra(self):
        app = self.app(lambda port: types.SimpleNamespace(poll=lambda: 1))
        with self.assertRaises(ValueError):
            S.reabrir_para_plugin(app, 8791)
        self.assertFalse(self.closed.is_set())

    def test_sem_encerramento_registrado_ou_porta_valida_recusa(self):
        with self.assertRaises(ValueError):
            S.reabrir_para_plugin(FastAPI(), 8791)
        for port in (None, True, 0, -1, 65536, '8791/other'):
            app = self.app(lambda port: self.fail('nao deve lancar'))
            with self.assertRaises((ValueError, TypeError)):
                S.reabrir_para_plugin(app, port)
            self.assertFalse(self.closed.is_set())

    def test_loader_usa_reinicio_dedicado(self):
        observed = {}
        provider = types.SimpleNamespace(install=lambda: {}, status=lambda: {'state': 'idle'},
            consent_status=lambda: {}, consent_policy=lambda: {})
        app = FastAPI()
        cfg = {'suite_root': BASE / 'host',
               'neuro_host_version': '8.10', 'arranque': {'PORT': '8791'},
               'recarregar': lambda: self.fail('recarga nao reinicia')}
        def build(root, info, config):
            observed.update(config)
            return provider
        with patch('radai_neuro_install.build_provider', side_effect=build):
            entry = P.montar(app, cfg)
        with patch.object(S, 'reabrir_para_plugin', return_value={'ok': True, 'scheduled': True}) as restart:
            self.assertTrue(observed['neuro_restart']()['ok'])
            restart.assert_called_once_with(app, 8791)
        self.assertIsNotNone(entry)

    def test_preparo_segura_fechamento_automatico(self):
        source = Path(_componentes.fonte('app/radai_watcher.py')).read_text(encoding='utf-8-sig')
        function = next(n for n in ast.parse(source).body
                        if isinstance(n, ast.FunctionDef) and n.name == 'o_que_segura_o_fechar')
        namespace = {'STATE': {}, 'quem_esta_segmentando': lambda: None,
                     '_turno_segue_na_fila': lambda: False, 'sys': sys}
        exec(compile(ast.Module(body=[function], type_ignores=[]), '<watcher-fixture>', 'exec'), namespace)
        with patch.object(P, 'preparo_em_andamento', return_value=True):
            self.assertIn('NEURO RT', namespace['o_que_segura_o_fechar']())
        with patch.object(P, 'preparo_em_andamento', return_value=False):
            self.assertIsNone(namespace['o_que_segura_o_fechar']())

    def test_verificacao_do_novo_processo_informa_contadores_sem_caminhos(self):
        with tempfile.TemporaryDirectory(prefix='radai_neuro_verification_', dir=BASE) as directory:
            root = Path(directory)
            plugin = root / 'Plugins/NEURO RT'
            code = plugin / 'versions/1.0.0'
            code.mkdir(parents=True)
            module = {'schema': 'neuro-rt/plugin-manifest/1', 'id': P.PLUGIN_ID,
                      'version': '1.0.0', 'host_contract': P.HOST_CONTRACT,
                      'host_min_version': '8.11', 'python': '>=3.10', 'adapter': 'adapter.py:mount'}
            (code / 'module.json').write_text(json.dumps(module), encoding='utf-8')
            (code / 'adapter.py').write_text('def mount(): pass', encoding='utf-8')
            files = []
            for name in ('module.json', 'adapter.py'):
                value = (code / name).read_bytes()
                files.append({'path': 'code/' + name, 'size': len(value),
                              'sha256': hashlib.sha256(value).hexdigest()})
            inventory = {'schema': 'neuro-rt/release-package/1', 'plugin_id': P.PLUGIN_ID,
                         'version': '1.0.0', 'files': files}
            (code / 'release-manifest.json').write_text(json.dumps(inventory), encoding='utf-8')
            (plugin / 'installation.json').write_text(json.dumps({'schema': 'neuro-rt/installation/1',
                'state': 'ready', 'active_version': '1.0.0'}), encoding='utf-8')
            progress = []
            result = P.discover_plugin(root, host_info={'contract': P.HOST_CONTRACT, 'version': '8.11'},
                                       progress=progress.append)
            self.assertEqual(result['state'], 'ready')
            self.assertEqual(progress[0]['completed_files'], 0)
            self.assertEqual(progress[-1]['completed_files'], 2)
            self.assertEqual(progress[-1]['processed_bytes'], sum(f['size'] for f in files))
            self.assertNotIn(str(root), json.dumps(progress))
            (code / 'adapter.py').write_text('tampered fixture', encoding='utf-8')
            result = P.discover_plugin(root, host_info={'contract': P.HOST_CONTRACT, 'version': '8.11'},
                                       progress=progress.append)
            self.assertEqual(result['state'], 'failed')

    def test_python_do_host_e_o_interpretador_em_execucao(self):
        info = P._host_info(BASE, {'neuro_host_version': '8.11'})
        self.assertEqual(info['python_executable'], sys.executable)

    def test_provider_nao_usa_recarga_como_reinicio(self):
        import radai_neuro_install as N
        received = {}
        restart = lambda: {'ok': True, 'scheduled': True}
        def coordinator(*args, **kwargs):
            received.update(kwargs)
            return types.SimpleNamespace(status=lambda: {})
        module = types.SimpleNamespace(UpdateCoordinator=coordinator)
        with patch.object(N, '_load_private_installer', return_value=module):
            N.build_provider(Path('.'), {'version': '8.11', 'python_executable': sys.executable},
                {'neuro_restart': restart, 'recarregar': lambda: None}).status()
        self.assertIs(received['restart'], restart)
        self.assertEqual(received['host_python'], sys.executable)

    def test_reabrir_aba_nao_libera_reserva_do_instalador(self):
        source = Path(_componentes.fonte('app/radai_watcher.py')).read_text(encoding='utf-8-sig')
        function = next(n for n in ast.parse(source).body
                        if isinstance(n, ast.FunctionDef) and n.name == '_segurar_a_fila_ao_fechar')
        calls = []
        namespace = {'_turno_segue_na_fila': lambda: False, 'sys': sys,
                     '_fila_da_estacao': lambda *args: calls.append(args), 'wlog': lambda *args: None}
        exec(compile(ast.Module(body=[function], type_ignores=[]), '<watcher-fixture>', 'exec'), namespace)
        with patch.object(P, 'preparo_em_andamento', return_value=True):
            namespace['_segurar_a_fila_ao_fechar'](False)
        self.assertEqual(calls, [])
        with patch.object(P, 'preparo_em_andamento', return_value=False):
            namespace['_segurar_a_fila_ao_fechar'](False)
        self.assertEqual(calls, [('pedir_fechar_ao_fim', False)])

    def test_verificacao_apos_reabertura_tambem_segura_o_fechamento(self):
        provider = types.SimpleNamespace(status=lambda: {'state': 'idle'},
                                         verification_in_progress=lambda: True)
        with patch.object(P, '_UPDATE_PROVIDER', provider):
            self.assertTrue(P.preparo_em_andamento())
        provider.verification_in_progress = lambda: False
        with patch.object(P, '_UPDATE_PROVIDER', provider):
            self.assertFalse(P.preparo_em_andamento())

    def test_estados_pendentes_nao_travam_fechamento_para_sempre(self):
        for phase in ('downloading', 'preparing', 'waiting', 'verifying', 'activating', 'restarting'):
            with patch.object(P, '_UPDATE_PROVIDER', types.SimpleNamespace(status=lambda: {'state': phase})):
                self.assertTrue(P.preparo_em_andamento(), phase)
        for phase in ('idle', 'error', 'failed', 'installed_pending_restart', 'absent'):
            with patch.object(P, '_UPDATE_PROVIDER', types.SimpleNamespace(status=lambda: {'state': phase})):
                self.assertFalse(P.preparo_em_andamento(), phase)


if __name__ == '__main__':
    unittest.main(verbosity=2)
