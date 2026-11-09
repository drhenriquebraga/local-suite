import json
from pathlib import Path

SCHEMA = 'local-suite/profile/1'
PROFILES = ('full', 'lung-rt')

def raiz():
    base = Path(__file__).resolve().parent
    return base.parent if base.name == 'app' else base

def perfil(root=None):
    path = Path(root) / 'suite-profile.json' if root is not None else raiz() / 'suite-profile.json'
    if not path.exists():
        return 'full'
    try:
        if path.stat().st_size > 4096:
            return 'lung-rt'
        value = json.loads(path.read_text(encoding='utf-8-sig'))
        if value.get('schema') != SCHEMA or value.get('profile') not in PROFILES:
            return 'lung-rt'
        return value['profile']
    except (OSError, ValueError, AttributeError):
        return 'lung-rt'

def completo(root=None):
    return perfil(root) == 'full'


def montar_portao(app, root=None):
    if getattr(app.state, 'installation_profile_guard', False):
        return
    app.state.installation_profile_guard = True

    @app.middleware('http')
    async def capabilities(request, call_next):
        if perfil(root) == 'lung-rt':
            from fastapi.responses import JSONResponse
            path = request.url.path.rstrip('/') or '/'
            denied = ('/bridge', '/elastic', '/bolus', '/neuro', '/nidus',
                      '/api/bridge', '/api/elastic', '/api/bolus', '/api/neuro', '/api/nidus',
                      '/api/recon3d/vascular', '/api/fila/neuro', '/api/plugins/neuro-rt', '/autocontorno')
            blocked = any(path == prefix or path.startswith(prefix + '/') for prefix in denied)
            if path == '/recon3d' or (path.startswith('/recon3d/') and path != '/recon3d/toracica'):
                blocked = True
            if path == '/api/recon3d/acervo' and request.query_params.get('ferramenta') != 'toracica':
                blocked = True
            if blocked:
                return JSONResponse({'detail':'Disponível na Local Suite completa'}, status_code=403,
                                    headers={'Cache-Control':'no-store'})
        return await call_next(request)
