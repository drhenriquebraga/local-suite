import os,sys,unittest,json,tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).absolute().parent))
import _componentes
_componentes.ligar_caminho()
import _cleanup
_cleanup.adotar_prefixo("radai_neuro_host_")
BASE=Path(_cleanup.temporaria("radai_neuro_host_"))
os.environ["RADAI_CALIB_DIR"]=str(BASE/"calib")
os.environ["RADAI_REGISTRO_DIR"]=str(BASE/"registro")
os.environ["RADAI_NAVEGADOR"]="0"
from fastapi import FastAPI
from fastapi.testclient import TestClient
import radai_plugins as P
import radai_neuro_install as N

class NeuroHost(unittest.TestCase):
 def setUp(self):
  self.root=Path(tempfile.mkdtemp(dir=BASE));self.events=[]
  self.provider=N.build_provider(self.root,{"version":"8.10"},{})
  self.app=FastAPI()
  self.stack=patch.object(N,"build_provider",return_value=self.provider);self.stack.start();self.addCleanup(self.stack.stop)
  for name,value in (("check_plugin_release",{"state":"unavailable"}),("status",{"state":"idle"})):
   p=patch.object(self.provider,name,return_value=value);p.start();self.addCleanup(p.stop)
  def install():self.events.append("install");return {"state":"preparing"}
  def update(plugin,action):self.events.append(action);return {"state":"preparing"}
  p=patch.object(self.provider,"install",side_effect=install);p.start();self.addCleanup(p.stop)
  p=patch.object(self.provider,"request_plugin_update",side_effect=update);p.start();self.addCleanup(p.stop)
  self.entry=P.montar(self.app,{"suite_root":self.root,"neuro_host_version":"8.10"})
  self.client=TestClient(self.app,base_url="http://localhost")
  self.headers={"origin":"http://localhost","x-neuro-plugin-token":self.entry["token"]}
 def acknowledgement(self):
  p=self.provider.consent_policy();return {"accepted":True,"version":p["version"],"digest":p["digest"]}
 def test_plugin_ausente_nao_importa_motor_e_expoe_termo_atual(self):
  before=set(sys.modules)
  d=self.client.get("/api/plugins/neuro-rt").json()
  self.assertEqual(d["state"],"absent");self.assertFalse(d["mounted"])
  self.assertFalse(d["consent"]["installation_accepted"])
  self.assertEqual(d["consent"]["policy"],self.provider.consent_policy())
  self.assertFalse(any(n.startswith(("torch","SimpleITK","neuro_rt")) for n in set(sys.modules)-before))
  self.assertEqual(self.events,[])
 def test_origem_token_e_aceite_atuais_antes_de_instalar(self):
  route="/api/plugins/neuro-rt/install";body={"confirm":True,"consent":self.acknowledgement()}
  self.assertEqual(self.client.post(route,json=body).status_code,403)
  self.assertEqual(self.client.post(route,json=body,headers=dict(self.headers,origin="https://outside.test")).status_code,403)
  self.assertEqual(self.client.post(route,json={"confirm":True},headers=self.headers).status_code,400)
  stale=dict(body,consent=dict(body["consent"],digest="0"*64))
  self.assertEqual(self.client.post(route,json=stale,headers=self.headers).status_code,400)
  self.assertEqual(self.events,[])
  self.assertEqual(self.client.post(route,json=body,headers=self.headers).status_code,202)
  self.assertEqual(self.events,["install"])
  self.assertTrue(self.provider.consent_status()["installation_accepted"])
  self.assertFalse(self.provider.consent_status()["first_use_accepted"])
 def test_atualizar_tambem_exige_aceite_e_recusa_acao_extra(self):
  route="/api/plugins/neuro-rt/update"
  for action in ("comecar","esperar","interromper"):
   self.assertEqual(self.client.post(route,json={"action":action},headers=self.headers).status_code,400)
  self.assertEqual(self.events,[])
  body={"action":"esperar","consent":self.acknowledgement()}
  self.assertEqual(self.client.post(route,json=body,headers=self.headers).status_code,202)
  self.assertEqual(self.client.post(route,json={"action":"interromper"},headers=self.headers).status_code,202)
  self.assertEqual(self.client.post(route,json={"action":"inventada"},headers=self.headers).status_code,400)
  self.assertEqual(self.events,["esperar","interromper"])

if __name__=="__main__":unittest.main(verbosity=2)
