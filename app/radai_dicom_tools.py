"""Shared, capability-driven DICOM toolbar. No image geometry is owned here."""
import json

LABELS = {
    'pt-BR': ['Navegar', 'Lápis', 'Pincel', 'Borracha', 'Arrastar', 'Medir distância',
              'Janela / nível', 'Aproximar', 'Afastar', 'Ajustar à tela', 'Interpolar contornos',
              'Desfazer', 'Refazer', 'Editor de contornos', 'Diâmetro do pincel', 'Ferramentas DICOM'],
    'en': ['Navigate', 'Pencil', 'Brush', 'Eraser', 'Pan', 'Measure distance',
           'Window / level', 'Zoom in', 'Zoom out', 'Fit to view', 'Interpolate contours',
           'Undo', 'Redo', 'Contour editor', 'Brush diameter', 'DICOM tools'],
    'es': ['Navegar', 'Lápiz', 'Pincel', 'Borrador', 'Desplazar', 'Medir distancia',
           'Ventana / nivel', 'Acercar', 'Alejar', 'Ajustar a la vista', 'Interpolar contornos',
           'Deshacer', 'Rehacer', 'Editor de contornos', 'Diámetro del pincel', 'Herramientas DICOM'],
    'de': ['Navigieren', 'Stift', 'Pinsel', 'Radierer', 'Verschieben', 'Abstand messen',
           'Fenster / Niveau', 'Vergrößern', 'Verkleinern', 'Ansicht einpassen', 'Konturen interpolieren',
           'Rückgängig', 'Wiederholen', 'Kontureditor', 'Pinseldurchmesser', 'DICOM-Werkzeuge'],
    'fr': ['Naviguer', 'Crayon', 'Pinceau', 'Gomme', 'Déplacer', 'Mesurer une distance',
           'Fenêtre / niveau', 'Agrandir', 'Réduire', 'Ajuster à la vue', 'Interpoler les contours',
           'Annuler', 'Rétablir', 'Éditeur de contours', 'Diamètre du pinceau', 'Outils DICOM'],
    'it': ['Naviga', 'Matita', 'Pennello', 'Gomma', 'Sposta', 'Misura distanza',
           'Finestra / livello', 'Ingrandisci', 'Riduci', 'Adatta alla vista', 'Interpola contorni',
           'Annulla', 'Ripristina', 'Editor dei contorni', 'Diametro del pennello', 'Strumenti DICOM'],
    'pl': ['Nawigacja', 'Ołówek', 'Pędzel', 'Gumka', 'Przesuń', 'Zmierz odległość',
           'Okno / poziom', 'Powiększ', 'Pomniejsz', 'Dopasuj widok', 'Interpoluj kontury',
           'Cofnij', 'Ponów', 'Edytor konturów', 'Średnica pędzla', 'Narzędzia DICOM'],
    'ja': ['移動', '鉛筆', 'ブラシ', '消しゴム', 'パン', '距離を測定',
           'ウィンドウ / レベル', '拡大', '縮小', '画面に合わせる', '輪郭を補間',
           '元に戻す', 'やり直す', '輪郭エディター', 'ブラシ直径', 'DICOMツール'],
    'zh-CN': ['浏览', '铅笔', '画笔', '橡皮擦', '平移', '测量距离',
              '窗宽 / 窗位', '放大', '缩小', '适应视图', '轮廓插值',
              '撤销', '重做', '轮廓编辑器', '画笔直径', 'DICOM工具'],
    'ko': ['탐색', '연필', '브러시', '지우개', '이동', '거리 측정',
           '창 / 레벨', '확대', '축소', '화면에 맞춤', '윤곽 보간',
           '실행 취소', '다시 실행', '윤곽 편집기', '브러시 지름', 'DICOM 도구'],
    'ar': ['تنقّل', 'قلم', 'فرشاة', 'ممحاة', 'تحريك', 'قياس المسافة',
           'النافذة / المستوى', 'تكبير', 'تصغير', 'ملاءمة العرض', 'استيفاء الحدود',
           'تراجع', 'إعادة', 'محرر الحدود', 'قطر الفرشاة', 'أدوات DICOM'],
    'bn': ['নেভিগেট', 'পেন্সিল', 'ব্রাশ', 'ইরেজার', 'সরান', 'দূরত্ব মাপুন',
           'উইন্ডো / লেভেল', 'বড় করুন', 'ছোট করুন', 'পর্দায় মানানসই', 'কনট্যুর ইন্টারপোলেশন',
           'পূর্বাবস্থায় ফেরান', 'আবার করুন', 'কনট্যুর সম্পাদক', 'ব্রাশের ব্যাস', 'DICOM সরঞ্জাম'],
}

