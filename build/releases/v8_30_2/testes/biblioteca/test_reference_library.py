"""Exercise the reference library on temporary workstation storage in headless Chrome."""
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time

from fastapi import FastAPI
from playwright.sync_api import sync_playwright
import uvicorn

APP = Path(__file__).resolve().parents[2] / "programa/app"
sys.path.insert(0, str(APP))
import radai_bibliography as bib
import radai_biblioteca_i18n as library_i18n
import radai_consent as consent
import radai_credits as credits
import radai_languages as lang
import radai_provenance_screen as provenance
import radai_termos_catalogo as catalog


def main():
    with tempfile.TemporaryDirectory() as workspace, socket.socket() as sock:
        os.environ['RADAI_CALIB_DIR'] = workspace
        os.environ['RADAI_CONFIG'] = str(Path(workspace) / 'sample.config')
        app = FastAPI()
        for module in (bib, consent, credits, provenance, lang):
            module.montar(app)
        sock.bind(('127.0.0.1', 0))
        sock.listen()
        base = 'http://127.0.0.1:' + str(sock.getsockname()[1])
        server = uvicorn.Server(uvicorn.Config(app, log_level='warning', lifespan='off', loop='asyncio', http='h11', ws='none'))
        thread = threading.Thread(target=server.run, kwargs={'sockets':[sock]}, daemon=True)
        thread.start()
        try:
            for attempt in range(900):
                if server.started:
                    break
                time.sleep(.05)
            assert server.started
            with sync_playwright() as play:
                browser = play.chromium.launch(channel='chrome', headless=True)
                browser_checks(browser, base)
                browser.close()
        finally:
            server.should_exit = True
            thread.join(5)


def browser_checks(browser, base):
    context = browser.new_context(viewport={'width':1260,'height':840})
    context.route('**/*', lambda route: route.continue_() if route.request.url.startswith(base + '/') else route.abort())
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda err: errors.append(str(err)))
    page.goto(base+'/bibliografia')
    page.wait_for_function("document.documentElement.lang==='en'")
    assert page.locator('#radaiMenu a[href="/bibliografia"]').count() == 1
    assert page.locator('#radaiMenu a[href="/licencas-ferramentas"]').count() == 0
    assert page.locator('#painel-bibliografia').is_visible()
    assert page.locator('#painel-bibliografia a[href="/procedencia"]').is_visible()
    names = page.locator('.bi-modelo .tit').all_text_contents()
    assert len(names) == len(bib._dados()['modelos'])
    assert page.evaluate("""(names) => {
      const cmp = new Intl.Collator(document.documentElement.lang,{sensitivity:'base',numeric:true}).compare;
      return names.every((n,i)=>!i || cmp(names[i-1],n)<=0);
    }""", names)
    card = page.locator('.bi-modelo').filter(has_text='ROCardS')
    assert card.count()==1 and card.inner_text().count('CC BY-NC 4.0') >= 2
    assert card.get_attribute('class') == 'bi-item bi-modelo'
    assert len(page.locator('#painel-bibliografia a[href^="https://doi.org/"]').all()) > 20
    page.locator('#aba-termos').click()
    assert page.locator('#painel-termos').is_visible() and page.url.endswith('/licencas-ferramentas')
    assert 'No acceptance has been recorded' in page.locator('#painel-termos').inner_text()
    page.go_back()
    assert page.locator('#painel-bibliografia').is_visible()
    page.locator('#aba-bibliografia').focus()
    page.keyboard.press('ArrowRight')
    assert page.locator('#aba-termos').get_attribute('aria-selected') == 'true'
    page.locator('header [data-radai-idiomas] .rl-bt').click()
    with page.expect_navigation():
        page.locator('header [data-radai-idiomas] [data-cod="fr"]').click()
    page.wait_for_function("document.documentElement.lang==='fr'")
    assert page.locator('#painel-termos').is_visible()
    page.locator('header [data-radai-idiomas] .rl-bt').click()
    with page.expect_navigation():
        page.locator('header [data-radai-idiomas] [data-cod="en"]').click()
    page.locator('#aba-termos').focus()
    page.keyboard.press('Home')
    assert page.locator('#painel-bibliografia').is_visible()
    print('PASS unified navigation, keyboard, browser history, DOI and structure provenance, neutral ROCardS listing')
    old = dict(versao='2.1', quando='2024-02-03 04:05:06', maquina=consent._maquina(), ferramentas_opcionais=['moose'])
    receipt = consent._caminho()
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(old),encoding='utf8')
    page.goto(base+'/bibliografia?aba=termos')
    page.wait_for_function("document.documentElement.lang==='en'")
    registered = page.locator('.bi-recibo').inner_text()
    assert 'MOOSE' in registered and 'CADS open' not in registered and old['quando'] in registered
    assert page.locator('#painel-termos').get_by_text('Acceptance needs to be renewed.').is_visible()
    assert json.loads(receipt.read_text('utf8')) == old
    print('PASS prior receipt retains its real date, version and optional scope without writes')
    for path in ['/termos','/politica-privacidade','/creditos','/procedencia']:
        assert page.request.get(base+path).status==200
    from radai_phrases import CODIGOS
    codes = ['pt-BR'] + CODIGOS
    for idx,code in enumerate(codes):
        page.evaluate('(c)=>localStorage.setItem("radai_idioma",c)',code)
        page.reload()
        page.wait_for_function('(c)=>document.documentElement.lang===c',arg=code)
        assert page.locator('#aba-bibliografia').inner_text()==library_i18n.FRASES[1][idx]
        assert page.locator('#aba-termos').inner_text()==library_i18n.FRASES[2][idx]
    print('PASS real tabs in all 12 languages and four document/provenance URLs')
    page.evaluate("localStorage.setItem('radai_idioma','pt-BR')")
    groups = catalog.grupos_opcionais()
    current = consent.montar_registro(itens=[i[0] for i in consent.PONTOS], catalogo_sha256=catalog.catalogo()[0],
                                     ensino_pesquisa=True, ferramentas=groups)
    receipt.write_text(json.dumps(current), encoding='utf8')
    page.goto(base+'/licencas-ferramentas')
    assert page.locator('#painel-termos').is_visible()
    assert page.get_by_text('Aceite vigente.',exact=True).is_visible()
    assert 'NV-Segment-CT' in page.locator('.bi-recibo').inner_text()
    assert page.locator('.lic-item').count() == len(catalog.catalogo()[1])
    page.goto(base+'/licencas-ferramentas#lic-rocards_lad')
    assert page.locator('#lic-rocards_lad').evaluate('(card)=>card.open')
    assert 'CC BY-NC' in page.locator('#lic-rocards_lad').inner_text()
    page.goto(base+'/licencas-ferramentas')
    page.screenshot(path=str(Path(__file__).with_name('termos-aceitos.png')))
    page.get_by_role('tab',name='Bibliografia e procedência').click()
    page.screenshot(path=str(Path(__file__).with_name('bibliografia.png')))
    assert json.loads(receipt.read_text('utf8')) == current and not errors, errors
    print('PASS current receipt, full catalog and no client-side exceptions')
    context.close()


if __name__ == '__main__':
    main()
