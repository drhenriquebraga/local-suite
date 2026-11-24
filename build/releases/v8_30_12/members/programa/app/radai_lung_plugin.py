import json
from pathlib import Path
import secrets
import threading
import time

_ENTRY = None


def preparing():
    return bool(_ENTRY and _ENTRY.get('preparing'))


def host_services(root, cfg):
    import radai_languages
    import radai_menu
    import radai_ui
    import radai_series_source
    plugin = Path(root) / 'Plugins/LUNG RT'
    core_cfg = dict(cfg.get('lung_cfg') or cfg.get('lote') or cfg)
    import radai_lung_install as sdk
    resource_root = plugin
    try:
        stamp = sdk._json(plugin/'installation.json')
        if stamp.get('resources_path'):
            resource_root = sdk._inside(plugin,stamp['resources_path'])
    except (OSError,ValueError):
        pass
    return {'suite_root':Path(root), 'installation_root':plugin, 'data_dir':plugin/'data',
            'resources_dir':resource_root/'runtimes/nvreason', 'model_root':resource_root/'models/nv-reason-ct-int4',
            'consent_path':plugin/'config/consent.json', 'lung_cfg':core_cfg, 'config':core_cfg,
            'resolve_series':radai_series_source.resolve_selection,
            'language':lambda request=None: radai_languages.idioma_do_config(),
            'ui_apply':lambda page, active='lung':radai_ui.com_portao(radai_menu.aplicar(page,active)),
            **dict(cfg.get('lung_host_services') or {})}


def _policy():
    import radai_lung_install
    policy = getattr(radai_lung_install,'CONSENT_POLICY',None)
    if not isinstance(policy,dict) or not policy.get('digest'):
        raise ValueError('Termos LUNG RT indisponíveis. Atualize a suíte.')
    return policy


def _accepted(root):
    import radai_lung_install as sdk
    try:
        value = sdk._json(sdk._inside(root,'Plugins/LUNG RT/config/consent.json'),8192)
        policy = _policy()
        return value.get('schema') == 'lung-rt/consent-receipt/1' and value.get('accepted') is True and value.get('digest') == policy['digest'] and value.get('version') == policy['version']
    except (OSError, ValueError):
        return False


def install_queue_status():
    import radai_atualizar as updater
    import radai_queue_state as queue

    summary = queue.resumo()
    owner = queue.quem_tem_a_vez()
    active = owner.get('dono') or summary.get('rodando') or updater.o_que_segura(updater._status())
    pending = max(summary.get('esperando', 0), summary.get('vigia_na_fila', 0), int(bool(owner.get('lote_quer'))))
    return {'active': bool(active), 'pending': pending}


