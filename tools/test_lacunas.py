# -*- coding: utf-8 -*-
import ast
import io
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import traceback
import types
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
APP = os.path.join(RAIZ, "app")
sys.path.insert(0, AQUI)
sys.path.insert(0, APP)

import _cleanup
import _componentes
_cleanup.adotar_prefixo("radai_lac_")
_BASE = tempfile.mkdtemp(prefix="radai_lac_")
os.environ["RADAI_CALIB_DIR"] = os.path.join(_BASE, "calib0")
_CFG = os.path.join(_BASE, "radai_watcher.config")
io.open(_CFG, "w", encoding="utf-8").write(u"ROOT=\n")
os.environ["RADAI_CONFIG"] = _CFG

_R = []


def checar(nome, ok, detalhe=u""):
    _R.append((nome, bool(ok), detalhe))
    print(u"  %-6s %s%s" % (u"ok" if ok else u"FALHA", nome,
                            (u"  [%s]" % detalhe) if detalhe and not ok else u""))
    return bool(ok)


def pulado(nome, motivo):
    print(u"  PULADO %s  [%s]" % (nome, motivo))


def secao(t):
    print(u"\n── %s %s" % (t, u"─" * max(0, 64 - len(t))))


def porta_livre():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
    finally:
        s.close()


def _sem_comentario_js(js):
    js = re.sub(r"(?s)/\*.*?\*/", u" ", js)
    return re.sub(r"(?m)^\s*//.*$", u" ", js)


def _funcao(js, nome):
    i = js.index(u"function %s(" % nome)
    j = js.find(u"\nfunction ", i + 10)
    return js[i:j if j > 0 else len(js)]


def _cliente(montar):
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
    app = FastAPI()
    montar(app)
    return TestClient(app)


def _modulo_trocado(nome, de, para):
    fonte = io.open(_componentes.fonte("app/" + nome + ".py"), encoding="utf-8").read()
    assert fonte.count(de) == 1, (nome, de[:50])
    m = types.ModuleType(nome + "_isca")
    m.__file__ = _componentes.fonte("app/" + nome + ".py")
    exec(compile(fonte.replace(de, para), m.__file__, "exec"), m.__dict__)
    return m


def _serie(destino, pid, n=24, dias=1):
    from datetime import datetime, timedelta
    from make_test_series import escreve_serie
    escreve_serie(destino, pid, datetime.now() - timedelta(days=dias), n)
    return destino


def _rotas_registradas():
    vivas = set()
    for nome in _componentes.nomes("app"):
        if nome.endswith(".py"):
            t = io.open(_componentes.fonte("app/" + nome), encoding="utf-8").read()
            vivas.update(re.findall(r'@app\.(?:get|post)\("(/api/[^"]+)"', t))
    return vivas


def _de_outra_trilha_que_existem(dic, vivas):
    return sorted(r for r in dic if r in vivas)


def teste_a_lista_de_outra_trilha():
    secao(u"LAC-01: nenhuma rota que já existe na lista «de outra trilha»")
    fonte = io.open(os.path.join(AQUI, "check_project.py"), encoding="utf-8").read()
    m = re.search(r"\n    de_outra_trilha = (\{.*?\})\n", fonte, re.S)
    dic = ast.literal_eval(m.group(1)) if m else None
    vivas = _rotas_registradas()
    checar(u"a lista existe e nenhuma rota dela já foi registrada",
           dic is not None and not _de_outra_trilha_que_existem(dic, vivas), str(dic))
    checar(u"  e a lógica que reprova a rota que já existe continua lá",
           u"ja_existem = sorted(r for r in de_outra_trilha if r in vivas)" in fonte)
    checar(u"  (isca) com /api/lote/selecao de volta, ela seria acusada",
           _de_outra_trilha_que_existem({"/api/lote/selecao": u"x"}, vivas)
           == ["/api/lote/selecao"])


PAGINA_MINIMA = u"<!doctype html><html><head></head><body><main>x</main></body></html>"


def teste_a_fronteira_mora_com_a_barra():
    secao(u"LAC-03: o diálogo do INICIAR mora onde a barra da direita mora")
    import radai_menu
    import radai_review as R
    import radai_todo
    p = radai_todo.aplicar(PAGINA_MINIMA)
    checar(u"a barra costurada leva o diálogo com a tag da regra 1",
           u'id="radai_rev_fronteira"' in p and R.FRASE_DA_FRONTEIRA in p
           and u"function radaiRevAbrir(" in p and u"function radaiPipe(" in p)
    checar(u"  uma vez só (o /lote, que costurava o seu, não duplica)",
           R.aplicar(p).count(u'id="radai_rev"') == 1)
    for chave in ("ver", "bridge_laudo", "recon3d", "nidus", "lote"):
        q = radai_menu.aplicar(PAGINA_MINIMA, chave)
        if u'id="radai_pipe_ini"' in q:
            checar(u"  [%s] o «Iniciar» da barra vem com o diálogo e a frase" % chave,
                   u'id="radai_rev_fronteira"' in q and R.FRASE_DA_FRONTEIRA in q)
    js = _sem_comentario_js(radai_todo._RESTO)
    pipe = _funcao(js, u"radaiPipe")
    cat = pipe[pipe.index(u".catch("):pipe.index(u"return;", pipe.index(u".catch("))]
    checar(u"o «catch» da conferência abre o diálogo, e não manda iniciar direto",
           u"radaiRevAbrir(null" in cat and re.search(
               r"\.catch\(\s*function\(\)\s*\{\s*radaiPipeMandar", cat) is None, cat[:120])
    ab = _funcao(_sem_comentario_js(R.HTML), u"radaiRevAbrir")
    checar(u"  e o diálogo sem dado abre com a tag e o botão, sem começar",
           u"if(!d){" in ab and u"aoIniciar()" not in ab[ab.index(u"if(!d){"):
                                                       ab.index(u"return;", ab.index(u"if(!d){"))])
    checar(u"  (isca) o «catch» antigo seria acusado", re.search(
        r"\.catch\(\s*function\(\)\s*\{\s*radaiPipeMandar",
        u".catch(function(){ radaiPipeMandar('iniciar') });") is not None)


