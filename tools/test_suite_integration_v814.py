from contextlib import ExitStack
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
import radai_series_source as Source
import radai_install_profile as Profile
import radai_varrer as Scan
import radai_thumbnail as Thumb
import radai_archive as Archive

class Isolated(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='suite-integration-v814-')
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(Source, '_EXTRACTED', {}))
        self.stack.enter_context(patch.object(Archive, 'marcar_em_uso'))
        self.stack.enter_context(patch.object(Archive, 'soltar_em_uso'))
        self.stack.enter_context(patch.object(Scan, '_VARREDURAS', {}))
        self.stack.enter_context(patch.object(Thumb, '_MAPA', {}))
        self.stack.enter_context(patch.object(Thumb, '_SERIES', {}))
        def extraction(**_):
            p = self.root / ('extract-' + uuid.uuid4().hex)
            p.mkdir()
            return str(p)
        self.stack.enter_context(patch.object(Source.tempfile, 'mkdtemp', extraction))

    def make_zip(self, entries):
        path = self.root / ('input-' + uuid.uuid4().hex + '.zip')
        with zipfile.ZipFile(path, 'w') as z:
            for name, value in entries:
                z.writestr(name, value)
        return path

    def reject_zip(self, path, **kwargs):
        folder, error = Source.resolve_folder(str(path), **kwargs)
        self.assertEqual(folder, '')
        self.assertTrue(error)
        self.assertFalse(list(self.root.glob('extract-*')))

    def selection(self):
        folder = self.root / 'series'
        folder.mkdir(exist_ok=True)
        file = folder / 'synthetic.dcm'
        file.write_bytes(b'NOT CLINICAL; CACHE CONTRACT FIXTURE')
        uid = '1.2.826.0.1.3680043.10.999.1'
        ticket = Thumb.bilhete(str(folder), uid)
        Thumb._SERIES[ticket] = {'uid':uid, 'arquivos':[str(file)], 'modalidade':'CT'}
        job = Scan._novo('series', str(folder), 0, {})
        job.update(final=True, fim=True, linhas=[{'uid':uid, 'bilhete':ticket}], source_original='synthetic.zip')
        Scan._VARREDURAS[job['v']] = job
        return {'scan_id':job['v'], 'bilhete':ticket, 'uid':uid}, job, file

class ProfileTests(Isolated):
    def test_default_and_explicit_profiles(self):
        self.assertEqual(Profile.perfil(self.root), 'full')
        for value in ('full','lung-rt'):
            (self.root/'suite-profile.json').write_text(json.dumps({'schema':Profile.SCHEMA,'profile':value}))
            self.assertEqual(Profile.perfil(self.root), value)

    def test_invalid_present_stamp_fails_closed(self):
        for content in ('{bad','[]','null','7','"full"', '{}', json.dumps({'schema':'wrong','profile':'full'}), ' '*4097):
            with self.subTest(content=content[:25]):
                (self.root/'suite-profile.json').write_text(content)
                self.assertEqual(Profile.perfil(self.root), 'lung-rt')

class ZipTests(Isolated):
    def test_valid_archive_cached_and_derived_preserved(self):
        path = self.make_zip([('case/one.dcm',b'SYNTHETIC'),('case/two.dcm',b'SYNTHETIC2')])
        folder, error = Source.resolve_folder(str(path))
        self.assertFalse(error)
        self.assertEqual((Path(folder)/'case/one.dcm').read_bytes(), b'SYNTHETIC')
        self.assertEqual(Source.resolve_folder(str(path)), (folder,''))
        derived = Path(folder)/'new-derived.dcm'
        derived.write_bytes(b'UNAPPROVED SYNTHETIC')
        Source.close()
        self.assertTrue(derived.is_file())

    def test_folder_identity(self):
        self.assertEqual(Source.resolve_folder(str(self.root)), (str(self.root.resolve()),''))

    def test_empty_input_is_not_current_directory(self):
        folder, error = Source.resolve_folder('')
        self.assertEqual(folder, '')
        self.assertTrue(error)

    def test_traversal_windows_ads_and_reserved_names(self):
        for name in ('../outside','C:/outside','/outside','a\\..\\outside','a/file:stream','NUL.dcm','a./x','a /x','a//x'):
            with self.subTest(name=name):
                self.reject_zip(self.make_zip([(name,b'x')]))
        self.assertFalse((self.root.parent/'outside').exists())

    def test_duplicate_casefold_and_file_directory_collision(self):
        for entries in ([('a.dcm',b'x'),('A.DCM',b'y')],[('a',b'x'),('a/b.dcm',b'y')]):
            with self.subTest(entries=entries):
                self.reject_zip(self.make_zip(entries))

    def test_symlink(self):
        entry = zipfile.ZipInfo('linked.dcm')
        entry.create_system = 3
        entry.external_attr = (stat.S_IFLNK | 0o777) << 16
        self.reject_zip(self.make_zip([(entry,b'../outside')]))

    def test_count_size_disk_and_cancel_limits(self):
        path = self.make_zip([('a',b'a'),('b',b'b')])
        with patch.object(Source,'MAX_FILES',1):
            self.reject_zip(path)
        with patch.object(Source,'MAX_BYTES',1):
            self.reject_zip(path)
        with patch.object(Source.shutil,'disk_usage',return_value=type('Disk',(),{'free':1})()):
            self.reject_zip(path)
        self.reject_zip(path,cancelled=lambda:True)

    def test_crc_corruption_is_not_returned_or_cached(self):
        path = self.make_zip([('a.dcm',b'UNIQUE_SYNTHETIC_PAYLOAD')])
        raw = path.read_bytes().replace(b'UNIQUE_SYNTHETIC_PAYLOAD',b'WRONG__SYNTHETIC_PAYLOAD')
        path.write_bytes(raw)
        self.reject_zip(path)
        self.assertFalse(Source._EXTRACTED)

