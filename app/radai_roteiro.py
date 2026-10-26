# -*- coding: utf-8 -*-
import json

CHAVE = u"GUIA_VISTO"
VERSAO_DO_GUIA = u"1"
ROTA_API = u"/api/roteiro"

PASSOS = (
    {"rota": u"/", "alvo": u"",
     "titulo": u"Bem-vindo à Local Suite",
     "texto": u"Seis apps de radioterapia que rodam inteiros nesta estação: "
              u"nenhuma imagem sai daqui. Este guia mostra os primeiros "
              u"passos sobre as telas de verdade."},
    {"rota": u"/", "alvo": u"a[href=\"/bridge\"]",
     "titulo": u"DicomBridge: o exame externo até o TPS",
     "texto": u"Carrega arquivos, uma pasta ou um CD, confere cada série e "
              u"converte para um DICOM que o sistema de planejamento "
              u"aceita."},
    {"rota": u"/bridge/laudo", "alvo": u".ui-envio",
     "titulo": u"Carregar, conferir, converter",
     "texto": u"Arraste o exame para cá, escolha a série, leia os alertas do "
              u"diagnóstico e entregue numa pasta nova. Imagem JPEG ou PNG "
              u"também entra aqui."},
    {"rota": u"/autocontorno", "alvo": u"a[href=\"/lote\"]",
     "titulo": u"ContourLab: a segmentação automática",
     "texto": u"«Rodar agora» segmenta a série que você escolher; «Ver "
              u"segmentação» abre o que já saiu, para revisar."},
    {"rota": u"/lote", "alvo": u"",
     "titulo": u"Rodar agora",
     "texto": u"Aponte a pasta, escolha a série e o modo (FAST, AUTO ou "
              u"PERSONALIZADO) e clique em INICIAR. Toda estrutura sai como "
              u"sugestão não aprovada: rascunho sujeito a revisão médica no "
              u"sistema de planejamento."},
    {"rota": u"/ver", "alvo": u"",
     "titulo": u"Ver segmentação",
     "texto": u"Escolha uma série do acervo e compare os conjuntos lado a "
              u"lado, em dois visores travados."},
    {"rota": u"/recon3d/anatomia", "alvo": u"",
     "titulo": u"Reconstruções 3D: anatomia geral",
     "texto": u"A reconstrução 3D dos casos já segmentados, para estudar a "
              u"anatomia girando o modelo."},
    {"rota": u"/config", "alvo": u"",
     "titulo": u"Configurações principais",
     "texto": u"Aqui ficam a pasta favorita, o idioma, o tema e o ritmo do "
              u"vigia. Para rever este guia: Configurações › Geral › Ver o "
              u"guia de novo."},
)

ROTULOS = {
    "proximo": u"Próximo",
    "voltar": u"Voltar",
    "pular": u"Pular guia",
    "concluir": u"Concluir",
    "rotulo": u"Guia inicial",
}


def visto(valor):
    return str(valor or u"").split(u"#")[0].strip() == VERSAO_DO_GUIA


def ler_marca():
    try:
        import radai_config
        return radai_config.chave_configurada(CHAVE)
    except Exception:
        return u""


def gravar_marca(caminho=None):
    try:
        import radai_config
        ok, erro = radai_config.escrever(caminho or radai_config.caminho_padrao(),
                                         {CHAVE: VERSAO_DO_GUIA})
        return bool(ok), erro
    except Exception as e:
        return False, u"%s: %s" % (type(e).__name__, str(e)[:120])


def montar(app):
    from fastapi import Request

    @app.post(ROTA_API)
    async def _roteiro(request: Request):
        try:
            corpo = await request.json()
        except Exception:
            corpo = {}
        if isinstance(corpo, dict) and corpo.get("visto") is True:
            ok, erro = gravar_marca()
            return {"ok": ok, "erro": erro, "visto": ok}
        return {"visto": visto(ler_marca()), "versao": VERSAO_DO_GUIA}

    return app