def teste_esvaziar_e_desta_pasta():
    secao(u"LAC-04: «Esvaziar seleção» tira só as séries da lista à vista")
    import radai_batch as L
    js = _sem_comentario_js(L._pagina())
    esv = _funcao(js, u"esvaziarSelecao")
    checar(u"esvaziar percorre a lista à vista, sem pergunta e sem a faxina inteira",
           u"SERIES" in esv and u"porNoCarrinho(s, false)" in esv
           and u"limparSelecao()" not in esv and u"perguntar(" not in esv, esv[:200])
    env = _funcao(js, u"mandarParaAFila")
    checar(u"  e o envio à fila continua esvaziando o carrinho inteiro",
           u"limparSelecao();" in env)


def teste_o_soltar_e_de_caminho():
    secao(u"LAC-05: o soltar do Rodar agora e do Ver segmentação")
    import radai_release as RL
    js = RL._js()
    checar(u"a área de envio é a do app (`ui-envio`), visível e com a seta",
           u"ui-envio rs-area" in js and u"ui-ico-subir" in js
           and u".ui-envio.rs-area" in RL.CSS)
    checar(u"  sem cor fixa e sem `textContent` para a frase",
           u"#ffc857" not in js and u"nota.textContent" not in js
           and u"window.uiTexto(no, frase)" in js)
    drop = js[js.index(u"alvo.addEventListener('drop'"):]
    drop = drop[:drop.index(u"}, {passive:false});")]
    checar(u"  só o nome: abre o explorador e não escreve o nome no campo",
           u"explorar(el, area)" in drop and u"el.value" not in drop
           and u"usar(el, r.caminho)" in drop)
    checar(u"  e o caminho absoluto continua indo para o campo",
           u"if(r.certeza)" in drop)
    checar(u"  (isca) o soltar antigo, que gravava o nome, seria acusado",
           u"el.value" in u"el.value = r.caminho;")


def teste_a_guarda_do_elastic():
    secao(u"LAC-06: a mistura de sujeitos é dita, e o valor não sai")
    import radai_thumbnail
    import radai_elastic_screen as T
    base = os.path.join(_BASE, "elastic")
    x1 = _serie(os.path.join(base, "PAC_X", "CT1"), u"PAC_X")
    x2 = _serie(os.path.join(base, "PAC_X", "CT2"), u"PAC_X", dias=2)
    y1 = _serie(os.path.join(base, "PAC_Y", "CT"), u"PAC_Y", dias=3)
    ida = T.identidade_da_serie
    checar(u"sujeitos diferentes: verdadeiro", T.sujeitos_diferentes(ida(x1), ida(y1)) is True)
    checar(u"  o mesmo sujeito: falso", T.sujeitos_diferentes(ida(x1), ida(x2)) is False)
    checar(u"  sem identificação legível: não sabe (None)",
           T.sujeitos_diferentes(ida(os.path.join(base, "nada")), ida(x1)) is None)
    c = _cliente(T.montar)
    bx1, bx2, by = (radai_thumbnail.bilhete(p, u"") for p in (x1, x2, y1))
    r1 = c.post("/api/elastic/par", json={"fixa": bx1, "movel": by})
    r2 = c.post("/api/elastic/par", json={"fixa": bx1, "movel": bx2}).json()
    checar(u"a rota diz `sujeitos_diferentes: true` para X × Y",
           r1.json().get("sujeitos_diferentes") is True, r1.text)
    checar(u"  e `false` para as duas de X", r2.get("sujeitos_diferentes") is False, r2)

    def sem_valor(txt):
        return u"PAC_X" not in txt and u"PAC_Y" not in txt
    checar(u"  e a resposta não leva o valor da identificação", sem_valor(r1.text))
    checar(u"  (isca) uma resposta com o PatientID seria acusada",
           not sem_valor(json.dumps({"sujeitos_diferentes": True, "pid": u"PAC_X"})))
    js = T.pagina()
    checar(u"o alerta mora ao lado do «Fundir», com a frase no dicionário",
           u'id="el-sujeitos"' in js and T.SUJEITOS_DIFERENTES in js
           and js.index(u'id="el-fundir"') < js.index(u'id="el-sujeitos"'))
    checar(u"  e o laudo da fusão registra a divergência",
           u"d.sujeitos_diferentes === true" in js and T.SUJEITOS_NO_LAUDO in js
           and u'"sujeitos_diferentes": t.get("sujeitos_diferentes")'
           in io.open(_componentes.fonte("app/radai_elastic_screen.py"), encoding="utf-8").read())


def teste_as_frases_do_elastic():
    secao(u"LAC-07: o que sobrava em português na tela do Elastic")
    import radai_elastic_screen as T
    js = _sem_comentario_js(T.pagina())
    checar(u"a frase de «DUAS séries» saiu com os seletores (os cartões escolhem uma série cada)",
           not hasattr(T, "FALTA_SERIE") and u"São necessárias DUAS séries" not in js)
    ruim = r"(?<!else )el\('el-erro'\)\.textContent\s*=\s*(?!'')"
    achados = re.findall(ruim + r"[^;]*;", js)
    checar(u"  e todo erro de `#el-erro` passa por `uiTexto` (a escrita direta só no recuo sem ela)",
           not achados, u" | ".join(achados))
    checar(u"  (isca) a escrita antiga seria acusada",
           re.search(ruim, u"if(msg){ el('el-erro').textContent = msg }") is not None)
    fonte = io.open(_componentes.fonte("app/radai_elastic_screen.py"), encoding="utf-8").read()
    checar(u"as mensagens do servidor são constantes com chave",
           u'{"erro": ESCOLHA_DUAS}' in fonte and u"FUSAO_EM_ANDAMENTO % " in fonte)


