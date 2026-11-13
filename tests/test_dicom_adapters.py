"""Real generated host pages with synthetic selected-viewer state, in Chrome."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
NEURO=Path(os.environ.get('RADAI_NEURO_ROOT',str(ROOT.parent/'radai-neuro-131')))
LUNG=Path(os.environ.get('RADAI_LUNG_ROOT',str(ROOT.parent/'radai-lung-release-1.1.1-codex'/'source')))
sys.path[:0]=[str(ROOT/'app'),str(ROOT.parent/'radai-contourlab-release-v817'/'app'),str(NEURO),str(LUNG/'app')]
os.environ.setdefault('RADAI_COMPONENTES_DIR',str(ROOT/'_montagem'/'componentes'))
for component in (ROOT/'_montagem'/'componentes').iterdir():
    if (component/'app').is_dir():sys.path.append(str(component/'app'))


class AdapterBrowser(unittest.TestCase):
    def test_rendered_page_adapters_and_twelve_languages(self):
        from fastapi import FastAPI
        from fastapi.responses import HTMLResponse,Response,JSONResponse
        from fastapi.staticfiles import StaticFiles
        from types import SimpleNamespace
        import uvicorn
        import radai_view,radai_recon3d_screen as R,radai_recon3d_vascular as V
        import radai_bolus_screen as B,radai_elastic_screen as E,radai_menu,radai_lung_screen as L,radai_languages
        from integration.radai_neuro_screen import pagina_estudo
        pages={'ver':radai_menu.aplicar(radai_view._pagina(),'ver'),
               'anatomia':radai_menu.aplicar(R.pagina('geral'),'recon_anatomia'),
               'torax':radai_menu.aplicar(R.pagina('toracica'),'recon_torax'),
               'vascular':radai_menu.aplicar(V.pagina(),'recon_vascular'),
               'bolus':radai_menu.aplicar(B.pagina(),'bolus_gerar'),
               'elastic':radai_menu.aplicar(E.pagina(),'elastic_fusao'),
               'neuro':pagina_estudo('glioma',None)}
        lung_app=FastAPI();L.montar(lung_app,{})
        pages['lung4d']=next(route.endpoint for route in lung_app.routes if getattr(route,'path','')=='/lung/4d')()
        from lung_rt.ui import render as lung_render
        lung_runtime=SimpleNamespace(root=LUNG,services={})
        pages['lungreport']=lung_render(lung_runtime,'report')
        pages['lungscreening']=lung_render(lung_runtime,'screening')
        app=FastAPI()
        app.mount('/lung-assets',StaticFiles(directory=str(LUNG/'web')),name='test-lung-assets')
        @app.get('/api/lung-plugin/state')
        def lung_state():return {'pending':[],'reports':[],'cases':[],'screening':{'active':False,'stage':'idle','generate_reports':0}}
        @app.get('/page/{name}',response_class=HTMLResponse)
        def page(name:str):return pages[name]
        @app.get('/radai-idiomas.js')
        def languages():return Response(radai_languages.corpo_js(),media_type='text/javascript')
        @app.get('/neuro/study.js')
        def neurojs():return Response((NEURO/'web'/'study.js').read_text(encoding='utf-8'),media_type='text/javascript')
        @app.get('/neuro/study.css')
        def neurocss():return Response((NEURO/'web'/'study.css').read_text(encoding='utf-8'),media_type='text/css')
        @app.api_route('/{rest:path}',methods=['GET','POST'])
        def fallback(rest:str):return JSONResponse({'series':[],'linhas':[],'jobs':[],'studies':[],'models':[],'plugins':[],'final':True,'token':'test-token','estado':'ok'})
        sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        server=uvicorn.Server(uvicorn.Config(app,log_level='error',access_log=False))
        thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True);thread.start()
        try:
            deadline=time.monotonic()+20
            while not server.started and time.monotonic()<deadline:time.sleep(.05)
            self.assertTrue(server.started)
            env=dict(os.environ,DICOM_ADAPTER_URL=f'http://127.0.0.1:{port}')
            env.setdefault('NEURO_PLAYWRIGHT_MODULE',r'C:\Users\henri\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules\playwright')
            result=subprocess.run(['node',str(ROOT/'tests'/'dicom_adapters_browser.cjs')],env=env,capture_output=True,text=True,encoding='utf-8',timeout=180)
            self.assertEqual(result.returncode,0,result.stdout+'\n'+result.stderr)
            print(result.stdout)
        finally:
            server.should_exit=True;thread.join(timeout=10)


if __name__=='__main__':unittest.main()
