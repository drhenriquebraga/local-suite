# -*- coding: utf-8 -*-
import shutil
import io
import os
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _cleanup
import _componentes
_cleanup.adotar_prefixo('radai_fechar_')
_cleanup.adotar_prefixo('radai_encerrar_acervo_')


sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(RAIZ, "app")
sys.path.insert(0, APP)

PORTA = 8792

_ACERVO_TESTE = tempfile.mkdtemp(prefix="radai_encerrar_acervo_")
os.environ["RADAI_CALIB_DIR"] = _ACERVO_TESTE

_ok = 0
_falhas = []


def checar(nome, cond, detalhe=u""):
    global _ok
    if cond:
        _ok += 1
        print(u"    OK     %s" % nome)
    else:
        _falhas.append(nome)
        print(u"    FALHA  %s  %s" % (nome, detalhe))


def secao(t):
    print(u"\n  ── %s %s" % (t, u"─" * max(0, 60 - len(t))))


def ler(*p):
    c = _componentes.fonte("/".join(p))
    return io.open(c, encoding="utf-8", errors="replace").read() if os.path.isfile(c) else u""


def teste_costura():
    secao(u"a costura: intacta quando nao acha onde")
    import radai_shutdown as E

    pagina = u"<html><head><title>x</title></head><body><p>oi</p></body></html>"
    saida = E.aplicar(pagina)
    checar(u"costura numa pagina completa", E.MARCA in saida)
    checar(u"e nao duplica quando ja tem", E.aplicar(saida) == saida)

    for rot, p in ((u"sem </head>", u"<body>x</body>"),
                   (u"sem </body>", u"<head></head>x"),
                   (u"vazia", u"")):
        checar(u"pagina %s sai intacta" % rot, E.aplicar(p) == p)

    checar(u"o modulo nao importa o vigia de volta",
           u"import radai_watcher" not in ler("app", "radai_shutdown.py"))


def _saidas_do_dialogo(h):
    import re as _re
    return _re.findall(r'<button class="rx-op[^"]*" id="([^"]+)"', h)


def teste_tres_saidas():
    secao(u"as duas saidas: Fechar tudo e Cancelar")
    import radai_shutdown as E
    h = E.HTML

    checar(u"o dialogo tem exatamente Fechar tudo e Cancelar",
           _saidas_do_dialogo(h) == [u"rx-tudo", u"rx-cancelar"],
           repr(_saidas_do_dialogo(h)))
    isca = h.replace(u'  <button class="rx-op" id="rx-cancelar"',
                     u'  <button class="rx-op" id="rx-so-vigia" type="button">'
                     u'<b>x</b></button>\n  <button class="rx-op" id="rx-cancelar"', 1)
    checar(u"  (isca) a terceira saida de volta e acusada",
           isca != h and _saidas_do_dialogo(isca) != [u"rx-tudo", u"rx-cancelar"])
    checar(u"e nenhum codigo trata a saida que saiu",
           u"rx-so-vigia" not in h)
    checar(u"o dialogo diz que fechar o navegador encerra depois da serie "
           u"em curso e do turno aberto",
           (u">%s<" % FRASE_DO_X_QUE_ESPERA) in h)
    antiga = (u"Fechar a janela do navegador também encerra tudo, mas só "
              u"depois que a série em curso termina; com o turno da noite "
              u"aberto, depois do turno.")
    checar(u"  e diz o caso do turno agendado com o lote andando ate ele (o "
           u"lote termina o que espera e roda o turno inteiro)",
           u"turno agendado" in FRASE_DO_X_QUE_ESPERA
           and u"roda o turno inteiro" in FRASE_DO_X_QUE_ESPERA
           and (u">%s<" % antiga) not in h)
    isca = h.replace(FRASE_DO_X_QUE_ESPERA, antiga, 1)
    checar(u"  (isca) o texto de antes, sem o turno agendado, reprova",
           isca != h and (u">%s<" % FRASE_DO_X_QUE_ESPERA) not in isca)
    checar(u"  e nao diz mais que o X encerra tudo na hora",
           u">Fechar a janela do navegador também encerra tudo.<" not in h)
    checar(u"  e nao promete mais os 3 minutos (o aviso de saida encerra em "
           u"segundos)", u"3 minutos" not in h)

    checar(u"o dialogo consulta o estado antes de perguntar",
           u"fetch('/api/status')" in h)
    checar(u"e avisa quando ha serie em curso",
           u"está sendo contornada agora" in h)

    checar(u"e nao promete uma janela preta que o motor oculto nao tem",
           u"janela preta" not in h)

    checar(u"cancelar nao chama o servidor",
           h.index(u"rx-cancelar") < h.index(u"/api/encerrar"))


def _sem_script(t):
    import re as _re
    return _re.sub(r"<script.*?</script>", " ", t, flags=_re.S)


def teste_a_porta_tem_o_fechar():
    secao(u"o FECHAR APP: na porta, dentro do power, e so nele")
    import re as _re
    import radai_router
    import radai_menu
    import radai_modules

    porta = radai_router.montar_porta()
    marc = _sem_script(porta)
    topo = marc[marc.find(u'<header class="ls-topo"'):]
    topo = topo[:topo.find(u"</header>")]
    eng = _re.search(r'(?s)<details class="ls-ctl ls-engrenagem" data-radai-engrenagem>'
                     r'(.*?)</details>', topo)
    eng = eng.group(1) if eng else u""
    pwr = _re.search(r'(?s)<details class="ls-ctl ls-power" data-radai-power>'
                     r'(.*?)</details>', topo)
    pwr = pwr.group(1) if pwr else u""
    checar(u"a porta tem a ancora do Fechar dentro do power do cabecalho",
           u"data-radai-encerrar" in pwr, topo[-300:])
    checar(u"e a ancora nao mora fora dele",
           u"data-radai-encerrar" not in marc.replace(pwr, u""))
    checar(u"e o dialogo das duas saidas foi costurado",
           u'id="rx-veu"' in marc
           and all(m in marc for m in (u'id="rx-tudo"', u'id="rx-cancelar"')))
    checar(u"o cabecalho da porta tem a engrenagem, com Configuracoes",
           u'href="/config"' in eng, topo[-200:])
    rot_py = ler("app", "radai_router.py")
    fn = rot_py[rot_py.index(u"def montar_porta("):]
    fn = fn[:fn.index(u"\ndef ")]
    checar(u"montar_porta costura o radai_shutdown DEPOIS da costura da porta",
           u"radai_shutdown" in fn and u"radai_menu.aplicar_porta" in fn
           and fn.index(u"radai_shutdown") > fn.index(u"radai_menu.aplicar_porta"))
    handler = rot_py[rot_py.index(u"def _suite():"):]
    handler = handler[:handler.index(u"@app.get")]
    checar(u"e a rota / serve a porta montada por ela",
           u"montar_porta()" in handler)

    import radai_shutdown as E
    checar(u"o botao se chama «Fechar app»", u"'Fechar app'" in E.HTML)
    js = E.aplicar(u"<html><head></head><body></body></html>")
    checar(u"e leva o icone de desligar (SVG, nao glifo)",
           u"<svg" in js and u"M12 4v8" in js and u"@ICO_" not in js)

    for chave in (u"bridge", u"recon3d"):
        p = radai_menu.aplicar(radai_modules.pagina_completa(chave), chave,
                               com_tarefas=False)
        checar(u"[%s] NAO tem a ancora do Fechar" % chave,
               u"data-radai-encerrar" not in _sem_script(p))


_BASE_HERMETICA = u"http://porta.radai.test"


def _fechar_da_porta(pg):
    s = pg.locator(u"[data-radai-power] summary")
    if s.count() == 1 and not pg.evaluate(
            u"document.querySelector('[data-radai-power]').open"):
        s.click()
    return pg.locator(u"[data-radai-power] [data-radai-encerrar] .rx-fechar")


def _abrir_o_dialogo(nav, pagina):
    import json as _json
    from urllib.parse import urlsplit as _us
    ctx = nav.new_context(viewport={"width": 1366, "height": 800})
    pedidos = []

    def atender(route):
        caminho = _us(route.request.url).path
        pedidos.append(caminho)
        if caminho == u"/":
            route.fulfill(status=200, content_type=u"text/html; charset=utf-8",
                          body=pagina)
        elif caminho == u"/api/status":
            route.fulfill(status=200, content_type=u"application/json",
                          body=_json.dumps({u"ocupado": {u"quem": u"lote",
                                                         u"desde": u"03:10"}}))
        else:
            route.fulfill(status=404, body=u"")
    try:
        ctx.route(_BASE_HERMETICA + u"/**", atender)
        pg = ctx.new_page()
        pg.goto(_BASE_HERMETICA + u"/", wait_until="domcontentloaded")
        bt = _fechar_da_porta(pg)
        if bt.count() != 1:
            return (None, u"", False, pedidos)
        bt.click()
        veu = pg.locator(u"#rx-veu")
        aberto = veu.is_visible()
        agora = u""
        if aberto:
            try:
                pg.wait_for_function(
                    u"document.getElementById('rx-agora').textContent"
                    u".indexOf('verificando') < 0", timeout=5000)
            except Exception:
                pass
            agora = pg.locator(u"#rx-agora").inner_text()
        foco = pg.evaluate(u"(document.activeElement||{}).id || ''")
        if aberto:
            pg.keyboard.press(u"Escape")
            aberto = (aberto, not veu.is_visible())
        return (aberto, agora, foco == u"rx-cancelar", pedidos)
    finally:
        ctx.close()


def teste_o_botao_abre_o_dialogo():
    secao(u"o FECHAR APP abre o dialogo (hermetico, com isca)")
    exe = _chromium()
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        sync_playwright = None
    if not exe or sync_playwright is None:
        print(u"    PULADO o navegador: sem Playwright ou sem Chromium")
        return
    import radai_router
    porta = radai_router.montar_porta()
    ligar = u"b.addEventListener('click', abrir);"
    checar(u"o botao se liga ao dialogo por um ouvinte de clique",
           porta.count(ligar) == 1, str(porta.count(ligar)))
    isca = porta.replace(ligar, u"")
    with sync_playwright() as pw:
        nav = pw.chromium.launch(executable_path=exe, headless=True)
        try:
            aberto, agora, foco, pedidos = _abrir_o_dialogo(nav, porta)
            checar(u"o botao nasce dentro da ancora do cabecalho da porta",
                   aberto is not None)
            checar(u"o clique abre o dialogo, e o Escape o fecha",
                   aberto == (True, True), repr(aberto))
            checar(u"antes das saidas ele pergunta ao vigia o que roda",
                   u"/api/status" in pedidos
                   and u"Rodar agora" in agora and u"Fechar tudo" in agora,
                   agora or repr(pedidos))
            checar(u"e o foco vai para o Cancelar (Enter por reflexo nao "
                   u"derruba o lote)", foco)
            aberto_i, _a, _f, pedidos_i = _abrir_o_dialogo(nav, isca)
            checar(u"[isca] sem o ouvinte, o botao aparece e o clique nao "
                   u"abre nada (a checagem distingue as duas versoes)",
                   aberto_i is False and u"/api/status" not in pedidos_i,
                   repr(aberto_i))
        finally:
            nav.close()


def _atalho_do_instalador():
    import re as _re
    ps = ler("installer", "INSTALL.ps1")
    novo = _re.search(r'\$lnk\s*=\s*Join-Path\s+\$d\.pasta\s+"([^"]+)\.lnk"', ps)
    velho = _re.search(r'\$antigo\s*=\s*Join-Path\s+\$d\.pasta\s+"([^"]+)\.lnk"', ps)
    return (novo.group(1) if novo else u""), (velho.group(1) if velho else u"")


_FRASES_DA_DESPEDIDA = (
    u"Fechar o Radioterapia.AI Local Suite",
    u"Radioterapia.AI Local Suite encerrado.",
    u"O motor parou. Pode fechar esta aba. Para abrir "
    u"de novo, use o atalho \"Radioterapia.ai Local Suite\".",
    u"Fechar o programa encerra o motor e a fila desta estação.",
    u"O motor para e a fila também. Nada continua rodando.",
    u"O motor ainda está encerrando.",
    u"Ele termina sozinho em instantes. Se o programa continuar no "
    u"Gerenciador de Tarefas, abra o atalho \"Radioterapia.ai Local Suite\": "
    u"a abertura encerra o que tiver sobrado.",
)

# GUARDA: frase nova entra em portugues e a traducao vem depois; quando ela
# ganhar os doze idiomas, sai daqui e passa para a lista da tela dela.
FRASE_DA_REABERTURA_QUE_NAO_VOLTOU = (
    u"O programa não voltou a abrir em 5 minutos (código %s). Abra pelo "
    u"atalho \"Radioterapia.ai Local Suite\".")
FRASES_DA_REABERTURA = (FRASE_DA_REABERTURA_QUE_NAO_VOLTOU,)
FRASE_DO_X_QUE_ESPERA = (
    u"Fechar a janela do navegador também encerra tudo, mas só depois que a "
    u"série em curso termina; com o turno da noite aberto, depois do turno; "
    u"com o turno agendado e o «Rodar agora» andando até ele, o lote termina "
    u"o que espera, roda o turno inteiro, e só então o programa se encerra.")
FRASE_DO_TURNO_ABERTO = (
    u"O turno da noite está aberto nesta estação: encerrar o programa "
    u"encerra o turno.")
FRASE_DO_TURNO_AGENDADO = (
    u"O turno da noite está agendado na fila desta estação.")
FRASES_DO_FECHAR_COM_TURNO = (FRASE_DO_X_QUE_ESPERA, FRASE_DO_TURNO_ABERTO,
                              FRASE_DO_TURNO_AGENDADO)
FRASES_SEM_TRADUCAO_AINDA = ()


def teste_a_despedida_diz_a_verdade():
    secao(u"a despedida: o atalho que existe, o endereco desta porta, o nome")
    import radai_shutdown as E
    import radai_phrases as F
    h = E.HTML
    novo, velho = _atalho_do_instalador()
    checar(u"o instalador declara o atalho que grava e o que apaga",
           bool(novo) and bool(velho), u"%r / %r" % (novo, velho))
    checar(u"«Fechar tudo» manda usar o atalho que o instalador GRAVA (%s)"
           % novo, bool(novo) and (u'use o atalho "%s"' % novo) in h)
    checar(u"  e nao o que ele APAGA (%s)" % velho,
           bool(velho) and velho not in h)
    checar(u"a despedida nao manda abrir a 8777 fixa", u"8777" not in h)
    checar(u"o dialogo e a despedida dizem o nome do produto, e nao "
           u"«AutoContorno»",
           u'<h3 id="rx-titulo">Fechar o Radioterapia.AI Local Suite</h3>' in h
           and u"AutoContorno" not in h)
    tabela = dict((t[0], t) for t in F.TABELA if isinstance(t, tuple))
    for fr in _FRASES_DA_DESPEDIDA:
        checar(u"  «%s…» esta na tela num literal so" % fr[:36],
               (u"'%s'" % fr) in h or (u">%s<" % fr) in h)
        t = tabela.get(fr)
        checar(u"    e tem chave nos doze idiomas",
               t is not None and len(t) == 12 and all(t), fr[:40])
    telas = h + E.PAGINA_REABRIR
    for fr in FRASES_DA_REABERTURA + FRASES_DO_FECHAR_COM_TURNO:
        checar(u"  «%s…» esta numa tela num literal so" % fr[:36],
               (u"'%s'" % fr) in telas or (u">%s<" % fr) in telas, fr[:60])
        t = tabela.get(fr) or tabela.get(F.normalizar(fr))
        checar(u"    e tem chave nos doze idiomas",
               t is not None and len(t) == 12 and all(t), fr[:40])
    for fr in FRASES_SEM_TRADUCAO_AINDA:
        checar(u"  «%s…» (nova) esta numa tela num literal so" % fr[:36],
               (u"'%s'" % fr) in telas or (u">%s<" % fr) in telas, fr[:60])
        t = tabela.get(fr) or tabela.get(F.normalizar(fr))
        checar(u"    e ainda espera a traducao (com os doze idiomas, mude de "
               u"lista)", not (t is not None and len(t) == 12 and all(t)),
               fr[:40])


def _despedida_no_navegador(nav, pagina, lingua, saida):
    import json as _json
    from urllib.parse import urlsplit as _us
    import radai_languages
    ctx = nav.new_context(viewport={"width": 1366, "height": 800})

    def atender(route):
        caminho = _us(route.request.url).path
        if caminho == u"/":
            route.fulfill(status=200, content_type=u"text/html; charset=utf-8",
                          body=pagina)
        elif caminho == u"/radai-idiomas.js":
            route.fulfill(status=200,
                          content_type=u"application/javascript; charset=utf-8",
                          body=radai_languages.corpo_js())
        elif caminho == u"/api/status":
            route.fulfill(status=200, content_type=u"application/json",
                          body=_json.dumps({u"ocupado": None}))
        elif caminho == u"/api/encerrar":
            route.fulfill(status=200, content_type=u"application/json",
                          body=_json.dumps({u"ok": True, u"encerrando": True}))
        elif caminho == u"/api/pulso":
            route.abort()
        else:
            route.fulfill(status=404, body=u"")
    try:
        ctx.route(_BASE_HERMETICA + u"/**", atender)
        ctx.add_init_script(u"window.close = function(){}")
        pg = ctx.new_page()
        pg.goto(_BASE_HERMETICA + u"/", wait_until="domcontentloaded")
        pg.evaluate(u"localStorage.setItem('radai_idioma', %s); true"
                    % _json.dumps(lingua))
        pg.goto(_BASE_HERMETICA + u"/", wait_until="networkidle")
        _fechar_da_porta(pg).click()
        pg.locator(u"#" + saida).click()
        pg.wait_for_selector(u".rx-fim", timeout=8000)
        pg.wait_for_timeout(300)
        return pg.evaluate(u"document.body.innerText")
    finally:
        ctx.close()


