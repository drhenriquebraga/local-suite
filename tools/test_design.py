# -*- coding: utf-8 -*-
import io
import json
import os
import re
import sys
import traceback

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
APP = os.path.join(RAIZ, "app")
sys.path.insert(0, AQUI)
sys.path.insert(0, APP)

import _cleanup
_cleanup.adotar_prefixo('radai_design_')
import tempfile as _tempfile
import _componentes
os.environ["RADAI_CALIB_DIR"] = _tempfile.mkdtemp(prefix="radai_design_")
_CFG = os.path.join(os.environ["RADAI_CALIB_DIR"], "radai_watcher.config")
io.open(_CFG, "w", encoding="utf-8").write(u"ROOT=\n")
os.environ["RADAI_CONFIG"] = _CFG

_RESULTADOS = []


def checar(nome, condicao, detalhe=""):
    _RESULTADOS.append((nome, bool(condicao), detalhe))
    if not condicao:
        print(u"  FALHA  %s%s" % (nome, (u"  [%s]" % detalhe) if detalhe else u""))


def secao(t):
    print(u"\n─── %s %s" % (t, u"─" * max(0, 66 - len(t))))


def _sem_script(p):
    p = re.sub(r"(?s)<script.*?</script>", u" ", p)
    p = re.sub(r"(?s)<style.*?</style>", u" ", p)
    return re.sub(r"(?s)<!--.*?-->", u" ", p)


def _texto(p):
    import html
    return html.unescape(re.sub(r"<[^>]+>", u"", _sem_script(p)))


ALERTA_DA_PORTA = u"Ferramenta de apoio, não validada para uso clínico"

TAGS = {
    u"autocontorno": u"bancada de estudo",
    u"bridge": u"Ponte até o TPS",
    u"recon3d": u"Estudo anatômico",
    u"nidus": u"Projeção Sintética",
    u"elastic": u"Fusão elástica",
    u"bolus": u"Inovação",
}

ALERTAS = {
    u"autocontorno": u"Material de estudo — 100% local. Nenhuma imagem sai desta rede",
    u"bridge": u"Processamento 100% local",
    u"recon3d": u"Uso próprio dentro do app",
    u"nidus": (u"Construção geométrica a partir do desenho do usuário — "
               u"não é um volume de tratamento"),
    u"bolus": (u"O STL sai por ato declarado, como rascunho sujeito a revisão "
               u"física e médica — a dosimetria do material é obrigatória"),
}

FRASES = {
    u"bridge": (u"Diagnostica e transforma arquivos para a travessia do exame "
                u"externo ao sistema de planejamento"),
    u"recon3d": (u"Carregue os casos segmentados pelo módulo ContourLab para "
                 u"análise tridimensional"),
}

CARTOES = {
    (u"autocontorno", u"Rodar agora"): (
        u"Realiza segmentação de imagens de Tomografia e Ressonância. "
        u"Personalize o seu estudo de acordo com topografias, tasks (plugins) "
        u"e diferentes modelos."),
    (u"autocontorno", u"Ver segmentação"): (
        u"Avalie os resultados comparando diferentes processamentos em cortes "
        u"axiais lado a lado, e veja como eles se comportam."),
    (u"bridge", u"Converter imagens para o TPS"): (
        u"TPS não lê o exame externo? Carregue o estudo, escolha as séries e a "
        u"segmentação de cada uma, veja o diagnóstico e receba a série DICOM "
        u"pronta numa pasta nova."),
    (u"recon3d", u"Anatomia geral"): (
        u"Visualize cada órgão, com ajuste de transparências no visor 3D, além "
        u"da segmentação nos 3 planos (axial, sagital e coronal) e MIP e MinIP "
        u"com laje ajustável."),
    (u"recon3d", u"Anatomia torácica"): (
        u"Reconstrução das tarefas geradas pelo protocolo do ContourLab: Lobos, "
        u"mediastino, vascularização, algoritmo de nódulos pulmonares e muito "
        u"mais."),
    (u"recon3d", u"Vascular"): (
        u"Superfície, trajeto dos vasos e projeções bidimensionais sintéticas a "
        u"partir da segmentação de vasos"),
    (u"bolus", u"Gerar bólus"): (
        u"Defina um volume sobre a superfície e defina a região do bólus. "
        u"Ajuste para espessura anatômica, bloco em caixa projetado ou molde "
        u"(casca) para preenchimento com material de cera. Exporte em STL para "
        u"dosimetria."),
}

TAGS_DOS_CARTOES = {
    (u"bridge", u"Converter imagens para o TPS"): (
        u"várias séries", u"diagnóstico", u"segmentação na fila",
        u"JPEG e PNG", u"CD"),
}

SAIRAM = {
    u"bridge": (u"Converter imagem", u"Ajustar série para o TPS",
                u"Escolha o que exportar para o TPS",
                u"Escolha o que exportar", u"Conversão de imagens"),
    u"recon3d": (u"Oncologia torácica",),
    u"nidus": (u"Trilha de ensino",),
    u"elastic": (u"Onde a fusão falha",),
}

NO_BALAO = {
    u"recon3d": u"Esta tela não exporta",
    u"nidus": u"A interseção é uma construção geométrica",
    u"elastic": u"Este módulo não propaga contorno",
    u"bolus": u"Este módulo exporta um STL",
}


def _mini(chave):
    if chave == u"autocontorno":
        import radai_panel
        return radai_panel._costurar_home(radai_panel.pagina_inicial())
    import radai_router
    return radai_router.mini_pagina(chave)


def _porta():
    import radai_router
    return radai_router.montar_porta()


def _fronteira():
    import radai_porta
    return u" ".join(_texto(radai_porta.FRONTEIRA).split())


