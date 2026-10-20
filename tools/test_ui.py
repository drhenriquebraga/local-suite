# -*- coding: utf-8 -*-
import io
import os
import re
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _cleanup
_cleanup.adotar_prefixo('radai_ac_ui')
_cleanup.adotar_prefixo('radai_js_')


sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
APP = os.path.join(RAIZ, "app")
sys.path.insert(0, APP)

import tempfile as _tempfile
import _componentes
os.environ["RADAI_CALIB_DIR"] = _tempfile.mkdtemp(prefix="radai_ac_ui_")


_RESULTADOS = []


def checar(nome, condicao, detalhe=""):
    _RESULTADOS.append((nome, bool(condicao), detalhe))
    if not condicao:
        print(u"  FALHA  %s%s" % (nome, (u"  [%s]" % detalhe) if detalhe else u""))


def secao(t):
    print(u"\n─── %s %s" % (t, u"─" * max(0, 66 - len(t))))


def teste_fichas_nos_dois_temas():
    secao(u"fichas: o claro cobre o escuro")
    import radai_ui

    def fichas(bloco):
        return set(re.findall(r"(--[a-z0-9-]+)\s*:", bloco))

    m = re.search(r"(?s):root\{(.*?)\}", radai_ui.TOKENS)
    c = re.search(r'(?s):root\[data-tema="claro"\]\{(.*?)\}', radai_ui.TOKENS)
    checar(u"o bloco do tema escuro existe", m is not None)
    checar(u"o bloco do tema claro existe", c is not None)
    if not (m and c):
        return
    escuro, claro = fichas(m.group(1)), fichas(c.group(1))
    checar(u"o escuro define fichas", len(escuro) > 15, str(len(escuro)))

    forma = set(f for f in escuro
                if f.startswith(("--r-", "--font-", "--ui-")))
    forma.add("--marca-grad")
    forma.add("--mono")
    cor = escuro - forma

    encaminha = set()
    for nome, valor in re.findall(r"(--[a-z0-9-]+)\s*:\s*([^;]+);", m.group(1)):
        if re.match(r"^\s*var\(\s*--[a-z0-9-]+\s*\)\s*$", valor):
            encaminha.add(nome)
    cor -= encaminha
    checar(u"os apelidos apontam para outra ficha (e seguem o tema)",
           len(encaminha) >= 1, u", ".join(sorted(encaminha)))

    faltando = sorted(cor - claro)
    checar(u"toda ficha de COR tem par no tema claro", not faltando,
           u", ".join(faltando[:6]))
    sobrando = sorted(claro - escuro)
    checar(u"o tema claro não inventa ficha que o escuro não tem", not sobrando,
           u", ".join(sobrando[:6]))


def teste_a_folha_tem_as_pecas():
    secao(u"a folha: casca, passo, ajuda, botão, campo")
    import radai_ui
    f = radai_ui.folha()
    for sel, rot in ((u".ps-cx{", u"o card do passo"),
                     (u".ps-num{", u"o número quadrado"),
                     (u".ps-seta{", u"a seta de dobra"),
                     (u".ps-cx.fechado > .ps-corpo{display:none}", u"recolher esconde"),
                     (u".ps-cx.inativo{", u"o passo inativo"),
                     (u".ui-ajuda{", u"o `?`"),
                     (u".ui-ajuda:hover .ui-balao", u"o balão abre no mouse"),
                     (u".ui-ajuda:focus .ui-balao", u"e no teclado"),
                     (u".ui-bt{", u"o botão"),
                     (u".ui-bt.pri{", u"o botão primário"),
                     (u"input[type=text]", u"o campo de texto"),
                     (u".radai-menu{top:var(--ui-topo)", u"a barra esquerda abaixo do topo"),
                     (u".radai-tarefas{top:var(--ui-topo)", u"a barra direita abaixo do topo")):
        checar(u"a folha traz %s" % rot, sel in f, sel[:34])

    m = re.search(r"(?s)\.ps-num\{(.*?)\}", f)
    checar(u"o número do passo existe na folha", m is not None)
    if m:
        b = m.group(1)
        lar = re.search(r"width:(\d+)px", b)
        alt = re.search(r"height:(\d+)px", b)
        fon = re.search(r"font-size:(\d+)px", b)
        checar(u"ele é quadrado (largura = altura)",
               lar and alt and lar.group(1) == alt.group(1),
               u"%s x %s" % (lar and lar.group(1), alt and alt.group(1)))
        checar(u"e grande o bastante para se ler de relance (>= 28 px)",
               lar and int(lar.group(1)) >= 28, lar and lar.group(1))
        checar(u"com a fonte em destaque (>= 15 px)",
               fon and int(fon.group(1)) >= 15, fon and fon.group(1))

    m = re.search(r"(?s)\.ps-seta\{(.*?)\}", f)
    if m:
        fon = re.search(r"font-size:(\d+)px", m.group(1))
        alvo = re.search(r"width:(\d+)px", m.group(1))
        checar(u"a seta é grande (>= 20 px)", fon and int(fon.group(1)) >= 20,
               fon and fon.group(1))
        checar(u"e tem área de clique (>= 26 px)",
               alvo and int(alvo.group(1)) >= 26, alvo and alvo.group(1))


def teste_o_js_e_por_delegacao():
    secao(u"o JS: delegação, cascata e tema")
    import radai_ui
    js = radai_ui.JS
    checar(u"a dobra é por delegação em document",
           u"document.addEventListener('click'" in js)
    checar(u"o alvo é o cabeçalho do passo", u"closest('.ps-cab')" in js)
    checar(u"clicar no balão de ajuda não dobra o bloco",
           u"closest('.ui-ajuda')" in js)
    checar(u"o passo inativo não abre no clique", u"inativo" in js)
    checar(u"responde ao teclado", u"'Enter'" in js and u"keydown" in js)
    checar(u"psAbrir existe para a cascata", u"window.psAbrir" in js)
    checar(u"psFechar também", u"window.psFechar" in js)
    codigo_js = re.sub(r"(?m)^\s*//.*$", u"", js)
    checar(u"o `#` da URL abre o bloco, e não só rola até ele",
           u"psPeloEndereco" in codigo_js and u"location.hash" in codigo_js)
    checar(u"  e vale na carga E na troca do #",
           u"hashchange" in codigo_js and u"DOMContentLoaded" in codigo_js)
    m2 = re.search(r"(?s)function psPeloEndereco\(\)\{.*?\n \}", js)
    checar(u"  e só abre o que é um bloco de passo",
           bool(m2) and u"ps-cx" in (m2.group(0) if m2 else u""))
    m = re.search(r"(?s)window\.psAbrir = function.*?\n \};", js)
    checar(u"psAbrir só ABRE (não recolhe ninguém)",
           m and u"add('fechado')" not in m.group(0))
    codigo = re.sub(r"(?m)^\s*//.*$", u"", js)
    checar(u"o tema fica no navegador, não no config",
           u"localStorage" in codigo and u"radai_watcher.config" not in codigo)


def teste_a_ajuda_e_o_passo_montam_certo():
    secao(u"ajuda() e passo(): o que sai do Python")
    import radai_ui
    a = radai_ui.ajuda(u"texto <b>com</b> marcação")
    checar(u"o `?` sai com o balão", u"ui-balao" in a and u">?<" in a)
    checar(u"chega pelo teclado", u'tabindex="0"' in a)
    checar(u"a marcação do texto sobrevive", u"<b>com</b>" in a)
    checar(u"a variante ancorada à direita existe",
           u"ui-ajuda dir" in radai_ui.ajuda(u"x", direita=True))

    p = radai_ui.passo(u"2", u"Título", u"<p>corpo</p>", ident=u"cx2", sub=u"— sub")
    checar(u"o passo traz o número", u'<span class="ps-num">2</span>' in p)
    checar(u"o título é frase de tradução", u"data-radai-frase>Título" in p)
    checar(u"o subtítulo entra como ps-sub", u'class="ps-sub">— sub' in p)
    checar(u"o corpo entra no ps-corpo", u'<div class="ps-corpo"><p>corpo</p>' in p)
    checar(u"o id vai para a section", u'id="cx2"' in p)

    i = radai_ui.passo(u"4", u"Depois", u"", inativo=True)
    checar(u"o passo inativo nasce recolhido", u"fechado" in i)
    checar(u"e marcado como inativo", u"inativo" in i)
    checar(u"sem papel de botão (não é clicável)", u'role="button"' not in i)
    checar(u"mas ainda numerado (a sequência não encolhe)",
           u'class="ps-num">4<' in i)

    e = radai_ui.passo(u"1", u'<script>x</script>', u"")
    checar(u"o título é escapado", u"&lt;script&gt;" in e and u"<script>x" not in e)


def teste_aplicar_costura_ou_devolve_intacta():
    secao(u"aplicar(): costura, ou devolve a página intacta")
    import radai_ui
    p = u"<html><head><title>t</title></head><body>oi</body></html>"
    r = radai_ui.aplicar(p)
    checar(u"costura a folha", radai_ui.MARCA_CSS in r)
    checar(u"e o JS", u"radai-ui-js" in r)
    checar(u"os dois antes do </head>",
           r.index(u"radai-ui-js") < r.lower().index(u"</head>"))
    checar(u"não duplica quando já tem", radai_ui.aplicar(r) == r)
    for ruim, rot in ((u"<html><body>sem head</body></html>", u"sem </head>"),
                      (u"", u"vazia"), (None, u"None")):
        checar(u"página %s sai intacta" % rot, radai_ui.aplicar(ruim) == ruim)


def _paginas():
    import radai_menu
    import radai_panel
    saida = [(u"autocontorno",
              radai_panel._costurar_home(radai_panel.pagina_inicial())),
             (u"config", radai_menu.aplicar(radai_panel.PAGINA_CONFIG, "config",
                                            com_tarefas=False))]
    for mod, const, chave in (("radai_watcher", "PAGE", "vigia"),):
        try:
            m = __import__(mod)
            saida.append((chave, radai_menu.aplicar(getattr(m, const), chave)))
        except Exception as e:
            print(u"  (pulei %s: %s)" % (chave, type(e).__name__))
    return saida


def teste_a_casca_e_a_mesma_em_toda_tela():
    secao(u"a casca: cabeçalho constante, barras abaixo")
    for chave, p in _paginas():
        checar(u"[%s] tem a folha do sistema" % chave, u"radai-ui-css" in p)
        checar(u"[%s] tem o cabeçalho" % chave, u'class="rc-topo"' in p)
        checar(u"[%s] o cabeçalho traz a marca" % chave, u'class="rc-marca"' in p)
        checar(u"[%s] carimba data-tela" % chave,
               re.search(r'<body[^>]*data-tela="%s"' % chave, p) is not None)
        checar(u"[%s] a marca aparece uma vez só" % chave,
               p.count(u'class="rc-marca"') == 1,
               str(p.count(u'class="rc-marca"')))


def _tem_ancora_de_idioma(p):
    m = re.sub(r"(?s)<script.*?</script>", u" ", p or u"")
    return bool(re.search(r"<[a-zA-Z][^<>]*\sdata-radai-(?:idiomas|lang)"
                          r"(?=[\s=>/])", m))


def teste_home_e_telas_internas_se_distinguem():
    secao(u"porta e telas internas: o que só existe em cada uma")
    por = dict(_paginas())
    mod = por.get(u"autocontorno", u"")
    checar(u"a mini-pagina TEM o trilho", u"radai-menu-css" in mod,
           u"era a unica tela da suite sem navegacao entre modulos")
    checar(u"e NAO tem o dialogo de fechar", u"rx-veu" not in mod,
           u"o Fechar vive na porta da suite")
    import radai_router
    import radai_todo
    checar(u"e tem a barra da fila (C1), recolhida no HTML servido",
           u"radai-tarefas-css" in mod
           and re.search(r'<html\b[^>]*class="dir-recolhida[^>]*'
                         r'data-dir-sozinha="0"', mod) is not None
           and u"autocontorno" not in radai_todo.TELAS_QUE_ABREM_SOZINHAS)
    outra = radai_router.mini_pagina(u"bridge")
    checar(u"  e nas outras mini-páginas também, recolhida de partida",
           u"radai-tarefas-css" in outra
           and re.search(r'<html\b[^>]*class="dir-recolhida', outra) is not None
           and u"bridge" not in radai_todo.TELAS_QUE_ABREM_SOZINHAS)
    checar(u"  e a porta não tem a barra",
           u"radai-tarefas-css" not in radai_router.montar_porta())

    painel_py = io.open(_componentes.fonte("app/radai_panel.py"),
                        encoding="utf-8").read()
    cfg_py = painel_py[painel_py.index("def _tela_config"):]
    cfg_py = cfg_py[:cfg_py.index("@app.get", 10)]
    checar(u"Configurações costura o seletor de idioma",
           u"radai_languages" in cfg_py)
    checar(u"e ANTES do menu",
           cfg_py.index(u"radai_languages") < cfg_py.index(u"radai_menu.aplicar"),
           u"depois do menu o seletor nasceria escondido")

    rot_py = io.open(_componentes.fonte("app/radai_router.py"),
                     encoding="utf-8").read()
    handler = rot_py[rot_py.index("def _suite():"):]
    handler = handler[:handler.index("@app.get")]
    checar(u"a porta NÃO costura o seletor",
           u"radai_languages" not in handler)
    import radai_router
    porta = radai_router.montar_porta()
    porta_m = re.sub(r"(?s)<script.*?</script>", u" ", porta)
    checar(u"a porta TEM o Fechar (a âncora, fora de <script>)",
           u"data-radai-encerrar" in porta_m)
    checar(u"e o diálogo das três saídas", u'id="rx-veu"' in porta_m)
    checar(u"a porta NÃO tem o trilho", u"radai-menu-css" not in porta
           and u'class="radai-menu' not in porta_m)

    vistas = []
    for chave in (u"config", u"vigia", u"compilador", u"calibrador"):
        p = por.get(chave)
        if p is None:
            continue
        vistas.append(chave)
        checar(u"[%s] tem a barra lateral" % chave, u"radai-menu-css" in p)
        checar(u"[%s] NÃO tem o Fechar" % chave,
               u"data-radai-encerrar" not in p)
        tem_ancora = _tem_ancora_de_idioma(p)
        if chave == u"config":
            checar(u"[config] TEM o seletor de idioma", tem_ancora,
                   u"é a casa dele desde a Fase 6")
        else:
            checar(u"[%s] NÃO repete o seletor de idioma" % chave,
                   not tem_ancora)
        checar(u"[%s] tem o tradutor" % chave, u"radai-idioma-js" in p)
        checar(u"[%s] tem o caminho de volta" % chave,
               u"rc-voltar" in p or u"ui-icone" in p)
        checar(u"[%s] um caminho de volta só" % chave,
               p.count(u'class="voltar"') == 0, str(p.count(u'class="voltar"')))
    checar(u"e /config está entre as telas conferidas (ela foi a exceção até "
           u"a v8.3)", u"config" in vistas, str(vistas))


def _tem_a_pilha(p):
    m = re.search(r'(?s)<script id="radai-ui-js">(.*?)</script>', p)
    return bool(m) and u"function histRegistrar(" in m.group(1)


def teste_o_voltar_tem_a_pilha_em_toda_tela():
    secao(u"o Voltar e a pilha do historico chegam juntos")
    import radai_menu
    import radai_modules
    import radai_router
    telas = list(_paginas())
    for chave in (u"bridge", u"recon3d", u"nidus", u"elastic", u"bolus"):
        telas.append((chave, radai_menu.aplicar(
            radai_modules.pagina_completa(chave), chave, com_tarefas=False)))
    try:
        import radai_consent
        telas.append((u"termos", radai_menu.aplicar_leitura(
            radai_consent.TERMOS, u"termos")))
    except Exception as e:
        print(u"  (pulei termos: %s)" % type(e).__name__)
    com_voltar = 0
    for chave, p in telas:
        if u"data-radai-voltar" not in re.sub(r"(?s)<script.*?</script>",
                                               u" ", p):
            continue
        com_voltar += 1
        checar(u"[%s] o Voltar marcado chega com o JS da pilha" % chave,
               _tem_a_pilha(p))
        checar(u"[%s] e o cabeçalho diz o nome da tela" % chave,
               re.search(r'<header class="rc-topo" data-radai-tela="[^"]+"', p)
               is not None)
    checar(u"as telas internas têm o Voltar marcado (%d)" % com_voltar,
           com_voltar >= 8, str(com_voltar))
    porta = radai_router.montar_porta()
    checar(u"a porta não tem Voltar (ela é o começo)",
           u"data-radai-voltar" not in re.sub(r"(?s)<script.*?</script>",
                                               u" ", porta))
    checar(u"mas entra na pilha: o cabeçalho dela também diz o nome",
           u'data-radai-tela="Radioterapia.AI Local"' in porta
           and _tem_a_pilha(porta))


def teste_a_barra_lateral():
    secao(u"o trilho: um item por modulo, engrenagem no pe, sem marca")
    import radai_menu
    nav = radai_menu.html("vigia")

    checar(u"a barra não tem marca", u"rc-marca" not in nav)
    checar(u"nem seletor de idioma", not _tem_ancora_de_idioma(nav)
           and u"data-radai-lang" not in nav
           and u"data-radai-idiomas" not in nav)
    checar(u"e o Início saiu do trilho", u'class="inicio' not in nav)

    esperado = len(radai_menu.MODULOS) + len(radai_menu.NO_PE)
    checar(u"uma âncora por módulo, mais a Estação",
           nav.count(u"<a ") == esperado,
           u"%d para %d + %d" % (nav.count(u"<a "), len(radai_menu.MODULOS),
                                 len(radai_menu.NO_PE)))
    for m in tuple(radai_menu.MODULOS) + tuple(radai_menu.NO_PE):
        checar(u"`%s` está no trilho" % m, (u'data-mod="%s"' % m) in nav)

    checar(u"a engrenagem fica no PÉ, separada",
           u'<div class="pe">' in nav
           and nav.index(u'<div class="pe">') > nav.index(u'data-mod="recon3d"'),
           u"ela não é um módulo: é a estação")

    checar(u"todo item tem title", nav.count(u"title=") >= 4,
           str(nav.count(u"title=")))
    checar(u"e aria-label", nav.count(u"aria-label=") >= 4,
           str(nav.count(u"aria-label=")))
    checar(u"o ícone e o rótulo são elementos separados",
           u'<span class="ico">' in nav and u'<span class="rot"' in nav,
           u"colados num nó só, a chave de tradução não casa")
    checar(u"e o rótulo tem chave própria",
           nav.count(u'class="rot" data-radai-frase') >= 4,
           u"%d rótulo(s) com chave" % nav.count(u'class="rot" data-radai-frase'))
    import radai_menu as _rm
    checar(u"e nasce escondido, com o trilho fechado",
           u".radai-menu a .rot{display:none}".replace(u" ", u"")
           in _rm.CSS.replace(u" ", u""),
           u"sem isso o rótulo estoura os 56 px")

    checar(u"a tela ativa marca o módulo dela",
           u'class="on" data-mod="autocontorno"' in nav)
    checar(u"e leva aria-current", u'aria-current="page"' in nav)

    import radai_phrases
    com_entrada = set(l[0] for l in radai_phrases.TABELA)
    checar(u"`DicomBridge` NÃO tem entrada de tradução (é nome próprio)",
           u"DicomBridge" not in com_entrada)


