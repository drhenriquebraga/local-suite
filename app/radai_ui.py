# -*- coding: utf-8 -*-

TOKENS = u"""
:root{
 --ui-topo:60px;
 --ui-lado:56px;
 --ui-dir:280px; --ui-dir-recolhida:44px;
 --bg-0:#060d1a; --bg-1:#0a1120; --panel:#0c1322; --panel-2:#0f1729;
 --line:#1e293b; --line-strong:#2a3a55;
 --text:#e6edf7; --text-muted:#a3b1c6; --text-dim:#72829b;
 --accent:#4DA3FF; --accent-line:#2a3d57; --accent-fraco:rgba(77,163,255,.14);
 --ok:#12873F; --ok-txt:#fff; --aviso:#E8A33D; --perigo:#E96A5C;
 --success:#5BC57F; --warn:#E1B23B;
 --mono:'JetBrains Mono',ui-monospace,'Cascadia Mono',Consolas,monospace;
 --r-sm:5px; --r-md:6px; --r-lg:8px; --r-xl:10px; --r-2xl:12px;
 --r-pill:999px;
 --marca-grad:linear-gradient(90deg,#4DA3FF 0%,#3DD9F0 48%,#9D8BFF 100%);
 --mod-auto:#4DA3FF;   --mod-auto-fraco:rgba(77,163,255,.14);
 --mod-bridge:#9D8BFF; --mod-bridge-fraco:rgba(124,92,255,.14);
 --mod-recon:#31D0AA;  --mod-recon-fraco:rgba(49,208,170,.14);
 --mod-nidus:#E39B4F;  --mod-nidus-fraco:rgba(227,155,79,.14);
 --mod-nidus-b:#7FD1D6;
 --mod-elastic:#8FA9F2;  --mod-elastic-fraco:rgba(143,169,242,.14);
 --mod-elastic-b:#F2B5D4;
 --mod-bolus:#B5D65A;  --mod-bolus-fraco:rgba(181,214,90,.14);
 --mod-bolus-txt:#101a06;
 --font-display:Inter,system-ui,'Segoe UI',Arial,sans-serif;
 --font-mono:Consolas,'SF Mono',Menlo,monospace;
 --sombra:0 10px 28px rgba(0,0,0,.55);
 --fundo-perigo:#160a08; --borda-perigo:#552b23;
 --fundo-aviso:#1c1608;  --borda-aviso:#4a3a18;
 --fundo-ok:#0d1a12;     --borda-ok:#24422f;
 --ui-painel-abre:400ms; --ui-painel-fecha:350ms;
 --ui-painel-curva:cubic-bezier(.22,1,.36,1); --ui-painel-desfoque:2px;
 --img-fundo:#000000; --img-texto:#e6edf7; --img-texto-fraco:#a3b1c6;
 --linha:#1e293b;                    /* apelido antigo, ainda citado em telas */
 --txt:var(--text); --txt-fraco:var(--text-muted); --fraco:var(--text-muted);
 --fundo-2:var(--panel-2); --bg-2:var(--panel-2); --linha-fraca:var(--line);
}
:root[data-tema="claro"]{
 --bg-0:#f4f6fa; --bg-1:#eef1f7; --panel:#ffffff; --panel-2:#f7f9fc;
 --line:#d9e0ea; --line-strong:#bcc7d6;
 --text:#16202e; --text-muted:#4a5b70; --text-dim:#566377;
 --accent:#0B62C6; --accent-line:#9fc3ea; --accent-fraco:rgba(11,98,198,.10);
 --ok:#137a39; --ok-txt:#fff; --aviso:#8a5a05; --perigo:#B4382B;
 --success:#137a39; --warn:#8a5a05;
 --mod-auto:#0B62C6;   --mod-auto-fraco:rgba(11,98,198,.10);
 --mod-bridge:#6A4FD8; --mod-bridge-fraco:rgba(106,79,216,.10);
 --mod-recon:#0B6E59;  --mod-recon-fraco:rgba(11,110,89,.10);
 --mod-nidus:#8A4E12;  --mod-nidus-fraco:rgba(138,78,18,.10);
 --mod-nidus-b:#176A6F;
 --mod-elastic:#3C56A8;  --mod-elastic-fraco:rgba(60,86,168,.10);
 --mod-elastic-b:#A03A6E;
 --mod-bolus:#4F6B12;  --mod-bolus-fraco:rgba(79,107,18,.10);
 --mod-bolus-txt:#ffffff;
 --sombra:0 10px 28px rgba(22,32,46,.16);
 --fundo-perigo:#fdeceb; --borda-perigo:#e8b4ae;
 --fundo-aviso:#fdf4e2;  --borda-aviso:#e0c78a;
 --fundo-ok:#eaf6ee;     --borda-ok:#a9d6ba;
 --img-fundo:#000000; --img-texto:#e6edf7; --img-texto-fraco:#a3b1c6;
 --linha:#d9e0ea;
}
"""

CASCA = u"""
html,body{background:var(--bg-0);color:var(--text);
 font-family:var(--font-display,Inter,system-ui,'Segoe UI',Arial,sans-serif)}
body{padding-top:var(--ui-topo) !important}
:where(a){color:var(--accent)}

.rc-topo,.ui-topo{position:fixed;top:0;left:0;right:0;height:var(--ui-topo);
 z-index:30;display:flex;align-items:center;gap:12px;padding:0 18px;margin:0;
 border-bottom:1px solid var(--line);background:var(--panel-2);
 box-sizing:border-box;flex-wrap:nowrap;min-width:0}
.rc-topo .dir,.ui-topo .dir{margin-left:auto;display:flex;gap:9px;
 align-items:center;flex:0 0 auto}

.rc-topo .rc-marca,.ui-topo .rc-marca{display:flex !important;
 align-items:baseline;font-size:16px;font-weight:700;white-space:nowrap}
.rc-topo .rc-seta,.ui-topo .rc-seta{display:inline !important;
 color:var(--text-dim);font-size:14px}
.rc-topo .rc-tela,.ui-topo .rc-tela{display:inline-block !important;
 font-size:14px;color:var(--text-muted);font-weight:500;white-space:nowrap;
 overflow:hidden;text-overflow:ellipsis;min-width:0;flex:0 1 auto}
.rc-topo .rc-voltar,.ui-topo .rc-voltar{display:inline-block !important}

.ui-icone{display:grid;place-items:center;width:32px;height:32px;
 border-radius:var(--r-lg);border:1px solid var(--line);background:var(--panel);
 color:var(--text-muted);font-size:14px;line-height:1;text-decoration:none;
 cursor:pointer;flex:0 0 auto;box-sizing:border-box}
.ui-icone:hover{border-color:var(--accent);color:var(--accent)}
.ui-icone:focus-visible{outline:2px solid var(--accent);outline-offset:2px}

.ui-volta{display:inline-flex;align-items:center;gap:7px;height:34px;
 padding:0 13px;border-radius:var(--r-lg);text-decoration:none;
 border:1px solid var(--accent);background:var(--accent-fraco,rgba(77,163,255,.14));
 color:var(--accent);font-size:13.5px;font-weight:600;line-height:1;
 cursor:pointer;flex:0 0 auto;box-sizing:border-box;white-space:nowrap}
.ui-volta:hover{background:var(--accent);color:var(--bg-1,#0a1120);
 border-color:var(--accent)}
.ui-volta:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.ui-volta .v-seta{font-size:16px;line-height:1}
@media (max-width:760px){.ui-volta .v-txt{display:none}
 .ui-volta{padding:0 9px}}

.rc-topo .radai-lang .lista,.ui-topo .radai-lang .lista{z-index:1000}
.radai-menu{top:var(--ui-topo) !important}
.radai-tarefas{top:var(--ui-topo) !important}

body[data-tela="inicio"] .rc-topo .rc-marca,
body[data-tela="inicio"] .ui-topo .rc-marca{display:none !important}
body[data-tela="inicio"] .rc-topo .rc-seta,
body[data-tela="inicio"] .ui-topo .rc-seta,
body[data-tela="inicio"] .rc-topo .rc-tela,
body[data-tela="inicio"] .ui-topo .rc-tela{display:none !important}

body[data-tela="inicio"] .rc-capa h1{font-size:50px;letter-spacing:-.032em}
@media (max-width:700px){
 body[data-tela="inicio"] .rc-capa h1{font-size:36px}
}

@media (max-width:900px){
 body{padding-top:0 !important}
 .rc-topo,.ui-topo{position:static;height:auto;padding:11px 14px;
  flex-wrap:wrap;overflow:visible}
 .radai-menu,.radai-tarefas{top:auto !important}
}
"""

PASSOS = u"""
.ps-cx{background:var(--panel);border:1px solid var(--line);
 border-radius:var(--r-xl);padding:18px 20px;margin:0 0 14px}
.ps-cab{cursor:pointer;user-select:none;display:flex;align-items:center;
 gap:12px;font-size:18px;font-weight:650;letter-spacing:-.01em;margin:0;
 padding:2px 0 12px;border-bottom:1px solid var(--line);
 transition:color .12s;color:var(--text)}
.ps-num{display:inline-flex;align-items:center;justify-content:center;
 width:32px;height:32px;border-radius:var(--r-md);
 font-family:var(--font-display);font-size:17px;font-weight:800;
 line-height:1;background:var(--accent-fraco);color:var(--accent);
 border:1px solid var(--accent-line);flex:0 0 auto}
.ps-cab .ps-sub{font-weight:400;font-size:12.5px;color:var(--text-dim)}

.ps-seta{margin-left:auto;flex:0 0 auto;display:inline-grid;place-items:center;
 width:30px;height:30px;border-radius:var(--r-md);font-size:22px;line-height:1;
 color:var(--text-dim);transition:transform .16s,color .12s,background .12s}
.ps-cab:hover{color:var(--accent)}
.ps-cab:hover .ps-seta{color:var(--accent);background:var(--accent-fraco)}
.ps-cx.fechado > .ps-cab{border-bottom:none;padding-bottom:2px}
.ps-cx.fechado > .ps-cab .ps-seta{transform:rotate(-90deg)}
.ps-cx.fechado > .ps-corpo{display:none}
.ps-cx > .ps-corpo{padding-top:14px}

.ps-cx.inativo{opacity:.55}
.ps-cx.inativo > .ps-cab{cursor:default}
.ps-cx.inativo .ps-num{background:transparent;color:var(--text-dim);
 border-color:var(--line)}
.ps-cx.inativo .ps-seta{visibility:hidden}

@keyframes ps-abriu{from{border-color:var(--accent)}to{border-color:var(--line)}}
.ps-cx.abriu{animation:ps-abriu 1.1s ease-out}
"""

MOVIMENTO = u"""

.ui-esqueleto{position:relative;overflow:hidden;border-radius:var(--r-md,6px);
 background:var(--panel-2,#0f1729);min-height:14px}
.ui-esqueleto::after{content:"";position:absolute;inset:0;
 transform:translateX(-100%);
 background:linear-gradient(90deg,transparent,
  var(--line-strong,#2a3a55),transparent);
 animation:uiVarre 1.25s ease-in-out infinite}
@keyframes uiVarre{to{transform:translateX(100%)}}
.ui-esq-l{height:12px;margin:0 0 9px}
.ui-esq-l:nth-child(2){width:86%}
.ui-esq-l:nth-child(3){width:72%}
.ui-esq-l:nth-child(4){width:91%}
.ui-esq-l:last-child{margin-bottom:0}

.ui-gira{display:inline-block;width:13px;height:13px;border-radius:999px;
 border:2px solid var(--line-strong,#2a3a55);
 border-top-color:var(--accent,#4DA3FF);
 animation:uiGira .85s linear infinite;vertical-align:-2px}
@keyframes uiGira{to{transform:rotate(360deg)}}
.ui-feito{display:inline-grid;place-items:center;width:13px;height:13px;
 border-radius:999px;background:var(--success,#5BC57F);
 color:var(--bg-0,#060d1a);font-size:9px;line-height:1;
 animation:uiNasce .34s cubic-bezier(.34,1.56,.64,1) both;vertical-align:-2px}
@keyframes uiNasce{from{transform:scale(.2);opacity:0}to{transform:none;opacity:1}}
.ui-falhou{background:var(--perigo,#E96A5C)}

.ui-brilho{animation:uiBrilho .9s ease-out}
@keyframes uiBrilho{
 0%{background:var(--accent-fraco,rgba(77,163,255,.14));
    box-shadow:0 0 0 3px var(--accent-fraco,rgba(77,163,255,.14))}
 100%{background:transparent;box-shadow:none}}

.ui-badge{display:inline-grid;place-items:center;min-width:17px;height:17px;
 padding:0 5px;border-radius:999px;font:700 10px/1 var(--font-display,inherit);
 background:var(--accent,#4DA3FF);color:var(--bg-0,#060d1a)}
.ui-badge.zero{display:none}
.ui-badge.subiu{animation:uiPulsa .5s cubic-bezier(.34,1.56,.64,1)}
@keyframes uiPulsa{0%{transform:scale(1)}45%{transform:scale(1.28)}
 100%{transform:scale(1)}}

.ui-treme{animation:uiTreme 280ms ease-in-out}
@keyframes uiTreme{0%{transform:translateX(0)}25%{transform:translateX(6px)}
 50%{transform:translateX(-6px)}75%{transform:translateX(4px)}
 100%{transform:translateX(0)}}

@keyframes uiPainelEntra{from{transform:translateX(var(--ui-painel-curso,0px));
 opacity:0;filter:blur(var(--ui-painel-desfoque,2px))}}
@keyframes uiPainelSai{to{transform:translateX(var(--ui-painel-curso,0px));
 opacity:0;filter:blur(var(--ui-painel-desfoque,2px))}}
@keyframes uiPainelDesvela{from{clip-path:inset(0 var(--ui-painel-corte,0px) 0 0)}
 to{clip-path:inset(0 0 0 0)}}
@keyframes uiPainelVela{from{clip-path:inset(0 0 0 0)}
 to{clip-path:inset(0 var(--ui-painel-corte,0px) 0 0)}}

@media (prefers-reduced-motion:reduce){
 .ui-esqueleto::after{animation:none;display:none}
 .ui-gira{animation:none}
 .ui-feito{animation:none}
 .ui-brilho{animation:none}
 .ui-badge.subiu{animation:none}
 .ui-treme{animation:none}
}
"""


CONTROLES = u"""
input[type="checkbox"]:where(:not([role="switch"]):not(.ui-check-nativo)){
 -webkit-appearance:none;appearance:none;box-sizing:border-box;
 display:inline-grid;place-content:center;vertical-align:middle;
 width:16px;height:16px;min-width:16px;padding:0;cursor:pointer;
 border:1.5px solid var(--line-strong,#2a3a55);border-radius:4px;
 background:var(--panel-2,#0f1729);color:var(--ok-txt,#fff);
 transition:background-color 150ms cubic-bezier(.22,1,.36,1),
            border-color 150ms cubic-bezier(.22,1,.36,1),
            transform 150ms cubic-bezier(.22,1,.36,1)}
input[type="checkbox"]:where(:not([role="switch"]):not(.ui-check-nativo))::before{
 content:"";width:8px;height:4.5px;margin-top:-2px;box-sizing:content-box;
 border-left:2px solid currentColor;border-bottom:2px solid currentColor;
 transform:rotate(-45deg);clip-path:inset(0 100% 0 0);
 transition:clip-path 350ms cubic-bezier(.22,1,.36,1)}
input[type="checkbox"]:where(:not([role="switch"]):not(.ui-check-nativo)):checked{
 background:var(--ui-check-cor,var(--accent,#4DA3FF));
 border-color:var(--ui-check-cor,var(--accent,#4DA3FF))}
input[type="checkbox"]:where(:not([role="switch"]):not(.ui-check-nativo)):checked::before{
 clip-path:inset(0 0 0 0)}
input[type="checkbox"]:where(:not([role="switch"]):not(.ui-check-nativo)):active{
 transform:scale(.92)}
input[type="checkbox"]:where(:not([role="switch"]):not(.ui-check-nativo)):focus-visible{
 outline:2px solid var(--accent,#4DA3FF);outline-offset:2px}
input[type="checkbox"]:where(:not([role="switch"]):not(.ui-check-nativo)):disabled{
 opacity:.45;cursor:not-allowed}

:is(button.pri,.ui-bt.pri,.rv-pri,.ui-verde){position:relative;overflow:hidden;
 transition:border-color .12s,background .12s,color .12s,
            transform .14s ease,box-shadow .14s ease}
:is(button.pri,.ui-bt.pri,.rv-pri,.ui-verde):not(:disabled):not(.desligado):not([aria-disabled="true"]):hover{
 transform:translateY(-1px);box-shadow:0 6px 18px rgba(21,163,74,.32)}
:is(button.pri,.ui-bt.pri,.rv-pri,.ui-verde):not(:disabled):not(.desligado):not([aria-disabled="true"]):active{
 transform:none;box-shadow:none}
:is(button.pri,.ui-bt.pri,.rv-pri,.ui-verde):not(:disabled):not(.desligado):not([aria-disabled="true"])::after{
 content:"";position:absolute;top:0;left:-140%;width:70%;height:100%;
 pointer-events:none;
 background:linear-gradient(100deg,transparent,rgba(255,255,255,.34),transparent);
 animation:uiBrilhoVerde 2.6s ease-in-out infinite}
@keyframes uiBrilhoVerde{0%{left:-140%}55%{left:160%}100%{left:160%}}

@media (prefers-reduced-motion:reduce){
 input[type="checkbox"]:where(:not([role="switch"]):not(.ui-check-nativo)),
 input[type="checkbox"]:where(:not([role="switch"]):not(.ui-check-nativo))::before{
  transition:none}
 input[type="checkbox"]:where(:not([role="switch"]):not(.ui-check-nativo)):active{
  transform:none}
 :is(button.pri,.ui-bt.pri,.rv-pri,.ui-verde){transition:none}
 :is(button.pri,.ui-bt.pri,.rv-pri,.ui-verde):hover{transform:none !important}
 :is(button.pri,.ui-bt.pri,.rv-pri,.ui-verde)::after{animation:none !important;
  display:none !important}
}
"""


TRANSICOES = u"""

.ui-pnl-veu{position:fixed;inset:0;z-index:5000;display:none;
 background:rgba(4,8,16,.62);backdrop-filter:blur(2px);
 align-items:flex-start;justify-content:center;padding:8vh 20px 20px;
 opacity:0;transition:opacity .18s ease}
.ui-pnl-veu.on{display:flex}
.ui-pnl-veu.vis{opacity:1}
.ui-pnl{width:100%;max-width:620px;background:var(--panel,#0c1424);
 border:1px solid var(--line-strong,#2a3a55);border-radius:var(--r-xl,12px);
 box-shadow:var(--sombra,0 18px 48px rgba(0,0,0,.5));color:var(--text,#e7eefc);
 overflow:hidden;
 display:grid;grid-template-rows:0fr;
 transform:translateY(-8px);
 transition:grid-template-rows .26s cubic-bezier(.22,1,.36,1),
            transform .26s cubic-bezier(.22,1,.36,1)}
.ui-pnl-veu.vis .ui-pnl{grid-template-rows:1fr;transform:none}
.ui-pnl>.dentro{min-height:0;overflow:hidden}

.ui-pnl-veu.debaixo{align-items:flex-end;justify-content:center;padding:0}
.ui-pnl-veu.debaixo .ui-pnl{max-width:560px;border-radius:16px 16px 0 0;
 border-bottom:0;max-height:88vh;
 transform:translateY(26px);
 box-shadow:0 -18px 48px rgba(0,0,0,.52)}
.ui-pnl-veu.debaixo.vis .ui-pnl{transform:none}
.ui-pnl-veu.debaixo .ui-pnl::before{content:"";display:block;width:38px;
 height:4px;border-radius:99px;background:var(--line-strong,#2a3a55);
 margin:10px auto 0}
@media (prefers-reduced-motion:reduce){
 .ui-pnl-veu.debaixo .ui-pnl{transform:none}
}
.ui-pnl .pnl-cab{display:flex;align-items:center;gap:10px;
 padding:15px 18px 0;font:600 15px/1.35 var(--font-display,inherit)}
.ui-pnl .pnl-cab .ic{color:var(--accent,#4DA3FF);font-size:17px;flex:0 0 auto}
.ui-pnl .pnl-corpo{padding:11px 18px 4px;font-size:13px;line-height:1.62;
 color:var(--text-muted,#a8b8d4);max-height:46vh;overflow:auto}
.ui-pnl .pnl-corpo p{margin:0 0 9px}
.ui-pnl .pnl-corpo p:last-child{margin-bottom:0}
.ui-pnl .pnl-corpo b{color:var(--text,#e7eefc);font-weight:600}
.ui-pnl .pnl-corpo ul{margin:0 0 9px;padding-left:19px}
.ui-pnl .pnl-corpo li{margin:0 0 4px}
.ui-pnl .pnl-corpo code{font-family:var(--font-mono,monospace);
 color:var(--text,#e7eefc)}
.ui-pnl .pnl-bts{display:flex;gap:9px;justify-content:flex-end;
 flex-wrap:wrap;padding:13px 18px 16px}

.ui-sino{position:relative;display:inline-grid;place-items:center;
 width:30px;height:30px;border-radius:var(--r-md,6px);
 border:1px solid transparent;background:transparent;cursor:pointer;
 color:var(--text-dim,#72829b);font-size:15px;line-height:1;
 transition:color .12s,border-color .12s}
.ui-sino:hover{color:var(--accent,#4DA3FF);
 border-color:var(--line-strong,#2a3a55)}
.ui-sino .n{position:absolute;top:-3px;right:-3px;min-width:16px;height:16px;
 padding:0 4px;border-radius:999px;
 font:700 9.5px/16px var(--font-display,inherit);text-align:center;
 background:var(--success,#5BC57F);color:var(--bg-0,#060d1a);
 border:2px solid var(--bg-0,#060d1a);box-sizing:content-box}
.ui-sino[data-n="0"]{display:none}
.ui-sino.bateu{animation:uiSinoBate .62s cubic-bezier(.36,.07,.19,.97)}
.ui-sino.bateu .n{animation:uiNasce .34s cubic-bezier(.34,1.56,.64,1) both}
@keyframes uiSinoBate{0%,100%{transform:rotate(0)}
 15%{transform:rotate(13deg)}30%{transform:rotate(-11deg)}
 45%{transform:rotate(8deg)}60%{transform:rotate(-5deg)}
 75%{transform:rotate(2deg)}}

.ui-abas{position:relative;display:inline-flex;gap:2px;padding:3px;
 border-radius:var(--r-md,6px);background:var(--panel-2,#0f1729);
 border:1px solid var(--line-strong,#2a3a55)}
.ui-abas .marca{position:absolute;top:3px;bottom:3px;left:0;width:0;
 border-radius:calc(var(--r-md,6px) - 2px);background:var(--accent,#4DA3FF);
 transition:transform .24s cubic-bezier(.22,1,.36,1),width .24s
            cubic-bezier(.22,1,.36,1);pointer-events:none}
.ui-abas button{position:relative;z-index:1;border:0;background:transparent;
 color:var(--text-muted,#a8b8d4);cursor:pointer;padding:6px 14px;
 font:500 12.5px/1.2 var(--font-display,inherit);border-radius:4px;
 white-space:nowrap;transition:color .18s}
.ui-abas button[aria-selected="true"]{color:var(--bg-0,#060d1a);font-weight:600}
.ui-abas button:focus-visible{outline:2px solid var(--accent,#4DA3FF);
 outline-offset:2px}
.ui-abas-fonte{position:absolute;width:1px;height:1px;padding:0;margin:-1px;
 overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;border:0}

.ui-morf{opacity:0;visibility:hidden;transform:translateY(-6px) scale(.97);
 transform-origin:top left;
 transition:opacity .16s ease,transform .18s cubic-bezier(.22,1,.36,1),
            visibility 0s linear .18s}
.ui-morf.on{opacity:1;visibility:visible;transform:none;
 transition:opacity .16s ease,transform .18s cubic-bezier(.22,1,.36,1),
            visibility 0s}

.ui-shimmer{background:linear-gradient(90deg,
  var(--text-muted,#a8b8d4) 0%,var(--text-muted,#a8b8d4) 38%,
  var(--text,#e7eefc) 50%,
  var(--text-muted,#a8b8d4) 62%,var(--text-muted,#a8b8d4) 100%);
 background-size:250% 100%;
 -webkit-background-clip:text;background-clip:text;color:transparent;
 animation:uiShimmer 2.4s linear infinite}
@keyframes uiShimmer{from{background-position:130% 0}to{background-position:-30% 0}}

.ui-revelar{animation:uiRevela .34s cubic-bezier(.22,1,.36,1) both}
@keyframes uiRevela{from{opacity:0;transform:translateY(6px)}
 to{opacity:1;transform:none}}
.ui-revelar-lista>*{animation:uiRevela .34s cubic-bezier(.22,1,.36,1) both}
.ui-revelar-lista>*:nth-child(1){animation-delay:0ms}
.ui-revelar-lista>*:nth-child(2){animation-delay:34ms}
.ui-revelar-lista>*:nth-child(3){animation-delay:68ms}
.ui-revelar-lista>*:nth-child(4){animation-delay:102ms}
.ui-revelar-lista>*:nth-child(5){animation-delay:136ms}
.ui-revelar-lista>*:nth-child(n+6){animation-delay:170ms}

.ui-ponto-alvo{position:relative}
.ui-ponto{position:absolute;top:-3px;right:-3px;width:9px;height:9px;
 border-radius:50%;background:var(--perigo,#E96A5C);pointer-events:none;
 box-shadow:0 0 0 2px var(--panel-2,#0f1729);
 animation:uiNasce .34s cubic-bezier(.34,1.56,.64,1) both}
.ui-ponto::after{content:"";position:absolute;inset:0;border-radius:50%;
 background:var(--perigo,#E96A5C);
 animation:uiPontoOnda 1.2s cubic-bezier(.22,1,.36,1) .34s 2 both}
@keyframes uiPontoOnda{from{transform:scale(1);opacity:.55}
 to{transform:scale(2.8);opacity:0}}

@media (prefers-reduced-motion:reduce){
 .ui-pnl-veu{transition:none}
 .ui-pnl{transition:none;grid-template-rows:1fr;transform:none}
 .ui-sino.bateu{animation:none}
 .ui-sino.bateu .n{animation:none}
 .ui-abas .marca{transition:none}
 .ui-morf{transition:none}
 .ui-shimmer{animation:none;background:none;-webkit-background-clip:border-box;
  background-clip:border-box;color:var(--text-muted,#a8b8d4)}
 .ui-revelar{animation:none}
 .ui-revelar-lista>*{animation:none}
 .ui-ponto{animation:none}
 .ui-ponto::after{animation:none;display:none}
}
"""


