const assert=require('node:assert/strict');
const {chromium}=require(process.env.NEURO_PLAYWRIGHT_MODULE||'playwright');
const langs=['pt-BR','en','es','de','fr','it','pl','ja','zh-CN','ar','ko','bn'];
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_EXECUTABLE||'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',headless:true,args:['--disable-gpu','--no-first-run']});
 const context=await browser.newContext({viewport:{width:1440,height:1000}});
 const results=[];
 try{
  for(const kind of ['ver','anatomia','torax','vascular','bolus','elastic','neuro','lung4d','lungreport','lungscreening']){
   process.stdout.write('Checking '+kind+'\n');
   const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
   await page.goto(process.env.DICOM_ADAPTER_URL+'/page/'+kind,{waitUntil:'domcontentloaded'});
   await page.waitForFunction(()=>!!window.RadaiDicomAdapters&&!!window.RadaiDicomToolbar);
   await page.evaluate(kind=>{
    window.adapterCalls=[];window.adapterActions=[];
    RadaiContourEditor.open=async cfg=>{adapterCalls.push(cfg);const div=document.createElement('div');['zoomIn','zoomOut','fit','interpolate'].forEach(k=>{const b=document.createElement('button');b.dataset.dicomTool=k;b.onclick=()=>adapterActions.push(k);div.append(b);});return{closed:false,ready:Promise.resolve(),toolbar:{element:div}};};
    if(kind==='ver'){CP.serie={b:'cp-ticket',rs:[{arquivo:'full.dcm'},{arquivo:'labels.npz',mapa:true}]};CP.lados=[{arq:'full.dcm'},{arq:'labels.npz'}];CP.carregando=false;document.getElementById('cp_raiz').classList.remove('cp-oculto');}
    if(['anatomia','torax','vascular'].includes(kind)){R3.b='r3-ticket';R3.abrindo=false;if(typeof R3M!=='undefined'){R3M.modo='gl';R3M.arquivos=[{arquivo:'labels.npz',mapa:true}];}const s=document.getElementById('r3_rs');if(s){s.innerHTML='<option value="@rotulos">labels</option>';s.value='@rotulos';}}
    if(kind==='bolus'){document.getElementById('bo-corpo').style.display='';document.getElementById('bo-abrir').disabled=false;document.getElementById('bo-i-ax').src='/api/bolus/corte?b=bolus-ticket&plano=ax';}
    if(kind==='elastic'){EL_SEL.fixa={b:'elastic-fixed-ticket'};EL_SEL.movel={b:'elastic-moving-ticket'};elFundindo=false;document.getElementById('el-corpo').classList.add('on');}
    if(kind==='neuro'){NeuroStudy.state.scene={};document.getElementById('viewer').hidden=false;document.getElementById('viewer').dataset.contourReference='neuro-reference-ticket';}
    if(kind==='lung4d'){document.getElementById('cine').hidden=false;document.getElementById('cine').dataset.contourReference='lung-native-phase-3';}
    if(['lungreport','lungscreening'].includes(kind)){const m=document.querySelector('.lung-mpr');m.dataset.contourReference='lung-displayed-volume';m.dataset.contourReady='1';}
    RadaiDicomAdapters.refresh();
   },kind);
   await page.keyboard.press('Escape');
   const bar=page.locator('.rdt-viewer-tools .rdt-toolbar').first();await bar.waitFor({state:'visible'});
   await page.waitForFunction(()=>{const b=document.querySelector('.rdt-viewer-tools [data-dicom-tool=editor]');return b&&!b.disabled;});
   assert.equal(await page.locator('.rdt-viewer-tools').count(),1,kind+' duplicate toolbar');
   await bar.locator('[data-dicom-tool=editor]').click();
   const call=await page.evaluate(()=>adapterCalls.at(-1));
   assert.equal(call.b,{ver:'cp-ticket',anatomia:'r3-ticket',torax:'r3-ticket',vascular:'r3-ticket',bolus:'bolus-ticket',elastic:'elastic-fixed-ticket',neuro:'neuro-reference-ticket',lung4d:'lung-native-phase-3',lungreport:'lung-displayed-volume',lungscreening:'lung-displayed-volume'}[kind]);
   assert.equal(call.source,'thumbnail');
   if(['anatomia','torax'].includes(kind))assert.equal(call.rs,'');
   if(kind==='ver'){
    assert.equal(call.rs,'full.dcm');
    await page.locator('#cp_visor1').dispatchEvent('pointerenter');
    await bar.locator('[data-dicom-tool=brush]').click();
    assert.equal((await page.evaluate(()=>adapterCalls.at(-1))).rs,'');
    const zoom=await page.evaluate(()=>CP.zoom);await bar.locator('[data-dicom-tool=zoomIn]').click();assert.ok(await page.evaluate(old=>CP.zoom>old,zoom));
    const saved=await page.evaluate(()=>{cpCarregarLado=side=>window.refreshedSide=side.arq;cpPedirMostrar=()=>{};adapterCalls[0].onClose({basename:'RS_RadAI_EDIT_test.dcm',fallback:false});return{file:CP.lados[0].arq,refreshed:window.refreshedSide,listed:CP.serie.rs.some(r=>r.arquivo==='RS_RadAI_EDIT_test.dcm')};});
    assert.deepEqual(saved,{file:'RS_RadAI_EDIT_test.dcm',refreshed:'RS_RadAI_EDIT_test.dcm',listed:true});
   }
   if(['anatomia','torax'].includes(kind)){
    const selected=await page.evaluate(()=>{r3mEstruturas=file=>window.refreshed3D=file;adapterCalls[0].onClose({basename:'RS_RadAI_EDIT_test.dcm',fallback:false});return window.refreshed3D;});
    assert.equal(selected,'RS_RadAI_EDIT_test.dcm');
   }
   if(kind==='vascular'){
    await page.evaluate(()=>{VX.zoom=3;VX.ux=14;VX.uy=19;VX.lapis=false;});await bar.locator('[data-dicom-tool=fit]').click();
    assert.deepEqual(await page.evaluate(()=>[VX.zoom,VX.ux,VX.uy]),[1,0,0]);
   }
   if(kind==='bolus'){
    await bar.locator('[data-dicom-tool=zoomIn]').click();await page.waitForFunction(()=>adapterActions.includes('zoomIn'));
    await page.evaluate(()=>document.getElementById('bo-i-ax').src='https://outside.invalid/api/bolus/corte?b=foreign');
    await page.waitForFunction(()=>document.querySelector('.rdt-viewer-tools [data-dicom-tool=editor]').disabled);
    await page.evaluate(()=>document.getElementById('bo-i-ax').src='/api/bolus/corte?b=bolus-ticket');
   }
   if(kind==='lung4d'){
    await page.evaluate(()=>document.getElementById('cine').dataset.contourReference='lung-native-phase-4');
    await bar.locator('[data-dicom-tool=editor]').click();
    assert.equal((await page.evaluate(()=>adapterCalls.at(-1))).b,'lung-native-phase-4');
    assert.equal(call.b,'lung-native-phase-3','prior editor selection must remain fixed');
   }
   if(['lungreport','lungscreening'].includes(kind)){
    assert.equal(call.slice,undefined,'reoriented display must not provide a native slice index');
    await page.evaluate(()=>{const m=document.querySelector('.lung-mpr');delete m.dataset.contourReference;delete m.dataset.contourReady;});
    await page.waitForFunction(()=>document.querySelector('.rdt-viewer-tools [data-dicom-tool=editor]').disabled);
    await page.evaluate(()=>{const m=document.querySelector('.lung-mpr');m.dataset.contourReference='lung-next-report-volume';m.dataset.contourReady='1';});
    await page.waitForFunction(()=>!document.querySelector('.rdt-viewer-tools [data-dicom-tool=editor]').disabled);
    await bar.locator('[data-dicom-tool=brush]').click();assert.equal((await page.evaluate(()=>adapterCalls.at(-1))).b,'lung-next-report-volume');
    assert.equal(call.b,'lung-displayed-volume','prior editor selection must remain fixed');
   }
   const labels=[];
   for(const lang of langs){
    await page.evaluate(lang=>{localStorage.setItem('radai_idioma',lang);document.documentElement.lang=lang;if(window.radaiRetraduzir)radaiRetraduzir();},lang);
    await page.waitForFunction(lang=>{const b=document.querySelector('.rdt-viewer-tools [data-dicom-tool=editor]');return document.documentElement.lang===lang&&b.getAttribute('aria-label')===RadaiDicomToolbar.label('editor');},lang);
    const label=await bar.locator('[data-dicom-tool=editor]').getAttribute('aria-label');assert.ok(label&&label.length>2,kind+' '+lang);labels.push(label);
    const bounds=await bar.boundingBox();assert.ok(bounds.width<=1440,kind+' toolbar overflow '+lang);
   }
   assert.ok(new Set(labels).size>=10,kind+' missing translation');
   assert.deepEqual(errors,[],kind+' JavaScript errors');
   results.push({page:kind,languages:langs.length,ticket:call.b,toolbarCount:1,otherPageErrors:errors});
   await page.close();
  }
  process.stdout.write(JSON.stringify({passed:results.length,results})+'\n');
 }finally{await browser.close();}
})().catch(e=>{console.error(e.stack||e);process.exitCode=1;});
