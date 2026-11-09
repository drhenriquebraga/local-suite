# -*- coding: utf-8 -*-
import radai_config

ROTA = "/primeiro-uso"
ROTA_API = "/api/primeiro-uso"
PORTAS = ("/", "/suite")


def _favorita(valores):
    return (valores.get("PASTA_FAVORITA") or u"").split("#")[0].strip().strip('"')


def estado(caminho):
    _t, valores = radai_config.ler_arquivo(caminho)
    tps = radai_config.tps_canonico(valores.get("TPS_DESTINO", u""))
    return {"feito": bool(tps), "tps": tps, "pasta": _favorita(valores),
            "rotulo": radai_config.rotulo_do_tps(tps),
            "tps_validos": list(radai_config.TPS_VALIDOS)}


def linha_do_registro(r):
    mudou = r.get("mudou") or ()
    partes = []
    if "TPS_DESTINO" in mudou:
        partes.append(u"TPS_DESTINO=%s (%s, o padrao; o anel se ajusta em "
                      u"Configuracoes > Geral)"
                      % (r["tps"], radai_config.rotulo_do_tps(r["tps"])))
    if "PASTA_FAVORITA" in mudou:
        partes.append(u"pasta favorita gravada" if r.get("pasta")
                      else u"pasta favorita apagada")
    if not partes:
        partes.append(u"pulado, sem mudanca" if r.get("pulou")
                      else u"sem mudanca")
    return u"primeiro uso: " + u", ".join(partes)


ANCORA_DO_CANTO = u'<div class="ac-lang"><span data-radai-idiomas></span></div>'

CANTO = (u'<div class="ac-lang"><span data-radai-idiomas></span>'
         u'<select data-ui-seg data-ui-tema aria-label="Aparência">'
         u'<option value="claro" data-ui-icone="sol" title="Modo claro">Claro</option>'
         u'<option value="escuro" data-ui-icone="lua" title="Modo escuro">Escuro</option>'
         u'<option value="sistema" data-ui-icone="monitor" '
         u'title="Seguir o tema do sistema">Sistema</option>'
         u'</select></div>')


def com_canto(pagina):
    return pagina.replace(ANCORA_DO_CANTO, CANTO, 1)


def gravar(caminho, pasta=u"", modelo=u"", validar=None, pular=False):
    validar = validar or radai_config.validar_favorita
    _t, valores = radai_config.ler_arquivo(caminho)
    mudancas = {}
    tps = radai_config.tps_canonico(valores.get("TPS_DESTINO", u""))
    if not tps:
        tps = radai_config.TPS_PADRAO
        mudancas["TPS_DESTINO"] = tps
    pasta = u"%s" % (pasta or u"")
    pasta = pasta.strip().strip('"')
    atual = _favorita(valores)
    laudo = None
    if not pular:
        if pasta:
            laudo = validar(pasta)
            if not (laudo.get("existe") and laudo.get("leitura")):
                return False, {"ok": False, "laudo": laudo,
                               "erro": u"pasta recusada"}
            if pasta != atual:
                mudancas["PASTA_FAVORITA"] = pasta
        elif atual:
            mudancas["PASTA_FAVORITA"] = u""
    if mudancas:
        ok, erro = radai_config.escrever(caminho, mudancas, modelo=modelo)
        if not ok:
            return False, {"ok": False, "erro": erro}
    final = pasta if "PASTA_FAVORITA" in mudancas else atual
    return True, {"ok": True, "tps": tps, "pasta": final, "pulou": bool(pular),
                  "mudou": sorted(mudancas), "laudo": laudo}


