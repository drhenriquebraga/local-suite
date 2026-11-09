import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
import radai_lung_install as I
import radai_plugins as P
import radai_install_profile as Profile

class Installation(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='suite-lung-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'suite';self.root.mkdir()
        (self.root/'entrega.txt').write_text('PROJETO=LOCAL_SUITE\nVERSAO=8.14\n')

    def package(self, resources=None, *, version='1.0.0'):
        source=Path(self.tmp.name)/('package-'+version);source.mkdir(exist_ok=True)
        code=source/'code';code.mkdir(exist_ok=True)
        recipe = [
            {'path': name, 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
             'url': 'https://example.invalid/' + name}
            for name, data in (resources or {}).items()
        ]
        values={'module.json':json.dumps({'schema':'lung-rt/plugin-manifest/1','id':'lung-rt',
            'version':version,'host_contract':'local-suite/plugins/1','host_min_version':'8.14',
            'python':'>=3.10,<3.15','adapter':'integration/local_suite.py:mount'}),
            'integration/local_suite.py':'def mount(app,code,host_services=None): return {}\n',
            'catalog/resource_recipe.json':json.dumps({'files':recipe})}
        files=[]
        for name,value in values.items():
            path=code/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(value,encoding='utf8')
            raw=path.read_bytes();files.append({'path':'code/'+name,'size':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
        raw=json.dumps({'schema':'lung-rt/release-package/1','plugin_id':'lung-rt','version':version,'files':files}).encode()
        (source/'release-manifest.json').write_bytes(raw)
        pin=hashlib.sha256(raw).hexdigest()
        return source,pin

    def plan(self,source):
        return dict(I.inspect_local_source(source),schema='lung-rt/external-plan/1',reports=False)

    def discover(self):
        return P.discover_plugin(self.root, 'lung-rt', {'contract': P.HOST_CONTRACT, 'version': '8.14'})

    def test_untrusted_package_does_not_run_or_write(self):
        source,pin=self.package()
        with self.assertRaises(ValueError):I.inspect_local_source(source)
        self.assertFalse((self.root/'Plugins').exists())

    def test_local_install_integrity_and_preserved_data(self):
        source,pin=self.package()
        data=self.root/'Plugins/LUNG RT/data';data.mkdir(parents=True);(data/'cases.db').write_bytes(b'private fixture')
        with patch.object(I,'TRUSTED_CODE_INVENTORIES',frozenset([pin])):
            result=I.run_external(self.plan(source),lambda x:None,suite_root=self.root,host_python=sys.executable)
        self.assertEqual(result['state'],'ready');self.assertEqual((data/'cases.db').read_bytes(),b'private fixture')
        with patch.object(I,'TRUSTED_CODE_INVENTORIES',frozenset([pin])):
            discovered=self.discover()
        self.assertEqual(discovered['state'],'ready',discovered)
        self.assertFalse((self.root/'python').exists())

    def test_code_corruption_preserves_active_pointer(self):
        source,pin=self.package()
        pointer=self.root/'Plugins/LUNG RT/installation.json';pointer.parent.mkdir(parents=True);pointer.write_text('{"active_version":"0.9"}')
        with patch.object(I,'TRUSTED_CODE_INVENTORIES',frozenset([pin])):
            plan=self.plan(source);(source/'code/integration/local_suite.py').write_text('untrusted')
            with self.assertRaises(ValueError):I.run_external(plan,None,suite_root=self.root,host_python=sys.executable)
        self.assertEqual(json.loads(pointer.read_text())['active_version'],'0.9')

    def test_reports_default_off_never_downloads_models(self):
        source,pin=self.package({'models/demo.bin': b'demo'})
        with patch.object(I,'TRUSTED_CODE_INVENTORIES',frozenset([pin])),patch.object(I,'_download',side_effect=AssertionError('download forbidden')):
            I.run_external(self.plan(source),None,suite_root=self.root,host_python=sys.executable)
        self.assertFalse((self.root/'Plugins/LUNG RT/resources').exists())

    def test_failed_resource_keeps_previous_installation(self):
        source,pin=self.package({'models/demo.bin': b'demo'})
        pointer=self.root/'Plugins/LUNG RT/installation.json';pointer.parent.mkdir(parents=True);pointer.write_text('{"active_version":"0.9"}')
        with patch.object(I,'TRUSTED_CODE_INVENTORIES',frozenset([pin])),patch.object(I,'_download',side_effect=ValueError('synthetic network failure')):
            plan=dict(self.plan(source),reports=True)
            with self.assertRaises(ValueError):I.run_external(plan,None,suite_root=self.root,host_python=sys.executable)
        self.assertEqual(json.loads(pointer.read_text())['active_version'],'0.9')

    def test_failed_upgrade_preserves_active_resources_after_first_copy(self):
        model = 'models/demo.bin'
        old_source, old_pin = self.package({model: b'old'})
        new_source, new_pin = self.package({model: b'new', 'runtimes/required.bin': b'required'},
                                          version='1.1.0')
        for source, data in ((old_source, b'old'), (new_source, b'new')):
            offline_file = source / 'resources' / model
            offline_file.parent.mkdir(parents=True)
            offline_file.write_bytes(data)

        plugin = self.root / 'Plugins/LUNG RT'
        pointer = plugin / 'installation.json'
        progress = []
        with patch.object(I, 'TRUSTED_CODE_INVENTORIES', {old_pin, new_pin}):
            I.run_external(dict(self.plan(old_source), reports=True), None,
                           suite_root=self.root, host_python=sys.executable)
            before = pointer.read_bytes()
            state = json.loads(before)
            active_model = plugin / state.get('resources_path', '') / model
            with patch.object(I, '_download', side_effect=ValueError('second resource failed')) as download:
                with self.assertRaisesRegex(ValueError, 'second resource failed'):
                    I.run_external(dict(self.plan(new_source), reports=True), progress.append,
                                   suite_root=self.root, host_python=sys.executable)
                download.assert_called_once()
            self.assertEqual(self.discover()['active_version'], '1.0.0')

        completed = [event for event in progress if event.get('resource_stage') == 'complete']
        self.assertEqual(len(completed), 1)
        self.assertEqual(pointer.read_bytes(), before)
        self.assertEqual(active_model.read_bytes(), b'old')

    def test_interrupted_same_version_repair_keeps_active_code_discoverable(self):
        source, pin = self.package()
        plugin = self.root / 'Plugins/LUNG RT'
        pointer = plugin / 'installation.json'
        replace = os.replace

        with patch.object(I, 'TRUSTED_CODE_INVENTORIES', {pin}):
            plan = self.plan(source)
            I.run_external(plan, None, suite_root=self.root, host_python=sys.executable)
            before = pointer.read_bytes()
            first = self.discover()
            self.assertEqual(first['state'], 'ready', first)
            old_code = Path(first['code_dir'])

            def interrupt_after_code_move(src, dest):
                replace(src, dest)
                if Path(src) == old_code or Path(dest).is_relative_to(plugin / 'versions'):
                    raise KeyboardInterrupt('interrupted before pointer commit')

            with patch.object(I.os, 'replace', side_effect=interrupt_after_code_move):
                with self.assertRaisesRegex(KeyboardInterrupt, 'before pointer commit'):
                    I.run_external(plan, None, suite_root=self.root, host_python=sys.executable)

            self.assertEqual(pointer.read_bytes(), before)
            self.assertTrue(old_code.is_dir())
            after = self.discover()
            self.assertEqual(after['state'], 'ready', after)
            self.assertEqual(after['code_dir'], first['code_dir'])

    def test_discovery_rejects_rewritten_code_inventory_and_pointer(self):
        source, pin = self.package()
        with patch.object(I, 'TRUSTED_CODE_INVENTORIES', {pin}):
            I.run_external(self.plan(source), None, suite_root=self.root, host_python=sys.executable)
            installed = self.discover()
        self.assertEqual(installed['state'], 'ready', installed)
        code = Path(installed['code_dir'])
        new_adapter = b'def mount(app, code, host_services=None): return {"altered": True}\n'
        (code / 'integration/local_suite.py').write_bytes(new_adapter)
        inventory = code / 'release-manifest.json'
        contents = json.loads(inventory.read_bytes())
        adapter = next(row for row in contents['files'] if row['path'] == 'code/integration/local_suite.py')
        adapter.update(size=len(new_adapter), sha256=hashlib.sha256(new_adapter).hexdigest())
        altered = json.dumps(contents).encode()
        inventory.write_bytes(altered)
        altered_pin = hashlib.sha256(altered).hexdigest()

        with patch.object(I, 'TRUSTED_CODE_INVENTORIES', {pin, altered_pin}):
            self.assertEqual(self.discover()['state'], 'failed', 'manifest must match the active pointer')
        pointer = self.root / 'Plugins/LUNG RT/installation.json'
        state = json.loads(pointer.read_bytes())
        state['inventory_sha256'] = altered_pin
        pointer.write_text(json.dumps(state), encoding='utf-8')
        with patch.object(I, 'TRUSTED_CODE_INVENTORIES', {pin}):
            self.assertEqual(self.discover()['state'], 'failed', 'pointer must match the host allowlist')

    def test_old_host_cannot_activate_new_plugin(self):
        source,pin=self.package();(self.root/'entrega.txt').write_text('VERSAO=8.1\n')
        with patch.object(I,'TRUSTED_CODE_INVENTORIES',frozenset([pin])):
            with self.assertRaises(ValueError):I.run_external(self.plan(source),None,suite_root=self.root,host_python=sys.executable)
        self.assertFalse((self.root/'Plugins/LUNG RT/installation.json').exists())

    def test_github_block_falls_back_for_detection(self):
        digest='a'*64
        def remote(url):
            if url==I.GITHUB:raise OSError('blocked by clinic')
            return {'schema':'lung-rt-update/1','version':'1.0.0','size':100,'sha256':digest}
        with patch.object(I,'_remote_json',side_effect=remote):r=I.check_latest('0.9')
        self.assertEqual(r['state'],'available');self.assertEqual(r['origin'],'mirror');self.assertIn('/v1.0.0/',r['urls'][0])

    def test_truncated_download_uses_next_mirror_and_verifies(self):
        class Response(io.BytesIO):
            def geturl(self):return 'https://example.invalid/file'
        dest=Path(self.tmp.name)/'download.zip';good=b'synthetic complete'
        with patch.object(I,'_request',side_effect=[Response(b'bad'),Response(good)]):
            I._download(['https://a.invalid','https://b.invalid'],dest,len(good),hashlib.sha256(good).hexdigest())
        self.assertEqual(dest.read_bytes(),good);self.assertEqual(list(dest.parent.glob('*.part-*')),[])

    def test_zip_traversal_and_windows_names_rejected(self):
        for name in ('../evil.py','C:/evil.py','code/CON.txt','code/a:stream','code/a/../b.py'):
            with self.subTest(name=name):
                path=Path(self.tmp.name)/'bad.zip'
                with zipfile.ZipFile(path,'w') as z:z.writestr(name,b'bad')
                with self.assertRaises(ValueError):I.Package(path)

    def test_profile_defaults_and_malformed_stamp(self):
        self.assertEqual(Profile.perfil(self.root),'full')
        stamp=self.root/'suite-profile.json';stamp.write_text('{bad')
        self.assertEqual(Profile.perfil(self.root),'lung-rt')
        stamp.write_text(json.dumps({'schema':Profile.SCHEMA,'profile':'lung-rt'}))
        self.assertFalse(Profile.completo(self.root))

if __name__=='__main__':unittest.main(verbosity=2)