def montar(app,cfg=None):
    global _ENTRY
    from fastapi import FastAPI,Request,HTTPException
    from fastapi.responses import HTMLResponse,JSONResponse
    from starlette.concurrency import run_in_threadpool
    from starlette.routing import Match,Mount
    import radai_plugins
    import radai_lung_install as sdk
    import radai_install_profile
    cfg = dict(cfg or {})
    if getattr(app.state,'lung_plugin_entry',None):
        return app.state.lung_plugin_entry
    root = Path(cfg.get('suite_root') or radai_install_profile.raiz()).resolve()
    info = radai_plugins._host_info(root,cfg)
    install = {'state':'checking','active_version':None,'reason':''}
    entry = {'installation':install,'token':secrets.token_urlsafe(32),'sources':{},
             'release':{'state':'checking'},'lock':threading.RLock(),'preparing':False,'closed':False}
    entry.update(load_complete=threading.Event(),active_routes=frozenset())
    _ENTRY = entry
    app.state.lung_plugin_entry = entry
    def local(request, mutation=False):
        host = request.client.host if request.client else ''
        allowed = ('localhost','127.0.0.1','::1')
        if host == 'testclient':
            allowed += ('testclient','testserver')
        if host not in allowed or request.url.hostname not in allowed or request.headers.get('sec-fetch-site') == 'cross-site':
            raise HTTPException(403,'Acesso local obrigatório.')
        if mutation and (request.headers.get('origin') not in (None,str(request.base_url).rstrip('/')) or
                not secrets.compare_digest(request.headers.get('x-lung-plugin-token',''),entry['token'])):
            raise HTTPException(403,'Origem ou token inválido.')

    async def body(request):
        raw = await request.body()
        if not 0 < len(raw) <= 8192:
            raise HTTPException(400,'Pedido inválido.')
        try:
            value=json.loads(raw)
            if not isinstance(value,dict):
                raise ValueError()
            return value
        except (ValueError,UnicodeError):
            raise HTTPException(400,'Pedido inválido.')

    def refresh():
        result = sdk.check_latest(entry['installation'].get('active_version'))
        with entry['lock']:
            entry['release']=result
        return result

    @app.get('/api/plugins/lung-rt/startup')
    def startup(request:Request):
        local(request)
        return JSONResponse({'finished':entry['load_complete'].is_set()},headers={'Cache-Control':'no-store'})

    @app.get('/api/plugins/lung-rt')
    def status(request:Request):
        from radai_plugin_setup import last_result

        local(request)
        try:
            policy=_policy()
        except ValueError:
            policy=None
        return JSONResponse({'suite_fingerprint':sdk.suite_identity(root),'state':entry['installation']['state'],'version':entry['installation'].get('active_version'),
                'code_version':entry['installation'].get('active_version'), 'weights':sdk.weights_status(root),
                'reason':entry['installation'].get('reason',''),'token':entry['token'],
                'release':entry['release'],'preparing':entry['preparing'],
                'last_result':last_result(root, 'lung-rt'),
                'policy':policy,'accepted':_accepted(root),'queue':install_queue_status()},headers={'Cache-Control':'no-store'})

    @app.post('/api/plugins/lung-rt/refresh')
    async def refresh_route(request:Request):
        local(request,True)
        return await run_in_threadpool(refresh)

    def remember_source(description, operation='weights'):
        source_id = secrets.token_urlsafe(24)
        with entry['lock']:
            entry['sources'] = {k:v for k,v in entry['sources'].items() if time.monotonic()-v['time'] < 900}
            if len(entry['sources']) >= 8:
                entry['sources'].pop(next(iter(entry['sources'])))
            entry['sources'][source_id] = {'time':time.monotonic(), 'description':description,'operation':operation}
        return {'source_id':source_id, 'version':description['version'],
                'offline':description.get('offline', False), 'format':description.get('format', 'setup_folder'),'operation':operation}

    @app.post('/api/plugins/lung-rt/connectivity')
    async def connectivity(request:Request):
        from radai_plugin_sources import connectivity as probe, read_metadata

        local(request, True)
        return await probe(lambda origin: sdk.lookup_origin(origin, read_metadata))

    @app.post('/api/plugins/lung-rt/local/upload')
    async def upload_setup(request:Request):
        from radai_plugin_sources import SetupUploadError, receive_setup

        local(request, True)
        purpose = request.query_params.get('operation','weights')
        if purpose == 'code':
            raise HTTPException(400,{'code':'SUITE_CODE_UPDATE_REQUIRED','message':'O código dos plugins é atualizado pelo instalador principal da Local Suite.'})
        if purpose != 'weights':
            raise HTTPException(400,'Operação de instalação inválida.')
        def inspect(path):
            description = sdk.inspect_local_source(path)
            if purpose=='weights' and not description.get('offline'):
                raise ValueError('Escolha o bundle de pesos completo preparado para levar.')
            return description
        try:
            description = await receive_setup(request,root,'lung-rt',inspect,
                sdk.MAX_BUNDLE if purpose=='weights' else sdk.MAX_SETUP)
        except SetupUploadError as error:
            raise HTTPException(error.status, {'code':error.code, 'message':str(error)}) from None
        except sdk.LungInstallError as error:
            raise HTTPException(400, {'code':error.error_code, 'message':str(error)}) from None
        except (ValueError, OSError):
            raise HTTPException(400, {'code':'PACKAGE_INVALID', 'message':'Escolha o bundle de pesos completo preparado para levar.'}) from None
        return remember_source(description,purpose)

    @app.post('/api/plugins/lung-rt/local/inspect')
    async def inspect_route(request:Request):
        local(request, True)
        purpose = request.query_params.get('operation','weights')
        if purpose == 'code':
            raise HTTPException(400,{'code':'SUITE_CODE_UPDATE_REQUIRED','message':'O código dos plugins é atualizado pelo instalador principal da Local Suite.'})
        if purpose != 'weights':
            raise HTTPException(400,'Operação de instalação inválida.')
        payload = await body(request)
        folder = payload.get('folder')
        if set(payload) != {'folder'} or not isinstance(folder, str) or len(folder) > 4096 or not Path(folder).is_absolute():
            raise HTTPException(400, {'code':'EXPECTED_SETUP_PATH', 'message':'Selecione a pasta extraída ou o bundle do LUNG RT.'})
        try:
            description = await run_in_threadpool(sdk.inspect_local_source, folder)
            if 'operation' not in request.query_params and description.get('offline'):
                purpose='weights'
            if purpose=='weights' and not description.get('offline'):
                raise ValueError('Escolha o bundle de pesos completo preparado para levar.')
        except sdk.LungInstallError as error:
            raise HTTPException(400, {'code':error.error_code, 'message':str(error)}) from None
        except (ValueError, OSError):
            raise HTTPException(400, {'code':'PACKAGE_INVALID', 'message':'Escolha o bundle de pesos completo preparado para levar.'}) from None
        return remember_source(description,purpose)

    @app.post('/api/plugins/lung-rt/install')
    async def install_route(request:Request):
        local(request,True)
        payload=await body(request)
        purpose=payload.get('operation','weights')
        if purpose == 'code':
            raise HTTPException(400,{'code':'SUITE_CODE_UPDATE_REQUIRED','message':'O código dos plugins é atualizado pelo instalador principal da Local Suite.'})
        if purpose != 'weights':
            raise HTTPException(400,'Operação de instalação inválida.')
        source_id=payload.get('source_id')
        if (source_id is not None and (not isinstance(source_id,str) or not 1 <= len(source_id) <= 96)) or not isinstance(payload.get('consent',{}),dict) or type(payload.get('reports',False)) is not bool:
            raise HTTPException(400,'Pedido inválido.')
        import radai_queue_state as queue
        import radai_atualizar
        import radai_plugin_setup
        with entry['lock']:
            if not entry['load_complete'].is_set():
                raise HTTPException(409,'Aguarde a conferência do código do LUNG RT.')
            if entry['preparing']:
                raise HTTPException(409,'A instalação já foi iniciada.')
            queue_state = install_queue_status()
            if queue_state['active'] or queue.fechando_ao_fim() or radai_atualizar.etapa() in radai_atualizar.EM_ANDAMENTO:
                raise HTTPException(409,'Encerre os processamentos e o rastreio antes de instalar.')
            if queue_state['pending'] and payload.get('confirm_pending') is not True:
                raise HTTPException(409, 'Há itens aguardando na fila. Confirme antes de instalar.')
            shutdown=getattr(app.state,'radai_reabertura',{})
            if not callable(shutdown.get('encerrar')):
                raise HTTPException(409,'Reabra a suíte pelo atalho para instalar o plugin.')
            if not _accepted(root):
                policy=_policy()
                consent=payload.get('consent') or {}
                if consent.get('accepted') is not True or consent.get('digest')!=policy['digest'] or consent.get('version')!=policy['version']:
                    raise HTTPException(400,'Leia e aceite os termos do LUNG RT.')
                sdk._atomic(sdk._inside(root,'Plugins/LUNG RT/config/consent.json'),{
                    'schema':'lung-rt/consent-receipt/1','accepted':True,'version':policy['version'],
                    'digest':policy['digest'],'accepted_at':time.time()})
            entry['preparing']=True
            if not queue.reservar_manutencao_ociosa():
                entry['preparing']=False
                raise HTTPException(409,'Encerre os processamentos e o rastreio antes de instalar.')
        handed_off=False
        try:
            folder = None
            verified = None
            if payload.get('source_id'):
                source=entry['sources'].get(payload['source_id'])
                if not source or time.monotonic()-source['time']>900:
                    raise ValueError('Confira novamente o pacote local.')
                verified = source['description']
                if source.get('operation') != 'weights':
                    raise ValueError('Confira o pacote na opção correta de código ou pesos.')
                folder = verified['path']
            payload=dict(payload,reports=True,resources_only=True)
            plan=await run_in_threadpool(sdk.prepare_external_plan,
                dict(payload,installed_version=entry['installation'].get('active_version')),source_folder=folder)
            if verified and verified.get('inventory_sha256') and any(
                    plan.get(key) != verified.get(key) for key in ('version', 'inventory_sha256', 'offline')):
                raise sdk.LungInstallError('PACKAGE_CHANGED', 'O pacote mudou desde a conferência. Selecione-o novamente.')
            port=int((cfg.get('arranque') or {}).get('PORT') or cfg.get('port') or 8777)
            installer=radai_plugin_setup.ExternalInstaller(root,port,shutdown['encerrar'],plugin_id='lung-rt')
            result=await run_in_threadpool(installer.launch,plan)
            entry['external_installer']=installer
            handed_off=True
            return result
        except (sdk.LungInstallError, radai_plugin_setup.SetupError) as error:
            raise HTTPException(400, {'code':error.error_code, 'message':str(error)}) from None
        except ValueError as error:
            raise HTTPException(400,str(error)) from None
        except OSError:
            raise HTTPException(400, {'code':'INSTALL_IO_ERROR', 'message':'Não foi possível ler ou gravar os arquivos do instalador.'}) from None
        finally:
            if not handed_off:
                entry['preparing']=False
                queue.pedir_fechar_ao_fim(False)

    xray_path = '/lung/laudo/rx'

    def landing(request:Request):
        local(request)
        if not entry['load_complete'].is_set():
            import radai_modules, radai_menu, radai_ui
            page = radai_ui.com_portao(radai_menu.aplicar(radai_modules.pagina_completa('lung'),'lung'))
            return HTMLResponse(page,headers={'Cache-Control':'no-store','Refresh':'1'})
        import radai_breadcrumb
        import radai_plugin_setup_ui
        active = 'lung_laudo_rx' if request.url.path == xray_path else 'lung'
        page = radai_plugin_setup_ui.landing('lung', active, radai_breadcrumb.rotulo(active), scripts())
        return HTMLResponse(page, headers={'Cache-Control':'no-store'})

    def preparar():
        import logging
        import radai_plugin_bootstrap
        inicio = time.monotonic()
        try:
            try:
                radai_plugin_bootstrap.ensure_base(root, 'lung-rt')
            except Exception:
                logging.getLogger(__name__).exception('LUNG RT: preparo do código integrado indisponível')
            finally:
                logging.getLogger(__name__).info('LUNG RT: preparo do código integrado em %.3f s',time.monotonic()-inicio)
            if entry['closed']:
                return
            install = radai_plugins.discover_plugin(root,'lung-rt',host_info=info)
            if install['state'] == 'ready' and not entry['closed']:
                receipt = radai_plugins.mount_plugin(plugin_app,install,host_services(root,cfg))
                if entry['closed']:
                    close_service(receipt)
                    return
                app.state.lung_plugin_mount = receipt
                app.state.lung_plugin = receipt.get('service')
                entry['receipt'] = receipt
                entry['active_routes'] = {route.path for route in plugin_app.routes
                                          if getattr(route,'path',None) in fallback_paths and
                                          'GET' in (getattr(route,'methods',None) or ())}
                app.openapi_schema = None
            entry['installation'] = install
        except Exception:
            logging.getLogger(__name__).exception('LUNG RT: falha na montagem')
            entry['installation'] = dict(entry['installation'],state='failed',reason='Não foi possível conectar o LUNG RT. Repare a instalação.')
        finally:
            entry['load_complete'].set()
        if not entry['closed']:
            refresh()

    class PluginRoutes(Mount):
        # The adapter installs its own middleware. Publish its fully prepared ASGI
        # application as a unit, after verifying all of the code.
        def matches(self, scope):
            if (not entry['load_complete'].is_set() or not entry.get('receipt')
                    or scope['type'] != 'http' or not scope['path'].startswith(
                        ('/api/lung-plugin/','/lung-assets/','/lung/rastreio','/lung/laudo'))
                    or not any(route.matches(scope)[0] != Match.NONE for route in plugin_app.routes)):
                return Match.NONE, {}
            return super().matches(scope)

    def close_service(receipt):
        stop = getattr((receipt or {}).get('service'),'close',None)
        if callable(stop):
            stop()

    async def close():
        entry['closed'] = True
        await run_in_threadpool(worker.join, .5)
        await run_in_threadpool(close_service,entry.get('receipt'))

    plugin_app = FastAPI(openapi_url=None,docs_url=None,redoc_url=None)
    fallback_paths = ('/lung/rastreio','/lung/laudo',xray_path)
    app.router.routes.append(PluginRoutes('',app=plugin_app))
    for path in fallback_paths:
        app.add_api_route(path,landing,methods=['GET'],include_in_schema=False)
    worker = threading.Thread(target=preparar,name='lung-verify-mount',daemon=True)
    app.router.add_event_handler('shutdown',close)
    worker.start()
    return entry


