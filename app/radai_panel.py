# -*- coding: utf-8 -*-
import html as _html
import os
import socket
from pathlib import Path

import radai_archive
import radai_menu
import radai_config
import radai_web

VERSAO_PAINEL = "1.1"

HERE = Path(__file__).resolve().parent

_GEOM = None
_MONTAGEM = {}

# GUARDA: TPS_DESTINO tem tela propria (o primeiro uso, /primeiro-uso); caixa
# de texto aqui aceitaria qualquer valor e seria uma segunda porta.
FORA_DA_TELA = ("DRY_RUN", "SUAVIZAR_MM", "RECORTE_NO_CORPO", "IDIOMA",
                "TASKS", "TPS_DESTINO", "GUIA_VISTO")


def _tem_modulo(nome):
    # GUARDA: pelo caminho de importação, e não pelo arquivo ao lado: em
    # desenvolvimento cada app mora numa pasta, e na estação todos no app/.
    try:
        import importlib.util
        return importlib.util.find_spec(nome) is not None
    except Exception:
        return False


def estado_geom():
    global _GEOM
    if _GEOM is None:
        try:
            import radai_geom
            _GEOM = {"ok": True, "versao": getattr(radai_geom, "VERSAO_LIB", "?"), "erro": ""}
        except Exception as e:
            _GEOM = {"ok": False, "versao": "",
                     "erro": "%s: %s" % (type(e).__name__, str(e)[:160])}
    return dict(_GEOM)


def _em_uso(config):
    valor = (config or {}).get("em_uso")
    if callable(valor):
        try:
            return dict(valor() or {})
        except Exception:
            return {}
    return dict(valor or {})


def divergencias(config):
    if not config:
        return []
    try:
        _, disco = radai_config.ler_arquivo(config.get("caminho", ""))
        em_uso = _em_uso(config)
        travadas = set(config.get("so_no_arranque") or ())
        travadas |= set(temporarias(config))
        return sorted(k for k, v in disco.items()
                      if k in em_uso and k not in travadas
                      and str(v).strip() != str(em_uso[k]).strip())
    except Exception:
        return []


def temporarias(config):
    try:
        f = (config or {}).get("temporarias")
        return list(f() if callable(f) else (f or ()))
    except Exception:
        return []


def so_reabrindo(config):
    if not config:
        return []
    try:
        _, disco = radai_config.ler_arquivo(config.get("caminho", ""))
        arranque = config.get("arranque") or {}
        return sorted(k for k, v in arranque.items()
                      if k in disco
                      and str(disco[k]).split("#")[0].strip() != str(v).strip())
    except Exception:
        return []


def estado(ler_vigia=None, config=None):
    acervo = radai_archive.estado()

    vigia = {}
    if ler_vigia is not None:
        try:
            vigia = ler_vigia() or {}
        except Exception as e:
            vigia = {"erro": "%s: %s" % (type(e).__name__, str(e)[:160])}

    pronto_lote = (_tem_modulo("radai_batch") and not _MONTAGEM.get("radai_batch"))
    return {
        "lote": {"pronto": pronto_lote, "url": "/lote" if pronto_lote else "",
                 "falha": _MONTAGEM.get("radai_batch", "")},
        "config_mudou": divergencias(config),
        "config_reabrir": so_reabrindo(config),
        "pode_recarregar": bool((config or {}).get("recarregar")),
        "versao_painel": VERSAO_PAINEL,
        "entrega": _carimbo_entrega(),
        "maquina": vigia.get("machine") or os.environ.get("RADAI_MACHINE") or socket.gethostname(),
        "vigia": vigia,
        "geom": estado_geom(),
        "acervo": acervo,
    }


CSS_REGISTRO = u"""
.reg-campo{display:block;margin:10px 0;font-size:12.5px}
.reg-campo span{display:block;margin-bottom:4px}
.reg-campo select,.reg-campo input{width:100%;padding:7px 9px;border-radius:8px;
 background:rgba(255,255,255,.05);color:inherit;
 border:1px solid rgba(255,255,255,.14)}

.rc-tec{font-size:11.5px;color:var(--text-dim,#72829b);margin-top:2px}

"""


PAGINA = u"""<!doctype html><html><head><meta charset="utf-8">
<title>AutoContorno RT · Radioterapia.AI</title>
<style>
:root{
 --bg-0:var(--bg-0,#060d1a); --bg-1:var(--bg-1,#0a1120); --panel:var(--panel,#0c1322); --panel-2:var(--panel-2,#0f1729);
 --line:var(--line,#1e293b); --line-strong:var(--line-strong,#2a3a55);
 --text:var(--text,#e6edf7); --text-muted:var(--text-muted,#a3b1c6); --text-dim:var(--text-dim,#72829b);
 --accent:var(--accent,#4DA3FF); --accent-2:var(--mod-bridge,#9D8BFF);
 --accent-soft:rgba(77,163,255,0.10); --accent-line:rgba(77,163,255,0.35);
 --success:#5BC57F; --warn:#E1B23B; --error:var(--perigo,#E96A5C);
 --r-md:10px; --r-xl:18px;
 --font-display:'Inter',system-ui,'Segoe UI',Arial,sans-serif;
 --font-mono:'JetBrains Mono',ui-monospace,Consolas,monospace;
 --shadow-lift:0 8px 32px -12px rgba(0,0,0,0.5);
}
*{box-sizing:border-box}
html,body{background:var(--bg-0);color:var(--text);font-family:var(--font-display);margin:0}
.wrap{max-width:1320px;margin:0 auto}
.rt-topbar{display:flex;align-items:center;justify-content:space-between;padding:16px 28px;
 border-bottom:1px solid var(--line);background:var(--bg-1);position:sticky;top:0;z-index:10}
.rt-logo{display:flex;align-items:center;gap:10px;font-size:15px;font-weight:700;
 letter-spacing:-0.01em}
.rt-logo .ai{color:var(--accent)}
.rt-topright{display:flex;align-items:center;gap:10px}
.rt-status-pill{display:inline-flex;align-items:center;gap:8px;font-size:12px;
 color:var(--text-muted);padding:6px 12px;border-radius:999px;border:1px solid var(--line);
 background:var(--panel);font-family:var(--font-mono)}
.rt-dot{width:6px;height:6px;border-radius:50%;background:var(--success);
 box-shadow:0 0 0 3px rgba(91,197,127,0.25)}
.rt-dot.warn{background:var(--warn);box-shadow:0 0 0 3px rgba(225,178,59,.25)}
.rt-dot.err{background:var(--error);box-shadow:0 0 0 3px rgba(233,106,92,.25)}
a.rt-gear{text-decoration:none;color:var(--text-muted);background:var(--panel);
 border:1px solid var(--line);border-radius:var(--r-md);padding:7px 12px;font-size:12px;
 white-space:nowrap}
a.rt-gear:hover{color:var(--text);border-color:var(--accent-line)}
.rt-hero{padding:44px 28px 20px}
.rt-hero.rt-hero-md{padding:0}
.rt-eyebrow{display:inline-flex;align-items:center;gap:8px;padding:6px 12px;border-radius:999px;
 border:1px solid var(--accent-line);background:var(--accent-soft);color:var(--accent);
 font-size:12px;font-weight:600;letter-spacing:0.04em;text-transform:uppercase;
 margin-bottom:18px;font-family:var(--font-mono)}
.rt-h1{margin:0;font-weight:800;font-size:clamp(38px,6vw,68px);line-height:1.02;
 letter-spacing:-0.035em}
.rt-h1 .ai{background:linear-gradient(135deg,var(--accent,#4DA3FF),var(--accent-2));-webkit-background-clip:text;
 background-clip:text;-webkit-text-fill-color:transparent}
.rt-version{margin-top:6px;font-family:var(--font-mono);font-size:13px;color:var(--text-dim);
 letter-spacing:0.08em}
.rt-sub{margin:14px 0 0;font-size:clamp(15px,1.6vw,19px);color:var(--text-muted);
 line-height:1.5;max-width:64ch}
.rt-sub b{color:var(--text)}
.rt-features{display:flex;gap:22px;margin-top:26px;flex-wrap:wrap}
.rt-feature{padding-left:14px;border-left:2px solid var(--accent-line)}
.rt-feature-k{font-size:13px;font-weight:600;font-family:var(--font-mono)}
.rt-feature-v{font-size:12px;color:var(--text-dim);margin-top:2px}
.rt-banner{margin:0 28px 18px;background:var(--panel);border:1px solid var(--line);
 border-left:3px solid var(--accent);border-radius:var(--r-md);padding:12px 14px;
 font-size:13px;color:var(--text-muted);line-height:1.55}
.rt-banner b{color:var(--text)}
#reinicie{display:none;margin:0 28px 14px;background:rgba(225,178,59,.08);
 border:1px solid rgba(225,178,59,.4);color:var(--warn);padding:10px 14px;
 border-radius:var(--r-md);font-size:13px;line-height:1.5;
 align-items:center;gap:12px;flex-wrap:wrap}
#reinicie span{flex:1;min-width:240px}
#btrei{background:var(--warn);color:var(--bg-0,#060d1a);border:0;border-radius:6px;padding:7px 13px;
 font-size:12px;font-weight:700;cursor:pointer;white-space:nowrap}
#btrei:disabled{background:var(--panel-2,#0f1729);color:var(--text-dim,#72829b);cursor:default}
#reabrir{display:none;margin:0 28px 14px;background:rgba(233,106,92,.07);
 border:1px solid rgba(233,106,92,.35);color:var(--perigo,#E96A5C);padding:10px 14px;
 border-radius:var(--r-md);font-size:13px}
.cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;
 padding:0 28px 8px}
.cards-3{grid-template-columns:repeat(3,minmax(0,1fr))}
.cards-2{grid-template-columns:repeat(2,minmax(0,1fr))}
@media (max-width:1180px){.cards-3{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (max-width:820px){.cards,.cards-3,.cards-2{grid-template-columns:minmax(0,1fr)}}
.card{background:var(--panel);border:1px solid var(--line);border-radius:var(--r-xl);
 padding:18px 22px;display:flex;flex-direction:column;box-shadow:var(--shadow-lift);
 transition:all .25s}
.card:hover{border-color:var(--accent-line);background:var(--panel-2);transform:translateY(-2px);
 box-shadow:0 12px 30px -10px rgba(77,158,255,0.25)}
.card.off{opacity:.66}.card.off:hover{transform:none}
.card.vai{cursor:pointer}
.card.vai:focus-visible{outline:2px solid var(--accent);outline-offset:3px}
.card.off{cursor:default}
.topo{display:flex;align-items:center;gap:9px;margin-bottom:6px}
.topo h2{font-size:17px;margin:0;flex:1;font-weight:700;letter-spacing:-0.01em}
.ico{font-size:19px}
.pill{font-size:10px;font-weight:700;letter-spacing:.4px;padding:3px 9px;border-radius:999px;
 border:1px solid var(--line);color:var(--text-muted);white-space:nowrap;font-family:var(--font-mono)}
.pill.ok{color:var(--success);border-color:rgba(91,197,127,.4);background:rgba(91,197,127,.08)}
.pill.warn{color:var(--warn);border-color:rgba(225,178,59,.4);background:rgba(225,178,59,.08)}
.pill.err{color:var(--error);border-color:rgba(233,106,92,.4);background:rgba(233,106,92,.08)}
.desc{color:var(--text-muted);font-size:12.5px;line-height:1.5;margin:0 0 12px}
.desc b{color:var(--text)}
.nums{display:grid;grid-template-columns:repeat(auto-fit,minmax(80px,1fr));gap:10px;
 margin-bottom:14px}
.k{color:var(--text-dim);font-size:10px;text-transform:uppercase;letter-spacing:.4px;
 font-family:var(--font-mono)}
.v{font-size:17px;font-weight:700;margin-top:2px}
.v.ok{color:var(--success)}.v.warn{color:var(--warn)}.v.err{color:var(--error)}
.v.mut{color:var(--text-dim)}
.acao{margin-top:auto}
a.btn,span.btn{display:inline-block;text-decoration:none;font-size:13px;font-weight:600;
 border-radius:var(--r-md);padding:10px 15px;background:var(--panel-2);
 border:1px solid var(--line-strong);color:var(--text);margin-right:6px}
a.btn.pri{background:var(--accent);border-color:var(--accent);color:var(--bg-0,#060d1a)}
a.btn:hover{filter:brightness(1.12)}
span.btn.off{background:transparent;border:1px dashed var(--line-strong);color:var(--text-dim)}
.falta{color:var(--text-dim);font-size:11px;margin-top:9px;line-height:1.5}
.rodape{margin:22px 28px 0;color:var(--text-dim);font-size:11px;line-height:1.8;
 border-top:1px solid var(--line);padding:14px 0 28px;font-family:var(--font-mono)}
.rodape code{color:var(--text-muted)}

.cx .det.porque{display:block;color:var(--aviso,#E8A33D);margin-top:2px}
@CSS_REGISTRO@
</style></head><body><div class="wrap">

<header class="rc-topo">
 <a class="rc-marca" href="/" title="Radioterapia.AI Local"><span class="rc-nome">radioterapia<span class="g">.ai</span></span><span class="rc-sub" data-radai-frase>Local Suite</span></a>
 <span class="rc-seta">&#8594;</span>
 <span class="rc-tela" data-radai-frase>Início</span>
 <div class="dir">
  <span class="rt-status-pill"><span class="rt-dot" id="dot"></span><span id="maq">&#8212;</span></span>
  <span data-radai-lang></span>
  <a class="rt-gear" href="/config">&#9881; <span data-radai-frase>Configurações</span></a>
 </div>
</header>

<div class="rt-hero rt-hero-md">
 @CAPA@
</div>

<div id="reinicie">
 <span id="reinicie_txt"></span>
 <button id="btrei" onclick="reiniciar()">&#8635; Reiniciar agora</button>
</div>
<div id="reabrir"></div>


<script>
var PEDIDO=false;    // uma recarga ja foi pedida: nao sobrescrever o aviso dela
function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;');}
function el(id){return document.getElementById(id);}
function reiniciar(){
 var b=document.getElementById('btrei'), t=document.getElementById('reinicie_txt');
 b.disabled=true; b.textContent='recarregando...';
 fetch('/api/reiniciar',{method:'POST'}).then(function(r){return r.json()}).then(function(d){
  if(!d.ok){ PEDIDO=false; t.textContent='Nao consegui recarregar: '+(d.erro||'');
   b.disabled=false; b.innerHTML='&#8635; Reiniciar agora'; return; }
  PEDIDO=true;
  t.textContent='Recarga pedida — vai valer '+(d.quando||'em instantes')
   +(d.ocupado?' (o vigia esta no meio de uma serie e nao pode trocar de configuracao agora).':'.');
  setTimeout(function(){ b.disabled=false; b.innerHTML='&#8635; Reiniciar agora'; upd(); }, 4000);
 }).catch(function(e){ PEDIDO=false; b.disabled=false;
  b.innerHTML='&#8635; Reiniciar agora'; t.textContent='Nao consegui recarregar: '+e; });
}
function nums(id,pares){
 var e=document.getElementById(id); if(!e) return;
 e.innerHTML = pares.map(function(p){
  return '<div><div class="k">'+esc(p[0])+'</div><div class="v '+(p[2]||'')+'">'+esc(p[1])+'</div></div>';
 }).join('');
}
function pill(id,texto,classe){
 var e=document.getElementById(id); if(!e) return;
 e.textContent=texto; e.className='pill '+(classe||'');
}
function classe(id,c){ var e=document.getElementById(id); if(e) e.className=c; }
function html(id,h){ var e=document.getElementById(id); if(e) e.innerHTML=h; }
function upd(){fetch('/api/painel').then(function(r){return r.json()}).then(function(d){
 document.getElementById('maq').textContent=d.maquina||'—';

 var rei=document.getElementById('reinicie'), mud=d.config_mudou||[];
 rei.style.display=mud.length?'flex':'none';
 if(mud.length && !PEDIDO) document.getElementById('reinicie_txt').textContent=
   'A configuracao mudou no arquivo ('+mud.join(', ')+') e o vigia em execucao ainda '
   +'usa os valores antigos.';
 document.getElementById('btrei').style.display=d.pode_recarregar?'':'none';
 if(!mud.length) PEDIDO=false;
 var rb=document.getElementById('reabrir'), rea=d.config_reabrir||[];
 rb.style.display=rea.length?'block':'none';
 rb.textContent='Estas chaves so valem reabrindo o programa: '+rea.join(', ')
   +'. O painel ja esta escutando na porta antiga — feche a janela do vigia e rode '
   +'o start_watcher.cmd de novo.';

 var v=d.vigia||{}, obs=[];
 var dot=document.getElementById('dot');
 dot.className='rt-dot'+((v.erro||Object.keys(v).length===0||v.ambiente_erro||v.saudavel===false)?' err'
   :((!v.root||v.paused||v.dry_run)?' warn':''));
 if(v.erro || Object.keys(v).length===0){ pill('p_vigia','SEM DADOS','err'); }
 else if(v.ambiente_erro){ pill('p_vigia','SEM O MOTOR','err');
   obs.push('Este Python nao roda o TotalSegmentator ('+esc(v.ambiente_erro)+'). O vigia parou '
    +'sozinho e NAO marcou serie nenhuma como falha. Abra o vigia pelo start_watcher.cmd, que usa '
    +'o Python do bundle, e clique em Rodar.'); }
 else if(!v.root){ pill('p_vigia','INERTE','warn'); obs.push('ROOT vazio no radai_watcher.config: o vigia subiu, mas nao esta varrendo nada. Preencher so depois de combinar com o TI.'); }
 else if(v.paused){ pill('p_vigia','PAUSADO','warn'); }
 else if(!v.saudavel){ pill('p_vigia','SEM RESPOSTA','err'); obs.push('O laco de trabalho nao responde ha '+esc(v.parado_ha)+'s. '+esc(v.worker_erro||'')); }
 else { pill('p_vigia','RODANDO','ok'); }
 if(v.dry_run) obs.push('MODO SIMULAÇÃO (DRY_RUN=1): nenhum RTSTRUCT de verdade é gravado, e nada entra no acervo.');
 if(v.root_ok===false) obs.push('ROOT inacessivel agora: '+esc(v.root));
 nums('n_vigia',[['Na fila', v.n_queue==null?'—':v.n_queue, ''],
                 ['Concluidas', v.done_today==null?'—':v.done_today, 'ok'],
                 ['Ult. varredura', v.last_scan||'—', 'mut']]);

 var lo=d.lote||{};
 pill('p_lote', lo.pronto?'PRONTO':'INDISPONIVEL', lo.pronto?'ok':'');
 classe('c_lote','card'+(lo.pronto?'':' off'));
 html('acao_lote', lo.pronto
  ? '<a class="btn pri" href="'+esc(lo.url)+'">Rodar agora</a>'
  : '<span class="btn off">Indisponivel</span>');



 var g=d.geom||{}, ac=d.acervo||{}, pes=[];
 pes.push(g.ok ? 'Biblioteca de geometria: v%s carregada.'.replace('%s', esc(g.versao))
                : '<span style="color:var(--perigo,#E96A5C)">Biblioteca de geometria NAO carrega: '+esc(g.erro)+' — o pos-processamento nao vai funcionar neste runtime.</span>');
 pes.push('Acervo: <code>'+esc(ac.raiz)+'</code>'+(ac.existe?'':' (ainda nao criado — nasce na primeira serie concluida)'));
 if(ac.erro) pes.push('<span style="color:var(--perigo,#E96A5C)">Erro lendo o acervo: '+esc(ac.erro)+'</span>');
 var ent=(d.entrega||{});
 if(ent.rotulo) pes.push('<b>'+esc(ent.rotulo)+'</b>');
 pes.push(v.versao
   ? 'painel v%s · vigia v%s'.replace('%s', esc(d.versao_painel)).replace('%s', esc(v.versao))
   : 'painel v' + esc(d.versao_painel));
 document.getElementById('rodape').innerHTML=pes.join('<br>');
 cartoesClicaveis();
})}

function cartoesClicaveis(){
 Array.prototype.forEach.call(document.querySelectorAll('.card'), function(c){
  var a = c.querySelector('.acao a[href]');
  if(!a || c.classList.contains('off')){
   c.classList.remove('vai'); c.removeAttribute('tabindex');
   c.removeAttribute('role'); c.dataset.href=''; return;
  }
  c.dataset.href = a.getAttribute('href');
  c.classList.add('vai');
  c.setAttribute('role','link');
  c.setAttribute('tabindex','0');
  if(c.dataset.ligado) return;             // ouvinte uma vez so, nao a cada 5 s
  c.dataset.ligado = '1';
  c.addEventListener('click', function(ev){
   if(ev.target.closest('a,button')) return;
   if(c.dataset.href) location.href = c.dataset.href;
  });
  c.addEventListener('keydown', function(ev){
   if((ev.key==='Enter'||ev.key===' ') && c.dataset.href){
    ev.preventDefault(); location.href = c.dataset.href;
   }
  });
 });
}

</script></body></html>"""




