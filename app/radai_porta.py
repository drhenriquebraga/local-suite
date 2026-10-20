# -*- coding: utf-8 -*-
import hashlib
import html as _html
import math
import os

PASTA = u"porta"

ARQUIVOS = {
    u"porta.js": u"application/javascript",
    u"Anton-Regular.ttf": u"font/ttf",
    u"local-suite-vidros-v2.png": u"image/png",
}

ESCOPO = u'body[data-tela="inicio"]'

FRONTEIRA = (u"Ferramenta de apoio, <strong>não validada para uso "
             u"clínico</strong> — toda estrutura sai como <strong>sugestão "
             u"não aprovada</strong>")

AUTOR = u"Henrique Braga"


def caminho(nome):
    if nome not in ARQUIVOS:
        return None
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), PASTA, nome)


def arquivo(nome):
    c = caminho(nome)
    if not c:
        return None
    try:
        with open(c, "rb") as f:
            return f.read(), ARQUIVOS[nome]
    except Exception:
        return None


def montar(app):
    from fastapi.responses import Response

    def _rota(nome):
        def _servir():
            a = arquivo(nome)
            if a is None:
                return Response(status_code=404)
            dados, tipo = a
            return Response(
                content=dados, media_type=tipo,
                headers={"ETag": '"%s"' % hashlib.sha256(dados).hexdigest()[:20],
                         "Cache-Control": "no-cache"})
        return _servir

    for nome in sorted(ARQUIVOS):
        app.get(u"/%s/%s" % (PASTA, nome))(_rota(nome))
    return app


def _malha_do_elastic():
    def ponto(u, v):
        return (13 + u * 57 + v * 9,
                68 - v * 44 - math.sin(u * math.pi) * math.sin(v * math.pi) * 22
                + u * 9)
    caminhos = []
    for eixo in (0, 1):
        for g in range(10):
            d = []
            for passo in range(25):
                u, v = ((passo / 24.0, g / 9.0) if eixo else (g / 9.0, passo / 24.0))
                x, y = ponto(u, v)
                d.append(u"%s%.2f %.2f" % (u"L" if passo else u"M", x, y))
            caminhos.append(u'<path d="%s" opacity="%s"/>'
                            % (u" ".join(d), u".68" if g % 3 else u".96"))
    return u"".join(caminhos)


_SVG_ICONE = (u'<svg class="ls-icone tool-icon%s" viewBox="0 0 84 84" fill="none" '
              u'stroke="currentColor" aria-hidden="true">'
              u'<g class="ls-detalhe" stroke-width="%s"%s>%s</g></svg>')

ICONES = {
    u"bridge": (u"", u"1.1", u"",
                u'<path d="m11 23 30-18 32 19-31 18Z"/>'
                u'<path d="m11 34 31 18 31-18M11 45l31 18 31-18M11 56l31 18 31-18M11 67l31 12 31-18"/>'
                u'<path d="m17 20 32 18m-25-22 32 18m-25-22 32 18m-28-19 32 19M20 29 51 11M27 33 58 15M34 37 65 19" opacity=".35"/>'),
    u"autocontorno": (u" ls-contornos", u"1.15", u"",
                      u'<path d="M15 68C6 66 13 47 14 28S27 6 39 10s19 20 30 33S85 70 66 74s-40-1-51-6Z"/>'
                      u'<path d="M20 63C13 61 19 45 20 30s12-20 22-14 13 19 24 31 13 21-2 23-34-2-44-7Z"/>'
                      u'<path d="M25 58C19 56 25 43 25 31s9-16 18-8 11 17 20 27 8 16-4 16-26-4-34-8Z"/>'
                      u'<path d="M31 53C26 51 31 40 31 33s6-10 12-3 10 13 17 22 0 11-8 9-16-5-21-8Z"/>'
                      u'<path d="M36 48c-4-2 1-9 0-13s6-1 10 4 10 11 8 14-12-1-18-5Z"/>'),
    u"recon3d": (u"", u"1.15", u"",
                 u'<path d="m42 5 29 17v37L42 78 13 59V22Z M13 22l29 18 29-18M42 40v38M42 5v35M13 59l29-19 29 19"/>'
                 u'<path d="m13 40 29 19 29-19M27 13v55m30-54v54m-30-5 30-36m-30-4 30 36" opacity=".23"/>'),
    u"nidus": (u" ls-vasos", u"1.35", u' stroke-linecap="round"',
               u'<path d="M31 78c2-19 7-27 13-36s2-16-1-27M40 60c-5-12-14-14-23-19S8 30 7 18M43 43c12-7 21-10 25-25M41 52c15 1 20 11 29 22M44 30C33 26 31 21 29 10M37 66C25 61 21 65 10 70M56 52c4-12 11-13 22-12M21 43c2-10-1-16-4-22M55 36c-4-8 3-15 5-27"/>'
               u'<path d="m43 16 6-8m-20 5 4-8M8 29l8-6m6 33-7-4m-2 17-7-6m61-39 9 1m-5 27 7 7m-12 10 10-3m-21-50-6-7" opacity=".7"/>'),
    u"elastic": (u"", u".85", u"", _malha_do_elastic()),
    u"bolus": (u"", u"1.15", u"",
               u'<path d="M13 56q-3 10 6 13l25 9q4 2 9-1l19-12q4-3 1-9L43 37Z"/>'
               u'<path d="M13 48q-3 10 6 13l25 9q4 2 9-1l19-12q4-3 1-9L43 29Z"/>'
               u'<path d="M15 37q-5 8 3 13l25 12q4 2 9-1l19-14q4-3-1-9L45 19q-5-3-9 0Z"/>'
               u'<path d="m20 35 19-12q5-3 10 1l17 13q5 4-1 8L50 55q-5 3-10 0L20 44q-6-3 0-9Z" fill="currentColor" fill-opacity=".08"/>'),
}

