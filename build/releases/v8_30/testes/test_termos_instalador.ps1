param([string]$Programa = (Join-Path (Split-Path -Parent $PSScriptRoot) 'programa'))
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
. (Join-Path $Programa 'packager/TERMOS_SUITE.ps1')
$temp = Join-Path ([IO.Path]::GetTempPath()) ('qa-termos-' + [Guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($temp)
try {
    # A operação de escrita só é exercitada com um catálogo fictício, em pasta temporária.
    $cat = Ler-CatalogoSuite (Join-Path $Programa 'app/data/licencas_suite.json') full
    $d = Nova-JanelaTermosSuite $cat
    try {
        $u = $d.Tag
        if ($u.lista.CheckedItems.Count -or $u.avancar.Enabled) { throw 'Aceite automático.' }
        foreach ($i in $u.necessarios.Keys) { $u.lista.SetItemChecked([int]$i,$true) }
        if ($u.avancar.Enabled) { throw 'Finalidade não declarada.' }
        $u.finalidade.Checked=$true
        if (-not $u.avancar.Enabled) { throw 'Botão não liberado com todos os obrigatórios.' }
        $idx=@($u.necessarios.Keys)[0]
        $u.lista.SetItemChecked([int]$idx,$false)
        if ($u.avancar.Enabled) { throw 'Desmarcar uma ferramenta obrigatória precisa desabilitar a continuação.' }
        Write-Output ("UI real: {0} itens, {1} famílias, nenhum recibo gravado." -f $cat.ids.Count,$u.grupos.Count)
    } finally { $d.Dispose() }
    $catalogo = Join-Path $temp 'qa.json'
    $recibo = Join-Path $temp 'QA-RECIBO.json'
    $fake = [ordered]@{schema='local-suite/termos/1'; itens=@(
        @{id='qa-requerido';sha256=('a'*64);perfis=@('full');opcional=$false;ferramenta='base'},
        @{id='qa-opcional';sha256=('b'*64);perfis=@('full');opcional=$true;ferramenta='extra'}
    )}
    [IO.File]::WriteAllText($catalogo,($fake | ConvertTo-Json -Depth 6),[Text.UTF8Encoding]::new($false))
    $c=Ler-CatalogoSuite $catalogo full
    Salvar-ReciboInstalador $c @($c.doc.itens[0]) $recibo
    if (-not (Testar-ReciboInstalador $recibo $c)) { throw 'Recibo válido recusado.' }
    Salvar-ReciboInstalador $c @($c.doc.itens) $recibo
    if (-not (Testar-ReciboInstalador $recibo $c)) { throw 'Troca atômica inválida.' }
    $registro = Get-Content -Raw -Encoding UTF8 -LiteralPath $recibo | ConvertFrom-Json
    $registro.catalogo_sha256 = '0'*64
    [IO.File]::WriteAllText($recibo,($registro | ConvertTo-Json -Depth 6))
    if (Testar-ReciboInstalador $recibo $c) { throw 'Recibo com hash errado foi aceito.' }
    Write-Output 'Recibo simulado: seleção parcial de opcionais, transação e rejeição verificadas.'
} finally {
    $seguro = [IO.Path]::GetFullPath($temp)
    if ([IO.Path]::GetDirectoryName($seguro) -eq [IO.Path]::GetTempPath().TrimEnd('\') -and [IO.Path]::GetFileName($seguro) -match '^qa-termos-[0-9a-f]{32}$') {
        Remove-Item -LiteralPath $seguro -Force -Recurse
    }
}
