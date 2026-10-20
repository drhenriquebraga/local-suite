# -*- coding: utf-8 -*-
import json

VERSAO_IDIOMAS = "1.0"

IDIOMAS = [
    ("de",       u"DE", u"Deutsch", False),
    ("en",       u"EN", u"English", False),
    ("es",       u"ES", u"Español", False),
    ("fr",       u"FR", u"Français", False),
    ("it",       u"IT", u"Italiano", False),
    ("pl",       u"PL", u"Polski", False),
    ("pt-BR",    u"PT", u"Português (Brasil)", False),
    ("ar",       u"AR", u"العربية", True),
    ("bn",       u"BN", u"বাংলা", False),
    ("ko",       u"KO", u"한국어", False),
    ("zh-CN",    u"ZH", u"中文", False),
    ("ja",       u"JA", u"日本語", False),
]


BANDEIRAS = {
    "de": (u'<path fill="#000" d="M0 0h30v6.67H0z"/>'
           u'<path fill="#DD0000" d="M0 6.67h30v6.66H0z"/>'
           u'<path fill="#FFCE00" d="M0 13.33h30V20H0z"/>'),
    "en": (u'<path fill="#012169" d="M0 0h30v20H0z"/>'
           u'<path stroke="#fff" stroke-width="4" d="M0 0l30 20M30 0L0 20"/>'
           u'<path stroke="#C8102E" stroke-width="1.4" d="M0 0l30 20M30 0L0 20"/>'
           u'<path stroke="#fff" stroke-width="6.6" d="M15 0v20M0 10h30"/>'
           u'<path stroke="#C8102E" stroke-width="4" d="M15 0v20M0 10h30"/>'),
    "es": (u'<path fill="#AA151B" d="M0 0h30v20H0z"/>'
           u'<path fill="#F1BF00" d="M0 5h30v10H0z"/>'),
    "fr": (u'<path fill="#fff" d="M0 0h30v20H0z"/>'
           u'<path fill="#002654" d="M0 0h10v20H0z"/>'
           u'<path fill="#ED2939" d="M20 0h10v20H20z"/>'),
    "it": (u'<path fill="#fff" d="M0 0h30v20H0z"/>'
           u'<path fill="#009246" d="M0 0h10v20H0z"/>'
           u'<path fill="#CE2B37" d="M20 0h10v20H20z"/>'),
    "pl": (u'<path fill="#fff" d="M0 0h30v10H0z"/>'
           u'<path fill="#DC143C" d="M0 10h30v10H0z"/>'),
    "pt-BR": (u'<path fill="#009C3B" d="M0 0h30v20H0z"/>'
              u'<path fill="#FFDF00" d="M15 2.4L27.4 10 15 17.6 2.6 10z"/>'
              u'<circle fill="#002776" cx="15" cy="10" r="4.9"/>'
              u'<path fill="none" stroke="#fff" stroke-width=".9" '
              u'd="M10.3 8.7c3.2-.7 6.6-.1 9.4 1.9"/>'),
    "ar": (u'<path fill="#006C35" d="M0 0h30v20H0z"/>'
           u'<path fill="none" stroke="#fff" stroke-width=".9" '
           u'stroke-linecap="round" d="M8 6.5c1-1 2 1 3 0s2 1 3 0 2 1 3 0 '
           u'2 1 3 0 2 1 3 0M9 9.6c1-1 2 1 3 0s2 1 3 0 2 1 3 0 2 1 3 0"/>'
           u'<path fill="none" stroke="#fff" stroke-width=".9" '
           u'stroke-linecap="round" d="M8.5 14h13M20.5 12.8v2.4"/>'),
    "bn": (u'<path fill="#006A4E" d="M0 0h30v20H0z"/>'
           u'<circle fill="#F42A41" cx="13.5" cy="10" r="6"/>'),
    "ko": (u'<path fill="#fff" d="M0 0h30v20H0z"/>'
           u'<g transform="rotate(33.69 15 10)">'
           u'<path fill="#CD2E3A" d="M10 10a5 5 0 0 1 10 0z"/>'
           u'<path fill="#0047A0" d="M10 10a5 5 0 0 0 10 0z"/>'
           u'<circle fill="#CD2E3A" cx="12.5" cy="10" r="2.5"/>'
           u'<circle fill="#0047A0" cx="17.5" cy="10" r="2.5"/></g>'
           u'<g stroke="#000" stroke-width=".7" fill="none">'
           u'<path transform="translate(6.3 4.2) rotate(-56.31)" '
           u'd="M-1.7-1.1h3.4M-1.7 0h3.4M-1.7 1.1h3.4"/>'
           u'<path transform="translate(23.7 15.8) rotate(-56.31)" '
           u'd="M-1.7-1.1h3.4M-1.7 0h3.4M-1.7 1.1h3.4"/>'
           u'<path transform="translate(23.7 4.2) rotate(56.31)" '
           u'd="M-1.7-1.1h3.4M-1.7 0h3.4M-1.7 1.1h3.4"/>'
           u'<path transform="translate(6.3 15.8) rotate(56.31)" '
           u'd="M-1.7-1.1h3.4M-1.7 0h3.4M-1.7 1.1h3.4"/></g>'),
    "zh-CN": (u'<path fill="#EE1C25" d="M0 0h30v20H0z"/>'
              u'<g fill="#FFFF00">'
              u'<path d="M5 2L5.67 4.07 7.85 4.07 6.09 5.35 6.76 7.43 5 6.15 '
              u'3.24 7.43 3.91 5.35 2.15 4.07 4.33 4.07z"/>'
              u'<path d="M9.14 2.51L9.62 1.97 9.25 1.34 9.91 1.63 10.39 1.08 '
              u'10.33 1.8 11 2.09 10.29 2.25 10.22 2.97 9.85 2.35z"/>'
              u'<path d="M11.01 4.14L11.66 3.82 11.56 3.1 12.07 3.62 12.72 '
              u'3.3 12.38 3.95 12.88 4.47 12.17 4.34 11.83 4.99 11.73 4.27z"/>'
              u'<path d="M11.04 6.73L11.76 6.7 11.96 6 12.21 6.68 12.94 6.66 '
              u'12.37 7.1 12.62 7.79 12.01 7.38 11.44 7.83 11.64 7.13z"/>'
              u'<path d="M9.22 8.38L9.9 8.63 10.35 8.06 10.32 8.79 11 9.05 '
              u'10.3 9.24 10.26 9.96 9.87 9.36 9.16 9.55 9.62 8.98z"/></g>'),
    "ja": (u'<path fill="#fff" d="M0 0h30v20H0z"/>'
           u'<circle fill="#BC002D" cx="15" cy="10" r="6"/>'),
}

