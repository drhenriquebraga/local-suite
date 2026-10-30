# -*- coding: utf-8 -*-

LARGURA = 56
LARGURA_ABERTA = 212

ITENS = [
    ("inicio",      "/",            u"inicio",      u"Início",        u"os módulos da suíte"),
    ("bridge",      "/bridge",      u"ponte",      u"DicomBridge",    u"o que impede o TPS de aceitar, e o que a conversão resolve"),
    ("autocontorno", "/autocontorno", u"contornos",     u"ContourLab",     u"comparar modelos sobre o mesmo exame"),
    ("neuro",       "/neuro",       u"cruzamento", u"NEURO RT", u"ferramentas de estudo do sistema nervoso central"),
    ("nidus",       "/nidus",       u"cruzamento",      u"Nidus RT",      u"projeção vascular: a mesma lesão em duas incidências"),
    ("nidus_projecao", "/nidus/projecao", u"cruzamento", u"Projeção Vascular", u"circular na projeção, ver onde as duas se cruzam"),
    ("elastic",     "/elastic",     u"malha",      u"Elastic RT",    u"fusão elástica: o que a deformação fez, e se ela é possível"),
    ("elastic_fusao", "/elastic/fusao", u"malha",  u"Fusão elástica", u"registrar duas séries e medir o campo"),
    ("bolus",       "/bolus",       u"bolus",      u"3D Printed Bolus", u"bólus impresso em 3D: a camada sobre a pele, em STL"),
    ("bolus_gerar", "/bolus/gerar", u"camadas",      u"Gerar bólus",   u"fechar a caixa no MPR e gerar o STL"),
    ("vigia",       "/vigia",       u"lua",      u"Vigia",         u"o lote automático da noite"),
    ("lote",        "/lote",        u"rodar",      u"Rodar agora",   u"escolher series e contornar"),
    ("ver",         "/ver",         u"olho",      u"Ver segmentação", u"abrir o que já está contornado"),
    ("procedencia", "/procedencia", u"lapis",      u"Procedência",   u"o que o programa faz com cada estrutura"),
    ("recon3d",     "/recon3d",     u"cubo",      u"Reconstruções 3D", u"MIP, MinIP e superfície do que já foi contornado"),
    ("bibliografia", "/bibliografia", u"manual",  u"Bibliografia",   u"de onde vem cada decisão, e sob que licença"),
    ("config",      "/config",      u"engrenagem",      u"Configurações", u"o vigia, os modelos e o diagnóstico"),
]

MODULOS_HOME = ("bridge", "autocontorno", "recon3d", "neuro", "elastic",
                "bolus")

SEM_ITEM_NO_MENU = ("diagnostico",)

