# -*- coding: utf-8 -*-
import json
import os
import socket
import subprocess
import sys
import tempfile
import time

from urllib.parse import urlsplit

# GUARDA: o Python embeddable da estacao nao poe a pasta do script no caminho; os import radai_* das funcoes dependem desta linha.
_PASTA_DO_LANCADOR = os.path.dirname(os.path.abspath(__file__))
if _PASTA_DO_LANCADOR not in sys.path:
    sys.path.insert(0, _PASTA_DO_LANCADOR)

CREATE_NO_WINDOW = 0x08000000
CREATE_BREAKAWAY_FROM_JOB = 0x01000000
CREATE_NEW_PROCESS_GROUP = 0x00000200
SYNCHRONIZE = 0x00100000
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
WAIT_TIMEOUT = 0x102
ERROR_INVALID_PARAMETER = 87
ERROR_ALREADY_EXISTS = 183

VARIAVEL_OCULTO = "RADAI_MOTOR_OCULTO"
VARIAVEL_CONSOLE = "RADAI_CONSOLE_DO_MOTOR"
VARIAVEL_NAVEGADOR = "RADAI_NAVEGADOR"
VARIAVEL_TEMP_DO_USUARIO = "RADAI_TEMP_DO_USUARIO"
VARIAVEL_LOG = "RADAI_LOG_DO_LANCADOR"
RODANDO, ENCERRADO = "rodando", "encerrado"
PORTA_PADRAO = 8777
TETO_DA_ESPERA_S = 300.0
TETO_DO_ENCERRAMENTO_S = 45.0
TETO_DA_DERRUBADA_S = 15.0
TETO_DO_SUCESSOR_S = 60.0
LINHAS_DO_RELATO = 40
NOME_DO_MOTOR = "radai_watcher.py"
NOME_DO_LANCADOR = "radai_lancador.py"
NOME_DO_LOG = "radai_lancador.log"
TETO_DO_LOG = 512 * 1024
PASTA_DO_PERFIL = "radai_janela"
ROTA_REABRIR = "/api/reabrir"
NOMES_DO_PYTHON = ("python.exe", "pythonw.exe")
RC_ABRIR_PELO_LOTE = 90
RC_NAO_ENCERROU = 2
ROTA_TENTAR = "/tentar"
TETO_DA_NOVA_TENTATIVA_S = 600.0
GIF_DE_UM_PIXEL = (b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff"
                   b"\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01"
                   b"\x00\x01\x00\x00\x02\x02D\x01\x00;")

NO_AR, SAIU, DEMOROU = "no_ar", "saiu", "demorou"
PERGUNTOU, EM_CURSO = "perguntou", "em_curso"
LIVRE, RESTO, TRAVADA = "livre", "resto", "travada"
PARADA, PROCESSANDO, OUTRO = "parada", "processando", "outro"


def porta_da_url(url, padrao=PORTA_PADRAO):
    try:
        p = urlsplit(str(url or "")).port
        return int(p) if p else int(padrao)
    except Exception:
        return int(padrao)


def arquivo_do_console(porta, pasta=None):
    return os.path.join(pasta or tempfile.gettempdir(),
                        "radai_motor_%d.txt" % int(porta))


def arquivo_de_estado(porta, base=None):
    base = base or os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, "RADIOTERAPIA_AI", "motor_%d.json" % int(porta))


def arquivo_de_log(pasta=None):
    fixo = (os.environ.get(VARIAVEL_LOG) or u"").strip()
    if fixo:
        return fixo
    return os.path.join(pasta or os.path.dirname(os.path.abspath(__file__)),
                        NOME_DO_LOG)


def _criado(pid):
    try:
        import radai_pulso
        return radai_pulso._criado_em(pid)
    except Exception:
        return None


def _lista_de_processos():
    try:
        import radai_pulso
        return radai_pulso._processos()
    except Exception:
        return []