def teste_o_panel_reveal_das_barras_laterais():
    secao(u"as barras laterais: o panel reveal, com os tempos do transitions.dev")
    import radai_ui as U
    import radai_menu as M
    folha = U.folha()
    for ficha in (u"--ui-painel-abre:400ms", u"--ui-painel-fecha:350ms",
                  u"--ui-painel-curva:cubic-bezier(.22,1,.36,1)",
                  u"--ui-painel-desfoque:2px"):
        checar(u"a ficha `%s` está na casca" % ficha, ficha in folha)
    checar(u"entrar é deslizar, aparecer e desfocar juntos, do curso a zero",
           u"@keyframes uiPainelEntra{from{transform:translateX(var(--ui-painel-curso,0px));"
           u"\n opacity:0;filter:blur(var(--ui-painel-desfoque,2px))}}" in folha)
    checar(u"  e sair é o caminho de volta",
           u"@keyframes uiPainelSai{to{transform:translateX(var(--ui-painel-curso,0px));"
           u"\n opacity:0;filter:blur(var(--ui-painel-desfoque,2px))}}" in folha)
    js = U.JS
    checar(u"o pedido de mão da barra direita é da ABA (sessionStorage), e o "
           u"guardado antigo do navegador inteiro saiu",
           u"DIR_USUARIO = 'radai_dir_usuario'" in js and u"ssGravar(DIR_USUARIO" in js
           and u"radai_dir_recolhido" not in js and u"data-dir-inicial" not in js)
    checar(u"a barra direita decide no <head>, antes do primeiro quadro, e anima depois dele",
           u"dirAplicar(dirQuer() === '0' && ssLer(DIR_VISTA) === 'aberta' ? '0' : '1', false)"
           in js and u"depoisDoPrimeiroQuadro(function(){\n   dirPronta = true;" in js)
    checar(u"  e pedido de script durante a carga não desfaz o estado de partida",
           u"if(!deMao && document.readyState === 'loading')" in js)
    checar(u"a barra esquerda vinda da porta nasce recolhida e se expande depois",
           u"ladoAplicar(daPorta ? '0' : salvo, false)" in js
           and u"ladoAplicar('1', true)" in js
           and u"n.type !== 'navigate'" in js)
    checar(u"movimento reduzido: o JS não espera a animação",
           js.count(u"!semMovimento()") == 2)
    trilho = M.folha_do_trilho()
    corte = M.LARGURA_ABERTA - M.LARGURA
    checar(u"o trilho aberto e o recorte saem das mesmas constantes",
           (u":root[data-trilho=\"aberto\"]{--ui-lado:%dpx}" % M.LARGURA_ABERTA) in trilho
           and (u"--ui-painel-corte:%dpx" % corte) in trilho
           and (u"--ui-painel-curso:-%dpx" % (corte // 2)) in trilho)
    checar(u"  o trilho desvela e vela pelo recorte, e o rótulo entra e sai",
           u"animation:uiPainelDesvela var(--ui-painel-abre,400ms)" in trilho
           and u"animation:uiPainelVela var(--ui-painel-fecha,350ms)" in trilho
           and u":root.lado-abrindo .radai-menu a .rot{" in trilho)
    checar(u"  e nada anima para quem pede movimento reduzido",
           u":root.lado-fechando .radai-menu,:root.lado-fechando .radai-menu a .rot"
           u"{animation:none}" in trilho)


SEM_PIPELINE = (u"config", u"vigia")


def teste_os_passos_das_telas():
    secao(u"os passos: numerados, o primeiro aberto")
    for chave, p in _paginas():
        cards = re.findall(r'<section class="ps-cx([^"]*)"', p)
        if chave in (u"inicio", u"autocontorno"):
            continue
        checar(u"[%s] tem passos numerados" % chave, len(cards) >= 2,
               str(len(cards)))
        if not cards:
            continue
        nums = re.findall(r'<span class="ps-num"[^>]*>(\d+)</span>', p)
        checar(u"[%s] a numeração começa em 1 e não pula" % chave,
               [n for n in nums] == [str(i + 1) for i in range(len(nums))]
               or chave in SEM_PIPELINE,
               u",".join(nums))
        if chave in SEM_PIPELINE:
            checar(u"[%s] todos os blocos nascem recolhidos" % chave,
                   all(u"fechado" in c for c in cards),
                   u"%d de %d" % (sum(1 for c in cards if u"fechado" in c),
                                  len(cards)))
        else:
            checar(u"[%s] o primeiro passo nasce aberto" % chave,
                   u"fechado" not in cards[0], cards[0])

    try:
        import radai_batch
        import radai_menu
        p = radai_menu.aplicar(radai_batch._pagina(), "lote")
        cards = re.findall(r'<section class="ps-cx([^"]*)"|<div class="ps-cx([^"]*)"', p)
        checar(u"[lote] o passo 1 mora no popup da casca, e na tela sobra o "
               u"das séries encontradas",
               len(cards) == 1 and u'<div class="ui-ps" id="cx1" data-ui-ps' in p
               and u'id="cx2"' in p, str(len(cards)))
        try:
            import radai_view
            pv = radai_menu.aplicar(radai_view._pagina(), "ver",
                                    com_tarefas=False)
            cv = re.findall(r'<section class="ps-cx([^"]*)"'
                            r'|<div class="ps-cx([^"]*)"'
                            r'|<button type="button" class="ui-cartao"', pv)
            checar(u"[ver] tem passos (o cartão da série conta), e poucos",
                   2 <= len(cv) <= 6, str(len(cv)))
            nums = re.findall(r'<span class="(?:ps-num|ui-cartao-ic)"'
                              r'(?: aria-hidden="true")?>(\d)</span>', pv)
            esperado = [str(i + 1) for i in range(len(nums))]
            checar(u"[ver] os passos sao 1..N e nao repetem",
                   nums == esperado, ",".join(nums))
            checar(u"[ver] sem a barra de tarefas",
                   '<aside class="radai-tarefas' not in pv, "")
            checar(u"[ver] traz os dois visores axiais",
                   'id="cp_visor0"' in pv and 'id="cp_visor1"' in pv, "")
            checar(u"[ver] e não traz mais o painel 3D", 'id="cv3D"' not in pv,
                   "")
            import radai_sets
            por_tela = dict((c["cod"], c)
                            for c in radai_view._conjuntos_da_tela())
            for c in radai_sets.CONJUNTOS:
                rot = (por_tela.get(c["cod"]) or {}).get(
                    "rotulo_curto") or c["rotulo_curto"]
                checar(u"[ver] lista o conjunto %s" % rot, rot in pv, "")
        except ImportError:
            pass
        checar(u"[lote] o passo 1 nasce recolhido",
               cards and u"fechado" in (cards[0][0] + cards[0][1]))
    except Exception as e:
        checar(u"[lote] a página monta", False, u"%s: %s" % (type(e).__name__, e))


def teste_nenhuma_tela_ficou_com_folha_propria_de_card():
    secao(u"nenhuma cópia local do card sobreviveu")
    for nome in _componentes.nomes("app"):
        if not nome.endswith(".py"):
            continue
        s = io.open(_componentes.fonte("app/" + nome), encoding="utf-8").read()
        for sel in (u"h2.dobra{", u".cx.fechado > .conteudo", u".cx > .conteudo"):
            checar(u"%s não redefine %s" % (nome, sel), sel not in s)


def teste_a_cor_vem_das_fichas():
    secao(u"a cor da casca vem das fichas")
    busca = re.compile(r'(?<![&\w,])(?<!fill=")(?<!stroke=")'
                       r'#([0-9a-fA-F]{6})\b')
    checar(u"(isca) cor escura em regra de folha conta; a do desenho não",
           busca.findall(u"x{color:#101010}") == [u"101010"]
           and not busca.findall(u'<path fill="#101010" stroke="#101010"/>'))

    def escuro(h):
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return (0.2126 * r + 0.7152 * g + 0.0722 * b) < 70

    total = 0
    piores = []
    for nome in _componentes.nomes("app"):
        if not nome.endswith(".py") or nome == "radai_ui.py":
            continue
        s = io.open(_componentes.fonte("app/" + nome), encoding="utf-8").read()
        n = len([h for h in busca.findall(s) if escuro(h)])
        total += n
        if n > 12:
            piores.append(u"%s=%d" % (nome, n))
    checar(u"nenhum módulo carrega mais de 12 cores escuras cravadas",
           not piores, u", ".join(piores))
    checar(u"o total fica abaixo de 60 (era 517)", total < 60, str(total))


def teste_o_tema_claro_e_legivel():
    secao(u"contraste: os dois temas se leem")
    import radai_ui

    def le(bloco):
        return dict(re.findall(r"(--[a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{3,8})", bloco))

    def lum(h):
        h = h.lstrip(u"#")
        if len(h) == 3:
            h = u"".join(c * 2 for c in h)
        r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))

        def c(x):
            return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4
        return 0.2126 * c(r) + 0.7152 * c(g) + 0.0722 * c(b)

    def razao(a, b):
        la, lb = lum(a) + 0.05, lum(b) + 0.05
        return (max(la, lb) / min(la, lb))

    m = re.search(r"(?s):root\{(.*?)\}", radai_ui.TOKENS)
    c = re.search(r'(?s):root\[data-tema="claro"\]\{(.*?)\}', radai_ui.TOKENS)
    for bloco, tema in ((m.group(1), u"escuro"), (c.group(1), u"claro")):
        f = le(bloco)
        for txt, fundo, minimo, rot in (
                ("--text", "--bg-0", 7.0, u"texto no fundo"),
                ("--text", "--panel", 7.0, u"texto no painel"),
                ("--text-muted", "--panel", 4.0, u"texto secundário no painel"),
                ("--text-dim", "--panel", 3.0, u"texto apagado no painel"),
                ("--accent", "--panel", 3.0, u"o acento no painel")):
            if txt not in f or fundo not in f:
                continue
            r = razao(f[txt], f[fundo])
            checar(u"[%s] %s: contraste >= %.1f" % (tema, rot, minimo),
                   r >= minimo, u"%.2f" % r)


def teste_a_roda_do_mouse_tem_forma():
    secao(u"a roda do mouse: o visor precisa saber quantos cortes tem")
    import radai_viewseg
    import radai_viewer
    js = radai_viewseg.JS

    abre = _corpo_js(js, u"cpAbrirSerie")
    checar(u"o passo 4 pede a forma ao servidor", u"/api/verseg/forma" in abre)
    checar(u"e trata a falha da rota (senao a roda morre calada)",
           u".catch(" in abre)
    checar(u"a reserva cobre forma vazia, e nao so ausente",
           u"!forma[0]" in abre or u"forma[0] ===" in abre,
           u"um `d.forma || reserva` sozinho aceita [0,0,0]")
    checar(u"e `cpDefinirForma` e sempre chamado", u"cpDefinirForma(" in abre)
    checar(u"e a roda do comparador so anda com a forma conhecida",
           u"CP.forma[0]" in _corpo_js(js, u"cpAndar"))

    v = radai_viewer.JS
    checar(u"a roda anda no visor sob o cursor", u"closest('[data-v]')" in v)
    checar(u"e nao no 3D", u"'3d'" in v)
    checar(u"Shift anda de dez em dez", u"shiftKey" in v)
    checar(u"a roda nao passa do primeiro nem do ultimo corte",
           u"Math.max(0, Math.min(" in v)
    checar(u"e ela cancela a rolagem da pagina",
           u"preventDefault" in v and u"passive:false" in v)


def _balanco(js):
    pilha, linha = [], 1
    i, n = 0, len(js)
    pares = {")": "(", "]": "[", "}": "{"}
    anterior = ""
    while i < n:
        c = js[i]
        if c == "\n":
            linha += 1
            i += 1
            continue
        if c in " \t\r":
            i += 1
            continue
        if c == "/" and i + 1 < n and js[i + 1] == "/":
            k = js.find("\n", i)
            i = n if k < 0 else k
            continue
        if c == "/" and i + 1 < n and js[i + 1] == "*":
            k = js.find("*/", i + 2)
            linha += js[i:(n if k < 0 else k)].count("\n")
            i = n if k < 0 else k + 2
            continue
        if c == "/" and anterior not in ")]}" and not (
                anterior.isalnum() or anterior in "_$"):
            k, classe = i + 1, False
            while k < n:
                if js[k] == "\\":
                    k += 2
                    continue
                if js[k] == "\n":
                    break
                if classe:
                    if js[k] == "]":
                        classe = False
                elif js[k] == "[":
                    classe = True
                elif js[k] == "/":
                    break
                k += 1
            if k < n and js[k] == "/":
                i = k + 1
                anterior = "/"
                continue
        if c in "\\'\\\"`":
            k = i + 1
            while k < n:
                if js[k] == "\\":
                    k += 2
                    continue
                if js[k] == c:
                    break
                if js[k] == "\n" and c != "`":
                    break
                k += 1
            linha += js[i:k].count("\n")
            i = k + 1
            anterior = "'"
            continue
        if c in "([{":
            pilha.append((c, linha))
        elif c in ")]}":
            if not pilha or pilha[-1][0] != pares[c]:
                return (linha, c)
            pilha.pop()
        anterior = c
        i += 1
    if pilha:
        return (pilha[-1][1], pilha[-1][0])
    return None


def _node():
    import shutil
    return shutil.which("node")


def _parsear(js, node):
    import os
    import subprocess
    import tempfile
    d = tempfile.mkdtemp(prefix="radai_js_")
    alvo = os.path.join(d, "b.js")
    try:
        io.open(alvo, "w", encoding="utf-8").write(js)
        r = subprocess.run([node, "--check", alvo], capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
        if r.returncode == 0:
            return None
        for ln in (r.stderr or "").splitlines():
            if "Error" in ln:
                return ln.strip()
        return (r.stderr or "").strip()[:160]
    finally:
        import shutil as _sh
        _sh.rmtree(d, ignore_errors=True)


def teste_o_js_das_telas_parseia():
    import re
    secao(u"o JS de cada tela e JavaScript valido")
    node = _node()
    if not node:
        checar(u"node disponivel para parsear o JS", False,
               u"PULADO -- sem node, so o balanco de delimitadores roda")
    for chave, p in _paginas():
        blocos = [b for b in re.findall(r"(?is)<script[^>]*>(.*?)</script>", p)
                  if len(b.strip()) >= 40]
        checar(u"[%s] tem script embutido" % chave, len(blocos) >= 1,
               u"%d bloco(s)" % len(blocos))
        for k, js in enumerate(blocos):
            r = _balanco(js)
            checar(u"[%s] script %d fecha os delimitadores" % (chave, k + 1),
                   r is None,
                   u"" if r is None else u"linha %d do bloco, `%s`" % r)
            if node:
                e = _parsear(js, node)
                checar(u"[%s] script %d parseia" % (chave, k + 1),
                       e is None, e or u"")


def teste_a_checagem_de_js_pega_o_defeito_de_verdade():
    secao(u"a propria checagem de JS e provada nos dois sentidos")
    node = _node()
    ruim = (u"var a=1;\n"
            u"x.t=' e '+(d.n?(' erro: '+(d.e[0]||{}).er:''):'');\n"
            u"f();\n")
    bom = (u'function esc(s){return String(s).replace(/&/g,"a")'
           u'.replace(/"/g,"b");}\n')
    if node:
        checar(u"o defeito do Compilador, reintroduzido, e acusado",
               _parsear(ruim, node) is not None,
               _parsear(ruim, node) or u"passou -- a checagem esta cega")
        checar(u"regex com aspa dentro nao vira falso positivo",
               _parsear(bom, node) is None, _parsear(bom, node) or u"")
    checar(u"o balanco pega chave a mais",
           _balanco(u"function f(){ if(a){ b(); }\n}}\n") is not None, u"")
    checar(u"o balanco nao acusa divisao de verdade",
           _balanco(u"var r=(a+b)/2; var q=x[0]/y;") is None, u"")
    checar(u"o balanco nao acusa regex com parentese na classe",
           _balanco(u"if(/[a-z(]/.test(s)){f();}") is None, u"")

def teste_o_portao_e_es5_e_ascii():
    secao(u"o portao: ES5 puro e ASCII puro")
    import radai_ui
    g = radai_ui.PORTAO
    m = re.search(r"(?is)<script[^>]*>(.*)</script>", g)
    checar(u"o portao e um <script>", m is not None)
    if not m:
        return
    js = m.group(1)
    checar(u"o portao e ASCII na fonte", all(ord(c) < 128 for c in g),
           u"%d caractere(s) acima de 127"
           % sum(1 for c in g if ord(c) >= 128))
    for nome, padrao in ((u"arrow function", r"=>"),
                         (u"const", r"\bconst\b"),
                         (u"let", r"\blet\b"),
                         (u"template literal", r"`"),
                         (u"fetch(", r"fetch\s*\("),
                         (u"Promise(", r"new\s+Promise"),
                         (u"var(--", r"var\(--"),
                         (u"class", r"\bclass\s+\w"),
                         (u"Object.assign", r"Object\.assign"),
                         (u".includes(", r"\.includes\("),
                         (u"querySelector", r"querySelector")):
        achou = re.search(padrao, js)
        checar(u"o portao nao usa %s" % nome, achou is None,
               u"" if achou is None else achou.group(0))
    for peca in (u"CSS custom properties", u"window.fetch", u"Promise"):
        checar(u"o portao nomeia a peca que falta: %s" % peca, peca in js)
    checar(u"o portao fala nos dois idiomas",
           u"This browser cannot run" in js and u"Este navegador" in js)
    node = _node()
    if node:
        e = _parsear(js, node)
        checar(u"o portao parseia", e is None, e or u"")
    else:
        checar(u"node disponivel para parsear o portao", False,
               u"PULADO -- so as checagens de texto rodaram")


def teste_o_portao_entra_no_head_depois_do_charset():
    secao(u"o portao entra no <head>, depois do charset")
    import radai_ui
    paginas = list(_paginas())
    try:
        import radai_consent
        paginas.append((u"aceite", radai_consent.pagina_aceite()))
    except Exception as e:
        print(u"  (pulei aceite: %s)" % type(e).__name__)
    for chave, p in paginas:
        q = radai_ui.com_portao(p)
        i = q.find(radai_ui.MARCA_PORTAO)
        checar(u"[%s] o portao entrou" % chave, i > 0)
        if i <= 0:
            continue
        baixa = q.lower()
        cab, fim_cab = baixa.find(u"<head"), baixa.find(u"</head>")
        checar(u"[%s] o portao esta dentro do <head>" % chave,
               cab >= 0 and cab < i < (fim_cab if fim_cab > 0 else len(q)))
        c = baixa.find(u"charset")
        if c >= 0:
            checar(u"[%s] o charset vem ANTES do portao" % chave, c < i,
                   u"charset em %d, portao em %d" % (c, i))
            checar(u"[%s] o charset cabe nos 1024 bytes do prescan" % chave,
                   len(q[:c].encode("utf-8")) < 1024,
                   u"%d bytes" % len(q[:c].encode("utf-8")))
        folha = baixa.find(u"radai-ui-css")
        if folha >= 0:
            checar(u"[%s] o portao vem antes da folha" % chave, i < folha)
        checar(u"[%s] costurar duas vezes nao duplica" % chave,
               radai_ui.com_portao(q) == q
               and q.count(radai_ui.MARCA_PORTAO) == 1,
               u"%d marca(s)" % q.count(radai_ui.MARCA_PORTAO))
    nu = radai_ui.com_portao(u"<body><p>x</p></body>")
    checar(u"sem <head>, o portao entra antes do <body>",
           nu.find(radai_ui.MARCA_PORTAO) < nu.lower().find(u"<body"))
    checar(u"pagina vazia sai vazia", radai_ui.com_portao(u"") == u"")


def teste_o_portao_e_servido_de_verdade():
    secao(u"o portao e servido em toda resposta HTML")
    try:
        from fastapi import FastAPI
        from fastapi.responses import HTMLResponse, Response
        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.testclient import TestClient
    except Exception as e:
        checar(u"cliente de teste disponivel", False,
               u"PULADO -- %s: %s" % (type(e).__name__, e))
        return
    import radai_ui
    import radai_watcher

    app = FastAPI()
    app.add_middleware(BaseHTTPMiddleware,
                       dispatch=radai_watcher._portao_do_navegador)

    @app.get("/tela", response_class=HTMLResponse)
    def _tela():
        return (u'<html><head><meta charset="utf-8"><title>t</title></head>'
                u'<body><p>rea\u00e7\u00e3o</p></body></html>')

    @app.get("/api/x")
    def _api():
        return {"ok": True}

    @app.get("/img")
    def _img():
        return Response(content=b"\x89PNG", media_type="image/png")

    c = TestClient(app)
    r = c.get("/tela")
    checar(u"a tela servida traz o portao", radai_ui.MARCA_PORTAO in r.text)
    checar(u"o content-length foi refeito",
           int(r.headers.get("content-length", -1)) == len(r.content),
           u"%s contra %d" % (r.headers.get("content-length"), len(r.content)))
    checar(u"o acento da pagina sobrevive ao middleware",
           u"rea\u00e7\u00e3o" in r.text)
    checar(u"o charset cabe nos 1024 bytes do prescan",
           0 <= r.content.lower().find(b"charset") < 1024,
           str(r.content.lower().find(b"charset")))
    checar(u"o JSON sai intocado",
           radai_ui.MARCA_PORTAO not in c.get("/api/x").text)
    checar(u"o PNG sai intocado", c.get("/img").content == b"\x89PNG")

    montado = any(getattr(m, "kwargs", {}).get("dispatch", None)
                  is radai_watcher._portao_do_navegador
                  for m in radai_watcher.app.user_middleware)
    checar(u"o portao esta montado no app do vigia", montado)


def teste_o_lancador_nao_recua_calado():
    secao(u"o lancador nao recua calado")
    p = os.path.join(RAIZ, "app", "launchers", "open_browser.cmd")
    checar(u"o lancador existe", os.path.exists(p))
    if not os.path.exists(p):
        return
    b = io.open(p, "rb").read()
    checar(u"o lancador e CRLF", b.count(b"\n") == b.count(b"\r\n"),
           u"%d LF solto(s)" % (b.count(b"\n") - b.count(b"\r\n")))
    try:
        t = b.decode("ascii")
        ascii_puro = True
    except UnicodeDecodeError:
        t, ascii_puro = b.decode("utf-8", "replace"), False
    checar(u"o lancador e ASCII puro", ascii_puro)
    echos = [l for l in t.splitlines() if l.strip().lower().startswith("echo")]
    checar(u"nenhum echo ainda chama isso de aba comum",
           not [l for l in echos if u"aba comum" in l], u" | ".join(echos)[:90])
    checar(u"o recuo diz que faltam os dois navegadores",
           u"NEM O EDGE NEM O CHROME" in t)
    checar(u"o recuo nomeia o Internet Explorer",
           u"Internet Explorer" in t)
    checar(u"o recuo ainda abre o navegador padrao",
           u'start "" %URL%' in t)
    checar(u"o comentario nao afirma mais que o Edge vem em toda estacao",
           u"vem em toda estacao Windows 10" not in t)
    checar(u"o GUARDA: diz que a LTSB nao traz o Edge",
           any(u"GUARDA:" in l and u"LTSB" in l for l in t.splitlines()))


def teste_as_animacoes_contam_estado():
    secao(u"as cinco animacoes contam estado")
    import radai_ui as U
    css = U.MOVIMENTO
    for classe in (u".ui-esqueleto", u".ui-gira", u".ui-feito", u".ui-brilho",
                   u".ui-badge", u".ui-treme"):
        checar(u"a folha tem `%s`" % classe, classe in css)

    i = css.index(u"@media (prefers-reduced-motion:reduce)")
    reduzido = css[i:]
    for classe in (u".ui-esqueleto", u".ui-gira", u".ui-feito", u".ui-brilho",
                   u".ui-badge", u".ui-treme"):
        checar(u"  e `%s` para com movimento reduzido" % classe,
               classe in reduzido,
               u"animacao que ignora a preferencia e a que ninguem consegue "
               u"desligar")
    checar(u"  e o bloco reduzido so desliga `animation`",
           u"background:" not in reduzido and u"color:" not in reduzido,
           u"tirar a cor junto apagaria o estado de quem pediu menos "
           u"movimento")
    checar(u"a folha do app carrega o bloco", u".ui-treme" in U.folha())

    import radai_batch as L
    checar(u"o esqueleto aparece na varredura",
           u"esqueleto(el('tab')" in L.PAGINA,
           u"varrer um share le o cabecalho de CADA arquivo")
    checar(u"e o tremor da casca, quando o clique e recusado (rola e da o foco)",
           u"uiTremer(el('btrodar'))" in L.PAGINA
           and u"uiTremer(el('pasta'))" in L.PAGINA
           and u"function treme(" not in L.PAGINA)
    _fonte_ui = io.open(U.__file__, encoding="utf-8").read()
    _i = _fonte_ui.find(u"uiTremer")
    checar(u"  e ela reinicia no segundo clique",
           _i >= 0 and u"void e.offsetWidth" in _fonte_ui[_i:_i + 1600])
    checar(u"o brilho acende so quando o numero MUDA",
           u"cx.dataset.n !== String(L.length)" in L.PAGINA,
           u"piscar a cada repintura seria um alarme")

    import radai_todo as TF
    checar(u"o card que roda tem anel, e o que terminou tem visto",
           u"ui-gira" in TF.HTML and u"ui-feito" in TF.HTML)
    checar(u"  e o que falhou tem visto vermelho",
           u"ui-feito ui-falhou" in TF.HTML)
    checar(u"o contador pulsa quando SOBE, e so entao",
           u"Number(n.dataset.esp) < (r.esperando || 0)" in TF.HTML)
    checar(u"e o esqueleto da fila so aparece na PRIMEIRA volta",
           u"alvo.dataset.javeio" in TF.HTML)


def teste_as_seis_que_faltavam_do_pedido():
    secao(u"as seis que faltavam do pedido de 19/09")
    import radai_ui as U
    css = U.TRANSICOES
    folha = U.folha()
    for classe, oquee in ((u".ui-pnl", u"panel reveal"),
                          (u".ui-sino", u"notification badge"),
                          (u".ui-abas", u"tabs sliding"),
                          (u".ui-morf", u"dropdown menu morph"),
                          (u".ui-shimmer", u"shimmer text"),
                          (u".ui-revelar", u"skeleton reveal")):
        checar(u"a folha tem `%s` (%s)" % (classe, oquee), classe in css)
        checar(u"  e ela chega na página servida", classe in folha,
               u"bloco que existe e não entra em `folha()` é bloco que não "
               u"existe para o navegador")

    i = css.index(u"@media (prefers-reduced-motion:reduce)")
    reduzido = css[i:]
    for classe in (u".ui-pnl", u".ui-sino", u".ui-abas", u".ui-morf",
                   u".ui-shimmer", u".ui-revelar"):
        checar(u"  `%s` para com movimento reduzido" % classe,
               classe in reduzido)

    checar(u"o balão do `?` não usa mais `display` para abrir",
           u"ui-balao{display:none" not in U.AJUDA,
           u"`display` não interpola: a transição escrita ali seria inerte")
    checar(u"  ele abre por `visibility` + `opacity`",
           u"visibility:hidden" in U.AJUDA and u"visibility:visible" in U.AJUDA,
           u"opacidade sozinha deixaria o balão invisível capturando o mouse "
           u"e visível para o leitor de tela")
    checar(u"  e a `visibility` só comuta no fim da saída",
           u"visibility 0s linear .18s" in U.AJUDA)

    js = U.JS
    checar(u"`uiPainel` existe e devolve controle", u"window.uiPainel" in js)
    checar(u"  Esc cancela e Enter confirma",
           u"e.key === 'Escape'" in js and u"e.key === 'Enter'" in js)
    checar(u"  e o Enter no Cancelar não confirma",
           u"e.target !== nao" in js)
    checar(u"  o foco volta para quem abriu", u"_pnlFoco" in js)
    checar(u"  o corpo é TEXTO por padrão, HTML só a pedido",
           u"if(o.html)" in js and u"corpo.textContent" in js,
           u"mensagem vinda de fora escrita como HTML é injeção")
    _p = js.index(u"window.uiPainel") if u"window.uiPainel" in js else -1
    _corpo_pnl = js[_p:_p + 2600] if _p >= 0 else u""
    for _alvo in (u"tit", u"sim", u"nao"):
        checar(u"  e `%s` é escrito por `uiTexto` (o véu é reusado)" % _alvo,
               (u"window.uiTexto(%s," % _alvo) in _corpo_pnl,
               u"`%s.textContent =` deixa a marca de traduzido no elemento"
               % _alvo)
    checar(u"  e o `display` volta depois da transição",
           u"setTimeout(function(){ v.classList.remove('on') }" in js)

    checar(u"as abas mantêm o `<select>` na página",
           u"ui-abas-fonte" in js and u"s.dispatchEvent(ev)" in js,
           u"trocar a UI não pode virar migração de estado: todo código que "
           u"lê `.value` ou pendura `onchange` continua valendo")
    checar(u"  e elas andam pelo teclado",
           u"ArrowLeft" in js and u"ArrowRight" in js)
    checar(u"  e se costuram sozinhas em `select[data-ui-abas]`",
           u"select[data-ui-abas]" in js and u"uiAbasTodas" in js)

    checar(u"o sino conta ENTREGA, e não fila",
           u"radai_entregues_visto" in js,
           u"«quantos saíram desde que você olhou» e «quantos faltam» são "
           u"perguntas diferentes")
    checar(u"  e um contador que cai não mata o sino",
           u"if(visto > total)" in js)
    checar(u"  zerar é ato de quem clica", u"s.onclick" in js)

    import radai_languages as LG
    checar(u"o tradutor tem entrada pública para DOM novo",
           u"window.radaiRetraduzir" in LG.corpo_js(),
           u"sem ela o painel aparece em português por até 3 s numa estação "
           u"em outro idioma — e ele pode sumir dentro dessa janela")
    checar(u"  e o painel a usa", u"window.radaiRetraduzir()" in js)

    import radai_watcher as W
    checar(u"o overnight pergunta por painel, e não por `confirm()`",
           u"uiPainel({" in W.PAGE
           and u"confirm('Dedicar esta estacao" not in W.PAGE,
           u"o `confirm()` nativo congela a página: o log para de pintar "
           u"justamente enquanto se lê a pergunta")


def _rodar_node(js, node):
    import json
    import subprocess
    import tempfile
    d = tempfile.mkdtemp(prefix="radai_js_")
    alvo = os.path.join(d, "r.js")
    try:
        io.open(alvo, "w", encoding="utf-8").write(js)
        r = subprocess.run([node, alvo], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=120)
        for ln in reversed((r.stdout or "").splitlines()):
            if ln.startswith("JSON:"):
                return json.loads(ln[5:]), None
        return None, ((r.stderr or "") + (r.stdout or ""))[-400:]
    finally:
        import shutil as _sh
        _sh.rmtree(d, ignore_errors=True)


def teste_a_ordem_de_bisseccao_e_a_mesma_nos_dois_lados():
    secao(u"a ordem de bisseccao: JavaScript e Python iguais")
    node = _node()
    if not node:
        checar(u"node disponível para executar o JS do visor", False,
               u"PULADO -- sem node")
        return
    import radai_thumbnail
    import radai_viewer
    js = (radai_viewer.JS_UM_EIXO
          + u"\nvar f = {}; for(var n = 0; n <= 300; n++) f[n] = ordemDeBisseccao(n);"
          + u"\nconsole.log('JSON:' + JSON.stringify(f));\n")
    d, erro = _rodar_node(js, node)
    checar(u"o JS do visor executa", d is not None, erro or u"")
    if d is None:
        return
    difere = [n for n in range(301)
              if d.get(str(n)) != radai_thumbnail.ordem_de_bisseccao(n)]
    checar(u"JS e Python dão a mesma ordem para n de 0 a 300", not difere,
           u"diferem em n = %s" % difere[:6])
    checar(u"e ela começa por 50%, 25%, 75%",
           (d.get("100") or [])[:3] == [50, 25, 75], str((d.get("100") or [])[:7]))


_CARGA_JS = u"""
function novo(n, falhar){
 var h = {pend: [], chegou: [], parou: [], descartados: 0, sinais: [], maxVoo: 0};
 h.C = RadaiCargaUmEixo({n: n, emVoo: 3,
  buscar: function(i, sinal){
   h.sinais.push(sinal);
   return new Promise(function(res, rej){ h.pend.push({i: i, res: res, rej: rej}); });
  },
  aoChegar: function(i){ h.chegou.push(i); },
  aoParar: function(st){ h.parou.push(st); },
  descartar: function(){ h.descartados++; }});
 h.falhar = falhar || function(){ return 0; };
 return h;
}
function tique(){ return new Promise(function(r){ setTimeout(r, 0); }); }
async function resolver(h, quantos){
 var feitos = 0;
 while(h.pend.length && feitos < quantos){
  h.maxVoo = Math.max(h.maxVoo, h.pend.length);
  var p = h.pend.shift(), st = h.falhar(p.i);
  if(st){ var e = new Error('x'); e.status = st; p.rej(e); } else { p.res('u' + p.i); }
  await tique();
  feitos++;
 }
 return feitos;
}
(async function(){
 var R = {};
 var a = novo(37); a.C.pedir(18);
 R.a_inicio = a.pend.length;
 var passos = await resolver(a, 5000);
 R.a_pedidos = a.C.pedidos; R.a_ordem = ordemDeBisseccao(37);
 R.a_prontos = a.C.nProntos; R.a_maxVoo = a.maxVoo; R.a_passos = passos;
 var b = novo(37); b.C.pedir(18); await resolver(b, 4);
 var alvo = b.C.ordem[b.C.ordem.length - 1];
 R.b_alvo_ja_pedido = b.C.pedidos.indexOf(alvo) >= 0;
 b.C.pedir(alvo);
 R.b_antes = b.C.pedidos.length;
 await resolver(b, 1);
 R.b_proximo = b.C.pedidos[R.b_antes]; R.b_alvo = alvo;
 var c = novo(37); c.C.pedir(18); await resolver(c, 2);
 var voando = c.sinais.slice(-3);
 var pedidosAntes = c.C.pedidos.length, chegouAntes = c.chegou.length;
 c.C.fechar();
 R.c_abortados = voando.filter(function(s){ return s && s.aborted; }).length;
 await resolver(c, 5000);
 R.c_pedidos_depois = c.C.pedidos.length - pedidosAntes;
 R.c_chegou_depois = c.chegou.length - chegouAntes;
 R.c_descartados = c.descartados;
 var d = novo(37, function(i){ return i === 18 ? 404 : 0; }); d.C.pedir(18);
 await resolver(d, 5000);
 R.d_parou = d.parou; R.d_pedidos = d.C.pedidos.length;
 var e = novo(37, function(i){ return i === 5 ? 422 : 0; }); e.C.pedir(5);
 R.e_passos = await resolver(e, 5000);
 R.e_pedidos = e.C.pedidos.length;
 R.e_unicos = e.C.pedidos.filter(function(x, k, t){ return t.indexOf(x) === k; }).length;
 R.e_falhos = e.C.nFalhos; R.e_prontos = e.C.nProntos;
 var f = novo(20); f.C.prontos = {3: 'a', 10: 'b'};
 var g = novo(20); g.C.prontos = {4: 'a', 8: 'b'};
 R.f = [f.C.maisProximo(6), f.C.maisProximo(7), g.C.maisProximo(6),
        f.C.maisProximo(0), novo(5).C.maisProximo(2)];
 console.log('JSON:' + JSON.stringify(R));
})();
"""


def teste_a_carga_por_bisseccao_executa():
    secao(u"a carga por bisseccao, executada")
    node = _node()
    if not node:
        checar(u"node disponível para executar o JS do visor", False,
               u"PULADO -- sem node")
        return
    import radai_viewer
    d, erro = _rodar_node(radai_viewer.JS_UM_EIXO + _CARGA_JS, node)
    checar(u"o roteiro da carga executa", d is not None, erro or u"")
    if d is None:
        return
    checar(u"ao abrir, saem três pedidos — e só três", d["a_inicio"] == 3,
           str(d["a_inicio"]))
    checar(u"sem rolar, os pedidos saem na ordem da bissecção",
           d["a_pedidos"] == d["a_ordem"], str(d["a_pedidos"][:8]))
    checar(u"todos os 37 cortes chegam", d["a_prontos"] == 37,
           str(d["a_prontos"]))
    checar(u"nunca mais de três em voo", d["a_maxVoo"] <= 3, str(d["a_maxVoo"]))
    checar(u"o corte rolado ainda não tinha sido pedido (a cobaia vale)",
           not d["b_alvo_ja_pedido"])
    checar(u"o corte rolado sai no próximo lugar livre",
           d["b_proximo"] == d["b_alvo"], u"%s em vez de %s"
           % (d["b_proximo"], d["b_alvo"]))
    checar(u"fechar aborta os três em voo", d["c_abortados"] == 3,
           str(d["c_abortados"]))
    checar(u"depois de fechar, nenhum pedido novo", d["c_pedidos_depois"] == 0,
           str(d["c_pedidos_depois"]))
    checar(u"e o que chega tarde não é pintado", d["c_chegou_depois"] == 0,
           str(d["c_chegou_depois"]))
    checar(u"cada imagem volta a quem a criou (2 chegadas + 3 tardias)",
           d["c_descartados"] == 5, str(d["c_descartados"]))
    checar(u"404 para a série e diz por que",
           d["d_parou"] == [404] and d["d_pedidos"] == 3,
           u"parou=%s pedidos=%s" % (d["d_parou"], d["d_pedidos"]))
    checar(u"422 marca só aquele corte, e ele não é pedido de novo",
           d["e_pedidos"] == 37 and d["e_unicos"] == 37 and d["e_falhos"] == 1
           and d["e_prontos"] == 36,
           u"pedidos=%s únicos=%s falhos=%s prontos=%s passos=%s"
           % (d["e_pedidos"], d["e_unicos"], d["e_falhos"], d["e_prontos"],
              d["e_passos"]))
    checar(u"o carregado mais perto, com empate para baixo",
           d["f"] == [3, 10, 4, 3, -1], str(d["f"]))


_ORIENTACAO_JS = u"""
var riscos = [];
var ctx = {clearRect: function(){}, fillRect: function(x, y){ riscos.push([x, y, this.fillStyle]); },
 save: function(){}, restore: function(){}, beginPath: function(){}, moveTo: function(){},
 lineTo: function(){}, stroke: function(){}, fillText: function(){}};
var canvas = {width: 400, height: 400, getContext: function(){ return ctx; },
 getBoundingClientRect: function(){ return {width: 400, height: 400}; },
 addEventListener: function(){}};
var document = {readyState: 'complete', addEventListener: function(){},
 getElementById: function(id){ return id === 'cv3D' ? canvas : null; }};
var window = {addEventListener: function(){}, devicePixelRatio: 1};
"""

_ORIENTACAO_RODA = u"""
function det(M){ return M[0]*(M[4]*M[8]-M[5]*M[7]) - M[1]*(M[3]*M[8]-M[5]*M[6])
                        + M[2]*(M[3]*M[7]-M[4]*M[6]); }
function cena(eixos, pontos){
 N3.eixos = eixos; N3.M = null;
 N3.itens = pontos.map(function(p){ return {pontos: [p[0]], normais: [p[1]], cor: p[2]}; });
 N3.escala = 1; N3.ux = 0; N3.uy = 0;
}
function onde(){
 var o = {};
 riscos.forEach(function(r, k){
  var m = /rgb\\((\\d+),(\\d+),(\\d+)\\)/.exec(r[2]);
  var c = (+m[1] > 0) ? 'r' : ((+m[2] > 0) ? 'g' : 'b');
  o[c] = {x: r[0] + 0.5 - 200, y: 200 - (r[1] + 0.5), ordem: k};
 });
 return o;
}
var C = ['esq', 'post', 'sup'];
var P = [[[0, 0, 40], [0, 0, 1], [255, 0, 0]],
         [[40, 0, 0], [1, 0, 0], [0, 255, 0]],
         [[0, -40, 0], [0, -1, 0], [0, 0, 255]]];
var R = {};
['ant', 'esq', 'sup'].forEach(function(v){
 cena(C, P); riscos = []; n3Vista(v); R[v] = onde();
 R['det_' + v] = det(n3MatrizDaVista(v, C));
});
R.det_inicial = det(n3MatrizInicial(C));
cena(['esq', 'post', 'inf'], [[[0, 0, 40], [0, 0, 1], [255, 0, 0]]]);
riscos = []; n3Vista('ant'); R.invertido = onde();
R.girar = n3Projetar(n3Girar(n3MatrizDaVista('ant', C), 10, 0), [0, -1, 0]);
console.log('JSON:' + JSON.stringify(R));
"""


def teste_o_3d_nao_espelha_e_as_vistas_sao_as_que_dizem():
    secao(u"o 3D: sem espelho, e as vistas sao as que dizem")
    node = _node()
    if not node:
        checar(u"node disponível para executar o renderizador", False,
               u"PULADO -- sem node")
        return
    import radai_viewer
    d, erro = _rodar_node(_ORIENTACAO_JS + radai_viewer.JS_3D + _ORIENTACAO_RODA,
                          node)
    checar(u"o renderizador executa com o canvas dublado", d is not None,
           erro or u"")
    if d is None:
        return
    ant, esq, sup = d["ant"], d["esq"], d["sup"]
    checar(u"«A»: a esquerda do paciente à direita da tela", ant["g"]["x"] > 30,
           str(ant["g"]))
    checar(u"«A»: o superior para cima", ant["r"]["y"] > 30, str(ant["r"]))
    checar(u"«A»: o anterior é o mais perto", ant["b"]["ordem"] == 2,
           str(ant["b"]))
    checar(u"«E»: o anterior à esquerda da tela", esq["b"]["x"] < -30,
           str(esq["b"]))
    checar(u"«E»: o lado esquerdo é o mais perto", esq["g"]["ordem"] == 2,
           str(esq["g"]))
    checar(u"«S»: o superior é o mais perto", sup["r"]["ordem"] == 2,
           str(sup["r"]))
    checar(u"«S»: o anterior para cima", sup["b"]["y"] > 30, str(sup["b"]))
    for v in ("ant", "esq", "sup", "inicial"):
        checar(u"a vista «%s» é uma rotação, e não um espelho" % v,
               abs(d["det_" + v] - 1.0) < 1e-9, str(d["det_" + v]))
    checar(u"série com as fatias invertidas: o inferior vai para baixo",
           d["invertido"]["r"]["y"] < -30, str(d["invertido"]))
    checar(u"arrastar para a direita leva a frente para a direita",
           d["girar"][0] > 0.05, str(d["girar"]))


class _Arvore(object):

    def __init__(self, html):
        from html.parser import HTMLParser
        vazios = {"input", "img", "br", "meta", "link", "hr", "source", "col"}
        self.ancestrais = {}
        pilha = []
        arv = self

        class P(HTMLParser):
            def handle_starttag(self, tag, attrs):
                a = dict(attrs)
                marca = (a.get("id") or u"", a.get("class") or u"")
                if a.get("id"):
                    arv.ancestrais[a["id"]] = list(pilha)
                if tag not in vazios:
                    pilha.append(marca)

            def handle_endtag(self, tag):
                if tag not in vazios and pilha:
                    pilha.pop()
        P().feed(html)

    def dentro(self, id_, id_pai=None, classe=None):
        for i, c in self.ancestrais.get(id_, []):
            if id_pai and i == id_pai:
                return True
            if classe and classe in c.split():
                return True
        return False


def _corpo_js(js, nome):
    i = js.find(u"function %s(" % nome)
    if i < 0:
        return u""
    k = js.find(u"{", i)
    prof = 0
    for j in range(k, len(js)):
        if js[j] == u"{":
            prof += 1
        elif js[j] == u"}":
            prof -= 1
            if prof == 0:
                return js[k:j + 1]
    return u""


def _costura_do_lote(pagina):
    faltam = []
    ver = _corpo_js(pagina, u"verNoPasso4")
    repor = _corpo_js(pagina, u"_reporPrevias")
    if not ver:
        return [u"`verNoPasso4` não existe na página"]
    if u"umEixoNaCelula(" not in ver and u"umEixoAbrir(" not in ver:
        faltam.append(u"`verNoPasso4` não abre o visor (umEixoNaCelula)")
    if u"umEixoSoltar(" not in ver and u"umEixoFechar(" not in ver:
        faltam.append(u"o segundo clique não fecha o visor (umEixoSoltar)")
    if u"umEixoNaCelula(" not in repor and u"umEixoAbrir(" not in repor:
        faltam.append(u"`_reporPrevias` não devolve o visor à linha "
                      u"repintada (umEixoNaCelula)")
    return faltam


def _costura_da_ponte(pagina):
    faltam = []
    if u"function RadaiUmEixo(" not in pagina:
        faltam.append(u"a página não costura `radai_viewer.JS_UM_EIXO`")
    if u".ue-visor" not in pagina:
        faltam.append(u"a página não costura `radai_viewer.CSS_UM_EIXO`")
    ligar = _corpo_js(pagina, u"dcVisorLigar")
    if u"RadaiUmEixo(" not in ligar:
        faltam.append(u"`dcVisorLigar` não cria o visor de um eixo "
                      u"(RadaiUmEixo)")
    return faltam


_CELULA_JS = u"""
function El(nome){ this.nome = nome || 'div'; this.filhos = []; this.parentNode = null;
 this._html = ''; this.className = ''; }
Object.defineProperty(El.prototype, 'innerHTML', {
 get: function(){ return this._html; },
 set: function(v){ this._html = v; this.filhos.forEach(function(f){ f.parentNode = null; });
                   this.filhos = []; }});
El.prototype.appendChild = function(c){
 if(c.parentNode) c.parentNode.removeChild(c);
 this.filhos.push(c); c.parentNode = this; return c; };
El.prototype.removeChild = function(c){
 var k = this.filhos.indexOf(c); if(k >= 0) this.filhos.splice(k, 1);
 c.parentNode = null; return c; };
var document = {createElement: function(n){ return new El(n); }};
var window = {};
var abertas = [], fechadas = [];
umEixoAbrir = function(alvo, serie){
 abertas.push(serie && serie.id);
 alvo.__radaiUmEixo = {fechado: false, visor: {fechado: false}};
 return Promise.resolve(null); };
umEixoFechar = function(alvo){
 fechadas.push(alvo);
 var s = alvo.__radaiUmEixo; if(s){ s.fechado = true; }
 alvo.__radaiUmEixo = null; alvo.innerHTML = ''; };
var R = {};
var A = new El('td'), B = new El('td'), C = new El('td'), D = new El('td');
var cx1 = umEixoNaCelula(A, 'k1', {id: 's1'});
R.abre = abertas.length; R.naA = (cx1.parentNode === A);
var cx2 = umEixoNaCelula(B, 'k1', {id: 's1'});
R.repintar_mesma = (cx2 === cx1); R.repintar_abre = abertas.length;
R.naB = (cx1.parentNode === B); R.saiuDeA = (A.filhos.indexOf(cx1) < 0);
var viva = UM_EIXO_CAIXAS['k1'];
if(viva && viva.__radaiUmEixo && viva.__radaiUmEixo.visor){
 viva.__radaiUmEixo.visor.fechado = true; }
var cx3 = umEixoNaCelula(C, 'k1', {id: 's1'});
R.morto_reabre = abertas.length; R.morto_nova = (cx3 !== cx1);
R.morto_fechou_a_velha = (fechadas.indexOf(cx1) >= 0);
umEixoSoltar('k1');
R.soltar_fecha = (fechadas.indexOf(cx3) >= 0); R.soltar_tira = (cx3.parentNode === null);
umEixoNaCelula(D, 'k1', {id: 's1'});
R.depois_de_soltar_abre = abertas.length;
var e1 = umEixoNaCelula(new El('td'), 'x', {id: 'sx'});
var e2 = umEixoNaCelula(new El('td'), 'y', {id: 'sy'});
R.chaves = (e1 !== e2) && abertas.slice(-2).join(',') === 'sx,sy';
console.log('JSON:' + JSON.stringify(R));
"""


def teste_a_celula_que_se_repinta_devolve_o_mesmo_visor():
    secao(u"a celula que se repinta devolve o mesmo visor")
    node = _node()
    if not node:
        checar(u"node disponível para executar o JS do visor", False,
               u"PULADO -- sem node")
        return
    import radai_viewer
    d, erro = _rodar_node(radai_viewer.JS_UM_EIXO + _CELULA_JS, node)
    checar(u"o roteiro da célula executa", d is not None, erro or u"")
    if d is None:
        return
    checar(u"abrir numa célula abre uma vez, e a caixa fica nela",
           d["abre"] == 1 and d["naA"], str(d))
    checar(u"repintar devolve a MESMA caixa, sem abrir de novo",
           d["repintar_mesma"] and d["repintar_abre"] == 1, str(d))
    checar(u"e a caixa muda para a célula nova",
           d["naB"] and d["saiuDeA"], str(d))
    checar(u"visor morto é reaberto numa caixa nova, e a velha é fechada",
           d["morto_reabre"] == 2 and d["morto_nova"]
           and d["morto_fechou_a_velha"], str(d))
    checar(u"soltar fecha e tira da página",
           d["soltar_fecha"] and d["soltar_tira"], str(d))
    checar(u"e depois de soltar, pedir de novo abre",
           d["depois_de_soltar_abre"] == 3, str(d))
    checar(u"duas séries, duas caixas", d["chaves"], str(d))


_VARRER_JS = u"""
function El(nome){ this.nome = nome || 'div'; this.filhos = []; this.parentNode = null;
 this._html = ''; this.className = ''; }
Object.defineProperty(El.prototype, 'innerHTML', {
 get: function(){ return this._html; },
 set: function(v){ this._html = v; this.filhos.forEach(function(f){ f.parentNode = null; });
                   this.filhos = []; }});
El.prototype.appendChild = function(c){
 if(c.parentNode) c.parentNode.removeChild(c);
 this.filhos.push(c); c.parentNode = this; return c; };
El.prototype.removeChild = function(c){
 var k = this.filhos.indexOf(c); if(k >= 0) this.filhos.splice(k, 1);
 c.parentNode = null; return c; };
var CORPO = new El('body');
var document = {createElement: function(n){ return new El(n); },
 body: {contains: function(x){ while(x){ if(x === CORPO) return true; x = x.parentNode; }
                               return false; }}};
var window = {};
var fechadas = [];
umEixoAbrir = function(alvo, serie){
 alvo.__radaiUmEixo = {fechado: false, visor: {fechado: false}};
 return Promise.resolve(null); };
umEixoFechar = function(alvo){
 fechadas.push(alvo);
 var s = alvo.__radaiUmEixo; if(s){ s.fechado = true; }
 alvo.__radaiUmEixo = null; alvo.innerHTML = ''; };
var R = {};
var tA = new El('td'), tB = new El('td'), tC = new El('td');
CORPO.appendChild(tA); CORPO.appendChild(tB); CORPO.appendChild(tC);
var a = umEixoNaCelula(tA, 'ka', {}), b = umEixoNaCelula(tB, 'kb', {});
var c = umEixoNaCelula(tC, 'kc', {});
CORPO.removeChild(tB);
R.soltas = umEixoVarrer();
R.fechou_b = fechadas.indexOf(b) >= 0;
R.poupou_a_c = fechadas.indexOf(a) < 0 && fechadas.indexOf(c) < 0;
R.chaves = Object.keys(UM_EIXO_CAIXAS).sort();
R.b_fora = (b.parentNode === null);
R.de_novo = umEixoVarrer();
console.log('JSON:' + JSON.stringify(R));
"""


def teste_a_caixa_que_saiu_da_pagina_e_solta():
    secao(u"a caixa que saiu da pagina e solta")
    node = _node()
    if not node:
        checar(u"node disponível para executar o JS do visor", False,
               u"PULADO -- sem node")
        return
    import radai_viewer
    d, erro = _rodar_node(radai_viewer.JS_UM_EIXO + _VARRER_JS, node)
    checar(u"o roteiro da varredura executa", d is not None, erro or u"")
    if d is None:
        return
    checar(u"a caixa da série que saiu da tabela é solta (fechada)",
           d["soltas"] == 1 and d["fechou_b"], str(d))
    checar(u"  e as que continuam na página ficam vivas",
           d["poupou_a_c"] and d["chaves"] == [u"ka", u"kc"], str(d))
    checar(u"  e varrer de novo não solta nada", d["de_novo"] == 0, str(d))


def _funcao_js(js, nome):
    i = js.find(u"function %s(" % nome)
    corpo = _corpo_js(js, nome)
    if i < 0 or not corpo:
        return u""
    return js[i:js.index(corpo, i) + len(corpo)]


_LOTE_DUBLES_JS = u"""
var ORDEM = [], BUSCOU = [];
function fetch(u){ BUSCOU.push(u); return new Promise(function(){}); }
var SERIES = [{uid: '1', pasta: 'p1', zip: ''}, {uid: '2', pasta: 'p2'},
              {uid: '3', pasta: 'p3', zip: 'z.zip'}];
var PREV_ABERTA = {};
function chaveDe(s){ return 'k' + s.uid; }
function el(id){
 if(id.indexOf('prev_') === 0){
  return {parentNode: {removeChild: function(){ ORDEM.push('tirou:' + id); }}};
 }
 return null;
}
function _rotuloVer(){}
function _linhaPrevia(i){ return {querySelector: function(){ return {td: i}; }}; }
function umEixoNaCelula(cel, k, s){ ORDEM.push('abre:' + k + ':' + s.pasta + ':'
                                                + s.zip + ':' + s.uid); }
function umEixoSoltar(k){ ORDEM.push('solta:' + k); }
function umEixoVarrer(){ ORDEM.push('varre'); }
"""

_LOTE_RODA_JS = u"""
var R = {};
verNoPasso4(0);
R.abrir = ORDEM.slice(); ORDEM = [];
verNoPasso4(0);
R.fechar = ORDEM.slice(); ORDEM = [];
PREV_ABERTA = {k1: true, k3: true};
_reporPrevias();
R.repintar = ORDEM.slice();
R.buscou = BUSCOU;
console.log('JSON:' + JSON.stringify(R));
"""


def teste_o_ver_imagens_do_lote_executa():
    secao(u"o ver imagens do lote, executado")
    node = _node()
    if not node:
        checar(u"node disponível para executar o JS do lote", False,
               u"PULADO -- sem node")
        return
    import radai_batch
    p = radai_batch._pagina()
    funcs = [_funcao_js(p, n) for n in (u"_serieDoVisor", u"_reporPrevias",
                                        u"verNoPasso4")]
    checar(u"as três funções estão na página do Rodar agora", all(funcs),
           str([bool(f) for f in funcs]))
    if not all(funcs):
        return
    d, erro = _rodar_node(_LOTE_DUBLES_JS + u"\n".join(funcs) + _LOTE_RODA_JS,
                          node)
    checar(u"o roteiro do lote executa", d is not None, erro or u"")
    if d is None:
        return
    checar(u"o primeiro clique abre o visor de um eixo, com pasta, zip e uid",
           d["abrir"] == [u"abre:k1:p1::1"], str(d["abrir"]))
    checar(u"  e não pede a prévia de um corte só", not d["buscou"],
           str(d["buscou"]))
    checar(u"o segundo clique SOLTA o visor antes de tirar a linha",
           d["fechar"] == [u"solta:k1", u"tirou:prev_0"], str(d["fechar"]))
    checar(u"a repintura devolve as abertas e varre UMA vez, no fim",
           d["repintar"] == [u"abre:k1:p1::1", u"abre:k3:p3:z.zip:3", u"varre"],
           str(d["repintar"]))


_AVISO_JS = u"""
function el(){ return {style: {}, hidden: false, textContent: '', className: '',
 value: '', addEventListener: function(){}, removeAttribute: function(){},
 setAttribute: function(){}, getAttribute: function(){ return null; }}; }
function alvoNovo(){
 var els = {};
 return {innerHTML: '', querySelector: function(s){ return els[s] || (els[s] = el()); },
         els: els};
}
var document = {body: {contains: function(){ return true; }}};
var window = {};
var URL = {createObjectURL: function(b){ return 'blob:' + b; }, revokeObjectURL: function(){}};
var falhar = function(){ return 0; };
function fetch(url){
 var i = +(/corte=(\\d+)/.exec(url)[1]);
 var st = falhar(i);
 return Promise.resolve({status: st || 200,
  headers: {get: function(){ return ''; }},
  blob: function(){ return Promise.resolve('c' + i); }});
}
function esperar(){ return new Promise(function(r){ setTimeout(r, 30); }); }
async function rodar(n, f, inicio){
 falhar = f;
 var a = alvoNovo();
 var V = RadaiUmEixo(a, {n: n, inicio: inicio,
                         url: function(i){ return '/c?corte=' + i; }});
 for(var k = 0; k < 60 && (V.carga.nVoando || V.carga.cursor < V.carga.ordem.length); k++){
  await esperar();
 }
 return {aviso: a.els['[data-ue="aviso"]'].textContent, prontos: V.carga.nProntos,
         falhos: V.carga.nFalhos};
}
(async function(){
 var R = {};
 R.tudo_422 = await rodar(9, function(){ return 422; }, 4);
 R.tudo_500 = await rodar(9, function(){ return 500; }, 4);
 R.o_exato_falhou = await rodar(9, function(i){ return i === 4 ? 422 : 0; }, 4);
 R.tudo_bem = await rodar(9, function(){ return 0; }, 4);
 console.log('JSON:' + JSON.stringify(R));
})();
"""


def teste_o_aviso_do_visor_diz_o_que_acontece():
    secao(u"o aviso do visor diz o que esta acontecendo")
    node = _node()
    if not node:
        checar(u"node disponível para executar o JS do visor", False,
               u"PULADO -- sem node")
        return
    import radai_viewer
    d, erro = _rodar_node(radai_viewer.JS_UM_EIXO + _AVISO_JS, node)
    checar(u"o roteiro do aviso executa", d is not None, erro or u"")
    if d is None:
        return
    for caso in (u"tudo_422", u"tudo_500"):
        checar(u"todo corte falhou (%s): diz que não abriu, e não «abrindo»"
               % caso[-3:],
               d[caso]["aviso"] == u"não consegui abrir a série"
               and d[caso]["falhos"] == 9, str(d[caso]))
    checar(u"o corte pedido falhou e os outros chegaram: diz que ESTE falhou",
           d["o_exato_falhou"]["aviso"] == u"este corte não pôde ser lido"
           and d["o_exato_falhou"]["prontos"] == 8, str(d["o_exato_falhou"]))
    checar(u"tudo chegou: aviso vazio",
           d["tudo_bem"]["aviso"] == u"" and d["tudo_bem"]["prontos"] == 9,
           str(d["tudo_bem"]))


_BUSSOLA_RODA = u"""
var letras = [];
ctx.fillText = function(t, x, y){ letras.push([t, x, y]); };
var R = {};
[[400, 400], [1100, 560], [260, 260]].forEach(function(t){
 canvas.getBoundingClientRect = function(){ return {width: t[0], height: t[1]}; };
 cena(['esq', 'post', 'sup'], [[[0, 0, 40], [0, 0, 1], [255, 0, 0]]]);
 letras = [];
 n3Vista('ant');
 var r = Math.min(t[0], t[1]) * 0.11, fs = Math.round(r * 0.42);
 R[t[0] + 'x' + t[1]] = letras.map(function(l){
  return {t: l[0], dentro: l[1] - 0.3*fs >= 0 && l[1] + 0.3*fs <= t[0]
                        && l[2] - 0.5*fs >= 0 && l[2] + 0.5*fs <= t[1]};
 });
});
console.log('JSON:' + JSON.stringify(R));
"""


def teste_a_bussola_cabe_no_quadro():
    secao(u"a bussola cabe no quadro")
    node = _node()
    if not node:
        checar(u"node disponível para executar o renderizador", False,
               u"PULADO -- sem node")
        return
    import radai_viewer
    corpo = _ORIENTACAO_RODA.split(u"var C = ['esq'")[0]
    d, erro = _rodar_node(_ORIENTACAO_JS + radai_viewer.JS_3D + corpo
                          + _BUSSOLA_RODA, node)
    checar(u"o renderizador executa com a bússola anotada", d is not None,
           erro or u"")
    if d is None:
        return
    for tam, letras in sorted(d.items()):
        fora = [l["t"] for l in letras if not l["dentro"]]
        checar(u"canvas %s: as seis letras dentro" % tam,
               len(letras) == 6 and not fora,
               u"%d letras; fora: %s" % (len(letras), u", ".join(fora)))


def teste_ver_segmentacao_dois_caminhos_e_um_visor():
    secao(u"ver segmentacao: dois caminhos em abas, um visor abaixo")
    import radai_view
    p = radai_view._pagina()
    visivel = re.sub(r"<!--.*?-->", u" ", p, flags=re.S)
    checar(u"sai a frase «Nada aqui processa nada»",
           u"Nada aqui processa nada" not in visivel
           and u"O que já está contornado, nos três planos e em 3D" not in visivel)
    checar(u"«Contornadas nesta máquina» virou «Acervo Local»",
           u"Acervo Local" in p and u"Contornadas nesta máquina" not in p)
    a = _Arvore(p)
    checar(u"as duas abas moram no popup que o cartão do item 1 abre",
           a.dentro(u"vr_guias", u"vr_escolha")
           and a.dentro(u"vr_cartao", u"cx_vr0")
           and u'data-ui-ps-abre="vr_escolha"' in p)
    checar(u"a aba do acervo vem antes da aba da pasta",
           0 <= p.find(u'data-guia="acervo"') < p.find(u'data-guia="pasta"'))
    checar(u"o visor está FORA do item 1, abaixo",
           u"cx_verseg" in a.ancestrais
           and not a.dentro(u"cx_verseg", u"cx_vr0")
           and p.find(u'id="cx_vr0"') < p.find(u'id="cx_verseg"'))
    checar(u"a pasta e as séries encontradas moram na aba da pasta",
           a.dentro(u"vr_pasta", u"vr_guias-p-pasta")
           and a.dentro(u"vr_lista", u"vr_guias-p-pasta")
           and a.dentro(u"vr_vazio", u"vr_guias-p-pasta"))
    checar(u"e a lista do acervo na aba do acervo",
           a.dentro(u"vr_acervo", u"vr_guias-p-acervo"))
    css = radai_view.CSS
    checar(u"as duas colunas da v8.3 saíram da folha",
           u".vr-duas" not in css)
    seletores = [s.strip() for sel in re.findall(
        r"([^{}]+)\{", re.sub(r"/\*.*?\*/", u"", css, flags=re.S))
        for s in sel.split(u",")]
    checar(u"`.oculto` com escopo, e não solto na página",
           u".vr .oculto{display:none" in css
           and u".oculto" not in seletores, u", ".join(
               s for s in seletores if u"oculto" in s))
    balao = [s for s in seletores if u"ui-balao" in s or u"ui-ajuda" in s]
    checar(u"a folha do Ver segmentação não redefine o balão do `?`",
           not balao, u", ".join(balao))
    checar(u"o campo da pasta tem `type`, e a folha do sistema o alcança",
           re.search(r'<input[^>]*type="text"[^>]*id="vr_pasta"', p) is not None)
    corpo = _corpo_js(radai_view.JS, u"vrAbrirDoAcervo")
    checar(u"o acervo abre a série direto no visor",
           u"vrAbrirSerie(" in corpo, corpo[:80])
    checar(u"e não atravessa a busca (não preenche a pasta nem varre)",
           u"vr_pasta" not in corpo and u"vrVarrer(" not in corpo)
    # GUARDA: a ação é a última coluna, pregada à direita; a tabela rola de
    # lado dentro do cartão, e sem o `position:sticky` o Abrir sai da vista.
    checar(u"a ação vem na ÚLTIMA coluna da tabela da pasta, pregada à direita",
           u"'<td class=\"vr-acao\"><button type=\"button\" class=\"ui-bt mini\" data-abrir"
           in radai_view.JS
           and u"position:sticky;right:0" in css)
    import radai_ui
    checar(u"  e na do acervo, que é a tabela da Suite (C2)",
           u"uiTabelaAcervo('vr_acervo'" in radai_view.JS
           and u"'<td class=\"ua-acao\">' + (falta" in radai_ui.COMPONENTES_JS
           and u".ui-acervo .ua-acao{position:sticky;right:0"
           in radai_ui.COMPONENTES)


_ACERVO_FALHA_JS = u"""
var CODE = {textContent: ''};
var MSG = {innerHTML: '', textContent: '', style: {},
           querySelector: function(s){ return s === 'code' ? CODE : null; }};
var PELO_UI = [];
var window = {
 uiHTML: function(e, h){ PELO_UI.push(h); e.innerHTML = h; },
 uiTexto: function(e, t){ e.textContent = t; }};
var document = {querySelectorAll: function(){ return []; }};
var VR = {series: [], escolhida: -1};
var VR_TABELA = null;
function vrPintar(){}
function vrAbrirSerie(){}
function vrEl(id){ return id === 'vr_acervo_msg' ? MSG : null; }
function fetch(){ return Promise.reject(new TypeError('Failed to fetch')); }
"""

_ACERVO_FALHA_RODA_JS = u"""
vrAbrirDoAcervo({bilhete: 'b'}, 0);
setTimeout(function(){
 console.log('JSON:' + JSON.stringify({pelo_ui: PELO_UI, html: MSG.innerHTML,
  code: CODE.textContent, texto: MSG.textContent}));
}, 30);
"""


def teste_o_acervo_que_nao_abre_diz_em_nos_separados():
    secao(u"o acervo que nao abre diz em nos separados")
    node = _node()
    if not node:
        checar(u"node disponível para executar o acervo", False,
               u"PULADO -- sem node")
        return
    import radai_view
    funcs = [_funcao_js(radai_view.JS, n)
             for n in (u"vrAcervoMsg", u"vrAbrirDoAcervo", u"vrCarregandoVisor",
                       u"vrMarcarAcervo", u"vrFalhaAoAbrir")]
    checar(u"as funções do acervo estão na página", all(funcs),
           str([bool(f) for f in funcs]))
    if not all(funcs):
        return
    d, erro = _rodar_node(_ACERVO_FALHA_JS + u"\n".join(funcs)
                          + _ACERVO_FALHA_RODA_JS, node)
    checar(u"o acervo executa com o fetch recusando", d is not None, erro or u"")
    if d is None:
        return
    checar(u"a falha escreve a frase num nó marcado, pelo `uiHTML`",
           len(d["pelo_ui"]) == 1 and d["pelo_ui"][0].startswith(
               u"<span data-radai-frase>não consegui abrir a série</span>"),
           str(d)[:240])
    checar(u"  e a exceção vai sozinha no `<code>`, que não se traduz",
           d["code"] == u"Failed to fetch", str(d)[:240])
    checar(u"  e nada de «ERRO: » colado à exceção",
           u"ERRO" not in d["texto"] and u"ERRO" not in d["html"], str(d)[:240])


def teste_o_visor_de_um_eixo_chega_as_telas():
    secao(u"o visor de um eixo chega as telas")
    import radai_viewer
    for nome in (u"function ordemDeBisseccao(", u"function RadaiCargaUmEixo(",
                 u"function RadaiUmEixo(", u"function umEixoAbrir(",
                 u"function umEixoFechar(", u"function umEixoNaCelula(",
                 u"function umEixoSoltar(", u"function umEixoVarrer("):
        checar(u"`radai_viewer.JS` traz %s" % nome, nome in radai_viewer.JS)
    try:
        import radai_batch
        pl = radai_batch._pagina()
        checar(u"a página do Rodar agora TRAZ as funções do visor de um eixo "
               u"(não prova que o botão as chama)",
               u"function umEixoNaCelula(" in pl
               and u"function umEixoAbrir(" in pl)
        faltam = _costura_do_lote(pl)
        checar(u"o «ver imagens» do Rodar agora ABRE o visor de um eixo",
               not faltam, u"; ".join(faltam))
    except Exception as e:
        checar(u"a página do Rodar agora monta", False,
               u"%s: %s" % (type(e).__name__, str(e)[:120]))
    try:
        import radai_bridge
        pb = radai_bridge.pagina()
        faltam = _costura_da_ponte(pb)
        checar(u"o visor do DicomBridge carrega por bissecção",
               not faltam, u"; ".join(faltam))
    except Exception as e:
        checar(u"a página do DicomBridge monta", False,
               u"%s: %s" % (type(e).__name__, str(e)[:120]))
    css = re.sub(r"/\*.*?\*/", u"", radai_viewer.CSS_UM_EIXO, flags=re.S)
    soltos = []
    for sel in re.findall(r"([^{}]+)\{", css):
        for s in sel.split(u","):
            s = s.strip()
            if s and not s.startswith(u"@media") and not s.startswith(u".ue"):
                soltos.append(s)
    checar(u"a folha do visor de um eixo só tem seletor `.ue…`", not soltos,
           u", ".join(soltos[:4]))
    try:
        from fastapi import FastAPI
        import radai_viewseg
        app = FastAPI()
        radai_viewseg.montar(app)
        vivas = set(getattr(r, "path", u"") for r in app.routes)
        for rota in (u"/api/umeixo/abrir", u"/api/umeixo/corte"):
            checar(u"a rota %s existe depois de montada" % rota, rota in vivas)
    except ImportError:
        checar(u"fastapi disponível para montar as rotas", False, u"PULADO")


_DICA3D_JS = u"""
var DICA = {textContent: '', marcado: true};
var PELO_UI = [];
var N3 = {itens: [1]};
function n3Canvas(){ return {}; }
function n3Desenhar(){}
function n3Mostrar(){}
var document = {getElementById: function(id){ return id === 'dica3d' ? DICA : null; }};
var window = {uiTexto: function(e, t){ PELO_UI.push(t); e.textContent = t;
                                       e.marcado = false; }};
function fetch(){ return Promise.reject(new TypeError('Failed to fetch')); }
"""

_DICA3D_RODA_JS = u"""
n3Carregar('p', 'rs', []);
var R = {vazia: DICA.textContent};
n3Carregar('p', 'rs', ['Heart_ai']);
R.montando = DICA.textContent;
setTimeout(function(){
 R.erro = DICA.textContent; R.pelo_ui = PELO_UI; R.marcado = DICA.marcado;
 console.log('JSON:' + JSON.stringify(R));
}, 30);
"""


def teste_a_dica_do_3d_passa_pelo_ui_texto():
    secao(u"a dica do 3D passa pelo uiTexto")
    node = _node()
    if not node:
        checar(u"node disponível para executar a dica do 3D", False,
               u"PULADO -- sem node")
        return
    import radai_viewer
    funcs = [_funcao_js(radai_viewer.JS_3D, n)
             for n in (u"n3Carregar", u"n3Dica")]
    checar(u"`n3Carregar` e `n3Dica` estão no JS do 3D", all(funcs),
           str([bool(f) for f in funcs]))
    if not all(funcs):
        return
    d, erro = _rodar_node(_DICA3D_JS + u"\n".join(funcs) + _DICA3D_RODA_JS,
                          node)
    checar(u"a dica executa com o fetch recusando", d is not None, erro or u"")
    if d is None:
        return
    esperadas = [u"marque uma estrutura para ver em 3D",
                 u"montando a superfície…"]
    checar(u"as duas frases da dica passam pelo `uiTexto`",
           d["pelo_ui"][:2] == esperadas, str(d["pelo_ui"])[:160])
    checar(u"  e o erro também (a marca sai, mesmo sem chave)",
           len(d["pelo_ui"]) == 3 and d["pelo_ui"][2].startswith(
               u"não consegui montar:"), str(d["pelo_ui"])[:160])
    import radai_phrases as _F
    chaves = set(_F.normalizar(t[0]) for t in _F.TABELA)
    checar(u"  e as duas frases têm chave no dicionário",
           all(_F.normalizar(e) in chaves for e in esperadas))


_BASE_IDIOMA = u"http://idioma.radai.test"


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


def _servir_idioma(ctx, paginas, js, posts):
    import json as _json
    from urllib.parse import urlsplit

    def atender(route):
        caminho = urlsplit(route.request.url).path
        if caminho in paginas:
            route.fulfill(status=200, content_type=u"text/html; charset=utf-8",
                          body=paginas[caminho])
        elif caminho == u"/radai-idiomas.js":
            route.fulfill(status=200, content_type=u"application/javascript",
                          body=js)
        elif caminho == u"/api/idioma" and route.request.method == u"POST":
            posts.append(route.request.post_data or u"")
            route.fulfill(status=200, content_type=u"application/json",
                          body=u'{"ok": true}')
        elif caminho == u"/api/aceite":
            route.fulfill(status=200, content_type=u"application/json",
                          body=_json.dumps({u"pontos": [], u"fontes": [],
                                            u"registro": {}, u"versao": u"1.5"}))
        else:
            route.fulfill(status=404, body=u"")
    ctx.route(_BASE_IDIOMA + u"/**", atender)


def _escolher_no_aceite(nav, pagina, js, cod):
    posts = []
    ctx = nav.new_context(viewport={"width": 1280, "height": 860})
    _servir_idioma(ctx, {u"/aceite": pagina}, js, posts)
    fora = {}
    try:
        pg = ctx.new_page()
        pg.goto(_BASE_IDIOMA + u"/aceite", wait_until="networkidle")
        bt = pg.locator(u".ac-lang .radai-lang .rl-bt")
        fora["botao"] = bt.count()
        if bt.count() != 1:
            return fora, posts
        fora["texto_botao"] = bt.inner_text().strip()
        cx = bt.locator(u".rl-band").bounding_box() or {}
        fora["caixa_bandeira"] = (round(cx.get("width", 0)),
                                  round(cx.get("height", 0)))
        fora["svg_no_botao"] = bt.locator(u".rl-band svg").count()
        lista = pg.locator(u".ac-lang .radai-lang .lista")
        fora["fechada_antes"] = not lista.is_visible()
        bt.click()
        pg.wait_for_timeout(260)
        fora["aberta"] = lista.is_visible()
        fora["expandido"] = bt.get_attribute(u"aria-expanded")
        fora["opcoes"] = lista.locator(u".rl-op").count()
        fora["opcoes_com_svg"] = lista.locator(u".rl-op .rl-band svg").count()
        fora["vaos"] = pg.evaluate(
            u"Array.prototype.map.call(document.querySelectorAll("
            u"'.ac-lang .lista .rl-op'),function(o){"
            u"var b=o.querySelector('.rl-band').getBoundingClientRect(),"
            u"r=document.createRange();"
            u"r.selectNodeContents(o.querySelector('.rl-nome'));"
            u"var n=r.getBoundingClientRect();"
            u"return [o.getAttribute('data-cod'),Math.round(n.left-b.right)]})")
        fora["foco"] = pg.evaluate(
            u"(document.activeElement||{}).getAttribute"
            u"&&document.activeElement.getAttribute('data-cod')")
        pg.keyboard.press(u"ArrowDown")
        fora["foco_seta"] = pg.evaluate(
            u"document.activeElement.getAttribute('data-cod')")
        pg.keyboard.press(u"Escape")
        pg.wait_for_timeout(260)
        fora["esc_fecha"] = (not lista.is_visible()) and pg.evaluate(
            u"document.activeElement.classList.contains('rl-bt')")
        if not lista.is_visible():
            bt.click()
            pg.wait_for_timeout(260)
        with pg.expect_navigation(timeout=5000):
            lista.locator(u'.rl-op[data-cod="%s"]' % cod).click()
        pg.wait_for_load_state("networkidle")
        fora["guardado"] = pg.evaluate(u"localStorage.getItem('radai_idioma')")
        fora["lang"] = pg.evaluate(u"document.documentElement.lang")
        fora["texto_depois"] = pg.locator(
            u".ac-lang .radai-lang .rl-bt").inner_text().strip()
        return fora, posts
    finally:
        ctx.close()


def teste_o_seletor_de_idioma_no_navegador():
    secao(u"o seletor de idioma com bandeira, no navegador")
    import json as _json
    import shutil
    import radai_consent
    import radai_languages as I

    base = _tempfile.mkdtemp(prefix="radai_ac_ui_idioma_")
    cfg = os.path.join(base, "radai_watcher.config")
    io.open(cfg, "w", encoding="utf-8").write(u"ROOT=\n")
    guardado = os.environ.get("RADAI_CONFIG")
    os.environ["RADAI_CONFIG"] = cfg
    try:
        pagina = radai_consent.pagina_aceite()
        m = re.sub(r"(?s)<script.*?</script>", u" ", pagina)
        m = re.sub(r"(?s)<!--.*?-->", u" ", m)
        checar(u"o aceite tem a âncora do seletor de hoje (fora de comentário)",
               u"data-radai-idiomas" in m, u"")
        js = I.corpo_js()
        exe = _chromium()
        try:
            from playwright.sync_api import sync_playwright
        except Exception:
            sync_playwright = None
        if not exe or sync_playwright is None:
            print(u"    PULADO o navegador: sem Playwright ou sem Chromium")
            return
        grava = u"return fetch('/api/idioma',"
        checar(u"a gravação na estação é UMA linha do dicionário",
               js.count(grava) == 1, str(js.count(grava)))
        js_isca = js.replace(grava, u"return (function(){ return null })(")
        with sync_playwright() as pw:
            nav = pw.chromium.launch(executable_path=exe, headless=True)
            try:
                f, posts = _escolher_no_aceite(nav, pagina, js, u"de")
                checar(u"o aceite mostra UM seletor", f.get("botao") == 1,
                       repr(f.get("botao")))
                checar(u"  com a bandeira desenhada no botão, 21 x 14",
                       f.get("svg_no_botao") == 1
                       and f.get("caixa_bandeira") == (21, 14),
                       repr((f.get("svg_no_botao"), f.get("caixa_bandeira"))))
                checar(u"  e o nome da língua em que a tela abriu (English)",
                       u"English" in (f.get("texto_botao") or u""),
                       repr(f.get("texto_botao")))
                checar(u"a lista nasce fechada e abre no clique",
                       f.get("fechada_antes") and f.get("aberta")
                       and f.get("expandido") == u"true",
                       repr((f.get("fechada_antes"), f.get("aberta"))))
                checar(u"  com as doze línguas, cada uma com a bandeira",
                       f.get("opcoes") == 12 and f.get("opcoes_com_svg") == 12,
                       repr((f.get("opcoes"), f.get("opcoes_com_svg"))))
                vaos = f.get("vaos") or []
                checar(u"  e o nome colado na bandeira em todas (o árabe "
                       u"também)", len(vaos) == 12
                       and all(0 <= v <= 14 for _c, v in vaos),
                       repr([x for x in vaos if not 0 <= x[1] <= 14][:3]))
                checar(u"o foco vai para a língua de agora, e a seta anda",
                       f.get("foco") == u"en" and f.get("foco_seta") == u"es",
                       repr((f.get("foco"), f.get("foco_seta"))))
                checar(u"  e o Esc fecha e devolve o foco ao botão",
                       f.get("esc_fecha") is True, repr(f.get("esc_fecha")))
                checar(u"escolher grava no navegador",
                       f.get("guardado") == u"de", repr(f.get("guardado")))
                corpos = [_json.loads(p or u"{}") for p in posts]
                checar(u"  E manda a escolha à estação, só com o código",
                       corpos == [{u"idioma": u"de"}], repr(posts))
                checar(u"  e a tela volta em alemão, com o botão dizendo "
                       u"Deutsch",
                       f.get("lang") == u"de"
                       and u"Deutsch" in (f.get("texto_depois") or u""),
                       repr((f.get("lang"), f.get("texto_depois"))))
                fi, posts_i = _escolher_no_aceite(nav, pagina, js_isca, u"de")
                checar(u"[isca] sem o fetch, a tela troca e a estação não "
                       u"recebe nada (a checagem distingue as duas)",
                       fi.get("guardado") == u"de" and posts_i == [],
                       repr((fi.get("guardado"), posts_i)))

                grade = (u'<!doctype html><html><head><meta charset="utf-8">'
                         u'</head><body><div data-radai-idiomas="grade"></div>'
                         u'</body></html>')
                grade = radai_ui_aplicar_idioma(grade)
                posts = []
                ctx = nav.new_context(viewport={"width": 900, "height": 600})
                _servir_idioma(ctx, {u"/grade": grade}, js, posts)
                pg = ctx.new_page()
                pg.goto(_BASE_IDIOMA + u"/grade", wait_until="networkidle")
                rad = pg.locator(u'.radai-lang.rl-grade [role="radio"]')
                marcada = pg.locator(
                    u'.radai-lang.rl-grade [aria-checked="true"]')
                checar(u"a grade mostra as doze como radio, com bandeira",
                       rad.count() == 12
                       and pg.locator(u".rl-grade .rl-band svg").count() == 12,
                       str(rad.count()))
                checar(u"  com a língua de agora marcada (en)",
                       marcada.count() == 1
                       and marcada.get_attribute(u"data-cod") == u"en",
                       str(marcada.count()))
                with pg.expect_navigation(timeout=5000):
                    pg.click(u'.rl-grade [data-cod="fr"]')
                pg.wait_for_load_state("networkidle")
                marcada = pg.locator(
                    u'.radai-lang.rl-grade [aria-checked="true"]')
                checar(u"  e escolher na grade grava, recarrega e marca",
                       [_json.loads(p) for p in posts] == [{u"idioma": u"fr"}]
                       and marcada.get_attribute(u"data-cod") == u"fr",
                       repr(posts))
                ctx.close()
            finally:
                nav.close()
    finally:
        if guardado is None:
            os.environ.pop("RADAI_CONFIG", None)
        else:
            os.environ["RADAI_CONFIG"] = guardado
        shutil.rmtree(base, ignore_errors=True)


def radai_ui_aplicar_idioma(pagina):
    import radai_languages
    import radai_ui
    return radai_ui.aplicar(radai_languages.aplicar(pagina))



_VER_ARQUIVOS = (
    (u"RS_RadAI_20260926_00000001.dcm", u"RadAI_OAR",
     ((u"Heart_ai", (255, 60, 60), (5, 10), (50, 50, 70, 70)),
      (u"Lung_L_ai", (80, 160, 255), (3, 15), (80, 40, 110, 90)))),
    (u"RS_RadAI_FAST_20260926_00000001.dcm", u"RadAI_OAR_Fast",
     ((u"Heart_ai", (255, 60, 60), (5, 10), (52, 52, 68, 68)),)),
    (u"RS_RadAI_FULL_20260926_00000001.dcm", u"STUDY_full",
     ((u"Heart_ai", (255, 60, 60), (5, 10), (40, 40, 80, 80)),
      (u"Lung_L_ai", (80, 160, 255), (3, 15), (80, 40, 110, 90)),
      (u"Lung_Upper_Lobe_L_ai", (60, 120, 220), (9, 15), (80, 40, 110, 64)),
      (u"Rectum_der", (170, 110, 60), (1, 3), (60, 90, 70, 100)))),
    (u"RS_RadAI_TS_20260926_00000001.dcm", u"STUDY_ts",
     ((u"heart_ts", (255, 60, 60), (5, 10), (44, 44, 76, 76)),)),
    (u"RS_RadAI_ORB_20260926_00000001.dcm", u"STUDY_orb",
     ((u"Eye_L_orb", (240, 220, 90), (16, 18), (20, 20, 30, 30)),)),
)


def _ver_rs_sintetico(caminho, rotulo, rois):
    from pydicom.dataset import Dataset, FileDataset
    from pydicom.sequence import Sequence
    from pydicom.uid import ExplicitVRLittleEndian, generate_uid
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
    ds.StructureSetLabel = rotulo
    ssr, rcs = [], []
    for i, (nome, cor, (z0, z1), (c0, r0, c1, r1)) in enumerate(rois, 1):
        r = Dataset()
        r.ROINumber = i
        r.ROIName = nome
        ssr.append(r)
        rc = Dataset()
        rc.ReferencedROINumber = i
        rc.ROIDisplayColor = list(cor)
        cs = []
        xs = (-128.0 + 2.0 * c0, -128.0 + 2.0 * c1)
        ys = (-128.0 + 2.0 * r0, -128.0 + 2.0 * r1)
        for z in range(z0, z1 + 1):
            zm = 3.0 * z
            c = Dataset()
            c.ContourGeometricType = "CLOSED_PLANAR"
            c.NumberOfContourPoints = 4
            c.ContourData = [xs[0], ys[0], zm, xs[1], ys[0], zm,
                             xs[1], ys[1], zm, xs[0], ys[1], zm]
            cs.append(c)
        rc.ContourSequence = Sequence(cs)
        rcs.append(rc)
    ds.StructureSetROISequence = Sequence(ssr)
    ds.ROIContourSequence = Sequence(rcs)
    try:
        ds.save_as(caminho, enforce_file_format=True)
    except TypeError:
        ds.save_as(caminho, write_like_original=False)


def _ver_serie_com_rtstructs(n=20):
    from datetime import datetime
    sys.path.insert(0, AQUI)
    import make_test_series
    base = _tempfile.mkdtemp(prefix="radai_ac_ui_ver_")
    pasta = os.path.join(base, "PAC_VER", "CT")
    uid = make_test_series.escreve_serie(pasta, "PAC_VER", datetime.now(), n)
    for arq, rot, rois in _VER_ARQUIVOS:
        _ver_rs_sintetico(os.path.join(pasta, arq), rot, rois)
    return base, pasta, uid


def _ver_xs_do_caminho(d):
    nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", d or u"")]
    return nums[0::2]


def teste_ver_segmentacao_compara_dois_axiais():
    secao(u"ver segmentacao: dois axiais, um arquivo em cada")
    import json
    import radai_view
    import radai_viewseg
    p = radai_view._pagina()
    visivel = re.sub(r"<!--.*?-->", u" ", p, flags=re.S)
    a = _Arvore(p)
    for k in (u"0", u"1"):
        checar(u"o lado %s tem o visor axial" % k,
               re.search(r'<section class="cp-lado" data-lado="%s"' % k, p)
               is not None and (u'id="cp_visor%s"' % k) in p
               and a.dentro(u"cp_visor%s" % k, classe=u"cp-lado"))
        checar(u"  e o seletor do arquivo ABAIXO do visor",
               a.dentro(u"cp_sel%s" % k, classe=u"cp-lado")
               and p.find(u'id="cp_visor%s"' % k)
               < p.find(u'id="cp_sel%s"' % k))
        checar(u"  e a lista das estruturas abaixo do seletor",
               a.dentro(u"cp_chips%s" % k, classe=u"cp-lado")
               and p.find(u'id="cp_sel%s"' % k)
               < p.find(u'id="cp_chips%s"' % k))
    checar(u"o lado 0 vem antes do lado 1 (esquerda, direita)",
           0 <= p.find(u'data-lado="0"') < p.find(u'data-lado="1"'))
    checar(u"UMA barra de corte, janela e zoom, fora dos dois lados",
           p.count(u'id="cp_rg"') == 1 and not a.dentro(u"cp_rg",
                                                         classe=u"cp-lado")
           and a.dentro(u"cp_rg", u"cp_raiz"))
    for fora in (u'id="imgCo"', u'id="imgSa"', u'id="cv3D"',
                 u'data-v="coronal"', u'data-v="sagital"', u'data-v="3d"',
                 u'id="vs_palco"'):
        checar(u"a tela não traz %s" % fora, fora not in p)
    js = radai_viewseg.JS
    for velho in (u"abertos[0]", u"VS_MAX_RS", u"VS.abertos"):
        checar(u"o JS não tem mais `%s`" % velho, velho not in js)
    checar(u"«Marque até 6» e o link ao calibrador saíram da tela",
           u"Marque até 6" not in visivel and u'href="/calibrador"'
           not in visivel)
    checar(u"«AI completo» não aparece no texto da tela",
           u"AI completo" not in visivel and u"AI_completo" not in visivel,
           visivel[max(0, visivel.find(u"AI completo") - 60):][:140])
    m = re.search(r"var VR_CONJ = (\[.*?\]);", p, re.S)
    lista = json.loads(m.group(1)) if m else []
    por = dict((c["cod"], c) for c in lista)
    checar(u"o chip do FULL diz FULL", (por.get(u"full") or {}).get(
        u"rotulo_curto") == u"FULL", str(por.get(u"full"))[:120])
    checar(u"o OAR_Fast é reconhecido, e só aparece quando está na pasta",
           (por.get(u"fast") or {}).get(u"infixo") == u"FAST_"
           and (por.get(u"fast") or {}).get(u"so_se_tem") is True,
           str(por.get(u"fast"))[:120])
    checar(u"o /ver chama o comparador para abrir a série",
           u"cpAbrirSerie(" in _corpo_js(radai_view.JS, u"vrAbrirSerie"))
    checar(u"o encaixe do palco repinta as abas da janela",
           u"cpRepintarAbas(" in _corpo_js(js, u"cpAjustarPalcos")
           and u"_uiPintar" in _corpo_js(js, u"cpRepintarAbas"))
    checar(u"a janela é o seletor de abas do sistema (`data-ui-abas`)",
           re.search(r'<select id="cp_janela" data-ui-abas', p) is not None)


def teste_ver_cada_lado_le_o_seu_arquivo():
    secao(u"ver segmentacao: as rotas, arquivo a arquivo")
    try:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
    except Exception as e:
        checar(u"fastapi e o TestClient disponíveis", False,
               u"PULADO: %s" % type(e).__name__)
        return
    import inspect
    import json
    import shutil
    import struct
    import radai_viewseg as V
    base, pasta, uid = _ver_serie_com_rtstructs()
    try:
        app = FastAPI()
        V.montar(app)
        cli = TestClient(app)

        rot = dict((arq, V.rotulo_do_arquivo(arq)) for arq, _r, _o
                   in _VER_ARQUIVOS)
        oar, fast, full, ts, orb = [x[0] for x in _VER_ARQUIVOS]
        checar(u"o FULL se chama FULL", rot[full]["curto"] == u"FULL",
               str(rot[full]))
        checar(u"o entregue é o OAR, e é entregue",
               rot[oar]["curto"] == u"OAR" and rot[oar]["entregue"])
        checar(u"o OAR_Fast é reconhecido pelo infixo FAST_, e é entregue",
               rot[fast]["curto"] == u"OAR_Fast" and rot[fast]["entregue"]
               and rot[fast]["cod"] == u"fast", str(rot[fast]))
        checar(u"o TS cru e o plugin da órbita têm o nome do registro",
               rot[ts]["curto"] == u"TS cru" and rot[orb]["cod"] == u"orb")
        des = V.rotulo_do_arquivo(u"RS_RadAI_ZZZ_20260926_1.dcm")
        checar(u"o infixo desconhecido NÃO vira o entregue",
               not des["entregue"] and des["cod"] == u"", str(des))

        d = cli.post("/api/verseg/series", json={"pasta": pasta}).json()
        series = d.get("series") or []
        checar(u"a busca acha a série com os cinco arquivos",
               len(series) == 1 and len(series[0].get("rs") or []) == 5,
               str(d)[:200])
        if len(series) != 1:
            return
        s = series[0]
        b = s.get("b", u"")
        ordem = [r["arquivo"] for r in s["rs"]]
        checar(u"os arquivos vêm na ordem da tela: OAR, OAR_Fast, FULL, TS, "
               u"plugins", ordem == [oar, fast, full, ts, orb], str(ordem))
        crua = json.dumps(s["rs"], ensure_ascii=False)
        checar(u"nenhum rótulo diz «AI completo»", u"AI completo" not in crua
               and u"AI_completo" not in crua, crua[:160])

        f = cli.get("/api/verseg/forma", params={"b": b, "uid": uid}).json()
        checar(u"a forma e o espaçamento vêm da série",
               f.get("forma") == [20, 128, 128]
               and [round(v, 3) for v in f.get("sp") or []] == [3.0, 2.0, 2.0]
               and f.get("hu") is True, str(f))

        e = cli.get("/api/verseg/estruturas", params={"b": b, "rs": full}).json()
        nomes = sorted(x["nome"] for x in e.get("estruturas") or [])
        checar(u"as estruturas do FULL são as do FULL",
               nomes == sorted(r[0] for r in _VER_ARQUIVOS[2][2]), str(nomes))
        checar(u"  e o rótulo DICOM vem do arquivo",
               e.get("rotulo_dicom") == u"STUDY_full" and e.get("rs") == full,
               str(e)[:160])

        def contornos(rs, corte):
            return cli.get("/api/verseg/contornos", params={
                "b": b, "uid": uid, "rs": rs, "corte": corte}).json()
        co = contornos(oar, 7)
        cf = contornos(full, 7)
        checar(u"a resposta diz de QUAL arquivo ela é",
               co.get("rs") == oar and cf.get("rs") == full, str(co)[:120])
        ho = [x for x in co.get("estruturas") or [] if x["n"] == u"Heart_ai"]
        hf = [x for x in cf.get("estruturas") or [] if x["n"] == u"Heart_ai"]
        xo = _ver_xs_do_caminho(ho[0]["d"]) if ho else []
        xf = _ver_xs_do_caminho(hf[0]["d"]) if hf else []
        checar(u"o Heart_ai do OAR é o do OAR (x de 50,5 a 70,5)",
               bool(xo) and min(xo) == 50.5 and max(xo) == 70.5, str(xo))
        checar(u"e o Heart_ai do FULL é o do FULL (x de 40,5 a 80,5) — a "
               u"homônima não é trocada",
               bool(xf) and min(xf) == 40.5 and max(xf) == 80.5, str(xf))
        c0 = contornos(oar, 0)
        checar(u"corte sem contorno devolve lista vazia, e não erro",
               c0.get("estruturas") == [] and not c0.get("erro"), str(c0))
        for ruim in (u"..\\" + oar, u"../" + oar, u"C:\\x\\" + oar,
                     u"RS_RadAI_20260101_nao_existe.dcm"):
            r = contornos(ruim, 7)
            checar(u"rs recusado: %s" % ruim, bool(r.get("erro"))
                   and not r.get("estruturas"), str(r)[:120])

        ct = cli.get("/api/verseg/ct", params={"b": b, "uid": uid,
                                               "corte": 7, "j": "mediastino"})
        ok_png = ct.status_code == 200 and ct.content[:8] == b"\x89PNG\r\n\x1a\n"
        checar(u"o corte da TC sai em PNG", ok_png, str(ct.status_code))
        if ok_png:
            w, h, prof, tipo = struct.unpack(">IIBB", ct.content[16:26])
            checar(u"  em escala de cinza, no tamanho da série (128 × 128)",
                   (w, h, prof, tipo) == (128, 128, 8, 0), str((w, h, prof, tipo)))
            checar(u"  com guarda privada no navegador",
                   u"private" in ct.headers.get("cache-control", u""))
            osso = cli.get("/api/verseg/ct", params={
                "b": b, "uid": uid, "corte": 7, "j": "osso"})
            checar(u"a janela muda a imagem", osso.content != ct.content)
        morto = cli.get("/api/verseg/ct", params={"b": "f" * 32, "uid": uid,
                                                  "corte": 1})
        checar(u"bilhete morto é 404", morto.status_code == 404,
               str(morto.status_code))

        cen = cli.get("/api/verseg/centro", params={
            "b": b, "uid": uid, "rs": oar, "nome": u"Heart_ai"}).json()
        checar(u"o centro da estrutura sai do arquivo pedido (corte 7,5)",
               abs(float(cen.get("z", -99)) - 7.5) < 0.6
               and abs(float(cen.get("x", -99)) - 60.0) < 1.0, str(cen))

        ruins = []
        for r in app.routes:
            if "GET" not in (getattr(r, "methods", None) or ()):
                continue
            ps = inspect.signature(r.endpoint).parameters
            ruins += [u"%s(%s)" % (r.path, n) for n in ps
                      if n in (u"pasta", u"caminho", u"dir", u"raiz")]
        checar(u"nenhuma rota GET do visor recebe caminho", not ruins,
               u", ".join(ruins))
    finally:
        shutil.rmtree(base, ignore_errors=True)


_VER_JS_HARNESS = u"""
var PEDIDOS = [], PINTADOS = [];
function fetch(u){
 PEDIDOS.push(u);
 var q = new URL(u, 'http://x').searchParams;
 var rs = q.get('rs') || '';
 var corpo = {rs: rs, corte: +q.get('corte'), estruturas: [
   {n: 'Heart_ai', c: [255, 0, 0], d: 'M1 1 L2 2 Z#' + rs},
   {n: 'Lung_L_ai', c: [0, 0, 255], d: 'M3 3 L4 4 Z#' + rs}]};
 return Promise.resolve({json: function(){ return Promise.resolve(corpo); }});
}
function Image(){
 var eu = this, s = '';
 Object.defineProperty(this, 'src', {get: function(){ return s; },
  set: function(v){ s = v; PEDIDOS.push(v);
   setTimeout(function(){ if(eu.onload) eu.onload(); }, 0); }});
}
cpPintar = function(z, url, dados){
 PINTADOS.push({z: z, url: url,
  rs0: dados[0] && dados[0].rs, rs1: dados[1] && dados[1].rs,
  svg0: cpSvgDe(cpVisiveis(CP.lados[0], dados[0])),
  svg1: cpSvgDe(cpVisiveis(CP.lados[1], dados[1]))});
};
function espera(ms){ return new Promise(function(r){ setTimeout(r, ms); }); }
var FULL = 'RS_RadAI_FULL_1.dcm', OAR = 'RS_RadAI_20260926_1.dcm';
(async function(){
 var R = {};
 R.padroes = [
  cpPadroes([{arquivo: OAR, cod: 'oar'}, {arquivo: 'RS_RadAI_FAST_1.dcm', cod: 'fast'},
             {arquivo: FULL, cod: 'full'}, {arquivo: 'RS_RadAI_TS_1.dcm', cod: 'ts'}]),
  cpPadroes([{arquivo: 'RS_RadAI_TS_1.dcm', cod: 'ts'}]),
  cpPadroes([{arquivo: 'RS_RadAI_FAST_1.dcm', cod: 'fast'}, {arquivo: FULL, cod: 'full'}])];
 R.bases = ['Rectum_der', 'Heart_ai', 'heart_ts', 'Eye_L_orb', 'Kidney_L_nv',
            'Heart_v3D'].map(cpBase);
 R.aposentado = [cpAposentado('Rectum_der'), cpAposentado('Rectum_ai')];

 CP.serie = {b: 'B', uid: 'U', cortes: 20};
 cpDefinirForma([20, 128, 128], [3, 2, 2], true);
 CP.lados = [cpNovoLado(0), cpNovoLado(1)];
 CP.lados[0].arq = FULL; CP.lados[1].arq = OAR;
 CP.lados[0].ligadas = {'Heart_ai': 1, 'Lung_L_ai': 1};
 CP.lados[1].ligadas = {'Heart_ai': 1};
 CP.corte = 7;
 cpPedirMostrar();
 await espera(40);
 R.primeiro = {pedidos: PEDIDOS.slice(), pintados: PINTADOS.slice()};

 PEDIDOS = []; PINTADOS = [];
 cpAndar(2);
 await espera(40);
 cpJanela('pulmao');
 await espera(40);
 R.depois = {pedidos: PEDIDOS.slice(), pintados: PINTADOS.slice(),
             corte: CP.corte, janela: CP.janela};

 var antes = JSON.stringify(CP.lados[1].ligadas);
 cpAlternar(CP.lados[0], 'Heart_ai');
 R.indep = {lado0: CP.lados[0].ligadas, lado1_igual: antes === JSON.stringify(CP.lados[1].ligadas)};

 var L = cpNovoLado(1);
 L.estruturas = [{nome: 'heart_ts'}, {nome: 'lung_left_ts'}];
 var D = cpNovoLado(0); D.ligadas = {'Heart_ai': 1};
 cpCopiar(D, L);
 R.copiado = L.ligadas;

 R.defesa = cpVisiveis(CP.lados[1], {rs: FULL, estruturas: [
  {n: 'Heart_ai', c: [1, 1, 1], d: 'M0 0 Z'}]}).length;
 console.log('JSON:' + JSON.stringify(R));
})();
"""


def _ver_rodar_harness(js, node):
    return _rodar_node(js + u"\n" + _VER_JS_HARNESS, node)


def _ver_cada_lado_o_seu(d):
    import urllib.parse as up
    falhas = []
    ped = (d.get("primeiro") or {}).get("pedidos") or []
    cont = [dict(up.parse_qsl(up.urlparse(u).query)) for u in ped
            if u.startswith(u"/api/verseg/contornos")]
    rss = sorted(c.get("rs") for c in cont)
    if rss != sorted([u"RS_RadAI_FULL_1.dcm", u"RS_RadAI_20260926_1.dcm"]):
        falhas.append(u"os lados pediram %s" % rss)
    pint = (d.get("primeiro") or {}).get("pintados") or []
    if not pint:
        falhas.append(u"nada foi pintado")
        return falhas
    p = pint[-1]
    if p.get("rs0") != u"RS_RadAI_FULL_1.dcm" or p.get("rs1") != \
            u"RS_RadAI_20260926_1.dcm":
        falhas.append(u"os dados chegaram trocados: %s / %s"
                      % (p.get("rs0"), p.get("rs1")))
    if p.get("svg0", u"").count(u"#RS_RadAI_FULL_1.dcm") != 2 \
            or u"#RS_RadAI_2026" in p.get("svg0", u""):
        falhas.append(u"o lado 0 não desenhou só o FULL")
    if p.get("svg1", u"").count(u"#RS_RadAI_20260926_1.dcm") != 1 \
            or u"#RS_RadAI_FULL" in p.get("svg1", u""):
        falhas.append(u"o lado 1 não desenhou só o OAR (e só o ligado)")
    return falhas


def _ver_urls_com_uid(d):
    fora = []
    for bloco in (u"primeiro", u"depois"):
        for u in (d.get(bloco) or {}).get(u"pedidos") or []:
            if u"uid=" in u:
                fora.append(u)
    return fora


def teste_ver_o_servidor_nas_bordas():
    secao(u"ver segmentacao: o servidor nas bordas")
    import radai_sets
    import radai_view
    import radai_viewseg as V
    a = [u"RS_RadAI_20260101_AAAA1111.dcm", u"RS_RadAI_FULL_20260101_AAAA1111.dcm",
         u"RS_RadAI_20260101_BB.22222.dcm"]
    checar(u"duas séries na pasta: cada uma com os SEUS arquivos",
           V._da_serie(a, u"1.2.3.AAAA1111") == a[:2]
           and V._da_serie(a, u"1.2.3.44.BB.22222") == a[2:],
           str(V._da_serie(a, u"1.2.3.AAAA1111")))
    checar(u"  e, sem UID no nome, a lista inteira (como antes)",
           V._da_serie(a, u"9.9.99999999") == a)

    uids = [u"1.2.3.AAAA1111", u"1.2.3.44.BB.22222", u"9.9.99999999"]
    copia = u"RS_RadAI_20260101_AAAA1111 - Copia.dcm"
    velho = u"RS_RadAI_20250101.dcm"
    checar(u"a série sem arquivo próprio NÃO herda o da outra série da pasta",
           V._da_serie(a, u"9.9.99999999", outros=uids) == [],
           str(V._da_serie(a, u"9.9.99999999", outros=uids)))
    checar(u"  e o recuo guarda só o que não é de série nenhuma (a geração "
           u"sem UID) — a cópia renomeada do arquivo da A continua sendo da A",
           V._da_serie(a + [copia, velho], u"9.9.99999999", outros=uids)
           == [velho], str(V._da_serie(a + [copia, velho], u"9.9.99999999",
                                       outros=uids)))
    checar(u"  e a série com arquivo próprio continua com os SEUS",
           V._da_serie(a, u"1.2.3.AAAA1111", outros=uids) == a[:2])
    d_vs = _tempfile.mkdtemp(prefix="radai_ac_ui_vs_outra_")
    original = V.radai_batch.varrer
    try:
        io.open(os.path.join(d_vs, a[0]), "wb").write(b"\0")
        V.radai_batch.varrer = lambda *args, **kw: [
            {"uid": u"1.2.3.AAAA1111", "pasta": d_vs, "pid": u"A"},
            {"uid": u"9.9.99999999", "pasta": d_vs, "pid": u"B"}]
        lst, _e = V.series_contornadas(d_vs)
        _isca_da_serie = V._da_serie
        try:
            V._da_serie = lambda nomes, uid, outros=(): _isca_da_serie(
                nomes, uid)
            lst_isca, _e2 = V.series_contornadas(d_vs)
        finally:
            V._da_serie = _isca_da_serie
    finally:
        V.radai_batch.varrer = original
        import shutil as _sh_vs
        _sh_vs.rmtree(d_vs, ignore_errors=True)
    checar(u"«Ver segmentação»: a série B da pasta, sem RTSTRUCT, não aparece "
           u"como contornada com o da A", [x.get(u"uid") for x in lst]
           == [u"1.2.3.AAAA1111"], str([x.get(u"uid") for x in lst]))
    checar(u"  (isca) sem os UIDs das outras, a B aparecia com o arquivo da A "
           u"-- a checagem discrimina",
           [x.get(u"uid") for x in lst_isca]
           == [u"1.2.3.AAAA1111", u"9.9.99999999"],
           str([x.get(u"uid") for x in lst_isca]))

    visto = {}
    original = V.radai_batch.varrer
    try:
        def falso(*args, **kw):
            visto.update(kw)
            return []
        V.radai_batch.varrer = falso
        d = _tempfile.mkdtemp(prefix="radai_ac_ui_verbordas_")
        try:
            V.series_contornadas(d)
        finally:
            import shutil
            shutil.rmtree(d, ignore_errors=True)
    finally:
        V.radai_batch.varrer = original
    checar(u"a lista pede TC e RM à varredura",
           u"CT" in (visto.get(u"modalidades") or ())
           and u"MR" in (visto.get(u"modalidades") or ()), str(visto))

    fast = dict((c[u"cod"], c) for c in radai_sets.SAIDAS_DE_MODO).get(
        u"fast") or {}
    r = V.rotulo_do_arquivo(u"RS_RadAI_FAST_20260926_1.dcm")
    checar(u"o OAR_Fast é o do registro (`SAIDAS_DE_MODO`), e é entregue",
           fast.get(u"infixo") == u"FAST_" and r[u"cod"] == u"fast"
           and r[u"curto"] == u"OAR_Fast" and r[u"entregue"] is True, str(r))
    tela = [c for c in radai_view._conjuntos_da_tela() if c[u"cod"] == u"fast"]
    checar(u"  e a lista do /ver o tem UMA vez, com a ajuda do registro",
           len(tela) == 1 and tela[0][u"ajuda"] == fast.get(u"ajuda")
           and tela[0][u"so_se_tem"] is True, str(tela)[:200])
    cods = [c[u"cod"] for c in radai_view._conjuntos_da_tela()]
    checar(u"  e vem logo depois do entregue (OAR, OAR_Fast, FULL, ...)",
           cods[:3] == [u"oar", u"fast", u"full"], str(cods[:5]))
    orig_modos = radai_sets.SAIDAS_DE_MODO
    try:
        radai_sets.SAIDAS_DE_MODO = ()
        r0 = V.rotulo_do_arquivo(u"RS_RadAI_FAST_20260926_1.dcm")
        cods0 = [c[u"cod"] for c in radai_view._conjuntos_da_tela()]
    finally:
        radai_sets.SAIDAS_DE_MODO = orig_modos
    checar(u"sem a entrada do registro, o comparador NÃO o reconhece "
           u"(detecção única)", r0[u"cod"] == u"" and not r0[u"entregue"],
           str(r0))
    checar(u"  e a lista do /ver também não", u"fast" not in cods0, str(cods0))
    todos, apos = V._sufixos_para_o_js()
    checar(u"os sufixos do JS são os do registro, com `_der` e `_abm` "
           u"aposentados",
           sorted(todos) == sorted(s.lower() for s in
                                   radai_sets.SUFIXOS_DE_TODAS_AS_GERACOES)
           and u"_der" in apos and u"_abm" in apos, str(apos))

    base, pasta, uid = _ver_serie_com_rtstructs()
    try:
        ct = V.corte_png(pasta, uid, 7, u"mediastino", True)[0]
        rm = V.corte_png(pasta, uid, 7, u"auto", False)[0]
        checar(u"a janela da RM sai do volume, e não da de TC",
               ct[:8] == rm[:8] == b"\x89PNG\r\n\x1a\n" and ct != rm)
    finally:
        import shutil
        shutil.rmtree(base, ignore_errors=True)


def teste_ver_o_js_de_cada_lado_executa():
    secao(u"ver segmentacao: o JS de cada lado, executado")
    node = _node()
    if not node:
        checar(u"node disponível para executar o comparador", False,
               u"PULADO -- sem node")
        return
    import radai_viewseg
    js = radai_viewseg.JS
    d, erro = _ver_rodar_harness(js, node)
    checar(u"o comparador executa no node", d is not None, erro or u"")
    if d is None:
        return
    F, O = u"RS_RadAI_FULL_1.dcm", u"RS_RadAI_20260926_1.dcm"
    checar(u"de fábrica: FULL à esquerda, OAR à direita",
           d["padroes"][0] == [F, O], str(d["padroes"][0]))
    checar(u"  com um arquivo só, os dois lados mostram o mesmo",
           d["padroes"][1] == [u"RS_RadAI_TS_1.dcm"] * 2, str(d["padroes"][1]))
    checar(u"  sem OAR, o OAR_Fast vai para a direita",
           d["padroes"][2] == [F, u"RS_RadAI_FAST_1.dcm"], str(d["padroes"][2]))
    checar(u"o nome sem sufixo conhece o `_der` aposentado e os plugins",
           d["bases"] == [u"rectum", u"heart", u"heart", u"eye_l",
                          u"kidney_l", u"heart"], str(d["bases"]))
    checar(u"  e diz qual sufixo é aposentado",
           d["aposentado"] == [u"_der", u""], str(d["aposentado"]))
    falhas = _ver_cada_lado_o_seu(d)
    checar(u"cada lado pede e desenha SÓ o seu arquivo", not falhas,
           u"; ".join(falhas))

    import urllib.parse as up
    dep = d.get("depois") or {}
    qs = [dict(up.parse_qsl(up.urlparse(u).query)) for u in dep.get("pedidos")
          or []]
    cortes_cont = set(q.get("corte") for q, u in zip(qs, dep["pedidos"])
                      if u.startswith(u"/api/verseg/contornos"))
    cts = [q for q, u in zip(qs, dep["pedidos"])
           if u.startswith(u"/api/verseg/ct")]
    checar(u"a roda de um lado anda os DOIS (os dois pedem o corte 9)",
           dep.get("corte") == 9 and cortes_cont == {u"9"}, str(cortes_cont))
    checar(u"a janela é uma só: a TC pedida já vem em pulmão",
           dep.get("janela") == u"pulmao"
           and any(q.get("j") == u"pulmao" for q in cts), str(cts)[:160])
    checar(u"trocar a janela não pede os contornos de novo",
           sum(1 for u in dep["pedidos"]
               if u.startswith(u"/api/verseg/contornos")) == 2,
           str(dep["pedidos"])[:200])
    pint = dep.get("pintados") or []
    checar(u"os dois lados pintam o MESMO corte e a MESMA imagem",
           bool(pint) and all(p["z"] == 9 for p in pint[-1:])
           and u"j=pulmao" in pint[-1]["url"], str(pint[-1:])[:160])
    checar(u"ligar/desligar num lado não mexe no outro",
           d["indep"]["lado1_igual"] and d["indep"]["lado0"] == {
               u"Lung_L_ai": 1}, str(d["indep"]))
    checar(u"copiar para o outro lado casa pelo nome sem sufixo",
           d["copiado"] == {u"heart_ts": 1}, str(d["copiado"]))
    checar(u"resposta de OUTRO arquivo não desenha, nem com o nome igual",
           d["defesa"] == 0, str(d["defesa"]))

    marca = u"rs: lado.arq"
    checar(u"a isca acha o ponto que ela troca", js.count(marca) == 1,
           str(js.count(marca)))
    isca = js.replace(marca, u"rs: CP.lados[0].arq")
    di, erro_i = _ver_rodar_harness(isca, node)
    checar(u"a isca executa", di is not None, erro_i or u"")
    if di is not None:
        checar(u"a ISCA (todo lado com o rs do lado 0) REPROVA a checagem",
               bool(_ver_cada_lado_o_seu(di)),
               u"a checagem passou com o defeito dentro")

    checar(u"nenhum pedido da tela leva o UID na URL",
           not _ver_urls_com_uid(d), u", ".join(_ver_urls_com_uid(d))[:200])
    marca_ct = u"cpQs({b: CP.serie.b || '', corte: z"
    checar(u"a isca do UID acha o ponto que ela troca",
           js.count(marca_ct) == 1, str(js.count(marca_ct)))
    du, erro_u = _ver_rodar_harness(
        js.replace(marca_ct, u"cpQs({b: CP.serie.b || '', uid: CP.serie.uid, "
                             u"corte: z"), node)
    checar(u"a ISCA (o UID de volta na URL do corte) REPROVA a checagem",
           du is not None and bool(_ver_urls_com_uid(du)), erro_u or u"")

    sem_bloco = (u"var document = {readyState: 'complete', "
                 u"getElementById: function(){ return null; }, "
                 u"addEventListener: function(){}, "
                 u"querySelector: function(){ return null; }, "
                 u"querySelectorAll: function(){ return []; }};\n"
                 u"var window = {addEventListener: function(){}};\n"
                 + js + u"\nconsole.log('JSON:' + JSON.stringify("
                 u"{montado: CP.montado}));\n")
    dl, erro_l = _rodar_node(sem_bloco, node)
    checar(u"o JS numa página sem o bloco carrega e fica inerte",
           dl is not None and dl.get("montado") is False, erro_l or str(dl))


def teste_onda_4b_a_casca():
    secao(u"onda 4b: links, foco preso, Voltar, aba Log, /ver e /config")
    import radai_ui as U
    import radai_todo as T
    import radai_view as VW
    import radai_sets as S
    import radai_panel as P
    import radai_cover as C
    casca = U.CASCA
    checar(u"o link sem cor própria leva a do tema (`:where(a)`, sem "
           u"especificidade)", u":where(a){color:var(--accent)}" in casca)
    js = U.JS if hasattr(U, u"JS") else u""
    if not js:
        js = io.open(_componentes.fonte("app/radai_ui.py"), encoding=u"utf-8").read()
    checar(u"o `uiPainel` prende o Tab no painel",
           u"window.uiPrenderFoco = function(caixa, e)" in js
           and u"if(e.key === 'Tab'){ window.uiPrenderFoco(v, e); return }" in js)
    checar(u"  e o foco ENTRA no painel (de novo, depois da transição), e o Tab "
           u"de fora o traz para dentro",
           u"setTimeout(_pnlFocar, 80); setTimeout(_pnlFocar, 280);" in js
           and u"window.uiPrenderFoco(v.querySelector('.ui-pnl') || v, e);" in js)
    checar(u"o Voltar monta o MOLDE «Voltar para %s», com o nome da tela no "
           u"idioma dela", u"'Voltar para %s'.replace('%s', nomeAnt)" in js
           and u"window.radaiFrase(nomeAnt)" in js)
    checar(u"  (isca) a concatenação de antes não está mais lá",
           u"var rot = 'Voltar para ' + (ant.t || ant.u);" not in js)
    tj = io.open(_componentes.fonte("app/radai_todo.py"), encoding=u"utf-8").read()
    checar(u"a aba Log com o ponto aceso se chama «Log — erro novo»",
           u"ab.setAttribute('aria-label', 'Log — erro novo')" in tj)
    checar(u"e o ponto de vida do vigia tem nome (não é só cor)",
           u"pt.setAttribute('role', 'img')" in tj
           and u"o vigia parou com erro" in tj)
    vj = io.open(_componentes.fonte("app/radai_view.py"), encoding=u"utf-8").read()
    checar(u"o /ver reescreve a mensagem por `uiTexto` e a contagem é molde",
           u"if(window.uiTexto) window.uiTexto(e, t || '')" in vj
           and u"'%s série(s) com contorno'.replace('%s', VR.series.length)"
           in vj)
    ts = [c for c in S.CONJUNTOS if c.get(u"cod") == u"ts"]
    aj = (ts[0].get(u"ajuda") or u"") if ts else u""
    checar(u"a ajuda do TS cru (o `title` do chip) não cita o Calibrador",
           bool(aj) and u"Calibrador" not in aj, aj[:80])
    import radai_phrases as F
    tab = dict((F.normalizar(t[0]), t) for t in F.TABELA)
    k = F.normalizar(aj)
    checar(u"  e tem chave nos doze idiomas (o `title` só casa chave exata)",
           k in tab and all(tab[k][1:]))
    pag = P.PAGINA_CONFIG
    checar(u"o rodapé da /config não oferece o tutorial da v8.2",
           u'<a href="/onboarding"' not in pag)
    checar(u"a folha dos documentos não redefine `--ok` (o fundo do botão "
           u"primário)", u"--ok:#5BC57F" not in C.CSS_DOC
           and u"button.pri{color:var(--ok-txt,#fff)}" in C.CSS_DOC)


def _erro_cru_no_explorador(js):
    return js.count(u"'ERRO: '")


def teste_o_explorador_traduz_o_erro():
    secao(u"TEL-17: o explorador de pastas escreve o erro por chave, e o detalhe à parte")
    import radai_ui as U
    import radai_phrases as F
    fonte = io.open(U.__file__, encoding="utf-8").read()
    checar(u"nenhum «ERRO: » cru no explorador", _erro_cru_no_explorador(fonte) == 0,
           str(_erro_cru_no_explorador(fonte)))
    checar(u"  (isca) a forma velha e contada",
           _erro_cru_no_explorador(u"arv.textContent = 'ERRO: ' + e") == 1)
    d = F.construir()
    for f in (u"Não consegui listar as unidades.", u"Não consegui listar a pasta.",
              u"Não consegui marcar a pasta como favorita."):
        checar(u"  «%s» está no JS e tem as onze traduções" % f,
               (u"'%s'" % f) in fonte
               and all(d[c].get(F.normalizar(f)) for c in F.CODIGOS))


GLIFOS_TEL19 = (u"◧", u"◑", u"⌇", u"◎", u"◒", u"⇥")


def _sem_script(p):
    return re.sub(r"(?is)<script\b.*?</script>", u" ", p or u"")


def teste_tel19_os_icones_sao_svg():
    secao(u"TEL-19: os ícones da suíte são SVG, e nenhum glifo chega à tela")
    import radai_ui as U
    import radai_menu
    import radai_modules
    import radai_router
    sem_desenho = [g for g, n in U.GLIFOS.items() if u"<svg" not in U.icone(n)]
    checar(u"todo glifo conhecido tem um ícone SVG com nome",
           not sem_desenho, repr(sem_desenho))
    for g in GLIFOS_TEL19:
        checar(u"  o %s vira SVG" % g, u"<svg" in U.icone_de(g))
    checar(u"  e o nome do ícone também desenha (icone_de)",
           u"<svg" in U.icone_de(u"cubo") and U.icone_de(u"cubo") == U.icone(u"cubo"))
    checar(u"  e texto que não é ícone volta como veio",
           U.icone_de(u"x") == u"x")
    paginas = [(u"trilho", radai_menu.html(u"")),
               (u"porta", radai_router.montar_porta())]
    for k in radai_modules.MODULOS:
        paginas.append((u"mini-página " + k, radai_modules.pagina(k)))
    for g in GLIFOS_TEL19:
        paginas.append((u"cabeça com " + g,
                        U.cabeca_de_funcao(g, u"Ferramenta", u"frase")))
    com_glifo = [(n, g) for n, p in paginas for g in GLIFOS_TEL19
                 if g in _sem_script(p)]
    checar(u"nenhuma tela da suíte mostra os glifos do TEL-19",
           not com_glifo, repr(com_glifo[:4]))
    registros = []
    for k, m in radai_modules.MODULOS.items():
        registros.append(m.get(u"icone"))
    for k, fs in radai_modules.FERRAMENTAS.items():
        registros.extend(f[1] for f in fs)
    registros.extend(i[2] for i in radai_menu.ITENS)
    fora = [r for r in registros if r not in U._TRACOS]
    checar(u"os registros (módulos, ferramentas, trilho) guardam o NOME "
           u"do ícone, e não o glifo", not fora, repr(fora[:6]))
    guardado = dict(U.GLIFOS)
    U.GLIFOS.clear()
    try:
        isca = U.cabeca_de_funcao(u"◧", u"Ferramenta", u"frase")
    finally:
        U.GLIFOS.update(guardado)
    checar(u"  (isca) sem a tradução de glifo, o ◧ chega à tela e é acusado",
           u"◧" in _sem_script(isca))


_BASE_C3 = u"http://casca.radai.test"

_PAGINA_C3 = u"""<!doctype html><html><head><meta charset="utf-8">
<title>c3</title></head><body style="margin:0">
<main style="padding:20px">
<label><input type="checkbox" id="ck"> marcar</label>
<label><input type="checkbox" id="ck_sw" role="switch"> chave</label>
<button type="button" class="ui-bt pri" id="verde">Salvar</button>
<button type="button" class="ui-bt pri" id="verde_off" disabled>Salvar</button>
<div id="quadro" style="width:200px;height:120px;position:relative"></div>
<div style="height:2400px"></div>
<input type="text" id="campo" placeholder="obrigatório">
</main></body></html>"""


def _medir_c3(nav, pagina, reduzir=False, minimo=None):
    from urllib.parse import urlsplit
    ctx = nav.new_context(viewport={"width": 900, "height": 600},
                          reduced_motion=u"reduce" if reduzir else u"no-preference")
    ctx.route(_BASE_C3 + u"/**", lambda r: r.fulfill(
        status=200, content_type=u"text/html; charset=utf-8", body=pagina)
        if urlsplit(r.request.url).path == u"/" else r.fulfill(status=404, body=u""))
    pg = ctx.new_page()
    m = {}
    try:
        pg.goto(_BASE_C3 + u"/")
        if minimo is not None:
            pg.evaluate(u"window.UI_CARREGANDO_MINIMO_MS = %d" % minimo)
        m.update(pg.evaluate(u"""(function(){
          var c = document.getElementById('ck'), s = document.getElementById('ck_sw');
          var cs = getComputedStyle(c), antes = getComputedStyle(c, '::before');
          var v = document.getElementById('verde'), vo = document.getElementById('verde_off');
          return {aparencia: cs.appearance || cs.webkitAppearance,
                  caixa_dur: cs.transitionDuration, caixa_curva: cs.transitionTimingFunction,
                  traco_dur: antes.transitionDuration, traco_curva: antes.transitionTimingFunction,
                  traco_antes: antes.clipPath,
                  chave_nativa: (getComputedStyle(s).appearance || '') !== 'none',
                  brilho: getComputedStyle(v, '::after').animationName,
                  brilho_display: getComputedStyle(v, '::after').display,
                  brilho_off: getComputedStyle(vo, '::after').content};
        })()"""))
        pg.click(u"#ck")
        pg.wait_for_timeout(450)
        m["traco_depois"] = pg.evaluate(
            u"getComputedStyle(document.getElementById('ck'), '::before').clipPath")
        m["tremeu"] = pg.evaluate(u"""(function(){
          var e = document.getElementById('campo');
          window.uiTremer(e);
          return {classe: e.classList.contains('ui-treme'),
                  dur: getComputedStyle(e).animationDuration,
                  nome: getComputedStyle(e).animationName,
                  foco: document.activeElement === e};
        })()""")
        pg.wait_for_timeout(900)
        m["visivel_depois_do_tremor"] = pg.evaluate(u"""(function(){
          var r = document.getElementById('campo').getBoundingClientRect();
          return r.top >= 0 && r.bottom <= innerHeight;
        })()""")
        pg.evaluate(u"""(function(){
          var q = document.getElementById('quadro');
          window.uiCarregando(q, true, 'abrindo a série…');
          setTimeout(function(){ window.uiCarregando(q, false) }, 100);
        })()""")
        pg.wait_for_timeout(1000)
        m["carregando_1s"] = pg.evaluate(
            u"!!document.querySelector('#quadro .ui-organico.vis')")
        pg.wait_for_timeout(1700)
        m["carregando_2s7"] = pg.evaluate(
            u"!!document.querySelector('#quadro .ui-organico')")
        m["ocupado_2s7"] = pg.evaluate(
            u"document.getElementById('quadro').getAttribute('aria-busy')")
    finally:
        ctx.close()
    return m


def teste_c3_as_animacoes_da_casca_no_navegador():
    secao(u"C3: check, reflexo do verde, tremor e carregamento de 2 s, no navegador")
    import radai_ui as U
    folha = U.folha()
    checar(u"a folha tem o check com os tempos do contrato (150 ms e 350 ms)",
           u"150ms cubic-bezier(.22,1,.36,1)" in folha
           and u"clip-path 350ms cubic-bezier(.22,1,.36,1)" in folha)
    checar(u"  o tremor é 0, 6, -6, 4, 0 px em 280 ms",
           u"uiTreme 280ms" in folha and u"25%{transform:translateX(6px)}" in folha
           and u"50%{transform:translateX(-6px)}" in folha
           and u"75%{transform:translateX(4px)}" in folha)
    checar(u"  e o brilho do verde mora na casca",
           u"@keyframes uiBrilhoVerde" in folha)
    checar(u"o JS da casca tem o ajudante de tremor e o mínimo do carregamento",
           u"window.uiTremer = function" in U.COMPONENTES_JS
           and u"window.UI_CARREGANDO_MINIMO_MS = 2000;" in U.COMPONENTES_JS)
    exe = _chromium()
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        sync_playwright = None
    if not exe or sync_playwright is None:
        print(u"    PULADO o navegador: sem Playwright ou sem Chromium")
        return
    pagina = U.aplicar(_PAGINA_C3)
    with sync_playwright() as pw:
        nav = pw.chromium.launch(executable_path=exe, headless=True)
        try:
            m = _medir_c3(nav, pagina)
            curva = u"cubic-bezier(0.22, 1, 0.36, 1)"
            checar(u"a caixa de marcar é desenhada pela casca (appearance none)",
                   m.get(u"aparencia") == u"none", repr(m))
            checar(u"  a caixa anima em 150 ms, e o traço em 350 ms, na curva do contrato",
                   u"0.15s" in (m.get(u"caixa_dur") or u"")
                   and curva in (m.get(u"caixa_curva") or u"")
                   and m.get(u"traco_dur") == u"0.35s"
                   and m.get(u"traco_curva") == curva, repr(m))
            checar(u"  o traço nasce escondido e aparece ao marcar",
                   u"100%" in (m.get(u"traco_antes") or u"")
                   and u"100%" not in (m.get(u"traco_depois") or u"x100%"), repr(m))
            checar(u"  e a chave (role=switch) continua com a roupa dela",
                   m.get(u"chave_nativa") is True, repr(m))
            checar(u"o botão verde tem o brilho, e o desligado não",
                   m.get(u"brilho") == u"uiBrilhoVerde"
                   and m.get(u"brilho_off") in (u"none", u"normal"), repr(m))
            t = m.get(u"tremeu") or {}
            checar(u"o tremor treme 280 ms e dá o foco ao campo",
                   t.get(u"classe") and t.get(u"dur") == u"0.28s"
                   and t.get(u"nome") == u"uiTreme" and t.get(u"foco"), repr(t))
            checar(u"  e rola a tela até ele",
                   m.get(u"visivel_depois_do_tremor") is True, repr(m))
            checar(u"o carregamento desligado com 100 ms continua na tela em 1 s",
                   m.get(u"carregando_1s") is True, repr(m))
            checar(u"  e sai depois dos 2 s, soltando o aria-busy",
                   m.get(u"carregando_2s7") is False and m.get(u"ocupado_2s7") is None,
                   repr(m))
            mi = _medir_c3(nav, pagina, minimo=0)
            checar(u"  (isca) sem o mínimo, o carregamento já saiu em 1 s",
                   mi.get(u"carregando_1s") is False, repr(mi))
            mr = _medir_c3(nav, pagina, reduzir=True)
            checar(u"movimento reduzido: a caixa e o traço sem transição",
                   mr.get(u"caixa_dur") in (u"0s", u"0s, 0s, 0s")
                   and mr.get(u"traco_dur") == u"0s", repr(mr))
            checar(u"  o verde sem brilho",
                   mr.get(u"brilho_display") == u"none", repr(mr))
            tr = mr.get(u"tremeu") or {}
            checar(u"  e o tremor não treme, mas dá o foco",
                   not tr.get(u"classe") and tr.get(u"foco"), repr(tr))
        finally:
            nav.close()


_BASE_TEMA = u"http://tema.radai.test"


def _seletor_do_tema():
    import radai_panel
    m = re.search(r'(?s)<select id="selTema".*?</select>', radai_panel.PAGINA_CONFIG)
    return m.group(0) if m else u""


def _pagina_do_tema(U, js_tema=None, tema_no_fim=False, fixo=False):
    corpo = (u'<script>window.__temaNoCorpo = document.documentElement'
             u'.getAttribute("data-tema");</script>'
             + _seletor_do_tema() + u'<p id="t">texto</p>')
    pagina = U.aplicar(u'<!doctype html><html%s><head><meta charset="utf-8">'
                       u'<title>tema</title></head><body>%s</body></html>'
                       % (u' data-tema-fixo="escuro"' if fixo else u"", corpo))
    if js_tema is not None:
        pagina = pagina.replace(U.TEMA_JS, js_tema)
    if tema_no_fim:
        pagina = (pagina.replace(U.TEMA_JS, u"")
                  .replace(u"</body>", U.TEMA_JS + u"</body>"))
    return pagina


def _servir_uma(ctx, base, pagina):
    from urllib.parse import urlsplit
    ctx.route(base + u"/**", lambda r: r.fulfill(
        status=200, content_type=u"text/html; charset=utf-8", body=pagina)
        if urlsplit(r.request.url).path == u"/" else r.fulfill(status=404, body=u""))


_JS_TEMA_LIDO = (u"[document.documentElement.getAttribute('data-tema'),"
                 u" document.documentElement.getAttribute('data-tema-escolha'),"
                 u" window.__temaNoCorpo]")


def _medir_tema(nav, pagina):
    ctx = nav.new_context(viewport={"width": 900, "height": 500}, color_scheme=u"dark")
    _servir_uma(ctx, _BASE_TEMA, pagina)
    erros = []
    m = {}
    try:
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: erros.append(str(e)[:120]))
        pg.goto(_BASE_TEMA + u"/")
        pg.wait_for_timeout(250)
        m["inicio"] = pg.evaluate(_JS_TEMA_LIDO)
        pg.evaluate(u"window.__avisos = 0; window.addEventListener('radai-tema',"
                    u" function(){ window.__avisos++ }); true")
        pg.emulate_media(color_scheme=u"light")
        pg.wait_for_timeout(150)
        m["sistema_claro"] = pg.evaluate(_JS_TEMA_LIDO)
        m["avisos"] = pg.evaluate(u"window.__avisos")
        m["botoes"] = pg.evaluate(
            u"Array.prototype.map.call(document.querySelectorAll('.ui-seg [role=radio]'),"
            u" function(b){ return [b.getAttribute('data-v'), b.getAttribute('aria-checked'),"
            u" !!b.querySelector('svg.ui-ic')] })")
        m["grupo"] = pg.evaluate(
            u"(function(){ var g = document.querySelector('.ui-seg');"
            u" return g ? [g.getAttribute('role'), g.getAttribute('aria-label')] : null })()")
        if m["botoes"]:
            pg.click(u".ui-seg button[data-v='escuro']")
            pg.wait_for_timeout(150)
        m["escolheu"] = pg.evaluate(_JS_TEMA_LIDO) + [
            pg.evaluate(u"localStorage.getItem('radai_tema')")]
        pg2 = ctx.new_page()
        pg2.goto(_BASE_TEMA + u"/")
        pg2.wait_for_timeout(200)
        m["outra_aba"] = pg2.evaluate(_JS_TEMA_LIDO)
        pg.reload()
        pg.wait_for_timeout(250)
        m["recarregou"] = pg.evaluate(_JS_TEMA_LIDO)
        pg.emulate_media(color_scheme=u"dark")
        pg.wait_for_timeout(100)
        pg.emulate_media(color_scheme=u"light")
        pg.wait_for_timeout(150)
        m["fixa_nao_segue"] = pg.evaluate(_JS_TEMA_LIDO)
        if m["botoes"]:
            pg.focus(u".ui-seg button[aria-checked='true']")
            pg.keyboard.press(u"ArrowRight")
            pg.wait_for_timeout(150)
        m["seta"] = pg.evaluate(_JS_TEMA_LIDO) + [pg.evaluate(
            u"document.activeElement && document.activeElement.getAttribute('data-v')")]
        if m["botoes"]:
            pg.click(u".ui-seg button[data-v='claro']")
            pg.wait_for_timeout(250)
        m["outra_aba_seguiu"] = pg2.evaluate(_JS_TEMA_LIDO)
        pg3 = ctx.new_page()
        pg3.on("pageerror", lambda e: erros.append(str(e)[:120]))
        pg3.set_content(pagina)
        pg3.wait_for_timeout(250)
        m["sem_storage_lanca"] = pg3.evaluate(
            u"(function(){ try{ localStorage.getItem('x'); return false }"
            u"catch(e){ return true } })()")
        m["sem_storage"] = pg3.evaluate(_JS_TEMA_LIDO)
        pg3.evaluate(u"uiTema('claro'); true")
        m["sem_storage_escolheu"] = pg3.evaluate(_JS_TEMA_LIDO)
    finally:
        ctx.close()
    m["erros"] = erros
    return m


def teste_o_tema_tem_tres_escolhas():
    secao(u"tema: claro, escuro ou o do sistema, antes do primeiro desenho")
    import radai_ui as U
    import radai_porta
    checar(u"as três escolhas e o padrão (sem escolha, vale o sistema)",
           U.TEMAS == (u"claro", u"escuro", u"sistema") and U.TEMA_PADRAO == u"sistema")
    pg = U.aplicar(u"<html><head><meta charset='utf-8'></head><body><p>x</p></body></html>")
    i_tema, i_css = pg.find(U.MARCA_TEMA), pg.find(U.MARCA_CSS)
    checar(u"o motor do tema vai no <head>, antes da folha e do corpo",
           0 <= i_tema < i_css < pg.find(u"</head>") < pg.find(u"<body>"),
           u"%d %d" % (i_tema, i_css))
    checar(u"  e o JS da casca não tem mais o uiTema antigo (que caía no escuro)",
           u"window.uiTema" not in U.JS and u"'escuro' }" not in U.JS)
    t = U.TEMA_JS
    checar(u"o sistema é lido por prefers-color-scheme e seguido ao vivo",
           u"prefers-color-scheme: light" in t and u"addEventListener('change'" in t
           and u"addListener(" in t)
    checar(u"  a escolha vale para as outras abas (o evento storage)",
           u"'storage'" in t)
    checar(u"  e toda leitura e gravação do localStorage está em try/catch",
           t.count(u"localStorage.") == 2
           and len(re.findall(r"try\{ (?:var v = )?localStorage\.", t)) == 2)
    sel = _seletor_do_tema()
    checar(u"a Configuração tem o seletor de três posições, com sol, lua e monitor",
           u"data-ui-seg" in sel and u"data-ui-tema" in sel
           and u"window.uiSeletorDeTema = function" in U.COMPONENTES_JS and all(
               (u'value="%s" data-ui-icone="%s"' % (v, i)) in sel
               for v, i in ((u"claro", u"sol"), (u"escuro", u"lua"),
                            (u"sistema", u"monitor"))), sel[:120])
    checar(u"  e os três ícones são SVG da casca",
           all(u"<svg" in U.icone(n) for n in (u"sol", u"lua", u"monitor"))
           and all(n in U.ICONES_DOS_COMPONENTES for n in (u"sol", u"lua", u"monitor")))
    checar(u"a porta (a arte é noturna) se declara escura nos dois temas",
           u'data-tema-fixo="escuro"' in radai_porta.PAGINA)
    for chave in (u"--img-fundo", u"--img-texto", u"--img-texto-fraco"):
        valores = re.findall(r"%s:([^;]+);" % re.escape(chave), U.TOKENS)
        checar(u"a área de imagem fica escura nos dois temas (`%s` igual)" % chave,
               len(valores) == 2 and valores[0] == valores[1], repr(valores))

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
            m = _medir_tema(nav, _pagina_do_tema(U))
            checar(u"[navegador] sem escolha, com o sistema escuro: escuro, já no "
                   u"primeiro script do corpo", m.get("inicio") == [u"escuro", u"sistema",
                                                                    u"escuro"], repr(m.get("inicio")))
            checar(u"  o sistema muda para claro e a tela acompanha, sem recarregar",
                   m.get("sistema_claro", [None])[:2] == [u"claro", u"sistema"]
                   and (m.get("avisos") or 0) >= 1, repr(m.get("sistema_claro")))
            checar(u"  o controle é um radiogroup com três rádios, cada um com ícone",
                   (m.get("grupo") or [None])[0] == u"radiogroup"
                   and [b[0] for b in m.get("botoes") or []] == [u"claro", u"escuro", u"sistema"]
                   and all(b[2] for b in m.get("botoes") or []), repr(m.get("botoes")))
            checar(u"  e marca o Sistema enquanto nada foi escolhido",
                   [b[1] for b in m.get("botoes") or []] == [u"false", u"false", u"true"],
                   repr(m.get("botoes")))
            checar(u"escolher Escuro grava no navegador e pinta na hora",
                   m.get("escolheu") == [u"escuro", u"escuro", u"escuro", u"escuro"],
                   repr(m.get("escolheu")))
            checar(u"  outra tela aberta depois já nasce escura, com o sistema claro",
                   (m.get("outra_aba") or [None])[0] == u"escuro"
                   and (m.get("outra_aba") or [None] * 3)[2] == u"escuro", repr(m.get("outra_aba")))
            checar(u"  recarregar mantém a escolha antes do primeiro desenho",
                   m.get("recarregou") == [u"escuro", u"escuro", u"escuro"],
                   repr(m.get("recarregou")))
            checar(u"  a escolha fixa não segue o sistema",
                   (m.get("fixa_nao_segue") or [None])[0] == u"escuro", repr(m.get("fixa_nao_segue")))
            checar(u"a seta leva de Escuro a Sistema, com o foco, e o sistema claro vale",
                   m.get("seta") == [u"claro", u"sistema", u"escuro", u"sistema"],
                   repr(m.get("seta")))
            checar(u"a escolha numa aba chega à outra aberta, sem recarregar",
                   (m.get("outra_aba_seguiu") or [None])[0:2] == [u"claro", u"claro"],
                   repr(m.get("outra_aba_seguiu")))
            checar(u"sem localStorage (a leitura lança), a tela abre pelo sistema",
                   m.get("sem_storage_lanca") is True
                   and (m.get("sem_storage") or [None])[0:2] == [u"escuro", u"sistema"],
                   repr(m.get("sem_storage")))
            checar(u"  e a escolha vale na memória da tela, sem erro de JS",
                   (m.get("sem_storage_escolheu") or [None])[0:2] == [u"claro", u"claro"]
                   and not m.get("erros"), repr([m.get("sem_storage_escolheu"), m.get("erros")]))
            mf = _medir_tema(nav, _pagina_do_tema(U, fixo=True))
            checar(u"a tela que se declara escura fica escura com o sistema e a escolha claros",
                   (mf.get("sistema_claro") or [None])[0] == u"escuro"
                   and (mf.get("outra_aba_seguiu") or [None])[0] == u"escuro",
                   repr([mf.get("sistema_claro"), mf.get("outra_aba_seguiu")]))
            i1 = _medir_tema(nav, _pagina_do_tema(U, js_tema=U.TEMA_JS.replace(
                u"guardado : 'sistema'", u"guardado : 'escuro'")))
            checar(u"  (isca) o padrão antigo (escuro) não segue o sistema claro",
                   (i1.get("sistema_claro") or [None])[0] == u"escuro", repr(i1.get("sistema_claro")))
            i2 = _medir_tema(nav, _pagina_do_tema(U, js_tema=U.TEMA_JS.replace(
                u"mq.addEventListener('change', seguirOSistema)", u"0")))
            checar(u"  (isca) sem o ouvinte, o sistema muda e a tela não",
                   (i2.get("sistema_claro") or [None])[0] == u"escuro", repr(i2.get("sistema_claro")))
            i3 = _medir_tema(nav, _pagina_do_tema(U, tema_no_fim=True))
            checar(u"  (isca) o tema aplicado no fim do corpo chega depois do primeiro script",
                   (i3.get("inicio") or [None] * 3)[2] is None, repr(i3.get("inicio")))
            i4 = _medir_tema(nav, _pagina_do_tema(U, js_tema=U.TEMA_JS.replace(
                u"try{ localStorage.setItem(CHAVE, t) }catch(e){}", u"")))
            checar(u"  (isca) sem gravar, recarregar volta ao sistema",
                   (i4.get("recarregou") or [None])[0] == u"claro", repr(i4.get("recarregou")))
        finally:
            nav.close()


_PAGINA_SEG = u"""<!doctype html><html><head><meta charset="utf-8">
<title>seg</title></head><body style="margin:0">
<main style="padding:40px">
<select id="m" data-ui-seg="embaralhar" aria-label="modo de teste">
<option value="fast" data-ui-balao="Explica o FAST.">FAST</option>
<option value="auto" selected data-ui-balao="Explica o AUTO.">AUTO</option>
<option value="perso" data-ui-balao="Explica o PERSONALIZADO.">PERSONALIZADO</option>
</select>
<p style="height:40px"></p>
<select id="off" data-ui-seg disabled aria-label="apagado">
<option value="a" selected>Um</option><option value="b">Dois</option></select>
<p style="height:40px"></p>
<select id="volta" data-ui-seg="embaralhar" aria-label="volta">
<option value="x" selected>XIS</option><option value="y">IPSILON</option></select>
</main>
<script>
window.__mudou = 0;
document.getElementById('m').addEventListener('change', function(){ window.__mudou++ });
document.getElementById('volta').addEventListener('change', function(ev){
 ev.target.value = 'x';
 var cx = ev.target.previousElementSibling; if(cx && cx._uiPintar) cx._uiPintar();
});
</script></body></html>"""

_JS_SEG_LIDO = u"""(function(id){
 var s = document.getElementById(id), g = s.previousElementSibling;
 var bs = g.querySelectorAll('[role=radio]'), ind = g.querySelector('.ui-seg-ind');
 var marcado = g.querySelector('[aria-checked=true]');
 return {grupo: [g.getAttribute('role'), g.getAttribute('aria-label')],
   v: s.value, marcado: marcado ? marcado.getAttribute('data-v') : null,
   tab: Array.prototype.map.call(bs, function(b){ return b.tabIndex }),
   desab: Array.prototype.map.call(bs, function(b){ return b.disabled }),
   desc: Array.prototype.map.call(bs, function(b){
     var d = document.getElementById(b.getAttribute('aria-describedby') || '-');
     return d ? d.textContent : null }),
   ind_x: ind.style.transform, ind_w: ind.style.width,
   alvo_x: marcado ? 'translateX(' + marcado.offsetLeft + 'px)' : null,
   alvo_w: marcado ? marcado.offsetWidth + 'px' : null,
   trans: getComputedStyle(ind).transitionDuration + '|' + getComputedStyle(ind).transitionTimingFunction,
   foco: document.activeElement && document.activeElement.getAttribute('data-v')};
})(%s)"""


def _medir_seg(nav, pagina, reduzir=False):
    ctx = nav.new_context(viewport={"width": 900, "height": 600},
                          reduced_motion=u"reduce" if reduzir else u"no-preference")
    _servir_uma(ctx, _BASE_TEMA, pagina)
    m = {}
    erros = []
    try:
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: erros.append(str(e)[:120]))
        pg.goto(_BASE_TEMA + u"/")
        pg.wait_for_timeout(300)
        m["ini"] = pg.evaluate(_JS_SEG_LIDO % u"'m'")
        pg.click(u".ui-seg button[data-v='fast']")
        pg.wait_for_timeout(60)
        m["mexendo"] = pg.evaluate(
            u"(function(){ var b = document.querySelector(\".ui-seg button[data-v='fast']\");"
            u" return [b.querySelector('.ui-seg-rot').classList.contains('mexendo'),"
            u" b.querySelector('.ui-seg-mex').textContent,"
            u" b.querySelector('.ui-seg-txt').textContent] })()")
        pg.wait_for_timeout(450)
        m["clicou"] = pg.evaluate(_JS_SEG_LIDO % u"'m'")
        m["assentou"] = pg.evaluate(
            u"(function(){ var b = document.querySelector(\".ui-seg button[data-v='fast']\");"
            u" return [b.querySelector('.ui-seg-rot').classList.contains('mexendo'),"
            u" b.querySelector('.ui-seg-mex').textContent] })()")
        m["mudou"] = pg.evaluate(u"window.__mudou")
        pg.wait_for_timeout(600)
        m["balao_clique"] = pg.evaluate(
            u"(function(){ var b = document.getElementById('ui-seg-balao');"
            u" return b ? [b.classList.contains('on'), b.textContent, b.getAttribute('aria-hidden')] : null })()")
        pg.keyboard.press(u"ArrowLeft")
        pg.wait_for_timeout(100)
        m["seta_esq"] = pg.evaluate(_JS_SEG_LIDO % u"'m'")
        pg.keyboard.press(u"Home")
        pg.wait_for_timeout(100)
        m["home"] = pg.evaluate(_JS_SEG_LIDO % u"'m'")
        pg.keyboard.press(u"ArrowRight")
        pg.wait_for_timeout(100)
        m["seta_dir"] = pg.evaluate(_JS_SEG_LIDO % u"'m'")
        pg.keyboard.press(u"Escape")
        pg.mouse.move(5, 590)
        pg.wait_for_timeout(250)
        pg.hover(u".ui-seg button[data-v='perso']")
        pg.wait_for_timeout(700)
        m["balao_passou"] = pg.evaluate(
            u"(function(){ var b = document.getElementById('ui-seg-balao');"
            u" return b ? [b.classList.contains('on'), b.textContent] : null })()")
        m["off"] = pg.evaluate(_JS_SEG_LIDO % u"'off'")
        pg.evaluate(u"document.querySelector('#off').previousElementSibling"
                    u".querySelector(\"[data-v='b']\").click(); true")
        m["off_depois"] = pg.evaluate(_JS_SEG_LIDO % u"'off'")
        pg.evaluate(u"document.querySelector('#volta').previousElementSibling"
                    u".querySelector(\"[data-v='y']\").click(); true")
        pg.wait_for_timeout(60)
        m["volta"] = pg.evaluate(_JS_SEG_LIDO % u"'volta'")
        m["volta_mexeu"] = pg.evaluate(
            u"Array.prototype.some.call(document.querySelector('#volta').previousElementSibling"
            u".querySelectorAll('.ui-seg-rot'), function(r){ return r.classList.contains('mexendo') })")
    finally:
        ctx.close()
    m["erros"] = erros
    return m


