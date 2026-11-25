"""Interactions shared by the anatomy and neuroanatomy reconstruction pages."""

CSS = """
.r3-tela:focus-visible,.r3-tela3d:focus-visible{outline:2px solid var(--mod-recon);outline-offset:2px}
.r3-quadro>.r3-tela3d{aspect-ratio:1;min-height:0;width:100%}
.r3-quadro>.r3-tela3d .r3-vistas{display:none}
.r3-col3d>.r3-tela{height:100%;min-height:0;aspect-ratio:auto}
.r3-col3d>.r3-tela img{width:100%;height:100%;object-fit:contain}
.r3-plan-nav{padding:10px;display:grid;gap:10px;align-content:start}
.r3-plan-nav .rot{display:flex;justify-content:space-between;gap:8px;text-transform:capitalize}
.r3-plan-nav input[type=range]{width:100%}
.r3-plan-nav .r3-ctrl{margin:0;flex-wrap:wrap}
.r3-ctrl[hidden],.r3-quadro[hidden],.r3-dsn[hidden],.rdt-viewer-tools[hidden],.r3-plan-nav[hidden],.r3-3d[data-plane-main] .r3-ferramentas>:not(.r3-plan-nav):not(.r3-grav){display:none}
.r3-ferramentas:has(.r3-plan-nav:not([hidden])){display:block}
.r3-max{box-sizing:border-box;width:96vw;max-width:96vw;height:94dvh;max-height:94dvh;
 margin:auto;padding:12px;background:var(--bg-0,#081321);color:var(--text,#dfebfa);
 border:1px solid var(--line-strong,#36526f);border-radius:12px}
.r3-max::backdrop{background:#030912d9}
.r3-max[open]{display:flex;flex-direction:column;gap:10px}
.r3-max-head{display:flex;align-items:center;justify-content:space-between}
.r3-max>.r3-3d{--r3-altura:100%;flex:1;min-height:0;width:100%;grid-template-columns:minmax(0,1fr) minmax(170px,18%) minmax(190px,22%);grid-template-rows:minmax(0,1fr)}
.r3-max>.r3-3d>.r3-ferramentas,.r3-max>.r3-3d>.r3-l3d{grid-column:auto;grid-row:auto}
.r3-max>.r3-3d>.r3-ferramentas{display:flex;flex-direction:column}
@media(max-width:800px){
 .r3-max>.r3-3d{display:flex;flex-direction:column;overflow:auto}
 .r3-max .r3-col3d{height:62dvh;flex:none}
 .r3-max .r3-ferramentas,.r3-max .r3-l3d{height:auto;max-height:none;flex:none}
}
"""

