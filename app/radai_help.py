# -*- coding: utf-8 -*-

MARCA = u"radai-ajuda-css"

CSS = u"""<style id="radai-ajuda-css">
.rj{position:relative;display:inline-flex;align-items:center;justify-content:center;
 width:15px;height:15px;border-radius:50%;border:1px solid var(--line,#1e293b);
 background:var(--panel-2,#0f1729);color:var(--text-dim,#72829b);
 font-size:10px;font-weight:700;cursor:help;vertical-align:middle;
 margin-left:5px;line-height:1;user-select:none;flex:none}
.rj:hover,.rj:focus-visible{border-color:var(--accent,#4DA3FF);
 color:var(--accent,#4DA3FF);outline:none}
.rj::after{content:attr(data-rj);position:absolute;bottom:calc(100% + 8px);
 left:50%;transform:translateX(-50%) translateY(3px);
 width:max-content;max-width:min(340px,72vw);
 background:var(--panel-2,#0f1729);color:var(--text,#e6edf7);
 border:1px solid var(--accent-line,#2a3d57);border-radius:9px;
 padding:9px 12px;font-size:12px;font-weight:400;line-height:1.58;
 text-align:left;white-space:pre-line;letter-spacing:normal;
 box-shadow:0 10px 30px rgba(0,0,0,.45);
 opacity:0;pointer-events:none;transition:opacity .13s,transform .13s;
 z-index:3000}
.rj::before{content:"";position:absolute;bottom:calc(100% + 3px);left:50%;
 transform:translateX(-50%) translateY(3px);border:5px solid transparent;
 border-top-color:var(--accent-line,#2a3d57);opacity:0;
 transition:opacity .13s,transform .13s;pointer-events:none;z-index:3001}
.rj:hover::after,.rj:focus-visible::after,
.rj:hover::before,.rj:focus-visible::before{opacity:1;
 transform:translateX(-50%) translateY(0)}
.rj.esq::after{left:0;transform:translateX(0) translateY(3px)}
.rj.esq:hover::after,.rj.esq:focus-visible::after{transform:translateX(0)}
.rj.dir::after{left:auto;right:0;transform:translateX(0) translateY(3px)}
.rj.dir:hover::after,.rj.dir:focus-visible::after{transform:translateX(0)}
@media (hover:none){.rj:focus::after,.rj:focus::before{opacity:1;
 transform:translateX(-50%) translateY(0)}}
</style>"""


def _esc(t):
    return (str(t or "").replace(u"&", u"&amp;").replace(u"<", u"&lt;")
            .replace(u">", u"&gt;").replace(u'"', u"&quot;"))


def ajuda(texto, lado=u""):
    if not texto:
        return u""
    cls = u"rj %s" % lado if lado in ("esq", "dir") else u"rj"
    return (u'<span class="%s" tabindex="0" role="note" data-rj="%s" '
            u'aria-label="%s">?</span>'
            % (cls, _esc(texto), _esc(texto)))


def aplicar(pagina):
    if not pagina or MARCA in pagina:
        return pagina
    i = pagina.lower().find(u"</head>")
    if i < 0:
        return pagina
    return pagina[:i] + CSS + pagina[i:]