def _cranio_com_vaso_encostado():
    import numpy as np
    import SimpleITK as sitk
    forma = (40, 80, 80)
    z, y, x = np.indices(forma).astype(np.float64)
    r = np.sqrt(((y - 40) * 2) ** 2 + ((x - 40) * 2) ** 2)
    a = np.full(forma, -1000, np.int16)
    a[r < 66] = 40
    casca = (r >= 60) & (r < 66)
    a[casca] = 1200
    tubo = (((z - 20) * 2) ** 2 + ((y - 40) * 2) ** 2 < 9) & (x >= 40) & (r < 60)
    a[tubo] = 350
    img = sitk.GetImageFromArray(a)
    img.SetSpacing((2.0, 2.0, 2.0))
    return img, tubo, r


def teste_a_angiografia_sintetica():
    secao(u"LAC-08: a angiografia sintética, no fantoma")
    import SimpleITK as sitk
    import radai_recon3d_vascular as V
    img, tubo, r = _cranio_com_vaso_encostado()
    sem = sitk.GetArrayFromImage(V.retirar_osso(img))
    longe = tubo & (r < 60 - V.OSSO_MARGEM_MM - 2.0)
    perto = tubo & (r >= 60 - 2.0)
    checar(u"o trecho do vaso a mais de %g mm do osso fica" % V.OSSO_MARGEM_MM,
           longe.any() and bool((sem[longe] == 350).all()), int((sem[longe] != 350).sum()))
    checar(u"  e o trecho encostado no osso sai junto (o que a tela diz)",
           perto.any() and bool((sem[perto] < 350).all()), int((sem[perto] == 350).sum()))
    pag = V.pagina()
    checar(u"o «?» de «mostrar o osso» diz isso em uma frase",
           u'id="vx_osso_aj"' in pag and V.OSSO_E_O_VASO in pag
           and (u"%g mm" % V.OSSO_MARGEM_MM) in V.OSSO_E_O_VASO
           and pag.index(u"mostrar o osso") < pag.index(u'id="vx_osso_aj"'))
    casca = (r >= 60) & (r < 66)
    checar(u"  e a calota sai inteira", bool((sem[casca] < 1200).all()),
           int((sem[casca] == 1200).sum()))
    velho = V.OSSO_HU
    V.OSSO_HU = 3000.0
    try:
        sem3 = sitk.GetArrayFromImage(V.retirar_osso(img))
    finally:
        V.OSSO_HU = velho
    checar(u"  (isca) com o limiar em 3000 HU a calota fica, e a medida reprova",
           bool((sem3[casca] == 1200).any()))


def teste_a_porta_das_baterias():
    secao(u"LAC-13: as baterias de navegador pedem porta livre")
    fonte = io.open(os.path.join(AQUI, "test_ui_interacao.py"), encoding="utf-8").read()
    checar(u"test_ui_interacao não fixa a porta",
           re.search(r"(?m)^PORTA = \d+", fonte) is None and u"PORTA = porta_livre()" in fonte)
    ocupa = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        ocupa.bind(("127.0.0.1", 8813))
        ocupa.listen(1)
        ns = {}
        exec(compile(fonte[fonte.index(u"def porta_livre"):fonte.index(u"PORTA = porta_livre()")],
                     "porta", "exec"), ns)
        p = ns["porta_livre"]()
        checar(u"  com a 8813 ocupada, a porta pedida é outra e está livre", p != 8813, p)
    except OSError:
        pulado(u"a 8813 ocupada", u"a porta já estava em uso por outro processo")
    finally:
        ocupa.close()
    checar(u"  (isca) a porta fixa seria acusada",
           re.search(r"(?m)^PORTA = \d+", u"PORTA = 8813\n") is not None)


def teste_as_frases_tem_os_doze_idiomas():
    secao(u"toda frase nova da trilha nos doze idiomas")
    import radai_elastic_screen as T
    import radai_phrases as P
    import radai_recon3d_vascular as V
    import radai_release as RL
    import radai_review as R
    linhas = dict((P.normalizar(l[0]), l) for l in P.TABELA)
    fr = [R.SEM_CONFERENCIA, RL.SO_O_NOME, RL.TITULO, RL.DICA, RL.RECEBIDO,
          T.SUJEITOS_DIFERENTES,
          T.SUJEITOS_NO_LAUDO, T.ESCOLHA_DUAS, T.FUSAO_EM_ANDAMENTO,
          T.ESCOLHA_A_PASTA, T.BUSCA_AINDA_LENDO,
          u"Esta pasta já está na lista, com o número [%s]. Para varrê-la de novo, "
          u"tire-a da lista antes.", V.OSSO_E_O_VASO]
    falta = []
    for f in fr:
        l = linhas.get(P.normalizar(f))
        sem = [c for i, c in enumerate(P.CODIGOS, start=1)
               if not l or i >= len(l) or not P.normalizar(l[i])]
        if sem:
            falta.append(u"%s (%s)" % (f[:50], u",".join(sem)))
    checar(u"%d frases, todas com as onze traduções" % len(fr), not falta, u" | ".join(falta[:6]))
    chaves = [P.normalizar(l[0]) for l in P.TABELA]
    rep = sorted(set(k for k in chaves if chaves.count(k) > 1 and k in
                     [P.normalizar(f) for f in fr]))
    checar(u"  e nenhuma delas repetida no dicionário", not rep, u" | ".join(rep))


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


def _subir(base, porta, nome):
    root = os.path.join(base, "share")
    os.makedirs(root, exist_ok=True)
    cfg = os.path.join(base, "t.config")
    io.open(cfg, "w", encoding="utf-8").write(
        u"ROOT=%s\nDRY_RUN=1\nMIN_SLICES=5\nQUIET_MIN=0\nTPS_DESTINO=eclipse\n"
        u"PORT=%d\nLOG_DIR=%s\nPASTA_FAVORITA=%s\n"
        % (root, porta, os.path.join(base, "log"), root))
    calib = os.path.join(base, "calib")
    env = dict(os.environ, RADAI_CONFIG=cfg, RADAI_MACHINE=nome,
               RADAI_CALIB_DIR=calib, RADAI_REGISTRO_DIR=os.path.join(base, "reg"),
               LOCALAPPDATA=os.path.join(base, "ad"), RADAI_TMP=os.path.join(base, "tmp"),
               RADAI_NOTIFICACAO="0", RADAI_URL_VERSOES="0",
               PYTHONIOENCODING="utf-8:replace")
    os.makedirs(env["RADAI_TMP"], exist_ok=True)
    velho = os.environ.get("RADAI_CALIB_DIR")
    os.environ["RADAI_CALIB_DIR"] = calib
    try:
        import radai_consent
        radai_consent.registrar_aceite(u"bateria das lacunas")
    finally:
        os.environ["RADAI_CALIB_DIR"] = velho
    saida = io.open(os.path.join(base, "vigia.log"), "wb")
    proc = subprocess.Popen([sys.executable, _componentes.fonte("app/radai_watcher.py")],
                            env=env, stdout=saida, stderr=subprocess.STDOUT)
    url = "http://127.0.0.1:%d" % porta
    for _ in range(120):
        try:
            urllib.request.urlopen(url + "/api/fila", timeout=2).read()
            return proc, root
        except urllib.error.HTTPError:
            return proc, root
        except Exception:
            time.sleep(1)
    proc.kill()
    return None, root


