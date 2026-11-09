# -*- coding: utf-8 -*-
import json

import radai_config

TETO_DO_CORPO = 2 * 1024 * 1024

MARCA_GERAL = u"@GERAL_ESTACAO@"
MARCA_SECAO = u"@SECAO_ESTRUTURAS@"
MARCA_CSS = u"@CSS_ESTACAO@"
MARCA_JS = u"@JS_ESTACAO@"
MARCAS = (MARCA_GERAL, MARCA_SECAO, MARCA_CSS, MARCA_JS)

GERAL = u"""
  <div class="est-bloco">
   <div class="est-rot" data-radai-frase>Pasta favorita</div>
   <p class="est-frase" data-radai-frase>Escolha ou altere a pasta usada como ponto de partida.</p>
   <p class="est-atual" id="fav_atual" hidden><code id="fav_caminho" data-radai-t="1" translate="no"></code></p>
   <div class="linha"><a class="ui-bt op" id="cfgFavorita" href="/primeiro-uso?de=/config" data-radai-frase>Configurar pasta favorita</a></div>
  </div>

  <div class="est-bloco">
   <div class="est-rot" id="an_rot"><span data-radai-frase>Ajuste de contornos em anel</span><span class="est-tag" data-radai-frase>Opcional</span><span class="ui-ajuda" tabindex="0" aria-label="ajuda">?<span class="ui-balao"><p><b>Eclipse / Monaco</b>: o furo de um contorno em anel sai como um segundo contorno, dentro do primeiro.</p><p><b>Xio / Focal</b>: o furo é ligado à borda por uma linha divisória estreita, para o sistema que não lê o furo como contorno separado.</p><p>Nos dois, o RTSTRUCT e o que o DicomBridge exporta saem em Implicit VR Little Endian, a sintaxe de transferência padrão do DICOM.</p></span></span></div>
   <div class="an-ops" role="radiogroup" aria-labelledby="an_rot">
    <button class="an-op" type="button" role="radio" data-tps="eclipse" aria-checked="false" tabindex="0"><b translate="no">Eclipse / Monaco</b><span data-radai-frase>Anel sem linha divisória</span></button>
    <button class="an-op" type="button" role="radio" data-tps="monaco" aria-checked="false" tabindex="-1"><b translate="no">Xio / Focal</b><span data-radai-frase>Versões anteriores, ou outros que precisem de linha divisória nos anéis</span></button>
   </div>
   <p class="msg est-msg" id="an_msg" aria-live="polite"></p>
  </div>

  <div class="est-bloco" id="gu_bloco" hidden>
   <div class="est-rot" data-radai-frase>Guia inicial</div>
   <div class="linha"><button class="ui-bt op" type="button" id="gu_ver" data-radai-frase>Ver o guia de novo</button></div>
  </div>

  <div class="est-bloco">
   <div class="est-rot"><span data-radai-frase>Levar estas configurações para outra máquina</span><span class="ui-ajuda" tabindex="0" aria-label="ajuda">?<span class="ui-balao"><p><b>Viajam</b> a configuração desta estação, os nomes próprios das estruturas e os protocolos próprios, num arquivo .json.</p><p><b>Não viajam</b> a placa de vídeo, o dispositivo e a porta, que são desta máquina, nem a chave do pseudônimo, o acervo e a fila.</p><p>Ao importar, você marca as seções; caminho que não existe na outra máquina é avisado e não é gravado.</p></span></span></div>
   <div class="linha">
    <button class="ui-bt op" type="button" id="exi_exportar" data-radai-frase>Exportar configurações</button>
    <button class="ui-bt op" type="button" id="exi_importar" data-radai-frase>Importar configurações…</button>
    <input type="file" id="exi_arquivo" accept=".json,application/json" hidden>
   </div>
   <div class="exi-previa" id="exi_previa" hidden></div>
   <p class="msg est-msg" id="exi_msg" aria-live="polite"></p>
  </div>
"""

SECAO = u"""
<section class="ps-cx fechado" id="ps_estruturas" hidden>
 <h2 class="ps-cab" tabindex="0" role="button"><span class="ps-num">5</span>
  <span data-radai-frase>Estruturas e Protocolos</span>
  <span class="ps-sub" id="sub_estruturas">&#8212;</span><span class="ui-ajuda" tabindex="0" aria-label="ajuda">?<span class="ui-balao"><p><b>Os nomes próprios valem só no STUDY</b>, o conjunto entregue. O FULL continua com os nomes padrão, que as outras telas leem.</p><p>Cada estrutura do STUDY guarda o nome padrão na descrição, com «sugestão IA não aprovada».</p><p>Um protocolo próprio escolhe as estruturas do STUDY no PERSONALIZADO do «Rodar agora». O vigia continua no AUTO.</p></span></span>
  <span class="ps-seta">&#9662;</span></h2>
 <div class="ps-corpo">
  <h4 class="cfg-sub" data-radai-frase>Nomes no STUDY</h4>
  <div class="est-barra">
   <select id="est_modo" data-ui-seg aria-label="Nomes no STUDY">
    <option value="padrao">Padrão</option>
    <option value="proprios">Tags próprias</option>
   </select>
   <select id="est_modal" data-ui-seg aria-label="Modalidade">
    <option value="CT">TC</option>
    <option value="MR">RM</option>
   </select>
   <input type="search" id="est_filtro" class="est-filtro" spellcheck="false" autocomplete="off" placeholder="filtrar por nome ou task" aria-label="filtrar por nome ou task">
   <label class="est-todas"><input type="checkbox" id="est_todas"><span data-radai-frase>Mostrar também as que só saem no FULL</span></label>
  </div>
  <p class="est-frase" id="est_nota"></p>
  <div class="est-tabela-cx" id="est_cx" aria-busy="true">
   <table class="est-tabela">
    <thead><tr><th scope="col" data-radai-frase>Task</th><th scope="col" data-radai-frase>Nome anatômico</th><th scope="col" data-radai-frase>Nome no STUDY</th><th scope="col" id="est_h_proprio" data-radai-frase>Nome próprio</th><th scope="col" id="est_h_cor" data-radai-frase>Cor no STUDY</th></tr></thead>
    <tbody id="est_corpo"><tr><td colspan="5" class="est-vazio"><span data-radai-frase>Abrindo a lista de estruturas…</span></td></tr></tbody>
   </table>
  </div>
  <div class="linha est-acoes">
   <button class="bt pri" type="button" id="est_salvar" data-radai-frase>Salvar os nomes</button>
   <span class="msg est-msg" id="est_msg" aria-live="polite"></span>
  </div>

  <h4 class="cfg-sub" data-radai-frase>Protocolos próprios</h4>
  <p class="est-frase" data-radai-frase>Cada protocolo é uma seleção do STUDY, com uniões, para uma modalidade.</p>
  <div class="prot-lista" id="prot_lista"></div>
  <div class="linha"><button class="bt" type="button" id="prot_novo" data-radai-frase>Novo protocolo</button><span class="msg est-msg" id="prot_lista_msg" aria-live="polite"></span></div>
  <div class="prot-editor" id="prot_editor" hidden>
   <div class="prot-campos">
    <div class="prot-campo">
     <label for="prot_nome" data-radai-frase>Nome do protocolo</label>
     <input id="prot_nome" type="text" maxlength="60" spellcheck="false" autocomplete="off">
     <div class="est-erro" id="prot_e_nome"></div>
    </div>
    <div class="prot-campo">
     <div class="est-rot" data-radai-frase>Modalidade</div>
     <select id="prot_modal" data-ui-seg aria-label="Modalidade">
      <option value="CT">TC</option>
      <option value="MR">RM</option>
     </select>
     <div class="est-erro" id="prot_e_modalidade"></div>
    </div>
   </div>
   <input type="search" id="prot_filtro" class="est-filtro" spellcheck="false" autocomplete="off" placeholder="filtrar por nome ou task" aria-label="filtrar por nome ou task">
   <div class="est-tabela-cx">
    <table class="est-tabela">
     <thead><tr><th scope="col" data-radai-frase>No STUDY</th><th scope="col" class="prot-col-unir" hidden data-radai-frase>Na união</th><th scope="col" data-radai-frase>Nome anatômico</th><th scope="col" data-radai-frase>Nome no STUDY</th><th scope="col" data-radai-frase>Task</th></tr></thead>
     <tbody id="prot_corpo"></tbody>
    </table>
   </div>
   <div class="est-erro" id="prot_e_estruturas"></div>
   <div class="est-rot prot-rot-unioes" data-radai-frase>Uniões</div>
   <div class="prot-unioes" id="prot_unioes"></div>
   <div class="linha" id="prot_uniao_abre"><button class="bt sec" type="button" id="prot_unir" data-radai-frase>Nova união</button></div>
   <div class="prot-uniao-form" id="prot_uniao_form" hidden>
    <input type="text" id="prot_uniao_nome" maxlength="16" spellcheck="false" autocomplete="off" placeholder="nome da união, até 16 caracteres" aria-label="nome da união, até 16 caracteres">
    <button class="bt sec" type="button" id="prot_uniao_criar" data-radai-frase>Criar a união com as marcadas</button>
    <button class="bt sec" type="button" id="prot_uniao_cancelar" data-radai-frase>Cancelar</button>
    <div class="est-erro" id="prot_e_uniao"></div>
   </div>
   <p class="prot-achado" id="prot_achado" hidden><span data-radai-frase>Este protocolo procura achado: no «Rodar agora», a confirmação aparece a cada execução.</span></p>
   <div class="linha">
    <button class="bt pri" type="button" id="prot_salvar" data-radai-frase>Salvar o protocolo</button>
    <button class="bt" type="button" id="prot_cancelar" data-radai-frase>Cancelar</button>
    <span class="msg est-msg" id="prot_msg" aria-live="polite"></span>
   </div>
  </div>
 </div>
</section>
"""

