# -*- coding: utf-8 -*-
import io
import json
import os
import shutil
import sys
import tempfile
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _cleanup
import _componentes
_cleanup.adotar_prefixo('radai_inicio_')

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(RAIZ, "app")
sys.path.insert(0, APP)

_ACERVO_TESTE = tempfile.mkdtemp(prefix="radai_inicio_acervo_")
os.environ["RADAI_CALIB_DIR"] = _ACERVO_TESTE

_ok = 0
_falhas = []


def checar(nome, cond, detalhe=u""):
    global _ok
    if cond:
        _ok += 1
        print(u"    OK     %s" % nome)
    else:
        _falhas.append(nome)
        print(u"    FALHA  %s  %s" % (nome, detalhe))


def secao(t):
    print(u"\n  ── %s %s" % (t, u"─" * max(0, 60 - len(t))))


def ler(*p):
    c = _componentes.fonte("/".join(p))
    return io.open(c, encoding="utf-8", errors="replace").read() if os.path.isfile(c) else u""


def ler_bytes(*p):
    c = _componentes.fonte("/".join(p))
    return open(c, "rb").read() if os.path.isfile(c) else b""


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


def _porta_livre():
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def teste_tela_cheia():
    secao(u"a janela do app abre em tela cheia (F11), nao maximizada")
    import radai_lancador as L
    amb = {u"ProgramFiles(x86)": u"C:\\PF86", u"ProgramFiles": u"C:\\PF",
           u"LOCALAPPDATA": u"C:\\LA", u"TEMP": u"C:\\T"}
    for rot, alvo in ((u"Edge", u"msedge.exe"), (u"Chrome", u"chrome.exe")):
        chamadas = []
        L.abrir_navegador(u"file:///C:/T/p.html", arquivo=u"C:\\T\\p.html",
                          ambiente=amb,
                          popen=lambda c, **kw: chamadas.append(c),
                          existe=lambda c, a=alvo: c.endswith(a),
                          padrao=lambda a: None)
        c = chamadas[0] if chamadas else []
        checar(u"%s: --app com --start-fullscreen" % rot,
               u"--start-fullscreen" in c and any(
                   str(x).startswith(u"--app=") for x in c), repr(c))
        checar(u"  e sem --start-maximized nem --kiosk (o F11 continua saindo)",
               u"--start-maximized" not in c and u"--kiosk" not in c, repr(c))
    cmd = ler_bytes("app", "launchers", "open_browser.cmd")
    txt = cmd.decode("ascii", "replace")
    linhas = [l for l in txt.splitlines() if u"--app=" in l]
    checar(u"o recuo do codigo 90 (open_browser.cmd) abre em tela cheia nos dois",
           len(linhas) == 2 and all(u"--start-fullscreen" in l
                                    and u"--start-maximized" not in l
                                    for l in linhas), repr(linhas))
    checar(u"  e continua em CRLF e ASCII",
           b"\r\n" in cmd and b"\n" not in cmd.replace(b"\r\n", b"")
           and all(b < 128 for b in cmd))


_MONITOR = (0, 0, 1920, 1080)
_MAXIMIZADA = (-8, -8, 1928, 1040)
_APPCMD = (u'"C:\\PF\\msedge.exe" --app=file:///C:/T/p.html '
           u'--start-fullscreen --user-data-dir=C:\\Users\\user\\AppData\\'
           u'Local\\Temp\\radai_janela --no-first-run')
_PESSOAL = u'"C:\\PF\\msedge.exe" --profile-directory=Default'


class _Plataforma(object):

    def __init__(self, janelas):
        self.j = dict(janelas)
        self.chamadas = []
        self.leituras = []

    def janelas(self):
        return list(self.j)

    def titulo(self, h):
        return self.j[h]["titulo"]

    def classe(self, h):
        return self.j[h].get("classe", u"Chrome_WidgetWin_1")

    def pid(self, h):
        return self.j[h].get("pid", 100 + h)

    def existe(self, h):
        return h in self.j

    def visivel(self, h):
        return True

    def minimizada(self, h):
        return self.j[h].get("min", False)

    def tem_barra(self, h):
        return self.j[h].get("barra", False)

    def mostrar(self, h, modo):
        self.chamadas.append((u"mostrar", h, modo))
        self.j[h]["min"] = (modo == 6)
        return True

    def trazer_para_frente(self, h):
        self.chamadas.append((u"frente", h))
        return True

    def tecla_f11(self, h):
        self.chamadas.append((u"f11", h))
        cheia = self.j[h].get("barra", False)
        self.j[h]["barra"] = not cheia
        self.j[h]["ret"] = self.monitor(h) if cheia else _MAXIMIZADA
        return True

    def retangulo(self, h):
        return self.j[h].get("ret", _MAXIMIZADA)

    def monitor(self, h):
        return self.j[h].get("mon", _MONITOR)

    def linha_de_comando(self, pid):
        self.leituras.append(pid)
        for h, d in self.j.items():
            if d.get("pid", 100 + h) == pid:
                return d.get("cmd", u"")
        return u""


def teste_a_janela_do_app():
    secao(u"a janela do app: achada pela ficha, so a do perfil do programa")
    import radai_janela as J
    J._JANELAS.clear()
    APPCMD = _APPCMD
    PESSOAL = _PESSOAL
    checar(u"o perfil do app e reconhecido pela folha radai_janela",
           J.e_do_perfil_do_app(APPCMD)
           and J.e_do_perfil_do_app(u'x --user-data-dir="C:\\T T\\radai_janela"'))
    checar(u"  (isca) o navegador pessoal e outro perfil parecido nao sao",
           not J.e_do_perfil_do_app(PESSOAL)
           and not J.e_do_perfil_do_app(
               u"x --user-data-dir=C:\\T\\radai_janela_velha")
           and not J.e_do_perfil_do_app(u""))
    f = u"rjabcdefghijklmnop12"
    checar(u"a ficha tem formato fechado (nada de texto livre no titulo)",
           J.ficha_valida(f) and not J.ficha_valida(u"a b")
           and not J.ficha_valida(u"<script>") and not J.ficha_valida(u"x"))
    pf = _Plataforma({
        1: {"titulo": u"Local Suite [%s] - Google Chrome" % f, "cmd": PESSOAL},
        2: {"titulo": u"Bloco de notas [%s]" % f, "classe": u"Notepad",
            "cmd": APPCMD},
        3: {"titulo": u"Local Suite [%s]" % f, "cmd": APPCMD, "barra": True},
        4: {"titulo": u"Local Suite", "cmd": APPCMD}})
    h = J.achar(f, pf, teto_s=0)
    checar(u"acha a janela da ficha no perfil do app, e nao a do navegador "
           u"pessoal com o mesmo titulo nem a de outra classe", h == 3, repr(h))
    checar(u"  sem a ficha no titulo, nada", J.achar(u"rjnadanadanada1234", pf,
                                                    teto_s=0) == 0)
    r = J.registrar(f, pf, teto_s=0)
    checar(u"a segunda janela de um perfil aberto nasce maximizada: o F11 vai "
           u"uma vez", r.get("ok") and r.get("tela_cheia_pedida")
           and pf.chamadas.count((u"f11", 3)) == 1, repr((r, pf.chamadas)))
    pf.j[3]["barra"] = True
    r2 = J.registrar(f, pf, teto_s=0)
    checar(u"  quem saiu da tela cheia pelo F11 nao e posto nela de novo",
           r2.get("ok") and not r2.get("nova")
           and pf.chamadas.count((u"f11", 3)) == 1, repr(r2))
    J._JANELAS.clear()
    pf.j[3]["min"] = True
    r3 = J.registrar(f, pf, teto_s=0)
    checar(u"  janela minimizada nao recebe F11 (voltaria sem tela cheia)",
           r3.get("ok") and not r3.get("tela_cheia_pedida"), repr(r3))
    pf.j[3]["min"] = False
    pf.chamadas[:] = []
    r = J.minimizar(f, pf, teto_s=0)
    checar(u"minimizar pela ficha minimiza so a janela do app",
           r.get("ok") and pf.chamadas == [(u"mostrar", 3, J.SW_MINIMIZE)],
           repr(pf.chamadas))
    pf.chamadas[:] = []
    r = J.restaurar(None, pf)
    checar(u"restaurar sem ficha usa a janela guardada pelo motor, e a traz "
           u"para a frente", r.get("ok") and (u"mostrar", 3, J.SW_RESTORE)
           in pf.chamadas and (u"frente", 3) in pf.chamadas, repr(pf.chamadas))
    del pf.j[3]
    r = J.minimizar(None, pf)
    checar(u"janela que fechou sai da lista; sem janela, a recusa diz por que",
           not r.get("ok") and r.get("motivo") == J.FRASE_SEM_JANELA
           and not J._JANELAS, repr(r))
    import radai_ui
    pg = radai_ui.aplicar(u"<html><head><title>t</title></head>"
                          u"<body><p>x</p></body></html>")
    checar(u"a casca leva o registro da janela em toda tela",
           J.MARCA in pg and u"radaiJanelaMinimizar" in pg)
    checar(u"  e o registro vai uma vez por janela e por motor (a sessao da "
           u"aba guarda o PID do motor)",
           u"sessionStorage.setItem(k, String(d.pid))" in J.JS
           and u"estado:'/api/janela/estado'" in J.JS)
    checar(u"  e a casca so fala com o motor por POST (caminho nenhum em GET)",
           u"fetch('/api/" not in J.JS.replace(u"fetch('/api/janela/estado', {method:'POST'", u"")
           and u"cache:'no-store'" not in J.JS)