MARCA = u"radai-roteiro-js"

CSS = u"""<style id="radai-roteiro-css">
.rt-veu{position:fixed;inset:0;z-index:6000;background:rgba(4,8,16,0);
 transition:background-color .26s ease;pointer-events:auto}
.rt-veu.vis{background:rgba(4,8,16,.58)}
.rt-veu.com-furo{background:transparent!important}
.rt-furo{position:fixed;z-index:6001;border-radius:var(--r-xl);pointer-events:none;
 box-shadow:0 0 0 2px var(--accent),0 0 0 100vmax rgba(4,8,16,.58);
 opacity:0;transition:opacity .26s ease,left .32s cubic-bezier(.22,1,.36,1),
 top .32s cubic-bezier(.22,1,.36,1),width .32s cubic-bezier(.22,1,.36,1),
 height .32s cubic-bezier(.22,1,.36,1)}
.rt-furo.vis{opacity:1}
.rt-cartao{position:fixed;z-index:6002;width:min(380px,calc(100vw - 32px));
 box-sizing:border-box;padding:18px 18px 14px;border-radius:var(--r-2xl);
 background:var(--panel);color:var(--text);border:1px solid var(--line-strong);
 box-shadow:var(--sombra);display:flex;flex-direction:column;gap:10px;
 opacity:0;transform:translateY(8px) scale(.98);filter:blur(2px);
 transition:opacity .2s ease,transform .26s cubic-bezier(.22,1,.36,1),
 filter .26s cubic-bezier(.22,1,.36,1)}
.rt-cartao.vis{opacity:1;transform:none;filter:none}
.rt-rotulo{margin:0;font:400 10px/1 var(--mono);letter-spacing:.16em;
 text-transform:uppercase;color:var(--text-dim)}
.rt-titulo{margin:0;font:650 16px/1.3 var(--font-display);letter-spacing:-.01em;
 color:var(--text);text-wrap:balance}
.rt-texto{margin:0;font-size:13.5px;line-height:1.6;color:var(--text-muted)}
.rt-pe{display:flex;align-items:center;gap:8px;margin-top:6px;flex-wrap:wrap}
.rt-conta{flex:1 1 auto;font:400 11px/1 var(--mono);color:var(--text-dim);
 font-variant-numeric:tabular-nums}
.rt-pular{background:transparent;border:0;padding:8px 6px;color:var(--text-muted);
 font:500 12.5px/1.2 var(--font-display);cursor:pointer;border-radius:var(--r-md)}
.rt-pular:hover{color:var(--text)}
.rt-pular:focus-visible,.rt-cartao .ui-bt:focus-visible{outline:2px solid var(--accent);
 outline-offset:2px}
.rt-pontos{display:flex;gap:5px}
.rt-pontos i{width:6px;height:6px;border-radius:var(--r-pill);background:var(--line-strong)}
.rt-pontos i.agora{background:var(--accent)}
@media (prefers-reduced-motion:reduce){
 .rt-veu,.rt-furo,.rt-cartao{transition:none}
 .rt-cartao{transform:none;filter:none}}
</style>"""

