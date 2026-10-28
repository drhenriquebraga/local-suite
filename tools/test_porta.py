# -*- coding: utf-8 -*-
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
APP = os.path.join(RAIZ, "app")
BUILD = os.path.join(RAIZ, "build", "porta")
sys.path.insert(0, APP)
sys.path.insert(0, AQUI)

import _cleanup
_cleanup.adotar_prefixo("radai_ac_porta")
os.environ["RADAI_CALIB_DIR"] = tempfile.mkdtemp(prefix="radai_ac_porta_")

import radai_porta as P
import _componentes

OK = FALHAS = 0

APROVADOS = {
    u"Anton-Regular.ttf":
        u"a4ba3a92350ebb031da0cb47630ac49eb265082ca1bc0450442f4a83ab947cab",
    u"local-suite-vidros-v2.png":
        u"f0c5df68106b9f84321bd6350706cd9ffab1b7fbfad900353ca36894fe7c4e10",
}
RENDERER_APROVADO = u"62ee9cc24715d0ff933e832c6c78facba184a56863754609dea76398dc50f8a0"
LOCKFILE_APROVADO = u"d6419887d9d9ef944a9289f9b979a49e999709bf14cebd72f797fe7a7617143c"
# GUARDA: o porta.js aprovado, fixo aqui; sem node o rebuild pula, e e' este
# hash (e nao o carimbo, que se regrava junto) que prova o arquivo servido.
PORTA_JS_APROVADO = u"0e51fd9dc1d028d337d96b365d6c99627d6541a2b90e27d1d49ccd496921d673"

ORDEM = ((u"bridge", u"/bridge", u"DicomBridge"),
         (u"autocontorno", u"/autocontorno", u"ContourLab"),
         (u"recon3d", u"/recon3d", u"Reconstruções 3D"),
         (u"nidus", u"/nidus", u"Nidus RT"),
         (u"elastic", u"/elastic", u"Elastic RT"),
         (u"bolus", u"/bolus", u"3D Printed Bolus"))
VIDRO = {u"bridge": 0, u"autocontorno": 1, u"recon3d": 2, u"nidus": 3,
         u"elastic": 4, u"bolus": 5}

PROIBIDOS_NO_SCRIPT = (u"8777", u"8788", u"127.0.0.1", u"module-dialog",
                       u"settings-dialog", u"motion-toggle", u"/api/encerrar",
                       u"sendBeacon", u"beforeunload", u"fetch(",
                       u"XMLHttpRequest", u"localStorage", u"setInterval",
                       u"innerHTML", u"eval(")
PAGEHIDE_DO_RENDERER = re.compile(
    r'addEventListener\("pagehide",\(\)=>\{cancelAnimationFrame\(\w+\),\w+=0,\w+=0\}\)')


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


def _sha(dados):
    return hashlib.sha256(dados).hexdigest()


def _ler(caminho):
    with open(caminho, "rb") as f:
        return f.read()


def _sem_script(p):
    return re.sub(r"(?is)<script\b.*?</script>", u"", p)


def _texto(p):
    import html
    t = re.sub(r"(?is)<(script|style)\b.*?</\1>", u" ", p)
    t = re.sub(r"<[^>]+>", u"", t)
    return u" ".join(html.unescape(t).split())


def _porta():
    import radai_router
    return radai_router.montar_porta()


def _controles(m):
    grupo = re.search(r'(?s)<div class="ls-controles">(.*?)</div>\s*</header>', m)
    grupo = grupo.group(1) if grupo else u""
    return [(re.search(r"(data-radai-[a-z]+)(?: hidden)?>", d).group(1), d)
            for d in re.findall(r'(?s)<details class="ls-ctl[^"]*" data-radai-[a-z]+(?: hidden)?>'
                                r'.*?</details>', grupo)]


FRONTEIRA_TXT = _texto(P.FRONTEIRA)


def _arquivos_ok(conteudos, nomes):
    falta = [n for n in APROVADOS if _sha(conteudos.get(n, b"")) != APROVADOS[n]]
    extra = sorted(set(nomes) - set(P.ARQUIVOS))
    ausente = sorted(set(P.ARQUIVOS) - set(nomes))
    return falta, extra, ausente


def teste_os_arquivos():
    secao(u"LND-01: a fonte e a imagem são as aprovadas, e a pasta só tem os três")
    pasta = _componentes.fonte("app/" + P.PASTA)
    nomes = sorted(os.listdir(pasta))
    conteudos = dict((n, _ler(os.path.join(pasta, n))) for n in APROVADOS)
    falta, extra, ausente = _arquivos_ok(conteudos, nomes)
    checar(u"o sha256 da fonte e da imagem bate com o aprovado", not falta, falta)
    checar(u"app/porta tem exatamente porta.js, a fonte e a imagem",
           not extra and not ausente, u"extra=%r ausente=%r" % (extra, ausente))
    checar(u"a lista do servidor tem os três tipos certos",
           P.ARQUIVOS == {u"porta.js": u"application/javascript",
                          u"Anton-Regular.ttf": u"font/ttf",
                          u"local-suite-vidros-v2.png": u"image/png"},
           repr(P.ARQUIVOS))
    isca = dict(conteudos)
    png = bytearray(isca[u"local-suite-vidros-v2.png"])
    png[1000] ^= 0xFF
    isca[u"local-suite-vidros-v2.png"] = bytes(png)
    checar(u"  (isca) um byte trocado na imagem reprova",
           bool(_arquivos_ok(isca, nomes)[0]))
    checar(u"  (isca) um quarto arquivo na pasta reprova",
           bool(_arquivos_ok(conteudos, nomes + [u"notas.txt"])[1]))


def _varrer_script(txt):
    achados = [p for p in PROIBIDOS_NO_SCRIPT if p in txt]
    n = txt.count(u"pagehide")
    if n != 1 or not PAGEHIDE_DO_RENDERER.search(txt):
        achados.append(u"pagehide fora do renderer (%d)" % n)
    if u"unload" in txt:
        achados.append(u"unload")
    return achados


def _hashes_do_build(porta_js=None):
    out = {}
    for n in (u"app.mjs", u"beam-renderer.mjs", u"package-lock.json"):
        out[n] = _sha(_ler(os.path.join(BUILD, n)))
    out[u"porta.js"] = _sha(porta_js if porta_js is not None else
                            _ler(os.path.join(APP, P.PASTA, u"porta.js")))
    return out


def teste_o_carimbo_do_script():
    secao(u"LND-03: o script é o gerado de build/porta, sem demonstração nem rede")
    with io.open(os.path.join(BUILD, u"carimbo.json"), encoding="utf-8") as f:
        carimbo = json.load(f)
    h = _hashes_do_build()
    checar(u"os quatro hashes batem com o carimbo.json", h == carimbo,
           u"%r contra %r" % (h, carimbo))
    checar(u"o renderer da luz é o aprovado (revealGlassDepth intacto)",
           h[u"beam-renderer.mjs"] == RENDERER_APROVADO, h[u"beam-renderer.mjs"])
    checar(u"o lockfile é o do pacote aprovado",
           h[u"package-lock.json"] == LOCKFILE_APROVADO, h[u"package-lock.json"])
    checar(u"o porta.js servido é o aprovado (sha256 fixo, vale sem node)",
           h[u"porta.js"] == PORTA_JS_APROVADO, h[u"porta.js"])
    bruto0 = _ler(os.path.join(APP, P.PASTA, u"porta.js"))
    checar(u"  (isca) porta.js e carimbo regravados juntos não passam pelo hash fixo",
           _sha(bruto0 + b";") != PORTA_JS_APROVADO)
    txt = _ler(os.path.join(APP, P.PASTA, u"porta.js")).decode("utf-8")
    achados = _varrer_script(txt)
    checar(u"o script não tem porta fixa, diálogo de demonstração, encerrar "
           u"nem rede", not achados, repr(achados))
    checar(u"  e traz a profundidade dos vidros", u"destination-out" in txt)
    bruto = _ler(os.path.join(APP, P.PASTA, u"porta.js"))
    checar(u"  (isca) o script editado à mão não bate o carimbo",
           _hashes_do_build(bruto + b"\n")[u"porta.js"] != carimbo[u"porta.js"])
    checar(u"  (isca) o app.js da prévia, com a porta fixa, reprova a varredura",
           bool(_varrer_script(txt + u'l.href=`http://127.0.0.1:8777${r}`')))
    checar(u"  (isca) um pagehide que encerra reprova a varredura",
           bool(_varrer_script(txt + u'addEventListener("pagehide",()=>{})')))
    rend = _ler(os.path.join(BUILD, u"beam-renderer.mjs")).decode("utf-8")
    trocado = rend.replace(u"mask.addColorStop(.73, 'rgba(0,0,0,.32)')",
                           u"mask.addColorStop(.73, 'rgba(0,0,0,.52)')")
    checar(u"  (isca) um stop do gradiente da profundidade trocado muda o hash",
           trocado != rend and _sha(trocado.encode("utf-8")) != RENDERER_APROVADO)
    _rebuild(carimbo)