_SETA = (u'<span class="ls-seta" aria-hidden="true"><svg viewBox="0 0 24 24">'
         u'<path d="M5 12h14m-6-6 6 6-6 6"/></svg></span>')

_ENGRENAGEM = (u'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
               u'stroke-width="1.5" aria-hidden="true"><path d="m9.3 3 .6-1h4.2l.6 2 '
               u'1.8 1 2-.4 2.1 3.6-1.4 1.6v2.1l1.4 1.6-2.1 3.6-2-.4-1.8 1-.6 2H9.9l'
               u'-.6-2-1.8-1-2 .4L3.4 14l1.4-1.6v-2.1L3.4 8.7l2.1-3.6 2 .4 1.8-1Z"/>'
               u'<circle cx="12" cy="10.9" r="3"/></svg>')


def icone(chave):
    i = ICONES.get(chave)
    if not i:
        return u""
    classe, traco, extra, corpo = i
    return _SVG_ICONE % (classe, traco, extra, corpo)


def _esc(t):
    return _html.escape(t or u"", quote=True)


def _estado(chave):
    try:
        import radai_modules
        m = radai_modules.MODULOS.get(chave) or {}
        e = m.get("estado") or u""
        return e if (e and radai_modules.nao_navega(e)) else u""
    except Exception:
        return u""


def cartao(chave, i):
    try:
        import radai_breadcrumb
        entrada = radai_breadcrumb.ARVORE.get(chave)
    except Exception:
        entrada = None
    if not entrada or chave not in ICONES:
        return u""
    nome, rota = entrada[0], entrada[1]
    if not rota or rota == u"/":
        return u""
    miolo = (u'%s<span class="ls-nome tool-name" data-radai-frase>%s</span>'
             % (icone(chave), _esc(nome)))
    estado = _estado(chave)
    if estado:
        return (u'<div class="ls-card tool-card ls-obra" data-tool="%d" '
                u'data-mod="%s">%s<span class="ls-selo" data-radai-frase>%s'
                u'</span></div>' % (i, _esc(chave), miolo, _esc(estado)))
    return (u'<a class="ls-card tool-card" href="%s" data-tool="%d" '
            u'data-mod="%s">%s%s</a>' % (_esc(rota), i, _esc(chave), miolo, _SETA))


def ordem():
    try:
        import radai_menu
        return tuple(radai_menu.MODULOS_HOME)
    except Exception:
        return (u"bridge", u"autocontorno", u"recon3d", u"nidus", u"elastic",
                u"bolus")


def _nome_da_raiz():
    try:
        import radai_breadcrumb
        return radai_breadcrumb.rotulo(radai_breadcrumb.RAIZ)
    except Exception:
        return u"Radioterapia.AI Local"


