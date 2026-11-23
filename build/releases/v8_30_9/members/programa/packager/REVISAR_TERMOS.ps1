[CmdletBinding()]
param([ValidateSet('full','lung-rt','plugin-neuro','plugin-lung','plugin-coronarias')][string]$Perfil = 'full')
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'TERMOS_SUITE.ps1')
$catalogo=Join-Path (Split-Path -Parent $PSScriptRoot) 'app/data/licencas_suite.json'
if ($Perfil -like 'plugin-*' -and -not (Ler-CatalogoSuite $catalogo $Perfil).condicoes.Count) {
    Write-Host 'Nenhuma condição adicional exige aceite para este pacote.'
    exit 0
}
$recibo=Solicitar-TermosSuite $catalogo $Perfil -Revisar
if (-not $recibo) { Write-Host 'Revisão cancelada.'; exit 2 }
Write-Host 'Decisões registradas para este catálogo e este perfil.'
