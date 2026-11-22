"""Round-trip of synthetic off-centre contours on rectangular DICOM pixels."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

import numpy as np
import pydicom
from pydicom.dataset import Dataset
from pydicom.uid import CTImageStorage, generate_uid
from rt_utils import ds_helper
from rt_utils.rtstruct import RTStruct

import engine
from radai_contour_edit import writer_add_roi
from radai_rt import SessaoRT, cabecalhos_para_matriz_rt_utils


def synthetic_rt(spacing):
    uid, series_uid, frame = (generate_uid() for _ in range(3))
    series = []
    for k in range(3):
        d = Dataset()
        d.StudyInstanceUID, d.SeriesInstanceUID, d.FrameOfReferenceUID = uid, series_uid, frame
        d.StudyDate, d.StudyTime, d.StudyID = "20200101", "120000", "PHANTOM"
        d.SOPClassUID, d.SOPInstanceUID = CTImageStorage, generate_uid()
        d.ImagePositionPatient = [-98.5, 21.0, -10.0 + 2.5 * k]
        d.ImageOrientationPatient = [.8, .6, 0, -.6, .8, 0]
        d.PixelSpacing, d.Rows, d.Columns = spacing, 30, 42
        series.append(d)
    return RTStruct(series, ds_helper.create_rtstruct_dataset(series))


class PixelSpacingRT(unittest.TestCase):
    def check_delivery(self, spacing, route):
        rt = synthetic_rt(spacing)
        mask = np.zeros((3, 30, 42), dtype=bool)
        mask[1, 8:16, 15:26] = True
        name, color = "Synthetic", [120, 40, 160]
        if route == "editor":
            geometry = dict(direction=np.array([[.8, -.6, 0], [.6, .8, 0], [0, 0, 1]]),
                            spacing=(2.5, *spacing), origin=rt.series_data[0].ImagePositionPatient)
            writer_add_roi(engine, rt, mask, name, color, geometry)
        elif route in ("terminal", "per_image"):
            engine._trocar_mascara_terminal(rt.ds, rt.series_data, name, 1, mask, color,
                                            None, spacing[::-1], por_imagem=route=="per_image")
        elif route == "fallback":
            with patch.object(engine, "_rt_utils_instalado", return_value="other"):
                engine._adicionar_mascara_rt(rt, mask, name, color)
        else:
            engine._adicionar_mascara_rt(rt, mask, name, color)

        with tempfile.TemporaryDirectory(prefix="spacing-rt-") as directory:
            path = Path(directory) / "rt.dcm"
            engine.gravar_dicom_em_fluxo(rt.ds, str(path))
            reopened = pydicom.dcmread(path)
        roi = reopened.ROIContourSequence[0]
        self.assertEqual(len(roi.ContourSequence), 1)
        contour = roi.ContourSequence[0]
        image = rt.series_data[1]
        self.assertEqual(contour.ContourImageSequence[0].ReferencedSOPInstanceUID, image.SOPInstanceUID)
        xyz = np.array(contour.ContourData, dtype=float).reshape(-1, 3)
        # Independent DICOM pixel coordinates, never inferred from the writer's matrix.
        axes = np.asarray(image.ImageOrientationPatient).reshape(2, 3)
        xy = (xyz - np.array(image.ImagePositionPatient)) @ axes.T / np.array(spacing[::-1])
        bounds = np.concatenate([xy.min(axis=0), xy.max(axis=0)])
        np.testing.assert_allclose(bounds, [15, 8, 25, 15], atol=.501 if route in
                                   ("terminal", "per_image", "editor") else .001)
        reader = SessaoRT(None, None, None, mask.shape, [name], RTStruct(rt.series_data, reopened))
        np.testing.assert_array_equal(reader.raster_da_roi(roi, por_imagem=route=="per_image"), mask)
        self.assertTrue(all(list(d.PixelSpacing) == spacing for d in rt.series_data))

    def test_rectangular_physical_coordinates_and_raster_roundtrip(self):
        for spacing in ([.96, .68], [.68, .96]):
            for route in ("common", "fallback", "terminal", "per_image", "editor"):
                with self.subTest(spacing=spacing, route=route):
                    self.check_delivery(spacing, route)

    def test_square_series_passes_unchanged(self):
        rt = synthetic_rt([.96, .96])
        self.assertIs(cabecalhos_para_matriz_rt_utils(rt.series_data), rt.series_data)
        self.check_delivery([.96, .96], "common")


if __name__ == "__main__":
    unittest.main()
