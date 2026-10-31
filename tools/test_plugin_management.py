import os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).absolute().parent))
import _componentes
_componentes.ligar_caminho()
import _cleanup
_cleanup.adotar_prefixo('radai_plugin_management_')
BASE=Path(_cleanup.temporaria('radai_plugin_management_'))
os.environ['RADAI_CALIB_DIR']=str(BASE/'calib')
os.environ['RADAI_REGISTRO_DIR']=str(BASE/'registro')
os.environ['RADAI_NAVEGADOR']='0'
from fastapi import FastAPI
from fastapi.testclient import TestClient
import radai_plugins as P
import radai_neuro_install as N
try:
 import radai_plugin_setup_ui as U
except ImportError:
 U=None

class Management(unittest.TestCase):
 def setUp(self):
  self.root=Path(tempfile.mkdtemp(dir=BASE))
  self.provider=N.build_provider(self.root,{'version':'8.12','python_executable':sys.executable},{})
  for obj,name,value in [(N,'build_provider',self.provider),(self.provider,'status',{'state':'idle'}),
    (self.provider,'check_plugin_release',{'state':'unavailable'}),
    (self.provider,'refresh_plugin_release',{'state':'available','version':'1.1.0'}),
    (self.provider,'request_plugin_update',{'state':'external_install','scheduled':True}),
    (N,'inspect_local_source',{'version':'1.1.0','kind':'bundle','trusted':True}),
    (N,'prepare_external_plan',{'schema':'neuro-rt/external-plan/1','mode':'local','version':'1.1.0'})]:
   item=patch.object(obj,name,create=True,return_value=value);mock=item.start();self.addCleanup(item.stop)
   if name=='inspect_local_source':self.inspect=mock
   if name=='prepare_external_plan':self.prepare=mock
   if name=='request_plugin_update':self.update=mock
   if name=='refresh_plugin_release':self.refresh=mock
  app=FastAPI();self.entry=P.montar(app,{'suite_root':self.root,'neuro_host_version':'8.12'})
  self.client=TestClient(app,base_url='http://localhost')
  self.headers={'origin':'http://localhost','x-neuro-plugin-token':self.entry['token']}
 def ack(self):
  p=self.provider.consent_policy();return {'accepted':True,'version':p['version'],'digest':p['digest']}
 def source(self):
  response=self.client.post('/api/plugins/neuro-rt/local/inspect',json={'folder':str(self.root)},headers=self.headers)
  self.assertEqual(response.status_code,200,response.text)
  return response.json()['source_id']
 def test_inspecao_local_exige_token_e_mantem_plano_no_servidor(self):
  route='/api/plugins/neuro-rt/local/inspect'
  self.assertEqual(self.client.post(route,json={'folder':str(self.root)}).status_code,403)
  self.assertEqual(self.inspect.call_count,0)
  response=self.client.post(route,json={'folder':str(self.root)},headers=self.headers)
  self.assertEqual(response.status_code,200,response.text)
  data=response.json();self.assertTrue(data['source_id']);self.assertEqual(data['version'],'1.1.0')
  self.assertNotIn('plan',data);self.assertNotIn('folder',data)
 def test_fonte_incompleta_orienta_extracao_sem_expor_detalhe(self):
  class LocalError(ValueError):source_hint='extract_setup'
  self.inspect.side_effect=LocalError('synthetic private internal path')
  response=self.client.post('/api/plugins/neuro-rt/local/inspect',json={'folder':str(self.root)},headers=self.headers)
  self.assertEqual(response.status_code,400)
  detail=response.json()['detail'];self.assertIsInstance(detail,dict)
  self.assertEqual(detail['source_hint'],'extract_setup');self.assertNotIn('synthetic private',str(detail))
 def test_refresh_real_independe_de_aceite(self):
  route='/api/plugins/neuro-rt/refresh'
  self.assertEqual(self.client.post(route,json={}).status_code,403)
  response=self.client.post(route,json={},headers=self.headers)
  self.assertEqual(response.status_code,200,response.text)
  self.assertEqual(response.json()['version'],'1.1.0');self.refresh.assert_called_once()
 def test_instalacao_local_revalida_fonte_e_exige_aceite(self):
  source=self.source();body={'confirm':True,'source_id':source}
  route='/api/plugins/neuro-rt/install'
  self.assertEqual(self.client.post(route,json=body,headers=self.headers).status_code,400)
  self.assertEqual(self.update.call_count,0)
  body['consent']=self.ack()
  response=self.client.post(route,json=body,headers=self.headers)
  self.assertEqual(response.status_code,202,response.text)
  self.prepare.assert_called_once();self.assertEqual(self.update.call_args.kwargs['plan']['mode'],'local')
 def test_fonte_desconhecida_ou_alterada_nao_inicia_instalacao(self):
  route='/api/plugins/neuro-rt/install';body={'confirm':True,'source_id':'unknown','consent':self.ack()}
  self.assertEqual(self.client.post(route,json=body,headers=self.headers).status_code,400)
  self.update.assert_not_called()
  body['source_id']=self.source();self.prepare.side_effect=ValueError('synthetic package changed')
  self.assertEqual(self.client.post(route,json=body,headers=self.headers).status_code,400)
  self.update.assert_not_called()
 def test_plano_enviado_pelo_cliente_nao_e_aceito(self):
  body={'confirm':True,'consent':self.ack(),'plan':{'python':'untrusted.exe'}}
  self.assertEqual(self.client.post('/api/plugins/neuro-rt/install',json=body,headers=self.headers).status_code,400)
  self.update.assert_not_called()
 def test_configuracao_tem_gestao_local_e_online_sem_duplicar(self):
  self.assertIsNotNone(U,'A gestão do plugin nas configurações ainda não existe')
  page='<html><body><nav class="cfg-cards"> <a class="cfg-card" href="#ps_limpar"></a></nav><section class="ps-cx fechado" id="ps_limpar" hidden></section></body></html>'
  result=U.config_page(page)
  for name in ('ps_neuro','neuro-update','neuro-local-folder','neuro-local-browse','neuro-local-inspect','neuro-release-refresh'):
   self.assertIn('id="'+name+'"',result)
  self.assertIn('data-neuro-settings="1"',result)
  self.assertIn('data-neuro-host-browse="1"',result)
  self.assertEqual(U.config_page(result),result)
  self.assertNotIn('transition:',result)

if __name__=='__main__':unittest.main(verbosity=2)
