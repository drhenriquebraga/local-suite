# -*- coding: utf-8 -*-

JANELAS = {"pulmao": (-1350.0, 150.0),
           "mediastino": (-160.0, 240.0),
           "osso": (-450.0, 1050.0)}


CSS = u"""
.visores{display:flex;gap:8px;align-items:stretch;
 height:calc(100vh - 300px);min-height:320px}
.principal{flex:1;min-width:0;display:flex;flex-direction:column;gap:6px}
.pilha{width:min(230px,26vw);display:flex;flex-direction:column;gap:8px;height:100%}
.pilha .visor{flex:1 1 0;min-height:0}

.visor{border:1px solid var(--line);background:var(--bg-0,#060d1a);border-radius:4px;
 position:relative;overflow:hidden;display:flex;align-items:center;
 justify-content:center;min-height:0}
.principal .visor{flex:1;min-height:0}
.visor img{display:block;max-width:100%;max-height:100%;width:100%;height:100%;
 object-fit:contain;cursor:crosshair}
.visor canvas{display:block;max-width:100%;max-height:100%;cursor:grab;touch-action:none}
.visor canvas:active{cursor:grabbing}
.pilha .visor{cursor:pointer}
.pilha .visor img,.pilha .visor canvas{cursor:pointer}
.pilha .visor:hover{border-color:var(--accent)}
.pilha .visor:hover .troca{opacity:1}
.troca{position:absolute;inset:0;display:grid;place-items:center;opacity:0;
 background:rgba(4,10,20,.55);font-size:11px;color:var(--text);
 transition:opacity .12s;pointer-events:none}
.v3-vistas{position:absolute;top:6px;right:6px;display:flex;gap:3px;opacity:.35;
 transition:opacity .15s}
.visor:hover .v3-vistas{opacity:1}
.v3-vistas button{width:20px;height:20px;padding:0;font-size:10px;
 line-height:1;border-radius:5px;border:1px solid var(--line);
 background:var(--panel,#0b1220);color:var(--text-dim);cursor:pointer;
 font-family:var(--mono,monospace)}
.v3-vistas button:hover{color:var(--text);border-color:var(--accent)}
.dica3d{position:absolute;bottom:6px;left:8px;right:8px;font-family:var(--mono,monospace);
 font-size:9.5px;color:var(--text-dim,#72829b);pointer-events:none}
.pilha .dica3d{font-size:9px;bottom:4px;text-align:center;left:4px;right:4px}
.visor .rot{position:absolute;top:7px;left:9px;font-family:var(--mono,monospace);font-size:9px;
 letter-spacing:.1em;text-transform:uppercase;color:var(--text-dim,#72829b);pointer-events:none}

.ferr .passo1{min-width:26px;padding:3px 0;justify-content:center;
 font-size:15px;line-height:1}
.ferr{display:flex;align-items:center;gap:6px;flex-wrap:wrap;flex:none;
 margin-top:8px;padding:7px 9px;border:1px solid var(--line);border-radius:6px;
 background:var(--bg-0,#060d1a)}
.ferr #rg{flex:1;min-width:140px;max-width:320px}
.ferr .sep{width:1px;height:16px;background:var(--line-strong);margin:0 3px}
.ferr 
.ferr{display:flex;align-items:center;flex-wrap:wrap;gap:6px}
.ferr .grupolbl,.ferr .cortelbl,.ferr .fbt,.ferr input[type=range]{
align-self:center;line-height:1}
.grupolbl{font-family:var(--mono,monospace);font-size:9px;letter-spacing:.12em;
 text-transform:uppercase;color:var(--text-dim)}
.cortelbl{font-family:var(--mono,monospace);font-size:11px;color:var(--text-muted)}
.fbt{font-family:var(--mono,monospace);font-size:10.5px;padding:4px 9px;border-radius:4px;
 border:1px solid var(--line-strong);color:var(--text-muted);cursor:pointer;
 background:transparent}
.fbt:hover{border-color:var(--accent);color:var(--text)}
.fbt.on{border-color:var(--accent);color:var(--accent);background:rgba(77,163,255,.10)}
.fbt[disabled]{opacity:.4;cursor:not-allowed}
.dicamouse{margin-left:auto;font-size:10.5px;color:var(--text-dim);white-space:nowrap}

.grade.max .lat,.grade.max .pilha{display:none}
.grade.max{grid-template-columns:minmax(0,1fr)}
"""


