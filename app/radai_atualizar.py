# -*- coding: utf-8 -*-
import io
import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
import zipfile

CREATE_NO_WINDOW = 0x08000000
CREATE_NEW_CONSOLE = 0x00000010
CREATE_BREAKAWAY_FROM_JOB = 0x01000000

PASTA_DE_TRABALHO = u"radai_atualizar"
TETO_DA_DECISAO_S = 240
INTERVALO_DA_ESPERA_S = 2.0
ATRASO_DO_FECHAR_S = 1.5
TETO_DA_REABERTURA_MS = 600000

LIVRE = u"livre"
OCUPADO = u"ocupado"
ESPERANDO = u"esperando"
BAIXANDO = u"baixando"
PREPARANDO = u"preparando"
BUNDLE = u"bundle"
FECHANDO = u"fechando"
PREPARADOR = u"preparador"
ERRO = u"erro"
EM_ANDAMENTO = (ESPERANDO, BAIXANDO, PREPARANDO, FECHANDO)

SEGURA_VIGIA = u"A série do vigia está rodando."
SEGURA_LOTE = u"O lote do «Rodar agora» está rodando."
SEGURA_TURNO = u"O turno da noite está aberto."
SEGURA_TURNO_NA_FILA = u"O turno da noite está na fila."

M_SEM_NOVA = u"Não há versão nova para instalar."
M_NAO_INSTALADO = (u"Este programa não roda de uma instalação: a atualização "
                   u"automática vale só para o programa instalado.")
M_DOWNLOAD = (u"O download do instalador falhou ou não confere com a release; "
              u"nada foi executado.")
M_OUTRO = u"O instalador baixado não é desta instalação; nada foi executado."
M_DECISAO = u"Não consegui decidir se a atualização pode ser só do código."
M_ABRIR = u"Não consegui abrir o atualizador."
M_PASTA = u"Não consegui preparar a pasta da atualização."

_TRAVA = threading.RLock()
_E = {"etapa": LIVRE, "motivo_chave": u"", "detalhe": u"", "progresso": 0,
      "tamanho_gib": None, "disco_gib": None, "tempo_min": None,
      "versao_nova": u""}
_CTX = {"ler_vigia": None, "log": None, "porta": None, "segurei": False,
        "raiz": u"", "pasta": u"", "cancelar": False, "bps": 0.0}


def _log(m):
    f = _CTX.get("log")
    if f:
        try:
            f(u"[atualizar] " + m)
        except Exception:
            pass


def _mudar(**kw):
    with _TRAVA:
        _E.update(kw)


def etapa():
    with _TRAVA:
        return _E["etapa"]


def o_que_segura(status):
    s = status if isinstance(status, dict) else {}
    if s.get("overnight"):
        return SEGURA_TURNO
    oc = s.get("ocupado")
    if oc:
        quem = oc.get("quem") if isinstance(oc, dict) else u""
        return SEGURA_LOTE if quem == u"lote" else SEGURA_VIGIA
    if s.get("current"):
        return SEGURA_VIGIA
    if s.get("turno_agendado"):
        return SEGURA_TURNO_NA_FILA
    return None


def _status():
    f = _CTX.get("ler_vigia")
    if not f:
        return {}
    try:
        return f() or {}
    except Exception:
        return {}


def _segurar_a_fila(sim):
    try:
        import radai_queue_state as Q
        Q.pedir_fechar_ao_fim(bool(sim))
        _CTX["segurei"] = bool(sim)
    except Exception:
        pass


def _soltar_se_segurei():
    if _CTX.get("segurei"):
        _segurar_a_fila(False)


def pasta_do_programa():
    try:
        import radai_version
        return radai_version.pasta_do_programa()
    except Exception:
        return u""


def e_instalacao(pasta):
    return bool(pasta) and all(os.path.isfile(os.path.join(pasta, *p)) for p in (
        ("python", "python.exe"), ("radai_lancador.py",), ("entrega.txt",)))


def _dentro(filho, pai):
    try:
        f = os.path.normcase(os.path.realpath(filho))
        p = os.path.normcase(os.path.realpath(pai)).rstrip("\\/") + os.sep
        return f.startswith(p)
    except Exception:
        return True