def teste_os_componentes_existem():
    secao(u"os componentes de radai_ui existem e chegam à página")
    import radai_ui as U
    folha = U.folha()
    for classe, oque in ((u".ui-guias", u"abas em pasta"),
                         (u".ui-envio", u"área de envio"),
                         (u".ui-fp-", u"explorador de pastas"),
                         (u".ui-modal", u"modal open/close"),
                         (u".ui-visor", u"visor de série"),
                         (u".ui-morfo", u"dropdown menu morph"),
                         (u".ui-organico", u"organic shimmer"),
                         (u".ui-fn-tag", u"tag de função"),
                         (u".ui-alerta", u"alerta de rodapé")):
        checar(u"a folha tem `%s` (%s)" % (classe, oque), classe in folha)
    i = U.COMPONENTES.index(u"@media (prefers-reduced-motion:reduce)")
    red = U.COMPONENTES[i:]
    for classe in (u".ui-guia", u".ui-envio", u".ui-modal", u".ui-morfo",
                   u".ui-organico"):
        checar(u"  `%s` para com movimento reduzido" % classe, classe in red)
    js = U.COMPONENTES_JS
    for f in (u"uiGuia", u"uiModal", u"uiVisor", u"uiMorfar", u"uiCarregando",
              u"uiEnvio", u"uiEnviarArquivos", u"uiExplorador"):
        checar(u"o JS tem `window.%s`" % f, (u"window.%s = function" % f) in js)
    pg = U.aplicar(u"<html><head><meta charset='utf-8'></head><body></body></html>")
    checar(u"a costura leva o JS dos componentes", u"radai-ui-comp-js" in pg)
    for n in U.ICONES_DOS_COMPONENTES:
        checar(u"  e o molde do ícone `%s`" % n, (u'id="ui-ico-%s"' % n) in pg)
        checar(u"  que é SVG desenhado", u"<svg" in U.icone(n))
    checar(u"o explorador pergunta ao servidor por POST",
           u"fetch('/api/lote/pastas', {method:'POST'" in js,
           u"caminho de paciente não viaja em GET")
    checar(u"  e nunca põe caminho na URL", u"/api/lote/pastas?" not in js)
    checar(u"a cor dos componentes vem das fichas (sem hexadecimal cru)",
           not re.search(r"#[0-9a-fA-F]{3,8}\b",
                         U.COMPONENTES.replace(u"#000", u"").replace(u"#e6edf7", u"")),
           u"o palco preto do visor e o texto sobre ele são os únicos")


def teste_os_helpers_montam_certo():
    secao(u"os helpers de marcação")
    import radai_ui as U
    g = U.guias(u"t1", [(u"a", u"Acervo local", u"<p>A</p>"),
                        (u"b", u"Aponte uma pasta", u"<p>B</p>")])
    checar(u"abas: um tablist", u'role="tablist"' in g)
    checar(u"  duas abas com aria-controls", g.count(u'role="tab"') == 2
           and g.count(u"aria-controls=") == 2)
    checar(u"  a primeira escolhida e a segunda escondida",
           u'aria-selected="true"' in g and u" hidden>" in g)
    checar(u"  o rótulo é chave do dicionário",
           u"<span data-radai-frase>Acervo local</span>" in g)
    t = U.cabeca_de_funcao(u"▶", u"Rodar agora", u"Uma frase.",
                           chave_modulo=u"autocontorno")
    checar(u"cabeça de função: a tag é o h1, na cor do módulo",
           u'<h1 class="ui-fn-tag"' in t and u"--mod-auto" in t)
    checar(u"  com UMA frase", t.count(u'class="ui-fn-frase"') == 1)
    a = U.alerta(u"Processamento <b>100% local</b>")
    checar(u"alerta: um bloco com o ponto", a.startswith(u'<div class="ui-alerta')
           and u'class="pt"' in a)
    e = U.area_de_envio(u"z1")
    checar(u"envio: pastas e arquivos", u"webkitdirectory" in e
           and u'data-envio="pasta"' in e and u'data-envio="arquivos"' in e)
    checar(u"  e nenhum campo de caminho", u'type="text"' not in e,
           u"o navegador não entrega caminho de disco, só conteúdo")
    checar(u"o item «em breve» saiu com os cartões que o usavam (sem chamador)",
           not hasattr(U, u"item_em_breve") and u".ui-breve" not in U.folha())


_BASE = u"http://design.radai.test"


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


_PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f"
        b"\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82")


def _servir(ctx, paginas, reg):
    from urllib.parse import urlsplit, parse_qs

    def atender(route):
        req = route.request
        u = urlsplit(req.url)
        c = u.path
        if c in paginas:
            route.fulfill(status=200, content_type=u"text/html; charset=utf-8",
                          body=paginas[c])
        elif c.startswith(u"/porta/"):
            import radai_porta as _P
            a = _P.arquivo(c[7:])
            if a:
                route.fulfill(status=200, content_type=a[1], body=a[0])
            else:
                route.fulfill(status=404, body=u"")
        elif c == u"/radai-idiomas.js":
            import radai_languages as _I
            route.fulfill(status=200, content_type=u"application/javascript",
                          body=_I.corpo_js())
        elif c == u"/api/lote/pastas":
            reg.setdefault("pastas", []).append((req.method, req.url,
                                                 req.post_data or u""))
            d = json.loads(req.post_data or u"{}")
            if d.get("unidades"):
                corpo = {"unidades": [{"raiz": u"C:\\", "tipo": "fixa", "ok": True}]}
            else:
                cam = d.get("caminho") or u""
                corpo = {"caminho": cam, "pai": u"C:\\" if cam != u"C:\\" else u"",
                         "pastas": ([{"nome": u"EXAMES", "caminho": u"C:\\EXAMES",
                                      "data": u"2026-10-01 08:00"}]
                                    if cam == u"C:\\" else [])}
            route.fulfill(status=200, content_type=u"application/json",
                          body=json.dumps(corpo))
        elif c == u"/api/fila":
            import radai_queue_state as QS
            card = {"tipo": "serie", "rotulo": u"PAC_A", "uid": u"1.2.3.4.55667788",
                    "pasta": u"C:\\EXAMES\\PAC_A\\CT", "estado": "esperando",
                    "dono": u"", "segundos": None,
                    "carga": {"pasta": u"C:\\EXAMES\\PAC_A\\CT", "modo": "auto",
                              "modalidade": "CT", "cortes": 120,
                              "desc": u"TORAX 5mm", "espessura_mm": 5.0,
                              "tasks": {"total_v3": 1, "lung_nodules": 0}}}
            route.fulfill(status=200, content_type=u"application/json",
                          body=json.dumps({"cards": QS.para_tela([card]),
                                           "resumo": {"esperando": 1}}))
        elif c == u"/api/lote/favorita":
            route.fulfill(status=200, content_type=u"application/json",
                          body=u'{"favorita": ""}')
        elif c == u"/envio":
            reg.setdefault("envio", []).append(req.post_data_buffer or b"")
            n = len(reg["envio"])
            route.fulfill(status=200, content_type=u"application/json",
                          body=json.dumps({"lote": "L1", "n": n}))
        elif c.startswith(u"/corte/"):
            reg.setdefault("cortes", []).append(
                (c.rsplit(u"/", 1)[-1], (parse_qs(u.query).get("jan") or [u""])[0]))
            route.fulfill(status=200, content_type=u"image/png", body=_PNG)
        else:
            route.fulfill(status=404, body=u"")
    ctx.route(_BASE + u"/**", atender)


