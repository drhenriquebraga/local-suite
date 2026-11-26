/* Isolated browser lifecycle regression. CSS metrics use 2.6 s of real foreground rendering. */
const assert = require('node:assert/strict');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

function program(root) {
  const load = "import sys,json;sys.path.insert(0,sys.argv[1]);import radai_pulso as p,radai_janela as j,radai_ui as u;print(json.dumps([p.SCRIPT,j.JS,u.CONTROLES+u.TRANSICOES]))";
  return JSON.parse(execFileSync(process.env.PYTHON || 'python',['-B','-c',load,root],{encoding:'utf8'}));
}
async function measure(browser, root, legacy) {
  const [pulse,win,css]=program(root);
  const page=await browser.newPage();
  try {
    const html='<title>Demo</title><details data-radai-maximizar><summary>Janela</summary><button data-radai-maximizar-acao></button></details>'+pulse+win;
    await page.route('**/*',r=>r.fulfill({contentType:'text/html',body:html}));
    await page.clock.install();
    await page.addInitScript(()=>{
      window.hits=[];
      window.XMLHttpRequest=class {
        open(method,url){this.url=url} setRequestHeader(){} send(){hits.push(this.url);this.onloadend?.()}
        abort(){this.onloadend?.()}
      };
      window.fetch=async url=>{hits.push(url);return {ok:true,json:async()=>({ok:true,pid:17,tela_cheia:false})}};
    });
    await page.goto('http://suite.invalid/');
    const count=route=>page.evaluate(route=>hits.filter(x=>x===route).length,route);
    const post='/api/pulso',state='/api/janela/tela-cheia/estado';
    const initial=await count(post);
    await page.clock.runFor(60000);
    const visible=await count(post)-initial;
    await page.evaluate(()=>{Object.defineProperty(document,'hidden',{value:true,configurable:true});document.dispatchEvent(new Event('visibilitychange'))});
    const start=await count(post);
    await page.clock.runFor(60000);
    const hidden=await count(post)-start;
    await page.evaluate(()=>{delete document.hidden; document.dispatchEvent(new Event('visibilitychange'));window.radaiJanelaDoApp=true});
    for(let i=0;i<5;i++){
      await page.evaluate(()=>{dispatchEvent(new Event('focus'));dispatchEvent(new Event('resize'))});
      await page.clock.runFor(500);
    }
    const nativeIdle=await count(state);
    await page.evaluate(()=>document.querySelector('details').open=true);
    await page.clock.runFor(650);
    const nativeMenu=await count(state)-nativeIdle;
    if(!legacy){
      assert.equal(visible,4); assert.equal(hidden,1);
      assert.equal(nativeIdle,0); assert.equal(nativeMenu,1);
    }
    console.log(JSON.stringify({root,visiblePerMinute:visible,hiddenPerMinute:hidden,nativeIdle,nativeMenu}));
  } finally {await page.close()}
  if(!legacy){
    for(const reducedMotion of ['no-preference','reduce']){
      const p=await browser.newPage({reducedMotion});
      try{
        await p.setContent('<style>'+css+'</style><button class="pri">Rodar</button>');
        const cdp=await p.context().newCDPSession(p);
        await cdp.send('Performance.enable');
        const get=async()=>Object.fromEntries((await cdp.send('Performance.getMetrics')).metrics.map(m=>[m.name,m.value]));
        const first=await get();await p.waitForTimeout(2600);const last=await get();
        console.log(JSON.stringify({css:reducedMotion,periodMs:2600,layouts:last.LayoutCount-first.LayoutCount,recalc:last.RecalcStyleCount-first.RecalcStyleCount,taskMs:Math.round(1000*(last.TaskDuration-first.TaskDuration))}));
      }finally{await p.close()}
    }
  }
}
(async()=>{
  const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_EXECUTABLE});
  try{
    if(process.argv[2])await measure(browser,process.argv[2],true);
    await measure(browser,path.resolve(__dirname,'../app'),false);
  }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
