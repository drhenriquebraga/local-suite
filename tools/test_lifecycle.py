# -*- coding: utf-8 -*-
import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _cleanup
import _componentes
_cleanup.adotar_prefixo('radai_ciclo_')
_cleanup.adotar_prefixo('radai_desinstalar_')
_cleanup.adotar_prefixo('radai_rm_')

os.environ["RADAI_CALIB_DIR"] = tempfile.mkdtemp(prefix="radai_ciclo_acervo_")

# GUARDA: o desinstalador lista (e pode apagar) o `radai_*` do %TEMP% e do
# `<disco>\RADIOTERAPIA_AI\tmp`; a bateria lhe da um temporario e discos proprios.
_CAIXA = tempfile.mkdtemp(prefix="radai_ciclo_caixa_")


def _ambiente_da_caixa(caixa=_CAIXA):
    t = os.path.join(caixa, "temp")
    for sub in ("temp", "ad", "discos"):
        os.makedirs(os.path.join(caixa, sub), exist_ok=True)
    return {"TEMP": t, "TMP": t, "LOCALAPPDATA": os.path.join(caixa, "ad"),
            "RADAI_UNIDADES_LOCAIS": os.path.join(caixa, "discos")}

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESINSTALAR = os.path.join(RAIZ, "installer", "UNINSTALL.ps1")
ATUALIZAR = os.path.join(RAIZ, "packager", "UPDATE.ps1")

_ok = 0
_falhou = 0
_falhas = []


def secao(t):
    print(u"")
    print(u"\u2500\u2500 %s %s" % (t, u"\u2500" * max(0, 62 - len(t))))


def checar(rotulo, cond, detalhe=u""):
    global _ok, _falhou
    if cond:
        _ok += 1
        print(u"  OK     %s" % rotulo)
    else:
        _falhou += 1
        _falhas.append(rotulo)
        print(u"  FALHA  %s  %s" % (rotulo, detalhe.replace("\n", " | ")[:150]))


def porta_livre():
    return _porta_livre()


def _ps(script, args, entrada=u"", timeout=300, extra=None):
    env = dict(os.environ)
    env["RADAI_SEM_JANELA"] = "1"
    env.update(_ambiente_da_caixa())
    env.update(extra or {})
    p = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
         "-File", script] + args,
        input=entrada.encode("cp1252"), stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, timeout=timeout, env=env)
    return p.returncode, p.stdout.decode("cp1252", "replace")


def montar_pacote(base, versao):
    p = os.path.join(base, "pacote")
    for sub in ("app", "tools", "build", "packager"):
        os.makedirs(os.path.join(p, sub), exist_ok=True)
    io.open(os.path.join(p, "entrega.txt"), "w").write(
        "PROJETO=AUTO_CONTORNO\nVERSAO=%s\n" % versao)
    for n in ("radai_watcher.py", "engine.py", "radai_geom.py",
              "radai_modulo_novo.py"):
        io.open(os.path.join(p, "app", n), "w").write(
            "# %s versao %s\n" % (n, versao))
    os.makedirs(os.path.join(p, "app", "data"), exist_ok=True)
    io.open(os.path.join(p, "app", "data", "bibliography.json"),
            "w", encoding="utf-8").write(
        '{"versao": "%s", "itens": []}' % versao)
    os.makedirs(os.path.join(p, "app", "launchers"), exist_ok=True)
    io.open(os.path.join(p, "app", "launchers", "open_browser.cmd"),
            "w").write("REM open_browser versao %s\n" % versao)
    io.open(os.path.join(p, "app", "launchers", "start_watcher.cmd"),
            "w").write("REM start_watcher versao %s\n" % versao)
    io.open(os.path.join(p, "tools", "testar_algo.py"), "w").write("# v%s\n" % versao)
    for f in ("requisitos.py", "requirements-demo.txt",
              "configurar_ambiente.py", "artefatos.py"):
        shutil.copy2(os.path.join(RAIZ, "build", f),
                     os.path.join(p, "build", f))
    shutil.copy2(_componentes.fonte("app/radai_tasks.py"),
                 os.path.join(p, "app", "radai_tasks.py"))
    shutil.copy2(_componentes.fonte("app/radai_models.py"),
                 os.path.join(p, "app", "radai_models.py"))
    shutil.copy2(ATUALIZAR, os.path.join(p, "packager", "UPDATE.ps1"))
    for n in ("NOTICE", "LICENSE"):
        io.open(os.path.join(p, n), "w", encoding="utf-8").write(
            u"%s versao %s\n" % (n, versao))
    return p


def _porta_livre(tentativas=8):
    for _ in range(tentativas):
        s = socket.socket()
        try:
            s.bind(("127.0.0.1", 0))
            p = s.getsockname()[1]
        finally:
            s.close()
        c = socket.socket()
        c.settimeout(0.4)
        try:
            c.connect(("127.0.0.1", p))
            c.close()
        except OSError:
            return p
        finally:
            try:
                c.close()
            except OSError:
                pass
    raise RuntimeError(u"nao achei porta livre em %d tentativas" % tentativas)


def montar_instalacao(base, versao, impressao_de, porta):
    raiz = os.path.join(base, "RADIOTERAPIA_AI")
    inst = os.path.join(raiz, "AUTO_CONTORNO")
    for sub in ("tools", "calibracao", "python"):
        os.makedirs(os.path.join(inst, sub), exist_ok=True)
    for n in ("radai_watcher.py", "engine.py", "radai_geom.py"):
        io.open(os.path.join(inst, n), "w").write("# %s ANTIGO\n" % n)
    io.open(os.path.join(inst, "entrega.txt"), "w").write("VERSAO=%s\n" % versao)
    io.open(os.path.join(inst, "radai_watcher.config"), "w").write(
        "PORT=%d\nROOT=C:\\nao_toque\n" % porta)
    io.open(os.path.join(inst, "calibracao", "receita.json"), "w").write("{}")
    io.open(os.path.join(inst, "radai_vigia.log"), "w").write("historico\n")
    for n in ("NOTICE", "LICENSE"):
        io.open(os.path.join(inst, n), "w", encoding="utf-8").write(
            u"%s ANTIGO\n" % n)
    io.open(os.path.join(inst, "python", "python.exe"), "wb").write(b"MZ\0")
    sys.path.insert(0, os.path.join(RAIZ, "build"))
    import requisitos as R
    d = R.calcular(impressao_de)
    d["versao"] = versao
    io.open(os.path.join(inst, "_requisitos.json"), "w",
            encoding="utf-8").write(json.dumps(d, ensure_ascii=False))
    io.open(os.path.join(raiz, "_instalados.json"), "w",
            encoding="utf-8").write(json.dumps(
                {"AUTO_CONTORNO": {"versao": versao, "pasta": inst}}))
    return inst


