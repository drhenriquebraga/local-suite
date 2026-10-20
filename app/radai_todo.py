# -*- coding: utf-8 -*-
LARGURA = 380
RECOLHIDA = 44




def atividade(ler_vigia=None):
    fora = []

    try:
        v = (ler_vigia() or {}) if ler_vigia else {}
    except Exception:
        v = {}
    if v:
        pausado = bool(v.get("pausado") or v.get("paused"))
        atual = v.get("atual") or v.get("current") or {}
        fila = int(v.get("n_queue") or v.get("fila") or 0)
        if atual:
            fora.append({
                "id": "vigia:serie", "tipo": "rodando", "icone": u"◐",
                "titulo": u"Segmentando %s" % (atual.get("pid") or u"uma série"),
                "detalhe": u"…%s · %s" % (str(atual.get("uid8")
                                              or atual.get("uid") or "")[-8:],
                                          atual.get("etapa")
                                          or u"em processamento"),
                "href": "/vigia"})
        elif pausado:
            fora.append({
                "id": "vigia:pausado", "tipo": "parado", "icone": u"⏸",
                "titulo": u"Fila de estudo pausada",
                "detalhe": (u"%d série(s) esperando na fila" % fila) if fila
                           else u"nada na fila",
                "href": "/vigia"})
        elif not str(v.get("root") or "").strip():
            fora.append({
                "id": "vigia:sem_pasta", "tipo": "info", "icone": u"○",
                "titulo": u"Fila de estudo em espera",
                "detalhe": u"sem pasta configurada — ela não varre nada até "
                           u"o ROOT ser preenchido",
                "botao": u"Configurar",
                "href": "/config"})
        else:
            fora.append({
                "id": "vigia:ativo", "tipo": "rodando", "icone": u"◐",
                "titulo": u"Fila de estudo ativa",
                "detalhe": (u"%d na fila · varrendo a pasta" % fila) if fila
                           else u"varrendo a pasta, nada pendente",
                "href": "/vigia"})

    try:
        import radai_batch
        e = radai_batch.estado() or {}
        if e.get("rodando"):
            fora.append({
                "id": "lote", "tipo": "rodando", "icone": u"▶",
                "titulo": u"Rodar agora: %s/%s"
                          % (e.get("feitas", 0), e.get("total", 0)),
                "detalhe": u"%s · %s" % (e.get("atual") or u"", e.get("etapa")
                                         or u"processando"),
                "href": "/lote"})
    except Exception:
        pass

    if fora:
        try:
            import radai_cleaner as LP
            m = LP.memoria_da_estacao()
            if m.get("total_mb"):
                apertado = m["livre_mb"] < 4000
                fora.append({
                    "id": "recurso:mem", "tipo": "aviso" if apertado else "info",
                    "icone": u"▤",
                    "titulo": u"%s MB de memória livres"
                              % "{:,}".format(m["livre_mb"]).replace(",", "."),
                    "detalhe": (u"apertado para uma TC de planejamento — "
                                u"veja o que dá para liberar")
                               if apertado else
                               (u"%d%% da memória em uso" % m.get("pct", 0)),
                    "href": "/config#ps_limpar",
                    "botao": u"Otimizar"})
        except Exception:
            pass
    return fora


