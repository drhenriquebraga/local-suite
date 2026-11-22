"""Exercita os protocolos da quarta coluna no navegador, com séries fictícias."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit

from fastapi import FastAPI
from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright

APP = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP))
import radai_batch as lote
import radai_config as config


class ColunaDosProtocolos(unittest.TestCase):
    def setUp(self):
        pasta = tempfile.TemporaryDirectory()
        self.addCleanup(pasta.cleanup)
        cfg = Path(pasta.name) / "config.txt"
        self.enterContext(patch.dict(os.environ, {"RADAI_CONFIG": str(cfg)}))
        self.enterContext(patch("radai_snc_rm.disponivel", return_value=True))
        self.proprio = cfg.with_name(config.NOME_DOS_PROTOCOLOS)
        self.proprio.write_text(json.dumps({"protocolos": [{
            "id": "estacao-antiga", "nome": "Da estação", "modalidade": "CT",
            "estruturas": ["urinary_bladder"], "merges": []}]}), encoding="utf-8")
        self.antes = self.proprio.read_bytes()
        app = FastAPI()
        lote.montar(app)
        self.api = TestClient(app)
        playwright = self.enterContext(sync_playwright())
        chrome = Path(os.environ.get("RADAI_CHROME", r"C:\Program Files\Google\Chrome\Application\chrome.exe"))
        browser = playwright.chromium.launch(headless=True, executable_path=str(chrome) if chrome.is_file() else None)
        self.addCleanup(browser.close)
        self.page = browser.new_page(locale="pt-BR", reduced_motion="reduce")
        self.requests = []
        self.queued = []
        self.page.route("**/*", self.serve)
        self.page.goto("http://suite.test/lote")
        self.page.wait_for_function("typeof OPC !== 'undefined' && OPC.CT && OPC.MR")

    def serve(self, route):
        request = route.request
        path = urlsplit(request.url).path
        if path == "/api/lote/enfileirar":
            self.queued.extend(request.post_data_json["series"])
            return route.fulfill(json={"ok": True, "enfileiradas": 1})
        if path == "/api/lote/previa_da_entrega":
            self.requests.append(request.post_data_json["serie"])
        if path in ("/lote", "/api/lote/opcoes", "/api/lote/previa_da_entrega"):
            response = self.api.request(request.method, request.url, content=request.post_data or b"")
            return route.fulfill(status=response.status_code, content_type=response.headers["content-type"],
                                 body=response.content)
        if path.endswith(".js"):
            return route.fulfill(content_type="application/javascript", body="")
        return route.fulfill(json={})

    def abrir_serie(self, modalidade):
        self.page.evaluate("""mod => {
            const s = {modalidade:mod, pasta:'fantoma', uid:'1.2.3.'+(mod==='CT'?1:2), cortes:100};
            SERIES=[s]; porNoCarrinho(s,true); sincronizarIncl(); pintarTabela(); psAbrir('cx2',true);
            escolhaDe(s).modo='perso'; _acertarPainel(0);
        }""", modalidade)
        self.pronto()

    def pronto(self):
        self.page.locator('#p4e_0[aria-busy="false"] .oar-tags').first.wait_for()

    def selecionar(self, seletor):
        # O conteúdo antigo deixa de ser interativo no próprio evento change,
        # antes da requisição de prévia do protocolo seguinte.
        with self.page.expect_response(lambda r: r.url.endswith("/previa_da_entrega")):
            restantes = self.page.locator(seletor).evaluate(
                "botao => {botao.click(); return document.querySelectorAll('#p4e_0 .oar-tag').length}")
            self.assertEqual(restantes, 0)
        self.pronto()

    def chaves(self, atributo="data-oar-x"):
        return set(self.page.locator("#p4e_0 [" + atributo + "]").evaluate_all(
            "(itens, attr) => itens.map(x=>x.getAttribute(attr))", atributo))

    def test_todos_os_protocolos_tc_e_rm_e_anatomia_toracica(self):
        for mod in ("CT", "MR"):
            self.abrir_serie(mod)
            for grupo, campo in (("prot", "protocolos"), ("p3d", "protocolos_3d")):
                ids = self.page.locator(f'input[data-{grupo}]').evaluate_all(
                    "(itens, attr) => itens.map(x=>x.getAttribute(attr))", "data-" + grupo)
                for cod in ids:
                    with self.subTest(modalidade=mod, protocolo=cod):
                        self.selecionar(f'input[data-{grupo}="{cod}"]')
                        pedido = self.requests[-1]
                        self.assertEqual(pedido[campo], [cod])
                        self.assertEqual(pedido["oar_fora"], [])
                        previsao = self.api.post("/api/lote/previa_da_entrega", json={"serie":pedido}).json()
                        self.assertEqual(self.chaves(), {x["chave"] for x in previsao["oar"]["estruturas"]})
                        self.assertFalse(self.chaves("data-oar-volta"))
                        if cod == "torax_mama":
                            self.assertIn("heart", self.chaves())
                            self.assertFalse(self.chaves() & {"anus","bag_bowel_oar","urinary_bladder"})
                        if cod == "pelve":
                            self.assertIn("urinary_bladder", self.chaves())
                            self.assertNotIn("heart", self.chaves())

    def test_manual_rascunho_proprio_full_e_fila(self):
        self.abrir_serie("CT")
        self.selecionar('input[data-prot="torax_mama"]')
        remover = self.page.locator('[data-oar-x="heart"]')
        with self.page.expect_response(lambda r:r.url.endswith("/previa_da_entrega")):
            remover.evaluate("b => b.click()")
        self.page.locator('[data-oar-volta="heart"]').wait_for()
        self.assertEqual(self.requests[-1]["oar_fora"], ["heart"])
        self.assertFalse(self.chaves("data-oar-volta") & {"bag_bowel_oar", "anus"})
        self.selecionar('input[data-task="breasts"]')
        self.assertTrue(self.page.locator('input.p4-livre-ck').is_checked())
        atual = self.requests[-1]
        self.assertTrue(atual["personalizado_derivado"])
        self.assertEqual(atual["origem_personalizada"]["protocolos"], ["torax_mama"])
        self.assertEqual(atual["tasks"]["breasts"], 0)
        self.assertEqual(atual["oar_fora"], ["heart"])
        self.page.evaluate("""() => {
            el('pasta').value='fantoma'; guardarRascunhoLote();
            LT_RASCUNHO=JSON.parse(sessionStorage.getItem('radai_lote_rascunho_v814'));
            ESCOLHA={}; _ltFim(SERIES, {final:true}, LT_LER,7,'fantoma',{quieto:true});
        }""")
        self.pronto()
        self.assertEqual(self.page.evaluate("payloadDaSerie(SERIES[0])"), atual)
        self.selecionar('input.p4-full-ck')
        self.assertTrue(self.requests[-1]["anatomia_geral_full"])
        self.assertGreater(len(self.chaves()), 25)
        self.selecionar('input.p4-full-ck')
        self.assertNotIn("bag_bowel_oar", self.chaves())
        self.selecionar('input.p4-pp-ck')
        self.assertEqual(self.chaves(), {"urinary_bladder"})
        self.assertEqual(self.requests[-1]["protocolo_proprio"], "estacao-antiga")
        with self.page.expect_response(lambda r:r.url.endswith("/api/lote/enfileirar")):
            self.page.evaluate("mandarParaAFila(SERIES)")
        self.assertEqual(self.queued, [self.requests[-1]])
        self.assertEqual(self.proprio.read_bytes(), self.antes)


if __name__ == "__main__":
    unittest.main(verbosity=2)
