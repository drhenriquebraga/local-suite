# -*- coding: utf-8 -*-
import datetime
import io
import json
import os
import sys
import threading

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

AQUI = os.path.dirname(os.path.abspath(__file__))


def pasta_app(aqui):
    for c in (os.path.join(aqui, "..", "app"), os.path.join(aqui, "..")):
        if os.path.exists(os.path.join(c, "radai_watcher.py")):
            return os.path.abspath(c)
    return os.path.abspath(os.path.join(aqui, "..", "app"))


APP = pasta_app(AQUI)
sys.path.insert(0, APP)
sys.path.insert(0, AQUI)

import tempfile
import _cleanup
_cleanup.adotar_prefixo("radai_ver_")
_cleanup.adotar_prefixo("radai_marca_")
os.environ["RADAI_CALIB_DIR"] = tempfile.mkdtemp(prefix="radai_ver_")

import radai_delivery as E
import radai_version as V

_ok = 0
_falhou = 0
_falhas = []
VERBOSO = "-v" in sys.argv


def secao(t):
    print(u"\n── %s %s" % (t, u"─" * max(0, 66 - len(t))))


def checar(rotulo, cond, detalhe=u""):
    global _ok, _falhou
    if cond:
        _ok += 1
        if VERBOSO:
            print(u"  OK     %s" % rotulo)
    else:
        _falhou += 1
        _falhas.append(u"%s  %s" % (rotulo, detalhe))
        print(u"  FALHA  %s  %s" % (rotulo, detalhe))


class _Servidor(object):

    def __init__(self, resposta, codigo=200):
        from http.server import BaseHTTPRequestHandler, HTTPServer

        corpo = json.dumps(resposta).encode("utf-8")
        pedidos = self.pedidos = []

        class Mao(BaseHTTPRequestHandler):
            def do_GET(self):
                pedidos.append({
                    "caminho": self.path,
                    "agente": self.headers.get("User-Agent", ""),
                    "tem_corpo": bool(self.headers.get("Content-Length")),
                    "metodo": self.command,
                })
                self.send_response(codigo)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(corpo)))
                self.end_headers()
                self.wfile.write(corpo)

            def log_message(self, *a):
                pass

        self.httpd = HTTPServer(("127.0.0.1", 0), Mao)
        self.porta = self.httpd.server_address[1]
        self.t = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.t.start()

    @property
    def url_pagina(self):
        return u"http://127.0.0.1:%d/x/y/releases" % self.porta

    def fechar(self):
        try:
            self.httpd.shutdown()
        except Exception:
            pass


def _html_handler(pedidos):
    from http.server import BaseHTTPRequestHandler

    class Mao(BaseHTTPRequestHandler):
        def do_GET(self):
            pedidos.append({"caminho": self.path, "agente": u"",
                            "tem_corpo": False, "metodo": self.command})
            corpo = b"<html><body>pagina de download</body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

        def log_message(self, *a):
            pass

    return Mao


def _com_versao(v):
    return lambda recarregar=False: {
        "projeto": "AUTO_CONTORNO", "versao": v, "data": "2026-09-02",
        "build": "", "origem": "(teste)"}


def teste_comparacao():
    secao(u"versao compara por NUMERO, e nao por texto")
    checar(u"2.10 e mais nova que 2.9", V._maior("2.10", "2.9"))
    checar(u"e 2.9 nao e mais nova que 2.10", not V._maior("2.9", "2.10"))
    checar(u"3.0 e mais nova que 2.10", V._maior("3.0", "2.10"))
    checar(u"e igual nao e mais nova", not V._maior("3.0", "3.0"))
    checar(u"o `v` do inicio nao atrapalha", V._maior("v3.1", "3.0"))
    checar(u"sufixo nao numerico nao levanta",
           V._maior("2.5.0-weights", "1.0") is True)


def teste_derivacao():
    secao(u"uma chave de configuracao, dois usos")
    api = V._api_de("https://github.com/dono/repo/releases")
    checar(u"a pagina de releases vira o endpoint da API",
           api == "https://api.github.com/repos/dono/repo/releases/latest", api)
    checar(u"o `.git` do fim nao entra no caminho",
           V._api_de("https://github.com/dono/repo.git").endswith(
               "/repos/dono/repo/releases/latest"))
    for ruim in ("", "   ", "nao e url", "ftp://x/y", r"C:\pasta\x"):
        checar(u"%r nao deriva endereco" % (ruim[:22] or u"vazio"),
               not V._api_de(ruim), repr(V._api_de(ruim))[:40])
    checar(u"e um endereco qualquer vai como esta (o espelho)",
           V._api_de("https://intranet/versao.json")
           == "https://intranet/versao.json")


