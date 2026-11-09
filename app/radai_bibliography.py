# -*- coding: utf-8 -*-
import json
import os

import radai_menu

AQUI = os.path.dirname(os.path.abspath(__file__))
CANDIDATOS = (("data", "bibliography.json"),
              ("dados", "bibliografia.json"))


def _arquivo():
    for pasta, nome in CANDIDATOS:
        p = os.path.join(AQUI, pasta, nome)
        if os.path.isfile(p):
            return p
    return os.path.join(AQUI, CANDIDATOS[0][0], CANDIDATOS[0][1])


ARQUIVO = _arquivo()

CSS = u"""
.wrap{max-width:1080px;margin:0 auto;padding:0 18px 40px 18px}
.bi-sec{margin-top:26px}
.bi-sec > h2{font-size:15px;margin:0 0 4px 0}
.bi-sec > p.sub{margin:0 0 14px 0;line-height:1.6}
.bi-item{border:1px solid var(--line);border-radius:10px;padding:14px 16px;
 margin-bottom:10px;background:var(--panel)}
.bi-item.fundamental{border-left:3px solid var(--accent)}
.bi-item .tit{font-size:13.5px;font-weight:600;line-height:1.4;color:var(--text)}
.bi-item .meta{font-size:11px;color:var(--text-dim);margin-top:3px;
 font-family:var(--mono,monospace)}
.bi-item .mudou{font-size:12.5px;color:var(--text-muted);line-height:1.6;
 margin-top:9px;padding-left:11px;border-left:2px solid var(--line)}
.bi-item .mudou b.rot{display:block;font-size:9.5px;letter-spacing:.11em;
 text-transform:uppercase;color:var(--text-dim);margin-bottom:3px;font-weight:600}
.bi-item a.doi{color:var(--accent);text-decoration:none;font-family:var(--mono,monospace);
 font-size:11px}
.bi-item a.doi:hover{text-decoration:underline}
.bi-peso{font-size:9.5px;letter-spacing:.1em;text-transform:uppercase;
 padding:2px 7px;border-radius:99px;border:1px solid var(--line);
 color:var(--text-dim);margin-left:8px;white-space:nowrap}
.bi-peso.fundamental{border-color:var(--accent);color:var(--accent)}
.bi-peso.conferir{border-color:var(--aviso);color:var(--aviso)}
.bi-item.restrito{border-left:3px solid var(--aviso);background:rgba(255,200,87,.05)}
.bi-item .lic{display:flex;gap:16px;flex-wrap:wrap;margin-top:8px;font-size:11.5px}
.bi-item .lic div span{display:block;font-size:9.5px;letter-spacing:.1em;
 text-transform:uppercase;color:var(--text-dim)}


.bi-conta{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0 0 0}
.bi-conta .p{border:1px solid var(--line);border-radius:8px;padding:7px 12px;
 font-size:11.5px;color:var(--text-dim)}
.bi-conta .p b{display:block;font-size:18px;font-family:var(--mono,monospace);
 color:var(--text)}
"""


def _dados():
    try:
        with open(ARQUIVO, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"artigos": [], "modelos": []}


def _esc(t):
    return (str(t or "").replace(u"&", u"&amp;").replace(u"<", u"&lt;")
            .replace(u">", u"&gt;").replace(u'"', u"&quot;"))


def _artigo(a):
    peso = str(a.get("peso") or "contexto")
    doi = str(a.get("doi") or "")
    return (
        u'<div class="bi-item %s">' % (u"fundamental" if peso == "fundamental" else u"")
        + u'<div class="tit">%s<span class="bi-peso %s">%s</span>%s</div>'
          % (_esc(a.get("titulo")), _esc(peso), _esc(peso),
             (u'<span class="bi-peso conferir">%s</span>'
              % (u"DOI a conferir" if a.get("doi") else u"sem DOI"))
             if a.get("precisa_conferir") else u"")
        + u'<div class="meta">%s%s%s</div>'
          % (_esc(a.get("autores") or u"—"),
             u" · " + _esc(a.get("revista")) if a.get("revista") else u"",
             u" · " + _esc(a.get("ano")) if a.get("ano") else u"")
        + (u'<div style="margin-top:5px"><a class="doi" target="_blank" '
           u'rel="noopener" href="https://doi.org/%s">doi:%s</a></div>'
           % (_esc(doi), _esc(doi)) if doi else u"")
        + (u'<div class="mudou"><b class="rot">o que mudou aqui</b>%s</div>'
           % _esc(a.get("mudou")) if a.get("mudou") else u"")
        + u'</div>')


