"""Station FAST study comparison. All displayed geometry and colours come from the delivered RTSTRUCT."""
import json
from html import escape

from radai_fast_config import STUDY_FAST, dados_para_o_visor
from radai_fast_i18n import LANGS, ROWS


def _text(key):
    return '<span data-fast-text="%s" data-radai-t="1">%s</span>' % (key, escape(ROWS[key][0]))


def _barra_de_esforco():
    niveis = len(STUDY_FAST)
    return ('<div class="effort-rail" data-radai-t="1">'
            '<div class="effort-label" aria-hidden="true"><span class="effort-name"></span></div>'
            '<div class="effort-track t-mslider"><div class="effort-bed" aria-hidden="true">'
            '<span class="effort-fill t-mslider-fill"></span><span class="effort-stops">%s</span>'
            '<span class="t-mslider-runner"><span class="effort-thumb t-mslider-thumb"></span></span></div>'
            '<input class="effort-input" type="range" min="0" max="%d" value="%d" step="1"'
            ' aria-label="%s"></div></div>' % (
                '<i></i>' * niveis, niveis - 1, list(STUDY_FAST).index('extra'),
                escape(ROWS["title"][0], quote=True)))


def page(html, *, estudo=None, caso=False):
    from radai_ui import icone

    card = ('<a class="cfg-card" href="#ps_fast" data-alvo="ps_fast"><span class="cab">'
            '<span class="ic" aria-hidden="true">%s</span><span class="n">7</span></span>'
            '<h3>%s</h3><p>%s</p></a>' % (icone("contornos"), _text("title"), _text("compare")))
    choices = []
    for ident, (mm, _) in STUDY_FAST.items():
        choices.append('<button type="button" class="fast-choice" data-study-card="%s" aria-controls="fast-canvas" aria-pressed="false" disabled>'
                       '<b>%s</b><small data-fast-mm="%s"></small>'
                       '<small>%s · <strong class="fast-clock"></strong></small>'
                       '<small class="fast-vertices" hidden></small></button>' % (ident, _text(ident), mm, _text("processingTime")))
    heading = ('<div class="fast-heading"><h2 id="effort-modal-title">%s</h2>'
               '<button type="button" id="fast-info-toggle" aria-label="%s" aria-expanded="false" '
               'aria-controls="fast-info">?</button></div>' % (_text("title"), escape(ROWS["effortHelp"][0], quote=True)))
    viewer = (
        '<div class="fast-settings" id="effort-view">'
        '<section id="fast-info" aria-label="%s" hidden><h3>%s</h3><p>%s</p><p>%s</p>'
        '<p class="fast-attribution"><span id="fast-case-source" data-radai-t="1"></span> <span id="fast-credits"></span>'
        '<a id="effort-model-references" href="%s" target="_blank" rel="noopener noreferrer">%s</a></p>'
        '<h3 id="fast-profile-name" data-radai-t="1"></h3>'
        '<p id="fast-description" data-radai-t="1"></p><p id="fast-models" data-radai-t="1" hidden></p>'
        '<p id="fast-profile-rois" data-radai-t="1" hidden></p>'
        '<details id="fast-all"><summary>%s <b class="fast-count"></b></summary><div class="fast-legend"></div></details>'
        '<p id="fast-missing-rois" data-radai-t="1" hidden></p>'
        '<p id="fast-profile-vertices" data-radai-t="1" hidden></p><p id="fast-time-basis">%s</p>'
        '<p id="fast-profile-timing" data-radai-t="1"></p><p class="fast-tps-note">%s</p>'
        '<p id="fast-cache" data-radai-t="1" hidden></p><p>%s</p>'
        '<details id="fast-help"><summary>%s</summary><p>%s</p><p>%s</p></details></section>'
        '<div class="fast-workspace"><div class="fast-pick">%s<div class="fast-cards">%s</div></div>'
        '<div class="fast-study"><div class="fast-viewport" tabindex="0" role="group"><figure class="fast-plane">'
        '<figcaption id="fast-title-choice" data-radai-t="1"></figcaption><div class="fast-frame">'
        '<canvas id="fast-canvas" aria-labelledby="fast-title-choice fast-readout" hidden></canvas><div class="fast-empty" hidden>%s</div>'
        '<div class="fast-compass" aria-hidden="true" hidden><i>A</i><i>P</i><i>R</i><i>L</i></div></div></figure></div>'
        '<label for="fast-slice" id="fast-readout" data-radai-t="1"></label><input type="range" id="fast-slice" min="1" max="1" step="1" disabled>'
        '<small class="fast-in-plane" hidden></small><div class="fast-legend" id="fast-view-legend" data-radai-t="1"></div>'
        '</div></div></div>'
        % (escape(ROWS["effortHelp"][0], quote=True), _text("studyTitle"), _text("fixedPublic"), _text("studyCase"),
           "bibliografia.html#modelos" if estudo is not None else "/bibliografia#modelos", _text("weightsRefs"), _text("allRois"),
           _text("relativeBasis"), _text("tpsVertices"), _text("allEngines"), _text("compare"), _text("tcNative"), _text("tcScroll"),
           _barra_de_esforco(), "".join(choices), _text("tcNoImage")))
    config = ('<section id="ps_fast" class="ps-cx fechado" hidden><h2 class="ps-cab" tabindex="0" role="button">'
              '<span class="ps-num">7</span>%s<span class="ps-seta">▾</span></h2><div class="ps-corpo"><p id="effort-preferred"></p>'
              '<button type="button" id="effort-config-open">%s</button></div></section>' % (_text("title"),_text("compare")))
    modal = ('<dialog id="effort-modal" aria-labelledby="effort-modal-title"><header>%s'
             '<button type="button" id="effort-close" autofocus>×</button></header><div class="effort-scroll">%s</div>'
             '<footer><output id="effort-status" role="status"></output><button type="button" id="effort-apply" hidden>%s</button>'
             '<button type="button" id="effort-save">%s</button></footer></dialog>' % (
                 heading,viewer,_text("applyCase"),_text("savePref")))
    if estudo is not None:
        section='<section id="esforco-publico">%s%s</section>'%(heading,viewer)
    elif caso:
        section=''
        html=html.replace('</body>',modal+'</body>',1)
    else:
        section=config
        html=html.replace('</body>',modal+'</body>',1)
    catalog = {code:{k:row[i] for k,row in ROWS.items()} for i,code in enumerate(LANGS)}
    def encode(value):
        return json.dumps(value,ensure_ascii=False,separators=(",",":")).replace("<", r"\u003c")
    script = SCRIPT
    if estudo is not None:
        inicio, fim = script.index("/*station-actions*/"), script.index("/*end-station-actions*/")
        script = script[:inicio] + script[fim+len("/*end-station-actions*/"):]
    script = script.replace("@WORDS@", encode(catalog)).replace("@STATIC@", encode(dados_para_o_visor(estudo) if estudo is not None else None))
    if estudo is None:
        sprite = "'/api/fast/study/'+id+'/'+(page+1)"
        load = "fetch('/api/fast/study',{cache:'no-store'}).then(r=>r.ok?r.json():{}).catch(()=>({})).then(data=>{study=data;loaded=true;render()});"
    else:
        sprite, load = "id==='ct'?study.basePages[page]:study.profiles[id].pages[page]", "study=staticStudy;loaded=true;render();"
    script = script.replace("@SPRITE_URL@", sprite).replace("@LOAD_STUDY@", load)
    return (html.replace("@FAST_CARD@", card).replace("@FAST_SECTION@", section)
            .replace("</head>", "<style>" + CSS + "</style></head>", 1)
            .replace("</body>", script + "</body>", 1))


