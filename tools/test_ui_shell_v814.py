# -*- coding: utf-8 -*-
import ast
import html
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
import radai_ui as U
import radai_phrases as F
import radai_languages as L
import radai_modules as M
import radai_breadcrumb as B
import radai_menu as MENU


class CatalogTests(unittest.TestCase):
    def test_catalog_and_profile(self):
        self.assertEqual(B.pai("elastic_fusao")[1], "/bridge")
        self.assertEqual(B.pai("recon_torax")[1], "/recon3d")
        self.assertEqual(B.rotulo("neuro_anatomia"), "AutoContorno Neuro")
        self.assertIn('/bridge/elastic', M.pagina("bridge"))
        self.assertNotIn('Elastic RT', M.pagina("bridge"))
        self.assertNotIn('est pesada', M.pagina("recon3d"))
        for route in ('/lung/rastreio', '/lung/laudo', '/recon3d/toracica'):
            self.assertIn(route, M.pagina("lung"))
        with patch('radai_install_profile.perfil', return_value='lung-rt'):
            nav = MENU.html("lung")
            self.assertNotIn('href="/autocontorno"', nav)
            self.assertIn('data-pagina="autocontorno"', nav)
            self.assertIn('aria-disabled="true"', nav)
            self.assertIn('href="/lung/laudo"', nav)
        with patch('radai_install_profile.perfil', return_value='full'):
            self.assertIn('href="/autocontorno"', MENU.html("lung"))

    def test_explicit_rows_have_twelve_languages(self):
        table = {F.normalizar(row[0]): row for row in F.TABELA}
        for key in ('Ver segmentações', 'Overnight Run · Vigia', 'AutoContorno Neuro',
                    'Laudo sintético', 'Rastreio populacional', 'Segmentar novo caso',
                    'Resolução da projeção', 'A sugestão geométrica exige revisão.'):
            row = table[key]
            self.assertEqual(len(row), 12)
            self.assertTrue(all(isinstance(value, str) and value.strip() for value in row))
        self.assertEqual(table['Overnight Run · Vigia'][1], 'Overnight Run · Watcher')

    def test_picker_composes_and_escapes(self):
        rendered = U.formulario_carregar_imagens('pick', pasta='"<script>',
            envolver=lambda form: U.abas_de_serie('pick_tabs', (
                ('acervo', 'Acervo Local', '<p>Acervo Local</p>'),
                ('pasta', 'Escolher a pasta', form)), padrao='pasta'))
        self.assertIn('pick_tabs-p-acervo', rendered)
        self.assertIn('id="pick_form"', rendered)
        self.assertIn('&quot;&lt;script&gt;', rendered)
        for bad in ('', 'a"', 'a b', '<x>', '1x'):
            with self.assertRaises(ValueError):
                U.formulario_carregar_imagens(bad)


FIXTURE_JS = r"""
window.demo={starts:0,stops:[],polls:0,finished:[],partial:[],errors:[],mode:'complete'};
var nativeFetch=window.fetch;
window.fetch=function(url, options){
 var payload=JSON.parse(options && options.body || '{}');
 function result(d){return {ok:true,json:function(){return Promise.resolve(d)}}}
 if(url==='/api/lote/favorita')return Promise.resolve(result({favorita:'C:/SYNTHETIC'}));
 if(url==='/api/varrer/iniciar'){
  demo.starts++; demo.input=payload; var id='synthetic-'+demo.starts;
  if(demo.mode==='error')return Promise.resolve(result({erro:'Nenhuma série nesta pasta.'}));
  return new Promise(function(resolve){setTimeout(function(){resolve(result({v:id,fim:false,
   series:1,pastas:2,linhas:[{uid:'synthetic',desc:'SYNTHETIC',cortes:2,carregando:true}]}))},demo.mode==='slow'?150:0)});
 }
 if(url==='/api/varrer/estado'){
  demo.polls++;
  if(demo.mode==='cancel')return Promise.resolve(result({v:payload.v,fim:true,parado:true,final:false,linhas:[{uid:'partial',carregando:true}]}));
  if(demo.mode==='complete')return Promise.resolve(result({v:payload.v,fim:true,final:true,series:1,pastas:2,
   linhas:[{uid:'synthetic',desc:'SYNTHETIC',cortes:8,bilhete:'opaque-synthetic'},{uid:'partial',carregando:true}]}));
  return Promise.resolve(result({v:payload.v,fim:false,linhas:[]}));
 }
 if(url==='/api/varrer/parar'){demo.stops.push(payload.v);return Promise.resolve(result({ok:true}))}
 return nativeFetch.apply(this,arguments);
};
window.addEventListener('DOMContentLoaded',function(){
 UI_VARRER_INTERVALO_MS=30;
 window.pick=uiCarregarImagens('pick',{
  aoParcial:function(rows,d){demo.partial.push({count:rows.length,final:!!d.final})},
  aoFim:function(rows,d,ctx){demo.finished.push({rows:rows,d:d,ctx:ctx})},
  aoErro:function(m){demo.errors.push(m)}
 });
});
"""


def fixture():
    body=U.formulario_carregar_imagens('pick', envolver=lambda form: U.abas_de_serie(
        'pick_tabs', (('acervo','Acervo Local','<p>Acervo Local</p>'),
                      ('pasta','Escolher a pasta',form)), padrao='pasta'))
    p=('<!doctype html><html><head><meta charset="utf-8">'
       '<meta name="viewport" content="width=device-width,initial-scale=1">'
       + U.folha() + U.JS + U.COMPONENTES_JS + U.VARREDURA_JS + '</head><body>'
       + body + U.moldes_de_icone() + '<script>'+FIXTURE_JS+'</script></body></html>')
    return L.aplicar(p)


class BrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        base=Path(os.environ['LOCALAPPDATA'])/'ms-playwright'
        candidates=sorted(base.glob('chromium-*/chrome-win64/chrome.exe'),reverse=True)
        if not candidates:
            candidates=sorted(base.glob('chromium-*/chrome-win/chrome.exe'),reverse=True)
        if not candidates:
            raise RuntimeError('Chromium required for the shared picker regression')
        cls.playwright=sync_playwright().start()
        cls.browser=cls.playwright.chromium.launch(executable_path=str(candidates[0]),headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.ctx=self.browser.new_context(viewport={'width':1280,'height':800},reduced_motion='reduce')
        page_html=fixture()
        def route(r):
            if r.request.url.endswith('/radai-idiomas.js'):
                r.fulfill(content_type='application/javascript',body=L.corpo_js())
            elif r.request.url.endswith('/fixture'):
                r.fulfill(content_type='text/html',body=page_html)
            else:
                r.fulfill(content_type='application/json',body='{}')
        self.ctx.route('**/*',route)
        self.page=self.ctx.new_page()
        self.page.set_default_timeout(5000)
        self.js_errors=[]
        self.page.on('pageerror',lambda error:self.js_errors.append(str(error)))
        self.page.goto('http://127.0.0.1:49199/fixture')
        self.page.evaluate("pick.abrir();pick.pasta('C:/SYNTHETIC')")
        self.page.wait_for_selector('.ui-modal-veu.vis .ui-modal')

    def tearDown(self):
        self.ctx.close()
        self.assertEqual(self.js_errors,[])

    def test_completion_real_counts_and_opaque_ticket(self):
        self.assertTrue(self.page.locator("#pick_fora").is_hidden())
        self.assertTrue(self.page.locator("#pick_progresso").is_hidden())
        self.page.locator('#pick_form button[type=submit]').click()
        self.page.wait_for_function('demo.finished.length===1')
        d=self.page.evaluate('demo.finished[0]')
        self.assertEqual(len(d['rows']),1)
        self.assertEqual(d['rows'][0]['bilhete'],'opaque-synthetic')
        self.assertEqual(d['ctx']['pasta'],'C:/SYNTHETIC')
        self.assertFalse(self.page.locator('#pick_form').is_hidden())
        self.assertEqual(self.page.locator('#pick').get_attribute('aria-busy'),'false')
        self.assertTrue(self.page.evaluate('demo.partial.length>0'))

    def test_cancel_after_ticket_exposes_no_partial_selection(self):
        self.page.evaluate("demo.mode='cancel';pick.varrer();pick.parar()")
        self.page.wait_for_function('demo.finished.length===1')
        self.assertEqual(self.page.evaluate('demo.finished[0].rows'),[])
        self.assertTrue(self.page.evaluate('demo.stops.length>0'))

    def test_close_before_ticket_cancels_and_ignores_late_response(self):
        self.page.evaluate("demo.mode='slow';pick.varrer();pick.fechar()")
        self.page.wait_for_function('demo.stops.length===1')
        self.assertEqual(self.page.evaluate('demo.finished.length'),0)
        self.assertEqual(self.page.evaluate('demo.polls'),0)
        self.page.wait_for_timeout(250)
        self.page.evaluate('pick.abrir()')
        self.page.wait_for_selector('.ui-modal-veu.vis .ui-modal')
        self.assertTrue(self.page.locator('#pick_form').is_visible())
        self.assertEqual(self.page.evaluate('pick.pasta()'),'C:/SYNTHETIC')

    def test_error_allows_retry(self):
        self.page.evaluate("demo.mode='error';pick.varrer()")
        self.page.wait_for_function('demo.errors.length===1')
        self.assertTrue(self.page.locator('#pick_form').is_visible())
        self.page.evaluate("demo.mode='complete';pick.varrer()")
        self.page.wait_for_function('demo.finished.length===1')

    def test_short_templates_translate_before_values(self):
        for lang, *_ in L.IDIOMAS:
            self.page.evaluate('(lang)=>localStorage.setItem("radai_idioma",lang)', lang)
            for key in ('Série %s', 'Estudo %s', 'Incluir %s'):
                value = 'UNCHANGED_42'
                expected = F.construir().get(lang, {}).get(key, key) % value
                result = self.page.evaluate('(x)=>uiMolde(x[0],[x[1]])', [key, value])
                self.assertEqual(result, expected)
                self.assertIn(value, result)

    def test_twelve_languages_desktop_mobile_and_rtl(self):
        table={row[0]:row for row in F.TABELA}
        for width in (1280,390):
            self.page.set_viewport_size({'width':width,'height':844})
            for language,*_ in L.IDIOMAS:
                self.page.evaluate('(lang)=>localStorage.setItem("radai_idioma",lang)',language)
                self.page.reload()
                self.page.evaluate("pick.abrir()")
                self.page.wait_for_selector(".ui-modal-veu.vis .ui-modal")
                expected=table['Adicionar novas séries'][0 if language=='pt-BR' else F.CODIGOS.index(language)+1]
                self.assertEqual(self.page.locator('.ui-modal-tit').inner_text(),expected)
                self.assertEqual(self.page.locator('html').evaluate('(el)=>getComputedStyle(el).direction'),'rtl' if language=='ar' else 'ltr')
                bounds=self.page.locator('.ui-modal').bounding_box()
                self.assertGreaterEqual(bounds['x'],-1)
                self.assertLessEqual(bounds['x']+bounds['width'],width+1)
        self.page.locator('#pick_tabs-t-acervo').click()
        self.assertTrue(self.page.locator('#pick_tabs-p-acervo').is_visible())


if __name__=='__main__':
    unittest.main(verbosity=2)