def _rebuild(carimbo):
    node = shutil.which("node")
    esb = os.path.join(BUILD, "node_modules", "esbuild")
    if not node or not os.path.isdir(esb):
        print(u"    PULADO o rebuild: sem node ou sem build/porta/node_modules "
              u"(o porta.js foi conferido pelo PORTA_JS_APROVADO)")
        return
    tmp = tempfile.mkdtemp(prefix="radai_ac_porta_build_")
    saida = os.path.join(tmp, "porta.js")
    script = (u"require('esbuild').build({entryPoints:[%s],outfile:%s,bundle:true,"
              u"format:'iife',target:['chrome110','edge110'],minify:true,"
              u"legalComments:'none',charset:'utf8'}).catch(e=>{console.error(e);"
              u"process.exit(1)})"
              % (json.dumps(os.path.join(BUILD, "app.mjs")), json.dumps(saida)))
    r = subprocess.run([node, "-e", script], cwd=BUILD, capture_output=True,
                       timeout=120)
    checar(u"refazer o build dá o mesmo porta.js, byte a byte",
           r.returncode == 0 and os.path.isfile(saida)
           and _sha(_ler(saida)) == carimbo[u"porta.js"],
           (r.stderr or b"")[:200])
    shutil.rmtree(tmp, ignore_errors=True)


def _git(cwd, *args):
    return subprocess.run(["git", "-c", "core.excludesFile=", "-c",
                           "core.attributesFile="] + list(args), cwd=cwd,
                          capture_output=True, text=True, timeout=60)


def _perguntar_ao_git(cwd):
    ign = _git(cwd, "check-ignore", "--no-index", "build/porta/node_modules/x")
    att = _git(cwd, "check-attr", "text", "app/porta/porta.js")
    return ign.returncode == 0, att.stdout.strip().endswith(u"unset")


def teste_o_git_guarda_os_bytes():
    secao(u"LND-04: node_modules fora do Git, e os arquivos da porta sem conversão")
    if not shutil.which("git"):
        print(u"    PULADO: sem git")
        return
    tmp = tempfile.mkdtemp(prefix="radai_ac_porta_git_")
    try:
        _git(tmp, "init", "-q")
        for n in (".gitignore", ".gitattributes"):
            shutil.copy(os.path.join(RAIZ, n), os.path.join(tmp, n))
        ign, att = _perguntar_ao_git(tmp)
        checar(u"build/porta/node_modules é ignorado", ign)
        checar(u"app/porta/porta.js tem text unset", att)
        for n, linhas in ((".gitignore", (u"node_modules/",)),
                          (".gitattributes", (u"app/porta/** -text",
                                              u"build/porta/** -text"))):
            with io.open(os.path.join(RAIZ, n), encoding="utf-8") as f:
                t = f.read()
            for l in linhas:
                t = t.replace(l, u"")
            with io.open(os.path.join(tmp, n), "w", encoding="utf-8") as f:
                f.write(t)
        ign, att = _perguntar_ao_git(tmp)
        checar(u"  (isca) sem as linhas, node_modules entraria", not ign)
        checar(u"  (isca) sem as linhas, porta.js seria texto", not att)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _so_rotas_fechadas(caminhos):
    return [c for c in caminhos if c.startswith(u"/porta") and u"{" in c]


def teste_as_rotas_estaticas():
    secao(u"LND-02: uma rota por arquivo, com tipo e ETag, e nada de travessia")
    try:
        from fastapi import FastAPI
        from starlette.testclient import TestClient
    except Exception as e:
        checar(u"cliente de teste disponível", False, u"PULADO -- %s" % e)
        return
    import radai_panel
    app = FastAPI()
    radai_panel.montar(app)
    c = TestClient(app, raise_server_exceptions=False)
    for nome, tipo in sorted(P.ARQUIVOS.items()):
        r = c.get(u"/porta/" + nome)
        checar(u"/porta/%s responde 200, %s, com ETag" % (nome, tipo),
               r.status_code == 200 and r.headers.get("content-type", "")
               .startswith(tipo) and r.headers.get("etag")
               and r.headers.get("cache-control") == "no-cache",
               u"%s %s" % (r.status_code, dict(r.headers)))
    for ruim in (u"/porta/x.py", u"/porta/%2e%2e/radai_watcher.py",
                 u"/porta/..%2fradai_watcher.py", u"/porta/"):
        checar(u"%s dá 404" % ruim, c.get(ruim).status_code == 404)
    rotas = [r.path for r in app.routes if getattr(r, "path", "").startswith("/porta")]
    checar(u"as rotas da porta são exatamente as da lista",
           sorted(rotas) == sorted(u"/porta/" + n for n in P.ARQUIVOS), repr(rotas))
    checar(u"nenhuma rota da porta tem parâmetro de caminho",
           not _so_rotas_fechadas(rotas))
    checar(u"arquivo() recusa nome fora da lista",
           P.arquivo(u"../radai_porta.py") is None and P.arquivo(u"x.py") is None)
    checar(u"  (isca) uma rota com {nome:path} reprova",
           bool(_so_rotas_fechadas(rotas + [u"/porta/{nome:path}"])))
    import radai_router
    orig = P.montar
    try:
        P.montar = lambda app: app
        app2 = FastAPI()
        radai_router.montar(app2)
        r2 = TestClient(app2, raise_server_exceptions=False).get(u"/porta/porta.js")
    finally:
        P.montar = orig
    checar(u"  (isca) sem a chamada em radai_router.montar o script some",
           r2.status_code == 404)


_SELETOR = re.compile(r"([^{}]+)\{")


def _regras_fora_do_escopo(css):
    css = re.sub(r"(?s)/\*.*?\*/", u"", css)
    fora = []
    for m in _SELETOR.finditer(css):
        sel = m.group(1).strip()
        if not sel or sel.startswith(u"@"):
            continue
        if re.fullmatch(r"(from|to|\d+%)(\s*,\s*(from|to|\d+%))*", sel):
            continue
        for s in sel.split(u","):
            if P.ESCOPO not in s:
                fora.append(s.strip())
    return fora


def _folha(p):
    m = re.search(r'(?s)<style id="radai-porta-css">(.*?)</style>', p)
    return m.group(1) if m else u""


def _cartoes_da_porta(p):
    return re.findall(r'(?s)<(a|div) class="ls-card tool-card[^"]*"([^>]*)>(.*?)</\1>',
                      _sem_script(p))