def _pagina_de_componentes(isca=None):
    import radai_ui as U
    corpo = (u'<main style="padding:30px">'
             + U.cabeca_de_funcao(u"▶", u"Rodar agora", u"Uma frase.",
                                  chave_modulo=u"autocontorno")
             + U.guias(u"gt", [(u"acervo", u"Acervo local", u'<p id="pa">A</p>'),
                               (u"pasta", u"Aponte uma pasta", u'<p id="pb">B</p>')])
             + u'<div style="height:20px"></div>' + U.area_de_envio(u"zona")
             + u'<button type="button" id="bt_modal" class="ui-bt">abrir</button>'
             + u'<button type="button" id="bt_mais" class="ui-mais" '
               u'aria-expanded="false">' + U.icone(u"mais") + u'</button>'
             + u'<div id="caixa" style="width:300px;height:200px"></div>'
             + U.alerta(u"Processamento <b>100% local</b>")
             + u'</main><script>'
               u'uiEnvio("zona",{url:"/envio",porLote:2});'
               u'document.getElementById("bt_mais").addEventListener("click",'
               u'function(){uiMorfar(this,{html:"<dl><dt>Modo</dt><dd>AUTO</dd>'
               u'<dt>Cortes</dt><dd>120</dd><dt>Tasks</dt><dd>total</dd></dl>"})});'
               u'</script>')
    p = U.aplicar(u'<!doctype html><html><head><meta charset="utf-8"></head>'
                  u'<body>%s</body></html>' % corpo)
    if isca:
        de, para = isca
        checar(u"  (a isca acha o trecho que troca)", de in p, de[:60])
        p = p.replace(de, para)
    return p


def _nav(pw, exe, paginas, reg, larg=1280, alt=800):
    nav = pw.chromium.launch(executable_path=exe, headless=True)
    ctx = nav.new_context(viewport={"width": larg, "height": alt})
    _servir(ctx, paginas, reg)
    return nav, ctx


def _medir_abas(pg):
    pg.click(u"#gt-t-pasta")
    pg.wait_for_timeout(80)
    a = pg.evaluate(u"[document.getElementById('gt-p-acervo').hidden,"
                    u"document.getElementById('gt-p-pasta').hidden,"
                    u"document.getElementById('gt-t-pasta').getAttribute('aria-selected'),"
                    u"document.getElementById('gt').getAttribute('data-ativa')]")
    pg.focus(u"#gt-t-pasta")
    pg.keyboard.press(u"ArrowLeft")
    b = pg.evaluate(u"[document.activeElement.id,"
                    u"document.getElementById('gt-p-acervo').hidden]")
    return a, b


def _medir_envio(pg, reg):
    reg.pop("envio", None)
    pg.evaluate(u"""(function(){
      var l=[];
      for(var i=0;i<3;i++) l.push({arquivo:new File(['abc'+i],'IM'+i),
                                   caminho:'EXAME/CT/IM'+i});
      return uiEnviarArquivos('zona', l);
    })()""")
    pg.wait_for_timeout(300)
    corpos = reg.get("envio") or []
    tudo = b"".join(corpos).decode("latin-1")
    return (len(corpos), tudo,
            pg.evaluate(u"document.querySelector('#zona .ui-envio-est').textContent"))


def _medir_modal(pg):
    pg.focus(u"#bt_modal")
    pg.evaluate(u"window.__m = uiModal({titulo:'Teste', html:'<p>corpo</p>'"
                u"+'<button id=\"dentro\">ok</button>', "
                u"origem:document.getElementById('bt_modal')})")
    pg.wait_for_timeout(350)
    aberto = pg.evaluate(u"!!document.querySelector('.ui-modal-veu.vis')")
    dentro = pg.evaluate(u"document.querySelector('.ui-modal').contains(document.activeElement)")
    for _ in range(4):
        pg.keyboard.press(u"Tab")
    preso = pg.evaluate(u"document.querySelector('.ui-modal').contains(document.activeElement)")
    pg.keyboard.press(u"Escape")
    pg.wait_for_timeout(350)
    fechou = pg.evaluate(u"!document.querySelector('.ui-modal-veu')")
    voltou = pg.evaluate(u"document.activeElement && document.activeElement.id")
    return aberto, dentro, preso, fechou, voltou


def _medir_morfo(pg):
    pg.click(u"#bt_mais")
    pg.wait_for_timeout(450)
    exp = pg.get_attribute(u"#bt_mais", u"aria-expanded")
    canto = pg.evaluate(u"""(function(){
      var p=document.querySelector('.ui-morfo'); if(!p) return 'sem painel';
      var r=p.getBoundingClientRect();
      var e=document.elementFromPoint(r.left+6, r.bottom-6);
      return p.contains(e) ? 'painel' : 'fora';
    })()""")
    pg.mouse.click(5, 790)
    pg.wait_for_timeout(400)
    fora = pg.evaluate(u"!document.querySelector('.ui-morfo')") and \
        pg.get_attribute(u"#bt_mais", u"aria-expanded") == u"false"
    return exp, canto, fora


def _medir_organico(pg):
    pg.evaluate(u"uiCarregando('caixa', true, 'abrindo a série')")
    pg.wait_for_timeout(300)
    on = pg.evaluate(u"""(function(){var c=document.querySelector('#caixa .ui-organico');
      return c ? [getComputedStyle(c).opacity, c.textContent,
      document.getElementById('caixa').getAttribute('aria-busy')] : null})()""")
    pg.evaluate(u"uiCarregando('caixa', false)")
    pg.wait_for_timeout(350)
    cedo = pg.evaluate(u"!!document.querySelector('#caixa .ui-organico')")
    pg.wait_for_timeout(1900)
    off = cedo and pg.evaluate(u"!document.querySelector('#caixa .ui-organico')")
    return on, off


def _medir_visor(pg, reg):
    reg.pop("cortes", None)
    pg.evaluate(u"window.__v = uiVisor({titulo:'Série', total:9, "
                u"src:function(i,j){return '/corte/'+i+'?jan='+j}, "
                u"cabecalho:[['Modalidade','CT'],['Cortes','9']]})")
    pg.wait_for_timeout(400)
    ini = pg.evaluate(u"__v.corte()")
    caixa = pg.locator(u".ui-visor-img").bounding_box()
    pg.mouse.move(caixa["x"] + 20, caixa["y"] + 20)
    pg.mouse.wheel(0, 120)
    pg.wait_for_timeout(150)
    depois = pg.evaluate(u"__v.corte()")
    pg.click(u".ui-visor-jan button[data-jan='pulmao']")
    pg.wait_for_timeout(250)
    cab = pg.evaluate(u"document.querySelector('.ui-visor-cab').textContent")
    pg.keyboard.press(u"Escape")
    pg.wait_for_timeout(300)
    return ini, depois, list(reg.get("cortes") or []), cab


