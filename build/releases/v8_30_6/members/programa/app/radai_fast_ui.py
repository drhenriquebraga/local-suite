"""Station FAST study comparison. All displayed geometry and colours come from the delivered RTSTRUCT."""
import json
from html import escape

from radai_fast_config import STUDY_FAST, dados_para_o_visor
from radai_fast_i18n import LANGS, ROWS


def _text(key):
    return '<span data-fast-text="%s" data-radai-t="1">%s</span>' % (key, escape(ROWS[key][0]))


def page(html, *, estudo=None, caso=False):
    from radai_ui import icone

    card = ('<a class="cfg-card" href="#ps_fast" data-alvo="ps_fast"><span class="cab">'
            '<span class="ic" aria-hidden="true">%s</span><span class="n"></span></span>'
            '<h3>%s</h3><p>%s</p></a>' % (icone("contornos"), _text("title"), _text("compare")))
    choices = []
    for ident, (mm, finish) in STUDY_FAST.items():
        choices.append('<button type="button" class="fast-choice" data-study-card="%s" aria-pressed="false" disabled>'
                       '<b>%s</b><small data-fast-mm="%s"></small>'
                       '<span class="fast-clock"></span><small class="fast-clock-type"></small>'
                       '<small class="fast-roi-count" hidden></small></button>' % (ident, _text(ident), mm))
    viewer = (
        '<div class="fast-settings" id="effort-view">'
        '<div class="fast-workspace"><div class="fast-study"><h3>%s</h3><p class="fast-note">%s</p>'
        '<p class="fast-attribution"><span id="fast-case-source" data-radai-t="1"></span> <span id="fast-credits"></span>'
        '<a id="effort-model-references" href="%s" target="_blank" rel="noopener noreferrer">%s</a></p>'
        '<div class="fast-viewport" tabindex="0"><figure class="fast-plane"><figcaption id="fast-title-choice"></figcaption>'
        '<div class="fast-frame"><canvas id="fast-canvas" hidden></canvas><div class="fast-empty" hidden>%s</div>'
        '<div class="fast-compass" aria-hidden="true" hidden><i>A</i><i>P</i><i>R</i><i>L</i></div></div>'
        '<small class="fast-in-plane" hidden></small><div class="fast-legend" id="fast-view-legend" data-radai-t="1"></div></figure>'
        '<figure id="fast-reference" class="fast-plane" hidden><figcaption id="fast-title-reference"></figcaption>'
        '<div class="fast-frame"><canvas id="fast-reference-canvas" hidden></canvas><div class="fast-empty" hidden>%s</div>'
        '<div class="fast-compass" aria-hidden="true" hidden><i>A</i><i>P</i><i>R</i><i>L</i></div></div>'
        '<small class="fast-in-plane" hidden></small><div class="fast-legend" id="fast-reference-legend" data-radai-t="1"></div></figure></div>'
        '<label for="fast-slice" id="fast-readout" data-radai-t="1"></label><input type="range" id="fast-slice" min="1" max="1" step="1" disabled>'
        '<details id="fast-all"><summary>%s <b class="fast-count"></b></summary><div class="fast-legend"></div></details>'
        '<p class="fast-note" id="fast-models" data-radai-t="1" hidden></p>'
        '</div>'
        '<div class="fast-pick"><h3>%s</h3><p class="fast-note" id="fast-time-basis">%s</p><div class="fast-cards">%s</div>'
        '<p id="fast-description" data-radai-t="1"></p><p id="fast-cache" class="fast-note" hidden data-radai-t="1"></p></div></div>'
        '<p class="fast-note fast-grid-note">%s</p><details id="fast-help"><summary>%s</summary><p>%s</p><p>%s</p></details></div>'
        % (_text("studyTitle"), _text("studyCase"), "bibliografia.html#modelos" if estudo is not None else "/bibliografia#modelos",_text("weightsRefs"),_text("tcNoImage"), _text("tcNoImage"), _text("allRois"), _text("effort"),
           _text("relativeBasis"), "".join(choices), _text("allEngines"), _text("compare"), _text("tcNative"), _text("tcScroll")))
    config = ('<section id="ps_fast" class="ps-cx fechado" hidden><h2 class="ps-cab" tabindex="0" role="button">'
              '<span class="ps-num"></span>%s<span class="ps-seta">▾</span></h2><div class="ps-corpo"><p id="effort-preferred"></p>'
              '<button type="button" id="effort-config-open">%s</button></div></section>' % (_text("title"),_text("compare")))
    modal = ('<dialog id="effort-modal" aria-labelledby="effort-modal-title"><header><div><h2 id="effort-modal-title">%s</h2>'
             '<p>%s</p></div><button type="button" id="effort-close" autofocus>×</button></header><div class="effort-scroll">%s</div>'
             '<footer><output id="effort-status" role="status"></output><button type="button" id="effort-apply" hidden>%s</button>'
             '<button type="button" id="effort-save">%s</button></footer></dialog>' % (
                 _text("compare"),_text("fixedPublic"),viewer,_text("applyCase"),_text("savePref")))
    if estudo is not None:
        section='<section id="esforco-publico"><h2>%s</h2><p>%s</p>%s</section>'%(_text("title"),_text("fixedPublic"),viewer)
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
        sprite, load = "f.pages[page]", "study=staticStudy;loaded=true;render();"
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
    <title>Local Suite · SBRT</title>
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
#effort-modal header{border-bottom:1px solid var(--line,#364452)}#effort-modal h2{font:650 1.1rem/1.3 inherit;margin:0}#effort-modal header p{margin:.25rem 0 0;color:var(--text-muted,#becbd5);font-size:.82rem}
#effort-modal footer{justify-content:flex-end;border-top:1px solid var(--line,#364452)}#effort-status{margin-inline-end:auto;font-size:.8rem}#effort-modal .effort-scroll{min-height:0;overflow:auto;overscroll-behavior:contain;padding:14px 18px}
#effort-close,#effort-apply,#effort-save,#effort-config-open,.effort-help{color:var(--text,#e6eef7);background:var(--panel-2,#26384a);border:1px solid var(--line-strong,#506172);border-radius:7px;padding:7px 11px;cursor:pointer}#effort-close{font-size:1.25rem;line-height:1}#effort-apply{background:#245682;color:white}
.effort-miniform{display:flex;align-items:center;gap:6px;margin:.5rem 0 .8rem}.effort-miniform .effort-trigger{min-width:7rem;border-radius:8px;font:inherit;background:var(--panel-2,#25364b);color:var(--text,#edf3fe);border:1px solid var(--line-strong,#536179);padding:.4rem .65rem;cursor:pointer}.effort-trigger::after{content:'⌄';margin-inline-start:.6rem}.effort-help{width:23px;height:23px;border-radius:50%;padding:0}
#effort-list{position:fixed;inset:auto;z-index:10000;margin:0;padding:5px;min-width:180px;max-width:calc(100vw - 12px);max-height:calc(100dvh - 12px);overflow-y:auto;border-radius:9px;border:1px solid var(--line-strong,#536179);background:var(--panel,#182331);box-shadow:0 5px 18px #0005;color:var(--text,#edf3fe)}
#effort-list[hidden]{display:none!important}#effort-list [role=option]{display:flex;width:100%;justify-content:space-between;align-items:center;padding:7px 10px;border:0;border-radius:5px;min-height:32px;color:inherit;background:transparent;text-align:start;cursor:pointer;font:inherit}
#effort-list [role=option]:focus-visible,#effort-list [role=option]:hover{background:var(--panel-2,#29425b);outline:1px solid var(--accent,#77b5eb)}#effort-list [aria-selected=true]::after{content:'✓';color:var(--accent,#9cd2ff)}
.effort-miniform[data-value=ultra] .effort-trigger,#effort-list [data-effort=ultra][aria-selected=true],.fast-choice[data-study-card=ultra][aria-pressed=true]{background:linear-gradient(110deg,#19487a,#432b70,#19487a);background-size:220% 100%;animation:effort-ultra 6s ease-in-out infinite;color:#fff}
@keyframes effort-ultra{50%{background-position:100% 50%}}@media(prefers-reduced-motion:reduce){.effort-miniform[data-value=ultra] .effort-trigger,#effort-list [data-effort=ultra][aria-selected=true],.fast-choice[data-study-card=ultra][aria-pressed=true]{animation:none}}
.fast-settings [hidden]{display:none!important}.fast-settings{--hi:var(--accent,#69b7fa);color:var(--text,inherit)}
.fast-settings h3{font-size:1rem;margin:0 0 .45rem}.fast-workspace{display:grid;gap:1rem}
.fast-viewport{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,260px),1fr));gap:12px;align-items:start;touch-action:pan-x}
.fast-plane{margin:0;min-width:0}.fast-plane figcaption{margin:0 0 4px;font-size:.82rem;font-weight:650}
.fast-frame{display:grid;place-items:center;position:relative;min-height:160px;height:clamp(210px,40vh,470px);overflow:hidden;border:1px solid var(--line-strong,#3a4755);border-radius:8px;background:#070b10}
.fast-frame canvas{display:block;width:100%;height:100%;min-height:0;object-fit:contain}.fast-settings :focus-visible{outline:2px solid var(--hi);outline-offset:2px}
.fast-empty{padding:20px;text-align:center;color:var(--text-muted)}.fast-compass i{position:absolute;color:#fff;font:600 .76rem sans-serif;background:#0008;padding:2px 4px}
.fast-compass i:nth-child(1){top:4px;left:50%}.fast-compass i:nth-child(2){bottom:4px;left:50%}.fast-compass i:nth-child(3){left:4px;top:50%}.fast-compass i:nth-child(4){right:4px;top:50%}
#fast-readout{display:block;font-size:.85rem;margin:.4rem 0 0}#fast-slice{width:100%;min-height:28px;accent-color:var(--hi);margin:0}
.fast-legend{display:flex;flex-wrap:wrap;gap:5px 12px;font-size:.76rem;line-height:1.3}.fast-legend>span{display:inline-flex;align-items:center;gap:5px;overflow-wrap:anywhere}
.fast-legend>span::before{content:'';flex:none;width:15px;height:3px;background:var(--ink);border-radius:2px}.fast-settings details{margin:.65rem 0}
.fast-settings summary{cursor:pointer;font-size:.85rem}.fast-settings details .fast-legend{margin:.5rem 0}#fast-credits,.fast-note{font-size:.81rem;color:var(--text-muted);line-height:1.45}
.fast-note{margin:0 0 .7rem}.fast-grid-note{margin-top:1rem}.fast-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,132px),1fr));gap:7px}
.fast-plane .fast-legend{margin-top:3px}.fast-in-plane{display:block;margin-top:5px;color:var(--text-muted);font-size:.73rem}.fast-roi-count{font-size:.73rem}
.fast-attribution{margin:0 0 .75rem;font-size:.78rem;line-height:1.5;color:var(--text-muted,#b7c4ce)}.fast-attribution a{color:var(--accent,#8dc4f3)}#effort-model-references{display:block;width:fit-content}
.fast-settings .fast-choice{display:flex;flex-direction:column;align-items:flex-start;justify-content:flex-start;gap:3px;min-height:82px;width:100%;white-space:normal;text-align:start;padding:9px 10px;font:inherit;line-height:1.25;border:1px solid var(--line-strong,#364757);border-radius:7px;color:var(--text,inherit);background:var(--panel-2,#18212b);cursor:pointer}
.fast-settings .fast-choice[aria-pressed=true]{border-color:var(--hi);box-shadow:inset 3px 0 var(--hi);background:var(--accent-fraco,#162d43)}
.fast-choice b{font-size:.84rem;color:var(--hi)}.fast-clock{font-weight:650;font-variant-numeric:tabular-nums;font-size:.93rem}.fast-clock-type{font-size:.73rem;color:var(--text-muted)}
#fast-description,#fast-help p{font-size:.84rem;line-height:1.5}#fast-all .fast-count{font-weight:500}
@media(max-width:600px){.fast-viewport{gap:8px}.fast-frame{height:clamp(160px,28vh,310px)}}
"""


SCRIPT = r"""<script>
(function(){
 const root=document.getElementById('effort-view');
 if(!root)return;
 const words=@WORDS@, staticStudy=@STATIC@;
 const byId=id=>document.getElementById(id);
 const cards=Array.from(root.querySelectorAll('[data-study-card]'));
 const viewport=root.querySelector('.fast-viewport'), canvas=byId('fast-canvas'), slider=byId('fast-slice');
 const dialog=byId('effort-modal'), sprites=new Map(), ids=cards.map(c=>c.dataset.studyCard);
 let study={}, selected='maximo', preferred='maximo', onSelect=null, requested=false, loaded=false, plane=null, paintId=0, lang='', saving=false;
 const t=()=>words[document.documentElement.lang]||words['pt-BR'];
 const number=(v,d=1)=>v.toLocaleString(document.documentElement.lang||'pt-BR',{useGrouping:false,maximumFractionDigits:d});
 const percent=(tenths,signed=false)=>new Intl.NumberFormat(document.documentElement.lang||'pt-BR',{
  style:'percent',maximumFractionDigits:1,signDisplay:signed?'always':'auto'
 }).format(tenths/1000);
 const mm=id=>({leve:6,medio:3}[id]||1.5), name=id=>t()[id];
 function grid(id){const used=Number(study.profiles?.[id]?.effective_mm||mm(id));return number(mm(id))+(used!==mm(id)?' → '+number(used):'')+' mm'}
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
 function drawPanel(id,figure,k,renderId){
  const f=study.profiles?.[id], surface=figure.querySelector('canvas'), compass=figure.querySelector('.fast-compass');
  const notice=figure.querySelector('.fast-empty'), labels=figure.querySelector('.fast-legend'), inPlane=figure.querySelector('.fast-in-plane');
  inPlane.hidden=!f;
  surface.hidden=true;compass.hidden=true;notice.hidden=!loaded||!!f;
  if(!f){labels.replaceChildren();return}
  inPlane.textContent=t().inPlane+' · '+number(f.labelsBySlice[k].length,0);
  list(labels,f.labelsBySlice[k],f.rois);
  const perPage=study.columns*study.rowsPerPage, page=Math.floor(k/perPage), tile=k%perPage;
  const url=@SPRITE_URL@;
  let img=sprites.get(url);
  if(!img){
   img=new Image();img.src=url;
   if(sprites.size>=4)sprites.delete(sprites.keys().next().value);
   sprites.set(url,img);
  }
  function paint(){
   if(renderId!==paintId)return;
   if(surface.width!==study.tileWidth)surface.width=study.tileWidth;
   if(surface.height!==study.tileHeight)surface.height=study.tileHeight;
   const w=surface.width,h=surface.height;
   surface.getContext('2d').drawImage(img,(tile%study.columns)*w,Math.floor(tile/study.columns)*h,w,h,0,0,w,h);
   surface.hidden=false;compass.hidden=false;
  }
  if(img.complete&&img.naturalWidth)paint();
  else img.decode().then(paint).catch(()=>{if(renderId===paintId){notice.hidden=false;inPlane.hidden=true;labels.replaceChildren()}});
 }
 function draw(){
  const renderId=++paintId, ref='maximo', hasFrames=!!(study.profiles?.[selected]||study.profiles?.[ref]);
  slider.disabled=!hasFrames;
  byId('fast-all').hidden=!study.profiles?.[selected];
  const refPanel=byId('fast-reference');
  refPanel.hidden=selected===ref;
  byId('fast-title-choice').textContent=(selected===ref?t().studyReference:t().studyChoice)+' · '+title(selected);
  byId('fast-title-reference').textContent=t().studyReference+' · '+title(ref);
  let k=0;
  if(study.positionsMm){
   plane=Math.min(study.lastSlice,Math.max(study.firstSlice,plane??Math.floor((study.firstSlice+study.lastSlice)/2)));
   k=plane-study.firstSlice;slider.min=study.firstSlice;slider.max=study.lastSlice;slider.value=plane;
   const where=t().tcSlice+' '+plane+'/'+study.total_slices+' · z '+number(study.positionsMm[k],2)+' mm';
   byId('fast-readout').textContent=where;slider.setAttribute('aria-valuetext',where);viewport.setAttribute('aria-label',where);
  }else{byId('fast-readout').textContent=''}
  drawPanel(selected,canvas.closest('figure'),k,renderId);
  if(!refPanel.hidden)drawPanel(ref,refPanel,k,renderId);
 }
 function timing(card, f){
  const elapsed=card.querySelector('.fast-clock'), detail=card.querySelector('.fast-clock-type');
  const share=f?.tempo_relativo_decimos;
  if(!Number.isSafeInteger(share)){elapsed.textContent='—';detail.textContent=t().relativeMissing;return}
  elapsed.textContent=percent(share);
  const delta=share-1000;
  if(card.dataset.studyCard==='maximo')detail.textContent=t().relativeReference;
  else if(!delta)detail.textContent=t().relativeTie;
  else detail.textContent=percent(delta,true)+' · '+(delta<0?t().relativeSaving:t().relativeAdded);
 }
 function render(){
  lang=document.documentElement.lang;
  document.querySelectorAll('[data-fast-text]').forEach(el=>el.textContent=t()[el.dataset.fastText]);
  for(const card of cards){
   const id=card.dataset.studyCard;card.setAttribute('aria-pressed',String(id===selected));card.disabled=false;
   card.querySelector('[data-fast-mm]').textContent=grid(id)+(id==='maximo'?' · '+t().factory:'');
   const profile=study.profiles?.[id], count=card.querySelector('.fast-roi-count');
   timing(card,profile);
   count.hidden=!profile;
   if(profile)count.textContent=t().roiCount+' · '+number(Object.keys(profile.rois).length,0);
  }
  const profile=study.profiles?.[selected];
  const models=byId('fast-models');models.hidden=!profile?.model_names?.length;
  models.textContent=models.hidden?'':t().studyModels+' · '+profile.model_names.join(', ');
  if(profile){
   const ids=Object.keys(profile.rois);byId('fast-all').querySelector('.fast-count').textContent='('+ids.length+')';
   list(byId('fast-all').querySelector('.fast-legend'),ids,profile.rois);
  }
  const promotion=profile&&Number(profile.effective_mm)!==mm(selected)?' '+t().effectiveGrid+' ('+grid(selected)+').':'';
  byId('fast-description').textContent=(selected==='ultra'?t().ultraHelp:t()['finishNote'+ids.indexOf(selected)])+promotion;
  byId('fast-case-source').textContent=study.kind==='reference_ct'?t().referenceCt:'';
  byId('fast-cache').hidden=!profile?.used_cache;byId('fast-cache').textContent=t().cacheNote;
  if(dialog){
   byId('effort-close').setAttribute('aria-label',t().close);
   const summary=byId('effort-preferred');if(summary)summary.textContent=t().effort+' · '+name(preferred);
   for(const el of document.querySelectorAll('.effort-miniform'))translateMini(el);
  }
  credits();if(!dialog||dialog.open)draw();
 }
 const valid=v=>ids.includes(v)?v:'maximo';
 window.radaiEsforcoPreferido=function(v){preferred=valid(String(v).split('#')[0].trim());render()};
 function translateMini(el){
  el.querySelector('.effort-trigger').textContent=t().effort+' · '+name(el.dataset.value);
  el.querySelector('.effort-help').setAttribute('aria-label',t().compare);
 }
 window.radaiMiniEsforco=function(i,value){
  const el=document.createElement('div');el.className='effort-miniform';el.dataset.value=valid(value);el.dataset.series=i;el.setAttribute('data-radai-t','1');
  el.innerHTML='<button type="button" class="effort-trigger" aria-haspopup="listbox" aria-expanded="false" aria-controls="effort-list"></button><button type="button" class="effort-help" aria-haspopup="dialog">?</button>';
  translateMini(el);return el.outerHTML;
 };
 window.radaiMiniAtualizar=function(el,v){el.dataset.value=valid(v);translateMini(el)};
 /*station-actions*/
 let popup=null, anchor=null;
 function closeList(refocus){
  if(!popup)return;
  if(popup.hidePopover)popup.hidePopover();popup.remove();popup=null;
  if(anchor){anchor.setAttribute('aria-expanded','false');if(refocus)anchor.focus()}anchor=null;
 }
 function setCase(el,value){
  window.radaiMiniAtualizar(el,value);
  window.dispatchEvent(new CustomEvent('radai-esforco-caso',{detail:{indice:Number(el.dataset.series),valor:value}}));
 }
 function positionList(){
  if(!anchor||!popup)return;
  if(!anchor.isConnected){
   const id=anchor.closest('.effort-miniform')?.dataset.series;
   const replacement=[...document.querySelectorAll('.effort-miniform')].find(el=>el.dataset.series===id);
   if(!replacement){closeList(false);return}
   anchor=replacement.querySelector('.effort-trigger');anchor.setAttribute('aria-expanded','true');
  }
  const r=anchor.getBoundingClientRect(),w=popup.offsetWidth,h=popup.offsetHeight;
  const x=popup.dir==='rtl'?r.right-w:r.left,below=window.innerHeight-r.bottom;
  const y=below<h+6&&r.top>below?r.top-h-4:r.bottom+4;
  popup.style.left=Math.max(6,Math.min(window.innerWidth-w-6,x))+'px';
  popup.style.top=Math.max(6,Math.min(window.innerHeight-h-6,y))+'px';
 }
 function openList(el){
  closeList(false);
  anchor=el.querySelector('.effort-trigger');anchor.setAttribute('aria-expanded','true');
  popup=document.createElement('div');popup.id='effort-list';popup.setAttribute('role','listbox');
  popup.setAttribute('aria-label',t().effort);popup.setAttribute('data-radai-t','1');popup.dir=getComputedStyle(el).direction;
  if('showPopover' in popup)popup.setAttribute('popover','manual');
  for(const id of ids){
   const row=document.createElement('button');row.type='button';row.setAttribute('role','option');
   row.dataset.effort=id;row.textContent=name(id);row.tabIndex=-1;row.setAttribute('aria-selected',String(id===el.dataset.value));
   row.onclick=()=>{closeList(true);setCase(el,id)};popup.append(row);
  }
  document.body.append(popup);if(popup.showPopover)popup.showPopover();
  positionList();
  popup.querySelector('[aria-selected=true]').focus({preventScroll:true});
 }
 document.addEventListener('click',e=>{
  const el=e.target.closest('.effort-miniform');
  if(e.target.closest('.effort-help')&&el){closeList(false);window.radaiEsforcoAbrir(el.dataset.value,v=>setCase(el,v))}
  else if(e.target.closest('.effort-trigger')&&el){if(anchor===el.querySelector('.effort-trigger'))closeList(true);else openList(el)}
  else if(popup&&!popup.contains(e.target))closeList(false)
 });
 document.addEventListener('keydown',e=>{
  if(!popup){if(e.target.closest('.effort-trigger')&&['ArrowDown','ArrowUp'].includes(e.key)){e.preventDefault();openList(e.target.closest('.effort-miniform'))}return}
  if(e.key==='Escape'||e.key==='Tab'){if(e.key==='Escape')e.preventDefault();closeList(true);return}
  const index=[...popup.children].indexOf(document.activeElement);
  const next={ArrowDown:(index+1)%ids.length,ArrowUp:(index-1+ids.length)%ids.length,Home:0,End:ids.length-1}[e.key];
  if(next!==undefined){e.preventDefault();popup.children[next].focus()}
 });
 window.addEventListener('resize',positionList);
 document.addEventListener('scroll',e=>{if(popup&&e.target!==popup&&!popup.contains(e.target))positionList()},true);
 if(dialog){
  const apply=byId('effort-apply'),save=byId('effort-save'),status=byId('effort-status');
  window.radaiEsforcoAbrir=function(v,selecionar){
   selected=valid(v||preferred);onSelect=typeof selecionar==='function'?selecionar:null;plane=null;
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
  const lang=new URLSearchParams(location.search).get('lang');
  if(lang && Object.hasOwn(words,lang))document.documentElement.lang=lang;
  document.documentElement.dir=document.documentElement.lang==='ar'?'rtl':'ltr';
  selected='maximo';
 }
 if(window.DADOS?.valores)preferred=valid(window.DADOS.valores.ESFORCO_PADRAO??window.DADOS.padroes?.ESFORCO_PADRAO);
 new MutationObserver(()=>{if(lang!==document.documentElement.lang)render()}).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
 open();render();
})();
</script>"""
