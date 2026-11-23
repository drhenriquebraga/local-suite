# Behavioral checks on the real WinForms controls, with receipts isolated from the station.
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$base=Split-Path -Parent $PSScriptRoot
. (Join-Path $base 'packager/TERMOS_SUITE.ps1')
. (Join-Path $base 'packager/PLUGIN_OPTIONS.ps1')
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.IO.Compression.FileSystem
function T([string]$Texto) { return $Texto }
function Verificar([bool]$ok,[string]$mensagem) { if (-not $ok) { throw $mensagem } }
$temp=[IO.Directory]::CreateDirectory((Join-Path ([IO.Path]::GetTempPath()) ('suite-termos-teste-'+[guid]::NewGuid().ToString('N')))).FullName
function Caminho-ReciboInstalador($Catalogo) { return (Join-Path $temp ($Catalogo.perfil+'/vigente/LICENCAS_COMPONENTES.json')) }
function UsuarioDosTermos { return 'TEST-SID' }
function IdiomaDosTermos { return $script:idioma }
function CarregarFuncaoPreparador([string]$Nome) {
    $def=$script:ast.Find({ param($no) $no -is [Management.Automation.Language.FunctionDefinitionAst] -and $no.Name -eq $Nome },$true)
    if (-not $def) { throw "Missing function: $Nome" }
    $fonte=$def.Extent.Text -replace ('^function '+[regex]::Escape($Nome)),('function script:'+$Nome)
    . ([scriptblock]::Create($fonte))
}
$arquivo=Join-Path $base 'app/data/licencas_suite.json'
try {
    $script:idioma='pt-BR'
    $catalogos=@(foreach ($perfil in @('full','plugin-neuro','plugin-lung','plugin-coronarias')) { Ler-CatalogoSuite $arquivo $perfil })
    $ctx=@(ContextosDosTermos $catalogos)
    Verificar (-not (RecibosDosContextos $ctx)) 'Aceite concedido antes da confirmação.'
    $p=Novo-PainelTermosSuite $catalogos[0] $ctx
    $f=[Windows.Forms.Form]::new(); $f.Size=[Drawing.Size]::new(900,620); $f.Controls.Add($p)
    try {
        $cb=$p.Tag.caixas
        Verificar ($cb.Count -eq 6 -and $cb.ContainsKey('rocards_lad') -and $cb.ContainsKey('lung-medgemma')) 'Condições da seleção incompletas.'
        Verificar ($p.Tag.btn.Enabled -and -not @($cb.Values | Where-Object {-not $_.Checked}).Count) 'Termos devem iniciar marcados.'
        Verificar (@(Get-ChildItem -LiteralPath $temp -Force).Count -eq 0) 'O desenho da tela gravou aceite.'
        $cb['rocards_lad'].Checked=$false
        Verificar (-not $p.Tag.btn.Enabled) 'Aceite de pesquisa desmarcado mas o botão prossegue.'
        foreach ($loc in $catalogos[0].politica.ui.PSObject.Properties.Name) {
            $script:idioma=$loc; Desenhar-TermosSuite $p
            Verificar (-not $p.Tag.caixas['rocards_lad'].Checked) 'A troca de idioma marcou um aceite recusado.'
            Verificar (@($p.Tag.lista.Controls | Where-Object {$_ -is [Windows.Forms.LinkLabel] -and $_.Tag.Scheme -eq 'https'}).Count -eq 6) 'Link ausente.'
            Verificar ($p.Tag.btn.Text -eq $catalogos[0].politica.ui.$loc.aceitar) 'Botão sem tradução.'
        }
        $p.Tag.caixas['rocards_lad'].Checked=$true
        $aceite=$p.Tag.btn.GetType().GetMethod('OnClick',[Reflection.BindingFlags]'NonPublic,Instance')
        $aceite.Invoke($p.Tag.btn,@([EventArgs]::Empty))
        Verificar ($p.Tag.concluido -and -not $p.Tag.btn.Enabled) 'Não encerrou após um clique.'
        foreach ($i in @(0,2,3)) { Verificar (Testar-ReciboInstalador $ctx[$i].recibo $catalogos[$i]) 'Recibo inválido.' }
        Verificar (-not (Test-Path -LiteralPath (Caminho-ReciboInstalador $catalogos[1]))) 'Registrou aceite fictício do NEURO.'
        Verificar (RecibosDosContextos @(ContextosDosTermos $catalogos)) 'Reabriu condições inalteradas.'
        Verificar (RecibosDosContextos @(ContextosDosTermos @($catalogos[1]))) 'NEURO isolado abriu uma janela vazia.'
        $soLung=Novo-PainelTermosSuite $catalogos[2]
        try {
            Verificar ($soLung.Tag.caixas.Count -eq 1 -and $soLung.Tag.caixas.ContainsKey('lung-medgemma')) 'LUNG isolado incluiu outras licenças.'
            $links=@($soLung.Tag.lista.Controls | Where-Object {$_ -is [Windows.Forms.LinkLabel] -and $_.Tag.IsFile -and [IO.File]::Exists($_.Tag.LocalPath)})
            Verificar ($links.Count -eq 2) 'Termos e política devem estar disponíveis mesmo offline.'
        }
        finally { $soLung.Dispose() }
        $semNv=Ler-CatalogoSuite $arquivo 'full' @('nv_segment_ct')
        $pSemNv=Novo-PainelTermosSuite $semNv
        try { Verificar (-not $pSemNv.Tag.caixas.ContainsKey('nv_segment_ct')) 'Incluiu comparador ausente do ZIP.' }
        finally { $pSemNv.Dispose() }
    } finally { $f.Dispose() }
    $catalogoPlugins=Ler-CatalogoPluginsSuite (Join-Path $base 'packager/plugin-options.json')
    $zipPath=Join-Path $temp 'transport-renamed.zip'
    $zip=[IO.Compression.ZipFile]::Open($zipPath,'Create')
    try {
        $out=[IO.StreamWriter]::new($zip.CreateEntry('release-manifest.json').Open())
        try { $out.Write('{"plugin_id":"lung-rt"}') } finally { $out.Dispose() }
    } finally { $zip.Dispose() }
    $plano=PlanoDosZipsPlugins $catalogoPlugins @($zipPath)
    Verificar ($plano.plugins.Count -eq 1 -and $plano.plugins[0].id -eq 'lung-rt' -and $plano.terms_mode -eq 'installer-v2') 'ZIP renomeado não identificado pelo manifesto.'
    $script:ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $base 'packager/prepare.ps1'),[ref]$null,[ref]$null)
    foreach ($nome in @('ContinuarComTermos','RetomarAcaoDosTermos','AtualizarRotuloDaPasta')) { CarregarFuncaoPreparador $nome }
    function ModoDireto { return $false }
    function PerfilParaTermos { return 'full' }
    function LimparTermosDoPacote($Dados) {}
    function Falhar($Texto) { throw $Texto }
    function MostrarTermosNaAba { param($Arquivo,$Perfil,$Omitidos,$Contextos) $script:pendente=$Contextos }
    function MontarSelecaoPortatil { param($Saida,$Plugins) $script:transportados=$Plugins }
    function VersaoDeixaPreparar { return $true }
    function Preparar { $script:iniciou=$true }
    $script:CatalogoDeTermos=$arquivo; $script:Ocupado=$false; $script:AcaoDosTermos=$null; $script:Modo='2'
    $script:BtRodar=@{Visible=$true}; $script:PainelTermosAtual=$null; $script:pendente=$null
    $abas=@{SelectedTab='home'}; $aba3='progress'; $script:RotuloPasta=@{Text=''}
    AtualizarRotuloDaPasta
    Verificar ($script:RotuloPasta.Text -eq 'Pasta de destino') 'A montagem exibe espaço fixo antes de verificar o destino.'
    ContinuarComTermos 'pluginsPortateis' @{saida=$temp;plugins=@('neuro-rt')} -Plugins @('neuro-rt')
    Verificar (-not $script:pendente -and $script:transportados[0] -eq 'neuro-rt') 'A montagem do NEURO foi interrompida.'
    $script:iniciou=$false
    ContinuarComTermos 'preparar' -Plugins @('neuro-rt','lung-rt','coronarias')
    Verificar (-not $script:pendente -and $script:iniciou) 'A montagem não prosseguiu com os aceites vigentes.'
    $reciboTeste=[IO.Path]::GetFullPath($ctx[3].recibo)
    if (-not $reciboTeste.StartsWith(($temp+'\'),[StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid fixture path.' }
    [IO.File]::Delete($reciboTeste)
    $script:iniciou=$false
    ContinuarComTermos 'preparar' -Plugins @('lung-rt','coronarias')
    Verificar (-not $script:iniciou -and $script:pendente.Count -eq 3) 'Uma condição inédita deve abrir uma única tela antes de montar.'
    # Run the real subprocess bridge with a temporary package. A gallery sentinel
    # stops a permitted execution immediately after the consent check, before copying.
    $script:AQUI=Join-Path $temp 'package/packager'
    $pacote=Split-Path -Parent $script:AQUI
    $destino=Join-Path $temp 'station with spaces'
    foreach ($dir in @($script:AQUI,$destino,(Join-Path $pacote 'app/data'),(Join-Path $pacote 'tools'),(Join-Path $pacote 'build'))) {
        [void][IO.Directory]::CreateDirectory($dir)
    }
    Copy-Item -LiteralPath (Join-Path $base 'packager/UPDATE.ps1') -Destination $script:AQUI
    foreach ($nome in @('licencas_suite.json','termos_instalador.json')) {
        Copy-Item -LiteralPath (Join-Path $base ('app/data/'+$nome)) -Destination (Join-Path $pacote 'app/data')
    }
    [IO.File]::WriteAllText((Join-Path $pacote 'entrega.txt'),"PROJETO=LOCAL_SUITE`nVERSAO=8.30.9")
    [IO.File]::WriteAllText((Join-Path $destino 'radai_watcher.py'),'')
    $requisitos=Join-Path $pacote 'build/requisitos.py'
    [IO.File]::WriteAllText($requisitos,'def comparar_estacao(p,i): return True, []')
    $marcador=Join-Path $destino 'passed-consent'
    [IO.File]::WriteAllText((Join-Path $pacote 'build/galeria_publica.py'),"import sys,pathlib`n(pathlib.Path(sys.argv[2])/'passed-consent').touch()`nsys.exit(1)")
    $python=(Get-Command python.exe).Source
    CarregarFuncaoPreparador 'RodarAtualizador'
    function AcompanharProcesso($pr) {
        try {
            $saida=$pr.StandardOutput.ReadToEndAsync(); $erros=$pr.StandardError.ReadToEndAsync()
            if (-not $pr.WaitForExit(30000)) { $pr.Kill(); throw 'Timed out waiting for UPDATE.ps1 (unexpected UI).' }
            $script:saidaUpdate=$saida.Result+' '+$erros.Result
            return $pr.ExitCode
        } finally { $pr.Dispose() }
    }
    $argPython='-Python "'+$python+'"'
    $script:ReciboIndividual=''
    $rc=RodarAtualizador $destino @('-SoDecidir','-SemPerguntar',$argPython)
    Verificar ($rc -eq 0 -and $script:saidaUpdate -match 'DECISAO=codigo') ('Consulta tentou usar o módulo de termos ou recibo: '+$script:saidaUpdate)
    [IO.File]::WriteAllText($requisitos,'def comparar_estacao(p,i): return False, ["different"]')
    $rc=RodarAtualizador $destino @('-SoDecidir','-SemPerguntar',$argPython)
    Verificar ($rc -eq 3 -and $script:saidaUpdate -match 'DECISAO=pacote') ('Consulta de pacote acessou termos: '+$script:saidaUpdate)
    [IO.File]::WriteAllText($requisitos,'def comparar_estacao(p,i): return True, ["current"]')
    $biblioteca=Join-Path $script:AQUI 'TERMOS_SUITE.ps1'
    Copy-Item -LiteralPath (Join-Path $base 'packager/TERMOS_SUITE.ps1') -Destination $biblioteca
    [IO.File]::AppendAllText($biblioteca,"`r`nfunction Solicitar-TermosSuite { throw 'DUPLICATE FORM' }`r`n")
    function UsuarioDosTermos { return [Security.Principal.WindowsIdentity]::GetCurrent().User.Value }
    $script:ReciboIndividual=Gravar-DecisaoSuite $catalogos[0] @() $null
    $hash=(Get-FileHash -LiteralPath $script:ReciboIndividual).Hash
    $rc=RodarAtualizador $destino @('-SemPerguntar',$argPython)
    Verificar ((Test-Path -LiteralPath $marcador) -and $script:saidaUpdate -notmatch 'DUPLICATE FORM' -and
        $hash -eq (Get-FileHash -LiteralPath $script:ReciboIndividual).Hash) ('Execução não usou o recibo confirmado: '+$script:saidaUpdate)
    [IO.File]::WriteAllText((Join-Path $destino 'suite-profile.json'),'{"schema":"local-suite/profile/1","profile":"lung-rt"}')
    [IO.File]::Delete($marcador)
    $rc=RodarAtualizador $destino @('-SemPerguntar',$argPython)
    Verificar ($rc -eq 2 -and -not (Test-Path -LiteralPath $marcador) -and $script:saidaUpdate -notmatch 'DUPLICATE FORM') 'Recibo de outro perfil aceito.'
    Write-Output 'PASS: UPDATE decision code/package without terms; apply reuses the explicit valid receipt, rejects a mismatched profile and never repeats consent.'
    Write-Output 'PASS: 12 languages, unified explicit consent, scoped receipts, unchanged terms, NEURO alone, offline plugin identity, destination label and packaging entry point.'
} finally {
    $expected=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')+'\'
    if ([IO.Path]::GetFullPath($temp).StartsWith($expected,[StringComparison]::OrdinalIgnoreCase) -and
        (Split-Path -Leaf $temp) -match '^suite-termos-teste-[a-f0-9]{32}$') { [IO.Directory]::Delete($temp,$true) }
}
