"""Run Now effort toggle on a synthetic CT. The queue endpoint only captures requests."""
from pathlib import Path
import os
import sys
import tempfile
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1] / 'app'
sys.path.insert(0, str(APP))


def check():
    from playwright.sync_api import sync_playwright
    import radai_batch as batch
    import radai_menu, radai_review, radai_todo as todo, radai_queue_state as queue
    html = radai_review.aplicar(radai_menu.aplicar(batch._pagina(), 'lote'))
    options = {m:batch.opcoes_da_tela(m) for m in ('CT', 'MR')}
    assert options['CT']['esforco'] == 'maximo'
    options['CT']['esforco'] = 'medio'  # estação configurada antes de abrir o formulário
    log, sent, folders, scans = [], [], [], []
    def log_event(msg):
        from datetime import datetime
        log.append({'t':datetime.now().strftime('%H:%M:%S'), 'txt':msg, 'nivel':todo._classificar(msg)})
    queue.ligar_ganchos(log_plugin=log_event)
    figures = Path(os.environ['RADAI_FIXTURE_SCREENSHOTS']) if os.getenv('RADAI_FIXTURE_SCREENSHOTS') else None
    if figures:
        figures.mkdir(parents=True, exist_ok=True)

    def serve(route):
        url = urlparse(route.request.url)
        query = parse_qs(url.query)
        if url.path == '/lote':
            return route.fulfill(content_type='text/html; charset=utf-8', body=html)
        if url.path in ('/api/lote/pastas', '/api/pastas'):
            query_folder = route.request.post_data_json
            folders.append(query_folder)
            return route.fulfill(json={'caminho':query_folder.get('caminho',''), 'unidades':[], 'pastas':[]})
        if url.path == '/api/varrer/iniciar':
            scans.append(route.request.post_data_json)
            return route.fulfill(json={'v':'fixture-date'})
        if url.path == '/api/varrer/estado':
            return route.fulfill(json={'ok':True, 'fim':True, 'final':True,'linhas':[],'series':0})
        if url.path == '/api/lote/opcoes':
            return route.fulfill(json=options[query['modalidade'][0]])
        if url.path == '/api/lote/previa_da_entrega':
            series = route.request.post_data_json['serie']
            return route.fulfill(json=batch.previa_da_entrega(series))
        if url.path == '/api/lote/enfileirar':
            sent.extend(route.request.post_data_json['series'])
            return route.fulfill(json={'ok': True, 'enfileiradas': 1})
        if url.path == '/api/log':
            cursor = max(0,int(query.get('desde', ['0'])[0]))
            return route.fulfill(json={'linhas':log[cursor:], 'proximo':len(log), 'estado':'parado'})
        if url.path in ('/favicon.ico', '/favicon.png', '/radioterapia_ai.png'):
            return route.fulfill(path=APP/url.path.lstrip('/'))
        if url.path == '/api/fila':
            return route.fulfill(json={'cards': queue.para_tela(queue.cards())})
        if url.path.startswith('/api/'):
            return route.fulfill(json={})
        return route.fulfill(status=404)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.getenv('PLAYWRIGHT_CHROMIUM_EXECUTABLE'), timeout=15000)
        try:
            page = browser.new_page(viewport={'width':1840, 'height':1080}, locale='pt-BR',
                                    device_scale_factor=1, timezone_id='America/Sao_Paulo', reduced_motion='reduce')
            page.route('**/*', serve)
            page.goto('http://fixture.test/lote', wait_until='load', timeout=20000)
            page.wait_for_function('window.OPC && OPC.CT && OPC.MR')
            def choose_series():
                page.evaluate("""() => {
                    SERIES=[{pasta:'C:/FANTOMA',uid:'2.25.84001',curto:'84001',nome:'Fantoma de demonstração',
                      modalidade:'CT',cortes:96,date:'20261124',desc:'TC de tórax · série simulada',espessura_mm:2,
                      topo:'torax',estudo:'FANTOMA',n:1,numero:1,esforco:'extra',situacao:'livre'}];
                    porNoCarrinho(SERIES[0], true); sincronizarIncl(); pintarTabela(); _tituloDoPasso2(true); cartMsg('',false);
                    window.psAbrir('cx2');
                }""")
            target = page.locator('#btrodar')
            assert target.is_disabled() and target.inner_text().strip().endswith('(0)')
            choose_series()
            assert target.is_enabled() and target.inner_text().strip().endswith('(1)')
            page.evaluate('alternar(0)')
            assert target.is_disabled() and target.inner_text().strip().endswith('(0)')
            page.evaluate('alternar(0)')
            radio = page.locator('#tab button[role=radio]')
            mini = page.locator('#cx2 .effort-miniform')
            assert radio.count() == 2
            assert page.locator('#tab select.md-sel').input_value() == 'auto'
            assert mini.count() == 0
            assert page.locator('#tab td.modo small').count() == 0
            page.locator('#btrodar').click()
            page.wait_for_function("document.querySelector('#cartmsg').innerText.includes('fila')")
            assert sent[-1]['modo'] == 'auto' and 'esforco' not in sent[-1]

            choose_series()
            card = queue.enqueue_neuro('c' * 64, 'a' * 64, model_ids=['anatomy_synthseg'])
            assert queue.try_neuro_turn(card['id'])
            queue.report_neuro(card['id'], {'stage':'running','model':{'id':'anatomy_synthseg','status':'running'}})
            page.evaluate("radaiTfAbrirAba('log', true)")
            page.wait_for_function("document.querySelector('#radai_tf_log').innerText.includes('segmentando')")
            page.evaluate("document.getElementById('cx2').scrollIntoView({block:'center'})")
            if figures:
                page.screenshot(path=figures/'rodar-agora-auto.png', animations='disabled')
            page.locator('#tab button[data-v=perso]').click()
            assert mini.is_visible()
            assert mini.get_attribute('data-value') == 'medio'
            assert 'esforco' not in page.evaluate("payloadDaSerie(SERIES[0])")
            page.evaluate("""() => {
                const outra=Object.assign({},SERIES[0],{uid:'2.25.84002',n:2}); SERIES.push(outra);
                porNoCarrinho(outra,true);escolhaDe(outra).modo='perso';
                window.dispatchEvent(new CustomEvent('radai-esforco-caso',{detail:{indice:1,valor:'ultra'}}));
                atualizarEsforcoPreferido('alto');
            }""")
            assert target.inner_text().strip().endswith('(2)')
            assert page.locator('#tab td.modo small').count() == 0
            assert mini.first.get_attribute('data-value') == 'alto'
            assert page.evaluate("payloadDaSerie(SERIES[1]).esforco") == 'ultra'
            assert 'esforco' not in page.evaluate("payloadDaSerie(SERIES[0])")
            page.evaluate("porNoCarrinho(SERIES[1],false);SERIES.pop();sincronizarIncl();pintarTabela();")
            page.locator('#perso_0 label').filter(has=page.locator('input[data-prot="torax_mama"]')).first.click()
            rail = mini.locator('.effort-input')
            rail.focus()
            rail.press('Home')
            assert mini.get_attribute('data-value') == 'leve'
            page.wait_for_selector('#p4e_0[aria-busy=false]', timeout=12000)
            page.evaluate("document.querySelector('.p4').scrollIntoView({block:'center'})")
            bounds=page.evaluate('''() => {
              const rect=s=>document.querySelector(s).getBoundingClientRect();
              const wrap=rect('.wrap'), block=rect('#cx2'),button=rect('#cd_add'), task=document.querySelector('.p4-tasks .p4-rola');
              const table=document.querySelector('.tab-rola');
              return [Math.abs(button.left-block.left),Math.abs((block.left-wrap.left)-(wrap.right-block.right)),
                table.scrollWidth-table.clientWidth,task.scrollHeight-task.clientHeight,
                document.documentElement.scrollWidth-document.documentElement.clientWidth];
            }''')
            assert all(value<=2 for value in bounds), bounds
            assert page.locator('#tab th').all_text_contents()[4]=='Espessura (mm)'
            assert 'Coronária descendente anterior' in page.locator('.p4-tasks').inner_text()
            if figures:
                page.screenshot(path=figures/'rodar-agora-personalizado.png', animations='disabled')
            page.locator('#btrodar').click()
            page.wait_for_function("document.querySelector('#cartcx').dataset.n === '0'")
            assert target.is_disabled() and target.inner_text().strip().endswith('(0)')
            assert sent[-1]['modo'] == 'perso' and sent[-1]['esforco'] == 'leve'

            choose_series()
            assert mini.is_visible() and mini.get_attribute('data-value') == 'leve'
            page.locator('#tab button[data-v=auto]').click()
            assert mini.count() == 0
            page.locator('#btrodar').click()
            page.wait_for_function("document.querySelector('#cartcx').dataset.n === '0'")
            assert sent[-1]['modo'] == 'auto' and 'esforco' not in sent[-1]
            assert len(sent) == 3
            page.reload()
            page.wait_for_function('window.OPC && OPC.CT')
            choose_series()
            page.locator('#tab button[data-v=perso]').click()
            assert mini.get_attribute('data-value') == 'medio'
            assert 'esforco' not in page.evaluate("payloadDaSerie(SERIES[0])")
            print('AUTO / PERSONALIZADO (leve) / AUTO: three queue requests verified.')
            # UTC is January 2, but it is still January 1 on this workstation.
            page.clock.set_fixed_time('2026-01-02T02:59:00Z')
            page.evaluate("carregarComumLote().pasta('C:/FANTOMA');carregarComumLote().abrir(el('cd_add'));")
            page.locator('#cx1_procurar').click()
            first_day = page.locator('.ui-fp .ui-dias [role=radio]').first
            assert first_day.get_attribute('data-v') == '-1'
            assert 'Hoje' in first_day.inner_text()
            assert first_day.locator('time').inner_text() == '01/01/2026'
            first_day.click()
            page.wait_for_function("document.querySelector('.ui-fp [data-fp=usar]').disabled === false")
            with page.expect_response(lambda res: res.url.endswith('/api/varrer/iniciar')):
                page.locator('.ui-fp [data-fp=usar]').click()
            page.wait_for_function("document.querySelector('.ui-fp') === null")
            assert scans and folders
            listed = [row for row in folders if row.get('caminho') and row.get('dias') == -1]
            assert listed and scans[-1]['dias'] == -1 and scans[-1]['opcoes']['referencia_filtro'] == listed[-1]['referencia']
            print('Hoje 01/01/2026 in São Paulo on UTC January 2. Folder listing and scan shared the date window.')
        finally:
            browser.close()
            queue.ligar_ganchos(log_plugin=None)


if __name__ == '__main__':
    with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, RADAI_CALIB_DIR=temp,
        RADAI_FILA_DIR=temp, RADAI_CONFIG=str(Path(temp)/'fixture.config'), RADAI_TMP=temp):
        check()
