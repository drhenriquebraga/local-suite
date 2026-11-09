# -*- coding: utf-8 -*-
import io
import json
import os
import tempfile

NOME_DA_PAGINA = "radai_carregando_%d.html"
NOME_DO_ESTADO = "radai_carregando_%d.js"
ROTA_SINAL = "/api/pulso/sinal"
ROTA_VERSAO = "/api/versao.js"
INTERVALO_MS = 500
LEITURA_DO_ESTADO_MS = 1000
LEITURA_DA_VERSAO_MS = 400
TETO_DA_CONSULTA_MS = 3000
NOVA_NA_TELA_MS = 900
SAIDA_MS = 200
TROCA_MS = 180
NOME_NA_TELA = u"Local Suite"

FRASES = {
    "abrindo": u"carregando…",
    "consultando": u"procurando atualizações…",
    "nova": u"versão nova encontrada",
    "parou": u"O programa parou antes de abrir (código %s).",
    "tentar": u"Tentar novamente",
    "tentando": u"tentando de novo…",
    "sem_tentar": (u"Não consegui pedir a nova tentativa. Abra o programa "
                   u"pelo atalho."),
}

PAGINA = u"""<!doctype html>
<html lang="@LANG@">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>@TITULO@</title>
<style>
:root{--bg:#0a1120;--panel:#0c1322;--text:#e6edf7;--muted:#a3b1c6;
 --accent:#4DA3FF;--bridge:#9D8BFF;--perigo:#E96A5C;--linha:#2a3a55;
 --ok:#12873F;--ok-txt:#fff;
 --marca:linear-gradient(90deg,#4DA3FF 0%,#3DD9F0 48%,#9D8BFF 100%);
 --curva:cubic-bezier(.22,1,.36,1)}
*{box-sizing:border-box}
html,body{height:100%;margin:0}
body{background:var(--bg);color:var(--text);overflow:hidden;
 font:400 14px/1.5 Inter,system-ui,'Segoe UI',Arial,sans-serif;
 display:grid;place-items:center}
::selection{background:rgba(77,163,255,.35);color:var(--text)}
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
.cg-linha{position:relative;min-height:1.5em;overflow:hidden}
.cg-st{display:inline-block;font-weight:500;font-size:14px;min-height:1.5em;
 background:linear-gradient(90deg,var(--muted) 0%,var(--muted) 38%,var(--text) 50%,
 var(--muted) 62%,var(--muted) 100%);background-size:250% 100%;
 -webkit-background-clip:text;background-clip:text;color:transparent;
 animation:cgBrilho 2.4s linear infinite;
 transition:opacity @TROCA@ms ease,transform @TROCA@ms var(--curva),filter @TROCA@ms ease}
.cg-st.sai{opacity:0;transform:translateY(-7px);filter:blur(2px)}
.cg-st.entra{opacity:0;transform:translateY(7px);filter:blur(2px);transition:none}
@keyframes cgBrilho{from{background-position:130% 0}to{background-position:-30% 0}}
.cg-tentar{display:none;align-items:center;height:34px;padding:0 16px;
 border-radius:6px;border:0;background:var(--ok);color:var(--ok-txt);
 font:600 13px/1 Inter,system-ui,'Segoe UI',Arial,sans-serif;cursor:pointer;
 transition:transform .16s var(--curva),filter .16s ease}
.cg-tentar:hover{filter:brightness(1.08)}
.cg-tentar:active{transform:translateY(1px)}
.cg-tentar:disabled{opacity:.45;cursor:default;filter:none;transform:none}
.cg-tentar:focus-visible{outline:2px solid var(--accent);outline-offset:3px}
html.parou.pode-tentar .cg-tentar{display:inline-flex}
.cg-nota{display:none;margin:0;font-size:12.5px;color:var(--muted);max-width:44ch}
html.sem-tentar .cg-nota{display:block}
html.saindo .cg-cx{opacity:0;transform:scale(.985);
 transition:opacity @SAIDA@ms ease,transform @SAIDA@ms var(--curva)}
html.parou .cg-st{animation:none;background:none;color:var(--perigo)}
html.parou .cg-fundo::before,html.parou .cg-fundo::after{animation-play-state:paused;opacity:.18}
@media (prefers-reduced-motion:reduce){
 .cg-fundo::before,.cg-fundo::after,.cg-cx,.cg-st{animation:none}
 .cg-st{background:none;color:var(--text);transition:none}
 .cg-st.sai,.cg-st.entra{opacity:1;transform:none;filter:none}
 .cg-tentar{transition:none}
 html.saindo .cg-cx{transition:none}}
</style>
</head>
<body>
<div class="cg-fundo" aria-hidden="true"></div>
<main class="cg-cx">
 <div class="cg-marca" aria-hidden="true">@MARCA@</div>
 <h1 class="cg-nome">@NOME@</h1>
 <div class="cg-linha"><div class="cg-st" id="cg-st" role="status" aria-live="polite">@ABRINDO@</div></div>
 <button type="button" class="cg-tentar" id="cg-tentar">@TENTAR@</button>
 <p class="cg-nota" id="cg-nota" role="alert">@SEM_TENTAR@</p>
</main>
<script>
(function(){
 var BASE = 'http://127.0.0.1:@PORTA@';
 var SINAL = BASE + '@SINAL@';
 var VERSAO = BASE + '@VERSAO@';
 var ESTADO = '@ESTADO@';
 var F = @FRASES@;
 var raiz = document.documentElement;
 var st = document.getElementById('cg-st');
 var bt = document.getElementById('cg-tentar');
 var feito = false, noAr = false, respondeu = false, tentarEm = '';
 var desde = 0, troca = null, ultimoRc = '?';
 var calmo = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
 function classe(c, sim){
  var l = (' ' + raiz.className + ' ').replace(' ' + c + ' ', ' ');
  raiz.className = (sim ? l + c : l).replace(/^\\s+|\\s+$/g, '');
 }
 // GUARDA: a troca de frase so mexe no texto da linha de estado; quem le a
 // tela com leitor ouve a frase nova pelo aria-live, e o movimento e so
 // a moldura da troca.
 function dizer(texto){
  if(st.textContent === texto) return;
  if(troca) clearTimeout(troca);
  if(calmo){ st.textContent = texto; return }
  st.className = 'cg-st sai';
  troca = setTimeout(function(){
   st.textContent = texto;
   st.className = 'cg-st entra';
   void st.offsetWidth;
   st.className = 'cg-st';
  }, @TROCA@);
 }
 function entrar(){
  if(feito) return;
  feito = true;
  classe('saindo', true);
  setTimeout(function(){ location.replace(BASE + '/') }, @SAIDA@);
 }
 function parar(rc, tentar){
  if(feito) return;
  feito = true;
  tentarEm = tentar || '';
  ultimoRc = String(rc);
  classe('parou', true);
  classe('pode-tentar', !!tentarEm);
  if(troca) clearTimeout(troca);
  st.className = 'cg-st';
  st.textContent = F.parou.replace('%s', String(rc));
  if(tentarEm){ bt.disabled = false; try{ bt.focus() }catch(e){} }
 }
 function recomecar(){
  feito = false; noAr = false; respondeu = false;
  classe('parou', false); classe('pode-tentar', false); classe('sem-tentar', false);
  st.className = 'cg-st';
  st.textContent = F.abrindo;
 }
 bt.addEventListener('click', function(){
  if(!tentarEm || bt.disabled) return;
  bt.disabled = true;
  classe('sem-tentar', false);
  st.textContent = F.tentando;
  var i = new Image();
  i.onload = function(){ recomecar() };
  i.onerror = function(){ bt.disabled = false; classe('sem-tentar', true);
                          st.textContent = F.parou.replace('%s', ultimoRc) };
  i.src = tentarEm + '?t=' + new Date().getTime();
 });
 window.radaiLancador = function(d){
  if(d && d.estado === 'saiu')
   parar(d.rc === null || d.rc === undefined ? '?' : d.rc, d.tentar || '');
 };
 window.radaiVersao = function(d){
  respondeu = true;
  if(feito || !d) { if(!d) entrar(); return }
  if(d.nova){ dizer(F.nova); setTimeout(entrar, @NOVA_MS@); return }
  if(d.consultando && (new Date().getTime() - desde) < @TETO_CONSULTA@){
   dizer(F.consultando);
   setTimeout(lerVersao, @LEITURA_VERSAO@);
   return;
  }
  entrar();
 };
 function lerVersao(){
  if(feito) return;
  respondeu = false;
  var s = document.createElement('script');
  s.src = VERSAO + '?t=' + new Date().getTime();
  s.onload = function(){
   if(s.parentNode) s.parentNode.removeChild(s);
   setTimeout(function(){ if(!respondeu) entrar() }, 60);
  };
  s.onerror = function(){ if(s.parentNode) s.parentNode.removeChild(s); entrar() };
  document.getElementsByTagName('head')[0].appendChild(s);
 }
 function noArAgora(){
  if(feito || noAr) return;
  noAr = true;
  desde = new Date().getTime();
  setTimeout(entrar, @TETO_CONSULTA@ + @NOVA_MS@);
  lerVersao();
 }
 function sondar(){
  if(feito || noAr) return;
  var i = new Image();
  i.onload = noArAgora;
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
        (u"@TENTAR@", _html(fr["tentar"])),
        (u"@SEM_TENTAR@", _html(fr["sem_tentar"])),
        (u"@MARCA@", marca_svg or u""),
        (u"@FRASES@", _js_seguro(json.dumps(fr, ensure_ascii=False))),
        (u"@ESTADO@", NOME_DO_ESTADO % int(porta)),
        (u"@SINAL@", ROTA_SINAL),
        (u"@VERSAO@", ROTA_VERSAO),
        (u"@LEITURA_VERSAO@", str(LEITURA_DA_VERSAO_MS)),
        (u"@TETO_CONSULTA@", str(TETO_DA_CONSULTA_MS)),
        (u"@NOVA_MS@", str(NOVA_NA_TELA_MS)),
        (u"@TROCA@", str(TROCA_MS)),
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


def gravar_estado(porta, estado, rc=None, pasta=None, tentar=None):
    try:
        d = {"estado": str(estado), "rc": rc}
        if tentar:
            d["tentar"] = str(tentar)
        dados = json.dumps(d)
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
