# -*- coding: utf-8 -*-

CSS = u"""
.rc-capa{width:100%;max-width:820px;margin:0 auto;text-align:center}
.rc-chip{display:inline-flex;align-items:center;gap:7px;padding:6px 13px;
 border:1px solid var(--line-strong,var(--line-strong,#2a3a55));border-radius:999px;
 background:var(--panel,var(--panel,#0c1322));font-family:var(--mono,monospace);font-size:10px;
 letter-spacing:.16em;text-transform:uppercase;color:var(--text-muted,var(--text-muted,#a3b1c6))}
.rc-chip i{display:inline-grid;place-items:center;width:18px;height:18px;
 border-radius:5px;background:rgba(77,163,255,.14);color:var(--accent,var(--accent,#4DA3FF));
 font-size:11px;font-style:normal}
.rc-capa h1{margin:20px 0 0;font-size:44px;line-height:1.06;font-weight:700;
 letter-spacing:-.02em;color:var(--text,var(--text,#e6edf7))}
.rc-capa h1 span{color:var(--accent,var(--accent,#4DA3FF))}
.rc-frase{margin:14px 0 0;font-size:15px;color:var(--text-muted,var(--text-muted,#a3b1c6))}
.rc-risca{width:64px;height:2px;background:var(--accent,var(--accent,#4DA3FF));border-radius:2px;
 margin:26px auto}
.rc-rotulo{font-family:var(--mono,monospace);font-size:10px;letter-spacing:.18em;
 text-transform:uppercase;color:var(--text-dim,var(--text-dim,#72829b));margin-bottom:14px;
 text-align:center}
.rc-nota{margin-top:22px;font-size:12px;color:var(--text-dim,var(--text-dim,#72829b));
 text-align:center}
.rc-nota b{color:var(--text-muted,var(--text-muted,#a3b1c6));font-weight:500;text-transform:none;
 letter-spacing:0;font-size:12px}

.rc-cartoes{display:flex;gap:16px;justify-content:center;flex-wrap:wrap;
 margin:0 auto;max-width:820px}
.rc-cartao{flex:1 1 300px;max-width:380px;text-align:left;padding:20px 22px;
 border:1px solid var(--line,var(--line,#1e293b));border-radius:10px;
 background:var(--panel,var(--panel,#0c1322));color:inherit;text-decoration:none;
 display:block;transition:border-color .12s}
.rc-cartao:hover{border-color:var(--accent,var(--accent,#4DA3FF))}
.rc-cartao .ic{font-size:20px;color:var(--accent,var(--accent,#4DA3FF));line-height:1}
.rc-cartao h3{margin:14px 0 6px;font-size:16px;font-weight:600;
 color:var(--text,var(--text,#e6edf7))}
.rc-cartao p{margin:0;font-size:12.5px;line-height:1.55;
 color:var(--text-muted,var(--text-muted,#a3b1c6))}

.rc-capa.rc-compacta{max-width:none;text-align:left;display:flex;
 align-items:center;gap:14px;flex-wrap:wrap}
.rc-capa.rc-compacta h1{margin:0;font-size:24px;font-weight:600;
 letter-spacing:-.01em}
.rc-capa.rc-compacta .rc-frase{margin:0;font-size:12.5px}
.rc-capa.rc-compacta .rc-risca{display:none}
"""