CSS = r'''
.rdt-toolbar{display:flex;align-items:center;gap:4px;flex-wrap:wrap;padding:6px 8px;
 border:1px solid var(--line,#233147);border-radius:9px;background:var(--panel,#0d1525);color:var(--text,#dbe6f4)}
.rdt-toolbar button{display:inline-grid;place-items:center;width:34px;height:34px;padding:6px;
 border:1px solid transparent;border-radius:6px;background:transparent;color:inherit;cursor:pointer;position:relative}
.rdt-toolbar button svg{width:20px;height:20px;pointer-events:none}
.rdt-toolbar button:hover,.rdt-toolbar button:focus-visible{border-color:var(--accent,#4da3ff);background:var(--panel-2,#17243a)}
.rdt-toolbar button[aria-pressed=true]{color:var(--accent,#4da3ff);border-color:currentColor;background:var(--accent-fraco,#172b43)}
.rdt-toolbar button:disabled{opacity:.35;cursor:not-allowed}
.rdt-toolbar button:focus-visible{outline:2px solid var(--accent,#4da3ff);outline-offset:2px}
.rdt-tip{position:absolute;inset-block-start:calc(100% + 7px);inset-inline-start:0;display:none;
 padding:6px 9px;background:#162338;border:1px solid #384e6a;border-radius:6px;white-space:nowrap;
 font:12px/1.4 var(--sans,system-ui);color:#e9f1fc;z-index:11050;pointer-events:none;box-shadow:0 5px 18px #0005}
.rdt-toolbar button:hover .rdt-tip,.rdt-toolbar button:focus-visible .rdt-tip{display:block}
.rdt-size{display:flex;align-items:center;gap:5px;margin-inline-start:7px;font-size:11px;font-variant-numeric:tabular-nums}
.rdt-size input{width:54px!important;min-width:0!important;color:inherit!important;background:var(--bg-0,#070f1e)!important;
 border:1px solid var(--line,#233147)!important;border-radius:5px;padding:5px;font:inherit}
.rdt-toolbar[aria-busy=true]{opacity:.7}
'''