def _medir_explorador(pg, reg):
    reg.pop("pastas", None)
    pg.evaluate(u"window.__usou = null; uiExplorador({aoUsar:function(c){"
                u"window.__usou = c}})")
    pg.wait_for_timeout(500)
    pg.click(u".ui-fp-arvore .ui-fp-nm")
    pg.wait_for_timeout(400)
    itens = pg.evaluate(u"Array.prototype.map.call(document.querySelectorAll("
                        u"'.ui-fp-lista .ui-fp-item[data-c]'),function(x){"
                        u"return x.getAttribute('data-c')})")
    if itens:
        pg.click(u".ui-fp-lista .ui-fp-item[data-c]")
        pg.wait_for_timeout(400)
    pg.click(u".ui-fp-pe [data-fp='usar']")
    pg.wait_for_timeout(300)
    return itens, pg.evaluate(u"window.__usou"), list(reg.get("pastas") or [])


def teste_os_componentes_no_navegador():
    secao(u"os componentes, executados num Chromium")
    exe = _chromium()
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        sync_playwright = None
    if not exe or sync_playwright is None:
        print(u"    PULADO o navegador: sem Playwright ou sem Chromium")
        return
    reg = {}
    paginas = {u"/c": _pagina_de_componentes()}
    with sync_playwright() as pw:
        nav, ctx = _nav(pw, exe, paginas, reg)
        try:
            pg = ctx.new_page()
            erros = []
            pg.on("pageerror", lambda e: erros.append(str(e)))
            pg.goto(_BASE + u"/c", wait_until="networkidle")

            a, b = _medir_abas(pg)
            checar(u"abas: o clique troca o painel", a[0] is True and a[1] is False,
                   repr(a))
            checar(u"  marca a aba e o contêiner", a[2] == u"true" and a[3] == u"pasta",
                   repr(a))
            checar(u"  a seta anda e leva o foco", b[0] == u"gt-t-acervo"
                   and b[1] is False, repr(b))
            n, tudo, est = _medir_envio(pg, reg)
            checar(u"envio: três arquivos em dois lotes de no máximo dois", n == 2,
                   str(n))
            checar(u"  cada parte leva o caminho RELATIVO com a pasta",
                   u'filename="EXAME/CT/IM0"' in tudo and u'filename="EXAME/CT/IM2"' in tudo,
                   tudo[:200])
            checar(u"  o `caminhos` vai junto, em JSON",
                   u'["EXAME/CT/IM0","EXAME/CT/IM1"]' in tudo)
            checar(u"  o segundo lote leva o `lote` que o servidor deu",
                   u'name="lote"\r\n\r\nL1' in tudo)
            checar(u"  e o último diz que é o último", u'name="ultimo"\r\n\r\n1' in tudo)
            checar(u"  a área diz que enviou", u"enviado" in (est or u""), est)
            checar(u"modal: abre, com o foco dentro, e prende o Tab",
                   _ok_modal(_medir_modal(pg)), u"")
            exp, canto, fora = _medir_morfo(pg)
            checar(u"morph: o botão diz que abriu", exp == u"true", exp)
            checar(u"  o painel abre inteiro (o canto de baixo é dele)",
                   canto == u"painel", canto)
            checar(u"  e o clique fora fecha", fora)
            on, off = _medir_organico(pg)
            checar(u"orgânico: o véu aparece com o texto e marca ocupado",
                   on and float(on[0]) > 0.5 and u"abrindo a série" in on[1]
                   and on[2] == u"true", repr(on))
            checar(u"  e sai quando desliga, depois dos 2 s mínimos (e não antes)", off)
            ini, depois, cortes, cab = _medir_visor(pg, reg)
            checar(u"visor: abre no corte do meio", ini == 4, str(ini))
            checar(u"  a roda anda um corte", depois == 5, str(depois))
            checar(u"  a janela vai no pedido da imagem",
                   (u"5", u"pulmao") in cortes, repr(cortes[-3:]))
            checar(u"  o cabeçalho está lá", u"Modalidade" in cab and u"CT" in cab, cab)
            itens, usou, pedidos = _medir_explorador(pg, reg)
            checar(u"explorador: a unidade abre a pasta", itens == [u"C:\\EXAMES"],
                   repr(itens))
            checar(u"  «Usar esta pasta» devolve o caminho escolhido",
                   usou == u"C:\\EXAMES", repr(usou))
            checar(u"  todo pedido é POST, sem caminho na URL",
                   pedidos and all(m == u"POST" and u"?" not in url
                                   for m, url, _c in pedidos), repr(pedidos[:2]))
            checar(u"nenhum erro de JavaScript na página", not erros, repr(erros))
            pg.close()
        finally:
            ctx.close()
            nav.close()

        secao(u"as iscas dos componentes")
        iscas = (
            (u"abas sem a troca do painel", u"if(p) p.hidden = !sel;", u"",
             lambda pg, reg: _medir_abas(pg)[0][1] is False),
            (u"envio sem o caminho relativo",
             u"fd.append('arquivos', x.arquivo, x.caminho);",
             u"fd.append('arquivos', x.arquivo);",
             lambda pg, reg: u'filename="EXAME/CT/IM0"' in _medir_envio(pg, reg)[1]),
            (u"modal sem o Esc", u"if(e.key === 'Escape'){ e.preventDefault(); e.stopPropagation(); fechar() }",
             u"if(false){}",
             lambda pg, reg: _ok_modal(_medir_modal(pg))),
            (u"morph que não abre", u"requestAnimationFrame(function(){ p.classList.add('aberto') });\n  setTimeout(function(){ p.classList.add('aberto') }, 40);",
             u"",
             lambda pg, reg: _medir_morfo(pg)[1] == u"painel"),
            (u"visor sem a roda", u"ir(i + rumoCaudal(e.deltaY > 0 ? 1 : -1));",
             u"",
             lambda pg, reg: _medir_visor(pg, reg)[1] == 5),
            (u"explorador que devolve vazio", u"try{ if(o.aoUsar) o.aoUsar(c) }",
             u"try{ if(o.aoUsar) o.aoUsar('') }",
             lambda pg, reg: _medir_explorador(pg, reg)[1] == u"C:\\EXAMES"),
        )
        for nome, de, para, passa in iscas:
            reg = {}
            nav, ctx = _nav(pw, exe, {u"/c": _pagina_de_componentes((de, para))}, reg)
            try:
                pg = ctx.new_page()
                pg.goto(_BASE + u"/c", wait_until="networkidle")
                try:
                    r = passa(pg, reg)
                except Exception:
                    r = False
                checar(u"(isca) %s reprova" % nome, not r)
            finally:
                ctx.close()
                nav.close()


def _ok_modal(m):
    aberto, dentro, preso, fechou, voltou = m
    return aberto and dentro and preso and fechou and voltou == u"bt_modal"


