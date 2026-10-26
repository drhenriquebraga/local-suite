# -*- coding: utf-8 -*-
import io
import json
import os
import sys
import tempfile
import threading
import time
import traceback

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
APP = os.path.join(RAIZ, "app")
sys.path.insert(0, AQUI)
sys.path.insert(0, APP)

import _cleanup
_cleanup.adotar_prefixo("radai_varrer_")
import _componentes
os.environ["RADAI_CALIB_DIR"] = tempfile.mkdtemp(prefix="radai_varrer_")
_CFG = os.path.join(os.environ["RADAI_CALIB_DIR"], "radai_watcher.config")
io.open(_CFG, "w", encoding="utf-8").write(u"ROOT=\n")
os.environ["RADAI_CONFIG"] = _CFG

_RESULTADOS = []


def checar(nome, condicao, detalhe=""):
    _RESULTADOS.append((nome, bool(condicao), detalhe))
    print(u"  %s  %s%s" % (u"ok   " if condicao else u"FALHA", nome,
                          (u"  [%s]" % detalhe) if (detalhe and not condicao)
                          else u""))


def secao(t):
    print(u"\n─── %s %s" % (t, u"─" * max(0, 66 - len(t))))


def _serie(destino, n=5, pid=u"FANTOMA_V"):
    import make_test_series as M
    from datetime import datetime
    M.escreve_serie(destino, pid, datetime.now(), n)
    return destino


def _envelhecer(pasta, dias):
    t = time.time() - dias * 86400.0
    os.utime(pasta, (t, t))


def _arvore(tmp):
    share = os.path.join(tmp, u"share")
    _serie(os.path.join(share, u"A_NOVA", u"CT"), 5, u"PAC_A")
    _serie(os.path.join(share, u"B_VELHA", u"CT"), 6, u"PAC_B")
    _envelhecer(os.path.join(share, u"B_VELHA", u"CT"), 40)
    return share


def teste_o_filtro_de_data_e_pela_pasta():
    secao(u"o filtro de data lê a data da pasta, sem abrir o DICOM")
    import radai_varrer as V
    tmp = _cleanup.temporaria("radai_varrer_")
    share = _arvore(tmp)
    d7 = V.iniciar("series", share, dias=7, em_segundo_plano=False)
    checar(u"7 dias: só a série da pasta nova (a velha tem DICOM de hoje, "
           u"e a pasta de 40 dias)", d7.get("series") == 1
           and d7.get("fora_da_data") == 1,
           json.dumps({k: d7.get(k) for k in ("series", "fora_da_data",
                                               "erro")}))
    d0 = V.iniciar("series", share, dias=0, em_segundo_plano=False)
    checar(u"todas as datas: as duas", d0.get("series") == 2
           and d0.get("fora_da_data") == 0, str(d0.get("series")))
    d30 = V.iniciar("series", share, dias=30, em_segundo_plano=False)
    checar(u"30 dias: a de 40 continua fora", d30.get("series") == 1)
    d5 = V.iniciar("series", share, dias=5, em_segundo_plano=False)
    checar(u"um valor fora da lista (5) vira o padrão de 7 dias",
           d5.get("dias") == V.DIAS_PADRAO == 7)
    checar(u"a lista do filtro é 1, 3, 7, 30 e todas",
           tuple(V.DIAS_DO_FILTRO) == (1, 3, 7, 30, 0))
    original = V.dentro_da_data
    try:
        V.dentro_da_data = lambda pasta, limite: True
        isca = V.iniciar("series", share, dias=7, em_segundo_plano=False)
    finally:
        V.dentro_da_data = original
    checar(u"  ISCA: sem o corte pela pasta, a velha entra e a checagem "
           u"reprova", isca.get("series") == 2)
    checar(u"pasta que não responde ao stat é lida (não some calada)",
           V.dentro_da_data(os.path.join(tmp, u"nao_existe"), time.time()))


