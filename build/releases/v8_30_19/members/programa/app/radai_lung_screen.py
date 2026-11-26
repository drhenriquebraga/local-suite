import secrets
import threading
import time

import radai_lung as L

_TRAVA = threading.RLock()
_SELECAO = {}
_ESTADO = {"ativo": False, "mensagem": "", "exportavel": False}
_FIM = threading.Event()
_LEITURA_RASTREIO = None
_ENTREGA = None


def _estado(**valores):
    with _TRAVA:
        _ESTADO.update(valores)
        return dict(_ESTADO)


def _cine_com_referencias(cine, series):
    """Each displayed phase retains its own source, never the SBRT/ITV target."""
    import radai_thumbnail
    if len(cine) != len(series):
        raise ValueError('As fases do CINE não correspondem às séries processadas.')
    return [dict(frame, contour_reference=radai_thumbnail.bilhete(
        serie.get('pasta') or serie.get('zip') or '', serie['uid']))
        for frame, serie in zip(cine, series)]


def _trabalho(tipo, selecao, cfg):
    import radai_queue_state as fila
    global _ENTREGA, _LEITURA_RASTREIO
    ultimo_passo = None
    def registrar(texto):
        nonlocal ultimo_passo
        if ultimo_passo != texto and callable(cfg.get("log")):
            cfg["log"]("[LUNG RT] " + texto)
            ultimo_passo = texto

    try:
        def avancar(texto):
            _estado(mensagem=texto)
            registrar(texto)

        registrar({"uma": "Contorno de nódulo aguardando na fila.", "4d": "4D CT aguardando na fila.",
                   "exportar": "Exportação 4D aguardando na fila.", "rastreio": "Iniciando o rastreio."}[tipo])
        if tipo == "rastreio":
            from radai_lung_plugin import LeiturasDoRastreio
            leituras = LeiturasDoRastreio(L)
            with _TRAVA:
                _LEITURA_RASTREIO = leituras
                fila.ligar_ganchos(pausa_rastreio_local=leituras.pausa)
                leituras.estado("watching")
            vistos, tentados = {}, set()
            while not _FIM.is_set():
                atuais = leituras.varrer(selecao["pasta"], cfg)
                estaveis = {}
                for s in atuais:
                    if _FIM.is_set():
                        break
                    k = s["uid"]
                    try:
                        _, _, estado = leituras._inspecionar(s)
                    except (ValueError, OSError):
                        continue
                    estaveis[k] = estado
                    if vistos.get(k) != estado or (k, estado) in tentados:
                        continue
                    leituras.estado("waiting")
                    if not fila.esperar_a_vez(L.DONO, parar=_FIM.is_set):
                        break
                    try:
                        avancar("Rastreio em andamento · só nódulos pulmonares.")
                        tem = L.rodar_nodulos(s, cfg, esperado=estado)
                        atual = _estado()
                        _estado(feitas=atual["feitas"] + 1,
                                achados=atual["achados"] + int(tem))
                        tentados.add((k, estado))
                    except Exception as e:
                        _estado(erro=_erro(e), falhas=_estado()["falhas"] + 1)
                        tentados.add((k, estado))
                    finally:
                        fila.soltar_a_vez(L.DONO)
                vistos = estaveis
                if not _FIM.is_set():
                    avancar("Vigiando a pasta por novas séries de TC.")
                _FIM.wait(20)
            avancar("Rastreio encerrado.")
            return

        if not fila.esperar_a_vez(L.DONO, parar=_FIM.is_set):
            avancar("Execução encerrada.")
            return
        try:
            if tipo == "uma":
                avancar("Processando a série de tórax.")
                serie = selecao["series"][0]
                if selecao["protocolo"] == "nodulos":
                    tem = L.rodar_nodulos(serie, cfg)
                    mensagem = ("RTSTRUCT de nódulos gravado ao lado da série." if tem
                                else "A tarefa terminou sem produzir contornos de nódulos.")
                else:
                    assinatura = L._inspecionar(serie)[2]
                    tem = L.processar_com_protocolo(serie, cfg, selecao["protocolo"],
                                                    selecao["esforco"], assinatura)
                    mensagem = ("STUDY gravado com anatomia e nódulos." if tem else
                                "STUDY gravado com anatomia. Nenhum nódulo gerou contorno.")
                _estado(feitas=1, achados=int(tem), mensagem=mensagem)
                registrar(mensagem)
            elif tipo == "4d":
                r = L.rodar_4d(selecao["series"], selecao["sbrt"], selecao["alvo"],
                              cfg, _FIM, avancar, selecao.get("adicionais", ()),
                              protocolo=selecao["protocolo"], esforco=selecao["esforco"])
                if not r:
                    avancar("Execução encerrada entre fases.")
                    return
                r['cine'] = _cine_com_referencias(r['cine'], selecao['series'])
                with _TRAVA:
                    aberta = selecao["ficha"] == _SELECAO.get("ficha")
                    _ENTREGA = r if aberta else None
                    _estado(ficha_export=selecao["ficha"] if aberta else "",
                            referencia=selecao["referencia"], cine_disponivel=aberta,
                            exportavel=aberta and bool(r["masks"]))
                vazias = ", ".join(str(i) for i in r["lacunas"])
                _estado(feitas=len(selecao["series"]),
                        achados=len(selecao["series"]) - len(r["lacunas"]),
                        falhas=r.get("estados_fases", []).count("falha"),
                        mensagem=(("STUDY gravado. Fases sem contorno: " + vazias + ".") if vazias
                                  else "STUDY e contornos das fases concluídos.") +
                                  (" Há fases com falha; confira as lacunas." if "falha" in r.get("estados_fases", []) else ""))
                registrar(_estado()["mensagem"])
            elif tipo == "exportar":
                avancar("Gravando RTSTRUCT 4D.")
                L.exportar(selecao["serie"], selecao["assinatura"], selecao["masks"], cfg,
                           curvas=selecao.get('curvas'))
                with _TRAVA:
                    _ENTREGA = None
                _estado(exportavel=False, mensagem="RTSTRUCT 4D gravado na série escolhida.")
                registrar("RTSTRUCT 4D gravado na série escolhida.")
        finally:
            fila.soltar_a_vez(L.DONO)
    except Exception as e:
        L.registrar_erro(e, cfg)
        registrar("O processamento falhou.")
        _estado(erro=_erro(e), mensagem="Não foi possível concluir.")
    finally:
        if tipo == "rastreio":
            with _TRAVA:
                fila.ligar_ganchos(pausa_rastreio_local=None)
                _LEITURA_RASTREIO = None
        _estado(ativo=False, parando=False)


