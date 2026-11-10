[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$PythonPath,
    [Parameter(Mandatory = $true)][string]$WorkerPath,
    [Parameter(Mandatory = $true)][string]$PlanPath,
    [Parameter(Mandatory = $true)][ValidatePattern('^[0-9a-f]{64}$')][string]$PlanSha256,
    [ValidateSet('NEURO RT','LUNG RT')][string]$PluginName = 'NEURO RT',
    [switch]$SemPausa
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$neuroResult = 1
$progressLog = Join-Path (Split-Path -Parent $PlanPath) 'progress.log'
$consoleLog = Join-Path (Split-Path -Parent $PlanPath) 'console.log'
$console = $null
try {
    try {
        $console = New-Object System.IO.StreamWriter($consoleLog, $false, (New-Object System.Text.UTF8Encoding($false)))
        $console.AutoFlush = $true
    } catch {}
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $env:PYTHONIOENCODING = 'utf-8'
    Write-Host ('LOCAL SUITE - ' + $PluginName)
    Write-Host 'Iniciando o instalador. O progresso aparece nesta janela.'
    foreach ($required in @($PythonPath, $WorkerPath, $PlanPath)) {
        if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
            throw ('Arquivo necessario ausente: ' + $required)
        }
    }
    # Windows PowerShell 5.1 can surface native stderr as a PowerShell error.
    $ErrorActionPreference = 'Continue'
    try {
        & $PythonPath -I -B $WorkerPath --plan $PlanPath --sha256 $PlanSha256 --supervisor-pid $PID 2>&1 |
            ForEach-Object {
                $line = [string]$_
                Write-Host $line
                if ($null -ne $console) { try { $console.WriteLine($line) } catch {} }
            }
        $neuroResult = $LASTEXITCODE
    } finally { $ErrorActionPreference = 'Stop' }
    if ($neuroResult -eq 0) {
        Write-Host 'Concluido. A Local Suite foi reaberta.'
    } else {
        Write-Host 'O preparo ou a reabertura nao foram concluidos. Leia o resultado acima.'
        Write-Host 'Os dados existentes foram preservados. Use o atalho Local Suite para continuar.'
    }
} catch {
    Write-Host 'Nao foi possivel iniciar o instalador. O programa existente foi preservado.'
    Write-Host $_.Exception.Message
    try { Add-Content -LiteralPath $progressLog -Encoding UTF8 -Value $_.Exception.Message } catch {}
} finally {
    if ($null -ne $console) { try { $console.Dispose() } catch {} }
}
if ($neuroResult -ne 0) {
    Write-Host ('Codigo de saida: ' + $neuroResult)
    if (Test-Path -LiteralPath $progressLog -PathType Leaf) {
        Write-Host ('Progresso: ' + $progressLog)
    }
    if (Test-Path -LiteralPath $consoleLog -PathType Leaf) {
        Write-Host ('Diagnostico: ' + $consoleLog)
    }
    if (-not $SemPausa) { Read-Host 'Pressione Enter para fechar esta janela' }
}
exit $neuroResult
