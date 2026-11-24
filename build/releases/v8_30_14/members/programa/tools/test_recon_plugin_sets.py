"""Regression for DICOM-linked plugin deliveries in the native 3D viewer."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
import pydicom
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
from pydicom.uid import CTImageStorage, ExplicitVRLittleEndian, RTStructureSetStorage, generate_uid
import radai_recon3d_screen as screen
import radai_thumbnail as tickets


def write(path, kind, uid, study, frame, patient):
    meta = FileMetaDataset()
    meta.MediaStorageSOPClassUID = kind
    meta.MediaStorageSOPInstanceUID = generate_uid()
    meta.TransferSyntaxUID = ExplicitVRLittleEndian
    data = FileDataset(str(path), {}, file_meta=meta, preamble=b"\0"*128)
    data.SOPClassUID, data.SOPInstanceUID = kind, meta.MediaStorageSOPInstanceUID
    data.StudyInstanceUID, data.SeriesInstanceUID, data.FrameOfReferenceUID = study, uid, frame
    data.PatientID, data.IssuerOfPatientID = patient, 'TEST'
    data.Modality = 'RTSTRUCT' if kind == RTStructureSetStorage else 'CT'
    return data


def output(path, uid, study, frame, patient, sequence_type='CLOSED_PLANAR'):
    from pydicom.sequence import Sequence
    data=write(path, RTStructureSetStorage, generate_uid(), study, frame, patient)
    r,s,f=Dataset(),Dataset(),Dataset()
    r.SeriesInstanceUID=uid
    s.RTReferencedSeriesSequence=Sequence([r])
    f.FrameOfReferenceUID=frame
    f.RTReferencedStudySequence=Sequence([s])
    data.ReferencedFrameOfReferenceSequence=Sequence([f])
    data.StructureSetLabel='RadAI_NEURO'
    roi=Dataset()
    roi.ROINumber=1
    roi.ROIName="Hippocampus_L_ai"
    roi.ROIDescription="NeuroRT / modelo anatomy_synthseg / classe 17"
    roi.ReferencedFrameOfReferenceUID=frame
    data.StructureSetROISequence=[roi]
    contours=Dataset()
    contours.ReferencedROINumber=1
    contours.ROIDisplayColor=[120,150,210]
    contours.ContourSequence=[]
    for z in (0,1,2):
        c=Dataset()
        c.ContourGeometricType=sequence_type
        c.ContourData=[1,1,z,4,1,z,4,4,z,1,4,z]
        c.NumberOfContourPoints=4
        contours.ContourSequence.append(c)
    data.ROIContourSequence=[contours]
    data.save_as(str(path), enforce_file_format=True)


class PublishedSets(TestCase):
    def test_existing_synthseg_lung_vascular_and_foreign_sibling(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            uid,other,study,frame=[generate_uid() for _ in range(4)]
            source=root/'image.dcm'
            write(source,CTImageStorage,uid,study,frame,'PHANTOM').save_as(str(source),enforce_file_format=True)
            names=['RS_NeuroRT_abc123.dcm','RS_RadAI_NOD_LUNG_abcdef.dcm',
                   'RS_RadAI_ITV4D_ab.dcm','RS_Vascular_Manual.dcm']
            for name in names: output(root/name,uid,study,frame,'PHANTOM')
            output(root/names[-1],uid,study,frame,'PHANTOM','CLOSEDPLANAR_XOR')
            for n,id_,fr,who in [('other',other,frame,'PHANTOM'),('frame',uid,generate_uid(),'PHANTOM'),('patient',uid,frame,'OTHER')]:
                output(root/('RS_NeuroRT_'+n+'.dcm'),id_,study,fr,who)
            with patch('radai_rt.fatias_da_serie',return_value=[str(source)]):
                b=tickets.bilhete(tmp,uid)
                rows=screen.arquivos_da_serie(tmp,uid)
                self.assertEqual({r['arquivo'] for r in rows},set(names))
                self.assertIn('SynthSeg',next(r['nome'] for r in rows if r['arquivo']==names[0]))
                out=screen.estruturas_da_serie(b,names[0])
                self.assertEqual([r['nome'] for r in out['estruturas']],['Hippocampus_L_ai'])
                self.assertGreater(len(screen.malha_stl(b,names[0],'Hippocampus_L_ai')),84)
                self.assertGreater(len(screen.malha_stl(b,names[-1],'Hippocampus_L_ai')),84)
                with patch('radai_tabela_acervo.linhas',return_value={
                            'series':[{'estado':'sem_rs','bilhete':b}]}):
                    self.assertEqual(screen.acervo('neuro')['series'][0]['estado'],'ok')
                self.assertNotEqual(screen.estruturas_da_serie(b,'RS_NeuroRT_other.dcm').get('erro'),'')
                import radai_sets
                self.assertEqual(radai_sets.arquivos_da_serie(names,uid),[])
if __name__ == '__main__':
    main()