def teste_a_pagina():
    secao(u"LND-05/06: um documento próprio, com a folha escopada")
    p = _porta()
    m = _sem_script(p)
    import radai_router
    checar(u"/ e /suite servem o mesmo corpo (uma função só)",
           radai_router.montar_porta() == p)
    h1 = re.findall(r"(?s)<h1\b.*?</h1>", m)
    checar(u"um só <h1>", len(h1) == 1, repr(h1))
    if h1:
        checar(u"  «Local Suite», com as duas palavras em span",
               _texto(h1[0]) == u"Local Suite"
               and u'<span class="ls-local">Local</span>' in h1[0]
               and u'<span class="ls-grad">Suite</span>' in h1[0], h1[0][:200])
    checar(u"o título da aba é «Local Suite»", u"<title>Local Suite</title>" in p)
    checar(u"a fonte e a imagem com preload absoluto",
           u'href="/porta/Anton-Regular.ttf" as="font"' in p
           and u'href="/porta/local-suite-vidros-v2.png" as="image"' in p)
    folha = _folha(p)
    checar(u"a folha está inline", len(folha) > 2000)
    fora = _regras_fora_do_escopo(folha)
    checar(u"nenhuma regra da folha sai do escopo body[data-tela=\"inicio\"]",
           not fora, repr(fora[:5]))
    checar(u"  e ela anula a casca global", u'html body[data-tela="inicio"]{' in folha
           and u"padding-top:0!important" in folha)
    corpo = re.search(r'html body\[data-tela="inicio"\]\{([^}]*)\}', folha)
    corpo = corpo.group(1) if corpo else u""
    checar(u"  e a página rola em vez de recortar",
           u"overflow-y:auto" in corpo and u"overflow:hidden" not in corpo, corpo)
    checar(u"  (isca) uma regra .tools sem escopo reprova",
           bool(_regras_fora_do_escopo(folha + u".tools{display:grid}")))
    checar(u"o script do desenho, com defer, no fim",
           u'<script defer src="/porta/porta.js"></script>' in p)
    checar(u"sem diálogo de demonstração, sem target nem URL absoluta",
           u"<dialog" not in m and u"target=" not in m
           and not re.search(r'(?:href|src)="https?:', m)
           and u"Abrir no aplicativo" not in m)
    checar(u"  (isca) o <dialog id=\"module-dialog\"> de volta reprova",
           u"<dialog" in _sem_script(p.replace(u"</main>",
                                                u'<dialog id="module-dialog"></dialog></main>')))

    secao(u"LND-06: só o que o autor aprovou fica na porta")
    ausentes = (u"radai-menu-css", u'class="radai-menu', u"radai-tarefas-css",
                u"hm-card", u"hm-grade", u"ui-ajuda", u'href="/procedencia"',
                u"Explorar", u">Abrir<", u"ESCOLHA O M", u"Da imagem ao contorno",
                u"radioterapia.ai<", u'class="rc-topo')
    nua = re.sub(r"(?is)<(script|style|template)\b.*?</\1>", u"", p)
    achados = [a for a in ausentes if a in nua]
    checar(u"sem trilho, sem barra, sem ?, sem Procedência, sem marca duplicada",
           not achados, repr(achados))
    import radai_modules
    mini = radai_modules.pagina_completa(u"autocontorno")
    checar(u"  e a mini-página continua com o ? e as ferramentas",
           u"ui-ajuda" in mini and u"/lote" in mini)
    import radai_menu
    velha = radai_menu.aplicar(p, u"inicio", com_tarefas=False)
    checar(u"  (isca) a porta pelo aplicar com trilho reprova",
           any(a in re.sub(r"(?is)<(script|style|template)\b.*?</\1>", u"", velha)
               for a in ausentes))

    secao(u"LND-07: seis cartões, na ordem aprovada, que navegam")
    cs = _cartoes_da_porta(p)
    hrefs = [re.search(r'href="([^"]*)"', a).group(1) if u"href=" in a else u""
             for _t, a, _c in cs]
    checar(u"os seis href na ordem aprovada",
           hrefs == [r for _k, r, _n in ORDEM], repr(hrefs))
    tools = [re.search(r'data-tool="(\d+)"', a).group(1) for _t, a, _c in cs]
    checar(u"data-tool 0..5", tools == [str(i) for i in range(6)], repr(tools))
    nomes = [_texto(re.search(r'(?s)<span class="ls-nome tool-name"[^>]*>(.*?)</span>',
                              c).group(1)) for _t, _a, c in cs]
    checar(u"os nomes são os da trilha", nomes == [n for _k, _r, n in ORDEM],
           repr(nomes))
    checar(u"cartão é âncora, sem target", all(t == u"a" for t, _a, _c in cs)
           and not any(u"target" in a for _t, a, _c in cs))
    import radai_breadcrumb
    for k, r, n in ORDEM:
        checar(u"  [%s] nome × rota = trilha" % k,
               radai_breadcrumb.ARVORE[k][:2] == (n, r))
    checar(u"MODULOS_HOME tem a ordem aprovada",
           tuple(radai_menu.MODULOS_HOME) == tuple(k for k, _r, _n in ORDEM),
           repr(radai_menu.MODULOS_HOME))
    checar(u"P.cartao: chave inexistente devolve vazio", P.cartao(u"xyz", 0) == u"")
    orig = radai_menu.MODULOS_HOME
    try:
        radai_menu.MODULOS_HOME = (u"autocontorno", u"bridge", u"recon3d",
                                   u"nidus", u"elastic", u"bolus")
        h_isca = [re.search(r'href="([^"]*)"', a).group(1)
                  for _t, a, _c in _cartoes_da_porta(P.pagina())]
    finally:
        radai_menu.MODULOS_HOME = orig
    checar(u"  (isca) a ordem antiga reprova", h_isca != hrefs)
    checar(u"  (isca) target=\"_blank\" num cartão reprova",
           any(u"target" in a for _t, a, _c in _cartoes_da_porta(
               p.replace(u'<a class="ls-card tool-card" href="/bridge"',
                         u'<a class="ls-card tool-card" target="_blank" href="/bridge"'))))
    travado = dict(radai_modules.MODULOS[u"nidus"], estado=u"EM BREVE")
    origm = radai_modules.MODULOS[u"nidus"]
    try:
        radai_modules.MODULOS[u"nidus"] = travado
        t = P.cartao(u"nidus", 3)
    finally:
        radai_modules.MODULOS[u"nidus"] = origm
    checar(u"módulo que não navega sai sem href, com o estado escrito",
           u"href=" not in t and u"EM BREVE" in t and u'data-tool="3"' in t, t[:160])

    secao(u"LND-09: o rodapé com a fronteira e a autoria")
    texto = _texto(p)
    checar(u"a fronteira inteira, UMA vez",
           texto.count(FRONTEIRA_TXT) == 1, FRONTEIRA_TXT)
    checar(u"  e a autoria", u"Por Henrique Braga" in texto)
    rod = re.search(r'(?s)<footer class="ls-rodape">(.*?)</footer>', m)
    rod = rod.group(1) if rod else u""
    checar(u"  as duas no <footer>, visíveis (não em title)",
           FRONTEIRA_TXT in _texto(rod) and u"Henrique Braga" in rod
           and u"title=" not in rod)
    checar(u"  (isca) a frase só num title reprova",
           _texto(p.replace(P.FRONTEIRA, u'<span title="x"></span>')).count(
               FRONTEIRA_TXT) != 1)
    checar(u"FRONTEIRA é constante própria (não o recuo das mini-páginas)",
           P.FRONTEIRA != radai_modules.ALERTA_DA_PORTA)

    secao(u"LND-11: três controles no cabeçalho (minimizar, configurações, power), "
          u"cada um com uma ação")
    topo = re.search(r'(?s)<header class="ls-topo"[^>]*>(.*?)</header>', m)
    checar(u"o cabeçalho tem o nome da raiz para a pilha do Voltar",
           u'<header class="ls-topo" data-radai-tela="Radioterapia.AI Local">' in m)
    topo = topo.group(1) if topo else u""
    ctl = _controles(m)
    checar(u"três <details> no grupo, na ordem minimizar, configurações, power",
           [c[0] for c in ctl] == [u"data-radai-minimizar", u"data-radai-maximizar", u"data-radai-engrenagem",
                                   u"data-radai-power"], repr([c[0] for c in ctl]))
    por = dict(ctl)
    eng = por.get(u"data-radai-engrenagem", u"")
    pwr = por.get(u"data-radai-power", u"")
    mnz = por.get(u"data-radai-minimizar", u"")
    checar(u"a engrenagem tem só /config", u'href="/config"' in eng
           and u"data-radai-encerrar" not in eng, eng[:200])
    checar(u"o power tem só a âncora do Fechar", u"data-radai-encerrar" in pwr
           and u'href="/config"' not in pwr, pwr[:200])
    checar(u"o minimizar tem a ação e a linha da falha, apagada de partida",
           u"data-radai-minimizar-acao" in mnz and u"data-radai-falha hidden" in mnz,
           mnz[:300])
    checar(u"  e ele nasce escondido, até o motor dizer que a janela é a do app",
           u'<details class="ls-ctl" data-radai-minimizar hidden>' in mnz, mnz[:80])
    fora = m
    for _k, c in ctl:
        fora = fora.replace(c, u"")
    checar(u"  e nenhuma das três ações fora do seu controle",
           u'href="/config"' not in fora and u"data-radai-encerrar" not in fora
           and u"data-radai-minimizar-acao" not in fora)
    for chave, rot in ((u"data-radai-minimizar", u"Minimizar"),
                       (u"data-radai-engrenagem", u"Configurações"),
                       (u"data-radai-power", u"Fechar app")):
        s = re.search(r"(?s)<summary\b[^>]*>(.*?)</summary>", por.get(chave, u""))
        s = s.group(1) if s else u""
        checar(u"  o summary de %s é ícone com o nome «%s» para o leitor" % (chave, rot),
               u"<svg" in s and (u'<span class="ls-rot" data-radai-frase>%s</span>' % rot) in s,
               s[:200])
    checar(u"o diálogo do Fechar foi costurado", u'id="rx-veu"' in p)
    velha = m.replace(pwr, u"").replace(
        u'<a href="/config"', u'<span data-radai-encerrar></span><a href="/config"')
    checar(u"  (isca) o Fechar de volta dentro da engrenagem reprova",
           u"data-radai-encerrar" in dict(_controles(velha)).get(
               u"data-radai-engrenagem", u""))
    checar(u"o script dos menus é pequeno, ES5 e sem temporizador",
           u"=>" not in P.JS and u"setInterval" not in P.JS
           and u"setTimeout" not in P.JS and len(P.JS) < 2600, str(len(P.JS)))

    secao(u"os seis nomes dos cards ficam inteiros, sem gradiente")
    import radai_modules
    for _t, a, c in cs:
        k = re.search(r'data-mod="([^"]+)"', a).group(1)
        nome = re.search(r'(?s)<span class="ls-nome tool-name"[^>]*>(.*?)</span>', c)
        nome = nome.group(1) if nome else u""
        checar(u"[%s] nome sem span de gradiente" % k,
               u"data-ls-fim" not in c and u"ls-fim" not in c)
        checar(u"nome continua igual ao da trilha",
               re.sub(r"<[^>]+>", u"", nome) == dict((x,n) for x,_r,n in ORDEM)[k])
    orig = radai_modules.MODULOS[u"nidus"]
    try:
        radai_modules.MODULOS[u"nidus"] = dict(orig, titulo=u"Neuro ")
        t = P.cartao(u"nidus", 3)
    finally:
        radai_modules.MODULOS[u"nidus"] = orig
    checar(u"  (isca) registro que não monta o nome da trilha não parte o nome",
           u"ls-fim" not in t and u">Nidus RT</span>" in t, t[-200:])

    secao(u"LND-21/22: o ícone do Elastic pronto e a cena decorativa")
    el = [c for _t, a, c in cs if u'data-mod="elastic"' in a]
    svg = re.search(r'(?s)<svg class="ls-icone.*?</svg>', el[0]) if el else None
    checar(u"o SVG do Elastic tem 20 <path> no HTML servido",
           bool(svg) and svg.group(0).count(u"<path") == 20)
    checar(u"  (isca) o grupo vazio reprova",
           P.icone(u"bridge").count(u"<path") != 20)
    checar(u"a cena é aria-hidden e sem aria-label",
           re.search(r'<section class="ls-cena" id="scene" aria-hidden="true">', m)
           is not None and u'id="scene" aria-label' not in m)
    checar(u"o <nav> dos cartões é rotulado",
           u'<nav class="ls-cards" aria-label="os módulos da suíte">' in m)


