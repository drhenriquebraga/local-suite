import json

import radai_ui


HINT = 'A suíte fecha durante o preparo, mostra o progresso no PowerShell e reabre ao terminar. O Python existente é reutilizado.'
PLUGINS = {
    'neuro': ('NEURO RT', 'neuro-rt', 'cruzamento', 'nidus'),
    'lung': ('LUNG RT', 'lung-rt', 'pulmoes', 'lung'),
}

CSS = '''
.plugin-install-page{max-width:1060px;width:100%;box-sizing:border-box;margin:0 auto;padding:clamp(18px,4vw,42px)}
.plugin-install{color:var(--text);font:14px/1.55 var(--font-display);min-width:0;--pi-cor:var(--mod-nidus);--pi-fraco:var(--mod-nidus-fraco)}
.plugin-install[data-plugin-install="lung-rt"]{--pi-cor:var(--mod-recon);--pi-fraco:var(--mod-recon-fraco)}
.plugin-install [hidden]{display:none!important}
.plugin-install p{margin:0;overflow-wrap:anywhere}
.plugin-install :is(h3,h4){margin:0;font-size:14px;font-weight:650;line-height:1.4}
.plugin-install .pi-status{border:1px solid var(--line);background:var(--panel-2);
 border-radius:var(--r-lg);padding:12px 14px;margin:0 0 18px;display:grid;gap:4px}
.plugin-install .pi-status p:empty,.plugin-install .pi-source:empty{display:none}
.plugin-install .pi-status code,.plugin-install .pi-channel code{
 color:var(--text-muted);font:12px var(--mono);overflow-wrap:anywhere}
.plugin-install .pi-options{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,188px),1fr));gap:10px;margin:0 0 12px}
.plugin-install .pi-option{display:grid;gap:5px;justify-items:start;align-content:start;min-width:0;
 text-align:start;padding:13px 14px;min-height:110px;background:var(--panel);color:var(--text);
 border:1px solid var(--line-strong);border-radius:var(--r-lg);font:inherit;cursor:pointer}
.plugin-install .pi-option :is(span,small){overflow-wrap:anywhere}
.plugin-install .pi-icon{display:grid;place-items:center;background:var(--pi-fraco);color:var(--pi-cor);
 border-radius:var(--r-md);width:26px;height:26px}
.plugin-install .pi-icon svg{width:16px;height:16px}
.plugin-install .pi-option:hover,.plugin-install .pi-option[aria-pressed="true"]{border-color:var(--pi-cor)}
.plugin-install .pi-option[aria-pressed="true"]{background:var(--pi-fraco)}
.plugin-install .pi-option:focus-visible{outline:2px solid var(--pi-cor);outline-offset:3px}
.plugin-install .pi-option:disabled{opacity:.55;cursor:not-allowed}
.plugin-install small,.plugin-install .pi-muted,.plugin-install .pi-hint{color:var(--text-muted);font-size:13px}
.plugin-install .pi-panel{display:grid;gap:10px;padding:14px;background:var(--panel-2);
 border:1px solid var(--line);border-radius:var(--r-lg);min-width:0}
.plugin-install .pi-overview{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,260px),1fr));gap:12px;margin:0 0 12px}
.plugin-install .pi-versions{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,220px),1fr));gap:10px;margin:0 0 12px}
.plugin-install .pi-versions>div{padding:12px 14px;border:1px solid var(--line);border-radius:var(--r-lg);background:var(--panel-2);display:grid;gap:3px}
.plugin-install .pi-versions dt{color:var(--text-muted);font-size:12px}
.plugin-install .pi-versions dd{margin:0;overflow-wrap:anywhere}
.plugin-install .pi-versions small{font-size:12px}
.plugin-install .pi-channel{display:grid;gap:6px;margin:0;padding:0;list-style:none}
.plugin-install .pi-channel li{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:6px 12px}
.plugin-install .pi-channel output{display:flex;align-items:baseline;gap:6px;flex-wrap:wrap;min-width:0}
.plugin-install .pi-channel output::before{content:"";width:7px;height:7px;border-radius:50%;background:var(--text-dim);align-self:center}
.plugin-install .pi-channel output[data-state="ok"]::before{background:var(--success)}
.plugin-install .pi-channel output[data-state="error"]::before{background:var(--perigo)}
.plugin-install .pi-row,.plugin-install .pi-actions{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.plugin-install .pi-row .ui-bt{white-space:normal}
.plugin-install .pi-field{color:var(--text);background:var(--bg-1);border:1px solid var(--line-strong);
 border-radius:var(--r-md);padding:8px 10px;font:inherit;flex:1 1 220px;min-width:0}
.plugin-install .pi-field:focus-visible{outline:2px solid var(--pi-cor);outline-offset:2px}
.plugin-install .pi-drop{width:100%;margin:0;box-sizing:border-box;color:var(--text);font:inherit;--accent:var(--pi-cor);--accent-fraco:var(--pi-fraco)}
.plugin-install .pi-drop[aria-disabled="true"]{cursor:not-allowed}
.plugin-install .pi-source{margin:10px 0;min-height:0;color:var(--text-muted)}
.plugin-install .pi-source[data-state="error"]{color:var(--perigo)}
.plugin-install .pi-source[data-state="ok"]{color:var(--success)}
.plugin-install .pi-terms{display:grid;gap:10px}
.plugin-install :is(.pi-terms,#neuro-install-consent){margin:16px 0 10px}
.plugin-install :is(.pi-terms,#neuro-install-consent) label{display:flex;align-items:flex-start;gap:8px}
.plugin-install .pi-terms input[type="checkbox"]{flex:none;margin-top:.33em;accent-color:var(--pi-cor)}
.plugin-install #neuro-install-consent-document{display:grid;gap:6px;margin-bottom:10px}
.plugin-install .pi-actions{margin:12px 0}
.plugin-install progress{width:100%;height:8px;accent-color:var(--pi-cor)}
.plugin-install .pi-last{color:var(--perigo)}
.plugin-install .pi-last + .pi-hint{margin-top:6px}
'''


