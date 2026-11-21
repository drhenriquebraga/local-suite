$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot '../programa/packager/TERMOS_SUITE.ps1')
$testRaiz=Join-Path ([IO.Path]::GetTempPath()) ('local-suite-termos-'+[Guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($testRaiz)
try {
    function Caminho-ReciboInstalador($Catalogo) {return (Join-Path $testRaiz ($Catalogo.perfil+'/vigente/LICENCAS_COMPONENTES.json'))}
    function UsuarioDosTermos {return 'S-TEST-LOCAL-SUITE'}
    function Assert($ok,[string]$msg) { if (!$ok) {throw $msg}; Write-Host ('PASS '+$msg) }
    function WriteJson($obj,$path) { [IO.File]::WriteAllText($path,($obj|ConvertTo-Json -Depth 15),[Text.UTF8Encoding]::new($false)) }
    $cat=Join-Path $testRaiz 'licencas_suite.json'
    $pol=Join-Path $testRaiz 'termos_instalador.json'
    Copy-Item (Join-Path $PSScriptRoot '../programa/app/data/licencas_suite.json') $cat
    Copy-Item (Join-Path $PSScriptRoot '../programa/app/data/termos_instalador.json') $pol
    $c=Ler-CatalogoSuite $cat full $null $null
    Assert ($c.condicoes.Count -eq 5 -and !$c.condicoes.ContainsKey('jhu_rectum')) 'Five actual material clauses in full profile; JHU informational'
    Assert (!(Obter-ReciboVigente $cat full)) 'New operator has no implicit consent'
    $env:RADAI_IDIOMA='pt-BR'
    $f=Nova-JanelaTermosSuite $c
    try {
        $f.Opacity=0; $f.ShowInTaskbar=$false; $f.Show(); $s=$f.Tag.Tag
        Assert ($s.btn.Enabled -and $s.btn.Text -eq 'Aceito todos os termos de uso') 'One action enabled with no scrolling'
        Assert ($s.texto.DetectUrls -and $s.texto.Text.Contains('https://') -and $s.texto.Text.IndexOf('Infraestrutura') -lt $s.texto.Text.IndexOf('Modelos de segmenta')) 'WinForms viewer has links and grouped infrastructure first'
        $nv=$s.menu.Items | Where-Object {$_.Tag -eq 'nv_segment_ct'}
        $nv.Checked=$false
        Assert (!$s.texto.Text.Contains('huggingface.co/nvidia/NV-Segment-CT')) 'Omitted optional terms hidden'
        $s.btn.PerformClick()
        Assert ($s.recibo -and (Testar-ReciboInstalador $s.recibo $c)) 'Single click produced verifiable receipt'
    } finally { $f.Dispose() }
    Assert ([bool](Obter-ReciboVigente $cat full)) 'Later installer step reuses receipt'
    $d=DecisaoAnteriorSuite $c
    Assert ($d.omitidos -contains 'nv_segment_ct') 'Optional choice retained'
    $oldPath=Caminho-ReciboInstalador $c
    $env:PYTHONDONTWRITEBYTECODE='1'
    python -B -c "import sys,platform; sys.path.insert(0,sys.argv[1]); import consentimento_instalador as cs; assert cs.validar(sys.argv[2],sys.argv[3],'full','S-TEST-LOCAL-SUITE',platform.node())=={'nv_segment_ct'}" (Join-Path $PSScriptRoot '../programa/build') $cat $oldPath
    Assert ($LASTEXITCODE -eq 0) 'Python verifier accepts WinForms receipt'
    $doc=$c.doc; $doc.itens[0].titulo='A revised attribution'; WriteJson $doc $cat
    Assert ([bool](Obter-ReciboVigente $cat full)) 'Attribution change skips consent'
    $policy=$c.politica; $policy.condicoes.rocards_lad.revisao='revision-test'; WriteJson $policy $pol
    $changed=Ler-CatalogoSuite $cat full
    Assert (!(Obter-ReciboVigente $cat full) -and (@(PendenciasDosTermos $changed $d $d.omitidos) -join ',') -ceq 'rocards_lad') 'Only changed ROCardS terms required'
    $wrong=Ler-DecisaoInstalador $oldPath $changed
    $record=[IO.File]::ReadAllText($oldPath)|ConvertFrom-Json
    $record.usuario_sid='S-OTHER'; WriteJson $record $oldPath
    Assert (!(DecisaoAnteriorSuite $changed)) 'Receipt cannot transfer between operators'
    Copy-Item (Join-Path $PSScriptRoot '../programa/app/data/licencas_suite.json') $cat -Force
    Copy-Item (Join-Path $PSScriptRoot '../programa/app/data/termos_instalador.json') $pol -Force
    $legado=Join-Path $testRaiz ('full/'+$c.sha+'/LICENCAS_COMPONENTES.json')
    [void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($legado))
    $old=[ordered]@{schema='local-suite/aceite/1';contexto='instalador';finalidade='ensino-pesquisa';perfil='full';usuario_sid=(UsuarioDosTermos)
        maquina=[Environment]::MachineName;utc='2026-11-21T01:00:00Z';catalogo_sha256=$c.sha;itens=@(foreach ($i in $c.elegiveis.Values) { if ($i.ferramenta -ne 'moose') { @{id=$i.id;sha256=$i.sha256} } })}
    WriteJson $old $legado
    Assert ([bool](Obter-ReciboVigente $cat full)) 'Valid 8.30 consent migrated with zero interactions'
    $m=DecisaoAnteriorSuite $c
    Assert ($m.origem -eq 'local-suite/aceite/2' -and $m.utc -eq $old.utc -and ($m.omitidos -contains 'moose')) 'Migration retains optional decisions and original consent date'
    Assert ($PSVersionTable.PSVersion.Major -eq 5) 'Windows PowerShell 5.1'
} finally {
    if ([IO.Path]::GetDirectoryName($testRaiz).TrimEnd('\') -ine [IO.Path]::GetTempPath().TrimEnd('\') -or [IO.Path]::GetFileName($testRaiz) -notmatch '^local-suite-termos-[a-f0-9]{32}$') { throw 'Unexpected test directory' }
    Remove-Item -LiteralPath $testRaiz -Recurse -Force
}