class _UsoLento(object):
    def __init__(self, n, espera, publica=True):
        self.n, self.espera, self.publica = n, espera, publica

    def registrar(self, nome):
        import radai_varrer as V
        estado = self

        def iniciar(job):
            job["dados"] = {"linhas": []}

        def ler(job, pasta, nomes):
            time.sleep(estado.espera)
            job["dados"]["linhas"].append({"uid": pasta, "desc": os.path.basename(pasta)})
            return estado.publica

        def linhas(job):
            return list(job["dados"]["linhas"])
        V.registrar(nome, ler, linhas, iniciar=iniciar, filtra=False)


def _pastas_de_um_arquivo(tmp, n):
    raiz = os.path.join(tmp, u"lento")
    for i in range(n):
        p = os.path.join(raiz, u"p%02d" % i)
        os.makedirs(p)
        io.open(os.path.join(p, u"x.txt"), "w").write(u"x")
    return raiz


def _acompanhar(v, prazo=10.0):
    import radai_varrer as V
    vistos, fim = [], None
    t0 = time.time()
    while time.time() - t0 < prazo:
        d = V.estado(v)
        vistos.append(d.get("series"))
        if d.get("fim"):
            fim = d
            break
        time.sleep(0.04)
    return vistos, fim


def teste_as_series_chegam_aos_poucos():
    secao(u"as séries chegam conforme a pasta é lida")
    import radai_varrer as V
    tmp = _cleanup.temporaria("radai_varrer_")
    raiz = _pastas_de_um_arquivo(tmp, 6)
    _UsoLento(6, 0.12).registrar("teste_lento")
    d = V.iniciar("teste_lento", raiz)
    checar(u"iniciar responde na hora, com a varredura em segundo plano",
           d.get("v") and not d.get("fim"), json.dumps(d)[:120])
    vistos, fim = _acompanhar(d["v"])
    meio = [x for x in vistos if x and 0 < x < 6]
    checar(u"a lista parcial cresce antes do fim (%s)" % sorted(set(vistos)),
           len(set(meio)) >= 2 and fim and fim.get("series") == 6)
    _UsoLento(6, 0.12, publica=False).registrar("teste_so_no_fim")
    d2 = V.iniciar("teste_so_no_fim", raiz)
    v2, f2 = _acompanhar(d2["v"])
    checar(u"  ISCA: quem só publica no fim não mostra lista parcial, e a "
           u"checagem reprova", not [x for x in v2 if x and 0 < x < 6]
           and f2 and f2.get("series") == 6, str(sorted(set(v2))))
    sem = V.estado(d["v"], versao=fim.get("versao"))
    checar(u"a consulta com a versão que já tem não repete as linhas",
           "linhas" not in sem and V.estado(d["v"]).get("linhas"))


def teste_parar_e_os_tetos():
    secao(u"parar, os tetos e a varredura que ninguém pediu")
    import radai_varrer as V
    tmp = _cleanup.temporaria("radai_varrer_")
    raiz = _pastas_de_um_arquivo(tmp, 12)
    _UsoLento(12, 0.15).registrar("teste_parar")
    d = V.iniciar("teste_parar", raiz)
    time.sleep(0.4)
    V.parar(d["v"])
    vistos, fim = _acompanhar(d["v"], prazo=5.0)
    checar(u"parar encerra a varredura com o que achou até ali",
           fim and fim.get("parado") and 0 < fim.get("series") < 12,
           json.dumps({k: (fim or {}).get(k) for k in ("parado", "series")}))
    checar(u"  e diz que foi interrompida",
           fim and V.BUSCA_INTERROMPIDA in (fim.get("avisos") or []))
    _UsoLento(40, 0.2).registrar("teste_empilha")
    raiz2 = _pastas_de_um_arquivo(os.path.join(tmp, u"b"), 40)
    vs = [V.iniciar("teste_empilha", raiz2)["v"] for _ in range(V.TETO_RODANDO + 1)]
    time.sleep(0.3)
    primeira = V.estado(vs[0])
    checar(u"a %da varredura ao mesmo tempo para a mais antiga (clique "
           u"repetido não empilha leitura)" % (V.TETO_RODANDO + 1),
           primeira.get("parado"))
    for v in vs:
        V.parar(v)
    checar(u"busca desconhecida diz que não existe mais",
           V.estado("x" * 32).get("desconhecida"))
    checar(u"sem pasta, recusa", V.iniciar("series", u"").get("erro") == V.SEM_PASTA)
    checar(u"uso desconhecido, recusa",
           V.iniciar("nao_existe", tmp).get("erro") == V.USO_DESCONHECIDO)
    checar(u"pasta que não existe diz que não achou",
           V.iniciar("series", os.path.join(tmp, u"zzz"),
                     em_segundo_plano=False).get("erro") == V.PASTA_NAO_ENCONTRADA)