_SVG_BANDEIRA = (u'<svg viewBox="0 0 30 20" preserveAspectRatio="none" '
                 u'aria-hidden="true" focusable="false">%s</svg>')


def bandeira(cod):
    tracos = BANDEIRAS.get(canonico(cod) or u"")
    return (_SVG_BANDEIRA % tracos) if tracos else u""


# GUARDA: PADRAO (o idioma dos documentos) e INICIAL (o da tela) sao dois;
# `avisarDocumento` compara com PADRAO, senao o aviso de que os Termos valem
# em portugues sumiria justamente para quem nao le portugues.
PADRAO = "pt-BR"

INICIAL_SEM_ESCOLHA = "en"

CHAVE_CONFIG = "IDIOMA"

ARQUIVO_IDIOMA = "idioma.txt"

ALIAS_IDIOMA = {
    "zh": "zh-CN",
    "pt": "pt-BR",
    "zh-Hans": "zh-CN",
}


def canonico(cod):
    c = str(cod or "").strip()
    if not c:
        return ""
    conhecidos = [x[0] for x in IDIOMAS]
    if c in conhecidos:
        return c
    return ALIAS_IDIOMA.get(c, "")


def idioma_do_config():
    try:
        import radai_config
        return canonico(radai_config.chave_configurada(CHAVE_CONFIG))
    except Exception:
        return u""