def teste_atualizar():
    secao(u"ATUALIZAR: a decisao entre copiar e mandar preparar")
    checar(u"o atualizador existe", os.path.isfile(ATUALIZAR))
    if not os.path.isfile(ATUALIZAR):
        return
    base = tempfile.mkdtemp(prefix="radai_ciclo_at_")
    pl = porta_livre()

    def rodar(pac, inst, entrada=u"S\n"):
        return _ps(os.path.join(pac, "packager", "UPDATE.ps1"),
                   ["-Destino", inst, "-Python", sys.executable], entrada)

    pac = montar_pacote(base, "9.2")
    inst = montar_instalacao(base, "9.1", pac, pl)
    rc, t = rodar(pac, inst)
    checar(u"so o codigo mudou: atualiza", rc == 0, t[-300:])
    checar(u"e diz que da para fazer aqui", "so o codigo mudou" in t)
    checar(u"o codigo novo chegou",
           "versao 9.2" in io.open(os.path.join(inst, "engine.py")).read())
    checar(u"e o modulo NOVO tambem",
           os.path.isfile(os.path.join(inst, "radai_modulo_novo.py")),
           u"copia que so sobrescreve deixa o modulo novo de fora")
    checar(u"o tools acompanha",
           os.path.isfile(os.path.join(inst, "tools", "testar_algo.py")))
    aj = os.path.join(inst, "launchers", "open_browser.cmd")
    checar(u"a subpasta `ferramentas` chegou", os.path.isfile(aj),
           u"o lancador e o open_browser moram la")
    if os.path.isfile(aj):
        checar(u"  e com o conteudo NOVO",
               "versao 9.2" in io.open(aj).read(),
               io.open(aj).read().strip()[:60])
    checar(u"  e o caminho relativo foi preservado",
           not os.path.isfile(os.path.join(inst, "open_browser.cmd")),
           u"achatar a arvore poria o arquivo na raiz, e o lancador chama "
           u"`launchers\\start_watcher.cmd`")
    checar(u"e a contagem inclui os da subpasta",
           "arquivo(s) novo(s)" in t, t[-200:])
    checar(u"a versao subiu no entrega.txt",
           "VERSAO=9.2" in io.open(os.path.join(inst, "entrega.txt")).read())

    dj = os.path.join(inst, "data", "bibliography.json")
    checar(u"o `.json` de dado chegou", os.path.isfile(dj),
           u"`app/data/` guarda dado do programa, e ele envelhecia calado")
    if os.path.isfile(dj):
        checar(u"  e com o conteudo NOVO",
               "9.2" in io.open(dj, encoding="utf-8").read(),
               io.open(dj, encoding="utf-8").read()[:80])
    cfg = os.path.join(inst, "radai_watcher.config")
    checar(u"o config do operador continua la", os.path.isfile(cfg))
    if os.path.isfile(cfg):
        checar(u"  e NAO foi sobrescrito",
               "nao_toque" in io.open(cfg, encoding="utf-8").read(),
               io.open(cfg, encoding="utf-8").read()[:80])
    rec = os.path.join(inst, "calibracao", "receita.json")
    checar(u"e a calibracao do operador continua intacta",
           os.path.isfile(rec),
           u"`.json` entrou na copia; a `calibracao\\` nao pode vir junto")
    checar(u"o config do operador ficou",
           "nao_toque" in io.open(os.path.join(inst, "radai_watcher.config")).read())
    checar(u"a calibracao ficou",
           os.path.isfile(os.path.join(inst, "calibracao", "receita.json")))
    checar(u"o log ficou",
           os.path.isfile(os.path.join(inst, "radai_vigia.log")))

    b2 = os.path.join(base, "b2")
    os.makedirs(b2)
    pac2 = montar_pacote(b2, "9.9")
    art = os.path.join(pac2, "build", "artefatos.py")
    t_art = io.open(art, encoding="utf-8").read()
    novo = t_art.replace('"torch": "2.5.1+cu121"', '"torch": "9.9.9+cu999"', 1)
    checar(u"a isca do torch entrou no fantoma", novo != t_art,
           u"o pino do torch mudou de forma; ajuste esta bateria")
    io.open(art, "w", encoding="utf-8").write(novo)
    inst2 = montar_instalacao(b2, "9.2", pac, pl)
    antes = io.open(os.path.join(inst2, "engine.py")).read()
    rc2, t2 = rodar(pac2, inst2)
    checar(u"biblioteca nova: RECUSA a copia offline", rc2 == 3, t2[-300:])
    checar(u"e diz O QUE mudou", "torch" in t2 and "9.9.9" in t2, t2[:400])
    _prep = io.open(os.path.join(RAIZ, "packager", "prepare.ps1"),
                    encoding="utf-8-sig").read()
    _m = re.search(r"\$btModo2 = NovoBotao '([^']+)'", _prep)
    _nome = _m.group(1) if _m else u"(nao achei o botao)"
    import unicodedata as _ud

    def _sem_acento(x):
        return u"".join(c for c in _ud.normalize("NFKD", x)
                        if not _ud.combining(c))
    checar(u"e manda para a maquina com internet, pelo nome do botao",
           _sem_acento(_nome) in _sem_acento(t2), u"%s -- %s" % (_nome, t2[-200:]))
    checar(u"e nao tocou no codigo",
           io.open(os.path.join(inst2, "engine.py")).read() == antes,
           u"recusou e mexeu assim mesmo")
    checar(u"e nao subiu a versao",
           "VERSAO=9.2" in io.open(os.path.join(inst2, "entrega.txt")).read())

    vazio = os.path.join(base, "vazio")
    os.makedirs(vazio)
    rc3, t3 = rodar(pac, vazio)
    checar(u"sem instalacao: recusa", rc3 == 1, t3[-200:])
    checar(u"e manda para o START_HERE", "START_HERE" in t3)

    rc4, t4 = _ps(os.path.join(pac, "packager", "UPDATE.ps1"),
                  ["-Destino", inst, "-Python",
                   os.path.join(inst, "python", "python.exe")], u"S\n")
    checar(u"decisor que nao roda: diz que NAO CONSEGUIU decidir",
           "Nao consegui decidir" in t4, t4[-300:])
    checar(u"e nao diz 'precisa de internet'",
           "PRECISA DE INTERNET" not in t4,
           u"sem resposta virou diagnostico")
    shutil.rmtree(base, ignore_errors=True)