JS = r"""
function r3ConfigurarPalco(){
 const main=document.querySelector('.r3-col3d'), grid=document.querySelector('.r3-grade');
 const side=document.querySelector('.r3-ferramentas'), three=r3El('r3_tela3d');
 if(!main || !grid || !side || !three) return;
 const stage=main.closest('.r3-3d'), tools=document.createElement('div');
 const winControls=grid.nextElementSibling;
 const winAnchor=document.createComment('janelas');
 winControls.before(winAnchor);
 tools.className='r3-plan-nav'; tools.hidden=true; side.prepend(tools);
 const dialog=document.createElement('dialog');
 dialog.className='r3-max';
 dialog.setAttribute('aria-labelledby','r3-max-title');
 dialog.innerHTML='<header class="r3-max-head"><strong id="r3-max-title"></strong><button type="button" class="ui-bt" data-radai-frase>Fechar</button></header>';
 const stageAnchor=document.createComment('reconstrução'); stage.before(stageAnchor);
 document.body.append(dialog);
 let selected=null;
 const zoom=document.createElement('div');zoom.className='r3-ctrl';
 for(const [glyph,factor,label] of [['−',.8,'Afastar'],['+',1.25,'Aproximar']]){
  const b=document.createElement('button');b.type='button';b.className='ui-bt';b.textContent=glyph;b.title=window.radaiFrase?.(label)||label;b.onclick=()=>scalePlane(factor);zoom.append(b)
 }
 tools.append(zoom);
 function scalePlane(factor){
  if(!selected)return;selected.zoom=Math.max(.25,Math.min(10,selected.zoom*factor));
  selected.view.querySelector('img').style.transform='scale('+selected.zoom+')';
 }
 window.r3PlaneRecording=()=>selected?{img:selected.view.querySelector('img'),zoom:selected.zoom}:null;
 const panels=[...grid.querySelectorAll('.r3-quadro')].map((card, index)=>({
   card,index,view:card.querySelector('.r3-tela'),parts:[...card.children],
   zoom:1,slider:r3El('r3_pos'+(index===3?'p':index))
 }));
 const miniTitle=document.createElement('div');miniTitle.className='rot';miniTitle.textContent='3D';
 function hint(node,primary,label){
  node.tabIndex=0;
  const tip=window.radaiFrase?radaiFrase(primary?'Ampliar':'Plano principal'):(primary?'Ampliar':'Plano principal');
  node.title=tip;
  node.setAttribute('aria-label',label+' · '+tip);
 }
 function name(panel){return panel.parts[0].querySelector('span').textContent;}
 function hints(){
  hint(three,!selected,'3D');
  panels.forEach(p=>hint(p.view,p===selected,name(p)));
 }
 function repaint(){
  if(typeof r3gPedir==='function' && window.R3G && R3G.gl) r3gPedir();
  if(typeof n3Desenhar==='function' && !r3El('cv3D').hidden) n3Desenhar();
 }
 function restore(){
  if(!selected)return;
  selected.view.querySelector('img').style.removeProperty('transform');main.append(three);
  miniTitle.remove();
  selected.card.append(...selected.parts);
  winAnchor.after(winControls);
  selected=null; tools.hidden=true;
  delete stage.dataset.planeMain;
  hints(); repaint();
 }
 function promote(p){
  restore();
  if(!p){three.focus({preventScroll:true});return;}
  selected=p; stage.dataset.planeMain=String(p.index);
  tools.append(...p.parts.filter(part=>part!==p.view),winControls);
  p.card.append(miniTitle,three); main.append(p.view); tools.hidden=false;
  scalePlane(1);hints(); p.view.focus({preventScroll:true}); repaint();
 }
 function close(){if(dialog.open)dialog.close();}
 function maximize(){
  if(dialog.open)return;
  dialog.querySelector('strong').textContent=selected?name(selected):'3D';
  dialog.append(stage);dialog.showModal();dialog.querySelector('button').focus();
  repaint();
 }
 dialog.querySelector('button').addEventListener('click',close);
 dialog.addEventListener('click',e=>{if(e.target===dialog)close();});
 dialog.addEventListener('close',()=>{
  stageAnchor.after(stage);(selected?selected.view:three).focus({preventScroll:true});repaint();
 });
 function bind(target,p){
  function activate(event){
   if(!R3.b || !R3.forma || (event.target.closest('button,input,select') && event.target!==target))return;
   if(target.parentNode===main)maximize();else promote(p);
  }
  target.addEventListener('dblclick',activate);
  target.addEventListener('keydown',event=>{
    if((event.key==='Enter' || event.key===' ') && event.target===target){
     event.preventDefault();activate(event);
    }
  });
 }
 bind(three,null);
 panels.forEach(p=>{
  bind(p.view,p);
  p.view.addEventListener('wheel',e=>{
   if(p!==selected || !R3.forma || !e.deltaY)return;
   if(e.ctrlKey){e.preventDefault();scalePlane(e.deltaY<0?1.15:1/1.15);return;}
   e.preventDefault();
   const value=Number(p.slider.value)+(e.deltaY>0?1:-1);
   p.slider.value=String(value);p.slider.dispatchEvent(new Event('input'));
  },{passive:false});
 });
 function sync(p){
  const axis=p.index===3?R3.proj:p.index;
  const last=Math.max(0,(R3.forma && R3.forma[axis] || 1)-1);
  p.slider.max=String(last);p.slider.value=String(Math.round((R3.pos[axis]||0)*last));
  if(p.index!==3)r3El('r3_posv'+axis).textContent=(Number(p.slider.value)+1)+' / '+(last+1);
 }
 window.r3PalcoReiniciar=()=>{close();restore();};
 window.r3PalcoSerie=(data)=>{
  const archive=Boolean(data && data.historico_planar);
  panels[3].card.hidden=archive;winControls.hidden=archive;
  const drawing=stage.querySelector('.r3-dsn');if(drawing)drawing.hidden=archive;
  panels.forEach(sync);
 };
 panels.forEach(p=>{
  p.slider.oninput=()=>{
   const axis=p.index===3?R3.proj:p.index;
   R3.pos[axis]=p.slider.max>0 ? Number(p.slider.value)/Number(p.slider.max) : 0;
   panels.filter(other=>other.index===axis || (other.index===3 && R3.proj===axis)).forEach(sync);
   r3Pintar(axis);if(R3.proj===axis)r3Proj();
  };
 });
 r3El('r3_eixop').addEventListener('change',()=>sync(panels[3]));
 hints();
}
"""