def visor_estatico(dados, idioma="pt-BR"):
    """Publica o mesmo visor com metadados embutidos e sprites relativos ao próprio HTML."""
    if idioma not in LANGS:
        idioma = "pt-BR"
    html = '''<!doctype html><html lang="%s"><head><meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <meta name="referrer" content="no-referrer">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src 'self' file:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'none'; base-uri 'none'; form-action 'none'">
    <title>Local Suite · RTSTRUCT</title>
    <style>:root{color-scheme:dark;--text:#e6eef7;--text-muted:#aebcc9;--accent:#88c7fa;--panel-2:#152332;--line-strong:#354859}
    *{box-sizing:border-box}body{margin:0;background:#0b131c;color:var(--text);font:16px/1.45 system-ui,sans-serif}
    main{max-width:1400px;margin:auto;padding:clamp(10px,2vw,30px)}h2{font-size:1.2rem;margin:0 0 1rem}
    a{color:var(--accent)}button{font:inherit}.ps-num,.ps-seta{display:none}</style></head>
    <body><main>@FAST_SECTION@</main></body></html>''' % idioma
    out = page(html,estudo=dados)
    return (out.replace('class="ps-cx fechado" hidden','class="ps-cx"')
            .replace('class="ps-cab" tabindex="0" role="button"','class="ps-cab"'))