def gravar_na_estacao(cod, caminho=None):
    c = canonico(cod)
    if not c:
        return False, u"idioma desconhecido: %s" % (str(cod or u"")[:20] or u"(vazio)")
    try:
        import radai_config
        alvo = caminho or radai_config.caminho_padrao()
        ok, erro = radai_config.escrever(alvo, {CHAVE_CONFIG: c})
    except Exception as e:
        return False, u"%s: %s" % (type(e).__name__, e)
    return (True, c) if ok else (False, erro or u"nao consegui gravar o config")


def padrao_efetivo():
    import io
    import os

    cod = idioma_do_config()
    if cod:
        return cod
    aqui = os.path.dirname(os.path.abspath(__file__))
    for base in (aqui, os.path.dirname(aqui)):
        p = os.path.join(base, ARQUIVO_IDIOMA)
        try:
            if os.path.isfile(p):
                cod = canonico(io.open(p, encoding="utf-8-sig").read())
                if cod:
                    return cod
        except (OSError, UnicodeError):
            pass
    return INICIAL_SEM_ESCOLHA

try:
    import radai_phrases
    FRASES = radai_phrases.construir()
    normalizar = radai_phrases.normalizar
except Exception:
    FRASES = {}

    def normalizar(t):
        return u" ".join((t or u"").split())

NAO_TRADUZIR = ("TG-263", "DICOM", "RTSTRUCT", "UNAPPROVED", "TotalSegmentator",
                "VISTA-3D", "MONAI", "Radioterapia.AI", "DSC", "HD95",
                "_ai", "_ts", "_nv", "U-Net", "nnU-Net")


