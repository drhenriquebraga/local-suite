"""Reprocessamento pelo cache na mesma entrada de saída usada na fila."""
from contextlib import ExitStack
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

PROGRAMA = Path(__file__).resolve().parents[1] / "programa"
sys.path[:0] = [str(PROGRAMA/"app"), str(PROGRAMA/"tools")]
import engine
import radai_cache_tasks as cache
import radai_rectum_jhu as jhu
import radai_ribs_predict as moose
import radai_study_modelos as modelos
from test_ribs_posterior import _fixture, _mock_pred


class Complementos(unittest.TestCase):
    def setUp(self):
        self.ref, self.base, pred = _fixture()
        self.reto = np.zeros(self.ref.GetSize()[::-1], bool)
        self.reto[6:10, 4:9, 18:23] = True
        self.base["colon"] = self.reto.copy()
        self.base["colon"][8:13, 8:12, 20:24] = True
        self.saida = SimpleNamespace(engine=engine, modalidade="CT", log=lambda _: None, _img_lida=self.ref)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.stack.enter_context(patch.object(cache, "pasta", return_value=root/"cache"))
        self.stack.enter_context(patch.object(cache, "armado", return_value=True))
        self.stack.enter_context(patch.object(jhu, "_pasta", return_value=root))
        self.stack.enter_context(patch.object(moose, "localizar", return_value=root))
        for rel in (*jhu._arquivos_usados(set()), *moose.ARQUIVOS):
            f = root/rel
            f.parent.mkdir(exist_ok=True, parents=True)
            f.write_bytes(b"fixture")
        self.worker_jhu = self.stack.enter_context(patch.object(jhu, "_segmentar_novo", return_value=(
            self.reto, {"dispositivo_usado": "cpu", "voxels": int(self.reto.sum())})))
        self.worker_moose = self.stack.enter_context(_mock_pred(self.ref, pred))

    def aplicar(self, pedido, usar_arcos=True, usar_reto=True):
        @cache.por_serie
        def rodar(s):
            cache.volume_dos_motores(self.ref)
            cache.conferir_refeito(set())
            masks = dict(self.base)
            dados = modelos.aplicar(self.saida, masks, {}, {"rib_left_7", "rectum", "colon"},
                {"torax", "pelve"}, None, "cpu", None, usar_arcos, usar_reto, base_ts=self.base)
            return masks, dados, cache.motores_usados()
        return rodar(pedido)

    def test_mesmos_voxels_e_vetos_sem_nova_inferencia(self):
        masks, dados, chaves = self.aplicar({})
        self.assertEqual(dados["avisos"], [])
        self.assertEqual(set(chaves), {"jhu_rectum", "moose_ribs"})
        self.assertGreater(dados["detalhes"]["moose_ribs"]["voxels_acrescidos"], 0)
        outro, refeito, usos = self.aplicar({"so_pos":True, "so_pos_motores":chaves})
        self.assertEqual(chaves, usos)
        for k in ("rectum", "colon", "rib_left_7"):
            np.testing.assert_array_equal(np.asarray(masks[k]), np.asarray(outro[k]))
        for k in ("rib_left_7", "ribs_left"):
            np.testing.assert_array_equal(np.asarray(dados["vetos_costais"][k]), np.asarray(refeito["vetos_costais"][k]))
        for nome in ("jhu_rectum", "moose_ribs"):
            self.assertTrue(refeito["detalhes"][nome]["do_cache"])
        self.worker_jhu.assert_called_once()
        self.worker_moose.assert_called_once()

    def test_ausencia_do_mapa_falha_sem_degradar_para_ts(self):
        for arcos, reto, nome in [(True, False, "moose_ribs"), (False, True, "jhu_rectum")]:
            with self.subTest(nome=nome), self.assertRaisesRegex(cache.ReprocessamentoSemMapa, nome):
                self.aplicar({"so_pos":True, "so_pos_motores":{}}, arcos, reto)
        self.worker_jhu.assert_not_called()
        self.worker_moose.assert_not_called()

    def test_desligar_uma_ou_as_duas(self):
        _, _, anteriores = self.aplicar({})
        for arcos, reto, esperados in ((False, True, {"jhu_rectum"}), (True, False, {"moose_ribs"}),
                                       (False, False, set())):
            with self.subTest(arcos=arcos, reto=reto):
                masks, dados, chaves = self.aplicar({"so_pos":True, "so_pos_motores":anteriores}, arcos, reto)
                self.assertEqual(set(chaves), esperados)
                self.assertEqual(dados["avisos"], [])
                if not arcos:
                    np.testing.assert_array_equal(np.asarray(masks["rib_left_7"]), np.asarray(self.base["rib_left_7"]))
                self.assertEqual("rectum" in masks, reto)
        self.worker_jhu.assert_called_once()
        self.worker_moose.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)

