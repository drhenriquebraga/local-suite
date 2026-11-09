import base64
import json
import importlib.util
import sys
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'packager/prepare.ps1'
sys.path[:0] = [str(ROOT/'tools'), str(ROOT/'app'), str(ROOT/'build')]
spec=importlib.util.spec_from_file_location('suite_prepare_profile_test', ROOT/'build/configurar_ambiente.py')
PROFILE=importlib.util.module_from_spec(spec)
spec.loader.exec_module(PROFILE)


def ps_run(body, names):
    quoted = str(SCRIPT).replace("'", "''")
    selected = ','.join("'" + name + "'" for name in names)
    prelude = r"""
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
$tokens=$null;$parseErrors=$null
$ast=[System.Management.Automation.Language.Parser]::ParseFile('__SCRIPT__',[ref]$tokens,[ref]$parseErrors)
if($parseErrors.Count){throw ($parseErrors | Out-String)}
$names=@(__NAMES__)
foreach($definition in $ast.FindAll({param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst]},$false)){
    if($names -contains $definition.Name){Invoke-Expression $definition.Extent.Text}
}
""".replace('__SCRIPT__', quoted).replace('__NAMES__', selected)
    encoded = base64.b64encode((prelude + body).encode('utf-16le')).decode()
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-STA', '-EncodedCommand', encoded], capture_output=True, encoding='utf-8', timeout=30)
    if result.returncode:
        raise AssertionError(result.stderr or result.stdout)
    return json.loads(result.stdout.strip().splitlines()[-1])