AJUDA = u"""
.ui-conexao{position:fixed;left:0;right:0;top:0;z-index:99999;
 padding:10px 16px;font-size:13px;line-height:1.55;
 background:var(--aviso);color:var(--bg-0);
 box-shadow:0 2px 12px rgba(0,0,0,.35)}
.ui-conexao.ok{background:var(--success);color:var(--bg-0)}
.ui-conexao b{font-weight:700}
.ui-conexao-nota{display:block;margin-top:3px;font-size:11.5px;opacity:.82}
.ui-ajuda{display:inline-grid;place-items:center;width:17px;height:17px;
 border-radius:50%;border:1px solid var(--line-strong);color:var(--text-dim);
 font-size:11px;font-weight:600;cursor:help;position:relative;vertical-align:2px;
 margin-left:6px;font-family:var(--font-display);flex:0 0 auto}
.ui-ajuda:hover,.ui-ajuda:focus{border-color:var(--accent);color:var(--accent);
 outline:none}
.ui-ajuda .ui-balao{display:block;opacity:0;visibility:hidden;
 transform:translateY(-6px) scale(.97);transform-origin:top left;
 transition:opacity .16s ease,transform .18s cubic-bezier(.22,1,.36,1),
            visibility 0s linear .18s;
 position:absolute;left:0;top:23px;z-index:60;
 width:min(430px,72vw);padding:11px 13px;border-radius:var(--r-lg);
 border:1px solid var(--line-strong);background:var(--panel);
 color:var(--text-muted);font-size:12px;line-height:1.55;font-weight:400;
 text-align:left;box-shadow:var(--sombra);cursor:auto;letter-spacing:0;
 text-transform:none;white-space:normal}
.ui-ajuda .ui-balao p{margin:0 0 9px}
.ui-ajuda .ui-balao p:last-child{margin-bottom:0}
.ui-ajuda .ui-balao b{color:var(--text);font-weight:600}
.ui-ajuda .ui-balao code{font-family:var(--font-mono);color:var(--text)}
.ui-ajuda:hover .ui-balao,.ui-ajuda:focus .ui-balao,
.ui-ajuda:focus-within .ui-balao{opacity:1;visibility:visible;transform:none;
 transition:opacity .16s ease,transform .18s cubic-bezier(.22,1,.36,1),
            visibility 0s}
/* GUARDA: fechado, o balão não tem altura; senão ele estica a rolagem da página. */
.ui-ajuda:not(:hover):not(:focus):not(:focus-within) .ui-balao{
 max-height:0 !important;padding-top:0 !important;padding-bottom:0 !important;
 border-top-width:0 !important;border-bottom-width:0 !important;overflow:hidden !important;
 transition:opacity .16s ease,transform .18s cubic-bezier(.22,1,.36,1),
            visibility 0s linear .18s,max-height 0s linear .18s,
            padding 0s linear .18s,border-width 0s linear .18s}
.ui-ajuda.dir .ui-balao{left:auto;right:0;transform-origin:top right}
@media (prefers-reduced-motion:reduce){
 .ui-ajuda .ui-balao{transition:none;transform:none}
}
@media (max-width:600px){
 .ui-ajuda .ui-balao,.ui-ajuda.dir .ui-balao{position:fixed;left:16px;
  right:16px;top:auto;width:auto;max-height:60vh;overflow:auto;
  transform-origin:top center}
}
"""

BOTOES = u"""
button.btn,.ui-bt{display:inline-flex;align-items:center;justify-content:center;gap:7px;
 background:var(--panel-2);border:1px solid var(--line-strong);
 color:var(--text);border-radius:var(--r-md);padding:8px 14px;font-size:12.5px;
 font-family:var(--font-display);cursor:pointer;text-decoration:none;
 line-height:1.2;transition:border-color .12s,background .12s,color .12s}
button.btn:hover,.ui-bt:hover{border-color:var(--accent);color:var(--accent)}
button.btn:disabled,.ui-bt:disabled,.ui-bt.desligado{opacity:.4;cursor:not-allowed}
.ui-bt:disabled:hover,.ui-bt.desligado:hover{border-color:var(--line-strong);
 color:var(--text)}
button.btn.pri,.ui-bt.pri{background:var(--ok);border-color:var(--ok);color:var(--ok-txt);
 font-weight:600}
.ui-bt.pri:hover{filter:brightness(1.12);color:var(--ok-txt)}
.ui-bt.perigo{border-color:var(--perigo);color:var(--perigo)}
.ui-bt.perigo:hover{background:rgba(233,106,92,.12)}
.ui-bt.lig{background:var(--ok);border-color:var(--ok);color:var(--ok-txt);
 font-weight:600}

input[type=text],input[type=number],input[type=search],input[type=password],
textarea,select{background:var(--panel-2);color:var(--text);
 border:1px solid var(--line-strong);border-radius:var(--r-md);
 padding:8px 10px;font-size:13px;font-family:var(--font-mono);
 box-sizing:border-box}
input[type=text]:focus,input[type=number]:focus,textarea:focus,select:focus{
 outline:none;border-color:var(--accent)}
input::placeholder,textarea::placeholder{color:var(--text-dim)}
input[type=text]:disabled,select:disabled{opacity:.5}

.ui-veu{display:none;position:fixed;inset:0;z-index:4000;
 background:rgba(4,8,16,.72);align-items:center;justify-content:center;padding:24px}
.ui-veu.on{display:flex}
.ui-cx{background:var(--panel);border:1px solid var(--line-strong);
 border-radius:var(--r-xl);max-width:520px;width:100%;padding:20px 22px;
 color:var(--text);box-shadow:var(--sombra);font-size:13.5px;line-height:1.6}
.ui-cx h3{margin:0 0 10px;font-size:16px;display:flex;align-items:center;gap:9px}
.ui-cx h3 .ic{color:var(--aviso);font-size:17px}
.ui-cx .motivo{background:var(--fundo-aviso);border:1px solid var(--borda-aviso);
 border-left:3px solid var(--aviso);border-radius:0 var(--r-lg) var(--r-lg) 0;
 padding:10px 13px;margin:0 0 14px;color:var(--text-muted);font-size:12.5px}
.ui-cx .bts{display:flex;gap:9px;justify-content:flex-end;flex-wrap:wrap}
"""

MARCA_TEMA = u"radai-tema-js"

TEMAS = (u"claro", u"escuro", u"sistema")

TEMA_PADRAO = u"sistema"

TEMA_JS = u"""
<script id="radai-tema-js">
(function(){
 var CHAVE = 'radai_tema', VALE = {claro: 1, escuro: 1, sistema: 1};
 var raiz = document.documentElement, guardado = null, mq = null;
 try{ mq = window.matchMedia ? window.matchMedia('(prefers-color-scheme: light)') : null }
 catch(e){ mq = null }
 function escolha(){
  try{ var v = localStorage.getItem(CHAVE); if(VALE[v]) return v }catch(e){}
  return VALE[guardado] ? guardado : 'sistema';
 }
 function efetivo(v){
  // GUARDA: a tela que so existe escura (a porta) se declara em data-tema-fixo, e a escolha nao a alcanca.
  var fixo = raiz.getAttribute('data-tema-fixo');
  if(fixo === 'claro' || fixo === 'escuro') return fixo;
  if(v === 'sistema') return (mq && mq.matches) ? 'claro' : 'escuro';
  return v;
 }
 function pintar(){
  var v = escolha(), t = efetivo(v);
  raiz.setAttribute('data-tema', t);
  raiz.setAttribute('data-tema-escolha', v);
  return t;
 }
 function avisar(){
  var d = {tema: raiz.getAttribute('data-tema'), escolha: escolha()};
  try{ window.dispatchEvent(new CustomEvent('radai-tema', {detail: d})) }
  catch(e){
   try{ var ev = document.createEvent('CustomEvent');
        ev.initCustomEvent('radai-tema', false, false, d); window.dispatchEvent(ev) }catch(x){}
  }
 }
 window.uiTemaEscolha = escolha;
 window.uiTema = function(t){
  if(t && VALE[t]){
   guardado = t;
   try{ localStorage.setItem(CHAVE, t) }catch(e){}
  }
  var v = pintar();
  if(t) avisar();
  return v;
 };
 pintar();
 function seguirOSistema(){ if(escolha() === 'sistema'){ pintar(); avisar() } }
 if(mq){
  if(mq.addEventListener) mq.addEventListener('change', seguirOSistema);
  else if(mq.addListener) mq.addListener(seguirOSistema);
 }
 window.addEventListener('storage', function(ev){
  if(!ev || ev.key === CHAVE || ev.key === null){ pintar(); avisar() }
 });
})();
</script>
"""

