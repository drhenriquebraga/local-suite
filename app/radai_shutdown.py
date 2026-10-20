# -*- coding: utf-8 -*-
import json
import os
import threading

MARCA = "radai-encerrar-css"
ROTA_ENCERRAR = "/api/encerrar"
ROTA_REABRIR = "/api/reabrir"
TETO_DO_ENCERRAMENTO_MS = 60000
TETO_DA_REABERTURA_MS = 300000
CODIGOS_DA_REABERTURA = (("caiu", "R1"), ("mudo", "R2"), ("antigo", "R3"),
                         ("outro", "R4"))

CSS = u"""
<style id="radai-encerrar-css">
.rx-fechar{display:inline-flex;align-items:center;gap:7px;height:32px;
padding:0 13px;border-radius:var(--r-lg,8px);box-sizing:border-box;
background:var(--fundo-perigo,#160a08);border:1px solid var(--perigo,#E96A5C);
color:var(--perigo,#E96A5C);font:600 12px/1 var(--font-display,inherit);
letter-spacing:.07em;text-transform:uppercase;white-space:nowrap;
cursor:pointer;flex:0 0 auto;
transition:background-color .14s ease,color .14s ease}
.rx-fechar .ui-ic{width:15px;height:15px;margin:0}
.rx-fechar .ui-ic + *{margin-inline-start:0}
.rx-fechar:hover{background:var(--perigo,#E96A5C);color:var(--bg-1,#0a1120)}
.rx-fechar:active{transform:translateY(1px)}
.rx-fechar:focus-visible{outline:2px solid var(--perigo,#E96A5C);outline-offset:2px}
.rc-encerrar{display:inline-flex;align-items:center}
@media (max-width:760px){.rx-fechar .rx-fechar-txt{display:none}
 .rx-fechar{padding:0 9px}}
.rx-veu{display:none;position:fixed;inset:0;z-index:4000;
background:rgba(4,8,16,.72);backdrop-filter:blur(2px);
align-items:center;justify-content:center;padding:24px}
.rx-veu.on{display:flex}
.rx-cx{background:var(--panel,#0c1322);border:1px solid var(--line-strong,#2a3a55);border-radius:12px;
max-width:560px;width:100%;padding:22px 24px;color:var(--text,#e6edf7);
box-shadow:var(--sombra,0 20px 60px rgba(0,0,0,.6));font-size:13.5px;line-height:1.6}
.rx-veu.on .rx-cx{animation:rxSobe .22s cubic-bezier(.22,1,.36,1) both}
@keyframes rxSobe{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
@media (prefers-reduced-motion:reduce){.rx-veu.on .rx-cx{animation:none}
 .rx-fechar{transition:none}}
.rx-cx h3{margin:0 0 4px;font-size:17px}
.rx-sub{color:var(--text-muted,#a3b1c6);font-size:12.5px}
.rx-agora{margin:12px 0 4px;padding:10px 12px;border-radius:8px;font-size:12.5px;
border:1px solid var(--borda-aviso,#4a3a18);border-inline-start:3px solid var(--aviso,#E8A33D);
background:var(--fundo-aviso,#1c1608);color:var(--text,#e6edf7)}
.rx-agora.livre{border-color:var(--borda-ok,#24422f);border-inline-start-color:var(--success,#5BC57F);
background:var(--fundo-ok,#0d1a12)}
.rx-op{display:block;width:100%;text-align:start;margin-top:10px;
background:var(--panel,#0c1322);border:1px solid var(--line-strong,#2a3a55);border-radius:8px;
padding:11px 13px;color:var(--text,#e6edf7);cursor:pointer;font-family:inherit;font-size:13px;
transition:background-color .12s ease,border-color .12s ease}
.rx-op:hover{background:var(--panel-2,#0f1729);border-color:var(--accent,#4DA3FF)}
.rx-op:focus-visible{outline:2px solid var(--accent,#4DA3FF);outline-offset:2px}
.rx-op b{display:block;font-size:13.5px;margin-bottom:2px}
.rx-op span{color:var(--text-muted,#a3b1c6);font-size:12px;line-height:1.5}
.rx-op.perigo{border-color:var(--borda-perigo,#552b23)}
.rx-op.perigo b{color:var(--perigo,#E96A5C)}
.rx-op.perigo:hover{background:var(--fundo-perigo,#160a08);border-color:var(--perigo,#E96A5C)}
.rx-op:disabled{cursor:progress;opacity:.8}
.rx-fim{text-align:center;padding:40px 20px;color:var(--text-muted,#a3b1c6);font-size:14px}
.rx-fim b{display:block;color:var(--text,#e6edf7);font-size:18px;margin-bottom:8px}
.rx-fim code{font-family:var(--mono,monospace);color:var(--text,#e6edf7)}
.rx-nota{margin-top:12px}
</style>
"""

