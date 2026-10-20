# -*- coding: utf-8 -*-
import io
import json
import os
import tempfile

NOME_DA_PAGINA = "radai_carregando_%d.html"
NOME_DO_ESTADO = "radai_carregando_%d.js"
ROTA_SINAL = "/api/pulso/sinal"
INTERVALO_MS = 500
LEITURA_DO_ESTADO_MS = 1000
SAIDA_MS = 200
NOME_NA_TELA = u"Local Suite"

FRASES = {
    "abrindo": u"carregando…",
    "parou": u"O programa parou antes de abrir (código %s).",
}

PAGINA = u"""<!doctype html>
<html lang="@LANG@">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>@TITULO@</title>
<style>
:root{--bg:#0a1120;--panel:#0c1322;--text:#e6edf7;--muted:#a3b1c6;
 --accent:#4DA3FF;--bridge:#9D8BFF;--perigo:#E96A5C;
 --marca:linear-gradient(90deg,#4DA3FF 0%,#3DD9F0 48%,#9D8BFF 100%);
 --curva:cubic-bezier(.22,1,.36,1)}
*{box-sizing:border-box}
html,body{height:100%;margin:0}
body{background:var(--bg);color:var(--text);overflow:hidden;
 font:400 14px/1.5 Inter,system-ui,'Segoe UI',Arial,sans-serif;
 display:grid;place-items:center}
.cg-fundo{position:fixed;inset:0;overflow:hidden;pointer-events:none}
.cg-fundo::before,.cg-fundo::after{content:"";position:absolute;width:62vmax;
 height:62vmax;border-radius:50%;filter:blur(70px);opacity:.38}
.cg-fundo::before{left:-14vmax;top:-18vmax;
 background:radial-gradient(circle at 50% 50%,var(--accent),transparent 68%);
 animation:cgA 7.5s ease-in-out infinite alternate}
.cg-fundo::after{right:-16vmax;bottom:-20vmax;
 background:radial-gradient(circle at 50% 50%,var(--bridge),transparent 66%);
 animation:cgB 9s ease-in-out infinite alternate}
@keyframes cgA{0%{transform:translate(0,0) scale(1)}
 50%{transform:translate(22%,18%) scale(1.18)}
 100%{transform:translate(38%,6%) scale(.92)}}
@keyframes cgB{0%{transform:translate(0,0) scale(1.05)}
 50%{transform:translate(-24%,-12%) scale(.9)}
 100%{transform:translate(-36%,-26%) scale(1.15)}}
.cg-cx{position:relative;display:flex;flex-direction:column;align-items:center;
 gap:14px;padding:32px 24px;max-width:560px;text-align:center;
 animation:cgSobe .42s var(--curva) both}
@keyframes cgSobe{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.cg-marca{width:76px;height:76px;filter:drop-shadow(0 8px 26px rgba(77,163,255,.35))}
.cg-marca svg{width:76px;height:76px;display:block}
.cg-nome{margin:0;font:700 22px/1.2 Inter,system-ui,'Segoe UI',Arial,sans-serif;
 letter-spacing:.01em;background:var(--marca);-webkit-background-clip:text;
 background-clip:text;color:transparent}
.cg-st{font-weight:500;font-size:14px;min-height:1.5em;
 background:linear-gradient(90deg,var(--muted) 0%,var(--muted) 38%,var(--text) 50%,
 var(--muted) 62%,var(--muted) 100%);background-size:250% 100%;
 -webkit-background-clip:text;background-clip:text;color:transparent;
 animation:cgBrilho 2.4s linear infinite}
@keyframes cgBrilho{from{background-position:130% 0}to{background-position:-30% 0}}
html.saindo .cg-cx{opacity:0;transform:scale(.985);
 transition:opacity @SAIDA@ms ease,transform @SAIDA@ms var(--curva)}
html.parou .cg-st{animation:none;background:none;color:var(--perigo)}
html.parou .cg-fundo::before,html.parou .cg-fundo::after{animation-play-state:paused;opacity:.18}
@media (prefers-reduced-motion:reduce){
 .cg-fundo::before,.cg-fundo::after,.cg-cx,.cg-st{animation:none}
 .cg-st{background:none;color:var(--text)}
 html.saindo .cg-cx{transition:none}}
</style>
</head>
<body>
<div class="cg-fundo" aria-hidden="true"></div>
<main class="cg-cx">
 <div class="cg-marca" aria-hidden="true">@MARCA@</div>
 <h1 class="cg-nome">@NOME@</h1>
 <div class="cg-st" id="cg-st" role="status" aria-live="polite">@ABRINDO@</div>
</main>
<script>
(function(){
 var BASE = 'http://127.0.0.1:@PORTA@';
 var SINAL = BASE + '@SINAL@';
 var ESTADO = '@ESTADO@';
 var F = @FRASES@;
 var raiz = document.documentElement;
 var st = document.getElementById('cg-st');
 var feito = false;
 function entrar(){
  if(feito) return;
  feito = true;
  raiz.className += ' saindo';
  setTimeout(function(){ location.replace(BASE + '/') }, @SAIDA@);
 }
 function parar(rc){
  if(feito) return;
  feito = true;
  raiz.className += ' parou';
  st.textContent = F.parou.replace('%s', String(rc));
 }
 window.radaiLancador = function(d){
  if(d && d.estado === 'saiu') parar(d.rc === null || d.rc === undefined ? '?' : d.rc);
 };
 function sondar(){
  if(feito) return;
  var i = new Image();
  i.onload = entrar;
  i.src = SINAL + '?t=' + new Date().getTime();
 }
 function lerEstado(){
  if(feito) return;
  var s = document.createElement('script');
  s.src = ESTADO + '?t=' + new Date().getTime();
  s.onload = s.onerror = function(){ if(s.parentNode) s.parentNode.removeChild(s) };
  document.getElementsByTagName('head')[0].appendChild(s);
 }
 // GUARDA: a sondagem começa depois do load; imagem e script pedidos antes
 // dele o adiam a cada volta, e a página nunca termina de carregar.
 function comecar(){
  sondar();
  setInterval(sondar, @INTERVALO@);
  setInterval(lerEstado, @LEITURA@);
 }
 if(document.readyState === 'complete') comecar();
 else window.addEventListener('load', comecar);
})();
</script>
</body>
</html>
"""


