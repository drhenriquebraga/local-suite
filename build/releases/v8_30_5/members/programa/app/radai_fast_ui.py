"""Illustrated station settings for FAST contour finishing."""
import json
from html import escape

from radai_fast_i18n import LANGS, ROWS


def _text(key):
    return '<span data-fast-text="%s" data-radai-t="1">%s</span>' % (key, escape(ROWS[key][0]))


def page(html):
    from radai_ui import icone

    card = ('<a class="cfg-card" href="#ps_fast" data-alvo="ps_fast"><span class="cab">'
            '<span class="ic" aria-hidden="true">%s</span><span class="n"></span></span>'
            '<h3>%s</h3><p>%s</p></a>' % (icone("contornos"), _text("title"), _text("intro")))
    stops = "".join(
        '<div class="fast-stop"><button type="button" data-fast-level="%d" aria-describedby="fast-tip-%d">'
        '<b>%d%%</b>%s</button><div class="fast-tip" id="fast-tip-%d" role="tooltip">'
        '<img loading="lazy" alt=""><p>%s</p></div></div>'
        % (n, n, n * 25, _text("l%d" % n), n, _text("d%d" % n)) for n in range(5))
    examples = "".join(
        '<figure data-fast-example="%d"><img loading="lazy" alt=""><figcaption><b>%d%% · %s</b>'
        '<p>%s</p></figcaption></figure>' % (n, n*25, _text("l%d" % n), _text("d%d" % n))
        for n in range(5))
    section = (
        '<section id="ps_fast" class="ps-cx fechado" hidden><h2 class="ps-cab" tabindex="0" role="button">'
        '<span class="ps-num"></span>%s<span class="ps-seta">▾</span></h2><div class="ps-corpo fast-settings">'
        '<div class="fast-layout"><div class="fast-pick"><div class="fast-top">'
        '<label for="f_FAST_NIVEL">%s</label>'
        '<button type="button" id="fast-help" class="fast-help" aria-haspopup="dialog">?</button></div>'
        '<input id="f_FAST_NIVEL" type="range" min="0" max="4" step="1" value="2" disabled>'
        '<div class="fast-stops">%s</div><p id="fast-description" aria-live="polite" data-radai-t="1"></p>'
        '<p class="fast-note">%s</p><p class="fast-note">%s</p>'
        '<button type="button" class="bt sec" id="fast-reset">%s</button></div>'
        '<div class="fast-sample"><div class="fast-switch" role="group">'
        '<button type="button" data-fast-sample="thorax" aria-pressed="true">%s</button>'
        '<button type="button" data-fast-sample="bowel" aria-pressed="false">%s</button></div>'
        '<figure><button type="button" id="fast-zoom" aria-haspopup="dialog">'
        '<img id="fast-picture" loading="lazy" alt=""><span>%s</span></button>'
        '<figcaption id="fast-caption" data-radai-t="1"></figcaption></figure><div class="fast-legend">'
        '<span data-key="breast">%s</span><span data-key="heart">%s</span><span data-key="lung">%s</span>'
        '<span data-key="bowel" hidden>%s</span></div></div></div>'
        '<dialog id="fast-dialog" aria-labelledby="fast-dialog-title"><header><h3 id="fast-dialog-title" data-radai-t="1"></h3>'
        '<button type="button" class="bt sec" id="fast-close">%s</button></header>'
        '<div id="fast-guide"><p>%s</p><div class="fast-examples">%s</div></div>'
        '<img id="fast-zoom-image" hidden alt=""></dialog></div></section>'
        % (_text("title"), _text("level"), stops, _text("scope"), _text("speed"), _text("reset"),
           _text("thorax"), _text("bowel"), _text("zoom"), _text("breast"), _text("heart"), _text("lung"),
           _text("bowel"), _text("close"), _text("helpText"), examples))
    catalog = {code: {key: words[i] for key, words in ROWS.items()} for i, code in enumerate(LANGS)}
    return (html.replace("@FAST_CARD@", card).replace("@FAST_SECTION@", section)
            .replace("</head>", "<style>" + CSS + "</style></head>", 1)
            .replace("</body>", SCRIPT.replace("@FAST_WORDS@", json.dumps(catalog, ensure_ascii=False)
                                                .replace("<", r"\u003c")) + "</body>", 1))


