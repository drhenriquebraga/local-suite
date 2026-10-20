# -*- coding: utf-8 -*-
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, ".."))
APP = os.path.join(RAIZ, "app")
sys.path.insert(0, APP)

import radai_cover as C

import _componentes
OK = 0
FALHAS = 0
VERBOSO = "-v" in sys.argv


def checar(nome, ok, detalhe=""):
    global OK, FALHAS
    if ok:
        OK += 1
    else:
        FALHAS += 1
    if VERBOSO or not ok:
        print("  %-6s %s%s" % ("OK" if ok else "FALHA", nome,
                               ("  [%s]" % detalhe) if detalhe else ""))


def secao(t):
    if VERBOSO:
        print("\n-- %s %s" % (t, "-" * max(0, 58 - len(t))))


def ler(rel):
    p = _componentes.fonte(rel)
    return io.open(p, encoding="utf-8", errors="replace").read() if os.path.isfile(p) else ""


def teste_capa_monta():
    secao("capa: chip, titulo em dois tons, frase, divisoria")
    h = C.capa(u"Módulo", u"Oncologia", u"Torácica", u"Uma frase.", icone=u"◈")
    checar("tem o chip", u'class="rc-chip"' in h)
    checar("tem o título", u"<h1>Oncologia" in h)
    checar("com o destaque na cor de acento", u"<span>Torácica</span>" in h)
    checar("tem a frase", u'class="rc-frase">Uma frase.' in h)
    checar("e a divisória", u'class="rc-risca"' in h)

    c = C.capa(u"Estação", u"Vigia", u"", u"máquina X", compacta=True)
    checar("compacta marca a classe", u"rc-compacta" in c)
    checar("e não leva divisória", u"rc-risca" not in c)
    checar("mas mantém a frase", u"máquina X" in c)


def teste_capa_escapa():
    secao("capa: texto com < e & nao vira marcacao")
    h = C.capa(u"a<b>", u"x&y", u'"z"', u"<script>alert(1)</script>")
    checar("escapa o chip", u"a&lt;b&gt;" in h)
    checar("escapa o título", u"x&amp;y" in h)
    checar("escapa a frase", u"&lt;script&gt;" in h and u"<script>" not in h)


def teste_cartao():
    secao("cartao: objetivo, e so vira link se levar a algum lugar")
    a = C.cartao(u"Título", u"Duas linhas.", href=u"/lote", icone=u"▶")
    checar("com href vira <a>", a.startswith(u"<a ") and u'href="/lote"' in a)
    d = C.cartao(u"Título", u"Duas linhas.")
    checar("sem href vira <div>", d.startswith(u"<div "))
    checar("e não promete navegação", u"href" not in d)


def teste_aplicar_nao_duplica():
    secao("folha: entra uma vez, e nunca quebra a pagina")
    p = u"<html><head><title>x</title></head><body>y</body></html>"
    a = C.aplicar(p)
    checar("injeta a folha", u"rc-capa{" in a)
    checar("antes do </head>", a.index(u"rc-capa{") < a.lower().index(u"</head>"))
    checar("segunda passada não duplica", C.aplicar(a).count(u".rc-capa{") == 1)
    checar("página sem <head> volta intacta",
           C.aplicar(u"<div>solto</div>") == u"<div>solto</div>")
    checar("vazio não explode", C.aplicar(u"") == u"")


def teste_toda_tela_que_usa_a_capa_recebe_a_folha():
    secao("folha: quem usa as classes, recebe a folha")
    menu = ler("app/radai_menu.py")
    checar("o menu serve a folha a toda tela que passa por ele",
           "radai_cover.aplicar" in menu)

    sem_folha = []
    for nome in _componentes.nomes("app"):
        if not nome.endswith(".py") or nome == "radai_cover.py":
            continue
        s = ler(os.path.join("app", nome))
        if 'class="rc-' not in s or "response_class=HTMLResponse" not in s:
            continue
        if "radai_menu.aplicar" in s or "radai_cover.aplicar" in s:
            continue
        sem_folha.append(nome)
    checar("nenhuma tela servida usa as classes sem servir a folha",
           not sem_folha, ", ".join(sem_folha))


