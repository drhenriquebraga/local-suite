"""Opt-in real ZIP streaming round trip. Uses only a synthetic installation."""
import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'app'))
if os.environ.get('CONTOURLAB_SOURCE'):
    sys.path.insert(1,str(Path(os.environ['CONTOURLAB_SOURCE'])/'app'))


def serve(folder,port):
    folder=Path(folder)
    for name in ('RADAI_CALIB_DIR','RADAI_REGISTRO_DIR','TOTALSEG_HOME_DIR','RADAI_TMP'):
        os.environ[name]=str(folder/name)
    config=folder/'watcher.config';config.write_text('ROOT=\nPORT=%d\n'%port,encoding='ascii')
    os.environ['RADAI_CONFIG']=str(config)
    # Install isolation/network guards before importing the self-mounting panel.
    from unittest.mock import patch
    import uvicorn
    import radai_lung_install as sdk
    import radai_plugin_setup
    import radai_lung_plugin
    import radai_panel
    sdk._request=lambda *a,**k:(_ for _ in ()).throw(AssertionError('External network forbidden in fixture'))
    class Installer:
        def __init__(self,*a,**k):pass
        def launch(self,plan):
            (folder/'captured-plan.json').write_text(json.dumps(plan),encoding='utf8')
            return {'ok':True,'scheduled':True}
    radai_plugin_setup.ExternalInstaller=Installer
    original_panel=radai_panel.montar
    def panel(app,ler_vigia=None,config=None):
        return original_panel(app,ler_vigia,dict(config or {},suite_root=str(folder),arranque={'PORT':port}))
    guard=patch('http.client.HTTPSConnection.connect',side_effect=AssertionError('External network forbidden in fixture'))
    guard.start()
    with patch.object(radai_panel,'montar',side_effect=panel):
        import radai_watcher
    if os.environ.get('CONTOURLAB_SOURCE'):
        assert Path(radai_watcher.__file__).resolve()==(Path(os.environ['CONTOURLAB_SOURCE'])/'app/radai_watcher.py').resolve()
    # Use the actual panel, including its global origin/host/body middleware.
    app=radai_watcher.app
    app.state.radai_reabertura={'encerrar':lambda:None}
    host_version=next(line.split('=',1)[1].strip() for line in (folder/'entrega.txt').read_text(encoding='utf-8-sig').splitlines() if line.startswith('VERSAO='))
    radai_lung_plugin.montar(app,{'suite_root':str(folder),'neuro_host_version':host_version,'port':port,
                                'lung_cfg':{'ROOT':str(folder/'EMPTY-SYNTHETIC-INPUT')}})
    radai_watcher.montar_portao_do_host(app,porta=port)
    uvicorn.run(app,host='127.0.0.1',port=port,log_level='warning')


def run(bundle):
    import radai_plugin_bootstrap as boot
    import radai_lung_install as sdk
    sdk._request=lambda *a,**k:(_ for _ in ()).throw(AssertionError('External network forbidden in fixture'))
    bundle=Path(bundle).resolve()
    with tempfile.TemporaryDirectory(prefix='lung-bundle-http-synthetic-') as directory:
        folder=Path(directory)
        (folder/'entrega.txt').write_bytes((ROOT/'entrega.txt').read_bytes())
        boot.ensure_base(folder,'lung-rt',installed_only=False)
        before=json.loads((folder/'Plugins/LUNG RT/installation.json').read_bytes())
        code_version=before['active_version']
        sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
        flags=getattr(subprocess,'CREATE_NO_WINDOW',0)
        server=subprocess.Popen([sys.executable,'-B',str(Path(__file__)), '--serve',str(folder),'--port',str(port)],creationflags=flags)
        def request(method,path,body=None,headers=None):
            connection=http.client.HTTPConnection('127.0.0.1',port,timeout=300)
            try:
                connection.request(method,path,body=body,headers=headers or {})
                response=connection.getresponse();data=json.loads(response.read())
                if response.status>=400:raise AssertionError((response.status,data))
                return data
            finally:connection.close()
        try:
            for _ in range(120):
                if server.poll() is not None:raise AssertionError('Synthetic server stopped')
                try:status=request('GET','/api/plugins/lung-rt');break
                except (OSError,http.client.HTTPException):time.sleep(.25)
            else:raise AssertionError('Synthetic server did not start')
            assert status['code_version']==code_version and status['weights']['state']=='missing',status
            token=status['token']
            def chunks():
                sent=0;checkpoint=0
                with bundle.open('rb') as stream:
                    while block:=stream.read(1024**2):
                        sent+=len(block)
                        if sent-checkpoint>=256*1024**2:
                            checkpoint=sent;print('Streaming local ZIP:',round(sent/1024**3,2),'GiB',flush=True)
                        yield block
            source=request('POST','/api/plugins/lung-rt/local/upload?operation=weights',chunks(),{
                'Content-Type':'application/zip','Content-Length':str(bundle.stat().st_size),'X-Lung-Plugin-Token':token})
            assert source['offline'] and source['operation']=='weights',source
            assert list((folder/'Plugins/LUNG RT/staging/local-setup').glob('setup-*/setup.zip'))
            print('Actual large ZIP upload and authentication passed.',flush=True)
            consent=status['policy']
            request('POST','/api/plugins/lung-rt/install',json.dumps({'source_id':source['source_id'],'operation':'weights',
                'consent':{'accepted':True,'version':consent['version'],'digest':consent['digest']}}),{
                'Content-Type':'application/json','X-Lung-Plugin-Token':token})
            plan=json.loads((folder/'captured-plan.json').read_bytes())
            assert plan['resources_only'] and plan['offline'] and plan['version']=='1.1.2',plan
            sdk.run_external(plan,lambda event:print('Preparing:',event.get('component',event['stage']),flush=True),
                             suite_root=folder,host_python=sys.executable)
            after=json.loads((folder/'Plugins/LUNG RT/installation.json').read_bytes())
            assert all(after[key]==before[key] for key in ('active_version','code_path','inventory_sha256'))
            result=request('GET','/api/plugins/lung-rt')
            assert result['weights']['state']=='ready' and result['weights']['version']=='1.1.2',result
            assert result['code_version']==code_version
            assert not (folder/'python').exists()
            assert not list((folder/'Plugins/LUNG RT/data').rglob('license.json'))
            receipt={'code_version':code_version,'bundle_version':'1.1.2','zip_bytes':bundle.stat().st_size,
                     'http_streaming_verified':True,'full_panel_middleware':True,'network_forbidden':True,'weights_ready':True,
                     'code_preserved':True,'no_python_copy':True,'no_model_terms_fabricated':True}
            target=Path(tempfile.gettempdir())/'lung-large-bundle-v819-result.json'
            target.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8')
            print(json.dumps(receipt),flush=True)
        finally:
            server.terminate();server.wait(timeout=20)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--serve');parser.add_argument('--port',type=int);parser.add_argument('--bundle')
    args=parser.parse_args()
    if args.serve:serve(args.serve,args.port)
    elif args.bundle:run(args.bundle)
    else:parser.error('Use --bundle with a locally prepared LUNG bundle.')
