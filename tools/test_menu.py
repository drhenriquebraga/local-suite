# -*- coding: utf-8 -*-
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(os.path.dirname(AQUI), "app")
sys.path.insert(0, APP)

import radai_menu as M

import tempfile as _tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _cleanup
import _componentes
_cleanup.adotar_prefixo('radai_ac_menu')
os.environ["RADAI_CALIB_DIR"] = _tempfile.mkdtemp(prefix="radai_ac_menu_")


OK = FALHAS = 0
PAGINA = (u'<!doctype html><html><head><meta charset="utf-8">'
          u'<title>x</title><style>body{margin:0;padding:18px}</style>'
          u'</head><body>\n<h1>oi</h1>\n</body></html>')


def secao(t):
    print("\n== %s ==" % t)


def checar(nome, cond, detalhe=""):
    global OK, FALHAS
    if cond:
        OK += 1
        print("  ok     %s" % nome)
    else:
        FALHAS += 1
        print("  FALHA  %s  [%s]" % (nome, detalhe))


def teste_itens():
    secao("menu: os itens")
    chaves = [i[0] for i in M.ITENS]
    checar("sem chave repetida", len(set(chaves)) == len(chaves))
    for c in ("inicio", "vigia", "lote", "config"):
        checar("tem o item %s" % c, c in chaves)
    for c in ("calibrador", "compilador"):
        checar("NAO tem mais o item %s" % c, c not in chaves, str(chaves))

    checar("conferencia NAO e item separado", "conferencia" not in chaves,
           str(chaves))
    checar("e nenhum item leva a /conferencia nem a /compilador",
           not [i for i in M.ITENS if i[1] in ("/conferencia", "/compilador")])
    checar("diagnostico NAO e item de menu", "diagnostico" not in chaves,
           str(chaves))
    checar("e a razao esta escrita", "diagnostico" in M.SEM_ITEM_NO_MENU)
    for chave, href, ico, rotulo, ajuda in M.ITENS:
        checar("%s: href absoluto" % chave, href.startswith("/"), href)
        checar("%s: tem rotulo" % chave, len(rotulo) >= 3, rotulo)
        checar("%s: tem dica" % chave, len(ajuda) >= 8, ajuda)
    agrupadas = [c for _, cs in M.GRUPOS for c in cs]
    import radai_modules
    import radai_breadcrumb
    checar("o trilho nao esta vazio", len(M.MODULOS) >= 3, str(M.MODULOS))
    checar("e o DicomBridge e o primeiro, antes do ContourLab",
           M.MODULOS[0] == "bridge" and M.MODULOS[1] == "autocontorno",
           str(M.MODULOS[:2]))
    checar("o trilho segue a ordem da porta",
           tuple(M.MODULOS) == tuple(M.MODULOS_HOME),
           "%r x %r" % (M.MODULOS, M.MODULOS_HOME))
    for _m in M.MODULOS:
        checar("`%s` tem identidade no registro" % _m,
               _m in radai_modules.MODULOS)
        checar("`%s` tem cor" % _m, _m in radai_modules.CORES)
        checar("`%s` sabe onde mora" % _m,
               (radai_breadcrumb.ARVORE.get(_m) or (None, "", None))[1] not in
               ("", "/", None),
               str(radai_breadcrumb.ARVORE.get(_m)))
    checar("o trilho e a home listam o MESMO conjunto",
           set(M.MODULOS) == set(M.MODULOS_HOME),
           str(sorted(set(M.MODULOS) ^ set(M.MODULOS_HOME))))
    checar("a porta tem a ordem aprovada (DicomBridge primeiro)",
           tuple(M.MODULOS_HOME) == ("bridge", "autocontorno", "recon3d",
                                     "nidus", "elastic", "bolus"),
           repr(M.MODULOS_HOME))
    checar("a Estacao FECHA o pe", M.NO_PE[-1] == "config", str(M.NO_PE))
    checar("e nenhum item do pe esta entre os modulos",
           not (set(M.NO_PE) & set(M.MODULOS)), str(M.NO_PE))

    casca = (u"<!doctype html><html><head><title>t</title></head>"
             u"<body><main>x</main></body></html>")
    html = M.aplicar(casca, "autocontorno")
    checar("a Bibliografia tem entrada em ITENS",
           any(i[0] == "bibliografia" for i in M.ITENS),
           "sem ela o `_item` volta calado e o trilho nasce sem o livro")
    checar("e ela CHEGA ao HTML do trilho", '"/bibliografia"' in html
           or "'/bibliografia'" in html or "/bibliografia" in html,
           "esta em NO_PE mas nao saiu na pagina")
    checar("e ela NAO esta entre os modulos",
           "config" not in M.MODULOS,
           "na mesma sequencia ela leria como um quarto modulo")
    for c in M.MODULOS + M.NO_PE:
        checar("`%s` existe em ITENS" % c, c in chaves)

    h_vazio = M.html("")
    checar("o Inicio NAO esta mais no trilho",
           'class="inicio' not in h_vazio and 'href="/"' not in h_vazio,
           "a marca do cabecalho ja leva para a porta")
    esperado = len(M.MODULOS) + len(M.NO_PE)
    checar("o trilho tem uma ancora por modulo, mais a Estacao",
           h_vazio.count("<a ") == esperado,
           "%d ancoras para %d modulos + %d no pe"
           % (h_vazio.count("<a "), len(M.MODULOS), len(M.NO_PE)))

    checar("`torax` nao esta em ITENS", "torax" not in chaves)
    checar("nem no trilho",
           "torax" not in M.MODULOS and "torax" not in M.NO_PE)
    checar("nem no ALIAS", "torax" not in M.ALIAS.values()
           and "pulmao" not in M.ALIAS)
    import radai_breadcrumb as _T
    checar("nem na arvore da trilha", "torax" not in _T.ARVORE)
    checar("e nenhuma rota do trilho aponta para /torax",
           "/torax" not in h_vazio)

    checar("`CARDS_HOME` nao existe mais", not hasattr(M, "CARDS_HOME"),
           "a home lista modulo, e cada modulo lista as ferramentas dele")