def teste_o_seletor_segmentado():
    secao(u"uiSegmentado: o destaque desliza, o rótulo embaralha, o balão explica")
    import radai_ui as U
    js = U.COMPONENTES_JS
    folha = U.folha()
    checar(u"a casca tem `window.uiSegmentado` e a costura de `select[data-ui-seg]`",
           u"window.uiSegmentado = function" in js and u"select[data-ui-seg]" in js
           and u"window.uiSegmentadoTodos" in js)
    checar(u"  o destaque desliza em 300 ms na curva (0.22, 1, 0.36, 1)",
           u"transition:transform .3s cubic-bezier(.22,1,.36,1),width .3s cubic-bezier(.22,1,.36,1)"
           in folha)
    checar(u"  o embaralhar dura 250 ms e olha o movimento reduzido",
           u"window.UI_SEG_EMBARALHAR_MS || 250" in js and u"segCalmo()" in js)
    checar(u"  e o destaque é a cor de acento (azul) da casca",
           u"background:var(--accent);" in folha[folha.find(u".ui-seg-ind{"):
                                                folha.find(u".ui-seg-ind{") + 300])
    h = U.segmentado(u"zz", [(u"a", u"Um", {u"icone": u"sol", u"balao": u"diz <um>"}),
                              (u"b", u"Dois")], valor=u"b", rotulo=u"grupo", embaralhar=True)
    checar(u"o helper Python monta o select que a casca costura",
           h.startswith(u'<select id="zz" data-ui-seg="embaralhar" aria-label="grupo">')
           and u'data-ui-icone="sol"' in h and u'data-ui-balao="diz &lt;um&gt;"' in h
           and u'<option value="b" selected>Dois</option>' in h, h)
    exe = _chromium()
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        sync_playwright = None
    if not exe or sync_playwright is None:
        print(u"    PULADO o navegador: sem Playwright ou sem Chromium")
        return
    pagina = U.aplicar(_PAGINA_SEG)
    with sync_playwright() as pw:
        nav = pw.chromium.launch(executable_path=exe, headless=True)
        try:
            m = _medir_seg(nav, pagina)
            ini = m.get("ini") or {}
            checar(u"[navegador] radiogroup com nome, o marcado é o do select, e só ele "
                   u"entra no Tab", ini.get("grupo") == [u"radiogroup", u"modo de teste"]
                   and ini.get("marcado") == u"auto" and ini.get("tab") == [-1, 0, -1], repr(ini))
            checar(u"  cada opção é descrita pelo texto do balão (aria-describedby)",
                   ini.get("desc") == [u"Explica o FAST.", u"Explica o AUTO.",
                                       u"Explica o PERSONALIZADO."], repr(ini.get("desc")))
            checar(u"  o destaque desliza 0,3 s na curva do pedido",
                   ini.get("trans") == u"0.3s, 0.3s|cubic-bezier(0.22, 1, 0.36, 1), "
                   u"cubic-bezier(0.22, 1, 0.36, 1)", repr(ini.get("trans")))
            mx = m.get("mexendo") or [None, u"", u""]
            checar(u"clicar embaralha o rótulo por um instante (as letras do próprio rótulo)",
                   mx[0] is True and len(mx[1]) == 4 and set(mx[1]) <= set(u"FAST")
                   and mx[2] == u"FAST", repr(mx))
            c = m.get("clicou") or {}
            checar(u"  e assenta: select, rádio marcado, Tab e destaque na opção nova",
                   c.get("v") == u"fast" and c.get("marcado") == u"fast"
                   and c.get("tab") == [0, -1, -1] and c.get("ind_x") == c.get("alvo_x")
                   and c.get("ind_w") == c.get("alvo_w")
                   and (m.get("assentou") or [True])[0] is False
                   and (m.get("assentou") or [0, u"x"])[1] == u"", repr([c, m.get("assentou")]))
            checar(u"  o change do select dispara uma vez (o comportamento de quem o usa "
                   u"não muda)", m.get("mudou") == 1, repr(m.get("mudou")))
            bc = m.get("balao_clique") or [False, u"", None]
            checar(u"o balão explica a opção focada, e o leitor de tela lê pela descrição",
                   bc[0] is True and u"Explica o FAST." in bc[1] and bc[2] == u"true", repr(bc))
            checar(u"a seta para a esquerda dá a volta (FAST → PERSONALIZADO), com o foco",
                   (m.get("seta_esq") or {}).get("marcado") == u"perso"
                   and (m.get("seta_esq") or {}).get("foco") == u"perso", repr(m.get("seta_esq")))
            checar(u"  Home vai ao primeiro, e a seta para a direita anda um",
                   (m.get("home") or {}).get("marcado") == u"fast"
                   and (m.get("seta_dir") or {}).get("marcado") == u"auto",
                   repr([m.get("home"), m.get("seta_dir")]))
            bp = m.get("balao_passou") or [False, u""]
            checar(u"passar o mouse mostra o balão daquela opção",
                   bp[0] is True and u"Explica o PERSONALIZADO." in bp[1], repr(bp))
            off, offd = m.get("off") or {}, m.get("off_depois") or {}
            checar(u"o select desabilitado deixa os rádios desabilitados, e o clique não muda",
                   off.get("desab") == [True, True] and offd.get("v") == u"a"
                   and off.get("tab") == [-1, -1], repr([off, offd]))
            vt = m.get("volta") or {}
            checar(u"quem desfaz a escolha no change é obedecido, sem embaralhar",
                   vt.get("v") == u"x" and vt.get("marcado") == u"x"
                   and m.get("volta_mexeu") is False, repr([vt, m.get("volta_mexeu")]))
            checar(u"  e nenhum erro de JS", not m.get("erros"), repr(m.get("erros")))
            mr = _medir_seg(nav, pagina, reduzir=True)
            checar(u"movimento reduzido: o destaque salta, sem transição",
                   (mr.get("ini") or {}).get("trans", u"").startswith(u"0s"), repr(mr.get("ini")))
            checar(u"  e o rótulo não embaralha",
                   (mr.get("mexendo") or [True])[0] is False, repr(mr.get("mexendo")))
            i1 = _medir_seg(nav, pagina.replace(u"if(mexe) segEmbaralhar(bt);", u""))
            checar(u"  (isca) sem a chamada, o clique não embaralha",
                   (i1.get("mexendo") or [True])[0] is False, repr(i1.get("mexendo")))
            i2 = _medir_seg(nav, pagina.replace(
                u"if(!rot || !txt || !mex || segCalmo()) return false;",
                u"if(!rot || !txt || !mex) return false;"), reduzir=True)
            checar(u"  (isca) sem olhar o movimento reduzido, ele embaralha",
                   (i2.get("mexendo") or [False])[0] is True, repr(i2.get("mexendo")))
            i3 = _medir_seg(nav, pagina.replace(u"else if(k === 'ArrowLeft') passo = rtl ? 1 : -1;", u""))
            checar(u"  (isca) sem a seta para a esquerda, o marcado não anda",
                   (i3.get("seta_esq") or {}).get("marcado") == u"fast", repr(i3.get("seta_esq")))
        finally:
            nav.close()