JS = u"""
<script id="radai-ui-js">
(function(){
 function el(id){ return document.getElementById(id) }

 window.uiTexto = function(alvo, frase){
  if(!alvo) return;
  alvo.textContent = frase;
  try{ alvo.removeAttribute('data-radai-t'); alvo.removeAttribute('data-radai-tr') }catch(e){}
 };
 window.uiHTML = function(alvo, html){
  if(!alvo) return;
  alvo.innerHTML = html;
  try{
   alvo.removeAttribute('data-radai-t'); alvo.removeAttribute('data-radai-tr');
   var m = alvo.querySelectorAll('[data-radai-t]');
   for(var i = 0; i < m.length; i++) m[i].removeAttribute('data-radai-t');
  }catch(e){}
 };
 window.psAbrir = function(id, piscar){
  var c = el(id); if(!c) return;
  c.classList.remove('inativo');
  if(!c.classList.contains('fechado')) return;
  c.classList.remove('fechado');
  if(piscar){ c.classList.add('abriu');
   setTimeout(function(){ c.classList.remove('abriu') }, 1200); }
 };
 window.psFechar = function(id){ var c=el(id); if(c) c.classList.add('fechado') };

 function psPeloEndereco(){
  try{
   var id = (location.hash || '').replace(/^#/, '');
   if(!id) return;
   var c = document.getElementById(id);
   if(!c || !c.classList.contains('ps-cx')) return;
   window.psAbrir(id, true);
   c.scrollIntoView({block:'start'});
  }catch(e){}
 }
 window.addEventListener('hashchange', psPeloEndereco);
 document.addEventListener('DOMContentLoaded', psPeloEndereco);
 document.addEventListener('click', function(ev){
  var h = ev.target.closest && ev.target.closest('.ps-cab'); if(!h) return;
  if(ev.target.closest('.ui-ajuda')) return;
  var cx = h.parentNode;
  if(cx.classList.contains('inativo')) return;
  cx.classList.toggle('fechado');
 });
 document.addEventListener('keydown', function(ev){
  if(ev.key !== 'Enter' && ev.key !== ' ') return;
  var h = ev.target.closest && ev.target.closest('.ps-cab'); if(!h) return;
  ev.preventDefault(); h.click();
 });

 window.uiPorQue = function(titulo, motivo, acao){
  var v = el('ui-veu'); if(!v) return;
  el('ui-veu-tit').textContent = titulo || 'Nada aconteceu';
  el('ui-veu-motivo').innerHTML = motivo || '';
  el('ui-veu-acao').innerHTML = (acao && acao.href)
   ? '<a class="ui-bt pri" href="' + acao.href + '">' + (acao.texto || 'Ir') + '</a>'
   : '';
  v.classList.add('on');
 };
 document.addEventListener('click', function(e){
  var v = el('ui-veu'); if(!v) return;
  if(e.target === v || (e.target.closest && e.target.closest('#ui-veu-fechar')))
   v.classList.remove('on');
 });
 document.addEventListener('keydown', function(e){
  if(e.key !== 'Escape') return;
  var v = el('ui-veu'); if(v) v.classList.remove('on');
 });

 function ssLer(k){ try{ return sessionStorage.getItem(k) }catch(e){ return null } }
 function ssGravar(k, v){
  try{ if(v === null) sessionStorage.removeItem(k); else sessionStorage.setItem(k, v) }catch(e){}
 }
 function semMovimento(){
  try{ return !!(window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches) }
  catch(e){ return false }
 }
 function painelMs(nome, padrao){
  try{
   var t = getComputedStyle(document.documentElement).getPropertyValue(nome);
   var n = parseFloat(t);
   if(isFinite(n) && n >= 0) return /ms\\s*$/.test(t) ? n : n * 1000;
  }catch(e){}
  return padrao;
 }
 function fixo(sel){
  var e = document.querySelector(sel);
  try{ return !!e && getComputedStyle(e).position === 'fixed' }catch(err){ return false }
 }
 function depoisDoPrimeiroQuadro(f){
  function vai(){ requestAnimationFrame(function(){ requestAnimationFrame(f) }) }
  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', vai);
  else vai();
 }

 var DIR_USUARIO = 'radai_dir_usuario', DIR_VISTA = 'radai_dir_vista';
 var dirT = 0, dirPronta = false;
 function dirFechada(){
  var c = document.documentElement.classList;
  return c.contains('dir-recolhida') || c.contains('dir-fechando');
 }
 function dirAvisar(){
  try{ document.dispatchEvent(new CustomEvent('radai:dir', {detail: {recolhida: dirFechada()}})) }
  catch(e){}
 }
 function dirAplicar(v, anima){
  var r = document.documentElement, c = r.classList;
  var mexe = !!anima && !semMovimento() && fixo('.radai-tarefas');
  if(v === '1' && c.contains('dir-fechando') && mexe) return v;
  if(v === '0' && c.contains('dir-abrindo')) return v;
  var antes = dirFechada();
  clearTimeout(dirT);
  c.remove('dir-abrindo'); c.remove('dir-fechando');
  if(v === '1'){
   if(!antes && mexe){
    c.add('dir-fechando');
    dirT = setTimeout(function(){
     c.remove('dir-fechando'); c.add('dir-recolhida'); dirAvisar();
    }, painelMs('--ui-painel-fecha', 350));
   } else c.add('dir-recolhida');
  } else {
   c.remove('dir-recolhida');
   if(antes && mexe){
    void r.offsetWidth;
    c.add('dir-abrindo');
    dirT = setTimeout(function(){ c.remove('dir-abrindo') },
                      painelMs('--ui-painel-abre', 400) + 50);
   }
  }
  ssGravar(DIR_VISTA, v === '1' ? 'recolhida' : 'aberta');
  dirAvisar();
  return v;
 }
 function dirQuer(){
  var u = ssLer(DIR_USUARIO);
  if(u === 'aberta') return '0';
  if(u === 'recolhida') return '1';
  return document.documentElement.getAttribute('data-dir-sozinha') === '1' ? '0' : '1';
 }
 window.uiDireita = function(forcar, deMao){
  try{
   var r = document.documentElement, v;
   if(forcar === undefined){
    // GUARDA: alterna pelo estado da TELA, e não pelo guardado: a tela que nasceu recolhida abre no primeiro clique.
    v = dirFechada() ? '0' : '1';
    deMao = true;
   } else v = (String(forcar) === '1') ? '1' : '0';
   // GUARDA: o estado de partida é da casca; pedido de script enquanto a página carrega não o desfaz.
   if(!deMao && document.readyState === 'loading') return dirFechada() ? '1' : '0';
   if(deMao){
    ssGravar(DIR_USUARIO, v === '1' ? 'recolhida'
             : (r.getAttribute('data-dir-sozinha') === '1' ? null : 'aberta'));
   }
   return dirAplicar(v, dirPronta);
  }catch(e){ return '0' }
 };
 (function(){
  var r = document.documentElement;
  if(!r.hasAttribute('data-dir-sozinha')){ ssGravar(DIR_VISTA, 'recolhida'); dirPronta = true; return }
  // GUARDA: nasce como o servidor mandou (recolhida); só abre antes do primeiro quadro se a tela anterior da aba já a mostrava aberta, senão abre animada depois dele.
  dirAplicar(dirQuer() === '0' && ssLer(DIR_VISTA) === 'aberta' ? '0' : '1', false);
  depoisDoPrimeiroQuadro(function(){
   dirPronta = true;
   if(dirQuer() === '0' && dirFechada()) dirAplicar('0', true);
  });
  window.addEventListener('pageshow', function(ev){
   if(!ev || !ev.persisted) return;
   var q = dirQuer();
   if(q !== (dirFechada() ? '1' : '0')) dirAplicar(q, true);
  });
 })();
 window.uiConexao = function(ok, detalhe){
  try{
   var f = document.getElementById('uiConexao');
   if(!f){
    if(ok) return;                      // nada a mostrar, e nada a criar
    f = document.createElement('div');
    f.id = 'uiConexao';
    f.className = 'ui-conexao';
    document.body.appendChild(f);
   }
   if(ok){
    if(f.dataset.caiu === '1'){
     f.className = 'ui-conexao ok';
     f.textContent = 'conexão com o programa restabelecida';
     setTimeout(function(){ if(f.parentNode) f.parentNode.removeChild(f) }, 2500);
    } else if(f.parentNode){
     f.parentNode.removeChild(f);
    }
    return;
   }
   f.dataset.caiu = '1';
   f.className = 'ui-conexao';
   f.innerHTML = '<b>O programa não está respondendo.</b> '
     + '<span>Isso costuma ser trabalho pesado em curso — uma varredura, uma série sendo aberta. A tela volta sozinha quando ele terminar.</span>'
     + '<span class="ui-conexao-nota"><span>O programa roda em segundo plano, sem janela. Se isto durar mais que alguns minutos, o log está em Configurações › Diagnóstico.</span>'
     + (detalhe ? ' (' + detalhe + ')' : '') + '</span>';
  }catch(e){}
 };

 var LADO = 'radai_trilho_aberto', ladoT = 0, ladoPronto = false;
 function ladoAberto(){
  var r = document.documentElement;
  return r.getAttribute('data-trilho') === 'aberto' && !r.classList.contains('lado-fechando');
 }
 function ladoRotulo(v){
  var b = document.getElementById('ladoDobra');
  if(!b) return;
  var rot = (v === '1') ? 'recolher o menu' : 'expandir o menu';
  b.setAttribute('title', rot);
  b.setAttribute('aria-label', rot);
 }
 function ladoAplicar(v, anima){
  var r = document.documentElement, c = r.classList;
  var mexe = !!anima && !semMovimento() && fixo('.radai-menu');
  if(v === '0' && c.contains('lado-fechando') && mexe) return v;
  if(v === '1' && c.contains('lado-abrindo')) return v;
  var antes = ladoAberto();
  clearTimeout(ladoT);
  c.remove('lado-abrindo'); c.remove('lado-fechando');
  if(v === '1'){
   r.setAttribute('data-trilho', 'aberto');
   if(!antes && mexe){
    void r.offsetWidth;
    c.add('lado-abrindo');
    ladoT = setTimeout(function(){ c.remove('lado-abrindo') },
                       painelMs('--ui-painel-abre', 400) + 50);
   }
  } else if(antes && mexe){
   c.add('lado-fechando');
   ladoT = setTimeout(function(){
    c.remove('lado-fechando'); r.removeAttribute('data-trilho');
   }, painelMs('--ui-painel-fecha', 350));
  } else r.removeAttribute('data-trilho');
  ladoRotulo(v);
  return v;
 }
 window.uiLado = function(forcar){
  try{
   var v;
   if(forcar === undefined){
    v = ladoAberto() ? '0' : '1';
    try{ localStorage.setItem(LADO, v) }catch(e){}
   } else v = (String(forcar) === '1') ? '1' : '0';
   return ladoAplicar(v, ladoPronto);
  }catch(e){ return '0' }
 };
 function veioDaPorta(){
  try{
   var n = performance.getEntriesByType('navigation')[0];
   if(n && n.type && n.type !== 'navigate') return false;
   if(!document.referrer) return false;
   var de = new URL(document.referrer);
   return de.origin === location.origin && (de.pathname === '/' || de.pathname === '/suite')
          && location.pathname !== '/' && location.pathname !== '/suite';
  }catch(e){ return false }
 }
 (function(){
  var salvo = '0';
  try{ salvo = (localStorage.getItem(LADO) === '1') ? '1' : '0' }catch(e){}
  // GUARDA: vinda da porta, a barra esquerda nasce recolhida e se expande depois do primeiro quadro; recarregar ou voltar não repete.
  var daPorta = veioDaPorta();
  ladoAplicar(daPorta ? '0' : salvo, false);
  depoisDoPrimeiroQuadro(function(){
   ladoPronto = true;
   ladoRotulo(ladoAberto() ? '1' : '0');
   if(daPorta && document.querySelector('.radai-menu')){
    try{ localStorage.setItem(LADO, '1') }catch(e){}
    ladoAplicar('1', true);
   }
  });
 })();

 var _pnlFoco = null;
 window.uiPrenderFoco = function(caixa, e){
  try{
   if(!caixa || !e || e.key !== 'Tab') return;
   var fs = Array.prototype.filter.call(caixa.querySelectorAll(
     'button,[href],input,select,textarea,[tabindex]'), function(x){
      if(x.disabled || x.getAttribute('tabindex') === '-1') return false;
      var r = x.getBoundingClientRect();
      return r.width > 0 && r.height > 0 && getComputedStyle(x).visibility !== 'hidden';
     });
   if(!fs.length){ e.preventDefault(); return }
   var i = fs.indexOf(document.activeElement);
   if(e.shiftKey){
    if(i <= 0){ e.preventDefault(); fs[fs.length - 1].focus() }
   } else if(i < 0 || i === fs.length - 1){
    e.preventDefault(); fs[0].focus();
   }
  }catch(err){}
 };
 function _pnlMonta(){
  var v = document.getElementById('ui-pnl-veu');
  if(v) return v;
  v = document.createElement('div');
  v.className = 'ui-pnl-veu';
  v.id = 'ui-pnl-veu';
  v.innerHTML = '<div class="ui-pnl" role="dialog" aria-modal="true"'
    + ' aria-labelledby="ui-pnl-tit"><div class="dentro">'
    + '<div class="pnl-cab"><span class="ic" aria-hidden="true">&#9679;</span>'
    + '<span id="ui-pnl-tit"></span></div>'
    + '<div class="pnl-corpo" id="ui-pnl-corpo"></div>'
    + '<div class="pnl-bts"><button type="button" class="ui-bt"'
    + ' id="ui-pnl-nao"></button>'
    + '<button type="button" class="ui-bt pri" id="ui-pnl-sim"></button>'
    + '</div></div></div>';
  document.body.appendChild(v);
  return v;
 }
 function _pnlFecha(v){
  v.classList.remove('vis');
  setTimeout(function(){ v.classList.remove('on') }, 200);
  try{ if(_pnlFoco && _pnlFoco.focus) _pnlFoco.focus() }catch(e){}
  _pnlFoco = null;
 }
 window.uiPainel = function(o){
  o = o || {};
  var v = _pnlMonta();
  var tit = document.getElementById('ui-pnl-tit');
  var corpo = document.getElementById('ui-pnl-corpo');
  var sim = document.getElementById('ui-pnl-sim');
  var nao = document.getElementById('ui-pnl-nao');
  _pnlFoco = document.activeElement;
  window.uiTexto(tit, o.titulo || 'Confirmar');
  if(o.html){ corpo.innerHTML = o.html; }
  else {
   corpo.textContent = '';
   String(o.corpo == null ? '' : o.corpo).split(String.fromCharCode(10))
    .forEach(function(linha){
     var p = document.createElement('p');
     p.textContent = linha;
     corpo.appendChild(p);
    });
  }
  window.uiTexto(sim, o.ok || 'Confirmar');
  window.uiTexto(nao, o.cancelar || 'Cancelar');
  sim.className = 'ui-bt ' + (o.perigo ? 'perigo' : 'pri');
  nao.style.display = o.so_ok ? 'none' : '';
  v.classList.toggle('debaixo', !!o.debaixo);
  function fim(qual){
   _pnlFecha(v);
   try{ if(qual && o.aoSim) o.aoSim(); }catch(e){}
   try{ if(!qual && o.aoNao) o.aoNao(); }catch(e){}
  }
  sim.onclick = function(){ fim(true) };
  nao.onclick = function(){ fim(false) };
  v.onclick = function(e){ if(e.target === v) fim(false) };
  v.onkeydown = function(e){
   if(e.key === 'Tab'){ window.uiPrenderFoco(v, e); return }
   if(e.key === 'Escape'){ e.preventDefault(); fim(false) }
   else if(e.key === 'Enter' && e.target !== nao){ e.preventDefault(); fim(true) }
  };
  v.classList.add('on');
  function _pnlFocar(){
   try{
    if(!v.classList.contains('vis') || v.contains(document.activeElement)) return;
    if(sim.style.display !== 'none') sim.focus();
    if(!v.contains(document.activeElement)){
     var f = v.querySelector('input,select,textarea,button,[href],[tabindex]:not([tabindex="-1"])');
     if(f) f.focus();
    }
   }catch(e){}
  }
  function _pnlAbrir(){
   if(v.classList.contains('vis')) return;
   v.classList.add('vis');
   try{ sim.focus() }catch(e){}
   setTimeout(_pnlFocar, 80); setTimeout(_pnlFocar, 280);
   try{ if(window.radaiRetraduzir) window.radaiRetraduzir() }catch(e){}
  }
  requestAnimationFrame(function(){ requestAnimationFrame(_pnlAbrir) });
  setTimeout(_pnlAbrir, 32);
  return { fechar: function(){ _pnlFecha(v) } };
 };
 window.uiConfirmar = function(o){ return window.uiPainel(o) };
 document.addEventListener('keydown', function(e){
  if(e.key !== 'Tab') return;
  var v = document.getElementById('ui-pnl-veu');
  if(!v || !v.classList.contains('vis') || v.contains(document.activeElement)) return;
  window.uiPrenderFoco(v.querySelector('.ui-pnl') || v, e);
 }, true);

 var _sinoUlt = null;
 window.uiEntregue = function(total){
  try{
   total = Number(total) || 0;
   var casa = document.querySelector('.rc-topo .dir, .ui-topo .dir');
   if(!casa) return;
   var s = document.getElementById('ui-sino');
   if(!s){
    s = document.createElement('button');
    s.type = 'button';
    s.id = 'ui-sino';
    s.className = 'ui-sino';
    s.innerHTML = '&#9679;<span class="n"></span>';
    s.onclick = function(){
     try{ localStorage.setItem('radai_entregues_visto', String(
       Number(s.getAttribute('data-total')) || 0)) }catch(e){}
     window.uiEntregue(Number(s.getAttribute('data-total')) || 0);
    };
    casa.insertBefore(s, casa.firstChild);
   }
   s.setAttribute('data-total', String(total));
   var visto = 0;
   try{ visto = Number(localStorage.getItem('radai_entregues_visto')) || 0 }
   catch(e){}
   if(visto > total){ visto = total;
    try{ localStorage.setItem('radai_entregues_visto', String(visto)) }catch(e){} }
   var n = Math.max(0, total - visto);
   s.setAttribute('data-n', String(n));
   s.querySelector('.n').textContent = String(n);
   var rot = (n === 0) ? 'nenhuma entrega nova'
     : (n + ' RTSTRUCT entregue(s) desde a sua ultima olhada');
   s.setAttribute('title', rot);
   s.setAttribute('aria-label', rot);
   if(_sinoUlt !== null && total > _sinoUlt && n > 0){
    s.classList.remove('bateu');
    void s.offsetWidth;
    s.classList.add('bateu');
   }
   _sinoUlt = total;
  }catch(e){}
 };

 window.uiPonto = function(alvo, ligado){
  try{
   var e = (typeof alvo === 'string') ? document.querySelector(alvo) : alvo;
   if(!e) return null;
   var p = null;
   for(var i = 0; i < e.children.length; i++)
    if(e.children[i].classList.contains('ui-ponto')) p = e.children[i];
   if(ligado === false){
    if(p) e.removeChild(p);
    e.classList.remove('ui-ponto-alvo');
    return null;
   }
   e.classList.add('ui-ponto-alvo');
   if(!p){
    p = document.createElement('span');
    p.className = 'ui-ponto';
    p.setAttribute('aria-hidden', 'true');
    e.appendChild(p);
   }
   return p;
  }catch(err){ return null }
 };

 window.uiAbas = function(alvo){
  try{
   var s = (typeof alvo === 'string') ? document.getElementById(alvo) : alvo;
   if(!s || s.tagName !== 'SELECT') return null;
   if(s.getAttribute('data-ui-abas-feito') === '1') return null;
   if(!s.options || s.options.length < 2) return null;
   var cx = document.createElement('div');
   cx.className = 'ui-abas';
   cx.setAttribute('role', 'tablist');
   var marca = document.createElement('span');
   marca.className = 'marca';
   cx.appendChild(marca);
   var bts = [];
   for(var i = 0; i < s.options.length; i++){
    var op = s.options[i];
    var b = document.createElement('button');
    b.type = 'button';
    b.setAttribute('role', 'tab');
    b.setAttribute('data-v', op.value);
    b.textContent = op.textContent;
    cx.appendChild(b);
    bts.push(b);
   }
   s.parentNode.insertBefore(cx, s);
   s.classList.add('ui-abas-fonte');
   s.setAttribute('data-ui-abas-feito', '1');
   function pintar(){
    var v = s.value;
    for(var i = 0; i < bts.length; i++){
     var sel = (bts[i].getAttribute('data-v') === v);
     bts[i].setAttribute('aria-selected', sel ? 'true' : 'false');
     bts[i].tabIndex = sel ? 0 : -1;
     if(sel && bts[i].offsetWidth){
      marca.style.width = bts[i].offsetWidth + 'px';
      marca.style.transform = 'translateX(' + bts[i].offsetLeft + 'px)';
     }
    }
   }
   function escolher(v){
    if(s.value === v){ pintar(); return }
    s.value = v;
    var ev;
    try{ ev = new Event('change', { bubbles: true }) }
    catch(e){ ev = document.createEvent('HTMLEvents');
              ev.initEvent('change', true, false) }
    s.dispatchEvent(ev);
    pintar();
   }
   cx.addEventListener('click', function(e){
    var b = e.target.closest ? e.target.closest('button[data-v]') : null;
    if(b) escolher(b.getAttribute('data-v'));
   });
   cx.addEventListener('keydown', function(e){
    if(e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
    var i = 0;
    for(var k = 0; k < bts.length; k++)
     if(bts[k].getAttribute('aria-selected') === 'true') i = k;
    i = (e.key === 'ArrowRight') ? (i + 1) % bts.length
                                 : (i - 1 + bts.length) % bts.length;
    e.preventDefault();
    escolher(bts[i].getAttribute('data-v'));
    try{ bts[i].focus() }catch(err){}
   });
   s.addEventListener('change', pintar);
   window.addEventListener('resize', pintar);
   pintar();
   requestAnimationFrame(pintar);
   cx._uiPintar = pintar;
   return cx;
  }catch(e){ return null }
 };
 window.uiAbasTodas = function(){
  try{
   var l = document.querySelectorAll('select[data-ui-abas]');
   for(var i = 0; i < l.length; i++) window.uiAbas(l[i]);
  }catch(e){}
 };

 window.uiShimmer = function(alvo, ligado){
  try{
   var e = (typeof alvo === 'string') ? document.getElementById(alvo) : alvo;
   if(!e) return;
   if(ligado === false) e.classList.remove('ui-shimmer');
   else e.classList.add('ui-shimmer');
  }catch(err){}
 };
 window.uiRevelar = function(alvo, comoLista){
  try{
   var e = (typeof alvo === 'string') ? document.getElementById(alvo) : alvo;
   if(!e) return;
   var c = comoLista ? 'ui-revelar-lista' : 'ui-revelar';
   e.classList.remove(c);
   void e.offsetWidth;
   e.classList.add(c);
   setTimeout(function(){ try{ e.classList.remove(c) }catch(err){} }, 700);
  }catch(err){}
 };

 var HIST = 'radai_hist', HIST_VOLTA = 'radai_hist_volta', HIST_MAX = 40;
 function histLer(){
  try{
   var p = JSON.parse(sessionStorage.getItem(HIST) || '[]');
   if(!(p instanceof Array)) return [];
   var ok = [];
   for(var i = 0; i < p.length; i++)
    if(p[i] && typeof p[i].u === 'string' && p[i].u.charAt(0) === '/')
     ok.push({u: p[i].u, t: String(p[i].t || '')});
   return ok;
  }catch(e){ return [] }
 }
 function histGravar(p){
  try{ sessionStorage.setItem(HIST, JSON.stringify(p.slice(-HIST_MAX))) }catch(e){}
 }
 function histNome(){
  var h = document.querySelector('.rc-topo[data-radai-tela], .ls-topo[data-radai-tela]');
  return h ? (h.getAttribute('data-radai-tela') || '') : null;
 }
 function histTipo(ev){
  if(ev && ev.persisted) return 'back_forward';
  try{
   var n = performance.getEntriesByType('navigation')[0];
   if(n && n.type) return n.type;
  }catch(e){}
  return 'navigate';
 }
 function histVolta(){
  var v = null;
  try{
   v = JSON.parse(sessionStorage.getItem(HIST_VOLTA) || 'null');
   sessionStorage.removeItem(HIST_VOLTA);
  }catch(e){ v = null }
  if(!v || typeof v.para !== 'string') return null;
  if(!(Date.now() - (v.em || 0) < 30000)) return null;
  return v;
 }
 function histBotao(p){
  var aqui = location.pathname;
  var bts = document.querySelectorAll('[data-radai-voltar]');
  for(var i = 0; i < bts.length; i++){
   var b = bts[i];
   if(!b.hasAttribute('data-radai-titulo0'))
    b.setAttribute('data-radai-titulo0', b.getAttribute('title') || '');
   var ant = (p.length >= 2 && p[p.length - 1].u === aqui) ? p[p.length - 2] : null;
   if(ant && ant.u !== aqui){
    b.setAttribute('href', ant.u);
    var nomeAnt = String(ant.t || ant.u);
    try{ if(window.radaiFrase) nomeAnt = window.radaiFrase(nomeAnt) }catch(e){}
    var rot = 'Voltar para %s'.replace('%s', nomeAnt);
    b.setAttribute('title', rot);
    b.setAttribute('aria-label', rot);
    b.setAttribute('data-radai-destino', 'historico');
   } else {
    var pai = b.getAttribute('data-radai-pai') || '/';
    var t0 = b.getAttribute('data-radai-titulo0') || '';
    var nomePai = b.getAttribute('data-radai-nome-pai') || '';
    if(nomePai){
     try{ if(window.radaiFrase) nomePai = window.radaiFrase(nomePai) }catch(e){}
     t0 = 'Voltar para %s'.replace('%s', nomePai);
    }
    b.setAttribute('href', pai);
    if(t0){ b.setAttribute('title', t0); b.setAttribute('aria-label', t0) }
    b.setAttribute('data-radai-destino', 'pai');
   }
  }
  if(bts.length){ try{ if(window.radaiRetraduzir) window.radaiRetraduzir() }catch(e){} }
 }
 function histRegistrar(ev){
  try{
   if(window.top !== window.self) return;
  }catch(e){ return }
  var nome = histNome();
  if(nome === null) return;
  var aqui = location.pathname, p = histLer(), tipo = histTipo(ev);
  var v = histVolta();
  var topo = p.length ? p[p.length - 1] : null;
  if(v && v.para === aqui && topo && topo.u === v.de && topo.u !== aqui){
   if(!v.sobe && p.length >= 2 && p[p.length - 2].u === aqui) p.pop();
   else p[p.length - 1] = {u: aqui, t: nome};
  } else if(topo && topo.u === aqui){
  } else if(tipo === 'back_forward'){
   var k = -1;
   for(var i = p.length - 2; i >= 0; i--) if(p[i].u === aqui){ k = i; break }
   if(k >= 0) p = p.slice(0, k + 1);
   else p.push({u: aqui, t: nome});
  } else {
   p.push({u: aqui, t: nome});
  }
  // GUARDA: a pilha nao repete tela; voltar a uma tela ja empilhada corta o que veio depois dela, e o voltar nunca alterna entre duas.
  if(p.length && p[p.length - 1].u === aqui){
   for(var j = 0; j < p.length - 1; j++)
    if(p[j].u === aqui){ p = p.slice(0, j + 1); break }
  }
  if(p.length && p[p.length - 1].u === aqui) p[p.length - 1].t = nome;
  histGravar(p);
  histBotao(p);
 }
 window.uiHistorico = function(){ return histLer() };
 document.addEventListener('DOMContentLoaded', function(){ histRegistrar(null) });
 window.addEventListener('pageshow', function(ev){
  if(ev && ev.persisted) histRegistrar(ev);
 });
 document.addEventListener('click', function(ev){
  var a = ev.target && ev.target.closest && ev.target.closest('[data-radai-voltar]');
  if(!a) return;
  if(ev.defaultPrevented || ev.button !== 0 || ev.ctrlKey || ev.metaKey
     || ev.shiftKey || ev.altKey) return;
  var p = histLer(), aqui = location.pathname;
  var temAnt = p.length >= 2 && p[p.length - 1].u === aqui
               && p[p.length - 2].u !== aqui;
  var para = temAnt ? p[p.length - 2].u
                    : (a.getAttribute('data-radai-pai') || '/');
  try{
   sessionStorage.setItem(HIST_VOLTA, JSON.stringify(
    {de: aqui, para: para, sobe: temAnt ? 0 : 1, em: Date.now()}));
  }catch(e){}
  ev.preventDefault();
  location.assign(para);
 });

 document.addEventListener('DOMContentLoaded', function(){
  try{ window.uiAbasTodas() }catch(e){}
 });
})();
</script>
"""

VEU = u"""
<div class="ui-veu" id="ui-veu"><div class="ui-cx">
 <h3><span class="ic">&#9888;</span><span id="ui-veu-tit"></span></h3>
 <div class="motivo" id="ui-veu-motivo"></div>
 <div id="ui-veu-extra"></div>
 <div class="bts"><button class="ui-bt" id="ui-veu-fechar">Entendi</button>
  <span id="ui-veu-acao"></span></div>
</div></div>
"""

MARCA_PORTAO = u"radai-portao-navegador"

PORTAO = u"""<script id="radai-portao-navegador">
(function () {
  var i = document.createElement("i");
  try { i.style.setProperty("--radai-portao", "1"); } catch (e) {}
  var falta = [];
  if (i.style.getPropertyValue("--radai-portao") !== "1") {
    falta.push("CSS custom properties");
  }
  if (typeof window.fetch !== "function") { falta.push("window.fetch"); }
  if (typeof window.Promise !== "function") { falta.push("Promise"); }
  if (falta.length === 0) { return; }
  function mostrar() {
    var b = document.body;
    if (!b) { return; }
    document.title = "ContourLab - browser not supported";
    b.setAttribute("style", "margin:0;background:#0b1320;color:#e6edf7;"
      + "font:16px/1.65 Segoe UI,Tahoma,Arial,sans-serif");
    b.innerHTML = '<div style="max-width:620px;margin:0 auto;padding:64px 24px">'
      + '<p style="margin:0;font:700 11px/1 Consolas,monospace;'
      + 'letter-spacing:.16em;color:#E8A33D">CONTOURLAB</p>'
      + '<h1 style="margin:14px 0 0;font:700 26px/1.25 inherit;color:#fff">'
      + 'This browser cannot run ContourLab</h1>'
      + '<p style="margin:16px 0 0;color:#a3b1c6">Open '
      + '<b style="color:#e6edf7">' + location.host + '</b> in Microsoft Edge '
      + 'or Google Chrome. Internet Explorer is not supported, and no part of '
      + 'the program works in it.</p>'
      + '<h2 style="margin:34px 0 0;font:700 18px/1.3 inherit;color:#fff">'
      + 'Este navegador n&#227;o roda o ContourLab</h2>'
      + '<p style="margin:12px 0 0;color:#a3b1c6">Abra '
      + '<b style="color:#e6edf7">' + location.host + '</b> no Microsoft Edge '
      + 'ou no Google Chrome. O Internet Explorer n&#227;o &#233; '
      + 'compat&#237;vel, e nenhuma parte do programa funciona nele.</p>'
      + '<p style="margin:32px 0 0;font:12px/1.7 Consolas,monospace;'
      + 'color:#6b7a92">missing / ausente: ' + falta.join(", ") + '</p>'
      + '</div>';
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mostrar, false);
  } else {
    mostrar();
  }
})();
</script>
"""


def _fim_do_charset(pagina, baixa, ini, fim):
    k = baixa.find(u"charset", ini)
    if k < 0 or k >= fim:
        return -1
    abre = baixa.rfind(u"<", ini, k)
    if abre < 0 or not baixa.startswith(u"<meta", abre):
        return -1
    fecha = pagina.find(u">", k)
    return (fecha + 1) if 0 <= fecha < fim else -1


def com_portao(pagina):
    if not pagina or MARCA_PORTAO in pagina:
        return pagina
    baixa = pagina.lower()
    cabeca = baixa.find(u"<head")
    if cabeca >= 0:
        fim_cabeca = baixa.find(u"</head>", cabeca)
        limite = fim_cabeca if fim_cabeca >= 0 else len(pagina)
        corte = _fim_do_charset(pagina, baixa, cabeca, limite)
        if corte < 0:
            fecha = pagina.find(u">", cabeca)
            corte = (fecha + 1) if fecha >= 0 else cabeca
        return pagina[:corte] + PORTAO + pagina[corte:]
    corpo = baixa.find(u"<body")
    if corpo >= 0:
        return pagina[:corpo] + PORTAO + pagina[corpo:]
    return PORTAO + pagina


MARCA_CSS = u"radai-ui-css"