def teste_cada_serie_chega_com_o_corte_central():
    secao(u"cada série chega com o corte central (a miniatura) sem reler a pasta")
    import radai_varrer as V
    import radai_thumbnail as T
    import radai_dicom as D
    tmp = _cleanup.temporaria("radai_varrer_")
    share = _arvore(tmp)
    d = V.iniciar("series", share, dias=0, em_segundo_plano=False)
    linhas = d.get("linhas") or []
    checar(u"as linhas levam bilhete, e nunca o caminho",
           len(linhas) == 2 and all(x.get("bilhete") for x in linhas)
           and not any("pasta" in x for x in linhas))
    chamadas = []
    original = D.varrer
    try:
        D.varrer = lambda *a, **k: (chamadas.append(a), original(*a, **k))[1]
        dados, info = T.png_central(linhas[0]["bilhete"])
    finally:
        D.varrer = original
    n = int(info.get("cortes") or 0)
    checar(u"a miniatura é o corte central e sai sem nova varredura",
           dados and n in (5, 6) and info.get("corte") == T.central(n)
           and not chamadas, json.dumps({k: info.get(k) for k in ("cortes", "corte")}))

    def so_a_de_6(linha, pasta, s):
        linha["marca_da_tela"] = u"x"
        return int(s.get("cortes") or 0) == 6
    V.registrar_series_de_pasta("teste_da_tela", enriquecer=so_a_de_6)
    e = V.iniciar("teste_da_tela", share, dias=0, em_segundo_plano=False)
    ls = e.get("linhas") or []
    checar(u"a tela que adota a varredura acrescenta o campo dela e tira a série "
           u"que não quer (o enriquecer devolve False)",
           len(ls) == 1 and ls[0].get("cortes") == 6
           and ls[0].get("marca_da_tela") == u"x", json.dumps(ls)[:160])

    import shutil
    dupla = os.path.join(tmp, u"dupla")
    os.makedirs(dupla)
    for k, n in ((u"A", 5), (u"B", 6)):
        solta = _serie(os.path.join(tmp, u"solta_" + k), n)
        for nome in os.listdir(solta):
            shutil.move(os.path.join(solta, nome), os.path.join(dupla, k + u"_" + nome))
    irmas = []

    def anota(linha, pasta, s):
        irmas.append(tuple(sorted(s.get("irmas") or ())))
        return True
    V.registrar_series_de_pasta("teste_das_irmas", enriquecer=anota)
    e = V.iniciar("teste_das_irmas", dupla, dias=0, em_segundo_plano=False)
    uids = tuple(sorted(x.get("uid") for x in e.get("linhas") or ()))
    checar(u"o enriquecer recebe as séries irmãs da mesma pasta (a tela não dá a "
           u"uma série os arquivos da outra)", len(uids) == 2
           and irmas == [uids, uids], json.dumps([uids, irmas])[:200])
    V.registrar_series_de_pasta(
        "teste_do_resolvedor",
        resolver=lambda c: (share, u"") if c == u"APELIDO"
        else (u"", u"recusada pelo resolvedor"))
    r1 = V.iniciar("teste_do_resolvedor", u"APELIDO", dias=0,
                   em_segundo_plano=False)
    r2 = V.iniciar("teste_do_resolvedor", u"OUTRA", dias=0,
                   em_segundo_plano=False)
    checar(u"o resolvedor da tela troca a pasta pedida antes de ler (o .zip "
           u"vira a pasta extraída)", len(r1.get("linhas") or []) == 2
           and not r1.get("erro"), json.dumps(r1)[:160])
    checar(u"  e a recusa dele volta como erro, sem ler nada",
           r2.get("erro") == u"recusada pelo resolvedor" and not r2.get("linhas"),
           json.dumps(r2)[:160])


