(() => {
  'use strict';
  if (window.radaiGuiaAbrir) return;
  const tabKey = 'suite.guia.aba';
  const courseKey = 'suite.guia.passo';
  const read = key => { try { return sessionStorage.getItem(key); } catch { return null; } };
  function keep(key, value) {
    try { if (value === null) sessionStorage.removeItem(key); else sessionStorage.setItem(key, value); } catch {}
  }
  const aba = read(tabKey) || (globalThis.crypto?.randomUUID?.() || Date.now() + '-' + Math.random());
  keep(tabKey, aba);
  let catalog, panel, target, previousFocus, starting = false;
  let loading;
  function dataset() {
    if (!loading) {
      let lang = document.documentElement.lang;
      try { lang = localStorage.getItem('radai_idioma') || lang; } catch {}
      loading = fetch('/api/roteiro/interface?idioma=' + encodeURIComponent(lang || ''), {cache:'no-store'})
        .then(r => { if (!r.ok) throw Error(r.status); return r.json(); })
        .then(data => (catalog = data)).catch(e => { loading = null; throw e; });
    }
    return loading;
  }
  async function request(acao, valor) {
    const r = await fetch('/api/roteiro', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({acao, aba, valor, sessao:catalog?.sessao}), cache:'no-store'});
    if (!r.ok) throw Error(r.status);
    return r.json();
  }
  function el(tag, text, cls) {
    const e = document.createElement(tag);
    if (text) e.textContent = text;
    if (cls) e.className = cls;
    return e;
  }
  function close() {
    if (target) target.classList.remove('rt-tour-target');
    target = null;
    if (panel) { panel.close(); panel.remove(); panel = null; }
    if (previousFocus?.isConnected) previousFocus.focus({preventScroll:true});
  }
  function frame(type, title, detail, cancel) {
    close();
    previousFocus = document.activeElement;
    panel = el('dialog', '', 'rt-tour');
    panel.dataset.type = type;
    panel.lang = catalog.idioma;
    panel.dir = catalog.idioma === 'ar' ? 'rtl' : 'ltr';
    panel.setAttribute('aria-labelledby','suiteTourTitle');
    const article = el('article'), top = el('div','','rt-top');
    top.append(el('span',type === 'tip' ? catalog.labels.tip : catalog.labels.guide));
    if (detail) top.append(el('span',detail));
    const heading = el('h2',title);
    heading.id = 'suiteTourTitle';
    if (type === 'tip') { top.removeChild(top.firstChild); if (!top.hasChildNodes()) top.hidden=true; }
    const actions = el('div','','rt-actions'), status = el('p');
    status.setAttribute('role','status');
    article.append(top,heading,status,actions);
    panel.append(article);
    panel.addEventListener('cancel', e => { e.preventDefault(); cancel(); });
    document.body.append(panel);
    return {article,actions,status,body(node){article.insertBefore(node,status);}};
  }
  function button(box, label, cls, act) {
    const b = el('button',label,cls);
    b.type = 'button';
    b.addEventListener('click',act);
    box.actions.append(b);
    return b;
  }
  function show(focus) {
    panel.showModal();
    focus?.focus({preventScroll:true});
  }
  function gotoStep(index, manual) {
    const p = catalog.passos[index];
    keep(courseKey, JSON.stringify({sessao:catalog.sessao, index, manual}));
    const already = location.pathname === p.rota || (p.rota === '/' && location.pathname === '/suite');
    const hash = p.fragmento ? '#' + p.fragmento : '';
    if (!already) { location.assign(p.rota + hash); return; }
    if (hash && location.hash !== hash) location.hash = hash;
    const l = catalog.labels;
    let completing = false;
    const finish = async () => {
      if (completing) return;
      completing = true;
      try {
        const next = manual ? null : await request('concluir');
        keep(courseKey,null);
        close();
        if (next?.tipo === 'dica') tip(next);
      } catch { completing = false; box.status.textContent = l.savefail; }
    };
    const title = p.nome || l[p.titulo];
    const box = frame('guide',title,(index+1)+' / '+catalog.passos.length, finish);
    panel.dataset.step = String(index);
    box.body(el('p',p.dica ? catalog.tips[p.dica] : l[p.texto]));
    if (p.imagem) {
      const img = el('img');
      img.alt = title; img.src = p.imagem;
      img.addEventListener('error',() => {img.hidden=true;});
      box.body(img);
    }
    if (p.alvo) {
      target = document.querySelector(p.alvo);
      target?.classList.add('rt-tour-target');
    }
    button(box,l.skip,'rt-skip',finish);
    if (index) button(box,l.prev,'',() => gotoStep(index-1,manual));
    const last = index + 1 === catalog.passos.length;
    show(button(box,last ? l.done : l.next,'rt-next',last ? finish : () => gotoStep(index+1,manual)));
  }
  function syncPref(value) {
    const control=document.getElementById('suiteTipsEnabled');
    if (control) control.checked=value;
  }
  function tip(info) {
    const l=catalog.labels, box=frame('tip',l.tip,'',close);
    panel.dataset.tip=info.id;
    box.body(el('p',catalog.tips[info.id]));
    const row=el('label'), disable=el('input');
    disable.type='checkbox';
    row.append(disable,el('span',l.hide)); box.body(row);
    let seen=false;
    // A fila só avança depois que o navegador exibiu esta dica.
    async function acknowledge(){
      if (seen) return true;
      try { await request('exibida',info.id); seen=true; return true; }
      catch { box.status.textContent=l.savefail; return false; }
    }
    disable.addEventListener('change',async () => {
      disable.disabled=true;
      try { await acknowledge(); const d=await request('preferencia',!disable.checked); syncPref(d.mostrar); }
      catch { disable.checked=!disable.checked; box.status.textContent=l.savefail; }
      finally {disable.disabled=false;}
    });
    const finish = async (url) => {
      if (!await acknowledge()) return;
      close(); if(url) location.assign(url);
    };
    if(info.url) button(box,l.open,'',() => finish(info.url));
    show(button(box,l.close,'rt-next',() => finish('')));
    requestAnimationFrame(() => { if(panel?.dataset.tip===info.id) acknowledge(); });
  }
  async function prefs() {
    const control=document.getElementById('suiteTipsEnabled');
    if (!control) return;
    try {
      const d=await dataset(), {mostrar}=await request('estado');
      const replay=document.getElementById('gu_ver');
      if(replay){ replay.removeAttribute('data-radai-frase'); replay.textContent=d.labels.again; }
      document.getElementById('suiteTipsCaption').textContent=d.labels.startup;
      document.getElementById('gu_bloco').hidden=false;
      document.getElementById('suiteTipsPref').hidden=false;
      syncPref(mostrar);
      control.addEventListener('change', async () => {
        control.disabled=true;
        const status=document.getElementById('suiteTipsStatus');
        try { await request('preferencia',control.checked); status.textContent=''; }
        catch {control.checked=!control.checked;status.textContent=d.labels.savefail;}
        finally {control.disabled=false;}
      });
    } catch {}
  }
  window.radaiGuiaAbrir = async function () {
    try { await dataset(); gotoStep(0,true); } catch {}
  };
  function savedCourse(){
    try {return JSON.parse(read(courseKey));} catch {return null;}
  }
  async function start() {
    if (starting || panel || document.visibilityState==='hidden') return;
    const course=savedCourse(), home=location.pathname==='/' || location.pathname==='/suite';
    const convite=read('suite.guia.abertura');
    if (!course && (!home || (!convite && window.radaiJanelaDoApp!==true))) return;
    if (/^\/(aceite|primeiro-uso|termos)(\/|$)/.test(location.pathname)) return;
    starting=true;
    try {
      await dataset();
      if(!convite && course?.sessao===catalog.sessao && Number.isInteger(course.index) && catalog.passos[course.index]) {
        gotoStep(course.index,!!course.manual);
      } else {
        keep(courseKey,null);
        if(!home || (!convite && window.radaiJanelaDoApp!==true)) return;
        const next=await request('inicio',convite);
        keep('suite.guia.abertura',null);
        if(next.tipo==='guia') gotoStep(0,false);
        if(next.tipo==='dica') tip(next);
      }
    } catch {} finally {starting=false;}
  }
  function init(){prefs();start();}
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',init,{once:true}); else init();
  document.addEventListener('radai-janela',start);
  document.addEventListener('visibilitychange',start);
})();