CSS = u"""
<style id="radai-tarefas-css">
body{margin-right:%(w)dpx !important}
html.dir-recolhida body{margin-right:%(r)dpx !important}
.radai-tarefas{position:fixed;right:0;top:0;bottom:0;width:%(w)dpx;z-index:7;
 background:var(--bg-1,#0a1120);border-left:1px solid var(--line,#1e293b);
 font-family:var(--font-display,Segoe UI,Arial);box-sizing:border-box;
 display:flex;flex-direction:column;overflow:hidden}
html.dir-recolhida .radai-tarefas{width:%(r)dpx}
@media (min-width:1101px){
 html.dir-abrindo .radai-tarefas{--ui-painel-curso:%(curso)dpx;
  animation:uiPainelEntra var(--ui-painel-abre,400ms)
   var(--ui-painel-curva,cubic-bezier(.22,1,.36,1)) both}
 html.dir-fechando .radai-tarefas{--ui-painel-curso:%(curso)dpx;pointer-events:none;
  animation:uiPainelSai var(--ui-painel-fecha,350ms)
   var(--ui-painel-curva,cubic-bezier(.22,1,.36,1)) both}
}
@media (prefers-reduced-motion:reduce){
 html.dir-abrindo .radai-tarefas,html.dir-fechando .radai-tarefas{animation:none}
}
.radai-tarefas button{margin:0}

.radai-tarefas .dir-abas{position:relative;flex:0 0 auto;display:flex;
 align-items:stretch;justify-content:center;gap:4px;padding:8px 30px 0;
 border-bottom:1px solid var(--line-strong,#2a3a55)}
.radai-tarefas .dir-aba{position:relative;z-index:1;flex:1 1 0;min-width:0;
 max-width:none;display:flex;align-items:center;justify-content:center;gap:7px;
 min-height:34px;margin:0 0 -1px;padding:7px 12px 8px;background:transparent;
 border:1px solid transparent;border-bottom:0;
 border-radius:var(--r-lg,8px) var(--r-lg,8px) 0 0;cursor:pointer;
 color:var(--text-dim,#72829b);
 font:600 10.5px/1.2 var(--font-mono,ui-monospace,Consolas,monospace);
 letter-spacing:.06em;text-transform:uppercase;white-space:normal;
 text-align:center;line-height:1.3;
 transition:color .16s ease,background-color .16s ease,border-color .16s ease}
.radai-tarefas .dir-aba::before{content:"";position:absolute;left:-1px;right:-1px;
 top:-1px;height:2px;border-radius:var(--r-lg,8px) var(--r-lg,8px) 0 0;
 background:transparent;transition:background-color .16s ease}
.radai-tarefas .dir-aba:hover{color:var(--text,#e6edf7);
 background:var(--panel,#0c1322)}
.radai-tarefas .dir-aba[aria-selected="true"]{color:var(--text,#e6edf7);
 background:var(--panel-2,#0f1729);border-color:var(--line-strong,#2a3a55)}
.radai-tarefas .dir-aba[aria-selected="true"]::before{background:var(--accent,#4DA3FF)}
.radai-tarefas .dir-aba:focus-visible{outline:2px solid var(--accent,#4DA3FF);
 outline-offset:-3px}
.radai-tarefas .dir-aba[data-aba="fila"]>span[data-radai-frase]{min-width:0;
 overflow-wrap:anywhere}
.radai-tarefas .dir-aba .n{font-variant-numeric:tabular-nums;
 color:var(--text-muted,#a3b1c6);letter-spacing:0}
.radai-tarefas .dir-aba .n.zero{display:none}
.radai-tarefas .dir-aba .ab-rot{display:inline-block;position:relative;
 padding-right:7px}
.radai-tarefas .dir-abas .dobra{position:absolute;right:4px;top:12px;
 background:none;border:0;color:var(--text-dim,#72829b);cursor:pointer;
 font-size:15px;line-height:1;padding:4px 6px}
.radai-tarefas .dir-abas .dobra:hover{color:var(--text,#e6edf7)}
.radai-tarefas .fila,.radai-tarefas .logreg{background:var(--panel-2,#0f1729)}
.radai-tarefas .fila{flex:1 1 0;min-height:0;display:flex;
 flex-direction:column}
.radai-tarefas .fila[hidden],.radai-tarefas .logreg[hidden]{display:none !important}
.radai-tarefas .pt{width:6px;height:6px;border-radius:999px;
 background:var(--text-dim,#72829b);display:inline-block;flex:0 0 auto}
.radai-tarefas .pt.ok{background:var(--success,#5BC57F)}
.radai-tarefas .pt.parado{background:var(--warn,#E1B23B)}
.radai-tarefas .pt.erro{background:var(--perigo,#E96A5C)}
.radai-tarefas .notif-pede{margin:8px 8px 0;border:1px solid var(--accent-line,#2a3d57);
 background:var(--accent-fraco,rgba(77,163,255,.14));border-radius:var(--r-md,6px);
 padding:8px 9px;font-size:11.5px;line-height:1.45;color:var(--text-muted,#a3b1c6)}
.radai-tarefas .notif-pede[hidden]{display:none}
.radai-tarefas .notif-pede .otm-bts{display:flex;gap:6px;margin-top:7px;flex-wrap:wrap}
.radai-tarefas .notif-pede button{font:600 11px/1 var(--font-display,inherit);
 padding:6px 10px;border-radius:var(--r-sm,5px);cursor:pointer;
 border:1px solid var(--line-strong,#2a3a55);background:var(--panel-2,#0f1729);
 color:var(--text,#e6edf7)}
.radai-tarefas .notif-pede button.sim{background:var(--accent,#4DA3FF);
 border-color:var(--accent,#4DA3FF);color:var(--bg-0,#060d1a)}

.radai-tarefas .fila .corpo{flex:1 1 auto;min-height:0;overflow-y:auto;
 padding:8px}
.radai-tarefas .pipe{flex:0 0 auto;display:grid;
 grid-template-columns:1fr 1fr;gap:7px;padding:10px;
 border-bottom:1px solid var(--line,#1e293b)}
.radai-tarefas .pipe-bt{display:flex;align-items:center;justify-content:center;
 gap:6px;min-height:36px;padding:8px 10px;border-radius:var(--r-lg,8px);
 border:1px solid var(--line-strong,#2a3a55);
 background:linear-gradient(180deg,rgba(255,255,255,.08) 0,rgba(255,255,255,0) 38%%,rgba(0,0,0,0) 62%%,rgba(0,0,0,.14) 100%%),
  var(--panel-2,#0f1729);
 color:var(--text,#e6edf7);font:700 11.5px/1.1 var(--font-display,inherit);
 letter-spacing:.06em;text-transform:uppercase;cursor:pointer;
 box-shadow:inset 0 1px 0 rgba(255,255,255,.12),0 2px 0 rgba(0,0,0,.35),
  0 4px 10px rgba(0,0,0,.28);
 transition:transform .12s ease-out,box-shadow .12s ease-out,
  filter .12s ease-out}
.radai-tarefas .pipe-bt:hover:not([disabled]){filter:brightness(1.08)}
.radai-tarefas .pipe-bt:active:not([disabled]){transform:translateY(2px);
 box-shadow:inset 0 1px 0 rgba(255,255,255,.08),0 0 0 rgba(0,0,0,.35),
  0 1px 3px rgba(0,0,0,.28)}
.radai-tarefas .pipe-bt:focus-visible{outline:2px solid var(--accent,#4DA3FF);
 outline-offset:2px}
.radai-tarefas .pipe-bt.ini{
 background:linear-gradient(180deg,rgba(255,255,255,.08) 0,rgba(255,255,255,0) 38%%,rgba(0,0,0,0) 62%%,rgba(0,0,0,.14) 100%%),
  var(--ok,#12873F);color:var(--ok-txt,#fff);border-color:var(--ok,#12873F)}
.radai-tarefas .pipe-bt.pau{
 background:linear-gradient(180deg,rgba(255,255,255,.08) 0,rgba(255,255,255,0) 38%%,rgba(0,0,0,0) 62%%,rgba(0,0,0,.14) 100%%),
  var(--fundo-aviso,#1c1608);color:var(--aviso,#E8A33D);
 border-color:var(--borda-aviso,#4a3a18)}
.radai-tarefas .pipe-bt.can{
 background:linear-gradient(180deg,rgba(255,255,255,.08) 0,rgba(255,255,255,0) 38%%,rgba(0,0,0,0) 62%%,rgba(0,0,0,.14) 100%%),
  var(--fundo-perigo,#160a08);color:var(--perigo,#E96A5C);
 border-color:var(--borda-perigo,#552b23)}
.radai-tarefas .pipe-bt[disabled]{background:var(--panel,#0c1322);
 color:var(--text-dim,#72829b);border-color:var(--line,#1e293b);
 border-style:dashed;box-shadow:none;cursor:not-allowed;transform:none;
 filter:none;opacity:.7}
.radai-tarefas .pipe-est{grid-column:1 / -1;min-height:14px;
 font:400 11px/1.35 var(--font-mono,monospace);color:var(--text-dim,#72829b)}
.radai-tarefas .pipe-est:empty{display:none}
.radai-tarefas .pipe-otm{grid-column:1 / -1;border:1px solid var(--borda-aviso,#4a3a18);
 background:var(--fundo-aviso,#1c1608);border-radius:var(--r-md,6px);
 padding:8px 9px;font-size:11.5px;line-height:1.45;color:var(--text-muted,#a3b1c6)}
.radai-tarefas .pipe-otm[hidden]{display:none}
.radai-tarefas .pipe-otm b{color:var(--text,#e6edf7)}
.radai-tarefas .pipe-otm .otm-bts{display:flex;gap:6px;margin-top:7px;
 flex-wrap:wrap}
.radai-tarefas .pipe-otm button{font:600 11px/1 var(--font-display,inherit);
 padding:6px 10px;border-radius:var(--r-sm,5px);cursor:pointer;
 border:1px solid var(--line-strong,#2a3a55);background:var(--panel-2,#0f1729);
 color:var(--text,#e6edf7)}
.radai-tarefas .pipe-otm button.otm-sim{background:var(--ok,#12873F);
 border-color:var(--ok,#12873F);color:var(--ok-txt,#fff)}
@media (prefers-reduced-motion:reduce){
 .radai-tarefas .pipe-bt{transition:none}
 .radai-tarefas .pipe-bt:active:not([disabled]){transform:none}
}

.radai-tarefas .cd{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:6px;
 align-items:center;padding:7px 8px;margin-bottom:6px;border-radius:6px;
 background:var(--bg-2,#0f172a);border:1px solid var(--line,#1e293b);
 position:relative}
.radai-tarefas .cd .cd-rot{position:static;font-size:12px;color:var(--txt,#e2e8f0);
 overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.radai-tarefas .cd .cd-sub{position:static;margin:2px 0 0;font-size:10px;
 color:var(--text-muted,#a3b1c6);
 overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.radai-tarefas .cd .cd-and{position:static;margin:3px 0 0;
 font:400 10.5px/1.4 var(--font-mono,monospace);color:var(--success,#5BC57F);
 overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.radai-tarefas .cd .cd-and .rel{font-variant-numeric:tabular-nums}
.radai-tarefas .cd .bts{display:flex;gap:2px}
.radai-tarefas .cd .bts button{background:none;border:0;cursor:pointer;
 color:var(--text-muted,#a3b1c6);font-size:13px;line-height:1;padding:3px 4px;
 border-radius:4px}
.radai-tarefas .cd .bts button:hover:not(:disabled){
 background:var(--line,#1e293b);color:var(--txt,#e2e8f0)}
.radai-tarefas .cd .bts button:disabled{opacity:.25;cursor:default}
.radai-tarefas .cd .bts button.ui-mais{width:22px;height:22px;padding:0;
 display:inline-grid;place-items:center;margin-right:3px;
 border:1px solid var(--line-strong,#2a3a55);border-radius:var(--r-md,6px);
 background:var(--panel-2,#0f1729);color:var(--text-muted,#a3b1c6)}
.radai-tarefas .cd .bts button.ui-mais[aria-expanded="true"]{
 color:var(--accent,#4DA3FF);border-color:var(--accent,#4DA3FF);
 background:var(--accent-fraco,rgba(77,163,255,.14))}
.radai-tarefas .cd.rodando{border-color:var(--ok,#12873F);
 background:color-mix(in srgb,var(--ok,#12873F) 12%%,var(--bg-2,#0f172a))}
.radai-tarefas .cd.skipped{opacity:.72}
.radai-tarefas .cd.feito{opacity:.42}
.radai-tarefas .cd .tag{display:inline-block;font-size:9px;padding:1px 5px;
 border-radius:99px;letter-spacing:.06em;text-transform:uppercase;
 border:1px solid var(--line,#1e293b);color:var(--text-muted,#a3b1c6)}
.radai-tarefas .cd .tag.skipped{border-color:var(--borda-aviso,#8a5a05);
 color:var(--aviso,#E8A33D)}
.radai-tarefas .cd .tag.origem{border-color:var(--mod-bridge-fraco);
 color:var(--mod-bridge)}
.radai-tarefas .cd .tag.overnight{border-color:var(--mod-elastic-fraco);
 color:var(--mod-elastic)}
.radai-tarefas .cd.vigia{border-style:dashed}
.radai-tarefas .cd.parcial{opacity:.72}
.radai-tarefas .cd.cancelado{opacity:.6}
.radai-tarefas .cd .cd-msg{position:static;margin:3px 0 0;font-size:10px;
 line-height:1.35;color:var(--text-muted,#a3b1c6);white-space:normal;
 overflow-wrap:anywhere}
.radai-tarefas .vigia-mais{margin:2px 2px 8px;font-size:10.5px;
 color:var(--text-dim,#72829b)}
.radai-tarefas .trilho-dir .cont{font:600 10px/1 var(--font-mono,monospace);
 color:var(--accent,#4DA3FF);font-variant-numeric:tabular-nums}
.radai-tarefas .trilho-dir .cont:empty{display:none}
.radai-tarefas .fora-fila{margin:6px 8px;padding:7px 9px;border:1px solid var(--borda-aviso);
 border-radius:6px;font-size:11px;line-height:1.45;color:var(--text-muted)}
.radai-tarefas .fora-fila .ff-it{margin-bottom:4px;overflow-wrap:anywhere}
.radai-tarefas .fora-fila .ff-tag{color:var(--aviso);font-weight:600}
.radai-tarefas .fora-fila .ff-id{font-family:var(--mono,monospace)}
.radai-tarefas .fora-fila .ff-bt{margin-top:2px;font-size:11px}
.radai-tarefas .vazia{padding:14px 10px;font-size:11px;
 color:var(--text-muted,#a3b1c6);line-height:1.5}

.radai-tarefas .dobra{flex:0 0 auto;background:none;border:0;cursor:pointer;
 color:var(--text-dim,#72829b);font-size:13px;padding:0 10px}
.radai-tarefas .dobra:hover{color:var(--text,#e6edf7)}

.radai-tarefas .painel{flex:1 1 0;min-height:0;overflow-y:auto;padding:12px;
 box-sizing:border-box}
.radai-tarefas .logreg{flex:1 1 0;min-height:0;display:flex;
 flex-direction:column}
.radai-tarefas .painel[hidden]{display:none}

.radai-tarefas .trilho-dir{display:none;flex-direction:column;align-items:center;
 gap:6px;padding:10px 0}
.radai-tarefas .trilho-dir button{min-width:30px;border-radius:var(--r-md,6px);
 border:1px solid var(--line,#1e293b);background:var(--panel,#0c1322);
 color:var(--text-dim,#72829b);cursor:pointer;font-size:13px;line-height:1;
 padding:7px 4px;display:flex;flex-direction:column;align-items:center;gap:6px}
.radai-tarefas .trilho-dir .nm{writing-mode:vertical-rl;font-size:10px;
 letter-spacing:.06em;font-weight:600;text-transform:lowercase}
.radai-tarefas .trilho-dir button:hover{color:var(--accent,#4DA3FF);
 border-color:var(--accent,#4DA3FF)}
html.dir-recolhida .radai-tarefas .dir-abas,
html.dir-recolhida .radai-tarefas .fila,
html.dir-recolhida .radai-tarefas .logreg,
html.dir-recolhida .radai-tarefas .painel{display:none !important}
html.dir-recolhida .radai-tarefas .trilho-dir{display:flex}

.radai-tarefas .subt{color:var(--text-dim,#72829b);font-size:10.5px;
 margin:0 0 10px}
.radai-tarefas .tf{background:var(--panel,#0c1322);border:1px solid var(--line,#1e293b);
 border-radius:var(--r-lg,8px);padding:9px 10px;margin-bottom:8px}
.radai-tarefas .tf b{display:block;font-size:12px;font-weight:600;
 color:var(--text,#e6edf7);line-height:1.35}
.radai-tarefas .tf span{display:block;color:var(--text-muted,#a3b1c6);
 font-size:10.5px;margin-top:3px;line-height:1.4}
.radai-tarefas .tf button,.radai-tarefas .tf a.bt{display:inline-block;
 margin-top:7px;background:var(--accent,#4DA3FF);color:var(--ok-txt,#fff);border:0;
 border-radius:var(--r-sm,5px);padding:5px 10px;font-size:11px;font-weight:600;
 cursor:pointer;text-decoration:none;font-family:inherit}
.radai-tarefas .tf button:hover,.radai-tarefas .tf a.bt:hover{filter:brightness(1.1)}
.radai-tarefas .vazio{color:var(--text-dim,#72829b);font-size:11px;line-height:1.5;
 border:1px dashed var(--line,#1e293b);border-radius:var(--r-lg,8px);padding:10px}

.radai-tarefas .log{font:400 10.5px/1.75 var(--font-mono,Consolas,monospace);
 white-space:pre-wrap;word-break:break-word}
.radai-tarefas .log .l{display:block}
.radai-tarefas .log .h{color:var(--text-dim,#72829b);margin-right:6px}
.radai-tarefas .log .m{color:var(--text-muted,#a3b1c6)}
.radai-tarefas .log .l.ok .m{color:var(--success,#5BC57F)}
.radai-tarefas .log .l.erro .m{color:var(--perigo,#E96A5C)}

.radai-tarefas .tf-ic{font-style:normal;margin-right:5px;opacity:.85}
.radai-tarefas .tf.rodando{border-color:var(--borda-ok,#24422f);background:var(--fundo-ok,#0d1a12)}
.radai-tarefas .tf.rodando .tf-ic{animation:radaiTfGira 2.4s linear infinite;
 display:inline-block}
.radai-tarefas .tf.parado{border-style:dashed}
.radai-tarefas .tf.aviso{border-color:var(--borda-aviso,#4a3a18);background:var(--fundo-aviso,#1c1608)}
.radai-tarefas .tf.info{border-color:var(--line-strong,#2a3a55)}
@keyframes radaiTfGira{to{transform:rotate(360deg)}}
@media (prefers-reduced-motion:reduce){
 .radai-tarefas .tf.rodando .tf-ic{animation:none}
}
#radai_tf_fundo{display:none;position:fixed;inset:0;background:rgba(2,6,14,.78);z-index:19}
@media (max-width:1100px){
 body,html.dir-recolhida body{margin-right:0 !important}
 .radai-tarefas,html.dir-recolhida .radai-tarefas{position:static;width:auto;
  height:auto;border-left:0;border-top:1px solid var(--line,#1e293b)}
 html.dir-recolhida .radai-tarefas .painel{display:block !important}
 html.dir-recolhida .radai-tarefas .dir-abas{display:flex !important}
 html.dir-recolhida .radai-tarefas .fila:not([hidden]){display:flex !important}
 html.dir-recolhida .radai-tarefas .logreg:not([hidden]){display:flex !important}
 .radai-tarefas .fila,.radai-tarefas .logreg{flex:0 0 auto}
 .radai-tarefas .fila .corpo{flex:0 0 auto;max-height:60vh}
 .radai-tarefas .logreg .painel{flex:0 0 auto;max-height:60vh}
 .radai-tarefas .trilho-dir{display:none !important}
 .radai-tarefas .dir-abas .dobra{display:none}
}
</style>"""