COMPONENTES = u"""
.ui-fn{--ui-fn-cor:var(--accent);--ui-fn-fraco:var(--accent-fraco);
 margin:28px 0 22px}
.ui-fn-tit{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.ui-fn-tag{display:inline-flex;align-items:center;gap:11px;margin:0;
 padding:9px 18px 9px 14px;border-radius:var(--r-xl);
 border:1px solid var(--ui-fn-cor);background:var(--ui-fn-fraco);
 color:var(--ui-fn-cor);font:650 21px/1.15 var(--font-display);
 letter-spacing:-.012em}
.ui-fn-tag .ui-fn-ic{font-size:17px;line-height:1;flex:0 0 auto}
.ui-fn-tit .ui-ajuda{vertical-align:0;margin-left:0}
.ui-fn-frase{margin:14px 0 0;font-size:14px;line-height:1.6;
 color:var(--text-muted);max-width:76ch}

.ui-alerta{display:flex;align-items:center;justify-content:center;gap:9px;
 margin:34px 0 0;padding:16px 0 0;border-top:1px solid var(--line);
 font-size:12.5px;line-height:1.5;color:var(--text-muted);text-align:center}
.ui-alerta b{color:var(--text);font-weight:600}
.ui-alerta .pt{width:7px;height:7px;border-radius:50%;flex:0 0 auto;
 background:var(--warn)}
.ui-alerta.esq{justify-content:flex-start;text-align:left}

.ui-guias{--ui-guia-cor:var(--accent)}
.ui-guias-faixa{position:relative;display:flex;justify-content:center;
 align-items:flex-end;gap:4px;padding:0 12px;
 border-bottom:1px solid var(--line-strong)}
.ui-guias.esq .ui-guias-faixa{justify-content:flex-start}
.ui-guia{position:relative;z-index:1;display:inline-flex;align-items:center;
 gap:7px;min-height:36px;margin:0 0 -1px;padding:8px 16px 8px;
 border:1px solid transparent;border-bottom:0;
 border-radius:var(--r-lg) var(--r-lg) 0 0;background:transparent;
 color:var(--text-dim);font:600 12.5px/1.2 var(--font-display);
 cursor:pointer;white-space:nowrap;
 transition:color .16s ease,background-color .16s ease,border-color .16s ease}
.ui-guia::before{content:"";position:absolute;left:-1px;right:-1px;top:-1px;
 height:2px;border-radius:var(--r-lg) var(--r-lg) 0 0;background:transparent;
 transition:background-color .16s ease}
.ui-guia:hover{color:var(--text);background:var(--panel-2)}
.ui-guia[aria-selected="true"]{color:var(--text);background:var(--panel);
 border-color:var(--line-strong)}
.ui-guia[aria-selected="true"]::before{background:var(--ui-guia-cor)}
.ui-guia:focus-visible{outline:2px solid var(--accent);outline-offset:-3px}
.ui-guia .n{font-variant-numeric:tabular-nums;color:var(--text-muted);
 font-weight:500}
.ui-guias-painel{background:var(--panel);border:1px solid var(--line-strong);
 border-top:0;border-radius:0 0 var(--r-xl) var(--r-xl);padding:16px 18px}
.ui-guias-painel[hidden]{display:none}

.ui-envio{--dx:0px;position:relative;display:flex;flex-direction:column;
 align-items:center;justify-content:center;gap:8px;min-height:150px;
 padding:22px 18px;border-radius:var(--r-2xl);box-sizing:border-box;
 border:1.5px dashed var(--line-strong);background:var(--panel-2);
 color:var(--text-muted);text-align:center;cursor:pointer;outline:none;
 transition:border-color .18s ease,background-color .18s ease,
            transform .32s cubic-bezier(.22,1,.36,1)}
.ui-envio:hover,.ui-envio:focus-visible{border-color:var(--accent);
 color:var(--text)}
.ui-envio:focus-visible{box-shadow:0 0 0 3px var(--accent-fraco)}
.ui-envio-ic{display:grid;place-items:center;width:46px;height:46px;
 border-radius:50%;background:var(--accent-fraco);color:var(--accent);
 font-size:22px;transform:translateX(var(--dx));
 transition:transform .36s cubic-bezier(.22,1,.36,1)}
.ui-envio-tit{font:600 14px/1.35 var(--font-display);color:var(--text)}
.ui-envio-dica{font-size:12px;line-height:1.45;color:var(--text-dim)}
.ui-envio-bts{display:flex;gap:8px;flex-wrap:wrap;justify-content:center;
 margin-top:4px}
.ui-envio input[type=file]{display:none}
.ui-envio.sobre{border-color:var(--accent);border-style:solid;
 background:var(--accent-fraco);transform:scale(1.012)}
.ui-envio.sobre .ui-envio-ic{animation:uiEnvioSobe .9s ease-in-out infinite}
@keyframes uiEnvioSobe{0%,100%{transform:translate(var(--dx),0)}
 50%{transform:translate(var(--dx),-6px)}}
.ui-envio.chamando{border-color:var(--accent);background:var(--accent-fraco)}
.ui-envio.chamando .ui-envio-ic{animation:uiEnvioSobe .9s ease-in-out infinite}
.ui-envio.engoliu .ui-envio-ic{animation:uiEnvioEngole .5s cubic-bezier(.22,1,.36,1)}
@keyframes uiEnvioEngole{0%{transform:scale(1)}35%{transform:scale(.82)}
 100%{transform:scale(1)}}
.ui-envio-barra{width:min(320px,80%);height:4px;border-radius:99px;
 background:var(--line);overflow:hidden;display:none}
.ui-envio.enviando .ui-envio-barra{display:block}
.ui-envio-barra i{display:block;height:100%;width:100%;border-radius:99px;
 background:var(--accent);transform:scaleX(0);transform-origin:left center;
 transition:transform .2s ease}
.ui-envio-est{font-size:12px;color:var(--text-muted);min-height:16px}
.ui-envio-est b{color:var(--text)}
.ui-envio.erro{border-color:var(--perigo)}
.ui-envio.erro .ui-envio-est{color:var(--perigo)}

.ui-modal-veu{position:fixed;inset:0;z-index:5200;display:flex;
 align-items:center;justify-content:center;padding:4vh 20px;
 background:rgba(4,8,16,0);transition:background-color .22s ease}
.ui-modal-veu.vis{background:rgba(4,8,16,.66)}
.ui-modal{position:relative;display:flex;flex-direction:column;
 width:min(var(--ui-modal-l,760px),100%);max-height:92vh;box-sizing:border-box;
 background:var(--panel);color:var(--text);border:1px solid var(--line-strong);
 border-radius:var(--r-2xl);box-shadow:var(--sombra);overflow:hidden;
 opacity:0;transform:scale(.94);filter:blur(3px);
 transition:opacity .2s ease,transform .26s cubic-bezier(.22,1,.36,1),
            filter .26s cubic-bezier(.22,1,.36,1)}
.ui-modal-veu.vis .ui-modal{opacity:1;transform:none;filter:none}
.ui-modal-veu.saindo{background:rgba(4,8,16,0);transition-duration:.16s;
 pointer-events:none}
.ui-modal-veu.saindo .ui-modal{opacity:0;transform:scale(.97);
 transition:opacity .14s ease-in,transform .16s ease-in}
.ui-modal-cab{display:flex;align-items:center;gap:10px;padding:13px 14px 12px 18px;
 border-bottom:1px solid var(--line);font:600 14.5px/1.3 var(--font-display)}
.ui-modal-cab .ui-modal-tit{flex:1 1 auto;min-width:0;overflow:hidden;
 text-overflow:ellipsis;white-space:nowrap}
.ui-modal-x{display:grid;place-items:center;width:30px;height:30px;
 border-radius:var(--r-md);border:1px solid transparent;background:transparent;
 color:var(--text-dim);cursor:pointer;font-size:16px;flex:0 0 auto}
.ui-modal-x:hover{color:var(--text);border-color:var(--line-strong)}
.ui-modal-x:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.ui-modal-corpo{padding:16px 18px;overflow:auto;min-height:0}

.ui-ps-casa[hidden]{display:none}
.ui-ps{display:flex;flex-direction:column;gap:10px;min-width:0}
.ui-ps .ui-guias-faixa{justify-content:flex-start;padding:0 4px}
.ui-ps-modal .ui-modal-corpo{padding:14px 16px 16px}
.ui-cartoes{display:flex;flex-wrap:wrap;gap:12px;margin:0 0 14px}
.ui-cartoes .ui-cartao{flex:1 1 300px;max-width:none}
.ui-cartao{--ui-cartao-cor:var(--accent);--ui-cartao-fraco:var(--accent-fraco);
 display:flex;align-items:center;gap:12px;width:100%;max-width:560px;
 min-height:62px;margin:0;padding:12px 16px;box-sizing:border-box;
 text-align:left;background:var(--panel);color:var(--text);
 border:1px solid var(--line);border-radius:var(--r-xl);font:inherit;
 cursor:pointer;transition:border-color .16s ease,background-color .16s ease,
 transform .16s ease}
.ui-cartao:hover{border-color:var(--ui-cartao-cor);background:var(--panel-2);
 transform:translateY(-1px)}
.ui-cartao:active{transform:none}
.ui-cartao:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.ui-cartao[aria-expanded="true"]{border-color:var(--ui-cartao-cor)}
.ui-cartao-ic{flex:0 0 auto;width:34px;height:34px;display:grid;
 place-items:center;border-radius:50%;background:var(--ui-cartao-fraco);
 color:var(--ui-cartao-cor);font:700 14px/1 var(--font-display)}
.ui-cartao-ic svg{width:17px;height:17px}
.ui-cartao-tx{flex:1 1 auto;min-width:0;display:flex;flex-direction:column;gap:3px}
.ui-cartao-tit{font:600 13.5px/1.3 var(--font-display);color:var(--text)}
.ui-cartao-rot{font-size:12px;line-height:1.45;color:var(--text-dim);
 overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ui-cartao.tem .ui-cartao-rot{color:var(--text-muted)}
.ui-cartao.tem .ui-cartao-ic{background:var(--ui-cartao-cor);color:var(--bg-0)}
.ui-cartao-seta{flex:0 0 auto;color:var(--text-dim);display:grid;place-items:center}
.ui-cartao-seta svg{width:16px;height:16px}

.ui-visor{display:grid;grid-template-columns:minmax(0,1fr) 230px;gap:14px;
 min-height:0}
.ui-visor-palco{display:flex;flex-direction:column;gap:8px;min-width:0}
.ui-visor-barra{display:flex;gap:6px;align-items:center;flex-wrap:wrap}
.ui-visor-jan{display:flex;gap:6px;flex-wrap:wrap}
.ui-visor-jan button,.ui-visor-ajustar{padding:6px 12px;border-radius:var(--r-md);
 border:1px solid var(--line-strong);background:var(--panel-2);
 color:var(--text-muted);font:600 12px/1 var(--font-display);cursor:pointer}
.ui-visor-jan button[aria-pressed="true"],.ui-visor-ajustar[aria-pressed="true"]{
 background:var(--accent-fraco);border-color:var(--accent);color:var(--text)}
.ui-visor-ajustar{margin-left:auto}
.ui-visor-quadro{position:relative;display:flex;justify-content:center;gap:8px;
 min-height:0}
.ui-visor-img{position:relative;flex:0 1 auto;width:min(100%,62vh);min-width:0;
 aspect-ratio:1/1;background:var(--img-fundo);border-radius:var(--r-lg);overflow:hidden;
 display:grid;place-items:center}
.ui-visor-img img{width:100%;height:100%;object-fit:contain;display:block;
 image-rendering:auto;user-select:none;-webkit-user-drag:none;
 transform-origin:center center}
.ui-visor-rol{writing-mode:vertical-lr;direction:rtl;width:18px;margin:0;
 accent-color:var(--accent);cursor:ns-resize}
.ui-visor-pos{position:absolute;left:10px;bottom:9px;padding:3px 8px;
 border-radius:var(--r-sm);background:rgba(0,0,0,.55);color:var(--img-texto);
 font:500 11.5px/1.2 var(--font-mono);font-variant-numeric:tabular-nums}
.ui-visor-cab{border:1px solid var(--line);border-radius:var(--r-lg);
 background:var(--panel-2);padding:10px 12px;overflow:auto;max-height:62vh;
 font-size:12px}
.ui-visor-cab dl{margin:0;display:grid;grid-template-columns:minmax(0,1fr);
 gap:1px 0}
.ui-visor-cab dt{color:var(--text-dim);font-size:11px;margin-top:6px}
.ui-visor-cab dt:first-child{margin-top:0}
.ui-visor-cab dd{margin:0;color:var(--text);font-family:var(--font-mono);
 font-size:11.5px;overflow-wrap:anywhere}
@media (max-width:760px){.ui-visor{grid-template-columns:1fr}}

.ui-morfo{position:fixed;z-index:5100;width:var(--ui-morfo-l,340px);
 max-width:calc(100vw - 24px);max-height:70vh;overflow:auto;box-sizing:border-box;
 background:var(--panel);color:var(--text);border:1px solid var(--line-strong);
 border-radius:var(--r-xl);box-shadow:var(--sombra);padding:12px 14px;
 clip-path:inset(var(--c-t,0) var(--c-d,0) var(--c-b,0) var(--c-e,0) round var(--r-lg));
 transition:clip-path .3s cubic-bezier(.22,1,.36,1),opacity .18s ease}
.ui-morfo.aberto{clip-path:inset(0 0 0 0 round var(--r-xl))}
.ui-morfo > .dentro{opacity:0;transform:translateY(-4px);
 transition:opacity .16s ease .08s,transform .24s cubic-bezier(.22,1,.36,1) .06s}
.ui-morfo.aberto > .dentro{opacity:1;transform:none}
.ui-morfo.fechando{opacity:0}
.ui-morfo dl{margin:0;display:grid;grid-template-columns:auto 1fr;gap:5px 10px;
 font-size:12px}
.ui-morfo dt{color:var(--text-dim);white-space:nowrap}
.ui-morfo dd{margin:0;color:var(--text);overflow-wrap:anywhere}
.ui-mais{display:inline-grid;place-items:center;width:24px;height:24px;
 border-radius:var(--r-md);border:1px solid var(--line-strong);
 background:var(--panel-2);color:var(--text-muted);cursor:pointer;padding:0;
 font-size:14px;line-height:1;flex:0 0 auto}
.ui-mais .ui-ic{margin:0;transition:transform .26s cubic-bezier(.22,1,.36,1)}
.ui-mais:hover{color:var(--accent);border-color:var(--accent)}
.ui-mais[aria-expanded="true"]{color:var(--accent);border-color:var(--accent);
 background:var(--accent-fraco)}
.ui-mais[aria-expanded="true"] .ui-ic{transform:rotate(45deg)}
.ui-mais:focus-visible{outline:2px solid var(--accent);outline-offset:2px}

.ui-organico-alvo{position:relative}
.ui-organico{--ui-org-cor:var(--accent);position:absolute;inset:0;z-index:4;
 display:grid;place-items:center;overflow:hidden;border-radius:inherit;
 background:var(--panel-2);opacity:0;transition:opacity .24s ease}
.ui-organico.vis{opacity:1}
.ui-organico::before,.ui-organico::after{content:"";position:absolute;
 width:70%;height:70%;border-radius:50%;filter:blur(38px);opacity:.55;
 background:radial-gradient(circle at 50% 50%,var(--ui-org-cor),transparent 68%)}
.ui-organico::before{left:-8%;top:-12%;animation:uiOrgA 7.5s ease-in-out infinite alternate}
.ui-organico::after{right:-10%;bottom:-14%;
 background:radial-gradient(circle at 50% 50%,var(--mod-bridge),transparent 66%);
 animation:uiOrgB 9s ease-in-out infinite alternate}
@keyframes uiOrgA{0%{transform:translate(0,0) scale(1)}
 50%{transform:translate(22%,18%) scale(1.18)}
 100%{transform:translate(38%,6%) scale(.92)}}
@keyframes uiOrgB{0%{transform:translate(0,0) scale(1.05)}
 50%{transform:translate(-24%,-12%) scale(.9)}
 100%{transform:translate(-36%,-26%) scale(1.15)}}
.ui-organico-txt{position:relative;z-index:1;font:500 13px/1.4 var(--font-display);
 text-align:center;padding:0 16px}

.ui-acervo{position:relative;overflow:auto;max-height:420px;
 border:1px solid var(--line);border-radius:var(--r-lg);background:var(--panel);
 scrollbar-color:var(--line-strong) transparent}
.ui-acervo > .ui-esqueleto{margin:10px 12px}
.ui-acervo table{width:100%;border-collapse:collapse;font-size:12.5px}
.ui-acervo thead th{position:sticky;top:0;z-index:2;background:var(--panel);
 text-align:left;padding:7px 8px;font:400 9.5px/1.3 var(--font-mono);
 letter-spacing:.11em;text-transform:uppercase;color:var(--text-dim);
 border-bottom:1px solid var(--line);white-space:normal;vertical-align:bottom}
.ui-acervo td{padding:6px 8px;border-bottom:1px solid var(--line);
 white-space:nowrap;color:var(--text-muted)}
.ui-acervo tbody tr:hover{background:var(--accent-fraco)}
.ui-acervo tbody tr.on{background:var(--accent-fraco);
 box-shadow:inset 3px 0 0 var(--accent);--text-dim:var(--text-muted)}
.ui-acervo .num{font-family:var(--font-mono);text-align:right;
 font-variant-numeric:tabular-nums}
.ui-acervo .mono{font-family:var(--font-mono);color:var(--text-dim)}
.ui-acervo td.ua-nome{color:var(--text)}
.ui-acervo .ua-nome [data-c="nome"]{font-weight:600}
.ui-acervo .ua-tasks{max-width:170px;overflow:hidden;text-overflow:ellipsis;
 font-family:var(--font-mono);font-size:11px}
.ui-acervo .ua-acao{position:sticky;right:0;z-index:1;width:1%;
 background:var(--panel);text-align:right;box-shadow:-1px 0 0 var(--line)}
.ui-acervo thead th.ua-acao{z-index:3}
.ui-acervo tbody tr:hover td.ua-acao{background:var(--panel-2)}
.ui-acervo .ua-acao .ui-bt{padding:5px 12px;font-size:12px}
.ui-acervo tr.ua-falta td{opacity:.55}
.ui-acervo .ua-esq{display:inline-block;width:72px;height:10px;
 min-height:0;vertical-align:middle}
.ui-acervo .ua-mais{display:none;margin-top:3px;font-weight:400;font-size:11.5px;
 line-height:1.5;color:var(--text-dim);white-space:normal}
.ui-acervo .ua-mais .ua-m{display:inline-block;margin-right:12px}
.ui-acervo .ua-mais .ua-m:empty{display:none}
.ui-acervo.compacto .ua-x{display:none}
.ui-acervo.compacto .ua-mais{display:block}
.ui-acervo.compacto td.ua-nome{white-space:normal;min-width:180px;max-width:300px}
.ui-acervo .ua-parcial{display:inline-block;padding:0 5px;margin-left:4px;
 border:1px solid var(--warn);border-radius:4px;color:var(--warn);
 font-size:10.5px;line-height:1.5;cursor:help}
.ui-acervo .ua-faltou{display:block;margin-top:2px;font-size:10.5px;line-height:1.4;
 color:var(--text-dim);white-space:normal}
.ui-acervo .ua-msg{margin:0;padding:12px 14px;font-size:12.5px;line-height:1.6;
 color:var(--text-dim)}
.ui-acervo .ua-msg.ruim{color:var(--perigo)}
.ui-acervo .ua-sr{position:absolute;width:1px;height:1px;overflow:hidden;
 clip:rect(0 0 0 0);white-space:nowrap}

.ui-seg{position:relative;display:inline-flex;align-items:stretch;gap:2px;
 padding:3px;margin:0;border-radius:var(--r-md);background:var(--panel-2);
 border:1px solid var(--line-strong);vertical-align:middle;isolation:isolate;
 box-sizing:border-box;max-width:100%}
.ui-seg-ind{position:absolute;top:3px;bottom:3px;left:0;width:0;z-index:0;
 border-radius:calc(var(--r-md) - 2px);background:var(--accent);
 pointer-events:none;
 transition:transform .3s cubic-bezier(.22,1,.36,1),width .3s cubic-bezier(.22,1,.36,1)}
.ui-seg.sem-salto .ui-seg-ind{transition:none}
.ui-seg>button{position:relative;z-index:1;display:inline-flex;align-items:center;
 justify-content:center;gap:6px;margin:0;border:0;border-radius:calc(var(--r-md) - 2px);
 background:transparent;color:var(--text-muted);cursor:pointer;padding:6px 13px;
 font:500 12.5px/1.2 var(--font-display,inherit);white-space:nowrap;
 transition:color .18s ease}
.ui-seg>button:hover:not(:disabled){color:var(--text)}
.ui-seg>button[aria-checked="true"],
.ui-seg>button[aria-checked="true"]:hover{color:var(--bg-0);font-weight:600}
.ui-seg>button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.ui-seg>button:disabled{cursor:not-allowed}
.ui-seg>button .ui-ic{margin:0;font-size:15px}
.ui-seg .ui-ic + *{margin-left:0}
.ui-seg-rot{position:relative;display:inline-block}
.ui-seg-mex{position:absolute;left:0;top:0;right:0;white-space:nowrap;
 overflow:hidden;visibility:hidden}
.ui-seg-rot.mexendo .ui-seg-txt{visibility:hidden}
.ui-seg-rot.mexendo .ui-seg-mex{visibility:visible}
.ui-seg-fonte{position:absolute;width:1px;height:1px;padding:0;margin:-1px;
 overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;border:0}
.ui-seg-balao{position:fixed;z-index:70;left:0;top:0;
 max-width:min(340px,calc(100vw - 32px));padding:10px 12px;
 border-radius:var(--r-md);border:1px solid var(--line-strong);
 background:var(--panel);color:var(--text-muted);font-size:12.5px;
 line-height:1.5;text-align:left;white-space:normal;box-shadow:var(--sombra);
 pointer-events:none;opacity:0;visibility:hidden;transform:translateY(-4px);
 transition:opacity .14s ease,transform .18s cubic-bezier(.22,1,.36,1),
            visibility 0s linear .18s}
.ui-seg-balao.on{opacity:1;visibility:visible;transform:none;
 transition:opacity .14s ease,transform .18s cubic-bezier(.22,1,.36,1),
            visibility 0s}
.ui-seg-balao .ui-seg-bt{display:block;margin:0 0 3px;color:var(--text);
 font-weight:700;letter-spacing:.03em}

@media (prefers-reduced-motion:reduce){
 .ui-seg-ind,.ui-seg>button,.ui-seg-balao,.ui-seg-balao.on{transition:none}
 .ui-seg-balao{transform:none}
 .ui-guia,.ui-guia::before{transition:none}
 .ui-envio,.ui-envio-ic{transition:none}
 .ui-envio.sobre{transform:none}
 .ui-envio.sobre .ui-envio-ic,.ui-envio.engoliu .ui-envio-ic,
 .ui-envio.chamando .ui-envio-ic{animation:none}
 .ui-modal,.ui-modal-veu{transition:none}
 .ui-modal{transform:none;filter:none}
 .ui-cartao{transition:none}
 .ui-cartao:hover{transform:none}
 .ui-morfo,.ui-morfo > .dentro,.ui-mais .ui-ic{transition:none}
 .ui-organico::before,.ui-organico::after{animation:none}
 .ui-organico{transition:none}
}
"""


