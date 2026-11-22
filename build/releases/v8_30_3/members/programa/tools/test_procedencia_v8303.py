"""Read the actual synthetic RTSTRUCT and check the policy against workstation receipts."""
from datetime import datetime
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "tools"))

import numpy as np
import pydicom
import engine
import make_test_series as phantom
import radai_consent as consent
import radai_sets


class Procedencia(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.enter = patch.dict(os.environ, {
            "RADAI_CALIB_DIR": str(self.base / "archive"),
            "RADAI_REGISTRO_DIR": str(self.base / "logs"),
            "COMPUTERNAME": "FANTOMA-8303",
        })
        self.enter.start()
        self.addCleanup(self.enter.stop)

    def test_dicom_study_full_nomes_unioes_e_fonte_alternativa(self):
        ct = self.base / "ct"
        with patch.object(phantom, "ROWS", 32), patch.object(phantom, "COLS", 32):
            phantom.escreve_serie(str(ct), "FANTOMA", datetime(2026, 1, 1), 9)
        for jhu in (True, False):
            with self.subTest(jhu=jhu):
                masks = {}
                for key, y in (("rectum", 4), ("colon", 11), ("urinary_bladder", 18)):
                    masks[key] = np.zeros((9, 32, 32), dtype=bool)
                    masks[key][2:7, y:y + 5, 10:19] = True
                origins = ({"rectum": "jhu_rectum", "colon": "ts_jhu_colon"} if jhu else {})
                masks["vazia"] = np.zeros((9, 32, 32), dtype=bool)
                origins["vazia"] = "jhu_rectum"
                # Keep all files of the writer, including its temporary FULL, inside the phantom.
                with patch.object(tempfile, "tempdir", str(self.base)):
                    prepared, standard = engine.build_rtstruct(
                        str(ct), masks, adiar=True, rotulo="RadAI_FULL", origem=origins,
                        modalidade="CT", exigir_grade=True, externo=np.ones((9, 32, 32), bool))
                    try:
                        study = self.base / "study.dcm"
                        selected = {"rectum", "colon", "urinary_bladder"}
                        prepared.gravar_selecao(selected, str(study),
                            nomes={standard["rectum"]: "RetoLocal"},
                            unioes=[{"nome": "IntestinoLocal", "de": ["colon", "rectum"]},
                                    {"nome": "OutroLocal", "de": ["urinary_bladder", "ausente", "vazia"]}])
                        full, _ = prepared.gravar()
                    finally:
                        prepared.liberar()
                for path in (study, Path(full)):
                    ds = pydicom.dcmread(path)
                    rois = {r.ROIName: r for r in ds.StructureSetROISequence}
                    number_contoured = {int(c.ReferencedROINumber)
                                        for c in ds.ROIContourSequence if c.ContourSequence}
                    rectum = "RetoLocal" if path == study else standard["rectum"]
                    for name, roi in rois.items():
                        self.assertIn(int(roi.ROINumber), number_contoured)
                        desc = str(getattr(roi, "ROIDescription", ""))
                        expected = jhu and name in (rectum, standard["colon"], "IntestinoLocal")
                        self.assertEqual("Johns Hopkins / MICA" in desc, expected, name)
                        self.assertEqual("planejamento prostatico" in desc, expected, name)
                        self.assertEqual("recortado pelo reto" in desc,
                                         jhu and name in (standard["colon"], "IntestinoLocal"))
                    self.assertIn(rectum, rois)
                    if jhu or path == study:
                        self.assertEqual(radai_sets.nome_padrao_da_descricao(rois[rectum].ROIDescription),
                                         standard["rectum"])
                    if path == study:
                        self.assertIn("IntestinoLocal", rois)
                        self.assertIn("OutroLocal", rois)
                        self.assertIsNone(radai_sets.nome_padrao_da_descricao(
                            rois["IntestinoLocal"].ROIDescription))

    def test_long_union_keeps_cohort_within_dicom_st(self):
        desc = radai_sets.com_procedencia_do_reto("a" * 1025, {"ts_jhu_colon"})
        self.assertLessEqual(len(desc), 1024)
        self.assertIn("planejamento prostatico", desc)
        self.assertTrue(desc.endswith("reto JHU."))

    def test_old_receipts_require_explicit_confirmation(self):
        options = dict(itens=[p[0] for p in consent.PONTOS], ensino_pesquisa=True,
                       catalogo_sha256=consent.catalogo_termos.catalogo()[0],
                       ferramentas=consent.catalogo_termos.grupos_opcionais())
        path = consent._caminho()
        path.parent.mkdir(parents=True)
        for previous in ("2.9", "3.0"):
            old = dict(consent.montar_registro("FANTOMA", **options), versao=previous,
                       impressao=consent.IMPRESSOES_PUBLICADAS[previous])
            original = json.dumps(old).encode("utf8")
            path.write_bytes(original)
            self.assertFalse(consent.aceito())
            self.assertFalse(consent.ferramenta_autorizada("moose"))
            self.assertEqual(consent.aceite(), old)
            self.assertEqual(path.read_bytes(), original)
        new = consent.registrar_aceite("FANTOMA", **options)
        self.assertEqual(new["versao"], "3.1")
        self.assertEqual(new["impressao"], consent.IMPRESSOES_PUBLICADAS["3.1"])
        self.assertTrue(consent.aceito())
        self.assertTrue(consent.ferramenta_autorizada("moose"))

    def test_credits_and_local_receipt_documentation(self):
        atlas = ROOT / "app/data/ajuda-tasks"
        items = json.loads((atlas / "fontes.json").read_text("utf8"))
        licensed = [key for key, info in items.items() if "BodyParts3D" in info["autor"]]
        self.assertGreater(len(licensed), 0)
        notice = (ROOT / "NOTICE").read_text("utf8")
        for key in licensed:
            item = items[key]
            self.assertTrue((atlas / (key + ".png")).is_file())
            self.assertIn(item["licenca_url"], notice)
            self.assertIn("CC BY-SA 2.1 JP", item["licenca"])
            self.assertIn("The Database Center for Life Science", item["autor"])
        policy = consent._visivel(consent.POLITICA)
        for field in ("SID", "UTC", "perfil de instalação", "nome do computador",
                      "LICENCAS_COMPONENTES.json", "LOCALAPPDATA", "remoção local",
                      "a importação preserva o valor local"):
            self.assertIn(field, policy)


if __name__ == "__main__":
    unittest.main()
