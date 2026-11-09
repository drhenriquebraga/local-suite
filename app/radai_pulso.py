# -*- coding: utf-8 -*-
import json
import os
import re
import subprocess
import threading
import time

TOLERANCIA_S = 180.0
INTERVALO_DA_TELA_S = 5
GRACA_DO_FECHAR_S = 15.0
JANELA_DE_CORRIDA_S = 3.0
INTERVALO_DA_VIGILANCIA_S = 1.0
TETO_DE_ABAS = 64
VARIAVEL_TOLERANCIA = "RADAI_PULSO_S"
VARIAVEL_GRACA = "RADAI_PULSO_GRACA_S"
VARIAVEL_OCULTO = "RADAI_MOTOR_OCULTO"
ROTA = "/api/pulso"
ROTA_SINAL = "/api/pulso/sinal"
CANAL = "radai-pulso"
MARCA = "radai-pulso-js"

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001

GIF_DO_SINAL = (b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff"
                b"!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01"
                b"\x00\x00\x02\x02D\x01\x00;")

# GUARDA: ES5 puro (XMLHttpRequest, sem arrow nem fetch) para pulsar também
# na página do portão que só o IE11 abre; o canal e o beacon são opcionais.
# GUARDA: a aba que fecha avisa as irmãs pelo canal, e elas pulsam na hora;
# sem isso a graça de 15 s mataria o motor com outra aba aberta.
SCRIPT = (u'<script id="@MARCA@">(function(){if(window.__radaiPulso)return;'
          u'window.__radaiPulso=1;'
          u'var aba=String(Math.random()).slice(2,10)+String(new Date().getTime());'
          u'function corpo(s){var o={aba:aba};if(s)o.saindo=true;'
          u'return JSON.stringify(o)}'
          u'function p(){try{var x=new XMLHttpRequest();'
          u'x.open("POST","@ROTA@",true);x.setRequestHeader("Content-Type",'
          u'"application/json");x.send(corpo(0))}catch(e){}}'
          u'var c=null;try{if(window.BroadcastChannel){c=new BroadcastChannel("@CANAL@");'
          u'c.onmessage=function(){p();setTimeout(p,1500)}}}catch(e){}'
          u'p();setInterval(p,@INTERVALO@);'
          u'try{document.addEventListener("visibilitychange",'
          u'function(){if(!document.hidden)p()})}catch(e){}'
          u'try{window.addEventListener("pageshow",function(e){if(e&&e.persisted)p()})}catch(e){}'
          u'try{window.addEventListener("pagehide",function(){'
          u'try{if(c)c.postMessage("saindo")}catch(e){}'
          u'try{if(navigator.sendBeacon)navigator.sendBeacon("@ROTA@",corpo(1))}catch(e){}'
          u'})}catch(e){}'
          u'})();</script>'
          ).replace(u"@MARCA@", MARCA).replace(u"@ROTA@", ROTA).replace(
              u"@CANAL@", CANAL).replace(u"@INTERVALO@",
                                         str(INTERVALO_DA_TELA_S * 1000))


def motor_oculto(ambiente=None):
    amb = os.environ if ambiente is None else ambiente
    return str(amb.get(VARIAVEL_OCULTO, "")).strip() == "1"


def _segundos(bruto):
    if bruto is None or str(bruto).strip() == "":
        return None
    try:
        return max(0.0, float(str(bruto).strip().replace(",", ".")))
    except ValueError:
        return None


def tolerancia_do_ambiente(oculto, ambiente=None):
    amb = os.environ if ambiente is None else ambiente
    v = _segundos(amb.get(VARIAVEL_TOLERANCIA))
    if v is not None:
        return v
    return TOLERANCIA_S if oculto else 0.0


def graca_do_ambiente(ambiente=None):
    amb = os.environ if ambiente is None else ambiente
    v = _segundos(amb.get(VARIAVEL_GRACA))
    return GRACA_DO_FECHAR_S if v is None else v


_ABA_VALIDA = re.compile(r"^[A-Za-z0-9_-]{1,40}$")


def ler_corpo_do_pulso(bruto):
    try:
        if isinstance(bruto, bytes):
            bruto = bruto.decode("utf-8", "replace")
        d = json.loads(bruto or u"{}")
    except Exception:
        return None, False
    if not isinstance(d, dict):
        return None, False
    aba = d.get("aba")
    aba = aba if isinstance(aba, str) and _ABA_VALIDA.match(aba) else None
    return aba, d.get("saindo") is True


