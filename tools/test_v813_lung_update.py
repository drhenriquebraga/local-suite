import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _componentes
_componentes.ligar_caminho()
import unittest
from unittest.mock import patch
from urllib.error import URLError
import json
import numpy as np
import engine as E
import radai_constructs as C
import radai_geom as G
import radai_sets as S
import radai_version as V
import radai_atualizar as A

class Entrega(unittest.TestCase):
    def test_atrio_inclusive_com_e_sem_pericardio(self):
        g = G.Grade((2, 2, 2))
        heart = np.zeros((30, 30, 30), bool)
        heart[3:25, 4:25, 4:25] = True
        atrio = np.zeros_like(heart)
        atrio[11:16, 8:16, 8:16] = True
        peri = np.zeros_like(heart)
        peri[3:28, 3:26, 3:26] = True
        for p in (False, peri):
            with self.subTest(com_pericardio=p is peri):
                r = C.coracao_ai({"heart": heart, "heart_atrium_left": atrio}, g, pericardio=p)
                self.assertIsNotNone(r)
                self.assertTrue(r.mascara[15].any())
                self.assertFalse(r.mascara[16:].any())

    def test_acabamento_obedece_plano_mesmo_com_mascara_que_cresceu(self):
        g = G.Grade((2, 2, 2))
        m = np.zeros((30, 30, 30), bool)
        m[3:25, 4:25, 4:25] = True
        out, _, _ = E._acabamento_do_coracao("heart", m, {}, g,
                                              spec={"plano_superior_heart": 15})
        self.assertTrue(out[15].any())
        self.assertFalse(out[16:].any())

    def test_vasos_nodulos_no_full_e_individuais_sem_legacy(self):
        for task, label in (("lung_vessels","lung_arteries"),("lung_nodules","lung_nodules")):
            self.assertTrue(S.rotulo_vai_ao_full(task, label))
            self.assertTrue(S.rotulo_vai_ao_plugin(task, label))
        self.assertFalse(S.task_do_full("lung_vessels_LEGACY"))

class Espelho(unittest.TestCase):
    def test_github_bloqueado_e_metadados_corretos_do_espelho(self):
        class R:
            def __init__(self, url):
                self.url = url
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def geturl(self):
                return self.url
            def read(self, n):
                return json.dumps({"schema":"local-suite-update/1","version":"98.12",
                                    "size":6150,"sha256":"a"*64}).encode()
        urls = []
        def rede(req, timeout):
            urls.append(req.full_url)
            if len(urls) == 1:
                raise URLError("bloqueado")
            return R(req.full_url)
        with patch("urllib.request.urlopen", side_effect=rede):
            d = V.consultar(V.URL_VERSOES)
        self.assertIn("api.github.com", urls[0])
        self.assertIn("drhenriquebraga.com.br", urls[1])
        self.assertEqual(d["estado"], "nova")
        self.assertEqual(d["fonte"], "espelho")
        self.assertEqual(d["instalador"]["sha256"], "a"*64)
        self.assertTrue(d["instalador"]["url"].endswith("/v98.12/"+V.nome_do_instalador_latest()))

    def test_arranque_so_espelho_quando_fila_livre(self):
        with patch.object(A,"e_instalacao",return_value=True), patch.object(A,"_status",return_value={}), patch.object(A,"o_que_segura",return_value=None), patch.object(A,"_registrar_tentativa_no_arranque",return_value=True), patch.object(A,"_iniciar") as ini:
            A.iniciar_no_arranque({"estado":"nova","fonte":"github","versao":"98.12"}, 8888)
            ini.assert_not_called()
            A.iniciar_no_arranque({"estado":"nova","fonte":"espelho","versao":"98.12"}, 8888)
            ini.assert_called_once_with(False, apenas_codigo=True)

import SimpleITK as sitk
import radai_lung as L

