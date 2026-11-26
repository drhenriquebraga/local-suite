# -*- coding: utf-8 -*-
from contextlib import contextmanager
import json
import os
import re
import subprocess
import threading
import time

TOLERANCIA_S = 180.0
INTERVALO_DA_TELA_S = 15
INTERVALO_DA_TELA_OCULTA_S = 60
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

# As abas modernas compartilham uma conexão de vida da janela e de mudanças da fila.
# O legado usa o mesmo fluxo por XHR. Fluxos abertos não têm pacotes de keepalive.
_FLUXO_JS = """
function canal(avisar) {
  var conexao=null, falhas=0, espera=0, permitido=true;
  function cortar() {
    if (!conexao) return;
    var x=conexao; conexao=null;
    x.onmessage=x.onerror=x.onloadend=x.onprogress=null;
    if(x.close) x.close(); else x.abort();
  }
  function caiu() {
    cortar();
    if(permitido && falhas<3 && !espera) {
      espera=setTimeout(function(){espera=0; abrir()},[1000,4000,16000][falhas++]);
    }
  }
  function receber(d) {
    try {avisar(JSON.parse(d)); falhas=0} catch(e) {}
  }
  function abrir() {
    if(!permitido || conexao) return;
    try {
      if(typeof EventSource!=="undefined") {
        conexao=new EventSource("/api/pulso/conexao");
        conexao.onmessage=function(e){receber(e.data)};
        conexao.onerror=caiu;
      } else {
        var x=conexao=new XMLHttpRequest(), inicio=0;
        function ler(){
          var s=x.responseText || "", fim;
          while((fim=s.indexOf("\\n\\n",inicio))>=0) {
            var linha=s.slice(inicio,fim); inicio=fim+2;
            if(linha.indexOf("data: ")===0) receber(linha.slice(6));
          }
          if(inicio>65536) {cortar(); abrir()}
        }
        x.open("GET","/api/pulso/conexao",true); x.onprogress=ler;
        x.onloadend=caiu; x.send();
      }
    } catch(e) {caiu()}
  }
  return {retomar:function(){permitido=true;if(!espera) abrir()},
    fechar:function(){permitido=false;clearTimeout(espera);espera=0;cortar()}};
}
"""
_WORKER_JS = _FLUXO_JS + """
var portas=[];
var fluxo=canal(function(tipos){
  portas.slice().forEach(function(p){try{p.postMessage(tipos)}catch(e){}});
});
onconnect=function(e){
  var p=e.ports[0]; portas.push(p);
  p.onmessage=function(m){
    if(m.data==="sair"){
      var i=portas.indexOf(p); if(i!==-1) portas.splice(i,1); p.close();
      if(!portas.length) fluxo.fechar();
    } else if(m.data==="retomar") fluxo.retomar();
  };
  p.postMessage(null); fluxo.retomar();
};
"""
SCRIPT = ('<script id="'+MARCA+'">(function(){if(window.__radaiPulso)return;'
          'window.__radaiPulso=1;'+_FLUXO_JS+"""
var worker=null, local=null, viva=true;
function emitir(tipos){
  if(!viva)return; var ev=document.createEvent("CustomEvent");
  ev.initCustomEvent("radai-estado-mudou",false,false,tipos);
  document.dispatchEvent(ev);
}
function direto(){
  if(!local)local=canal(emitir);
  local.retomar();
}
function abrir(){
  if(!viva)return;
  if(worker){worker.port.postMessage("retomar");return}
  if(local){local.retomar();return}
  try{
    if(window.SharedWorker){
      worker=new SharedWorker("/api/pulso/compartilhado.js");
      worker.port.onmessage=function(e){emitir(e.data)};
      worker.onerror=function(){if(worker){worker.port.close();worker=null}if(viva)direto()};
      worker.port.start();return;
    }
  }catch(e){worker=null}
  direto();
}
function fechar(){
  viva=false;
  if(worker){worker.port.postMessage("sair");worker.port.close();worker=null}
  if(local){local.fechar();local=null}
}
window.addEventListener("pagehide",fechar);
window.addEventListener("pageshow",function(e){if(e.persisted){viva=true;abrir()}});
document.addEventListener("visibilitychange",function(){if(!document.hidden)abrir()});
window.addEventListener("online",abrir);
abrir();
})();</script>""")


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


