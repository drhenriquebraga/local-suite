"""Check delivered terminal contours in each referenced MR image's own coordinates."""
from datetime import datetime
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pydicom
from pydicom.uid import MRImageStorage, RTStructureSetStorage

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "app")]
import engine
import make_test_series as phantom


ROWS, COLS = 38, 52
REGULAR = (0, 3, 6, 9, 12, 15)
IRREGULAR = (0, 1.1, 2.8, 4.0, 12.5, 15)


def write_mr(directory, angle, offsets, drift):
    with patch.object(phantom, "ROWS", ROWS), patch.object(phantom, "COLS", COLS):
        phantom.escreve_serie(str(directory), "QA-MR", datetime(2020, 1, 1), len(offsets))
    a = np.deg2rad(angle)
    first, second = np.array([1., 0., 0.]), np.array([0., np.cos(a), np.sin(a)])
    normal = np.cross(first, second)
    images = []
    for k, path in enumerate(sorted(directory.glob("*.dcm"))):
        ds = pydicom.dcmread(path)
        ds.Modality = "MR"
        ds.SOPClassUID = ds.file_meta.MediaStorageSOPClassUID = MRImageStorage
        ds.SeriesDescription = "MR synthetic geometry"
        ds.PixelSpacing = [.96, .68]
        ds.ImageOrientationPatient = ["%.10g" % v for v in np.r_[first, second]]
        ipp = np.array([-98.5, 21.0, -10.0]) + normal * offsets[k] + k * drift * first
        ds.ImagePositionPatient = ["%.10g" % v for v in ipp]
        ds.save_as(path, enforce_file_format=True)
        images.append(ds)
    return images


def target_mask():
    mask = np.zeros((6, ROWS, COLS), dtype=bool)
    for k in (1, 2, 3, 4):
        # All the contours are off-centre and different on successive slices.
        mask[k, 6 + k:18 + k, 13 + 2*k:29 + 2*k] = True
        mask[k, 9 + k:14 + k, 13 + 2*k:16 + 2*k] = False
        mask[k, 7 + k, 29 + 2*k:32 + 2*k] = True
    return mask


def included_centres(polygon):
    # Even-odd horizontal ray in independent pixel-centre coordinates.
    y, x = np.indices((ROWS, COLS), dtype=float)
    inside = np.zeros((ROWS, COLS), dtype=bool)
    on_boundary = np.zeros_like(inside)
    for (ax, ay), (bx, by) in zip(polygon, np.roll(polygon, -1, axis=0)):
        dx, dy = bx - ax, by - ay
        if abs(dx) + abs(dy) < 1e-10:
            continue
        on_segment = (x-ax)*(x-bx) + (y-ay)*(y-by) <= 1e-8
        on_boundary |= on_segment & (np.abs((x-ax)*dy - (y-ay)*dx) < 1e-8)
        if dy:
            inside ^= ((ay > y) != (by > y)) & (x < ax + (y-ay)*dx/dy)
    return inside | on_boundary