def _prints():
    d = os.environ.get("RADAI_PRINTS_DIR", "").strip()
    return d or None


def _print(pg, nome, inteira=True):
    d = _prints()
    if not d:
        return
    os.makedirs(d, exist_ok=True)
    pg.screenshot(path=os.path.join(d, nome + ".png"), full_page=inteira)


class Nav(object):
    def __init__(self, pg, base):
        self.pg, self.base = pg, base

    def abrir(self, rota, idioma="pt-BR", barra=True, espera="networkidle"):
        pg = self.pg
        pg.evaluate("(a) => { try{ localStorage.setItem('radai_idioma', a[0]);"
                    " sessionStorage.setItem('radai_dir_usuario', a[1]) }catch(e){} }",
                    [idioma, "aberta" if barra else "recolhida"])
        pg.goto(self.base + rota, wait_until=espera, timeout=120000)
        pg.wait_for_timeout(900)


def _vis(pg, sel):
    return pg.evaluate("(s) => { const e = document.querySelector(s); if(!e) return false;"
                       " const r = e.getBoundingClientRect(); const c = getComputedStyle(e);"
                       " return r.width > 0 && r.height > 0 && c.visibility !== 'hidden'"
                       " && c.display !== 'none' }", sel)


def _frase(idioma, pt):
    import radai_phrases as P
    if idioma in ("pt-BR", "", None):
        return pt
    return P.construir()[idioma].get(P.normalizar(pt), pt)


def _soltar(pg, sel, texto=None, nome=None):
    pg.evaluate("""(a) => { const dt = new DataTransfer();
      if(a[1]) dt.setData('text/plain', a[1]);
      if(a[2]) dt.items.add(new File(['x'], a[2], {type: ''}));
      const alvo = document.querySelector(a[0]);
      for(const t of ['dragenter', 'dragover', 'drop'])
        alvo.dispatchEvent(new DragEvent(t, {dataTransfer: dt, bubbles: true, cancelable: true}));
    }""", [sel, texto or u"", nome or u""])


def _alinhamento(pg):
    return pg.evaluate("""() => {
      const r = e => e.getBoundingClientRect();
      const i = r(document.getElementById('pasta'));
      return [...document.querySelectorAll('.cam-linha button')].map(r)
        .map(x => Math.abs((x.top + x.height / 2) - (i.top + i.height / 2)));
    }""")