JS_PALCO = u"""
function RadaiPalco(cfg){
 var P = {
  base: cfg.base,                    // ex.: '/api/torax'
  corte: {axial:0, coronal:0, sagital:0},
  nc:    {axial:0, coronal:0, sagital:0},
  cortes: 0,
  janela: 'mediastino', wl: [40, 400],
  zoom: Number(window.UI_VISOR_ZOOM_INICIAL) || 1, pan: {x:0, y:0}, principal: 'axial',
  ferramenta: 'janela',      // janela | pan

  regua: null, arrasto: null,
  aoClicar: cfg.aoClicar || null,    // (plano, fx, fy) quando nao ha regua
  estruturas: cfg.estruturas || function(){ return ''; },
  extra: cfg.extra || function(){ return ''; },
  ao3D: cfg.ao3D || null,
  cranial: (cfg.cranial === 1 || cfg.cranial === -1) ? cfg.cranial : 0
 };
 P.rumoCaudal = function(pl, d){
  return (pl === 'axial' && P.cranial) ? -d * P.cranial : d;
 };
 function el(i){ return document.getElementById(i); }
 function esc(s){ return String(s==null?'':s).replace(/[&<>"]/g,function(c){
  return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }

 P.fracao = function(img, ev){
  var r=img.getBoundingClientRect();
  if(!img.naturalWidth || !img.naturalHeight) return null;
  var arI=img.naturalWidth/img.naturalHeight, arC=r.width/r.height;
  var w=r.width, h=r.height, ox=0, oy=0;
  if(arC > arI){ w=r.height*arI; ox=(r.width-w)/2; }
  else         { h=r.width/arI;  oy=(r.height-h)/2; }
  var fx=(ev.clientX-r.left-ox)/w, fy=(ev.clientY-r.top-oy)/h;
  if(fx<0||fx>1||fy<0||fy>1) return null;    // caiu na tarja
  return {fx:fx, fy:fy};
 };

 P.imagens = function(){
  if(!P.nc.axial) return;
  var comum='&e='+encodeURIComponent(P.estruturas())+'&j='+P.janela
           +'&t='+Date.now()+P.extra()
           +(P.janela?'':('&c='+Math.round(P.wl[0])+'&l='+Math.round(P.wl[1])));
  var alvo={axial:'imgAx', coronal:'imgCo', sagital:'imgSa'};
  Object.keys(alvo).forEach(function(pl){
   var im=el(alvo[pl]); if(!im) return;
   im.src = P.base+'/imagem?corte='+P.corte[pl]+comum+'&plano='+pl;
  });
  var pl=P.principal==='3d' ? 'axial' : P.principal;
  var l=el('lbl');  if(l) l.textContent=pl+' '+(P.corte[pl]+1)+' de '+P.nc[pl];
  var rg=el('rg');  if(rg){ rg.max=Math.max(0,P.nc[pl]-1); rg.value=P.corte[pl]; }
 };

 P.irPara = function(z, y, x){
  if(z!=null) P.corte.axial   = Math.max(0, Math.min(P.nc.axial-1,   Math.round(z)));
  if(y!=null) P.corte.coronal = Math.max(0, Math.min(P.nc.coronal-1, Math.round(y)));
  if(x!=null) P.corte.sagital = Math.max(0, Math.min(P.nc.sagital-1, Math.round(x)));
  P.imagens();
 };

 P.definirForma = function(forma, cranial){
  var z=(forma||[])[0]||0, y=(forma||[])[1]||0, x=(forma||[])[2]||0;
  if(cranial === 1 || cranial === -1) P.cranial = cranial;
  P.nc = {axial:z, coronal:y, sagital:x};
  P.cortes = z;
  P.corte = {axial:Math.floor(z/2), coronal:Math.floor(y/2), sagital:Math.floor(x/2)};
 };

 P.trocar = function(qual){
  if(qual === P.principal) return;
  var novo=document.querySelector('[data-v="'+qual+'"]');
  var velho=document.querySelector('[data-v="'+P.principal+'"]');
  if(!novo || !velho) return;
  var onde=novo.nextSibling, pai=novo.parentNode;
  el('principal').appendChild(novo);
  pai.insertBefore(velho, onde);
  P.principal = qual;
  P.aplicarZoom();
  if(P.ao3D) setTimeout(P.ao3D, 60);
 };

 P.aplicarZoom = function(){
  ['imgAx','imgCo','imgSa'].forEach(function(id){
   var im=el(id); if(!im) return;
   var cx=im.closest('[data-v]');
   var noPrincipal = cx && cx.parentNode && cx.parentNode.id==='principal';
   im.style.transform = noPrincipal
     ? ('translate('+P.pan.x+'px,'+P.pan.y+'px) scale('+P.zoom+')') : '';
   im.style.transformOrigin='center center';
  });
  var z=el('zlbl'); if(z) z.textContent=Math.round(P.zoom*100)+'%';
 };
 function zoom(f){ P.zoom=Math.min(6, Math.max(1, P.zoom*f));
  if(P.zoom===1) P.pan={x:0,y:0};   // sem zoom nao ha para onde deslocar
  P.aplicarZoom(); }

 P.reguaLigar = function(){
  P.regua = P.regua ? null : {p1:null};
  var b=el('btregua'); if(b) b.className='fbt'+(P.regua?' on':'');
  var t=el('reguatxt'); if(t) t.textContent = P.regua ? 'clique o primeiro ponto' : '';
 };
 function reguaClique(img, ev, plano){
  var f=P.fracao(img, ev), t=el('reguatxt');
  if(!f){ if(t) t.textContent='clique sobre a imagem'; return; }
  if(!P.regua.p1){ P.regua.p1=f; if(t) t.textContent='clique o segundo ponto'; return; }
  fetch(P.base+'/regua',{method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify(Object.assign({plano:plano, corte:P.corte,
      fx1:P.regua.p1.fx, fy1:P.regua.p1.fy, fx2:f.fx, fy2:f.fy},
      cfg.corpoExtra ? cfg.corpoExtra() : {}))})
  .then(function(r){return r.json()}).then(function(d){
   if(t) t.textContent = d.erro ? d.erro
     : (d.cm.toFixed(2).replace('.',',')+' cm  ('+d.mm.toFixed(1).replace('.',',')+' mm)');
   P.regua={p1:null};
  }).catch(function(e){ if(t) t.textContent='nao consegui medir: '+e; });
 }

 var vs = el('visores');
 function andar(d){
  if(!P.cortes) return;
  var pl = (P.principal === '3d' || !P.principal) ? 'axial' : P.principal;
  P.corte[pl] = Math.max(0, Math.min(P.nc[pl]-1, P.corte[pl] + d));
  P.imagens();
 }
 (function(){
  var a=el('cort_ant'), b=el('cort_prox');
  if(a) a.addEventListener('click', function(){ andar(-1) });
  if(b) b.addEventListener('click', function(){ andar(1) });
 })();

 vs.addEventListener('wheel', function(ev){
  var v=ev.target.closest('[data-v]');
  if(!v || v.getAttribute('data-v')==='3d' || !P.cortes) return;
  ev.preventDefault();
  var passo = ev.shiftKey ? 10 : 1;
  var pl = v.getAttribute('data-v');            // a roda anda NO VISOR sob o cursor
  P.corte[pl] = Math.max(0, Math.min(P.nc[pl]-1,
                 P.corte[pl] + P.rumoCaudal(pl, ev.deltaY>0?passo:-passo)));
  P.imagens();
 }, {passive:false});

 vs.addEventListener('contextmenu', function(ev){
  if(ev.target.closest('[data-v]')) ev.preventDefault();      // o direito e nosso
 });
 vs.addEventListener('pointerdown', function(ev){
  var v=ev.target.closest('[data-v]');
  if(!v || v.getAttribute('data-v')==='3d') return;
  if(ev.button!==0 && ev.button!==2) return;
  P.arrasto={botao:ev.button, x0:ev.clientX, y0:ev.clientY, andou:false,
             wl0:P.wl.slice(), zoom0:P.zoom, pan0:{x:P.pan.x,y:P.pan.y}};
  try{ ev.target.setPointerCapture(ev.pointerId); }catch(e){}
 });
 vs.addEventListener('pointermove', function(ev){
  var A=P.arrasto; if(!A) return;
  var dx=ev.clientX-A.x0, dy=ev.clientY-A.y0;
  if(!A.andou && Math.abs(dx)+Math.abs(dy) < 4) return;    // ainda pode ser clique
  A.andou=true;
  if(A.botao===0 && P.ferramenta==='pan'){
   P.pan = {x: A.pan0.x + dx, y: A.pan0.y + dy};
   P.aplicarZoom();
  } else if(A.botao===2){
   P.zoom=Math.min(6, Math.max(1, A.zoom0*Math.pow(1.006, -dy)));
   P.aplicarZoom();
  }
 });
 function solta(){ P.arrasto=null; }
 vs.addEventListener('pointerup', solta);
 vs.addEventListener('pointercancel', solta);

 vs.addEventListener('click', function(ev){
  var img=ev.target.closest('img'); if(!img) return;
  var cx=img.closest('[data-v]');
  if(!cx || cx.parentNode.id!=='principal') return;   // na pilha o clique troca
  if(P.arrasto && P.arrasto.andou) return;            // arrasto nao e clique
  var plano=cx.getAttribute('data-v');
  if(P.regua){ reguaClique(img, ev, plano); return; }
  var f=P.fracao(img, ev);
  if(f && P.aoClicar) P.aoClicar(plano, f.fx, f.fy);
 });

 el('pilha').addEventListener('click', function(ev){
  var v=ev.target.closest('[data-v]'); if(v) P.trocar(v.getAttribute('data-v'));
 });
 el('zmais').addEventListener('click', function(){ zoom(1.25); });
 el('zmenos').addEventListener('click', function(){ zoom(1/1.25); });
 el('zreset').addEventListener('click', function(){ P.zoom=1; P.pan={x:0,y:0}; P.aplicarZoom(); });
 el('btpan').addEventListener('click', function(){
  P.ferramenta = (P.ferramenta === 'pan') ? 'janela' : 'pan';
  this.className = 'fbt' + (P.ferramenta==='pan' ? ' on' : '');
  var d=el('dicamouse');
  if(d) d.textContent = (P.ferramenta==='pan')
    ? 'roda: corte · esq.: arrastar a imagem · dir.: zoom'
    : 'roda: corte · dir.: zoom · janela: nos botões acima';
 });
 el('btregua').addEventListener('click', P.reguaLigar);
 el('rg').addEventListener('input', function(){
  var pl=P.principal==='3d' ? 'axial' : P.principal;
  P.corte[pl]=+this.value; P.imagens();
 });
 el('btmax').addEventListener('click', function(){
  var g=document.getElementById('grade');
  var max = g ? g.classList.toggle('max') : false;
  this.textContent = max ? 'restaurar' : 'maximizar';
  if(P.ao3D) setTimeout(P.ao3D, 60);
 });
 Array.prototype.forEach.call(document.querySelectorAll('[data-j]'), function(b){
  b.addEventListener('click', function(){
   P.janela=b.getAttribute('data-j');
   Array.prototype.forEach.call(document.querySelectorAll('[data-j]'),
    function(o){ o.className='fbt'+(o===b?' on':''); });
   P.imagens();
  });
 });
 P.aplicarZoom();
 return P;
}
"""