class StudyMRGeometry(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="qa-study-mr-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        for config in (
            patch.object(tempfile, "tempdir", temp.name),
            patch.dict(os.environ, {"RADAI_CALIB_DIR": temp.name, "RADAI_REGISTRO_DIR": temp.name,
                                    "RADAI_ACEITA_TILT_MM": ""}),
            patch.object(engine, "tps_destino", return_value=engine.TPS_ECLIPSE),
        ):
            config.start()
            self.addCleanup(config.stop)

    def save_selection(self, directory, path, mask, meta):
        # A terminal overlap assigns exactly the known calibration mask to this ROI.
        support = engine.MascaraCompacta.de(mask)
        prepared, names = engine.build_rtstruct(str(directory), {"rectum": mask.copy()},
            adiar=True, modalidade="MR", exigir_grade=True, perfil_contornos="padrao", suavizar_mm=1.5,
            externo=np.ones(mask.shape, bool), limites_intestinais={"rectum": support},
            sobreposicao_reto_jhu=support, meta=meta)
        try:
            prepared.gravar_selecao({"rectum"}, str(path))
        finally:
            prepared.liberar()
        self.assertIn("acabamento_terminal", meta)
        return names["rectum"]

    def check_series(self, angle, offsets, drift):
        directory = self.base / "mr"
        images = write_mr(directory, angle, offsets, drift)
        mask = target_mask()
        path = self.base / "STUDY.dcm"
        roi_name = self.save_selection(directory, path, mask, {})
        rt = pydicom.dcmread(path)
        self.assertEqual(rt.SOPClassUID, RTStructureSetStorage)
        self.assertEqual(rt.StructureSetLabel, "RadAI_STUDY")
        self.assertEqual(str(rt.FrameOfReferenceUID), str(images[0].FrameOfReferenceUID))
        self.assertEqual(str(rt.StudyInstanceUID), str(images[0].StudyInstanceUID))
        by_sop = {str(img.SOPInstanceUID): (k, img) for k, img in enumerate(images)}
        frame, = rt.ReferencedFrameOfReferenceSequence
        study, = frame.RTReferencedStudySequence
        series, = study.RTReferencedSeriesSequence
        self.assertEqual(series.SeriesInstanceUID, images[0].SeriesInstanceUID)
        self.assertEqual({str(ref.ReferencedSOPInstanceUID) for ref in series.ContourImageSequence},
                         set(by_sop))
        roi, = rt.StructureSetROISequence
        self.assertEqual(str(roi.ROIName), roi_name)
        rc, = rt.ROIContourSequence
        self.assertEqual(rc.ReferencedROINumber, roi.ROINumber)
        reopened_mask = np.zeros_like(mask)
        contour_slices = set()
        for contour in rc.ContourSequence:
            ref, = contour.ContourImageSequence
            self.assertEqual(ref.ReferencedSOPClassUID, MRImageStorage)
            k, img = by_sop[str(ref.ReferencedSOPInstanceUID)]
            contour_slices.add(k)
            points = np.asarray(contour.ContourData, dtype=float).reshape(-1, 3)
            self.assertEqual(len(points), int(contour.NumberOfContourPoints))
            delta = points - np.asarray(img.ImagePositionPatient, dtype=float)
            column_axis, row_axis = np.asarray(img.ImageOrientationPatient, dtype=float).reshape(2, 3)
            normal = np.cross(column_axis, row_axis)
            plane_error = float(np.max(np.abs(delta @ normal)))
            self.assertLess(plane_error, .001, "slice %d: off plane by %.5f mm" % (k, plane_error))
            row_mm, column_mm = map(float, img.PixelSpacing)
            pixels = np.column_stack((delta @ column_axis / column_mm, delta @ row_axis / row_mm))
            reopened_mask[k] ^= included_centres(pixels)
        self.assertEqual(contour_slices, set(np.flatnonzero(np.any(mask, axis=(1, 2)))))
        lost, added = np.sum(mask & ~reopened_mask), np.sum(reopened_mask & ~mask)
        self.assertEqual((int(lost), int(added)), (0, 0), "lost/added voxel centres")

    def test_axial(self):
        self.check_series(0, REGULAR, 0)

    def test_coronal(self):
        self.check_series(90, REGULAR, 0)

    def test_oblique_nonuniform_gaps(self):
        self.check_series(32, IRREGULAR, 0)

    def test_oblique_nonuniform_gaps_with_lateral_drift(self):
        # 1.75 mm, above two columns, within the routine's 2 mm tilt tolerance.
        self.check_series(32, IRREGULAR, .35)

    def test_out_of_tolerance_tilt_remains_blocked(self):
        directory = self.base / "mr"
        write_mr(directory, 32, REGULAR, .85)
        path = self.base / "STUDY.dcm"
        with self.assertRaisesRegex(RuntimeError, "gantry inclinado"):
            self.save_selection(directory, path, target_mask(), {})
        self.assertFalse(path.exists())

    def test_unrecoverable_reference_does_not_deliver(self):
        directory = self.base / "mr"
        write_mr(directory, 32, REGULAR, 0)
        source = sorted(directory.glob("*.dcm"))
        previous = pydicom.dcmread(source[1])
        corrupt = pydicom.dcmread(source[2])
        corrupt.SOPInstanceUID = corrupt.file_meta.MediaStorageSOPInstanceUID = previous.SOPInstanceUID
        corrupt.save_as(source[2], enforce_file_format=True)
        path = self.base / "STUDY.dcm"
        with self.assertRaisesRegex((ValueError, RuntimeError), r"SOPInstanceUID duplicado"):
            self.save_selection(directory, path, target_mask(), {})
        self.assertFalse(path.exists())

    def test_missing_image_position_has_geometry_error_and_no_study(self):
        directory = self.base / "mr"
        write_mr(directory, 32, REGULAR, 0)
        path = sorted(directory.glob("*.dcm"))[2]
        invalid = pydicom.dcmread(path)
        del invalid.ImagePositionPatient
        invalid.save_as(path, enforce_file_format=True)
        output = self.base / "STUDY.dcm"
        with self.assertRaisesRegex((ValueError, RuntimeError), r"Geometria DICOM incompleta"):
            self.save_selection(directory, output, target_mask(), {})
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