def marcar_estado(porta, estado, base=None):
    try:
        cam = arquivo_de_estado(porta, base)
        os.makedirs(os.path.dirname(cam), exist_ok=True)
        dados = {"estado": estado, "pid": os.getpid(),
                 "hora": time.strftime("%Y-%m-%d %H:%M:%S"),
                 "exe": python_deste_processo()}
        # GUARDA: PID + instante de criação é a identidade do processo; só
        # com os dois a próxima abertura pode derrubar o que sobrou.
        c = _criado(os.getpid())
        if c is not None:
            dados["criado"] = c
        tmp = cam + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(dados, f)
        os.replace(tmp, cam)
        return True
    except Exception:
        return False


def ler_registro(porta, base=None):
    try:
        with open(arquivo_de_estado(porta, base), encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        return None
    return d if isinstance(d, dict) else None


def saida_anormal(porta, base=None):
    d = ler_registro(porta, base)
    return d if d and d.get("estado") == RODANDO else None


def limpar_o_console(caminho, fd=1):
    try:
        if not caminho or not os.path.samestat(os.fstat(fd), os.stat(caminho)):
            return False
        os.ftruncate(fd, 0)
        os.lseek(fd, 0, os.SEEK_SET)
        return True
    except Exception:
        return False


def _kernel32():
    import ctypes
    from ctypes import wintypes
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.OpenProcess.restype = wintypes.HANDLE
    k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k.CloseHandle.argtypes = [wintypes.HANDLE]
    k.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    k.WaitForSingleObject.restype = wintypes.DWORD
    k.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD)]
    k.QueryFullProcessImageNameW.restype = wintypes.BOOL
    k.CreateMutexW.restype = wintypes.HANDLE
    k.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL,
                               wintypes.LPCWSTR]
    return k


def imagem_do_processo(pid):
    if os.name != "nt":
        return u""
    try:
        import ctypes
        from ctypes import wintypes
        k = _kernel32()
        h = k.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
        if not h:
            return u""
        try:
            buf = ctypes.create_unicode_buffer(32768)
            n = wintypes.DWORD(32768)
            if not k.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n)):
                return u""
            return buf.value
        finally:
            k.CloseHandle(h)
    except Exception:
        return u""


def esperar_sair(pid, teto_s=0.0):
    if os.name != "nt":
        fim = time.monotonic() + float(teto_s)
        while True:
            try:
                os.kill(int(pid), 0)
            except OSError:
                return True
            if time.monotonic() >= fim:
                return False
            time.sleep(0.2)
    try:
        import ctypes
        k = _kernel32()
        h = k.OpenProcess(SYNCHRONIZE, False, int(pid))
        if not h:
            # GUARDA: só ERROR_INVALID_PARAMETER quer dizer que o PID não
            # existe; acesso negado é processo vivo de outro usuário.
            return ctypes.get_last_error() == ERROR_INVALID_PARAMETER
        try:
            return k.WaitForSingleObject(
                h, int(max(0.0, float(teto_s)) * 1000)) != WAIT_TIMEOUT
        finally:
            k.CloseHandle(h)
    except Exception:
        return False


def processo_vivo(pid):
    return not esperar_sair(pid, 0.0)


def python_deste_processo():
    # GUARDA: o sys.executable de um venv é o redirecionador, e não o binário
    # que roda; a identidade do Python é a imagem do próprio processo.
    return imagem_do_processo(os.getpid()) or os.path.abspath(sys.executable)


def _norm(caminho):
    try:
        return os.path.normcase(os.path.realpath(os.path.abspath(caminho)))
    except Exception:
        return os.path.normcase(str(caminho or u""))


