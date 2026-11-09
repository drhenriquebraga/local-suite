import html
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


def montar(app,cfg=None):
    global _ENTRY
    from fastapi import Request,HTTPException
    from fastapi.responses import HTMLResponse,JSONResponse
    from starlette.concurrency import run_in_threadpool
    import radai_plugins
    import radai_lung_install as sdk
    import radai_install_profile
    cfg = dict(cfg or {})
    if getattr(app.state,'lung_plugin_entry',None):
        return app.state.lung_plugin_entry
    root = Path(cfg.get('suite_root') or radai_install_profile.raiz()).resolve()
    info = radai_plugins._host_info(root,cfg)
    install = radai_plugins.discover_plugin(root,'lung-rt',host_info=info)
    entry = {'installation':install,'token':secrets.token_urlsafe(32),'sources':{},
             'release':{'state':'checking'},'lock':threading.RLock(),'preparing':False,'closed':False}
    _ENTRY = entry
    app.state.lung_plugin_entry = entry
    if install['state'] == 'ready':
        try:
            entry['receipt'] = radai_plugins.mount_plugin(app,install,host_services(root,cfg))
        except Exception:
            import logging
            logging.getLogger(__name__).exception('LUNG RT: falha na montagem')
            entry['installation'] = dict(install,state='failed',reason='Não foi possível conectar o LUNG RT. Repare a instalação.')

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

    threading.Thread(target=refresh,name='lung-release-check',daemon=True).start()

    @app.get('/api/plugins/lung-rt')
    def status(request:Request):
        local(request)
        try:
            policy=_policy()
        except ValueError:
            policy=None
        return JSONResponse({'suite_fingerprint':sdk.suite_identity(root),'state':entry['installation']['state'],'version':entry['installation'].get('active_version'),
                'reason':entry['installation'].get('reason',''),'token':entry['token'],
                'release':entry['release'],'preparing':entry['preparing'],
                'policy':policy,'accepted':_accepted(root)},headers={'Cache-Control':'no-store'})

    @app.post('/api/plugins/lung-rt/refresh')
    async def refresh_route(request:Request):
        local(request,True)
        return await run_in_threadpool(refresh)

    @app.post('/api/plugins/lung-rt/local/inspect')
    async def inspect_route(request:Request):
        local(request,True)
        payload=await body(request)
        try:
            description=await run_in_threadpool(sdk.inspect_local_source,payload.get('folder',''))
            source_id=secrets.token_urlsafe(24)
            entry['sources']={k:v for k,v in entry['sources'].items() if time.monotonic()-v['time']<900}
            if len(entry['sources'])>15:
                entry['sources'].clear()
            entry['sources'][source_id]={'time':time.monotonic(),'description':description}
            return {'source_id':source_id,'version':description['version'],'offline':description.get('offline',False)}
        except (ValueError,OSError):
            raise HTTPException(400,'Não foi possível validar este pacote. Atualize a suíte ou selecione a pasta completa do instalador LUNG RT.')

    @app.post('/api/plugins/lung-rt/install')
    async def install_route(request:Request):
        local(request,True)
        payload=await body(request)
        source_id=payload.get('source_id')
        if (source_id is not None and (not isinstance(source_id,str) or not 1 <= len(source_id) <= 96)) or not isinstance(payload.get('consent',{}),dict) or type(payload.get('reports',False)) is not bool:
            raise HTTPException(400,'Pedido inválido.')
        import radai_queue_state as queue
        import radai_atualizar
        import radai_plugin_setup
        with entry['lock']:
            if entry['preparing']:
                raise HTTPException(409,'A instalação já foi iniciada.')
            if queue.quem_tem_a_vez().get('dono') or queue.fechando_ao_fim() or radai_atualizar.etapa() in radai_atualizar.EM_ANDAMENTO:
                raise HTTPException(409,'Encerre os processamentos e o rastreio antes de instalar.')
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
            queue.pedir_fechar_ao_fim(True)
        handed_off=False
        try:
            folder=None
            if payload.get('source_id'):
                source=entry['sources'].get(payload['source_id'])
                if not source or time.monotonic()-source['time']>900:
                    raise ValueError('Confira novamente o pacote local.')
                folder=source['description']['path']
            plan=await run_in_threadpool(sdk.prepare_external_plan,
                dict(payload,installed_version=entry['installation'].get('active_version')),source_folder=folder)
            port=int((cfg.get('arranque') or {}).get('PORT') or cfg.get('port') or 8777)
            installer=radai_plugin_setup.ExternalInstaller(root,port,shutdown['encerrar'],plugin_id='lung-rt')
            result=await run_in_threadpool(installer.launch,plan)
            entry['external_installer']=installer
            handed_off=True
            return result
        except (OSError,ValueError) as error:
            raise HTTPException(400,str(error)) from None
        finally:
            if not handed_off:
                entry['preparing']=False
                queue.pedir_fechar_ao_fim(False)

    xray_path = '/lung/laudo/rx'

    def landing(request:Request):
        local(request)
        import radai_breadcrumb
        import radai_menu
        import radai_ui
        xray = request.url.path == xray_path
        active = 'lung_laudo_rx' if xray else 'lung'
        title = radai_breadcrumb.rotulo(active)
        action_title = 'Instalar ou atualizar LUNG RT'
        header = radai_ui.cabeca_de_funcao('imagem' if xray else 'pulmoes',title,action_title,chave_modulo='lung')
        page = ('<!doctype html><html><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                '<title>'+html.escape(title)+'</title></head><body><main>'
                +header+radai_ui.passo(1,action_title,controls())+'</main>'+scripts()+'</body></html>')
        return HTMLResponse(radai_ui.com_portao(radai_menu.aplicar(page,active)),headers={'Cache-Control':'no-store'})

    if not (entry.get('receipt') or {}).get('mounted'):
        app.add_api_route('/lung/rastreio',landing,methods=['GET'])
        app.add_api_route('/lung/laudo',landing,methods=['GET'])
    if not any(getattr(route,'path',None)==xray_path and 'GET' in (getattr(route,'methods',None) or ())
               for route in app.routes):
        app.add_api_route(xray_path,landing,methods=['GET'])
    return entry