def _pagina_ps(U, com_serie=False):
    abas = U.abas_de_serie(u"ps_abas", [(u"acervo", u"Acervo local", u"<p>tabela</p>"),
                                        (u"pasta", u"Aponte uma pasta",
                                         u'<input type="text" id="ps_campo">')],
                           padrao=u"pasta")
    return U.aplicar(
        u'<!doctype html><html><head><meta charset="utf-8"><title>ps</title></head>'
        u'<body style="margin:0"><main style="padding:40px">%s%s</main>%s'
        u'<script>window.COM_SERIE = %s;'
        u"document.addEventListener('DOMContentLoaded', function(){"
        u" uiPopupSerie('ps_t', {sozinho: function(){ return !window.COM_SERIE }}) });"
        u'</script></body></html>'
        % (U.cartao_de_serie(u"cs_um", u"ps_t", u"Escolha a série", numero=u"1"),
           U.cartao_de_serie(u"cs_dois", u"ps_t", u"Carregar série", contexto=u"fixa"),
           U.popup_de_serie(u"ps_t", abas, sozinho=True),
           u"true" if com_serie else u"false"))


_JS_PS_LIDO = u"""(function(){
 var n = document.getElementById('ps_t'), f = n.querySelector('.ui-guias-faixa');
 var a = f.querySelector('.ui-guia'), m = n.closest('.ui-modal');
 return {aberto: !!n.closest('.ui-modal-veu.vis'), casa: n.parentNode.id,
         aba: (n.querySelector('.ui-guia[aria-selected="true"]') || {getAttribute: function(){ return null }}).getAttribute('data-guia'),
         just: getComputedStyle(f).justifyContent,
         esq: Math.round(a.getBoundingClientRect().left - f.getBoundingClientRect().left),
         origem: m ? m.style.transformOrigin : '',
         exp: document.getElementById('cs_um').getAttribute('aria-expanded')};
})()"""