_SINAIS_TRAVA = threading.Lock()
_ASSINANTES = {}
_VIGILANTES = set()
_TIPOS_DE_MUDANCA = frozenset(("fila", "log", "config", "acervo", "plugins"))


@contextmanager
def observar_fila(evento):
    with _SINAIS_TRAVA:
        _VIGILANTES.add(evento)
    try:
        yield
    finally:
        with _SINAIS_TRAVA:
            _VIGILANTES.discard(evento)


def notificar_mudanca(tipo="fila"):
    """Invalidar o estado exibido sem consultar disco, rede ou GPU."""
    tipo = tipo if tipo in _TIPOS_DE_MUDANCA or tipo == "encerrar" else "*"
    with _SINAIS_TRAVA:
        if tipo in ("fila", "*"):
            for evento in _VIGILANTES:
                evento.set()
        for evento, (loop, tipos) in _ASSINANTES.items():
            agendar = not tipos
            tipos.add(tipo)
            if agendar or tipo == "encerrar":
                try:
                    if tipo == "encerrar":
                        loop.call_soon_threadsafe(evento.set)
                    else:
                        # Somente durante mudanças: agrupar progresso e linhas do log.
                        loop.call_soon_threadsafe(loop.call_later, 0.25, evento.set)
                except RuntimeError:
                    pass  # Loop encerrando; o finally da resposta remove o assinante.


class Pulso(object):
    def __init__(self, tolerancia_s, relogio=None, graca_s=None):
        self.tolerancia_s = float(tolerancia_s or 0.0)
        self.graca_s = float(graca_do_ambiente() if graca_s is None
                             else graca_s)
        self._relogio = relogio or time.monotonic
        self._trava = threading.Lock()
        self._ultimo = self._relogio()
        self._abas = {}
        self._conexoes = set()
        self.mudou = threading.Event()
        self._saida = None
        self.batidas = 0
        self.avisos = 0
        self.saidas = 0

    def conectar(self, token):
        with self._trava:
            self._conexoes.add(token)
            self._ultimo = self._relogio()
            self._saida = None
            self.batidas += 1
        self.mudou.set()

    def desconectar(self, token):
        with self._trava:
            if token not in self._conexoes:
                return
            self._conexoes.remove(token)
            if not self._conexoes:
                agora = self._relogio()
                self._ultimo = agora
                self.avisos += 1
                if not any(agora - t <= INTERVALO_DA_TELA_OCULTA_S + self.graca_s
                           for t in self._abas.values()):
                    self._saida = (None, agora)
                    self.saidas += 1
        self.mudou.set()

    def ate_proximo_prazo(self):
        with self._trava:
            if self._conexoes or self.tolerancia_s <= 0:
                return None
            agora = self._relogio()
            prazo = self._ultimo + self.tolerancia_s
            if self._saida and self.graca_s > 0:
                prazo = min(prazo, self._saida[1] + self.graca_s)
            return max(0.0, prazo - agora)

    def bater(self, aba=None):
        with self._trava:
            agora = self._relogio()
            self._ultimo = agora
            self.batidas += 1
            self.mudou.set()
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
            self.mudou.set()
            if self._conexoes:
                return False
            if aba is not None:
                self._abas.pop(aba, None)
            # GUARDA: a irmã acordada pelo canal pode pulsar ANTES de o
            # aviso desta aba chegar; o pulso recente dela vale como resposta.
            vivas = [a for (a, t) in self._abas.items()
                     if agora - t <= INTERVALO_DA_TELA_OCULTA_S + self.graca_s]
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

    def conexoes_abertas(self):
        with self._trava:
            return len(self._conexoes)

    def silencio_s(self):
        with self._trava:
            return 0.0 if self._conexoes else max(0.0, self._relogio() - self._ultimo)

    def armar(self, tolerancia_s):
        with self._trava:
            self.tolerancia_s = float(tolerancia_s or 0.0)
            self.mudou.set()
            self._ultimo = self._relogio()

    def armado(self):
        return self.tolerancia_s > 0

    def venceu(self):
        return self.armado() and self.silencio_s() >= self.tolerancia_s