def teste_a_porta_de_reserva():
    secao(u"LND-20: sem radai_porta, a reserva ainda abre e navega")
    import radai_router
    orig = sys.modules.get("radai_porta")
    sys.modules["radai_porta"] = None
    try:
        p = radai_router.montar_porta()
    finally:
        sys.modules["radai_porta"] = orig
    links = re.findall(r'<a href="([^"]+)">', _sem_script(p))
    mods = [l for l in links if l != u"/config"]
    checar(u"a reserva lista os seis, na ordem aprovada",
           mods == [r for _k, r, _n in ORDEM], repr(links))
    checar(u"  e mantém a engrenagem com o Fechar",
           u"data-radai-engrenagem" in p and u"data-radai-encerrar" in p)
    checar(u"TEL-18: a reserva mostra a fronteira clínica, a mesma da porta",
           P.FRONTEIRA in p and _texto(P.FRONTEIRA) in _texto(p),
           _texto(p)[:200])
    import radai_phrases as _F
    chave = _F.normalizar(_texto(P.FRONTEIRA))
    checar(u"  e a frase tem chave (se traduz na reserva também)",
           bool(_F.construir()["en"].get(chave)), chave)


_BASE = u"http://porta.radai.test"


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


def _mini(chave):
    import radai_menu
    import radai_modules
    return radai_menu.aplicar(radai_modules.pagina_completa(chave), chave,
                              com_tarefas=False)


def _simples(chave):
    import radai_menu
    return radai_menu.aplicar(
        u'<!doctype html><html><head><meta charset="utf-8"><title>x</title>'
        u'</head><body><main><p>%s</p></main></body></html>' % chave,
        chave, com_tarefas=False)


def _paginas():
    p = _porta()
    pg = {u"/": p, u"/suite": p}
    for k, r, _n in ORDEM:
        pg[r] = _mini(k)
    pg[u"/config"] = _simples(u"config")
    pg[u"/lote"] = _simples(u"lote")
    return pg


def _servir(ctx, paginas, reg, sem=()):
    from urllib.parse import urlsplit
    import radai_languages as I

    def atender(route):
        c = urlsplit(route.request.url).path
        reg.setdefault("pedidos", []).append(c)
        if c in paginas:
            route.fulfill(status=200, content_type=u"text/html; charset=utf-8",
                          body=paginas[c])
        elif c.startswith(u"/porta/"):
            a = None if c[7:] in sem else P.arquivo(c[7:])
            if a:
                route.fulfill(status=200, content_type=a[1], body=a[0])
            else:
                route.fulfill(status=404, body=u"")
        elif c == u"/radai-idiomas.js":
            route.fulfill(status=200, content_type=u"application/javascript",
                          body=I.corpo_js())
        elif c.startswith(u"/favicon."):
            f = _componentes.fonte("app/" + c[1:])
            if os.path.isfile(f):
                route.fulfill(status=200, body=_ler(f),
                              content_type=u"image/svg+xml" if c.endswith(u"svg")
                              else u"image/png")
            else:
                route.fulfill(status=204, body=u"")
        elif c == u"/api/versao":
            route.fulfill(status=200, content_type=u"application/json",
                          body=u'{"estado":"nunca","nova":false}')
        elif c == u"/api/status":
            route.fulfill(status=200, content_type=u"application/json",
                          body=u'{"ocupado":null,"current":null}')
        elif c == u"/api/pulso":
            route.fulfill(status=200, content_type=u"application/json", body=u"{}")
        elif c == u"/api/janela/estado":
            route.fulfill(status=200, content_type=u"application/json",
                          body=u'{"pid": 4321}')
        elif c == u"/api/janela/registrar":
            route.fulfill(status=200, content_type=u"application/json", body=u'{"ok": true}')
        elif c in (u"/api/atualizar", u"/api/roteiro"):
            route.fulfill(status=200, content_type=u"application/json", body=u"{}")
        elif c == u"/api/encerrar":
            reg["encerrar"] = reg.get("encerrar", 0) + 1
            route.fulfill(status=200, content_type=u"application/json",
                          body=u'{"ok":true}')
        else:
            route.fulfill(status=404, body=u"")
    ctx.route(_BASE + u"/**", atender)


_VIGIA_ENCERRAR = u"""(function(){
 function marca(u){ try{ if(String(u).indexOf('/api/encerrar')>=0){
  var n=+(sessionStorage.getItem('radai_t_encerrar')||0);
  sessionStorage.setItem('radai_t_encerrar',String(n+1)) } }catch(e){} }
 if(navigator.sendBeacon){ var sb=navigator.sendBeacon.bind(navigator);
  navigator.sendBeacon=function(u,d){ marca(u); return sb(u,d) } }
 var f=window.fetch; window.fetch=function(u){ marca(u&&u.url||u);
  return f.apply(this,arguments) };
})();"""


def _tentativas_de_encerrar(pg, reg):
    try:
        n = int(pg.evaluate(u"sessionStorage.getItem('radai_t_encerrar')||0"))
    except Exception:
        n = 0
    return n + reg.get("encerrar", 0)


def _ctx(nav, paginas, reg, larg=1280, alt=720, idioma=u"pt-BR", reduzir=False,
         escala=1, sem=()):
    ctx = nav.new_context(viewport={"width": larg, "height": alt},
                          device_scale_factor=escala, locale=u"pt-BR",
                          reduced_motion=u"reduce" if reduzir else u"no-preference")
    ctx.add_init_script(u"try{localStorage.setItem('radai_idioma','%s')}catch(e){}"
                        % idioma)
    ctx.add_init_script(_VIGIA_ENCERRAR)
    _servir(ctx, paginas, reg, sem)
    return ctx


def _abrir(ctx, rota=u"/", espera=700):
    pg = ctx.new_page()
    pg._radai_erros = []
    pg.on("pageerror", lambda e: pg._radai_erros.append(u"pageerror: %s" % e))
    pg.on("console", lambda m: pg._radai_erros.append(u"%s: %s" % (m.type, m.text))
          if m.type in (u"error", u"warning") else None)
    pg.goto(_BASE + rota, wait_until="networkidle")
    pg.wait_for_timeout(espera)
    return pg


def _com_navegador(fn):
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
            fn(nav)
        finally:
            nav.close()


def _medir_navegacao(nav, paginas):
    reg = {}
    ctx = _ctx(nav, paginas, reg)
    out = []
    try:
        for k, r, _n in ORDEM:
            pg = _abrir(ctx, u"/", 200)
            antes = pg.evaluate(u"history.length")
            pg.click(u'.ls-card[data-mod="%s"]' % k)
            pg.wait_for_load_state("networkidle")
            out.append((k, pg.url.replace(_BASE, u""), pg.evaluate(u"history.length") > antes))
            pg.close()
    finally:
        ctx.close()
    return out


def teste_os_cartoes_navegam():
    secao(u"LND-07: clicar cada cartão abre a mini-página na mesma aba")

    def f(nav):
        pgs = _paginas()
        for k, url, cresceu in _medir_navegacao(nav, pgs):
            rota = dict((a, b) for a, b, _c in ORDEM)[k]
            checar(u"[%s] leva a %s e entra no histórico" % (k, rota),
                   url == rota and cresceu, u"%s %s" % (url, cresceu))
        isca = dict(pgs)
        isca[u"/"] = _como_botoes(pgs[u"/"])
        r = _medir_navegacao(nav, isca)
        checar(u"  (isca) cartões como <button> não navegam",
               all(u == u"/" for _k, u, _c in r), repr(r[:2]))
    _com_navegador(f)