def teste_marcacao():
    secao("menu: a tela ativa se marca")
    h = M.html("ver")
    checar("o ativo leva a classe on", u'class="on"' in h)
    checar("so um ativo", h.count(u'class="on"') == 1, str(h.count(u'class="on"')))
    mod_cal = M.modulo_de("ver")
    checar("e o marcado e o MODULO da ferramenta",
           (u'class="on" data-mod="%s"' % mod_cal) in h,
           u"modulo_de(ver) = %s" % mod_cal)
    import radai_breadcrumb as _tr
    for tela in ("vigia", "lote", "ver", "bridge", "recon3d", "procedencia"):
        mod = M.modulo_de(tela)
        checar("`%s` marca um modulo do trilho (`%s`)" % (tela, mod),
               bool(mod) and (mod in M.MODULOS or mod in M.NO_PE),
               u"a arvore poe `%s` sob `%s`"
               % (tela, (_tr.ARVORE.get(tela) or ("", "", "?"))[2]))
    checar("o Inicio nao pertence a modulo nenhum",
           M.modulo_de("inicio") == "")
    checar("sem ativo, nenhum marcado", u'class="on"' not in M.html(""))
    checar("chave inexistente nao quebra", u'class="on"' not in M.html("xpto"))
    checar("e o ativo leva aria-current",
           u'aria-current="page"' in h,
           "leitor de tela precisa saber qual e a pagina atual")


