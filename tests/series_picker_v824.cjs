const assert=require('node:assert/strict');
const fs=require('node:fs');
const {chromium}=require(process.env.NEURO_PLAYWRIGHT_MODULE);
(async()=>{
 const fixture=JSON.parse(fs.readFileSync(process.env.PICKER_FIXTURE,'utf8'));
 const browser=await chromium.launch({executablePath:process.env.CHROME_EXECUTABLE||'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1280,height:900},reducedMotion:'reduce'}),errors=[],folders=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',async route=>{
   const url=new URL(route.request().url());
   if(url.pathname==='/fixture')return route.fulfill({contentType:'text/html',body:fixture.html});
   if(url.pathname==='/radai-idiomas.js')return route.fulfill({contentType:'application/javascript',body:fixture.languages});
   if(url.pathname==='/api/lote/pastas'){
    const request=route.request().postDataJSON();folders.push(request);
    const dirs=[{nome:'OLD',caminho:'C:/SYNTHETIC/OLD',data:'2026-11-01 10:00'},
                {nome:'NEW',caminho:'C:/SYNTHETIC/NEW',data:'2026-11-13 10:00'}];
    dirs.sort((a,b)=>(request.ordem==='data'?a.data.localeCompare(b.data):a.nome.localeCompare(b.nome))*(request.sentido==='desc'?-1:1));
    return route.fulfill({json:{unidades:[{raiz:'C:/',tipo:'fixa',ok:true}],caminho:request.caminho||'',pai:'C:/',pastas:dirs}});
   }
   return route.fulfill({json:{}});
  });
  await page.goto('http://127.0.0.1:49199/fixture');
  await page.evaluate(()=>pick.abrir());
  await page.locator('#pick_procurar').click();
  await page.waitForFunction(()=>document.querySelector('.ui-fp-cam')?.value==='C:/SYNTHETIC');
  assert.equal(await page.locator('.ui-fp-ord [data-ord=data]').getAttribute('aria-pressed'),'true');
  assert.equal(await page.locator('.ui-fp-ord [data-ord=data]').getAttribute('data-sentido'),'desc');
  assert.equal(await page.locator('.ui-fp-item[data-c]').first().getAttribute('data-c'),'C:/SYNTHETIC/NEW');
  await page.locator('.ui-fp [data-fp=usar]').click();
  await page.waitForFunction(()=>demo.finished.length===1);
  assert.equal(await page.evaluate(()=>demo.starts),1,'one folder choice must start exactly one scan');
  assert.equal(await page.evaluate(()=>demo.finished[0].ctx.pasta),'C:/SYNTHETIC');
  assert.equal(await page.locator('#pick_form button[type=submit]').count(),0,'redundant scan button');
  await page.locator('#pick_pasta').fill('C:/MANUAL');
  await page.locator('#pick_pasta').press('Enter');
  await page.waitForFunction(()=>demo.finished.length===2);
  assert.equal(await page.evaluate(()=>demo.starts),2,'Enter must start once');
  assert.equal(await page.evaluate(()=>demo.finished[1].ctx.pasta),'C:/MANUAL');
  await page.locator('#pick_procurar').click();
  await page.locator('.ui-fp [data-fp=cancelar]').click();
  assert.equal(await page.evaluate(()=>demo.starts),2,'cancel is not a choice');
  await page.locator('[data-ui-fav=pick_pasta]').click();
  await page.waitForFunction(()=>demo.finished.length===3);
  assert.equal(await page.evaluate(()=>demo.starts),3,'favorite must start once');
  await page.evaluate(()=>{demo.mode='slow';pick.varrer();pick.fechar();});
  await page.waitForFunction(()=>demo.stops.length>=1);
  await page.waitForTimeout(200);
  assert.equal(await page.evaluate(()=>demo.finished.length),3,'late scan must not reopen or select');
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({passed:true,scans:3,newestDefault:true,manualEnter:true,cancelledLateResultIgnored:true}));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