def teste_consulta():
    secao(u"a consulta: quatro estados, e nenhum deles mente")
    real = E.carimbo
    try:
        s = _Servidor({"tag_name": "v9.9"})
        try:
            E.carimbo = _com_versao("3.0")
            r = V.consultar(s.url_pagina, timeout=5)
            checar(u"versao maior no servidor -> `nova`",
                   r["estado"] == "nova", u"%s %s" % (r["estado"], r["erro"]))
            checar(u"e ela vem no laudo", r["versao"] == "9.9", r["versao"])

            checar(u"chegou exatamente um pedido", len(s.pedidos) == 1,
                   str(len(s.pedidos)))
            if s.pedidos:
                p = s.pedidos[0]
                checar(u"e ele e um GET", p["metodo"] == "GET", p["metodo"])
                checar(u"sem corpo", not p["tem_corpo"])
                checar(u"e sem parametro de query", "?" not in p["caminho"],
                       p["caminho"])
                ag = p["agente"].lower()
                checar(u"o User-Agent nao identifica a maquina",
                       "radioterapia" in ag
                       and not any(x in ag for x in (
                           os.environ.get("COMPUTERNAME", "###").lower(),
                           os.environ.get("USERNAME", "###").lower())),
                       p["agente"])

            E.carimbo = _com_versao("99.0")
            r = V.consultar(s.url_pagina, timeout=5)
            checar(u"versao menor no servidor -> `atual`",
                   r["estado"] == "atual", r["estado"])

            E.carimbo = _com_versao("")
            r = V.consultar(s.url_pagina, timeout=5)
            checar(u"sem saber a versao daqui, NAO diz `atual`",
                   r["estado"] != "atual", r["estado"])
            checar(u"e explica por que", "nao sei a" in (r["erro"] or ""),
                   r["erro"][:60])
        finally:
            s.fechar()

        s = _Servidor({"message": "Not Found"}, codigo=404)
        try:
            E.carimbo = _com_versao("3.0")
            r = V.consultar(s.url_pagina, timeout=5)
            checar(u"404 -> `privado`, e nao «nao existe»",
                   r["estado"] == "privado", r["estado"])
            checar(u"e a frase admite as duas hipoteses",
                   "privado" in r["erro"] and "endereco" in r["erro"],
                   r["erro"][:70])
        finally:
            s.fechar()

        E.carimbo = _com_versao("3.0")
        r = V.consultar(u"http://127.0.0.1:9/x/y/releases", timeout=3)
        checar(u"porta fechada -> `erro`, com motivo", r["estado"] == "erro"
               and bool(r["erro"]), u"%s %s" % (r["estado"], r["erro"][:50]))
        checar(u"e NUNCA `atual`", r["estado"] != "atual")

        s2 = _Servidor({"tag_name": "v9.9"})
        try:
            s2.httpd.RequestHandlerClass = _html_handler(s2.pedidos)
            E.carimbo = _com_versao("3.0")
            r = V.consultar(s2.url_pagina, timeout=5)
            checar(u"resposta que nao e JSON -> erro, e NUNCA `atual`",
                   r["estado"] not in ("atual", "nova"),
                   u"%s %s" % (r["estado"], r["erro"][:40]))
            checar(u"e o motivo vem junto", bool(r["erro"]), r["erro"][:50])
        finally:
            s2.fechar()

        r = V.consultar(u"", timeout=3)
        checar(u"sem URL_VERSOES -> `sem_endereco`",
               r["estado"] == "sem_endereco", r["estado"])
    finally:
        E.carimbo = real


