"""Contracts on synthetic grids. No network, model weights, inference or patient data."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
import numpy as np
import SimpleITK as sitk
import radai_recortes_ct as crop
import radai_tasks as tasks


class Bounds:
    def __init__(self, shape, bounds):
        self.shape, self.bounds = shape, bounds

    def __contains__(self, name):
        return name in self.bounds

    def caixa_de(self, name):
        return self.bounds[name]


class RecortesCT(unittest.TestCase):
    def setUp(self):
        self.image = sitk.Image([100, 100, 200], sitk.sitkInt16)
        self.image.SetSpacing([3.0, 4.0, 5.0])
        self.image.SetOrigin([17.0, -82.0, 113.0])
        self.shape = self.image.GetSize()[::-1]
        labels = {label for _, required, *_ in [*crop.FIELDS.values(), crop.PELVIC_FIELD] for label in required}
        self.raw = Bounds(self.shape, {key: ((60, 90), (36, 61), (26, 63)) for key in labels})
        for key in labels:
            if key.endswith(("_left", "_right")):
                x = (55, 70) if key.endswith("_left") else (25, 40)
                self.raw.bounds[key] = ((60, 90), (36, 61), x)

    def test_audit_covers_the_complete_installed_ct_catalog(self):
        self.assertEqual(set(crop.FIELDS) | set(crop.WIDE) | crop.NATIVE,
                         {r["task"] for r in tasks.CATALOGO if r["modalidade"] == "CT"})
        self.assertFalse(set(crop.FIELDS) & set(crop.WIDE) or (set(crop.FIELDS) | set(crop.WIDE)) & crop.NATIVE)
        for task in crop.FIELDS:
            with self.subTest(task=task):
                box, why = crop.propor(task, self.image, self.raw, None)
                self.assertIsNotNone(box, why)
                self.assertFalse(box["medido"])

    def test_breast_preserves_lateral_and_anterior_field(self):
        b, why = crop.propor("breasts", self.image, self.raw, None)
        self.assertEqual(b["zyx"], ((44, 107), (0, 100), (0, 100)), why)
        del self.raw.bounds["rib_right_12"]
        self.assertIsNone(crop.propor("breasts", self.image, self.raw, None)[0])

    def test_bilateral_anchors_agree_with_physical_left_and_right(self):
        flip = (-1.,0.,0., 0.,-1.,0., 0.,0.,1.)
        self.image.SetDirection(flip)
        self.assertIn("lateralidade", crop.propor("breasts", self.image, self.raw, None)[1])
        for k, box in list(self.raw.bounds.items()):
            a, b = box[2]
            self.raw.bounds[k] = (box[0], box[1], (99-b, 99-a))
        self.assertIsNotNone(crop.propor("breasts", self.image, self.raw, None)[0])

    def test_orbital_margin_in_mm_and_native_geometry(self):
        import engine
        b, why = crop.propor("oculomotor_muscles", self.image, self.raw, None)
        self.assertEqual(b["zyx"], ((48, 103), (21, 77), (6, 84)), why)
        roi = engine.recortar_imagem(self.image, b)
        roi[25, 31, 27] = 8
        restored = engine.colar_na_grade(roi, self.image, b)
        self.assertEqual(restored.GetSize(), self.image.GetSize())
        self.assertEqual(restored.GetOrigin(), self.image.GetOrigin())
        self.assertEqual(restored.GetSpacing(), self.image.GetSpacing())
        self.assertEqual(restored[31, 52, 75], 8)

    def test_missing_partial_wrong_grade_oblique_and_small_saving_use_full(self):
        task = "oculomotor_muscles"
        self.assertIsNone(crop.propor(task, self.image, None, {})[0])
        self.raw.bounds["skull"] = ((0, 90), (36, 61), (26, 63))
        self.assertIsNone(crop.propor(task, self.image, self.raw, None)[0])
        for label in crop.HEAD:
            self.raw.bounds[label] = ((70, 73), (50, 52), (50, 53))
        self.assertIsNone(crop.propor(task, self.image, self.raw, None)[0])
        self.raw.bounds["skull"] = ((4, 196), (4, 96), (4, 96))
        self.assertIsNone(crop.propor(task, self.image, self.raw, None)[0])
        self.raw.shape = (10, 10, 10)
        self.assertIn("geometria", crop.propor(task, self.image, self.raw, None)[1])
        self.image.SetDirection((1,0,0, 0,0,1, 0,1,0))
        self.assertIn("orientação", crop.propor(task, self.image, self.raw, None)[1])

    def test_guards_every_artificial_face_but_accepts_the_original_faces(self):
        box, _ = crop.propor("oculomotor_muscles", self.image, self.raw, None)
        shape = tuple(b-a for a,b in box["zyx"])
        a = np.zeros(shape, np.uint8)
        with self.assertRaises(crop.CampoCompletoNecessario):
            crop.conferir_saida(a, self.image, box)
        idx = [n//2 for n in shape]
        a[tuple(idx)] = 4
        crop.conferir_saida(a, self.image, box)
        for axis in range(3):
            for i in (0, -1):
                face = list(idx)
                face[axis] = i
                a[tuple(face)] = 1
                with self.assertRaises(crop.CampoCompletoNecessario):
                    crop.conferir_saida(a, self.image, box)
                a[tuple(face)] = 0
        box, _ = crop.propor("breasts", self.image, self.raw, None)
        a = np.zeros(tuple(b-a for a,b in box["zyx"]), np.uint8)
        a[a.shape[0]//2, 0, -1] = 1
        crop.conferir_saida(a, self.image, box)

    def test_scheduler_retries_only_the_failed_task_and_uses_only_base_sources(self):
        import engine
        for mode in ("fast", "auto", "perso"):
            seen, ended, raw = [], [], {}
            def simulate(_, name, device, jid, **kw):
                seen.append((name, bool(kw.get("caixa"))))
                if name == "total_v3":
                    raw[name] = self.raw
                elif kw.get("caixa"):
                    raise crop.CampoCompletoNecessario("face artificial")
                return {}
            res = engine.rodar_tasks(self.image, ["total_v3", "lung_nodules"], "cpu", None,
                                     rodar=simulate, cruas=raw, portao=False, modo=mode,
                                     ao_terminar=lambda n,d: ended.append((n,d["ok"])))
            self.assertEqual(seen, [("total_v3",False), ("lung_nodules",True), ("lung_nodules",False)])
            self.assertEqual(ended, [("total_v3", True), ("lung_nodules", True)])
            self.assertFalse(res["recortes"])
        seen = []
        engine.rodar_tasks(self.image, ["liver_segments"], "cpu", None, rodar=simulate,
                           cruas={"total_v3": self.raw}, portao=False)
        self.assertEqual(seen, [("liver_segments",False)])

    def test_short_breast_scan_keeps_existing_transverse_crop_and_checks_its_edges(self):
        import engine
        del self.raw.bounds["rib_left_12"]
        lateral = {"task": "breasts", "zyx": ((0, self.shape[0]), (10, 91), (4, 93)),
                   "eixos": "xy pelo corpo", "pelo_corpo": True}
        called = []
        def simulate(_, name, device, jid, **kw):
            called.append(kw.get("caixa"))
            return {}
        with patch.object(engine, "caixa_de_recorte", return_value=(lateral, "")):
            engine.rodar_tasks(self.image, ["breasts"], "cpu", None, rodar=simulate,
                               cruas={"total_v3": self.raw}, portao=False)
        self.assertEqual(called, [dict(lateral, vigiar_faces=True)])

    def test_rectum_retries_boundary_on_native_field_and_restores_exact_coordinates(self):
        import radai_rectum_jhu as jhu
        box, _ = crop.propor("jhu_rectum", self.image, self.raw, None)
        shape = tuple(hi-lo for lo,hi in box["zyx"])
        for cut in (False, True):
            calls = []
            def predict(img, *args):
                size = img.GetSize()[::-1]
                calls.append(size)
                m = np.zeros(size, bool)
                center = [n//2 for n in size]
                if cut and size == shape:
                    center[0] = 0
                m[tuple(center)] = True
                return m, {}
            with patch.object(jhu, "_segmentar_novo", side_effect=predict):
                mask, info = jhu.segmentar(self.image, pasta_pesos=Path.cwd(), base_ts=self.raw)
            self.assertEqual(mask.shape, self.shape)
            self.assertEqual(calls, [shape, self.shape] if cut else [shape])
            pos = tuple(n//2 for n in self.shape) if cut else tuple(
                lo + n//2 for (lo,_), n in zip(box["zyx"], shape))
            self.assertTrue(mask[pos])
            self.assertEqual(bool(info.get("recorte_pelve")), not cut)


class SuporteLargoTC(unittest.TestCase):
    def test_todos_os_planos_e_tecido_fora_da_predicao(self):
        import SimpleITK as sitk
        import engine
        hu = np.full((20, 180, 200), -1024, dtype=np.int16)
        hu[:, 60:115, 65:125] = 40
        hu[14, 42, 155] = 70
        ref = sitk.GetImageFromArray(hu)
        ref.SetSpacing((2., 2., 2.))
        mask = np.zeros_like(hu, dtype=np.uint8)
        mask[:, 68:72, 78:82] = 1
        mask[1:15, 57:66, 50:60] = 2
        base = engine.MasksCruas(mask, {1: "liver", 2: "spleen"})
        caixa, motivo = crop.suporte_transversal(ref, base)
        self.assertIsNotNone(caixa, motivo)
        self.assertEqual(caixa["zyx"], ((0, 20), (17, 140), (25, 181)))
        self.assertIsNone(crop.suporte_transversal(ref, None)[0])


if __name__ == "__main__":
    unittest.main()