def _carimbo_entrega():
    try:
        import radai_delivery
        c = dict(radai_delivery.carimbo())
        c["rotulo"] = radai_delivery.rotulo()
        return c
    except Exception:
        return {"rotulo": "", "versao": "", "build": "", "origem": ""}


def _costurar_home(p):
    for nome, mod, fn_ in ((u"sistema de design", "radai_ui", "aplicar"),
                           (u"folha da capa", "radai_cover", "aplicar"),
                           (u"seletor de idioma", "radai_languages", "aplicar")):
        try:
            p = getattr(__import__(mod), fn_)(p)
        except Exception as e:
            try:
                import sys as _s
                _s.stderr.write("[home] %s nao foi montado: %s\n" % (nome, e))
            except Exception:
                pass
    try:
        import radai_menu
        p = radai_menu.aplicar(p, "autocontorno")
    except Exception:
        try:
            import radai_menu as _m
            p = _m.marcar_tela(p, "autocontorno")
        except Exception:
            pass
    return p


def pagina_inicial():
    try:
        import radai_modules
        corpo = radai_modules.pagina("autocontorno")
        capa = (u'<style>%s%s</style>%s'
                % (radai_modules.CSS, radai_modules.JS_VIGIA and u"", corpo))
    except Exception:
        capa = u"<h1>AutoContorno RT</h1>"
    try:
        import radai_modules as _md
        cards = _md.JS_VIGIA
    except Exception:
        cards = u""
    return (PAGINA.replace("@CARDS@", cards)
                  .replace("@CAPA@", capa))