def _modelo(m):
    restrito = str(m.get("uso") or "") == "nao_comercial"
    return (
        u'<div class="bi-item %s">' % (u"restrito" if restrito else u"")
        + u'<div class="tit">%s%s</div>'
          % (_esc(m.get("nome")),
             u'<span class="bi-peso" style="border-color:var(--aviso);color:var(--aviso)">'
             u'não comercial</span>' if restrito else u"")
        + u'<div class="meta">%s</div>' % _esc(m.get("papel"))
        + u'<div class="lic">'
        + u'<div><span>licença do código</span>%s</div>' % _esc(m.get("licenca_codigo") or u"—")
        + u'<div><span>licença dos pesos</span>%s</div>' % _esc(m.get("licenca_pesos") or u"—")
        + (u'<div><span>origem</span><a class="doi" target="_blank" rel="noopener" '
           u'href="%s">%s</a></div>' % (_esc(m.get("url")), _esc(m.get("url")))
           if m.get("url") else u"")
        + u'</div>'
        + (u'<div class="mudou"><b class="rot">o que isso significa</b>%s</div>'
           % _esc(m.get("nota")) if m.get("nota") else u"")
        + u'</div>')





def _pagina():
    d = _dados()
    arts = list(d.get("artigos") or [])
    mods = list(d.get("modelos") or [])
    ordem = {"fundamental": 0, "importante": 1, "contexto": 2}
    arts.sort(key=lambda a: (ordem.get(str(a.get("peso")), 3),
                             -int(str(a.get("ano") or 0)[:4] or 0)))
    guias = [a for a in arts if str(a.get("categoria") or "") == "diretriz"]
    arts = [a for a in arts if str(a.get("categoria") or "") != "diretriz"]
    n_fund = sum(1 for a in (arts + guias) if a.get("peso") == "fundamental")
    n_ref = len(arts) + len(guias)
    n_restrito = sum(1 for m in mods if m.get("uso") == "nao_comercial")
    return PAGINA \
        .replace("@CSS@", CSS) \
        .replace("@CONTA@",
                 u'<div class="bi-conta">'
                 u'<div class="p"><b>%d</b>referências</div>'
                 u'<div class="p"><b>%d</b>fundamentais</div>'
                 u'<div class="p"><b>%d</b>modelos</div>'
                 u'<div class="p"><b>%d</b>com licença restritiva</div></div>'
                 % (n_ref, n_fund, len(mods), n_restrito)) \
        .replace("@ARTIGOS@", u"".join(_artigo(a) for a in arts)) \
        .replace("@DIRETRIZES@", u"".join(_artigo(a) for a in guias)) \
        .replace("@MODELOS@", u"".join(_modelo(m) for m in mods))


PAGINA = u"""<!doctype html><html><head><meta charset="utf-8">
<title>Bibliografia · Radioterapia.AI</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>@CSS@</style></head><body><div class="wrap">

<div class="rc-capa">
 <div class="rc-eyebrow">PROCEDÊNCIA</div>
 <h1 class="rc-titulo">De onde vem <span class="g">cada decisão</span></h1>
 <p class="sub" style="line-height:1.65;max-width:74ch">Os artigos que sustentam
  o que este programa faz, e os modelos que reconhecem os órgãos. Cada
  referência diz <b>o que mudou aqui</b> — referência que não mudou nada é
  leitura, não bibliografia. E só entra o que foi lido.</p>
</div>
@CONTA@

<div class="bi-sec">
 <h2>Modelos</h2>
 <p class="sub">Nenhum deles é nosso. O que construímos é a camada que os põe na
  estação — e a licença dos <b>pesos</b> costuma não ser a do código.</p>
 @MODELOS@
</div>


<div class="bi-sec">
 <h2>Diretrizes de contorno</h2>
 <p class="sub">O que cada estrutura <b>deve ser</b>, e segundo quem. Elas nao
  dizem como o programa calcula &mdash; dizem onde o contorno comeca e onde
  termina.</p>
 @DIRETRIZES@
</div>
<div class="bi-sec">
 <h2>Referências</h2>
 <p class="sub">Ordenadas pelo peso que tiveram nas decisões, e não por ano.
  O DOI abre a página do artigo.</p>
 @ARTIGOS@
</div>


</div></body></html>"""


def montar(app):
    from fastapi.responses import HTMLResponse

    @app.get("/bibliografia", response_class=HTMLResponse)
    def _tela():
        return radai_menu.aplicar(_pagina(), "bibliografia", com_tarefas=False)

    return app