_ORDEM_DO_FECHAR = u"""
window.__ordem = [];
(function(){
 var f0 = window.fetch;
 window.fetch = function(u){
  var p = f0.apply(this, arguments);
  if(String(u).indexOf('/api/pulso') >= 0)
   p.then(function(){ window.__ordem.push('vivo') },
          function(){ window.__ordem.push('caiu') });
  if(String(u).indexOf('/api/encerrar') >= 0) window.__ordem.push('encerrar');
  return p;
 };
 window.close = function(){ window.__ordem.push('fechou') };
})();
"""


def _ordem_do_fechar(nav, pagina, vivos):
    import json as _json
    from urllib.parse import urlsplit as _us
    ctx = nav.new_context(viewport={"width": 1366, "height": 800})
    chamadas = [0]

    def atender(route):
        caminho = _us(route.request.url).path
        if caminho == u"/":
            route.fulfill(status=200, content_type=u"text/html; charset=utf-8",
                          body=pagina)
        elif caminho == u"/api/status":
            route.fulfill(status=200, content_type=u"application/json",
                          body=_json.dumps({u"ocupado": None}))
        elif caminho == u"/api/encerrar":
            route.fulfill(status=200, content_type=u"application/json",
                          body=_json.dumps({u"ok": True, u"encerrando": True}))
        elif caminho == u"/api/pulso":
            chamadas[0] += 1
            if chamadas[0] <= vivos:
                route.fulfill(status=200, content_type=u"application/json",
                              body=_json.dumps({u"radai": True, u"pid": 7}))
            else:
                route.abort()
        else:
            route.fulfill(status=404, body=u"")
    try:
        ctx.route(_BASE_HERMETICA + u"/**", atender)
        ctx.add_init_script(_ORDEM_DO_FECHAR)
        pg = ctx.new_page()
        pg.goto(_BASE_HERMETICA + u"/", wait_until="networkidle")
        _fechar_da_porta(pg).click()
        pg.locator(u"#rx-tudo").click()
        try:
            pg.wait_for_selector(u".rx-fim", timeout=10000)
        except Exception:
            pass
        pg.wait_for_timeout(200)
        return pg.evaluate(u"window.__ordem"), pg.evaluate(
            u"(document.querySelector('.rx-fim')||{}).innerText || ''")
    finally:
        ctx.close()


def teste_o_fechar_espera_a_porta_cair():
    secao(u"Fechar tudo: a aba so fecha depois que a porta deixa de responder")
    exe = _chromium()
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        sync_playwright = None
    if not exe or sync_playwright is None:
        print(u"    PULADO o navegador: sem Playwright ou sem Chromium")
        return
    import radai_router
    porta = radai_router.montar_porta()
    velho = (u".then(function(){ setTimeout(sondar, 300) },\n"
             u"         function(){ setTimeout(sondar, 300) });")
    checar(u"o Fechar tudo sonda a porta depois do pedido de encerrar",
           porta.count(velho) == 1, str(porta.count(velho)))
    isca = porta.replace(velho, u".then(function(){ parou() },\n"
                                u"         function(){ parou() });")
    with sync_playwright() as pw:
        nav = pw.chromium.launch(executable_path=exe, headless=True)
        try:
            ordem, fim = _ordem_do_fechar(nav, porta, 3)
            i_caiu = ordem.index(u"caiu") if u"caiu" in ordem else -1
            i_fechou = ordem.index(u"fechou") if u"fechou" in ordem else -1
            checar(u"o motor respondeu 3 vezes e a aba esperou (%s)"
                   % u",".join(ordem), ordem.count(u"vivo") >= 3, repr(ordem))
            checar(u"  a aba so tentou fechar depois que a porta caiu",
                   0 <= i_caiu < i_fechou, repr(ordem))
            checar(u"  e, sem poder fechar por script, diz que ja pode fechar",
                   u"Pode fechar esta aba" in fim, fim[:160])
            ordem_i, _f = _ordem_do_fechar(nav, isca, 3)
            checar(u"[isca] fechando logo depois do pedido, a aba fecha com o "
                   u"motor ainda vivo (a checagem distingue)",
                   u"fechou" in ordem_i and (u"caiu" not in ordem_i or
                                             ordem_i.index(u"fechou")
                                             < ordem_i.index(u"caiu")),
                   repr(ordem_i))
        finally:
            nav.close()


def teste_a_despedida_no_navegador():
    secao(u"a despedida no navegador: o endereco desta porta, em alemao")
    exe = _chromium()
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        sync_playwright = None
    if not exe or sync_playwright is None:
        print(u"    PULADO o navegador: sem Playwright ou sem Chromium")
        return
    import radai_router
    import radai_phrases as F
    de = F.construir()[u"de"]
    porta = radai_router.montar_porta()
    novo, _velho = _atalho_do_instalador()
    with sync_playwright() as pw:
        nav = pw.chromium.launch(executable_path=exe, headless=True)
        try:
            tudo = _despedida_no_navegador(nav, porta, u"pt-BR", u"rx-tudo")
            checar(u"«Fechar tudo» cita o atalho que o instalador grava",
                   bool(novo) and novo in tudo, tudo[-160:])
            tudo_de = _despedida_no_navegador(nav, porta, u"de", u"rx-tudo")
            esperado = de.get(_FRASES_DA_DESPEDIDA[2], u"")
            checar(u"  e a do «Fechar tudo» tambem, com o nome do atalho "
                   u"intacto", bool(esperado) and esperado in tudo_de
                   and novo in tudo_de, tudo_de[-200:])
        finally:
            nav.close()


_FRASES_DO_ESTADO = (
    u"O «Rodar agora» está segmentando agora (desde %s).",
    u"O vigia está contornando uma série agora (desde %s).",
    u"Uma série está sendo contornada agora (desde %s).",
    u"Fechar tudo interrompe esse trabalho: a série volta para a fila e "
    u"outra máquina pode pegá-la. Nenhum contorno pela metade é gravado.",
    u"Nenhuma série está sendo contornada neste momento.",
    u"Não consegui confirmar o que está em andamento (esta estação tem uma "
    u"versão anterior do vigia). Se houver um lote rodando, Fechar tudo o "
    u"interrompe.",
    u"Não consegui conferir o que está em andamento.",
    u"Encerrando…",
)


def teste_o_estado_tem_chave():
    secao(u"a frase do estado: um literal por sentenca, e chave nos doze")
    import radai_shutdown as E
    import radai_phrases as F
    tabela = dict((F.normalizar(t[0]), t) for t in F.TABELA
                  if isinstance(t, tuple))
    for fr in _FRASES_DO_ESTADO:
        checar(u"«%s…» esta no dialogo num literal so" % fr[:40],
               (u"'%s'" % fr) in E.HTML, fr[:60])
        t = tabela.get(F.normalizar(fr))
        checar(u"  e tem chave nos doze idiomas",
               t is not None and len(t) == 12 and all(t), fr[:40])
    for fr in _FRASES_DO_ESTADO[:3]:
        t = tabela.get(F.normalizar(fr)) or ()
        checar(u"  «%s…»: cada traducao leva o %%s da hora" % fr[:30],
               bool(t) and all(c.count(u"%s") == 1 for c in t), fr[:40])
    checar(u"a frase do caso ocupado nao e montada por concatenacao",
           u"nome + ' agora (desde '" not in E.HTML)


def _estado_e_tab_no_navegador(nav, pagina, lingua, quem=u"lote"):
    import json as _json
    from urllib.parse import urlsplit as _us
    import radai_languages
    ctx = nav.new_context(viewport={"width": 1366, "height": 800})

    def atender(route):
        caminho = _us(route.request.url).path
        if caminho == u"/":
            route.fulfill(status=200, content_type=u"text/html; charset=utf-8",
                          body=pagina)
        elif caminho == u"/radai-idiomas.js":
            route.fulfill(status=200,
                          content_type=u"application/javascript; charset=utf-8",
                          body=radai_languages.corpo_js())
        elif caminho == u"/api/status":
            route.fulfill(status=200, content_type=u"application/json",
                          body=_json.dumps({u"ocupado": {u"quem": quem,
                                                         u"desde": u"22:10"}}))
        else:
            route.fulfill(status=404, body=u"")
    try:
        ctx.route(_BASE_HERMETICA + u"/**", atender)
        pg = ctx.new_page()
        pg.goto(_BASE_HERMETICA + u"/", wait_until="domcontentloaded")
        pg.evaluate(u"localStorage.setItem('radai_idioma', %s); true"
                    % _json.dumps(lingua))
        pg.goto(_BASE_HERMETICA + u"/", wait_until="networkidle")
        _fechar_da_porta(pg).click()
        try:
            pg.wait_for_function(
                u"document.getElementById('rx-agora').textContent"
                u".indexOf('22:10') >= 0", timeout=5000)
        except Exception:
            pass
        pg.wait_for_timeout(250)
        agora = pg.locator(u"#rx-agora").inner_text()
        focos = []
        for _ in range(6):
            pg.keyboard.press(u"Tab")
            focos.append(pg.evaluate(
                u"(function(a){ return a ? (a.id || a.className || a.tagName)"
                u" + (document.getElementById('rx-veu').contains(a) ? '' : '!FORA')"
                u" : '' })(document.activeElement)"))
        for _ in range(2):
            pg.keyboard.press(u"Shift+Tab")
            focos.append(pg.evaluate(
                u"(function(a){ return a ? (a.id || a.className || a.tagName)"
                u" + (document.getElementById('rx-veu').contains(a) ? '' : '!FORA')"
                u" : '' })(document.activeElement)"))
        return agora, focos
    finally:
        ctx.close()


def teste_o_estado_em_alemao_e_o_tab_preso():
    secao(u"o dialogo em alemao: o estado ocupado traduzido, e o Tab preso")
    exe = _chromium()
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        sync_playwright = None
    if not exe or sync_playwright is None:
        print(u"    PULADO o navegador: sem Playwright ou sem Chromium")
        return
    import re as _re
    import radai_router
    import radai_phrases as F
    de = F.construir()[u"de"]
    porta = radai_router.montar_porta()
    velha = u"function estado(cx, frases){"
    isca_estado = porta.replace(
        velha, velha + u" cx.textContent = frases.join(' '); return;", 1)
    ligar = u"else prender(e);"
    isca_tab = porta.replace(ligar, u"")
    checar(u"o dialogo liga o ciclo de foco no ouvinte do teclado",
           porta.count(ligar) == 1, str(porta.count(ligar)))

    def _casa(tr, txt):
        pad = u"(.+?)".join(_re.escape(p) for p in tr.split(u"%s"))
        return bool(_re.search(pad, txt or u""))
    with sync_playwright() as pw:
        nav = pw.chromium.launch(executable_path=exe, headless=True)
        try:
            agora, focos = _estado_e_tab_no_navegador(nav, porta, u"de")
            ocup = de.get(_FRASES_DO_ESTADO[0], u"")
            inter = de.get(F.normalizar(_FRASES_DO_ESTADO[3]), u"")
            checar(u"o «Rodar agora» ocupado sai em alemao, com a hora",
                   bool(ocup) and _casa(ocup, agora) and u"22:10" in agora,
                   agora[:160])
            checar(u"  e a frase do que o «Fechar tudo» interrompe tambem",
                   bool(inter) and inter in agora, agora[:200])
            checar(u"  e nada dela ficou em portugues",
                   u"segmentando" not in agora and u"interrompe" not in agora,
                   agora[:160])
            agora_v, _f = _estado_e_tab_no_navegador(nav, porta, u"de",
                                                     quem=u"vigia")
            ocup_v = de.get(_FRASES_DO_ESTADO[1], u"")
            checar(u"  o vigia ocupado tambem sai em alemao",
                   bool(ocup_v) and _casa(ocup_v, agora_v), agora_v[:160])
            checar(u"o Tab e o Shift+Tab nunca saem do dialogo (%d passos)"
                   % len(focos), bool(focos)
                   and not any(f.endswith(u"!FORA") for f in focos), repr(focos))
            checar(u"  e o Tab do ultimo botao volta ao primeiro",
                   u"rx-tudo" in focos, repr(focos))
            agora_i, _f = _estado_e_tab_no_navegador(nav, isca_estado, u"de")
            checar(u"[isca] as duas sentencas num no so ficam em portugues",
                   u"segmentando" in agora_i, agora_i[:120])
            _a, focos_i = _estado_e_tab_no_navegador(nav, isca_tab, u"de")
            checar(u"[isca] sem o ciclo de foco, o Tab sai para tras do veu",
                   any(f.endswith(u"!FORA") for f in focos_i), repr(focos_i))
        finally:
            nav.close()


def teste_lock():
    secao(u"fechar tudo solta o lock da serie em curso")
    fonte = ler("app", "radai_watcher.py")

    checar(u"existe encerrar_tudo()", u"def encerrar_tudo(" in fonte)
    fn = fonte[fonte.index(u"def encerrar_tudo("):]
    fn = fn[:fn.index(u"\ndef ")]
    for chamada in (u"_cancelar_o_trabalho_em_curso()",
                    u"encerrar_filhos_do_motor(",
                    u"soltar_os_locks_deste_processo()",
                    u"encerrar_sinalizacao()", u"ENCERRANDO.set()"):
        checar(u"  e chama %s" % chamada, chamada in fn)
    checar(u"  e nao religa servico nenhum (a pausa de servicos saiu)",
           u"_ov.encerrar(" not in fn and u"radai_overnight" not in fn)
    checar(u"  e o cancelamento vem antes de soltar os locks",
           fn.find(u"_cancelar_o_trabalho_em_curso()")
           < fn.find(u"soltar_os_locks_deste_processo()"))
    checar(u"ele pausa o worker", u'STATE["paused"] = True' in fonte)
    checar(u"e chama unclaim na serie em curso",
           u'unclaim(atual["sdir"], atual["uid_cheio"])' in fonte)
    checar(u"e o current guarda o caminho completo para isso",
           u'"sdir": s["dir"], "uid_cheio": s["uid"]' in fonte)

    checar(u"o servidor e guardado para poder sair",
           u'SERVIDOR["s"] = uvicorn.Server(config)' in fonte)
    codigo = u"\n".join(l for l in fonte.splitlines()
                        if not l.lstrip().startswith("#"))
    checar(u"e a saida e limpa (should_exit), nao os._exit",
           u"should_exit = True" in codigo and u"os._exit(" not in codigo)

    checar(u"a rota recebe a funcao por lambda (ela e definida depois)",
           u"radai_shutdown.montar(app, lambda: encerrar_tudo())" in fonte)


def _chromium():
    base = os.path.join(os.environ.get("LOCALAPPDATA", ""), "ms-playwright")
    if not os.path.isdir(base):
        return None
    for nome in sorted(os.listdir(base), reverse=True):
        if not nome.startswith("chromium-"):
            continue
        for sub in ("chrome-win64", "chrome-win"):
            exe = os.path.join(base, nome, sub, "chrome.exe")
            if os.path.isfile(exe):
                return exe
    return None