PAGINA_CONFIG = u"""<!doctype html><html><head><meta charset="utf-8">
<title>Configurações · Radioterapia.AI</title><style>
@CSS_REGISTRO@
.proc-laudo{border:1px solid var(--line);border-radius:8px;padding:10px 12px;
 margin-top:10px;background:rgba(255,255,255,.02)}
.proc-laudo table{border-collapse:collapse;font-size:12px}
.proc-laudo th{text-align:left;padding:3px 14px 3px 0;color:var(--text-dim);
 font-weight:500;white-space:nowrap;vertical-align:top}
.proc-laudo td{padding:3px 0;color:var(--text-muted)}
.aviso-inline{margin:8px 0 0 0;padding:7px 10px;border-radius:6px;font-size:11.5px;
 background:rgba(255,107,107,.12);border:1px solid rgba(255,107,107,.4);
 color:var(--text)}

body{font-family:Segoe UI,Arial;background:var(--bg-0,#060d1a);color:var(--text,#e6edf7);margin:0;padding:18px 18px 28px}
h1{font-size:20px;margin:0 0 2px 0}.a{color:var(--accent,#4DA3FF)}
.sub{color:var(--text-muted,#a3b1c6);font-size:12px}
.sub code{color:var(--text-muted,#a3b1c6)}
.cabecalho{display:flex;align-items:flex-start;gap:12px;margin-bottom:14px}
.cabecalho>div:first-child{flex:1}
.topo{position:sticky;top:0;z-index:5;background:var(--bg-0,#060d1a);
margin:-18px -18px 14px -18px;padding:14px 18px 1px 18px;border-bottom:1px solid var(--line,#1e293b)}
.acoes{display:flex;align-items:center;gap:9px;flex-wrap:wrap;justify-content:flex-end}
.acoes #msg{margin-right:4px;text-align:right;max-width:340px}
.acoes button{white-space:nowrap}
@media (max-width:720px){
 .topo{position:static}
 .cabecalho{flex-wrap:wrap}
 .cabecalho>*{flex:1 1 100%;min-width:0}
 .cabecalho .acoes{justify-content:flex-start}
 #arq{word-break:break-all}
}
a.voltar{text-decoration:none;color:var(--text,#e6edf7);background:var(--panel-2,#0f1729);border:1px solid var(--accent-line,#2a3d57);
border-radius:6px;padding:9px 13px;font-size:12px;white-space:nowrap}
a.voltar:hover{background:var(--line-strong,#2a3a55)}
.aviso{background:var(--panel,#0c1322);border:1px solid var(--accent-line,#2a3d57);border-left:4px solid var(--accent,#4DA3FF);
border-radius:8px;padding:10px 12px;margin-bottom:14px;font-size:13px;color:var(--text,#e6edf7);line-height:1.5}
.aviso b{color:var(--text,#fff)}
.cf-barra{margin:12px 0 0;padding:10px 13px;border-radius:var(--r-md,6px);
 border:1px solid var(--line-strong,#2a3a55);background:var(--panel-2,#0f1729);
 font-size:12.5px;color:var(--text,#e6edf7)}
.cf-barra.ok{border-color:var(--ok,#12873F)}
.cf-barra.ruim{border-color:var(--perigo,#E96A5C)}
.cf-rel{margin-top:12px;border:1px solid var(--line,#1e293b);
 border-radius:var(--r-md,6px);max-height:460px;overflow:auto;
 background:var(--bg-0,#060d1a)}
.cf-sec{padding:9px 13px;border-bottom:1px solid var(--line,#1e293b)}
.cf-sec h4{margin:0 0 7px;font-size:11px;letter-spacing:.11em;
 text-transform:uppercase;color:var(--text-dim,#72829b);
 font-family:var(--mono,monospace)}
.cf-l{display:flex;gap:9px;align-items:baseline;padding:2px 0;
 font-size:12px;line-height:1.5}
.cf-m{flex:0 0 15px;font-family:var(--mono,monospace);font-weight:700}
.cf-l.ok .cf-m{color:var(--success,#5BC57F)}
.cf-l.falta .cf-m{color:var(--perigo,#E96A5C)}
.cf-l.aviso .cf-m{color:var(--aviso,#E8A33D)}
.cf-n{flex:0 0 220px;color:var(--text-muted,#a3b1c6)}
.cf-v{flex:1 1 auto;font-family:var(--mono,monospace);
 font-variant-numeric:tabular-nums;color:var(--text,#e6edf7);
 word-break:break-all}
.cf-d{padding:1px 0 4px 244px;font-size:11px;
 color:var(--text-dim,#72829b);line-height:1.45}
@media (max-width:720px){.cf-n{flex:0 0 130px}.cf-d{padding-left:154px}}
.faixa{display:none;background:var(--fundo-aviso,#1c1608);border:1px solid var(--aviso,#E8A33D);color:var(--text,#e6edf7);padding:9px 12px;
border-radius:8px;margin-bottom:14px;font-size:13px;line-height:1.5}
.faixa b{color:var(--text,#e6edf7)}
.faixa.ok{background:var(--fundo-ok,#0d1a12);border-color:var(--success,#5BC57F);color:var(--text,#e6edf7)}
.campos{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:12px}
.campos .larga{grid-column:1 / -1}
.modulo{background:var(--bg-1,#0a1120);border:1px solid var(--line,#1e293b);border-radius:8px;margin-bottom:10px}
.modulo>summary{cursor:pointer;padding:10px 12px;font-size:13px;font-weight:600;
color:var(--text,#e6edf7);list-style:none;display:flex;align-items:center;gap:8px}
.modulo>summary::-webkit-details-marker{display:none}
.modulo>summary::before{content:"▸";color:var(--accent,#4DA3FF);font-size:11px}
.modulo[open]>summary::before{content:"▾"}
.modulo>summary:hover{background:var(--panel,#0c1322)}
.modulo>summary .qtd{background:var(--panel-2,#0f1729);color:var(--text-muted,#a3b1c6);border-radius:10px;
padding:1px 7px;font-size:10px;font-weight:400}
.modulo>.campos{padding:0 12px 12px 12px}
.modulo iframe{width:100%;height:62vh;border:0;border-radius:6px;background:var(--bg-0,#060d1a)}
.ps-corpo iframe{width:100%;height:62vh;min-height:420px;border:0;
 border-radius:var(--r-md,6px);background:var(--bg-0,#060d1a);display:block}
label.sw{display:flex;align-items:center;gap:9px;cursor:pointer;font-size:12px;
color:var(--text,#e6edf7);line-height:1.4}
label.sw input{position:absolute;opacity:0;width:0;height:0}
label.sw .tr{flex:none;width:36px;height:20px;border-radius:10px;background:var(--panel-2,#0f1729);
position:relative;transition:background .15s}
label.sw .tr::after{content:"";position:absolute;top:2px;left:2px;width:16px;height:16px;
border-radius:50%;background:var(--text-muted,#a3b1c6);transition:transform .15s,background .15s}
label.sw input:checked + .tr{background:var(--ok,#12873F)}
label.sw input:checked + .tr::after{transform:translateX(16px);background:var(--ok-txt,#fff)}
label.sw input:focus-visible + .tr{outline:2px solid var(--accent,#4DA3FF)}
.campo{background:var(--panel,#0c1322);border:1px solid var(--line,#1e293b);border-radius:8px;padding:11px 12px}
.campo.destaque{border-color:var(--accent,#4DA3FF)}
.campo .ui-fav{margin:7px 0 0 6px;padding:6px 9px;vertical-align:top}
label{display:block;font-size:11px;font-weight:700;letter-spacing:.4px;color:var(--accent,#4DA3FF);margin-bottom:5px}
input,select{width:100%;box-sizing:border-box;background:var(--bg-0,#060d1a);color:var(--text,#e6edf7);
border:1px solid var(--accent-line,#2a3d57);border-radius:6px;padding:8px 9px;font-size:13px;
font-family:Consolas,monospace}
input:focus,select:focus{outline:0;border-color:var(--accent,#4DA3FF)}
.ajuda{color:var(--text-muted,#a3b1c6);font-size:11px;line-height:1.45;margin-top:6px}
.res{font-size:11px;line-height:1.45;margin-top:7px}
.res.ok{color:var(--success,#5BC57F)}.res.err{color:var(--perigo,#E96A5C)}.res.warn{color:var(--warn,#E1B23B)}
button{background:var(--panel-2,#0f1729);color:var(--text,#e6edf7);border:0;border-radius:6px;padding:9px 14px;
font-size:13px;cursor:pointer}
button.pri{background:var(--ok,#12873F);color:var(--ok-txt,#fff)}button.sec{background:var(--panel-2,#0f1729);margin-top:7px;padding:6px 10px;font-size:12px}
a.bt{display:inline-block;background:var(--panel-2,#0f1729);color:var(--text,#e6edf7);border:0;
border-radius:6px;padding:9px 14px;font-size:13px;text-decoration:none;cursor:pointer}
a.bt.sec{margin-top:7px;padding:6px 10px;font-size:12px}
a.bt:hover{filter:brightness(1.2)}
a.bt:focus-visible{outline:2px solid var(--accent,#4DA3FF);outline-offset:2px}
button:disabled{background:var(--panel-2,#0f1729);color:var(--text-dim,#72829b);cursor:default}
.barra{margin-top:16px;display:flex;align-items:center;gap:12px}
#msg{font-size:13px}

.proc-rec{margin-top:10px;padding:10px 12px;border-radius:9px;
 border:1px solid var(--line);background:rgba(120,170,255,.06);
 --text-dim:var(--text-muted)}
.proc-rec.ok{background:rgba(120,220,160,.05)}
.proc-rec .rc-lin{display:flex;align-items:center;gap:9px;flex-wrap:wrap}
.proc-rec .rc-tag{font-size:9.5px;letter-spacing:.11em;text-transform:uppercase;
 color:var(--text-dim)}
.proc-rec code{font-size:13px;font-weight:600}
.proc-rec .rc-ja{font-size:11.5px;color:var(--text-dim)}
.proc-rec .sub{margin:7px 0 0 0;line-height:1.55}
.proc-rec .rc-ganho{color:var(--text-muted)}
.proc-rec .rc-risco{border-left:2px solid var(--line);padding-left:10px;
 font-size:11.5px}
.btn.peq{padding:4px 11px;font-size:11.5px;border-radius:7px}
.rodape{margin:26px 0 0;color:var(--text-dim);font-size:11px;
 line-height:1.8}
.rodape code{color:var(--text-muted);font-family:var(--font-mono,monospace);
 overflow-wrap:anywhere}
.cfg-docs{display:flex;flex-wrap:wrap;gap:6px 18px;align-items:baseline;
 margin:26px 0 8px;padding-top:14px;border-top:1px solid var(--line);
 font-size:11.5px;color:var(--text-dim)}
.cfg-docs a{color:var(--text-muted);text-decoration:none;
 border-bottom:1px solid transparent}
.cfg-docs a:hover{color:var(--accent);border-bottom-color:var(--accent)}
.cfg-docs a:focus-visible{outline:2px solid var(--accent);outline-offset:2px}

.cfg-cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;
 margin:2px 0 18px}
@media (max-width:1180px){.cfg-cards{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (max-width:560px){
 .cfg-cards{grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}
 a.cfg-card{min-height:0;padding:11px 12px}
 .cfg-card p{display:none}
 .ps-cab .ps-sub{display:none}
}
a.cfg-card{display:flex;flex-direction:column;gap:7px;min-height:122px;
 padding:14px 15px 13px;border-radius:12px;background:var(--panel,#0c1322);
 border:1px solid var(--line,#1e293b);color:var(--text,#e6edf7);
 text-decoration:none;box-sizing:border-box;min-width:0;
 transition:border-color .15s ease,background-color .15s ease}
a.cfg-card:hover{border-color:var(--accent-line,#2a3d57);
 background:var(--panel-2,#0f1729)}
a.cfg-card:focus-visible{outline:2px solid var(--accent,#4DA3FF);outline-offset:2px}
.cfg-card .cab{display:flex;align-items:center;justify-content:space-between}
.cfg-card .ic{display:inline-grid;place-items:center;width:30px;height:30px;
 border-radius:var(--r-md,8px);font-size:17px;color:var(--accent,#4DA3FF);
 background:var(--accent-fraco,rgba(77,163,255,.10));
 border:1px solid var(--accent-line,#2a3d57)}
.cfg-card .ic .ui-ic{margin:0}
.cfg-card .n{font:600 10.5px/1 var(--font-mono,monospace);
 color:var(--text-dim,#72829b);letter-spacing:.06em}
.cfg-card h3{margin:2px 0 0;font:650 14px/1.25 var(--font-display,inherit);
 color:var(--text,#e6edf7);letter-spacing:-.005em}
.cfg-card p{margin:0;font-size:12px;line-height:1.5;color:var(--text-muted,#a3b1c6)}
.cfg-card .st{margin-top:auto;padding-top:4px;font:400 11px/1.4 var(--font-mono,monospace);
 color:var(--text-dim,#72829b);white-space:nowrap;overflow:hidden;
 text-overflow:ellipsis}
.cfg-card .st b{color:var(--text-muted,#a3b1c6);font-weight:600}
a.cfg-card.perigo .ic{color:var(--perigo,#E96A5C);
 background:rgba(233,106,92,.08);border-color:rgba(233,106,92,.35)}
a.cfg-card.perigo:hover{border-color:rgba(233,106,92,.55)}
.ps-cx{scroll-margin-top:var(--cfg-topo,150px)}
.cfg-sub{margin:4px 0 8px;font:600 12px/1.3 var(--font-display,inherit);
 color:var(--text,#e6edf7)}
.cfg-sub ~ .cfg-sub{margin-top:18px;padding-top:14px;
 border-top:1px solid var(--line,#1e293b)}
a.cfg-card[aria-current="true"]{border-color:var(--accent,#4DA3FF);
 background:var(--panel-2,#0f1729)}
@media (prefers-reduced-motion:reduce){a.cfg-card{transition:none}}
@CSS_ESTACAO@
</style></head><body>
<div class="topo">
 <div class="cabecalho">
<header class="rc-topo"><a class="rc-marca" href="/" title="Radioterapia.AI Local"><span class="rc-nome">radioterapia<span class="g">.ai</span></span><span class="rc-sub" data-radai-frase>Local Suite</span></a><span class="rc-seta">&#8594;</span><span class="rc-tela">Configurações</span><div class="dir"><a class="rc-voltar" href="/">&#8592; Voltar ao menu</a></div></header>

  <div class="rc-capa rc-compacta">
   <span class="rc-chip"><i>⚙</i> Estação</span>
   <h1>Configurações da <span>estação</span></h1>
   <p class="rc-frase" data-radai-frase>o que vale para esta máquina: a aparência, o processamento, o ritmo da automação e as ferramentas</p>
   <p class="rc-frase rc-tec">arquivo: <code id="arq">—</code></p></div>
  <div class="acoes">
   <span id="msg"></span>
   <button class="pri" id="btsalvar" onclick="salvar()">Salvar no arquivo</button>
   <button id="btrei_cfg" style="display:none" onclick="recarregar()">&#8635; Reiniciar agora</button>
  </div>
 </div>
 <div class="faixa" id="faixa"></div>
</div>

<nav class="cfg-cards" aria-label="funções desta estação">
 <a class="cfg-card" href="#ps_geral" data-alvo="ps_geral">
  <span class="cab"><span class="ic">@CFG_ICO_GERAL@</span><span class="n">1</span></span>
  <h3 data-radai-frase>Geral</h3>
  <p data-radai-frase>Aparência, idioma, pasta favorita e o anel dos contornos.</p>
  <span class="st" id="cst_geral">&#8212;</span></a>
 <a class="cfg-card" href="#ps_processamento" data-alvo="ps_processamento">
  <span class="cab"><span class="ic">@CFG_ICO_PROCESSAMENTO@</span><span class="n">2</span></span>
  <h3 data-radai-frase>Processamento</h3>
  <p data-radai-frase>Onde o programa processa: a placa de vídeo ou o processador.</p>
  <span class="st" id="cst_processamento">&#8212;</span></a>
 <a class="cfg-card" href="#ps_ritmo" data-alvo="ps_ritmo">
  <span class="cab"><span class="ic">@CFG_ICO_RITMO@</span><span class="n">3</span></span>
  <h3 data-radai-frase>Ritmo da automação</h3>
  <p data-radai-frase>De quanto em quanto a fila varre, quanto espera, e quando uma task é dada como travada.</p>
  <span class="st" id="cst_ritmo">&#8212;</span></a>
 <a class="cfg-card" href="#ps_pastas" data-alvo="ps_pastas">
  <span class="cab"><span class="ic">@CFG_ICO_PASTAS@</span><span class="n">4</span></span>
  <h3 data-radai-frase>Pastas e porta</h3>
  <p data-radai-frase>Onde saem os arquivos, o log e o status, e a porta do painel.</p>
  <span class="st" id="cst_pastas">&#8212;</span></a>
 <a class="cfg-card" href="#ps_estruturas" data-alvo="ps_estruturas">
  <span class="cab"><span class="ic">@CFG_ICO_ESTRUTURAS@</span><span class="n">5</span></span>
  <h3 data-radai-frase>Estruturas e Protocolos</h3>
  <p data-radai-frase>Os nomes das estruturas no STUDY e os seus protocolos de entrega.</p>
  <span class="st" id="cst_estruturas">&#8212;</span></a>
 <a class="cfg-card" href="#ps_atualizar" data-alvo="ps_atualizar">
  <span class="cab"><span class="ic">@CFG_ICO_ATUALIZAR@</span><span class="n">6</span></span>
  <h3 data-radai-frase>Atualizar o programa</h3>
  <p data-radai-frase>A versão desta estação e o instalador mais recente.</p>
  <span class="st" id="cst_atualizar">@SUB_ATU@</span></a>
 <a class="cfg-card" href="#ps_limpar" data-alvo="ps_limpar">
  <span class="cab"><span class="ic">@CFG_ICO_DIAGNOSTICAR@</span><span class="n">7</span></span>
  <h3 data-radai-frase>Diagnósticos e Registros</h3>
  <p data-radai-frase>Conferir a instalação, e o registro de casos para enviar.</p>
  <span class="st"><b id="cst_registro">?</b> <span data-radai-frase>caso(s) registrado(s)</span></span></a>
 <a class="cfg-card perigo" href="#secDesinst" data-alvo="secDesinst">
  <span class="cab"><span class="ic">@CFG_ICO_DESINSTALAR@</span><span class="n">8</span></span>
  <h3 data-radai-frase>Desinstalar</h3>
  <p data-radai-frase>Remover o programa desta estação, guardando o que você construiu.</p></a>
</nav>

<div class="aviso" id="cfgAviso" hidden title="A configuração é lida uma vez, no arranque. Por isso salvar não basta: o Reiniciar agora manda o vigia reler o arquivo entre uma série e outra, sem fechar o programa.">
<b>Depois de salvar, clique em Reiniciar agora: o vigia relê o arquivo entre uma série e outra, sem fechar o programa.</b>
</div>

<section class="ps-cx fechado" id="ps_geral" hidden>
 <h2 class="ps-cab" tabindex="0" role="button"><span class="ps-num">1</span>
  <span data-radai-frase>Geral</span>
  <span class="ps-sub" id="subTema">&#8212;</span><span class="ui-ajuda" tabindex="0" aria-label="ajuda">?<span class="ui-balao"><p><b>As escolhas desta seção valem na hora</b>, sem reiniciar o vigia.</p><p>As outras chaves são lidas uma vez, no arranque, e valem para o lote da noite. O tema fica no navegador desta estação; na primeira abertura, ele é o escuro.</p></span></span>
  <span class="ps-seta">&#9662;</span></h2>
 <div class="ps-corpo">
  <label data-radai-frase>Aparência</label>
  <div class="linha opcoes" id="opTema">
   <select id="selTema" data-ui-seg data-ui-tema aria-label="Aparência">
    <option value="claro" data-ui-icone="sol" title="Modo claro">Claro</option>
    <option value="escuro" data-ui-icone="lua" title="Modo escuro">Escuro</option>
    <option value="sistema" data-ui-icone="monitor" title="Seguir o tema do sistema">Sistema</option>
   </select>
  </div>

  <label style="margin-top:14px"><span data-radai-frase>Idioma da
   interface</span><span class="ui-ajuda" tabindex="0" aria-label="ajuda">?<span class="ui-balao"><p>Vale para as telas, e para esta esta&ccedil;&atilde;o.</p><p><b>Nada do que se grava muda:</b> nome de estrutura, caminho e identificador de licen&ccedil;a ficam como est&atilde;o.</p><p>Termos e Pol&iacute;tica valem <b>em portugu&ecirc;s</b> &mdash; tradu&ccedil;&atilde;o jur&iacute;dica exige revisor, e enquanto n&atilde;o houver um, o original &eacute; o que responde.</p></span></span></label>
  <div class="linha" data-radai-idiomas data-radai-lang></div>

@GERAL_ESTACAO@
 </div>
</section>

<section class="ps-cx fechado" id="ps_processamento" hidden>
 <h2 class="ps-cab" tabindex="0" role="button"><span class="ps-num">2</span>
  <span data-radai-frase>Processamento</span>
  <span class="ps-sub" id="sub_processamento">&#8212;</span><span class="ui-ajuda" tabindex="0" aria-label="ajuda">?<span class="ui-balao"><p><b>O recomendado é auto:</b> o programa mede a placa e a memória livre antes de cada task e escolhe sozinho onde processar.</p><p>O laudo abaixo diz o que esta estação tem e onde o auto vai processar nela.</p></span></span>
  <span class="ps-seta">&#9662;</span></h2>
 <div class="ps-corpo"><div class="campos" id="campos_processamento"></div></div>
</section>

<section class="ps-cx fechado" id="ps_ritmo" hidden>
 <h2 class="ps-cab" tabindex="0" role="button"><span class="ps-num">3</span>
  <span data-radai-frase>Ritmo da automação</span>
  <span class="ps-sub" id="sub_ritmo">&#8212;</span><span class="ui-ajuda" tabindex="0" aria-label="ajuda">?<span class="ui-balao"><p>Vale para a fila da noite e para o «Rodar agora»: de quanto em quanto a pasta é varrida, quanto tempo uma série nova espera parada antes de entrar, e os tetos de tempo.</p><p><b>O travamento</b> (as chaves TRAVA_*) decide quando uma task sem sinal de vida é interrompida e refeita, sem derrubar a série.</p></span></span>
  <span class="ps-seta">&#9662;</span></h2>
 <div class="ps-corpo"><div class="campos" id="campos_ritmo"></div></div>
</section>

<section class="ps-cx fechado" id="ps_pastas" hidden>
 <h2 class="ps-cab" tabindex="0" role="button"><span class="ps-num">4</span>
  <span data-radai-frase>Pastas e porta</span>
  <span class="ps-sub" id="sub_pastas">&#8212;</span>
  <span class="ps-seta">&#9662;</span></h2>
 <div class="ps-corpo"><div class="campos" id="campos_pastas"></div></div>
</section>

<div id="campos"></div>
<template id="cfg_fav_molde">@FAV_CFG@</template>

@SECAO_ESTRUTURAS@

<section class="ps-cx fechado" id="ps_atualizar" hidden>
 <h2 class="ps-cab" tabindex="0" role="button"><span class="ps-num" id="numAtu">6</span>
  <span data-radai-frase>Atualizar o programa</span>
  <span class="ps-sub" id="subAtu">@SUB_ATU@</span><span class="ui-ajuda" tabindex="0" aria-label="ajuda">?<span class="ui-balao"><p>Abre a p&aacute;gina onde a vers&atilde;o mais recente do instalador &eacute; publicada.</p><p><b>Nada &eacute; baixado sozinho.</b> &laquo;Atualizar agora&raquo; baixa e roda o instalador quando voc&ecirc; clica: o app fecha, atualiza e reabre, e a configura&ccedil;&atilde;o, o acervo e os logs desta esta&ccedil;&atilde;o ficam.</p><p>Se esta esta&ccedil;&atilde;o n&atilde;o tem internet, abra o link em outra m&aacute;quina e traga o arquivo.</p></span></span>
  <span class="ps-seta">&#9662;</span></h2>
 <div class="ps-corpo">
  <p class="sub" style="margin:0 0 10px" data-radai-frase>Esta estação está na
   versão indicada acima. O instalador preserva a configuração, o acervo e
   os logs desta estação.</p>
  <div class="linha">
   <button type="button" class="sec" id="btConsultarVersao" onclick="if(window.radaiConsultarVersao) window.radaiConsultarVersao()" data-radai-frase>Verificar atualizações</button>
   @BT_ATU_AGORA@
   <a class="bt sec" id="lkAtu" target="_blank" rel="noopener"
    href="@URL_VERSOES@"
    data-radai-frase>Ver as versões publicadas</a>
   @BT_INSTALADOR@
  </div>
  <p class="sub" style="margin:10px 0 0" data-radai-frase>Sem internet nesta
   estação? Abra o link em outra máquina e traga o arquivo — o instalador
   funciona sem rede.</p>
 </div>
</section>

<section class="ps-cx fechado" id="ps_limpar" hidden>
 <h2 class="ps-cab" tabindex="0" role="button"><span class="ps-num" id="numLimp">7</span>
  <span data-radai-frase>Diagnósticos e Registros</span>
  <span class="ps-sub" id="subLimp">&#8212;</span><span class="ui-ajuda" tabindex="0" aria-label="ajuda">?<span class="ui-balao"><p><b>Diagnosticar</b> confere a instala&ccedil;&atilde;o e a esta&ccedil;&atilde;o num clique e escreve tudo no log da barra da direita. N&atilde;o muda nada.</p><p><b>O registro de casos</b> guarda o que cada série ensinou, sem identificação de paciente, e monta o pacote e o relatório para enviar.</p></span></span>
  <span class="ps-seta">&#9662;</span></h2>
 <div class="ps-corpo">
  <h4 class="cfg-sub" data-radai-frase>Diagnosticar</h4>
  <div class="linha">
   <button class="bt pri" id="btDiag" onclick="diagnosticar()"
    data-radai-frase>Diagnosticar</button>
  </div>
  <p class="sub" style="margin:10px 0 6px" data-radai-frase>Diagnosticar
   confere a instalação e a estação num clique — versões, pesos, GPU,
   travas clínicas, memória e disco — e escreve tudo no log da
   barra da direita.</p>
  <div id="cfBarra" class="cf-barra" style="display:none"></div>
  <div id="cfRel" class="cf-rel" style="display:none"></div>

  <h4 class="cfg-sub"><span data-radai-frase>Registro de casos</span> &#8212; <b id="reg_n">?</b> <span data-radai-frase>caso(s) registrado(s)</span></h4>
  <p class="sub" style="margin:0 0 10px" data-radai-frase>Cada série contornada deixa aqui o que
   ela ensinou: a máquina, a série, os tempos, os achados e o log completo.
   <b>Sem identificação de paciente</b> — nem nome, nem registro, nem UID,
   nem caminho de pasta.</p>
  <label class="reg-campo"><span data-radai-frase>Esta máquina é</span>
   <select id="reg_papel">
    <option value="">(não declarado)</option>
    <option value="servidor de radioterapia">servidor de radioterapia</option>
    <option value="estacao de trabalho">estação de trabalho</option>
    <option value="estacao de contorno dedicada">estação de contorno dedicada</option>
    <option value="maquina pessoal">máquina pessoal</option>
    <option value="servidor de TI">servidor de TI</option>
   </select></label>
  <label class="reg-campo"><span data-radai-frase>Nota para quem vai ler</span>
   <input id="reg_nota" type="text" maxlength="200"
          placeholder="opcional: o que você quer que eu olhe neste lote"></label>
  <div class="linha">
   <button class="bt pri" id="reg_bt" onclick="regExportar()"
           data-radai-frase>Gerar pacote para enviar</button>
   <button class="bt sec" id="reg_rel_bt" onclick="regRelatorio()"
           data-radai-frase>Gerar relatório do período</button>
  </div>
  <p class="msg" id="reg_msg"></p>
  <h3 class="reg-resumo-tit" data-radai-frase>Resumo da última noite</h3>
  <div class="linha">
   <button class="bt sec" id="reg_resumo_bt" onclick="regResumo()"
           data-radai-frase>Copiar resumo</button>
  </div>
  <pre class="reg-resumo" id="reg_resumo" tabindex="0"
       style="white-space:pre-wrap;overflow-wrap:anywhere;max-height:320px;overflow:auto;font-size:12px;margin:8px 0 0"></pre>
  <div class="linha" id="fila_falhas" hidden>
   <p class="msg" id="fila_falhas_txt"></p>
   <button class="bt sec" id="fila_liberar_bt" onclick="filaLiberar()"
           data-radai-frase>Liberar</button>
  </div>
 </div>
</section>

<section class="ps-cx fechado" id="secDesinst" hidden>
 <h2 class="ps-cab" tabindex="0" role="button"><span class="ps-num" id="numFerr">8</span>
  <span data-radai-frase>Desinstalar</span>
  <span class="ps-sub" data-radai-frase>&#8212; remover o programa desta estação</span><span class="ui-ajuda" tabindex="0" aria-label="ajuda">?<span class="ui-balao"><p>Abre a ferramenta de remo&ccedil;&atilde;o, que fica na pasta do programa.</p><p>Ela mostra o que vai apagar, oferece <b>guardar</b> o acervo, a configura&ccedil;&atilde;o e os logs numa pasta ao lado, e pede a palavra <b>DESINSTALAR</b> digitada.</p><p>O programa precisa fechar antes: ele mesmo segura os arquivos.</p></span></span>
  <span class="ps-seta">&#9662;</span></h2>
 <div class="ps-corpo">
  <p class="sub" style="margin:0 0 10px" data-radai-frase>Isto fecha o programa e abre a ferramenta de remoção numa janela de comando. Nada é apagado sem você digitar a confirmação lá.</p>
  <p class="sub" id="dsOnde" style="margin:0 0 10px"></p>
  <div class="linha">
   <button class="bt" id="btDesinst" onclick="desinstalar()"
    data-radai-frase>Fechar e remover o programa</button>
  </div>
  <p class="msg" id="dsMsg"></p>
 </div>
</section>

<div class="rodape" id="rodape"></div>

<footer class="cfg-docs">
 <span data-radai-frase>Documentos desta instala&ccedil;&atilde;o</span>
 <a href="/termos" data-radai-frase>Termos de uso</a>
 <a href="/politica-privacidade" data-radai-frase>Pol&iacute;tica de privacidade</a>
 <a href="/creditos" data-radai-frase>Cr&eacute;ditos e licen&ccedil;as</a>
 <a href="/procedencia" data-radai-frase>Proced&ecirc;ncia das estruturas</a>
</footer>



<script>
var DADOS=null;
function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;');}
function el(id){return document.getElementById(id);}
function msg(t,ok){var m=el('msg');m.textContent=t;m.style.color=ok?'var(--success,#5BC57F)':'var(--perigo,#E96A5C)';}

var VAZIO_SIGNIFICA={
 OUT_DIR: 'vazio = grava o RTSTRUCT ao lado da própria série',
 LOG_DIR: 'vazio = grava o log na pasta do acervo (calibracao)',
 STATUS_DIR: 'vazio = guarda o status junto do log'
};

var LIGADESLIGA={
};


function chave(k,v,ajuda){
 var on=['1','true','sim','yes','on','ligado'].indexOf(String(v).trim().toLowerCase())>=0;
 return '<label class="sw"><input id="f_'+k+'" type="checkbox"'+(on?' checked':'')
  +' data-bool="1"><span class="tr"></span><span class="lb">'+esc(ajuda)+'</span></label>';
}

function opcoes(k,v,pares){
 return '<select id="f_'+k+'">'+pares.map(function(p){
  return '<option value="'+esc(p[0])+'"'+(String(v).trim()===p[0]?' selected':'')+'>'+esc(p[1])+'</option>';
 }).join('')+'</select>';
}

function cfBarra(txt, tom){
 var b=el('cfBarra'); if(!b) return;
 b.className='cf-barra'+(tom?' '+tom:'');
 b.style.display='';
 if(window.uiHTML) uiHTML(b, txt); else b.innerHTML = txt;
}
function cfPintar(d, soProblemas){
 var r=el('cfRel'); if(!r) return;
 var h='';
 (d.secoes||[]).forEach(function(s){
  var itens = (s.itens||[]).filter(function(i){
   return !soProblemas || (i.ok!==true && !i.nota);
  });
  if(!itens.length) return;
  h+='<div class="cf-sec"><h4>'+esc(s.titulo)+'</h4>';
  itens.forEach(function(i){
   var cls = (i.ok===true) ? 'ok' : ((i.ok===false && i.grave) ? 'falta' : 'aviso');
   var m = (i.ok===true) ? '✓' : ((i.ok===false && i.grave) ? '✕' : '!');
   h+='<div class="cf-l '+cls+'"><span class="cf-m">'+m+'</span>'
     +'<span class="cf-n">'+esc(i.nome)+'</span>'
     +'<span class="cf-v">'+esc(i.valor||'')+'</span></div>';
   if(i.detalhe) h+='<div class="cf-d">'+esc(i.detalhe)+'</div>';
  });
  h+='</div>';
 });
 if(!h){ r.style.display='none'; return; }
 if(window.uiHTML) uiHTML(r, h); else r.innerHTML = h;
 r.style.display='';
}
function limpBarra(pct){
 var cor = pct >= 85 ? 'var(--perigo,#E96A5C)'
         : (pct >= 70 ? 'var(--aviso,#E1B23B)' : 'var(--ok,#12873F)');
 return '<div style="height:8px;border-radius:99px;overflow:hidden;'
  + 'background:var(--panel-2,#0f1729);margin:6px 0 10px">'
  + '<div style="height:100%;width:' + Math.min(100, pct) + '%;background:'
  + cor + '"></div></div>';
}

function diagnosticar(){
 var b = el('btDiag'); if(b) b.disabled = true;
 cfBarra('diagnosticando... o relatório vai para o log da barra da direita');
 var rr = el('cfRel'); if(rr) rr.style.display = 'none';
 try{
  if(window.radaiAbrirLog) window.radaiAbrirLog();
  else if(window.uiDireita) window.uiDireita('0');
 }catch(e){}
 fetch('/api/diagnosticar', {method:'POST'}).then(function(r){return r.json()})
 .then(function(d){
  if(b) b.disabled = false;
  if(d.erro){ cfBarra('ERRO: '+esc(d.erro), 'ruim'); return; }
  var q = d.resumo || {}, m = d.memoria || {};
  cfBarra('<b>'+(q.ok||0)+'</b> em ordem &middot; <b>'+(q.faltam||0)
   +'</b> faltando &middot; <b>'+(q.avisos||0)+'</b> avisos'
   +(m.total_mb ? (' &middot; <b>'+esc(m.livre_mb)+' MB</b> livres') : '')
   +' &middot; '+(d.segundos||0)+' s'
   +(m.total_mb ? limpBarra(m.pct||0) : ''),
   (q.faltam||0) ? 'ruim' : 'ok');
  cfPintar(d.conferencia || {}, true);
  if(m.total_mb){
   var st = el('subLimp');
   if(st && window.uiTexto) uiTexto(st, '— ' + m.livre_mb + ' MB livres');
   else if(st) st.textContent = '— ' + m.livre_mb + ' MB livres';
  }
  try{ if(window.radaiTfLog) window.radaiTfLog(); }catch(e){}
 }).catch(function(e){
  if(b) b.disabled = false;
  cfBarra('falhou: '+esc(''+e), 'ruim');
 });
}

function abrirPasta(){
 fetch('/api/desinstalar/pasta',{method:'POST'})
  .then(function(r){return r.json()})
  .then(function(d){ el('dsMsg').textContent = d.erro || d.pasta || ''; })
  .catch(function(e){ el('dsMsg').textContent = 'falhou: ' + e; });
}
function desinstalar(){
 var b = el('btDesinst');
 if(b.dataset.armado !== '1'){
  b.dataset.armado = '1';
  b.classList.add('perigo');
  b.textContent = 'Confirmar: fechar e abrir a remo\u00e7\u00e3o';
  el('dsMsg').textContent = 'O programa vai fechar. A remo\u00e7\u00e3o pede a '
   + 'palavra DESINSTALAR digitada, numa janela de comando.';
  return;
 }
 b.disabled = true;
 el('dsMsg').textContent = 'abrindo a ferramenta de remo\u00e7\u00e3o...';
 fetch('/api/desinstalar',{method:'POST'})
  .then(function(r){return r.json()})
  .then(function(d){
   if(d.erro){ b.disabled=false; el('dsMsg').textContent = d.erro; return; }
   el('dsMsg').textContent = 'A janela de remo\u00e7\u00e3o abriu. Fechando o programa...';
   fetch('/api/encerrar',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({modo:'tudo'})}).catch(function(){});
  })
  .catch(function(e){ b.disabled=false; el('dsMsg').textContent='falhou: '+e; });
}

function carregar(manter){fetch('/api/config').then(function(r){return r.json()}).then(function(d){
 var pintar = manter ? function(){} : faixa;
 DADOS=d; el('arq').textContent=d.caminho||'(nao definido)';
 if(!d.editavel){ el('campos').innerHTML='<div class="campo">Este processo nao expos a configuracao para edicao.</div>';
   el('btsalvar').disabled=true; return; }
 if((d.divergente||[]).length){
   pintar('O arquivo ja tem mudancas que o vigia em execucao ainda nao usa: <b>'
     +d.divergente.map(esc).join(', ')+'</b>. Clique em <b>Reiniciar agora</b>, aqui em cima.');
   el('btrei_cfg').style.display=''; }
 else pintar('');

 var html='';
 var campoDe={};
 (d.chaves||[]).forEach(function(k){
  var v = (d.valores[k]!==undefined) ? d.valores[k] : (d.padroes[k]||'');
  var campo;
  if(k==='DEVICE') campo=opcoes(k,v,[['auto','auto (recomendado)'],
                                     ['gpu','gpu'],['cpu','cpu']]);
  else if(LIGADESLIGA[k]) campo=chave(k,v,LIGADESLIGA[k]);
  else {
   var dica = VAZIO_SIGNIFICA[k] || '';
   campo='<input id="f_'+k+'" value="'+esc(v)+'" spellcheck="false"'
     +(dica?' placeholder="'+esc(dica)+'"':'')+'>';
  }
  campoDe[k]='<div class="campo"><label for="f_'+k+'">'
       +esc(k)+'</label>'+campo
       +'<div class="ajuda">'+esc(d.ajuda[k]||'')+'</div></div>';
 });

 montarGrupos(d, campoDe);
})}

function procCarregar(){
 var alvo = el('procLaudo');
 if(!alvo) return;
 alvo.innerHTML = '<p class="sub">consultando esta estação…</p>';
 fetch('/api/processamento').then(function(r){return r.json()}).then(function(d){
  var linhas = [];
  if(d.gpu){
   linhas.push(['GPU', d.gpu.nome + ' — ' + d.gpu.memoria_gb + ' GB'
     + (d.gpu.cuda ? (' · CUDA ' + d.gpu.cuda) : '')]);
  } else {
   linhas.push(['GPU', 'nenhuma disponível nesta estação']);
  }
  linhas.push(['CPU', (d.cpu && d.cpu.nucleos
    ? d.cpu.nucleos + ' <span data-radai-frase>núcleos</span>' : '—')]);
  linhas.push(['Vai usar', '<b>' + esc(d.resolve_em || '?') + '</b>'
    + (d.escolhido === 'auto'
       ? ' <span data-radai-frase>(o campo está em <code>auto</code>)</span>' : '')]);
  var cp = el('cst_processamento');
  if(cp) cp.textContent = 'DEVICE=' + (d.escolhido || 'auto') + ' \u2192 '
    + (d.resolve_em || '?');
  var h = '<div class="proc-laudo"><table>' + linhas.map(function(l){
   return '<tr><th>' + l[0] + '</th><td>' + l[1] + '</td></tr>' }).join('')
   + '</table>';
  if(d.estimativa && d.estimativa.texto){
   h += '<p class="sub" style="margin:8px 0 0 0">' + esc(d.estimativa.texto) + '</p>';
   if(d.estimativa.base){
    h += '<p class="sub" style="margin:2px 0 0 0;color:var(--text-dim);font-size:10.5px">'
      + esc(d.estimativa.base) + '</p>';
   }
   if(d.estimativa.recomendacao){
    h += '<p class="sub" style="margin:6px 0 0 0"><b>' + esc(d.estimativa.recomendacao) + '</b></p>';
   }
  }
  if(d.aviso){
   h += '<p class="aviso-inline">' + esc(d.aviso) + '</p>';
  }
  var r = d.recomendacao;
  if(r && r.device){
   h += '<div class="proc-rec' + (r.ja_esta ? ' ok' : '') + '">'
     + '<div class="rc-lin"><span class="rc-tag">recomendado</span>'
     + '<code>' + esc(r.device) + '</code>'
     + (r.ja_esta
        ? '<span class="rc-ja">esta estação já está neste valor</span>'
        : '<button type="button" class="btn peq" id="procAplicar">Usar este valor</button>')
     + '</div>'
     + '<p class="sub">' + esc(r.porque) + '</p>'
     + (r.ganho ? '<p class="sub rc-ganho">' + esc(r.ganho) + '</p>' : '')
     + (r.risco ? '<p class="sub rc-risco">' + esc(r.risco) + '</p>' : '')
     + '</div>';
  }
  alvo.innerHTML = h + '</div>';
  var bt = el('procAplicar');
  if(bt && r){
   bt.onclick = function(){
    var campo = el('f_DEVICE');
    if(!campo){ return }
    campo.value = r.device;
    campo.dispatchEvent(new Event('change', {bubbles:true}));
    campo.dispatchEvent(new Event('input', {bubbles:true}));
    campo.focus();
    bt.textContent = 'preenchido — falta salvar';
    bt.disabled = true;
   };
  }
 }).catch(function(e){
  alvo.innerHTML = '<p class="sub">não consegui consultar: ' + esc(e) + '</p>';
 });
}

function montarGrupos(d, campoDe){
 var FORA_DESTA_TELA=['ROOT','MODALITIES','DAYS_BACK'];
 var GRUPOS=[
  ['processamento', ['DEVICE']],
  ['ritmo', ['SCAN_EVERY_MIN','QUIET_MIN','MIN_SLICES','TIMEOUT_TASK_H',
             'TRAVA_SEM_PULSO_MIN','TRAVA_PAGINANDO_MIN','TRAVA_RAM_PCT',
             'MAX_RETRIES','LOCK_MAX_H','HEARTBEAT_MIN','LOCK_PARADO_MIN']],
  ['pastas', ['OUT_DIR','LOG_DIR','STATUS_DIR','PASTA_FAVORITA','PORT']]
 ];
 var usadas={};
 FORA_DESTA_TELA.forEach(function(k){usadas[k]=1});
 GRUPOS.forEach(function(g){
  var alvo=el('campos_'+g[0]); if(!alvo) return;
  var dentro=g[1].filter(function(k){return campoDe[k]});
  dentro.forEach(function(k){usadas[k]=1});
  var corpo = dentro.map(function(k){
   var c = campoDe[k];
   if(k === 'DEVICE') c += '<div id="procLaudo" class="larga"></div>';
   return c;
  }).join('');
  alvo.innerHTML = corpo || '<div class="campo" data-radai-frase>Nenhuma chave desta seção no arquivo desta estação.</div>';
  var sub=el('sub_'+g[0]);
  var _sh = '&#8212; ' + dentro.length + ' <span data-radai-frase>'
    + (dentro.length===1 ? 'chave' : 'chaves') + '</span>';
  if(sub){ if(window.uiHTML) window.uiHTML(sub, _sh); else sub.innerHTML = _sh }
 });
 var sobrando=(d.chaves||[]).filter(function(k){return !usadas[k] && campoDe[k]});
 el('campos').innerHTML = sobrando.length
   ? cardModulo(0, 'Outras', sobrando.length,
       sobrando.map(function(k){return campoDe[k]}).join(''))
   : '';
 var val=function(k){ var v=(d.valores||{})[k];
   return (v===undefined||v===null||v==='') ? (d.padroes||{})[k] : v; };
 var cr=el('cst_ritmo');
 if(cr) cr.textContent='SCAN_EVERY_MIN='+(val('SCAN_EVERY_MIN')||'?');
 var cp=el('cst_pastas');
 if(cp) cp.textContent='PORT='+(val('PORT')||'?');
 numerar();
 procCarregar();
 if(window.estFavoritaProcurar) window.estFavoritaProcurar();
 cfgFavoritaEstrela();
}

function cfgFavoritaEstrela(){
 var campo = el('f_PASTA_FAVORITA'), m = el('cfg_fav_molde');
 if(!campo || !m || !m.content || el('cfg_fav_estrela') || !window.uiFavoritaLigar) return;
 var b = m.content.firstElementChild;
 if(!b) return;
 b = b.cloneNode(true);
 b.id = 'cfg_fav_estrela';
 var depois = el('fav_procurar') || campo;
 depois.parentNode.insertBefore(b, depois.nextSibling);
 window.uiFavoritaLigar(b);
}

function cardModulo(n, titulo, qtd, campos){
 return '<section class="ps-cx fechado" id="ps_outras"' + (CFG_ATUAL === 'ps_pastas' ? '' : ' hidden') + '>'
  +'<h2 class="ps-cab" tabindex="0" role="button">'
  +'<span class="ps-num">'+n+'</span><span data-radai-frase>'+esc(titulo)+'</span>'
  +'<span class="ps-sub">&#8212; '+qtd+' <span data-radai-frase>'+(qtd===1?'chave':'chaves')+'</span></span>'
  +'<span class="ps-seta">&#9662;</span></h2>'
  +'<div class="ps-corpo"><div class="campos">'+campos+'</div></div></section>';
}

function numerar(){
 var numeros = document.querySelectorAll('.ps-num');
 for(var i=0;i<numeros.length;i++) numeros[i].textContent = i+1;
 var cartoes = document.querySelectorAll('a.cfg-card[data-alvo]');
 for(var j=0;j<cartoes.length;j++){
  var s = el(cartoes[j].getAttribute('data-alvo'));
  var n = s ? s.querySelector('.ps-num') : null;
  var alvo = cartoes[j].querySelector('.n');
  if(n && alvo) alvo.textContent = n.textContent;
 }
}

var CFG_ATUAL = '';
var CFG_COM_SALVAR = {ps_processamento:1, ps_ritmo:1, ps_pastas:1};
function cfgMostrar(id){
 var s = id ? el(id) : null;
 if(id && !s) return false;
 CFG_ATUAL = s ? id : '';
 Array.prototype.forEach.call(document.querySelectorAll('section.ps-cx'), function(x){
  x.hidden = !s || (x !== s && !(x.id === 'ps_outras' && id === 'ps_pastas'));
 });
 var av = el('cfgAviso'); if(av) av.hidden = !CFG_COM_SALVAR[CFG_ATUAL];
 Array.prototype.forEach.call(document.querySelectorAll('a.cfg-card[data-alvo]'), function(c){
  if(c.getAttribute('data-alvo') === CFG_ATUAL) c.setAttribute('aria-current', 'true');
  else c.removeAttribute('aria-current');
 });
 if(s && window.psAbrir) window.psAbrir(id); else if(s) s.classList.remove('fechado');
 return !!s;
}
window.cfgMostrar = cfgMostrar;
function cfgPeloEndereco(){
 var h = (location.hash || '').replace(/^#/, '');
 if(h && el(h) && el(h).classList.contains('ps-cx')) cfgMostrar(h);
}
window.addEventListener('hashchange', cfgPeloEndereco);
cfgPeloEndereco();
document.addEventListener('click', function(ev){
 var a = ev.target.closest && ev.target.closest('a.cfg-card[data-alvo]');
 if(!a) return;
 var id = a.getAttribute('data-alvo'), s = el(id);
 if(!s) return;
 ev.preventDefault();
 cfgMostrar(id);
 medirTopo();
 if(window.psAbrir) window.psAbrir(id, true); else s.classList.remove('fechado');
 var calmo = window.matchMedia
   && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
 s.scrollIntoView({block:'start', behavior: calmo ? 'auto' : 'smooth'});
 try{ history.replaceState(null, '', '#' + id) }catch(e){}
});
function medirTopo(){
 var t = document.querySelector('.topo');
 if(!t) return;
 var fixo = getComputedStyle(t).position === 'sticky';
 var fundo = fixo ? Math.max(0, t.getBoundingClientRect().bottom) : 0;
 document.documentElement.style.setProperty('--cfg-topo',
   Math.round(fundo + 12) + 'px');
}
window.addEventListener('resize', medirTopo);
medirTopo();


function faixa(html,tom){
 var f=el('faixa');
 if(!html){ f.style.display='none'; f.innerHTML=''; return; }
 f.className='faixa'+(tom==='ok'?' ok':'');
 f.style.display='block'; f.innerHTML=html;
}

function recarregar(){
 var b=el('btrei_cfg'); b.disabled=true; b.textContent='recarregando...';
 fetch('/api/reiniciar',{method:'POST'}).then(function(r){return r.json()}).then(function(d){
  b.disabled=false; b.innerHTML='&#8635; Reiniciar agora';
  if(!d.ok){ faixa('Nao consegui recarregar: '+esc(d.erro||'')); return; }
  var extra=(d.so_reabrindo||[]).length
   ? ' <b>'+d.so_reabrindo.map(esc).join(', ')+'</b> so vale fechando e reabrindo o programa.' : '';
  faixa('Recarga pedida — vai valer '+esc(d.quando||'em instantes')+'.'+extra,
        extra?'':'ok');
  msg(''); b.style.display='none';
 }).catch(function(e){ b.disabled=false; b.innerHTML='&#8635; Reiniciar agora';
  faixa('ERRO: '+esc(''+e)); });
}

function regFalha(txt){
 var m = el('reg_msg'); if(!m) return;
 var h = '<span>não consegui ler o registro de casos:</span> <code>'
   + esc(txt) + '</code>';
 if(window.uiHTML) uiHTML(m, h); else m.innerHTML = h;
}
function regEstado(){
 fetch('/api/registro').then(function(r){return r.json()}).then(function(d){
  var n = el('reg_n'), c = el('cst_registro');
  if(n) n.textContent = d.erro ? '?' : String(d.casos||0);
  if(c) c.textContent = d.erro ? '?' : String(d.casos||0);
  if(d.erro) regFalha(d.erro);
  else if(d.aviso){
   var m = el('reg_msg');
   if(m && window.uiTexto) uiTexto(m, d.aviso); else if(m) m.textContent = d.aviso;
   try{ if(window.radaiRetraduzir) window.radaiRetraduzir() }catch(e){}
  }
  var p = el('reg_papel');
  if(p && d.papel) p.value = d.papel;
 }).catch(function(e){
  var n = el('reg_n'); if(n) n.textContent = '?';
  regFalha(String(e));
 });
}
function regExportar(){
 var bt = el('reg_bt');
 var m = el('reg_msg');
 bt.disabled = true;
 if(window.uiTexto) uiTexto(m, 'conferindo e empacotando');
 else m.textContent = 'conferindo e empacotando';
 fetch('/api/registro/exportar', {method:'POST',
   headers:{'Content-Type':'application/json'},
   body: JSON.stringify({papel: el('reg_papel').value,
                         nota: el('reg_nota').value})})
 .then(function(r){return r.json()}).then(function(d){
  bt.disabled = false;
  if(!d.ok){ m.textContent = (d.avisos||[]).join(' | ') || 'falhou';
             return; }
  var h = '<b>'+esc(d.casos)+'</b> <span>caso(s) no pacote</span> &middot; '
    +esc(d.tamanho_kb)+' KB<br><code>'+esc(d.arquivo)+'</code>';
  if(d.recusados && d.recusados.length)
   h += '<br><b>'+d.recusados.length+'</b> <span>caso(s) ficaram de fora: a conferência recusou</span>';
  if(window.uiHTML) uiHTML(m, h); else m.innerHTML = h;
  regEstado();
 }).catch(function(e){ bt.disabled=false; m.textContent='falhou: '+e; });
}
function regRelatorio(){
 var bt = el('reg_rel_bt');
 var m = el('reg_msg');
 bt.disabled = true;
 if(window.uiTexto) uiTexto(m, 'montando o relatório do período');
 else m.textContent = 'montando o relatório do período';
 fetch('/api/registro/relatorio', {method:'POST',
   headers:{'Content-Type':'application/json'}, body: '{}'})
 .then(function(r){return r.json()}).then(function(d){
  bt.disabled = false;
  if(!d.ok){ m.textContent = (d.avisos||[]).join(' | ') || 'falhou';
             return; }
  var h = '<b>'+esc(d.casos)+'</b> <span>caso(s) no relatório</span><br><code>'
    +esc(d.html)+'</code><br><code>'+esc(d.md)+'</code>';
  if(window.uiHTML) uiHTML(m, h); else m.innerHTML = h;
 }).catch(function(e){ bt.disabled=false; m.textContent='falhou: '+e; });
}
regEstado();

function regFrase(pt){
 try{ return window.radaiFrase ? window.radaiFrase(pt) : pt }
 catch(e){ return pt }
}
function regResumo(){
 var bt = el('reg_resumo_bt'), pre = el('reg_resumo');
 bt.disabled = true;
 fetch('/api/registro/resumo').then(function(r){return r.json()})
 .then(function(d){
  bt.disabled = false;
  var t = (d && d.texto) || '';
  pre.textContent = t;
  if(t && navigator.clipboard){ navigator.clipboard.writeText(t)
    .catch(function(){}) }
 }).catch(function(e){ bt.disabled = false;
   if(window.uiTexto) uiTexto(pre, '—'); else pre.textContent = '—'; });
}
function filaFalhas(){
 fetch('/api/status').then(function(r){return r.json()}).then(function(d){
  var cx = el('fila_falhas'), tx = el('fila_falhas_txt');
  if(!cx || !tx) return;
  var partes = [];
  (d.alertas_de_assinatura || []).forEach(function(a){
   partes.push(regFrase('em espera: a mesma falha em %d séries')
     .replace('%d', String(a.series || 0)) + ' — ' + (a.frase || ''));
  });
  if(d.nao_contornaveis){
   partes.push(regFrase('Não contornável') + ': ' + d.nao_contornaveis);
  }
  (d.em_espera_grupos || []).forEach(function(g){
   if((d.alertas_de_assinatura || []).some(function(a){
     return a.assinatura === g.assinatura })) return;
   partes.push(regFrase('em espera: a mesma falha em %d séries')
     .replace('%d', String(g.series || 0)) + ' — ' + (g.frase || ''));
  });
  cx.hidden = !partes.length;
  if(window.uiTexto) uiTexto(tx, partes.join(' | '));
  else tx.textContent = partes.join(' | ');
 }).catch(function(){});
}
function filaLiberar(){
 var bt = el('fila_liberar_bt');
 bt.disabled = true;
 fetch('/api/liberar_falhas', {method:'POST'}).then(function(){
  bt.disabled = false; filaFalhas();
 }).catch(function(){ bt.disabled = false; });
}
filaFalhas();
[1200, 3500, 7000].forEach(function(ms){ setTimeout(filaFalhas, ms) });
setInterval(filaFalhas, 15000);

function salvar(){
 if(!DADOS) return;
 var vals={};
 (DADOS.chaves||[]).forEach(function(k){
  var e=el('f_'+k); if(!e) return;
  vals[k] = e.getAttribute('data-bool') ? (e.checked?'1':'0') : e.value;
 });
 msg('salvando...',true);
 fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},
  body:JSON.stringify({valores:vals})})
 .then(function(r){return r.json()}).then(function(d){
  if(d.precisa_confirmar){
   faixa('O ROOT n\u00e3o se grava por esta tela: a pasta que o vigia varre se escolhe no Overnight Run, no \u00abRodar agora\u00bb.');
   msg('',true); return;
  }
  if(d.nada_mudou){ msg('Nada mudou.',true); faixa(''); return; }
  if(d.ok){
   msg('');
   el('btrei_cfg').style.display='';
   carregar(true);
   faixa('Gravado no arquivo: <b>'+(d.salvos||[]).map(esc).join(', ')+'</b>. '
     +'O vigia em execucao ainda usa os valores antigos — clique em '
     +'<b>Reiniciar agora</b>, ao lado, para aplicar.');
  }
  else faixa('ERRO: '+esc(d.erro||'nao consegui gravar'));
 }).catch(function(e){faixa('ERRO: '+esc(''+e));});
}

carregar();

(function(){
 fetch('/api/painel').then(function(r){return r.json()}).then(function(d){
  var g=d.geom||{}, ac=d.acervo||{}, v=(d.vigia||{}), pes=[];
  pes.push(g.ok ? 'Biblioteca de geometria: v%s carregada.'.replace('%s', esc(g.versao))
    : '<span style="color:var(--perigo,#E96A5C)">Biblioteca de geometria NAO carrega: '
      +esc(g.erro)+' — o pos-processamento nao vai funcionar neste runtime.</span>');
  pes.push('Acervo: <code>'+esc(ac.raiz)+'</code>'
    +(ac.existe?'':' (ainda nao criado — nasce na primeira serie concluida)'));
  if(ac.erro) pes.push('<span style="color:var(--perigo,#E96A5C)">Erro lendo o acervo: '
    +esc(ac.erro)+'</span>');
  var ent=(d.entrega||{});
  if(ent.rotulo) pes.push('<b>'+esc(ent.rotulo)+'</b>');
  pes.push(v.versao
    ? 'painel v%s · vigia v%s'.replace('%s', esc(d.versao_painel)).replace('%s', esc(v.versao))
    : 'painel v' + esc(d.versao_painel));
  var r=el('rodape'); if(r) r.innerHTML=pes.join('<br>');
 }).catch(function(){});
})();

function pintarTema(){
 var t = uiTema();
 var v = (typeof uiTemaEscolha === 'function') ? uiTemaEscolha() : t;
 var _tm = (v==='sistema' ? 'tema do sistema' : (t==='claro' ? 'modo claro' : 'modo escuro'));
 var e = el('subTema');
 if(e){ var _h = '&#8212; <span data-radai-frase>' + _tm + '</span>';
  if(window.uiHTML) window.uiHTML(e, _h); else e.innerHTML = _h }
 var c = el('cst_geral');
 if(c){ if(window.uiTexto) window.uiTexto(c, _tm); else c.textContent = _tm }
}
window.addEventListener('radai-tema', function(){ pintarTema() });
// GUARDA: se a folha do sistema nao foi costurada (instalacao sem
// radai_ui), a tela ainda abre -- so sem seletor de tema.
if(typeof uiTema === 'function') pintarTema();
</script>@JS_ESTACAO@</body></html>"""