def teste_aplicar():
    secao("menu: a costura na pagina")
    p = M.aplicar(PAGINA, "vigia")
    checar("o CSS entrou antes do </head>",
           p.index("radai-menu-css") < p.index("</head>"))
    checar("o nav entrou depois do <body>",
           p.index("<body") < p.index('<nav class="radai-menu"'))
    checar("e o body foi carimbado com a tela",
           'data-tela="vigia"' in p[p.index("<body"):p.index(">", p.index("<body"))])
    checar("e ANTES do conteudo da pagina",
           p.index('<nav class="radai-menu"') < p.index("<h1>oi</h1>"))
    checar("o conteudo original continua inteiro", "<h1>oi</h1>" in p)
    checar("o </html> continua no fim", p.rstrip().endswith("</html>"))
    checar("desloca o body com margin, nao padding",
           "body{margin-left:var(--ui-lado)" in p,
           "margin-left ausente")
    checar("a largura do nav le a MESMA variavel que a margem do body",
           "width:var(--ui-lado)" in p and "body{margin-left:var(--ui-lado)" in p)
    checar("a variavel nasce com a largura declarada",
           ("--ui-lado:%dpx" % M.LARGURA) in p, "valor inicial ausente")
    checar("a largura do trilho e 56", M.LARGURA == 56, str(M.LARGURA))
    checar("nao ha mais estado recolhido a esquerda",
           "--ui-lado-recolhido" not in p and "lado-recolhido" not in p,
           "56px e a largura, e ponto")
    checar("o botao do trilho controla a barra da DIREITA",
           "uiDireita()" in p, "e nao a propria barra esquerda")
    checar("tem media query para tela estreita", "@media (max-width:900px)" in p)


def teste_nunca_quebra():
    secao("menu: aplicar() nunca derruba uma tela")
    for nome, entrada in (
            ("string vazia", u""),
            ("None", None),
            ("sem <head>", u"<html><body>oi</body></html>"),
            ("sem <body>", u"<html><head></head>oi</html>"),
            ("texto solto", u"isso nao e html"),
            ("so o doctype", u"<!doctype html>")):
        try:
            saida = M.aplicar(entrada, "vigia")
            checar("%s: devolve sem levantar" % nome, True)
            if entrada and u"</head>" not in entrada.lower():
                checar("%s: devolve a pagina INTACTA" % nome, saida == entrada,
                       repr(saida)[:80])
        except Exception as e:
            checar("%s: devolve sem levantar" % nome, False,
                   "%s: %s" % (type(e).__name__, e))

    duas = M.aplicar(M.aplicar(PAGINA, "vigia"), "config")
    checar("aplicar duas vezes nao duplica o menu",
           duas.count('<nav class="radai-menu"') == 1,
           str(duas.count('<nav class="radai-menu"')))


def teste_escapa():
    secao("menu: escapa o que vai para o HTML")
    guardado_itens = list(M.ITENS)
    guardado_mods = M.MODULOS
    try:
        M.ITENS.append(("xpto", "/x", u"?", u'a"b<c', u'dica & <script>'))
        M.MODULOS = tuple(list(M.MODULOS) + ["xpto"])
        h = M.html("")
        checar("aspas no rotulo nao escapam do atributo", u'a"b' not in h)
        checar("< do rotulo vira entidade", u"a&quot;b&lt;c" in h,
               "title=/aria-label= sem escape")
        checar("e ele aparece nos DOIS atributos",
               h.count(u"a&quot;b&lt;c") >= 2,
               "title e aria-label")
        checar("nao sobra <script> cru", u"<script>" not in h)
    finally:
        M.ITENS[:] = guardado_itens
        M.MODULOS = guardado_mods