def _erro(e):
    import traceback
    from pathlib import Path
    import radai_batch
    frames = traceback.extract_tb(e.__traceback__)
    origem = Path(frames[-1].filename).name if frames else ''
    if isinstance(e, (ValueError, RuntimeError)) and origem in (
            'radai_lung.py', 'radai_lung_screen.py', 'radai_lung_4d.py'):
        return radai_batch._sem_caminho_nem_uid(str(e))[:240]
    return "Falha durante o processamento (%s)." % type(e).__name__


def _origem_ok(request):
    return request.headers.get("origin") == "%s://%s" % (request.url.scheme, request.url.netloc)


def _seletor_de_series(quatro):
    import radai_tabela_acervo
    import radai_ui

    cartao = radai_ui.cartao_de_serie(
        "lung_cartao", "lung_escolha", "Escolher a série", chave_modulo="lung")
    pasta = '<button id="nova_serie" class="ui-bt" type="button" data-radai-frase>Adicionar novas séries</button><input id="pasta" type="hidden">'
    ajuda = radai_ui.ajuda(
        "Escolha uma TC no Acervo Local ou aponte a pasta do estudo.",
        ("No Acervo Local, a série selecionada identifica o estudo. "
         "Se as fases estiverem em pastas diferentes, aponte a pasta que reúne as fases."
         if quatro else "Ao apontar uma pasta, escolha a série axial de TC na lista.")
        + " Se o acervo apontar para uma pasta protegida, selecione uma cópia em uma pasta de trabalho.",
        direita=True,
    )
    abas = radai_ui.abas_de_serie("lung_origem", [
        ("acervo", "Acervo Local", radai_tabela_acervo.html("lung_acervo")),
        ("pasta", "Aponte uma pasta", pasta),
    ], padrao="acervo")
    popup = radai_ui.popup_de_serie(
        "lung_escolha",
        '<div class="lung-ajuda">%s</div>%s'
        '<p id="lung_escolha_msg" role="status" aria-live="polite"></p>' % (ajuda, abas),
        sozinho=True,
    )
    return cartao, popup + radai_ui.formulario_carregar_imagens("lung_add", dias="0")


