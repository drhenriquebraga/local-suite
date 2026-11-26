"""Liberação de caches de visualização compartilhados entre abas."""
from functools import wraps
import threading
import time


class CacheDoVisor:
    def __init__(self, limpar, prazo=180):
        self.limpar = limpar
        self.prazo = prazo
        self._trava = threading.RLock()
        self._donos = {}
        self._usos = 0
        self._pendente = False
        self._relogio = None
        self._ultimo = 0.

    def _agendar(self, segundos):
        if self._relogio is not None:
            return
        t = threading.Timer(segundos, self._expirar)
        t.daemon = True
        self._relogio = t
        t.start()

    def _expirar(self):
        with self._trava:
            if threading.current_thread() is not self._relogio:
                return
            self._relogio = None
            falta = self._ultimo + self.prazo - time.monotonic()
            if falta > 0 or self._usos:
                self._agendar(max(1., falta, self.prazo if self._usos else 0.))
            else:
                self._limpar()

    def _limpar(self):
        if self._relogio is not None:
            self._relogio.cancel()
            self._relogio = None
        self._pendente = False
        self.limpar()

    def abrir(self, dono):
        with self._trava:
            agora = time.monotonic()
            if len(self._donos) >= 1024:
                self._donos = {k:v for k,v in self._donos.items() if agora-v < 86400}
            if len(self._donos) >= 1024:
                return
            self._donos[dono] = agora
            self._pendente = False

    def fechar(self, dono):
        with self._trava:
            if dono not in self._donos:
                return
            del self._donos[dono]
            if not self._donos:
                if self._usos:
                    self._pendente = True
                else:
                    self._limpar()

    def usar(self, funcao):
        @wraps(funcao)
        def usar(*args, **kwargs):
            with self._trava:
                self._usos += 1
                self._ultimo = time.monotonic()
                self._agendar(self.prazo)
            try:
                return funcao(*args, **kwargs)
            finally:
                with self._trava:
                    self._usos -= 1
                    if self._pendente and not self._usos:
                        self._limpar()
        return usar

    def montar(self, app, nome):
        from fastapi import Request, Response
        @app.post("/api/cache-visor/" + nome, include_in_schema=False)
        async def sessao(request: Request):
            try:
                dados = await request.json()
                dono = dados.get("dono", "")
                if len(dono) != 32 or any(c not in "0123456789abcdef" for c in dono):
                    return Response(status_code=400)
                if dados.get("ativo") is True:
                    self.abrir(dono)
                else:
                    self.fechar(dono)
            except (ValueError, TypeError, AttributeError):
                return Response(status_code=400)
            return Response(status_code=204)


def cliente(nome):
    return """(function(){
 var dono='';
 function avisar(ativo){
  var corpo=JSON.stringify({dono:dono,ativo:ativo}),url='/api/cache-visor/NAME';
  if(!navigator.sendBeacon || !navigator.sendBeacon(url,corpo)){
   fetch(url,{method:'POST',body:corpo,keepalive:true}).catch(function(){});
  }
 }
 function abrir(){
  if(dono || typeof navigator==='undefined' || typeof crypto==='undefined' || !crypto.getRandomValues)return;
  dono=Array.from(crypto.getRandomValues(new Uint32Array(4)),function(x){return x.toString(16).padStart(8,'0')}).join('');
  avisar(true);
 }
 function fechar(){ if(dono){avisar(false);dono=''} }
 if(typeof window!=='undefined' && window.addEventListener)window.addEventListener('pagehide',fechar);
 return {abrir:abrir,fechar:fechar};
})()""".replace("NAME", nome)