def teste_a_janela_pelo_titulo_e_o_f11_que_nao_desliga():
    secao(u"a janela pelo titulo, sem ler o processo, e o F11 que nao desliga")
    import radai_janela as J
    f = u"rjqrstuvwxyz98765432"
    linhas = []
    antes = J._CTX.get("log")
    J._CTX["log"] = linhas.append
    try:
        J._JANELAS.clear()
        pf = _Plataforma({
            5: {"titulo": u"Local Suite [%s] - Google Chrome" % f,
                "cmd": _PESSOAL},
            7: {"titulo": u"Local Suite [%s]" % f, "cmd": _APPCMD,
                "barra": True}})
        h = J.achar(f, pf, teto_s=0)
        checar(u"a janela em modo de aplicativo (o titulo termina na ficha) e "
               u"achada pelo titulo", h == 7, repr(h))
        checar(u"  sem ler a linha de comando de processo nenhum",
               not pf.leituras, repr(pf.leituras))
        checar(u"  e o log diz que foi pelo titulo",
               linhas == [J.LOG_PELO_TITULO], repr(linhas))
        del pf.j[7]
        linhas[:] = []
        checar(u"  (isca) a janela de abas do navegador pessoal, com a ficha e o "
               u"nome do navegador depois dela, nao e achada",
               J.achar(f, pf, teto_s=0) == 0 and not linhas, repr(linhas))
        checar(u"  quem a recusou foi o recuo: a linha de comando do dono diz "
               u"outro perfil", pf.leituras == [105], repr(pf.leituras))
        pf.j[8] = {"titulo": u"Local Suite [%s] - Microsoft​ Edge" % f,
                   "cmd": _APPCMD}
        pf.leituras[:] = []
        h = J.achar(f, pf, teto_s=0)
        checar(u"titulo que nao termina na ficha so passa com o perfil do app "
               u"conferido pela linha de comando (o recuo)",
               h == 8 and 108 in pf.leituras, repr((h, pf.leituras)))
        checar(u"  e o log diz que foi pela linha de comando",
               linhas == [J.LOG_PELA_LINHA], repr(linhas))
        pf.j[2] = {"titulo": u"Bloco de notas [%s]" % f, "classe": u"Notepad",
                   "cmd": _APPCMD}
        del pf.j[8]
        checar(u"  (isca) outra classe com a ficha no fim do titulo nao e achada",
               J.achar(f, pf, teto_s=0) == 0)

        J._JANELAS.clear()
        pf = _Plataforma({9: {"titulo": u"Local Suite [%s]" % f,
                              "cmd": _APPCMD, "barra": True,
                              "ret": _MONITOR}})
        r = J.registrar(f, pf, teto_s=0)
        checar(u"a janela que ja cobre o monitor inteiro nao recebe F11 (ele "
               u"liga e desliga: a tiraria da tela cheia)",
               r.get("ok") and r.get("nova") and not r.get("tela_cheia_pedida")
               and (u"f11", 9) not in pf.chamadas, repr((r, pf.chamadas)))
        J._JANELAS.clear()
        pf.j[9].update(barra=True, ret=_MAXIMIZADA)
        pf.chamadas[:] = []
        r = J.registrar(f, pf, teto_s=0)
        checar(u"  a maximizada (a barra de tarefas fica de fora) recebe uma vez",
               r.get("tela_cheia_pedida") and pf.chamadas.count((u"f11", 9)) == 1,
               repr((r, pf.chamadas)))
        checar(u"  trazida para a frente antes do F11 (o Edge ignora o F11 "
               u"postado na janela de tras)",
               pf.chamadas[-2:] == [(u"frente", 9), (u"f11", 9)],
               repr(pf.chamadas))
        J._JANELAS.clear()
        pf.j[9].update(barra=True, ret=None)
        r = J.registrar(f, pf, teto_s=0)
        checar(u"  sem medida da janela, vale a barra de titulo (como antes)",
               r.get("tela_cheia_pedida"), repr(r))
        checar(u"cobrir o monitor e conter os quatro lados dele",
               J.cobre_o_monitor(_MONITOR, _MONITOR)
               and J.cobre_o_monitor((-8, -8, 1928, 1088), _MONITOR)
               and J.cobre_o_monitor((1920, 0, 3840, 1080), (1920, 0, 3840, 1080)))
        checar(u"  (isca) um pixel a menos, outro monitor ou sem medida nao cobre",
               not J.cobre_o_monitor((0, 0, 1920, 1079), _MONITOR)
               and not J.cobre_o_monitor((1, 0, 1920, 1080), _MONITOR)
               and not J.cobre_o_monitor((1920, 0, 3840, 1080), _MONITOR)
               and not J.cobre_o_monitor(None, _MONITOR)
               and not J.cobre_o_monitor(_MONITOR, None)
               and not J.cobre_o_monitor(_MONITOR, (0, 0, 0, 0)))

        pf.chamadas[:] = []
        pf.leituras[:] = []
        r = J.minimizar(None, pf)
        checar(u"minimizar sem ficha reconfere a janela guardada pelo PID e pela "
               u"classe, sem ler a linha de comando",
               r.get("ok") and (u"mostrar", 9, J.SW_MINIMIZE) in pf.chamadas
               and not pf.leituras, repr((r, pf.chamadas, pf.leituras)))
        pf.j[9]["pid"] = 4242
        r = J.restaurar(None, pf)
        checar(u"  (isca) o handle que passou a ser de outro processo sai da lista",
               not r.get("ok") and not J._JANELAS, repr(r))
        pf.j[9]["pid"] = 109
        J._JANELAS[9] = {"desde": 0, "pid": 109}
        pf.j[9]["classe"] = u"Notepad"
        r = J.restaurar(None, pf)
        checar(u"  (isca) e o que passou a ser de outra classe tambem",
               not r.get("ok") and not J._JANELAS, repr(r))

        from fastapi import FastAPI
        import radai_panel
        tela = []
        radai_panel.montar(FastAPI(), ler_vigia=lambda: {},
                           config={"registrar": tela.append})
        pf = _Plataforma({7: {"titulo": u"Local Suite [%s]" % f,
                              "cmd": _APPCMD}})
        J.achar(f, pf, teto_s=0)
        checar(u"o painel liga a linha da janela ao log da tela",
               tela == [J.LOG_PELO_TITULO], repr(tela))

        from starlette.testclient import TestClient
        app = FastAPI()
        J.montar(app, tela.append)
        tela[:] = []
        J._JANELAS.clear()
        plat = list(J._PLATAFORMA)
        J._PLATAFORMA[:] = [pf]
        try:
            d = TestClient(app, raise_server_exceptions=False).post(
                u"/api/janela/registrar", json={"ficha": f})
        finally:
            J._PLATAFORMA[:] = plat
        corpo = d.json() if d.status_code == 200 else None
        checar(u"(isca) a rota de registro montada com o log continua "
               u"registrando a janela, e o log recebe so a linha do caminho",
               isinstance(corpo, dict) and corpo.get("ok") is True
               and tela == [J.LOG_PELO_TITULO],
               repr((d.status_code, d.text[:160], tela)))
    finally:
        J._CTX["log"] = antes
        J._JANELAS.clear()