def teste_nenhuma_tela_tem_a_segunda_copia():
    secao("folha: nenhuma copia local do desenho da capa")
    donas = []
    for nome in _componentes.nomes("app"):
        if not nome.endswith(".py") or nome == "radai_cover.py":
            continue
        s = ler(os.path.join("app", nome))
        for regra in (".rc-capa{", ".rc-chip{", ".rc-risca{", ".rc-rotulo{"):
            if regra in s:
                donas.append("%s tem %s" % (nome, regra))
    checar("a folha da capa mora em radai_cover.py, e só lá",
           not donas, " | ".join(donas))

    css = C.CSS
    fora = [s for s in re.findall(r"(?m)^\.([\w-]+)", css) if not s.startswith("rc-")]
    checar("toda classe da folha tem prefixo rc-", not fora, ", ".join(sorted(set(fora))))


def _canto(h):
    i = h.find(u'<div class="dir">')
    return h[i:] if i >= 0 else u""


def teste_a_porta_tem_o_fechar_ao_lado_da_engrenagem():
    secao("o cabecalho das telas nunca escreve a ancora do Fechar")
    raiz = C.cabecalho(com_idioma=True, chave=u"inicio")
    checar("cabecalho() ignora com_idioma: nem a raiz ganha a ancora",
           u"data-radai-encerrar" not in raiz, raiz[-200:])
    import radai_router
    porta = radai_router.montar_porta()
    eng = re.search(r'(?s)<details class="ls-engrenagem" data-radai-engrenagem>'
                    r'(.*?)</details>', porta)
    checar("a ancora da porta mora dentro da engrenagem (radai_porta)",
           bool(eng) and u"data-radai-encerrar" in eng.group(1))
    for chave in (u"lote", u"autocontorno", u"config", u"recon_anatomia"):
        h = C.cabecalho(chave=chave)
        checar("[%s] NAO tem a ancora do Fechar" % chave,
               u"data-radai-encerrar" not in h)


def teste_o_voltar_leva_o_pai_como_reserva():
    secao("o voltar: marcado para o historico, com o pai de reserva")
    import radai_breadcrumb as B
    for chave in (u"lote", u"recon_anatomia", u"bridge_laudo", u"config",
                  u"termos"):
        h = C.cabecalho(chave=chave)
        pai = (B.pai(chave) or (u"", u""))[1]
        canto = _canto(h)
        checar("[%s] o voltar e marcado para o historico" % chave,
               u"data-radai-voltar" in canto, canto[:200])
        checar("[%s] o href e o pai (%s)" % (chave, pai),
               (u'href="%s"' % pai) in canto)
        checar("[%s] e o pai viaja tambem num atributo proprio" % chave,
               (u'data-radai-pai="%s"' % pai) in canto)
        checar("[%s] a classe continua ui-volta" % chave,
               u'class="ui-volta"' in canto)
        rot = B.rotulo(chave)
        checar("[%s] o cabecalho diz o nome da tela" % chave,
               (u'data-radai-tela="%s"' % C._esc(rot)) in h, rot)
    import radai_router
    checar("a porta nao tem voltar",
           u"data-radai-voltar" not in re.sub(r"(?is)<script\b.*?</script>", u"",
                                               radai_router.montar_porta()))


BASE_TESTE = u"http://suite.radai.test"


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


_TELAS = ((u"/", u"inicio", True), (u"/autocontorno", u"autocontorno", False),
          (u"/lote", u"lote", False), (u"/config", u"config", False),
          (u"/termos", u"termos", False))


MARCA_DO_CORTE = u"  // GUARDA: a pilha nao repete tela"
FIM_DO_CORTE = u"  if(p.length && p[p.length - 1].u === aqui) p[p.length - 1].t = nome;"
INICIO_DA_PILHA = u" var HIST = 'radai_hist'"
DEPOIS_DA_PILHA = u"try{ window.uiAbasTodas() }catch(e){}"