def teste_telas_ligadas():
    secao("menu: quais telas foram ligadas")
    esperado = {"radai_batch.py": "lote"}
    for arq, chave in esperado.items():
        fonte = open(_componentes.fonte("app/" + arq), encoding="utf-8").read()
        checar("%s usa o menu" % arq,
               ('radai_menu.aplicar(PAGINA, "%s"' % chave) in fonte
               or ('radai_menu.aplicar(_pagina(), "%s"' % chave) in fonte)
        checar("%s importa radai_menu" % arq, "import radai_menu" in fonte)
    for arq in ("radai_calibrator.py", "radai_crosscheck.py",
                "radai_studio.py", "radai_compiler.py"):
        checar("%s nao existe mais (v8.3)" % arq,
               not os.path.exists(_componentes.fonte("app/" + arq)))

    painel = open(_componentes.fonte("app/radai_panel.py"), encoding="utf-8").read()
    checar("a tela de config usa o menu",
           'radai_menu.aplicar(p, "config"' in painel)
    checar("a de diagnostico tambem",
           'radai_menu.aplicar(PAGINA_LOG, "diagnostico")' in painel)
    checar("a LANDING nao leva menu",
           "radai_menu.aplicar(PAGINA" not in painel.split("def _tela_config")[0])
    inicio = painel.split("def _inicio")[1].split("@app.get")[0]
    checar("a landing costura por uma funcao com nome",
           "_costurar_home(" in inicio)
    costura = painel[painel.index("def _costurar_home("):]
    costura = costura[:costura.index("def pagina_inicial(")]
    for mod, rot in (("radai_ui", "o sistema de design"),
                     ("radai_cover", "a folha da capa")):
        checar("e a costura da mini-pagina traz %s" % rot, mod in costura)
    checar("e NAO traz mais o botao de fechar",
           "radai_shutdown" not in costura,
           "numa mini-pagina ele ficaria a um centimetro do Voltar")
    cfg_py = painel[painel.index("def _tela_config"):]
    cfg_py = cfg_py[:cfg_py.index("@app.get", 10)]
    rot_py = open(_componentes.fonte("app/radai_router.py"), encoding="utf-8").read()
    checar("quem traz o idioma e Configuracoes", "radai_languages" in cfg_py)
    checar("o seletor vem ANTES do menu",
           cfg_py.index("radai_languages") < cfg_py.index("radai_menu.aplicar"))
    porta_py = rot_py[rot_py.index("def montar_porta("):]
    porta_py = porta_py[:porta_py.index("\ndef ")]
    checar("quem traz o Fechar e a porta da suite",
           "radai_shutdown" in porta_py,
           "sem a costura, a ancora do cabecalho fica sem botao")
    checar("e o encerrar DEPOIS da costura da porta",
           "radai_menu.aplicar_porta" in porta_py
           and porta_py.index("radai_shutdown")
           > porta_py.index("radai_menu.aplicar_porta"))
    composicao = rot_py[:rot_py.index("\ndef montar(")]
    checar("a porta da suite nao costura o seletor de idioma",
           "radai_languages" not in composicao,
           "sem ancora no cabecalho da porta, ele nao apareceria la")
    checar("e a mini-pagina costura o trilho",
           "radai_menu.aplicar(p, \"autocontorno\"" in costura,
           "sem ele, so se volta pela marca do cabecalho")
    menu_py = open(_componentes.fonte("app/radai_menu.py"), encoding="utf-8").read()
    corpo = menu_py[menu_py.index("def aplicar("):]
    checar("as telas internas NAO recebem o Fechar",
           "_com_encerrar(" not in corpo)
    checar("nem o seletor de idioma", "_com_idioma(" not in corpo)

    vigia = open(_componentes.fonte("app/radai_watcher.py"), encoding="utf-8").read()
    checar("o painel do worker virou redirecionamento para /lote",
           'RedirectResponse(url="/lote"' in vigia)
    checar("  e preserva o metodo (307, e nao 302)",
           "status_code=307" in vigia,
           "302 troca POST por GET; nada chama /vigia com POST hoje, e o "
           "dia em que alguem acrescentar o primeiro e o dia em que isso "
           "deixa de ser verdade calado")
    checar("com import preguicoso e protegido",
           "        import radai_menu" in vigia and "    except Exception:" in vigia)
    checar("e o GUARDA: diz por que",
           "GUARDA: import pregui" in vigia)