def montar(app, opcoes=None):
    from fastapi import Request
    from fastapi.responses import HTMLResponse, JSONResponse
    from starlette.concurrency import run_in_threadpool

    cfg = dict(opcoes or {})

    def tela(tipo):
        import radai_menu
        import radai_ui
        import radai_review
        quatro = tipo == "4d"
        titulo = "4D CT &amp; ITV" if quatro else "Contorno de Nódulo Pulmonar"
        cartao, popup = _seletor_de_series(quatro)
        html = PAGINA.replace("@TITULO@", titulo).replace("@MODO@", tipo)
        from radai_fast_ui import page as pagina_com_esforco
        from radai_velocidade_tc import esforco_atual
        html = html.replace("@ESFORCO@", esforco_atual())
        html = html.replace("@AVISO@", radai_review.FRASE_DA_FRONTEIRA)
        html = html.replace("@CARTAO@", cartao).replace("@POPUP@", popup)
        html = html.replace("@CABECA@", radai_ui.cabeca_de_funcao(
            radai_ui.icone("pulmoes"), "4D CT & ITV" if quatro else "Contorno de Nódulo Pulmonar",
            "Escolha as séries e confira os resultados antes de exportar.", chave_modulo="lung"))
        return radai_menu.aplicar(
            radai_ui.com_portao(pagina_com_esforco(html, caso=True)), "lung_4d" if quatro else "lung_nodulos")

    @app.get("/lung/nodulos", response_class=HTMLResponse)
    def _tela_nodulos():
        return tela("nodulos")

    @app.get("/lung/4d", response_class=HTMLResponse)
    def _tela_4d():
        return tela("4d")

    @app.get("/api/lung/estado")
    def _ver():
        return _estado()

    @app.get("/api/lung/cine")
    def _cine(ficha: str):
        with _TRAVA:
            if _ENTREGA is None or ficha != _ESTADO.get("ficha_export"):
                return JSONResponse({"erro": "Abra o resultado desta seleção."}, status_code=404)
            return JSONResponse({"cine": _ENTREGA['cine'], "curvas": _ENTREGA['curvas']},
                                headers={"Cache-Control": "no-store"})

    @app.post("/api/lung/acao")
    async def _acao(request: Request):
        if not _origem_ok(request):
            return JSONResponse({"erro": "Pedido fora da tela local."}, status_code=403)
        try:
            d = await request.json()
            if not isinstance(d, dict):
                raise ValueError("Pedido inválido.")
            if d.get("acao") == "carregar":
                import radai_consulta_isolada
                import radai_thumbnail
                dados = {"pedido": d, "cfg": {"min_cortes": cfg.get("min_cortes", 20)}}
                if "bilhete" in d:
                    pasta, uid = radai_thumbnail.resolver(d["bilhete"])
                    if not pasta or not uid:
                        raise ValueError("A seleção do Acervo Local não está mais disponível.")
                    dados["referencia"] = (pasta, uid)
                series = await radai_consulta_isolada.ler(request, "lung_series", dados)
                if await request.is_disconnected():
                    return JSONResponse({}, status_code=499)
                return _acao_local(d, cfg, series)
            return await run_in_threadpool(_acao_local, d, cfg)
        except ConnectionAbortedError:
            return JSONResponse({}, status_code=499)
        except Exception as e:
            L.registrar_erro(e, cfg)
            return JSONResponse({"erro": _erro(e)}, status_code=400)


def _series_da_escolha(d, cfg):
    if isinstance(d.get('series'), list):
        series = L.resolver_series(d['series'], cfg)
        return (series[0]['pasta'] if series else ''), series
    bilhete = d.get("bilhete")
    if bilhete is None:
        pasta = L.pasta_valida(d.get("pasta"), cfg)
        return pasta, L.varrer(pasta, cfg)

    import radai_tabela_acervo

    if not isinstance(bilhete, str) or not bilhete or len(bilhete) > 200:
        raise ValueError("A seleção do Acervo Local não está mais disponível.")
    pasta, uid = radai_tabela_acervo.resolver(bilhete)
    if not pasta or not uid:
        raise ValueError("A seleção do Acervo Local não está mais disponível.")
    try:
        pasta = L.pasta_valida(pasta, cfg)
    except ValueError as e:
        raise ValueError(
            f"{e} Em Aponte uma pasta, selecione uma cópia da TC em uma pasta de trabalho."
        ) from e
    series = L.varrer(pasta, cfg)
    escolhida = next((s for s in series if s["uid"] == uid), None)
    if escolhida is None:
        raise ValueError(
            "A TC axial não foi encontrada na pasta registrada no Acervo Local. "
            "Em Aponte uma pasta, selecione a pasta que contém a TC."
        )
    if d.get("modo") != "4d":
        return pasta, [escolhida]

    grupo = escolhida.get("pid"), escolhida.get("estudo")
    if not all(grupo):
        raise ValueError("A série do Acervo Local não identifica um estudo 4D.")
    fases = [s for s in series if (s.get("pid"), s.get("estudo")) == grupo]
    if len(fases) < 2:
        raise ValueError("Aponte a pasta que reúne as fases deste estudo 4D.")
    return pasta, fases


