import hashlib,json,os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).absolute().parent))
import _componentes
_componentes.ligar_caminho()
import _cleanup
_cleanup.adotar_prefixo('radai_plugin_setup_')
BASE=Path(_cleanup.temporaria('radai_plugin_setup_'))
os.environ['RADAI_CALIB_DIR']=str(BASE/'calib')
os.environ['RADAI_REGISTRO_DIR']=str(BASE/'registro')
os.environ['RADAI_NAVEGADOR']='0'
try:
 import radai_plugin_setup as P
except ImportError:
 P=None

class ExternalInstall(unittest.TestCase):
 def setUp(self):
  self.assertIsNotNone(P,'O instalador externo confiável ainda não existe')
  self.root=Path(tempfile.mkdtemp(dir=BASE));self.closed=[];self.protected=[];self.scheduled=[];self.commands=[]
  self.process=type('Process',(),{'pid':43210,'poll':lambda s:None,'terminate':lambda s:None})()
 def spawn(self,command,**options):
  self.commands.append((command,options))
  self.plan=Path(command[command.index('-PlanPath')+1]);self.sha=command[command.index('-PlanSha256')+1]
  d=json.loads(self.plan.read_text(encoding='utf-8'))
  (self.plan.parent/'ready.json').write_text(json.dumps({'ready':True,'nonce':d['nonce'],'supervisor_pid':43210,'worker_pid':43211}),encoding='utf-8')
  return self.process
 def manager(self,spawn=None):
  return P.ExternalInstaller(self.root,8777,lambda:self.closed.append(True),popen=spawn or self.spawn,
      protect=self.protected.append,schedule=self.scheduled.append,wait_s=.02)
 def launch(self,manager=None):
  return (manager or self.manager()).launch({'schema':'neuro-rt/external-plan/1','source':'online','version':'1.1.0'})
 def test_ack_antecede_fechamento_e_protege_supervisor_e_worker(self):
  result=self.launch()
  self.assertTrue(result['ok']);self.assertTrue(result['scheduled']);self.assertEqual(self.closed,[])
  self.assertEqual(self.protected,[43210,43211]);self.assertEqual(len(self.scheduled),1)
  self.scheduled[0]();self.assertEqual(self.closed,[True])
  command,options=self.commands[0];self.assertNotIn('shell',options)
  self.assertIn('-File',command);self.assertIn('-PlanSha256',command)
  self.assertEqual(hashlib.sha256(self.plan.read_bytes()).hexdigest(),self.sha)
 def test_sem_ack_mantem_app_e_cancela_worker(self):
  def spawn(command,**options):
   process=self.spawn(command,**options);(self.plan.parent/'ready.json').unlink();return process
  with self.assertRaises(ValueError):self.launch(self.manager(spawn))
  self.assertEqual(self.scheduled,[]);self.assertEqual(self.closed,[])
  self.assertTrue((self.plan.parent/'cancel.json').is_file())
 def test_nonce_ou_pid_divergente_nao_encerra(self):
  for field,value in [('nonce','wrong'),('supervisor_pid',9),('worker_pid',0)]:
   with self.subTest(field=field):
    def spawn(command,**options):
     process=self.spawn(command,**options);p=self.plan.parent/'ready.json';d=json.loads(p.read_text());d[field]=value;p.write_text(json.dumps(d));return process
    with self.assertRaises(ValueError):self.launch(self.manager(spawn))
  self.assertEqual(self.scheduled,[])
 def test_repetir_pedido_usa_mesma_transacao(self):
  manager=self.manager();a=self.launch(manager);b=self.launch(manager)
  self.assertEqual(a,b);self.assertEqual(len(self.commands),1)
 def test_falha_de_abertura_nao_fecha(self):
  def spawn(*a,**k):raise OSError('synthetic')
  with self.assertRaises(ValueError):self.launch(self.manager(spawn))
  self.assertEqual(self.closed,[]);self.assertEqual(self.scheduled,[])
 def test_worker_so_instala_apos_saida_e_reabre_com_loopback(self):
  self.launch();events=[]
  def wait(pid,cancelled):events.append(('wait',pid));return True
  def run(plan,progress):events.append(('install',plan['source']));progress({'stage':'verifying'});return {'state':'ready','active_version':'1.1.0'}
  def reopen(root,port,pid):events.append(('open',port));return True
  result=P.run_worker(self.plan,self.sha,43210,runner=run,wait_old=wait,reopen=reopen)
  self.assertEqual(result,0);self.assertEqual([x[0] for x in events],['wait','install','open'])
  receipt=json.loads((self.plan.parent/'result.json').read_text());self.assertTrue(receipt['ok']);self.assertTrue(receipt['reopened'])
 def test_worker_recusa_hash_adulterado_antes_de_qualquer_acao(self):
  self.launch();events=[]
  with self.assertRaises(ValueError):P.run_worker(self.plan,'0'*64,43210,runner=lambda *a:events.append(a))
  self.assertEqual(events,[])
 def test_pid_antigo_vivo_nao_instala_nem_reabre(self):
  self.launch();events=[]
  result=P.run_worker(self.plan,self.sha,43210,runner=lambda *a:events.append('install'),wait_old=lambda *a:False,reopen=lambda *a:events.append('open'))
  self.assertEqual(result,1);self.assertEqual(events,[])
 def test_falha_instalacao_registra_erro_seguro_e_reabre_base(self):
  self.launch();events=[]
  def fail(*a):raise OSError('synthetic secret path')
  result=P.run_worker(self.plan,self.sha,43210,runner=fail,wait_old=lambda *a:True,reopen=lambda *a:events.append('open') or True)
  self.assertEqual(result,1);self.assertEqual(events,['open'])
  text=(self.plan.parent/'result.json').read_text();self.assertNotIn('secret',text);self.assertIn('INSTALL_FAILED',text)
 def test_cancelado_nao_instala(self):
  self.launch();d=json.loads(self.plan.read_text());(self.plan.parent/'cancel.json').write_text(json.dumps({'nonce':d['nonce']}))
  events=[];result=P.run_worker(self.plan,self.sha,43210,runner=lambda *a:events.append('install'),wait_old=lambda *a:True,reopen=lambda *a:True)
  self.assertEqual(result,1);self.assertEqual(events,[])

 def test_interpreta_os_mesmos_bytes_cujo_hash_foi_conferido(self):
  self.launch();seen=[];read_bytes=Path.read_bytes
  def change_after_read(path):
   raw=read_bytes(path)
   if path==self.plan:
    changed=json.loads(raw);changed['payload']['version']='9.9.9';path.write_text(json.dumps(changed))
   return raw
  def run(plan,progress):seen.append(plan['version']);return {'state':'ready','active_version':plan['version']}
  with patch.object(Path,'read_bytes',change_after_read):
   code=P.run_worker(self.plan,self.sha,43210,runner=run,wait_old=lambda *a:True,reopen=lambda *a:True)
  self.assertEqual(code,0);self.assertEqual(seen,['1.1.0'])
 def test_log_indisponivel_apos_ack_nao_impede_preparo_e_reabertura(self):
  self.launch();events=[];open_path=Path.open;writes=[]
  def unavailable(path,*args,**kwargs):
   if path.name=='progress.log':
    writes.append(1)
    if len(writes)>1:raise OSError('synthetic log unavailable')
   return open_path(path,*args,**kwargs)
  def run(*args):events.append('install');return {'state':'ready','active_version':'1.1.0'}
  try:
   with patch.object(Path,'open',unavailable):
    code=P.run_worker(self.plan,self.sha,43210,runner=run,wait_old=lambda *a:True,reopen=lambda *a:events.append('open') or True)
  except OSError:
   code=-1
  self.assertEqual(code,0);self.assertEqual(events,['install','open'])

 def settings_root(self):
  app=self.root/'app';app.mkdir();worker=app/'radai_plugin_setup.py';worker.write_text('')
  (app/'radai_lancador.py').write_text('');(self.root/'entrega.txt').write_text('PROJETO=LOCAL_SUITE\nVERSAO=8.12\n')
  return worker
 def test_start_here_abre_config_sem_reiniciar_host_vivo(self):
  self.assertTrue(hasattr(P,'open_settings'),'Ainda falta o comando de abrir configurações')
  worker=self.settings_root();events=[]
  with patch.object(P,'__file__',str(worker)):
   result=P.open_settings(self.root,8778,alive=lambda port:True,open_browser=lambda url:events.append(('open',url)) or True,launch=lambda cmd:events.append(('launch',cmd)) or True)
  self.assertTrue(result);self.assertEqual(events,[('open','http://127.0.0.1:8778/config#ps_neuro')])
 def test_start_here_lanca_host_ausente_na_porta_da_base(self):
  self.assertTrue(hasattr(P,'open_settings'),'Ainda falta o comando de abrir configurações')
  worker=self.settings_root();(worker.parent/'radai_watcher.config').write_text('ROOT=private-unrelated\nPORT=8781\n')
  events=[]
  with patch.object(P,'__file__',str(worker)),patch.dict(os.environ,{'RADAI_CONFIG':''}):
   result=P.open_settings(self.root,alive=lambda port:False,open_browser=lambda url:False,launch=lambda cmd:events.append(cmd) or True)
  self.assertTrue(result);self.assertEqual(len(events),1)
  self.assertIn('http://127.0.0.1:8781/config#ps_neuro',events[0]);self.assertIn('--abrir-janela',events[0])

 def test_progresso_dos_recursos_exibe_bytes_no_console(self):
  self.launch();messages=[]
  def run(plan,progress):
   progress({'stage':'resources','downloaded_bytes':1048576,'total_bytes':2097152})
   return {'state':'ready','active_version':'1.1.0'}
  with patch.object(P,'_message',side_effect=lambda work,text:messages.append(text)):
   code=P.run_worker(self.plan,self.sha,43210,runner=run,wait_old=lambda *a:True,reopen=lambda *a:True)
  self.assertEqual(code,0)
  self.assertTrue(any('recursos' in text and '1.0/2.0 MB' in text for text in messages),messages)

 def test_progresso_offline_identifica_componente_e_etapa_reais(self):
  self.launch();messages=[]
  def run(plan,progress):
   progress({'stage':'resources','resource_stage':'extracting','component':'MRI_Meningioma'})
   return {'state':'ready','active_version':'1.1.0'}
  with patch.object(P,'_message',side_effect=lambda work,text:messages.append(text)):
   code=P.run_worker(self.plan,self.sha,43210,runner=run,wait_old=lambda *a:True,reopen=lambda *a:True)
  self.assertEqual(code,0)
  self.assertTrue(any('Extraindo' in text and 'MRI_Meningioma' in text for text in messages),messages)

if __name__=='__main__':unittest.main(verbosity=2)
