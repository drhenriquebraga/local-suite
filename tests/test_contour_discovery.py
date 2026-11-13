"""Manual contour visibility must never serve as AUTO completion evidence."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from test_contour_edit import E,ROOT,make_series
for component in (ROOT/'_montagem'/'componentes').iterdir():
    if (component/'app').is_dir():sys.path.append(str(component/'app'))
import pydicom
from fastapi import FastAPI
import radai_contour_discovery as D
import radai_batch,radai_sets,radai_viewseg,radai_recon3d_screen as R
import radai_thumbnail,radai_watcher,radai_tabela_acervo
import radai_rt,radai_recon3d


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.folder=Path(self.tmp.name)
        self.uid,self.files=make_series(self.folder)
        self.s=E.Session(self.folder,self.uid,self.files)
        self.s.new_roi('Manual_only',[255,0,0]);self.s.mask(1)[2,4:10,8:18]=True
        self.receipt=self.s.save();self.name=self.receipt['basename']
        self.app=FastAPI()
        @self.app.get('/api/recon3d/estado')
        def state(b:str=''):return {'segmentada':False,'conjuntos':[]}
        D.install(self.app)
        self.ticket=radai_thumbnail.bilhete(str(self.folder),self.uid)

    def tearDown(self):self.tmp.cleanup()

    def test_manual_copy_appears_in_both_viewers_but_not_auto_evidence(self):
        self.assertEqual(D.manual_copies(self.folder,self.uid),[self.name])
        cp=radai_viewseg.arquivos_contornados(str(self.folder),self.uid)
        recon=R.arquivos_da_serie(str(self.folder),self.uid)
        for entries in (cp,recon):
            row=next(r for r in entries if r['arquivo']==self.name)
            self.assertFalse(row['entregue']);self.assertFalse(row['plugin'])
        self.assertEqual(radai_batch._rs_da_serie(str(self.folder),self.uid),[])
        self.assertEqual(radai_sets.arquivos_da_serie([self.name],self.uid),[])
        self.assertFalse(radai_watcher._rtstruct_da_serie_em(str(self.folder),self.uid))
        self.assertFalse(radai_watcher.entrega_completa_no_disco(str(self.folder),self.uid))

    def test_recon_picker_archive_and_state_accept_manual_only(self):
        line={};self.assertTrue(R.linha_da_pasta(line,str(self.folder),{'uid':self.uid,'cortes':5}))
        self.assertTrue(line['segmentada']);self.assertTrue(line['contornos_manuais'])
        source={'series':[{'bilhete':self.ticket,'estado':'sem_rs'}],'sumiram':0}
        with patch.object(radai_tabela_acervo,'linhas',return_value=source):
            found=R.acervo('geral')['series']
        self.assertEqual(len(found),1);self.assertTrue(found[0]['contornos_manuais'])
        route=next(r for r in self.app.routes if getattr(r,'path','')=='/api/recon3d/estado')
        state=route.dependant.call(self.ticket)
        self.assertTrue(state['segmentada']);self.assertEqual(state['conjuntos'][0]['arquivo'],self.name)
        self.assertFalse(route.dependant.call('unknown')['segmentada'])

    def test_complete_dicom_identity_is_required_and_invalid_files_are_ignored(self):
        original=pydicom.dcmread(self.folder/self.name)
        for label,change in (('patient',lambda d:setattr(d,'PatientID','Other')),
                             ('study',lambda d:setattr(d,'StudyInstanceUID',pydicom.uid.generate_uid())),
                             ('frame',lambda d:setattr(d.ReferencedFrameOfReferenceSequence[0],'FrameOfReferenceUID',pydicom.uid.generate_uid()))):
            ds=copy.deepcopy(original);change(ds)
            ds.save_as(self.folder/(D.PREFIX+label+'.dcm'),enforce_file_format=True)
        (self.folder/(D.PREFIX+'broken.dcm')).write_bytes(b'not DICOM')
        self.assertEqual(D.manual_copies(self.folder,self.uid),[self.name])
        self.assertEqual(D.manual_copies(self.folder,pydicom.uid.generate_uid()),[])

    def test_install_is_idempotent(self):
        before=(radai_viewseg._rs_da_pasta,R.arquivos_da_serie,R.linha_da_pasta)
        D.install(self.app);D.install(self.app)
        self.assertEqual(before,(radai_viewseg._rs_da_pasta,R.arquivos_da_serie,R.linha_da_pasta))
        self.assertEqual(sum(r['arquivo']==self.name for r in R.arquivos_da_serie(str(self.folder),self.uid)),1)

    def test_classic_source_without_part10_preamble_is_discoverable(self):
        for path in self.files:
            payload=path.read_bytes();self.assertEqual(payload[128:132],b'DICM')
            path.write_bytes(payload[132:])
        self.assertEqual(D.manual_copies(self.folder,self.uid),[self.name])
        found=radai_viewseg.arquivos_contornados(str(self.folder),self.uid)
        self.assertIn(self.name,[row['arquivo'] for row in found])

    def test_header_caches_avoid_repeat_inventory_and_invalidate_changes(self):
        D._SOURCE_CACHE.clear();D._HEADER_CACHE.clear()
        with patch.object(radai_rt,'fatias_da_serie',wraps=radai_rt.fatias_da_serie) as inventory:
            with patch.object(pydicom,'dcmread',wraps=pydicom.dcmread) as reader:
                self.assertEqual(D.manual_copies(self.folder,self.uid),[self.name])
                reads=reader.call_count
                self.assertEqual(D.manual_copies(self.folder,self.uid),[self.name])
                self.assertEqual(reader.call_count,reads)
            self.assertEqual(inventory.call_count,1)
            first=self.files[0];original=first.read_bytes()
            ds=pydicom.dcmread(first);ds.PatientID='Different_source_identity';ds.save_as(first,enforce_file_format=True)
            self.assertEqual(D.manual_copies(self.folder,self.uid),[])
            self.assertEqual(inventory.call_count,2)
            first.write_bytes(original)
            self.assertEqual(D.manual_copies(self.folder,self.uid),[self.name])
            manual=self.folder/self.name;ds=pydicom.dcmread(manual)
            ds.PatientID='Different_manual_identity';ds.save_as(manual,enforce_file_format=True)
            self.assertEqual(D.manual_copies(self.folder,self.uid),[])

    def test_new_copy_is_visible_after_cached_discovery(self):
        self.assertEqual(D.manual_copies(self.folder,self.uid),[self.name])
        second=D.PREFIX+'newly_saved.dcm'
        (self.folder/second).write_bytes((self.folder/self.name).read_bytes())
        self.assertEqual(set(D.manual_copies(self.folder,self.uid)),{self.name,second})

    def test_real_viewers_open_manual_xor_contours_without_changing_dataset(self):
        path=self.folder/self.name;before=path.read_bytes()
        dataset=pydicom.dcmread(path)
        self.assertEqual({str(c.ContourGeometricType) for c in dataset.ROIContourSequence[0].ContourSequence},{'CLOSEDPLANAR_XOR'})
        original_types=[str(c.ContourGeometricType) for c in dataset.ROIContourSequence[0].ContourSequence]
        contours=radai_recon3d.contornos_da_roi(dataset,'Manual_only')
        self.assertTrue(contours)
        self.assertEqual([str(c.ContourGeometricType) for c in dataset.ROIContourSequence[0].ContourSequence],original_types)
        loaded,chosen,_,_=R.conjunto_da_serie(self.ticket,self.name)
        self.assertEqual(chosen,self.name);self.assertTrue(loaded['contornos']['Manual_only'])
        cp=radai_viewseg.contornos_do_corte(str(self.folder),self.uid,self.name,2)
        self.assertTrue(next(r for r in cp['estruturas'] if r['n']=='Manual_only')['d'])
        self.assertEqual(path.read_bytes(),before)
        dataset.StructureSetLabel='OTHER'
        self.assertEqual(radai_recon3d.contornos_da_roi(dataset,'Manual_only'),[])


if __name__=='__main__':unittest.main()
