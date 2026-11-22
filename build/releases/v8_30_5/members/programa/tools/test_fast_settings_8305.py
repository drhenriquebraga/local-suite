"""Station settings regression with synthetic RTSTRUCT captures, no patient data."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit

APP = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP))
import radai_config as config
import radai_config_transferencia as transfer
import radai_fast_config as fast
from radai_fast_i18n import LANGS, ROWS


class FastSettings(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.cfg = Path(temp.name) / "radai_watcher.config"
        self.cfg.write_text("DEVICE=cpu\n", encoding="utf-8")

    def save(self, value):
        return transfer.salvar({"valores": {fast.CHAVE: value}}, self.cfg,
                               [fast.CHAVE], {fast.CHAVE: "2"}, {}, "")

    def test_legacy_settings_and_transactional_transfer(self):
        self.assertEqual(fast.nivel_atual(self.cfg), 2)
        old_files = {self.cfg.with_name(config.NOME_DOS_NOMES): b'{"modo":"proprio","nomes":{"A":"B"}}',
                     self.cfg.with_name(config.NOME_DOS_PROTOCOLOS): b'{"versao":1,"protocolos":[]}'}
        for path, contents in old_files.items():
            path.write_bytes(contents)
        def export():
            return transfer.exportar(self.cfg, [fast.CHAVE], "8.30.5", ["configuracao"], {})
        initial = export()
        self.assertEqual(initial["secoes"]["configuracao"], {fast.CHAVE: "2"})
        for level in ("0", "1", "3", "4"):
            self.assertTrue(self.save(level)["ok"])
            self.assertEqual(fast.nivel_atual(self.cfg), int(level))
        before = self.cfg.read_bytes()
        with self.assertRaises((ValueError, OSError)):
            self.save("5")
        self.assertEqual(self.cfg.read_bytes(), before)
        req = {"dados": initial, "secoes": ["configuracao"]}
        req["revisao"] = transfer.transferir(req, self.cfg, [fast.CHAVE], {}, "")["revisao"]
        transfer.transferir(req, self.cfg, [fast.CHAVE], {}, "", aplicar=True)
        self.assertEqual(fast.nivel_atual(self.cfg), 2)
        transfer.desfazer(self.cfg)
        self.assertEqual(fast.nivel_atual(self.cfg), 4)
        for path, contents in old_files.items():
            self.assertEqual(path.read_bytes(), contents)

    def test_preview_endpoints_and_translations(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        app = FastAPI()
        fast.montar(app)
        client = TestClient(app)
        for sample in ("bowel", "thorax"):
            for level in range(5):
                response = client.get(f"/api/fast/preview/{sample}/{level}")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers["content-type"], "image/png")
                self.assertTrue(response.content.startswith(b"\x89PNG"))
        for sample, level in (("test", "0"), ("thorax", "5"), ("bowel", "-1")):
            self.assertEqual(client.get(f"/api/fast/preview/{sample}/{level}").status_code, 404)
        self.assertEqual(len(LANGS), 12)
        self.assertTrue(all(len(row) == len(LANGS) and all(row) for row in ROWS.values()))

    def test_chromium(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.skipTest("Playwright is required for the Chromium checks")
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        import radai_languages
        import radai_panel
        app = FastAPI()
        radai_panel.montar(app, config={"caminho": str(self.cfg), "chaves": [fast.CHAVE],
                                       "padroes": {fast.CHAVE: "2"}})
        client = TestClient(app)
        cfg = client.get("/config")
        self.assertEqual(cfg.status_code, 200)
        import radai_batch
        suite = FastAPI()
        radai_batch.montar(suite)
        batch = TestClient(suite)
        options = {code: radai_batch.opcoes_da_tela(code) for code in ("CT", "MR")}
        for entry in options.values():
            for row in [entry["base_item"], *entry["tasks"]]:
                self.assertTrue(row["figuras"], row["task"])
        ct = options["CT"]
        rows = {row["task"]: row for row in ct["tasks"]}
        for row, sample in ((ct["base_item"], "thorax"), (rows["breasts"], "thorax"),
                            (rows["trunk_cavities"], "bowel")):
            self.assertIn("/api/fast/preview/" + sample + "/2", [fig["url"] for fig in row["figuras"]])
        def serve(route):
            req = route.request
            path = urlsplit(req.url).path
            if path == "/config":
                route.fulfill(status=200, content_type="text/html; charset=utf-8", body=cfg.content)
            elif path == "/lote":
                route.fulfill(status=200, content_type="text/html; charset=utf-8", body=batch.get(path).content)
            elif path == "/api/lote/opcoes":
                modality = parse_qs(urlsplit(req.url).query).get("modalidade", ["CT"])[0]
                route.fulfill(json=options[modality])
            elif path.startswith("/api/lote/ajuda/"):
                resp = batch.get(path)
                route.fulfill(status=resp.status_code, content_type=resp.headers["content-type"], body=resp.content)
            elif path in {"/api/config", "/api/config/estacao/salvar"} or path.startswith("/api/fast/preview/"):
                resp = client.request(req.method, path, content=req.post_data or b"")
                route.fulfill(status=resp.status_code, content_type=resp.headers["content-type"], body=resp.content)
            elif path == radai_languages.ROTA_JS:
                route.fulfill(content_type="application/javascript; charset=utf-8", body=radai_languages.corpo_js())
            elif path.endswith(".js"):
                route.fulfill(content_type="application/javascript", body="")
            else:
                route.fulfill(json={})
        with sync_playwright() as playwright:
            chrome = os.environ.get("RADAI_CHROME", r"C:\Program Files\Google\Chrome\Application\chrome.exe")
            browser = playwright.chromium.launch(headless=True, executable_path=chrome if Path(chrome).is_file() else None)
            try:
                for mobile in (False, True):
                    with self.subTest(mobile=mobile):
                        ctx = browser.new_context(viewport={"width": 390 if mobile else 1400, "height": 900},
                                                  is_mobile=mobile, has_touch=mobile, reduced_motion="reduce")
                        page = ctx.new_page()
                        page.route("**/*", serve)
                        page.goto("http://station.test/config#ps_fast")
                        page.wait_for_function("document.querySelector('#f_FAST_NIVEL')?.disabled===false")
                        slider = page.locator("#f_FAST_NIVEL")
                        self.assertEqual(slider.input_value(), "2")
                        self.assertTrue(slider.is_visible())
                        page.locator("#fast-picture").scroll_into_view_if_needed()
                        page.wait_for_function("document.querySelector('#fast-picture').naturalWidth>100")
                        for i, lang in enumerate(LANGS):
                            page.evaluate("l=>{localStorage.setItem('radai_idioma',l);document.documentElement.lang=l}", lang)
                            page.wait_for_function("s=>document.querySelector('a[href=\"#ps_fast\"] h3').textContent===s", arg=ROWS["title"][i])
                            self.assertEqual(page.locator("#fast-help").get_attribute("aria-label"), ROWS["help"][i])
                        page.evaluate("localStorage.setItem('radai_idioma','pt-BR');document.documentElement.lang='pt-BR'")
                        outputs = os.environ.get("RADAI_FAST_SCREENSHOT_DIR")
                        if outputs:
                            target = Path(outputs)
                            target.mkdir(parents=True, exist_ok=True)
                            page.locator("#ps_fast").screenshot(path=str(target / f"fast-card-{'mobile' if mobile else 'desktop'}.png"))
                        stop = page.locator('[data-fast-level="0"]')
                        if mobile:
                            stop.tap()
                        else:
                            stop.hover()
                            self.assertTrue(page.locator("#fast-tip-0").is_visible())
                            stop.focus()
                            stop.press("Enter")
                        self.assertEqual(slider.input_value(), "0")
                        self.assertTrue(page.locator("#fast-tip-0").is_visible())
                        page.locator('[data-fast-sample="bowel"]').click()
                        page.wait_for_function("document.querySelector('#fast-picture').src.endsWith('/bowel/0')")
                        page.locator("#fast-help").click()
                        dialog = page.locator("#fast-dialog")
                        self.assertTrue(dialog.is_visible())
                        for img in dialog.locator("[data-fast-example] img").all():
                            img.scroll_into_view_if_needed()
                            self.assertTrue(img.get_attribute("alt"))
                            img.evaluate("i=>i.decode()")
                        self.assertLessEqual(dialog.bounding_box()["width"], page.viewport_size["width"])
                        if outputs:
                            dialog.locator("header").scroll_into_view_if_needed()
                            dialog.screenshot(path=str(target / f"fast-help-{'mobile' if mobile else 'desktop'}.png"))
                        page.keyboard.press("Escape")
                        self.assertFalse(dialog.is_visible())
                        self.assertTrue(page.locator("#fast-help").evaluate("e=>e===document.activeElement"))
                        page.locator("#fast-zoom").click()
                        self.assertTrue(page.locator("#fast-zoom-image").is_visible())
                        page.locator("#fast-close").click()
                        with page.expect_response(lambda res: res.url.endswith("/api/config/estacao/salvar")) as saved:
                            page.locator("#btsalvar").click()
                        self.assertTrue(saved.value.json()["ok"])
                        self.assertEqual(fast.nivel_atual(self.cfg), 0)
                        page.reload()
                        page.wait_for_function("!document.querySelector('#f_FAST_NIVEL').disabled && document.querySelector('#f_FAST_NIVEL').value==='0'")
                        slider.focus()
                        slider.press("ArrowRight")
                        self.assertEqual(slider.input_value(), "1")
                        page.locator("#fast-reset").click()
                        with page.expect_response(lambda res: res.url.endswith("/api/config/estacao/salvar")):
                            page.locator("#btsalvar").click()
                        self.assertEqual(fast.nivel_atual(self.cfg), 2)
                        if not mobile:
                            page.goto("http://station.test/lote")
                            page.wait_for_function("typeof OPC!=='undefined' && OPC.CT && OPC.MR")
                            page.evaluate("""() => {
                               const serie = {modalidade:'CT',pasta:'phantom',uid:'1.2.3',cortes:100,nome:'Fantoma'};
                               SERIES=[serie];porNoCarrinho(serie,true);sincronizarIncl();pintarTabela();
                               psAbrir('cx2',true);
                            }""")
                            mode = page.locator('.md-cx [data-v="auto"]')
                            errors = []
                            page.on("pageerror", lambda err: errors.append(str(err)))
                            mode.focus()
                            mode.press("ArrowRight")
                            self.assertEqual(page.locator('.md-sel').input_value(), "perso", page.locator('.md-cx').inner_html())
                            finish = page.locator('.p4-perfil [data-v="padrao"]')
                            self.assertEqual(finish.count(), 1, (errors, page.locator('#perso_0').count(),
                                                                page.locator('.p4-perfil').all_text_contents()))
                            finish.focus()
                            finish.press("ArrowRight")
                            self.assertEqual(page.locator('.p4-acab').input_value(), "fast")
                            self.assertEqual(page.locator('.md-cx [data-ui-balao],.p4-perfil [data-ui-balao]').count(), 0)
                            task_help = page.locator('button[data-p4-aj="task"][data-cod="breasts"]')
                            task_help.focus()
                            task_help.press("Enter")
                            img = page.locator('.tk-modal-ficha img[src$="/thorax/2"]')
                            img.scroll_into_view_if_needed(timeout=4000)
                            img.evaluate("i=>i.decode()")
                            self.assertTrue(img.get_attribute("alt"))
                            page.keyboard.press("Escape")
                        ctx.close()
            finally:
                browser.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