def _medir_ps(nav, pagina):
    ctx = nav.new_context(viewport={"width": 1100, "height": 700})
    _servir_uma(ctx, _BASE_TEMA, pagina)
    m, erros = {}, []
    try:
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: erros.append(str(e)[:120]))
        pg.goto(_BASE_TEMA + u"/")
        pg.wait_for_timeout(400)
        m["ini"] = pg.evaluate(_JS_PS_LIDO)
        pg.keyboard.press(u"Escape")
        pg.wait_for_timeout(400)
        m["fechou"] = pg.evaluate(_JS_PS_LIDO)
        pg.click(u"#cs_dois")
        pg.wait_for_timeout(400)
        m["reabriu"] = pg.evaluate(_JS_PS_LIDO)
        m["ctx"] = pg.evaluate(u"uiPopupSerie('ps_t').contexto()")
        cx = pg.evaluate(u"(function(){ var r = document.getElementById('cs_um')"
                         u".getBoundingClientRect(); return [r.left + 30, r.top + r.height / 2] })()")
        pg.keyboard.press(u"Escape")
        pg.wait_for_timeout(40)
        pg.mouse.click(cx[0], cx[1])
        pg.wait_for_timeout(400)
        m["rapido"] = pg.evaluate(_JS_PS_LIDO)
        pg.evaluate(u"uiPopupSerie('ps_t').fechar(); uiCartaoRotulo('cs_um', '12/10/2026 · FANTOMA'); true")
        pg.wait_for_timeout(400)
        m["rotulo"] = pg.evaluate(
            u"[document.querySelector('#cs_um .ui-cartao-rot').textContent,"
            u" document.getElementById('cs_um').classList.contains('tem'),"
            u" document.querySelector('#cs_um .ui-cartao-rot [translate=no]') !== null]")
        m["fim"] = pg.evaluate(_JS_PS_LIDO)
    finally:
        ctx.close()
    m["erros"] = erros
    return m