def teste_o_idioma_e_o_fechar_aparecem():
    secao("o idioma e o fechar tem onde aparecer")
    import radai_languages
    import radai_menu
    import radai_panel
    import radai_router

    p = radai_panel.PAGINA_CONFIG
    p = radai_languages.aplicar(p)
    p = radai_menu.aplicar(p, "config", com_tarefas=False)
    porta = radai_router.montar_porta()

    import re as _re
    def sem_script(t):
        return _re.sub(r"<script.*?</script>", " ", t, flags=_re.S)

    def ancora_de_idioma(t):
        t = _re.sub(r"<style.*?</style>", " ", t, flags=_re.S)
        return bool(_re.search(r"<[a-zA-Z][^<>]*\sdata-radai-(?:idiomas|lang)"
                               r"(?=[\s=>/])", t))

    marcacao = sem_script(p)
    checar("a tela de config tem a ancora do idioma",
           ancora_de_idioma(marcacao))
    checar("o seletor de idioma foi costurado", "radai-lang" in p)
    porta_m = sem_script(porta)
    checar("a porta da suite tem a ancora do encerrar",
           "data-radai-encerrar" in porta_m)
    checar("e o dialogo das duas saidas tambem", "rx-veu" in porta)
    for saida in ("rx-tudo", "rx-cancelar"):
        checar("a saida `%s` esta la" % saida, saida in porta)
    checar("e a saida que saiu (manter so o vigia) nao volta",
           "rx-so-vigia" not in porta)

    import radai_modules
    interna = radai_menu.aplicar(radai_modules.pagina_completa("bridge"),
                                 "bridge", com_tarefas=False)
    interna_m = sem_script(interna)
    checar("a tela interna NAO tem a ancora do idioma",
           not ancora_de_idioma(interna_m))
    checar("nem a do encerrar", "data-radai-encerrar" not in interna_m)
    checar("e mesmo assim ela traduz", "radai-idioma-js" in interna)
    checar("buscando o dicionario por referencia",
           "/radai-idiomas.js" in interna,
           "sem a rota o script aponta para um 404 e nada traduz")


def _nome_na_porta(chave):
    import re as _re
    import radai_modules as M
    import radai_router as R
    porta = R.montar_porta()
    rota = {"nidus": "/nidus", "elastic": "/elastic"}[chave]
    m = _re.search(r'<a class="ls-card tool-card" href="%s"[^>]*>.*?'
                   r'<span class="ls-nome tool-name"[^>]*>(.*?)</span>'
                   % rota, porta, _re.S)
    h2 = _re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else ""
    pag = M.pagina(chave)
    h = _re.search(r"<h1[^>]*>(.*?)</h1>", pag, _re.S)
    h1 = _re.sub(r"<[^>]+>", "", h.group(1)).strip() if h else ""
    return h2, h1


def teste_os_nomes_dos_modulos_tem_o_espaco():
    secao("Nidus RT e Elastic RT, com o espaco, na porta e no h1")
    import radai_modules as M
    for chave, nome in (("nidus", "Nidus RT"), ("elastic", "Elastic RT")):
        h2, h1 = _nome_na_porta(chave)
        checar("[%s] a porta diz «%s»" % (chave, nome), h2 == nome, repr(h2))
        checar("[%s]   e o h1 da mini-pagina tambem" % chave,
               " ".join(h1.split()) == nome, repr(h1))
        m = M.MODULOS[chave]
        checar("[%s]   e o nome montado do registro" % chave,
               (m["titulo"] + m["destaque"]) == nome,
               repr(m["titulo"] + m["destaque"]))
    isca = dict(M.MODULOS["nidus"], titulo="Nidus")
    checar("  (isca) sem o espaco, o nome montado volta a ser «NidusRT»",
           isca["titulo"] + isca["destaque"] == "NidusRT")


def _corpo(p):
    i = p.lower().find("<body")
    return p[i:p.index(">", i) + 1] if i >= 0 else ""