def controls():
    import radai_plugin_setup_ui
    return radai_plugin_setup_ui.controls(plugin='lung')


def minipage_script():
    return r'''<script>(function () {
  'use strict';
  const cards = Array.from(document.querySelectorAll('[data-lung-capability]'));
  if (!cards.length) return;
  async function carregar(){
    const response=await fetch('/api/plugins/lung-rt/startup',{cache:'no-store'});
    if(response.ok && !(await response.json()).finished){setTimeout(()=>carregar().catch(()=>{}),700);return;}
    return fetch('/api/lung-plugin/status', {cache: 'no-store'})
    .then(response => response.ok ? response.json() : null)
    .then(status => {
      for (const card of cards) {
        if (status?.capabilities?.[card.dataset.lungCapability]?.resources_ready !== true) continue;
        const link = document.createElement('a');
        for (const attribute of card.attributes) {
          if (attribute.name !== 'aria-disabled') link.setAttribute(attribute.name, attribute.value);
        }
        link.classList.remove('obra');
        link.href = card.dataset.lungRoute;
        card.querySelector('.lung-resource-settings')?.remove();
        while (card.firstChild) link.append(card.firstChild);
        const arrow = document.querySelector('.md-grade a.md-fer .md-abrir')?.cloneNode(true);
        if (arrow) link.querySelector('.md-pe')?.append(arrow);
        card.replaceWith(link);
      }
    });
  }
  carregar().catch(()=>{});
})();</script>'''