def teste_as_rotas():
    secao(u"as rotas: tudo por POST, e o mapeamento de unidade")
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import radai_varrer as V
    app = FastAPI()
    V.montar(app)
    cli = TestClient(app)
    tmp = _cleanup.temporaria("radai_varrer_")
    share = _arvore(tmp)
    d = cli.post("/api/varrer/iniciar", json={"uso": "series", "pasta": share,
                                               "dias": 0}).json()
    fim = None
    for _ in range(100):
        fim = cli.post("/api/varrer/estado", json={"v": d.get("v")}).json()
        if fim.get("fim"):
            break
        time.sleep(0.05)
    checar(u"iniciar e consultar pela rota acham as duas séries",
           fim and fim.get("series") == 2, json.dumps(fim)[:160])
    checar(u"caminho não viaja em GET (as rotas não aceitam GET)",
           cli.get("/api/varrer/estado").status_code == 405
           and cli.get("/api/pastas/mapear").status_code == 405)
    antes = [[u"Y:\\"]]

    def letras():
        return antes[0]

    def dialogo_ok():
        antes[0] = [u"Y:\\", u"Z:\\"]
        return 0
    r = V.mapear_unidade(dialogo=dialogo_ok, letras=letras)
    checar(u"mapear: a unidade nova vem na resposta",
           r.get("ok") and r.get("novas") == [u"Z:\\"], json.dumps(r))
    antes[0] = [u"Y:\\"]
    r = V.mapear_unidade(dialogo=lambda: 0xFFFFFFFF, letras=letras)
    checar(u"mapear cancelado diz que nada foi mapeado",
           r.get("cancelado") and r.get("erro") == V.MAPEAMENTO_CANCELADO)
    r = V.mapear_unidade(dialogo=lambda: 1203, letras=letras)
    checar(u"mapear recusado diz o código do Windows",
           not r.get("ok") and u"1203" in (r.get("erro") or u""))
    original = V.mapear_unidade
    try:
        V.mapear_unidade = lambda: {"ok": True, "novas": [u"Q:\\"]}
        rr = cli.post("/api/pastas/mapear", json={}).json()
    finally:
        V.mapear_unidade = original
    checar(u"a rota do mapeamento devolve o que o diálogo fez",
           rr.get("novas") == [u"Q:\\"], json.dumps(rr))


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


_BASE = u"http://varrer.radai.test"


def _pagina(isca=None):
    import radai_ui as U
    corpo = (u'<main style="padding:30px;width:900px">'
             + U.filtro_de_data(u"dd")
             + u'<input id="campo" type="text">' + U.botao_favorita(u"campo")
             + U.area_de_envio(u"zona", imagens=u".png,.jpg")
             + u'<div id="ler"></div><div id="pensa"></div>'
             + u'<span id="troca">antes</span><div id="certo"></div>'
             + u'<div id="vl_est"></div><div id="vl"></div>'
             + u'</main><script>uiEnvio("zona",{url:"/envio"});</script>')
    p = U.aplicar(u'<!doctype html><html><head><meta charset="utf-8"></head>'
                  u'<body>%s</body></html>' % corpo)
    if isca:
        de, para = isca
        checar(u"  (a isca acha o trecho que troca)", de in p, de[:60])
        p = p.replace(de, para)
    return p


def _servir(ctx, paginas, reg):
    from urllib.parse import urlsplit

    def atender(route):
        req = route.request
        c = urlsplit(req.url).path
        corpo = {}
        try:
            corpo = json.loads(req.post_data or u"{}")
        except Exception:
            corpo = {}
        if c in paginas:
            route.fulfill(status=200, content_type=u"text/html; charset=utf-8",
                          body=paginas[c])
            return
        reg.setdefault(c, []).append(corpo)
        if c == u"/api/lote/favorita":
            body = {"favorita": reg.get("_fav", u"")}
        elif c == u"/api/lote/pastas":
            body = ({"unidades": [{"raiz": u"C:\\", "tipo": "fixa", "ok": True}]}
                    if corpo.get("unidades") else {"caminho": corpo.get("caminho") or u"",
                                                   "pai": u"", "pastas": []})
        elif c == u"/api/pastas/mapear":
            body = {"ok": True, "novas": [u"Z:\\"]}
        elif c == u"/api/varrer/iniciar":
            reg["_n"] = 0
            body = {"v": "v1", "fim": False, "series": 0, "pastas": 0,
                    "versao": 0, "linhas": []}
        elif c == u"/api/varrer/estado":
            reg["_n"] = n = reg.get("_n", 0) + 1
            linhas = [{"uid": u"u%d" % i, "desc": u"SERIE %d" % i}
                      for i in range(min(n, 3))]
            fim = n >= 4
            body = {"v": "v1", "fim": fim, "series": len(linhas), "pastas": n,
                    "versao": min(n, 3), "linhas": linhas,
                    "fora_da_data": 2 if fim else 0,
                    "avisos": [], "dias": 7}
        elif c == u"/api/varrer/parar":
            body = {"v": "v1", "fim": True, "parado": True}
        else:
            route.fulfill(status=404, body=u"")
            return
        route.fulfill(status=200, content_type=u"application/json",
                      body=json.dumps(body))
    ctx.route(_BASE + u"/**", atender)