def _como_botoes(p):
    p = re.sub(r'<a class="ls-card tool-card" href="([^"]+)"',
               r'<button type="button" class="ls-card tool-card" data-route="\1"', p)
    return re.sub(r'(<span class="ls-seta"[^>]*>.*?</span>)</a>', r'\1</button>', p,
                  flags=re.S)


def _vidros_acesos(nav, porta):
    reg = {}
    ctx = _ctx(nav, {u"/": porta}, reg)
    out = {}
    try:
        pg = _abrir(ctx)
        for k, _r, _n in ORDEM:
            pg.hover(u'.ls-card[data-mod="%s"]' % k)
            pg.wait_for_timeout(450)
            out[k] = pg.evaluate(u"""(function(){
              var s=document.querySelector('#scene');
              var g=[].slice.call(document.querySelectorAll('[data-glass]'));
              return [s.dataset.activeTool, g.filter(function(x){
                return parseFloat(getComputedStyle(x).opacity)>0.01}).map(function(x){
                return +x.getAttribute('data-glass')})]})()""")
            pg.mouse.move(2, 2)
            pg.wait_for_timeout(250)
    finally:
        ctx.close()
    return out


def teste_cada_cartao_acende_o_seu_vidro():
    secao(u"LND-08: o hover de cada cartão acende só o vidro dele")

    def f(nav):
        p = _porta()
        m = _vidros_acesos(nav, p)
        nomes = dict((k, n) for k, _r, n in ORDEM)
        for k, (ativo, acesos) in sorted(m.items(), key=lambda x: VIDRO[x[0]]):
            checar(u"[%s] acende o vidro %d e só ele" % (k, VIDRO[k]),
                   ativo == nomes[k] and acesos == [VIDRO[k]],
                   u"%r %r" % (ativo, acesos))
        cs = re.findall(r'(?s)<a class="ls-card tool-card".*?</a>', p)
        isca = p.replace(cs[0], u"@@0@@").replace(cs[1], cs[0]).replace(u"@@0@@", cs[1])
        m2 = _vidros_acesos(nav, isca)
        checar(u"  (isca) dois cartões trocados de lugar acendem o vidro errado",
               m2[u"bridge"][1] != [VIDRO[u"bridge"]], repr(m2[u"bridge"]))
    _com_navegador(f)


_MEDIR_RODAPE = u"""(function(){
  var p=document.querySelector('.ls-rodape p'), a=document.querySelector('.ls-autor');
  function vis(e){ if(!e) return false; var r=e.getBoundingClientRect();
    return r.height>0 && r.width>0 && r.top>=0 && r.bottom<=innerHeight+0.5
      && getComputedStyle(e).visibility!=='hidden' }
  return {p:vis(p), a:vis(a), txt:p?p.textContent.trim():'',
          sh:document.documentElement.scrollHeight, ih:innerHeight,
          sw:document.documentElement.scrollWidth, iw:innerWidth,
          eng:(document.querySelector('[data-radai-engrenagem] summary span')||{}).textContent||'',
          x0:document.querySelector('.ls-card[data-tool="0"]').getBoundingClientRect().left,
          x1:document.querySelector('.ls-card[data-tool="1"]').getBoundingClientRect().left,
          oy:getComputedStyle(document.body).overflowY}})()"""

TAMANHOS = ((1280, 720), (1280, 680), (1366, 768), (1440, 900), (1600, 900),
            (1920, 1080), (390, 844))


def teste_o_rodape_a_vista():
    secao(u"LND-09/17: a fronteira e a autoria à vista, sem rolar, nos tamanhos e idiomas")

    def f(nav):
        pgs = {u"/": _porta()}
        for idioma in (u"pt-BR", u"de", u"ar"):
            for (w, h) in TAMANHOS:
                ctx = _ctx(nav, pgs, {}, w, h, idioma)
                try:
                    pg = _abrir(ctx, espera=900)
                    r = pg.evaluate(_MEDIR_RODAPE)
                finally:
                    ctx.close()
                checar(u"[%s %dx%d] fronteira e autoria à vista, sem rolagem"
                       % (idioma, w, h),
                       r["p"] and r["a"] and r["sh"] <= r["ih"] + 1
                       and r["sw"] <= r["iw"], repr(r))
                if idioma == u"pt-BR" and (w, h) == (1280, 720):
                    checar(u"  em pt-BR a frase é a do autor", r["txt"] == FRONTEIRA_TXT,
                           r["txt"])
                if idioma == u"de" and (w, h) == (1280, 720):
                    checar(u"  em alemão o rodapé e a engrenagem trocam",
                           u"Unterstützendes Werkzeug" in r["txt"]
                           and r["eng"] == u"Einstellungen", repr(r["txt"][:40]) + r["eng"])
                if idioma == u"ar" and (w, h) == (1280, 720):
                    checar(u"  em árabe o cartão 0 continua à esquerda do 1",
                           r["x0"] < r["x1"], repr((r["x0"], r["x1"])))
        isca = pgs[u"/"].replace(u'<footer class="ls-rodape">',
                                 u'<footer class="ls-rodape" style="display:none">')
        ctx = _ctx(nav, {u"/": isca}, {}, 1280, 720)
        try:
            r = _abrir(ctx).evaluate(_MEDIR_RODAPE)
        finally:
            ctx.close()
        checar(u"  (isca) o rodapé com display:none reprova", not r["p"], repr(r))
        isca = pgs[u"/"].replace(u"</head>",
                                 u'<style>html body[data-tela="inicio"] .ls-cards'
                                 u'{direction:rtl}</style></head>')
        ctx = _ctx(nav, {u"/": isca}, {}, 1280, 720, u"ar")
        try:
            r = _abrir(ctx).evaluate(_MEDIR_RODAPE)
        finally:
            ctx.close()
        checar(u"  (isca) a grade com direction rtl inverte a ordem",
               r["x0"] > r["x1"], repr((r["x0"], r["x1"])))
    _com_navegador(f)


def _alcancavel(r):
    visivel = r["p"] and r["a"]
    rola = r["sh"] > r["ih"] and r["oy"] != u"hidden"
    return (visivel or rola) and r[u"depois"]


def _medir_corte(nav, porta, w, h, escala, idioma):
    ctx = _ctx(nav, {u"/": porta}, {}, w, h, idioma, escala=escala)
    try:
        pg = _abrir(ctx, espera=900)
        r = pg.evaluate(_MEDIR_RODAPE)
        pg.evaluate(u"window.scrollTo(0, document.documentElement.scrollHeight)")
        pg.wait_for_timeout(150)
        r[u"depois"] = pg.evaluate(u"""(function(){
          return ['.ls-rodape p','.ls-autor'].every(function(s){
            var r=document.querySelector(s).getBoundingClientRect();
            return r.bottom<=innerHeight+0.5 && r.top>=0})})()""")
    finally:
        ctx.close()
    return r


def teste_nunca_recorta_a_fronteira():
    secao(u"LND-10: onde não cabe, a página rola e a fronteira continua alcançável")

    def f(nav):
        p = _porta()
        casos = ((1280, 520, 1, u"pt-BR"), (853, 480, 1.5, u"pt-BR"),
                 (801, 360, 1, u"de"), (390, 440, 1, u"de"))
        for (w, h, e, idioma) in casos:
            r = _medir_corte(nav, p, w, h, e, idioma)
            ok = _alcancavel(r)
            checar(u"[%dx%d ×%s %s] a fronteira à vista ou alcançável rolando"
                   % (w, h, e, idioma), ok, repr(r))
        isca = p.replace(u"</head>", u'<style>html body[data-tela="inicio"]'
                                     u'{overflow:hidden!important}</style></head>')
        r = _medir_corte(nav, p, 390, 440, 1, u"de")
        checar(u"  (a isca usa um caso que transborda)", r["sh"] > r["ih"], repr(r))
        r = _medir_corte(nav, isca, 390, 440, 1, u"de")
        checar(u"  (isca) overflow:hidden de volta deixa a fronteira fora",
               not _alcancavel(r), repr(r))
    _com_navegador(f)