JS_3D = u"""
var N3 = {itens: [], M: null, chaveM: '', escala: 1, arrastando: false,
          ux: 0, uy: 0, pronto: false, eixos: null};
var N3_VISTAS = {ant: ['esq', 'sup', 'ant'],
                 esq: ['post', 'sup', 'esq'],
                 sup: ['dir', 'ant', 'sup']};
var N3_INICIAL = {vista: 'ant', giroY: 0.55, giroX: 0.35};
var N3_LADO = {sup:'S', inf:'I', ant:'A', post:'P', esq:'E', dir:'D'};
var N3_LADO_DICOM = {sup:'S', inf:'I', ant:'A', post:'P', esq:'L', dir:'R'};
var N3_LANG = null;
function n3Lados(){
 var lg = '';
 try{ lg = String(document.documentElement.getAttribute('lang') || '').toLowerCase() }
 catch(e){}
 var t = (!lg || lg.indexOf('pt') === 0) ? N3_LADO : N3_LADO_DICOM;
 if(N3_LANG !== lg){
  N3_LANG = lg;
  try{
   Array.prototype.forEach.call(document.querySelectorAll('[data-n3-lado]'),
    function(b){ var k = b.getAttribute('data-n3-lado'); if(t[k]) b.textContent = t[k] });
  }catch(e){}
 }
 return t;
}
try{ document.addEventListener('DOMContentLoaded', function(){
 setTimeout(n3Lados, 60) }) }catch(e){}
var N3_OPOSTO = {sup:'inf', inf:'sup', ant:'post', post:'ant',
                 esq:'dir', dir:'esq'};

function n3Dir(nome, eixos){
 var ex = (eixos && eixos.length === 3) ? eixos : ['esq', 'post', 'sup'];
 for(var i = 0; i < 3; i++){
  var v = [0, 0, 0];
  if(ex[i] === nome){ v[i] = 1; return v; }
  if(N3_OPOSTO[ex[i]] === nome){ v[i] = -1; return v; }
 }
 return null;
}
function n3MatrizDaVista(nome, eixos){
 var t = N3_VISTAS[nome]; if(!t) return null;
 var X = n3Dir(t[0], eixos), Y = n3Dir(t[1], eixos), Z = n3Dir(t[2], eixos);
 if(!X || !Y || !Z) return null;
 return [X[0], X[1], X[2], Y[0], Y[1], Y[2], Z[0], Z[1], Z[2]];
}
function n3Mul(A, B){
 var C = [];
 for(var i = 0; i < 3; i++) for(var j = 0; j < 3; j++)
  C.push(A[i*3]*B[j] + A[i*3+1]*B[3+j] + A[i*3+2]*B[6+j]);
 return C;
}
function n3RotY(a){ var c = Math.cos(a), s = Math.sin(a);
 return [c, 0, s, 0, 1, 0, -s, 0, c]; }
function n3RotX(a){ var c = Math.cos(a), s = Math.sin(a);
 return [1, 0, 0, 0, c, -s, 0, s, c]; }
function n3Girar(M, dx, dy){
 return n3Mul(n3RotX(dy * 0.011), n3Mul(n3RotY(dx * 0.011), M));
}
function n3MatrizInicial(eixos){
 var M = n3MatrizDaVista(N3_INICIAL.vista, eixos) || [1,0,0, 0,1,0, 0,0,1];
 return n3Mul(n3RotX(N3_INICIAL.giroX), n3Mul(n3RotY(N3_INICIAL.giroY), M));
}
function n3Projetar(M, p){
 return [M[0]*p[0] + M[1]*p[1] + M[2]*p[2],
         M[3]*p[0] + M[4]*p[1] + M[5]*p[2],
         M[6]*p[0] + M[7]*p[1] + M[8]*p[2]];
}
function n3M(){
 var k = JSON.stringify(N3.eixos || null);
 if(!N3.M || N3.chaveM !== k){ N3.M = n3MatrizInicial(N3.eixos); N3.chaveM = k; }
 return N3.M;
}

function n3Canvas(){ return document.getElementById('cv3D') }

function n3Carregar(pasta, rs, estruturas){
 var c = n3Canvas(); if(!c) return;
 var dica = document.getElementById('dica3d');
 if(!estruturas || !estruturas.length){
  N3.itens = []; n3Desenhar();
  n3Dica(dica, 'marque uma estrutura para ver em 3D');
  return;
 }
 n3Dica(dica, 'montando a superfície…');
 fetch('/api/verseg/nuvem3d', {method:'POST',
   headers:{'Content-Type':'application/json'},
   body: JSON.stringify({pasta: pasta, rs: rs, estruturas: estruturas})})
  .then(function(r){ return r.json() })
  .then(function(d){ n3Mostrar(d) })
  .catch(function(e){ n3Dica(dica, 'não consegui montar: ' + e) });
}
function n3Dica(dica, t){
 if(!dica) return;
 if(window.uiTexto) window.uiTexto(dica, t); else dica.textContent = t;
}

function n3Mostrar(d, texto){
 var c = n3Canvas(); if(!c) return;
 var dica = document.getElementById('dica3d');
 d = d || {};
 n3Ajustar(c);
 N3.itens = d.itens || [];
 N3.eixos = d.eixos || null;
 N3.pronto = true;
 var maior = 1;
 N3.itens.forEach(function(it){
  (it.pontos||[]).forEach(function(p){
   var r2 = p[0]*p[0] + p[1]*p[1] + p[2]*p[2];
   if(r2 > maior) maior = r2;
  });
 });
 N3.escala = (Math.min(c.width, c.height) * 0.42) / Math.sqrt(maior);
 if(dica){
  var n = N3.itens.reduce(function(a, it){ return a + (it.pontos||[]).length }, 0);
  var t = d.erro ? d.erro
    : (texto || (N3.itens.length + ' estrutura(s) · ' + n
                 + ' pontos · arraste para girar'));
  if(window.uiTexto) window.uiTexto(dica, t); else dica.textContent = t;
 }
 n3Desenhar();
}

function n3Ajustar(c){
 var r = c.getBoundingClientRect();
 var dpr = window.devicePixelRatio || 1;
 var w = Math.max(80, Math.round(r.width * dpr));
 var h = Math.max(80, Math.round(r.height * dpr));
 if(c.width !== w || c.height !== h){ c.width = w; c.height = h; return true }
 return false;
}

function n3Desenhar(){
 var c = n3Canvas(); if(!c) return;
 n3Ajustar(c);
 var g = c.getContext('2d');
 g.clearRect(0, 0, c.width, c.height);
 if(!N3.itens.length) return;
 var cx = c.width/2 + N3.ux, cy = c.height/2 + N3.uy;
 var M = n3M();
 var todos = [];
 N3.itens.forEach(function(it){
  var cor = it.cor || [120,170,255];
  var P = it.pontos || [], Nn = it.normais || [];
  for(var i = 0; i < P.length; i++){
   var q = n3Projetar(M, P[i]);
   var nz = Nn[i] ? n3Projetar(M, Nn[i])[2] : 0;
   todos.push([q[2], q[0], q[1], cor, nz]);
  }
 });
 todos.sort(function(a, b){ return a[0] - b[0] });
 var r = Math.max(1, Math.round(c.width / 260));
 for(var k = 0; k < todos.length; k++){
  var t = todos[k], cor = t[3];
  var luz = 0.35 + 0.65 * Math.max(0, Math.min(1, (t[4] + 1) / 2));
  g.fillStyle = 'rgb(' + Math.round(cor[0]*luz) + ',' + Math.round(cor[1]*luz)
              + ',' + Math.round(cor[2]*luz) + ')';
  g.fillRect(cx + t[1]*N3.escala - r/2, cy - t[2]*N3.escala - r/2, r, r);
 }
 n3Bussola(g, c, M);
}

function n3Bussola(g, c, M){
 if(!N3.eixos || N3.eixos.length !== 3) return;
 var R = Math.min(c.width, c.height) * 0.11;
 var bx = c.width - 1.5*R - 8*(window.devicePixelRatio||1);
 var by = c.height - 1.5*R - 8*(window.devicePixelRatio||1);
 g.save();
 g.font = Math.round(R*0.42) + 'px monospace';
 g.textAlign = 'center'; g.textBaseline = 'middle';
 for(var i = 0; i < 3; i++){
  var x1 = M[i], y1 = M[3+i], z2 = M[6+i];
  var nome = N3.eixos[i], LADO = n3Lados();
  var pares = [[x1, y1, LADO[nome] || '?', z2],
               [-x1, -y1, LADO[N3_OPOSTO[nome]] || '?', -z2]];
  for(var k = 0; k < 2; k++){
   var p = pares[k];
   var frente = p[3] >= 0;
   g.globalAlpha = frente ? 0.95 : 0.30;
   g.strokeStyle = '#8fa6c8'; g.fillStyle = '#dce6f5';
   g.beginPath(); g.moveTo(bx, by);
   g.lineTo(bx + p[0]*R, by - p[1]*R); g.stroke();
   g.fillText(p[2], bx + p[0]*R*1.22, by - p[1]*R*1.22);
  }
 }
 g.restore();
}

function n3Vista(qual){
 var M = (qual === 'inicial') ? n3MatrizInicial(N3.eixos)
                              : n3MatrizDaVista(qual, N3.eixos);
 if(!M) return;
 N3.M = M; N3.chaveM = JSON.stringify(N3.eixos || null);
 N3.ux = 0; N3.uy = 0;
 n3Desenhar();
}

(function(){
 function liga(){
  var c = n3Canvas(); if(!c) return;
  var ax = 0, ay = 0;
  c.addEventListener('mousedown', function(e){
   N3.arrastando = true; ax = e.clientX; ay = e.clientY; e.preventDefault();
  });
  window.addEventListener('mouseup', function(){ N3.arrastando = false });
  window.addEventListener('mousemove', function(e){
   if(!N3.arrastando) return;
   N3.M = n3Girar(n3M(), e.clientX - ax, e.clientY - ay);
   ax = e.clientX; ay = e.clientY;
   n3Desenhar();
  });
  c.addEventListener('wheel', function(e){
   e.preventDefault();
   N3.escala *= (e.deltaY < 0) ? 1.12 : 0.89;
   n3Desenhar();
  }, {passive:false});
  var tx = 0, ty = 0;
  c.addEventListener('touchstart', function(e){
   if(!e.touches.length) return;
   tx = e.touches[0].clientX; ty = e.touches[0].clientY;
   e.preventDefault();
  }, {passive:false});
  c.addEventListener('touchmove', function(e){
   if(!e.touches.length) return;
   N3.M = n3Girar(n3M(), e.touches[0].clientX - tx, e.touches[0].clientY - ty);
   tx = e.touches[0].clientX; ty = e.touches[0].clientY;
   n3Desenhar(); e.preventDefault();
  }, {passive:false});
  window.addEventListener('resize', function(){ n3Desenhar() });
 }
 if(document.readyState === 'loading'){
  document.addEventListener('DOMContentLoaded', liga);
 } else { liga(); }
})();
"""