def instancia_registrada(porta, base=None, exe=None, vivo=processo_vivo,
                         imagem=imagem_do_processo, criado=_criado,
                         processos=_lista_de_processos):
    d = ler_registro(porta, base)
    if not d:
        return None
    try:
        pid = int(d.get("pid") or 0)
        marca = int(d.get("criado"))
    except (TypeError, ValueError):
        return None
    if pid <= 0 or pid == os.getpid():
        return None
    nosso = _norm(exe or python_deste_processo())

    def do_programa(p):
        img = imagem(p)
        return bool(img) and _norm(img) == nosso

    principal = None
    if vivo(pid) and criado(pid) == marca and do_programa(pid):
        principal = pid
    orfaos = []
    for (p, pai, nome) in processos():
        if pai != pid or p == pid or str(nome).lower() not in NOMES_DO_PYTHON:
            continue
        # GUARDA: o filho tem de ter nascido depois do motor registrado; um
        # PID reaproveitado não herda os filhos de ninguém.
        c = criado(p)
        if c is None or c < marca:
            continue
        if do_programa(p):
            orfaos.append(p)
    if principal is None and not orfaos:
        return None
    return {"pid": principal, "orfaos": orfaos,
            "estado": d.get("estado"), "hora": d.get("hora")}


def _taskkill(pid):
    raiz = os.environ.get("SystemRoot")
    tk = os.path.join(raiz, "System32", "taskkill.exe") if raiz else ""
    kw = {"creationflags": CREATE_NO_WINDOW} if os.name == "nt" else {}
    try:
        subprocess.run([tk if tk and os.path.isfile(tk) else "taskkill",
                        "/PID", str(int(pid)), "/T", "/F"],
                       capture_output=True, timeout=30, **kw)
        return True
    except Exception:
        return False


def derrubar(reg, matar=_taskkill):
    alvos = []
    if reg and reg.get("pid"):
        alvos.append(int(reg["pid"]))
    for p in (reg or {}).get("orfaos") or []:
        if int(p) not in alvos:
            alvos.append(int(p))
    for p in alvos:
        matar(p)
    return alvos


def porta_responde(porta, teto_s=1.0):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(teto_s)
    try:
        s.connect(("127.0.0.1", int(porta)))
        return True
    except Exception:
        return False
    finally:
        try:
            s.close()
        except Exception:
            pass


def _pedir(porta, caminho, dados=None, teto_s=3.0):
    from urllib.request import ProxyHandler, Request, build_opener
    # GUARDA: sem ProxyHandler({}) o urllib usa o proxy do Windows, que
    # não exclui 127.0.0.1; numa rede de hospital o pedido iria ao proxy.
    abrir = build_opener(ProxyHandler({})).open
    corpo = None if dados is None else json.dumps(dados).encode("utf-8")
    req = Request("http://127.0.0.1:%d%s" % (int(porta), caminho), data=corpo,
                  headers={"Content-Type": "application/json"},
                  method="GET" if corpo is None else "POST")
    with abrir(req, timeout=teto_s) as r:
        return json.loads(r.read().decode("utf-8", "replace") or "{}")


def ler_pulso(porta, teto_s=3.0):
    try:
        d = _pedir(porta, "/api/pulso", teto_s=teto_s)
    except Exception:
        return None
    return d if isinstance(d, dict) and d.get("radai") is True else None


def e_o_nosso_painel(porta, teto_s=3.0):
    return ler_pulso(porta, teto_s) is not None


def ler_status(porta, teto_s=5.0):
    try:
        d = _pedir(porta, "/api/status", teto_s=teto_s)
    except Exception:
        return None
    return d if isinstance(d, dict) else None


def pedir_para_encerrar(porta):
    try:
        d = _pedir(porta, "/api/encerrar", {"modo": "tudo"}, teto_s=10.0)
        return bool(isinstance(d, dict) and d.get("ok"))
    except Exception:
        return False


