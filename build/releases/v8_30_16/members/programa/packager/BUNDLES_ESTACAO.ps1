# Read only the station's small installation receipts. Model files are never opened.
function Ler-JsonBundleEstacao([string]$arquivo) {
    try { $item = Get-Item -LiteralPath $arquivo -Force -ErrorAction Stop }
    catch [System.Management.Automation.ItemNotFoundException] { return $null }
    if ($item.PSIsContainer -or $item.Length -gt 1048576) { throw 'Invalid receipt file.' }
    $json = [IO.File]::ReadAllText($item.FullName, [Text.UTF8Encoding]::new($false, $true)) | ConvertFrom-Json -ErrorAction Stop
    if ($null -eq $json -or $json -isnot [pscustomobject]) { throw 'Invalid receipt.' }
    return $json
}

function VersaoBundleEstacao($valor) {
    if ($valor -isnot [string] -or $valor -cnotmatch '^[0-9]+(?:\.[0-9]+){1,3}\z') { throw 'Invalid bundle version.' }
    return $valor
}

function EstadoBundlePrincipal([string]$pasta) {
    $perfil = Ler-JsonBundleEstacao (Join-Path $pasta 'suite-profile.json')
    if ($perfil) {
        if ($perfil.schema -cne 'local-suite/profile/1' -or @('full','lung-rt') -cnotcontains $perfil.profile) { throw 'Invalid profile.' }
        if ($perfil.profile -ceq 'lung-rt') { return 'absent' }
    }
    $origem = Ler-JsonBundleEstacao (Join-Path $pasta 'bundle-origem.json')
    if ($origem) {
        if ($origem.schema -cne 'local-suite/installed-bundle/1' -or $origem.product -cne 'principal') { throw 'Invalid source.' }
        if ($origem.source -ceq 'pending' -and $null -eq $origem.version) { return 'unknown' }
        if ($origem.source -ceq 'online' -and $null -eq $origem.version) { return 'online' }
        if ($origem.source -and $origem.source -cne 'offline') { throw 'Invalid source.' }
        return (VersaoBundleEstacao $origem.version)
    }
    # entrega.txt, _requisitos.json and MANIFESTO.txt also change on online preparations.
    if ((Test-Path -LiteralPath (Join-Path $pasta 'python/python.exe') -PathType Leaf -ErrorAction Stop) -and
        (Test-Path -LiteralPath (Join-Path $pasta 'radai_watcher.py') -PathType Leaf -ErrorAction Stop)) { return 'unknown' }
    return 'absent'
}

function EstadoBundlePlugin([string]$pasta, [string]$id) {
    $nome = if ($id -ceq 'neuro-rt') { 'NEURO RT' } else { 'LUNG RT' }
    $plugin = Join-Path (Join-Path $pasta 'Plugins') $nome
    $dados = Ler-JsonBundleEstacao (Join-Path $plugin 'installation.json')
    if (-not $dados) {
        # A resource directory without the installation pointer can be a legacy or interrupted installation.
        if (Test-Path -LiteralPath (Join-Path $plugin 'resources') -PathType Container -ErrorAction Stop) { return 'unknown' }
        return 'absent'
    }
    if ($dados.schema -cne "$id/installation/1") { throw 'Invalid plugin receipt.' }
    if ($id -ceq 'neuro-rt') {
        $recursos = $dados.resources
        if (-not $recursos) {
            if ($null -ne $dados.resource_bundle_version -or $dados.resource_source -or $dados.resource_recipe_sha256) { throw 'Missing resource receipt.' }
            return 'absent'
        }
        if ($recursos.schema -cne 'neuro-rt/resolved-resources/1' -or $recursos.recipe_digest -cnotmatch '^[0-9a-f]{64}\z') { throw 'Invalid resource recipe.' }
        if ($dados.resource_recipe_sha256 -and $dados.resource_recipe_sha256 -cne $recursos.recipe_digest) { throw 'Conflicting resource receipts.' }
        $sha = $recursos.receipt_sha256
        $caminho = $recursos.receipt_relative_path
        if ($sha -or $caminho) {
            if ($sha -cnotmatch '^[0-9a-f]{64}\z' -or $caminho -cne ('resources/' + $recursos.recipe_digest + '/' + $sha + '.json')) { throw 'Invalid receipt path.' }
            $arquivo = Join-Path $plugin $caminho
            $confirmado = Ler-JsonBundleEstacao $arquivo
            if (-not $confirmado -or $confirmado.schema -cne $recursos.schema -or $confirmado.recipe_digest -cne $recursos.recipe_digest -or
                (Get-FileHash -Algorithm SHA256 -LiteralPath $arquivo -ErrorAction Stop).Hash -ine $sha) { throw 'Invalid activation receipt.' }
        }
    } else {
        if ($dados.reports_installed -isnot [bool] -and $null -ne $dados.reports_installed) { throw 'Invalid installation flag.' }
        if ($dados.reports_installed -ne $true) {
            if ($null -ne $dados.resource_bundle_version -or $dados.resource_source -or $dados.resources_path) { throw 'Conflicting resource state.' }
            return 'absent'
        }
        if ($dados.resources_path) {
            if ($dados.resources_path -cnotmatch '^resources/([0-9a-f]{64})(?:-[0-9a-f]{32})?\z') { throw 'Invalid resource path.' }
            $receita = $Matches[1]
            if ($dados.resource_recipe_sha256 -and $dados.resource_recipe_sha256 -cne $receita) { throw 'Conflicting resource receipts.' }
            if (-not (Test-Path -LiteralPath (Join-Path $plugin $dados.resources_path) -PathType Container -ErrorAction Stop)) { throw 'Missing resource directory.' }
        }
    }
    if ($dados.resource_source -and @('offline','offline_bundle','online') -cnotcontains $dados.resource_source) { throw 'Invalid resource source.' }
    if ($null -ne $dados.resource_bundle_version) { return (VersaoBundleEstacao $dados.resource_bundle_version) }
    if ($dados.resource_source -ceq 'online') { return 'online' }
    return 'unknown'
}

function Ler-BundlesDaEstacao([string]$pasta) {
    # Older receipt schemas omit optional properties. Keep variable checks while reading them.
    Set-StrictMode -Version 1.0
    $resumo = @{'principal'='absent'; 'lung-rt'='absent'; 'neuro-rt'='absent'}
    if ([string]::IsNullOrWhiteSpace($pasta)) { return $resumo }
    foreach ($id in @('principal','lung-rt','neuro-rt')) {
        try {
            if ($id -ceq 'principal') { $resumo[$id] = EstadoBundlePrincipal $pasta }
            else { $resumo[$id] = EstadoBundlePlugin $pasta $id }
        } catch { $resumo[$id] = 'unreadable' }
    }
    return $resumo
}