def _tela_do_rodar(nv, root, pasta_a, pasta_b):
    pg = nv.pg
    secao(u"[tela] LAC-05 e LAC-11: o soltar e o alinhamento depois da ação")
    pg.set_viewport_size({"width": 1280, "height": 900})
    for idioma in ("pt-BR", "de"):
        nv.abrir("/lote", idioma)
        pg.evaluate("novasSeries(); true")
        pg.wait_for_timeout(500)
        checar(u"[%s] a área de envio está visível sem arrastar nada" % idioma,
               _vis(pg, "#rs_area_pasta"))
        antes = pg.input_value("#pasta")
        _soltar(pg, "#rs_area_pasta", nome=u"PAC_A")
        pg.wait_for_timeout(900)
        est = pg.inner_text("#rs_area_pasta .ui-envio-est").strip()
        aberto = _vis(pg, ".ui-fp")
        valor = pg.input_value("#pasta")
        def nao_recebeu(v):
            return v == antes and v != u"PAC_A"
        checar(u"[%s] só o nome: o campo NÃO recebe o nome" % idioma, nao_recebeu(valor), valor)
        checar(u"[%s]   e o explorador de pastas abre" % idioma, aberto)
        esperado = _frase(idioma, u"O navegador não entrega o caminho de uma pasta "
                                  u"arrastada — escolha-a aqui no explorador.")
        checar(u"[%s]   e a frase sai no idioma da tela" % idioma, est == esperado, est)
        cor = pg.evaluate("getComputedStyle(document.querySelector('#rs_area_pasta .ui-envio-est')).color")
        aviso = pg.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--aviso').trim()")
        checar(u"[%s]   na cor do token de aviso" % idioma, bool(aviso) and cor != u"rgb(255, 200, 87)", cor)
        if idioma == "de":
            _print(pg, u"lacunas_soltar_so_o_nome_1280_de", inteira=False)
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(300)
            pg.evaluate("() => { const e = document.querySelector('#rs_area_pasta .ui-envio-est');"
                        " e.textContent = 'o navegador nao entregou o caminho completo — so o nome. "
                        "Confira o campo antes de varrer.'; if(window.radaiRetraduzir) radaiRetraduzir() }")
            pg.wait_for_timeout(700)
            velho = pg.inner_text("#rs_area_pasta .ui-envio-est").strip()
            checar(u"[de]   (isca) a frase antiga, por `textContent`, ficaria em português",
                   velho != esperado and u"navegador" in velho, velho)
            continue
        _print(pg, u"lacunas_soltar_so_o_nome_1280_pt", inteira=False)
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(300)
        checar(u"[pt]   (isca) o campo com o nome seria acusado", not nao_recebeu(u"PAC_A"))
        _soltar(pg, "#rs_area_pasta", texto=pasta_a, nome=u"PAC_A")
        pg.wait_for_selector("#tab tr[id^=linha_]", timeout=30000)
        pg.wait_for_timeout(1200)
        checar(u"[pt] com o caminho absoluto: o campo recebe o caminho e varre",
               pg.input_value("#pasta") == pasta_a
               and pg.evaluate("document.querySelectorAll('#tab tr[id^=linha_]').length") >= 1)
        pg.evaluate("ltEscolha(); msg('Nenhuma série nesta pasta.', false);"
                    " _notaNoPopup(_notaDasCurtas() || '<b>3</b> série(s) desta pasta"
                    " não aparecem na lista'); true")
        pg.wait_for_timeout(400)
        for larg in (1280, 1600):
            pg.set_viewport_size({"width": larg, "height": 900})
            pg.evaluate("uiDireita('0')")
            pg.wait_for_timeout(400)
            geo = _alinhamento(pg)
            msg = pg.inner_text("#msg").strip()
            checar(u"[pt %d] R10 depois da varredura (com #msg e a nota): botões alinhados ao campo"
                   % larg, msg and geo and max(geo) <= 2.5, u"%s | %s" % (geo, msg[:40]))
        pg.set_viewport_size({"width": 1280, "height": 900})
        _print(pg, u"lacunas_rodar_depois_da_acao_1280_pt", inteira=False)
        pg.add_style_tag(content=u".cam-linha{align-items:flex-start !important}"
                                 u".cam-linha button{min-height:64px !important}")
        pg.wait_for_timeout(300)
        geo = _alinhamento(pg)
        checar(u"[pt]   (isca) com a linha alinhada no topo, a medida reprova",
               geo and max(geo) > 2.5, str(geo))
    for idioma in ("pt-BR", "de"):
        nv.abrir("/ver", idioma)
        pg.click("#vr_guias-t-pasta")
        pg.wait_for_selector("#vr_pasta", state="visible", timeout=20000)
        pg.wait_for_timeout(600)
        checar(u"[%s /ver] a área de envio está visível, abaixo do campo" % idioma,
               _vis(pg, "#rs_area_vr_pasta") and pg.evaluate(
                   "document.getElementById('rs_area_vr_pasta').getBoundingClientRect().top >= "
                   "document.getElementById('vr_pasta').getBoundingClientRect().bottom"))
        antes = pg.input_value("#vr_pasta")
        _soltar(pg, "#rs_area_vr_pasta", nome=u"PAC_A")
        pg.wait_for_timeout(900)
        est = pg.inner_text("#rs_area_vr_pasta .ui-envio-est").strip()
        checar(u"[%s /ver] só o nome: o campo não o recebe, o explorador abre e a frase sai no idioma"
               % idioma, pg.input_value("#vr_pasta") == antes and _vis(pg, ".ui-fp")
               and est == _frase(idioma, u"O navegador não entrega o caminho de uma pasta "
                                         u"arrastada — escolha-a aqui no explorador."), est)
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(300)
        _print(pg, u"lacunas_ver_soltar_1280_%s" % idioma.lower(), inteira=False)
        _soltar(pg, "#rs_area_vr_pasta", texto=pasta_a)
        pg.wait_for_timeout(1500)
        checar(u"[%s /ver] com o caminho absoluto: o campo recebe o caminho" % idioma,
               pg.input_value("#vr_pasta") == pasta_a, pg.input_value("#vr_pasta"))
    secao(u"[tela] LAC-04: «Esvaziar seleção» = tirar as desta pasta")
    nv.abrir("/lote")
    pg.evaluate("novasSeries(); true")
    pg.wait_for_timeout(400)

    def varrer(p):
        pg.evaluate("ltEscolha(); true")
        pg.wait_for_timeout(300)
        pg.fill("#pasta", p)
        pg.click(".cam-linha button.pri")
        pg.wait_for_function("(p) => SERIES.length > 0 && SERIES.every(s => s.pasta.indexOf(p) === 0)",
                             arg=p, timeout=30000)
        pg.wait_for_timeout(1500)
    def incluir_todas():
        if pg.is_enabled("#cartsel"):
            pg.click("#cartsel")
            pg.wait_for_timeout(300)
    varrer(pasta_a)
    incluir_todas()
    varrer(pasta_b)
    incluir_todas()
    fila0 = pg.evaluate("document.querySelectorAll('#radai_fila .cd').length")

    def pastas_no_carrinho():
        return pg.evaluate("carrinhoLista().map(s => s.pasta)")
    tudo = pastas_no_carrinho()
    pg.click("#cartesv")
    pg.wait_for_timeout(500)
    dlg = pg.evaluate("!!document.querySelector('.ui-pnl-veu.vis, .ui-modal-veu.vis')")
    ficou = pastas_no_carrinho()

    def so_as_de_a(lst):
        return bool(lst) and all(p.startswith(pasta_a) for p in lst)
    checar(u"[tela] com séries de duas pastas, «Esvaziar» na B deixa as da A",
           len(tudo) >= 2 and so_as_de_a(ficou), json.dumps([tudo, ficou]))
    checar(u"[tela]   sem diálogo nenhum", not dlg)
    checar(u"[tela]   e a fila da barra não muda",
           pg.evaluate("document.querySelectorAll('#radai_fila .cd').length") == fila0)
    banner = pg.inner_text("#cartxt")
    checar(u"[tela]   e o banner continua contando as que ficaram",
           str(len(ficou)) in banner, banner)
    _print(pg, u"lacunas_esvaziar_desta_pasta_1280_pt", inteira=False)
    incluir_todas()
    pg.evaluate("limparSelecao()")
    checar(u"[tela]   (isca) o esvaziar antigo (o carrinho inteiro) seria acusado",
           not so_as_de_a(pastas_no_carrinho()))


_ULTIMA_FILA = ("((window.DC && DC.filas && DC.filas.length) ? "
                "DC.filas[DC.filas.length - 1] : null)")