JS_UM_EIXO = u"""
function ordemDeBisseccao(n){
 n = Math.floor(+n || 0);
 if(!(n > 0)) return [];
 var fora = [], fila = [[0, n]], k = 0;
 while(k < fila.length){
  var lo = fila[k][0], hi = fila[k][1];
  k++;
  if(lo >= hi) continue;
  var meio = Math.floor((lo + hi) / 2);
  fora.push(meio);
  fila.push([lo, meio]);
  fila.push([meio + 1, hi]);
 }
 return fora;
}

function RadaiCargaUmEixo(cfg){
 var C = {
  n: Math.max(0, Math.floor(+cfg.n || 0)),
  emVoo: Math.max(1, Math.min(3, Math.floor(+cfg.emVoo || 3))),
  ordem: null, cursor: 0,
  voando: {}, nVoando: 0,
  prontos: {}, nProntos: 0,
  falhos: {}, nFalhos: 0,
  alvo: -1, fechado: false, parado: 0,
  pedidos: []
 };
 C.ordem = ordemDeBisseccao(C.n);

 function livre(i){
  return i >= 0 && i < C.n && !C.prontos.hasOwnProperty(i)
      && !C.voando.hasOwnProperty(i) && !C.falhos.hasOwnProperty(i);
 }
 function proximo(){
  if(livre(C.alvo)) return C.alvo;
  while(C.cursor < C.ordem.length){
   if(livre(C.ordem[C.cursor])) return C.ordem[C.cursor];
   C.cursor++;
  }
  return -1;
 }
 function bombear(){
  while(!C.fechado && !C.parado && C.nVoando < C.emVoo){
   var i = proximo();
   if(i < 0) return;
   disparar(i);
  }
 }
 function disparar(i){
  var ctl = (typeof AbortController === 'function') ? new AbortController() : null;
  C.voando[i] = ctl || true;
  C.nVoando++;
  C.pedidos.push(i);
  var p;
  try{ p = cfg.buscar(i, ctl ? ctl.signal : null); }
  catch(e){ p = Promise.reject(e); }
  Promise.resolve(p).then(function(v){
   if(C.fechado){ if(cfg.descartar) cfg.descartar(v); return; }
   delete C.voando[i]; C.nVoando--;
   C.prontos[i] = v; C.nProntos++;
   if(cfg.aoChegar) cfg.aoChegar(i, v);
  }, function(e){
   if(C.fechado) return;
   delete C.voando[i]; C.nVoando--;
   var st = (e && e.status) || 0;
   if(st === 404 || st === 204){
    if(C.parado) return;
    C.parado = st;
    if(cfg.aoParar) cfg.aoParar(st, e);
    return;
   }
   C.falhos[i] = true; C.nFalhos++;
   if(cfg.aoChegar) cfg.aoChegar(i, null);
  }).then(function(){ bombear(); });
 }

 C.iniciar = function(){ bombear(); return C; };
 C.pedir = function(i){ C.alvo = Math.floor(+i); bombear(); };
 C.maisProximo = function(i){
  i = Math.floor(+i);
  for(var d = 0; d < C.n; d++){
   if(C.prontos.hasOwnProperty(i - d)) return i - d;
   if(C.prontos.hasOwnProperty(i + d)) return i + d;
  }
  return -1;
 };
 C.fechar = function(){
  if(C.fechado) return;
  C.fechado = true;
  for(var k in C.voando){
   var ctl = C.voando[k];
   if(ctl && ctl.abort){ try{ ctl.abort(); }catch(e){} }
  }
  C.voando = {}; C.nVoando = 0;
  var vals = C.prontos;
  C.prontos = {}; C.nProntos = 0;
  if(cfg.descartar){ for(var k2 in vals){ cfg.descartar(vals[k2]); } }
 };
 return C;
}

function RadaiUmEixo(alvo, cfg){
 var n = Math.max(0, Math.floor(+cfg.n || 0));
 var V = {n: n, atual: 0, mostrado: -1, carga: null, fechado: false,
          cranial: (cfg.cranial === 1 || cfg.cranial === -1) ? cfg.cranial : 0};
 V.rumoCaudal = function(d){ return V.cranial ? -d * V.cranial : d; };
 function dizer(el, t){
  if(!el) return;
  if(window.uiTexto) window.uiTexto(el, t); else el.textContent = t;
 }
 V.atual = Math.max(0, Math.min(n - 1,
   (cfg.inicio == null) ? Math.floor(n / 2) : Math.floor(+cfg.inicio)));
 alvo.innerHTML =
   '<div class="ue">'
  + '<div class="ue-visor" tabindex="0">'
  +  '<img class="ue-img" alt="" draggable="false">'
  +  '<span class="ue-aviso" data-ue="aviso"></span>'
  + '</div>'
  + '<div class="ue-barra">'
  +  '<button type="button" class="ue-passo" data-ue-passo="-1"'
  +   ' title="corte anterior" aria-label="corte anterior">&#8249;</button>'
  +  '<input type="range" class="ue-rg" min="0" max="' + Math.max(0, n - 1)
  +   '" value="' + V.atual + '" aria-label="corte">'
  +  '<button type="button" class="ue-passo" data-ue-passo="1"'
  +   ' title="próximo corte" aria-label="próximo corte">&#8250;</button>'
  +  '<span class="ue-perto" data-ue="perto" hidden'
  +   ' title="o corte exato ainda está chegando">&#8776;</span>'
  +  '<span class="ue-rot" data-ue="rot"></span>'
  +  '<span class="ue-carga" title="cortes que já chegaram"'
  +   ' aria-label="cortes que já chegaram"><i data-ue="carga"></i></span>'
  +  '<button type="button" class="ue-ajustar" data-ue-ajustar'
  +   ' aria-pressed="false"></button>'
  + '</div>'
  + '</div>';
 var q = function(s){ return alvo.querySelector(s); };
 var img = q('.ue-img'), rg = q('.ue-rg'), rot = q('[data-ue="rot"]');
 var barra = q('[data-ue="carga"]'), aviso = q('[data-ue="aviso"]');
 var perto = q('[data-ue="perto"]'), visor = q('.ue-visor');
 var btAj = q('[data-ue-ajustar]');
 dizer(btAj, 'ajustar');
 V.zoomInicial = Number(window.UI_VISOR_ZOOM_INICIAL) || 1;
 V.zoom = V.zoomInicial;
 V.aplicarZoom = function(){
  img.style.transform = (V.zoom === 1) ? '' : 'scale(' + V.zoom + ')';
  btAj.setAttribute('aria-pressed', V.zoom === 1 ? 'true' : 'false');
 };
 V.ajustar = function(){ V.zoom = 1; V.aplicarZoom(); };
 V.aplicarZoom();
 var ultimoAviso = null;
 function avisar(t){
  if(t === ultimoAviso) return;
  ultimoAviso = t;
  dizer(aviso, t);
 }

 function pintar(){
  if(V.fechado || !V.carga) return;
  var k = V.carga.maisProximo(V.atual);
  if(k >= 0 && k !== V.mostrado){
   img.src = V.carga.prontos[k];
   V.mostrado = k;
  }
  var aprox = (k >= 0 && k !== V.atual);
  perto.hidden = !aprox;
  rot.textContent = (V.atual + 1) + ' / ' + n;
  rot.className = 'ue-rot' + (aprox ? ' ue-aprox' : '');
  barra.style.width = (n ? Math.round(100 * V.carga.nProntos / n) : 0) + '%';
  if(!V.carga.parado) avisar(V.aviso());
 }
 V.aviso = function(){
  var C = V.carga;
  if(C.nProntos === 0){
   return (C.nFalhos >= n) ? 'não consegui abrir a série' : 'abrindo a série…';
  }
  return C.falhos.hasOwnProperty(V.atual) ? 'este corte não pôde ser lido' : '';
 };
 V.ir = function(i){
  if(V.fechado || !n) return;
  V.atual = Math.max(0, Math.min(n - 1, Math.floor(+i)));
  rg.value = String(V.atual);
  V.carga.pedir(V.atual);
  pintar();
 };

 V.carga = RadaiCargaUmEixo({
  n: n, emVoo: cfg.emVoo || 3,
  buscar: function(i, sinal){
   return fetch(cfg.url(i), sinal ? {signal: sinal} : {})
    .then(function(r){
     if(r.status !== 200){
      var e = new Error('http ' + r.status); e.status = r.status;
      try{ e.modalidade = r.headers.get('X-RadAI-Modalidade') || ''; }
      catch(x){ e.modalidade = ''; }
      throw e;
     }
     return r.blob();
    })
    .then(function(b){ return URL.createObjectURL(b); });
  },
  aoChegar: function(){
   if(document.body && !document.body.contains(alvo)){ V.fechar(); return; }
   pintar();
  },
  aoParar: function(st, e){
   avisar(st === 204 ? 'esta série não tem imagem para mostrar'
                     : 'recarregue a lista de séries');
   if(cfg.aoParar) cfg.aoParar(st, e);
  },
  descartar: function(u){ try{ URL.revokeObjectURL(u); }catch(e){} }
 });

 visor.addEventListener('wheel', function(ev){
  ev.preventDefault();
  if(!ev.deltaY) return;
  var passo = (ev.deltaY > 0 ? 1 : -1) * (ev.shiftKey ? 10 : 1);
  V.ir(V.atual + V.rumoCaudal(passo));
 }, {passive: false});
 visor.addEventListener('keydown', function(ev){
  var c = {ArrowDown: 1, ArrowUp: -1, PageDown: 10, PageUp: -10}[ev.key];
  var d = c ? V.rumoCaudal(c) : {ArrowRight: 1, ArrowLeft: -1}[ev.key];
  if(!d) return;
  ev.preventDefault();
  V.ir(V.atual + d);
 });
 rg.addEventListener('input', function(){ V.ir(+rg.value); });
 alvo.querySelector('.ue-barra').addEventListener('click', function(ev){
  var b = ev.target.closest ? ev.target.closest('[data-ue-passo]') : null;
  if(b) V.ir(V.atual + (+b.getAttribute('data-ue-passo')));
  if(ev.target.closest && ev.target.closest('[data-ue-ajustar]')){
   V.zoom = (V.zoom === 1) ? V.zoomInicial : 1;
   V.aplicarZoom();
  }
 });

 V.fechar = function(){
  if(V.fechado) return;
  V.fechado = true;
  V.carga.fechar();
  img.removeAttribute('src');
 };
 V.carga.pedir(V.atual);
 pintar();
 return V;
}

function umEixoFechar(alvo){
 if(!alvo) return;
 var s = alvo.__radaiUmEixo;
 if(s){ s.fechado = true; if(s.visor) s.visor.fechar(); }
 alvo.__radaiUmEixo = null;
 alvo.innerHTML = '';
}
function umEixoAbrir(alvo, serie){
 if(!alvo) return Promise.resolve(null);
 umEixoFechar(alvo);
 var sessao = {fechado: false, visor: null};
 alvo.__radaiUmEixo = sessao;
 alvo.innerHTML = '<span class="sub ue-abrindo"></span>';
 var msg = alvo.querySelector('.ue-abrindo');
 var dizer = function(t){
  if(window.uiTexto) window.uiTexto(msg, t); else msg.textContent = t;
 };
 dizer('abrindo a série…');
 serie = serie || {};
 return fetch('/api/umeixo/abrir', {method: 'POST',
   headers: {'Content-Type': 'application/json'},
   body: JSON.stringify({pasta: serie.pasta || '', zip: serie.zip || '',
                         uid: serie.uid || ''})})
  .then(function(r){ return r.json(); })
  .then(function(d){
   if(sessao.fechado) return null;
   if(!d || d.erro || !d.b){
    dizer((d && d.erro) || 'não consegui abrir a série');
    return null;
   }
   var b = d.b, jan = d.janela || 'mediastino';
   sessao.visor = RadaiUmEixo(alvo, {
    n: d.cortes, inicio: d.central, emVoo: 3, cranial: d.cranial,
    url: function(i){
     return '/api/umeixo/corte?b=' + encodeURIComponent(b)
          + '&corte=' + i + '&janela=' + encodeURIComponent(jan);
    }
   });
   return sessao.visor;
  })
  .catch(function(e){
   if(!sessao.fechado) dizer('não consegui abrir a série');
   return null;
  });
}

var UM_EIXO_CAIXAS = {};
function _umEixoVivo(caixa){
 var s = caixa && caixa.__radaiUmEixo;
 return !!(s && !s.fechado && !(s.visor && s.visor.fechado));
}
function umEixoNaCelula(celula, chave, serie){
 if(!celula) return null;
 chave = String(chave);
 var caixa = UM_EIXO_CAIXAS[chave];
 var vivo = _umEixoVivo(caixa);
 if(!vivo){
  if(caixa) umEixoFechar(caixa);
  caixa = document.createElement('div');
  caixa.className = 'ue-caixa';
  UM_EIXO_CAIXAS[chave] = caixa;
 }
 if(caixa.parentNode !== celula){
  celula.innerHTML = '';
  celula.appendChild(caixa);
 }
 if(!vivo) umEixoAbrir(caixa, serie);
 return caixa;
}
function umEixoSoltar(chave){
 chave = String(chave);
 var caixa = UM_EIXO_CAIXAS[chave];
 delete UM_EIXO_CAIXAS[chave];
 if(!caixa) return;
 umEixoFechar(caixa);
 if(caixa.parentNode) caixa.parentNode.removeChild(caixa);
}
function umEixoVarrer(){
 var chaves = [], soltas = 0;
 for(var k in UM_EIXO_CAIXAS){
  if(UM_EIXO_CAIXAS.hasOwnProperty(k)) chaves.push(k);
 }
 for(var i = 0; i < chaves.length; i++){
  var caixa = UM_EIXO_CAIXAS[chaves[i]];
  var naPagina = !!(caixa && document.body && document.body.contains(caixa));
  if(!naPagina){ umEixoSoltar(chaves[i]); soltas++; }
 }
 return soltas;
}
"""