def teste_desinstalar_diz_o_que_fica_fora():
    secao(u"DESINSTALAR: o que o programa deixou FORA da pasta")
    base = tempfile.mkdtemp(prefix="radai_ciclo_fora_")

    def cenario(nome):
        caixa = os.path.join(base, nome)
        amb = _ambiente_da_caixa(caixa)
        tmp_d = os.path.join(amb["RADAI_UNIDADES_LOCAIS"], "RADIOTERAPIA_AI", "tmp")
        os.makedirs(os.path.join(tmp_d, "radai_lote_ab12"))
        io.open(os.path.join(tmp_d, "radai_lote_ab12", "RS.dcm"), "w").write(u"x")
        os.makedirs(os.path.join(tmp_d, "outro_programa"))
        io.open(os.path.join(amb["TEMP"], "radai_motor_8777.txt"), "w").write(u"x")
        os.makedirs(os.path.join(amb["TEMP"], "radai_janela", "Default"))
        io.open(os.path.join(amb["TEMP"], "nada_nosso.txt"), "w").write(u"x")
        ad = os.path.join(amb["LOCALAPPDATA"], "RADIOTERAPIA_AI")
        os.makedirs(ad)
        io.open(os.path.join(ad, "motor_8777.json"), "w").write(u"{}")
        io.open(os.path.join(ad, "sonda_torch.json"), "w").write(u"{}")
        inst = montar_instalacao(caixa, "9.1", RAIZ, porta_livre())
        acervo = os.path.join(caixa, "dados", "calibracao")
        os.makedirs(os.path.join(caixa, "dados", "cache_tasks", "chave"))
        os.makedirs(acervo)
        io.open(os.path.join(inst, "_dados.txt"), "w").write(u"# acervo\n%s\n" % acervo)
        return amb, inst, tmp_d, ad, caixa

    amb, inst, tmp_d, ad, caixa = cenario("a")
    rc, t = _ps(DESINSTALAR, ["-Alvo", inst, "-SemPerguntar"], extra=amb)
    checar(u"desinstalar sem perguntar: termina", rc == 0, t[-300:])
    for rot, alvo in ((u"o temporario do disco (radai_*)", u"radai_lote_ab12"),
                      (u"o console do motor", u"radai_motor_8777.txt"),
                      (u"o perfil do navegador", u"radai_janela"),
                      (u"o estado do motor", u"motor_8777.json"),
                      (u"o cache por task deslocado", u"cache_tasks")):
        checar(u"  lista %s" % rot, alvo in t, t[-600:])
    checar(u"  e nao lista o que nao e nosso nem o que nao e de paciente",
           u"outro_programa" not in t and u"nada_nosso" not in t
           and u"sonda_torch" not in t)
    checar(u"  sem -ApagarFora, guarda e DIZ que guardou",
           u"KEPT" in t and os.path.isdir(os.path.join(tmp_d, "radai_lote_ab12")))

    amb, inst, tmp_d, ad, caixa = cenario("b")
    rc, t = _ps(DESINSTALAR, ["-Alvo", inst], u"YES\n\nDESINSTALAR\n", extra=amb)
    checar(u"com YES digitado: apaga o que ficou fora", rc == 0
           and not os.path.exists(os.path.join(tmp_d, "radai_lote_ab12"))
           and not os.path.exists(os.path.join(amb["TEMP"], "radai_janela"))
           and not os.path.exists(os.path.join(amb["TEMP"], "radai_motor_8777.txt"))
           and not os.path.exists(os.path.join(ad, "motor_8777.json"))
           and not os.path.exists(os.path.join(caixa, "dados", "cache_tasks")),
           t[-400:])
    checar(u"  (isca) e so isso: o de outro programa, a sonda e o acervo ficam",
           os.path.isdir(os.path.join(tmp_d, "outro_programa"))
           and os.path.isfile(os.path.join(ad, "sonda_torch.json"))
           and os.path.isfile(os.path.join(amb["TEMP"], "nada_nosso.txt"))
           and os.path.isdir(os.path.join(caixa, "dados", "calibracao")))

    amb, inst, tmp_d, ad, caixa = cenario("c")
    rc, t = _ps(DESINSTALAR, ["-Alvo", inst], u"\n\nDESINSTALAR\n", extra=amb)
    checar(u"com ENTER: o padrao e guardar o que ficou fora",
           rc == 0 and os.path.isdir(os.path.join(tmp_d, "radai_lote_ab12")), t[-300:])
    shutil.rmtree(base, ignore_errors=True)


class _PainelFantoma(object):
    def __init__(self, corpo):
        import http.server
        import threading
        dono = self
        self.corpo = corpo

        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                b = dono.corpo.encode("utf-8")
                self.send_response(200 if self.path == "/api/pulso" else 404)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(b)))
                self.end_headers()
                self.wfile.write(b)

            def log_message(self, *a):
                pass
        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.porta = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def fechar(self):
        self.srv.shutdown()
        self.srv.server_close()


def teste_a_porta_ocupada_diz_de_quem_e():
    secao(u"porta ocupada: o nosso painel ou outro programa")
    base = tempfile.mkdtemp(prefix="radai_ciclo_po_")
    pac = montar_pacote(base, "9.2")
    for corpo, nosso in ((u'{"radai": true, "armado": true}', True),
                         (u'{"outro": 1}', False)):
        srv = _PainelFantoma(corpo)
        try:
            b = os.path.join(base, "n%d" % int(nosso))
            os.makedirs(b)
            inst = montar_instalacao(b, "9.1", pac, srv.porta)
            rc, t = _ps(os.path.join(pac, "packager", "UPDATE.ps1"),
                        ["-Destino", inst, "-Python", sys.executable], u"S\n")
            rcd, td = _ps(DESINSTALAR, ["-Alvo", inst, "-SemPerguntar"])
        finally:
            srv.fechar()
        if nosso:
            checar(u"Atualizar com o NOSSO painel na porta: manda usar o FECHAR APP",
                   rc == 1 and u"FECHAR APP" in t and u"troque o PORT" not in t,
                   t[-300:])
            checar(u"  e nao manda fechar uma «janela preta» que nao existe",
                   u"janela preta" not in t)
            checar(u"Desinstalar com o NOSSO painel: idem",
                   rcd == 1 and u"FECHAR APP" in td and os.path.isdir(inst),
                   td[-300:])
        else:
            checar(u"(isca) outro programa na porta: ai sim, troque o PORT",
                   rc == 1 and u"troque o PORT" in t and u"FECHAR APP" not in t,
                   t[-300:])
            checar(u"  (isca) e o Desinstalar nao manda ao FECHAR APP",
                   rcd == 1 and u"FECHAR APP" not in td and os.path.isdir(inst),
                   td[-300:])
    shutil.rmtree(base, ignore_errors=True)


