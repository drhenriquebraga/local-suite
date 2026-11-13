"""One editing workspace shared by viewers; all geometry lives in the host API."""
import json

from radai_contour_edit_i18n import TEXT, ERRORS
from radai_contour_scene_ui import JS as SCENE_JS

CSS = r'''
.rce-dialog{position:fixed;inset:14px;width:calc(100vw - 28px);height:calc(100vh - 28px);max-width:none;max-height:none;margin:auto;
 padding:0;border:1px solid var(--line,#26344b);border-radius:12px;color:var(--text,#dce8fa);background:var(--bg-0,#080f1d);
 font:13px/1.45 var(--sans,system-ui);box-shadow:0 20px 80px #0009;overflow:hidden}
.rce-dialog::backdrop{background:#030817cc}.rce-shell{display:flex;flex-direction:column;height:100%;min-height:0}
.rce-head{display:flex;align-items:center;gap:12px;padding:12px 16px;border-bottom:1px solid #26344b;background:var(--panel,#101a2c)}
.rce-head h2{margin:0;font-size:19px;font-family:inherit;display:flex;align-items:center;gap:9px}.rce-head h2 svg{color:var(--accent,#4da3ff);width:23px;height:23px}
.rce-head .rce-spacer{flex:1}.rce-dialog button.rce-button{border:1px solid #324863;border-radius:6px;background:#101d30;color:inherit;
 padding:7px 11px;font:inherit;cursor:pointer}.rce-dialog button.rce-button:hover{border-color:var(--accent,#4da3ff)}
.rce-dialog button:disabled{opacity:.4;cursor:not-allowed}.rce-primary{background:#12382f!important;color:#86e5ca!important;border-color:#286a58!important}
.rce-body{display:grid;grid-template-columns:245px minmax(0,1fr);min-height:0;flex:1}.rce-side{padding:12px;border-inline-end:1px solid #26344b;overflow:auto;background:#0d1626;min-width:0}
.rce-dialog label{display:block;font-size:12px;color:#a4b6ce;margin-bottom:6px}.rce-dialog input:not([type=range]),.rce-dialog select{box-sizing:border-box;width:100%;margin-top:5px;background:#081120!important;
 color:#e3edf9!important;border:1px solid #2b3c56!important;border-radius:6px;padding:8px;font:inherit}.rce-dialog input[type=color]{height:34px;padding:3px!important}
.rce-rois{display:flex;flex-direction:column;gap:4px;margin:10px 0 14px}.rce-rois button{display:flex;align-items:center;gap:8px;text-align:start;
 color:#c7d7ea;background:transparent;border:1px solid transparent;border-radius:6px;padding:8px;font:inherit;cursor:pointer;overflow-wrap:anywhere}
.rce-rois button[aria-selected=true]{background:#16362f;border-color:#2f7d67;color:#a6f3d5}.rce-rois i{flex:none;width:10px;height:10px;border-radius:50%}
.rce-rois small{margin-inline-start:auto}.rce-tabs{display:flex;gap:4px;margin:13px 0 10px}.rce-tabs button{flex:1;font-size:11px!important;padding:6px!important}
.rce-tabs button[aria-selected=true]{border-color:#55bca4!important;color:#89e0c7}
.rce-main{display:flex;flex-direction:column;min-width:0;min-height:0;padding:10px;gap:9px;position:relative}
.rce-planes{display:grid;grid-template-columns:minmax(0,2.1fr) minmax(230px,1fr);grid-template-rows:repeat(3,minmax(0,1fr));flex:1;min-height:0;gap:8px}
.rce-pane[data-plane=axial]{grid-row:1/4;grid-column:1}.rce-pane[data-plane=coronal]{grid-row:1;grid-column:2}.rce-pane[data-plane=sagittal]{grid-row:2;grid-column:2}.rce-pane[data-plane=scene]{grid-row:3;grid-column:2}
.rce-inline{position:relative;inset:auto;width:100%;height:max(680px,calc(100vh - 150px));margin:0;box-sizing:border-box;box-shadow:none}.rce-identity{display:flex;gap:8px 20px;flex-wrap:wrap;padding:7px 16px;background:#10192a;border-bottom:1px solid #26344b;font-size:12px;overflow-wrap:anywhere}.rce-identity b{color:#8ba6c7;font-weight:500;margin-inline-end:5px}.rce-scene-stage{position:relative;flex:1;min-height:0;display:grid;place-items:center}.rce-scene-stage canvas{position:absolute;inset:0;width:100%;height:100%;touch-action:none}.rce-scene-message{position:relative;padding:9px;text-align:center;color:#9cb7d4;pointer-events:none;font-size:11px}.rce-scene-actions{display:flex;gap:5px;align-items:center}.rce-head-actions{display:flex;gap:7px}
.rce-pane{display:flex;flex-direction:column;min-width:0;min-height:0;border:1px solid #24354c;background:#060b14;border-radius:8px;overflow:hidden}
.rce-pane[data-active=true]{border-color:#4da3ff}.rce-pane header{display:flex;align-items:center;justify-content:space-between;padding:8px 10px;font-size:12px;color:#9cb7d4}
.rce-canvas{display:block;width:100%;height:100%;min-height:0;flex:1;touch-action:none;outline:none}.rce-canvas:focus-visible{box-shadow:inset 0 0 0 2px #4da3ff}
.rce-pane input[type=range]{width:calc(100% - 18px);margin:9px;accent-color:#4da3ff}.rce-status{min-height:18px;font-size:12px;color:#9fb4d1}
.rce-status[data-error=true]{color:#ff929c}.rce-footer{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:8px 16px;font-size:11px;color:#8dabc9;border-top:1px solid #22324a}
.rce-dot{color:#e3bf43;margin-inline-end:5px}.rce-interpolation{padding:10px;background:#101e32;border:1px solid #334c6b;border-radius:7px}
.rce-interpolation[hidden],.rce-dialog [hidden]{display:none!important}.rce-interpolation .rce-row{display:flex;gap:9px;align-items:end;flex-wrap:wrap}.rce-interpolation label{width:100px;margin:0}
.rce-interpolation p{margin:0 0 8px;color:#9db3d0;font-size:12px}.rce-load{position:absolute;inset:50px 10px 32px;background:#070d1de8;z-index:2;display:grid;place-items:center}
.rce-dialog a{color:#79bcff}.rce-side hr{border:0;border-top:1px solid #25374f;margin:15px 0}
@media(max-width:1000px){.rce-body{grid-template-columns:190px minmax(0,1fr)}.rce-planes{grid-template-columns:minmax(0,1.7fr) minmax(180px,1fr)}.rce-pane header{padding:5px}.rce-head{flex-wrap:wrap}}
@media(max-width:680px){.rce-body{grid-template-columns:145px minmax(0,1fr)}.rce-planes{grid-template-columns:1fr;grid-template-rows:none;overflow:auto}.rce-pane[data-plane]{min-height:220px;grid-row:auto;grid-column:1}}
'''