CSS_UM_EIXO = u"""
.ue{display:flex;flex-direction:column;gap:6px;min-width:0}
.ue-visor{position:relative;background:var(--img-fundo,#000);border:1px solid var(--line);
 border-radius:var(--r-md,6px);display:flex;align-items:center;
 justify-content:center;min-height:180px;overflow:hidden;outline:none}
.ue-visor:focus-visible{border-color:var(--accent)}
.ue-img{display:block;width:100%;height:auto;aspect-ratio:1/1;
 max-height:min(62vh,520px);object-fit:contain;user-select:none;
 transform-origin:center center}
.ue-aviso{position:absolute;left:8px;right:8px;bottom:8px;text-align:center;
 font-size:11.5px;color:var(--text-dim);pointer-events:none}
.ue-barra{display:flex;align-items:center;gap:6px;flex-wrap:wrap;min-width:0}
.ue-barra .ue-rg{flex:1;min-width:120px}
.ue-passo{min-width:26px;padding:3px 6px;font-size:15px;line-height:1;
 border-radius:4px;border:1px solid var(--line-strong,var(--line));
 background:transparent;color:var(--text-muted);cursor:pointer}
.ue-passo:hover{border-color:var(--accent);color:var(--text)}
.ue-ajustar{padding:3px 8px;font-size:11px;line-height:1.2;border-radius:4px;
 border:1px solid var(--line-strong,var(--line));background:transparent;
 color:var(--text-muted);cursor:pointer}
.ue-ajustar:hover{border-color:var(--accent);color:var(--text)}
.ue-ajustar[aria-pressed="true"]{border-color:var(--accent);color:var(--text)}
.ue-rot{font-family:var(--mono,monospace);font-size:11px;color:var(--text-muted);
 min-width:64px;text-align:right;white-space:nowrap}
.ue-perto{font-family:var(--mono,monospace);font-size:12px;color:var(--text-dim);
 cursor:help}
.ue-perto[hidden]{display:none}
.ue-rot.ue-aprox{color:var(--text-dim)}
.ue-carga{flex:0 0 64px;height:3px;border-radius:2px;overflow:hidden;
 background:var(--line)}
.ue-carga i{display:block;height:100%;width:0;background:var(--accent);
 transition:width .2s ease-out}
@media (prefers-reduced-motion:reduce){.ue-carga i{transition:none}}
"""