def scripts():
    return r'''<script>(function () {
  'use strict';
  const e = id => document.getElementById(id);
  if (!e('lung-plugin-setup')) return;
  const t = text => window.radaiFrase ? window.radaiFrase(text) : text;
  let state = null, source = null, busy = false, checking = false, handedOff = false;
  const say = text => {e('lp-status').textContent=t(text);};
  function enable() {
    e('lp-install').disabled = busy || checking || handedOff || !state?.policy || (setup.local() && !source);
    e('lp-refresh').disabled = busy || checking || handedOff;
    setup.sync();
  }
  async function api(path, body) {
    const response = await fetch('/api/plugins/lung-rt' + path, {
      method: body ? 'POST' : 'GET', cache:'no-store',
      headers:body ? {'Content-Type':'application/json','X-Lung-Plugin-Token':state?.token || ''} : {},
      body:body ? JSON.stringify(body) : undefined
    });
    return window.RadaiPluginSetup.checked(response);
  }
  const setup = window.RadaiPluginSetup.bind(e('lung-plugin-setup'), {
    tokenHeader:'X-Lung-Plugin-Token', status:() => api(''),
    reset(){source=null;enable();}, lock(value){checking=value;enable();},
    accept(id){source=id;}, isLocked:() => busy || handedOff
  });
  async function load() {
    state=await api('');handedOff=state.preparing;
    setup.versions(state);setup.result(state.last_result);
    const labels={ready:'Pesos prontos',partial:'Pesos incompletos',missing:'Pesos não instalados',checking:'Conferindo os pesos…'};
    say(handedOff ? 'A instalação já foi iniciada.' : labels[state.weights?.state] || 'Conferindo os pesos…');
    enable();
    return state;
  }
  async function action(run) {
    if(busy || checking || handedOff) return;
    busy=true;enable();setup.clearFailure();
    try{await run();}catch(error){setup.failure(error);}finally{busy=false;enable();}
  }
  e('lp-refresh').addEventListener('click',() => action(async () => {
    await setup.checkWeights(load);
  }));
  e('lp-install').addEventListener('click',() => action(async () => {
    if(setup.local() && !source) return;
    state=await api('');setup.versions(state);
    if(state.queue?.active) throw {detail:'Encerre os processamentos e o rastreio antes de instalar.'};
    const pending = Boolean(state.queue?.pending);
    if(pending && !await new Promise(resolve => window.uiConfirmar({
      titulo:t('Instalar ou atualizar os pesos'), corpo:t('Há itens aguardando na fila. Confirme antes de instalar.'),
      aoSim:() => resolve(true), aoNao:() => resolve(false)}))) return;
    if(!await window.RadaiPluginSetup.confirmInstallation(state,'LUNG RT')) return;
    await api('/install',{
      source_id:setup.local() ? source : undefined,operation:setup.operation(),confirm_pending:pending,
      consent:{accepted:true,version:state.policy.version,digest:state.policy.digest}
    });
    handedOff=true;say('Instalação externa iniciada. Acompanhe o PowerShell.');
  }));
  const start=() => load().catch(error => {setup.failure(error);enable();});
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();</script>'''