_PAINEL_PENDENCIAS = u"""
 <div class="painel" id="radai_tf_pn_p"
  role="region" aria-label="o que est&aacute; rodando agora">
  <div class="subt" id="radai_tf_sub">carregando&hellip;</div>
  <div id="radai_tf_lista"></div>
 </div>"""

_ICONE_PENDENCIAS = u"""
  <button type="button" onclick="radaiTfAbrirAba('fila', true)" id="radai_tf_ic_fila"
   title="%(titulo)s" aria-label="%(titulo)s">&#9776;<span class="cont"
   id="radai_fila_cont"></span><span class="nm"
   data-radai-frase>%(titulo)s</span></button>"""

_FILA_HTML = u"""
 <section class="fila" id="radai_tf_reg_fila" role="tabpanel"
  aria-labelledby="radai_tf_ab_fila">
 <div class="pipe" role="group" aria-label="controle do processamento">
  <button type="button" class="pipe-bt ini" id="radai_pipe_ini"
    data-radai-frase>Iniciar</button>
  <button type="button" class="pipe-bt pau" id="radai_pipe_pau"
    data-radai-frase>Pausar fila</button>
  <button type="button" class="pipe-bt lim" id="radai_pipe_lim"
    data-radai-frase>Limpar fila</button>
  <button type="button" class="pipe-bt can" id="radai_pipe_can"
    data-radai-frase>Cancelar</button>
  <span class="pipe-est" id="radai_pipe_est" role="status"></span>
  <div class="pipe-otm" id="radai_pipe_otm" hidden></div>
 </div>
  <div class="notif-pede" id="radai_notif_pede" hidden>
   <span data-radai-frase>Avisar com som e notificação quando uma série terminar ou falhar? O navegador pede a permissão uma vez.</span>
   <div class="otm-bts">
    <button type="button" class="sim" id="radai_notif_sim" data-radai-frase>Permitir avisos</button>
    <button type="button" id="radai_notif_nao" data-radai-frase>Agora não</button>
   </div>
  </div>
  <div class="fora-fila" id="radai_fora_fila" role="status" hidden>
   <div id="radai_fora_fila_txt"></div>
   <button type="button" class="ff-bt" id="radai_fora_fila_bt"
     onclick="radaiForaLiberar()" data-radai-frase>Liberar</button>
  </div>
  <div class="corpo" id="radai_fila"></div>
 </section>"""

_BARRA = u"""
<aside class="radai-tarefas" data-fonte="%(fonte)s">
 <div class="dir-abas" role="tablist" aria-label="barra da direita">
  <button type="button" role="tab" class="dir-aba" id="radai_tf_ab_fila"
   data-aba="fila" aria-selected="true" aria-controls="radai_tf_reg_fila"
   ><span data-radai-frase>Fila desta esta&ccedil;&atilde;o</span>
   <span class="n" id="radai_fila_n"></span></button>
  <button type="button" role="tab" class="dir-aba" id="radai_tf_ab_log"
   data-aba="log" aria-selected="false" aria-controls="radai_tf_reg_log"
   tabindex="-1"><span class="pt" id="radai_tf_pt"></span><span
   class="ab-rot" id="radai_tf_ab_log_rot"><span
   data-radai-frase>Log</span></span></button>
  <button type="button" class="dobra" onclick="uiDireita()"
   title="recolher" aria-label="recolher a barra">&#8250;</button>
 </div>
%(fila)s%(painel_p)s
 <section class="logreg" id="radai_tf_reg_log" role="tabpanel"
  aria-labelledby="radai_tf_ab_log" hidden>
 <div class="painel" id="radai_tf_pn_l">
  <div class="log" id="radai_tf_log"></div>
 </div>
 </section>
 <div class="trilho-dir">%(icone_p)s
  <button type="button" onclick="radaiTfAbrirAba('log', true)"
   title="Log" aria-label="Log">&#8999;<span class="nm"
   data-radai-frase>Log</span></button>
 </div>
</aside>"""


def barra(com_pendencias=False):
    return _BARRA % {
        "fila": _FILA_HTML,
        "painel_p": _PAINEL_PENDENCIAS.replace(
            u'id="radai_tf_pn_p"', u'id="radai_tf_pn_p" hidden'),
        "icone_p": _ICONE_PENDENCIAS % {"titulo": u"Fila"},
        "fonte": u"atividade",
    }

