"""Native-grid regression for automatic anchors, identity, centroid and 3D."""
import tempfile
import json
import time
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
from test_contour_edit import E, make_series


class EditorV824(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.folder=Path(self.temp.name)
        uid,files=make_series(self.folder,shape=(13,32,36))
        self.s=E.Session(self.folder,uid,files); self.s.new_roi('Target',[255,30,40])
    def tearDown(self):self.temp.cleanup()

    def test_automatic_piecewise_anchors_preview_and_explicit_apply(self):
        for k,x in ((1,.3),(4,.4),(8,.55),(11,.6)):
            self.s.stroke(1,'axial',k,[[x,.5]],diameter_mm=4)
        original=self.s.mask(1).copy()
        preview=self.s.interpolate(1,'axial')
        self.assertEqual(preview['anchors'],[1,4,8,11])
        self.assertEqual(preview['intervals'],[[1,4],[4,8],[8,11]])
        np.testing.assert_array_equal(self.s.mask(1),original)
        self.s.interpolate(1,apply=True,preview_id=preview['preview_id'])
        for k in (1,4,8,11):np.testing.assert_array_equal(self.s.mask(1)[k],original[k])
        for k in (2,3,5,6,7,9,10):self.assertTrue(self.s.mask(1)[k].any())
        self.assertFalse(self.s.mask(1)[0].any());self.assertFalse(self.s.mask(1)[12].any())

    def test_identity_centroid_and_mesh_keep_oblique_patient_coordinates(self):
        self.s.stroke(1,'axial',2,[[.5,.5]],diameter_mm=3)
        state=self.s.state();self.assertEqual(state['identity']['patient_id'],'SYNTHETIC')
        self.assertEqual(state['identity']['patient_name'],'Synthetic^Editor')
        center=self.s.center(1)
        indices=np.array(np.where(self.s.mask(1))).mean(axis=1)
        np.testing.assert_allclose(center['indices_zyx'],indices)
        expected=self.s.geo['origin']+self.s.geo['direction']@(indices[::-1]*np.array(self.s.geo['spacing'][::-1]))
        np.testing.assert_allclose(center['center_lps'],expected)
        scene=self.s.scene();mesh=scene['meshes'][0]
        self.assertEqual(scene['session'],self.s.id);self.assertEqual(mesh['roi'],1)
        self.assertEqual(mesh['coordinate_system'],'LPS_mm')
        self.assertGreater(len(mesh['faces']),0)
        self.assertGreater(np.ptp(np.array(mesh['vertices'])[:,2]),0)

    def test_automatic_preview_does_not_replace_cross_plane_manual_edits(self):
        self.s.stroke(1,'axial',1,[[.4,.4]],diameter_mm=5)
        self.s.stroke(1,'axial',11,[[.5,.5]],diameter_mm=5)
        self.s.stroke(1,'coronal',20,[[.8,.5]],diameter_mm=4)
        protected=self.s.mask(1)[:,20,:].copy()
        preview=self.s.interpolate(1,'axial')
        self.s.interpolate(1,apply=True,preview_id=preview['preview_id'])
        np.testing.assert_array_equal(self.s.mask(1)[:,20,:],protected)

    def test_scene_cache_is_per_roi_and_rename_is_metadata_only(self):
        self.s.stroke(1,'axial',2,[[.5,.5]],diameter_mm=3)
        self.s.new_roi('Second',[0,50,255]);self.s.stroke(2,'axial',3,[[.3,.3]],diameter_mm=4)
        self.s.scene();second=self.s.mesh_cache[2];first=self.s.mesh_cache[1]
        self.s.stroke(1,'axial',4,[[.5,.5]],diameter_mm=3)
        self.assertIs(self.s.mesh_cache[2],second);self.assertNotIn(1,self.s.mesh_cache)
        self.s.scene();first=self.s.mesh_cache[1]
        self.s.rename(1,'Renamed');self.assertIs(self.s.mesh_cache[1],first)
        scene=self.s.scene();self.assertEqual(scene['meshes'][0]['name'],'Renamed')
        self.s.history();self.assertIs(self.s.mesh_cache[1],first)
        self.assertEqual(self.s.scene()['meshes'][0]['name'],'Target')

    def test_scene_limits_do_not_change_masks_or_hide_skipped_rois(self):
        from radai_contour_scene import scene
        self.s.stroke(1,'axial',2,[[.5,.5]],diameter_mm=3);original=self.s.mask(1).copy()
        with patch('radai_contour_scene.MAX_CROP_VOXELS',1):result=scene(self.s)
        self.assertEqual(result['meshes'],[]);self.assertEqual(result['skipped'],[{'roi':1,'reason':'RESOURCE_LIMIT'}])
        np.testing.assert_array_equal(self.s.mask(1),original)

    def test_all_editor_languages_include_new_workflow_and_errors(self):
        from radai_contour_edit_i18n import TEXT,ERRORS,LANGUAGES,_EDITOR_824
        for values in _EDITOR_824.values():self.assertEqual(len(values),len(LANGUAGES))
        expected=set(TEXT['en'])
        for language in LANGUAGES:
            self.assertEqual(set(TEXT[language]),expected)
            self.assertTrue(all(TEXT[language].values()))
            self.assertTrue(ERRORS['EMPTY_STRUCTURE'][language]);self.assertTrue(ERRORS['INVALID_INTERVAL'][language])

    def test_scene_delta_transfers_only_modified_geometry(self):
        for i in range(1,13):
            if i>1:self.s.new_roi('ROI_%s'%i,[10*i,30,150])
            for k in range(2,10):self.s.stroke(i,'axial',k,[[.2+i*.035,.5]],diameter_mm=6)
        before=time.perf_counter();full=self.s.scene();cold=time.perf_counter()-before
        known={str(m['roi']):m['geometry_revision'] for m in full['meshes']}
        self.s.stroke(1,'axial',10,[[.2,.5]],diameter_mm=6)
        before=time.perf_counter();delta=self.s.scene(known);warm=time.perf_counter()-before
        self.assertEqual(len(delta['meshes']),12)
        self.assertEqual([m['roi'] for m in delta['meshes'] if not m.get('unchanged')],[1])
        full_bytes=len(json.dumps(full));delta_bytes=len(json.dumps(delta))
        self.assertLess(delta_bytes,full_bytes*.2)
        print('3D 12 ROIs: full=%s bytes, delta=%s bytes; cold=%.3fs, edit=%.3fs'%(full_bytes,delta_bytes,cold,warm))


if __name__=='__main__':unittest.main()
