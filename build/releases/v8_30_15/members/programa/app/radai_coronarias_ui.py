# -*- coding: utf-8 -*-
"""Plugin settings and the workstation's separate coronary research consent."""
import json
from html import escape

import radai_lung_plugin
import radai_plugin_coronarias as policy
import radai_plugin_setup_ui as setup
import radai_ui
from radai_coronarias_ui_i18n import STRINGS


def _text(key):
    return '<span data-cor-text="%s" data-radai-t="1">%s</span>' % (key, escape(STRINGS['pt-BR'][key]))


def _tile(name, title, icon):
    return (f'<a class="plug-tile" href="#ps_{name}" aria-controls="ps_{name}" '
            f'aria-expanded="false" data-plug="{name}"><span class="plug-icon" '
            f'aria-hidden="true">{radai_ui.icone(icon)}</span><strong>{title}</strong></a>')


def _links():
    return (f'<div class="cor-links"><a href="{policy.FONTE}/tree/{policy.REVISAO}#license" '
            'target="_blank" rel="noopener noreferrer">' + _text('authors') + '</a>'
            f'<a href="{policy.PESOS_URL}" '
            'target="_blank" rel="noopener noreferrer">' + _text('weights') + '</a>'
            f'<a href="{policy.TERMOS_URL}" '
            'target="_blank" rel="noopener noreferrer">CC BY-NC 4.0</a></div>')


def _source_choice(mode, icon, title, description):
    pressed = 'true' if mode == 'online' else 'false'
    return (f'<button type="button" class="pi-option" data-cor-choice="{mode}" aria-pressed="{pressed}">'
            f'<span class="pi-icon" aria-hidden="true">{radai_ui.icone(icon)}</span>'
            f'<strong>{_text(title)}</strong><small>{_text(description)}</small></button>')


def _coronary():
    return ('<p>' + _text('model') + '</p>' + _links() + '''
<div id="cor-state" class="cor-state" tabindex="-1" aria-live="polite" role="status">
 <svg class="cor-indicator" viewBox="0 0 32 32" fill="none" aria-hidden="true">
  <circle cx="16" cy="16" r="12" pathLength="100"/>
  <path d="m9 16 5 5 9-10" pathLength="100"/>
 </svg>
 <div><p id="cor-message"></p><p id="cor-transcript" hidden></p></div>
</div>
<div class="pi-options" id="cor-choices" hidden>'''
 + _source_choice('online', 'rede', 'online', 'online_hint')
 + _source_choice('offline', 'pasta', 'offline', 'offline_hint') + '''</div>
<div id="cor-zip-panel" class="pi-panel" hidden>
 <button type="button" class="ui-envio pi-drop" id="cor-import">
 <span class="ui-envio-ic" aria-hidden="true">''' + radai_ui.icone('subir') + '''</span>
 <span class="ui-envio-tit">''' + _text('drop') + '''</span><span class="ui-envio-dica">ROCardS · ZIP</span></button>
 <input type="file" id="cor-file" accept=".zip,application/zip" hidden>
 <details class="cor-help"><summary>''' + _text('offline_help') + '''</summary><p>''' + _text('pack') + '''</p></details>
</div>
<p class="pi-source" role="status" id="cor-selection" hidden><bdi></bdi> <button type="button" class="ui-bt" id="cor-change">''' + _text('change') + '''</button></p>
<div class="pi-actions">
 <button type="button" class="ui-bt pri" id="cor-review" hidden>''' + _text('activate') + '''</button>
 <button type="button" class="ui-bt" id="cor-retry" hidden>''' + _text('retry') + '''</button>
</div>
<p class="pi-feedback" id="cor-diagnostic" role="status" hidden></p>
<p class="pi-feedback" id="cor-file-error" role="alert" hidden>''' + _text('bad_zip') + '''</p>
<template id="cor-template"><form class="cor-form">
 <div class="cor-warning" role="note"><span aria-hidden="true">⚠</span><strong>''' + _text('scope') + '''</strong></div>''' + _links() + '''
 <p>''' + _text('download') + '''</p>
 <p data-cor-filename hidden><bdi></bdi></p>
 <details data-cor-document hidden><summary>''' + _text('original') + '''</summary>
  <p lang="en" dir="ltr" class="cor-original"></p></details>
 <p class="cor-version"><bdi>ROCardS · <span data-cor-version></span></bdi></p>
 <label class="cor-agreement"><input required type="checkbox">''' + _text('agree') + '''</label>
 <div class="cor-actions">
  <button type="button" class="ui-bt" data-cor-cancel autofocus>''' + _text('cancel') + '''</button>
  <button type="submit" class="ui-bt pri" disabled>''' + _text('activate') + '''</button>
 </div>
</form></template>''')


