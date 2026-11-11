const fs=require('fs'),assert=require('assert');
const {chromium}=require(process.argv[3]);
const folder=process.argv[2],words=JSON.parse(fs.readFileSync(folder+'/expected.json','utf8'));
const errorMessage='O ZIP excede o limite permitido para esta operação.';
let terminalState='failed',coldState=null;
function status(slug){
 const version=slug==='neuro-rt'?'1.3.4':'1.1.4';
 const policy={schema:'neuro-rt/consent-policy/1',plugin_id:'neuro-rt',title:'SYNTHETIC TERMS',version:'1.1',digest:'a'.repeat(64),clauses:[{text:'SYNTHETIC TERMS'}]};
 const value={token:'SYNTHETIC_TOKEN',host_pid:1234,state:'ready',mounted:true,base_ready:true,code_ready:true,
   code_version:version,active_version:version,version,weights:{state:'missing',version:null},
   consent:{policy,installation_accepted:true,first_use_accepted:true},policy:{title:'LUNG RT',version:'1.0',digest:'b'.repeat(64),clauses:['SYNTHETIC TERMS']},accepted:true,
   update:{state:terminalState,error_code:'INSTALL_FAILED',reason:'SYNTHETIC OLD FAILURE'},
   last_result:{error_code:'INSTALL_FAILED',message:'SYNTHETIC OLD FAILURE',error_component:'old-model'},release_check:{state:'current'}};
 if(slug==='neuro-rt'&&coldState)Object.assign(value,{state:coldState,mounted:false,base_ready:false,code_ready:false});
 return value;
}
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.argv[4]});
 try{
  for(const locale of Object.keys(words)){
   terminalState=['failed','ready','idle',undefined][Object.keys(words).indexOf(locale)%4];
   const page=await browser.newPage({viewport:{width:390,height:900},reducedMotion:'reduce'});
   const errors=[],mutations=[],launched=new Set();let failUpload=true,landings=0,expectedLocal=true,coldReads=0;
   page.on('pageerror',e=>errors.push(String(e)));
   await page.addInitScript(code=>localStorage.setItem('radai_idioma',code),locale);
   await page.route('http://suite.test/**',async route=>{
    const req=route.request(),url=new URL(req.url());
    if(url.pathname==='/settings')return route.fulfill({contentType:'text/html',body:fs.readFileSync(folder+'/settings.html','utf8')});
    if(url.pathname==='/minipage')return route.fulfill({contentType:'text/html',body:fs.readFileSync(folder+'/minipage.html','utf8')});
    if(url.pathname==='/neuro'){landings++;return route.fulfill({contentType:'text/html',body:fs.readFileSync(folder+'/landing.html','utf8')});}
    if(url.pathname==='/neuro/')return route.fulfill({contentType:'text/html',body:'<p>SYNTHETIC NEURO MINIPAGE</p>'});
    if(url.pathname==='/radai-idiomas.js')return route.fulfill({contentType:'application/javascript',body:fs.readFileSync(folder+'/languages.js','utf8')});
    if(req.resourceType()==='script')return route.fulfill({contentType:'application/javascript',body:''});
    if(!url.pathname.startsWith('/api/plugins/'))return route.fulfill({json:{}});
    const slug=url.pathname.includes('neuro-rt')?'neuro-rt':'lung-rt';
    if(req.method()==='GET'){
      if(slug==='neuro-rt'&&coldState)coldReads++;
      return route.fulfill({json:launched.has(slug)?{...status(slug),update:{state:'external_install'},preparing:true}:status(slug)});
    }
    if(url.pathname.endsWith('/local/upload')){
      assert.equal(url.searchParams.get('operation'),'weights');
      if(failUpload)return route.fulfill({status:413,json:{detail:{code:'LOCAL_UPLOAD_TOO_LARGE',message:errorMessage}}});
      return route.fulfill({json:{source_id:'WEIGHTS_SOURCE',version:slug==='neuro-rt'?'1.3.0':'1.1.2',format:'offline_bundle'}});
    }
    if(url.pathname.endsWith('/install')||url.pathname.endsWith('/update')){
      const payload=req.postDataJSON();assert.equal(payload.operation,'weights');
      if(expectedLocal)assert.equal(payload.source_id,'WEIGHTS_SOURCE');else assert(!payload.source_id);
      mutations.push({slug,payload});launched.add(slug);
      return route.fulfill({json:{state:'external_install'}});
    }
    if(url.pathname.endsWith('/connectivity'))return route.fulfill({json:{github:{status:'unavailable',code:'HTTP_403'},mirror:{status:'available',code:'OK'}}});
    throw Error('Unexpected mutation '+url.pathname);
   });
   if(locale==='pt-BR'){
    for(const phase of ['checking','loading']){
     coldState=phase;coldReads=0;
     await page.goto('http://suite.test/neuro');
     await page.waitForFunction(phase=>window.NeuroPluginUpdate?.state.last?.state===phase,phase);
     assert(await page.locator('[data-pi-feedback]').isHidden(),'cold '+phase+' landing showed historical failure');
     const deadline=Date.now()+10000;
     while(coldReads<4){assert(Date.now()<deadline,'cold verification was not polled');await new Promise(r=>setTimeout(r,50));}
     assert(await page.locator('[data-pi-feedback]').isHidden(),'historical failure returned during cold verification');
     assert(!(await page.locator('#neuro-update').innerText()).includes('INSTALL_FAILED'));
     coldState=null;await page.waitForURL('http://suite.test/neuro/');
    }
    coldState='checking';await page.goto('http://suite.test/settings');
    await page.waitForFunction(()=>window.NeuroPluginUpdate?.state.last?.state==='checking');
    assert((await page.locator('#neuro-update [data-pi-feedback]').innerText()).includes('INSTALL_FAILED'),'settings history was suppressed');
    coldState=null;
   }
   landings=0;
   await page.goto('http://suite.test/neuro');await page.waitForURL('http://suite.test/neuro/');
   assert.equal(landings,1,'NEURO landing loop in '+locale);
   assert((await page.locator('body').innerText()).includes('SYNTHETIC NEURO MINIPAGE'));
   terminalState='failed';
   await page.goto('http://suite.test/minipage');
   await page.waitForFunction(()=>!!window.NeuroPluginUpdate?.state.last);
   assert(await page.locator('#neuro-update').isHidden(),'ready minipage showed maintenance widget in '+locale);
   await page.goto('http://suite.test/settings');
   await page.waitForFunction(()=>!!window.NeuroPluginUpdate?.state.last);
   await page.evaluate(()=>window.uiConfirmar=options=>options.aoSim());
   for(const slug of ['neuro-rt','lung-rt']){
    const panel=page.locator('[data-plugin-install="'+slug+'"]');
    assert.equal(await panel.locator('[data-pi-choice]').count(),2);
    assert.equal(await panel.locator('[data-pi-choice="zip"]').count(),0);
    await panel.locator('[data-pi-choice="folder"]').click();
    await panel.locator('[data-pi-weights-file]').setInputFiles({name:'BUNDLE.zip',mimeType:'application/zip',buffer:Buffer.from('SYNTHETIC ERROR ONLY')});
    await page.waitForFunction(({slug,text})=>document.querySelector('[data-plugin-install="'+slug+'"] [data-pi-feedback]').textContent.includes(text),{slug,text:'LOCAL_UPLOAD_TOO_LARGE'});
    if(slug==='neuro-rt')await page.waitForTimeout(1100);
    const feedback=panel.locator('[data-pi-feedback]');
    assert.equal(await feedback.count(),1);
    assert.equal(await feedback.innerText(),words[locale][errorMessage]+' · LOCAL_UPLOAD_TOO_LARGE');
    assert(!(await panel.innerText()).includes('INSTALL_FAILED'),'old error returned in '+locale);
    assert(!(await panel.innerText()).includes('SYNTHETIC OLD FAILURE'));
    assert.equal(await panel.locator('[data-pi-source]').innerText(),'');
   }
   failUpload=false;
   for(const slug of ['neuro-rt','lung-rt']){
    const panel=page.locator('[data-plugin-install="'+slug+'"]');
    await panel.locator('[data-pi-weights-file]').setInputFiles({name:'BUNDLE.zip',mimeType:'application/zip',buffer:Buffer.from('SYNTHETIC VALID RESPONSE ONLY')});
    await panel.locator('[data-pi-source][data-state="ok"]').waitFor();
    const maintenance=page.waitForResponse(response=>response.request().method()==='POST'&&new RegExp('/api/plugins/'+slug+'/(install|update)$').test(new URL(response.url()).pathname)&&response.ok());
    await panel.locator(slug==='neuro-rt'?'[data-neuro-action="comecar"]':'#lp-install').click();
    await maintenance;
   }
   assert.equal(mutations.length,2,'missing actual controller weight request in '+locale);
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),true,'mobile overflow in '+locale);
   await page.setViewportSize({width:1440,height:1000});
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),true,'desktop overflow in '+locale);
   mutations.length=0;launched.clear();expectedLocal=false;
   await page.goto('http://suite.test/settings');
   await page.waitForFunction(()=>!!window.NeuroPluginUpdate?.state.last);
   await page.evaluate(()=>window.uiConfirmar=options=>options.aoSim());
   for(const slug of ['neuro-rt','lung-rt']){
    const maintenance=page.waitForResponse(response=>response.request().method()==='POST'&&new RegExp('/api/plugins/'+slug+'/(install|update)$').test(new URL(response.url()).pathname)&&response.ok());
    await page.locator(slug==='neuro-rt'?'[data-neuro-action="comecar"]':'#lp-install').click();
    await maintenance;
   }
   await page.waitForFunction(()=>document.querySelector('#neuro-update-progress').hidden===false);
   assert.equal(await page.locator('#neuro-update-progress').getAttribute('value'),null,'handoff progress should be indeterminate');
   assert(await page.locator('#lp-install').isDisabled());
   assert.equal(mutations.length,2,'automatic weights setup did not hand off in '+locale);
   assert.deepEqual(errors,[]);
   await page.close();
  }
  console.log('PASS 12 locales: real NEURO/LUNG controllers, weights-only requests, one error after HTTP413 and poll, ready NEURO ignores old failure, responsive layout');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
