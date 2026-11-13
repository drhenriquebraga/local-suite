"""Exercise embedded plugin code and authenticated offline extraction."""
import base64
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
import radai_plugin_bootstrap as bootstrap
import radai_plugins
import radai_plugin_seeds


def seed_bytes(plugin_id):
    return zlib.decompress(base64.b64decode(radai_plugin_seeds.SEEDS[plugin_id]['archive']))


def modified_zip(plugin_id, additions=(), prefix=''):
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(seed_bytes(plugin_id))) as source, \
            zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as dest:
        for name in source.namelist():
            dest.writestr(prefix + name, source.read(name))
        for name, raw in additions:
            dest.writestr(prefix + name, raw)
    return output.getvalue()


class PluginBootstrap(unittest.TestCase):
    def test_single_plugin_cli_uses_only_requested_suite_code_seed(self):
        with patch.object(sys,'argv',['bootstrap','--suite-root','SYNTHETIC','--base-only','--plugin','lung-rt']),patch.object(bootstrap,'ensure_base',return_value=True) as ensure:
            self.assertEqual(bootstrap.main(),0)
            self.assertEqual(ensure.call_count,1)
            self.assertEqual(ensure.call_args.args,('SYNTHETIC','lung-rt'))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='suite-plugin-bootstrap-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'suite'
        self.root.mkdir()
        for name in ('radai_panel.py', 'radai_ui.py'):
            (self.root / name).write_text('# synthetic base marker\n')
        (self.root / 'entrega.txt').write_text('PROJETO=LOCAL_SUITE\nVERSAO=8.24\n')
        self.headers = {'contract': radai_plugins.HOST_CONTRACT, 'version': '8.24'}

    def test_actual_embedded_code_bootstraps_both_plugins_without_extra_resources(self):
        keeps = []
        for plugin_id, label in bootstrap._IDS.items():
            folder = self.root / 'Plugins' / label
            data = folder / 'data/cases.db'
            config = folder / 'config/local.json'
            for path, value in ((data, b'synthetic existing case'), (config, b'{"synthetic":true}')):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(value)
                keeps.append((path, value))
        with patch('urllib.request.urlopen', side_effect=AssertionError('No downloads during base bootstrap')):
            for plugin_id, label in bootstrap._IDS.items():
                with self.subTest(plugin_id=plugin_id):
                    self.assertTrue(bootstrap.ensure_base(self.root, plugin_id, installed_only=False))
                    state = radai_plugins.discover_plugin(self.root, plugin_id, self.headers)
                    self.assertEqual(state['state'], 'ready', state)
                    self.assertEqual(state['active_version'], radai_plugin_seeds.SEEDS[plugin_id]['version'])
                    plugin = self.root / 'Plugins' / label
                    self.assertFalse(list((plugin / 'config').glob('consent*')))
                    for directory in ('models', 'resources'):
                        self.assertFalse([path for path in (plugin / directory).rglob('*') if path.is_file()])
                    installed = json.loads((plugin / 'installation.json').read_text())
                    self.assertIsNone(installed.get('resources'))
                    self.assertFalse(installed.get('reports_installed', False))
        self.assertFalse((self.root / 'python').exists())
        self.assertFalse((self.root / '.venv').exists())
        for path, value in keeps:
            self.assertEqual(path.read_bytes(), value)

    def test_current_or_newer_installation_is_not_replaced_by_an_older_seed(self):
        for plugin_id in bootstrap._IDS:
            with self.subTest(plugin_id=plugin_id):
                self.assertTrue(bootstrap.ensure_base(self.root, plugin_id, installed_only=False))
                record = dict(radai_plugin_seeds.SEEDS[plugin_id], version='0.1')
                label = bootstrap._IDS[plugin_id]
                pointer = self.root / 'Plugins' / label / 'installation.json'
                before = pointer.read_bytes()
                with patch.object(bootstrap, '_seed', return_value=record), \
                        patch.object(bootstrap, 'seed_source', side_effect=AssertionError('Do not downgrade')):
                    self.assertTrue(bootstrap.ensure_base(self.root, plugin_id, installed_only=False))
                self.assertEqual(pointer.read_bytes(), before)

    def test_unknown_resource_entry_is_not_extracted(self):
        for plugin_id in bootstrap._IDS:
            with self.subTest(plugin_id=plugin_id):
                destination = Path(self.temp.name) / ('unknown-' + plugin_id)
                destination.mkdir()
                unknown = ('models/extra/untrusted.bin' if plugin_id == 'neuro-rt'
                           else 'resources/extra/untrusted.bin')
                raw = modified_zip(plugin_id, [(unknown, b'not part of a trusted recipe')])
                with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                    bootstrap._extract(archive, destination, plugin_id)
                self.assertFalse((destination / unknown).exists())

    def test_resource_size_mismatch_fails_before_copying_code(self):
        for plugin_id in bootstrap._IDS:
            with self.subTest(plugin_id=plugin_id):
                destination = Path(self.temp.name) / ('size-' + plugin_id)
                destination.mkdir()
                with zipfile.ZipFile(io.BytesIO(seed_bytes(plugin_id))) as source:
                    manifest = json.loads(source.read('release-manifest.json'))
                    code = {record['path']: record for record in manifest['files']}
                    assets = bootstrap._assets(source, '', code, plugin_id)
                name, expected = next((name, record) for name, record in assets.items() if record['size'] > 0)
                raw = modified_zip(plugin_id, [(name, b'')])
                with zipfile.ZipFile(io.BytesIO(raw)) as archive, self.assertRaises(ValueError):
                    bootstrap._extract(archive, destination, plugin_id)
                self.assertEqual(list(destination.iterdir()), [])

    def test_single_wrapper_folder_is_supported(self):
        for plugin_id in bootstrap._IDS:
            with self.subTest(plugin_id=plugin_id):
                destination = Path(self.temp.name) / ('wrapped-' + plugin_id)
                destination.mkdir()
                raw = modified_zip(plugin_id, prefix='Bundle/')
                with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                    bootstrap._extract(archive, destination, plugin_id, code_only=True)
                self.assertTrue((destination / 'release-manifest.json').is_file())
                self.assertFalse((destination / 'Bundle').exists())

    def test_traversal_entry_is_rejected_before_copying(self):
        destination = Path(self.temp.name) / 'escape'
        destination.mkdir()
        raw = modified_zip('neuro-rt', [('../outside.txt', b'bad')])
        with zipfile.ZipFile(io.BytesIO(raw)) as archive, self.assertRaises(ValueError):
            bootstrap._extract(archive, destination, 'neuro-rt')
        self.assertFalse((destination.parent / 'outside.txt').exists())
        self.assertEqual(list(destination.iterdir()), [])

    def test_explicit_offline_selection_rejects_a_light_setup_without_downloads(self):
        for plugin_id in bootstrap._IDS:
            with self.subTest(plugin_id=plugin_id):
                path = Path(self.temp.name) / (plugin_id + '.zip')
                path.write_bytes(seed_bytes(plugin_id))
                row = {'id': plugin_id, 'accepted': True, 'source': str(path),
                       'consent': dict(radai_plugin_seeds.SEEDS[plugin_id]['policy'], accepted=True)}
                with patch('urllib.request.urlopen', side_effect=AssertionError('Explicit offline must stay offline')):
                    result = bootstrap.install_selection(self.root, {'plugins': [row]})
                self.assertFalse(result[0]['ok'])
                self.assertIn('offline', result[0]['reason'].lower())
                installed = radai_plugins.discover_plugin(self.root,plugin_id,self.headers)
                self.assertEqual(installed['state'],'ready',installed)
                self.assertEqual(installed['active_version'],radai_plugin_seeds.SEEDS[plugin_id]['version'])
                self.assertFalse((self.root/'Plugins'/bootstrap._IDS[plugin_id]/'models').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