def pasta_de_trabalho(programa, base=None):
    base = (base or os.environ.get("RADAI_TEMP_DO_USUARIO")
            or tempfile.gettempdir())
    p = os.path.join(base, PASTA_DE_TRABALHO)
    # GUARDA: o instalador baixado nunca mora dentro da pasta do programa,
    # que o proprio atualizador sobrescreve.
    if programa and _dentro(p, programa):
        return u""
    return p


def extrair(arquivo, destino):
    os.makedirs(destino, exist_ok=True)
    base = os.path.normcase(os.path.realpath(destino)).rstrip("\\/") + os.sep
    n = 0
    with zipfile.ZipFile(arquivo) as z:
        for info in z.infolist():
            alvo = os.path.realpath(os.path.join(destino, info.filename))
            if not os.path.normcase(alvo).startswith(base):
                raise ValueError(u"o arquivo baixado grava fora da pasta da "
                                 u"extração: %s" % info.filename[:80])
            if info.is_dir():
                os.makedirs(alvo, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(alvo), exist_ok=True)
            with z.open(info) as o, io.open(alvo, "wb") as d:
                shutil.copyfileobj(o, d)
            n += 1
    return n


def raiz_do_pacote(pasta):
    if os.path.isfile(os.path.join(pasta, "packager", "UPDATE.ps1")):
        return pasta
    try:
        for nome in sorted(os.listdir(pasta)):
            c = os.path.join(pasta, nome)
            if os.path.isfile(os.path.join(c, "packager", "UPDATE.ps1")):
                return c
    except Exception:
        pass
    return u""


def campo_da_entrega(pasta, chave):
    try:
        for linha in io.open(os.path.join(pasta, "entrega.txt"),
                             encoding="utf-8-sig", errors="replace"):
            linha = linha.strip()
            if linha.upper().startswith(chave.upper() + "="):
                return linha.split("=", 1)[1].strip()
    except Exception:
        pass
    return u""


def mesma_versao(a, b):
    try:
        import radai_version as V
        return bool(a) and bool(b) and not V._maior(a, b) and not V._maior(b, a)
    except Exception:
        return False


def powershell():
    raiz = os.environ.get("SystemRoot") or u"C:\\Windows"
    c = os.path.join(raiz, "System32", "WindowsPowerShell", "v1.0",
                     "powershell.exe")
    return c if os.path.isfile(c) else u"powershell.exe"


def ambiente_do_atualizador(base=None):
    try:
        import radai_lancador
        return radai_lancador.ambiente_do_sucessor(base)
    except Exception:
        return dict(os.environ if base is None else base)


def decidir(raiz, programa, rodar=None):
    rodar = rodar or subprocess.run
    upd = os.path.join(raiz, "packager", "UPDATE.ps1")
    kw = {"creationflags": CREATE_NO_WINDOW} if os.name == "nt" else {}
    try:
        p = rodar([powershell(), "-NoProfile", "-NonInteractive",
                   "-ExecutionPolicy", "Bypass", "-File", upd,
                   "-Destino", programa, "-SoDecidir"],
                  capture_output=True, stdin=subprocess.DEVNULL,
                  timeout=TETO_DA_DECISAO_S, env=ambiente_do_atualizador(),
                  **kw)
    except Exception as e:
        return None, u"%s: %s" % (type(e).__name__, str(e)[:120])
    saida = ((p.stdout or b"") + (p.stderr or b"")).decode("cp1252", "replace")
    if p.returncode == 0 and u"DECISAO=codigo" in saida:
        return u"codigo", saida
    if p.returncode == 3 and u"DECISAO=pacote" in saida:
        return u"pacote", saida
    cauda = u" | ".join(l.strip() for l in saida.splitlines() if l.strip())[-300:]
    return None, u"codigo %s: %s" % (p.returncode, cauda)


def tamanho_do_pacote(raiz):
    try:
        with io.open(os.path.join(raiz, "packager", "catalogo.json"),
                     encoding="utf-8-sig") as f:
            p = (json.load(f) or {}).get("pacote") or {}
        return float(p.get("download_gib") or 0) or None, \
            float(p.get("disco_gib") or 0) or None
    except Exception:
        return None, None


def tempo_estimado_min(download_gib, bps):
    if not download_gib or not bps or bps <= 0:
        return None
    return int(round(download_gib * 1024 ** 3 / float(bps) / 60.0)) or 1


