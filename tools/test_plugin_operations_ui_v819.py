import ast
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
import radai_languages as LANG
import radai_phrases as PHRASES
import radai_plugin_setup_i18n as I18N
import radai_plugin_setup_ui as UI
import radai_ui

TEXTS = (
    'Instalar / atualizar apenas o código offline',
    'Instalar / atualizar o pacote de pesos offline',
    'Escolha o SETUP leve. Os pesos instalados são preservados.',
    'Escolha o ZIP do bundle de pesos. O código carregado é preservado.',
    'Código carregado', 'Pacote de pesos', 'Usar uma pasta já extraída',
    'Código offline', 'Pacote de pesos offline', 'Enviando ZIP local…',
    'Escolha um único arquivo ZIP.', 'Ainda não instalado',
    'Instalado · versão não registrada', 'Pesos prontos', 'Pesos não instalados',
    'Pesos incompletos', 'Conferindo os pesos…', 'Instalar ou atualizar %s',
    'O código do LUNG RT está atualizado.', 'O código do NEURO RT está atualizado.',
    'Instalar ou atualizar os pesos', 'Prepare os pesos que faltam usando o código instalado.',
    'Servidores de atualização do código',
    'O código deste pacote é mais antigo. Use o pacote de pesos offline ou um SETUP atualizado.',
    'Escolha o bundle de pesos completo preparado para levar.',
    'Confira o pacote na opção correta de código ou pesos.',
    'Não há espaço livre suficiente para copiar o ZIP local.',
    'O ZIP excede o limite permitido para esta operação.',
    'Operação de instalação inválida.', 'Escolha o ZIP do código offline.',
    'Atualize o código da Local Suite antes de preparar os pesos.',
    'Confira novamente o código carregado antes de preparar os pesos.',
    'O código ativo mudou durante o preparo. Reabra e confira a instalação.',
    'Conferir pesos',
    'O código dos plugins é atualizado pelo instalador principal da Local Suite.',
    'Esta ferramenta precisa dos modelos adicionais do NEURO RT. Deseja abrir as configurações para preparar os pesos?',
    'Possível 3D TOF · confirmar', 'Possível TOF · confirmar',
    'Sugestão pelos metadados; confirme a sequência e escolha a série original, sem MIP.',
    'Qualidade máxima · dados originais', 'Maximizar angiografia', 'Restaurar estação',
    'Centrar consenso', 'Anatomia na entrega',
    'Consenso vazio: ajuste a temperatura ou revise as incidências.', 'Não foi possível centrar o consenso.',
    'Incidências guardadas', 'Exportar sugestão', 'Anatomia', 'Tecidos', 'Vasos',
    'Preparando recursos', 'Baixando componentes',
)

CONTROLLER = r'''<script>
document.addEventListener('DOMContentLoaded',async()=>{
  window.testAccepted={};window.testPanels={};window.testNotice=[];window.testConsentResult=null;
  const panels=document.querySelectorAll('[data-plugin-install]');
  for(const panel of panels){
    const slug=panel.dataset.pluginInstall;let locked=false;
    const setup=window.RadaiPluginSetup.bind(panel,{
      tokenHeader:slug==='neuro-rt'?'X-Neuro-Plugin-Token':'X-Lung-Plugin-Token',
      status:async()=>await(await fetch('/api/plugins/'+slug)).json(),
      reset(){delete window.testAccepted[slug];},
      lock(value){locked=value;},isLocked:()=>locked,
      accept(id,version,current,format){window.testAccepted[slug]={id,version,current,format};}
    });
    window.testPanels[slug]=setup;
    setup.versions(await(await fetch('/api/plugins/'+slug)).json());setup.sync();
    new MutationObserver(()=>window.testNotice.push(panel.querySelector('[data-pi-source]').textContent))
      .observe(panel.querySelector('[data-pi-source]'),{childList:true,characterData:true,subtree:true});
  }
  document.getElementById('open-test-terms').onclick=async()=>{
    window.testConsentResult=await window.RadaiPluginSetup.confirmInstallation({accepted:false,
      policy:{title:'LUNG RT',clauses:['SYNTHETIC LUNG TERMS']}}
      ,'LUNG RT');
  };
  document.getElementById('open-test-accepted').onclick=async()=>{
    window.testConsentResult=await window.RadaiPluginSetup.confirmInstallation({accepted:true},'LUNG RT');
  };
  window.testReady=true;
});</script>'''