def _bloco_completo(inicial=None):
    bloco = u"""
<style id="radai-idioma-css">
.radai-lang{position:relative;display:inline-block;font-family:inherit;
--rl-curva:cubic-bezier(.22,1,.36,1)}
.radai-lang .rl-band{display:inline-block;width:21px;height:14px;flex:0 0 auto;
border-radius:2px;overflow:hidden;line-height:0;
box-shadow:0 0 0 1px var(--line-strong,#2a3a55)}
.radai-lang .rl-band svg{display:block;width:100%;height:100%}
.radai-lang .rl-bt{display:inline-flex;align-items:center;gap:8px;
background:var(--panel-2,#0f1729);border:1px solid var(--accent-line,#2a3d57);
color:var(--text,#e6edf7);border-radius:var(--r-md,6px);padding:6px 10px 6px 8px;
font-family:inherit;font-size:12.5px;font-weight:500;line-height:1.2;cursor:pointer;
transition:background .12s,border-color .12s}
.radai-lang .rl-bt:hover{border-color:var(--accent,#4DA3FF)}
.radai-lang .rl-bt:focus-visible,.radai-lang .rl-op:focus-visible{
outline:2px solid var(--accent,#4DA3FF);outline-offset:2px}
.radai-lang .rl-seta{width:0;height:0;margin-inline-start:2px;opacity:.7;
border-left:4px solid transparent;border-right:4px solid transparent;
border-top:5px solid currentColor;transition:transform .18s}
.radai-lang.on .rl-seta{transform:rotate(180deg)}
.radai-lang .lista{position:absolute;inset-inline-end:0;top:calc(100% + 6px);
z-index:30;min-width:224px;max-height:60vh;overflow-y:auto;padding:4px;
background:var(--panel,#0c1322);border:1px solid var(--accent-line,#2a3d57);
border-radius:var(--r-lg,8px);box-shadow:var(--sombra,0 8px 24px rgba(0,0,0,.5));
opacity:0;visibility:hidden;transform:translateY(-6px) scale(.98);
transform-origin:top right;
transition:opacity .16s ease,transform .18s var(--rl-curva),
visibility 0s linear .18s}
.radai-lang.on .lista{opacity:1;visibility:visible;transform:none;
transition:opacity .16s ease,transform .18s var(--rl-curva),visibility 0s}
.radai-lang .rl-op{display:flex;width:100%;gap:9px;align-items:center;
padding:7px 9px;border:0;border-radius:var(--r-sm,5px);background:transparent;
color:var(--text,#e6edf7);font-family:inherit;font-size:12.5px;line-height:1.3;
text-align:start;cursor:pointer}
.radai-lang .rl-op:hover{background:var(--panel-2,#0f1729)}
.radai-lang .rl-op.on{background:var(--accent-fraco,rgba(77,163,255,.14));font-weight:600}
.radai-lang .rl-nome{flex:0 1 auto;min-width:0}
.radai-lang .rl-cod{margin-inline-start:auto;padding-inline-start:12px;
font-family:var(--font-mono,monospace);font-size:10px;
letter-spacing:.08em;color:var(--text-dim,#72829b)}
.radai-lang.rl-grade{display:grid;width:100%;gap:6px;
grid-template-columns:repeat(auto-fill,minmax(158px,1fr))}
.radai-lang.rl-grade .rl-op{border:1px solid var(--line,#1e293b);
background:var(--panel-2,#0f1729);padding:8px 10px}
.radai-lang.rl-grade .rl-op:hover{border-color:var(--line-strong,#2a3a55)}
.radai-lang.rl-grade .rl-op.on{border-color:var(--accent,#4DA3FF);
box-shadow:inset 0 0 0 1px var(--accent,#4DA3FF);
background:var(--accent-fraco,rgba(77,163,255,.14))}
@media (prefers-reduced-motion:reduce){
.radai-lang .lista,.radai-lang.on .lista,.radai-lang .rl-seta{transition:none}}
</style>
<script id="radai-idioma-js">
(function(){
 var IDIOMAS=@IDIOMAS@, FRASES=(function(c){var o={},k=c.k,cod,a,d,i;for(cod in c.t){a=c.t[cod];d={};for(i=0;i<k.length;i++)if(a[i]!==null)d[k[i]]=a[i];o[cod]=d;}return o;})(@FRASES@),
     FIXOS=@FIXOS@, PADRAO=@PADRAO@,
     INICIAL=@INICIAL@;

 var ALIAS=@ALIAS@;
 function canon(c){ if(!c) return '';
  for(var i=0;i<IDIOMAS.length;i++) if(IDIOMAS[i][0]===c) return c;
  return ALIAS[c]||''; }
 function atual(){ try{ return canon(localStorage.getItem('radai_idioma'))||INICIAL }
                   catch(e){ return INICIAL } }

 function norm(t){ return (t||'').replace(/\\s+/g,' ').trim() }

 function fixo(t){
  var nu=t.replace(/^[\\s"'(\\[]+|[\\s"'.,;:)\\]]+$/g,'');
  for(var i=0;i<FIXOS.length;i++) if(nu===FIXOS[i]) return true;
  return false;
 }

 var FRAGIL='input,select,textarea,button,canvas,img,svg,video,iframe,table,form';
 var ANCORA='[id]';
 var BLOCOS='p,li,h1,h2,h3,h4,td,th,label,button,a,summary,figcaption,'
           +'.desc,.sub,.rc-frase,.rc-nota,.rc-rotulo,.aviso,.balao,.fonte,'
           +'.ps-sub,'
           +'.rot,.dica3d,.dicamouse,.grupolbl,.tit,.pq,.instr,'
           +'.rt-declaracao>span,.decl>span,.rodape-clinico>span,'
           +'[data-radai-frase]';

 var MARCA=/%s|%d|\\{\\d+\\}/g;
 var MOLDES={};
 function escRe(s){ return s.replace(/[.*+?^${}()|[\\]\\\\]/g,'\\\\$&') }
 function moldesDe(cod){
  if(MOLDES[cod]) return MOLDES[cod];
  var d=FRASES[cod]||{}, fora=[];
  Object.keys(d).forEach(function(k){
   var km=k.match(MARCA); if(!km) return;
   var tr=d[k]; if(!tr) return;
   if((tr.match(MARCA)||[]).length!==km.length) return;
   var partes=k.split(MARCA);
   if(partes.join('').length<12) return;
   fora.push([new RegExp('^'+partes.map(escRe).join('(.+?)')+'$'), tr, km]);
  });
  MOLDES[cod]=fora;
  return fora;
 }
 function porMolde(cod, chave, el){
  try{
   // GUARDA: a marca que o passo 1 poe (`data-radai-tr`) nao e documento.
   if(el&&el.closest&&(el.closest('.env')
      ||el.closest('[data-radai-t="1"]:not([data-radai-tr])')))
    return '';
   var ms=moldesDe(cod);
   for(var i=0;i<ms.length;i++){
    var m=ms[i][0].exec(chave); if(!m) continue;
    var km=ms[i][2], seq=0;
    return ms[i][1].replace(MARCA,function(mk){
     if(mk.charAt(0)==='{'){ var p=km.indexOf(mk); return p>=0?m[p+1]:mk }
     var n=0;
     for(var q=0;q<km.length;q++){
      if(km[q].charAt(0)!=='%') continue;
      if(n===seq){ seq++; return m[q+1] }
      n++;
     }
     return mk;
    });
   }
  }catch(e){}
  return '';
 }

 function traduzir(cod){
  var d=FRASES[cod]; if(!d) return;

  try{
   if(!window.__radaiTitulo0) window.__radaiTitulo0 = document.title || '';
   var t0 = window.__radaiTitulo0;
   if(t0){
    var pos = t0.indexOf(' · ');
    var rot = (pos > 0) ? t0.slice(0, pos) : t0;
    var resto = (pos > 0) ? t0.slice(pos) : '';
    var novo = d[norm(rot)] || d[rot] || rot;
    document.title = novo + resto;
   }
  }catch(e){}

  var blocos;
  try{ blocos=document.body.querySelectorAll(BLOCOS) }catch(e){ blocos=[] }
  Array.prototype.forEach.call(blocos,function(el){
   if(el.getAttribute('data-radai-t')==='1') return;
   if(el.closest('.radai-lang')) return;
   if(el.querySelector&&el.querySelector(FRAGIL)) return;
   if(el.querySelector&&el.querySelector(ANCORA)) return;
   if(el.querySelector&&el.querySelector('[data-radai-t="1"]')) return;
   var chave=norm(el.textContent);
   if(!chave||fixo(chave)) return;
   var novo=d[chave];
   if(!novo) novo=porMolde(cod,chave,el);
   if(!novo) return;
   el.textContent=novo;
   el.setAttribute('data-radai-t','1');
   el.setAttribute('data-radai-tr','1');
  });

  var it=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT,null,false);
  var nos=[],n;
  while(n=it.nextNode()){
   var pai=n.parentNode, tag=pai&&pai.nodeName;
   if(tag==='SCRIPT'||tag==='STYLE'||tag==='TEXTAREA') continue;
   if(pai&&pai.closest&&pai.closest('.radai-lang')) continue;
   if(pai&&pai.getAttribute&&pai.getAttribute('data-radai-t')==='1') continue;
   nos.push(n);
  }
  nos.forEach(function(no){
   var chave=norm(no.nodeValue);
   if(!chave||fixo(chave)) return;
   var novo=d[chave];
   if(!novo) novo=porMolde(cod,chave,no.parentNode);
   if(novo) no.nodeValue=no.nodeValue.replace(no.nodeValue.trim(),novo);
  });

  ['title','aria-label','placeholder'].forEach(function(at){
   var els;
   try{ els=document.body.querySelectorAll('['+at+']') }catch(e){ return }
   Array.prototype.forEach.call(els,function(el){
    if(el.closest&&el.closest('.radai-lang')) return;
    var chave=norm(el.getAttribute(at));
    if(!chave||fixo(chave)) return;
    var novo=d[chave];
    if(!novo) novo=porMolde(cod,chave,el);
    if(novo) el.setAttribute(at,novo);
   });
  });

  var rtl=false;
  IDIOMAS.forEach(function(x){ if(x[0]===cod) rtl=x[3] });
  document.documentElement.setAttribute('lang',cod);
  document.documentElement.setAttribute('dir',rtl?'rtl':'ltr');
 }

 var AVISO_DOC='A interface está traduzida; este texto vale em português. Tradução jurídica exige revisão humana, e enquanto não houver uma, o original é o que responde.';
 function avisarDocumento(cod){
  if(cod===PADRAO) return;
  var p=location.pathname;
  if(p!=='/termos'&&p!=='/politica-privacidade') return;
  if(document.getElementById('radai-aviso-doc')) return;
  var alvo=document.querySelector('.env')||document.body;
  var cx=document.createElement('div');
  cx.id='radai-aviso-doc';
  cx.setAttribute('style','margin:0 0 16px;padding:11px 13px;border-radius:8px;'
   +'border:1px solid var(--borda-ok,#3a4c2a);background:var(--fundo-ok,#141c10);'
   +'color:var(--text,#c9d9b8);font-size:12.5px;'
   +'line-height:1.55');
  cx.textContent=(FRASES[cod]&&FRASES[cod][AVISO_DOC])||AVISO_DOC;
  alvo.insertBefore(cx,alvo.firstChild);
 }

 function gravarNaEstacao(cod){
  try{
   return fetch('/api/idioma',{method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({idioma:cod}),keepalive:true}).catch(function(){});
  }catch(e){ return null }
 }
 function escolher(cod, atualCod){
  try{ localStorage.setItem('radai_idioma',cod) }catch(e){}
  var p=gravarNaEstacao(cod);
  if(cod===atualCod) return;
  var foi=false;
  function ir(){ if(foi) return; foi=true; location.reload() }
  if(p&&p.then) p.then(ir,ir);
  setTimeout(ir,1500);
 }

 function rotuloDe(x){
  return '<span class="rl-band" aria-hidden="true">'+(x[4]||'')+'</span>'
   +'<span class="rl-nome" lang="'+x[0]+'" dir="'+(x[3]?'rtl':'ltr')+'">'
   +x[2]+'</span>';
 }
 var _nSel=0;

 function montarLista(alvo, cur){
  var cx=document.createElement('div'); cx.className='radai-lang';
  var id='radai-lang-lista-'+(++_nSel);
  cx.innerHTML='<button type="button" class="rl-bt" aria-haspopup="listbox" '
   +'aria-expanded="false" aria-controls="'+id+'">'+rotuloDe(cur)
   +'<span class="rl-seta" aria-hidden="true"></span></button>'
   +'<div class="lista" id="'+id+'" role="listbox">'+IDIOMAS.map(function(x){
     var on=(x[0]===cur[0]);
     return '<button type="button" role="option" class="rl-op'+(on?' on':'')
      +'" data-cod="'+x[0]+'" aria-selected="'+(on?'true':'false')+'">'
      +rotuloDe(x)+'<span class="rl-cod">'+x[1]+'</span></button>'}).join('')
   +'</div>';
  alvo.appendChild(cx);
  var bt=cx.querySelector('.rl-bt'), lista=cx.querySelector('.lista');
  var ops=Array.prototype.slice.call(lista.querySelectorAll('.rl-op'));
  function abrir(focar){
   cx.classList.add('on'); bt.setAttribute('aria-expanded','true');
   var f=lista.querySelector('.rl-op.on')||ops[0];
   if(focar&&f) setTimeout(function(){ try{ f.focus() }catch(e){} },0);
  }
  function fechar(devolver){
   cx.classList.remove('on'); bt.setAttribute('aria-expanded','false');
   if(devolver){ try{ bt.focus() }catch(e){} }
  }
  bt.addEventListener('click',function(e){
   e.preventDefault(); if(cx.classList.contains('on')) fechar(false); else abrir(true)});
  bt.addEventListener('keydown',function(e){
   if(e.key==='ArrowDown'||e.key==='ArrowUp'){ e.preventDefault(); abrir(true) }});
  lista.addEventListener('keydown',function(e){
   var i=ops.indexOf(document.activeElement), n=ops.length, k=-1;
   if(e.key==='Escape'){ e.preventDefault(); fechar(true); return }
   if(e.key==='Tab'){ fechar(false); return }
   if(e.key==='ArrowDown') k=(i+1)%n;
   else if(e.key==='ArrowUp') k=(i-1+n)%n;
   else if(e.key==='Home') k=0;
   else if(e.key==='End') k=n-1;
   if(k>=0){ e.preventDefault(); ops[k].focus() }
  });
  ops.forEach(function(o){ o.addEventListener('click',function(){
   var c=o.getAttribute('data-cod');
   ops.forEach(function(p){ var s=(p===o);
    p.classList.toggle('on',s); p.setAttribute('aria-selected',s?'true':'false') });
   fechar(true);
   escolher(c, cur[0]);
  })});
  document.addEventListener('click',function(e){
   if(!cx.contains(e.target)) fechar(false)});
 }

 function montarGrade(alvo, cur){
  var cx=document.createElement('div'); cx.className='radai-lang rl-grade';
  cx.setAttribute('role','radiogroup');
  cx.innerHTML=IDIOMAS.map(function(x){
   var on=(x[0]===cur[0]);
   return '<button type="button" role="radio" class="rl-op'+(on?' on':'')
    +'" data-cod="'+x[0]+'" aria-checked="'+(on?'true':'false')+'" tabindex="'
    +(on?'0':'-1')+'">'+rotuloDe(x)+'</button>'}).join('');
  alvo.appendChild(cx);
  var ops=Array.prototype.slice.call(cx.querySelectorAll('.rl-op'));
  ops.forEach(function(o){ o.addEventListener('click',function(){
   ops.forEach(function(p){ var s=(p===o);
    p.classList.toggle('on',s); p.setAttribute('aria-checked',s?'true':'false');
    p.tabIndex=s?0:-1 });
   escolher(o.getAttribute('data-cod'), cur[0]);
  })});
  cx.addEventListener('keydown',function(e){
   var i=ops.indexOf(document.activeElement), n=ops.length, k=-1;
   if(i<0) return;
   if(e.key==='ArrowRight'||e.key==='ArrowDown') k=(i+1)%n;
   else if(e.key==='ArrowLeft'||e.key==='ArrowUp') k=(i-1+n)%n;
   else if(e.key==='Home') k=0;
   else if(e.key==='End') k=n-1;
   if(k>=0){ e.preventDefault(); ops[i].tabIndex=-1; ops[k].tabIndex=0; ops[k].focus() }
  });
 }

 function montar(){
  var alvos=document.querySelectorAll('[data-radai-idiomas],[data-radai-lang]');
  if(!alvos.length) return;
  var cod=atual(), cur=null;
  IDIOMAS.forEach(function(x){ if(x[0]===cod) cur=x });
  if(!cur){ IDIOMAS.forEach(function(x){ if(x[0]===INICIAL) cur=x }) }
  if(!cur){ cur=IDIOMAS[0] }
  Array.prototype.forEach.call(alvos,function(alvo){
   if(alvo.querySelector('.radai-lang')) return;
   if(alvo.getAttribute('data-radai-idiomas')==='grade') montarGrade(alvo,cur);
   else montarLista(alvo,cur);
  });
 }

 window.radaiRetraduzir = function(){ try{ traduzir(atual()) }catch(e){} };
 window.radaiFrase = function(pt){
  try{
   var d=FRASES[atual()]; if(!d) return pt;
   var k=norm(pt); if(!k||fixo(k)) return pt;
   return d[k]||pt;
  }catch(e){ return pt }
 };

 function iniciar(){ montar(); traduzir(atual()); avisarDocumento(atual());
  setInterval(function(){ traduzir(atual()) }, 3000);
 }
 if(document.readyState==='loading')
  document.addEventListener('DOMContentLoaded',iniciar);
 else iniciar();
})();
</script>"""
    for marca, valor in (
            ("@IDIOMAS@", json.dumps([[c, b, n, r, bandeira(c)]
                                      for (c, b, n, r) in IDIOMAS],
                                     ensure_ascii=False)),
            # GUARDA: JSON compacto; o dicionário mora perto do teto de 2 MB.
            ("@FRASES@", json.dumps(_frases_compactas(), ensure_ascii=False,
                                    separators=(",", ":"))),
            ("@FIXOS@", json.dumps(list(NAO_TRADUZIR), ensure_ascii=False)),
            ("@PADRAO@", json.dumps(PADRAO)),
            ("@INICIAL@", json.dumps(inicial if inicial is not None
                                     else padrao_efetivo())),
            ("@ALIAS@", json.dumps(ALIAS_IDIOMA, ensure_ascii=False))):
        bloco = bloco.replace(marca, valor)
    return bloco