def controls():
    return '''<section id="lung-plugin-setup"><p id="lp-status" role="status" data-radai-frase>Verificando a instalação do LUNG RT…</p>
<div class="linha"><button type="button" class="sec" id="lp-refresh" data-radai-frase>Verificar atualizações</button>
<a href="/lung/rastreio#config" data-radai-frase>Configurar rastreio e laudos</a></div>
<details><summary data-radai-frase>Usar instalador ou pacote offline de uma pasta</summary>
<p data-radai-frase>Sem acesso aos servidores? Em outra máquina, abra o START HERE do LUNG RT e prepare o pacote offline. Traga a pasta completa e confira abaixo.</p>
<div class="linha"><input id="lp-folder" aria-label="Pasta do instalador LUNG RT" autocomplete="off"><button id="lp-browse" class="sec" type="button" data-radai-frase>Procurar…</button><button id="lp-inspect" class="sec" type="button" data-radai-frase>Conferir pacote local</button></div><p id="lp-source" role="status"></p></details>
<label><input type="checkbox" id="lp-reports"><span data-radai-frase>Preparar também o piloto local de laudos (aproximadamente 3 GB)</span></label>
<div id="lp-policy"></div><label id="lp-accept-label"><input type="checkbox" id="lp-accept"><span data-radai-frase>Li e aceito os termos do LUNG RT e a participação na fase de testes.</span></label>
<button type="button" id="lp-install" disabled data-radai-frase>Instalar ou atualizar LUNG RT</button>
<p data-radai-frase>A suíte fecha durante o preparo, mostra o progresso no PowerShell e reabre ao terminar. O Python existente é reutilizado.</p></section>'''