CSS = u"""
<style id="radai-menu-css">
:root{--ui-lado:%(w)dpx}
body{margin-left:var(--ui-lado) !important}
.radai-menu{position:fixed;left:0;top:60px;top:var(--ui-topo,60px);bottom:0;
 width:var(--ui-lado);z-index:8;
 background:var(--bg-1,#0a1120);border-right:1px solid var(--line,#1e293b);
 overflow-y:auto;overflow-x:hidden;font-family:var(--font-display,Segoe UI,Arial);
 box-sizing:border-box;padding:8px 0 12px;
 display:flex;flex-direction:column;align-items:center;gap:4px}

:root[data-trilho="aberto"]{--ui-lado:%(aberta)dpx}
@media (min-width:901px){
 :root.lado-abrindo .radai-menu{--ui-painel-corte:%(corte)dpx;
  animation:uiPainelDesvela var(--ui-painel-abre,400ms)
   var(--ui-painel-curva,cubic-bezier(.22,1,.36,1)) both}
 :root.lado-abrindo .radai-menu a .rot{--ui-painel-curso:-%(curso)dpx;
  animation:uiPainelEntra var(--ui-painel-abre,400ms)
   var(--ui-painel-curva,cubic-bezier(.22,1,.36,1)) both}
 :root.lado-fechando .radai-menu{--ui-painel-corte:%(corte)dpx;pointer-events:none;
  animation:uiPainelVela var(--ui-painel-fecha,350ms)
   var(--ui-painel-curva,cubic-bezier(.22,1,.36,1)) both}
 :root.lado-fechando .radai-menu a .rot{--ui-painel-curso:-%(curso)dpx;
  animation:uiPainelSai var(--ui-painel-fecha,350ms)
   var(--ui-painel-curva,cubic-bezier(.22,1,.36,1)) both}
}
@media (prefers-reduced-motion:reduce){
 :root.lado-abrindo .radai-menu,:root.lado-abrindo .radai-menu a .rot,
 :root.lado-fechando .radai-menu,:root.lado-fechando .radai-menu a .rot{animation:none}
}
.radai-menu a .rot{display:none}
:root[data-trilho="aberto"] .radai-menu{align-items:stretch;
 padding-left:8px;padding-right:8px}
:root[data-trilho="aberto"] .radai-menu a{width:100%%;
 grid-template-columns:38px 1fr;justify-items:start;
 place-items:center start}
:root[data-trilho="aberto"] .radai-menu a .ico{
 display:grid;place-items:center;width:38px}
:root[data-trilho="aberto"] .radai-menu a .rot{display:block;
 position:static;top:auto;left:auto;
 font-size:13px;font-weight:600;white-space:nowrap;
 overflow:hidden;text-overflow:ellipsis;padding-right:6px}
:root[data-trilho="aberto"] .radai-menu .lado-dobra{
 justify-content:flex-start;padding-left:4px;gap:6px}
.radai-menu a{display:grid;place-items:center;width:38px;height:38px;
 border-radius:var(--r-lg,8px);color:var(--text-dim,#72829b);
 text-decoration:none;font-size:16px;line-height:1;flex:0 0 auto;
 box-sizing:border-box;border:1px solid transparent}
.radai-menu a:hover{color:var(--text,#e6edf7);background:var(--panel,#0c1322)}
.radai-menu a:focus-visible{outline:2px solid var(--accent,#4DA3FF);
 outline-offset:2px}
.radai-menu a.on{background:var(--mod-cor-fraca,var(--accent-fraco,rgba(77,163,255,.14)));
 color:var(--mod-cor,var(--accent,#4DA3FF));
 border-color:var(--mod-cor,var(--accent,#4DA3FF))}
.radai-menu a[data-mod="autocontorno"]{--mod-cor:var(--mod-auto,#4DA3FF);
 --mod-cor-fraca:var(--mod-auto-fraco,rgba(77,163,255,.14))}
.radai-menu a[data-mod="bridge"]{--mod-cor:var(--mod-bridge,#9D8BFF);
 --mod-cor-fraca:var(--mod-bridge-fraco,rgba(124,92,255,.14))}
.radai-menu a[data-mod="recon3d"]{--mod-cor:var(--mod-recon,#31D0AA);
 --mod-cor-fraca:var(--mod-recon-fraco,rgba(49,208,170,.14))}
.radai-menu a[data-mod="neuro"],.radai-menu a[data-mod="nidus"]{--mod-cor:var(--mod-nidus,#E39B4F);
 --mod-cor-fraca:var(--mod-nidus-fraco,rgba(227,155,79,.14))}
.radai-menu a[data-mod="elastic"]{--mod-cor:var(--mod-elastic,#8FA9F2);
 --mod-cor-fraca:var(--mod-elastic-fraco,rgba(143,169,242,.14))}
.radai-menu a[data-mod="bolus"]{--mod-cor:var(--mod-bolus,#B5D65A);
 --mod-cor-fraca:var(--mod-bolus-fraco,rgba(181,214,90,.14))}

.radai-menu .lado-dobra{display:flex;justify-content:center;width:100%%;
 padding:0 0 6px;margin:0 0 4px;border-bottom:1px solid var(--line,#1e293b)}
.radai-menu .lado-dobra button{background:none;
 border:1px solid var(--line,#1e293b);color:var(--text-dim,#72829b);
 border-radius:var(--r-md,6px);cursor:pointer;width:30px;height:30px;
 line-height:1;font-size:13px;padding:0}
.radai-menu .lado-dobra button:hover{color:var(--text,#e6edf7);
 border-color:var(--accent,#4DA3FF)}

.radai-menu .pe ~ .pe{margin-top:0;border-top:0;padding-top:2px}
.radai-menu .pe{margin-top:auto;width:100%%;display:flex;
 justify-content:center;padding-top:8px;border-top:1px solid var(--line,#1e293b)}

@media (max-width:900px){
 body{margin-left:0 !important}
 .radai-menu{position:static;width:auto;height:auto;bottom:auto;
  border-right:0;border-bottom:1px solid var(--line,#1e293b);
  flex-direction:row;flex-wrap:wrap;align-items:center;padding:6px;gap:6px}
 .radai-menu .pe{margin-top:0;width:auto;border-top:0;padding-top:0;
  margin-left:auto}
 .radai-menu .lado-dobra{width:auto;border-bottom:0;padding:0;margin:0 4px 0 0}

 :root[data-trilho="aberto"] .radai-menu{align-items:center;
  padding:6px;flex-direction:row;flex-wrap:wrap}
 :root[data-trilho="aberto"] .radai-menu a{width:auto;height:32px;
  grid-template-columns:22px auto;gap:5px;padding:0 9px 0 5px}
 :root[data-trilho="aberto"] .radai-menu a .ico{width:22px}
 :root[data-trilho="aberto"] .radai-menu a .rot{font-size:12px}
 :root[data-trilho="aberto"] .radai-menu .pe{margin-top:0;width:auto;
  border-top:0;padding-top:0;margin-left:auto}
 :root[data-trilho="aberto"] .radai-menu .lado-dobra{width:auto;
  border-bottom:0;padding:0;margin:0 4px 0 0}
}
</style>"""