def _tela_do_bridge(nv, estudo, uid_tc, uid_rm, destino):
    import test_bridge_tela as BT
    pg = nv.pg
    secao(u"[tela] LAC-02: do DicomBridge à fila única, sem dublê")
    nv.abrir("/bridge/laudo")
    url0 = pg.url
    BT._carregar(pg, estudo)
    i_tc = BT._indice(pg, "CT")
    BT._clicar_e_esperar(pg, "#dcs%d" % i_tc)
    b_tc = pg.evaluate("DC.series[%d].bilhete" % i_tc)
    pg.click("#dcr_%s .dc-seg button[data-modo=\"fast\"]" % b_tc)
    pg.click("#dc_avancar")
    pg.wait_for_function("!document.getElementById('dc_e3').hidden", timeout=20000)
    pg.click("#dc_converter")
    pg.wait_for_function("!document.getElementById('dc_e5').hidden", timeout=60000)
    pg.wait_for_timeout(500)
    BT._destino_pelo_explorador(pg, "#dc_e5 #bg_dest_mais", destino)
    if not checar(u"[bridge] uma série marcada (a TC), e o destino é a pasta da bateria",
                  BT._so_um_destino(pg, destino)
                  and pg.evaluate("dcMarcadas().map(i => DC.series[i].modalidade)") == [u"CT"],
                  json.dumps(pg.evaluate("BG.destinos.slice()"))):
        return False
    pg.click("#dc_entregar")
    pg.wait_for_function(_ULTIMA_FILA + " && (" + _ULTIMA_FILA + ".estado === "
                         "'na_fila' || " + _ULTIMA_FILA + ".estado === "
                         "'indisponivel')", timeout=90000)
    pg.wait_for_timeout(1500)
    fila = pg.evaluate("(f => ({estado: f.estado, itens: f.itens,"
                       " ids: (f.cartoes || []).map(c => c.id)}))("
                       + _ULTIMA_FILA + ")")
    checar(u"[bridge] (a) a fila única aceitou o pedido, e a tela não navegou",
           fila["estado"] == u"na_fila" and pg.url == url0
           and u"%5C" not in pg.url and u":\\" not in pg.url,
           json.dumps([fila["estado"], pg.url])[:200])

    def so_a_marcada(itens):
        return len(itens) == 1 and itens[0].get("uid") == uid_tc

    def na_pasta_salva(itens):
        if len(itens) != 1:
            return False
        p = os.path.normcase(itens[0].get("pasta") or u"")
        return (p.startswith(os.path.normcase(destino) + os.sep)
                and os.path.basename(os.path.dirname(itens[0]["pasta"])).startswith(u"DICOM_BRIDGE_"))
    checar(u"[bridge] (b) vai à fila só a série marcada, de origem DicomBridge",
           so_a_marcada(fila["itens"]) and fila["itens"][0].get("origem") == u"dicombridge",
           json.dumps(fila["itens"])[:300])
    checar(u"[bridge] (c) a pasta enfileirada é a SALVA pelo DicomBridge, e não a de origem",
           na_pasta_salva(fila["itens"]), json.dumps(fila["itens"])[:300])
    est = pg.evaluate("(ids) => fetch('/api/fila/estado', {method: 'POST',"
                      " headers: {'Content-Type': 'application/json'},"
                      " body: JSON.stringify({ids: ids})}).then(r => r.json())", fila["ids"])
    cards = (est or {}).get("cartoes") or []
    checar(u"[bridge]   e o cartão está na fila da estação, com a origem",
           len(cards) == 1 and cards[0].get("origem") == u"dicombridge"
           and estudo not in json.dumps(est), json.dumps(est)[:300])
    isca_origem = [{"uid": uid_tc, "pasta": os.path.join(estudo, "TC")}]
    isca_outra = [{"uid": uid_rm, "pasta": (fila["itens"] or [{}])[0].get("pasta", u"")}]
    checar(u"[bridge]   (isca) a pasta de origem seria acusada em (c)", not na_pasta_salva(isca_origem))
    checar(u"[bridge]   (isca) a série não marcada seria acusada em (b)", not so_a_marcada(isca_outra))
    rec = pg.evaluate("document.documentElement.classList.contains('dir-recolhida')")
    aba = pg.evaluate("(document.getElementById('radai_tf_ab_fila')||{getAttribute:()=>null})"
                      ".getAttribute('aria-selected')")
    checar(u"[bridge] (d) a barra da direita abre, na aba da fila",
           rec is False and aba == u"true", u"recolhida=%s aba=%s" % (rec, aba))
    _print(pg, u"lacunas_bridge_na_fila_1280_pt", inteira=False)
    return True