def teste_a_porta():
    secao(u"a porta: um título, seis cartões, o rodapé e a engrenagem com o Fechar")
    import html as _h
    p = _porta()
    m = _sem_script(p)
    topo = re.search(r'(?s)<header class="ls-topo.*?</header>', m)
    topo = topo.group(0) if topo else u""
    eng = re.search(r'(?s)<details class="ls-engrenagem" data-radai-engrenagem>.*?</details>',
                    topo)
    eng = eng.group(0) if eng else u""
    checar(u"o cabeçalho da porta tem a engrenagem, com Configurações",
           u'href="/config"' in eng, topo[-300:])
    checar(u"  e a âncora do FECHAR APP dentro dela",
           u"data-radai-encerrar" in eng
           and u"data-radai-encerrar" not in m.replace(eng, u""))
    checar(u"sem o trilho", u'class="radai-menu' not in m)
    checar(u"um título só", len(re.findall(r"<h1\b", m)) == 1)
    checar(u"a grade de módulos", u'class="ls-cards"' in m)
    n = len(re.findall(r'class="ls-card tool-card', m))
    checar(u"  com os seis módulos", n == 6, str(n))
    t = u" ".join(_texto(p).split())
    checar(u"o rodapé traz a fronteira do autor, com «sugestão não aprovada»",
           _fronteira() in t and u"sugestão não aprovada" in t.lower())
    checar(u"  ela está UMA vez", t.count(_fronteira()) == 1)
    checar(u"o nome do autor está na porta", u"Henrique Braga" in t)


def _cartoes(p):
    import html
    fora = []
    for bloco in re.findall(r'(?s)<(?:a|div) class="md-fer[^"]*".*?</(?:a|div)>\s*(?=<(?:a|div) class="md-fer|</div>)',
                            _sem_script(p)):
        nome = re.search(r"<h2[^>]*>(.*?)</h2>", bloco)
        txt = re.search(r"<p(?:\s[^>]*)?>(.*?)</p>", bloco)
        tags = re.findall(r"<span>([^<]*)</span>", bloco.split(u'class="tags"')[-1]) \
            if u'class="tags"' in bloco else []
        fora.append((html.unescape(nome.group(1)) if nome else u"",
                     html.unescape(txt.group(1)) if txt else u"",
                     tuple(html.unescape(x) for x in tags)))
    return fora


def teste_as_mini_paginas():
    secao(u"as mini-páginas: tag, frase, cartões, alerta e `?`")
    import html
    import radai_modules as M
    for chave in (u"autocontorno", u"bridge", u"recon3d", u"nidus", u"elastic",
                  u"bolus"):
        p = _mini(chave)
        m = _sem_script(p)
        chip = re.search(r'<span class="md-chip">(.*?)</span>\s*<div class="md-tit"', m, re.S)
        chip_t = html.unescape(re.sub(r"<[^>]+>", u"", chip.group(1))).strip() if chip else u""
        checar(u"%s: a tag é «%s»" % (chave, TAGS[chave]),
               chip_t.endswith(TAGS[chave]) and u"·" not in chip_t, chip_t)
        if chave in FRASES:
            checar(u"  a frase do autor", FRASES[chave] in _texto(p))
        alertas = re.findall(r'<div class="ui-alerta[^"]*">.*?</span></div>', m, re.S)
        checar(u"  UM alerta, numa linha com o ponto", len(alertas) == 1,
               str(len(alertas)))
        if alertas:
            at = html.unescape(re.sub(r"<[^>]+>", u"", alertas[0])).strip()
            if chave in ALERTAS:
                checar(u"  o alerta é o do autor", at == ALERTAS[chave], at)
            checar(u"  e não repete o da porta", _fronteira() not in at)
            checar(u"  ele vem DEPOIS dos cartões",
                   m.index(alertas[0]) > m.rindex(u'class="md-fer'))
        checar(u"  nenhum parágrafo longo à vista (foi para o `?`)",
               u'<p class="md-semexp"' not in m)
        if chave in NO_BALAO:
            bal = re.search(r'(?s)<div class="md-tit">.*?</h1>.*?</span></span></div>', m)
            bal = html.unescape(re.sub(r"<[^>]+>", u"", bal.group(0))) if bal else u""
            checar(u"  o texto longo mora no `?` do título",
                   NO_BALAO[chave] in bal, NO_BALAO[chave])
        cs = _cartoes(p)
        nomes = [c[0] for c in cs]
        for (mod, nome), texto in CARTOES.items():
            if mod != chave:
                continue
            achou = [c for c in cs if c[0] == nome]
            checar(u"  o cartão «%s» existe" % nome, bool(achou), repr(nomes))
            if achou:
                checar(u"    com o texto do autor", achou[0][1] == texto, achou[0][1])
                if (mod, nome) in TAGS_DOS_CARTOES:
                    checar(u"    e as tags pedidas",
                           achou[0][2] == TAGS_DOS_CARTOES[(mod, nome)], repr(achou[0][2]))
        for nome in SAIRAM.get(chave, ()):
            checar(u"  o cartão «%s» saiu" % nome, nome not in nomes, repr(nomes))
    checar(u"o primeiro cartão do DicomBridge é a conversão",
           M.FERRAMENTAS[u"bridge"][0][2] == u"Converter imagens para o TPS")
    bol = [f for f in M.FERRAMENTAS[u"bolus"] if f[0] == u"bolus_gerar"][0]
    checar(u"o bólus perdeu as tags LPS e «ato declarado», e ganhou outra",
           u"LPS" not in bol[6] and u"ato declarado" not in bol[6]
           and len(bol[6]) >= 3, repr(bol[6]))
    recon = M.secoes_de_ajuda(u"recon3d")
    todo = u" ".join(u" ".join(v) for v in recon.values())
    checar(u"o `?` das Reconstruções não fala mais de vídeo",
           u"vídeo" not in todo, todo[:120])


def teste_as_frases_novas_tem_os_doze_idiomas():
    secao(u"toda frase nova está no dicionário, nos doze idiomas")
    import radai_phrases as F
    tab = dict((t[0], t) for t in F.TABELA)
    novas = [ALERTA_DA_PORTA, _fronteira()] + list(TAGS.values()) \
        + list(ALERTAS.values()) \
        + list(FRASES.values()) + list(CARTOES.values()) \
        + [n for (_m, n) in CARTOES] \
        + [u"Arraste para cá, ou clique para carregar",
           u"Pastas, vários arquivos ou um .zip do exame",
           u"Escolher arquivos", u"Escolher pasta", u"arquivo(s)", u"enviando",
           u"enviado", u"o envio falhou", u"nada para enviar",
           u"O que sai daqui", u"camada 1-30 mm", u"Espessura",
           u"detalhes do pedido",
           u"Não exporta malha nem estrutura. Uso próprio, dentro do app."]
    import html as _h
    import radai_modules as M
    for k, v in M.SEM_EXPORTACAO.items():
        novas.append(_h.unescape(re.sub(r"<[^>]+>", u"", v)).strip())
    def traduzida(f):
        t = tab.get(f)
        return t is not None and len(t) == 12 and all(x and x.strip() for x in t)
    for f in novas:
        if f in PENDENTES_DE_TRADUCAO:
            continue
        checar(u"«%s»" % f[:60], traduzida(f), f)
    for f in PENDENTES_DE_TRADUCAO:
        checar(u"pendente de tradução ainda sem os doze idiomas (tire da lista "
               u"quando traduzir): «%s»" % f[:50], not traduzida(f), f)


