"""Perfis de acabamento, saídas do gravador e preferências congeladas na fila."""
import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parent
sys.path[:0] = [str(TOOLS.parent / "app"), str(TOOLS)]
import engine
import make_test_series
import radai_batch as batch
import radai_fast_config as pref
import radai_queue_state as fila
from radai_output import Saida
from test_bolsas_fast import contornos, insumos


class TestFastNiveis(unittest.TestCase):
    def test_casos_novos_legados_e_fila_restaurada(self):
        with patch.object(pref, "nivel_atual", return_value=0):
            self.assertEqual(batch._congelar_fast({"uid": "novo"})["fast_nivel"], 0)
            self.assertEqual(batch._congelar_fast({"uid": "antigo"}, legado=True)["fast_nivel"], 2)
            self.assertEqual(batch.escolha_da_serie({})["fast_nivel"], 2)
            self.assertEqual(batch.escolha_da_serie({"fast_nivel": "inválido"})["fast_nivel"], 2)
            with patch.object(fila, "_CARDS", []):
                serie = {"uid": "1.2.3", "pasta": "serie", "modo": "perso", "acabamento": "fast"}
                fila._acrescentar([serie], "lote")
                with patch.object(pref, "nivel_atual", return_value=4):
                    fila._acrescentar([serie], "lote")
                disco = fila._ao_arquivo(fila._CARDS[0])["escolha"]
                self.assertEqual(disco["fast_nivel"], 0)
                self.assertEqual(disco["acabamento"], "fast")
                self.assertEqual(batch._congelar_fast(disco, legado=True)["fast_nivel"], 0)

    def test_cinco_perfis_releitura_study_e_escopo_das_bolsas(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = {"RADAI_CONFIG": str(root / "config"), "RADAI_CALIB_DIR": str(root / "calib"),
                   "RADAI_REGISTRO_DIR": str(root / "registro")}
            with patch.dict(os.environ, env):
                serie = root / "CT"
                make_test_series.escreve_serie(serie, "FANTOMA", datetime(2026, 1, 1), 24)
                def gerar(modo, acabamento, nivel):
                    destino = root / ("%s-%s-%s" % (modo, acabamento, nivel))
                    destino.mkdir()
                    sd = Saida(engine, serie, destino, "RS.dcm", tasks=("total", "trunk_cavities"), modalidade="CT")
                    opts = {} if nivel is None else {"fast_nivel": nivel}
                    res = sd.full_e_oar(insumos(), modo=modo, acabamento=acabamento, regioes=("abdome", "pelve"),
                                        arcos_costais_moose=False, coronaria_rocards=False, reto_jhu=False, **opts)
                    self.assertIsNone(res["full"])
                    return contornos(res["oar"])
                padrao = gerar("perso", "padrao", None)
                self.assertEqual(padrao, gerar("perso", "padrao", 0))
                manual = [gerar("perso", "fast", i) for i in range(5)]
                self.assertEqual(manual[2], gerar("perso", "fast", None))
                self.assertEqual(manual[4], padrao)
                bolsas = {engine.nome_clinico(k) for k in ("bag_bowel", "bag_bowel_oar")}
                bolsa = engine.nome_clinico("bag_bowel_oar")
                self.assertIn(bolsa, padrao)
                self.assertEqual(len({tuple(map(tuple, m[bolsa])) for m in manual}), 5)
                bolsas_auto = []
                for i in range(5):
                    auto = gerar("auto", "padrao", i)
                    bolsas_auto.append(tuple(auto[bolsa]))
                    self.assertEqual(auto.keys(), padrao.keys())
                    self.assertEqual(manual[i].keys(), padrao.keys())
                    for nome in auto:
                        if nome not in bolsas:
                            self.assertEqual(auto[nome], padrao[nome], (i, nome))
                    if i in (2, 4):
                        self.assertEqual(auto[bolsa], manual[i][bolsa], i)
                self.assertEqual(len(set(bolsas_auto)), 5)


if __name__ == "__main__":
    unittest.main()