CSS = u"""
#ps_geral [hidden],#ps_estruturas [hidden]{display:none!important}
.est-bloco{margin-top:20px}
.est-rot{display:flex;align-items:center;gap:8px;font-size:11px;font-weight:700;
 letter-spacing:.4px;color:var(--accent);margin:0 0 5px}
.est-frase{margin:0 0 8px;font-size:12px;line-height:1.5;color:var(--text-muted);max-width:76ch}
.est-atual{margin:0 0 8px;font-size:12px;color:var(--text-muted)}
.est-atual code{font-family:var(--font-mono);overflow-wrap:anywhere;color:var(--text)}
.est-tag{display:inline-block;padding:1px 8px;border-radius:var(--r-pill);
 border:1px solid var(--line-strong);font:500 10.5px/1.5 var(--font-display);
 letter-spacing:0;color:var(--text-muted)}
.est-msg{display:block;min-height:18px;margin:6px 0 0;font-size:12.5px}
.est-msg.ok{color:var(--success)}
.est-msg.ruim{color:var(--perigo)}
.an-ops{display:flex;flex-wrap:wrap;gap:10px;margin:6px 0 0;max-width:760px}
.an-op{flex:1 1 220px;text-align:start;padding:11px 13px;border-radius:var(--r-md);
 border:1px solid var(--line-strong);background:var(--panel-2);color:var(--text);
 font:inherit;cursor:pointer;transition:border-color .15s ease,box-shadow .15s ease}
.an-op b{display:block;font-size:13.5px}
.an-op span{display:block;font-size:11.5px;line-height:1.45;color:var(--text-muted);margin-top:2px}
.an-op:hover{border-color:var(--accent-line)}
.an-op[aria-checked="true"]{border-color:var(--accent);box-shadow:inset 0 0 0 1px var(--accent)}
.an-op:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.est-barra{display:flex;flex-wrap:wrap;align-items:center;gap:10px 14px;margin:4px 0 10px}
.est-barra .ui-seg{flex:0 0 auto}
#ps_estruturas input.est-filtro{flex:1 1 220px;width:auto;min-width:0;max-width:340px;
 font-family:var(--font-display);background:var(--bg-0);margin:0}
#ps_estruturas .prot-editor input.est-filtro{display:block;width:100%;margin:0 0 8px}
label.est-todas{display:flex;align-items:center;gap:8px;margin:0;font-size:12px;font-weight:400;
 letter-spacing:0;color:var(--text-muted);cursor:pointer}
label.est-todas input{width:16px;height:16px;margin:0;flex:0 0 auto}
.est-tabela-cx{max-height:460px;overflow:auto;border:1px solid var(--line);
 border-radius:var(--r-md);background:var(--bg-0)}
.est-tabela{width:100%;border-collapse:collapse;font-size:12.5px}
.est-tabela thead th{position:sticky;top:0;z-index:1;background:var(--panel);text-align:start;
 padding:8px 10px;font:600 11px/1.3 var(--font-display);letter-spacing:.3px;
 color:var(--text-dim);border-bottom:1px solid var(--line-strong);white-space:nowrap}
.est-tabela td{padding:6px 10px;border-bottom:1px solid var(--line);vertical-align:middle;
 color:var(--text);line-height:1.45}
.est-tabela tbody tr:hover td{background:var(--panel)}
.est-tabela tr.com-erro td{background:var(--fundo-perigo)}
.est-mono{font-family:var(--font-mono);font-size:12px;color:var(--text-muted);overflow-wrap:anywhere}
.est-mono span{color:var(--text)}
.est-sub{display:block;font-size:11px;color:var(--text-dim)}
.est-chip{display:inline-block;margin-inline-start:6px;padding:0 7px;border-radius:var(--r-pill);
 border:1px solid var(--line-strong);font:500 10px/1.6 var(--font-display);letter-spacing:.3px;
 color:var(--text-dim);white-space:nowrap;vertical-align:1px}
.est-chip.achado{border-color:var(--borda-aviso);color:var(--aviso)}
.est-cor{width:74px;text-align:center}.est-cor input[type=color]{width:42px;height:32px;padding:2px;border:1px solid var(--line);background:var(--panel-2);border-radius:var(--r-md);cursor:pointer}.est-cor input:disabled{opacity:.45;cursor:not-allowed}
.est-proprio{min-width:170px;width:30%}
.est-proprio input{margin:0;padding:6px 8px;font-size:12.5px;background:var(--panel-2);
 border-color:var(--line-strong)}
.est-proprio input:disabled{opacity:.45;cursor:not-allowed}
.est-proprio input[aria-invalid="true"]{border-color:var(--perigo)}
.est-erro{min-height:0;margin:3px 0 0;font-size:11.5px;line-height:1.4;color:var(--perigo)}
.est-erro:empty{margin:0}
.est-vazio{padding:16px 12px;color:var(--text-dim);font-size:12.5px}
.est-vazio-p{margin:0 0 8px;font-size:12.5px;color:var(--text-dim)}
.est-acoes{margin-top:10px;align-items:center}
.prot-lista{display:flex;flex-direction:column;gap:8px;margin:4px 0 8px;max-width:820px}
.prot-item{display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px;padding:10px 12px;
 border:1px solid var(--line);border-radius:var(--r-md);background:var(--panel)}
.prot-item-txt{flex:1 1 260px;display:flex;flex-wrap:wrap;align-items:center;gap:4px 6px;min-width:0}
.prot-item-txt>b{font-size:13.5px;color:var(--text);overflow-wrap:anywhere}
.prot-item-n{flex:1 1 100%;font-size:11.5px;color:var(--text-muted)}
.prot-item .bt.sec{margin-top:0}
.prot-item .bt.perigo{background:var(--fundo-perigo);color:var(--perigo)}
.prot-editor{margin:12px 0 0;padding:14px;border:1px solid var(--line-strong);
 border-radius:var(--r-lg);background:var(--panel)}
.prot-editor>.linha{margin-top:12px}
#ps_limpar .reg-resumo-tit{margin:18px 0 6px;font:600 12.5px/1.3 var(--font-display);
 color:var(--text)}
.prot-campos{display:flex;flex-wrap:wrap;gap:12px 18px;margin:0 0 12px}
.prot-campo{flex:1 1 260px;min-width:0}
.prot-campo:last-child{flex:0 0 auto}
.prot-rot-unioes{margin-top:14px}
.prot-unioes{display:flex;flex-direction:column;gap:8px;margin:0 0 6px}
.prot-uniao{display:flex;flex-wrap:wrap;align-items:center;gap:6px 10px;padding:8px 10px;
 border:1px solid var(--line);border-radius:var(--r-md);background:var(--bg-1)}
.prot-uniao input{flex:0 0 190px;width:190px;margin:0;padding:6px 8px;font-size:12.5px}
.prot-uniao .bt.sec{margin-top:0}
.prot-partes{flex:1 1 240px;font:12px/1.5 var(--font-mono);color:var(--text-muted);overflow-wrap:anywhere}
.prot-uniao .est-erro{flex:1 1 100%}
.prot-uniao-form{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin:6px 0 0}
.prot-uniao-form input{flex:0 0 240px;width:240px;margin:0}
.prot-uniao-form .bt.sec{margin-top:0}
.prot-uniao-form .est-erro{flex:1 1 100%}
.prot-achado{margin:10px 0 0;padding:8px 11px;border-radius:var(--r-md);
 border:1px solid var(--borda-aviso);background:var(--fundo-aviso);font-size:12.5px;color:var(--text)}
.exi-previa{margin:10px 0 0;padding:12px 14px;border:1px solid var(--line-strong);
 border-radius:var(--r-lg);background:var(--panel);max-width:900px}
.exi-secao{padding:8px 0 10px;border-bottom:1px solid var(--line)}
.exi-secao:last-of-type{border-bottom:0}
label.exi-marca{display:flex;align-items:center;gap:8px;margin:0 0 6px;font-size:13px;
 font-weight:600;letter-spacing:0;color:var(--text);cursor:pointer}
label.exi-marca input{width:16px;height:16px;margin:0;flex:0 0 auto}
.exi-tabela{border-collapse:collapse;font-size:12px;margin:4px 0 0}
.exi-tabela th{text-align:start;padding:3px 14px 3px 0;color:var(--text-dim);font-weight:500;white-space:nowrap}
.exi-tabela td{padding:3px 14px 3px 0;font-family:var(--font-mono);color:var(--text-muted);
 overflow-wrap:anywhere;vertical-align:top}
.exi-tabela td.exi-aviso{font-family:var(--font-display);color:var(--perigo)}
.exi-linha{margin:2px 0;font-size:12px;color:var(--text-muted)}
.exi-linha code{font-family:var(--font-mono);color:var(--text)}
.exi-linha.ruim{color:var(--perigo)}
@media (prefers-reduced-motion:reduce){.an-op{transition:none}}
"""

