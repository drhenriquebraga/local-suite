"""Contrato do writer e regressões de seleção, arquivos vazios e cache."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import generate_uid, CTImageStorage, ExplicitVRLittleEndian
import pydicom

APP=Path(__file__).resolve().parents[1]/"setup"/"programa"/"app"
sys.path.insert(0,str(APP))
import radai_geom as geom
import radai_output as output
import engine
import radai_sets


def serie_sintetica(stage,shape):
    study,serie,frame=(generate_uid() for _ in range(3))
    z,y,x=np.indices(shape)
    vol=np.where((x-24)**2+(y-24)**2<20**2,60,-1000).astype(np.int16)
    for i,sl in enumerate(vol):
        sop=generate_uid()
        f=FileMetaDataset()
        f.MediaStorageSOPClassUID=CTImageStorage
        f.MediaStorageSOPInstanceUID=sop
        f.TransferSyntaxUID=ExplicitVRLittleEndian
        ds=FileDataset("",{},file_meta=f,preamble=bytes(128))
        ds.SOPClassUID,ds.SOPInstanceUID=CTImageStorage,sop
        ds.StudyInstanceUID,ds.SeriesInstanceUID,ds.FrameOfReferenceUID=study,serie,frame
        ds.PatientName,ds.PatientID="Fantoma^Teste","SYNTH-828"
        ds.StudyDate,ds.StudyTime,ds.StudyID="20261120","120000","1"
        ds.SeriesNumber,ds.Modality,ds.InstanceNumber=1,"CT",i+1
        ds.ImageOrientationPatient=[1,0,0,0,1,0]
        ds.ImagePositionPatient=[0,0,i*2]
        ds.PixelSpacing=[1,1]
        ds.SliceThickness=ds.SpacingBetweenSlices=2
        ds.Rows,ds.Columns=sl.shape
        ds.SamplesPerPixel,ds.PhotometricInterpretation=1,"MONOCHROME2"
        ds.BitsAllocated=ds.BitsStored=16
        ds.HighBit,ds.PixelRepresentation=15,1
        ds.RescaleIntercept,ds.RescaleSlope=0,1
        ds.PixelData=sl.tobytes()
        ds.save_as(stage/("%03d.dcm"%i),write_like_original=False)
    return vol


class Motor828(unittest.TestCase):
    def test_taubin(self):
        rng=np.random.default_rng(82)
        for n in (3,8,12,16,33,66,423,2001):
            p=rng.uniform(-275,275,(n,2))
            if n>=8:
                np.testing.assert_allclose(geom.suavizar_poligono(p),geom.suavizar_anel_de_entrega(p),atol=5e-12,rtol=1e-13)
        t=np.arange(512)*(2*np.pi/512)
        q=np.column_stack([40*np.cos(t),30*np.sin(t)])
        self.assertLessEqual(len(geom.reduzir_vertices_do_anel(q)),258)
        self.assertLessEqual(len(geom.reduzir_vertices_do_anel(q,.25,2)),132)

    def test_subtracao_vascular_preserva_espiculas_dos_operandos(self):
        from pydicom.dataset import Dataset
        t=np.arange(128)*(2*np.pi/128)
        pontos=np.column_stack((40*np.cos(t),30*np.sin(t),np.zeros(128)))
        def anel(perfil,integros):
            c=Dataset()
            c.ContourData=pontos.ravel().tolist()
            c.NumberOfContourPoints=len(pontos)
            rc=Dataset()
            rc.ReferencedROINumber=7
            rc.ContourSequence=[c]
            ds=Dataset()
            ds.ROIContourSequence=[rc]
            self.assertEqual(engine._suavizar_contornos(ds,(1.,1.),perfil=perfil,integros=integros),1)
            return np.asarray(c.ContourData)
        ref=anel(None,())
        for perfil in ("padrao","fast"):
            np.testing.assert_array_equal(ref,anel(perfil,{7}))
            self.assertLess(anel(perfil,()).size,ref.size)

    def test_plano_e_cache(self):
        a=np.zeros((12,48,48),np.uint8)
        a[2:6,10:14,10:14]=1
        a[4:10,30:36,30:36]=2
        a[1:4,2:5,2:7]=3
        m=engine.MasksCruas(a,{1:"liver",2:"tooth_11",3:"orphan"})
        sd=type("SaidaTeste",(),{"rotulos_para_cache":{(id(m),"liver")}})()
        m.compacta("tooth_11")
        m.espiar("orphan")
        self.assertNotIn("orphan",m._consultadas)
        engine.configurar_cache_entrega("test-828",modo="perso",oar_fora=["orphan"])
        try:
            engine._CACHE_ENTREGA["test-828"]["pendentes"]["teeth"]=({"chave":"x"},"cpu",False)
            with patch.object(engine,"_gravar_no_cache",return_value=True) as gravador:
                self.assertEqual(engine.finalizar_cache_entrega("test-828",{"teeth":m},sd),{"teeth":"x"})
            self.assertEqual(set(np.unique(gravador.call_args.args[1])),{0,1,2})
            self.assertEqual(set(np.unique(m._arr)),{0,1,2,3})
        finally:
            engine.liberar_cache_entrega("test-828")
        plano=engine.plano_de_rotulos({"lungs"},{"lung_lower_lobe_left","lung_upper_lobe_left","tooth_11"})
        self.assertTrue({"lung_left","lung_upper_lobe_left","lung_lower_lobe_left"}<=plano)
        self.assertNotIn("tooth_11",plano)
        fontes={"heart_model","pericardial_effusion","inferior_vena_cava","pericardium","costal_cartilages"}
        self.assertLessEqual(fontes,engine.plano_de_rotulos({"heart"},fontes))
        peri={"heart_model","aorta","pericardium","atrial_appendage_left"}
        self.assertLessEqual(peri,engine.plano_de_rotulos({"pericardium"},peri))

    def test_recorte_do_anus(self):
        import radai_constructs as construcoes
        import radai_rt
        with tempfile.TemporaryDirectory() as tmp:
            raiz=Path(tmp)
            stage=raiz/"series"
            stage.mkdir()
            shape=(18,48,48)
            serie_sintetica(stage,shape)
            import SimpleITK as sitk
            grade=geom.Grade.de_sitk(engine.load_sitk(stage))
            bag=np.zeros(shape,bool)
            bag[2:16,17:30,18:32]=True
            hip=np.zeros(shape,bool)
            hip[7:16,9:13,8:16]=True
            roi=construcoes.anus({"bag_bowel":bag,"hip_left":hip},grade).mascara
            self.assertTrue(roi.any())
            self.assertTrue(np.array_equal(np.where(roi.any(axis=(1,2)))[0],np.arange(2,8)))
            notas=[]
            for acabamento in ("padrao","fast"):
                rs,_=engine.build_rtstruct(stage,{"anus":roi},cru=True,rotulo="RadAI_STUDY",
                    modalidade="CT",suavizar_mm=1.5,perfil_contornos=acabamento)
                try:
                    le=radai_rt.abrir(stage,rs,com_ct=False)
                    try:
                        notas.append(le.mascara(le.nomes[0]).copy())
                    finally:
                        le.fechar()
                finally:
                    import shutil
                    shutil.rmtree(Path(rs).parent)
            np.testing.assert_array_equal(notas[0],notas[1])
            self.assertTrue(np.array_equal(np.where(notas[0].any(axis=(1,2)))[0],np.arange(2,8)))

    def test_roteamento_e_falhas(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz=Path(tmp)
            stage=raiz/"series"
            stage.mkdir()
            shape=(18,48,48)
            vol=serie_sintetica(stage,shape)
            a=np.zeros(shape,np.uint8)
            a[4:13,16:23,17:23]=1
            a[4:13,26:32,25:32]=2
            cruas={"teeth":engine.MasksCruas(a,{1:"tooth_11",2:"tooth_12"})}
            def saida(nome):
                out=raiz/nome
                out.mkdir()
                return output.Saida(engine,stage,out,"RS_RadAI_teste.dcm",tasks=["teeth"],modalidade="CT")
            s=saida("p")
            r=s.full_e_oar(cruas,volume_hu=vol,modo="perso",tasks_marcadas=["teeth"],oar_fora=["tooth_12"])
            self.assertFalse(r["full"])
            self.assertEqual(r["estruturas"],[engine.nome_clinico("tooth_11")])
            sf=saida("f")
            f=sf.full_e_oar(cruas,volume_hu=vol,modo="perso",tasks_marcadas=["teeth"],anatomia_geral_full=True)
            self.assertFalse(f["oar"])
            self.assertEqual(set(f["estruturas"]),{engine.nome_clinico(v) for v in ("tooth_11","tooth_12")})
            su=saida("uniao")
            proprio={"nome":"Teste","modalidade":"CT","estruturas":[],"merges":[{"nome":"MinhaUniao","de":["trachea","esophagus"]}]}
            cbase={"total_v3":engine.MasksCruas(a,{1:"trachea",2:"esophagus"})}
            ru=su.full_e_oar(cbase,volume_hu=vol,modo="perso",protocolo=proprio,
                oar_fora=["trachea","esophagus"],anatomia_geral_full=True)
            self.assertIn("MinhaUniao",ru["estruturas"])
            self.assertNotIn(engine.nome_clinico("trachea"),ru["estruturas"])
            sreq=saida("pedido-sem-volume")
            req=sreq.full_e_oar(cbase,volume_hu=vol,modo="perso",protocolo={
                "nome":"Teste","modalidade":"CT","estruturas":["trachea","anus"]})
            self.assertTrue(Path(req["entregue"]).is_file())
            self.assertIn("anus",req["parcial"]["motivo"])
            smu=saida("uniao-removida")
            with self.assertRaisesRegex(RuntimeError,"Nenhuma estrutura"):
                smu.full_e_oar(cbase,volume_hu=vol,modo="perso",protocolo=proprio,
                    oar_fora=["trachea","esophagus","uniao:MinhaUniao"])
            sx=saida("x")
            with self.assertRaisesRegex(RuntimeError,"Nenhuma estrutura"):
                sx.full_e_oar(cruas,volume_hu=vol,modo="perso",tasks_marcadas=["teeth"],oar_fora=["tooth_11","tooth_12"])
            self.assertFalse(list(Path(sx.destino).glob("*.dcm")))
            sc=saida("c")
            c=sc.full_e_oar(cruas,volume_hu=vol,modo="perso",tasks_marcadas=["teeth"],
                  comparadores={"ts":True,"cads":{"tooth_11":a==1},"mse":{"tooth_11":a==1},"nv":{"tooth_11":a==1}})
            for prefix in ("TS_","NV_","CADS_","MOOSE_"):
                self.assertTrue(any(n.startswith(prefix) for n in c["estruturas"]),prefix)
            self.assertEqual(len(list(Path(sc.destino).glob("*.dcm"))),1)
            sp=saida("parcial")
            pequena=np.zeros(shape,bool)
            pequena[9,20,20]=True
            rp=sp.full_e_oar(cruas,volume_hu=vol,modo="perso",tasks_marcadas=["teeth"],comparadores={"cads":{"minima":pequena}})
            self.assertTrue(rp["parcial"])
            self.assertTrue(Path(rp["entregue"]).exists())
            si=saida("grade")
            with self.assertRaisesRegex(ValueError,"grade"):
                si.full_e_oar(cruas,volume_hu=vol,modo="perso",tasks_marcadas=["teeth"],comparadores={"cads":{"erro":np.ones((2,2,2))}})
            self.assertFalse(list(Path(si.destino).glob("*.dcm")))
            sm=saida("snc")
            with self.assertRaisesRegex(RuntimeError,"SNC"):
                sm.full_e_oar(cruas,snc={})
            self.assertFalse(list(Path(sm.destino).glob("*.dcm")))

if __name__=="__main__":
    unittest.main()
