import hashlib
import importlib.util
import json
import re
import sys
import threading
import time
from pathlib import Path, PureWindowsPath

PLUGIN_ID = 'neuro-rt'
HOST_CONTRACT = 'local-suite/plugins/1'
_MOUNT_LOCK = threading.RLock()
_UPDATE_PROVIDER = None


def check_plugin_release(plugin_id, installed_version):
    if _UPDATE_PROVIDER is None:
        raise RuntimeError("Conector NeuroRT ainda não montado.")
    return _UPDATE_PROVIDER.check_plugin_release(plugin_id, installed_version)


def request_plugin_update(plugin_id, action):
    if _UPDATE_PROVIDER is None:
        raise RuntimeError("Conector NeuroRT ainda não montado.")
    return _UPDATE_PROVIDER.request_plugin_update(plugin_id, action)


def _inside(root, relative):
    if not isinstance(relative, str) or not relative:
        raise ValueError('Caminho relativo inválido.')
    win = PureWindowsPath(relative)
    parts = relative.replace('\\', '/').split('/')
    reserved = {'CON', 'PRN', 'AUX', 'NUL'} | {p + str(n) for p in ('COM', 'LPT') for n in range(1, 10)}
    if (win.drive or win.root or any(p in ('', '.', '..') or p.endswith((' ', '.'))
            or p.split('.')[0].upper() in reserved for p in parts)
            or any(ord(c) < 32 or c in '<>:"|?*' for c in relative)):
        raise ValueError('Caminho fora do contrato de instalação.')
    root = Path(root).resolve()
    path = root.joinpath(*parts).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Caminho escapa da instalação.')
    return path


def _version(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d+(?:\.\d+)*', value):
        raise ValueError('Versão inválida.')
    parts = [int(n) for n in value.split('.')]
    while len(parts) > 1 and parts[-1] == 0:
        parts.pop()
    return tuple(parts)


def _json(path):
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise ValueError('Metadados de instalação inválidos.')
    return value


def discover_plugin(suite_root, plugin_id=PLUGIN_ID, host_info=None, *, cancelled=None):
    result = {'plugin_id': PLUGIN_ID, 'state': 'absent', 'reason': '', 'active_version': None}
    try:
        if plugin_id != PLUGIN_ID:
            raise ValueError('Plugin não autorizado.')
        plugin = _inside(suite_root, 'Plugins/NEURO RT')
        result['plugin_root'] = str(plugin)
        state_file = plugin / 'installation.json'
        if not state_file.is_file():
            return result
        state = _json(state_file)
        if state.get('schema') != 'neuro-rt/installation/1':
            raise ValueError('Schema de instalação inválido.')
        result['state'] = state.get('state', 'failed')
        result['installation_state'] = state
        if result['state'] == 'installed_pending_restart' and state.get('active_version'):
            result['pending_version'] = state.get('pending_version')
            result['state'] = 'ready'
        if result['state'] != 'ready':
            result['reason'] = 'Instalação aguardando preparo ou ativação.'
            return result
        version = state.get('active_version')
        _version(version)
        code = _inside(plugin, 'versions/' + version)
        manifest = _json(code / 'module.json')
        if (manifest.get('schema') != 'neuro-rt/plugin-manifest/1'
                or manifest.get('id') != PLUGIN_ID or manifest.get('version') != version
                or manifest.get('host_contract') != HOST_CONTRACT):
            raise ValueError('Manifesto não corresponde à instalação.')
        minimum = manifest.get('host_min_version')
        host_info = host_info or {}
        if (minimum is None or host_info.get('contract') != HOST_CONTRACT
                or _version(host_info.get('version')) < _version(minimum)):
            result.update(state='incompatible', reason='Atualize o Local Suite para a versão exigida pelo plugin.')
            return result
        python_rule = manifest.get('python', '')
        python_minimum = re.search(r'>=(\d+)\.(\d+)', python_rule)
        python_maximum = re.search(r'<(\d+)\.(\d+)', python_rule)
        if ((python_minimum and sys.version_info[:2] < tuple(map(int, python_minimum.groups()))) or
                (python_maximum and sys.version_info[:2] >= tuple(map(int, python_maximum.groups())))):
            result.update(state='incompatible', reason='O Python desta versão do Local Suite não atende o plugin.')
            return result
        inventory = _json(code / 'release-manifest.json')
        if (inventory.get('schema') != 'neuro-rt/release-package/1'
                or inventory.get('plugin_id') != PLUGIN_ID or inventory.get('version') != version):
            raise ValueError('Inventário da release não corresponde ao plugin.')
        files = inventory.get('files')
        if not isinstance(files, list) or not files:
            raise ValueError('Inventário de código ausente.')
        covered = set()
        for entry in files:
            if cancelled and cancelled():
                result.update(state='checking', reason='Verificação interrompida pelo encerramento do Local Suite.')
                return result
            name = entry.get('path')
            if not isinstance(name, str):
                raise ValueError('Entrada de inventário inválida.')
            if name.startswith('code/'):
                relative = name[5:]
                file = _inside(code, relative)
                if relative in covered:
                    raise ValueError('Inventário repete arquivo.')
                covered.add(relative)
            elif name.startswith(('models/', 'runtimes/')):
                file = _inside(plugin, name)
            else:
                raise ValueError('Artefato fora das áreas do plugin.')
            digest = entry.get('sha256')
            if (not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest)
                    or type(entry.get('size')) is not int or not file.is_file()
                    or file.stat().st_size != entry['size']):
                raise ValueError('Artefato da instalação incompleto ou inválido.')
            sha = hashlib.sha256()
            with file.open('rb') as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b''):
                    if cancelled and cancelled():
                        result.update(state='checking', reason='Verificação interrompida pelo encerramento do Local Suite.')
                        return result
                    sha.update(block)
            if sha.hexdigest() != digest:
                raise ValueError('Integridade de artefato não confirmada.')
        adapter = manifest.get('adapter', '')
        if not isinstance(adapter, str) or adapter.count(':') != 1:
            raise ValueError('Adaptador inválido.')
        adapter_file, function = adapter.split(':')
        _inside(code, adapter_file)
        if (adapter_file not in covered or 'module.json' not in covered
                or not re.fullmatch('[A-Za-z_]\\w*', function)):
            raise ValueError('Adaptador não protegido pelo inventário.')
        for file in code.rglob('*.py'):
            if file.relative_to(code).as_posix() not in covered:
                raise ValueError('Código Python não previsto na release.')
        result.update(state='ready', reason='', active_version=version,
                      code_dir=str(code), manifest=manifest, adapter_file=adapter_file,
                      adapter_function=function)
    except (OSError, ValueError, TypeError, AttributeError, KeyError) as error:
        result.update(state='failed', reason=str(error))
    return result


