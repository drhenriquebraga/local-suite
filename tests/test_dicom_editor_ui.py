"""Real browser + real local API, using an oblique synthetic DICOM fixture."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'app'), str(ROOT/'tests'),
               str(ROOT.parent/'radai-contourlab-release-v817'/'app')]
os.environ.setdefault('RADAI_COMPONENTES_DIR',str(ROOT/'_montagem'/'componentes'))
for component in (ROOT/'_montagem'/'componentes').iterdir():
    if (component/'app').is_dir(): sys.path.append(str(component/'app'))


class EditorBrowser(unittest.TestCase):
    def test_real_editor_roundtrip_and_toolbar(self):
        from fastapi import FastAPI
        from fastapi.responses import HTMLResponse
        import uvicorn
        import radai_contour_edit as core
        import radai_contour_edit_api as api
        import radai_dicom_tools as toolbar
        import radai_contour_editor_ui as editor
        import radai_dicom_adapters as adapters
        from test_contour_edit import make_series, write_rt
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            uid,files=make_series(folder,shape=(9,64,72))
            reference=core.Session(folder,uid,files)
            write_rt(reference,folder/'source.dcm')
            original=core.resolve_ticket
            core.resolve_ticket=lambda ticket,source='thumbnail',uid_=None:(folder,uid,files)
            app=FastAPI();api.montar(app)
            @app.get('/',response_class=HTMLResponse)
            def page():
                return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><style>body{background:#080f1d;color:#ddd;margin:12px}'+toolbar.CSS+editor.CSS+'</style></head><body>'
                        '<button id="open">Open</button><div id="host"></div>'
                        '<script>'+toolbar.JS+editor.JS+adapters.JS+
                        ';document.getElementById("open").onclick=function(){RadaiContourEditor.open({b:"synthetic",rs:"source.dcm"})};</script></body></html>')
            sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            server=uvicorn.Server(uvicorn.Config(app,log_level='error',access_log=False))
            thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True);thread.start()
            try:
                deadline=time.monotonic()+20
                while not server.started and time.monotonic()<deadline:time.sleep(.05)
                self.assertTrue(server.started)
                env=dict(os.environ,DICOM_EDITOR_URL=f'http://127.0.0.1:{port}',PYTHONDONTWRITEBYTECODE='1')
                env['DICOM_EDITOR_ARTIFACTS']=str(ROOT.parent/'dicom-editor-review')
                env.setdefault('NEURO_PLAYWRIGHT_MODULE',r'C:\Users\henri\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules\playwright')
                result=subprocess.run(['node',str(ROOT/'tests'/'dicom_editor_browser.cjs')],env=env,capture_output=True,text=True,timeout=120)
                self.assertEqual(result.returncode,0,result.stdout+'\n'+result.stderr)
                print(result.stdout)
            finally:
                server.should_exit=True;thread.join(timeout=10);core.resolve_ticket=original
                for key in list(core._SESSIONS):core.close_session(key)


if __name__=='__main__':unittest.main()
