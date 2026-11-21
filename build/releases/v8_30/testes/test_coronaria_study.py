"""Contrato da coronária no caminho de entrega e na releitura independente do DICOM."""
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import numpy as np
import pydicom
import SimpleITK as sitk

PROGRAMA = Path(__file__).resolve().parents[1] / "programa"
sys.path[:0] = [str(PROGRAMA / "app"), str(PROGRAMA / "tools")]
import engine
import radai_geom
import radai_output
import radai_cache_tasks as cache
from make_test_series import escreve_serie


class CoronariaSTUDY(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.serie = self.base / "TC"
        escreve_serie(str(self.serie), "QA", datetime(2026, 1, 1), 24)
        self.imagem = engine.load_sitk(str(self.serie))
        self.forma = self.imagem.GetSize()[::-1]
        self.grade = radai_geom.Grade.de_sitk(self.imagem)
        self.coracao = np.zeros(self.forma, dtype=bool)
        self.coracao[4:19, 48:78, 50:80] = True
        self.pericardio = np.zeros_like(self.coracao)
        self.pericardio[3:21, 44:82, 46:84] = True
        self.lad = np.zeros_like(self.coracao)
        for z in range(6, 16):
            self.lad[z, 48:50, z+43:z+45] = True
        self.lad[16,48,59] = True
        self.cruas = {"total_v3":{"heart":self.coracao},
                      "trunk_cavities":{"pericardium":self.pericardio}}

    def entrega(self, estruturas, **kwargs):
        saida = radai_output.Saida(engine, self.serie, self.base, "RS.dcm",
            modalidade="CT", grade=self.grade, suavizar_mm=1.5)
        hu = sitk.GetArrayViewFromImage(self.imagem)
        saida._serie_lida = (self.grade, hu)
        saida._img_lida = self.imagem
        protocolo = {"nome":"QA", "id":"qa", "modalidade":"CT", "estruturas":estruturas}
        return saida.full_e_oar(self.cruas, volume_hu=hu, protocolo=protocolo,
            regioes=["torax"], arcos_costais_moose=False, reto_jhu=False, **kwargs)

    def test_coracao_acabado_nome_proprio_e_releitura_da(self):
        fonte = {}
        def inferir(ref, heart, **kw):
            fonte["heart"] = heart.copy()
            self.assertTrue(kw["interpolar_lacunas"])
            return self.lad, {"descricao_dicom":"ROCardS QA, 1 corte interpolado"}
        with ExitStack() as pilha:
            pilha.enter_context(patch("radai_sets.nomes_proprios_em_vigor", return_value={
                "Heart_ai":"Coracao_Local", "DA_ai":"DA_Local"}))
            pilha.enter_context(patch("radai_rocards.segmentar", side_effect=inferir))
            entrega = self.entrega(["heart"])
        self.assertIsNone(entrega["parcial"])
        ds = pydicom.dcmread(entrega["oar"])
        numeros = {str(roi.ROIName):int(roi.ROINumber) for roi in ds.StructureSetROISequence}
        self.assertEqual(set(numeros), {"Coracao_Local","DA_Local"})
        self.assertTrue(any("1 corte interpolado" in getattr(obs, "ROIObservationDescription", "")
                            for obs in ds.RTROIObservationsSequence if int(obs.ReferencedROINumber)==numeros["DA_Local"]))
        cab, _ = engine._cabecalhos_para_rt(str(self.serie))
        rasters = engine._raster_do_dataset(ds, cab, self.grade, self.forma, numeros, None)
        np.testing.assert_array_equal(rasters["DA_Local"].cheia(), self.lad)
        self.assertGreater(fonte["heart"].sum(), self.coracao.sum())

    def test_desligada_por_tarefa_ou_estrutura(self):
        with patch("radai_rocards.segmentar", side_effect=AssertionError) as rede:
            for escolha in ({"coronaria_rocards":False}, {"oar_fora":["rocards_lad"]}, {"oar_fora":["DA_ai"]}):
                with self.subTest(escolha=escolha):
                    entrega = self.entrega(["heart"], **escolha)
                    self.assertEqual(len(entrega["estruturas"]),1)
                    self.assertIsNone(entrega["parcial"])
            rede.assert_not_called()

    def test_auto_do_tensorflow_independe_do_dispositivo_do_pytorch(self):
        with patch("radai_rocards.segmentar", return_value=(self.lad, {})) as rede:
            self.entrega(["heart"], dispositivo_modelos="gpu", dispositivo_rocards="auto")
            self.assertEqual(rede.call_args.kwargs["dispositivo"], "auto")

    def test_tensorflow_sem_gpu_atende_auto_e_respeita_gpu_explicita(self):
        from radai_rocards_worker import Motor
        tf = MagicMock()
        tf.config.list_physical_devices.return_value = []
        with patch("radai_rocards_worker.carregar_runtime", return_value=tf):
            self.assertEqual(Motor(self.base, self.base, "auto", 1).dispositivo, "CPU")
            with self.assertRaisesRegex(RuntimeError, "Use Auto ou CPU"):
                Motor(self.base, self.base, "gpu", 1)
            tf.config.list_physical_devices.return_value = ["GPU:0"]
            self.assertEqual(Motor(self.base, self.base, "gpu", 1).dispositivo, "GPU")

    def test_falha_modelo_preserva_coracao_e_sinaliza(self):
        with patch("radai_rocards.segmentar",side_effect=FileNotFoundError("peso ausente")) as rede:
            entrega = self.entrega(["heart"])
            rede.assert_called_once()
        self.assertEqual(len(entrega["estruturas"]),1)
        self.assertIn("peso ausente",entrega["parcial"]["motivo"])

    def test_so_pos_reutiliza_cache_e_nunca_dispara_rede(self):
        @cache.por_serie
        def processar(pedido, **escolha):
            cache.volume_dos_motores(self.imagem)
            resposta = self.entrega(["heart"], **escolha)
            return resposta, cache.motores_usados()
        # Este teste varia a seleção e a presença física da entrada, sem exigir
        # instalar as sete redes no ambiente de testes do gravador.
        with ExitStack() as pilha:
            pilha.enter_context(patch.object(cache, "pasta", return_value=self.base/"cache"))
            pilha.enter_context(patch.object(cache, "armado", return_value=True))
            pilha.enter_context(patch.object(cache, "_chave_motor", return_value="a"*64))
            rede = pilha.enter_context(patch("radai_rocards.segmentar", return_value=(
                self.lad, {"descricao_dicom":"Teste, 1 corte interpolado"})))
            entrega, anteriores = processar({})
            self.assertEqual(anteriores, {"rocards_lad":"a"*64})
            self.assertIsNone(entrega["parcial"])
            refeito, usados = processar({"so_pos":True, "so_pos_motores":anteriores})
            self.assertEqual(usados, anteriores)
            self.assertEqual(refeito["estruturas"], entrega["estruturas"])
            rede.assert_called_once()
            with self.assertRaises(cache.ReprocessamentoSemMapa):
                processar({"so_pos":True, "so_pos_motores":{}})
            alterado, usados = processar({"so_pos":True, "so_pos_motores":{}}, coronaria_rocards=False)
            self.assertEqual(usados,{})
            self.assertEqual(len(alterado["estruturas"]),1)
            rede.assert_called_once()

if __name__ == "__main__":
    unittest.main(verbosity=2)