def teste_o_popup_de_serie():
    secao(u"o popup de seleção de série da casca: abre sozinho, aba padrão, abas à esquerda, cartão")
    import radai_ui as U
    p = _pagina_ps(U)
    checar(u"a casa do popup nasce escondida, com o conteúdo marcado `data-ui-ps`",
           u'<div class="ui-ps-casa" id="ps_t_casa" hidden><div class="ui-ps" id="ps_t" '
           u'data-ui-ps' in p and u"data-sozinho" in p)
    checar(u"  as abas são as da casca, com a padrão escolhida por quem monta",
           u'class="ui-guias esq" id="ps_abas" data-ativa="pasta"' in p)
    checar(u"o cartão abre o popup que ele nomeia, e se anuncia como diálogo",
           u'id="cs_um" data-ui-ps-abre="ps_t" aria-haspopup="dialog"' in p
           and u'data-ui-ps-ctx="fixa"' in p)
    checar(u"  o número do passo no lugar do ícone, quando há",
           u'<span class="ui-cartao-ic" aria-hidden="true">1</span>' in p)
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
            m = _medir_ps(nav, p)
            ini = m.get("ini") or {}
            checar(u"[navegador] o popup abre sozinho ao carregar, na aba padrão",
                   ini.get("aberto") is True and ini.get("aba") == u"pasta", repr(ini))
            checar(u"  as abas alinhadas à esquerda",
                   ini.get("just") in (u"flex-start", u"start") and ini.get("esq", 99) <= 8,
                   repr(ini))
            checar(u"  ele cresce a partir do cartão (a origem da animação)",
                   bool(ini.get("origem")) and ini.get("exp") == u"true", repr(ini))
            fe = m.get("fechou") or {}
            checar(u"Esc fecha, e o conteúdo volta para a casa escondida",
                   fe.get("aberto") is False and fe.get("casa") == u"ps_t_casa"
                   and fe.get("exp") == u"false", repr(fe))
            re_ = m.get("reabriu") or {}
            checar(u"o cartão reabre o popup e diz de qual cartão veio (o contexto)",
                   re_.get("aberto") is True and m.get("ctx") == u"fixa", repr([re_, m.get("ctx")]))
            checar(u"  e reabre na hora, mesmo com o véu do popup ainda saindo",
                   (m.get("rapido") or {}).get("aberto") is True, repr(m.get("rapido")))
            i3 = _medir_ps(nav, p.replace(u"transition-duration:.16s;\n pointer-events:none}",
                                           u"transition-duration:.16s}"))
            checar(u"  (isca) com o véu que sai ainda pegando o clique, não reabre",
                   (i3.get("rapido") or {}).get("aberto") is False, repr(i3.get("rapido")))
            r = m.get("rotulo") or []
            checar(u"o cartão passa a dizer a série escolhida (fora da tradução do navegador)",
                   r[:1] == [u"12/10/2026 · FANTOMA"] and r[1:] == [True, True], repr(r))
            checar(u"  e nenhum erro de JS", not m.get("erros"), repr(m.get("erros")))
            c = _medir_ps(nav, _pagina_ps(U, com_serie=True)).get("ini") or {}
            checar(u"a tela que chegou com a série diz não, e o popup fica fechado",
                   c.get("aberto") is False, repr(c))
            i1 = _medir_ps(nav, p.replace(u"querySelectorAll('[data-ui-ps][data-sozinho]')",
                                           u"querySelectorAll('[data-nada]')")).get("ini") or {}
            checar(u"  (isca) sem a abertura da casca, ele não abre sozinho",
                   i1.get("aberto") is False, repr(i1))
            sem_esq = p.replace(u'class="ui-guias esq" id="ps_abas"',
                                u'class="ui-guias" id="ps_abas"')
            s2 = _medir_ps(nav, sem_esq).get("ini") or {}
            checar(u"  abas montadas sem `esquerda` também ficam à esquerda dentro do popup",
                   s2.get("esq", 99) <= 8, repr(s2))
            i2 = _medir_ps(nav, sem_esq.replace(
                u".ui-ps .ui-guias-faixa{justify-content:flex-start;",
                u".ui-ps .ui-guias-faixa{")).get("ini") or {}
            checar(u"  (isca) sem a regra do popup, elas voltam ao centro",
                   i2.get("esq", 0) > 8, repr(i2))
        finally:
            nav.close()


