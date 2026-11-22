$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$root=(Resolve-Path (Join-Path $PSScriptRoot '../../programa')).Path
$prepare=Join-Path $root 'packager/prepare.ps1'
$tree=[Management.Automation.Language.Parser]::ParseFile($prepare,[ref]$null,[ref]$null)
foreach($name in @('PastaQueOPacoteOcupa','RaizParaOInstalador','MarcaDeInstalacaoAntiga','MarcaDeInstalacao')){
    $def=$tree.Find({param($ast) $ast -is [Management.Automation.Language.FunctionDefinitionAst] -and $ast.Name -eq $name},$false)
    Invoke-Expression $def.Extent.Text
}
function Anote {}
$scriptInstall=[IO.File]::ReadAllText((Join-Path $root 'installer/INSTALL.ps1'))
$inicio=$scriptInstall.IndexOf('$folha = Split-Path -Leaf $RAIZ')
$fim=$scriptInstall.IndexOf('Diga ("   " + $DESTINO)',$inicio)
if($inicio -lt 0 -or $fim -lt 0){throw 'Cannot locate the offline destination assignment'}
$decidir=[scriptblock]::Create($scriptInstall.Substring($inicio,$fim-$inicio))
$fixtureRoot=Join-Path ([IO.Path]::GetTempPath()) ('suite-destino-'+[Guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($fixtureRoot)
try {
    $PROJETO='LOCAL_SUITE'; $NO_LUGAR=''
    foreach ($folder in @('nova','LOCAL_SUITE','suite-renomeada','suite-antiga')){
        $p=Join-Path $fixtureRoot $folder
        [void][IO.Directory]::CreateDirectory($p)
        if($folder -ne 'nova'){
            [IO.File]::WriteAllText((Join-Path $p 'radai_watcher.py'),'')
            if($folder -eq 'suite-antiga'){
                [void][IO.Directory]::CreateDirectory((Join-Path $p 'python'))
                [IO.File]::WriteAllText((Join-Path $p 'python/python.exe'),'')
            }else{[IO.File]::WriteAllText((Join-Path $p 'entrega.txt'),'PROJETO=LOCAL_SUITE')}
        }
        $esperado=if($folder -eq 'nova'){Join-Path $p $PROJETO}else{$p}
        $previsto=PastaQueOPacoteOcupa $p $PROJETO
        $env:RADAI_RAIZ_INSTALACAO=RaizParaOInstalador $p $PROJETO
        $RAIZ=$env:RADAI_RAIZ_INSTALACAO
        . $decidir
        if($previsto -ine $esperado -or $DESTINO -ine $esperado){throw ("Unexpected destination: " + $DESTINO + ' / ' + $previsto)}
        Write-Host ('PASS destination '+$folder)
    }
}finally{
    if([IO.Path]::GetDirectoryName($fixtureRoot).TrimEnd('\') -ine [IO.Path]::GetTempPath().TrimEnd('\') -or [IO.Path]::GetFileName($fixtureRoot) -notmatch '^suite-destino-[a-f0-9]{32}$'){throw 'Unexpected fixture path'}
    Remove-Item -LiteralPath $fixtureRoot -Recurse -Force
}