ROTA_JS = "/radai-idiomas.js"

_CORPOS = {}


def _corpo_e_marca():
    ini = padrao_efetivo()
    par = _CORPOS.get(ini)
    if par is None:
        import hashlib
        b = _bloco_completo(ini)
        i = b.index(u'<script id="radai-idioma-js">')
        i = b.index(u">", i) + 1
        corpo = b[i:b.rindex(u"</script>")]
        par = (corpo, u'"%s"' % hashlib.sha256(
            corpo.encode("utf-8")).hexdigest()[:20])
        _CORPOS[ini] = par
    return par


def _frases_compactas():
    chaves = sorted(set().union(*[set(d) for d in FRASES.values()]))
    return {"k": chaves,
            "t": {c: [d.get(k) for k in chaves] for c, d in FRASES.items()}}


def corpo_js():
    return _corpo_e_marca()[0]


_ESTILO = [u""]


def estilo():
    if not _ESTILO[0]:
        b = _bloco_completo(INICIAL_SEM_ESCOLHA)
        _ESTILO[0] = b[:b.index(u'<script id="radai-idioma-js">')]
    return _ESTILO[0]


def etag_js():
    return _corpo_e_marca()[1]


def montar(app):
    from fastapi import Request
    from fastapi.responses import Response

    @app.get(ROTA_JS)
    def _dicionario(request: Request = None):
        marca = etag_js()
        cabs = {"ETag": marca, "Cache-Control": "private, no-cache"}
        anterior = u""
        try:
            anterior = (request.headers.get("if-none-match") or u"") if request else u""
        except Exception:
            anterior = u""
        if anterior.strip() == marca:
            return Response(status_code=304, headers=cabs)
        return Response(content=corpo_js(),
                        media_type="application/javascript", headers=cabs)

    return app