PENDENTES_DE_TRADUCAO = frozenset()


RISCO_DO_APLICADOR = (u"acessório de tratamento", u"rascunho",
                      u"revisão física e médica", u"segunda TC",
                      u"teste de passagem", u"plano")


def _risco_que_falta(texto):
    t = u" ".join((texto or u"").split())
    return [p for p in RISCO_DO_APLICADOR if p not in t]


def teste_o_bolus_diz_o_aplicador_e_o_risco():
    secao(u"3D Printed Bolus: os textos da Suite dizem o aplicador, e o risco")
    import html as _h
    import radai_modules as M
    m = M.MODULOS[u"bolus"]
    checar(u"a frase da porta e da mini-página nomeia o aplicador de "
           u"superfície e diz que é acessório de tratamento",
           u"aplicador de superfície" in m[u"frase"]
           and u"acessório de tratamento" in m[u"frase"]
           and u"rascunho" in m[u"frase"], m[u"frase"])
    bol = [f for f in M.FERRAMENTAS[u"bolus"] if f[0] == u"bolus_gerar"][0]
    checar(u"a tag do cartão nomeia o aplicador",
           u"aplicador de superfície" in bol[6], repr(bol[6]))
    nao = u" ".join(M.AJUDA[u"bolus"][u"O que não faz"])
    checar(u"o «O que não faz» diz o aplicador com o risco inteiro",
           u"aplicador" in nao and not _risco_que_falta(nao),
           _risco_que_falta(nao))
    checar(u"  e o «não é para uso clínico» fica com o bólus, sem negar o "
           u"aplicador", u"O bólus não é para uso clínico" in nao)
    fronteira = _h.unescape(re.sub(r"<[^>]+>", u"", M.SEM_EXPORTACAO[u"bolus"]))
    checar(u"a fronteira diz o .zip do aplicador e o risco inteiro",
           u"aplicador de superfície" in fronteira and u".zip" in fronteira
           and not _risco_que_falta(fronteira), _risco_que_falta(fronteira))
    checar(u"(isca) o texto de antes, sem o aplicador, reprova",
           bool(_risco_que_falta(
               u"Não é para uso clínico. Não grava RTSTRUCT e não calcula "
               u"dose. Para o plano considerar o bólus, o físico faz uma TC "
               u"com ele posto.")))


def teste_a_conversao_de_imagens_tem_destaque():
    secao(u"DicomBridge: um cartão só, o pipeline, e o destaque continua desenhável")
    import radai_modules as M
    p = M.pagina(u"bridge")
    cart = re.findall(r'<a class="(md-fer[^"]*)" href="([^"]+)"', p)
    checar(u"a mini-página do DicomBridge tem UM cartão, o pipeline, sem destaque",
           cart == [(u"md-fer", u"/bridge/laudo")], repr(cart))
    original = M.EM_DESTAQUE
    try:
        M.EM_DESTAQUE = frozenset((u"bridge_laudo",))
        isca = re.findall(r'<a class="(md-fer[^"]*)" href="([^"]+)"', M.pagina(u"bridge"))
    finally:
        M.EM_DESTAQUE = original
    checar(u"  (isca) o cartão em EM_DESTAQUE leva a classe do destaque",
           isca == [(u"md-fer destaque", u"/bridge/laudo")], repr(isca))
    checar(u"a folha desenha o destaque na cor do módulo",
           u".md-fer.destaque{" in M.CSS and u"--md-cor-fraco" in M.CSS
           and u"--md-cor-fraco:var(--mod-bridge-fraco)" in p)


def teste_a_geometria_no_navegador():
    secao(u"a geometria: a porta sem rolar e as mini-páginas alinhadas")
    exe = _chromium()
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        sync_playwright = None
    if not exe or sync_playwright is None:
        print(u"    PULADO o navegador: sem Playwright ou sem Chromium")
        return
    paginas = {u"/": _porta()}
    rotas = {u"autocontorno": u"/autocontorno", u"bridge": u"/bridge",
             u"recon3d": u"/recon3d", u"nidus": u"/nidus", u"elastic": u"/elastic",
             u"bolus": u"/bolus"}
    for k, r in rotas.items():
        paginas[r] = _mini(k)
    reg = {}
    with sync_playwright() as pw:
        nav, ctx = _nav(pw, exe, paginas, reg, 1280, 680)
        try:
            pg = ctx.new_page()
            pg.goto(_BASE + u"/", wait_until="networkidle")
            pg.wait_for_timeout(300)
            medir = u"""(function(){
              var cs=document.querySelectorAll('.ls-card');
              var xs={}, ys={};
              Array.prototype.forEach.call(cs,function(c){var r=c.getBoundingClientRect();
                xs[Math.round(r.left)]=1; ys[Math.round(r.top)]=1});
              var a=document.querySelector('.ls-rodape').getBoundingClientRect();
              return [Object.keys(xs).length, Object.keys(ys).length,
                      Math.round(a.bottom), innerHeight,
                      document.documentElement.scrollHeight]})()"""
            g = pg.evaluate(medir)
            checar(u"a porta: três colunas", g[0] == 3, repr(g))
            checar(u"  duas linhas", g[1] == 2, repr(g))
            checar(u"  e o rodapé à vista sem rolar, a 1280 × 680",
                   g[2] <= g[3] and g[4] <= g[3] + 1, repr(g))
            pg.set_viewport_size({"width": 1280, "height": 720})
            pg.wait_for_timeout(250)
            g = pg.evaluate(medir)
            checar(u"  e a 1280 × 720", g[2] <= g[3] and g[4] <= g[3] + 1
                   and g[0] == 3 and g[1] == 2, repr(g))
            pg.set_viewport_size({"width": 780, "height": 900})
            pg.wait_for_timeout(250)
            g = pg.evaluate(medir)
            checar(u"  até 800 px: duas colunas e três linhas",
                   g[0] == 2 and g[1] == 3, repr(g))
            pg.set_viewport_size({"width": 1280, "height": 680})
            pg.wait_for_timeout(150)
            geo = {}
            for k, r in rotas.items():
                pg.goto(_BASE + r, wait_until="networkidle")
                pg.wait_for_timeout(200)
                barra = pg.evaluate(u"""(function(){
                  var b=document.querySelector('.radai-tarefas');
                  return [!!b, b ? !document.documentElement.classList
                          .contains('dir-recolhida') : null]})()""")
                checar(u"%s: a barra da fila está na mini-página, recolhida de partida" % k,
                       barra[0] and barra[1] is False, repr(barra))
                # GUARDA: mede o molde com a barra no mesmo estado; aberta, ela desloca o centro.
                pg.evaluate(u"window.uiDireita && window.uiDireita('1')")
                pg.wait_for_timeout(150)
                geo[k] = pg.evaluate(u"""(function(){
                  var c=document.querySelector('.md-chip').getBoundingClientRect();
                  var h=document.querySelector('.md-tit h1').getBoundingClientRect();
                  var a=document.querySelector('.ui-alerta');
                  var ar=a?a.getBoundingClientRect():{height:0};
                  var fs=a?parseFloat(getComputedStyle(a).lineHeight)||18:18;
                  return [Math.round(c.left), Math.round(c.top), Math.round(h.left),
                          Math.round(h.top - c.bottom), Math.round(ar.height), fs,
                          document.documentElement.scrollWidth, innerWidth]})()""")
            ref = geo[u"autocontorno"]
            for k, v in geo.items():
                checar(u"%s: a tag no mesmo lugar do ContourLab" % k,
                       abs(v[0] - ref[0]) <= 1 and abs(v[1] - ref[1]) <= 1,
                       u"%r contra %r" % (v[:2], ref[:2]))
                checar(u"  respiro de linha dupla entre a tag e o título",
                       v[3] >= 24, str(v[3]))
                checar(u"  o alerta numa linha só", 0 < v[4] <= v[5] * 1.5 + 17,
                       repr(v[4:6]))
                checar(u"  sem rolagem lateral", v[6] <= v[7], repr(v[6:]))
        finally:
            ctx.close()
            nav.close()


