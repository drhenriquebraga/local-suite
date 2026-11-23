"""Regressões da montagem sem espelho: recursos locais, integridade, espaço e seleção."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'build'), str(ROOT/'app')]
import bundle_portatil as bundle
import pacotes_portateis as pp
import configurar_ambiente as motor
import artefatos


class Portatil(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.sha = hashlib.sha256(b'valido').hexdigest()
        self.row = {'size':6, 'sha256':self.sha}

    def test_estacao_corrompida_mesmo_tamanho_recupera_do_zip(self):
        f=self.root/'python'/'file'; f.parent.mkdir(); f.write_bytes(b'falhou')
        good=self.root/'anterior.zip'
        with zipfile.ZipFile(good,'w') as out:
            out.writestr('LOCAL_SUITE/python/file',b'valido')
            out.writestr('LOCAL_SUITE/registro/arquivo',b'privado')
        with zipfile.ZipFile(good) as old, zipfile.ZipFile(self.root/'novo.zip','w') as out:
            src=bundle.verificar_local('python/file',(6,self.sha),[self.root],[old],'LOCAL_SUITE')
            self.assertIsInstance(src,tuple)
            bundle.escrever(out,'LOCAL_SUITE/python/file',src,self.sha)
        with zipfile.ZipFile(self.root/'novo.zip') as out:
            self.assertEqual(out.namelist(),['LOCAL_SUITE/python/file'])
            self.assertEqual(out.read(out.namelist()[0]),b'valido')

    def test_arquivo_alterado_durante_montagem_bloqueado(self):
        p=self.root/'peso';p.write_bytes(b'falhou')
        with zipfile.ZipFile(self.root/'teste.zip','w') as z, self.assertRaisesRegex(ValueError,'alterado'):
            bundle.escrever(z,'publico',p,self.sha)

    def test_corrompido_solicita_um_unico_dataset(self):
        folder='Dataset123_Peso'
        rel='ts_weights/'+folder+'/a'
        info=zipfile.ZipInfo(folder+'/a')
        def transfer(url,dest,progress):
            with zipfile.ZipFile(dest,'w') as z:z.writestr(info,b'valido')
        grupo='ts_weights/'+folder
        with mock.patch.dict(artefatos.PESOS_TS,{folder+'.zip':{'release':'test','bytes':10}}), \
                mock.patch.object(artefatos,'conferir_peso_ts',return_value=(True,'','')), \
                mock.patch.object(motor,'_transferir',side_effect=transfer) as baixar:
            with zipfile.ZipFile(self.root/'novo.zip','w') as out:
                for name,src,sha in bundle.complemento_ts(motor,grupo,{rel:(6,self.sha),rel+'antigo':(6,self.sha)},
                                                          {rel+'antigo':self.root},[],self.root):
                    self.assertEqual(sha,self.sha);bundle.escrever(out,name,src,sha)
            self.assertEqual(baixar.call_count,1)

    def test_disco_mesmo_volume_exige_so_saida_mais_temporarios(self):
        with mock.patch.object(bundle.shutil,'disk_usage',return_value=mock.Mock(free=124)):
            bundle.conferir_espaco(self.root,self.root,123,1)
            with self.assertRaisesRegex(OSError,'insuficiente'):
                bundle.conferir_espaco(self.root,self.root,123,2)

    def test_lung_reutiliza_locais_e_baixa_so_ausente(self):
        path='peso/a'; (self.root/'code/catalog').mkdir(parents=True)
        xray={'revision':'v', **{k:dict(self.row,filename=k,url=k) for k in ('runtime','model','mmproj')}}
        (self.root/'code/catalog/xray_resources.json').write_text(json.dumps(xray))
        rt=self.root/'Plugins/LUNG RT/resources/v'/path
        rt.parent.mkdir(parents=True);rt.write_bytes(b'valido')
        x=self.root/'Plugins/LUNG RT/data/xray/v';x.mkdir(parents=True)
        for k in ('model','mmproj'):(x/k).write_bytes(b'valido')
        def download(urls,dest,*unused):
            dest.write_bytes(b'valido');return dest
        with mock.patch.object(pp.lung,'_download',side_effect=download) as fetch:
            result=[(name,f.read_bytes()) for name,f,*_ in pp.recursos_lung(
                self.root,self.root,{'files':[dict(self.row,path=path,url=path)]},self.root)]
        self.assertEqual(len(result),4)
        self.assertEqual(fetch.call_count,1)
        self.assertEqual(fetch.call_args.args[0],['runtime'])
        self.assertTrue(rt.exists())

    def test_catalogo_cobre_perfil_atual_e_exclui_dados_privados(self):
        rows=bundle.inventario(dict(profile='full',modelos_omitidos={'nv_segment_ct'},so_cpu=False,cuda='cu121'),motor)
        self.assertIn('ts_weights/Dataset299_body_1559subj',rows)
        self.assertIn('modelos/jhu_rectum',rows)
        self.assertNotIn('modelos/nv_segment_ct',rows)
        self.assertNotIn('modelos/rocards',rows)
        self.assertNotIn('registro',rows)
        self.assertGreater(len(rows['python']),20000)

if __name__=='__main__': unittest.main()
