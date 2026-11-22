"""Regressões do índice e da escrita de STUDY/FULL em séries DICOM sintéticas."""
import json
import os
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np
import pydicom

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
import engine
import radai_archive
from radai_output import Saida
from make_test_series import escreve_serie


class TestEntrega(unittest.TestCase):
    def setUp(self):
        contexto = ExitStack()
        self.addCleanup(contexto.close)
        self.pasta = Path(contexto.enter_context(tempfile.TemporaryDirectory()))
        contexto.enter_context(mock.patch.dict(os.environ, {
            "RADAI_CONFIG": str(self.pasta / "config.json"),
            "RADAI_CALIB_DIR": str(self.pasta / "calib"),
            "RADAI_REGISTRO_DIR": str(self.pasta / "registro"),
        }))
        self.serie = self.pasta / "CT"
        self.uid = escreve_serie(self.serie, "FANTOMA", datetime(2026, 1, 1), 12)
        z, y, x = np.ogrid[:12, :128, :128]
        self.mask = ((z - 5)**2 / 20 + (y - 60)**2 / 196 + (x - 69)**2 / 324 < 1)

    def entregar(self, destino, full=False, ajustar=None):
        destino.mkdir()
        logs = []
        saida = Saida(engine, self.serie, destino, "RS_RadAI_FANTOMA.dcm",
                      tasks=("total",), log=logs.append, modalidade="CT")
        with ExitStack() as spies:
            aneis = spies.enter_context(mock.patch.object(
                engine, "_aneis_da_mascara", wraps=engine._aneis_da_mascara))
            escrever = spies.enter_context(mock.patch.object(
                engine, "gravar_dicom_em_fluxo", wraps=engine.gravar_dicom_em_fluxo))
            validar = spies.enter_context(mock.patch.object(
                saida, "_publicar_entrega", wraps=saida._publicar_entrega))
            spies.enter_context(mock.patch.object(
                engine, "_salvar_sem_escrever_no_console", side_effect=AssertionError("RT intermediário")))
            if ajustar:
                spies.enter_context(mock.patch.object(engine, "_normalizar_coordenadas_ds", ajustar))
            resposta = saida.full_e_oar({"total": {"spleen": self.mask}}, modo="perso" if full else "auto",
                    anatomia_geral_full=full, arcos_costais_moose=False, reto_jhu=False, coronaria_rocards=False)
        self.assertEqual((aneis.call_count, escrever.call_count, validar.call_count), (1, 1, 1))
        self.assertIsNone(resposta["oar" if full else "full"])
        rt = pydicom.dcmread(resposta["full" if full else "oar"])
        refs = rt.ReferencedFrameOfReferenceSequence[0].RTReferencedStudySequence[0].RTReferencedSeriesSequence[0]
        self.assertEqual(refs.SeriesInstanceUID, self.uid)
        fontes = {pydicom.dcmread(f, specific_tags=["SOPInstanceUID"]).SOPInstanceUID for f in self.serie.glob("*.dcm")}
        coordenadas = []
        for roi in rt.ROIContourSequence:
            for corte in roi.ContourSequence:
                sop = corte.ContourImageSequence[0].ReferencedSOPInstanceUID
                self.assertIn(sop, fontes)
                raw = corte.get_item(engine.TAG_DOS_PONTOS).value
                self.assertTrue(all(len(v) <= 16 for v in raw.rstrip(b" ").split(b"\\")))
                pontos = tuple(map(float, corte.ContourData))
                self.assertEqual(len(pontos), 3 * corte.NumberOfContourPoints)
                coordenadas.append((str(sop), pontos))
        self.assertTrue(coordenadas)
        return coordenadas, logs

    def test_study_e_full_gravam_uma_vez_e_a_correcao_ds_preserva_geometria(self):
        normalizar = engine._normalizar_coordenadas_ds

        def inserir_ds_longo(ds):
            corte = ds.ROIContourSequence[0].ContourSequence[0]
            pontos = list(map(str, corte.ContourData))
            pontos[0] = format(float(pontos[0]), ".23f")
            engine._gravar_pontos(corte, pontos)
            return normalizar(ds)

        for full in (False, True):
            with self.subTest(full=full):
                base, sem_aviso = self.entregar(self.pasta / ("normal-%d" % full), full)
                corrigido, com_aviso = self.entregar(self.pasta / ("corrigido-%d" % full), full, inserir_ds_longo)
                self.assertEqual(base, corrigido)
                self.assertFalse(any("DS acima" in s for s in sem_aviso))
                self.assertEqual(sum("1 valor(es) DS acima" in s for s in com_aviso), 1)

    def test_arquivo_invalido_nao_e_publicado(self):
        def corromper(ds, caminho, **kwargs):
            Path(caminho).write_bytes(b"fantoma truncado")

        with mock.patch.object(engine, "gravar_dicom_em_fluxo", corromper):
            for full in (False, True):
                destino = self.pasta / ("falha-%d" % full)
                with self.subTest(full=full), self.assertRaises(pydicom.errors.InvalidDicomError):
                    self.entregar(destino, full)
                self.assertEqual(list(destino.iterdir()), [])

    def test_mesma_mascara_em_serie_deslocada_usa_plano_e_referencias_dela(self):
        antiga, _ = self.entregar(self.pasta / "primeira")
        self.serie = self.pasta / "outra-CT"
        self.uid = escreve_serie(self.serie, "FANTOMA", datetime(2026, 1, 1), 12)
        for caminho in self.serie.glob("*.dcm"):
            corte = pydicom.dcmread(caminho)
            corte.ImagePositionPatient[0] += 23.0
            corte.save_as(caminho)
        nova, _ = self.entregar(self.pasta / "segunda")
        self.assertEqual(len(antiga), len(nova))
        for (sop_antigo, antes), (sop_novo, depois) in zip(antiga, nova):
            self.assertNotEqual(sop_antigo, sop_novo)
            esperado = np.array(antes).reshape(-1, 3) + (23.0, 0.0, 0.0)
            np.testing.assert_allclose(np.array(depois).reshape(-1, 3), esperado, rtol=0, atol=1e-4)


class TestIndice(unittest.TestCase):
    def test_ultima_comparacao_define_ordem_conteudo_e_limite(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "comparacoes.jsonl"
            linhas = [
                {"uid": "1", "estrutura": "A", "n": 0}, {"uid": "2", "estrutura": "A", "n": 1},
                {"uid": "1", "estrutura": "B", "n": 2}, {"uid": "1", "estrutura": "A", "n": 3, "vista_nome": "legado"},
            ]
            p.write_text("\n".join(map(json.dumps, linhas)) + "\n{\nnull\n", encoding="utf-8")
            with mock.patch.object(radai_archive, "caminho_comparacoes", return_value=p):
                for limite, esperado in ((None, [3, 2, 1]), (0, [3, 2, 1]), (2, [3, 2]), (-1, [3, 2])):
                    regs = radai_archive.ler_comparacoes(limite)
                    self.assertEqual([r["n"] for r in regs], esperado)
                    self.assertEqual(regs[0]["nv_nome"], "legado")


if __name__ == "__main__":
    unittest.main()
