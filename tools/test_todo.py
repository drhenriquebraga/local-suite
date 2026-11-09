# -*- coding: utf-8 -*-
import shutil
import os
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(os.path.dirname(AQUI), "app")
sys.path.insert(0, APP)

os.environ["RADAI_CALIB_DIR"] = tempfile.mkdtemp(prefix="radai_tarefas_")
os.environ["RADAI_CONFIG"] = os.path.join(os.environ["RADAI_CALIB_DIR"],
                                          "radai_watcher.config")
_CONFIG_DO_APP = os.path.join(APP, "radai_watcher.config")
_CONFIG_DO_APP_ANTES = (os.path.getmtime(_CONFIG_DO_APP)
                        if os.path.exists(_CONFIG_DO_APP) else None)

import radai_archive as A
import radai_todo as TF

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _cleanup
import _componentes
_cleanup.adotar_prefixo('radai_tarefas_')


assert str(A.raiz()) == os.environ["RADAI_CALIB_DIR"], "acervo NAO isolado"

OK = FALHAS = 0
PAGINA = (u'<!doctype html><html><head><title>x</title>'
          u'<style>body{margin:0}</style></head><body>\n<h1>oi</h1>\n</body></html>')


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


def teste_vazio_diz_que_esta_vazio():
    secao("atividade: sem nada rodando, diz que nao ha")
    checar("lista vazia e resposta valida numa maquina parada",
           TF.atividade(None) == [], str(TF.atividade(None)))
    checar("a barra explica o vazio em vez de sumir",
           "Nada rodando nesta estação" in TF.HTML)
    checar("e diz de onde virao os cartoes",
           "Quando um lote ou o vigia estiverem trabalhando" in TF.HTML)


def teste_a_fila_de_validacao_saiu():
    secao("tarefas: a fila de validacao saiu com o calibrador")
    fonte = open(_componentes.fonte("app/radai_todo.py"), encoding="utf-8").read()
    for nome in ("listar", "pacote_compilado", "pacote_treino", "abrir_pasta",
                 "_series_por_validar", "_versoes_sem_envio", "_treino"):
        checar("%s saiu do modulo" % nome, not hasattr(TF, nome))
    checar("nenhum import do compilador nem do treino",
           "import radai_compiler" not in fonte
           and "import radai_training" not in fonte)
    for rota in ("/conferencia", "/compilador"):
        checar("nenhum cartao aponta para %s" % rota,
               ('"%s' % rota) not in fonte and ("'%s" % rota) not in fonte)
    checar("o modal do pacote de e-mail saiu",
           "radai_tf_modal" not in TF.HTML and "radaiTfPreparar" not in TF.HTML)
    checar("a rota da fila de validacao saiu",
           '@app.get("/api/tarefas")' not in fonte
           and '"/api/tarefas/pacote"' not in fonte)


def teste_costura_na_pagina():
    secao("tarefas: a costura")
    p = TF.aplicar(PAGINA)
    checar("o CSS entra antes do </head>",
           p.index("radai-tarefas-css") < p.index("</head>"))
    checar("a barra entra ANTES do </body>",
           p.index('class="radai-tarefas"') < p.rindex("</body>"))
    checar("o conteudo da pagina continua inteiro", "<h1>oi</h1>" in p)
    checar("desloca o body pela direita",
           "body{margin-right:%dpx !important}" % TF.LARGURA in p)
    checar("aplicar duas vezes nao duplica",
           TF.aplicar(p).count('class="radai-tarefas"') == 1)
    for nome, entrada in (("vazia", u""), ("None", None),
                          ("sem head", u"<html><body>x</body></html>"),
                          ("sem body", u"<html><head></head>x</html>"),
                          ("texto solto", u"nao e html")):
        try:
            saida = TF.aplicar(entrada)
            checar("%s: nao levanta" % nome, True)
            checar("%s: devolve intacta" % nome, saida == entrada, repr(saida)[:60])
        except Exception as e:
            checar("%s: nao levanta" % nome, False, "%s: %s" % (type(e).__name__, e))


def teste_ligada_ao_menu():
    secao("tarefas: entra junto com o menu")
    menu = open(_componentes.fonte("app/radai_menu.py"), encoding="utf-8").read()
    checar("o menu costura a barra da direita", "_com_tarefas(pagina" in menu)
    checar("com import protegido", "        import radai_todo" in menu)
    checar("e da para desligar por tela", "com_tarefas=True" in menu)

    import radai_menu
    p = radai_menu.aplicar(PAGINA, "vigia")
    checar("as duas barras convivem na mesma pagina",
           'class="radai-menu"' in p and 'class="radai-tarefas"' in p)
    checar("uma desloca para a esquerda e a outra para a direita",
           "margin-left:" in p and "margin-right:" in p)
    sem = radai_menu.aplicar(PAGINA, "vigia", com_tarefas=False)
    checar("desligada, so o menu entra",
           'class="radai-menu"' in sem and 'class="radai-tarefas"' not in sem)

    painel = open(_componentes.fonte("app/radai_panel.py"), encoding="utf-8").read()
    checar("o painel monta a API das tarefas", '"radai_todo"' in painel)


def _nasce_recolhida(p, sozinha):
    import re
    m = re.search(r"<html\b[^>]*>", p or u"", re.I)
    if not m:
        return False
    tag = m.group(0)
    c = re.search(r"\sclass=\"([^\"]*)\"", tag)
    return (bool(c) and u"dir-recolhida" in c.group(1).split()
            and (u'data-dir-sozinha="%s"' % (u"1" if sozinha else u"0")) in tag)