def teste_a_janela_de_verdade():
    secao(u"a janela de verdade: F11, minimizar e restaurar num Chromium")
    if os.environ.get("RADAI_JANELA_DE_VERDADE") != "1" or os.name != "nt":
        print(u"    PULADO: abre uma janela na area de trabalho de quem roda; "
              u"ligue com RADAI_JANELA_DE_VERDADE=1")
        return
    exes = [c for c in (
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
        if os.path.isfile(c)]
    if not exes:
        print(u"    PULADO: sem Edge nem Chrome")
        return
    for exe in exes:
        _uma_janela_de_verdade(exe)


def _uma_janela_de_verdade(exe):
    import subprocess
    import radai_janela as J
    nome = os.path.basename(exe)
    pasta = tempfile.mkdtemp(prefix="radai_inicio_janela_")
    perfil = os.path.join(pasta, u"radai_janela")
    f = u"rjtestedeverdade0001"
    pag = os.path.join(pasta, u"p.html")
    io.open(pag, "w", encoding="utf-8").write(
        u"<!doctype html><title>Local Suite [%s]</title><p>x</p>" % f)
    uri = u"file:///" + pag.replace(u"\\", u"/")
    base = [u"--user-data-dir=" + perfil, u"--no-first-run",
            u"--no-default-browser-check"]
    pf = J.plataforma()
    J._JANELAS.clear()
    linhas = []
    antes = J._CTX.get("log")
    J._CTX["log"] = linhas.append
    try:
        subprocess.Popen([exe, u"--app=" + uri, u"--start-maximized"] + base)
        h = J.achar(f, pf, teto_s=20)
        checar(u"[janela %s] a janela do perfil radai_janela e achada pela ficha"
               % nome, bool(h))
        if not h:
            return
        checar(u"[janela %s] pelo titulo, sem ler a linha de comando" % nome,
               linhas == [J.LOG_PELO_TITULO], repr((linhas, pf.titulo(h))))
        time.sleep(2.0)
        checar(u"[janela %s] ela nasce maximizada, com barra e sem cobrir o "
               u"monitor (a segunda janela de um perfil aberto)" % nome,
               pf.tem_barra(h) and not J.ja_cobre_o_monitor(h, pf),
               repr((pf.retangulo(h), pf.monitor(h))))
        r = J.registrar(f, pf, teto_s=5)
        time.sleep(3.0)
        checar(u"[janela %s] o registro poe em tela cheia (sem barra, cobrindo "
               u"o monitor)" % nome, r.get("tela_cheia_pedida")
               and not pf.tem_barra(h) and J.ja_cobre_o_monitor(h, pf),
               repr((r, pf.retangulo(h), pf.monitor(h))))
        J._JANELAS.clear()
        r2 = J.registrar(f, pf, teto_s=5)
        time.sleep(1.5)
        checar(u"[janela %s] a que ja esta em tela cheia nao recebe F11 de novo"
               % nome, r2.get("ok") and not r2.get("tela_cheia_pedida")
               and not pf.tem_barra(h), repr(r2))
        J.minimizar(f, pf, teto_s=5)
        time.sleep(1.5)
        checar(u"[janela %s] minimizar a minimiza" % nome, pf.minimizada(h))
        J.restaurar(None, pf)
        time.sleep(2.0)
        checar(u"[janela %s] restaurar a devolve em tela cheia" % nome,
               not pf.minimizada(h) and not pf.tem_barra(h))
    finally:
        J._CTX["log"] = antes
        ps = (u"Get-CimInstance Win32_Process -Filter \"Name='msedge.exe' OR "
              u"Name='chrome.exe'\" | Where-Object { $_.CommandLine -like '*"
              + pasta.replace(u"'", u"''") + u"*' -and $_.CommandLine "
              u"-notlike '*--type=*' } | ForEach-Object { taskkill /PID "
              u"$_.ProcessId /T /F | Out-Null }")
        subprocess.run([u"powershell", u"-NoProfile", u"-Command", ps],
                       capture_output=True)
        time.sleep(1.0)
        shutil.rmtree(pasta, ignore_errors=True)
        J._JANELAS.clear()


class _Servidor(object):

    def __init__(self, rotas, porta=0):
        import http.server
        rotas_ = rotas
        self.pedidos = []
        pedidos = self.pedidos

        class Mao(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                caminho = self.path.split("?", 1)[0]
                pedidos.append(caminho)
                f = rotas_.get(caminho)
                if f is None:
                    for k, v in rotas_.items():
                        if k.endswith("*") and caminho.startswith(k[:-1]):
                            f = v
                            break
                if f is None:
                    self.send_response(404)
                    self.end_headers()
                    return
                codigo, tipo, corpo = f(caminho)
                if isinstance(corpo, str):
                    corpo = corpo.encode("utf-8")
                self.send_response(codigo)
                self.send_header("Content-Type", tipo)
                self.send_header("Content-Length", str(len(corpo)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(corpo)

            def log_message(self, *a):
                pass

        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", porta), Mao)
        self.porta = self.httpd.server_address[1]
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def fechar(self):
        try:
            self.httpd.shutdown()
            self.httpd.server_close()
        except Exception:
            pass


def _gif():
    import radai_lancador as L
    return (200, "image/gif", L.GIF_DE_UM_PIXEL)


def teste_a_pagina_de_carregamento_pensa():
    secao(u"a abertura: as frases que trocam e o «Tentar novamente»")
    import radai_carregando as C
    pasta = tempfile.mkdtemp(prefix="radai_inicio_carr_")
    porta = _porta_livre()
    cam = C.gravar(porta, u"http://127.0.0.1:%d/" % porta, pasta=pasta,
                   pasta_do_programa=APP,
                   tradutor=lambda: ((lambda f: f), u"pt-BR"))
    h = io.open(cam, encoding="utf-8").read()
    checar(u"a pagina tem as frases da espera pela versao e o botao de tentar",
           C.FRASES["consultando"] in h and C.FRASES["nova"] in h
           and (u">%s<" % C.FRASES["tentar"]) in h)
    checar(u"  e nao tem «Ver log» nem caminho de log",
           u"Ver log" not in h and u"radai_lancador.log" not in h)
    checar(u"  a troca de frase respeita o movimento reduzido",
           u"prefers-reduced-motion" in h and u"cg-st.sai" in h)
    checar(u"  e a versao e lida por script (o file:// nao le JSON)",
           (u"'%s'" % C.ROTA_VERSAO) in h and u"window.radaiVersao" in h)
    exe = _chromium()
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        sync_playwright = None
    if not exe or sync_playwright is None:
        print(u"    PULADO o navegador: sem Playwright ou sem Chromium")
        shutil.rmtree(pasta, ignore_errors=True)
        return
    import pathlib
    t0 = [None]

    def versao_consultando(_c):
        if t0[0] is None:
            t0[0] = time.time()
        consultando = time.time() - t0[0] < 1.2
        return (200, "application/javascript",
                u"window.radaiVersao&&window.radaiVersao(%s);"
                % json.dumps({"estado": "nunca" if consultando else "atual",
                              "nova": False, "consultando": consultando}))

    def painel(_c):
        return (200, "text/html; charset=utf-8",
                u"<title>painel</title><p>o painel</p>")
    rotas = {C.ROTA_SINAL: lambda c: _gif(), C.ROTA_VERSAO: versao_consultando,
             "/": painel}
    srv = None
    vistas = []
    try:
        with sync_playwright() as pw:
            nav = pw.chromium.launch(executable_path=exe, headless=True)
            try:
                pg = nav.new_page()
                pg.expose_function("anotar", lambda t: vistas.append(t))
                pg.add_init_script(
                    u"new MutationObserver(function(){var s=document.getElementById"
                    u"('cg-st'); if(s) window.anotar(s.textContent)}).observe("
                    u"document, {subtree:true, childList:true, characterData:true});")
                pg.goto(pathlib.Path(cam).as_uri())
                pg.wait_for_timeout(800)
                srv = _Servidor(rotas, porta)
                try:
                    pg.wait_for_function(u"document.title === 'painel'",
                                         timeout=9000)
                except Exception:
                    pass
                checar(u"[navegador] com o motor no ar e a consulta em curso, diz "
                       u"«procurando atualizações…» e depois entra",
                       C.FRASES["consultando"] in vistas
                       and pg.evaluate(u"document.title") == u"painel",
                       repr(vistas[-4:]))
                srv.fechar()
                rotas[C.ROTA_VERSAO] = lambda c: (
                    200, "application/javascript",
                    u"window.radaiVersao&&window.radaiVersao("
                    u"{\"estado\":\"nova\",\"nova\":true,\"consultando\":false});")
                vistas[:] = []
                pg2 = nav.new_page()
                pg2.expose_function("anotar", lambda t: vistas.append(t))
                pg2.add_init_script(
                    u"new MutationObserver(function(){var s=document.getElementById"
                    u"('cg-st'); if(s) window.anotar(s.textContent)}).observe("
                    u"document, {subtree:true, childList:true, characterData:true});")
                srv = _Servidor(rotas, porta)
                C.gravar(porta, None, pasta=pasta, pasta_do_programa=APP,
                         tradutor=lambda: ((lambda f: f), u"pt-BR"))
                pg2.goto(pathlib.Path(cam).as_uri())
                try:
                    pg2.wait_for_function(u"document.title === 'painel'",
                                          timeout=9000)
                except Exception:
                    pass
                checar(u"[navegador] versao nova: a pagina diz «versão nova "
                       u"encontrada» antes de entrar", C.FRASES["nova"] in vistas,
                       repr(vistas[-4:]))
                srv.fechar()
                rotas[C.ROTA_VERSAO] = lambda c: (200, "text/html",
                                                  u"<html>nao e script</html>")
                srv = _Servidor(rotas, porta)
                pg3 = nav.new_page()
                C.gravar(porta, None, pasta=pasta, pasta_do_programa=APP,
                         tradutor=lambda: ((lambda f: f), u"pt-BR"))
                t = time.time()
                pg3.goto(pathlib.Path(cam).as_uri())
                try:
                    pg3.wait_for_function(u"document.title === 'painel'",
                                          timeout=9000)
                except Exception:
                    pass
                checar(u"[navegador] (isca) resposta da versao que nao e script: "
                       u"entra sem esperar o teto",
                       pg3.evaluate(u"document.title") == u"painel"
                       and time.time() - t < 3.5, u"%.1f s" % (time.time() - t))
                srv.fechar()
                srv = None
                tentativas = []

                def tentar(c):
                    tentativas.append(c)
                    C.gravar_estado(porta, u"subindo", None, pasta)
                    return _gif()
                rt = _Servidor({"/tentar/abc*": tentar})
                pg4 = nav.new_page()
                C.gravar(porta, None, pasta=pasta, pasta_do_programa=APP,
                         tradutor=lambda: ((lambda f: f), u"pt-BR"))
                pg4.goto(pathlib.Path(cam).as_uri())
                pg4.wait_for_timeout(500)
                C.gravar_estado(porta, u"saiu", 4, pasta,
                                tentar=u"http://127.0.0.1:%d/tentar/abc123"
                                % rt.porta)
                try:
                    pg4.wait_for_function(
                        u"document.documentElement.className.indexOf('parou') >= 0",
                        timeout=5000)
                except Exception:
                    pass
                vis = pg4.evaluate(u"getComputedStyle(document.getElementById("
                                   u"'cg-tentar')).display")
                checar(u"[navegador] o motor parou: o codigo e o botao «Tentar "
                       u"novamente», sem log", vis != u"none"
                       and u"código 4" in pg4.inner_text(u"body")
                       and u"log" not in pg4.inner_text(u"body").lower(),
                       vis)
                pg4.click(u"#cg-tentar")
                try:
                    pg4.wait_for_function(
                        u"document.documentElement.className.indexOf('parou') < 0",
                        timeout=5000)
                except Exception:
                    pass
                checar(u"[navegador] o clique pede ao lancador a nova tentativa "
                       u"e a pagina volta a esperar",
                       tentativas and pg4.inner_text(u"#cg-st").strip()
                       == C.FRASES["abrindo"], repr(tentativas))
                rt.fechar()
                pg5 = nav.new_page()
                C.gravar(porta, None, pasta=pasta, pasta_do_programa=APP,
                         tradutor=lambda: ((lambda f: f), u"pt-BR"))
                pg5.goto(pathlib.Path(cam).as_uri())
                pg5.wait_for_timeout(500)
                C.gravar_estado(porta, u"saiu", 7, pasta)
                try:
                    pg5.wait_for_function(
                        u"document.documentElement.className.indexOf('parou') >= 0",
                        timeout=5000)
                except Exception:
                    pass
                vis5 = pg5.evaluate(u"getComputedStyle(document.getElementById("
                                    u"'cg-tentar')).display")
                checar(u"[navegador] (isca) sem o lancador esperando, o botao nao "
                       u"aparece", vis5 == u"none", vis5)
            finally:
                nav.close()
    finally:
        if srv:
            srv.fechar()
        shutil.rmtree(pasta, ignore_errors=True)


def teste_o_lancador_tenta_de_novo():
    secao(u"o lancador espera o «Tentar novamente» e sobe o motor de novo")
    import urllib.request
    import radai_lancador as L
    avisos = []

    def informar(porta, estado, rc=None, tentar=None):
        avisos.append((estado, rc, tentar))
        return True
    res = []
    t = threading.Thread(target=lambda: res.append(L.esperar_nova_tentativa(
        8999, 4, lambda m: None, informar=informar, teto_s=10)))
    t.start()
    fim = time.time() + 5
    while time.time() < fim and not (avisos and avisos[-1][2]):
        time.sleep(0.05)
    url = avisos[-1][2] if avisos else u""
    checar(u"a pagina recebe o codigo e o endereco do pedido, com ficha",
           avisos and avisos[0][0] == L.SAIU and avisos[0][1] == 4
           and u"/tentar/" in url and len(url.rsplit(u"/", 1)[-1]) >= 16, url)
    base = url.rsplit(u"/", 1)[0]
    try:
        urllib.request.urlopen(base + u"/outra", timeout=3).read()
        recusou = False
    except Exception:
        recusou = True
    checar(u"  (isca) pedido sem a ficha nao sobe o motor", recusou and not res)
    try:
        corpo = urllib.request.urlopen(url, timeout=3).read()
    except Exception as e:
        corpo = repr(e).encode()
    t.join(5)
    checar(u"  com a ficha, ele responde uma imagem e devolve sim",
           corpo.startswith(b"GIF") and res == [True], repr((corpo[:10], res)))
    checar(u"  e a pagina volta a «subindo» antes da resposta",
           avisos[-1][0] == u"subindo", repr(avisos[-1]))
    avisos[:] = []
    r = L.esperar_nova_tentativa(8999, 9, lambda m: None, informar=informar,
                                 teto_s=1)
    checar(u"sem clique ate o teto: desiste e tira o botao da pagina",
           r is False and avisos[-1] == (L.SAIU, 9, None), repr(avisos))
    subidas, esperas = [], [(L.SAIU, 3), (L.NO_AR, 0)]
    r = L.lancar(u"http://127.0.0.1:8998/", escrever=lambda m: None,
                 subir=lambda c, cons, amb: subidas.append(c) or object(),
                 esperar=lambda p, porta, teto: esperas.pop(0),
                 anterior=lambda porta: None, console=os.path.join(
                     _ACERVO_TESTE, u"c.txt"),
                 instancia=lambda porta: (L.LIVRE, None),
                 abrir=lambda a, arquivo=None: u"x",
                 carregando=lambda porta, url: os.path.join(_ACERVO_TESTE,
                                                            u"p.html"),
                 informar=lambda *a, **k: True, travar=lambda porta: True,
                 tentar=lambda porta, rc, esc: True)
    checar(u"o lancador sobe o motor de novo depois do pedido, e fica no ar",
           r[0] == L.NO_AR and len(subidas) == 2, repr((r, len(subidas))))
    informados = []
    r = L.lancar(u"http://127.0.0.1:8998/", escrever=lambda m: None,
                 subir=lambda c, cons, amb: object(),
                 esperar=lambda p, porta, teto: (L.SAIU, 5),
                 anterior=lambda porta: None, console=os.path.join(
                     _ACERVO_TESTE, u"c.txt"),
                 instancia=lambda porta: (L.LIVRE, None),
                 abrir=lambda a, arquivo=None: u"x",
                 carregando=lambda porta, url: u"p.html",
                 informar=lambda *a, **k: informados.append(a),
                 travar=lambda porta: True)
    checar(u"  sem quem espere o clique (as baterias), sai com o codigo, como antes",
           r == (L.SAIU, 5) and informados and informados[0][1] == L.SAIU,
           repr((r, informados)))
    src = ler("app", "radai_lancador.py")
    checar(u"  e o main liga a espera do clique",
           u"tentar=esperar_nova_tentativa" in src)


def _zip_de_setup(destino, projeto=u"LOCAL_SUITE", versao=u"9.9", fuga=False,
                  pasta_raiz=u"LOCAL_SUITE_SETUP"):
    import zipfile
    with zipfile.ZipFile(destino, "w") as z:
        z.writestr(pasta_raiz + u"/entrega.txt",
                   u"PROJETO=%s\r\nVERSAO=%s\r\n" % (projeto, versao))
        z.writestr(pasta_raiz + u"/packager/UPDATE.ps1", u"# atualizador\r\n")
        z.writestr(pasta_raiz + u"/packager/prepare.ps1", u"# preparador\r\n")
        z.writestr(pasta_raiz + u"/packager/catalogo.json",
                   json.dumps({"pacote": {"download_gib": 12.5,
                                          "disco_gib": 41.0}}))
        if fuga:
            z.writestr(u"../fora_da_extracao.txt", u"fugiu")
    return destino


def teste_o_download_confere_a_soma():
    secao(u"o download do instalador: so passa o que bate com a release")
    import hashlib
    import radai_version as V
    pasta = tempfile.mkdtemp(prefix="radai_inicio_dl_")
    try:
        zipado = _zip_de_setup(os.path.join(pasta, u"setup.zip"))
        dados = open(zipado, "rb").read()
        sha = hashlib.sha256(dados).hexdigest()
        srv = _Servidor({"/a.zip": lambda c: (200, "application/zip", dados)})
        nome = V.nome_do_instalador_latest()
        url = u"http://127.0.0.1:%d/a.zip" % srv.porta
        rel = {"tag_name": "v9.9", "assets": [
            {"name": u"OUTRO.zip", "browser_download_url": url, "size": 1,
             "digest": u"sha256:" + u"0" * 64},
            {"name": nome, "browser_download_url": url, "size": len(dados),
             "digest": u"sha256:" + sha.upper()}]}
        inst = V.instalador_da_release(rel)
        checar(u"a release diz o instalador de nome fixo, o tamanho e a soma",
               inst.get("nome") == nome and inst.get("tamanho") == len(dados)
               and inst.get("sha256") == sha and inst.get("url") == url,
               repr(inst))
        r = V.baixar_instalador(inst, os.path.join(pasta, u"ok"))
        checar(u"bate o tamanho e a soma: baixa e diz onde",
               r["ok"] and os.path.isfile(r["arquivo"]) and r["bytes"] == len(dados),
               repr(r))
        errada = dict(inst, sha256=u"f" * 64)
        r = V.baixar_instalador(errada, os.path.join(pasta, u"errada"))
        checar(u"(isca) soma que nao bate: recusa e apaga o que baixou",
               not r["ok"] and u"SHA-256" in r["motivo"]
               and not os.listdir(os.path.join(pasta, u"errada")), repr(r))
        antes = len(srv.pedidos)
        r = V.baixar_instalador(dict(inst, sha256=u""), os.path.join(pasta, u"s"))
        checar(u"release sem soma publicada: nem baixa (nada sem soma e executado)",
               not r["ok"] and u"SHA-256" in r["motivo"]
               and len(srv.pedidos) == antes, repr(r))
        r = V.baixar_instalador(dict(inst, tamanho=len(dados) - 10),
                                os.path.join(pasta, u"t"))
        checar(u"(isca) tamanho que nao bate: recusa", not r["ok"], repr(r))
        r = V.baixar_instalador(dict(inst, url=u"http://exemplo.invalid/a.zip"),
                                os.path.join(pasta, u"h"))
        checar(u"endereco sem https (fora desta maquina): recusa",
               not r["ok"] and u"https" in r["motivo"], repr(r))
        r = V.baixar_instalador(dict(inst, nome=u"..\\fora.zip"),
                                os.path.join(pasta, u"n"))
        checar(u"(isca) nome com caminho: recusa", not r["ok"], repr(r))
        srv.fechar()
        src = ler("app", "radai_version.py")
        checar(u"a rede continua so no modulo declarado da consulta",
               u"urlopen" not in ler("app", "radai_atualizar.py")
               and u"urlopen" in src)
    finally:
        shutil.rmtree(pasta, ignore_errors=True)


def _com_atualizar(**trocas):
    import radai_atualizar as A
    guardado = {}
    for k, v in trocas.items():
        alvo, nome = k.split(u".", 1) if u"." in k else (u"A", k)
        mod = A if alvo == u"A" else sys.modules[alvo]
        guardado[(mod, nome)] = getattr(mod, nome)
        setattr(mod, nome, v)
    return guardado


def _desfazer(guardado):
    for (mod, nome), v in guardado.items():
        setattr(mod, nome, v)


def _esperar_etapa(A, etapas, teto=10):
    fim = time.time() + teto
    while time.time() < fim:
        if A.etapa() in etapas:
            return A.etapa()
        time.sleep(0.05)
    return A.etapa()


def teste_a_atualizacao_pelo_app():
    secao(u"o «Atualizar agora»: espera ou pergunta, baixa, confere e passa a vez")
    import radai_atualizar as A
    import radai_version as V
    import radai_queue_state as Q
    A._mudar(etapa=A.LIVRE)
    checar(u"o que segura: o turno aberto, a serie do vigia, o lote e o turno na fila",
           A.o_que_segura({"overnight": True}) == A.SEGURA_TURNO
           and A.o_que_segura({"ocupado": {"quem": "vigia"}}) == A.SEGURA_VIGIA
           and A.o_que_segura({"ocupado": {"quem": "lote"}}) == A.SEGURA_LOTE
           and A.o_que_segura({"turno_agendado": True}) == A.SEGURA_TURNO_NA_FILA
           and A.o_que_segura({"ocupado": None, "current": None}) is None)
    prog = tempfile.mkdtemp(prefix="radai_inicio_prog_")
    os.makedirs(os.path.join(prog, u"python"))
    for n in (u"python\\python.exe", u"radai_lancador.py", u"entrega.txt"):
        io.open(os.path.join(prog, n), "w").write(
            u"PROJETO=LOCAL_SUITE\nVERSAO=8.7\n" if n == u"entrega.txt" else u"#")
    checar(u"a pasta do trabalho nunca mora dentro do programa",
           A.pasta_de_trabalho(prog, base=prog) == u""
           and A.pasta_de_trabalho(prog, base=_ACERVO_TESTE) != u"")
    zipado = _zip_de_setup(os.path.join(_ACERVO_TESTE, u"s.zip"), fuga=True)
    destino = os.path.join(_ACERVO_TESTE, u"extr")
    try:
        A.extrair(zipado, destino)
        fugiu = True
    except ValueError:
        fugiu = False
    checar(u"(isca) o zip que grava fora da pasta e recusado",
           not fugiu and not os.path.exists(os.path.join(_ACERVO_TESTE,
                                                         u"fora_da_extracao.txt")))
    status = {"v": {}}
    lancados, encerrou, minimizou, segurou = [], [], [], []
    baixado = _zip_de_setup(os.path.join(_ACERVO_TESTE, u"bom.zip"),
                            versao=u"9.9")
    decisao = {"v": u"codigo"}

    def baixar(inst, pasta, progresso=None, **kw):
        os.makedirs(pasta, exist_ok=True)
        alvo = os.path.join(pasta, u"x.zip")
        shutil.copy2(baixado, alvo)
        if progresso:
            progresso(5, 10)
        return {"ok": True, "arquivo": alvo, "bytes": 10 * 1024 ** 2,
                "segundos": 2.0, "motivo": u""}
    g = _com_atualizar(
        pasta_do_programa=lambda: prog,
        _status=lambda: status["v"],
        decidir=lambda raiz, programa: (decisao["v"], u"DECISAO=" + decisao["v"]),
        lancar_atualizador=lambda raiz, programa, pid: lancados.append(
            (raiz, programa, pid)) or type("P", (), {"pid": 4242})(),
        _encerrar_o_motor=lambda porta, atraso_s=0: encerrou.append(porta),
        _minimizar_as_janelas=lambda: minimizou.append(1),
        pasta_de_trabalho=lambda programa, base=None: os.path.join(
            _ACERVO_TESTE, u"trab"),
        **{"radai_version.ultima_consulta": lambda hoje=None: {
            "estado": u"nova", "versao": u"9.9",
            "instalador": {"url": u"https://x/y.zip", "nome": u"y.zip",
                           "tamanho": 10, "sha256": u"a" * 64}},
           "radai_version.baixar_instalador": baixar,
           "radai_queue_state.pedir_fechar_ao_fim":
               lambda sim=True: segurou.append(bool(sim)) or bool(sim)})
    try:
        status["v"] = {"ocupado": {"quem": "vigia"}}
        d = A.agir(u"comecar", 8777)
        checar(u"com serie do vigia rodando: nao baixa nada e pergunta",
               d["etapa"] == A.OCUPADO and d["motivo_chave"] == A.SEGURA_VIGIA
               and not lancados)
        d = A.agir(u"esperar", 8777)
        checar(u"«Atualizar quando terminar»: espera, e o vigia e o lote nao "
               u"comecam serie nova", d["etapa"] == A.ESPERANDO
               and segurou[-1] is True)
        time.sleep(0.3)
        checar(u"  enquanto roda, continua esperando", A.etapa() == A.ESPERANDO
               and not lancados)
        status["v"] = {}
        e = _esperar_etapa(A, (A.FECHANDO, A.ERRO), teto=10)
        checar(u"  terminou a serie: baixa, confere, decide e passa a vez ao "
               u"atualizador, que espera este PID e reabre",
               e == A.FECHANDO and lancados and lancados[-1][2] == os.getpid()
               and lancados[-1][1] == prog, repr((e, lancados, A._E)))
        checar(u"  e o app minimiza a janela e pede o proprio encerramento",
               minimizou and encerrou == [8777], repr((minimizou, encerrou)))
        A._mudar(etapa=A.LIVRE)
        lancados[:] = []
        encerrou[:] = []
        status["v"] = {"overnight": True}
        d = A.agir(u"comecar", 8777)
        checar(u"turno aberto: pergunta", d["etapa"] == A.OCUPADO
               and d["motivo_chave"] == A.SEGURA_TURNO)
        d = A.agir(u"interromper", 8777)
        e = _esperar_etapa(A, (A.FECHANDO, A.ERRO), teto=10)
        checar(u"«Interromper e atualizar» (confirmado na tela): segue mesmo com "
               u"o turno aberto", e == A.FECHANDO and lancados, repr(A._E))
        A._mudar(etapa=A.LIVRE)
        lancados[:] = []
        encerrou[:] = []
        status["v"] = {}
        decisao["v"] = u"pacote"
        d = A.agir(u"comecar", 8777)
        e = _esperar_etapa(A, (A.BUNDLE, A.ERRO), teto=10)
        with A._TRAVA:
            dd = dict(A._E)
        checar(u"precisa de pacote novo: para e pede a segunda confirmacao, com "
               u"o tamanho do catalogo e o tempo pela velocidade medida",
               e == A.BUNDLE and dd["tamanho_gib"] == 12.5 and dd["tempo_min"]
               and not lancados and segurou[-1] is False, repr(dd))
        pre = []
        g2 = _com_atualizar(lancar_preparador=lambda raiz, programa, aqui:
                            pre.append((raiz, programa)))
        d = A.agir(u"bundle", 8777)
        _desfazer(g2)
        checar(u"  a segunda confirmacao abre o preparador da versao nova, na "
               u"tela de licencas, com o app intacto",
               d["etapa"] == A.PREPARADOR and pre and pre[0][1] == prog
               and not encerrou, repr(d))
        A._mudar(etapa=A.BUNDLE)
        d = A.agir(u"cancelar", 8777)
        checar(u"  «Agora não»: volta ao livre e solta a fila",
               d["etapa"] == A.LIVRE and segurou[-1] is False)
        decisao["v"] = u"codigo"
        g3 = _com_atualizar(**{"radai_version.ultima_consulta": lambda hoje=None: {
            "estado": u"atual", "versao": u"8.7"}})
        d = A.agir(u"comecar", 8777)
        _desfazer(g3)
        checar(u"sem versao nova: nao faz nada e diz", d["etapa"] == A.ERRO
               and d["motivo_chave"] == A.M_SEM_NOVA)
        g4 = _com_atualizar(pasta_do_programa=lambda: _ACERVO_TESTE)
        d = A.agir(u"comecar", 8777)
        _desfazer(g4)
        checar(u"rodando fora de uma instalacao (o repositorio): recusa",
               d["etapa"] == A.ERRO and d["motivo_chave"] == A.M_NAO_INSTALADO)
        A._mudar(etapa=A.LIVRE)
        outro = _zip_de_setup(os.path.join(_ACERVO_TESTE, u"outro.zip"),
                              projeto=u"OUTRO_PROJETO")
        g5 = _com_atualizar(**{"radai_version.baixar_instalador":
                               lambda inst, pasta, progresso=None, **kw: {
                                   "ok": True, "arquivo": outro, "bytes": 1,
                                   "segundos": 0.0, "motivo": u""}})
        A.agir(u"comecar", 8777)
        e = _esperar_etapa(A, (A.FECHANDO, A.ERRO, A.BUNDLE), teto=10)
        _desfazer(g5)
        checar(u"(isca) instalador de outro projeto: nada roda",
               e == A.ERRO and A._E["motivo_chave"] == A.M_OUTRO
               and not lancados, repr(A._E))
    finally:
        _desfazer(g)
        A._mudar(etapa=A.LIVRE)
        shutil.rmtree(prog, ignore_errors=True)
    trab = os.path.join(_ACERVO_TESTE, u"trab_limpeza")
    for sub in (u"baixado", u"extraido"):
        os.makedirs(os.path.join(trab, sub))
        io.open(os.path.join(trab, sub, u"x"), "w").write(u"x")
    g6 = _com_atualizar(pasta_de_trabalho=lambda programa, base=None: trab)
    A.limpar_o_baixado(u"C:\\qualquer")
    _desfazer(g6)
    checar(u"no arranque sai so o .zip baixado; a pasta extraida (do preparador "
           u"ou do atualizador terminando) fica",
           not os.path.exists(os.path.join(trab, u"baixado"))
           and os.path.isfile(os.path.join(trab, u"extraido", u"x")))
    try:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
    except Exception:
        print(u"    PULADO a rota: sem fastapi")
        return
    app = FastAPI()
    A.montar(app, ler_vigia=lambda: {}, registrar=lambda m: None)
    cli = TestClient(app, base_url="http://127.0.0.1:8777")
    r = cli.post("/api/atualizar", json={"acao": "comecar"})
    checar(u"a rota so aceita a propria tela (sem Origin: 403)",
           r.status_code == 403, r.status_code)
    r = cli.post("/api/atualizar", json={"acao": "comecar"},
                 headers={"Origin": "http://exemplo.invalid"})
    checar(u"  (isca) de outro site tambem nao", r.status_code == 403)
    js = cli.get("/api/versao.js")
    checar(u"a versao para a pagina de abertura sai como script, sem cache",
           js.status_code == 200 and u"window.radaiVersao" in js.text
           and u"javascript" in js.headers.get("content-type", u"")
           and js.headers.get("cache-control") == u"no-store", js.text[:80])


ATUALIZAR = os.path.join(RAIZ, "packager", "UPDATE.ps1")


def _pacote_leve(base, versao, projeto=u"LOCAL_SUITE"):
    p = os.path.join(base, "pacote")
    for sub in ("app", "tools", "build", "packager"):
        os.makedirs(os.path.join(p, sub), exist_ok=True)
    io.open(os.path.join(p, "entrega.txt"), "w").write(
        u"PROJETO=%s\nVERSAO=%s\n" % (projeto, versao))
    for n in ("radai_watcher.py", "engine.py", "radai_geom.py"):
        io.open(os.path.join(p, "app", n), "w").write(u"# %s versao %s\n" % (n, versao))
    io.open(os.path.join(p, "app", "RADIOTERAPIA_AI_LOCAL_SUITE.cmd"), "w").write(
        u"@echo off\r\n")
    io.open(os.path.join(p, "app", "radai_lancador.py"), "w").write(
        u"import sys, os\n"
        u"open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "
        u"'reaberto.txt'), 'w').write(' '.join(sys.argv[1:]))\n")
    for f_ in ("requisitos.py", "requirements-demo.txt",
               "configurar_ambiente.py", "artefatos.py"):
        shutil.copy2(os.path.join(RAIZ, "build", f_), os.path.join(p, "build", f_))
    for rel in ("app/radai_tasks.py", "app/radai_models.py"):
        shutil.copy2(_componentes.fonte(rel), os.path.join(p, rel.replace("/", os.sep)))
    shutil.copy2(ATUALIZAR, os.path.join(p, "packager", "UPDATE.ps1"))
    return p


def _instalacao_leve(base, versao, pacote, porta, igual=True,
                     projeto=u"LOCAL_SUITE"):
    raiz = os.path.join(base, "RADIOTERAPIA_AI")
    inst = os.path.join(raiz, projeto)
    os.makedirs(os.path.join(inst, "python"))
    for n in ("radai_watcher.py", "engine.py", "radai_geom.py"):
        io.open(os.path.join(inst, n), "w").write(u"# %s ANTIGO\n" % n)
    io.open(os.path.join(inst, "entrega.txt"), "w").write(
        u"PROJETO=%s\nVERSAO=%s\n" % (projeto, versao))
    io.open(os.path.join(inst, "radai_watcher.config"), "w").write(
        u"PORT=%d\n" % porta)
    sys.path.insert(0, os.path.join(RAIZ, "build"))
    import requisitos as R
    d = R.calcular(pacote)
    d["versao"] = versao
    if not igual:
        d["impressao"] = u"0" * 12
        d["requisitos"] = list(d.get("requisitos") or []) + [u"pacote-novo==1.0"]
    io.open(os.path.join(inst, "_requisitos.json"), "w").write(json.dumps(d))
    return raiz, inst


def _rodar_ps(script, args, amb, timeout=300):
    import subprocess
    env = dict(os.environ)
    env.update(amb)
    p = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy",
         "Bypass", "-File", script] + args,
        capture_output=True, stdin=subprocess.DEVNULL, env=env, timeout=timeout)
    return p.returncode, ((p.stdout or b"") + (p.stderr or b"")).decode(
        "cp1252", "replace")


def _funcoes_ps1(texto):
    import re as _re
    achadas, atual, nome = {}, [], None
    for linha in texto.replace("\r\n", "\n").split("\n"):
        if nome is None:
            m = _re.match(r"function ([\w-]+)\(", linha)
            if not m:
                continue
            if linha.count("{") and linha.count("{") == linha.count("}"):
                achadas[m.group(1)] = linha
                continue
            nome, atual = m.group(1), [linha]
            continue
        atual.append(linha)
        if linha == "}":
            achadas[nome] = "\n".join(atual)
            nome = None
    return achadas


def teste_o_atualizador_decide_espera_e_reabre():
    secao(u"o UPDATE.ps1 do «Atualizar agora»: decide, espera o app, refaz os "
          u"atalhos e reabre")
    import subprocess
    base = tempfile.mkdtemp(prefix="radai_inicio_upd_")
    ad = os.path.join(base, u"ad")
    os.makedirs(ad)
    amb = {"LOCALAPPDATA": ad, "RADAI_ATALHOS_NA_RAIZ": "1"}
    try:
        pac = _pacote_leve(base, u"8.8")
        raiz, inst = _instalacao_leve(base, u"8.7", pac, _porta_livre())
        upd = os.path.join(pac, "packager", "UPDATE.ps1")
        rc, t = _rodar_ps(upd, ["-Destino", inst, "-Python", sys.executable,
                                "-SoDecidir"], amb)
        checar(u"-SoDecidir com a impressao igual: 0, DECISAO=codigo, e nada muda",
               rc == 0 and u"DECISAO=codigo" in t
               and u"ANTIGO" in io.open(os.path.join(inst, "engine.py")).read()
               and not os.path.exists(os.path.join(raiz, "_atalhos_desktop")),
               t[-300:])
        base2 = tempfile.mkdtemp(prefix="radai_inicio_upd2_", dir=base)
        raiz2, inst2 = _instalacao_leve(base2, u"8.7", pac, _porta_livre(),
                                        igual=False)
        rc, t = _rodar_ps(upd, ["-Destino", inst2, "-Python", sys.executable,
                                "-SoDecidir"], amb)
        checar(u"-SoDecidir com a impressao diferente: 3, DECISAO=pacote",
               rc == 3 and u"DECISAO=pacote" in t, t[-300:])
        dorme = subprocess.Popen([sys.executable, "-c",
                                  "import time; time.sleep(4)"])
        t0 = time.time()
        rc, t = _rodar_ps(upd, ["-Destino", inst, "-Python", sys.executable,
                                "-SemPerguntar", "-EsperarPid", str(dorme.pid),
                                "-Reabrir"], amb)
        dt = time.time() - t0
        checar(u"espera o app que pediu a atualizacao fechar sozinho antes de "
               u"tocar no codigo", rc == 0 and u"esperando o app fechar" in t
               and u"o app fechou" in t and dt >= 2.5, u"%.1f s | %s" % (dt, t[-300:]))
        checar(u"  e atualiza", u"versao 8.8" in io.open(
            os.path.join(inst, "engine.py")).read())
        for sub in (u"_atalhos_desktop", u"_atalhos_menu"):
            lnk = os.path.join(raiz, sub, u"Radioterapia.ai Local Suite.lnk")
            checar(u"  refaz o atalho que faltava (%s)" % sub, os.path.isfile(lnk),
                   lnk)
        fim = time.time() + 15
        marca = os.path.join(inst, u"reaberto.txt")
        while time.time() < fim and not os.path.isfile(marca):
            time.sleep(0.2)
        arg = io.open(marca).read() if os.path.isfile(marca) else u""
        checar(u"  e reabre o app pelo lancador, como sucessor do PID que saiu",
               (u"--sucessor %d" % dorme.pid) in arg and u"--url" in arg, arg)
        checar(u"  com o log da atualizacao na pasta do programa",
               os.path.isfile(os.path.join(inst, u"radai_atualizar.log")))
        io.open(os.path.join(inst, "entrega.txt"), "w").write(
            u"PROJETO=LOCAL_SUITE\nVERSAO=8.7\n")
        os.remove(marca)
        shutil.copy2(os.path.join(pac, "app", "radai_lancador.py"),
                     os.path.join(inst2, "radai_lancador.py"))
        rc, t = _rodar_ps(upd, ["-Destino", inst2, "-Python", sys.executable,
                                "-SemPerguntar", "-Reabrir"], amb)
        checar(u"precisa de pacote: nao toca no codigo e ainda assim reabre o app",
               rc == 3 and u"ANTIGO" in io.open(os.path.join(inst2, "engine.py")).read()
               and u"reabrindo o app" in t, t[-300:])
        a = _funcoes_ps1(io.open(os.path.join(RAIZ, "installer", "INSTALL.ps1"),
                                 encoding="utf-8-sig").read())
        b = _funcoes_ps1(io.open(ATUALIZAR, encoding="utf-8-sig").read())
        checar(u"os atalhos se fazem pela MESMA funcao no INSTALL.ps1 e no "
               u"UPDATE.ps1", a.get("CriarAtalhos") and
               a.get("CriarAtalhos") == b.get("CriarAtalhos"))
        checar(u"  (isca) uma letra trocada numa delas e acusada",
               a.get("CriarAtalhos", u"").replace(u"Local Suite.lnk",
                                                  u"Local  Suite.lnk")
               != b.get("CriarAtalhos"))
    finally:
        shutil.rmtree(base, ignore_errors=True)


def teste_o_guia_inicial_no_dado():
    secao(u"o guia inicial: os passos, a marca da estacao e o nome do componente")
    import radai_roteiro as G
    import radai_phrases as F
    checar(u"de 6 a 8 passos, cada um numa tela de verdade",
           6 <= len(G.PASSOS) <= 8
           and all(p["rota"].startswith(u"/") for p in G.PASSOS))
    rotas = [p["rota"] for p in G.PASSOS]
    checar(u"  passa pelo DicomBridge, pelo ContourLab, pelas Reconstrucoes "
           u"(anatomia geral) e pelas Configuracoes",
           u"/bridge/laudo" in rotas and u"/lote" in rotas
           and u"/recon3d/anatomia" in rotas and u"/config" in rotas, repr(rotas))
    lote = [p for p in G.PASSOS if p["rota"] == u"/lote"][0]
    checar(u"  e o passo do ContourLab repete a fronteira (sugestão não aprovada, "
           u"revisão médica)", u"sugestão não aprovada" in lote["texto"]
           and u"revisão médica" in lote["texto"])
    js = G.PARA_A_CASCA
    checar(u"«Pular guia» em todo passo, e o contrato window.radaiGuiaAbrir",
           u"rt-pular" in js and u"window.radaiGuiaAbrir = function" in js
           and G.ROTULOS["pular"] == u"Pular guia")
    checar(u"  sem reaproveitar o nome uiGuia (que e o componente de abas)",
           u"uiGuia" not in js)
    import re as _re
    import radai_janela as _J
    import radai_atualizar as _A
    chamadas = []
    for mod in (G, _J, _A):
        for m in _re.finditer(r"fetch\((.*?)\)\s*(?:\.then|;)", mod.PARA_A_CASCA, _re.S):
            chamadas.append(m.group(1))
    sem_post = [c[:60] for c in chamadas if u"method:'POST'" not in c]
    checar(u"as pecas da casca (guia, janela, atualizar) so falam com o motor por POST",
           len(chamadas) >= 6 and not sem_post, repr((len(chamadas), sem_post)))
    chaves = set(F.normalizar(l[0]) for l in F.TABELA)
    textos = [p["titulo"] for p in G.PASSOS] + [p["texto"] for p in G.PASSOS] \
        + list(G.ROTULOS.values())
    sem = [t for t in textos if F.normalizar(t) not in chaves]
    checar(u"  e todo texto do guia tem chave nos doze idiomas", not sem,
           repr(sem[:3]))
    cfg = os.path.join(_ACERVO_TESTE, u"cfg_guia", u"radai_watcher.config")
    os.makedirs(os.path.dirname(cfg))
    io.open(cfg, "w", encoding="utf-8").write(u"ROOT=C:\\x\nPORT=8777\n")
    antes = os.environ.get("RADAI_CONFIG")
    os.environ["RADAI_CONFIG"] = cfg
    try:
        checar(u"estacao nova: o guia nao foi visto", not G.visto(G.ler_marca()))
        ok, _ = G.gravar_marca()
        txt = io.open(cfg, encoding="utf-8").read()
        checar(u"a marca e a chave GUIA_VISTO do config, uma vez por estacao, e "
               u"o resto do config fica", ok and u"GUIA_VISTO=1" in txt
               and u"ROOT=C:\\x" in txt and G.visto(G.ler_marca()), txt)
        checar(u"  (isca) marca de outra versao do guia nao conta como vista",
               not G.visto(u"0") and not G.visto(u""))
    finally:
        if antes is None:
            os.environ.pop("RADAI_CONFIG", None)
        else:
            os.environ["RADAI_CONFIG"] = antes


class _Uvicorn(object):

    def __init__(self, app, porta):
        import uvicorn
        self.srv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1",
                                                 port=porta, log_level="error"))
        self.t = threading.Thread(target=self.srv.run, daemon=True)
        self.t.start()
        fim = time.time() + 15
        while time.time() < fim and not self.srv.started:
            time.sleep(0.05)

    def fechar(self):
        self.srv.should_exit = True
        self.t.join(10)


