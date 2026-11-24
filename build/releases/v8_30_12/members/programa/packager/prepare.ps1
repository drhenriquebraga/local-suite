
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

$script:AQUI     = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $script:AQUI 'TERMOS_SUITE.ps1')
$script:CatalogoDeTermos = Join-Path (Split-Path -Parent $script:AQUI) 'app/data/licencas_suite.json'
$script:ReciboIndividual = ''
$script:TransporteLiberado = $false
function PerfilParaTermos {
    if ($script:PerfilPreparo) { return $script:PerfilPreparo }
    if ($script:Instalado -and $script:Modo -ne '2') {
        return (PerfilDaInstalacao ([string]$script:Instalado.pasta))
    }
    return 'full'
}
$script:AcaoDosTermos = $null
$script:UltimaAcao = 'local'
$script:TemFalha = $false
$script:PastaEscolhida = @{ '1' = ''; '2' = ''; '3' = '' }

function LimparTermosDoPacote($Dados) {
    if ($Dados -and $Dados.ContainsKey('termos')) {
        foreach ($nome in @('licencas_suite.json','termos_instalador.json')) {
            $p = Join-Path $Dados.termos.pasta $nome
            if (Test-Path -LiteralPath $p -PathType Leaf) { [IO.File]::Delete($p) }
        }
        try { [IO.Directory]::Delete($Dados.termos.pasta) } catch { }
    }
}

function ContinuarComTermos {
    param([string]$Acao, [hashtable]$Dados = @{}, [string]$Arquivo = $script:CatalogoDeTermos,
          [string]$Perfil = (PerfilParaTermos), [string[]]$Omitidos = @(), [string[]]$Plugins=@())
    if ($script:Ocupado) { return }
    $script:TransporteLiberado=$false
    if ($script:AcaoDosTermos) { LimparTermosDoPacote $script:AcaoDosTermos.dados }
    $script:AcaoDosTermos = @{ acao = $Acao; dados = $Dados }
    $script:TemFalha = $false
    $script:BtRodar.Visible = $false
    try {
        $catalogos=@(
            if ($Acao -ne 'pluginsPortateis') { Ler-CatalogoSuite $Arquivo $Perfil $Omitidos }
            $perfis=@{'neuro-rt'='plugin-neuro';'lung-rt'='plugin-lung';'coronarias'='plugin-coronarias'}
            foreach ($id in $Plugins) { Ler-CatalogoSuite $script:CatalogoDeTermos $perfis[$id] }
        )
        $contextos=@(ContextosDosTermos $catalogos)
        if (RecibosDosContextos $contextos) { RetomarAcaoDosTermos $contextos[0].recibo }
        else { MostrarTermosNaAba $Arquivo $Perfil -Omitidos $Omitidos -Contextos $contextos }
    } catch {
        LimparTermosDoPacote $Dados
        $script:AcaoDosTermos = $null
        Falhar $_.Exception.Message
    }
}

function RetomarAcaoDosTermos([string]$Recibo) {
    if ($script:Ocupado -or -not $script:AcaoDosTermos) { return }
    if (-not $Recibo -and $script:AcaoDosTermos.acao -ne 'pluginsPortateis') { return }
    $pendente = $script:AcaoDosTermos
    $script:AcaoDosTermos = $null
    $script:ReciboIndividual = $Recibo
    if ($script:PainelTermosAtual) {
        $estado=$script:PainelTermosAtual.Tag; $estado.concluido=$true
        $estado.btn.Enabled=$false; $estado.opcoes.Enabled=$false; $estado.lista.Enabled=$false
    }
    $dados = $pendente.dados
    $abas.SelectedTab = $aba3
    try {
        switch ($pendente.acao) {
            'atualizar' { [void](IniciarAtualizarApp $dados.inst) }
            'preparar'  { if (VersaoDeixaPreparar) { Preparar } }
            'arquivo'   { InstalarArquivoSelecionado @dados }
            'pacote'    { AtualizarPacoteSelecionado @dados }
            'pluginsPortateis' {
                $script:TransporteLiberado=$true
                try { MontarSelecaoPortatil @dados } finally { $script:TransporteLiberado=$false }
            }
        }
    } catch { Falhar $_.Exception.Message }
    finally { LimparTermosDoPacote $dados }
}

try {
    . (Join-Path $script:AQUI 'languages.ps1')
    [void](Carregar-Idiomas $script:AQUI)
} catch {
    function T { param([AllowEmptyString()][string]$Texto) return $Texto }
    function Registrar-Texto { param($Controle, [string]$Texto)
        if ($Controle) { $Controle.Text = $Texto }; return $Controle }
    function Retraduzir { param($Formulario) }
    function Novo-SeletorIdioma { param($X, $Y, $Largura = 190,
        $Formulario = $null, $AoTrocar = $null) return $null }
}
$script:VERSAO   = '1.1'
$script:Ocupado  = $false
$script:Trabalho = ''
$script:ArquivoLog = ''
$script:CaixaLog = $null

