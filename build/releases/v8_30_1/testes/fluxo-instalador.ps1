$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$fonte = Join-Path $PSScriptRoot '../programa/packager/prepare.ps1'
$tree = [Management.Automation.Language.Parser]::ParseFile((Resolve-Path $fonte),[ref]$null,[ref]$null)
$testar = @('ContinuarComTermos','RetomarAcaoDosTermos','IniciarAtualizarApp','AtualizarApp','InstalarOuAtualizar','PerfilParaTermos','UltimoDaSaida','MaisNovaQue','ComoNumero','MesmaVersao','LimparTermosDoPacote','RetomarAtualizarApp','IniciarPacotePortatil')
foreach($nome in $testar) {
    $def = $tree.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq $nome},$false)
    if(-not $def) { throw "missing $nome" }
    Invoke-Expression $def.Extent.Text
}
function T($t) { $t }
function Sessao {}
function Registrar {}
function DescreverUnidade {}
function VersaoPublicada { @{ok=$true; respondeu=$script:rede; erro=''; versao='8.30.1'} }
function VersaoDaPasta { '8.25.1' }
function PerfilDaInstalacao { 'full' }
function ConfirmarSeRetrocede { $true }
function PerguntarSeProcessando { $true }
function HaRede { $script:rede }
function FecharJanelasDoApp { 0 }
function AcharInstalacao { $script:Instalado }
function ConferirInstalacao { $script:Instalado }
function FecharAJanela {}
function MarcarModo($m) { $script:Modo=$m }
function EsconderPreparo {}
function MostrarPreparo {}
function PintarEstado {}
function AvisarAtualizarApp { throw 'An unexpected dialog interrupted an automatic action.' }
function MostrarRetentativa { $script:TemFalha=$true }
function Falhar($e) { throw $e }
function Obter-ReciboVigente($arq,$perfil,$Omitidos) { $script:recibo }
function MostrarTermosNaAba($arq,$perfil,$Omitidos) { $script:telas++; $abas.SelectedTab='termos' }
function RodarAtualizador($p,$opts) {
    if($opts -contains '-SoDecidir') { $script:decisoes++;return $script:decisao }
    $script:copias++;return 0
}
function AtualizarDePacote($inst,$titulo) { $script:offline++;return 'selecionado' }
function VersaoDeixaPreparar { $true }
function Preparar { $script:preparos++ }
function ConcluirAtualizacao { $script:conclusoes++ }
function Inicializar([bool]$estacao=$true) {
    $script:root=Join-Path $PSScriptRoot 'estacao-ficticia/LOCAL_SUITE'
    $script:AcaoDosTermos=$null; $script:recibo='vigente'; $script:ReciboIndividual=''
    $script:CatalogoDeTermos='fixture';$script:PerfilPreparo='';$script:Ocupado=$false
    $script:TesteLocal=$false;$script:Modo='';$script:CascataVeioDe='';$script:CascataConferiuAVersao=$false
    $script:VERSAO_INSTALADOR='8.30.1';$script:PainelTermosAtual=$null
    $script:Instalado=if($estacao){ @{pasta=$script:root;versao='8.25.1';como='fixture'} }else{$null}
    $script:rede=$true;$script:copias=0;$script:decisoes=0;$script:conclusoes=0;$script:preparos=0
    $script:telas=0;$script:offline=0;$script:decisao=3;$script:TemFalha=$false
}
function Confirmar($nome,[bool]$ok){if(-not $ok){throw "FAIL $nome"};Write-Output "PASS $nome"}
$abas=@{SelectedTab='inicio'};$aba3='progresso';$script:BtRodar=@{Visible=$false}
Inicializar
[void](InstalarOuAtualizar)
Confirmar 'Outdated online bundle + 8.30 receipt -> prepare starts immediately' ($decisoes -eq 1 -and $preparos -eq 1 -and $copias -eq 0 -and $telas -eq 0 -and $Modo -eq '7')
Inicializar
$recibo='';[void](InstalarOuAtualizar)
Confirmar 'New terms wait in main form without modifying the station' ($telas -eq 1 -and $preparos -eq 0 -and $decisoes -eq 0)
$recibo='accepted'; RetomarAcaoDosTermos $recibo; RetomarAcaoDosTermos $recibo
Confirmar 'One acceptance continues the transaction exactly once' ($telas -eq 1 -and $preparos -eq 1 -and $decisoes -eq 1)
[void](InstalarOuAtualizar)
Confirmar 'Retry reuses accepted terms' ($telas -eq 1 -and $preparos -eq 2)
Inicializar
$decisao=0;[void](InstalarOuAtualizar)
Confirmar 'Compatible fingerprint -> code only' ($decisoes -eq 1 -and $copias -eq 1 -and $preparos -eq 0 -and $conclusoes -eq 1)
Inicializar
$rede=$false;[void](InstalarOuAtualizar)
Confirmar 'Offline incompatible bundle -> offline package chooser' ($offline -eq 1 -and $preparos -eq 0 -and $copias -eq 0)
Inicializar $false
[void](InstalarOuAtualizar)
Confirmar 'Fresh station -> direct install' ($preparos -eq 1 -and $Modo -eq '1' -and $decisoes -eq 0)
Inicializar $false
IniciarPacotePortatil
Confirmar 'Portable online -> package creation' ($preparos -eq 1 -and $Modo -eq '2' -and $decisoes -eq 0)
Inicializar
$decisao=9;[void](InstalarOuAtualizar)
Confirmar 'Hard failure -> retry, no installation' ($TemFalha -and $preparos -eq 0 -and $copias -eq 0)
