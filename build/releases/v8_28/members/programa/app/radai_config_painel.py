"""Painel inferior único de transferência de configurações."""
HTML = """
<dialog id="cfg_transfer" aria-labelledby="cfg_transfer_titulo">
 <div class="cfg-handle" aria-hidden="true"></div>
 <h2 id="cfg_transfer_titulo" tabindex="-1"></h2>
 <input type="file" id="exi_arquivo" accept=".json,application/json" hidden>
 <button type="button" id="cfg_escolher"><span aria-hidden="true" class="cfg-upload"><svg viewBox="0 0 24 24" width="26" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M6.5 18.5a5 5 0 0 1-.8-9.9 6.3 6.3 0 0 1 12.4 1.1 4.4 4.4 0 0 1-.4 8.8z"/><path d="M12 16v-6m-2.6 2.6L12 10l2.6 2.6"/></svg></span><span data-radai-frase>Escolher arquivo</span><small data-radai-frase>Arraste o arquivo JSON aqui</small></button>
 <div id="exi_previa"></div>
 <p class="msg" id="exi_msg" role="status" aria-live="polite"></p>
 <div class="linha"><button type="button" id="cfg_confirmar" class="bt pri"></button>
 <button type="button" id="cfg_cancelar" class="bt" data-radai-frase>Cancelar</button></div>
</dialog>
"""
CSS = """
#cfg_transfer{box-sizing:border-box;inset:auto 0 0;margin:0 auto;max-width:690px;width:min(100%,690px);
 max-height:82vh;overflow:auto;color:var(--text);background:var(--panel);border:1px solid var(--line-strong);
 border-radius:18px 18px 0 0;padding:12px 24px 20px;box-shadow:0 -8px 48px #0006}
#cfg_transfer[open]{animation:cfg-panel-entrar 180ms ease-out}
#cfg_transfer::backdrop{background:#080e18a6}
.cfg-handle{width:38px;height:4px;border-radius:4px;margin:0 auto 16px;background:var(--text-dim)}
#cfg_transfer h2{font-size:1.15rem;margin:0 0 16px}
#cfg_transfer [hidden]{display:none!important}
#cfg_escolher{width:100%;display:grid;justify-items:center;gap:6px;padding:20px;margin-bottom:12px;
 color:var(--text);background:var(--panel-2);border:1px solid var(--line-strong);border-radius:10px}
#cfg_escolher[data-drag]{border-color:var(--accent);background:var(--accent-fraco)}
.cfg-upload{display:grid;place-items:center;border-radius:9px;background:var(--panel);font-size:24px;width:40px;height:40px}
#cfg_transfer label{display:flex;gap:9px;align-items:center;margin:9px 0}
#cfg_transfer small{color:var(--text-muted)}
#cfg_transfer input[type=checkbox]{accent-color:var(--accent)}
#cfg_transfer input[type=checkbox]:checked{animation:cfg-check 130ms ease-out}
@keyframes cfg-panel-entrar{from{transform:translateY(30%);opacity:0}to{transform:translateY(0);opacity:1}}
@keyframes cfg-check{from{transform:scale(.82)}to{transform:scale(1)}}
@media(prefers-reduced-motion:reduce){#cfg_transfer[open],#cfg_transfer input[type=checkbox]:checked{animation:none}}
"""
JS = r"""
 const sheet = $('cfg_transfer'), preview = $('exi_previa'), fileButton = $('cfg_escolher');
 const labels = {configuracao:'Configuração da estação', nomes:'Nomes, cores e modo do STUDY',
                 protocolos:'Protocolos próprios', aparencia:'Aparência'};
 const prefKeys = ['radai_tema','radai_idioma','radai_trilho_aberto','radai_varrer_dias'];
 let operation = '', draft = null, version = '', sequence = 0, busy = false;
 function prefs(){
  const out = {};
  for(const key of prefKeys){const val=localStorage.getItem(key); if(val!==null) out[key]=val}
  return out;
 }
 function changedNames(){
  const normalize=obj=>JSON.stringify(Object.entries(obj||{}).sort((a,b)=>a[0].localeCompare(b[0])));
  return EST.carregado && (EST.modo!==EST.salvo.modo || normalize(EST.nomes)!==normalize(EST.salvo.nomes)
                          || normalize(EST.cores)!==normalize(EST.salvo.cores));
 }
 function checks(keys){
  return keys.map(k=>'<label><input type="checkbox" data-secao="'+esc(k)+'" checked>'+frase(labels[k])+'</label>').join('');
 }
 function selected(){return Array.from(preview.querySelectorAll('[data-secao]:checked'), e=>e.dataset.secao)}
 function enable(){
  $('cfg_confirmar').disabled=busy || (operation==='importar' && !version) || !selected().length;
 }
 function showError(error){texto($('exi_msg'),error.message||'Não consegui ler o arquivo.','ruim')}
 function openSheet(mode){
  operation=mode; draft=null; version=''; sequence++; busy=false;
  const title=mode==='exportar'?'Exportar configurações':'Importar configurações';
  texto($('cfg_transfer_titulo'),title); texto($('cfg_confirmar'),mode==='exportar'?'Exportar configurações':'Importar o que está marcado');
  texto($('exi_msg'),''); fileButton.hidden=mode==='exportar';
  preview.innerHTML=mode==='exportar'?checks(Object.keys(labels)):'';
  enable(); retraduzir(); sheet.showModal(); $('cfg_transfer_titulo').focus();
 }
 $('exi_exportar').onclick=()=>openSheet('exportar');
 $('exi_importar').onclick=()=>openSheet('importar');
 $('cfg_cancelar').onclick=()=>sheet.close();
 sheet.addEventListener('close',()=>{sequence++;draft=null; version=''});
 fileButton.onclick=()=>$('exi_arquivo').click();
 for(const ev of ['dragenter','dragover','dragleave','drop']) fileButton.addEventListener(ev,e=>{
   e.preventDefault(); fileButton.toggleAttribute('data-drag',ev==='dragenter'||ev==='dragover');
   if(ev==='drop' && e.dataTransfer.files.length) readFile(e.dataTransfer.files[0]);
 });
 $('exi_arquivo').onchange=e=>{const file=e.target.files[0];e.target.value='';if(file)readFile(file)};
 preview.onchange=enable;
 async function inspect(doc){
  const request=++sequence;
  version=''; preview.replaceChildren();enable();
  const d=await pedir('/api/config/importar/previa',{dados:doc,aparencia:prefs()});
  if(request!==sequence)return;
  if(!d||!d.ok)throw Error((d||{}).erro||'Não consegui ler o arquivo.');
  draft=doc;version=d.revisao;
  let rows=checks(d.secoes);
  const custom=d.personalizadas||{};
  for(const group of [['novos','Protocolos a adicionar'],['iguais','Protocolos idênticos'],['conflitos','Protocolos diferentes']]){
   const list=custom[group[0]]||[];
   if(list.length)rows+='<p>'+frase(group[1])+' · '+list.map(v=>esc(v.nome)+' ('+esc(v.modalidade)+')').join(', ')+'</p>';
  }
  if(custom.conflitos && custom.conflitos.length) rows+='<label><input id="cfg_trocar_protocolos" type="checkbox">'+frase('Substituir pelos do arquivo')+'</label>';
  if(custom.perguntar_nomes) rows+='<label><input id="cfg_trocar_nomes" type="checkbox">'+frase('Usar as do arquivo')+'</label>';
  for(const item of (d.configuracao||{}).itens||[]){
   if(item.muda||item.aviso)rows+='<p><code>'+esc(item.chave)+'</code> · '+esc(item.atual)+' → '+esc(item.novo)+(item.aviso?' · '+frase(item.aviso):'')+'</p>';
  }
  preview.innerHTML=rows;texto($('exi_msg'),'');retraduzir();enable();
 }
 async function readFile(file){
  try{
   if(file.size>2*1024*1024)throw Error('este arquivo não é uma exportação das configurações');
   const doc=JSON.parse((await file.text()).replace(/^\uFEFF/,''));await inspect(doc);
  }catch(err){draft=null;version='';preview.replaceChildren();enable();showError(err)}
 }
 function applyPrefs(values,restore=false){
  for(const key of prefKeys){
   if(key in values)localStorage.setItem(key,values[key]);
   else if(restore)localStorage.removeItem(key);
  }
 }
 $('cfg_confirmar').onclick=async()=>{
  if(busy || !selected().length)return;
  busy=true;enable();
  try{
   if(operation==='exportar'){
    const doc=await pedir('/api/config/exportar',{secoes:selected(),aparencia:prefs()});
    if(!doc||!doc.formato)throw Error((doc||{}).erro||'Não consegui exportar.');
    baixarConfiguracoes(doc,'local_suite_');sheet.close();texto($('msg'),'O arquivo foi para a pasta de downloads do navegador.','ok');
   }else{
    if(PROT.ed||changedNames())throw Error('Salve ou descarte a edição em andamento antes de importar.');
    const body={dados:draft,secoes:selected(),revisao:version,aparencia:prefs(),
      substituir_nomes:!!($('cfg_trocar_nomes')||{}).checked,substituir_protocolos:!!($('cfg_trocar_protocolos')||{}).checked};
    const r=await fetch('/api/config/importar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    const d=await r.json();
    if(r.status===409){await inspect(draft);throw Error(d.erro)}
    if(!r.ok||!d.ok)throw Error(d.erro||'Não consegui importar.');
    applyPrefs(d.aparencia||{});sessionStorage.setItem('radai_config_importada','1');location.reload();
   }
  }catch(e){showError(e)}finally{busy=false;enable()}
 };
 $('cfg_desfazer').onclick=async function(){
  this.disabled=true;
  try{const d=await pedir('/api/config/importar/desfazer',{});
   if(!d||!d.ok)throw Error((d||{}).erro||'Não consegui importar.');
   applyPrefs(d.aparencia||{},true);sessionStorage.removeItem('radai_config_importada');location.reload();
  }catch(e){texto($('msg'),e.message,'ruim');this.disabled=false}
 };
 if(sessionStorage.getItem('radai_config_importada')==='1'){$('cfg_desfazer').hidden=false;texto($('msg'),'Importado.','ok')}
 window.radaiSalvarEstacao=async function(){
  if(!window.DADOS || $('btsalvar').disabled)return;
  const btn=$('btsalvar');btn.disabled=true;
  try{
   const valores={};for(const k of DADOS.chaves||[]){
    const input=$('f_'+k);if(input)valores[k]=input.hasAttribute('data-bool')?(input.checked?'1':'0'):input.value;
   }
   if(anelEditado)valores.TPS_DESTINO=ANEL;
   const body={valores,aparencia:prefs()};
   if(changedNames())body.nomes={modo:EST.modo,nomes:EST.nomes,cores:EST.cores};
   if(PROT.ed)body.protocolo=Object.assign({},PROT.ed,{nome:$('prot_nome').value,modalidade:$('prot_modal').value});
   const d=await pedir('/api/config/estacao/salvar',body);
   if(!d||!d.ok){
    if(d&&d.secao==='protocolos')protErros(d.erros||{});
    if(d&&d.secao==='nomes'){EST.erros=d.erros||{};estPintar()}
    throw Error((d||{}).erro||'Nada foi gravado: confira os campos marcados.');
   }
   anelEditado=false;
   if(body.protocolo){protFechar();protCarregar()}
   if(body.nomes){EST.salvo={modo:EST.modo,nomes:copia(EST.nomes),cores:copia(EST.cores)};estPintar();resumo()}
   if(d.salvos.length){$('btrei_cfg').style.display='';carregar(true)}
   texto($('msg'),d.nada_mudou?'Nada mudou.':'Gravado: vale para a próxima série.','ok');
  }catch(err){texto($('msg'),err.message,'ruim')}finally{btn.disabled=false}
 };
"""
