"""Private integration checks. The temporary CT phantom uses synthetic identifiers."""
from pathlib import Path
import os,sys,tempfile,json,hashlib
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'setup/programa/app'))
import pydicom
from pydicom.dataset import FileDataset, Dataset, FileMetaDataset
from pydicom.uid import generate_uid, ExplicitVRLittleEndian, CTImageStorage, RTStructureSetStorage
from fastapi import FastAPI
import radai_rt_importar as I, radai_contour_discovery as D
import radai_config as C, radai_config_transferencia as T
from zipfile import ZipFile

def has(condition, text):
    if not condition:raise AssertionError(text)
    print('ok',text,flush=True)

def dicom(path,sop_class,modality,study,series,frame):
    meta=FileMetaDataset();meta.TransferSyntaxUID=ExplicitVRLittleEndian
    ds=FileDataset(str(path),{},file_meta=meta,preamble=bytes(128))
    ds.SOPClassUID=meta.MediaStorageSOPClassUID=sop_class
    ds.SOPInstanceUID=meta.MediaStorageSOPInstanceUID=generate_uid()
    ds.PatientID='PHANTOM';ds.Modality=modality;ds.StudyInstanceUID=study
    ds.SeriesInstanceUID=series;ds.FrameOfReferenceUID=frame
    ds.is_little_endian=True;ds.is_implicit_VR=False
    return ds

def example():
    return Dataset()

with tempfile.TemporaryDirectory() as temp:
 root=Path(temp)
 cfg=root/'estacao.config'; cfg.write_text('MODO_DEDICADO=1\nDEVICE=cpu\nCPU_THREADS=4\nTPS_DESTINO=eclipse\n',encoding='utf8')
 keys=['CPU_THREADS','MODO_DEDICADO','DEVICE','TPS_DESTINO']; table={'CT':[],'MR':[]}
 original=T.exportar(cfg,keys,'8.28',list(T.SECOES),{'radai_idioma':'pt-BR'})
 has(set(original['secoes'])==set(T.SECOES),'quatro seções')
 has('DEVICE' not in original['secoes']['configuracao'] and original['secoes']['configuracao']['MODO_DEDICADO']=='1','preferência do modo dedicado exportada')
 r=T.salvar({'valores':{'CPU_THREADS':'5'},'aparencia':{}},cfg,keys,{},table,'')
 has(r['ok'] and C.ler_arquivo(cfg)[1]['CPU_THREADS']=='5','salvar configuração')
 before=cfg.read_bytes()
 r=T.salvar({'valores':{'CPU_THREADS':'6'},'protocolo':{}},cfg,keys,{},table,'')
 has(not r['ok'] and cfg.read_bytes()==before,'falha no protocolo não altera o restante')
 args={'dados':original,'aparencia':{'radai_idioma':'zh-CN'}}
 preview=T.transferir(args,cfg,keys,table,'')
 has(preview['ok'] and preview['revisao'],'prévia e revisão')
 C.escrever(cfg,{'CPU_THREADS':'7'})
 try:T.transferir(dict(args,revisao=preview['revisao']),cfg,keys,table,'',True)
 except C.ErroPersonalizacao as err:has(err.status==409,'importação concorrente rejeitada')
 else:raise AssertionError('stale revision')
 preview=T.transferir(args,cfg,keys,table,'')
 out=T.transferir(dict(args,revisao=preview['revisao']),cfg,keys,table,'',True)
 has(out['aparencia']=={'radai_idioma':'pt-BR'} and C.ler_arquivo(cfg)[1]['CPU_THREADS']=='4','importação integral')
 has(T.desfazer(cfg)['aparencia']==args['aparencia'] and C.ler_arquivo(cfg)[1]['CPU_THREADS']=='7','desfazer importação')
 with mock.patch.object(T,'_prefs',wraps=T._prefs):
    try:T.salvar({'valores':{'CPU_THREADS':'9\nPORT=9000'}},cfg,keys,{},table,'')
    except C.ErroPersonalizacao:pass
    else:raise AssertionError('quebra de linha aceita')
 st,ser,frame=(generate_uid() for _ in range(3));ct=dicom(root/'image.dcm',CTImageStorage,'CT',st,ser,frame)
 ct.InstanceNumber=1;ct.ImagePositionPatient=[0,0,0];ct.ImageOrientationPatient=[1,0,0,0,1,0];ct.Rows=ct.Columns=32;ct.save_as(root/'image.dcm',write_like_original=False)
 rs=dicom(root/'arquivo.part',RTStructureSetStorage,'RTSTRUCT',st,generate_uid(),frame);rs.StructureSetLabel='Externo'
 ref=example();ref.FrameOfReferenceUID=frame;rs.ReferencedFrameOfReferenceSequence=[ref]
 studyref=example(); ref.RTReferencedStudySequence=[studyref]
 refseries=example();refseries.SeriesInstanceUID=ser;studyref.RTReferencedSeriesSequence=[refseries]
 img=example();img.ReferencedSOPClassUID=CTImageStorage;img.ReferencedSOPInstanceUID=ct.SOPInstanceUID
 refseries.ContourImageSequence=[img];roi=example();roi.ROINumber=1;roi.ROIName='ROI';roi.ReferencedFrameOfReferenceUID=frame;rs.StructureSetROISequence=[roi]
 item=example();item.ReferencedROINumber=1;c=example();c.NumberOfContourPoints=3;c.ContourGeometricType='CLOSED_PLANAR';c.ContourData=[1,1,0,1,3,0,3,1,0];c.ContourImageSequence=[img];item.ContourSequence=[c];rs.ROIContourSequence=[item]
 tmp=root/'arquivo.part';rs.save_as(tmp,write_like_original=False)
 with mock.patch('radai_rt.fatias_da_serie',return_value=[str(root/'image.dcm')]):
    digest=hashlib.sha256(tmp.read_bytes()).hexdigest();row=I._publicar(tmp,root,ser,digest)
    has(row['arquivo'] in D.manual_copies(root,ser),'RT importado reconhecido pela série')
    D._viewer_functions()
    import radai_viewseg as V,radai_recon3d_screen as R
    has(V._arquivo_rs(str(root),ser,row['arquivo']) and any(r['arquivo']==row['arquivo'] for r in R.arquivos_da_serie(str(root),ser)),'mesmo RT visível em compare e reconstrução')
    img.ReferencedSOPInstanceUID=generate_uid();rs.save_as(tmp,write_like_original=False)
    try:I._validar(tmp,root,ser)
    except ValueError as err:has(str(err)==I.INCOMPATIVEL,'SOP de outra série recusado')
    else:raise AssertionError('SOP errado')
print('PASS',flush=True)