def teste_a_engrenagem_e_o_fechar():
    secao(u"LND-11/12: cada controle abre o seu menu, o power abre o diálogo de sempre")

    def f(nav):
        reg = {}
        pgs = _paginas()
        ctx = _ctx(nav, pgs, reg)
        try:
            pg = _abrir(ctx)
            pg.click(u"[data-radai-engrenagem] summary")
            pg.wait_for_timeout(120)
            aberto = pg.evaluate(u"document.querySelector('[data-radai-engrenagem]').open")
            checar(u"o summary abre o menu", aberto is True)
            checar(u"  com Configurações → /config, e aria-expanded acompanha",
                   pg.evaluate(u"!!document.querySelector('[data-radai-engrenagem] "
                               u".ls-menu a[href=\"/config\"]') && document.querySelector("
                               u"'[data-radai-engrenagem] summary').getAttribute("
                               u"'aria-expanded')==='true'"))
            pg.click(u"[data-radai-power] summary")
            pg.wait_for_timeout(120)
            st = pg.evaluate(u"[document.querySelector('[data-radai-engrenagem]').open,"
                             u"document.querySelector('[data-radai-power]').open,"
                             u"document.querySelector('[data-radai-engrenagem] summary')"
                             u".getAttribute('aria-expanded')]")
            checar(u"abrir o power fecha a engrenagem: um menu por vez",
                   st == [False, True, u"false"], repr(st))
            pg.click(u"[data-radai-power] .rx-fechar")
            pg.wait_for_timeout(200)
            st = pg.evaluate(u"[!!document.querySelector('#rx-veu.on'),"
                             u"(document.activeElement||{}).id,"
                             u"document.querySelector('[data-radai-power]').open]")
            checar(u"«Fechar app» abre #rx-veu com o foco no Cancelar, e o menu fica",
                   st == [True, u"rx-cancelar", True], repr(st))
            pg.click(u"#rx-cancelar")
            pg.wait_for_timeout(150)
            st = pg.evaluate(u"[!!document.querySelector('#rx-veu.on'),"
                             u"(document.activeElement||{}).className]")
            checar(u"Cancelar fecha e devolve o foco ao botão",
                   st[0] is False and u"rx-fechar" in (st[1] or u""), repr(st))
            pg.click(u"[data-radai-power] .rx-fechar")
            pg.wait_for_timeout(150)
            pg.keyboard.press(u"Escape")
            pg.wait_for_timeout(100)
            st1 = pg.evaluate(u"[!!document.querySelector('#rx-veu.on'),"
                              u"document.querySelector('[data-radai-power]').open]")
            pg.keyboard.press(u"Escape")
            pg.wait_for_timeout(100)
            st2 = pg.evaluate(u"[document.querySelector('[data-radai-power]').open,"
                              u"(document.activeElement||{}).parentNode"
                              u"=== document.querySelector('[data-radai-power]')]")
            checar(u"Escape fecha o diálogo, depois o menu, e o foco volta ao ícone",
                   st1 == [False, True] and st2 == [False, True], repr((st1, st2)))
            pg.click(u"[data-radai-engrenagem] summary")
            pg.mouse.click(640, 300)
            pg.wait_for_timeout(100)
            checar(u"clique fora fecha o menu",
                   pg.evaluate(u"document.querySelector('[data-radai-engrenagem]').open")
                   is False)
            st = _sair_do_menu_pelo_tab(pg)
            checar(u"TEL-07: sair do menu pelo Tab fecha o menu",
                   st == [False, False], repr(st))
            for k, _r, _n in ORDEM:
                pg.hover(u'.ls-card[data-mod="%s"]' % k)
            pg.click(u'.ls-card[data-mod="nidus"]')
            pg.wait_for_load_state("networkidle")
            pg.go_back(wait_until="networkidle")
            pg.reload(wait_until="networkidle")
            pg.wait_for_timeout(300)
            n = _tentativas_de_encerrar(pg, reg)
        finally:
            ctx.close()
        checar(u"LND-12: navegar, abrir o menu, voltar e recarregar não encerra nada",
               n == 0, repr(n))
        isca = dict(pgs)
        isca[u"/"] = pgs[u"/"].replace(
            u"</body>", u"<script>addEventListener('pagehide',function(){"
                        u"navigator.sendBeacon('/api/encerrar')})</script></body>")
        reg2 = {}
        ctx = _ctx(nav, isca, reg2)
        try:
            pg = _abrir(ctx)
            pg.click(u'.ls-card[data-mod="bolus"]')
            pg.wait_for_load_state("networkidle")
            pg.wait_for_timeout(300)
            n = _tentativas_de_encerrar(pg, reg2)
        finally:
            ctx.close()
        checar(u"  (isca) um pagehide com sendBeacon é contado", n >= 1, repr(n))
        isca = dict(pgs)
        isca[u"/"] = pgs[u"/"].replace(u"m.addEventListener('focusout'",
                                       u"m.addEventListener('x-nada'")
        ctx = _ctx(nav, isca, {})
        try:
            pg = _abrir(ctx)
            st = _sair_do_menu_pelo_tab(pg)
        finally:
            ctx.close()
        checar(u"  (isca) sem o focusout, o menu fica aberto com o foco fora dele",
               isca[u"/"] != pgs[u"/"] and st == [True, False], repr(st))
    _com_navegador(f)


def _minimizar(nav, porta, resposta):
    reg = {}
    pgs = {u"/": porta}
    ctx = _ctx(nav, pgs, reg)

    def janela(route):
        reg.setdefault("janela", []).append(route.request.method)
        if resposta is None:
            route.fulfill(status=404, body=u"")
        else:
            route.fulfill(status=200, content_type=u"application/json",
                          body=json.dumps(resposta))
    ctx.route(_BASE + u"/api/janela/minimizar", janela)
    try:
        pg = _abrir(ctx)
        pg.wait_for_selector(u"[data-radai-minimizar] summary", state="visible", timeout=5000)
        pg.click(u"[data-radai-minimizar] summary")
        pg.wait_for_timeout(100)
        pg.click(u"[data-radai-minimizar-acao]")
        pg.wait_for_timeout(400)
        return reg.get("janela", []), pg.evaluate(
            u"[document.querySelector('[data-radai-minimizar]').open,"
            u"!document.querySelector('[data-radai-falha]').hidden,"
            u"document.querySelector('[data-radai-falha]').getAttribute('role')]")
    finally:
        ctx.close()


def _minimizar_visivel(nav, porta, estado):
    ctx = _ctx(nav, {u"/": porta}, {})
    ctx.route(_BASE + u"/api/janela/estado",
              lambda r: r.fulfill(status=200, content_type=u"application/json",
                                  body=json.dumps(estado)))
    try:
        pg = _abrir(ctx, espera=1800)
        return pg.evaluate(u"(function(){var m=document.querySelector('[data-radai-minimizar]');"
                           u"return [m.hidden, m.getBoundingClientRect().width>0]})()")
    finally:
        ctx.close()


def teste_o_minimizar():
    secao(u"LND-24: o Minimizar pede ao motor e diz quando não conseguiu")

    def f(nav):
        p = _porta()
        checar(u"com a janela do app reconhecida pelo motor, o minimizar aparece",
               _minimizar_visivel(nav, p, {u"pid": 4321}) == [False, True])
        r = _minimizar_visivel(nav, p, {})
        checar(u"sem a janela do app (navegador comum), ele não aparece", r == [True, False],
               repr(r))
        isca = p.replace(u"data-radai-minimizar hidden>", u"data-radai-minimizar>").replace(
            u"document.addEventListener('radai-janela'", u"document.addEventListener('x-isca'")
        r = _minimizar_visivel(nav, isca, {})
        checar(u"  (isca) sem esconder nem ouvir o motor, o botão que não funciona aparece",
               isca != p and r == [False, True], repr(r))
        ped, st = _minimizar(nav, p, {u"ok": True})
        checar(u"um POST em /api/janela/minimizar, e o menu fecha",
               ped == [u"POST"] and st[0] is False and st[1] is False, repr((ped, st)))
        ped, st = _minimizar(nav, p, None)
        checar(u"sem a rota (navegador comum), a falha aparece, como status",
               ped == [u"POST"] and st[0] is True and st[1] is True
               and st[2] == u"status", repr((ped, st)))
        ped, st = _minimizar(nav, p, {u"ok": False})
        checar(u"com ok:false, a falha aparece também", st[1] is True, repr((ped, st)))
        isca = p.replace(u"querySelector('[data-radai-minimizar-acao]')",
                         u"querySelector('[data-x-isca]')")
        ped, st = _minimizar(nav, isca, {u"ok": True})
        checar(u"  (isca) sem o ouvinte, nada é pedido", isca != p and ped == [],
               repr(ped))
    _com_navegador(f)


def _animacao_do_menu(nav, porta, reduzir):
    ctx = _ctx(nav, {u"/": porta}, {}, reduzir=reduzir)
    try:
        pg = _abrir(ctx, espera=300)
        fechado = pg.evaluate(u"getComputedStyle(document.querySelector("
                              u"'[data-radai-engrenagem] .ls-menu')).animationName")
        pg.click(u"[data-radai-engrenagem] summary")
        pg.wait_for_timeout(50)
        aberto = pg.evaluate(u"getComputedStyle(document.querySelector("
                             u"'[data-radai-engrenagem] .ls-menu')).animationName")
        return fechado, aberto
    finally:
        ctx.close()


def teste_o_menu_anima_so_aberto():
    secao(u"LND-25: o mini-menu anima só ao abrir, e nada anima com movimento reduzido")

    def f(nav):
        p = _porta()
        r = _animacao_do_menu(nav, p, False)
        checar(u"fechado sem animação (o varredor de contraste não o lê apagado), "
               u"aberto com a entrada", r == (u"none", u"lsMenu"), repr(r))
        r = _animacao_do_menu(nav, p, True)
        checar(u"com movimento reduzido, nem aberto anima", r == (u"none", u"none"), repr(r))
        isca = p.replace(u'body[data-tela="inicio"] .ls-ctl[open]>.ls-menu{animation:none}',
                         u'body[data-tela="inicio"] .ls-menu{animation:none}')
        r = _animacao_do_menu(nav, isca, True)
        checar(u"  (isca) a regra do reduzido mais fraca que a da entrada deixa animar",
               isca != p and r[1] == u"lsMenu", repr(r))
    _com_navegador(f)