CSS = u"""
@font-face{font-family:Anton;src:url('/porta/Anton-Regular.ttf') format('truetype');font-display:swap;font-weight:400}
html @S{margin:0;padding-top:0!important;width:100%;min-height:100%;overflow-x:hidden;overflow-y:auto;background:#020917;color:#eef4ff;font:400 15px/1.45 system-ui,'Segoe UI',Arial,sans-serif;-webkit-font-smoothing:antialiased}
:root:has(@S){background:#020917;scrollbar-color:#2a3a55 #020917}
@S ::selection{background:rgba(157,139,255,.38);color:#fff}
@S .ls-suite{--ls-noite:#020917;--ls-tinta:#eef4ff;--ls-azul:#4da3ff;--ls-ouro:#ecd6aa;--ls-saida:cubic-bezier(.23,1,.32,1);--ls-tempo:180ms;position:relative;min-height:100dvh;width:100%;box-sizing:border-box;display:grid;grid-template-rows:16dvh 49dvh 27dvh minmax(8dvh,auto);background:radial-gradient(ellipse at 51% 40%,#03101e 0%,var(--ls-noite) 66%);isolation:isolate;color:var(--ls-tinta)}
@S .ls-suite *{box-sizing:border-box}
@S .ls-suite a{color:inherit;text-decoration:none;-webkit-tap-highlight-color:transparent}
@S .ls-suite svg{display:block}
@S .ls-suite h1,@S .ls-suite p{margin:0}
@S .ls-suite a:focus-visible,@S .ls-suite summary:focus-visible{outline:2px solid var(--ls-ouro);outline-offset:5px}
@S .ls-topo{grid-row:1;background:transparent;display:flex;align-items:center;justify-content:center;position:relative;z-index:6;padding-top:8px}
@S .ls-titulo{font:400 clamp(54px,6.5vw,116px)/1.04 Anton,'Arial Narrow',Impact,sans-serif;letter-spacing:-.012em;white-space:nowrap;text-align:center;user-select:none;color:#fafcff}
@S .ls-local{color:#fafcff}
@S .ls-grad{color:var(--ls-azul);background:linear-gradient(95deg,#21bbf4 3%,#3c88ff 42%,#a581f4 84%);background-clip:text;-webkit-background-clip:text;-webkit-text-fill-color:transparent}
@S .ls-engrenagem{position:absolute;top:clamp(17px,3.4vh,34px);right:clamp(20px,2.4vw,42px)}
@S .ls-engrenagem>summary{list-style:none;display:flex;gap:11px;align-items:center;cursor:pointer;font-size:clamp(11px,.88vw,14px);padding:5px 0;color:#e6edf6;border-radius:8px;transition:color var(--ls-tempo) ease;user-select:none}
@S .ls-engrenagem>summary::-webkit-details-marker{display:none}
@S .ls-engrenagem>summary::marker{content:''}
@S .ls-engrenagem>summary svg{height:25px;width:25px;transition:transform 200ms var(--ls-saida)}
@S .ls-engrenagem[open]>summary{color:#c0b8ff}
@S .ls-engrenagem[open]>summary svg{transform:rotate(30deg)}
@S .ls-menu{position:absolute;right:0;top:calc(100% + 10px);min-width:228px;padding:6px;display:flex;flex-direction:column;gap:4px;border-radius:12px;background:linear-gradient(145deg,rgba(20,40,61,.97),rgba(6,15,32,.98));border:1px solid rgba(191,215,243,.28);box-shadow:0 18px 60px rgba(0,0,0,.55),inset 0 1px 0 rgba(255,255,255,.09)}
@S .ls-menu>a{display:block;padding:10px 12px;border-radius:8px;font-size:14px;color:#e6edf6;white-space:nowrap;transition:background-color 140ms ease}
@S .ls-menu>a:hover{background:rgba(255,255,255,.07)}
@S .ls-encerrar{display:block}
@S .ls-encerrar .rx-fechar{width:100%;height:38px;justify-content:flex-start;background:#160a08;border-color:#e96a5c;color:#e96a5c}
@S .ls-encerrar .rx-fechar:hover{background:#e96a5c;color:#0a1120}
@S .ls-encerrar .rx-fechar .rx-fechar-txt{display:inline}
@S .ls-cena{position:absolute;inset:0;z-index:0;overflow:hidden;pointer-events:none;background:transparent}
@S .ls-rig{position:absolute;left:50%;top:0;width:100%;aspect-ratio:1672/941;transform:translateX(-50%)}
@S .ls-drift{position:relative;width:100%;height:100%;transform:translate3d(0,0,0)}
@S .ls-arte,@S .ls-luz,@S .ls-vidros,@S .beam-bloom{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}
@S .ls-arte{-webkit-mask-image:linear-gradient(to bottom,transparent 0%,#000 12%,#000 76%,transparent 100%);mask-image:linear-gradient(to bottom,transparent 0%,#000 12%,#000 76%,transparent 100%)}
@S .ls-luz{opacity:0;transition:opacity 500ms ease-out}
@S .ls-cena[data-renderer="canvas2d"] .ls-luz{opacity:1}
@S .ls-vidros{overflow:visible}
@S .ls-placa{opacity:0}
@S .ls-anel{transform-box:fill-box;transform-origin:center;opacity:0}
@S .beam-bloom{filter:blur(6px);mix-blend-mode:screen;opacity:.9}
@S .ls-cards{grid-row:3;direction:ltr;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));grid-template-rows:repeat(2,minmax(0,1fr));gap:clamp(10px,1.65vh,17px) clamp(13px,1.15vw,20px);padding:6px clamp(30px,8vw,150px) clamp(20px,3.2vh,34px);position:relative;z-index:4;min-height:0}
@S .ls-card{--mx:50%;--my:20%;position:relative;display:flex;align-items:center;gap:clamp(17px,2vw,34px);min-width:0;text-align:start;padding:clamp(14px,1.6vh,21px) clamp(17px,1.6vw,28px);color:#edf3ff;border:1px solid rgba(129,224,249,.8);border-radius:16px;background:linear-gradient(150deg,rgba(47,121,156,.20),rgba(11,31,47,.35) 43%,rgba(10,22,37,.45) 74%,rgba(58,122,143,.17));box-shadow:inset 0 1px 1px rgba(232,243,252,.22),inset 0 0 30px rgba(25,123,169,.025),0 5px 18px rgba(0,0,0,.09);transition:border-color var(--ls-tempo) ease,box-shadow var(--ls-tempo) ease;overflow:hidden;isolation:isolate}
@S .ls-card::before{content:'';position:absolute;inset:0;background:radial-gradient(ellipse at var(--mx,50%) var(--my,20%),rgba(161,164,255,.20),transparent 70%);opacity:0;z-index:-1;transition:opacity var(--ls-tempo) ease}
@S .ls-card::after{content:'';position:absolute;inset:0;border-radius:inherit;background:linear-gradient(120deg,transparent 16%,rgba(244,219,167,.035) 34%,rgba(176,218,243,.08) 36%,transparent 54%);pointer-events:none}
@S .ls-card[data-active="true"],@S .ls-card:focus-visible{border-color:rgba(237,218,173,.92);box-shadow:inset 0 1px 1px rgba(255,237,206,.35),0 0 22px rgba(92,136,233,.13),0 9px 26px rgba(0,0,0,.18)}
@S .ls-card[data-active="true"]::before,@S .ls-card:focus-visible::before{opacity:1}
@S .ls-card:focus-visible{outline:2px solid var(--ls-ouro);outline-offset:5px}
@S .ls-icone{flex:none;width:clamp(42px,4.5vw,77px);height:clamp(42px,4.5vw,77px);color:#a8e6ff;filter:drop-shadow(0 0 7px rgba(77,163,255,.16));transform:translate3d(0,0,0);transform-origin:center}
@S .ls-contornos{color:#63d3ff}
@S .ls-vasos{color:#d3efff}
@S .ls-detalhe{transform-box:fill-box;transform-origin:center}
@S .ls-nome{font-size:clamp(15px,1.42vw,25px);font-weight:500;line-height:1.2;letter-spacing:-.015em;min-width:0}
@S .ls-seta{display:grid;place-items:center;flex:none;margin-inline-start:auto;width:clamp(31px,2.7vw,45px);height:clamp(31px,2.7vw,45px);border:1px solid var(--ls-ouro);border-radius:50%;color:var(--ls-ouro);transition:color var(--ls-tempo) ease,background var(--ls-tempo) ease}
@S .ls-seta svg{width:21px;height:21px;fill:none;stroke:currentColor;stroke-width:1.4;stroke-linecap:round;stroke-linejoin:round}
:root[dir="rtl"] @S .ls-card{direction:rtl}
:root[dir="rtl"] @S .ls-seta svg{transform:scaleX(-1)}
@S .ls-card[data-active="true"] .ls-seta{background:rgba(236,214,170,.11);color:#fff0d3}
@S .ls-obra{cursor:default;opacity:.72}
@S .ls-selo{margin-inline-start:auto;font:600 11px/1 system-ui,'Segoe UI',Arial,sans-serif;letter-spacing:.05em;text-transform:uppercase;padding:4px 8px;border-radius:99px;color:var(--ls-ouro);border:1px solid var(--ls-ouro)}
@S .ls-rodape{grid-row:4;margin:0 clamp(22px,2.3vw,42px);display:flex;align-items:center;justify-content:center;gap:clamp(24px,3vw,50px);border-top:1px solid rgba(135,166,197,.28);padding:10px 24px;position:relative;z-index:5;background:var(--ls-noite);font-size:clamp(10.5px,.85vw,14px);color:#b7c2d5;line-height:1.5;text-align:center}
@S .ls-rodape strong{font-weight:500;color:#eef1fa}
@S .ls-autor{white-space:nowrap;border-inline-start:1px solid rgba(169,192,219,.42);padding-inline-start:clamp(24px,2.5vw,45px)}
@media(hover:hover) and (pointer:fine){@S .ls-engrenagem>summary:hover{color:#c0b8ff}@S .ls-engrenagem>summary:hover svg{transform:rotate(30deg)}}
@media(min-width:801px) and (max-height:700px){@S .ls-titulo{font-size:clamp(54px,7vh,80px)}@S .ls-icone{width:42px;height:42px}@S .ls-cards{padding-bottom:13px;gap:10px 14px}@S .ls-card{border-radius:12px;padding:10px 16px;gap:16px}@S .ls-nome{font-size:16px}@S .ls-rodape{font-size:10.5px;padding:6px 8px}@S .ls-engrenagem{top:15px}}
@media(max-width:1100px) and (min-width:801px){@S .ls-cards{padding-left:5vw;padding-right:5vw}@S .ls-card{gap:16px;padding-left:19px;padding-right:19px}@S .ls-icone{width:48px;height:48px}@S .ls-nome{font-size:17px}@S .ls-rodape{gap:20px;padding-left:0;padding-right:0;font-size:10.5px}@S .ls-autor{padding-inline-start:20px}}
@media(max-width:800px){@S .ls-suite{grid-template-rows:16dvh 35dvh 36dvh minmax(13dvh,auto)}@S .ls-titulo{font-size:clamp(52px,9.5vw,76px)}@S .ls-engrenagem{top:16px;right:19px}@S .ls-engrenagem>summary{gap:7px;font-size:11px}@S .ls-engrenagem>summary svg{width:20px;height:20px}@S .ls-cards{grid-template-columns:repeat(2,minmax(0,1fr));grid-template-rows:repeat(3,minmax(0,1fr));padding:0 5vw 16px;gap:12px}@S .ls-card{gap:11px;border-radius:12px;padding:12px}@S .ls-icone{width:38px;height:38px}@S .ls-nome{font-size:clamp(12px,2.15vw,16px)}@S .ls-seta{width:24px;height:24px}@S .ls-seta svg{width:15px;height:15px}@S .ls-rodape{margin:0 5vw;padding:10px 0;flex-direction:column;justify-content:center;gap:8px;font-size:11px}@S .ls-autor{border:0;padding:0;font-size:11px}}
@media(max-width:420px){@S .ls-icone{width:30px;height:30px}@S .ls-card{gap:8px;padding:9px}@S .ls-nome{font-size:12px}@S .ls-seta{width:21px;height:21px}@S .ls-cards{gap:10px}@S .ls-titulo{font-size:56px}@S .ls-engrenagem>summary>span{display:none}@S .ls-engrenagem{top:21px}@S .ls-rodape{font-size:10.5px}}
@media(prefers-reduced-motion:reduce){@S .ls-engrenagem>summary svg{transition:none}@S .ls-card,@S .ls-engrenagem>summary,@S .ls-seta{transition:color 160ms ease,border-color 160ms ease,background 160ms ease}@S .ls-drift,@S .ls-icone,@S .ls-card{transform:none!important}@S .ls-luz{transition:none}}
""".replace(u"@S", ESCOPO)