def lancar_atualizador(raiz, programa, pid, popen=None):
    popen = popen or subprocess.Popen
    upd = os.path.join(raiz, "packager", "UPDATE.ps1")
    cmd = [powershell(), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
           upd, "-Destino", programa, "-SemPerguntar", "-EsperarPid",
           str(int(pid)), "-Reabrir"]
    kw = dict(stdin=subprocess.DEVNULL, close_fds=True,
              cwd=os.path.dirname(upd), env=ambiente_do_atualizador())
    base = CREATE_NEW_CONSOLE if os.name == "nt" else 0
    try:
        return popen(cmd, creationflags=base | (
            CREATE_BREAKAWAY_FROM_JOB if os.name == "nt" else 0), **kw)
    except OSError:
        return popen(cmd, creationflags=base, **kw)


def lancar_preparador(raiz, programa, versao_aqui, popen=None):
    popen = popen or subprocess.Popen
    prep = os.path.join(raiz, "packager", "prepare.ps1")
    amb = ambiente_do_atualizador()
    amb["RADAI_ATUALIZAR_APP"] = programa
    amb["RADAI_ATUALIZAR_APP_DE"] = versao_aqui or u"0"
    cmd = [powershell(), "-NoProfile", "-ExecutionPolicy", "Bypass", "-STA",
           "-WindowStyle", "Hidden", "-File", prep]
    kw = dict(stdin=subprocess.DEVNULL, close_fds=True,
              cwd=os.path.dirname(prep), env=amb)
    base = CREATE_NEW_CONSOLE if os.name == "nt" else 0
    try:
        return popen(cmd, creationflags=base | (
            CREATE_BREAKAWAY_FROM_JOB if os.name == "nt" else 0), **kw)
    except OSError:
        return popen(cmd, creationflags=base, **kw)


def _minimizar_as_janelas():
    try:
        import radai_janela
        r = radai_janela.minimizar(None)
        if not r.get("ok"):
            _log(u"a janela do app nao foi achada para minimizar; o "
                 u"atualizador pode abrir por tras dela")
    except Exception:
        pass


def _encerrar_o_motor(porta, atraso_s=ATRASO_DO_FECHAR_S):
    def _fim():
        time.sleep(atraso_s)
        try:
            import radai_lancador
            radai_lancador.pedir_para_encerrar(int(porta))
        except Exception as e:
            _log(u"nao consegui pedir o encerramento (%s)" % type(e).__name__)
    threading.Thread(target=_fim, name="radai-atualizar-fecha",
                     daemon=False).start()


def _falhar(chave, detalhe=u""):
    _soltar_se_segurei()
    _mudar(etapa=ERRO, motivo_chave=chave, detalhe=detalhe or u"")
    _log(u"nao aconteceu: %s %s" % (chave, detalhe or u""))