def config_page(page):
    if 'id="ps_plugins"' in page:
        return page
    card_marker = ' <a class="cfg-card" href="#ps_limpar"'
    section_marker = '<section class="ps-cx fechado" id="ps_limpar" hidden>'
    if card_marker not in page or section_marker not in page:
        raise ValueError('Missing plugin settings anchor')
    card = (' <a class="cfg-card" href="#ps_plugins" data-alvo="ps_plugins">'
            '<span class="cab"><span class="ic">' + radai_ui.icone('pacote') +
            '</span><span class="n">8</span></span><h3>' + _text('plugins') +
            '</h3><p>NEURO RT · LUNG RT · ' + _text('coronary') + '</p></a>')
    section = ('<section class="ps-cx fechado" id="ps_plugins" hidden><h2 class="ps-cab" '
               'tabindex="0" role="button"><span class="ps-num">8</span>' + _text('plugins') +
               '<span class="ps-seta">&#9662;</span></h2><div class="ps-corpo">'
               '<div class="plug-tiles">' + _tile('neuro', 'NEURO RT', 'neuro_anatomia') +
               _tile('lung', 'LUNG RT', 'pulmoes') + _tile('coronarias', _text('coronary'), 'vaso') +
               '</div><div class="plug-panel" id="ps_neuro" hidden>' + setup.controls(True) +
               '</div><div class="plug-panel" id="ps_lung" hidden>' + radai_lung_plugin.controls() +
               '</div><div class="plug-panel plugin-install" id="ps_coronarias" hidden>' + _coronary() +
               '</div></div></section>')
    page = page.replace(card_marker, card + card_marker, 1)
    page = page.replace(section_marker, section + section_marker, 1)
    page = setup.assets(page).replace('</head>', '<style>' + CSS + '</style></head>', 1)
    catalog = json.dumps(STRINGS, ensure_ascii=True).replace('<', '\\u003c')
    scripts = setup.scripts() + radai_lung_plugin.scripts() + SCRIPT.replace('@CATALOG@', catalog)
    return page.replace('</body>', scripts + '</body>', 1)


CSS = '''
.cor-warning{margin:16px 0;display:flex;align-items:center;gap:14px;background:#ffdc84;color:#35230a;border:2px solid #bd850c;border-radius:10px;padding:14px 16px;line-height:1.5}.cor-warning>span{font-size:32px;flex:none}
.plug-tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,150px),1fr));gap:10px}
.plug-tile{display:flex;align-items:center;gap:10px;min-height:54px;box-sizing:border-box;padding:10px 14px;
 border:1px solid var(--line-strong);border-radius:var(--r-lg);color:var(--text);background:var(--panel-2);text-decoration:none}
.plug-tile[aria-expanded=true]{border-color:var(--accent);background:var(--accent-fraco)}
.plug-tile:focus-visible,.cor-form :focus-visible{outline:2px solid var(--accent);outline-offset:3px}
.plug-icon{color:var(--accent);display:grid;place-items:center}.plug-icon .ui-ic{width:24px;height:24px}
.plug-panel{margin-block-start:16px}.plug-panel[hidden],.plug-panel [hidden],.cor-form [hidden]{display:none!important}
.cor-links,.cor-actions{display:flex;gap:8px 16px;align-items:center;flex-wrap:wrap}
.cor-links{font-size:.88em}.cor-links a{color:var(--accent);text-decoration:underline}
.cor-help{margin-block-start:14px}.cor-help summary{cursor:pointer}
.cor-form [data-cor-filename]{padding:8px 12px;background:var(--panel-2);border:1px solid var(--line);border-radius:var(--r-lg);overflow-wrap:anywhere}
.cor-state{margin:16px 0;padding:12px 14px;display:flex;align-items:center;gap:10px;background:var(--panel-2);
 border:1px solid var(--line);border-radius:var(--r-lg)}.cor-state p{margin:0}
.cor-state:is([data-phase=active],[data-phase=restricted]){border-inline-start:4px solid var(--aviso,#c28a29)}
.cor-state:is([data-phase=active],[data-phase=restricted]) #cor-message{font-weight:650}
#cor-transcript,.cor-version{font-size:.88em;color:var(--text-muted)}.cor-indicator{display:none;width:27px;height:27px;flex:none}
#cor-diagnostic{font:12px/1.5 var(--mono);overflow-wrap:anywhere}
.cor-indicator circle,.cor-indicator path{stroke:currentColor;stroke-width:2.8;stroke-linecap:round;stroke-linejoin:round}
.cor-indicator circle{stroke-dasharray:74 100;transform-origin:center}
.cor-indicator path{stroke-dasharray:100;stroke-dashoffset:100}
.cor-state:is([data-phase=sending],[data-phase=upload],[data-phase=preparing],[data-phase=checking],[data-phase=active]) .cor-indicator{display:block;color:var(--accent)}
.cor-state:not([data-phase=active]) .cor-indicator circle{animation:cor-spin .82s linear infinite}
.cor-state[data-phase=active] .cor-indicator{color:var(--success)}
.cor-state[data-phase=active] .cor-indicator circle{opacity:.25;stroke-dasharray:100}
.cor-state[data-phase=active] .cor-indicator path{stroke-dashoffset:0}
.cor-state.cor-completed .cor-indicator path{animation:cor-check .26s ease-out}
@keyframes cor-spin{to{transform:rotate(360deg)}}@keyframes cor-check{from{stroke-dashoffset:100}}
.cor-form{display:grid;gap:14px}.cor-form p{margin:0}.cor-form summary{cursor:pointer}
.cor-original{white-space:pre-wrap;overflow-wrap:anywhere;max-height:30vh;overflow:auto;padding:.6em 0}
.cor-agreement{display:flex!important;align-items:flex-start;gap:9px;margin:0!important}
.cor-agreement input{flex:none;margin:.28em 0 0;accent-color:var(--accent)}
.cor-form .cor-actions{justify-content:flex-end}
@media(prefers-reduced-motion:reduce){.cor-state .cor-indicator *{animation:none!important;transition:none!important}}
'''