def teste_a_barra_nasce_recolhida_no_html_servido():
    secao(u"a barra da direita nasce recolhida no HTML servido")
    checar(u"só o Rodar agora e o Ver segmentação abrem sozinhos",
           TF.TELAS_QUE_ABREM_SOZINHAS == ("lote", "ver"),
           str(TF.TELAS_QUE_ABREM_SOZINHAS))
    for tela, sozinha in ((u"lote", True), (u"ver", True), (u"autocontorno", False),
                          (u"bridge_laudo", False), (u"recon_anatomia", False)):
        p = TF.aplicar(PAGINA, tela=tela)
        checar(u"%s: recolhida no <html>, e abre sozinha=%s" % (tela, sozinha),
               _nasce_recolhida(p, sozinha), p[:90])
    checar(u"  (isca) a página sem a marca é acusada",
           not _nasce_recolhida(PAGINA, False)
           and not _nasce_recolhida(TF.aplicar(PAGINA, tela=u"lote"), False))
    p = TF.aplicar(PAGINA.replace(u"<html>", u'<html lang="pt" class="x">'), tela=u"ver")
    checar(u"a classe que a página já tinha fica",
           u'<html lang="pt" class="dir-recolhida x" data-dir-sozinha="1">' in p, p[:90])
    p = TF.aplicar(PAGINA.replace(u"<html>", u""), tela=u"lote")
    checar(u"página sem <html> ganha um antes do <head>",
           _nasce_recolhida(p, True) and p.index(u"<html") < p.index(u"<head"), p[:90])
    p = TF.aplicar(PAGINA.replace(u"<body>", u'<body data-tela="ver">'))
    checar(u"sem a tela no pedido, lê a do <body>", _nasce_recolhida(p, True), p[:90])
    p = TF.aplicar(PAGINA, tela=u"lote")
    checar(u"marcar de novo não duplica",
           TF.marcar_html(p, u"bridge").count(u"data-dir-sozinha") == 1)
    import radai_menu
    checar(u"o menu passa a tela: o Ver segmentação abre sozinho, a mini-página não",
           _nasce_recolhida(radai_menu.aplicar(PAGINA, u"ver"), True)
           and _nasce_recolhida(radai_menu.aplicar(PAGINA, u"autocontorno"), False))
    checar(u"a decisão depois do DOMContentLoaded saiu (era o pisca)",
           u"radaiFilaInicial" not in TF.HTML and u"ABERTA_EM" not in TF.HTML
           and u"radai_dir_recolhido" not in TF.HTML)
    css = TF.folha()
    checar(u"abrir e recolher animam o panel reveal da casca, com metade da largura de curso",
           u"html.dir-abrindo .radai-tarefas{--ui-painel-curso:%dpx;" % (TF.LARGURA // 2)
           in css and u"animation:uiPainelEntra var(--ui-painel-abre,400ms)" in css
           and u"animation:uiPainelSai var(--ui-painel-fecha,350ms)" in css)
    checar(u"  e nada anima para quem pede movimento reduzido",
           u"html.dir-abrindo .radai-tarefas,html.dir-fechando .radai-tarefas"
           u"{animation:none}" in css)
    checar(u"o ponto da fila se refaz quando a barra assenta (o recolher espera a animação)",
           u"document.addEventListener('radai:dir'" in TF.HTML)


def teste_so_biblioteca_padrao():
    secao("tarefas: so stdlib no topo")
    import ast
    fonte = open(_componentes.fonte("app/radai_todo.py"), encoding="utf-8").read()
    topo = []
    for no in ast.parse(fonte).body:
        if isinstance(no, ast.Import):
            topo += [a.name.split(".")[0] for a in no.names]
        elif isinstance(no, ast.ImportFrom) and no.module:
            topo.append(no.module.split(".")[0])
    checar("nada pesado no topo",
           not ({"numpy", "SimpleITK", "fastapi", "torch", "pydicom"} & set(topo)),
           str(topo))
    checar("o contato do e-mail do compilado saiu com ele",
           not hasattr(TF, "CONTATO"))


def teste_as_abas_fila_e_log():
    secao(u"a barra da direita: duas abas, Fila e Log")
    PAG = u"<html><head></head><body><h1>oi</h1></body></html>"
    p = TF.aplicar(PAG, com_pendencias=True)
    so = TF.aplicar(PAG)
    checar(u"com_pendencias=True da a MESMA barra (a fila de validacao saiu)",
           p == so)

    import re as _re
    tabs = _re.findall(u'<button type="button" role="tab"[^>]*>', so)
    checar(u"ha uma linha de abas, com DUAS abas",
           u'role="tablist"' in so and len(tabs) == 2, u"%d aba(s)" % len(tabs))
    _fila = next((t for t in tabs if u'id="radai_tf_ab_fila"' in t), u"")
    _log = next((t for t in tabs if u'id="radai_tf_ab_log"' in t), u"")
    checar(u"  a da Fila nasce escolhida, e a do Log nao",
           u'aria-selected="true"' in _fila and u'aria-selected="false"' in _log,
           u"«a Fila aberta por padrao»")
    checar(u"  e cada aba aponta para a sua regiao (`aria-controls`)",
           u'aria-controls="radai_tf_reg_fila"' in _fila
           and u'aria-controls="radai_tf_reg_log"' in _log)
    checar(u"  e so a escolhida entra na ordem do Tab (a outra tem -1)",
           u'tabindex="-1"' in _log and u"tabindex" not in _fila)
    checar(u"a aba da Fila vem ANTES da do Log",
           so.index(u'id="radai_tf_ab_fila"') < so.index(u'id="radai_tf_ab_log"'))
    i_fila = so.index(u'id="radai_tf_reg_fila"')
    i_log = so.index(u'id="radai_tf_reg_log"')
    tag_fila = so[so.rfind(u"<section", 0, i_fila):so.index(u">", i_fila)]
    tag_log = so[so.rfind(u"<section", 0, i_log):so.index(u">", i_log)]
    checar(u"a regiao da Fila e um `tabpanel` e nasce visivel",
           u'role="tabpanel"' in tag_fila and u"hidden" not in tag_fila,
           tag_fila)
    checar(u"a regiao do Log e um `tabpanel` e nasce OCULTA",
           u'role="tabpanel"' in tag_log and u"hidden" in tag_log, tag_log)
    checar(u"o contador da fila esta DENTRO da aba da Fila",
           so.index(u'id="radai_tf_ab_fila"') < so.index(u'id="radai_fila_n"')
           < so.index(u'id="radai_tf_ab_log"'))
    checar(u"o ponto de vida do vigia e o rotulo do ponto vermelho estao na "
           u"aba do Log",
           so.index(u'id="radai_tf_ab_log"') < so.index(u'id="radai_tf_pt"')
           < so.index(u'id="radai_tf_ab_log_rot"')
           < so.index(u'id="radai_tf_reg_fila"'))
    _abas = so[so.index(u'role="tablist"'):so.index(u'id="radai_tf_reg_fila"')]
    checar(u"e o recolher esta na linha das abas",
           u'class="dobra" onclick="uiDireita()"' in _abas)
    for nome, h in ((u"configuracoes", p), (u"tela de trabalho", so)):
        checar(u"[%s] o log existe" % nome, u'id="radai_tf_log"' in h)

    checar(u"a fila aparece nas duas formas",
           u'id="radai_fila"' in so and u'id="radai_fila"' in p)
    checar(u"e o painel do «Agora» nasce oculto",
           u'id="radai_tf_pn_p" hidden' in so)
    checar(u"a fila vem ANTES do log no documento",
           so.index(u'id="radai_fila"') < so.index(u'id="radai_tf_log"'))

    checar(u"a fonte viaja no DOM, e e uma so",
           u'data-fonte="atividade"' in so and u'data-fonte="pendencias"' not in p)
    checar(u"e a rota e a do que esta rodando",
           u"/api/atividade" in so and u"'/api/tarefas'" not in so)
    checar(u"o log e o MESMO nas duas formas (nao ha segunda implementacao)",
           u'id="radai_tf_log"' in so and u'id="radai_tf_log"' in p)
    corpo = _funcao_js(so, u"radaiTfAba")
    checar(u"`radaiTfAba` troca a aba de verdade, e entende 'l' e 'p'",
           u"qual === 'l'" in corpo and u"qual === 'p'" in corpo
           and u"r.hidden = !sel" in corpo and u"aria-selected" in corpo,
           corpo[:120])
    checar(u"  e abrir o Log apaga o ponto vermelho",
           u"radaiTfPontoLog(false)" in corpo)

    for nome, h in ((u"configuracoes", p), (u"tela de trabalho", so)):
        arr = h[h.index(u"DOMContentLoaded"):]
        checar(u"[%s] o log comeca a bater no arranque" % nome,
               u"radaiTfLog();" in arr)
    corpo_log = _funcao_js(so, u"radaiTfLog")
    checar(u"o polling para com a barra recolhida",
           u"classList.contains('dir-recolhida')" in corpo_log)
    checar(u"  e NAO para com a aba Log fechada (o ponto depende disso)",
           u"RADAI_TF_ABA" not in corpo_log and u"hidden" not in corpo_log,
           corpo_log[:160])


def teste_o_log_le_o_vigia_EM_EXECUCAO():
    secao(u"o log le o vigia EM EXECUCAO, e nao uma segunda copia")
    import sys as _s
    from collections import deque

    class _Falso(object):
        LOGBUF = deque([u"[24/08 22:13:01] Vigia iniciado",
                        u"[24/08 22:13:02] FALHOU serie ...1234",
                        u"[24/08 22:13:03] 7 estrutura(s) em RS.dcm"])
        STATE = {"paused": False, "worker_erro": "", "ambiente_erro": ""}

    guardado = _s.modules.get("__main__")
    _s.modules["__main__"] = _Falso()
    try:
        linhas, prox, estado = TF._fatia_do_log(0)
        checar(u"le o LOGBUF de quem esta rodando", len(linhas) == 3,
               u"%d linha(s) -- zero aqui e o defeito de volta" % len(linhas))
        checar(u"e separa a hora do texto",
               linhas and linhas[0]["t"] == u"22:13:01", str(linhas[:1]))
        checar(u"e nao repete o carimbo dentro do texto",
               linhas and u"[24/08" not in linhas[0]["txt"])
        checar(u"classifica falha como erro",
               len(linhas) > 1 and linhas[1]["nivel"] == "erro")
        checar(u"e conclusao como ok",
               len(linhas) > 2 and linhas[2]["nivel"] == "ok")
        checar(u"o cursor avanca (o pedido e incremental)", prox == 3, str(prox))
        checar(u"pedindo do fim, nada volta", TF._fatia_do_log(3)[0] == [])
        checar(u"o estado sai do STATE de quem roda", estado == "ok", estado)

        _Falso.STATE["paused"] = True
        checar(u"vigia pausado acende ambar",
               TF._estado_do_vigia() == "parado", TF._estado_do_vigia())
        _Falso.STATE["paused"] = False
        _Falso.STATE["ambiente_erro"] = u"sem TotalSegmentator"
        checar(u"e erro de ambiente acende vermelho",
               TF._estado_do_vigia() == "erro", TF._estado_do_vigia())
    finally:
        if guardado is not None:
            _s.modules["__main__"] = guardado
        else:
            _s.modules.pop("__main__", None)

    class _Nada(object):
        pass
    guardado = _s.modules.get("__main__")
    _s.modules["__main__"] = _Nada()
    try:
        l, prox, est = TF._fatia_do_log(0)
        checar(u"sem vigia, nao levanta", isinstance(l, list))
    finally:
        if guardado is not None:
            _s.modules["__main__"] = guardado
        else:
            _s.modules.pop("__main__", None)


def teste_todo_cartao_leva_a_algum_lugar():
    secao(u"todo cartao de atividade leva a algum lugar")
    import radai_todo as TF

    def _vigia():
        return {"atual": {"pid": "PACX", "uid8": "12345678", "etapa": "task total"},
                "n_queue": 2}

    cartoes = TF.atividade(_vigia)
    checar(u"ha cartao com algo rodando", bool(cartoes), str(cartoes))
    sem_destino = [c for c in cartoes
                   if not (c.get("href") or c.get("acao"))]
    checar(u"nenhum cartao nasce sem destino nem acao",
           not sem_destino, str(sem_destino))
    mem = [c for c in cartoes if c["id"] == "recurso:mem"]
    if mem:
        h = mem[0].get("href") or ""
        checar(u"o de memoria leva ao Diagnosticar, e nao so a /config",
               h.startswith("/config#"), h)
        checar(u"  e nao oferece mais o Otimizar",
               (mem[0].get("botao") or "") != u"Otimizar", mem[0].get("botao"))
        checar(u"  e o botao diz o que ele faz",
               (mem[0].get("botao") or "").lower() != "abrir",
               mem[0].get("botao"))
    parada = TF.atividade(lambda: {})
    checar(u"maquina parada nao mostra cartao de recurso",
           not [c for c in parada if c["id"].startswith("recurso:")],
           str(parada))


def teste_os_dois_icones_da_barra_recolhida_dizem_o_nome():
    secao(u"os dois icones da barra recolhida dizem o nome")
    import radai_todo as TF
    for com_pend in (False, True):
        b = TF.barra(com_pendencias=com_pend)
        nomes = b.count(u'class="nm"')
        checar(u"os dois icones tem nome visivel (pendencias=%s)" % com_pend,
               nomes == 2, u"%d achado(s)" % nomes)
    b = TF.barra()
    import re as _re
    nms = _re.findall(u'class="nm"[^>]*>([^<]*)<', b)
    checar(u"os dois nomes sao DIFERENTES", len(set(nms)) == 2,
           u" / ".join(nms) or u"nenhum")
    checar(u"e os nomes sao os das abas (Fila e Log)",
           sorted(nms) == [u"Fila", u"Log"], u" / ".join(nms))
    checar(u"e cada um abre a barra na SUA aba",
           b.count(u"radaiTfAbrirAba('fila', true)") == 1
           and b.count(u"radaiTfAbrirAba('log', true)") == 1)
    corpo = _funcao_js(TF.HTML, u"radaiTfAbrirAba")
    checar(u"  e abrir a aba desdobra a barra antes, dizendo se foi pedido de mão",
           u"uiDireita('0', !!deMao)" in corpo and u"radaiTfAba(qual)" in corpo,
           corpo[:120])
    checar(u"o botao de dobrar some onde a barra nao dobra",
           u".radai-tarefas .dir-abas .dobra{display:none}" in TF.CSS)
    for reg in (u".dir-abas", u".fila", u".logreg", u".painel"):
        checar(u"recolhida, `%s` some" % reg,
               u"html.dir-recolhida .radai-tarefas %s" % reg in TF.CSS)


def _tokens_por_tema():
    import re
    import radai_ui
    fonte = open(radai_ui.__file__, encoding="utf-8").read()
    base = {}
    temas = {}
    for sel, corpo in re.findall(r"(:root(?:\[data-tema=\"claro\"\])?)\s*\{([^{}]*)\}",
                                 fonte):
        pares = dict(re.findall(r"(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{3,6})\b", corpo))
        if sel == ":root" and "--bg-0" in pares:
            base.update(pares)
        elif "claro" in sel and "--bg-0" in pares:
            temas["claro"] = pares
    temas["escuro"] = dict(base)
    if "claro" in temas:
        claro = dict(base)
        claro.update(temas["claro"])
        temas["claro"] = claro
    return temas


def _contraste(a, b):
    def lum(h):
        h = h.lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        cs = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
        cs = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
              for c in cs]
        return 0.2126 * cs[0] + 0.7152 * cs[1] + 0.0722 * cs[2]
    l1, l2 = sorted((lum(a), lum(b)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def teste_a_fila_na_altura_inteira_e_os_quatro_botoes():
    secao(u"a aba na altura inteira, e os quatro botoes")
    so = TF.aplicar(PAGINA)
    css = TF.folha()
    checar(u"a fila e o log crescem os dois ate a altura inteira",
           u".radai-tarefas .fila{flex:1 1 0;" in css
           and u".radai-tarefas .logreg{flex:1 1 0;" in css,
           u"base zero, e a aba oculta sai do fluxo")
    checar(u"  e a regiao oculta sai do fluxo de verdade (`[hidden]` vence o "
           u"`display:flex`)",
           u".radai-tarefas .fila[hidden],.radai-tarefas .logreg[hidden]"
           u"{display:none !important}" in css)
    checar(u"as constantes da divisao 2:1 sairam com ela",
           not hasattr(TF, "FATIA_FILA") and not hasattr(TF, "FATIA_LOG"))
    i_log = so.index(u'<section class="logreg"')
    checar(u"o painel do log mora na regiao do log",
           i_log < so.index(u'id="radai_tf_pn_l"') < so.index(u"</section>", i_log))
    checar(u"e o `button` nu da tela hospedeira nao da margem aos da barra",
           u".radai-tarefas button{margin:0}" in css,
           u"a margem do `/lote` inflava o cabecalho do log para 66 px")
    i_fila = so.index(u'<section class="fila"')
    i_fim = so.index(u"</section>", i_fila)
    ids = (u"radai_pipe_ini", u"radai_pipe_pau", u"radai_pipe_lim",
           u"radai_pipe_can")
    for bid in ids:
        checar(u"o botao `%s` existe, dentro da regiao da fila" % bid,
               i_fila < so.find(u'id="%s"' % bid) < i_fim,
               u"o controle da fila mora na aba dela")
    checar(u"o pedido de avisar mora na aba da Fila, e nasce oculto",
           i_fila < so.find(u'id="radai_notif_pede" hidden') < i_fim)
    for rota in (u"/api/pipeline/iniciar", u"/api/pipeline/pausar",
                 u"/api/pipeline/cancelar", u"/api/fila/limpar"):
        checar(u"  e a rota `%s` esta escrita por inteiro" % rota,
               (u"'%s'" % rota) in so)
    for rota in (u"/api/lote/otimizacao", u"/api/lote/otimizar"):
        checar(u"  e a rota `%s` do Otimizar saiu da barra" % rota,
               rota not in so)
    checar(u"  e o alerta de estacao nao otimizada tambem",
           u"radai_pipe_otm" not in so and u"radaiOtimSugerir" not in so)
    i = so.index(u"function radaiPipe(")
    corpo = so[i:so.index(u"function radaiPipeMandar(", i)]
    checar(u"cancelar pergunta antes de mandar",
           u"acao === 'cancelar'" in corpo
           and u"radaiPipePerguntar({" in corpo.split(u"acao === 'cancelar'")[1][:400])
    checar(u"iniciar nao pergunta nada alem da conferencia: as duas perguntas "
           u"sao as do Cancelar (a serie do lote e a do vigia)",
           corpo.count(u"radaiPipePerguntar(") == 2
           and corpo.split(u"acao === 'limpar'")[0].count(
               u"radaiPipePerguntar(") == 2, str(corpo.count(u"radaiPipePerguntar(")))
    checar(u"o Limpar vai pela funcao dele, que pergunta so pelo que falhou",
           u"radaiFilaLimpar();" in corpo
           and u"falhas_restantes" in _funcao_js(so, u"radaiFilaLimpar"))
    lim = _funcao_js(so, u"radaiFilaLimpar")
    checar(u"  e com parcial entre eles a pergunta diz que saiu parcial, e que "
           u"o aviso do que faltou some junto",
           u"parciais_restantes" in lim and u"saíram parciais" in lim
           and u"o aviso do que faltou" in lim, lim[:200])
    temas = _tokens_por_tema()
    pares = {u"INICIAR": (u"--ok-txt", u"--ok"),
             u"PAUSAR": (u"--aviso", u"--fundo-aviso"),
             u"CANCELAR": (u"--perigo", u"--fundo-perigo"),
             u"LIMPAR": (u"--text", u"--panel-2")}
    checar(u"os dois temas foram lidos da folha", set(temas) == {u"escuro",
                                                                 u"claro"},
           str(sorted(temas)))
    for tema, tok in sorted(temas.items()):
        for bt, (txt, fundo) in sorted(pares.items()):
            if txt not in tok or fundo not in tok:
                checar(u"[%s] %s: os tokens existem" % (tema, bt), False,
                       u"%s / %s" % (txt, fundo))
                continue
            r = _contraste(tok[txt], tok[fundo])
            checar(u"[%s] %s passa a AA (%.2f:1)" % (tema, bt, r), r >= 4.5,
                   u"%s sobre %s" % (tok[txt], tok[fundo]))
    import re
    blo = css[css.index(u".radai-tarefas .pipe-bt.ini{"):
              css.index(u".radai-tarefas .pipe-bt[disabled]{")]
    for tok, fb in re.findall(r"var\((--[\w-]+),(#[0-9a-fA-F]{3,6})\)", blo):
        checar(u"o recuo de `%s` e o valor do token" % tok,
               temas[u"escuro"].get(tok, u"").lower() == fb.lower(),
               u"%s != %s" % (fb, temas[u"escuro"].get(tok)))

    i = so.index(u"function radaiFilaCard(")
    card = so[i:so.index(u"function radaiFilaPintar(", i)]
    checar(u"o rotulo do card e `.cd-rot`, e nao `.rot`",
           u'class="cd-rot"' in card and u'class="rot"' not in card)
    checar(u"  e a linha de baixo e `.cd-sub`, e nao `.sub`",
           u'class="cd-sub"' in card and u'class="sub"' not in card)
    checar(u"  e o rotulo fica no fluxo mesmo que alguem declare `.rot` global",
           u".radai-tarefas .cd .cd-rot{position:static" in css)
    checar(u"o card que roda mostra o andamento (task, parte, relogio)",
           u"radaiFilaAndamento(c.andamento)" in card
           and u"function radaiRelogio(" in so)


def _funcao_js(js, nome):
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
                return js[i:j + 1]
    return u""


_FILA_DUBLES_JS = u"""
var ORDEM = [];
var EL = {radai_fila: {innerHTML: '', dataset: {},
                       querySelector: function(){ return null; }}};
var document = {getElementById: function(id){ return EL[id] || null; }};
var window = {radaiRetraduzir: function(){
 ORDEM.push('retraduzir:' + EL.radai_fila.innerHTML.length); }};
function radaiPipePintar(){ ORDEM.push('pipe'); }
function radaiFilaCard(c){ return '<div class="cd">' + c.rotulo + '</div>'; }
"""

_FILA_RODA_JS = u"""
var R = {};
radaiFilaPintar({cards: [], resumo: {}});
R.vazia = ORDEM.slice(); R.vazia_html = EL.radai_fila.innerHTML; ORDEM = [];
EL.radai_fila.innerHTML = '';
radaiFilaPintar({cards: [{rotulo: 'serie 1'}], resumo: {esperando: 1}});
R.cheia = ORDEM.slice();
console.log('JSON:' + JSON.stringify(R));
"""


def teste_a_fila_repintada_chama_o_tradutor():
    secao(u"a fila repintada chama o tradutor, nos dois caminhos")
    import json
    import shutil as _sh
    import subprocess
    node = _sh.which("node")
    if not node:
        checar(u"node disponivel para executar a fila", False,
               u"PULADO -- sem node")
        return
    fontes = [_funcao_js(TF.HTML, n)
              for n in (u"radaiFilaPintar", u"radaiFilaTraduzir",
                        u"radaiFilaManterDetalhe", u"radaiFilaIdDe")]
    checar(u"as funcoes da fila estao na pagina", all(fontes),
           str([bool(f) for f in fontes]))
    if not all(fontes):
        return
    d = tempfile.mkdtemp(prefix="radai_tarefas_js_")
    alvo = os.path.join(d, "fila.js")
    try:
        with open(alvo, "w", encoding="utf-8") as f:
            f.write(_FILA_DUBLES_JS + u"\n".join(fontes) + _FILA_RODA_JS)
        r = subprocess.run([node, alvo], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=60)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    res = None
    for ln in reversed((r.stdout or u"").splitlines()):
        if ln.startswith(u"JSON:"):
            res = json.loads(ln[5:])
            break
    checar(u"a fila executa no node", res is not None,
           ((r.stderr or u"") + (r.stdout or u""))[-200:])
    if res is None:
        return

    def _depois_de_pintar(ordem):
        return any(o.startswith(u"retraduzir:") and int(o.split(u":")[1]) > 0
                   for o in ordem)
    checar(u"fila VAZIA: o tradutor passa depois de a frase ser pintada",
           u"data-radai-frase" in res["vazia_html"]
           and _depois_de_pintar(res["vazia"]), str(res["vazia"]))
    checar(u"fila com card: o tradutor passa depois de pintar os cards",
           _depois_de_pintar(res["cheia"]), str(res["cheia"]))


def _vars_do_card():
    import re as _re
    return u"\n".join(_re.findall(
        r"(?ms)^var RADAI_FILA_(?:ORIGEM|TAG_DO_ESTADO)\b.*?;[ \t]*$",
        TF.HTML)) + u"\n"


_CARD_TURNO_DUBLES_JS = u"""
var RADAI_FILA_TIPO = {overnight: {icone: 'L', tag: 'turno', cls: 'overnight'},
                       serie: {icone: 'S', tag: '', cls: ''}};
function radaiFilaAndamento(){ return '' }
function radaiFilaFrase(f){ return f }
"""

_CARD_TURNO_RODA_JS = u"""
var T = function(est, m){ return {tipo: 'overnight', estado: est,
                                   rotulo: 'Turno da noite', motivo: m} };
var R = {feito: radaiFilaCard(T('pronto', 'turno aberto as 22:10'), 0, 1),
         rodando: radaiFilaCard(T('rodando', 'turno aberto as 23:40'), 0, 1),
         falhou: radaiFilaCard(T('falhou', 'o ROOT <b>vazio</b>'), 0, 1),
         espera: radaiFilaCard(T('esperando', 'motivo velho'), 0, 1)};
console.log('JSON:' + JSON.stringify(R));
"""


def teste_o_card_do_turno_diz_o_motivo():
    secao(u"o card do turno diz o motivo (v8.3)")
    fontes = [_funcao_js(TF.HTML, n) for n in (u"radaiTfEsc", u"radaiFilaCard")]
    checar(u"a funcao do card e o escape estao na pagina", all(fontes),
           str([bool(f) for f in fontes]))
    if not all(fontes):
        return
    res, erro = _rodar_ponto(_CARD_TURNO_DUBLES_JS + _vars_do_card()
                             + u"\n".join(fontes) + _CARD_TURNO_RODA_JS)
    checar(u"o card do turno executa no node", res is not None, erro)
    if res is None:
        return
    checar(u"o turno ABERTO diz quando abriu, na linha de baixo do card",
           u'class="cd-motivo"' in res["feito"]
           and u"turno aberto as 22:10" in res["feito"], res["feito"][:240])
    checar(u"o turno RODANDO (aberto agora) diz quando abriu, com o giro",
           u'class="cd-motivo"' in res["rodando"]
           and u"turno aberto as 23:40" in res["rodando"]
           and u"ui-gira" in res["rodando"], res["rodando"][:240])
    checar(u"o turno que FALHOU diz por que, com o texto escapado",
           u"o ROOT &lt;b&gt;vazio&lt;/b&gt;" in res["falhou"]
           and u"<b>vazio" not in res["falhou"], res["falhou"][:240])
    checar(u"  e o card que ainda ESPERA nao mostra motivo nenhum",
           u"motivo velho" not in res["espera"], res["espera"][:240])


_PONTO_DUBLES_JS = u"""
var EVT = {ponto: [], notif: [], som: 0};
function _el(){ return {hidden: false, tabIndex: 0, className: '', scrollTop: 0,
  scrollHeight: 100, clientHeight: 50, _a: {}, html: '',
  style: {setProperty:function(k,v){this[k]=v}},
  setAttribute: function(k, v){ this._a[k] = String(v) },
  getAttribute: function(k){ return (k in this._a) ? this._a[k] : null },
  removeAttribute: function(k){ delete this._a[k] },
  hasAttribute: function(k){ return k in this._a },
  insertAdjacentHTML: function(p, h){ this.html += h },
  classList: {toggle: function(){}, add: function(){}, remove: function(){}}} }
var EL = {radai_tf_log: _el(), radai_tf_pn_l: _el(), radai_tf_pt: _el(),
  radai_tf_ab_log_rot: _el(), radai_tf_ab_fila: _el(), radai_tf_ab_log: _el(),
  radai_tf_reg_fila: _el(), radai_tf_reg_log: _el()};
var _LS = {};
var localStorage = {getItem: function(k){ return (k in _LS) ? _LS[k] : null },
  setItem: function(k, v){ _LS[k] = String(v) }};
var document = {getElementById: function(id){ return EL[id] || null },
  documentElement: {classList: {contains: function(){ return false }}}};
function Notification(t, o){ EVT.notif.push({t: t, body: o.body, tag: o.tag}) }
Notification.permission = 'granted';
var window = {uiPonto: function(a, l){ EVT.ponto.push(l ? 'acende' : 'apaga') },
  Notification: Notification};
function radaiTfEsc(s){ return String(s) }
function radaiSom(){ EVT.som++ }
function radaiFraseNaLingua(f){ return f }
var RADAI_TF_LOG_N = 0, RADAI_TF_LOG_FIM = true;
"""

_PONTO_RODA_JS = u"""
var R = {};
var ERRO = {linhas: [{t: '22:13', nivel: 'erro', txt: 'FALHOU serie ...12345678'}],
            proximo: 3, estado: 'ok'};
radaiTfLogRecebeu(ERRO);
R.primeira = EVT.ponto.slice();
radaiTfLogRecebeu({linhas: [{t: '22:14', nivel: 'info', txt: 'segmentando'}],
                   proximo: 4, estado: 'ok'});
R.info = EVT.ponto.slice();
radaiTfLogRecebeu(ERRO);
R.erro_com_fila = EVT.ponto.slice();
R.nome_aceso = EL.radai_tf_ab_log.getAttribute('aria-label');
R.vida = [EL.radai_tf_pt.getAttribute('role'), EL.radai_tf_pt.getAttribute('aria-label')];
radaiTfAba('log');
R.abriu = EVT.ponto.slice();
R.nome_apagado = EL.radai_tf_ab_log.getAttribute('aria-label');
R.reg_log_oculta = EL.radai_tf_reg_log.hidden;
R.reg_fila_oculta = EL.radai_tf_reg_fila.hidden;
radaiTfLogRecebeu(ERRO);
R.erro_com_log = EVT.ponto.slice();
radaiTfAba('p');
R.p_e_fila = [EL.radai_tf_reg_fila.hidden, EL.radai_tf_reg_log.hidden];

var C = function(uid, est, rot){ return {tipo: 'serie', uid: uid, estado: est,
                                           rotulo: rot} };
radaiAvisosDaFila({cards: [C('11111111', 'esperando', 'ISCA BELTRANO'),
                           C('22222222', 'pronto', 'FANTOMA JOSE')]});
R.partida = EVT.notif.length;
radaiAvisosDaFila({cards: [C('11111111', 'pronto', 'ISCA BELTRANO'),
                           C('22222222', 'pronto', 'FANTOMA JOSE')]});
R.pronta = EVT.notif.slice();
radaiAvisosDaFila({cards: [C('11111111', 'pronto', 'ISCA BELTRANO'),
                           C('33333333', 'falhou', 'FANTOMA ANA')]});
R.falha = EVT.notif.slice(R.pronta.length);
radaiAvisosDaFila({cards: [C('11111111', 'pronto', 'ISCA BELTRANO')]});
R.total = EVT.notif.length;
R.som = EVT.som;
radaiTfAba('log'); radaiTfAba('fila'); radaiTfPontoLog(true,'ok');
R.apenas_ok = [EL.radai_tf_ab_log.getAttribute('aria-label'), EL.radai_tf_ab_log_rot.style['--ui-ponto-cor']];
radaiTfPontoLog(true,'erro');
R.mistos = [EL.radai_tf_ab_log.getAttribute('aria-label'), EL.radai_tf_ab_log_rot.style['--ui-ponto-cor']];
console.log('JSON:' + JSON.stringify(R));
"""


def _rodar_ponto(js):
    import json
    import shutil as _sh
    import subprocess
    node = _sh.which("node")
    if not node:
        return None, u"PULADO -- sem node"
    d = tempfile.mkdtemp(prefix="radai_tarefas_js_")
    alvo = os.path.join(d, "ponto.js")
    try:
        with open(alvo, "w", encoding="utf-8") as f:
            f.write(js)
        r = subprocess.run([node, alvo], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=60)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    for ln in reversed((r.stdout or u"").splitlines()):
        if ln.startswith(u"JSON:"):
            return json.loads(ln[5:]), u""
    return None, ((r.stderr or u"") + (r.stdout or u""))[-300:]


def teste_o_ponto_vermelho_e_os_avisos():
    secao(u"o ponto vermelho da aba Log e os avisos de serie")
    fontes = [_funcao_js(TF.HTML, n) for n in
              (u"radaiTfPontoLog", u"radaiTfLogRecebeu", u"radaiTfAba",
               u"radaiAvisosDaFila", u"radaiAvisar", u"radaiTfRecolhida",
               u"radaiTfPontoFila")]
    checar(u"as sete funcoes estao na barra", all(fontes),
           str([bool(f) for f in fontes]))
    if not all(fontes):
        return
    import re as _re
    vars_js = u"\n".join(_re.findall(
        r"(?ms)^var RADAI_(?:TF_ABA|TF_ABAS|TF_LOG_(?:PRIMEIRA|AVISOS)|TF_FORA|AVISO_[A-Z]+)\b.*?;[ \t]*$",
        TF.HTML)) + u"\n"
    js = _PONTO_DUBLES_JS + vars_js + u"\n".join(fontes) + _PONTO_RODA_JS
    res, erro = _rodar_ponto(js)
    if erro.startswith(u"PULADO"):
        checar(u"node disponivel para executar o ponto", False, erro)
        return
    checar(u"o ponto e os avisos executam no node", res is not None, erro)
    if res is None:
        return
    checar(u"a primeira volta (a historia) NAO acende o ponto",
           res["primeira"] == [], str(res["primeira"]))
    checar(u"  e linha que nao e erro tambem nao", res["info"] == [],
           str(res["info"]))
    checar(u"a linha de erro que CHEGA com a aba Fila aberta acende",
           res["erro_com_fila"] == [u"acende"], str(res["erro_com_fila"]))
    checar(u"  e abrir a aba Log apaga",
           res["abriu"] == [u"acende", u"apaga"], str(res["abriu"]))
    checar(u"  com o ponto aceso, a aba se chama «Log — erro novo» (o ponto "
           u"e so cor, e o leitor de tela precisa do nome)",
           res.get("nome_aceso") == u"Log — erro novo", str(res.get("nome_aceso")))
    checar(u"  e apagado, o nome volta ao do texto da aba",
           res.get("nome_apagado") is None, str(res.get("nome_apagado")))
    checar(u"  e o ponto de vida do vigia tem nome (role=img)",
           res.get("vida") == [u"img", u"o vigia está rodando"], str(res.get("vida")))
    checar(u"  e abrir o Log mostra a regiao dele e esconde a da Fila",
           res["reg_log_oculta"] is False and res["reg_fila_oculta"] is True)
    checar(u"  e erro com a aba Log aberta nao acende de novo",
           res["erro_com_log"] == res["abriu"], str(res["erro_com_log"]))
    checar(u"`radaiTfAba('p')` (o nome antigo) volta para a Fila",
           res["p_e_fila"] == [False, True], str(res["p_e_fila"]))
    checar(u"o retrato de partida da fila nao avisa nada",
           res["partida"] == 0, str(res["partida"]))
    pronta = res["pronta"]
    checar(u"a serie que passou a `pronto` avisa UMA vez",
           len(pronta) == 1 and u"11111111" in pronta[0]["body"]
           and u"pronta para o TPS" in pronta[0]["body"], str(pronta))
    checar(u"a que falhou avisa, com o caminho para o Log",
           len(res["falha"]) == 1 and u"33333333" in res["falha"][0]["body"]
           and u"aba Log" in res["falha"][0]["body"], str(res["falha"]))
    _corpos = u" ".join(n["body"] for n in pronta + res["falha"])
    checar(u"nenhum aviso leva o NOME do paciente (o rotulo do card)",
           u"ISCA" not in _corpos and u"FANTOMA" not in _corpos, _corpos)
    checar(u"o estado repetido nao avisa de novo", res["total"] == 2,
           str(res["total"]))
    checar(u"  e cada aviso tocou o som", res["som"] == 2, str(res["som"]))

    checar(u"so conclusao acende verde, com nome proprio para o leitor de tela",
           res["apenas_ok"][0] == u"Log — conclusão nova" and u"success" in res["apenas_ok"][1])
    checar(u"erro e conclusao juntos acendem amarelo",
           res["mistos"][0] == u"Log — erros e conclusões novos" and u"warn" in res["mistos"][1])
    guarda = u"!RADAI_TF_LOG_PRIMEIRA && "
    r1, e1 = _rodar_ponto(js.replace(guarda, u""))
    checar(u"  (isca) sem a guarda da primeira volta, a historia acende -- "
           u"a checagem discrimina",
           guarda in js and r1 is not None and r1["primeira"] == [u"acende"],
           e1 or str((r1 or {}).get("primeira")))
    nomeia = _re.search(r"ab\.setAttribute\('aria-label', RADAI_TF_LOG_AVISOS\.erro.*?;", TF.HTML, _re.S).group(0)
    r3, e3 = _rodar_ponto(js.replace(nomeia, u"void 0;"))
    checar(u"  (isca) sem dar nome a aba, o ponto aceso fica mudo para o leitor "
           u"de tela -- a checagem discrimina",
           nomeia in js and r3 is not None and r3.get("nome_aceso") is None,
           e3 or str((r3 or {}).get("nome_aceso")))
    uid_no_corpo = u"'…' + uid + ' · ' + frase"
    corpo_isca = js.replace(u"radaiAvisar(tipo, u);",
                            u"radaiAvisar(tipo, (L.filter(function(c){"
                            u" return c.uid === u })[0] || {}).rotulo);")
    r2, e2 = _rodar_ponto(corpo_isca)
    _c2 = u" ".join(n["body"] for n in (r2 or {}).get("pronta", []))
    checar(u"  (isca) com o rotulo no lugar do UID, o nome chega ao aviso -- "
           u"a checagem discrimina",
           uid_no_corpo in js and u"ISCA" in _c2, e2 or _c2)


_PONTO_FILA_DUBLES_JS = u"""
var PONTOS = [], CLS = {};
function _el2(id){ return {id: id, _a: {},
  setAttribute: function(k, v){ this._a[k] = String(v) },
  removeAttribute: function(k){ delete this._a[k] }} }
var EL = {radai_tf_ic_fila: _el2('ic'), radai_tf_ab_fila: _el2('ab')};
var document = {getElementById: function(id){ return EL[id] || null },
  documentElement: {classList: {contains: function(c){ return !!CLS[c] }}}};
var window = {uiPonto: function(a, l){ PONTOS.push(a.id + (l ? '+' : '-')) }};
"""

_PONTO_FILA_RODA_JS = u"""
var R = {};
CLS = {'dir-fechando': true};
radaiTfPontoFila(true);
R.fechando = PONTOS.slice();
CLS = {'dir-recolhida': true};
radaiTfPontoFila();
R.recolhida = PONTOS.slice();
CLS = {};
radaiTfPontoFila();
R.aberta = PONTOS.slice();
CLS = {'dir-abrindo': true};
radaiTfPontoFila();
R.abrindo = PONTOS.slice();
console.log('JSON:' + JSON.stringify(R));
"""


def teste_o_ponto_da_fila_com_a_barra_fechando():
    secao(u"o ponto da fila com a barra que anima para fechar")
    fontes = [_funcao_js(TF.HTML, n) for n in
              (u"radaiTfRecolhida", u"radaiTfPontoFila")]
    checar(u"as duas funcoes estao na barra", all(fontes),
           str([bool(f) for f in fontes]))
    if not all(fontes):
        return
    import re as _re
    vars_js = u"\n".join(_re.findall(
        r"(?ms)^var RADAI_(?:TF_ABA|TF_FORA)\b.*?;[ \t]*$", TF.HTML)) + u"\n"
    js = _PONTO_FILA_DUBLES_JS + vars_js + u"\n".join(fontes) + _PONTO_FILA_RODA_JS
    res, erro = _rodar_ponto(js)
    if erro.startswith(u"PULADO"):
        checar(u"node disponivel para executar o ponto da fila", False, erro)
        return
    checar(u"o ponto da fila executa no node", res is not None, erro)
    if res is None:
        return
    checar(u"serie fora da fila com a barra em dir-fechando (os 350 ms do "
           u"panel reveal) acende o ponto no icone, e nao espera o fim",
           res["fechando"] == [u"ic+"], str(res["fechando"]))
    checar(u"  e no fim da animacao (dir-recolhida) nada pisca",
           res["recolhida"] == [u"ic+"], str(res["recolhida"]))
    checar(u"  com a barra aberta na aba Fila, o ponto apaga",
           res["aberta"] == [u"ic+", u"ic-"], str(res["aberta"]))
    checar(u"  e abrindo (dir-abrindo) conta como aberta",
           res["abrindo"] == res["aberta"], str(res["abrindo"]))
    certo = u"c.contains('dir-recolhida') || c.contains('dir-fechando')"
    r1, e1 = _rodar_ponto(js.replace(certo, u"c.contains('dir-recolhida')"))
    checar(u"  (isca) olhando so dir-recolhida, a serie que chega durante o "
           u"fechamento nao acende -- a checagem discrimina",
           certo in js and r1 is not None and r1["fechando"] == [],
           e1 or str((r1 or {}).get("fechando")))


_CARD_CONCLUIDA_RODA_JS = u"""
var S = function(est, jc){ var c = {tipo: 'serie', estado: est, uid: '12345678',
                                    rotulo: 'ISCA BELTRANO'};
                           if(jc) c.ja_concluida = true; return c };
var R = {concluida: radaiFilaCard(S('pronto', true), 0, 1),
         feita: radaiFilaCard(S('pronto', false), 0, 1)};
radaiAvisosDaFila({cards: [S('esperando', false)]});
radaiAvisosDaFila({cards: [S('pronto', true)]});
R.aviso_concluida = EVT.notif.length;
radaiAvisosDaFila({cards: [{tipo: 'serie', estado: 'esperando', uid: '87654321'}]});
radaiAvisosDaFila({cards: [{tipo: 'serie', estado: 'pronto', uid: '87654321'}]});
R.aviso_feita = EVT.notif.length;
console.log('JSON:' + JSON.stringify(R));
"""


def teste_a_serie_ja_concluida_nao_diz_feito():
    secao(u"a serie ja concluida nao diz feito (revisao da v8.3)")
    nomes = (u"radaiTfEsc", u"radaiFilaCard", u"radaiAvisosDaFila",
             u"radaiAvisar")
    fontes = [_funcao_js(TF.HTML, n) for n in nomes]
    checar(u"as funcoes do card e do aviso estao na pagina", all(fontes),
           str([bool(f) for f in fontes]))
    if not all(fontes):
        return
    import re as _re
    vars_js = u"\n".join(_re.findall(
        r"(?ms)^var RADAI_AVISO_[A-Z]+\b.*?;[ \t]*$", TF.HTML)) + u"\n"
    dubles = _PONTO_DUBLES_JS.replace(
        u"function radaiTfEsc(s){ return String(s) }\n", u"")
    base = (dubles + _CARD_TURNO_DUBLES_JS + _vars_do_card() + vars_js
            + u"var RADAI_TF_ABA = 'fila';\nfunction radaiTfPontoLog(){}\n")
    js = base + u"\n".join(fontes) + _CARD_CONCLUIDA_RODA_JS
    res, erro = _rodar_ponto(js)
    if erro.startswith(u"PULADO"):
        checar(u"node disponivel para executar o card", False, erro)
        return
    checar(u"o card e o aviso executam no node", res is not None, erro)
    if res is None:
        return
    frase = u"já concluída, não refeita"
    checar(u"o card da serie ja concluida diz «%s», com a marca de "
           u"traducao, e nao a tag «feito»" % frase,
           (u"data-radai-frase>%s<" % frase) in res["concluida"]
           and u"data-radai-frase>feito<" not in res["concluida"],
           res["concluida"][:260])
    checar(u"  e a serie feita agora continua dizendo «feito»",
           u"data-radai-frase>feito<" in res["feita"]
           and frase not in res["feita"], res["feita"][:260])
    checar(u"o aviso de serie pronta NAO toca pela ja concluida",
           res["aviso_concluida"] == 0, str(res["aviso_concluida"]))
    checar(u"  e toca pela feita agora", res["aviso_feita"] == 1,
           str(res["aviso_feita"]))

    card = fontes[1]
    guarda_card = u"fim && c.ja_concluida"
    r1, e1 = _rodar_ponto(js.replace(guarda_card, u"fim && false"))
    checar(u"  (isca) sem a condicao do card, ele volta a dizer «feito» -- a "
           u"checagem discrimina", guarda_card in card and r1 is not None
           and u"data-radai-frase>feito<" in r1["concluida"],
           e1 or (r1 or {}).get("concluida", u"")[:200])
    guarda_aviso = u"c.ja_concluida ? '' : "
    r2, e2 = _rodar_ponto(js.replace(guarda_aviso, u""))
    checar(u"  (isca) sem a guarda do aviso, a ja concluida toca -- a "
           u"checagem discrimina", guarda_aviso in fontes[2]
           and r2 is not None and r2["aviso_concluida"] == 1,
           e2 or str((r2 or {}).get("aviso_concluida")))


_CARD_TAGS_RODA_JS = u"""
var S = function(est, extra){ var c = {tipo: 'serie', estado: est,
                                       uid: '12345678', rotulo: 'SILVA'};
                              for(var k in (extra || {})) c[k] = extra[k];
                              return c };
var R = [radaiFilaCard(S('pronto'), 0, 1), radaiFilaCard(S('falhou'), 0, 1),
         radaiFilaCard(S('pronto', {ja_concluida: true}), 0, 1),
         radaiFilaCard(S('pulado', {dono: 'OUTRA'}), 0, 1),
         radaiFilaCard(S('parcial'), 0, 1),
         radaiFilaCard(S('cancelado'), 0, 1),
         radaiFilaCard(S('esperando', {origem: 'vigia'}), 0, 1)];
console.log('JSON:' + JSON.stringify(R));
"""

PENDENTES_DE_TRADUCAO = ()


def _tags_sem_traducao(htmls, dicionario):
    import re as _re
    fora = []
    for h in htmls or ():
        for f in _re.findall(u"data-radai-frase>([^<]+)<", h):
            f = u" ".join(f.split())
            falta = [c for c, d in dicionario.items() if f not in d]
            if falta and f not in fora:
                fora.append(u"%s (%s)" % (f, u",".join(falta)))
    return fora


def teste_as_tags_do_card_tem_traducao():
    secao(u"as tags do card da fila tem traducao (onda 4b)")
    import radai_phrases as FR
    fontes = [_funcao_js(TF.HTML, n) for n in (u"radaiTfEsc", u"radaiFilaCard")]
    if not all(fontes):
        checar(u"o card esta na pagina", False)
        return
    dubles = _PONTO_DUBLES_JS.replace(
        u"function radaiTfEsc(s){ return String(s) }\n", u"")
    js = (dubles + _CARD_TURNO_DUBLES_JS + _vars_do_card()
          + u"\n".join(fontes) + _CARD_TAGS_RODA_JS)
    res, erro = _rodar_ponto(js)
    if erro.startswith(u"PULADO"):
        checar(u"node disponivel para executar o card", False, erro)
        return
    checar(u"o card executa no node", res is not None, erro)
    if not res:
        return
    dic = dict((c, {}) for c in FR.CODIGOS)
    for linha in FR.TABELA:
        pt = FR.normalizar(linha[0])
        for k, cod in enumerate(FR.CODIGOS, start=1):
            alvo = FR.normalizar(linha[k]) if k < len(linha) else u""
            if pt and alvo:
                dic[cod][pt] = alvo
    falta = [f for f in _tags_sem_traducao(res, dic)
             if f.split(u" (")[0] not in PENDENTES_DE_TRADUCAO]
    checar(u"toda tag do card (feito, falhou, ja concluida, pulado, Parcial, "
           u"Vigia) tem traducao nos onze idiomas", not falta,
           u" | ".join(falta))
    ainda = [p for p in PENDENTES_DE_TRADUCAO
             if not any(f.startswith(p + u" (")
                        for f in _tags_sem_traducao(res, dic))]
    checar(u"  e a frase nova que ja ganhou traducao sai da lista de "
           u"pendentes (a lista nao envelhece calada)", not ainda,
           u", ".join(ainda))
    checar(u"  e o card cancelado diz «cancelado» (a pendencia e real)",
           u"data-radai-frase>cancelado<" in res[5], res[5][:200])
    checar(u"  e a do card que terminou e mesmo a «feito» (a medida pegou a "
           u"tag certa)", u"data-radai-frase>feito<" in res[0], res[0][:200])
    sem = dict((c, dict((k, v) for k, v in d.items() if k != u"feito"))
               for c, d in dic.items())
    checar(u"  (isca) sem a entrada «feito» no dicionario, a tag fica em "
           u"portugues -- a checagem discrimina",
           any(x.startswith(u"feito ") for x in _tags_sem_traducao(res, sem)))



def teste_o_iniciar_aceita_turno_sozinho():
    secao(u"INICIAR arma o turno sozinho e o que chegou durante o lote")
    fonte = _funcao_js(TF.HTML, u"radaiPipePintar")
    js = u"""var B={radai_pipe_ini:{},radai_pipe_pau:{},radai_pipe_est:{}};
var document={getElementById:function(id){return B[id]||null}};
var RADAI_PIPE_FRASE='';
""" + fonte + u"""
function medir(rodando,armado,manuais){
 radaiPipePintar({resumo:{total:1,esperando:1,manuais_esperando:manuais},
  lote:{rodando:rodando},cards:[{tipo:'overnight',estado:'esperando',iniciar_pedido:armado}]});
 return B.radai_pipe_ini.disabled;
}
console.log('JSON:'+JSON.stringify([medir(false,false,0),medir(true,false,0),medir(false,true,0),medir(false,true,1),medir(true,true,1)]));
"""
    res, erro = _rodar_ponto(js)
    checar(u"as cinco combinacoes do turno e da fila manual executam",res is not None,erro)
    if res is not None:
        checar(u"turno desarmado habilita Iniciar, inclusive com lote em curso",
               res[:2] == [False,False],repr(res))
        checar(u"turno ja armado e fila vazia nao duplicam o executor",
               res[2] is True and res[4] is True,repr(res))
        checar(u"a fila manual parada continua iniciando normalmente",res[3] is False,repr(res))

def main():
    print("test_todo | barra da direita")
    for t in (teste_vazio_diz_que_esta_vazio, teste_a_fila_de_validacao_saiu,
              teste_costura_na_pagina,
              teste_ligada_ao_menu,
              teste_a_barra_nasce_recolhida_no_html_servido,
              teste_so_biblioteca_padrao,
              teste_as_abas_fila_e_log,
              teste_o_log_le_o_vigia_EM_EXECUCAO,
              teste_todo_cartao_leva_a_algum_lugar,
              teste_os_dois_icones_da_barra_recolhida_dizem_o_nome,
              teste_a_fila_na_altura_inteira_e_os_quatro_botoes,
              teste_a_fila_repintada_chama_o_tradutor,
              teste_o_card_do_turno_diz_o_motivo,
              teste_o_ponto_vermelho_e_os_avisos,
              teste_o_ponto_da_fila_com_a_barra_fechando,
              teste_a_serie_ja_concluida_nao_diz_feito,
              teste_as_tags_do_card_tem_traducao,
              teste_o_iniciar_aceita_turno_sozinho):
        try:
            t()
        except Exception as e:
            import traceback
            checar("%s (excecao inesperada)" % t.__name__, False,
                   "%s: %s" % (type(e).__name__, e))
            traceback.print_exc()
    secao("a bateria nao grava o config da pasta app")
    depois = (os.path.getmtime(_CONFIG_DO_APP)
              if os.path.exists(_CONFIG_DO_APP) else None)
    checar("app/radai_watcher.config continua como estava (o config vai para "
           "RADAI_CONFIG, no temporario da bateria)",
           depois == _CONFIG_DO_APP_ANTES, "%r -> %r" % (_CONFIG_DO_APP_ANTES,
                                                         depois))
    print()
    if FALHAS:
        print("FALHOU: %d de %d checagens" % (FALHAS, OK + FALHAS))
        return 1
    print("OK: %d checagens, todas passaram" % OK)
    return 0


if __name__ == "__main__":
    sys.exit(main())