def _medir_pensando(pg):
    pg.evaluate(u"window.__p = uiPensando('pensa'); __p.dizer(['Lendo A', 'Lendo B'])")
    pg.wait_for_timeout(200)
    a = pg.evaluate(u"[__p.linha().textContent, __p.linha().getAttribute('data-t'),"
                    u" getComputedStyle(__p.linha(), '::before').animationName]")
    pg.wait_for_timeout(2300)
    b = pg.evaluate(u"[__p.linha().textContent, document.querySelectorAll("
                    u"'#pensa .ui-pensa-linha').length]")
    pg.evaluate(u"__p.parar()")
    return a, b


def _medir_certo_e_troca(pg):
    cedo = pg.evaluate(u"window.__c = null; uiCerto('certo').then(function(c){ window.__c = c });"
                       u" parseFloat(getComputedStyle(document.querySelector('#certo .ui-certo')).opacity)")
    pg.wait_for_timeout(700)
    tarde = pg.evaluate(u"[parseFloat(getComputedStyle(document.querySelector('#certo .ui-certo')).opacity),"
                        u" parseFloat(getComputedStyle(document.querySelector('#certo path')).strokeDashoffset),"
                        u" !!window.__c]")
    meio = pg.evaluate(u"window.__t = 0; uiTrocarTexto('troca', 'depois').then(function(){ window.__t = 1 });"
                       u" [document.getElementById('troca').className, document.getElementById('troca').textContent]")
    pg.wait_for_timeout(450)
    fim = pg.evaluate(u"[document.getElementById('troca').textContent, window.__t,"
                      u" document.getElementById('troca').className]")
    return cedo, tarde, meio, fim


def _medir_lista(pg, reg):
    pg.evaluate(u"uiVarrerLista({alvo:'vl', estado:'vl_est', pasta:'C:/X', dias:'dd',"
                u" linha:function(s){ return '<div class=\"it\">'+s.desc+'</div>' }})")
    contagens = []
    for _ in range(14):
        pg.wait_for_timeout(160)
        contagens.append(pg.evaluate(u"document.querySelectorAll('#vl .it').length"))
    est = pg.evaluate(u"document.getElementById('vl_est').textContent")
    tem_todas = pg.evaluate(u"!!document.querySelector('#vl_est [data-ui-vl=\"todas\"]')")
    pedido = (reg.get(u"/api/varrer/iniciar") or [{}])[0]
    if tem_todas:
        pg.click(u"#vl_est [data-ui-vl='todas']")
        pg.wait_for_timeout(250)
    de_novo = (reg.get(u"/api/varrer/iniciar") or [{}])[-1]
    dd = pg.evaluate(u"[document.getElementById('dd').value, localStorage.getItem('radai_varrer_dias')]")
    return contagens, est, tem_todas, pedido, de_novo, dd