def teste_o_final_do_nome_sobrevive_a_traducao():
    secao(u"a traducao conserva os nomes da home sem inserir gradiente")
    def f(nav):
        p = _porta()
        for idioma, esperado in ((u"en",u"3D reconstructions"),(u"de",u"3D-Rekonstruktionen"),(u"zh-CN",u"三维重建")):
            ctx = _ctx(nav,{u"/":p},{},idioma=idioma)
            try:
                pg = _abrir(ctx,espera=500)
                resultado = pg.evaluate("""(function(){var n=document.querySelector('.ls-card[data-mod="recon3d"] .ls-nome');return [n.textContent,!!n.querySelector('.ls-fim')]})()""")
                checar(u"[%s] nome traduzido inteiro e sem gradiente" % idioma,
                       resultado == [esperado,False],repr(resultado))
            finally: ctx.close()
    _com_navegador(f)


def _sair_do_menu_pelo_tab(pg):
    pg.focus(u"[data-radai-engrenagem] summary")
    pg.keyboard.press(u"Enter")
    pg.wait_for_timeout(100)
    for _ in range(6):
        pg.keyboard.press(u"Tab")
        pg.wait_for_timeout(40)
        if not pg.evaluate(u"document.querySelector('[data-radai-engrenagem]')"
                           u".contains(document.activeElement)"):
            break
    return pg.evaluate(u"[document.querySelector('[data-radai-engrenagem]').open,"
                       u"document.querySelector('[data-radai-engrenagem]')"
                       u".contains(document.activeElement)]")


PERMITIDOS = re.compile(r"^(/|/porta/[A-Za-z0-9.\-]+|/radai-idiomas\.js|/favicon\.\w+"
                        r"|/api/versao|/api/pulso|/api/janela/estado|/api/janela/registrar"
                        r"|/api/atualizar|/api/roteiro)$")


def _pedidos_da_porta(nav, porta):
    reg = {}
    ctx = _ctx(nav, {u"/": porta}, reg)
    try:
        _abrir(ctx, espera=6000)
    finally:
        ctx.close()
    return sorted(set(reg.get("pedidos", [])))


def teste_a_porta_nao_consulta_estado_clinico():
    secao(u"LND-13: os pedidos da porta são só os dela")

    def f(nav):
        p = _porta()
        ped = _pedidos_da_porta(nav, p)
        fora = [x for x in ped if not PERMITIDOS.match(x)]
        checar(u"em 6 s, só /porta/*, idiomas, ícone e versão", not fora,
               repr(ped))
        isca = p.replace(u"</body>", u"<script>fetch('/api/status')</script></body>")
        fora = [x for x in _pedidos_da_porta(nav, isca) if not PERMITIDOS.match(x)]
        checar(u"  (isca) um fetch('/api/status') na porta reprova", bool(fora))
    _com_navegador(f)


def teste_a_porta_entra_na_pilha_do_voltar():
    secao(u"LND-16: /lote → / → /config, e o Voltar de /config aponta para /")

    def medir(nav, pgs):
        ctx = _ctx(nav, pgs, {})
        try:
            pg = _abrir(ctx, u"/lote", 300)
            pg.goto(_BASE + u"/", wait_until="networkidle")
            pg.wait_for_timeout(300)
            pg.goto(_BASE + u"/config", wait_until="networkidle")
            pg.wait_for_timeout(400)
            return pg.evaluate(u"""(function(){var v=document.querySelector('[data-radai-voltar]');
              return v ? [v.getAttribute('href'), v.getAttribute('data-radai-destino')] : null})()""")
        finally:
            ctx.close()

    def f(nav):
        pgs = _paginas()
        r = medir(nav, pgs)
        checar(u"o Voltar de /config é histórico e aponta para /",
               r == [u"/", u"historico"], repr(r))
        isca = dict(pgs)
        isca[u"/"] = pgs[u"/"].replace(u'class="ls-topo" data-radai-tela=', u'class="ls-topo" data-x=')
        r = medir(nav, isca)
        checar(u"  (isca) a porta fora da pilha faz o Voltar apontar para /lote",
               r and r[0] == u"/lote", repr(r))
    _com_navegador(f)


def _medir_movimento(nav, porta, reduzir):
    ctx = _ctx(nav, {u"/": porta}, {}, reduzir=reduzir)
    try:
        pg = _abrir(ctx, espera=900)
        a = pg.evaluate(u"[document.querySelector('#scene').dataset.motion,"
                        u"+document.querySelector('#scene').dataset.beamTick]")
        pg.wait_for_timeout(600)
        b = pg.evaluate(u"+document.querySelector('#scene').dataset.beamTick")
        pg.focus(u'.ls-card[data-mod="recon3d"]')
        pg.wait_for_timeout(200)
        foco = pg.evaluate(u"""(function(){
          var g=document.querySelector('[data-glass="2"]');
          var c=document.querySelector('.ls-card[data-mod="recon3d"]');
          return [parseFloat(getComputedStyle(g).opacity),
                  getComputedStyle(c).transform]})()""")
    finally:
        ctx.close()
    return a[0], a[1], b, foco


def teste_o_movimento_reduzido():
    secao(u"LND-18: movimento reduzido pausa a luz; foco acende o vidro sem transform")

    def f(nav):
        p = _porta()
        mot, t0, t1, foco = _medir_movimento(nav, p, True)
        checar(u"com reduzir: data-motion = paused e o tick parado",
               mot == u"paused" and t0 == t1, repr((mot, t0, t1)))
        checar(u"  o foco acende o vidro, sem transform no cartão",
               foco[0] > 0 and foco[1] in (u"none", u""), repr(foco))
        mot, t0, t1, foco = _medir_movimento(nav, p, False)
        checar(u"sem reduzir: running e o tick sobe", mot == u"running" and t1 > t0,
               repr((mot, t0, t1)))
        checar(u"  o foco por teclado acende o vidro", foco[0] > 0, repr(foco))
        isca = p.replace(
            u'<script defer src="/porta/porta.js">',
            u"<script>(function(){var mm=window.matchMedia;window.matchMedia="
            u"function(q){var r=mm.call(window,q);if(q.indexOf('reduce')>=0)"
            u"return {matches:false,media:q,addEventListener:function(){},"
            u"removeEventListener:function(){}};return r}})()</script>"
            u'<script defer src="/porta/porta.js">')
        mot, t0, t1, _f = _medir_movimento(nav, isca, True)
        checar(u"  (isca) matchMedia forçado: com a emulação o tick sobe",
               t1 > t0, repr((mot, t0, t1)))
    _com_navegador(f)


def _erros_do_console(nav, porta):
    ctx = _ctx(nav, {u"/": porta}, {})
    try:
        pg = _abrir(ctx, espera=600)
        for k, _r, _n in ORDEM:
            pg.hover(u'.ls-card[data-mod="%s"]' % k)
            pg.wait_for_timeout(60)
        pg.wait_for_timeout(300)
        return list(pg._radai_erros)
    finally:
        ctx.close()


def teste_o_console_limpo():
    secao(u"LND-19: sem os controles de demonstração, o console fica limpo")

    def f(nav):
        p = _porta()
        e = _erros_do_console(nav, p)
        checar(u"nenhum erro nem advertência ao carregar e passar o mouse", not e,
               repr(e[:3]))
        isca = p.replace(u"</body>", u"<script>document.querySelector('#motion-toggle')"
                                     u".checked</script></body>")
        e = _erros_do_console(nav, isca)
        checar(u"  (isca) um seletor de demonstração esquecido gera erro na página",
               any(x.startswith(u"pageerror") for x in e), repr(e[:2]))
    _com_navegador(f)


def _sem_o_script(nav, porta):
    pgs = _paginas()
    pgs[u"/"] = porta
    ctx = _ctx(nav, pgs, {}, sem=(u"porta.js",))
    try:
        pg = _abrir(ctx)
        r = pg.evaluate(_MEDIR_RODAPE)
        n = pg.evaluate(u"document.querySelectorAll('.ls-card[href]').length")
        pg.click(u"[data-radai-engrenagem] summary")
        menu = [pg.evaluate(u"document.querySelector('[data-radai-engrenagem]').open")]
        pg.click(u"[data-radai-power] summary")
        menu.append(pg.evaluate(u"!!document.querySelector('[data-radai-power] .rx-fechar')"))
        pg.keyboard.press(u"Escape")
        pg.click(u"[data-radai-power] summary")
        pg.click(u'.ls-card[data-mod="elastic"]')
        pg.wait_for_load_state("networkidle")
        url = pg.url.replace(_BASE, u"")
    finally:
        ctx.close()
    return r, n, menu, url


