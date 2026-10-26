# -*- coding: utf-8 -*-
import os
import re
import threading
import time

CLASSE_DA_JANELA = u"Chrome_WidgetWin_1"
PASTA_DO_PERFIL = u"radai_janela"
SW_MINIMIZE = 6
SW_RESTORE = 9
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
VK_F11 = 0x7A
WS_CAPTION = 0x00C00000
GWL_STYLE = -16
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
PROCESS_COMMAND_LINE_INFORMATION = 60
MONITOR_DEFAULTTONEAREST = 2
TETO_DA_PROCURA_S = 2.0
PASSO_DA_PROCURA_S = 0.1
FORMATO_DA_FICHA = re.compile(r"^[a-z0-9]{12,40}$")

FRASE_SEM_JANELA = (u"Não achei a janela do app: ela só é achada quando foi "
                    u"aberta pelo atalho do programa.")
FRASE_SO_WINDOWS = u"Minimizar só existe no Windows."
LOG_PELO_TITULO = (u"[janela] achada pelo titulo: a ficha fecha o titulo da "
                   u"janela em modo de aplicativo")
LOG_PELA_LINHA = (u"[janela] achada pela linha de comando do navegador: o "
                  u"titulo nao bastou")

_TRAVA = threading.Lock()
_JANELAS = {}
_CTX = {"log": None}


def _log(m):
    f = _CTX.get("log")
    if f:
        try:
            f(m)
        except Exception:
            pass


