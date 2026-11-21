"""Contratos de geometria e reutilização da TC. Os dublês não carregam redes."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import SimpleITK as sitk

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
import engine
import radai_cads_engine as cads
import radai_cranio_engine as buti
import radai_geom
import radai_moose_engine as moose


class Motores(unittest.TestCase):
    def setUp(self):
        arr = np.zeros((12, 18, 24), np.int16)
        arr[3:6, 8:12, 10:15] = 55
        self.ref = sitk.GetImageFromArray(arr)
        self.ref.SetSpacing((1.3, 1.6, 2.1))
        self.ref.SetOrigin((4., 15., -73.))
        self.ref.SetDirection((0., -1., 0., 1., 0., 0., 0., 0., 1.))

    def test_cads_e_moose_reutilizam_a_mesma_tc(self):
        def saida(entrada, destino, **kw):
            lida = sitk.ReadImage(entrada)
            self.assertTrue(engine._mesma_grade_para_rotulos(lida, self.ref))
            arr = sitk.GetArrayFromImage(lida)
            np.testing.assert_array_equal(arr, sitk.GetArrayFromImage(self.ref))
            seg = lida > 0
            sitk.WriteImage(seg, destino)
            return True, ""
        with patch.object(engine, "load_sitk", side_effect=AssertionError("releitura DICOM")):
            with (patch.object(cads, "disponivel", return_value=(True, "")),
                  patch.object(cads, "rodar", side_effect=saida),
                  patch.object(cads, "rotulos", return_value={1: "liver"}),
                  patch.object(cads, "conferir_rotulos")):
                res = cads.contornar("pasta-inexistente", ref=self.ref)
                self.assertEqual(np.asarray(res["liver"]).sum(), 60)
            with (patch.object(moose, "modelos_disponiveis", return_value={"cardiac": (True, ""), "body_composition": (True, "")}),
                  patch.object(moose, "rodar", side_effect=lambda k, a, b, **kw: saida(a, b)),
                  patch.object(moose, "rotulos", side_effect=lambda k, p: {1: k}),
                  patch.object(moose, "conferir_rotulos")):
                res = moose.contornar("pasta-inexistente", ref=self.ref)
                self.assertEqual(set(res), {"cardiac", "body_composition"})
                self.assertEqual(np.asarray(res["cardiac"]).sum(), 60)

    def test_matriz_igual_mas_origem_errada_rejeitada(self):
        errada = sitk.Image(self.ref)
        errada.SetOrigin((7., 15., -73.))
        with tempfile.TemporaryDirectory() as pasta:
            arq = str(Path(pasta) / "resultado.nii.gz")
            sitk.WriteImage(errada, arq)
            forma = self.ref.GetSize()[::-1]
            with self.assertRaisesRegex(ValueError, "grade física"):
                cads.masks_da_saida(arq, forma, ref=self.ref)
            with self.assertRaisesRegex(ValueError, "grade física"):
                moose.masks_da_saida("cardiac", arq, forma, ref=self.ref)
            def gerar(entrada, destino, **kwargs):
                img = sitk.ReadImage(entrada)
                img.SetOrigin(tuple(x + 3 for x in img.GetOrigin()))
                sitk.WriteImage(img, destino)
                return True, ""
            with (patch.object(buti, "disponivel", return_value=(True, pasta)),
                  patch.object(buti, "encefalo_no_campo", return_value=(True, "", 150.)),
                  patch.object(buti, "rodar", side_effect=gerar),
                  self.assertRaisesRegex(ValueError, "grade")):
                buti.segmentar_serie(self.ref, {"brain":sitk.GetArrayFromImage(self.ref)>0},
                                     radai_geom.Grade.de_sitk(self.ref))


if __name__ == "__main__":
    unittest.main(verbosity=2)