def _fantoma_no_acervo():
    import json as _json
    import radai_archive
    try:
        import pydicom
        from pydicom.dataset import FileDataset, FileMetaDataset
        from pydicom.uid import ExplicitVRLittleEndian, generate_uid
    except Exception:
        return None
    base = _tempfile.mkdtemp(prefix="radai_ac_ui_acervo_")
    pasta = os.path.join(base, u"FANTOMA_TABELA")
    os.makedirs(os.path.join(pasta, u"_RadAI"))
    uid = generate_uid()
    meta = FileMetaDataset()
    meta.MediaStorageSOPClassUID = u"1.2.840.10008.5.1.4.1.1.2"
    meta.MediaStorageSOPInstanceUID = generate_uid()
    meta.TransferSyntaxUID = ExplicitVRLittleEndian
    ds = FileDataset(os.path.join(pasta, u"CT_1.dcm"), {}, file_meta=meta,
                     preamble=b"\0" * 128)
    ds.SeriesInstanceUID = uid
    ds.PatientName = u"FANTOMA^TABELA"
    ds.PatientID = u"FANT0001"
    ds.Modality = u"CT"
    ds.SliceThickness = u"2.5"
    try:
        ds.save_as(os.path.join(pasta, u"CT_1.dcm"), enforce_file_format=True)
    except TypeError:
        ds.save_as(os.path.join(pasta, u"CT_1.dcm"), write_like_original=False)
    io.open(os.path.join(pasta, u"RS_RadAI_teste.dcm"), "wb").write(b"x")
    with io.open(os.path.join(pasta, u"_RadAI", uid + u".done.json"), "w",
                 encoding="utf-8") as f:
        _json.dump({"modo": "auto", "cortes": 97,
                    "tasks_ok": ["total_v3", "lung_vessels"]}, f)
    radai_archive.registrar_serie(uid, pasta, u"RS_RadAI_teste.dcm",
                                  date=u"20260102", pid=u"FANT0001",
                                  estruturas=5, secs=75)
    return pasta, uid, base