def teste_nao_bloqueia():
    secao(u"o arranque nao espera a resposta")
    import time
    real = E.carimbo
    E.carimbo = _com_versao("3.0")
    try:
        t0 = time.time()
        t = V.iniciar_consulta(u"http://127.0.0.1:9/x/y/releases", timeout=4)
        dt = time.time() - t0
        checar(u"iniciar_consulta devolve na hora (< 0,5 s)", dt < 0.5,
               u"%.3f s" % dt)
        checar(u"e a thread e daemon (nao segura o encerrar)", t.daemon)
        t.join(timeout=12)
        d = V.ultima_consulta()
        checar(u"depois ela conta o que aconteceu", bool(d.get("frase")),
               repr(d.get("frase"))[:60])
        _fr = (d.get("frase") or "").lower()
        checar(u"a frase nao afirma que esta em dia",
               not any(x in _fr for x in ("mais recente", "esta atual",
                                          "em dia")),
               _fr[:60])
        checar(u"e ela NOMEIA a causa, em vez de so' dizer que falhou",
               any(x in _fr for x in ("indisponivel", "nao consegui",
                                      "erro", "sem resposta")) and "(" in _fr,
               _fr[:60])
        checar(u"o log leva essa linha", bool(V.linhas_de_consulta(d)))
        for _l in V.linhas_de_consulta(d):
            checar(u"a linha do log diz «versao:» uma vez so",
                   _l.lower().count(u"versao:") == 1, _l[:70])
        checar(u"  e a frase sozinha nao traz o prefixo do log",
               not (d.get("frase") or u"").lower().startswith(u"versao:"),
               (d.get("frase") or u"")[:60])
    finally:
        E.carimbo = real


def teste_idade():
    secao(u"a idade do build: a pergunta que nao precisa de ninguem")
    real = E.carimbo
    HOJE = datetime.date(2026, 9, 2)
    try:
        casos = (
            (u"2026-09-02", "novo"),
            (u"2026-08-13", "novo"),
            (u"2026-07-29", "perto"),
            (u"2026-07-04", "vencido"),
            (u"2026-10-01", "relogio_suspeito"),
            (u"", "sem_carimbo"),
        )
        for data, esperado in casos:
            E.carimbo = lambda recarregar=False, _d=data: {
                "projeto": "AUTO_CONTORNO", "versao": "3.0", "data": _d,
                "build": "", "origem": "(teste)"}
            r = V.idade(hoje=HOJE)
            checar(u"carimbo %-12s -> %s" % (data or u"(sem)", esperado),
                   r["estado"] == esperado,
                   u"veio %s" % r["estado"])
            checar(u"  e tem frase", bool(r["frase"]) or esperado == "novo")

        E.carimbo = lambda recarregar=False: {
            "projeto": "AUTO_CONTORNO", "versao": "3.0", "data": "",
            "build": "", "origem": "(teste)"}
        r = V.idade(hoje=HOJE)
        checar(u"sem carimbo, ele MANDA conferir",
               "conferir" in r["frase"].lower(), r["frase"][:60])
    finally:
        E.carimbo = real


def teste_registro_que_mente():
    secao(u"o registro diz o que foi instalado um dia, e nao o que esta la")
    laudo = V.conferir("3.0")
    f = laudo.get("fontes") or {}
    checar(u"o laudo diz SE a pasta instalada existe",
           "instalada_existe" in f, str(sorted(f))[:70])
    onde = f.get("instalada_em") or ""
    if onde and not f.get("instalada_existe"):
        checar(u"e avisa quando ela sumiu",
               any("nao existe mais" in a for a in laudo.get("avisos", [])),
               str(laudo.get("avisos"))[:80])
    else:
        checar(u"PULADO: o registro desta maquina aponta para pasta que existe",
               True, onde[:50])