def _montar_telas(sem_pilha=False, sem_corte=False):
    import radai_ui
    js_real = radai_ui.JS
    if sem_corte:
        ini = js_real.index(MARCA_DO_CORTE)
        fim = js_real.index(FIM_DO_CORTE, ini)
        radai_ui.JS = js_real[:ini] + js_real[fim:]
    if sem_pilha:
        ini = js_real.index(INICIO_DA_PILHA)
        fim = js_real.rfind(
            u" document.addEventListener('DOMContentLoaded'", ini,
            js_real.index(DEPOIS_DA_PILHA, ini))
        if fim < 0 or u"function histRegistrar(" not in js_real[ini:fim] \
                or u"[data-radai-voltar]" not in js_real[ini:fim]:
            raise ValueError(u"fim do bloco do Voltar nao achado")
        radai_ui.JS = js_real[:ini] + js_real[fim:]
    try:
        links = u"".join(u'<a id="ir%s" href="%s">%s</a> '
                         % (r.replace(u"/", u"_") or u"_", r, r)
                         for r, _c, _raiz in _TELAS)
        links += (u'<a id="ir_lote_busca" href="/lote?pasta=C%3A%5CPACIENTES'
                  u'%5CSILVA_FANTOMA%5CCT">busca</a> '
                  u'<a id="ir_config_hash" href="/config#ps_x">hash</a>')
        telas = {}
        import radai_router
        for rota, chave, raiz in _TELAS:
            if raiz:
                porta = radai_router.montar_porta()
                telas[rota] = porta.replace(
                    u"</main>", u'<p style="position:relative;z-index:9">%s</p></main>'
                    % links, 1)
                continue
            html = (u'<!doctype html><html><head><meta charset="utf-8">'
                    u'<title>%s</title></head><body>%s<main style="padding:'
                    u'90px 20px">%s</main></body></html>'
                    % (chave, C.cabecalho(chave=chave), links))
            telas[rota] = radai_ui.aplicar(html)
        return telas
    finally:
        radai_ui.JS = js_real


def _servir(ctx, telas):
    from urllib.parse import urlsplit

    def atender(route):
        caminho = urlsplit(route.request.url).path
        corpo = telas.get(caminho)
        if corpo is None:
            route.fulfill(status=404, body=u"")
        else:
            route.fulfill(status=200, content_type=u"text/html; charset=utf-8",
                          body=corpo)
    ctx.route(BASE_TESTE + u"/**", atender)


def _voltar(pg):
    b = pg.locator(u".rc-topo [data-radai-voltar]")
    if b.count() != 1:
        return (u"", u"", u"")
    return (b.get_attribute(u"data-radai-destino") or u"",
            b.get_attribute(u"href") or u"", b.get_attribute(u"title") or u"")


def _rota(pg):
    from urllib.parse import urlsplit
    return urlsplit(pg.url).path


def _ir(pg, seletor):
    with pg.expect_navigation():
        pg.click(seletor)


