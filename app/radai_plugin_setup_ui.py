import json

HINT = 'O instalador reutiliza o Python da suíte e prepara os componentes necessários ao plugin. A suíte fecha durante o preparo e reabre em uma nova janela.'


def controls(settings=False):
    return ('''<section id="neuro-update" data-neuro-install="1" data-neuro-settings="''' +
            ('1' if settings else '0') + '''">
<p id="neuro-update-message" role="status"></p>
<progress id="neuro-update-progress" max="100" hidden></progress>
<div id="neuro-update-actions"></div>
<button type="button" class="sec" id="neuro-release-refresh" data-radai-frase>Verificar atualizações</button>
<p data-radai-frase>''' + HINT + '''</p>
<details id="neuro-local-source"><summary data-radai-frase>Usar instalador ou pacote offline de uma pasta</summary>
<p data-radai-frase>Sem internet nesta estação? Em outra máquina com acesso, abra o START HERE do NEURO RT e monte o pacote offline. Traga a pasta completa para esta estação e selecione abaixo.</p>
<label for="neuro-local-folder" data-radai-frase>Pasta do instalador ou pacote offline</label>
<div class="linha"><input id="neuro-local-folder" type="text" autocomplete="off" spellcheck="false">
<button type="button" class="sec" id="neuro-local-browse" data-neuro-host-browse="1" data-radai-frase>Procurar…</button>
<button type="button" class="sec" id="neuro-local-inspect" data-radai-frase>Conferir pacote local</button></div>
<p id="neuro-local-message" role="status"></p></details></section>''')


BROWSE = '''<script id="neuro-local-browser">
(function(){
 var button=document.getElementById('neuro-local-browse');
 var field=document.getElementById('neuro-local-folder');
 if(!button||!field)return;
 button.addEventListener('click',function(){
  if(typeof window.uiExplorador!=='function'){field.focus();return}
  window.uiExplorador({titulo:'Pasta do instalador NEURO RT',origem:button,inicial:field.value||'',
   aoUsar:function(path){field.value=path||'';field.dispatchEvent(new Event('input',{bubbles:true}));field.dispatchEvent(new Event('change',{bubbles:true}))}});
 });
})();
</script>'''


def scripts():
    import radai_neuro_install as sdk
    catalog = json.dumps(sdk.INSTALL_UI_CATALOG, ensure_ascii=True).replace('<', '\\u003c')
    return ('<script>window.NEURO_INSTALL_CATALOG=' + catalog + ';' +
            sdk.INSTALL_UI_SCRIPT.replace('</script', '<\\/script') + '</script>' + BROWSE)


def config_page(page):
    if 'id="ps_neuro"' in page:
        return page
    card = ''' <a class="cfg-card" href="#ps_neuro" data-alvo="ps_neuro">
<span class="cab"><span class="n">N</span></span>
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
    return page.replace('</body>', scripts() + '</body>', 1)