class TestLung(unittest.TestCase):
    def test_fases_com_mesma_grade_numerica_mas_origem_diferente(self):
        alvo = sitk.Image([10,10,10],sitk.sitkInt16)
        fonte = sitk.Image(alvo)
        fonte.SetOrigin((2.0,0.0,0.0))
        a = np.zeros((10,10,10),dtype=bool)
        a[3,4,2] = True
        b = L.transportar(a, fonte, alvo)
        self.assertTrue(b[3,4,4])
        self.assertFalse(b[3,4,2])
        a[3,4,9] = True
        with self.assertRaises(ValueError):
            L.transportar(a,fonte,alvo)
    def test_itv_uniao_e_contornos_por_fase(self):
        a=np.zeros((4,4,4),bool); b=a.copy()
        a[1,1,1]=1; b[1,1,2]=1
        masks=L.unir_fases([a,b,None])
        self.assertEqual(set(masks),{"GTV_F01_N01","GTV_F02_N01","ITV"})
        self.assertTrue(np.array_equal(a|b,masks["ITV"]))
    def test_motor_so_chama_nodulos_e_exclui_classe_auxiliar(self):
        ref=sitk.Image([10,10,10],sitk.sitkInt16)
        a=np.zeros((10,10,10),bool)
        a[2,2,2]=1
        with patch("engine._job_new",return_value="fantoma"), patch("engine._job_del"), patch("engine._resolve_device",return_value="cpu"), patch("engine.run_ts_task",return_value={"lung":np.ones_like(a),"lung_nodules":a}) as run:
            mask=L.inferir(ref,{"device":"cpu","timeout_task_s":37})
        self.assertTrue(np.array_equal(a,mask))
        self.assertEqual(run.call_count,1)
        self.assertEqual(run.call_args.args[1:4],("lung_nodules","cpu","fantoma"))

    def test_rtstruct_referencia_fase_correta_na_grade_real(self):
        import os, tempfile, pathlib
        from datetime import datetime
        import pydicom
        import make_test_series
        with tempfile.TemporaryDirectory(prefix="radai_lung_test_") as pasta:
            raiz=pathlib.Path(pasta)
            os.environ.update(LOCALAPPDATA=pasta,RADAI_TMP=pasta)
            for nome in ("a","b"):
                make_test_series.escreve_serie(str(raiz/nome),"FANTOMA-4D",datetime(2026,11,6),12)
            primeiro=pydicom.dcmread(str(raiz/"a"/"CT_0001.dcm"),stop_before_pixels=True)
            for f in (raiz/"b").glob("*.dcm"):
                ds=pydicom.dcmread(str(f))
                ds.StudyInstanceUID=primeiro.StudyInstanceUID
                ds.FrameOfReferenceUID=primeiro.FrameOfReferenceUID
                ds.ImagePositionPatient[0]=float(ds.ImagePositionPatient[0])+2.0
                ds.save_as(str(f),enforce_file_format=True)
            cfg={"min_cortes":5,"maquina":"FANTOMA","device":"cpu","marcadores":{
                "claim": lambda *_: True, "unclaim":lambda *_:None,
                "renovar":lambda *_:True,"lock_e_meu":lambda *_:True}}
            series=L.varrer(pasta,cfg)
            self.assertEqual(len(series),2)
            alvo=next(s for s in series if s["pasta"]==str(raiz/"a"))
            origem=next(s for s in series if s["pasta"]==str(raiz/"b"))
            h=L.validar_grupo(series,alvo["uid"],alvo["uid"])
            mask=np.zeros((12,128,128),bool);mask[4:7,60:65,60:65]=True
            with L._serie(alvo,h[alvo["uid"]]) as (_,ref,_):
                with patch.object(L,"inferir",return_value=mask):
                    alinhado=L.rodar_nodulos(origem,cfg,h[origem["uid"]],ref)
                self.assertFalse(alinhado[4,60,60]); self.assertTrue(alinhado[4,60,65])
            nodule_file=next((raiz/"b").glob("RS_RadAI_NOD_LUNG_*.dcm"))
            nod=pydicom.dcmread(str(nodule_file),stop_before_pixels=True)
            self.assertEqual(nod.ApprovalStatus,"UNAPPROVED")
            self.assertEqual(len(nod.StructureSetROISequence),1)
            L.exportar(alvo,h[alvo["uid"]],L.unir_fases([mask,alinhado]),cfg)
            out=next((raiz/"a").glob("RS_RadAI_ITV4D_*.dcm"))
            d=pydicom.dcmread(str(out),stop_before_pixels=True)
            self.assertEqual(d.ApprovalStatus,"UNAPPROVED")
            self.assertEqual(len(d.StructureSetROISequence),3)
            serie=d.ReferencedFrameOfReferenceSequence[0].RTReferencedStudySequence[0].RTReferencedSeriesSequence[0]
            self.assertEqual(serie.SeriesInstanceUID,alvo["uid"])
            self.assertTrue(all("_ai" in str(x.ROIName) for x in d.StructureSetROISequence))


if __name__ == '__main__':
    unittest.main(verbosity=2)