JS = r"""
<script>
(function(){
 function $(id){ return document.getElementById(id) }
 function esc(s){ return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
   .replace(/>/g, '&gt;').replace(/"/g, '&quot;') }
 function retraduzir(){ try{ if(window.radaiRetraduzir) window.radaiRetraduzir() }catch(e){} }
 function html(el, h){ if(!el) return; if(window.uiHTML) window.uiHTML(el, h); else el.innerHTML = h }
 function frase(t){ return '<span data-radai-frase>' + esc(t) + '</span>' }
 function texto(el, t, tom){
  if(!el) return;
  if(window.uiTexto) window.uiTexto(el, t || ''); else el.textContent = t || '';
  el.classList.remove('ok'); el.classList.remove('ruim');
  if(tom) el.classList.add(tom);
  retraduzir();
 }
 function pedir(url, corpo){
  var o = (corpo === undefined) ? {} : {method:'POST', headers:{'Content-Type':'application/json'},
                                       body: JSON.stringify(corpo)};
  return fetch(url, o).then(function(r){ return r.json() });
 }
 function idioma(){
  var l = document.documentElement.getAttribute('lang');
  if(l) return l;
  try{ return localStorage.getItem('radai_idioma') || 'pt-BR' }catch(e){ return 'pt-BR' }
 }
 function segDefinir(s, v){
  if(!s) return;
  s.value = v;
  var cx = s.previousElementSibling;
  if(cx && cx._uiPintar) cx._uiPintar();
 }
 function semAcento(s){
  s = String(s || '').toLowerCase();
  return s.normalize ? s.normalize('NFD').replace(/[̀-ͯ]/g, '') : s;
 }
 function copia(o){ var r = {}; Object.keys(o || {}).forEach(function(k){ r[k] = o[k] }); return r }

 var MOTIVO = {
  espaco: 'sem espaço no começo nem no fim',
  ascii: 'só letras sem acento, números e sinais do teclado (ASCII)',
  limite: 'até 16 caracteres',
  barra: 'sem contrabarra: o DICOM a usa como separador',
  reservado: 'nome reservado a alvo (GTV, CTV, ITV, PTV) ou ao contorno externo (BODY, External)',
  repetido: 'repete o nome de outra estrutura',
  curta: 'uma união precisa de pelo menos duas estruturas',
  semNome: 'dê um nome à união'
 };
 function motivoDoNome(v){
  if(!v) return '';
  if(v !== v.trim()) return MOTIVO.espaco;
  if(/[^\x20-\x7e]/.test(v)) return MOTIVO.ascii;
  if(v.length > 16) return MOTIVO.limite;
  if(v.indexOf('\\') >= 0) return MOTIVO.barra;
  var a = v.toUpperCase();
  if(a === 'BODY' || a === 'EXTERNAL' || /^(GTV|CTV|ITV|PTV)/.test(a)) return MOTIVO.reservado;
  return '';
 }

 var ANEL = '';
 function anelPintar(v){
  ANEL = v;
  Array.prototype.forEach.call(document.querySelectorAll('.an-op'), function(b){
   var on = b.getAttribute('data-tps') === v;
   b.setAttribute('aria-checked', on ? 'true' : 'false');
   b.tabIndex = on ? 0 : -1;
  });
 }
 function anelEscolher(v){
  if(!v || v === ANEL) return;
  var antes = ANEL;
  anelPintar(v);
  pedir('/api/config/tps', {tps: v}).then(function(d){
   if(d && d.ok){ anelPintar(d.tps); texto($('an_msg'), 'Gravado: vale para o próximo RTSTRUCT.', 'ok'); return }
   anelPintar(antes); texto($('an_msg'), (d && d.erro) || 'Não consegui gravar.', 'ruim');
  }).catch(function(){ anelPintar(antes); texto($('an_msg'), 'Não consegui gravar.', 'ruim') });
 }
 Array.prototype.forEach.call(document.querySelectorAll('.an-op'), function(b){
  b.addEventListener('click', function(){ anelEscolher(b.getAttribute('data-tps')) });
  b.addEventListener('keydown', function(e){
   if(['ArrowRight', 'ArrowDown', 'ArrowLeft', 'ArrowUp'].indexOf(e.key) < 0) return;
   e.preventDefault();
   var ops = Array.prototype.slice.call(document.querySelectorAll('.an-op'));
   var i = ops.indexOf(b), n = ops.length;
   var k = (e.key === 'ArrowRight' || e.key === 'ArrowDown') ? (i + 1) % n : (i - 1 + n) % n;
   ops[k].focus(); anelEscolher(ops[k].getAttribute('data-tps'));
  });
 });

 var EST = {mod: 'CT', cache: {}, modo: 'padrao', salvo: {modo: 'padrao', nomes: {}, cores: {}},
            nomes: {}, cores: {}, erros: {}, todas: false, carregado: false};
 var PROT = {lista: [], ed: null, unindo: false, marcadas: {}, armado: ''};

 function resumo(){
  var modo = EST.salvo.modo, n = PROT.lista.length;
  var h = frase(modo === 'proprios' ? 'Tags próprias' : 'Padrão') + ' &middot; <b>' + n + '</b> '
        + frase('protocolo(s) próprio(s)');
  html($('cst_estruturas'), h);
  html($('sub_estruturas'), '&#8212; ' + h);
  retraduzir();
 }

 function estacao(){
  pedir('/api/config/estacao').then(function(d){
   anelPintar(d.tps_em_vigor || 'eclipse');
   var fav = d.favorita || '';
   if($('fav_atual')) $('fav_atual').hidden = !fav;
   if($('fav_caminho')) $('fav_caminho').textContent = fav;
   if(!EST.carregado){ EST.salvo.modo = d.modo || 'padrao'; EST.modo = EST.salvo.modo }
   resumo();
  }).catch(function(){});
 }

 function corHex(c){ return '#' + (c || [160,160,160]).map(function(v){ return ('0' + Math.max(0,Math.min(255,+v || 0)).toString(16)).slice(-2) }).join('') }
 function estCarregar(mod, depois){
  if(EST.cache[mod]){ if(depois) depois(EST.cache[mod]); return }
  pedir('/api/config/estruturas?modalidade=' + encodeURIComponent(mod)
        + '&idioma=' + encodeURIComponent(idioma())).then(function(d){
   EST.cache[mod] = d || {linhas: []};
   if(!EST.carregado){
    EST.carregado = true;
    EST.modo = d.modo || 'padrao';
    EST.salvo = {modo: EST.modo, nomes: copia(d.nomes), cores: copia(d.cores)};
    EST.nomes = copia(d.nomes); EST.cores = copia(d.cores);
    segDefinir($('est_modo'), EST.modo);
   }
   if(depois) depois(EST.cache[mod]);
  }).catch(function(){
   EST.cache[mod] = null;
   if(depois) depois({linhas: [], erro: 'Não consegui ler a lista de estruturas.'});
  });
 }

 function linhas(mod){
  var d = EST.cache[mod] || {linhas: []}, vistos = {}, saida = [];
  (d.linhas || []).forEach(function(l){
   if(vistos[l.nome_padrao]) return;
   vistos[l.nome_padrao] = 1;
   saida.push(l);
  });
  return saida;
 }
 function visivel(l, filtro, todas){
  if(!todas && !l.no_study) return false;
  if(!filtro) return true;
  var t = semAcento(filtro);
  return [l.nome_padrao, l.anatomico, l.task, EST.nomes[l.nome_padrao] || ''].some(function(x){
   return semAcento(x).indexOf(t) >= 0 });
 }

 function estConferir(){
  var erros = {}, grupos = {};
  Object.keys(EST.nomes).forEach(function(n){
   var m = motivoDoNome(EST.nomes[n]); if(m) erros[n] = m });
  linhas(EST.mod).forEach(function(l){
   var e = (EST.nomes[l.nome_padrao] || l.nome_padrao).toLowerCase();
   (grupos[e] = grupos[e] || []).push(l.nome_padrao);
  });
  Object.keys(grupos).forEach(function(k){
   if(grupos[k].length < 2) return;
   grupos[k].forEach(function(n){ if(EST.nomes[n] && !erros[n]) erros[n] = MOTIVO.repetido });
  });
  EST.erros = erros;
  Array.prototype.forEach.call($('est_corpo').querySelectorAll('input[data-n]'), function(i){
   var m = erros[i.getAttribute('data-n')] || '', tr = i.closest('tr');
   if(m) i.setAttribute('aria-invalid', 'true'); else i.removeAttribute('aria-invalid');
   if(tr) tr.classList.toggle('com-erro', !!m);
   html(i.nextElementSibling, m ? frase(m) : '');
  });
  retraduzir();
  return erros;
 }

 function estPintar(){
  var d = EST.cache[EST.mod] || {linhas: []}, ls = linhas(EST.mod);
  var corpo = $('est_corpo'), propria = (EST.modo === 'proprios');
  $('est_cx').setAttribute('aria-busy', 'false');
  if(!ls.length){
   corpo.innerHTML = '<tr><td colspan="5" class="est-vazio">' + frase(d.erro || 'Nenhuma estrutura nesta modalidade.') + '</td></tr>';
   $('est_salvar').disabled = true;
   texto($('est_nota'), '');
   retraduzir();
   return;
  }
  $('est_salvar').disabled = false;
  var filtro = $('est_filtro').value, h = '', n = 0;
  ls.forEach(function(l, i){
   if(!visivel(l, filtro, EST.todas)) return;
   n++;
   var v = EST.nomes[l.nome_padrao] || '', err = EST.erros[l.nome_padrao] || '';
   h += '<tr' + (err ? ' class="com-erro"' : '') + '>'
     + '<td class="est-mono" data-radai-t="1" translate="no">' + esc(l.task) + '</td>'
     + '<td><span data-radai-t="1">' + esc(l.anatomico || '—') + '</span>'
     + (l.achado ? '<span class="est-chip achado" data-radai-frase>ACHADO</span>' : '') + '</td>'
     + '<td class="est-mono"><span id="est_n_' + i + '" data-radai-t="1" translate="no">' + esc(l.nome_padrao) + '</span>'
     + (l.no_study ? '' : '<span class="est-chip" data-radai-frase>só no FULL</span>') + '</td>'
     + '<td class="est-proprio"><input type="text" maxlength="16" spellcheck="false" autocomplete="off" data-n="'
     + esc(l.nome_padrao) + '" value="' + esc(v) + '" aria-labelledby="est_h_proprio est_n_' + i + '"'
     + (propria ? '' : ' disabled') + (err ? ' aria-invalid="true"' : '') + '><div class="est-erro">'
     + (err ? frase(err) : '') + '</div></td>'
     + '<td class="est-cor"><input type="color" data-cor="' + esc(l.nome_padrao)
     + '" value="' + corHex(EST.cores[l.nome_padrao] || l.cor_padrao)
     + '" aria-labelledby="est_h_cor est_n_' + i + '"' + (propria && l.no_study ? '' : ' disabled') + '></td></tr>';
  });
  if(!n) h = '<tr><td colspan="5" class="est-vazio">' + frase('Nenhuma estrutura com este filtro.') + '</td></tr>';
  corpo.innerHTML = h;
  texto($('est_nota'), propria
   ? 'Com tags próprias, o STUDY sai com o nome que você escreveu; a linha em branco fica com o nome padrão.'
   : 'Em Padrão, o STUDY sai com os nomes padrão; o que você escreveu fica guardado.');
  retraduzir();
 }

 var tFiltro = null;
 $('est_filtro').addEventListener('input', function(){
  if(tFiltro) clearTimeout(tFiltro);
  tFiltro = setTimeout(estPintar, 160);
 });
 $('est_todas').addEventListener('change', function(){ EST.todas = this.checked; estPintar() });
 $('est_modal').addEventListener('change', function(){
  EST.mod = this.value;
  $('est_cx').setAttribute('aria-busy', 'true');
  estCarregar(EST.mod, function(){ estConferir(); estPintar() });
 });
 var tConf = null;
 $('est_corpo').addEventListener('input', function(ev){
   var i = ev.target, cor = i && i.getAttribute ? i.getAttribute('data-cor') : '';
   if(cor){
    var hex = i.value.replace('#', '');
    EST.cores[cor] = [0,2,4].map(function(k){ return parseInt(hex.slice(k,k+2),16) });
    return;
   }
   var n = i && i.getAttribute ? i.getAttribute('data-n') : '';
   if(!n) return;
  if(i.value) EST.nomes[n] = i.value; else delete EST.nomes[n];
  if(tConf) clearTimeout(tConf);
  tConf = setTimeout(estConferir, 140);
 });
 $('est_modo').addEventListener('change', function(){
  var v = this.value;
  pedir('/api/config/nomes', {modo: v, nomes: EST.salvo.nomes, cores: EST.salvo.cores}).then(function(d){
   if(d && d.ok){
    EST.modo = d.modo; EST.salvo.modo = d.modo;
    estPintar(); resumo();
    texto($('est_msg'), d.modo === 'proprios' ? 'Gravado: o STUDY sai com as tags próprias.'
                                             : 'Gravado: o STUDY sai com os nomes padrão.', 'ok');
    return;
   }
   segDefinir($('est_modo'), EST.modo);
   texto($('est_msg'), (d && (d.erro || (d.erros && d.erros['']))) || 'Nada foi gravado: confira as linhas marcadas.', 'ruim');
  }).catch(function(){ segDefinir($('est_modo'), EST.modo); texto($('est_msg'), 'Não consegui gravar.', 'ruim') });
 });
 $('est_salvar').addEventListener('click', function(){
  var b = this, erros = estConferir();
  if(Object.keys(erros).length){ texto($('est_msg'), 'Nada foi gravado: confira as linhas marcadas.', 'ruim'); return }
  b.disabled = true;
  pedir('/api/config/nomes', {modo: EST.modo, nomes: EST.nomes, cores: EST.cores}).then(function(d){
   b.disabled = false;
   if(d && d.ok){
    EST.salvo = {modo: d.modo, nomes: copia(d.nomes), cores: copia(d.cores)}; EST.erros = {};
    estPintar(); resumo();
    texto($('est_msg'), 'Gravado: vale para a próxima série.', 'ok');
    return;
   }
   EST.erros = (d && d.erros) || {};
   if(EST.erros['']){ texto($('est_msg'), EST.erros[''], 'ruim'); return }
   estPintar();
   texto($('est_msg'), (d && d.erro) || 'Nada foi gravado: confira as linhas marcadas.', 'ruim');
  }).catch(function(){ b.disabled = false; texto($('est_msg'), 'Não consegui gravar.', 'ruim') });
 });

 function protCarregar(){
  pedir('/api/config/protocolos').then(function(d){
   PROT.lista = (d && d.protocolos) || [];
   protListar(); resumo();
  }).catch(function(){});
 }
 function protListar(){
  var h = '';
  PROT.lista.forEach(function(p){
   h += '<div class="prot-item" data-id="' + esc(p.id) + '"><div class="prot-item-txt">'
     + '<b data-radai-t="1">' + esc(p.nome) + '</b>'
     + '<span class="est-chip" data-radai-frase>' + (p.modalidade === 'MR' ? 'RM' : 'TC') + '</span>'
     + (p.tem_achado ? '<span class="est-chip achado" data-radai-frase>ACHADO</span>' : '')
     + '<span class="prot-item-n"><b>' + (p.estruturas || []).length + '</b> ' + frase('estrutura(s)')
     + ' &middot; <b>' + (p.merges || []).length + '</b> ' + frase('união(ões)') + '</span></div>'
     + '<button class="bt sec" type="button" data-acao="editar" data-radai-frase>Editar</button>'
     + '<button class="bt sec' + (PROT.armado === p.id ? ' perigo' : '') + '" type="button" data-acao="apagar" data-radai-frase>'
     + (PROT.armado === p.id ? 'Confirmar: apagar' : 'Apagar') + '</button></div>';
  });
  if(!h) h = '<p class="est-vazio-p">' + frase('Nenhum protocolo próprio. Sem protocolo, nada muda no «Rodar agora».') + '</p>';
  html($('prot_lista'), h);
  retraduzir();
 }
 $('prot_lista').addEventListener('click', function(ev){
  var b = ev.target.closest ? ev.target.closest('[data-acao]') : null;
  if(!b) return;
  var item = b.closest('.prot-item'), id = item ? item.getAttribute('data-id') : '';
  var p = PROT.lista.filter(function(x){ return x.id === id })[0];
  if(!p) return;
  if(b.getAttribute('data-acao') === 'editar'){ PROT.armado = ''; protAbrir(p); return }
  if(PROT.armado !== id){ PROT.armado = id; protListar(); return }
  PROT.armado = '';
  pedir('/api/config/protocolos/apagar', {id: id}).then(function(d){
   if(d && d.ok){ texto($('prot_lista_msg'), 'Protocolo apagado.', 'ok'); protCarregar(); return }
   texto($('prot_lista_msg'), (d && d.erro) || 'Não consegui apagar.', 'ruim'); protListar();
  }).catch(function(){ texto($('prot_lista_msg'), 'Não consegui apagar.', 'ruim') });
 });

 function protErros(erros){
  ['nome', 'modalidade', 'estruturas'].forEach(function(k){
   html($('prot_e_' + k), erros[k] ? frase(erros[k]) : '') });
  (PROT.ed ? PROT.ed.merges : []).forEach(function(m, i){
   html($('prot_e_uniao_' + i), erros['uniao:' + i] ? frase(erros['uniao:' + i]) : '') });
  retraduzir();
 }
 function protAchado(){
  var marcadas = {};
  PROT.ed.estruturas.forEach(function(n){ marcadas[n] = 1 });
  PROT.ed.merges.forEach(function(m){ m.de.forEach(function(n){ marcadas[n] = 1 }) });
  var tem = linhas(PROT.ed.modalidade).some(function(l){ return l.achado && marcadas[l.nome_padrao] });
  $('prot_achado').hidden = !tem;
 }
 function protUnioes(){
  var h = '';
  PROT.ed.merges.forEach(function(m, i){
   h += '<div class="prot-uniao"><input type="text" maxlength="16" spellcheck="false" autocomplete="off" data-uniao="'
     + i + '" value="' + esc(m.nome) + '" aria-label="nome da união, até 16 caracteres">'
     + '<span class="prot-partes" data-radai-t="1" translate="no">' + m.de.map(esc).join(' + ') + '</span>'
     + '<button class="bt sec" type="button" data-desfazer="' + i + '" data-radai-frase>Desfazer</button>'
     + '<div class="est-erro" id="prot_e_uniao_' + i + '"></div></div>';
  });
  if(!h) h = '<p class="est-vazio-p">' + frase('Nenhuma união.') + '</p>';
  html($('prot_unioes'), h);
 }
 function protPintar(){
  if(!PROT.ed) return;
  var mod = PROT.ed.modalidade, d = EST.cache[mod] || {linhas: []}, ls = linhas(mod);
  var tags = (EST.salvo.modo === 'proprios') ? EST.salvo.nomes : {};
  var f = $('prot_filtro').value, unindo = PROT.unindo, h = '';
  Array.prototype.forEach.call(document.querySelectorAll('.prot-col-unir'), function(th){ th.hidden = !unindo });
  ls.forEach(function(l, i){
   if(l.protocolo === false || !visivel(l, f, true)) return;
   var sel = PROT.ed.estruturas.indexOf(l.nome_padrao) >= 0, tag = tags[l.nome_padrao] || '';
   h += '<tr><td><input type="checkbox" data-sel="' + esc(l.nome_padrao) + '"' + (sel ? ' checked' : '')
     + ' aria-labelledby="prot_n_' + i + '"></td>'
     + (unindo ? '<td><input type="checkbox" data-unir="' + esc(l.nome_padrao) + '"'
        + (PROT.marcadas[l.nome_padrao] ? ' checked' : '') + ' aria-labelledby="prot_n_' + i + '"></td>' : '')
     + '<td><span data-radai-t="1">' + esc(l.anatomico || '—') + '</span>'
     + (l.achado ? '<span class="est-chip achado" data-radai-frase>ACHADO</span>' : '') + '</td>'
     + '<td class="est-mono"><span id="prot_n_' + i + '" data-radai-t="1" translate="no">' + esc(tag || l.nome_padrao) + '</span>'
     + (tag ? '<span class="est-sub" data-radai-t="1" translate="no">' + esc(l.nome_padrao) + '</span>' : '')
     + (l.no_study ? '' : '<span class="est-chip" data-radai-frase>só no FULL</span>') + '</td>'
     + '<td class="est-mono" data-radai-t="1" translate="no">' + esc(l.task) + '</td></tr>';
  });
  if(!h) h = '<tr><td colspan="5" class="est-vazio">' + frase(d.erro || 'Nenhuma estrutura com este filtro.') + '</td></tr>';
  $('prot_corpo').innerHTML = h;
  protUnioes(); protAchado(); retraduzir();
 }
 function protAbrir(p){
  PROT.ed = p ? JSON.parse(JSON.stringify(p))
              : {id: '', nome: '', modalidade: EST.mod || 'CT', estruturas: [], merges: []};
  PROT.unindo = false; PROT.marcadas = {};
  $('prot_nome').value = PROT.ed.nome;
  $('prot_filtro').value = '';
  segDefinir($('prot_modal'), PROT.ed.modalidade);
  $('prot_uniao_form').hidden = true; $('prot_uniao_abre').hidden = false;
  $('prot_editor').hidden = false;
  texto($('prot_msg'), '');
  protErros({});
  estCarregar(PROT.ed.modalidade, protPintar);
  try{ $('prot_editor').scrollIntoView({block: 'nearest'}) }catch(e){}
  $('prot_nome').focus();
 }
 function protFechar(){ PROT.ed = null; $('prot_editor').hidden = true; $('prot_novo').focus() }
 $('prot_novo').addEventListener('click', function(){ protAbrir(null) });
 $('prot_cancelar').addEventListener('click', protFechar);
 $('prot_modal').addEventListener('change', function(){
  if(!PROT.ed) return;
  PROT.ed.modalidade = this.value;
  estCarregar(PROT.ed.modalidade, function(){
   var ok = {};
   linhas(PROT.ed.modalidade).forEach(function(l){ ok[l.nome_padrao] = 1 });
   PROT.ed.estruturas = PROT.ed.estruturas.filter(function(n){ return ok[n] });
   PROT.ed.merges = PROT.ed.merges.filter(function(m){ return m.de.every(function(n){ return ok[n] }) });
   protPintar();
  });
 });
 var tProt = null;
 $('prot_filtro').addEventListener('input', function(){
  if(tProt) clearTimeout(tProt);
  tProt = setTimeout(protPintar, 160);
 });
 $('prot_corpo').addEventListener('change', function(ev){
  var c = ev.target;
  if(!c || !PROT.ed) return;
  var n = c.getAttribute('data-sel');
  if(n){
   var i = PROT.ed.estruturas.indexOf(n);
   if(c.checked && i < 0) PROT.ed.estruturas.push(n);
   if(!c.checked && i >= 0) PROT.ed.estruturas.splice(i, 1);
   protAchado();
   return;
  }
  var u = c.getAttribute('data-unir');
  if(u){ if(c.checked) PROT.marcadas[u] = 1; else delete PROT.marcadas[u] }
 });
 $('prot_unioes').addEventListener('input', function(ev){
  var i = ev.target.getAttribute ? ev.target.getAttribute('data-uniao') : null;
  if(i === null || !PROT.ed) return;
  PROT.ed.merges[+i].nome = ev.target.value;
  var m = motivoDoNome(ev.target.value);
  html($('prot_e_uniao_' + i), m ? frase(m) : '');
  retraduzir();
 });
 $('prot_unioes').addEventListener('click', function(ev){
  var b = ev.target.closest ? ev.target.closest('[data-desfazer]') : null;
  if(!b || !PROT.ed) return;
  PROT.ed.merges.splice(+b.getAttribute('data-desfazer'), 1);
  protPintar();
 });
 $('prot_unir').addEventListener('click', function(){
  PROT.unindo = true; PROT.marcadas = {};
  $('prot_uniao_abre').hidden = true; $('prot_uniao_form').hidden = false;
  $('prot_uniao_nome').value = ''; html($('prot_e_uniao'), '');
  protPintar();
  $('prot_uniao_nome').focus();
 });
 function protUniaoFechar(){
  PROT.unindo = false; PROT.marcadas = {};
  $('prot_uniao_form').hidden = true; $('prot_uniao_abre').hidden = false;
  protPintar();
 }
 $('prot_uniao_cancelar').addEventListener('click', protUniaoFechar);
 $('prot_uniao_criar').addEventListener('click', function(){
  var nome = $('prot_uniao_nome').value, de = Object.keys(PROT.marcadas);
  var m = nome ? motivoDoNome(nome) : MOTIVO.semNome;
  if(!m && de.length < 2) m = MOTIVO.curta;
  if(m){ html($('prot_e_uniao'), frase(m)); retraduzir(); return }
  PROT.ed.merges.push({nome: nome, de: de});
  protUniaoFechar();
 });
 $('prot_salvar').addEventListener('click', function(){
  if(!PROT.ed) return;
  var b = this;
  PROT.ed.nome = $('prot_nome').value;
  PROT.ed.modalidade = $('prot_modal').value;
  b.disabled = true;
  pedir('/api/config/protocolos', {protocolo: PROT.ed}).then(function(d){
   b.disabled = false;
   if(d && d.ok){
    protFechar();
    texto($('prot_lista_msg'), d.protocolo && d.protocolo.tem_achado
     ? 'Protocolo gravado. Ele procura achado: a confirmação aparece a cada execução.'
     : 'Protocolo gravado.', 'ok');
    protCarregar();
    return;
   }
   if(d && d.protocolo && d.protocolo.id) PROT.ed.id = d.protocolo.id;
   protErros((d && d.erros) || {});
   texto($('prot_msg'), (d && d.erro) || 'Nada foi gravado: confira os campos marcados.', 'ruim');
  }).catch(function(){ b.disabled = false; texto($('prot_msg'), 'Não consegui gravar.', 'ruim') });
 });

 var EXI = {dados: null};
 function rotuloDaSecao(s){
  return {configuracao: 'Configuração da estação', nomes: 'Nomes no STUDY',
          protocolos: 'Protocolos próprios'}[s] || s;
 }
 function exiPrevia(d){
  if(!d || !d.ok){ texto($('exi_msg'), (d && d.erro) || 'Não consegui ler o arquivo.', 'ruim'); return }
  var h = '', c = d.configuracao || {itens: []}, n = d.nomes || {}, p = d.protocolos || {};
  var muda = (c.itens || []).filter(function(i){ return i.muda });
  h += '<div class="exi-secao"><label class="exi-marca"><input type="checkbox" data-secao="configuracao" checked>'
    + frase(rotuloDaSecao('configuracao')) + '</label>';
  if(muda.length){
   h += '<table class="exi-tabela"><thead><tr><th data-radai-frase>Chave</th><th data-radai-frase>Nesta estação</th>'
     + '<th data-radai-frase>No arquivo</th></tr></thead><tbody>';
   muda.forEach(function(i){
    h += '<tr><td data-radai-t="1" translate="no">' + esc(i.chave) + '</td><td data-radai-t="1" translate="no">'
      + esc(i.atual || '—') + '</td><td data-radai-t="1" translate="no">' + esc(i.novo || '—') + '</td></tr>';
    if(i.aviso) h += '<tr><td></td><td colspan="2" class="exi-aviso">' + frase(i.aviso) + '</td></tr>';
   });
   h += '</tbody></table>';
  } else h += '<p class="exi-linha">' + frase('Nenhuma chave muda.') + '</p>';
  h += '</div><div class="exi-secao"><label class="exi-marca"><input type="checkbox" data-secao="nomes" checked>'
    + frase(rotuloDaSecao('nomes')) + '</label><p class="exi-linha">'
    + frase(n.modo === 'proprios' ? 'Tags próprias' : 'Padrão') + ' &middot; <b>'
    + Object.keys(n.validos || {}).length + '</b> ' + frase('nome(s) próprio(s)') + '</p>';
  Object.keys(n.recusados || {}).forEach(function(k){
   h += '<p class="exi-linha ruim"><code data-radai-t="1" translate="no">' + esc(k || '—') + '</code> ' + frase(n.recusados[k]) + '</p>';
  });
  h += '</div><div class="exi-secao"><label class="exi-marca"><input type="checkbox" data-secao="protocolos" checked>'
    + frase(rotuloDaSecao('protocolos')) + '</label><p class="exi-linha"><b>' + (p.validos || []).length + '</b> '
    + frase('protocolo(s) próprio(s)') + '</p>';
  (p.recusados || []).forEach(function(r){
   Object.keys(r.erros || {}).forEach(function(k){
    h += '<p class="exi-linha ruim"><code data-radai-t="1">' + esc(r.nome || '—') + '</code> ' + frase(r.erros[k]) + '</p>';
   });
  });
  h += '</div><div class="linha"><button class="bt pri" type="button" id="exi_aplicar" data-radai-frase>Importar o que está marcado</button>'
    + '<button class="bt" type="button" id="exi_cancelar" data-radai-frase>Cancelar</button></div>';
  var alvo = $('exi_previa');
  html(alvo, h);
  alvo.hidden = false;
  texto($('exi_msg'), '');
  retraduzir();
 }
 $('exi_exportar').addEventListener('click', function(){
  var b = this;
  b.disabled = true;
  pedir('/api/config/exportar', {}).then(function(d){
   b.disabled = false;
   if(!d || d.formato !== 'radai-configuracao'){ texto($('exi_msg'), (d && d.erro) || 'Não consegui exportar.', 'ruim'); return }
   var dt = new Date(), z = function(x){ return (x < 10 ? '0' : '') + x };
   var nome = 'radai_configuracao_' + dt.getFullYear() + z(dt.getMonth() + 1) + z(dt.getDate()) + '.json';
   var url = URL.createObjectURL(new Blob([JSON.stringify(d, null, 1)], {type: 'application/json'}));
   var a = document.createElement('a');
   a.href = url; a.download = nome; a.hidden = true;
   document.body.appendChild(a); a.click(); a.parentNode.removeChild(a);
   setTimeout(function(){ URL.revokeObjectURL(url) }, 5000);
   texto($('exi_msg'), 'O arquivo foi para a pasta de downloads do navegador.', 'ok');
  }).catch(function(){ b.disabled = false; texto($('exi_msg'), 'Não consegui exportar.', 'ruim') });
 });
 $('exi_importar').addEventListener('click', function(){ $('exi_arquivo').click() });
 $('exi_arquivo').addEventListener('change', function(){
  var f = this.files && this.files[0];
  this.value = '';
  if(!f) return;
  if(f.size > 2 * 1024 * 1024){ texto($('exi_msg'), 'este arquivo não é uma exportação das configurações', 'ruim'); return }
  var r = new FileReader();
  r.onload = function(){
   var dados = null;
   try{ dados = JSON.parse(String(r.result || '')) }catch(e){ dados = null }
   if(!dados){ texto($('exi_msg'), 'este arquivo não é uma exportação das configurações', 'ruim'); return }
   EXI.dados = dados;
   pedir('/api/config/importar/previa', {dados: dados}).then(exiPrevia)
    .catch(function(){ texto($('exi_msg'), 'Não consegui ler o arquivo.', 'ruim') });
  };
  r.onerror = function(){ texto($('exi_msg'), 'Não consegui ler o arquivo.', 'ruim') };
  r.readAsText(f);
 });
 $('exi_previa').addEventListener('click', function(ev){
  var b = ev.target.closest ? ev.target.closest('button') : null;
  if(!b) return;
  if(b.id === 'exi_cancelar'){ $('exi_previa').hidden = true; EXI.dados = null; return }
  if(b.id !== 'exi_aplicar' || !EXI.dados) return;
  var secoes = Array.prototype.map.call($('exi_previa').querySelectorAll('input[data-secao]:checked'),
                                        function(x){ return x.getAttribute('data-secao') });
  if(!secoes.length){ texto($('exi_msg'), 'Marque pelo menos uma seção.', 'ruim'); return }
  b.disabled = true;
  pedir('/api/config/importar', {dados: EXI.dados, secoes: secoes}).then(function(d){
   b.disabled = false;
   if(!d || !d.ok){ texto($('exi_msg'), (d && d.erro) || 'Não consegui importar.', 'ruim'); return }
   $('exi_previa').hidden = true; EXI.dados = null;
   EST.cache = {}; EST.carregado = false;
   estacao(); protCarregar();
   if(!$('ps_estruturas').hidden) estCarregar(EST.mod, estPintar);
   var rei = $('btrei_cfg');
   if(secoes.indexOf('configuracao') >= 0 && rei){
    rei.style.display = '';
    texto($('exi_msg'), 'Importado. Clique em Reiniciar agora para o vigia reler o arquivo.', 'ok');
   } else texto($('exi_msg'), 'Importado.', 'ok');
  }).catch(function(){ b.disabled = false; texto($('exi_msg'), 'Não consegui importar.', 'ruim') });
 });

 function guiaVer(){
  var b = $('gu_bloco');
  if(b) b.hidden = (typeof window.radaiGuiaAbrir !== 'function');
 }
 $('gu_ver').addEventListener('click', function(){
  if(typeof window.radaiGuiaAbrir === 'function') window.radaiGuiaAbrir();
 });
 guiaVer();
 window.addEventListener('load', guiaVer);
 setTimeout(guiaVer, 1500);

 window.estFavoritaProcurar = function(){
  var campo = $('f_PASTA_FAVORITA');
  if(!campo || campo.getAttribute('data-procurar') === '1') return;
  campo.setAttribute('data-procurar', '1');
  var b = document.createElement('button');
  b.type = 'button'; b.className = 'sec'; b.id = 'fav_procurar';
  b.setAttribute('data-radai-frase', '');
  b.textContent = 'Procurar…';
  campo.parentNode.insertBefore(b, campo.nextSibling);
  b.addEventListener('click', function(){
   if(typeof window.uiExplorador !== 'function') return;
   window.uiExplorador({titulo: 'Pasta favorita', origem: b, inicial: campo.value || '',
    aoUsar: function(c){
     campo.value = c || '';
     campo.dispatchEvent(new Event('input', {bubbles: true}));
     campo.dispatchEvent(new Event('change', {bubbles: true}));
    }});
  });
  retraduzir();
 };

 var sec = $('ps_estruturas');
 function talvezCarregar(){
  if(sec && !sec.hidden && !EST.carregado) estCarregar(EST.mod, function(){ estConferir(); estPintar() });
 }
 if(sec && window.MutationObserver){
  new MutationObserver(talvezCarregar).observe(sec, {attributes: true, attributeFilter: ['hidden', 'class']});
 }
 estacao();
 protCarregar();
 talvezCarregar();
 window.estFavoritaProcurar();
})();
</script>
"""