PAGINA = PAGINA.replace(u"@CSS_REGISTRO@", CSS_REGISTRO)
PAGINA_CONFIG = PAGINA_CONFIG.replace(u"@CSS_REGISTRO@", CSS_REGISTRO)


_ICONES_CFG = {
    u"geral": u'<path d="M4 7h9M17 7h3M4 17h3M11 17h9"/>'
              u'<circle cx="15" cy="7" r="2"/><circle cx="9" cy="17" r="2"/>',
    u"processamento": u'<rect x="7" y="7" width="10" height="10" rx="1.5"/>'
                      u'<path d="M10 3.5V7M14 3.5V7M10 17v3.5M14 17v3.5'
                      u'M3.5 10H7M3.5 14H7M17 10h3.5M17 14h3.5"/>',
    u"ritmo": u'<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
    u"pastas": u"ui:pasta",
    u"estruturas": u'<path d="M3.5 12.2V4.5a1 1 0 0 1 1-1h7.7l8.3 8.3a1 1 0 0 1 0 1.4'
                   u'l-7.3 7.3a1 1 0 0 1-1.4 0z"/><circle cx="8.3" cy="8.3" r="1.6"/>',
    u"atualizar": u'<path d="M19.5 12a7.5 7.5 0 1 1-2.2-5.3"/>'
                  u'<path d="M19.5 4.5v4h-4"/>',
    u"diagnosticar": u'<path d="M3 12h4l2.5-6 5 12 2.5-6H21"/>',
    u"desinstalar": u'<path d="M4.5 7h15M9.5 7V4.5h5V7M6.5 7l1 12.5h9l1-12.5'
                    u'M10.5 11v5M13.5 11v5"/>',
}


