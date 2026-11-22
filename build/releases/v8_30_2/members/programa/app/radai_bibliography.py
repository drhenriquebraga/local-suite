# -*- coding: utf-8 -*-
import json
import os

import radai_menu
import radai_termos_catalogo

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
.bi-item .lic{display:flex;gap:16px;flex-wrap:wrap;margin-top:8px;font-size:11.5px}
.bi-item .lic div span{display:block;font-size:9.5px;letter-spacing:.1em;
 text-transform:uppercase;color:var(--text-dim)}


.bi-conta{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0 0 0}
.bi-conta .p{border:1px solid var(--line);border-radius:8px;padding:7px 12px;
 font-size:11.5px;color:var(--text-dim)}
.bi-conta .p b{display:block;font-size:18px;font-family:var(--mono,monospace);
 color:var(--text)}
.bi-abas{display:flex;gap:4px;flex-wrap:wrap;border-bottom:1px solid var(--line);margin:20px 0}
.bi-abas a{padding:10px 14px;border-bottom:3px solid transparent;color:var(--text-dim);text-decoration:none}
.bi-abas a[aria-selected=true]{border-color:var(--accent);color:var(--text);font-weight:650}
.bi-abas a:focus-visible,.bi-links a:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.bi-links{display:flex;flex-wrap:wrap;gap:8px 20px}
.bi-links a{color:var(--accent)}
.bi-recibo{display:grid;grid-template-columns:auto 1fr;gap:6px 16px;margin-block:10px 18px}
.bi-recibo dt{color:var(--text-dim)}.bi-recibo dd{margin:0;overflow-wrap:anywhere}
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


def _guia_leitura(a):
    temas = " · ".join(a.get("temas") or ())
    return ((u'<div class="meta">%s</div>' % _esc(temas) if temas else u"")
            + (u'<div class="meta">%s</div>' % _esc(a["localizador"]) if a.get("localizador") else u""))


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
        + (u'<div class="mudou">%s</div>' % _esc(a["nota"]) if a.get("nota") else u"")
        + _guia_leitura(a)
        + u'</div>')