_JS = r'''
(function(){'use strict';
 if(window.RadaiDicomToolbar)return;
 var labels=__LABELS__, keys=['pointer','pencil','brush','eraser','pan','measure','window','zoomIn','zoomOut','fit','interpolate','undo','redo','editor'];
 var paths={pointer:'M4 3l15 9-7 2-3 7z',pencil:'M4 16L16 4l4 4L8 20H4zM14 6l4 4',
 brush:'M14 4l6 6-8 8-6-6zM6 12c-5 0-1 8-5 9 6 1 11-1 11-3',eraser:'M3 14L14 3l7 7-11 11H6zM8 9l7 7M10 21h11',
 pan:'M12 3v18M3 12h18M9 6l3-3 3 3M9 18l3 3 3-3M6 9l-3 3 3 3M18 9l3 3-3 3',
 measure:'M3 16L16 3l5 5L8 21zM8 11l2 2M11 8l3 3M14 5l2 2',window:'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 3v18M15 5v14M18 8v8',
 zoomIn:'M10 3a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM15 15l6 6M10 7v6M7 10h6',
 zoomOut:'M10 3a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM15 15l6 6M7 10h6',
 fit:'M3 9V3h6M15 3h6v6M21 15v6h-6M9 21H3v-6M7 7h10v10H7z',
 interpolate:'M3 4h18M3 20h18M5 8h14M7 12h10M5 16h14',undo:'M8 4L3 9l5 5M3 9h10a7 7 0 0 1 0 14',
 redo:'M16 4l5 5-5 5M21 9H11a7 7 0 0 0 0 14',editor:'M3 4h18v16H3zM8 4v16M12 8h5M12 12h5M12 16h3'};
 var active=null;
 function language(){var l=document.documentElement.lang||'pt-BR';return labels[l]?l:'en';}
 function txt(key){var n=keys.indexOf(key);return labels[language()][n<0?({diameter:14,tools:15}[key]||0):n];}
 function svg(key){return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="'+(paths[key]||paths.pointer)+'"/></svg>';}
 function input(el){return !!(el&&el.closest&&el.closest('input,select,textarea,[contenteditable=true]'));}
 function mount(target,cfg){
  cfg=cfg||{};if(typeof target==='string')target=document.querySelector(target);if(!target)return null;
  var bar=document.createElement('div');bar.className='rdt-toolbar';bar.setAttribute('role','toolbar');bar.setAttribute('translate','no');
  var T={tool:cfg.tool||'pointer',diameter:Number(cfg.diameter)||5,element:bar,destroyed:false};
  var buttons={}, scope=cfg.scope||target, handlers=[];
  function listen(el,type,fn,opt){el.addEventListener(type,fn,opt);handlers.push([el,type,fn,opt]);}
  function can(k){return !T.destroyed&&(!cfg.enabled||cfg.enabled(k)!==false);}
  function editing(){return T.tool==='brush'||T.tool==='eraser';}
  (cfg.tools||keys).forEach(function(k){
   if(keys.indexOf(k)<0)return;var b=document.createElement('button');b.type='button';b.dataset.dicomTool=k;
   b.innerHTML=svg(k)+'<span class="rdt-tip" role="tooltip"></span>';bar.appendChild(b);buttons[k]=b;
   if(keys.indexOf(k)<7)b.setAttribute('aria-pressed',String(T.tool===k));
   listen(b,'click',function(e){e.preventDefault();e.stopPropagation();active=T;if(!can(k))return;
    if(keys.indexOf(k)<7){T.setTool(k);if(cfg.onTool)cfg.onTool(k,T);}else if(cfg.onAction)cfg.onAction(k,T);T.refresh();});
   listen(b,'dblclick',function(e){e.stopPropagation();});
  });
  var size=document.createElement('label');size.className='rdt-size';size.innerHTML='<input type="number" min="0.5" max="100" step="0.5"><span>mm</span>';
  var diameter=size.querySelector('input');bar.appendChild(size);target.appendChild(bar);
  T.setTool=function(k){if(buttons[k]&&keys.indexOf(k)<7){T.tool=k;T.refresh();}return T;};
  T.setDiameter=function(v){v=Number(v);if(!Number.isFinite(v))return T;T.diameter=Math.max(.5,Math.min(100,Math.round(v*2)/2));diameter.value=String(T.diameter);
   if(cfg.onDiameter)cfg.onDiameter(T.diameter,T);return T;};
  T.refresh=function(){if(T.destroyed)return;bar.setAttribute('aria-label',txt('tools'));
   Object.keys(buttons).forEach(function(k){var b=buttons[k],s=txt(k);b.title=s;b.setAttribute('aria-label',s);var tip=b.querySelector('.rdt-tip');if(tip.textContent!==s)tip.textContent=s;b.disabled=!can(k);
    if(keys.indexOf(k)<7)b.setAttribute('aria-pressed',String(k===T.tool));});
   size.hidden=!(buttons.brush||buttons.eraser);diameter.title=txt('diameter')+' · Ctrl + scroll · , / .';diameter.setAttribute('aria-label',txt('diameter'));diameter.value=String(T.diameter);
   diameter.disabled=!can('brush')&&!can('eraser');};
  T.handleWheel=function(e){if(!e.ctrlKey||!editing()||!can(T.tool)||!e.deltaY||input(e.target))return false;
   e.preventDefault();e.stopImmediatePropagation();active=T;T.setDiameter(T.diameter+(e.deltaY<0?.5:-.5));return true;};
  function activate(){active=T;}
  listen(scope,'pointerenter',activate);listen(scope,'focusin',activate);listen(bar,'pointerenter',activate);listen(bar,'focusin',activate);
  listen(scope,'wheel',T.handleWheel,{capture:true,passive:false});
  listen(diameter,'change',function(){T.setDiameter(this.value);});
  listen(document,'keydown',function(e){if(active!==T||input(e.target)||e.altKey||e.metaKey||e.ctrlKey||!editing()||!can(T.tool))return;
   var d=(e.code==='Comma'||e.key===','||e.key==='<')?-.5:(e.code==='Period'||e.key==='.'||e.key==='>')?.5:0;
   if(d){e.preventDefault();e.stopPropagation();T.setDiameter(T.diameter+d);}});
  var observer=new MutationObserver(function(){T.refresh();});observer.observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
  T.destroy=function(){T.destroyed=true;handlers.forEach(function(h){h[0].removeEventListener(h[1],h[2],h[3]);});observer.disconnect();if(active===T)active=null;bar.remove();};
  T.refresh();return T;
 }
 window.RadaiDicomToolbar={mount:mount,icon:svg,label:txt};
})();
'''
JS = _JS.replace('__LABELS__', json.dumps(LABELS, ensure_ascii=False))


def aplicar(page):
    if not page or 'id="radai-dicom-tools"' in page:
        return page
    import radai_contour_editor_ui
    import radai_dicom_adapters
    assets = '<style id="radai-dicom-tools">' + CSS + radai_contour_editor_ui.CSS + '</style>'
    assets += '<script>' + JS + radai_contour_editor_ui.JS + radai_dicom_adapters.JS + '</script>'
    return page.replace('</body>', assets + '</body>')