def _contraste(c1, c2):
    import re as _re

    def lum(c):
        v = [float(x) for x in _re.findall(r"[\d.]+", c)[:3]]
        out = []
        for x in v:
            x /= 255.0
            out.append(x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4)
        return 0.2126 * out[0] + 0.7152 * out[1] + 0.0722 * out[2]
    a, b = lum(c1), lum(c2)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def _no_navegador(base):
    exe = _chromium()
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        sync_playwright = None
    if not exe or sync_playwright is None:
        print(u"    PULADO o navegador: sem Playwright ou sem Chromium")
        return
    with sync_playwright() as pw:
        nav = pw.chromium.launch(executable_path=exe, headless=True)
        try:
            pg = nav.new_page(viewport={"width": 1366, "height": 800})
            pg.goto(base + "/", wait_until="networkidle")
            bt = _fechar_da_porta(pg)
            checar(u"[navegador] o FECHAR APP aparece no menu do power da porta",
                   bt.count() == 1 and bt.is_visible(), str(bt.count()))
            if bt.count() != 1:
                return
            checar(u"[navegador] e diz FECHAR APP",
                   bt.inner_text().strip() == u"FECHAR APP",
                   bt.inner_text())
            cb = bt.bounding_box()
            checar(u"[navegador] no canto direito, sob o power",
                   bool(cb) and 1366 - (cb["x"] + cb["width"]) < 60
                   and cb["y"] < 160, u"%s" % cb)
            checar(u"[navegador] e a engrenagem esta no cabecalho da porta, sem trilho",
                   pg.locator(u'.ls-topo [data-radai-engrenagem] a[href="/config"]')
                   .count() == 1 and pg.locator(u".radai-menu").count() == 0)
            for tema in (u"escuro", u"claro"):
                pg.evaluate(u"localStorage.setItem('radai_tema', '%s'); true"
                            % tema)
                pg.reload(wait_until="networkidle")
                _fechar_da_porta(pg)
                cor = pg.evaluate(
                    u"(function(){var b=document.querySelector('.rx-fechar');"
                    u"var s=getComputedStyle(b);return [s.color,"
                    u"s.backgroundColor,getComputedStyle(document.body)"
                    u".backgroundColor]})()")
                fundo = cor[1] if not cor[1].startswith(u"rgba(0, 0, 0, 0") \
                    else cor[2]
                r = _contraste(cor[0], fundo)
                checar(u"[navegador] tema %s: o texto do botao passa a AA "
                       u"(%.2f:1)" % (tema, r), r >= 4.5, repr(cor))
            pg.evaluate(u"localStorage.removeItem('radai_tema'); true")
            pg.reload(wait_until="networkidle")
            pedidos = []
            pg.on("request", lambda rq: pedidos.append(rq.url))
            _fechar_da_porta(pg).click()
            veu = pg.locator("#rx-veu")
            checar(u"[navegador] o clique abre o dialogo",
                   veu.is_visible() and u"on" in (veu.get_attribute("class")
                                                  or u""))
            try:
                pg.wait_for_function(
                    u"document.getElementById('rx-agora').textContent"
                    u".indexOf('verificando') < 0", timeout=8000)
                agora = pg.locator("#rx-agora").inner_text()
            except Exception:
                agora = u""
            checar(u"[navegador] e pergunta ao vigia o que roda antes de "
                   u"oferecer as saidas",
                   any(u.endswith(u"/api/status") for u in pedidos)
                   and bool(agora), agora or repr(pedidos[-5:]))
            checar(u"[navegador] com as duas saidas visiveis",
                   all(pg.locator(s).is_visible()
                       for s in (u"#rx-tudo", u"#rx-cancelar"))
                   and pg.locator(u"#rx-so-vigia").count() == 0)
            pg.locator("#rx-cancelar").click()
            checar(u"[navegador] Cancelar fecha e nada e alterado",
                   not veu.is_visible())

            ctx = nav.new_context(viewport={"width": 1366, "height": 800})
            try:
                pg2 = ctx.new_page()
                pg2.goto(base + "/lote", wait_until="domcontentloaded")
                vb = pg2.locator(u".rc-topo [data-radai-voltar]")
                checar(u"[navegador] /lote digitado: o Voltar e o pai",
                       vb.get_attribute(u"data-radai-destino") == u"pai"
                       and vb.get_attribute(u"href") == u"/autocontorno",
                       u"%s %s" % (vb.get_attribute(u"data-radai-destino"),
                                   vb.get_attribute(u"href")))
                popup = pg2.locator(u".ui-modal-veu.vis .ui-ps-modal")
                try:
                    popup.wait_for(state=u"visible", timeout=8000)
                    abriu = True
                except Exception:
                    abriu = False
                if abriu:
                    pg2.locator(u".ui-modal-veu.vis .ui-modal-x").click()
                try:
                    pg2.locator(u".ui-modal-veu").wait_for(state=u"detached",
                                                           timeout=5000)
                    sumiu = True
                except Exception:
                    sumiu = False
                checar(u"[navegador] /lote abre o popup de series sozinho, e o "
                       u"X dele o fecha antes de usar o trilho",
                       abriu and sumiu, u"abriu=%s sumiu=%s" % (abriu, sumiu))
                with pg2.expect_navigation():
                    pg2.locator(u'.radai-menu a[href="/config"]').first.click()
                vb = pg2.locator(u".rc-topo [data-radai-voltar]")
                checar(u"[navegador] em /config vindo do trilho do /lote, o "
                       u"Voltar aponta o /lote (e nao a porta)",
                       vb.get_attribute(u"data-radai-destino") == u"historico"
                       and vb.get_attribute(u"href") == u"/lote",
                       u"%s %s" % (vb.get_attribute(u"data-radai-destino"),
                                   vb.get_attribute(u"href")))
                with pg2.expect_navigation():
                    vb.click()
                from urllib.parse import urlsplit as _us
                checar(u"[navegador] e o clique volta para o /lote",
                       _us(pg2.url).path == u"/lote", pg2.url)
            finally:
                ctx.close()
        finally:
            nav.close()


_PROG_TETO = r'''
import json, os, socket, sys, threading, time
sys.path.insert(0, os.environ["RADAI_APP_TESTE"])
import radai_watcher as W
import uvicorn
from fastapi import FastAPI
s = socket.socket(); s.bind(("127.0.0.1", 0)); porta = s.getsockname()[1]; s.close()
cfg = W.config_do_servidor(FastAPI(), porta)
srv = uvicorn.Server(cfg)
t = threading.Thread(target=srv.run, daemon=True)
t.start()
for _ in range(150):
    if srv.started:
        break
    time.sleep(0.1)
class _Fantasma(object):
    pass
f = _Fantasma()
a = srv.servers[0]
a.get_loop().call_soon_threadsafe(a._attach, f)
time.sleep(0.5)
t0 = time.time()
srv.should_exit = True
t.join(40)
print(json.dumps({"subiu": bool(srv.started), "saiu": not t.is_alive(),
                  "s": round(time.time() - t0, 1),
                  "teto": getattr(cfg, "timeout_graceful_shutdown", None)}))
sys.stdout.flush()
os._exit(0)
'''


def teste_a_saida_tem_teto():
    secao(u"a saida limpa tem teto, mesmo com uma conexao presa")
    trab = tempfile.mkdtemp(prefix="radai_fechar_teto_")
    cfg = os.path.join(trab, "teste.config")
    io.open(cfg, "w", encoding="utf-8").write(
        "\n".join(["ROOT=", "TPS_DESTINO=eclipse", "PORT=%d" % PORTA, "DRY_RUN=1", ""]))
    env = dict(os.environ)
    env.update({"RADAI_CONFIG": cfg, "RADAI_CALIB_DIR": trab,
                "RADAI_APP_TESTE": APP, "PYTHONIOENCODING": "utf-8:replace"})
    try:
        r = subprocess.run([sys.executable, "-c", _PROG_TETO], cwd=APP,
                           env=env, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=90)
        linha = [l for l in (r.stdout or u"").splitlines()
                 if l.startswith(u"{")]
        import json as _json
        d = _json.loads(linha[-1]) if linha else {}
        detalhe = d or ((r.stderr or u"")[-300:])
    except subprocess.TimeoutExpired:
        d, detalhe = {}, u"o processo filho nao saiu em 90 s"
    except Exception as e:
        d, detalhe = {}, u"%s: %s" % (type(e).__name__, e)
    finally:
        shutil.rmtree(trab, ignore_errors=True)
    checar(u"com um cliente que nunca sai, o servidor do vigia sai assim "
           u"mesmo (teto da saida limpa)",
           d.get("subiu") and d.get("saiu"), detalhe)
    fonte = ler("app", "radai_watcher.py")
    checar(u"  e o main monta o servidor por config_do_servidor (a funcao "
           u"medida aqui)",
           u"config = config_do_servidor(app, PORT)" in fonte
           and u"uvicorn.Config(app, host" not in fonte.split(
               u"def main(")[-1])


def teste_vivo():
    secao(u"o vigia sobe, responde, e encerra quando mandam")

    def pede(caminho, dados=None):
        u = "http://127.0.0.1:%d%s" % (PORTA, caminho)
        req = urllib.request.Request(
            u, data=(dados.encode("utf-8") if dados else None),
            headers={"Content-Type": "application/json"},
            method="POST" if dados is not None else "GET")
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.read().decode("utf-8", "replace")

    trab = tempfile.mkdtemp(prefix="radai_fechar_")
    cfg = os.path.join(trab, "teste.config")
    io.open(cfg, "w", encoding="utf-8").write(
        "\n".join(["ROOT=", "TPS_DESTINO=eclipse", "PORT=%d" % PORTA, "DRY_RUN=1", "DAYS_BACK=1", ""]))
    env = dict(os.environ)
    env["RADAI_CONFIG"] = cfg
    env["RADAI_CALIB_DIR"] = trab
    env["PYTHONIOENCODING"] = "utf-8:replace"
    env["LOCALAPPDATA"] = os.path.join(trab, "ad")
    env["RADAI_REGISTRO_DIR"] = os.path.join(trab, "registro")
    env["RADAI_URL_VERSOES"] = "0"
    env["RADAI_NOTIFICACAO"] = "0"

    p = subprocess.Popen([sys.executable, _componentes.fonte("app/radai_watcher.py")],
                         cwd=APP, env=env, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True,
                         encoding="utf-8", errors="replace")
    _saida_do_vigia = []

    def _drenar():
        try:
            for _linha in p.stdout:
                _saida_do_vigia.append(_linha)
        except Exception:
            pass

    threading.Thread(target=_drenar, daemon=True).start()
    try:
        subiu = False
        for _ in range(60):
            time.sleep(0.5)
            if p.poll() is not None:
                break
            try:
                pede("/api/status")
                subiu = True
                break
            except Exception:
                pass
        checar(u"o vigia sobe", subiu)
        if not subiu:
            return

        import json as _jv
        import radai_pulso as _P
        est = _jv.loads(pede("/api/pulso"))
        pais = dict((q, pai) for (q, pai, _n) in _P._processos())
        checar(u"o pulso diz o PID do motor (a reabertura reconhece o novo)",
               est.get("pid") in (p.pid,) or pais.get(est.get("pid")) == p.pid,
               repr(est))
        with urllib.request.urlopen("http://127.0.0.1:%d/api/pulso/sinal"
                                    % PORTA, timeout=10) as r:
            tipo, corpo = r.headers.get("Content-Type", ""), r.read()
        checar(u"o sinal da pagina local e uma imagem de verdade",
               tipo.startswith("image/gif") and corpo.startswith(b"GIF89a"),
               tipo)
        with urllib.request.urlopen("http://127.0.0.1:%d/api/reabrir" % PORTA,
                                    timeout=10) as r:
            reab = r.read().decode("utf-8", "replace")
        checar(u"a pergunta da reabertura e servida, com as duas saidas e o "
               u"pulso", all(m in reab for m in (u'id="rr-continuar"',
                                                u'id="rr-reabrir"',
                                                u"radai-pulso-js")))

        def tela(rota):
            return urllib.request.urlopen(
                "http://127.0.0.1:%d%s" % (PORTA, rota), timeout=10
            ).read().decode("utf-8", "replace")

        import json as _json
        sys.path.insert(0, APP)
        import radai_consent as _CS
        io.open(os.path.join(trab, _CS.ARQUIVO_ACEITE), "w",
                encoding="utf-8").write(_json.dumps(
                    _CS.montar_registro(u"bateria",
                                        [k for k, _t, _d in _CS.PONTOS]),
                    ensure_ascii=False))
        checar(u"sem aceite, a home e o portao",
               u'id="ac_ok"' in tela("/aceite"))

        home = tela("/")
        home_m = _sem_script(home)
        checar(u"o botao chega na porta da suite",
               u"data-radai-encerrar" in home_m,
               u"sem a ancora o JS nao tem onde escrever")
        checar(u"com o dialogo das duas saidas",
               all(m in home for m in (u"rx-tudo", u"rx-cancelar"))
               and u"rx-so-vigia" not in home)
        vigia = tela("/vigia")
        vigia_m = _sem_script(vigia)
        checar(u"e NAO na tela de trabalho",
               u"data-radai-encerrar" not in vigia_m)
        checar(u"que continua tendo o caminho de volta",
               u'class="ui-volta"' in vigia and u'href="/autocontorno"' in vigia)

        import re as _re_s
        import radai_breadcrumb as _B
        servidas, com_voltar, fechar_fora = 0, 0, []
        for _ch, (_rot, _rota, _pai) in sorted(_B.ARVORE.items()):
            try:
                corpo = tela(_rota)
            except Exception:
                continue
            if u"<html" not in corpo[:600].lower():
                continue
            servidas += 1
            m = _sem_script(corpo)
            if u"data-radai-encerrar" in m and _rota != u"/":
                fechar_fora.append(_rota)
            if u"data-radai-voltar" not in m:
                continue
            com_voltar += 1
            _js = _re_s.search(r'(?s)<script id="radai-ui-js">(.*?)</script>',
                               corpo)
            checar(u"[%s] o Voltar marcado chega com a pilha do historico, "
                   u"e o cabecalho diz o nome da tela" % _rota,
                   bool(_js) and u"function histRegistrar(" in _js.group(1)
                   and u'<header class="rc-topo" data-radai-tela="' in m)
        checar(u"as telas da arvore foram servidas (%d, %d com Voltar)"
               % (servidas, com_voltar), servidas >= 12 and com_voltar >= 10,
               u"%d / %d" % (servidas, com_voltar))
        ainda_em = ()
        checar(u"e nenhuma alem da porta tem o Fechar (fora as declaradas)",
               not [r for r in fechar_fora if r not in ainda_em],
               u", ".join(fechar_fora))
        consertadas = [r for r in ainda_em if r not in fechar_fora]
        checar(u"a excecao declarada ainda vale (tire da lista a tela que "
               u"ja nao costura o Fechar)", not consertadas,
               u", ".join(consertadas))

        _no_navegador(u"http://127.0.0.1:%d" % PORTA)

        pede("/api/encerrar", '{"modo":"vigia"}')
        time.sleep(1.2)
        checar(u"modo 'vigia' NAO encerra o processo", p.poll() is None)

        try:
            pede("/api/encerrar", '{"modo":"tudo"}')
        except (urllib.error.URLError, OSError):
            pass
        for _ in range(60):
            time.sleep(0.25)
            if p.poll() is not None:
                break
        checar(u"modo 'tudo' encerra o processo", p.poll() is not None,
               u"ainda vivo; ultimas linhas do vigia: %s"
               % u" | ".join(l.strip() for l in _saida_do_vigia[-8:]))
        if p.poll() is not None:
            checar(u"e sai limpo (codigo 0)", p.returncode == 0,
                   str(p.returncode))
    finally:
        if p.poll() is None:
            p.kill()