def _fluxo(interromper):
    import radai_version as V
    programa = pasta_do_programa()
    if not e_instalacao(programa):
        return _falhar(M_NAO_INSTALADO)
    info = V.ultima_consulta()
    if info.get("estado") != u"nova":
        return _falhar(M_SEM_NOVA)
    versao = str(info.get("versao") or u"")
    inst = info.get("instalador") or {}
    if not inst.get("url"):
        info = V.consultar()
        inst = info.get("instalador") or {}
        versao = str(info.get("versao") or versao)
    _mudar(versao_nova=versao)
    pasta = pasta_de_trabalho(programa)
    if not pasta:
        return _falhar(M_PASTA)
    try:
        if os.path.isdir(pasta):
            shutil.rmtree(pasta)
        os.makedirs(pasta)
    except Exception as e:
        return _falhar(M_PASTA, u"%s: %s" % (type(e).__name__, str(e)[:120]))
    _CTX["pasta"] = pasta
    _log(u"baixando o instalador da v%s" % versao)

    def _prog(n, total):
        _mudar(progresso=int(100.0 * n / total) if total else 0)
    r = V.baixar_instalador(inst, os.path.join(pasta, u"baixado"),
                            progresso=_prog)
    if _CTX.get("cancelar"):
        _limpar_pasta()
        return None
    if not r.get("ok"):
        return _falhar(M_DOWNLOAD, r.get("motivo") or u"")
    _CTX["bps"] = (r["bytes"] / r["segundos"]) if r.get("segundos", 0) >= 0.3 \
        else 0.0
    _log(u"instalador conferido: tamanho e soma SHA-256 da release")
    _mudar(etapa=PREPARANDO, progresso=100)
    try:
        extrair(r["arquivo"], os.path.join(pasta, u"extraido"))
    except Exception as e:
        return _falhar(M_OUTRO, u"%s: %s" % (type(e).__name__, str(e)[:160]))
    raiz = raiz_do_pacote(os.path.join(pasta, u"extraido"))
    if not raiz:
        return _falhar(M_OUTRO, u"o arquivo baixado nao traz o "
                                u"packager\\UPDATE.ps1")
    projeto = campo_da_entrega(programa, u"PROJETO")
    if campo_da_entrega(raiz, u"PROJETO") != projeto or not mesma_versao(
            campo_da_entrega(raiz, u"VERSAO"), versao):
        return _falhar(M_OUTRO, u"entrega.txt: %s %s, e a instalacao e %s v%s"
                       % (campo_da_entrega(raiz, u"PROJETO"),
                          campo_da_entrega(raiz, u"VERSAO"), projeto, versao))
    _CTX["raiz"] = raiz
    decisao, saida = decidir(raiz, programa)
    if _CTX.get("cancelar"):
        _limpar_pasta()
        return None
    if decisao is None:
        return _falhar(M_DECISAO, saida)
    if decisao == u"pacote":
        dl, disco = tamanho_do_pacote(raiz)
        _mudar(etapa=BUNDLE, tamanho_gib=dl, disco_gib=disco,
               tempo_min=tempo_estimado_min(dl, _CTX.get("bps")))
        _soltar_se_segurei()
        _log(u"a v%s precisa de pacote novo: espera a segunda confirmacao"
             % versao)
        return None
    if not interromper:
        segura = o_que_segura(_status())
        if segura:
            _soltar_se_segurei()
            _mudar(etapa=OCUPADO, motivo_chave=segura)
            return None
    if _CTX.get("cancelar"):
        _limpar_pasta()
        return None
    try:
        p = lancar_atualizador(raiz, programa, os.getpid())
    except Exception as e:
        return _falhar(M_ABRIR, u"%s: %s" % (type(e).__name__, str(e)[:120]))
    try:
        import radai_pulso
        radai_pulso.poupar(p.pid)
    except Exception:
        pass
    _log(u"so o codigo muda: o atualizador abriu (PID %s), o app fecha e "
         u"reabre sozinho" % getattr(p, "pid", u"?"))
    _mudar(etapa=FECHANDO)
    _minimizar_as_janelas()
    porta = _CTX.get("porta")
    if porta:
        _encerrar_o_motor(porta)
    return None


def _rodar_fluxo(interromper):
    try:
        _fluxo(interromper)
    except Exception as e:
        _falhar(M_DECISAO, u"%s: %s" % (type(e).__name__, str(e)[:160]))


def _iniciar(interromper):
    _CTX["cancelar"] = False
    _mudar(etapa=BAIXANDO, motivo_chave=u"", detalhe=u"", progresso=0,
           tamanho_gib=None, disco_gib=None, tempo_min=None)
    _segurar_a_fila(True)
    threading.Thread(target=_rodar_fluxo, args=(bool(interromper),),
                     name="radai-atualizar", daemon=True).start()


def _esperar():
    while etapa() == ESPERANDO:
        if o_que_segura(_status()) is None:
            _log(u"o que segurava terminou: a atualizacao comeca")
            _iniciar(False)
            return
        time.sleep(INTERVALO_DA_ESPERA_S)


def _limpar_pasta():
    p = _CTX.get("pasta")
    if p and os.path.isdir(p):
        shutil.rmtree(p, ignore_errors=True)
    _CTX["pasta"] = u""
    _CTX["raiz"] = u""