def _option(key, icon, title, help_text, selected=False):
    return (f'<button type="button" class="pi-option" data-pi-choice="{key}" '
            f'aria-pressed="{str(selected).lower()}"><span class="pi-icon" aria-hidden="true">'
            f'{radai_ui.icone(icon)}</span><strong data-radai-frase>{title}</strong>'
            f'<small data-radai-frase>{help_text}</small></button>')


def _choices(name, ids):
    return ('''<div class="pi-options" role="group" aria-label="Origem da instalação">'''
            + _option('auto', 'rede', 'Instalação automática', 'Prepare os pesos que faltam usando o código instalado.', True)
            + _option('zip', 'pacote', 'Instalar / atualizar apenas o código offline', 'Escolha o SETUP leve. Os pesos instalados são preservados.')
            + _option('folder', 'pasta', 'Instalar / atualizar o pacote de pesos offline', 'Escolha o ZIP do bundle de pesos. O código carregado é preservado.')
            + f'''</div>

<div class="pi-overview">
<div class="pi-panel" data-pi-panel="auto">
  <h3 data-radai-frase>Servidores de atualização do código</h3>
  <ul class="pi-channel">
    <li><span>GitHub</span><output data-pi-channel="github"><span data-radai-frase>Ainda não consultado</span></output></li>
    <li><span data-radai-frase>Espelho</span><output data-pi-channel="mirror"><span data-radai-frase>Ainda não consultado</span></output></li>
  </ul>
  <div class="pi-row">
    <button class="ui-bt" type="button" data-pi-probe data-radai-frase>Testar conexão</button>
    <button class="ui-bt" type="button" id="{ids['refresh']}" data-radai-frase>Verificar atualizações</button>
  </div>
</div>
<dl class="pi-versions" data-pi-versions>
  <div><dt data-radai-frase>Código carregado</dt><dd data-pi-code-version>—</dd></div>
  <div><dt data-radai-frase>Pacote de pesos</dt><dd data-pi-weights-version>—</dd><small data-pi-weights-state></small></div>
</dl>
</div>
<div class="pi-panel" data-pi-panel="zip" hidden>
  <h3 data-radai-frase>Instalar / atualizar apenas o código offline</h3>
  <p class="pi-muted" data-radai-frase>Escolha o SETUP leve. Os pesos instalados são preservados.</p>
  <input type="file" accept=".zip,application/zip" data-pi-file hidden>
  <button type="button" class="ui-envio pi-drop" data-pi-drop>
    <span class="ui-envio-ic" aria-hidden="true">{radai_ui.icone('subir')}</span>
    <span class="ui-envio-tit" data-radai-frase>Arraste o ZIP ou clique para escolher</span>
    <span class="ui-envio-dica">{name} · SETUP (.zip)</span>
  </button>
</div>
<div class="pi-panel" data-pi-panel="folder" id="{ids['folder_panel']}" hidden>
  <h3 data-radai-frase>Instalar / atualizar o pacote de pesos offline</h3>
  <p class="pi-muted" data-radai-frase>Escolha o ZIP do bundle de pesos. O código carregado é preservado.</p>
  <input type="file" accept=".zip,application/zip" data-pi-weights-file hidden>
  <button type="button" class="ui-envio pi-drop" data-pi-weights-drop>
    <span class="ui-envio-ic" aria-hidden="true">{radai_ui.icone('subir')}</span>
    <span class="ui-envio-tit" data-radai-frase>Arraste o ZIP ou clique para escolher</span>
    <span class="ui-envio-dica">{name} · BUNDLE (.zip)</span>
  </button>
  <details><summary data-radai-frase>Usar uma pasta já extraída</summary>
  <label for="{ids['folder']}" data-radai-frase>Pasta do instalador ou pacote offline</label>
  <div class="pi-row">
    <input type="text" class="pi-field" id="{ids['folder']}" data-pi-folder autocomplete="off" spellcheck="false">
    <button class="ui-bt" type="button" id="{ids['browse']}" data-neuro-host-browse="1" data-pi-browse data-radai-frase>Procurar…</button>
    <button class="ui-bt" type="button" id="{ids['inspect']}" data-pi-inspect data-radai-frase>Conferir pacote local</button>
  </div>
  </details>
</div>
<p class="pi-source" id="{ids['source']}" data-pi-source role="status"></p>''')