COMPONENTES_JS = u"""
<script id="radai-ui-comp-js">
(function(){
 function $(id){ return document.getElementById(id) }
 function esc(s){ return String(s == null ? '' : s).replace(/&/g,'&amp;')
  .replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;') }
 function ico(nome){
  var t = document.getElementById('ui-ico-' + nome);
  return t ? t.innerHTML : '';
 }
 function traduzir(){ try{ if(window.radaiRetraduzir) window.radaiRetraduzir() }catch(e){} }
 function frase(txt){ return '<span data-radai-frase>' + esc(txt) + '</span>' }

 function guiaContainer(t){ return t && t.closest ? t.closest('.ui-guias') : null }
 function guiaAbas(cx){
  var f = cx.querySelector('.ui-guias-faixa');
  return f ? Array.prototype.slice.call(f.querySelectorAll('.ui-guia')) : [];
 }
 window.uiGuia = function(alvo, chave){
  try{
   var cx, aba;
   if(typeof alvo === 'string') cx = $(alvo);
   else if(alvo && alvo.classList && alvo.classList.contains('ui-guia')){
    aba = alvo; cx = guiaContainer(alvo);
   } else cx = alvo;
   if(!cx) return null;
   var abas = guiaAbas(cx);
   if(!aba){
    for(var i = 0; i < abas.length; i++)
     if(abas[i].getAttribute('data-guia') === chave) aba = abas[i];
   }
   if(!aba) return null;
   var k = aba.getAttribute('data-guia');
   abas.forEach(function(a){
    var sel = (a === aba);
    a.setAttribute('aria-selected', sel ? 'true' : 'false');
    a.tabIndex = sel ? 0 : -1;
    var p = $(a.getAttribute('aria-controls'));
    if(p) p.hidden = !sel;
   });
   cx.setAttribute('data-ativa', k);
   if(cx.hasAttribute('data-lembrar') && cx.id){
    try{ sessionStorage.setItem('radai_guia_' + cx.id, k) }catch(e){}
   }
   var ev;
   try{ ev = new CustomEvent('ui-guia', {bubbles:true, detail:{chave:k}}) }
   catch(e){ ev = document.createEvent('CustomEvent');
             ev.initCustomEvent('ui-guia', true, false, {chave:k}) }
   cx.dispatchEvent(ev);
   return k;
  }catch(e){ return null }
 };
 document.addEventListener('click', function(e){
  var a = e.target && e.target.closest ? e.target.closest('.ui-guia') : null;
  if(a && guiaContainer(a)) window.uiGuia(a);
 });
 document.addEventListener('keydown', function(e){
  var a = e.target && e.target.closest ? e.target.closest('.ui-guia') : null;
  if(!a) return;
  var cx = guiaContainer(a); if(!cx) return;
  var abas = guiaAbas(cx), i = abas.indexOf(a), j = -1;
  if(e.key === 'ArrowRight') j = (i + 1) % abas.length;
  else if(e.key === 'ArrowLeft') j = (i - 1 + abas.length) % abas.length;
  else if(e.key === 'Home') j = 0;
  else if(e.key === 'End') j = abas.length - 1;
  if(j < 0) return;
  e.preventDefault();
  window.uiGuia(abas[j]);
  try{ abas[j].focus() }catch(err){}
 });
 document.addEventListener('DOMContentLoaded', function(){
  var l = document.querySelectorAll('.ui-guias[data-lembrar]');
  for(var i = 0; i < l.length; i++){
   var k = null;
   try{ k = sessionStorage.getItem('radai_guia_' + l[i].id) }catch(e){}
   if(k) window.uiGuia(l[i], k);
  }
 });

 window.uiModal = function(o){
  o = o || {};
  var antes = document.activeElement;
  var v = document.createElement('div');
  v.className = 'ui-modal-veu';
  var m = document.createElement('div');
  m.className = 'ui-modal' + (o.classe ? ' ' + o.classe : '');
  m.setAttribute('role', 'dialog');
  m.setAttribute('aria-modal', 'true');
  var idt = 'ui-modal-t' + Math.floor(Math.random() * 1e9);
  m.setAttribute('aria-labelledby', idt);
  if(o.largura) m.style.setProperty('--ui-modal-l', o.largura + 'px');
  m.innerHTML = '<div class="ui-modal-cab"><span class="ui-modal-tit" id="' + idt
   + '"></span><button type="button" class="ui-modal-x" title="fechar"'
   + ' aria-label="fechar">' + ico('fechar') + '</button></div>'
   + '<div class="ui-modal-corpo"></div>';
  var tit = m.querySelector('.ui-modal-tit');
  tit.textContent = o.titulo || '';
  tit.setAttribute('data-radai-frase', '');
  var corpo = m.querySelector('.ui-modal-corpo');
  if(o.no) corpo.appendChild(o.no); else if(o.html) corpo.innerHTML = o.html;
  v.appendChild(m);
  document.body.appendChild(v);
  if(o.origem && o.origem.getBoundingClientRect){
   var r = o.origem.getBoundingClientRect(), q = m.getBoundingClientRect();
   m.style.transformOrigin = Math.round(r.left + r.width / 2 - q.left) + 'px '
    + Math.round(r.top + r.height / 2 - q.top) + 'px';
  }
  var aberto = true;
  function fechar(){
   if(!aberto) return; aberto = false;
   v.classList.add('saindo'); v.classList.remove('vis');
   setTimeout(function(){ if(v.parentNode) v.parentNode.removeChild(v) }, 200);
   document.removeEventListener('keydown', tecla, true);
   try{ if(antes && antes.focus) antes.focus() }catch(e){}
   try{ if(o.aoFechar) o.aoFechar() }catch(e){}
  }
  function tecla(e){
   if(!aberto) return;
   if(e.key === 'Escape'){ e.preventDefault(); e.stopPropagation(); fechar() }
   else if(e.key === 'Tab' && window.uiPrenderFoco) window.uiPrenderFoco(m, e);
   else if(o.aoTecla) o.aoTecla(e);
  }
  document.addEventListener('keydown', tecla, true);
  v.addEventListener('mousedown', function(e){ if(e.target === v) fechar() });
  m.querySelector('.ui-modal-x').addEventListener('click', fechar);
  function abrir(){
   if(v.classList.contains('vis') || !aberto) return;
   v.classList.add('vis');
   try{ (m.querySelector('[autofocus]') || m.querySelector('.ui-modal-x')).focus() }catch(e){}
   traduzir();
  }
  requestAnimationFrame(function(){ requestAnimationFrame(abrir) });
  setTimeout(abrir, 32);
  return { fechar: fechar, corpo: corpo, caixa: m, veu: v };
 };

 var UI_PS = {};
 function psCartoes(id){
  return Array.prototype.slice.call(
   document.querySelectorAll('[data-ui-ps-abre="' + id + '"]'));
 }
 function psExpandido(id, sim){
  psCartoes(id).forEach(function(c){ c.setAttribute('aria-expanded', sim ? 'true' : 'false') });
 }
 window.uiPopupSerie = function(id, o){
  var r = UI_PS[id] || (UI_PS[id] = {o: {}, modal: null, ctx: ''});
  if(o) for(var k in o) if(Object.prototype.hasOwnProperty.call(o, k)) r.o[k] = o[k];
  function casa(){ return $(id + '_casa') }
  function abrir(origem, ctx){
   var no = $(id); if(!no) return false;
   r.ctx = (ctx == null) ? '' : String(ctx);
   no.setAttribute('data-contexto', r.ctx);
   if(r.o.guia) window.uiGuia(no.querySelector('.ui-guias'), r.o.guia);
   try{ if(r.o.aoAbrir) r.o.aoAbrir(r.ctx, no) }catch(e){}
   if(r.modal){ psExpandido(id, true); return true }
   if(!window.uiModal){ var c0 = casa(); if(c0) c0.hidden = false; return true }
   var cartao = (origem && origem.getBoundingClientRect) ? origem : psCartoes(id)[0];
   r.modal = window.uiModal({titulo: r.o.titulo || no.getAttribute('data-titulo') || '',
    no: no, classe: 'ui-ps-modal', origem: cartao || null,
    largura: Number(r.o.largura || no.getAttribute('data-largura')) || 1180,
    aoFechar: function(){
     r.modal = null; psExpandido(id, false);
     // GUARDA: o conteúdo só volta para casa depois da saída; reaberto antes disso, fica no novo.
     setTimeout(function(){ var c = casa(); if(!r.modal && c && no.parentNode !== c) c.appendChild(no) }, 220);
     try{ if(r.o.aoFechar) r.o.aoFechar(r.ctx) }catch(e){}
    }});
   psExpandido(id, true);
   return true;
  }
  function fechar(){
   if(r.modal){ r.modal.fechar(); return }
   var c = casa(); if(c && !c.hidden){ c.hidden = true; try{ if(r.o.aoFechar) r.o.aoFechar(r.ctx) }catch(e){} }
  }
  return {abrir: abrir, fechar: fechar, aberto: function(){ return !!r.modal },
          contexto: function(){ return r.ctx }, caixa: function(){ return $(id) }};
 };
 window.uiCartaoRotulo = function(alvo, texto, frase){
  var c = (typeof alvo === 'string') ? $(alvo) : alvo;
  if(!c) return;
  var rot = c.querySelector('.ui-cartao-rot'); if(!rot) return;
  if(!rot.hasAttribute('data-vazio')) rot.setAttribute('data-vazio', rot.innerHTML);
  if(texto){
   rot.innerHTML = frase ? '<span data-radai-frase></span>' : '<span translate="no"></span>';
   rot.firstChild.textContent = String(texto);
   c.classList.add('tem');
   traduzir();
  } else {
   rot.innerHTML = rot.getAttribute('data-vazio') || '';
   c.classList.remove('tem');
  }
 };
 document.addEventListener('click', function(e){
  var c = e.target && e.target.closest ? e.target.closest('[data-ui-ps-abre]') : null;
  if(!c || c.disabled || c.getAttribute('aria-disabled') === 'true') return;
  e.preventDefault();
  window.uiPopupSerie(c.getAttribute('data-ui-ps-abre'))
   .abrir(c, c.getAttribute('data-ui-ps-ctx') || '');
 });
 document.addEventListener('DOMContentLoaded', function(){
  // GUARDA: depois de todo DOMContentLoaded: a tela já disse se chegou com série escolhida.
  setTimeout(function(){
   Array.prototype.forEach.call(document.querySelectorAll('[data-ui-ps][data-sozinho]'), function(no){
    var r = UI_PS[no.id], s = r ? r.o.sozinho : true;
    if(s === false) return;
    if(typeof s === 'function'){ try{ if(!s()) return }catch(e){ return } }
    window.uiPopupSerie(no.id).abrir();
   });
  }, 0);
 });

 window.uiVisor = function(o){
  o = o || {};
  var total = Math.max(1, Number(o.total) || 1);
  var i = Math.min(total - 1, Math.max(0, o.inicial == null
          ? Math.floor((total - 1) / 2) : Number(o.inicial)));
  var jans = o.janelas || [{chave:'mediastino', rotulo:'mediastino'},
                           {chave:'pulmao', rotulo:'pulmão'},
                           {chave:'osso', rotulo:'osso'}];
  var jan = o.janela || jans[0].chave;
  var raiz = document.createElement('div');
  raiz.className = 'ui-visor';
  var bts = jans.map(function(j){
   return '<button type="button" data-jan="' + esc(j.chave) + '" aria-pressed="'
    + (j.chave === jan ? 'true' : 'false') + '">' + frase(j.rotulo) + '</button>';
  }).join('');
  raiz.innerHTML = '<div class="ui-visor-palco"><div class="ui-visor-barra">'
   + '<div class="ui-visor-jan" role="group" aria-label="janela">' + bts + '</div>'
   + '<button type="button" class="ui-visor-ajustar" aria-pressed="false">'
   + frase('ajustar') + '</button></div>'
   + '<div class="ui-visor-quadro"><div class="ui-visor-img" tabindex="0">'
   + '<img alt=""><span class="ui-visor-pos"></span></div>'
   + '<input type="range" class="ui-visor-rol" min="0" max="' + (total - 1)
   + '" step="1" aria-label="corte"></div></div>'
   + '<aside class="ui-visor-cab"><dl></dl></aside>';
  var img = raiz.querySelector('img'), pos = raiz.querySelector('.ui-visor-pos');
  var rol = raiz.querySelector('.ui-visor-rol'), quadro = raiz.querySelector('.ui-visor-img');
  var dl = raiz.querySelector('dl'), btAj = raiz.querySelector('.ui-visor-ajustar');
  var zoomInicial = Number(window.UI_VISOR_ZOOM_INICIAL) || 1, zoom = zoomInicial;
  function aplicarZoom(){
   img.style.transform = (zoom === 1) ? '' : 'scale(' + zoom + ')';
   btAj.setAttribute('aria-pressed', zoom === 1 ? 'true' : 'false');
  }
  function ajustar(){ zoom = 1; aplicarZoom() }
  btAj.addEventListener('click', function(){
   zoom = (zoom === 1) ? zoomInicial : 1; aplicarZoom();
  });
  aplicarZoom();
  function cabecalho(){
   var c = (typeof o.cabecalho === 'function') ? o.cabecalho(i) : (o.cabecalho || []);
   dl.innerHTML = (c || []).map(function(par){
    return '<dt>' + frase(par[0]) + '</dt><dd>' + esc(par[1]) + '</dd>';
   }).join('');
  }
  var primeiro = true;
  function pintar(){
   rol.value = String(i);
   pos.textContent = (i + 1) + ' / ' + total;
   var u = o.src ? o.src(i, jan) : '';
   if(primeiro && window.uiCarregando) window.uiCarregando(quadro, true, o.carregando || '');
   img.onload = function(){
    if(primeiro && window.uiCarregando) window.uiCarregando(quadro, false);
    primeiro = false;
   };
   img.src = u;
   if(o.src){
    [i - 1, i + 1].forEach(function(k){
     if(k >= 0 && k < total){ var p = new Image(); p.src = o.src(k, jan) }
    });
   }
   if(typeof o.cabecalho === 'function') cabecalho();
  }
  function ir(k){
   k = Math.min(total - 1, Math.max(0, k));
   if(k === i) return; i = k; pintar();
  }
  var cranial = (o.cranial === 1 || o.cranial === -1) ? o.cranial : 0;
  function rumoCaudal(d){ return cranial ? -d * cranial : d }
  quadro.addEventListener('wheel', function(e){
   e.preventDefault();
   if(!e.deltaY) return;
   ir(i + rumoCaudal(e.deltaY > 0 ? 1 : -1));
  }, {passive:false});
  rol.addEventListener('input', function(){ ir(Number(rol.value)) });
  raiz.querySelector('.ui-visor-jan').addEventListener('click', function(e){
   var b = e.target.closest ? e.target.closest('button[data-jan]') : null;
   if(!b) return;
   jan = b.getAttribute('data-jan');
   Array.prototype.forEach.call(raiz.querySelectorAll('button[data-jan]'), function(x){
    x.setAttribute('aria-pressed', x === b ? 'true' : 'false');
   });
   pintar();
  });
  var md = window.uiModal({titulo: o.titulo || '', no: raiz, largura: o.largura || 980,
   origem: o.origem, aoFechar: o.aoFechar,
   aoTecla: function(e){
    if(e.key === 'ArrowDown' || e.key === 'PageDown'){ e.preventDefault(); ir(i + rumoCaudal(1)) }
    else if(e.key === 'ArrowUp' || e.key === 'PageUp'){ e.preventDefault(); ir(i + rumoCaudal(-1)) }
    else if(e.key === 'Home'){ e.preventDefault(); ir(0) }
    else if(e.key === 'End'){ e.preventDefault(); ir(total - 1) }
   }});
  cabecalho();
  pintar();
  return { fechar: md.fechar, ir: ir, corte: function(){ return i },
           janela: function(){ return jan }, cabecalho: cabecalho,
           zoom: function(){ return zoom }, ajustar: ajustar,
           definirSentido: function(c){ cranial = (c === 1 || c === -1) ? c : 0 } };
 };

 var _morfo = null;
 function morfoFechar(){
  var m = _morfo; if(!m) return; _morfo = null;
  m.botao.setAttribute('aria-expanded', 'false');
  var p = m.painel;
  p.classList.remove('aberto'); p.classList.add('fechando');
  setTimeout(function(){ if(p.parentNode) p.parentNode.removeChild(p) }, 300);
  try{ if(m.o.aoFechar) m.o.aoFechar() }catch(e){}
 }
 window.uiMorfar = function(botao, o){
  o = o || {};
  if(!botao) return null;
  if(_morfo && _morfo.botao === botao){ morfoFechar(); return null }
  morfoFechar();
  var p = document.createElement('div');
  p.className = 'ui-morfo';
  p.setAttribute('role', 'dialog');
  if(o.largura) p.style.setProperty('--ui-morfo-l', o.largura + 'px');
  var d = document.createElement('div');
  d.className = 'dentro';
  if(o.no) d.appendChild(o.no); else d.innerHTML = o.html || '';
  p.appendChild(d);
  document.body.appendChild(p);
  var r = botao.getBoundingClientRect(), q = p.getBoundingClientRect();
  var L = (o.lado === 'esq') ? r.left : (r.right - q.width);
  L = Math.max(12, Math.min(L, window.innerWidth - q.width - 12));
  var T = r.bottom + 6;
  if(T + q.height > window.innerHeight - 12) T = Math.max(12, r.top - q.height - 6);
  p.style.left = Math.round(L) + 'px'; p.style.top = Math.round(T) + 'px';
  p.style.setProperty('--c-t', Math.max(0, r.top - T) + 'px');
  p.style.setProperty('--c-e', Math.max(0, r.left - L) + 'px');
  p.style.setProperty('--c-d', Math.max(0, (L + q.width) - r.right) + 'px');
  p.style.setProperty('--c-b', Math.max(0, (T + q.height) - r.bottom) + 'px');
  botao.setAttribute('aria-expanded', 'true');
  _morfo = {botao: botao, painel: p, o: o};
  void p.offsetWidth;
  requestAnimationFrame(function(){ p.classList.add('aberto') });
  setTimeout(function(){ p.classList.add('aberto') }, 40);
  traduzir();
  return { fechar: morfoFechar, painel: p };
 };
 document.addEventListener('mousedown', function(e){
  if(!_morfo) return;
  if(_morfo.painel.contains(e.target) || _morfo.botao.contains(e.target)) return;
  morfoFechar();
 });
 document.addEventListener('keydown', function(e){
  if(e.key === 'Escape' && _morfo){
   var b = _morfo.botao; morfoFechar();
   try{ b.focus() }catch(err){}
  }
 });

 window.UI_CARREGANDO_MINIMO_MS = 2000;
 window.UI_VISOR_ZOOM_INICIAL = 1.25;
 window.uiCarregando = function(alvo, ligado, texto){
  try{
   var e = (typeof alvo === 'string') ? $(alvo) : alvo;
   if(!e) return null;
   var c = null;
   for(var k = 0; k < e.children.length; k++)
    if(e.children[k].classList.contains('ui-organico')) c = e.children[k];
   if(ligado === false){
    if(!c){ e.removeAttribute('aria-busy'); return null }
    c._uiLigado = false;
    var tira = c;
    // GUARDA: o carregamento fica na tela pelo menos o minimo; desligar antes so agenda a saida.
    var falta = Math.max(0, (Number(window.UI_CARREGANDO_MINIMO_MS) || 0)
                            - (Date.now() - (c._uiDesde || 0)));
    clearTimeout(c._uiApaga);
    c._uiApaga = setTimeout(function(){
     if(tira._uiLigado) return;
     tira.classList.remove('vis');
     tira._uiDesde = 0;
     e.removeAttribute('aria-busy');
     tira._uiTira = setTimeout(function(){
      if(tira.parentNode && !tira._uiLigado) tira.parentNode.removeChild(tira)
     }, 260);
    }, falta);
    return null;
   }
   if(getComputedStyle(e).position === 'static') e.classList.add('ui-organico-alvo');
   // GUARDA: religar antes da saída terminar cancela a remoção pendente.
   if(c){ clearTimeout(c._uiTira); clearTimeout(c._uiApaga); c._uiTira = null;
          c._uiLigado = true; if(!c._uiDesde) c._uiDesde = Date.now();
          c.classList.add('vis') }
   if(!c){
    c = document.createElement('div');
    c.className = 'ui-organico';
    c.setAttribute('role', 'status');
    c.innerHTML = '<span class="ui-organico-txt ui-shimmer" data-radai-frase></span>';
    e.appendChild(c);
    c._uiLigado = true;
    c._uiDesde = Date.now();
    var nova = c;
    // GUARDA: a entrada atrasada não reacende o que já foi desligado.
    requestAnimationFrame(function(){ if(nova._uiLigado) nova.classList.add('vis') });
    setTimeout(function(){ if(nova._uiLigado) nova.classList.add('vis') }, 30);
   }
   if(window.uiTexto) window.uiTexto(c.firstChild, texto || '');
   else c.firstChild.textContent = texto || '';
   e.setAttribute('aria-busy', 'true');
   traduzir();
   return c;
  }catch(err){ return null }
 };

 var UA_COLUNAS = ['Data do exame', 'Paciente', 'ID', 'Modalidade', 'Cortes',
                   'Espessura', 'Estruturas', 'Modo', 'Tasks', 'Contornada em',
                   'Levou'];
 var UA_EXTRAS = {'Modo': 1, 'Tasks': 1, 'Contornada em': 1, 'Levou': 1};
 var UA_MODO = {fast: 'FAST', auto: 'AUTO', perso: 'PERSONALIZADO',
                personalizado: 'PERSONALIZADO'};
 var UA_LOTE = 6;
 function uaData(d){
  d = String(d == null ? '' : d).trim();
  return /^[0-9]{8}/.test(d) ? (d.slice(6, 8) + '/' + d.slice(4, 6) + '/' + d.slice(0, 4)) : d;
 }
 function uaDuracao(s){
  s = Math.max(0, parseInt(s, 10) || 0);
  if(s < 60) return s + 's';
  var m = Math.floor(s / 60);
  if(m < 60) return m + 'min ' + (s % 60) + 's';
  return Math.floor(m / 60) + 'h ' + (m % 60) + 'min';
 }
 function uaPost(url, corpo){
  return fetch(url, {method: 'POST', headers: {'Content-Type': 'application/json'},
                     body: JSON.stringify(corpo || {})})
   .then(function(r){ return r.json() });
 }
 window.uiTabelaAcervo = function(alvo, o){
  o = o || {};
  var cx = (typeof alvo === 'string') ? $(alvo) : alvo;
  if(!cx) return null;
  cx.classList.add('ui-acervo');
  var est = {linhas: [], det: [], marcada: -1, vez: 0};
  var url = o.url || '/api/acervo/tabela';
  var urlDet = o.detalhes || '/api/acervo/tabela/detalhes';
  function esq(){ return '<span class="ui-esqueleto ua-esq" aria-hidden="true"></span>' }
  function cab(){
   return '<thead><tr>' + UA_COLUNAS.map(function(c){
    return '<th' + (UA_EXTRAS[c] ? ' class="ua-x"' : '') + ' data-radai-frase>' + esc(c) + '</th>';
   }).join('') + '<th class="ua-acao"><span class="ua-sr" data-radai-frase>Abrir</span></th></tr></thead>';
  }
  function mais(s){
   return '<div class="ua-mais"><span class="ua-m" data-c2="modo"></span>'
    + '<span class="ua-m" data-c2="tasks" translate="no"></span>'
    + '<span class="ua-m" data-c2="quando"><span data-radai-frase>Contornada em</span> '
    + esc((s.quando || '').slice(0, 16)) + '</span>'
    + '<span class="ua-m" data-c2="levou"><span data-radai-frase>Levou</span> '
    + (s.secs ? esc(uaDuracao(s.secs)) : '&mdash;') + '</span></div>';
  }
  function linha(s, i){
   var falta = (s.estado === 'sem_rs');
   return '<tr data-i="' + i + '"' + (falta ? ' class="ua-falta"' : '') + '>'
    + '<td data-c="data">' + esc(uaData(s.date)) + '</td>'
    + '<td class="ua-nome"><span data-c="nome" translate="no">' + esq() + '</span>' + mais(s) + '</td>'
    + '<td class="mono" data-c="id" translate="no">' + esc(s.pid) + '</td>'
    + '<td data-c="modalidade">' + esq() + '</td>'
    + '<td class="num" data-c="cortes">' + esq() + '</td>'
    + '<td class="num" data-c="espessura">' + esq() + '</td>'
    + '<td class="num" data-c="estruturas">' + esc(s.estruturas) + '</td>'
    + '<td class="ua-x" data-c="modo">' + esq() + '</td>'
    + '<td class="ua-tasks ua-x" data-c="tasks" translate="no">' + esq() + '</td>'
    + '<td class="mono ua-x" data-c="quando">' + esc((s.quando || '').slice(0, 16)) + '</td>'
    + '<td class="num ua-x" data-c="levou">' + (s.secs ? esc(uaDuracao(s.secs)) : '&mdash;') + '</td>'
    + '<td class="ua-acao">' + (falta
       ? '<span class="sub" data-radai-frase>o arquivo não está mais lá</span>'
       : '<button type="button" class="ui-bt" data-ua-abrir="' + i + '">'
         + '<span data-radai-frase>Abrir</span></button>')
    + '</td></tr>';
  }
  function ajustar(){
   var t = cx.querySelector('table');
   if(!t || !cx.clientWidth) return;
   cx.classList.remove('compacto');
   if(t.scrollWidth > cx.clientWidth + 1) cx.classList.add('compacto');
  }
  function preencher(i, x){
   var tr = cx.querySelector('tr[data-i="' + i + '"]');
   if(!tr) return;
   x = x || {};
   est.det[i] = x;
   function cel(k, v, titulo){
    var td = tr.querySelector('[data-c="' + k + '"]');
    var txt = (v == null || v === '') ? '' : String(v);
    if(td){ td.textContent = txt || '—'; if(titulo) td.title = titulo }
    var m = tr.querySelector('[data-c2="' + k + '"]');
    if(m){ m.textContent = txt; if(titulo) m.title = titulo }
   }
   cel('nome', x.nome);
   cel('modalidade', x.modalidade);
   cel('cortes', x.cortes);
   cel('espessura', x.espessura_mm == null ? '' : (x.espessura_mm + ' mm'));
   cel('modo', UA_MODO[x.modo] || '');
   var t = (x.tasks || []).join(', ');
   cel('tasks', t, t + ((x.protocolos || []).length ? ' · ' + x.protocolos.join(', ') : ''));
   var falt = x.faltou || [];
   if(falt.length){
    var ftx = (window.radaiFrase ? window.radaiFrase('Faltou nesta série: %s')
               : 'Faltou nesta série: %s').replace('%s', falt.join(', '));
    [tr.querySelector('[data-c="modo"]'), tr.querySelector('[data-c2="modo"]')]
     .forEach(function(a){
      if(!a) return;
      var sp = document.createElement('span');
      sp.className = 'ua-parcial';
      sp.setAttribute('data-radai-frase', '');
      sp.textContent = 'Parcial';
      sp.title = ftx;
      a.appendChild(sp);
      var fl = document.createElement('span');
      fl.className = 'ua-faltou';
      fl.textContent = ftx;
      a.appendChild(fl);
     });
   }
   if(o.filtro){
    var linhaToda = Object.assign({}, est.linhas[i] || {}, x);
    var fica = true;
    try{ fica = o.filtro(linhaToda) !== false }catch(e){}
    tr.hidden = !fica;
   }
  }
  function detalhes(ini, vez){
   var L = est.linhas;
   if(vez !== est.vez || ini >= L.length) return;
   var fim = Math.min(L.length, ini + UA_LOTE), bs = [];
   for(var i = ini; i < fim; i++) bs.push(L[i].bilhete);
   uaPost(urlDet, {bilhetes: bs}).catch(function(){ return null }).then(function(d){
    if(vez !== est.vez) return;
    var R = (d && d.itens) || [];
    for(var k = ini; k < fim; k++) preencher(k, R[k - ini]);
    traduzir(); ajustar();
    detalhes(fim, vez);
   });
  }
  function msg(txt, ruim, extra){
   cx.innerHTML = '<p class="ua-msg' + (ruim ? ' ruim' : '') + '" data-radai-frase></p>'
    + (extra || '');
   cx.querySelector('.ua-msg').textContent = txt;
   traduzir();
  }
  function pintar(d){
   d = d || {};
   est.linhas = d.series || [];
   est.det = [];
   est.marcada = -1;
   est.vez++;
   cx.removeAttribute('aria-busy');
   if(!est.linhas.length){
    msg(d.erro ? 'não consegui ler o acervo'
        : (o.vazioTexto || 'Nenhuma série foi contornada nesta máquina ainda.'),
        !!d.erro, d.erro ? '' : (o.vazio || ''));
   } else {
    var h = '<table>' + cab() + '<tbody>';
    est.linhas.forEach(function(s, i){ h += linha(s, i) });
    if(d.sumiram) h += '<tr><td colspan="12" class="sub">'
     + esc('%s série(s) que esta máquina contornou já não estão no lugar — a pasta foi movida ou apagada.'
           .replace('%s', d.sumiram)) + '</td></tr>';
    cx.innerHTML = h + '</tbody></table>';
    traduzir(); ajustar();
    detalhes(0, est.vez);
   }
   try{ if(o.aoCarregar) o.aoCarregar(est.linhas.slice()) }catch(e){}
  }
  function carregar(){
   cx.setAttribute('aria-busy', 'true');
   return uaPost(url, {limite: o.limite || 60}).then(pintar).catch(function(){
    cx.removeAttribute('aria-busy');
    msg('não consegui ler o acervo', true);
   });
  }
  function marcar(i){
   est.marcada = (i == null) ? -1 : Number(i);
   Array.prototype.forEach.call(cx.querySelectorAll('tbody tr[data-i]'), function(tr){
    tr.classList.toggle('on', Number(tr.getAttribute('data-i')) === est.marcada);
   });
  }
  cx.addEventListener('click', function(e){
   var b = e.target.closest ? e.target.closest('[data-ua-abrir]') : null;
   if(!b || !cx.contains(b)) return;
   var i = Number(b.getAttribute('data-ua-abrir'));
   var s = est.linhas[i];
   if(!s) return;
   marcar(i);
   try{ if(o.aoAbrir) o.aoAbrir(Object.assign({}, s, est.det[i] || {}), i, b) }catch(err){}
  });
  if(window.ResizeObserver){
   var largura = -1;
   new ResizeObserver(function(){
    if(cx.clientWidth === largura) return;
    largura = cx.clientWidth; ajustar();
   }).observe(cx);
  }
  carregar();
  return { recarregar: carregar, marcar: marcar, caixa: cx,
           linhas: function(){ return est.linhas.map(function(s, i){
             return Object.assign({}, s, est.det[i] || {}) }) } };
 };

 var SEG_N = 0, SEG_BALAO_T = null, SEG_BALAO_DE = null;
 function segCalmo(){
  try{ return !!(window.matchMedia
                 && window.matchMedia('(prefers-reduced-motion: reduce)').matches) }
  catch(e){ return false }
 }
 function segBalao(){
  var b = $('ui-seg-balao');
  if(b) return b;
  b = document.createElement('div');
  b.id = 'ui-seg-balao'; b.className = 'ui-seg-balao';
  b.setAttribute('aria-hidden', 'true');
  document.body.appendChild(b);
  return b;
 }
 function segEsconder(){
  clearTimeout(SEG_BALAO_T);
  var b = $('ui-seg-balao');
  if(b) b.classList.remove('on');
  SEG_BALAO_DE = null;
 }
 function segMostrar(bt, atraso){
  clearTimeout(SEG_BALAO_T);
  var txt = bt ? bt.getAttribute('data-ui-balao') : '';
  if(!txt){ segEsconder(); return }
  SEG_BALAO_T = setTimeout(function(){
   if(!bt.isConnected){ segEsconder(); return }
   var b = segBalao(), rot = bt.querySelector('.ui-seg-txt');
   var tr = window.radaiFrase ? window.radaiFrase(txt) : txt;
   b.innerHTML = '<span class="ui-seg-bt">' + esc(rot ? rot.textContent : '')
     + '</span>' + esc(tr);
   b.classList.remove('on');
   b.style.left = '0px'; b.style.top = '0px';
   var r = bt.getBoundingClientRect(), W = window.innerWidth, H = window.innerHeight;
   var w = b.offsetWidth || 300, h = b.offsetHeight || 80;
   var x = Math.min(r.left + r.width / 2 - w / 2, W - w - 16);
   var y = r.bottom + 8;
   if(y + h > H - 16 && r.top - 8 - h > 16) y = r.top - 8 - h;
   b.style.left = Math.max(16, x) + 'px';
   b.style.top = Math.max(16, y) + 'px';
   void b.offsetWidth;
   b.classList.add('on');
   SEG_BALAO_DE = bt;
  }, atraso || 0);
 }
 function segEmbaralhar(bt){
  var rot = bt.querySelector('.ui-seg-rot'), txt = bt.querySelector('.ui-seg-txt'),
      mex = bt.querySelector('.ui-seg-mex');
  if(!rot || !txt || !mex || segCalmo()) return false;
  var alvo = txt.textContent || '', letras = alvo.replace(/\\s/g, '');
  if(!letras) return false;
  if(bt._uiMex) cancelAnimationFrame(bt._uiMex);
  var t0 = null, DUR = window.UI_SEG_EMBARALHAR_MS || 250;
  rot.classList.add('mexendo');
  function quadro(t){
   if(t0 === null) t0 = t;
   var p = Math.min(1, (t - t0) / DUR), fixas = Math.floor(p * alvo.length), s = '';
   for(var i = 0; i < alvo.length; i++){
    var c = alvo.charAt(i);
    s += (i < fixas || /\\s/.test(c)) ? c
         : letras.charAt(Math.floor(Math.random() * letras.length));
   }
   mex.textContent = s;
   if(p < 1){ bt._uiMex = requestAnimationFrame(quadro); return }
   mex.textContent = '';
   rot.classList.remove('mexendo');
   bt._uiMex = 0;
  }
  bt._uiMex = requestAnimationFrame(quadro);
  return true;
 }

 window.uiSegmentado = function(alvo, o){
  try{
   o = o || {};
   var s = (typeof alvo === 'string') ? $(alvo) : alvo;
   if(!s || s.tagName !== 'SELECT') return null;
   if(s.getAttribute('data-ui-seg-feito') === '1'){
    var ja = s.previousElementSibling;
    return (ja && ja._uiSeg) ? ja : null;
   }
   if(!s.options || s.options.length < 2) return null;
   var mexe = (o.embaralhar !== undefined) ? !!o.embaralhar
              : (s.getAttribute('data-ui-seg') === 'embaralhar');
   var n = ++SEG_N;
   var cx = document.createElement('div');
   cx.className = 'ui-seg' + (o.classe ? ' ' + o.classe : '');
   cx.setAttribute('role', 'radiogroup');
   var nome = o.rotulo || s.getAttribute('aria-label') || '';
   if(nome) cx.setAttribute('aria-label', nome);
   var ind = document.createElement('span');
   ind.className = 'ui-seg-ind'; ind.setAttribute('aria-hidden', 'true');
   cx.appendChild(ind);
   var bts = [], descs = [], travadas = [];
   for(var i = 0; i < s.options.length; i++){
    var op = s.options[i], v = op.value;
    var b = document.createElement('button');
    b.type = 'button';
    b.setAttribute('role', 'radio');
    b.setAttribute('data-v', v);
    var icn = (o.icones && o.icones[v]) || op.getAttribute('data-ui-icone');
    var bal = (o.baloes && o.baloes[v]) || op.getAttribute('data-ui-balao');
    var tit = op.getAttribute('title');
    b.innerHTML = (icn ? ico(icn) : '') + '<span class="ui-seg-rot">'
      + '<span class="ui-seg-txt"></span>'
      + '<span class="ui-seg-mex" aria-hidden="true"></span></span>';
    b.querySelector('.ui-seg-txt').textContent = op.textContent;
    if(tit) b.setAttribute('title', tit);
    if(bal){
     var d = document.createElement('span');
     d.id = 'ui-seg-' + n + '-' + i; d.className = 'ui-seg-desc'; d.hidden = true;
     d.textContent = bal;
     descs.push(d);
     b.setAttribute('data-ui-balao', bal);
     b.setAttribute('aria-describedby', d.id);
    }
    travadas.push(!!op.disabled);
    cx.appendChild(b);
    bts.push(b);
   }
   descs.forEach(function(d){ cx.appendChild(d) });
   s.parentNode.insertBefore(cx, s);
   s.classList.add('ui-seg-fonte');
   s.setAttribute('data-ui-seg-feito', '1');
   s.tabIndex = -1;
   s.setAttribute('aria-hidden', 'true');

   var pintado = false;
   function pintar(){
    var v = s.value, tudo = !!s.disabled, achou = false;
    if(tudo) cx.setAttribute('aria-disabled', 'true');
    else cx.removeAttribute('aria-disabled');
    for(var i = 0; i < bts.length; i++){
     var sel = (bts[i].getAttribute('data-v') === v);
     bts[i].disabled = tudo || travadas[i];
     bts[i].setAttribute('aria-checked', sel ? 'true' : 'false');
     bts[i].tabIndex = (sel && !tudo) ? 0 : -1;
     if(sel){
      achou = true;
      if(bts[i].offsetWidth){
       pintado = true;
       ind.style.width = bts[i].offsetWidth + 'px';
       ind.style.transform = 'translateX(' + bts[i].offsetLeft + 'px)';
      }
     }
    }
    ind.style.opacity = achou ? '' : '0';
    if(!achou && !tudo){
     for(var k = 0; k < bts.length; k++) if(!bts[k].disabled){ bts[k].tabIndex = 0; break }
    }
   }
   function semSalto(){
    cx.classList.add('sem-salto');
    pintar();
    requestAnimationFrame(function(){ requestAnimationFrame(function(){
     cx.classList.remove('sem-salto') }) });
   }
   function escolher(v){
    if(s.disabled) return false;
    var bt = null;
    for(var k = 0; k < bts.length; k++) if(bts[k].getAttribute('data-v') === v) bt = bts[k];
    if(!bt || bt.disabled) return false;
    if(s.value === v){ pintar(); return false }
    s.value = v;
    var ev;
    try{ ev = new Event('change', {bubbles: true}) }
    catch(e){ ev = document.createEvent('HTMLEvents'); ev.initEvent('change', true, false) }
    s.dispatchEvent(ev);
    pintar();
    if(s.value !== v) return false;
    if(mexe) segEmbaralhar(bt);
    if(o.aoMudar){ try{ o.aoMudar(v) }catch(e){} }
    return true;
   }
   cx.addEventListener('click', function(e){
    var b = e.target.closest ? e.target.closest('button[data-v]') : null;
    if(b && !b.disabled) escolher(b.getAttribute('data-v'));
   });
   cx.addEventListener('keydown', function(e){
    var k = e.key, passo = 0, rtl = false;
    try{ rtl = getComputedStyle(cx).direction === 'rtl' }catch(x){}
    if(k === 'ArrowRight') passo = rtl ? -1 : 1;
    else if(k === 'ArrowLeft') passo = rtl ? 1 : -1;
    else if(k === 'ArrowDown') passo = 1;
    else if(k === 'ArrowUp') passo = -1;
    else if(k === 'Escape'){ segEsconder(); return }
    else if(k !== 'Home' && k !== 'End') return;
    e.preventDefault();
    var vivos = bts.filter(function(b){ return !b.disabled });
    if(!vivos.length) return;
    var i = 0;
    for(var j = 0; j < vivos.length; j++)
     if(vivos[j].getAttribute('aria-checked') === 'true') i = j;
    if(k === 'Home') i = 0;
    else if(k === 'End') i = vivos.length - 1;
    else i = (i + passo + vivos.length) % vivos.length;
    escolher(vivos[i].getAttribute('data-v'));
    try{ vivos[i].focus() }catch(x){}
    segMostrar(vivos[i], 0);
   });
   cx.addEventListener('mouseover', function(e){
    var b = e.target.closest ? e.target.closest('button[data-v]') : null;
    if(b && b !== SEG_BALAO_DE) segMostrar(b, 350);
   });
   cx.addEventListener('mouseleave', segEsconder);
   cx.addEventListener('focusin', function(e){
    var b = e.target.closest ? e.target.closest('button[data-v]') : null;
    if(b) segMostrar(b, 0);
   });
   cx.addEventListener('focusout', function(e){
    if(!e.relatedTarget || !cx.contains(e.relatedTarget)) segEsconder();
   });
   s.addEventListener('change', pintar);
   var ro = null;
   if(window.ResizeObserver){
    try{
     ro = new ResizeObserver(function(){ if(pintado) pintar(); else semSalto() });
     ro.observe(cx);
    }catch(e){ ro = null }
   }
   if(!ro) window.addEventListener('resize', pintar);
   semSalto();
   cx._uiSeg = true;
   cx._uiPintar = pintar;
   cx._uiSoltar = function(){
    if(ro){ try{ ro.disconnect() }catch(e){} }
    window.removeEventListener('resize', pintar);
   };
   cx.uiValor = function(){ return s.value };
   cx.uiEscolher = escolher;
   return cx;
  }catch(err){ return null }
 };
 window.uiSegmentadoTodos = function(){
  try{
   var l = document.querySelectorAll('select[data-ui-seg]'), feitos = 0;
   for(var i = 0; i < l.length; i++) if(window.uiSegmentado(l[i])) feitos++;
   if(feitos) traduzir();
  }catch(e){}
 };
 window.uiSeletorDeTema = function(alvo){
  try{
   var s = (typeof alvo === 'string') ? $(alvo) : alvo;
   if(!s || s.tagName !== 'SELECT' || typeof window.uiTema !== 'function') return null;
   if(s.getAttribute('data-ui-tema-feito') === '1') return s;
   s.setAttribute('data-ui-tema-feito', '1');
   var sincronizar = function(){
    var v = window.uiTemaEscolha ? window.uiTemaEscolha() : 'sistema';
    if(s.value === v) return;
    s.value = v;
    var cx = s.previousElementSibling;
    if(cx && cx._uiPintar) cx._uiPintar();
   };
   s.addEventListener('change', function(){ window.uiTema(s.value) });
   window.addEventListener('radai-tema', sincronizar);
   sincronizar();
   return s;
  }catch(e){ return null }
 };
 document.addEventListener('DOMContentLoaded', function(){
  try{
   var l = document.querySelectorAll('select[data-ui-tema]');
   for(var i = 0; i < l.length; i++) window.uiSeletorDeTema(l[i]);
  }catch(e){}
  window.uiSegmentadoTodos();
 });
 window.addEventListener('scroll', function(){
  var b = $('ui-seg-balao');
  if(b && b.classList.contains('on')){ b.classList.remove('on'); SEG_BALAO_DE = null }
 }, true);

 window.uiTremer = function(alvo){
  try{
   var e = (typeof alvo === 'string') ? ($(alvo) || document.querySelector(alvo)) : alvo;
   if(!e) return null;
   var calmo = !!(window.matchMedia
                  && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
   try{ e.scrollIntoView({block: 'center', behavior: calmo ? 'auto' : 'smooth'}) }
   catch(x){ try{ e.scrollIntoView() }catch(y){} }
   if(!calmo){
    e.classList.remove('ui-treme');
    void e.offsetWidth;
    e.classList.add('ui-treme');
    clearTimeout(e._uiTreme);
    e._uiTreme = setTimeout(function(){ e.classList.remove('ui-treme') }, 320);
   }
   var CAMPO = 'input,select,textarea,button,[contenteditable="true"],[tabindex]';
   var f = (e.matches && e.matches(CAMPO)) ? e
           : e.querySelector(CAMPO.replace('[tabindex]', '[tabindex]:not([tabindex="-1"])'));
   try{ (f || e).focus({preventScroll: true}) }catch(x){ try{ (f || e).focus() }catch(y){} }
   return e;
  }catch(err){ return null }
 };

 function lerEntrada(ent, base, saida){
  return new Promise(function(ok){
   if(!ent){ ok(); return }
   if(ent.isFile){
    ent.file(function(f){ saida.push({arquivo:f, caminho: base + f.name}); ok() },
             function(){ ok() });
    return;
   }
   if(!ent.isDirectory){ ok(); return }
   var leitor = ent.createReader(), todos = [];
   (function mais(){
    leitor.readEntries(function(l){
     if(!l.length){
      var p = Promise.resolve();
      todos.forEach(function(x){
       p = p.then(function(){ return lerEntrada(x, base + ent.name + '/', saida) });
      });
      p.then(ok);
      return;
     }
     todos = todos.concat(Array.prototype.slice.call(l));
     mais();
    }, function(){ ok() });
   })();
  });
 }
 function doArrasto(dt){
  var saida = [], itens = dt && dt.items ? Array.prototype.slice.call(dt.items) : [];
  var ents = itens.map(function(it){
   return (it.kind === 'file' && it.webkitGetAsEntry) ? it.webkitGetAsEntry() : null;
  });
  if(ents.some(function(x){ return x })){
   var p = Promise.resolve();
   ents.forEach(function(x){ p = p.then(function(){ return lerEntrada(x, '', saida) }) });
   return p.then(function(){ return saida });
  }
  var fs = dt && dt.files ? Array.prototype.slice.call(dt.files) : [];
  return Promise.resolve(fs.map(function(f){ return {arquivo:f, caminho:f.name} }));
 }
 function doCampo(inp){
  return Array.prototype.slice.call(inp.files || []).map(function(f){
   return {arquivo:f, caminho: f.webkitRelativePath || f.name};
  });
 }
 function envioEstado(z, txt, html){
  var s = z.querySelector('.ui-envio-est'); if(!s) return;
  if(html){ if(window.uiHTML) window.uiHTML(s, html); else s.innerHTML = html }
  else if(window.uiTexto) window.uiTexto(s, txt || ''); else s.textContent = txt || '';
  traduzir();
 }
 function envioBarra(z, f){
  var b = z.querySelector('.ui-envio-barra i');
  if(b) b.style.transform = 'scaleX(' + Math.max(0, Math.min(1, f)).toFixed(3) + ')';
 }
 function envioPorPedacos(z, o, lista){
  var tam = Math.max(65536, Number(o.pedaco) || 4194304);
  var paralelo = Math.max(1, Number(o.paralelo) || 3);
  var total = 0, feito = 0;
  lista.forEach(function(x){ total += x.arquivo.size || 0 });
  z.classList.remove('erro'); z.classList.add('enviando');
  envioBarra(z, 0);
  envioEstado(z, '', '<b>' + lista.length + '</b> ' + frase('arquivo(s)') + ' &middot; '
   + frase('enviando'));
  function umArquivo(x){
   var off = 0;
   function pedaco(){
    var fatia = x.arquivo.slice(off, off + tam);
    return fetch(o.url, {method:'POST', body: fatia, headers:{
      'Content-Type': 'application/octet-stream',
      'X-RadAI-Sessao': o.sessao || '',
      'X-RadAI-Arquivo': encodeURIComponent(x.caminho),
      'X-RadAI-Offset': String(off)}})
     .then(function(r){
      return r.json().catch(function(){ return {} }).then(function(d){
       if(!r.ok || (d && d.erro)) throw new Error((d && d.erro) || ('HTTP ' + r.status));
       if(d && d.sessao) o.sessao = String(d.sessao);
       off += fatia.size; feito += fatia.size;
       envioBarra(z, total ? feito / total : 1);
       if(off < (x.arquivo.size || 0)) return pedaco();
      });
     });
   }
   return pedaco();
  }
  var fila = lista.slice();
  function trabalhador(){
   if(!fila.length) return Promise.resolve();
   return umArquivo(fila.shift()).then(trabalhador);
  }
  // GUARDA: o primeiro arquivo vai sozinho; é ele que abre a sessão que os paralelos usam.
  var inicio = o.sessao ? Promise.resolve() : umArquivo(fila.shift());
  return inicio.then(function(){
   var ts = [];
   for(var k = 0; k < paralelo; k++) ts.push(trabalhador());
   return Promise.all(ts);
  }).then(function(){
   if(!o.fim) return {sessao: o.sessao};
   return fetch(o.fim, {method:'POST', headers:{'Content-Type':'application/json'},
     body: JSON.stringify({sessao: o.sessao || ''})}).then(function(r){
    return r.json().catch(function(){ return {} }).then(function(d){
     if(!r.ok || (d && d.erro)) throw new Error((d && d.erro) || ('HTTP ' + r.status));
     d = d || {}; if(!d.sessao) d.sessao = o.sessao;
     return d;
    });
   });
  }).then(function(d){
   z.classList.remove('enviando');
   envioEstado(z, '', '<b>' + lista.length + '</b> ' + frase('arquivo(s)') + ' &middot; '
    + frase('enviado'));
   try{ if(o.aoTerminar) o.aoTerminar([d], lista) }catch(e){}
   return [d];
  }, function(err){
   z.classList.remove('enviando'); z.classList.add('erro');
   envioEstado(z, '', frase('o envio falhou') + ' <code>' + esc(err && err.message) + '</code>');
   try{ if(o.aoErro) o.aoErro(err) }catch(e){}
   throw err;
  });
 }
 window.uiEnviarArquivos = function(zona, lista){
  var z = (typeof zona === 'string') ? $(zona) : zona;
  var o = (z && z._uiEnvio) || {};
  lista = (lista || []).filter(function(x){ return x && x.arquivo });
  if(!z || !o.url){ return Promise.reject(new Error('sem destino')) }
  if(!lista.length){ envioEstado(z, 'nada para enviar'); return Promise.resolve([]) }
  if(o.pedacos) return envioPorPedacos(z, o, lista);
  var porLote = Math.max(1, Number(o.porLote) || 64);
  var total = 0, feito = 0;
  lista.forEach(function(x){ total += x.arquivo.size || 0 });
  var lotes = [];
  for(var k = 0; k < lista.length; k += porLote) lotes.push(lista.slice(k, k + porLote));
  var lote = '', respostas = [];
  z.classList.remove('erro'); z.classList.add('enviando');
  envioBarra(z, 0);
  envioEstado(z, '', '<b>' + lista.length + '</b> ' + frase('arquivo(s)') + ' &middot; '
   + frase('enviando'));
  var p = Promise.resolve();
  lotes.forEach(function(grupo, n){
   p = p.then(function(){
    var fd = new FormData();
    var caminhos = [];
    grupo.forEach(function(x){
     fd.append('arquivos', x.arquivo, x.caminho);
     caminhos.push(x.caminho);
    });
    fd.append('caminhos', JSON.stringify(caminhos));
    fd.append('lote', lote);
    fd.append('ultimo', n === lotes.length - 1 ? '1' : '0');
    var campos = o.campos || {};
    for(var c in campos) if(Object.prototype.hasOwnProperty.call(campos, c))
     fd.append(c, campos[c]);
    return fetch(o.url, {method:'POST', body:fd}).then(function(r){
     return r.json().catch(function(){ return {} }).then(function(d){
      if(!r.ok || (d && d.erro)) throw new Error((d && d.erro) || ('HTTP ' + r.status));
      if(d && d.lote) lote = String(d.lote);
      respostas.push(d);
      grupo.forEach(function(x){ feito += x.arquivo.size || 0 });
      envioBarra(z, total ? feito / total : (n + 1) / lotes.length);
     });
    });
   });
  });
  return p.then(function(){
   z.classList.remove('enviando');
   envioEstado(z, '', '<b>' + lista.length + '</b> ' + frase('arquivo(s)') + ' &middot; '
    + frase('enviado'));
   try{ if(o.aoTerminar) o.aoTerminar(respostas, lista) }catch(e){}
   return respostas;
  }, function(err){
   z.classList.remove('enviando'); z.classList.add('erro');
   envioEstado(z, '', frase('o envio falhou') + ' <code>' + esc(err && err.message) + '</code>');
   try{ if(o.aoErro) o.aoErro(err) }catch(e){}
   throw err;
  });
 };
 window.uiEnvio = function(zona, o){
  var z = (typeof zona === 'string') ? $(zona) : zona;
  if(!z) return null;
  z._uiEnvio = o || {};
  if(z.getAttribute('data-ui-envio-feito') === '1') return z;
  z.setAttribute('data-ui-envio-feito', '1');
  var arq = z.querySelector('.ui-envio-arq'), dir = z.querySelector('.ui-envio-dir');
  var fundo = 0;
  function soltar(lista){
   z.classList.remove('engoliu'); void z.offsetWidth; z.classList.add('engoliu');
   setTimeout(function(){ z.classList.remove('engoliu') }, 520);
   return window.uiEnviarArquivos(z, lista).catch(function(){});
  }
  z.addEventListener('dragenter', function(e){ e.preventDefault(); fundo++;
   z.classList.add('sobre') });
  z.addEventListener('dragover', function(e){
   e.preventDefault();
   try{ e.dataTransfer.dropEffect = 'copy' }catch(err){}
   var r = z.getBoundingClientRect();
   var dx = Math.max(-10, Math.min(10, (e.clientX - (r.left + r.width / 2)) / 18));
   z.style.setProperty('--dx', dx.toFixed(1) + 'px');
  });
  z.addEventListener('dragleave', function(){
   fundo = Math.max(0, fundo - 1);
   if(!fundo){ z.classList.remove('sobre'); z.style.setProperty('--dx', '0px') }
  });
  z.addEventListener('drop', function(e){
   e.preventDefault(); fundo = 0;
   z.classList.remove('sobre'); z.style.setProperty('--dx', '0px');
   doArrasto(e.dataTransfer).then(soltar);
  });
  if(z._uiEnvio.pagina){
   // GUARDA: sem isto, soltar o arquivo fora da zona faz o navegador abrir o arquivo e sair da tela.
   var temArquivo = function(e){
    var t = e.dataTransfer && e.dataTransfer.types;
    return !!t && Array.prototype.indexOf.call(t, 'Files') >= 0;
   };
   document.addEventListener('dragover', function(e){
    if(!temArquivo(e) || z.contains(e.target)) return;
    e.preventDefault();
    try{ e.dataTransfer.dropEffect = 'copy' }catch(err){}
    z.classList.add('chamando');
   });
   document.addEventListener('dragleave', function(e){
    if(!e.relatedTarget) z.classList.remove('chamando');
   });
   document.addEventListener('drop', function(e){
    z.classList.remove('chamando');
    if(!temArquivo(e) || z.contains(e.target)) return;
    e.preventDefault();
    doArrasto(e.dataTransfer).then(soltar);
   });
  }
  z.addEventListener('click', function(e){
   var b = e.target.closest ? e.target.closest('[data-envio]') : null;
   if(b){ e.preventDefault();
    (b.getAttribute('data-envio') === 'pasta' ? dir : arq).click(); return }
   if(e.target === arq || e.target === dir) return;
   arq.click();
  });
  z.addEventListener('keydown', function(e){
   if(e.target !== z) return;
   if(e.key === 'Enter' || e.key === ' '){ e.preventDefault(); arq.click() }
  });
  [arq, dir].forEach(function(inp){
   if(!inp) return;
   inp.addEventListener('change', function(){
    var l = doCampo(inp); inp.value = '';
    if(l.length) soltar(l);
   });
  });
  return z;
 };

 var FP = null;
 var FP_TIPO = {fixa:'local', rede:'rede', removivel:'removível', optica:'óptica', ram:'RAM'};
 function fpPedir(corpo){
  return fetch('/api/lote/pastas', {method:'POST',
   headers:{'Content-Type':'application/json'}, body: JSON.stringify(corpo)})
   .then(function(r){ return r.json() });
 }
 function fpNorm(c){
  var SEP = new RegExp('[' + String.fromCharCode(92) + '/]+$');
  return String(c || '').replace(SEP, '').toLowerCase();
 }
 function fpMontar(){
  var r = document.createElement('div');
  r.className = 'ui-fp';
  r.innerHTML = '<div class="ui-fp-nav">'
   + '<button type="button" class="ui-bt" data-fp="volta" title="voltar" aria-label="voltar">' + ico('esquerda') + '</button>'
   + '<button type="button" class="ui-bt" data-fp="frente" title="avancar" aria-label="avancar">' + ico('direita') + '</button>'
   + '<button type="button" class="ui-bt" data-fp="sobe" title="subir um nivel" aria-label="subir um nivel">' + ico('acima') + '</button>'
   + '<button type="button" class="ui-bt" data-fp="fav" title="ir para a pasta favorita" aria-label="ir para a pasta favorita">' + ico('estrela') + '</button>'
   + '<input type="text" class="ui-fp-cam" spellcheck="false" aria-label="caminho">'
   + '<button type="button" class="ui-bt" data-fp="ir">' + frase('Ir') + '</button></div>'
   + '<div class="ui-fp-corpo"><aside class="ui-fp-lado" aria-label="unidades">'
   + '<div class="ui-fp-sec">' + frase('Unidades') + '</div>'
   + '<div class="ui-fp-arvore" role="tree"></div></aside>'
   + '<section class="ui-fp-dir"><div class="ui-fp-ferr">'
   + '<input type="text" class="ui-fp-busca" spellcheck="false" placeholder="buscar nesta pasta &mdash; trecho do nome ou do prontu&aacute;rio">'
   + '<button type="button" class="ui-bt" data-fp="limpar">' + frase('limpar') + '</button>'
   + '<span class="ui-fp-ord" role="group" aria-label="ordenar">'
   + '<button type="button" data-ord="nome" aria-pressed="true">' + frase('Nome') + '</button>'
   + '<button type="button" data-ord="data" aria-pressed="false">' + frase('Data') + '</button></span></div>'
   + '<div class="ui-fp-cabl">' + frase('Nome') + frase('Modificada em') + '</div>'
   + '<div class="ui-fp-lista" role="listbox" aria-label="pastas"></div>'
   + '<div class="ui-fp-msg"></div></section></div>'
   + '<div class="ui-fp-pe"><button type="button" class="ui-bt" data-fp="favoritar">'
   + ico('estrela') + frase('marcar como favorita') + '</button><span class="ui-fp-esp"></span>'
   + '<button type="button" class="ui-bt" data-fp="cancelar">' + frase('Cancelar') + '</button>'
   + '<button type="button" class="ui-bt pri" data-fp="usar">' + frase('Usar esta pasta') + '</button></div>';
  return r;
 }
 function fpQ(s){ return FP.raiz.querySelector(s) }
 function fpErro(el, rotulo, detalhe){
  var h = frase(rotulo) + (detalhe ? ' <code data-radai-t="1" translate="no">' + esc(detalhe) + '</code>' : '');
  if(window.uiHTML) window.uiHTML(el, h); else el.innerHTML = h;
  traduzir();
 }
 function fpBotoes(){
  fpQ('[data-fp="volta"]').disabled = !(FP.pos > 0);
  fpQ('[data-fp="frente"]').disabled = !(FP.pos < FP.hist.length - 1);
  fpQ('[data-fp="sobe"]').disabled = !FP.pai;
  fpQ('[data-fp="fav"]').style.display = FP.fav ? '' : 'none';
  Array.prototype.forEach.call(FP.raiz.querySelectorAll('.ui-fp-ord button'), function(b){
   var on = (b.getAttribute('data-ord') === FP.ordem);
   b.setAttribute('aria-pressed', on ? 'true' : 'false');
   b.setAttribute('data-sentido', on ? FP.sentido : '');
  });
 }
 function fpMarcar(){
  var atual = fpNorm(fpQ('.ui-fp-cam').value);
  Array.prototype.forEach.call(FP.raiz.querySelectorAll('.ui-fp-no'), function(n){
   n.classList.toggle('atual', !!atual && fpNorm(n.getAttribute('data-c')) === atual);
  });
 }
 function fpNo(c, rotulo, tipo, respondeu){
  var cx = document.createElement('div');
  cx.innerHTML = '<div class="ui-fp-no" role="treeitem" aria-expanded="false" data-c="'
   + esc(c) + '"><button type="button" class="ui-fp-tg" aria-label="abrir">&#9656;</button>'
   + '<span class="ui-fp-nm" tabindex="0">' + esc(rotulo)
   + ((tipo || respondeu === null) ? '<span class="ui-fp-tipo" data-radai-frase>'
     + esc(respondeu === null ? 'não respondeu' : (FP_TIPO[tipo] || tipo)) + '</span>' : '')
   + '</span></div><div class="ui-fp-filhos" hidden></div>';
  return cx;
 }
 function fpArvore(){
  var arv = fpQ('.ui-fp-arvore');
  arv.innerHTML = '<div class="ui-esqueleto ui-esq-l"></div><div class="ui-esqueleto ui-esq-l"></div>';
  fpPedir({caminho:'', unidades:true}).then(function(d){
   arv.innerHTML = '';
   (d.unidades || []).forEach(function(u){ arv.appendChild(fpNo(u.raiz, u.raiz, u.tipo, u.ok)) });
   if(!arv.children.length) arv.innerHTML = '<div class="ui-fp-item vazio">'
     + frase('nenhuma unidade respondeu') + '</div>';
   fpMarcar(); traduzir();
  }).catch(function(e){ fpErro(arv, 'Não consegui listar as unidades.', e) });
 }
 function fpExpandir(no){
  var filhos = no.parentNode.querySelector('.ui-fp-filhos'), tg = no.querySelector('.ui-fp-tg');
  if(!filhos.hidden){ filhos.hidden = true; tg.innerHTML = '&#9656;';
   no.setAttribute('aria-expanded', 'false'); return }
  filhos.hidden = false; tg.innerHTML = '&#9662;'; no.setAttribute('aria-expanded', 'true');
  if(filhos.getAttribute('data-veio')) return;
  filhos.innerHTML = '<div class="ui-esqueleto ui-esq-l"></div>';
  fpPedir({caminho: no.getAttribute('data-c'), ordem:'nome'}).then(function(d){
   filhos.setAttribute('data-veio', '1'); filhos.innerHTML = '';
   (d.pastas || []).forEach(function(p){ filhos.appendChild(fpNo(p.caminho, p.nome, '', true)) });
   if(!(d.pastas || []).length){ filhos.hidden = true; tg.disabled = true }
   fpMarcar();
  }).catch(function(){ filhos.innerHTML = ''; filhos.hidden = true });
 }
 function fpLista(d){
  var q = (fpQ('.ui-fp-busca').value || '').trim(), partes = [];
  if(q && d.achados >= 0) partes.push('<b>' + esc(d.achados) + '</b> ' + frase('pasta(s) com o termo')
   + ' &laquo;' + esc(q) + '&raquo;');
  if(d.mostrando) partes.push(frase('mostrando') + ' <b>' + esc(d.mostrando) + '</b> '
   + frase('de') + ' <b>' + esc(d.total) + '</b> ' + frase('pastas'));
  if(d.dica) partes.push(frase(d.dica));
  if(d.erro) partes.push(frase(d.erro) + (d.tipo ? ' <code>' + esc(d.tipo) + '</code>' : ''));
  var m = fpQ('.ui-fp-msg');
  if(window.uiHTML) window.uiHTML(m, partes.join(' &mdash; ')); else m.innerHTML = partes.join(' &mdash; ');
  var pasta = ico('pasta'), h = '';
  (d.pastas || []).forEach(function(p){
   h += '<div class="ui-fp-item" role="option" tabindex="0" data-c="' + esc(p.caminho) + '">'
    + '<span class="ui-fp-n">' + pasta + '<span>' + esc(p.nome) + '</span></span>'
    + '<span class="ui-fp-d">' + esc(p.data || '') + '</span></div>';
  });
  if(!h) h = '<div class="ui-fp-item vazio">' + frase(d.caminho ? '(nenhuma subpasta aqui)'
   : 'Escolha uma unidade à esquerda para começar.') + '</div>';
  var l = fpQ('.ui-fp-lista');
  if(window.uiHTML) window.uiHTML(l, h); else l.innerHTML = h;
  traduzir();
 }
 function fpCarregar(c){
  fpPedir({caminho:c, busca:(fpQ('.ui-fp-busca').value || '').trim(),
           ordem:FP.ordem, sentido:FP.sentido}).then(function(d){
   fpQ('.ui-fp-cam').value = d.caminho || c || '';
   FP.pai = d.pai || '';
   fpBotoes(); fpLista(d); fpMarcar();
  }).catch(function(e){ fpErro(fpQ('.ui-fp-msg'), 'Não consegui listar a pasta.', e) });
 }
 function fpNavegar(c){
  FP.hist = FP.hist.slice(0, FP.pos + 1);
  if(FP.hist[FP.hist.length - 1] !== c) FP.hist.push(c);
  FP.pos = FP.hist.length - 1;
  fpCarregar(c);
 }
 function fpAcao(a){
  if(a === 'volta' && FP.pos > 0){ FP.pos--; fpCarregar(FP.hist[FP.pos]) }
  else if(a === 'frente' && FP.pos < FP.hist.length - 1){ FP.pos++; fpCarregar(FP.hist[FP.pos]) }
  else if(a === 'sobe' && FP.pai) fpNavegar(FP.pai);
  else if(a === 'fav' && FP.fav) fpNavegar(FP.fav);
  else if(a === 'ir') fpNavegar(fpQ('.ui-fp-cam').value || '');
  else if(a === 'limpar'){ fpQ('.ui-fp-busca').value = ''; fpCarregar(fpQ('.ui-fp-cam').value || '') }
  else if(a === 'cancelar') FP.modal.fechar();
  else if(a === 'usar'){
   var c = fpQ('.ui-fp-cam').value || '', o = FP.o;
   FP.modal.fechar();
   try{ if(o.aoUsar) o.aoUsar(c) }catch(e){}
  } else if(a === 'favoritar'){
   var cf = fpQ('.ui-fp-cam').value || '';
   if(!cf) return;
   fetch('/api/lote/favorita', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({caminho:cf})}).then(function(r){ return r.json() }).then(function(d){
    if(d && d.erro){ fpErro(fpQ('.ui-fp-msg'), 'Não consegui marcar a pasta como favorita.', d.erro); return }
    FP.fav = (d && d.favorita) || cf; fpBotoes();
   }).catch(function(){});
  }
 }
 window.uiExplorador = function(o){
  o = o || {};
  var raiz = fpMontar();
  FP = {o:o, raiz:raiz, hist:[], pos:-1, pai:'', fav:'', ordem:'nome', sentido:'asc', t:null};
  FP.modal = window.uiModal({titulo: o.titulo || 'Escolher a pasta', no: raiz, largura: 940,
   origem: o.origem, classe:'ui-fp-modal'});
  raiz.addEventListener('click', function(e){
   var b = e.target.closest ? e.target.closest('[data-fp]') : null;
   if(b){ fpAcao(b.getAttribute('data-fp')); return }
   var ord = e.target.closest ? e.target.closest('.ui-fp-ord button') : null;
   if(ord){
    var k = ord.getAttribute('data-ord');
    if(FP.ordem === k) FP.sentido = (FP.sentido === 'asc') ? 'desc' : 'asc';
    else { FP.ordem = k; FP.sentido = (k === 'data') ? 'desc' : 'asc' }
    fpBotoes(); fpCarregar(fpQ('.ui-fp-cam').value || ''); return;
   }
   var tg = e.target.closest ? e.target.closest('.ui-fp-tg') : null;
   if(tg){ fpExpandir(tg.parentNode); return }
   var nm = e.target.closest ? e.target.closest('.ui-fp-nm') : null;
   if(nm){ fpNavegar(nm.parentNode.getAttribute('data-c')); return }
   var it = e.target.closest ? e.target.closest('.ui-fp-item[data-c]') : null;
   if(it) fpNavegar(it.getAttribute('data-c'));
  });
  raiz.addEventListener('dblclick', function(e){
   var it = e.target.closest ? e.target.closest('.ui-fp-item[data-c]') : null;
   if(it){ fpQ('.ui-fp-cam').value = it.getAttribute('data-c'); fpAcao('usar') }
  });
  raiz.addEventListener('keydown', function(e){
   if(e.key !== 'Enter' && e.key !== ' ') return;
   var it = e.target.closest ? e.target.closest('.ui-fp-item[data-c], .ui-fp-nm') : null;
   if(!it) return;
   e.preventDefault();
   var c = it.getAttribute('data-c') || it.parentNode.getAttribute('data-c');
   fpNavegar(c);
  });
  fpQ('.ui-fp-cam').addEventListener('keydown', function(e){
   if(e.key === 'Enter'){ e.preventDefault(); fpAcao('ir') } });
  fpQ('.ui-fp-busca').addEventListener('input', function(){
   if(FP.t) clearTimeout(FP.t);
   FP.t = setTimeout(function(){ fpCarregar(fpQ('.ui-fp-cam').value || '') }, 260);
  });
  fpBotoes();
  fpArvore();
  var ini = o.inicial || '';
  var fav = fetch('/api/lote/favorita', {method:'POST', headers:{'Content-Type':'application/json'},
   body:'{}'}).then(function(r){ return r.json() }).then(function(d){
    FP.fav = (d && d.favorita) || ''; fpBotoes();
   }).catch(function(){});
  if(ini) fpNavegar(ini);
  else fav.then(function(){ if(FP.fav && !(o.semFavorita)) fpNavegar(FP.fav);
                            else fpLista({pastas:[], caminho:''}) });
  return { fechar: FP.modal.fechar };
 };
})();
</script>
"""