def agir(acao, porta=None):
    if porta:
        _CTX["porta"] = int(porta)
    acao = str(acao or u"")
    with _TRAVA:
        atual = _E["etapa"]
        if acao in (u"comecar", u"esperar", u"interromper") and \
                atual in EM_ANDAMENTO:
            return estado_publico()
        if acao == u"comecar":
            try:
                import radai_version as V
                nova = V.ultima_consulta().get("estado") == u"nova"
            except Exception:
                nova = False
            if not nova:
                _mudar(etapa=ERRO, motivo_chave=M_SEM_NOVA, detalhe=u"")
                return estado_publico()
            if not e_instalacao(pasta_do_programa()):
                _mudar(etapa=ERRO, motivo_chave=M_NAO_INSTALADO, detalhe=u"")
                return estado_publico()
            segura = o_que_segura(_status())
            if segura:
                _mudar(etapa=OCUPADO, motivo_chave=segura, detalhe=u"")
                return estado_publico()
            _iniciar(False)
        elif acao == u"esperar":
            if o_que_segura(_status()) is None:
                _iniciar(False)
            else:
                _mudar(etapa=ESPERANDO, detalhe=u"")
                _segurar_a_fila(True)
                _log(u"espera a fila terminar para atualizar")
                threading.Thread(target=_esperar, name="radai-atualizar-espera",
                                 daemon=True).start()
        elif acao == u"interromper":
            _log(u"a pessoa confirmou interromper o que rodava para atualizar")
            _iniciar(True)
        elif acao == u"bundle" and atual == BUNDLE:
            try:
                import radai_version as V
                aqui = V._entrega_txt()
                lancar_preparador(_CTX.get("raiz"), pasta_do_programa(), aqui)
            except Exception as e:
                _falhar(M_ABRIR, u"%s: %s" % (type(e).__name__, str(e)[:120]))
                return estado_publico()
            _log(u"o instalador da versao nova abriu para o pacote completo")
            _mudar(etapa=PREPARADOR)
            _minimizar_as_janelas()
        elif acao == u"cancelar" and atual != FECHANDO:
            _CTX["cancelar"] = True
            _soltar_se_segurei()
            if atual != PREPARADOR:
                _limpar_pasta()
            _mudar(etapa=LIVRE, motivo_chave=u"", detalhe=u"")
    return estado_publico()


def estado_publico():
    with _TRAVA:
        d = dict(_E)
    d["pid"] = os.getpid()
    try:
        import radai_version as V
        t = V.para_a_tela()
        d.update({"aqui": t.get("aqui"), "publicada": t.get("publicada"),
                  "link": t.get("link"), "nova": t.get("nova")})
    except Exception:
        pass
    return d


def versao_js():
    try:
        import radai_version as V
        d = V.para_a_tela()
        d["consultando"] = bool(d.get("estado") == u"nunca"
                                and V.url_em_vigor())
    except Exception:
        d = {"estado": u"erro", "nova": False, "consultando": False}
    corpo = json.dumps({"estado": d.get("estado"), "nova": bool(d.get("nova")),
                        "consultando": bool(d.get("consultando"))})
    return u"window.radaiVersao&&window.radaiVersao(%s);\n" % (
        corpo.replace(u"</", u"<\\/"))


def limpar_o_baixado(programa=None):
    # GUARDA: so o .zip baixado sai no arranque; a pasta extraida pode ser a
    # do preparador ou a do atualizador que ainda esta terminando.
    pasta = pasta_de_trabalho(programa if programa is not None
                              else pasta_do_programa())
    alvo = os.path.join(pasta, u"baixado") if pasta else u""
    if alvo and os.path.isdir(alvo):
        shutil.rmtree(alvo, ignore_errors=True)
        return True
    return False


def montar(app, ler_vigia=None, registrar=None):
    from fastapi import Request
    from starlette.responses import JSONResponse, Response
    _CTX["ler_vigia"] = ler_vigia
    _CTX["log"] = registrar
    try:
        limpar_o_baixado()
    except Exception:
        pass

    @app.get("/api/versao.js")
    def _versao_js():
        return Response(content=versao_js(),
                        media_type="application/javascript",
                        headers={"Cache-Control": "no-store"})

    @app.post("/api/atualizar")
    async def _agir(request: Request):
        # GUARDA: so a propria tela dispara a atualizacao; sem Origin igual
        # ao do painel o pedido e recusado, mesmo vindo desta maquina.
        origem = request.headers.get("origin") or u""
        alvo = u"%s://%s" % (request.url.scheme, request.url.netloc)
        if origem != alvo:
            return JSONResponse(status_code=403, content={
                "erro": u"a atualização só se dispara pela tela do programa"})
        try:
            corpo = await request.json()
        except Exception:
            corpo = {}
        corpo = corpo if isinstance(corpo, dict) else {}
        from starlette.concurrency import run_in_threadpool
        return await run_in_threadpool(agir, corpo.get("acao"),
                                       request.url.port)

    return app