class Plataforma(object):

    def __init__(self):
        import ctypes
        from ctypes import wintypes
        self.ctypes = ctypes
        self.wintypes = wintypes
        u = ctypes.WinDLL("user32", use_last_error=True)
        self.enum_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND,
                                            wintypes.LPARAM)
        u.EnumWindows.argtypes = [self.enum_proc, wintypes.LPARAM]
        u.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR,
                                     ctypes.c_int]
        u.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR,
                                    ctypes.c_int]
        u.GetWindowThreadProcessId.argtypes = [
            wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        u.IsWindow.argtypes = [wintypes.HWND]
        u.IsWindowVisible.argtypes = [wintypes.HWND]
        u.IsIconic.argtypes = [wintypes.HWND]
        u.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        u.SetForegroundWindow.argtypes = [wintypes.HWND]
        u.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT,
                                   wintypes.WPARAM, wintypes.LPARAM]
        u.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
        u.GetWindowLongW.restype = ctypes.c_long

        class _InfoDoMonitor(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                        ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]
        self.InfoDoMonitor = _InfoDoMonitor
        u.GetWindowRect.argtypes = [wintypes.HWND,
                                    ctypes.POINTER(wintypes.RECT)]
        u.MonitorFromWindow.restype = wintypes.HANDLE
        u.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
        u.GetMonitorInfoW.argtypes = [wintypes.HANDLE,
                                      ctypes.POINTER(_InfoDoMonitor)]
        self.u = u
        k = ctypes.WinDLL("kernel32", use_last_error=True)
        k.OpenProcess.restype = wintypes.HANDLE
        k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k.CloseHandle.argtypes = [wintypes.HANDLE]
        self.k = k
        self.n = None

    def _ntdll(self):
        if self.n is None:
            ctypes, wintypes = self.ctypes, self.wintypes
            n = ctypes.WinDLL("ntdll")
            n.NtQueryInformationProcess.restype = ctypes.c_long
            n.NtQueryInformationProcess.argtypes = [
                wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, ctypes.c_ulong,
                ctypes.POINTER(ctypes.c_ulong)]
            self.n = n
        return self.n

    def janelas(self):
        achadas = []

        def cb(h, _):
            achadas.append(int(h or 0))
            return True
        self.u.EnumWindows(self.enum_proc(cb), 0)
        return [h for h in achadas if h]

    def titulo(self, h):
        b = self.ctypes.create_unicode_buffer(512)
        self.u.GetWindowTextW(h, b, 512)
        return b.value

    def classe(self, h):
        b = self.ctypes.create_unicode_buffer(256)
        self.u.GetClassNameW(h, b, 256)
        return b.value

    def pid(self, h):
        p = self.wintypes.DWORD()
        self.u.GetWindowThreadProcessId(h, self.ctypes.byref(p))
        return int(p.value)

    def existe(self, h):
        return bool(self.u.IsWindow(h))

    def visivel(self, h):
        return bool(self.u.IsWindowVisible(h))

    def minimizada(self, h):
        return bool(self.u.IsIconic(h))

    def tem_barra(self, h):
        return bool((self.u.GetWindowLongW(h, GWL_STYLE) & 0xFFFFFFFF)
                    & WS_CAPTION)

    def mostrar(self, h, modo):
        self.u.ShowWindow(h, int(modo))
        return True

    def trazer_para_frente(self, h):
        return bool(self.u.SetForegroundWindow(h))

    def tecla_f11(self, h):
        self.u.PostMessageW(h, WM_KEYDOWN, VK_F11, 0x00570001)
        self.u.PostMessageW(h, WM_KEYUP, VK_F11, 0xC0570001)
        return True

    def retangulo(self, h):
        r = self.wintypes.RECT()
        if not self.u.GetWindowRect(h, self.ctypes.byref(r)):
            return None
        return (r.left, r.top, r.right, r.bottom)

    def monitor(self, h):
        m = self.u.MonitorFromWindow(h, MONITOR_DEFAULTTONEAREST)
        if not m:
            return None
        info = self.InfoDoMonitor()
        info.cbSize = self.ctypes.sizeof(self.InfoDoMonitor)
        if not self.u.GetMonitorInfoW(m, self.ctypes.byref(info)):
            return None
        r = info.rcMonitor
        return (r.left, r.top, r.right, r.bottom)

    def linha_de_comando(self, pid):
        ctypes = self.ctypes
        h = self.k.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False,
                               int(pid))
        if not h:
            return u""
        try:
            tamanho = 65536
            buf = ctypes.create_string_buffer(tamanho)
            n = ctypes.c_ulong(0)
            st = self._ntdll().NtQueryInformationProcess(
                h, PROCESS_COMMAND_LINE_INFORMATION, buf, tamanho,
                ctypes.byref(n))
            if st != 0:
                return u""

            class _UnicodeString(ctypes.Structure):
                _fields_ = [("Length", ctypes.c_ushort),
                            ("MaximumLength", ctypes.c_ushort),
                            ("Buffer", ctypes.c_void_p)]
            us = _UnicodeString.from_buffer(buf)
            if not us.Buffer or not us.Length:
                return u""
            return ctypes.wstring_at(us.Buffer, us.Length // 2)
        finally:
            self.k.CloseHandle(h)


_PLATAFORMA = []


def plataforma():
    if os.name != "nt":
        return None
    if not _PLATAFORMA:
        try:
            _PLATAFORMA.append(Plataforma())
        except Exception:
            _PLATAFORMA.append(None)
    return _PLATAFORMA[0]


def perfil_da_linha(linha):
    m = re.search(r'--user-data-dir=(?:"([^"]*)"|(\S+))', linha or u"")
    if not m:
        return u""
    return (m.group(1) or m.group(2) or u"").strip()


def e_do_perfil_do_app(linha):
    valor = perfil_da_linha(linha).rstrip(u"\\/")
    return bool(valor) and (re.split(r"[\\/]", valor)[-1].lower()
                            == PASTA_DO_PERFIL)


def ficha_valida(ficha):
    return bool(FORMATO_DA_FICHA.match(str(ficha or u"")))


def janela_do_app(h, pf):
    # GUARDA: so a janela do perfil proprio do programa; minimizar o
    # navegador pessoal da pessoa inteiro seria surpresa.
    try:
        if not pf.existe(h) or pf.classe(h) != CLASSE_DA_JANELA:
            return False
        return e_do_perfil_do_app(pf.linha_de_comando(pf.pid(h)))
    except Exception:
        return False


def pelo_titulo(h, titulo, ficha, pf):
    # GUARDA: pelo titulo so a janela em modo de aplicativo, em que o titulo
    # da janela e o da pagina e termina na ficha; a janela de abas acrescenta
    # o nome do navegador e so passa pelo perfil conferido na linha de comando.
    return (titulo.rstrip().endswith(u"[%s]" % ficha) and pf.existe(h)
            and pf.classe(h) == CLASSE_DA_JANELA)


def _uma_volta(ficha, pf):
    resto = []
    for h in pf.janelas():
        try:
            t = pf.titulo(h)
            if ficha not in t:
                continue
            if pelo_titulo(h, t, ficha, pf):
                return h, LOG_PELO_TITULO
            resto.append(h)
        except Exception:
            continue
    for h in resto:
        if janela_do_app(h, pf):
            return h, LOG_PELA_LINHA
    return 0, u""


def achar(ficha, pf=None, teto_s=TETO_DA_PROCURA_S, relogio=time.monotonic,
          dormir=time.sleep):
    pf = pf if pf is not None else plataforma()
    if pf is None or not ficha_valida(ficha):
        return 0
    fim = relogio() + float(teto_s)
    while True:
        h, caminho = _uma_volta(ficha, pf)
        if h:
            _log(caminho)
            return h
        if relogio() >= fim:
            return 0
        dormir(PASSO_DA_PROCURA_S)


def ainda_e_a_mesma(h, dados, pf):
    # GUARDA: o handle guardado se reconfere pelo PID do dono e pela classe;
    # handle reaproveitado por janela de outro processo sai da lista.
    try:
        return (pf.existe(h) and pf.classe(h) == CLASSE_DA_JANELA
                and pf.pid(h) == (dados or {}).get("pid"))
    except Exception:
        return False


def guardadas(pf=None):
    pf = pf if pf is not None else plataforma()
    if pf is None:
        return []
    with _TRAVA:
        hs = dict(_JANELAS)
    vivas = [h for h, d in hs.items() if ainda_e_a_mesma(h, d, pf)]
    with _TRAVA:
        for h in hs:
            if h not in vivas:
                _JANELAS.pop(h, None)
    return vivas


def cobre_o_monitor(janela, monitor):
    if not janela or not monitor or monitor[2] <= monitor[0] \
            or monitor[3] <= monitor[1]:
        return False
    return (janela[0] <= monitor[0] and janela[1] <= monitor[1]
            and janela[2] >= monitor[2] and janela[3] >= monitor[3])


def ja_cobre_o_monitor(h, pf):
    try:
        return cobre_o_monitor(pf.retangulo(h), pf.monitor(h))
    except Exception:
        return False


def garantir_tela_cheia(h, pf):
    # GUARDA: a segunda janela de um perfil ja aberto ignora o
    # --start-fullscreen; o F11 vai uma vez por janela, e quem saiu da tela
    # cheia pelo F11 nao volta a ser posto nela. O F11 liga e desliga: a
    # janela que ja cobre o monitor inteiro esta em tela cheia e nao o recebe.
    if pf.minimizada(h) or not pf.tem_barra(h) or ja_cobre_o_monitor(h, pf):
        return False
    # GUARDA: o Edge ignora o F11 postado em janela que nao esta na frente.
    try:
        pf.trazer_para_frente(h)
    except Exception:
        pass
    pf.tecla_f11(h)
    return True


def registrar(ficha, pf=None, **kw):
    pf = pf if pf is not None else plataforma()
    if pf is None:
        return {"ok": False, "motivo": FRASE_SO_WINDOWS}
    h = achar(ficha, pf, **kw)
    if not h:
        return {"ok": False, "motivo": FRASE_SEM_JANELA}
    with _TRAVA:
        nova = h not in _JANELAS
        if nova:
            _JANELAS[h] = {"desde": time.time(), "pid": pf.pid(h)}
    f11 = garantir_tela_cheia(h, pf) if nova else False
    return {"ok": True, "nova": nova, "tela_cheia_pedida": f11}


def _alvos(ficha, pf, **kw):
    if ficha:
        h = achar(ficha, pf, **kw)
        if h:
            with _TRAVA:
                _JANELAS.setdefault(h, {"desde": time.time(),
                                        "pid": pf.pid(h)})
            return [h]
        return []
    return guardadas(pf)


def minimizar(ficha=None, pf=None, **kw):
    pf = pf if pf is not None else plataforma()
    if pf is None:
        return {"ok": False, "motivo": FRASE_SO_WINDOWS}
    alvos = _alvos(ficha, pf, **kw)
    if not alvos:
        return {"ok": False, "motivo": FRASE_SEM_JANELA}
    for h in alvos:
        pf.mostrar(h, SW_MINIMIZE)
    return {"ok": True, "janelas": len(alvos)}


def restaurar(ficha=None, pf=None, **kw):
    pf = pf if pf is not None else plataforma()
    if pf is None:
        return {"ok": False, "motivo": FRASE_SO_WINDOWS}
    alvos = _alvos(ficha, pf, **kw)
    if not alvos:
        return {"ok": False, "motivo": FRASE_SEM_JANELA}
    for h in alvos:
        if pf.minimizada(h):
            pf.mostrar(h, SW_RESTORE)
        try:
            pf.trazer_para_frente(h)
        except Exception:
            pass
    return {"ok": True, "janelas": len(alvos)}


def _ficha_do_corpo(corpo):
    f = (corpo or {}).get("ficha") if isinstance(corpo, dict) else None
    return f if ficha_valida(f) else None


def montar(app, log=None):
    from fastapi import Request
    from starlette.concurrency import run_in_threadpool

    _CTX["log"] = log

    async def _corpo(request):
        try:
            c = await request.json()
        except Exception:
            c = {}
        return c if isinstance(c, dict) else {}

    @app.post("/api/janela/estado")
    def _estado():
        return {"pid": os.getpid()}

    @app.post("/api/janela/registrar")
    async def _registrar(request: Request):
        f = _ficha_do_corpo(await _corpo(request))
        if not f:
            return {"ok": False, "motivo": u"ficha invalida"}
        return await run_in_threadpool(registrar, f)

    @app.post("/api/janela/minimizar")
    async def _minimizar(request: Request):
        f = _ficha_do_corpo(await _corpo(request))
        return await run_in_threadpool(minimizar, f)

    @app.post("/api/janela/restaurar")
    async def _restaurar(request: Request):
        f = _ficha_do_corpo(await _corpo(request))
        return await run_in_threadpool(restaurar, f)

    return app


MARCA = u"radai-janela-js"

JS = u"""<script id="radai-janela-js">
(function(){
 if(window.radaiJanelaMinimizar) return;
 var ROT = {registrar:'/api/janela/registrar', minimizar:'/api/janela/minimizar',
            restaurar:'/api/janela/restaurar', estado:'/api/janela/estado'};
 function ficha(){
  var c = 'abcdefghijklmnopqrstuvwxyz0123456789', s = 'rj';
  for(var i = 0; i < 18; i++) s += c.charAt(Math.floor(Math.random() * c.length));
  return s;
 }
 // GUARDA: o motor acha a janela pelo titulo; o tradutor reescreve o titulo
 // de tempos em tempos, e a ficha e reposta ate a resposta chegar.
 function comFicha(rota){
  var f = ficha(), t0 = document.title, marca = ' [' + f + ']';
  function por(){ if(document.title.indexOf(f) < 0) document.title = document.title + marca }
  por();
  var laco = setInterval(por, 100);
  function fim(d){
   clearInterval(laco);
   if(document.title.indexOf(f) >= 0) document.title = document.title.replace(marca, '');
   return d || {ok:false};
  }
  return fetch(rota, {method:'POST', headers:{'Content-Type':'application/json'},
                      body: JSON.stringify({ficha: f})})
   .then(function(r){ return r.ok ? r.json() : {ok:false} })
   .then(fim, function(){ return fim({ok:false}) });
 }
 window.radaiJanelaMinimizar = function(){ return comFicha(ROT.minimizar) };
 window.radaiJanelaRestaurar = function(){ return comFicha(ROT.restaurar) };
 function avisar(ok){
  window.radaiJanelaDoApp = !!ok;
  try{ document.dispatchEvent(new CustomEvent('radai-janela', {detail: {ok: !!ok}})) }catch(e){}
 }
 function registrar(){
  fetch(ROT.estado, {method:'POST', headers:{'Content-Type':'application/json'}, body:'{}'})
   .then(function(r){ return r.ok ? r.json() : null })
   .then(function(d){
    if(!d || !d.pid){ avisar(false); return }
    var k = 'radai_janela_motor', feito = '';
    try{ feito = sessionStorage.getItem(k) || '' }catch(e){}
    if(feito === String(d.pid)){ avisar(true); return }
    comFicha(ROT.registrar).then(function(r){
     if(r && r.ok){ try{ sessionStorage.setItem(k, String(d.pid)) }catch(e){} }
     avisar(r && r.ok);
    });
   }).catch(function(){ avisar(false) });
 }
 function depois(){ setTimeout(registrar, 700) }
 if(document.readyState === 'complete') depois();
 else window.addEventListener('load', depois);
})();
</script>"""

PARA_A_CASCA = JS