_RESTO = u"""
<script>
function radaiTfEsc(s){return String(s==null?'':s).replace(/&/g,'&amp;')
 .replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}
var RADAI_FILA_TIPO = {
 overnight: {icone:'\u263E', tag:'turno',                 cls:'overnight'},
 serie:     {icone:'\u25A6', tag:'',                      cls:''}
};
var RADAI_FILA_ORIGEM = {vigia: 'Vigia', dicombridge: 'DicomBridge',
                         nidus: 'Nidus RT'};
var RADAI_FILA_TAG_DO_ESTADO = {pronto: 'feito', falhou: 'falhou',
                                cancelado: 'cancelado'};

function radaiRelogio(s){
 s = Math.max(0, Math.floor(Number(s) || 0));
 var h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), x = s % 60;
 function d2(v){ return (v < 10 ? '0' : '') + v }
 return (h ? (h + ':' + d2(m)) : String(m)) + ':' + d2(x);
}
setInterval(function(){
 var agora = Date.now();
 [].forEach.call(document.querySelectorAll('.radai-tarefas .cd-and .rel[data-t0]'),
  function(r){
   var base = Number(r.getAttribute('data-s')) || 0;
   var t0 = Number(r.getAttribute('data-t0')) || agora;
   r.textContent = radaiRelogio(base + (agora - t0) / 1000);
  });
}, 1000);

function radaiFilaAndamento(a){
 if(!a) return '';
 var h = '<div class="cd-and">';
 if(a.etapa) h += radaiTfEsc(a.etapa);
 if(a.parte) h += ' · <span data-radai-frase>parte</span> ' + radaiTfEsc(a.parte);
 if(a.segundos != null){
  h += ' · <span class="rel" data-s="' + Number(a.segundos) + '" data-t0="'
     + Date.now() + '">' + radaiRelogio(a.segundos) + '</span>';
 }
 return h + '</div>';
}

function radaiFilaFrase(pt){
 try{ return window.radaiFrase ? window.radaiFrase(pt) : pt }
 catch(e){ return pt }
}
function radaiFilaCard(c, i, n){
 var T = RADAI_FILA_TIPO[c.tipo] || RADAI_FILA_TIPO.serie;
 var A = c.acoes || {};
 var rodando = (c.estado === 'rodando');
 var fim = (c.estado === 'pronto' || c.estado === 'parcial'
            || c.estado === 'falhou' || c.estado === 'cancelado');
 var marca = rodando ? '<span class="ui-gira"></span>'
   : ((c.estado === 'pronto' || c.estado === 'parcial')
      ? '<span class="ui-feito">\u2713</span>'
      : ((c.estado === 'falhou' || c.estado === 'cancelado')
         ? '<span class="ui-feito ui-falhou">\u2715</span>' : ''));
 var sub = '';
 if(c.estado === 'pulado'){
  sub = '<span class="tag skipped" data-radai-frase>pulado</span> '
      + radaiTfEsc(c.dono || '');
 } else if(T.tag){
  sub = '<span class="tag ' + T.cls + '" data-radai-frase>' + T.tag + '</span>';
  if(c.tipo === 'overnight' && fim && c.motivo){
   sub += ' <span class="cd-motivo" title="' + radaiTfEsc(c.motivo) + '">'
        + radaiTfEsc(c.motivo) + '</span>';
  }
 } else if(fim && c.nao_contornavel){
  sub = '<span class="tag" data-radai-frase>Não contornável</span> '
      + '<span class="cd-motivo" title="' + radaiTfEsc(c.nao_contornavel) + '">'
      + radaiTfEsc(c.nao_contornavel) + '</span>';
 } else if(fim && c.faltou && c.faltou.length){
  var ftx = radaiFilaFrase('Faltou nesta série: %s').replace('%s', c.faltou.join(', '));
  sub = '<span class="tag parcial" data-radai-frase title="' + radaiTfEsc(ftx)
      + '">Parcial</span> <span class="cd-motivo" title="' + radaiTfEsc(ftx)
      + '">' + radaiTfEsc(ftx) + '</span>';
 } else if(c.estado === 'parcial'){
  sub = '<span class="tag parcial" data-radai-frase>Parcial</span>';
 } else if(fim && c.ja_concluida){
  sub = '<span class="tag" data-radai-frase>já concluída, não refeita</span>';
 } else if(fim){
  sub = '<span class="tag" data-radai-frase>'
      + radaiTfEsc(RADAI_FILA_TAG_DO_ESTADO[c.estado] || c.estado) + '</span>';
 }
 if(!sub && c.tipo === 'serie' && c.uid){
  sub = '<span class="tag">&hellip;' + radaiTfEsc(c.uid) + '</span>';
 }
 var org = RADAI_FILA_ORIGEM[c.origem];
 if(org && c.tipo === 'serie'){
  sub = '<span class="tag origem"' + (c.origem === 'vigia'
        ? ' data-radai-frase' : ' data-radai-t="1"') + '>' + org + '</span> '
      + sub;
 }
 if(fim && c.sem_estrutura && c.sem_estrutura.length){
  sub += ' <span class="cd-motivo">' + radaiTfEsc(c.sem_estrutura.join(', '))
       + ' — ' + radaiTfEsc(radaiFilaFrase('sem estrutura no campo'))
       + '</span>';
 }
 var msg = c.mensagem ? ('<div class="cd-msg">' + radaiTfEsc(c.mensagem)
                         + '</div>') : '';
 var cls = 'cd' + (rodando ? ' rodando' : '')
         + (c.estado === 'pulado' ? ' skipped' : '')
         + (fim ? ' ' + c.estado + (c.estado === 'pronto' ? ' feito' : '') : '')
         + (c.origem === 'vigia' && !fim && !rodando ? ' vigia' : '');
 var id = radaiTfEsc(c.id || '');
 return '<div class="' + cls + '" data-id="' + id + '">'
  + '<div><div class="cd-rot">' + (marca || T.icone) + ' '
  + radaiTfEsc(c.rotulo || '') + '</div>'
  + (sub ? ('<div class="cd-sub">' + sub + '</div>') : '')
  + msg
  + (rodando ? radaiFilaAndamento(c.andamento) : '') + '</div>'
  + '<div class="bts">'
  + (c.tipo === 'serie' ? ('<button type="button" class="ui-mais" onclick="radaiFilaDetalheBt(this)"'
     + ' aria-expanded="false" title="detalhes do pedido" aria-label="detalhes do pedido">'
     + ((document.getElementById('ui-ico-mais') || {}).innerHTML || '+') + '</button>') : '')
  + (A.repor ? ('<button type="button" class="fila-repor" onclick="radaiFilaReporBt(this)"'
     + ' title="pôr na fila de novo" aria-label="pôr na fila de novo">\u21BB</button>') : '')
  + '<button type="button" onclick="radaiFilaMoverBt(this,-1)"'
  + (A.subir ? '' : ' disabled')
  + ' title="subir" aria-label="subir">\u25B2</button>'
  + '<button type="button" onclick="radaiFilaMoverBt(this,1)"'
  + (A.descer ? '' : ' disabled')
  + ' title="descer" aria-label="descer">\u25BC</button>'
  + '<button type="button" onclick="radaiFilaCancelarBt(this)"'
  + (A.tirar ? '' : ' disabled')
  + ' title="tirar da fila" aria-label="tirar da fila">\u2715</button>'
  + '</div></div>';
}

var RADAI_FILA_MODO = {fast:'FAST', auto:'AUTO', perso:'PERSONALIZADO'};
function radaiFilaCardDoId(id){
 var L = window.RADAI_FILA_L || [];
 for(var k = 0; k < L.length; k++) if(L[k] && L[k].id === id) return L[k];
 return null;
}
function radaiFilaDetalheBt(bt){
 var id = radaiFilaIdDe(bt), c = id ? radaiFilaCardDoId(id) : null;
 if(!c){
  var cd = (bt && bt.closest) ? bt.closest('.cd') : null;
  var irmaos = (cd && cd.parentNode) ? [].slice.call(cd.parentNode.children)
   .filter(function(x){ return x.classList && x.classList.contains('cd') }) : [];
  c = (window.RADAI_FILA_L || [])[irmaos.indexOf(cd)] || null;
 }
 radaiFilaDetalhe(c, bt);
}
function radaiFilaDetalhe(c, bt){
 if(!c || !window.uiMorfar) return;
 var e = c.detalhe || {}, linhas = [];
 function par(rot, val){
  if(val === undefined || val === null || val === '' ) return;
  linhas.push('<dt data-radai-frase>' + rot + '</dt><dd>' + radaiTfEsc(val) + '</dd>');
 }
 par('Série', c.rotulo);
 if(c.uid) linhas.push('<dt>UID</dt><dd>\u2026' + radaiTfEsc(c.uid) + '</dd>');
 par('Modo', RADAI_FILA_MODO[e.modo] || e.modo);
 par('Modalidade', e.modalidade);
 par('Cortes', e.cortes);
 par('Espessura', e.espessura != null
  ? Number(e.espessura).toFixed(2).replace('.', ',') + ' mm' : null);
 par('Descrição', e.descricao);
 par('Protocolos', (e.protocolos || []).join(', '));
 par('Tasks', (e.tasks || []).join(', '));
 par('Estação', c.dono);
 window.uiMorfar(bt, {html: '<dl>' + linhas.join('') + '</dl>', largura: 300});
}

var RADAI_FILA_IDS = null;
function radaiFilaChegouDoBridge(L){
 var agora = {}, novo = false;
 L.forEach(function(c){
  if(!c || !c.id) return;
  agora[c.id] = 1;
  if(RADAI_FILA_IDS !== null && !RADAI_FILA_IDS[c.id]
     && c.origem === 'dicombridge') novo = true;
 });
 RADAI_FILA_IDS = agora;
 return novo;
}
function radaiFilaPintar(d){
 try{ radaiAvisosDaFila(d) }catch(e){}
 var alvo = document.getElementById('radai_fila');
 if(!alvo) return;                      /* tela sem a fila: /config */
 alvo.dataset.javeio = '1';
 var L = (d && d.cards) || [];
 window.RADAI_FILA_L = L;
 window.RADAI_FILA_D = d || {};
 var n = document.getElementById('radai_fila_n');
 var r = (d && d.resumo) || {};
 var esp = (r.esperando || 0) + (r.rodando || 0);
 if(n){
  n.textContent = L.length ? ((r.esperando || 0) + '/' + L.length) : '';
  n.className = 'n' + (L.length ? '' : ' zero');
  if(L.length && n.dataset.esp !== undefined
     && Number(n.dataset.esp) < (r.esperando || 0)){
   n.classList.remove('ui-badge','subiu'); void n.offsetWidth;
   n.classList.add('ui-badge','subiu');
   setTimeout(function(){ n.classList.remove('ui-badge','subiu') }, 700);
  }
  n.dataset.esp = String(r.esperando || 0);
 }
 var cont = document.getElementById('radai_fila_cont');
 if(cont) cont.textContent = esp ? String(esp) : '';
 try{ if(radaiFilaChegouDoBridge(L)) radaiFilaAbrirBarra() }catch(e){}
 var aberto = alvo.querySelector('.ui-mais[aria-expanded="true"]');
 var abertoId = aberto ? radaiFilaIdDe(aberto) : '';
 if(!L.length){
  radaiPipePintar(d);
  alvo.innerHTML = '<div class="vazia" data-radai-frase>A fila est\u00e1 vazia. Ela se enche quando voc\u00ea pede s\u00e9ries em &laquo;Rodar agora&raquo;, ou quando o vigia encontra exames novos.</div>';
  radaiFilaManterDetalhe(alvo, aberto, abertoId);
  radaiFilaTraduzir();
  return;
 }
 var h = '', vigiaNaTela = 0;
 for(var i=0;i<L.length;i++){
  h += radaiFilaCard(L[i], i, L.length);
  if(L[i].origem === 'vigia' && L[i].estado === 'esperando') vigiaNaTela++;
 }
 var resto = (r.vigia_na_fila || 0) - vigiaNaTela;
 if(resto > 0){
  h += '<div class="vigia-mais">+' + resto + ' <span data-radai-frase>na fila do vigia</span></div>';
 }
 alvo.innerHTML = h;
 radaiFilaManterDetalhe(alvo, aberto, abertoId);
 radaiPipePintar(d);
 radaiFilaTraduzir();
}

// GUARDA: a repintura recria os cartoes; o botao + aberto volta ao lugar (o painel do detalhe aponta para ele), e some com o cartao que saiu.
function radaiFilaManterDetalhe(alvo, aberto, id){
 if(!aberto) return;
 var novo = null;
 if(id){
  var bts = alvo.querySelectorAll('.cd .ui-mais');
  for(var k = 0; k < bts.length; k++)
   if(radaiFilaIdDe(bts[k]) === id){ novo = bts[k]; break }
 }
 if(novo && novo.parentNode){ novo.parentNode.replaceChild(aberto, novo); return }
 try{ if(window.uiMorfar) window.uiMorfar(aberto) }catch(e){}
}

function radaiFilaTraduzir(){
 try{ if(window.radaiRetraduzir) window.radaiRetraduzir() }catch(e){}
}

var RADAI_PIPE_FRASE = '';
function radaiPipePintar(d){
 var ini = document.getElementById('radai_pipe_ini');
 var pau = document.getElementById('radai_pipe_pau');
 var lim = document.getElementById('radai_pipe_lim');
 var can = document.getElementById('radai_pipe_can');
 var est = document.getElementById('radai_pipe_est');
 if(!ini || !pau) return;                 /* tela sem a barra: /config */
 var r = (d && d.resumo) || {};
 var lote = (d && d.lote) || null;
 var vez = (d && d.vez) || {};
 var vigia = (vez.dono === 'vigia');
 var rodando = lote ? !!lote.rodando : ((r.rodando || 0) > 0);
 var espera  = (r.manuais_esperando != null) ? r.manuais_esperando
                                             : (r.esperando || 0);
 var cards   = (r.total || 0);
 ini.disabled = rodando || espera === 0;
 pau.disabled = !(rodando || vigia) || !!(lote && lote.pausa_pedida);
 if(lim) lim.disabled = (cards - (r.rodando || 0) - (r.esperando || 0)
                         - (r.pulado || 0)) <= 0;
 if(can) can.disabled = !(rodando || vigia) || !!(lote && lote.cancelando);
 var txt = (!rodando && !vigia) ? RADAI_PIPE_FRASE
   : ((lote && lote.cancelando) ? 'cancelando a série atual'
   : ((lote && lote.pausa_pedida)
      ? 'pausa pedida: a série atual termina e a próxima não começa'
      : ((rodando && vigia)
         ? 'a série do vigia em curso termina primeiro; as pedidas à mão começam em seguida'
         : 'processando')));
 if(est){
  if(typeof uiTexto === 'function') uiTexto(est, txt);
  else est.textContent = txt;
 }
}

function radaiPipePerguntar(o){
 if(window.uiPainel) return window.uiPainel(o);
 var ok = confirm([o.titulo, o.corpo].join(String.fromCharCode(10, 10)));
 try{ if(ok && o.aoSim) o.aoSim() }catch(e){}
 return null;
}

function radaiPipe(acao){
 if(acao === 'iniciar' && typeof radaiRevAbrir === 'function'){
  fetch('/api/pipeline/revisao')
   .then(function(r){ return r.json() })
   .then(function(d){
    radaiRevAbrir((d && d.revisao) || null,
                  function(){ radaiPipeMandar('iniciar') });
   })
   /* GUARDA: sem a conferencia o dialogo abre so com a tag da regra 1; a
      fila so comeca no botao dele, e a rede fora do ar nao vira portao. */
   .catch(function(){
    radaiRevAbrir(null, function(){ radaiPipeMandar('iniciar') });
   });
  return;
 }
 if(acao === 'cancelar'){
  var D = window.RADAI_FILA_D || {};
  var doVigia = ((D.vez || {}).dono === 'vigia');
  var loteEspera = !!((D.lote || {}).rodando);
  if(doVigia){
   radaiPipePerguntar({
    titulo: 'Interromper a série do vigia',
    corpo: loteEspera
     ? 'A série que o vigia está segmentando é interrompida e o que ela já fez é descartado; ela volta para a fila do vigia, sem contar como falha. As séries pedidas à mão começam em seguida.'
     : 'A série que o vigia está segmentando é interrompida e o que ela já fez é descartado; ela volta para a fila do vigia, sem contar como falha, e o vigia fica pausado até o Iniciar.',
    ok: 'Interromper a série', cancelar: 'Continuar rodando', perigo: true,
    aoSim: function(){ radaiPipeMandar('cancelar') }
   });
   return;
  }
  radaiPipePerguntar({
   titulo: 'Cancelar a série em curso',
   corpo: 'A segmentação que está rodando é interrompida e o que ela já fez é descartado. As séries que esperam continuam na fila, e o Iniciar as retoma.',
   ok: 'Cancelar a série', cancelar: 'Continuar rodando', perigo: true,
   aoSim: function(){ radaiPipeMandar('cancelar') }
  });
  return;
 }
 if(acao === 'limpar'){
  radaiFilaLimpar();
  return;
 }
 radaiPipeMandar(acao);
}

function radaiPipeMandar(acao){
 var bts = ['radai_pipe_ini','radai_pipe_pau','radai_pipe_lim','radai_pipe_can'];
 bts.forEach(function(id){ var b = document.getElementById(id);
                           if(b) b.disabled = true });
 var rota = (acao === 'iniciar') ? '/api/pipeline/iniciar'
          : (acao === 'cancelar') ? '/api/pipeline/cancelar'
          : (acao === 'limpar') ? '/api/fila/limpar'
          : '/api/pipeline/pausar';
 fetch(rota, {method:'POST'})
  .then(function(r){ return r.json() })
  .then(function(d){
   if(d && d.erro){
    var est = document.getElementById('radai_pipe_est');
    if(est){
     if(typeof uiTexto === 'function') uiTexto(est, d.erro.slice(0, 60));
     else est.textContent = d.erro.slice(0, 60);
    }
   }
   if(acao === 'iniciar' && d && d.ok) radaiOtimSugerir();
   if(typeof radaiFilaCarregar === 'function') radaiFilaCarregar();
  })
  .catch(function(){ if(typeof radaiFilaCarregar === 'function') radaiFilaCarregar() });
}

function radaiFilaFraseDoLimpar(tirados, soltas){
 var t = (tirados === 1) ? radaiFilaFrase('%d cartão tirado')
                         : radaiFilaFrase('%d cartões tirados');
 var f = t.replace('%d', String(tirados));
 if(soltas){
  f += ', ' + ((soltas === 1) ? radaiFilaFrase('%d trava solta')
                              : radaiFilaFrase('%d travas soltas'))
          .replace('%d', String(soltas));
 }
 return f;
}
function radaiFilaLimparMostrar(tirados, soltas){
 RADAI_PIPE_FRASE = radaiFilaFraseDoLimpar(tirados, soltas);
 var est = document.getElementById('radai_pipe_est');
 if(est){
  if(typeof uiTexto === 'function') uiTexto(est, RADAI_PIPE_FRASE);
  else est.textContent = RADAI_PIPE_FRASE;
 }
 setTimeout(function(){ RADAI_PIPE_FRASE = '' }, 15000);
}
function radaiFilaLimpar(){
 var lim = document.getElementById('radai_pipe_lim');
 if(lim) lim.disabled = true;
 function mandar(comFalhas){
  return fetch('/api/fila/limpar', {method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({com_falhas: !!comFalhas})})
   .then(function(r){ return r.json() });
 }
 mandar(false).then(function(d){
  radaiFilaPintar(d);
  var tirados = Number(d.tirados || 0), soltas = Number(d.travas_soltas || 0);
  var falhas = Number(d.falhas_restantes || 0);
  var parciais = Number(d.parciais_restantes || 0);
  if(falhas > 0){
   radaiPipePerguntar({
    titulo: parciais ? 'Tirar também o que não terminou inteiro?'
                     : 'Tirar também o que falhou?',
    corpo: parciais
     ? radaiFilaFrase('%d cartão(ões) falharam, foram cancelados ou saíram parciais. Tirados, eles somem da fila, e com eles o aviso do que faltou na série.').replace('%d', String(falhas))
     : radaiFilaFrase('%d cartão(ões) falharam ou foram cancelados. Tirados, eles somem da fila; para refazer, use «pôr na fila de novo» antes.').replace('%d', String(falhas)),
    ok: 'Tirar também', cancelar: 'Deixar na fila', perigo: true,
    aoSim: function(){
     mandar(true).then(function(d2){
      radaiFilaPintar(d2);
      radaiFilaLimparMostrar(tirados + Number(d2.tirados || 0),
                             soltas + Number(d2.travas_soltas || 0));
     }).catch(function(){ radaiFilaCarregar() });
    },
    aoNao: function(){ radaiFilaLimparMostrar(tirados, soltas) }
   });
   return;
  }
  radaiFilaLimparMostrar(tirados, soltas);
 }).catch(function(){ radaiFilaCarregar() });
}

var RADAI_PIPE_ACAO = {radai_pipe_ini:'iniciar', radai_pipe_pau:'pausar',
                       radai_pipe_lim:'limpar', radai_pipe_can:'cancelar'};
document.addEventListener('click', function(ev){
 var b = ev.target && ev.target.closest
         && ev.target.closest('#radai_pipe_ini,#radai_pipe_pau,#radai_pipe_lim,#radai_pipe_can');
 if(!b || b.disabled) return;
 radaiPipe(RADAI_PIPE_ACAO[b.id]);
});

function radaiOtimSugerir(){
 var cx = document.getElementById('radai_pipe_otm');
 if(!cx) return;
 fetch('/api/lote/otimizacao').then(function(r){ return r.json() })
 .then(function(d){
  if(!d || d.erro || d.turno_ativo){ cx.hidden = true; return }
  var h = '<b data-radai-frase>A estação não está otimizada para a fila.</b>';
  var placa = (d.placa || []).map(function(p){
   return radaiTfEsc(p.nome) + (p.mb != null ? (' (' + p.mb + ' MB)') : '');
  }).join(', ');
  if(placa){
   h += '<div><span data-radai-frase>Na placa de vídeo agora:</span> '
      + placa + '</div>';
  } else if(d.placa_erro){
   h += '<div><span data-radai-frase>A placa de vídeo não foi lida:</span> '
      + radaiTfEsc(String(d.placa_erro).slice(0, 90)) + '</div>';
  }
  if(d.protegidos_na_placa){
   h += '<div><b>' + Number(d.protegidos_na_placa) + '</b> '
      + '<span data-radai-frase>programa(s) clínico(s) protegido(s) também usam a placa, e nunca são fechados.</span></div>';
  }
  if((d.servicos || []).length){
   h += '<div><span data-radai-frase>Serviços que a otimização pausa:</span> '
      + (d.servicos || []).map(radaiTfEsc).join(', ') + '</div>';
  }
  h += '<div class="otm-bts">'
     + '<button type="button" class="otm-sim" onclick="radaiOtimizar(true)" data-radai-frase>Otimizar a estação</button>'
     + '<button type="button" onclick="radaiOtimFechar()" data-radai-frase>Agora não</button>'
     + '</div>';
  if(typeof uiHTML === 'function') uiHTML(cx, h); else cx.innerHTML = h;
  cx.hidden = false;
  try{ if(window.radaiRetraduzir) window.radaiRetraduzir() }catch(e){}
 }).catch(function(){ cx.hidden = true });
}
function radaiOtimFechar(){
 var cx = document.getElementById('radai_pipe_otm'); if(cx) cx.hidden = true;
}
function radaiOtimizar(ligar){
 var cx = document.getElementById('radai_pipe_otm');
 fetch('/api/lote/otimizar', {method:'POST',
   headers:{'Content-Type':'application/json'},
   body:JSON.stringify({ligar: !!ligar})})
 .then(function(r){ return r.json() })
 .then(function(d){
  if(!cx) return;
  var h;
  if(d && d.turno_ativo){
   h = '<b>' + Number(d.n_pausados || 0) + '</b> '
     + '<span data-radai-frase>serviço(s) pausado(s). Eles voltam quando a estação for restaurada.</span>'
     + '<div class="otm-bts"><button type="button" onclick="radaiOtimizar(false)" data-radai-frase>Restaurar a estação</button>'
     + '<button type="button" onclick="radaiOtimFechar()" data-radai-frase>Fechar</button></div>';
  } else if(d && d.ok){
   h = '<span data-radai-frase>Estação restaurada: os serviços pausados voltaram.</span>'
     + '<div class="otm-bts"><button type="button" onclick="radaiOtimFechar()" data-radai-frase>Fechar</button></div>';
  } else {
   h = radaiTfEsc('ERRO: ' + ((d && (d.erro || d.msg)) || ''));
  }
  if(typeof uiHTML === 'function') uiHTML(cx, h); else cx.innerHTML = h;
  cx.hidden = false;
  try{ if(window.radaiRetraduzir) window.radaiRetraduzir() }catch(e){}
 }).catch(function(e){ if(cx){ cx.textContent = 'ERRO: ' + e; cx.hidden = false } });
}

function radaiForaDaFila(){
 var cx = document.getElementById('radai_fora_fila');
 var tx = document.getElementById('radai_fora_fila_txt');
 if(!cx || !tx) return;
 fetch('/api/fora_da_fila').then(function(r){return r.json()}).then(function(d){
  var h = '';
  (d.em_espera || []).forEach(function(g){
   h += '<div class="ff-it"><span class="ff-tag">'
      + radaiTfEsc(radaiFilaFrase('em espera: a mesma falha em %d séries')
                   .replace('%d', String(g.series || 0)))
      + '</span> <span>' + radaiTfEsc(g.frase || '') + '</span></div>';
  });
  var nc = d.nao_contornaveis || [];
  nc.forEach(function(x){
   h += '<div class="ff-it"><span class="ff-tag">'
      + radaiTfEsc(radaiFilaFrase('Não contornável')) + '</span> '
      + '<span class="ff-id">&hellip;' + radaiTfEsc(x.uid8 || '')
      + (x.pid ? ' · ' + radaiTfEsc(x.pid) : '') + '</span> '
      + '<span>' + radaiTfEsc(x.motivo || '') + '</span></div>';
  });
  if((d.n_nao_contornaveis || 0) > nc.length){
   h += '<div class="ff-it">+' + ((d.n_nao_contornaveis || 0) - nc.length) + '</div>';
  }
  cx.hidden = !h;
  if(window.uiHTML) window.uiHTML(tx, h);
  else tx.innerHTML = h;
  radaiTfPontoFila(!!h);
 }).catch(function(){});
}
// GUARDA: serie fora da fila com a aba escondida acende o ponto.
var RADAI_TF_FORA = false, RADAI_TF_FORA_ACESO = {ab: false, ic: false};
function radaiTfRecolhida(){
 var c = document.documentElement.classList;
 // GUARDA: a barra que anima para fechar ja conta como recolhida; o ponto vai para o icone antes do fim da animacao.
 return c.contains('dir-recolhida') || c.contains('dir-fechando');
}
function radaiTfPontoFila(tem){
 if(tem !== undefined) RADAI_TF_FORA = !!tem;
 var recolhida = radaiTfRecolhida();
 var naAba = RADAI_TF_FORA && (recolhida || RADAI_TF_ABA !== 'fila');
 var ic = document.getElementById('radai_tf_ic_fila');
 var ab = document.getElementById('radai_tf_ab_fila');
 if(ab){
  if(naAba) ab.setAttribute('aria-label', 'Fila desta estação — série fora da fila');
  else ab.removeAttribute('aria-label');
 }
 var quer = {ab: naAba && !recolhida, ic: naAba && recolhida};
 if(window.uiPonto){
  if(ab && quer.ab !== RADAI_TF_FORA_ACESO.ab) window.uiPonto(ab, quer.ab);
  if(ic && quer.ic !== RADAI_TF_FORA_ACESO.ic) window.uiPonto(ic, quer.ic);
 }
 RADAI_TF_FORA_ACESO = quer;
 try{ if(naAba && window.radaiRetraduzir) window.radaiRetraduzir() }catch(e){}
}
function radaiForaLiberar(){
 var bt = document.getElementById('radai_fora_fila_bt');
 if(bt) bt.disabled = true;
 fetch('/api/liberar_falhas', {method:'POST'}).then(function(){
  if(bt) bt.disabled = false; radaiForaDaFila();
 }).catch(function(){ if(bt) bt.disabled = false; });
}
function radaiFilaCarregar(){
 var alvo = document.getElementById('radai_fila');
 if(!alvo) return;
 radaiForaDaFila();
 if(!alvo.dataset.javeio && !alvo.innerHTML.trim()){
  alvo.innerHTML = '<div class="ui-esqueleto ui-esq-l"></div>'
   + '<div class="ui-esqueleto ui-esq-l"></div>'
   + '<div class="ui-esqueleto ui-esq-l"></div>';
 }
 fetch('/api/fila').then(function(r){return r.json()})
  .then(radaiFilaPintar)
  .catch(function(){});
}

function radaiFilaMover(id,d){
 fetch('/api/fila/mover',{method:'POST',
   headers:{'Content-Type':'application/json'},
   body:JSON.stringify({id:id,d:d})})
  .then(function(r){return r.json()}).then(radaiFilaPintar).catch(function(){});
}

function radaiFilaCancelar(id){
 fetch('/api/fila/cancelar',{method:'POST',
   headers:{'Content-Type':'application/json'},
   body:JSON.stringify({id:id})})
  .then(function(r){return r.json()}).then(radaiFilaPintar).catch(function(){});
}

function radaiFilaRepor(id){
 fetch('/api/fila/repor',{method:'POST',
   headers:{'Content-Type':'application/json'},
   body:JSON.stringify({id:id})})
  .then(function(r){return r.json()}).then(radaiFilaPintar).catch(function(){});
}

function radaiFilaIdDe(bt){
 var c = (bt && bt.closest) ? bt.closest('.cd') : null;
 return c ? (c.getAttribute('data-id') || '') : '';
}
function radaiFilaMoverBt(bt, d){ radaiFilaMover(radaiFilaIdDe(bt), d) }
function radaiFilaCancelarBt(bt){ radaiFilaCancelar(radaiFilaIdDe(bt)) }
function radaiFilaReporBt(bt){ radaiFilaRepor(radaiFilaIdDe(bt)) }

function radaiFilaAbrirBarra(){
 try{ if(window.uiDireita) window.uiDireita('0') }catch(e){}
 try{ radaiTfAba('fila') }catch(e){}
 try{ radaiTfPontoFila() }catch(e){}
 return true;
}
window.radaiFilaAbrir = function(){
 radaiFilaAbrirBarra();
 radaiFilaCarregar();
 return true;
};

function radaiTfFonte(){
 var a = document.querySelector('.radai-tarefas');
 return (a && a.getAttribute('data-fonte')) || 'atividade';
}

function radaiTfCarregar(){
 radaiFilaCarregar();
 var fonte = radaiTfFonte();
 fetch('/api/atividade').then(function(r){return r.json()}).then(function(d){
  var L=d.tarefas||[], alvo=document.getElementById('radai_tf_lista');
  uiTexto(document.getElementById('radai_tf_sub'),
    L.length ? 'nesta estação agora' : 'nada rodando nesta estação');
  var c = document.getElementById('radai_tf_cont');
  if(c){ c.textContent = String(L.length);
         c.className = 'cont' + (L.length ? '' : ' zero'); }
  if(!L.length){ uiHTML(alvo, '<div class="vazio" data-radai-frase>'
    + 'Nada rodando nesta estação. Quando um lote ou o vigia estiverem trabalhando, eles aparecem aqui.'
    + '</div>'); return }
  alvo.innerHTML=L.map(function(t){
   var bt = '';
   if(t.href) bt = '<a class="bt" href="'+radaiTfEsc(t.href)+'">'
     +radaiTfEsc(t.botao || 'Abrir')+'</a>';
   var ico = t.icone ? ('<i class="tf-ic">'+radaiTfEsc(t.icone)+'</i> ') : '';
   return '<div class="tf '+radaiTfEsc(t.tipo)+'">'+ico+'<b>'
     +radaiTfEsc(t.titulo)+'</b>'
     +'<span>'+radaiTfEsc(t.detalhe)+'</span>'+bt+'</div>'}).join('');
 }).catch(function(){
  uiTexto(document.getElementById('radai_tf_sub'), '—')})}

var RADAI_TF_ABA = 'fila';
var RADAI_TF_ABAS = {fila: ['radai_tf_ab_fila', 'radai_tf_reg_fila'],
                     log: ['radai_tf_ab_log', 'radai_tf_reg_log']};
function radaiTfAba(qual){
 if(qual === 'l') qual = 'log';
 if(qual === 'p') qual = 'fila';
 if(!RADAI_TF_ABAS[qual]) return false;
 RADAI_TF_ABA = qual;
 for(var k in RADAI_TF_ABAS){
  var b = document.getElementById(RADAI_TF_ABAS[k][0]);
  var r = document.getElementById(RADAI_TF_ABAS[k][1]);
  var sel = (k === qual);
  if(b){ b.setAttribute('aria-selected', sel ? 'true' : 'false');
         b.tabIndex = sel ? 0 : -1; }
  if(r) r.hidden = !sel;
 }
 radaiTfPontoFila();
 if(qual === 'log'){
  radaiTfPontoLog(false);
  var pn = document.getElementById('radai_tf_pn_l');
  if(pn && RADAI_TF_LOG_FIM) pn.scrollTop = pn.scrollHeight;
 }
 return true;
}
function radaiTfAbrirAba(qual, deMao){
 try{ if(window.uiDireita) window.uiDireita('0', !!deMao) }catch(e){}
 radaiTfAba(qual);
 if(qual === 'log') radaiTfLog();
}
document.addEventListener('radai:dir', function(){
 try{ radaiTfPontoFila() }catch(e){}
});
document.addEventListener('click', function(ev){
 var a = ev.target && ev.target.closest && ev.target.closest('.dir-aba[data-aba]');
 if(!a) return;
 radaiTfAba(a.getAttribute('data-aba'));
 if(a.getAttribute('data-aba') === 'log') radaiTfLog();
});
document.addEventListener('keydown', function(ev){
 var a = ev.target && ev.target.closest && ev.target.closest('.dir-aba[data-aba]');
 if(!a || (ev.key !== 'ArrowLeft' && ev.key !== 'ArrowRight')) return;
 ev.preventDefault();
 var outra = (a.getAttribute('data-aba') === 'fila') ? 'log' : 'fila';
 radaiTfAba(outra);
 var b = document.getElementById(RADAI_TF_ABAS[outra][0]);
 if(b) b.focus();
});

var RADAI_TF_LOG_PRIMEIRA = true;
function radaiTfPontoLog(ligado){
 var a = document.getElementById('radai_tf_ab_log_rot');
 if(!a) return;
 var ab = document.getElementById('radai_tf_ab_log');
 if(ab){
  if(ligado) ab.setAttribute('aria-label', 'Log — erro novo');
  else ab.removeAttribute('aria-label');
  try{ if(ligado && window.radaiRetraduzir) window.radaiRetraduzir() }catch(e){}
 }
 if(window.uiPonto){ window.uiPonto(a, !!ligado); return }
 a.classList.toggle('ui-ponto-alvo', !!ligado);
}

var RADAI_TF_LOG_N = 0, RADAI_TF_LOG_T = null, RADAI_TF_LOG_FIM = true;
var RADAI_TF_LOG_VOO = false;
function radaiTfLogRecebeu(d){
 var cx = document.getElementById('radai_tf_log');
 var pn = document.getElementById('radai_tf_pn_l');
 var L = (d && d.linhas) || [];
 if(cx && L.length){
  var h = L.map(function(x){
   var n = (x.nivel === 'ok' || x.nivel === 'erro') ? (' ' + x.nivel) : '';
   return '<span class="l' + n + '"><span class="h">' + radaiTfEsc(x.t)
    + '</span><span class="m">' + radaiTfEsc(x.txt) + '</span></span>';
  }).join('');
  cx.insertAdjacentHTML('beforeend', h);
  if(pn && RADAI_TF_LOG_FIM) pn.scrollTop = pn.scrollHeight;
 }
 var erro = L.some(function(x){ return x.nivel === 'erro' });
 if(erro && !RADAI_TF_LOG_PRIMEIRA && RADAI_TF_ABA !== 'log') radaiTfPontoLog(true);
 RADAI_TF_LOG_PRIMEIRA = false;
 if(d && typeof d.proximo === 'number') RADAI_TF_LOG_N = d.proximo;
 var pt = document.getElementById('radai_tf_pt');
 if(pt && d){
  pt.className = 'pt ' + (d.estado || '');
  var PT_FRASE = {ok: 'o vigia está rodando', parado: 'o vigia está pausado',
                  erro: 'o vigia parou com erro'};
  var fr = PT_FRASE[d.estado || ''];
  if(fr){
   if(pt.getAttribute('data-pt') !== d.estado){
    pt.setAttribute('data-pt', d.estado);
    pt.setAttribute('role', 'img');
    pt.setAttribute('title', fr);
    pt.setAttribute('aria-label', fr);
   }
  } else if(pt.hasAttribute('data-pt')){
   pt.removeAttribute('data-pt'); pt.removeAttribute('role');
   pt.removeAttribute('title'); pt.removeAttribute('aria-label');
  }
 }
}
function radaiTfLog(){
 if(RADAI_TF_LOG_VOO) return;
 var cx = document.getElementById('radai_tf_log');
 if(!cx) return;
 var pn = document.getElementById('radai_tf_pn_l');
 if(!pn) return;
 if(document.documentElement.classList.contains('dir-recolhida')){
  if(RADAI_TF_LOG_T) clearTimeout(RADAI_TF_LOG_T);
  RADAI_TF_LOG_T = setTimeout(radaiTfLog, 3000);
  return;
 }
 RADAI_TF_LOG_VOO = true;
 fetch('/api/log?desde=' + RADAI_TF_LOG_N).then(function(r){ return r.json() })
 .then(radaiTfLogRecebeu).catch(function(){})
 .then(function(){
  RADAI_TF_LOG_VOO = false;
  if(RADAI_TF_LOG_T) clearTimeout(RADAI_TF_LOG_T);
  RADAI_TF_LOG_T = setTimeout(radaiTfLog, 3000);
 });
}
function radaiAbrirLog(){
 try{
  RADAI_TF_LOG_FIM = true;
  radaiTfAbrirAba('log');
  var pn = document.getElementById('radai_tf_pn_l');
  if(pn) pn.scrollTop = pn.scrollHeight;
 }catch(e){}
}
window.radaiAbrirLog = radaiAbrirLog;
document.addEventListener('DOMContentLoaded', function(){
 try{
  var pn = document.getElementById('radai_tf_pn_l');
  if(pn) pn.addEventListener('scroll', function(){
   if(pn.clientHeight === 0) return;
   RADAI_TF_LOG_FIM = (pn.scrollHeight - pn.scrollTop - pn.clientHeight) < 24;
  });
  radaiTfLog();
  radaiAvisosPedir();
 }catch(e){}
});

var RADAI_AVISO_ANTES = null;
var RADAI_AVISO_FINAIS = {pronto: 'ok', parcial: 'ok', falhou: 'erro'};
function radaiAvisosDaFila(d){
 var L = (d && d.cards) || [], agora = {}, uids = {};
 L.forEach(function(c){
  if(c && c.tipo === 'serie' && (c.id || c.uid)){
   var k = c.id || c.uid;
   agora[k] = c.ja_concluida ? '' : (c.estado || '');
   uids[k] = c.uid || '';
  }
 });
 if(RADAI_AVISO_ANTES !== null){
  Object.keys(agora).forEach(function(k){
   var tipo = RADAI_AVISO_FINAIS[agora[k]];
   if(!tipo || RADAI_AVISO_ANTES[k] === agora[k]) return;
   var u = uids[k];
   radaiAvisar(tipo, u);
  });
 }
 RADAI_AVISO_ANTES = agora;
}
function radaiFraseNaLingua(frase){
 try{
  var s = document.createElement('span');
  s.setAttribute('data-radai-frase', '');
  s.style.cssText = 'position:absolute;left:-9999px;top:0';
  s.textContent = frase;
  document.body.appendChild(s);
  if(window.radaiRetraduzir) window.radaiRetraduzir();
  var t = s.textContent;
  s.parentNode.removeChild(s);
  return t || frase;
 }catch(e){ return frase }
}
function radaiAvisar(tipo, uid){
 var k = 'radai_aviso_' + uid + '_' + tipo;
 try{
  var t = Number(localStorage.getItem(k)) || 0;
  if(Date.now() - t < 120000) return;
  localStorage.setItem(k, String(Date.now()));
 }catch(e){}
 radaiSom(tipo);
 if(tipo === 'erro' && RADAI_TF_ABA !== 'log') radaiTfPontoLog(true);
 try{
  if(!window.Notification || Notification.permission !== 'granted') return;
  var frase = (tipo === 'ok')
    ? radaiFraseNaLingua('todas as gravações feitas — pronta para o TPS')
    : radaiFraseNaLingua('a série falhou — o motivo está na aba Log');
  new Notification('Radioterapia.AI', {body: '…' + uid + ' · ' + frase, tag: k});
 }catch(e){}
}
var RADAI_AUDIO = null;
function radaiAudio(){
 try{
  if(!RADAI_AUDIO){
   var C = window.AudioContext || window.webkitAudioContext;
   if(!C) return null;
   RADAI_AUDIO = new C();
  }
  if(RADAI_AUDIO.state === 'suspended' && RADAI_AUDIO.resume) RADAI_AUDIO.resume();
  return RADAI_AUDIO;
 }catch(e){ return null }
}
['pointerdown', 'keydown'].forEach(function(ev){
 document.addEventListener(ev, function(){ radaiAudio() },
                           {once: true, capture: true});
});
var RADAI_SOM_TOCOU = 0;
function radaiSom(tipo){
 var a = radaiAudio();
 if(!a || a.state !== 'running') return false;
 var notas = (tipo === 'ok') ? [660, 880] : [440, 294];
 var t0 = a.currentTime + 0.02;
 notas.forEach(function(f, k){
  var o = a.createOscillator(), g = a.createGain();
  o.type = 'sine'; o.frequency.value = f;
  var ini = t0 + k * 0.17;
  g.gain.setValueAtTime(0.0001, ini);
  g.gain.exponentialRampToValueAtTime(0.16, ini + 0.02);
  g.gain.exponentialRampToValueAtTime(0.0001, ini + 0.15);
  o.connect(g); g.connect(a.destination);
  o.start(ini); o.stop(ini + 0.17);
 });
 RADAI_SOM_TOCOU++;
 return true;
}
function radaiAvisosPedir(){
 var cx = document.getElementById('radai_notif_pede');
 if(!cx) return;
 var ja = false;
 try{ ja = !!localStorage.getItem('radai_avisos_perguntado') }catch(e){}
 cx.hidden = !(window.Notification && Notification.permission === 'default' && !ja);
}
function radaiAvisosResponder(sim){
 try{ localStorage.setItem('radai_avisos_perguntado', sim ? 'sim' : 'nao') }catch(e){}
 var cx = document.getElementById('radai_notif_pede');
 if(cx) cx.hidden = true;
 radaiAudio();
 if(sim && window.Notification && Notification.requestPermission){
  try{ Notification.requestPermission() }catch(e){}
 }
}
document.addEventListener('click', function(ev){
 var b = ev.target && ev.target.closest
         && ev.target.closest('#radai_notif_sim,#radai_notif_nao');
 if(b) radaiAvisosResponder(b.id === 'radai_notif_sim');
});

document.addEventListener('DOMContentLoaded', function(){
 try{ radaiTfPontoFila() }catch(e){}
});

radaiTfCarregar(); setInterval(radaiTfCarregar, 15000);
</script>"""