CSS_DOC = u"""
:root{--bg:var(--bg-0,#060d1a);--painel:var(--panel,#0c1322);--linha:var(--line,#1e293b);--txt:var(--text,#e6edf7);--mut:var(--text-muted,#a3b1c6);
--ac:var(--accent,#4DA3FF);--al:var(--warn,#E1B23B)}
button.pri{color:var(--ok-txt,#fff)}
body{font-family:Inter,system-ui,'Segoe UI',Arial,sans-serif;background:var(--bg);
color:var(--txt);margin:0;padding:18px 18px 46px;line-height:1.65}
.env{max-width:820px;margin:0 auto}
h1{font-size:23px;margin:0 0 4px}
h2{font-size:16px;margin:26px 0 8px;color:var(--ac);
border-bottom:1px solid var(--linha);padding-bottom:6px}
h3{font-size:14px;margin:18px 0 5px;color:var(--text,#e6edf7)}
p,li{font-size:14px}p{margin:0 0 11px}
.sub{color:var(--mut);font-size:13px}
a{color:var(--ac)}
ul{margin:0 0 11px;padding-left:20px}li{margin-bottom:6px}
code{background:var(--bg-0,#060d1a);border:1px solid var(--linha);border-radius:4px;
padding:1px 5px;font-size:12.5px}
pre{background:var(--bg-1,#0a1120);border:1px solid var(--linha);border-radius:9px;
padding:18px 20px;font-family:var(--mono,ui-monospace),Consolas,monospace;
font-size:12px;line-height:1.62;color:var(--text,#e6edf7);white-space:pre-wrap;
word-wrap:break-word;overflow-x:auto}
.cx{background:var(--painel);border:1px solid var(--linha);border-radius:9px;
padding:13px 15px;margin:14px 0}
.cx.aviso{border-left:4px solid var(--al)}
.cx.destaque{border-left:3px solid var(--ac)}
.cx.falta{border:1px solid var(--borda-perigo,#552b23);background:var(--fundo-perigo,#160a08);color:var(--perigo,#E96A5C)}
a.voltar{text-decoration:none;color:var(--text,#e6edf7);background:var(--panel-2,#0f1729);
border:1px solid var(--accent-line,#2a3d57);border-radius:6px;padding:8px 13px;font-size:12.5px;
display:inline-block;margin-bottom:14px}
.decl{position:fixed;left:0;right:0;bottom:0;background:var(--bg-1,#0a1120);
border-top:1px solid var(--accent-line,#2a3d57);padding:9px 20px;font-size:12px;color:var(--text-muted,#a3b1c6);
display:flex;gap:10px;align-items:center}
.decl .m{width:7px;height:7px;border-radius:50%;background:var(--warn,#E1B23B);flex:none}
.decl b{color:var(--txt)}
"""


CSS_MARCA = u"""
.rc-topo{display:flex;align-items:center;gap:14px;padding:0 22px;
 height:var(--ui-topo,60px);
 border-bottom:1px solid var(--line,var(--line,#1e293b));background:var(--panel-2,var(--panel-2,#0f1729));
 flex-wrap:nowrap;box-sizing:border-box}
.rc-marca{display:flex;flex-direction:column;align-items:flex-start;gap:0;
 text-decoration:none;line-height:1.02;white-space:nowrap;flex:0 0 auto}
.rc-marca .rc-nome{font-size:19px;font-weight:700;letter-spacing:-.028em;
 color:var(--text,#e6edf7)}
.rc-marca .g{background:var(--marca-grad,linear-gradient(90deg,#4DA3FF 0%,#3DD9F0 48%,#9D8BFF 100%));
 -webkit-background-clip:text;background-clip:text;color:transparent}
.rc-marca .rc-sub{font-size:9.5px;letter-spacing:.26em;text-transform:uppercase;
 color:var(--text-dim,#72829b);font-weight:500;margin-top:1px}
.rc-marca:hover .rc-nome{color:var(--accent,#4DA3FF)}
.rc-seta{color:var(--text-dim,var(--text-dim,#72829b));font-size:15px;
 opacity:.65}
.rc-tela{font-size:13.5px;color:var(--text,#e6edf7);font-weight:600}
a.rc-passo{font-size:13.5px;color:var(--text-muted,#a3b1c6);text-decoration:none;
 font-weight:500;border-bottom:1px solid transparent}
a.rc-passo:hover{color:var(--accent,#4DA3FF);border-bottom-color:var(--accent,#4DA3FF)}
.rc-topo .dir{margin-left:auto;display:flex;gap:10px;align-items:center}
.rc-controles{display:flex;gap:9px;align-items:center}
a.rc-voltar{text-decoration:none;color:var(--text,#e6edf7);background:var(--panel-2,#0f1729);
 border:1px solid var(--accent-line,#2a3d57);border-radius:6px;padding:7px 12px;font-size:12.5px;
 display:inline-block;white-space:nowrap}
a.rc-voltar:hover{border-color:var(--accent,var(--accent,#4DA3FF));color:var(--accent,var(--accent,#4DA3FF))}
"""


def marca(compacta=False):
    baixo = (u"" if compacta
             else u'<span class="rc-sub" data-radai-frase>Local Suite</span>')
    return (u'<a class="rc-marca" href="/" title="Radioterapia.AI Local">'
            u'<span class="rc-nome">radioterapia<span class="g">.ai</span></span>'
            u'%s</a>' % baixo)