ALIAS = {
    "diagnostico": "config",
    "creditos": "bibliografia",
}

MODULOS = ("bridge", "autocontorno", "recon3d", "neuro", "elastic", "bolus")
NO_PE = ("bibliografia", "config")

GRUPOS = [(u"", MODULOS), (u"", NO_PE)]


_JA_RECLAMOU = set()


def _reclamar(o_que, erro):
    chave = "%s:%s" % (o_que, type(erro).__name__)
    if chave in _JA_RECLAMOU:
        return
    _JA_RECLAMOU.add(chave)
    try:
        import sys
        sys.stderr.write("[radai_menu] %s nao foi montado: %s: %s\n"
                         % (o_que, type(erro).__name__, str(erro)[:200]))
    except Exception:
        pass


def _esc(t):
    return (t.replace(u"&", u"&amp;").replace(u"<", u"&lt;")
            .replace(u">", u"&gt;").replace(u'"', u"&quot;"))


def _so_traduzir(pagina):
    try:
        import radai_languages
        return radai_languages.so_traduzir(pagina)
    except Exception as e:
        _reclamar("tradutor", e)
        return pagina


def _com_idioma(pagina):
    try:
        import radai_languages
        return radai_languages.aplicar(pagina)
    except Exception as e:
        _reclamar("seletor de idioma", e)
        return pagina


def _com_capa(pagina):
    try:
        import radai_cover
        return radai_cover.aplicar(pagina)
    except Exception as e:
        _reclamar("folha da capa", e)
        return pagina


def _com_soltar(pagina):
    try:
        import radai_release
        return radai_release.aplicar(pagina)
    except Exception as e:
        _reclamar("arrastar e soltar", e)
        return pagina


def _com_ajuda(pagina):
    try:
        import radai_help
        return radai_help.aplicar(pagina)
    except Exception as e:
        _reclamar("folha da ajuda", e)
        return pagina


def _com_cabecalho(pagina, ativo, com_seletor=False):
    if not pagina:
        return pagina
    _a = str(ativo or "")
    try:
        import radai_breadcrumb as _rt
        chave = _a if _a in _rt.ARVORE else ALIAS.get(_a, _a)
    except Exception:
        chave = ALIAS.get(_a, _a)
    try:
        import radai_cover
        import radai_breadcrumb
        if chave == radai_breadcrumb.RAIZ:
            return pagina
        novo = radai_cover.cabecalho(chave=chave, com_seletor=com_seletor)
    except Exception as e:
        _reclamar("cabecalho", e)
        return pagina

    ini = pagina.find(u'<header class="rc-topo"')
    if ini >= 0:
        fim = pagina.find(u"</header>", ini)
        if fim < 0:
            return pagina
        return pagina[:ini] + novo + pagina[fim + len(u"</header>"):]

    if not chave or chave not in radai_breadcrumb.ARVORE:
        return pagina
    baixa = pagina.lower()
    i = baixa.find(u"<body")
    if i < 0:
        return pagina
    corte = pagina.find(u">", i)
    if corte < 0:
        return pagina
    return pagina[:corte + 1] + novo + pagina[corte + 1:]




def _com_ui(pagina):
    try:
        import radai_ui
        return radai_ui.aplicar(pagina)
    except Exception as e:
        _reclamar("sistema de design", e)
        return pagina


def _com_tarefas(pagina, com_pendencias=False, tela=u""):
    try:
        import radai_todo
        return radai_todo.aplicar(pagina, com_pendencias=com_pendencias,
                                  tela=tela)
    except Exception as e:
        _reclamar("barra de tarefas", e)
        return pagina


