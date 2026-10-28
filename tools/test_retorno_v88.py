# -*- coding: utf-8 -*-
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "app"))
sys.path.insert(0, str(RAIZ / "tools"))
import _cleanup
_cleanup.adotar_prefixo("radai_v88_")
BASE = _cleanup.temporaria("radai_v88_")
os.environ["RADAI_TMP"] = str(Path(BASE) / "tmp")
os.environ["RADAI_CALIB_DIR"] = str(Path(BASE) / "calib")
os.environ["RADAI_RAIZ_INSTALACAO"] = str(Path(BASE) / "instalacao")
os.environ["RADAI_CONFIG"] = str(Path(BASE) / "config" / "radai_watcher.config")
Path(os.environ["RADAI_CONFIG"]).parent.mkdir(parents=True, exist_ok=True)
Path(os.environ["RADAI_CONFIG"]).write_text("ROOT=\n", encoding="utf-8")


class RetornoCampo(unittest.TestCase):
    def test_temporarios_bytes_e_qhull_dentro_da_serie(self):
        import numpy as np
        from scipy.spatial import ConvexHull
        import radai_archive as A
        A.esquecer_temporaria()
        A.pasta_temporaria_local()
        with A.TemporariaDaSerie() as serie:
            for prefix in (b"scipy-", "scipy-"):
                fd, p = tempfile.mkstemp(prefix=prefix)
                os.close(fd)
                self.assertEqual(os.path.realpath(os.fsdecode(Path(os.fsdecode(p)).parent)),
                                 os.path.realpath(serie.pasta))
                os.unlink(p)
                d = tempfile.mkdtemp(prefix=prefix)
                os.rmdir(d)
            hull = ConvexHull(np.array([[0, 0], [3, 0], [3, 2], [0, 2], [1, 1]]))
            self.assertAlmostEqual(hull.volume, 6.0)
        self.assertTrue(serie.apagada)

    def test_rgb_persistencia_limites_e_modo_padrao(self):
        import radai_config as C
        cfg = str(Path(BASE) / "rgb" / "config")
        estruturas = {"CT": [{"nome_padrao": "Heart_ai"}]}
        ok, r = C.gravar_nomes("proprios", {}, estruturas, caminho_cfg=cfg,
                                cores={"Heart_ai": [0, 128, 255]})
        self.assertTrue(ok, r)
        self.assertEqual(C.cor_propria("Heart_ai", caminho_cfg=cfg), (0, 128, 255))
        ok, _ = C.gravar_nomes("padrao", {}, estruturas, caminho_cfg=cfg)
        self.assertTrue(ok)
        self.assertIsNone(C.cor_propria("Heart_ai", caminho_cfg=cfg))
        self.assertEqual(C.ler_nomes(cfg)["cores"], {"Heart_ai": [0, 128, 255]})
        for ruim in ([0, 256, 1], [True, 2, 3], [1, 2], "#123456"):
            ok, _ = C.gravar_nomes("proprios", {}, estruturas, caminho_cfg=cfg,
                                    cores={"Heart_ai": ruim})
            self.assertFalse(ok, ruim)
        ok, _ = C.gravar_nomes("proprios", {}, estruturas, caminho_cfg=cfg,
                                cores={"Outra_ai": [1, 2, 3]})
        self.assertFalse(ok)

    def test_importacao_roots_valida_todas_e_rgb_viaja(self):
        import json
        import radai_config as C
        valida = lambda p: {"existe": p != "ausente", "leitura": True, "escrita": True}
        self.assertFalse(C._aviso_da_chave("ROOTS", '["origem1", "origem2"]', valida))
        self.assertTrue(C._aviso_da_chave("ROOTS", '["origem1", "ausente"]', valida))
        self.assertTrue(C._aviso_da_chave("ROOTS", '{"path":"origem1"}', valida))
        estruturas = {"CT": [{"nome_padrao": "Heart_ai"}]}
        cfg = str(Path(BASE) / "exportar" / "config")
        C.gravar_nomes("proprios", {}, estruturas, caminho_cfg=cfg,
                       cores={"Heart_ai": [7, 83, 191]})
        exportado = C.exportar(cfg, [])
        outro = str(Path(BASE) / "importar" / "config")
        self.assertTrue(C.importar(exportado, ["nomes"], outro, [], estruturas)["ok"])
        self.assertEqual(C.cor_propria("Heart_ai", caminho_cfg=outro), (7, 83, 191))

    def test_serie_completa_nao_e_substituida_por_parcial_ou_recusada(self):
        import radai_varrer as V
        import radai_thumbnail as T
        job = V._novo("series", BASE, 0, {})
        V._iniciar_series(job)
        serie = {"uid": "1.2.3", "modalidade": "CT", "cortes": 12}
        with patch.object(T, "registrar_series", return_value={"1.2.3": "completa"}):
            V._aceitar_series(job, BASE, {"series": [serie]})
            maior = dict(serie, cortes=20)
            V._aceitar_series(job, BASE, {"series": [maior]}, carregando=True)
            self.assertEqual(V._linhas_series(job)[0]["bilhete"], "completa")
            V._aceitar_series(job, BASE, {"series": [maior]}, enriquecer=lambda *a: False)
        self.assertEqual(V._linhas_series(job)[0]["cortes"], 12)
        self.assertEqual(V._linhas_series(job)[0]["bilhete"], "completa")

    def test_publicacao_nao_regride_quando_dois_leitores_disputam(self):
        import radai_varrer as V
        job = V._novo("series", BASE, 0, {})
        V._iniciar_series(job)
        job["dados"]["por_uid"]["1"] = {"uid": "1", "cortes": 2, "carregando": True}
        publicando_parcial = threading.Event()
        liberar_parcial = threading.Event()
        atualizando = threading.Event()
        completa_publicada = threading.Event()
        original = V.publicar

        def publicar(j, linhas, *a, **k):
            if linhas[0]["carregando"]:
                publicando_parcial.set()
                liberar_parcial.wait(10)
            original(j, linhas, *a, **k)

        def completa():
            atualizando.set()
            with job["dados"]["trava"]:
                job["dados"]["por_uid"]["1"] = {
                    "uid": "1", "cortes": 20, "carregando": False, "bilhete": "PRONTO"}
            V.publicar_linhas(job, V._linhas_series)
            completa_publicada.set()

        with patch.object(V, "publicar", publicar):
            a = threading.Thread(target=V.publicar_linhas, args=(job, V._linhas_series))
            b = threading.Thread(target=completa)
            a.start()
            try:
                self.assertTrue(publicando_parcial.wait(10))
                b.start()
                self.assertTrue(atualizando.wait(10))
                self.assertFalse(completa_publicada.wait(0.1))
            finally:
                liberar_parcial.set()
                a.join(10)
                if b.ident is not None:
                    b.join(10)
        self.assertFalse(a.is_alive())
        self.assertFalse(b.is_alive())
        self.assertEqual(job["linhas"][0]["cortes"], 20)
        self.assertEqual(job["linhas"][0]["bilhete"], "PRONTO")

    def test_parar_nao_comeca_pastas_que_ainda_esperam_leitor(self):
        import radai_varrer as V
        raiz = Path(BASE) / "pendentes"
        for i in range(6):
            d = raiz / str(i)
            d.mkdir(parents=True, exist_ok=True)
            (d / "sintetico.txt").write_text("x", encoding="ascii")
        tres = threading.Event()
        liberar = threading.Event()
        chamadas = []
        trava = threading.Lock()

        def ler(job, pasta, nomes):
            with trava:
                chamadas.append(pasta)
                if len(chamadas) == 3:
                    tres.set()
            liberar.wait(10)
            return False

        u = V.registrar("teste_v88_pendentes", ler, lambda job: [])
        u.paralela = True
        d = V.iniciar(u.nome, str(raiz), dias=0)
        try:
            self.assertTrue(tres.wait(10))
            V.parar(d["v"])
        finally:
            liberar.set()
        limite = time.monotonic() + 10
        while not V.estado(d["v"])["fim"] and time.monotonic() < limite:
            time.sleep(0.02)
        self.assertTrue(V.estado(d["v"])["fim"])
        self.assertEqual(len(chamadas), 3)

    def test_varredura_publica_antes_do_fim_e_para_so_descoberta(self):
        import radai_dicom as D
        import radai_varrer as V
        import make_test_series as M
        from datetime import datetime
        pasta = Path(BASE) / "stream"
        M.escreve_serie(str(pasta), "FANTOMA_V88", datetime.now(), 12)
        original = D._ler_arquivo
        chegou = threading.Event()
        liberar = threading.Event()
        n = [0]

        def ler(*a, **k):
            original(*a, **k)
            n[0] += 1
            if n[0] == 3:
                chegou.set()
                liberar.wait(10)

        with patch.object(D, "_ler_arquivo", ler):
            d = V.iniciar("series", str(pasta), dias=0)
            try:
                self.assertTrue(chegou.wait(10))
                parcial = V.estado(d["v"])
                self.assertFalse(parcial["fim"])
                self.assertEqual(parcial["series"], 1)
                linha = parcial["linhas"][0]
                self.assertTrue(linha["carregando"])
                self.assertEqual(linha["cortes"], 2)
                self.assertIsNone(linha["bilhete"])
                V.parar(d["v"])
            finally:
                liberar.set()
            limite = time.monotonic() + 10
            while not V.estado(d["v"])["fim"] and time.monotonic() < limite:
                time.sleep(0.02)
            final = V.estado(d["v"])
        self.assertTrue(final["fim"])
        self.assertTrue(final["parado"])
        self.assertEqual(final["linhas"][0]["cortes"], 12)
        self.assertFalse(final["linhas"][0]["carregando"])
        self.assertTrue(final["linhas"][0]["bilhete"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
