"""Regressões de geometria da redução de vértices de Alto e Extra em TC."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
import engine
import radai_geom as geom


def elipse(rx, ry, n=320, centro=(110.1, -75.5)):
    theta = np.arange(n) * (2 * np.pi / n)
    return np.column_stack((centro[0] + rx * np.cos(theta),
                            centro[1] + ry * np.sin(theta), np.full(n, -28.0)))


def erro_cordas(origem, reduzido):
    # Mede cada subarco original contra a corda que o substitui em mm.
    chaves = {tuple(p): i for i, p in enumerate(origem)}
    indices = [chaves[tuple(p)] for p in reduzido]
    assert indices == sorted(indices) and indices[0] == 0
    erro_max = 0.
    for inicio, fim in zip(indices, indices[1:] + [len(origem)]):
        ab = origem[fim % len(origem)] - origem[inicio]
        relativos = origem[inicio:fim] - origem[inicio]
        t = np.clip((relativos @ ab) / (ab @ ab), 0, 1)
        erro_max = max(erro_max, np.linalg.norm(relativos - t[:, None] * ab, axis=1).max())
    return erro_max


class VerticesPorEsforco(unittest.TestCase):
    def test_orcamento_com_limites_em_mm(self):
        anel = elipse(48, 25)
        reduzidos = []
        for fracao, teto in engine._ORCAMENTO_VERTICES_TC.values():
            reduzido = geom.reduzir_anel_por_orcamento(anel, fracao, teto)
            self.assertLessEqual(erro_cordas(anel, reduzido), teto)
            self.assertLessEqual(abs(geom.area_poligono(reduzido) / geom.area_poligono(anel) - 1), .005)
            self.assertEqual(geom.sentido_poligono(anel), geom.sentido_poligono(reduzido))
            self.assertFalse(geom.aneis_em_contato(reduzido))
            reduzidos.append(len(reduzido))
        self.assertLess(reduzidos[0], reduzidos[1])
        self.assertLess(reduzidos[1], len(anel) / 2)

    def test_tolerancia_fisica_no_plano_obliquo(self):
        anel = elipse(20, 12)
        anel[:, 2] = 1.8 * anel[:, 1] + 12.
        fracao, teto = engine._ORCAMENTO_VERTICES_TC["alto"]
        reduzido = geom.reduzir_anel_por_orcamento(anel, fracao, teto)
        self.assertLessEqual(erro_cordas(anel, reduzido), teto)

    def test_aneis_pequenos_estreitos_e_repetidos(self):
        for anel in (elipse(.65, .65), elipse(.3, 20), elipse(9, 7, n=8)):
            np.testing.assert_array_equal(geom.reduzir_anel_por_orcamento(anel, .19, .35), anel)
        olho = elipse(3, 2)
        self.assertLessEqual(erro_cordas(olho, geom.reduzir_anel_por_orcamento(olho, .19, .35)), .10)
        anel = np.vstack((olho, olho[:1]))
        np.testing.assert_array_equal(geom.reduzir_anel_por_orcamento(anel, .19, .35), anel)

    def test_contato_colinearidade_e_cruzamento(self):
        quadrado = np.array([[0., 0], [2, 0], [2, 2], [0, 2]])
        self.assertFalse(geom.aneis_em_contato(quadrado))
        self.assertTrue(geom.aneis_em_contato(quadrado[[0, 2, 1, 3]]))
        self.assertTrue(geom.aneis_em_contato(quadrado, quadrado + [2., .5]))
        self.assertFalse(geom.aneis_em_contato(quadrado, quadrado + [2.01, .5]))

    def test_ilha_e_furo_sobrevivem_a_alteracao_do_contorno_externo(self):
        externo = elipse(20, 20)
        furo = elipse(7, 7)[::-1].copy()
        ilha = elipse(3, 3)
        aneis = (externo, furo, ilha)
        controles = [SimpleNamespace() for _ in aneis]
        reduzidos = [geom.reduzir_anel_por_orcamento(p, .19, .35) for p in aneis]
        engine._escrever_aneis_por_esforco({0: list(zip(controles, aneis, reduzidos))}, None)
        for contorno, esperado in zip(controles, reduzidos):
            np.testing.assert_array_equal(np.reshape(contorno.ContourData, (-1, 3)), esperado)
        # Força como candidata uma corda que cortaria o furo. A fatia conserva a geometria.
        falso = externo[[0, 80, 160]]
        engine._escrever_aneis_por_esforco({0: [(controles[0], externo, falso), (None, furo, furo)]}, None)
        np.testing.assert_array_equal(np.reshape(controles[0].ContourData, (-1, 3)), externo)

    def test_insumos_terminais_seguem_iguais_ao_maximo(self):
        ctx = {"medula": {"chave": "cord", "l2_chave": "l2"},
               "vetos_costais": {"ribs": True}, "atms": {"tmj": 2},
               "intestino_pelvico": {"rectum": True},
               "prioridade_mandibula": {"chave": "mandible", "parotidas": {"parotid": True}},
               "prioridade_esofago": {"chave": "esophagus", "aorta_chave": "aorta"}}
        chaves = ("ribs", "custom", "cord", "l2", engine.CHAVE_CAUDA_EQUINA,
                  "tmj", "rectum", "mandible", "parotid", "esophagus", "aorta", "liver")
        mapa = {k: k + "_ai" for k in chaves}
        numeros = {nome: i+1 for i, nome in enumerate(mapa.values())}
        numeros["interno"] = 90
        referencias = engine._referencias_dos_recortes_terminais(
            ctx, mapa, {"l2": "interno"}, numeros, ("custom",),
            {"custom": {"contem": ("ribs", "vertebra")}})
        self.assertEqual(referencias, set(numeros.values()) - {numeros["liver_ai"]})

        def gravar(esforco, numero):
            pts = elipse(35, 23)
            c = SimpleNamespace(ContourData=pts.ravel().tolist(), NumberOfContourPoints=len(pts))
            ds = SimpleNamespace(ROIContourSequence=[SimpleNamespace(ReferencedROINumber=numero, ContourSequence=[c])])
            engine._suavizar_contornos(ds, dxdy=(1, 1), perfil="padrao", fast_nivel=4,
                                       esforco_vertices=esforco, referencia_terminal=referencias)
            return c.ContourData

        for esforco in ("alto", "extra"):
            np.testing.assert_array_equal(gravar(esforco, numeros["ribs_ai"]), gravar(None, numeros["ribs_ai"]))
            self.assertLess(len(gravar(esforco, numeros["liver_ai"])), len(gravar(None, numeros["liver_ai"])))


if __name__ == "__main__":
    unittest.main()