def teste_atualizar_tira_o_calibrador_apagado():
    secao(u"ATUALIZAR tira o calibrador e o compilador apagados (v8.3)")
    if not os.path.isfile(ATUALIZAR):
        checar(u"o atualizador existe", False)
        return
    texto = io.open(ATUALIZAR, encoding="utf-8-sig").read()
    NOMES = (u"radai_calibrator.py", u"radai_compiler.py",
             u"radai_crosscheck.py", u"radai_studio.py",
             u"tools\\test_calibrator.py")
    m = re.search(r"\$ORFAOS\s*=\s*@\((.*?)\)", texto, re.S)
    lista = re.findall(r'"([^"]+)"', m.group(1)) if m else []
    for n in NOMES:
        checar(u"`%s` esta na lista $ORFAOS" % n, n in lista, lista)
    base = tempfile.mkdtemp(prefix="radai_ciclo_cal_")
    try:
        pl = porta_livre()

        def _cenario(sub, script_texto):
            b = os.path.join(base, sub)
            os.makedirs(b)
            pac = montar_pacote(b, "9.3")
            if script_texto is not None:
                io.open(os.path.join(pac, "packager", "UPDATE.ps1"), "w",
                        encoding="utf-8-sig").write(script_texto)
            inst = montar_instalacao(b, "9.2", pac, pl)
            for n in NOMES + (u"radai_do_operador.py",):
                alvo = os.path.join(inst, *n.split(u"\\"))
                os.makedirs(os.path.dirname(alvo), exist_ok=True)
                io.open(alvo, "w").write(u"# %s\n" % n)
            rc, t = _ps(os.path.join(pac, "packager", "UPDATE.ps1"),
                        ["-Destino", inst, "-Python", sys.executable], u"S\n")
            return rc, t, inst

        rc, t, inst = _cenario("real", None)
        checar(u"a atualizacao rodou", rc == 0, t[-300:])
        for n in NOMES:
            checar(u"  e `%s` saiu" % n,
                   not os.path.exists(os.path.join(inst, *n.split(u"\\"))),
                   u"o cartao da tela apagada reacenderia pelo arquivo")
        checar(u"  e o `.py` do OPERADOR na mesma pasta ficou",
               os.path.isfile(os.path.join(inst, "radai_do_operador.py")),
               u"a lista tira o que e' NOSSO; remocao generica desfaz a regra")

        isca = texto.replace(u'    "radai_calibrator.py",\n', u"", 1)
        checar(u"(isca montada: a linha saiu da lista)", isca != texto)
        rc2, t2, inst2 = _cenario("isca", isca)
        checar(u"(isca) sem a linha, o radai_calibrator.py FICA -- a checagem "
               u"sabe reprovar",
               rc2 == 0 and os.path.isfile(
                   os.path.join(inst2, "radai_calibrator.py")),
               u"rc=%s %s" % (rc2, t2[-200:]))
    finally:
        shutil.rmtree(base, ignore_errors=True)


def teste_atualizar_leva_o_notice():
    secao(u"ATUALIZAR: o NOTICE e o LICENSE acompanham o codigo")
    if not os.path.isfile(ATUALIZAR):
        checar(u"o atualizador existe", False)
        return
    base = tempfile.mkdtemp(prefix="radai_ciclo_notice_")
    try:
        pl = porta_livre()
        pac = montar_pacote(base, "9.2")
        inst = montar_instalacao(base, "9.1", pac, pl)
        rc, t = _ps(os.path.join(pac, "packager", "UPDATE.ps1"),
                    ["-Destino", inst, "-Python", sys.executable], u"S\n")
        checar(u"a atualizacao correu", rc == 0, t[-300:])

        def ler(n, onde=inst):
            p = os.path.join(onde, n)
            return io.open(p, encoding="utf-8").read() if os.path.isfile(p) else u""
        checar(u"o NOTICE instalado e' o do pacote",
               u"NOTICE versao 9.2" in ler("NOTICE"), ler("NOTICE")[:60])
        checar(u"e o LICENSE tambem",
               u"LICENSE versao 9.2" in ler("LICENSE"), ler("LICENSE")[:60])
        checar(u"e o log diz, antes de perguntar, que eles acompanham o codigo",
               u"acompanham o codigo:" in t and u"NOTICE, LICENSE" in t,
               t[-400:])

        b2 = os.path.join(base, "isca")
        os.makedirs(b2)
        pac2 = montar_pacote(b2, "9.2")
        up = os.path.join(pac2, "packager", "UPDATE.ps1")
        txt = io.open(up, encoding="utf-8-sig").read()
        isca = re.sub(r"foreach \(\$nm in \$DOCUMENTOS\) \{\n.*?\n\}\n", u"",
                      txt, count=1, flags=re.S)
        checar(u"  (a isca cabe no texto do atualizador)", isca != txt)
        io.open(up, "w", encoding="utf-8-sig", newline="\r\n").write(isca)
        inst2 = montar_instalacao(b2, "9.1", pac2, pl)
        rc2, t2 = _ps(up, ["-Destino", inst2, "-Python", sys.executable], u"S\n")
        checar(u"  (isca: sem a copia, o NOTICE fica o da primeira instalacao "
               u"-- e a checagem acima o reprova)",
               rc2 == 0 and u"NOTICE ANTIGO" in ler("NOTICE", inst2),
               u"rc=%s | %s | %s" % (rc2, ler("NOTICE", inst2)[:40], t2[-160:]))
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _pacote_do_zip_real(base, versao):
    sys.path.insert(0, os.path.join(RAIZ, "build"))
    import empacotar_instalador as E
    p = os.path.join(base, "pacote")
    for nome, origem in E.coletar():
        alvo = os.path.join(p, nome.replace("/", os.sep))
        os.makedirs(os.path.dirname(alvo), exist_ok=True)
        shutil.copy2(origem, alvo)
    io.open(os.path.join(p, "entrega.txt"), "w").write(
        "PROJETO=AUTO_CONTORNO\nVERSAO=%s\n" % versao)
    shutil.copy2(ATUALIZAR, os.path.join(p, "packager", "UPDATE.ps1"))
    return p


_SONDA_DO_TEXTO = u"""
import json, os, sys
sys.path.insert(0, sys.argv[1])
import radai_consent, radai_credits
print(json.dumps({
    "impressao": radai_consent.impressao_dos_documentos(),
    "notice": str(radai_credits.caminho_notice() or ""),
}))
"""


def _sondar_texto(pasta_do_programa):
    d = tempfile.mkdtemp(prefix="radai_ciclo_sonda_")
    try:
        sc = os.path.join(d, "sonda.py")
        io.open(sc, "w", encoding="utf-8").write(_SONDA_DO_TEXTO)
        p = subprocess.run([sys.executable, sc, pasta_do_programa],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=300, env=dict(os.environ),
                           cwd=d)
        txt = p.stdout.decode("utf-8", "replace")
        linha = [l for l in txt.splitlines() if l.startswith("{")]
        if p.returncode != 0 or not linha:
            return {"erro": txt[-300:]}
        return json.loads(linha[-1])
    finally:
        shutil.rmtree(d, ignore_errors=True)