def config_page(page):
    if 'id="ps_lung"' in page:
        return page
    import radai_ui
    import radai_plugin_setup_ui
    card=''' <a class="cfg-card" href="#ps_lung" data-alvo="ps_lung"><span class="cab"><span class="ic">'''+radai_ui.icone('pulmoes')+'''</span><span class="n">L</span></span><h3 data-radai-frase>Plugin LUNG RT</h3><p data-radai-frase>Instalar, atualizar, configurar rastreio e laudos locais.</p><span class="st" data-radai-frase>Instalação e atualização</span></a>'''
    section='''<section class="ps-cx fechado" id="ps_lung" hidden><h2 class="ps-cab" tabindex="0" role="button"><span class="ps-num">L</span><span data-radai-frase>Plugin LUNG RT</span>'''+radai_plugin_setup_ui.help_html()+'''<span class="ps-seta">&#9662;</span></h2><div class="ps-corpo">'''+controls()+'</div></section>'
    return radai_plugin_setup_ui.assets(page).replace(' <a class="cfg-card" href="#ps_limpar"',card+' <a class="cfg-card" href="#ps_limpar"',1).replace('<section class="ps-cx fechado" id="ps_limpar" hidden>',section+'<section class="ps-cx fechado" id="ps_limpar" hidden>',1).replace('</body>',scripts()+'</body>',1)
