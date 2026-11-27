"""Regressions for the folder cutoff and the idle NIDUS temporal worker."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main
from unittest.mock import Mock, patch
import base64
import io
import os
import sys
import threading
import time
import zipfile
import zlib

APP = Path(__file__).resolve().parents[1] / 'app'
sys.path.insert(0, str(APP))


class ScreenWork(TestCase):
    def test_cutoff_before_limit_and_chronological_order(self):
        import radai_batch as batch
        import radai_varrer as scan
        with TemporaryDirectory() as root:
            now = int(time.time()) - 30
            for name, age in [('a-old',2*86400),('b-edge',86400),('c-new',60)]:
                path = Path(root)/name
                path.mkdir()
                os.utime(path,(now-age,now-age))
            result = batch.listar_pastas_do_explorador(root, ordem='data', sentido='desc', teto=1, dias=1, referencia=now)
            self.assertEqual((result['total'],result['ocultas_data'],result['mostrando']),(2,1,1))
            self.assertEqual([p['nome'] for p in result['pastas']],['c-new'])
            self.assertTrue(scan.dentro_da_data(Path(root)/'b-edge', scan.limite_da_data(1,now)))
            self.assertFalse(scan.dentro_da_data(Path(root)/'a-old', scan.limite_da_data(1,now)))
            self.assertEqual(batch.listar_pastas_do_explorador(root)['total'],3)

    def test_mapped_and_unc_paths_reserve_the_same_server(self):
        import radai_archive as archive
        import radai_leitura_ativa as reads
        with patch.object(archive,'_destino_dos',return_value='/device/lanmanredirector/;z:123/fileserver/share'.replace('/',chr(92))):
            server=reads.servidor_da_pasta('Z:/studies')
            self.assertEqual(server,'fileserver')
            self.assertEqual(reads.servidor_da_pasta('//Fileserver/Other'),server)
            self.assertTrue(reads._adquirir(server))
            try:
                self.assertFalse(reads._adquirir(server))
                self.assertFalse(reads._adquirir(True))
                self.assertTrue(reads._adquirir('other-server'))
                reads._liberar('other-server')
            finally:reads._liberar(server)

    def test_two_clients_share_one_surface_and_last_close_cancels(self):
        import asyncio
        from fastapi import HTTPException
        import radai_recon3d_screen as recon

        async def run():
            class Client:
                def __init__(self):
                    self.left=asyncio.Event()
                async def receive(self):
                    await self.left.wait()
                    return {"type":"http.disconnect"}
            begin, release = asyncio.Event(), asyncio.Event()
            built = []
            async def build(request, ticket, func):
                built.append(ticket)
                begin.set()
                if ticket=='shared':
                    await release.wait()
                    return b'surface'
                await request.receive()
                release.set()
                raise HTTPException(499)
            first,second=Client(),Client()
            def mesh(): pass
            with patch.object(recon,'_ler_visor',side_effect=build):
                a=asyncio.create_task(recon._malha_compartilhada(first,'shared',mesh))
                await begin.wait()
                b=asyncio.create_task(recon._malha_compartilhada(second,'shared',mesh))
                await asyncio.sleep(0)
                first.left.set()
                with self.assertRaises(HTTPException):await a
                release.set()
                self.assertEqual(await b,b'surface')
                self.assertEqual(built,['shared'])
                begin.clear();release.clear()
                c=asyncio.create_task(recon._malha_compartilhada(second,'cancel',mesh))
                await begin.wait()
                second.left.set()
                with self.assertRaises(HTTPException):await c
                await asyncio.wait_for(release.wait(),1)
                self.assertFalse(recon._malhas_em_curso)
        asyncio.run(run())

    def test_seed_temporal_worker_drains_and_cache_expires(self):
        from radai_plugin_seeds import SEEDS
        seed = SEEDS['neuro-rt']
        with TemporaryDirectory() as folder:
            with zipfile.ZipFile(io.BytesIO(zlib.decompress(base64.b64decode(seed['archive'])))) as archive:
                archive.extractall(folder)
            sys.path.insert(0,str(Path(folder)/'code'))
            try:
                from neuro_rt.nidus_temporal_api import TemporalService
                s=TemporalService(None,threading.Lock())
                try:
                    self.assertIsNone(s.worker)
                    self.assertIsNone(s.expiry)
                    s.ttl=.15
                    done=threading.Event()
                    group=Mock(id='test-group',kind='projection2d',frames=[])
                    group.public.return_value=dict(kind='projection2d',can_rotate=False,frames=[],timing_known=True)
                    def run(job):
                        with s.lock: job.state='ready'
                        done.set()
                    for n in range(2):
                        with s.lock:s.groups[group.id]=(group,time.monotonic())
                        with patch.object(s,'_run',side_effect=run):
                            s.prepare({'group':group.id})
                            self.assertTrue(done.wait(2))
                        until=time.monotonic()+2
                        while time.monotonic()<until and (s.worker or s.expiry):time.sleep(.01)
                        self.assertIsNone(s.worker)
                        self.assertIsNone(s.expiry)
                        self.assertEqual(len(s.jobs)+len(s.groups),0)
                        done.clear()
                finally:s.close()
            finally:sys.path.pop(0)


if __name__=='__main__':
    main()