JS = u"""<script id="radai-porta-menu">
(function(){
 var m = document.querySelector('[data-radai-engrenagem]');
 if(!m) return;
 var s = m.querySelector('summary');
 function aberto(){ return m.hasAttribute('open') }
 function veuAberto(){
  var v = document.getElementById('rx-veu');
  return !!(v && v.classList.contains('on'));
 }
 window.addEventListener('keydown', function(e){
  if(e.key !== 'Escape' || !aberto() || veuAberto()) return;
  m.removeAttribute('open');
  try{ if(s) s.focus() }catch(x){}
 }, true);
 document.addEventListener('click', function(e){
  if(!aberto() || veuAberto()) return;
  if(m.contains(e.target)) return;
  var v = document.getElementById('rx-veu');
  if(v && v.contains(e.target)) return;
  m.removeAttribute('open');
 });
 m.addEventListener('focusout', function(e){
  if(!aberto() || veuAberto()) return;
  var p = e.relatedTarget;
  if(!p || m.contains(p)) return;
  var v = document.getElementById('rx-veu');
  if(v && v.contains(p)) return;
  m.removeAttribute('open');
 });
})();
</script>"""


PAGINA = u"""<!doctype html><html lang="pt-BR" data-tema-fixo="escuro"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#020917">
<title>Local Suite</title>
<link rel="preload" href="/porta/Anton-Regular.ttf" as="font" type="font/ttf" crossorigin>
<link rel="preload" href="/porta/local-suite-vidros-v2.png" as="image">
<style id="radai-porta-css">@CSS@</style>
</head><body>
<main class="ls-suite" id="suite">
<header class="ls-topo" data-radai-tela="@RAIZ@">
<h1 class="ls-titulo"><span class="ls-local">Local</span> <span class="ls-grad">Suite</span></h1>
<details class="ls-engrenagem" data-radai-engrenagem>
<summary aria-label="Configurações">@ENGRENAGEM@<span data-radai-frase>Configurações</span></summary>
<div class="ls-menu">
<a href="/config" data-radai-frase>Configurações</a>
<span class="ls-encerrar" data-radai-encerrar></span>
</div>
</details>
</header>
<section class="ls-cena" id="scene" aria-hidden="true">
<div class="ls-rig" id="art-rig">
<div class="ls-drift" id="art-drift">
<svg class="ls-arte" viewBox="0 0 1672 941" preserveAspectRatio="xMidYMid meet"><image href="/porta/local-suite-vidros-v2.png" width="1672" height="941"/></svg>
<canvas class="ls-luz" id="light-canvas"></canvas>
<svg class="ls-vidros" id="glass-feedback" viewBox="0 0 1672 941" preserveAspectRatio="xMidYMid meet">
<defs>
<filter id="soft-light" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="9"/></filter>
<radialGradient id="pane-light"><stop offset="0" stop-color="#e8dcff" stop-opacity=".45"/><stop offset=".42" stop-color="#9d8bff" stop-opacity=".18"/><stop offset="1" stop-color="#4da3ff" stop-opacity="0"/></radialGradient>
</defs>
<g id="glass-layers"></g>
</svg>
</div>
</div>
</section>
<nav class="ls-cards" aria-label="os módulos da suíte">
@CARTOES@
</nav>
<footer class="ls-rodape">
<p data-radai-frase>@FRONTEIRA@</p>
<span class="ls-autor"><span data-radai-frase>Por</span> @AUTOR@</span>
</footer>
</main>
@JS@
<script defer src="/porta/porta.js"></script>
</body></html>"""


def pagina():
    cartoes = u"\n".join(c for c in (cartao(k, i) for i, k in enumerate(ordem()))
                         if c)
    return (PAGINA.replace(u"@CSS@", CSS)
            .replace(u"@RAIZ@", _esc(_nome_da_raiz()))
            .replace(u"@ENGRENAGEM@", _ENGRENAGEM)
            .replace(u"@CARTOES@", cartoes)
            .replace(u"@FRONTEIRA@", FRONTEIRA)
            .replace(u"@AUTOR@", _esc(AUTOR))
            .replace(u"@JS@", JS))