def mount_plugin(app, installation, host_services):
    with _MOUNT_LOCK:
        return _mount_plugin(app, installation, host_services)


def _mount_plugin(app, installation, host_services):
    if installation.get('state') != 'ready':
        return {'mounted': False, 'reason': installation.get('reason', 'Plugin indisponível.')}
    previous = getattr(app.state, 'neuro_plugin_mount', None)
    if previous is not None:
        if previous['version'] != installation['active_version']:
            raise RuntimeError('Reabra o Local Suite para ativar a nova versão do plugin.')
        return previous
    if host_services is None:
        raise RuntimeError('Serviços compartilhados do host não foram fornecidos.')
    sys.dont_write_bytecode = True
    code = Path(installation['code_dir']).resolve()
    path = _inside(code, installation['adapter_file'])
    if str(code) not in sys.path:
        sys.path.insert(0, str(code))
    spec = importlib.util.spec_from_file_location('_radai_neuro_adapter', path)
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    service = getattr(adapter, installation['adapter_function'])(app, code, host_services=host_services)
    receipt = {'mounted': True, 'version': installation['active_version'], 'service': service}
    app.state.neuro_plugin_mount = receipt
    return receipt


def _support(installation, name):
    sys.dont_write_bytecode = True
    path = _inside(installation['code_dir'], 'integration/' + name + '.py')
    key = '_local_suite_neuro_' + name
    spec = importlib.util.spec_from_file_location(key, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[key] = module
    spec.loader.exec_module(module)
    return module


def build_host_services(installation, host_info, cfg=None):
    cfg = cfg or {}
    provided = cfg.get('neuro_host_services')
    if provided is not None and not isinstance(provided, dict):
        return provided(host_info) if callable(provided) else provided
    bindings = _support(installation, 'default_host_services').bindings_for_host(host_info, cfg)
    bindings.update(dict(provided or {}))

    def queue_factory():
        import radai_queue_state
        required = ('enqueue_neuro', 'try_neuro_turn', 'report_neuro',
                    'finish_neuro', 'cancel_neuro')
        if not all(callable(getattr(radai_queue_state, n, None)) for n in required):
            raise RuntimeError('A fila compartilhada do host precisa ser atualizada.')
        return _support(installation, 'queue_bridge').QueueBridge(radai_queue_state)

    return _support(installation, 'host_services').build_host_services(
        host_info, bindings, queue_bridge_factory=queue_factory)


def _host_info(suite_root, cfg):
    version = cfg.get('neuro_host_version')
    if version is None:
        import radai_version
        version = radai_version._entrega_txt()
    return {'contract': HOST_CONTRACT, 'version': str(version),
            'suite_root': str(suite_root)}


def _installation_hint(suite_root):
    result = {'plugin_id': PLUGIN_ID, 'state': 'absent', 'reason': '', 'active_version': None}
    try:
        plugin = _inside(suite_root, 'Plugins/NEURO RT')
        result['plugin_root'] = str(plugin)
        pointer = _inside(plugin, 'installation.json')
        if not pointer.is_file():
            return result
        if pointer.stat().st_size > 64 * 1024:
            raise ValueError('Estado da instalação excede o limite permitido.')
        state = _json(pointer)
        if state.get('schema') != 'neuro-rt/installation/1':
            raise ValueError('Estado da instalação inválido.')
        if state.get('active_version'):
            _version(state['active_version'])
        result.update(state='checking', reason='Verificando a instalação do NEURO RT em segundo plano.')
    except (OSError, ValueError, TypeError, KeyError):
        result.update(state='failed', reason='Não foi possível ler o estado da instalação do NEURO RT.')
    return result


def montar(app, cfg=None):
    global _UPDATE_PROVIDER
    import secrets
    from fastapi import HTTPException, Request
    from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
    from starlette.concurrency import run_in_threadpool

    previous = getattr(app.state, 'neuro_plugin_entry', None)
    if previous is not None:
        return previous
    cfg = dict(cfg or {})
    base = Path(__file__).resolve().parent
    if base.name == 'app' and (base.parent / 'tools').is_dir():
        base = base.parent
    suite_root = Path(cfg.get('suite_root') or base).resolve()
    info = _host_info(suite_root, cfg)
    installation = _installation_hint(suite_root)
    entry = {'installation': installation, 'receipt': None,
             'token': secrets.token_urlsafe(32), 'host_services': None}
    entry.update(load_lock=threading.RLock(), load_complete=threading.Event(),
                 closed=threading.Event(), load_thread=None, release_thread=None,
                 load_started=False, release_checked_at=0.0,
                 release_check={'state': 'checking', 'reason': 'Consultando a versão disponível.'})
    app.state.neuro_plugin_entry = entry
    import radai_neuro_install
    provider = radai_neuro_install.build_provider(suite_root, info, cfg)
    entry['update_provider'] = provider
    _UPDATE_PROVIDER = provider
    cfg.setdefault('neuro_install', provider.install)

    def load_installation():
        try:
            import radai_queue_state as queue
            if queue.quem_tem_a_vez().get('dono') or queue.fechando_ao_fim():
                entry['installation'] = dict(entry['installation'],
                    reason='Aguardando a fila terminar para verificar o NEURO RT.')
            while queue.quem_tem_a_vez().get('dono') or queue.fechando_ao_fim():
                if entry['closed'].wait(.1):
                    return
            if entry['closed'].is_set():
                return
            entry['installation'] = dict(entry['installation'], reason='Verificando a instalação do NEURO RT.')
            verified = discover_plugin(suite_root, host_info=info, cancelled=entry['closed'].is_set)
            if entry['closed'].is_set():
                return
            if verified['state'] != 'ready':
                entry['installation'] = verified
                return
            entry['installation'] = dict(verified, state='loading', reason='Conectando o NEURO RT à fila da suíte.')
            while queue.quem_tem_a_vez().get('dono') or queue.fechando_ao_fim():
                if entry['closed'].wait(.1):
                    return
            if entry['closed'].is_set():
                return
            services = build_host_services(verified, info, cfg)
            if entry['closed'].is_set():
                return
            receipt = mount_plugin(app, verified, services)
            app.openapi_schema = None
            if entry['closed'].is_set():
                close = getattr(receipt.get('service'), 'close', None)
                if callable(close):
                    close()
                return
            entry.update(installation=verified, host_services=services, receipt=receipt)
        except Exception:
            import logging
            logging.getLogger(__name__).exception('Falha na montagem em segundo plano do plugin NEURO RT')
            if not entry['closed'].is_set():
                entry['installation'] = dict(entry['installation'], state='failed',
                    reason='Não foi possível conectar o plugin. Reabra ou repare a instalação.')
        finally:
            entry['load_complete'].set()

    def check_release():
        try:
            result = provider.check_plugin_release(PLUGIN_ID, entry['installation'].get('active_version'))
        except Exception:
            result = {'state': 'unavailable', 'reason': 'Não foi possível consultar a versão disponível.'}
        if not entry['closed'].is_set():
            entry['release_check'] = result
            entry['release_checked_at'] = time.monotonic()

    def ensure_background_work():
        with entry['load_lock']:
            if entry['closed'].is_set():
                return
            if entry['installation']['state'] == 'checking' and not entry['load_started']:
                entry['load_started'] = True
                entry['load_thread'] = threading.Thread(target=load_installation, name='neuro-verify-mount', daemon=True)
                entry['load_thread'].start()
            release_thread = entry['release_thread']
            if ((release_thread is None or not release_thread.is_alive()) and
                    (not entry['release_checked_at'] or time.monotonic() - entry['release_checked_at'] >= 60)):
                entry['release_thread'] = threading.Thread(target=check_release, name='neuro-release-check', daemon=True)
                entry['release_thread'].start()

    async def close_background_work():
        entry['closed'].set()
        for worker in (entry['load_thread'], entry['release_thread']):
            if worker is not None and worker.is_alive():
                await run_in_threadpool(worker.join, .5)

    app.router.add_event_handler('shutdown', close_background_work)

    def local(request):
        client = request.client.host if request.client else ''
        allowed = ('127.0.0.1', '::1', 'localhost')
        if client == 'testclient':
            allowed += ('testserver',)
        if client not in allowed + ('testclient',) or request.url.hostname not in allowed:
            raise HTTPException(403, 'Acesso local obrigatório.')
        if request.headers.get('sec-fetch-site') == 'cross-site':
            raise HTTPException(403, 'Origem não permitida.')

    def public_status():
        current = entry['installation']
        consent = provider.consent_status()
        return {'plugin_id': PLUGIN_ID, 'state': current['state'],
                'reason': current.get('reason', ''),
                'active_version': current.get('active_version'),
                'mounted': bool((entry['receipt'] or {}).get('mounted')),
                'install_available': callable(cfg.get('neuro_install')),
                'token': entry['token'],
                'release_check': entry.get('release_check'),
                'update': provider.status(),
                'consent': {'policy': provider.consent_policy(),
                            'installation_accepted': consent.get('installation_accepted') is True,
                            'first_use_accepted': consent.get('first_use_accepted') is True}}

    def landing():
        import html
        import radai_menu
        import radai_modules
        status = public_status()
        states = {'absent': 'O plugin NEURO RT ainda não está instalado.',
                  'failed': 'O plugin não pôde ser carregado.',
                  'incompatible': 'Esta versão requer outro Local Suite.',
                  'checking': 'Verificando a instalação do NEURO RT.',
                  'loading': 'Conectando o NEURO RT à suíte.',
                  'downloading': 'Baixando os arquivos do plugin.',
                  'preparing': 'Preparando o plugin.',
                  'activating': 'Ativando o plugin.'}
        message = states.get(status['state'], 'O plugin aguarda ativação.')
        content = ('<section class="md-pg"><h1>NEURO RT</h1><p role="status">' +
                   html.escape(message) + '</p><p>' + html.escape(status['reason']) + '</p>')
        content += ('<section id="neuro-update" data-neuro-install="1">'
                    '<p id="neuro-update-message" role="status"></p>'
                    '<progress id="neuro-update-progress" max="100" hidden></progress>'
                    '<div id="neuro-update-actions"></div></section>'
                    '<p>O preparo baixa código, ambiente e modelos licenciados. Confirme para iniciar.</p>'
                    '<p><a href="/">Voltar à suíte</a></p></section>')
        script = ('<script>window.NEURO_INSTALL_CATALOG=' +
                  json.dumps(radai_neuro_install.INSTALL_UI_CATALOG, ensure_ascii=True).replace('<', '\\u003c') +
                  ';' + radai_neuro_install.INSTALL_UI_SCRIPT + '</script>')
        page = ('<!doctype html><html><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                '<title>NEURO RT · Local Suite</title><style>' + radai_modules.CSS +
                '</style></head><body>' + content + script + '</body></html>')
        return radai_menu.aplicar(page, 'neuro')

    @app.get('/api/plugins/neuro-rt')
    def status(request: Request):
        local(request)
        ensure_background_work()
        return JSONResponse(public_status(), headers={'Cache-Control': 'no-store'})

    async def accept_installation_terms(payload):
        try:
            current = await run_in_threadpool(provider.consent_status)
            if current.get('installation_accepted') is not True or 'consent' in payload:
                acknowledgement = payload.get('consent')
                if not isinstance(acknowledgement, dict):
                    raise ValueError('Aceite explícito ausente.')
                await run_in_threadpool(provider.accept_consent, acknowledgement)
        except (ValueError, TypeError, OSError):
            raise HTTPException(400, 'Leia e aceite a versão atual do termo do plugin NEURO RT.')

    @app.post('/api/plugins/neuro-rt/install')
    async def install(request: Request):
        local(request)
        origin = request.headers.get('origin')
        if (origin not in (None, str(request.base_url).rstrip('/')) or
                not secrets.compare_digest(request.headers.get('x-neuro-plugin-token', ''), entry['token'])):
            raise HTTPException(403, 'Origem ou token inválido.')
        body = await request.body()
        if not 0 < len(body) <= 4096:
            raise HTTPException(400, 'Pedido inválido.')
        try:
            payload = json.loads(body)
        except (ValueError, UnicodeError):
            raise HTTPException(400, 'Pedido inválido.')
        if (not isinstance(payload, dict) or set(payload) not in ({'confirm'}, {'confirm', 'consent'})
                or payload['confirm'] is not True):
            raise HTTPException(400, 'Confirmação explícita obrigatória.')
        callback = cfg.get('neuro_install')
        if not callable(callback):
            raise HTTPException(501, 'Instalação ainda não conectada nesta versão do Local Suite.')
        await accept_installation_terms(payload)
        result = await run_in_threadpool(callback)
        if not isinstance(result, dict):
            raise HTTPException(500, 'O instalador não devolveu um estado válido.')
        return JSONResponse(result, status_code=202, headers={'Cache-Control': 'no-store'})

    @app.post('/api/plugins/neuro-rt/update')
    async def update(request: Request):
        local(request)
        if (request.headers.get('origin') not in (None, str(request.base_url).rstrip('/')) or
                not secrets.compare_digest(request.headers.get('x-neuro-plugin-token', ''), entry['token'])):
            raise HTTPException(403, 'Origem ou token inválido.')
        body = await request.body()
        if not 0 < len(body) <= 4096:
            raise HTTPException(400, 'Pedido inválido.')
        try:
            payload = json.loads(body)
            if (not isinstance(payload, dict) or set(payload) not in ({'action'}, {'action', 'consent'})
                    or payload.get('action') not in ('comecar', 'esperar', 'interromper')):
                raise ValueError()
            await accept_installation_terms(payload)
            result = await run_in_threadpool(provider.request_plugin_update, PLUGIN_ID, payload['action'])
        except (ValueError, TypeError, UnicodeError):
            raise HTTPException(400, 'Ação de atualização inválida.')
        return JSONResponse(result, status_code=202, headers={'Cache-Control': 'no-store'})

    @app.get('/neuro')
    def neuro(request: Request):
        local(request)
        ensure_background_work()
        if (entry['receipt'] or {}).get('mounted'):
            return RedirectResponse('/neuro/', status_code=307)
        return HTMLResponse(landing(), headers={'Cache-Control': 'no-store'})

    @app.get('/neuro/nidus')
    def nidus(request: Request):
        local(request)
        if not (entry['receipt'] or {}).get('mounted'):
            return RedirectResponse('/neuro', status_code=307)
        return RedirectResponse('/nidus/projecao', status_code=307)

    def study_route(category):
        def study(request: Request):
            local(request)
            if not (entry['receipt'] or {}).get('mounted'):
                return RedirectResponse('/neuro', status_code=307)
            return RedirectResponse('/neuro/?category=' + category, status_code=307)
        return study

    for category in ('glioma', 'metastasis', 'meningioma', 'anatomia'):
        app.get('/neuro/' + category)(study_route(category))

    return entry
