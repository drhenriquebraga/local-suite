import os,sys,tempfile,unittest,subprocess,importlib.util,threading,json,shutil
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).absolute().parent))
import _componentes
_componentes.ligar_caminho()
import _cleanup
_cleanup.adotar_prefixo("radai810_")
BASE=Path(_cleanup.temporaria("radai810_"))
os.environ["RADAI_CALIB_DIR"]=str(BASE/"calib")
os.environ["RADAI_REGISTRO_DIR"]=str(BASE/"registro")
os.environ["RADAI_NAVEGADOR"]="0"
import radai_atualizar as A
import radai_version as V

class Atualizador810(unittest.TestCase):
 def test_decisor_real_sem_console_devolve_codigo_e_pacote(self):
  spec=importlib.util.spec_from_file_location("inicio810",Path(__file__).parent/"test_inicio.py")
  t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)
  for igual in (True,False):
   with self.subTest(igual=igual):
    base=tempfile.mkdtemp(prefix="radai810_decisor_",dir=BASE)
    pacote=t._pacote_leve(base,"8.10");_,inst=t._instalacao_leve(base,"8.9",pacote,t._porta_livre(),igual=igual)
    def rodar(cmd,**kw):return subprocess.run(cmd+["-Python",sys.executable],**kw)
    decisao,saida=A.decidir(pacote,inst,rodar=rodar)
    self.assertEqual(decisao,"codigo" if igual else "pacote",saida)
    self.assertIn("DECISAO="+decisao,saida)
    self.assertIn("ANTIGO",(Path(inst)/"engine.py").read_text())
 def test_consulta_manual_dispara_rede_sem_iniciar_atualizacao(self):
  with patch.object(V,"iniciar_consulta") as consultar,patch.object(A,"_iniciar") as atualizar:
   A.agir("consultar")
   consultar.assert_called_once_with(forcar=True);atualizar.assert_not_called()
 def test_consultas_simultaneas_compartilham_thread(self):
  iniciou=threading.Event();fim=threading.Event()
  def consulta(*a,**k):iniciou.set();fim.wait(5);return {"estado":"atual","versao":"8.10"}
  with patch.object(V,"consultar",side_effect=consulta) as rede:
   try:
    t=V.iniciar_consulta(forcar=True);self.assertTrue(iniciou.wait(3))
    self.assertTrue(V.ultima_consulta().get("consultando"))
    self.assertIs(V.iniciar_consulta(forcar=True),t)
   finally:fim.set();t.join(5)
   self.assertEqual(rede.call_count,1);self.assertFalse(V.ultima_consulta().get("consultando"))
 def test_interface_de_consulta_e_recuperacao_no_navegador(self):
  node=shutil.which("node")
  modulo=Path(os.environ.get("RADAI_PLAYWRIGHT_MODULE",str(Path.home()/".cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright")))
  chrome=Path(os.environ.get("RADAI_CHROME",r"C:\Program Files\Google\Chrome\Application\chrome.exe"))
  if not node or not modulo.is_dir() or not chrome.is_file():self.skipTest("Chrome e Playwright ausentes")
  import radai_ui as UI
  pasta=BASE/"browser";pasta.mkdir(exist_ok=True)
  html='<!doctype html><html><head><meta charset="utf-8"></head><body><button id="btConsultarVersao" onclick="radaiConsultarVersao()">Verificar atualizações</button><span id="subAtu"></span><button id="btAtuAgora" style="display:none">Atualizar agora</button>'+UI.COMPONENTES_JS+A.PARA_A_CASCA+'</body></html>'
  (pasta/"config.html").write_text(html,encoding="utf-8")
  driver=Path(__file__).with_name("atualizar_v810_browser.cjs")
  r=subprocess.run([node,str(driver),str(pasta),str(modulo),str(chrome)],capture_output=True,text=True,encoding="utf-8",timeout=60)
  self.assertEqual(r.returncode,0,r.stdout+r.stderr)
  self.assertIn("PASS refresh",r.stdout)
 def test_falha_de_decisao_abre_instalador_baixado(self):
  old=dict(A._E);ctx=dict(A._CTX)
  try:
   A._E.update(etapa=A.ERRO,motivo_chave=A.M_DECISAO);A._CTX["raiz"]=str(BASE)
   with patch.object(A,"lancar_preparador") as abrir,patch.object(A,"_minimizar_as_janelas"):
    A.agir("instalador");abrir.assert_called_once();self.assertEqual(A.etapa(),A.PREPARADOR)
  finally:A._E.clear();A._E.update(old);A._CTX.clear();A._CTX.update(ctx)

if __name__=="__main__":unittest.main(verbosity=2)