def _com_icones_cfg(pagina):
    try:
        import radai_ui
        svg = radai_ui._SVG
    except Exception:
        radai_ui, svg = None, None
    for nome, tracos in _ICONES_CFG.items():
        marca = u"@CFG_ICO_%s@" % nome.upper()
        if marca not in pagina:
            continue
        if svg is None:
            desenho = u""
        elif tracos.startswith(u"ui:"):
            desenho = radai_ui.icone(tracos[3:])
        else:
            desenho = svg % tracos
        pagina = pagina.replace(marca, desenho)
    return pagina


PAGINA_CONFIG = _com_icones_cfg(PAGINA_CONFIG)


def _com_estacao(pagina):
    try:
        import radai_config_estacao
        return radai_config_estacao.aplicar(pagina)
    except Exception:
        for marca in (u"@GERAL_ESTACAO@", u"@SECAO_ESTRUTURAS@",
                      u"@CSS_ESTACAO@", u"@JS_ESTACAO@"):
            pagina = pagina.replace(marca, u"")
        return pagina


PAGINA_CONFIG = _com_estacao(PAGINA_CONFIG)


def _com_favorita(pagina):
    try:
        import radai_ui
        estrela = radai_ui.botao_favorita(u"f_PASTA_FAVORITA")
    except Exception:
        estrela = u""
    return pagina.replace(u"@FAV_CFG@", estrela)


