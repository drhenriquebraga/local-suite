"""Compare the bowel contours persisted by the STUDY writer on a DICOM phantom."""
from datetime import datetime
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import pydicom

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "app"), str(ROOT / "tools")]
import engine
import make_test_series as phantom
import radai_rt
import radai_geom
import radai_study_modelos


class BowelStudyFinish(unittest.TestCase):
    def test_small_bowel_first_large_interfaces_and_bilateral_limit(self):
        shape = (20, 36, 40)
        z,y,x = np.indices(shape)
        reto = (z>=2)&(z<=14)&(y>=12)&(y<23)&(x>=12)&(x<24)
        colon = (z>=7)&(z<=16)&(y>=10)&(y<20)&(x>=17)&(x<30)
        ilha = (z==12)&(y==22)&(x>=11)&(x<=12)
        colon |= ilha
        small = (z>=6)&(z<=8)&(x>=11)&(x<15)&(y>=17)&(y<22)
        esq = (z>=5)&(z<=15)&(y>=9)&(y<14)&(x>=3)&(x<6)
        dir = (z>=4)&(z<=15)&(y>=9)&(y<14)&(x>=34)&(x<37)
        for order in (1,-1):
            grade = radai_geom.Grade((2,1,1),("sup" if order==1 else "inf","post","esq"))
            part = radai_study_modelos.repartir_intestino(engine,engine.MascaraCompacta.de(reto[::order]),
                colon[::order],small[::order], (esq[::order],dir[::order]),grade)
            r,c,ilha_real,anal = [p.cheia()[::order] for p in part[:4]]
            self.assertEqual(part[4],5)
            np.testing.assert_array_equal(ilha_real,ilha)
            np.testing.assert_array_equal(r, ((reto|ilha)&~small)&(z>=5))
            np.testing.assert_array_equal(anal,(reto&~small)&(z<5))
            np.testing.assert_array_equal(c,colon & ~ilha)
            self.assertTrue((c&r).any())
        for lados in [(None,dir),(esq|((z==0)&(y==11)&(x==4)),dir)]:
            result=radai_study_modelos.repartir_intestino(engine,engine.MascaraCompacta.de(reto),colon,small,
                lados,radai_geom.Grade((2,1,1)))
            self.assertIsNone(result[4])
            self.assertFalse(result[3].any())

    def test_reopened_anorectal_partition_with_large_interface_and_small_bowel(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(tempfile, "tempdir", temp), patch.dict(
                os.environ, {"RADAI_CALIB_DIR": temp, "RADAI_REGISTRO_DIR": temp}):
            ct = Path(temp) / "ct"
            with patch.object(phantom, "ROWS", 48), patch.object(phantom, "COLS", 48):
                phantom.escreve_serie(str(ct), "FANTOMA", datetime(2026, 1, 1), 18)
            shape = (18,48,48)
            z,y,x = np.indices(shape)
            raw = (z>=2)&(z<=13)&(y>=15)&(y<=25)&(x>=14)&(x<=24)
            gross = (z>=7)&(z<=15)&(y>=12)&(y<=21)&(x>=19)&(x<=35)
            small = (z>=7)&(z<=10)&(y>=15)&(y<=23)&(x>=10)&(x<=16)
            original = {"colon": gross, "small_intestine": small,
                        "hip_left": (z>=5)&(z<16)&(x==5)&(y==14),
                        "hip_right": (z>=4)&(z<16)&(x==39)&(y==14)}
            source = SimpleNamespace(engine=engine, modalidade="CT", log=lambda _: None,
                                     _img_lida=SimpleNamespace(GetSize=lambda: shape[::-1]))
            with patch("radai_rectum_jhu.segmentar", return_value=(raw, {})):
                pelvic = radai_study_modelos.aplicar(source, original, {}, {"rectum","colon","anus"},
                         {"pelve"}, radai_geom.Grade((2,1,1)), "cpu", "", usar_arcos=False)
            self.assertEqual(pelvic["pelve_terminal"]["bilateral"],5)
            inputs = {k:v for k,v in original.items() if not k.startswith("hip")}
            inputs["anus"] = (z<=7)&(z>=1)&(x>=17)&(x<=26)&(y>=18)&(y<=26)
            for tps in (engine.TPS_ECLIPSE, engine.TPS_MONACO):
                with self.subTest(tps=tps), patch.object(engine,"tps_destino",return_value=tps):
                    pre,names = engine.build_rtstruct(str(ct),dict(inputs), suavizar_mm=1.5, adiar=True,
                            modalidade="CT", exigir_grade=True, externo=np.ones(shape,bool),
                            perfil_contornos="padrao", limites_intestinais=pelvic["limites"],
                            sobreposicao_reto_jhu=pelvic["sobreposicao_reto_jhu"],
                            pelve_terminal=pelvic["pelve_terminal"])
                    path = Path(temp) / ("recorte-"+tps+".dcm")
                    try:
                        pre.gravar_selecao(set(inputs),str(path))
                    finally:
                        pre.liberar()
                    study = radai_rt.abrir(str(ct),path,com_ct=False)
                    try:
                        r,c,d,a = (study.mascara(names[k]) for k in ("rectum","colon","small_intestine","anus"))
                        self.assertFalse(r[:5].any())
                        self.assertTrue(r[5].any())
                        self.assertFalse((r & a).any())
                        self.assertFalse((r & d).any())
                        self.assertTrue((r & c)[8:11,17:21,20:23].all())
                        self.assertTrue(a[2:5,16:25,15:24].all())
                    finally:
                        study.fechar()

    def test_keeps_the_standard_coordinates_when_no_voxel_needs_correction(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(tempfile, "tempdir", temp), patch.dict(
                os.environ, {"RADAI_CALIB_DIR": temp, "RADAI_REGISTRO_DIR": temp}):
            ct = Path(temp) / "ct"
            with patch.object(phantom, "ROWS", 40), patch.object(phantom, "COLS", 40):
                phantom.escreve_serie(str(ct), "FANTOMA", datetime(2026, 1, 1), 8)
            z, y, x = np.indices((8, 40, 40))
            mask = (abs(z-4) < 3) & ((x-10)**2/49 + (y-20)**2/85 < 1)
            # A previous body crop can put the entire current ROI well inside
            # its authorized model support. Its ordinary contours must survive.
            supports = {"rectum": engine.MascaraCompacta.de(x < 20),
                        "colon": engine.MascaraCompacta.de(x >= 20)}
            empty = engine.MascaraCompacta(mask.shape, None, None)
            contours = []
            for options in ({}, {"limites_intestinais": supports,
                                 "sobreposicao_reto_jhu": empty}):
                inputs = {"rectum": mask.copy(), "colon": np.roll(mask, 20, axis=2)}
                prepared, _ = engine.build_rtstruct(str(ct), inputs, suavizar_mm=1.5, adiar=True,
                    modalidade="CT", exigir_grade=True, externo=np.ones(mask.shape, bool),
                    perfil_contornos="padrao", **options)
                path = Path(temp) / ("study-%d.dcm" % len(contours))
                try:
                    prepared.gravar_selecao(set(inputs), str(path))
                finally:
                    prepared.liberar()
                ds = pydicom.dcmread(path)
                self.assertEqual(len(ds.ROIContourSequence), 2)
                contours.append([[tuple(c.ContourData) for c in roi.ContourSequence]
                                 for roi in ds.ROIContourSequence])
            self.assertEqual(contours[0], contours[1])

    def test_finished_polygons_respect_jhu_voxels_and_unclaimed_space(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(tempfile, "tempdir", temp), patch.dict(
                os.environ, {"RADAI_CALIB_DIR": temp, "RADAI_REGISTRO_DIR": temp}):
            base = Path(temp)
            ct = base / "ct"
            with patch.object(phantom, "ROWS", 96), patch.object(phantom, "COLS", 96):
                phantom.escreve_serie(str(ct), "FANTOMA", datetime(2026, 1, 1), 13)
            z, y, x = np.indices((13, 96, 96))
            rectum = (abs(z-6) < 5) & ((x-16)**2/108 + (y-41)**2/158 < 1)
            rectum[:, 41:43, 25:28] = False
            colon = np.roll(rectum, 31, axis=2)
            small = np.roll(rectum, 62, axis=2)
            # The TS label also occupies a small JHU edge on one slice only.
            ilha = np.zeros_like(colon)
            ilha[3, 37:40, 24:28] = True
            colon |= ilha
            shared = colon & rectum
            self.assertTrue(shared.any())
            original = {"colon": colon, "small_intestine": small}
            shape = rectum.shape
            origins = {}
            source = SimpleNamespace(engine=engine, modalidade="CT", log=lambda _: None,
                                     _img_lida=SimpleNamespace(GetSize=lambda: shape[::-1]))
            with patch("radai_rectum_jhu.segmentar", return_value=(rectum, {})):
                pelvic = radai_study_modelos.aplicar(source, original, origins, {"rectum", "colon"},
                                                      {"pelve"}, radai_geom.Grade((2, 1, 1)), "cpu", "", usar_arcos=False)
            self.assertTrue(pelvic["limites"].keys() >= {"rectum", "colon"})
            np.testing.assert_array_equal(pelvic["sobreposicao_reto_jhu"].cheia(), ilha)
            for tps in (engine.TPS_ECLIPSE, engine.TPS_MONACO):
                with self.subTest(tps=tps), patch.object(engine, "tps_destino", return_value=tps):
                    prepared, names = engine.build_rtstruct(str(ct), dict(original), origem=origins,
                        suavizar_mm=1.5, adiar=True, rotulo="RadAI_FULL", modalidade="CT",
                        exigir_grade=True, externo=np.ones(shape, bool), perfil_contornos="padrao",
                        limites_intestinais=pelvic["limites"], sobreposicao_reto_jhu=pelvic["sobreposicao_reto_jhu"],
                        pelve_terminal=pelvic["pelve_terminal"])
                    path = base / ("study-" + tps + ".dcm")
                    try:
                        prepared.gravar_selecao(set(original), str(path), nomes={names["rectum"]: "RetoLocal"})
                    finally:
                        prepared.liberar()
                    ds = pydicom.dcmread(path)
                    fractions = {}
                    for roi in ds.StructureSetROISequence:
                        rc = next(r for r in ds.ROIContourSequence if r.ReferencedROINumber == roi.ROINumber)
                        ring = rc.ContourSequence[len(rc.ContourSequence)//2]
                        xy = np.asarray(ring.ContourData, float).reshape(-1, 3)[:, :2]
                        edges = xy - np.roll(xy, 1, axis=0)
                        fractions[str(roi.ROIName)] = np.mean(np.abs(edges).min(axis=1) < 1e-5)
                    for name in (names["colon"], "RetoLocal"):
                        # Native doubled-grid outlines give 84% axial edges on this
                        # curved phantom; the actual small-bowel reference has 6%.
                        self.assertLess(fractions[name], fractions[names["small_intestine"]] + .30)
                    reader = radai_rt.abrir(str(ct), path, com_ct=False)
                    try:
                        r = reader.mascara("RetoLocal")
                        c = reader.mascara(names["colon"])
                        self.assertFalse((r & c).any())
                        self.assertFalse((r & ~(rectum | ilha)).any())
                        self.assertFalse((c & ~colon).any())
                        self.assertFalse((shared & ~r).any())
                    finally:
                        reader.fechar()


if __name__ == "__main__":
    unittest.main()