def cabecalho(tela=u"", com_idioma=False, chave=u"", com_seletor=False):
    passos = []
    try:
        import radai_breadcrumb
        passos = radai_breadcrumb.trilha(chave) if chave else []
    except Exception:
        passos = []

    if passos:
        meio = []
        for i, (rot, rota) in enumerate(passos[1:], 1):
            ultimo = (i == len(passos) - 1)
            meio.append(u'<span class="rc-seta">&#8250;</span>')
            meio.append(
                u'<span class="rc-tela" data-radai-frase>%s</span>' % _esc(rot)
                if ultimo else
                u'<a class="rc-passo" href="%s" data-radai-frase>%s</a>'
                % (rota, _esc(rot)))
        migalhas = u"".join(meio)
    else:
        migalhas = (u'<span class="rc-seta">&#8250;</span>'
                    u'<span class="rc-tela" data-radai-frase>%s</span>'
                    % _esc(tela)) if tela else u""

    # GUARDA: a âncora do Fechar só é escrita pela porta (radai_porta); aqui, sempre o Voltar.
    alvo, rot = u"/", u"In&iacute;cio"
    try:
        import radai_breadcrumb
        p = radai_breadcrumb.pai(chave)
        if p:
            rot, alvo = _esc(p[0]), p[1]
    except Exception:
        pass
    dir_ = (u'<a class="ui-volta" href="%s" data-radai-voltar '
            u'data-radai-pai="%s" data-radai-nome-pai="%s" title="Voltar para %s" '
            u'aria-label="Voltar para %s"><span class="v-seta">&#8592;</span>'
            u'<span class="v-txt" data-radai-frase>Voltar</span></a>'
            % (alvo, alvo, rot, rot, rot))

    if com_seletor:
        dir_ = u'<span data-radai-idiomas></span>' + dir_

    nome = u""
    try:
        import radai_breadcrumb
        nome = radai_breadcrumb.rotulo(chave) if chave else u""
    except Exception:
        nome = u""
    nome = nome or tela or u""
    attr = (u' data-radai-tela="%s"' % _esc(nome)) if nome else u""

    return (u'<header class="rc-topo"%s>%s%s<div class="dir">%s</div></header>'
            % (attr, marca(), migalhas, dir_))


def _esc(t):
    return (str(t or "").replace(u"&", u"&amp;").replace(u"<", u"&lt;")
            .replace(u">", u"&gt;").replace(u'"', u"&quot;"))


def capa(chip, titulo, destaque=u"", frase=u"", icone=u"◈", compacta=False,
         colado=False):
    partes = [u'<div class="rc-capa%s">' % (u" rc-compacta" if compacta else u"")]
    if chip:
        partes.append(u'<span class="rc-chip"><i>%s</i> %s</span>'
                      % (_esc(icone), _esc(chip)))
    partes.append(u'<h1>%s%s</h1>'
                  % (_esc(titulo),
                     ((u'' if colado else u' ') + u'<span>%s</span>'
                      % _esc(destaque)) if destaque else u""))
    if frase:
        partes.append(u'<p class="rc-frase">%s</p>' % _esc(frase))
    if not compacta:
        partes.append(u'<div class="rc-risca"></div>')
    partes.append(u'</div>')
    return u"".join(partes)


def cartao(titulo, texto, href=u"", icone=u"", extra=u""):
    tag = u"a" if href else u"div"
    alvo = (u' href="%s"' % _esc(href)) if href else u""
    return (u'<%s class="rc-cartao"%s%s>'
            u'%s<h3>%s</h3><p>%s</p></%s>'
            % (tag, alvo, (u" " + extra) if extra else u"",
               (u'<div class="ic">%s</div>' % _esc(icone)) if icone else u"",
               _esc(titulo), _esc(texto), tag))


def aplicar(pagina):
    if not pagina or u"rc-capa{" in pagina:
        return pagina
    baixa = pagina.lower()
    fim = baixa.find(u"</head>")
    if fim < 0:
        return pagina
    return (pagina[:fim] + u"<style>" + CSS + CSS_MARCA + u"</style>"
            + pagina[fim:])
