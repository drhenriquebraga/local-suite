[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$PythonPath,
    [Parameter(Mandatory = $true)][string]$WorkerPath,
    [Parameter(Mandatory = $true)][string]$PlanPath,
    [Parameter(Mandatory = $true)][ValidatePattern('^[0-9a-f]{64}$')][string]$PlanSha256,
    [switch]$SemPausa
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$neuroResult = 1
try {
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $env:PYTHONIOENCODING = 'utf-8'
    Write-Host 'LOCAL SUITE - NEURO RT'
    Write-Host 'Iniciando o instalador. O progresso aparece nesta janela.'
    & $PythonPath -I -B $WorkerPath --plan $PlanPath --sha256 $PlanSha256 --supervisor-pid $PID
    $neuroResult = $LASTEXITCODE
    if ($neuroResult -eq 0) {
        Write-Host 'Concluido. A Local Suite foi reaberta.'
    } else {
        Write-Host 'O preparo ou a reabertura nao foram concluidos. Leia o resultado acima.'
        Write-Host 'Os dados existentes foram preservados. Use o atalho Local Suite para continuar.'
    }
} catch {
    Write-Host 'Nao foi possivel iniciar o instalador. O programa existente foi preservado.'
}
if ($neuroResult -ne 0 -and -not $SemPausa) {
    Read-Host 'Pressione Enter para fechar esta janela'
}
exit $neuroResult
