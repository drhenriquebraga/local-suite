"""Synthetic optional LUNG resources and host minipage contract; no clinical data."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'app'))
import radai_lung_install as SDK

SEED=Path(os.environ.get('LUNG_RT_CODE_SEED',str(Path(tempfile.gettempdir())/'radai-lung-code-seed-112.zip')))


def digest(data):return hashlib.sha256(data).hexdigest()


def bundle(destination,*,version='1.1.2',revision='a'*40,damage=None,marker=None):
    payloads={name:(b'SYNTHETIC RESOURCE ONLY '+name.encode()+b' '*600) for name in (
        'models/nv-reason-ct-int4/model.test',
        'runtimes/nvreason/ort-wasm-simd-threaded.asyncify.mjs',
        'runtimes/nvreason/ort-wasm-simd-threaded.asyncify.wasm')}
    resources=[{'path':name,'size':len(raw),'sha256':digest(raw),'url':'https://invalid.test/no-network'} for name,raw in payloads.items()]
    xray={'schema':'lung-rt/xray-resources/1','model_id':'google/medgemma-1.5-4b-it','revision':revision}
    for key in ('runtime','model','mmproj'):
        name=key+'.test';raw=b'SYNTHETIC RX ONLY '+name.encode()+b' '*600
        xray[key]={'filename':name,'size':len(raw),'sha256':digest(raw),'url':'https://invalid.test/no-network'}
        payloads['xray/'+revision+'/'+name]=raw
    code={
        'module.json':json.dumps({'schema':'lung-rt/plugin-manifest/1','id':'lung-rt','version':version,'host_contract':'local-suite/plugins/1','host_min_version':'8.17','python':'>=3.10,<3.15','adapter':'integration/local_suite.py:mount'}).encode(),
        'integration/local_suite.py':b'def mount(app, code, host_services=None): return {}\n',
        'catalog/resource_recipe.json':json.dumps({'files':resources}).encode(),
        'catalog/xray_resources.json':json.dumps(xray).encode(),
    }
    raw=json.dumps({'schema':'lung-rt/release-package/1','plugin_id':'lung-rt','version':version,'files':[{'path':'code/'+name,'size':len(data),'sha256':digest(data)} for name,data in code.items()]}).encode()
    pin=digest(raw)
    record={'schema':'lung-rt/offline-preparation/1','code_pin':pin,'reports':True,'complete':True} if marker is None else marker
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_STORED) as out:
        out.writestr('release-manifest.json',raw)
        out.writestr('.lung-offline-preparation.json',json.dumps(record))
        for name,data in code.items():out.writestr('code/'+name,data)
        for name,data in payloads.items():out.writestr('resources/'+name,(damage or {}).get(name,data))
    return pin,payloads


class OptionalResourceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='lung-optional-synthetic-');self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name);self.root=self.folder/'Suite';self.root.mkdir()
        (self.root/'entrega.txt').write_text('PROJETO=LOCAL_SUITE\nVERSAO=8.17\n')

    def install(self,source,reports=True):
        plan=SDK.prepare_external_plan({'reports':reports},source_folder=str(source))
        self.assertTrue(plan['offline']);return SDK.run_external(plan,None,suite_root=self.root,host_python=sys.executable)

    def test_offline_zip_streams_ct_and_rx_without_network_python_or_license_receipt(self):
        source=self.folder/'LUNG_RT_OFFLINE.zip';pin,payloads=bundle(source)
        with patch.object(SDK,'TRUSTED_CODE_INVENTORIES',{pin}),patch.object(SDK,'_download',side_effect=AssertionError('network forbidden')),patch.object(SDK,'_request',side_effect=AssertionError('network forbidden')):
            self.assertEqual(self.install(source)['state'],'ready')
        plugin=self.root/'Plugins/LUNG RT';state=json.loads((plugin/'installation.json').read_text())
        for name,raw in payloads.items():
            target=plugin/('data' if name.startswith('xray/') else state['resources_path'])/name
            self.assertEqual(target.read_bytes(),raw)
        self.assertFalse(any(self.root.rglob('license.json')))
        self.assertFalse((self.root/'python').exists())
        self.assertFalse(any(plugin.rglob('*.part-*')))

    def test_reports_false_leaves_both_model_groups_uninstalled(self):
        source=self.folder/'LUNG_RT_OFFLINE.zip';pin,_=bundle(source)
        with patch.object(SDK,'TRUSTED_CODE_INVENTORIES',{pin}),patch.object(SDK,'_download',side_effect=AssertionError('network forbidden')):
            self.install(source,reports=False)
        plugin=self.root/'Plugins/LUNG RT'
        self.assertFalse((plugin/'resources').exists());self.assertFalse((plugin/'data/xray').exists())
        self.assertFalse(json.loads((plugin/'installation.json').read_text())['reports_installed'])

    def test_bad_size_and_hash_leave_previous_code_pointer_and_assets_unchanged(self):
        old=self.folder/'old.zip';old_pin,old_payloads=bundle(old,version='1.1.1',revision='a'*40)
        for bad_key in ('models/nv-reason-ct-int4/model.test','xray/'+('b'*40)+'/mmproj.test'):
            for corruption in ('size','hash'):
                with self.subTest(resource=bad_key,corruption=corruption):
                    with patch.object(SDK,'TRUSTED_CODE_INVENTORIES',{old_pin}),patch.object(SDK,'_download',side_effect=AssertionError('network forbidden')):self.install(old)
                    plugin=self.root/'Plugins/LUNG RT';pointer=plugin/'installation.json';before=pointer.read_bytes();state=json.loads(before)
                    canonical=b'SYNTHETIC RX ONLY mmproj.test'+b' '*600 if bad_key.startswith('xray/') else old_payloads[bad_key]
                    damaged=canonical[:-1] if corruption=='size' else b'X'*len(canonical)
                    new=self.folder/'new.zip';new_pin,_=bundle(new,version='1.1.2',revision='b'*40,damage={bad_key:damaged})
                    # Force the CT path through the package as well, instead of a valid existing model cache.
                    existing_ct=plugin/state['resources_path']/'models/nv-reason-ct-int4/model.test'
                    saved=existing_ct.read_bytes();existing_ct.unlink()
                    try:
                        with patch.object(SDK,'TRUSTED_CODE_INVENTORIES',{old_pin,new_pin}),patch.object(SDK,'_download',side_effect=AssertionError('network forbidden')):
                            with self.assertRaises(ValueError):self.install(new)
                    finally:existing_ct.write_bytes(saved)
                    self.assertEqual(pointer.read_bytes(),before)
                    for name,raw in old_payloads.items():
                        target=plugin/('data' if name.startswith('xray/') else state['resources_path'])/name
                        self.assertEqual(target.read_bytes(),raw)
                    self.assertFalse(any(plugin.rglob('*.part-*')))
                    self.assertFalse(any(plugin.rglob('license.json')))

    def test_large_zip_marker_path_without_allocating_large_files(self):
        source=self.folder/'large-synthetic.zip';pin,_=bundle(source)
        with patch.object(SDK,'MAX_SETUP',1024),patch.object(SDK,'TRUSTED_CODE_INVENTORIES',{pin}),patch.object(SDK,'_download',side_effect=AssertionError('network forbidden')):
            self.assertTrue(SDK.inspect_local_source(source)['offline']);self.install(source)

    def test_malformed_marker_is_a_package_error(self):
        for marker in ([],None,{'complete':False}):
            if marker is None:continue
            source=self.folder/'bad-marker.zip';pin,_=bundle(source,marker=marker)
            with self.subTest(marker=marker),patch.object(SDK,'MAX_SETUP',1024),patch.object(SDK,'TRUSTED_CODE_INVENTORIES',{pin}):
                with self.assertRaises(ValueError):SDK.inspect_local_source(source)

    def test_actual_frozen_code_mounts_without_extra_models(self):
        if not SEED.is_file():self.skipTest('Set LUNG_RT_CODE_SEED to the frozen code-only ZIP.')
        sys.path.insert(0,r'C:\AI_PROJETOS\CONTOURLAB\app')
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        import radai_plugins
        with patch.object(SDK,'_download',side_effect=AssertionError('network forbidden')):
            plan=SDK.prepare_external_plan({'reports':False},source_folder=str(SEED))
            SDK.run_external(plan,None,suite_root=self.root,host_python=sys.executable)
        installation=radai_plugins.discover_plugin(self.root,'lung-rt',{'contract':radai_plugins.HOST_CONTRACT,'version':'8.17'})
        self.assertEqual(installation['state'],'ready',installation)
        app=FastAPI()
        receipt=radai_plugins.mount_plugin(app,installation,{'data_dir':str(self.root/'Plugins/LUNG RT/data'),'test_client':True,'hardware':lambda:{},'acquire_gpu':lambda name:True,'release_gpu':lambda name:None})
        with TestClient(app,base_url='http://127.0.0.1') as client:
            status=client.get('/api/lung-plugin/status').json();caps=status['capabilities']
            self.assertTrue(all(caps[name] for name in ('rastreio','nodulos','4d')))
            self.assertFalse(caps['report_ct']['resources_ready']);self.assertFalse(caps['report_rx']['resources_ready'])
            for page in ('/lung/rastreio','/lung/laudo','/lung/laudo/rx'):
                self.assertEqual(client.get(page).status_code,200,page)
        receipt['service'].reports.monitor.join(3)


class MinipageMarkupTests(unittest.TestCase):
    def test_only_report_cards_are_initially_disabled_with_settings_path(self):
        import radai_modules
        page=radai_modules.pagina_completa('lung')
        self.assertIn('data-lung-capability="report_ct"',page)
        self.assertIn('data-lung-capability="report_rx"',page)
        self.assertIn('href="/config#ps_lung"',page)
        self.assertNotIn('href="/lung/laudo"',page)
        self.assertNotIn('href="/lung/laudo/rx"',page)
        for path in ('/lung/rastreio','/lung/nodulos','/lung/4d'):self.assertIn('href="'+path+'"',page)


@unittest.skipUnless(os.environ.get('LUNG_RT_BROWSER')=='1','Set LUNG_RT_BROWSER=1 with Playwright available.')
class BrowserMinipageTests(unittest.TestCase):
    def test_readiness_states_no_initial_flash_and_twelve_languages(self):
        from playwright.sync_api import sync_playwright
        from urllib.request import build_opener,ProxyHandler
        import radai_languages
        port=os.environ.get('LUNG_RT_HOST_TEST_PORT','18779');base='http://127.0.0.1:'+port
        with tempfile.TemporaryDirectory(prefix='lung-host-browser-') as tmp:
            with (Path(tmp)/'server.log').open('wb') as log:
                server=subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'--browser-server'],env={**os.environ,'LUNG_RT_HOST_TEST_PORT':port},stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                try:
                    for attempt in range(80):
                        try:
                            with build_opener(ProxyHandler({})).open(base+'/blank',timeout=.5):break
                        except OSError:
                            if server.poll() is not None:self.fail('Synthetic server failed: '+(Path(tmp)/'server.log').read_text(errors='replace'))
                            time.sleep(.1)
                    else:self.fail('Synthetic server did not start')
                    with sync_playwright() as playwright:
                        browser=playwright.chromium.launch(headless=True,executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe')
                        try:
                            page=browser.new_page(viewport={'width':1440,'height':1000});errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
                            pending=[]
                            page.route('**/api/lung-plugin/status',lambda route:pending.append(route))
                            titles={'report_ct':'Laudo sintético','report_rx':'Laudo sintético de raios X'}
                            for locale in ('pt-BR','en','de','es','fr','it','pl','ar','bn','ko','zh-CN','ja'):
                                page.goto(base+'/blank');page.evaluate('(locale)=>localStorage.setItem("radai_idioma",locale)',locale)
                                for ready in (False,True):
                                    page.goto(base+'/lung',wait_until='domcontentloaded')
                                    page.wait_for_function('document.querySelectorAll("[data-lung-capability]").length===2')
                                    for key in titles:
                                        card=page.locator('[data-lung-capability="'+key+'"]')
                                        self.assertEqual(card.evaluate('el=>el.tagName'),'DIV')
                                        self.assertEqual(card.get_attribute('aria-disabled'),'true')
                                    self.assertEqual(page.locator('.md-grade a[href="/lung/laudo"],.md-grade a[href="/lung/laudo/rx"]').count(),0)
                                    for path in ('/lung/rastreio','/lung/nodulos','/lung/4d'):
                                        self.assertEqual(page.locator('.md-grade a[href="'+path+'"]').count(),1)
                                    self.assertEqual(len(pending),1)
                                    pending.pop().fulfill(json={'capabilities':{key:{'resources_ready':ready} for key in titles}})
                                    page.wait_for_function('typeof window.radaiFrase==="function"')
                                    if ready:page.wait_for_function('document.querySelectorAll("a[data-lung-capability]").length===2')
                                    page.evaluate('window.radaiRetraduzir()')
                                    for key,title in titles.items():
                                        card=page.locator('[data-lung-capability="'+key+'"]')
                                        expected=title if locale=='pt-BR' else radai_languages.FRASES[locale][radai_languages.normalizar(title)]
                                        self.assertEqual(card.locator('h2').inner_text(),expected,(locale,key))
                                        if not ready:
                                            expected='Configurações' if locale=='pt-BR' else radai_languages.FRASES[locale][radai_languages.normalizar('Configurações')]
                                            self.assertEqual(card.locator('.lung-resource-settings').inner_text(),expected)
                                        else:self.assertEqual(card.locator('.md-abrir').count(),1)
                            for state in ({'report_ct':True,'report_rx':False},{'report_ct':False,'report_rx':True}):
                                page.goto(base+'/lung',wait_until='domcontentloaded');self.assertEqual(len(pending),1)
                                pending.pop().fulfill(json={'capabilities':{key:{'resources_ready':value} for key,value in state.items()}})
                                page.wait_for_function('document.querySelectorAll("a[data-lung-capability]").length===1')
                                for key,ready in state.items():self.assertEqual(page.locator('[data-lung-capability="'+key+'"]').evaluate('el=>el.tagName'),'A' if ready else 'DIV')
                            page.goto(base+'/lung',wait_until='domcontentloaded');pending.pop().abort();page.wait_for_timeout(50)
                            self.assertEqual(page.locator('div[data-lung-capability]').count(),2)
                            self.assertFalse(errors,errors)
                        finally:browser.close()
                finally:
                    server.terminate();server.wait(timeout=10)


def serve_browser_fixture():
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse
    import radai_languages,radai_router,uvicorn
    app=FastAPI();radai_languages.montar(app)
    @app.get('/lung',response_class=HTMLResponse)
    def mini():return radai_router.mini_pagina('lung')
    @app.get('/blank',response_class=HTMLResponse)
    def blank():return '<!doctype html><title>SYNTHETIC TEST ONLY</title>'
    uvicorn.run(app,host='127.0.0.1',port=int(os.environ.get('LUNG_RT_HOST_TEST_PORT','18779')),log_level='warning')


if __name__=='__main__':
    if '--browser-server' in sys.argv:serve_browser_fixture()
    else:unittest.main(verbosity=2)