ICONES_DOS_COMPONENTES = (u"fechar", u"esquerda", u"direita", u"acima",
                          u"estrela", u"pasta", u"subir", u"mais",
                          u"alerta", u"desmarcar", u"sol", u"lua", u"monitor")


def moldes_de_icone():
    return u"".join(u'<template id="ui-ico-%s">%s</template>' % (n, icone(n))
                    for n in ICONES_DOS_COMPONENTES)


CSS_EXPLORADOR = u"""
.ui-fp-modal .ui-modal-corpo{padding:14px 16px 16px}
.ui-fp-nav{display:flex;align-items:center;gap:6px;margin:0 0 10px}
.ui-fp-nav .ui-bt{padding:7px 9px;min-width:32px}
.ui-fp-nav .ui-bt .ui-ic{margin:0}
.ui-fp-nav .ui-bt:disabled{opacity:.35}
.ui-fp-cam{flex:1 1 auto;min-width:0}
.ui-fp-corpo{display:grid;grid-template-columns:220px minmax(0,1fr);gap:12px}
.ui-fp-lado{border:1px solid var(--line);border-radius:var(--r-md);
 background:var(--bg-1);padding:6px;max-height:420px;overflow:auto}
.ui-fp-sec{font:600 10px/1.4 var(--font-mono);letter-spacing:.5px;
 text-transform:uppercase;color:var(--text-dim);padding:4px 6px 6px}
.ui-fp-no{display:flex;align-items:center;gap:2px;border-radius:5px;
 font-size:12px;color:var(--text-muted);min-height:26px}
.ui-fp-no.atual{background:var(--accent-fraco);color:var(--text)}
.ui-fp-tg{background:none;border:0;color:var(--text-dim);width:20px;height:22px;
 padding:0;font-size:10px;cursor:pointer;flex:0 0 auto}
.ui-fp-tg:hover{color:var(--accent)}
.ui-fp-tg[disabled]{visibility:hidden}
.ui-fp-nm{flex:1 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis;
 white-space:nowrap;cursor:pointer;padding:3px 4px;border-radius:4px}
.ui-fp-nm:hover{color:var(--text)}
.ui-fp-tipo{font:400 9.5px/1 var(--font-mono);color:var(--text-dim);margin-left:6px;
 text-transform:uppercase;letter-spacing:.4px}
.ui-fp-filhos{padding-left:14px}
.ui-fp-dir{min-width:0;display:flex;flex-direction:column}
.ui-fp-ferr{display:flex;align-items:center;gap:8px;margin:0 0 8px;flex-wrap:wrap}
.ui-fp-busca{flex:1 1 180px;min-width:0}
.ui-fp-ord{display:inline-flex;border:1px solid var(--line-strong);
 border-radius:var(--r-md);overflow:hidden}
.ui-fp-ord button{border:0;padding:7px 11px;font-size:12px;cursor:pointer;
 background:var(--panel-2);color:var(--text-muted)}
.ui-fp-ord button + button{border-left:1px solid var(--line-strong)}
.ui-fp-ord button[aria-pressed="true"]{background:var(--accent-fraco);color:var(--text)}
.ui-fp-ord button[data-sentido="asc"]::after{content:" ▲";font-size:9px}
.ui-fp-ord button[data-sentido="desc"]::after{content:" ▼";font-size:9px}
.ui-fp-cabl{display:grid;grid-template-columns:minmax(0,1fr) 128px;gap:8px;
 padding:5px 10px;font:600 10px/1.4 var(--font-mono);letter-spacing:.4px;
 text-transform:uppercase;color:var(--text-dim);border-bottom:1px solid var(--line)}
.ui-fp-lista{max-height:360px;min-height:180px;overflow:auto;
 border:1px solid var(--line);border-top:0;border-radius:0 0 var(--r-md) var(--r-md);
 padding:4px}
.ui-fp-item{display:grid;grid-template-columns:minmax(0,1fr) 128px;gap:8px;
 align-items:center;padding:6px 10px;border-radius:6px;cursor:pointer;
 font-size:12.5px;color:var(--text-muted)}
.ui-fp-item .ui-fp-n{display:flex;align-items:center;gap:7px;min-width:0;
 overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ui-fp-item .ui-fp-d{font:400 11.5px/1.3 var(--font-mono);color:var(--text-dim);
 font-variant-numeric:tabular-nums}
.ui-fp-item:hover,.ui-fp-item:focus-visible{background:var(--panel-2);
 color:var(--text);outline:0}
.ui-fp-item.vazio{cursor:default;display:block;color:var(--text-dim)}
.ui-fp-msg{font-size:12px;color:var(--text-dim);margin:6px 0 0;min-height:16px}
.ui-fp-pe{display:flex;align-items:center;gap:8px;margin-top:12px;flex-wrap:wrap}
.ui-fp-esp{flex:1 1 auto}
@media (max-width:640px){
 .ui-fp-corpo{grid-template-columns:1fr}
 .ui-fp-lado{max-height:150px}
 .ui-fp-cabl,.ui-fp-item{grid-template-columns:minmax(0,1fr) 104px}
}
"""


