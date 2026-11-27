"""Regressão de anéis internos nos RTSTRUCTs da suíte e importados."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

import numpy as np
import pydicom
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
from pydicom.uid import CTImageStorage, ExplicitVRLittleEndian, generate_uid
from radai_contour_edit import Session, EditError
from rt_utils import RTStructBuilder


def slice_file(path, k, study, series, frame):
    meta = FileMetaDataset()
    meta.MediaStorageSOPClassUID = CTImageStorage
    meta.MediaStorageSOPInstanceUID = generate_uid()
    meta.TransferSyntaxUID = ExplicitVRLittleEndian
    ds = FileDataset(str(path), {}, file_meta=meta, preamble=bytes(128))
    ds.SOPClassUID, ds.SOPInstanceUID = CTImageStorage, meta.MediaStorageSOPInstanceUID
    ds.SeriesInstanceUID, ds.StudyInstanceUID, ds.FrameOfReferenceUID = series, study, frame
    ds.PatientName, ds.PatientID, ds.Modality = "Editor^Phantom", "SYNTH", "CT"
    ds.SeriesNumber = 1
    ds.StudyDate = ds.SeriesDate = "20000101"
    ds.StudyTime = ds.SeriesTime = "120000"
    ds.StudyID = "1"
    ds.InstanceNumber, ds.ImagePositionPatient = k+1, [0, 0, k]
    ds.ImageOrientationPatient, ds.PixelSpacing = [1,0,0,0,1,0], [1,1]
    ds.Rows = ds.Columns = 32
    ds.SliceThickness = ds.SamplesPerPixel = 1
    ds.BitsAllocated = ds.BitsStored = 16
    ds.HighBit, ds.PixelRepresentation, ds.PhotometricInterpretation = 15, 0, "MONOCHROME2"
    ds.PixelData = np.zeros((32,32), dtype="<u2").tobytes()
    ds.is_little_endian = True
    ds.is_implicit_VR = False
    ds.save_as(path, write_like_original=False)


def fixture(root, suite):
    study, series, frame = [generate_uid() for _ in range(3)]
    files = [root / ("CT-%d.dcm" % k) for k in range(5)]
    for k,path in enumerate(files):
        slice_file(path,k,study,series,frame)
    rt = RTStructBuilder.create_new(dicom_series_path=str(root))
    mask = np.zeros((32,32,5),bool)
    mask[2:28,2:28,1:4] = True
    rt.add_roi(mask=mask, name="Ring", color=[32,240,80])
    rt.add_roi(mask=mask, name="Another", color=[240,120,80])
    ds = rt.ds
    ds.Manufacturer = "Radioterapia.AI" if suite else "External"
    ds.ManufacturerModelName = "RadAI motor" if suite else "External"
    for i,roi in enumerate(ds.ROIContourSequence):
        original = list(roi.ContourSequence)
        roi.ContourSequence = []
        for c in original:
            k=float(c.ContourData[2])
            for lo,hi in ([(3,27),(10,19)] if i==0 else [(5,7)]):
                d=Dataset(); d.ContourGeometricType="CLOSED_PLANAR"
                d.ContourData=[v for x,y in ((lo,lo),(hi,lo),(hi,hi),(lo,hi)) for v in (x,y,k)]
                d.NumberOfContourPoints=4; d.ContourImageSequence=c.ContourImageSequence
                roi.ContourSequence.append(d)
    target = root/"RS.dcm"
    ds.save_as(target, write_like_original=False)
    s=Session(root,series,files)
    s.import_rs(next(iter(s.rs_files)))
    return s,target


class Rings(unittest.TestCase):
    def test_suite_hole_and_edits(self):
        with tempfile.TemporaryDirectory() as tmp:
            s,p=fixture(Path(tmp),True); before=p.read_bytes()
            m=s.mask(1)
            self.assertTrue(m[2,5,5]); self.assertFalse(m[2,14,14])
            for plane in ("axial","sagittal","coronal"):
                layer=s.overlay(1,"lps_"+plane,2 if plane=="axial" else 15)
                self.assertTrue(layer["polygons"])
            self.assertEqual(len(s.overlay(1,"lps_axial",2)["polygons"]),2)
            s.stroke(1,"lps_axial",2,[[.45,.45]],2,"brush")
            self.assertTrue(s.mask(1)[2,14,14]); self.assertFalse(s.mask(1)[1,14,14])
            receipt=s.save(); exported=pydicom.dcmread(s.saved[receipt["download_url"].split("file=")[-1]])
            self.assertEqual(p.read_bytes(),before)
            self.assertEqual(exported.ROIContourSequence[0 if exported.ROIContourSequence[0].ReferencedROINumber==2 else 1],s.original.ROIContourSequence[1])
            modified=next(r for r in exported.ROIContourSequence if int(r.ReferencedROINumber)==1)
            self.assertEqual({c.ContourGeometricType for c in modified.ContourSequence},{"CLOSEDPLANAR_XOR"})

    def test_unattributed_nested_contour_preserved_and_visible(self):
        with tempfile.TemporaryDirectory() as tmp:
            s,p=fixture(Path(tmp),False); before=p.read_bytes()
            from radai_contour_scene import scene
            first_scene=scene(s,rois=[1])
            self.assertTrue(first_scene['meshes'][0]['lines'])
            self.assertFalse(first_scene['meshes'][0]['faces'])
            axial=s.overlay(1,"lps_axial",2)
            self.assertEqual(len(axial["polygons"]),2)
            self.assertTrue(s.overlay(1,"lps_sagittal",15)["points"])
            self.assertTrue(s.overlay(1,"lps_coronal",15)["points"])
            self.assertFalse(s.rois[1]["editable"])
            with self.assertRaises(EditError):
                s.stroke(1,"lps_axial",2,[[.45,.45]],2,"brush")
            s.rename(2,"Renamed")
            receipt=s.save(); exported=pydicom.dcmread(s.saved[receipt["download_url"].split("file=")[-1]])
            self.assertEqual(s.original.ROIContourSequence,exported.ROIContourSequence)
            self.assertEqual(p.read_bytes(),before)
            self.assertRaises(EditError,s.import_rs,"")
            cleared=s.import_rs("",discard=True)
            self.assertEqual(cleared["rois"],[])
            self.assertEqual(cleared["source_rtstruct"],"")
            self.assertFalse(s.prepared or s.mesh_cache or s.undo_stack)
            self.assertEqual(len(s.import_rs(next(iter(s.rs_files)))["rois"]),2)


if __name__ == "__main__":
    unittest.main()

