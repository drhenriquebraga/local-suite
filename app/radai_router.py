# -*- coding: utf-8 -*-
import radai_breadcrumb
import radai_menu


def pagina():
    try:
        import radai_porta
        p = radai_porta.pagina()
    except Exception:
        # GUARDA: sem o módulo da porta ela ainda abre, com os nomes e os links.
        p = (PAGINA.replace("@TOPO@", _topo_de_reserva()).replace("@CSS@", u"")
             .replace("@CORPO@", _porta_de_reserva()).replace("@AVISO_VERSAO@", u""))
    aviso = (u'<style id="radai-versao-css">' + CSS_AVISO_VERSAO + u"</style>"
             + JS_AVISO_VERSAO)
    fim = p.lower().rfind(u"</body>")
    return (p[:fim] + aviso + p[fim:]) if fim >= 0 else p + aviso


def montar_porta():
    p = radai_menu.aplicar_porta(pagina())
    try:
        import radai_shutdown
        p = radai_shutdown.aplicar(p)
    except Exception:
        pass
    return p


def _topo_de_reserva():
    import html
    try:
        nome = radai_breadcrumb.rotulo(radai_breadcrumb.RAIZ)
    except Exception:
        nome = u"Radioterapia.AI Local"
    return (u'<header class="ls-topo" data-radai-tela="%s">'
            u'<details class="ls-engrenagem" data-radai-engrenagem>'
            u'<summary data-radai-frase>Configurações</summary>'
            u'<a href="/config" data-radai-frase>Configurações</a>'
            u'</details> '
            u'<details class="ls-power" data-radai-power>'
            u'<summary data-radai-frase>Fechar app</summary>'
            u'<span class="ls-encerrar" data-radai-encerrar></span>'
            u'</details></header>' % html.escape(nome, quote=True))


def _porta_de_reserva():
    import html
    links = []
    for chave in radai_menu.MODULOS_HOME:
        nome, rota = (radai_breadcrumb.ARVORE.get(chave) or (u"", u""))[:2]
        if nome and rota:
            links.append(u'<a href="%s">%s</a>' % (html.escape(rota, quote=True),
                                                  html.escape(nome)))
    return (u'<div style="padding:40px;text-align:center">'
            u'<h1>radioterapia.ai</h1><p>%s</p>'
            u'<p data-radai-frase>%s</p></div>'
            % (u" &middot; ".join(links), FRONTEIRA_DA_RESERVA))


# GUARDA: igual a `radai_porta.FRONTEIRA`, sem importá-lo — a reserva é a
# porta de quando ele não importa (regra 1: a fronteira não some).
FRONTEIRA_DA_RESERVA = (u"Ferramenta de apoio, <strong>não validada para uso "
                        u"clínico</strong> — toda estrutura sai como <strong>"
                        u"sugestão não aprovada</strong>")


