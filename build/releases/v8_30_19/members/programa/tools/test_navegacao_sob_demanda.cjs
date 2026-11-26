/* Browser regression with fictitious Windows paths. Every HTTP request is intercepted. */
const assert = require('node:assert/strict');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

function scripts(root) {
  const extract = [
    'import ast, json, pathlib, sys',
    'def literal(file,name):',
    ' for n in ast.parse((pathlib.Path(sys.argv[1])/file).read_bytes()).body:',
    '  if isinstance(n, ast.Assign) and any(isinstance(k, ast.Name) and k.id==name for k in n.targets): return ast.literal_eval(n.value)',
    ' raise KeyError(name)',
    "print(json.dumps([literal('radai_ui.py','COMPONENTES_JS'),literal('radai_batch.py','JS_VIGIA')]))"
  ].join('\n');
  return JSON.parse(execFileSync(process.env.PYTHON || 'python',['-c',extract,root],{encoding:'utf8'}));
}

async function run(browser, root, legacy) {
  const [selectors,overnight] = scripts(root);
  const slice = overnight.slice(0,overnight.indexOf('function _ovCard('));
  const ctx = await browser.newContext({serviceWorkers:'block'});
  const page = await ctx.newPage();
  page.setDefaultTimeout(3500);
  const seen = [], holds = [];
  const favorite='Z:/favorita', start='Y:/anterior', offline='Z:/offline', slow='Z:/lenta';
  let failFavorite=false;
  const response=(route,data)=>route.fulfill({json:data});
  await page.route('**/*',async route=>{
    const req=route.request(),url=new URL(req.url());
    if(url.origin!=='http://suite.invalid')throw Error('Unexpected origin: '+url.origin);
    if(url.pathname==='/')return route.fulfill({contentType:'text/html',body:'<!doctype html><body><button id="origem">Abrir</button>'+selectors+'<script>'+slice+'</script></body>'});
    const body=req.postData()?JSON.parse(req.postData()):{};
    seen.push({url:url.pathname,body});
    if(url.pathname==='/api/lote/favorita')return failFavorite?route.fulfill({status:503,body:'unavailable'}):response(route,{favorita:favorite});
    if(url.pathname==='/api/lote/pastas'){
      if(body.unidades)return response(route,{unidades:[{raiz:'Z:/'}]});
      if(body.caminho===offline)return response(route,{erro:'Tempo esgotado',codigo:'tempo_esgotado',pastas:[]});
      if(body.caminho===slow){ holds.push(route);return }
      return response(route,{caminho:body.caminho,pai:'Z:/',pastas:[]});
    }
    if(url.pathname==='/api/lote/conferir_pasta')return response(route,{existe:true,leitura:true});
    if(url.pathname==='/api/config')return response(route,{valores:{ROOT:favorite,ROOTS:JSON.stringify([favorite,slow])}});
    return response(route,{});
  });
  await page.addInitScript(()=>{
    const original=window.fetch.bind(window);
    window.aborted=[];
    window.fetch=(url,opts)=>{
      if(opts?.signal)opts.signal.addEventListener('abort',()=>window.aborted.push(opts.body),{once:true});
      return original(url,opts);
    };
  });
  try {
    await page.goto('http://suite.invalid/');
    const dialog=page.locator('.ui-fp-modal');
    const reads=()=>seen.filter(x=>x.url==='/api/lote/pastas' && x.body.caminho).map(x=>x.body.caminho);
    const settle=()=>page.waitForTimeout(90);
    async function open(initial) {
      await page.evaluate(initial=>uiExplorador({inicial:initial,aoUsar:p=>window.chosen=p}),initial);
      await dialog.locator('.ui-fp-nm').waitFor();
      await settle();
    }
    async function close() {
      await dialog.locator('[data-fp=cancelar]').click();
      await dialog.waitFor({state:'detached'});
    }
    const initialReads=[];
    for(const initial of [start,favorite,'',favorite]){
      failFavorite=initialReads.length===3;
      const first=reads().length;
      await open(initial);
      initialReads.push(reads().slice(first));
      await close();
    }
    failFavorite=false;
    if(!legacy)assert.deepEqual(initialReads,[[],[],[],[]]);
    console.log(JSON.stringify({root,initialReads}));
    if(legacy)return;
    await open(start);
    assert.equal(await dialog.locator('[data-fp=usar]').isEnabled(),true);
    await dialog.locator('[data-fp=fav]').click();
    await dialog.locator('[data-fp=usar]:enabled').waitFor();
    assert.deepEqual(reads(),[favorite]);
    const input=dialog.locator('.ui-fp-cam');
    await input.fill(offline);
    await input.press('Enter');
    await dialog.locator('.ui-fp-msg button').waitFor();
    assert.match(await dialog.locator('.ui-fp-msg').innerText(),/Tempo esgotado/);
    assert.doesNotMatch(await dialog.innerText(),/nenhuma subpasta aqui/);
    assert.equal(await dialog.locator('[data-fp=usar]').isDisabled(),true);
    await dialog.locator('.ui-fp-msg button').click();
    await dialog.locator('.ui-fp-msg button').waitFor();
    await dialog.locator('[data-fp=volta]').click();
    await dialog.locator('[data-fp=usar]:enabled').waitFor();
    await dialog.locator('[data-fp=usar]').click();
    await dialog.waitFor({state:'detached'});
    assert.equal(await page.evaluate(()=>window.chosen),favorite);
    assert.deepEqual(reads(),[favorite,offline,offline,favorite]);
    for (const hidden of [false,true]){
      const beforeAbort=await page.evaluate(s=>window.aborted.filter(b=>b && b.includes(s)).length,slow);
      await open(slow);
      await input.press('Enter');
      await page.waitForTimeout(100);
      if(hidden)await page.evaluate(()=>{Object.defineProperty(document,'hidden',{configurable:true,value:true});document.dispatchEvent(new Event('visibilitychange'))});
      else await dialog.locator('[data-fp=cancelar]').click();
      await dialog.waitFor({state:'detached'});
      assert.equal(await page.evaluate(s=>window.aborted.filter(b=>b && b.includes(s)).length,slow),beforeAbort+1);
      if(hidden)await page.evaluate(()=>{delete document.hidden;document.dispatchEvent(new Event('visibilitychange'))});
    }
    assert.equal(holds.length,2);
    for(const route of holds)await route.abort().catch(()=>{});
    await open(start);
    await dialog.locator('[data-fp=usar]').click();
    await dialog.waitFor({state:'detached'});
    assert.equal(await page.evaluate(()=>window.chosen),start);
    const before=seen.length;
    await page.evaluate(()=>{
      document.body.insertAdjacentHTML('beforeend','<div class="ui-pnl-veu"><div class="ui-pnl"><div id="ov_roots"><input id="ov_root" data-ov-root></div><div id="ov_root_laudo"></div><button id="ov_testar"></button><button id="ui-pnl-sim"></button></div></div>');
      window.uiTexto=(el,txt)=>{el.textContent=txt}; _ovLigar(); _ovPreencher();
    });
    await page.locator('#ov_roots input').nth(1).waitFor();
    const field=page.locator('#ov_roots input').nth(1);
    await field.fill('Y:/escolhida');
    await page.waitForTimeout(600);
    const validations=()=>seen.slice(before).filter(x=>x.url==='/api/lote/conferir_pasta').map(x=>x.body.caminho);
    assert.deepEqual(validations(),[]);
    await page.locator('#ov_testar').click();
    await page.waitForFunction(()=>window.OV?.laudo?.leitura===true);
    assert.deepEqual(validations(),[favorite,'Y:/escolhida']);
    console.log(JSON.stringify({manual:reads(),explicitOvernight:validations(),aborted:holds.length}));
  } finally { await ctx.close() }
}
(async()=>{
  const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_EXECUTABLE});
  try{
    if(process.argv[2])await run(browser,process.argv[2],true);
    await run(browser,path.resolve(__dirname,'../app'),false);
  }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
