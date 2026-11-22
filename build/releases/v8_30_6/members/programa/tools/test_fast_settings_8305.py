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
        for sample in fast.AMOSTRAS:
            for level in range(5):
                response = client.get(f"/api/fast/preview/{sample}/{level}")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers["content-type"], "image/png")
                self.assertTrue(response.content.startswith(b"\x89PNG"))
        for sample, level in (("test", "0"), ("thorax", "5"), ("bowel", "-1")):
            self.assertEqual(client.get(f"/api/fast/preview/{sample}/{level}").status_code, 404)
        self.assertEqual(len(LANGS), 12)
        self.assertTrue(all(len(row) == len(LANGS) and all(row) for row in ROWS.values()))

    def test_gallery_never_uses_station_data(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from unittest.mock import patch
        app=FastAPI()
        fast.montar(app)
        client=TestClient(app,base_url="http://127.0.0.1",client=("127.0.0.1",5555))
        with patch("radai_archive.raiz",side_effect=AssertionError("Accessed station case data")):
            self.assertNotEqual(client.get("/api/fast/galeria").json()["upper"].get("kind"),"station_ct")
            self.assertEqual(client.get("/api/fast/preview/upper/2?local=true").status_code,404)
            self.assertEqual(client.get("/api/fast/study/leve/1?local=true").status_code,404)
            self.assertNotEqual(client.get("/api/fast/study").json().get("kind"),"station_ct")

    def test_ct_resolution_migration(self):
        from radai_velocidade_tc import CHAVE, PADRAO, mm_atual
        self.cfg.write_text("DEVICE=cpu\nFAST_NIVEL=3\n", encoding="utf-8")
        keys = [fast.CHAVE,CHAVE]
        defaults = {CHAVE:PADRAO,fast.CHAVE:"2"}
        self.assertEqual(mm_atual(self.cfg), "1.5")
        initial = transfer.exportar(self.cfg, keys, "teste", ["configuracao"], {})
        self.assertEqual(initial["secoes"]["configuracao"], {fast.CHAVE:"3",CHAVE:"1.5"})
        for mm in ("3", "6", "1.5", "6"):
            self.assertTrue(transfer.salvar({"valores":{CHAVE:mm}},self.cfg,keys,defaults,{},"")["ok"])
            self.assertEqual(mm_atual(self.cfg), mm)
            self.assertEqual(fast.nivel_atual(self.cfg), 3)
        contents = self.cfg.read_bytes()
        with self.assertRaises((ValueError,OSError)):
            transfer.salvar({"valores":{CHAVE:"4"}},self.cfg,keys,defaults,{},"")
        self.assertEqual(contents,self.cfg.read_bytes())
        del initial["secoes"]["configuracao"][CHAVE]
        req = {"dados":initial,"secoes":["configuracao"]}
        req["revisao"] = transfer.transferir(req,self.cfg,keys,{},"")["revisao"]
        transfer.transferir(req,self.cfg,keys,{},"",aplicar=True)
        self.assertEqual(mm_atual(self.cfg), "6")
        self.assertEqual(fast.nivel_atual(self.cfg),3)


    def test_relative_time_uses_comparable_estimates_only(self):
        prices = {"maximo": 100, "leve": 78.54, "medio": 77.50, "alto": 99.96,
                  "extra": 99.94, "ultra": 114.66}
        raw = {"profiles": {k: {"estimated_s": v, "time_s": 8, "write_s": 2} for k,v in prices.items()}}
        def fractions():
            return {k:p["tempo_relativo_decimos"] for k,p in fast.dados_para_o_visor(raw)["profiles"].items()}
        self.assertEqual(fractions(), {"maximo":1000,"leve":785,"medio":775,"alto":1000,"extra":999,"ultra":1147})
        del raw["profiles"]["medio"]["estimated_s"]
        self.assertIsNone(fractions()["medio"])
        for reference in (None, 0, float("nan")):
            raw["profiles"]["maximo"]["estimated_s"] = reference
            self.assertEqual(set(fractions().values()), {None})
        del raw["profiles"]["maximo"]
        self.assertEqual(set(fractions().values()), {None})

    def study_fixture(self):
        import base64
        import json
        root = self.cfg.parent / "fake-app" / "data" / "fast_previews"
        root.mkdir(parents=True,exist_ok=True)
        webp = base64.b64decode("UklGRiAAAABXRUJQVlA4TBMAAAAvB0AAAB8QIxPzH1Y4lH5E/0MBAA==")
        (root/"thorax-2.png").write_bytes((APP/"data"/"fast_previews"/"thorax-2.png").read_bytes())
        doc = {"case_id":"s0102","version":3,"protocol":"sbrt_lung","total_slices":4,"firstSlice":1,"lastSlice":4,
               "positionsMm":[10,12,14,16],"orientation":"axial-radiological","superiorAt":"last",
               "tileWidth":2,"tileHeight":2,"columns":4,"rowsPerPage":1,"profiles":{}}
        for idx, (name,(mm,finish)) in enumerate(fast.STUDY_FAST.items()):
            filename=f"study-{name}-stack-001.webp"
            (root/filename).write_bytes(webp)
            doc["profiles"][name]={"mm":mm,"finish":finish,"body_mm":1.5 if name=="ultra" else 6,"source":"RTSTRUCT_STUDY","pages":[filename],
                "rois":{"41":{"name":"Ribs_ai", "color":[1,128,255]},
                        "304":{"name":"Custom OAR "+name, "color":[233,8,31]}},
                "labelsBySlice":[[],["41","304"],["304"],["41"]],"write_s":3.1+idx,
                "estimated_s":120.3+idx if idx!=1 else None, "time_s":93.2 if name=="maximo" else None,
                "used_cache":name!="maximo"}
        doc.update(fast.ORIGEM_STUDY_PUBLICO,author="Jakob Wasserthal, University Hospital Basel")
        (root/"tc-study.json").write_text(json.dumps(doc),encoding="utf8")
        refs={"study_public":dict(fast.ORIGEM_STUDY_PUBLICO)}
        (root.parent/"fast_preview_sources.json").write_text(json.dumps(refs),encoding="utf8")
        return root,doc

    def test_study_complete_protocol_masks_and_privacy(self):
        import json
        from unittest.mock import patch
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        root,doc=self.study_fixture()
        self.assertEqual(set(fast.ler_study_fast(root)["profiles"]),set(fast.STUDY_FAST))
        self.assertTrue(fast.estudo_de_referencia(root,{"study_public":fast.ORIGEM_STUDY_PUBLICO}))
        self.assertFalse(fast.estudo_de_referencia(root,{"study_public":dict(fast.ORIGEM_STUDY_PUBLICO,source_url="https://example.org")}))
        from radai_fast_ui import visor_estatico
        estatico=visor_estatico(fast.ler_study_fast(root))
        self.assertNotIn("/api/fast/",estatico)
        for token in ("estimated_s","time_s","write_s"):
            self.assertNotIn(token,estatico)
        self.assertIn("study-leve-stack-001.webp",estatico)
        self.assertEqual(estatico.count('data-study-card="'),6)
        app=FastAPI()
        fast.montar(app)
        local=TestClient(app,base_url="http://127.0.0.1",client=("127.0.0.1",5555))
        remote=TestClient(app,base_url="http://127.0.0.1",client=("192.0.2.4",5556))
        self.assertEqual(local.get("/api/fast/study/leve/1?local=true").status_code,404)
        self.assertEqual(remote.get("/api/fast/study/leve/1?local=true").status_code,404)
        doc["profiles"]["leve"]["finish"]=4
        doc["profiles"]["medio"]["pages"]=["../frame.webp"]
        doc["profiles"]["alto"]["labelsBySlice"][0]=["999"]
        (root/"tc-study.json").write_text(json.dumps(doc),encoding="utf8")
        self.assertEqual(fast.ler_study_fast(root),{})
        actual=fast.ler_study_fast(root,completo=False)["profiles"]
        self.assertEqual(set(actual),{"extra","maximo","ultra"})
        self.assertEqual(actual["maximo"]["rois"]["41"]["color"],[1,128,255])
        doc["case_id"]="local"
        (root/"tc-study.json").write_text(json.dumps(doc),encoding="utf8")
        self.assertEqual(fast.ler_study_fast(root,completo=False),{})

    def test_chromium(self):
        from unittest.mock import patch
        from playwright.sync_api import sync_playwright
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from radai_velocidade_tc import CHAVE, PADRAO, mm_atual
        import radai_languages
        import radai_panel
        root,_=self.study_fixture()
        self.cfg.write_text("DEVICE=cpu\nFAST_NIVEL=2\n",encoding="utf-8")
        patcher = patch.object(fast,"__file__",str(root.parent.parent/"radai_fast_config.py"))
        patcher.start()
        self.addCleanup(patcher.stop)
        app = FastAPI()
        radai_panel.montar(app, config={"caminho":str(self.cfg),"chaves":[fast.CHAVE,CHAVE,"ESFORCO_PADRAO"],
                                       "padroes":{fast.CHAVE:"2",CHAVE:PADRAO,"ESFORCO_PADRAO":"maximo"}})
        client = TestClient(app,base_url="http://127.0.0.1",client=("127.0.0.1",6543))
        cfg = client.get("/config")
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
            elif path in {"/api/config", "/api/config/estacao/salvar"} or path.startswith("/api/fast/"):
                resp = client.request(req.method, req.url, content=req.post_data or b"")
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
                for mobile in (False,True):
                    with self.subTest(mobile=mobile):
                        self.cfg.write_text("DEVICE=cpu\nFAST_NIVEL=2\n",encoding="utf-8")
                        ctx=browser.new_context(viewport={"width":390 if mobile else 1400,"height":900},is_mobile=mobile,has_touch=mobile,reduced_motion="reduce",locale="pt-BR")
                        page=ctx.new_page()
                        page.route("**/*",serve)
                        page.goto("http://127.0.0.1/config#ps_fast")
                        page.locator("#effort-config-open").click()
                        page.locator("#fast-canvas").wait_for(state="visible")
                        page.evaluate("document.documentElement.lang='pt-BR'")
                        page.wait_for_function("s=>document.querySelector('#fast-time-basis').textContent===s",arg=ROWS["relativeBasis"][0])
                        self.assertTrue(page.locator("#effort-apply").is_hidden())
                        self.assertEqual(page.locator("[data-study-card]").count(),6)
                        self.assertEqual(page.locator('[data-study-card="maximo"] .fast-clock').inner_text(),"100%")
                        self.assertEqual(page.locator('[data-study-card="medio"] .fast-clock').inner_text(),"—")
                        self.assertIn(ROWS["relativeSaving"][0],page.locator('[data-study-card="leve"]').inner_text())
                        self.assertIn(ROWS["relativeAdded"][0],page.locator('[data-study-card="ultra"]').inner_text())
                        self.assertEqual(page.locator("#fast-slice").input_value(),"2")
                        self.assertIn("Ribs_ai",page.locator("#fast-view-legend").inner_text())
                        self.assertEqual(page.locator("#effort-model-references").count(),1)
                        self.assertEqual(page.locator("#effort-model-references").get_attribute("href"),"/bibliografia#modelos")
                        self.assertIn("s0102/ct.nii.gz",page.locator("#fast-credits").inner_text())
                        self.assertIn("10.5281/zenodo.10047292",page.locator("#fast-credits").inner_text())
                        for j,lang in enumerate(LANGS):
                            page.evaluate("l=>{document.documentElement.lang=l}",lang)
                            page.wait_for_function("s=>document.querySelector('#effort-save').textContent===s",arg=ROWS["savePref"][j])
                            self.assertEqual(page.locator('#fast-time-basis').inner_text(),ROWS["relativeBasis"][j])
                            self.assertEqual(page.locator('[data-study-card="medio"] .fast-clock-type').inner_text(),ROWS["relativeMissing"][j])
                            self.assertEqual(page.locator("#effort-model-references").inner_text(),ROWS["weightsRefs"][j])
                            self.assertIn(ROWS["zipDataset"][j],page.locator("#fast-credits").inner_text())
                        page.evaluate("document.documentElement.lang='pt-BR'")
                        page.locator('[data-study-card="leve"]').click()
                        page.locator("#fast-reference-canvas").wait_for(state="visible")
                        self.assertEqual(page.locator('[data-study-card="leve"] .fast-roi-count').inner_text(),"ROIs no STUDY · 2")
                        area=page.locator(".fast-viewport")
                        area.focus()
                        area.press("ArrowRight")
                        self.assertIn("Custom OAR maximo",page.locator("#fast-reference-legend").inner_text())
                        self.assertEqual(page.locator("#fast-view-legend").inner_text(),"Custom OAR leve")
                        self.assertEqual(page.locator(".fast-in-plane").first.inner_text(),"Estruturas neste corte · 1")
                        self.assertNotIn("ESFORCO_PADRAO=leve",self.cfg.read_text(encoding="utf8"))
                        with page.expect_response(lambda r:r.url.endswith("/api/config/estacao/salvar")):
                            page.locator("#effort-save").click()
                        page.wait_for_function("s=>document.getElementById('effort-status').textContent===s",arg=ROWS["saved"][0])
                        self.assertIn("ESFORCO_PADRAO=leve",self.cfg.read_text(encoding="utf8"))
                        page.keyboard.press("Escape")
                        page.locator("#effort-config-open").click()
                        self.assertEqual(page.locator('[data-study-card="leve"]').get_attribute("aria-pressed"),"true")
                        page.keyboard.press("Escape")
                        if not mobile:
                            page.goto("http://127.0.0.1/lote")
                            page.wait_for_function("typeof OPC!=='undefined' && OPC.CT && OPC.MR")
                            page.evaluate("""() => {
                               const serie = {modalidade:'CT',pasta:'phantom',uid:'1.2.3',cortes:100,nome:'Fantoma'};
                               SERIES=[serie];porNoCarrinho(serie,true);sincronizarIncl();pintarTabela();
                               psAbrir('cx2',true);
                            }""")
                            self.assertEqual(page.locator('[data-esforco-auto] .effort-trigger').count(),1)
                            mode = page.locator('.md-cx [data-v="auto"]')
                            errors = []
                            page.on("pageerror", lambda err: errors.append(str(err)))
                            mode.focus()
                            mode.press("ArrowRight")
                            self.assertEqual(page.locator('.md-sel').input_value(), "perso", page.locator('.md-cx').inner_html())
                            effort=page.locator(".effort-trigger")
                            self.assertEqual(effort.count(),1)
                            effort.press("ArrowDown")
                            self.assertEqual(page.locator("#effort-list [role=option]").count(),6)
                            page.keyboard.press("Escape")
                            effort.click()
                            page.locator('#effort-list [data-effort="extra"]').click()
                            self.assertEqual(page.evaluate("payloadDaSerie(SERIES[0]).esforco"),"extra")
                            page.locator(".effort-help").click()
                            page.locator('[data-study-card="ultra"]').click()
                            self.assertEqual(page.evaluate("payloadDaSerie(SERIES[0]).esforco"),"extra")
                            page.locator("#effort-apply").click()
                            self.assertIn("Ultra",effort.inner_text())
                            self.assertIn("ESFORCO_PADRAO=leve",self.cfg.read_text(encoding="utf8"))
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