def teste_pulso_e_vigilancia():
    secao(u"o pulso das telas e a vigilancia do motor sem janela")
    import radai_pulso as P
    agora = [1000.0]

    def rel():
        return agora[0]

    p = P.Pulso(0.0, relogio=rel)
    agora[0] += 10000.0
    checar(u"desarmado, o silencio nunca vence", not p.venceu())
    p.armar(180.0)
    agora[0] += 179.0
    checar(u"armado: 179 s de silencio ainda nao vencem", not p.venceu())
    agora[0] += 1.0
    checar(u"  e 180 s vencem", p.venceu())
    p.bater()
    checar(u"  e um pulso zera o relogio", not p.venceu() and p.batidas == 1)

    checar(u"motor sem janela: 3 minutos de tolerancia",
           P.tolerancia_do_ambiente(True, {}) == 180.0)
    checar(u"motor com janela: o pulso nao encerra nada",
           P.tolerancia_do_ambiente(False, {}) == 0.0)
    checar(u"RADAI_PULSO_S manda (bateria)",
           P.tolerancia_do_ambiente(True, {P.VARIAVEL_TOLERANCIA: u"6"}) == 6.0)
    checar(u"  e lixo nela volta ao padrao",
           P.tolerancia_do_ambiente(True, {P.VARIAVEL_TOLERANCIA: u"x"}) == 180.0)
    checar(u"o motor sem janela se reconhece por RADAI_MOTOR_OCULTO=1",
           P.motor_oculto({P.VARIAVEL_OCULTO: u"1"}) and not P.motor_oculto({}))

    pedidos, encerrou, linhas = [], [], []
    oc = [False]
    vp = P.Pulso(0.0, relogio=rel)
    v = P.Vigilancia(vp, lambda: encerrou.append(1), lambda: oc[0],
                     log=linhas.append,
                     acordado=lambda s: pedidos.append(s) or True,
                     navegador_aberto=lambda: None)
    v.passo()
    checar(u"fila parada: nao pede nada ao Windows", pedidos == [])
    oc[0] = True
    v.passo()
    v.passo()
    checar(u"fila rodando: pede para nao suspender, uma vez so",
           pedidos == [True], repr(pedidos))
    oc[0] = False
    v.passo()
    checar(u"fila esvaziou: devolve a suspensao ao Windows",
           pedidos == [True, False], repr(pedidos))
    vp.armar(5.0)
    agora[0] += 6.0
    v.passo()
    v.passo()
    checar(u"sem pulso alem da tolerancia: encerra tudo, e uma vez so",
           encerrou == [1], repr(encerrou))
    checar(u"  e o log diz o motivo",
           any(u"navegador foi fechado" in l for l in linhas), repr(linhas))

    class _EmDia(object):
        tolerancia_s = 5.0

        def venceu(self):
            return False
    v2 = P.Vigilancia(_EmDia(), lambda: encerrou.append(2), lambda: False,
                      acordado=lambda s: True)
    v2.passo()
    checar(u"  (isca) com o pulso em dia, nada encerra", encerrou == [1])

    aberto = [True]
    enc3, lin3 = [], []
    vp3 = P.Pulso(5.0, relogio=rel)
    v3 = P.Vigilancia(vp3, lambda: enc3.append(1), lambda: True,
                      log=lin3.append, acordado=lambda s: True,
                      navegador_aberto=lambda: aberto[0])
    agora[0] += 600.0
    v3.passo()
    v3.passo()
    checar(u"aba adormecida (sem pulso, navegador do programa aberto): "
           u"a fila nao e encerrada", enc3 == [], repr(enc3))
    checar(u"  e o log diz uma vez so",
           sum(1 for l in lin3 if u"continua aberto" in l) == 1, repr(lin3))
    aberto[0] = False
    v3.passo()
    checar(u"  fechado o navegador, encerra", enc3 == [1], repr(enc3))
    aberto[0] = None
    enc4 = []
    v4 = P.Vigilancia(P.Pulso(5.0, relogio=rel), lambda: enc4.append(1),
                      lambda: False, acordado=lambda s: True,
                      navegador_aberto=lambda: aberto[0])
    agora[0] += 600.0
    v4.passo()
    checar(u"  sem como saber (navegador padrao, sem perfil): encerra como antes",
           enc4 == [1], repr(enc4))

    base = tempfile.mkdtemp(prefix=u"radai_t_perfil_")
    try:
        checar(u"perfil que nao existe: nao se sabe (None)",
               P.navegador_do_programa_aberto(os.path.join(base, u"x")) is None)
        checar(u"perfil sem lockfile: navegador fechado",
               P.navegador_do_programa_aberto(base) is False)
        io.open(os.path.join(base, u"lockfile"), "w").close()
        checar(u"perfil com lockfile (o Chromium o apaga ao fechar): aberto",
               P.navegador_do_programa_aberto(base) is True)
    finally:
        shutil.rmtree(base, ignore_errors=True)
    checar(u"o perfil e o mesmo do lancador (%TEMP%\\radai_janela)",
           P.perfil_da_janela({u"TEMP": u"C:\\T"}) == os.path.join(u"C:\\T", u"radai_janela")
           and u'set "PERFIL=%TEMP%\\radai_janela"' in ler("app", "launchers",
                                                          "open_browser.cmd"))

    fonte = ler("app", "radai_pulso.py")
    checar(u"o pedido ao Windows e ES_CONTINUOUS | ES_SYSTEM_REQUIRED",
           P.ES_CONTINUOUS == 0x80000000 and P.ES_SYSTEM_REQUIRED == 0x1
           and u"SetThreadExecutionState" in fonte)


def teste_o_pulso_vai_em_toda_tela():
    secao(u"o script do pulso entra em toda tela servida")
    import radai_pulso as P
    h = u"<html><head></head><body><p>x</p></body></html>"
    s = P.injetar(h)
    checar(u"a tela recebe o pulso antes do </body>",
           P.MARCA in s and s.index(P.MARCA) < s.lower().rindex(u"</body>"))
    checar(u"  e nao duplica", P.injetar(s) == s)
    checar(u"  e documento sem </body> sai intacto",
           P.injetar(u"<p>x</p>") == u"<p>x</p>")

    def es5(js):
        return (u"=>" not in js and u"fetch(" not in js
                and u"let " not in js and u"const " not in js)
    checar(u"o script e ES5 (pulsa ate na pagina do portao do IE11)",
           es5(P.SCRIPT))
    checar(u"  (isca) um arrow no script seria acusado",
           not es5(P.SCRIPT.replace(u"function p(){", u"var p=()=>{")))
    checar(u"ele pulsa na rota que o servidor monta",
           (u'"%s"' % P.ROTA) in P.SCRIPT)
    checar(u"  e pelo menos tres vezes dentro da tolerancia",
           P.INTERVALO_DA_TELA_S * 3 <= P.TOLERANCIA_S)
    checar(u"  e tres vezes dentro da graca do fechar (aba visivel)",
           P.INTERVALO_DA_TELA_S * 3 <= P.GRACA_DO_FECHAR_S)
    checar(u"a graca do fechar e de 15 s", P.GRACA_DO_FECHAR_S == 15.0)
    checar(u"cada aba se identifica no pulso",
           u"o={aba:aba}" in P.SCRIPT and u"Math.random()" in P.SCRIPT)
    checar(u"ao fechar, a aba avisa por beacon, na rota do pulso",
           u'addEventListener("pagehide"' in P.SCRIPT
           and (u'navigator.sendBeacon("%s",corpo(1))' % P.ROTA) in P.SCRIPT
           and u"o.saindo=true" in P.SCRIPT
           and u"JSON.stringify(o)" in P.SCRIPT)
    checar(u"  e acorda as irmas pelo canal, que pulsam na hora",
           (u'new BroadcastChannel("%s")' % P.CANAL) in P.SCRIPT
           and u"c.onmessage=function(){p();" in P.SCRIPT
           and u'c.postMessage("saindo")' in P.SCRIPT)
    checar(u"  e a pagina que volta do cache pulsa",
           u'addEventListener("pageshow"' in P.SCRIPT
           and u"e.persisted" in P.SCRIPT)
    checar(u"o beacon e o canal sao opcionais (o IE11 nao tem)",
           u"if(navigator.sendBeacon)" in P.SCRIPT
           and u"if(window.BroadcastChannel)" in P.SCRIPT)
    checar(u"o corpo do pulso e lido sem confiar no que vem",
           P.ler_corpo_do_pulso(b'{"aba":"ab12","saindo":true}') == (u"ab12", True)
           and P.ler_corpo_do_pulso(b"{}") == (None, False)
           and P.ler_corpo_do_pulso(b"lixo") == (None, False)
           and P.ler_corpo_do_pulso(b'{"aba":"<x>"}') == (None, False)
           and P.ler_corpo_do_pulso(b'{"saindo":"sim"}') == (None, False))


def teste_o_aviso_de_saida():
    secao(u"fechar pelo X: o aviso da aba e a graca de 15 s")
    import radai_pulso as P
    agora = [5000.0]

    def rel():
        return agora[0]

    p = P.Pulso(180.0, relogio=rel, graca_s=15.0)
    p.bater(u"A")
    p.bater(u"B")
    agora[0] += 4.0
    checar(u"duas abas: a irma que pulsou ha mais de 3 s deixa a saida "
           u"pendente", p.sair(u"A") is True and p.saida_pendente())
    agora[0] += 1.0
    p.bater(u"B")
    checar(u"  e o pulso dela (acordada pelo canal) a cancela",
           not p.saida_pendente())
    p2 = P.Pulso(180.0, relogio=rel, graca_s=15.0)
    p2.bater(u"A")
    agora[0] += 10.0
    p2.bater(u"B")
    agora[0] += 1.0
    checar(u"a irma que pulsou ANTES do aviso chegar conta como viva",
           p2.sair(u"A") is False and not p2.saida_pendente())
    p3 = P.Pulso(180.0, relogio=rel, graca_s=15.0)
    p3.bater(u"A")
    agora[0] += 10.0
    checar(u"aba unica que fecha: saida pendente", p3.sair(u"A") is True
           and p3.saida_pendente())
    agora[0] += 14.0
    checar(u"  14 s depois ainda nao vence", not p3.saida_vencida())
    agora[0] += 1.0
    checar(u"  15 s depois vence", p3.saida_vencida())
    p4 = P.Pulso(180.0, relogio=rel, graca_s=15.0)
    p4.sair(u"A")
    agora[0] += 1.0
    p4.bater(u"N")
    checar(u"navegar entre paginas: a pagina nova pulsa e cancela a saida",
           not p4.saida_pendente())
    p5 = P.Pulso(180.0, relogio=rel, graca_s=15.0)
    p5.sair(u"A")
    agora[0] += 0.5
    p5.bater(u"A")
    checar(u"o pulso atrasado da propria aba que fechou nao cancela",
           p5.saida_pendente())
    agora[0] += 5.0
    p5.bater(u"A")
    checar(u"  mas a mesma aba voltando do cache, segundos depois, cancela",
           not p5.saida_pendente())
    p6 = P.Pulso(180.0, relogio=rel, graca_s=15.0)
    p6.sair(None)
    agora[0] += 1.0
    p6.bater()
    checar(u"pulso sem aba (pagina antiga) tambem cancela",
           not p6.saida_pendente())
    p7 = P.Pulso(0.0, relogio=rel, graca_s=15.0)
    p7.sair(u"A")
    agora[0] += 60.0
    checar(u"desarmado (motor com janela), a saida nunca vence",
           not p7.saida_vencida())
    checar(u"RADAI_PULSO_GRACA_S manda (bateria), e lixo volta aos 15 s",
           P.graca_do_ambiente({P.VARIAVEL_GRACA: u"3"}) == 3.0
           and P.graca_do_ambiente({P.VARIAVEL_GRACA: u"x"}) == 15.0
           and P.graca_do_ambiente({}) == 15.0)

    def vig(pulso, aberto, oc=False):
        enc, lin = [], []
        v = P.Vigilancia(pulso, lambda: enc.append(1), lambda: oc,
                         log=lin.append, acordado=lambda s: True,
                         navegador_aberto=lambda: aberto)
        return v, enc, lin

    for aberto, rot in ((False, u"navegador do programa fechado"),
                        (None, u"sem perfil (navegador padrao)")):
        q = P.Pulso(180.0, relogio=rel, graca_s=15.0)
        q.sair(u"A")
        v, enc, lin = vig(q, aberto, oc=True)
        agora[0] += 10.0
        v.passo()
        checar(u"%s: 10 s depois do aviso, nada encerra" % rot, enc == [])
        agora[0] += 5.0
        v.passo()
        v.passo()
        checar(u"  15 s depois, encerra tudo uma vez so, mesmo com a fila "
               u"rodando", enc == [1], repr(enc))
        checar(u"  e o log diz que a ultima aba fechou",
               any(u"ultima aba do programa foi fechada" in l for l in lin),
               repr(lin))
    q = P.Pulso(180.0, relogio=rel, graca_s=15.0)
    q.sair(u"A")
    v, enc, lin = vig(q, True)
    agora[0] += 16.0
    v.passo()
    checar(u"com outra janela do perfil do programa aberta: nada encerra",
           enc == [] and not q.saida_pendente(), repr(enc))
    checar(u"  e o log diz por que", any(u"continua aberto" in l for l in lin))
    agora[0] += 100.0
    v.passo()
    checar(u"  e quem decide dali em diante e a tolerancia", enc == [])
    q = P.Pulso(180.0, relogio=rel, graca_s=15.0)
    q.sair(u"A")
    v, enc, lin = vig(q, False)
    agora[0] += 5.0
    q.bater(u"B")
    agora[0] += 20.0
    v.passo()
    checar(u"(isca) outra aba pulsou dentro da graca: nada encerra",
           enc == [], repr(enc))
    checar(u"o laco da vigilancia anda de segundo em segundo (encerra entre "
           u"15 e 16 s)", P.INTERVALO_DA_VIGILANCIA_S <= 1.0)
    checar(u"o servidor do vigia monta o pulso",
           u"radai_pulso.montar(app, PULSO)" in ler("app", "radai_watcher.py"))


def teste_a_captura_do_console():
    secao(u"sem janela, print e traceback viram linha de log")
    import radai_pulso as P
    linhas = []
    c = P.CapturaDoConsole(linhas.append)
    c.write(u"meia ")
    checar(u"linha pela metade espera o fim", linhas == [])
    c.write(u"linha\noutra\n\n")
    checar(u"cada linha inteira chega uma vez",
           linhas == [u"meia linha", u"outra"], repr(linhas))
    eco = []

    def destino(l):
        eco.append(l)
        c2.write(u"reentrada\n")
    c2 = P.CapturaDoConsole(destino)
    c2.write(u"um\n")
    checar(u"o destino que escreve de volta nao entra em laco",
           eco == [u"um"], repr(eco))
    checar(u"e ela se apresenta como texto sem terminal",
           c.isatty() is False and c.flush() is None)
    fonte = ler("app", "radai_watcher.py")
    checar(u"o vigia instala a captura so com o motor sem janela",
           u"_rp.CapturaDoConsole(wlog" in fonte
           and u"if not _rp.motor_oculto():" in fonte)