CSS = """
.fast-settings{--fast-tint:var(--accent,#53b6d7);color:var(--text,inherit)}
.fast-settings [hidden]{display:none!important}
.fast-layout{display:grid;grid-template-columns:minmax(16rem,0.8fr) minmax(18rem,1.25fr);gap:clamp(12px,2.5vw,36px);align-items:start}
.fast-top,.fast-switch,.fast-settings dialog header{display:flex;align-items:center;justify-content:space-between;gap:8px}
.fast-top label{font-weight:650;font-size:1rem}.fast-top .fast-help{border:1px solid var(--line-strong);border-radius:50%;font:inherit;font-weight:650;width:30px;height:30px;padding:0;color:var(--fast-tint)}
#f_FAST_NIVEL{width:100%;margin:16px 0 2px;accent-color:var(--fast-tint);cursor:pointer;min-height:28px}
.fast-stops{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:2px;position:relative}
.fast-stop>button{display:flex;flex-direction:column;align-items:center;justify-content:start;gap:3px;width:100%;min-height:48px;white-space:normal;background:transparent;border:1px solid transparent;border-radius:6px;padding:3px 1px;color:var(--text-muted);font:inherit;line-height:1.2;font-size:.75rem;overflow-wrap:anywhere}
.fast-stop>button>span{font-weight:400}.fast-stop>button[aria-pressed=true],.fast-switch button[aria-pressed=true]{color:var(--fast-tint);border-color:var(--accent-line,#527186);background:var(--accent-fraco,var(--panel-2))}
.fast-settings button{cursor:pointer}.fast-settings :focus-visible{outline:2px solid var(--fast-tint);outline-offset:2px}
.fast-tip{pointer-events:none;position:absolute;z-index:20;top:100%;inset-inline-start:0;max-width:min(22rem,100%);display:flex;align-items:center;gap:10px;padding:9px 11px;border:1px solid var(--line-strong);background:var(--bg,#121923);color:var(--text);box-shadow:0 6px 18px #0004;border-radius:8px;opacity:0;visibility:hidden;transform:translateY(-3px);transition:opacity 120ms ease,transform 120ms ease,visibility 0s linear 120ms}
.fast-stop[data-open] .fast-tip{opacity:1;visibility:visible;transform:translateY(0);transition-delay:0s}
.fast-tip img{width:76px;height:52px;object-fit:contain;border-radius:4px;background:#111}
.fast-tip p{font-size:.79rem;line-height:1.35;margin:0}.fast-note,.fast-sample figcaption{font-size:.86rem;color:var(--text-muted);line-height:1.5}
#fast-description{min-height:2.6em;margin:14px 0 5px;font-size:.93rem}.fast-note{margin:.5em 0}
#fast-reset{margin-block-start:12px}.fast-switch{justify-content:start;flex-wrap:wrap;gap:4px;margin-bottom:8px}
.fast-switch button{border:1px solid var(--line-strong);border-radius:6px;background:var(--panel);color:inherit;padding:5px 10px}
.fast-sample figure{margin:0}.fast-sample figcaption{margin:5px 0}
.fast-legend{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:.8rem}.fast-legend>span{display:inline-flex;align-items:center;gap:5px}
.fast-legend>span::before{content:'';width:16px;height:3px;background:var(--ink);border-radius:2px}
.fast-legend [data-key=breast]{--ink:#fcc299}.fast-legend [data-key=heart]{--ink:#ff826c}.fast-legend [data-key=lung]{--ink:#52cef1}.fast-legend [data-key=bowel]{--ink:#edd161}
#fast-zoom{display:block;background:#0d1217;border:1px solid var(--line-strong);border-radius:9px;width:100%;padding:0;overflow:hidden;position:relative}
#fast-picture{display:block;width:100%;height:auto;aspect-ratio:640/410;object-fit:contain}
#fast-zoom>span{position:absolute;inset-inline-end:8px;inset-block-end:8px;background:#182329eb;color:#fff;border:1px solid #ffffff44;border-radius:4px;padding:3px 7px;font-size:.72rem}
.fast-settings dialog{width:min(90vw,760px);max-height:88vh;box-sizing:border-box;padding:17px;background:var(--bg,#121923);color:var(--text,inherit);border:1px solid var(--line-strong);border-radius:12px;overflow:auto}
.fast-settings dialog::backdrop{background:#0009}.fast-settings dialog header h3{margin:0}.fast-examples{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:16px}
.fast-examples figure{margin:0}.fast-examples img,#fast-zoom-image{width:100%;height:auto;display:block;background:#111;border-radius:6px}.fast-examples figcaption{margin-top:5px}.fast-examples p{font-size:.8rem;margin:4px 0}.fast-settings dialog header{margin-bottom:10px}
@media(max-width:800px){.fast-layout{grid-template-columns:minmax(0,1fr)}}
@media(prefers-reduced-motion:reduce){.fast-tip{transition:none;transform:none}}
"""


