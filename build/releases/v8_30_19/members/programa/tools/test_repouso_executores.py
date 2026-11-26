"""Regressões de repouso dos executores com fila, plugin real e dados sintéticos."""
from contextlib import ExitStack, nullcontext
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main
from unittest.mock import Mock, patch
import os
import sys
import threading
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
import radai_queue_state as fila
import radai_pulso as pulso
import radai_dedicado as dedicado


def esperar(fn, prazo=4):
    fim = time.monotonic() + prazo
    while time.monotonic() < fim:
        if fn():
            return True
        time.sleep(.01)
    return bool(fn())


class Repouso(TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.base = Path(self.stack.enter_context(TemporaryDirectory()))
        cfg = self.base / "watcher.config"
        cfg.write_text("ROOT=\nDRY_RUN=1\nLOG_DIR=" + str(self.base/"log"), encoding="utf8")
        self.stack.enter_context(patch.dict(os.environ, {"RADAI_CONFIG":str(cfg),
            "LOCALAPPDATA":str(self.base),"RADAI_CALIB_DIR":str(self.base/"calib"),
            "RADAI_FILA_DIR":str(self.base/"fila"),"RADAI_TMP":str(self.base/"tmp")}))
        for k, v in {"_CARDS": [], "_PERSISTIR":{"ligada":False,"gravacoes":0,"erro":""},
                "_RECUPERACAO_ADIADA":False, "_GANCHOS":{}, "_VEZ":{"dono":None,"desde":0,"lote_quer":False},
                "_NEURO_PAUSA":False,"_RASTREIO_CARD":{},"_VIGIA_NA_FILA":{"total":0}}.items():
            self.stack.enter_context(patch.object(fila,k,v))

    def test_lote_prepara_motor_so_para_primeira_serie_real(self):
        import radai_batch as b
        from types import SimpleNamespace
        cont = []
        preparar = lambda: cont.append("preparo")
        eng = SimpleNamespace(diagnostico_de_computacao=lambda d:cont.append("gpu"))
        self.stack.enter_context(patch.dict(sys.modules,engine=eng))
        self.stack.enter_context(patch.object(b,"_CFG",{"preparar_primeiro_processamento":preparar}))
        self.stack.enter_context(patch.object(b,"_JOB",dict(b._JOB,pausar=False,cancelar=False,
                                                resultados=[],feitas=0)))
        self.stack.enter_context(patch.object(b._pre_carga,"durante_serie",return_value=nullcontext()))
        for nome in ("_turno_na_vez","_proxima_da_fila","soltar_extracoes_do_lote","_fila_diz"):
            self.stack.enter_context(patch.object(b,nome,return_value=False))
        self.stack.enter_context(patch("radai_archive.limpar_temporaria",return_value=(0,0)))
        self.stack.enter_context(patch.object(b,"_series_a_rodar",side_effect=lambda series,*a,**k:iter(series)))
        self.stack.enter_context(patch.object(b,"_uma_serie",side_effect=lambda s,*a:cont.append(s["uid"]) or {}))
        claim = self.stack.enter_context(patch.object(b,"_fila_assume",return_value=True))
        def rodar(itens):
            b._rodar_tudo([{"uid":x} for x in itens],False,None,"cpu","unused",5,5,lambda s:None,None,"",2,1)
        with patch.object(fila,"_escrever_json") as writes:
            rodar([])
            b._JOB["pausar"] = True
            rodar(["paused"])
            b._JOB["pausar"] = False
            claim.return_value=False
            rodar(["removed"])
            claim.return_value=True
            self.assertEqual(cont, [])
            self.assertEqual(writes.call_count,0)
            rodar(["first","second"])
        self.assertEqual(cont,["preparo","gpu","first","second"])
        self.assertFalse(b._JOB.get("erro"),b._JOB.get("erro"))

    def test_100_consultas_sem_avisos_e_mudancas_reais_acordam(self):
        with patch.object(pulso,"notificar_mudanca") as sinal:
            for _ in range(100):
                fila.estado_publico(); fila.resumo(); fila.quem_tem_a_vez()
                fila.vigia_na_fila([]); fila.rastreio_status("idle")
            sinal.assert_not_called()
            fila.vigia_na_fila([dict(uid="1.2.3",rotulo="fixture")])
            self.assertEqual(sinal.call_count,1)
            fila.vigia_na_fila([dict(uid="1.2.3",rotulo="fixture")])
            self.assertEqual(sinal.call_count,1)
            fila.pausar_neuro(True); fila.pausar_neuro(True); fila.pausar_neuro(False)
            self.assertEqual(sinal.call_count,3)

    def test_marcador_dorme_sem_inventario_e_renova_quando_ativo(self):
        import radai_watcher as w
        import radai_cleaner as cleaner
        ativo = [False]
        gravados = []
        def gravar(porta,**kw):
            gravados.append(kw)
            return True
        with patch.object(cleaner,"RENOVAR_EM_USO_S",.05), patch.object(cleaner,"gravar_em_uso",side_effect=gravar), \
                patch.object(w,"_ocupacao_do_limpador",side_effect=lambda:(ativo[0],False,None)):
            w._EM_USO_PARAR.clear()
            w._EM_USO_ULTIMA[:]=[None,0]
            t = threading.Thread(target=w._laco_em_uso, daemon=True)
            t.start()
            try:
                self.assertTrue(esperar(lambda:len(gravados)==1))
                for _ in range(4):
                    w._EM_USO_MUDOU.set(); time.sleep(.06)
                self.assertEqual(len(gravados),1)
                self.assertEqual(gravados[0]["procs"],[])
                ativo[0]=True; w._EM_USO_MUDOU.set()
                self.assertTrue(esperar(lambda:len(gravados)>=3))
                self.assertNotIn("procs",gravados[-1])
                ativo[0]=False; w._EM_USO_MUDOU.set()
                self.assertTrue(esperar(lambda:not gravados[-1]["segmentando"]))
                n=len(gravados); time.sleep(.22)
                self.assertEqual(len(gravados),n)
            finally:
                w._EM_USO_PARAR.set(); w._EM_USO_MUDOU.set(); t.join(2)
            self.assertFalse(t.is_alive())
            if w._LOG_FH:
                w._LOG_FH.close(); w._LOG_FH=None

    def test_rastreio_da_seed_pausa_no_meio_reabre_e_encerra_enquanto_pausado(self):
        import radai_plugin_bootstrap as boot
        from radai_lung_plugin import LeiturasDoRastreio
        from types import SimpleNamespace
        pasta = self.stack.enter_context(boot.seed_source("lung-rt"))
        diretorio = str(next(pasta.rglob("screening.py")).parent.parent)
        self.stack.enter_context(patch.object(sys,"path",[diretorio,*sys.path]))
        from lung_rt.screening import Screening
        from lung_rt.store import Store
        db = Store(self.base/"db")
        leituras = []
        terminou = threading.Event()
        def varrer(path,cfg,*,parar):
            try:
                for i in range(180):
                    if parar():
                        break
                    leituras.append(i); time.sleep(.002)
                return []
            finally:
                terminou.set()
        core = LeiturasDoRastreio(SimpleNamespace(varrer=varrer,pasta_valida=lambda path,cfg:path))
        fila.ligar_ganchos(pausa_rastreio=core.pausa)
        scan=Screening(db,core,{},None,lambda:False,lambda:None,core.estado)
        scan.resume()
        self.assertIsNone(scan.thread)
        scan.start([str(self.base)],interval=1)
        try:
            self.assertTrue(esperar(lambda:len(leituras)>6))
            fila.pausar_neuro(True)
            self.assertTrue(terminou.wait(.6))
            parada=len(leituras)
            self.assertLess(parada,180)
            time.sleep(1.25)
            self.assertEqual(len(leituras),parada)
            self.assertTrue(scan.state["active"])
            terminou.clear()
            fila.pausar_neuro(False)
            self.assertTrue(esperar(lambda:len(leituras)>parada+5))
            fila.pausar_neuro(True)
            self.assertTrue(terminou.wait(.6))
            time.sleep(1.1)
            scan.cancel()
            scan.thread.join(1)
            self.assertFalse(scan.thread.is_alive())
            self.assertFalse(scan.options()["enabled"])
        finally:
            scan.cancel(); scan.thread.join(2)

    def test_pausa_nativa_sem_heartbeat_e_excecao_reutiliza_lista_de_pids(self):
        import radai_cleaner as cleaner
        from types import SimpleNamespace
        proc = SimpleNamespace(pid=55001, poll=lambda:None)
        item={"tipo":"servico", "nome":"fixture", "reversao":True}
        c=SimpleNamespace(publico={"ativo":True},proc=proc,estacionado=True,
                          reg={"acoes":[{"estado":"aplicada","item":item}]})
        with patch.object(dedicado,"_CONTROLADOR",c):
            with patch.object(sys,"executable",r"C:\RADIOTERAPIA_AI\LOCAL_SUITE\python\python.exe"):
                self.assertEqual(dedicado.sinalizacao(),(False,None))
            with patch.object(sys,"executable",r"D:\Aplicacoes\LocalSuite\python.exe"):
                self.assertEqual(dedicado.sinalizacao(),(True,55001))
                item["reversao"]=False
                self.assertEqual(dedicado.sinalizacao(),(False,None))
        arquivo = self.base / "em_uso.json"
        cache = [4101,4102]
        with patch.object(cleaner,"processos",side_effect=AssertionError("inventario")), \
                patch.object(cleaner,"_clientes_tcp_painel",side_effect=AssertionError("tcp")):
            self.assertTrue(cleaner.gravar_em_uso(8777,False,pid_app=5101,caminho=str(arquivo),
                dedicado=True,pid_vigia=55001,cache_pids=cache,reusar_pids=True))
        self.assertEqual(set(cache),{4101,4102,5101,55001})

    def test_restauro_transitorio_limitado_sem_fsync_em_loop_e_nova_abertura(self):
        import radai_dedicado_vigia as vigia
        tempo=[0]; esperas=[]
        p=self.base
        reg={"sessao":"a"*32,"terminou":True,
             "acoes":[{"id":"exec", "estado":"aplicada","item":{"tipo":"servico","nome":"FixtureService"}},
                      {"id":"manual","estado":"aplicada","item":{"tipo":"app","nome":"AppFixture","automatico":False}}]}
        dedicado.gravar(p/"dedicado.json",reg)
        platform=Mock()
        platform.restaurar.side_effect=TimeoutError("transição pendente")
        def esperar_intervalo(n):
            tempo[0]+=n; esperas.append(n)
        with patch.object(dedicado,"gravar",wraps=dedicado.gravar) as writes:
            vigia.vigiar(reg["sessao"],p,platform,esperar=esperar_intervalo)
            self.assertEqual(sum(call.args[0].name=="dedicado.json" for call in writes.call_args_list),1)
        self.assertEqual(tempo[0],13)
        self.assertEqual(esperas,[3,10])
        self.assertEqual(platform.restaurar.call_count,3)
        self.assertEqual({c.args[0]["nome"] for c in platform.restaurar.call_args_list},{"FixtureService"})
        self.assertEqual(dedicado.diagnostico_do_restauro(p),["FixtureService"])
        platform.restaurar.side_effect=None
        platform.restaurar.return_value=True
        self.assertTrue(dedicado.recuperar(p,platform))
        self.assertEqual(dedicado.diagnostico_do_restauro(p),[])
        self.assertEqual([a["id"] for a in dedicado.pendentes(dedicado.ler_registro(p/"dedicado.json"))],["manual"])

    def test_negacao_de_permissao_para_depois_da_primeira_tentativa(self):
        import radai_dedicado_vigia as vigia
        p=self.base
        reg={"sessao":"b"*32,"terminou":True,"acoes":[{"id":"repor","estado":"aplicada",
                    "item":{"tipo":"servico","nome":"FixtureDenied"}}]}
        dedicado.gravar(p/"dedicado.json",reg)
        platform=Mock()
        platform.restaurar.side_effect=PermissionError("fixture de política")
        vigia.vigiar(reg["sessao"],p,platform,esperar=Mock(side_effect=AssertionError("não deveria aguardar")))
        self.assertEqual(platform.restaurar.call_count,1)
        vigia.vigiar(reg["sessao"],p,platform,esperar=Mock(side_effect=AssertionError))
        self.assertEqual(platform.restaurar.call_count,1)
        self.assertEqual(dedicado.diagnostico_do_restauro(p),["FixtureDenied"])
        platform.restaurar.side_effect=None
        platform.restaurar.return_value=True
        self.assertTrue(dedicado.recuperar(p,platform))

    def test_entrada_legada_na_pausa_conserva_o_item_e_retoma_a_mesma_serie(self):
        import radai_batch as b
        pedido={"serie":{"uid":"synthetic"},"tasks":["total"],"incluir_vista":False}
        with patch.object(b,"_FILA",[pedido]),patch.object(b,"_JOB",dict(rodando=False,cancelar=False,pausar=True)), \
                patch.object(b,"iniciar_uma",side_effect=[{"ok":False},{"ok":True}]) as start:
            self.assertFalse(b._proxima_da_fila())
            self.assertEqual(start.call_count,0)
            b._JOB["pausar"]=False
            self.assertFalse(b._proxima_da_fila())
            self.assertEqual(b._FILA,[pedido])
            self.assertTrue(b._proxima_da_fila())
            self.assertEqual(b._FILA,[])
            self.assertEqual(start.call_count,2)

    def test_supervisor_reage_ao_fim_e_a_queda_sem_reler_o_journal(self):
        import subprocess
        import json
        app = str(Path(__file__).resolve().parents[1] / "app")
        child = """import sys, os, pathlib
sys.path.insert(0,sys.argv[1]); import radai_dedicado as d, radai_dedicado_vigia as v
p=pathlib.Path(sys.argv[2]); orig=d.recuperar
def recuperar(*a):
    with (p/'tentativas').open('a') as f: f.write('x')
    return orig(*a)
d.recuperar=recuperar
v.vigiar('a'*32,p,None,.03,sys.stdin.buffer)
"""
        owner = """import pathlib, sys, subprocess, os, time
sys.path.insert(0,sys.argv[1]); import radai_dedicado as d
p=pathlib.Path(sys.argv[2]); r=d.Reserva(p); assert r.adquirir()
d.gravar(p/'dedicado.json',dict(sessao='a'*32,acoes=[],terminou=False))
proc=subprocess.Popen([sys.executable,'-B','-c',sys.argv[3],sys.argv[1],str(p)],stdin=subprocess.PIPE)
flag=p/'sair'
while not flag.exists(): time.sleep(.01)
if sys.argv[4]=='queda': os._exit(23)
r.soltar(); proc.stdin.close(); sys.exit(proc.wait(4))
"""
        for modo in ("normal","queda"):
            with self.subTest(modo=modo):
                pasta=self.base/modo
                pasta.mkdir()
                p=subprocess.Popen([sys.executable,"-B","-c",owner,app,str(pasta),child,modo])
                try:
                    self.assertTrue(esperar(lambda:(pasta/"tentativas").exists()))
                    antes=(pasta/"tentativas").read_text()
                    time.sleep(.25)
                    self.assertEqual(antes,"x")
                    self.assertEqual((pasta/"tentativas").read_text(),antes)
                    (pasta/"sair").touch()
                    self.assertEqual(p.wait(5),0 if modo=="normal" else 23)
                    self.assertTrue(esperar(lambda:json.loads((pasta/"dedicado.json").read_text()).get("terminou")))
                    self.assertEqual((pasta/"tentativas").read_text(),"xx")
                finally:
                    (pasta/"sair").touch()
                    p.wait(5)

    def test_dedicado_pausado_para_de_computar_estado_e_preserva_retomada(self):
        fila_inicial={"total":1,"ids":["manual"],"revisao":"x","log_seq":0}
        n=[0]; rodou=threading.Event(); concluido=[False]
        def snapshot():
            n[0]+=1
            return dict(fila_inicial, fase="ready_wait", pausado=True, rodando=False, encerrada=lambda _:concluido[0],
                        com_falha=lambda _:False)
        c=dedicado.Coordenador(self.base,Mock(),snapshot,lambda _:(rodou.set() or True),lambda:None,
                              lambda:True,0, intervalo=.03)
        c.reg={"sessao":"a","acoes":[]}; c.fim.clear()
        c.publico.update(ativo=True,seq=0,sessao="a",log_seq=0)
        t=threading.Thread(target=c._rodar,args=(fila_inicial,),daemon=True); t.start()
        try:
            self.assertTrue(rodou.wait(1)); self.assertTrue(esperar(lambda:c.estacionado))
            antes=n[0]; time.sleep(.18); self.assertEqual(n[0],antes)
            with patch.object(dedicado,"ler_registro",side_effect=FileNotFoundError) as ler:
                concluido[0]=True; pulso.notificar_mudanca("fila")
                self.assertTrue(c.fim.wait(1))
                for _ in range(100): c.estado()
                self.assertEqual(ler.call_count,1)
        finally:
            c.sair_pedido.set(); c.mudou.set(); t.join(1)


if __name__ == "__main__":
    main(verbosity=2)