CSS = u"""
.pu-passos{display:flex;flex-wrap:wrap;gap:8px 18px;margin:22px 0 0;padding:0;
 list-style:none;font-size:12px;color:var(--text-dim,#72829b)}
.pu-passos li{display:flex;align-items:center;gap:7px}
.pu-passos .n{display:inline-flex;align-items:center;justify-content:center;
 width:20px;height:20px;border-radius:50%;border:1px solid var(--line-strong,#2a3a55);
 font:600 11px/1 var(--font-mono,monospace)}
.pu-passos .feito .n{background:var(--success,#5BC57F);border-color:var(--success,#5BC57F);
 color:var(--bg-0,#060d1a)}
.pu-passos .agora{color:var(--text,#e6edf7)}
.pu-passos .agora .n{border-color:var(--accent,#4DA3FF);color:var(--accent,#4DA3FF)}
.pu-cx{margin:22px 0 0;padding:16px 18px;border-radius:var(--r-lg,8px);
 background:var(--panel,#0c1322);border:1px solid var(--line,#1e293b)}
.pu-cx h2{display:flex;align-items:center;justify-content:space-between;gap:12px;
 margin:0;font:600 15px/1.3 var(--font-display,inherit)}
.pu-cx p{margin:6px 0 0;font-size:12.5px;line-height:1.6;color:var(--text-muted,#a3b1c6)}
.pu-tag{flex:0 0 auto;padding:2px 9px;border-radius:var(--r-pill,999px);
 border:1px solid var(--line-strong,#2a3a55);font:500 11px/1.5 var(--font-display,inherit);
 color:var(--text-muted,#a3b1c6)}
.pu-linha{display:flex;gap:8px;margin:14px 0 0;flex-wrap:wrap;align-items:stretch}
.ac .pu-linha input{flex:1 1 260px;min-width:0;margin:0;padding:9px 12px;border-radius:var(--r-md,6px);
 border:1px solid var(--line-strong,#2a3a55);background:var(--panel-2,#0f1729);
 color:var(--text,#e6edf7);font:13px var(--font-mono,monospace)}
.ac .pu-linha input::placeholder{color:var(--text-dim,#72829b);font-family:var(--font-display,inherit)}
.pu-bt{padding:9px 14px;border-radius:var(--r-md,6px);border:1px solid var(--line-strong,#2a3a55);
 background:var(--panel-2,#0f1729);color:var(--text,#e6edf7);font:inherit;font-size:13px;
 cursor:pointer}
.pu-bt:hover{border-color:var(--accent-line,#2a3d57)}
.pu-bt:focus-visible,.ac .pu-linha input:focus-visible{outline:2px solid var(--accent,#4DA3FF);outline-offset:2px}
.ac .pu-linha .ui-fav{flex:0 0 auto;margin:0}
.pu-laudo{margin:10px 0 0;font-size:12.5px;min-height:18px}
.pu-laudo.ok{color:var(--success,#5BC57F)}
.pu-laudo.ruim,.ac .msg.ruim{color:var(--perigo,#E96A5C)}
.pu-det{display:block;margin-top:3px;font:11.5px var(--font-mono,monospace);
 color:var(--text-dim,#72829b);overflow-wrap:anywhere}
.pu-anel{margin:14px 0 0;font-size:12px;line-height:1.55;color:var(--text-muted,#a3b1c6)}
.pu-acoes{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:10px;
 margin:20px 0 0;padding-top:16px;border-top:1px solid var(--line,#1e293b)}
.pu-acoes .bt{margin:0}
"""

PAGINA = u"""<!doctype html><html><head><meta charset="utf-8">
<title>Primeiro uso &middot; Radioterapia.AI</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>@CSS@</style></head><body><div class="ac">
<div class="ac-lang"><span data-radai-idiomas></span></div>
<h1 data-radai-frase>Seu ponto de partida</h1>
<p class="pp" data-radai-frase>A pasta favorita é onde os seletores de pasta abrem. Ela não muda a pasta que o vigia varre.</p>

<ol class="pu-passos">
 <li class="feito"><span class="n">1</span><span data-radai-frase>Termos de uso</span></li>
 <li class="agora"><span class="n">2</span><span data-radai-frase>Pasta favorita</span></li>
</ol>

<section class="pu-cx" aria-labelledby="pu_t">
 <h2><span id="pu_t" data-radai-frase>Pasta favorita</span><span class="pu-tag" data-radai-frase>Opcional</span></h2>
 <p data-radai-frase>Você pode escolher agora ou continuar e configurar depois.</p>
 <div class="pu-linha">
  <input id="pu_pasta" type="text" spellcheck="false" autocomplete="off" aria-labelledby="pu_t" placeholder="Nenhuma pasta selecionada">
  @FAV@
  <button class="pu-bt" type="button" id="pu_procurar" data-radai-frase>Procurar…</button>
 </div>
 <div class="pu-laudo" id="pu_laudo" aria-live="polite"></div>
</section>

<p class="pu-anel" data-radai-frase>Os contornos em anel saem no padrão Eclipse / Monaco. Usa Xio / Focal? Ajuste em Configurações, na seção Geral.</p>

<div class="pu-acoes">
 <button class="pu-bt" id="pu_pular" type="button" data-radai-frase>Pular por agora</button>
 <button class="bt" id="pu_salvar" type="button" data-radai-frase>Salvar e continuar</button>
</div>
<p class="msg" id="pu_msg" aria-live="polite"></p>
<p class="mini" data-radai-frase>Você pode mudar a pasta favorita em Configurações, na seção Geral.</p>
</div><script>
(function(){
 var DE = (function(){
  var p = new URLSearchParams(location.search).get('de') || '', n = '';
  for (var k = 0; k < p.length; k++) {
   var cc = p.charCodeAt(k);
   if (cc === 9 || cc === 10 || cc === 13) { continue; }
   n += (cc === 92) ? '/' : p.charAt(k);
  }
  if (n.indexOf('/primeiro-uso') === 0) { return '/'; }
  return (n.charAt(0) === '/' && n.charAt(1) !== '/') ? n : '/';
 })();
 var salvar = document.getElementById('pu_salvar');
 var pular = document.getElementById('pu_pular');
 var pasta = document.getElementById('pu_pasta');
 var procurar = document.getElementById('pu_procurar');
 var laudoEl = document.getElementById('pu_laudo');
 var msg = document.getElementById('pu_msg');
 function traduzir(){ try{ if(window.radaiRetraduzir) window.radaiRetraduzir() }catch(e){} }
 var ERRO_DA_PASTA = {
  nao_existe: 'A pasta não existe ou não está acessível desta máquina.',
  sem_leitura: 'Sem permissão para ler esta pasta.',
  erro: 'Não consegui conferir a pasta.'
 };
 function frase(el, txt, classe, detalhe){
  el.className = el.className.replace(/ ?(ok|ruim)/g, '') + (classe ? ' ' + classe : '');
  var h = '<span data-radai-frase></span>';
  if(detalhe) h += ' <code class="pu-det" data-radai-t="1" translate="no"></code>';
  if(window.uiHTML) window.uiHTML(el, h); else el.innerHTML = h;
  el.querySelector('span').textContent = txt;
  if(detalhe) el.querySelector('code').textContent = detalhe;
  traduzir();
 }
 function post(url, corpo){
  return fetch(url, {method:'POST', headers:{'Content-Type':'application/json'},
                     body: JSON.stringify(corpo || {})})
   .then(function(r){ return r.json() });
 }
 function mostrarLaudo(l){
  if(!l || l.vazio){ frase(laudoEl, ''); return }
  if(l.existe && l.leitura) frase(laudoEl, '');
  else frase(laudoEl, ERRO_DA_PASTA[l.codigo] || 'Pasta recusada.', 'ruim', l.detalhe || '');
 }
 procurar.hidden = (typeof window.uiExplorador !== 'function');
 procurar.addEventListener('click', function(){
  if(typeof window.uiExplorador !== 'function') return;
  window.uiExplorador({titulo: 'Pasta favorita', origem: procurar, inicial: pasta.value.trim(),
   aoUsar: function(c){ pasta.value = c || ''; mostrarLaudo(null); frase(msg, '') }});
 });
 pasta.addEventListener('input', function(){ mostrarLaudo(null); frase(msg, '') });
 function enviar(corpo){
  salvar.disabled = true; pular.disabled = true;
  post('/api/primeiro-uso', corpo).then(function(d){
   if(d && d.ok){ location.href = DE; return }
   salvar.disabled = false; pular.disabled = false;
   if(d && d.laudo){
    mostrarLaudo(d.laudo);
    frase(msg, 'Nada foi gravado: confira a pasta acima.', 'ruim');
   } else frase(msg, (d && d.erro) || 'Não consegui gravar.', 'ruim');
  }).catch(function(){
   salvar.disabled = false; pular.disabled = false;
   frase(msg, 'Não consegui gravar.', 'ruim');
  });
 }
 salvar.addEventListener('click', function(){ enviar({pasta: pasta.value}) });
 pular.addEventListener('click', function(){ enviar({pular: true}) });
 fetch('/api/primeiro-uso').then(function(r){ return r.json() }).then(function(d){
  if(d && d.pasta && !pasta.value) pasta.value = d.pasta;
 }).catch(function(){});
})();
</script></body></html>"""


