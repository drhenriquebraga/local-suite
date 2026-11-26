"""Contenção por origem com pastas, tickets e leituras de teste locais."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP))
sys.path.insert(1, str(Path(__file__).resolve().parent))


class Pedido:
    def __init__(self, dados=None):
        self.dados = dados

    async def is_disconnected(self):
        return False

    async def json(self):
        return self.dados


class Rede(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(tempfile, "tempdir", tempfile.gettempdir()))
        self.base = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        paths = {"RADAI_TMP": "tmp", "RADAI_CALIB_DIR": "calib", "RADAI_FILA_DIR": "fila",
                 "RADAI_REGISTRO_DIR": "registro", "RADAI_CONFIG": "watcher.config",
                 "LOCALAPPDATA": "local", "APPDATA": "roaming"}
        self.stack.enter_context(patch.dict(os.environ, {k:str(self.base/v) for k,v in paths.items()}))
        (self.base/"watcher.config").write_text("ROOT=\nDRY_RUN=1\nLOG_DIR="+str(self.base/"log"), encoding="utf8")

    def tearDown(self):
        watcher = sys.modules.get("radai_watcher")
        if watcher and watcher._LOG_FH and self.base in Path(watcher._LOG_FH.name).parents:
            watcher._LOG_FH.close()
            watcher._LOG_FH = None

    @unittest.skipUnless(os.name == "nt", "namespace DOS")
    def test_classificacao_sem_stat(self):
        import radai_archive as A
        destinos = {"C:":r"\device\harddiskvolume1", "Z:":r"\device\mup\fake",
                    "S:":r"\??\z:\a", "L:":r"\??\c:\a", "R:":r"\??\r:\a"}
        with patch.object(A,"_destino_dos",side_effect=lambda d:destinos.get(d.upper(), "")), \
                patch.object(os,"stat",side_effect=AssertionError("Sonda inesperada")):
            for p in (r"\\fake\demo", r"\\?\UNC\fake\demo",r"\\?\Z:\d",r"Z:\demo",r"S:\demo",
                      r"R:\ciclo",r"U:\desconectada",r"\\?\GLOBALROOT\Device\mup\demo"):
                self.assertTrue(A._parece_rede(p),p)
            for p in (r"C:\local",r"\\?\C:\local",r"L:\local"):
                self.assertFalse(A._parece_rede(p),p)

    @unittest.skipUnless(os.name == "nt", "unidades Windows")
    def test_temporario_exclui_mapeamento_antes_de_consultar_volume(self):
        import ctypes
        import radai_archive as A
        from unittest.mock import Mock
        k = Mock()
        k.GetLogicalDrives.return_value = (1 << 2) | (1 << 25)
        tipos, volumes = [], []
        def tipo(raiz):
            tipos.append(raiz.value[0])
            return 3
        def volume(raiz, *args):
            volumes.append(raiz.value[0])
            args[-2].value = "NTFS"
            return 1
        k.GetDriveTypeW.side_effect = tipo
        k.GetVolumeInformationW.side_effect = volume
        with patch.object(ctypes.windll, "kernel32", k), patch.object(
                A, "_destino_dos", side_effect=lambda u: r"\device\harddiskvolume1" if u=="C:" else r"\device\mup"):
            self.assertEqual([p[0] for p in A._unidades_locais(lambda p:False)], ["C"])
        self.assertEqual(tipos, ["C"])
        self.assertEqual(volumes, ["C"])

    def test_vagas_locais_com_rede_saturada(self):
        import radai_leitura_ativa as A
        async def testar():
            liberar = threading.Event()
            ocupados, pico = [0], [0]
            trava = threading.Lock()
            def rede(parar):
                with trava:
                    ocupados[0] += 1
                    pico[0] = max(pico[0],ocupados[0])
                try:
                    liberar.wait(3)
                finally:
                    with trava:
                        ocupados[0] -= 1
            tarefas = [asyncio.create_task(A.executar(Pedido(),rede,rede=True)) for _ in range(8)]
            try:
                for _ in range(100):
                    if ocupados[0] == 2:
                        break
                    await asyncio.sleep(.01)
                self.assertEqual(ocupados[0],2)
                self.assertTrue(await asyncio.wait_for(A.executar(Pedido(),lambda parar: True),1))
                self.assertEqual(pico[0],2)
            finally:
                liberar.set()
                for tarefa in tarefas:
                    tarefa.cancel()
                await asyncio.gather(*tarefas,return_exceptions=True)
        asyncio.run(testar())

    def test_detalhes_de_lote_misto_conservam_os_locais(self):
        from fastapi import FastAPI
        import radai_leitura_ativa as A
        import radai_tabela_acervo as T
        import radai_thumbnail as B
        app=FastAPI()
        T.montar(app)
        endpoint=next(r.endpoint for r in app.routes if r.path == T.ROTA_DETALHES)
        r=B.bilhete(r"\\teste\synthetic", "remote")
        l=B.bilhete(str(self.base), "local")
        orig=A.executar
        feitas=[]
        terminou=threading.Event()
        async def curto(*args, rede=False, prazo=None):
            return await orig(*args,rede=rede,prazo=.2 if rede else prazo)
        def detalhes(bs,parar):
            feitas.append(list(bs))
            if bs == [r]:
                try:
                    while not parar():
                        time.sleep(.01)
                finally:
                    terminou.set()
            return [{"ok":x} for x in bs]
        with patch.object(A,"executar",curto),patch.object(T,"detalhes",detalhes):
            dados=asyncio.run(endpoint(Pedido({"bilhetes":[r,l]})))
        self.assertEqual(feitas,[[l],[r]])
        self.assertEqual(dados["itens"],[T._vazio(),{"ok":l}])
        self.assertTrue(terminou.wait(1))

    def test_dois_visores_nao_se_bloqueiam_e_mesma_ficha_reutiliza(self):
        import radai_image_screen as I
        import radai_thumbnail as B
        entrou=threading.Event()
        soltar=threading.Event()
        local=self.base/"local_serie"
        local.mkdir()
        a,b = B.bilhete(str(self.base),"s"), B.bilhete(str(local),"s")
        feitas=[]
        def ler(pasta,parar):
            feitas.append(pasta)
            if pasta == str(self.base):
                entrou.set()
                soltar.wait(3)
            return {"series":[{"chave":"s"}]}
        with patch.object(I.radai_image,"varrer",ler),ThreadPoolExecutor(max_workers=3) as ex:
            f=ex.submit(I._ficha_visual,a)
            try:
                self.assertTrue(entrou.wait(2))
                locais=[ex.submit(I._ficha_visual,b) for _ in range(2)]
                for fut in locais:
                    self.assertEqual(fut.result(timeout=1)[1],str(local))
            finally:
                soltar.set()
            self.assertEqual(f.result(timeout=2)[1],str(self.base))
        self.assertEqual(feitas.count(str(local)),1)
        from radai_leitura_ativa import _TRAVAS_LEITURA
        self.assertFalse(_TRAVAS_LEITURA)

    def test_recon_mesmos_voxels_e_geometria_no_acesso_direto_e_caminho_longo(self):
        from datetime import datetime
        import engine
        import SimpleITK as sitk
        import numpy as np
        import make_test_series
        import radai_recon3d_screen as R
        pasta=str(self.base/"fantoma")
        uid=make_test_series.escreve_serie(pasta,"FANTOMA",datetime(2000,1,1),5)
        original=engine.load_sitk(pasta,uid)
        with patch.object(R._REQUISICAO_VISOR,"parar",lambda:False,create=True):
            for longo in (False,True):
                with patch.object(engine,"_pasta_para_o_gdcm",return_value=None if longo else pasta):
                    img=R._imagem_do_visor(pasta,uid)
                self.assertEqual(img.GetSpacing(),original.GetSpacing())
                self.assertEqual(img.GetOrigin(),original.GetOrigin())
                self.assertEqual(img.GetDirection(),original.GetDirection())
                self.assertTrue(np.array_equal(sitk.GetArrayViewFromImage(img), sitk.GetArrayViewFromImage(original)))

    def test_recon_volume_remoto_nao_segura_local_ou_repete_decodificacao(self):
        import SimpleITK as sitk
        import radai_recon3d_screen as R
        import radai_archive as A
        real = sitk.Image(4, 3, 2, sitk.sitkInt16)
        entrou, soltar = threading.Event(), threading.Event()
        chamadas = []
        def decodificar(pasta, uid):
            chamadas.append(pasta)
            if pasta == "remota":
                entrou.set()
                soltar.wait(4)
            return real
        with patch.object(R,"_imagem_do_visor",decodificar),patch.object(A,"_parece_rede",side_effect=lambda p:p=="remota"),ThreadPoolExecutor(max_workers=3) as ex:
            remota = ex.submit(R._snapshot_do_volume,"remota","uid")
            try:
                self.assertTrue(entrou.wait(2))
                fs = [ex.submit(R._snapshot_do_volume,"local","uid") for _ in range(2)]
                for f in fs:
                    self.assertEqual(f.result(timeout=1)[0].shape,(2,3,4))
                self.assertEqual(chamadas.count("local"),1)
            finally:
                soltar.set()
            self.assertEqual(remota.result(timeout=2)[0].shape,(2,3,4))
        R._soltar_cache_visual()

    def test_recon_pedido_desconectado_interrompe_sem_gravar_volume(self):
        from fastapi import FastAPI, HTTPException
        import radai_recon3d_screen as R
        import radai_thumbnail as B
        app = FastAPI()
        R.montar(app)
        estado = next(r.endpoint for r in app.routes if r.path=="/api/recon3d/estado")
        abriu, saiu = threading.Event(), threading.Event()
        class Desconectar(Pedido):
            async def is_disconnected(self):
                return abriu.is_set()
        def decodificar(pasta,uid):
            abriu.set()
            try:
                for _ in range(200):
                    R._conferir_visor()
                    time.sleep(.01)
                raise AssertionError("decodificação não interrompida")
            finally:
                saiu.set()
        b = B.bilhete(str(self.base), "serie_fantoma")
        with patch.object(R,"_modalidade",return_value="CT"),patch.object(R,"_rotulos_meta",return_value=None),patch.object(R,"arquivos_da_serie",return_value=[]),patch.object(R,"_imagem_do_visor",decodificar):
            with self.assertRaises(HTTPException) as erro:
                asyncio.run(estado(Desconectar(),b))
            self.assertEqual(erro.exception.status_code,499)
            self.assertTrue(saiu.wait(1))
            self.assertNotEqual(R._VOL["chave"],(str(self.base),"serie_fantoma"))
        self.assertIn("signal:r3Leitura.signal", R.JS_MALHA if hasattr(R,"JS_MALHA") else R.pagina("geral"))
        self.assertIn("r3PararLeituras",R.JS_SERIE)

    def test_uma_busca_de_rede_nao_exclui_busca_local(self):
        import radai_varrer as V
        import radai_archive as A
        r=self.base/"simulada"
        r.mkdir()
        (r/"exemplo").touch()
        local=self.base/"rapida"
        local.mkdir()
        (local/"exemplo").touch()
        entrou,soltar=threading.Event(),threading.Event()
        def ler(job,pasta,arqs):
            if job["rede"]:
                entrou.set()
                soltar.wait(3)
            return False
        with patch.dict(V._USOS),patch.dict(V._VARREDURAS),patch.object(A,"_parece_rede",side_effect=lambda p:p==str(r)):
            u=V.registrar("teste_smb",ler,lambda j:[],filtra=False)
            u.paralela=True
            j=V.iniciar(u.nome,str(r))
            try:
                self.assertTrue(entrou.wait(2))
                self.assertTrue(V.iniciar(u.nome,str(r))["erro"])
                res=V.iniciar(u.nome,str(local),em_segundo_plano=False)
                self.assertTrue(res["fim"])
                self.assertFalse(res["erro"])
            finally:
                soltar.set()
                self.assertTrue(V._VARREDURAS[j["v"]]["concluida"].wait(2))

    def test_turno_prioriza_local_e_serializa_a_origem_remota(self):
        import radai_watcher as W
        import radai_archive as A
        with patch.object(A,"_parece_rede",side_effect=lambda p:p=="remota"):
            chamadas=[]
            def trilhar(raizes,progressivo,parar):
                chamadas.append(raizes)
                yield raizes[0],[],[]
            with patch.object(W,"_percorrer_raizes",trilhar):
                it=W._pastas_da_varredura(["remota","local"],True)
                self.assertEqual(next(it)[0],"local")
                self.assertEqual(chamadas,[["local"]])
                self.assertEqual(next(it)[0],"remota")
                outro=W._pastas_da_varredura(["remota"],True,parar=lambda: True)
                self.assertEqual(list(outro),[])
                self.assertEqual(chamadas,[["local"],["remota"]])
                it.close()
                self.assertEqual(len(list(W._pastas_da_varredura(["remota"]))),1)

    @unittest.skipUnless(os.name=="nt","CancelSynchronousIo")
    def test_parar_turno_interrompe_io_ja_bloqueada(self):
        import radai_watcher as W
        entrou,saiu=threading.Event(),threading.Event()
        leitura,escrita=os.pipe()
        def bloqueio(*args):
            entrou.set()
            try:
                os.read(leitura,1)
            finally:
                saiu.set()
            return {},[]
        try:
            with patch.object(W,"raizes_do_turno",return_value=[str(self.base)]),patch.object(W,"scan_root",bloqueio):
                estado={}
                W._varrer_turno_em_paralelo(estado)
                self.assertTrue(entrou.wait(2))
                time.sleep(.05)
                W._parar_varredura_do_turno(estado)
                self.assertTrue(saiu.wait(1),"IO nativa continuou bloqueada")
                for _ in range(50):
                    if W.VARREDURA_DO_TURNO[0] is None:
                        break
                    time.sleep(.01)
                self.assertIsNone(W.VARREDURA_DO_TURNO[0])
                self.assertNotIn("varredura",estado)
        finally:
            os.close(escrita)
            os.close(leitura)


if __name__=="__main__":
    unittest.main(verbosity=2)
