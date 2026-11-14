const fs=require('fs'),assert=require('node:assert/strict');
const {chromium}=require(process.env.NEURO_PLAYWRIGHT_MODULE||'playwright');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.NEURO_BROWSER_EXECUTABLE||'C:/Program Files/Google/Chrome/Application/chrome.exe'});
 try{
  const page=await browser.newPage();
  await page.route('http://weights.test/**',r=>r.fulfill({contentType:'text/html',body:fs.readFileSync(process.env.WEIGHTS_CHECK_HTML,'utf8')}));
  await page.goto('http://weights.test/');
  await page.evaluate(()=>{
   const panel=document.getElementById('neuro-update');
   window.checker=RadaiPluginSetup.bind(panel,{status:async()=>({token:'test'}),lock(){},reset(){},accept(){},isLocked:()=>false});
   window.reads=0;
   document.getElementById('neuro-release-refresh').onclick=()=>checker.checkWeights(async()=>{
    window.reads++;await new Promise(r=>setTimeout(r,200));if(window.fail)throw Error('offline');
    return window.answer;
   }).catch(()=>{});
  });
  const button=page.locator('#neuro-release-refresh'),status=page.locator('[data-pi-weight-check]');
  await page.evaluate(()=>window.answer={code_version:'1.3.9',weights:{state:'ready',version:'1.3.0'}});
  await button.click();await status.locator('progress').waitFor();assert(await button.isDisabled());
  assert.equal(await status.getAttribute('aria-busy'),'true');
  await page.evaluate(()=>document.getElementById('neuro-release-refresh').click());
  await page.waitForFunction(()=>document.querySelector('[data-pi-weight-check]').dataset.state==='ok');
  assert.equal(await page.evaluate(()=>reads),1);assert.match(await status.innerText(),/Pesos prontos.*1\.3\.0/);
  assert.equal(await page.locator('[data-pi-code-version]').innerText(),'1.3.9');
  assert.equal(await page.locator('[data-pi-weights-version]').innerText(),'1.3.0');assert(await button.isEnabled());
  await page.evaluate(()=>window.answer={code_version:'1.3.9',weights:{state:'missing'}});await button.click();
  await page.waitForFunction(()=>document.querySelector('[data-pi-weight-check]').dataset.state==='missing');
  assert.match(await status.innerText(),/Pacote de pesos ainda não instalado/);
  await page.evaluate(()=>window.fail=true);await button.click();
  await page.waitForFunction(()=>document.querySelector('[data-pi-weight-check]').dataset.state==='error');
  assert.match(await status.innerText(),/Não foi possível conferir/);assert(await button.isEnabled());
  assert.equal(await status.getAttribute('aria-busy'),'false');assert.equal(await status.locator('progress').count(),0);
  console.log('PASS: visible checking, single flight, distinct code/bundle versions, missing weights, failed check and restored button.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
