[CmdletBinding()]
param([ValidateSet('full','lung-rt','plugin-neuro','plugin-lung')][string]$Perfil = 'full')
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'TERMOS_SUITE.ps1')
$catalogo=Join-Path (Split-Path -Parent $PSScriptRoot) 'app/data/licencas_suite.json'
$recibo=Solicitar-TermosSuite $catalogo $Perfil -Revisar
if (-not $recibo) { Write-Host 'Revisão cancelada.'; exit 2 }
Write-Host 'Decisões registradas para este catálogo e este perfil.'