def _app_da_casca(status, cfg, janela=None):
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse
    import radai_router
    import radai_languages
    import radai_menu
    import radai_janela
    import radai_roteiro
    import radai_atualizar
    import radai_ui
    app = FastAPI()
    janela = janela if janela is not None else {"ok": True}

    @app.post("/api/janela/registrar")
    def _registrar():
        return {"ok": bool(janela["ok"])}
    radai_router.montar(app)
    radai_languages.montar(app)
    radai_janela.montar(app)
    radai_roteiro.montar(app)
    radai_atualizar.montar(app, ler_vigia=lambda: status["v"],
                           registrar=lambda m: None)
    radai_ui.montar_icone(app)

    @app.get("/api/pulso")
    def _pulso():
        return {"radai": True, "pid": os.getpid()}

    def tela(chave, corpo):
        return radai_menu.aplicar(
            u"<!doctype html><html><head><meta charset='utf-8'><title>%s"
            u"</title></head><body>%s</body></html>" % (chave, corpo), chave)

    @app.get("/bridge/laudo", response_class=HTMLResponse)
    def _bridge():
        return tela(u"bridge_laudo", radai_ui.area_de_envio(u"x"))

    @app.get("/config", response_class=HTMLResponse)
    def _config():
        import radai_panel
        return radai_menu.aplicar(radai_panel.PAGINA_CONFIG, "config")

    for rota in (u"/autocontorno", u"/lote", u"/ver", u"/recon3d/anatomia"):
        def _t(r=rota):
            return HTMLResponse(tela(r.strip(u"/").replace(u"/", u"_"),
                                     u"<p><a href='/lote'>Rodar agora</a></p>"))
        app.get(rota)(_t)
    return app


