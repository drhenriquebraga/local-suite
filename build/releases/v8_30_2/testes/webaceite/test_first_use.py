"""Verify the first-use agreement in a disposable research station and headless Chrome."""
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from playwright.sync_api import sync_playwright
import uvicorn

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "programa/app"))


def check_previous_receipts(c):
    points = [key for key, _, _ in c.PONTOS]
    catalog = c.catalogo_termos.catalogo()[0]
    groups = c.catalogo_termos.grupos_opcionais()
    old = c.montar_registro("QA", points, catalog, True, groups)
    old.update(versao="2.9", impressao=c.IMPRESSOES_PUBLICADAS["2.9"], quando="2026-11-21 08:00:00")
    path = c._caminho()
    path.parent.mkdir(parents=True)
    def set_old(**changes):
        raw = json.dumps(dict(old, **changes)).encode()
        path.write_bytes(raw)
        return raw
    raw = set_old()
    assert c.aceito() and c.ferramenta_autorizada("moose") and path.read_bytes() == raw
    for changes in (dict(ferramentas_opcionais=groups[:-1]), dict(itens=points[:-1]), dict(impressao="bad"),
                    dict(catalogo_sha256="bad"), dict(maquina="other-host"), dict(ensino_pesquisa=False)):
        raw = set_old(**changes)
        assert not c.aceito() and not c.ferramenta_autorizada("moose") and path.read_bytes() == raw
    path.unlink()
    print("PASS 2.9 full receipt preserved without rewrite; incomplete, wrong-host and stale receipts never promoted", flush=True)


def check_browser(browser, base, c):
    import radai_languages as lang
    import radai_catalogo_nomes_i18n as labels
    from radai_phrases import CODIGOS

    data = {row[0]: row for row in labels.FRASES}
    context = browser.new_context()
    page = context.new_page()
    errors = []
    writes = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("request", lambda req: writes.append(req.url) if req.method == "POST" else None)
    page.route("**/*", lambda r: r.continue_() if r.request.url.startswith(base + "/") else r.abort())
    page.goto(base + "/aceite")
    for i, code in enumerate(["pt-BR", *CODIGOS]):
        page.evaluate("(c)=>localStorage.setItem('radai_idioma',c)", code)
        page.goto(base + "/aceite")
        button = page.locator("#ac_bt")
        expected = data["Aceitar todos os termos e entrar"][i]
        page.wait_for_function("(t)=>document.querySelector('#ac_bt').textContent.trim()===t && !document.querySelector('#ac_bt').disabled", arg=expected)
        assert page.locator("#ac_ferramentas .v").all_text_contents() == ["✓"] * 5
        assert page.locator("#ac_opcionais input, #ac_ok, #ac_catalogo input").count() == 0
        assert page.locator(".lic-item").count() == len(c.catalogo_termos.catalogo()[1])
        assert page.locator("#ac_pontos b").first.inner_text() == (c.PONTOS[0][1] if not i else lang.FRASES[code][c.PONTOS[0][1]])
        assert page.locator("#ac_pontos .pt span").all_text_contents()[1] == data[c.PONTOS[0][2]][i]
        summary = page.locator("#lic-rocards_lad summary").text_content()
        assert summary == data["ROCardS · descendente anterior"][i], (code, summary)
        assert page.locator("#lic-rocards_lad .lic-fontes a").count() >= 2
        assert page.locator("#ac_catalogo").get_attribute("data-documentos") == c.impressao_dos_documentos()
        if code == "en":
            page.locator("#ac_ferramentas a").first.click()
            assert page.locator("#ac_catalogo").evaluate("el=>el.open")
            assert page.locator(".lic-item:visible").count() == sum(x["ferramenta"] == "cads_open" for x in c.catalogo_termos.catalogo()[1])
            page.locator("#ac_todos").click()
            assert page.locator(".lic-item:visible").count() == len(c.catalogo_termos.catalogo()[1])
            page.locator("#ac_catalogo summary").first.click()
            page.screenshot(path=str(Path(__file__).with_name("aceite-en.png")), full_page=True)
        print("PASS", code, "one button, 5 checked tools, 245 alphabetic records, localized conditions", flush=True)
    assert not any("/api/aceite" in w or "install" in w or "baixar" in w for w in writes) and not c.aceito(), writes
    expected = {"quem": "", "itens": [x[0] for x in c.PONTOS], "catalogo_sha256": c.catalogo_termos.catalogo()[0],
                "ensino_pesquisa": True, "ferramentas_opcionais": c.catalogo_termos.grupos_opcionais(),
                "impressao": c.impressao_dos_documentos()}
    for changes in (dict(ferramentas_opcionais=expected["ferramentas_opcionais"][:-1]), dict(impressao="obsolete")):
        rejected = page.request.post(base + "/api/aceite", data={**expected, **changes}).json()
        assert rejected.get("erro") and not c.aceito()
    page.locator("#ac_bt").click()
    page.wait_for_url(base + "/")
    assert c.aceito() and c.aceite()["ferramentas_opcionais"] == c.catalogo_termos.grupos_opcionais()
    assert writes.count(base + "/api/aceite") == 1 and not any("install" in w or "baixar" in w for w in writes) and not errors, (writes, errors)
    print("PASS explicit POST saves all reviewed terms, stale browser and partial selection rejected, no install started", flush=True)
    context.close()


def main():
    with tempfile.TemporaryDirectory() as station, socket.socket() as sock:
        os.environ["RADAI_CALIB_DIR"] = station
        import radai_languages as lang
        import radai_consent as c
        check_previous_receipts(c)
        app = FastAPI()
        c.montar(app)
        lang.montar(app)
        @app.get("/", response_class=HTMLResponse)
        def home():
            return "<title>Local Suite</title>"
        @app.get("/api/primeiro-uso")
        def first_use():
            return {"feito": True}
        c.montar_portao(app)
        sock.bind(("127.0.0.1", 0))
        sock.listen(128)
        server = uvicorn.Server(uvicorn.Config(app, log_level="error", lifespan="off"))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
        thread.start()
        try:
            for _ in range(100):
                if server.started:
                    break
                time.sleep(.05)
            assert server.started
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(channel="chrome", headless=True)
                try:
                    check_browser(browser, "http://127.0.0.1:" + str(sock.getsockname()[1]), c)
                finally:
                    browser.close()
        finally:
            server.should_exit = True
            thread.join(10)


if __name__ == "__main__":
    main()