def estado_da_instancia(porta, responde=porta_responde, pulso=ler_pulso,
                        status=ler_status, registrada=instancia_registrada,
                        tentativas=3, dormir=time.sleep):
    reg = registrada(porta)
    if not responde(porta):
        return (RESTO, reg) if reg else (LIVRE, None)
    p = None
    for i in range(max(1, int(tentativas))):
        p = pulso(porta)
        if p:
            break
        # GUARDA: um laço de eventos ocupado por segundos não é instância
        # travada; só três silêncios seguidos justificam derrubar.
        if i + 1 < tentativas:
            dormir(1.0)
    if not p:
        return (TRAVADA, reg) if reg else (OUTRO, None)
    s = status(porta)
    if isinstance(s, dict) and "ocupado" in s:
        # GUARDA: o turno da noite aberto ou agendado segura o fechar pelo X;
        # encerrar sem perguntar derrubaria o turno com o vigia ocioso.
        ocupado = bool(s.get("ocupado") or s.get("current")
                       or s.get("overnight") or s.get("turno_agendado"))
        return (PROCESSANDO if ocupado else PARADA), reg
    return PROCESSANDO, reg


def esperar_a_porta_livrar(porta, teto_s, responde=porta_responde,
                           relogio=time.monotonic, dormir=time.sleep):
    fim = relogio() + float(teto_s)
    while responde(porta):
        if relogio() >= fim:
            return False
        dormir(0.5)
    return True


def encerrar_instancia(porta, estado, reg, escrever, pedir=pedir_para_encerrar,
                       derrubar_=derrubar, livre=esperar_a_porta_livrar,
                       sair=esperar_sair, teto_s=TETO_DO_ENCERRAMENTO_S):
    pid = (reg or {}).get("pid")
    if estado in (PARADA, PROCESSANDO):
        pedir(porta)
        if livre(porta, teto_s):
            if not pid or sair(pid, TETO_DA_DERRUBADA_S):
                return True
            escrever(u" The previous session closed its panel, but its "
                     u"process (PID %d) is still running: stopping it." % pid)
        elif not reg:
            return False
        else:
            escrever(u" The previous session did not close in %d s: "
                     u"stopping it." % int(teto_s))
    if not reg:
        return not porta_responde(porta)
    alvos = derrubar_(reg)
    escrever(u" Stopped process(es): %s." % u", ".join(str(a) for a in alvos))
    ok = livre(porta, TETO_DA_DERRUBADA_S)
    if pid:
        ok = sair(pid, TETO_DA_DERRUBADA_S) and ok
    return ok


_TRAVAS = []


def trava_do_lancador(porta):
    if os.name != "nt":
        return True
    try:
        import ctypes
        k = _kernel32()
        h = k.CreateMutexW(None, False, u"Local\\radai_lancador_%d" % int(porta))
        erro = ctypes.get_last_error()
        if not h:
            return True
        if erro == ERROR_ALREADY_EXISTS:
            k.CloseHandle(h)
            return False
        # GUARDA: o handle vive até o processo sair; é ele que faz o segundo
        # clique no atalho esperar o primeiro, em vez de derrubar o motor que
        # ainda está subindo.
        _TRAVAS.append(h)
        return True
    except Exception:
        return True


def candidatos_de_navegador(ambiente=None):
    amb = os.environ if ambiente is None else ambiente
    pf86 = amb.get("ProgramFiles(x86)") or u""
    pf = amb.get("ProgramFiles") or u""
    local = amb.get("LOCALAPPDATA") or u""
    edge = os.path.join("Microsoft", "Edge", "Application", "msedge.exe")
    chrome = os.path.join("Google", "Chrome", "Application", "chrome.exe")
    # GUARDA: o Windows 10 LTSB (build 14393) não traz o Edge; o recuo tenta
    # o Chrome e depois o navegador padrão.
    saida = []
    for base, rel in ((pf86, edge), (pf, edge), (pf, chrome), (pf86, chrome),
                      (local, chrome)):
        if base:
            c = os.path.join(base, rel)
            if c not in saida:
                saida.append(c)
    return saida


def perfil_da_janela(ambiente=None):
    amb = os.environ if ambiente is None else ambiente
    base = (amb.get(VARIAVEL_TEMP_DO_USUARIO) or amb.get("TEMP")
            or amb.get("TMP") or tempfile.gettempdir())
    return os.path.join(base, PASTA_DO_PERFIL)