class TicketTests(Isolated):
    def test_binds_scan_ticket_uid_and_ignores_client_paths(self):
        selected, job, file = self.selection()
        selected.update(pasta='C:/UNRELATED',arquivos=['C:/UNRELATED'])
        value = Source.resolve_selection(selected)
        self.assertEqual(value['pasta'],str(file.parent))
        self.assertEqual(value['scan_root'],job['pasta'])
        self.assertEqual(value['source_original'],'synthetic.zip')
        self.assertEqual(value['arquivos'],[str(file)])

    def test_bad_inputs_and_cross_scan(self):
        selected,job,file = self.selection()
        for item in (None,[],{},dict(selected,scan_id='absent'),dict(selected,bilhete='wrong'),dict(selected,uid='wrong')):
            with self.subTest(value=item):
                with self.assertRaises(ValueError):
                    Source.resolve_selection(item)

    def test_incomplete_error_partial_and_refused_rows(self):
        selected,job,file = self.selection()
        for changes in ({'final':False},{'erro':'failed'},{'linhas':[dict(job['linhas'][0],carregando=True)]},{'linhas':[dict(job['linhas'][0],recusa='wrong modality')]}):
            old = job.copy()
            job.update(changes)
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    Source.resolve_selection(selected)
            job.clear();job.update(old)

    def test_ticket_expiry(self):
        selected,job,file = self.selection()
        Thumb._MAPA.clear()
        with self.assertRaises(ValueError):
            Source.resolve_selection(selected)

    def test_cached_selection_requires_files_still_available(self):
        selected,job,file = self.selection()
        file.unlink()
        with self.assertRaises(ValueError):
            Source.resolve_selection(selected)

class RoutingTests(Isolated):
    def test_compact_blocks_full_module_urls(self):
        from fastapi import FastAPI
        from starlette.testclient import TestClient
        import radai_router as Router
        import radai_porta as Home
        app = FastAPI()
        with patch.object(Profile,'perfil',return_value='lung-rt'), patch.object(Router,'mini_pagina',side_effect=lambda key:'synthetic '+key), patch.object(Home,'montar'):
            Router.montar(app)
            with TestClient(app) as client:
                for path in ('/bridge','/bolus','/recon3d','/elastic'):
                    with self.subTest(path=path):
                        response=client.get(path,follow_redirects=False)
                        self.assertIn(response.status_code,(403,404))
                self.assertEqual(client.get('/lung').status_code,200)


