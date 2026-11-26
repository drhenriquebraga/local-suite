/* Four generated MR series traverse the real converter and a temporary delivery destination. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const cfg=JSON.parse(process.argv[2]);
const choose=(row,value)=>row.locator('[data-modo="'+value+'"]');
const checked=(row)=>row.locator('[data-modo][aria-pressed=true]').getAttribute('data-modo');
const baseSwitch=row=>row.locator('input[data-task=total_mr][role=switch]');

async function verifyTaskSheets(page, row, screenshot){
  const help=row.locator('button[data-dc-ajuda="total_mr"]');
  await help.waitFor();
  const originalMode=await checked(row);
  const originalChecks=()=>row.locator('input[data-task]').evaluateAll(ns=>ns.map(n=>[n.dataset.task,n.checked]));
  const before=await originalChecks();
  assert(!(await row.innerText()).includes('A próstata faz parte'));
  await help.focus();
  await help.press('Enter');
  const dialog=page.locator('.tk-modal-ficha').last();
  await dialog.waitFor();
  const labels=dialog.locator('[data-f="segmenta"] .tk-est span');
  await labels.first().waitFor();
  assert((await labels.count())>=30);
  assert((await labels.allTextContents()).some(n=>/prostat|próstat/i.test(n)));
  if(screenshot){
    const figure=dialog.locator('.tk-figura img').first();
    if(await figure.count())await figure.evaluate(img=>img.decode());
    const dest=path.join(path.dirname(screenshot),'10-bridge-ajuda-total-mr.png');
    await dialog.screenshot({path:dest});
    await labels.last().scrollIntoViewIfNeeded();
    await dialog.screenshot({path:path.join(path.dirname(screenshot),'11-bridge-estruturas-total-mr.png')});
  }
  await page.keyboard.press('Escape');
  await dialog.waitFor({state:'detached'});
  assert.equal(await checked(row),originalMode);
  assert.deepEqual(await originalChecks(),before);
  const inputs=await row.locator('input[data-task]').evaluateAll(ns=>ns.map(n=>n.dataset.task));
  for(const task of inputs){
    assert.equal(await row.locator('button[data-dc-ajuda="'+task+'"]').count(),1,'missing task sheet '+task);
  }
  if(originalMode==='personalizado'){
    const optional=row.locator('button[data-dc-ajuda="liver_segments_mr"]');
    await optional.click();
    const sheet=page.locator('.tk-modal-ficha').last();
    await sheet.waitFor();
    assert.equal(await sheet.locator('[data-f="segmenta"] .tk-est span').count(),8);
    await page.keyboard.press('Escape');
    await sheet.waitFor({state:'detached'});
    assert.deepEqual(await originalChecks(),before);
  }
}

async function exercise(browser, imageOnly){
  const ctx=await browser.newContext({viewport:{width:1380,height:970},locale:'pt-BR',reducedMotion:'reduce',serviceWorkers:'block'});
  const page=await ctx.newPage();
  const external=[],errors=[],convert=[],delivery=[],queue=[],guard=[];
  page.setDefaultTimeout(12000);
  page.on('pageerror',error=>errors.push(error.message));
  await page.addInitScript(()=>localStorage.setItem('radai_idioma','pt-BR'));
  await page.route('**/*',route=>{
    const req=route.request(),u=new URL(req.url()),p=u.pathname;
    if(['blob:','data:'].includes(u.protocol))return route.continue();
    if(u.origin!==cfg.origin){external.push(req.url());return route.abort();}
    if(p==='/api/bridge/etapa/converter' && req.method()==='POST')convert.push(req.postDataJSON());
    if(p==='/api/bridge/etapa/entregar' && req.method()==='POST')delivery.push(req.postDataJSON());
    // All DICOM IO is real. Capture queue traffic without starting inference on the workstation.
    if(p==='/api/bridge/fila/guardar'){guard.push(req.postDataJSON());return route.fulfill({json:{ok:true,guarda:'demo-guard'}});}
    if(['/api/fila/enfileirar','/api/bridge/fila/enfileirar','/api/bridge/fila/de_novo'].includes(p)){
      const data=req.postDataJSON();queue.push(data);
      return route.fulfill({json:{ok:true,cartoes:(data.itens || []).map((item,i)=>({id:'demo-'+i,estado:'esperando'}))}});
    }
    return route.continue();
  });
  try{
    await page.goto(cfg.origin+'/bridge/laudo');
    await page.locator('#dc_envio [data-envio=pasta]').click();
    const explorer=page.locator('.ui-fp-modal');
    await explorer.locator('[data-fp=fav]').click();
    const file=explorer.locator('.ui-fp-item[data-c]').filter({hasText:'Quatro séries de RM'});
    await file.click();
    await page.waitForFunction(folder=>document.querySelector('.ui-fp-cam')?.value===folder,cfg.mr_folder);
    await explorer.locator('[data-fp=usar]').click();
    await page.waitForFunction(()=>window.DC?.series.length===4 && !DC.varre);
    await page.locator('#dc_marcar_todas').click();
    const rows=page.locator('#dc_marcadas .dc-mrow');
    assert.equal(await rows.count(),4);
    const ids=await rows.evaluateAll(ns=>ns.map(n=>n.id.slice(4)));
    const order=await page.evaluate(ids=>ids.map(b=>DC.series.find(s=>s.bilhete===b).uid),ids);
    assert.equal(new Set(order).size,4);
    for(const row of await rows.all()){
      assert.equal(await checked(row),'nenhuma');
      assert.match(await choose(row,'nenhuma').innerText(),/imagem.*TPS/i);
    }
    for(let i=0;i<4;i++){
      const row=page.locator('#dcr_'+ids[i]);
      const mode=i%2===0?'auto':'personalizado';
      await choose(row,mode).click();
      const base=baseSwitch(row);await base.waitFor();
      assert(await base.isChecked(),'The chosen MR segmentation mode includes its base model');
      if(!imageOnly && i<2){
        if(i===1)await row.locator('[data-task=liver_segments_mr]').waitFor();
        await verifyTaskSheets(page,row,i===0 && cfg.screenshot);
      }
      if(imageOnly || i>=2) {
        if(i===1){
          const extra=row.locator('input[data-task]:not([data-task=total_mr]):not(:disabled)').first();
          if(await extra.count())await extra.check();
        }
        // Switching the base off removes this input together with its options.
        await base.click();
        assert.equal(await checked(row),'nenhuma','Removing the base must return only this row to image only');
        assert.deepEqual(await page.evaluate(b=>dcItensDaFila({series:[{b,pasta:'demonstracao',uid:'demo'}]}),ids[i]),[]);
      }
      for(let j=i+1;j<4;j++)assert.equal(await checked(rows.nth(j)),'nenhuma');
    }
    if(!imageOnly){
      if(cfg.screenshot)await page.locator('#dc_marcadas').screenshot({path:cfg.screenshot});
    }else{
      assert.equal(await rows.locator('[data-modo=nenhuma][aria-pressed=true]').count(),4);
      const idx=await page.evaluate(b=>DC.series.findIndex(s=>s.bilhete===b),ids[1]);
      const card=page.locator('#dcs'+idx);
      await card.press('Space');
      await page.locator('#dcr_'+ids[1]).waitFor({state:'detached'});
      await card.press('Space');
      assert.equal(await checked(page.locator('#dcr_'+ids[1])),'nenhuma','Reselecting keeps the edit');
      if(cfg.screenshot){
        const ext=path.extname(cfg.screenshot);
        await page.locator('#dc_e2').screenshot({path:cfg.screenshot.slice(0,-ext.length)+'-somente-imagens'+ext});
      }
    }
    // Go through the standard read, convert and deliver buttons (no direct POST).
    await page.locator('#dc_avancar').click();
    await page.locator('#dc_converter').click();
    await page.waitForFunction(()=>!!window.DC?.conversao && DC.exportadas.length===4,{},{timeout:45000});
    await page.locator('#dc_entregar').click();
    await page.waitForFunction(()=>window.DC?.entregue?.series?.length===4,{},{timeout:30000});
    const delivered=await page.evaluate(()=>({name:DC.entregue.nome,references:DC.entregue.series.map(x=>({source:x.b,uid:x.uid})),
      items:dcItensDaFila(DC.entregue),cards:DC.filas.length}));
    assert.equal(convert.length,1);assert.equal(delivery.length,1);
    assert.deepEqual(convert[0].series.map(s=>s.b).sort(),[...ids].sort());
    assert.deepEqual(delivery[0].destinos,[cfg.destination]);
    assert.deepEqual(delivered.references.map(s=>s.source).sort(),[...ids].sort());
    assert.equal(new Set(delivered.references.map(s=>s.uid)).size,4);
    const dest=path.join(cfg.destination,delivered.name);
    const seriesDirs=fs.readdirSync(dest,{withFileTypes:true}).filter(d=>d.isDirectory());
    assert.equal(seriesDirs.length,4);
    for (const d of seriesDirs) assert(fs.readdirSync(path.join(dest,d.name)).length>=6);
    if(imageOnly){
      assert.deepEqual(delivered.items,[]);assert.equal(delivered.cards,0);
      assert.equal(queue.length,0);assert.equal(guard.length,0);
    }else{
      await page.waitForFunction(()=>DC.filas.some(f=>f.cartoes && f.cartoes.length>0));
      assert.equal(queue.length,1);assert.equal(guard.length,1);
      const payload=queue[0].itens;
      const deliveredUid=b=>delivered.references.find(s=>s.source===b).uid;
      assert.deepEqual(payload.map(x=>x.uid).sort(),ids.slice(0,2).map(deliveredUid).sort());
      assert.deepEqual(payload.map(x=>x.modo),['auto','personalizado']);
      assert(payload.every(x=>x.chaves?.total_mr===1 && x.modalidade==='MR'));
      assert(payload.every(x=>!ids.slice(2).map(deliveredUid).includes(x.uid)));
      assert.deepEqual(guard[0].itens,payload);
    }
    assert.deepEqual(external,[]);assert.deepEqual(errors,[]);
    console.log(JSON.stringify({scenario:imageOnly?'image_only':'independent_modes',converted:4,delivered:4,
      queued:delivered.items.length,modes:delivered.items.map(x=>x.modo),queueRequests:queue.length,guardRequests:guard.length}));
  }finally{await ctx.close();}
}
(async()=>{
  const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_EXECUTABLE});
  try{await exercise(browser,true);await exercise(browser,false);}finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