def controls(settings=False, *, plugin='neuro'):
    name, slug, _, _ = PLUGINS[plugin]
    if plugin == 'neuro':
        panel = f'id="neuro-update" data-neuro-install="1" data-neuro-settings="{int(settings)}"'
        ids = {'refresh': 'neuro-release-refresh', 'folder_panel': 'neuro-local-source',
               'folder': 'neuro-local-folder', 'browse': 'neuro-local-browse',
               'inspect': 'neuro-local-inspect', 'source': 'neuro-local-message'}
        status = '''<p id="neuro-update-message" role="status" data-radai-frase>Verificando a instalação do NEURO RT.</p>
<progress id="neuro-update-progress" max="100" aria-label="Progresso da instalação" hidden></progress>'''
        actions = '<div class="pi-actions" id="neuro-update-actions"></div>'
    else:
        panel = 'id="lung-plugin-setup"'
        ids = {'refresh': 'lp-refresh', 'folder_panel': 'lp-folder-panel', 'folder': 'lp-folder',
               'browse': 'lp-browse', 'inspect': 'lp-inspect', 'source': 'lp-source'}
        status = '<p id="lp-status" role="status" data-radai-frase>Verificando a instalação do LUNG RT…</p>'
        actions = '''<div class="pi-actions">
  <button class="ui-bt pri" type="button" id="lp-install" disabled data-radai-frase>Instalar ou atualizar LUNG RT</button>
  <a href="/lung/rastreio#config" data-radai-frase>Configurar rastreio e laudos</a>
</div>'''
    return (f'<section class="plugin-install" {panel} data-plugin-install="{slug}">'
            f'<div class="pi-status">{status}<p class="pi-last" data-pi-error role="status" hidden></p>'
            '<p class="pi-last" data-pi-last role="status" hidden></p></div>'
            + _choices(name, ids) + actions + f'<p class="pi-hint" data-radai-frase>{HINT}</p></section>')