TRAVA_DO_CHROMIUM = "lockfile"


VARIAVEL_TEMP_DO_USUARIO = "RADAI_TEMP_DO_USUARIO"


def perfil_da_janela(ambiente=None):
    from radai_perfil_janela import perfil_da_janela as resolver
    return resolver(ambiente)


def navegador_do_programa_aberto(perfil=None, verificar_janelas=None):
    perfil = perfil_da_janela() if perfil is None else perfil
    if not perfil or not os.path.isdir(perfil):
        return None
    if verificar_janelas is not None or os.name == "nt":
        if verificar_janelas is None:
            from radai_janela import perfil_tem_janela as verificar_janelas
        return verificar_janelas(perfil)
    return None


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
        self._janela_verificada = 0.0
        self._janela_aberta = None

    def _estado_do_navegador(self):
        agora = time.monotonic()
        if self.navegador_aberto is navegador_do_programa_aberto and agora < self._janela_verificada:
            return self._janela_aberta
        self._janela_aberta = self.navegador_aberto()
        self._janela_verificada = agora + 10
        return self._janela_aberta

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
                aberto = self._estado_do_navegador()
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
                aberto = self._estado_do_navegador()
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
        evento = self.pulso.mudou
        with _SINAIS_TRAVA:
            _VIGILANTES.add(evento)
        try:
            while not self._parar.is_set():
                evento.clear()
                prazo_anterior = self.pulso.ate_proximo_prazo()
                self.passo()
                if self.venceu or self._parar.is_set():
                    break
                prazo = self.pulso.ate_proximo_prazo()
                if prazo == 0 and prazo_anterior == 0:
                    # Sem clientes no canal, uma janela legada pode continuar
                    # aberta. A reavaliação deste caso não envolve o painel ocioso.
                    prazo = None if self.adiando else max(1.0, self.pulso.tolerancia_s)
                evento.wait(prazo)
        finally:
            with _SINAIS_TRAVA:
                _VIGILANTES.discard(evento)
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
        self.pulso.mudou.set()


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


def injetar(html, necessario=True):
    if not html or MARCA in html:
        return html
    baixa = html.lower()
    fim = baixa.rfind(u"</body>")
    if fim < 0:
        return html
    # Em modo de console não há vigilância para alimentar.
    return html[:fim] + (SCRIPT if necessario else "") + html[fim:]


def montar(app, pulso):
    from fastapi import Request
    from starlette.responses import Response
    # GUARDA: depois de ler o body_iterator a resposta original não serve
    # mais; qualquer falha a partir dali tem de devolver a nova, nunca a velha.

    from starlette.responses import StreamingResponse
    import asyncio
    import anyio

    class FluxoDaJanela(StreamingResponse):
        def __init__(self):
            self.evento = asyncio.Event()
            self.tipos = set()
            super().__init__(self.mensagens(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})

        async def mensagens(self):
            yield b"data: null\n\n"
            while True:
                await self.evento.wait()
                with _SINAIS_TRAVA:
                    pendentes = sorted(self.tipos)
                    self.tipos.clear()
                    self.evento.clear()
                if "encerrar" in pendentes:
                    return
                if pendentes:
                    yield "data: " + json.dumps(None if "*" in pendentes else pendentes) + "\n\n"

        async def __call__(self, scope, receive, send):
            with _SINAIS_TRAVA:
                cheio = len(_ASSINANTES) >= TETO_DE_ABAS
                if not cheio:
                    _ASSINANTES[self.evento] = (asyncio.get_running_loop(), self.tipos)
            if cheio:
                await Response(status_code=503)(scope, receive, send)
                return
            pulso.conectar(self.evento)
            try:
                # Também detectar desconexão quando não há mensagens para enviar.
                async with anyio.create_task_group() as grupo:
                    async def escutar():
                        await self.listen_for_disconnect(receive)
                        grupo.cancel_scope.cancel()
                    grupo.start_soon(escutar)
                    try:
                        await self.stream_response(send)
                    finally:
                        grupo.cancel_scope.cancel()
            finally:
                with _SINAIS_TRAVA:
                    _ASSINANTES.pop(self.evento, None)
                pulso.desconectar(self.evento)

    @app.get("/api/pulso/compartilhado.js")
    async def _worker_da_janela():
        return Response(_WORKER_JS, media_type="application/javascript",
                        headers={"Cache-Control": "no-store"})

    @app.get("/api/pulso/conexao")
    async def _conexao(request: Request):
        if request.headers.get("sec-fetch-site") == "cross-site":
            return Response(status_code=403)
        return FluxoDaJanela()

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
                "conexoes": pulso.conexoes_abertas(),
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
        if request.url.path == "/api/reabrir" and not pulso.armado():
            return resposta
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
_VIGIAS_POUPADOS = {}
_LOCK_VIGIAS = threading.Lock()