SCRIPT = r"""<script>
(function(){
 const root=document.getElementById('ps_fast');
 if(!root)return;
 const words=@FAST_WORDS@;
 const byId=id=>document.getElementById(id);
 const input=byId('f_FAST_NIVEL'), dialog=byId('fast-dialog'), picture=byId('fast-picture');
 const stops=Array.from(root.querySelectorAll('[data-fast-level]'));
 const tabs=Array.from(root.querySelectorAll('[data-fast-sample]'));
 let sample='thorax', dialogMode='help', opener=null, renderedLanguage='';
 const language=()=>words[document.documentElement.lang] || words['pt-BR'];
 const image=(n)=>'/api/fast/preview/'+sample+'/'+n;
 function describe(n){return (n*25)+'% · '+language()['l'+n]}
 function updateDialog(){
  const t=language(), n=Number(input.value), guide=dialogMode==='help';
  byId('fast-dialog-title').textContent=guide?t.help:describe(n);
  byId('fast-guide').hidden=!guide;
  const large=byId('fast-zoom-image');
  large.hidden=guide;
  if(guide){
   root.querySelectorAll('[data-fast-example]').forEach(f=>{
    const i=Number(f.dataset.fastExample), img=f.querySelector('img');
    img.src=image(i);img.alt=t[sample+'Alt']+' '+describe(i);
   });
  }else{large.src=image(n);large.alt=t[sample+'Alt']+' '+describe(n)}
 }
 function render(){
  const n=Number(input.value), t=language();
  renderedLanguage=document.documentElement.lang;
  document.querySelectorAll('[data-fast-text]').forEach(el=>{el.textContent=t[el.dataset.fastText]});
  stops.forEach((btn,i)=>{
   btn.setAttribute('aria-pressed',String(i===n));
   btn.disabled=input.disabled;
   const tip=btn.parentElement.querySelector('.fast-tip img');
   if(btn.parentElement.hasAttribute('data-open')) tip.src=image(i);
  });
  tabs.forEach(btn=>btn.setAttribute('aria-pressed',String(btn.dataset.fastSample===sample)));
  root.querySelectorAll('.fast-legend [data-key]').forEach(el=>{el.hidden=(el.dataset.key==='bowel')!==(sample==='bowel')});
  input.setAttribute('aria-valuetext',describe(n)); byId('fast-description').textContent=t['d'+n];
  byId('fast-help').setAttribute('aria-label',t.help);
  byId('fast-zoom').setAttribute('aria-label',t.zoom+' · '+t[sample]);
  byId('fast-reset').disabled=input.disabled || n===2;
  if(!root.hidden) picture.src=image(n);
  picture.alt=t[sample+'Alt']+' '+describe(n);
  byId('fast-caption').textContent=t[sample+'Alt']+' '+describe(n);
  if(dialog.open)updateDialog();
 }
 window.radaiFastSet=function(valor){
  const n=String(valor).split('#')[0].trim();
  input.value=/^[0-4]$/.test(n)?n:'2';input.disabled=false;render();
 };
 const data=window.DADOS;
 if(data && data.editavel && (data.chaves||[]).includes('FAST_NIVEL'))
  window.radaiFastSet((data.valores||{}).FAST_NIVEL??(data.padroes||{}).FAST_NIVEL);
 function hide(){stops.forEach(b=>b.parentElement.removeAttribute('data-open'))}
 function show(btn){hide();btn.parentElement.setAttribute('data-open','');btn.parentElement.querySelector('img').src=image(btn.dataset.fastLevel)}
 function select(i){if(input.disabled)return;input.value=String(i);input.dispatchEvent(new Event('input',{bubbles:true}));input.dispatchEvent(new Event('change',{bubbles:true}))}
 input.addEventListener('input',render);
 stops.forEach(btn=>{
  btn.addEventListener('pointerenter',e=>{if(e.pointerType!=='touch')show(btn)});
  btn.addEventListener('pointerleave',()=>{if(document.activeElement!==btn)hide()});
  btn.addEventListener('focus',()=>show(btn));btn.addEventListener('blur',hide);
  btn.addEventListener('click',()=>{select(btn.dataset.fastLevel);show(btn)});
 });
 document.addEventListener('pointerdown',e=>{if(!e.target.closest('.fast-stop'))hide()});
 root.addEventListener('keydown',e=>{if(e.key==='Escape')hide()});
 tabs.forEach(btn=>btn.addEventListener('click',()=>{sample=btn.dataset.fastSample;hide();render()}));
 byId('fast-reset').addEventListener('click',()=>{hide();select(2)});
 function open(mode,button){hide();dialogMode=mode;opener=button;updateDialog();dialog.showModal()}
 byId('fast-help').addEventListener('click',e=>open('help',e.currentTarget));
 byId('fast-zoom').addEventListener('click',e=>open('zoom',e.currentTarget));
 byId('fast-close').addEventListener('click',()=>dialog.close());
 dialog.addEventListener('close',()=>{if(opener && !root.hidden)opener.focus()});
 new MutationObserver(()=>{if(renderedLanguage!==document.documentElement.lang)render()})
  .observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
 new MutationObserver(()=>{if(root.hidden){hide();if(dialog.open)dialog.close()}else render()}).observe(root,{attributes:true,attributeFilter:['hidden']});
 render();
})();
</script>"""