class Pulso(object):
    def __init__(self, tolerancia_s, relogio=None, graca_s=None):
        self.tolerancia_s = float(tolerancia_s or 0.0)
        self.graca_s = float(graca_do_ambiente() if graca_s is None
                             else graca_s)
        self._relogio = relogio or time.monotonic
        self._trava = threading.Lock()
        self._ultimo = self._relogio()
        self._abas = {}
        self._saida = None
        self.batidas = 0
        self.avisos = 0
        self.saidas = 0

    def bater(self, aba=None):
        with self._trava:
            agora = self._relogio()
            self._ultimo = agora
            self.batidas += 1
            s = self._saida
            # GUARDA: o pulso que a aba mandou antes de fechar pode chegar
            # depois do aviso dela; não conta como aba viva.
            if (s is not None and aba is not None and aba == s[0]
                    and agora - s[1] <= JANELA_DE_CORRIDA_S):
                return
            if aba is not None:
                self._abas[aba] = agora
                if len(self._abas) > TETO_DE_ABAS:
                    velha = min(self._abas, key=self._abas.get)
                    self._abas.pop(velha, None)
            self._saida = None

    def sair(self, aba=None):
        with self._trava:
            agora = self._relogio()
            self.avisos += 1
            if aba is not None:
                self._abas.pop(aba, None)
            # GUARDA: a irmã acordada pelo canal pode pulsar ANTES de o
            # aviso desta aba chegar; o pulso recente dela vale como resposta.
            vivas = [a for (a, t) in self._abas.items()
                     if agora - t <= JANELA_DE_CORRIDA_S]
            if vivas:
                self._saida = None
                return False
            self._saida = (aba, agora)
            self.saidas += 1
            return True

    def saida_pendente(self):
        with self._trava:
            return self._saida is not None

    def esquecer_saida(self):
        with self._trava:
            self._saida = None

    def saida_vencida(self):
        if not self.armado() or self.graca_s <= 0:
            return False
        with self._trava:
            s = self._saida
            return s is not None and self._relogio() - s[1] >= self.graca_s

    def silencio_s(self):
        with self._trava:
            return max(0.0, self._relogio() - self._ultimo)

    def armar(self, tolerancia_s):
        with self._trava:
            self.tolerancia_s = float(tolerancia_s or 0.0)
            self._ultimo = self._relogio()

    def armado(self):
        return self.tolerancia_s > 0

    def venceu(self):
        return self.armado() and self.silencio_s() >= self.tolerancia_s


PASTA_DO_PERFIL = "radai_janela"
TRAVA_DO_CHROMIUM = "lockfile"


VARIAVEL_TEMP_DO_USUARIO = "RADAI_TEMP_DO_USUARIO"


def perfil_da_janela(ambiente=None):
    amb = os.environ if ambiente is None else ambiente
    # GUARDA: o lancador cria o perfil no %TEMP% do USUARIO; o vigia reaponta
    # o proprio TEMP (radai_archive._marcar_ambiente) e guarda o de antes aqui.
    base = (amb.get(VARIAVEL_TEMP_DO_USUARIO) or amb.get("TEMP")
            or amb.get("TMP") or "")
    return os.path.join(base, PASTA_DO_PERFIL) if base else ""


def navegador_do_programa_aberto(perfil=None):
    # GUARDA: o Chromium abre o lockfile com DELETE_ON_CLOSE; ele some quando
    # o navegador fecha, inclusive morto à força.
    perfil = perfil_da_janela() if perfil is None else perfil
    if not perfil or not os.path.isdir(perfil):
        return None
    return os.path.exists(os.path.join(perfil, TRAVA_DO_CHROMIUM))


def pedir_para_nao_suspender(sim):
    if os.name != "nt":
        return False
    try:
        import ctypes
        f = ctypes.windll.kernel32.SetThreadExecutionState
        f.restype = ctypes.c_uint
        f.argtypes = [ctypes.c_uint]
        bandeiras = ES_CONTINUOUS | (ES_SYSTEM_REQUIRED if sim else 0)
        return bool(f(bandeiras))
    except Exception:
        return False


