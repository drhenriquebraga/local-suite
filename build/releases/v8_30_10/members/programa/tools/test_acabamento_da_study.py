"""Contornos da DA do STUDY em TC sintética, sem executar o ROCardS."""
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pydicom

sys.path[:0] = [str(Path(__file__).resolve().parents[1] / "app"), str(Path(__file__).resolve().parent)]
import engine as E
import radai_geom as G
from radai_rt import PlanoDaImagem, SessaoRT
from test_rtstruct_pixel_spacing import synthetic_rt


class AcabamentoDA(unittest.TestCase):
    def test_perfil_de_entrega_respeita_esforco_e_cortes_finos(self):
        y, x = np.indices((30,42))
        mascara = (x-14)**2 + (y-13)**2 <= 16
        mascara[13,16:34] = True
        nativo, = E._aneis_nativos_plano(mascara)
        for nivel in (0, 1, 4):
            with self.subTest(nivel=nivel):
                novo = E._suavizar_anel_vascular(nativo, mascara.shape, np.asarray, centros_exatos=True,
                                                  nivel=nivel, acabamento_vaso_fino=True)
                esperado = nativo if nivel == 0 else G.suavizar_anel_de_entrega(nativo, leve=(nivel==1))
                np.testing.assert_allclose(novo, esperado, atol=1e-9)

    def test_contorno_de_vaso_fino_no_dicom_preserva_os_ramos(self):
        rt = synthetic_rt([1.2, 0.7])
        nome = "DA_estacao"
        masks = np.zeros((3, 30, 42), dtype=bool)
        y, x = np.indices(masks.shape[1:])
        masks[0] = (x-14)**2 + (y-13)**2 <= 16
        masks[0, 13, 16:34] = True  # ramo distal de um voxel de largura
        masks[1, 14, 12:14] = True  # o diâmetro deste anel é crítico
        masks[2, 9, 29] = True
        for k, fatia in enumerate(rt.series_data):
            fatia.ImagePositionPatient[0] += 0.8 * k
        original = E.MascaraCompacta.de(masks)
        arrays = {"rocards_lad": original}
        E._finalizar_rois_terminais(rt.ds, rt.series_data, G.Grade((2.5, 1.2, .7)),
            arrays, {"rocards_lad": nome}, arrays, {}, None, (.7,1.2),
            {nome:1}, {nome:[220,90,30]}, descricoes={nome:"DA ROCardS, Heart + 10 mm."}, nivel=4)
        with tempfile.TemporaryDirectory() as tmp:
            arquivo = Path(tmp) / "STUDY.dcm"
            E.gravar_dicom_em_fluxo(rt.ds, str(arquivo))
            rt.ds = pydicom.dcmread(arquivo)
        self.assertIn("ROCardS", rt.ds.StructureSetROISequence[0].ROIDescription)
        leitor = SessaoRT(None, None, None, masks.shape, [nome], rt)
        np.testing.assert_array_equal(leitor.mascara(nome), masks)
        cortes = rt.ds.ROIContourSequence[0].ContourSequence
        self.assertEqual(len(cortes), 3)
        for k, (anel, imagem) in enumerate(zip(cortes, rt.series_data)):
            self.assertEqual(anel.ContourImageSequence[0].ReferencedSOPInstanceUID,
                             imagem.SOPInstanceUID)
            novo = PlanoDaImagem(imagem).pixels(np.asarray(anel.ContourData).reshape(-1,3).astype(float))
            nativo, = E._aneis_nativos_plano(masks[k])
            area = G.area_poligono(nativo)
            self.assertLessEqual(abs(G.area_poligono(novo)-area), .005 * area + .001)
            if k == 0:
                # Mesma passada de Taubin usada pelos contornos de carótida.
                np.testing.assert_allclose(novo, G.suavizar_anel_de_entrega(nativo), atol=.001)
            if k == 2:
                np.testing.assert_allclose(novo, nativo, atol=.001)


if __name__ == "__main__":
    unittest.main()