def _medir_explorador(pg, reg):
    pg.evaluate(u"uiExplorador({})")
    pg.wait_for_timeout(500)
    fav = pg.evaluate(u"[document.querySelector('.ui-fp [data-fp=\"fav\"]').disabled,"
                      u" getComputedStyle(document.querySelector('.ui-fp [data-fp=\"fav\"]')).display]")
    pg.click(u".ui-fp [data-fp='mapear']")
    pg.wait_for_timeout(500)
    mapa = pg.evaluate(u"document.querySelector('.ui-fp-mapa').textContent")
    frescos = [x for x in reg.get(u"/api/lote/pastas") or [] if x.get("fresco")]
    pg.keyboard.press(u"Escape")
    pg.wait_for_timeout(300)
    return fav, mapa, len(reg.get(u"/api/pastas/mapear") or []), len(frescos)


def _medir_envio(pg):
    return pg.evaluate(u"""(function(){
      var z = document.getElementById('zona'), qual = [];
      ['.ui-envio-arq','.ui-envio-dir','.ui-envio-img'].forEach(function(s){
        var i = z.querySelector(s); if(i) i.click = function(){ qual.push(s) } });
      z.querySelector('[data-envio="imagem"]').click();
      z.querySelector('[data-envio="pasta"]').click();
      var img = z.querySelector('.ui-envio-img');
      return [qual, img ? img.getAttribute('accept') : null];
    })()""")