def _tela_do_iniciar(nv):
    import radai_review as R
    pg = nv.pg
    secao(u"[tela] LAC-03: a fronteira antes de qualquer início, em toda tela")
    posts = []

    def iniciar(rota):
        posts.append(time.time())
        rota.fulfill(status=200, content_type="application/json",
                     body=json.dumps({"ok": True}))
    pg.route("**/api/pipeline/iniciar", iniciar)
    try:
        for rota in ("/ver", "/bridge/laudo", "/lote"):
            nv.abrir(rota)
            pg.wait_for_timeout(1500)
            pg.evaluate("document.querySelectorAll('[data-ui-ps]').forEach(function(n){"
                        " uiPopupSerie(n.id).fechar() }); true")
            pg.evaluate("uiDireita('0')")
            pg.wait_for_timeout(400)
            pg.wait_for_function("!document.getElementById('radai_pipe_ini').disabled", timeout=20000)
            n0 = len(posts)
            pg.click("#radai_pipe_ini")
            pg.wait_for_selector("#radai_rev_fronteira", state="visible", timeout=15000)
            pg.wait_for_timeout(400)
            g = pg.evaluate("""() => { const t = document.getElementById('radai_rev_fronteira');
              const b = document.getElementById('radai_rev_ok');
              const rt = t.getBoundingClientRect(), rb = b.getBoundingClientRect();
              return {texto: t.textContent.trim(), prox: t.nextElementSibling.className,
                      gap: rb.top - rt.bottom, vis: rt.height > 0 && rt.top >= 0 && rt.bottom <= innerHeight}; }""")
            checar(u"[%s] «Iniciar» mostra a tag com a frase, logo antes do botão" % rota,
                   g["texto"] == R.FRASE_DA_FRONTEIRA and g["prox"] == u"rev-bt" and g["vis"]
                   and 0 <= g["gap"] <= 40, json.dumps(g, ensure_ascii=False)[:200])
            checar(u"[%s]   e nenhum POST de iniciar saiu antes do clique no botão" % rota,
                   len(posts) == n0, str(len(posts) - n0))
            if rota == "/ver":
                _print(pg, u"lacunas_iniciar_no_ver_1280_pt", inteira=False)
            pg.click("#radai_rev_ok")
            pg.wait_for_timeout(700)
            checar(u"[%s]   e o botão do diálogo começa a fila" % rota, len(posts) == n0 + 1)
            pg.route("**/api/pipeline/revisao", lambda r: r.fulfill(status=500, body="x"))
            try:
                n1 = len(posts)
                pg.click("#radai_pipe_ini")
                pg.wait_for_selector("#radai_rev_fronteira", state="visible", timeout=15000)
                pg.wait_for_timeout(500)
                sub = pg.inner_text("#radai_rev_sub").strip()
                checar(u"[%s] com a conferência fora do ar, a tag aparece do mesmo jeito" % rota,
                       _vis(pg, "#radai_rev_fronteira") and len(posts) == n1
                       and sub == R.SEM_CONFERENCIA, sub)
                if rota == "/bridge/laudo":
                    _print(pg, u"lacunas_iniciar_sem_conferencia_1280_pt", inteira=False)
                pg.evaluate("radaiRevFechar()")
                pg.wait_for_timeout(300)
                checar(u"[%s]   e fechar não começa nada" % rota, len(posts) == n1)
            finally:
                pg.unroute("**/api/pipeline/revisao")
        n2 = len(posts)
        pg.evaluate("window.radaiRevAbrir = undefined")
        pg.click("#radai_pipe_ini")
        pg.wait_for_timeout(900)
        checar(u"(isca) uma tela sem a costura começaria a fila sem a frase — e a medida acusa",
               len(posts) == n2 + 1 and not _vis(pg, "#radai_rev_fronteira"))
    finally:
        pg.unroute("**/api/pipeline/iniciar")


def _el_escolher(pg, qual, b):
    pg.evaluate("(a) => { uiPopupSerie('el_escolha').abrir(document.getElementById('el-' + a[0]), a[0]);"
                " var it = document.querySelector('#el-lista .el-it[data-b=\"' + a[1] + '\"]');"
                " elEscolher(a[1], it ? it.textContent : '') }", [qual, b])


def _tela_do_elastic(nv, pasta_el):
    import radai_elastic_screen as T
    pg = nv.pg
    secao(u"[tela] LAC-06 e LAC-07: o Elastic RT em alemão")
    nv.abrir("/elastic/fusao", "de", barra=False)
    pg.click("#el-movel")
    pg.wait_for_timeout(500)
    pg.click("#el_origem-t-pasta")
    pg.fill("#el-pasta", pasta_el)
    pg.click("#el-buscar")
    pg.wait_for_function("document.querySelectorAll('#el-lista .el-it').length >= 3",
                         timeout=60000)
    pg.wait_for_timeout(1500)
    da_pasta = pg.eval_on_selector_all("#el-lista .el-it", "os => os.map(o => o.getAttribute('data-b'))")
    lin = u" ".join(
        pg.eval_on_selector_all("#el-lista .el-it", "os => os.map(o => o.textContent)"))
    checar(u"[de] a lista de séries do popup sem português", u"cortes" not in lin
           and u"série" not in lin, lin[:200])
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(400)
    respostas = []
    pg.on("response", lambda r: respostas.append(r) if "/api/elastic/par" in r.url else None)
    alertas = 0
    for i in range(len(da_pasta)):
        for j in range(i + 1, len(da_pasta)):
            _el_escolher(pg, "fixa", da_pasta[i])
            _el_escolher(pg, "movel", da_pasta[j])
            pg.wait_for_timeout(900)
            if _vis(pg, "#el-sujeitos"):
                alertas += 1
    checar(u"[de] três séries da pasta (X, X, Y): o alerta aparece nos dois pares X × Y",
           len(da_pasta) == 3 and alertas == 2, u"%d séries, %d alertas" % (len(da_pasta), alertas))
    txt = pg.inner_text("#el-sujeitos").strip()
    checar(u"[de]   traduzido, ao lado do «Fundir»", txt == _frase("de", T.SUJEITOS_DIFERENTES), txt)
    corpos = []
    for r in respostas:
        try:
            corpos.append(r.text())
        except Exception:
            pass
    checar(u"[de]   e nenhuma resposta leva o valor da identificação",
           corpos and not [c for c in corpos if u"PAC_X" in c or u"PAC_Y" in c], len(corpos))
    _print(pg, u"lacunas_elastic_sujeitos_1280_de", inteira=False)

    def sem_pt(t):
        return not re.search(u"série|cortes|necessárias|Escolha", t or u"")
    rot = pg.inner_text("#el-fixa .ui-cartao-rot").strip()
    checar(u"[de] o cartão diz a série escolhida sem português", rot and sem_pt(rot), rot)
    pg.evaluate("(b) => fetch('/api/elastic/fundir', {method:'POST', headers:{'Content-Type':'application/json'},"
                " body: JSON.stringify({fixa: b, movel: b})}).then(r => r.json()).then(d => elParar(d.erro))",
                da_pasta[0])
    pg.wait_for_timeout(900)
    e3 = pg.inner_text("#el-erro").strip()
    checar(u"[de] o erro do servidor («Escolha duas séries…») sai em alemão",
           e3 == _frase("de", T.ESCOLHA_DUAS) and sem_pt(e3), e3)
    pg.evaluate("() => { el('el-erro').textContent = 'Escolha duas séries diferentes, e a lista tem 1.';"
                " if(window.radaiRetraduzir) radaiRetraduzir() }")
    pg.wait_for_timeout(900)
    checar(u"[de]   (isca) uma frase fora do dicionário, por `textContent`, fica em português",
           not sem_pt(pg.inner_text("#el-erro")))