_JS = r'''
(function(){'use strict';if(window.RadaiContourEditor)return;
 var texts=__TEXT__, errors=__ERRORS__, instance=null,drafts=new Map();
 function errorText(code){var l=document.documentElement.lang||'pt-BR';var values=errors[code]||errors.EDIT_FAILED;return values[l]||values.en;}
 function t(k){var l=document.documentElement.lang||'pt-BR';return (texts[l]||texts.en)[k]||texts.en[k]||k;}
 function node(tag,cls,text){var e=document.createElement(tag);if(cls)e.className=cls;if(text!=null)e.textContent=text;return e;}
 function button(k,fn,primary){var e=node('button','rce-button'+(primary?' rce-primary':''),t(k));e.type='button';if(fn)e.addEventListener('click',fn);return e;}
 function open(cfg){
  cfg=cfg||{};var draftKey=JSON.stringify([cfg.source||'thumbnail',cfg.b||'',cfg.rs||'']);if(instance){instance.dialog.focus();instance.status(t('saveFirst'),true);return Promise.resolve(instance);}
  var retained=drafts.get(draftKey);if(retained){retained.resume(cfg);return Promise.resolve(retained);}
  var E={cfg:cfg,session:null,roi:null,busy:false,closed:false,dirty:false,preview:null,planes:{},active:'axial',measure:null,urls:[],generation:0,tool:cfg.tool||'pointer',loaded:false,initialReady:false};
  var inline=!!cfg.inlineRoot,d=node(inline?'section':'dialog','rce-dialog'+(inline?' rce-inline':''));d.tabIndex=-1;d.setAttribute('aria-label',t('title'));d.setAttribute('translate','no');E.dialog=d;instance=E;E.suspended=false;E.draftKey=draftKey;
  var shell=node('div','rce-shell'),head=node('header','rce-head'),title=node('h2');title.innerHTML=window.RadaiDicomToolbar.icon('editor');title.appendChild(node('span','',t('title')));
  head.appendChild(title);head.appendChild(node('span','rce-spacer'));var save=button('save',function(){mutate('save',{}).then(function(r){if(!r)return;E.dirty=false;E.savedReceipt=E.lastSavedReceipt=r;status(r.fallback?t('fallbackSaved'):t('saved'));if(r.download_url){download.href=r.download_url;download.hidden=false;download.textContent=t('download');}refreshControls();});},true);
  head.appendChild(save);var discardBtn=button('discardDraft',function(){if(!E.dirty||window.confirm(t('discard')))close(true);});head.appendChild(discardBtn);var closeBtn=button('close',function(){close();});head.appendChild(closeBtn);shell.appendChild(head);
  var identity=node('div','rce-identity');identity.setAttribute('aria-label',t('identification'));shell.appendChild(identity);
  var body=node('div','rce-body'),side=node('aside','rce-side'),main=node('main','rce-main');body.append(side,main);shell.appendChild(body);
  var sourceLabel=node('label','',t('file')),sources=node('select');sourceLabel.appendChild(sources);side.appendChild(sourceLabel);
  var importBtn=button('import',function(){if(E.dirty&&!window.confirm(t('sourceChanged')))return;mutate('import',{rs:sources.value,discard:true}).then(function(r){if(r){E.roi=null;E.dirty=false;consume(r);}});});side.appendChild(importBtn);
  var tabs=node('div','rce-tabs');tabs.setAttribute('role','tablist');var tabOld=button('existing',function(){setTab(false);}),tabNew=button('addTab',function(){setTab(true);});
  [tabOld,tabNew].forEach(function(b){b.setAttribute('role','tab');tabs.appendChild(b);});side.appendChild(tabs);
  var rois=node('div','rce-rois');rois.setAttribute('role','listbox');rois.setAttribute('aria-label',t('rois'));side.appendChild(rois);
  var createBox=node('div'),nameLabel=node('label','',t('name')),name=node('input');name.maxLength=64;name.autocomplete='off';nameLabel.appendChild(name);
  var colorLabel=node('label','',t('color')),color=node('input');color.type='color';color.value='#ff3d4d';colorLabel.appendChild(color);
  var createBtn=button('create',function(){var hex=color.value;mutate('new-roi',{name:name.value.trim(),color:[1,3,5].map(function(i){return parseInt(hex.slice(i,i+2),16);})}).then(function(r){if(r){E.roi=(r.rois||[]).slice(-1)[0]?.id;name.value='';setTab(false);consume(r);E.toolbar.setTool('brush');E.tool='brush';}});},true);
  createBox.append(nameLabel,colorLabel,createBtn);side.appendChild(createBox);var renameBtn=button('rename',function(){var r=currentROI();if(!r)return;var n=window.prompt(t('name'),r.name);if(n&&n.trim()!==r.name)mutate('rename',{roi:E.roi,name:n.trim()}).then(consume);});side.appendChild(renameBtn);
  side.appendChild(node('hr'));var hint=node('p','rce-status',t('select'));side.appendChild(hint);
  var tools=node('div');main.appendChild(tools);
  var inter=node('section','rce-interpolation');inter.hidden=true;var interTitle=node('p');inter.appendChild(interTitle);inter.appendChild(node('p','',t('interpolationHelp')));var row=node('div','rce-row');
  row.appendChild(button('preview',function(){mutate('interpolate',{roi:E.roi,plane:inter.dataset.plane,apply:false},false).then(function(r){if(r){E.preview=r.preview_id;apply.hidden=false;status(t('previewReady'));refreshControls();showPlanes();}});}));
  var apply=button('apply',function(){mutate('interpolate',{roi:E.roi,plane:E.active,apply:true,preview_id:E.preview}).then(function(r){if(r){E.preview=null;inter.hidden=true;consume(r);}});},true);apply.hidden=true;row.appendChild(apply);
  row.appendChild(button('cancel',function(){E.preview=null;inter.hidden=true;showPlanes();}));inter.appendChild(row);main.appendChild(inter);
  var grid=node('div','rce-planes');main.appendChild(grid);
  ['axial','coronal','sagittal'].forEach(function(plane){
   var pane=node('section','rce-pane'),ph=node('header'),label=node('span','',t(plane)),count=node('span'),canvas=node('canvas','rce-canvas'),range=node('input');
   pane.dataset.plane=plane;pane.dataset.active=String(plane===E.active);ph.append(label,count);canvas.tabIndex=0;canvas.setAttribute('aria-label',t(plane));range.type='range';range.min=0;range.step=1;range.value=0;range.setAttribute('aria-label',t(plane));
   pane.append(ph,canvas,range);grid.appendChild(pane);E.planes[plane]={pane:pane,canvas:canvas,range:range,count:count,label:label,index:0,zoom:1,pan:[0,0],img:null,overlay:null,serial:0,loaded:false,drag:null,center:null,width:null};
   range.addEventListener('input',function(){if(E.busy||hasDrag()){range.value=E.planes[plane].index;return;}E.measure=null;E.planes[plane].index=Number(range.value);loadPlane(plane);});
   canvas.addEventListener('pointerdown',function(e){down(plane,e);});canvas.addEventListener('pointermove',function(e){move(plane,e);});
   canvas.addEventListener('pointerup',function(e){up(plane,e);});canvas.addEventListener('pointercancel',function(e){var p=E.planes[plane];if(!p.drag||p.drag.pointer!==e.pointerId)return;clearTimeout(p.windowTimer);p.windowTimer=null;p.drag=null;refreshControls();draw(plane);});
   canvas.addEventListener('pointerleave',function(){E.planes[plane].hover=null;draw(plane);});
   canvas.addEventListener('contextmenu',function(e){e.preventDefault();});
   canvas.addEventListener('wheel',function(e){e.preventDefault();var p=E.planes[plane];if(E.busy||hasDrag()||!E.session)return;activate(plane);if(e.ctrlKey){p.zoom=Math.max(.25,Math.min(12,p.zoom*(e.deltaY<0?1.15:1/1.15)));draw(plane);return;}
    p.index=Math.max(0,Math.min(p.n-1,p.index+(e.deltaY>0?1:-1)*(e.shiftKey?10:1)));range.value=p.index;E.measure=null;loadPlane(plane);},{passive:false});
  });
  var scenePane=node('section','rce-pane');scenePane.dataset.plane='scene';var sceneHead=node('header'),sceneStage=node('div','rce-scene-stage'),sceneCanvas=node('canvas'),sceneMessage=node('span','rce-scene-message',t('sceneHint'));sceneCanvas.setAttribute('aria-label',t('sceneTitle'));
  var sceneButton=button('show3d',function(){E.sceneEnabled=true;requestScene();});sceneHead.append(node('span','',t('sceneTitle')),sceneButton);sceneStage.append(sceneCanvas,sceneMessage);scenePane.append(sceneHead,sceneStage);grid.appendChild(scenePane);E.sceneEnabled=!!cfg.externalScene;E.sceneSerial=0;
  function mountExternal(){var external=cfg.externalScene;if(!external?.element)return;var element=external.element,placeholder=document.createComment('contour-scene-return');element.parentNode?.insertBefore(placeholder,element);E.externalPlacement={element:element,placeholder:placeholder,style:element.getAttribute('style')};element.style.cssText+=';position:absolute;inset:0;width:100%;height:100%;min-height:0;';sceneStage.insertBefore(element,sceneMessage);sceneCanvas.hidden=true;}
  function restoreExternal(){var placed=E.externalPlacement;if(!placed)return;if(placed.placeholder.parentNode)placed.placeholder.replaceWith(placed.element);if(placed.style==null)placed.element.removeAttribute('style');else placed.element.setAttribute('style',placed.style);E.externalPlacement=null;cfg.externalScene?.resize?.();}
  mountExternal();
  var centerButton=button('centerStructure',function(){mutate('center',{roi:E.roi},false).then(function(r){if(!r)return;['axial','coronal','sagittal'].forEach(function(a,i){E.planes[a].index=Math.round(r.indices_zyx[i]);E.planes[a].pan=[0,0];});if(E.sceneViewer)E.sceneViewer.center(r.center_lps);cfg.externalScene?.center?.(r.center_lps);showPlanes();});});side.appendChild(centerButton);
  var st=node('div','rce-status');st.setAttribute('role','status');st.setAttribute('aria-live','polite');main.appendChild(st);
  var load=node('div','rce-load');main.appendChild(load);
  var foot=node('footer','rce-footer'),note=node('span');note.appendChild(node('span','rce-dot','●'));note.appendChild(node('span','',t('review')));var local=node('span','',t('local')),download=node('a');download.hidden=true;download.download='';foot.append(note,local,download);shell.appendChild(foot);d.appendChild(shell);(cfg.inlineRoot||document.body).appendChild(d);
  d.addEventListener('cancel',function(e){e.preventDefault();close();});if(!inline)d.showModal();setTab(false);
  var resize=new ResizeObserver(function(){Object.keys(E.planes).forEach(draw);if(E.sceneViewer)E.sceneViewer.draw();cfg.externalScene?.resize?.();});resize.observe(grid);
  E.toolbar=window.RadaiDicomToolbar.mount(tools,{scope:grid,tool:E.tool,diameter:5,enabled:function(k){return !!E.session&&E.initialReady&&!E.busy&&!hasDrag()&&(!['brush','eraser','pencil','interpolate'].includes(k)||(!!E.roi&&currentROI()?.editable!==false))&& (k!=='undo'||E.session.can_undo)&&(k!=='redo'||E.session.can_redo);},
   tools:['pointer','pencil','brush','eraser','pan','measure','window','zoomIn','zoomOut','fit','interpolate','undo','redo'],
   onTool:function(k){E.tool=k;E.measure=null;Object.keys(E.planes).forEach(draw);if(k==='measure')status(t('measureHint'));},onDiameter:function(){Object.keys(E.planes).forEach(draw);},onAction:function(k){
    var p=E.planes[E.active];if(k==='zoomIn'||k==='zoomOut'){p.zoom=Math.max(.25,Math.min(12,p.zoom*(k==='zoomIn'?1.25:.8)));draw(E.active);}
    else if(k==='fit'){Object.keys(E.planes).forEach(function(a){E.planes[a].zoom=1;E.planes[a].pan=[0,0];draw(a);});}
    else if(k==='undo'||k==='redo')mutate(k,{}).then(consume);
    else if(k==='interpolate'){inter.hidden=!inter.hidden;inter.dataset.plane=E.active;interTitle.textContent=t('interpolate')+' · '+p.label.textContent;apply.hidden=true;}
   }});
  E.status=status;
  function setTab(isNew){tabOld.setAttribute('aria-selected',String(!isNew));tabNew.setAttribute('aria-selected',String(isNew));rois.hidden=isNew;createBox.hidden=!isNew;renameBtn.hidden=isNew;if(isNew)setTimeout(function(){name.focus();},0);}
  function status(s,error){st.textContent=s||'';st.dataset.error=String(!!error);}
  function currentROI(){return (E.session?.rois||[]).find(function(r){return String(r.id)===String(E.roi);});}
  function hasDrag(){return Object.values(E.planes).some(function(p){return !!p.drag;});}
  function activate(plane){E.active=plane;Object.keys(E.planes).forEach(function(k){E.planes[k].pane.dataset.active=String(k===plane);});}
  function refreshControls(){var locked=E.busy||hasDrag();save.disabled=!E.session||!E.initialReady||locked||!E.dirty;createBtn.disabled=!E.session||!E.initialReady||locked;importBtn.disabled=!E.session||!E.initialReady||locked||!sources.value;renameBtn.disabled=!E.roi||!E.initialReady||locked;sources.disabled=locked;closeBtn.disabled=!!E.session&&locked;apply.disabled=locked||!E.preview;
   tabOld.disabled=tabNew.disabled=locked;discardBtn.disabled=locked;centerButton.disabled=locked||!E.roi||!E.initialReady;sceneButton.disabled=locked||!E.initialReady;rois.querySelectorAll('button').forEach(function(b){b.disabled=locked;});
   if(E.toolbar)E.toolbar.refresh();Object.values(E.planes).forEach(function(p){p.range.disabled=locked;});}
  function busy(v,msg){E.busy=v;d.setAttribute('aria-busy',String(v));refreshControls();if(msg)status(msg);}
  async function call(path,data){var o={method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)},r=await fetch('/api/contour-edit/'+path,o),j;
   try{j=await r.json();}catch(_){throw Error(t('failed'));}if(!r.ok||j.error||j.erro)throw Error(j.error?errorText(j.error):(j.detail||j.erro||t('failed')));return j;}
  async function mutate(path,data,changes){if(E.closed||!E.session||E.busy||hasDrag())return null;busy(true,path==='save'?t('saving'):t('busy'));
   try{var r=await call(path,Object.assign({s:E.session.session,csrf:E.session.csrf,revision:E.session.revision},data));if(E.closed)return null;
    if(changes!==false&&path!=='save'){E.dirty=true;E.savedReceipt=null;E.preview=null;}if(path==='interpolate')E.preview=null;if(r.revision!=null)E.session.revision=r.revision;status(path==='save'?t('saved'):E.dirty?t('changed'):t('ready'));return r;
   }catch(err){if(!E.closed)status(err.message,true);return null;}finally{if(!E.closed)busy(false);}}
  function consume(data){if(!data||E.closed)return;var old=E.session;E.session=Object.assign({},E.session||{},data);if(!E.session.csrf&&old)E.session.csrf=old.csrf;
   identity.replaceChildren();var ident=E.session.identity||{};[['patient',ident.patient_name],['patientId',ident.patient_id],['study',ident.study_description||ident.study_date],['series',[(ident.modality||''),(ident.series_number||''),(ident.series_description||'')].filter(Boolean).join(' · ')]].forEach(function(pair){if(!pair[1])return;var item=node('span');item.append(node('b','',t(pair[0])+':'),node('span','',pair[1]));identity.appendChild(item);});
   var options=E.session.rs_files||[];sources.replaceChildren();var empty=node('option','',t('empty'));empty.value='';sources.appendChild(empty);
   options.forEach(function(f){var o=node('option','',f.name||f.label||f.rs||f.id||f);o.value=f.id||f.rs||f.name||f;sources.appendChild(o);if(f.name===E.session.source_rtstruct)o.selected=true;});if(E.session.rs)sources.value=E.session.rs;
   if(!(E.session.rois||[]).some(function(r){return String(r.id)===String(E.roi);}))E.roi=E.session.rois?.find(function(r){return r.editable!==false;})?.id||E.session.rois?.[0]?.id||null;
   rois.replaceChildren();(E.session.rois||[]).forEach(function(r){var b=node('button');b.type='button';b.setAttribute('role','option');b.setAttribute('aria-selected',String(String(r.id)===String(E.roi)));var dot=node('i');dot.style.background='rgb('+r.color.join(',')+')';b.append(dot,node('span','',r.name));if(r.edited)b.appendChild(node('small','','●'));
    b.onclick=function(){if(E.busy||hasDrag())return;E.roi=r.id;E.preview=null;inter.hidden=true;consume(E.session);};rois.appendChild(b);});
   var shape=E.session.shape,spacing=E.session.spacing;if(shape&&spacing){Object.keys(E.planes).forEach(function(a){var p=E.planes[a],axes=a==='axial'?[0,1,2]:a==='coronal'?[1,0,2]:[2,0,1];p.n=shape[axes[0]];p.h=shape[axes[1]];p.w=shape[axes[2]];p.sy=spacing[axes[1]];p.sx=spacing[axes[2]];
    if(!E.loaded)p.index=a==='axial'&&Number.isInteger(cfg.slice)?Math.max(0,Math.min(p.n-1,cfg.slice)):Math.floor(p.n/2);p.range.max=p.n-1;p.range.value=p.index;
    p.label.textContent=a==='axial'?t('planeOriginal'):t('planeMPR')+' '+(a==='coronal'?'1':'2');
    var direction=E.session.direction;
    if(direction&&direction.length===3){var xaxis=a==='sagittal'?1:0,yaxis=a==='axial'?1:2;
     function directionLabel(axis,sign){var v=direction.map(function(r){return r[axis]*sign;}),names=[['R','L'],['A','P'],['I','S']];return [0,1,2].sort(function(i,j){return Math.abs(v[j])-Math.abs(v[i]);}).filter(function(i){return Math.abs(v[i])>.2;}).map(function(i){return names[i][v[i]>0?1:0];}).join('');}
     p.edges={left:directionLabel(xaxis,-1),right:directionLabel(xaxis,1),top:directionLabel(yaxis,-1),bottom:directionLabel(yaxis,1)};}
   });E.loaded=true;}
   hint.textContent=currentROI()?.editable===false?t('unsupportedROI'):t('select');refreshControls();if(E.initialReady)scheduleScene();return showPlanes();
  }
  async function loadPlane(a){var p=E.planes[a];if(!E.session||!p.w)return false;var serial=++p.serial,index=p.index,revision=E.session.revision;p.loaded=false;draw(a);
   p.count.textContent=(index+1)+' / '+p.n;p.range.value=index;var q=new URLSearchParams({s:E.session.session,plane:a,index:index,revision:revision});if(p.center!=null){q.set('center',p.center);q.set('width',p.width);}
   var oq=new URLSearchParams({s:E.session.session,plane:a,index:index,roi:E.roi==null?'':E.roi,revision:revision});if(E.preview)oq.set('preview_id',E.preview);
   try{var results=await Promise.all([fetch('/api/contour-edit/image?'+q).then(function(r){if(!r.ok)throw Error(t('failed'));return r.blob();}),E.roi==null||currentROI()?.editable===false?Promise.resolve(null):fetch('/api/contour-edit/overlay?'+oq).then(function(r){if(!r.ok)throw Error(t('failed'));return r.json();})]);
    var url=URL.createObjectURL(results[0]),img=new Image();try{img.src=url;await img.decode();}finally{URL.revokeObjectURL(url);}
    if(E.closed||serial!==p.serial||revision!==E.session.revision)return false;p.img=img;p.overlay=results[1];p.loaded=true;draw(a);return true;
   }catch(err){if(!E.closed&&serial===p.serial){status(err.message,true);draw(a);}return false;}
  }
  function showPlanes(){return Promise.all(Object.keys(E.planes).map(loadPlane));}
  function matrix(p){var c=p.canvas,rect=c.getBoundingClientRect();if(!rect.width||!rect.height||!p.w)return null;
   var ratio=window.devicePixelRatio||1,w=Math.round(rect.width*ratio),h=Math.round(rect.height*ratio);if(c.width!==w||c.height!==h){c.width=w;c.height=h;}
   var k=Math.min(rect.width/(p.w*p.sx),rect.height/(p.h*p.sy))*.94*p.zoom;
   return {sx:p.sx*k,sy:p.sy*k,x:rect.width/2-p.w*p.sx*k/2+p.pan[0],y:rect.height/2-p.h*p.sy*k/2+p.pan[1],ratio:ratio,width:rect.width,height:rect.height};}
  function point(p,e){var m=matrix(p),r=p.canvas.getBoundingClientRect();if(!m)return null;var u=(e.clientX-r.left-m.x)/(m.sx*p.w),v=(e.clientY-r.top-m.y)/(m.sy*p.h);
   return u>=0&&u<=1&&v>=0&&v<=1?[u,v]:null;}
  function draw(a){var p=E.planes[a],m=matrix(p);if(!m)return;var c=p.canvas.getContext('2d');c.setTransform(m.ratio,0,0,m.ratio,0,0);c.fillStyle='#02050a';c.fillRect(0,0,m.width,m.height);
   if(!p.img)return;c.save();c.translate(m.x,m.y);c.scale(m.sx,m.sy);c.drawImage(p.img,0,0,p.w,p.h);
   var roi=currentROI(),color=roi?'rgb('+roi.color.join(',')+')':'#ff3d4d';c.strokeStyle=color;c.fillStyle=color;
   function line(points,closed,width){if(!points||!points.length)return;c.beginPath();points.forEach(function(pt,i){var x=pt[0]*p.w,y=pt[1]*p.h;i?c.lineTo(x,y):c.moveTo(x,y);});if(closed)c.closePath();c.lineWidth=width||1.7/Math.max(m.sx,m.sy);c.stroke();}
   (p.overlay?.polygons||[]).forEach(function(poly){line(poly,true,2/Math.max(m.sx,m.sy));});
   if(p.drag&&p.drag.points){c.save();c.setTransform(m.ratio,0,0,m.ratio,0,0);c.lineCap='round';c.lineJoin='round';c.globalAlpha=.65;c.strokeStyle=p.drag.tool==='eraser'?'#ffffff':color;
    var pts=p.drag.points;c.beginPath();pts.forEach(function(pt,i){var x=m.x+pt[0]*p.w*m.sx,y=m.y+pt[1]*p.h*m.sy;i?c.lineTo(x,y):c.moveTo(x,y);});
    if(p.drag.tool==='pencil')c.closePath();else if(pts.length===1)c.lineTo(m.x+pts[0][0]*p.w*m.sx+.01,m.y+pts[0][1]*p.h*m.sy);
     c.lineWidth=p.drag.tool==='pencil'?1.5:p.drag.target.diameter*m.sx/p.sx;c.stroke();c.restore();}
   if(E.measure?.plane===a&&E.measure.index===p.index){c.strokeStyle='#ffde69';line(E.measure.points,false,2/Math.max(m.sx,m.sy));}
   c.restore();if(p.edges){c.font='12px system-ui';c.fillStyle='#a5c9e6';c.textAlign='center';c.fillText(p.edges.top,m.width/2,16);c.fillText(p.edges.bottom,m.width/2,m.height-9);c.textAlign='left';c.fillText(p.edges.left,8,m.height/2);c.textAlign='right';c.fillText(p.edges.right,m.width-8,m.height/2);}
   if(p.hover&&['brush','eraser'].includes(E.tool)&&p.loaded){c.strokeStyle=E.tool==='eraser'?'#fff':color;c.lineWidth=1;c.beginPath();c.arc(m.x+p.hover[0]*p.w*m.sx,m.y+p.hover[1]*p.h*m.sy,E.toolbar.diameter*.5*m.sx/p.sx,0,Math.PI*2);c.stroke();}
   if(!p.loaded){c.fillStyle='#060d1a99';c.fillRect(0,0,m.width,m.height);}
  }
  function down(a,e){if(e.button!==0||E.busy||hasDrag()||!E.session||!E.initialReady)return;var p=E.planes[a];activate(a);if(!p.loaded)return;var f=point(p,e);if(!f&&E.tool!=='pan')return;
   p.canvas.focus();e.preventDefault();if(E.tool==='measure'){if(!E.measure||E.measure.plane!==a||E.measure.index!==p.index||E.measure.points.length===2)E.measure={plane:a,index:p.index,points:[f]};else{E.measure.points.push(f);var z=E.measure.points[0],mm=Math.hypot((z[0]-f[0])*p.w*p.sx,(z[1]-f[1])*p.h*p.sy);status(mm.toLocaleString(document.documentElement.lang,{maximumFractionDigits:2})+' mm');}draw(a);return;}
   if(['brush','eraser','pencil'].includes(E.tool)&&(E.roi==null||currentROI()?.editable===false)){status(t('noRoi'),true);return;}
   p.drag={tool:E.tool,points:f?[f]:[],x:e.clientX,y:e.clientY,pan:p.pan.slice(),center:p.center==null?(E.session.window?.center||0):p.center,width:p.width||E.session.window?.width||1000,pointer:e.pointerId,
    target:{session:E.session.session,revision:E.session.revision,roi:E.roi,plane:a,index:p.index,diameter:E.toolbar.diameter,serial:p.serial,img:p.img}};
   p.canvas.setPointerCapture(e.pointerId);refreshControls();
  }
  function move(a,e){var p=E.planes[a],g=p.drag;p.hover=point(p,e);if(!g){draw(a);return;}if(g.pointer!==e.pointerId)return;var dx=e.clientX-g.x,dy=e.clientY-g.y;
   if(g.tool==='pan'){p.pan=[g.pan[0]+dx,g.pan[1]+dy];draw(a);return;}
   if(g.tool==='window'){p.center=g.center+dy*g.width/300;p.width=Math.max(1,g.width+dx*g.width/200);if(!p.windowTimer)p.windowTimer=setTimeout(function(){p.windowTimer=null;if(!E.closed&&p.drag)loadPlane(a);},100);return;}
   if(['brush','eraser','pencil'].includes(g.tool)){var f=point(p,e);if(!f){g.exited=true;return;}if(!g.exited){if(g.points.length>=4096){g.overflow=true;return;}g.points.push(f);draw(a);}}
  }
  function up(a,e){var p=E.planes[a],g=p.drag;if(!g||g.pointer!==e.pointerId)return;p.drag=null;refreshControls();try{p.canvas.releasePointerCapture(e.pointerId);}catch(_){}
   if(g.tool==='window'){clearTimeout(p.windowTimer);p.windowTimer=null;Object.values(E.planes).forEach(function(q){q.center=p.center;q.width=p.width;});showPlanes();return;}
   if(g.tool==='pointer'&&g.points[0]){var f=g.points[0],u=Math.max(0,Math.min(p.w-1,Math.round(f[0]*p.w-.5))),v=Math.max(0,Math.min(p.h-1,Math.round(f[1]*p.h-.5)));
    var indices=a==='axial'?{axial:p.index,coronal:v,sagittal:u}:a==='coronal'?{axial:v,coronal:p.index,sagittal:u}:{axial:v,coronal:u,sagittal:p.index};
    Object.keys(indices).forEach(function(k){E.planes[k].index=indices[k];});showPlanes();return;}
   if(['brush','eraser','pencil'].includes(g.tool)){var target=g.target;
    if(E.closed||!p.loaded||target.session!==E.session?.session||target.revision!==E.session.revision||target.roi!==E.roi||target.index!==p.index||target.serial!==p.serial||target.img!==p.img){draw(a);return;}
    if(g.overflow){status(t('longStroke'),true);draw(a);return;}if(g.tool==='pencil'&&g.points.length<3){draw(a);return;}
    mutate('stroke',{roi:target.roi,plane:target.plane,index:target.index,points:g.points,diameter_mm:target.diameter,operation:g.tool==='eraser'?'erase':g.tool==='pencil'?'polygon':'brush'}).then(consume);
   }else draw(a);
  }
  function reference(){return {b:cfg.b||'',source:cfg.source||'thumbnail',uid:E.session?.uid||'',frame_uid:E.session?.frame_uid||''};}
  function scheduleScene(){clearTimeout(E.sceneTimer);if(!E.sceneEnabled&&!cfg.onPreview)return;E.sceneTimer=setTimeout(requestScene,120);}
  async function requestScene(){if(E.closed||!E.session||!E.initialReady)return;var serial=++E.sceneSerial,revision=E.session.revision,session=E.session.session;
   if(E.sceneAbort)E.sceneAbort.abort();E.sceneAbort=new AbortController();sceneMessage.hidden=false;sceneMessage.textContent=t('building3d');
   var previous=new Map((E.scene?.meshes||[]).map(function(m){return [m.roi,m];})),known={};previous.forEach(function(m,id){if(Number.isInteger(m.geometry_revision))known[String(id)]=m.geometry_revision;});
   try{var response=await fetch('/api/contour-edit/scene',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({s:session,csrf:E.session.csrf,revision:revision,known:known}),signal:E.sceneAbort.signal});var result=await response.json();
    if(E.closed||serial!==E.sceneSerial||revision!==E.session.revision||session!==E.session.session)return;
    if(!response.ok||result.error)throw Error(errorText(result.error||'EDIT_FAILED'));
    result.meshes=result.meshes.map(function(m){if(!m.unchanged)return m;var old=previous.get(m.roi);if(!old||old.geometry_revision!==m.geometry_revision)throw Error(t('failed'));return Object.assign({},old,m,{unchanged:false});});result.reference=reference();E.scene=result;
    if(E.sceneEnabled&&!cfg.externalScene){if(!E.sceneViewer)E.sceneViewer=window.RadaiContourScene.create(sceneCanvas);E.sceneViewer.update(result);}
    var count=result.meshes.reduce(function(n,m){return n+(m.faces||[]).length;},0);sceneMessage.hidden=count>0&&!result.skipped.length;sceneMessage.textContent=result.skipped.length?t('scenePartial'):t('sceneEmpty');
    if(cfg.onPreview)cfg.onPreview(result);cfg.externalScene?.request?.();window.dispatchEvent(new CustomEvent('radai:contour-preview',{detail:result}));
   }catch(err){if(err.name==='AbortError'||E.closed||serial!==E.sceneSerial||revision!==E.session?.revision)return;sceneMessage.hidden=false;sceneMessage.textContent=err.message==='WEBGL_UNAVAILABLE'?t('noWebGL'):err.message;}
  }
  function close(discard){if(E.closed||(E.session&&(E.busy||hasDrag())))return;
   var keep=!!E.session&&E.initialReady&&!discard&&E.dirty;E.suspended=keep;resize.disconnect();restoreExternal();if(!inline)d.close();d.remove();instance=null;
   if(keep){drafts.set(draftKey,E);status(t('draftKept'));}
   else{E.closed=true;E.generation++;clearTimeout(E.sceneTimer);if(E.sceneAbort)E.sceneAbort.abort();if(E.sceneViewer)E.sceneViewer.dispose();E.toolbar.destroy();drafts.delete(draftKey);
    if(E.session)call('close',{s:E.session.session,csrf:E.session.csrf,revision:E.session.revision}).catch(function(){});
    window.removeEventListener('beforeunload',beforeLeave);window.removeEventListener('pagehide',pageLeft);}
   if(cfg.onClose)cfg.onClose((discard?E.lastSavedReceipt:E.savedReceipt)||null,{draft:keep,lastSavedReceipt:E.lastSavedReceipt||null,reference:reference(),session:E.session?.session,revision:E.session?.revision});}
  E.close=close;
  E.requestPreview=requestScene;
  E.resume=function(next){cfg=Object.assign(cfg,next||{});E.cfg=cfg;E.suspended=false;instance=E;(cfg.inlineRoot||document.body).appendChild(d);mountExternal();if(!inline)d.showModal();resize.observe(grid);status(E.dirty?t('draftKept'):t('ready'));refreshControls();Object.keys(E.planes).forEach(draw);if(E.sceneViewer)E.sceneViewer.draw();if(cfg.tool){E.tool=cfg.tool;E.toolbar.setTool(cfg.tool);}E.ready=Promise.resolve(E);scheduleScene();};
  function beforeLeave(event){if(E.dirty&&!E.closed){event.preventDefault();event.returnValue='';}}
  function pageLeft(){if(E.session&&!E.closed)navigator.sendBeacon('/api/contour-edit/close',new Blob([JSON.stringify({s:E.session.session,csrf:E.session.csrf,revision:E.session.revision})],{type:'application/json'}));}
  window.addEventListener('beforeunload',beforeLeave);window.addEventListener('pagehide',pageLeft);
  busy(true,t('loading'));load.textContent=t('loading');if(window.uiCarregando)window.uiCarregando(load,true,t('loading'));
  E.ready=call('open',{b:cfg.b||'',source:cfg.source||'thumbnail',rs:cfg.rs||''}).then(function(r){if(E.closed){call('close',{s:r.session,csrf:r.csrf,revision:r.revision}).catch(function(){});return;}E.dirty=false;return consume(r);}).then(function(results){if(E.closed)return;if(!results||results.some(function(ok){return !ok;}))throw Error(t('failed'));E.initialReady=true;load.hidden=true;busy(false,t('ready'));if(!E.session?.rois?.length)setTab(true);scheduleScene();}).catch(function(err){if(E.closed)return;load.hidden=true;busy(false);status(err.message,true);});
  return Promise.resolve(E);
 }
 window.RadaiContourEditor={open:open,text:t,current:function(){return instance;},drafts:function(){return Array.from(drafts.values()).map(function(e){return {session:e.session?.session,revision:e.session?.revision,reference:{b:e.cfg.b,source:e.cfg.source||'thumbnail'},dirty:e.dirty};});}};
})();
'''
JS = SCENE_JS + _JS.replace('__TEXT__', json.dumps(TEXT, ensure_ascii=False)).replace('__ERRORS__', json.dumps(ERRORS, ensure_ascii=False))
