"""Offline controls and monitor for the dedicated queue session."""
CSS = r"""<style id="radai-dedicado-css">
#ded-escolha[hidden],#ded-plano[hidden],#ded-retomar[hidden],#ded-fim[hidden],#ded-aviso[hidden]{display:none}
#ded-escolha{padding:12px 14px;margin-block:12px;border:1px solid var(--line,#2a3a55);border-radius:10px}
#ded-escolha [hidden],#ded-tela [hidden]{display:none!important}
#ded-tela .ded-visual{display:grid;place-items:center}#ded-tela .ded-visual>*{grid-area:1/1}
#ded-tela .ded-visual span{font-weight:600;color:#e7efff;max-width:18ch}
#ded-lista-nav{padding-inline-start:1.25rem}
#ded-escolha label{display:flex;align-items:center;gap:.7em;line-height:1.5;cursor:pointer}
#ded-escolha input{accent-color:var(--accent,#4da3ff)}
#ded-escolha .ded-opcao{font-weight:600}
#ded-plano{max-height:min(48dvh,450px);overflow:auto}#ded-itens{display:grid;gap:6px;margin-block:8px}
#ded-plano p{margin:6px 0}
#ded-escolha .ded-alerta{color:var(--warn,#e1b23b)}
#ded-retomar{position:fixed;inset-block-start:54px;inset-inline-end:24px;z-index:3000}
#ded-tela{box-sizing:border-box;width:100vw;height:100dvh;max-width:none;max-height:none;margin:0;padding:clamp(16px,3vw,44px);border:0;color:#e6edf7;background:radial-gradient(ellipse at 50% 42%,#18283f 0,#0c1627 42%,#0a1120 80%);font-family:inherit}
#ded-tela[open]{display:grid;grid-template-rows:auto 1fr auto;gap:16px}
#ded-tela::backdrop{background:#0a1120}
#ded-tela header,#ded-tela footer{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:10px}
#ded-tela h2{font:inherit;font-weight:600;font-size:clamp(14px,2vw,20px);color:#a3b1c6;margin:0}
#ded-tela .ded-marca{color:#e6edf7;font-weight:700;letter-spacing:-.03em}
#ded-tela .ded-centro{text-align:center;align-self:center;min-height:0;overflow:auto}
#ded-tela canvas{display:block;margin:auto;width:min(46vmin,290px);height:auto;aspect-ratio:1}
#ded-fase{margin:0;font-weight:600;font-size:clamp(21px,3.5vw,38px);overflow-wrap:anywhere}
#ded-pensa,#ded-metrica,#ded-historico{color:#a3b1c6}
#ded-pensa{min-height:2.6em;margin-block:10px;line-height:1.45}
#ded-pensa .ui-pensa{min-height:2.6em}
#ded-metrica bdi{font-variant-numeric:tabular-nums}
#ded-historico{font-family:var(--font-mono,monospace);padding:0;margin:8px 0;list-style:none;font-size:.82em}
#ded-fim,#ded-aviso{background:#121d2d;border:1px solid #374963;border-radius:8px;padding:10px 14px}
#ded-tela button,#ded-retomar{color:#e6edf7;background:#18263a;border:1px solid #435671;border-radius:7px;font:inherit;padding:.52em .9em;cursor:pointer}
#ded-tela button:focus-visible,#ded-retomar:focus-visible{outline:2px solid #4da3ff;outline-offset:3px}
#ded-tela .ded-botoes{display:flex;flex-wrap:wrap;gap:8px}
@media(max-height:500px){#ded-tela canvas{width:min(29vmin,135px)}#ded-tela[open]{gap:4px}#ded-historico{display:none}}
@media(prefers-reduced-motion:reduce){#ded-pensa *,#ded-pensa *::before{animation:none!important;transition:none!important;filter:none!important;transform:none!important}}
</style>"""
BUTTON = '<button type="button" id="radai_rev_ded" hidden data-radai-frase>Modo de processamento dedicado</button>'
CHOICE = r"""<section id="ded-escolha" hidden>
 <div id="ded-plano" hidden><p class="ded-alerta" data-radai-frase>Salve todos os trabalhos abertos antes de continuar.</p>
 <p id="ded-externos" hidden data-radai-frase>Os aplicativos da lista abaixo podem ser fechados.</p>
 <p id="ded-perfil" data-radai-frase>O navegador da Local Suite permanece aberto.</p>
 <p id="ded-shell" hidden data-radai-frase>O Explorer não está disponível para reabrir aplicativos. Eles permanecerão abertos.</p>
 <p id="ded-admin" class="ded-alerta" hidden data-radai-frase>Sem permissão de administrador. Nenhum serviço será pausado.</p>
 <p id="ded-desconhecidos" hidden data-radai-frase>Revise os programas desconhecidos antes de selecioná-los.</p>
 <div id="ded-itens"></div><label id="ded-grupo-nav" hidden><input type="checkbox" id="ded-navegadores" checked><span data-radai-frase>Outros navegadores</span></label><div id="ded-lista-nav"></div>
 <p id="ded-preservados" hidden><span data-radai-frase>Permanecem abertos</span> · <bdi></bdi></p>
 <p id="ded-servidor" class="ded-alerta" hidden data-radai-frase>Esta estação hospeda serviços usados por outros computadores.</p>
 <p id="ded-memoria" hidden><span data-radai-frase>Memória estimada das ações selecionadas</span> · <bdi></bdi></p><p id="ded-plano-status" role="status"></p>
 <p data-radai-frase>A tela cheia acompanha a fila. Use Esc para sair do modo dedicado.</p>
 <button type="button" id="ded-rever" hidden data-radai-frase>Tentar novamente</button></div>
</section>"""
MONITOR = r"""<button type="button" id="ded-retomar" hidden data-radai-frase>Modo de processamento dedicado</button>
<dialog id="ded-tela" aria-labelledby="ded-titulo">
 <header><span class="ded-marca" translate="no">Local Suite</span><h2 id="ded-titulo" data-radai-frase>Modo de processamento dedicado</h2></header>
 <div class="ded-centro">
  <div class="ded-visual" aria-hidden="true"><canvas id="ded-anel" width="340" height="340"></canvas><span data-radai-frase>Processando</span></div>
  <p id="ded-fase" role="status" aria-live="polite"></p><div id="ded-pensa" aria-hidden="true"></div>
  <p id="ded-metrica"><bdi></bdi></p><ul id="ded-historico"></ul>
  <div id="ded-resumo"><p id="ded-manter" hidden><span data-radai-frase>Permanecem abertos</span> · <bdi></bdi></p><p id="ded-manuais" hidden><span data-radai-frase>Reabertura manual</span> · <bdi></bdi></p></div>
  <p id="ded-aviso" hidden role="status"></p>
 </div>
 <footer><button id="ded-reabrir" type="button" hidden data-radai-frase>Reabrir</button><button id="ded-cheia" type="button" data-radai-frase>Entrar em tela cheia</button>
 <div class="ded-botoes"><button id="ded-voltar" type="button" data-radai-frase>Voltar ao painel</button>
 <button id="ded-sair" type="button" data-radai-frase>Encerrar modo dedicado</button></div>
 <div id="ded-fim" hidden><p data-radai-frase>A fila continua rodando. Os serviços voltam agora. Os programas fechados podem ser reabertos no resumo.</p>
 <button id="ded-cancelar-saida" type="button" data-radai-frase>Cancelar</button>
 <button id="ded-confirmar-saida" type="button" data-radai-frase>Encerrar modo dedicado</button></div>
 </footer>
</dialog>
<script id="radai-dedicado-js">
(function(){
 'use strict';
 if(window.radaiDedicado) return;
 const el=id=>document.getElementById(id), tela=el('ded-tela'), botao=el('radai_rev_ok');
 const base='/api/estacao/dedicado/';
 const fases={preparing:'Preparando a estação…',ready_wait:'Aguardando o motor de processamento…',
  input:'Lendo os dados de entrada…',loading_model:'Carregando o modelo…',inference:'Segmentando…',
  postprocessing:'Aplicando o pós-processamento…',writing_output:'Gravando os arquivos de saída…',
  paused:'Processamento pausado.',restoring:'Restaurando a estação…',completed:'Fila concluída',
  partial:'Preparo parcial.',returned:'Estação devolvida.',failed:'Não foi possível concluir.'};
 const movimento=window.matchMedia('(prefers-reduced-motion: reduce)');
 let oferta=false,habilitado=false,bloqueado=false,geracao=0,plano=null,promessa=false;
 let estado=null,lendo=false,timer=0,ultimo='',historico=[],pensa=null,anel=null,ultimoLog=0;
 let volta=null,fechando=false,negativa=false,aguardandoRevisao=false;
 const tr=chave=>window.radaiFrase?window.radaiFrase(chave):chave;
 function frase(no,chave){
  if(no.dataset.dedFrase===chave && no.textContent===tr(chave)) return;
  no.dataset.dedFrase=chave;
  if(window.uiTexto)window.uiTexto(no,tr(chave));else no.textContent=tr(chave);
  no.setAttribute('data-radai-t','1');
 }
 function aviso(chave){
  const no=el('ded-aviso'); no.hidden=!chave;
  if(chave) frase(no,chave);
 }
 async function api(rota,body){
  const opt={cache:'no-store',credentials:'same-origin'};
  if(body!==undefined){opt.method='POST';opt.headers={'Content-Type':'application/json'};opt.body=JSON.stringify(body)}
  const r=await fetch(base+rota,opt);
  const d=await r.json();
  if(!r.ok||!d||d.ok===false)throw new Error(String(d?.motivo||r.status));
  return d;
 }
 function prepararBotao(){
  if(!el('ded-escolha'))return;
  const ligado=habilitado;
  el('ded-escolha').hidden=!ligado;el('ded-plano').hidden=!ligado;
  el('radai_rev_ded').hidden=!oferta||ligado;el('radai_rev_ded').disabled=bloqueado||promessa;
  el('radai_rev_corpo').hidden=ligado;el('radai_rev_sub').hidden=ligado;
  frase(el('radai_rev_nao'),ligado?'Voltar':'Cancelar');
  botao.disabled=bloqueado || (ligado && (!plano || promessa));
  const texto=bloqueado?'Não dá para começar agora':ligado?'Já salvei. Iniciar em modo dedicado':'Começar a segmentar a fila agora';
  frase(botao,texto);
 }
 function memoria(){
  let mb=0;
  for(const ck of el('ded-escolha').querySelectorAll('input[data-item]:checked:not(:disabled)')){
   const valor=Number(ck.dataset.memoria);if(Number.isFinite(valor)&&valor>0)mb+=valor;
  }
  const box=el('ded-memoria');box.hidden=!mb;
  box.querySelector('bdi').textContent=(mb/1024).toLocaleString(document.documentElement.lang||undefined,{maximumFractionDigits:2})+' GiB';
 }
 function navegadores(){
  const ligado=el('ded-navegadores').checked;
  for(const ck of el('ded-lista-nav').querySelectorAll('input'))ck.disabled=!ligado;
  memoria();
 }
 async function prever(){
  const vez=++geracao;
  plano=null;el('ded-itens').replaceChildren();el('ded-externos').hidden=true;
  el('ded-lista-nav').replaceChildren();el('ded-grupo-nav').hidden=true;
  for(const id of ['ded-preservados','ded-servidor','ded-memoria','ded-admin','ded-desconhecidos','ded-shell'])el(id).hidden=true;
  el('ded-navegadores').checked=true;
  el('ded-rever').hidden=true;frase(el('ded-plano-status'),'Preparando a estação…');prepararBotao();
  try{
   const p=await api('prever',{});
   if(vez!==geracao || !habilitado) return;
   if(p.disponivel===false||typeof p.token!=='string'||!p.token) throw new Error('indisponivel');
   const itens=Array.isArray(p.itens)?p.itens:[];
   for(const item of itens){
    if(typeof item.id!=='string'||typeof item.nome!=='string') continue;
    const label=document.createElement('label'), ck=document.createElement('input'),nome=document.createElement('bdi');
    ck.type='checkbox';ck.value=item.id;ck.checked=item.selecionado===true;
    ck.dataset.item='1';ck.dataset.memoria=item.tipo==='app'?Number(item.memoria_mb)||0:0;
    nome.textContent=item.nome;label.append(ck,nome);
    const detalhes=[];
    if(Number.isInteger(item.janelas)&&item.janelas>=0)detalhes.push(tr('Janelas')+' '+item.janelas);
    if(Number.isFinite(item.memoria_mb)&&item.memoria_mb>0)detalhes.push(Number(item.memoria_mb).toLocaleString(document.documentElement.lang)+' MiB');
    if(detalhes.length){const info=document.createElement('bdi');info.textContent=detalhes.join(' · ');label.append(info)}
    if(item.conhecido===false)el('ded-desconhecidos').hidden=false;
    const classe={memoria:'Compactar memória',prioridade:'Reduzir prioridade',servico:'Pausar serviço',app:'Fechar aplicativo'}[item.tipo];
    if(classe){const acao=document.createElement('small');frase(acao,classe);label.append(acao)}
    el(item.navegador===true||item.tipo==='navegador'?'ded-lista-nav':'ded-itens').append(label);
   }
   el('ded-grupo-nav').hidden=!el('ded-lista-nav').childElementCount;
   el('ded-externos').hidden=!el('ded-itens').childElementCount && el('ded-grupo-nav').hidden;
   const mantidos=Array.isArray(p.preservados)?p.preservados.map(x=>typeof x==='string'?x:x.nome).filter(x=>typeof x==='string'&&x):[];
   el('ded-preservados').hidden=!mantidos.length;el('ded-preservados').querySelector('bdi').textContent=mantidos.map(tr).join(', ');
   el('ded-servidor').hidden=p.hospeda_servicos!==true;
   el('ded-admin').hidden=(p.administrador??p.admin)!==false;
   el('ded-shell').hidden=p.sem_shell!==true;
   navegadores();
   plano=p;el('ded-plano-status').textContent='';
  }catch(err){
   if(vez!==geracao) return;
   frase(el('ded-plano-status'),'Confira novamente a prévia do modo dedicado.');
   el('ded-rever').hidden=false;
  }
  prepararBotao();
 }
 function revisar(aberto,ocupada){
  if(!el('ded-escolha'))return;
  ++geracao;oferta=!!aberto;habilitado=false;bloqueado=!!ocupada;plano=null;
  prepararBotao();
 }
 function fecharRevisao(){
  ++geracao;oferta=false;habilitado=false;plano=null;
  if(el('ded-escolha')){el('ded-escolha').hidden=true;el('radai_rev_ded').hidden=true}
  el('radai_rev_corpo').hidden=false;el('radai_rev_sub').hidden=false;
 }
 function voltar(){
  if(!habilitado)return false;
  ++geracao;habilitado=false;plano=null;prepararBotao();el('radai_rev_ded').focus();return true;
 }
 el('ded-escolha')?.addEventListener('change',memoria);
 el('ded-navegadores')?.addEventListener('change',navegadores);
 el('radai_rev_ded')?.addEventListener('click',()=>{
  if(oferta&&!bloqueado&&!promessa){habilitado=true;prever();el('radai_rev_nao').focus()}
 });
 el('ded-rever')?.addEventListener('click',prever);
 function iniciarArte(){
  if(anel)anel.parar();anel=null;
  if(tela.open&&!document.hidden&&window.uiAnel)anel=window.uiAnel(el('ded-anel'),{estatico:!!estado&&!estado.ativo&&!promessa});
 }
 function mostrar(){
  if(!tela.open){
   volta=document.activeElement;tela.showModal();el('ded-cheia').focus();iniciarArte();
  }
  el('ded-retomar').hidden=true;
 }
 function esconder(){
  if(!tela.open)return;
  aguardandoRevisao=false;if(document.fullscreenElement)document.exitFullscreen().catch(()=>{});
  tela.close();if(anel)anel.parar();anel=null;
  if(pensa)pensa.parar();pensa=null;el('ded-fim').hidden=true;
  el('ded-retomar').hidden=!(estado?.ativo||estado?.restauracao_pendente||estado?.reabrir?.length);
  const alvo=el('ded-retomar').hidden?volta:el('ded-retomar');
  if(alvo&&alvo.isConnected)alvo.focus();
 }
 function cheia(){
  if(document.fullscreenElement){document.exitFullscreen().catch(()=>{});return}
  if(!document.documentElement.requestFullscreen){negativa=true;aviso('Tela cheia indisponível.');return}
  try{document.documentElement.requestFullscreen().catch(()=>{negativa=true;aviso('Tela cheia indisponível.')})}
  catch(e){negativa=true;aviso('Tela cheia indisponível.')}
 }
 function desenhar(d){
  if(d.sessao && d.sessao===estado?.sessao && Number.isInteger(d.seq) && d.seq<estado.seq)return;
  const mudouAtivo=estado?.ativo!==d.ativo;
  if(d.sessao!==estado?.sessao){historico=[];ultimo='';ultimoLog=0;fechando=false}
  estado=d;if(mudouAtivo&&tela.open)iniciarArte();
  const final=!d.ativo,pendente=!!d.restauracao_pendente;
  if(!final||pendente){
   if(!tela.open && d.sessao)mostrar();
   el('ded-retomar').hidden=tela.open;
  } else el('ded-retomar').hidden=tela.open||!d.reabrir?.length;
  if(!tela.open)return;
  if(final&&!pendente&&d.sessao&&document.fullscreenElement)document.exitFullscreen().catch(()=>{});
  if(final&&!pendente&&!d.sessao){if(!promessa&&!aguardandoRevisao)esconder();return}
  const fase=fases[d.fase]||'Processando';
  const evento=fases[d.evento];
  const identificado=d.sessao+'|'+String(d.seq)+'|'+d.fase;
  if(ultimo!==identificado){
   ultimo=identificado;
   const linha=evento||fase;
   if(historico[historico.length-1]!==linha)historico.push(linha);
   historico=historico.slice(-3);
  }
  frase(el('ded-fase'),fase);aviso(pendente?'Restauração pendente.':negativa?'Tela cheia indisponível.':'');
  el('ded-historico').replaceChildren(...historico.map(k=>{const li=document.createElement('li');frase(li,k);return li}));
  if(!pensa&&window.uiPensando)pensa=window.uiPensando(el('ded-pensa'),{segurarMs:4800});
  const linha=evento||historico[historico.length-2];
  const seguras=Array.isArray(d.prints_seguros)?d.prints_seguros.filter(x=>typeof x==='string'&&x.length&&x.length<=200).slice(-3):[];
  if(seguras.length){
   el('ded-historico').replaceChildren(...seguras.map(s=>{const li=document.createElement('li');li.translate=false;li.setAttribute('data-radai-t','1');li.textContent=s;return li}));
  }
  if(Number.isSafeInteger(d.log_seq)&&d.log_seq>ultimoLog){
   ultimoLog=d.log_seq;
   if(seguras.length&&anel&&!document.hidden)anel.pulso();
  }
  const recente=seguras.length?{t:seguras[seguras.length-1],cru:true}:linha;
  if(pensa)pensa.dizer(!movimento.matches&&recente&&recente!==fase?[fase,recente]:[]);
  const metr=el('ded-metrica').firstElementChild;
  const contagens=[];
  if(Number.isInteger(d.feitas)&&Number.isInteger(d.total)&&d.total>0 && d.feitas>=0&&d.feitas<=d.total)
   contagens.push(d.feitas+' / '+d.total);
  for(const [ch,v] of [['Ações aplicadas',d.aplicados],['Ações puladas',d.pulados],['Ações pendentes',d.pendentes]]){
   if(Number.isInteger(v)&&v>0)contagens.push(tr(ch)+' '+v);
  }
  for(const [ch,v] of [['Memória livre',d.memoria_livre_gb],['Variação de memória livre',d.ganho_memoria_gb],['VRAM',d.vram_livre_gb]]){
   if(Number.isFinite(v)) contagens.push(tr(ch)+' '+v.toLocaleString(document.documentElement.lang||undefined,{maximumFractionDigits:1})+' GB');
  }
  if(Number.isInteger(d.servicos_restaurados)&&final)contagens.push(tr('Serviços restaurados')+' '+d.servicos_restaurados);
  metr.textContent=contagens.join(' · ');
  for(const [id,items] of [['ded-manter',d.ficaram_abertos],['ded-manuais',d.reabrir]]){
   const no=el(id),nomes=Array.isArray(items)?items.map(i=>typeof i==='string'?i:i.nome).filter(v=>typeof v==='string'&&v):[];
   no.hidden=!final||!nomes.length;no.querySelector('bdi').textContent=nomes.join(', ');
  }
  el('ded-voltar').hidden=!final&&!pendente;
  el('ded-reabrir').hidden=!final||!Array.isArray(d.reabrir)||!d.reabrir.length;
  el('ded-sair').hidden=final&&!pendente;el('ded-sair').disabled=fechando||d.fase==='restoring';
  frase(el('ded-sair'),pendente?'Retomar restauração':'Encerrar modo dedicado');
 }
 function agendar(ms){clearTimeout(timer);timer=setTimeout(ler,ms)}
 async function ler(){
  if(lendo)return;lendo=true;
  try{desenhar(await api('estado'))}
  catch(err){if(tela.open)aviso('Conexão perdida. Tentando novamente…')}
  finally{lendo=false;if(!document.hidden && (estado?.ativo||estado?.restauracao_pendente||tela.open))agendar(1000)}
 }
 async function entrar(carga){
  try{
   const d=await api('entrar',carga);
   if(d.sessao)desenhar(d);
   await ler();
  }catch(err){
   // Delivery of a POST can precede loss of its response. Observe the server
   // before deciding whether another preview is needed. Never start normally here.
   let d;
   try{d=await api('estado')}catch(e){}
   if(d?.ativo||d?.restauracao_pendente){desenhar(d);agendar(500)}
   else {estado=d||null;aguardandoRevisao=true;aviso('Confira novamente a prévia do modo dedicado.');el('ded-sair').hidden=true;el('ded-voltar').focus()}
  }finally{promessa=false}
 }
 function confirmar(){
  if(!habilitado)return false;
  if(bloqueado||!plano||promessa)return true;
  promessa=true;
  const carga={consentido:true,token:plano.token,itens:[...el('ded-escolha').querySelectorAll('input[data-item]:checked:not(:disabled)')].map(i=>i.value)};
  radaiRevFechar();negativa=false;aguardandoRevisao=false;el('ded-sair').hidden=true;
  mostrar();frase(el('ded-fase'),'Preparando a estação…');aviso('');cheia();entrar(carga);
  return true;
 }
 async function sair(){
  if(!estado?.sessao||fechando)return;
  fechando=true;el('ded-fim').hidden=true;el('ded-sair').disabled=true;
  try{await api('sair',{sessao:estado.sessao});await ler()}
  catch(err){aviso('Conexão perdida. Tentando novamente…');agendar(700)}
  finally{fechando=false}
 }
 function solicitarSaida(){
  if(estado?.restauracao_pendente){sair();return}
  if(!estado?.ativo){esconder();return}
  el('ded-fim').hidden=false;el('ded-cancelar-saida').focus();
 }
 el('ded-sair').addEventListener('click',solicitarSaida);
 el('ded-cancelar-saida').addEventListener('click',()=>{el('ded-fim').hidden=true;el('ded-sair').focus()});
 el('ded-confirmar-saida').addEventListener('click',sair);
 el('ded-reabrir').addEventListener('click',async function(){
  if(this.disabled||!estado?.sessao)return;this.disabled=true;
  try{await api('reabrir',{sessao:estado.sessao,itens:estado.reabrir.map(x=>x.id)});await ler()}
  catch(err){aviso('Conexão perdida. Tentando novamente…')}
  finally{this.disabled=false}
 });
 el('ded-voltar').addEventListener('click',esconder);
 el('ded-retomar').addEventListener('click',()=>{mostrar();ler()});
 el('ded-cheia').addEventListener('click',cheia);
 tela.addEventListener('cancel',e=>{e.preventDefault();if(!el('ded-fim').hidden){el('ded-cancelar-saida').click();return}solicitarSaida()});
 document.addEventListener('fullscreenchange',()=>{frase(el('ded-cheia'),document.fullscreenElement?'Sair da tela cheia':'Entrar em tela cheia')});
 movimento.addEventListener('change',()=>{iniciarArte();if(estado)desenhar(estado)});
 document.addEventListener('visibilitychange',()=>{
  iniciarArte();
  if(document.hidden){clearTimeout(timer);if(pensa){pensa.parar();pensa=null}}
  else ler();
 });
 window.addEventListener('pageshow',ler);
 window.addEventListener('focus',()=>{if(!promessa)ler()});
 window.radaiDedicado={revisar,fecharRevisao,confirmar,voltar};
 window.addEventListener('pagehide',()=>{clearTimeout(timer);if(anel)anel.parar();if(pensa)pensa.parar()});
 agendar(0);
})();
</script>"""