def pagina():
    css = CSS
    try:
        import radai_consent
        css = radai_consent.CSS_ACEITE + CSS
    except Exception:
        pass
    try:
        import radai_ui
        css = radai_ui.TOKENS + css
    except Exception:
        pass
    p = com_canto(PAGINA.replace(u"@CSS@", css))
    try:
        import radai_ui as _ui
        p = _ui.aplicar(p.replace(u"@FAV@", _ui.botao_favorita(u"pu_pasta")))
    except Exception:
        p = p.replace(u"@FAV@", u"")
    try:
        import radai_languages as _idi
        p = _idi.so_traduzir(p)
    except Exception:
        pass
    return p


def montar(app, caminho, modelo=u"", registrar=None, recarregar=None):
    from fastapi import Request
    from fastapi.responses import HTMLResponse, JSONResponse

    from fastapi.responses import RedirectResponse

    # GUARDA: a porta desvia enquanto o primeiro uso nao rodou (sem TPS_DESTINO
    # no arquivo); o aceite tambem leva ate aqui.
    @app.middleware("http")
    async def _desvio_da_porta(request, call_next):
        try:
            _rota = request.url.path or "/"
            if (request.method == "GET" and _rota in PORTAS
                    and not estado(caminho)["feito"]):
                return RedirectResponse(ROTA + "?de=" + _rota, status_code=303)
        except Exception:
            pass
        return await call_next(request)

    @app.get(ROTA, response_class=HTMLResponse)
    def _tela():
        return pagina()

    @app.get(ROTA_API)
    def _estado():
        return estado(caminho)

    @app.post(ROTA_API)
    async def _gravar(request: Request):
        try:
            c = await request.json() or {}
        except Exception:
            c = {}
        if not isinstance(c, dict):
            c = {}
        ok, r = gravar(caminho, c.get("pasta"), modelo=modelo,
                       pular=c.get("pular") is True)
        if not ok:
            return JSONResponse(r, status_code=400)
        if registrar:
            try:
                registrar(linha_do_registro(r))
            except Exception:
                pass
        if recarregar and r.get("mudou"):
            try:
                recarregar()
            except Exception:
                pass
        return r

    return app