def folha_do_trilho():
    corte = LARGURA_ABERTA - LARGURA
    return CSS % {"w": LARGURA, "aberta": LARGURA_ABERTA, "corte": corte,
                  "curso": corte // 2}


def modulo_de(chave):
    c = ALIAS.get(chave, chave)
    if not c:
        return u""
    if c in MODULOS or c in NO_PE:
        return c
    try:
        import radai_breadcrumb
        visto = set()
        while c and c not in visto:
            visto.add(c)
            p = radai_breadcrumb.ARVORE.get(c)
            if not p:
                return u""
            c = p[2]
            if c in MODULOS or c in NO_PE:
                return c
    except Exception:
        return u""
    return u""


def html(ativo=""):
    por_chave = {i[0]: i for i in ITENS}
    ativo = modulo_de(ativo) or ALIAS.get(ativo, ativo)
    partes = [u'<nav class="radai-menu" aria-label="m&oacute;dulos">'
              u'<div class="lado-dobra">'
              u'<button type="button" id="ladoDobra" onclick="uiLado()" '
              u'aria-label="expandir o menu" '
              u'title="expandir o menu">&#9776;</button>'
              u'</div>']

    def _ico(txt):
        try:
            import radai_ui
            return radai_ui.icone_de(txt)
        except Exception:
            return _esc(txt or u"")

    def _item(c, no_pe=False):
        if c not in por_chave:
            return
        _, href, ico, rotulo, ajuda = por_chave[c]
        ico = _ico(ico)
        alvo = (u'<a href="%s"%s data-mod="%s" title="%s" '
                u'aria-label="%s"%s><span class="ico">%s</span>'
                u'<span class="rot" data-radai-frase>%s</span></a>') % (
            href,
            u' class="on"' if c == ativo else u"",
            _esc(c), _esc(rotulo), _esc(rotulo),
            u' aria-current="page"' if c == ativo else u"",
            ico, _esc(rotulo))
        partes.append(u'<div class="pe">%s</div>' % alvo if no_pe else alvo)

    for c in MODULOS:
        _item(c)
    for c in NO_PE:
        _item(c, no_pe=True)
    partes.append(u"</nav>")
    return u"".join(partes)


def aplicar_leitura(pagina, ativo=""):
    pagina = _com_ui(pagina)
    pagina = _com_capa(pagina)
    if not pagina:
        return pagina
    pagina = marcar_tela(pagina, ativo)
    pagina = _com_cabecalho(pagina, ativo, com_seletor=True)
    pagina = _com_idioma(pagina)
    return _so_traduzir(pagina)


def aplicar_porta(pagina):
    pagina = _com_ui(pagina)
    if not pagina:
        return pagina
    try:
        import radai_breadcrumb
        raiz = radai_breadcrumb.RAIZ
    except Exception:
        raiz = "inicio"
    pagina = marcar_tela(pagina, raiz)
    return _so_traduzir(pagina)


def aplicar(pagina, ativo="", com_tarefas=True, com_pendencias=False):
    pagina = _com_ui(pagina)
    pagina = _com_capa(pagina)
    pagina = _com_ajuda(pagina)
    pagina = _com_soltar(pagina)
    pagina = (_com_tarefas(pagina, com_pendencias=com_pendencias,
                           tela=ativo)
              if com_tarefas else pagina)
    pagina = _so_traduzir(pagina)
    if not pagina or u"radai-menu-css" in pagina:
        return pagina

    baixa = pagina.lower()
    if baixa.find(u"</head>") < 0:
        return pagina
    if baixa.find(u"<body") < 0:
        return pagina
    if pagina.find(u">", baixa.find(u"<body")) < 0:
        return pagina

    pagina = marcar_tela(pagina, ativo)
    pagina = _com_cabecalho(pagina, ativo)

    folha = folha_do_trilho()
    fim_head = pagina.lower().find(u"</head>")
    saida = pagina[:fim_head] + folha + pagina[fim_head:]
    corte = saida.find(u">", saida.lower().find(u"<body")) + 1
    return saida[:corte] + html(ativo) + saida[corte:]


def e_ferramenta(chave):
    try:
        import radai_breadcrumb
        entrada = radai_breadcrumb.ARVORE.get(str(chave or ""))
    except Exception:
        return False
    return bool(entrada) and entrada[2] in MODULOS


def marcar_tela(pagina, chave):
    if not pagina:
        return pagina
    i = pagina.lower().find(u"<body")
    if i < 0:
        return pagina
    j = pagina.find(u">", i)
    if j < 0:
        return pagina
    extra = u""
    if u"data-tela=" not in pagina[i:j]:
        extra += u' data-tela="%s"' % _esc(chave)
    if e_ferramenta(chave) and u"data-ls-identidade=" not in pagina[i:j]:
        extra += u' data-ls-identidade="trabalho"'
    if not extra:
        return pagina
    return pagina[:i + 5] + extra + pagina[i + 5:]