SCRIPT = r'''
(function () {
  'use strict';
  const t = text => window.radaiFrase ? window.radaiFrase(text) : text;
  const safeCode = code => typeof code === 'string' && /^[A-Z0-9_-]{1,60}$/.test(code) ? code : '';
  const formatNames = {
    setup_zip: 'Código offline',
    setup_folder: 'Código offline',
    offline_bundle: 'Pacote de pesos offline'
  };
  const hints = {
    extract_setup: 'Use o card ZIP do instalador ou extraia todos os arquivos para escolher a pasta.',
    update_suite: 'Atualize ou repare a base do Local Suite antes de instalar o plugin.',
    prepare_again: 'Escolha o SETUP deste plugin ou prepare novamente o bundle completo.'
  };
  function messageFor(error) {
    const detail = error.detail;
    if (typeof detail === 'string') return t(detail);
    const message = detail && (hints[detail.source_hint] || detail.message);
    return t(message || 'Não foi possível concluir.');
  }
  function errorText(error) {
    const code = safeCode(error.detail?.error_code || error.detail?.code || error.code);
    return [messageFor(error), code || (error.status ? 'HTTP ' + error.status : '')].filter(Boolean).join(' · ');
  }
  async function checked(response) {
    const payload = await response.json().catch(() => ({}));
    if (response.ok) return payload;
    throw Object.assign(new Error('plugin'), {status: response.status, detail: payload.detail});
  }

  function bind(panel, hooks) {
    const slug = panel.dataset.pluginInstall;
    const find = selector => panel.querySelector(selector);
    const options = Array.from(panel.querySelectorAll('[data-pi-choice]'));
    const panels = Array.from(panel.querySelectorAll('[data-pi-panel]'));
    const folder = find('[data-pi-folder]');
    const browse = find('[data-pi-browse]');
    const inspect = find('[data-pi-inspect]');
    const source = find('[data-pi-source]');
    const drop = find('[data-pi-drop]');
    const file = find('[data-pi-file]');
    const weightDrop = find('[data-pi-weights-drop]');
    const weightFile = find('[data-pi-weights-file]');
    const probe = find('[data-pi-probe]');
    const inlineError = find('[data-pi-error]');
    const last = find('[data-pi-last]');
    let mode = 'auto', pending = false, probing = false;

    function sync() {
      const locked = pending || Boolean(hooks.isLocked());
      for (const control of [...options, folder, browse, file, weightFile].filter(Boolean)) control.disabled = locked;
      inspect.disabled = locked || !folder.value.trim();
      drop.setAttribute('aria-disabled', String(locked));
      if (weightDrop) weightDrop.setAttribute('aria-disabled', String(locked));
      probe.disabled = locked || probing;
    }
    function notice(text = '', status = '') {
      source.textContent = text;
      source.dataset.state = status;
    }
    function setMode(next) {
      if (next === mode || pending || hooks.isLocked()) return;
      mode = next;
      for (const option of options) {
        option.setAttribute('aria-pressed', String(option.dataset.piChoice === mode));
      }
      for (const part of panels) part.hidden = part.dataset.piPanel !== mode;
      notice();
      hooks.reset();
      sync();
    }
    async function post(path, value, raw = false) {
      const current = await hooks.status();
      if (raw) return new Promise((resolve,reject) => {
        const request = new XMLHttpRequest();
        request.open('POST','/api/plugins/' + slug + '/' + path);
        request.responseType = 'json';
        request.setRequestHeader('Content-Type','application/zip');
        request.setRequestHeader(hooks.tokenHeader,current.token);
        request.upload.addEventListener('progress',event => {
          const total = event.lengthComputable ? event.total : value.size;
          notice(t('Enviando ZIP local…') + ' ' + (event.loaded / 1048576).toFixed(1) + ' / ' + (total / 1048576).toFixed(1) + ' MB');
        });
        request.upload.addEventListener('load',() => notice(t('Conferindo o pacote local…')));
        request.addEventListener('load',() => {
          if(request.status >= 200 && request.status < 300) resolve({current,body:request.response || {}});
          else reject(Object.assign(new Error('plugin'),{status:request.status,detail:request.response?.detail}));
        });
        request.addEventListener('error',() => reject(Object.assign(new Error('plugin'),{code:'LOCAL_UPLOAD_FAILED'})));
        request.send(value);
      });
      const response = await fetch('/api/plugins/' + slug + '/' + path, {
        method: 'POST',
        headers: {
          'Content-Type': raw ? 'application/zip' : 'application/json',
          [hooks.tokenHeader]: current.token
        },
        body: raw ? value : JSON.stringify(value)
      });
      return {current, body: await checked(response)};
    }
    async function verify(path, value, raw = false) {
      if (pending || hooks.isLocked()) return;
      pending = true;
      hooks.reset();
      hooks.lock(true);
      sync();
      notice(t('Conferindo o pacote local…'));
      try {
        const operation = mode === 'zip' ? 'code' : 'weights';
        const result = await post(path + '?operation=' + operation, value, raw);
        const {body} = result;
        const description = body.description || body;
        const version = description.version;
        if (typeof body.source_id !== 'string' || !/^[A-Za-z0-9_-]{1,128}$/.test(body.source_id) ||
            typeof version !== 'string' || !/^\d+(?:\.\d+)*$/.test(version)) {
          throw new Error('source');
        }
        const format = description.format || body.format ||
          (raw ? 'setup_zip' : description.offline ? 'offline_bundle' : 'setup_folder');
        hooks.accept(body.source_id, version, result.current, format);
        notice(t(formatNames[format] || 'Pacote local') + ' · ' + version + ' · ' + t('Pacote conferido'), 'ok');
      } catch (error) {
        notice(errorText(error), 'error');
      } finally {
        pending = false;
        hooks.lock(false);
        sync();
      }
    }
    function zip(files, expectedMode = 'zip') {
      if (mode !== expectedMode || pending || hooks.isLocked() || !files.length) return;
      if (files.length !== 1 || !/\.zip$/i.test(files[0].name)) {
        hooks.reset();
        notice(t('Escolha um único arquivo ZIP.'), 'error');
        return;
      }
      verify('local/upload', files[0], true);
    }
    function paintChannel(output, result) {
      const status = result?.status;
      const ok = ['ok', 'available', 'current', 'reachable', 'online', 'up'].includes(status);
      const unavailable = !ok && status !== 'checking';
      const label = document.createElement('span');
      label.textContent = t(ok ? 'Disponível' : unavailable ? 'Indisponível' : 'Consultando…');
      const details = document.createElement('code');
      const version = typeof result?.version === 'string' && /^\d+(?:\.\d+)*$/.test(result.version) ? result.version : '';
      details.textContent = [version, safeCode(String(result?.code || ''))].filter(Boolean).join(' · ');
      output.dataset.state = ok ? 'ok' : unavailable ? 'error' : '';
      output.replaceChildren(label);
      if (details.textContent) output.append(details);
    }
    async function testConnection() {
      if (probing || hooks.isLocked()) return;
      probing = true;
      sync();
      const outputs = Array.from(panel.querySelectorAll('[data-pi-channel]'));
      outputs.forEach(output => paintChannel(output, {status: 'checking'}));
      try {
        const result = (await post('connectivity', {})).body;
        outputs.forEach(output => paintChannel(output, result[output.dataset.piChannel]));
      } catch (error) {
        outputs.forEach(output => paintChannel(output, {status: 'error', code: error.status || 'NETWORK_ERROR'}));
      } finally {
        probing = false;
        sync();
      }
    }
    function presentResult(result, target) {
      const code = safeCode(result?.error_code || result?.code);
      if (!code) {
        target.hidden = true;
        if (target.textContent) target.textContent = '';
        return;
      }
      const rawStage = result.error_stage || result.stage;
      const stageNames = {
        checking: 'Conferindo o pacote local…', handoff: 'Preparando o plugin',
        preparing: 'Preparando o plugin', downloading: 'Baixando componentes',
        resources: 'Preparando recursos', extracting: 'Preparando recursos',
        verifying: 'Conferindo o pacote local…', validating: 'Conferindo o pacote local…',
        restart: 'Reabrindo a suíte'
      };
      const stage = typeof rawStage === 'string' && /^[a-z][a-z_]{0,40}$/.test(rawStage)
        ? t(stageNames[rawStage] || rawStage) : '';
      const log = typeof result.log === 'string' && /^[A-Za-z0-9_. /\\-]{1,180}$/.test(result.log) ? result.log : '';
      const note = typeof result.message === 'string' ? t(result.message) : '';
      const text = [note, t('Código:') + ' ' + code, stage && t('Etapa:') + ' ' + stage, log && t('Log de instalação') + ' ' + log].filter(Boolean).join(' · ');
      if (target.textContent !== text) target.textContent = text;
      target.hidden = false;
    }
    options.forEach(option => option.addEventListener('click', () => setMode(option.dataset.piChoice)));
    browse.addEventListener('click', () => {
      if (!window.uiExplorador) { folder.focus(); return; }
      window.uiExplorador({
        titulo: t('Pasta do instalador ou pacote offline'), origem: browse, inicial: folder.value,
        aoUsar(path) { folder.value = path; folder.dispatchEvent(new Event('input')); }
      });
    });
    folder.addEventListener('input', () => {
      hooks.reset();
      notice();
      sync();
    });
    inspect.addEventListener('click', () => {
      if (folder.value.trim()) verify('local/inspect', {folder: folder.value.trim()});
    });
    function bindDrop(zone, input, expectedMode) {
    if (!zone || !input) return;
    let depth = 0;
    zone.addEventListener('click', () => { if (zone.getAttribute('aria-disabled') === 'false') input.click(); });
    input.addEventListener('change', () => { zip(input.files, expectedMode); input.value = ''; });
    zone.addEventListener('dragenter', event => {
      event.preventDefault();
      if (zone.getAttribute('aria-disabled') === 'false') { depth++; zone.classList.add('sobre'); }
    });
    zone.addEventListener('dragover', event => {
      event.preventDefault();
      event.dataTransfer.dropEffect = zone.getAttribute('aria-disabled') === 'false' ? 'copy' : 'none';
    });
    zone.addEventListener('dragleave', () => {
      depth = Math.max(0, depth - 1);
      if (!depth) zone.classList.remove('sobre');
    });
    zone.addEventListener('drop', event => {
      event.preventDefault();
      depth = 0;
      zone.classList.remove('sobre');
      zip(event.dataTransfer.files, expectedMode);
    });
    }
    bindDrop(drop, file, 'zip');
    bindDrop(weightDrop, weightFile, 'folder');
    function versions(data) {
      const code = find('[data-pi-code-version]');
      const bundle = find('[data-pi-weights-version]');
      const detail = find('[data-pi-weights-state]');
      if (!code || !bundle || !detail) return;
      const valid = value => typeof value === 'string' && /^\d+(?:\.\d+)*$/.test(value);
      const current = data?.code_version || data?.active_version || data?.version;
      code.textContent = valid(current) ? current : t('Ainda não instalado');
      const weights = data?.weights || {};
      bundle.textContent = valid(weights.version) ? weights.version :
        t(weights.state === 'ready' ? 'Instalado · versão não registrada' : 'Ainda não instalado');
      const names = {ready:'Pesos prontos',missing:'Pesos não instalados',partial:'Pesos incompletos',checking:'Conferindo os pesos…'};
      detail.textContent = t(names[weights.state] || 'Conferindo os pesos…');
    }
    probe.addEventListener('click', testConnection);
    return {
      sync, versions, local: () => mode !== 'auto', operation: () => mode === 'zip' ? 'code' : 'weights',
      failure(error) { inlineError.textContent = errorText(error); inlineError.hidden = false; },
      clearFailure() { inlineError.textContent = ''; inlineError.hidden = true; },
      result(result) { presentResult(result, last); }
    };
  }
  async function confirmInstallation(data, name) {
    if (data.accepted) return new Promise(resolve => {
      window.uiConfirmar({titulo:t('Instalar ou atualizar %s').replace('%s',name),
        corpo:t('A suíte será fechada para instalar o plugin e reaberta ao terminar. Continuar?'),
        aoSim:() => resolve(true), aoNao:() => resolve(false)});
    });
    const policy = data.policy;
    if (!policy || !Array.isArray(policy.clauses)) return false;
    return new Promise(resolve => {
      let finished = false;
      const box = document.createElement('div');
      box.className = 'plugin-install pi-terms';
      for (const clause of policy.clauses) {
        const line = document.createElement('p');
        line.textContent = t(typeof clause === 'string' ? clause : clause.text);
        box.append(line);
      }
      const label = document.createElement('label');
      const input = document.createElement('input'); input.type = 'checkbox';
      const words = document.createElement('span');
      words.textContent = t('Li e aceito os termos do LUNG RT e a participação na fase de testes.');
      label.append(input, words);box.append(label);
      const note = document.createElement('p');note.textContent = t('A suíte fecha durante o preparo, mostra o progresso no PowerShell e reabre ao terminar. O Python existente é reutilizado.');box.append(note);
      const row = document.createElement('div');row.className = 'pi-actions';
      const cancel = document.createElement('button');cancel.type = 'button';cancel.className = 'ui-bt';cancel.textContent = t('Cancelar');
      const accept = document.createElement('button');accept.type = 'button';accept.className = 'ui-bt pri';accept.disabled = true;accept.textContent = t('Instalar ou atualizar %s').replace('%s',name);
      row.append(cancel,accept);box.append(row);
      const modal = window.uiModal({titulo:policy.title,no:box,largura:720,aoFechar(){if(!finished){finished=true;resolve(false);}}});
      input.addEventListener('change',() => {accept.disabled = !input.checked;});
      cancel.addEventListener('click',() => modal.fechar());
      accept.addEventListener('click',() => {if(!input.checked)return;finished=true;modal.fechar();resolve(true);});
    });
  }
  window.RadaiPluginSetup = {bind, checked, confirmInstallation};
})();
'''


