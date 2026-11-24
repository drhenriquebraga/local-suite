"""Exercise the Bridge conversion and delivery endpoints, then write STUDYs for their outputs."""
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pydicom
from pydicom.uid import generate_uid, MRImageStorage, RLELossless, RTStructureSetStorage

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "app")]
import test_study_mr_planos_dicom as geometry
import engine


def dicoms(directory):
    return sorted((pydicom.dcmread(file) for file in directory.glob("*.dcm")),
                  key=lambda ds: int(ds.InstanceNumber))


class BridgeStudyIdentities(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="qa-mr-bridge-study-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.source = self.base / "source"
        self.destination = self.base / "tps"
        self.destination.mkdir()
        for setting in (patch.object(tempfile, "tempdir", temp.name),
                        patch.dict(os.environ, {"RADAI_TMP": temp.name, "RADAI_REGISTRO_DIR": temp.name,
                                                "LOCALAPPDATA": temp.name, "RADAI_CALIB_DIR": temp.name,
                                                "RADAI_CONFIG": str(self.base / "suite.config")})):
            setting.start()
            self.addCleanup(setting.stop)
        from test_bridge_motor import cliente
        self.client = cliente()

    def post(self, step, body):
        return self.client.post("/api/bridge/" + step, json=body).json()

    def create_series(self):
        study, frame = generate_uid(), generate_uid()
        originals = {}
        for name, compressed in (("T1", True), ("T2", False)):
            folder = self.source / name
            geometry.write_mr(folder, 0 if compressed else 32,
                              geometry.REGULAR if compressed else geometry.IRREGULAR, 0)
            for file in sorted(folder.glob("*.dcm")):
                ds = pydicom.dcmread(file)
                ds.StudyInstanceUID, ds.FrameOfReferenceUID = study, frame
                ds.SeriesDescription = "QA MR " + name
                ds.SeriesNumber = 1 if compressed else 2
                ds.ImageType = ["ORIGINAL", "PRIMARY"]
                if compressed:
                    ds.compress(RLELossless, generate_instance_uid=False)
                ds.save_as(file, enforce_file_format=True)
            originals[name] = dicoms(folder)
        return originals

    def convert(self, directory):
        found = self.post("varrer", {"pasta": str(directory)})
        self.assertNotIn("erro", found)
        tickets = [{"b": series["bilhete"]} for series in found["series"]]
        return found, self.post("etapa/converter", {"pasta": str(directory), "series": tickets})

    def check_study(self, folder, delivered_images, mask, path):
        support = engine.MascaraCompacta.de(mask)
        prepared, names = engine.build_rtstruct(str(folder), {"rectum": mask.copy()}, adiar=True,
            modalidade="MR", exigir_grade=True, suavizar_mm=1.5, perfil_contornos="padrao",
            externo=np.ones(mask.shape, bool), limites_intestinais={"rectum": support},
            sobreposicao_reto_jhu=support)
        try:
            prepared.gravar_selecao({"rectum"}, str(path))
        finally:
            prepared.liberar()
        rt = pydicom.dcmread(path)
        self.assertEqual(rt.SOPClassUID, RTStructureSetStorage)
        self.assertEqual(rt.file_meta.MediaStorageSOPClassUID, rt.SOPClassUID)
        self.assertEqual(rt.file_meta.MediaStorageSOPInstanceUID, rt.SOPInstanceUID)
        self.assertEqual(rt.StructureSetLabel, "RadAI_STUDY")
        expected = {str(d.SOPInstanceUID): (i, d) for i, d in enumerate(delivered_images)}
        first = delivered_images[0]
        self.assertEqual(rt.StudyInstanceUID, first.StudyInstanceUID)
        self.assertEqual(rt.FrameOfReferenceUID, first.FrameOfReferenceUID)
        frame, = rt.ReferencedFrameOfReferenceSequence
        self.assertEqual(frame.FrameOfReferenceUID, first.FrameOfReferenceUID)
        study, = frame.RTReferencedStudySequence
        self.assertEqual(study.ReferencedSOPInstanceUID, first.StudyInstanceUID)
        series, = study.RTReferencedSeriesSequence
        self.assertEqual(series.SeriesInstanceUID, first.SeriesInstanceUID)
        self.assertCountEqual([str(r.ReferencedSOPInstanceUID) for r in series.ContourImageSequence], expected)
        self.assertTrue(all(r.ReferencedSOPClassUID == MRImageStorage for r in series.ContourImageSequence))
        roi, = rt.StructureSetROISequence
        self.assertEqual(roi.ROIName, names["rectum"])
        self.assertEqual(roi.ReferencedFrameOfReferenceUID, first.FrameOfReferenceUID)
        rc, = rt.ROIContourSequence
        self.assertEqual(rc.ReferencedROINumber, roi.ROINumber)
        result = np.zeros_like(mask)
        for ring in rc.ContourSequence:
            ref, = ring.ContourImageSequence
            self.assertEqual(ref.ReferencedSOPClassUID, MRImageStorage)
            k, img = expected[str(ref.ReferencedSOPInstanceUID)]
            world = np.asarray(ring.ContourData, dtype=float).reshape(-1, 3)
            off = world - np.asarray(img.ImagePositionPatient, dtype=float)
            axes = np.asarray(img.ImageOrientationPatient, dtype=float).reshape(2, 3)
            self.assertLess(np.max(np.abs(off @ np.cross(*axes))), .001)
            xy = (off @ axes.T) / np.asarray(img.PixelSpacing[::-1], dtype=float)
            result[k] ^= geometry.included_centres(xy)
        np.testing.assert_array_equal(result, mask)
        return rt

    def test_derived_and_only_decompressed_studies_with_sources(self):
        originals = self.create_series()
        compressed_path = self.source / "T1" / "CT_0002.dcm"
        shutil.copy2(compressed_path, self.source / "T1" / "exact-copy.dcm")
        found, conversion = self.convert(self.source)
        self.assertNotIn("erro", conversion, str(conversion))
        self.assertEqual(conversion["recusadas"], [])
        self.assertEqual(len(conversion["exportadas"]), 2)
        self.assertEqual(sum(s["copias_identicas"] for s in conversion["exportadas"]), 1)
        delivered = self.post("etapa/entregar", {"conversao": conversion["conversao"],
                                                 "destinos": [str(self.destination)]})
        self.assertEqual(delivered.get("falhas"), [], delivered)
        self.assertEqual(len(delivered["series"]), 2)
        src_by_ticket = {s["bilhete"]: s["descricao"] for s in found["series"]}
        mixed = self.base / "review"
        shutil.copytree(self.source / "T2", mixed / "T2-original")
        studies, layers = [], {}
        for row in delivered["series"]:
            folder = Path(row["pasta"])
            self.assertIn(self.destination, folder.parents)
            name = src_by_ticket[row["b"]].split()[-1]
            src, images = originals[name], dicoms(folder)
            self.assertEqual(len(images), 6)
            first = images[0]
            self.assertEqual(first.SeriesInstanceUID, row["uid"])
            source_sops = {str(d.SOPInstanceUID) for d in src}
            target_sops = {str(d.SOPInstanceUID) for d in images}
            self.assertEqual(len(target_sops), 6)
            if name == "T1":
                self.assertTrue(all(d.file_meta.TransferSyntaxUID == RLELossless for d in src))
                self.assertEqual(first.SeriesInstanceUID, src[0].SeriesInstanceUID)
                self.assertEqual(source_sops, target_sops)
            else:
                self.assertNotEqual(first.SeriesInstanceUID, src[0].SeriesInstanceUID)
                self.assertTrue(source_sops.isdisjoint(target_sops))
            for original, output in zip(src, images):
                self.assertFalse(output.file_meta.TransferSyntaxUID.is_compressed)
                self.assertEqual(original.StudyInstanceUID, output.StudyInstanceUID)
                self.assertEqual(original.FrameOfReferenceUID, output.FrameOfReferenceUID)
                self.assertEqual(output.SeriesInstanceUID, first.SeriesInstanceUID)
                self.assertEqual(output.SOPClassUID, MRImageStorage)
                self.assertEqual(output.file_meta.MediaStorageSOPClassUID, output.SOPClassUID)
                self.assertEqual(output.file_meta.MediaStorageSOPInstanceUID, output.SOPInstanceUID)
                np.testing.assert_array_equal(output.pixel_array, original.pixel_array)
                np.testing.assert_allclose(output.ImagePositionPatient, original.ImagePositionPatient)
                np.testing.assert_allclose(output.ImageOrientationPatient, original.ImageOrientationPatient)
                np.testing.assert_allclose(output.PixelSpacing, original.PixelSpacing)
                if name == "T2":
                    self.assertEqual(output.ImageType[0], "DERIVED")
                    self.assertTrue(output.DerivationDescription)
                    self.assertIn(original.SOPInstanceUID, [r.ReferencedSOPInstanceUID for r in output.SourceImageSequence])
                else:
                    self.assertEqual(output.SOPInstanceUID, original.SOPInstanceUID)
                    self.assertEqual(output.ImageType[0], "ORIGINAL")
            shutil.copytree(folder, mixed / (name + "-delivered"), ignore=shutil.ignore_patterns("*.txt", "*.json"))
            studies.append(self.check_study(folder, images, geometry.target_mask(), mixed / (name+"-RS.dcm")))
            layers[name] = target_sops
        # A TPS can ingest the original T2, its derived images, the native T1
        # and the two structure sets in one Study without any object-ID collision.
        objects = list(layers["T1"]) + list(layers["T2"])
        objects += [str(d.SOPInstanceUID) for d in originals["T2"]]
        objects += [str(rt.SOPInstanceUID) for rt in studies]
        self.assertEqual(len(objects), 20)
        self.assertEqual(len(set(objects)), len(objects))
        self.assertEqual(len({str(rt.SeriesInstanceUID) for rt in studies}), 2)
        scanned = self.post("varrer", {"pasta": str(mixed)})
        self.assertNotIn("erro", scanned)
        groups = {entry["uid"]: entry["cortes"] for entry in scanned["series"] if entry["modalidade"] == "MR"}
        # The UI lists short IDs. Verify the full object identities from disk below.
        series_uids = [str(originals["T2"][0].SeriesInstanceUID), *(item["uid"] for item in delivered["series"])]
        self.assertEqual(groups, {uid[-12:]: 6 for uid in series_uids})
        self.assertCountEqual([str(pydicom.dcmread(p, stop_before_pixels=True).SOPInstanceUID)
                               for p in mixed.rglob("*.dcm")], objects)

    def test_different_pixels_with_the_same_sop_block_the_whole_export(self):
        self.create_series()
        same = self.source / "T2" / "CT_0002.dcm"
        bad = pydicom.dcmread(same)
        pixels = bad.pixel_array.copy()
        pixels[0, 0] += 1
        bad.PixelData = pixels.tobytes()
        bad.save_as(same.with_name("conflicting.dcm"), enforce_file_format=True)
        _, refused = self.convert(self.source)
        self.assertIn("Conflito de UID", refused.get("erro", ""), refused)
        self.assertNotIn("conversao", refused)
        self.assertFalse(list(self.destination.iterdir()))


if __name__ == "__main__":
    unittest.main()