class CapabilityMatrixTests(Isolated):
    DENIED = (
        '/bridge/laudo','/elastic/fusao','/bolus/gerar','/neuro','/nidus',
        '/recon3d','/recon3d/anatomia','/recon3d/vascular','/autocontorno',
        '/api/bridge/laudo','/api/elastic/fundir','/api/bolus/gerar',
        '/api/neuro/segmentar','/api/nidus/exportar','/api/recon3d/vascular/exportar',
        '/api/fila/neuro/iniciar','/api/plugins/neuro-rt/install',
    )
    ALLOWED = (
        '/lung','/lung/nodulos','/lung/4d','/lung/rastreio','/lung/laudo','/config','/aceite',
        '/lote','/recon3d/toracica','/ver','/api/lung/acao','/api/lung-plugin/action',
        '/api/plugins/lung-rt/install','/api/lote/enfileirar','/api/lote/favorita',
        '/api/pipeline/iniciar','/api/varrer/iniciar','/api/pastas','/api/verseg/forma',
        '/api/umeixo/corte','/api/ver/abrir','/api/recon3d/projecao','/api/recon3d/malha',
        '/api/fila/estado','/api/reiniciar','/radai-idiomas.js','/lung-assets/app.js',
    )
    def client(self, profile):
        from fastapi import FastAPI, Request
        from starlette.testclient import TestClient
        (self.root/'suite-profile.json').write_text(json.dumps({'schema':Profile.SCHEMA,'profile':profile}))
        app=FastAPI()
        self.reached=[]
        async def sentinel(request:Request):
            self.reached.append((request.method, request.url.path))
            return {'synthetic':True}
        for route in self.DENIED+self.ALLOWED:
            app.add_api_route(route,sentinel,methods=['GET','POST','PUT','DELETE'])
        Profile.montar_portao(app, self.root)
        Profile.montar_portao(app, self.root)
        self.assertEqual(len(app.user_middleware),1)
        return TestClient(app,base_url='http://127.0.0.1')

    def test_compact_denies_mutations_before_endpoint(self):
        with self.client('lung-rt') as client:
            for path in self.DENIED:
                for method in ('GET','POST','PUT','DELETE'):
                    with self.subTest(path=path,method=method):
                        response=client.request(method,path,json={'synthetic':True})
                        self.assertEqual(response.status_code,403)
                        self.assertEqual(response.headers.get('cache-control'),'no-store')
            self.assertEqual(self.reached,[])

    def test_compact_keeps_lung_and_shared_services(self):
        with self.client('lung-rt') as client:
            for path in self.ALLOWED:
                for method in ('GET','POST'):
                    with self.subTest(path=path,method=method):
                        self.assertEqual(client.request(method,path).status_code,200)
            self.assertEqual(len(self.reached),2*len(self.ALLOWED))

    def test_full_preserves_all_routes_and_methods(self):
        with self.client('full') as client:
            for path in self.DENIED+self.ALLOWED:
                for method in ('GET','POST','PUT','DELETE'):
                    with self.subTest(path=path,method=method):
                        self.assertEqual(client.request(method,path).status_code,200)
            self.assertEqual(len(self.reached),4*(len(self.DENIED)+len(self.ALLOWED)))

class RealDiscoveryTests(Isolated):
    def test_synthetic_dicom_zip_final_ticket_resolution(self):
        import io
        import pydicom
        from pydicom.dataset import FileDataset, FileMetaDataset
        from pydicom.uid import ExplicitVRLittleEndian, CTImageStorage, generate_uid
        study,series,frame=generate_uid(),generate_uid(),generate_uid()
        entries=[]
        for index in range(3):
            sop=generate_uid()
            meta=FileMetaDataset()
            meta.TransferSyntaxUID=ExplicitVRLittleEndian
            meta.MediaStorageSOPClassUID=CTImageStorage
            meta.MediaStorageSOPInstanceUID=sop
            ds=FileDataset(None,{},file_meta=meta,preamble=b'\0'*128)
            ds.SOPClassUID=CTImageStorage;ds.SOPInstanceUID=sop
            ds.StudyInstanceUID=study;ds.SeriesInstanceUID=series;ds.FrameOfReferenceUID=frame
            ds.PatientID='SYNTHETIC';ds.PatientName='SYNTHETIC'
            ds.StudyDate='20200101';ds.Modality='CT';ds.SeriesDescription='SYNTHETIC CHEST'
            ds.Rows=2;ds.Columns=2;ds.InstanceNumber=index+1
            ds.ImagePositionPatient=[0,0,float(index)];ds.ImageOrientationPatient=[1,0,0,0,1,0]
            ds.PixelSpacing=[1,1];ds.SliceThickness=1
            ds.SamplesPerPixel=1;ds.PhotometricInterpretation='MONOCHROME2'
            ds.BitsAllocated=16;ds.BitsStored=16;ds.HighBit=15;ds.PixelRepresentation=1
            ds.PixelData=b'\0'*8
            stream=io.BytesIO()
            pydicom.dcmwrite(stream,ds,write_like_original=False)
            entries.append(('case/%s.dcm'%index,stream.getvalue()))
        path=self.make_zip(entries)
        state=Scan.iniciar('series',str(path),dias=0,em_segundo_plano=False)
        self.assertFalse(state.get('erro'),state)
        self.assertTrue(state['final'],state)
        self.assertEqual(len(state['linhas']),1,state)
        row=state['linhas'][0]
        self.assertEqual(row['uid'],series)
        result=Source.resolve_selection(dict(row,scan_id=state['v']))
        self.assertEqual(result['source_original'],str(path))
        self.assertEqual(len(result['arquivos']),3)
        self.assertTrue(all(isinstance(f, dict) and Path(f['caminho']).is_file() for f in result['arquivos']))
        self.assertNotEqual(result['scan_root'],str(path))


if __name__ == '__main__':
    unittest.main(verbosity=2)