def teste_atualizar_renova_o_texto_aceito():
    secao(u"ATUALIZAR: a estacao passa a mostrar o texto do pacote")
    if not os.path.isfile(ATUALIZAR):
        checar(u"o atualizador existe", False)
        return
    base = tempfile.mkdtemp(prefix="radai_ciclo_texto_")
    try:
        pl = porta_livre()
        try:
            pac = _pacote_do_zip_real(base, "9.2")
        except (Exception, SystemExit) as e:
            checar(u"o pacote com o conteudo do .zip real foi montado", False,
                   u"%s: %s" % (type(e).__name__, e))
            return
        esperado = _sondar_texto(os.path.join(pac, "app"))
        checar(u"o programa do pacote responde a impressao do texto aceito",
               len(esperado.get("impressao") or u"") == 64,
               esperado.get("erro") or esperado)
        if not esperado.get("impressao"):
            return

        def estacao(onde):
            os.makedirs(onde, exist_ok=True)
            inst = montar_instalacao(onde, "9.1", pac, pl)
            io.open(os.path.join(inst, "NOTICE"), "w", encoding="utf-8").write(
                u"NOTICE da primeira instalacao: outra lista de terceiros\n")
            return inst

        inst = estacao(os.path.join(base, "e1"))
        rc, t = _ps(os.path.join(pac, "packager", "UPDATE.ps1"),
                    ["-Destino", inst, "-Python", sys.executable], u"S\n",
                    timeout=900)
        checar(u"a atualizacao com o conteudo do .zip real correu", rc == 0,
               t[-300:])
        obtido = _sondar_texto(inst)
        checar(u"a estacao atualizada le o NOTICE da propria pasta",
               os.path.normcase(obtido.get("notice") or u"")
               == os.path.normcase(os.path.join(inst, "NOTICE")),
               obtido.get("erro") or obtido.get("notice"))
        checar(u"a impressao do texto aceito na estacao e' a do pacote",
               obtido.get("impressao") == esperado["impressao"],
               u"estacao %s | pacote %s"
               % ((obtido.get("impressao") or obtido.get("erro") or u"")[:16],
                  esperado["impressao"][:16]))

        up = os.path.join(pac, "packager", "UPDATE.ps1")
        txt = io.open(up, encoding="utf-8-sig").read()
        isca = re.sub(r'(?m)^\$DOCUMENTOS = @\(.*\)$', u"$DOCUMENTOS = @()",
                      txt, count=1)
        checar(u"  (a isca cabe no texto do atualizador)", isca != txt)
        up2 = os.path.join(pac, "packager", "UPDATE_isca.ps1")
        io.open(up2, "w", encoding="utf-8-sig", newline="\r\n").write(isca)
        inst2 = estacao(os.path.join(base, "e2"))
        rc2, t2 = _ps(up2, ["-Destino", inst2, "-Python", sys.executable],
                      u"S\n", timeout=900)
        isc = _sondar_texto(inst2)
        checar(u"  (isca: sem os documentos, a estacao fica com OUTRA impressao "
               u"-- a checagem acima reprova)",
               rc2 == 0 and isc.get("impressao")
               and isc.get("impressao") != esperado["impressao"],
               u"rc=%s | %s" % (rc2, isc))
    finally:
        shutil.rmtree(base, ignore_errors=True)


def teste_desinstalar():
    secao(u"DESINSTALAR: as tres recusas, e o que ele guarda")
    checar(u"o desinstalador existe", os.path.isfile(DESINSTALAR))
    if not os.path.isfile(DESINSTALAR):
        return
    base = tempfile.mkdtemp(prefix="radai_ciclo_de_")

    def rodar(alvo, entrada=u"", sem=True):
        args = ["-Alvo", alvo]
        if sem:
            args.append("-SemPerguntar")
        return _ps(DESINSTALAR, args, entrada)

    qualquer = os.path.join(base, "documentos")
    os.makedirs(qualquer)
    io.open(os.path.join(qualquer, "importante.txt"), "w").write("nao apague\n")
    rc, t = rodar(qualquer)
    checar(u"recusa pasta sem as marcas", rc == 1 and "nao parece" in t, t[-200:])
    checar(u"e nao tocou no que estava la",
           os.path.isfile(os.path.join(qualquer, "importante.txt")),
           u"apagou uma pasta que nao era nossa")

    rc, t = rodar("C:\\")
    checar(u"recusa a raiz de um disco", rc == 1, t[-160:])

    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p_ocupada = s.getsockname()[1]
    s.listen(1)
    try:
        ocup = montar_instalacao(base, "9.1", RAIZ, p_ocupada)
        rc, t = rodar(ocup)
        checar(u"recusa com a porta ocupada", rc == 1 and "atendendo na porta" in t,
               t[-200:])
        checar(u"e a pasta continua la", os.path.isdir(ocup))
    finally:
        s.close()

    b2 = os.path.join(base, "b2")
    os.makedirs(b2)
    inst = montar_instalacao(b2, "9.1", RAIZ, porta_livre())
    rc, t = rodar(inst, entrada=u"\nsim\n", sem=False)
    checar(u"cancela sem a palavra DESINSTALAR", rc == 2, t[-200:])
    checar(u"e a pasta continua la", os.path.isdir(inst))

    rc, t = rodar(inst, entrada=u"\nDESINSTALAR\n", sem=False)
    checar(u"aceita a palavra digitada", rc == 0, t[-300:])
    raiz_pai = os.path.dirname(inst)
    guardadas = [d for d in os.listdir(raiz_pai) if "_GUARDADO_" in d]
    checar(u"guardou o dado do operador", len(guardadas) == 1, u"%s" % guardadas)
    if guardadas:
        g = os.path.join(raiz_pai, guardadas[0])
        for n in ("radai_watcher.config", "calibracao", "radai_vigia.log"):
            checar(u"  guardou %s" % n, os.path.exists(os.path.join(g, n)))
    import glob as _glob
    lotes = sorted(_glob.glob(os.path.join(_ambiente_da_caixa()["TEMP"],
                                           "radai_rm_*.cmd")),
                   key=os.path.getmtime)
    checar(u"o removedor destacado foi escrito", bool(lotes),
           u"sem ele nao ha o que apagar a pasta depois que o script sai")
    if lotes:
        rm = io.open(lotes[-1], encoding="ascii", errors="replace").read()
        checar(u"  ele ESPERA o processo sair",
               "tasklist" in rm and "findstr" in rm,
               u"apagar a pasta com o processo dentro deixa a metade la")
        checar(u"  apaga a pasta certa",
               ("rmdir /s /q \"%s\"" % inst) in rm or inst in rm, inst)
        checar(u"  trata o que sobrou (antivirus, arquivo aberto)",
               "Something is left" in rm)
        checar(u"  e se apaga no fim",
               "del /q" in rm and "%~f0" in rm,
               u"senao fica um `.cmd` no %TEMP% por desinstalacao")
        checar(u"  e nao usa o `pause` do sistema",
               "pause >nul" in rm and "\npause\n" not in rm,
               u"o `pause` cru imprime a mensagem do Windows, noutro idioma "
               u"que o resto da tela")
        checar(u"a pasta segue ate alguem rodar o removedor",
               os.path.isdir(inst),
               u"em modo de teste o `.cmd` e escrito e nao executado")
    shutil.rmtree(base, ignore_errors=True)