class Vigilancia(object):
    # GUARDA: SetThreadExecutionState vale para a thread que o chama; quem
    # pede e quem solta tem de ser a mesma thread, viva até o fim do processo.
    def __init__(self, pulso, ao_vencer, ocupado, log=None,
                 intervalo_s=INTERVALO_DA_VIGILANCIA_S,
                 acordado=pedir_para_nao_suspender,
                 navegador_aberto=navegador_do_programa_aberto,
                 em_curso=None, ao_adiar=None):
        self.pulso = pulso
        self.navegador_aberto = navegador_aberto
        self.adormecida_dita = False
        self.ao_vencer = ao_vencer
        self.ocupado = ocupado
        self.em_curso = em_curso
        self.ao_adiar = ao_adiar
        self.adiando = False
        self.log = log or (lambda m: None)
        self.intervalo_s = float(intervalo_s)
        self.acordado = acordado
        self.pedindo_acordado = False
        self.venceu = False
        self._parar = threading.Event()
        self._thread = None

    def passo(self):
        try:
            oc = bool(self.ocupado())
        except Exception:
            oc = False
        if oc != self.pedindo_acordado:
            ok = self.acordado(oc)
            self.pedindo_acordado = oc
            if oc:
                self.log(u"energia: a fila esta rodando; pedi ao Windows para "
                         u"nao suspender a estacao%s"
                         % (u"" if ok else u" (o pedido nao foi aceito)"))
            else:
                self.log(u"energia: a fila esvaziou; o Windows volta a poder "
                         u"suspender a estacao")
        if self.venceu:
            return
        vencido = self.pulso.venceu()
        saiu = False
        if not vencido:
            try:
                saiu = bool(getattr(self.pulso, "saida_vencida",
                                    lambda: False)())
            except Exception:
                saiu = False
        if self.adiando and not (vencido or saiu):
            self._cancelar_adiamento()
            return
        if saiu:
            try:
                aberto = self.navegador_aberto()
            except Exception:
                aberto = None
            graca = getattr(self.pulso, "graca_s", GRACA_DO_FECHAR_S)
            if aberto:
                # GUARDA: outra janela do perfil do programa continua aberta;
                # quem decide daqui em diante é a tolerância.
                try:
                    self.pulso.esquecer_saida()
                except Exception:
                    pass
                self.log(u"pulso: uma aba do programa fechou e nenhuma outra "
                         u"respondeu em %.0f s, mas o navegador do programa "
                         u"continua aberto; nada foi encerrado" % graca)
                return
            if self._adiar(u"a ultima aba do programa foi fechada"):
                return
            self.venceu = True
            self.log(u"pulso: a ultima aba do programa foi fechada (nenhuma "
                     u"outra respondeu em %.0f s); encerrando tudo" % graca)
            try:
                self.ao_vencer()
            except Exception as e:
                self.log(u"pulso: o encerramento falhou (%s: %s)"
                         % (type(e).__name__, str(e)[:160]))
            return
        if vencido:
            # GUARDA: aba congelada pelo navegador não pulsa; só o navegador
            # fechado encerra a fila.
            try:
                aberto = self.navegador_aberto()
            except Exception:
                aberto = None
            if aberto is None and oc:
                # GUARDA: sem como saber se a janela fechou, a fila em curso
                # termina; o encerramento espera a fila esvaziar.
                if not self.adormecida_dita:
                    self.adormecida_dita = True
                    self.log(u"pulso: nenhuma tela respondeu em %.0f s e o "
                             u"perfil da janela do programa nao foi achado; "
                             u"com a fila rodando, nada foi encerrado"
                             % self.pulso.tolerancia_s)
                return
            if aberto:
                if not self.adormecida_dita:
                    self.adormecida_dita = True
                    self.log(u"pulso: nenhuma tela respondeu em %.0f s, mas o "
                             u"navegador do programa continua aberto (aba "
                             u"adormecida); nada foi encerrado"
                             % self.pulso.tolerancia_s)
                return
            if self._adiar(u"nenhuma tela do programa respondeu em %.0f s"
                           % self.pulso.tolerancia_s):
                return
            self.venceu = True
            self.log(u"pulso: nenhuma tela do programa respondeu em %.0f s "
                     u"(o navegador foi fechado); encerrando tudo"
                     % self.pulso.tolerancia_s)
            try:
                self.ao_vencer()
            except Exception as e:
                self.log(u"pulso: o encerramento falhou (%s: %s)"
                         % (type(e).__name__, str(e)[:160]))

    def _adiar(self, motivo):
        # GUARDA: fechar pelo X nao interrompe a serie em curso nem o turno da noite; so o botao Fechar tudo interrompe.
        if self.em_curso is None:
            return False
        try:
            o_que = self.em_curso()
        except Exception:
            o_que = None
        if not o_que:
            if self.adiando:
                self.log(u"pulso: o que segurava o encerramento terminou; "
                         u"encerrando tudo")
            return False
        if not self.adiando:
            self.adiando = True
            self.log(u"pulso: %s, mas %s: o programa termina isso e se "
                     u"encerra depois (o «Fechar tudo» interrompe agora)"
                     % (motivo, o_que if isinstance(o_que, str)
                        else u"ha uma serie rodando"))
            if self.ao_adiar is not None:
                try:
                    self.ao_adiar(True)
                except Exception as e:
                    self.log(u"pulso: nao consegui segurar a fila (%s)"
                             % type(e).__name__)
        return True

    def _cancelar_adiamento(self):
        self.adiando = False
        self.log(u"pulso: uma tela do programa voltou a responder; o "
                 u"encerramento depois da serie foi cancelado")
        if self.ao_adiar is not None:
            try:
                self.ao_adiar(False)
            except Exception:
                pass

    def _laco(self):
        while not self._parar.wait(self.intervalo_s):
            self.passo()
            if self.venceu:
                break
        if self.pedindo_acordado:
            self.acordado(False)
            self.pedindo_acordado = False

    def iniciar(self):
        self._thread = threading.Thread(target=self._laco, name="radai-pulso",
                                        daemon=True)
        self._thread.start()
        return self._thread

    def parar(self):
        self._parar.set()