TELAS_QUE_ABREM_SOZINHAS = ("lote", "ver")


def folha():
    return CSS % {"w": LARGURA, "r": RECOLHIDA, "curso": LARGURA // 2}


def _resto():
    return _RESTO


HTML = barra() + _resto()


def _tela_do_corpo(pagina):
    import re
    m = re.search(r"<body\b[^>]*?\sdata-tela=\"([^\"]*)\"", pagina, re.I)
    return m.group(1) if m else u""


def marcar_html(pagina, tela=u""):
    import re
    if not pagina:
        return pagina
    sozinha = (tela or _tela_do_corpo(pagina)) in TELAS_QUE_ABREM_SOZINHAS
    marca = u' data-dir-sozinha="%s"' % (u"1" if sozinha else u"0")
    m = re.search(r"<html(?=[\s>])", pagina, re.I)
    if not m:
        h = re.search(r"<head(?=[\s>])", pagina, re.I)
        if not h:
            return pagina
        return (pagina[:h.start()] + u'<html class="dir-recolhida"%s>' % marca
                + pagina[h.start():])
    fim = pagina.find(u">", m.end())
    if fim < 0:
        return pagina
    tag = pagina[m.start():fim]
    if u"data-dir-sozinha=" in tag:
        return pagina
    c = re.search(r"\sclass\s*=\s*([\"'])", tag, re.I)
    if c:
        i = m.start() + c.end()
        tag_nova = pagina[m.start():i] + u"dir-recolhida " + pagina[i:fim]
    else:
        tag_nova = tag + u' class="dir-recolhida"'
    return pagina[:m.start()] + tag_nova + marca + pagina[fim:]


def aplicar(pagina, com_pendencias=False, tela=u""):
    if not pagina or u"radai-tarefas-css" in pagina:
        return pagina
    baixa = pagina.lower()
    fim_head = baixa.find(u"</head>")
    fim_corpo = baixa.rfind(u"</body>")
    if fim_head < 0 or fim_corpo < 0:
        return pagina
    css = folha()
    saida = pagina[:fim_head] + css + pagina[fim_head:]
    corte = fim_corpo + len(css)
    saida = saida[:corte] + barra(com_pendencias) + _resto() + saida[corte:]
    saida = marcar_html(saida, tela)
    # GUARDA: o Iniciar desta barra abre o dialogo com a frase da regra 1; ele mora onde a barra mora.
    import radai_review
    return radai_review.aplicar(saida)


_NIVEL = (
    (u"falhou", "erro"), (u"erro", "erro"), (u"parei", "erro"),
    (u"nao consegui", "erro"), (u"não consegui", "erro"),
    (u"pronto", "ok"), (u"concluida", "ok"), (u"concluída", "ok"),
    (u"gravado", "ok"), (u"estrutura(s) em", "ok"),
)


def _classificar(txt):
    b = (txt or u"").lower()
    for frag, nivel in _NIVEL:
        if frag in b:
            return nivel
    return "info"


def _modulo_do_vigia():
    import sys as _s
    m = _s.modules.get("__main__")
    if m is not None and hasattr(m, "LOGBUF"):
        return m
    try:
        import radai_watcher
        return radai_watcher
    except Exception:
        return None


def _buffer_do_vigia():
    m = _modulo_do_vigia()
    if m is None:
        return None
    try:
        return list(m.LOGBUF)
    except Exception:
        return None


def _brutas_do_vigia(desde, teto):
    m = _modulo_do_vigia()
    if m is None:
        return None, int(desde or 0)
    fatiar = getattr(m, "fatia_do_log", None)
    if callable(fatiar):
        brutas, prox, _reiniciou = fatiar(desde, teto)
        return list(brutas), int(prox)
    buf = _buffer_do_vigia()
    if buf is None:
        return None, int(desde or 0)
    n = len(buf)
    i = max(0, min(int(desde or 0), n))
    return buf[i:i + teto], min(n, i + teto)


def _fatia_do_log(desde=0, teto=400):
    linhas = []
    brutas, prox = _brutas_do_vigia(desde, teto)
    if brutas is None:
        return [], int(desde or 0), ""
    for bruta in brutas:
        b = str(bruta or "")
        hora, txt = u"", b
        if b.startswith(u"[") and u"]" in b:
            dentro, txt = b[1:b.index(u"]")], b[b.index(u"]") + 1:].strip()
            hora = dentro.split(u" ")[-1]
        linhas.append({"t": hora, "nivel": _classificar(txt), "txt": txt})
    return linhas, prox, _estado_do_vigia()


def _estado_do_vigia():
    m = _modulo_do_vigia()
    if m is None:
        return ""
    try:
        st = m.STATE
        if st.get("ambiente_erro") or st.get("worker_erro"):
            return "erro"
        if st.get("paused"):
            return "parado"
        return "ok"
    except Exception:
        return ""


def montar(app, ler_vigia=None):
    @app.get("/api/atividade")
    def _atividade():
        try:
            return {"tarefas": atividade(ler_vigia)}
        except Exception as e:
            return {"tarefas": [], "erro": "%s: %s" % (type(e).__name__, e)}

    @app.get("/api/log")
    def _log(desde: int = 0):
        try:
            linhas, prox, estado = _fatia_do_log(desde)
            return {"linhas": linhas, "proximo": prox, "estado": estado}
        except Exception:
            return {"linhas": [], "proximo": int(desde or 0), "estado": ""}