def aplicar(pagina):
    for marca, valor in ((MARCA_GERAL, GERAL), (MARCA_SECAO, SECAO),
                         (MARCA_CSS, CSS), (MARCA_JS, JS)):
        pagina = pagina.replace(marca, valor)
    return pagina


def montar(app, caminho, chaves=(), modelo=u"", registrar=None, versao=None):
    from fastapi import Request
    from fastapi.responses import JSONResponse

    todas = [k for k in (chaves or ())]

    def _log(msg):
        if not registrar:
            return
        try:
            registrar(msg)
        except Exception:
            pass

    async def _corpo(request):
        try:
            bruto = await request.body()
        except Exception:
            return {}
        if len(bruto or b"") > TETO_DO_CORPO:
            return None
        try:
            c = json.loads((bruto or b"{}").decode("utf-8") or u"{}")
        except Exception:
            return {}
        return c if isinstance(c, dict) else {}

    def _grande():
        return JSONResponse({"ok": False, "erro": u"pedido grande demais"},
                            status_code=413)

    def _versao():
        try:
            return (versao() if callable(versao) else versao) or u""
        except Exception:
            return u""

    @app.get("/api/config/estacao")
    def _estacao():
        _t, v = radai_config.ler_arquivo(caminho)
        tps = radai_config.tps_canonico(v.get("TPS_DESTINO", u""))
        n = radai_config.ler_nomes(caminho)
        fav = (v.get("PASTA_FAVORITA") or u"").split(u"#")[0].strip().strip(u'"')
        return {"tps": tps, "tps_em_vigor": tps or radai_config.TPS_VALIDOS[0],
                "rotulos": radai_config.TPS_ROTULOS, "favorita": fav,
                "modo": n["modo"], "nomes": len(n["nomes"]),
                "protocolos": len(radai_config.ler_protocolos(caminho))}

    @app.post("/api/config/tps")
    async def _tps(request: Request):
        c = await _corpo(request)
        if c is None:
            return _grande()
        ok, erro = radai_config.gravar_tps(caminho, c.get("tps"), modelo=modelo)
        if not ok:
            return JSONResponse({"ok": False, "erro": erro}, status_code=400)
        t = radai_config.tps_canonico(c.get("tps"))
        _log(u"anel dos contornos: TPS_DESTINO=%s (%s), gravado pela tela de "
             u"configuracoes" % (t, radai_config.rotulo_do_tps(t)))
        return {"ok": True, "tps": t, "rotulo": radai_config.rotulo_do_tps(t)}

    @app.get("/api/config/estruturas")
    def _estruturas(modalidade: str = "CT", idioma: str = u"pt-BR"):
        mod = radai_config.modalidade_canonica(modalidade) or "CT"
        linhas, erro = radai_config.linhas_da_tabela(mod)
        achados = radai_config.tasks_de_achado()
        for l in linhas:
            l["anatomico"] = radai_config.nome_anatomico(l["chave_anatomica"],
                                                         idioma)
            l["achado"] = bool(l.get("achado")) or l["task"] in achados
        import engine
        for l in linhas:
            l["cor_padrao"] = list(engine._color(l["nome_padrao"]))
        n = radai_config.ler_nomes(caminho)
        return {"modalidade": mod, "linhas": linhas, "erro": erro,
                "modo": n["modo"], "nomes": n["nomes"], "cores": n["cores"]}

    @app.post("/api/config/nomes")
    async def _nomes(request: Request):
        c = await _corpo(request)
        if c is None:
            return _grande()
        ok, r = radai_config.gravar_nomes(
            c.get("modo"), c.get("nomes") or {},
            radai_config.estruturas_por_modalidade(), caminho_cfg=caminho, cores=c.get("cores"))
        if ok:
            _log(u"nomes das estruturas: modo=%s, %d nome(s) proprio(s), "
                 u"gravado pela tela de configuracoes" % (r["modo"], len(r["nomes"])))
        return r

    @app.get("/api/config/protocolos")
    def _protocolos():
        return {"protocolos": radai_config.ler_protocolos(caminho)}

    @app.post("/api/config/protocolos")
    async def _gravar_protocolo(request: Request):
        c = await _corpo(request)
        if c is None:
            return _grande()
        bruto = c.get("protocolo") if isinstance(c.get("protocolo"), dict) else {}
        mod = radai_config.modalidade_canonica(bruto.get("modalidade"))
        linhas, _erro = radai_config.linhas_da_tabela(mod) if mod else ([], u"")
        ok, r = radai_config.gravar_protocolo(bruto, linhas, caminho_cfg=caminho)
        if ok:
            p = r["protocolo"]
            _log(u"protocolo proprio gravado pela tela: %s (%s, %d estrutura(s), "
                 u"%d uniao(oes)%s)" % (p["nome"], p["modalidade"],
                                        len(p["estruturas"]), len(p["merges"]),
                                        u", procura ACHADO" if p["tem_achado"]
                                        else u""))
        return r

    @app.post("/api/config/protocolos/apagar")
    async def _apagar_protocolo(request: Request):
        c = await _corpo(request)
        if c is None:
            return _grande()
        ok, erro = radai_config.apagar_protocolo(u"%s" % (c.get("id") or u""),
                                                 caminho_cfg=caminho)
        if ok:
            _log(u"protocolo proprio apagado pela tela de configuracoes")
        return {"ok": ok, "erro": erro}

    @app.post("/api/config/exportar")
    def _exportar():
        return radai_config.exportar(caminho, todas, versao=_versao())

    @app.post("/api/config/importar/previa")
    async def _previa(request: Request):
        c = await _corpo(request)
        if c is None:
            return _grande()
        return radai_config.previa_da_importacao(
            c.get("dados"), caminho, todas,
            radai_config.estruturas_por_modalidade())

    @app.post("/api/config/importar")
    async def _importar(request: Request):
        c = await _corpo(request)
        if c is None:
            return _grande()
        secoes = c.get("secoes") if isinstance(c.get("secoes"), list) else []
        r = radai_config.importar(c.get("dados"), secoes, caminho, todas,
                                  radai_config.estruturas_por_modalidade(),
                                  modelo=modelo)
        if r.get("ok"):
            g = r.get("gravado") or {}
            _log(u"configuracoes importadas pela tela: %s" % u", ".join(
                u"%s=%s" % (k, (len(v) if isinstance(v, list) else v))
                for k, v in sorted(g.items())))
        r.pop("previa", None)
        return r

    return app
