"""Ciclo de vida de caches de prévias JPEG, Ver Segmentação e Reconstrução 3D."""
import asyncio
import concurrent.futures
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"app"))
import radai_cache_visor
import radai_image_screen as imagem
import radai_recon3d_screen as recon
import radai_viewseg as verse


class Caches(unittest.TestCase):
    def test_duas_abas_e_fechamento_durante_leitura(self):
        evento = threading.Event()
        em_uso = threading.Event()
        esvaziou = []
        cache = radai_cache_visor.CacheDoVisor(lambda: esvaziou.append(1))
        @cache.usar
        def ler():
            em_uso.set()
            evento.wait(2)
            return "ok"
        cache.abrir("a")
        cache.abrir("b")
        cache.fechar("a")
        self.assertFalse(esvaziou)
        with concurrent.futures.ThreadPoolExecutor(1) as pool:
            result = pool.submit(ler)
            self.assertTrue(em_uso.wait(2))
            cache.fechar("b")
            self.assertFalse(esvaziou)
            evento.set()
            self.assertEqual(result.result(2),"ok")
        self.assertEqual(esvaziou,[1])
        self.assertIsNone(cache._relogio)

    def test_expira_sem_cliente_e_nao_sonda_o_disco(self):
        acabou = threading.Event()
        cache = radai_cache_visor.CacheDoVisor(acabou.set,prazo=.05)
        cache.usar(lambda: None)()
        self.assertTrue(acabou.wait(2))
        self.assertIsNone(cache._relogio)

    def test_reabrir_entre_fechamento_e_fim_da_resposta(self):
        cache = radai_cache_visor.CacheDoVisor(lambda: self.fail("apagou a segunda aba"))
        cache.abrir("a")
        @cache.usar
        def ler():
            cache.fechar("a")
            cache.abrir("b")
        ler()
        cache.limpar=lambda:None
        cache.fechar("b")

    def test_rotas_soltam_so_cache_da_ultima_aba(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        app=FastAPI()
        for m in (imagem,verse,recon):m.montar(app)
        with TestClient(app) as cli:
            for nome,obj,key,cache in [('imagem',imagem._VOLUMES,'demo',imagem._CACHE_VISUAL),
                                       ('verseg',verse._SERIE,'ct',verse._CACHE_VISUAL),
                                       ('recon3d',recon._VOL,'v',recon._CACHE_VISUAL)]:
                url='/api/cache-visor/'+nome
                a,b='a'*32,'b'*32
                for token in [a,b]:
                    self.assertEqual(cli.post(url,json={'dono':token,'ativo':True}).status_code,204)
                token_object=object();obj[key]=token_object
                cli.post(url,json={'dono':a,'ativo':False})
                self.assertIs(obj.get(key),token_object)
                cli.post(url,json={'dono':b,'ativo':False})
                self.assertIsNone(obj.get(key))

    def test_cancelar_laudo_interrompe_amostra_e_preserva_conversao_confirmada(self):
        from fastapi import FastAPI
        from PIL import Image
        import radai_image
        app = FastAPI()
        imagem.montar(app)
        rota = next(r.endpoint for r in app.routes if r.path == "/api/imagem/laudo")
        geometria = {"espacamento_mm": (0.8, 0.8), "espessura_mm": 3,
                     "orientacao": "axial", "posicao_paciente": "HFS"}
        fechar = threading.Event()
        amostrando = threading.Event()
        convertendo = threading.Event()
        seguir = threading.Event()
        laudo_concluido = threading.Event()
        chamadas = []
        ctx = threading.local()
        decodificar = radai_image.ler_cinza
        original_conferir = radai_image.conferir

        class Pedido:
            async def json(self):
                return {"b": "fantoma", "geometria": geometria}

            async def is_disconnected(self):
                return fechar.is_set()

        def ficha(_bilhete, _parar):
            ctx.previa = True
            return serie, temp

        def ler(caminho):
            if getattr(ctx, "previa", False):
                chamadas.append(caminho)
                amostrando.set()
                time.sleep(.25)
            else:
                convertendo.set()
                self.assertTrue(seguir.wait(3))
            return decodificar(caminho)

        def conferir(*args, **kwargs):
            try:
                return original_conferir(*args, **kwargs)
            finally:
                if getattr(ctx, "previa", False):
                    laudo_concluido.set()

        with tempfile.TemporaryDirectory() as temp:
            raiz = Path(temp)
            for i in range(12):
                Image.new('L', (48, 64), i).save(raiz / ('image_s0001_i%04d.png' % i))
            serie = radai_image.varrer(temp)['series'][0]
            with patch.object(imagem, "_ficha_visual", side_effect=ficha), \
                 patch.object(radai_image, "ler_cinza", side_effect=ler), \
                 patch.object(radai_image, "conferir", side_effect=conferir), \
                 concurrent.futures.ThreadPoolExecutor(2) as pool:
                laudo = pool.submit(asyncio.run, rota(Pedido()))
                try:
                    self.assertTrue(amostrando.wait(2))
                    conv = pool.submit(radai_image.converter, serie, str(raiz / 'saida'),
                                       geometria, modalidade='MR', como='sc')
                    self.assertTrue(convertendo.wait(2))
                    fechar.set()
                    self.assertIn("interrompida", laudo.result(3)["erro"].lower())
                    self.assertTrue(laudo_concluido.wait(2))
                    self.assertEqual(len(chamadas), 1)
                finally:
                    fechar.set()
                    seguir.set()
                self.assertEqual(conv.result(3)["gravados"], 12)
                self.assertEqual(len(list((raiz / 'saida').glob("*.dcm"))), 12)

    def test_mpr_dois_planos_compartilham_varredura_e_decode(self):
        from PIL import Image
        import radai_thumbnail
        import radai_image
        with tempfile.TemporaryDirectory() as temp:
            for i in range(5): Image.new('L',(48,64),i).save(Path(temp)/('s1i%02d.png'%i))
            chave=radai_image.varrer(temp)['series'][0]['chave']
            with patch.object(radai_thumbnail,'resolver',return_value=(temp,chave)), \
                 patch.object(radai_image,'varrer',wraps=radai_image.varrer) as scan, \
                 patch.object(radai_image,'volume',wraps=radai_image.volume) as dec:
                with concurrent.futures.ThreadPoolExecutor(2) as pool:
                    a,b=pool.map(imagem._volume,['A','A'])
                self.assertIs(a[1],b[1])
                self.assertEqual(scan.call_count,1)
                self.assertEqual(dec.call_count,1)
                # A conversão confirmada pelo operador consulta a origem novamente.
                imagem.serie_do_bilhete('A')
                self.assertEqual(scan.call_count,2)
            imagem._soltar_cache_visual()

if __name__=='__main__':
    unittest.main()
