# -*- coding: utf-8 -*-
"""Ciclo real do Vigia sobre séries de bancada, sem motor de inferência."""
from contextlib import ExitStack
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP))
import radai_avisos_windows as native
import radai_vigia_incremental as inc


class Vigia(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.tmp = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.root = self.tmp / "origem"
        self.root.mkdir()
        cfg = self.tmp / "vigia.config"
        cfg.write_text("ROOT="+str(self.root)+"\nDAYS_BACK=0\nNOTIFICAR=0\nDRY_RUN=1\n", "utf-8")
        self.stack.enter_context(patch.dict(os.environ, RADAI_CONFIG=str(cfg), LOCALAPPDATA=str(self.tmp),
                                           RADAI_REGISTRO=str(self.tmp), RADAI_TMP=str(self.tmp)))
        import radai_watcher as w
        self.w = w
        self.mods = ["wlog", "preparar_primeiro_processamento", "abrir_turno_das_assinaturas",
                     "_status_periodico", "_calibracao_do_turno", "salvar_status", "_faxina_do_cache",
                     "_lembrar_de_outras", "_sinalizar_em_uso_agora"]
        for name in self.mods:
            self.stack.enter_context(patch.object(w, name))
        for name, value in dict(ROOT=str(self.root), CACHE_PATH=self.tmp/"index.json", OUT_DIR="",
                                MIN_SLICES=1, DAYS_BACK=0, QUIET_S=0, SCAN_EVERY=60, STATUS_DIR="",
                                MODALITIES={"CT", "MR"}).items():
            self.stack.enter_context(patch.object(w, name, value))
        self.stack.enter_context(patch.dict(w.STATE, ligado=True, overnight=False, paused=False, ambiente_erro=""))
        self.stack.enter_context(patch.object(w, "recurso_esgotado", return_value=False))
        self.stack.enter_context(patch.object(w,"quem_esta_segmentando", return_value=None))
        self.ocupado = True
        self.stack.enter_context(patch.object(w, "_fila_da_estacao", side_effect=self.fila_central))
        self.stack.enter_context(patch.object(w, "process_series", side_effect=AssertionError("não segmentar")))
        self.stack.enter_context(patch.object(w.time, "sleep"))
        self.stack.enter_context(patch.object(inc.Avisos,"esperar"))
        self.estado = {"fila":None,"proxima_varredura":0.0}
        self.stack.callback(w._fechar_avisos, self.estado)
        self.callbacks, self.handles, self.steps, self.reads, self.opens = {}, [], [], [], []
        self.instrumentar = self.stack.enter_context(patch.object(native, "inscrever", side_effect=self.inscrever))
        self.scan = self.stack.enter_context(patch.object(w, "scan_root", wraps=w.scan_root))
        self.clock = time.monotonic()
        self.stack.enter_context(patch.object(inc.time,"monotonic", side_effect=lambda:self.clock))
        self.stack.enter_context(patch.object(w, "is_dicom", side_effect=lambda p:str(p).endswith(".dcm")))
        def read_header(arq, **kwargs):
            self.reads.append(Path(w.sem_prefixo(arq)))
            return SimpleNamespace(**json.loads(Path(arq).read_text("utf-8")))
        self.stack.enter_context(patch.object(w.pydicom, "dcmread", side_effect=read_header))
        scandir = os.scandir
        def listar(path):
            if isinstance(path,(str, Path)):
                self.opens.append(Path(w.sem_prefixo(path)))
            return scandir(path)
        self.stack.enter_context(patch.object(os, "scandir", side_effect=listar))
        w.RESCAN_NOW.clear()
        w.RECARREGAR.clear()
        self.full = w.scan_root
        self.root2 = None

    def fila_central(self, acao, *args, **kw):
        return not self.ocupado if acao == "tentar_a_vez" else kw.get("padrao")

    def inscrever(self, raiz, avisar):
        self.steps.append(("armou", raiz))
        self.callbacks[raiz] = avisar
        handle = SimpleNamespace(fechado=False)
        handle.fechar = lambda: setattr(handle,"fechado",True)
        self.handles.append(handle)
        avisar("pronto", ())
        return handle

    def image(self, rel, uid, grupo=None, nome="001", raiz=None):
        folder = (raiz or self.root)/rel
        folder.mkdir(parents=True,exist_ok=True)
        path = folder/(nome+".dcm")
        path.write_text(json.dumps(dict(SeriesInstanceUID=uid,Modality="CT", PatientID="PHANTOM",
                        SeriesDate="20261126", StudyInstanceUID=grupo or uid+".99")), "utf-8")
        return path

    def done(self, file, uid, date="20261126090000"):
        p = self.w.m_path(str(file.parent), uid, "done", criar=True)
        p.write_text(json.dumps({"dry_run":True,"machine":"OUTRA","date":date}), "utf-8")
        return p

    def emit(self, path, action=1, raiz=None):
        r = raiz or self.root
        self.callbacks[str(r)]("mudou", ((action,str(path.relative_to(r))),))

    def volta(self, periodo=False):
        if periodo:
            self.estado["proxima_varredura"] = 0
        self.w._uma_volta(self.estado)
        return {s["uid"] for s in self.estado["fila"] or ()}

    def test_arvore_1800_quiet_e_intervalo(self):
        for i in range(1800):
            uid = "1.2.826.0.1."+str(i+1)
            f = self.image("pac%03d/s%d"%(i//6, i%6),uid)
            self.done(f, uid)
        self.w.QUIET_S = 5
        self.assertEqual(self.volta(), set())
        self.assertEqual(self.scan.call_count, 1)
        self.assertEqual(len(self.reads), 1800)
        self.assertFalse(hasattr(self.w, "_DA_VARREDURA"))
        self.assertNotIn("series",self.estado)
        self.assertTrue(self.steps)
        self.reads.clear()
        self.opens.clear()
        for _ in range(3):
            self.volta(True)
        self.assertEqual(self.scan.call_count, 1)
        self.assertEqual(self.reads, [])
        self.assertEqual([p for p in self.opens if self.root in p.parents or p == self.root], [])
        u1,u2="1.2.826.4.100","1.2.826.4.101"
        f1=self.image("pac002/nova",u1)
        f2=self.image("pacNovo/alvo",u2)
        for f in (f1,f2):
            os.utime(f,(time.time()-20,)*2)
            self.emit(f)
        self.clock += 2
        self.emit(f1,3)
        self.clock += 3
        self.assertEqual(self.volta(), {u2})
        self.clock += 2
        self.assertEqual(self.volta(), {u1,u2})
        self.assertEqual(set(self.reads), {f1,f2})
        self.assertTrue(set(p for p in self.opens if self.root in p.parents or p==self.root)
                        <= {f1.parent, f2.parent})
        self.assertEqual(self.scan.call_count, 1)
        print("1800 series/300 pacientes: 1800 cabecalhos iniciais, 0 acessos a arvore em 3 intervalos, 2 pastas e 2 cabecalhos apos chegada.")
        self.reads.clear(); self.opens.clear()
        marker = self.done(f1,u1)
        self.emit(marker)
        self.emit(f1.parent/("RS_RadAI_"+u1+".dcm"))
        self.assertFalse(self.estado["avisos"].pendentes)
        self.assertEqual(self.volta(True), {u2})
        self.assertFalse(self.reads)
        self.assertFalse(self.opens)
        marker.unlink()
        self.emit(marker,2)
        self.assertEqual(self.volta(True), {u1,u2})
        self.assertEqual(self.reads, [])

    def test_duas_raizes_mesma_serie_renome_e_remocao(self):
        self.root2 = self.tmp/"outra";self.root2.mkdir()
        self.stack.enter_context(patch.object(self.w,"raizes_do_turno",return_value=[str(self.root),str(self.root2)]))
        u, v = "1.2.826.90", "1.2.826.91"
        a=self.image("uma", u)
        b=self.image("series",u,raiz=self.root2)
        c=self.image("series",v,nome="002",raiz=self.root2)
        self.assertEqual(self.volta(),{u,v})
        self.assertEqual({s["uid"]:s["count"] for s in self.estado["fila"]},{u:2,v:1})
        self.reads.clear()
        novo=self.root2/"movida"
        b.parent.rename(novo)
        self.emit(b.parent,4,self.root2); self.emit(novo,5,self.root2)
        self.assertEqual(self.volta(), {u,v})
        self.assertEqual({s["uid"]:s["count"] for s in self.estado["fila"]},{u:2,v:1})
        self.assertEqual(set(self.reads),{novo/b.name,novo/c.name})
        shutil.rmtree(novo)
        self.emit(novo,2,self.root2)
        self.assertEqual(self.volta(),{u})
        self.assertEqual(self.estado["fila"][0]["count"],1)
        self.assertEqual(self.w.serie_da_varredura(v),("",""))
        self.assertEqual(self.w.sem_prefixo(self.w.serie_da_varredura(u)[0]),str(a.parent))
        self.assertEqual(self.scan.call_count, 1)

    def test_trava_sem_aviso_e_perda_de_aviso(self):
        u = "1.2.826.190"
        f=self.image("serie",u)
        self.assertEqual(self.volta(),{u})
        self.reads.clear()
        self.ocupado=False
        with patch.object(self.w,"claim",return_value=False) as claim:
            self.assertEqual(self.volta(),set())
            self.assertEqual(claim.call_count,1)
        self.ocupado=True
        self.assertEqual(self.volta(True),{u})
        self.assertEqual(self.reads,[])
        self.callbacks[str(self.root)]("overflow", ())
        self.clock+=61
        self.volta()
        self.assertEqual(len(self.handles),2)
        self.assertTrue(self.handles[0].fechado)
        self.assertEqual(self.reads,[f])
        self.volta(True)
        self.assertEqual(self.reads,[f])
        self.callbacks[str(self.root)]("sem_suporte", ())
        self.volta(True)
        self.assertEqual(self.reads,[f], "O recuo visita a árvore e reutiliza os cabeçalhos intactos.")
        self.assertIn(f.parent, self.opens)
        self.w.STATE["paused"]=True
        self.volta()
        self.assertTrue(self.handles[-1].fechado)

    def test_primeira_fila_igual_e_adiamento_sem_descida(self):
        u,v = "1.2.826.200","1.2.826.201"
        f=self.image("p",u)
        self.image("q",v)
        vence = [False]
        with patch.object(self.w, "adiamento_de", side_effect=lambda fl:
                          (None,"") if vence[0] else (time.time()+15,"recurso")), \
                patch.object(self.w, "read_marker", wraps=self.w.read_marker) as reader:
            self.w.m_path(f.parent,u,"fail",criar=True).write_text(json.dumps({"tries":0}),"utf-8")
            classico = self.w.build_queue(*self.w.scan_root())
            self.assertEqual({s["uid"] for s in classico},{v})
            self.assertEqual(self.volta(),{v})
            self.reads.clear()
            chamadas = self.scan.call_count
            vence[0]=True
            self.assertEqual(self.volta(True),{u,v})
            self.assertEqual(self.scan.call_count,chamadas)
            self.assertFalse(self.reads)


    def test_cartao_overnight_publica_primeira_parcial_antes_de_terminar(self):
        import threading
        self.w.STATE["overnight"] = True
        u, v, z = "1.2.826.300","1.2.826.301","1.2.826.302"
        a = self.image("pac1/serie", u)
        b = self.image("pac2/serie", v)
        gate, primeiro = threading.Event(), threading.Event()
        self.addCleanup(gate.set)
        self.ocupado = False
        concluido = []
        def terminar(sr):
            path = {u:a, v:b}[sr["uid"]]
            self.done(path, sr["uid"])
            concluido.append(sr["uid"])
        walker = self.w._pastas_da_varredura
        def com_barreira(*args, **kwargs):
            self.assertIn(str(self.root),self.callbacks)
            for item in walker(*args, **kwargs):
                yield item
                if item[0] is None and not primeiro.is_set():
                    primeiro.set()
                    gate.wait(5)
        with patch.object(self.w,"_pastas_da_varredura",side_effect=com_barreira), \
                patch.object(self.w,"process_series",side_effect=terminar), \
                patch.object(self.w,"_contar_o_desfecho_a_fila"), \
                patch.object(self.w, "claim", return_value=True):
            self.volta()
            self.assertTrue(primeiro.wait(4))
            self.volta()
            self.assertEqual(len(concluido), 1, "A fila deve começar durante a descida progressiva.")
            self.ocupado=True
            novo=self.image("pacNova/serie",z)
            self.emit(novo)
            gate.set()
            for _ in range(150):
                self.volta()
                if self.estado.get("primeira_com_indice"):
                    break
                threading.Event().wait(.025)
            self.assertTrue(self.estado.get("primeira_com_indice"))
            self.volta()
            self.assertIn(z,{s["uid"] for s in self.estado["fila"]})
            self.reads.clear();self.opens.clear()
            for _ in range(3):
                self.volta(True)
            self.assertEqual(self.reads,[])
            self.assertFalse([p for p in self.opens if self.root in p.parents or self.root==p])
            self.assertEqual(self.scan.call_count,1)
            self.assertNotIn("varredura_tentadas",self.estado)
            self.assertNotIn("varredura",self.estado)

    def test_troca_raiz_invalida_antes_de_qualquer_leitura(self):
        u="1.2.826.401"; f=self.image("p",u);self.volta()
        self.assertEqual(self.w.sem_prefixo(self.w.serie_da_varredura(u)[0]),str(f.parent))
        outra=self.tmp/"outroExame";outra.mkdir()
        self.w.ROOT=str(outra)
        self.assertEqual(self.w.serie_da_varredura(u),("",""))
        self.assertEqual(self.volta(),set())
        self.assertTrue(self.handles[0].fechado)
        self.assertEqual(self.w.serie_da_varredura(u),("",""))
        self.w.ROOT=""
        self.assertEqual(self.w.serie_da_varredura(u),("",""))

    def test_inelegiveis_no_disco_permanecem_no_painel_e_podem_ser_liberadas(self):
        u,v="1.2.826.500","1.2.826.501"
        for uid in (u,v):
            f=self.image("p"+uid,uid)
            self.w.m_path(f.parent,uid,"fail",criar=True).write_text(json.dumps(
                {self.w.INELEGIVEL:"recorte insuficiente","cortes":1}),"utf-8")
        self.assertFalse(self.volta())
        self.assertFalse(self.w.NAO_CONTORNAVEIS)
        d=self.w.fora_da_fila(1)
        self.assertEqual(d["n_nao_contornaveis"],2)
        self.assertEqual(len(d["nao_contornaveis"]),1)
        self.assertEqual(self.w.liberar_falhas()["liberadas"],2)
        self.assertEqual(self.volta(),{u,v})

    def test_escrita_no_conteudo_invalida_cache_antes_da_proxima_descida(self):
        a, b = "1.2.826.600","1.2.826.601"
        f = self.image("p",a)
        self.assertEqual(self.volta(),{a})
        stamp = f.parent.stat()
        self.image("p",b)
        os.utime(f.parent, ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
        self.emit(f,3)
        self.assertEqual(self.volta(),{b})
        self.w.RESCAN_NOW.set()
        self.assertEqual(self.volta(),{b})
        self.assertEqual(self.w.serie_da_varredura(a),("",""))

    def test_desinstalador_lista_so_os_indices_e_seus_auxiliares(self):
        import subprocess
        exe = shutil.which("powershell")
        if not exe:
            self.skipTest("PowerShell do instalador")
        pasta = self.tmp/"RadAI_Watcher"
        pasta.mkdir(exist_ok=True)
        alvos = {n+s for n in ("vigia-consulta.sqlite3","vigia-turno.sqlite3")
                 for s in ("","-wal","-shm","-journal")}
        for n in alvos | {"consentimento.json", "outro.sqlite3", "vigia-turno.sqlite3.bak", "index.json"}:
            (pasta/n).write_bytes(b"exemplo")
        # Executa só a função de descoberta do instalador. A desinstalação
        # completa também mexeria nos atalhos da conta do Windows.
        env = dict(os.environ, LOCALAPPDATA=str(self.tmp), TEMP=str(self.tmp))
        env["VIGIA_TESTE_PS"] = str(APP.parent/"installer"/"UNINSTALL.ps1")
        cmd = """
        $ErrorActionPreference = 'Stop'
        $s = [scriptblock]::Create((Get-Content -Raw -LiteralPath $env:VIGIA_TESTE_PS))
        $func = $s.Ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq '_IndicesDoVigia'}, $true)
        . ([scriptblock]::Create($func.Extent.Text))
        @(_IndicesDoVigia) | ForEach-Object { [IO.Path]::GetFileName($_) } | ConvertTo-Json -Compress
        """
        run = subprocess.run([exe,"-NoProfile","-NonInteractive","-Command",cmd],
                             capture_output=True,check=True,env=env,timeout=20,
                             creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        self.assertEqual(set(json.loads(run.stdout)),alvos)

if __name__ == "__main__":
    unittest.main(verbosity=2)