CSS_AVISO_VERSAO = u"""
.rv-aviso{position:fixed;z-index:60;bottom:12px;
 left:calc(var(--ui-lado,56px) + 12px);width:min(344px,calc(100vw - 32px));box-sizing:border-box;
 padding:14px 16px 13px;border-radius:var(--r-xl,10px);
 background:var(--panel,#0c1322);border:1px solid var(--line-strong,#2a3a55);
 box-shadow:var(--sombra,0 10px 28px rgba(0,0,0,.55));color:var(--text,#e6edf7);
 opacity:0;transform:translateY(-6px);
 transition:opacity .2s ease,transform .24s cubic-bezier(.22,1,.36,1)}
.rv-aviso.vis{opacity:1;transform:none}
.rv-aviso::before{content:"";position:absolute;left:-6px;bottom:16px;
 width:10px;height:10px;transform:rotate(45deg);
 background:var(--panel,#0c1322);border-left:1px solid var(--line-strong,#2a3a55);
 border-bottom:1px solid var(--line-strong,#2a3a55)}
.rv-aviso .rv-cab{display:flex;align-items:center;gap:9px;
 font:600 13.5px/1.35 var(--font-display,inherit)}
.rv-aviso .rv-cab .rv-marca{width:8px;height:8px;border-radius:50%;flex:0 0 auto;
 background:var(--perigo,#E96A5C)}
.rv-aviso .rv-v{margin:8px 0 0;font-size:13px;color:var(--text-muted,#a3b1c6)}
.rv-aviso .rv-v code{font-family:var(--font-mono,monospace);font-size:12.5px;
 color:var(--text,#e6edf7)}
.rv-aviso .rv-v .rv-seta{margin:0 6px;color:var(--text-dim,#72829b)}
.rv-aviso .rv-txt{margin:8px 0 0;font-size:12.5px;line-height:1.55;
 color:var(--text-muted,#a3b1c6)}
.rv-aviso .rv-bts{display:flex;gap:8px;justify-content:flex-end;flex-wrap:wrap;
 margin-top:12px}
.rv-aviso .rv-pri,.rv-aviso .rv-sec{display:inline-flex;align-items:center;
 height:32px;padding:0 13px;border-radius:var(--r-md,6px);
 font:600 12.5px/1 var(--font-display,inherit);text-decoration:none;cursor:pointer}
.rv-aviso .rv-pri{background:var(--ok,#12873F);color:var(--ok-txt,#fff);border:0}
.rv-aviso .rv-sec{background:transparent;color:var(--text,#e6edf7);
 border:1px solid var(--line-strong,#2a3a55)}
.rv-aviso .rv-sec:hover{border-color:var(--accent,#4DA3FF);color:var(--accent,#4DA3FF)}
.rv-aviso .rv-man{margin:10px 0 0;font-size:12px;text-align:right}
.rv-aviso .rv-man a{color:var(--text-muted,#a3b1c6);text-decoration:underline;
 text-underline-offset:2px}
.rv-aviso .rv-man a:hover{color:var(--accent,#4DA3FF)}
.rv-aviso a:focus-visible,.rv-aviso button:focus-visible{
 outline:2px solid var(--accent,#4DA3FF);outline-offset:2px}
body[data-tela="inicio"] .rv-aviso{top:76px;right:16px;bottom:auto;left:auto}
body[data-tela="inicio"] .rv-aviso::before{left:auto;right:30px;top:-6px;bottom:auto;
 border-left:1px solid var(--line-strong,#2a3a55);border-top:1px solid var(--line-strong,#2a3a55);
 border-bottom:0}
@media (prefers-reduced-motion:reduce){.rv-aviso{transition:none}}
"""

JS_AVISO_VERSAO = u"""<script id="radai-versao-js">
(function(){
 var ESPERAS=[0,3000,7000,15000], n=0;
 function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;')
  .replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}
 function engrenagem(){
  return document.querySelector('[data-radai-engrenagem] summary')
   || document.querySelector('.radai-menu a[href="/config"]');
 }
 function vista(){ try{ return localStorage.getItem('radai_versao_vista')||'' }
                   catch(e){ return '' } }
 function fechar(cx, versao){
  try{ localStorage.setItem('radai_versao_vista', versao) }catch(e){}
  cx.classList.remove('vis');
  setTimeout(function(){ if(cx.parentNode) cx.parentNode.removeChild(cx) }, 260);
 }
 function avisar(d){
  if(document.getElementById('rv-aviso')) return;
  var cx=document.createElement('div');
  cx.className='rv-aviso'; cx.id='rv-aviso';
  cx.setAttribute('role','status'); cx.setAttribute('aria-live','polite');
  var agora=(typeof window.radaiAtualizarAgora==='function');
  cx.innerHTML='<div class="rv-cab"><span class="rv-marca" aria-hidden="true"></span>'
   +'<span data-radai-frase>Versão nova disponível</span></div>'
   +'<p class="rv-v"><code>'+esc(d.aqui||'?')+'</code><span class="rv-seta"'
   +' aria-hidden="true">&#8594;</span><code>'+esc(d.publicada)+'</code></p>'
   +(agora?'<p class="rv-txt" data-radai-frase>'
     +'O app fecha, o atualizador roda numa janela do Windows e o app reabre sozinho, com a sua configuração.'
     +'</p>':'')
   +'<div class="rv-bts">'
   +'<button type="button" class="rv-sec" data-rv="fechar" data-radai-frase>Fechar</button>'
   +(agora?'<button type="button" class="rv-pri" data-rv="agora" data-radai-frase>Atualizar agora</button>'
     :(d.link?'<a class="rv-pri" target="_blank" rel="noopener" href="'+esc(d.link)
       +'" data-radai-frase>Baixar o instalador mais recente</a>':''))
   +'</div>'
   +(agora&&d.link?'<p class="rv-man"><a target="_blank" rel="noopener" href="'+esc(d.link)
     +'" data-radai-frase>Baixar o instalador mais recente</a></p>':'');
  document.body.appendChild(cx);
  cx.querySelector('[data-rv="fechar"]').addEventListener('click',function(){
   fechar(cx, d.publicada) });
  var ag=cx.querySelector('[data-rv="agora"]');
  if(ag) ag.addEventListener('click',function(){
   fechar(cx, d.publicada); window.radaiAtualizarAgora() });
  document.addEventListener('keydown',function(e){
   if(e.key==='Escape'&&cx.parentNode) fechar(cx, d.publicada) });
  try{ if(window.radaiRetraduzir) window.radaiRetraduzir() }catch(e){}
  requestAnimationFrame(function(){ requestAnimationFrame(function(){
   cx.classList.add('vis') }) });
 }
 function acender(d){
  var g=engrenagem(); if(!g) return;
  if(window.uiPonto) window.uiPonto(g, true);
  if(vista()!==String(d.publicada)) avisar(d);
 }
 function perguntar(){
  fetch('/api/versao',{cache:'no-store'})
   .then(function(r){ return r.ok ? r.json() : null })
   .then(function(d){
    if(!d) return;
    if(d.nova && d.publicada){ acender(d); return }
    if(d.estado==='nunca' && ++n<ESPERAS.length)
     setTimeout(perguntar, ESPERAS[n]);
   }).catch(function(){});
 }
 if(document.readyState==='loading')
  document.addEventListener('DOMContentLoaded',perguntar);
 else perguntar();
})();
</script>"""