SCRIPT = r'''<script>
(() => {
 'use strict';
 const catalog = @CATALOG@;
 const endpoint = '/api/plugins/coronarias';
 const tiles = [...document.querySelectorAll('#ps_plugins [data-plug]')];
 const node = id => document.getElementById(id);
 const status = node('cor-state'), review = node('cor-review'), retry = node('cor-retry');
 const importButton = node('cor-import'), picker = node('cor-file'), badZip = node('cor-file-error');
 function locale() {
   let pref;
   try { pref = localStorage.getItem('radai_idioma'); } catch {}
   const value = document.documentElement.lang || pref || 'pt-BR';
   return catalog[value] ? value : Object.keys(catalog).find(code => code.split('-')[0] === value.split('-')[0]) || 'en';
 }
 const words = key => catalog[locale()][key];
 let selected = null, mode = 'online', uploadProgress = '';
 const choices = node('cor-choices'), zipPanel = node('cor-zip-panel'), selection = node('cor-selection');
 let state = null, restricted = false, phase = 'loading', detail = '', operation = 0, timer = 0, started = 0, dialog = null;
 function translate(root) {
   root.querySelectorAll('[data-cor-text]').forEach(el => {el.textContent = words(el.dataset.corText);});
 }
 function render() {
   status.dataset.phase = phase;
   node('cor-message').textContent = words(phase) + (phase === 'upload' && uploadProgress ? ' ' + uploadProgress : '');
   const recorded = restricted;
   node('cor-transcript').hidden = !recorded;
   node('cor-transcript').textContent = recorded ? words('saved') +
     (phase === 'active' || phase === 'restricted' ? '' : ' ' + words('scope')) : '';
   const diagnostic = node('cor-diagnostic');
   diagnostic.hidden = !detail || (phase !== 'error' && phase !== 'restricted');
   diagnostic.textContent = diagnostic.hidden ? '' : detail;
   const action = review.querySelector('[data-cor-text]');
   action.dataset.corText = mode === 'offline' ? 'import' : recorded ? 'repair' : 'start';
   action.textContent = words(action.dataset.corText);
   review.hidden = !(phase === 'inactive' || phase === 'restricted' || (phase === 'error' && state && !state.preparando));
   choices.hidden = review.hidden;
   zipPanel.hidden = review.hidden || mode !== 'offline' || Boolean(selected);
   selection.hidden = review.hidden || mode !== 'offline' || !selected;
   selection.querySelector('bdi').textContent = selected?.name || '';
   review.disabled = mode === 'offline' && !selected;
   for(const btn of choices.querySelectorAll('[data-cor-choice]')) btn.setAttribute('aria-pressed',String(btn.dataset.corChoice === mode));
   retry.hidden = phase !== 'error';
 }
 function language() {
   translate(document);
   if (dialog) dialog.caixa.querySelector('.ui-modal-tit').textContent = words('terms');
   render();
 }
 function select(name) {
   tiles.forEach(tile => {
     const open = tile.dataset.plug === name;
     tile.setAttribute('aria-expanded', String(open));
     node(tile.getAttribute('aria-controls')).hidden = !open;
   });
 }
 function followLocation() {
   const tile = tiles.find(item => item.hash === location.hash);
   if (tile) {window.cfgMostrar('ps_plugins'); select(tile.dataset.plug);}
 }
 tiles.forEach(tile => tile.addEventListener('click', ev => {
   if (ev.ctrlKey || ev.altKey || ev.metaKey || ev.shiftKey || ev.button !== 0) return;
   ev.preventDefault();
   const name = tile.getAttribute('aria-expanded') === 'true' ? '' : tile.dataset.plug;
   select(name);
   history.replaceState(null, '', name ? tile.hash : '#ps_plugins');
 }));
 followLocation();
 window.addEventListener('hashchange', followLocation);
 function setPhase(value) {phase = value;render();}
 function valid(data) {
   return data && typeof data.ativado === 'boolean' && typeof data.disponivel === 'boolean'
     && typeof data.termos_versao === 'string' && !!data.termos_versao
     && typeof data.termos_sha256 === 'string' && /^[a-f0-9]{64}$/i.test(data.termos_sha256);
 }
 function diagnostic(value) {
   if (typeof value !== 'string') return '';
   const line = value.trim().split(/[\r\n]/, 1)[0];
   // Absolute workstation paths can include personal directory names.
   return line.replace(/(?:[A-Z]:[\\/]|\\\\|(?:^|\s)\/(?!\/)).*$/i,' […]').slice(0, 240);
 }
 function diagnosis(message, status) {
   const value = diagnostic(message);
   if (!value && !status) return '';
   if (locale() === 'pt-BR' && value) return value;
   const key = status === 413 || /acima do teto|excede o tamanho|tamanho de pacote/i.test(value) ? 'too_large' :
     status === 507 || /espaço|space|disk full/i.test(value) ? 'disk' :
     /sha-256|integridade|inesperad|ausente|bad zip|pacote inválido|incompleta/i.test(value) ? 'invalid_package' :
     /termos|aceite|formulário/i.test(value) ? 'terms' : 'diagnostic';
   return words(key) + (status ? ' · HTTP ' + status : '');
 }
 async function request(path, options) {
   const response = await fetch(path, {mode:'same-origin', credentials:'same-origin', cache:'no-store',
     redirect:'error', ...options});
   const body = await response.json();
   if (!response.ok) {const err = Error('http ' + response.status);err.detail = diagnosis(body.erro, response.status);throw err;}
   return body;
 }
 function finish() {
   if (!started) {setPhase('active'); return;}
   const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
   const wait = reduced ? 0 : Math.max(0, 2000 - (performance.now() - started));
   setPhase('checking');
   timer = setTimeout(() => {
     started = 0;
     status.classList.add('cor-completed');
     setPhase('active');
   }, wait);
 }
 async function refresh() {
   clearTimeout(timer);
   const serial = ++operation;
   try {
     const data = await request(endpoint);
     if (serial !== operation) return;
     if (!valid(data)) throw Error('invalid status');
     state = data;restricted = data.ativado;detail = diagnosis(data.erro);
     if (data.ativado && data.disponivel && !data.preparando) finish();
     else if (data.preparando) {
       setPhase('preparing');timer = setTimeout(refresh, 1800);
     } else {started = 0;setPhase(data.ativado ? 'restricted' : data.erro ? 'error' : 'inactive');}
   } catch (err) {
     if (serial !== operation) return;
     state = null;started = 0;detail = err.detail || '';setPhase('error');
   }
 }
 function sendPackage(snapshot, file) {
   return new Promise((resolve, reject) => {
     const xhr = new XMLHttpRequest();
     xhr.open('POST', endpoint + '/importar');
     xhr.responseType = 'json';
     const headers = {'Content-Type':'application/zip','X-Radai-Aceito':'1',
       'X-Radai-Termos-Versao':snapshot.termos_versao,'X-Radai-Termos-Sha256':snapshot.termos_sha256};
     for(const [name,value] of Object.entries(headers)) xhr.setRequestHeader(name,value);
     xhr.upload.onprogress = event => {
       const format = new Intl.NumberFormat(locale(),{maximumFractionDigits:1});
       uploadProgress = format.format(event.loaded / 1048576) + ' / ' + format.format((event.total || file.size) / 1048576) + ' MiB';
       render();
     };
     xhr.onload = () => {
       if(xhr.status >= 200 && xhr.status < 300 && xhr.response) resolve(xhr.response);
       else reject({detail: diagnosis(xhr.response?.erro, xhr.status)});
     };
     xhr.onerror = xhr.onabort = () => reject({detail:words('error')});
     xhr.send(file);
   });
 }
 async function activate(snapshot, file) {
   const serial = ++operation;
   clearTimeout(timer);
   started = performance.now();detail = '';uploadProgress = '';status.classList.remove('cor-completed');
   setPhase(file ? 'upload' : 'sending');status.focus({preventScroll:true});
   try {
     const result = file ? await sendPackage(snapshot, file) : await request(endpoint + '/ativar', {method:'POST',
       headers:{'Content-Type':'application/json'},body:JSON.stringify({
         aceito:true, termos_versao:snapshot.termos_versao, termos_sha256:snapshot.termos_sha256
       })});
     if (serial !== operation) return;
     if (result.ok !== true || (!result.ativado && !result.preparando)) {
       const err = Error('activation');err.detail = diagnosis(result.erro);throw err;
     }
     if (result.ativado === true && !result.preparando) await refresh();
     else {setPhase('preparing');timer = setTimeout(refresh, 1000);}
   } catch (err) {
     if (serial !== operation) return;
     started = 0;detail = err.detail || '';setPhase('error');
   }
 }
 function openConsent(file) {
   if (dialog || !valid(state) || (state.ativado && state.disponivel) || state.preparando) return;
   const snapshot = state, form = node('cor-template').content.firstElementChild.cloneNode(true);
   const check = form.querySelector('input'), submit = form.querySelector('[type=submit]');
   if (file) {
     form.querySelector('[data-cor-text=download]').dataset.corText = 'import_terms';
     submit.querySelector('[data-cor-text]').dataset.corText = 'import';
     const filename = form.querySelector('[data-cor-filename]');
     filename.hidden = false;filename.querySelector('bdi').textContent = file.name;
   } else if (snapshot.ativado) {submit.querySelector('[data-cor-text]').dataset.corText = 'repair';}
   translate(form);
   form.querySelector('[data-cor-version]').textContent = snapshot.termos_versao;
   if (typeof snapshot.termos_texto === 'string' && snapshot.termos_texto.trim()) {
     form.querySelector('[data-cor-document]').hidden = false;
     form.querySelector('.cor-original').textContent = snapshot.termos_texto;
   }
   dialog = window.uiModal({titulo:words('terms'),no:form,largura:640,origem:review,
     aoFechar(){dialog.caixa.inert = true;dialog.caixa.setAttribute('aria-hidden','true');dialog = null;}});
   check.addEventListener('change', () => {submit.disabled = !check.checked;});
   form.querySelector('[data-cor-cancel]').addEventListener('click', () => dialog.fechar());
   form.addEventListener('submit', ev => {
     ev.preventDefault();if (!check.checked || submit.disabled) return;
     submit.disabled = true;dialog.fechar();activate(snapshot, file);
   });
 }
 for(const button of choices.querySelectorAll('[data-cor-choice]')) button.addEventListener('click', () => {
   mode = button.dataset.corChoice;badZip.hidden=true;render();
 });
 function choose(files) {
   if(!files?.length) return;
   const file = files[0];
   if(files.length!==1 || !file.size || !/\.zip$/i.test(file.name)) {
     selected = null; badZip.hidden = false;
   } else { selected=file;badZip.hidden=true; }
   render();
 }
 review.addEventListener('click', () => {badZip.hidden = true;openConsent(mode==='offline' ? selected : null);});
 importButton.addEventListener('click', () => {picker.value='';picker.click();});
 picker.addEventListener('change', () => choose(picker.files));
 node('cor-change').addEventListener('click', () => {selected=null;badZip.hidden=true;render();importButton.focus();});
 importButton.addEventListener('dragover', e=>{e.preventDefault();e.dataTransfer.dropEffect='copy';importButton.classList.add('sobre');});
 importButton.addEventListener('dragleave', ()=>importButton.classList.remove('sobre'));
 importButton.addEventListener('drop', e=>{e.preventDefault();importButton.classList.remove('sobre');choose(e.dataTransfer.files);});
 retry.addEventListener('click', () => {state = null;setPhase('loading');refresh();});
 new MutationObserver(language).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
 window.addEventListener('pageshow', ev => {if (ev.persisted) refresh();});
 language();refresh();
})();</script>'''
