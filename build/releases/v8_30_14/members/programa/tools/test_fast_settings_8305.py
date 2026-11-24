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
        from unittest.mock import patch
        from base64 import b64decode
        # One valid 1x1 PNG exercises the packaged gallery route without a model.
        pixel = b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/2ioAAAAASUVORK5CYII=")
        preview_dir = self.cfg.parent / "data/fast_previews"
        preview_dir.mkdir(parents=True)
        for sample in fast.AMOSTRAS:
            for level in range(5):
                (preview_dir / f"{sample}-{level}.png").write_bytes(pixel)
        # The gallery downloads separately from the lightweight installer.
        with patch.object(fast, "__file__", str(self.cfg.parent / "radai_fast_config.py")):
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
        # The public gallery downloads separately. This fixture only needs a decodable PNG.
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+kMFsAAAAASUVORK5CYII=")
        (root/"thorax-2.png").write_bytes(png)
        doc = {"case_id":"s0102","version":3,"protocol":"sbrt_lung","total_slices":4,"firstSlice":1,"lastSlice":4,
               "positionsMm":[10,12,14,16],"orientation":"axial-radiological","superiorAt":"last",
               "tileWidth":2,"tileHeight":2,"columns":4,"rowsPerPage":1,"profiles":{}}
        for idx, (name,(mm,finish)) in enumerate(fast.STUDY_FAST.items()):
            filename=f"study-{name}-stack-001.webp"
            (root/filename).write_bytes(webp)
            estimated = {"medio": None, "ultra": 128.3}.get(name, 120.3 + idx)
            doc["profiles"][name]={"mm":mm,"effective_mm":mm,"base_attempts_mm":[mm],"finish":finish,"body_mm":1.5 if name=="ultra" else 6,"source":"RTSTRUCT_STUDY","pages":[filename],
                "rois":{"41":{"name":"Ribs_ai", "color":[1,128,255]},
                        "304":{"name":"Custom OAR "+name, "color":[233,8,31]}},
                "labelsBySlice":[[],["41","304"],["304"],["41"]],"write_s":3.1+idx,
                "roi_stats":{"41":{"points":12000+idx},"304":{"points":345}},"total_vertices":12345+idx,
                "estimated_s":estimated, "time_s":93.2 if name=="maximo" else None,
                "used_cache":name!="maximo"}
        doc["requested_rois"] = ["Ribs_ai", "OAR sem máscara", *["Custom OAR " + n for n in fast.STUDY_FAST]]
        doc.update(fast.ORIGEM_STUDY_PUBLICO,author="Jakob Wasserthal, University Hospital Basel")
        (root/"tc-study.json").write_text(json.dumps(doc),encoding="utf8")
        refs={"study_public":dict(fast.ORIGEM_STUDY_PUBLICO, version=doc["version"])}
        (root.parent/"fast_preview_sources.json").write_text(json.dumps(refs),encoding="utf8")
        return root,doc

    def test_preview_requires_the_native_grid_for_each_effort(self):
        import json
        root, doc = self.study_fixture()
        candidate = doc["profiles"]["leve"]
        for effective, attempts in (("3", ["6", "3"]), ("6", ["6", "3"]), (None, None)):
            with self.subTest(effective=effective, attempts=attempts):
                candidate.update(effective_mm=effective, base_attempts_mm=attempts)
                (root/"tc-study.json").write_text(json.dumps(doc), encoding="utf8")
                self.assertEqual(fast.ler_study_fast(root), {})
                self.assertNotIn("leve", fast.ler_study_fast(root, completo=False)["profiles"])

    def test_exported_vertex_counts_match_roi_totals(self):
        import json
        root,doc=self.study_fixture()
        doc["protocol"]="demo_thorax_abdomen"
        doc["profiles"]["extra"]["total_vertices"] += 1
        del doc["profiles"]["maximo"]["roi_stats"]["41"]
        del doc["profiles"]["ultra"]["roi_stats"]
        (root/"tc-study.json").write_text(json.dumps(doc),encoding="utf8")
        result=fast.dados_para_o_visor(fast.ler_study_fast(root))["profiles"]
        self.assertEqual(result["alto"]["total_vertices"],12347)
        for profile in ("extra","maximo","ultra"):
            self.assertNotIn("total_vertices",result[profile])

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

    def test_effort_without_gallery_in_chromium(self):
        from playwright.sync_api import sync_playwright, expect
        from radai_fast_ui import page as effort_page
        html = effort_page('<html lang="pt-BR"><head></head><body><main></main></body></html>', caso=True)
        with sync_playwright() as playwright:
            chrome = Path(os.environ.get("RADAI_CHROME", r"C:\Program Files\Google\Chrome\Application\chrome.exe"))
            browser = playwright.chromium.launch(headless=True, executable_path=str(chrome) if chrome.is_file() else None)
            try:
                page = browser.new_page(viewport={"width": 420, "height": 760})
                page.route("http://esforco.test/", lambda r: r.fulfill(content_type="text/html; charset=utf-8",body=html))
                page.route("**/api/fast/study", lambda r: r.fulfill(status=503,body="{}"))
                page.goto("http://esforco.test/")
                page.evaluate("""() => {
                    document.querySelector('main').innerHTML=radaiMiniEsforco(1,'maximo')+radaiMiniEsforco(2,'leve');
                    window.escolhas=[];
                    addEventListener('radai-esforco-caso',e=>escolhas.push(e.detail));
                }""")
                mini=page.locator('.effort-miniform[data-series="1"]')
                other=page.locator('.effort-miniform[data-series="2"] .effort-input')
                rail=mini.locator('.effort-input')
                rail.press("End")
                expect(rail).to_have_attribute("aria-valuetext","Ultra")
                page.keyboard.press("Home")
                page.keyboard.press("ArrowRight")
                expect(rail).to_have_attribute("aria-valuetext","Médio")
                expect(rail).to_be_focused()
                expect(other).to_have_attribute("aria-valuetext","Leve")
                self.assertTrue(page.evaluate("escolhas.every(e=>e.indice===1)"))
                rect=rail.bounding_box()
                x,y=rect["x"],rect["y"]+rect["height"]/2
                begin=x+14+(rect["width"]-28)/5
                end=x+14+3*(rect["width"]-28)/5
                count=page.evaluate("escolhas.length")
                page.mouse.move(begin,y)
                page.mouse.down()
                # Between stops the thumb follows the pointer, without committing a case.
                free=x+14+.47*(rect["width"]-28)
                page.mouse.move(free,y,steps=5)
                middle=mini.locator(".t-mslider-thumb").bounding_box()
                self.assertAlmostEqual(middle["x"]+middle["width"]/2,free,delta=1.5)
                self.assertEqual(page.evaluate("escolhas.length"),count)
                page.mouse.move(end,y,steps=7)
                page.mouse.up()
                expect(rail).to_have_attribute("aria-valuetext","Extra")
                self.assertEqual(page.evaluate("escolhas.length"),count+1)
                expect(mini.locator(".effort-was")).to_have_count(0,timeout=1800)
                thumb=mini.locator(".effort-thumb").bounding_box()
                self.assertAlmostEqual(thumb["x"]+thumb["width"]/2,end,delta=1.5)
                # A cancelled gesture must return to the original choice.
                count=page.evaluate("escolhas.length")
                page.mouse.down()
                page.mouse.move(x+18,y)
                rail.evaluate("el=>el.dispatchEvent(new PointerEvent('pointercancel',{bubbles:true,pointerId:1}))")
                page.mouse.up()
                self.assertEqual(page.evaluate("escolhas.length"),count)
                expect(rail).to_have_attribute("aria-valuetext","Extra")
                mini.locator(".effort-help").click()
                expect(page.locator(".fast-empty")).to_be_visible()
                comparison=page.locator(".fast-pick .effort-input")
                comparison.press("End")
                expect(page.locator('[data-study-card="ultra"]')).to_have_attribute("aria-pressed","true")
                expect(rail).to_have_attribute("aria-valuetext","Extra")
                page.locator("#effort-apply").click()
                expect(rail).to_have_attribute("aria-valuetext","Ultra")
                page.evaluate("document.documentElement.lang='ar'; document.documentElement.dir='rtl'")
                expect(rail).to_have_attribute("aria-valuetext",ROWS["ultra"][LANGS.index("ar")])
                rail.press("Home")
                rail.press("ArrowLeft")
                expect(rail).to_have_attribute("aria-valuetext",ROWS["medio"][LANGS.index("ar")])
                page.emulate_media(reduced_motion="reduce")
                rail.press("End")
                expect(mini.locator(".effort-was")).to_have_count(0)
                self.assertEqual(mini.locator(".effort-thumb").evaluate("el=>getComputedStyle(el).transitionDuration"),"0s")
            finally:
                browser.close()

    def test_chromium(self):
        from unittest.mock import patch
        from playwright.sync_api import sync_playwright, expect
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
                        ctx.add_init_script("localStorage.setItem('radai_idioma','pt-BR')")
                        page=ctx.new_page()
                        page.route("**/*",serve)
                        # The demonstration deep link must not hijack station routes or anchors.
                        page.goto("http://127.0.0.1/config?slice=1#ps_fast")
                        page.locator("#effort-config-open").click()
                        page.locator("#fast-canvas").wait_for(state="visible")
                        self.assertEqual(page.locator("#fast-slice").input_value(), "2")
                        page.evaluate("document.documentElement.lang='pt-BR'")
                        page.wait_for_function("s=>document.querySelector('#fast-time-basis').textContent===s",arg=ROWS["relativeBasis"][0])
                        help_button=page.locator("#fast-info-toggle")
                        info=page.locator("#fast-info")
                        detail=info.locator("#fast-help")
                        expect(page.locator("#effort-view canvas")).to_have_count(1)
                        expect(help_button).to_have_attribute("aria-controls","fast-info")
                        expect(help_button).to_have_attribute("aria-expanded","false")
                        expect(info).to_be_hidden()
                        expect(page.locator("#fast-credits, #effort-model-references").first).to_be_hidden()
                        expect(page.locator("#fast-time-basis")).to_be_hidden()
                        help_button.focus()
                        help_button.press("Enter")
                        expect(help_button).to_have_attribute("aria-expanded","true")
                        expect(info).to_be_visible()
                        self.assertFalse(detail.evaluate("e=>e.open"))
                        detail.locator("summary").press("Enter")
                        self.assertTrue(detail.evaluate("e=>e.open"))
                        self.assertTrue(page.locator("#effort-apply").is_hidden())
                        comparison=page.locator(".fast-pick .effort-input")
                        expect(comparison).to_have_attribute("aria-valuetext",ROWS["maximo"][0])
                        comparison.press("End")
                        expect(page.locator('[data-study-card="ultra"]')).to_have_attribute("aria-pressed","true")
                        comparison.press("Home")
                        expect(page.locator(".fast-pick .effort-name")).to_have_text(ROWS["leve"][0])
                        expect(page.locator(".fast-pick .effort-was")).to_have_count(0)
                        self.assertEqual(page.locator("[data-study-card]").count(),6)
                        self.assertEqual(page.locator('[data-study-card="maximo"] .fast-clock').inner_text(),"100%")
                        self.assertEqual(page.locator('[data-study-card="medio"] .fast-clock').inner_text(),"—")
                        for effort, key in (("leve","relativeSaving"),("extra","relativeNear"),("ultra","relativeAdded")):
                            page.locator(f'[data-study-card="{effort}"]').click()
                            expect(comparison).to_have_attribute("aria-valuetext",ROWS[effort][0])
                            expect(page.locator("#fast-profile-timing")).to_contain_text(ROWS[key][0])
                        page.locator('[data-study-card="medio"]').click()
                        self.assertEqual(page.locator("#fast-slice").input_value(),"2")
                        self.assertIn("Ribs_ai",page.locator("#fast-view-legend").inner_text())
                        self.assertEqual(page.locator("#effort-model-references").count(),1)
                        self.assertEqual(page.locator("#effort-model-references").get_attribute("href"),"/bibliografia#modelos")
                        self.assertIn("s0102/ct.nii.gz",page.locator("#fast-credits").inner_text())
                        self.assertIn("10.5281/zenodo.10047292",page.locator("#fast-credits").inner_text())
                        for j,lang in enumerate(LANGS):
                            page.evaluate("l=>{document.documentElement.lang=l}",lang)
                            page.wait_for_function("s=>document.querySelector('#effort-save').textContent===s",arg=ROWS["savePref"][j])
                            expect(comparison).to_have_attribute("aria-label",ROWS["title"][j])
                            expect(comparison).to_have_attribute("aria-valuetext",ROWS["medio"][j])
                            self.assertEqual(page.locator('#fast-time-basis').inner_text(),ROWS["relativeBasis"][j])
                            self.assertEqual(page.locator('.fast-tps-note').inner_text(),ROWS["tpsVertices"][j])
                            self.assertIn(ROWS["vertexCount"][j],page.locator('[data-study-card="alto"] .fast-vertices').inner_text())
                            self.assertIn(ROWS["relativeMissing"][j],page.locator("#fast-profile-timing").inner_text())
                            self.assertEqual(page.locator("#effort-model-references").inner_text(),ROWS["weightsRefs"][j])
                            self.assertIn(ROWS["zipDataset"][j],page.locator("#fast-credits").inner_text())
                        page.evaluate("document.documentElement.lang='pt-BR'")
                        page.locator('[data-study-card="leve"]').click()
                        page.locator("#fast-canvas").wait_for(state="visible")
                        self.assertIn("OAR sem máscara", page.locator("#fast-missing-rois").inner_text())
                        self.assertIn("Custom OAR maximo", page.locator("#fast-missing-rois").inner_text())
                        self.assertNotIn("Ribs_ai", page.locator("#fast-missing-rois").inner_text())
                        self.assertIn("0%", page.locator('[data-study-card="alto"] .fast-vertices').inner_text())
                        self.assertEqual(page.locator("#fast-profile-rois").inner_text(),"ROIs no STUDY · 2 de 8 solicitadas")
                        self.assertEqual(page.locator("#fast-profile-vertices").inner_text(),"Vértices · 12.345 (0% em relação ao Máximo)")
                        area=page.locator(".fast-viewport")
                        area.focus()
                        area.press("ArrowRight")
                        self.assertEqual(page.locator("#fast-slice").input_value(),"3")
                        expect(page.locator("#fast-view-legend")).not_to_contain_text("Custom OAR maximo")
                        page.locator('[data-study-card="maximo"]').click()
                        expect(page.locator("#fast-view-legend")).to_have_text("Custom OAR maximo")
                        self.assertEqual(page.locator("#fast-slice").input_value(),"3")
                        page.locator('[data-study-card="leve"]').click()
                        expect(page.locator("#fast-view-legend")).to_have_text("Custom OAR leve")
                        self.assertEqual(page.locator("#fast-slice").input_value(),"3")
                        self.assertEqual(page.locator("#fast-view-legend").inner_text(),"Custom OAR leve")
                        self.assertEqual(page.locator(".fast-in-plane").first.inner_text(),"Estruturas neste corte · 1")
                        self.assertNotIn("ESFORCO_PADRAO=leve",self.cfg.read_text(encoding="utf8"))
                        if info.is_visible():
                            help_button.click()
                        expect(info).to_be_hidden()
                        with page.expect_response(lambda r:r.url.endswith("/api/config/estacao/salvar")):
                            page.locator("#effort-save").click()
                        page.wait_for_function("s=>document.getElementById('effort-status').textContent===s",arg=ROWS["saved"][0])
                        self.assertIn("ESFORCO_PADRAO=leve",self.cfg.read_text(encoding="utf8"))
                        page.keyboard.press("Escape")
                        page.locator("#effort-config-open").click()
                        self.assertEqual(page.locator('[data-study-card="leve"]').get_attribute("aria-pressed"),"true")
                        expect(info).to_be_hidden()
                        expect(page.locator("#fast-slice")).to_have_value("2")
                        page.keyboard.press("Escape")
                        if not mobile:
                            page.goto("http://127.0.0.1/lote")
                            page.wait_for_function("typeof OPC!=='undefined' && OPC.CT && OPC.MR")
                            page.evaluate("""() => {
                               const serie = {modalidade:'CT',pasta:'phantom',uid:'1.2.3',cortes:100,nome:'Fantoma'};
                               SERIES=[serie];porNoCarrinho(serie,true);sincronizarIncl();pintarTabela();
                               psAbrir('cx2',true);
                            }""")
                            self.assertEqual(page.locator('#tab .effort-input').count(),0)
                            mode = page.locator('.md-cx [data-v="auto"]')
                            errors = []
                            page.on("pageerror", lambda err: errors.append(str(err)))
                            mode.focus()
                            mode.press("ArrowRight")
                            self.assertEqual(page.locator('.md-sel').input_value(), "perso", page.locator('.md-cx').inner_html())
                            effort=page.locator(".effort-miniform .effort-input")
                            self.assertEqual(effort.count(),1)
                            self.assertEqual(page.locator(".effort-miniform .effort-stops i").count(),6)
                            effort.press("End")
                            page.keyboard.press("ArrowLeft")
                            page.keyboard.press("ArrowLeft")
                            expect(effort).to_be_focused()
                            self.assertEqual(page.evaluate("payloadDaSerie(SERIES[0]).esforco"),"extra")
                            capture=os.environ.get("RADAI_TEST_SCREENSHOT_ESFORCO")
                            if capture:
                                effort.evaluate("e=>e.blur()")
                                page.locator(".effort-miniform").screenshot(path=capture)
                            page.locator(".effort-help").click()
                            page.locator('[data-study-card="ultra"]').click()
                            self.assertEqual(page.evaluate("payloadDaSerie(SERIES[0]).esforco"),"extra")
                            page.locator("#effort-apply").click()
                            expect(effort).to_have_attribute("aria-valuetext",ROWS["ultra"][0])
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
