import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'app'), str(ROOT/'tools')]
import radai_lung_install as SDK
import test_lung_install as fixtures


class WeightOperations(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.Installation()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.payload = b'SYNTHETIC WEIGHT ONLY'
        self.resource = 'models/demo.bin'
        self.old, old_pin = self.fixture.package({self.resource:self.payload}, version='1.1.1')
        self.new, new_pin = self.fixture.package({self.resource:self.payload}, version='1.1.2')
        self.old_pin = old_pin
        self.new_pin = new_pin
        self.pin = patch.object(SDK, 'TRUSTED_CODE_INVENTORIES', {old_pin,new_pin})
        self.pin.start()
        self.addCleanup(self.pin.stop)
        SDK.run_external(self.fixture.plan(self.new), None, suite_root=self.root, host_python=sys.executable)
        self.pointer = self.root/'Plugins/LUNG RT/installation.json'
        self.before = json.loads(self.pointer.read_bytes())
        local = self.old/'resources'/self.resource
        local.parent.mkdir(parents=True)
        local.write_bytes(self.payload)
        (self.old/'.lung-offline-preparation.json').write_text(json.dumps({
            'schema':'lung-rt/offline-preparation/1','complete':True,'code_pin':old_pin}), encoding='utf8')

    def test_old_weight_bundle_preserves_new_code_and_records_bundle_version(self):
        plan = dict(self.fixture.plan(self.old), reports=True, resources_only=True)
        with patch.object(SDK,'_download',side_effect=AssertionError('network forbidden')):
            SDK.run_external(plan,None,suite_root=self.root,host_python=sys.executable)
        after = json.loads(self.pointer.read_bytes())
        for key in ('active_version','code_path','inventory_sha256'):
            self.assertEqual(after[key], self.before[key], key)
        self.assertEqual(after['resource_bundle_version'],'1.1.1')
        self.assertEqual((self.root/'Plugins/LUNG RT'/after['resources_path']/self.resource).read_bytes(), self.payload)
        self.assertFalse((self.root/'python').exists())

    def test_online_weights_use_active_code_without_release_or_code_download(self):
        with patch.object(SDK,'check_latest',side_effect=AssertionError('code metadata not needed')):
            plan = SDK.prepare_external_plan({'resources_only':True,'installed_version':'1.1.2'})
        self.assertEqual(plan['source'],'installed')
        with patch.object(SDK,'check_latest',side_effect=AssertionError('code release not needed')), \
             patch.object(SDK,'_download') as download:
            def model(urls,destination,size,digest,progress):
                self.assertEqual(size,len(self.payload))
                destination.parent.mkdir(parents=True,exist_ok=True)
                destination.write_bytes(self.payload)
            download.side_effect=model
            SDK.run_external(plan,None,suite_root=self.root,host_python=sys.executable)
        self.assertEqual(json.loads(self.pointer.read_bytes())['code_path'],self.before['code_path'])
        download.assert_called_once()

    def test_incomplete_offline_weights_preserve_active_code(self):
        (self.old/'resources'/self.resource).unlink()
        plan = dict(self.fixture.plan(self.old), reports=True, resources_only=True)
        with patch.object(SDK,'_download',side_effect=AssertionError('network forbidden')):
            with self.assertRaises(ValueError):
                SDK.run_external(plan,None,suite_root=self.root,host_python=sys.executable)
        self.assertEqual(json.loads(self.pointer.read_bytes())['code_path'],self.before['code_path'])

    def test_wrapped_code_and_weight_packages_are_logically_identical(self):
        archive = self.old.parent/'wrapped.zip'
        with zipfile.ZipFile(archive,'w') as output:
            output.writestr('README.txt','SYNTHETIC TEST')
            output.writestr('START_HERE_TO_INSTALL_LUNG_RT.cmd','@exit /b 0')
            for path in self.old.rglob('*'):
                if path.is_file():output.write(path,'programa/'+path.relative_to(self.old).as_posix())
        description = SDK.inspect_local_source(archive)
        self.assertTrue(description['offline'])
        self.assertEqual(description['inventory_sha256'],self.old_pin)

    def test_code_update_preserves_independent_weight_version(self):
        SDK.run_external(dict(self.fixture.plan(self.old),reports=True,resources_only=True),None,
                         suite_root=self.root,host_python=sys.executable)
        SDK.run_external(self.fixture.plan(self.new),None,suite_root=self.root,host_python=sys.executable)
        after = json.loads(self.pointer.read_bytes())
        self.assertEqual(after['active_version'],'1.1.2')
        self.assertEqual(after['resource_bundle_version'],'1.1.1')

    def test_older_code_is_rejected_without_changing_active_installation(self):
        before=self.pointer.read_bytes()
        with self.assertRaises(SDK.LungInstallError) as error:
            SDK.run_external(self.fixture.plan(self.old),None,suite_root=self.root,host_python=sys.executable)
        self.assertEqual(error.exception.error_code,'CODE_DOWNGRADE_BLOCKED')
        self.assertEqual(self.pointer.read_bytes(),before)

    def test_full_offline_install_records_its_new_bundle_version(self):
        local=self.new/'resources'/self.resource;local.parent.mkdir(parents=True);local.write_bytes(self.payload)
        (self.new/'.lung-offline-preparation.json').write_text(json.dumps({
            'schema':'lung-rt/offline-preparation/1','complete':True,'code_pin':self.new_pin}),encoding='utf8')
        state=json.loads(self.pointer.read_bytes());state.update(resource_bundle_version='0.9',resource_recipe_sha256='0'*64)
        self.pointer.write_text(json.dumps(state),encoding='utf8')
        SDK.run_external(dict(self.fixture.plan(self.new),reports=True),None,suite_root=self.root,host_python=sys.executable)
        state=json.loads(self.pointer.read_bytes())
        self.assertEqual(state['resource_bundle_version'],'1.1.2')
        self.assertEqual(state['resource_source'],'offline_bundle')
        self.assertEqual(state['resource_recipe_sha256'],SDK._sha(self.new/'code/catalog/resource_recipe.json'))

    def test_upload_cleanup_never_removes_the_original_bundle_folder(self):
        from radai_plugin_setup import _cleanup_uploaded_source
        original=self.old/'original.zip';original.write_bytes(b'SYNTHETIC')
        _cleanup_uploaded_source(self.root,'lung-rt',{'path':str(original)})
        self.assertTrue(original.exists())
        copy=self.root/'Plugins/LUNG RT/staging/local-setup/setup-synthetic/setup.zip'
        copy.parent.mkdir(parents=True);copy.write_bytes(b'SYNTHETIC')
        _cleanup_uploaded_source(self.root,'lung-rt',{'path':str(copy)})
        self.assertFalse(copy.parent.exists())
        self.assertTrue(original.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