def teste_a_tela_renderizada():
    secao(u"a tela renderizada (Chromium, vigia de verdade, séries fantoma)")
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        pulado(u"o navegador", u"sem Playwright neste Python")
        return
    exe = _chromium()
    if not exe:
        pulado(u"o navegador", u"sem o Chromium do Playwright na máquina")
        return
    import test_bridge_tela as BT
    base = os.path.join(_BASE, "nav")
    os.makedirs(base, exist_ok=True)
    root = os.path.join(base, "share")
    pasta_a = _serie(os.path.join(root, "A", "PAC_A", "CT"), u"PAC_A", n=24, dias=1)
    pasta_a = os.path.join(root, "A")
    _serie(os.path.join(root, "B", "PAC_B", "CT"), u"PAC_B", n=24, dias=2)
    pasta_b = os.path.join(root, "B")
    pasta_el = os.path.join(root, "EL")
    _serie(os.path.join(pasta_el, "PAC_X", "CT1"), u"PAC_X", n=24, dias=1)
    _serie(os.path.join(pasta_el, "PAC_X", "CT2"), u"PAC_X", n=24, dias=2)
    _serie(os.path.join(pasta_el, "PAC_Y", "CT"), u"PAC_Y", n=24, dias=3)
    estudo = os.path.join(base, "estudo")
    uid_tc = BT.escrever_tc(os.path.join(estudo, "TC"))
    uid_rm = BT.escrever_rm(os.path.join(estudo, "RM"))
    destino = os.path.join(base, "exporta")
    os.makedirs(destino, exist_ok=True)
    porta = porta_livre()
    proc, root = _subir(base, porta, "BATERIA_LACUNAS")
    if not checar(u"o vigia de teste subiu", proc is not None):
        print(io.open(os.path.join(base, "vigia.log"), encoding="utf-8", errors="replace").read()[-600:])
        return
    erros = []
    try:
        with sync_playwright() as p:
            nav = p.chromium.launch(executable_path=exe, headless=True)
            ctx = nav.new_context(viewport={"width": 1280, "height": 900})
            pg = ctx.new_page()
            pg.on("pageerror", lambda e: erros.append(str(e)[:160]))
            nv = Nav(pg, "http://127.0.0.1:%d" % porta)
            pg.goto(nv.base + "/aceite", wait_until="domcontentloaded")
            for passo in (lambda: _tela_do_rodar(nv, root, pasta_a, pasta_b),
                          lambda: _tela_do_bridge(nv, estudo, uid_tc, uid_rm, destino),
                          lambda: _tela_do_iniciar(nv),
                          lambda: _tela_do_elastic(nv, pasta_el)):
                try:
                    passo()
                except Exception as e:
                    checar(u"o roteiro chegou ao fim", False,
                           u"%s: %s" % (type(e).__name__, str(e).splitlines()[0][:220]))
                    traceback.print_exc()
            nav.close()
    finally:
        proc.kill()
        try:
            proc.wait(timeout=10)
        except Exception:
            pass
    checar(u"nenhum erro de JavaScript em todo o percurso", not erros, u" | ".join(erros[:3]))


def codigos_fora_do_resumo(texto):
    veredito = set(re.findall(r'if not "%(RC\d+)%"=="0" goto :falhou', texto))
    m = re.search(r"^:falhou\r?\n(.*?)^echo   Log completo", texto, re.M | re.S)
    resumo = set(re.findall(r"%(RC\d+)%", m.group(1))) if m else set()
    return sorted(veredito - resumo), len(veredito)


def teste_o_resumo_do_verify_mostra_todo_codigo_do_veredito():
    secao(u"o resumo de FALHOU do verify.cmd mostra todo codigo que entra no "
          u"veredito")
    texto = io.open(os.path.join(RAIZ, "verify.cmd"), encoding="ascii",
                    newline="").read()
    fora, n = codigos_fora_do_resumo(texto)
    checar(u"cada um dos %d codigos do veredito aparece no resumo"
           % n, n > 50 and not fora, str(fora))
    m = re.search(r"^:falhou\r?\n(.*?)^echo   Log completo", texto, re.M | re.S)
    bloco = m.group(1) if m else u""
    alvo = sorted(set(re.findall(r"%(RC\d+)%", bloco)),
                  key=lambda rc: int(rc[2:]))[-2:]
    sem = bloco
    for rc in alvo:
        sem = sem.replace(u"%" + rc + u"%", u"")
    isca = texto.replace(bloco, sem) if bloco else texto
    checar(u"  (isca) sem os dois ultimos codigos no resumo, os dois sao "
           u"acusados", len(alvo) == 2
           and codigos_fora_do_resumo(isca)[0] == sorted(alvo),
           str(codigos_fora_do_resumo(isca)[0]))
    checar(u"  e o verify.cmd continua em CRLF e ASCII",
           u"\r\n" in texto and u"\n" not in texto.replace(u"\r\n", u""))


def main():
    print(u"=" * 68)
    print(u"test_lacunas | o que a auditoria de completude da v8.4 achou aberto")
    print(u"=" * 68)
    testes = (teste_a_lista_de_outra_trilha, teste_a_fronteira_mora_com_a_barra,
              teste_esvaziar_e_desta_pasta, teste_o_soltar_e_de_caminho,
              teste_a_guarda_do_elastic, teste_as_frases_do_elastic,
              teste_a_angiografia_sintetica,
              teste_a_porta_das_baterias, teste_as_frases_tem_os_doze_idiomas,
              teste_o_resumo_do_verify_mostra_todo_codigo_do_veredito,
              teste_a_tela_renderizada)
    for t in testes:
        try:
            t()
        except Exception as e:
            checar(u"%s chegou ao fim" % t.__name__, False, u"%s: %s" % (type(e).__name__, e))
            traceback.print_exc()
    falhas = [r for r in _R if not r[1]]
    print()
    if falhas:
        print(u"FALHOU: %d de %d checagens" % (len(falhas), len(_R)))
        for n, _ok, d in falhas:
            print(u"  - %s%s" % (n, (u"  [%s]" % d) if d else u""))
        return 1
    print(u"OK: %d checagens, todas passaram" % len(_R))
    return 0


if __name__ == "__main__":
    sys.exit(main())