PAGINA_CONFIG = _com_favorita(PAGINA_CONFIG)


PAGINA_LOG = u"""<!doctype html><html><head><meta charset="utf-8">
<title>Diagnóstico · Radioterapia.AI</title><style>
:root{--bg-0:var(--bg-0,#060d1a);--bg-1:var(--bg-1,#0a1120);--panel:var(--panel,#0c1322);--panel-2:var(--panel-2,#0f1729);--line:var(--line,#1e293b);
--line-strong:var(--line-strong,#2a3a55);--text:var(--text,#e6edf7);--text-muted:var(--text-muted,#a3b1c6);--text-dim:var(--text-dim,#72829b);
--accent:var(--accent,#4DA3FF);--success:#5BC57F;--warn:#E1B23B;--error:var(--perigo,#E96A5C);--r-md:10px;
--font-display:'Inter',system-ui,'Segoe UI',Arial,sans-serif;
--font-mono:'JetBrains Mono',ui-monospace,Consolas,monospace}
*{box-sizing:border-box}
html,body{background:var(--bg-0);color:var(--text);font-family:var(--font-display);margin:0}
.wrap{max-width:1320px;margin:0 auto;padding-bottom:30px}
.rt-topbar{display:flex;align-items:center;justify-content:space-between;padding:16px 28px;
border-bottom:1px solid var(--line);background:var(--bg-1)}
.rt-logo{font-size:15px;font-weight:700}.rt-logo .ai{color:var(--accent)}
a.rt-gear{text-decoration:none;color:var(--text-muted);background:var(--panel);
border:1px solid var(--line);border-radius:var(--r-md);padding:7px 12px;font-size:12px}
a.rt-gear:hover{color:var(--text)}
h1{font-size:24px;margin:22px 28px 4px;font-weight:800;letter-spacing:-0.02em}
.sub{color:var(--text-muted);font-size:13px;margin:0 28px 12px;line-height:1.5}
.cx{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px;
margin:0 28px 12px}
.cx h2{font-size:12px;margin:0 0 10px;color:var(--accent);text-transform:uppercase;
letter-spacing:.5px;font-family:var(--font-mono)}
table{width:100%;border-collapse:collapse;font-size:12px;font-family:var(--font-mono)}
td,th{padding:4px 7px;border-bottom:1px solid var(--line);text-align:left;
vertical-align:top;word-break:break-all}
td:first-child{color:var(--text-dim);width:210px;white-space:nowrap}
.ok{color:var(--success)}.warn{color:var(--warn)}.err{color:var(--error)}
#log{background:var(--bg-0,#060d1a);border:1px solid var(--line);border-radius:var(--r-md);padding:10px;
height:520px;overflow:auto;font-family:var(--font-mono);font-size:11px;color:var(--text-muted,#a3b1c6);
white-space:pre-wrap;line-height:1.5}
.linha{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:8px}
input,select{background:var(--panel-2);color:var(--text);border:1px solid var(--line);
border-radius:var(--r-md);padding:7px 9px;font-size:12px;font-family:var(--font-mono)}
input#filtro{flex:1;min-width:200px}
button{background:var(--panel-2);color:var(--text);border:1px solid var(--line-strong);
border-radius:var(--r-md);padding:7px 12px;font-size:12px;cursor:pointer}
label.chk{font-size:12px;color:var(--text-muted);display:flex;align-items:center;gap:5px}
</style></head><body><div class="wrap">
<div class="rt-topbar">
 <div class="rt-logo">&#9762; radioterapia<span class="ai">.ai</span> · Diagnóstico</div>
 <div><a class="rt-gear" href="/config">&#9881; Configurações</a>
  <a class="rt-gear" href="/">&#8592; Menu</a></div>
</div>

<header class="rc-topo"><a class="rc-marca" href="/" title="Radioterapia.AI Local"><span class="rc-nome">radioterapia<span class="g">.ai</span></span><span class="rc-sub" data-radai-frase>Local Suite</span></a><span class="rc-seta">&#8594;</span><span class="rc-tela">Diagnóstico</span><div class="dir"><a class="rc-voltar" href="/">&#8592; Voltar ao menu</a></div></header>
<div class="rc-capa rc-compacta">
 <span class="rc-chip"><i>@ICO_DUVIDA@</i> <span data-radai-frase>Suporte</span></span>
 <h1>Diagnóstico</h1>
 <p class="rc-frase">Tudo que o programa sabe sobre si mesmo, num lugar só.</p></div>
<p class="rc-nota" style="text-align:left"><b>Primeira tela a olhar</b> quando algo
 sai diferente — e a que dá para copiar inteira e mandar junto com o relato.</p>

<div class="cx">
 <h2>Log do vigia</h2>
 <div class="linha">
  <input id="filtro" placeholder="filtrar (ex.: VISTA, FALHOU, serie)" oninput="pinta()">
  <label class="chk"><input type="checkbox" id="auto" checked> atualizar sozinho</label>
  <label class="chk"><input type="checkbox" id="fim" checked> rolar para o fim</label>
  <button onclick="copiar()">Copiar tudo</button>
  <button onclick="carregar()">Recarregar o log</button>
 </div>
 <div id="log"></div>
 <div class="sub" id="logmeta" style="margin:8px 0 0"></div>
</div>

<div class="cx">
 <h2>Ambiente</h2>
 <table id="amb"></table>
</div>

<div class="cx">
 <h2>Configuração em uso</h2>
 <div class="sub" style="margin:0 0 8px">O que ESTE processo carregou no arranque. Se o
 arquivo mudou depois, a página inicial avisa.</div>
 <table id="cfg"></table>
</div>

<script>
var LINHAS=[];
function el(i){return document.getElementById(i)}
function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;')}
function linhas(obj){return Object.keys(obj||{}).map(function(k){
 var v=obj[k], cls='';
 if(v===true||String(v)==='OK') cls='ok';
 if(v===false) cls='warn';
 if(String(v).toLowerCase().indexOf('erro')>=0||String(v).toLowerCase().indexOf('falta')>=0) cls='err';
 return '<tr><td>'+esc(k)+'</td><td class="'+cls+'">'+esc(v)+'</td></tr>'}).join('')}

function carregar(){fetch('/api/diagnostico').then(function(r){return r.json()}).then(function(d){
 LINHAS=d.log||[];
 el('amb').innerHTML=linhas(d.ambiente);
 el('cfg').innerHTML=linhas(d.config);
 el('logmeta').textContent=(d.log||[]).length+' linha(s) em memória · arquivo: '+(d.arquivo||'—')
  +(d.bytes_arquivo?(' ('+Math.round(d.bytes_arquivo/1024)+' KB)'):'');
 pinta();
})}

function pinta(){
 var f=(el('filtro').value||'').toLowerCase();
 var t=LINHAS.filter(function(l){return !f || l.toLowerCase().indexOf(f)>=0});
 var lg=el('log');
 lg.textContent=t.join('\\n');
 if(el('fim').checked) lg.scrollTop=lg.scrollHeight;
}
function copiar(){
 var t=el('log').textContent;
 if(navigator.clipboard){navigator.clipboard.writeText(t)}
 else{var a=document.createElement('textarea');a.value=t;document.body.appendChild(a);
  a.select();document.execCommand('copy');a.remove()}
}
setInterval(function(){if(el('auto').checked) carregar()},3000);
carregar();
</script></div></body></html>"""