def teste_o_voltar_e_historico_no_navegador():
    secao("o voltar e historico, no navegador")
    exe = _chromium()
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        sync_playwright = None
    if not exe or sync_playwright is None:
        print(u"    PULADO o navegador: sem Playwright ou sem Chromium")
        return
    telas = _montar_telas()
    isca = _montar_telas(sem_pilha=True)
    with sync_playwright() as pw:
        nav = pw.chromium.launch(executable_path=exe, headless=True)
        try:
            ctx = nav.new_context()
            _servir(ctx, telas)
            pg = ctx.new_page()
            pg.goto(BASE_TESTE + u"/lote")
            d, h, _t = _voltar(pg)
            checar("sem historico (endereco digitado), o Voltar e o pai",
                   d == u"pai" and h == u"/autocontorno", u"%s %s" % (d, h))

            _ir(pg, u"#ir_config")
            d, h, t = _voltar(pg)
            checar("com historico, o destino e a tela anterior, e nao o pai",
                   d == u"historico" and h == u"/lote", u"%s %s" % (d, h))
            checar("e o title diz o nome dela",
                   t == u"Voltar para Rodar agora", t)
            _ir(pg, u".rc-topo [data-radai-voltar]")
            checar("o clique volta para /lote (o pai de /config e /)",
                   _rota(pg) == u"/lote", pg.url)

            d, h, _t = _voltar(pg)
            checar("de volta em /lote, a pilha acabou e vale o pai",
                   d == u"pai" and h == u"/autocontorno", u"%s %s" % (d, h))
            _ir(pg, u".rc-topo [data-radai-voltar]")
            d, h, _t = _voltar(pg)
            checar("subir nao cria vai-e-vem: de /autocontorno vai para /",
                   _rota(pg) == u"/autocontorno" and d == u"pai"
                   and h == u"/", u"%s %s %s" % (_rota(pg), d, h))
            ctx.close()

            ctx = nav.new_context()
            _servir(ctx, telas)
            pg = ctx.new_page()
            pg.goto(BASE_TESTE + u"/")
            _ir(pg, u"#ir_termos")
            pg.reload()
            d, h, _t = _voltar(pg)
            checar("a recarga nao empilha a tela de novo",
                   d == u"historico" and h == u"/", u"%s %s" % (d, h))
            _ir(pg, u"#ir_lote")
            d, h, _t = _voltar(pg)
            checar("em /lote vindo de /termos, o Voltar leva a /termos",
                   d == u"historico" and h == u"/termos", u"%s %s" % (d, h))
            with pg.expect_navigation():
                pg.go_back()
            d, h, _t = _voltar(pg)
            checar("o voltar do NAVEGADOR mantem a pilha em dia",
                   _rota(pg) == u"/termos" and d == u"historico" and h == u"/",
                   u"%s %s %s" % (_rota(pg), d, h))
            with pg.expect_navigation():
                pg.go_forward()
            d, h, _t = _voltar(pg)
            checar("e o avancar do navegador tambem",
                   _rota(pg) == u"/lote" and h == u"/termos",
                   u"%s %s %s" % (_rota(pg), d, h))

            _ir(pg, u"#ir_lote_busca")
            _ir(pg, u"#ir_config_hash")
            pilha = pg.evaluate(u"sessionStorage.getItem('radai_hist') || ''")
            checar("a pilha guarda so a rota: sem busca, sem caminho, sem #",
                   pilha and u"?" not in pilha and u"#" not in pilha
                   and u"PACIENTES" not in pilha and u"%5C" not in pilha
                   and u"SILVA" not in pilha, pilha[:200])
            import json as _json
            itens = _json.loads(pilha or u"[]")
            checar("e cada item e so {u, t}",
                   itens and all(sorted(i) == [u"t", u"u"] for i in itens),
                   pilha[:200])
            ctx.close()

            ctx = nav.new_context()
            _servir(ctx, isca)
            pg = ctx.new_page()
            pg.goto(BASE_TESTE + u"/lote")
            _ir(pg, u"#ir_config")
            _ir(pg, u".rc-topo [data-radai-voltar]")
            checar("[isca] sem o bloco do historico, o Voltar sobe para o pai "
                   "(a bateria distingue as duas versoes)",
                   _rota(pg) == u"/", pg.url)
            ctx.close()
        finally:
            nav.close()


def _trilha_e_voltar(nav, telas):
    ctx = nav.new_context()
    _servir(ctx, telas)
    pg = ctx.new_page()
    m = {}
    try:
        pg.goto(BASE_TESTE + u"/")
        _ir(pg, u"#ir_autocontorno")
        _ir(pg, u"#ir_lote")
        passo = pg.locator(u".rc-topo a.rc-passo")
        m["passos"] = passo.count()
        m["href_passo"] = passo.first.get_attribute(u"href") if m["passos"] else u""
        if m["passos"]:
            _ir(pg, u".rc-topo a.rc-passo")
        m["depois_do_passo"] = _rota(pg)
        m["voltar"] = _voltar(pg)
        _ir(pg, u".rc-topo [data-radai-voltar]")
        m["depois_do_voltar"] = _rota(pg)
        _ir(pg, u"#ir_lote")
        _ir(pg, u"#ir_config")
        _ir(pg, u"#ir_lote")
        m["voltar_lote"] = _voltar(pg)
        _ir(pg, u".rc-topo [data-radai-voltar]")
        m["volta1"] = _rota(pg)
        m["voltar_volta1"] = _voltar(pg)
    finally:
        ctx.close()
    return m