# GUARDA: uma frase por literal; o tradutor casa a frase inteira, e frase
# montada por concatenação nunca acha a chave.
JS_DO_ESTADO = u"""
 var INTERROMPE = 'Fechar tudo interrompe esse trabalho: a série volta para a fila e outra máquina pode pegá-la. Nenhum contorno pela metade é gravado.';
 function estado(cx, frases){
  var h = frases.map(function(f){
   return '<span data-radai-frase></span>' }).join(' ');
  if(window.uiHTML) window.uiHTML(cx, h); else cx.innerHTML = h;
  var ss = cx.querySelectorAll('span');
  for(var i = 0; i < ss.length; i++) ss[i].textContent = frases[i];
  try{ cx.removeAttribute('data-radai-t') }catch(e){}
  try{ if(window.radaiRetraduzir) window.radaiRetraduzir() }catch(e){}
 }
 function descrever(cx){
  cx.className = 'rx-agora';
  estado(cx, ['verificando o que está em andamento…']);
  fetch('/api/status').then(function(r){ return r.json() }).then(function(s){
   var oc = s && s.ocupado, quem = oc && oc.quem;
   var desde = String((oc && oc.desde) || (s && s.current && s.current.desde) || '?');
   if(quem){
    estado(cx, [((quem === 'lote')
                 ? 'O «Rodar agora» está segmentando agora (desde %s).'
                 : 'O vigia está contornando uma série agora (desde %s).'
                ).replace('%s', desde), INTERROMPE]);
   } else if(s && s.current){
    estado(cx, ['Uma série está sendo contornada agora (desde %s).'
                .replace('%s', desde), INTERROMPE]);
   } else if(s && s.overnight){
    estado(cx, ['O turno da noite está aberto nesta estação: encerrar o programa encerra o turno.']);
   } else if(s && s.turno_agendado){
    estado(cx, ['O turno da noite está agendado na fila desta estação.']);
   } else if(s && ('ocupado' in s)){
    cx.className = 'rx-agora livre';
    estado(cx, ['Nenhuma série está sendo contornada neste momento.']);
   } else {
    estado(cx, ['Não consegui confirmar o que está em andamento (esta estação tem uma versão anterior do vigia). Se houver um lote rodando, Fechar tudo o interrompe.']);
   }
  }).catch(function(){
   estado(cx, ['Não consegui conferir o que está em andamento.']);
  });
 }
 function dizer(el, t){
  if(window.uiTexto) window.uiTexto(el, t); else el.textContent = t;
  try{ if(window.radaiRetraduzir) window.radaiRetraduzir() }catch(e){}
 }
 function agora(){ return new Date().getTime() }
 function perguntarAoMotor(feito){
  var ctl = window.AbortController ? new AbortController() : null;
  var t = ctl ? setTimeout(function(){ ctl.abort() }, 3000) : null;
  fetch('/api/pulso', {cache: 'no-store', signal: ctl ? ctl.signal : undefined})
   .then(function(r){
     clearTimeout(t);
     return r.json().then(function(d){ feito('vivo', d) },
                          function(){ feito('vivo', null) });
    },
    function(e){ clearTimeout(t);
                 feito((e && e.name === 'AbortError') ? 'mudo' : 'caiu', null) });
 }
"""

