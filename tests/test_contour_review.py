"""Independent native-grid/export review; synthetic source data only."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pydicom

from test_contour_edit import E, make_series, write_rt


class IndependentReview(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.uid, self.files = make_series(self.folder)
        self.s = E.Session(self.folder, self.uid, self.files)

    def tearDown(self):
        self.tmp.cleanup()

    def test_disconnected_tiny_components_survive_export_roundtrip(self):
        self.s.new_roi('Composite', [255, 0, 0])
        m = self.s.mask(1)
        m[1, 2:8, 2:9] = True
        m[1, 15, 15] = True
        m[2, 18, 12:16] = True
        m[3, 22:25, 22] = True
        expected = m.copy()
        receipt = self.s.save()
        other = E.Session(self.folder, self.uid, self.files)
        other.import_rs(receipt['basename'])
        actual = other.mask(1)
        np.testing.assert_array_equal(actual, expected, err_msg='missing=%s extra=%s' % (np.argwhere(expected & ~actual).tolist(), np.argwhere(actual & ~expected).tolist()))

    def test_holes_border_pixels_and_islands_survive_export(self):
        self.s.new_roi('Ring_and_borders', [255, 0, 0])
        m = self.s.mask(1)
        m[2, 2:20, 2:25] = True
        m[2, 7:14, 7:18] = False
        m[2, 10, 11] = True
        m[2, 0, 0] = True
        m[2, -1, -1] = True
        expected = m.copy()
        receipt = self.s.save()
        other = E.Session(self.folder, self.uid, self.files)
        other.import_rs(receipt['basename'])
        actual = other.mask(1)
        np.testing.assert_array_equal(actual, expected, err_msg='missing=%s extra=%s' % (np.argwhere(expected & ~actual).tolist(), np.argwhere(actual & ~expected).tolist()))

    def test_all_three_brush_planes_match_lps_distance(self):
        for axis, plane in enumerate(('axial', 'coronal', 'sagittal')):
            with self.subTest(plane=plane):
                self.s.new_roi('Physical_' + plane, [200, 0, 0])
                n = max(self.s.rois)
                shape = self.s.geo['volume'].shape
                center = np.array([2, 16, 18])
                idx = int(center[axis])
                axes = [a for a in range(3) if a != axis]
                h, w = np.array(shape)[axes]
                point = [[(center[axes[1]] + .5) / w, (center[axes[0]] + .5) / h]]
                self.s.stroke(n, plane, idx, point, diameter_mm=5)
                zz, yy, xx = np.indices(shape)
                coords = np.stack((zz, yy, xx), axis=-1)
                local_mm = (coords - center) * self.s.geo['spacing']
                lps_mm = local_mm[..., ::-1] @ self.s.geo['direction'].T
                expected = (np.linalg.norm(lps_mm, axis=-1) <= 2.5 + 1e-8) & (coords[..., axis] == idx)
                np.testing.assert_array_equal(self.s.mask(n), expected)

    def test_native_sagittal_and_coronal_export_keep_exact_grid(self):
        for name, x, y in (('sagittal', [0,1,0], [0,0,1]),
                           ('coronal_flipped', [-1,0,0], [0,0,1])):
            with self.subTest(orientation=name):
                x,y=np.asarray(x,float),np.asarray(y,float)
                for k,path in enumerate(self.files):
                    ds=pydicom.dcmread(path)
                    ds.ImageOrientationPatient=np.r_[x,y].tolist()
                    ds.ImagePositionPatient=(np.array([-17.,24.,35.])+np.cross(x,y)*k*2.5).tolist()
                    ds.save_as(path,enforce_file_format=True)
                self.s=E.Session(self.folder,self.uid,self.files)
                self.s.new_roi('Native_'+name,[255,0,0])
                m=self.s.mask(1);m[1:4,2:20,2:25]=True;m[1:4,7:14,7:18]=False;m[2,0,0]=True
                expected=m.copy();receipt=self.s.save()
                other=E.Session(self.folder,self.uid,self.files);other.import_rs(receipt['basename'])
                np.testing.assert_array_equal(other.mask(1),expected)

    def test_monaco_keyholes_preserve_native_mask(self):
        import engine
        self.s.new_roi('Monaco_ring',[255,0,0]);m=self.s.mask(1)
        m[2,2:20,2:25]=True;m[2,7:14,7:18]=False;m[2,10,11]=True;m[2,0,0]=True
        with patch.object(engine,'tps_destino',return_value=engine.TPS_MONACO):
            receipt=self.s.save()
        other=E.Session(self.folder,self.uid,self.files);other.import_rs(receipt['basename'])
        np.testing.assert_array_equal(other.mask(1),m)

    def test_lossy_writer_result_is_rejected_before_publication(self):
        original=E.writer_add_roi
        def shifted(engine,rt,mask,name,color,geometry):
            original(engine,rt,mask,name,color,geometry)
            delta=geometry['direction'][:,0]*geometry['spacing'][-1]
            for c in rt.ds.ROIContourSequence[-1].ContourSequence:
                p=np.asarray(c.ContourData,float).reshape(-1,3)+delta
                engine._gravar_pontos(c,[float(v) for v in p.ravel()])
        self.s.new_roi('Reject_loss',[255,0,0]);m=self.s.mask(1);m[2,5:12,7:18]=True
        original_bytes={p:p.read_bytes() for p in self.files}
        with patch.object(E,'writer_add_roi',shifted):
            with self.assertRaises(E.EditError) as raised:self.s.save()
        self.assertEqual(raised.exception.code,'WRITER_GEOMETRY')
        self.assertFalse(list(self.folder.glob('RS_LOCAL_SUITE_EDIT_*.dcm')))
        self.assertFalse(self.s.saved)
        self.assertTrue(all(p.read_bytes()==data for p,data in original_bytes.items()))

    def test_rename_history_does_not_copy_contours_and_has_action_cap(self):
        path=self.folder/'source.dcm';write_rt(self.s,path)
        self.s.rs_files=self.s._find_rs();self.s.import_rs(path.name)
        original_contours=self.s.rois[1]['contours']
        with patch.object(E,'MAX_HISTORY_ACTIONS',4):
            for i in range(10):self.s.rename(1,'Renamed_%d'%i)
        self.assertEqual(len(self.s.undo_stack),4)
        self.assertTrue(all(isinstance(r[2],str) and isinstance(r[3],str) for r in self.s.undo_stack))
        self.assertIs(self.s.rois[1]['contours'],original_contours)
        self.s.history();self.assertEqual(self.s.rois[1]['name'],'Renamed_8')
        self.s.history(True);self.assertEqual(self.s.rois[1]['name'],'Renamed_9')
        before=list(self.s.undo_stack)
        with patch.object(E,'MAX_MEMORY',0):
            with self.assertRaises(E.EditError):self.s.rename(1,'Must_not_change')
        self.assertEqual(self.s.rois[1]['name'],'Renamed_9')
        self.assertEqual(self.s.undo_stack,before)

    def test_interpolation_preview_counts_toward_memory_limit(self):
        self.s.new_roi('Preview',[255,0,0]);m=self.s.mask(1)
        m[0,3:10,3:10]=True;m[4,5:12,5:12]=True
        self.s.interpolate(1,'axial',0,4)
        used=(self.s.geo['volume'].nbytes+m.nbytes
              +sum(self.s._history_bytes(r) for r in self.s.undo_stack))
        with patch.object(E,'MAX_MEMORY',used+m.nbytes-1):
            with self.assertRaises(E.EditError) as raised:self.s._memory()
        self.assertEqual(raised.exception.code,'RESOURCE_LIMIT')

    def test_large_edit_is_rejected_before_allocating_voxel_indices(self):
        self.s.new_roi('Bounded',[255,0,0]);before=self.s.mask(1)
        after=np.ones_like(before);history=list(self.s.undo_stack)
        with patch.object(E,'MAX_HISTORY',1024), patch.object(E.np,'flatnonzero',side_effect=AssertionError('must count first')):
            with self.assertRaises(E.EditError) as raised:self.s._record(1,before,after)
        self.assertEqual(raised.exception.code,'RESOURCE_LIMIT')
        self.assertFalse(before.any());self.assertEqual(self.s.undo_stack,history)


if __name__ == '__main__':
    unittest.main()