JS = JS_PALCO + JS_3D + JS_UM_EIXO
CSS = CSS + CSS_UM_EIXO


def html(com_3d=True):
    tres = u"""
      <div class="visor" data-v="coronal">
        <img id="imgCo" alt="coronal"><span class="rot">Coronal</span>
        <span class="troca">trazer para o principal</span>
      </div>
      <div class="visor" data-v="sagital">
        <img id="imgSa" alt="sagital"><span class="rot">Sagital</span>
        <span class="troca">trazer para o principal</span>
      </div>"""
    if com_3d:
        tres += u"""
      <div class="visor" id="v3D" data-v="3d">
        <canvas id="cv3D" width="300" height="300"></canvas>
        <span class="rot">3D · arraste para girar</span>
        <span class="v3-vistas">
          <button type="button" onclick="n3Vista('ant')" title="anterior" aria-label="anterior" data-n3-lado="ant">A</button>
          <button type="button" onclick="n3Vista('esq')" title="esquerda do paciente" aria-label="esquerda do paciente" data-n3-lado="esq">E</button>
          <button type="button" onclick="n3Vista('sup')" title="superior" aria-label="superior" data-n3-lado="sup">S</button>
          <button type="button" onclick="n3Vista('inicial')" title="voltar ao início" aria-label="voltar ao início">&#8635;</button>
        </span>
        <span class="dica3d" id="dica3d">marque uma estrutura para ver em 3D</span>
        <span class="troca">trazer para o principal</span>
      </div>"""
    return u"""
    <div class="visores" id="visores">
      <div class="principal" id="principal">
        <div class="visor" id="vAx" data-v="axial">
          <img id="imgAx" alt="axial"><span class="rot">Axial</span>
          <span class="troca">trazer para o principal</span>
        </div>
      </div>
      <div class="pilha" id="pilha">%s
      </div>
    </div>
    <div class="ferr" id="ferr">
      <span class="grupolbl">corte</span>
      <input type="range" id="rg" min="0" max="0" value="0">
        <button class="fbt passo1" id="cort_ant" title="corte anterior">&#8249;</button>
        <button class="fbt passo1" id="cort_prox" title="proximo corte">&#8250;</button>
      <span class="cortelbl" id="lbl">—</span>
      <span class="sep"></span>
      <span class="grupolbl">janela</span>
      <button class="fbt" data-j="pulmao">pulmão</button>
      <button class="fbt on" data-j="mediastino">mediastino</button>
      <button class="fbt" data-j="osso">osso</button>
      <span class="sep"></span>
      <span class="grupolbl">zoom</span>
      <button class="fbt" id="zmenos">−</button>
      <button class="fbt" id="zmais">+</button>
      <span class="cortelbl" id="zlbl">100%%</span>
      <button class="fbt" id="zreset">ajustar</button>
      <button class="fbt" id="btpan" title="mão: clique aqui e arraste a imagem com o botão esquerdo">@ICO_MOVER@<span data-radai-frase>mover</span></button>
      <span class="sep"></span>
      <button class="fbt" id="btregua">medir cm</button>
      <span class="cortelbl" id="reguatxt"></span>
      <span class="sep"></span>
      <button class="fbt" id="btmax">maximizar</button>
      <span class="dicamouse" id="dicamouse">roda: corte · esq.: janela · dir.: zoom</span>
    </div>""" % tres