def tag_de_funcao(icone_txt, nome, chave_modulo=u""):
    cor, fraca = _COR_DO_MODULO.get(chave_modulo, (u"--accent", u"--accent-fraco"))
    return (u'<h1 class="ui-fn-tag" style="--ui-fn-cor:var(%s);--ui-fn-fraco:var(%s)">'
            u'<span class="ui-fn-ic" aria-hidden="true">%s</span>'
            u'<span data-radai-frase>%s</span></h1>'
            % (cor, fraca, icone_de(icone_txt), _esc(nome)))


def cabeca_de_funcao(icone_txt, nome, frase, ajuda_html=u"", chave_modulo=u""):
    return (u'<header class="ui-fn">'
            u'<div class="ui-fn-tit">%s%s</div>'
            u'<p class="ui-fn-frase" data-radai-frase>%s</p></header>'
            % (tag_de_funcao(icone_txt, nome, chave_modulo), ajuda_html,
               _esc(frase)))


def alerta(html, esquerda=False):
    # GUARDA: `div` e não `p` — `p` é bloco do tradutor e perderia o ponto.
    return (u'<div class="ui-alerta%s"><span class="pt" aria-hidden="true"></span>'
            u'<span data-radai-frase>%s</span></div>'
            % (u" esq" if esquerda else u"", html))


