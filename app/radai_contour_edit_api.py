"""HTTP boundary for the host contour editor (opaque tickets, bounded input)."""
import json
from fastapi import Request
from fastapi.responses import JSONResponse, Response, FileResponse
from starlette.concurrency import run_in_threadpool
import radai_contour_edit as core

PREFIX='/api/contour-edit'
MAX_PAYLOAD=512*1024


def montar(app):
    import radai_contour_discovery
    radai_contour_discovery.install(app)
    async def body(request):
        origin=request.headers.get('origin')
        if origin and origin.rstrip('/') != str(request.base_url).rstrip('/'):
            core.fail('INVALID_ORIGIN','Origem da requisição inválida.',403)
        if request.headers.get('sec-fetch-site')=='cross-site':
            core.fail('INVALID_ORIGIN','Origem da requisição inválida.',403)
        data=bytearray()
        async for chunk in request.stream():
            data.extend(chunk)
            if len(data)>MAX_PAYLOAD:
                core.fail('PAYLOAD_LIMIT','Traçado grande demais.',413)
        try:
            result=json.loads(data)
            if not isinstance(result,dict): raise ValueError()
            return result
        except (ValueError,UnicodeDecodeError):
            core.fail('INVALID_INPUT','Solicitação inválida.')

    def error(exc):
        if isinstance(exc,core.EditError):
            return JSONResponse({'error':exc.code,'erro':str(exc)},status_code=exc.status)
        # Do not expose patient paths or raw decoder errors through the API.
        import logging
        logging.getLogger(__name__).exception('Contour editor operation failed')
        return JSONResponse({'error':'EDIT_FAILED','erro':'Não foi possível concluir a edição. Confira a geometria e os arquivos de origem.'},status_code=400)

    @app.post(PREFIX+'/open')
    async def open_(request:Request):
        try:
            d=await body(request)
            return await run_in_threadpool(core.open_session,d.get('b'),d.get('source','thumbnail'),d.get('uid'),d.get('rs'))
        except Exception as exc: return error(exc)

    @app.get(PREFIX+'/state')
    def state(s:str):
        try:
            session=core.get_session(s)
            with session.lock: return session.state()
        except Exception as exc: return error(exc)

    @app.get(PREFIX+'/image')
    def image(s:str,plane:str='axial',index:int=0,center:float=None,width:float=None):
        try:
            session=core.get_session(s)
            with session.lock: png=session.image(plane,index,center,width)
            return Response(png,media_type='image/png',headers={'Cache-Control':'no-store'})
        except Exception as exc: return error(exc)

    @app.get(PREFIX+'/overlay')
    def overlay(s:str,roi:int,plane:str='axial',index:int=0,preview_id:str=None):
        try:
            session=core.get_session(s)
            with session.lock: return session.overlay(roi,plane,index,preview_id)
        except Exception as exc: return error(exc)

    def mutate(name,d):
        session=core.get_session(d.get('s'))
        with session.lock:
            session.check(d.get('csrf'),d.get('revision'))
            if name=='import':
                if type(d.get('discard',False)) is not bool:core.fail('INVALID_INPUT','Solicitação inválida.')
                return session.import_rs(d.get('rs'),d.get('discard',False))
            if name=='new-roi': return session.new_roi(d.get('name'),d.get('color',[255,80,80]))
            if name=='rename': return session.rename(d.get('roi'),d.get('name'))
            if name=='stroke': return session.stroke(d.get('roi'),d.get('plane'),d.get('index'),d.get('points'),d.get('diameter_mm',5),d.get('operation','brush'))
            if name in ('undo','redo'): return session.history(name=='redo')
            if name=='center': return session.center(d.get('roi'))
            if name=='scene': return session.scene(d.get('known'))
            if name=='interpolate':
                if type(d.get('apply',False)) is not bool:core.fail('INVALID_INPUT','Solicitação inválida.')
                return session.interpolate(d.get('roi'),d.get('plane'),d.get('start'),d.get('end'),d.get('apply',False),d.get('preview_id'))
            if name=='save': return session.save()
            if name=='close':
                core.close_session(session.id)
                return {'closed':True}
            core.fail('INVALID_OPERATION','Operação inválida.')

    for operation in ('import','new-roi','rename','stroke','undo','redo','interpolate','center','scene','save','close'):
        def handler(name):
            async def endpoint(request:Request):
                try:
                    d=await body(request)
                    return await run_in_threadpool(mutate,name,d)
                except Exception as exc: return error(exc)
            endpoint.__name__='contour_edit_'+name.replace('-','_')
            return endpoint
        app.add_api_route(PREFIX+'/'+operation,handler(operation),methods=['POST'])

    @app.get(PREFIX+'/download')
    def download(s:str,file:str):
        try:
            session=core.get_session(s)
            with session.lock: path=session.saved.get(file)
            if path is None or not path.is_file():
                core.fail('FILE_NOT_FOUND','A cópia não está mais disponível.',404)
            return FileResponse(str(path),filename=path.name,media_type='application/dicom',headers={'Cache-Control':'no-store'})
        except Exception as exc: return error(exc)