def teste_o_guia_e_o_popup_no_navegador():
    secao(u"o guia e o popup de atualizacao, renderizados (1280 x 800, dois temas)")
    exe = _chromium()
    try:
        from playwright.sync_api import sync_playwright
        import uvicorn
    except Exception:
        sync_playwright = None
    if not exe or sync_playwright is None:
        print(u"    PULADO: sem Playwright, uvicorn ou Chromium")
        return
    import radai_atualizar as A
    import radai_version as V
    telas = os.environ.get("RADAI_TELAS_DIR") or u""
    cfg = os.path.join(_ACERVO_TESTE, u"cfg_nav", u"radai_watcher.config")
    os.makedirs(os.path.dirname(cfg))
    io.open(cfg, "w", encoding="utf-8").write(u"PORT=8777\n")
    antes = os.environ.get("RADAI_CONFIG")
    os.environ["RADAI_CONFIG"] = cfg
    status = {"v": {}}
    janela = {"ok": False}
    porta = _porta_livre()
    srv = _Uvicorn(_app_da_casca(status, cfg, janela), porta)
    base = u"http://127.0.0.1:%d" % porta
    g = None
    try:
        with sync_playwright() as pw:
            nav = pw.chromium.launch(executable_path=exe, headless=True)
            try:
                ctx = nav.new_context(viewport={"width": 1280, "height": 800})
                pg0 = ctx.new_page()
                pg0.goto(base + u"/")
                pg0.wait_for_timeout(3500)
                checar(u"[guia] (isca) fora da janela do app (aba comum, navegador "
                       u"de bateria): o guia nao se impoe",
                       pg0.evaluate(u"document.querySelectorAll('.rt-cartao')"
                                    u".length") == 0
                       and u"GUIA_VISTO" not in io.open(cfg, encoding="utf-8").read())
                pg0.close()
                janela["ok"] = True
                pg = ctx.new_page()
                pg.goto(base + u"/")
                try:
                    pg.wait_for_selector(u".rt-cartao.vis[data-roteiro-passo='0']",
                                         timeout=8000)
                    abriu = True
                except Exception:
                    abriu = False
                checar(u"[guia] estacao nova: o guia abre sozinho na porta, "
                       u"no passo 1", abriu)
                pg.wait_for_timeout(400)
                checar(u"  e a marca GUIA_VISTO foi gravada (uma vez por estacao)",
                       u"GUIA_VISTO=1" in io.open(cfg, encoding="utf-8").read())
                checar(u"  o cartao e um dialogo com titulo e texto, e o foco no "
                       u"«Próximo»", pg.evaluate(
                           u"(function(){var c=document.querySelector('.rt-cartao');"
                           u"return c.getAttribute('role')==='dialog' && "
                           u"document.activeElement===c.querySelector('.rt-proximo')"
                           u"})()"))
                if telas:
                    pg.screenshot(path=os.path.join(telas, u"guia_1_porta.png"))
                pg.click(u".rt-proximo")
                pg.wait_for_selector(u".rt-cartao.vis[data-roteiro-passo='1']",
                                     timeout=5000)
                pg.wait_for_timeout(1600)
                sobre = pg.evaluate(
                    u"(function(){var f=document.querySelector('.rt-furo');"
                    u"var a=document.querySelector('a[href=\"/bridge\"]');"
                    u"if(!f||!a) return 'sem';var r=f.getBoundingClientRect(),"
                    u"s=a.getBoundingClientRect();return (f.classList.contains('vis')"
                    u"&& r.left<=s.left && r.right>=s.right && r.top<=s.top && "
                    u"r.bottom>=s.bottom) ? 'ok' : JSON.stringify([r,s])})()")
                checar(u"[guia] o passo do DicomBridge acende o cartao dele na porta",
                       sobre == u"ok", sobre)
                if telas:
                    pg.screenshot(path=os.path.join(telas, u"guia_2_dicombridge.png"))
                pg.click(u".rt-proximo")
                try:
                    pg.wait_for_url(base + u"/bridge/laudo", timeout=8000)
                    pg.wait_for_selector(u".rt-cartao.vis[data-roteiro-passo='2']",
                                         timeout=8000)
                    seguiu = True
                except Exception:
                    seguiu = False
                checar(u"[guia] «Próximo» leva a tela de verdade e o guia continua "
                       u"la", seguiu, pg.url)
                pg.click(u".rt-pular")
                pg.wait_for_timeout(500)
                checar(u"[guia] «Pular guia» fecha e nao volta",
                       pg.evaluate(u"document.querySelectorAll('.rt-cartao').length")
                       == 0 and pg.evaluate(
                           u"sessionStorage.getItem('radai_roteiro_passo')") is None)
                pg.goto(base + u"/")
                pg.wait_for_timeout(2200)
                checar(u"  na porta de novo, ja visto: nao abre sozinho",
                       pg.evaluate(u"document.querySelectorAll('.rt-cartao').length")
                       == 0)
                pg.goto(base + u"/config")
                pg.wait_for_timeout(600)
                pg.evaluate(u"window.radaiGuiaAbrir()")
                try:
                    pg.wait_for_url(base + u"/", timeout=8000)
                    pg.wait_for_selector(u".rt-cartao.vis[data-roteiro-passo='0']",
                                         timeout=8000)
                    reviu = True
                except Exception:
                    reviu = False
                checar(u"[guia] «Ver o guia de novo» (radaiGuiaAbrir) recomeca do "
                       u"passo 1, na porta", reviu, pg.url)
                pg.keyboard.press(u"Escape")
                pg.wait_for_timeout(400)
                checar(u"  e o Esc fecha",
                       pg.evaluate(u"document.querySelectorAll('.rt-cartao').length")
                       == 0)
                if telas:
                    for tema in (u"escuro", u"claro"):
                        pt = ctx.new_page()
                        pt.add_init_script(u"try{localStorage.setItem('radai_tema',"
                                           u"'%s')}catch(e){}" % tema)
                        pt.goto(base + u"/config")
                        pt.wait_for_timeout(500)
                        pt.evaluate(u"sessionStorage.setItem('radai_roteiro_passo','7')")
                        pt.reload()
                        pt.wait_for_selector(u".rt-cartao.vis", timeout=8000)
                        pt.wait_for_timeout(500)
                        pt.screenshot(path=os.path.join(
                            telas, u"guia_8_config_%s.png" % tema))
                        pt.close()
                g = _com_atualizar(
                    e_instalacao=lambda p: True,
                    **{"radai_version.ultima_consulta": lambda hoje=None: {
                        "estado": u"nova", "versao": u"8.8", "instalador": {}},
                       "radai_version.para_a_tela": lambda: {
                           "estado": u"nova", "nova": True, "publicada": u"8.8",
                           "aqui": u"8.7", "link": u"https://exemplo.invalid/x.zip"}})
                status["v"] = {"ocupado": {"quem": "vigia"}}
                for tema in (u"escuro", u"claro"):
                    pu = ctx.new_page()
                    pu.add_init_script(u"try{localStorage.setItem('radai_tema',"
                                       u"'%s')}catch(e){}" % tema)
                    pu.goto(base + u"/config")
                    pu.wait_for_timeout(500)
                    pu.evaluate(u"window.radaiAtualizarAgora()")
                    pu.wait_for_selector(u".ra-modal .ra-bts .perigo", timeout=6000)
                    pu.wait_for_timeout(400)
                    n = pu.evaluate(u"document.querySelectorAll('.ra-bts button').length")
                    checar(u"[popup %s] com serie rodando: esperar, interromper "
                           u"ou cancelar" % tema, n == 3, str(n))
                    if telas:
                        pu.screenshot(path=os.path.join(
                            telas, u"atualizar_ocupado_%s.png" % tema))
                    pu.click(u".ra-bts .perigo")
                    pu.wait_for_timeout(300)
                    checar(u"  interromper pede uma segunda confirmacao, e nada "
                           u"comeca ainda", A.etapa() == A.OCUPADO
                           and pu.evaluate(u"document.querySelectorAll("
                                           u"'.ra-bts .perigo').length") == 1)
                    pu.close()
                    A._mudar(etapa=A.BUNDLE, tamanho_gib=12.5, tempo_min=95,
                             versao_nova=u"8.8")
                    pn = ctx.new_page()
                    pedidos_n = []
                    pn.on(u"request", lambda rq: pedidos_n.append(rq.url))
                    pn.goto(base + u"/config")
                    pn.wait_for_timeout(1500)
                    checar(u"[popup %s] (isca) aba que nao pediu a atualizacao nao "
                           u"pergunta o estado dela" % tema,
                           not [u for u in pedidos_n if u.endswith(u"/api/atualizar")]
                           and pn.evaluate(u"document.querySelectorAll('.ra-modal')"
                                           u".length") == 0, repr(pedidos_n[-5:]))
                    pn.close()
                    pb = ctx.new_page()
                    pb.add_init_script(u"try{localStorage.setItem('radai_tema',"
                                       u"'%s');sessionStorage.setItem("
                                       u"'radai_atualizar_pedido','1')}catch(e){}" % tema)
                    pb.goto(base + u"/config")
                    try:
                        pb.wait_for_selector(u".ra-modal .ra-bts .pri", timeout=6000)
                        reabriu = True
                    except Exception:
                        reabriu = False
                    checar(u"[popup %s] o pedido de pacote novo reabre sozinho em "
                           u"qualquer tela, com o tamanho e o tempo" % tema,
                           reabriu and u"13" in pb.inner_text(u".ra-txt"),
                           pb.inner_text(u".ra-txt")[:120] if reabriu else u"")
                    pb.wait_for_timeout(400)
                    if telas:
                        pb.screenshot(path=os.path.join(
                            telas, u"atualizar_bundle_%s.png" % tema))
                    pb.close()
                    A._mudar(etapa=A.LIVRE)
            finally:
                nav.close()
    finally:
        if g:
            _desfazer(g)
        A._mudar(etapa=A.LIVRE)
        srv.fechar()
        if antes is None:
            os.environ.pop("RADAI_CONFIG", None)
        else:
            os.environ["RADAI_CONFIG"] = antes