def teste_o_alerta_sobrevive_a_traducao():
    secao(u"o alerta traduzido continua com o ponto amarelo")
    exe = _chromium()
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        sync_playwright = None
    if not exe or sync_playwright is None:
        print(u"    PULADO o navegador: sem Playwright ou sem Chromium")
        return
    pag = _mini(u"bolus")
    isca = pag.replace(u'<div class="ui-alerta', u'<p class="ui-alerta', 1)
    with sync_playwright() as pw:
        nav, ctx = _nav(pw, exe, {u"/bolus": pag, u"/isca": isca}, {})
        try:
            pg = ctx.new_page()
            pg.goto(_BASE + u"/bolus", wait_until="networkidle")
            pg.evaluate(u"localStorage.setItem('radai_idioma','en'); true")
            def medir(rota):
                pg.goto(_BASE + rota, wait_until="networkidle")
                pg.wait_for_timeout(1200)
                return pg.evaluate(u"""(function(){var a=document.querySelector('.ui-alerta');
                  return a ? [a.querySelectorAll('.pt').length, a.textContent.trim()] : [0,'']})()""")
            m = medir(u"/bolus")
            checar(u"em inglês, o alerta do bólus está traduzido",
                   m[1].startswith(u"The STL"), m[1][:80])
            checar(u"  e o ponto amarelo continua lá", m[0] == 1, repr(m))
            checar(u"(isca) o alerta em `<p>` perde o ponto na tradução",
                   medir(u"/isca")[0] == 0)
        finally:
            ctx.close()
            nav.close()


def _pagina_com_barra():
    import radai_menu
    return radai_menu.aplicar(u'<!doctype html><html><head><meta charset="utf-8">'
                              u'</head><body><main>x</main></body></html>', u"lote")


def _medir_barra(pg):
    return pg.evaluate(u"""(function(){
      var t=document.querySelector('.radai-tarefas .dir-abas');
      var ab=document.querySelectorAll('.radai-tarefas .dir-aba');
      var r=t.getBoundingClientRect(), a=ab[0].getBoundingClientRect(),
          b=ab[1].getBoundingClientRect();
      var meio=(a.left+b.right)/2, centro=(r.left+r.right)/2;
      var sa=getComputedStyle(ab[0]), sb=getComputedStyle(ab[1]);
      var antes=getComputedStyle(ab[0],'::before');
      return [Math.round(Math.abs(meio-centro)),
              Math.round(Math.max(a.width,b.width)/r.width*100),
              sa.backgroundColor !== sb.backgroundColor,
              parseFloat(sa.borderTopLeftRadius) > 0,
              antes.backgroundColor, sa.borderTopStyle]})()""")


def teste_as_abas_da_barra_da_direita():
    secao(u"a barra da direita: abas em pasta, perto do centro (R16, R25)")
    exe = _chromium()
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        sync_playwright = None
    if not exe or sync_playwright is None:
        print(u"    PULADO o navegador: sem Playwright ou sem Chromium")
        return
    reg = {}
    p = _pagina_com_barra()
    with sync_playwright() as pw:
        nav, ctx = _nav(pw, exe, {u"/b": p, u"/isca": p.replace(
            u".radai-tarefas .dir-abas{position:relative;flex:0 0 auto;display:flex;\n"
            u" align-items:stretch;justify-content:center;",
            u".radai-tarefas .dir-abas{position:relative;flex:0 0 auto;display:flex;\n"
            u" align-items:stretch;justify-content:flex-start;").replace(
            u".radai-tarefas .dir-aba{position:relative;z-index:1;flex:1 1 0;",
            u".radai-tarefas .dir-aba{position:relative;z-index:1;flex:0 1 auto;")},
            reg)
        try:
            pg = ctx.new_page()
            pg.goto(_BASE + u"/b", wait_until="networkidle")
            m = _medir_barra(pg)
            checar(u"as duas abas ficam no centro da barra", m[0] <= 16, repr(m))
            checar(u"  nenhuma toma a barra inteira", m[1] <= 64, repr(m))
            checar(u"  a escolhida se distingue pelo fundo (aba de pasta)", m[2], repr(m))
            checar(u"  com o canto de cima arredondado", m[3], repr(m))
            checar(u"  e o traço de cor em cima", u"rgba(0, 0, 0, 0)" not in m[4], repr(m))
            pg.goto(_BASE + u"/isca", wait_until="networkidle")
            checar(u"(isca) as abas encostadas à esquerda reprovam",
                   _medir_barra(pg)[0] > 16)
        finally:
            ctx.close()
            nav.close()