def teste_o_lancador():
    secao(u"o lancador: motor sem janela, e o painel no ar antes do navegador")
    import radai_lancador as L
    checar(u"a porta sai da URL", L.porta_da_url(u"http://127.0.0.1:8803/") == 8803
           and L.porta_da_url(u"lixo") == L.PORTA_PADRAO)
    amb = L.ambiente_do_motor({u"X": u"1"})
    checar(u"o motor sobe com RADAI_MOTOR_OCULTO=1 e o resto do ambiente",
           amb.get(u"RADAI_MOTOR_OCULTO") == u"1" and amb.get(u"X") == u"1")
    cmd = L.comando_do_motor(u"py.exe")
    checar(u"o comando e o radai_watcher.py ao lado do lancador",
           cmd[0] == u"py.exe"
           and os.path.normcase(cmd[1]) == os.path.normcase(os.path.join(
               os.path.dirname(os.path.abspath(L.__file__)), "radai_watcher.py")))
    checar(u"  ou o motor que o sucessor recebeu",
           L.comando_do_motor(u"py.exe", motor=u"C:\\m\\radai_watcher.py")[1]
           == u"C:\\m\\radai_watcher.py")
    checar(u"o console do motor vai para o temporario local",
           L.arquivo_do_console(8803).startswith(tempfile.gettempdir()))
    import ast as _ast
    fonte_l = ler("app", "radai_lancador.py")
    chamadas = [getattr(n.func, "id", getattr(n.func, "attr", u""))
                for n in _ast.walk(_ast.parse(fonte_l))
                if isinstance(n, _ast.Call)]
    checar(u"a pergunta ao painel local nao passa pelo proxy do Windows",
           u"ProxyHandler" in chamadas and u"urlopen" not in chamadas,
           repr(sorted(set(chamadas))[:12]))

    vistos = []

    class _Proc(object):
        pass

    def popen(c, **kw):
        vistos.append(kw.get("creationflags"))
        if len(vistos) == 1:
            raise OSError("tarefa sem permissao de sair")
        return _Proc()
    con = os.path.join(tempfile.mkdtemp(prefix="radai_fechar_"), u"c.txt")
    L.subir_o_motor([u"py.exe", u"x.py"], con, {}, popen=popen)
    if os.name == "nt":
        checar(u"o motor sobe SEM JANELA (CREATE_NO_WINDOW)",
               all(f & L.CREATE_NO_WINDOW for f in vistos), repr(vistos))
        checar(u"  e, se a tarefa proibe sair dela, tenta sem o breakaway",
               len(vistos) == 2 and not (vistos[1] & L.CREATE_BREAKAWAY_FROM_JOB))

    class _P(object):
        def __init__(self, rcs):
            self.rcs = list(rcs)

        def poll(self):
            return self.rcs.pop(0) if self.rcs else None
    t = [0.0]
    est = L.esperar_o_painel(_P([None, None]), 1, teto_s=10,
                             responde=lambda porta: t[0] >= 1.0,
                             relogio=lambda: t[0],
                             dormir=lambda s: t.__setitem__(0, t[0] + 0.5))
    checar(u"o painel respondeu: no ar", est == (L.NO_AR, 0), repr(est))
    est = L.esperar_o_painel(_P([None, 7]), 1, teto_s=10,
                             responde=lambda porta: False,
                             relogio=lambda: t[0],
                             dormir=lambda s: None)
    checar(u"o motor morreu antes: devolve o codigo dele",
           est == (L.SAIU, 7), repr(est))
    t[0] = 0.0
    est = L.esperar_o_painel(_P([]), 1, teto_s=2,
                             responde=lambda porta: False,
                             relogio=lambda: t[0],
                             dormir=lambda s: t.__setitem__(0, t[0] + 1.0))
    checar(u"o painel demorou: segue (o navegador espera mais)",
           est == (L.DEMOROU, 0), repr(est))

    import socket as _s
    outro = _s.socket()
    outro.bind(("127.0.0.1", 0))
    outro.listen(5)
    try:
        po = outro.getsockname()[1]
        est = L.esperar_o_painel(_P([None, None, 4]), po, teto_s=30,
                                 dormir=lambda s: None)
        checar(u"porta de OUTRO programa: nao confunde com o painel; espera "
               u"o motor sair com o codigo dele", est == (L.SAIU, 4), repr(est))
        est_i = L.esperar_o_painel(_P([None, None, 4]), po, teto_s=30,
                                   responde=L.porta_responde,
                                   dormir=lambda s: None)
        checar(u"  (isca) so «a porta abriu» diria que o painel subiu",
               est_i == (L.NO_AR, 0), repr(est_i))
    finally:
        outro.close()

    pasta = tempfile.mkdtemp(prefix="radai_fechar_")
    con = os.path.join(pasta, u"radai_motor_1.txt")
    with open(con, "wb") as f:
        f.write(b"linha do arranque com a pasta da serie\n")
        f.flush()
        outro = os.path.join(pasta, u"outro.txt")
        io.open(outro, "w").write(u"x")
        checar(u"(isca) o console so e esvaziado se o fd for ele",
               L.limpar_o_console(outro, f.fileno()) is False
               and os.path.getsize(con) > 0)
        checar(u"com o painel no ar, o console do motor e esvaziado",
               L.limpar_o_console(con, f.fileno()) is True
               and os.path.getsize(con) == 0)
        os.write(f.fileno(), b"Fatal Python error\n")
    checar(u"  e o que vier depois (a mensagem fatal) fica do comeco",
           io.open(con, "rb").read() == b"Fatal Python error\n")
    checar(u"a sessao que saiu limpa nao e anormal",
           L.marcar_estado(9, L.ENCERRADO, base=pasta)
           and L.saida_anormal(9, base=pasta) is None)
    L.marcar_estado(9, L.RODANDO, base=pasta)
    checar(u"a que ficou «rodando» e anormal",
           (L.saida_anormal(9, base=pasta) or {}).get(u"estado") == L.RODANDO)
    reg = L.ler_registro(9, base=pasta) or {}
    import radai_pulso as _P
    checar(u"o registro do motor guarda PID, instante de criacao e o Python",
           reg.get(u"pid") == os.getpid()
           and reg.get(u"criado") == _P._criado_em(os.getpid())
           and _norm(reg.get(u"exe", u"")) == _norm(L.python_deste_processo()),
           repr(reg))

    def lancar(**kw):
        ditas = kw.pop("ditas", [])
        base = dict(escrever=ditas.append, travar=lambda porta: True,
                    instancia=lambda porta: (L.LIVRE, None),
                    encerrar=lambda *a: True,
                    abrir=lambda alvo, arquivo=None: True,
                    carregando=lambda porta, url: u"C:\\t\\c.html",
                    informar=lambda *a: True,
                    subir=lambda *a: None, esperar=lambda *a: (L.NO_AR, 0),
                    anterior=lambda porta: None, console=con)
        base.update(kw)
        return L.lancar(u"http://127.0.0.1:%d/" % _porta_livre(), **base)

    ordem = []
    subiu = []
    est = lancar(carregando=lambda porta, url: ordem.append(u"pagina")
                 or u"C:\\t\\c.html",
                 abrir=lambda alvo, arquivo=None: ordem.append(alvo) or True,
                 subir=lambda *a: ordem.append(u"motor") or subiu.append(a))
    checar(u"porta livre: abre a pagina de carregamento e sobe o motor",
           est == (L.NO_AR, 0) and bool(subiu), repr(est))
    checar(u"  a pagina abre ANTES de o motor subir (a tela branca sumiu)",
           ordem[:1] == [u"pagina"] and u"motor" in ordem
           and ordem.index(u"motor") > 1, repr(ordem))
    checar(u"  pelo endereco file:// da pagina", any(
        str(o).startswith(u"file:") for o in ordem), repr(ordem))
    checar(u"  e diz ao motor qual e o arquivo do console",
           subiu and subiu[0][2].get(L.VARIAVEL_CONSOLE) == subiu[0][1],
           repr(subiu)[:200])
    est = lancar(carregando=lambda porta, url: None)
    checar(u"sem a pagina de carregamento (instalacao parcial), o lote abre "
           u"o navegador como antes (codigo 90)",
           est == (L.NO_AR, L.RC_ABRIR_PELO_LOTE), repr(est))
    est = lancar(abrir=lambda alvo, arquivo=None: u"")
    checar(u"  e tambem quando o navegador nao abriu",
           est == (L.NO_AR, L.RC_ABRIR_PELO_LOTE), repr(est))

    abertos, subiu, enc = [], [], []
    est = lancar(instancia=lambda porta: (L.PROCESSANDO, {u"pid": 5}),
                 abrir=lambda alvo, arquivo=None: abertos.append(alvo) or True,
                 subir=lambda *a: subiu.append(a),
                 encerrar=lambda *a: enc.append(a) or True)
    checar(u"outra instancia PROCESSANDO: pergunta no navegador, sem "
           u"encerrar nem subir nada", est == (L.PERGUNTOU, 0) and not subiu
           and not enc, repr(est))
    checar(u"  e a pergunta e a pagina da reabertura da instancia viva",
           len(abertos) == 1 and abertos[0].endswith(L.ROTA_REABRIR)
           and abertos[0].startswith(u"http://127.0.0.1:"), repr(abertos))
    for estado, rot in ((L.PARADA, u"PARADA (responde e nao processa)"),
                        (L.RESTO, u"RESTO (nao responde)"),
                        (L.TRAVADA, u"TRAVADA (porta aberta, sem resposta)")):
        enc, subiu, ditas = [], [], []
        reg = {u"pid": 4242, u"orfaos": []}
        est = lancar(instancia=lambda porta, e=estado, r=reg: (e, r),
                     encerrar=lambda *a: enc.append(a) or True,
                     subir=lambda *a: subiu.append(a), ditas=ditas)
        checar(u"outra instancia %s: encerra e so entao sobe a nova" % rot,
               est == (L.NO_AR, 0) and len(enc) == 1 and enc[0][1] == estado
               and enc[0][2] is reg and bool(subiu), repr((est, enc)))
    subiu = []
    est = lancar(instancia=lambda porta: (L.OUTRO, None),
                 encerrar=lambda *a: enc.append(u"NAO") or True,
                 subir=lambda *a: subiu.append(a))
    checar(u"porta de OUTRO programa: nada e encerrado; o motor sobe e conta "
           u"a porta ocupada", u"NAO" not in enc and bool(subiu), repr(enc))

    abertos, subiu = [], []
    est = lancar(travar=lambda porta: False,
                 abrir=lambda alvo, arquivo=None: abertos.append(alvo) or True,
                 subir=lambda *a: subiu.append(a))
    checar(u"segundo clique com um lancamento em curso: nao derruba nem sobe "
           u"nada, so mostra a pagina de carregamento",
           est == (L.EM_CURSO, 0) and not subiu and len(abertos) == 1,
           repr((est, abertos)))

    esperou, abertos, subiu, enc = [], [], [], []
    est = lancar(sucessor=777,
                 aguardar=lambda pid, porta, e: esperou.append(pid),
                 instancia=lambda porta: (L.PROCESSANDO, {u"pid": 777}),
                 encerrar=lambda *a: enc.append(a) or True,
                 abrir=lambda alvo, arquivo=None: abertos.append(alvo) or True,
                 subir=lambda *a: subiu.append(a))
    checar(u"o sucessor espera o PID antigo sair, encerra o que sobrou sem "
           u"perguntar e sobe o motor, sem abrir navegador",
           est == (L.NO_AR, 0) and esperou == [777] and len(enc) == 1
           and bool(subiu) and not abertos, repr((est, esperou, abertos)))

    ditas, informados = [], []
    est = lancar(anterior=lambda porta: {u"estado": L.RODANDO, u"hora": u"H"},
                 ditas=ditas)
    checar(u"a proxima abertura diz que a sessao anterior nao fechou, e mostra "
           u"o fim do console dela",
           any(u"did not close normally" in m for m in ditas)
           and any(u"Fatal Python error" in m for m in ditas), ditas)
    est = lancar(esperar=lambda *a: (L.SAIU, 3),
                 informar=lambda *a: informados.append(a))
    checar(u"o motor que morre antes do painel: relata e apaga o console",
           est == (L.SAIU, 3) and not os.path.exists(con))
    checar(u"  e avisa a pagina de carregamento (ela para de esperar)",
           informados and informados[0][1:] == (L.SAIU, 3), repr(informados))
    fonte_w = ler("app", "radai_watcher.py")
    checar(u"o vigia esvazia o console quando o painel sobe e marca a saida",
           u"_esvaziar_o_console()" in fonte_w
           and fonte_w.count(u'_marcar_o_motor("encerrado")') == 2
           and u'_marcar_o_motor("rodando")' in fonte_w)
    shutil.rmtree(pasta, ignore_errors=True)


def _norm(c):
    return os.path.normcase(os.path.realpath(os.path.abspath(c or u"x")))


def teste_o_estado_da_outra_instancia():
    secao(u"abrir com outra instancia: o diagnostico e o que se derruba")
    import radai_lancador as L
    reg = {u"pid": 31, u"orfaos": []}

    def estado(responde, pulsos, status, registrada):
        tentativas = []

        def pulso(porta):
            tentativas.append(1)
            return pulsos.pop(0) if pulsos else None
        e = L.estado_da_instancia(1, responde=lambda p: responde,
                                  pulso=pulso, status=lambda p: status,
                                  registrada=lambda p: registrada,
                                  dormir=lambda s: None)
        return e, len(tentativas)
    checar(u"porta fechada e nada registrado: LIVRE",
           estado(False, [], None, None)[0] == (L.LIVRE, None))
    checar(u"porta fechada e o motor registrado vivo: RESTO",
           estado(False, [], None, reg)[0] == (L.RESTO, reg))
    e, n = estado(True, [None, None, None], None, reg)
    checar(u"porta aberta, tres silencios e o motor registrado: TRAVADA",
           e == (L.TRAVADA, reg) and n == 3, repr((e, n)))
    e, n = estado(True, [None, {u"radai": True}], {u"ocupado": None}, reg)
    checar(u"  (isca) um silencio so nao e trava: responde na 2a e esta PARADA",
           e == (L.PARADA, reg) and n == 2, repr((e, n)))
    checar(u"porta aberta sem resposta e sem registro: OUTRO programa",
           estado(True, [], None, None)[0] == (L.OUTRO, None))
    checar(u"responde e algo esta segmentando: PROCESSANDO",
           estado(True, [{u"radai": True}], {u"ocupado": {u"quem": u"vigia"}},
                  None)[0][0] == L.PROCESSANDO)
    checar(u"responde com serie em curso no estado: PROCESSANDO",
           estado(True, [{u"radai": True}], {u"ocupado": None,
                                             u"current": {u"uid": u"x"}},
                  None)[0][0] == L.PROCESSANDO)
    checar(u"responde sem dizer o estado: pergunta (PROCESSANDO)",
           estado(True, [{u"radai": True}], None, None)[0][0] == L.PROCESSANDO)

    base = tempfile.mkdtemp(prefix="radai_fechar_reg_")
    try:
        exe = sys.executable

        def gravar(dados):
            cam = L.arquivo_de_estado(55, base)
            os.makedirs(os.path.dirname(cam), exist_ok=True)
            io.open(cam, "w", encoding="utf-8").write(
                __import__("json").dumps(dados))
        criados = {500: 1000, 600: 1100, 601: 900, 602: 1200}
        imagens = {500: exe, 600: exe, 601: exe, 602: u"C:\\outro\\python.exe"}
        procs = [(600, 500, u"python.exe"), (601, 500, u"python.exe"),
                 (602, 500, u"python.exe"), (700, 500, u"cmd.exe")]

        def achar(**kw):
            return L.instancia_registrada(
                55, base=base, exe=exe, vivo=kw.get("vivo", lambda p: True),
                imagem=lambda p: imagens.get(p, u""),
                criado=lambda p: criados.get(p),
                processos=lambda: kw.get("procs", procs))
        gravar({u"estado": u"rodando", u"pid": 500, u"criado": 1000,
                u"exe": exe})
        r = achar()
        checar(u"o PID gravado, vivo, com o mesmo instante de criacao e o "
               u"Python da pasta instalada: e nosso", (r or {}).get(u"pid") == 500,
               repr(r))
        checar(u"  e os filhos dele que nasceram depois, do mesmo Python, vao "
               u"junto (e so eles)", (r or {}).get(u"orfaos") == [600], repr(r))
        r = achar(vivo=lambda p: False)
        checar(u"o motor morto deixa os filhos orfaos para derrubar",
               (r or {}).get(u"pid") is None and (r or {}).get(u"orfaos") == [600],
               repr(r))
        gravar({u"estado": u"rodando", u"pid": 500, u"criado": 999,
                u"exe": exe})
        checar(u"PID reaproveitado (instante de criacao diferente): nao e "
               u"nosso", achar(procs=[]) is None)
        gravar({u"estado": u"rodando", u"pid": 602, u"criado": 1200,
                u"exe": exe})
        checar(u"o PID gravado com outro Python (outra instalacao): nao e "
               u"nosso", achar(procs=[]) is None)
        gravar({u"estado": u"rodando", u"pid": 500, u"exe": exe})
        checar(u"registro sem o instante de criacao (versao anterior): nada "
               u"se derruba", achar() is None)
        gravar({u"estado": u"rodando", u"pid": os.getpid(), u"criado": 1,
                u"exe": exe})
        checar(u"o proprio lancador nunca e alvo", achar(procs=[]) is None)
    finally:
        shutil.rmtree(base, ignore_errors=True)

    mortos = []
    checar(u"derrubar leva o PID e os orfaos, uma vez cada",
           L.derrubar({u"pid": 5, u"orfaos": [6, 5]},
                      matar=mortos.append) == [5, 6] and mortos == [5, 6])

    passos = []

    def enc(estado, reg, livre=True, sair=True):
        passos[:] = []
        ok = L.encerrar_instancia(
            1, estado, reg, lambda m: passos.append(u"disse"),
            pedir=lambda p: passos.append(u"pedir"),
            derrubar_=lambda r: passos.append(u"derrubar") or [r.get(u"pid")],
            livre=lambda p, t: passos.append(u"livre") or livre,
            sair=lambda p, t: passos.append(u"sair") or sair)
        return ok, list(passos)
    ok, ps = enc(L.PARADA, {u"pid": 9})
    checar(u"PARADA: pede para encerrar, espera a porta e o processo; nada "
           u"e derrubado", ok and ps[0] == u"pedir" and u"derrubar" not in ps,
           repr(ps))
    ok, ps = enc(L.PARADA, {u"pid": 9}, livre=False)
    checar(u"  e se nao fecha no teto, derruba o PID conferido",
           u"derrubar" in ps and ps.index(u"pedir") < ps.index(u"derrubar"),
           repr(ps))
    ok, ps = enc(L.PARADA, None, livre=False)
    checar(u"  sem registro conferido, nao derruba nada (diz que nao fechou)",
           ok is False and u"derrubar" not in ps, repr(ps))
    ok, ps = enc(L.RESTO, {u"pid": 9})
    checar(u"RESTO: derruba sem pedir", u"pedir" not in ps and u"derrubar" in ps,
           repr(ps))

    def atualizar(estado, ok=True):
        feitos = []
        rc = L.encerrar_para_atualizar(
            u"http://127.0.0.1:8803/", lambda m: None,
            instancia=lambda p: (estado, {u"pid": 3}),
            encerrar=lambda *a: feitos.append(a[1]) or ok)
        return rc, feitos
    checar(u"--encerrar (para o atualizador): sem o programa no ar, nada a "
           u"fazer", atualizar(L.LIVRE) == (0, []))
    checar(u"  porta de outro programa: nada e encerrado",
           atualizar(L.OUTRO) == (0, []))
    checar(u"  processando: encerra sem perguntar (o atualizador decidiu)",
           atualizar(L.PROCESSANDO) == (0, [L.PROCESSANDO]))
    checar(u"  e diz quando nao conseguiu (codigo 2)",
           atualizar(L.TRAVADA, ok=False) == (L.RC_NAO_ENCERROU, [L.TRAVADA]))

    import subprocess as _sp
    import radai_pulso as _P
    filho = _sp.Popen([getattr(sys, "_base_executable", None) or sys.executable,
                       u"-c", u"import time; time.sleep(60)"])
    base = tempfile.mkdtemp(prefix="radai_fechar_reg_")
    try:
        time.sleep(0.3)
        cam = L.arquivo_de_estado(56, base)
        os.makedirs(os.path.dirname(cam), exist_ok=True)

        def gravar_real(criado):
            io.open(cam, "w", encoding="utf-8").write(__import__("json").dumps(
                {u"estado": u"rodando", u"pid": filho.pid, u"criado": criado,
                 u"exe": sys.executable}))
        gravar_real(_P._criado_em(filho.pid) + 1)
        checar(u"[processo real] criacao que nao bate: nao e reconhecido",
               L.instancia_registrada(56, base=base) is None)
        L.derrubar(L.instancia_registrada(56, base=base) or {})
        checar(u"  e continua vivo", filho.poll() is None)
        gravar_real(_P._criado_em(filho.pid))
        r = L.instancia_registrada(56, base=base)
        checar(u"[processo real] o PID gravado e conferido e reconhecido",
               (r or {}).get(u"pid") == filho.pid, repr(r))
        checar(u"  e a imagem dele e o Python desta pasta",
               _norm(L.imagem_do_processo(filho.pid))
               == _norm(L.python_deste_processo()))
        L.derrubar(r or {})
        checar(u"  derrubado, ele sai", L.esperar_sair(filho.pid, 10.0)
               and filho.wait(10) is not None)
        checar(u"  e um PID que nao existe conta como saido",
               L.esperar_sair(filho.pid, 0.0))
    finally:
        if filho.poll() is None:
            filho.kill()
        shutil.rmtree(base, ignore_errors=True)


