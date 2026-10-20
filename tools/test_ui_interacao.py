# -*- coding: utf-8 -*-
import io
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _cleanup
import _componentes
_cleanup.adotar_prefixo('radai_ui_')



def porta_livre():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
    finally:
        s.close()


PORTA = porta_livre()
BASE = "http://127.0.0.1:%d" % PORTA


def _frase_do_molde():
    sys.path.insert(0, os.path.join(RAIZ, "app"))
    try:
        import radai_phrases as _F
        d = _F.construir()
        k = next(k for k in sorted(d["en"])
                 if k.startswith(u"Esta máquina tem %s, e o torch"))
        vals = (u"NVIDIA Quadro P2200", u"2.5.1+cu121", u"12.1")
        return k % vals, d["de"][k] % vals, vals
    except Exception:
        return u"", u"", ()
    finally:
        sys.path.pop(0)


_FRASE_DO_MOLDE, _FRASE_DO_MOLDE_DE, _VALORES_DO_MOLDE = _frase_do_molde()

_R = []


def checar(nome, ok, detalhe=u""):
    _R.append((nome, bool(ok), detalhe))
    print(u"  %-6s %s%s" % (u"ok" if ok else u"FALHA", nome,
                            (u"  [%s]" % detalhe) if detalhe and not ok else u""))
    return bool(ok)


def secao(t):
    print(u"\n-- %s --" % t)


def _cortes_pedidos(urls):
    from urllib.parse import parse_qs, urlparse
    fora = []
    for u in urls:
        v = parse_qs(urlparse(u).query).get("corte")
        if v:
            fora.append(int(v[0]))
    return fora


_DOCUMENTOS = ("/termos", "/politica-privacidade")

_JS_TEXTO_DOC = (
    "(function(){ var e = document.querySelector('.env'); if(!e) return null;"
    " var c = e.cloneNode(true), a = c.querySelector('#radai-aviso-doc');"
    " if(a) a.remove(); return c.textContent.replace(/\\s+/g, ' ').trim() })()")
_JS_TEXTO_TOPO = (
    "(function(){ var h = document.querySelector('header.rc-topo');"
    " return h ? h.textContent.replace(/\\s+/g, ' ').trim() : null })()")