def _acao_local(d, cfg, selecao_lida=None):
    global _ENTREGA
    acao = d.get("acao")
    if acao == "associar":
        import radai_lung_4d
        with _TRAVA:
            if (_ESTADO['ativo'] or _ENTREGA is None
                    or d.get('ficha') != _ESTADO.get('ficha_export')):
                raise ValueError("Abra o resultado desta seleção antes de associar lesões.")
            associacoes = d.get('associacoes')
            if not isinstance(associacoes, dict) or len(associacoes) > 512:
                raise ValueError("Associações inválidas.")
            masks, curvas = radai_lung_4d.associar(_ENTREGA['fases'], _ENTREGA['grade'],
                                                 associacoes=associacoes,
                                                 medidas_nativas=_ENTREGA.get('medidas_nativas'))
            _ENTREGA.update(masks=masks, curvas=curvas)
        return {'ok': True}
    if acao == "fechar":
        with _TRAVA:
            if d.get("ficha") and d["ficha"] == _SELECAO.get("ficha"):
                _SELECAO.clear()
                _ENTREGA = None
                _estado(exportavel=False, cine_disponivel=False, ficha_export="")
        return {"ok": True}
    if acao == "parar":
        if _estado()["ativo"]:
            _FIM.set()
            with _TRAVA:
                if _LEITURA_RASTREIO:
                    _LEITURA_RASTREIO.estado("cancelling")
            _estado(parando=True, mensagem="Encerrando depois da série em curso.")
        return _estado()
    if acao == "carregar":
        pasta, series = selecao_lida if selecao_lida is not None else _series_da_escolha(d, cfg)
        if not series:
            raise ValueError("Nenhuma série axial de TC encontrada.")
        ids, grupos = {}, {}
        with _TRAVA:
            if _ESTADO["ativo"]:
                raise ValueError("Aguarde a execução em andamento.")
            _ENTREGA = None
            _estado(exportavel=False, ficha_export="", referencia="", cine_disponivel=False)
            _SELECAO.clear()
            ficha = secrets.token_urlsafe(18)
            for s in series:
                id_ = secrets.token_urlsafe(9)
                ids[id_] = s
                grupo = grupos.setdefault((s.get("pid"), s.get("estudo")), len(grupos) + 1)
                s["_lung_id"] = id_
                s["_lung_grupo"] = grupo
            _SELECAO.update(ficha=ficha, pasta=pasta, ids=ids, ate=time.monotonic() + 1800)
        return {"ficha": ficha, "series": [
            {"id": s["_lung_id"], "grupo": s["_lung_grupo"], "numero": s.get("numero"),
             "cortes": s["cortes"], "descricao": s.get("desc"), "fase": s.get("fase_respiratoria")} for s in series]}
    if acao not in ("uma", "rastreio", "4d", "exportar") or d.get("confirmado") is not True:
        raise ValueError("Confirme o pedido na tela para prosseguir.")
    with _TRAVA:
        if _ESTADO["ativo"]:
            raise ValueError("O LUNG RT já está processando nesta estação.")
        if acao == "exportar":
            if _ENTREGA is None or not d.get("ficha") or d["ficha"] != _ESTADO.get("ficha_export"):
                raise ValueError("Abra a seleção que gerou este resultado antes de exportar.")
            selecao = _ENTREGA
        elif acao == "rastreio":
            selecao = {"pasta": L.pasta_valida(d.get("pasta"), cfg)}
        else:
            if not _SELECAO or d.get("ficha") != _SELECAO["ficha"] or time.monotonic() > _SELECAO["ate"]:
                raise ValueError("Carregue as séries novamente.")
            ids = d.get("ids")
            catalogo = _SELECAO["ids"]
            if (not isinstance(ids, list) or not all(isinstance(k, str) and k in catalogo for k in ids)
                    or len(set(ids)) != len(ids)):
                raise ValueError("Seleção de séries inválida.")
            protocolo, esforco = L.opcoes_study(d.get("protocolo"), d.get("esforco"), acao == "4d")
            series = [catalogo[k] for k in ids]
            if acao == "uma":
                if len(series) != 1:
                    raise ValueError("Selecione exatamente uma série.")
                selecao = {"series": series}
            else:
                sbrt, alvo = d.get("sbrt"), d.get("alvo")
                if (not 2 <= len(series) <= L.MAX_FASES or sbrt not in catalogo or alvo not in catalogo
                        or len({s["_lung_grupo"] for s in series}) != 1):
                    raise ValueError("Selecione as fases de um estudo, a fase SBRT e a referência.")
                selecao = {"series": sorted(series, key=lambda s: s.get("fase_respiratoria") or 0),
                           "adicionais": [catalogo[sbrt], catalogo[alvo]], "sbrt": catalogo[sbrt]["uid"],
                           "alvo": catalogo[alvo]["uid"], "ficha": d["ficha"],
                           "referencia": catalogo[alvo].get("desc") or
                           ("Série " + str(catalogo[alvo].get("numero") or ""))}
            selecao.update(protocolo=protocolo, esforco=esforco)
        if acao != "exportar":
            _ENTREGA = None
        _FIM.clear()
        _estado(ativo=True, parando=False, modo=acao, feitas=0, achados=0, falhas=0,
                exportavel=acao == "exportar", erro="", mensagem="Aguardando a fila local.")
        threading.Thread(target=_trabalho, args=(acao, selecao, cfg),
                         daemon=True, name="radai-lung").start()
        return _estado()


