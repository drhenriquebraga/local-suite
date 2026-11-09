import hashlib,json,os,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).absolute().parent))
import _componentes
_componentes.ligar_caminho()
import _cleanup
_cleanup.adotar_prefixo('radai_neuro_integrity_')
BASE=Path(_cleanup.temporaria('radai_neuro_integrity_'))
os.environ['RADAI_CALIB_DIR']=str(BASE/'calib');os.environ['RADAI_REGISTRO_DIR']=str(BASE/'registro');os.environ['RADAI_NAVEGADOR']='0'
import radai_plugins as P
import radai_lancador as L

class Integrity(unittest.TestCase):
 def fixture(self):
  root=Path(tempfile.mkdtemp(dir=BASE));plugin=root/'Plugins/NEURO RT';code=plugin/'versions/1.0.0';code.mkdir(parents=True)
  module={'schema':'neuro-rt/plugin-manifest/1','id':'neuro-rt','version':'1.0.0','host_contract':P.HOST_CONTRACT,'host_min_version':'8.10','python':'>=3.10','adapter':'adapter.py:mount'}
  (code/'module.json').write_text(json.dumps(module));(code/'adapter.py').write_text('def mount(): pass\n')
  files=[]
  for name in ('module.json','adapter.py'):
   raw=(code/name).read_bytes();files.append({'path':'code/'+name,'size':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
  (code/'release-manifest.json').write_text(json.dumps({'schema':'neuro-rt/release-package/1','plugin_id':'neuro-rt','version':'1.0.0','files':files}))
  (code/'install-receipt.json').write_text('{}')
  (plugin/'installation.json').write_text(json.dumps({'schema':'neuro-rt/installation/1','state':'ready','active_version':'1.0.0'}))
  return root,code
 def discover(self,root):return P.discover_plugin(root,host_info={'contract':P.HOST_CONTRACT,'version':'8.12'})
 def test_inventario_completo_aceita_apenas_metadados_gerados(self):
  root,code=self.fixture();self.assertEqual(self.discover(root)['state'],'ready')
 def test_bytecode_e_outros_extras_sao_recusados_antes_mount(self):
  for name in ('__pycache__/adapter.cpython-310.pyc','adapter.pyc','adapter.pyo','helper.pyd','web/unexpected.js','.hidden-binary'):
   with self.subTest(name=name):
    root,code=self.fixture();file=code/name;file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(b'synthetic extra')
    self.assertEqual(self.discover(root)['state'],'failed')
 def test_reparse_na_ancestral_nao_e_oculto_por_resolve(self):
  root,code=self.fixture();alias=code/'alias';alias.mkdir();lstat=Path.lstat
  def reparse(path,*args,**kwargs):
   value=lstat(path,*args,**kwargs)
   if path==alias:return types.SimpleNamespace(st_mode=value.st_mode,st_file_attributes=0x400)
   return value
  with patch.object(Path,'lstat',reparse):
   with self.assertRaises(ValueError):P._inside(code,'alias/package.py')
 def test_diretorio_cache_vazio_e_recusado(self):
  root,code=self.fixture();(code/'__pycache__').mkdir();self.assertEqual(self.discover(root)['state'],'failed')
 def test_reparse_no_proprio_root_e_recusado(self):
  root,code=self.fixture();lstat=Path.lstat
  def reparse(path,*args,**kwargs):
   value=lstat(path,*args,**kwargs)
   if path==code:return types.SimpleNamespace(st_mode=value.st_mode,st_file_attributes=0x400)
   return value
  with patch.object(Path,'lstat',reparse):
   with self.assertRaises(ValueError):P._inside(code,'adapter.py')
 def test_reparse_quebrado_e_recusado_sem_seguir_exists(self):
  root,code=self.fixture();alias=code/'alias';alias.mkdir();lstat=Path.lstat;exists=Path.exists
  def reparse(path,*args,**kwargs):
   value=lstat(path,*args,**kwargs)
   if path==alias:return types.SimpleNamespace(st_mode=value.st_mode,st_file_attributes=0x400)
   return value
  with patch.object(Path,'lstat',reparse),patch.object(Path,'exists',lambda path:False if path==alias else exists(path)),patch.object(Path,'is_symlink',return_value=False):
   with self.assertRaises(ValueError):P._inside(code,'alias/package.py')
 def test_motor_principal_desabilita_escrita_de_bytecode(self):
  command=L.comando_do_motor(python='python.exe',motor='synthetic-motor.py')
  self.assertIn('-B',command);self.assertEqual(command[-1],'synthetic-motor.py')

if __name__=='__main__':unittest.main(verbosity=2)