def _modelo(m):
    return (
        u'<div class="bi-item bi-modelo">'
        + u'<div class="tit">%s</div>' % _esc(m.get("nome"))
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





def _recibo():
    import radai_consent
    registro = radai_consent.aceite()
    if not registro.get("versao"):
        return '<p>Ainda não há aceite registrado nesta estação.</p>'
    situacao = ("Aceite vigente." if radai_consent.aceito() else
                "O aceite precisa ser atualizado.")
    campos = [("Versão aceita:", registro["versao"]), ("Data do aceite", registro.get("quando"))]
    if "ferramentas_opcionais" in registro:
        # Preserve exactly the optional scope acknowledged by this receipt.
        nomes = {"cads_open": "CADS open", "lung-rt": "LUNG RT", "moose": "MOOSE",
                 "neuro-rt": "NEURO RT", "nv_segment_ct": "NV-Segment-CT"}
        grupos = sorted(nomes.get(g, g) for g in registro["ferramentas_opcionais"] or ())
        if grupos:
            campos.append(("Ferramentas incluídas no aceite", " · ".join(grupos)))
    linhas = "".join('<dt>%s</dt><dd>%s</dd>' % (_esc(k), _esc(v)) for k,v in campos if v)
    return '<p>%s</p><dl class="bi-recibo">%s</dl>' % (situacao, linhas)


def _pagina(aba="bibliografia"):
    d = _dados()
    arts = list(d.get("artigos") or [])
    mods = sorted(d.get("modelos") or [], key=lambda m: m["nome"].casefold())
    ordem = {"fundamental": 0, "importante": 1, "contexto": 2}
    arts.sort(key=lambda a: (ordem.get(str(a.get("peso")), 3),
                             -int(str(a.get("ano") or 0)[:4] or 0)))
    guias = [a for a in arts if str(a.get("categoria") or "") == "diretriz"]
    arts = [a for a in arts if str(a.get("categoria") or "") != "diretriz"]
    n_fund = sum(1 for a in (arts + guias) if a.get("peso") == "fundamental")
    leituras = d.get("leituras_em_avaliacao", [])
    n_ref = len(arts) + len(guias) + len(leituras)
    termos = aba == "termos"
    return PAGINA \
        .replace("@CSS@", CSS + radai_termos_catalogo.CSS) \
        .replace("@BIB_ATIVA@", "false" if termos else "true") \
        .replace("@TERMOS_ATIVA@", "true" if termos else "false") \
        .replace("@BIB_FOCO@", "-1" if termos else "0") \
        .replace("@TERMOS_FOCO@", "0" if termos else "-1") \
        .replace("@BIB_OCULTA@", "hidden" if termos else "") \
        .replace("@TERMOS_OCULTA@", "" if termos else "hidden") \
        .replace("@RECIBO@", _recibo()) \
        .replace("@CONTA@",
                 u'<div class="bi-conta">'
                 u'<div class="p"><b>%d</b>referências</div>'
                 u'<div class="p"><b>%d</b>fundamentais</div>'
                 u'<div class="p"><b>%d</b>modelos</div></div>'
                 % (n_ref, n_fund, len(mods))) \
        .replace("@LEITURAS@", u"".join(_artigo(a) for a in leituras)) \
        .replace("@ARTIGOS@", u"".join(_artigo(a) for a in arts)) \
        .replace("@DIRETRIZES@", u"".join(_artigo(a) for a in guias)) \
        .replace("@MODELOS@", u"".join(_modelo(m) for m in mods))


PAGINA = u"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<title>Referências e licenças · Local Suite</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>@CSS@</style></head><body><main class="wrap">

<div class="rc-capa">
 <h1 class="rc-titulo">Referências e licenças</h1>
</div>
<nav class="bi-abas" role="tablist" aria-label="Referências e licenças">
 <a role="tab" href="/bibliografia" id="aba-bibliografia" aria-controls="painel-bibliografia"
    aria-selected="@BIB_ATIVA@" tabindex="@BIB_FOCO@">Bibliografia e procedência</a>
 <a role="tab" href="/licencas-ferramentas" id="aba-termos" aria-controls="painel-termos"
    aria-selected="@TERMOS_ATIVA@" tabindex="@TERMOS_FOCO@">Termos de uso aceitos</a>
</nav>
<section role="tabpanel" id="painel-bibliografia" aria-labelledby="aba-bibliografia" @BIB_OCULTA@>
<div class="bi-links"><a href="/procedencia">Procedência das estruturas</a></div>
@CONTA@

<div class="bi-sec">
 <h2>Modelos</h2>
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
<div class="bi-sec">
 <h2>Leituras para avaliação</h2>
 <p class="sub">Estudos sobre candidatos a modelos, anatomia e avaliação de contornos.</p>
 @LEITURAS@
</div>


</section>
<section role="tabpanel" id="painel-termos" aria-labelledby="aba-termos" @TERMOS_OCULTA@>
@RECIBO@
<h2>Documentos vigentes</h2>
<div class="bi-links"><a href="/termos">Termos de uso</a>
 <a href="/politica-privacidade">Política de privacidade</a>
 <a href="/creditos">Créditos e licenças</a></div>
<h2>Ferramentas e licenças</h2>
@CATALOGO@
</section></main>
<script>
(function() {
 const tabs=Array.from(document.querySelectorAll('.bi-abas [role=tab]'));
 let idiomaOrdenado='';
 function ordenarFichas() {
   const idioma=document.documentElement.lang;
   if(idioma===idiomaOrdenado) return;
   const ordem=new Intl.Collator(idioma,{sensitivity:'base',numeric:true});
   for(const [ficha,titulo] of [['.bi-modelo','.tit'],['.lic-item','summary']]) {
     const todos=Array.from(document.querySelectorAll(ficha));
     todos.sort((a,b)=>ordem.compare(a.querySelector(titulo).textContent,b.querySelector(titulo).textContent));
     todos.forEach(el=>el.parentElement.appendChild(el));
   }
   idiomaOrdenado=idioma;
   if(location.hash) pelaURL();
 }
 new MutationObserver(ordenarFichas).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
 document.addEventListener('DOMContentLoaded',ordenarFichas);
 function selecionar(tab) {
   tabs.forEach(function(t) {
     const ativa=t===tab;
     t.setAttribute('aria-selected',String(ativa));
     t.tabIndex=ativa?0:-1;
     document.getElementById(t.getAttribute('aria-controls')).hidden=!ativa;
   });
 }
 function pelaURL() {
   const termos=location.pathname==='/licencas-ferramentas' || new URLSearchParams(location.search).get('aba')==='termos';
   selecionar(tabs[termos?1:0]);
   const ficha=document.getElementById(location.hash.slice(1));
   if(termos && ficha && ficha.classList.contains('lic-item')) {
     ficha.open=true;
     ficha.scrollIntoView({block:'start'});
   }
 }
 tabs.forEach(function(t,i) {
   t.addEventListener('click', function(e) {
     if(e.ctrlKey || e.metaKey || e.shiftKey || e.altKey || e.button!==0) return;
     e.preventDefault();
     if(t.getAttribute('aria-selected')==='true') return;
     history.pushState(null,'',t.href);
     selecionar(t);
   });
   t.addEventListener('keydown',function(e) {
     if(!['Home','End','ArrowLeft','ArrowRight'].includes(e.key)) return;
     e.preventDefault();
     const prox=e.key==='Home'?0:e.key==='End'?tabs.length-1:1-i;
     tabs[prox].focus();
     tabs[prox].click();
   });
 });
 window.addEventListener('popstate',pelaURL);
 window.addEventListener('hashchange',pelaURL);
 pelaURL();
})();
</script></body></html>"""


def pagina_com_menu(aba="bibliografia"):
    pagina = radai_menu.aplicar(_pagina(aba), "bibliografia", com_tarefas=False)
    return pagina.replace("@CATALOGO@", radai_termos_catalogo.bloco())


def montar(app):
    from fastapi.responses import HTMLResponse

    @app.get("/bibliografia", response_class=HTMLResponse)
    def _tela(aba: str = "bibliografia"):
        return pagina_com_menu(aba)

    return app