$script:LogSessao = $null
try {
    if ($env:RADAI_LOG_PREPARADOR -and [Console]::IsOutputRedirected) {
        $script:LogSessao = New-Object System.IO.StreamWriter(
            [Console]::OpenStandardOutput(), (New-Object System.Text.UTF8Encoding($false)))
        $script:LogSessao.AutoFlush = $true
    }
} catch { $script:LogSessao = $null }
function SemUsuario {
    param([string]$Texto)
    if (-not $Texto) { return $Texto }
    return ($Texto -replace '(?i)([\\/]+Users[\\/]+)[^\\/:*?"<>|\r\n]+', '$1<usuario>')
}
$script:PastasDoOperador = @()
$script:InstalacaoAnotada = ''
function EPastaSugerida {
    param([string]$Caminho)
    $c = ([string]$Caminho).Trim().TrimEnd('\', '/')
    if (-not $c) { return $false }
    if ($c -match '^[A-Za-z]:[\\/]+RADIOTERAPIA_AI$') { return $true }
    foreach ($nome in @('RAIZ_RT', 'DESTINO_PADRAO', 'PASTA_RT', 'PREPARO_SUGERIDO', 'PACOTE_SUGERIDO')) {
        $v = Get-Variable -Name $nome -Scope Script -ValueOnly -ErrorAction SilentlyContinue
        if (-not $v) { continue }
        $n = ([string]$v).TrimEnd('\', '/') -replace '/', '\'
        if ($n -and (($c -replace '/', '\') -ieq $n)) { return $true }
    }
    return $false
}
function AnotarPastaDoOperador {
    param([string]$Caminho, [string]$Rotulo)
    if (-not $Caminho -or -not $Rotulo) { return }
    $c = $Caminho.Trim().TrimEnd('\', '/')
    $partes = @($c -split '[\\/]+' | Where-Object { $_ })
    if ($partes.Count -lt 2) { return }
    if ($c -match '^[A-Za-z]:[\\/]+Users[\\/]+[^\\/]+$') { return }
    if (EPastaSugerida $c) { return }
    foreach ($p in $script:PastasDoOperador) { if ($p.caminho -ieq $c) { return } }
    $re = ($partes | ForEach-Object { [regex]::Escape($_) }) -join '[\\/]+'
    if ($c -match '^[\\/]{2}') { $re = '[\\/]{2,}' + $re }
    $script:PastasDoOperador = @(
        @(@($script:PastasDoOperador) +
          @(@{ caminho = $c; rotulo = $Rotulo;
               re = ('(?i)' + $re + '(?![\w\-]|\.[\w\-])') })) |
        Sort-Object { $_.caminho.Length } -Descending)
}
function AnotarPastaDaInstalacao {
    param([string]$Pasta)
    if (-not $Pasta) { return }
    $c = $Pasta.Trim().TrimEnd('\', '/')
    if (-not $c) { return }
    $folha = ''
    try { $folha = Split-Path -Leaf $c } catch { }
    $projeto = Get-Variable -Name PROJETO_RT -Scope Script -ValueOnly -ErrorAction SilentlyContinue
    $nossos = @('LOCAL_SUITE', 'AUTO_CONTORNO')
    if ($projeto) { $nossos += [string]$projeto }
    $alvo = $c
    if ($folha -and ($nossos -contains $folha)) {
        try { $alvo = Split-Path -Parent $c } catch { $alvo = '' }
    }
    AnotarPastaDoOperador $alvo '<pasta da instalacao>'
}
function SemPastaDoOperador {
    param([string]$Texto)
    if (-not $Texto) { return $Texto }
    $inst = Get-Variable -Name Instalado -Scope Script -ValueOnly -ErrorAction SilentlyContinue
    if ($inst) {
        $pInst = [string]$inst.pasta
        $jaAnotada = Get-Variable -Name InstalacaoAnotada -Scope Script -ValueOnly -ErrorAction SilentlyContinue
        if ($pInst -and $pInst -ne $jaAnotada) {
            try { AnotarPastaDaInstalacao $pInst } catch { }
            $script:InstalacaoAnotada = $pInst
        }
    }
    foreach ($p in $script:PastasDoOperador) {
        $Texto = [regex]::Replace($Texto, $p.re, $p.rotulo.Replace('$', '$$'))
    }
    return $Texto
}
function DescreverUnidade {
    param([string]$Caminho)
    if (-not $Caminho) { return 'unidade desconhecida' }
    if ($Caminho -match '^[\\/]{2}') { return 'caminho de rede (UNC)' }
    try {
        $q = (Split-Path -Qualifier $Caminho).ToUpper()
        $di = New-Object System.IO.DriveInfo($q)
        $tipo = switch ($di.DriveType.ToString()) {
            'Fixed'     { 'disco local' }
            'Network'   { 'unidade de rede' }
            'Removable' { 'unidade removivel' }
            'CDRom'     { 'unidade de CD/DVD' }
            default     { 'tipo desconhecido' }
        }
        return ('unidade ' + $q + ', ' + $tipo)
    } catch { return 'unidade desconhecida' }
}
function Sessao {
    param([string]$Texto)
    if (-not $script:LogSessao) { return }
    try {
        $script:LogSessao.WriteLine('[' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') +
                                    '] ' + (SemUsuario (SemPastaDoOperador $Texto)))
    } catch { }
}
Sessao ('Starting Local Suite installer: PowerShell ' + $PSVersionTable.PSVersion + ', ' +
        $(if ([System.Threading.Thread]::CurrentThread.GetApartmentState() -eq 'STA') { 'STA' }
          else { 'MTA (the file picker requires STA)' }) +
        ', directory ' + (Split-Path -Parent $MyInvocation.MyCommand.Path))
$script:ErroJaNoLog = $false
trap {
    if (-not $script:ErroJaNoLog) {
        try {
            Sessao ('Installer stopped: ' +
                    $_.Exception.GetType().FullName + ': ' + $_.Exception.Message)
            Sessao ('  at: ' + ([string]$_.InvocationInfo.PositionMessage -replace "[`r`n]+", ' | '))
        } catch { }
    }
    break
}
$script:LogY = 188
$script:PacoteFinal = ''
$script:UltimaConclusao = @('', '')
$script:BtLicencas = $null
$script:RotLicencas = $null
$script:RotEstado = $null
$script:RotOnde = $null
$script:RotInstalador = $null
$script:RotAceita = $null
$script:ResultadoModo3 = ''
$script:AtualizouSoCodigo = $null
$script:VersaoAntesDoCodigo = ''
$script:EstacaoFinal = $null
$script:ResumoPlugins = ''
$script:PlanoPlugins = $null
# GUARDA: RADAI_ATUALIZAR_APP e RADAI_ATUALIZAR_APP_DE sao o contrato com o instalador anterior que baixou este; nao renomear.
$script:SetupSemRede = $env:RADAI_SETUP_OFFLINE -eq '1'
$env:RADAI_SETUP_OFFLINE = $null
$script:PastaDaCascata = [string]$env:RADAI_ATUALIZAR_APP
$script:CascataVeioDe = [string]$env:RADAI_ATUALIZAR_APP_DE
$env:RADAI_ATUALIZAR_APP = $null
$env:RADAI_ATUALIZAR_APP_DE = $null
$script:CascataConferiuAVersao = $false

$script:RAIZ_RT = 'C:\RADIOTERAPIA_AI'
$script:DESTINO_PADRAO = Join-Path (Join-Path $env:SystemDrive 'RADIOTERAPIA_AI') 'LOCAL_SUITE'
$script:Cancelar = $false
function ProjetoDaEntrega {
    foreach ($c in @((Join-Path $script:AQUI 'entrega.txt'),
                     (Join-Path (Split-Path -Parent $script:AQUI) 'entrega.txt'))) {
        if (-not (Test-Path -LiteralPath $c)) { continue }
        try {
            foreach ($l in (Get-Content -LiteralPath $c -Encoding UTF8)) {
                if ($l -match '^\s*PROJETO\s*=\s*(.+?)\s*$') { return $Matches[1] }
            }
        } catch { }
    }
    return 'AUTO_CONTORNO'
}
$script:PROJETO_RT = ProjetoDaEntrega

function ValorDaEntrega {
    param([string]$Chave)
    foreach ($c in @((Join-Path (Split-Path -Parent $script:AQUI) 'entrega.txt'),
                     (Join-Path $script:AQUI 'entrega.txt'))) {
        if (-not (Test-Path -LiteralPath $c)) { continue }
        try {
            $re = '^\s*' + [regex]::Escape($Chave) + '\s*=\s*(.+?)\s*$'
            foreach ($l in (Get-Content -LiteralPath $c -Encoding UTF8)) {
                if ($l -match $re) { return $Matches[1] }
            }
        } catch { }
        return ''
    }
    return ''
}
$script:VERSAO_INSTALADOR = ValorDaEntrega 'VERSAO'
$script:TesteLocal = (ValorDaEntrega 'CANAL') -eq 'TESTE_LOCAL'
$script:BUNDLE_MINIMO = ValorDaEntrega 'BUNDLE_MINIMO'
$script:BundleMinimoDeOnde = 'entrega.txt'
if (-not $script:BUNDLE_MINIMO) {
    $script:BUNDLE_MINIMO = $script:VERSAO_INSTALADOR
    $script:BundleMinimoDeOnde = 'recuo: o entrega.txt nao declara BUNDLE_MINIMO, e vale a propria VERSAO'
}
Sessao ('Installer v' + $script:VERSAO_INSTALADOR + '; minimum offline bundle v' + $script:BUNDLE_MINIMO)
$script:LANCADORES = @('RADIOTERAPIA_AI_LOCAL_SUITE.cmd',
                       'ABRIR_AUTO_CONTORNO.cmd')
$script:PASTA_RT = Join-Path $script:RAIZ_RT $script:PROJETO_RT
$script:PREPARO_SUGERIDO = Join-Path $script:PASTA_RT 'preparo'
# GUARDA: o pacote para levar nao nasce dentro da pasta do programa, que e onde a instalacao direta escreve.
$script:PACOTE_SUGERIDO = Join-Path $env:USERPROFILE 'RadioterapiaAI_pacote'
$script:PastaInstalada = ''

$script:PacoteGB     = 20.0
$script:DownloadGB   = 13.0
$script:DiscoGB      = 23.0
$script:NTarefas     = '?'
$script:NModelos     = '?'
$script:TamanhoDeOnde = 'reserva: catalogo.json ainda nao lido'

function CarregarTamanhoDoPacote {
    $c = Join-Path $script:AQUI 'catalogo.json'
    if (-not (Test-Path -LiteralPath $c)) {
        $c = Join-Path (Split-Path -Parent $script:AQUI) 'packager\catalogo.json'
    }
    if (-not (Test-Path -LiteralPath $c)) {
        $script:TamanhoDeOnde = 'reserva: nao achei o catalogo.json ao lado do preparador'
        return $false
    }
    try {
        $j = [System.IO.File]::ReadAllText($c, [System.Text.Encoding]::UTF8) |
             ConvertFrom-Json
        $p = $j.pacote
        $script:PacoteGB   = [double]$p.pacote_gib
        $script:DownloadGB = [double]$p.download_gib
        $script:DiscoGB    = [double]$p.disco_gib
        $script:NTarefas   = [string][int]$p.tarefas
        $script:NModelos   = [string][int]$p.modelos
        $script:TamanhoDeOnde = ('catalogo.json (' + $c + ')')
        return $true
    } catch {
        $script:TamanhoDeOnde = ('reserva: o catalogo.json nao trouxe o bloco pacote (' +
                                 $_.Exception.Message + ')')
        return $false
    }
}
[void](CarregarTamanhoDoPacote)

function GBInteiro { param([double]$V) return ('{0:N0}' -f [math]::Round($V)) }

function GBnecessarios {
    return [int][math]::Ceiling($script:DiscoGB)
}

function GBnecessariosDireto {
    param([string]$Pasta)
    if ($Pasta -and (MarcaDeInstalacaoAntiga $Pasta)) { return 5 }
    return [int][math]::Ceiling($script:PacoteGB + 2)
}

function PastaServeParaInstalarDireto {
    param([string]$Pasta)
    $c = ([string]$Pasta).Trim().TrimEnd('\')
    if (-not $c) { return (T 'Diga a pasta do programa.') }
    $partes = @($c -split '[\\/]+' | Where-Object { $_ })
    if ($partes.Count -lt 2) { return ((T 'Escolha uma pasta dentro do disco, e nao a raiz dele:') + ' ' + $c) }
    if (-not (Test-Path -LiteralPath $c)) { return '' }
    if (-not (Test-Path -LiteralPath $c -PathType Container)) { return ((T 'Esse caminho existe e nao e uma pasta:') + ' ' + $c) }
    if ((MarcaDeInstalacaoAntiga $c) -or
        (Test-Path -LiteralPath (Join-Path (Join-Path $c '_instalacao') '_motor_comecou.txt') -PathType Leaf)) { return '' }
    $nossos = @('LICENCAS_ACEITAS.txt', 'idioma.txt', 'preparar_log.txt', '_instalacao')
    $outros = @(Get-ChildItem -LiteralPath $c -Force -ErrorAction SilentlyContinue |
                Where-Object { ($nossos -notcontains $_.Name) -and -not (SobraDoPreparoAntigo $_.FullName) } |
                ForEach-Object { $_.Name })
    if ($outros.Count -gt 0) {
        return ((T 'Esta pasta ja tem arquivos que nao sao desta instalacao. Escolha uma pasta vazia, nova, ou a pasta de uma instalacao existente.') +
                [char]10 + [char]10 + '  ' + $c + [char]10 + '  ' + (($outros | Select-Object -First 4) -join ', '))
    }
    return ''
}

$script:Cor = @{
    Fundo   = [System.Drawing.Color]::FromArgb(6, 13, 26)
    Painel  = [System.Drawing.Color]::FromArgb(12, 19, 34)
    Borda   = [System.Drawing.Color]::FromArgb(30, 41, 59)
    Texto   = [System.Drawing.Color]::FromArgb(230, 237, 247)
    Fraco   = [System.Drawing.Color]::FromArgb(143, 160, 184)
    Titulo  = [System.Drawing.Color]::FromArgb(77, 163, 255)
    Roxo    = [System.Drawing.Color]::FromArgb(124, 92, 255)
    Ok      = [System.Drawing.Color]::FromArgb(91, 197, 127)
    Alerta  = [System.Drawing.Color]::FromArgb(255, 207, 102)
    Critico = [System.Drawing.Color]::FromArgb(233, 106, 92)
    Botao   = [System.Drawing.Color]::FromArgb(24, 34, 52)
}

function Pump { [System.Windows.Forms.Application]::DoEvents() }

function Fonte {
    param([int]$Tam = 9, [string]$Estilo = 'Regular', [string]$Nome = 'Segoe UI')
    New-Object System.Drawing.Font($Nome, $Tam, [System.Drawing.FontStyle]::$Estilo)
}

function Registrar {
    param([string]$Texto, [string]$Nivel = 'info')
    $Texto = SemUsuario (SemPastaDoOperador $Texto)
    $linha = '[' + (Get-Date -Format 'HH:mm:ss') + '] ' + $Texto
    if ($script:ArquivoLog) {
        try { Add-Content -LiteralPath $script:ArquivoLog -Value $linha -Encoding UTF8 } catch { }
    }
    Sessao $Texto
    if ($script:CaixaLog) {
        $cor = switch ($Nivel) {
            'ok'     { $script:Cor.Ok }
            'alerta' { $script:Cor.Alerta }
            'erro'   { $script:Cor.Critico }
            'titulo' { $script:Cor.Titulo }
            default  { $script:Cor.Texto }
        }
        $script:CaixaLog.SelectionStart  = $script:CaixaLog.TextLength
        $script:CaixaLog.SelectionLength = 0
        $script:CaixaLog.SelectionColor  = $cor
        $script:CaixaLog.AppendText($linha + "`r`n")
        $script:CaixaLog.ScrollToCaret()
        Pump
    }
}

function MostrarRetentativa {
    $script:TemFalha = $true
    $abas.SelectedTab = $aba3
    $script:BtRodar.Visible = $true
    $script:BtRodar.Enabled = $true
    $script:BtRodar.Text = (T 'Tentar novamente')
}
function Falhar {
    param([string]$Texto)
    Registrar $Texto 'erro'
    if ($script:BtRodar -and $abas.SelectedTab -ne $aba0) { MostrarRetentativa; return }
    [System.Windows.Forms.MessageBox]::Show(
        $Texto, 'Local Suite',
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Error) | Out-Null
}

function NovoRotulo {
    param([string]$Texto, [int]$X, [int]$Y, [int]$L, [int]$A,
          [int]$Tam = 9, [string]$Estilo = 'Regular',
          [System.Drawing.Color]$Cor = $script:Cor.Texto)
    $r = New-Object System.Windows.Forms.Label
    [void](Registrar-Texto $r $Texto)
    $r.Location = New-Object System.Drawing.Point($X, $Y)
    $r.Size = New-Object System.Drawing.Size($L, $A)
    $r.Font = Fonte $Tam $Estilo
    $r.ForeColor = $Cor
    $r.BackColor = [System.Drawing.Color]::Transparent
    return $r
}

function NovoBotao {
    param([string]$Texto, [int]$X, [int]$Y, [int]$L, [int]$A,
          [System.Drawing.Color]$Cor = $script:Cor.Titulo)
    $b = New-Object System.Windows.Forms.Button
    [void](Registrar-Texto $b $Texto)
    $b.Location = New-Object System.Drawing.Point($X, $Y)
    $b.Size = New-Object System.Drawing.Size($L, $A)
    $b.FlatStyle = [System.Windows.Forms.FlatStyle]::Flat
    $b.FlatAppearance.BorderColor = $Cor
    $b.FlatAppearance.BorderSize = 1
    $b.BackColor = $script:Cor.Botao
    $b.ForeColor = $Cor
    $b.Font = Fonte 9 'Bold'
    $b.Cursor = [System.Windows.Forms.Cursors]::Hand
    return $b
}

function NovoPainel {
    param([int]$X, [int]$Y, [int]$L, [int]$A)
    $p = New-Object System.Windows.Forms.Panel
    $p.Location = New-Object System.Drawing.Point($X, $Y)
    $p.Size = New-Object System.Drawing.Size($L, $A)
    $p.BackColor = $script:Cor.Painel
    return $p
}

function NovaCaixaTexto {
    param([string]$Texto, [int]$X, [int]$Y, [int]$L, [int]$A, [int]$Tam = 10)
    $t = New-Object System.Windows.Forms.RichTextBox
    $t.Location = New-Object System.Drawing.Point($X, $Y)
    $t.Size = New-Object System.Drawing.Size($L, $A)
    $t.Anchor = 'Top,Left,Right,Bottom'
    $t.BackColor = $script:Cor.Fundo
    $t.ForeColor = $script:Cor.Texto
    $t.BorderStyle = 'FixedSingle'
    $t.ReadOnly = $true
    $t.Multiline = $true
    $t.WordWrap = $true
    $t.ScrollBars = 'Vertical'
    $t.DetectUrls = $false
    $t.Font = Fonte $Tam
    [void](Registrar-Texto $t $Texto)
    $t.Add_MouseEnter({ $this.Focus() | Out-Null })
    return $t
}

$form = New-Object System.Windows.Forms.Form
$form.Text = 'Local Suite'
$form.Size = New-Object System.Drawing.Size(1000, 740)
$form.StartPosition = 'CenterScreen'
$form.BackColor = $script:Cor.Fundo
$form.Font = Fonte 9
$form.MinimumSize = New-Object System.Drawing.Size(900, 640)
$script:IconeDaJanela = 'none (app icon not found)'
foreach ($n in @('favicon.ico', 'radioterapia_ai.ico')) {
    $ico = Join-Path (Split-Path -Parent $script:AQUI) ('app\' + $n)
    if (-not (Test-Path -LiteralPath $ico)) { continue }
    try {
        $form.Icon = New-Object System.Drawing.Icon($ico)
        $script:IconeDaJanela = $n
        break
    } catch {
        $script:IconeDaJanela = ('could not load ' + $n + ' (' + $_.Exception.Message + ')')
    }
}
Sessao ('Window icon: ' + $script:IconeDaJanela)

$cab = NovoPainel 0 0 1000 76
$cab.Dock = [System.Windows.Forms.DockStyle]::Top
$cab.Height = 76
$form.Controls.Add($cab)

$fMarca = Fonte 16 'Bold'
function PintarMarcaDoCabecalho {
    param($Painel, $Graficos)
    $t = $Painel.Tag
    $Graficos.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAlias
    $fmt = [System.Drawing.StringFormat]::GenericTypographic
    $zero = [System.Drawing.PointF]::Empty
    $w1 = $Graficos.MeasureString($t.Palavra, $t.Fonte, $zero, $fmt).Width
    $pA = New-Object System.Drawing.SolidBrush($t.CorPalavra)
    $pB = New-Object System.Drawing.SolidBrush($t.CorSufixo)
    try {
        $Graficos.DrawString($t.Palavra, $t.Fonte, $pA, [single]0, [single]2, $fmt)
        $Graficos.DrawString($t.Sufixo, $t.Fonte, $pB, [single]$w1, [single]2, $fmt)
    } finally { $pA.Dispose(); $pB.Dispose() }
}
$script:MarcaPintada = 'nunca'
$mMarca = New-Object System.Windows.Forms.Panel
$mMarca.Location = New-Object System.Drawing.Point(26, 16)
$mMarca.Size = New-Object System.Drawing.Size(420, 32)
$mMarca.BackColor = $script:Cor.Painel
$mMarca.Tag = @{ Palavra = 'Local'; Sufixo = ' Suite'
                 Fonte = $fMarca
                 CorPalavra = $script:Cor.Texto; CorSufixo = $script:Cor.Titulo }
$mMarca.Add_Paint({
    param($remetente, $ev)
    try {
        PintarMarcaDoCabecalho $remetente $ev.Graphics
        $script:MarcaPintada = 'ok'
    } catch {
        $script:MarcaPintada = ('ERRO ' + $_.Exception.Message)
    }
})
$cab.Controls.Add($mMarca)
$script:MarcaDoCabecalho = $mMarca

function _VaoEntreCores {
    param($Controle)
    $bmp = New-Object System.Drawing.Bitmap($Controle.Width, $Controle.Height)
    $fundo = $Controle.BackColor
    $trechos = @()
    $nClaro = 0; $nAzul = 0
    try {
        $Controle.DrawToBitmap($bmp, (New-Object System.Drawing.Rectangle(
            0, 0, $bmp.Width, $bmp.Height)))
        $trechoAtual = $null
        for ($px = 0; $px -lt $bmp.Width; $px++) {
            $tinta = $false; $cl = 0; $az = 0
            for ($py = 0; $py -lt $bmp.Height; $py++) {
                $c = $bmp.GetPixel($px, $py)
                $dist = [math]::Abs($c.R - $fundo.R) + [math]::Abs($c.G - $fundo.G) +
                        [math]::Abs($c.B - $fundo.B)
                if ($dist -gt 90) { $tinta = $true }
                if ($c.R -gt 150 -and $c.G -gt 150 -and $c.B -gt 150) { $cl++ }
                elseif ($c.B -gt 150 -and $c.R -lt 110 -and $c.G -gt 90) { $az++ }
            }
            $nClaro += $cl; $nAzul += $az
            if ($tinta) {
                if ($null -eq $trechoAtual) { $trechoAtual = @{ ini = $px; fim = $px; cl = 0; az = 0 } }
                $trechoAtual.fim = $px; $trechoAtual.cl += $cl; $trechoAtual.az += $az
            } elseif ($null -ne $trechoAtual) {
                $trechos += , $trechoAtual; $trechoAtual = $null
            }
        }
        if ($null -ne $trechoAtual) { $trechos += , $trechoAtual }
        $script:UltimaContagemDeCores = ('' + $nClaro + '/' + $nAzul + ' em ' +
                                         $bmp.Width + 'x' + $bmp.Height +
                                         ', ' + $trechos.Count + ' trechos')
    } finally { $bmp.Dispose() }
    for ($k = 1; $k -lt $trechos.Count; $k++) {
        $trechoK = $trechos[$k]
        if ($trechoK.az -gt $trechoK.cl) {
            $trechoAntes = $trechos[$k - 1]
            if ($trechoAntes.cl -le $trechoAntes.az) { return -1 }
            return ($trechoK.ini - $trechoAntes.fim - 1)
        }
    }
    return -1
}

function MedirMarcaDoCabecalho {
    $script:UltimaContagemDeCores = ''
    $novo = _VaoEntreCores $script:MarcaDoCabecalho
    $coresNovo = $script:UltimaContagemDeCores
    $velho = -1
    $coresVelho = ''
    $pAntigo = New-Object System.Windows.Forms.Panel
    try {
        $pAntigo.Size = New-Object System.Drawing.Size(460, 40)
        $pAntigo.BackColor = $script:Cor.Painel
        $g0 = $pAntigo.CreateGraphics()
        $lA = [int]$g0.MeasureString('Radioterapia', $fMarca).Width
        $g0.Dispose()
        $a1 = New-Object System.Windows.Forms.Label
        $a1.Text = 'Radioterapia'; $a1.Font = $fMarca
        $a1.ForeColor = $script:Cor.Texto; $a1.BackColor = [System.Drawing.Color]::Transparent
        $a1.Location = New-Object System.Drawing.Point(0, 4)
        $a1.Size = New-Object System.Drawing.Size(($lA + 6), 30)
        $b1 = New-Object System.Windows.Forms.Label
        $b1.Text = '.ai Local Suite'; $b1.Font = $fMarca
        $b1.ForeColor = $script:Cor.Titulo; $b1.BackColor = [System.Drawing.Color]::Transparent
        $b1.Location = New-Object System.Drawing.Point($lA, 4)
        $b1.Size = New-Object System.Drawing.Size(300, 30)
        $pAntigo.Controls.Add($b1); $pAntigo.Controls.Add($a1)
        $pAntigo.Location = New-Object System.Drawing.Point(26, 0)
        $script:MarcaDoCabecalho.Parent.Controls.Add($pAntigo)
        $pAntigo.BringToFront()
        [System.Windows.Forms.Application]::DoEvents()
        $velho = _VaoEntreCores $pAntigo
        $coresVelho = $script:UltimaContagemDeCores
    } catch {
        $velho = -2
        $coresVelho = ('ERRO ' + $_.Exception.Message)
    } finally {
        try { $script:MarcaDoCabecalho.Parent.Controls.Remove($pAntigo) } catch { }
        $pAntigo.Dispose()
    }
    return ('vao=' + $novo + "`tvao_antigo=" + $velho + "`tpintado=" + $script:MarcaPintada +
            "`tcores=" + $coresNovo + "`tcores_antigo=" + $coresVelho)
}
$sub = NovoRotulo 'Preparador — baixa, confere e monta o pacote de instalação' 27 48 660 20 9 'Regular' $script:Cor.Fraco
$cab.Controls.Add($sub)
$cab.Controls.Add((NovoRotulo '' 860 22 110 20 9 'Regular' $script:Cor.Fraco))

$script:SeletoresIdioma = @()
function SincronizarSeletoresIdioma {
    $atual = Idioma-Atual
    foreach ($sel in $script:SeletoresIdioma) {
        if (-not $sel) { continue }
        try {
            if (-not ($sel.Tag -is [hashtable])) { continue }
            if (-not $sel.Tag.Contains('Ordem')) { continue }
            $i = [array]::IndexOf($sel.Tag.Ordem, $atual)
            if ($i -ge 0 -and $sel.SelectedIndex -ne $i) {
                $sel.SelectedIndex = $i
            }
        } catch { }
    }
}
$script:AoTrocarIdioma = {
    try { SincronizarSeletoresIdioma } catch { }
    if (Get-Command AtualizarVisorTermos -ErrorAction SilentlyContinue) { AtualizarVisorTermos }
    if (Get-Command AplicarModo -ErrorAction SilentlyContinue) { AplicarModo }
    try { AtualizarConclusao $script:UltimaConclusao[0] $script:UltimaConclusao[1] } catch { }
    try { AtualizarRotuloDaPasta } catch { }
    try { PintarEstado } catch { }
    try { PintarVersoes } catch { }
    if ($script:Modo) { try { AtualizarSugestaoPasta } catch { } }
}
$selIdioma = Novo-SeletorIdioma 742 46 200 $form $script:AoTrocarIdioma
if ($selIdioma) {
    $selIdioma.Anchor = 'Top,Right'
    $cab.Controls.Add($selIdioma)
    $script:SeletoresIdioma += $selIdioma
}

$abas = New-Object System.Windows.Forms.TabControl
$abas.Location = New-Object System.Drawing.Point(16, 88)
$abas.Size = New-Object System.Drawing.Size(960, 552)
$abas.Anchor = 'Top,Left,Right,Bottom'
$abas.Font = Fonte 9
$form.Controls.Add($abas)

function NovaAba {
    param([string]$Titulo)
    $t = New-Object System.Windows.Forms.TabPage
    [void](Registrar-Texto $t $Titulo.Trim() -Antes '  ' -Depois '  ')
    $t.BackColor = $script:Cor.Painel
    $t.ForeColor = $script:Cor.Texto
    $abas.TabPages.Add($t)
    $t.Size = New-Object System.Drawing.Size(($abas.Width - 8), ($abas.Height - 28))
    return $t
}

function MarcaDeInstalacao {
    param([string]$Pasta)
    if (-not $Pasta) { return $false }
    try {
        if (-not (Test-Path -LiteralPath $Pasta -PathType Container)) { return $false }
        return ((Test-Path -LiteralPath (Join-Path $Pasta 'radai_watcher.py')) -and
                (Test-Path -LiteralPath (Join-Path $Pasta 'entrega.txt')))
    } catch { return $false }
}

function MarcaDeInstalacaoAntiga {
    param([string]$Pasta)
    if (MarcaDeInstalacao $Pasta) { return $true }
    try {
        return ((Test-Path -LiteralPath (Join-Path $Pasta 'radai_watcher.py')) -and
                (Test-Path -LiteralPath (Join-Path $Pasta 'python\python.exe')))
    } catch { return $false }
}

function SobraDoPreparoAntigo {
    param([string]$Pasta)
    try {
        if (-not $Pasta) { return $false }
        if ((Split-Path -Leaf $Pasta) -ne 'preparo') { return $false }
        if (-not (Test-Path -LiteralPath $Pasta -PathType Container)) { return $false }
        if ((Test-Path -LiteralPath (Join-Path $Pasta '_montagem') -PathType Container) -or
            (Test-Path -LiteralPath (Join-Path $Pasta '_instalados.json') -PathType Leaf)) { return $true }
        foreach ($s in @(Get-ChildItem -LiteralPath $Pasta -Directory -ErrorAction SilentlyContinue)) {
            if (MarcaDeInstalacao $s.FullName) { return $true }
        }
    } catch { }
    return $false
}

function VersaoDaPasta {
    param([string]$Pasta)
    try {
        $ent = Join-Path $Pasta 'entrega.txt'
        if (-not (Test-Path -LiteralPath $ent)) { return '' }
        foreach ($l in [System.IO.File]::ReadAllLines($ent)) {
            if ($l -match '^\s*VERSAO\s*=\s*(.+?)\s*$') { return $Matches[1] }
        }
    } catch { }
    return ''
}

function UnidadesLocais {
    # GUARDA: a mesma variavel do UNINSTALL.ps1; a bateria simula outro disco sem tocar nos discos de quem a roda.
    if ($env:RADAI_UNIDADES_LOCAIS) {
        return @($env:RADAI_UNIDADES_LOCAIS -split ';' | Where-Object { $_ })
    }
    $r = @()
    foreach ($d in [System.IO.DriveInfo]::GetDrives()) {
        try {
            if (-not $d.IsReady) { continue }
            if ($d.DriveType -ne [System.IO.DriveType]::Fixed) { continue }
            $r += $d.RootDirectory.FullName
        } catch { }
    }
    return $r
}

function RaizesDeBusca {

    $raizes = @()
    $topos = @()
    if ($env:RADAI_RAIZES_BUSCA) {
        foreach ($r in ($env:RADAI_RAIZES_BUSCA -split ';')) {
            if ($r.Trim()) { $topos += $r.Trim() }
        }
    } else {
        foreach ($u in @(UnidadesLocais)) {
            $topos += (Join-Path $u 'RADIOTERAPIA_AI')
        }
    }
    foreach ($topo in $topos) {
        $raizes += $topo
        try {
            if (Test-Path -LiteralPath $topo -PathType Container) {
                foreach ($sub in (Get-ChildItem -LiteralPath $topo -Directory -ErrorAction SilentlyContinue)) {
                    $raizes += $sub.FullName
                    # GUARDA: a instalacao pela montagem antiga gravou programa e registro em <raiz>\<pasta>\preparo.
                    $prep = Join-Path $sub.FullName 'preparo'
                    if (SobraDoPreparoAntigo $prep) { $raizes += $prep }
                }
            }
        } catch { }
    }
    return $raizes
}



function AcharInstalacao {
    foreach ($raiz in (RaizesDeBusca)) {
        try {
            $reg = Join-Path $raiz '_instalados.json'
            if (-not (Test-Path -LiteralPath $reg)) { continue }
            # GUARDA: registro DENTRO da pasta do programa e o duplicado antigo;
            # a regra unica le so o do pai, e a versao vem do entrega.txt.
            if (MarcaDeInstalacaoAntiga $raiz) { continue }
            $j = [System.IO.File]::ReadAllText($reg,
                 [System.Text.Encoding]::UTF8) | ConvertFrom-Json
            foreach ($p in $j.PSObject.Properties) {
                $cands = @()
                try { if ($p.Value.caminho) { $cands += [string]$p.Value.caminho } } catch { }
                $cands += (Join-Path $raiz $p.Name)
                foreach ($pasta in $cands) {
                    if (MarcaDeInstalacao $pasta) {
                        $v = VersaoDaPasta $pasta
                        if (-not $v) { try { $v = [string]$p.Value.versao } catch { } }
                        return @{ pasta = $pasta; versao = $v; projeto = $p.Name;
                                  como = 'registro' }
                    }
                }
            }
        } catch { }
    }

    foreach ($raiz in (RaizesDeBusca)) {
        try {
            if (-not (Test-Path -LiteralPath $raiz -PathType Container)) { continue }
            if (MarcaDeInstalacao $raiz) {
                return @{ pasta = $raiz; versao = (VersaoDaPasta $raiz);
                          projeto = (Split-Path $raiz -Leaf); como = 'marca' }
            }
            foreach ($sub in (Get-ChildItem -LiteralPath $raiz -Directory -ErrorAction SilentlyContinue)) {
                if (MarcaDeInstalacao $sub.FullName) {
                    return @{ pasta = $sub.FullName;
                              versao = (VersaoDaPasta $sub.FullName);
                              projeto = $sub.Name; como = 'marca' }
                }
            }
        } catch { }
    }
    foreach ($raiz in (RaizesDeBusca)) {
        try {
            if (-not (Test-Path -LiteralPath $raiz -PathType Container)) { continue }
            $cands = @($raiz) + @(Get-ChildItem -LiteralPath $raiz -Directory -ErrorAction SilentlyContinue |
                                   ForEach-Object { $_.FullName })
            foreach ($c in $cands) {
                if (MarcaDeInstalacaoAntiga $c) {
                    return @{ pasta = $c; versao = (VersaoDaPasta $c);
                              projeto = (Split-Path $c -Leaf); como = 'marca antiga' }
                }
            }
        } catch { }
    }
    return $null
}

function RecusaDaInstalacaoAntiga {
    param($Inst)
    # GUARDA: o UNINSTALL.ps1 exige radai_watcher.py E entrega.txt; a marca antiga nao basta.
    if ($Inst -and -not (MarcaDeInstalacao ([string]$Inst.pasta))) {
        return ((T 'Esta instalacao e antiga: falta o entrega.txt ao lado do radai_watcher.py. Use «Instalar / Atualizar app nesta máquina», que instala o programa inteiro por cima e mantem a sua configuracao; depois Desinstalar volta a funcionar.') +
                "`r`n`r`n" + [string]$Inst.pasta)
    }
    return ''
}

function CompletarMarcaParaRemover {
    param($Inst)
    $p = [string]$Inst.pasta
    # GUARDA: so a pasta com a marca antiga (radai_watcher.py e python\python.exe).
    if (-not $p -or -not (MarcaDeInstalacaoAntiga $p)) { return $false }
    $ent = Join-Path $p 'entrega.txt'
    if (Test-Path -LiteralPath $ent) { return $true }
    $v = [string]$Inst.versao
    if (-not $v) { $v = 'desconhecida' }
    try {
        [System.IO.File]::WriteAllText($ent,
            ('PROJETO=' + (Split-Path -Leaf $p) + "`r`nVERSAO=" + $v + "`r`n"),
            (New-Object System.Text.UTF8Encoding($false)))
        Registrar ('  entrega.txt gravado em ' + $p + ', para o desinstalador reconhecer a pasta') 'alerta'
        return $true
    } catch { return $false }
}

$script:Instalado = AcharInstalacao

$aba0 = NovaAba 'Início'


$pnEstado = NovoPainel 20 16 900 56
$pnEstado.BorderStyle = [System.Windows.Forms.BorderStyle]::FixedSingle
$aba0.Controls.Add($pnEstado)

function PintarEstado {
    if (-not $script:RotEstado -or -not $script:RotOnde) { return }
    if ($script:Instalado) {
        $script:RotEstado.Text = ((T 'Ja instalado nesta maquina') + '   -   versao ' +
            $(if ($script:Instalado.versao) { $script:Instalado.versao } else { '?' }))
        $script:RotEstado.ForeColor = $script:Cor.Ok
        $script:RotOnde.Text = [string]$script:Instalado.pasta
    } else {
        $script:RotEstado.Text = (T 'Nenhuma instalacao encontrada nesta maquina')
        $script:RotEstado.ForeColor = $script:Cor.Alerta
        $script:RotOnde.Text = ''
    }
}
$rotEstado = NovoRotulo '' 14 8 860 20 10 'Bold' $script:Cor.Alerta
$rotOnde = NovoRotulo '' 14 30 860 18 8 'Regular' $script:Cor.Fraco
$script:RotEstado = $rotEstado
$script:RotOnde = $rotOnde
PintarEstado
$pnEstado.Controls.Add($rotEstado)
$pnEstado.Controls.Add($rotOnde)

$rotInstalador = NovoRotulo '' 20 80 900 18 9 'Bold' $script:Cor.Titulo
$rotAceita = NovoRotulo '' 20 98 900 18 9 'Regular' $script:Cor.Fraco
$script:RotInstalador = $rotInstalador
$script:RotAceita = $rotAceita
$catalogoVersoes=[IO.File]::ReadAllText($script:CatalogoDeTermos,[Text.Encoding]::UTF8) | ConvertFrom-Json
$script:VersoesPlugins=@{}
foreach ($item in $catalogoVersoes.itens) {
    if ($item.id -in @('neuro-rt-plugin','lung-rt-plugin','rocards_lad')) {
        $script:VersoesPlugins[$item.id]=[string]$item.versoes[0]
    }
}
$opcoesCodigo = Join-Path $script:AQUI 'plugin-options.json'
if (Test-Path -LiteralPath $opcoesCodigo) {
    $pluginsCodigo = ([IO.File]::ReadAllText($opcoesCodigo, [Text.Encoding]::UTF8) | ConvertFrom-Json).plugins
    foreach ($id in @('neuro-rt','lung-rt')) {
        $infoCodigo = $pluginsCodigo.$id
        if ($infoCodigo -and $infoCodigo.PSObject.Properties['code_version']) {
            $script:VersoesPlugins[$id + '-plugin'] = $infoCodigo.code_version
        }
    }
}
function PintarVersoes {
    if (-not $script:RotInstalador -or -not $script:RotAceita) { return }
    $v = $(if ($script:VERSAO_INSTALADOR) { $script:VERSAO_INSTALADOR } else { '?' })
    $m = $(if ($script:BUNDLE_MINIMO) { $script:BUNDLE_MINIMO } else { '?' })
    $script:RotInstalador.Text = ((T 'Instalador v{0}') -f $v) + '   ·   Local Suite   ' + ((T 'Aceita pacote de transferencia (bundle) versao {0} ou superior') -f $m)
    $rev=$script:VersoesPlugins['rocards_lad']
    $script:RotAceita.Text = (T 'Plugins desta versão') + '   ·   LUNG RT '+$script:VersoesPlugins['lung-rt-plugin']+'   ·   NEURO RT '+$script:VersoesPlugins['neuro-rt-plugin']+'   ·   '+(T 'Coronárias (ROCardS)')+' @'+$rev.Substring(0,8)
}
PintarVersoes
$aba0.Controls.Add($rotInstalador)
$aba0.Controls.Add($rotAceita)

$script:Modo = ''
$script:PerfilPreparo = ''
$temInst = [bool]$script:Instalado
$btModo1 = NovoBotao 'Instalar / Atualizar app nesta máquina' 20 128 910 64 $script:Cor.Ok
$btModo1.Font = Fonte 13 'Bold'
$btModo1.FlatAppearance.BorderSize = 2
$btModo1.BackColor = $script:Cor.Ok
$btModo1.ForeColor = $script:Cor.Painel
$btModo3 = NovoBotao 'Máquina offline: instalar de um pacote que eu trouxe' 20 244 445 40 $script:Cor.Titulo
$btModo2 = NovoBotao 'Montar pacotes do app e dos plugins para levar' 485 244 445 40 $script:Cor.Titulo
foreach ($bMenor in @($btModo3, $btModo2)) { $bMenor.Font = Fonte 9 'Regular' }
$btModo5 = NovoBotao 'Desinstalar' 20 352 290 28 $script:Cor.Critico
$btModo5.Font = Fonte 8 'Regular'
$btModo5.ForeColor = $script:Cor.Fraco
# GUARDA: instalar/atualizar decide pela deteccao no clique; desinstalar custa a pasta e exige deteccao.
$btModo1.Enabled = $true
$btModo5.Enabled = $temInst

$script:LegendasDaPorta = @()
foreach ($par in @(
        @($btModo1, 'Confere se o programa já está nesta máquina. Se está, atualiza o que precisa e mantém a sua configuração; se não está, baixa e instala tudo.'),
        @($btModo3, 'Não baixa nada: instala o .zip preparado em outra máquina. Para estação sem internet.'),
        @($btModo2, 'Escolha os pacotes que serão preparados para a estação offline.'))) {
    $b = $par[0]
    $leg = NovoRotulo $par[1] $b.Left ($b.Bottom + 2) $b.Width 30 8 'Regular' $script:Cor.Fraco
    $aba0.Controls.Add($leg)
    $script:LegendasDaPorta += $leg
}

function ModoDireto {
    return ($script:Modo -eq '1' -or $script:Modo -eq '7')
}

function MarcarModo {
    param([string]$Qual, [switch]$CompletarSuite)
    if ($Qual -eq '7') {
        $inst = GarantirInstalacao (T 'Aponte a pasta onde o programa esta instalado')
        if (-not $inst) { return }
    }
    $script:Modo = $Qual
    $script:PlanoPlugins = $null
    $script:AtualizouSoCodigo = $null
    $script:PacoteFinal = ''
    $script:PerfilPreparo = $(if ($Qual -eq '7' -and $CompletarSuite) { 'full' } else { '' })
    if     ($Qual -eq '2') { $script:EstacaoFinal = $false }
    elseif ($Qual -eq '3') { $script:EstacaoFinal = $null }
    else                   { $script:EstacaoFinal = $true }
    $doBotao = $(if ($Qual -eq '7') { '1' } else { $Qual })
    foreach ($par in @(@($btModo1,'1'), @($btModo2,'2'), @($btModo3,'3'))) {
        $b = $par[0]
        if ($par[1] -eq $doBotao) {
            $b.BackColor = $script:Cor.Ok
            $b.ForeColor = $script:Cor.Painel
        } else {
            $b.BackColor = $script:Cor.Botao
            $b.ForeColor = $(if ($par[1] -eq '1') { $script:Cor.Ok } else { $script:Cor.Titulo })
        }
    }
    AplicarModo
    AtualizarSugestaoPasta
    $abas.SelectedTab = $aba3
}

$script:PluginsParaLevar=@()
. (Join-Path $script:AQUI 'PACOTES_PORTATEIS.ps1')

function IniciarPacoteOffline {
    param([switch]$SemRede)
    if ($script:Ocupado) { return }
    $script:UltimaAcao = $(if ($SemRede) { 'local' } else { 'arquivo' })
    MarcarModo '3'
    $titulo = ''
    if ($SemRede) {
        $titulo = (T 'Sem internet: escolha o .zip de um pacote completo que você trouxe')
        Registrar $titulo 'alerta'
    }
    InstalarDeArquivo -Titulo $titulo
}

$btModo2.Add_Click({ IniciarPacotePortatil })
$btModo3.Add_Click({ IniciarPacoteOffline })

function PedirPastaInstalada {
    param([string]$Titulo)
    $dlg = New-Object System.Windows.Forms.FolderBrowserDialog
    $dlg.Description = ($Titulo + [char]13 + [char]10 +
        (T 'Pode apontar a pasta do programa ou qualquer pasta acima dela — eu procuro.'))
    $dlg.ShowNewFolderButton = $false
    foreach ($p in @('C:\RADIOTERAPIA_AI', 'D:\RADIOTERAPIA_AI')) {
        if (Test-Path -LiteralPath $p) { $dlg.SelectedPath = $p; break }
    }
    if ($dlg.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { return $null }
    $escolhida = $dlg.SelectedPath

    $fila = @(@{ p = $escolhida; n = 0 })
    while ($fila.Count -gt 0) {
        $atual = $fila[0]; $fila = @($fila | Select-Object -Skip 1)
        if (MarcaDeInstalacao $atual.p) {
            return @{ pasta = $atual.p; versao = (VersaoDaPasta $atual.p);
                      projeto = (Split-Path $atual.p -Leaf); como = 'apontada' }
        }
        if ($atual.n -ge 3) { continue }
        try {
            foreach ($sub in (Get-ChildItem -LiteralPath $atual.p -Directory -ErrorAction SilentlyContinue)) {
                $fila += @{ p = $sub.FullName; n = $atual.n + 1 }
            }
        } catch { }
    }
    [System.Windows.Forms.MessageBox]::Show(
        ((T 'Nao achei uma instalacao em') + "`r`n`r`n  " + $escolhida +
         "`r`n`r`n" +
         (T 'Uma pasta instalada tem radai_watcher.py e entrega.txt lado a lado. Aponte a pasta do programa, ou a pasta que a contem.')),
        (T 'Atualizar'),
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Warning) | Out-Null
    return $null
}

$script:URL_REPOSITORIO = 'https://github.com/drhenriquebraga/local-suite'
$script:URL_PAGINA_VERSOES = $script:URL_REPOSITORIO + '/releases'
$script:URL_ESPELHO = 'https://drhenriquebraga.com.br/_distribuicao/radioterapia-ai/local-suite/atualizacoes'

function UrlDaConsultaDeVersao {
    # GUARDA: a mesma regra de radai_version.url_em_vigor e _api_de: RADAI_URL_VERSOES troca o endereco, e 0 desliga.
    $u = $script:URL_PAGINA_VERSOES
    $amb = [Environment]::GetEnvironmentVariable('RADAI_URL_VERSOES')
    if ($null -ne $amb) {
        $amb = $amb.Trim().Trim('"')
        if (@('0', 'off', 'desligado', 'desligada', 'nao', 'no', 'false') -contains $amb.ToLower()) { return '' }
        if ($amb) { $u = $amb }
    }
    if ($u -notmatch '^https?://') { return '' }
    if ($u -match '^https?://api\.github\.com/') { return $u }
    if ($u -match 'github\.com/([^/]+)/([^/?#]+)') {
        return ('https://api.github.com/repos/' + $Matches[1] + '/' +
                ($Matches[2] -replace '\.git$', '') + '/releases/latest')
    }
    return $u
}
$script:URL_RELEASES = UrlDaConsultaDeVersao
$script:URLS_DA_REDE = @($script:URL_RELEASES, 'https://pypi.org/simple/pip/', 'https://huggingface.co/api/models?limit=1')
$script:VersaoLa = $null

function NomeDoInstaladorLatest {
    $p = ValorDaEntrega 'PRODUTO'
    if (-not $p) { $p = ValorDaEntrega 'PROJETO' }
    if (-not $p) { return '' }
    return ($p + '_SETUP_LATEST.zip')
}

function LinkDoInstalador {
    $n = NomeDoInstaladorLatest
    if (-not $n) { return ($script:URL_REPOSITORIO + '/releases') }
    return ($script:URL_REPOSITORIO + '/releases/latest/download/' + $n)
}

function InstaladorDaRelease {
    param($Release)
    $r = @{ nome = (NomeDoInstaladorLatest); url = (LinkDoInstalador)
            tamanho = [int64]0; sha256 = '' }
    try {
        foreach ($a in @($Release.assets)) {
            if (-not $a) { continue }
            if ([string]$a.name -ne [string]$r.nome) { continue }
            try { if ($a.browser_download_url) { $r.url = [string]$a.browser_download_url } } catch { }
            try { $r.tamanho = [int64]$a.size } catch { }
            try {
                if ([string]$a.digest -match '^sha256:([0-9a-fA-F]{64})$') { $r.sha256 = $Matches[1].ToUpper() }
            } catch { }
            break
        }
    } catch { }
    return $r
}

function RespondeuHttp {
    param($Erro)
    try { return ($null -ne $Erro.Response) } catch { return $false }
}

function LigarTls12 {
    try {
        [Net.ServicePointManager]::SecurityProtocol =
            [Net.ServicePointManager]::SecurityProtocol -bor
            [Net.SecurityProtocolType]::Tls12
    } catch { }
}

function VersaoDoPacoteAqui {
    return (ValorDaEntrega 'VERSAO')
}

function ComoNumero {
    param([string]$V)
    $limpa = ($V -replace '^[vV]', '')
    $n = @()
    foreach ($p in ($limpa -split '\.')) {
        $x = 0
        if ([int]::TryParse($p, [ref]$x)) { $n += $x } else { $n += 0 }
    }
    while ($n.Count -lt 4) { $n += 0 }
    return $n
}

function MaisNovaQue {
    param([string]$A, [string]$B)
    $x = ComoNumero $A; $y = ComoNumero $B
    for ($i = 0; $i -lt 4; $i++) {
        if ($x[$i] -gt $y[$i]) { return $true }
        if ($x[$i] -lt $y[$i]) { return $false }
    }
    return $false
}

function EsperarSemTravar {
    param($Tarefa, [int]$LimiteMs = 0, [int]$PassoMs = 100)
    $relogio = [System.Diagnostics.Stopwatch]::StartNew()
    while (-not $Tarefa.IsCompleted) {
        if ($LimiteMs -gt 0 -and $relogio.ElapsedMilliseconds -gt $LimiteMs) {
            throw ((T 'tempo esgotado: sem resposta em {0} s') -f
                   [math]::Round($LimiteMs / 1000.0))
        }
        Start-Sleep -Milliseconds $PassoMs
        Pump
    }
    if ($Tarefa.IsFaulted) { throw $Tarefa.Exception.GetBaseException() }
    if ($Tarefa.IsCanceled) { throw (T 'a transferencia foi cancelada antes de terminar') }
}

function BaixarSemTravar {
    param([string]$Url, [string]$Destino, [int]$LimiteMs = 0)
    if (-not $script:ReciboIndividual -and -not $script:TransporteLiberado) { throw (T 'Os termos de uso precisam ser aceitos antes de continuar.') }
    $wc = New-Object System.Net.WebClient
    try {
        EsperarSemTravar ($wc.DownloadFileTaskAsync($Url, $Destino)) $LimiteMs
    } finally {
        try { $wc.CancelAsync() } catch { }
        $wc.Dispose()
    }
}

function VersaoDoEspelho {
    $padrao = 'https://api.github.com/repos/drhenriquebraga/local-suite/releases/latest'
    if ($script:URL_RELEASES -ne $padrao) { return $null }
    $resp = $null
    $leitor = $null
    $req = $null
    try {
        LigarTls12
        $req = [System.Net.HttpWebRequest]::Create($script:URL_ESPELHO + '/latest.json')
        $req.AllowAutoRedirect = $false
        $req.UserAgent = 'radioterapia-ai-preparador'
        $req.Accept = 'application/json'
        $req.Headers['Cache-Control'] = 'no-cache'
        $tt = $req.GetResponseAsync()
        EsperarSemTravar $tt 8000
        $resp = $tt.Result
        if ([int]$resp.StatusCode -ne 200 -or $resp.ContentLength -gt 4096) { return $null }
        $leitor = [System.IO.StreamReader]::new($resp.GetResponseStream())
        $buf = New-Object char[] 4097
        $tl = $leitor.ReadBlockAsync($buf, 0, $buf.Length)
        EsperarSemTravar $tl 8000
        if ($tl.Result -lt 1 -or $tl.Result -gt 4096) { return $null }
        $d = (-join $buf[0..($tl.Result - 1)]) | ConvertFrom-Json -ErrorAction Stop
        $tag = [string]$d.version
        $sha = [string]$d.sha256
        $tam = [int64]0
        $nome = NomeDoInstaladorLatest
        if ($d.schema -cne 'local-suite-update/1' -or -not $nome -or
            $tag -notmatch '^[0-9]{1,4}(\.[0-9]{1,4}){1,3}$' -or
            $sha -cnotmatch '^[0-9a-f]{64}$' -or
            -not [int64]::TryParse([string]$d.size, [ref]$tam) -or
            $tam -le 0 -or $tam -gt 268435456) { return $null }
        $url = $script:URL_ESPELHO + '/v' + $tag + '/' + $nome
        return @{ ok = $true; versao = $tag; url = $url; erro = ''; respondeu = $true
                  fonte = 'espelho'
                  instalador = @{ nome = $nome; url = $url; tamanho = $tam; sha256 = $sha.ToUpperInvariant() } }
    } catch {
        return $null
    } finally {
        if ($leitor) { $leitor.Dispose() }
        if ($resp) { $resp.Dispose() }
        if ($req) { $req.Abort() }
    }
}

function VersaoPublicada {
    $c = Ler-CatalogoSuite $script:CatalogoDeTermos (PerfilParaTermos)
    if (-not (Testar-ReciboInstalador (Caminho-ReciboInstalador $c) $c)) {
        return @{ok=$false; versao=''; url=''; erro='Aceite do operador pendente.'; respondeu=$false; instalador=@{nome='';url='';tamanho=0;sha256=''}}
    }
    if ($null -ne $script:VersaoLa) { return $script:VersaoLa }
    $conf = @{ ok = $false; versao = ''; url = ''; erro = ''; respondeu = $false
               instalador = @{ nome = ''; url = ''; tamanho = [int64]0; sha256 = '' } }
    if (-not $script:URL_RELEASES) {
        $conf.erro = 'a consulta de versao esta desligada (RADAI_URL_VERSOES)'
        $script:VersaoLa = $conf
        return $conf
    }
    try {
        LigarTls12
        $wcV = New-Object System.Net.WebClient
        try {
            $wcV.Headers['User-Agent'] = 'radioterapia-ai-preparador'
            $wcV.Encoding = [System.Text.Encoding]::UTF8
            $tV = $wcV.DownloadStringTaskAsync($script:URL_RELEASES)
            EsperarSemTravar $tV 8000
            $d = $tV.Result | ConvertFrom-Json
        } finally {
            try { $wcV.CancelAsync() } catch { }
            $wcV.Dispose()
        }
        $conf.respondeu = $true
        $tag = [string]$d.tag_name
        if ($tag -match '^[vV]?[0-9]{1,4}(\.[0-9]{1,4}){0,3}$') {
            $conf.ok = $true
            $conf.fonte = 'github'
            $conf.versao = ($tag -replace '^[vV]', '')
            $conf.url = LinkDoInstalador
            $conf.instalador = InstaladorDaRelease $d
        } else {
            $conf.erro = 'a resposta nao trouxe tag_name'
        }
    } catch {
        $conf.erro = $_.Exception.Message
        if (RespondeuHttp $_.Exception) { $conf.respondeu = $true }
        try {
            $st = $_.Exception.Response.StatusCode.value__
            if ($st -eq 404) {
                $conf.erro = ((T 'o endereco das versoes respondeu 404: ou ele esta errado, ou nao existe release publicada nele. Isto nao e problema de internet. O instalador mais recente fica sempre em {0}') -f (LinkDoInstalador))
            }
        } catch { }
    }
    if (-not $conf.ok) {
        $espelho = VersaoDoEspelho
        if ($espelho) {
            Registrar '  GitHub indisponivel. Consultei a copia do instalador no site do autor.'
            $conf = $espelho
        }
    }
    $script:VersaoLa = $conf
    return $conf
}

function ConferirMinhaVersao {
    $aqui = VersaoDoPacoteAqui
    if (-not $aqui) {
        return @{ estado = 'sem_versao'; url = ''
                  frase = (T 'Este instalador nao diz de que versao e.') }
    }
    $la = VersaoPublicada
    if (-not $la.ok) {
        return @{ estado = 'sem_resposta'; url = ''
                  frase = ((T 'Nao consegui conferir se ha versao mais nova ({0}). Sigo com a v{1}.') -f $la.erro, $aqui) }
    }
    if (MaisNovaQue $la.versao $aqui) {
        return @{ estado = 'velho'; url = $la.url
                  frase = ((T 'Este instalador e a v{0}, e ja existe a v{1}.') -f $aqui, $la.versao) }
    }
    return @{ estado = 'atual'; url = $la.url
              frase = ((T 'Esta e a versao mais recente (v{0}).') -f $aqui) }
}


function GarantirInstalacao {
    param([string]$Titulo)
    if ($script:Instalado) { return $script:Instalado }
    $achada = PedirPastaInstalada $Titulo
    if ($achada) {
        $script:Instalado = $achada
        PintarEstado
    }
    return $achada
}

function EsconderPreparo {
    $abas.SelectedTab = $aba3
    $script:PrepEscondido = @()
    foreach ($c in @($aba3.Controls)) {
        if ($c -eq $script:CaixaLog -or $c -eq $script:BtParar) { continue }
        if ($c.Visible) { $script:PrepEscondido += $c; $c.Visible = $false }
    }
    $script:CaixaLog.Location = New-Object System.Drawing.Point(20, 20)
    $script:CaixaLog.Height = $script:BtParar.Top - 10 - $script:CaixaLog.Top
    [System.Windows.Forms.Application]::DoEvents()
}

function MostrarPreparo {
    try {
        foreach ($c in $script:PrepEscondido) { $c.Visible = $true }
        $script:PrepEscondido = @()
        $script:CaixaLog.Location = New-Object System.Drawing.Point(20, $script:LogY)
        $script:CaixaLog.Height = $script:BtParar.Top - 10 - $script:CaixaLog.Top
    } catch { }
}

function RodarAtualizador {
    param([string]$Pasta, [string[]]$Extra)
    $ps = Join-Path $script:AQUI 'UPDATE.ps1'
    if (-not (Test-Path -LiteralPath $ps)) {
        Registrar '  nao achei o UPDATE.ps1 ao lado do preparador' 'erro'
        return -1
    }
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = 'powershell.exe'
    $psi.Arguments = ('-NoProfile -ExecutionPolicy Bypass -File "' + $ps +
                      '" -Destino "' + ([string]$Pasta).TrimEnd('\') + '" ' + ($Extra -join ' '))
    if ($Extra -notcontains '-SoDecidir' -and $Extra -notcontains '-SoEncerrar') {
        if (-not $script:ReciboIndividual) { throw (T 'Os termos de uso precisam ser aceitos antes de continuar.') }
        $psi.Arguments += ' -ReciboDoPreparo "' + $script:ReciboIndividual + '"'
    }
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true
    $pr = [System.Diagnostics.Process]::Start($psi)
    return (AcompanharProcesso $pr)
}

function PerguntarSeTentaDeNovo {
    param([string]$Pasta)
    $r = [System.Windows.Forms.MessageBox]::Show(
        (T 'Nao consegui encerrar o app aberto nesta pasta. Feche-o pela engrenagem (Fechar, Fechar tudo) ou pelo Gerenciador de Tarefas, e clique em Tentar de novo.') +
        "`r`n`r`n" + $Pasta, (T 'O app esta aberto'),
        [System.Windows.Forms.MessageBoxButtons]::RetryCancel,
        [System.Windows.Forms.MessageBoxIcon]::Warning)
    return ([string]$r -eq 'Retry')
}

function PortaDoApp {
    param([string]$Pasta)
    $p = 8777
    try {
        $cfg = Join-Path $Pasta 'radai_watcher.config'
        if (Test-Path -LiteralPath $cfg) {
            foreach ($l in [System.IO.File]::ReadAllLines($cfg)) {
                if ($l -match '^[\s﻿]*PORT\s*=\s*(\d+)') { $p = [int]$Matches[1] }
            }
        }
    } catch { }
    return $p
}

function PerguntarAoApp {
    param([int]$Porta, [string]$Rota)
    try {
        $req = [System.Net.WebRequest]::Create('http://127.0.0.1:' + $Porta + $Rota)
        # GUARDA: sem Proxy nulo o pedido ao 127.0.0.1 vai ao proxy do Windows.
        $req.Proxy = $null
        $req.Timeout = 3000
        $resp = $req.GetResponse()
        try {
            $sr = New-Object System.IO.StreamReader($resp.GetResponseStream())
            $txt = $sr.ReadToEnd()
            $sr.Close()
        } finally { $resp.Close() }
        return ($txt | ConvertFrom-Json)
    } catch { return $null }
}

function CampoDoApp {
    param($Obj, [string]$Nome)
    # GUARDA: o preparador roda em StrictMode; campo que falta na resposta do app nao pode derrubar a pergunta.
    if (-not $Obj) { return $null }
    $c = $Obj.PSObject.Properties[$Nome]
    if ($c) { return $c.Value }
    return $null
}

function EstadoDoAppAberto {
    param([string]$Pasta)
    $r = @{ aberto = $false; processando = $false; oque = '' }
    if (-not $Pasta) { return $r }
    $porta = PortaDoApp $Pasta
    $p = PerguntarAoApp $porta '/api/pulso'
    if (-not (CampoDoApp $p 'radai')) { return $r }
    $r.aberto = $true
    $s = PerguntarAoApp $porta '/api/status'
    # GUARDA: os mesmos campos que o lancador le para perguntar antes de reabrir; sem resposta, conta como processando.
    if (-not $s) { $r.processando = $true; $r.oque = 'não respondeu se está processando' }
    elseif (CampoDoApp $s 'overnight') { $r.processando = $true; $r.oque = 'o turno da noite está aberto' }
    elseif ((CampoDoApp $s 'ocupado') -or (CampoDoApp $s 'current')) { $r.processando = $true; $r.oque = 'há uma série em processamento' }
    elseif (CampoDoApp $s 'turno_agendado') { $r.processando = $true; $r.oque = 'o turno da noite está na fila' }
    return $r
}

function PerguntarSeProcessando {
    param([string]$Pasta)
    $e = EstadoDoAppAberto $Pasta
    if (-not $e.processando) { return $true }
    Registrar ('  o app aberto em ' + $Pasta + ': ' + $e.oque)
    $r = [System.Windows.Forms.MessageBox]::Show(
        ((T 'O app está aberto nesta máquina e {0}. Encerrar agora interrompe o que está rodando: a série volta para a fila, sem contar como falha.') -f (T $e.oque)) +
        "`r`n`r`n" + (T 'Encerrar o app e seguir?'),
        (T 'O app está processando'),
        [System.Windows.Forms.MessageBoxButtons]::YesNo,
        [System.Windows.Forms.MessageBoxIcon]::Warning)
    $sim = ([string]$r -eq 'Yes')
    if ($sim) { Registrar '  a pessoa confirmou encerrar o app' }
    else { Registrar '  a pessoa escolheu deixar o app aberto' 'alerta' }
    return $sim
}

function FecharJanelasDoApp {
    # GUARDA: so as janelas do perfil proprio do app (o --user-data-dir que termina em radai_janela); o navegador da pessoa nunca e tocado.
    $n = 0
    $procs = @()
    try {
        $procs = @(Get-CimInstance Win32_Process -Filter "Name='msedge.exe' OR Name='chrome.exe'" -ErrorAction Stop)
    } catch { $procs = @() }
    foreach ($p in $procs) {
        $cl = [string]$p.CommandLine
        if ($cl -match '--type=') { continue }
        if ($cl -notmatch '--user-data-dir=[^"]*\\radai_janela("|\s|$)') { continue }
        try {
            $gp = Get-Process -Id ([int]$p.ProcessId) -ErrorAction Stop
            if ($gp.MainWindowHandle -ne [IntPtr]::Zero) { [void]$gp.CloseMainWindow() }
            if (-not $gp.WaitForExit(5000)) {
                Stop-Process -Id $gp.Id -Force -ErrorAction SilentlyContinue
            }
            $n++
        } catch { }
    }
    return $n
}

function EncerrarAppNoArranque {
    if (-not $script:Instalado) { return }
    $pasta = ([string]$script:Instalado.pasta).TrimEnd('\')
    if (-not (MarcaDeInstalacaoAntiga $pasta)) { return }
    if (-not (PerguntarSeProcessando $pasta)) {
        Registrar '  o app continua aberto; o instalador pergunta de novo antes de trocar o codigo' 'alerta'
        return
    }
    [void](GarantirAppFechado $pasta -JaPerguntou)
}

function ConcluirAtualizacao {
    param($Inst, [string]$Como, [string]$De)
    $script:PastaInstalada = ([string]$Inst.pasta).TrimEnd('\')
    $script:AtualizouSoCodigo = @($Como, $De, $script:VERSAO_INSTALADOR)
    try { AtualizarConclusao $script:PastaInstalada '' } catch { }
    try { $abas.SelectedTab = $aba4 } catch { }
}

function GarantirAppFechado {
    param([string]$Pasta, [switch]$JaPerguntou)
    # GUARDA: trocar codigo ou biblioteca por baixo do app aberto corrompe a
    # instalacao; quem encerra e o atualizador, que so mexe no Python da pasta.
    if (-not $Pasta -or -not (MarcaDeInstalacaoAntiga $Pasta)) { return $true }
    if (-not $JaPerguntou -and -not (PerguntarSeProcessando $Pasta)) {
        Registrar '  cancelado: o app esta processando e continua aberto; nada foi trocado' 'alerta'
        return $false
    }
    $nJ = FecharJanelasDoApp
    if ($nJ -gt 0) { Registrar ('  a janela do app foi fechada (' + $nJ + ')') }
    while ($true) {
        Registrar ('  conferindo se o app esta aberto em ' + $Pasta)
        $rc = RodarAtualizador $Pasta @('-SoEncerrar')
        if ($rc -eq 0) { return $true }
        if (-not (PerguntarSeTentaDeNovo $Pasta)) {
            Registrar '  cancelado: o app continua aberto, e nada foi trocado' 'alerta'
            return $false
        }
    }
}

function UltimoDaSaida {
    param($Saida)
    $a = @($Saida)
    if ($a.Count -eq 0) { return $null }
    return $a[$a.Count - 1]
}

function CampoDaEntregaEm {
    param([string]$Pasta, [string]$Chave)
    try {
        $ent = Join-Path $Pasta 'entrega.txt'
        if (-not (Test-Path -LiteralPath $ent)) { return '' }
        $re = '^\s*' + [regex]::Escape($Chave) + '\s*=\s*(.+?)\s*$'
        foreach ($l in [System.IO.File]::ReadAllLines($ent)) {
            if ($l -match $re) { return $Matches[1] }
        }
    } catch { }
    return ''
}

function MesmaVersao {
    param([string]$A, [string]$B)
    if (-not $A -or -not $B) { return $false }
    return ((-not (MaisNovaQue $A $B)) -and (-not (MaisNovaQue $B $A)))
}

function HaRede {
    if (-not [Net.NetworkInformation.NetworkInterface]::GetIsNetworkAvailable()) { return $false }
    LigarTls12
    foreach ($u in @($script:URLS_DA_REDE)) {
        if (-not $u) { continue }
        $req = [System.Net.HttpWebRequest]::Create($u)
        try {
            $req.Method = 'HEAD'
            $req.UserAgent = 'radioterapia-ai-preparador'
            $tarefa = $req.GetResponseAsync()
            EsperarSemTravar $tarefa 4000
            $tarefa.Result.Dispose()
            return $true
        } catch {
            if (RespondeuHttp $_.Exception) { return $true }
        } finally {
            $req.Abort()
        }
    }
    return $false
}

function ExtrairInstaladorNovo {
    param([string]$Zip, [string]$Destino)
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    New-Item -ItemType Directory -Path $Destino -Force | Out-Null
    $base = [System.IO.Path]::GetFullPath($Destino).TrimEnd('\') + '\'
    $z = [System.IO.Compression.ZipFile]::OpenRead($Zip)
    try {
        $n = 0
        foreach ($e in $z.Entries) {
            $alvo = [System.IO.Path]::GetFullPath([System.IO.Path]::Combine($base, $e.FullName))
            # GUARDA: entrada com .. ou caminho absoluto gravaria fora da pasta da extracao.
            if (-not $alvo.StartsWith($base, [System.StringComparison]::OrdinalIgnoreCase)) {
                throw ('o arquivo baixado grava fora da pasta da extracao: ' + $e.FullName)
            }
            if (-not $e.Name) {
                New-Item -ItemType Directory -Path $alvo -Force | Out-Null
                continue
            }
            $pai = Split-Path -Parent $alvo
            if (-not (Test-Path -LiteralPath $pai)) { New-Item -ItemType Directory -Path $pai -Force | Out-Null }
            [System.IO.Compression.ZipFileExtensions]::ExtractToFile($e, $alvo, $true)
            $n++
            if (($n % 50) -eq 0) { Pump }
        }
    } finally {
        $z.Dispose()
    }
}

function AcharPreparadorEm {
    param([string]$Pasta)
    $c = Join-Path $Pasta 'packager\prepare.ps1'
    if (Test-Path -LiteralPath $c) { return $c }
    foreach ($s in @(Get-ChildItem -LiteralPath $Pasta -Directory -ErrorAction SilentlyContinue)) {
        $c = Join-Path $s.FullName 'packager\prepare.ps1'
        if (Test-Path -LiteralPath $c) { return $c }
    }
    return ''
}

function BaixarInstaladorNovo {
    param($La)
    $r = @{ ok = $false; preparador = ''; motivo = ''; conferido = '' }
    $ins = $La.instalador
    if (-not $ins -or -not $ins.url) {
        $r.motivo = 'a release nao diz de onde baixar o instalador'
        return $r
    }
    if ([string]$ins.url -notmatch '^https://' -or [string]$ins.sha256 -notmatch '^[0-9a-f]{64}$' -or
        [int64]$ins.tamanho -le 0 -or [int64]$ins.tamanho -gt 268435456) {
        $r.motivo = 'a origem nao publicou URL HTTPS, tamanho e SHA-256 validos; nada foi executado'
        return $r
    }
    $nome = 'RadioterapiaAI_instalador_v' + (([string]$La.versao) -replace '[^0-9A-Za-z.]', '_')
    $dir = Join-Path $env:TEMP $nome
    $zip = $dir + '.zip'
    try {
        foreach ($velho in @($zip, $dir)) {
            if (Test-Path -LiteralPath $velho) {
                Remove-Item -LiteralPath $velho -Recurse -Force -ErrorAction Stop
            }
        }
        Registrar ('  baixando ' + $ins.url)
        try {
            BaixarSemTravar ([string]$ins.url) $zip 900000
        } catch {
            if ($La.fonte -ne 'github') { throw }
            $espelho = VersaoDoEspelho
            if (-not $espelho -or -not (MesmaVersao $espelho.versao $La.versao) -or
                $espelho.instalador.sha256 -ne $ins.sha256 -or
                $espelho.instalador.tamanho -ne $ins.tamanho) { throw }
            Registrar '  Download do GitHub falhou; tentando a copia identica no site.'
            BaixarSemTravar ([string]$espelho.instalador.url) $zip 900000
        }
        $tam = (Get-Item -LiteralPath $zip).Length
        $conf = @()
        if ([int64]$ins.tamanho -gt 0) {
            if ($tam -ne [int64]$ins.tamanho) {
                $r.motivo = ('o arquivo baixado tem ' + $tam + ' bytes, e a release diz ' +
                             $ins.tamanho + ' bytes')
                return $r
            }
            $conf += ('tamanho de ' + $tam + ' bytes')
        }
        if ($ins.sha256) {
            $h = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToUpper()
            if ($h -ne ([string]$ins.sha256).ToUpper()) {
                $r.motivo = ('a soma SHA-256 do arquivo baixado (' + $h.Substring(0, 12) +
                             '...) nao bate com a da release (' +
                             ([string]$ins.sha256).Substring(0, 12) + '...)')
                return $r
            }
            $conf += 'soma SHA-256'
        }
        if ($conf.Count -eq 0) { $conf += 'so pelo conteudo: a release nao publica tamanho nem soma' }
        ExtrairInstaladorNovo $zip $dir
        $prep = AcharPreparadorEm $dir
        if (-not $prep) {
            $r.motivo = 'o arquivo baixado nao traz o packager\prepare.ps1'
            return $r
        }
        $raizNova = Split-Path -Parent (Split-Path -Parent $prep)
        $vNova = CampoDaEntregaEm $raizNova 'VERSAO'
        if (-not (MesmaVersao $vNova ([string]$La.versao))) {
            $r.motivo = ('o instalador baixado diz ser a v' + $vNova + ', e a release e a v' + $La.versao)
            return $r
        }
        $pNovo = CampoDaEntregaEm $raizNova 'PROJETO'
        if ($pNovo -and $script:PROJETO_RT -and ($pNovo -ne $script:PROJETO_RT)) {
            $r.motivo = ('o instalador baixado e de outro projeto (' + $pNovo + ')')
            return $r
        }
        $r.ok = $true
        $r.preparador = $prep
        $r.conferido = ($conf -join ' e ')
    } catch {
        $r.motivo = $_.Exception.Message
    } finally {
        Remove-Item -LiteralPath $zip -Force -ErrorAction SilentlyContinue
        if (-not $r.ok -and (Test-Path -LiteralPath $dir)) {
            Remove-Item -LiteralPath $dir -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
    return $r
}

# GUARDA: minimizar, e nao Hide: esconder a janela aberta por ShowDialog encerra o laco modal dela.
function EsconderAJanela { try { $form.WindowState = [System.Windows.Forms.FormWindowState]::Minimized } catch { } }
function MostrarAJanela { try { $form.WindowState = [System.Windows.Forms.FormWindowState]::Normal } catch { } }
function FecharAJanela { try { $form.Close() } catch { } }

function AvisarAtualizarApp {
    param([string]$Texto, [string]$Icone = 'Information')
    [System.Windows.Forms.MessageBox]::Show($Texto, (T 'Atualizar app'),
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::$Icone) | Out-Null
}

function ContinuarPeloInstaladorNovo {
    param([string]$Preparador, [string]$Pasta)
    $env:RADAI_ATUALIZAR_APP = $Pasta
    $env:RADAI_ATUALIZAR_APP_DE = $script:VERSAO_INSTALADOR
    $rc = -1
    try {
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = 'powershell.exe'
        $psi.Arguments = ('-NoProfile -ExecutionPolicy Bypass -STA -File "' + $Preparador + '"')
        $psi.UseShellExecute = $false
        EsconderAJanela
        try {
            $pr = [System.Diagnostics.Process]::Start($psi)
        } catch {
            MostrarAJanela
            throw
        }
        while (-not $pr.HasExited) {
            Start-Sleep -Milliseconds 200
            Pump
        }
        $pr.WaitForExit()
        $rc = $pr.ExitCode
    } finally {
        $env:RADAI_ATUALIZAR_APP = $null
        $env:RADAI_ATUALIZAR_APP_DE = $null
    }
    return $rc
}

function AtualizarApp {
    param($Inst)
    $pasta = ([string]$Inst.pasta).TrimEnd('\')
    $vInst = VersaoDaPasta $pasta
    Registrar ''
    Registrar 'ATUALIZAR APP' 'titulo'
    Registrar ('  pasta: ' + $pasta + ' (' + (DescreverUnidade $pasta) + ')')
    Registrar ('  instalado: v' + $(if ($vInst) { $vInst } else { '?' }) +
               '; este instalador: v' + $script:VERSAO_INSTALADOR)
    if (-not $script:TesteLocal) {
        Registrar ('  A cascata decide sozinha, nesta ordem: o instalador mais novo da release; ' +
               'so o codigo, sem internet, se a impressao de requisitos bate; tudo, com ' +
               'internet, se nao bate; e, sem internet, o pacote que voce trouxe. Nada do ' +
               'que voce configurou e tocado, e o app aberto nesta pasta e encerrado antes ' +
               'de qualquer troca de codigo.')
    }
    $rede = $false
    $setupLocal = $script:SetupSemRede -or ($vInst -and (MaisNovaQue $script:VERSAO_INSTALADOR $vInst))
    if ($setupLocal) {
        Registrar ('  Verificando os requisitos deste SETUP local v' + $script:VERSAO_INSTALADOR + ' antes de consultar a rede.')
    } elseif ($script:TesteLocal) {
        Registrar ('  Teste local: aplicando o codigo deste ZIP v' + $script:VERSAO_INSTALADOR + '.')
    } elseif ($script:CascataVeioDe) {
        Registrar ('  cascata 1/4: o instalador v' + $script:CascataVeioDe +
                   ' acabou de baixar este pela rede; nao consulto a release de novo')
        $rede = $true
    } else {
        $la = VersaoPublicada
        $rede = [bool]$la.respondeu
        if (-not $la.ok) {
            Registrar ('  cascata 1/4: nao consegui conferir a release mais nova (' + $la.erro +
                       '); sigo com este instalador') 'alerta'
        } elseif (MaisNovaQue $la.versao $script:VERSAO_INSTALADOR) {
            Registrar ('  cascata 1/4: a release tem o instalador v' + $la.versao +
                       ', mais novo que este; baixo e sigo por ele')
            $novo = BaixarInstaladorNovo $la
            if ($novo.ok) {
                Registrar ('  o instalador v' + $la.versao + ' foi conferido (' + $novo.conferido +
                           '); a atualizacao continua por ele') 'ok'
                $rcNovo = ContinuarPeloInstaladorNovo ([string]$novo.preparador) $pasta
                Registrar ('  o instalador v' + $la.versao + ' terminou (codigo ' + $rcNovo + ')')
                return 'novo'
            }
            Registrar ('  nao deu para seguir pelo instalador v' + $la.versao + ': ' + $novo.motivo +
                       '. Sigo com este, v' + $script:VERSAO_INSTALADOR) 'alerta'
        } else {
            Registrar ('  cascata 1/4: a release mais nova e a v' + $la.versao +
                       ', e este instalador esta em dia')
        }
    }
    if (-not (ConfirmarSeRetrocede $pasta)) {
        Registrar '  cancelado: a versao instalada e mais nova que este instalador, e nada foi trocado' 'alerta'
        return 'retrocesso'
    }
    Registrar '  cascata 2/4: comparo a impressao de requisitos da instalacao (_requisitos.json) com a deste instalador'
    $script:VersaoAntesDoCodigo = $vInst
    if ((Test-Path -LiteralPath (Join-Path $pasta '_instalacao\_motor_comecou.txt') -PathType Leaf) -and
        (-not (Test-Path -LiteralPath (Join-Path $pasta 'python\python.exe') -PathType Leaf) -or
         -not (Test-Path -LiteralPath (Join-Path $pasta '_requisitos.json') -PathType Leaf))) {
        $rc = 3
    } else {
        $rc = RodarAtualizador $pasta @('-SoDecidir','-SemPerguntar')
    }
    if ($rc -eq 0) {
        if (-not (PerguntarSeProcessando $pasta)) { return 'aberto' }
        do {
            $opcoes = @('-SemPerguntar')
            if ($setupLocal -or -not $rede) { $opcoes += '-SomenteLocal' }
            $rc = RodarAtualizador $pasta $opcoes
        } while ($rc -eq 4 -and (PerguntarSeTentaDeNovo $pasta))
    }
    Registrar ''
    if ($rc -eq 0) {
        $nJ = FecharJanelasDoApp
        if ($nJ -gt 0) { Registrar ('  a janela do app antigo foi fechada (' + $nJ + ')') }
        Registrar 'ATUALIZADO: a impressao bateu, e so o codigo foi trocado, sem internet.' 'ok'
        $script:Instalado = AcharInstalacao
        try { PintarEstado } catch { }
        return 'codigo'
    }
    if ($rc -eq 4) {
        Registrar 'A atualizacao nao aconteceu: o app continua aberto nesta pasta.' 'alerta'
        return 'aberto'
    }
    if ($rc -ne 3) {
        Registrar ('A atualizacao nao aconteceu (codigo ' + $rc + '). Veja o log acima.') 'erro'
        return 'erro'
    }
    if ($script:TesteLocal) {
        Registrar 'Esta instalacao precisa de outras dependencias. Confira o motivo indicado acima. O teste requer uma instalacao compativel.' 'erro'
        return 'erro'
    }
    if (-not $rede -and -not $script:SetupSemRede) { $rede = HaRede }
    if ($rede) {
        Registrar ('  cascata 3/4: a impressao mudou e ha internet: sigo para atualizar tudo ' +
                   '(runtime, bibliotecas e pesos) na pasta instalada') 'alerta'
        return 'tudo'
    }
    Registrar ('  cascata 4/4: a impressao mudou e nao ha internet: peco o .zip de um pacote ' +
               'completo trazido de outra maquina') 'alerta'
    return 'pacote'
}

function IniciarAtualizarApp {
    param($Inst)
    if ($script:Ocupado -or -not $script:ReciboIndividual) { return '' }
    EsconderPreparo
    $script:Ocupado = $true
    $fim = 'erro'
    try {
        $fim = [string](UltimoDaSaida (AtualizarApp $Inst))
    } catch {
        Falhar ('Erro ao atualizar: ' + $_.Exception.Message)
        $fim = 'erro'
    } finally {
        $script:Ocupado = $false
        MostrarPreparo
    }
    if ($fim -in @('erro','aberto','retrocesso')) { MostrarRetentativa }
    if ($fim -eq 'novo') {
        FecharAJanela
        return $fim
    }
    if ($fim -eq 'codigo') {
        ConcluirAtualizacao $Inst 'codigo' $script:VersaoAntesDoCodigo
        return $fim
    }
    if ($fim -eq 'tudo') {
        $script:CascataConferiuAVersao = $true
        MarcarModo '7'
        if (VersaoDeixaPreparar) { Preparar }
        return $fim
    }
    if ($fim -eq 'pacote') {
        $r = [string](UltimoDaSaida (AtualizarDePacote $Inst (T 'Sem internet: escolha o .zip de um pacote completo que você trouxe')))
        Registrar ('  pacote trazido: ' + $(if ($r) { $r } else { 'sem resposta' }))
        if ($r -eq 'selecionado') { return $r }
        if ($r -eq 'aberto') {
            Registrar 'A atualizacao nao aconteceu: o app continua aberto nesta pasta.' 'alerta'
            return 'aberto'
        }
        if ($r -eq 'falhou') { return 'erro' }
        if ($r -ne 'feito') {
            MostrarRetentativa
            Registrar ('CANCELADO: o pacote instalado e incompativel com a v' + $script:VERSAO_INSTALADOR +
                       ', esta maquina esta sem internet e nenhum pacote completo valido foi escolhido. ' +
                       'Nada foi trocado.') 'erro'
            AvisarAtualizarApp ((T 'Atualização cancelada. O pacote instalado nesta máquina (o bundle) é incompatível com a v{0} e impede o uso dela, e aqui não há internet para atualizá-lo. Traga um pacote atualizado, preparado numa máquina com internet por «Montar pacotes do app e dos plugins para levar», e clique de novo em «Instalar / Atualizar app nesta máquina». A instalação atual continua como estava.') -f $script:VERSAO_INSTALADOR) 'Warning'
            return 'cancelado'
        }
        ConcluirAtualizacao $Inst 'pacote' ([string]$Inst.versao)
        return 'pacote'
    }
    return $fim
}

function ConferirInstalacao {
    $achada = AcharInstalacao
    if (-not $achada -and $script:Instalado -and
            (MarcaDeInstalacaoAntiga ([string]$script:Instalado.pasta))) {
        $achada = $script:Instalado
    }
    $script:Instalado = $achada
    try { PintarEstado } catch { }
    $btModo5.Enabled = [bool]$achada
    return $achada
}

function PerfilDaInstalacao {
    param([string]$Pasta)
    $marca = Join-Path $Pasta 'suite-profile.json'
    if (-not (Test-Path -LiteralPath $marca -PathType Leaf)) { return 'full' }
    try {
        $perfil = [System.IO.File]::ReadAllText($marca) | ConvertFrom-Json
        if ($perfil.schema -ne 'local-suite/profile/1' -or
            @('full', 'lung-rt') -notcontains $perfil.profile) { throw 'perfil invalido' }
        return [string]$perfil.profile
    } catch {
        throw (T 'Não consegui ler o perfil da instalação. Repare suite-profile.json antes de continuar.')
    }
}

function NovaEscolhaPerfilCompacto {
    $d = New-Object System.Windows.Forms.Form
    $d.ClientSize = New-Object System.Drawing.Size(720, 330)
    $d.StartPosition = 'CenterParent'
    $d.FormBorderStyle = 'FixedDialog'
    $d.MaximizeBox = $false
    $d.MinimizeBox = $false
    $d.ShowInTaskbar = $false
    $d.AutoScaleMode = 'Font'
    $d.Font = Fonte 10
    $d.BackColor = $script:Cor.Painel
    $d.ForeColor = $script:Cor.Texto
    if ((Idioma-Atual) -eq 'ar') { $d.RightToLeft = 'Yes'; $d.RightToLeftLayout = $true }
    $d.Text = (T 'Perfil da instalação')
    $d.Controls.Add((NovoRotulo 'Esta instalação usa o perfil compacto LUNG RT.' 24 20 672 48 12 'Bold' $script:Cor.Titulo))
    $d.Controls.Add((NovoRotulo 'Completar a Suite baixa os recursos que faltam. Atualizar mantém o perfil compacto. Plugins, dados e configurações são preservados.' 24 76 672 72 10 'Regular' $script:Cor.Texto))
    $completar = NovoBotao 'Completar a Suite' 24 160 672 44 $script:Cor.Ok
    $completar.DialogResult = [System.Windows.Forms.DialogResult]::Yes
    $atualizar = NovoBotao 'Atualizar somente o perfil existente' 24 214 672 44 $script:Cor.Titulo
    $atualizar.DialogResult = [System.Windows.Forms.DialogResult]::No
    $cancelar = NovoBotao 'Cancelar' 526 278 170 32 $script:Cor.Fraco
    $cancelar.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
    $d.Controls.AddRange(@($completar, $atualizar, $cancelar))
    $d.AcceptButton = $atualizar
    $d.CancelButton = $cancelar
    return $d
}

function EscolherPerfilCompacto {
    $d = NovaEscolhaPerfilCompacto
    try {
        $escolha = $d.ShowDialog($form)
        if ($escolha -eq [System.Windows.Forms.DialogResult]::Yes) { return 'full' }
        if ($escolha -eq [System.Windows.Forms.DialogResult]::No) { return 'manter' }
        return 'cancelar'
    } finally { $d.Dispose() }
}

function InstalarOuAtualizar {
    if ($script:Ocupado) { return '' }
    $script:UltimaAcao = 'local'
    $inst = ConferirInstalacao
    if ($script:TesteLocal) {
        if (-not $inst) {
            $inst = GarantirInstalacao (T 'Aponte a pasta onde o programa esta instalado')
            if (-not $inst) { return 'cancelado' }
        }
        ContinuarComTermos 'atualizar' @{ inst = $inst }
        return 'atualizar'
    }
    if ($inst) {
        try { $perfil = PerfilDaInstalacao ([string]$inst.pasta) }
        catch { Falhar $_.Exception.Message; return 'erro' }
        if ($perfil -eq 'lung-rt') {
            $escolha = EscolherPerfilCompacto
            if ($escolha -eq 'full') {
                $script:CascataConferiuAVersao = $false
                MarcarModo '7' -CompletarSuite
                ContinuarComTermos 'preparar'
                return 'completar'
            }
            if ($escolha -ne 'manter') { return 'cancelado' }
        }
        $script:PerfilPreparo = $perfil
        Sessao ('Instalar / Atualizar: instalacao achada (' + [string]$inst.como + '); sigo pela cascata do Atualizar app')
        ContinuarComTermos 'atualizar' @{ inst = $inst }
        return 'atualizar'
    }
    $script:Ocupado = $true
    $form.UseWaitCursor = $true
    try { $temRede = HaRede } finally { $form.UseWaitCursor = $false; $script:Ocupado = $false }
    if (-not $temRede) {
        IniciarPacoteOffline -SemRede
        return 'offline'
    }
    Sessao 'Instalar / Atualizar: nenhuma instalacao achada; sigo para instalar tudo'
    MarcarModo '1'
    if ($script:OpcoesPluginsCarregadas -and -not $env:RADAI_PREPARADOR_AUTOTESTE) {
        $catalogo=Ler-CatalogoPluginsSuite (Join-Path $script:AQUI 'plugin-options.json')
        $script:PlanoPlugins=Selecionar-PluginsSuite -Catalogo $catalogo -Owner $form
    }
    $plugins=@(if ($script:PlanoPlugins) { $script:PlanoPlugins.plugins | ForEach-Object { $_.id } })
    ContinuarComTermos 'preparar' -Plugins $plugins
    return 'instalar'
}

$btModo1.Add_Click({ [void](InstalarOuAtualizar) })

function RetomarAtualizarApp {
    Sessao ('Atualizar app: continuo a partir do instalador v' + $script:CascataVeioDe)
    if (MarcaDeInstalacao $script:PastaDaCascata) {
        $script:Instalado = @{ pasta = $script:PastaDaCascata
                               versao = (VersaoDaPasta $script:PastaDaCascata)
                               projeto = (Split-Path -Leaf $script:PastaDaCascata)
                               como = 'instalador anterior' }
        try { PintarEstado } catch { }
    }
    $inst = GarantirInstalacao (T 'Aponte a pasta onde o programa esta instalado')
    if (-not $inst) { return }
    try { $script:PerfilPreparo = PerfilDaInstalacao ([string]$inst.pasta) }
    catch { Falhar $_.Exception.Message; return }
    ContinuarComTermos 'atualizar' @{ inst = $inst }
}

function ListaDePreservados {
    $preserv = @('radai_watcher.config', '_dados.txt', '_bundle.txt',
                 'calibracao', 'registro', 'radai_status.json',
                 'nomes_proprios.json', 'protocolos_proprios.json',
                 '.personalizacoes-pendentes.json', '.suite-config-pendente.json',
                 '.suite-config-anterior.json', 'local-suite-dicas-vistas.json')
    return $preserv
}

function LevarDoPreparoAntigo {
    param([string]$Pasta)
    $script:LevadosDoPreparo = @()
    $sobra = Join-Path $Pasta 'preparo'
    if (-not (SobraDoPreparoAntigo $sobra)) { return }
    $velha = @(Get-ChildItem -LiteralPath $sobra -Directory -ErrorAction SilentlyContinue |
               Where-Object { MarcaDeInstalacao $_.FullName } | Select-Object -First 1)
    if ($velha.Count -eq 0) { return }
    $de = $velha[0].FullName
    $levados = @()
    foreach ($n in (ListaDePreservados)) {
        $o = Join-Path $de $n
        $a = Join-Path $Pasta $n
        if ((Test-Path -LiteralPath $o) -and -not (Test-Path -LiteralPath $a)) {
            try {
                Copy-Item -LiteralPath $o -Destination $a -Recurse -Force
                $levados += $n
            } catch { Registrar ('  nao consegui trazer ' + $n + ' de ' + $de + ': ' + $_.Exception.Message) 'alerta' }
        }
    }
    if ($levados.Count -gt 0) {
        Registrar ('  da instalacao antiga em ' + $de + ' vieram: ' + ($levados -join ', ')) 'ok'
    }
    $script:LevadosDoPreparo = $levados
}

function JanelaDesinstalar {
    param([string]$Pasta, [string]$Ps1)

    $d = New-Object System.Windows.Forms.Form
    $d.Text = (T 'Desinstalar')
    $d.Size = New-Object System.Drawing.Size(640, 460)
    $d.StartPosition = 'CenterParent'
    $d.FormBorderStyle = 'FixedDialog'
    $d.MaximizeBox = $false
    $d.MinimizeBox = $false
    $d.BackColor = $script:Cor.Fundo

    $t = New-Object System.Windows.Forms.Label
    $t.Text = (T 'Isto remove o programa desta maquina')
    $t.Location = New-Object System.Drawing.Point(20, 16)
    $t.Size = New-Object System.Drawing.Size(590, 26)
    $t.Font = Fonte 12 'Bold'
    $t.ForeColor = $script:Cor.Critico
    $d.Controls.Add($t)

    $preserv = ListaDePreservados
    $seus = @()
    foreach ($n in $preserv) {
        if (Test-Path -LiteralPath (Join-Path $Pasta $n)) { $seus += $n }
    }
    try {
        foreach ($f in (Get-ChildItem -LiteralPath $Pasta -Filter '*.log' `
                        -File -ErrorAction SilentlyContinue)) { $seus += $f.Name }
    } catch { }

    $vis = NovaCaixaTexto '' 20 50 590 180
    $linhas = @()
    $linhas += (T 'VAI SER APAGADO')
    $linhas += ('    ' + $Pasta)
    $linhas += ('    ' + (T 'os dois atalhos: area de trabalho e menu Iniciar'))
    $linhas += ('    ' + (T 'a entrada deste programa no _instalados.json'))
    $linhas += ''
    if ($seus.Count -gt 0) {
        $linhas += (T 'O QUE VOCE CONSTRUIU, e que reinstalar NAO traz de volta:')
        foreach ($a in $seus) { $linhas += ('    ' + $a) }
    } else {
        $linhas += (T 'Nao ha dado local seu nesta pasta.')
    }
    $vis.Text = ($linhas -join "`r`n")
    $d.Controls.Add($vis)

    $cb = New-Object System.Windows.Forms.CheckBox
    $cb.Text = (T 'Guardar isso numa pasta ao lado antes de apagar')
    $cb.Location = New-Object System.Drawing.Point(20, 240)
    $cb.Size = New-Object System.Drawing.Size(590, 26)
    $cb.Checked = $true
    $cb.Enabled = ($seus.Count -gt 0)
    $cb.ForeColor = $script:Cor.Texto
    $cb.BackColor = [System.Drawing.Color]::Transparent
    $d.Controls.Add($cb)

    $rc = NovoRotulo (T 'Para confirmar, digite DESINSTALAR') 20 276 590 24
    $d.Controls.Add($rc)
    $cx = New-Object System.Windows.Forms.TextBox
    $cx.Location = New-Object System.Drawing.Point(20, 302)
    $cx.Size = New-Object System.Drawing.Size(300, 28)
    $cx.Font = Fonte 11 'Bold'
    $d.Controls.Add($cx)

    $bt = NovoBotao 'Desinstalar agora' 20 348 220 40 $script:Cor.Critico
    $bt.Enabled = $false
    $bc = NovoBotao 'Cancelar' 260 348 140 40 $script:Cor.Fraco
    $d.Controls.Add($bt); $d.Controls.Add($bc)

    $cx.Add_TextChanged({
        $v = $cx.Text.Trim().ToUpper()
        $bt.Enabled = ($v -eq 'DESINSTALAR' -or $v -eq 'UNINSTALL')
    })
    $bc.Add_Click({ $d.Tag = 'nao'; $d.Close() })
    $bt.Add_Click({ $d.Tag = 'sim'; $d.Close() })
    [void]$d.ShowDialog()
    if ($d.Tag -ne 'sim') { return $false }

    $args = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $Ps1,
              '-Alvo', $Pasta, '-SemPerguntar')
    if ($cb.Checked -and $seus.Count -gt 0) { $args += '-Guardar' }
    $saida = ''
    try {
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = 'powershell.exe'
        $psi.Arguments = ($args | ForEach-Object {
            if ($_ -match '\s') { '"' + $_ + '"' } else { $_ } }) -join ' '
        $psi.UseShellExecute = $false
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true
        $psi.CreateNoWindow = $true
        $psi.StandardOutputEncoding = [System.Text.Encoding]::UTF8
        $pr = [System.Diagnostics.Process]::Start($psi)
        $linhasD = New-Object System.Collections.Generic.List[string]
        $rc2 = AcompanharProcesso $pr -Coletar $linhasD
        $saida = ($linhasD -join "`n")
    } catch {
        $saida = $_.Exception.Message
        $rc2 = -1
    }
    $fim = if ($rc2 -eq 0) {
        (T 'Pronto. A pasta e apagada por um processo separado, em segundos.')
    } else {
        (T 'A remocao nao completou. O texto abaixo diz por que.')
    }
    [System.Windows.Forms.MessageBox]::Show(
        $fim + "`r`n`r`n" + ($saida -split "`n" | Select-Object -Last 14 |
                             ForEach-Object { $_.TrimEnd() }) -join "`r`n",
        (T 'Desinstalar'), 'OK',
        $(if ($rc2 -eq 0) { 'Information' } else { 'Warning' })) | Out-Null
    return $true
}


$btModo5.Add_Click({
    if ($script:Ocupado) { return }
    $inst = GarantirInstalacao (T 'Aponte a pasta do programa que voce quer remover')
    if (-not $inst) { return }
    if (RecusaDaInstalacaoAntiga $inst) {
        $r = [System.Windows.Forms.MessageBox]::Show(
            ((T 'Esta instalacao e antiga: falta o entrega.txt ao lado do radai_watcher.py. Para remove-la, o preparador grava o entrega.txt que falta e abre o desinstalador, que mostra o que vai apagar e pede confirmacao. Continuar?') +
             "`r`n`r`n" + [string]$inst.pasta), (T 'Desinstalar'), 'YesNo', 'Warning')
        if ([string]$r -ne 'Yes') { return }
        if (-not (CompletarMarcaParaRemover $inst)) {
            [System.Windows.Forms.MessageBox]::Show(
                ((RecusaDaInstalacaoAntiga $inst)), (T 'Desinstalar'), 'OK', 'Warning') | Out-Null
            return
        }
    }
    $ps1Pacote = Join-Path (Split-Path -Parent $script:AQUI) 'installer\UNINSTALL.ps1'
    $alvo = ''
    foreach ($cand in @(
        (Join-Path $script:Instalado.pasta 'maintenance\UNINSTALL.cmd'),
        (Join-Path $script:Instalado.pasta 'UNINSTALL.cmd'))) {
        if (Test-Path -LiteralPath $cand) { $alvo = $cand; break }
    }
    if (-not $alvo) {
        $ps1 = Join-Path (Split-Path -Parent $script:AQUI) 'installer\UNINSTALL.ps1'
        if (Test-Path -LiteralPath $ps1) {
            $r0 = [System.Windows.Forms.MessageBox]::Show(
                (T 'Esta instalacao e anterior ao desinstalador, entao vou usar o que veio no pacote. Ele mostra o que vai apagar — a pasta, os dois atalhos e o registro — e pede confirmacao digitada.') +
                "`r`n`r`n" + $script:Instalado.pasta,
                (T 'Desinstalar'), 'OKCancel', 'Warning')
            if ($r0 -ne 'OK') { return }
            [void](JanelaDesinstalar -Pasta $script:Instalado.pasta -Ps1 $ps1)
            return
        }
        [System.Windows.Forms.MessageBox]::Show(
            (T 'Nao achei a ferramenta de remocao nem na instalacao nem neste pacote. Isso nao deveria acontecer: mande o log.'),
            (T 'Desinstalar'), 'OK', 'Error') | Out-Null
        return
    }
    $ps1Inst = [System.IO.Path]::ChangeExtension($alvo, '.ps1')
    if (-not (Test-Path -LiteralPath $ps1Inst)) { $ps1Inst = $ps1Pacote }
    if (-not (Test-Path -LiteralPath $ps1Inst)) {
        [System.Windows.Forms.MessageBox]::Show(
            (T 'Nao achei a ferramenta de remocao. Mande o log.'),
            (T 'Desinstalar'), 'OK', 'Error') | Out-Null
        return
    }
    [void](JanelaDesinstalar -Pasta $script:Instalado.pasta -Ps1 $ps1Inst)
})

$script:BotoesDaPorta = @($btModo1, $btModo3, $btModo2, $btModo5)
foreach ($bPorta in $script:BotoesDaPorta) { $aba0.Controls.Add($bPorta) }

function AplicarModo {
    if (-not $script:Modo) { return }
    if ($script:BtRodar) { $script:BtRodar.Text = (T 'Tentar novamente') }
}

$aba2 = NovaAba 'Termos de uso'
$script:PainelTermosAtual = $null
function MostrarTermosNaAba([string]$Arquivo,[string]$Perfil='full',[string[]]$Omitidos=@(),[object[]]$Contextos=@()) {
    if (-not $Contextos.Count) { $Contextos=@(ContextosDosTermos @((Ler-CatalogoSuite $Arquivo $Perfil $Omitidos))) }
    if ($script:PainelTermosAtual) {
        $aba2.Controls.Remove($script:PainelTermosAtual)
        $script:PainelTermosAtual.Dispose()
    }
    $script:PainelTermosAtual = Novo-PainelTermosSuite $Contextos[0].cat $Contextos
    $script:PainelTermosAtual.Tag.apos = { param($recibo) RetomarAcaoDosTermos $recibo }
    $aba2.Controls.Add($script:PainelTermosAtual)
    $abas.SelectedTab = $aba2
}
function AtualizarVisorTermos {
    if ($script:PainelTermosAtual) { Desenhar-TermosSuite $script:PainelTermosAtual }
}


$aba3 = NovaAba 'Progresso'

$script:RotuloPasta = NovoRotulo '' 20 18 700 20 9 'Bold' $script:Cor.Texto
$aba3.Controls.Add($script:RotuloPasta)
function AtualizarRotuloDaPasta {
    if (ModoDireto) {
        $script:RotuloPasta.Text = ((T 'Pasta do programa: instala direto aqui (precisa de cerca de {0} GB livres):') -f
                                    (GBnecessariosDireto ''))
    } else {
        $script:RotuloPasta.Text = (T 'Pasta de destino')
    }
}
AtualizarRotuloDaPasta

$cxPasta = New-Object System.Windows.Forms.TextBox
$cxPasta.Location = New-Object System.Drawing.Point(20, 42)
$cxPasta.Size = New-Object System.Drawing.Size(560, 26)
$cxPasta.Anchor = 'Top,Left'
$cxPasta.BackColor = $script:Cor.Fundo
$cxPasta.ForeColor = $script:Cor.Texto
$cxPasta.BorderStyle = 'FixedSingle'
$cxPasta.Font = Fonte 9
$cxPasta.Text = $script:DESTINO_PADRAO
$aba3.Controls.Add($cxPasta)

$btPasta = NovoBotao 'Procurar pasta…' 592 40 165 30 $script:Cor.Titulo
$btPasta.Anchor = 'Top,Left'
$btPasta.Add_Click({
    $d = New-Object System.Windows.Forms.FolderBrowserDialog
    $d.Description = (T 'Procurar pasta…')
    $d.ShowNewFolderButton = $true
    if (Test-Path -LiteralPath $cxPasta.Text) { $d.SelectedPath = $cxPasta.Text }
    if ($d.ShowDialog() -eq 'OK') { $cxPasta.Text = $d.SelectedPath; $script:PastaEscolhida[$script:Modo] = $d.SelectedPath }
    $d.Dispose()
})
$aba3.Controls.Add($btPasta)


function PosicionarLinhaPasta {
    $larg = $aba3.ClientSize.Width
    if ($larg -lt 400) { return }
    $margem = 20
    $folga  = 12
    $btPasta.Left = $larg - $margem - $btPasta.Width
    $cxPasta.Width = [Math]::Max(200, $btPasta.Left - $folga - $cxPasta.Left)
}
$aba3.Add_Resize({ PosicionarLinhaPasta })
$aba3.Add_SizeChanged({ PosicionarLinhaPasta })

$rotPasta = NovoRotulo '' 20 74 900 34 8 'Regular' $script:Cor.Fraco
$aba3.Controls.Add($rotPasta)

function PastaDoProgramaSugerida {
    if ($script:Modo -eq '1' -and $script:PastaEscolhida['1']) { return $script:PastaEscolhida['1'] }
    if (($script:Modo -eq '7' -or $script:Modo -eq '1') -and $script:Instalado) {
        $p = [string]$script:Instalado.pasta
        if ($script:Modo -eq '1') {
            $pai = Split-Path -Parent $p
            if ($pai -and (SobraDoPreparoAntigo $pai)) { return (Split-Path -Parent $pai) }
        }
        return $p
    }
    return $script:DESTINO_PADRAO
}

function AtualizarSugestaoPasta {
    AtualizarRotuloDaPasta
    $fixa = ($script:Modo -eq '7')
    $cxPasta.ReadOnly = $fixa
    $btPasta.Visible = (-not $fixa)
    if (ModoDireto) {
        $cxPasta.Text = (PastaDoProgramaSugerida)
        if ($fixa) {
            $rotPasta.Text = (T 'A atualizacao acontece na pasta instalada. Baixa so o que falta; a sua configuracao e o registro de casos ficam.')
        } else {
            $rotPasta.Text = (T 'Instalacao direta: baixa e monta nesta pasta, sem pacote e sem descompactar. Se ja houver uma instalacao aqui, a sua configuracao fica.')
        }
        $rotPasta.ForeColor = $script:Cor.Ok
        return
    }
    if ($script:EstacaoFinal -eq $true) {
        $cxPasta.Text = (PastaDoProgramaSugerida)
        $rotPasta.Text = (T 'Instalacao direta: baixa e monta nesta pasta, sem pacote e sem descompactar. Se ja houver uma instalacao aqui, a sua configuracao fica.')
        $rotPasta.ForeColor = $script:Cor.Ok
    } elseif ($script:EstacaoFinal -eq $false) {
        $cxPasta.Text = $(if ($script:PastaEscolhida['2']) { $script:PastaEscolhida['2'] } else { $script:PACOTE_SUGERIDO })
        $rotPasta.Text = 'Máquina de passagem: o preparo fica no seu perfil, e o pacote sai daí para o pendrive. ' +
                         'Nada é criado em ' + $script:RAIZ_RT + ' nesta máquina.'
        $rotPasta.ForeColor = $script:Cor.Fraco
    } elseif ($script:Modo -eq '3') {
        $cxPasta.Text = $(if ($script:PastaEscolhida['3']) { $script:PastaEscolhida['3'] }
                          elseif ($script:Instalado) { [string]$script:Instalado.pasta }
                          else { $script:DESTINO_PADRAO })
        $rotPasta.Text = ''
    }
}

$btRodar = NovoBotao 'Tentar novamente' 20 116 220 36 $script:Cor.Ok
$btRodar.Visible = $false
$script:BtRodar = $btRodar

function PerguntarSobreVersaoNova {
    param($Conferencia)
    $r = [System.Windows.Forms.MessageBox]::Show(
        $Conferencia.frase + "`r`n`r`n" +
        ((T 'Preparar agora monta um pacote de ~{0} GB da versao ANTIGA, e leva de 20 min a 2 h. Baixar o instalador novo antes custa 2 MB.') -f
         (GBInteiro $script:PacoteGB)) +
        "`r`n`r`n" + (T 'Quer abrir a pagina das versoes?'),
        (T 'Ha uma versao mais nova'),
        [System.Windows.Forms.MessageBoxButtons]::YesNoCancel,
        [System.Windows.Forms.MessageBoxIcon]::Warning)
    return [string]$r
}

function VersaoDeixaPreparar {
    if ($script:TesteLocal) { return $true }
    if ($script:Modo -eq '2') { return $true }
    if ($script:Modo -eq '3') {
        Registrar 'modo 3: sem consulta de versao na internet (instala a versao do arquivo trazido)'
        return $true
    }
    if ($env:RADAI_PREPARADOR_AUTOTESTE) {
        return $true
    }
    if ($script:Modo -eq '7' -and $script:CascataConferiuAVersao) {
        Registrar 'modo 7: o Atualizar app ja conferiu a release antes de chegar aqui'
        return $true
    }
    $script:BtRodar.Enabled = $false
    try {
        $c = ConferirMinhaVersao
    } finally {
        $script:BtRodar.Enabled = $true
    }
    Registrar $c.frase $(if ($c.estado -eq 'velho') { 'alerta' } else { 'info' })
    if ($c.estado -ne 'velho') { return $true }
    $r = PerguntarSobreVersaoNova $c
    if ($r -eq 'Yes') {
        try { Start-Process $c.url } catch { }
        return $false
    }
    if ($r -eq 'Cancel') { return $false }
    return $true
}
$aba3.Controls.Add($btRodar)

$btParar = NovoBotao 'Cancelar' ($aba3.ClientSize.Width - 150) ($aba3.ClientSize.Height - 52) 130 36 $script:Cor.Critico
$btParar.Anchor = 'Bottom,Right'
$btParar.Enabled = $false
$script:BtParar = $btParar
$btParar.Add_Click({
    $script:Cancelar = $true
    $script:BtParar.Enabled = $false
    Registrar 'cancelando... (termino o arquivo atual e paro)' 'alerta'
})
$aba3.Controls.Add($btParar)
$aba3.Controls.Add((NovoRotulo 'Leva de 20 min a 2 h, conforme a internet. Não feche esta janela.' 20 160 900 20 9 'Regular' $script:Cor.Fraco))

$script:LogY = 188
$script:CaixaLog = New-Object System.Windows.Forms.RichTextBox
$script:CaixaLog.Location = New-Object System.Drawing.Point(20, $script:LogY)
$script:CaixaLog.Size = New-Object System.Drawing.Size(($aba3.ClientSize.Width - 40), ($btParar.Top - 10 - $script:LogY))
$script:CaixaLog.Anchor = 'Top,Left,Right,Bottom'
$script:CaixaLog.BackColor = $script:Cor.Fundo
$script:CaixaLog.ForeColor = $script:Cor.Texto
$script:CaixaLog.BorderStyle = 'FixedSingle'
$script:CaixaLog.ReadOnly = $true
$script:CaixaLog.ScrollBars = 'Vertical'
$script:CaixaLog.Font = Fonte 9 'Regular' 'Consolas'
$script:CaixaLog.Add_MouseEnter({ $this.Focus() | Out-Null })
$aba3.Controls.Add($script:CaixaLog)

$btRodar.Add_Click({
    if ($script:Ocupado) { return }
    if ($cxPasta.Text.Trim() -and $script:Modo -in @('1','2','3')) { $script:PastaEscolhida[$script:Modo] = $cxPasta.Text.Trim() }
    switch ($script:UltimaAcao) {
        'portatil' { IniciarPacotePortatil }
        'arquivo'  { IniciarPacoteOffline }
        default    { [void](InstalarOuAtualizar) }
    }
})

$aba4 = NovaAba 'Conclusão'

$txt4 = NovaCaixaTexto '' 20 20 910 400
$aba4.Controls.Add($txt4)

$btAbrirPasta = NovoBotao 'Abrir a pasta do pacote' 282 440 230 38 $script:Cor.Titulo
$btAbrirPasta.Anchor = 'Bottom,Left'
$btAbrirPasta.Enabled = $false
$btAbrirPasta.Add_Click({
    if ($script:PacoteFinal -and (Test-Path -LiteralPath $script:PacoteFinal)) {
        Start-Process explorer.exe ('/select,"' + $script:PacoteFinal + '"')
    } elseif ($script:Trabalho -and (Test-Path -LiteralPath $script:Trabalho)) {
        Start-Process explorer.exe ('"' + $script:Trabalho + '"')
    } else {
        [System.Windows.Forms.MessageBox]::Show(
            (T 'Ainda não há pacote nem pasta de trabalho para abrir.'),
            (T '4 · Levar para a estação'), 'OK', 'Information') | Out-Null
    }
})
$aba4.Controls.Add($btAbrirPasta)

function CaminhoDoPrograma {
    $base = $script:PastaInstalada
    if (-not $base) { return '' }
    foreach ($n in $script:LANCADORES) {
        $c = Join-Path $base $n
        if (Test-Path -LiteralPath $c) { return $c }
    }
    return ''
}

$btAbrirPrograma = NovoBotao 'Rodar Suíte Local' 20 440 250 38 $script:Cor.Ok
$btAbrirPrograma.Anchor = 'Bottom,Left'
$btAbrirPrograma.Visible = $false
$btAbrirPrograma.Add_Click({
    $exe = CaminhoDoPrograma
    if (-not $exe) {
        [System.Windows.Forms.MessageBox]::Show(
            (T 'Não achei o arquivo que abre o programa. Veja o log desta janela.'),
            (T 'Rodar Suíte Local'), 'OK', 'Warning') | Out-Null
        return
    }
    Start-Process $exe
    $form.Close()
})
$aba4.Controls.Add($btAbrirPrograma)

$btFechar = NovoBotao 'Fechar' 524 440 130 38 $script:Cor.Fraco
$btFechar.Anchor = 'Bottom,Left'
$btFechar.Add_Click({ $form.Close() })
$aba4.Controls.Add($btFechar)

function NomeDoArquivo {
    param([string]$Caminho)
    if (-not $Caminho) { return '' }
    return (Split-Path -Leaf $Caminho)
}

function ArgumentosDoPreparo {
    param([string]$Motor, [string]$Pasta)
    $argumentos = @($Motor, '--preparo', $Pasta)
    if (ModoDireto) { $argumentos = @($Motor, '--instalar', $Pasta) }
    $detectada = Get-Variable -Name Instalado -Scope Script -ValueOnly -ErrorAction SilentlyContinue
    if (-not (ModoDireto) -and $detectada -and $detectada.pasta) {
        $argumentos += @('--reutilizar-instalacao', $script:Instalado.pasta)
    }
    if ($script:Modo -eq '7' -and $script:PerfilPreparo -eq 'full') {
        $argumentos += @('--profile', 'full')
    }
    return $argumentos
}

function LinhaDeArgumentos {
    param([string[]]$Lista)
    return (($Lista | ForEach-Object {
        '"' + ([string]$_ -replace '(\\+)$', '$1$1') + '"' }) -join ' ')
}

function AtualizarConclusao {
    param([string]$Pasta, [string]$Zip)
    $script:UltimaConclusao = @($Pasta, $Zip)
    if (-not $Pasta) {
        $txt4.Text = (T 'O resultado aparecerá aqui ao terminar.')
        $btAbrirPasta.Visible = $false
        $btAbrirPrograma.Visible = $false
        $btFechar.Left = 20
        return
    }
    if ($Zip -and $script:Modo -eq '2') {
        $titulo = T 'Pacote pronto para levar'
        $local = $Zip
    } elseif ($script:Modo -eq '7' -or $script:AtualizouSoCodigo) {
        $titulo = T 'Atualização concluída'
        $local = $script:PastaInstalada
    } else {
        $titulo = T 'Instalação concluída'
        $local = $script:PastaInstalada
    }
    $linhas = @($titulo, '', ((T 'Instalador v{0}') -f $script:VERSAO_INSTALADOR), $local)
    if ($script:ArquivoLog) { $linhas += @('', (NomeDoArquivo $script:ArquivoLog)) }
    if ($script:ResultadoModo3) { $linhas += @('', $script:ResultadoModo3) }
    if ($script:ResumoPlugins) { $linhas += @('', $script:ResumoPlugins) }
    $txt4.Text = $linhas -join [Environment]::NewLine
    $exeAqui = CaminhoDoPrograma
    $instalouAqui = [bool]$exeAqui

    $temPacoteParaLevar = ((-not $instalouAqui) -and $Zip -and
                           (Test-Path -LiteralPath $Zip))

    $btAbrirPrograma.Visible = $instalouAqui
    $btAbrirPasta.Enabled = $temPacoteParaLevar
    $btAbrirPasta.Visible = $temPacoteParaLevar

    $btFechar.Left = if ($temPacoteParaLevar) { 524 }
                     elseif ($instalouAqui) { 282 }
                     else { 20 }
}

function RaizesEspelhadas {
    $achadas = @()
    $db = Join-Path $env:LOCALAPPDATA 'Google\DriveFS\root_preference_sqlite.db'
    if (-not (Test-Path -LiteralPath $db)) { return $achadas }
    $marca = [System.Guid]::NewGuid().ToString('N').Substring(0, 8)
    $tmp = Join-Path $env:TEMP ('radai_drivecfg_' + $marca + '.db')
    try {
        Copy-Item -LiteralPath $db -Destination $tmp -Force -ErrorAction Stop
        $txt = [System.IO.File]::ReadAllText($tmp, [System.Text.Encoding]::ASCII)
        $padrao = '[A-Z]:\\[A-Za-z0-9_\\\-\. ]{2,70}'
        foreach ($m in [regex]::Matches($txt, $padrao)) {
            $c = AparaAtePasta $m.Value
            if ($c -and $achadas -notcontains $c) { $achadas += $c }
        }
    } catch {
    } finally {
        Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
    }
    return $achadas
}

function AparaAtePasta {
    param([string]$Bruto)
    $c = $Bruto.TrimEnd(' ', '\')
    while ($c.Length -gt 3) {
        if (Test-Path -LiteralPath $c -PathType Container) { return $c }
        $c = $c.Substring(0, $c.Length - 1).TrimEnd(' ', '\')
    }
    return $null
}

function DestinoSincroniza {
    param([string]$Caminho)
    try { $alvo = [System.IO.Path]::GetFullPath($Caminho).TrimEnd('\') } catch { return $null }
    foreach ($r in (RaizesEspelhadas)) {
        if ($alvo -eq $r -or $alvo.StartsWith($r + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
            return $r
        }
    }
    return $null
}

function GravarAceites {
    param([string]$Pasta)
    try {
        [System.IO.File]::WriteAllText((Join-Path $Pasta 'idioma.txt'),
            (Idioma-Atual), (New-Object System.Text.UTF8Encoding($false)))
    } catch { }

    $arq = Join-Path $Pasta 'LICENCAS_ACEITAS.txt'
    $catalogo = Ler-CatalogoSuite $script:CatalogoDeTermos (PerfilParaTermos)
    if (-not (Testar-ReciboInstalador $script:ReciboIndividual $catalogo)) { throw (T 'Os termos de uso precisam ser aceitos antes de continuar.') }
    $registro = [IO.File]::ReadAllText($script:ReciboIndividual, [Text.Encoding]::UTF8) | ConvertFrom-Json
    $l = [Collections.Generic.List[string]]::new()
    $l.Add('Local Suite | Ensino e pesquisa')
    $l.Add('Catálogo ' + $registro.catalogo_sha256)
    if ($registro.PSObject.Properties['omitidos']) { $l.Add('Componentes opcionais omitidos: ' + (@($registro.omitidos) -join ', ')) }
    foreach ($item in $catalogo.doc.itens) {
        if (@($registro.itens.id) -contains $item.id) {
            $l.Add('[ACEITA] ' + $item.titulo)
            $l.Add('           identificador: ' + $item.id)
            $l.Add('           código: ' + $item.licenca_codigo)
            $l.Add('           pesos: ' + $item.licenca_pesos)
        }
    }
    # GUARDA: o aceite anterior e evidencia; nos modos que gravam na pasta do
    # programa ele seria sobrescrito. Fica ao lado, com a versao e a hora.
    if ((Test-Path -LiteralPath $arq) -and (MarcaDeInstalacao $Pasta)) {
        try {
            $vant = ''
            try { $vant = VersaoDaPasta $Pasta } catch { }
            if (-not $vant) { $vant = 'anterior' }
            $quando = (Get-Item -LiteralPath $arq).LastWriteTime.ToString('yyyyMMdd-HHmmss')
            $velho = Join-Path $Pasta ('LICENCAS_ACEITAS_v' + $vant + '_' + $quando + '.txt')
            if (-not (Test-Path -LiteralPath $velho)) {
                Move-Item -LiteralPath $arq -Destination $velho
            }
        } catch { }
    }
    [System.IO.File]::WriteAllLines($arq, $l, (New-Object System.Text.UTF8Encoding($false)))
    return $arq
}

function AcharOuBaixarPython {
    param([string]$Pasta,[switch]$Exato310)
    foreach ($nome in @('python', 'py')) {
        try {
            $c = Get-Command $nome -ErrorAction Stop
            $v = & $c.Source -c "import sys;print('%d.%d'%sys.version_info[:2])" 2>$null
            if ($v -and [version]$v -ge [version]'3.9' -and (-not $Exato310 -or $v -eq '3.10')) {
                Registrar ('  achei Python ' + $v + ' no sistema')
                return $c.Source
            }
        } catch { }
    }
    Registrar '  nao achei Python no sistema - baixando o portatil'
    $zip = Join-Path $Pasta 'python-embed.zip'
    $dest = Join-Path $Pasta 'python-preparo'
    $url = 'https://www.python.org/ftp/python/3.10.11/python-3.10.11-embed-amd64.zip'
    try {
        Registrar ('  baixando ' + $url)
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
        BaixarSemTravar $url $zip
    } catch {
        Falhar ("Nao consegui baixar o Python:`n" + $_.Exception.Message + "`n`n" +
                (T 'Esta maquina precisa de internet para PREPARAR o pacote.') + "`n" +
                (T 'Se nao ha rede aqui (ou o proxy pede senha), volte ao passo 0 e escolha "Máquina offline: instalar de um pacote que eu trouxe" - esse caminho nao baixa nada.'))
        return $null
    }
    $tam = (Get-Item -LiteralPath $zip).Length
    if ($tam -lt 5MB) {
        Falhar ('O download do Python veio com ' + $tam + ' bytes, o que nao e um ' +
                'runtime. Provavelmente o proxy devolveu uma pagina de erro.')
        return $null
    }

    $somaEsperada = '608619f8619075629c9c69f361352a0da6ed7e62f83a0e19c63e0ea32eb7629d'
    $soma = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLower()
    if ($soma -ne $somaEsperada) {
        Remove-Item -LiteralPath $zip -Force -ErrorAction SilentlyContinue
        Falhar ('A soma do Python nao confere.' + "`n" +
                '  esperada: ' + $somaEsperada + "`n" +
                '  recebida: ' + $soma + "`n`n" +
                'O arquivo foi apagado. Isso costuma ser proxy ou espelho ' +
                'devolvendo outra coisa -- nao continue por cima.')
        return $null
    }

    Expand-Archive -LiteralPath $zip -DestinationPath $dest -Force
    $exe = Join-Path $dest 'python.exe'
    if (-not (Test-Path -LiteralPath $exe)) { Falhar 'O zip do Python nao trouxe python.exe.'; return $null }
    Get-ChildItem -LiteralPath $dest -Filter '*._pth' | ForEach-Object {
        $c = Get-Content -LiteralPath $_.FullName
        $c = $c -replace '^#\s*import site', 'import site'
        if ($c -notcontains 'import site') { $c += 'import site' }
        Set-Content -LiteralPath $_.FullName -Value $c -Encoding ASCII
    }
    return $exe
}

function AcompanharProcesso {
    param([System.Diagnostics.Process]$Proc, [int]$PassoMs = 100,
          $Coletar = $null, [scriptblock]$FormatarLinha = $null, [switch]$Cancelavel)
    $saida = $Proc.StandardOutput
    $erro  = $Proc.StandardError
    $tSaida = $saida.ReadLineAsync()
    $tErro  = $erro.ReadLineAsync()
    $fimSaida = $false
    $fimErro  = $false
    while (-not ($fimSaida -and $fimErro)) {
        if ($Cancelavel -and $script:Cancelar -and -not $Proc.HasExited) {
            & taskkill.exe /PID $Proc.Id /T /F 2>$null | Out-Null
            throw (T 'Cancelado pelo operador.')
        }
        $andou = $false
        if (-not $fimSaida -and $tSaida.IsCompleted) {
            $l = $tSaida.Result
            if ($null -eq $l) { $fimSaida = $true }
            else {
                $legivel = $l
                if ($FormatarLinha) { $legivel = & $FormatarLinha $l }
                Registrar ('  ' + $legivel)
                if ($null -ne $Coletar) { [void]$Coletar.Add($l) }
                $tSaida = $saida.ReadLineAsync()
                $andou = $true
            }
        }
        if (-not $fimErro -and $tErro.IsCompleted) {
            $l = $tErro.Result
            if ($null -eq $l) { $fimErro = $true }
            else {
                $legivel = $l
                if ($FormatarLinha) { $legivel = & $FormatarLinha $l }
                Registrar ('  ' + $legivel) 'erro'
                if ($null -ne $Coletar) { [void]$Coletar.Add($l) }
                $tErro = $erro.ReadLineAsync()
                $andou = $true
            }
        }
        if (-not $andou) { Start-Sleep -Milliseconds $PassoMs }
        Pump
    }
    $Proc.WaitForExit()
    return $Proc.ExitCode
}

# Load at script scope: WinForms callbacks created with GetNewClosure cannot
# resolve functions dot-sourced only inside a still-running local function.
$script:OpcoesPluginsCarregadas = $false
try {
    . (Join-Path $script:AQUI 'PLUGIN_OPTIONS.ps1')
    $script:OpcoesPluginsCarregadas = $true
} catch { Sessao ('Optional plugins unavailable: ' + $_.Exception.Message) }

function OferecerPluginsOpcionais {
    # Automatic updates and installer diagnostics never open optional dialogs.
    if (-not $script:PastaInstalada -or $script:PastaDaCascata -or
        $script:Modo -eq '7' -or $env:RADAI_PREPARADOR_AUTOTESTE) { return }
    $abrirHabilitado = $btAbrirPrograma.Enabled
    $btAbrirPrograma.Enabled = $false
    try {
        if (-not $script:OpcoesPluginsCarregadas) {
            throw (T 'O preparo dos plugins não está disponível nesta instalação. A suíte pode ser aberta normalmente.')
        }
        $plano = $script:PlanoPlugins
        if (-not $plano) {
            $script:ResumoPlugins = (T 'Plugins opcionais não selecionados. A suíte está pronta para abrir.')
            Registrar $script:ResumoPlugins
            return
        }
        if (-not (GarantirAppFechado $script:PastaInstalada)) {
            $script:ResumoPlugins = (T 'Feche a suíte antes de instalar os plugins. A instalação principal foi concluída.')
            Registrar $script:ResumoPlugins 'alerta'
            return
        }
        Registrar ''
        Registrar (T 'Preparando os plugins selecionados; acompanhe o progresso nesta janela.') 'titulo'
        $rcPlugins = Instalar-PluginsSuite -SuiteRoot $script:PastaInstalada -Plano $plano
        if ($rcPlugins -ne 0) {
            $script:ResumoPlugins = (T 'O preparo dos plugins não terminou. A suíte continua disponível; use Configurações para tentar novamente ou apontar um pacote offline.')
            Registrar $script:ResumoPlugins 'alerta'
        } else {
            $script:ResumoPlugins = (T 'Plugins selecionados preparados. A suíte pode ser aberta.')
            Registrar $script:ResumoPlugins 'ok'
        }
    } catch {
        $script:ResumoPlugins = ((T 'Os plugins opcionais não foram preparados. A instalação principal permanece disponível:') +
            ' ' + $_.Exception.Message)
        Registrar $script:ResumoPlugins 'alerta'
    } finally { $btAbrirPrograma.Enabled = $abrirHabilitado }
}

function Preparar {
    if ($script:Ocupado -or -not $script:ReciboIndividual) { return }
    $script:Ocupado = $true
    $script:Cancelar = $false
    if ($script:BtParar) { $script:BtParar.Enabled = $true }
    $btRodar.Enabled = $false
    try {
        $trab = $cxPasta.Text.Trim()
        $direto = ModoDireto
        if ($direto) { $trab = $trab.TrimEnd('\') }
        if (-not $trab) { Falhar 'Diga a pasta de trabalho.'; return }
        AnotarPastaDoOperador $trab '<pasta de trabalho>'

        $espelho = DestinoSincroniza $trab
        if ($espelho) {
            Falhar ('Esta pasta SINCRONIZA COM A NUVEM.' + [char]10 + [char]10 +
                    '   destino: ' + $trab + [char]10 +
                    '   espelho: ' + $espelho + [char]10 + [char]10 +
                    ('Sao cerca de ' + (GBInteiro $script:DownloadGB) + ' GB baixados e ' +
                     (GBInteiro $script:PacoteGB) + ' GB de pacote. Caindo aqui,') + [char]10 +
                    'tudo sobe para a nuvem com historico de versao.' + [char]10 + [char]10 +
                    'Peso de modelo e gratuito e se baixa de novo: nao se versiona.' + [char]10 +
                    'Escolha uma pasta FORA do espelho.')
            return
        }
        $pyDir = $trab
        if ($direto) {
            $motivo = PastaServeParaInstalarDireto $trab
            if ($motivo) { Falhar $motivo; return }
            if (-not (ConfirmarSeRetrocede $trab)) { return }
            if (-not (GarantirAppFechado $trab)) { return }
            $pyDir = Join-Path $trab '_instalacao'
        }

        if (-not (Test-Path -LiteralPath $trab)) {
            New-Item -ItemType Directory -Path $trab -Force | Out-Null
        }
        if (-not (Test-Path -LiteralPath $pyDir)) {
            New-Item -ItemType Directory -Path $pyDir -Force | Out-Null
        }
        $script:Trabalho = $trab
        $script:PastaInstalada = ''
        $script:ArquivoLog = Join-Path $trab 'preparar_log.txt'

        Registrar '=== Local Suite ===' 'titulo'
        Registrar ('pasta de trabalho: ' + (SemPastaDoOperador $trab) + ' (' +
                   (DescreverUnidade $trab) + ')')
        Registrar ('maquina: ' + $env:COMPUTERNAME)
        Registrar ('estacao de uso: ' + $(if ($script:EstacaoFinal) { 'SIM' } else { 'nao (maquina de passagem)' }))
        if ($direto) {
            Registrar ('modo: ' + $(if ($script:Modo -eq '7') { 'atualizar tudo, na pasta instalada' }
                                  else { 'instalacao DIRETA na pasta final (sem pacote e sem descompactar)' }))
        }

        $unidade = (Get-Item -LiteralPath $trab).PSDrive.Name
        $livre = (Get-PSDrive $unidade).Free
        Registrar ('espaco livre em ' + $unidade + ': ' + [math]::Round($livre / 1GB, 1) + ' GB')
        $precisoGB = 0
        if ($direto) { $precisoGB = GBnecessariosDireto $trab }
        $metade = GBInteiro $script:PacoteGB
        if ($direto) {
            Registrar ('espaco necessario: ' + $precisoGB + ' GB')
        } else {
            Registrar 'O preparador verificará o espaço no destino e nos temporários após conferir os componentes locais.'
        }
        Registrar ('  tamanho do pacote de: ' + $script:TamanhoDeOnde)
        if ($direto -and $livre -lt ($precisoGB * 1GB)) {
            Falhar ('Espaco insuficiente em ' + $unidade + ': ha ' +
                    [math]::Round($livre / 1GB, 1) + ' GB e sao necessarios cerca de ' +
                    $precisoGB + ' GB.')
            return
        }

        Registrar ''
        Registrar '1/4  Gravando o aceite das licencas' 'titulo'
        $arqAceite = GravarAceites $trab
        Registrar ('  gravado: ' + (Split-Path -Leaf $arqAceite)) 'ok'

        Registrar ''
        Registrar '2/4  Procurando o motor de preparo' 'titulo'
        $motor = Join-Path $script:AQUI 'configurar_ambiente.py'
        if (-not (Test-Path -LiteralPath $motor)) {
            $motor = Join-Path (Split-Path -Parent $script:AQUI) 'build\configurar_ambiente.py'
        }
        if (-not (Test-Path -LiteralPath $motor)) {
            Falhar ("Nao achei o configurar_ambiente.py.`n`n" +
                    'Ele deve estar em programa\build\. Se voce copiou so o .ps1, ' +
                    'copie a pasta inteira.')
            return
        }
        Registrar ('  motor: ' + $motor) 'ok'

        Registrar ''
        Registrar '3/4  Python para rodar o preparo' 'titulo'
        $py = $null
        if (-not $direto -and $script:Instalado -and $script:Instalado.pasta) {
            $candidato = Join-Path $script:Instalado.pasta 'python/python.exe'
            if (Test-Path -LiteralPath $candidato -PathType Leaf) { $py = $candidato }
        }
        if (-not $py) { $py = AcharOuBaixarPython $pyDir }
        if (-not $py) { return }
        Registrar ('  python: ' + $py) 'ok'

        Registrar ''
        if ($direto) {
            Registrar '4/4  Baixando e conferindo, direto na pasta final (sem pacote)' 'titulo'
        } else {
            Registrar '4/4  Baixando, conferindo e empacotando' 'titulo'
        }
        Registrar '  Os pesos e o Python baixados sao conferidos: SHA-256 onde ha'
        Registrar '  soma conhecida, tamanho e CRC nos demais. Peso do'
        Registrar '  TotalSegmentator ou Python que nao confere PARA o preparo e'
        Registrar '  diz qual foi; modelo de comparacao que nao confere fica fora'
        Registrar '  do pacote, e o log diz qual. O MANIFESTO.txt do pacote'
        Registrar '  registra o que foi conferido em cada zip do TotalSegmentator.'

        if ($direto -and $script:PerfilPreparo -ne 'full' -and
                (PerfilDaInstalacao $trab) -eq 'lung-rt') {
            Registrar '  Perfil compacto LUNG RT preservado: preparo apenas dos recursos desse perfil.'
        } else {
            Registrar ('  Pacote COMPLETO: runtime, ' + $script:NTarefas +
                       ' tarefas do TotalSegmentator e ' + $script:NModelos +
                       ' modelos de comparacao (~' + (GBInteiro $script:PacoteGB) + ' GB).')
        }
        Registrar ''

        $argumentos = @(ArgumentosDoPreparo $motor $trab)
        $pi = New-Object System.Diagnostics.ProcessStartInfo
        $pi.FileName = $py
        $pi.Arguments = LinhaDeArgumentos $argumentos
        $pi.UseShellExecute = $false
        $pi.RedirectStandardOutput = $true
        $pi.RedirectStandardError = $true
        $pi.CreateNoWindow = $true
        $pi.WorkingDirectory = Split-Path -Parent $motor
        $pi.EnvironmentVariables['PYTHONIOENCODING'] = 'utf-8:replace'
        $pi.EnvironmentVariables['PYTHONUNBUFFERED'] = '1'
        $pi.StandardOutputEncoding = New-Object System.Text.UTF8Encoding($false)
        $pi.StandardErrorEncoding  = New-Object System.Text.UTF8Encoding($false)

        $proc = New-Object System.Diagnostics.Process
        $proc.StartInfo = $pi
        $proc.Start() | Out-Null
        $rcMotor = AcompanharProcesso $proc

        if ($rcMotor -ne 0) {
            $classe = ''
            if ($rcMotor -eq 2) {
                $classe = (T 'A conexao caiu durante o download, e nao ha defeito no pacote. O que ja foi baixado fica: mande preparar de novo quando a rede voltar.') + [char]10 + [char]10
            } elseif ($rcMotor -eq 3) {
                $classe = (T 'A rede desta maquina inspeciona HTTPS: o programa nao reconheceu o certificado apresentado. O log diz o que fazer (pedir ao TI o certificado raiz no Windows, ou montar o pacote em outra rede e trazer pelo modo 3).') + [char]10 + [char]10
            } elseif ($rcMotor -eq 4) {
                $classe = (T 'O certificado do servidor foi recusado por estar fora da validade. Confira primeiro a DATA e a HORA do Windows desta maquina: com o relogio errado, todo certificado e recusado. Se o relogio estiver certo, o log diz o que fazer.') + [char]10 + [char]10
            } elseif ($rcMotor -eq 5) {
                $classe = (T 'O servidor de origem respondeu com erro (fora do ar ou sobrecarregado), mesmo depois de novas tentativas. Nao ha defeito no pacote nem na rede desta maquina. O que ja foi baixado fica: mande preparar de novo daqui a alguns minutos.') + [char]10 + [char]10
            }
            Falhar ($classe + 'O preparo terminou com erro ' + $rcMotor + '.' + [char]10 + [char]10 +
                    'O log completo e o arquivo ' + (NomeDoArquivo $script:ArquivoLog) +
                    ', na pasta de trabalho escolhida.' + [char]10 + [char]10 +
                    'Mande esse arquivo junto com o relato.')
            return
        }

        if ($direto) {
            foreach ($resto in @('python-preparo', 'python-embed.zip')) {
                $r0 = Join-Path $pyDir $resto
                if (Test-Path -LiteralPath $r0) {
                    Remove-Item -LiteralPath $r0 -Recurse -Force -ErrorAction SilentlyContinue
                }
            }
            if ($script:Modo -eq '1') { LevarDoPreparoAntigo $trab }
            InstalarNoLugar $trab
            if (-not $script:InstalouNoLugar) {
                $script:Instalado = AcharInstalacao
                try { PintarEstado } catch { }
                Falhar ('A instalacao nao completou: ' + $script:MotivoDaInstalacao + '.' + [char]10 + [char]10 +
                        'O programa esta em ' + $trab + ', sem a garantia dos atalhos e do registro.' + [char]10 +
                        'O log completo e o arquivo ' + (NomeDoArquivo $script:ArquivoLog) +
                        ', na pasta de trabalho escolhida.')
                return
            }
            $script:Instalado = AcharInstalacao
            try { PintarEstado } catch { }
            try { $btModo5.Enabled = [bool]$script:Instalado } catch { }
            $sobra = Join-Path $trab 'preparo'
            if (SobraDoPreparoAntigo $sobra) {
                Registrar ''
                $velhas = @(Get-ChildItem -LiteralPath $sobra -Directory -ErrorAction SilentlyContinue |
                            Where-Object { MarcaDeInstalacao $_.FullName } | ForEach-Object { $_.FullName })
                if ($velhas.Count -gt 0 -and $script:Modo -eq '1') {
                    Registrar ('  a instalacao antiga em ' + ($velhas -join ', ') + ' continua la: ' +
                               'o programa novo e o desta pasta, e a configuracao dela veio junto (' +
                               ((@($script:LevadosDoPreparo) + @()) -join ', ') + '). ' +
                               'Confira e apague a pasta "preparo" para liberar o disco.') 'alerta'
                } else {
                    Registrar ('  a pasta "preparo" ao lado sobrou de uma instalacao feita pela montagem antiga: ' +
                               'ela nao e usada pelo programa, e voce pode apaga-la para liberar o disco.') 'alerta'
                }
            }
            Registrar ''
            Registrar 'PRONTO.' 'ok'
            OferecerPluginsOpcionais
            AtualizarConclusao $trab ''
            $abas.SelectedTab = $aba4
            return
        }
        $todos = @(Get-ChildItem -LiteralPath $trab -Filter '*.zip' -Recurse -ErrorAction SilentlyContinue)
        $zip = $todos |
               Where-Object { $_.Name -like '*_BUNDLE_v*' -or $_.Name -like 'AUTO_CONTORNO*' } |
               Sort-Object @{ Expression = 'LastWriteTime'; Descending = $true },
                           @{ Expression = 'Length'; Descending = $true } |
               Select-Object -First 1
        if (-not $zip) {
            $zip = $todos | Sort-Object Length -Descending | Select-Object -First 1
        }
        if ($zip) {
            $script:PacoteFinal = $zip.FullName
            if ($script:Modo -eq '2' -and $script:PluginsParaLevar.Count) {
                Montar-PluginsPortateis $zip.DirectoryName $script:PluginsParaLevar
            }
        }
        else {
            Registrar ('NAO achei o .zip do pacote na pasta de trabalho' +
                       ' escolhida -- o preparo terminou bem, mas nao sei' +
                       ' dizer onde o arquivo ficou. Procure por *.zip' +
                       ' nessa pasta.') 'erro'
        }

        Registrar ''
        Registrar 'PRONTO.' 'ok'
        if ($script:PacoteFinal) {
            Registrar ('pacote: ' + (NomeDoArquivo $script:PacoteFinal) +
                       '  (na pasta de trabalho escolhida)') 'ok'
        }

        if ($script:EstacaoFinal -eq $true -and $script:PacoteFinal) {
            Registrar ''
            Registrar 'Instalando nesta maquina (voce disse que ela e a estacao de uso)' 'titulo'
            InstalarAqui $script:PacoteFinal
            OferecerPluginsOpcionais
        }

        AtualizarConclusao $trab $script:PacoteFinal
        $abas.SelectedTab = $aba4
    }
    catch {
        Falhar ('Erro inesperado: ' + $_.Exception.Message)
    }
    finally {
        $script:Ocupado = $false
        $script:Cancelar = $false
        if ($script:BtParar) { $script:BtParar.Enabled = $false }
        $btRodar.Enabled = $true
    }
}

function VersaoDoZip {
    param([string]$Zip)
    $lz = @{ versao = ''; projeto = ''; onde = ''; erro = '' }
    $z = $null
    try {
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        $z = [System.IO.Compression.ZipFile]::OpenRead($Zip)
        $achada = $null
        foreach ($e in $z.Entries) {
            $nome = ($e.FullName -replace '\\', '/')
            if ($nome -eq 'entrega.txt') { $achada = $e; break }
            if ((-not $achada) -and ($nome -match '^[^/]+/entrega\.txt$')) { $achada = $e }
        }
        if (-not $achada) {
            $lz.erro = (T 'o pacote nao tem o entrega.txt')
            return $lz
        }
        $lz.onde = ($achada.FullName -replace '\\', '/')
        $leitor = New-Object System.IO.StreamReader($achada.Open(), [System.Text.Encoding]::UTF8)
        try { $texto = $leitor.ReadToEnd() } finally { $leitor.Dispose() }
        foreach ($l in ($texto -split "`r?`n")) {
            if ($l -match '^\s*VERSAO\s*=\s*(.+?)\s*$') { if (-not $lz.versao) { $lz.versao = $Matches[1] } }
            elseif ($l -match '^\s*PROJETO\s*=\s*(.+?)\s*$') { if (-not $lz.projeto) { $lz.projeto = $Matches[1] } }
        }
        if (-not $lz.versao) {
            $lz.erro = ((T 'o entrega.txt do pacote nao diz a VERSAO ({0})') -f $lz.onde)
        }
    } catch {
        $lz.erro = $_.Exception.Message
    } finally {
        if ($z) { $z.Dispose() }
    }
    return $lz
}

function DecisaoDoPacote {
    param([string]$Pacote, [string]$Minimo, [string]$Instalador, [string]$Erro = '')
    if (-not $Pacote) {
        return @{ acao = 'recusa'
                  frase = ((T 'Nao consegui ler a versao deste pacote ({0}), e sem ela nao da para saber se este instalador o aceita. Monte um pacote novo com "Montar pacotes do app e dos plugins para levar".') -f
                           $(if ($Erro) { $Erro } else { 'VERSAO ausente' })) }
    }
    if ($Minimo -and (MaisNovaQue $Minimo $Pacote)) {
        return @{ acao = 'recusa'
                  frase = ((T 'Este pacote e da versao {0}; este instalador aceita pacote de transferencia da versao {1} ou superior. Monte um pacote novo com "Montar pacotes do app e dos plugins para levar".') -f
                           $Pacote, $Minimo) }
    }
    if ($Instalador -and (MaisNovaQue $Instalador $Pacote)) {
        return @{ acao = 'instala_e_atualiza'; frase = '' }
    }
    return @{ acao = 'instala'; frase = '' }
}

function ConfirmarCodigoDoPacote {
    if (-not $script:PastaInstalada -or (VersaoDaPasta $script:PastaInstalada) -ne $script:VERSAO_INSTALADOR) {
        throw ((T 'Falha ao montar os pacotes selecionados.') + ' ' + $script:VERSAO_INSTALADOR)
    }
}

function InstalarDeArquivo {
    param([string]$Titulo)
    $script:ResultadoModo3 = ''
    $dlg = New-Object System.Windows.Forms.OpenFileDialog
    try {
        $dlg.Title = $(if ($Titulo) { $Titulo } else { T 'Selecione um pacote da Local Suite e, se desejar, até dois pacotes dos plugins NEURO RT e LUNG RT.' })
        $dlg.Filter = (T 'Qualquer arquivo .zip') + ' (*.zip)|*.zip|' + (T 'Todos os arquivos') + ' (*.*)|*.*'
        $dlg.CheckFileExists = $true
        $dlg.Multiselect = $true
        if ($dlg.ShowDialog($form) -ne [System.Windows.Forms.DialogResult]::OK) {
            $abas.SelectedTab = $aba0
            return
        }
        $arquivos = @($dlg.FileNames)
    } finally { $dlg.Dispose() }
    $zip = $arquivos[0]
    $pacotesPlugins = @()
    if ($arquivos.Count -gt 1) {
        try {
            if (-not $script:OpcoesPluginsCarregadas) {
                throw (T 'O preparo dos plugins não está disponível nesta instalação. A suíte pode ser aberta normalmente.')
            }
            $pacotes = Ler-PacotesSuite -Caminhos $arquivos
            $zip = $pacotes.Base
            $pacotesPlugins = @($pacotes.Plugins)
        } catch {
            [void][System.Windows.Forms.MessageBox]::Show($_.Exception.Message,
                (T 'Pacotes offline'), 'OK', 'Warning')
            return
        }
    }
    AnotarPastaDoOperador (Split-Path -Parent $zip) '<pasta do .zip>'

    try {
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        $z = [System.IO.Compression.ZipFile]::OpenRead($zip)
        $tem = @($z.Entries | Where-Object { $_.FullName -eq 'INSTALL.ps1' }).Count
        $n   = $z.Entries.Count
        $z.Dispose()
    } catch {
        [System.Windows.Forms.MessageBox]::Show(
            ((T 'Nao consegui abrir esse arquivo como .zip:') + "`r`n`r`n" + $_.Exception.Message),
            (T 'Arquivo invalido'), 'OK', 'Error') | Out-Null
        return
    }
    if ($tem -eq 0) {
        [System.Windows.Forms.MessageBox]::Show(
            (T 'Esse .zip nao tem o INSTALL.ps1 na raiz, entao ele nao e um pacote deste programa. Escolha o arquivo gerado por "Montar pacotes do app e dos plugins para levar".'),
            (T 'Nao e um pacote da Radioterapia.ai Local Suite'), 'OK', 'Warning') | Out-Null
        return
    }

    $vz = VersaoDoZip $zip
    $dec = DecisaoDoPacote $vz.versao $script:BUNDLE_MINIMO $script:VERSAO_INSTALADOR $vz.erro
    if ($dec.acao -eq 'recusa') {
        Registrar ('  o modo 3 recusou ' + (NomeDoArquivo $zip) + ': ' + $dec.frase) 'alerta'
        [System.Windows.Forms.MessageBox]::Show($dec.frase,
            (T 'Este pacote nao serve a este instalador'), 'OK', 'Warning') | Out-Null
        return
    }
    $termos = Ler-TermosDoZip $zip
    $dados = @{zip=$zip; vz=$vz; dec=$dec; n=$n; pacotesPlugins=$pacotesPlugins; termos=$termos}
    try {
        $plugins=@()
        if ($pacotesPlugins.Count) {
            $catalogo=Ler-CatalogoPluginsSuite (Join-Path $script:AQUI 'plugin-options.json')
            $script:PlanoPlugins=PlanoDosZipsPlugins $catalogo $pacotesPlugins
            $plugins=@($script:PlanoPlugins.plugins | ForEach-Object { $_.id })
        }
        ContinuarComTermos 'arquivo' $dados $termos.arquivo $termos.perfil $termos.omitidos -Plugins $plugins
    } catch { LimparTermosDoPacote $dados; Falhar $_.Exception.Message }
}

function InstalarArquivoSelecionado {
    param($Zip, $Vz, $Dec, $N, $PacotesPlugins, $Termos)
    $raizEscolhida = ''
    try { $raizEscolhida = ([string]$cxPasta.Text).Trim().TrimEnd('\') } catch { }
    if (-not $raizEscolhida) { $raizEscolhida = $script:DESTINO_PADRAO }
    $abas.SelectedTab = $aba3
    if (-not (GarantirAppFechado (PastaQueOPacoteOcupa $raizEscolhida $vz.projeto))) { return }

    if (-not $script:Trabalho -or -not (Test-Path -LiteralPath $script:Trabalho)) {
        $script:Trabalho = Join-Path $env:TEMP ('radai_receber_' + [System.IO.Path]::GetRandomFileName().Substring(0,8))
        New-Item -ItemType Directory -Path $script:Trabalho -Force | Out-Null
    }

    $script:Ocupado = $true
    $script:BtRodar.Enabled = $false
    try {
        $abas.SelectedTab = $aba3
        Registrar ''
        Registrar 'INSTALANDO A PARTIR DO ARQUIVO TRAZIDO' 'titulo'
        Registrar ('  arquivo: ' + (NomeDoArquivo $zip))
        Registrar ('  {0} item(ns) dentro' -f $n)
        Registrar ('  pacote v' + $vz.versao + ' (' + $vz.onde + '); este instalador v' +
                   $script:VERSAO_INSTALADOR + ', que aceita a partir da v' + $script:BUNDLE_MINIMO)
        if ($dec.acao -eq 'instala_e_atualiza') {
            Registrar ('  o código v' + $script:VERSAO_INSTALADOR + ' será aplicado à extração antes da instalação.')
        }
        try { AnotarPastaDoOperador $raizEscolhida '<pasta de destino>' } catch { }
        InstalarAqui $zip $raizEscolhida
        if ($dec.acao -eq 'instala_e_atualiza') { ConfirmarCodigoDoPacote }
        OferecerPluginsOpcionais
        AtualizarConclusao $script:Trabalho $zip
        $abas.SelectedTab = $aba4
    } finally {
        $script:Ocupado = $false
        $script:BtRodar.Enabled = $true
    }
}

function PastaQueOPacoteOcupa {
    param([string]$Raiz, [string]$Projeto)
    $r = ([string]$Raiz).Trim().TrimEnd('\')
    if (-not $Projeto) { return $r }
    if (MarcaDeInstalacaoAntiga $r) { return $r }
    if ((Split-Path -Leaf $r) -ieq $Projeto) { return $r }
    return (Join-Path $r $Projeto)
}

function RaizParaOInstalador {
    param([string]$Raiz, [string]$Projeto)
    # GUARDA: com a raiz terminando no projeto, o INSTALL.ps1 de um pacote
    # antigo gravaria o _instalados.json DENTRO da pasta do programa.
    $r = ([string]$Raiz).Trim().TrimEnd('\')
    if ($Projeto -and ((Split-Path -Leaf $r) -ieq $Projeto)) {
        $pai = Split-Path -Parent $r
        if ($pai) { return $pai }
    }
    return $r
}

function EscolherPacoteTrazido {
    param([string]$Titulo = '')
    $dlg = New-Object System.Windows.Forms.OpenFileDialog
    $dlg.Title  = $(if ($Titulo) { $Titulo } else { (T 'Escolha o arquivo que voce trouxe') })
    $dlg.Filter = (T 'Pacote do Radioterapia.ai') + ' (*.zip)|*RADIOTERAPIA_AI*.zip;*AUTO_CONTORNO*.zip|' + (T 'Qualquer arquivo .zip') + ' (*.zip)|*.zip|' + (T 'Todos os arquivos') + ' (*.*)|*.*'
    $dlg.CheckFileExists = $true
    if ($dlg.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { return '' }
    return [string]$dlg.FileName
}

function AtualizarDePacote {
    param($Inst, [string]$Titulo = '')
    $script:ResultadoModo3 = ''
    $pasta = ([string]$Inst.pasta).TrimEnd('\')
    $zip = [string](UltimoDaSaida (EscolherPacoteTrazido $Titulo))
    if (-not $zip) { return 'sem_pacote' }
    AnotarPastaDoOperador (Split-Path -Parent $zip) '<pasta do .zip>'
    $tem = 0
    try {
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        $z = [System.IO.Compression.ZipFile]::OpenRead($zip)
        $tem = @($z.Entries | Where-Object { $_.FullName -eq 'INSTALL.ps1' }).Count
        $z.Dispose()
    } catch {
        [System.Windows.Forms.MessageBox]::Show(
            ((T 'Nao consegui abrir esse arquivo como .zip:') + "`r`n`r`n" + $_.Exception.Message),
            (T 'Arquivo invalido'), 'OK', 'Error') | Out-Null
        return 'recusado'
    }
    if ($tem -eq 0) {
        [System.Windows.Forms.MessageBox]::Show(
            (T 'Esse .zip nao tem o INSTALL.ps1 na raiz, entao ele nao e um pacote deste programa. Escolha o arquivo gerado por "Montar pacotes do app e dos plugins para levar".'),
            (T 'Nao e um pacote da Radioterapia.ai Local Suite'), 'OK', 'Warning') | Out-Null
        return 'recusado'
    }
    $vz = VersaoDoZip $zip
    $dec = DecisaoDoPacote $vz.versao $script:BUNDLE_MINIMO $script:VERSAO_INSTALADOR $vz.erro
    if ($dec.acao -eq 'recusa') {
        [System.Windows.Forms.MessageBox]::Show($dec.frase,
            (T 'Este pacote nao serve a este instalador'), 'OK', 'Warning') | Out-Null
        return 'recusado'
    }
    if ((PastaQueOPacoteOcupa (Split-Path -Parent $pasta) $vz.projeto) -ine $pasta) {
        [System.Windows.Forms.MessageBox]::Show(
            ((T 'A instalacao achada esta numa pasta de outro nome, e este pacote instala numa pasta {0}. Use "Máquina offline: instalar de um pacote que eu trouxe" e escolha a pasta.') -f $vz.projeto) +
            "`r`n`r`n" + $pasta, (T 'Atualizar'), 'OK', 'Warning') | Out-Null
        return 'recusado'
    }
    $termos = Ler-TermosDoZip $zip
    $dados = @{inst=$Inst; pasta=$pasta; zip=$zip; vz=$vz; dec=$dec; termos=$termos}
    ContinuarComTermos 'pacote' $dados $termos.arquivo $termos.perfil $termos.omitidos
    return 'selecionado'
}

function AtualizarPacoteSelecionado {
    param($Inst, $Pasta, $Zip, $Vz, $Dec, $Termos)
    EsconderPreparo
    $script:Ocupado = $true
    $script:BtRodar.Enabled = $false
    $res = 'falhou'
    try {
        Registrar ''
        Registrar 'ATUALIZANDO A PARTIR DO PACOTE TRAZIDO' 'titulo'
        Registrar ('  pasta: ' + $pasta + ' (' + (DescreverUnidade $pasta) + ')')
        Registrar ('  arquivo: ' + (NomeDoArquivo $zip) + ', pacote v' + $vz.versao +
                   '; este instalador v' + $script:VERSAO_INSTALADOR)
        Registrar '  Nada e baixado. A sua configuracao, o registro de casos e os logs ficam.'
        if (-not (GarantirAppFechado $pasta)) {
            $res = 'aberto'
        } else {
            InstalarAqui $zip (Split-Path -Parent $pasta)
            if ($dec.acao -eq 'instala_e_atualiza') { ConfirmarCodigoDoPacote }
            Registrar ''
            if ($script:PastaInstalada) {
                Registrar ('ATUALIZADO A PARTIR DO PACOTE v' + $vz.versao + '.') 'ok'
                $res = 'feito'
            } else {
                Registrar 'A atualizacao a partir do pacote nao completou. Veja o log acima.' 'erro'
            }
            if ($script:ResultadoModo3) { Registrar ('  ' + $script:ResultadoModo3) 'alerta' }
            $script:Instalado = AcharInstalacao
            try { PintarEstado } catch { }
        }
    } catch {
        Falhar ('Erro ao atualizar: ' + $_.Exception.Message)
    } finally {
        $script:Ocupado = $false
        $script:BtRodar.Enabled = $true
        MostrarPreparo
        if ($res -ne 'feito') { MostrarRetentativa }
    }
    if ($res -eq 'feito') { ConcluirAtualizacao $Inst 'pacote' ([string]$Inst.versao) }
}

function PastaDeExtracao {
    param([string]$Zip, [string]$Raiz = '')
    $cands = @()
    $d = $Raiz
    if (-not $d) { try { $d = ($cxPasta.Text).Trim() } catch { $d = '' } }
    if ($d) { $cands += $d }
    if ($Zip) { $cands += (Split-Path -Parent $Zip) }
    $cands += $env:TEMP
    foreach ($c in $cands) {
        if (-not $c) { continue }
        try { $q = Split-Path -Qualifier $c } catch { continue }
        if (-not $q) { continue }
        return ([System.IO.Path]::Combine($c, '_radai_extracao'))
    }
    return ([System.IO.Path]::Combine($env:TEMP, '_radai_extracao'))
}

function LivreEm {
    param([string]$Caminho)
    try {
        $q = Split-Path -Qualifier $Caminho
        return (New-Object System.IO.DriveInfo($q)).AvailableFreeSpace
    } catch { return -1 }
}

function GB { param($b) return ('{0:N1} GB' -f ($b / 1GB)) }

$script:RelogioPump = [System.Diagnostics.Stopwatch]::StartNew()
$script:BufExtracao = New-Object byte[] (4MB)
function PumpSeHouveTempo {
    if ($script:RelogioPump.ElapsedMilliseconds -ge 100) {
        Pump
        $script:RelogioPump.Restart()
    }
}

function ExtrairEntrada {
    param($Entrada, [string]$Destino)
    $de = $Entrada.Open()
    try {
        $para = [System.IO.File]::Create($Destino)
        try {
            while (($n = $de.Read($script:BufExtracao, 0, $script:BufExtracao.Length)) -gt 0) {
                $para.Write($script:BufExtracao, 0, $n)
                PumpSeHouveTempo
                if ($script:Cancelar) { throw 'cancelado por voce' }
            }
        } finally { $para.Dispose() }
    } finally { $de.Dispose() }
    try { [System.IO.File]::SetLastWriteTime($Destino, $Entrada.LastWriteTime.DateTime) } catch { }
}

function RemoverSemTravar {
    param([string]$Pasta)
    try {
        $env:RADAI_APAGAR = $Pasta
        $pr = Start-Process -FilePath 'powershell' -WindowStyle Hidden -PassThru `
                -ArgumentList @('-NoProfile', '-Command',
                    'Remove-Item -LiteralPath $env:RADAI_APAGAR -Recurse -Force -ErrorAction SilentlyContinue')
        while (-not $pr.HasExited) { Start-Sleep -Milliseconds 100; Pump }
    } catch {
        Remove-Item -LiteralPath $Pasta -Recurse -Force -ErrorAction SilentlyContinue
    } finally {
        $env:RADAI_APAGAR = $null
    }
}

function InstalarAqui {
    param([string]$Zip, [string]$Raiz = '')
    $reciboZip = $script:ReciboIndividual
    if (-not $reciboZip) { throw (T 'Os termos de uso precisam ser aceitos antes de continuar.') }
    $script:PastaInstalada = ''
    $opcoes = [IO.File]::ReadAllText($reciboZip,[Text.Encoding]::UTF8) | ConvertFrom-Json
    if ($opcoes.PSObject.Properties['omitidos']) { $omitir = @($opcoes.omitidos) }
    else { $omitir = @('cads_open','moose','nv_segment_ct' | Where-Object { $_ -notin @($opcoes.itens.id) }) }
    if (-not $Raiz) { try { $Raiz = ([string]$cxPasta.Text).Trim() } catch { $Raiz = '' } }
    $tmp = PastaDeExtracao $Zip $Raiz
    try {
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        $zq = [System.IO.Compression.ZipFile]::OpenRead($Zip)
        try { $precisa = ($zq.Entries | Measure-Object -Property Length -Sum).Sum }
        finally { $zq.Dispose() }
        $destino0 = $Raiz
        $mesmoDisco = $false
        if ($destino0) {
            try {
                $mesmoDisco = ((Split-Path -Qualifier $destino0) -eq
                               (Split-Path -Qualifier $tmp))
            } catch { }
        }
        $fator = 1; if ($mesmoDisco) { $fator = 2 }
        $livre = LivreEm $tmp
        $noZip = 0
        try { $noZip = (Get-Item -LiteralPath $Zip).Length } catch { }
        Registrar ('  o pacote ocupa ' + (GB $precisa) + ' extraido' +
                   $(if ($noZip -gt 0) { ' (o .zip tem ' + (GB $noZip) +
                                         ' - ele nao e comprimido)' } else { '' }) +
                   '; ' + (Split-Path -Qualifier $tmp) + ' tem ' +
                   (GB $livre) + ' livre')
        if ($livre -ge 0 -and $livre -lt ($precisa * $fator)) {
            throw ((T 'Falta espaco em disco.') + ' ' +
                   (Split-Path -Qualifier $tmp) + ': ' + (GB $livre) + ' livre, ' +
                   (GB ($precisa * $fator)) + ' necessarios (' + (GB $precisa) +
                   ' para extrair' + $(if ($fator -eq 2) { ' e outro tanto para instalar no mesmo disco' } else { '' }) + ').')
        }
        if (Test-Path -LiteralPath $tmp) {
            RemoverSemTravar $tmp
            if (Test-Path -LiteralPath $tmp) {
                throw ((T 'Nao consegui apagar a extracao anterior. Feche o que estiver usando esta pasta e tente de novo:') +
                       ' ' + $tmp)
            }
        }
        New-Item -ItemType Directory -Path $tmp -Force | Out-Null
        Registrar ('  extraindo o pacote em ' + $tmp + ' ...')
        $za = [System.IO.Compression.ZipFile]::OpenRead($Zip)
        try {
            $total = $za.Entries.Count
            $feitos = 0
            $ultimo = 0
            foreach ($ent in $za.Entries) {
                if ($script:Cancelar) {
                    throw 'cancelado por voce'
                }
                $nomeNoZip = $ent.FullName.Replace('\','/')
                if ($nomeNoZip -match '^LOCAL_SUITE/(registro|Plugins|modelos/rocards)(/|$)') { continue }
                if ($nomeNoZip -match '^LOCAL_SUITE/modelos/([^/]+)/' -and $Matches[1] -in $omitir) { continue }
                $destino = [IO.Path]::GetFullPath((Join-Path $tmp $ent.FullName))
                if (-not $destino.StartsWith(([IO.Path]::GetFullPath($tmp).TrimEnd('\') + '\'), [StringComparison]::OrdinalIgnoreCase)) { throw 'Entrada fora da pasta do pacote.' }
                $pai = Split-Path -Parent $destino
                if ($pai -and -not (Test-Path -LiteralPath $pai)) {
                    New-Item -ItemType Directory -Force -Path $pai | Out-Null
                }
                if ($ent.Name) {
                    ExtrairEntrada $ent $destino
                }
                $feitos++
                PumpSeHouveTempo
                if (($feitos - $ultimo) -ge 2000) {
                    $ultimo = $feitos
                    Registrar ('    ' + $feitos + ' de ' + $total + ' arquivos')
                }
            }
        } finally {
            $za.Dispose()
        }
        $infoExtracao = Join-Path $tmp 'entrega.txt'
        $leitura = Get-Content -LiteralPath $infoExtracao -Encoding UTF8
        $versaoCarga = ($leitura | Where-Object {$_ -match '^\s*VERSAO\s*='} | Select-Object -First 1) -replace '^\s*VERSAO\s*=\s*',''
        $idCarga = ($leitura | Where-Object {$_ -match '^\s*PROJETO\s*='} | Select-Object -First 1) -replace '^\s*PROJETO\s*=\s*',''
        if ($idCarga -notin @('LOCAL_SUITE','AUTO_CONTORNO')) { throw 'Bundle incompatível.' }
        if (-not (MaisNovaQue $versaoCarga $script:VERSAO_INSTALADOR)) {
            $pyCarga = Join-Path (Join-Path $tmp $idCarga) 'python/python.exe'
            $atualizarCarga = Join-Path (Split-Path -Parent $script:AQUI) 'build/atualizar_carga_offline.py'
            $estacaoAnterior = PastaQueOPacoteOcupa $Raiz $idCarga
            & $pyCarga -B $atualizarCarga $tmp (Split-Path -Parent $Zip) $estacaoAnterior |
                ForEach-Object { Registrar ([string]$_) }
            if ($LASTEXITCODE -ne 0) { throw (T 'Falha ao montar os pacotes selecionados.') }
        }
        $ps1 = Join-Path (Split-Path -Parent $script:AQUI) 'installer\INSTALL.ps1'
        if (-not (Test-Path -LiteralPath $ps1)) {
            throw (T 'Não encontrei o instalador que acompanha este SETUP.')
        }
        Registrar '  rodando o instalador...'
        $env:RADAI_PASTA_PACOTE = $tmp
        $projPac = ''
        try {
            $entPac = Join-Path $tmp 'entrega.txt'
            if (Test-Path -LiteralPath $entPac) {
                foreach ($l in [System.IO.File]::ReadAllLines($entPac)) {
                    if ($l -match '^\s*PROJETO\s*=\s*(.+?)\s*$') {
                        $projPac = $Matches[1]; break
                    }
                }
            }
        } catch { }
        $destino = $Raiz
        if (-not $destino) {
            $destino = $script:DESTINO_PADRAO
            Registrar ('  sem pasta escolhida: vale a padrao ' + $destino) 'alerta'
        }
        $destino = RaizParaOInstalador $destino $projPac
        $env:RADAI_RAIZ_INSTALACAO = $destino
        Registrar ('  instalando em ' + (PastaQueOPacoteOcupa $destino $projPac))
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = 'powershell.exe'
        $psi.Arguments = LinhaDeArgumentos @('-NoProfile','-ExecutionPolicy','Bypass','-File',$ps1)
        $psi.UseShellExecute = $false
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true
        $psi.CreateNoWindow = $true
        $psi.EnvironmentVariables['RADAI_IDIOMA'] = Idioma-Atual
        $proc = [Diagnostics.Process]::Start($psi)
        try { $codigo = AcompanharProcesso $proc } finally { $proc.Dispose() }
        if ($codigo -ne 0) { throw ((T 'O instalador retornou o código {0}.') -f $codigo) }
        $raizes = @($destino)
        if ($env:LOCALAPPDATA) { $raizes += (Join-Path $env:LOCALAPPDATA 'RADIOTERAPIA_AI') }
        $script:PastaInstalada = ''
        foreach ($r in $raizes) {
            if (-not $r) { continue }
            $cands = @()
            if ($projPac) { $cands += (Join-Path $r $projPac) }
            $cands += $r
            foreach ($cand in $cands) {
                if (MarcaDeInstalacao $cand) { $script:PastaInstalada = $cand; break }
            }
            if ($script:PastaInstalada) { break }
        }
        if ($script:PastaInstalada) {
            Registrar ('  INSTALADO em ' + $script:PastaInstalada) 'ok'
        } else {
            throw (T 'A instalação não foi confirmada. Consulte o log acima.')
        }
        try {
            $t = $script:Trabalho
            if ($t -and (Test-Path -LiteralPath $t) -and
                (Split-Path -Leaf $t).StartsWith('radai_receber_') -and
                ((Split-Path -Parent $t) -eq $env:TEMP) -and
                -not (Get-ChildItem -LiteralPath $t -Force)) {
                Remove-Item -LiteralPath $t -Force -ErrorAction SilentlyContinue
            }
        } catch { }
    } catch {
        Registrar ('  nao consegui instalar automaticamente: ' + $_.Exception.Message) 'alerta'
        Registrar '  CAMINHO A MAO:' 'alerta'
        Registrar ('    1. extraia o proprio ' + (Split-Path -Leaf $Zip))
        Registrar '       num disco com espaco (nao e o instalador leve: e este .zip)'
        Registrar '    2. rode o INSTALL.cmd de DENTRO da pasta extraida'
        throw
    } finally {
        $env:RADAI_RAIZ_INSTALACAO = $null
        $env:RADAI_PASTA_PACOTE = $null
        if ($tmp -and (Test-Path -LiteralPath $tmp)) {
            Registrar '  removendo a extracao...'
            RemoverSemTravar $tmp
        }
    }
}

function PerguntaDoRetrocesso {
    param([string]$Pasta)
    $vInst = VersaoDaPasta $Pasta
    if (-not $vInst -or -not $script:VERSAO_INSTALADOR) { return '' }
    if (-not (MaisNovaQue $vInst $script:VERSAO_INSTALADOR)) { return '' }
    return ((T 'A versao instalada nesta pasta (v{0}) e mais nova que este instalador (v{1}). Instalar por cima volta a estacao para a v{1}. Continuar mesmo assim?') -f
            $vInst, $script:VERSAO_INSTALADOR)
}

function ConfirmarSeRetrocede {
    param([string]$Pasta)
    $pergunta = PerguntaDoRetrocesso $Pasta
    if (-not $pergunta) { return $true }
    $r = [System.Windows.Forms.MessageBox]::Show(
        $pergunta,
        (T 'Versao mais antiga'),
        [System.Windows.Forms.MessageBoxButtons]::YesNo,
        [System.Windows.Forms.MessageBoxIcon]::Warning)
    return ([string]$r -eq 'Yes')
}

function RegistroDaInstalacaoConfere {
    param([string]$Pasta)
    try {
        $reg = Join-Path (Split-Path -Parent $Pasta) '_instalados.json'
        if (-not (Test-Path -LiteralPath $reg)) { return $false }
        $j = [System.IO.File]::ReadAllText($reg, [System.Text.Encoding]::UTF8) | ConvertFrom-Json
        $ver = ''
        foreach ($l in (Get-Content -LiteralPath (Join-Path $Pasta 'entrega.txt') -Encoding UTF8)) {
            if ($l -match '^\s*VERSAO\s*=\s*(.+?)\s*$') { $ver = $Matches[1] }
        }
        $alvo = [System.IO.Path]::GetFullPath($Pasta).TrimEnd('\')
        foreach ($p in $j.PSObject.Properties) {
            $c = [string]$p.Value.caminho
            if (-not $c) { continue }
            if (([System.IO.Path]::GetFullPath($c).TrimEnd('\') -ieq $alvo) -and
                ([string]$p.Value.versao -eq $ver)) { return $true }
        }
    } catch { }
    return $false
}

function InstalarNoLugar {
    param([string]$Pasta)
    $script:PastaInstalada = ''
    $script:InstalouNoLugar = $false
    $script:MotivoDaInstalacao = 'o INSTALL.ps1 nao rodou'
    $rcIns = $null
    $ps1 = Join-Path (Split-Path -Parent $script:AQUI) 'installer\INSTALL.ps1'
    if (-not (Test-Path -LiteralPath $ps1)) { $ps1 = Join-Path $script:AQUI 'INSTALL.ps1' }
    Registrar ''
    Registrar '8/8  Atalhos e registro (a pasta ja e a final: nada a copiar)' 'titulo'
    if (-not (Test-Path -LiteralPath $ps1)) {
        Registrar '  nao achei o INSTALL.ps1 junto deste instalador: sem atalhos nem registro' 'alerta'
        $script:MotivoDaInstalacao = 'nao achei o INSTALL.ps1 junto deste instalador'
        return
    }
    $arqSaida = Join-Path (Join-Path $Pasta '_instalacao') '_instalador_saida.txt'
    $idi = ''
    try { $idi = Idioma-Atual } catch { }
    $env:RADAI_INSTALAR_NO_LUGAR = $Pasta
    $env:RADAI_PASTA_PACOTE = $script:AQUI
    if ($idi) { $env:RADAI_IDIOMA = $idi }
    try {
        $argumentos = LinhaDeArgumentos @('-NoProfile','-ExecutionPolicy','Bypass','-File',$ps1)
        $pIns = Start-Process -FilePath 'powershell' -ArgumentList $argumentos `
                -RedirectStandardOutput $arqSaida -NoNewWindow -PassThru
        try { $null = $pIns.Handle } catch { }
        $lidas = 0
        while (-not $pIns.HasExited) {
            Start-Sleep -Milliseconds 120
            Pump
            try {
                $tudo = @(Get-Content -LiteralPath $arqSaida -Encoding UTF8 -ErrorAction SilentlyContinue)
                while ($lidas -lt $tudo.Count) { Registrar ('    ' + $tudo[$lidas]); $lidas++ }
            } catch { }
        }
        $pIns.WaitForExit()
        try { $rcIns = $pIns.ExitCode } catch { $rcIns = $null }
        try {
            $tudo = @(Get-Content -LiteralPath $arqSaida -Encoding UTF8 -ErrorAction SilentlyContinue)
            while ($lidas -lt $tudo.Count) { Registrar ('    ' + $tudo[$lidas]); $lidas++ }
        } catch { }
    } catch {
        Registrar ('  nao consegui rodar o INSTALL.ps1: ' + $_.Exception.Message) 'alerta'
    } finally {
        $env:RADAI_INSTALAR_NO_LUGAR = $null
        $env:RADAI_PASTA_PACOTE = $null
        $env:RADAI_IDIOMA = $null
        Remove-Item -LiteralPath $arqSaida -Force -ErrorAction SilentlyContinue
    }
    # GUARDA: o entrega.txt ja esta na pasta antes do INSTALL.ps1 rodar; a
    # marca sozinha nao prova nada. Vale o codigo de saida e o registro.
    if ($rcIns -ne 0) {
        $script:MotivoDaInstalacao = ('o INSTALL.ps1 terminou com o codigo ' + $rcIns)
    } elseif (-not (MarcaDeInstalacao $Pasta)) {
        $script:MotivoDaInstalacao = 'faltam as marcas do programa na pasta final'
    } elseif (-not (RegistroDaInstalacaoConfere $Pasta)) {
        $script:MotivoDaInstalacao = 'esta pasta nao entrou no _instalados.json com a versao do entrega.txt'
    } else {
        $script:InstalouNoLugar = $true
    }
    if ($script:InstalouNoLugar) {
        $script:PastaInstalada = $Pasta
        Registrar ('  INSTALADO em ' + $Pasta) 'ok'
    } else {
        Registrar ('  a instalacao NAO completou: ' + $script:MotivoDaInstalacao + ' - veja o log acima') 'alerta'
    }
}

$rodape = NovoRotulo 'Código aberto · 12 idiomas · 100% local — pós-processamento sobre modelos publicados, para estudo e comparação.' 20 652 940 20 9 'Regular' $script:Cor.Fraco
$rodape.Anchor = 'Bottom,Left'
$form.Controls.Add($rodape)

AtualizarConclusao '' ''
$abas.Add_SelectedIndexChanged({
    if ($abas.SelectedTab -eq $aba2 -and -not $script:PainelTermosAtual) {
        MostrarTermosNaAba $script:CatalogoDeTermos (PerfilParaTermos)
        $script:PainelTermosAtual.Tag.btn.Enabled = $false
        $script:PainelTermosAtual.Tag.opcoes.Enabled = $false
    }
})
$form.Add_FormClosed({
    if ($script:AcaoDosTermos) { LimparTermosDoPacote $script:AcaoDosTermos.dados }
})

function _AutoRotulo {
    param($C)
    $t = ''
    try { $t = [string]$C.Text } catch { $t = '' }
    $t = ($t -replace "[`r`n`t]", ' ')
    if ($t.Length -gt 46) { $t = $t.Substring(0, 46) }
    if (-not $t) { $t = '(' + $C.GetType().Name + ')' }
    return $t
}

function _AutoMedir {
    param($Pai, [string]$Onde, [string]$Fase)
    $vis = $Pai.ClientRectangle
    $rola = $false
    try { $rola = [bool]$Pai.AutoScroll } catch { $rola = $false }
    foreach ($c in $Pai.Controls) {
        $tipo = $c.GetType().Name
        if ($tipo -in @('Button', 'RadioButton', 'CheckBox', 'LinkLabel')) {
            $b = $c.Bounds
            $fora = @()
            if (-not $rola -and $b.Bottom -gt $vis.Bottom) { $fora += ('abaixo por ' + ($b.Bottom - $vis.Bottom)) }
            if ($b.Right  -gt $vis.Right)  { $fora += ('a direita por ' + ($b.Right - $vis.Right)) }
            if (-not $rola -and $b.Top -lt 0) { $fora += ('acima por ' + (-$b.Top)) }
            if ($b.Left   -lt 0)           { $fora += ('a esquerda por ' + (-$b.Left)) }
            if ($fora.Count) {
                [Console]::Out.WriteLine("FORA`t" + $Fase + "`t" + $Onde + "`t" +
                              (_AutoRotulo $c) + "`t" + ($fora -join ', ') +
                              "`tcontrole=" + $b.ToString() + " visivel=" + $vis.ToString())
            }
        }
        if ($c.Controls.Count -gt 0) {
            _AutoMedir $c ($Onde + '/' + $tipo) $Fase
        }
    }
}

function CapturarTelaPreparador($Janela, [string]$Nome) {
    if (-not $env:RADAI_PREPARADOR_CAPTURA) { return }
    $Janela.Refresh()
    Pump
    $bmp = [Drawing.Bitmap]::new($Janela.Width,$Janela.Height)
    try {
        $Janela.DrawToBitmap($bmp,[Drawing.Rectangle]::new(0,0,$bmp.Width,$bmp.Height))
        # RichEdit does not draw its client text for WM_PRINT sent by DrawToBitmap.
        if ($Janela -eq $form -and $abas.SelectedTab -in @($aba3,$aba4)) {
            if (-not ('LocalSuiteRichEditCapture' -as [type])) {
                Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public static class LocalSuiteRichEditCapture {
    [StructLayout(LayoutKind.Sequential)] struct RECT { public int l,t,r,b; }
    [StructLayout(LayoutKind.Sequential)] struct RANGE { public int first,last; }
    [StructLayout(LayoutKind.Sequential)] struct FORMAT { public IntPtr device, target; public RECT area,page; public RANGE range; }
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern IntPtr SendMessage(IntPtr w, int m, IntPtr p, IntPtr data);
    public static void Render(IntPtr control, IntPtr dc, int widthTwips, int heightTwips) {
        var rect = new RECT {l=30,t=15,r=widthTwips,b=heightTwips};
        var f = new FORMAT { device=dc, target=dc, area=rect, page=rect, range=new RANGE {first=0,last=-1} };
        IntPtr mem=Marshal.AllocCoTaskMem(Marshal.SizeOf(typeof(FORMAT)));
        try { Marshal.StructureToPtr(f,mem,false); SendMessage(control,0x0439,(IntPtr)1,mem); }
        finally { SendMessage(control,0x0439,IntPtr.Zero,IntPtr.Zero); Marshal.FreeCoTaskMem(mem); }
    }
}
"@
            }
            $box = if ($abas.SelectedTab -eq $aba3) { $script:CaixaLog } else { $txt4 }
            if ($box -and $box.TextLength) {
                $client = $box.ClientSize
                $page = [Drawing.Bitmap]::new($client.Width,$client.Height)
                $g = [Drawing.Graphics]::FromImage($page)
                try {
                    $g.Clear($box.BackColor)
                    $tx=[int](1440*$client.Width/$g.DpiX); $ty=[int](1440*$client.Height/$g.DpiY)
                    $dc = $g.GetHdc()
                    try { [LocalSuiteRichEditCapture]::Render($box.Handle,$dc,$tx,$ty) } finally { $g.ReleaseHdc($dc) }
                    $p = $box.PointToScreen([Drawing.Point]::Empty)
                    $dest = [Drawing.Graphics]::FromImage($bmp)
                    try { $dest.DrawImageUnscaled($page,$p.X-$Janela.Left,$p.Y-$Janela.Top) } finally { $dest.Dispose() }
                } finally { $g.Dispose(); $page.Dispose() }
            }
        }
        $bmp.Save((Join-Path $env:RADAI_PREPARADOR_CAPTURA ($Nome+'.png')), [Drawing.Imaging.ImageFormat]::Png)
    } finally { $bmp.Dispose() }
}

if ($env:RADAI_PREPARADOR_AUTOTESTE) {
    $form.Add_Shown({
        try {
            $esperadas = @($aba0,$aba2,$aba3,$aba4)
            if ($abas.TabPages.Count -ne 4) { throw 'Unexpected tab count' }
            foreach ($aba in $esperadas) { _AutoMedir $aba $aba.Text 'normal' }
            if ($mMarca.Tag.Palavra + $mMarca.Tag.Sufixo -cne 'Local Suite') { throw 'Unexpected header' }
            if ($env:RADAI_PREPARADOR_CAPTURA) {
                # No receipt is read, migrated or written for this visual fixture.
                function script:DecisaoAnteriorSuite { param($Catalogo) return $null }
                $abas.SelectedTab = $aba0
                CapturarTelaPreparador $form '01-inicio'
                $catalogosExemplo=@(foreach ($perfil in @('full','plugin-neuro','plugin-lung','plugin-coronarias')) { Ler-CatalogoSuite $script:CatalogoDeTermos $perfil })
                MostrarTermosNaAba $script:CatalogoDeTermos 'full' -Contextos @(ContextosDosTermos $catalogosExemplo)
                CapturarTelaPreparador $form '02-termos'
                $abas.SelectedTab = $aba0
                $abas.SelectedTab = $aba2
                if (-not $script:PainelTermosAtual.Tag.btn.Enabled) { throw 'Back/forward lost pending consent' }
                if (-not @($script:PainelTermosAtual.Tag.lista.Controls | Where-Object {$_ -is [Windows.Forms.LinkLabel] -and $_.Tag.Scheme -eq 'https'}).Count) { throw 'Terms have no links' }
                $script:Modo = '7'
                $script:Instalado = @{pasta='C:\RADIOTERAPIA_AI\LOCAL_SUITE'; versao='8.25.1'}
                AtualizarSugestaoPasta
                $abas.SelectedTab = $aba3
                Registrar 'Simulação · atualização dos componentes da estação.' 'titulo'
                Registrar 'Versão instalada: 8.25.1'
                Registrar 'Termos de uso já aceitos.' 'ok'
                Registrar 'Verificando as bibliotecas e os modelos da instalação.'
                $btParar.Enabled = $true
                CapturarTelaPreparador $form '03-progresso'
                $btParar.Enabled = $false
                Registrar 'Simulação · conexão interrompida. Os downloads concluídos serão reutilizados.' 'erro'
                MostrarRetentativa
                CapturarTelaPreparador $form '04-retomar'
                $script:PastaInstalada = $script:Instalado.pasta
                function script:CaminhoDoPrograma { return 'preview-only' }
                AtualizarConclusao $script:PastaInstalada ''
                $abas.SelectedTab = $aba4
                CapturarTelaPreparador $form '05-conclusao'
            }
            [Console]::Out.WriteLine('PASS: Native installer flow and layout')
        } catch {
            [Console]::Error.WriteLine('FAIL: '+ $_.Exception.Message + ' ' + $_.ScriptStackTrace)
            $script:FalhaAutoteste = $true
        } finally { $form.Close() }
    })
}

$script:FalhaAutoteste = $false
$script:TituloPintado = 'nunca'
$script:Splash = $null

function PintarTituloDaMarca {
    param($Painel, $Graficos)
    $t = $Painel.Tag
    $Graficos.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAlias
    $fmt = [System.Drawing.StringFormat]::GenericTypographic
    $zero = [System.Drawing.PointF]::Empty
    $w1 = $Graficos.MeasureString($t.Palavra, $t.Fonte, $zero, $fmt).Width
    $w2 = $Graficos.MeasureString($t.Sufixo, $t.Fonte, $zero, $fmt).Width
    $h = $Graficos.MeasureString($t.Palavra + $t.Sufixo, $t.Fonte, $zero, $fmt).Height
    $x = [single](($Painel.ClientSize.Width - ($w1 + $w2)) / 2)
    $y = [single](($Painel.ClientSize.Height - $h) / 2)
    $pincel = New-Object System.Drawing.SolidBrush($t.CorTexto)
    try { $Graficos.DrawString($t.Palavra, $t.Fonte, $pincel, $x, $y, $fmt) }
    finally { $pincel.Dispose() }
    $caixa = New-Object System.Drawing.RectangleF(($x + $w1), $y,
                                                  [math]::Max($w2, 1), [math]::Max($h, 1))
    $grad = New-Object System.Drawing.Drawing2D.LinearGradientBrush($caixa,
                $t.Cores[0], $t.Cores[2],
                [System.Drawing.Drawing2D.LinearGradientMode]::Horizontal)
    try {
        $mistura = New-Object System.Drawing.Drawing2D.ColorBlend(3)
        $mistura.Colors = [System.Drawing.Color[]]$t.Cores
        $mistura.Positions = [single[]]@(0.0, 0.48, 1.0)
        $grad.InterpolationColors = $mistura
        $Graficos.DrawString($t.Sufixo, $t.Fonte, $grad, ($x + $w1), $y, $fmt)
    } finally { $grad.Dispose() }
}

function MedirMarcaDaSplash {
    $s = $script:Splash
    $partes = @()
    $nImg = @($s.Form.Controls | Where-Object {
                  $_ -is [System.Windows.Forms.PictureBox] }).Count
    $partes += ('imagens=' + $nImg)
    $bmp = New-Object System.Drawing.Bitmap($s.Titulo.Width, $s.Titulo.Height)
    $claros = 0; $azuis = 0; $violetas = 0
    try {
        $s.Titulo.DrawToBitmap($bmp, (New-Object System.Drawing.Rectangle(0, 0, $bmp.Width, $bmp.Height)))
        for ($px = 0; $px -lt $bmp.Width; $px += 2) {
            for ($py = 0; $py -lt $bmp.Height; $py += 2) {
                $c = $bmp.GetPixel($px, $py)
                if ($c.R -gt 180 -and $c.G -gt 180 -and $c.B -gt 180) { $claros++ }
                elseif ($c.B -gt 200 -and $c.R -lt 110 -and $c.G -gt 130) { $azuis++ }
                elseif ($c.B -gt 200 -and $c.R -gt 120 -and $c.G -lt 170) { $violetas++ }
            }
        }
    } finally { $bmp.Dispose() }
    $partes += ('titulo=' + $s.Titulo.Tag.Palavra + $s.Titulo.Tag.Sufixo)
    $partes += ('pintado=' + $script:TituloPintado)
    $partes += ('pixels=' + $claros + '/' + $azuis + '/' + $violetas)
    $partes += ('sub=' + $s.Sub.Text)
    $partes += ('topo=' + $s.Titulo.Top)
    $partes += ('ordem=' + $(if (($s.Titulo.Bottom -le $s.Sub.Top) -and
                                 ($s.Sub.Bottom -le $s.Pergunta.Top) -and
                                 ($s.Pergunta.Bottom -le $s.Seletor.Top)) { 'ok' }
                             else { 'A MARCA NAO ESTA EM CIMA DO SELETOR' }))
    return ($partes -join "`t")
}

function PerguntarIdioma {
    $d = New-Object System.Windows.Forms.Form
    $d.Text = 'Select language'
    $d.ClientSize = New-Object System.Drawing.Size(440, 240)
    $d.StartPosition = 'CenterScreen'
    $d.FormBorderStyle = 'FixedDialog'
    $d.MaximizeBox = $false
    $d.MinimizeBox = $false
    $d.BackColor = $script:Cor.Fundo
    try { if ($form.Icon) { $d.Icon = $form.Icon } } catch { }

    Sessao 'Opening the Local Suite language selector'

    $tit = New-Object System.Windows.Forms.Panel
    $tit.Location = New-Object System.Drawing.Point(20, 28)
    $tit.Size = New-Object System.Drawing.Size(400, 50)
    $tit.BackColor = $script:Cor.Fundo
    $tit.Tag = @{
        Palavra  = 'Local'
        Sufixo   = ' Suite'
        Fonte    = (Fonte 26 'Bold')
        CorTexto = $script:Cor.Texto
        Cores    = @([System.Drawing.Color]::FromArgb(0x4D, 0xA3, 0xFF),
                     [System.Drawing.Color]::FromArgb(0x3D, 0xD9, 0xF0),
                     [System.Drawing.Color]::FromArgb(0x9D, 0x8B, 0xFF))
    }
    $tit.Add_Paint({
        param($remetente, $ev)
        try {
            PintarTituloDaMarca $remetente $ev.Graphics
            $script:TituloPintado = 'ok'
        } catch {
            $script:TituloPintado = ('ERRO ' + $_.Exception.Message)
        }
    })
    $d.Controls.Add($tit)

    $sub = New-Object System.Windows.Forms.Label
    $sub.Text = ''
    $sub.Location = New-Object System.Drawing.Point(20, 78)
    $sub.Size = New-Object System.Drawing.Size(400, 22)
    $sub.Font = Fonte 10 'Bold'
    $sub.ForeColor = $script:Cor.Fraco
    $sub.BackColor = [System.Drawing.Color]::Transparent
    $sub.TextAlign = [System.Drawing.ContentAlignment]::MiddleCenter
    $d.Controls.Add($sub)

    $t = New-Object System.Windows.Forms.Label
    $t.Text = 'Select your language'
    $t.Location = New-Object System.Drawing.Point(30, 120)
    $t.Size = New-Object System.Drawing.Size(380, 24)
    $t.Font = Fonte 10 'Bold'
    $t.ForeColor = $script:Cor.Titulo
    $t.BackColor = [System.Drawing.Color]::Transparent
    $d.Controls.Add($t)

    $sel = Novo-SeletorIdioma 30 148 380 $form $script:AoTrocarIdioma
    if ($sel) { $d.Controls.Add($sel); $script:SeletoresIdioma += $sel }

    $ok = New-Object System.Windows.Forms.Button
    $ok.Text = 'Continue'
    $ok.Location = New-Object System.Drawing.Point(310, 188)
    $ok.Size = New-Object System.Drawing.Size(100, 34)
    $ok.BackColor = $script:Cor.Titulo
    $ok.ForeColor = $script:Cor.Fundo
    $ok.FlatStyle = 'Flat'
    $ok.Add_Click({ $d.Close() })
    $d.Controls.Add($ok)
    $d.AcceptButton = $ok
    $script:Splash = @{ Form = $d; Titulo = $tit; Sub = $sub
                        Pergunta = $t; Seletor = $(if ($sel) { $sel } else { $ok }) }

    if ($env:RADAI_PREPARADOR_AUTOTESTE) {
        $d.Add_Shown({
            if ($t.Text -cne 'Select your language' -or $ok.Text -cne 'Continue') {
                $script:FalhaAutoteste = $true
            }
            CapturarTelaPreparador $d '00-language'
            if ($env:RADAI_PREPARADOR_IDIOMA_TESTE) {
                $idx = [array]::IndexOf($sel.Tag.Ordem, $env:RADAI_PREPARADOR_IDIOMA_TESTE)
                if ($idx -lt 0) { $script:FalhaAutoteste = $true }
                else { $sel.SelectedIndex = $idx }
                if ((Idioma-Atual) -ne $env:RADAI_PREPARADOR_IDIOMA_TESTE) { $script:FalhaAutoteste = $true }
            }
            $d.Close()
        })
    }
    [void]$d.ShowDialog()
}
if (-not $script:PastaDaCascata) {
    try { PerguntarIdioma } catch {
        [Console]::Out.WriteLine('Unable to open the language selector (' +
                                 $_.Exception.Message + ')')
    }
}
if ($script:PastaDaCascata -and -not $env:RADAI_PREPARADOR_AUTOTESTE) {
    $form.Add_Shown({ RetomarAtualizarApp })
}
Sessao ('tamanho do pacote: ~' + (GBInteiro $script:PacoteGB) + ' GB, de ' +
        $script:TamanhoDeOnde)
Sessao ('instalacao detectada: ' +
        $(if ($script:Instalado) {
              $script:Instalado.pasta + ' (' + (DescreverUnidade $script:Instalado.pasta) + ')'
          } else { 'nenhuma' }))
Sessao 'janela aberta'
try {
    [void]$form.ShowDialog()
} catch {
    Sessao ('ERRO que derrubou a janela: ' + $_.Exception.GetType().FullName +
            ': ' + $_.Exception.Message)
    Sessao ('  at: ' + $_.InvocationInfo.PositionMessage)
    $script:ErroJaNoLog = $true
    throw
}
Sessao 'janela fechada; fim normal'

if ($env:RADAI_PREPARADOR_AUTOTESTE -and $script:FalhaAutoteste) { exit 1 }
