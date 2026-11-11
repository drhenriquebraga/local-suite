const fs=require('fs'),assert=require('assert');
const {chromium}=require(process.argv[3]);
const root=process.argv[2], expected=JSON.parse(fs.readFileSync(root+'/expected.json','utf8'));
const codeTitle='Instalar / atualizar apenas o código offline';
const weightsTitle='Instalar / atualizar o pacote de pesos offline';
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.argv[4]});
 try{
  for(const locale of Object.keys(expected)){
   const page=await browser.newPage({viewport:{width:390,height:900},reducedMotion:'reduce'});
   const errors=[],uploads=[];let uploadError=null;page.on('pageerror',e=>errors.push(String(e)));
   await page.addInitScript(code=>localStorage.setItem('radai_idioma',code),locale);
   await page.addInitScript(()=>{
    const send=XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.send=function(body){
     if(body instanceof Blob){const target=this.upload;setTimeout(()=>target.dispatchEvent(new ProgressEvent('progress',{
       lengthComputable:true,loaded:Math.max(1,Math.floor(body.size/2)),total:body.size
     })),30);}
     return send.call(this,body);
    };
   });
   await page.route('http://suite.test/**',async route=>{
    const req=route.request(),url=new URL(req.url());
    if(url.pathname==='/config')return route.fulfill({contentType:'text/html',body:fs.readFileSync(root+'/config.html','utf8')});
    if(url.pathname==='/radai-idiomas.js')return route.fulfill({contentType:'application/javascript',body:fs.readFileSync(root+'/languages.js','utf8')});
    if(req.resourceType()==='script')return route.fulfill({contentType:'application/javascript',body:'/* synthetic shared shell dependency */'});
    if(!url.pathname.startsWith('/api/plugins/'))return route.fulfill({json:{}});
    const slug=url.pathname.includes('neuro-rt')?'neuro-rt':'lung-rt';
    const version=slug==='neuro-rt'?'1.3.3':'1.1.3';
    if(req.method()==='GET')return route.fulfill({json:{token:'SYNTHETIC_TOKEN',version,code_version:version,weights:{version:slug==='neuro-rt'?'1.3.0':null,state:slug==='neuro-rt'?'partial':'missing'}}});
    if(url.pathname.endsWith('/connectivity'))return route.fulfill({json:{github:{status:'unavailable',code:'HTTP_403'},mirror:{status:'available',version,code:'OK'}}});
    if(url.pathname.endsWith('/local/upload')){
      assert.equal(req.headers()['content-type'],'application/zip');
      assert.equal(req.headers()[slug==='neuro-rt'?'x-neuro-plugin-token':'x-lung-plugin-token'],'SYNTHETIC_TOKEN');
      const operation=url.searchParams.get('operation');assert.equal(operation,'weights');
      uploads.push({slug,operation});
      await new Promise(resolve=>setTimeout(resolve,100));
      if(uploadError)return route.fulfill({status:400,json:{detail:uploadError}});
      return route.fulfill({json:{source_id:'SYNTHETIC_'+operation,version:operation==='weights'?'1.3.0':version,format:operation==='weights'?'offline_bundle':'setup_zip'}});
    }
    return route.fulfill({json:{}});
   });
   await page.goto('http://suite.test/config');await page.waitForFunction(()=>window.testReady);
   const words=expected[locale];
   const translated=await page.evaluate(texts=>Object.fromEntries(texts.map(text=>[text,window.radaiFrase(text)])),Object.keys(words));
   assert.deepEqual(translated,words,'shared code/weights and error translations in '+locale);
   for(const slug of ['neuro-rt','lung-rt']){
    const panel=page.locator('[data-plugin-install="'+slug+'"]');
    assert.equal(await panel.locator('[data-pi-choice="zip"]').count(),0);
    assert.equal(await panel.locator('[data-pi-choice="folder"] strong').textContent(),words[weightsTitle]);
    assert.equal(await panel.locator('[data-pi-file]').count(),0);
    assert.equal(await panel.locator('[data-pi-weights-file]').getAttribute('accept'),'.zip,application/zip');
    assert.equal(await panel.locator('[data-pi-code-version]').textContent(),slug==='neuro-rt'?'1.3.3':'1.1.3');
    assert.equal(await panel.locator('[data-pi-weights-version]').textContent(),slug==='neuro-rt'?'1.3.0':words['Ainda não instalado']);
    await panel.locator('[data-pi-probe]').click();
    await panel.locator('[data-pi-channel="mirror"][data-state="ok"]').waitFor();
    assert((await panel.locator('[data-pi-channel="mirror"]').textContent()).includes(words['Disponível']));
    await panel.locator('[data-pi-choice="folder"]').click();
    await panel.locator('[data-pi-weights-file]').setInputFiles({name:'WEIGHTS_BUNDLE.zip',mimeType:'application/zip',buffer:Buffer.from('SYNTHETIC ZIP ONLY')});
    await page.waitForFunction(s=>window.testAccepted[s]?.id==='SYNTHETIC_weights',slug);
    assert.equal(await page.evaluate(s=>window.testPanels[s].operation(),slug),'weights');
    await panel.locator('[data-pi-weights-drop]').evaluate(element=>{
      const data=new DataTransfer();data.items.add(new File(['SYNTHETIC WEIGHTS ONLY'],'WEIGHTS_BUNDLE.zip',{type:'application/zip'}));
      element.dispatchEvent(new DragEvent('drop',{bubbles:true,dataTransfer:data}));
    });
    await page.waitForFunction(s=>window.testAccepted[s]?.id==='SYNTHETIC_weights',slug);
    assert.equal(await page.evaluate(s=>window.testPanels[s].operation(),slug),'weights');
    assert.equal(await panel.locator('[data-pi-code-version]').textContent(),slug==='neuro-rt'?'1.3.3':'1.1.3');
    await page.evaluate(s=>window.testPanels[s].versions({code_version:'9.0',weights:{state:'ready'}}),slug);
    assert.equal(await panel.locator('[data-pi-code-version]').textContent(),'9.0');
    assert.equal(await panel.locator('[data-pi-weights-version]').textContent(),words['Instalado · versão não registrada']);
    assert.equal(await panel.locator('[data-pi-weights-state]').textContent(),words['Pesos prontos']);
    const before=uploads.length;
    await panel.locator('[data-pi-weights-file]').setInputFiles({name:'NOT_A_ZIP.txt',mimeType:'text/plain',buffer:Buffer.from('SYNTHETIC INVALID FILE')});
    await panel.locator('[data-pi-feedback]:visible').waitFor();
    assert.equal(await panel.locator('[data-pi-feedback]').textContent(),words['Escolha um único arquivo ZIP.']);
    assert.equal(uploads.length,before);
   }
   assert.equal(uploads.length,4);
   assert((await page.evaluate(()=>window.testNotice)).some(text=>text.startsWith(words['Enviando ZIP local…'])),'XHR upload progress missing in '+locale);
   const panel=page.locator('[data-plugin-install="lung-rt"]');
   for(const detail of [
     'Não há espaço livre suficiente para copiar o ZIP local.',
     {code:'CODE_DOWNGRADE_BLOCKED',message:'O código deste pacote é mais antigo. Use o pacote de pesos offline ou um SETUP atualizado.'}
   ]){
    uploadError=detail;
    await panel.locator('[data-pi-weights-file]').setInputFiles({name:'ERROR_FIXTURE.zip',mimeType:'application/zip',buffer:Buffer.from('SYNTHETIC ERROR RESPONSE')});
    await panel.locator('[data-pi-feedback]:visible').waitFor();
    const message=typeof detail==='string'?detail:detail.message;
    assert.equal(await panel.locator('[data-pi-feedback]').textContent(),words[message]+' · '+(typeof detail==='string'?'HTTP 400':detail.code));
    await page.evaluate(()=>window.testPanels['lung-rt'].result({error_code:'INSTALL_FAILED',message:'SYNTHETIC OLD FAILURE'}));
    assert(!(await panel.innerText()).includes('SYNTHETIC OLD FAILURE'));
   }
   uploadError=null;
   for(const [phase,label] of [['RESOURCES','Preparando recursos'],['DOWNLOAD','Baixando componentes']]){
    await page.evaluate(({phase})=>{
      window.testPanels['lung-rt'].clearFailure();
      window.testPanels['lung-rt'].result({error_code:'DOWNLOAD_FAILED',error_phase:phase,error_component:'medgemma-model',error_reason:'HTTP_403'});
    },{phase});
    const text=await panel.locator('[data-pi-feedback]').innerText();
    assert(text.includes(words[label]),'uppercase worker phase not translated in '+locale);
    assert(text.includes('DOWNLOAD_FAILED')&&text.includes('medgemma-model')&&text.includes('HTTP_403'));
   }
   assert.equal(await page.locator('.pi-terms').count(),0);
   assert(!(await page.locator('body').innerText()).includes('SYNTHETIC LUNG TERMS'));
   await page.locator('#open-test-terms').click();
   const modal=page.locator('.ui-modal');await modal.waitFor();
   assert((await modal.textContent()).includes('SYNTHETIC LUNG TERMS'));
   const accept=modal.locator('.pi-actions .pri');assert(await accept.isDisabled());
   await modal.locator('input[type=checkbox]').check();assert(!(await accept.isDisabled()));
   assert.equal(await accept.textContent(),words['Instalar ou atualizar %s'].replace('%s','LUNG RT'));
   await accept.click();await page.waitForFunction(()=>window.testConsentResult===true);
   await page.waitForFunction(()=>!document.querySelector('.ui-modal'));
   assert.equal(await page.locator('.pi-terms').count(),0);
   await page.locator('#open-test-accepted').click();
   await page.locator('#ui-pnl-veu.vis').waitFor();
   assert(!(await page.textContent('#ui-pnl-veu')).includes('SYNTHETIC LUNG TERMS'));
   await page.keyboard.press('Escape');
   await page.waitForFunction(()=>window.testConsentResult===false);
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),true,'horizontal overflow in '+locale);
   assert.deepEqual(errors,[]);
   await page.close();
  }
  console.log('PASS 12 locales: code/weights ZIP uploads, drag/drop, synthetic XHR progress, independent versions, no inline terms, consent modal, mobile layout');
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exitCode=1});