def _html(texto):
    return (texto.replace(u"&", u"&amp;").replace(u"<", u"&lt;")
            .replace(u">", u"&gt;").replace(u'"', u"&quot;"))


def _js_seguro(texto):
    # GUARDA: a sequência que fecha o bloco de script dentro de uma string
    # encerra o script ali mesmo.
    return texto.replace(u"</", u"<\\/")


def marca(pasta_do_programa=None):
    if not pasta_do_programa:
        return u""
    try:
        svg = io.open(os.path.join(pasta_do_programa, "favicon.svg"),
                      encoding="utf-8").read()
    except Exception:
        return u""
    i = svg.find(u"<svg")
    if i < 0 or u"<script" in svg.lower():
        return u""
    return svg[i:].strip()


def tradutor_da_estacao():
    try:
        import radai_languages
        cod = radai_languages.padrao_efetivo()
    except Exception:
        return (lambda f: f), u"pt-BR"
    if not cod or cod == u"pt-BR":
        return (lambda f: f), u"pt-BR"
    try:
        import radai_phrases
        tabela = (radai_phrases.construir() or {}).get(cod) or {}
        normalizar = getattr(radai_phrases, "normalizar", lambda f: f)
    except Exception:
        return (lambda f: f), cod

    def traduzir(f):
        return tabela.get(f) or tabela.get(normalizar(f)) or f
    return traduzir, cod


def montar(porta, frases=None, lang=u"pt-BR", marca_svg=u""):
    fr = dict(FRASES)
    fr.update(frases or {})
    trocas = (
        (u"@LANG@", _html(lang or u"pt-BR")),
        (u"@TITULO@", _html(NOME_NA_TELA)),
        (u"@NOME@", _html(NOME_NA_TELA)),
        (u"@ABRINDO@", _html(fr["abrindo"])),
        (u"@MARCA@", marca_svg or u""),
        (u"@FRASES@", _js_seguro(json.dumps(fr, ensure_ascii=False))),
        (u"@ESTADO@", NOME_DO_ESTADO % int(porta)),
        (u"@SINAL@", ROTA_SINAL),
        (u"@PORTA@", str(int(porta))),
        (u"@INTERVALO@", str(INTERVALO_MS)),
        (u"@LEITURA@", str(LEITURA_DO_ESTADO_MS)),
        (u"@SAIDA@", str(SAIDA_MS)),
    )
    pagina = PAGINA
    for a, b in trocas:
        pagina = pagina.replace(a, b)
    return pagina


def caminho(porta, pasta=None):
    return os.path.join(pasta or tempfile.gettempdir(),
                        NOME_DA_PAGINA % int(porta))


def caminho_do_estado(porta, pasta=None):
    return os.path.join(pasta or tempfile.gettempdir(),
                        NOME_DO_ESTADO % int(porta))


def gravar_estado(porta, estado, rc=None, pasta=None):
    try:
        dados = json.dumps({"estado": str(estado), "rc": rc})
        with io.open(caminho_do_estado(porta, pasta), "w",
                     encoding="utf-8") as f:
            f.write(u"window.radaiLancador&&window.radaiLancador(%s);\n"
                    % dados)
        return True
    except Exception:
        return False


def gravar(porta, url=None, pasta=None, pasta_do_programa=None,
           tradutor=None):
    traduzir, lang = tradutor() if tradutor else tradutor_da_estacao()
    frases = dict((k, traduzir(v)) for (k, v) in FRASES.items())
    pagina = montar(porta, frases, lang, marca(pasta_do_programa))
    destino = caminho(porta, pasta)
    # GUARDA: o estado da abertura anterior (que pode ter falhado) sai antes
    # de a página nova abrir; senão ela mostraria a falha velha.
    gravar_estado(porta, u"subindo", None, pasta)
    with io.open(destino, "w", encoding="utf-8") as f:
        f.write(pagina)
    return destino
