"""Test secondary/main/maximized viewing using the actual browser renderer."""
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit

APP = Path(__file__).resolve().parents[1] / 'app'
sys.path.insert(0, str(APP))

def check():
    from playwright.sync_api import sync_playwright
    import radai_recon3d_screen as screen
    import radai_menu
    pages = {mode: radai_menu.aplicar(screen.pagina(mode), 'recon_neuro' if mode=='neuro' else 'recon_anatomia') for mode in ('neuro','geral')}
    with sync_playwright() as play:
        browser=play.chromium.launch(channel='chrome')
        try:
            page=browser.new_page(viewport=dict(width=1600,height=1000), reduced_motion="reduce")
            page.set_default_timeout(6000)
            errors=[]
            page.on('pageerror',lambda err:errors.append(str(err)))
            def serve(route):
                path=urlsplit(route.request.url).path
                if path=='/recon3d/anatomia':
                    return route.fulfill(body=pages['neuro' if 'neuro' in route.request.url else 'geral'],content_type='text/html; charset=utf-8')
                if path=='/api/recon3d/projecao':
                    return route.fulfill(content_type='image/svg+xml',body='<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64"><circle cx="32" cy="32" r="16" fill="gray"/></svg>')
                if path=='/api/recon3d/estado':
                    return route.fulfill(json={'forma':[215,120,71],'segmentada':True,'cranial':1,'historico_planar':'archive-test' in route.request.url})
                if path.endswith('.js'):return route.fulfill(content_type='application/javascript',body='')
                return route.fulfill(json={})
            page.route('**/*',serve)
            for mode in ('geral','neuro'):
                page.goto('http://127.0.0.1/recon3d/anatomia?modo='+mode+'&b=fixture',wait_until='domcontentloaded')
                page.wait_for_function("window.R3 && R3.forma && R3.forma[0]===215")
                assert page.locator('.r3-wrap').get_attribute('data-ferramenta')==mode
                assert page.locator('.r3-col3d #r3_tela3d').count()==1
                for code in ('0','1','2','p'):
                    viewport=page.locator('#r3_img'+code).locator('..')
                    viewport.dblclick()
                    assert page.locator('.r3-col3d #r3_img'+code).count()==1
                    assert not page.locator('.r3-max').is_visible()
                    assert page.locator('.r3-plan-nav').is_visible() and page.locator('.r3-grade #r3_tela3d').is_visible()
                    assert page.locator('.r3-plan-nav #r3_pos'+code).is_visible()
                    viewport.dblclick()
                    assert page.locator('dialog[open] .r3-col3d #r3_img'+code).is_visible()
                    slider=page.locator('.r3-max .r3-plan-nav #r3_pos'+code)
                    slider.fill('3')
                    page.keyboard.press('Escape')
                    page.locator('.r3-q3d .r3-col3d #r3_img'+code).wait_for(state='visible')
                    assert slider.count()==0
                page.locator('.r3-grade #r3_tela3d').focus()
                page.keyboard.press('Enter')
                assert page.locator('.r3-col3d #r3_tela3d').count()==1
                page.locator('#r3_tela3d').press('Enter')
                assert page.locator('dialog[open] #r3_tela3d').is_visible()
                page.locator('.r3-max[open] .r3-max-head button').click()
                assert not page.locator('.r3-max').is_visible()
                page.evaluate("r3Abrir('archive-test','')")
                page.wait_for_function('R3.historicoPlanar')
                assert page.locator('#r3_imgp').is_hidden()
                assert page.locator('#r3_img0').is_visible()
                assert page.locator('#j_cerebro').is_hidden()
                assert page.locator('#r3_desenhar').is_hidden()
                page.locator('#r3_img1').locator('..').dblclick()
                assert page.locator('.r3-plan-nav #j_cerebro').is_hidden()
            assert not errors,errors
        finally:browser.close()
    print('Anatomia e Neuro: quatro vistas promovidas e maximizadas; canvas original, sliders, teclado e revisões persistidas verificados.')

if __name__=='__main__':check()