def teste_desinstalar_pela_interface():
    secao(u"desinstalar pela interface, sem console")
    prep = os.path.join(RAIZ, "packager", "prepare.ps1")
    des = os.path.join(RAIZ, "installer", "UNINSTALL.ps1")
    checar(u"os dois arquivos existem",
           os.path.isfile(prep) and os.path.isfile(des))
    if not (os.path.isfile(prep) and os.path.isfile(des)):
        return
    fp = io.open(prep, encoding="utf-8-sig").read()
    fd = io.open(des, encoding="utf-8-sig").read()

    checar(u"ha uma janela de desinstalar", "function JanelaDesinstalar" in fp)
    i = fp.find("$btModo5.Add_Click({")
    fim = fp.find("\n})", i)
    corpo = fp[i:fim] if (i >= 0 and fim > i) else ""
    checar(u"o botao chama a janela", "JanelaDesinstalar" in corpo)
    checar(u"e nao abre console nenhum",
           "-WindowStyle Normal" not in corpo,
           u"o console e a saida da janela, e sair da janela e sair da tarefa")

    j = fp.find("function JanelaDesinstalar")
    fim2 = fp.find("$btModo5.Add_Click({", j)
    jan = fp[j:fim2] if (j >= 0 and fim2 > j) else ""
    checar(u"a janela roda escondida", "CreateNoWindow = $true" in jan)
    checar(u"e mostra a saida do desinstalador", "StandardOutput" in jan)

    checar(u"a confirmacao digitada continua exigida", "'DESINSTALAR'" in jan)
    checar(u"  e as duas palavras valem (papel antigo diz UNINSTALL)",
           "'UNINSTALL'" in jan)
    checar(u"  e o botao nasce desabilitado", "$bt.Enabled = $false" in jan)

    checar(u"o desinstalador aceita `-Guardar`", "[switch]$Guardar" in fd)
    checar(u"a janela oferece guardar, e o padrao GUARDA",
           "$cb.Checked = $true" in jan)
    checar(u"e passa a escolha adiante", "'-Guardar'" in jan)
    checar(u"o log diz a escolha, nos dois sentidos",
           "guardar: SIM" in fd and "guardar: NAO" in fd)


def teste_desinstalar_do_duplo_clique():
    secao(u"DESINSTALAR: o duplo clique, de dentro de `ferramentas\\`")
    if not os.path.isfile(DESINSTALAR):
        checar(u"o desinstalador existe", False)
        return
    base = tempfile.mkdtemp(prefix="radai_ciclo_dc_")
    try:
        prog = os.path.join(base, "LOCAL_SUITE", "AUTO_CONTORNO")
        ferr = os.path.join(prog, "maintenance")
        os.makedirs(ferr)
        io.open(os.path.join(prog, "radai_watcher.py"), "w").write("# fantoma\n")
        io.open(os.path.join(prog, "entrega.txt"), "w").write(
            "PROJETO=AUTO_CONTORNO\nVERSAO=9.9\n")
        io.open(os.path.join(prog, "radai_watcher.config"), "w").write(
            "PORT=%d\nROOT=\n" % _porta_livre())
        alvo = os.path.join(ferr, "UNINSTALL.ps1")
        shutil.copy2(DESINSTALAR, alvo)

        rc, t = _ps(alvo, [], entrada=u"nao\n")
        checar(u"resolve a raiz do programa a partir de `ferramentas\\`",
               prog in t, t[:400])
        checar(u"e NÃO recusa por falta das marcas",
               "nao parece uma instalacao" not in t, t[-300:])
        checar(u"chega na confirmação digitada", rc == 2,
               u"rc=%s — 2 é «cancelou», que é o que respondemos" % rc)
        checar(u"e a resposta ausente CANCELA, em vez de estourar",
               "InvokeMethodOnNull" not in t and "valor nulo" not in t,
               u"`Read-Host` sem entrada devolve nulo — trate a ausência, "
               u"não a exceção")
        checar(u"e não apagou nada",
               os.path.isfile(os.path.join(prog, "radai_watcher.py")))

        solto = os.path.join(base, "Downloads")
        os.makedirs(solto)
        s2 = os.path.join(solto, "UNINSTALL.ps1")
        shutil.copy2(DESINSTALAR, s2)
        rc, t = _ps(s2, [], entrada=u"nao\n")
        checar(u"cópia solta continua sendo recusada", rc == 1,
               u"rc=%s" % rc)
        checar(u"e a recusa NÃO manda fazer o que já foi feito",
               "de DENTRO da pasta instalada" not in t,
               u"a frase antiga mandava repetir o que a pessoa acabou de fazer")
        checar(u"ela oferece o `-Alvo`", "-Alvo" in t, t[-300:])

        pn = io.open(_componentes.fonte("app/radai_panel.py"),
                     encoding="utf-8").read()
        i = pn.find(u'def _api_desinstalar')
        if i < 0:
            i = pn.find(u'/api/desinstalar')
        rota = pn[i:i + 2600] if i >= 0 else u""
        checar(u"a rota de Configurações existe", bool(rota))
        checar(u"  ela procura em `maintenance/` primeiro",
               u'"maintenance", "ferramentas", ""' in rota,
               u"e a velha continua na lista: a estacao que so ATUALIZOU "
               u"nao recebe `maintenance/`, porque o UPDATE copia so "
               u"`app/**` e `tools/**`")
        checar(u"  e dispara SEM `-Alvo`", u"-Alvo" not in rota,
               u"se passar a mandar `-Alvo`, a subida acima deixa de ser o "
               u"caminho do botão e esta bateria mede outra coisa")
    finally:
        shutil.rmtree(base, ignore_errors=True)


