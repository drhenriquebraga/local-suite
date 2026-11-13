"""Synthetic DICOM regression; no patient data and no segmentation models."""
import copy
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'app'))
CONTOUR=Path(os.environ.get('RADAI_CONTOUR_APP',str(ROOT.parent/'radai-contourlab-release-v817'/'app')))
sys.path.insert(1,str(CONTOUR))
import numpy as np
import pydicom
from pydicom.dataset import FileDataset,FileMetaDataset,Dataset
from pydicom.sequence import Sequence
from pydicom.uid import generate_uid,ExplicitVRLittleEndian,CTImageStorage,MRImageStorage
import radai_contour_edit as E


def make_series(folder,oblique=True,modality='CT',shape=(5,32,36)):
    uid,study,frame=generate_uid(),generate_uid(),generate_uid()
    theta=.38 if oblique else 0
    x=np.array([np.cos(theta),0,np.sin(theta)]); y=np.array([0.,1.,0.]); z=np.cross(x,y)
    origin=np.array([-17.,24.,35.]); paths=[]
    for k in range(shape[0]):
        path=Path(folder)/('image_%02d.dcm'%k)
        meta=FileMetaDataset();meta.TransferSyntaxUID=ExplicitVRLittleEndian
        meta.MediaStorageSOPClassUID=CTImageStorage if modality=='CT' else MRImageStorage
        meta.MediaStorageSOPInstanceUID=generate_uid()
        ds=FileDataset(str(path),{},file_meta=meta,preamble=b'\0'*128)
        ds.SOPClassUID=meta.MediaStorageSOPClassUID;ds.SOPInstanceUID=meta.MediaStorageSOPInstanceUID
        ds.Modality=modality;ds.SeriesInstanceUID=uid;ds.StudyInstanceUID=study;ds.FrameOfReferenceUID=frame
        ds.PatientName='Synthetic^Editor';ds.PatientID='SYNTHETIC';ds.StudyDate='20261113';ds.StudyTime='120000';ds.StudyID='1'
        ds.SeriesNumber=1;ds.InstanceNumber=k+1;ds.Rows=shape[1];ds.Columns=shape[2]
        ds.ImagePositionPatient=(origin+z*k*2.5).tolist();ds.ImageOrientationPatient=np.r_[x,y].tolist()
        ds.PixelSpacing=[1.2,.6];ds.SliceThickness=2.5
        ds.SamplesPerPixel=1;ds.PhotometricInterpretation='MONOCHROME2'
        ds.BitsAllocated=16;ds.BitsStored=16;ds.HighBit=15;ds.PixelRepresentation=1
        ds.PixelData=np.full(shape[1:],k*20,dtype=np.int16).tobytes()
        ds.RescaleSlope=1;ds.RescaleIntercept=-100
        ds.save_as(str(path),enforce_file_format=True);paths.append(path)
    return uid,paths


def write_rt(session,path):
    import engine
    from rt_utils import RTStructBuilder
    rt=RTStructBuilder.create_new(dicom_series_path=str(session.folder))
    m=np.zeros(session.geo['volume'].shape,bool);m[1:4,5:19,6:24]=True;m[1:4,9:14,11:17]=False
    other=np.zeros_like(m);other[2,22:27,25:31]=True
    for mask,name in ((m,'Original_ring'),(other,'Untouched')):
        E.writer_add_roi(engine,rt,mask,name,[10,20,240],session.geo)
    for rc in rt.ds.ROIContourSequence:
        for c in rc.ContourSequence:c.ContourGeometricType='CLOSEDPLANAR_XOR'
    rt.ds.ApprovalStatus='APPROVED';rt.ds.ReviewerName='Original^Reviewer'
    rt.ds.save_as(str(path),enforce_file_format=True)
    return m


class GeometryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.folder=Path(self.tmp.name)
        self.uid,self.files=make_series(self.folder)
        self.s=E.Session(self.folder,self.uid,self.files)
    def tearDown(self):self.tmp.cleanup()

    def test_oblique_anisotropic_grid_is_original(self):
        g=self.s.geo
        self.assertEqual(g['volume'].shape,(5,32,36))
        np.testing.assert_allclose(g['spacing'],[2.5,1.2,.6])
        self.assertAlmostEqual(g['direction'][2,0],np.sin(.38))
        self.assertEqual(g['volume'][4,10,10],-20)
        self.assertTrue(self.s.image('coronal',9).startswith(b'\x89PNG'))

    def test_irregular_or_enhanced_rejected(self):
        ds=pydicom.dcmread(self.files[2]);ds.ImagePositionPatient=[float(v)+.2 for v in ds.ImagePositionPatient];ds.save_as(self.files[2])
        with self.assertRaisesRegex(E.EditError,'irregulares'):E.load_geometry(self.files,self.uid)
        ds.NumberOfFrames=2;ds.save_as(self.files[2])
        with self.assertRaisesRegex(E.EditError,'Enhanced'):E.load_geometry(self.files,self.uid)

    def test_physical_brush_undo_redo_and_stale(self):
        self.s.new_roi('Manual',[255,0,0]);n=1
        self.s.stroke(n,'axial',2,[[(18.5)/36,(16.5)/32]],diameter_mm=4.8)
        m=self.s.mask(n);yy,xx=np.where(m[2]);self.assertGreater(np.ptp(xx),np.ptp(yy))
        before=m.copy();self.s.history();self.assertFalse(m.any());self.s.history(True);np.testing.assert_array_equal(m,before)
        with self.assertRaises(E.EditError):self.s.check(self.s.csrf,self.s.revision-1)
        with self.assertRaises(E.EditError):self.s.check('wrong',self.s.revision)

    def test_xor_hole_import_and_invalid_reference(self):
        path=self.folder/'source.dcm';write_rt(self.s,path)
        self.s.rs_files=self.s._find_rs();self.s.import_rs(path.name)
        m=self.s.mask(1)
        self.assertFalse(m[2,11,13]);self.assertTrue(m[2,6,7]);self.assertEqual(m.shape,(5,32,36))
        self.assertTrue(self.s.overlay(1,'axial',2)['polygons'])
        ds=copy.deepcopy(self.s.original);ds.ROIContourSequence[0].ContourSequence[0].ContourImageSequence[0].ReferencedSOPInstanceUID=generate_uid()
        self.s.rois[1]['contours']=ds.ROIContourSequence[0];self.s.masks.clear()
        with self.assertRaisesRegex(E.EditError,'referência'):self.s.mask(1)

    def test_interpolation_preview_is_revision_bound_and_explicit(self):
        self.s.new_roi('Target',[1,2,3]);m=self.s.mask(1);m[0,5:10,5:10]=True;m[4,7:12,7:12]=True
        preview=self.s.interpolate(1,'axial',0,4)
        self.assertFalse(m[2].any());self.assertTrue(self.s.overlay(1,'axial',2,preview['preview_id'])['polygons'])
        self.s.interpolate(1,apply=True,preview_id=preview['preview_id']);self.assertTrue(m[2].any())
        with self.assertRaises(E.EditError):self.s.interpolate(1,apply=True,preview_id=preview['preview_id'])
        self.s.history();self.assertFalse(m[2].any())

    def test_save_preserves_original_and_unedited_roi(self):
        path=self.folder/'source.dcm';write_rt(self.s,path)
        original=path.read_bytes();self.s.rs_files=self.s._find_rs();self.s.import_rs(path.name)
        unchanged={seq:copy.deepcopy(next(r for r in self.s.original[seq].value if int(getattr(r,'ROINumber' if seq=='StructureSetROISequence' else 'ReferencedROINumber'))==2)) for seq in ('StructureSetROISequence','ROIContourSequence','RTROIObservationsSequence')}
        self.s.stroke(1,'axial',2,[[.15,.10]],diameter_mm=2)
        receipt=self.s.save();output=self.folder/receipt['basename']
        self.assertEqual(path.read_bytes(),original);self.assertTrue(output.is_file());self.assertFalse(receipt['fallback'])
        ds=pydicom.dcmread(output)
        self.assertEqual(ds.ApprovalStatus,'UNAPPROVED');self.assertNotIn('ReviewerName',ds)
        self.assertNotEqual(ds.SOPInstanceUID,self.s.original.SOPInstanceUID)
        self.assertNotEqual(ds.SeriesInstanceUID,self.s.original.SeriesInstanceUID)
        for seq,old in unchanged.items():
            new=next(r for r in ds[seq].value if int(getattr(r,'ROINumber' if seq=='StructureSetROISequence' else 'ReferencedROINumber'))==2)
            self.assertEqual(new,old,seq)
        other=E.Session(self.folder,self.uid,self.files);other.import_rs(receipt['basename']);m=other.mask(1)
        self.assertFalse(m[2,11,13]);self.assertTrue(m[2,6,7])
        for rc in ds.ROIContourSequence:
            for c in rc.ContourSequence:
                pts=np.asarray(c.ContourData,float).reshape(-1,3)
                local=(pts-self.s.geo['origin'])@self.s.geo['direction']/np.array(self.s.geo['spacing'][::-1])
                self.assertLess(np.max(np.abs(local[:,2]-np.round(local[:,2]))),.001)

    def test_readonly_source_fallback_and_source_changed(self):
        self.s.new_roi('Target',[255,0,0]);self.s.stroke(1,'axial',2,[[.5,.5]],diameter_mm=5)
        before=self.s.source_signatures[str(self.files[0])]
        self.s.source_signatures[str(self.files[0])]=(0,0)
        with self.assertRaisesRegex(E.EditError,'mudou'):self.s.save()
        self.s.source_signatures[str(self.files[0])]=before
        real_open=Path.open
        def guarded(path,*args,**kwargs):
            if path.parent==self.folder and args and args[0]=='xb':raise PermissionError('readonly')
            return real_open(path,*args,**kwargs)
        with patch.object(Path,'open',guarded):receipt=self.s.save()
        self.assertTrue(receipt['fallback']);self.assertTrue(self.s.saved[next(iter(self.s.saved))].is_file())

    def test_publication_is_atomic_and_rechecks_sources(self):
        stage=self.folder/'writer-output.bin';stage.write_bytes(b'synthetic dicom bytes')
        destination=self.folder/'new-copy.dcm'
        copy_fn=E.shutil.copyfileobj
        def interrupt(source,target):
            target.write(b'partial')
            self.assertFalse(destination.exists())
            raise OSError('synthetic interruption')
        with patch.object(E.shutil,'copyfileobj',interrupt):
            with self.assertRaises(OSError):self.s._publish_copy(stage,destination)
        self.assertFalse(destination.exists());self.assertFalse(list(self.folder.glob('*.part')))
        def changed(source,target):
            copy_fn(source,target)
            self.s.source_signatures[str(self.files[0])]=(0,0)
        with patch.object(E.shutil,'copyfileobj',changed):
            with self.assertRaises(E.EditError):self.s._publish_copy(stage,destination)
        self.assertFalse(destination.exists());self.assertFalse(list(self.folder.glob('*.part')))

    def test_import_does_not_interpolate_missing_planes(self):
        path=self.folder/'source.dcm';write_rt(self.s,path)
        ds=pydicom.dcmread(path);rc=ds.ROIContourSequence[0]
        sop=str(self.s.geo['headers'][2].SOPInstanceUID)
        rc.ContourSequence=Sequence(c for c in rc.ContourSequence if str(c.ContourImageSequence[0].ReferencedSOPInstanceUID)!=sop)
        ds.save_as(path);self.s.rs_files=self.s._find_rs();self.s.import_rs(path.name)
        self.assertFalse(self.s.mask(1)[2].any())

    def test_single_voxel_export_and_manual_anchor_preserved(self):
        self.s.new_roi('One voxel',[255,0,0]);m=self.s.mask(1);m[2,10,11]=True
        receipt=self.s.save();ds=pydicom.dcmread(self.folder/receipt['basename'])
        c=ds.ROIContourSequence[0].ContourSequence[0]
        self.assertGreaterEqual(int(c.NumberOfContourPoints),3)
        p=np.asarray(c.ContourData,float).reshape(-1,3)
        local=(p-self.s.geo['origin'])@self.s.geo['direction']/np.array(self.s.geo['spacing'][::-1])
        self.assertTrue(np.allclose(local[:,2],2,atol=.001))
        m[:]=False;m[0,3:9,3:9]=True;m[4,6:12,6:12]=True
        self.s.stroke(1,'axial',2,[[(25.5)/36,(25.5)/32]],diameter_mm=2)
        manual=m[2].copy();p=self.s.interpolate(1,'axial',0,4)
        self.s.interpolate(1,apply=True,preview_id=p['preview_id'])
        np.testing.assert_array_equal(m[2],manual)

    def test_rename_undo_and_preserves_contour_data(self):
        path=self.folder/'source.dcm';write_rt(self.s,path)
        self.s.rs_files=self.s._find_rs();self.s.import_rs(path.name)
        original=copy.deepcopy(self.s.original.ROIContourSequence)
        self.s.rename(1,'Renamed');self.s.history();self.assertEqual(self.s.rois[1]['name'],'Original_ring')
        self.s.history(True);self.assertEqual(self.s.rois[1]['name'],'Renamed')
        receipt=self.s.save();ds=pydicom.dcmread(self.folder/receipt['basename'])
        self.assertEqual(ds.ROIContourSequence,original)
        self.assertEqual(ds.StructureSetROISequence[0].ROIName,'Renamed')

    def test_new_roi_undo_redo(self):
        self.s.new_roi('New',[1,2,3]);self.s.history();self.assertFalse(self.s.rois)
        self.s.history(True);self.assertEqual(self.s.rois[1]['name'],'New')

    def test_ambiguous_legacy_holes_are_not_silently_filled(self):
        path=self.folder/'source.dcm';write_rt(self.s,path)
        ds=pydicom.dcmread(path)
        for c in ds.ROIContourSequence[0].ContourSequence:c.ContourGeometricType='CLOSED_PLANAR'
        ds.save_as(path);self.s.rs_files=self.s._find_rs();self.s.import_rs(path.name)
        with self.assertRaisesRegex(E.EditError,'XOR'):self.s.mask(1)


if __name__=='__main__':unittest.main()
