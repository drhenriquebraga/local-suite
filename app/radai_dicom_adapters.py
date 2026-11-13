"""Viewer adapters pass only selected opaque DICOM tickets to the common editor."""
JS = r'''
(function(){'use strict';if(window.RadaiDicomAdapters)return;
 var adapters=[], watched=false;
 function el(id){return document.getElementById(id);}
 function rtstruct(value,entries){
  var name=String(value||'');
  if(!name||/^[#@]/.test(name)||/[\\/:\x00]/.test(name)||/\.(?:nii(?:\.gz)?|npz|npy|mha|mhd|nrrd|zarr)$/i.test(name))return '';
  var row=(entries||[]).find(function(r){return (r.arquivo||r.id)===name;});
  return row&&(row.mapa||row.cod==='rotulos')?'':name;
 }
 function imageTicket(id,path){
  var image=el(id),src=image&&image.getAttribute('src');if(!src)return '';
  try{var url=new URL(src,location.href);return url.origin===location.origin&&url.pathname===path?url.searchParams.get('b')||'':'';}catch(_){return '';}
 }
 function register(cfg){
  var scope=typeof cfg.scope==='string'?document.querySelector(cfg.scope):cfg.scope;if(!scope||scope.dataset.dicomToolbar)return null;
  scope.dataset.dicomToolbar='1';var target=document.createElement('div');target.className='rdt-viewer-tools';target.style.margin='8px 0';scope.before(target);
  function selection(){try{return cfg.selection();}catch(_){return null;}}
  function edit(tool){var s=selection();if(!s||!s.b)return;var action=['zoomIn','zoomOut','fit','interpolate'].includes(tool);
   var p=Object.assign({},s,{tool:tool==='editor'||action?'pointer':tool,onClose:function(receipt){if(cfg.onEdited)cfg.onEdited(s,receipt);}});
   window.RadaiContourEditor.open(p).then(function(E){if(action)E.ready.then(function(){if(!E.closed)E.toolbar.element.querySelector('[data-dicom-tool="'+tool+'"]')?.click();});}).catch(function(){});}
  var toolbar=window.RadaiDicomToolbar.mount(target,{scope:scope,tools:cfg.tools||['pointer','pencil','brush','eraser','pan','measure','window','zoomIn','zoomOut','fit','interpolate','editor'],
   enabled:function(k){var s=selection();return !!(s&&s.b)&&(!cfg.ready||cfg.ready());},
   onTool:function(k,T){if(k==='pointer')return;if(cfg.native&&cfg.native(k))return;edit(k);T.setTool('pointer');},
   onAction:function(k){if(cfg.native&&cfg.native(k))return;edit(k);}});
  var record={toolbar:toolbar,scope:scope,target:target,selection:selection};adapters.push(record);refresh(record);return record;
 }
 function refresh(a){a.target.hidden=!a.scope.isConnected||!a.scope.getClientRects().length;if(!a.target.hidden)a.toolbar.refresh();}
 function defaults(){
  if(typeof CP!=='undefined'&&el('cp_raiz')&&!el('cp_raiz').dataset.dicomToolbar){
   var side=0;[0,1].forEach(function(i){var v=el('cp_visor'+i);if(v){v.addEventListener('pointerenter',function(){side=i;});v.addEventListener('focusin',function(){side=i;});}});
   register({scope:el('cp_raiz'),selection:function(){return CP.serie?{b:CP.serie.b,source:'thumbnail',rs:rtstruct(CP.lados[side]?.arq,CP.serie.rs),slice:CP.corte,viewerSide:side}:null;},ready:function(){return !CP.carregando;},
    native:function(k){if(k==='zoomIn'||k==='zoomOut'){cpZoom(k==='zoomIn'?1.25:.8);return true;}if(k==='fit'){cpAjustar();return true;}return k==='pan'&&CP.zoom>1;},
    onEdited:function(selected,receipt){if(!CP.serie||CP.serie.b!==selected.b)return;CP.cacheCont={};CP.ordemCache=[];
     if(receipt&&!receipt.fallback&&receipt.basename){var file=receipt.basename;CP.serie.rs=CP.serie.rs||[];
      if(!CP.serie.rs.some(function(r){return r.arquivo===file;}))CP.serie.rs.push({arquivo:file,cod:'edit',curto:file,rotulo:file});
      CP.serie.sem_contorno=false;var side=CP.lados[selected.viewerSide||0];side.arq=file;
      if(window.cpPreencherSeletores)cpPreencherSeletores();if(window.cpCarregarLado)cpCarregarLado(side);}
     if(window.cpPedirMostrar)cpPedirMostrar();}});
  }
  if(typeof R3!=='undefined'){
   var root=el('r3_palco')||el('r3_cena')||el('r3_tela3d')?.closest('.r3-q3d')||el('vx_cmd')?.parentElement||el('cvGL')?.closest('.ps-corpo');
   if(root&&!root.dataset.dicomToolbar)register({scope:root,selection:function(){return {b:R3.b,source:'thumbnail',rs:rtstruct(el('r3_rs')?.value,typeof R3M!=='undefined'?R3M.arquivos:[])};},ready:function(){return !R3.abrindo;},
    native:function(k){if(k==='zoomIn'||k==='zoomOut'||k==='fit'){
      if(typeof VX!=='undefined'&&window.vxZoom){if(VX.lapis)return false;vxZoom(k==='fit'?0:k==='zoomIn'?1.25:.8);return true;}
      if(window.R3G&&window.r3gPedir&&typeof R3M!=='undefined'&&R3M.modo==='gl'){
       R3G.zoom=k==='fit'?1:Math.max(.2,Math.min(25,R3G.zoom*(k==='zoomIn'?1.25:.8)));if(k==='fit'){R3G.ux=0;R3G.uy=0;}r3gPedir();return true;}}
     return false;},onEdited:function(selected,receipt){
      if(receipt&&!receipt.fallback&&receipt.basename&&R3.b===selected.b&&typeof R3M!=='undefined'&&window.r3mEstruturas){R3M.nuvens={};r3mEstruturas(receipt.basename);}
     }});
  }
  var box=el('bo-corpo')||el('bo-visores')||el('bo-palco');
  if(box&&!box.dataset.dicomToolbar){
   register({scope:box,selection:function(){var ticket=imageTicket('bo-i-ax','/api/bolus/corte');return ticket?{b:ticket,source:'thumbnail'}:null;},
    ready:function(){return !!box.getClientRects().length&&!el('bo-abrir')?.disabled;}});
  }
  if(typeof EL_SEL!=='undefined'){
   var eroot=el('el-corpo')||el('el-visor')||el('el-img')?.parentElement;
   if(eroot&&!eroot.dataset.dicomToolbar)register({scope:eroot,selection:function(){return EL_SEL.fixa?{b:EL_SEL.fixa.b,source:'thumbnail'}:null;},
    ready:function(){return typeof elFundindo==='undefined'||!elFundindo;}});
  }
  var cine=el('cine');
  if(cine&&!cine.dataset.dicomToolbar)register({scope:cine,selection:function(){
   var ticket=cine.dataset.contourReference;return ticket?{b:ticket,source:'thumbnail'}:null;
  },ready:function(){return !cine.hidden;}});
  var lung=document.querySelector('.lung-mpr');
  if(lung&&!lung.dataset.dicomToolbar)register({scope:lung,selection:function(){
   var ticket=lung.dataset.contourReference;return ticket&&lung.dataset.contourReady==='1'?{b:ticket,source:'thumbnail'}:null;
  },ready:function(){return lung.dataset.contourReady==='1';}});
 }
 function start(){defaults();if(watched)return;watched=true;var pending=false;
  new MutationObserver(function(){if(pending)return;pending=true;requestAnimationFrame(function(){pending=false;defaults();adapters=adapters.filter(function(a){if(a.scope.isConnected){refresh(a);return true;}a.toolbar.destroy();a.target.remove();return false;});});}).observe(document.body,{childList:true,subtree:true});
  setInterval(function(){adapters.forEach(refresh);},1000);
 }
 window.RadaiDicomAdapters={register:register,refresh:defaults};
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();
'''