_TRAVA_NO_FILHO = u'''
import sys
sys.path.insert(0, sys.argv[1])
import radai_lancador as L
print("livre" if L.trava_do_lancador(int(sys.argv[2])) else "ocupada")
'''


def _estado_com_status(L, status, fonte=None):
    ns = {}
    if fonte is not None:
        exec(compile(fonte, "isca", "exec"), dict(vars(L)), ns)
    f = ns.get("estado_da_instancia", L.estado_da_instancia)
    return f(1, responde=lambda p: True, pulso=lambda p: {u"radai": True},
             status=lambda p: status, registrada=lambda p: None,
             dormir=lambda s: None)[0]


def _agora_da_reabertura(nav, pagina, status):
    import json as _json
    from urllib.parse import urlsplit as _us
    ctx = nav.new_context(viewport={"width": 1366, "height": 800})

    def atender(route):
        caminho = _us(route.request.url).path
        if caminho == u"/api/reabrir":
            route.fulfill(status=200, content_type=u"text/html; charset=utf-8",
                          body=pagina)
        elif caminho == u"/api/status":
            route.fulfill(status=200, content_type=u"application/json",
                          body=_json.dumps(status))
        else:
            route.fulfill(status=404, body=u"")
    try:
        ctx.route(_BASE_HERMETICA + u"/**", atender)
        pg = ctx.new_page()
        pg.goto(_BASE_HERMETICA + u"/api/reabrir", wait_until="networkidle")
        return pg.inner_text(u"#rr-agora")
    finally:
        ctx.close()


def teste_o_turno_da_noite_conta_como_processando():
    secao(u"o turno da noite aberto ou agendado: a reabertura pergunta")
    import ast
    import inspect
    import radai_lancador as L
    parada = {u"ocupado": None, u"current": None, u"overnight": False,
              u"turno_agendado": False}
    checar(u"vigia ocioso, sem turno: PARADA (encerra sem perguntar)",
           _estado_com_status(L, parada) == L.PARADA)
    aberto = dict(parada, overnight=True)
    agendado = dict(parada, turno_agendado=True)
    checar(u"turno da noite ABERTO com o vigia ocioso: PROCESSANDO (pergunta)",
           _estado_com_status(L, aberto) == L.PROCESSANDO)
    checar(u"turno da noite AGENDADO na fila: PROCESSANDO (pergunta)",
           _estado_com_status(L, agendado) == L.PROCESSANDO)
    checar(u"vigia de antes, sem o campo do agendado: decide pelo resto",
           _estado_com_status(L, {u"ocupado": None}) == L.PARADA)
    fonte = inspect.getsource(L.estado_da_instancia)
    velha = fonte.replace(
        u'\n                       or s.get("overnight") or '
        u's.get("turno_agendado"))', u")")
    checar(u"  (isca) o lancador sem o turno volta a encerrar o turno aberto",
           velha != fonte and _estado_com_status(L, aberto, velha) == L.PARADA
           and _estado_com_status(L, agendado, velha) == L.PARADA)

    import radai_queue as Q
    import radai_queue_state as S
    with S._TRAVA:
        antes = list(S._CARDS)
        del S._CARDS[:]
    try:
        checar(u"fila sem card do turno: nao agendado", not S.turno_agendado())
        with S._TRAVA:
            S._CARDS.append(Q.novo_card(Q.OVERNIGHT, rotulo=u"Turno da noite"))
        checar(u"card do turno esperando a vez: agendado", S.turno_agendado())
        with S._TRAVA:
            S._CARDS[0] = Q.terminar(S._CARDS[0], Q.PRONTO)
        checar(u"  (isca) o card do turno ja aberto e fechado: nao agendado",
               not S.turno_agendado())
    finally:
        with S._TRAVA:
            del S._CARDS[:]
            S._CARDS.extend(antes)

    arv = ast.parse(ler("app", "radai_watcher.py"))
    chaves, chama = set(), False
    for no in ast.walk(arv):
        if isinstance(no, ast.FunctionDef) and no.name == "status":
            for d in ast.walk(no):
                if isinstance(d, ast.Dict):
                    chaves.update(k.value for k in d.keys
                                  if isinstance(k, ast.Constant))
        if isinstance(no, ast.FunctionDef) and no.name == \
                "_turno_agendado_na_fila":
            chama = any(isinstance(d, ast.Attribute)
                        and d.attr == "turno_agendado" for d in ast.walk(no))
    checar(u"o /api/status do vigia diz o turno aberto e o agendado",
           {u"overnight", u"turno_agendado", u"ocupado"} <= chaves,
           repr(sorted(chaves))[:200])
    checar(u"  e o agendado vem da fila da estacao", chama)
    checar(u"  (isca) a busca nao inventa chave",
           u"turno_agendado_isca" not in chaves and len(chaves) > 10)

    exe = _chromium()
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        sync_playwright = None
    if not exe or sync_playwright is None:
        print(u"    PULADO o navegador: sem Playwright ou sem Chromium")
        return
    import radai_shutdown as E
    h = E.pagina_de_reabrir()
    with sync_playwright() as pw:
        nav = pw.chromium.launch(executable_path=exe, headless=True)
        try:
            t = _agora_da_reabertura(nav, h, aberto)
            checar(u"a pergunta diz que o turno esta aberto",
                   FRASE_DO_TURNO_ABERTO in t, t[:160])
            t = _agora_da_reabertura(nav, h, agendado)
            checar(u"a pergunta diz que o turno esta agendado",
                   FRASE_DO_TURNO_AGENDADO in t, t[:160])
            t = _agora_da_reabertura(nav, h, parada)
            checar(u"  (isca) sem turno, diz que nada esta rodando",
                   u"Nenhuma série está sendo contornada" in t
                   and u"turno" not in t, t[:160])
        finally:
            nav.close()


def teste_a_trava_do_lancador():
    secao(u"dois cliques no atalho: o segundo nao derruba o primeiro")
    if os.name != "nt":
        checar(u"(fora do Windows a trava nao se aplica)", True)
        return
    import radai_lancador as L
    import subprocess as _sp
    porta = _porta_livre()
    checar(u"o primeiro lancador pega a trava da porta",
           L.trava_do_lancador(porta) is True)

    def no_filho(p):
        r = _sp.run([sys.executable, u"-c", _TRAVA_NO_FILHO,
                     os.path.dirname(os.path.abspath(L.__file__)), str(p)],
                    capture_output=True, text=True, timeout=60)
        return (r.stdout or u"").strip()
    checar(u"  o segundo, noutro processo, acha a trava ocupada",
           no_filho(porta) == u"ocupada")
    checar(u"  (isca) noutra porta a trava esta livre",
           no_filho(_porta_livre()) == u"livre")


def teste_o_navegador_e_o_sucessor():
    secao(u"o navegador aberto pelo lancador, e o sucessor da reabertura")
    import radai_lancador as L
    import radai_pulso as P
    amb = {u"ProgramFiles(x86)": u"C:\\PF86", u"ProgramFiles": u"C:\\PF",
           u"LOCALAPPDATA": u"C:\\LA", u"TEMP": u"C:\\T"}
    chamadas, padrao = [], []
    exe = L.abrir_navegador(u"file:///C:/T/p.html", arquivo=u"C:\\T\\p.html",
                            ambiente=amb,
                            popen=lambda c, **kw: chamadas.append(c),
                            existe=lambda c: c.endswith(u"msedge.exe"),
                            padrao=padrao.append)
    checar(u"o Edge abre direto, sem .cmd no meio", exe.endswith(u"msedge.exe")
           and chamadas and chamadas[0][0].endswith(u"msedge.exe"), repr(chamadas))
    c = chamadas[0] if chamadas else []
    checar(u"  em modo app, com a pagina e o perfil proprio do programa",
           u"--app=file:///C:/T/p.html" in c
           and (u"--user-data-dir=" + os.path.join(u"C:\\T", u"radai_janela")) in c,
           repr(c))
    checar(u"  o perfil e o mesmo que a vigilancia confere",
           os.path.join(u"C:\\T", P.PASTA_DO_PERFIL)
           == L.perfil_da_janela(amb))
    chamadas[:] = []
    exe = L.abrir_navegador(u"http://x/", ambiente=amb,
                            popen=lambda c, **kw: chamadas.append(c),
                            existe=lambda c: c.endswith(u"chrome.exe"),
                            padrao=padrao.append)
    checar(u"sem Edge (LTSB 2016), o Chrome", exe.endswith(u"chrome.exe"))
    exe = L.abrir_navegador(u"file:///C:/T/p.html", arquivo=u"C:\\T\\p.html",
                            ambiente=amb, popen=lambda c, **kw: None,
                            existe=lambda c: False, padrao=padrao.append)
    checar(u"sem nenhum dos dois, o navegador padrao, com o arquivo",
           exe == u"padrao" and padrao == [u"C:\\T\\p.html"], repr(padrao))
    checar(u"RADAI_NAVEGADOR=0 nao abre nada (bateria)",
           L.abrir_navegador(u"x", ambiente=dict(amb, RADAI_NAVEGADOR=u"0"),
                             popen=lambda c, **kw: 1 / 0) == u"")

    vistos = []

    class _Proc(object):
        pid = 4321
    amb_m = {u"TEMP": u"C:\\R\\tmp", u"TMP": u"C:\\R\\tmp", u"TMPDIR": u"C:\\R",
             L.VARIAVEL_TEMP_DO_USUARIO: u"C:\\U\\Temp",
             L.VARIAVEL_OCULTO: u"1", L.VARIAVEL_CONSOLE: u"C:\\R\\c.txt",
             u"X": u"1"}
    p = L.subir_sucessor(8803, 99, python=u"py.exe",
                         lancador=u"C:\\prog\\radai_lancador.py",
                         motor=u"C:\\prog\\radai_watcher.py", ambiente=amb_m,
                         popen=lambda c, **kw: vistos.append((c, kw)) or _Proc())
    c, kw = vistos[0] if vistos else ([], {})
    checar(u"o sucessor e o lancador desta pasta, com o PID que ele espera "
           u"sair", c[:2] == [u"py.exe", u"C:\\prog\\radai_lancador.py"]
           and c[c.index(u"--sucessor") + 1] == u"99"
           and c[c.index(u"--url") + 1] == u"http://127.0.0.1:8803/"
           and c[c.index(u"--motor") + 1] == u"C:\\prog\\radai_watcher.py",
           repr(c))
    checar(u"  e grava o log ao lado dele", u"--log" in c and c[
        c.index(u"--log") + 1].endswith(L.NOME_DO_LOG), repr(c))
    e = kw.get("env") or {}
    checar(u"  com o TEMP do usuario de volta e sem a marca de motor oculto",
           e.get(u"TEMP") == u"C:\\U\\Temp" and e.get(u"TMP") == u"C:\\U\\Temp"
           and u"TMPDIR" not in e and L.VARIAVEL_OCULTO not in e
           and L.VARIAVEL_CONSOLE not in e and e.get(u"X") == u"1", repr(e))
    if os.name == "nt":
        checar(u"  sem janela", bool(kw.get("creationflags", 0)
                                     & L.CREATE_NO_WINDOW))
    checar(u"  e o motor que esta saindo nao o derruba com os filhos",
           4321 in P.POUPADOS and P.filhos_do_motor(
               1, processos=[(4321, 1, u"python.exe"), (4322, 1, u"python.exe")],
               criado_em=lambda p: 1) == [4322])
    P.POUPADOS.discard(4321)
    import ast as _ast
    fonte = ler("app", "radai_shutdown.py")
    arv = _ast.parse(fonte)
    fim = [n for n in _ast.walk(arv) if isinstance(n, _ast.FunctionDef)
           and n.name == u"_fim"]
    corpo = _ast.get_source_segment(fonte, fim[0]) if fim else u""
    checar(u"a reabertura so lanca o sucessor DEPOIS de o encerramento voltar",
           u"ao_encerrar()" in corpo and u"sucessor(" in corpo
           and corpo.index(u"ao_encerrar()") < corpo.index(u"sucessor("),
           corpo[:200])
    checar(u"  e a thread que o lanca segura o processo ate la (nao daemon)",
           u"daemon=not reabrir" in fonte)


def teste_a_rota_de_reabrir():
    secao(u"a rota do encerrar: reabrir lanca o sucessor, e so quando pedido")
    import radai_shutdown as E
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    for reabrir, rot in ((True, u"com reabrir"), (False, u"sem reabrir")):
        app = FastAPI()
        ordem = []
        pronto = threading.Event()

        def sucessor(porta, o=ordem, ev=pronto):
            o.append((u"sucessor", porta))
            ev.set()

        def encerrar(o=ordem, ev=pronto, r=reabrir):
            o.append(u"encerrou")
            if not r:
                ev.set()
        E.montar(app, encerrar, sucessor=sucessor)
        cli = TestClient(app, base_url=u"http://127.0.0.1:8811")
        corpo = {u"modo": u"tudo"}
        if reabrir:
            corpo[u"reabrir"] = True
        r = cli.post(u"/api/encerrar", json=corpo).json()
        pronto.wait(10)
        time.sleep(0.2)
        if reabrir:
            checar(u"%s: encerra e depois lanca o sucessor na porta do pedido"
                   % rot, ordem == [u"encerrou", (u"sucessor", 8811)]
                   and r.get(u"reabrindo") is True, repr((ordem, r)))
        else:
            checar(u"%s: so encerra" % rot, ordem == [u"encerrou"]
                   and r.get(u"reabrindo") is False, repr((ordem, r)))
        checar(u"  e responde com o PID de quem esta saindo",
               r.get(u"pid") == os.getpid())
    h = E.pagina_de_reabrir()
    checar(u"a pagina da pergunta tem as duas saidas, e o foco no Continuar",
           u'id="rr-continuar"' in h and u'id="rr-reabrir"' in h
           and u"continuar.focus()" in h)
    checar(u"  o Continuar so volta para a sessao aberta",
           u"continuar.addEventListener('click', function(){ "
           u"location.replace('/') });" in h)
    checar(u"  o Encerrar pede a reabertura ao motor",
           u"JSON.stringify({modo:'tudo', reabrir:true})" in h)
    checar(u"  e entra no novo quando o PID muda",
           u"d.pid !== pid0" in h and u"location.replace('/')" in h)
    checar(u"  com o estado do que roda, nas frases que ja tem traducao",
           u"descrever(document.getElementById('rr-agora'))" in h
           and u"'O vigia está contornando uma série agora (desde %s).'" in h)
    checar(u"  e a espera e texto, sem o brilho da casca (que e so de janela "
           u"de imagem)", u"uiCarregando" not in E.PAGINA_REABRIR
           and u"dizer(espera, texto)" in h)
    checar(u"  sem resposta em 5 minutos, so o codigo: nada de mandar abrir "
           u"o radai_lancador.log", u"radai_lancador.log" not in h
           and (u"'%s'" % FRASE_DA_REABERTURA_QUE_NAO_VOLTOU) in h)
    import json as _json
    checar(u"  e os codigos vem de CODIGOS_DA_REABERTURA, um por estado da "
           u"sondagem", (u"var CODIGOS = %s;"
                         % _json.dumps(dict(E.CODIGOS_DA_REABERTURA))) in h
           and sorted(dict(E.CODIGOS_DA_REABERTURA))
           == [u"antigo", u"caiu", u"mudo", u"outro"])
    checar(u"  e nenhum literal fecha o bloco de script antes da hora",
           h.count(u"<script") == h.count(u"<" + u"/script>"),
           u"%d / %d" % (h.count(u"<script"), h.count(u"<" + u"/script>")))


def _pergunta_no_navegador(nav, pagina, botao, pulsos):
    import json as _json
    from urllib.parse import urlsplit as _us
    ctx = nav.new_context(viewport={"width": 1366, "height": 800})
    encerrar = []
    seq = list(pulsos)

    def atender(route):
        caminho = _us(route.request.url).path
        if caminho == u"/api/reabrir":
            route.fulfill(status=200, content_type=u"text/html; charset=utf-8",
                          body=pagina)
        elif caminho == u"/":
            route.fulfill(status=200, content_type=u"text/html; charset=utf-8",
                          body=u"<title>painel</title><p>painel</p>")
        elif caminho == u"/api/status":
            route.fulfill(status=200, content_type=u"application/json",
                          body=_json.dumps({u"ocupado": {u"quem": u"vigia",
                                                         u"desde": u"02:15"}}))
        elif caminho == u"/api/encerrar":
            encerrar.append(route.request.post_data or u"")
            route.fulfill(status=200, content_type=u"application/json",
                          body=_json.dumps({u"ok": True, u"encerrando": True}))
        elif caminho == u"/api/pulso":
            pid = seq.pop(0) if len(seq) > 1 else seq[0]
            if pid is None:
                route.abort()
            else:
                route.fulfill(status=200, content_type=u"application/json",
                              body=_json.dumps({u"radai": True, u"pid": pid}))
        else:
            route.fulfill(status=404, body=u"")
    try:
        ctx.route(_BASE_HERMETICA + u"/**", atender)
        pg = ctx.new_page()
        pg.goto(_BASE_HERMETICA + u"/api/reabrir", wait_until="networkidle")
        agora = pg.inner_text(u"#rr-agora")
        foco = pg.evaluate(u"(document.activeElement||{}).id || ''")
        pg.locator(u"#" + botao).click()
        try:
            pg.wait_for_function(u"document.title === 'painel'", timeout=15000)
        except Exception:
            pass
        return agora, foco, encerrar, pg.evaluate(u"document.title"), \
            pg.evaluate(u"location.pathname")
    finally:
        ctx.close()