DISTRIBUICAO = {"totalsegmentator": "TotalSegmentator", "rt_utils": "rt-utils",
                "pkg_resources": "setuptools", "PIL": "Pillow"}


def versao_da_biblioteca(nome, modulo=None):
    try:
        from importlib import metadata
        v = metadata.version(DISTRIBUICAO.get(nome, nome))
        if v:
            return str(v)
    except Exception:
        pass
    v = getattr(modulo, "__version__", None)
    return v if isinstance(v, str) and v else u""


def diagnostico(ler_vigia=None, config=None):
    import os
    import platform
    import sys

    cfg = dict(config or {})
    vigia = {}
    if ler_vigia is not None:
        try:
            vigia = ler_vigia() or {}
        except Exception as e:
            vigia = {"erro": "%s: %s" % (type(e).__name__, e)}

    amb = {
        "maquina": vigia.get("machine", ""),
        "versao do vigia": vigia.get("versao", ""),
        "versao do painel": VERSAO_PAINEL,
        "python": "%s (%s)" % (platform.python_version(), sys.executable),
        "sistema": platform.platform(),
        "estado do vigia": ("PAUSADO" if vigia.get("paused") else
                            ("SEM RESPOSTA" if vigia.get("saudavel") is False else "rodando")),
        "modo simulacao (DRY_RUN)": bool(vigia.get("dry_run")),
        "ROOT": vigia.get("root") or "(vazio — nao varre nada)",
        "ambiente do motor": vigia.get("ambiente_erro") or "OK",
        "series puladas por falha": vigia.get("puladas", 0),
        "arquivo de log": vigia.get("log") or "(o vigia ainda nao abriu o log)",
    }
    try:
        g = estado_geom()
        amb["radai_geom"] = ("v%s" % g["versao"]) if g["ok"] else ("ERRO: " + g["erro"])
    except Exception as e:
        amb["radai_geom"] = "ERRO: %s" % e
    for nome in ("numpy", "scipy", "SimpleITK", "rt_utils", "pydicom",
                 "torch", "monai", "totalsegmentator", "nnunetv2"):
        try:
            m = __import__(nome)
        except Exception:
            amb["lib " + nome] = "FALTA"
            continue
        amb["lib " + nome] = (versao_da_biblioteca(nome, m)
                              or "importa, versao desconhecida")
    try:
        __import__("engine")
        amb["motor (engine)"] = "importa"
    except Exception:
        amb["motor (engine)"] = "FALTA"
    try:
        amb["pesos TotalSegmentator"] = os.environ.get("TOTALSEG_WEIGHTS_PATH") or "(padrao)"
        import radai_models
        ev = radai_models.estado()
        amb["pasta de modelos"] = ev["raiz"]
        for m in ev["modelos"]:
            amb["modelo " + m["id"]] = ("instalado" if m["instalado"]
                                        else "NAO instalado (%s)" % (", ".join(m["faltando"][:2]) or "sem rota"))
    except Exception as e:
        amb["acervo de modelos"] = "ERRO: %s" % str(e)[:120]
    try:
        ac = radai_archive.estado()
        amb["acervo"] = ac["raiz"]
        amb["series no acervo"] = ac["series"]
        amb["comparacoes no acervo"] = ac.get("comparacoes", 0)
    except Exception as e:
        amb["acervo"] = "ERRO: %s" % str(e)[:120]

    try:
        import radai_prerequisites
        pr = radai_prerequisites.conferir()
        amb["--- esta maquina ---"] = ""
        for k, v in (pr or {}).items():
            if isinstance(v, (dict, list)):
                continue
            amb["maquina: " + str(k)] = v
    except Exception as e:
        amb["pre-requisitos"] = "ERRO: %s" % str(e)[:120]

    try:
        import radai_version
        lv = radai_version.conferir(vigia.get("versao") or VERSAO_PAINEL)
        for k, v in (lv.get("fontes") or {}).items():
            amb["versao: " + k] = v or "-"
        for i, a in enumerate(lv.get("avisos") or [], 1):
            amb["versao: aviso %d" % i] = a
    except Exception as e:
        amb["versoes"] = "ERRO: %s" % str(e)[:120]

    conf = {}
    try:
        _, disco = radai_config.ler_arquivo(cfg.get("caminho", ""))
        conf["arquivo"] = cfg.get("caminho", "")
        for k in (cfg.get("chaves") or []):
            conf[k] = _em_uso(cfg).get(k, disco.get(k, ""))
        mudou = divergencias(cfg)
        if mudou:
            conf["!! mudou no arquivo e o processo ainda nao usa"] = ", ".join(mudou)
        so_turno = temporarias(cfg)
        if so_turno:
            conf["!! so deste turno, sem gravar no arquivo"] = ", ".join(so_turno)
    except Exception as e:
        conf["erro"] = str(e)[:200]

    arquivo, bytes_arq = "", 0
    try:
        arquivo = str(vigia.get("log_arquivo") or "")
        if arquivo and os.path.isfile(arquivo):
            bytes_arq = os.path.getsize(arquivo)
    except Exception:
        pass

    return {"log": list(vigia.get("log") or []), "ambiente": amb, "config": conf,
            "arquivo": arquivo, "bytes_arquivo": bytes_arq}


def resumo_do_registro(base=""):
    r = {"casos": 0, "primeiro": "", "ultimo": "", "tamanho_kb": 0.0,
         "pasta": "", "papel": "", "erro": ""}
    try:
        import radai_records as RG
        casos = RG.listar_casos(base)
        praiz = RG.raiz(base)
        tam = 0
        for raiz_, _, arqs in os.walk(praiz):
            for a in arqs:
                try:
                    tam += os.path.getsize(os.path.join(raiz_, a))
                except OSError:
                    pass
        papel = ""
        try:
            import json as _j
            with open(os.path.join(praiz, "estacao.json"), encoding="utf-8") as f:
                papel = (_j.load(f) or {}).get("papel_declarado") or ""
        except (OSError, ValueError):
            pass
        r.update({"casos": len(casos), "pasta": praiz,
                  "primeiro": (casos[0][:10] if casos else ""),
                  "ultimo": (casos[-1][:10] if casos else ""),
                  "tamanho_kb": round(tam / 1024.0, 1), "papel": papel})
    except Exception as e:
        r["erro"] = "%s: %s" % (type(e).__name__, str(e)[:200])
    return r