def teste_a_identidade_marca_so_as_ferramentas():
    secao("identidade: so as telas de ferramenta levam data-ls-identidade")
    import radai_breadcrumb as B
    ferramentas = sorted(k for k, v in B.ARVORE.items() if v[2] in M.MODULOS)
    checar("a arvore tem as ferramentas dos seis modulos",
           len(ferramentas) >= 9 and "bolus_gerar" in ferramentas
           and "lote" in ferramentas, repr(ferramentas))
    for k in ferramentas:
        checar("`%s` e ferramenta" % k, M.e_ferramenta(k))
        c = _corpo(M.aplicar(PAGINA, k, com_tarefas=False))
        checar("  e o body leva data-ls-identidade=\"trabalho\"",
               'data-ls-identidade="trabalho"' in c, c)
    for k in ("inicio", "config", "bibliografia", "procedencia", "creditos",
              "termos", "diagnostico", "xpto", "") + tuple(M.MODULOS):
        c = _corpo(M.aplicar(PAGINA, k, com_tarefas=False))
        checar("`%s` nao e tela de ferramenta" % k,
               not M.e_ferramenta(k) and "data-ls-identidade" not in c, c)
    ja = (u'<!doctype html><html><head><title>x</title></head>'
          u'<body data-tela="lote"><p>x</p></body></html>')
    c = _corpo(M.marcar_tela(ja, "lote"))
    checar("body que ja tem data-tela ganha a identidade sem repetir a tela",
           c.count("data-tela=") == 1 and 'data-ls-identidade="trabalho"' in c, c)
    c = _corpo(M.marcar_tela(M.marcar_tela(PAGINA, "lote"), "lote"))
    checar("  e marcar de novo nao repete o atributo",
           c.count("data-ls-identidade") == 1, c)


def teste_o_trilho_pinta_cada_modulo():
    secao("trilho: cada modulo tem a sua cor, e o icone inativo acende no hover")
    folha = M.folha_do_trilho()
    import re as _re
    for k in M.MODULOS:
        achou = _re.search(r'\.radai-menu a\[data-mod="%s"\]\{--mod-cor:var\(--mod-'
                           % k, folha)
        checar("`%s` define --mod-cor no trilho" % k, bool(achou))
    isca = folha.replace('a[data-mod="nidus"]', 'a[data-mod="nidus-isca"]')
    checar("  (isca) sem a linha do Nidus, ele volta ao azul",
           not _re.search(r'\.radai-menu a\[data-mod="nidus"\]\{--mod-cor', isca))


def teste_o_bolus_tem_icone_proprio():
    secao("trilho: o 3D Printed Bolus tem icone proprio, distinto do DicomBridge")
    import radai_ui as U
    por = dict((i[0], i) for i in M.ITENS)
    checar("o item do bolus usa a chave `bolus`", por["bolus"][2] == u"bolus",
           por["bolus"][2])
    svg = U.icone(u"bolus")
    checar("a chave `bolus` desenha com o envelope de radai_ui.icone",
           u'class="ui-ic"' in svg and u'viewBox="0 0 24 24"' in svg
           and u'aria-hidden="true"' in svg and u'focusable="false"' in svg)
    checar("  com as camadas curvas da porta, no traco efetivo de 1,6",
           u'scale(.2857142857)' in svg and u'stroke-width="5.6"' in svg
           and svg.count(u"<path") == 4, svg[:200])
    h = M.html(u"bolus_gerar")
    item = h[h.index(u'data-mod="bolus"'):]
    item = item[:item.index(u"</a>")]
    checar("o trilho mostra o icone novo no item do bolus",
           u"scale(.2857142857)" in item, item[:160])
    checar("  e so nele", h.count(u"scale(.2857142857)") == 1)
    checar("  e o desenho e outro que o do DicomBridge",
           U.icone(u"bolus") != U.icone(por["bridge"][2]))
    checar("a chave `camadas` continua a mesma (nao foi trocada no lugar)",
           u"scale(" not in U.icone(u"camadas"))


def main():
    print("test_menu | barra lateral das telas de trabalho")
    for t in (teste_itens, teste_marcacao, teste_aplicar, teste_nunca_quebra,
              teste_escapa, teste_telas_ligadas,
              teste_o_idioma_e_o_fechar_aparecem,
              teste_os_nomes_dos_modulos_tem_o_espaco,
              teste_a_identidade_marca_so_as_ferramentas,
              teste_o_trilho_pinta_cada_modulo, teste_o_bolus_tem_icone_proprio):
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