JS = u"""<script id="radai-roteiro-js">
(function(){
 if(window.radaiGuiaAbrir) return;
 var PASSOS = @PASSOS@;
 var R = @ROTULOS@;
 var CHAVE = 'radai_roteiro_passo';
 var aberto = null;
 function T(pt){ try{ return window.radaiFrase ? window.radaiFrase(pt) : pt }catch(e){ return pt } }
 function escrever(no, texto){ if(window.uiTexto) window.uiTexto(no, texto); else no.textContent = texto }
 function caminho(){ var p = location.pathname || '/'; return p === '/suite' ? '/' : p }
 function lerPasso(){ try{ var v = sessionStorage.getItem(CHAVE); return v === null ? -1 : parseInt(v, 10) }catch(e){ return -1 } }
 function guardar(i){ try{ if(i < 0) sessionStorage.removeItem(CHAVE); else sessionStorage.setItem(CHAVE, String(i)) }catch(e){} }
 function marcarVisto(){
  try{ fetch('@API@', {method:'POST', headers:{'Content-Type':'application/json'}, body:'{"visto":true}'}) }catch(e){}
 }
 function fechar(){
  if(!aberto) return;
  var a = aberto; aberto = null;
  document.removeEventListener('keydown', a.tecla, true);
  window.removeEventListener('resize', a.medir);
  [a.veu, a.furo, a.cartao].forEach(function(n){ n.classList.remove('vis') });
  setTimeout(function(){ [a.veu, a.furo, a.cartao].forEach(function(n){ if(n.parentNode) n.parentNode.removeChild(n) }) }, 220);
  try{ if(a.antes && a.antes.focus) a.antes.focus() }catch(e){}
 }
 function pular(){ guardar(-1); marcarVisto(); fechar() }
 function ir(i){
  if(i < 0 || i >= PASSOS.length){ guardar(-1); fechar(); return }
  guardar(i);
  if(PASSOS[i].rota !== caminho()){ fechar(); location.href = PASSOS[i].rota; return }
  mostrar(i);
 }
 function alvoDe(p){
  if(!p.alvo) return null;
  try{
   var n = document.querySelector(p.alvo);
   if(!n) return null;
   var r = n.getBoundingClientRect();
   return (r.width > 4 && r.height > 4) ? n : null;
  }catch(e){ return null }
 }
 function mostrar(i){
  fechar();
  var p = PASSOS[i];
  var veu = document.createElement('div'); veu.className = 'rt-veu';
  var furo = document.createElement('div'); furo.className = 'rt-furo';
  var c = document.createElement('div'); c.className = 'rt-cartao';
  var idt = 'rt-t' + i, idx = 'rt-x' + i;
  c.setAttribute('role', 'dialog'); c.setAttribute('aria-modal', 'true');
  c.setAttribute('aria-labelledby', idt); c.setAttribute('aria-describedby', idx);
  c.setAttribute('data-roteiro-passo', String(i));
  c.innerHTML = '<p class="rt-rotulo"></p><h2 class="rt-titulo" id="' + idt + '"></h2>'
   + '<p class="rt-texto" id="' + idx + '"></p>'
   + '<div class="rt-pe"><span class="rt-conta"></span>'
   + '<button type="button" class="rt-pular"></button>'
   + (i > 0 ? '<button type="button" class="ui-bt rt-voltar"></button>' : '')
   + '<button type="button" class="ui-bt pri rt-proximo"></button></div>';
  escrever(c.querySelector('.rt-rotulo'), T(R.rotulo));
  escrever(c.querySelector('.rt-titulo'), T(p.titulo));
  escrever(c.querySelector('.rt-texto'), T(p.texto));
  escrever(c.querySelector('.rt-conta'), String(i + 1) + ' / ' + String(PASSOS.length));
  escrever(c.querySelector('.rt-pular'), T(R.pular));
  var ult = (i === PASSOS.length - 1);
  escrever(c.querySelector('.rt-proximo'), T(ult ? R.concluir : R.proximo));
  if(i > 0) escrever(c.querySelector('.rt-voltar'), T(R.voltar));
  document.body.appendChild(veu); document.body.appendChild(furo); document.body.appendChild(c);
  c.querySelector('.rt-pular').addEventListener('click', pular);
  c.querySelector('.rt-proximo').addEventListener('click', function(){ if(ult){ guardar(-1); fechar() } else ir(i + 1) });
  if(i > 0) c.querySelector('.rt-voltar').addEventListener('click', function(){ ir(i - 1) });
  function medir(){
   var n = alvoDe(p), vw = window.innerWidth, vh = window.innerHeight;
   var cw = c.offsetWidth, ch = c.offsetHeight, x, y;
   if(n){
    var r = n.getBoundingClientRect(), m = 6;
    furo.style.left = (r.left - m) + 'px'; furo.style.top = (r.top - m) + 'px';
    furo.style.width = (r.width + 2 * m) + 'px'; furo.style.height = (r.height + 2 * m) + 'px';
    furo.classList.add('vis'); veu.classList.add('com-furo');
    x = Math.min(Math.max(16, r.left), vw - cw - 16);
    y = (r.bottom + 14 + ch <= vh - 16) ? r.bottom + 14 : Math.max(16, r.top - 14 - ch);
   } else {
    furo.classList.remove('vis'); veu.classList.remove('com-furo');
    x = Math.round((vw - cw) / 2); y = Math.round((vh - ch) / 2);
   }
   c.style.left = Math.round(x) + 'px'; c.style.top = Math.round(y) + 'px';
  }
  function tecla(e){
   if(e.key === 'Escape'){ e.preventDefault(); e.stopPropagation(); pular() }
   else if(e.key === 'Tab' && window.uiPrenderFoco) window.uiPrenderFoco(c, e);
  }
  aberto = {veu:veu, furo:furo, cartao:c, tecla:tecla, medir:medir, antes:document.activeElement};
  document.addEventListener('keydown', tecla, true);
  window.addEventListener('resize', medir);
  medir();
  setTimeout(function(){ if(aberto && aberto.cartao === c) medir() }, 700);
  setTimeout(function(){ if(aberto && aberto.cartao === c) medir() }, 1500);
  requestAnimationFrame(function(){ requestAnimationFrame(function(){
   veu.classList.add('vis'); c.classList.add('vis'); medir();
   try{ c.querySelector('.rt-proximo').focus() }catch(e){}
  }) });
 }
 window.radaiGuiaAbrir = function(){
  marcarVisto();
  guardar(0);
  if(caminho() === '/') mostrar(0); else location.href = '/';
 };
 function inicio(){ return document.body && document.body.getAttribute('data-tela') === 'inicio' }
 // GUARDA: o guia abre sozinho so na janela do app (a do perfil proprio,
 // achada pelo motor); numa aba comum ou num navegador de bateria ele nao se
 // impoe, e o botao de rever continua valendo.
 function naJanelaDoApp(f){
  if(window.radaiJanelaDoApp === true){ f(); return }
  if(window.radaiJanelaDoApp === false) return;
  var feito = false;
  function ouvir(e){
   if(feito) return;
   feito = true;
   document.removeEventListener('radai-janela', ouvir);
   if(e && e.detail && e.detail.ok) f();
  }
  document.addEventListener('radai-janela', ouvir);
  setTimeout(function(){ if(!feito){ feito = true; document.removeEventListener('radai-janela', ouvir) } }, 8000);
 }
 function aoCarregar(){
  var i = lerPasso();
  if(i >= 0 && i < PASSOS.length){
   if(PASSOS[i].rota === caminho()) setTimeout(function(){ mostrar(i) }, 500);
   else guardar(-1);
   return;
  }
  if(!inicio()) return;
  naJanelaDoApp(function(){
   fetch('@API@', {method:'POST', headers:{'Content-Type':'application/json'}, body:'{}'})
    .then(function(r){ return r.ok ? r.json() : null })
    .then(function(d){ if(d && d.visto === false) setTimeout(window.radaiGuiaAbrir, 600) })
    .catch(function(){});
  });
 }
 if(document.readyState === 'complete') aoCarregar();
 else window.addEventListener('load', aoCarregar);
})();
</script>"""


def _js():
    passos = [{"rota": p["rota"], "alvo": p["alvo"], "titulo": p["titulo"],
               "texto": p["texto"]} for p in PASSOS]
    return (JS.replace(u"@PASSOS@", json.dumps(passos, ensure_ascii=False)
                       .replace(u"</", u"<\\/"))
            .replace(u"@ROTULOS@", json.dumps(ROTULOS, ensure_ascii=False))
            .replace(u"@API@", ROTA_API))


PARA_A_CASCA = CSS + _js()
