"""Regression coverage for combined chest STUDY and native per-phase RTSTRUCTs."""
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from datetime import datetime
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "app"), str(ROOT / "tools")]

import make_test_series
import numpy as np
import pydicom
import radai_lung as lung


class LungStudy(unittest.TestCase):
    def test_presets_and_invalid_choices(self):
        import radai_batch as batch
        for protocol in ("torax_mama", "sbrt_pulmao"):
            for effort in ("leve", "medio", "alto", "extra", "maximo", "ultra"):
                self.assertEqual(lung.opcoes_study(protocol, effort, True), (protocol, effort))
                series = dict(modo="perso", modalidade="CT", protocolos=[protocol], esforco=effort,
                              tasks={lung.TASK: True}, tasks_marcadas=[lung.TASK], achado_declarado=True)
                choice = batch.escolha_da_serie(series)
                self.assertEqual(choice["esforco"], effort)
                self.assertIn(lung.TASK, batch.escopo_da_escolha(choice))
        for protocol, effort in (("abdome", "maximo"), ("sbrt_pulmao", "unknown"), ("nodulos", "alto")):
            with self.assertRaises(ValueError):
                lung.opcoes_study(protocol, effort, True)

    def test_protocol_reports_empty_nodule_and_partial_study(self):
        import radai_batch as batch
        def deliver(*args, **kwargs):
            kwargs["ao_receber_nodulos"](None, mask)
            return {"conjuntos": ["oar"], "nodulo_no_study": written}
        mask, written = None, False
        with patch.object(batch, "_uma_serie", side_effect=deliver), patch.object(
                lung, "_inspecionar", side_effect=AssertionError("source inspected by batch")):
            self.assertFalse(lung.processar_com_protocolo({}, {"marcadores": {}},
                                                          "torax_mama", "alto", "signature"))
            mask = np.ones((5,5,5), bool)
            with self.assertRaisesRegex(RuntimeError, "não gerou contorno"):
                lung.processar_com_protocolo({}, {"marcadores": {}}, "sbrt_pulmao", "alto", "signature")
            written = True
            self.assertTrue(lung.processar_com_protocolo({}, {"marcadores": {}},
                                                         "sbrt_pulmao", "extra", "signature"))

    def test_native_lung_files_survive_routine_study_replacement(self):
        from radai_topography import entregas_a_substituir
        native = ["RS_RadAI_STUDY_LUNG_123_456.dcm", "RS_RadAI_NOD_LUNG_1_456.dcm",
                  "RS_RadAI_ITV4D_2_456.dcm"]
        self.assertEqual(entregas_a_substituir(native + ["RS_RadAI_normal.dcm"]), ["RS_RadAI_normal.dcm"])

    def test_combined_study_and_phase_rtstructs_reference_native_ct(self):
        import engine
        import radai_archive
        import radai_batch as batch
        import radai_topography
        from contextlib import ExitStack

        with tempfile.TemporaryDirectory(prefix="lung_study_test_") as base, ExitStack() as stack:
            root = Path(base)
            env = dict(LOCALAPPDATA=base, RADAI_CALIB_DIR=base, RADAI_REGISTRO_DIR=base,
                       RADAI_TMP=base, RADAI_NOTIFICACAO="0", RADAI_URL_VERSOES="0")
            stack.enter_context(patch.dict(os.environ, env))
            study, frame = pydicom.uid.generate_uid(), pydicom.uid.generate_uid()
            ids, image_ids = [], {}
            for pos, percent in enumerate((0, 50)):
                folder = root / str(percent)
                uid = make_test_series.escreve_serie(str(folder), "PHANTOM", datetime(2026, 1, 1), 12)
                ids.append(uid)
                image_ids[uid] = set()
                for path in folder.glob("*.dcm"):
                    image = pydicom.dcmread(path)
                    image.StudyInstanceUID = study
                    image.FrameOfReferenceUID = frame
                    image.SeriesDescription = "Respiratory %d%%" % percent
                    image.save_as(path, enforce_file_format=True)
                    image_ids[uid].add(str(image.SOPInstanceUID))
            events, calls = [], []
            cfg = dict(device="cpu", min_cortes=5, log=events.append, marcadores={
                "has_marker": lambda *a: True, "claim": lambda *a: True, "unclaim": lambda *a: None,
                "lock_e_meu": lambda *a: (True, "TEST"), "renovar": lambda *a, **k: True,
                "m_path": lambda p,u,k: Path(p) / ("fixture-" + k)})
            def native(ref, task, *args, **kwargs):
                calls.append(task)
                shape = tuple(reversed(ref.GetSize()))
                m = np.zeros(shape, np.uint8)
                if task == lung.TASK:
                    m[2:10,28:45,28:45] = 1
                    m[4:9,32:40,32:40] = 2
                    labels = {1: "lung", 2: lung.TASK}
                else:
                    m[2:10,30:60,28:56] = 1
                    labels = {1: "lung_upper_lobe_left" if task.startswith("total") else
                              {"trunk_cavities": "pericardium", "breasts":"breast",
                               "pleural_pericard_effusion":"pericardial_effusion",
                               "lung_vessels":"lung_airways"}.get(task, "heart")}
                if kwargs.get("cruas") is not None:
                    kwargs["cruas"][task] = engine.MasksCruas(m, labels)
                return {name:m == idx for idx,name in labels.items()}
            stack.enter_context(patch.object(engine, "run_ts_task", side_effect=native))
            stack.enter_context(patch.object(radai_archive, "registrar_serie"))
            stack.enter_context(patch.object(batch, "_notificar_a_serie"))
            stack.enter_context(patch.object(radai_topography, "anatomia_da_base",
                 return_value=dict(regioes=["torax"], laudo=[], coracao_cm3=None, pescoco=(False, ""))))
            series = sorted(lung.varrer(base, cfg), key=lambda s:s["fase_respiratoria"])
            fases = lung.rodar_4d(series, ids[0], ids[1], cfg, threading.Event(), events.append,
                                  protocolo="torax_mama", esforco="maximo")
            self.assertEqual(fases["estados_fases"], ["positivo", "positivo"], events)
            self.assertEqual(calls.count(lung.TASK), 2, calls)
            self.assertEqual(fases["serie"]["uid"], ids[1])
            def check_file(path, uid):
                ds = pydicom.dcmread(path)
                ref = ds.ReferencedFrameOfReferenceSequence[0]
                self.assertEqual(str(ref.FrameOfReferenceUID), frame)
                rs = ref.RTReferencedStudySequence[0].RTReferencedSeriesSequence[0]
                self.assertEqual(str(rs.SeriesInstanceUID), uid)
                self.assertEqual(ds.ApprovalStatus, "UNAPPROVED")
                for roi in ds.ROIContourSequence:
                    for contour in roi.ContourSequence:
                        self.assertTrue(contour.ContourImageSequence)
                        for image in contour.ContourImageSequence:
                            self.assertIn(str(image.ReferencedSOPInstanceUID), image_ids[uid])
                return [str(roi.ROIName) for roi in ds.StructureSetROISequence]
            for i, s in enumerate(series):
                files = list(Path(s["pasta"]).glob("RS_RadAI*.dcm"))
                self.assertEqual(len(files), 1, (i,files))
                rois = check_file(files[0], s["uid"])
                self.assertGreater(len(rois), 0)
                if i == 0:
                    self.assertGreater(len(rois), 1, rois)
                    self.assertIn("STUDY", files[0].name)
                else:
                    self.assertIn("NOD", files[0].name)
            self.assertTrue(fases["masks"])
            lung.exportar(fases["serie"], fases["assinatura"], fases["masks"], cfg, fases["curvas"])
            check_file(next(Path(series[1]["pasta"]).glob("RS_RadAI_ITV4D*.dcm")), ids[1])

if __name__ == "__main__":
    unittest.main()