def guias(ident, abas, ativa=None, cor_var=u"", esquerda=False, lembrar=False):
    ident = _esc(ident)
    if ativa is None and abas:
        ativa = abas[0][0]
    faixa, paineis = [], []
    for chave, rotulo, html in abas:
        k = _esc(chave)
        sel = (chave == ativa)
        faixa.append(
            u'<button type="button" role="tab" class="ui-guia" id="%s-t-%s" '
            u'data-guia="%s" aria-controls="%s-p-%s" aria-selected="%s" '
            u'tabindex="%s"><span data-radai-frase>%s</span></button>'
            % (ident, k, k, ident, k, u"true" if sel else u"false",
               u"0" if sel else u"-1", _esc(rotulo)))
        paineis.append(
            u'<div class="ui-guias-painel" role="tabpanel" id="%s-p-%s" '
            u'aria-labelledby="%s-t-%s"%s>%s</div>'
            % (ident, k, ident, k, u"" if sel else u" hidden", html))
    estilo = (u' style="--ui-guia-cor:var(%s)"' % cor_var) if cor_var else u""
    return (u'<div class="ui-guias%s" id="%s" data-ativa="%s"%s%s>'
            u'<div class="ui-guias-faixa" role="tablist">%s</div>%s</div>'
            % (u" esq" if esquerda else u"", ident, _esc(ativa or u""), estilo,
               u" data-lembrar" if lembrar else u"", u"".join(faixa),
               u"".join(paineis)))


TITULO_DO_POPUP_DE_SERIE = u"Escolher a série"


def abas_de_serie(ident, abas, padrao=None, cor_var=u"", lembrar=False):
    return guias(ident, abas, ativa=padrao, cor_var=cor_var, esquerda=True,
                 lembrar=lembrar)


def popup_de_serie(ident, corpo, titulo=TITULO_DO_POPUP_DE_SERIE,
                   sozinho=False, largura=1180):
    ident = _esc(ident)
    return (u'<div class="ui-ps-casa" id="%s_casa" hidden>'
            u'<div class="ui-ps" id="%s" data-ui-ps data-titulo="%s" '
            u'data-largura="%d"%s>%s</div></div>'
            % (ident, ident, _esc(titulo), int(largura),
               u" data-sozinho" if sozinho else u"", corpo))


def cartao_de_serie(ident, popup, titulo, vazio=u"nenhuma série aberta",
                    icone_nome=u"pasta", chave_modulo=u"", contexto=u"",
                    numero=u"", ident_rot=u""):
    cor, fraca = _COR_DO_MODULO.get(chave_modulo, (u"--accent", u"--accent-fraco"))
    marca = _esc(numero) if numero else icone(icone_nome)
    return (u'<button type="button" class="ui-cartao" id="%s" '
            u'data-ui-ps-abre="%s"%s aria-haspopup="dialog" '
            u'aria-expanded="false" '
            u'style="--ui-cartao-cor:var(%s);--ui-cartao-fraco:var(%s)">'
            u'<span class="ui-cartao-ic" aria-hidden="true">%s</span>'
            u'<span class="ui-cartao-tx"><span class="ui-cartao-tit" '
            u'data-radai-frase>%s</span><span class="ui-cartao-rot"%s>'
            u'<span data-radai-frase>%s</span></span></span>'
            u'<span class="ui-cartao-seta" aria-hidden="true">%s</span>'
            u'</button>'
            % (_esc(ident), _esc(popup),
               (u' data-ui-ps-ctx="%s"' % _esc(contexto)) if contexto else u"",
               cor, fraca, marca, _esc(titulo),
               (u' id="%s"' % _esc(ident_rot)) if ident_rot else u"",
               _esc(vazio), icone(u"direita")))


def area_de_envio(ident, titulo=u"Arraste para cá, ou clique para carregar",
                  dica=u"Pastas, vários arquivos ou um .zip do exame",
                  aceita=u"", extra=u""):
    ac = (u' accept="%s"' % _esc(aceita)) if aceita else u""
    return (u'<div class="ui-envio" id="%s" tabindex="0" role="button" '
            u'aria-label="%s">'
            u'<input type="file" class="ui-envio-arq" multiple%s>'
            u'<input type="file" class="ui-envio-dir" webkitdirectory multiple>'
            u'<span class="ui-envio-ic" aria-hidden="true">%s</span>'
            u'<span class="ui-envio-tit" data-radai-frase>%s</span>'
            u'<span class="ui-envio-dica" data-radai-frase>%s</span>'
            u'<span class="ui-envio-bts">'
            u'<button type="button" class="ui-bt" data-envio="arquivos">%s'
            u'<span data-radai-frase>Escolher arquivos</span></button>'
            u'<button type="button" class="ui-bt" data-envio="pasta">%s'
            u'<span data-radai-frase>Escolher pasta</span></button>%s</span>'
            u'<span class="ui-envio-barra"><i></i></span>'
            u'<span class="ui-envio-est" role="status"></span></div>'
            % (_esc(ident), _esc(titulo), ac, icone(u"subir"), _esc(titulo),
               _esc(dica), icone(u"arquivo"), icone(u"pasta"), extra or u""))


_COR_DO_MODULO = {
    u"bridge": (u"--mod-bridge", u"--mod-bridge-fraco"),
    u"autocontorno": (u"--mod-auto", u"--mod-auto-fraco"),
    u"recon3d": (u"--mod-recon", u"--mod-recon-fraco"),
    u"nidus": (u"--mod-nidus", u"--mod-nidus-fraco"),
    u"elastic": (u"--mod-elastic", u"--mod-elastic-fraco"),
    u"bolus": (u"--mod-bolus", u"--mod-bolus-fraco"),
}


def folha():
    return (u'<style id="%s">' % MARCA_CSS) + TOKENS + CASCA + PASSOS \
        + AJUDA + BOTOES + MOVIMENTO + CONTROLES + TRANSICOES + CSS_ICONES \
        + COMPONENTES + CSS_EXPLORADOR + u"</style>"


def _esc(t):
    return (str(t if t is not None else u"").replace(u"&", u"&amp;")
            .replace(u"<", u"&lt;").replace(u">", u"&gt;").replace(u'"', u"&quot;"))


def ajuda(*paragrafos, **kw):
    direita = kw.get("direita", False)
    corpo = u"".join(u"<p>%s</p>" % p for p in paragrafos if p)
    return (u'<span class="ui-ajuda%s" tabindex="0" aria-label="ajuda">?'
            u'<span class="ui-balao">%s</span></span>'
            % (u" dir" if direita else u"", corpo))


def passo(num, titulo, corpo, ident=u"", sub=u"", ajuda_html=u"",
          fechado=False, inativo=False):
    classes = u"ps-cx"
    if fechado or inativo:
        classes += u" fechado"
    if inativo:
        classes += u" inativo"
    return (u'<section class="%s"%s>'
            u'<h2 class="ps-cab"%s><span class="ps-num">%s</span>'
            u'<span data-radai-frase>%s</span>%s%s'
            u'<span class="ps-seta">&#9662;</span></h2>'
            u'<div class="ps-corpo">%s</div></section>'
            % (classes, (u' id="%s"' % _esc(ident)) if ident else u"",
               u"" if inativo else u' tabindex="0" role="button"',
               _esc(num), _esc(titulo),
               (u'<span class="ps-sub">%s</span>' % _esc(sub)) if sub else u"",
               ajuda_html, corpo))


_ATRIBUTOS_DA_OPCAO = ((u"icone", u"data-ui-icone"), (u"balao", u"data-ui-balao"),
                       (u"titulo", u"title"))


def segmentado(ident, opcoes, valor=None, rotulo=u"", embaralhar=False):
    partes = []
    for op in opcoes:
        v, txt = op[0], op[1]
        extra = (op[2] if len(op) > 2 else None) or {}
        attrs = u"".join(u' %s="%s"' % (nome, _esc(extra[chave]))
                         for chave, nome in _ATRIBUTOS_DA_OPCAO if extra.get(chave))
        partes.append(u'<option value="%s"%s%s>%s</option>'
                      % (_esc(v), attrs,
                         u" selected" if (valor is not None and v == valor) else u"",
                         _esc(txt)))
    return (u'<select id="%s" data-ui-seg%s%s>%s</select>'
            % (_esc(ident), u'="embaralhar"' if embaralhar else u"",
               (u' aria-label="%s"' % _esc(rotulo)) if rotulo else u"",
               u"".join(partes)))


_PREFIXO_ICO = u"@ICO_"


def _resolver_icones(pagina):
    if not pagina or _PREFIXO_ICO not in pagina:
        return pagina
    for nome in _TRACOS:
        marca = u"@ICO_%s@" % nome.upper()
        if marca in pagina:
            pagina = pagina.replace(marca, icone(nome))
    return pagina


def aplicar(pagina):
    pagina = _resolver_icones(pagina)
    pagina = _pendurar_icone(pagina)
    if not pagina or MARCA_CSS in pagina:
        return pagina
    baixa = pagina.lower()
    fim_head = baixa.find(u"</head>")
    if fim_head < 0:
        return pagina
    saida = (pagina[:fim_head] + TEMA_JS + folha() + JS + COMPONENTES_JS
             + pagina[fim_head:])
    fim_corpo = saida.lower().rfind(u"</body>")
    if fim_corpo < 0:
        return saida
    return saida[:fim_corpo] + VEU + moldes_de_icone() + saida[fim_corpo:]


_SVG = (u'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        u'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" '
        u'width="1em" height="1em" aria-hidden="true" focusable="false" '
        u'class="ui-ic">%s</svg>')

_TRACOS = {
    u"power":   u'<path d="M12 4v8"/><path d="M6.3 7.3a8 8 0 1 0 11.4 0"/>',
    u"lua":     u'<path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a6.8 6.8 0 0 0 10.5 10.5z"/>',
    u"sol":     u'<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4'
                u'M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    u"monitor": u'<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>',
    u"pasta":  u'<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    u"disco":  u'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="2.4"/>'
               u'<path d="M12 6.2a5.8 5.8 0 0 1 5.8 5.8"/>',
    u"mover":   u'<path d="M12 3v18M3 12h18"/><path d="M9 6l3-3 3 3M9 18l3 3 3-3'
                u'M6 9l-3 3 3 3M18 9l3 3-3 3"/>',
    u"duvida":  u'<circle cx="12" cy="12" r="9"/><path d="M9.2 9.3a2.9 2.9 0 0 1 5.6 1'
                u'c0 1.9-2.8 2.3-2.8 4"/><path d="M12 17.6h.01"/>',
    u"estrela": u'<path d="M12 3.6l2.6 5.3 5.8.8-4.2 4.1 1 5.8-5.2-2.7-5.2 2.7 1-5.8'
                u'-4.2-4.1 5.8-.8z"/>',
    u"zoom_mais":  u'<circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.3 15.3L20 20M10.5 7.8v5.4M7.8 10.5h5.4"/>',
    u"zoom_menos": u'<circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.3 15.3L20 20M7.8 10.5h5.4"/>',
    u"inverter":   u'<circle cx="12" cy="12" r="8.5"/><path d="M12 3.5a8.5 8.5 0 0 1 0 17z" fill="currentColor"/>',
    u"caixa":      u'<path d="M4 8V4h4M16 4h4v4M20 16v4h-4M8 20H4v-4"/><rect x="8.5" y="8.5" width="7" height="7" rx="1"/>',
    u"manual":  u'<path d="M4 4.5A1.5 1.5 0 0 1 5.5 3H19v15H5.5A1.5 1.5 0 0 0 4 19.5z"/>'
                u'<path d="M4 19.5A1.5 1.5 0 0 1 5.5 18H19v3H5.5A1.5 1.5 0 0 1 4 19.5z"/>'
                u'<path d="M8 7.5h7M8 10.5h7"/>',
    u"obra":    u'<path d="M3 20h18"/><path d="M5 20V9.5L12 5l7 4.5V20"/>'
                u'<path d="M5 12.5l14 5M19 12.5l-14 5"/>',
    u"pacote":  u'<path d="M21 8.5v7a1.5 1.5 0 0 1-.8 1.3l-7.5 4a1.5 1.5 0 0 1-1.4 0'
                u'l-7.5-4A1.5 1.5 0 0 1 3 15.5v-7"/>'
                u'<path d="M3.3 7.7l8 4.3a1.5 1.5 0 0 0 1.4 0l8-4.3"/>'
                u'<path d="M12 12.4V21"/>'
                u'<path d="M11.3 3.2l-7.5 4a1.5 1.5 0 0 0 0 2.6"/>'
                u'<path d="M12.7 3.2l7.5 4a1.5 1.5 0 0 1 0 2.6"/>',
    u"fechar":   u'<path d="M6 6l12 12M18 6L6 18"/>',
    u"esquerda": u'<path d="M19 12H5M11 6l-6 6 6 6"/>',
    u"direita":  u'<path d="M5 12h14M13 6l6 6-6 6"/>',
    u"acima":    u'<path d="M12 19V5M6 11l6-6 6 6"/>',
    u"subir":    u'<path d="M12 16V4M7 9l5-5 5 5"/><path d="M4 15v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3"/>',
    u"mais":     u'<path d="M12 5v14M5 12h14"/>',
    u"arquivo":  u'<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/>',
    u"rodar":    u'<path d="M7 4.8v14.4a.8.8 0 0 0 1.2.7l11.3-7.2a.8.8 0 0 0 0-1.4L8.2 4.1A.8.8 0 0 0 7 4.8z"/>',
    u"carrinho": u'<path d="M4 6h16M4 12h16M4 18h10"/>',
    u"alerta":   u'<path d="M10.3 4.2L2.6 17.6A2 2 0 0 0 4.3 20.6h15.4a2 2 0 0 0 1.7-3L13.7 4.2a2 2 0 0 0-3.4 0z"/>'
                 u'<path d="M12 9.5v4.5M12 17.2h.01"/>',
    u"desmarcar": u'<circle cx="12" cy="12" r="9"/><path d="M9 9l6 6M15 9l-6 6"/>',
    u"contornos": u'<path d="M4.5 15.5C3 11 6 5.5 11.5 4.8s9 2.3 9 6.4-3.3 8-8.3 8-6.6-1.4-7.7-3.7z"/>'
                  u'<path d="M8.3 14.4c-.7-2.6 1.2-5.3 4.3-5.5s5 1.4 5 3.6-2.1 4.2-4.8 4.2-3.9-.6-4.5-2.3z"/>'
                  u'<circle cx="12.9" cy="12.6" r="1.1"/>',
    u"ponte":    u'<path d="M4 8h14M14 4l4 4-4 4"/><path d="M20 16H6M10 12l-4 4 4 4"/>',
    u"cubo":     u'<path d="M12 3l8 4.5v9L12 21l-8-4.5v-9z"/><path d="M4 7.5l8 4.5 8-4.5M12 12v9"/>',
    u"pulmoes":  u'<path d="M12 3.5V11M12 9.5c-.8 1.3-2 1.9-3 1.9M12 9.5c.8 1.3 2 1.9 3 1.9"/>'
                 u'<path d="M9.6 6.6C6.2 7.4 4 11.6 4 16.6c0 2.1 1.1 3.4 3 3.4 2.4 0 3.6-1.8 3.6-4.7V8"/>'
                 u'<path d="M14.4 6.6c3.4.8 5.6 5 5.6 10 0 2.1-1.1 3.4-3 3.4-2.4 0-3.6-1.8-3.6-4.7V8"/>',
    u"vaso":     u'<path d="M12 21v-5.5c0-2.2-1.2-3.3-3.2-4.6S5 7.6 5 4"/>'
                 u'<path d="M12 15.5c0-2.2 1.2-3.3 3.2-4.6S19 7.6 19 4"/>'
                 u'<path d="M8.8 10.9C8.8 8.4 10 6.3 12 4.2M15.2 10.9c.2-1.6 1.1-3 2.4-4"/>',
    u"cruzamento": u'<ellipse cx="12" cy="12" rx="9" ry="3.6" transform="rotate(32 12 12)"/>'
                   u'<ellipse cx="12" cy="12" rx="9" ry="3.6" transform="rotate(-32 12 12)"/>'
                   u'<circle cx="12" cy="12" r="1.4" fill="currentColor"/>',
    u"malha":    u'<path d="M4 6.5c3 1.2 5-1 8 0s5 1.2 8 0M4 12c3 1.6 5-1.6 8 0s5 1.6 8 0M4 17.5c3 1.2 5-1 8 0s5 1.2 8 0"/>'
                 u'<path d="M6.5 4c1.2 3-1 5 0 8s1.2 5 0 8M12 4c1.6 3-1.6 5 0 8s1.6 5 0 8M17.5 4c1.2 3-1 5 0 8s1.2 5 0 8"/>',
    u"camadas":  u'<path d="M3 19.5c2-6.5 16-6.5 18 0"/><path d="M3 15c2-6.5 16-6.5 18 0"/>'
                 u'<path d="M3 15v4.5M21 15v4.5"/>',
    u"exportar": u'<path d="M3 12h12.5M11.5 7l5 5-5 5M20 4.5v15"/>',
    u"converter": u'<rect x="3" y="3.5" width="8" height="8" rx="1.5"/><path d="M5.2 9.7l1.9-2.4 1.7 1.7"/>'
                  u'<path d="M7 14.5v1.5a2 2 0 0 0 2 2h4M11 16l2 2-2 2"/>'
                  u'<rect x="15" y="12" width="6" height="9" rx="1.2"/><path d="M17 15h2M17 17.5h2"/>',
    u"engrenagem": u'<path d="M9.3 3l.6-1h4.2l.6 2 1.8 1 2-.4 2.1 3.6-1.4 1.6v2.1l1.4 1.6-2.1 3.6-2-.4'
                   u'-1.8 1-.6 2H9.9l-.6-2-1.8-1-2 .4L3.4 14l1.4-1.6v-2.1L3.4 8.7l2.1-3.6 2 .4 1.8-1Z"/>'
                   u'<circle cx="12" cy="10.9" r="3"/>',
    u"inicio":   u'<path d="M4 11l8-7 8 7"/><path d="M6 9.5V20h12V9.5"/>',
    u"olho":     u'<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/>'
                 u'<circle cx="12" cy="12" r="3"/>',
    u"lapis":    u'<path d="M15.5 4.5l4 4L8 20H4v-4z"/><path d="M13 7l4 4"/>',
}


def icone(nome):
    tracos = _TRACOS.get(nome)
    return (_SVG % tracos) if tracos else u""


GLIFOS = {
    u"◈": u"contornos", u"⇄": u"ponte", u"◧": u"cubo", u"◑": u"pulmoes",
    u"⌇": u"vaso", u"◎": u"cruzamento", u"⧉": u"malha", u"◒": u"camadas",
    u"⇥": u"exportar", u"⚙": u"engrenagem", u"⌂": u"inicio", u"◉": u"olho",
    u"▶": u"rodar", u"◐": u"lua", u"✎": u"lapis",
}


def icone_de(valor):
    v = valor or u""
    if v in _TRACOS:
        return icone(v)
    if v in GLIFOS:
        return icone(GLIFOS[v])
    return v


CSS_ICONES = u"""
.ui-ic{display:inline-block;vertical-align:-.13em;flex:0 0 auto}
.ui-ic + *{margin-left:.5em}
button .ui-ic,.ui-bt .ui-ic,.btn .ui-ic{margin-right:.5em}
"""


MARCA_ICONE = u'rel="icon" href="/favicon.svg"'

LINKS_ICONE = u"""
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="alternate icon" href="/favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="/favicon.png">
"""


def _pendurar_icone(pagina):
    if not pagina or MARCA_ICONE in pagina:
        return pagina
    fim = pagina.lower().find(u"</head>")
    if fim < 0:
        return pagina
    return pagina[:fim] + LINKS_ICONE + pagina[fim:]


def montar_icone(app):
    import os
    from fastapi.responses import Response

    AQUI = os.path.dirname(os.path.abspath(__file__))
    TIPOS = {"favicon.svg": "image/svg+xml",
             "favicon.ico": "image/x-icon",
             "favicon.png": "image/png"}
    _marcas = {}

    def _servir(nome):
        caminho = os.path.join(AQUI, nome)
        try:
            with open(caminho, "rb") as f:
                dados = f.read()
        except Exception:
            return Response(status_code=404)
        if nome not in _marcas:
            import hashlib
            _marcas[nome] = '"%s"' % hashlib.sha256(dados).hexdigest()[:20]
        return Response(
            content=dados, media_type=TIPOS[nome],
            headers={"ETag": _marcas[nome],
                     "Cache-Control": "no-cache"})

    @app.get("/favicon.svg")
    def _fav_svg():
        return _servir("favicon.svg")

    @app.get("/favicon.ico")
    def _fav_ico():
        return _servir("favicon.ico")

    @app.get("/favicon.png")
    def _fav_png():
        return _servir("favicon.png")