_HTML_MODELO = u"""
<div class="rx-veu" id="rx-veu">
 <div class="rx-cx" role="dialog" aria-modal="true" aria-labelledby="rx-titulo">
  <h3 id="rx-titulo">Fechar o Radioterapia.AI Local Suite</h3>
  <div class="rx-sub">Fechar o programa encerra o motor e a fila desta estação.</div>
  <div class="rx-agora" id="rx-agora">verificando o que está em andamento…</div>

  <button class="rx-op perigo" id="rx-tudo" type="button">
   <b>Fechar tudo</b>
   <span>O motor para e a fila também. Nada continua rodando.</span>
  </button>

  <button class="rx-op" id="rx-cancelar" type="button">
   <b>Cancelar</b>
   <span>Volta para a tela. Nada é alterado.</span>
  </button>
  <div class="rx-sub rx-nota">Fechar a janela do navegador também encerra tudo, mas só depois que a série em curso termina; com o turno da noite aberto, depois do turno; com o turno agendado e o «Rodar agora» andando até ele, o lote termina o que espera, roda o turno inteiro, e só então o programa se encerra.</div>
 </div>
</div>
<script id="radai-encerrar-js">
(function(){
 var veu = document.getElementById('rx-veu');
 if(!veu) return;
@JS_DO_ESTADO@
 function montarBotao(){
  var canto = document.querySelector('[data-radai-encerrar]');
  if(!canto || canto.querySelector('.rx-fechar')) return;
  var b = document.createElement('button');
  b.type = 'button';
  b.className = 'rx-fechar';
  b.title = 'Fechar o programa: o vigia e o motor rodam fora desta aba';
  b.innerHTML = ICONE;
  var t = document.createElement('span');
  t.className = 'rx-fechar-txt';
  t.textContent = 'Fechar app';
  b.appendChild(t);
  b.addEventListener('click', abrir);
  canto.appendChild(b);
 }
 var ICONE = '@ICO_POWER@';
 var ultimoFoco = null;

 function abrir(){
  ultimoFoco = document.activeElement;
  veu.classList.add('on');
  try{ document.getElementById('rx-cancelar').focus() }catch(e){}
  descrever(document.getElementById('rx-agora'));
 }

 function prender(e){
  if(e.key !== 'Tab' || !veu.classList.contains('on')) return;
  var caixa = veu.querySelector('.rx-cx');
  if(window.uiPrenderFoco){ window.uiPrenderFoco(caixa, e); return }
  var fs = Array.prototype.filter.call(caixa.querySelectorAll('button'),
    function(x){ return !x.disabled });
  if(!fs.length) return;
  var i = fs.indexOf(document.activeElement);
  if(e.shiftKey){ if(i <= 0){ e.preventDefault(); fs[fs.length - 1].focus() } }
  else if(i < 0 || i === fs.length - 1){ e.preventDefault(); fs[0].focus() }
 }

 function fechar(){
  if(!veu.classList.contains('on')) return;
  veu.classList.remove('on');
  try{ if(ultimoFoco && ultimoFoco.focus) ultimoFoco.focus() }catch(e){}
 }

 function despedir(titulo, texto){
  document.body.innerHTML = '<div class="rx-fim"><b data-radai-frase></b>'
    + '<span data-radai-frase></span></div>';
  document.querySelector('.rx-fim b').textContent = titulo;
  document.querySelector('.rx-fim span').textContent = texto;
  try{ if(window.radaiRetraduzir) window.radaiRetraduzir() }catch(e){}
 }

 document.getElementById('rx-cancelar').addEventListener('click', fechar);
 veu.addEventListener('click', function(e){ if(e.target === veu) fechar() });
 document.addEventListener('keydown', function(e){
  if(e.key === 'Escape') fechar();
  else prender(e);
 });

 document.getElementById('rx-tudo').addEventListener('click', function(){
  var b = this;
  b.disabled = true;
  try{ document.getElementById('rx-cancelar').disabled = true }catch(e){}
  dizer(b.querySelector('b'), 'Encerrando…');
  var fim = agora() + @TETO_DO_ENCERRAMENTO_MS@;
  // GUARDA: a aba só fecha depois que a porta deixa de responder; fechar
  // antes deixaria o motor vivo sem ninguém para dizer que ele não parou.
  function sondar(){
   perguntarAoMotor(function(como){
    if(como === 'caiu'){ parou(); return }
    if(agora() > fim){
     despedir('O motor ainda está encerrando.',
       'Ele termina sozinho em instantes. Se o programa continuar no Gerenciador de Tarefas, abra o atalho "Radioterapia.ai Local Suite": a abertura encerra o que tiver sobrado.');
     return;
    }
    setTimeout(sondar, 500);
   });
  }
  function parou(){
   try { window.close() } catch(e) {}
   setTimeout(function(){
    despedir('Radioterapia.AI Local Suite encerrado.',
      'O motor parou. Pode fechar esta aba. Para abrir de novo, use o atalho "Radioterapia.ai Local Suite".');
   }, 150);
  }
  fetch('/api/encerrar', {method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({modo:'tudo'})})
   .then(function(){ setTimeout(sondar, 300) },
         function(){ setTimeout(sondar, 300) });
 });

 if(document.readyState === 'loading')
  document.addEventListener('DOMContentLoaded', montarBotao);
 else montarBotao();
})();
</script>
"""