@unittest.skipUnless(os.name == 'nt', 'PowerShell Windows contract')
class PrepareProfileTests(unittest.TestCase):
    def route(self, folder, choice):
        body = r"""
$script:Ocupado=$false
$script:Instalado=@{pasta='__FOLDER__';como='synthetic';versao='8.14'}
$script:calls=@()
$script:PerfilPreparo='full'
function ConferirInstalacao {return $script:Instalado}
function EscolherPerfilCompacto {return '__CHOICE__'}
function IniciarAtualizarApp {param($Inst) $script:calls+='update'}
function Sessao {param($Texto)}
function Falhar {param($Texto) $script:calls+='error'}
function MarcarModo {param([string]$Qual,[switch]$CompletarSuite) $script:calls+=('mode:'+ $Qual +':full='+[bool]$CompletarSuite)}
$result=InstalarOuAtualizar
@{result=$result;calls=@($script:calls);intent=$script:PerfilPreparo}|ConvertTo-Json -Compress
""".replace('__FOLDER__', str(folder).replace("'", "''")).replace('__CHOICE__', choice)
        return ps_run(body, ['InstalarOuAtualizar', 'PerfilDaInstalacao'])

    def test_compact_complete_is_explicit_mode7_not_code_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            (folder/'suite-profile.json').write_text(json.dumps({'schema':'local-suite/profile/1','profile':'lung-rt'}))
            result=self.route(folder,'full')
            self.assertEqual(result['calls'],['mode:7:full=True'])
            self.assertEqual(result['result'],'completar')


    def test_existing_compact_update_keeps_profile_and_sentinels(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            (folder/'suite-profile.json').write_text(json.dumps({'schema':'local-suite/profile/1','profile':'lung-rt'}))
            for name in ('Plugins/LUNG RT/data/test.txt','registro/test.txt','radai_watcher.config','python/python.exe'):
                file=folder/name;file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(b'synthetic sentinel only')
            before={p.relative_to(folder):p.read_bytes() for p in folder.rglob('*') if p.is_file()}
            result=self.route(folder,'manter')
            self.assertEqual(result['calls'],['update'])
            self.assertEqual(result['intent'],'')
            self.assertEqual(PROFILE.perfil_do_destino(None,folder),'lung-rt')
            after={p.relative_to(folder):p.read_bytes() for p in folder.rglob('*') if p.is_file()}
            self.assertEqual(after,before)

    def test_cancel_never_starts_update_or_preparation(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            (folder/'suite-profile.json').write_text(json.dumps({'schema':'local-suite/profile/1','profile':'lung-rt'}))
            result=self.route(folder,'cancelar')
            self.assertEqual(result['calls'],[])
            self.assertEqual(result['result'],'cancelado')

    def test_full_or_legacy_install_uses_existing_update_flow(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            for value in (None,{'schema':'local-suite/profile/1','profile':'full'}):
                if value:(folder/'suite-profile.json').write_text(json.dumps(value))
                result=self.route(folder,'full')
                self.assertEqual(result['calls'],['update'])
                self.assertEqual(result['intent'],'')

    def test_invalid_profile_fails_before_update_or_prepare(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            for value in ('invalid json',json.dumps({'schema':'wrong','profile':'lung-rt'}),json.dumps({'schema':'local-suite/profile/1','profile':'unknown'})):
                (folder/'suite-profile.json').write_text(value)
                result=self.route(folder,'full')
                self.assertEqual(result['calls'],['error'])
                self.assertEqual(result['result'],'erro')

    def test_new_install_enters_normal_install_mode(self):
        body=r"""
$script:Ocupado=$false
$script:calls=@()
function ConferirInstalacao {return $null}
function Sessao {param($Text)}
function MarcarModo {param($Qual) $script:calls+=('mode:'+ $Qual)}
$result=InstalarOuAtualizar
@{result=$result;calls=@($script:calls)}|ConvertTo-Json -Compress
"""
        result=ps_run(body,['InstalarOuAtualizar'])
        self.assertEqual(result,{'result':'instalar','calls':['mode:1']})

    def test_modes_bind_and_clear_explicit_full_intent(self):
        body=r"""
function T {param($Text) return $Text}
function GarantirInstalacao {param($Title) return @{pasta='X:\synthetic'}}
function AplicarModo {}
function AtualizarSugestaoPasta {}
$script:Cor=@{Ok='green';Painel='black';Botao='gray';Titulo='white'}
$btModo1=[pscustomobject]@{BackColor='';ForeColor=''}
$btModo2=[pscustomobject]@{BackColor='';ForeColor=''}
$btModo3=[pscustomobject]@{BackColor='';ForeColor=''}
$rotModo=[pscustomobject]@{Text=''}
$abas=[pscustomobject]@{SelectedTab=''};$aba1='before'
$cases=@()
foreach($step in @(@('7',$true),@('7',$false),@('1',$true),@('2',$true),@('3',$false))){
    MarcarModo $step[0] -CompletarSuite:$step[1]
    $cases+=@{mode=$script:Modo;profile=$script:PerfilPreparo;tab=$abas.SelectedTab}
}
@{cases=$cases}|ConvertTo-Json -Depth 4 -Compress
"""
        result=ps_run(body,['MarcarModo'])
        self.assertEqual([x['profile'] for x in result['cases']],['full','','','',''])
        self.assertTrue(all(x['tab']=='before' for x in result['cases']))

    def test_actual_motor_arguments_select_all_tasks_only_for_explicit_full(self):
        body=r"""
$motor='C:\synthetic path\configurar_ambiente.py'
$target='D:\synthetic estação\LOCAL_SUITE'
$cases=@()
foreach($step in @(@('7','full'),@('7',''),@('1',''),@('2',''))){
    $script:Modo=$step[0];$script:PerfilPreparo=$step[1]
    $arguments=@(ArgumentosDoPreparo $motor $target)
    $cases+=@{arguments=$arguments;line=(LinhaDeArgumentos $arguments)}
}
@{cases=$cases}|ConvertTo-Json -Depth 4 -Compress
"""
        result=ps_run(body,['ModoDireto','ArgumentosDoPreparo','LinhaDeArgumentos'])
        full,compact,new,package=[c['arguments'] for c in result['cases']]
        self.assertEqual(full[-2:],['--profile','full'])
        self.assertEqual(full[1],'--instalar')
        self.assertNotIn('--profile',compact)
        self.assertNotIn('--profile',new)
        self.assertEqual(package[1],'--preparo')
        self.assertIn('"D:\\synthetic estação\\LOCAL_SUITE"',result['cases'][0]['line'])
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            (folder/'suite-profile.json').write_text(json.dumps({'schema':'local-suite/profile/1','profile':'lung-rt'}))
            selected=PROFILE.perfil_do_destino(full[-1],folder)
            self.assertEqual(PROFILE.tasks_do_perfil({'profile':selected}),PROFILE.TASKS)
            self.assertGreater(len(PROFILE.TASKS),len(PROFILE.TASKS_LUNG))
            kept=PROFILE.perfil_do_destino(None,folder)
            self.assertEqual(PROFILE.tasks_do_perfil({'profile':kept}),PROFILE.TASKS_LUNG)

    def test_preparation_process_uses_reviewed_argument_builder(self):
        body=r"""
$preparar=$ast.FindAll({param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Preparar'},$false)|Select-Object -First 1
if(-not $preparar){throw 'preparation function missing'}
$assignments=@($preparar.FindAll({param($n) $n -is [System.Management.Automation.Language.AssignmentStatementAst] -and $n.Left.Extent.Text -eq '$argumentos'},$true))
$builders=@($preparar.FindAll({param($n) $n -is [System.Management.Automation.Language.CommandAst] -and $n.GetCommandName() -eq 'ArgumentosDoPreparo'},$true))
@{assignments=$assignments.Count;builders=$builders.Count;rhs=$assignments[0].Right.Extent.Text}|ConvertTo-Json -Compress
"""
        result=ps_run(body,[])
        self.assertEqual(result['assignments'],1)
        self.assertEqual(result['builders'],1)
        self.assertEqual(result['rhs'],'@(ArgumentosDoPreparo $motor $trab)')

    def test_dialog_hidden_layout_and_safe_default_in_twelve_languages(self):
        body=r"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
. '__LANGUAGES__'
[void](Carregar-Idiomas '__PACKAGER__')
$script:Cor=@{Ok=[Drawing.Color]::Lime;Painel=[Drawing.Color]::Black;Botao=[Drawing.Color]::DarkSlateGray;Titulo=[Drawing.Color]::Cyan;Texto=[Drawing.Color]::White;Fraco=[Drawing.Color]::Silver}
$results=@()
foreach($language in $script:CodigosIdioma){
    $script:IdiomaAtual=$language
    $d=NovaEscolhaPerfilCompacto
    try{
        $d.CreateControl();$d.PerformLayout()
        $outside=@($d.Controls|Where-Object {$_.Right -gt $d.ClientSize.Width -or $_.Bottom -gt $d.ClientSize.Height -or $_.Left -lt 0 -or $_.Top -lt 0})
        $clipped=@()
        foreach($control in $d.Controls){
            $size=[Drawing.Size]::new(($control.Width-12),32767)
            $measure=[Windows.Forms.TextRenderer]::MeasureText($control.Text,$control.Font,$size,[Windows.Forms.TextFormatFlags]::WordBreak)
            if($measure.Height -gt ($control.Height-6)){$clipped+= $control.Text}
        }
        $results+=@{language=$language;outside=$outside.Count;clipped=@($clipped);default=[string]$d.AcceptButton.DialogResult;cancel=[string]$d.CancelButton.DialogResult;rtl=[string]$d.RightToLeft;controls=$d.Controls.Count;visible=$d.Visible}
    }finally{$d.Dispose()}
}
@{results=$results}|ConvertTo-Json -Depth 5 -Compress
""".replace('__LANGUAGES__',str(ROOT/'packager/languages.ps1').replace("'","''")).replace('__PACKAGER__',str(ROOT/'packager').replace("'","''"))
        result=ps_run(body,['NovaEscolhaPerfilCompacto','Fonte','NovoRotulo','NovoBotao'])
        self.assertEqual(len(result['results']),12)
        for item in result['results']:
            self.assertEqual(item['outside'],0,item)
            self.assertEqual(item['clipped'],[],item)
            self.assertEqual(item['default'],'No',item)
            self.assertEqual(item['cancel'],'Cancel',item)
            self.assertEqual(item['controls'],5,item)
            self.assertFalse(item['visible'],item)
            self.assertEqual(item['rtl'],'Yes' if item['language']=='ar' else 'No')


if __name__ == '__main__':
    unittest.main(verbosity=2)