def poupar_enquanto_vivo(proc):
    # Conservar o handle do supervisor impede confundir o seu PID com um PID reutilizado.
    with _LOCK_VIGIAS:
        for pid in [pid for pid, anterior in _VIGIAS_POUPADOS.items() if anterior.poll() is not None]:
            del _VIGIAS_POUPADOS[pid]
        _VIGIAS_POUPADOS[proc.pid] = proc


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
    with _LOCK_VIGIAS:
        vigias = {p for p, proc in _VIGIAS_POUPADOS.items() if proc.poll() is None}
    saida = []
    for (p, pai, nome) in lista:
        if pai != pid or p == pid:
            continue
        # GUARDA: o lançador que reabre o programa é filho do motor que está
        # saindo; derrubar a árvore não pode levá-lo junto.
        if p in POUPADOS or p in vigias:
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


def _liberar_reserva_pelo_handle(caminho, token):
    # Só a ação explícita Fechar tudo entra aqui. O mesmo handle dá exclusividade
    # à leitura do dono e à exclusão. Interromper o filho antes dela deixa o marcador intacto.
    if os.name != "nt" or not token:
        return False
    import ctypes
    from ctypes import wintypes
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.CreateFileW.argtypes = [wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,
                              wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
    k.CreateFileW.restype = wintypes.HANDLE
    k.ReadFile.argtypes = [wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD),ctypes.c_void_p]
    k.SetFileInformationByHandle.argtypes = [wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
    k.CloseHandle.argtypes = [wintypes.HANDLE]
    # GENERIC_READ | DELETE, FILE_SHARE_READ, OPEN_EXISTING.
    h = k.CreateFileW(caminho,0x80010000,1,None,3,0x00200000,None)
    if h == ctypes.c_void_p(-1).value:
        return ctypes.get_last_error() in (2,3)
    try:
        buf, tamanho = ctypes.create_string_buffer(16384), wintypes.DWORD()
        if not k.ReadFile(h,buf,len(buf),ctypes.byref(tamanho),None) or tamanho.value==len(buf):
            return False
        dado = json.loads(buf.raw[:tamanho.value].decode("utf-8"))
        if not isinstance(dado,dict) or not dado.get("token"):
            return False
        if dado["token"] != token:
            return True  # a reserva original já saiu e a do outro dono permanece.
        excluir = ctypes.c_ubyte(1)  # FILE_DISPOSITION_INFO.DeleteFile
        return bool(k.SetFileInformationByHandle(h,4,ctypes.byref(excluir),ctypes.sizeof(excluir)))
    except (ValueError,UnicodeError):
        return False
    finally:
        k.CloseHandle(h)


def liberar_reservas_ao_fechar(caminhos,token,prazo=2.0):
    import sys
    try:
        filho = subprocess.Popen([sys.executable,"-B",os.path.abspath(__file__),"--soltar-reservas"],
                                 stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                                 creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        try:
            filho.communicate(json.dumps([caminhos,token]).encode("utf-8"),timeout=prazo)
        except subprocess.TimeoutExpired:
            filho.kill()
            try:
                filho.wait(timeout=.5)
            except subprocess.TimeoutExpired:
                pass
            return False
        return filho.returncode==0
    except OSError:
        return False


if __name__ == "__main__":
    import sys
    if sys.argv[1:] != ["--soltar-reservas"]:
        sys.exit(2)
    caminhos, token = json.load(sys.stdin)
    resultados = [_liberar_reserva_pelo_handle(p,token) for p in caminhos]
    sys.exit(0 if all(resultados) else 1)