def teste_c2_a_tabela_do_acervo():
    secao(u"C2: a tabela do acervo, com bilhete no lugar do caminho")
    import json as _json
    import shutil
    import radai_tabela_acervo as TA
    import radai_thumbnail
    checar(u"as doze colunas do Ver segmentação, na ordem",
           TA.COLUNAS == (u"Data do exame", u"Paciente", u"ID", u"Modalidade",
                          u"Cortes", u"Espessura", u"Estruturas", u"Modo",
                          u"Tasks", u"Contornada em", u"Levou", u"Abrir"),
           repr(TA.COLUNAS))
    h = TA.html(u"tab<x>")
    checar(u"html() monta o contêiner marcado e escapa o id",
           u'data-ui-acervo' in h and u'id="tab&lt;x&gt;"' in h)
    f = _fantoma_no_acervo()
    if f is None:
        checar(u"pydicom disponível para o fantoma", False, u"PULADO")
        return
    pasta, uid, base = f
    try:
        from fastapi import FastAPI
        from starlette.testclient import TestClient
        app = FastAPI()
        TA.montar(app)
        metodos = dict((getattr(r, "path", u""), sorted(getattr(r, "methods", ()) or ()))
                       for r in app.routes)
        checar(u"as duas rotas são POST, e nenhuma é GET",
               metodos.get(TA.ROTA) == [u"POST"]
               and metodos.get(TA.ROTA_DETALHES) == [u"POST"], repr(metodos))
        c = TestClient(app)
        r = c.post(TA.ROTA, json={})
        d = r.json()
        linha = next((x for x in d.get(u"series") or [] if x.get(u"uid8") == uid[-8:]), None)
        checar(u"a lista traz a série do fantoma", bool(linha), r.text[:300])
        bruto = r.text
        checar(u"  sem caminho de paciente na resposta (nem a pasta, nem o UID inteiro)",
               u"FANTOMA_TABELA" not in bruto and u"pasta" not in (linha or {})
               and uid not in bruto, bruto[:300])
        checar(u"  com o bilhete opaco, o ID, a data, as estruturas e o tempo",
               linha and len(linha.get(u"bilhete") or u"") == 32
               and linha.get(u"pid") == u"FANT0001" and linha.get(u"date") == u"20260102"
               and linha.get(u"estruturas") == 5 and linha.get(u"secs") == 75,
               repr(linha))
        b = (linha or {}).get(u"bilhete") or u""
        checar(u"o servidor resolve o bilhete para a série",
               TA.resolver(b) == (pasta, uid), repr(TA.resolver(b)))
        estranho = radai_thumbnail.bilhete(base, uid)
        checar(u"  e recusa bilhete de pasta que não está no acervo",
               TA.resolver(estranho) == (None, None))
        dd = c.post(TA.ROTA_DETALHES, json={u"bilhetes": [b, estranho]}).json()
        it = (dd.get(u"itens") or [{}, {}])
        checar(u"os detalhes leem nome, modalidade, espessura, modo, cortes e tasks",
               it[0].get(u"nome") == u"FANTOMA TABELA" and it[0].get(u"modalidade") == u"CT"
               and it[0].get(u"espessura_mm") == 2.5 and it[0].get(u"modo") == u"auto"
               and it[0].get(u"cortes") == 97
               and it[0].get(u"tasks") == [u"total_v3", u"lung_vessels"], repr(it))
        checar(u"  e o bilhete estranho volta vazio, sem ler disco",
               it[1].get(u"nome") == u"" and it[1].get(u"tasks") == [], repr(it))
        _tabela_no_navegador({u"series": [linha], u"sumiram": 0}, dd)
    finally:
        shutil.rmtree(base, ignore_errors=True)


_PAGINA_C2 = u"""<!doctype html><html><head><meta charset="utf-8">
<title>c2</title></head><body style="margin:0"><main style="padding:20px;width:1400px">
@TABELA@
<p id="vazio_alvo"></p>
</main><script>
window.ABERTOS = [];
var T = uiTabelaAcervo('tab', {aoAbrir: function(l, i){ window.ABERTOS.push({l: l, i: i}) }});
</script></body></html>"""


def _tabela_no_navegador(lista, detalhes):
    import json as _json
    from urllib.parse import urlsplit
    import radai_tabela_acervo as TA
    import radai_ui as U
    exe = _chromium()
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        sync_playwright = None
    if not exe or sync_playwright is None:
        print(u"    PULADO o navegador: sem Playwright ou sem Chromium")
        return
    pagina = U.aplicar(_PAGINA_C2.replace(u"@TABELA@", TA.html(u"tab")))
    pedidos = []

    def atender(route):
        caminho = urlsplit(route.request.url).path
        pedidos.append((route.request.method, caminho))
        if caminho == u"/":
            route.fulfill(status=200, content_type=u"text/html; charset=utf-8", body=pagina)
        elif caminho == TA.ROTA:
            route.fulfill(status=200, content_type=u"application/json",
                          body=_json.dumps(lista))
        elif caminho == TA.ROTA_DETALHES:
            route.fulfill(status=200, content_type=u"application/json",
                          body=_json.dumps({u"itens": (detalhes.get(u"itens") or [])[:1]}))
        else:
            route.fulfill(status=404, body=u"")
    with sync_playwright() as pw:
        nav = pw.chromium.launch(executable_path=exe, headless=True)
        try:
            ctx = nav.new_context(viewport={"width": 1500, "height": 800})
            ctx.route(_BASE_C3 + u"/**", atender)
            pg = ctx.new_page()
            pg.goto(_BASE_C3 + u"/")
            pg.wait_for_function(
                u"(document.querySelector('#tab [data-c=\"nome\"]')||{}).textContent"
                u" === 'FANTOMA TABELA'", timeout=6000)
            m = pg.evaluate(u"""(function(){
              var ths = Array.prototype.map.call(document.querySelectorAll('#tab thead th'),
                function(t){ return t.textContent.trim() });
              var tr = document.querySelector('#tab tbody tr[data-i]');
              return {ths: ths, linhas: document.querySelectorAll('#tab tbody tr[data-i]').length,
                      modalidade: tr.querySelector('[data-c="modalidade"]').textContent,
                      espessura: tr.querySelector('[data-c="espessura"]').textContent,
                      modo: tr.querySelector('[data-c="modo"]').textContent,
                      data: tr.querySelector('[data-c="data"]').textContent,
                      levou: tr.querySelector('[data-c="levou"]').textContent};
            })()""")
            checar(u"no navegador: as doze colunas no cabeçalho",
                   m.get(u"ths") == list(TA.COLUNAS), repr(m.get(u"ths")))
            checar(u"  a linha se completa com os detalhes (CT, 2.5 mm, AUTO, 02/01/2026, 1min 15s)",
                   m.get(u"modalidade") == u"CT" and m.get(u"espessura") == u"2.5 mm"
                   and m.get(u"modo") == u"AUTO" and m.get(u"data") == u"02/01/2026"
                   and m.get(u"levou") == u"1min 15s", repr(m))
            pg.click(u"#tab [data-ua-abrir]")
            ab = pg.evaluate(u"window.ABERTOS")
            checar(u"o Abrir chama o callback com a linha e o índice",
                   len(ab) == 1 and ab[0][u"i"] == 0
                   and ab[0][u"l"].get(u"bilhete") == (lista[u"series"][0][u"bilhete"])
                   and ab[0][u"l"].get(u"nome") == u"FANTOMA TABELA", repr(ab)[:300])
            checar(u"  sem caminho de paciente no objeto",
                   u"pasta" not in ab[0][u"l"], repr(ab)[:300])
            checar(u"  e a linha fica marcada",
                   pg.evaluate(u"document.querySelector('#tab tbody tr[data-i=\"0\"]')"
                               u".classList.contains('on')") is True)
            checar(u"nenhum pedido GET leva o caminho (só POST às rotas da tabela)",
                   all(mt == u"POST" for mt, cam in pedidos if cam.startswith(u"/api/")),
                   repr(pedidos))
            ctx.close()
        finally:
            nav.close()


def main():
    print(u"test_ui | o sistema de design e a casca que ele monta")
    testes = [teste_o_explorador_traduz_o_erro,
              teste_fichas_nos_dois_temas, teste_a_folha_tem_as_pecas,
              teste_o_js_e_por_delegacao, teste_a_ajuda_e_o_passo_montam_certo,
              teste_aplicar_costura_ou_devolve_intacta,
              teste_a_casca_e_a_mesma_em_toda_tela,
              teste_home_e_telas_internas_se_distinguem,
              teste_o_voltar_tem_a_pilha_em_toda_tela,
              teste_a_barra_lateral,
              teste_o_panel_reveal_das_barras_laterais,
              teste_os_passos_das_telas,
              teste_nenhuma_tela_ficou_com_folha_propria_de_card,
              teste_a_cor_vem_das_fichas, teste_o_tema_claro_e_legivel,
              teste_a_roda_do_mouse_tem_forma,
              teste_o_js_das_telas_parseia,
              teste_a_checagem_de_js_pega_o_defeito_de_verdade,
              teste_o_portao_e_es5_e_ascii,
              teste_o_portao_entra_no_head_depois_do_charset,
              teste_o_portao_e_servido_de_verdade,
              teste_o_lancador_nao_recua_calado,
              teste_as_animacoes_contam_estado,
              teste_as_seis_que_faltavam_do_pedido,
              teste_a_ordem_de_bisseccao_e_a_mesma_nos_dois_lados,
              teste_a_carga_por_bisseccao_executa,
              teste_a_celula_que_se_repinta_devolve_o_mesmo_visor,
              teste_a_caixa_que_saiu_da_pagina_e_solta,
              teste_o_ver_imagens_do_lote_executa,
              teste_o_aviso_do_visor_diz_o_que_acontece,
              teste_o_3d_nao_espelha_e_as_vistas_sao_as_que_dizem,
              teste_a_bussola_cabe_no_quadro,
              teste_ver_segmentacao_dois_caminhos_e_um_visor,
              teste_o_acervo_que_nao_abre_diz_em_nos_separados,
              teste_o_visor_de_um_eixo_chega_as_telas,
              teste_a_dica_do_3d_passa_pelo_ui_texto,
              teste_o_seletor_de_idioma_no_navegador,
              teste_ver_segmentacao_compara_dois_axiais,
              teste_ver_cada_lado_le_o_seu_arquivo,
              teste_ver_o_servidor_nas_bordas,
              teste_ver_o_js_de_cada_lado_executa,
              teste_onda_4b_a_casca,
              teste_tel19_os_icones_sao_svg,
              teste_c3_as_animacoes_da_casca_no_navegador,
              teste_c2_a_tabela_do_acervo,
              teste_o_tema_tem_tres_escolhas,
              teste_o_seletor_segmentado,
              teste_o_popup_de_serie]
    todos = set(k for k, v in globals().items()
                if k.startswith(u"teste_") and callable(v))
    fora = sorted(todos - set(f.__name__ for f in testes))
    checar(u"todo teste do arquivo está na lista do main()", not fora,
           u", ".join(fora))
    for t in testes:
        try:
            t()
        except Exception as e:
            checar(u"%s (exceção inesperada)" % t.__name__, False,
                   u"%s: %s" % (type(e).__name__, e))
            traceback.print_exc()

    falhas = [(n, d) for n, ok, d in _RESULTADOS if not ok]
    print(u"\n" + u"=" * 68)
    if falhas:
        print(u"FALHOU: %d de %d checagens" % (len(falhas), len(_RESULTADOS)))
        for n, d in falhas:
            print(u"  - %s%s" % (n, (u"  [%s]" % d) if d else u""))
    else:
        print(u"OK: %d checagens, todas passaram" % len(_RESULTADOS))
    print(u"=" * 68)
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