MARCA = u"radai-atualizar-js"

CSS = u"""<style id="radai-atualizar-css">
.ra-modal .ui-modal-corpo{padding:18px 20px 20px}
.ra-cx{display:flex;flex-direction:column;gap:12px;min-width:0}
.ra-v{display:flex;align-items:center;gap:10px;margin:0;
 font:500 13px/1.2 var(--mono);color:var(--text-muted)}
.ra-v code{padding:3px 8px;border-radius:var(--r-sm);background:var(--panel-2);
 border:1px solid var(--line);color:var(--text);font:inherit}
.ra-v .ra-seta{color:var(--text-dim)}
.ra-v[hidden]{display:none}
.ra-st{margin:0;font:600 15px/1.4 var(--font-display);color:var(--text)}
.ra-st.vivo{background:linear-gradient(90deg,var(--text-muted) 0%,var(--text-muted) 38%,
 var(--text) 50%,var(--text-muted) 62%,var(--text-muted) 100%);background-size:250% 100%;
 -webkit-background-clip:text;background-clip:text;color:transparent;
 animation:raBrilho 2.4s linear infinite}
@keyframes raBrilho{from{background-position:130% 0}to{background-position:-30% 0}}
.ra-barra{position:relative;height:6px;border-radius:var(--r-pill);
 background:var(--panel-2);border:1px solid var(--line);overflow:hidden}
.ra-barra[hidden]{display:none}
.ra-barra i{position:absolute;inset:0 auto 0 0;width:0;border-radius:inherit;
 background:var(--accent);transition:width .3s cubic-bezier(.22,1,.36,1)}
.ra-txt{margin:0;font-size:13.5px;line-height:1.6;color:var(--text-muted);max-width:62ch}
.ra-txt:empty,.ra-det:empty{display:none}
.ra-det{margin:0;padding:8px 10px;border-radius:var(--r-md);background:var(--panel-2);
 border:1px solid var(--line);font:400 11.5px/1.5 var(--mono);color:var(--text-dim);
 overflow-wrap:anywhere}
.ra-bts{display:flex;flex-wrap:wrap;gap:8px;margin-top:6px}
.ra-bts:empty{display:none}
.ra-bts a.ui-bt{text-decoration:none}
@media (prefers-reduced-motion:reduce){
 .ra-st.vivo{animation:none;background:none;color:var(--text)}
 .ra-barra i{transition:none}}
</style>"""