def teste_os_componentes_no_navegador():
    secao(u"thinking-states, success-check, text-states-swap, filtro e lista, num Chromium")
    exe = _chromium()
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        sync_playwright = None
    if not exe or sync_playwright is None:
        print(u"    PULADO o navegador: sem Playwright ou sem Chromium")
        return
    reg = {}
    paginas = {u"/c": _pagina()}
    with sync_playwright() as pw:
        nav = pw.chromium.launch(executable_path=exe, headless=True)
        try:
            ctx = nav.new_context(viewport={"width": 1280, "height": 800},
                                  reduced_motion="no-preference")
            ctx.add_init_script(u"try{ localStorage.setItem('radai_varrer_dias','30') }catch(e){}")
            _servir(ctx, paginas, reg)
            pg = ctx.new_page()
            erros = []
            pg.on("pageerror", lambda e: erros.append(str(e)))
            pg.goto(_BASE + u"/c", wait_until="networkidle")
            dd = pg.evaluate(u"document.getElementById('dd').value")
            checar(u"o filtro abre no valor lembrado pela estação (30)", dd == u"30", dd)
            a, b = _medir_pensando(pg)
            checar(u"thinking-states: a linha e o brilho levam o mesmo texto",
                   a[0] == u"Lendo A" and a[1] == u"Lendo A"
                   and a[2] == u"uiPensaBrilho", str(a))
            checar(u"  e depois de 2 s troca para o estado seguinte, sem sobrar linha",
                   b[0] == u"Lendo B" and b[1] == 1, str(b))
            cedo, tarde, meio, fim = _medir_certo_e_troca(pg)
            checar(u"success-check: nasce transparente e termina inteiro, com o traço desenhado",
                   cedo < 0.6 and tarde[0] > 0.99 and tarde[1] < 0.5 and tarde[2],
                   str((cedo, tarde)))
            checar(u"text-states-swap: o texto velho sai primeiro, o novo entra depois",
                   u"ui-troca-sai" in meio[0] and meio[1] == u"antes"
                   and fim[0] == u"depois" and fim[1] == 1
                   and u"ui-troca-sai" not in fim[2] and u"ui-troca-entra" not in fim[2],
                   str((meio, fim)))
            contagens, est, tem_todas, pedido, de_novo, dd2 = _medir_lista(pg, reg)
            checar(u"a lista cresce a cada consulta (%s)" % contagens,
                   1 in contagens and 2 in contagens and contagens[-1] == 3)
            checar(u"  e pede a varredura com os dias do filtro (30)",
                   pedido.get("dias") == 30, json.dumps(pedido))
            checar(u"  o fim diz quantas pastas ficaram fora e oferece «Ler todas as datas»",
                   tem_todas and u"fora do filtro" in est, est)
            checar(u"  que refaz a varredura sem filtro e a estação passa a lembrar «todas»",
                   de_novo.get("dias") == 0 and dd2 == [u"0", u"0"], str((de_novo, dd2)))
            fav, mapa, n_mapear, n_frescos = _medir_explorador(pg, reg)
            checar(u"explorador: a estrela está sempre lá, apagada sem favorita",
                   fav[0] is True and fav[1] != u"none", str(fav))
            checar(u"  «Mapear nova unidade de rede» chama o servidor e relê as unidades sem cache",
                   n_mapear == 1 and n_frescos >= 1 and u"Z:" in mapa, str((n_mapear, n_frescos, mapa)))
            qual, aceita = _medir_envio(pg)
            checar(u"o quarto botão abre o explorador de imagens (e não o de arquivos)",
                   qual == [u".ui-envio-img", u".ui-envio-dir"]
                   and aceita == u".png,.jpg", str((qual, aceita)))
            reg["_fav"] = u"C:\\EXAMES"
            checar(u"sem erro de JavaScript na página", not erros, u" | ".join(erros)[:200])

            pg2 = ctx.new_page()
            pg2.goto(_BASE + u"/c", wait_until="networkidle")
            pg2.wait_for_timeout(300)
            pg2.click(u".ui-fav")
            pg2.wait_for_timeout(200)
            checar(u"a estrela do campo preenche com a pasta favorita",
                   pg2.evaluate(u"document.getElementById('campo').value") == u"C:\\EXAMES")
            pg2.close()

            ctx2 = nav.new_context(viewport={"width": 1280, "height": 800},
                                   reduced_motion="reduce")
            _servir(ctx2, paginas, reg)
            pc = ctx2.new_page()
            pc.goto(_BASE + u"/c", wait_until="networkidle")
            pc.evaluate(u"window.__p = uiPensando('pensa'); __p.dizer(['A', 'B']);"
                        u" uiCerto('certo'); uiTrocarTexto('troca', 'depois')")
            pc.wait_for_timeout(30)
            calma = pc.evaluate(u"[getComputedStyle(__p.linha()).transitionDuration,"
                                u" getComputedStyle(__p.linha(), '::before').display,"
                                u" parseFloat(getComputedStyle(document.querySelector('#certo .ui-certo')).opacity),"
                                u" document.getElementById('troca').textContent]")
            checar(u"movimento reduzido: sem transição nem brilho, o check já inteiro e o "
                   u"texto trocado na hora (o estado continua legível parado)",
                   calma[0] in (u"0s", u"0s, 0s, 0s") and calma[1] == u"none"
                   and calma[2] > 0.99 and calma[3] == u"depois", str(calma))
            ctx2.close()

            isca = {u"/c": _pagina((u"localStorage.setItem(DIAS_CHAVE, s.value)",
                                    u"void 0"))}
            ctx3 = nav.new_context(viewport={"width": 1280, "height": 800})
            _servir(ctx3, isca, {})
            pi = ctx3.new_page()
            pi.goto(_BASE + u"/c", wait_until="networkidle")
            pi.evaluate(u"uiDias('dd', 3)")
            checar(u"  ISCA: sem gravar a escolha, a estação não lembra, e a checagem reprova",
                   pi.evaluate(u"localStorage.getItem('radai_varrer_dias')") != u"3")
            ctx3.close()
        finally:
            nav.close()


def main():
    testes = [teste_o_filtro_de_data_e_pela_pasta,
              teste_as_series_chegam_aos_poucos,
              teste_parar_e_os_tetos,
              teste_cada_serie_chega_com_o_corte_central,
              teste_as_rotas,
              teste_os_componentes_no_navegador]
    todos = set(k for k, v in globals().items()
                if k.startswith("teste_") and callable(v))
    fora = sorted(todos - set(f.__name__ for f in testes))
    checar("todo teste do arquivo esta na lista do main()", not fora,
           ", ".join(fora))
    for t in testes:
        try:
            t()
        except Exception as e:
            checar("%s (excecao inesperada)" % t.__name__, False,
                   "%s: %s" % (type(e).__name__, e))
            traceback.print_exc()
    falhas = [(n, d) for n, ok, d in _RESULTADOS if not ok]
    print("\n" + "=" * 64)
    if falhas:
        print("FALHOU: %d de %d checagens" % (len(falhas), len(_RESULTADOS)))
        for n, d in falhas:
            print("  - %s%s" % (n, ("  [%s]" % d) if d else ""))
    else:
        print("OK: %d checagens, todas passaram" % len(_RESULTADOS))
    print("=" * 64)
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