PAGINA = u"""<!doctype html><html><head><meta charset="utf-8">
<title>Radioterapia.AI Local</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>@CSS@</style></head><body>

@TOPO@

@CORPO@

@AVISO_VERSAO@
</body></html>"""


MINI_PAGINAS = (("bridge", "/bridge"), ("recon3d", "/recon3d"),
                ("nidus", "/nidus"), ("elastic", "/elastic"),
                ("bolus", "/bolus"))


def mini_pagina(chave):
    import radai_modules
    return radai_menu.aplicar(radai_modules.pagina_completa(chave), chave)


def montar(app):
    from fastapi.responses import HTMLResponse

    @app.get("/", response_class=HTMLResponse)
    @app.get("/suite", response_class=HTMLResponse)
    def _suite():
        return montar_porta()

    for _chave, _rota in MINI_PAGINAS:
        def _mod(chave=_chave):
            return mini_pagina(chave)
        app.get(_rota, response_class=HTMLResponse)(_mod)

    @app.get("/torax", response_class=HTMLResponse)
    def _torax_saiu():
        from fastapi.responses import HTMLResponse as _H
        return _H(status_code=410, content=(
            u'<!doctype html><meta charset="utf-8">'
            u'<title>Oncologia tor&aacute;cica</title>'
            u'<div style="font:400 14px/1.7 system-ui;max-width:60ch;'
            u'margin:12vh auto;padding:0 20px;color:#a3b1c6;'
            u'background:#060d1a">'
            u'<h1 style="color:#e6edf7;font-size:22px">O m&oacute;dulo de '
            u'oncologia tor&aacute;cica saiu para projeto pr&oacute;prio.</h1>'
            u'<p>Ele n&atilde;o faz parte deste pacote. '
            u'<a href="/" style="color:#4DA3FF">Voltar para a su&iacute;te</a>.'
            u'</p></div>'))

    try:
        import radai_porta
        radai_porta.montar(app)
    except Exception:
        pass

    @app.get("/api/versao")
    def _versao():
        try:
            import radai_version
            return radai_version.para_a_tela()
        except Exception:
            return {"estado": "nunca", "nova": False, "publicada": u"",
                    "aqui": u"", "link": u""}

    try:
        import radai_languages
        radai_languages.montar_idioma_da_estacao(app)
    except Exception:
        pass

    return app
