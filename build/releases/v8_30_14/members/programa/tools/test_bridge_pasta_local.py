"""Run the local folder and file/ZIP browser regression against isolated Bridge routes."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import zipfile


def run(work, screenshot, mr=False):
    from PIL import Image
    import uvicorn
    from fastapi import FastAPI, Request

    tools = Path(__file__).resolve().parent
    sys.path.insert(0, str(tools))
    import _componentes
    _componentes.ligar_caminho()
    import radai_batch
    import radai_bridge
    import radai_languages
    import radai_varrer
    from test_bridge_tela import escrever_tc, escrever_rm

    folder = work / 'Exames sintéticos' / 'TC de demonstração'
    escrever_tc(str(folder), n=8, descricao='TC SINTETICA BRIDGE')
    image = work / 'fantoma.png'
    Image.new('L', (64, 64), 140).save(image)
    archive = work / 'fantoma.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as output:
        for file in sorted(folder.glob('*.dcm')):
            output.write(file, 'TC/' + file.name)

    mr_folder = folder.parent / 'Quatro séries de RM'
    delivery = work / 'Entrega de teste'
    delivery.mkdir()
    if mr:
        from pydicom import dcmread
        from pydicom.uid import generate_uid
        study, frame = generate_uid(), generate_uid()
        for number, sequence in enumerate(('T1 sem contraste','T1 pós-contraste','T2','FLAIR'), start=1):
            series_folder = mr_folder / ('s' + str(number))
            escrever_rm(str(series_folder), n=6, numero=number, descricao='RM FANTOMA ' + sequence, estudo=study)
            for file in series_folder.glob('*.dcm'):
                ds=dcmread(file)
                ds.SpecificCharacterSet='ISO_IR 192'
                ds.SeriesDescription='RM FANTOMA ' + sequence
                ds.PatientName='FANTOMA BRIDGE'
                ds.PatientID='PESQUISA-04'
                ds.FrameOfReferenceUID=frame
                ds.save_as(file, enforce_file_format=True)

    api = FastAPI()
    @api.get('/api/bridge/destinos')
    def test_destination():
        return {'downloads':str(delivery)}

    @api.get('/api/lote/opcoes')
    def options(modalidade='CT'):
        return radai_batch.opcoes_da_tela(modalidade)

    radai_languages.montar(api)
    radai_bridge.montar(api)
    radai_varrer.montar(api)

    @api.post('/api/lote/pastas')
    async def folders(request: Request):
        body = await request.json()
        # Keep other directories and mounted network drives out of the fixture.
        requested = Path(body.get('caminho') or folder.parent).resolve()
        if requested != folder.parent and folder.parent not in requested.parents:
            return {'erro':'Fora da demonstração'}
        result = radai_batch.listar_pastas_do_explorador(
            str(requested), body.get('busca', ''), body.get('ordem', 'nome'), body.get('sentido', 'asc'))
        if body.get('unidades'):
            result['unidades'] = [{'raiz': str(folder.parent), 'ok': True}]
        return result

    @api.post('/api/lote/favorita')
    def favorite():
        return {'favorita': str(folder.parent)}

    # Register the normal illustration route after the isolated folder routes.
    radai_batch.montar(api)
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    sock.listen(32)
    cfg = uvicorn.Config(api, log_level='warning', access_log=False, loop='asyncio', http='h11', ws='none', lifespan='off')
    server = uvicorn.Server(cfg)
    thread = threading.Thread(target=server.run, kwargs={'sockets':[sock]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 25
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(.05)
        if not server.started:
            import traceback
            stalled=sys._current_frames().get(thread.ident)
            raise RuntimeError('O servidor isolado não iniciou. ' + ''.join(traceback.format_stack(stalled)))
        args = {'origin':'http://127.0.0.1:' + str(sock.getsockname()[1]), 'folder':str(folder),
                'file':str(image), 'zip':str(archive), 'mr_folder':str(mr_folder),'destination':str(delivery),
                'screenshot':str(screenshot) if screenshot else None}
        controller = 'test_bridge_rm_por_serie.cjs' if mr else 'test_bridge_pasta_local.cjs'
        subprocess.run(['node', str(tools / controller), json.dumps(args)],
                       check=True, timeout=140)
    finally:
        server.should_exit = True
        thread.join(10)
        sock.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--screenshot', type=Path)
    parser.add_argument('--rm', action='store_true', help='Validar entrega e seleção independente de quatro séries de RM.')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='bridge_pasta_') as tmp:
        work = Path(tmp).resolve()
        for key, leaf in [('RADAI_TMP','tmp'),('LOCALAPPDATA','appdata'),('RADAI_REGISTRO_DIR','registro')]:
            dest = work / leaf
            dest.mkdir()
            os.environ[key] = str(dest)
        config = work / 'isolated.config'
        watch_root = work / 'vigia'
        watch_root.mkdir()
        config.write_text('ROOT=' + str(watch_root) + '\nDRY_RUN=1\nMIN_SLICES=5\n', encoding='utf-8')
        os.environ.update(RADAI_CONFIG=str(config), RADAI_NOTIFICACAO='0', RADAI_URL_VERSOES='0')
        run(work, args.screenshot,args.rm)