def teste_a_trilha_navega_e_o_voltar_nao_faz_laco():
    secao("a trilha navega, e o voltar nao alterna entre duas telas")
    exe = _chromium()
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        sync_playwright = None
    if not exe or sync_playwright is None:
        print(u"    PULADO o navegador: sem Playwright ou sem Chromium")
        return
    telas = _montar_telas()
    isca = _montar_telas(sem_corte=True)
    with sync_playwright() as pw:
        nav = pw.chromium.launch(executable_path=exe, headless=True)
        try:
            m = _trilha_e_voltar(nav, telas)
            checar("em /lote a trilha tem o passo do ContourLab, com link",
                   m.get("passos") == 1 and m.get("href_passo") == u"/autocontorno",
                   repr(m))
            checar("  e clicar nele navega para /autocontorno",
                   m.get("depois_do_passo") == u"/autocontorno", repr(m))
            checar("de volta a uma tela ja empilhada, o voltar leva a porta "
                   "(e nao a /lote, de onde se veio)",
                   m.get("voltar", ())[:2] == (u"historico", u"/"), repr(m))
            checar("  e o clique chega la",
                   m.get("depois_do_voltar") == u"/", repr(m))
            checar("/ > /lote > /config > /lote: o voltar de /lote vai para /",
                   m.get("voltar_lote", ())[:2] == (u"historico", u"/")
                   and m.get("volta1") == u"/", repr(m))
            mi = _trilha_e_voltar(nav, isca)
            checar("[isca] sem o corte da pilha, o voltar alterna: de "
                   "/autocontorno volta a /lote (a bateria distingue)",
                   mi.get("voltar", ())[1:2] == (u"/lote",), repr(mi))
        finally:
            nav.close()


_VERSAO_NOVA = {u"estado": u"nova", u"nova": True, u"publicada": u"8.4",
                u"aqui": u"8.2",
                u"link": u"https://github.com/radioterapia-ai/local-suite/"
                         u"releases/latest/download/X_SETUP_LATEST.zip"}
_VERSAO_PRIVADO = {u"estado": u"privado", u"nova": False, u"publicada": u"",
                   u"aqui": u"8.2", u"link": u""}
_ENGRENAGEM = u'[data-radai-engrenagem] summary'


def _porta_servida(nav, porta, respostas):
    import json as _json
    from urllib.parse import urlsplit
    ctx = nav.new_context(viewport={"width": 1366, "height": 800})
    pedidos = []

    def atender(route):
        caminho = urlsplit(route.request.url).path
        if caminho == u"/":
            route.fulfill(status=200, content_type=u"text/html; charset=utf-8",
                          body=porta)
        elif caminho == u"/api/versao":
            r = respostas[min(len(pedidos), len(respostas) - 1)]
            pedidos.append(r[u"estado"])
            route.fulfill(status=200, content_type=u"application/json",
                          body=_json.dumps(r))
        else:
            route.fulfill(status=404, body=u"")
    ctx.route(BASE_TESTE + u"/**", atender)
    pg = ctx.new_page()
    pg.goto(BASE_TESTE + u"/", wait_until="domcontentloaded")
    return ctx, pg, pedidos


def _estado_da_porta(pg, esperar_ms=1500):
    try:
        pg.wait_for_selector(u"#rv-aviso.vis", timeout=esperar_ms)
    except Exception:
        pass
    pontos = pg.locator(_ENGRENAGEM + u" .ui-ponto").count()
    av = pg.locator(u"#rv-aviso")
    vis = av.count() == 1 and av.is_visible()
    return pontos, vis, (av.inner_text() if av.count() == 1 else u"")