def teste_a_porta_sem_o_script():
    secao(u"LND-20: sem porta.js, os cartões navegam e a engrenagem funciona")

    def f(nav):
        p = _porta()
        r, n, menu, url = _sem_o_script(nav, p)
        checar(u"seis links clicáveis", n == 6, str(n))
        checar(u"o rodapé à vista", r["p"] and r["a"], repr(r))
        checar(u"a engrenagem abre o menu e o Fechar nasce", menu == [True, True],
               repr(menu))
        checar(u"o clique no cartão navega", url == u"/elastic", url)
        r, n, menu, url = _sem_o_script(nav, _como_botoes(p))
        checar(u"  (isca) cartões como <button> não navegam sem o script",
               url == u"/", url)
    _com_navegador(f)


def _luminancia(rgb):
    def canal(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb[:3]
    return 0.2126 * canal(r) + 0.7152 * canal(g) + 0.0722 * canal(b)


def _contraste(css_cor, fundo=(2, 9, 23)):
    n = [float(x) for x in re.findall(r"[\d.]+", css_cor)]
    if len(n) < 3:
        return 0.0
    a = n[3] if len(n) > 3 else 1.0
    rgb = [n[i] * a + fundo[i] * (1 - a) for i in range(3)]
    l1, l2 = _luminancia(rgb), _luminancia(fundo)
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)


def _cores(nav, porta):
    ctx = _ctx(nav, {u"/": porta}, {})
    try:
        pg = _abrir(ctx)
        return pg.evaluate(u"""(function(){function c(s){var e=document.querySelector(s);
          return e?getComputedStyle(e).color:''}
          return {eng:c('[data-radai-engrenagem] summary'),
                  mnz:c('[data-radai-minimizar] summary'), pwr:c('[data-radai-power] summary'),
                  nome:c('.ls-nome'),
                  rodape:c('.ls-rodape p'), autor:c('.ls-autor')}})()""")
    finally:
        ctx.close()


_MENU_ABERTO = u"""(sel) => {
 function rgba(s){ const m = (s || '').match(/[\\d.]+/g) || [0, 0, 0, 0];
  return [+m[0], +m[1], +m[2], m.length > 3 ? +m[3] : 1] }
 function sobre(a, b){ const k = a[3]; return [a[0]*k + b[0]*(1-k), a[1]*k + b[1]*(1-k),
  a[2]*k + b[2]*(1-k), 1] }
 const e = document.querySelector(sel);
 if(!e || !e.getClientRects().length) return null;
 const camadas = []; let n = e;
 while(n && n.nodeType === 1){ const f = rgba(getComputedStyle(n).backgroundColor);
  if(f[3] > 0) camadas.push(f); if(f[3] >= 1) break; n = n.parentElement }
 let fundo = [2, 9, 23, 1];
 for(let i = camadas.length - 1; i >= 0; i--) fundo = sobre(camadas[i], fundo);
 return {cor: sobre(rgba(getComputedStyle(e).color), fundo).slice(0, 3),
         fundo: fundo.slice(0, 3)};
}"""


def _menus_abertos(nav, porta, tema):
    ctx = _ctx(nav, {u"/": porta}, {})
    ctx.add_init_script(u"try{localStorage.setItem('radai_tema','%s')}catch(e){}" % tema)
    fora = {}
    try:
        pg = _abrir(ctx)
        for ctl, sel in ((u"engrenagem", u"[data-radai-engrenagem] .ls-menu a"),
                         (u"power", u"[data-radai-power] .ls-encerrar button")):
            pg.click(u"[data-radai-%s] > summary" % ctl)
            pg.wait_for_timeout(350)
            fora[ctl] = pg.evaluate(_MENU_ABERTO, sel)
            pg.click(u"[data-radai-%s] > summary" % ctl)
            pg.wait_for_timeout(250)
    finally:
        ctx.close()
    return fora


def _razao(m):
    if not m:
        return 0.0
    l1, l2 = _luminancia(m["cor"]), _luminancia(m["fundo"])
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)


def _vermelho(m):
    r, g, b = (m or {}).get("cor") or (0, 0, 0)
    return r > 180 and r > g * 1.6 and r > b * 1.6


def teste_os_menus_abertos_nos_dois_temas():
    secao(u"os menus abertos da porta passam 4,5:1 nos dois temas, e o FECHAR APP "
          u"continua vermelho")

    def f(nav):
        p = _porta()
        for tema in (u"escuro", u"claro"):
            m = _menus_abertos(nav, p, tema)
            checar(u"[%s] «Configurações» no menu da engrenagem: %.1f:1"
                   % (tema, _razao(m.get(u"engrenagem"))),
                   _razao(m.get(u"engrenagem")) >= 4.5, repr(m.get(u"engrenagem")))
            checar(u"[%s] «FECHAR APP» no menu do power: %.1f:1"
                   % (tema, _razao(m.get(u"power"))),
                   _razao(m.get(u"power")) >= 4.5, repr(m.get(u"power")))
            checar(u"[%s]   e em vermelho" % tema, _vermelho(m.get(u"power")),
                   repr(m.get(u"power")))
        isca = p.replace(u"</head>", u"<style>.ls-suite .ls-menu>a{color:#33415a!important}"
                                     u".ls-suite .ls-encerrar .rx-fechar{color:#5a2a26!important}"
                                     u"</style></head>")
        mi = _menus_abertos(nav, isca, u"escuro")
        checar(u"  (isca) as cores apagadas de antes reprovam nos dois menus",
               _razao(mi.get(u"engrenagem")) < 4.5 and _razao(mi.get(u"power")) < 4.5,
               u"%.2f %.2f" % (_razao(mi.get(u"engrenagem")), _razao(mi.get(u"power"))))
    _com_navegador(f)


def teste_o_contraste():
    secao(u"LND-22: contraste ≥ 4,5:1 sobre o fundo da porta")

    def f(nav):
        p = _porta()
        for k, v in sorted(_cores(nav, p).items()):
            checar(u"%s: %s (%.1f:1)" % (k, v, _contraste(v)), _contraste(v) >= 4.5)
        isca = p.replace(u"</head>", u'<style>html body[data-tela="inicio"] .ls-rodape'
                                     u'{color:#3a4a66}</style></head>')
        checar(u"  (isca) o rodapé em #3a4a66 reprova",
               _contraste(_cores(nav, isca)["rodape"]) < 4.5)
    _com_navegador(f)



def teste_maximizar_restaurar_explicito():
    secao(u"a home so alterna tela cheia por clique, com as setas e nome do estado")
    def f(nav):
        ctx=_ctx(nav,{u"/":_porta()},{})
        try:
            pg=_abrir(ctx,espera=300)
            pg.evaluate("""window.cliquesTela=0;window.tela=false;
             window.radaiJanelaTelaCheia=function(){cliquesTela++;tela=!tela;var d={ok:true,tela_cheia:tela};document.dispatchEvent(new CustomEvent('radai-janela-tela-cheia',{detail:d}));return Promise.resolve(d)};
             document.dispatchEvent(new CustomEvent('radai-janela',{detail:{ok:true}}));""")
            checar(u"sem clique nao pede F11",pg.evaluate('cliquesTela')==0)
            for cheia,rot in ((True,u"Restaurar"),(False,u"Maximizar")):
                pg.locator('[data-radai-maximizar] summary').click()
                pg.locator('[data-radai-maximizar-acao]').click()
                pg.wait_for_timeout(100)
                estado=pg.locator('[data-radai-maximizar]').get_attribute('data-tela-cheia')
                nome=pg.locator('[data-radai-maximizar] summary').inner_text().strip()
                checar(u"apos o clique: %s e setas do estado" % rot,
                       estado==('true' if cheia else 'false') and nome==rot,repr((estado,nome)))
            checar(u"dois cliques fazem duas acoes",pg.evaluate('cliquesTela')==2)
        finally:ctx.close()
    _com_navegador(f)

def main():
    print("test_porta | a porta da suite: a landing Local Suite")
    for t in (teste_os_arquivos, teste_o_carimbo_do_script,
              teste_o_git_guarda_os_bytes, teste_as_rotas_estaticas,
              teste_a_pagina, teste_a_porta_de_reserva,
              teste_os_cartoes_navegam, teste_cada_cartao_acende_o_seu_vidro,
              teste_o_rodape_a_vista, teste_nunca_recorta_a_fronteira,
              teste_a_engrenagem_e_o_fechar,
              teste_a_porta_nao_consulta_estado_clinico,
              teste_a_porta_entra_na_pilha_do_voltar, teste_o_movimento_reduzido,
              teste_o_console_limpo, teste_a_porta_sem_o_script,
              teste_o_contraste, teste_os_menus_abertos_nos_dois_temas,
              teste_o_minimizar, teste_o_menu_anima_so_aberto,
              teste_o_final_do_nome_sobrevive_a_traducao,
              teste_maximizar_restaurar_explicito):
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
