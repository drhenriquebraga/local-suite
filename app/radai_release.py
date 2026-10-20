# -*- coding: utf-8 -*-

MARCA = "radai-soltar-js"

SO_O_NOME = (u"O navegador não entrega o caminho de uma pasta arrastada — "
             u"escolha-a aqui no explorador.")
TITULO = u"Arraste aqui a pasta ou o .zip do exame, ou clique para procurar"
DICA = (u"o caminho vai para o campo acima; nada é copiado — o RTSTRUCT é "
        u"gravado ao lado da série")
RECEBIDO = u"caminho recebido do Explorer"

CSS = u"""<style id="radai-soltar-css">
.ui-envio.rs-area{flex-direction:row;justify-content:flex-start;gap:12px;
 min-height:0;margin:8px 0 0;padding:10px 14px;text-align:left;
 border-radius:var(--r-lg,8px)}
.ui-envio.rs-area .ui-envio-ic{width:34px;height:34px;font-size:16px;flex:none}
.ui-envio.rs-area .ui-envio-ic svg{width:18px;height:18px}
.rs-area-tx{display:flex;flex-direction:column;gap:2px;min-width:0}
.ui-envio.rs-area .ui-envio-tit{font-size:13px}
.ui-envio.rs-area .ui-envio-est{min-height:0}
.ui-envio.rs-area .ui-envio-est:empty{display:none}
.ui-envio.rs-area .ui-envio-est.rs-aviso{color:var(--aviso,#E1B23B)}
</style>"""

JS = u"""<script id="radai-soltar-js">
(function(){
 var ALVOS = {pasta: 'varrer', vr_pasta: 'vrVarrer'};
 var SO_O_NOME = @SO_O_NOME@, TITULO = @TITULO@, DICA = @DICA@, RECEBIDO = @RECEBIDO@;

 var BS = String.fromCharCode(92);
 function absoluto(t){
  var u = t.charAt(2);
  if(/[A-Za-z]/.test(t.charAt(0)) && t.charAt(1) === ':' && (u === BS || u === '/')) return true;
  return t.slice(0, 2) === BS + BS && t.length > 2 && u !== BS;
 }
 function caminhoDe(dt){
  var t = '';
  try { t = (dt.getData('text/plain') || dt.getData('text') || '').trim() } catch(e){}
  if(t){
   t = t.split(/[\\r\\n]+/)[0].trim().replace(/^"(.*)"$/, '$1');
   if(t.toLowerCase().indexOf('file:///') === 0){
    try { t = decodeURIComponent(t.slice(8)).split('/').join(BS) } catch(e){}
   }
   if(absoluto(t)) return {caminho: t, certeza: true};
  }
  try {
   var f = dt.files && dt.files[0];
   if(f && f.name) return {caminho: '', certeza: false};
  } catch(e){}
  return t ? {caminho: '', certeza: false} : null;
 }
 function escreve(no, frase, aviso){
  if(window.uiTexto) window.uiTexto(no, frase); else no.textContent = frase;
  no.classList.toggle('rs-aviso', !!aviso);
  try{ if(window.radaiRetraduzir) window.radaiRetraduzir() }catch(e){}
 }
 function usar(el, c){
  if(!c) return;
  el.value = c;
  el.dispatchEvent(new Event('input', {bubbles:true}));
  el.dispatchEvent(new Event('change', {bubbles:true}));
  var f = window[ALVOS[el.id]];
  if(typeof f === 'function') f(); else el.focus();
 }
 function explorar(el, area){
  if(!window.uiExplorador) return;
  window.uiExplorador({titulo: 'Escolher a pasta', origem: area,
   inicial: (el.value || '').trim(), aoUsar: function(c){ usar(el, c) }});
 }
 function icone(){
  var m = document.getElementById('ui-ico-subir');
  return m ? m.innerHTML : '';
 }

 function ligar(id){
  var el = document.getElementById(id);
  if(!el || el.dataset.rsLigado) return;
  el.dataset.rsLigado = '1';
  var ancora = (el.closest && el.closest('.cam-linha, .vr-busca')) || el;
  var area = document.createElement('div');
  area.className = 'ui-envio rs-area';
  area.id = 'rs_area_' + id;
  area.tabIndex = 0;
  area.setAttribute('role', 'button');
  area.innerHTML = '<span class="ui-envio-ic" aria-hidden="true">' + icone() + '</span>'
   + '<span class="rs-area-tx"><span class="ui-envio-tit"></span>'
   + '<span class="ui-envio-dica"></span>'
   + '<span class="ui-envio-est" role="status"></span></span>';
  var tit = area.querySelector('.ui-envio-tit'), est = area.querySelector('.ui-envio-est');
  escreve(tit, TITULO); escreve(area.querySelector('.ui-envio-dica'), DICA);
  area.setAttribute('aria-label', TITULO);
  ancora.parentNode.insertBefore(area, ancora.nextSibling);

  var fundo = 0;
  function sobre(v){ area.classList.toggle('sobre', v); if(!v) area.style.setProperty('--dx', '0px') }
  [area, el].forEach(function(alvo){
   alvo.addEventListener('dragenter', function(e){ e.preventDefault(); e.stopPropagation();
    fundo++; sobre(true) }, {passive:false});
   alvo.addEventListener('dragover', function(e){ e.preventDefault(); e.stopPropagation();
    try{ e.dataTransfer.dropEffect = 'copy' }catch(err){}
    var r = area.getBoundingClientRect();
    var dx = Math.max(-10, Math.min(10, (e.clientX - (r.left + r.width / 2)) / 18));
    area.style.setProperty('--dx', dx.toFixed(1) + 'px');
    sobre(true) }, {passive:false});
   alvo.addEventListener('dragleave', function(e){ e.preventDefault(); e.stopPropagation();
    fundo = Math.max(0, fundo - 1); if(!fundo) sobre(false) }, {passive:false});
   alvo.addEventListener('drop', function(e){
    e.preventDefault(); e.stopPropagation(); fundo = 0; sobre(false);
    var r = caminhoDe(e.dataTransfer);
    if(!r) return;
    if(r.certeza){ escreve(est, RECEBIDO, false); usar(el, r.caminho); return }
    escreve(est, SO_O_NOME, true);
    explorar(el, area);
   }, {passive:false});
  });
  area.addEventListener('click', function(){ explorar(el, area) });
  area.addEventListener('keydown', function(e){
   if(e.key === 'Enter' || e.key === ' '){ e.preventDefault(); explorar(el, area) } });
 }

 function ligarTodos(){ Object.keys(ALVOS).forEach(ligar) }
 if(document.readyState === 'loading')
  document.addEventListener('DOMContentLoaded', ligarTodos);
 else ligarTodos();
 try { new MutationObserver(ligarTodos).observe(document.body,
        {childList:true, subtree:true}) } catch(e){}
})();
</script>"""


def _js():
    import json
    return (JS.replace(u"@SO_O_NOME@", json.dumps(SO_O_NOME, ensure_ascii=False))
              .replace(u"@TITULO@", json.dumps(TITULO, ensure_ascii=False))
              .replace(u"@DICA@", json.dumps(DICA, ensure_ascii=False))
              .replace(u"@RECEBIDO@", json.dumps(RECEBIDO, ensure_ascii=False)))


def aplicar(pagina):
    if not pagina or MARCA in pagina:
        return pagina
    baixa = pagina.lower()
    i = baixa.find(u"</head>")
    if i < 0:
        return pagina
    p = pagina[:i] + CSS + pagina[i:]
    j = p.lower().rfind(u"</body>")
    if j < 0:
        return p
    return p[:j] + _js() + p[j:]