def teste_a_engrenagem_acende_com_versao_nova():
    secao("versao nova: o ponto na engrenagem e o aviso, no navegador")
    import radai_router
    porta = radai_router.montar_porta()
    porta_sem_script = re.sub(r"(?s)<script.*?</script>", u" ", porta)
    checar("a porta pergunta ao servidor, e nao ao GitHub",
           u"fetch('/api/versao'" in porta and u"api.github.com" not in porta)
    checar("e o aviso nao nasce no HTML (so com versao nova)",
           u'id="rv-aviso"' not in porta_sem_script)
    exe = _chromium()
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        sync_playwright = None
    if not exe or sync_playwright is None:
        print(u"    PULADO o navegador: sem Playwright ou sem Chromium")
        return
    acende = u"if(window.uiPonto) window.uiPonto(g, true);"
    checar("o ponto e aceso por uma linha so", porta.count(acende) == 1,
           str(porta.count(acende)))
    isca = porta.replace(acende, u"")
    with sync_playwright() as pw:
        nav = pw.chromium.launch(executable_path=exe, headless=True)
        try:
            ctx, pg, ped = _porta_servida(nav, porta, [_VERSAO_NOVA])
            n, vis, txt = _estado_da_porta(pg)
            checar("versao nova: UM ponto na engrenagem", n == 1, str(n))
            checar("  e o aviso aparece", vis, txt[:80])
            checar("  com as duas versoes", u"8.2" in txt and u"8.4" in txt,
                   txt[:120])
            lk = pg.locator(u"#rv-aviso a.rv-pri")
            checar("  e o link permanente do instalador",
                   lk.count() == 1
                   and lk.get_attribute(u"href") == _VERSAO_NOVA[u"link"]
                   and lk.get_attribute(u"target") == u"_blank",
                   lk.get_attribute(u"href") if lk.count() else u"(sem link)")
            cor = pg.evaluate(
                u"(function(){var p=document.querySelector('%s .ui-ponto');"
                u"var t=getComputedStyle(document.documentElement)"
                u".getPropertyValue('--perigo').trim();"
                u"return p?[getComputedStyle(p).backgroundColor,t]:null})()"
                % _ENGRENAGEM)
            checar("  o ponto e o vermelho de perigo das fichas",
                   bool(cor) and cor[1].lower() == u"#e96a5c"
                   and cor[0] == u"rgb(233, 106, 92)", repr(cor))
            pg.click(u"#rv-aviso .rv-sec")
            pg.wait_for_timeout(450)
            vista = pg.evaluate(u"localStorage.getItem('radai_versao_vista')")
            checar("Fechar tira o aviso", pg.locator(u"#rv-aviso").count() == 0)
            checar("  e o ponto continua na engrenagem",
                   pg.locator(_ENGRENAGEM + u" .ui-ponto").count() == 1)
            checar("  e o navegador guarda a versao vista", vista == u"8.4",
                   repr(vista))
            pg.reload(wait_until="domcontentloaded")
            n, vis, _t = _estado_da_porta(pg, 1200)
            checar("recarregada: o ponto volta e o aviso NAO (uma vez por "
                   "versao)", n == 1 and not vis, u"%s %s" % (n, vis))
            ctx.close()

            ctx, pg, ped = _porta_servida(nav, porta, [_VERSAO_PRIVADO])
            n, vis, _t = _estado_da_porta(pg, 1200)
            checar("repositorio privado: nem ponto nem aviso",
                   n == 0 and not vis and ped == [u"privado"],
                   u"%s %s %s" % (n, vis, ped))
            ctx.close()

            nunca = dict(_VERSAO_PRIVADO, estado=u"nunca")
            ctx, pg, ped = _porta_servida(nav, porta, [nunca, _VERSAO_NOVA])
            n, vis, _t = _estado_da_porta(pg, 6000)
            checar("com a consulta ainda sem resposta, a porta pergunta de "
                   "novo e acende", n == 1 and vis and len(ped) >= 2,
                   u"%s %s %s" % (n, vis, ped))
            ctx.close()

            ctx, pg, _ped = _porta_servida(nav, isca, [_VERSAO_NOVA])
            n, vis, _t = _estado_da_porta(pg)
            checar("[isca] sem a linha do ponto, o aviso aparece e a "
                   "engrenagem fica apagada (a checagem distingue as duas)",
                   n == 0 and vis, u"%s %s" % (n, vis))
            ctx.close()
        finally:
            nav.close()


def main():
    print("test_cover | a capa das telas e a folha compartilhada")
    for t in (teste_capa_monta, teste_capa_escapa, teste_cartao,
              teste_aplicar_nao_duplica,
              teste_toda_tela_que_usa_a_capa_recebe_a_folha,
              teste_nenhuma_tela_tem_a_segunda_copia,
              teste_a_porta_tem_o_fechar_ao_lado_da_engrenagem,
              teste_o_voltar_leva_o_pai_como_reserva,
              teste_o_voltar_e_historico_no_navegador,
              teste_a_trilha_navega_e_o_voltar_nao_faz_laco,
              teste_a_engrenagem_acende_com_versao_nova):
        try:
            t()
        except Exception as e:
            import traceback
            checar("%s (excecao inesperada)" % t.__name__, False,
                   "%s: %s" % (type(e).__name__, e))
            traceback.print_exc()
    print()
    if FALHAS:
        print("FALHOU: %d de %d checagens" % (FALHAS, OK + FALHAS))
        return 1
    print("OK: %d checagens, todas passaram" % OK)
    return 0


if __name__ == "__main__":
    sys.exit(main())