def _trocas(antes, depois):
    import difflib
    a, b = (antes or u"").split(), (depois or u"").split()
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    return [(u" ".join(a[i1:i2]), u" ".join(b[j1:j2]))
            for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal"]


async def _documentos_em(pg, lingua):
    fora = {}
    if not (pg.url or u"").startswith(BASE):
        await pg.goto(BASE + _DOCUMENTOS[0], wait_until="networkidle")
    await pg.evaluate("localStorage.setItem('radai_idioma', '%s'); true"
                      % lingua)
    for rota in _DOCUMENTOS:
        await pg.goto(BASE + rota, wait_until="networkidle")
        await pg.wait_for_timeout(700)
        fora[rota] = (await pg.evaluate(_JS_TEXTO_DOC),
                      await pg.evaluate(_JS_TEXTO_TOPO),
                      await pg.evaluate(
                          "!!document.getElementById('radai-aviso-doc')"))
    return fora


def _bisseccao(n):
    app = os.path.join(RAIZ, "app")
    if app not in sys.path:
        sys.path.insert(0, app)
    import radai_thumbnail
    return radai_thumbnail.ordem_de_bisseccao(int(n or 0))


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


def _subir(base_tmp):
    sys.path.insert(0, os.path.join(RAIZ, "tools"))
    from datetime import datetime, timedelta
    from make_test_series import escreve_serie

    root = os.path.join(base_tmp, "share")
    if not os.path.isdir(root):
        for nome, dias, cortes in (("PAC_A", 1, 30), ("PAC_B", 2, 28),
                                   ("PAC_C", 3, 26)):
            escreve_serie(os.path.join(root, nome, "CT"), nome,
                          datetime.now() - timedelta(days=dias), cortes)
    cfg = os.path.join(base_tmp, "t.config")
    io.open(cfg, "w", encoding="utf-8").write(
        u"ROOT=%s\nDRY_RUN=1\nMIN_SLICES=5\nQUIET_MIN=0\nTPS_DESTINO=eclipse\nPORT=%d\nLOG_DIR=%s\n"
        % (root, PORTA, os.path.join(base_tmp, "log")))
    env = dict(os.environ, RADAI_CONFIG=cfg, RADAI_MACHINE="BATERIA_UI",
               RADAI_CALIB_DIR=os.path.join(base_tmp, "calib"),
               LOCALAPPDATA=os.path.join(base_tmp, "ad"),
               PYTHONIOENCODING="utf-8:replace")
    saida = io.open(os.path.join(base_tmp, "vigia.log"), "wb")
    proc = subprocess.Popen(
        [sys.executable, _componentes.fonte("app/radai_watcher.py")],
        env=env, stdout=saida, stderr=subprocess.STDOUT)
    for _ in range(60):
        try:
            urllib.request.urlopen(BASE + "/aceite", timeout=2).read()
            return proc, root
        except Exception:
            time.sleep(1)
    proc.kill()
    return None, root


async def _encher_pasta(pg, valor):
    await pg.evaluate("ltEscolha(); true")
    await pg.wait_for_timeout(300)
    await pg.fill("#pasta", valor)


async def _rodar(pg, root):
    secao(u"o portao do aceite")
    await pg.goto(BASE + "/vigia", wait_until="networkidle")
    checar(u"rota de trabalho sem aceite cai no /aceite",
           "/aceite" in pg.url, pg.url)
    await pg.wait_for_timeout(600)
    checar(u"o botao de entrar nasce desabilitado",
           await pg.is_disabled("#ac_bt"))
    await pg.check("#ac_ok")
    checar(u"  e a caixa o habilita", await pg.is_enabled("#ac_bt"))
    linhas = await pg.locator("#ac_fo_linhas .fo").count()
    checar(u"a splash lista os pesos de terceiros", linhas >= 4,
           u"%d linha(s)" % linhas)
    nao = await pg.locator(".pt.nao").count()
    aten = await pg.locator(".pt.atencao").count()
    checar(u"e os pontos saem com os tres sinais", nao >= 1 and aten >= 1,
           u"nao=%d atencao=%d" % (nao, aten))
    await pg.click("#ac_bt")
    await pg.wait_for_timeout(1500)
    checar(u"aceitar leva para dentro", "/aceite" not in pg.url, pg.url)

    secao(u"a porta")
    await pg.goto(BASE + "/", wait_until="networkidle")
    await pg.wait_for_timeout(500)
    checar(u"a autoria esta no pe",
           (await pg.locator(".ls-rodape .ls-autor").count()) == 1)
    n = await pg.evaluate(
        "document.querySelector('.ls-cards').children.length")
    checar(u"os seis modulos estao la, na grade", n >= 6, u"%d" % n,)

    secao(u"o ContourLab tem dois cartoes")
    await pg.goto(BASE + "/autocontorno", wait_until="networkidle")
    await pg.wait_for_timeout(400)
    cart = await pg.locator(".md-fer").count()
    checar(u"sao dois cartoes", cart == 2, u"%d" % cart)
    checar(u"e nenhum deles e o do vigia",
           (await pg.locator('.md-fer[href="/vigia"]').count()) == 0)

    secao(u"o «Rodar agora»: carrinho, agrupamento e animacoes")
    await pg.goto(BASE + "/lote", wait_until="networkidle")
    await pg.wait_for_timeout(900)
    cds = pg.locator(".rc-card")
    n_cd = await cds.count()
    checar(u"os cards do topo estao la", n_cd >= 2, u"%d" % n_cd)
    inertes = []
    for _i in range(n_cd):
        _c = cds.nth(_i)
        if not await _c.evaluate("e => e.classList.contains('acao')"):
            inertes.append(await _c.evaluate("e => e.id || '(sem id)'"))
    checar(u"  e todo cartao da fileira e uma ACAO",
           not inertes, u", ".join(inertes))
    checar(u"  ao carregar, o popup do passo 1 ja aparece",
           await pg.evaluate("!!document.getElementById('cx1').closest('.ui-modal-veu.vis')"))
    await pg.keyboard.press("Escape")
    await pg.wait_for_timeout(300)
    await pg.evaluate("document.getElementById('cd_add').click()")
    await pg.wait_for_timeout(250)
    checar(u"  e clicar em «Adicionar novas series» reabre o popup do passo 1",
           await pg.evaluate("!!document.getElementById('cx1').closest('.ui-modal-veu.vis')"))
    await pg.keyboard.press("Escape")
    await pg.wait_for_timeout(300)

    await pg.evaluate("rodar()")
    await pg.wait_for_timeout(80)
    checar(u"processar sem nada faz o BOTAO tremer",
           await pg.evaluate(
               "document.getElementById('btrodar')"
               ".classList.contains('ui-treme')"),
           u"a mensagem sai no passo 1, e o botao esta abaixo")

    await _encher_pasta(pg, os.path.join(root, "PAC_A"))
    n = await pg.evaluate(
        "varrer(); document.querySelectorAll('#tab .ui-esqueleto').length")
    checar(u"a varredura pinta o esqueleto", n > 0, u"%d barra(s)" % n)
    await pg.wait_for_timeout(4000)
    checar(u"  e ele some quando a lista chega",
           (await pg.locator("#tab .ui-esqueleto").count()) == 0)
    checar(u"a serie entrou no carrinho",
           await pg.evaluate("carrinhoLista().length") == 1)

    await _encher_pasta(pg, os.path.join(root, "PAC_B"))
    await pg.click('button[onclick="varrer()"]')
    await pg.wait_for_timeout(4000)
    n = await pg.evaluate("carrinhoLista().length")
    checar(u"a outra pasta SOMA ao carrinho", n == 2, u"%d" % n)
    r = await pg.evaluate("carrinhoRaizes()")
    checar(u"  e o resumo sabe que sao duas pastas", r == 2, u"%d" % r)
    checar(u"  e o resumo esta visivel",
           await pg.is_visible("#cartcx"))

    await pg.evaluate("marcar(false)")
    n = await pg.evaluate("carrinhoLista().length")
    checar(u"«tirar as desta pasta» poupa a outra", n == 1, u"%d" % n)

    await pg.evaluate("ltEscolha(); true")
    await pg.wait_for_timeout(300)
    await pg.click('button[onclick="varrer()"]')
    await pg.wait_for_timeout(4000)
    n = await pg.evaluate("carrinhoLista().length")
    checar(u"revarrer nao devolve o que foi tirado", n == 1, u"%d" % n)

    secao(u"o passo 2 enxuto, e o passo 3 fora")
    for sel, nome in (("#loc", u"a segunda busca"), ("#cx3", u"o passo 3"),
                      ("#tab tr.grp", u"a linha do estudo"),
                      ("#btcancel", u"o Cancelar do passo 2"),
                      ("#modo", u"o modo do lote inteiro")):
        checar(u"%s nao esta na tela" % nome,
               (await pg.locator(sel).count()) == 0)

    secao(u"o modo e da linha: FAST, AUTO e PERSONALIZADO")
    await _encher_pasta(pg, root)
    await pg.click('button[onclick="varrer()"]')
    await pg.wait_for_timeout(4000)
    await pg.evaluate("limparSelecao(); SERIES.forEach(function(s){"
                      " delete ESCOLHA[chaveDe(s)] }); pintarTabela(); true")
    await pg.wait_for_timeout(300)
    ix = await pg.evaluate(
        "(function(){ var r = {}; SERIES.forEach(function(s, i){ r[s.pid] = i });"
        " return r })()")
    checar(u"a pasta raiz lista as tres series fantoma",
           sorted(ix) == [u"PAC_A", u"PAC_B", u"PAC_C"], str(ix))
    a, b, c = ix.get(u"PAC_A", 0), ix.get(u"PAC_B", 1), ix.get(u"PAC_C", 2)
    n_sel = await pg.locator("#tab td.modo select.md-sel").count()
    n_abas = await pg.locator("#tab td.modo .ui-seg").count()
    n_aj = await pg.locator("#tab td.modo [data-md-aj]").count()
    checar(u"cada linha tem o seletor na ULTIMA coluna, e o `?` ao lado",
           n_sel == 3 and n_abas == 3 and n_aj == 3,
           u"select=%d abas=%d ?=%d" % (n_sel, n_abas, n_aj))
    ultima = await pg.evaluate(
        "(function(){ var tr = document.getElementById('linha_0');"
        " return tr ? tr.lastElementChild.className : '' })()")
    checar(u"  e a coluna do modo e a ultima da linha", ultima == u"modo", ultima)
    checar(u"o botao «escolher estudos» da v8.2 saiu",
           (await pg.locator("#tab [data-md-ed]").count()) == 0
           and (await pg.locator("#tab .est-ck, #tab .cat-ck").count()) == 0)

    def _modo(i):
        return pg.evaluate("escolhaDe(SERIES[%d]).modo" % i)

    cinza = await pg.evaluate(
        "(function(i){ var cx = document.querySelector('#linha_' + i + ' .md-cx');"
        " var bs = cx ? cx.querySelectorAll('.ui-seg button') : [];"
        " return [cx ? cx.classList.contains('md-off') : false, bs.length,"
        "  Array.prototype.every.call(bs, function(b){ return b.disabled })] })(%d)" % a)
    checar(u"serie NAO incluida: o seletor inteiro apagado e desabilitado",
           cinza == [True, 3, True], str(cinza))
    await pg.click('#linha_%d .ui-seg button[data-v="perso"]' % a, force=True)
    await pg.wait_for_timeout(300)
    checar(u"  e clicar no PERSONALIZADO apagado nao muda nada",
           await _modo(a) == u"" and (await pg.locator("#perso_%d" % a).count()) == 0,
           str(await _modo(a)))
    await pg.evaluate(
        "window.__ms = _montarSeletores; window.__mm = _mudouModo;"
        " _montarSeletores = function(){ Array.prototype.forEach.call("
        "  document.querySelectorAll('#tab select.md-sel'), function(s){"
        "  s.disabled = false; var cx = uiSegmentado(s); }) };"
        " _mudouModo = function(sel){ var i = parseInt(sel.getAttribute('data-md-i'),10);"
        "  escolhaDe(SERIES[i]).modo = sel.value; _acertarPainel(i) };"
        " pintarTabela(); true")
    await pg.wait_for_timeout(300)
    await pg.click('#linha_%d .ui-seg button[data-v="perso"]' % a, force=True)
    await pg.wait_for_timeout(300)
    isca_cinza = await _modo(a)
    await pg.evaluate("_montarSeletores = window.__ms; _mudouModo = window.__mm;"
                      " escolhaDe(SERIES[%d]).modo = ''; pintarTabela(); true" % a)
    await pg.wait_for_timeout(300)
    checar(u"  (isca) sem a trava, o mesmo clique mudava o modo -- a checagem "
           u"discrimina", isca_cinza == u"perso", str(isca_cinza))

    await pg.evaluate("alternar(%d); true" % a)
    await pg.wait_for_timeout(300)
    sel_a = await pg.evaluate(
        "(function(i){ var b = document.querySelector('#linha_' + i +"
        " ' .ui-seg button[aria-checked=\"true\"]');"
        " var cx = document.querySelector('#linha_' + i + ' .md-cx');"
        " return [b ? b.getAttribute('data-v') : '', cx.classList.contains('md-off')] })(%d)" % a)
    checar(u"incluir a serie a faz nascer em AUTO (e o seletor acende)",
           await _modo(a) == u"auto" and sel_a == [u"auto", False],
           u"modo=%s aba=%s" % (await _modo(a), sel_a))
    await pg.evaluate(
        "window.__pn = porNoCarrinho; porNoCarrinho = function(s, dentro){"
        " var k = chaveDe(s); if(!k) return; if(dentro){ if(!s._raiz) s._raiz = '';"
        " CARRINHO[k] = s } else { delete CARRINHO[k] } };"
        " alternar(%d); true" % b)
    await pg.wait_for_timeout(200)
    isca_auto = await _modo(b)
    await pg.evaluate("porNoCarrinho = window.__pn; alternar(%d); alternar(%d); true"
                      % (b, b))
    await pg.wait_for_timeout(300)
    checar(u"  (isca) sem o AUTO ao incluir, a serie ficava sem modo -- a "
           u"checagem discrimina", isca_auto == u"", repr(isca_auto))
    checar(u"  e a serie B, incluida de novo, nasce em AUTO", await _modo(b) == u"auto",
           str(await _modo(b)))
    await pg.click('#linha_%d .ui-seg button[data-v="fast"]' % a)
    await pg.evaluate("alternar(%d); alternar(%d); true" % (a, a))
    await pg.wait_for_timeout(300)
    checar(u"  e a que sai e volta mantem o modo que tinha (FAST)",
           await _modo(a) == u"fast", str(await _modo(a)))

    checar(u"FAST nao abre painel", (await pg.locator("#perso_%d" % a).count()) == 0)
    checar(u"  e AUTO tambem nao", (await pg.locator("#perso_%d" % b).count()) == 0)
    await pg.evaluate("window.__pa = _painelAberto;"
                      " _painelAberto = function(i){ return !!INCL[i] };"
                      " pintarTabela(); true")
    await pg.wait_for_timeout(400)
    isca_fast = await pg.locator("#perso_%d" % a).count()
    await pg.evaluate("_painelAberto = window.__pa; pintarTabela(); true")
    await pg.wait_for_timeout(400)
    checar(u"  (isca) com o painel aberto para qualquer modo, o FAST abria -- "
           u"a checagem discrimina", isca_fast == 1, str(isca_fast))

    await pg.click('#linha_%d [data-md-aj]' % b)
    await pg.wait_for_timeout(400)
    bal = await pg.evaluate(
        "(function(){ var e = document.getElementById('md_balao');"
        " if(!e || e.hidden) return null; var r = e.getBoundingClientRect();"
        " return {dt: e.querySelectorAll('dt').length, dd: e.querySelectorAll('dd').length,"
        "  foco: document.activeElement === e, dentro: r.left >= 0 && r.right <= window.innerWidth,"
        "  exp: document.querySelector('#linha_%d [data-md-aj]').getAttribute('aria-expanded')} })()" % b)
    checar(u"o `?` abre o balao com os TRES modos explicados, dentro da tela",
           bool(bal) and bal["dt"] == 3 and bal["dd"] == 3 and bal["dentro"],
           str(bal))
    checar(u"  e o foco vai para dentro dele, com `aria-expanded`",
           bool(bal) and bal["foco"] and bal["exp"] == u"true", str(bal))
    await pg.keyboard.press("Escape")
    await pg.wait_for_timeout(300)
    checar(u"  e Esc fecha e devolve o foco ao `?`",
           await pg.evaluate("document.getElementById('md_balao').hidden &&"
                             " document.activeElement === document.querySelector("
                             "'#linha_%d [data-md-aj]')" % b))

    await pg.click('#linha_%d .ui-seg button[data-v="perso"]' % b)
    await pg.wait_for_timeout(600)
    checar(u"PERSONALIZADO abre o painel SO sob a linha dele",
           (await pg.locator("#perso_%d" % b).count()) == 1
           and (await pg.locator("tr.perso").count()) == 1,
           u"paineis=%d" % (await pg.locator("tr.perso").count()))
    anterior = await pg.evaluate(
        "(function(i){ var p = document.getElementById('perso_' + i);"
        " return p && p.previousElementSibling ? p.previousElementSibling.id : '' })(%d)" % b)
    checar(u"  logo abaixo da linha da serie", anterior == u"linha_%d" % b, anterior)
    colunas = await pg.evaluate(
        "Array.from(document.querySelectorAll('#perso_%d .p4-col')).map("
        "function(c){ return c.className.split(' ')[1] })" % b)
    checar(u"  com as QUATRO colunas, na ordem: protocolos, tasks, comparacao, "
           u"entregas", colunas == [u"p4-prot", u"p4-tasks", u"p4-comp", u"p4-ent"],
           str(colunas))
    base = await pg.evaluate(
        "(function(i){ var x = document.querySelector('#perso_' + i +"
        " ' .p4-task-ck:disabled'); return x ? [x.getAttribute('data-task'), x.checked,"
        " x.getAttribute('role')] : null })(%d)" % b)
    checar(u"  e a base travada em 1, como chave (`role=switch`)",
           bool(base) and base[1] is True and base[2] == u"switch", str(base))
    n_vel = await pg.locator("#perso_%d .p4-ln .selo-vel" % b).count()
    n_ach = await pg.locator("#perso_%d .p4-ln .selo-achado" % b).count()
    checar(u"  e a etiqueta de tempo SAIU da linha (mora no `?`); o selo "
           u"ACHADO ficou", n_vel == 0 and n_ach >= 1,
           u"etiquetas=%d achado=%d" % (n_vel, n_ach))
    marcadas = await pg.evaluate(
        "Array.from(document.querySelectorAll('#perso_%d .p4-task-ck:checked:not(:disabled)'))"
        ".map(function(x){ return x.getAttribute('data-task') })" % b)
    checar(u"  e na TC nascem ligadas so a cavidade do tronco (o pericardio do "
           u"Heart_ai) e o derrame (anatomia do torax)",
           sorted(marcadas) == [u"pleural_pericard_effusion",
                                u"trunk_cavities"],
           str(marcadas))

    async def _var_do_heart():
        for _ in range(25):
            v = await pg.evaluate(
                "(function(i){ var b = document.querySelector('#p4e_' + i +"
                " ' [data-oar-x=\"heart\"]'); var t = b ? b.closest('.oar-tag') : null;"
                " var s = t ? t.querySelector('.oar-var') : null;"
                " return s ? [s.textContent, s.classList.contains('sem')] : null })(%d)" % b)
            if v:
                return v
            await pg.wait_for_timeout(300)
        return None
    v_on = await _var_do_heart()
    checar(u"  e a previa das Entregas mostra o Heart_ai «com pericardio»",
           bool(v_on) and v_on[1] is False and bool(v_on[0].strip()),
           str(v_on))
    await pg.click('#perso_%d label.sw:has(.p4-task-ck[data-task="trunk_cavities"])' % b)
    await pg.wait_for_timeout(1500)
    v_off = await _var_do_heart()
    pl_off = await pg.evaluate("payloadDaSerie(SERIES[%d])" % b)
    checar(u"desligar a cavidade (o ato) leva a chave em 0 no payload, e a tag "
           u"do Heart_ai passa a «sem pericardio»",
           (pl_off.get("tasks") or {}).get(u"trunk_cavities") == 0
           and bool(v_off) and v_off[1] is True and bool(v_on)
           and v_off[0] != v_on[0],
           u"%s | %s" % ((pl_off.get("tasks") or {}).get(u"trunk_cavities"),
                         v_off))
    await pg.click('#perso_%d label.sw:has(.p4-task-ck[data-task="trunk_cavities"])' % b)
    await pg.wait_for_timeout(1500)
    v_volta = await _var_do_heart()
    checar(u"  e religada, a tag volta a «com pericardio»",
           bool(v_volta) and v_volta[1] is False, str(v_volta))
    await pg.evaluate("window.__lf = OPC.CT.ligadas_de_fabrica;"
                      " OPC.CT.ligadas_de_fabrica = [];"
                      " (function(e){ Object.keys(e.mao).forEach(function(k){"
                      " delete e.mao[k] }) })(escolhaDe(SERIES[%d]));"
                      " _acertarChaves(%d); true" % (b, b))
    isca_fab = await pg.evaluate(
        "Array.from(document.querySelectorAll('#perso_%d .p4-task-ck:checked:not(:disabled)'))"
        ".map(function(x){ return x.getAttribute('data-task') })" % b)
    await pg.evaluate("OPC.CT.ligadas_de_fabrica = window.__lf; _acertarChaves(%d);"
                      " pedirPrevia(%d); true" % (b, b))
    await pg.wait_for_timeout(900)
    checar(u"  (isca) sem a tabela de fabrica, a chave nascia desligada -- a "
           u"checagem discrimina", isca_fab == [], str(isca_fab))
    await pg.evaluate("alternar(%d); true" % c)
    await pg.wait_for_timeout(300)
    await pg.click('#linha_%d .ui-seg button[data-v="perso"]' % c)
    await pg.wait_for_timeout(500)
    await pg.click('#perso_%d label.sw:has(.p4-prot-ck[data-prot="coluna"])' % c)
    await pg.wait_for_timeout(300)
    dois = await pg.evaluate(
        "[protocolosLigados(SERIES[%d], escolhaDe(SERIES[%d])),"
        " protocolosLigados(SERIES[%d], escolhaDe(SERIES[%d]))]" % (b, b, c, c))
    checar(u"duas series em PERSONALIZADO, cada uma com os SEUS protocolos",
           dois == [[], [u"coluna"]] and (await pg.locator("tr.perso").count()) == 2,
           str(dois))
    await pg.evaluate("window.__ed = escolhaDe; escolhaDe = function(){"
                      " return ESCOLHA.__uma || (ESCOLHA.__uma = {modo:'perso', prot:{},"
                      " mao:{}, comp:{}, oar_fora:{}}) }; true")
    await pg.evaluate("ligarProtocolo(SERIES[%d], escolhaDe(SERIES[%d]), 'coluna', true); true"
                      % (c, c))
    isca_uma = await pg.evaluate("protocolosLigados(SERIES[%d], escolhaDe(SERIES[%d]))"
                                 % (b, b))
    await pg.evaluate("escolhaDe = window.__ed; delete ESCOLHA.__uma; true")
    checar(u"  (isca) com uma escolha so para a tela, a outra serie herdava o "
           u"protocolo -- a checagem discrimina", isca_uma == [u"coluna"],
           str(isca_uma))
    await pg.click('#perso_%d label.sw:has(.p4-prot-ck[data-prot="coluna"])' % c)
    await pg.click('#linha_%d .ui-seg button[data-v="auto"]' % c)
    await pg.wait_for_timeout(400)

    def _ligadas():
        return pg.evaluate(
            "Array.from(document.querySelectorAll('#perso_%d .p4-task-ck:checked:not(:disabled)'))"
            ".map(function(x){ return x.getAttribute('data-task') }).sort()" % b)

    def _livre():
        return pg.evaluate("!!escolhaDe(SERIES[%d]).livre" % b)
    DELE = sorted([u"breasts", u"pleural_pericard_effusion", u"trunk_cavities"])
    await pg.click('#perso_%d label.sw:has(.p4-prot-ck[data-prot="torax_mama"])' % b)
    await pg.wait_for_timeout(300)
    lig = await _ligadas()
    checar(u"ligar o Tórax / Mama liga só as tasks dele e desliga o resto",
           lig == DELE, str(lig))
    ach = await pg.evaluate(
        "Array.from(document.querySelectorAll('#perso_%d .p4-achado .p4-task-ck:checked')).length"
        % b)
    checar(u"  e nenhuma de ACHADO (REGRA A: protocolo nunca arrasta achado)",
           ach == 0, str(ach))
    await pg.click('#perso_%d label.sw:has(.p4-task-ck[data-task="breasts"])' % b)
    await pg.wait_for_timeout(300)
    pl = await pg.evaluate("payloadDaSerie(SERIES[%d])" % b)
    marcada = await pg.evaluate(
        "!!document.querySelector('#perso_%d input.p4-livre-ck:checked')" % b)
    checar(u"mexer à mão numa task desliga o protocolo e liga a Seleção livre",
           (pl.get("tasks") or {}).get(u"breasts") == 0
           and (pl.get("tasks") or {}).get(u"trunk_cavities") == 1
           and pl.get("protocolos") == [] and pl.get("modo") == u"perso"
           and await _livre() and marcada,
           str({k: pl.get(k) for k in ("modo", "protocolos")}))
    checar(u"  e o payload leva o estado FINAL de toda chave, e a comparacao "
           u"em zero",
           len(pl.get("tasks") or {}) >= 10
           and pl.get("comparacao") == {u"ts": 0, u"nv": 0, u"cads": 0, u"mse": 0}
           and u"estudos" not in pl and u"tasks_extra" not in pl,
           str(sorted(pl)))
    await pg.click('#perso_%d label.sw:has(.p4-prot-ck[data-prot="torax_mama"])' % b)
    await pg.wait_for_timeout(300)
    lig2 = await _ligadas()
    checar(u"  religar o protocolo volta a ligar só as tasks dele, e a Seleção "
           u"livre desliga", lig2 == DELE and not await _livre(), str(lig2))
    await pg.click('#perso_%d label.sw:has(.p4-prot-ck[data-prot="torax_mama"])' % b)
    await pg.evaluate("window.__tl = tasksLigadas; tasksLigadas = function(s, e){"
                      " var on = {}; Object.keys(e.mao).forEach(function(t){"
                      " if(e.mao[t] === 1) on[t] = 1 }); return on }; true")
    await pg.click('#perso_%d label.sw:has(.p4-prot-ck[data-prot="torax_mama"])' % b)
    await pg.wait_for_timeout(300)
    isca_arr = await _ligadas()
    await pg.evaluate("tasksLigadas = window.__tl; _acertarChaves(%d); true" % b)
    checar(u"  (isca) sem o protocolo na conta, nada ligava -- a checagem "
           u"discrimina", u"trunk_cavities" not in isca_arr, str(isca_arr))
    await pg.click('#perso_%d label.sw:has(.p4-prot-ck[data-prot="abdome"])' % b)
    await pg.wait_for_timeout(300)
    lig3 = await _ligadas()
    protos = await pg.evaluate(
        "protocolosLigados(SERIES[%d], escolhaDe(SERIES[%d]))" % (b, b))
    checar(u"escolher outro protocolo liga só as tasks dele (a glândula e o "
           u"derrame do Tórax / Mama saem)",
           protos == [u"abdome"] and u"trunk_cavities" in lig3
           and u"breasts" not in lig3
           and u"pleural_pericard_effusion" not in lig3, str([protos, lig3]))
    await pg.click('#perso_%d label.sw:has(.p4-prot-ck[data-prot="torax_mama"])' % b)
    await pg.wait_for_timeout(300)
    checar(u"  e voltar ao Tórax / Mama troca de novo, sem passar pela Seleção "
           u"livre", await _ligadas() == DELE and not await _livre(),
           str(await _ligadas()))

    previas = []

    def _anota_previa(req):
        if "/api/lote/previa_da_entrega" in req.url:
            try:
                previas.append(json.loads(req.post_data or u"{}"))
            except Exception:
                previas.append({})
    pg.on("request", _anota_previa)
    for _ in range(20):
        if await pg.locator("#p4e_%d [data-oar-x]" % b).count():
            break
        await pg.wait_for_timeout(300)
    n_tags = await pg.locator("#p4e_%d .oar-tag:not(.fora)" % b).count()
    checar(u"as entregas chegam do servidor, com o OAR em tags", n_tags >= 10,
           u"%d tag(s)" % n_tags)
    arq = await pg.evaluate(
        "Array.from(document.querySelectorAll('#p4e_%d .ent-arq .ent-rot')).map("
        "function(x){ return x.textContent })" % b)
    checar(u"  e os arquivos que vao sair (o OAR e o FULL, no minimo)",
           len(arq) >= 2, str(arq))
    alvo = await pg.evaluate(
        "(function(i){ var b = document.querySelector('#p4e_' + i + ' [data-oar-x=\"heart\"]')"
        " || document.querySelector('#p4e_' + i + ' [data-oar-x]');"
        " return b.getAttribute('data-oar-x') })(%d)" % b)
    previas[:] = []
    await pg.click('#p4e_%d [data-oar-x="%s"]' % (b, alvo))
    await pg.wait_for_timeout(1800)
    fora_dom = await pg.evaluate(
        "Array.from(document.querySelectorAll('#p4e_%d [data-oar-volta]')).map("
        "function(x){ return x.getAttribute('data-oar-volta') })" % b)
    fica = await pg.locator('#p4e_%d [data-oar-x="%s"]' % (b, alvo)).count()
    checar(u"o «x» tira a tag `%s` do OAR (ela vai para a linha de fora)" % alvo,
           fora_dom == [alvo] and fica == 0, u"fora=%s ainda=%d" % (fora_dom, fica))
    pl = await pg.evaluate("payloadDaSerie(SERIES[%d])" % b)
    checar(u"  e o payload da serie leva `oar_fora`",
           pl.get("oar_fora") == [alvo], str(pl.get("oar_fora")))
    enviada = [p.get("serie", {}).get("oar_fora") for p in previas]
    checar(u"  e a previa que foi ao servidor tambem",
           bool(enviada) and enviada[-1] == [alvo], str(enviada))
    await pg.evaluate(
        "window.__tr = _tirarDoOar; _tirarDoOar = function(bt, tirar){"
        " var t = bt.closest('.oar-tag'); if(t) t.parentNode.removeChild(t) }; true")
    outro = await pg.evaluate(
        "document.querySelector('#p4e_%d [data-oar-x]').getAttribute('data-oar-x')" % b)
    await pg.click('#p4e_%d [data-oar-x="%s"]' % (b, outro))
    isca_x = await pg.evaluate("payloadDaSerie(SERIES[%d]).oar_fora" % b)
    await pg.evaluate("_tirarDoOar = window.__tr; true")
    checar(u"  (isca) o «x» que so apaga a tag nao chega ao payload -- a "
           u"checagem discrimina", outro not in (isca_x or []), str(isca_x))
    await pg.click('#p4e_%d [data-oar-volta="%s"]' % (b, alvo))
    await pg.wait_for_timeout(1500)
    checar(u"  e o «+» devolve a estrutura ao OAR",
           (await pg.evaluate("payloadDaSerie(SERIES[%d]).oar_fora" % b)) == [],
           u"")
    pg.remove_listener("request", _anota_previa)

    await pg.click('#perso_%d [data-p4-aj="task"][data-cod="abdominal_muscles"]' % b)
    await pg.wait_for_timeout(600)
    ficha = await pg.evaluate(
        "(function(){ var bs = document.querySelectorAll('.ui-pnl .tk-b');"
        " var f = bs[bs.length - 1]; if(!f) return null;"
        " return {f: Array.from(f.querySelectorAll('[data-f]')).map(function(x){"
        "  return x.getAttribute('data-f') }),"
        "  vel: !!f.querySelector('[data-f=\"tempo\"] .selo-vel')} })()")
    checar(u"o `?` da task abre a ficha: o tempo (a etiqueta), o que alimenta, "
           u"o modelo de origem, a versao, a task e o que ela segmenta",
           bool(ficha) and ficha["vel"] and all(
               k in ficha["f"] for k in (u"tempo", u"alimenta", u"modelo",
                                         u"versao", u"task", u"segmenta")),
           str(ficha))
    await pg.keyboard.press("Escape")
    await pg.wait_for_timeout(400)

    modos = await pg.evaluate(
        "[payloadDaSerie(SERIES[%d]).modo, payloadDaSerie(SERIES[%d]).modo,"
        " payloadDaSerie(SERIES[%d]).modo]" % (a, b, c))
    checar(u"cada serie viaja com o SEU modo", modos == [u"fast", u"perso", u"auto"],
           str(modos))
    pa = await pg.evaluate("payloadDaSerie(SERIES[%d])" % a)
    checar(u"  e FAST e AUTO nao levam protocolo, chave nem `oar_fora`",
           not any(k in pa for k in ("protocolos", "tasks", "comparacao", "oar_fora")),
           str(sorted(pa)))

    secao(u"adicionar a fila nao pergunta nada")
    await pg.evaluate("filaOvernight(false)")
    await pg.evaluate("limparSelecao()")
    antes_fila = await pg.locator("#radai_fila .cd").count()
    await pg.evaluate("if(!noCarrinho(SERIES[%d])) alternar(%d)" % (b, b))
    await pg.click("#btrodar")
    await pg.wait_for_timeout(900)
    dialogo_1 = await pg.locator(".ui-pnl-veu.vis").count()
    checar(u"a primeira adicao nao abre dialogo nenhum", dialogo_1 == 0,
           u"%d painel(is) aberto(s)" % dialogo_1)
    if dialogo_1:
        await pg.keyboard.press("Escape")
        await pg.wait_for_timeout(300)
    await _encher_pasta(pg, os.path.join(root, "PAC_C"))
    await pg.click('button[onclick="varrer()"]')
    await pg.wait_for_timeout(3500)
    await pg.evaluate("if(!noCarrinho(SERIES[0])) alternar(0)")
    await pg.evaluate("escolhaDe(SERIES[0]).modo = 'auto'; pintarTabela(); true")
    await pg.click("#btrodar")
    await pg.wait_for_timeout(900)
    dialogo_2 = await pg.locator(".ui-pnl-veu.vis").count()
    checar(u"  e a segunda tambem nao", dialogo_2 == 0,
           u"%d painel(is) aberto(s)" % dialogo_2)
    if dialogo_2:
        await pg.keyboard.press("Escape")
        await pg.wait_for_timeout(300)
    depois_fila = await pg.locator("#radai_fila .cd").count()
    checar(u"  e a fila ganhou os dois cards",
           depois_fila == antes_fila + 2, u"%d -> %d" % (antes_fila, depois_fila))
    checar(u"  e a selecao esvaziou sozinha",
           await pg.evaluate("carrinhoLista().length") == 0)
    rv = await pg.evaluate(
        "fetch('/api/pipeline/revisao').then(function(r){return r.json()})")
    estudos = dict((m.get("cod"), m.get("n"))
                   for m in ((rv or {}).get("revisao") or {}).get("estudos")
                   or ())
    checar(u"o modo de CADA serie chegou ao servidor (a conferencia soma)",
           estudos.get(u"perso") == 1 and estudos.get(u"perso:torax_mama") == 1
           and estudos.get(u"auto") == 1 and u"" not in estudos, str(estudos))
    checar(u"  e a chave `modos` saiu da conferencia",
           "modos" not in ((rv or {}).get("revisao") or {}),
           str(sorted(((rv or {}).get("revisao") or {}).keys())))
    checar(u"  e a conferencia manda a lista de problemas (vazia aqui)",
           ((rv or {}).get("revisao") or {}).get("problemas") == [],
           str(((rv or {}).get("revisao") or {}).get("problemas")))

    secao(u"a conferencia desenha o que nao calculou")
    await pg.evaluate(
        "radaiRevAbrir({origem:'lote', n_series:2, series:[], mais:0,"
        " tasks:[], estudos:[], conjuntos:[], estacao:{}, aviso:'-', onde:'-',"
        " problemas:[{uid8:'40001111', o_que:'tasks', erro:'ValueError: x'},"
        "            {uid8:'40002222', o_que:'motores', erro:'KeyError: y'}]},"
        " null)")
    await pg.wait_for_timeout(200)
    n_falha = await pg.locator("#radai_rev .rev-falha").count()
    checar(u"o dialogo desenha uma linha por problema", n_falha == 2,
           u"%d linha(s)" % n_falha)
    checar(u"  e cada linha tem a FRASE num no proprio (casa a chave)",
           await pg.locator("#radai_rev .rev-falha [data-radai-frase]").count()
           == 2)
    await pg.evaluate("radaiRevFechar()")
    await pg.wait_for_timeout(150)

    secao(u"os cards da fila, legiveis e no lugar")
    caixas = await pg.evaluate(
        "Array.from(document.querySelectorAll('#radai_fila .cd')).map(function(c){"
        " var r=c.getBoundingClientRect(), t=c.querySelector('.cd-rot');"
        " var q=t?t.getBoundingClientRect():null;"
        " return {top:r.top,bottom:r.bottom,left:r.left,right:r.right,"
        "  rt:q?q.top:-1,rb:q?q.bottom:-1,txt:t?t.textContent.trim():''} })")
    pipe_bottom = await pg.evaluate(
        "document.querySelector('.radai-tarefas .pipe').getBoundingClientRect().bottom")
    checar(u"todo card tem o rotulo com texto", caixas and all(
        c["txt"] for c in caixas), str([c["txt"] for c in caixas]))
    checar(u"  e o rotulo esta DENTRO do proprio card",
           all(c["top"] - 1 <= c["rt"] and c["rb"] <= c["bottom"] + 1
               for c in caixas), str(caixas[:2]))
    checar(u"  e os cards estao abaixo dos botoes, um depois do outro",
           all(c["top"] >= pipe_bottom - 1 for c in caixas)
           and all(caixas[k]["top"] >= caixas[k - 1]["bottom"] - 1
                   for k in range(1, len(caixas))),
           u"pipe=%.0f cards=%s" % (pipe_bottom,
                                    [(round(c["top"]), round(c["bottom"]))
                                     for c in caixas]))

    secao(u"o X tira o card da fila")
    n0 = await pg.locator("#radai_fila .cd").count()
    await pg.click('#radai_fila .cd:nth-child(1) .bts button[onclick^="radaiFilaCancelarBt"]')
    await pg.wait_for_timeout(800)
    n1 = await pg.locator("#radai_fila .cd").count()
    checar(u"o card cancelado SAI da fila", n1 == n0 - 1, u"%d -> %d" % (n0, n1))
    checar(u"  e nao sobra card apagado de cancelado",
           (await pg.locator("#radai_fila .cd.cancelado").count()) == 0)

    secao(u"ver imagens abre e fecha pelo mesmo botao")
    tem_vi = (await pg.locator("#vi_0").count()) == 1
    if tem_vi:
        cortes_lote, aberturas = [], []

        def _anota_lote(req):
            if "/api/umeixo/corte" in req.url:
                cortes_lote.append(req.url)
            elif "/api/umeixo/abrir" in req.url:
                aberturas.append(req.url)
        pg.on("request", _anota_lote)
        await pg.evaluate("window.radaiRetraduzir && radaiRetraduzir()")
        r0 = (await pg.inner_text("#vi_0")).strip()
        await pg.click("#vi_0")
        await pg.wait_for_timeout(1500)
        await pg.evaluate("window.radaiRetraduzir && radaiRetraduzir()")
        r1 = (await pg.inner_text("#vi_0")).strip()
        checar(u"aberto, o botao troca o rotulo", r1 != r0 and r1,
               u"%r -> %r" % (r0, r1))
        checar(u"  e o texto «clique de novo» nao existe mais",
               u"clique de novo" not in (await pg.inner_text("#tab")))
        n_cortes = await pg.evaluate("SERIES[0].cortes")
        pedidos = _cortes_pedidos(cortes_lote)
        esperado = _bisseccao(n_cortes)[:3]
        checar(u"os tres primeiros cortes pedidos sao 50%, 25% e 75%",
               len(pedidos) >= 3 and pedidos[:3] == esperado,
               u"n=%s pedidos=%s esperado=%s" % (n_cortes, pedidos[:6], esperado))
        checar(u"  e cada corte uma vez so",
               len(pedidos) == len(set(pedidos)), str(pedidos[:12]))
        checar(u"  e o visor de um eixo esta na linha da serie",
               (await pg.locator("#prev_0 .ue-visor").count()) == 1)
        await pg.evaluate(
            "document.querySelector('#prev_0 .ue-caixa').__marca = 7;"
            " pintarTabela()")
        await pg.wait_for_timeout(400)
        mesma = await pg.evaluate(
            "(function(){ var c = document.querySelector('#prev_0 .ue-caixa');"
            " return !!c && c.__marca === 7 })()")
        checar(u"repintar a tabela devolve a MESMA caixa, sem abrir de novo",
               mesma and len(aberturas) == 1,
               u"mesma=%s aberturas=%d" % (mesma, len(aberturas)))
        await pg.click("#vi_0")
        await pg.wait_for_timeout(300)
        await pg.evaluate("window.radaiRetraduzir && radaiRetraduzir()")
        checar(u"fechar volta o rotulo e tira a previa",
               (await pg.inner_text("#vi_0")).strip() == r0
               and (await pg.locator("#prev_0").count()) == 0)
        checar(u"  e solta o visor (nenhuma caixa guardada)",
               await pg.evaluate("Object.keys(UM_EIXO_CAIXAS).length") == 0)
        pg.remove_listener("request", _anota_lote)
    else:
        checar(u"a serie tem o botao «ver imagens»", False,
               u"#vi_0 ausente -- a serie ja tinha RTSTRUCT?")

    secao(u"o seletor: busca, ida e volta")
    await pg.evaluate("fpAbrir()")
    await pg.wait_for_timeout(500)
    await pg.evaluate("fpNavegar(%r)" % root)
    await pg.wait_for_timeout(900)
    antes = await pg.locator("#fp_lista .fp_item").count()
    await pg.fill("#fp_busca", "PAC_C")
    await pg.wait_for_timeout(1000)
    depois = await pg.locator("#fp_lista .fp_item").count()
    checar(u"a busca filtra no servidor", depois < antes and depois >= 1,
           u"%d -> %d" % (antes, depois))
    conta = await pg.evaluate(
        "(function(){ var e=document.getElementById('fp_erro');"
        " return [e.querySelectorAll('b').length,"
        "  e.querySelectorAll('[data-radai-frase]').length] })()")
    checar(u"  e a conta da busca sai com o numero e a frase separados",
           conta[0] >= 1 and conta[1] >= 1, str(conta))
    await pg.evaluate("fpBuscarLimpar()")
    await pg.wait_for_timeout(800)
    checar(u"e limpar devolve a lista",
           (await pg.locator("#fp_lista .fp_item").count()) == antes)
    await pg.evaluate("fpNavegar(%r)" % os.path.join(root, "PAC_A"))
    await pg.wait_for_timeout(700)
    checar(u"o «voltar» acende depois de descer",
           await pg.is_enabled("#fp_bvolta"))
    await pg.evaluate("fpVoltar()")
    await pg.wait_for_timeout(700)
    checar(u"  e ele volta mesmo",
           (await pg.input_value("#fp_cam")).rstrip("\\/") == root.rstrip("\\/"),
           await pg.input_value("#fp_cam"))
    checar(u"  e o «avancar» acende", await pg.is_enabled("#fp_bfrente"))
    n_nos = await pg.locator("#fp_arvore .fp-no").count()
    checar(u"as particoes estao na arvore da esquerda", n_nos >= 1,
           u"%d no(s)" % n_nos)
    datas = await pg.evaluate(
        "Array.from(document.querySelectorAll('#fp_lista .fp_item .fp-d'))"
        ".map(function(d){ return d.textContent })")
    import re as _re
    checar(u"cada pasta da lista mostra a data de modificacao",
           datas and all(_re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$", d)
                         for d in datas), str(datas[:3]))
    await pg.click("#fp_odata")
    await pg.wait_for_timeout(700)
    checar(u"ordenar por data acende o botao, da mais recente para a antiga",
           await pg.get_attribute("#fp_odata", "aria-pressed") == u"true"
           and await pg.get_attribute("#fp_odata", "data-sentido") == u"desc")
    await pg.click("#fp_onome")
    await pg.wait_for_timeout(700)
    nomes = await pg.evaluate(
        "Array.from(document.querySelectorAll('#fp_lista .fp_item .fp-n'))"
        ".map(function(d){ return d.textContent.trim() })")
    checar(u"  e por nome volta a ordem alfabetica",
           nomes == sorted(nomes, key=lambda s: s.lower()), str(nomes))
    await pg.click("#fp_onome")
    await pg.wait_for_timeout(700)
    nomes2 = await pg.evaluate(
        "Array.from(document.querySelectorAll('#fp_lista .fp_item .fp-n'))"
        ".map(function(d){ return d.textContent.trim() })")
    checar(u"  e o segundo clique no mesmo botao inverte",
           nomes2 == list(reversed(nomes)), str(nomes2))
    await pg.click("#fp_arvore .fp-no .fp-tg")
    await pg.wait_for_timeout(1200)
    checar(u"o triangulo da arvore abre os filhos da unidade",
           await pg.evaluate(
               "(function(){ var f=document.querySelector('#fp_arvore .fp-filhos');"
               " var t=document.querySelector('#fp_arvore .fp-tg');"
               " return !!f && (!f.hidden || (t && t.disabled)) })()"))
    await pg.evaluate("fpFechar()")

    secao(u"a fila de cards")
    n_antes = await pg.locator("#radai_fila .cd").count()
    await pg.evaluate("filaOvernight()")
    await pg.wait_for_timeout(900)
    rot = await pg.locator("#radai_fila .cd .cd-rot").all_inner_texts()
    turno = await pg.locator("#radai_fila .cd .tag.overnight").count()
    checar(u"o turno da noite entra na fila",
           turno == 1 and len(rot) == n_antes + 1, u"%s" % rot)
    checar(u"  e o card diz o nome",
           any(u"noite" in x.lower() or u"overnight" in x.lower() or
               u"night" in x.lower() for x in rot), u"%s" % rot)
    checar(u"  e ele e o ULTIMO da fila",
           await pg.evaluate(
               "(function(){ var c=document.querySelectorAll('#radai_fila .cd');"
               " return !!c.length && !!c[c.length-1].querySelector('.tag.overnight') })()"))
    await pg.evaluate("filaOvernight()")
    await pg.wait_for_timeout(900)
    checar(u"e sai com o segundo clique",
           (await pg.locator("#radai_fila .cd").count()) == n_antes)

    secao(u"o modal do turno: Cancelar e Salvar e iniciar (v8.4)")
    pedidos_ov, iniciou = [], []

    async def _fila_ov_de_verdade(route):
        try:
            pedidos_ov.append(json.loads(route.request.post_data or "{}"))
        except Exception:
            pedidos_ov.append({})
        await route.continue_()

    async def _turno_dublado(route):
        iniciou.append(1)
        await route.fulfill(status=200, content_type="application/json",
                            body=json.dumps({"ok": True, "recarga_pendente": True,
                                             "pausados": [], "n_pausados": 0,
                                             "servicos": []}))
    pipe = []

    async def _pipe_dublada(route):
        pipe.append(1)
        await route.fulfill(status=200, content_type="application/json",
                            body=json.dumps({"ok": True}))
    await pg.route("**/api/overnight/iniciar", _turno_dublado)
    await pg.route("**/api/fila/overnight", _fila_ov_de_verdade)
    await pg.route("**/api/pipeline/iniciar", _pipe_dublada)
    await pg.evaluate("localStorage.setItem('radai_idioma', 'pt-BR'); true")
    try:
        await pg.evaluate("folhaOvernight()")
        await pg.wait_for_timeout(1800)
        campo = await pg.input_value(".ui-pnl #ov_root")
        checar(u"o modal abre com a pasta GRAVADA no campo", campo == root,
               campo)
        checar(u"  e o terceiro botao («Iniciar sem salvar») nao existe mais",
               (await pg.locator("#ov_bt_sem").count()) == 0)
        checar(u"  e «Salvar e iniciar» nasce habilitado (a pasta passa no laudo)",
               await pg.is_enabled("#ui-pnl-sim"))
        await pg.fill(".ui-pnl #ov_root", os.path.join(root, "NAO_EXISTE"))
        await pg.wait_for_timeout(1800)
        checar(u"a pasta que nao passa no laudo desabilita «Salvar e iniciar»",
               await pg.is_disabled("#ui-pnl-sim"))
        await pg.fill(".ui-pnl #ov_root", root)
        await pg.wait_for_timeout(1800)
        checar(u"com a pasta de volta, «Salvar e iniciar» volta a valer",
               await pg.is_enabled("#ui-pnl-sim"))
        frente = await pg.evaluate(
            "fetch('/api/fila').then(function(r){ return r.json() })"
            ".then(function(d){ return (d.cards || []).some(function(c){"
            " return c.tipo === 'serie' && (c.estado === 'esperando'"
            " || c.estado === 'rodando') }) })")
        await pg.evaluate("_ovSemBotao(); OV.painel && OV.painel.fechar && OV.painel.fechar();"
                          " _ovPorNaFila(true).catch(function(){}); true")
        await pg.wait_for_timeout(1500)
        corpo = pedidos_ov[-1] if pedidos_ov else {}
        checar(u"o card do turno vai a fila, sem valores de uma noite so",
               corpo.get("ligado") is True and "temporarios" not in corpo,
               str(corpo))
        tx = await pg.inner_text("#cd_night_tx")
        checar(u"  com serie na frente, o card espera a vez e o turno NAO e "
               u"pedido agora", frente is True and not iniciou,
               u"%s | %s" % (frente, tx))
        checar(u"  e a fila, que estava PARADA, e iniciada pelo mesmo clique "
               u"(a rota do «Iniciar» da barra), e o cartao diz",
               len(pipe) == 1 and u"estava parada e foi iniciada" in tx,
               u"%d | %s" % (len(pipe), tx))
        await pg.evaluate("window.__fa = _ovFilaAnda;"
                          " _ovFilaAnda = function(){ return true }; true")
        await pg.evaluate("_ovPorNaFila(true, null).catch(function(){}); true")
        await pg.wait_for_timeout(1200)
        tx_isca = await pg.inner_text("#cd_night_tx")
        await pg.evaluate("_ovFilaAnda = window.__fa; true")
        checar(u"    (isca) com a fila tida como andando, nada e iniciado e o "
               u"card so espera -- a checagem discrimina", len(pipe) == 1
               and u"quando a fila chegar nele" in tx_isca,
               u"%d | %s" % (len(pipe), tx_isca))
        await pg.evaluate("filaOvernight(false)")
        await pg.wait_for_timeout(700)

        await pg.unroute("**/api/fila/overnight")

        async def _fila_so_o_turno(route):
            await route.fulfill(status=200, content_type="application/json",
                                body=json.dumps({"cards": [
                                    {"tipo": "overnight", "estado": "esperando",
                                     "rotulo": u"Turno da noite", "uid": u""}],
                                    "resumo": {}}))
        await pg.route("**/api/fila/overnight", _fila_so_o_turno)
        async def _fila_com_o_turno_aberto(route):
            try:
                resp = await route.fetch()
                j = await resp.json()
            except Exception:
                j = {"cards": [], "resumo": {}}
            cards = [c for c in (j.get("cards") or [])
                     if c.get("tipo") != "overnight"]
            cards.append({"tipo": "overnight", "estado": "feito",
                          "rotulo": u"Turno da noite", "uid": u"",
                          "motivo": u"turno aberto"})
            j["cards"] = cards
            await route.fulfill(status=200, content_type="application/json",
                                body=json.dumps(j))

        async def _status_com_o_turno_aberto(route):
            try:
                resp = await route.fetch()
                j = await resp.json()
            except Exception:
                j = {}
            j["overnight"] = True
            j["recarga_pendente"] = True
            await route.fulfill(status=200, content_type="application/json",
                                body=json.dumps(j))
        await pg.route("**/api/fila", _fila_com_o_turno_aberto)
        await pg.route("**/api/status", _status_com_o_turno_aberto)
        await pg.evaluate("ovIniciar(false, _ovValores(), true, {DAYS_BACK: '7'})")
        await pg.wait_for_timeout(1200)
        tx = await pg.inner_text("#cd_night_tx")
        checar(u"sem serie na frente, a tela pede o turno na hora",
               len(iniciou) == 1, str(len(iniciou)))
        checar(u"  e o cartao DIZ que a configuracao nova ainda nao valeu "
               u"(recarga pendente)",
               u"vale quando a série em curso terminar" in tx, tx)
        await pg.evaluate("filaEstado(); true")
        await pg.wait_for_timeout(900)
        tx = await pg.inner_text("#cd_night_tx")
        checar(u"  e continua dizendo depois da volta do pintor de 15 s "
               u"(filaEstado le a fila e o status)",
               u"vale quando a série em curso terminar" in tx, tx)
    finally:
        await pg.unroute("**/api/fila")
        await pg.unroute("**/api/status")
        await pg.unroute("**/api/fila/overnight")
        await pg.unroute("**/api/overnight/iniciar")
        await pg.unroute("**/api/pipeline/iniciar")
        await pg.evaluate("localStorage.removeItem('radai_idioma'); true")
        await pg.keyboard.press("Escape")
        await pg.evaluate("filaOvernight(false)")
        await pg.wait_for_timeout(700)
    checar(u"e o card do turno saiu da fila de verdade",
           (await pg.locator("#radai_fila .cd .tag.overnight").count()) == 0)

    secao(u"a barra da direita: abas Fila | Log")
    abas = await pg.evaluate(
        "Array.from(document.querySelectorAll('.radai-tarefas .dir-aba')).map("
        "function(b){ return [b.getAttribute('data-aba'), b.getAttribute('aria-selected')] })")
    checar(u"duas abas, Fila e Log, e a Fila nasce escolhida",
           abas == [[u"fila", u"true"], [u"log", u"false"]], str(abas))
    checar(u"  a Fila visivel e o Log oculto",
           await pg.is_visible("#radai_fila")
           and not await pg.is_visible("#radai_tf_pn_l"))
    alt = await pg.evaluate(
        "(function(){ var a = document.querySelector('.radai-tarefas');"
        " var t = document.querySelector('.radai-tarefas .dir-abas');"
        " var f = document.getElementById('radai_tf_reg_fila');"
        " return [a.getBoundingClientRect().height, t.getBoundingClientRect().height,"
        "  f.getBoundingClientRect().height] })()")
    checar(u"a aba da Fila ocupa a altura inteira da barra",
           abs(alt[0] - alt[1] - alt[2]) <= 3,
           u"barra=%.0f abas=%.0f fila=%.0f" % tuple(alt))
    _erro = ("radaiTfLogRecebeu({linhas:[{t:'23:41:07', nivel:'erro',"
             " txt:'FALHOU serie ...12345678'}], proximo: RADAI_TF_LOG_N,"
             " estado:'ok'}); true")
    await pg.evaluate(_erro)
    await pg.wait_for_timeout(300)
    checar(u"a linha de erro que chega com a Fila aberta acende o ponto da aba Log",
           (await pg.locator("#radai_tf_ab_log_rot .ui-ponto").count()) == 1)
    await pg.click("#radai_tf_ab_log")
    await pg.wait_for_timeout(500)
    checar(u"  e abrir a aba Log apaga o ponto",
           (await pg.locator("#radai_tf_ab_log_rot .ui-ponto").count()) == 0)
    checar(u"  e mostra o log (e esconde a fila)",
           await pg.is_visible("#radai_tf_log") and not await pg.is_visible("#radai_fila"))
    await pg.evaluate(_erro)
    await pg.wait_for_timeout(300)
    checar(u"  e erro que chega com o Log aberto nao acende",
           (await pg.locator("#radai_tf_ab_log_rot .ui-ponto").count()) == 0)
    await pg.click("#radai_tf_ab_fila")
    await pg.evaluate("window.__pl = radaiTfPontoLog; radaiTfPontoLog = function(){}; true")
    await pg.evaluate(_erro)
    await pg.wait_for_timeout(300)
    isca_ponto = await pg.locator("#radai_tf_ab_log_rot .ui-ponto").count()
    await pg.evaluate("radaiTfPontoLog = window.__pl; true")
    checar(u"  (isca) sem a funcao do ponto, nada acende -- a checagem discrimina",
           isca_ponto == 0, str(isca_ponto))
    await pg.focus("#radai_tf_ab_fila")
    await pg.keyboard.press("ArrowRight")
    await pg.wait_for_timeout(200)
    checar(u"a seta para a direita leva a aba Log, com o foco",
           await pg.evaluate("document.activeElement.id") == u"radai_tf_ab_log"
           and await pg.get_attribute("#radai_tf_ab_log", "aria-selected") == u"true")
    linhas = await pg.evaluate(
        "document.getElementById('radai_tf_log').children.length")
    checar(u"e o LOG esta batendo", linhas > 1, u"%d linha(s)" % linhas)
    cor = await pg.evaluate(
        "getComputedStyle(document.getElementById('radai_tf_pt'))"
        ".backgroundColor")
    checar(u"e o ponto de vida esta colorido",
           cor not in ("rgb(107, 122, 146)", "rgb(114, 130, 155)",
                       "rgba(0, 0, 0, 0)"), cor)
    await pg.click("#radai_tf_ab_fila")
    await pg.wait_for_timeout(300)
    await pg.evaluate(
        "window.__notif = []; window.Notification = function(t, o){"
        " window.__notif.push(o.body) }; window.Notification.permission = 'granted';"
        " window.__somN = 0; window.__som = radaiSom; radaiSom = function(){ window.__somN++ };"
        " RADAI_AVISO_ANTES = null;"
        " var c = function(e){ return {tipo:'serie', uid:'87654321', estado:e,"
        "  rotulo:'NOME DO PACIENTE'} };"
        " radaiAvisosDaFila({cards:[c('rodando')]});"
        " radaiAvisosDaFila({cards:[c('pronto')]}); true")
    notif = await pg.evaluate("window.__notif")
    som = await pg.evaluate("window.__somN")
    await pg.evaluate("radaiSom = window.__som; true")
    checar(u"a serie que termina toca o som e abre a notificacao",
           som == 1 and len(notif) == 1 and u"87654321" in notif[0],
           u"som=%s notif=%s" % (som, notif))
    checar(u"  e a notificacao nao leva o nome do paciente",
           bool(notif) and u"NOME" not in notif[0], str(notif))
    n_bt = await pg.locator(".radai-tarefas .pipe .pipe-bt").count()
    checar(u"os quatro botoes da fila estao la", n_bt == 4, u"%d" % n_bt)
    sombra = await pg.evaluate(
        "(function(){ var b=document.getElementById('radai_pipe_can');"
        " return [b.disabled, getComputedStyle(b).boxShadow] })()")
    checar(u"  e o desabilitado e plano (sem a sombra do relevo)",
           (not sombra[0]) or sombra[1] in (u"none", u""), str(sombra))

    secao(u"a tela em 375 px")
    await pg.set_viewport_size({"width": 375, "height": 812})
    await pg.goto(BASE + "/lote", wait_until="networkidle")
    await pg.wait_for_timeout(900)
    larg = await pg.evaluate(
        "[document.documentElement.scrollWidth, window.innerWidth]")
    checar(u"em 375 px a pagina nao rola de lado", larg[0] <= larg[1] + 1,
           u"scrollWidth=%d innerWidth=%d" % (larg[0], larg[1]))
    await _encher_pasta(pg, os.path.join(root, "PAC_A"))
    await pg.evaluate("varrer()")
    await pg.wait_for_timeout(3500)
    if (await pg.locator("#vi_0").count()) == 1:
        await pg.evaluate("verNoPasso4(0)")
        await pg.wait_for_timeout(1200)
        caixa = await pg.evaluate(
            "(function(){ var i = document.querySelector('#prev_0 .ue-img');"
            " var q = document.querySelector('#prev_0 .ue-visor');"
            " if(!i || !q) return null; var r = q.getBoundingClientRect();"
            " return [i.offsetWidth, i.offsetHeight, r.left, r.right,"
            " window.innerWidth] })()")
        checar(u"a 375 px a imagem do visor e quadrada pela largura",
               caixa and caixa[1] <= caixa[0] + 2 and caixa[1] < 400,
               str(caixa))
        checar(u"  e cabe na janela, sem rolar a tabela de lado",
               caixa and caixa[2] >= 0 and caixa[3] <= caixa[4] + 1,
               str(caixa))
        await pg.evaluate("verNoPasso4(0)")
    else:
        checar(u"a 375 px a serie tem o botao «ver imagens»", False,
               u"#vi_0 ausente")
    await pg.set_viewport_size({"width": 1520, "height": 950})

    secao(u"o visor do DicomBridge chega por bisseccao")
    cortes_ponte = []

    def _anota_ponte(req):
        if "/api/bridge/corte" in req.url:
            cortes_ponte.append(req.url)
    pg.on("request", _anota_ponte)
    await pg.goto(BASE + "/bridge/laudo", wait_until="networkidle")
    await pg.wait_for_timeout(500)
    await pg.fill("#dc_pasta", os.path.join(root, "PAC_A"))
    await pg.evaluate("dcVarrer()")
    await pg.wait_for_timeout(3000)
    n_ponte = await pg.evaluate("(DC.series[0] || {}).cortes || 0")
    checar(u"a pasta tem a serie fantoma", n_ponte > 3, str(n_ponte))
    await pg.evaluate("dcEtapa(3); dcAbrir(0)")
    await pg.wait_for_timeout(1500)
    pedidos = _cortes_pedidos(cortes_ponte)
    esperado = _bisseccao(n_ponte)[:3]
    checar(u"os tres primeiros cortes pedidos sao 50%, 25% e 75%",
           len(pedidos) >= 3 and pedidos[:3] == esperado,
           u"n=%s pedidos=%s esperado=%s" % (n_ponte, pedidos[:6], esperado))
    checar(u"  e cada corte uma vez so", len(pedidos) == len(set(pedidos)),
           str(pedidos[:12]))
    await pg.wait_for_timeout(800)
    medidas = await pg.evaluate(
        "(function(){ var l = document.getElementById('dc_laudo');"
        " var v = document.getElementById('dc_visor');"
        " var a = l.getBoundingClientRect(), b = v.getBoundingClientRect();"
        " return [a.width, b.width, a.top >= b.bottom - 1] })()")
    checar(u"o laudo tem a largura da coluna, e nao ~30 px",
           medidas[0] >= 0.9 * medidas[1] and medidas[0] > 250,
           u"laudo=%.0f visor=%.0f" % (medidas[0], medidas[1]))
    checar(u"  e fica embaixo do visor", medidas[2], str(medidas))
    await pg.evaluate("DC.visor.ir(2)")
    await pg.wait_for_timeout(300)
    antes = len(cortes_ponte)
    onde = await pg.evaluate("DC.visor.atual")
    await pg.evaluate("dcJanela('osso')")
    await pg.wait_for_timeout(600)
    novo = cortes_ponte[antes] if len(cortes_ponte) > antes else u""
    checar(u"trocar a janela abre no MESMO corte, na janela nova",
           _cortes_pedidos([novo]) == [onde] and u"janela=osso" in novo,
           u"onde=%s novo=%s" % (onde, novo[-60:]))
    pg.remove_listener("request", _anota_ponte)

    secao(u"os selos saem na lingua da estacao (alemao)")
    await pg.evaluate("localStorage.setItem('radai_idioma', 'de'); true")
    try:
        await pg.goto(BASE + "/lote", wait_until="networkidle")
        await pg.wait_for_timeout(900)
        await _encher_pasta(pg, os.path.join(root, "PAC_A"))
        await pg.evaluate("varrer(); true")
        await pg.wait_for_timeout(3500)
        await pg.evaluate("if(!noCarrinho(SERIES[0])) alternar(0); true")
        await pg.wait_for_timeout(300)
        await pg.click('#linha_0 .ui-seg button[data-v="perso"]')
        await pg.wait_for_timeout(700)
        await pg.evaluate("window.radaiRetraduzir && radaiRetraduzir(); true")
        await pg.wait_for_timeout(300)
        achados = await pg.evaluate(
            "Array.from(document.querySelectorAll('#perso_0 .selo-achado'))"
            ".map(function(s){ return s.textContent })")
        base_t = await pg.evaluate("(OPC.CT && OPC.CT.base_item || {}).task || ''")
        _est_task = await pg.evaluate(
            "((OPC.CT && OPC.CT.tasks) || []).filter(function(t){"
            " return t.velocidade && !t.velocidade_medida && !t.motor })"
            ".map(function(t){ return t.task })[0] || ''")
        selos, ficha = {}, []
        for _t in (u"abdominal_muscles", base_t, _est_task):
            if not _t or not re.match(r"^[a-z0-9_]+$", _t):
                continue
            await pg.click('#perso_0 [data-p4-aj="task"][data-cod="%s"]' % _t)
            await pg.wait_for_timeout(500)
            await pg.evaluate("window.radaiRetraduzir && radaiRetraduzir(); "
                              "true")
            await pg.wait_for_timeout(300)
            selos[_t] = await pg.evaluate(
                "(function(){ var bs = document.querySelectorAll('.ui-pnl .tk-b');"
                " var b = bs[bs.length - 1];"
                " var s = b && b.querySelector('[data-f=\"tempo\"] .selo-vel');"
                " return s ? s.textContent : '' })()")
            if _t == _est_task:
                ficha = await pg.evaluate(
                    "(function(){ var bs = document.querySelectorAll('.tk-b');"
                    " var b = bs[bs.length - 1]; if(!b) return [];"
                    " return Array.from(b.querySelectorAll('.tk-v'))"
                    ".map(function(v){ return v.textContent }) })()")
            await pg.keyboard.press("Escape")
            await pg.wait_for_timeout(400)
        aj_nv = await pg.evaluate(
            "(function(){ var c = ((OPC.CT && OPC.CT.comparacao) || [])"
            ".filter(function(x){ return x.cod === 'nv' })[0];"
            " return c ? (c.ajuda || '') : '' })()")
        await pg.click('#perso_0 [data-p4-aj="comp"][data-cod="nv"]')
        await pg.wait_for_timeout(500)
        await pg.evaluate("window.radaiRetraduzir && radaiRetraduzir(); true")
        await pg.wait_for_timeout(300)
        ps_nv = await pg.evaluate(
            "(function(){ var bs = document.querySelectorAll('.ui-pnl .tk-b');"
            " var b = bs[bs.length - 1]; if(!b) return null;"
            " return Array.from(b.querySelectorAll('p'))"
            ".map(function(p){ return p.textContent }) })()")
        await pg.keyboard.press("Escape")
        await pg.wait_for_timeout(400)
        isca_nv = await pg.evaluate(
            "(function(t){ var p = document.createElement('p');"
            " p.setAttribute('data-radai-frase', ''); p.textContent = t;"
            " document.body.appendChild(p); radaiRetraduzir();"
            " var r = p.textContent; p.remove(); return r })(%s)"
            % json.dumps(aj_nv, ensure_ascii=False))
        selos[u"total_v3"] = selos.get(base_t, u"")
        isca_ficha, molde = u"", {}
        if _est_task:
            isca_ficha = await pg.evaluate(
                "(function(){ var v = document.createElement('span');"
                " v.className = 'tk-v'; v.textContent = '~fast';"
                " document.body.appendChild(v); radaiRetraduzir();"
                " var t = v.textContent; v.remove(); return t })()")
        molde = await pg.evaluate(
            "(function(f){ var fora = [];"
            " [['sub', f], ['env', f], ['marc', f],"
            "  ['isca', f.replace('torch deste', 'torch daquele')]]"
            ".forEach(function(par){"
            "  var c = document.createElement('div');"
            "  var p = document.createElement('p');"
            "  if(par[0] === 'env') c.className = 'env';"
            "  if(par[0] === 'marc') c.setAttribute('data-radai-t', '1');"
            "  p.className = (par[0] === 'env' || par[0] === 'marc') ? ''"
            "   : 'sub';"
            "  p.textContent = par[1]; c.appendChild(p);"
            "  document.body.appendChild(c); fora.push([par[0], c, p]) });"
            " var s = document.createElement('span'); s.className = 'sub';"
            " var b1 = document.createElement('b');"
            " b1.textContent = 'Usar a GPU desta estação'; s.appendChild(b1);"
            " s.appendChild(document.createTextNode(' — ganho: x'));"
            " s.appendChild(document.createElement('br'));"
            " s.appendChild(document.createTextNode(f + ' '));"
            " var b2 = document.createElement('b');"
            " b2.textContent = 'Configurações'; s.appendChild(b2);"
            " var cs = document.createElement('div'); cs.appendChild(s);"
            " document.body.appendChild(cs); fora.push(['no', cs, s]);"
            " radaiRetraduzir();"
            " var r = {}; fora.forEach(function(x){"
            "  r[x[0]] = x[2].textContent; x[1].remove() });"
            " return r })(%s)" % json.dumps(_FRASE_DO_MOLDE,
                                            ensure_ascii=False))
    finally:
        await pg.evaluate("localStorage.removeItem('radai_idioma'); true")
    checar(u"em alemao, a etiqueta medida sai traduzida (a abdominal_muscles, "
           u"ultra-slow)", selos.get(u"abdominal_muscles") == u"sehr langsam",
           str(selos.get(u"abdominal_muscles")))
    checar(u"  e a da base tambem (slow)",
           selos.get(u"total_v3") == u"langsam", str(selos.get(u"total_v3")))
    _est = [v for v in selos.values() if v.startswith(u"~")]
    checar(u"  e a estimada guarda o `~` na frente da palavra traduzida",
           bool(_est) and all(v[1:] in (u"schnell", u"mittel", u"langsam")
                              for v in _est), str(_est[:4]))
    checar(u"  e o selo de ACHADO diz BEFUND, em todas as caixas dele",
           bool(achados) and all(a == u"BEFUND" for a in achados),
           str(achados))
    sys.path.insert(0, os.path.join(RAIZ, "app"))
    try:
        import radai_phrases as _F
        _de = _F.construir()["de"]
    finally:
        sys.path.pop(0)
    _linhas_nv = [l for l in aj_nv.split(u"\n") if l]
    _nota = u"Cada modelo grava um arquivo próprio; nenhum entra no RadAI_OAR."
    checar(u"o `?` do motor de comparacao (NV) tem as DUAS linhas da ajuda, "
           u"cada uma no seu <p>, e a nota de que cada modelo grava o seu arquivo",
           len(_linhas_nv) == 2 and len(ps_nv or []) == 3,
           u"ajuda=%r p=%r" % (aj_nv[:60], ps_nv))
    checar(u"  e as tres saem em alemao, pela chave de cada linha",
           len(_linhas_nv) == 2 and all(l in _de for l in _linhas_nv + [_nota])
           and ps_nv == [_de[l] for l in _linhas_nv + [_nota]],
           str(ps_nv)[:160])
    checar(u"  (isca) a forma de antes -- as duas linhas num <p> so -- fica em "
           u"portugues no mesmo tradutor", bool(aj_nv) and isca_nv == aj_nv,
           str(isca_nv)[:120])

    def _estimada_traduzida(v):
        return (v.startswith(u"~") and v[1:] in (u"schnell", u"mittel",
                                                  u"langsam", u"sehr langsam"))
    _vel_ficha = [v for v in ficha if v.startswith(u"~")]
    checar(u"a FICHA (o `?`) de uma task estimada tambem traduz a etiqueta, "
           u"com o `~` na frente (%s)" % _est_task,
           bool(_vel_ficha) and all(_estimada_traduzida(v)
                                    for v in _vel_ficha), str(ficha[:8]))
    checar(u"  (isca) a forma de antes -- o `~` colado num no so -- continua "
           u"sem traducao no mesmo navegador",
           isca_ficha == u"~fast" and not _estimada_traduzida(isca_ficha),
           repr(isca_ficha))
    checar(u"a frase com o nome da placa sai em alemao pelo MOLDE, com os "
           u"valores intactos",
           bool(_FRASE_DO_MOLDE_DE) and molde.get("sub") == _FRASE_DO_MOLDE_DE
           and all(v in molde.get("sub", u"") for v in _VALORES_DO_MOLDE),
           (molde.get("sub") or u"(vazio)")[:90])
    checar(u"  e tambem como NO DE TEXTO no meio de um `.sub` com <b> e <br> "
           u"(a forma da tela do limpador: quem traduz e o passo 2)",
           bool(_FRASE_DO_MOLDE_DE)
           and _FRASE_DO_MOLDE_DE in molde.get("no", u"")
           and _FRASE_DO_MOLDE not in molde.get("no", u""),
           (molde.get("no") or u"(vazio)")[:120])
    checar(u"  e dentro do conteiner dos documentos (`.env`) fica em "
           u"portugues", bool(_FRASE_DO_MOLDE)
           and molde.get("env") == _FRASE_DO_MOLDE,
           (molde.get("env") or u"(vazio)")[:60])
    checar(u"  e debaixo de `data-radai-t=\"1\"` tambem",
           bool(_FRASE_DO_MOLDE) and molde.get("marc") == _FRASE_DO_MOLDE,
           (molde.get("marc") or u"(vazio)")[:60])
    checar(u"  (isca) a parte fixa mexida nao casa molde nenhum: fica em "
           u"portugues",
           bool(_FRASE_DO_MOLDE) and molde.get("isca")
           == _FRASE_DO_MOLDE.replace(u"torch deste", u"torch daquele"),
           (molde.get("isca") or u"(vazio)")[:60])

    secao(u"os documentos legais nao passam pelo dicionario (alemao)")
    try:
        pt = await _documentos_em(pg, u"pt-BR")
        de = await _documentos_em(pg, u"de")
    finally:
        await pg.evaluate("localStorage.removeItem('radai_idioma'); true")
    for rota in _DOCUMENTOS:
        doc_pt, topo_pt, _av = pt[rota]
        doc_de, topo_de, aviso_de = de[rota]
        checar(u"%s em alemao: o cabecalho troca de lingua (o tradutor "
               u"rodou na tela)" % rota,
               bool(topo_pt) and bool(topo_de) and topo_pt != topo_de,
               u"%r / %r" % ((topo_pt or u"")[:40], (topo_de or u"")[:40]))
        checar(u"  e o aviso de que o texto vale em portugues aparece",
               aviso_de)
        mudou = _trocas(doc_pt, doc_de)
        checar(u"  e o texto do documento sai IGUAL ao portugues (nenhum "
               u"pedaco trocado pelo dicionario)",
               bool(doc_pt) and not mudou,
               u"; ".join(u"%s -> %s" % (a[:30], b[:30])
                          for a, b in mudou[:8]))
    _isca = _trocas(u"o log anuncia com a palavra ACHADO , o que ela devolve",
                    u"o log anuncia com a palavra BEFUND , o que ela devolve")
    checar(u"  (isca) a comparacao acusa a palavra trocada, e so ela",
           _isca == [(u"ACHADO", u"BEFUND")], str(_isca))

    await _buracos_da_l3(pg, root)
    await _ver_em_alemao(pg, root)
    await _ver_acervo_cabe(pg)
    await _cartoes_pelo_teclado(pg)
    await _tema_claro_legivel(pg, root)
    await _onda_4b(pg, root)
    await _temas_nas_telas(pg, root)

    secao(u"nenhum erro de JavaScript")
    return True


_JS_QUADROS = u"""(() => {
  const Q = window.__radaiQuadros = [];
  const t0 = performance.now();
  function amostra(){
    const r = document.documentElement;
    if(r){
      const c = r.classList;
      Q.push({t: Math.round(performance.now() - t0),
              barra: r.hasAttribute('data-dir-sozinha'),
              dir: !c.contains('dir-recolhida'),
              abr: c.contains('dir-abrindo'), fech: c.contains('dir-fechando'),
              lado: r.getAttribute('data-trilho') === 'aberto',
              ladoAbr: c.contains('lado-abrindo')});
    }
    if(performance.now() - t0 < 3000) requestAnimationFrame(amostra);
  }
  requestAnimationFrame(amostra);
})();"""

TELAS_COM_BARRA = ("/autocontorno", "/lote", "/ver", "/bridge", "/bridge/laudo",
                   "/bridge/imagem", "/recon3d", "/recon3d/anatomia", "/nidus",
                   "/nidus/projecao", "/elastic", "/elastic/fusao", "/bolus",
                   "/bolus/gerar", "/config")
ABREM_SOZINHAS = ("/lote", "/ver")

_JS_ANIMACAO = u"""(sel) => { const e = document.querySelector(sel);
  if(!e) return null; const s = getComputedStyle(e);
  return [s.animationName, s.animationDuration, s.animationTimingFunction]; }"""


def _piscou(q, chave="dir"):
    visto = False
    for x in q:
        if x.get(chave):
            visto = True
        elif visto:
            return True
    return False


def _nasce_recolhida_no_html(texto, sozinha):
    m = re.search(r"<html\b[^>]*>", texto or u"", re.I)
    if not m:
        return False
    tag = m.group(0)
    c = re.search(r"\sclass=\"([^\"]*)\"", tag)
    return (bool(c) and u"dir-recolhida" in c.group(1).split()
            and (u'data-dir-sozinha="%s"' % (u"1" if sozinha else u"0")) in tag)


async def _quadros(p, rota, espera=1300):
    await p.goto(BASE + rota, wait_until="domcontentloaded")
    await p.wait_for_timeout(espera)
    return await p.evaluate("window.__radaiQuadros || []")


def _resumo(q, chave="dir"):
    return u"".join(u"1" if x.get(chave) else u"0" for x in q[:40])


async def _barras_laterais(pg):
    secao(u"as barras laterais: nascem no estado certo, sem piscar, com o panel reveal")
    p = await pg.context.new_page()
    erros = []
    p.on("pageerror", lambda e: erros.append(str(e)[:160]))
    await p.add_init_script(_JS_QUADROS)
    try:
        ruins = []
        for rota in TELAS_COM_BARRA:
            r = await p.request.get(BASE + rota)
            if not _nasce_recolhida_no_html(await r.text(), rota in ABREM_SOZINHAS):
                ruins.append(rota)
        checar(u"todo HTML servido com a barra traz a barra direita recolhida no <html>",
               not ruins, u", ".join(ruins))
        checar(u"  (isca) o <html> sem a marca seria acusado",
               not _nasce_recolhida_no_html(u'<html lang="pt"><head>', False)
               and not _nasce_recolhida_no_html(
                   u'<html class="dir-recolhida" data-dir-sozinha="0">', True))

        secao(u"a barra direita, sem pedido do usuário (aba nova)")
        roteiro = list(TELAS_COM_BARRA) + [u"/ver"]
        anterior_aberta = False
        for rota in roteiro:
            q = await _quadros(p, rota)
            if not q:
                checar(u"%s: o primeiro quadro foi amostrado" % rota, False)
                continue
            if rota in ABREM_SOZINHAS:
                if anterior_aberta:
                    ok = q[0]["dir"] and all(x["dir"] for x in q) and not any(
                        x["abr"] for x in q)
                    oque = u"vinda de outra que abre sozinha, já nasce aberta, sem animar"
                else:
                    ok = (not q[0]["dir"]) and q[-1]["dir"] and any(
                        x["abr"] for x in q)
                    oque = u"nasce recolhida e se expande sozinha, animada"
                anterior_aberta = True
            else:
                ok = q[0]["barra"] and not any(x["dir"] for x in q)
                oque = u"nasce recolhida e fica recolhida"
                anterior_aberta = False
            checar(u"%s: %s, sem piscar" % (rota, oque),
                   ok and not _piscou(q), _resumo(q))

        secao(u"a barra direita recolhida à mão continua recolhida")
        q = await _quadros(p, u"/lote")
        anim = await p.evaluate(u"""() => { document.querySelector('.radai-tarefas .dobra').click();
          const c = document.documentElement.classList; const s = getComputedStyle(
          document.querySelector('.radai-tarefas'));
          return [c.contains('dir-fechando'), c.contains('dir-recolhida'), s.animationName,
                  s.animationDuration, s.animationTimingFunction]; }""")
        await p.wait_for_timeout(500)
        fim = await p.evaluate("document.documentElement.classList.contains('dir-recolhida')")
        checar(u"recolher pelo botão anima o panel reveal (350 ms, a curva) e só então recolhe",
               anim[:2] == [True, False] and anim[2] == u"uiPainelSai"
               and anim[3] == u"0.35s" and anim[4] == u"cubic-bezier(0.22, 1, 0.36, 1)"
               and fim, repr(anim))
        for rota in (u"/ver", u"/lote"):
            q = await _quadros(p, rota)
            checar(u"  e em %s ela continua recolhida, sem piscar" % rota,
                   q and not any(x["dir"] for x in q), _resumo(q))

        secao(u"a barra direita expandida à mão fica exposta na navegação")
        q = await _quadros(p, u"/recon3d")
        anim = await p.evaluate(u"""() => { document.getElementById('radai_tf_ic_fila').click();
          const c = document.documentElement.classList; const s = getComputedStyle(
          document.querySelector('.radai-tarefas'));
          return [c.contains('dir-abrindo'), c.contains('dir-recolhida'), s.animationName,
                  s.animationDuration, s.animationTimingFunction]; }""")
        checar(u"expandir pelo trilho anima o panel reveal (400 ms, a curva)",
               anim[:2] == [True, False] and anim[2] == u"uiPainelEntra"
               and anim[3] == u"0.4s" and anim[4] == u"cubic-bezier(0.22, 1, 0.36, 1)",
               repr(anim))
        await p.wait_for_timeout(500)
        for rota in (u"/elastic", u"/bridge/laudo", u"/lote", u"/config"):
            q = await _quadros(p, rota)
            checar(u"  e em %s ela já nasce aberta, sem animar nem piscar" % rota,
                   q and all(x["dir"] for x in q) and not any(x["abr"] for x in q),
                   _resumo(q))
        outra = await pg.context.new_page()
        await outra.add_init_script(_JS_QUADROS)
        q = await _quadros(outra, u"/elastic")
        await outra.close()
        checar(u"  o pedido é da aba: noutra aba ela nasce recolhida",
               q and not any(x["dir"] for x in q), _resumo(q))
        await p.evaluate("document.querySelector('.radai-tarefas .dobra').click()")
        await p.wait_for_timeout(500)
        await _quadros(p, u"/lote")
        await p.evaluate("document.getElementById('radai_tf_ic_fila').click()")
        await p.wait_for_timeout(500)
        q1 = await _quadros(p, u"/recon3d")
        q2 = await _quadros(p, u"/ver")
        checar(u"  expandida à mão no Rodar agora, volta à regra: recolhe fora e abre "
               u"sozinha no Ver segmentação",
               q1 and not any(x["dir"] for x in q1) and q2 and not q2[0]["dir"]
               and q2[-1]["dir"], _resumo(q1) + u" | " + _resumo(q2))

        await p.route("**/recon3d", _rota_que_pisca)
        q = await _quadros(p, u"/recon3d")
        await p.unroute("**/recon3d", _rota_que_pisca)
        checar(u"  (isca) a barra que nasce aberta e recolhe depois é acusada",
               _piscou(q), _resumo(q))

        secao(u"a barra esquerda")
        await p.goto(BASE + u"/", wait_until="domcontentloaded")
        await p.wait_for_timeout(600)
        await p.evaluate("location.assign('/bridge')")
        await p.wait_for_url(BASE + u"/bridge")
        await p.wait_for_timeout(1300)
        q = await p.evaluate("window.__radaiQuadros || []")
        checar(u"vinda da porta, nasce recolhida e se expande sozinha, animada",
               q and not q[0]["lado"] and q[-1]["lado"] and any(x["ladoAbr"] for x in q)
               and not _piscou(q, "lado"), _resumo(q, "lado"))
        await p.reload(wait_until="domcontentloaded")
        await p.wait_for_timeout(1000)
        q = await p.evaluate("window.__radaiQuadros || []")
        checar(u"  recarregar não repete: nasce como ficou, sem animar",
               q and all(x["lado"] for x in q) and not any(x["ladoAbr"] for x in q),
               _resumo(q, "lado"))
        anim = await p.evaluate(u"""() => { document.getElementById('ladoDobra').click();
          const c = document.documentElement.classList;
          const n = getComputedStyle(document.querySelector('.radai-menu'));
          return [c.contains('lado-fechando'), n.animationName, n.animationDuration,
                  n.animationTimingFunction]; }""")
        await p.wait_for_timeout(500)
        fim = await p.evaluate("document.documentElement.getAttribute('data-trilho')")
        checar(u"recolher a pedido anima (350 ms, a curva) e só então recolhe",
               anim == [True, u"uiPainelVela", u"0.35s",
                        u"cubic-bezier(0.22, 1, 0.36, 1)"] and fim is None,
               repr((anim, fim)))
        q = await _quadros(p, u"/recon3d")
        checar(u"  e fora da porta ela nasce como ficou, sem animar",
               q and not any(x["lado"] for x in q), _resumo(q, "lado"))
        anim = await p.evaluate(u"""() => { document.getElementById('ladoDobra').click();
          const c = document.documentElement.classList;
          const r = getComputedStyle(document.querySelector('.radai-menu a .rot'));
          return [c.contains('lado-abrindo'), r.animationName, r.animationDuration]; }""")
        checar(u"  expandir a pedido anima o panel reveal (400 ms)",
               anim == [True, u"uiPainelEntra", u"0.4s"], repr(anim))
        await p.wait_for_timeout(500)
        await p.goto(BASE + u"/", wait_until="domcontentloaded")
        await p.wait_for_timeout(600)
        await p.evaluate("location.assign('/nidus')")
        await p.wait_for_url(BASE + u"/nidus")
        await p.wait_for_timeout(1300)
        q = await p.evaluate("window.__radaiQuadros || []")
        checar(u"  vinda da porta com ela guardada aberta, nasce recolhida e se expande",
               q and not q[0]["lado"] and q[-1]["lado"], _resumo(q, "lado"))

        secao(u"movimento reduzido")
        await p.emulate_media(reduced_motion="reduce")
        await _quadros(p, u"/recon3d", 900)
        r = await p.evaluate(u"""() => { const c = document.documentElement.classList;
          document.getElementById('radai_tf_ic_fila').click();
          const a = [c.contains('dir-abrindo'), c.contains('dir-recolhida')];
          document.querySelector('.radai-tarefas .dobra').click();
          const b = [c.contains('dir-fechando'), c.contains('dir-recolhida')];
          document.getElementById('ladoDobra').click();
          return a.concat(b, [c.contains('lado-abrindo') || c.contains('lado-fechando'),
            getComputedStyle(document.querySelector('.radai-tarefas')).animationName]); }""")
        checar(u"nada anima: abre, recolhe e o trilho troca na hora",
               r == [False, False, False, True, False, u"none"], repr(r))
        await p.emulate_media(reduced_motion="no-preference")
        checar(u"nenhum erro de JavaScript nas barras", not erros, u"; ".join(erros[:3]))
    finally:
        await p.close()


async def _rota_que_pisca(route):
    resp = await route.fetch()
    corpo = (await resp.text()).replace(u'class="dir-recolhida" ', u"", 1)
    velho = (u"<script>document.documentElement.classList.remove('dir-recolhida');"
             u"setTimeout(function(){document.documentElement.classList"
             u".add('dir-recolhida')}, 150)</" + u"script>")
    i = corpo.lower().rfind(u"</body>")
    await route.fulfill(response=resp, body=corpo[:i] + velho + corpo[i:])


def _molde_re(tr):
    return re.compile(u"^" + u"(.+?)".join(
        re.escape(p) for p in re.split(r"%s|%d", tr)) + u"$")


async def _buracos_da_l3(pg, root):
    secao(u"a tela renderizada em alemao: os buracos que a L3 mediu")
    sys.path.insert(0, os.path.join(RAIZ, "app"))
    try:
        import radai_phrases as _F
        de = _F.construir()["de"]
    finally:
        sys.path.pop(0)

    async def _txt(sel):
        return await pg.evaluate(
            "(function(s){ var e = document.querySelector(s);"
            " return e ? e.textContent.replace(/\\s+/g, ' ').trim() : null })(%s)"
            % json.dumps(sel))

    async def _abrir(rota, espera=900):
        await pg.goto(BASE + rota, wait_until="networkidle")
        await pg.wait_for_timeout(espera)
        await pg.evaluate("window.radaiRetraduzir && radaiRetraduzir(); true")
        await pg.wait_for_timeout(350)

    lido = {}
    isca = {}
    await pg.evaluate("localStorage.setItem('radai_idioma', 'de'); true")
    try:
        await _abrir("/")
        lido["h2"] = await _txt('a.ls-card[href="/recon3d"] .ls-nome')
        lido["por"] = await _txt(".ls-autor [data-radai-frase]")
        await _abrir("/lote")
        await _encher_pasta(pg, os.path.join(root, "PAC_A"))
        await pg.evaluate("varrer(); true")
        await pg.wait_for_timeout(3500)
        await pg.evaluate("if(!noCarrinho(SERIES[0])) alternar(0); true")
        await pg.wait_for_timeout(400)
        await pg.evaluate("radaiRetraduzir(); true")
        await pg.wait_for_timeout(300)
        for k, s in (("msg", "#msg"), ("conta", "#cx2_n"),
                     ("cart", "#cartxt [data-radai-frase]"),
                     ("incl", "#linha_0 button.dentro [data-radai-frase]"),
                     ("motivo", "#linha_0 .tec2 [data-radai-frase]")):
            lido[k] = await _txt(s)
        isca["incl"] = await pg.evaluate(
            "(function(){ var b = document.createElement('button');"
            " b.innerHTML = '&#10003; incluída'; document.body.appendChild(b);"
            " radaiRetraduzir(); var t = b.textContent; b.remove(); return t })()")
        await pg.evaluate("localStorage.setItem('radai_tema', 'escuro'); true")
        await _abrir("/config", 1500)
        lido["tema"] = await _txt("#subTema [data-radai-frase]")
        await pg.evaluate("localStorage.removeItem('radai_tema'); true")
        lido["chaves"] = await _txt("#sub_ritmo [data-radai-frase]")
        lido["rodape"] = await _txt("#rodape")
        await _abrir("/nidus/projecao", 1500)
        await pg.evaluate("ndListar(%s); true"
                          % json.dumps(os.path.join(root, "PAC_A")))
        for _ in range(20):
            await pg.wait_for_timeout(500)
            if await pg.evaluate("ND.lista.length > 0"):
                break
        await pg.evaluate("ndEscolher(0); true")
        await pg.wait_for_timeout(3500)
        lido["passo"] = await _txt("#nd_passo")
        await _abrir("/elastic/fusao", 1000)
        await pg.evaluate("elVarrer(false); true")
        await pg.wait_for_timeout(3000)
        lido["series"] = await _txt(".el-pasta-q [data-radai-frase]")
        isca["series"] = await pg.evaluate(
            "(function(){ var s = document.createElement('span');"
            " s.className = 'el-pasta-q'; s.textContent = '2 séries';"
            " document.body.appendChild(s); radaiRetraduzir();"
            " var t = s.textContent; s.remove(); return t })()")
        await _abrir("/bridge/laudo", 1500)
        await pg.evaluate("dcVarrer(); true")
        await pg.wait_for_timeout(400)
        lido["av1"] = await _txt("#dc_msg")
        isca["av1"] = await pg.evaluate(
            "(function(){ var s = document.createElement('span');"
            " s.setAttribute('data-radai-frase', '');"
            " s.textContent = 'informe a pasta do estudo'; document.body.appendChild(s);"
            " radaiRetraduzir(); s.textContent = 'informe a pasta do estudo';"
            " radaiRetraduzir(); var t = s.textContent; s.remove(); return t })()")
    finally:
        await pg.evaluate("localStorage.removeItem('radai_idioma'); true")

    checar(u"a porta: «Reconstruções 3D» sai em alemao (era «Reconstruções3D», "
           u"sem chave)", lido.get("h2") == de.get(u"Reconstruções 3D"),
           repr(lido.get("h2")))
    checar(u"  e o «Por» da autoria tambem", lido.get("por") == de.get(u"Por"),
           repr(lido.get("por")))
    checar(u"o Rodar agora: a contagem da varredura sai pelo MOLDE",
           bool(lido.get("msg")) and bool(_molde_re(
               de[u"%s serie(s) encontrada(s)"]).match(lido["msg"])),
           repr(lido.get("msg")))
    checar(u"  e «N série(s) nesta lista», no titulo do passo 2, tambem",
           bool(lido.get("conta")) and bool(_molde_re(
               de[u"%s série(s) nesta lista"]).match(lido["conta"])),
           repr(lido.get("conta")))
    checar(u"  e a frase do carrinho, inteira, num no so",
           bool(lido.get("cart")) and any(_molde_re(de[k]).match(lido["cart"])
               for k in (u"%s série(s) no carrinho",
                         u"%s série(s) no carrinho, de %s pastas")),
           repr(lido.get("cart")))
    checar(u"  e o botao da serie incluida (a palavra fora do `✓`)",
           lido.get("incl") == de.get(u"incluída"), repr(lido.get("incl")))
    checar(u"  (isca) a forma de antes -- «✓ incluída» num no so -- fica em "
           u"portugues no mesmo tradutor",
           (isca.get("incl") or u"").strip() == u"✓ incluída", repr(isca.get("incl")))
    checar(u"  e o motivo da sugestao, uma frase por no (`radai_triage`)",
           bool(lido.get("motivo")) and bool(_molde_re(
               de[u"TC de simulacao do exame: %s mm"]).match(lido["motivo"])),
           repr(lido.get("motivo")))
    checar(u"as Configuracoes: o tema no subtitulo sai em alemao",
           lido.get("tema") in (de.get(u"modo escuro"), de.get(u"modo claro")),
           repr(lido.get("tema")))
    checar(u"  e a contagem de chaves (a palavra no seu no)",
           lido.get("chaves") in (de.get(u"chave"), de.get(u"chaves")),
           repr(lido.get("chaves")))
    _geo = de[u"Biblioteca de geometria: v%s carregada."].split(u"%s")[0]
    checar(u"  e o rodape tecnico, pelo molde (%s…)" % _geo,
           _geo in (lido.get("rodape") or u"")
           and u"Biblioteca de geometria" not in (lido.get("rodape") or u""),
           (lido.get("rodape") or u"")[:90])
    checar(u"o Nidus RT: o passo do detector sai pelo MOLDE, e por `uiTexto`",
           bool(lido.get("passo")) and any(_molde_re(de[k]).match(lido["passo"])
               for k in (u"%s mm por pixel da projeção",
                         u"%s mm por pixel da projeção — acima do que esta "
                         u"série oferece: o que aparece a mais é interpolação, "
                         u"e não o paciente")),
           repr(lido.get("passo")))
    checar(u"o Elastic RT: «séries» no seu proprio no, em alemao",
           lido.get("series") in (de.get(u"série"), de.get(u"séries")),
           repr(lido.get("series")))
    checar(u"  (isca) a forma de antes -- «2 séries» num no so -- fica em "
           u"portugues", isca.get("series") == u"2 séries",
           repr(isca.get("series")))
    checar(u"o DicomBridge: o aviso da pasta, repintado por `uiTexto`, sai "
           u"em alemao", lido.get("av1") == de.get(u"informe a pasta do estudo"),
           repr(lido.get("av1")))
    checar(u"  (isca) repintado por `textContent` sobre a marca, fica em "
           u"portugues", isca.get("av1") == u"informe a pasta do estudo",
           repr(isca.get("av1")))


def _serie_contornada(base):
    sys.path.insert(0, os.path.join(RAIZ, "tools"))
    from datetime import datetime
    from make_test_series import escreve_serie
    from pydicom.dataset import Dataset, FileDataset
    from pydicom.sequence import Sequence
    from pydicom.uid import ExplicitVRLittleEndian, generate_uid
    pasta = os.path.join(base, "ver", "PAC_VER", "CT")
    uid = escreve_serie(pasta, "PAC_VER", datetime.now(), 20)
    meta = Dataset()
    meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.481.3"
    meta.MediaStorageSOPInstanceUID = generate_uid()
    meta.TransferSyntaxUID = ExplicitVRLittleEndian
    ds = FileDataset(None, {}, file_meta=meta, preamble=b"\0" * 128)
    ds.SOPClassUID = meta.MediaStorageSOPClassUID
    ds.SOPInstanceUID = meta.MediaStorageSOPInstanceUID
    ds.SeriesInstanceUID = generate_uid()
    ds.Modality = "RTSTRUCT"
    ds.PatientID = "FANTOMA"
    ds.StructureSetLabel = "RadAI_OAR"
    roi = Dataset()
    roi.ROINumber = 1
    roi.ROIName = "Heart_ai"
    rc = Dataset()
    rc.ReferencedROINumber = 1
    rc.ROIDisplayColor = [255, 60, 60]
    cs = []
    for z in range(5, 11):
        c = Dataset()
        c.ContourGeometricType = "CLOSED_PLANAR"
        c.NumberOfContourPoints = 4
        c.ContourData = [-48.0, -48.0, 3.0 * z, 32.0, -48.0, 3.0 * z,
                         32.0, 32.0, 3.0 * z, -48.0, 32.0, 3.0 * z]
        cs.append(c)
    rc.ContourSequence = Sequence(cs)
    ds.StructureSetROISequence = Sequence([roi])
    ds.ROIContourSequence = Sequence([rc])
    nome = "RS_RadAI_20260927_%s.dcm" % uid[-8:]
    try:
        ds.save_as(os.path.join(pasta, nome), enforce_file_format=True)
    except TypeError:
        ds.save_as(os.path.join(pasta, nome), write_like_original=False)
    return pasta, uid


async def _ver_em_alemao(pg, root):
    secao(u"o /ver em alemao: o «abrir» continua sendo botao, e abre a serie")
    sys.path.insert(0, os.path.join(RAIZ, "app"))
    try:
        import radai_phrases as _F
        abrir_de = _F.construir()["de"].get(u"Abrir") or u""
    finally:
        sys.path.pop(0)
    try:
        pasta, uid = _serie_contornada(os.path.dirname(root))
    except Exception as e:
        checar(u"o fantoma contornado do /ver foi montado", False,
               u"%s: %s" % (type(e).__name__, str(e)[:120]))
        return

    sys.path.insert(0, os.path.join(RAIZ, "app"))
    calib_antes = os.environ.get("RADAI_CALIB_DIR")
    os.environ["RADAI_CALIB_DIR"] = os.path.join(os.path.dirname(root), "calib")
    try:
        import radai_archive
        radai_archive.registrar_serie(
            uid=uid, pasta=pasta, rs="RS_RadAI_20260927_%s.dcm" % uid[-8:],
            date="20260927", pid="FANTOMA", estruturas=1, secs=61,
            maquina="BATERIA_UI", ver="bateria")
    finally:
        sys.path.pop(0)
        if calib_antes is None:
            os.environ.pop("RADAI_CALIB_DIR", None)
        else:
            os.environ["RADAI_CALIB_DIR"] = calib_antes

    async def _aberta():
        return await pg.evaluate(
            "(function(){ var c = document.getElementById('cx_verseg'),"
            " q = document.getElementById('cp_qual');"
            " return !!c && !c.classList.contains('fechado')"
            " && !!q && q.textContent.indexOf('20') >= 0 })()")

    lido = {}
    await pg.evaluate("localStorage.setItem('radai_idioma', 'de'); true")
    try:
        await pg.goto(BASE + "/ver", wait_until="networkidle")
        await pg.wait_for_timeout(900)
        await pg.evaluate("window.radaiRetraduzir && radaiRetraduzir(); true")
        await pg.wait_for_timeout(300)
        bts = pg.locator("#vr_acervo td.ua-acao button")
        lido["acervo_n"] = await bts.count()
        lido["acervo_rot"] = ((await bts.first.inner_text()).strip()
                              if lido["acervo_n"] else u"")
        if lido["acervo_n"]:
            await bts.first.click()
            for _ in range(20):
                await pg.wait_for_timeout(500)
                if await _aberta():
                    break
            lido["acervo_abriu"] = await _aberta()
        await pg.goto(BASE + "/ver", wait_until="networkidle")
        await pg.wait_for_timeout(600)
        await pg.click("#vr_guias-t-pasta")
        await pg.wait_for_timeout(200)
        await pg.fill("#vr_pasta", os.path.dirname(os.path.dirname(pasta)))
        await pg.evaluate("vrVarrer(); true")
        await pg.wait_for_timeout(3500)
        await pg.evaluate("window.radaiRetraduzir && radaiRetraduzir(); true")
        await pg.wait_for_timeout(300)
        bts = pg.locator("#vr_tab [data-abrir]")
        lido["busca_n"] = await bts.count()
        lido["busca_rot"] = ((await bts.first.inner_text()).strip()
                             if lido["busca_n"] else u"")
        if lido["busca_n"]:
            await bts.first.click()
            await pg.wait_for_timeout(2000)
            lido["busca_abriu"] = await _aberta()
        lido["isca_n"] = await pg.evaluate(
            "(function(){ var t = document.querySelector('#vr_tab td.vr-acao');"
            " if(!t) return -1; t.textContent = t.textContent;"
            " return document.querySelectorAll('#vr_tab [data-abrir]').length })()")
    finally:
        await pg.evaluate("localStorage.removeItem('radai_idioma'); true")

    checar(u"o Acervo local em alemao: a linha tem o BOTAO depois da traducao",
           lido.get("acervo_n") == 1, str(lido.get("acervo_n")))
    checar(u"  e ele diz «%s» (traduzido, e nao em portugues)" % abrir_de,
           bool(abrir_de) and lido.get("acervo_rot") == abrir_de,
           repr(lido.get("acervo_rot")))
    checar(u"  e clicar nele ABRE a serie no comparador (passo 2 aberto, 20 "
           u"cortes)", lido.get("acervo_abriu") is True,
           repr(lido.get("acervo_abriu")))
    checar(u"a busca por pasta em alemao: a linha tem o BOTAO depois da "
           u"traducao", lido.get("busca_n") == 1, str(lido.get("busca_n")))
    checar(u"  e ele diz «%s»" % abrir_de,
           bool(abrir_de) and lido.get("busca_rot") == abrir_de,
           repr(lido.get("busca_rot")))
    checar(u"  e clicar nele ABRE a serie no comparador",
           lido.get("busca_abriu") is True, repr(lido.get("busca_abriu")))
    checar(u"  (isca) a celula reescrita por cima, como o tradutor fazia, "
           u"deixa zero botoes", lido.get("isca_n") == 0,
           str(lido.get("isca_n")))


# GUARDA: a 1280 px com a barra da direita aberta, cada informação da linha
# do Acervo Local (as onze colunas e o Abrir) está à vista sem rolar de lado
# dentro do cartão: as colunas que não cabem passam a uma linha embaixo do
# nome. Medido na tela renderizada, em português e em alemão.
_VR_LINHA = {"pid": "PAC_LARGO", "date": "20260927", "uid8": "12345678",
             "estruturas": 47, "quando": "2026-09-27 10:00", "secs": 1881,
             "estado": "ok", "bilhete": "b1"}
_VR_DETALHE = {"nome": "FANTOMA COM NOME LONGO", "modalidade": "CT",
               "cortes": 97, "espessura_mm": 5, "modo": "perso",
               "tasks": ["total_v3", "trunk_cavities", "breasts",
                         "abdominal_muscles"], "protocolos": ["torax_mama"]}
_JS_VR_A_VISTA = u"""(function(){
 var cx = document.getElementById('vr_acervo');
 var tr = cx && cx.querySelector('tbody tr[data-i="0"]');
 if(!tr) return {erro: 'sem linha'};
 var c = cx.getBoundingClientRect();
 function ve(el){
  if(!el) return false;
  var r = el.getBoundingClientRect();
  if(!r.width || !r.height) return false;
  var s = getComputedStyle(el);
  if(s.display === 'none' || s.visibility === 'hidden') return false;
  return r.left >= c.left - 1 && r.right <= c.right + 1;
 }
 function algum(sel){
  return Array.prototype.some.call(tr.querySelectorAll(sel), ve);
 }
 var fora = [];
 ['data','nome','id','modalidade','cortes','espessura','estruturas','modo',
  'tasks'].forEach(function(k){
  if(!algum('[data-c="' + k + '"],[data-c2="' + k + '"]')) fora.push(k);
 });
 if(!algum('[data-c="quando"],[data-c2="quando"]')) fora.push('quando');
 if(!algum('[data-c="levou"],[data-c2="levou"]')) fora.push('levou');
 if(!algum('td.ua-acao button')) fora.push('abrir');
 return {fora: fora, rola: cx.scrollWidth > cx.clientWidth + 1, cont: cx.clientWidth,
         barra: !document.documentElement.classList.contains('dir-recolhida')
                && !document.body.classList.contains('dir-recolhida')};
})()"""


async def _ver_acervo_cabe(pg):
    secao(u"o Acervo Local do /ver cabe a 1280 px com a barra da direita aberta")

    async def _acervo(route):
        await route.fulfill(status=200, content_type="application/json",
                            body=json.dumps({"series": [_VR_LINHA]}))

    async def _detalhes(route):
        await route.fulfill(status=200, content_type="application/json",
                            body=json.dumps({"itens": [_VR_DETALHE]}))

    lido = {}
    await pg.route("**/api/acervo/tabela", _acervo)
    await pg.route("**/api/acervo/tabela/detalhes", _detalhes)
    try:
        for lingua, larg in ((u"pt-BR", 1280), (u"de", 1280), (u"pt-BR", 1600),
                             (u"de", 1600)):
            await pg.set_viewport_size({"width": larg, "height": 900})
            await pg.evaluate("localStorage.setItem('radai_idioma', '%s');"
                              " sessionStorage.removeItem('radai_dir_usuario');"
                              " true" % lingua)
            await pg.goto(BASE + "/ver", wait_until="networkidle")
            await pg.click("#vr_guias-t-acervo")
            await pg.wait_for_timeout(1500)
            lido[(lingua, larg)] = await pg.evaluate(_JS_VR_A_VISTA)
        await pg.set_viewport_size({"width": 1280, "height": 900})
        await pg.evaluate("localStorage.setItem('radai_idioma', 'pt-BR'); true")
        await pg.goto(BASE + "/ver", wait_until="networkidle")
        await pg.click("#vr_guias-t-acervo")
        await pg.wait_for_timeout(1500)
        await pg.add_style_tag(content=u".ui-acervo .ua-mais{display:none !important}"
                                       u".ui-acervo .ua-x{display:table-cell !important}")
        await pg.wait_for_timeout(200)
        lido["isca"] = await pg.evaluate(_JS_VR_A_VISTA)
    finally:
        await pg.unroute("**/api/acervo/tabela/detalhes")
        await pg.unroute("**/api/acervo/tabela")
        await pg.evaluate("localStorage.removeItem('radai_idioma'); true")
        await pg.set_viewport_size({"width": 1520, "height": 950})
    for (lingua, larg), d in sorted((k, v) for k, v in lido.items()
                                    if k != "isca"):
        checar(u"[%s %d] a barra da direita está aberta" % (lingua, larg),
               bool(d.get("barra")), repr(d))
        checar(u"[%s %d] tudo da linha à vista, sem rolar de lado" % (lingua, larg),
               d.get("fora") == [], repr(d))
    checar(u"  (isca) sem a linha de baixo, as colunas do fim saem da vista",
           bool((lido.get("isca") or {}).get("fora")), repr(lido.get("isca")))


async def _cartoes_pelo_teclado(pg):
    secao(u"os cartoes do /lote pelo teclado: o Tab chega, Enter e Espaco abrem")
    await pg.route("**/api/overnight/iniciar", lambda r: r.abort())
    try:
        await pg.goto(BASE + "/lote", wait_until="networkidle")
        await pg.wait_for_timeout(900)
        await pg.evaluate("window.uiPopupSerie && uiPopupSerie('cx1').fechar(); true")
        await pg.wait_for_timeout(300)
        await pg.evaluate("document.activeElement && document.activeElement.blur();"
                          " window.scrollTo(0, 0); true")
        chegou = {}
        for passo in range(1, 301):
            await pg.keyboard.press("Tab")
            ident = await pg.evaluate(
                "document.activeElement ? (document.activeElement.id || '') : ''")
            if ident in (u"cd_add", u"cd_night") and ident not in chegou:
                chegou[ident] = passo
            if len(chegou) == 2:
                break
        checar(u"o Tab para em «Adicionar novas series»", u"cd_add" in chegou,
               str(chegou))
        checar(u"  e em «Incluir Overnight Run»", u"cd_night" in chegou,
               str(chegou))
        papel = await pg.evaluate(
            "['cd_add','cd_night'].map(function(i){ var e = document.getElementById(i);"
            " return e ? (e.getAttribute('role') || '') : '' })")
        checar(u"  os dois se anunciam como botao (role=button, para o leitor "
               u"de tela)", papel == [u"button", u"button"], str(papel))
        await pg.focus("#cd_night")
        await pg.keyboard.press("Enter")
        await pg.wait_for_timeout(1500)
        abriu = await pg.locator(".ui-pnl #ov_root").count()
        checar(u"Enter no «Incluir Overnight Run» abre o modal com o ROOT",
               abriu == 1, str(abriu))
        await pg.keyboard.press("Escape")
        await pg.wait_for_timeout(500)
        await pg.evaluate("window.uiPopupSerie && uiPopupSerie('cx1').fechar(); true")
        await pg.wait_for_timeout(400)
        await pg.focus("#cd_add")
        await pg.keyboard.press(" ")
        await pg.wait_for_timeout(400)
        estado = await pg.evaluate(
            "[!!document.getElementById('cx1').closest('.ui-modal-veu.vis'),"
            " (document.activeElement || {}).id || '', window.scrollY]")
        checar(u"Espaco no «Adicionar novas series» abre o popup do passo 1 e leva o "
               u"foco para a pasta", estado[0] is True and estado[1] == u"pasta",
               str(estado))
        await pg.keyboard.press("Escape")
        await pg.wait_for_timeout(400)
        anel = await pg.evaluate(
            "(function(){ var e = document.getElementById('cd_night'); e.focus();"
            " var s = getComputedStyle(e); return [e.matches(':focus-visible'),"
            " s.outlineStyle, s.outlineWidth] })()")
        checar(u"  e o foco no cartao se ve (anel de :focus-visible)",
               anel[1] not in (u"none", u"") and anel[2] not in (u"0px", u""),
               str(anel))
    finally:
        await pg.unroute("**/api/overnight/iniciar")
        await pg.keyboard.press("Escape")


_JS_CONTRASTE = """(function(sel, cor){
 var e = document.querySelector(sel); if(!e) return null;
 if(cor) e.style.color = cor;
 function rgba(s){ var m = (s || '').match(/[\\d.]+/g) || [0, 0, 0, 0];
  return [+m[0], +m[1], +m[2], m.length > 3 ? +m[3] : 1] }
 function sobre(a, b){ var k = a[3]; return [a[0]*k + b[0]*(1-k),
  a[1]*k + b[1]*(1-k), a[2]*k + b[2]*(1-k), 1] }
 var camadas = [], n = e;
 while(n && n.nodeType === 1){
  var f = rgba(getComputedStyle(n).backgroundColor);
  if(f[3] > 0) camadas.push(f);
  if(f[3] >= 1) break;
  n = n.parentElement;
 }
 var fundo = [255, 255, 255, 1];
 for(var i = camadas.length - 1; i >= 0; i--) fundo = sobre(camadas[i], fundo);
 var t = sobre(rgba(getComputedStyle(e).color), fundo);
 function lum(c){ return [0, 1, 2].map(function(j){ var v = c[j] / 255;
  return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4) })
  .reduce(function(s, v, j){ return s + v * [0.2126, 0.7152, 0.0722][j] }, 0) }
 var a = lum(t), b = lum(fundo);
 return Math.round(100 * (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05)) / 100;
})(%s, %s)"""


async def _tema_claro_legivel(pg, root):
    secao(u"o tema claro: o que o /lote pinta passa o piso de 4,5:1")
    await pg.evaluate("localStorage.setItem('radai_tema', 'claro');"
                      " localStorage.setItem('radai_idioma', 'pt-BR'); true")
    medido = {}
    try:
        await pg.goto(BASE + "/lote", wait_until="networkidle")
        await pg.wait_for_timeout(900)
        medido["tema"] = await pg.evaluate(
            "document.documentElement.getAttribute('data-tema')")
        await _encher_pasta(pg, os.path.join(root, "PAC_A"))
        await pg.evaluate("varrer(); true")
        await pg.wait_for_timeout(3500)
        await pg.evaluate("if(SERIES.length && !noCarrinho(SERIES[0])) "
                          "alternar(0); true")
        await pg.wait_for_timeout(400)
        for k, sel in (("incluida", "#linha_0 button.dentro"),
                       ("msg", "#msg"),
                       ("card_da_fila", ".radai-tarefas .cd .cd-sub, .radai-tarefas .vazia")):
            medido[k] = await pg.evaluate(
                _JS_CONTRASTE % (json.dumps(sel), u"null"))
        medido["isca"] = await pg.evaluate(
            _JS_CONTRASTE % (json.dumps("#linha_0 button.dentro"),
                             json.dumps("#7fd8a3")))
        await pg.evaluate("document.querySelector('#linha_0 button.dentro')"
                          ".style.color = ''; true")
    finally:
        await pg.evaluate("localStorage.removeItem('radai_tema');"
                          " localStorage.removeItem('radai_idioma'); true")
    checar(u"a tela abriu no tema claro", medido.get("tema") == u"claro",
           repr(medido.get("tema")))
    for k, rot in (("incluida", u"«✓ incluída» no botao da serie"),
                   ("msg", u"a mensagem da varredura"),
                   ("card_da_fila", u"o subtitulo do card da Fila")):
        v = medido.get(k)
        checar(u"  %s: contraste >= 4,5:1" % rot,
               v is not None and v >= 4.5, repr(v))
    checar(u"  (isca) o verde escrito a mao de antes, no mesmo botao, fica "
           u"abaixo do piso", medido.get("isca") is not None
           and medido["isca"] < 4.5, repr(medido.get("isca")))


_JS_PIOR_CASO = (
    "(function(){ for(var i = 0; i < SERIES.length; i++)"
    " if(!noCarrinho(SERIES[i])) alternar(i);"
    " if(SERIES[0]){ SERIES[0].situacao = 'concluida';"
    "  SERIES[0].detalhe = 'BATERIA_UI · 27/09 22:10 · AUTO'; SERIES[0].tem_rs = true;"
    "  SERIES[0].nome = 'PACIENTE FANTOMA COM NOME COMPRIDO';"
    "  SERIES[0].kernel = 'FC08-H' }"
    " if(SERIES[1]){ SERIES[1].tem_rs = true; SERIES[1].desc = 'TORAX ROTINA C/"
    " CONTRASTE 5.0 MM MEDIASTINO AXIAL RECON PLANEJAMENTO RADIOTERAPIA' }"
    " pintarTabela(); if(SERIES[2] && noCarrinho(SERIES[2])) alternar(2);"
    " if(window.radaiRetraduzir) radaiRetraduzir(); return true })()")
_JS_CABE = (
    "(function(){ var t = document.getElementById('tab'),"
    " r = t.parentElement.getBoundingClientRect();"
    " var q = t.querySelector('td.modo .md-aj'), qb = q ? q.getBoundingClientRect() : null;"
    " return {tab: t.scrollWidth, caixa: t.parentElement.clientWidth,"
    "  aj_dentro: !!qb && qb.right <= r.right + 0.5 && qb.left >= r.left } })()")


async def _onda_4b(pg, root):
    secao(u"onda 4b: a linha cabe, os links, a /config no claro, o foco e o idioma")
    sys.path.insert(0, os.path.join(RAIZ, "app"))
    try:
        import radai_phrases as _F
        de = _F.construir()["de"]
    finally:
        sys.path.pop(0)
    lido = {}
    try:
        await pg.set_viewport_size({"width": 1600, "height": 950})
        for lingua in (u"pt-BR", u"de"):
            await pg.goto(BASE + "/lote", wait_until="networkidle")
            await pg.evaluate("localStorage.setItem('radai_idioma', %s);"
                              " sessionStorage.removeItem('radai_dir_usuario'); true"
                              % json.dumps(lingua))
            await pg.goto(BASE + "/lote", wait_until="networkidle")
            await pg.wait_for_timeout(900)
            await _encher_pasta(pg, root)
            await pg.evaluate("varrer(); true")
            await pg.wait_for_timeout(4000)
            await pg.evaluate(_JS_PIOR_CASO)
            await pg.wait_for_timeout(700)
            lido["cabe_" + lingua] = await pg.evaluate(_JS_CABE)
            if lingua == u"de":
                await pg.add_style_tag(content=(
                    "td.acoes .acoes-bts{display:inline;white-space:nowrap}"
                    "td.acoes{white-space:nowrap}"
                    "td.desc{width:auto;min-width:0}"
                    "td.desc .desc-cx{width:auto;min-width:0}"))
                await pg.wait_for_timeout(300)
                lido["cabe_isca"] = await pg.evaluate(_JS_CABE)
        await pg.goto(BASE + "/autocontorno", wait_until="networkidle")
        await pg.wait_for_timeout(500)
        await pg.goto(BASE + "/ver", wait_until="networkidle")
        await pg.wait_for_timeout(1300)
        lido["voltar"] = await pg.evaluate(
            "(function(){ var b = document.querySelector('[data-radai-voltar]');"
            " return b ? [b.getAttribute('title'), b.getAttribute('aria-label')] : null })()")
        lido["ph"] = await pg.evaluate(
            "(function(){ var e = document.getElementById('vr_pasta');"
            " return e ? e.getAttribute('placeholder') : null })()")
        lido["ph_isca"] = await pg.evaluate(
            "(function(){ var i = document.createElement('input');"
            " i.setAttribute('placeholder', 'zzqx dica sem chave zzqx');"
            " document.body.appendChild(i); radaiRetraduzir();"
            " var v = i.getAttribute('placeholder'); i.remove(); return v })()")
        await pg.evaluate("sessionStorage.clear(); true")
        await pg.goto(BASE + "/recon3d/anatomia", wait_until="networkidle")
        await pg.wait_for_timeout(1300)
        lido["voltar_pai"] = await pg.evaluate(
            "(function(){ var b = document.querySelector('[data-radai-voltar]');"
            " return b ? [b.getAttribute('title'), b.getAttribute('aria-label'),"
            " b.getAttribute('data-radai-destino')] : null })()")
        await pg.evaluate("localStorage.setItem('radai_idioma', 'pt-BR');"
                          " localStorage.setItem('radai_tema', 'escuro'); true")
        await pg.goto(BASE + "/lote", wait_until="networkidle")
        await pg.wait_for_timeout(700)
        lido["link"] = await pg.evaluate(
            _JS_CONTRASTE % (json.dumps(".rc-nota a[href='/ver']"), u"null"))
        lido["link_3d"] = await pg.evaluate(
            u"!!document.querySelector(\".rc-nota a[href='/recon3d']\")")
        lido["link_isca"] = await pg.evaluate(
            _JS_CONTRASTE % (json.dumps(".rc-nota a[href='/ver']"),
                             json.dumps("rgb(0,0,238)")))
        await pg.evaluate("document.querySelector(\".rc-nota a[href='/ver']\")"
                          ".style.color = ''; true")
        await pg.focus("#cd_night")
        await pg.keyboard.press("Enter")
        await pg.wait_for_timeout(1200)
        dentro = []
        for _ in range(14):
            await pg.keyboard.press("Tab")
            dentro.append(await pg.evaluate(
                "(function(){ var p = document.querySelector('.ui-pnl');"
                " return !!p && p.contains(document.activeElement) })()"))
        lido["tab_preso"] = dentro
        await pg.keyboard.press("Escape")
        await pg.wait_for_timeout(500)
        await pg.evaluate("localStorage.setItem('radai_tema', 'claro'); true")
        await pg.goto(BASE + "/config", wait_until="networkidle")
        await pg.wait_for_timeout(1500)
        for ok in (u"true", u"false"):
            lido["msg_" + ok] = await pg.evaluate(
                u"(function(){ try{ msg('teste', %s) }catch(e){ return null }"
                u" return %s })()" % (ok, _JS_CONTRASTE % (json.dumps("#msg"),
                                                           u"null")))
        await pg.evaluate(
            "(function(){ ['ok','err','warn'].forEach(function(c){"
            " var d = document.createElement('div'); d.className = 'res ' + c;"
            " d.id = 'zz4b_' + c; d.textContent = 'resultado';"
            " (document.querySelector('.campo') || document.body).appendChild(d) });"
            " return true })()")
        for c in (u"ok", u"err", u"warn"):
            lido["res_" + c] = await pg.evaluate(
                _JS_CONTRASTE % (json.dumps("#zz4b_" + c), u"null"))
        lido["msg_isca"] = await pg.evaluate(
            _JS_CONTRASTE % (json.dumps("#msg"), json.dumps("#5bd07a")))
        lido["sem_onboarding"] = await pg.evaluate(
            "document.querySelectorAll('a[href=\"/onboarding\"]').length === 0")
    finally:
        await pg.set_viewport_size({"width": 1520, "height": 950})
        await pg.evaluate("localStorage.removeItem('radai_idioma');"
                          " localStorage.removeItem('radai_tema'); true")

    for lingua in (u"pt-BR", u"de"):
        c = lido.get("cabe_" + lingua) or {}
        checar(u"a 1600 px com a barra aberta a linha CABE (%s): tabela <= caixa"
               % lingua, c.get("tab") is not None and c["tab"] <= c["caixa"],
               repr(c))
        checar(u"  e o `?` da coluna Modo esta inteiro dentro da caixa (%s)"
               % lingua, c.get("aj_dentro") is True, repr(c))
    ci = lido.get("cabe_isca") or {}
    checar(u"  (isca) as acoes lado a lado e a descricao sem coluna voltam a "
           u"transbordar em alemao", ci.get("tab", 0) > ci.get("caixa", 10 ** 6),
           repr(ci))
    esperado_v = _molde_re(de.get(u"Voltar para %s", u"^$"))
    v = lido.get("voltar") or [u"", u""]
    checar(u"o Voltar em alemao: `title` e `aria-label` pelo molde, com o nome "
           u"da tela", bool(v[0]) and bool(esperado_v.match(v[0]))
           and v[0] == v[1], repr(v))
    vp = lido.get("voltar_pai") or [u"", u"", u""]
    checar(u"TEL-14: aberta direto, o Voltar cita a tela de cima em alemao",
           vp[2] == u"pai" and bool(esperado_v.match(vp[0] or u""))
           and u"Reconstruções" not in (vp[0] or u"") and vp[0] == vp[1], repr(vp))
    checar(u"o placeholder da busca do /ver sai em alemao",
           lido.get("ph") == de.get(u"cole o caminho da pasta, ou use o "
                                    u"Procurar ao lado"), repr(lido.get("ph")))
    checar(u"  (isca) placeholder sem chave fica como esta",
           lido.get("ph_isca") == u"zzqx dica sem chave zzqx",
           repr(lido.get("ph_isca")))
    checar(u"o link sem cor propria no escuro passa de 4,5:1",
           (lido.get("link") or 0) >= 4.5, repr(lido.get("link")))
    checar(u"  (isca) o azul do navegador fica abaixo do piso",
           (lido.get("link_isca") or 99) < 4.5, repr(lido.get("link_isca")))
    checar(u"a nota do /lote liga tambem as Reconstrucoes 3D",
           lido.get("link_3d") is True)
    tp = lido.get("tab_preso") or []
    checar(u"o painel do Overnight Run prende o Tab (%d passos, todos dentro)"
           % len(tp), bool(tp) and all(tp), repr(tp))
    for k in (u"msg_true", u"msg_false", u"res_ok", u"res_err", u"res_warn"):
        checar(u"a /config no claro: %s passa de 4,5:1" % k,
               (lido.get(k) or 0) >= 4.5, repr(lido.get(k)))
    checar(u"  (isca) o verde escrito a mao de antes fica abaixo do piso",
           (lido.get("msg_isca") or 99) < 4.5, repr(lido.get("msg_isca")))
    checar(u"o rodape da /config nao oferece o tutorial da v8.2",
           lido.get("sem_onboarding") is True)


_JS_AMOSTRA_DE_CONTRASTE = r"""(function(){
 function rgba(s){
  var m = String(s || '').match(/rgba?\(([^)]+)\)/);
  if(!m) return [0, 0, 0, 0];
  var p = m[1].split(/[\s,\/]+/).filter(Boolean).map(Number);
  return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1];
 }
 function sobre(a, b){
  var k = a[3];
  return [a[0] * k + b[0] * (1 - k), a[1] * k + b[1] * (1 - k), a[2] * k + b[2] * (1 - k), 1];
 }
 function lum(c){
  return [0, 1, 2].map(function(j){ var v = c[j] / 255;
   return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4) })
   .reduce(function(s, v, j){ return s + v * [0.2126, 0.7152, 0.0722][j] }, 0);
 }
 function razao(a, b){ var x = lum(a), y = lum(b);
  return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05) }
 function nome(e){
  var s = [], n = e;
  for(var k = 0; n && n.nodeType === 1 && k < 4; k++, n = n.parentElement){
   var t = n.tagName.toLowerCase();
   if(n.id){ s.unshift(t + '#' + n.id); break }
   var c = (typeof n.className === 'string') ? n.className.trim().split(/\s+/).slice(0, 2).join('.') : '';
   s.unshift(t + (c ? '.' + c : ''));
  }
  return s.join('>');
 }
 function dobrar(camadas){
  var f = [255, 255, 255, 1];
  for(var j = camadas.length - 1; j >= 0; j--) f = sobre(camadas[j], f);
  return f;
 }
 var IMAGEM = {IMG: 1, CANVAS: 1, VIDEO: 1};
 function pelaArvore(e){
  var camadas = [], solto = false;
  for(var q = e; q && q.nodeType === 1; q = q.parentElement){
   var qs = getComputedStyle(q);
   if(qs.backgroundImage && qs.backgroundImage !== 'none') return null;
   if(qs.position === 'absolute' || qs.position === 'fixed') solto = true;
   var f = rgba(qs.backgroundColor);
   if(f[3] > 0) camadas.push(f);
   if(f[3] >= 1) return {fundo: dobrar(camadas), solto: false};
  }
  return {fundo: dobrar(camadas), solto: solto};
 }
 function peloPonto(e){
  var r = e.getBoundingClientRect();
  if(r.bottom < 0 || r.top > innerHeight){ e.scrollIntoView({block: 'center'}); r = e.getBoundingClientRect() }
  var x = r.left + Math.min(r.width / 2, 8), y = r.top + r.height / 2;
  var camadas = [], fe = rgba(getComputedStyle(e).backgroundColor);
  if(fe[3] > 0) camadas.push(fe);
  if(fe[3] >= 1) return dobrar(camadas);
  var pilha = document.elementsFromPoint(x, y);
  for(var i = 0; i < pilha.length; i++){
   var z = pilha[i];
   if(z === e || e.contains(z)) continue;
   if(IMAGEM[z.tagName]) return null;
   var zs = getComputedStyle(z);
   if(zs.backgroundImage && zs.backgroundImage !== 'none') return null;
   var f = rgba(zs.backgroundColor);
   if(f[3] > 0) camadas.push(f);
   if(f[3] >= 1) break;
  }
  return dobrar(camadas);
 }
 function doIndicador(e){
  var b = e.closest('.ui-seg>button[aria-checked="true"],.ui-abas>button[aria-selected="true"]');
  if(!b) return null;
  var ind = b.parentNode.querySelector('.ui-seg-ind,.marca');
  if(!ind) return null;
  var base = pelaArvore(b.parentNode);
  return sobre(rgba(getComputedStyle(ind).backgroundColor), base ? base.fundo : [255, 255, 255, 1]);
 }
 var ruins = [], n = 0, vistos = {};
 var todos = document.body.querySelectorAll('*');
 var x0 = scrollX, y0 = scrollY;
 for(var i = 0; i < todos.length; i++){
  var e = todos[i], tag = e.tagName;
  if(tag === 'SCRIPT' || tag === 'STYLE' || tag === 'OPTION' || tag === 'TEMPLATE') continue;
  var txt = '';
  for(var c = e.firstChild; c; c = c.nextSibling)
   if(c.nodeType === 3) txt += c.nodeValue;
  txt = txt.replace(/\s+/g, ' ').trim();
  if(!txt || txt.length < 2) continue;
  if(e.closest('svg,select,.ui-seg-fonte,.ui-abas-fonte,[aria-hidden="true"],.radai-lang .lista')) continue;
  if(e.closest(':disabled,[aria-disabled="true"],.md-off,[inert]')) continue;
  var r = e.getBoundingClientRect();
  if(r.width < 1 || r.height < 1) continue;
  var cs = getComputedStyle(e);
  if(cs.visibility !== 'visible') continue;
  if(/rgba\(0, 0, 0, 0\)/.test(cs.webkitTextFillColor || '') || cs.color === 'rgba(0, 0, 0, 0)') continue;
  var op = 1;
  for(var p = e; p && p.nodeType === 1; p = p.parentElement){
   var ps = getComputedStyle(p);
   op *= Number(ps.opacity);
   if(ps.display === 'none'){ op = 0; break }
  }
  if(op < 0.05) continue;
  var fundo = doIndicador(e);
  if(!fundo){
   var a = pelaArvore(e);
   if(!a) continue;
   fundo = a.solto ? peloPonto(e) : a.fundo;
   if(!fundo) continue;
  }
  var cor = rgba(cs.color);
  cor[3] = cor[3] * op;
  var t = sobre(cor, fundo);
  var px = parseFloat(cs.fontSize), peso = parseInt(cs.fontWeight, 10) || 400;
  var minimo = (px >= 24 || (px >= 18.66 && peso >= 700)) ? 3 : 4.5;
  var k = razao(t, fundo);
  n++;
  if(k < minimo){
   var chave = nome(e) + '|' + txt.slice(0, 30);
   if(vistos[chave]) continue;
   vistos[chave] = 1;
   ruins.push({sel: nome(e), txt: txt.slice(0, 60), r: Math.round(k * 100) / 100, min: minimo});
  }
 }
 scrollTo(x0, y0);
 return {tema: document.documentElement.getAttribute('data-tema'), n: n, ruins: ruins};
})()"""

_ROTAS_DA_AMOSTRA = ("/", "/config", "/autocontorno", "/lote", "/ver", "/procedencia",
                     "/bibliografia", "/diagnostico", "/termos", "/politica-privacidade",
                     "/bridge", "/bridge/laudo", "/bridge/imagem", "/recon3d",
                     "/recon3d/anatomia", "/recon3d/toracica", "/recon3d/vascular",
                     "/nidus", "/nidus/projecao", "/elastic", "/elastic/fusao",
                     "/bolus", "/bolus/gerar")

_JS_TEMA_DA_TELA = ("[document.documentElement.getAttribute('data-tema'),"
                    " document.documentElement.getAttribute('data-tema-escolha')]")


async def _abrir_com_secoes(pg, rota, root):
    await pg.goto(BASE + rota, wait_until="networkidle")
    await pg.wait_for_timeout(1000)
    await pg.evaluate(
        "(function(){ document.querySelectorAll('.ps-cx.fechado').forEach(function(c){"
        " c.classList.remove('fechado') }); document.querySelectorAll('.ps-cx[hidden]')"
        ".forEach(function(c){ c.hidden = false }); return true })()")
    await pg.wait_for_timeout(250)
    if rota == "/lote":
        await _encher_pasta(pg, root)
        await pg.evaluate("varrer(); true")
        await pg.wait_for_timeout(3500)
        await pg.evaluate("if(SERIES.length && !noCarrinho(SERIES[0])) alternar(0); true")
        await pg.wait_for_timeout(400)


async def _temas_nas_telas(pg, root):
    secao(u"o tema: a escolha da Configuração vale em toda tela, e nenhuma perde contraste")
    lido = {}
    amostra = {}
    try:
        await pg.evaluate("localStorage.removeItem('radai_tema');"
                          " localStorage.setItem('radai_idioma', 'pt-BR'); true")
        await pg.emulate_media(color_scheme="dark")
        await _abrir_com_secoes(pg, "/config", root)
        lido["cfg_ini"] = await pg.evaluate(
            "(function(){ var b = document.querySelector('#opTema .ui-seg [aria-checked=true]');"
            " return [b ? b.getAttribute('data-v') : null,"
            " document.documentElement.getAttribute('data-tema')] })()")
        await pg.click("#opTema .ui-seg button[data-v='claro']")
        await pg.wait_for_timeout(300)
        lido["cfg_claro"] = await pg.evaluate(
            _JS_TEMA_DA_TELA[:-1] + ", localStorage.getItem('radai_tema'),"
            " document.getElementById('subTema').textContent.trim()]")
        for rota in ("/lote", "/nidus/projecao"):
            await pg.goto(BASE + rota, wait_until="networkidle")
            await pg.wait_for_timeout(400)
            lido["claro" + rota] = await pg.evaluate(_JS_TEMA_DA_TELA)
        await _abrir_com_secoes(pg, "/config", root)
        await pg.click("#opTema .ui-seg button[data-v='sistema']")
        await pg.wait_for_timeout(300)
        await pg.goto(BASE + "/lote", wait_until="networkidle")
        await pg.wait_for_timeout(400)
        lido["sis_escuro"] = await pg.evaluate(_JS_TEMA_DA_TELA)
        await pg.emulate_media(color_scheme="light")
        await pg.wait_for_timeout(300)
        lido["sis_claro"] = await pg.evaluate(_JS_TEMA_DA_TELA)
        await pg.goto(BASE + "/", wait_until="networkidle")
        await pg.wait_for_timeout(400)
        lido["porta"] = await pg.evaluate(_JS_TEMA_DA_TELA)
        for tema in (u"claro", u"escuro"):
            await pg.evaluate("localStorage.setItem('radai_tema', %s); true" % json.dumps(tema))
            for rota in _ROTAS_DA_AMOSTRA:
                await _abrir_com_secoes(pg, rota, root)
                amostra[(tema, rota)] = await pg.evaluate(_JS_AMOSTRA_DE_CONTRASTE)
        await pg.evaluate("localStorage.setItem('radai_tema', 'claro'); true")
        await _abrir_com_secoes(pg, "/config", root)
        await pg.evaluate(
            "(function(){ var p = document.createElement('p'); p.id = 'zz_isca_tema';"
            " p.textContent = 'texto claro de tela escura'; p.style.color = '#a3b1c6';"
            " (document.querySelector('.ps-corpo') || document.body).appendChild(p); return true })()")
        isca = await pg.evaluate(_JS_AMOSTRA_DE_CONTRASTE)
        lido["isca"] = [x for x in isca["ruins"] if u"zz_isca_tema" in x["sel"]]
    finally:
        await pg.emulate_media(color_scheme="light")
        await pg.evaluate("localStorage.removeItem('radai_tema');"
                          " localStorage.removeItem('radai_idioma'); true")

    checar(u"sem escolha, a Configuração marca Sistema e segue o sistema (escuro)",
           lido.get("cfg_ini") == [u"sistema", u"escuro"], repr(lido.get("cfg_ini")))
    checar(u"escolher Claro na Configuração pinta na hora, grava e diz no subtítulo",
           lido.get("cfg_claro") == [u"claro", u"claro", u"claro", u"— modo claro"],
           repr(lido.get("cfg_claro")))
    checar(u"  e vale nas outras telas (Rodar agora e Nidus), com o sistema escuro",
           lido.get("claro/lote") == [u"claro", u"claro"]
           and lido.get("claro/nidus/projecao") == [u"claro", u"claro"],
           repr([lido.get("claro/lote"), lido.get("claro/nidus/projecao")]))
    checar(u"Sistema: o Rodar agora abre escuro com o sistema escuro",
           lido.get("sis_escuro") == [u"escuro", u"sistema"], repr(lido.get("sis_escuro")))
    checar(u"  e passa a claro quando o sistema muda, sem recarregar",
           lido.get("sis_claro") == [u"claro", u"sistema"], repr(lido.get("sis_claro")))
    checar(u"a porta continua escura com o sistema claro (a arte dela é noturna)",
           (lido.get("porta") or [None])[0] == u"escuro", repr(lido.get("porta")))
    for tema in (u"claro", u"escuro"):
        medidas = [(r, amostra.get((tema, r)) or {}) for r in _ROTAS_DA_AMOSTRA]
        temas = set(m.get("tema") for r, m in medidas if r != "/")
        checar(u"[%s] as %d telas abriram no tema pedido" % (tema, len(medidas) - 1),
               temas == {tema}, repr(sorted(t for t in temas if t)))
        textos = sum(m.get("n") or 0 for r, m in medidas)
        checar(u"[%s] a amostra mediu texto de verdade" % tema, textos > 2000, str(textos))
        ruins = [(r, x) for r, m in medidas for x in (m.get("ruins") or [])]
        checar(u"[%s] nenhum texto abaixo de 4,5:1 (3:1 no grande) nas %d telas"
               % (tema, len(medidas)), not ruins,
               u"; ".join(u"%s %s «%s» %.2f" % (r, x["sel"][-40:], x["txt"][:24], x["r"])
                          for r, x in ruins[:5]))
    checar(u"  (isca) o cinza do tema escuro escrito à mão numa tela clara é acusado",
           len(lido.get("isca") or []) == 1, repr(lido.get("isca")))


def main():
    print(u"=" * 68)
    print(u"test_ui_interacao | o que a pessoa faz, num navegador de verdade")
    print(u"=" * 68)
    try:
        from playwright.async_api import async_playwright
    except Exception:
        print(u"\nPULADO: o Playwright nao esta neste runtime.")
        print(u"  Instale com:  .venv\\Scripts\\python.exe -m pip install playwright")
        print(u"  O que esta bateria guarda continua guardado pelas estruturais.")
        return 0
    chrome = _chromium()
    if not chrome:
        print(u"\nPULADO: nao achei um Chromium do Playwright nesta maquina.")
        print(u"  Instale com:  .venv\\Scripts\\python.exe -m playwright install chromium")
        return 0

    import asyncio
    import shutil
    import tempfile
    base_tmp = tempfile.mkdtemp(prefix="radai_ui_")
    proc = None
    try:
        proc, root = _subir(base_tmp)
        if not proc:
            print(u"\nPULADO: o vigia de teste nao subiu na porta %d." % PORTA)
            return 0

        erros = []

        async def _tudo():
            async with async_playwright() as p:
                nav = await p.chromium.launch(executable_path=chrome)
                ctx = await nav.new_context(
                    viewport={"width": 1520, "height": 950})
                pg = await ctx.new_page()
                pg.on("pageerror", lambda e: erros.append(str(e)[:160]))
                try:
                    try:
                        await _rodar(pg, root)
                    except Exception as e:
                        _msg = str(e).splitlines()[0][:200] if str(e) else u""
                        checar(u"a bateria chegou ao fim sem parar no meio",
                               False, u"%s: %s" % (type(e).__name__, _msg))
                    # GUARDA: as barras laterais se medem numa aba propria, mesmo se o roteiro de cima parou.
                    try:
                        await _barras_laterais(pg)
                    except Exception as e:
                        _msg = str(e).splitlines()[0][:200] if str(e) else u""
                        checar(u"as barras laterais chegaram ao fim sem parar no meio",
                               False, u"%s: %s" % (type(e).__name__, _msg))
                finally:
                    await nav.close()

        asyncio.run(_tudo())
        checar(u"nenhum erro de JavaScript em nenhuma tela", not erros,
               u"; ".join(erros[:3]))
    finally:
        if proc:
            try:
                proc.kill()
            except Exception:
                pass
        shutil.rmtree(base_tmp, ignore_errors=True)

    falhas = [(n, d) for n, ok, d in _R if not ok]
    print(u"\n" + u"=" * 68)
    if falhas:
        print(u"FALHOU: %d de %d checagens" % (len(falhas), len(_R)))
        for n, d in falhas:
            print(u"  - %s%s" % (n, (u"  [%s]" % d) if d else u""))
    else:
        print(u"OK: %d checagens, todas passaram" % len(_R))
    print(u"=" * 68)
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