def _harness_do_preparador(funcoes, corpo):
    import subprocess
    prep = os.path.join(RAIZ, "packager", "prepare.ps1")
    cab = (u"[Console]::OutputEncoding = [System.Text.Encoding]::UTF8\n"
           u"$ErrorActionPreference = 'Stop'\nSet-StrictMode -Version Latest\n"
           u"$e = $null; $t = $null\n"
           u"$ast = [System.Management.Automation.Language.Parser]::ParseFile('%s', [ref]$t, [ref]$e)\n"
           u"foreach ($n in @(%s)) {\n"
           u"  $f = $ast.FindAll({ param($x) $x -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $x.Name -eq $n }, $true) | Select-Object -First 1\n"
           u"  if (-not $f) { 'SEM_FUNCAO:' + $n; continue }\n"
           u"  . ([scriptblock]::Create($f.Extent.Text))\n"
           u"}\n" % (prep.replace(u"'", u"''"),
                     u", ".join(u"'%s'" % f for f in funcoes)))
    pasta = tempfile.mkdtemp(prefix="radai_inicio_ps_")
    try:
        s = os.path.join(pasta, u"h.ps1")
        io.open(s, "w", encoding="utf-8-sig", newline="\r\n").write(cab + corpo)
        env = dict(os.environ)
        env.pop("PSModulePath", None)
        p = subprocess.run(["powershell", "-NoProfile", "-NonInteractive",
                            "-ExecutionPolicy", "Bypass", "-File", s],
                           capture_output=True, timeout=180, env=env)
        out = (p.stdout or b"").decode("utf-8", "replace")
        if not out.strip():
            out = (p.stdout or b"").decode("cp1252", "replace") + \
                (p.stderr or b"").decode("cp1252", "replace")
        marcas = {}
        for l in out.splitlines():
            if u":" in l:
                k, v = l.split(u":", 1)
                if k.isupper():
                    marcas[k] = v.strip()
        return marcas, out
    finally:
        shutil.rmtree(pasta, ignore_errors=True)