JS = u"""<script id="radai-atualizar-js">
(function(){
 if(window.radaiAtualizarAgora) return;
 var ATIVAS = ['esperando', 'baixando', 'preparando', 'bundle', 'fechando'];
 var MARCA = 'radai_atualizar_pedido';
 var M = null, laco = null, pid0 = null, reabrindo = false;
 function T(pt){ try{ return window.radaiFrase ? window.radaiFrase(pt) : pt }catch(e){ return pt } }
 function escrever(no, texto){
  if(!no) return;
  if(window.uiTexto) window.uiTexto(no, texto); else no.textContent = texto;
 }
 function pedir(acao){
  return fetch('/api/atualizar', {method:'POST', headers:{'Content-Type':'application/json'},
                                  body: JSON.stringify({acao: acao})})
   .then(function(r){ return r.json() })
   .catch(function(){ return {etapa:'erro', motivo_chave:'O app não respondeu.'} });
 }
 function ler(){
  return fetch('/api/atualizar', {method:'POST', headers:{'Content-Type':'application/json'},
                                  body: JSON.stringify({acao: 'estado'})})
   .then(function(r){ return r.ok ? r.json() : null }).catch(function(){ return null });
 }
 function parar(){ if(laco){ clearTimeout(laco); laco = null } }
 function caixa(){
  if(M && M.veu && M.veu.parentNode) return M;
  var no = document.createElement('div');
  no.className = 'ra-cx';
  no.innerHTML = '<p class="ra-v" hidden><code class="ra-de"></code>'
   + '<span class="ra-seta" aria-hidden="true">&#8594;</span><code class="ra-para"></code></p>'
   + '<p class="ra-st" role="status" aria-live="polite"></p>'
   + '<div class="ra-barra" hidden><i></i></div>'
   + '<p class="ra-txt"></p><p class="ra-det"></p><div class="ra-bts"></div>';
  M = window.uiModal({titulo: T('Atualizar o programa'), no: no, largura: 540,
                      classe: 'ra-modal', aoFechar: function(){ M = null; parar() }});
  return M;
 }
 function q(sel){ return M ? M.corpo.querySelector(sel) : null }
 function botoes(lista){
  var b = q('.ra-bts'); if(!b) return;
  b.innerHTML = '';
  lista.forEach(function(x){
   var e;
   if(x.href){
    e = document.createElement('a'); e.href = x.href; e.target = '_blank'; e.rel = 'noopener';
   } else { e = document.createElement('button'); e.type = 'button' }
   e.className = 'ui-bt' + (x.cls ? ' ' + x.cls : '');
   escrever(e, T(x.rot));
   if(x.fn) e.addEventListener('click', x.fn);
   b.appendChild(e);
  });
  var p = b.querySelector('.pri') || b.querySelector('.ui-bt');
  if(p) p.setAttribute('autofocus', '');
  try{ if(p) p.focus() }catch(e){}
 }
 function fechar(){ if(M) M.fechar() }
 function versoes(d){
  var v = q('.ra-v'); if(!v) return;
  if(d && d.aqui && (d.publicada || d.versao_nova)){
   escrever(q('.ra-de'), String(d.aqui));
   escrever(q('.ra-para'), String(d.publicada || d.versao_nova));
   v.hidden = false;
  }
 }
 function quadro(st, txt, det, vivo){
  var s = q('.ra-st');
  escrever(s, st || '');
  if(s) s.className = 'ra-st' + (vivo ? ' vivo' : '');
  escrever(q('.ra-txt'), txt || '');
  escrever(q('.ra-det'), det || '');
 }
 function barra(pct){
  var b = q('.ra-barra'); if(!b) return;
  if(pct === null || pct === undefined){ b.hidden = true; return }
  b.hidden = false;
  b.querySelector('i').style.width = Math.max(0, Math.min(100, pct)) + '%';
 }
 function tempo(min){
  if(!min) return T('O tempo depende da rede.');
  if(min < 90) return T('Tempo estimado nesta rede: cerca de %s minutos.').replace('%s', String(min));
  return T('Tempo estimado nesta rede: cerca de %s horas.').replace('%s', String(Math.round(min / 60)));
 }
 function seguir(){ parar(); laco = setTimeout(function(){ ler().then(pintar) }, 600) }
 function confirmarInterromper(d){
  quadro(T(d.motivo_chave || ''), T('A série em curso para e volta para a fila, sem contar como falha; o turno da noite, se estiver aberto, é encerrado.'), '', false);
  barra(null);
  botoes([{rot:'Interromper e atualizar', cls:'perigo', fn:function(){ pedir('interromper').then(pintar) }},
          {rot:'Voltar', fn:function(){ pintar(d) }}]);
 }
 function esperarOMotorNovo(){
  if(reabrindo) return;
  reabrindo = true;
  var fim = new Date().getTime() + @TETO_REABERTURA@;
  function sondar(){
   fetch('/api/janela/estado', {method:'POST', headers:{'Content-Type':'application/json'}, body:'{}'})
    .then(function(r){ return r.ok ? r.json() : null })
    .then(function(d){
     if(d && d.pid && pid0 && d.pid !== pid0){
      var ir = function(){ location.replace('/') };
      if(window.radaiJanelaRestaurar) window.radaiJanelaRestaurar().then(ir, ir); else ir();
      return;
     }
     depois();
    }, depois);
  }
  function depois(){
   if(new Date().getTime() > fim){
    if(!M) caixa();
    quadro(T('O app não reabriu em 10 minutos. Abra pelo atalho da área de trabalho.'), '', '', false);
    botoes([{rot:'Fechar', fn:fechar}]);
    return;
   }
   setTimeout(sondar, 1000);
  }
  setTimeout(sondar, 1500);
 }
 function pintar(d){
  d = d || {etapa:'erro', motivo_chave:'O app não respondeu.'};
  if(d.pid && !pid0) pid0 = d.pid;
  if(!M) caixa();
  versoes(d);
  var e = d.etapa;
  if(e === 'ocupado'){
   quadro(T(d.motivo_chave || ''), T('Atualizar agora interromperia isso. A atualização pode esperar terminar, ou interromper agora.'), '', false);
   barra(null);
   botoes([{rot:'Atualizar quando terminar', cls:'pri', fn:function(){ pedir('esperar').then(pintar) }},
           {rot:'Interromper e atualizar agora', cls:'perigo', fn:function(){ confirmarInterromper(d) }},
           {rot:'Cancelar', fn:function(){ pedir('cancelar'); fechar() }}]);
  } else if(e === 'esperando'){
   quadro(T('Esperando terminar para atualizar…'), T('A atualização começa sozinha quando terminar. O vigia e o lote não começam série nova até lá.'), '', true);
   barra(null);
   botoes([{rot:'Cancelar a espera', fn:function(){ pedir('cancelar'); fechar() }},
           {rot:'Fechar', fn:fechar}]);
   seguir();
  } else if(e === 'baixando'){
   quadro(T('Baixando o instalador…'), T('O instalador da versão nova é conferido pela soma SHA-256 que a release publica antes de qualquer coisa rodar.'), '', true);
   barra(d.progresso || 0);
   botoes([{rot:'Cancelar', fn:function(){ pedir('cancelar'); fechar() }}]);
   seguir();
  } else if(e === 'preparando'){
   quadro(T('Preparando a atualização…'), '', '', true);
   barra(100);
   botoes([]);
   seguir();
  } else if(e === 'bundle'){
   var txt = (d.tamanho_gib ? T('Cerca de %s GB de download.').replace('%s', String(Math.round(d.tamanho_gib))) + ' ' : '')
    + tempo(d.tempo_min) + ' '
    + T('O instalador abre na tela de licenças: aceite as licenças e clique em Atualizar tudo. O app continua funcionando até lá.');
   quadro(T('Esta versão precisa de um pacote novo de modelos e bibliotecas.'), txt, '', false);
   barra(null);
   botoes([{rot:'Abrir o instalador', cls:'pri', fn:function(){ pedir('bundle').then(pintar) }},
           {rot:'Agora não', fn:function(){ pedir('cancelar'); fechar() }}]);
  } else if(e === 'preparador'){
   quadro(T('O instalador abriu.'), T('Aceite as licenças e clique em Atualizar tudo; o app fecha quando o instalador pedir.'), '', false);
   barra(null);
   botoes([{rot:'Fechar', fn:fechar}]);
  } else if(e === 'fechando'){
   parar();
   quadro(T('Atualizando… o app reabre sozinho.'), T('O app fecha, o atualizador roda numa janela do Windows e o app reabre sozinho, com a sua configuração.'), '', true);
   barra(null);
   botoes([]);
   esperarOMotorNovo();
  } else if(e === 'erro'){
   parar();
   quadro(T('A atualização não aconteceu.'), T(d.motivo_chave || ''), d.detalhe || '', false);
   barra(null);
   var bs = [];
   if(d.link) bs.push({rot:'Baixar o instalador mais recente', href:d.link});
   bs.push({rot:'Fechar', fn:function(){ pedir('cancelar'); fechar() }});
   botoes(bs);
  } else {
   fechar();
  }
 }
 window.radaiAtualizarAgora = function(){
  reabrindo = false;
  try{ sessionStorage.setItem(MARCA, '1') }catch(e){}
  caixa();
  quadro(T('Preparando a atualização…'), '', '', true);
  botoes([]);
  return pedir('comecar').then(pintar);
 };
 // GUARDA: so a aba que pediu a atualizacao pergunta o estado dela ao abrir
 // cada tela; as outras telas nao falam com a rota.
 function retomar(){
  var pediu = '';
  try{ pediu = sessionStorage.getItem(MARCA) || '' }catch(e){}
  if(!pediu) return;
  ler().then(function(d){
   if(d && ATIVAS.indexOf(d.etapa) >= 0) pintar(d);
   else{ try{ sessionStorage.removeItem(MARCA) }catch(e){} }
  });
 }
 if(document.readyState === 'complete') setTimeout(retomar, 400);
 else window.addEventListener('load', function(){ setTimeout(retomar, 400) });
})();
</script>"""

PARA_A_CASCA = CSS + JS.replace(u"@TETO_REABERTURA@", str(TETO_DA_REABERTURA_MS))