def assets(page):
    if 'id="plugin-install-script"' in page:
        return page
    page = page.replace('</head>', '<style id="plugin-install-css">' + CSS + '</style></head>', 1)
    return page.replace('</body>', '<script id="plugin-install-script">' + SCRIPT + '</script></body>', 1)


def scripts():
    import radai_neuro_install as sdk
    catalog = json.dumps(sdk.INSTALL_UI_CATALOG, ensure_ascii=True).replace('<', '\\u003c')
    return ('<script>window.NEURO_INSTALL_CATALOG=' + catalog + ';' +
            sdk.INSTALL_UI_SCRIPT.replace('</script', '<\\/script') + '</script>')


def landing(plugin, active=None, title=None, controller=None):
    import html
    import radai_menu

    name, _, icon, palette = PLUGINS[plugin]
    title = title or name
    action = 'Instalar ou atualizar ' + name
    header = radai_ui.cabeca_de_funcao(icon, title, action, chave_modulo=palette)
    page = ('<!doctype html><html><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{html.escape(title)} · Local Suite</title></head><body>'
            '<main class="plugin-install-page">' + header
            + radai_ui.passo(1, action, controls(plugin=plugin)) + '</main></body></html>')
    page = assets(page).replace('</body>', (controller or scripts()) + '</body>', 1)
    return radai_ui.com_portao(radai_menu.aplicar(page, active or plugin))