def _reabertura_que_nao_volta(nav, pagina, pulsos):
    import json as _json
    from urllib.parse import urlsplit as _us
    ctx = nav.new_context(viewport={"width": 1366, "height": 800})
    seq = list(pulsos)

    def atender(route):
        caminho = _us(route.request.url).path
        if caminho == u"/api/reabrir":
            route.fulfill(status=200, content_type=u"text/html; charset=utf-8",
                          body=pagina)
        elif caminho == u"/api/status":
            route.fulfill(status=200, content_type=u"application/json",
                          body=_json.dumps({u"ocupado": None}))
        elif caminho == u"/api/encerrar":
            route.fulfill(status=200, content_type=u"application/json",
                          body=_json.dumps({u"ok": True, u"encerrando": True}))
        elif caminho == u"/api/pulso":
            r = seq.pop(0) if len(seq) > 1 else seq[0]
            if r is None:
                route.abort()
            else:
                route.fulfill(status=200, content_type=u"application/json",
                              body=_json.dumps(r))
        else:
            route.fulfill(status=404, body=u"")
    try:
        ctx.route(_BASE_HERMETICA + u"/**", atender)
        pg = ctx.new_page()
        pg.goto(_BASE_HERMETICA + u"/api/reabrir", wait_until="networkidle")
        pg.locator(u"#rr-reabrir").click()
        try:
            pg.wait_for_selector(u"#rr-nota:not([hidden])", timeout=15000)
        except Exception:
            pass
        return (pg.inner_text(u"#rr-nota"),
                pg.evaluate(u"!!document.querySelector('.ui-carregando, "
                            u"[aria-busy=\"true\"]')"))
    finally:
        ctx.close()


def teste_a_pergunta_no_navegador():
    secao(u"a pergunta da reabertura, no navegador (hermetico, com isca)")
    exe = _chromium()
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        sync_playwright = None
    if not exe or sync_playwright is None:
        print(u"    PULADO o navegador: sem Playwright ou sem Chromium")
        return
    import radai_shutdown as E
    h = E.pagina_de_reabrir()
    with sync_playwright() as pw:
        nav = pw.chromium.launch(executable_path=exe, headless=True)
        try:
            agora, foco, enc, titulo, onde = _pergunta_no_navegador(
                nav, h, u"rr-continuar", [7])
            checar(u"a pagina diz o que esta rodando agora",
                   u"02:15" in agora and u"contornando" in agora, agora[:160])
            checar(u"  o foco nasce no Continuar (Enter por reflexo nao "
                   u"interrompe a serie)", foco == u"rr-continuar", foco)
            checar(u"Continuar volta para a sessao aberta sem encerrar nada",
                   not enc and titulo == u"painel" and onde == u"/",
                   repr((enc, titulo, onde)))
            agora, foco, enc, titulo, onde = _pergunta_no_navegador(
                nav, h, u"rr-reabrir", [7, 7, 7, None, None, 8])
            checar(u"Encerrar e abrir de novo pede a reabertura ao motor",
                   len(enc) == 1 and u'"reabrir":true' in enc[0].replace(
                       u" ", u""), repr(enc))
            checar(u"  espera o antigo cair e entra no novo (outro PID)",
                   titulo == u"painel" and onde == u"/", repr((titulo, onde)))
            agora, foco, enc, titulo, onde = _pergunta_no_navegador(
                nav, h, u"rr-reabrir", [7])
            checar(u"  (isca) com o mesmo PID respondendo, nao entra",
                   titulo != u"painel", repr((titulo, onde)))
            curta = h.replace(u"agora() + %d;" % E.TETO_DA_REABERTURA_MS,
                              u"agora() + 1200;")
            checar(u"  (o teto da espera se encurta para a prova)", curta != h)
            cod = dict(E.CODIGOS_DA_REABERTURA)
            for pulsos, estado, rot in (
                    ([{u"radai": True, u"pid": 7}], u"antigo",
                     u"o antigo continua respondendo"),
                    ([{u"radai": True, u"pid": 7}, None], u"caiu",
                     u"a porta caiu e o novo nao subiu"),
                    ([{u"radai": True, u"pid": 7}, {u"outro": 1}], u"outro",
                     u"outro programa responde na porta")):
                nota, brilho = _reabertura_que_nao_volta(nav, curta, pulsos)
                checar(u"sem volta (%s): a nota diz so o codigo %s"
                       % (rot, cod[estado]),
                       (u"(código %s)" % cod[estado]) in nota
                       and u"radai_lancador" not in nota, nota[:160])
                checar(u"  e a espera nao ganha o brilho da casca", not brilho)
        finally:
            nav.close()


def teste_a_pagina_de_carregamento():
    secao(u"a tela branca do arranque: a pagina local de carregamento")
    import radai_carregando as C
    pasta = tempfile.mkdtemp(prefix="radai_fechar_carr_")
    porta = _porta_livre()
    try:
        cam = C.gravar(porta, u"http://127.0.0.1:%d/" % porta, pasta=pasta,
                       pasta_do_programa=APP,
                       tradutor=lambda: ((lambda f: f), u"pt-BR"))
        h = io.open(cam, encoding="utf-8").read()
        checar(u"a pagina e um arquivo local, com o nome da porta",
               os.path.basename(cam) == C.NOME_DA_PAGINA % porta)
        checar(u"  com a marca (o desenho do icone) e o nome curto, Local Suite",
               u"<svg" in h
               and (u'<h1 class="cg-nome">%s</h1>' % C.NOME_NA_TELA) in h
               and C.NOME_NA_TELA == u"Local Suite")
        checar(u"  e so «carregando…» embaixo do nome, sem a dica de minutos",
               (u">%s<" % C.FRASES["abrindo"]) in h
               and C.FRASES["abrindo"] == u"carregando…"
               and u"alguns minutos" not in h and u"cg-dica" not in h)
        checar(u"  com o carregamento organico e o brilho, e sem animacao para "
               u"quem pede movimento reduzido",
               u"@keyframes cgA" in h and u"cgBrilho" in h
               and u"prefers-reduced-motion:reduce" in h)
        checar(u"  confere a porta a cada meio segundo, por imagem (file:// "
               u"nao le JSON de outra origem)",
               u"setInterval(sondar, 500)" in h and u"new Image()" in h
               and (u"'%s'" % C.ROTA_SINAL) in h)
        checar(u"  e entra no app sem deixar a pagina local no historico",
               u"location.replace(BASE + '/')" in h)
        checar(u"  nenhum CSS ou script de fora (sem servidor nem internet)",
               u"<link" not in h and u'src="http' not in h)
        est = io.open(C.caminho_do_estado(porta, pasta), encoding="utf-8").read()
        checar(u"o estado da abertura anterior e trocado antes de abrir",
               u'"subindo"' in est)
        exe = _chromium()
        try:
            from playwright.sync_api import sync_playwright
        except Exception:
            sync_playwright = None
        if not exe or sync_playwright is None:
            print(u"    PULADO o navegador: sem Playwright ou sem Chromium")
            return
        import http.server as _hs
        import pathlib as _pl

        class _H(_hs.BaseHTTPRequestHandler):
            imagem = True

            def do_GET(self):
                if self.path.startswith(C.ROTA_SINAL) and self.imagem:
                    import radai_pulso as _P
                    self.send_response(200)
                    self.send_header(u"Content-Type", u"image/gif")
                    self.end_headers()
                    self.wfile.write(_P.GIF_DO_SINAL)
                    return
                self.send_response(200)
                self.send_header(u"Content-Type", u"text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"<title>painel</title><p>o painel</p>")

            def log_message(self, *a):
                pass

        class _Outro(_H):
            imagem = False
        with sync_playwright() as pw:
            nav = pw.chromium.launch(executable_path=exe, headless=True)
            try:
                pg = nav.new_page()
                pg.goto(_pl.Path(cam).as_uri())
                pg.wait_for_timeout(1500)
                checar(u"[navegador] sem motor, a pagina espera dizendo "
                       u"«carregando…»",
                       pg.inner_text(u"#cg-st").strip() == u"carregando…"
                       and pg.url.startswith(u"file:"), pg.url)
                srv = _hs.ThreadingHTTPServer((u"127.0.0.1", porta), _Outro)
                threading.Thread(target=srv.serve_forever, daemon=True).start()
                pg.wait_for_timeout(2500)
                checar(u"[navegador] (isca) outro programa na porta, que nao "
                       u"serve a imagem: a pagina NAO entra",
                       pg.url.startswith(u"file:"), pg.url)
                srv.shutdown()
                srv.server_close()
                srv = _hs.ThreadingHTTPServer((u"127.0.0.1", porta), _H)
                threading.Thread(target=srv.serve_forever, daemon=True).start()
                try:
                    pg.wait_for_function(u"document.title === 'painel'",
                                         timeout=8000)
                except Exception:
                    pass
                checar(u"[navegador] o painel no ar: a pagina entra nele",
                       pg.evaluate(u"document.title") == u"painel"
                       and pg.evaluate(u"location.href").startswith(
                           u"http://127.0.0.1:%d/" % porta),
                       pg.evaluate(u"location.href"))
                srv.shutdown()
                srv.server_close()
                pg2 = nav.new_page()
                C.gravar(porta, None, pasta=pasta, pasta_do_programa=APP,
                         tradutor=lambda: ((lambda f: f), u"pt-BR"))
                pg2.goto(_pl.Path(cam).as_uri())
                pg2.wait_for_timeout(600)
                C.gravar_estado(porta, u"saiu", 4, pasta)
                try:
                    pg2.wait_for_function(
                        u"document.documentElement.className.indexOf('parou') >= 0",
                        timeout=5000)
                except Exception:
                    pass
                txt = pg2.inner_text(u"body")
                checar(u"[navegador] o motor morreu no arranque: a pagina para "
                       u"de esperar e diz so o codigo do erro",
                       u"código 4" in txt and u"radai_lancador.log" not in txt
                       and u"motivo" not in txt, txt[:200])
            finally:
                nav.close()
    finally:
        shutil.rmtree(pasta, ignore_errors=True)


def teste_os_lotes():
    secao(u"os .cmd do ciclo: CRLF, ASCII, sem chcp, pause e log nos erros")
    for rel in (u"app/launchers/start_watcher.cmd",
                u"app/RADIOTERAPIA_AI_LOCAL_SUITE.cmd",
                u"app/launchers/open_browser.cmd"):
        b = io.open(_componentes.fonte(rel), "rb").read()
        sem_crlf = b.replace(b"\r\n", b"")
        checar(u"%s: CRLF em toda linha" % rel,
               b"\n" not in sem_crlf and b"\r" not in sem_crlf)
        checar(u"  ASCII puro", all(c < 128 for c in bytearray(b)))
        checar(u"  sem chcp", b"chcp" not in b.lower())
        linhas = b.decode("ascii", "replace").split(u"\r\n")
        sem_pausa = [i for i, l in enumerate(linhas)
                     if l.strip().lower().startswith(u"exit /b 1")
                     and not any(u"pause" in x.lower()
                                 for x in linhas[max(0, i - 3):i])]
        checar(u"  todo caminho de erro para com pause antes de sair",
               not sem_pausa, repr(sem_pausa))
    sw = ler("app", "launchers", "start_watcher.cmd")
    checar(u"start_watcher: o lancador escreve o log em arquivo",
           u'set "LOGF=%PROG%radai_lancador.log"' in sw
           and u'--url %URL% --log "%LOGF%"' in sw)
    checar(u"  e os erros do proprio lote tambem vao para o log",
           sw.count(u'>>"%LOGF%" echo') >= 2)
    checar(u"  o navegador nao abre por `start` de outro .cmd",
           u'start "" "%JANELA%"' not in sw and u'start "" /min "%JANELA%"' not in sw)
    checar(u"  e o codigo 90 (sem pagina de carregamento) cai no navegador "
           u"de antes", u'if "%RC%"=="90" goto :navegador' in sw
           and u':navegador\r\ncall "%JANELA%" %URL%' in io.open(
               _componentes.fonte(u"app/launchers/start_watcher.cmd"), "rb"
           ).read().decode("ascii"))
    raiz = ler("app", "RADIOTERAPIA_AI_LOCAL_SUITE.cmd")
    checar(u"RADIOTERAPIA_AI_LOCAL_SUITE: a instalacao incompleta vai para o log",
           u'>>"%~dp0radai_lancador.log" echo' in raiz)


def _pid_do_motor(porta):
    import json as _json
    try:
        return _json.loads(_pedir(porta, "/api/pulso")).get("pid")
    except Exception:
        return None


def _encerrar_e_esperar(porta, teto=40):
    try:
        _pedir(porta, "/api/encerrar", '{"modo":"tudo"}')
    except Exception:
        pass
    fim = time.time() + teto
    while time.time() < fim:
        if _pid_do_motor(porta) is None:
            return True
        time.sleep(0.5)
    return False


def teste_fechar_pelo_x_no_navegador():
    secao(u"fechar pelo X, no navegador de verdade: o motor sai em segundos")
    exe = _chromium()
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        sync_playwright = None
    if not exe or sync_playwright is None:
        print(u"    PULADO o navegador: sem Playwright ou sem Chromium")
        return
    trab = tempfile.mkdtemp(prefix="radai_fechar_")
    porta = _porta_livre()
    p, saida = _motor_oculto(trab, porta, 300, extra={"RADAI_PULSO_GRACA_S": "4"})
    try:
        estado = _esperar_no_ar(p, porta)
        checar(u"o motor sem janela sobe com a graca do fechar de 4 s",
               bool(estado) and estado.get("graca_s") == 4.0, repr(estado))
        if not estado:
            return
        base = u"http://127.0.0.1:%d" % porta
        sem_relogio = u"window.setInterval = function(){ return 0 };"
        sem_canal = sem_relogio + u" window.BroadcastChannel = undefined;"
        with sync_playwright() as pw:
            nav = pw.chromium.launch(executable_path=exe, headless=True)
            try:
                ctx = nav.new_context()
                a = ctx.new_page()
                a.goto(base + u"/", wait_until="domcontentloaded")
                b = ctx.new_page()
                b.add_init_script(sem_relogio)
                b.goto(base + u"/", wait_until="domcontentloaded")
                time.sleep(4.0)
                d0 = _jload(_pedir(porta, "/api/pulso"))
                avisos0 = d0.get("avisos_de_saida", 0)
                checar(u"  (isca) antes de fechar, a saida ja nao esta "
                       u"pendente: a espera que olhasse so esse campo "
                       u"passaria sem o aviso, por isso ela espera o "
                       u"contador de avisos subir",
                       d0.get("saida_pendente") is False, repr(d0))
                a.close()
                d = _esperar_o_pulso(porta, lambda e: e.get(
                    "avisos_de_saida", 0) > avisos0 and e.get(
                    "saida_pendente") is False)
                checar(u"uma aba fecha: o aviso dela chega ao motor",
                       d.get("avisos_de_saida", 0) > avisos0, repr(d))
                checar(u"  e a irma (sem relogio, so com o canal) acorda e "
                       u"responde na hora", d.get("saida_pendente") is False,
                       repr(d))
                ctx2 = nav.new_context()
                c = ctx2.new_page()
                c.add_init_script(sem_canal)
                c.goto(base + u"/", wait_until="domcontentloaded")
                x = ctx2.new_page()
                x.goto(base + u"/", wait_until="domcontentloaded")
                import radai_pulso as _P
                calmo = _esperar_o_pulso(porta, lambda e: float(e.get(
                    "silencio_s") or 0) > _P.JANELA_DE_CORRIDA_S + 0.5,
                    teto_s=20.0)
                checar(u"  antes de fechar a aba, nenhuma pulsou na janela "
                       u"de corrida (a irma que pulsou nela conta como viva)",
                       float(calmo.get("silencio_s") or 0)
                       > _P.JANELA_DE_CORRIDA_S, repr(calmo))
                avisos1 = calmo.get("avisos_de_saida", 0)
                x.close()
                d = _esperar_o_pulso(porta, lambda e: e.get(
                    "avisos_de_saida", 0) > avisos1 and e.get(
                    "saida_pendente") is True)
                checar(u"  (isca) a irma sem o canal nao responde: a saida "
                       u"fica pendente", d.get("saida_pendente") is True,
                       repr(d))
                c.reload(wait_until="domcontentloaded")
                d = _esperar_o_pulso(porta, lambda e: e.get(
                    "saida_pendente") is False)
                checar(u"  e qualquer pagina que pulsa a cancela",
                       d.get("saida_pendente") is False, repr(d))
                time.sleep(5.0)
                checar(u"  passada a graca, o motor continua vivo",
                       p.poll() is None)
                b.goto(base + u"/config", wait_until="domcontentloaded")
                time.sleep(6.0)
                checar(u"navegar entre paginas tambem avisa, e a pagina nova "
                       u"cancela: o motor continua vivo", p.poll() is None)
                t0 = time.time()
                c.close()
                b.close()
                for _ in range(60):
                    if p.poll() is not None:
                        break
                    time.sleep(0.25)
                dt = time.time() - t0
                checar(u"a ultima aba fecha: o motor sai sozinho em segundos "
                       u"(%.1f s, graca de 4)" % dt,
                       p.poll() is not None and dt < 12.0, u"%.1f s" % dt)
                checar(u"  e sai limpo (codigo 0)", p.returncode == 0,
                       str(p.returncode))
                ctx2.close()
                ctx.close()
            finally:
                nav.close()
        log = u""
        try:
            log = io.open(os.path.join(trab, "radai_vigia.log"),
                          encoding="utf-8", errors="replace").read()
        except Exception:
            pass
        checar(u"  e o log diz que a ultima aba fechou",
               u"ultima aba do programa foi fechada" in log, log[-300:])
    finally:
        if p.poll() is None:
            p.kill()
        shutil.rmtree(trab, ignore_errors=True)


def _jload(t):
    import json as _json
    try:
        return _json.loads(t)
    except Exception:
        return {}


def _esperar_o_pulso(porta, condicao, teto_s=10.0, pausa_s=0.1):
    fim = time.time() + teto_s
    d = {}
    while True:
        try:
            d = _jload(_pedir(porta, "/api/pulso"))
        except Exception:
            pass
        if condicao(d) or time.time() >= fim:
            return d
        time.sleep(pausa_s)


def teste_a_espera_do_aviso_consulta_ate_o_teto():
    secao(u"a espera do aviso de saida consulta o motor ate um teto")
    import json as _json
    global _pedir
    real = _pedir
    inicio = [time.time()]

    def motor_lento(porta, caminho, dados=None):
        chegou = time.time() - inicio[0] >= 1.5
        return _json.dumps({"avisos_de_saida": 1 if chegou else 0,
                            "saida_pendente": False})
    _pedir = motor_lento
    try:
        inicio[0] = time.time()
        d = _esperar_o_pulso(0, lambda e: e.get("avisos_de_saida", 0) > 0)
        checar(u"o aviso que chega 1,5 s depois (motor sob carga) e esperado",
               d.get("avisos_de_saida") == 1, repr(d))
        inicio[0] = time.time()
        time.sleep(1.0)
        fixo = _jload(_pedir(0, "/api/pulso"))
        checar(u"  (isca) a pausa fixa de 1 s le o motor antes do aviso, e a "
               u"checagem reprovaria", fixo.get("avisos_de_saida") == 0,
               repr(fixo))
        t0 = time.time()
        _esperar_o_pulso(0, lambda e: False, teto_s=0.5)
        dt = time.time() - t0
        checar(u"  e o aviso que nunca chega para a espera no teto",
               0.5 <= dt < 5.0, u"%.2f s" % dt)
    finally:
        _pedir = real


def teste_a_reabertura_de_verdade():
    secao(u"encerrar e abrir de novo: o motor sai e o sucessor sobe outro")
    trab = tempfile.mkdtemp(prefix="radai_fechar_")
    porta = _porta_livre()
    log_l = os.path.join(trab, "radai_lancador.log")
    p, saida = _motor_oculto(trab, porta, 300,
                             extra={"RADAI_LOG_DO_LANCADOR": log_l})
    novo = None
    try:
        estado = _esperar_no_ar(p, porta)
        checar(u"o motor sobe", bool(estado), repr(estado))
        if not estado:
            return
        antigo = estado.get("pid")
        r = _jload(_pedir(porta, "/api/encerrar",
                          '{"modo":"tudo","reabrir":true}'))
        checar(u"o pedido de reabrir e aceito", r.get("reabrindo") is True
               and r.get("pid") == antigo, repr(r))
        caiu = False
        fim = time.time() + 120
        while time.time() < fim:
            pid = _pid_do_motor(porta)
            if pid is None:
                caiu = True
            elif pid != antigo:
                novo = pid
                break
            time.sleep(0.5)
        checar(u"o motor antigo saiu", caiu and p.poll() is not None)
        checar(u"  e outro subiu sozinho na mesma porta, com outro PID",
               bool(novo) and novo != antigo, u"novo=%s antigo=%s"
               % (novo, antigo))
        texto = u""
        for _ in range(40):
            try:
                texto = io.open(log_l, encoding="utf-8",
                                errors="replace").read()
            except Exception:
                pass
            if u"Panel is up" in texto:
                break
            time.sleep(0.5)
        checar(u"  o sucessor escreveu no log do lancador o que fez",
               u"Reopening the program after the previous session" in texto
               and u"Panel is up" in texto, texto[-400:])
        if novo:
            checar(u"o novo encerra pelo Fechar tudo, como qualquer outro",
                   _encerrar_e_esperar(porta))
    finally:
        if p.poll() is None:
            p.kill()
        if _pid_do_motor(porta):
            pid = _pid_do_motor(porta)
            import subprocess as _sp
            _sp.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                    capture_output=True)
        time.sleep(0.5)
        shutil.rmtree(trab, ignore_errors=True)