class CapturaDoConsole(object):
    # GUARDA: com o motor sem janela, print e traceback de thread só chegam
    # a alguém se virarem linha de log; o destino não pode escrever de volta
    # aqui (a reentrada é engolida).
    encoding = "utf-8"
    errors = "replace"

    def __init__(self, destino, original=None):
        self._destino = destino
        self._original = original
        self._local = threading.local()

    def write(self, s):
        if not s:
            return 0
        texto = s if isinstance(s, str) else s.decode("utf-8", "replace")
        if getattr(self._local, "dentro", False):
            return len(texto)
        resto = getattr(self._local, "resto", "") + texto
        linhas = resto.split("\n")
        self._local.resto = linhas.pop()
        self._local.dentro = True
        try:
            for linha in linhas:
                if linha.strip():
                    try:
                        self._destino(linha.rstrip("\r"))
                    except Exception:
                        pass
        finally:
            self._local.dentro = False
        return len(texto)

    def flush(self):
        return None

    def isatty(self):
        return False

    def reconfigure(self, *a, **k):
        return None

    def fileno(self):
        if self._original is not None:
            return self._original.fileno()
        raise OSError("sem descritor")


def injetar(html):
    if not html or MARCA in html:
        return html
    baixa = html.lower()
    fim = baixa.rfind(u"</body>")
    if fim < 0:
        return html
    return html[:fim] + SCRIPT + html[fim:]


def montar(app, pulso):
    from fastapi import Request
    from starlette.responses import Response
    # GUARDA: depois de ler o body_iterator a resposta original não serve
    # mais; qualquer falha a partir dali tem de devolver a nova, nunca a velha.

    @app.post("/api/pulso")
    async def _bater(request: Request):
        try:
            bruto = await request.body()
        except Exception:
            bruto = b""
        aba, saindo = ler_corpo_do_pulso(bruto)
        if saindo:
            pulso.sair(aba)
        else:
            pulso.bater(aba)
        return {"radai": True, "ok": True}

    @app.get("/api/pulso")
    def _estado():
        return {"radai": True, "armado": pulso.armado(),
                "tolerancia_s": pulso.tolerancia_s,
                "silencio_s": round(pulso.silencio_s(), 1),
                "graca_s": getattr(pulso, "graca_s", GRACA_DO_FECHAR_S),
                "saida_pendente": bool(getattr(pulso, "saida_pendente",
                                               lambda: False)()),
                "avisos_de_saida": getattr(pulso, "avisos", 0),
                "pid": os.getpid()}

    # GUARDA: a página local de carregamento (file://) não lê JSON de outra
    # origem; uma imagem que carrega prova que o painel é o nosso.
    @app.get("/api/pulso/sinal")
    def _sinal():
        return Response(content=GIF_DO_SINAL, media_type="image/gif",
                        headers={"Cache-Control": "no-store"})

    @app.middleware("http")
    async def _costurar_o_pulso(request, call_next):
        resposta = await call_next(request)
        tipo = resposta.headers.get("content-type", "")
        if resposta.status_code != 200 or not tipo.startswith("text/html"):
            return resposta
        corpo = b""
        async for pedaco in resposta.body_iterator:
            corpo += pedaco if isinstance(pedaco, bytes) else pedaco.encode("utf-8")
        cabecalhos = dict((k, v) for (k, v) in resposta.headers.items()
                          if k.lower() != "content-length")
        try:
            novo = injetar(corpo.decode("utf-8")).encode("utf-8")
        except Exception:
            novo = corpo
        return Response(content=novo, status_code=resposta.status_code,
                        headers=cabecalhos)

    return app


