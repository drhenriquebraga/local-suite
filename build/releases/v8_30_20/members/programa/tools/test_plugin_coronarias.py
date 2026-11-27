"""Aceite dedicado e persistência do ROCardS em uma estação isolada."""
import asyncio
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
import radai_plugin_coronarias as plugin


class Consentimento(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.inicio = threading.Event()
        self.continuar = threading.Event()
        self.pronto = False
        self.chamadas = 0
        for chave, valor in (("REGISTRO", Path(tmp.name)), ("_estacao", lambda: "estacao_A"),
                             ("_preparar_recursos", self.preparar), ("_disponivel", lambda: self.pronto),
                             ("_erro", ""), ("_preparando", False)):
            edit = patch.object(plugin, chave, valor)
            edit.start()
            self.addCleanup(edit.stop)
        self.form = dict(aceito=True, termos_versao=plugin.VERSAO, termos_sha256=plugin.IMPRESSAO)
        self.addCleanup(self.terminar)

    def preparar(self):
        self.chamadas += 1
        self.inicio.set()
        if not self.continuar.wait(4):
            raise TimeoutError("tempo de teste")
        self.pronto = True

    def terminar(self):
        self.continuar.set()
        inicio = time.monotonic()
        while plugin.estado()["preparando"] and time.monotonic() - inicio < 5:
            time.sleep(.01)
        self.assertFalse(plugin.estado()["preparando"])

    def test_pesos_e_aceite_generico_nao_ativam(self):
        self.pronto = True
        (plugin.REGISTRO / "aceite.json").write_text(json.dumps(self.form))
        self.assertTrue(plugin.estado()["disponivel"])
        self.assertFalse(plugin.ativado())
        for mod in ({"aceito": False}, {"aceito": 1}, {"termos_versao": "0"}, {"termos_sha256": ""}):
            with self.assertRaises(ValueError):
                plugin.solicitar(dict(self.form, **mod))
        self.assertEqual(self.chamadas, 0)

    def test_ativar_idempotente_vinculado_a_estacao(self):
        self.assertTrue(plugin.solicitar(self.form)["preparando"])
        self.assertTrue(self.inicio.wait(2))
        self.assertFalse(plugin.ativado())
        plugin.solicitar(self.form)
        self.terminar()
        self.assertTrue(plugin.ativado())
        caminho = plugin._caminho()
        original = caminho.read_bytes()
        self.assertTrue(plugin.solicitar(self.form)["ativado"])
        self.assertEqual(self.chamadas, 1)
        self.assertEqual(caminho.read_bytes(), original)
        with patch.object(plugin, "_estacao", lambda: "estacao_B"):
            outro = plugin._caminho()
            outro.parent.mkdir()
            outro.write_bytes(original)
            self.assertFalse(plugin.ativado())
        self.pronto = False
        self.assertTrue(plugin.estado()["ativado"])
        self.assertFalse(plugin.estado()["disponivel"])
        caminho.write_text("{}", encoding="utf-8")
        self.assertFalse(plugin.ativado())

    def test_erro_ao_baixar_ou_gravar_nao_ativa(self):
        self.continuar.set()
        for metodo in ("_preparar_recursos", "_gravar"):
            with patch.object(plugin, metodo, side_effect=OSError("falha de teste")):
                plugin.solicitar(self.form)
                self.terminar()
            self.assertIn("falha de teste", plugin.estado()["erro"])
            self.assertFalse(plugin.ativado())
            self.assertFalse(plugin._caminho().exists())

    def test_rotas(self):
        from starlette.testclient import httpx
        from fastapi import FastAPI
        app = FastAPI()
        plugin.montar_rotas(app)

        async def testar():
            url = "http://127.0.0.1:8800"
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url=url) as cli:
                endpoint = "/api/plugins/coronarias/ativar"
                self.assertFalse((await cli.get("/api/plugins/coronarias")).json()["ativado"])
                for headers in ({}, {"origin": "https://externo.example"}):
                    self.assertEqual((await cli.post(endpoint, json=self.form, headers=headers)).status_code, 403)
                headers = {"origin": url}
                for dados in ({}, [], {"aceito": True}):
                    self.assertEqual((await cli.post(endpoint, json=dados, headers=headers)).status_code, 400)
                self.assertEqual((await cli.post(endpoint, content=b"x", headers=headers)).status_code, 415)
                resp = await cli.post(endpoint, json=self.form, headers=headers)
                self.assertEqual(resp.status_code, 202)
                self.assertTrue(resp.json()["preparando"])
        asyncio.run(testar())
        self.terminar()
        self.assertTrue(plugin.ativado())

    def test_importacao_exige_aceite_e_remove_temporario(self):
        from starlette.testclient import httpx
        from fastapi import FastAPI
        app = FastAPI()
        plugin.montar_rotas(app)
        recebidos = []

        def ler(arquivo):
            recebidos.append(arquivo)
            self.assertEqual(arquivo.read_bytes(), b"fixture")
            self.preparar()

        async def testar():
            url = "http://127.0.0.1:8800"
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url=url) as cli:
                endpoint = "/api/plugins/coronarias/importar"
                headers = {"origin": url, "content-type": "application/zip"}
                self.assertEqual((await cli.post(endpoint, content=b"x", headers=headers)).status_code, 400)
                headers.update({"x-radai-aceito": "1", "x-radai-termos-versao": plugin.VERSAO,
                                "x-radai-termos-sha256": plugin.IMPRESSAO})
                self.assertEqual((await cli.post(endpoint, content=b"", headers=headers)).status_code, 400)
                with patch.object(plugin, "MAX_PACOTE", 3):
                    self.assertEqual((await cli.post(endpoint, content=b"fixture", headers=headers)).status_code, 413)
                self.assertFalse(plugin.ativado())
                resp = await cli.post(endpoint, content=b"fixture", headers=headers)
                self.assertEqual(resp.status_code, 202)
                self.assertEqual((await cli.post(endpoint, content=b"fixture", headers=headers)).status_code, 409)
        with patch.object(plugin, "_importar_recursos", side_effect=ler), patch.object(plugin, "_preparar_recursos") as online:
            asyncio.run(testar())
            self.terminar()
            online.assert_not_called()
        self.assertTrue(plugin.ativado())
        self.assertEqual(len(recebidos), 1)
        self.assertFalse(recebidos[0].exists())

    def test_aceite_geral_33_exige_renovacao_e_nao_ativa_o_plugin(self):
        import radai_consent as geral
        registro = dict(versao=geral.VERSAO_DOCS, ensino_pesquisa=True,
                        catalogo_sha256=geral.catalogo_termos.catalogo()[0],
                        impressao=geral.impressao_dos_documentos(), itens=[p[0] for p in geral.PONTOS],
                        ferramentas_opcionais=geral.catalogo_termos.grupos_opcionais())
        with patch.object(geral, "aceite", return_value=registro):
            self.assertTrue(geral.aceito())
            self.assertFalse(plugin.ativado())
            self.assertFalse(geral.ferramenta_autorizada("rocards_lad"))
            for antiga in ("3.1", "3.2"):
                registro.update(versao=antiga, impressao=geral.IMPRESSOES_PUBLICADAS[antiga])
                self.assertFalse(geral.aceito())

    def test_durante_segmentacao_nao_inicia_download(self):
        import radai_atualizar as atualizar
        with patch.object(atualizar, "o_que_segura", return_value=atualizar.SEGURA_LOTE), patch.object(
                plugin, "_iniciar") as iniciar:
            with self.assertRaises(RuntimeError):
                plugin.solicitar(self.form)
            iniciar.assert_not_called()
            self.assertFalse(plugin.estado()["preparando"])


if __name__ == "__main__":
    unittest.main()