class PluginOperationsUI(unittest.TestCase):
    def test_new_words_have_canonical_translations_and_legacy_keys_survive(self):
        required = set(TEXTS)
        table = {PHRASES.normalizar(row[0]): row for row in I18N.TABELA}
        for text in required:
            self.assertIn(text, table)
            self.assertEqual(len(table[text]), 12)
            for code, translated in zip(PHRASES.CODIGOS, table[text][1:]):
                self.assertEqual(LANG.FRASES[code][text], PHRASES.normalizar(translated))
                if '%s' in text:
                    self.assertIn('%s', translated)
        for text in ('ZIP do instalador', 'Pasta local ou bundle'):
            self.assertIn(text, table)

    def test_both_panels_have_zip_dropzones_without_inline_terms(self):
        for plugin in ('neuro', 'lung'):
            page = UI.controls(settings=True, plugin=plugin)
            self.assertEqual(page.count('accept=".zip,application/zip"'), 1)
            self.assertNotIn('data-pi-choice="zip"', page)
            self.assertNotIn('data-pi-file', page)
            self.assertIn('data-pi-weights-drop', page)
            self.assertEqual(page.count('data-pi-feedback'), 1)
            self.assertNotIn('data-pi-last', page)
            self.assertNotIn('data-pi-error', page)
            self.assertIn('data-pi-code-version', page)
            self.assertIn('data-pi-weights-version', page)
            self.assertNotIn('LUNG RT está em fase de testes.', page)
            self.assertNotIn('lp-policy', page)
            self.assertNotIn('lp-accept', page)

    def test_browser_code_weights_separation_modal_and_twelve_languages(self):
        node = shutil.which('node')
        module = Path(os.environ.get('RADAI_PLAYWRIGHT_MODULE', str(Path.home() / '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright')))
        chrome = Path(os.environ.get('RADAI_CHROME', r'C:\Program Files\Google\Chrome\Application\chrome.exe'))
        if not node or not module.is_dir() or not chrome.is_file():
            self.skipTest('Chrome and Playwright not installed')
        with tempfile.TemporaryDirectory(prefix='plugin-operations-ui-') as folder:
            directory = Path(folder)
            page = ('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                    '<style>' + radai_ui.TOKENS + radai_ui.COMPONENTES + radai_ui.BOTOES +
                    'body{margin:0;padding:16px;background:var(--bg-0);color:var(--text);font-family:var(--font-display)}main{max-width:1060px;margin:auto}section+section{margin-top:24px}'
                    '</style></head><body><main>' + UI.controls(True) + UI.controls(True, plugin='lung') +
                    '<button id="open-test-terms">Open terms</button><button id="open-test-accepted">Open accepted</button></main>' +
                    radai_ui.JS + radai_ui.COMPONENTES_JS + '</body></html>')
            page = UI.assets(page)
            page = LANG.aplicar(page)
            page = page.replace('</body>', CONTROLLER + '</body>')
            (directory / 'config.html').write_text(page, encoding='utf8')
            (directory / 'languages.js').write_text(LANG.corpo_js(), encoding='utf8')
            expected = {code: {text: text if code == 'pt-BR' else LANG.FRASES[code].get(PHRASES.normalizar(text), text)
                               for text in TEXTS + ('Arraste o ZIP ou clique para escolher', 'Disponível', 'Pesos prontos', 'Pesos incompletos')}
                        for code in ('pt-BR', *PHRASES.CODIGOS)}
            (directory / 'expected.json').write_text(json.dumps(expected, ensure_ascii=False), encoding='utf8')
            result = subprocess.run([node, str(Path(__file__).with_name('plugin_operations_ui_v819_browser.cjs')), str(directory), str(module), str(chrome)], capture_output=True, text=True, encoding='utf8', errors='replace', timeout=180)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('PASS 12 locales', result.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