def _porta_livre():
    import socket as _s
    s = _s.socket()
    s.bind(("127.0.0.1", 0))
    porta = s.getsockname()[1]
    s.close()
    return porta


def _motor_oculto(trab, porta, tolerancia, extra=None):
    cfg = os.path.join(trab, "teste.config")
    io.open(cfg, "w", encoding="utf-8").write(
        u"\n".join([u"ROOT=", u"TPS_DESTINO=eclipse", u"PORT=%d" % porta, u"DRY_RUN=1", u""]))
    env = dict(os.environ)
    env.update({"RADAI_CONFIG": cfg, "RADAI_CALIB_DIR": trab,
                "PYTHONIOENCODING": "utf-8:replace",
                "RADAI_URL_VERSOES": "0", "RADAI_NOTIFICACAO": "0",
                "RADAI_MOTOR_OCULTO": "1",
                "RADAI_PULSO_S": str(tolerancia)})
    env.update(extra or {})
    env["LOCALAPPDATA"] = os.path.join(trab, "ad")
    env["RADAI_REGISTRO_DIR"] = os.path.join(trab, "registro")
    env["TEMP"] = env["TMP"] = trab
    import json as _json
    import radai_consent as _CS
    io.open(os.path.join(trab, _CS.ARQUIVO_ACEITE), "w",
            encoding="utf-8").write(_json.dumps(
                _CS.montar_registro(u"bateria", [k for k, _t, _d in _CS.PONTOS]),
                ensure_ascii=False))
    p = subprocess.Popen([sys.executable, _componentes.fonte("app/radai_watcher.py")],
                         cwd=APP, env=env, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True,
                         encoding="utf-8", errors="replace")
    saida = []

    def drenar():
        try:
            for l in p.stdout:
                saida.append(l)
        except Exception:
            pass
    threading.Thread(target=drenar, daemon=True).start()
    return p, saida


def _pedir(porta, caminho, dados=None):
    req = urllib.request.Request(
        "http://127.0.0.1:%d%s" % (porta, caminho),
        data=(dados.encode("utf-8") if dados is not None else None),
        headers={"Content-Type": "application/json",
                 "Origin": "http://127.0.0.1:%d" % porta},
        method="POST" if dados is not None else "GET")
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.read().decode("utf-8", "replace")


def _esperar_no_ar(p, porta, teto=60):
    import json as _json
    for _ in range(int(teto * 2)):
        time.sleep(0.5)
        if p.poll() is not None:
            return None
        try:
            return _json.loads(_pedir(porta, "/api/pulso"))
        except Exception:
            pass
    return None


def teste_motor_oculto_vivo():
    secao(u"o motor sem janela: pulsa, cala o console, e encerra sozinho")
    trab = tempfile.mkdtemp(prefix="radai_fechar_")
    porta = _porta_livre()
    p, saida = _motor_oculto(trab, porta, 8)
    try:
        estado = _esperar_no_ar(p, porta)
        checar(u"o motor sem janela sobe e responde ao pulso",
               bool(estado) and estado.get("radai") is True, repr(estado))
        if not estado:
            return
        checar(u"  armado com a tolerancia do ambiente (8 s)",
               estado.get("armado") is True
               and estado.get("tolerancia_s") == 8.0, repr(estado))
        import radai_lancador as _la0
        checar(u"  e marca a sessao como «rodando» enquanto vive",
               (_la0.saida_anormal(porta, base=os.path.join(trab, "ad"))
                or {}).get(u"estado") == u"rodando")
        home = _pedir(porta, "/")
        checar(u"a porta da suite sai com o script do pulso",
               u"radai-pulso-js" in home)
        for _ in range(7):
            _pedir(porta, "/api/pulso", "{}")
            time.sleep(2.0)
        checar(u"com pulso a cada 2 s ele continua vivo depois de 14 s "
               u"(a tolerancia e 8)", p.poll() is None)
        for _ in range(80):
            time.sleep(0.5)
            if p.poll() is not None:
                break
        checar(u"sem pulso ele se encerra sozinho", p.poll() is not None)
        checar(u"  e sai limpo (codigo 0)", p.returncode == 0, str(p.returncode))
        import radai_lancador as _la
        marca = _la.arquivo_de_estado(porta, base=os.path.join(trab, "ad"))
        checar(u"  e marca a saida limpa (a proxima abertura nao acusa)",
               _la.saida_anormal(porta, base=os.path.join(trab, "ad")) is None
               and os.path.isfile(marca), marca)
        log = u""
        try:
            log = io.open(os.path.join(trab, "radai_vigia.log"),
                          encoding="utf-8", errors="replace").read()
        except Exception:
            pass
        checar(u"o log diz por que encerrou",
               u"navegador foi fechado" in log, log[-300:])
        console = u"".join(saida)
        checar(u"o console mostra o arranque (o lancador relata a falha dele)",
               u"motor sem janela" in console, console[-300:])
        checar(u"  e se cala depois do painel no ar (o log fica na tela)",
               u"navegador foi fechado" not in console, console[-300:])
        import radai_cleaner as _rc
        em_uso = os.path.join(trab, "ad", "RADIOTERAPIA_AI", _rc.NOME_EM_USO)
        checar(u"o em_uso.json saiu com ele", not os.path.exists(em_uso), em_uso)
    finally:
        if p.poll() is None:
            p.kill()

    trab2 = tempfile.mkdtemp(prefix="radai_fechar_")
    porta2 = _porta_livre()
    p2, _s2 = _motor_oculto(trab2, porta2, 0)
    try:
        estado = _esperar_no_ar(p2, porta2)
        checar(u"(isca) com RADAI_PULSO_S=0 o pulso fica desarmado",
               bool(estado) and estado.get("armado") is False, repr(estado))
        time.sleep(14.0)
        checar(u"  (isca) e o mesmo silencio NAO o encerra", p2.poll() is None)
        try:
            _pedir(porta2, "/api/encerrar", '{"modo":"tudo"}')
        except Exception:
            pass
        for _ in range(80):
            time.sleep(0.5)
            if p2.poll() is not None:
                break
        checar(u"  e o «Fechar tudo» continua encerrando", p2.poll() is not None)
    finally:
        if p2.poll() is None:
            p2.kill()


def teste_o_perfil_da_janela_depois_do_temp_reapontado():
    secao(u"VIG-03: o perfil da janela com o TEMP reapontado")
    import radai_archive as A
    import radai_pulso as P
    usuario = tempfile.mkdtemp(prefix=u"radai_fechar_usr_")
    outra = tempfile.mkdtemp(prefix=u"radai_fechar_tmp_")
    perfil = os.path.join(usuario, P.PASTA_DO_PERFIL)
    os.makedirs(perfil)
    io.open(os.path.join(perfil, P.TRAVA_DO_CHROMIUM), "w").close()
    chaves = ("TEMP", "TMP", "TMPDIR", P.VARIAVEL_TEMP_DO_USUARIO)
    antes = dict((k, os.environ.get(k)) for k in chaves)
    try:
        for k in ("TEMP", "TMP", "TMPDIR"):
            os.environ[k] = usuario
        os.environ.pop(P.VARIAVEL_TEMP_DO_USUARIO, None)
        A._marcar_ambiente(outra)
        checar(u"o TEMP do processo foi reapontado",
               os.environ.get("TEMP") == outra)
        checar(u"o perfil continua o do %TEMP% do usuario",
               P.perfil_da_janela() == perfil, P.perfil_da_janela())
        checar(u"  e o navegador aberto e visto",
               P.navegador_do_programa_aberto() is True)
        A._marcar_ambiente(os.path.join(outra, u"x"))
        checar(u"uma segunda marcacao nao troca o TEMP do usuario",
               P.perfil_da_janela() == perfil)
        isca = P.perfil_da_janela({u"TEMP": os.environ.get("TEMP")})
        checar(u"ISCA: pelo TEMP de depois, o perfil nao existe",
               P.navegador_do_programa_aberto(isca) is None)
    finally:
        for k, v in antes.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        tempfile.tempdir = None
        shutil.rmtree(usuario, ignore_errors=True)
        shutil.rmtree(outra, ignore_errors=True)

    agora = [1000.0]
    enc, lin = [], []
    oc = [True]
    v = P.Vigilancia(P.Pulso(5.0, relogio=lambda: agora[0]),
                     lambda: enc.append(1), lambda: oc[0], log=lin.append,
                     acordado=lambda s: True, navegador_aberto=lambda: None)
    agora[0] += 600.0
    v.passo()
    v.passo()
    checar(u"sem perfil e com a fila rodando: nada encerra", enc == [],
           repr(enc))
    checar(u"  e o log diz uma vez so", sum(
        1 for l in lin if u"perfil da janela" in l) == 1, repr(lin))
    oc[0] = False
    v.passo()
    checar(u"  a fila vazia, encerra como antes", enc == [1], repr(enc))


def lado_fisico(css):
    import re
    rx = re.compile(r"border-left|border-right|text-align:\s*(?:left|right)"
                    r"|margin-left|margin-right|padding-left|padding-right")
    return sorted(set(rx.findall(css or u"")))


def teste_os_dialogos_sao_rtl():
    secao(u"TEL-16: o Fechar, o primeiro uso e a conferência usam o lado lógico")
    import radai_shutdown as SD
    import radai_primeiro_uso as PU
    import radai_review as RV
    for nome, css in ((u"radai_shutdown", SD.CSS), (u"radai_primeiro_uso", PU.CSS),
                      (u"radai_review", RV.CSS_DA_FRONTEIRA)):
        checar(u"%s sem border-left/text-align:left e afins" % nome,
               not lado_fisico(css), repr(lado_fisico(css)))
    checar(u"  (isca) a regra velha do Fechar e acusada",
           lado_fisico(u".rx-agora{border-left:3px solid red}") == [u"border-left"])


def main():
    print(u"\n" + u"=" * 70)
    print(u"  FECHAR O APP — o botao, o X, a reabertura e o arranque")
    print(u"=" * 70)
    for t in (teste_os_dialogos_sao_rtl,
              teste_costura, teste_tres_saidas, teste_a_porta_tem_o_fechar,
              teste_o_botao_abre_o_dialogo, teste_a_despedida_diz_a_verdade,
              teste_a_despedida_no_navegador, teste_o_estado_tem_chave,
              teste_o_estado_em_alemao_e_o_tab_preso, teste_lock,
              teste_a_saida_tem_teto, teste_vivo,
              teste_o_fechar_espera_a_porta_cair,
              teste_pulso_e_vigilancia, teste_o_pulso_vai_em_toda_tela,
              teste_o_aviso_de_saida,
              teste_a_captura_do_console, teste_o_lancador,
              teste_o_estado_da_outra_instancia,
              teste_o_turno_da_noite_conta_como_processando,
              teste_a_trava_do_lancador,
              teste_o_navegador_e_o_sucessor, teste_a_rota_de_reabrir,
              teste_a_pergunta_no_navegador,
              teste_a_pagina_de_carregamento, teste_os_lotes,
              teste_motor_oculto_vivo,
              teste_a_espera_do_aviso_consulta_ate_o_teto,
              teste_fechar_pelo_x_no_navegador,
              teste_a_reabertura_de_verdade,
              teste_o_perfil_da_janela_depois_do_temp_reapontado):
        try:
            t()
        except Exception as e:
            import traceback
            checar(u"%s (excecao inesperada)" % t.__name__, False,
                   u"%s: %s" % (type(e).__name__, e))
            traceback.print_exc()
    print(u"\n" + u"=" * 70)
    if _falhas:
        print(u"FALHOU: %d de %d checagens" % (len(_falhas), _ok + len(_falhas)))
        for f in _falhas:
            print(u"    - %s" % f)
        print(u"=" * 70)
        return 1
    print(u"OK: %d checagens, todas passaram" % _ok)
    print(u"=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