PAGINA_REABRIR = u"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Radioterapia.AI Local Suite</title>
@CSS@
<style id="radai-reabrir-css">
body.rr-corpo{margin:0;min-height:100vh;display:grid;place-items:center;
 padding:24px;box-sizing:border-box;background:var(--bg-1,#0a1120);
 color:var(--text,#e6edf7);font:400 14px/1.5 var(--font-display,system-ui,'Segoe UI',Arial,sans-serif)}
.rr-cx{animation:rxSobe .22s cubic-bezier(.22,1,.36,1) both}
.rr-cx h1{margin:0 0 4px;font-size:18px}
.rr-espera{margin-top:14px;color:var(--text-muted,#a3b1c6)}
.rr-espera[hidden],.rr-nota[hidden]{display:none}
@media (prefers-reduced-motion:reduce){.rr-cx{animation:none}}
</style>
</head>
<body class="rr-corpo">
<main class="rx-cx rr-cx" role="dialog" aria-labelledby="rr-titulo">
 <h1 id="rr-titulo">O Radioterapia.AI Local Suite já está aberto</h1>
 <div class="rx-sub">Abrir de novo encerra a sessão aberta.</div>
 <div class="rx-agora" id="rr-agora">verificando o que está em andamento…</div>
 <button class="rx-op" id="rr-continuar" type="button">
  <b>Continuar na sessão aberta</b>
  <span>Volta para o programa que já está rodando. Nada é interrompido.</span>
 </button>
 <button class="rx-op perigo" id="rr-reabrir" type="button">
  <b>Encerrar e abrir de novo</b>
  <span>O motor para e a fila também; o programa abre outra vez em seguida.</span>
 </button>
 <div class="rr-espera" id="rr-espera" role="status" aria-live="polite" hidden></div>
 <div class="rx-sub rx-nota rr-nota" id="rr-nota" hidden></div>
</main>
<script id="radai-reabrir-js">
(function(){
@JS_DO_ESTADO@
 var espera = document.getElementById('rr-espera');
 var nota = document.getElementById('rr-nota');
 var continuar = document.getElementById('rr-continuar');
 var reabrir = document.getElementById('rr-reabrir');
 var pid0 = null;
 var CODIGOS = @CODIGOS_DA_REABERTURA@;
 descrever(document.getElementById('rr-agora'));
 perguntarAoMotor(function(como, d){ if(d && d.pid) pid0 = d.pid });
 try{ continuar.focus() }catch(e){}
 continuar.addEventListener('click', function(){ location.replace('/') });

 function esperar(texto){
  espera.hidden = false;
  dizer(espera, texto);
 }

 reabrir.addEventListener('click', function(){
  reabrir.disabled = true;
  continuar.disabled = true;
  dizer(reabrir.querySelector('b'), 'Encerrando…');
  esperar('Encerrando a sessão aberta…');
  var fim = agora() + @TETO_DA_REABERTURA_MS@;
  var caiu = false;
  var ultimo = 'mudo';
  // GUARDA: o motor novo se reconhece pelo PID diferente; o antigo ainda
  // responde enquanto espera a série em curso parar.
  function sondar(){
   perguntarAoMotor(function(como, d){
    if(como === 'caiu' && !caiu){ caiu = true; esperar('Abrindo de novo…') }
    var novo = como === 'vivo' && d && d.radai === true && d.pid
               && (pid0 ? d.pid !== pid0 : caiu);
    if(novo){ location.replace('/'); return }
    ultimo = (como !== 'vivo') ? como
             : ((d && d.radai === true) ? 'antigo' : 'outro');
    if(agora() > fim){
     espera.hidden = true;
     nota.hidden = false;
     dizer(nota, 'O programa não voltou a abrir em 5 minutos (código %s). Abra pelo atalho "Radioterapia.ai Local Suite".'
                 .replace('%s', CODIGOS[ultimo] || '?'));
     return;
    }
    setTimeout(sondar, 500);
   });
  }
  fetch('/api/encerrar', {method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({modo:'tudo', reabrir:true})})
   .then(function(){ setTimeout(sondar, 500) },
         function(){ setTimeout(sondar, 500) });
 });
})();
</script>
</body>
</html>
"""


def _icone():
    try:
        import radai_ui
        return radai_ui.icone(u"power") or u""
    except Exception:
        return u""


def _com_js(modelo):
    return (modelo.replace(u"@JS_DO_ESTADO@", JS_DO_ESTADO)
            .replace(u"@TETO_DO_ENCERRAMENTO_MS@", str(TETO_DO_ENCERRAMENTO_MS))
            .replace(u"@TETO_DA_REABERTURA_MS@", str(TETO_DA_REABERTURA_MS))
            .replace(u"@CODIGOS_DA_REABERTURA@",
                     json.dumps(dict(CODIGOS_DA_REABERTURA))))


HTML = _com_js(_HTML_MODELO)


def aplicar(pagina):
    if not pagina or MARCA in pagina:
        return pagina
    baixa = pagina.lower()
    fim_head = baixa.find(u"</head>")
    if fim_head < 0:
        return pagina
    fim_corpo = baixa.rfind(u"</body>")
    if fim_corpo < 0:
        return pagina
    html = HTML.replace(u"@ICO_POWER@", _icone().replace(u"'", u'"'))
    saida = pagina[:fim_head] + CSS + pagina[fim_head:]
    corte = fim_corpo + len(CSS)
    return saida[:corte] + html + saida[corte:]


def pagina_de_reabrir():
    pagina = _com_js(PAGINA_REABRIR).replace(u"@CSS@", CSS)
    try:
        import radai_ui
        pagina = radai_ui.aplicar(pagina)
    except Exception:
        pass
    try:
        import radai_languages
        pagina = radai_languages.aplicar(pagina)
    except Exception:
        pass
    return pagina


def _sucessor_padrao(porta):
    import radai_lancador
    return radai_lancador.subir_sucessor(porta, os.getpid())


def montar(app, ao_encerrar, sucessor=None):
    from fastapi import Request
    from fastapi.responses import HTMLResponse
    sucessor = sucessor or _sucessor_padrao

    @app.post("/api/encerrar")
    async def _encerrar(request: Request):
        try:
            corpo = await request.json()
        except Exception:
            corpo = {}
        corpo = corpo if isinstance(corpo, dict) else {}
        modo = corpo.get("modo", "tudo")
        if modo != "tudo":
            return {"ok": True, "encerrando": False}
        reabrir = corpo.get("reabrir") is True
        porta = request.url.port

        def _fim():
            ao_encerrar()
            if reabrir and porta:
                try:
                    sucessor(int(porta))
                except Exception:
                    pass
        # GUARDA: o encerramento espera a série em curso parar (segundos);
        # dentro da rota ele seguraria o laço de eventos do servidor.
        # GUARDA: o sucessor nasce DEPOIS de o motor derrubar os filhos, e a
        # thread não é daemon para o processo não sair antes de lançá-lo.
        threading.Thread(target=_fim, name="radai-encerrar",
                         daemon=not reabrir).start()
        return {"ok": True, "encerrando": True, "reabrindo": reabrir,
                "pid": os.getpid()}

    @app.get("/api/reabrir")
    def _reabrir():
        return HTMLResponse(pagina_de_reabrir(),
                            headers={"Cache-Control": "no-store"})

    return app