def _abrir_no_padrao(alvo):
    if os.name == "nt":
        os.startfile(alvo)
    else:
        import webbrowser
        webbrowser.open(alvo)


def abrir_navegador(alvo, arquivo=None, ambiente=None, popen=None,
                    existe=os.path.isfile, padrao=_abrir_no_padrao):
    amb = os.environ if ambiente is None else ambiente
    if str(amb.get(VARIAVEL_NAVEGADOR, "")).strip() == "0":
        return u""
    popen = popen or subprocess.Popen
    for exe in candidatos_de_navegador(amb):
        if not existe(exe):
            continue
        cmd = [exe, "--app=" + alvo, "--start-fullscreen",
               "--user-data-dir=" + perfil_da_janela(amb),
               "--no-first-run", "--no-default-browser-check"]
        kw = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                  stderr=subprocess.DEVNULL, close_fds=True)
        try:
            try:
                popen(cmd, creationflags=CREATE_BREAKAWAY_FROM_JOB
                      if os.name == "nt" else 0, **kw)
            except OSError:
                popen(cmd, **kw)
            return exe
        except OSError:
            continue
    try:
        padrao(arquivo or alvo)
        return u"padrao"
    except Exception:
        return u""


def pagina_de_carregamento(porta, url):
    try:
        import radai_carregando
    except Exception:
        return None
    try:
        return radai_carregando.gravar(
            porta, url, pasta_do_programa=os.path.dirname(
                os.path.abspath(__file__)))
    except Exception:
        return None


def informar_a_pagina(porta, estado, rc=None, tentar=None):
    try:
        import radai_carregando
        return radai_carregando.gravar_estado(porta, estado, rc,
                                              tentar=tentar)
    except Exception:
        return False


def _responder(conexao, codigo, corpo, tipo):
    cab = (u"HTTP/1.0 %d %s\r\nContent-Type: %s\r\nContent-Length: %d\r\n"
           u"Cache-Control: no-store\r\nConnection: close\r\n\r\n"
           % (codigo, u"OK" if codigo == 200 else u"Not Found", tipo,
              len(corpo)))
    conexao.sendall(cab.encode("ascii") + corpo)


