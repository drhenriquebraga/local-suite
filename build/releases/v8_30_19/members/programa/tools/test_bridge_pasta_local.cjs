/* Called by test_bridge_pasta_local.py with synthetic series and a real loopback API. */
const assert = require('node:assert/strict');
const path = require('node:path');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const cfg=JSON.parse(process.argv[2]);

(async()=>{
  const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_EXECUTABLE});
  try {
    const summary=[];
    for (const [lang,kind] of [['pt-BR','folder'],['en','folder'],['es','folder'],['pt-BR','file'],['pt-BR','zip']]) {
      const ctx=await browser.newContext({viewport:{width:1380,height:920},locale:lang,reducedMotion:'reduce',serviceWorkers:'block'});
      const page=await ctx.newPage();
      page.setDefaultTimeout(10000);
      const requests=[],outside=[],errors=[];
      let choosers=0;
      page.on('pageerror',err=>errors.push(err.message));
      page.on('filechooser',()=>{choosers++;});
      await page.route('**/*',route=>{
        const req=route.request(),u=new URL(req.url());
        if(u.protocol==='data:' || u.protocol==='blob:')return route.continue();
        if(u.origin!==cfg.origin){outside.push(req.url());return route.abort();}
        requests.push({path:u.pathname,method:req.method(),body:u.pathname==='/api/varrer/iniciar'?req.postDataJSON():null});
        return route.continue();
      });
      try {
        await page.addInitScript(locale=>localStorage.setItem('radai_idioma',locale),lang);
        await page.goto(cfg.origin+'/bridge/laudo');
        const drop=page.locator('#dc_envio');
        await drop.waitFor();
        assert.equal(await drop.locator('input[webkitdirectory]').count(),0);
        const entry=drop.locator('[data-envio=pasta]');
        const expected=await page.evaluate(()=>window.radaiFrase('Escolher pasta'));
        if(lang!=='pt-BR')assert.notEqual(expected,'Escolher pasta',lang+' folder translation');
        assert.equal((await entry.innerText()).trim(),expected);
        if(kind==='folder'){
          await entry.click();
          const modal=page.locator('.ui-fp-modal');
          await modal.waitFor();
          const title=await modal.locator('.ui-modal-tit').innerText();
          if(lang!=='pt-BR')assert.notEqual(title,'Escolher a pasta',lang+' modal translation');
          await modal.locator('[data-fp=fav]').click();
          const exam=modal.locator('.ui-fp-item[data-c]').filter({hasText:'TC de demonstração'});
          await exam.waitFor().catch(async err=>{throw Error(err.message+' '+await modal.locator('.ui-fp-msg').innerText()+' '+await modal.locator('.ui-fp-lista').innerText());});
          if(cfg.screenshot && lang==='pt-BR')await modal.screenshot({path:cfg.screenshot});
          await exam.click();
          await page.waitForFunction(folder=>document.querySelector('.ui-fp-cam')?.value===folder,cfg.folder);
          await modal.locator('[data-fp=usar]').click();
          await modal.waitFor({state:'hidden'});
        }else{
          const event=page.waitForEvent('filechooser');
          await drop.locator('[data-envio=arquivos]').click();
          await (await event).setFiles(cfg[kind]);
        }
        await page.waitForFunction(()=>Array.isArray(window.DC?.series) && DC.series.length>0);
        const scanned=requests.filter(r=>r.path==='/api/varrer/iniciar');
        const intake=requests.filter(r=>r.path.startsWith('/api/bridge/receber'));
        assert.equal(scanned.length,1,lang+' '+kind+' scan count');
        assert.equal(scanned[0].body.uso,'bridge');
        const series=await page.evaluate(()=>DC.series.map(s=>s.descricao || s.desc || s.nome || ''));
        if(kind==='folder'){
          assert.equal(path.resolve(scanned[0].body.pasta),path.resolve(cfg.folder));
          await page.locator('#dc_marcar_todas').click();
          const row=page.locator('#dc_marcadas .dc-mrow').first();
          await row.locator('[data-modo=auto]').click();
          const base=row.locator('button[data-dc-ajuda=total_v3]');
          await base.click();
          const sheet=page.locator('.tk-modal-ficha');
          await sheet.waitFor();
          assert.equal(await sheet.locator('[data-f=segmenta] .tk-est span').count(),117);
          await page.keyboard.press('Escape');
          await sheet.waitFor({state:'detached'});
          const details=row.locator('details.dc-catalogo-auto');
          await details.locator('summary').click();
          assert(await details.locator('button[data-dc-ajuda]').count()>1);
          await details.locator('button[data-dc-ajuda]').first().click();
          await sheet.waitFor();
          assert(await sheet.locator('[data-f=segmenta] .tk-est span').count()>0);
          await page.keyboard.press('Escape');
          await sheet.waitFor({state:'detached'});
          assert.equal(await row.locator('[data-modo=auto]').getAttribute('aria-pressed'),'true');
          assert.equal(choosers,0);
          assert.equal(intake.length,0);
          assert(series.some(value=>value.includes('TC SINTETICA BRIDGE')),JSON.stringify(series));
        }else{
          assert.equal(choosers,1);
          assert(intake.some(r=>r.path==='/api/bridge/receber' && r.method==='POST'));
          assert(intake.some(r=>r.path==='/api/bridge/receber/fim' && r.method==='POST'));
          if(kind==='zip')assert(series.some(value=>value.includes('TC SINTETICA BRIDGE')),JSON.stringify(series));
        }
        assert.deepEqual(outside,[]);
        assert.deepEqual(errors,[]);
        summary.push({language:lang,source:kind,filechoosers:choosers,localIntakeRequests:intake.length,series:series.length,externalRequests:outside.length});
      }finally{await ctx.close();}
    }
    console.log(JSON.stringify(summary,null,2));
  }finally{await browser.close();}
})().catch(err=>{console.error(err);process.exitCode=1;});
