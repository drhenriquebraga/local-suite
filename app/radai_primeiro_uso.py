# -*- coding: utf-8 -*-
import radai_config

ROTA = "/primeiro-uso"
ROTA_API = "/api/primeiro-uso"
PORTAS = ("/", "/suite")


def estado(caminho):
    _t, valores = radai_config.ler_arquivo(caminho)
    tps = radai_config.tps_canonico(valores.get("TPS_DESTINO", u""))
    root = (valores.get("ROOT") or u"").split("#")[0].strip().strip('"')
    return {"feito": bool(tps), "tps": tps, "root": root,
            "rotulo": radai_config.rotulo_do_tps(tps),
            "tps_validos": list(radai_config.TPS_VALIDOS)}


def linha_do_registro(r):
    return u"primeiro uso: TPS_DESTINO=%s (%s)%s" % (
        r["tps"], radai_config.rotulo_do_tps(r["tps"]),
        (u", ROOT=%s (existe, le e escreve)" % r["root"])
        if r["root"] else u", ROOT sem mudanca")


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


def gravar(caminho, tps, root=u"", modelo=u"", validar=None):
    validar = validar or radai_config.validar_pasta
    t = radai_config.tps_canonico(tps)
    if not t:
        return False, {"ok": False, "erro": u"escolha eclipse ou monaco"}
    mudancas = {"TPS_DESTINO": t}
    root = str(root or u"").strip().strip('"')
    laudo = None
    if root:
        laudo = validar(root)
        if not (laudo.get("existe") and laudo.get("leitura")
                and laudo.get("escrita")):
            return False, {"ok": False, "laudo": laudo,
                           "erro": laudo.get("erro") or u"pasta recusada"}
        mudancas["ROOT"] = root
    ok, erro = radai_config.escrever(caminho, mudancas, modelo=modelo)
    if not ok:
        return False, {"ok": False, "erro": erro}
    return True, {"ok": True, "tps": t, "root": root, "laudo": laudo}


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
.pu-cx h2{margin:0;font:600 15px/1.3 var(--font-display,inherit)}
.pu-cx p{margin:6px 0 0;font-size:12.5px;line-height:1.6;color:var(--text-muted,#a3b1c6)}
.pu-ops{display:flex;flex-wrap:wrap;gap:10px;margin:12px 0 0}
.pu-op{flex:1 1 180px;text-align:start;padding:11px 13px;border-radius:var(--r-md,6px);
 border:1px solid var(--line-strong,#2a3a55);background:var(--panel-2,#0f1729);
 color:var(--text,#e6edf7);font:inherit;cursor:pointer}
.pu-op b{display:block;font-size:14px}
.pu-op span{display:block;font-size:11.5px;color:var(--text-dim,#72829b);margin-top:2px}
.pu-op[aria-pressed="true"]{border-color:var(--accent,#4DA3FF);
 box-shadow:inset 0 0 0 1px var(--accent,#4DA3FF)}
.pu-op:focus-visible,.pu-bt:focus-visible,.pu-pasta:focus-visible{
 outline:2px solid var(--accent,#4DA3FF);outline-offset:2px}
.pu-linha{display:flex;gap:8px;margin:12px 0 0;flex-wrap:wrap;align-items:stretch}
.ac .pu-linha input{flex:1 1 260px;min-width:0;margin:0;padding:9px 12px;border-radius:var(--r-md,6px);
 border:1px solid var(--line-strong,#2a3a55);background:var(--panel-2,#0f1729);
 color:var(--text,#e6edf7);font:13px var(--font-mono,monospace)}
.pu-bt{padding:9px 14px;border-radius:var(--r-md,6px);border:1px solid var(--line-strong,#2a3a55);
 background:var(--panel-2,#0f1729);color:var(--text,#e6edf7);font:inherit;font-size:13px;
 cursor:pointer}
.pu-laudo{margin:10px 0 0;font-size:12.5px;min-height:18px}
.pu-laudo.ok{color:var(--success,#5BC57F)}
.pu-laudo.ruim,.ac .msg.ruim{color:var(--perigo,#E96A5C)}
.pu-det{display:block;margin-top:3px;font:11.5px var(--font-mono,monospace);
 color:var(--text-dim,#72829b);overflow-wrap:anywhere}
.pu-lista{display:none;margin:10px 0 0;max-height:260px;overflow:auto;
 border:1px solid var(--line,#1e293b);border-radius:var(--r-md,6px)}
.pu-lista.on{display:block}
.pu-pasta{display:block;width:100%;text-align:start;padding:7px 11px;border:0;
 border-bottom:1px solid var(--line,#1e293b);background:transparent;
 color:var(--text,#e6edf7);font:12.5px var(--font-mono,monospace);cursor:pointer}
.pu-pasta:hover{background:var(--panel-2,#0f1729)}
"""

PAGINA = u"""<!doctype html><html><head><meta charset="utf-8">
<title>Primeiro uso &middot; Radioterapia.AI</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>@CSS@</style></head><body><div class="ac">
<div class="ac-lang"><span data-radai-idiomas></span></div>
<div class="rot" data-radai-frase>Primeiro uso</div>
<h1 data-radai-frase>Configure esta estação</h1>
<p class="pp" data-radai-frase>Duas escolhas, uma vez só. Elas ficam gravadas no arquivo de configuração desta estação, e nas próximas aberturas o programa já sabe.</p>

<ol class="pu-passos">
 <li class="feito"><span class="n">1</span><span data-radai-frase>Idioma da interface</span></li>
 <li class="feito"><span class="n">2</span><span data-radai-frase>Termos de uso</span></li>
 <li class="agora" id="pu_passo3"><span class="n">3</span><span data-radai-frase>TPS de destino</span></li>
 <li class="agora"><span class="n">4</span><span data-radai-frase>Pasta das séries</span></li>
</ol>

<section class="pu-cx" aria-labelledby="pu_t3">
 <h2><span id="pu_t3" data-radai-frase>TPS de destino</span><span class="ui-ajuda" tabindex="0" aria-label="ajuda">?<span class="ui-balao"><p><b>Eclipse / Monaco</b>: o furo de um contorno em anel sai como um segundo contorno, dentro do primeiro.</p><p><b>Xio / Focal</b>: o furo é ligado à borda por uma linha divisória estreita, para o sistema que não lê o furo como contorno separado.</p><p>Nos dois, o RTSTRUCT e o que o DicomBridge exporta saem em Implicit VR Little Endian, a sintaxe de transferência padrão do DICOM.</p></span></span></h2>
 <p data-radai-frase>Para qual sistema de planejamento esta estação entrega os RTSTRUCT?</p>
 <div class="pu-ops" role="group" aria-labelledby="pu_t3">
  <button class="pu-op" type="button" data-tps="eclipse" aria-pressed="false"><b translate="no">Eclipse / Monaco</b><span data-radai-frase>Anel sem linha divisória</span></button>
  <button class="pu-op" type="button" data-tps="monaco" aria-pressed="false"><b translate="no">Xio / Focal</b><span data-radai-frase>Versões anteriores, ou outros que precisem de linha divisória nos anéis</span></button>
 </div>
</section>

<section class="pu-cx" aria-labelledby="pu_t4">
 <h2 id="pu_t4" data-radai-frase>Pasta das séries</h2>
 <p data-radai-frase>A pasta que o vigia varre à noite, com as pastas dos pacientes. Pode deixar em branco e escolher depois, no Overnight Run.</p>
 <div class="pu-linha">
  <input id="pu_root" type="text" spellcheck="false" autocomplete="off" aria-labelledby="pu_t4">
  <button class="pu-bt" type="button" id="pu_procurar" data-radai-frase>Procurar…</button>
  <button class="pu-bt" type="button" id="pu_conferir" data-radai-frase>Conferir a pasta</button>
 </div>
 <div class="pu-lista" id="pu_lista"></div>
 <div class="pu-laudo" id="pu_laudo" aria-live="polite"></div>
</section>

<div><button class="bt" id="pu_salvar" type="button" disabled data-radai-frase>Salvar e continuar</button></div>
<p class="msg" id="pu_msg" aria-live="polite"></p>
<p class="mini" data-radai-frase>Dá para refazer depois em Configurações, na seção Geral.</p>
</div><script>
(function(){
 var TPS = '';
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
 var bts = document.querySelectorAll('.pu-op');
 var salvar = document.getElementById('pu_salvar');
 var root = document.getElementById('pu_root');
 var laudoEl = document.getElementById('pu_laudo');
 var lista = document.getElementById('pu_lista');
 function traduzir(){ try{ if(window.radaiRetraduzir) window.radaiRetraduzir() }catch(e){} }
 var ERRO_DA_PASTA = {
  nao_existe: 'A pasta não existe ou não está acessível desta máquina.',
  sem_leitura: 'Sem permissão para ler esta pasta.',
  sem_escrita: 'Dá para ler, mas não para escrever nesta pasta. O vigia grava o RTSTRUCT e os marcadores _RadAI na própria pasta da série: sem escrita, nenhuma série é processada. Fale com o TI.',
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
 function escolher(v){
  TPS = v;
  for(var i = 0; i < bts.length; i++)
   bts[i].setAttribute('aria-pressed', bts[i].getAttribute('data-tps') === v ? 'true' : 'false');
  salvar.disabled = !TPS;
  var p3 = document.getElementById('pu_passo3');
  if(p3) p3.className = TPS ? 'feito' : 'agora';
 }
 for(var i = 0; i < bts.length; i++)
  bts[i].addEventListener('click', function(){ escolher(this.getAttribute('data-tps')) });
 function post(url, corpo){
  return fetch(url, {method:'POST', headers:{'Content-Type':'application/json'},
                     body: JSON.stringify(corpo || {})})
   .then(function(r){ return r.json() });
 }
 function mostrarLaudo(l){
  if(!l || l.vazio){ frase(laudoEl, ''); return }
  if(l.existe && l.leitura && l.escrita)
   frase(laudoEl, 'A pasta existe, e dá para ler e escrever nela.', 'ok');
  else frase(laudoEl, ERRO_DA_PASTA[l.codigo] || 'Pasta recusada.', 'ruim',
             l.detalhe || '');
 }
 document.getElementById('pu_conferir').addEventListener('click', function(){
  if(!root.value.trim()){ frase(laudoEl, ''); return }
  post('/api/config/testar', {caminho: root.value}).then(mostrarLaudo)
   .catch(function(){ frase(laudoEl, 'Não consegui conferir a pasta.', 'ruim') });
 });
 function abrir(caminho){
  post('/api/pastas', {caminho: caminho || ''}).then(function(r){
   lista.className = 'pu-lista on';
   lista.innerHTML = '';
   function item(rotulo, nome, alvo, usar){
    var b = document.createElement('button');
    b.type = 'button'; b.className = 'pu-pasta';
    if(rotulo){
     var s = document.createElement('span');
     s.setAttribute('data-radai-frase', '');
     s.textContent = rotulo;
     b.appendChild(s);
     if(nome) b.appendChild(document.createTextNode(' '));
    }
    if(nome){
     var c = document.createElement('code');
     c.setAttribute('data-radai-t', '1');
     c.textContent = nome;
     b.appendChild(c);
    }
    b.addEventListener('click', function(){
     if(usar){ root.value = alvo; lista.className = 'pu-lista'; mostrarLaudo(null) }
     else abrir(alvo);
    });
    lista.appendChild(b);
   }
   if(r.caminho){
    item('Usar esta pasta:', r.caminho, r.caminho, true);
    if(r.pai) item('Pasta de cima', '', r.pai, false);
    (r.pastas || []).forEach(function(p){ item('', p.nome, p.caminho, false) });
   } else {
    (r.unidades || []).forEach(function(u){ item('', u, u, false) });
   }
   if(r.erro){
    var e = document.createElement('div');
    e.className = 'pu-laudo ruim';
    e.textContent = r.erro;
    lista.appendChild(e);
   }
   traduzir();
  });
 }
 document.getElementById('pu_procurar').addEventListener('click', function(){
  abrir(root.value.trim());
 });
 salvar.addEventListener('click', function(){
  var msg = document.getElementById('pu_msg');
  salvar.disabled = true;
  post('/api/primeiro-uso', {tps: TPS, root: root.value}).then(function(d){
   if(d && d.ok){ location.href = DE; return }
   if(d && d.laudo){
    mostrarLaudo(d.laudo);
    frase(msg, 'Nada foi gravado: confira a pasta acima.', 'ruim');
   } else frase(msg, (d && d.erro) || 'Não consegui gravar.', 'ruim');
   salvar.disabled = !TPS;
  }).catch(function(){
   frase(msg, 'Não consegui gravar.', 'ruim');
   salvar.disabled = !TPS;
  });
 });
 fetch('/api/primeiro-uso').then(function(r){ return r.json() }).then(function(d){
  if(d && d.tps) escolher(d.tps);
  if(d && d.root && !root.value) root.value = d.root;
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
        p = _ui.aplicar(p)
    except Exception:
        pass
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

    # GUARDA: a porta desvia enquanto o TPS nao foi escolhido; o aceite tambem
    # leva ate aqui, mas a estacao com o aceite em dia so chega por este desvio.
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
        ok, r = gravar(caminho, c.get("tps"), c.get("root"), modelo=modelo)
        if not ok:
            return JSONResponse(r, status_code=400)
        if registrar:
            try:
                registrar(linha_do_registro(r))
            except Exception:
                pass
        if recarregar:
            try:
                recarregar()
            except Exception:
                pass
        return r

    return app
