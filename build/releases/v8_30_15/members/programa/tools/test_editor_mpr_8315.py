"""DICOM round-trip through the editor in CT and oblique coronal MR."""
from pathlib import Path
import tempfile
import unittest
import sys

import numpy as np
import pydicom
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import CTImageStorage, MRImageStorage, ExplicitVRLittleEndian, generate_uid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
from radai_contour_edit import Session
from radai_mpr_geometry import PatientGrid, original_traces


def phantom(directory, modality):
    study, series, frame = [generate_uid() for _ in range(3)]
    angle = 0 if modality == 'CT' else np.deg2rad(78)
    direction = np.array([[1,0,0],[0,np.cos(angle),-np.sin(angle)],[0,np.sin(angle),np.cos(angle)]])
    origin = np.array([11.,-36.,22.])
    instance_class = CTImageStorage if modality == 'CT' else MRImageStorage
    paths = []
    for k in range(12):
        path = directory / f'{k:02}.dcm'
        meta = FileMetaDataset()
        meta.TransferSyntaxUID = ExplicitVRLittleEndian
        meta.MediaStorageSOPClassUID = instance_class
        meta.MediaStorageSOPInstanceUID = generate_uid()
        ds = FileDataset(str(path), {}, file_meta=meta, preamble=bytes(128))
        ds.SOPInstanceUID, ds.SOPClassUID = meta.MediaStorageSOPInstanceUID, instance_class
        ds.SeriesInstanceUID, ds.StudyInstanceUID, ds.FrameOfReferenceUID = series, study, frame
        ds.PatientName = ds.PatientID = 'PHANTOM'
        ds.PatientBirthDate = ds.StudyDate = ds.SeriesDate = '20000101'
        ds.StudyTime = ds.SeriesTime = '120000'
        ds.StudyID, ds.SeriesNumber, ds.InstanceNumber, ds.Modality = '1', 1, k+1, modality
        ds.SeriesDescription = ds.StudyDescription = 'QA'
        ds.PatientSex = ''
        ds.Rows, ds.Columns = 36, 44
        ds.PixelSpacing, ds.SliceThickness = [1.,1.2], 2.
        ds.ImageOrientationPatient = [float(x) for x in direction[:,:2].T.ravel()]
        ds.ImagePositionPatient = list(origin+k*2*direction[:,2])
        ds.SamplesPerPixel, ds.PhotometricInterpretation = 1, 'MONOCHROME2'
        ds.BitsAllocated = ds.BitsStored = 16
        ds.HighBit, ds.PixelRepresentation = 15, 1
        ds.PixelData = np.zeros((36,44),dtype='<i2').tobytes()
        pydicom.dcmwrite(path,ds,write_like_original=False)
        paths.append(path)
    return series, paths


class EditorGeometry(unittest.TestCase):
    def test_ct_and_coronal_mr_write_reopen(self):
        for modality in ('CT','MR'):
            with self.subTest(modality=modality),tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp)
                uid, files = phantom(folder,modality)
                session = Session(folder,uid,files)
                session.new_roi('Proof',[200,170,60])
                for axis,plane in enumerate(['axial','coronal','sagittal']):
                    session.stroke(1,'lps_'+plane,session.display.shape[axis]//2,[[.43,.45],[.55,.55]],5)
                expected = session.mask(1).copy()
                self.assertGreater(expected.sum(),0)
                result = session.save()
                edited = pydicom.dcmread(folder/result['basename'])
                refs={str(d.SOPInstanceUID):d for d in session.geo['headers']}
                for contour in edited.ROIContourSequence[0].ContourSequence:
                    src=refs[str(contour.ContourImageSequence[0].ReferencedSOPInstanceUID)]
                    ij=np.array(src.ImageOrientationPatient).reshape(2,3)
                    distances=(np.array(contour.ContourData).reshape(-1,3)-src.ImagePositionPatient) @ np.cross(*ij)
                    self.assertLess(np.max(np.abs(distances)),.002)
                fresh=Session(folder,uid,files)
                fresh.import_rs(next(iter(fresh.rs_files)))
                np.testing.assert_array_equal(fresh.mask(1),expected)
                self.assertTrue(fresh.state()['rois'][0]['editable'])

    def test_unmodified_physical_points(self):
        grid=PatientGrid((5,12,12),(2.,1.,1.),(0.,0.,0.),np.eye(3))
        ring=np.array([[1.,1.,3.],[4.,1.,3.],[4.,6.,3.],[1.,6.,3.]])
        boundary=original_traces([ring],grid,1,4)
        np.testing.assert_allclose(sorted(boundary['points']),[[1.5/12,3./5],[4.5/12,3./5]])
        self.assertEqual(boundary['polygons'],[])
        empty=original_traces([ring],grid,0,2)
        self.assertEqual(empty['points']+empty['polygons'],[])


if __name__=='__main__':
    unittest.main()