CSS = """
#effort-modal{color:var(--text,#e6eef7);background:var(--panel,#121d2b);border:1px solid var(--line-strong,#435464);padding:0;border-radius:14px;width:min(1180px,96vw);max-height:92dvh;max-width:96vw;overflow:hidden}
#effort-modal[open]{display:flex;flex-direction:column}#effort-modal::backdrop{background:#07111cbd}#effort-modal header,#effort-modal footer{display:flex;align-items:center;justify-content:space-between;gap:.6rem;flex:none;padding:12px 18px;background:var(--panel,#121d2b)}
#effort-modal header{border-bottom:1px solid var(--line,#364452)}.fast-heading{display:flex;align-items:center;gap:.6rem;min-width:0}.fast-heading h2{margin:0;font-size:1.15rem;line-height:1.3}#esforco-publico>.fast-heading{margin-bottom:.85rem}
#fast-info-toggle{display:grid;place-items:center;flex:none;width:28px;height:28px;border-radius:50%;font:600 .9rem/1 system-ui;color:var(--accent,#88c7fa);background:var(--panel-2,#152332);border:1px solid var(--line-strong,#506172);cursor:pointer}#fast-info-toggle[aria-expanded=true]{border-color:var(--accent,#88c7fa)}#fast-info-toggle:focus-visible{outline:2px solid var(--accent,#88c7fa);outline-offset:2px}
#fast-info{border:1px solid var(--line-strong,#435464);border-radius:9px;padding:1rem;margin:0 0 1rem;background:var(--panel-2,#152332);font-size:.85rem;line-height:1.45;color:var(--text-muted,#aebcc9)}#fast-info h3{color:var(--text,#e6eef7)}#fast-info p{margin:.45rem 0}#fast-profile-name{margin-top:1rem}#fast-info .fast-attribution{overflow-wrap:anywhere}#fast-info details:last-child{margin-bottom:0}
#effort-modal footer{justify-content:flex-end;border-top:1px solid var(--line,#364452)}#effort-status{margin-inline-end:auto;font-size:.8rem}#effort-modal .effort-scroll{min-height:0;overflow:auto;overscroll-behavior:contain;padding:14px 18px}
#effort-close,#effort-apply,#effort-save,#effort-config-open,.effort-help{color:var(--text,#e6eef7);background:var(--panel-2,#26384a);border:1px solid var(--line-strong,#506172);border-radius:7px;padding:7px 11px;cursor:pointer}#effort-close{font-size:1.25rem;line-height:1}#effort-apply{background:#245682;color:white}
.effort-miniform{position:relative;width:min(100%,16rem);margin:.5rem 0 .8rem}
.effort-miniform .effort-help{position:absolute;inset:4px 5px auto auto;border:0;border-radius:50%;width:32px;height:32px;padding:0;background:transparent;color:#b9c6d1}
.effort-miniform:dir(rtl) .effort-help{inset:4px auto auto 5px}
/* Transitions.dev free recipes: tabs-sliding and number-subtle-change, adapted
   to a native discrete slider. Logical positions mirror the native input in RTL. */
.effort-rail{--effort-pos:80%;--rail-ease:cubic-bezier(.22,1,.36,1);box-sizing:border-box;background:#262626;color:#f5f7fb;border:1px solid #414144;border-radius:16px;padding:9px 10px 4px;min-width:0}
.fast-pick>.effort-rail{width:min(100%,20rem);margin:0 auto .75rem}
.effort-label{display:grid;place-items:center;position:relative;min-height:25px;line-height:1.3;font:650 .91rem/1.3 system-ui,sans-serif;text-align:center;color:#c0ddf7}
.effort-miniform .effort-label{margin-inline:26px}
.effort-context{display:block;margin:0 1.25rem 3px;text-align:center;font:400 .71rem/1.3 system-ui,sans-serif;color:#b3b7bf}
.effort-label>span{grid-area:1/1;overflow-wrap:anywhere}
.effort-track{position:relative;height:38px}
.effort-bed{position:absolute;inset-inline:14px;top:50%;height:22px;margin-top:-11px;pointer-events:none}
.effort-bed::before,.effort-fill{content:"";position:absolute;inset-block:0;border-radius:20px}
.effort-bed::before{inset-inline:-10px;background:#45454a}
/* transitions.dev Magnetic slider. Thumb and fill share one continuous position. */
.t-mslider{cursor:grab;touch-action:pan-y;--mslider-snap:380ms;--mslider-grab:180ms;--mslider-grab-scale:1.06;--mslider-ease:cubic-bezier(.22,1,.36,1);--mslider-snap-ease:cubic-bezier(.34,1.45,.64,1)}
.t-mslider-fill{inset-inline:-10px;background:#0868bc;--cut:calc((100% - 20px)*(1 - var(--mslider-ratio,.8)) + 10px);clip-path:inset(0 var(--cut) 0 0)}
.t-mslider:dir(rtl) .t-mslider-fill{clip-path:inset(0 0 0 var(--cut))}
.t-mslider.is-min .t-mslider-fill{--cut:100%}
.t-mslider-runner{position:absolute;inset:0;transform:translateX(var(--effort-pos))}
.t-mslider:dir(rtl) .t-mslider-runner{transform:translateX(calc(-1 * var(--effort-pos)))}
.t-mslider-runner,.t-mslider-fill{transition:transform var(--mslider-snap) var(--mslider-snap-ease),clip-path var(--mslider-snap) var(--mslider-snap-ease)}
.t-mslider.is-grabbed .t-mslider-runner,.t-mslider.is-grabbed .t-mslider-fill{transition:none}
.t-mslider.is-grabbed .t-mslider-thumb{transform:scale(var(--mslider-grab-scale))}
.effort-stops{position:absolute;inset:0;display:flex;align-items:center;justify-content:space-between}
.effort-stops i{display:grid;width:0;place-content:center}
.effort-stops i::after{content:"";border-radius:50%;width:4px;height:4px;background:#d7edff80}
.effort-thumb{position:absolute;inset-inline-start:0;top:50%;margin-inline-start:-12px;margin-top:-12px;width:24px;height:24px;border-radius:50%;background:#fff;box-shadow:0 1px 3px #0005;transition:transform var(--mslider-grab) var(--mslider-ease)}
.effort-rail .effort-input{display:block;box-sizing:border-box;width:100%;min-width:0;max-width:none;position:absolute;inset:0;margin:0;padding:0;height:100%;border:0;opacity:0;appearance:none;background:transparent;pointer-events:none}
.t-mslider.is-grabbed{cursor:grabbing}
.effort-input::-webkit-slider-thumb{appearance:none;border:0;width:28px;height:28px}
.effort-input::-moz-range-thumb{border:0;width:28px;height:28px}
.effort-rail:has(.effort-input:focus-visible){outline:2px solid #8ccaff;outline-offset:2px}
.effort-miniform .effort-help:focus-visible{outline:2px solid #8ccaff;outline-offset:-2px}
.effort-rail[data-effort=ultra] .effort-fill{background:linear-gradient(90deg,#0868bc,#6550bc,#8657d1);background-size:140% 100%;animation:effort-ultra 4s ease-in-out infinite alternate}
.effort-rail[data-effort=ultra] .effort-label{color:#decafa}
.effort-label.changing .effort-name{animation:effort-name-in 455ms var(--rail-ease) both}
.effort-label .effort-was{pointer-events:none;animation:effort-name-out 455ms var(--rail-ease) forwards}
@keyframes effort-name-in{from{opacity:0;transform:translateY(calc(var(--dir)*.14em));filter:blur(.042em)}}
@keyframes effort-name-out{to{opacity:0;transform:translateY(calc(var(--dir)*-.14em));filter:blur(.042em)}}
@keyframes effort-ultra{to{background-position:100% 50%}}
@media(prefers-reduced-motion:reduce){.effort-rail .t-mslider-runner,.effort-rail .effort-fill,.effort-rail .effort-thumb,.effort-rail .effort-name{transition:none!important;animation:none!important}.effort-label .effort-was{display:none}.t-mslider.is-grabbed .t-mslider-thumb{transform:none}}
@media(forced-colors:active){.effort-bed{display:none}.effort-rail .effort-input{opacity:1;appearance:auto;accent-color:Highlight;pointer-events:auto}.effort-input::-webkit-slider-thumb{appearance:auto}}
.fast-settings [hidden]{display:none!important}.fast-settings{--hi:var(--accent,#69b7fa);color:var(--text,inherit)}
.fast-settings h3{font-size:1rem;margin:0 0 .45rem}.fast-workspace{display:grid;gap:.75rem}.fast-viewport{touch-action:pan-x}
.fast-plane{margin:0;min-width:0}.fast-plane figcaption{margin:0 0 4px;font-size:.82rem;font-weight:650}
.fast-frame{display:grid;place-items:center;position:relative;min-height:160px;height:clamp(230px,48vh,540px);overflow:hidden;border:1px solid var(--line-strong,#3a4755);border-radius:8px;background:#070b10}
.fast-frame canvas{display:block;width:100%;height:100%;min-height:0;object-fit:contain}.fast-settings :focus-visible{outline:2px solid var(--hi);outline-offset:2px}
.fast-empty{padding:20px;text-align:center;color:var(--text-muted)}.fast-compass i{position:absolute;color:#fff;font:600 .76rem sans-serif;background:#0008;padding:2px 4px}
.fast-compass i:nth-child(1){top:4px;left:50%}.fast-compass i:nth-child(2){bottom:4px;left:50%}.fast-compass i:nth-child(3){left:4px;top:50%}.fast-compass i:nth-child(4){right:4px;top:50%}
#fast-readout{display:block;font-size:.85rem;margin:.4rem 0 0}#fast-slice{width:100%;min-height:28px;accent-color:var(--hi);margin:0}
.fast-legend{display:flex;flex-wrap:wrap;gap:5px 12px;font-size:.76rem;line-height:1.3}.fast-legend>span{display:inline-flex;align-items:center;gap:5px;overflow-wrap:anywhere}
.fast-legend>span::before{content:'';flex:none;width:15px;height:3px;background:var(--ink);border-radius:2px}.fast-settings details{margin:.65rem 0}
.fast-settings summary{cursor:pointer;font-size:.85rem}.fast-settings details .fast-legend{margin:.5rem 0}#fast-credits,.fast-note{font-size:.81rem;color:var(--text-muted);line-height:1.45}
.fast-cards{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:6px}.fast-in-plane{display:block;margin:.2rem 0 .35rem;color:var(--text-muted);font-size:.73rem}
.fast-attribution{margin:0 0 .75rem;font-size:.78rem;line-height:1.5;color:var(--text-muted,#b7c4ce)}.fast-attribution a{color:var(--accent,#8dc4f3)}#effort-model-references{display:block;width:fit-content}
.fast-settings .fast-choice{display:flex;flex-direction:column;align-items:flex-start;justify-content:flex-start;gap:3px;min-width:0;width:100%;white-space:normal;overflow-wrap:anywhere;text-align:start;padding:7px 8px;font:inherit;line-height:1.25;border:1px solid var(--line-strong,#364757);border-radius:7px;color:var(--text,inherit);background:var(--panel-2,#18212b);cursor:pointer}
.fast-settings .fast-choice[aria-pressed=true]{border-color:var(--hi);box-shadow:inset 3px 0 var(--hi);background:var(--accent-fraco,#162d43)}
.fast-choice b{font-size:.84rem;color:var(--hi)}.fast-choice small{font-size:.74rem}.fast-clock{font-weight:650;font-variant-numeric:tabular-nums}
#fast-description,#fast-help p{font-size:.84rem;line-height:1.5}#fast-all .fast-count{font-weight:500}
@media(max-width:700px){.fast-cards{grid-template-columns:repeat(3,minmax(0,1fr))}.fast-frame{height:clamp(180px,36vh,340px)}}
"""