def scripts():
    return r'''<script>(function(){
const e=id=>document.getElementById(id),t=s=>window.radaiFrase?radaiFrase(s):s,m=(s,v)=>window.uiMolde?uiMolde(s,[v]):t(s).replace('%s',v);let state=null,source=null,busy=false;
function say(s){e('lp-status').textContent=t(s)}
function enable(){e('lp-install').disabled=busy||!state||!state.policy||(!state.accepted&&!e('lp-accept').checked)}
async function api(path,body){const r=await fetch('/api/plugins/lung-rt'+path,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json','X-Lung-Plugin-Token':state?.token||''}:{},body:body?JSON.stringify(body):undefined});const d=await r.json();if(!r.ok)throw Error(d.detail||'Não foi possível concluir.');return d}
async function load(){state=await api('');say(state.preparing?'A instalação já foi iniciada.':state.state==='ready'?'LUNG RT instalado.':state.reason||'O plugin LUNG RT ainda não está instalado.');const box=e('lp-policy');box.replaceChildren();if(state.policy){for(const clause of state.policy.clauses){const p=document.createElement('p');p.textContent=t(typeof clause==='string'?clause:clause.text);box.append(p)}}box.hidden=state.accepted;e('lp-accept-label').hidden=state.accepted;enable()}
async function action(fn){if(busy)return;busy=true;enable();try{await fn()}catch(err){say(err.message)}finally{busy=false;enable()}}
e('lp-accept').onchange=enable;e('lp-folder').oninput=()=>{source=null;e('lp-source').textContent=''};
e('lp-refresh').onclick=()=>action(async()=>{say('Consultando a versão disponível.');const d=await api('/refresh',{});say(d.state==='available'?m('Nova versão disponível: %s',d.version):d.state==='current'?'LUNG RT está atualizado.':d.reason)});
e('lp-browse').onclick=()=>{if(window.uiExplorador)uiExplorador({titulo:t('Pasta do instalador LUNG RT'),origem:e('lp-browse'),inicial:e('lp-folder').value,aoUsar:p=>{e('lp-folder').value=p;source=null}});else e('lp-folder').focus()};
e('lp-inspect').onclick=()=>action(async()=>{source=await api('/local/inspect',{folder:e('lp-folder').value});e('lp-source').textContent=m('Pacote conferido: %s',source.version);say('Pacote local pronto para instalar.')});
e('lp-install').onclick=()=>action(async()=>{if(!confirm(t('A suíte será fechada para instalar o plugin e reaberta ao terminar. Continuar?')))return;const d=await api('/install',{source_id:source?.source_id,reports:e('lp-reports').checked,consent:{accepted:e('lp-accept').checked,version:state.policy.version,digest:state.policy.digest}});say('Instalação externa iniciada. Acompanhe o PowerShell.');e('lp-install').disabled=true});
load().catch(err=>say(err.message));
})();</script>'''


def config_page(page):
    if 'id="ps_lung"' in page:
        return page
    card=''' <a class="cfg-card" href="#ps_lung" data-alvo="ps_lung"><span class="cab"><span class="n">L</span></span><h3 data-radai-frase>Plugin LUNG RT</h3><p data-radai-frase>Instalar, atualizar, configurar rastreio e laudos locais.</p><span class="st" data-radai-frase>Instalação e atualização</span></a>'''
    section='''<section class="ps-cx fechado" id="ps_lung" hidden><h2 class="ps-cab" tabindex="0" role="button"><span class="ps-num">L</span><span data-radai-frase>Plugin LUNG RT</span><span class="ps-seta">&#9662;</span></h2><div class="ps-corpo">'''+controls()+'</div></section>'
    return page.replace(' <a class="cfg-card" href="#ps_limpar"',card+' <a class="cfg-card" href="#ps_limpar"',1).replace('<section class="ps-cx fechado" id="ps_limpar" hidden>',section+'<section class="ps-cx fechado" id="ps_limpar" hidden>',1).replace('</body>',scripts()+'</body>',1)