def montar_idioma_da_estacao(app):
    from fastapi import Request

    @app.get("/api/idioma")
    def _idioma_da_estacao():
        return {"idioma": padrao_efetivo(), "config": idioma_do_config(),
                "padrao": PADRAO, "idiomas": [c for (c, _, _, _) in IDIOMAS]}

    @app.post("/api/idioma")
    async def _gravar_idioma(request: Request):
        from fastapi.responses import JSONResponse
        try:
            c = await request.json() or {}
        except Exception:
            c = {}
        ok, r = gravar_na_estacao((c or {}).get("idioma")
                                  if isinstance(c, dict) else None)
        if not ok:
            return JSONResponse({"ok": False, "erro": r}, status_code=400)
        return {"ok": True, "idioma": r}

    return app


def _js():
    return (estilo()
            + u'<script id="radai-idioma-js" src="%s" defer></script>'
              % ROTA_JS)



def so_traduzir(pagina):
    p = aplicar(pagina)
    if p is pagina:
        return pagina
    return p


def aplicar(pagina):
    if not pagina or u"radai-idioma-js" in pagina:
        return pagina
    baixa = pagina.lower()
    if baixa.find(u"</head>") < 0:
        return pagina
    fim = baixa.rfind(u"</body>")
    if fim < 0:
        return pagina
    return pagina[:fim] + _js() + pagina[fim:]
