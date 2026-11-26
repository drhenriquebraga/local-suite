"""E/S da descoberta em árvores simuladas, com índice local e sem inferência."""
import asyncio
from contextlib import ExitStack
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"app"))


class Descoberta(unittest.TestCase):
    def setUp(self):
        self.ctx = ExitStack()
        self.addCleanup(self.ctx.close)
        self.base = Path(self.ctx.enter_context(tempfile.TemporaryDirectory()))
        cfg = self.base/"config.txt"
        cfg.write_text("ROOT=\nDRY_RUN=1\nLOG_DIR="+str(self.base/"log"), encoding="utf8")
        self.ctx.enter_context(patch.dict(os.environ, {"RADAI_CONFIG":str(cfg), "RADAI_TMP":str(self.base/"tmp"),
                               "RADAI_CALIB_DIR":str(self.base/"calibracao"), "RADAI_FILA_DIR":str(self.base/"fila"),
                               "RADAI_REGISTRO_DIR":str(self.base/"registro")}))
        import radai_watcher as W
        import radai_archive as A
        self.w, self.a = W,A
        self.indice = self.base/"index.json"
        self.ctx.enter_context(patch.object(W, "CACHE_PATH", self.indice))
        self.ctx.enter_context(patch.object(W, "DAYS_BACK", 0))
        self.ctx.enter_context(patch.object(W, "MIN_SLICES", 1))

    def tearDown(self):
        if self.w._LOG_FH:
            self.w._LOG_FH.close()
            self.w._LOG_FH=None

    def test_500_marcadores_frios_quentes_edicoes_e_cancelamento(self):
        from pydicom.dataset import Dataset
        W = self.w
        root = self.base/"series"
        for i in range(500):
            serie=root/str(i)
            pasta=serie/"_RadAI"
            pasta.mkdir(parents=True)
            (pasta/"1.done.json").write_text(json.dumps({"date":"20261101000000"}))
            (serie/"CT.dcm").touch()
        def cabecalho(fp,**kw):
            d=Dataset()
            d.SeriesInstanceUID="1.2.3."+Path(fp).parent.name
            d.Modality="CT"
            d.SeriesDate="20260101"
            d.StudyDate="20000101"
            return d
        self.ctx.enter_context(patch.object(W,"is_dicom",side_effect=lambda f:str(f).endswith(".dcm")))
        self.ctx.enter_context(patch.object(W.pydicom,"dcmread",side_effect=cabecalho))
        chamadas=[]
        orig=Path.read_text
        def ler(p,*args,**kwargs):
            if p.name.endswith(".done.json"):
                chamadas.append(Path(W.sem_prefixo(p)))
            return orig(p,*args,**kwargs)
        def scan(parar=None):
            chamadas.clear()
            return W.scan_root([str(root)],parar=parar)
        with patch.object(Path,"read_text",ler):
            series,datas=scan()
            self.assertEqual((len(series),len(datas),len(chamadas)),(500,500,500))
            self.assertTrue(all(s["date"]=="20260101000000" for s in series.values()))
            with patch.object(W,"cache_save",wraps=W.cache_save) as gravar:
                self.assertEqual(scan(),(series,datas))
                self.assertEqual(chamadas,[])
                gravar.assert_not_called()
            with patch.object(self.a,"_parece_rede",return_value=True):
                self.assertEqual(scan(),(series,datas))
                self.assertEqual(chamadas,[])
            # Edição in-place por outra estação, com o mesmo número de bytes e sem mexer na data da pasta.
            pasta=root/"0"/"_RadAI"
            marcador=pasta/"1.done.json"
            ac,mod=pasta.stat().st_atime_ns,pasta.stat().st_mtime_ns
            st=marcador.stat()
            marcador.write_text(json.dumps({"date":"20261225000000"}))
            os.utime(marcador,ns=(st.st_atime_ns,st.st_mtime_ns+2_000_000_000))
            os.utime(pasta,ns=(ac,mod))
            _,datas=scan()
            self.assertEqual(chamadas,[marcador])
            self.assertEqual(datas.count("20261225000000"),1)
            # Publicação, remoção e substituição por escrita atômica entre duas varreduras.
            (root/"1"/"_RadAI"/"1.done.json").unlink()
            pasta=root/"2"/"_RadAI"
            novo=pasta/"2.done.json"
            novo.write_text('{"date":"20261226000000"}')
            tmp=pasta/"edit.tmp"
            tmp.write_text('{"date":"20261227000000","extra":true}')
            os.replace(tmp,pasta/"1.done.json")
            _,datas=scan()
            self.assertEqual(set(chamadas),{novo,pasta/"1.done.json"})
            self.assertEqual(len(datas),500)
            self.assertIn("20261227000000",datas)
            self.assertIn("20261226000000",datas)
            novo.write_text("{")
            _,datas=scan()
            self.assertEqual(len(datas),499)
            self.assertEqual(chamadas,[novo])
            novo.write_text('{"date":"20261228000000"}')
            anterior=self.indice.read_bytes()
            self.assertEqual(scan(lambda: bool(chamadas)),({},[]))
            self.assertEqual(self.indice.read_bytes(),anterior)
            self.assertIn("20261228000000",scan()[1])
            self.assertEqual(chamadas,[novo])
            # Isca: limpar as assinaturas traz de volta as 500 aberturas.
            with patch.object(W,"cache_load",return_value={}):
                self.assertEqual(len(scan()[1]),500)
                self.assertEqual(len(chamadas),500)

    def test_teto_real_da_enumeracao_de_rede_preserva_o_local(self):
        import radai_varrer as V
        from types import SimpleNamespace
        from contextlib import contextmanager
        dominio = "origem"
        atuais=[]
        @contextmanager
        def scandir(pasta):
            def entradas():
                if pasta!=dominio:
                    return
                for i in range(45000):
                    atuais.append(i)
                    yield SimpleNamespace(name=str(i),is_symlink=lambda:False,is_dir=lambda **kw:False)
            yield entradas()
        u=V.Uso("dummy",None,None,pular=lambda nome:False)
        with patch.object(os,"scandir",scandir):
            for rede,esperado in [(True,40000),(False,45000)]:
                with patch.object(self.a,"_parece_rede",return_value=rede):
                    job=V._novo(u.nome,dominio,0,{})
                atuais.clear()
                pasta,arquivos=next(V._pastas_para_ler(job,dominio,u))
                self.assertEqual(len(arquivos),esperado)
                self.assertEqual(len(atuais),esperado)
                self.assertEqual(job["cortada"],"arquivos" if rede else None)
        @contextmanager
        def arvore(pasta):
            def entradas():
                if pasta==dominio:
                    for i in range(3500):
                        yield SimpleNamespace(name=str(i),is_symlink=lambda:False,is_dir=lambda **kw:True)
            yield entradas()
        with patch.object(os,"scandir",arvore):
            for rede,esperado in [(True,2500),(False,3501)]:
                with patch.object(self.a,"_parece_rede",return_value=rede):
                    job=V._novo(u.nome,dominio,0,{})
                self.assertEqual(sum(1 for _ in V._pastas_para_ler(job,dominio,u)),esperado)

    def test_cliente_substitui_apenas_busca_da_mesma_janela(self):
        import shutil, subprocess
        import radai_ui
        node = shutil.which("node")
        if not node:
            self.skipTest("Node necessário para testar o controlador do popup")
        codigo = radai_ui.VARREDURA_JS.split(" var UI_VARRE = ",1)[1].split(" var DIAS_CHAVE =",1)[0]
        fixture = r"""
        const assert = require("node:assert/strict");
        global.window=global; global.document={addEventListener(){}};
        global.addEventListener=()=>{}; global.no = x=>x;
        const inicios=[], paradas=[]; let continuar;
        global.post = async (url,o)=>{
          if(url.endsWith('/iniciar')){
            inicios.push(o);
            if(o.pasta==='uma') await new Promise(resolve=>continuar=resolve);
            return {v:o.pasta,linhas:[],fim:false};
          }
          return {};
        };
        global.fetch=async (_url,opt)=>{paradas.push(JSON.parse(opt.body).v);return {json:async()=>({})}};
        """
        exercicio = r"""
        (async()=>{
          const abrir=(p,canal='esta')=>uiVarrer({chave:canal,pasta:p});
          const prox=()=>new Promise(r=>setImmediate(r));
          const primeira=abrir('uma');
          await prox();
          const segunda=abrir('duas');
          const terceira=abrir('tres');
          const outra=abrir('outra','separada');
          await prox();
          assert.deepEqual(inicios.map(a=>a.pasta),['uma','outra']);
          continuar();
          await prox(); await prox();
          assert.deepEqual(inicios.map(a=>[a.pasta,a.substitui]),[['uma',''],['outra',''],['tres','uma']]);
          assert.ok(paradas.includes('uma'));
          terceira.parar(true); outra.parar(true);
        })().catch(e=>{console.error(e);process.exitCode=1});
        """
        r=subprocess.run([node,"-"],input=fixture+"\nvar UI_VARRE = "+codigo+"\n"+exercicio,
                         encoding="utf8",capture_output=True,timeout=12)
        self.assertEqual(r.returncode,0,r.stderr)

    def test_rede_troca_por_bilhete_exclusivo_apos_a_saida_real(self):
        from fastapi import FastAPI
        import radai_varrer as V
        r1,r2,local=[self.base/n for n in ("rede1","rede2","local")]
        for p in (r1,r2,local):
            p.mkdir()
            (p/"f").touch()
        app=FastAPI()
        V.montar(app)
        endpoint=next(r.endpoint for r in app.routes if r.path=="/api/varrer/iniciar")
        class Requisicao:
            def __init__(self, pasta, anterior=""):
                self.pasta,self.anterior=str(pasta),anterior
            async def json(self):
                return {"pasta":self.pasta,"uso":"com_dono","substitui":self.anterior}
            async def is_disconnected(self):
                return False
        abriu,soltar=threading.Event(),threading.Event()
        eventos=[]
        def ler(job,pasta,arqs):
            if pasta==str(r1):
                eventos.append("inicio1")
                abriu.set()
                try:
                    soltar.wait(3)
                finally:
                    eventos.append("saiu1")
            elif pasta==str(r2):
                eventos.append("inicio2")
            return False
        async def testar():
            inicial=await endpoint(Requisicao(r1))
            anterior=inicial["v"]
            self.assertTrue(abriu.wait(1.5))
            try:
                # Outra janela sem o bilhete, ou com bilhete aleatório, não preempta o trabalho.
                for outra in ("","0"*32):
                    self.assertTrue((await endpoint(Requisicao(r2,outra)))["erro"])
                    self.assertFalse(V.estado(anterior)["parado"])
                self.assertIn("v",await endpoint(Requisicao(local)))
                substituicao=asyncio.create_task(endpoint(Requisicao(r2,anterior)))
                await asyncio.sleep(.12)
                self.assertTrue(V.estado(anterior)["parado"])
                self.assertEqual(eventos,["inicio1"])
                self.assertFalse(substituicao.done())
                soltar.set()
                nova=await asyncio.wait_for(substituicao,2)
                self.assertIn("v",nova)
                self.assertTrue(V._VARREDURAS[nova["v"]]["concluida"].wait(1))
                self.assertEqual(eventos,["inicio1","saiu1","inicio2"])
            finally:
                soltar.set()
            # A substituição em espera perde a janela: a série seguinte não começa.
            soltar.clear()
            abriu.clear()
            eventos.clear()
            anterior=(await endpoint(Requisicao(r1)))["v"]
            self.assertTrue(abriu.wait(1))
            class Fechada(Requisicao):
                async def is_disconnected(self):
                    return True
            try:
                resp=await endpoint(Fechada(r2,anterior))
                self.assertTrue(resp["fim"])
                self.assertNotIn("v",resp)
            finally:
                soltar.set()
            self.assertTrue(V._VARREDURAS[anterior]["concluida"].wait(1))
            self.assertEqual(eventos,["inicio1","saiu1"])
        with patch.dict(V._USOS),patch.dict(V._VARREDURAS),patch.object(
                self.a,"_parece_rede",side_effect=lambda path:str(path) in (str(r1),str(r2))):
            V.registrar("com_dono",ler,lambda j:[],filtra=False)
            asyncio.run(testar())


if __name__ == "__main__":
    unittest.main(verbosity=2)
