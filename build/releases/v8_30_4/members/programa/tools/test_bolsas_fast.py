"""Regressões da bolsa intestinal e do perfil de acabamento escolhido para o STUDY."""
from datetime import datetime
from pathlib import Path
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pydicom

TOOLS = Path(__file__).resolve().parent
sys.path[:0] = [str(TOOLS.parent / "app"), str(TOOLS)]
import engine
import make_test_series
import radai_geom
from radai_output import Saida


def insumos(n=24, lado=128):
    z, y, x = np.ogrid[:n, :lado, :lado]
    z = (z - n/2) / (n/2)
    y = (y - lado/2) / (lado/2)
    x = (x - lado/2) / (lado/2)
    cavidade = (z/.94)**2 + (y/.75)**2 + (x/.89)**2 < 1
    alcas = (z/.55)**2 + ((y+.12)/.3)**2 + ((x+.12)/.4)**2 < 1
    baco = ((z-.25)/.27)**2 + ((y-.14)/.24)**2 + ((x-.52)/.23)**2 < 1
    return {"total": {"small_intestine": alcas, "spleen": baco},
            "trunk_cavities": {"abdominal_cavity": cavidade}}


def contornos(path):
    ds = pydicom.dcmread(path)
    nomes = {int(r.ROINumber): str(r.ROIName) for r in ds.StructureSetROISequence}
    return {nomes[int(r.ReferencedROINumber)]: [tuple(map(float, c.ContourData)) for c in r.ContourSequence]
            for r in ds.ROIContourSequence}


class TestBolsasFast(unittest.TestCase):
    def test_componente_unica_contagem_e_desempate(self):
        m = np.zeros((8, 9, 10), dtype=bool)
        for pos, n in [(None, 0), ((1, 2, 3), 1), ((5, 6, 7), 2)]:
            if pos:
                m[pos] = True
            with self.subTest(n=n), patch.object(radai_geom, "rotular", wraps=radai_geom.rotular) as rot:
                maior, contagem = radai_geom.maior_componente_e_contagem(m)
            self.assertEqual(contagem, n)
            self.assertEqual(rot.call_count, int(n > 0))
            esperado = np.zeros_like(m)
            esperado[1, 2, 3] = n > 0
            np.testing.assert_array_equal(maior, esperado)

    def test_auto_entrega_bolsa_fast_e_acabamento_padrao_nos_orgaos(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = {"RADAI_CONFIG": str(root / "config.json"), "RADAI_CALIB_DIR": str(root / "calib"),
                   "RADAI_REGISTRO_DIR": str(root / "registro")}
            with patch.dict(os.environ, env):
                serie = root / "CT"
                make_test_series.escreve_serie(serie, "FANTOMA", datetime(2026, 1, 1), 24)
                saidas = {}
                for modo, acabamento in (("perso", "padrao"), ("perso", "fast"), ("auto", "padrao")):
                    nome = modo + acabamento
                    destino = root / nome
                    destino.mkdir()
                    saida = Saida(engine, serie, destino, "RS_BAG.dcm",
                                  tasks=("total", "trunk_cavities"), modalidade="CT")
                    resposta = saida.full_e_oar(insumos(), modo=modo, acabamento=acabamento,
                               regioes=("abdome", "pelve"), arcos_costais_moose=False,
                               coronaria_rocards=False, reto_jhu=False)
                    self.assertIsNone(resposta["full"])
                    saidas[nome] = contornos(resposta["oar"])
                auto, padrao, fast = [saidas[s] for s in ("autopadrao", "persopadrao", "persofast")]
                bag = engine.nome_clinico("bag_bowel_oar")
                baco = engine.nome_clinico("spleen")
                self.assertEqual(auto.keys(), padrao.keys())
                self.assertEqual(auto[bag], fast[bag])
                self.assertEqual(auto[baco], padrao[baco])
                self.assertLess(sum(map(len, auto[bag])), sum(map(len, padrao[bag])))


if __name__ == "__main__":
    unittest.main()