def esperar_nova_tentativa(porta, rc, escrever, informar=None,
                           teto_s=TETO_DA_NOVA_TENTATIVA_S,
                           relogio=time.monotonic):
    informar = informar or informar_a_pagina
    import secrets
    ficha = secrets.token_hex(12)
    try:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.bind(("127.0.0.1", 0))
        srv.listen(4)
        srv.settimeout(0.5)
    except Exception:
        informar(porta, SAIU, rc)
        return False
    caminho = u"%s/%s" % (ROTA_TENTAR, ficha)
    try:
        url = u"http://127.0.0.1:%d%s" % (srv.getsockname()[1], caminho)
        # GUARDA: a ficha no caminho impede que outra pagina aberta no
        # navegador peca para subir o motor de novo.
        informar(porta, SAIU, rc, tentar=url)
        escrever(u" To try again, use Try again on the loading page; this "
                 u"window waits up to %d min." % int(float(teto_s) // 60))
        fim = relogio() + float(teto_s)
        while relogio() < fim:
            try:
                c, _ = srv.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                c.settimeout(3.0)
                pedido = c.recv(4096).decode("latin-1", "replace")
                linha = pedido.split(u"\r\n", 1)[0].split(u" ")
                alvo = linha[1].split(u"?", 1)[0] if len(linha) > 1 else u""
                if linha[0] == u"GET" and alvo == caminho:
                    informar(porta, u"subindo", None)
                    _responder(c, 200, GIF_DE_UM_PIXEL, u"image/gif")
                    return True
                _responder(c, 404, b"", u"text/plain")
            except Exception:
                pass
            finally:
                try:
                    c.close()
                except Exception:
                    pass
        informar(porta, SAIU, rc)
        return False
    finally:
        try:
            srv.close()
        except Exception:
            pass


def _uri(caminho):
    try:
        import pathlib
        return pathlib.Path(os.path.abspath(caminho)).as_uri()
    except Exception:
        return u"file:///" + os.path.abspath(caminho).replace(os.sep, "/")


def comando_do_motor(python=None, pasta=None, motor=None):
    pasta = pasta or os.path.dirname(os.path.abspath(__file__))
    return [python or sys.executable, motor or os.path.join(pasta, NOME_DO_MOTOR)]


def ambiente_do_motor(base=None, console=None):
    amb = dict(os.environ if base is None else base)
    amb[VARIAVEL_OCULTO] = "1"
    if console:
        amb[VARIAVEL_CONSOLE] = str(console)
    return amb


def subir_o_motor(comando, console, ambiente=None, popen=None):
    popen = popen or subprocess.Popen
    saida = open(console, "wb")
    base = CREATE_NO_WINDOW if os.name == "nt" else 0
    kw = dict(stdin=subprocess.DEVNULL, stdout=saida, stderr=subprocess.STDOUT,
              env=ambiente, cwd=os.path.dirname(comando[-1]) or None)
    try:
        try:
            return popen(comando, creationflags=base | (
                CREATE_BREAKAWAY_FROM_JOB if os.name == "nt" else 0), **kw)
        except OSError:
            # GUARDA: a tarefa do Windows que abriu esta janela pode proibir
            # sair dela; sem o recuo o motor não sobe.
            return popen(comando, creationflags=base, **kw)
    finally:
        saida.close()


def comando_do_sucessor(porta, pid, python=None, lancador=None, motor=None):
    lanc = lancador or os.path.abspath(__file__)
    cmd = [python or sys.executable, lanc,
           "--url", "http://127.0.0.1:%d/" % int(porta),
           "--sucessor", str(int(pid)),
           "--log", arquivo_de_log(os.path.dirname(lanc))]
    if motor:
        cmd += ["--motor", motor]
    return cmd


def ambiente_do_sucessor(base=None):
    amb = dict(os.environ if base is None else base)
    usuario = amb.get(VARIAVEL_TEMP_DO_USUARIO)
    if usuario:
        # GUARDA: o motor reaponta o próprio TEMP; o sucessor volta ao do
        # usuário, onde moram o console e o perfil da janela.
        amb["TEMP"] = amb["TMP"] = usuario
        amb.pop("TMPDIR", None)
    amb.pop(VARIAVEL_CONSOLE, None)
    amb.pop(VARIAVEL_OCULTO, None)
    return amb


def subir_sucessor(porta, pid=None, python=None, lancador=None, motor=None,
                   ambiente=None, popen=None):
    popen = popen or subprocess.Popen
    pid = int(pid or os.getpid())
    if motor is None:
        principal = sys.modules.get("__main__")
        arq = getattr(principal, "__file__", None) if principal else None
        if arq and os.path.basename(arq) == NOME_DO_MOTOR:
            motor = os.path.abspath(arq)
    cmd = comando_do_sucessor(porta, pid, python, lancador, motor)
    base = (CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP) if os.name == "nt" else 0
    kw = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
              stderr=subprocess.DEVNULL, env=ambiente_do_sucessor(ambiente),
              cwd=os.path.dirname(cmd[1]) or None, close_fds=True)
    try:
        p = popen(cmd, creationflags=base | (
            CREATE_BREAKAWAY_FROM_JOB if os.name == "nt" else 0), **kw)
    except OSError:
        p = popen(cmd, creationflags=base, **kw)
    try:
        import radai_pulso
        radai_pulso.poupar(p.pid)
    except Exception:
        pass
    return p


def aguardar_a_saida_do_antigo(pid, porta, escrever, sair=esperar_sair,
                               registrada=instancia_registrada,
                               derrubar_=derrubar, teto_s=TETO_DO_SUCESSOR_S):
    if sair(pid, teto_s):
        return True
    reg = registrada(porta)
    if reg and reg.get("pid") == int(pid):
        escrever(u" The previous session (PID %d) did not finish closing in "
                 u"%d s: stopping it." % (int(pid), int(teto_s)))
        derrubar_(reg)
        return sair(pid, TETO_DA_DERRUBADA_S)
    return False


def esperar_o_painel(proc, porta, teto_s=TETO_DA_ESPERA_S, intervalo_s=0.5,
                     responde=None, relogio=time.monotonic,
                     dormir=time.sleep):
    # GUARDA: a porta abrir não basta; com outro programa nela, o motor
    # morre com 4 e o painel nunca é o nosso.
    responde = responde or (lambda p: porta_responde(p) and e_o_nosso_painel(p))
    fim = relogio() + float(teto_s)
    while True:
        rc = proc.poll()
        if rc is not None:
            return SAIU, rc
        if responde(porta):
            return NO_AR, 0
        if relogio() >= fim:
            return DEMOROU, 0
        dormir(intervalo_s)


def cauda(caminho, n=LINHAS_DO_RELATO):
    try:
        with open(caminho, "rb") as f:
            texto = f.read().decode("utf-8", "replace")
    except Exception:
        return []
    return [l for l in texto.splitlines() if l.strip()][-int(n):]


def _escrever_no_console(m):
    try:
        sys.stdout.write(m + "\n")
        sys.stdout.flush()
    except Exception:
        pass


class Registro(object):
    def __init__(self, caminho, console=True):
        self.caminho = caminho
        self.console = console
        try:
            if caminho and os.path.getsize(caminho) > TETO_DO_LOG:
                with open(caminho, "rb") as f:
                    f.seek(-TETO_DO_LOG // 2, os.SEEK_END)
                    resto = f.read()
                with open(caminho, "wb") as f:
                    f.write(resto)
        except Exception:
            pass

    def __call__(self, m):
        if self.console:
            _escrever_no_console(m)
        if not self.caminho:
            return
        try:
            with open(self.caminho, "a", encoding="utf-8",
                      errors="replace") as f:
                f.write(u"%s [%d]%s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"),
                                          os.getpid(), m))
        except Exception:
            pass