def linhas_do_registro_para_arranque(base=""):
    import unicodedata
    r = resumo_do_registro(base)
    if r["erro"]:
        s = u"registro de casos: nao lido (%s)" % r["erro"]
    else:
        s = (u"registro de casos: %d caso(s)%s | %.1f MB | papel declarado: %s | "
             u"pasta: %s | o pacote para enviar sai em Configuracoes"
             % (r["casos"],
                (u" de %s a %s" % (r["primeiro"], r["ultimo"])) if r["casos"] else u"",
                r["tamanho_kb"] / 1024.0, r["papel"] or u"nao declarado",
                r["pasta"]))
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return [s]


def montar(app, ler_vigia=None, config=None):
    from fastapi import Request
    from fastapi.responses import HTMLResponse

    cfg = dict(config or {})
    caminho = cfg.get("caminho") or ""
    chaves = [k for k in (cfg.get("chaves") or []) if k not in FORA_DA_TELA]
    padroes = dict(cfg.get("padroes") or {})
    modelo = cfg.get("modelo") or u""
    registrar = cfg.get("registrar")
    recarregar = cfg.get("recarregar")

    if caminho:
        try:
            import radai_primeiro_uso
            radai_primeiro_uso.montar(app, caminho, modelo=modelo,
                                      registrar=registrar,
                                      recarregar=recarregar)
        except Exception:
            pass
        try:
            import radai_config_estacao
            radai_config_estacao.montar(
                app, caminho, chaves=list(cfg.get("chaves") or []),
                modelo=modelo, registrar=registrar,
                versao=lambda: _carimbo_entrega().get("versao") or u"")
        except Exception as e:
            _MONTAGEM["radai_config_estacao"] = "%s: %s" % (type(e).__name__,
                                                            str(e)[:200])

    @app.post("/api/pastas")
    async def _api_pastas(request: Request):
        try:
            c = await request.json() or {}
        except Exception:
            c = {}
        return radai_config.listar_pastas(str(c.get("caminho") or ""),
                                          str(c.get("arquivos") or ""),
                                          str(c.get("busca") or ""))

    def _log_do_vigia(msg):
        try:
            if registrar:
                registrar(msg)
        except Exception:
            pass

    def _raiz_e_porta():
        try:
            vg = (ler_vigia() or {}) if ler_vigia else {}
            return (str(vg.get("root") or ""),
                    int(vg.get("port") or vg.get("porta") or 0))
        except Exception:
            return "", 0

    @app.post("/api/diagnosticar")
    async def _api_diagnosticar():
        def _fazer():
            import time as _t
            t0 = _t.time()
            raiz, porta = _raiz_e_porta()
            cf, ld, eu = {}, {}, {}
            try:
                import radai_station_check as CE
                cf = CE.conferir(root=raiz or "", porta=porta or 0)
            except Exception as e:
                _log_do_vigia("diagnostico: a conferencia da instalacao nao "
                              "rodou (%s: %s)" % (type(e).__name__, e))
            try:
                import radai_cleaner as LP
                ld = LP.laudo()
                eu = LP.ler_em_uso()
                for linha in LP.linhas_do_diagnostico(cf, ld, eu):
                    _log_do_vigia(linha)
            except Exception as e:
                return {"erro": "%s: %s" % (type(e).__name__, e)}
            return {"ok": True, "resumo": cf.get("resumo") or {},
                    "conferencia": cf, "memoria": ld.get("memoria") or {},
                    "segundos": round(_t.time() - t0, 1)}
        return await radai_web.no_threadpool(_fazer)

    @app.post("/api/desinstalar/pasta")
    def _api_desinst_pasta():
        import subprocess
        alvo = os.path.dirname(os.path.abspath(
            os.path.join(os.path.dirname(__file__), "radai_watcher.py")))
        if not os.path.isdir(alvo):
            return {"erro": "nao achei a pasta do programa"}
        try:
            subprocess.Popen(["explorer.exe", alvo])
        except Exception as e:
            return {"erro": "%s: %s" % (type(e).__name__, e)}
        return {"pasta": alvo}

    @app.post("/api/desinstalar")
    def _api_desinstalar():
        import subprocess

        aqui = os.path.dirname(os.path.abspath(__file__))
        ps1 = ""
        for pasta in ("maintenance", "ferramentas", ""):
            cand = os.path.join(aqui, pasta, "UNINSTALL.ps1")
            if os.path.isfile(cand):
                ps1 = cand
                break
        if not ps1:
            ps1 = os.path.join(aqui, "UNINSTALL.ps1")
        if not os.path.isfile(ps1):
            return {"erro": "esta instalacao nao tem o UNINSTALL.ps1 "
                            "(e anterior a ele). Apague a pasta a mao: %s"
                            % aqui}
        try:
            subprocess.Popen(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                 "-File", ps1, "-EsperarFechar", "30"],
                cwd=aqui,
                creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0))
        except Exception as e:
            return {"erro": "%s: %s" % (type(e).__name__, e)}

        return {"ok": True, "pasta": aqui}

    @app.post("/api/reiniciar")
    def _api_reiniciar():
        if not recarregar:
            return {"ok": False, "erro": "este processo nao expos a recarga"}
        try:
            r = recarregar() or {}
        except Exception as e:
            return {"ok": False, "erro": "%s: %s" % (type(e).__name__, e)}
        resposta = {"ok": True, "so_reabrindo": so_reabrindo(cfg)}
        resposta.update(r)
        return resposta

    @app.get("/autocontorno", response_class=HTMLResponse)
    def _inicio():
        return _costurar_home(pagina_inicial())

    @app.get("/api/painel")
    def _api_painel():
        return estado(ler_vigia, cfg)

    for nome in ("radai_todo", "radai_models",
                 "radai_consent", "radai_batch",
                 "radai_viewseg", "radai_view", "radai_bibliography",
                 "radai_router",
                 "radai_bridge", "radai_recon3d_screen",
                 "radai_elastic_screen",
                 "radai_bolus_screen",
                 "radai_provenance_screen",
                 "radai_queue_state",
                 "radai_tabela_acervo",
                 "radai_janela", "radai_roteiro", "radai_atualizar",
                 "radai_varrer"):
        if not _tem_modulo(nome):
            continue
        try:
            mod = __import__(nome)
            if hasattr(mod, "montar"):
                if nome == "radai_batch":
                    mod.montar(app, cfg.get("lote"))
                elif nome == "radai_todo":
                    mod.montar(app, ler_vigia)
                elif nome == "radai_provenance_screen":
                    mod.montar(app, cfg)
                elif nome in ("radai_bolus_screen", "radai_janela"):
                    mod.montar(app, cfg.get("registrar"))
                elif nome == "radai_atualizar":
                    mod.montar(app, ler_vigia, cfg.get("registrar"))
                else:
                    mod.montar(app)
        except Exception as e:
            _MONTAGEM[nome] = "%s: %s" % (type(e).__name__, str(e)[:200])

    try:
        import radai_plugins
        radai_plugins.montar(app, cfg)
    except Exception as e:
        _MONTAGEM["radai_plugins"] = "%s: %s" % (type(e).__name__, str(e)[:200])

    @app.get("/config", response_class=HTMLResponse)
    def _tela_config():
        p = PAGINA_CONFIG

        url, desligada = u"", False
        try:
            import radai_version
            url = str(radai_version.URL_VERSOES or u"").strip()
            desligada = not str(radai_version.url_em_vigor() or u"").strip()
        except Exception:
            url, desligada = u"", True
        pecas = []
        try:
            import radai_version
            pecas.append(radai_version.idade().get("frase") or u"")
            pecas.append(radai_version.ultima_consulta().get("frase") or u"")
        except Exception:
            pass
        if desligada:
            pecas.append(u"verificação de versão desligada nesta estação")
        sub = u" · ".join(
            u'<span data-radai-frase>%s</span>' % _html.escape(x)
            for x in pecas if x)
        if not url:
            url = u"#"
        link = u""
        try:
            import radai_version
            link = (radai_version.link_do_instalador()
                    if url != u"#" else u"") or u""
        except Exception:
            link = u""
        try:
            import radai_version
            nova = bool(radai_version.para_a_tela().get("nova"))
        except Exception:
            nova = False
        agora = (u'<button type="button" class="pri" id="btAtuAgora" %s '
                 u'onclick="if(window.radaiAtualizarAgora) '
                 u'window.radaiAtualizarAgora()" data-radai-frase>'
                 u'Atualizar agora</button>') % (u"" if nova else u'hidden style="display:none"')
        if link:
            bt = (u'<a class="bt %s" id="lkInst" target="_blank" '
                  u'rel="noopener" href="%s" data-radai-frase>Baixar o '
                  u'instalador mais recente</a>'
                  % (u"sec" if nova else u"pri", _html.escape(link)))
        else:
            bt = u""
        p = (p.replace(u"@URL_VERSOES@", url)
              .replace(u"@BT_ATU_AGORA@", agora)
              .replace(u"@BT_INSTALADOR@", bt)
              .replace(u"@SUB_ATU@", sub or u"&#8212;"))
        try:
            import radai_languages
            p = radai_languages.aplicar(p)
        except Exception:
            pass
        p = radai_menu.aplicar(p, "config", com_tarefas=True)
        return p

    @app.get("/diagnostico", response_class=HTMLResponse)
    def _tela_log(nu: int = 0):
        if nu:
            return PAGINA_LOG.replace(
                u"</head>", u"<style>.rt-topbar{display:none}</style></head>", 1)
        return radai_menu.aplicar(PAGINA_LOG, "diagnostico")



    @app.get("/api/diagnostico")
    def _api_diag():
        return diagnostico(ler_vigia, cfg)

    @app.get("/api/registro")
    def _registro_estado():
        r = resumo_do_registro()
        if r.get("erro"):
            return {"erro": r["erro"]}
        aviso = u""
        try:
            import radai_records as RG
            aviso = RG.aviso_do_segredo()
        except Exception:
            aviso = u""
        return {"casos": r["casos"], "primeiro": r["primeiro"],
                "ultimo": r["ultimo"], "papel": r["papel"], "aviso": aviso}

    @app.post("/api/registro/exportar")
    async def _registro_exportar(request: Request):
        try:
            c = await request.json() or {}
        except Exception:
            c = {}
        try:
            import radai_records as RG
            papel = str(c.get("papel") or "")
            if papel:
                RG.gravar_perfil(papel)
            destino = os.path.join(RG.raiz(), "pacotes")
            return RG.exportar(destino, nota=str(c.get("nota") or ""))
        except Exception as e:
            return {"ok": False,
                    "avisos": ["%s: %s" % (type(e).__name__, str(e)[:200])]}

    @app.get("/api/registro/resumo")
    def _registro_resumo():
        try:
            import radai_records as RG
            from datetime import datetime as _dt, timedelta as _td
            agora = _dt.now()
            texto = RG.resumo_do_turno(
                desde=(agora - _td(hours=24)).strftime("%Y-%m-%d %H:%M:%S"),
                ate=agora.strftime("%Y-%m-%d %H:%M:%S"))
            try:
                RG.conferir_relatorio(texto)
            except RG.ContemIdentificacao as e:
                return {"ok": False, "texto": u"", "avisos": [u"%s" % e]}
            return {"ok": True, "texto": texto}
        except Exception as e:
            return {"ok": False, "texto": u"",
                    "avisos": ["%s: %s" % (type(e).__name__, str(e)[:200])]}

    @app.post("/api/registro/relatorio")
    def _registro_relatorio():
        try:
            import radai_records as RG
            return RG.gravar_relatorio(os.path.join(RG.raiz(), "relatorios"))
        except Exception as e:
            return {"ok": False,
                    "avisos": ["%s: %s" % (type(e).__name__, str(e)[:200])]}

    @app.get("/api/config")
    def _api_config():
        texto, valores = radai_config.ler_arquivo(caminho)
        return {"caminho": caminho, "existe": bool(texto), "chaves": chaves,
                "padroes": padroes, "valores": valores,
                "ajuda": radai_config.comentarios(texto or modelo),
                "divergente": divergencias(cfg),
                "editavel": bool(caminho and chaves)}

    @app.post("/api/config/testar")
    async def _api_testar(request: Request):
        try:
            corpo = await request.json()
        except Exception:
            corpo = {}
        return radai_config.validar_pasta((corpo or {}).get("caminho", ""))

    @app.post("/api/config")
    async def _api_salvar(request: Request):
        if not caminho or not chaves:
            return {"ok": False, "erro": "este processo nao expos a configuracao"}
        try:
            corpo = await request.json()
        except Exception:
            corpo = {}
        entrada = (corpo or {}).get("valores") or {}
        novos = dict((k, str(entrada[k])) for k in chaves if k in entrada)
        _, disco = radai_config.ler_arquivo(caminho)
        mudou = dict((k, v) for k, v in novos.items()
                     if str(v).strip() != str(disco.get(k, padroes.get(k, ""))).strip())
        if not mudou:
            return {"ok": True, "nada_mudou": True, "salvos": []}

        if "ROOT" in mudou and not (corpo or {}).get("confirmar_root"):
            return {"ok": False, "precisa_confirmar": True,
                    "root_atual": disco.get("ROOT", padroes.get("ROOT", "")),
                    "root_novo": mudou["ROOT"],
                    "validacao": radai_config.validar_pasta(mudou["ROOT"])}

        ok, erro = radai_config.escrever(caminho, mudou, modelo=modelo)
        if ok and registrar:
            try:
                registrar("configuracao alterada pela tela: %s (o processo em "
                          "execucao segue com os valores antigos ate reiniciar)"
                          % ", ".join(sorted(mudou)))
            except Exception:
                pass
        return {"ok": ok, "erro": erro, "salvos": sorted(mudou.keys()), "reiniciar": ok}

    return app