def teste_acha_a_instalacao_com_nome_de_pasta_livre():
    secao(u"achar a instalacao com nome de pasta livre")
    base = tempfile.mkdtemp(prefix="radai_ciclo_ac_")
    raiz = os.path.join(base, "RADIOTERAPIA_AI")
    inst = os.path.join(raiz, "LOCAL_SUITE")
    os.makedirs(inst, exist_ok=True)
    io.open(os.path.join(inst, "radai_watcher.py"), "w").write("# fantoma\n")
    io.open(os.path.join(inst, "entrega.txt"), "w").write(
        "PROJETO=AUTO_CONTORNO\nVERSAO=2.2\n")
    io.open(os.path.join(raiz, "_instalados.json"), "w").write(
        json.dumps({"AUTO_CONTORNO": {"versao": "2.2", "data": "2026-09-01",
                                      "caminho": inst}}))

    prep = os.path.join(RAIZ, "packager", "prepare.ps1")
    checar(u"o preparador existe", os.path.isfile(prep))
    if os.path.isfile(prep):
        rc, saida = _ps_expr(prep, "function MarcaDeInstalacao",
                             "$script:Instalado = AcharInstalacao",
                             "$r = AcharInstalacao; "
                             "if ($r) { 'ACHOU|' + $r.pasta + '|' + $r.como } "
                             "else { 'NAO' }", raiz)
        checar(u"o preparador acha a pasta com nome livre",
               "ACHOU|" in saida and inst.lower() in saida.lower(),
               saida.strip()[-160:])
        checar(u"  e acha PELO REGISTRO (o caminho gravado)",
               "|registro" in saida, saida.strip()[-80:])

    os.remove(os.path.join(raiz, "_instalados.json"))
    if os.path.isfile(prep):
        rc, saida = _ps_expr(prep, "function MarcaDeInstalacao",
                             "$script:Instalado = AcharInstalacao",
                             "$r = AcharInstalacao; "
                             "if ($r) { 'ACHOU|' + $r.pasta + '|' + $r.como } "
                             "else { 'NAO' }", raiz)
        checar(u"sem registro, acha pela marca",
               "ACHOU|" in saida and "|marca" in saida, saida.strip()[-160:])

    os.remove(os.path.join(inst, "entrega.txt"))
    if os.path.isfile(prep):
        rc, saida = _ps_expr(prep, "function MarcaDeInstalacao",
                             "$script:Instalado = AcharInstalacao",
                             "$r = AcharInstalacao; "
                             "if ($r) { 'ACHOU|' + $r.pasta } else { 'NAO' }",
                             raiz)
        checar(u"pasta sem `entrega.txt` NAO conta como instalacao",
               "NAO" in saida, saida.strip()[-120:])

    base3 = tempfile.mkdtemp(prefix="radai_ciclo_ac3_")
    topo3 = os.path.join(base3, "RADIOTERAPIA_AI")
    raiz3 = os.path.join(topo3, "LOCAL_SUITE")
    inst3 = os.path.join(raiz3, "AUTO_CONTORNO")
    os.makedirs(inst3, exist_ok=True)
    io.open(os.path.join(inst3, "radai_watcher.py"), "w").write("# fantoma\n")
    io.open(os.path.join(inst3, "entrega.txt"), "w").write("VERSAO=2.1\n")
    io.open(os.path.join(raiz3, "_instalados.json"), "w").write(
        json.dumps({"AUTO_CONTORNO": {"versao": "2.1", "caminho": inst3}}))
    if os.path.isfile(prep):
        rc, saida = _ps_expr(prep, "function MarcaDeInstalacao",
                             "$script:Instalado = AcharInstalacao",
                             "$r = AcharInstalacao; "
                             "if ($r) { 'ACHOU|' + $r.pasta + '|' + $r.como } "
                             "else { 'NAO' }", topo3)
        checar(u"acha o layout de TRES niveis (raiz escolhida + projeto)",
               "ACHOU|" in saida and inst3.lower() in saida.lower(),
               saida.strip()[-160:])
        os.remove(os.path.join(raiz3, "_instalados.json"))
        rc, saida = _ps_expr(prep, "function MarcaDeInstalacao",
                             "$script:Instalado = AcharInstalacao",
                             "$r = AcharInstalacao; "
                             "if ($r) { 'ACHOU|' + $r.pasta } else { 'NAO' }",
                             topo3)
        checar(u"  e acha sem registro, tres niveis abaixo",
               "ACHOU|" in saida and inst3.lower() in saida.lower(),
               saida.strip()[-160:])
    shutil.rmtree(base3, ignore_errors=True)

    if os.path.isfile(prep):
        fp3 = io.open(prep, encoding="utf-8-sig").read()
        checar(u"o seletor desce niveis em vez de exigir o certo",
               "$atual.n -ge 3" in fp3,
               u"aceitar so um nivel devolve a pessoa ao dialogo")
        checar(u"e o dialogo DIZ que qualquer nivel serve",
               "qualquer pasta acima dela" in fp3)

    if os.path.isfile(prep):
        fp4 = io.open(prep, encoding="utf-8-sig").read()
        checar(u"a atualizacao esconde os controles de preparar",
               "$script:PrepEscondido" in fp4)
        checar(u"  e os devolve no fim",
               fp4.count("$script:PrepEscondido") >= 3,
               u"aba que fica vazia depois parece preparador quebrado")
        checar(u"  e diz o que a atualizacao faz, antes de fazer",
               "A cascata decide sozinha, nesta ordem" in fp4)

    io.open(os.path.join(inst, "entrega.txt"), "w").write(
        "PROJETO=AUTO_CONTORNO\nVERSAO=2.2\n")
    io.open(os.path.join(raiz, "_instalados.json"), "w").write(
        json.dumps({"AUTO_CONTORNO": {"versao": "2.2", "caminho": inst}}))
    fonte = io.open(ATUALIZAR, encoding="utf-8-sig").read()
    checar(u"o atualizador le o `caminho` do registro",
           "$p.Value.caminho" in fonte,
           u"montar `raiz\\<chave>` e o defeito de campo")
    checar(u"e tambem varre por marca",
           'entrega.txt"))' in fonte or "entrega.txt" in fonte)

    if os.path.isfile(prep):
        fp = io.open(prep, encoding="utf-8-sig").read()
        checar(u"o botao Instalar / Atualizar nasce ativo",
               "$btModo1.Enabled = $true" in fp,
               u"ele nascia `= $temInst`")
        checar(u"o botao Desinstalar segue a deteccao",
               "$btModo5.Enabled = $temInst" in fp,
               u"botao ativo promete que o programa sabe o que vai apagar")
        checar(u"e ha um seletor de pasta para quando nao achar",
               "FolderBrowserDialog" in fp and "GarantirInstalacao" in fp)
        _mm = fp[fp.find("function MarcarModo"):]
        _mm = _mm[:_mm.find("\n}")]
        checar(u"os handlers que agem numa instalacao ja escolhida passam por ele "
               u"(a retomada pelo instalador novo, desinstalar e o modo 7)",
               fp.count("GarantirInstalacao (T ") == 3
               and "GarantirInstalacao (T " in _mm,
               u"um botao que nao pergunta volta a ficar sem saida")
        _io = fp[fp.find("function InstalarOuAtualizar"):]
        _io = _io[:_io.find("\n}")]
        checar(u"e o Instalar / Atualizar nao pergunta: sem instalacao achada, instala tudo",
               "ConferirInstalacao" in _io and "GarantirInstalacao" not in _io
               and "MarcarModo '1'" in _io,
               u"perguntar a pasta devolve o operador ao Atualizar que pedia a pasta")
    shutil.rmtree(base, ignore_errors=True)


def _ps_expr(script, de, ate, expr, raizes):
    ps = (
        "$ErrorActionPreference='Stop';"
        "$env:RADAI_RAIZES_BUSCA=%s;"
        "$f=Get-Content -LiteralPath %s -Raw;"
        "$i=$f.IndexOf(%s);$j=$f.IndexOf(%s);"
        "Invoke-Expression $f.Substring($i,$j-$i);"
        "%s"
    ) % (_pslit(raizes), _pslit(script), _pslit(de), _pslit(ate), expr)
    p = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy",
                        "Bypass", "-Command", ps],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       timeout=180)
    return p.returncode, p.stdout.decode("cp1252", "replace")


def _pslit(s):
    return "'" + str(s).replace("'", "''") + "'"