def lancar(url, python=None, pasta=None, teto_s=TETO_DA_ESPERA_S,
           escrever=None, subir=subir_o_motor, esperar=esperar_o_painel,
           ambiente=None, anterior=saida_anormal, console=None,
           instancia=estado_da_instancia, encerrar=encerrar_instancia,
           abrir=abrir_navegador, carregando=pagina_de_carregamento,
           informar=informar_a_pagina, travar=trava_do_lancador,
           sucessor=None, motor=None, aguardar=aguardar_a_saida_do_antigo,
           tentar=None):
    escrever = escrever or _escrever_no_console
    porta = porta_da_url(url)

    def abrir_a_pagina():
        pagina = carregando(porta, url)
        if not pagina:
            return False
        escrever(u" Opening the loading page in the browser.")
        return bool(abrir(_uri(pagina), arquivo=pagina))

    if not travar(porta):
        escrever(u" Another launch is already starting the program; showing "
                 u"its loading page.")
        if sucessor:
            return EM_CURSO, 0
        return EM_CURSO, (0 if abrir_a_pagina() else RC_ABRIR_PELO_LOTE)

    if sucessor:
        escrever(u" Reopening the program after the previous session (PID %d)."
                 % int(sucessor))
        aguardar(int(sucessor), porta, escrever)

    estado, reg = instancia(porta)
    if estado == PROCESSANDO and not sucessor:
        escrever(u" The program is already open and processing a series.")
        escrever(u" The question is in the browser: keep the open session, "
                 u"or close it and start again.")
        aberto = abrir(url.rstrip("/") + ROTA_REABRIR)
        return PERGUNTOU, (0 if aberto else RC_ABRIR_PELO_LOTE)
    if estado == PARADA:
        escrever(u" The program was already open and idle: closing it to "
                 u"start a fresh session.")
    elif estado in (RESTO, TRAVADA):
        escrever(u" A previous session was left running without answering "
                 u"(PID %s): stopping it."
                 % ((reg or {}).get("pid") or u", ".join(
                     str(p) for p in (reg or {}).get("orfaos") or [])))
    elif estado == PROCESSANDO:
        escrever(u" The previous session is still closing: stopping it.")
    elif estado == OUTRO:
        escrever(u" Port %d answers, but not as this program." % porta)
    if estado in (PARADA, PROCESSANDO, RESTO, TRAVADA):
        if not encerrar(porta, estado, reg, escrever):
            escrever(u" The previous session did not close; the engine will "
                     u"report the busy port.")

    console = console or arquivo_do_console(porta)
    ant = anterior(porta)
    if ant:
        escrever(u" The previous engine session (started %s) did not close "
                 u"normally. The station log has what it was doing."
                 % ant.get("hora", u"?"))
        for linha in cauda(console, 15):
            escrever(u"   " + linha)
    aberto = False if sucessor else abrir_a_pagina()
    while True:
        proc = subir(comando_do_motor(python, pasta, motor), console,
                     ambiente_do_motor(ambiente, console))
        escrever(u" Starting the engine in the background (no window)...")
        estado_m, rc = esperar(proc, porta, teto_s)
        if estado_m != SAIU:
            break
        escrever(u"")
        escrever(u" THE ENGINE STOPPED BEFORE THE PANEL CAME UP (code %s)."
                 % rc)
        for linha in cauda(console):
            escrever(u"   " + linha)
        com_botao = bool(aberto and tentar is not None)
        if com_botao and tentar(porta, rc, escrever):
            escrever(u" Trying again, as asked on the loading page.")
            continue
        if not com_botao:
            informar(porta, SAIU, rc)
        try:
            os.remove(console)
        except OSError:
            pass
        return SAIU, rc
    if estado_m == NO_AR:
        escrever(u" Panel is up at %s - this window closes by itself." % url)
        escrever(u" To quit, use CLOSE APP in the panel, or close the "
                 u"browser window: the engine stops a few seconds later.")
    elif estado_m == DEMOROU:
        escrever(u" The panel did not answer in %d s; opening the browser "
                 u"anyway." % int(teto_s))
    return estado_m, (0 if (aberto or sucessor) else RC_ABRIR_PELO_LOTE)