PAGINA = """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>@TITULO@ · LUNG RT</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:var(--bg-0,#060d1a);color:var(--text,#e6edf7);font:15px/1.55 Inter,system-ui,sans-serif}
main.lung-page{width:min(1000px,calc(100% - 32px));margin:48px auto;padding-bottom:48px}
a{color:var(--accent,#82b9ff)} h1{font-size:clamp(26px,5vw,44px);line-height:1.12;margin:12px 0}
.lung-page>fieldset,.lung-page>section{border:1px solid var(--line,#344256);padding:20px;margin:16px 0;border-radius:12px}
legend,label,strong{font-weight:600} p{margin:8px 0}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:10px 0}
.lung-ajuda{display:flex;justify-content:flex-end}
input[type=text]{flex:1;min-width:200px}
input,select,button{font:inherit;padding:8px 12px;color:inherit;background:var(--panel,#101c2d);border:1px solid var(--line,#46566d);border-radius:8px}
button{cursor:pointer;font-weight:600}
button.primary{background:var(--accent,#82b9ff);color:var(--bg-0,#060d1a)}
button:disabled{opacity:.45;cursor:default}
table{width:100%;border-collapse:collapse} td,th{text-align:left;padding:7px 5px;border-bottom:1px solid var(--line,#344256)}
.note{border-left:3px solid var(--accent,#82b9ff);padding-left:12px}
#erro{color:var(--warn,#efbb56)} [hidden]{display:none!important}
</style></head><body><main class="lung-page">
@CABECA@
<p id="intro"></p>
@CARTAO@
<section id="selecao" hidden>
<div class="row" id="grupoRow" hidden><label for="grupo" data-radai-frase>Estudo</label><select id="grupo"></select></div>
<table><thead><tr><th data-radai-frase>Incluir</th><th data-radai-frase>Série</th><th data-radai-frase>Cortes</th><th id="sbrtTitle" data-radai-frase>Série para o STUDY</th></tr></thead><tbody id="series"></tbody></table>
<div class="row" id="alvoRow" hidden><label for="alvo" data-radai-frase>Série de referência para exportação</label><select id="alvo"></select></div>
</section>
<section aria-label="Execução">
<div class="row"><label for="protocolo" data-radai-frase>Protocolo</label>
<select id="protocolo"><option value="nodulos" data-radai-frase>Somente nódulos</option>
<option value="torax_mama" data-radai-frase>Tórax / Mama</option><option value="sbrt_pulmao" data-radai-frase>SBRT de tórax</option></select></div>
<div id="esforco" hidden></div>
<p class="note" data-radai-frase>@AVISO@</p>
<p data-radai-frase>Os resultados exigem revisão médica. A ausência de contorno não exclui nódulos.</p>
<div class="row"><button id="rodar" class="ui-bt pri" type="button" disabled></button>
<button id="vigiar" type="button" data-radai-frase>Iniciar Rastreio</button>
<button id="parar" type="button" data-radai-frase>Encerrar depois da série</button>
<button id="exportar" class="ui-bt pri" type="button" data-radai-frase hidden>Exportar GTVs e ITV sugerido</button></div>
<p id="referencia" hidden></p><p id="status" role="status" aria-live="polite"></p><p id="erro" role="alert"></p>
</section>
<section id="cine" hidden>
<h2 data-radai-frase>CINE · pulmões e nódulos</h2>
<div class="row"><button id="cinePlay" type="button" data-radai-frase>Reproduzir / pausar</button>
<label><span data-radai-frase>Fase</span> <input id="cineFase" type="range" min="0" value="0"></label>
<span id="cineNumero"></span><label><span data-radai-frase>Rotação 3D</span> <input id="cineAngulo" type="range" min="0" max="360" value="20"></label></div>
<div class="row"><img id="cineAxial" alt="Axial" width="200"><img id="cineCoronal" alt="Coronal" width="200"><img id="cineSagital" alt="Sagital" width="200"><canvas id="cine3d" width="260" height="260" aria-label="Pulmões e nódulos 3D"></canvas></div>
<label for="cineLesao" data-radai-frase>Lesão</label><select id="cineLesao"></select>
<p data-radai-frase>Deslocamento LR/AP/SI e vetor desde a fase 0, em mm. Volume por fase, em mm³. Lacunas permanecem sem medida.</p>
<canvas id="cineCurva" width="700" height="230" style="max-width:100%"></canvas>
<canvas id="cineVolume" width="700" height="170" style="max-width:100%"></canvas>
<p id="cineLacunas"></p>
<p data-radai-frase>Associações geométricas sugeridas: confira cada lesão. Use a mesma identidade nas fases correspondentes; uma lacuna não impede exportar o ITV.</p>
<div id="cineAssociacoes"></div><button id="cineSalvar" type="button" data-radai-frase>Aplicar associações</button>
</section></main>@POPUP@
<script>
'use strict';
const get=id=>document.getElementById(id), modo='@MODO@', quatro=modo==='4d';
let esforco='@ESFORCO@';
let dados=[], ficha='', ativo=false, carregando=false, msgLocal='';
texto(get('intro'),quatro
 ? 'Selecione as fases e a série para o STUDY. Cada outra fase positiva recebe os seus próprios contornos.'
 : 'Selecione uma TC. Inclua um protocolo de tórax para gravar os nódulos e a anatomia no mesmo STUDY.');
texto(get('rodar'),quatro?'Processar fases selecionadas':'Processar a série selecionada');
if(quatro){get('protocolo').querySelector('[value=nodulos]').remove();get('protocolo').value='sbrt_pulmao';}
function ajustarEsforco(){
 const cont=get('esforco');cont.hidden=get('protocolo').value==='nodulos';
 if(!cont.hidden && !cont.firstChild && window.radaiMiniEsforco) cont.innerHTML=window.radaiMiniEsforco(0,esforco);
}
get('protocolo').addEventListener('change',ajustarEsforco);
document.addEventListener('DOMContentLoaded',ajustarEsforco);
window.addEventListener('radai-esforco-caso',ev=>{esforco=ev.detail.valor;});
get('vigiar').hidden=true;
get('sbrtTitle').hidden=!quatro;
function texto(e,key,values){
 e.setAttribute('data-radai-frase','');
 const value=window.uiMolde?uiMolde(key,values||[]):key;
 if(window.uiTexto)uiTexto(e,value);else e.textContent=value;
 if(window.radaiRetraduzir)window.radaiRetraduzir();
}
function molde(key,values){return window.uiMolde?uiMolde(key,values):key;}
function erro(m){msgLocal=m||'';texto(get('erro'),msgLocal);}
async function pedir(d,signal){
 const r=await fetch('/api/lung/acao',{method:'POST',signal,headers:{'Content-Type':'application/json'},body:JSON.stringify(d)});
 const j=await r.json(); if(!r.ok || j.erro) throw Error(j.erro||'O programa não aceitou o pedido.');return j;
}
function el(tag,t){const e=document.createElement(tag);if(t!=null)e.textContent=t;return e;}
function campos(){const t=get('series');return {ids:[...t.querySelectorAll('[name=incluir]:checked')].map(x=>x.value),
 sbrt:t.querySelector('[name=sbrt]:checked')?.value,alvo:get('alvo').value,protocolo:get('protocolo').value,esforco};}
function habilitar(){
 const s=campos();
 get('protocolo').disabled=ativo||carregando;get('esforco').inert=ativo||carregando;
 get('rodar').disabled=ativo||carregando||!ficha||(quatro?(s.ids.length<2||!s.sbrt||!s.alvo):s.ids.length!==1);
 get('lung_cartao').disabled=ativo||carregando;
}
function render(){
 const t=get('series'), alvo=get('alvo');t.replaceChildren();alvo.replaceChildren();
 const lista=quatro?dados.filter(s=>String(s.grupo)===get('grupo').value):dados;
 lista.forEach((s,i)=>{
  const linha=el('tr'), incluir=el('input');incluir.type=quatro?'checkbox':'radio';incluir.name='incluir';
  incluir.checked=quatro?(s.fase!==null):i===0;incluir.disabled=quatro&&s.fase===null;incluir.value=s.id;
  const nome=s.descricao||molde('Série %s',[s.numero||i+1]);incluir.setAttribute('aria-label',molde('Incluir %s',[nome]));
  const c=el('td');c.append(incluir);linha.append(c,el('td',nome),el('td',s.cortes));
  if(quatro){
   const sb=el('input');sb.type='radio';sb.name='sbrt';sb.value=s.id;
   sb.setAttribute('aria-label',molde('Série para o STUDY')+' · '+nome);
   sb.onchange=habilitar;
   const cs=el('td');cs.append(sb);linha.append(cs);
   const op=el('option',nome);op.value=s.id;alvo.append(op);
  }
  incluir.onchange=habilitar;t.append(linha);
 });
 get('alvoRow').hidden=!quatro;habilitar();
}
get('alvo').onchange=habilitar;get('grupo').onchange=render;
function mensagemEscolha(texto){
 const msg=get('lung_escolha_msg');
 if(window.uiTexto) window.uiTexto(msg,texto); else msg.textContent=texto;
}
function limparSelecao(){
 ficha='';dados=[];get('series').replaceChildren();get('selecao').hidden=true;
 get('exportar').hidden=true;get('referencia').hidden=true;
 if(window.uiCartaoRotulo) window.uiCartaoRotulo('lung_cartao','nenhuma série aberta',true);
 habilitar();
}
let leituraSerie=null;
function cancelarLeituraSerie(){if(leituraSerie) leituraSerie.abort();}
window.addEventListener('pagehide',()=>{
 cancelarLeituraSerie();
 if(ficha){
  const body=JSON.stringify({acao:'fechar',ficha});
  if(navigator.sendBeacon)navigator.sendBeacon('/api/lung/acao',new Blob([body],{type:'application/json'}));
  else fetch('/api/lung/acao',{method:'POST',keepalive:true,headers:{'Content-Type':'application/json'},body}).catch(()=>{});
 }
});
async function carregar(origem){
 if(ativo||carregando) return;
 const ctl=leituraSerie=new AbortController();
 carregando=true;limparSelecao();erro('');
 if(origem.bilhete) get('pasta').value='';
 mensagemEscolha('Procurando séries de TC…');
 try{
  const r=await pedir({acao:'carregar',modo,...origem},ctl.signal);
  if(ctl.signal.aborted)return;
  dados=r.series;ficha=r.ficha;
  const grupos=[...new Set(dados.map(s=>s.grupo))];get('grupo').replaceChildren();
  grupos.forEach(g=>{const op=el('option');texto(op,'Estudo %s',[g]);op.value=g;get('grupo').append(op);});
  get('grupoRow').hidden=!quatro||grupos.length<2;get('selecao').hidden=false;render();
  if(window.uiCartaoRotulo){
   const descricao=!quatro&&dados.length===1&&dados[0].descricao;
   const resumo=quatro?'Fases do estudo carregadas':(dados.length===1?'Série carregada':'Séries da pasta carregadas');
   window.uiCartaoRotulo('lung_cartao',descricao||resumo,!descricao);
  }
  mensagemEscolha('');
  if(window.uiPopupSerie) window.uiPopupSerie('lung_escolha').fechar();
 }catch(e){
  if(!ctl.signal.aborted){mensagemEscolha(e.message);erro(e.message);}
 }finally{
  leituraSerie=null;carregando=false;habilitar();
 }
}
let seletorComum;
document.addEventListener('DOMContentLoaded',()=>{
 window.uiPopupSerie('lung_escolha',{aoFechar:cancelarLeituraSerie});
 seletorComum=window.uiCarregarImagens('lung_add',{uso:'lote',chave:'lung_add',aoFechar:cancelarLeituraSerie,
  aoFim:(linhas,d,contexto)=>{if(d.final&&!d.parado){get('pasta').value=contexto.pasta;
   carregar({series:linhas}).then(()=>seletorComum.fechar());}},aoErro:m=>erro(m)});
 get('nova_serie').onclick=()=>{window.uiPopupSerie('lung_escolha').fechar();seletorComum.abrir(get('lung_cartao'));};
});
document.addEventListener('DOMContentLoaded',()=>{
 if(window.uiTabelaAcervo){
  window.uiTabelaAcervo('lung_acervo',{
   filtro:linha=>!linha.modalidade||String(linha.modalidade).toUpperCase()==='CT',
   aoAbrir:linha=>{
    if(linha&&linha.bilhete) carregar({bilhete:linha.bilhete});
   }
  });
 }
});
async function executar(d, frase){
 erro('');if(!window.confirm(window.radaiTraduzir?window.radaiTraduzir(frase):frase))return;
 try{await pedir({...d,confirmado:true});await atualizar();}catch(e){erro(e.message);}
}
get('rodar').onclick=()=>executar({acao:quatro?'4d':'uma',ficha,...campos()},
 quatro?'Processar as fases e gravar o STUDY na série marcada?':(get('protocolo').value==='nodulos'?'Rodar somente a tarefa de nódulos nesta série?':'Processar a série com o protocolo selecionado?'));
get('vigiar').onclick=()=>{location.href='/lung/rastreio';};
get('parar').onclick=async()=>{try{await pedir({acao:'parar'});await atualizar();}catch(e){erro(e.message);}};
get('exportar').onclick=()=>executar({acao:'exportar',ficha},'Gravar as sugestões de GTV e a união ITV na série selecionada? Revise todas as fases antes de usar o resultado.');
let estadoCtl=null,tempoEstado=null;
async function atualizar(){
 if(document.hidden||estadoCtl)return;
 const ctl=estadoCtl=new AbortController();
 clearTimeout(tempoEstado);
 try{const d=await (await fetch('/api/lung/estado',{cache:'no-store',signal:ctl.signal})).json();if(ctl.signal.aborted)return;ativo=!!d.ativo;
  texto(get('status'),d.mensagem||'');
  if(!msgLocal)texto(get('erro'),d.erro||'');
  get('vigiar').disabled=ativo;get('parar').hidden=!ativo;get('parar').disabled=!!d.parando;
  const mostrar=quatro&&d.exportavel&&ficha===d.ficha_export;
  get('referencia').hidden=!mostrar;
  texto(get('referencia'),mostrar?molde('Referência da exportação: %s',[d.referencia]):'');
  get('exportar').hidden=!mostrar;get('exportar').disabled=ativo;habilitar();
  if(quatro&&d.cine_disponivel&&d.ficha_export===ficha&&cineToken!==ficha){cineToken=ficha;carregarCine().catch(e=>erro(e.message));}
 }catch(_){}finally{
  if(estadoCtl===ctl)estadoCtl=null;
  if(!ctl.signal.aborted&&!document.hidden&&ativo)tempoEstado=setTimeout(atualizar,1500);
 }
}
function pausarLung(){clearTimeout(tempoEstado);if(estadoCtl)estadoCtl.abort();estadoCtl=null;clearInterval(tempoCine);cineRodando=false;}
document.addEventListener('visibilitychange',()=>{if(document.hidden)pausarLung();else atualizar();});
window.addEventListener('pagehide',pausarLung);
window.addEventListener('pageshow',e=>{if(e.persisted){limparSelecao();atualizar();}});
let tempoCine=null;
let cineDados=null,cineRodando=false,cineToken='';
function pintarGrafico(canvas,rows,campos,cores){
 const c=canvas.getContext('2d'),w=canvas.width,h=canvas.height;c.clearRect(0,0,w,h);
 const valores=rows.flatMap(r=>r?campos.map(f=>f(r)).filter(v=>v!==null):[]);
 let min=Math.min(0,...valores),max=Math.max(1,...valores); if(max===min)max=min+1;
 c.fillStyle='#ccd6e2';c.font='12px system-ui';c.fillText(max.toFixed(1),0,18);c.fillText(min.toFixed(1),0,h-12);
 campos.forEach((campo,j)=>{c.strokeStyle=cores[j];c.beginPath();let aberto=false;
 rows.forEach((r,i)=>{const value=r?campo(r):null;if(value===null){aberto=false;return;}
 const x=45+i*(w-65)/Math.max(1,rows.length-1),y=15+(max-value)*(h-45)/(max-min);
 if(!aberto)c.moveTo(x,y);else c.lineTo(x,y);aberto=true;});c.stroke();});
 rows.forEach((r,i)=>c.fillText(String(i),43+i*(w-65)/Math.max(1,rows.length-1),h-3));
}
function pintarCine(){
 if(!cineDados)return;const phase=Number(get('cineFase').value),f=cineDados.cine[phase];if(!f)return;
 get('cine').dataset.contourReference=f.contour_reference||'';
 ['axial','coronal','sagital'].forEach(p=>get('cine'+p[0].toUpperCase()+p.slice(1)).src=f.mpr[p]);
 get('cineNumero').textContent=String(phase);
 const canvas=get('cine3d'),c=canvas.getContext('2d'),angle=Number(get('cineAngulo').value)*Math.PI/180;
 c.clearRect(0,0,260,260);const all=Object.values(f.pontos_lps).flat();
 if(all.length){const bounds=[0,1,2].map(a=>[Math.min(...all.map(p=>p[a])),Math.max(...all.map(p=>p[a]))]);
 const mid=bounds.map(b=>(b[0]+b[1])/2),scale=220/Math.max(...bounds.map(b=>b[1]-b[0]),1);
 Object.entries(f.pontos_lps).forEach(([name,pts])=>{c.fillStyle=name==='nodulos'?'#ffb414':'#46b4ff';c.globalAlpha=name==='nodulos'?1:.38;
 pts.forEach(p=>{let x=p[0]-mid[0],y=p[1]-mid[1],z=p[2]-mid[2];c.fillRect(130+(x*Math.cos(angle)-y*Math.sin(angle))*scale,130-z*scale,name==='nodulos'?3:1.5,name==='nodulos'?3:1.5);});});c.globalAlpha=1;}
 const lesion=cineDados.curvas.find(x=>x.id===get('cineLesao').value);if(!lesion)return;
 const delta=(r,i)=>r.deslocamento_lps_mm?r.deslocamento_lps_mm[i]:null;
 pintarGrafico(get('cineCurva'),lesion.fases,[r=>delta(r,0),r=>delta(r,1),r=>delta(r,2),r=>r.vetor_mm],['#ef7777','#7ee787','#79b8ff','#ffcf66']);
 pintarGrafico(get('cineVolume'),lesion.fases,[r=>r.volume_mm3],['#ffcf66']);
 get('cineLacunas').replaceChildren();const legenda=el('span'),lacunas=el('span');texto(legenda,'LR (vermelho) · AP (verde) · SI (azul) · vetor (amarelo).');texto(lacunas,'Fases contribuintes: %s · Lacunas: %s',[lesion.contribuintes.join(', '),lesion.lacunas.join(', ')]);get('cineLacunas').append(legenda,el('br'),lacunas);
}
async function carregarCine(){
 const r=await fetch('/api/lung/cine?ficha='+encodeURIComponent(ficha),{cache:'no-store'});if(!r.ok)return;
 cineDados=await r.json();get('cine').hidden=false;get('cineFase').max=cineDados.cine.length-1;
 get('cineLesao').replaceChildren();get('cineAssociacoes').replaceChildren();
 cineDados.curvas.forEach(l=>{const op=el('option',l.id);get('cineLesao').append(op);
 l.fases.forEach(r=>{if(!r)return;const lab=el('label'),caption=el('span'),input=el('input');texto(caption,'F%s / componente %s',[r.fase,r.componente]);lab.append(caption);
 input.value=l.id;input.size=5;input.maxLength=4;input.dataset.associacao=r.fase+':'+r.componente;lab.append(input);get('cineAssociacoes').append(lab);});});pintarCine();
}
get('cinePlay').onclick=()=>{
 clearInterval(tempoCine);cineRodando=!cineRodando;
 if(cineRodando&&cineDados)tempoCine=setInterval(()=>{get('cineFase').value=(Number(get('cineFase').value)+1)%cineDados.cine.length;pintarCine();},400);
};
get('cineFase').oninput=pintarCine;get('cineAngulo').oninput=pintarCine;get('cineLesao').onchange=pintarCine;
get('cineSalvar').onclick=async()=>{try{const associacoes={};document.querySelectorAll('[data-associacao]').forEach(e=>associacoes[e.dataset.associacao]=e.value);
 await pedir({acao:'associar',ficha,associacoes});await carregarCine();}catch(e){erro(e.message);}};
atualizar();
</script></body></html>"""