SCRIPT = r"""<script>
(function(){
 const root=document.getElementById('effort-view');
 if(!root)return;
 const words=@WORDS@, staticStudy=@STATIC@;
 const byId=id=>document.getElementById(id);
 const cards=Array.from(root.querySelectorAll('[data-study-card]'));
 const viewport=root.querySelector('.fast-viewport'), canvas=byId('fast-canvas'), slider=byId('fast-slice');
 const info=byId('fast-info'), help=byId('fast-info-toggle');
 const dialog=byId('effort-modal'), sprites=new Map(), ids=cards.map(c=>c.dataset.studyCard);
 const viewerRail=root.querySelector('.effort-rail'), blankRail=viewerRail.cloneNode(true);
 let study={}, selected='extra', preferred='extra', onSelect=null, requested=false, loaded=false, plane=null, paintId=0, lang='', saving=false;
 const t=()=>words[document.documentElement.lang]||words['pt-BR'];
 const number=(v,d=1)=>v.toLocaleString(document.documentElement.lang||'pt-BR',{useGrouping:false,maximumFractionDigits:d});
 const percent=(tenths,signed=false)=>new Intl.NumberFormat(document.documentElement.lang||'pt-BR',{
  style:'percent',maximumFractionDigits:1,signDisplay:signed?'always':'auto'
 }).format(tenths/1000);
 const mm=id=>({leve:6,medio:3}[id]||1.5), name=id=>t()[id];
 const grid=id=>number(mm(id))+' mm';
 const title=id=>name(id)+' · '+grid(id);
 function list(node,ids,rois){
  node.replaceChildren();
  for(const id of ids){
   const roi=rois[id], span=document.createElement('span');
   span.style.setProperty('--ink','rgb('+roi.color.join(',')+')');span.textContent=roi.name;
   span.setAttribute('data-radai-t','1');node.append(span);
  }
 }
 function credits(){
  const e=byId('fast-credits');e.replaceChildren();e.hidden=!study.url;
  if(e.hidden)return;
  e.append(study.source+' · ');
  for(const [href,label] of [[study.source_record_url,'Zenodo · '+study.source_archive_member],
    [study.source_archive_url,t().zipDataset+' ('+number(23.6)+' GB)'],
    [study.url,'DOI '+study.dataset_doi],[study.license_url,study.license]]){
   if(typeof href!=='string'||!href.startsWith('https://'))continue;
   const a=document.createElement('a');a.href=href;a.textContent=label;a.target='_blank';a.rel='noopener noreferrer';
   if(e.querySelector('a'))e.append(' · ');e.append(a);
  }
 }
 function drawSlice(id,k,renderId){
  const f=study.profiles?.[id], surface=canvas, compass=viewport.querySelector('.fast-compass');
  const notice=viewport.querySelector('.fast-empty'), labels=byId('fast-view-legend'), inPlane=root.querySelector('.fast-in-plane');
  inPlane.hidden=!f;
  surface.hidden=true;compass.hidden=true;notice.hidden=!loaded||!!f;
  if(!f){labels.replaceChildren();return}
  inPlane.textContent=t().inPlane+' · '+number(f.labelsBySlice[k].length,0);
  list(labels,f.labelsBySlice[k],f.rois);
  const perPage=study.columns*study.rowsPerPage, page=Math.floor(k/perPage), tile=k%perPage;
  function sprite(id){
   const url=@SPRITE_URL@;
   let image=sprites.get(url);
   if(!image){
    image=new Image();image.src=url;
    if(sprites.size>=10)sprites.delete(sprites.keys().next().value);
    sprites.set(url,image);
   }
   return image;
  }
  const layers=study.basePages?[sprite('ct'),sprite(id)]:[sprite(id)];
  function paint(){
   if(renderId!==paintId)return;
   if(surface.width!==study.tileWidth)surface.width=study.tileWidth;
   if(surface.height!==study.tileHeight)surface.height=study.tileHeight;
   const w=surface.width,h=surface.height;
   const ctx=surface.getContext('2d');
   for(const image of layers)ctx.drawImage(image,(tile%study.columns)*w,Math.floor(tile/study.columns)*h,w,h,0,0,w,h);
   surface.hidden=false;compass.hidden=false;
  }
  if(layers.every(image=>image.complete&&image.naturalWidth))paint();
  else Promise.all(layers.map(image=>image.decode())).then(paint).catch(()=>{if(renderId===paintId){notice.hidden=false;inPlane.hidden=true;labels.replaceChildren()}});
 }
 function draw(){
  const renderId=++paintId, hasFrames=!!study.profiles?.[selected];
  slider.disabled=!hasFrames;
  byId('fast-all').hidden=!hasFrames;
  byId('fast-title-choice').textContent=title(selected);
  let k=0;
  if(study.positionsMm){
   plane=Math.min(study.lastSlice,Math.max(study.firstSlice,plane??Math.floor((study.firstSlice+study.lastSlice)/2)));
   k=plane-study.firstSlice;slider.min=study.firstSlice;slider.max=study.lastSlice;slider.value=plane;
   const where=t().tcSlice+' '+plane+'/'+study.total_slices+' · z '+number(study.positionsMm[k],2)+' mm';
   byId('fast-readout').textContent=where;slider.setAttribute('aria-valuetext',where);viewport.setAttribute('aria-label',where);
  }else{byId('fast-readout').textContent=''}
  drawSlice(selected,k,renderId);
 }
 function timingDetail(share){
  if(!Number.isSafeInteger(share))return t().relativeMissing;
  const delta=share-1000;
  if(selected==='maximo')return t().relativeReference;
  if(!delta)return t().relativeTie;
  if(Math.abs(delta)<10)return t().relativeNear;
  return percent(delta,true)+' · '+(delta<0?t().relativeSaving:t().relativeAdded);
 }
 function vertexDelta(points,baseline){
  if(!Number.isSafeInteger(points)||!Number.isSafeInteger(baseline)||baseline<=0)return '';
  const difference=points-baseline, tenths=Math.round(1000*Math.abs(difference)/baseline);
  return tenths?percent(Math.sign(difference)*tenths,true):percent(0);
 }
 function showHelp(expanded){
  help.setAttribute('aria-expanded',String(expanded));info.hidden=!expanded;
  if(!expanded){byId('fast-help').open=false;byId('fast-all').open=false}
 }
 help.addEventListener('click',()=>showHelp(info.hidden));
 function render(){
  lang=document.documentElement.lang;
  updateRail(viewerRail,selected);
  document.querySelectorAll('[data-fast-text]').forEach(el=>el.textContent=t()[el.dataset.fastText]);
  help.setAttribute('aria-label',t().effortHelp);info.setAttribute('aria-label',t().effortHelp);
  const baseline=study.profiles?.maximo?.total_vertices;
  for(const card of cards){
   const id=card.dataset.studyCard;card.setAttribute('aria-pressed',String(id===selected));card.disabled=false;
   card.querySelector('[data-fast-mm]').textContent=grid(id)+(id==='extra'?' · '+t().factory:'');
   const profile=study.profiles?.[id], share=profile?.tempo_relativo_decimos;
   card.querySelector('.fast-clock').textContent=Number.isSafeInteger(share)?percent(share):'—';
   const vertices=card.querySelector('.fast-vertices');
   const delta=vertexDelta(profile?.total_vertices,baseline);
   vertices.hidden=!delta;
   vertices.textContent=delta?(id==='maximo'?t().vertexReference:t().vertexCount+' · '+delta):'';
  }
  const profile=study.profiles?.[selected];
  byId('fast-profile-name').textContent=t().studyChoice+' · '+title(selected);
  byId('fast-profile-timing').textContent=timingDetail(profile?.tempo_relativo_decimos);
  const count=byId('fast-profile-rois');count.hidden=!profile;
  const points=profile?.total_vertices, vertices=byId('fast-profile-vertices');
  vertices.hidden=!Number.isSafeInteger(points);
  if(!vertices.hidden){
   vertices.textContent=t().vertexCount+' · '+points.toLocaleString(lang||'pt-BR');
   const delta=vertexDelta(points,baseline);
   if(delta&&selected!=='maximo')vertices.textContent+=' ('+t().vertexVsMax.replace('{delta}',delta)+')';
  }
  const models=byId('fast-models');models.hidden=!profile?.model_names?.length;
  models.textContent=models.hidden?'':t().studyModels+' · '+profile.model_names.join(', ');
  if(profile){
   const roiIds=Object.keys(profile.rois), done=number(roiIds.length,0), asked=study.requested_rois?.length;
   count.textContent=t().roiCount+' · '+(asked?t().roiRequested.replace('{done}',done).replace('{asked}',number(asked,0)):done);
   byId('fast-all').querySelector('.fast-count').textContent='('+done+')';
   list(byId('fast-all').querySelector('.fast-legend'),roiIds,profile.rois);
  }
  const missing=byId('fast-missing-rois'), reference=study.profiles?.maximo;
  const selectedNames=new Set(Object.values(profile?.rois||{}).map(roi=>roi.name));
  const requestedNames=study.requested_rois;
  const expected=requestedNames||Object.values(reference?.rois||{}).map(roi=>roi.name);
  const absent=profile?expected.filter(n=>!selectedNames.has(n)):[];
  missing.hidden=!absent.length;
  missing.textContent=absent.length?(requestedNames?t().missingRequested:t().missingVsMax).replace('{rois}',absent.join(', ')):'';
  byId('fast-description').textContent=selected==='ultra'?t().ultraHelp:t()['finishNote'+ids.indexOf(selected)];
  byId('fast-case-source').textContent=study.kind==='reference_ct'?t().referenceCt:'';
  byId('fast-cache').hidden=!profile?.used_cache;byId('fast-cache').textContent=t().cacheNote;
  if(dialog){
   byId('effort-close').setAttribute('aria-label',t().close);
   const summary=byId('effort-preferred');if(summary)summary.textContent=t().effort+' · '+name(preferred);
   for(const el of document.querySelectorAll('.effort-miniform'))translateMini(el);
  }
  credits();if(!dialog||dialog.open)draw();
 }
 const valid=v=>ids.includes(v)?v:'extra';
 window.radaiEsforcoPreferido=function(v){preferred=valid(String(v).split('#')[0].trim());render()};
 function paintMagnet(track,ratio){
  track.style.setProperty('--effort-pos',(100*ratio)+'%');
  track.style.setProperty('--mslider-ratio',String(ratio));
  track.classList.toggle('is-min',ratio===0);
 }
 // Keep the native input for keyboard and assistive technology. Drag freely and
 // dispatch its ordinary input/change pair only when a new stop is released.
 document.addEventListener('pointerdown',event=>{
  const track=event.target.closest?.('.t-mslider');
  const input=track?.querySelector('.effort-input');
  if(!input || event.button!==0 || !event.isPrimary ||
     input.disabled || matchMedia('(forced-colors: active)').matches)return;
  const bed=track.querySelector('.effort-bed');
  const rect=bed.getBoundingClientRect();
  if(!rect.width || track.classList.contains('is-grabbed'))return;
  event.preventDefault();
  const rtl=getComputedStyle(input).direction==='rtl', pointer=event.pointerId;
  const ratioAt=x=>Math.max(0,Math.min(1,rtl?(rect.right-x)/rect.width:(x-rect.left)/rect.width));
  const last=Number(input.max);
  input.focus({preventScroll:true});
  track.classList.add('is-grabbed');
  paintMagnet(track,ratioAt(event.clientX));
  input.setPointerCapture(pointer);
  function move(e){
   if(e.pointerId===pointer)paintMagnet(track,ratioAt(e.clientX));
  }
  function finish(e){
   if(e.pointerId!==pointer)return;
   input.removeEventListener('pointermove',move);
   for(const type of ['pointerup','pointercancel','lostpointercapture'])input.removeEventListener(type,finish);
   const current=input.valueAsNumber;
   const next=e.type==='pointerup'?Math.round(ratioAt(e.clientX)*last):current;
   track.classList.remove('is-grabbed');
   paintMagnet(track,next/last);
   if(input.hasPointerCapture(pointer))input.releasePointerCapture(pointer);
   if(next===current)return;
   input.value=String(next);
   input.dispatchEvent(new Event('input',{bubbles:true}));
   input.dispatchEvent(new Event('change',{bubbles:true}));
  }
  input.addEventListener('pointermove',move);
  for(const type of ['pointerup','pointercancel','lostpointercapture'])input.addEventListener(type,finish);
 });
 function updateRail(rail,value){
  const previous=rail.dataset.effort, index=ids.indexOf(value), input=rail.querySelector('.effort-input');
  const label=rail.querySelector('.effort-label'), current=label.querySelector('.effort-name');
  rail.dataset.effort=value;
  const track=input.closest('.t-mslider');
  if(!track.classList.contains('is-grabbed'))paintMagnet(track,index/(ids.length-1));
  input.setAttribute('value',String(index));input.value=String(index);
  input.setAttribute('aria-label',t().title);input.setAttribute('aria-valuetext',name(value));
  if(current.textContent===name(value))return;
  const animate=previous&&previous!==value&&!matchMedia('(prefers-reduced-motion: reduce)').matches;
  const fresh=document.createElement('span');fresh.className='effort-name';fresh.textContent=name(value);
  label.classList.toggle('changing',Boolean(animate));
  label.replaceChildren(fresh);
  if(animate){
   label.style.setProperty('--dir',String(Math.sign(index-ids.indexOf(previous))));
   current.className='effort-was';label.append(current);
   current.addEventListener('animationend',()=>current.remove(),{once:true});
  }
 }
 function translateMini(el){
  updateRail(el.querySelector('.effort-rail'),el.dataset.value);
  el.querySelector('.effort-context').textContent=t().title;
  el.querySelector('.effort-help').setAttribute('aria-label',t().compare);
 }
 window.radaiMiniEsforco=function(i,value){
  const el=document.createElement('div');el.className='effort-miniform';el.dataset.value=valid(value);el.dataset.series=i;el.setAttribute('data-radai-t','1');
  el.innerHTML='<button type="button" class="effort-help" aria-haspopup="dialog" aria-controls="effort-modal">?</button>';
  el.prepend(blankRail.cloneNode(true));
  const context=document.createElement('small');context.className='effort-context';
  el.querySelector('.effort-label').after(context);
  translateMini(el);return el.outerHTML;
 };
 window.radaiMiniAtualizar=function(el,v){el.dataset.value=valid(v);translateMini(el)};
 /*station-actions*/
 function setCase(el,value){
  window.radaiMiniAtualizar(el,value);
  window.dispatchEvent(new CustomEvent('radai-esforco-caso',{detail:{indice:Number(el.dataset.series),valor:value}}));
 }
 document.addEventListener('input',e=>{
  if(e.target.matches('.effort-miniform .effort-input'))updateRail(e.target.closest('.effort-rail'),ids[e.target.valueAsNumber]);
 });
 document.addEventListener('change',e=>{
  if(e.target.matches('.effort-miniform .effort-input'))setCase(e.target.closest('.effort-miniform'),ids[e.target.valueAsNumber]);
 });
 document.addEventListener('click',e=>{
  const button=e.target.closest('.effort-help');if(!button)return;
  const el=button.closest('.effort-miniform');
  window.radaiEsforcoAbrir(el.dataset.value,v=>setCase(el,v));
 });
 if(dialog){
  const apply=byId('effort-apply'),save=byId('effort-save'),status=byId('effort-status');
  window.radaiEsforcoAbrir=function(v,selecionar){
   selected=valid(v||preferred);onSelect=typeof selecionar==='function'?selecionar:null;plane=null;
   showHelp(false);
   apply.hidden=!onSelect;save.disabled=saving;status.textContent='';dialog.showModal();
   dialog.querySelector('.effort-scroll').scrollTop=0;open();render();
  };
  byId('effort-config-open')?.addEventListener('click',()=>window.radaiEsforcoAbrir(preferred));
  byId('effort-close').onclick=()=>dialog.close();
  dialog.addEventListener('close',()=>{paintId++;sprites.clear();onSelect=null});
  apply.onclick=()=>{if(onSelect){onSelect(selected);dialog.close()}};
  save.onclick=async()=>{
   if(saving)return;const value=selected;saving=true;save.disabled=true;
   try{
    const r=await fetch('/api/config/estacao/salvar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({valores:{ESFORCO_PADRAO:value}})});
    if(!r.ok||!(await r.json()).ok)throw Error();
    window.radaiEsforcoPreferido(value);status.textContent=t().saved;
   }catch(e){status.textContent=t().saveError}finally{saving=false;save.disabled=false}
  };
 }
 /*end-station-actions*/
 viewerRail.querySelector('.effort-input').addEventListener('input',e=>{
  selected=ids[e.target.valueAsNumber];render();
 });
 for(const card of cards)card.addEventListener('click',()=>{
  selected=card.dataset.studyCard;
  render();
 });
 function move(delta){
  if(slider.disabled)return;
  plane=Math.max(study.firstSlice,Math.min(study.lastSlice,plane+delta));draw();
 }
 slider.addEventListener('input',()=>{plane=Number(slider.value);draw()});
 viewport.addEventListener('wheel',e=>{if(!slider.disabled&&e.deltaY&&!e.ctrlKey){e.preventDefault();move(Math.sign(e.deltaY))}},{passive:false});
 viewport.addEventListener('keydown',e=>{
  const step={ArrowUp:-1,ArrowLeft:-1,ArrowDown:1,ArrowRight:1,PageUp:-10,PageDown:10}[e.key];
  if(step){e.preventDefault();move(step)}
 });
 let touchY=null;
 viewport.addEventListener('pointerdown',e=>{if(e.pointerType==='touch'){touchY=e.clientY;viewport.setPointerCapture(e.pointerId)}});
 viewport.addEventListener('pointermove',e=>{if(e.pointerType==='touch'&&touchY!==null){const d=Math.trunc((touchY-e.clientY)/14);if(d){move(d);touchY-=d*14}}});
 for(const ev of ['pointerup','pointercancel'])viewport.addEventListener(ev,()=>{touchY=null});
 function open(){
  if((dialog&&!dialog.open)||requested)return;
  requested=true;
  @LOAD_STUDY@
 }
 if(staticStudy){
  const params=new URLSearchParams(location.search);
  const lang=params.get('lang');
  const requestedSlice=params.get('slice')??new URLSearchParams(location.hash.slice(1)).get('corte');
  if(/^\d+$/.test(requestedSlice??'')){
   const z=Number(requestedSlice);
   if(Number.isSafeInteger(z)&&z>=staticStudy.firstSlice&&z<=staticStudy.lastSlice)plane=z;
  }
  if(lang && Object.hasOwn(words,lang))document.documentElement.lang=lang;
  document.documentElement.dir=document.documentElement.lang==='ar'?'rtl':'ltr';
  selected=valid(params.get('effort'));
 }
 if(window.DADOS?.valores)preferred=valid(window.DADOS.valores.ESFORCO_PADRAO??window.DADOS.padroes?.ESFORCO_PADRAO);
 new MutationObserver(()=>{if(lang!==document.documentElement.lang)render()}).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
 open();render();
})();
</script>"""