def encerrar_para_atualizar(url, escrever, instancia=estado_da_instancia,
                            encerrar=encerrar_instancia):
    porta = porta_da_url(url)
    estado, reg = instancia(porta)
    if estado == LIVRE:
        escrever(u" The program is not running on port %d." % porta)
        return 0
    if estado == OUTRO:
        escrever(u" Port %d answers, but not as this program; nothing was "
                 u"stopped." % porta)
        return 0
    escrever(u" Closing the running program (%s) before replacing its code."
             % estado)
    if encerrar(porta, estado, reg, escrever):
        escrever(u" The program is closed.")
        return 0
    escrever(u" COULD NOT CLOSE THE RUNNING PROGRAM on port %d." % porta)
    return RC_NAO_ENCERROU


def _valor(args, chave):
    if chave in args:
        i = args.index(chave)
        if i + 1 < len(args):
            return args[i + 1]
    return None


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    url = _valor(args, "--url") or "http://127.0.0.1:%d/" % PORTA_PADRAO
    try:
        sucessor = int(_valor(args, "--sucessor") or 0) or None
    except ValueError:
        sucessor = None
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass
    escrever = Registro(_valor(args, "--log") or arquivo_de_log(),
                        console=not sucessor)
    if "--encerrar" in args:
        return encerrar_para_atualizar(url, escrever)
    estado, rc = lancar(url, escrever=escrever, sucessor=sucessor,
                        motor=_valor(args, "--motor"),
                        tentar=esperar_nova_tentativa)
    if estado == SAIU:
        return int(rc) if rc else 1
    return int(rc or 0)


if __name__ == "__main__":
    sys.exit(main())