def _serie_da_varredura():
    import types
    import radai_batch as B
    ds = types.SimpleNamespace(
        Modality="CT", SeriesInstanceUID=u"1.2.99.7.7", PatientID=u"X",
        SeriesDescription=u"TORAX 5mm", SliceThickness=5.0, SeriesNumber=3,
        ImagePositionPatient=[0.0, 0.0, 0.0],
        ImageOrientationPatient=[1, 0, 0, 0, 1, 0])
    achados = {}
    B._juntar(achados, ds, u"C:\\P\\X")
    s = achados[u"1.2.99.7.7"]
    d = dict((k, v) for k, v in s.items() if not k.startswith(u"_"))
    d["modo"] = "auto"
    return d


def teste_o_mais_do_card_da_fila():
    secao(u"o «+» do card da fila abre os detalhes do pedido (R17)")
    import radai_queue_state as QS
    card = {"tipo": "serie", "rotulo": u"X", "uid": u"9" * 30,
            "pasta": u"C:\\P\\X", "estado": "esperando",
            "carga": {"pasta": u"C:\\P\\X", "modo": "perso", "modalidade": "MR",
                      "desc": u"C:\\outra\\pasta", "cortes": 40,
                      "protocolos": [{"cod": "mama"}], "tasks": {"a": 1, "b": 0}}}
    t = QS.para_tela([card])[0]
    txt = json.dumps(t)
    checar(u"o detalhe leva modo, modalidade, cortes, protocolos e as tasks ligadas",
           t.get("detalhe") == {"modo": "perso", "modalidade": "MR", "cortes": 40,
                                "protocolos": ["mama"], "tasks": ["a"]},
           repr(t.get("detalhe")))
    checar(u"  e nenhum caminho de disco viaja", u"P\\\\X" not in txt
           and u"outra" not in txt, txt[:200])
    checar(u"  (isca) a carga inteira levaria o caminho",
           u"outra" in json.dumps(card["carga"]))
    serie = _serie_da_varredura()
    d = QS.detalhe_publico(serie)
    checar(u"a série da varredura de verdade leva a descrição ao detalhe",
           d.get("descricao") == u"TORAX 5mm", repr(d))
    checar(u"  e a espessura", d.get("espessura") == 5.0, repr(d))
    checar(u"  (isca) com as chaves inventadas, nem uma nem outra chegariam",
           "descricao" not in serie and "espessura" not in serie,
           u", ".join(sorted(serie)))
    exe = _chromium()
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        sync_playwright = None
    if not exe or sync_playwright is None:
        print(u"    PULADO o navegador: sem Playwright ou sem Chromium")
        return
    with sync_playwright() as pw:
        nav, ctx = _nav(pw, exe, {u"/b": _pagina_com_barra()}, {})
        try:
            pg = ctx.new_page()
            pg.goto(_BASE + u"/b", wait_until="networkidle")
            pg.wait_for_timeout(600)
            n = pg.locator(u"#radai_fila .cd .ui-mais").count()
            checar(u"o card da série tem o «+»", n == 1, str(n))
            if n:
                pg.click(u"#radai_fila .cd .ui-mais")
                pg.wait_for_timeout(450)
                m = pg.evaluate(u"(document.querySelector('.ui-morfo')||{}).textContent||''")
                checar(u"  e ele abre o detalhe com o modo e a modalidade",
                       u"AUTO" in m and u"CT" in m and u"120" in m and u"total_v3" in m, m)
                checar(u"  com a descrição e a espessura da série",
                       u"TORAX 5mm" in m and u"5,00 mm" in m, m)
                checar(u"  sem a task desligada", u"lung_nodules" not in m, m)
                checar(u"  e o botão diz que abriu",
                       pg.get_attribute(u"#radai_fila .cd .ui-mais", u"aria-expanded") == u"true")
        finally:
            ctx.close()
            nav.close()


TELAS_DE_FUNCAO = {
    u"R3": u"app/radai_batch.py",
    u"V1": u"app/radai_view.py",
    u"N5": u"app/radai_nidus_screen.py",
    u"X1": u"app/radai_elastic_screen.py",
    u"O8": u"app/radai_bolus_screen.py",
    u"B8": u"app/radai_bridge.py",
}
# GUARDA: reprova nos dois sentidos — a tela que ainda não chama a cabeça e
# saiu da lista, e a que passou a chamar e continua nela.
PENDENTES_DA_CABECA = frozenset()


def _chama_a_cabeca(fonte):
    import ast
    for no in ast.walk(ast.parse(fonte)):
        if isinstance(no, ast.Call):
            f = no.func
            nome = getattr(f, "attr", None) or getattr(f, "id", None)
            if nome == "cabeca_de_funcao":
                return True
    return False


def teste_as_telas_de_funcao_usam_a_cabeca():
    secao(u"as telas de função usam radai_ui.cabeca_de_funcao")
    sem = set()
    for ident, rel in sorted(TELAS_DE_FUNCAO.items()):
        with io.open(_componentes.fonte(rel), encoding="utf-8") as f:
            if not _chama_a_cabeca(f.read()):
                sem.add(ident)
    checar(u"as telas sem a cabeça são exatamente as pendentes",
           sem == set(PENDENTES_DA_CABECA),
           u"sem a cabeça: %s; pendentes: %s"
           % (sorted(sem), sorted(PENDENTES_DA_CABECA)))
    checar(u"  isca: chamada de verdade conta",
           _chama_a_cabeca(u"import radai_ui\nradai_ui.cabeca_de_funcao('a','b','c')\n"))
    checar(u"  isca: o nome num comentário ou num texto não conta",
           not _chama_a_cabeca(u"# radai_ui.cabeca_de_funcao\nx = 'cabeca_de_funcao'\n"))


def main():
    for t in (teste_os_componentes_existem, teste_os_helpers_montam_certo,
              teste_as_telas_de_funcao_usam_a_cabeca,
              teste_os_componentes_no_navegador, teste_a_porta,
              teste_as_mini_paginas, teste_as_frases_novas_tem_os_doze_idiomas,
              teste_a_geometria_no_navegador, teste_as_abas_da_barra_da_direita,
              teste_o_mais_do_card_da_fila, teste_o_alerta_sobrevive_a_traducao,
              teste_o_bolus_diz_o_aplicador_e_o_risco,
              teste_a_conversao_de_imagens_tem_destaque):
        try:
            t()
        except Exception:
            checar(u"%s rodou sem exceção" % t.__name__, False,
                   traceback.format_exc()[-900:])
    ok = sum(1 for _n, c, _d in _RESULTADOS if c)
    falhou = len(_RESULTADOS) - ok
    print(u"\n" + u"=" * 68)
    if falhou:
        print(u"FALHOU: %d de %d checagens" % (falhou, len(_RESULTADOS)))
    else:
        print(u"OK: %d checagens, todas passaram" % ok)
    print(u"=" * 68)
    return 1 if falhou else 0


if __name__ == "__main__":
    sys.exit(main())