def _processos():
    if os.name != "nt":
        return []
    import ctypes
    from ctypes import wintypes

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD),
                    ("cntUsage", wintypes.DWORD),
                    ("th32ProcessID", wintypes.DWORD),
                    ("th32DefaultHeapID", ctypes.c_size_t),
                    ("th32ModuleID", wintypes.DWORD),
                    ("cntThreads", wintypes.DWORD),
                    ("th32ParentProcessID", wintypes.DWORD),
                    ("pcPriClassBase", wintypes.LONG),
                    ("dwFlags", wintypes.DWORD),
                    ("szExeFile", wintypes.WCHAR * 260)]

    k32 = ctypes.windll.kernel32
    k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    snap = k32.CreateToolhelp32Snapshot(0x00000002, 0)
    if not snap or snap == wintypes.HANDLE(-1).value:
        return []
    saida = []
    try:
        e = PROCESSENTRY32W()
        e.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        ok = k32.Process32FirstW(snap, ctypes.byref(e))
        while ok:
            saida.append((int(e.th32ProcessID), int(e.th32ParentProcessID),
                          str(e.szExeFile)))
            ok = k32.Process32NextW(snap, ctypes.byref(e))
    finally:
        k32.CloseHandle(snap)
    return saida


def _criado_em(pid):
    if os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.windll.kernel32
        k32.OpenProcess.restype = wintypes.HANDLE
        h = k32.OpenProcess(0x1000, False, int(pid))
        if not h:
            return None
        try:
            c, s, kk, u = (wintypes.FILETIME(), wintypes.FILETIME(),
                           wintypes.FILETIME(), wintypes.FILETIME())
            if not k32.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(s),
                                       ctypes.byref(kk), ctypes.byref(u)):
                return None
            return (int(c.dwHighDateTime) << 32) | int(c.dwLowDateTime)
        finally:
            k32.CloseHandle(h)
    except Exception:
        return None


NOMES_DO_MOTOR = ("python.exe", "pythonw.exe")

POUPADOS = set()


def poupar(pid):
    try:
        POUPADOS.add(int(pid))
    except (TypeError, ValueError):
        pass


def filhos_do_motor(pid=None, processos=None, criado_em=None):
    pid = int(pid or os.getpid())
    lista = _processos() if processos is None else processos
    quando = criado_em or _criado_em
    meu = quando(pid)
    saida = []
    for (p, pai, nome) in lista:
        if pai != pid or p == pid:
            continue
        # GUARDA: o lançador que reabre o programa é filho do motor que está
        # saindo; derrubar a árvore não pode levá-lo junto.
        if p in POUPADOS:
            continue
        if str(nome).lower() not in NOMES_DO_MOTOR:
            continue
        # GUARDA: PID reaproveitado; o órfão de um processo antigo pode
        # apontar para o nosso PID como pai.
        dele = quando(p)
        if meu is not None and dele is not None and dele < meu:
            continue
        saida.append(p)
    return saida


def encerrar_filhos_do_motor(log=None, pid=None):
    log = log or (lambda m: None)
    mortos = []
    for p in filhos_do_motor(pid):
        try:
            raiz = os.environ.get("SystemRoot")
            tk = os.path.join(raiz, "System32", "taskkill.exe") if raiz else ""
            subprocess.run([tk if tk and os.path.isfile(tk) else "taskkill",
                            "/PID", str(p), "/T", "/F"],
                           capture_output=True, timeout=30)
            mortos.append(p)
        except Exception as e:
            log(u"encerrando: nao consegui encerrar o processo %s (%s)"
                % (p, type(e).__name__))
    if mortos:
        log(u"encerrando: %d processo(s) de segmentacao encerrado(s) com a "
            u"arvore" % len(mortos))
    return mortos