def config_page(page):
    if 'id="ps_neuro"' in page:
        return page
    card = ''' <a class="cfg-card" href="#ps_neuro" data-alvo="ps_neuro">
<span class="cab"><span class="n">N</span><span class="ic">''' + radai_ui.icone('neuro_anatomia') + '''</span></span>
<h3 data-radai-frase>Plugin NEURO RT</h3>
<p data-radai-frase>Instalar, atualizar e preparar com uma pasta offline.</p>
<span class="st" data-radai-frase>Instalação e atualização</span></a>
'''
    section = '''<section class="ps-cx fechado" id="ps_neuro" hidden>
<h2 class="ps-cab" tabindex="0" role="button"><span class="ps-num">N</span>
<span data-radai-frase>Plugin NEURO RT</span><span class="ps-seta">&#9662;</span></h2>
<div class="ps-corpo">''' + controls(True) + '</div></section>\n'
    card_marker = ' <a class="cfg-card" href="#ps_limpar"'
    section_marker = '<section class="ps-cx fechado" id="ps_limpar" hidden>'
    if card_marker not in page or section_marker not in page:
        raise ValueError('A tela de configurações precisa ser atualizada.')
    page = page.replace(card_marker, card + card_marker, 1)
    page = page.replace(section_marker, section + section_marker, 1)
    return assets(page).replace('</body>', scripts() + '</body>', 1)