def _lnk(acao, caminho, alvo=u"", icone=u""):
    tmp = tempfile.mkdtemp(prefix="radai_ciclo_lnk_")
    try:
        s = os.path.join(tmp, "l.ps1")
        io.open(s, "w", encoding="utf-8-sig", newline="\r\n").write(
            u"param([string]$A, [string]$C, [string]$T, [string]$I)\n"
            u"$ws = New-Object -ComObject WScript.Shell\n"
            u"$s = $ws.CreateShortcut($C)\n"
            u"if ($A -eq 'criar') { $s.TargetPath = $T; $s.IconLocation = $I; $s.Save() }\n"
            u"'ICONE=' + $s.IconLocation\n"
            u"'ALVO=' + $s.TargetPath\n")
        p = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy",
                            "Bypass", "-File", s, "-A", acao, "-C", caminho,
                            "-T", alvo, "-I", icone],
                           capture_output=True, timeout=120)
        d = {}
        for l in p.stdout.decode("cp1252", "replace").splitlines():
            if u"=" in l:
                k, v = l.split(u"=", 1)
                d[k.strip()] = v.strip()
        return d
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def teste_atualizar_refaz_o_icone_do_atalho():
    secao(u"ATUALIZAR: o icone do atalho acompanha o favicon.ico novo")
    fav = _componentes.fonte("app/favicon.ico")
    checar(u"o favicon.ico existe no repositorio", os.path.isfile(fav))
    if not os.path.isfile(fav):
        return
    base = tempfile.mkdtemp(prefix="radai_ciclo_ico_")
    pac = montar_pacote(base, "9.2")
    shutil.copy2(fav, os.path.join(pac, "app", "favicon.ico"))
    inst = montar_instalacao(base, "9.1", pac, porta_livre())
    raiz = os.path.dirname(inst)
    desk = os.path.join(raiz, "_atalhos_desktop")
    os.makedirs(desk)
    nosso = os.path.join(desk, u"Radioterapia.ai Local Suite.lnk")
    outro = os.path.join(desk, u"Outro programa.lnk")
    velho = os.path.join(inst, "radioterapia_ai.ico") + u",0"
    alheio = os.environ.get("SystemRoot", r"C:\Windows") + r"\notepad.exe"
    _lnk(u"criar", nosso, os.path.join(inst, "RADIOTERAPIA_AI_LOCAL_SUITE.cmd"),
         velho)
    _lnk(u"criar", outro, alheio, alheio + u",0")
    rc, t = _ps(os.path.join(pac, "packager", "UPDATE.ps1"),
                ["-Destino", inst, "-Python", sys.executable], u"S\n",
                extra={"RADAI_ATALHOS_NA_RAIZ": "1"})
    checar(u"a atualizacao termina", rc == 0, t[-300:])
    checar(u"o favicon.ico chegou a instalacao",
           os.path.isfile(os.path.join(inst, "favicon.ico")))
    lido = _lnk(u"ler", nosso)
    esperado = os.path.join(inst, "favicon.ico") + u",0"
    checar(u"o atalho DESTA instalacao passou a usar o favicon.ico",
           lido.get(u"ICONE", u"").lower() == esperado.lower(),
           u"%s -- esperava %s" % (lido.get(u"ICONE"), esperado))
    checar(u"  e o alvo dele nao mudou",
           lido.get(u"ALVO", u"").lower().endswith(
               u"radioterapia_ai_local_suite.cmd"), lido.get(u"ALVO"))
    lido2 = _lnk(u"ler", outro)
    checar(u"o atalho de OUTRO programa nao foi tocado",
           lido2.get(u"ICONE", u"").lower() == (alheio + u",0").lower(),
           lido2.get(u"ICONE"))
    checar(u"e o que foi refeito e' o da pasta de teste, e nao o Desktop real",
           (u"icone do atalho refeito: " + nosso) in t
           and t.count(u"icone do atalho refeito") == 1,
           u" | ".join([l for l in t.splitlines() if u"icone" in l][:3]))
    shutil.rmtree(base, ignore_errors=True)


def teste_atualizar_tira_o_lancador_do_motor_http():
    secao(u"ATUALIZAR tira o lancador do motor HTTP (os tres nomes dele)")
    if not os.path.isfile(ATUALIZAR):
        checar(u"o atualizador existe", False)
        return
    texto = io.open(ATUALIZAR, encoding="utf-8-sig").read()
    NOMES = (u"launchers\\start_engine.cmd", u"ferramentas\\iniciar_motor.cmd",
             u"iniciar_motor.cmd")
    m = re.search(r"\$ORFAOS\s*=\s*@\((.*?)\)", texto, re.S)
    lista = re.findall(r'"([^"]+)"', m.group(1)) if m else []
    for n in NOMES:
        checar(u"`%s` esta na lista $ORFAOS" % n, n in lista, lista)
    base = tempfile.mkdtemp(prefix="radai_ciclo_orf_")
    try:
        pl = porta_livre()

        def _cenario(sub, script_texto):
            b = os.path.join(base, sub)
            os.makedirs(b)
            pac = montar_pacote(b, "9.2")
            if script_texto is not None:
                io.open(os.path.join(pac, "packager", "UPDATE.ps1"), "w",
                        encoding="utf-8-sig").write(script_texto)
            inst = montar_instalacao(b, "9.1", pac, pl)
            for n in NOMES + (u"launchers\\meu_atalho.cmd",):
                alvo = os.path.join(inst, *n.split(u"\\"))
                os.makedirs(os.path.dirname(alvo), exist_ok=True)
                io.open(alvo, "w").write(u"REM %s\n" % n)
            rc, t = _ps(os.path.join(pac, "packager", "UPDATE.ps1"),
                        ["-Destino", inst, "-Python", sys.executable], u"S\n")
            return rc, t, inst

        rc, t, inst = _cenario("real", None)
        checar(u"a atualizacao rodou", rc == 0, t[-300:])
        for n in NOMES:
            checar(u"  e `%s` saiu" % n,
                   not os.path.exists(os.path.join(inst, *n.split(u"\\"))),
                   u"ficaria clicavel, subindo um servidor que nao existe mais")
        checar(u"  e o `.cmd` do OPERADOR na mesma pasta ficou",
               os.path.isfile(os.path.join(inst, "launchers", "meu_atalho.cmd")),
               u"a lista tira o que e' NOSSO; remocao generica desfaz a regra")

        bloco = m.group(0)
        sem = re.sub(r'(?m)^[ \t]*"launchers\\start_engine\.cmd",?[ \t]*\r?\n',
                     u"", bloco)
        sem = re.sub(r",(\s*\))$", r"\1", sem)
        isca = texto.replace(bloco, sem)
        checar(u"(isca montada: a linha saiu da lista)",
               isca != texto and u"start_engine" not in sem)
        rc2, t2, inst2 = _cenario("isca", isca)
        checar(u"(isca) sem a linha, o lancador FICA -- a checagem sabe "
               u"reprovar",
               rc2 == 0 and os.path.isfile(
                   os.path.join(inst2, "launchers", "start_engine.cmd")),
               u"rc=%s %s" % (rc2, t2[-200:]))
    finally:
        shutil.rmtree(base, ignore_errors=True)


def main():
    print(u"=" * 68)
    print(u"test_lifecycle | atualizar e desinstalar uma estacao")
    print(u"=" * 68)
    teste_acha_a_instalacao_com_nome_de_pasta_livre()
    teste_atualizar()
    teste_a_porta_ocupada_diz_de_quem_e()
    teste_atualizar_tira_o_lancador_do_motor_http()
    teste_atualizar_tira_o_calibrador_apagado()
    teste_atualizar_leva_o_notice()
    teste_atualizar_renova_o_texto_aceito()
    teste_atualizar_refaz_o_icone_do_atalho()
    teste_desinstalar()
    teste_desinstalar_diz_o_que_fica_fora()
    teste_desinstalar_do_duplo_clique()
    teste_desinstalar_pela_interface()
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
