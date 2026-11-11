"""Safe failure evidence: synthetic resources only, no external network or installer process."""
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'app'))
import radai_lung_install as SDK
import radai_plugin_setup as WORKER


class DownloadEvidence(unittest.TestCase):
    def test_resource_failure_identifies_component_phase_and_http_status_safely(self):
        with tempfile.TemporaryDirectory() as temp:
            dest=Path(temp)/'runtime.zip'
            resource={'filename':'runtime.zip','size':1,'sha256':'0'*64,'url':'https://private.invalid/secret-token'}
            error=HTTPError(resource['url'],403,'secret token',{},None)
            events=[]
            with patch.object(SDK,'_request',side_effect=error):
                with self.assertRaises(SDK.LungInstallError) as found:
                    SDK._install_resource(None,'xray/'+'a'*40+'/runtime.zip',dest,dest,resource,False,events.append)
            self.assertEqual(found.exception.error_code,'DOWNLOAD_FAILED')
            self.assertEqual(found.exception.error_reason,'HTTP_403')
            self.assertEqual(found.exception.error_component,'medgemma-runtime')
            self.assertEqual(found.exception.error_phase,'DOWNLOAD')
            self.assertNotIn('secret',str(found.exception))
            self.assertEqual(events[0]['component'],'medgemma-runtime')

    def test_integrity_failure_is_distinct_from_network_failure(self):
        class Response(io.BytesIO):
            def geturl(self):return 'https://public.invalid/synthetic'
        with tempfile.TemporaryDirectory() as temp,patch.object(SDK,'_request',return_value=Response(b'X')):
            with self.assertRaises(SDK.LungInstallError) as found:
                SDK._download(['https://public.invalid/synthetic'],Path(temp)/'file',1,hashlib.sha256(b'Y').hexdigest())
            self.assertEqual(found.exception.error_reason,'HASH_MISMATCH')
            self.assertFalse((Path(temp)/'file').exists())

    def test_ct_failures_identify_the_exact_resource_instead_of_generic_model(self):
        with tempfile.TemporaryDirectory() as temp:
            dest=Path(temp)/'vision.data0'
            resource={'size':1,'sha256':'0'*64,'url':'https://private.invalid/secret'}
            with patch.object(SDK,'_request',side_effect=HTTPError(resource['url'],403,'private',{},None)):
                with self.assertRaises(SDK.LungInstallError) as found:
                    SDK._install_resource(None,'models/nv-reason-ct-int4/vision.data0',dest,dest,resource,False,None)
            self.assertEqual(found.exception.error_component,'nv-reason-ct-vision.data0')
            self.assertEqual(found.exception.error_reason,'HTTP_403')

    def test_offline_missing_resource_never_tries_network(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(SDK,'_request',side_effect=AssertionError('network forbidden')) as request:
            path=Path(temp)/'missing'
            with self.assertRaises(SDK.LungInstallError) as found:
                SDK._install_resource(None,'models/demo.bin',path,path,{'id':'ct-test','size':1,'sha256':'0'*64},True,lambda event:None)
            self.assertEqual(found.exception.error_code,'LOCAL_RESOURCES_MISSING')
            self.assertEqual(found.exception.error_component,'ct-test')
            request.assert_not_called()

    def worker(self,runner):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name);transaction='a'*32
        plan=root/'Plugins/LUNG RT/staging/external'/transaction/'plan.json';plan.parent.mkdir(parents=True)
        raw=json.dumps({'schema':WORKER.SCHEMA,'plugin_id':'lung-rt','transaction_id':transaction,'nonce':'b'*64,'old_pid':12345,'port':8777,'suite_root':str(root),'python':sys.executable,'payload':{}}).encode()
        plan.write_bytes(raw)
        result=WORKER.run_worker(plan,hashlib.sha256(raw).hexdigest(),43210,runner=runner,wait_old=lambda *args:True,reopen=lambda *args:True)
        self.assertEqual(result,1)
        return json.loads((plan.parent/'result.json').read_bytes()),(plan.parent/'progress.log').read_text(encoding='utf8')

    def test_worker_persists_safe_fields_and_never_raw_exception_or_url(self):
        def runner(plan,progress):
            error=SDK.LungInstallError('DOWNLOAD_FAILED','secret path https://private.invalid/token')
            error.error_component='medgemma-runtime';error.error_phase='DOWNLOAD';error.error_reason='HTTP_403'
            raise error
        result,log=self.worker(runner)
        self.assertEqual(result['error_component'],'medgemma-runtime')
        self.assertEqual(result['error_phase'],'DOWNLOAD')
        self.assertEqual(result['error_reason'],'HTTP_403')
        self.assertTrue(result['reopened'])
        self.assertNotIn('secret',json.dumps(result)+log)
        self.assertNotIn('https:',json.dumps(result)+log)

    def test_worker_keeps_last_component_when_sdk_has_no_typed_diagnostics(self):
        def runner(plan,progress):
            progress({'stage':'resources','resource_stage':'downloading','component':'MRI_Meningioma'})
            raise OSError('secret path')
        result,log=self.worker(runner)
        self.assertEqual(result['error_component'],'MRI_Meningioma')
        self.assertEqual(result['error_phase'],'DOWNLOADING')
        self.assertEqual(result['error_reason'],'IO_ERROR')
        self.assertNotIn('secret',json.dumps(result)+log)

    def test_worker_rejects_urls_or_arbitrary_text_in_diagnostic_fields(self):
        def runner(plan,progress):
            error=ValueError('private token')
            error.error_component='https://private.invalid/secret';error.error_phase='private/path';error.error_reason='PRIVATE_SECRET'
            raise error
        result,log=self.worker(runner)
        self.assertNotIn('error_component',result)
        self.assertNotIn('error_phase',result)
        self.assertEqual(result['error_reason'],'VALIDATION_FAILED')
        self.assertNotIn('private',json.dumps(result)+log)


if __name__=='__main__':unittest.main(verbosity=2)