def _fantoma_instalado(base, versao=u"8.4"):
    import importlib.util
    import shutil
    raiz_proj = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raiz = os.path.join(base, "RADIOTERAPIA_AI")
    prog = os.path.join(raiz, "LOCAL_SUITE")
    os.makedirs(prog)
    shutil.copy2(os.path.join(raiz_proj, "app", "radai_version.py"), prog)
    io.open(os.path.join(prog, "entrega.txt"), "w", encoding="utf-8").write(
        u"PROJETO=LOCAL_SUITE\nVERSAO=%s\n" % versao)
    spec = importlib.util.spec_from_file_location(
        "rv_fantoma_%d" % len(base), os.path.join(prog, "radai_version.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return raiz, prog, m


def _gravar_registro(pasta, dados):
    io.open(os.path.join(pasta, "_instalados.json"), "w",
            encoding="utf-8").write(json.dumps(dados))


def teste_o_registro_segue_a_regra_unica():
    import shutil

    secao(u"o registro mora no PAI da pasta do programa, e so ele e lido")
    base = tempfile.mkdtemp(prefix="radai_marca_")
    guardado = dict(os.environ)
    try:
        os.environ.pop("RADAI_RAIZ_INSTALACAO", None)
        sysd = os.path.join(base, "SYSDRIVE")
        os.makedirs(os.path.join(sysd, "RADIOTERAPIA_AI"))
        os.environ["SystemDrive"] = sysd
        raiz, prog, m = _fantoma_instalado(base)
        checar(u"a pasta do programa e a que tem o entrega.txt",
               m.pasta_do_programa() == prog,
               m.pasta_do_programa().replace(base, u"<tmp>"))
        checar(u"e o registro dela e o do pai",
               m.registro_da_instalacao() == os.path.join(raiz, "_instalados.json"),
               m.registro_da_instalacao().replace(base, u"<tmp>"))

        _gravar_registro(raiz, {"LOCAL_SUITE": {"versao": "8.4", "caminho": prog}})
        _gravar_registro(prog, {"LOCAL_SUITE": {"versao": "8.3", "caminho": prog}})
        _gravar_registro(os.path.join(sysd, "RADIOTERAPIA_AI"),
                         {"LOCAL_SUITE": {"versao": "2.1",
                                          "caminho": os.path.join(sysd, "X")}})
        d, caminho = m._instalados()
        checar(u"com o registro duplicado DENTRO da pasta, le o do pai",
               caminho == os.path.join(raiz, "_instalados.json")
               and (d.get("LOCAL_SUITE") or {}).get("versao") == "8.4",
               (caminho.replace(base, u"<tmp>"), d))
        laudo = m.conferir("8.4")
        av = laudo.get("avisos") or []
        f = laudo.get("fontes") or {}
        checar(u"  e NAO da o alarme falso «instalada=8.3, codigo=8.4»",
               laudo.get("ok") and not any(u"8.3" in a and u"CÓPIA" in a for a in av)
               and f.get("instalada") == u"8.4", (laudo.get("ok"), av))
        checar(u"  o laudo diz qual arquivo leu",
               f.get("registro") == os.path.join(raiz, "_instalados.json"),
               f.get("registro"))
        checar(u"  e aponta o de dentro como ignorado, sem reprovar",
               f.get("registro_ignorado") == os.path.join(prog, "_instalados.json")
               and any(u"segundo registro" in a for a in av), (f, av))
        log = m.linhas_para_log(laudo)
        checar(u"  e a linha do log diz o registro lido",
               bool(log) and (u"registro lido: %s" % f.get("registro")) in log[0],
               log[:1])

        def ingenuo():
            d0 = os.path.dirname(os.path.abspath(
                os.path.join(prog, "radai_version.py")))
            for _ in range(6):
                if os.path.isfile(os.path.join(d0, "_instalados.json")):
                    return os.path.join(d0, "_instalados.json")
                d0 = os.path.dirname(d0)
            return u""
        checar(u"  (isca) a busca antiga, subindo pela marca, lia o de DENTRO",
               ingenuo() == os.path.join(prog, "_instalados.json"), ingenuo())

        os.remove(os.path.join(prog, "_instalados.json"))
        _gravar_registro(raiz, {"LOCAL_SUITE": {"versao": "8.3", "caminho": prog}})
        laudo = m.conferir("8.4")
        av = laudo.get("avisos") or []
        checar(u"registro desta pasta com versao velha: diz que ficou para tras",
               not laudo.get("ok") and any(u"ficou para trás" in a for a in av)
               and not any(u"CÓPIA" in a for a in av), av)

        outra = os.path.join(raiz, "LOCAL_SUITE_OUTRA")
        os.makedirs(outra)
        _gravar_registro(raiz, {"LOCAL_SUITE": {"versao": "8.4", "caminho": outra}})
        laudo = m.conferir("8.4")
        av = laudo.get("avisos") or []
        checar(u"registro de OUTRA pasta que existe: diz que esta e uma copia",
               not laudo.get("ok") and any(u"CÓPIA" in a for a in av), av)

        _gravar_registro(raiz, {"LOCAL_SUITE": {"versao": "2.1",
                                                "caminho": os.path.join(base, "SUMIU")}})
        laudo = m.conferir("8.4")
        av = laudo.get("avisos") or []
        checar(u"registro apontando para pasta que sumiu: avisa que sumiu",
               any("nao existe mais" in a for a in av), str(av)[:90])
        checar(u"  e NAO diz tambem que voce roda uma copia (as duas se "
               u"contradizem)", not any(u"CÓPIA" in a for a in av), str(av)[:90])

        os.remove(os.path.join(raiz, "_instalados.json"))
        laudo = m.conferir("8.4")
        av = laudo.get("avisos") or []
        checar(u"sem registro no pai: diz que nao ha registro, e nao le o do "
               u"SystemDrive", any(u"não há registro" in a for a in av)
               and (laudo.get("fontes") or {}).get("instalada") == u"", av)
    finally:
        os.environ.clear()
        os.environ.update(guardado)
        shutil.rmtree(base, ignore_errors=True)


def teste_constante_e_porta():
    secao(u"o endereco e constante, e a porta so acende com versao nova")
    checar(u"a constante existe e e do GitHub",
           str(getattr(V, "URL_VERSOES", "")).startswith(
               "https://github.com/"), repr(getattr(V, "URL_VERSOES", None)))
    api = V._api_de(V.URL_VERSOES)
    checar(u"  e deriva a API em api.github.com",
           api.startswith("https://api.github.com/repos/"), api)
    checar(u"sem argumento vale a constante", V._url(None) == V.URL_VERSOES)
    checar(u"  e string vazia continua desligando", V._url(u"") == u"")
    checar(u"o link do instalador sai da constante sem argumento",
           V.link_do_instalador() == V.link_do_instalador(V.URL_VERSOES)
           and V.link_do_instalador().startswith("https://github.com/"),
           V.link_do_instalador())

    guardado = dict(V._CONSULTA)
    real = E.carimbo
    try:
        E.carimbo = _com_versao("8.2")
        for est, acende in (("nova", True), ("atual", False),
                            ("privado", False), ("erro", False),
                            ("sem_endereco", False), ("nunca", False)):
            V._CONSULTA.update({"estado": est, "versao": u"8.4",
                                "url": u"", "erro": u"x", "quando": None})
            t = V.para_a_tela()
            checar(u"estado %-12s -> ponto %s" % (est, u"aceso" if acende
                                                  else u"apagado"),
                   bool(t.get("nova")) is acende, str(t)[:90])
        V._CONSULTA.update({"estado": "nova", "versao": u"8.4", "url": u""})
        t = V.para_a_tela()
        checar(u"com `nova`, a tela recebe as duas versoes",
               t.get("publicada") == u"8.4" and t.get("aqui") == u"8.2",
               str(t)[:90])
        checar(u"  e o link permanente do instalador",
               t.get("link") == V.link_do_instalador(), t.get("link"))
        V._CONSULTA.update({"url": u"http://127.0.0.1:9/versao.json"})
        t = V.para_a_tela()
        checar(u"  e o espelho da instituicao nao ganha link inventado",
               t.get("nova") and t.get("link") == u"", str(t)[:90])
        V._CONSULTA.update({"estado": "privado", "versao": u""})
        t = V.para_a_tela()
        checar(u"com `privado`, nada de versao nem de link na porta",
               not t.get("publicada") and not t.get("link"), str(t)[:90])
        checar(u"a resposta tem so as cinco chaves",
               sorted(t) == ["aqui", "estado", "link", "nova", "publicada"],
               str(sorted(t)))
    finally:
        V._CONSULTA.clear()
        V._CONSULTA.update(guardado)
        E.carimbo = real


def main():
    print(u"=" * 68)
    print(u"test_version | a idade do build, e a versao publicada")
    print(u"=" * 68)
    for t in (teste_comparacao, teste_derivacao, teste_consulta,
              teste_nao_bloqueia, teste_idade, teste_registro_que_mente,
              teste_o_registro_segue_a_regra_unica, teste_constante_e_porta):
        try:
            t()
        except Exception as e:
            import traceback
            checar(u"a secao %s roda ate o fim" % t.__name__, False,
                   u"%s: %s" % (type(e).__name__, e))
            if VERBOSO:
                traceback.print_exc()
    print(u"\n" + u"=" * 68)
    if _falhou:
        print(u"FALHOU: %d de %d checagens" % (_falhou, _ok + _falhou))
        for f in _falhas:
            print(u"  - %s" % f)
    else:
        print(u"OK: %d checagens, todas passaram" % _ok)
    print(u"=" * 68)
    return 1 if _falhou else 0


if __name__ == "__main__":
    sys.exit(main())