def teste_o_instalador_vai_para_a_etapa_4():
    secao(u"o instalador: depois do so-codigo, a etapa 4 com o botao verde de abrir o app")
    corpo = (u"[Console]::OutputEncoding = [System.Text.Encoding]::UTF8\n"
             u". '%(lang)s'\n[void](Carregar-Idiomas '%(pack)s')\n"
             u"$txt4 = [pscustomobject]@{ Text = '' }\n"
             u"$aba4 = [pscustomobject]@{ Nome = 'aba4' }\n"
             u"$abas = [pscustomobject]@{ SelectedTab = $null }\n"
             u"function CaminhoDoPrograma { if ($script:PastaInstalada) { return ($script:PastaInstalada + '\\RADIOTERAPIA_AI_LOCAL_SUITE.cmd') } return '' }\n"
             u"$btAbrirPrograma = [pscustomobject]@{ Visible = $false; Enabled = $false; Left = 0 }\n"
             u"$btAbrirPasta = [pscustomobject]@{ Visible = $false; Enabled = $false; Left = 0 }\n"
             u"$btFechar = [pscustomobject]@{ Visible = $false; Enabled = $false; Left = 0 }\n"
             u"$script:PastaInstalada = ''\n$script:PASTA_RT = 'C:\\RADIOTERAPIA_AI\\LOCAL_SUITE'\n"
             u"$script:EstacaoFinal = $null\n$script:Modo = '1'\n"
             u"$script:VERSAO_INSTALADOR = '8.7'\n"
             u"foreach ($cod in @('pt-BR', 'en')) {\n"
             u"  $script:IdiomaAtual = $cod\n"
             u"  ConcluirAtualizacao @{ pasta = 'C:\\PASTA_DO_TESTE\\LOCAL_SUITE\\' } 'codigo' '8.6'\n"
             u"  ('TELA_' + $cod.Replace('-', '_').ToUpper()) + ':' + ($txt4.Text -replace \"[`r`n]+\", ' ~ ')\n"
             u"  ('ABA_' + $cod.Replace('-', '_').ToUpper()) + ':' + $abas.SelectedTab.Nome + '|' + $btAbrirPrograma.Visible + '|' + $script:PastaInstalada\n"
             u"}\n"
             u"$script:AtualizouSoCodigo = $null\n$script:IdiomaAtual = 'pt-BR'\n"
             u"AtualizarConclusao 'C:\\PASTA_DO_TESTE\\LOCAL_SUITE' ''\n"
             u"'TELA_INSTALAR:' + ($txt4.Text -replace \"[`r`n]+\", ' ~ ')\n"
             % {"lang": os.path.join(RAIZ, "packager", "languages.ps1").replace(u"'", u"''"),
                "pack": os.path.join(RAIZ, "packager").replace(u"'", u"''")})
    m, out = _harness_do_preparador(["ConcluirAtualizacao", "AtualizarConclusao",
                                     "ModoDireto", "NomeDoArquivo"], corpo)
    pt = m.get(u"TELA_PT_BR") or u""
    checar(u"so o codigo trocado: a conclusao diz ATUALIZADO, as duas versoes, a pasta "
           u"e os atalhos refeitos", u"APP ATUALIZADO NESTA MÁQUINA" in pt
           and u"8.6" in pt and u"8.7" in pt and u"PASTA_DO_TESTE" in pt
           and u"atalhos" in pt and u"botão verde" in pt, pt[:300] or out[-500:])
    aba = (m.get(u"ABA_PT_BR") or u"").split(u"|")
    checar(u"  a tela vai sozinha para a etapa 4, com o botao verde de abrir o app",
           len(aba) == 3 and aba[0] == u"aba4" and aba[1] == u"True"
           and aba[2].endswith(u"LOCAL_SUITE"), m.get(u"ABA_PT_BR") or out[-300:])
    en = m.get(u"TELA_EN") or u""
    checar(u"  e em ingles sai traduzida, com o caminho intacto",
           u"APP UPDATED ON THIS MACHINE" in en and u"PASTA_DO_TESTE" in en
           and u"ATUALIZADO" not in en, en[:200])
    checar(u"  (isca) sem a atualizacao, a conclusao da instalacao continua a de antes",
           u"APP ATUALIZADO" not in (m.get(u"TELA_INSTALAR") or u"x")
           and u"PRONTO" in (m.get(u"TELA_INSTALAR") or u""),
           (m.get(u"TELA_INSTALAR") or out[-300:])[:200])


