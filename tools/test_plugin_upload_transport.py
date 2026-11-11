"""Real panel middleware plus both plugin routes; synthetic streamed ZIP transport only."""
import asyncio
from contextlib import ExitStack
import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
CONTOUR=Path(os.environ.get('CONTOURLAB_SOURCE',ROOT.parent/'CONTOURLAB'))
HOST_VERSION=next(line.split('=',1)[1].strip() for line in (ROOT/'entrega.txt').read_text(encoding='utf-8-sig').splitlines() if line.startswith('VERSAO='))
sys.path[:0]=[str(ROOT/'app'),str(CONTOUR/'app')]


class PanelPluginUploadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory=tempfile.TemporaryDirectory(prefix='panel-upload-synthetic-')
        cls.root=Path(cls.directory.name)
        (cls.root/'entrega.txt').write_bytes((ROOT/'entrega.txt').read_bytes())
        cls.stack=ExitStack()
        for name in ('RADAI_CALIB_DIR','RADAI_REGISTRO_DIR','TOTALSEG_HOME_DIR','RADAI_TMP'):
            cls.stack.enter_context(patch.dict(os.environ,{name:str(cls.root/name)}))
        config=cls.root/'watcher.config';config.write_text('ROOT=\nPORT=8777\n',encoding='ascii')
        cls.stack.enter_context(patch.dict(os.environ,{'RADAI_CONFIG':str(config)}))
        import radai_panel,radai_plugins,radai_lung_plugin,radai_lung_install,radai_neuro_install
        cls.lung=radai_lung_install;cls.neuro=radai_neuro_install
        cls.stack.enter_context(patch('radai_plugin_bootstrap.ensure_base',return_value=False))
        cls.stack.enter_context(patch.object(radai_lung_install,'check_latest',return_value={'state':'current'}))
        cls.stack.enter_context(patch('http.client.HTTPSConnection.connect',side_effect=AssertionError('External network forbidden in fixture')))
        cls.stack.enter_context(patch.object(radai_plugins,'_host_info',return_value={'contract':radai_plugins.HOST_CONTRACT,'version':HOST_VERSION,'python_executable':sys.executable}))
        original_panel=radai_panel.montar
        def panel(app,ler_vigia=None,config=None):
            return original_panel(app,ler_vigia,dict(config or {},suite_root=str(cls.root),arranque={'PORT':8777}))
        with patch.object(radai_panel,'montar',side_effect=panel):
            cls.watcher=importlib.import_module('radai_watcher')
        if (CONTOUR/'app/radai_watcher.py').is_file():
            assert Path(cls.watcher.__file__).resolve()==(CONTOUR/'app/radai_watcher.py').resolve()
        cls.app=cls.watcher.app
        cls.app.state.radai_reabertura={'encerrar':lambda:None}
        cls.entries={
            'neuro-rt':radai_plugins.montar(cls.app,{'suite_root':str(cls.root),'arranque':{'PORT':8777}}),
            'lung-rt':radai_lung_plugin.montar(cls.app,{'suite_root':str(cls.root),'port':8777})}
        from fastapi import Request
        @cls.app.post('/api/transport-test/read')
        async def read(request:Request):
            count=0
            async for chunk in request.stream():count+=len(chunk)
            return {'bytes':count}
        cls.watcher.montar_portao_do_host(cls.app,porta=8777)

    @classmethod
    def tearDownClass(cls):
        cls.entries['neuro-rt']['closed'].set()
        if cls.watcher._LOG_FH:
            cls.watcher._LOG_FH.close();cls.watcher._LOG_FH=None
        cls.stack.close();cls.directory.cleanup()

    def request(self,path,*,data=b'',headers=None,client_host='127.0.0.1'):
        import httpx
        async def send():
            transport=httpx.ASGITransport(app=self.app,client=(client_host,50000))
            async with httpx.AsyncClient(transport=transport,base_url='http://127.0.0.1:8777') as client:
                return await client.post(path,content=data,headers=headers or {})
        return asyncio.run(send())

    def headers(self,plugin,**extra):
        return {'Content-Type':'application/zip','X-'+('Neuro' if plugin=='neuro-rt' else 'Lung')+'-Plugin-Token':self.entries[plugin]['token'],**extra}

    def test_both_authenticated_weight_routes_stream_more_than_global_16mib(self):
        count=17*1024**2
        async def chunks():
            for _ in range(17):yield b'x'*1024**2
        seen=[]
        def neuro(path,**kwargs):
            seen.append(('neuro',path.stat().st_size,kwargs))
            return {'source_folder':str(path),'version':'1.3.0','kind':'offline_bundle','offline_ready':True}
        def lung(path):
            seen.append(('lung',path.stat().st_size,{}))
            return {'path':str(path),'version':'1.1.2','offline':True}
        with patch.object(self.neuro,'inspect_local_zip',side_effect=neuro),patch.object(self.lung,'inspect_local_source',side_effect=lung):
            for plugin in ('neuro-rt','lung-rt'):
                with self.subTest(plugin=plugin):
                    response=self.request('/api/plugins/'+plugin+'/local/upload?operation=weights',data=chunks(),headers=self.headers(plugin,**{'Content-Length':str(count)}))
                    self.assertEqual(response.status_code,200,response.text)
                    self.assertEqual(response.json()['operation'],'weights')
        self.assertEqual([row[1] for row in seen],[count,count])
        self.assertTrue(seen[0][2]['resources_only'])
        for key in ('NEURO RT','LUNG RT'):
            inbox=self.root/'Plugins'/key/'staging/local-setup'
            self.assertTrue(any(inbox.glob('setup-*/setup.zip')))

    def test_json_and_unauthorized_requests_keep_small_limit(self):
        count=17*1024**2
        response=self.request('/api/transport-test/read',headers={'Content-Type':'application/json','Content-Length':str(count)})
        self.assertEqual(response.status_code,413,response.text)
        for plugin in ('neuro-rt','lung-rt'):
            headers=self.headers(plugin,**{'Content-Length':str(count)})
            headers['X-'+('Neuro' if plugin=='neuro-rt' else 'Lung')+'-Plugin-Token']='wrong-token'
            response=self.request('/api/plugins/'+plugin+'/local/upload?operation=weights',headers=headers)
            self.assertIn(response.status_code,(403,413),response.text)
        self.assertEqual(self.watcher.TETO_DO_CORPO_BYTES,16*1024**2)

    def test_weight_header_above_16gib_is_rejected_before_receiving(self):
        for plugin in ('neuro-rt','lung-rt'):
            response=self.request('/api/plugins/'+plugin+'/local/upload?operation=weights',headers=self.headers(plugin,**{'Content-Length':str(16*1024**3+1)}))
            self.assertEqual(response.status_code,413,response.text)

    def test_only_same_origin_local_weight_operation_gets_the_large_allowance(self):
        count=17*1024**2
        async def chunks():
            for _ in range(17):yield b'x'*1024**2
        for plugin in ('neuro-rt','lung-rt'):
            path='/api/plugins/'+plugin+'/local/upload'
            for query in ('?operation=code','?operation=weights&operation=weights','?operation=','?operation=unknown'):
                response=self.request(path+query,headers=self.headers(plugin,**{'Content-Length':str(count)}))
                self.assertEqual(response.status_code,413,response.text)
            response=self.request(path+'?operation=weights',data=b'x',headers=self.headers(plugin,Origin='https://outside.invalid'))
            self.assertEqual(response.status_code,403,response.text)
            response=self.request(path+'?operation=weights',data=b'x',headers=self.headers(plugin),client_host='192.0.2.10')
            self.assertEqual(response.status_code,403,response.text)
            description=({'source_folder':'synthetic','version':'1.3.0','kind':'offline_bundle','offline_ready':True}
                         if plugin=='neuro-rt' else {'path':'synthetic','version':'1.1.2','offline':True})
            name='inspect_local_zip' if plugin=='neuro-rt' else 'inspect_local_source'
            with patch.object(self.neuro if plugin=='neuro-rt' else self.lung,name,return_value=description):
                response=self.request(path,data=chunks(),headers=self.headers(plugin,**{'Content-Length':str(count),'Origin':'http://127.0.0.1:8777'}))
            self.assertEqual(response.status_code,200,response.text)

    def test_chunked_json_still_enforces_real_byte_limit(self):
        async def chunks():
            for _ in range(17):yield b'x'*1024**2
        response=self.request('/api/transport-test/read',data=chunks(),headers={'Content-Type':'application/json'})
        self.assertEqual(response.status_code,413,response.text)

    def test_weight_stream_overflow_is_413_and_partial_upload_is_removed(self):
        async def chunks():
            for _ in range(3):yield b'x'*1024**2
        for plugin in ('neuro-rt','lung-rt'):
            inbox=self.root/'Plugins'/('NEURO RT' if plugin=='neuro-rt' else 'LUNG RT')/'staging/local-setup'
            before=set(inbox.glob('setup-*')) if inbox.exists() else set()
            with patch.object(self.watcher,'TETO_UPLOAD_PESOS_BYTES',2*1024**2):
                response=self.request('/api/plugins/'+plugin+'/local/upload?operation=weights',data=chunks(),headers=self.headers(plugin))
            self.assertEqual(response.status_code,413,response.text)
            self.assertEqual(set(inbox.glob('setup-*')),before)

    def test_full_panel_upload_to_offline_plan_installs_only_verified_resources(self):
        import radai_plugin_setup,radai_queue_state,radai_atualizar
        sys.path.insert(0,str(ROOT/'tools'))
        import test_lung_install as fixtures
        fixture=fixtures.Installation();fixture.setUp();self.addCleanup(fixture.doCleanups)
        payload=b'SYNTHETIC WEIGHT ONLY'*900000
        relative='models/demo.bin'
        old,oldpin=fixture.package({relative:payload},version='1.1.2')
        new,newpin=fixture.package({relative:payload},version='1.1.4')
        resource=old/'resources'/relative;resource.parent.mkdir(parents=True);resource.write_bytes(payload)
        (old/'.lung-offline-preparation.json').write_text(json.dumps({'schema':'lung-rt/offline-preparation/1','complete':True,'code_pin':oldpin}),encoding='utf8')
        archive=old.parent/'old-complete.zip'
        with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_STORED) as output:
            for file in old.rglob('*'):
                if file.is_file():output.write(file,file.relative_to(old).as_posix())
        self.assertGreater(archive.stat().st_size,16*1024**2)
        captured=[]
        class Installer:
            def __init__(self,*args,**kwargs):pass
            def launch(self,plan):captured.append(plan);return {'ok':True,'scheduled':True}
        async def chunks():
            with archive.open('rb') as incoming:
                while block:=incoming.read(1024**2):yield block
        with patch.object(self.lung,'TRUSTED_CODE_INVENTORIES',{oldpin,newpin}), \
             patch.object(self.lung,'_request',side_effect=AssertionError('external network forbidden')), \
             patch.object(radai_queue_state,'quem_tem_a_vez',return_value={'dono':None}), \
             patch.object(radai_queue_state,'fechando_ao_fim',return_value=False), \
             patch.object(radai_queue_state,'pedir_fechar_ao_fim'), \
             patch.object(radai_atualizar,'etapa',return_value='idle'), \
             patch.object(radai_plugin_setup,'ExternalInstaller',Installer):
            self.lung.run_external(fixture.plan(new),None,suite_root=self.root,host_python=sys.executable)
            pointer=self.root/'Plugins/LUNG RT/installation.json';before=json.loads(pointer.read_bytes())
            self.entries['lung-rt']['installation'].update(state='ready',active_version='1.1.4')
            response=self.request('/api/plugins/lung-rt/local/upload?operation=weights',data=chunks(),headers=self.headers('lung-rt',**{'Content-Length':str(archive.stat().st_size)}))
            self.assertEqual(response.status_code,200,response.text)
            policy=self.lung.CONSENT_POLICY
            body={'operation':'weights','source_id':response.json()['source_id'],'consent':{'accepted':True,'version':policy['version'],'digest':policy['digest']}}
            response=self.request('/api/plugins/lung-rt/install',data=json.dumps(body).encode(),headers={**self.headers('lung-rt'),'Content-Type':'application/json'})
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(len(captured),1)
            self.assertTrue(captured[0]['offline']);self.assertTrue(captured[0]['resources_only'])
            self.lung.run_external(captured[0],None,suite_root=self.root,host_python=sys.executable)
            after=json.loads(pointer.read_bytes())
            for key in ('active_version','code_path','inventory_sha256'):self.assertEqual(before[key],after[key])
            self.assertEqual(after['resource_bundle_version'],'1.1.2')
            self.assertEqual((self.root/'Plugins/LUNG RT'/after['resources_path']/relative).read_bytes(),payload)
            self.assertFalse((self.root/'python').exists())
        self.entries['lung-rt']['preparing']=False


if __name__=='__main__':unittest.main(verbosity=2)