def teste_o_instalador_ve_se_o_app_processa():
    secao(u"o instalador: pergunta so se o app processa, e so fecha a janela do app")
    estado = {"status": {}}
    srv = _Servidor({
        "/api/pulso": lambda c: (200, "application/json", u'{"radai": true}'),
        "/api/status": lambda c: (200, "application/json",
                                  json.dumps(estado["status"]))})
    pasta = tempfile.mkdtemp(prefix="radai_inicio_inst_")
    try:
        io.open(os.path.join(pasta, u"radai_watcher.config"), "w",
                encoding="utf-8-sig").write(u"PORT=%d\n" % srv.porta)
        resultados = {}
        for rot, st in ((u"LIVRE", {"ocupado": None, "current": None}),
                        (u"SERIE", {"ocupado": {"quem": "vigia"}}),
                        (u"TURNO", {"overnight": True}),
                        (u"AGENDADO", {"turno_agendado": True})):
            estado["status"] = st
            m, out = _harness_do_preparador(
                ["PortaDoApp", "PerguntarAoApp", "CampoDoApp", "EstadoDoAppAberto"],
                u"$x = EstadoDoAppAberto '%s'\n'R:' + $x.aberto + '|' + $x.processando + '|' + $x.oque\n"
                % pasta.replace(u"'", u"''"))
            resultados[rot] = m.get(u"R") or out[-200:]
        checar(u"app aberto e livre: encerra sem perguntar",
               resultados[u"LIVRE"].startswith(u"True|False|"), resultados[u"LIVRE"])
        checar(u"  serie rodando, turno aberto ou turno na fila: pergunta, dizendo o que",
               resultados[u"SERIE"] == u"True|True|há uma série em processamento"
               and resultados[u"TURNO"] == u"True|True|o turno da noite está aberto"
               and resultados[u"AGENDADO"] == u"True|True|o turno da noite está na fila",
               repr(resultados))
        srv.fechar()
        m, out = _harness_do_preparador(
            ["PortaDoApp", "PerguntarAoApp", "CampoDoApp", "EstadoDoAppAberto"],
            u"$x = EstadoDoAppAberto '%s'\n'R:' + $x.aberto + '|' + $x.processando\n"
            % pasta.replace(u"'", u"''"))
        checar(u"  (isca) sem o app na porta: nada a perguntar nem a encerrar",
               m.get(u"R") == u"False|False", m.get(u"R") or out[-200:])
    finally:
        srv.fechar()
        shutil.rmtree(pasta, ignore_errors=True)
    if os.environ.get("RADAI_JANELA_DE_VERDADE") != "1" or os.name != "nt":
        print(u"    PULADO o fechar da janela de verdade: ligue com "
              u"RADAI_JANELA_DE_VERDADE=1")
        return
    import subprocess
    exe = None
    for c in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"):
        if os.path.isfile(c):
            exe = c
            break
    if not exe:
        print(u"    PULADO: sem Edge nem Chrome")
        return
    base = tempfile.mkdtemp(prefix="radai_inicio_fecha_")
    try:
        ps = []
        for nome in (u"radai_janela", u"perfil_da_pessoa"):
            pag = os.path.join(base, nome + u".html")
            io.open(pag, "w").write(u"<title>%s</title>" % nome)
            ps.append(subprocess.Popen([exe, u"--app=file:///" + pag.replace(u"\\", u"/"),
                                        u"--user-data-dir=" + os.path.join(base, nome),
                                        u"--no-first-run", u"--no-default-browser-check"]))
        time.sleep(5)
        m, out = _harness_do_preparador(
            ["FecharJanelasDoApp"], u"'N:' + (FecharJanelasDoApp)\n")

        def vivos(nome):
            r = subprocess.run(
                [u"powershell", u"-NoProfile", u"-Command",
                 u"@(Get-CimInstance Win32_Process -Filter \"Name='chrome.exe' OR "
                 u"Name='msedge.exe'\" | Where-Object { $_.CommandLine -like '*"
                 + os.path.join(base, nome).replace(u"'", u"''") + u"*' }).Count"],
                capture_output=True, text=True)
            return int((r.stdout or u"0").strip() or 0)
        time.sleep(2)
        checar(u"[janela] o instalador fecha o navegador do perfil do app",
               vivos(u"radai_janela") == 0 and m.get(u"N", u"0") != u"0", m)
        checar(u"  (isca) e nao toca no navegador de outro perfil",
               vivos(u"perfil_da_pessoa") > 0)
    finally:
        subprocess.run([u"powershell", u"-NoProfile", u"-Command",
                        u"Get-CimInstance Win32_Process -Filter \"Name='chrome.exe' OR "
                        u"Name='msedge.exe'\" | Where-Object { $_.CommandLine -like '*"
                        + base.replace(u"'", u"''") + u"*' -and $_.CommandLine -notlike "
                        u"'*--type=*' } | ForEach-Object { taskkill /PID $_.ProcessId /T /F "
                        u"| Out-Null }"], capture_output=True)
        time.sleep(1)
        shutil.rmtree(base, ignore_errors=True)


TESTES = [teste_tela_cheia, teste_a_janela_do_app,
          teste_a_janela_pelo_titulo_e_o_f11_que_nao_desliga,
          teste_a_janela_de_verdade,
          teste_a_pagina_de_carregamento_pensa, teste_o_lancador_tenta_de_novo,
          teste_o_download_confere_a_soma, teste_a_atualizacao_pelo_app,
          teste_o_atualizador_decide_espera_e_reabre,
          teste_o_guia_inicial_no_dado, teste_o_guia_e_o_popup_no_navegador,
          teste_o_instalador_vai_para_a_etapa_4,
          teste_o_instalador_ve_se_o_app_processa]


def main():
    print(u"\n" + u"=" * 70)
    print(u"  INICIO — tela cheia, janela, abertura, atualizacao e guia")
    print(u"=" * 70)
    for t in TESTES:
        try:
            t()
        except Exception as e:
            import traceback
            checar(u"%s (excecao inesperada)" % t.__name__, False,
                   u"%s: %s" % (type(e).__name__, e))
            traceback.print_exc()
    shutil.rmtree(_ACERVO_TESTE, ignore_errors=True)
    print(u"\n" + u"=" * 70)
    if _falhas:
        print(u"FALHOU: %d de %d checagens" % (len(_falhas), _ok + len(_falhas)))
        for f in _falhas:
            print(u"    - %s" % f)
        print(u"=" * 70)
        return 1
    print(u"OK: %d checagens, todas passaram" % _ok)
    print(u"=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
