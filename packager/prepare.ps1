
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

$script:AQUI     = Split-Path -Parent $MyInvocation.MyCommand.Path

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
Sessao ('preparador iniciado: PowerShell ' + $PSVersionTable.PSVersion + ', ' +
        $(if ([System.Threading.Thread]::CurrentThread.GetApartmentState() -eq 'STA') { 'STA' }
          else { 'MTA (o seletor de arquivo nao abre assim)' }) +
        ', pasta ' + (Split-Path -Parent $MyInvocation.MyCommand.Path))
$script:ErroJaNoLog = $false
trap {
    if (-not $script:ErroJaNoLog) {
        try {
            Sessao ('ERRO que parou o preparador: ' +
                    $_.Exception.GetType().FullName + ': ' + $_.Exception.Message)
            Sessao ('  em: ' + ([string]$_.InvocationInfo.PositionMessage -replace "[`r`n]+", ' | '))
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
# GUARDA: RADAI_ATUALIZAR_APP e RADAI_ATUALIZAR_APP_DE sao o contrato com o instalador anterior que baixou este; nao renomear.
$script:PastaDaCascata = [string]$env:RADAI_ATUALIZAR_APP
$script:CascataVeioDe = [string]$env:RADAI_ATUALIZAR_APP_DE
$env:RADAI_ATUALIZAR_APP = $null
$env:RADAI_ATUALIZAR_APP_DE = $null
$script:CascataConferiuAVersao = $false
$script:URLS_DA_REDE = @('https://pypi.org/simple/pip/', 'https://huggingface.co/api/models?limit=1')

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
$script:BUNDLE_MINIMO = ValorDaEntrega 'BUNDLE_MINIMO'
$script:BundleMinimoDeOnde = 'entrega.txt'
if (-not $script:BUNDLE_MINIMO) {
    $script:BUNDLE_MINIMO = $script:VERSAO_INSTALADOR
    $script:BundleMinimoDeOnde = 'recuo: o entrega.txt nao declara BUNDLE_MINIMO, e vale a propria VERSAO'
}
Sessao ('instalador v' + $script:VERSAO_INSTALADOR + '; aceita pacote de transferencia v' +
        $script:BUNDLE_MINIMO + ' ou superior (' + $script:BundleMinimoDeOnde + ')')
$script:LANCADORES = @('RADIOTERAPIA_AI_LOCAL_SUITE.cmd',
                       'ABRIR_AUTO_CONTORNO.cmd')
$script:PASTA_RT = Join-Path $script:RAIZ_RT $script:PROJETO_RT
$script:PREPARO_SUGERIDO = Join-Path $script:PASTA_RT 'preparo'
# GUARDA: o pacote para levar nao nasce dentro da pasta do programa, que e onde a instalacao direta escreve.
$script:PACOTE_SUGERIDO = Join-Path $env:USERPROFILE 'RadioterapiaAI_pacote'
$script:PastaInstalada = ''

$script:PacoteGB     = 20.0
$script:DownloadGB   = 13.0
$script:DiscoGB      = 42.0
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

function Falhar {
    param([string]$Texto)
    Registrar $Texto 'erro'
    [System.Windows.Forms.MessageBox]::Show(
        $Texto, 'Radioterapia.ai Local Suite - Preparador',
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
$form.Text = 'Radioterapia.ai Local Suite - Preparador'
$form.Size = New-Object System.Drawing.Size(1000, 740)
$form.StartPosition = 'CenterScreen'
$form.BackColor = $script:Cor.Fundo
$form.Font = Fonte 9
$form.MinimumSize = New-Object System.Drawing.Size(900, 640)
$script:IconeDaJanela = 'nenhum: nao achei favicon.ico nem radioterapia_ai.ico em ..\app'
foreach ($n in @('favicon.ico', 'radioterapia_ai.ico')) {
    $ico = Join-Path (Split-Path -Parent $script:AQUI) ('app\' + $n)
    if (-not (Test-Path -LiteralPath $ico)) { continue }
    try {
        $form.Icon = New-Object System.Drawing.Icon($ico)
        $script:IconeDaJanela = $n
        break
    } catch {
        $script:IconeDaJanela = ('recusado: ' + $n + ' (' + $_.Exception.Message + ')')
    }
}
Sessao ('icone da janela: ' + $script:IconeDaJanela)

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
$mMarca.Tag = @{ Palavra = 'Radioterapia'; Sufixo = '.ai Local Suite'
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
    try { AtualizarBotaoLicencas } catch { }
    try { AtualizarDicasDasLicencas } catch { }
    try { AtualizarRota } catch { }
    try { AtualizarSugestaoPasta } catch { }
    try { AtualizarConclusao $script:UltimaConclusao[0] $script:UltimaConclusao[1] } catch { }
    try { $txt1.Text = (TextoDaAba1 $script:Modo) } catch { }
    try { AtualizarRotuloDaPasta } catch { }
    try { PintarEstado } catch { }
    try { PintarVersoes } catch { }
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

function InstalacaoAntigaAchada {
    if (-not $script:Instalado) { return $false }
    return (-not (MarcaDeInstalacao ([string]$script:Instalado.pasta)))
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

$aba0 = NovaAba '0 · O que voce vai fazer'


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
        $script:RotOnde.Text = (T 'Procurei o registro e as pastas com radai_watcher.py em todas as particoes. Se o programa esta noutro lugar, Desinstalar pede a pasta.')
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
function PintarVersoes {
    if (-not $script:RotInstalador -or -not $script:RotAceita) { return }
    $v = $(if ($script:VERSAO_INSTALADOR) { $script:VERSAO_INSTALADOR } else { '?' })
    $m = $(if ($script:BUNDLE_MINIMO) { $script:BUNDLE_MINIMO } else { '?' })
    $script:RotInstalador.Text = ((T 'Instalador v{0}') -f $v)
    $script:RotAceita.Text = ((T 'Aceita pacote de transferencia (bundle) versao {0} ou superior') -f $m)
}
PintarVersoes
$aba0.Controls.Add($rotInstalador)
$aba0.Controls.Add($rotAceita)

$script:Modo = ''
$temInst = [bool]$script:Instalado
$btModo1 = NovoBotao 'Instalar / Atualizar app nesta máquina' 20 128 910 64 $script:Cor.Ok
$btModo1.Font = Fonte 13 'Bold'
$btModo1.FlatAppearance.BorderSize = 2
$btModo1.BackColor = $script:Cor.Ok
$btModo1.ForeColor = $script:Cor.Painel
$btModo3 = NovoBotao 'Máquina offline: instalar de um pacote que eu trouxe' 20 244 445 40 $script:Cor.Titulo
$btModo2 = NovoBotao 'Máquina com internet: montar um pacote para levar para a máquina offline' 485 244 445 40 $script:Cor.Titulo
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
        @($btModo2, 'Baixa tudo e gera um .zip para levar. Nada é instalado nesta máquina.'),
        @($btModo5, 'Mostra o que vai apagar, oferece guardar o que é seu e pede confirmação digitada.'))) {
    $b = $par[0]
    $leg = NovoRotulo $par[1] $b.Left ($b.Bottom + 2) $b.Width 30 8 'Regular' $script:Cor.Fraco
    $aba0.Controls.Add($leg)
    $script:LegendasDaPorta += $leg
}

$rotModo = NovoRotulo '' 330 352 600 40 9 'Regular' $script:Cor.Fraco
if (InstalacaoAntigaAchada) {
    $rotModo.Text = (T 'Achei uma instalacao antiga, sem o entrega.txt. «Instalar / Atualizar app nesta máquina» instala o programa inteiro por cima e mantem a sua configuracao; Desinstalar pede confirmacao antes de completar o que falta.')
} elseif (-not $temInst) {
    $rotModo.Text = (T 'Nao achei instalacao nesta maquina: Instalar / Atualizar vai instalar tudo. Desinstalar fica apagado.')
}
$aba0.Controls.Add($rotModo)

function ModoDireto {
    return ($script:Modo -eq '1' -or $script:Modo -eq '7')
}

function MarcarModo {
    param([string]$Qual)
    if ($Qual -eq '7') {
        $inst = GarantirInstalacao (T 'Aponte a pasta onde o programa esta instalado')
        if (-not $inst) { return }
    }
    $script:Modo = $Qual
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
    if ($Qual -eq '1') {
        $rotModo.Text = (T 'Vai baixar e montar direto na pasta do programa, sem pacote e sem descompactar. Precisa de internet.')
    } elseif ($Qual -eq '2') {
        $rotModo.Text = (T 'Vai baixar tudo e gerar um arquivo para voce levar. Nada sera instalado aqui.')
    } elseif ($Qual -eq '7') {
        $rotModo.Text = (T 'Vai atualizar o app e os modelos direto na pasta instalada. A sua configuracao fica.')
    } else {
        $rotModo.Text = (T 'Nao vai baixar nada. Voce escolhe o arquivo que trouxe, e ele e instalado nesta maquina.')
    }
    AplicarModo
    AtualizarSugestaoPasta
    $abas.SelectedTab = $aba1
}

$btModo2.Add_Click({ MarcarModo '2' })
$btModo3.Add_Click({ MarcarModo '3' })

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

$script:URL_REPOSITORIO = 'https://github.com/radioterapia-ai/local-suite'
$script:URL_PAGINA_VERSOES = $script:URL_REPOSITORIO + '/releases'

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
    $wc = New-Object System.Net.WebClient
    try {
        EsperarSemTravar ($wc.DownloadFileTaskAsync($Url, $Destino)) $LimiteMs
    } finally {
        try { $wc.CancelAsync() } catch { }
        $wc.Dispose()
    }
}

function VersaoPublicada {
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
        if ($tag) {
            $conf.ok = $true
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
        if ($c -eq $script:CaixaLog) { continue }
        if ($c.Visible) { $script:PrepEscondido += $c; $c.Visible = $false }
    }
    $script:CaixaLog.Location = New-Object System.Drawing.Point(20, 20)
    [System.Windows.Forms.Application]::DoEvents()
}

function MostrarPreparo {
    try {
        foreach ($c in $script:PrepEscondido) { $c.Visible = $true }
        $script:PrepEscondido = @()
        $script:CaixaLog.Location = New-Object System.Drawing.Point(20, $script:LogY)
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
    LigarTls12
    foreach ($u in @($script:URLS_DA_REDE)) {
        if (-not $u) { continue }
        $wc = New-Object System.Net.WebClient
        try {
            $wc.Headers['User-Agent'] = 'radioterapia-ai-preparador'
            EsperarSemTravar ($wc.DownloadStringTaskAsync($u)) 8000
            return $true
        } catch {
            if (RespondeuHttp $_.Exception) { return $true }
        } finally {
            try { $wc.CancelAsync() } catch { }
            $wc.Dispose()
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
        BaixarSemTravar ([string]$ins.url) $zip 900000
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
    Registrar ('  A cascata decide sozinha, nesta ordem: o instalador mais novo da release; ' +
               'so o codigo, sem internet, se a impressao de requisitos bate; tudo, com ' +
               'internet, se nao bate; e, sem internet, o pacote que voce trouxe. Nada do ' +
               'que voce configurou e tocado, e o app aberto nesta pasta e encerrado antes ' +
               'de qualquer troca de codigo.')
    $rede = $false
    if ($script:CascataVeioDe) {
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
    if (-not (PerguntarSeProcessando $pasta)) {
        Registrar 'A atualizacao nao aconteceu: o app esta processando e continua aberto.' 'alerta'
        return 'aberto'
    }
    $rc = -1
    while ($true) {
        $rc = RodarAtualizador $pasta @('-SemPerguntar')
        if ($rc -ne 4) { break }
        if (-not (PerguntarSeTentaDeNovo $pasta)) { break }
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
    if (-not $rede) { $rede = HaRede }
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
    if ($script:Ocupado) { return '' }
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
        AvisarAtualizarApp (T 'Esta versão precisa de bibliotecas ou modelos que a instalação não tem, e há internet aqui. O «Instalar / Atualizar app nesta máquina» segue para atualizar tudo na pasta instalada: aceite as licenças e clique em Atualizar tudo. A sua configuração fica.')
        MarcarModo '7'
        return $fim
    }
    if ($fim -eq 'pacote') {
        $r = [string](UltimoDaSaida (AtualizarDePacote $Inst (T 'Sem internet: escolha o .zip de um pacote completo que você trouxe')))
        Registrar ('  pacote trazido: ' + $(if ($r) { $r } else { 'sem resposta' }))
        if ($r -eq 'aberto') {
            Registrar 'A atualizacao nao aconteceu: o app continua aberto nesta pasta.' 'alerta'
            return 'aberto'
        }
        if ($r -eq 'falhou') { return 'erro' }
        if ($r -ne 'feito') {
            Registrar ('CANCELADO: o pacote instalado e incompativel com a v' + $script:VERSAO_INSTALADOR +
                       ', esta maquina esta sem internet e nenhum pacote completo valido foi escolhido. ' +
                       'Nada foi trocado.') 'erro'
            AvisarAtualizarApp ((T 'Atualização cancelada. O pacote instalado nesta máquina (o bundle) é incompatível com a v{0} e impede o uso dela, e aqui não há internet para atualizá-lo. Traga um pacote atualizado, preparado numa máquina com internet por «Máquina com internet: montar um pacote para levar para a máquina offline», e clique de novo em «Instalar / Atualizar app nesta máquina». A instalação atual continua como estava.') -f $script:VERSAO_INSTALADOR) 'Warning'
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
    try { $btModo5.Enabled = [bool]$achada } catch { }
    return $achada
}

function InstalarOuAtualizar {
    if ($script:Ocupado) { return '' }
    $inst = ConferirInstalacao
    if ($inst) {
        Sessao ('Instalar / Atualizar: instalacao achada (' + [string]$inst.como + '); sigo pela cascata do Atualizar app')
        [void](IniciarAtualizarApp $inst)
        return 'atualizar'
    }
    Sessao 'Instalar / Atualizar: nenhuma instalacao achada; sigo para instalar tudo'
    MarcarModo '1'
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
    [void](IniciarAtualizarApp $inst)
}

function ListaDePreservados {
    $preserv = @('radai_watcher.config', '_dados.txt', '_bundle.txt',
                 'calibracao', 'registro', 'radai_status.json',
                 'nomes_proprios.json', 'protocolos_proprios.json')
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
    $offline = ($script:Modo -eq '3')
    SincronizarRota
    if ($null -ne $script:BtRodar) {
        if ($offline) {
            $script:BtRodar.Text = (T 'Instalar a partir do arquivo')
        } elseif ($script:Modo -eq '1') {
            $script:BtRodar.Text = (T 'Instalar agora')
        } elseif ($script:Modo -eq '7') {
            $script:BtRodar.Text = (T 'Atualizar tudo')
        } else {
            $script:BtRodar.Text = (T 'Preparar o pacote')
        }
    }
}

$aba1 = NovaAba '1 · Antes de começar'

$txt1 = NovaCaixaTexto '' 20 20 (920 - 380) 400
$aba1.Controls.Add($txt1)

$pRota = NovoPainel 570 20 350 250
$pRota.Anchor = 'Top,Right'
$pRota.BackColor = [System.Drawing.Color]::FromArgb(11, 22, 38)
$aba1.Controls.Add($pRota)

$rotRotaTit = NovoRotulo 'ESTA MÁQUINA É A ESTAÇÃO DE USO?' 16 14 320 20 9 'Bold' $script:Cor.Titulo
$pRota.Controls.Add($rotRotaTit)
$rotRotaSub = NovoRotulo ('Ou seja: é aqui que os exames serão contornados,' + "`r`n" +
    'no dia a dia?') 16 38 320 34 8 'Regular' $script:Cor.Fraco
$pRota.Controls.Add($rotRotaSub)

$rbSim = New-Object System.Windows.Forms.RadioButton
$rbSim.Text = 'Sim — preparar e já instalar aqui'
$rbSim.Location = New-Object System.Drawing.Point(16, 82)
$rbSim.Size = New-Object System.Drawing.Size(320, 24)
$rbSim.Font = Fonte 9 'Bold'
$rbSim.ForeColor = $script:Cor.Ok
$pRota.Controls.Add($rbSim)
$pRota.Controls.Add((NovoRotulo 'A instalação é feita direto nesta pasta, sem pacote e sem descompactar:' 38 106 300 26 8 'Regular' $script:Cor.Fraco))
$pRota.Controls.Add((NovoRotulo $script:PASTA_RT 38 130 300 18 8 'Bold' $script:Cor.Fraco))

$rbNao = New-Object System.Windows.Forms.RadioButton
$rbNao.Text = 'Não — é máquina de passagem'
$rbNao.Location = New-Object System.Drawing.Point(16, 148)
$rbNao.Size = New-Object System.Drawing.Size(320, 24)
$rbNao.Font = Fonte 9 'Bold'
$rbNao.ForeColor = $script:Cor.Alerta
$pRota.Controls.Add($rbNao)
$pRota.Controls.Add((NovoRotulo ('Só preparo o pacote. Você leva num pendrive' + "`r`n" +
    'e instala na estação depois.') 38 172 300 34 8 'Regular' $script:Cor.Fraco))

$bt1 = NovoBotao 'Entendi — ver as licenças' 20 440 260 38 $script:Cor.Titulo
$bt1.Anchor = 'Bottom,Left'
$bt1.Enabled = $false
$aba1.Controls.Add($bt1)
$rot1 = NovoRotulo 'Responda a pergunta ao lado para continuar.' 292 450 500 20 9 'Regular' $script:Cor.Fraco
$rot1.Anchor = 'Bottom,Left'
$aba1.Controls.Add($rot1)

function AtualizarRota {
    if ($rbSim.Checked)      { $script:EstacaoFinal = $true }
    elseif ($rbNao.Checked)  { $script:EstacaoFinal = $false }
    else                     { $script:EstacaoFinal = $null; return }
    if (-not $script:Modo) {
        if ($rbSim.Checked) { MarcarModo '1' } else { MarcarModo '2' }
        return
    }
    # GUARDA: Sim e a instalacao direta; o modo 2 com EstacaoFinal reabriria montar, zipar e extrair na estacao.
    if ($script:Modo -eq '2' -and $rbSim.Checked) { MarcarModo '1'; return }
    if ($script:Modo -eq '1' -and $rbNao.Checked) { MarcarModo '2'; return }
    $bt1.Enabled = $true
    $rot1.Text = ''
    AtualizarSugestaoPasta
}
$rbSim.Add_CheckedChanged({ AtualizarRota })
$rbNao.Add_CheckedChanged({ AtualizarRota })


function TextoDaAba1 {
    param([string]$Qual)
    if ($Qual -eq '3') {
        return (T @"
Você escolheu INSTALAR UM PACOTE QUE JÁ EXISTE.


O QUE VAI ACONTECER

  1. Você aponta o arquivo do pacote (um .zip de vários GB)
  2. Ele é conferido: o conteúdo, e o aceite de licenças que veio dentro
  3. Você escolhe onde instalar
  4. O programa é copiado, e os atalhos são criados

  Nada é baixado. Esta máquina NÃO precisa de internet.


O QUE ELE NÃO FAZ

  Não mexe no registro do Windows, não pede administrador e não envia nada
  para lugar nenhum. Para remover, use a ferramenta de remoção que fica
  dentro do próprio programa, em Configurações.
"@)
    }
    if ($Qual -eq '1' -or $Qual -eq '7') {
        return ((T @"
Você escolheu INSTALAR OU ATUALIZAR DIRETO NESTA MÁQUINA.


O QUE VAI ACONTECER

  1. Você aceita as licenças: todas de uma vez, ou uma a uma
  2. Você confirma a pasta do programa: a instalação achada, ou uma nova
  3. Os downloads caem direto nessa pasta, conferidos: o Python
     portátil, as bibliotecas e os pesos dos modelos, cerca de {0} GB
  4. Os atalhos e o registro são criados, e o programa fica pronto

  Sem pasta de montagem, sem pacote .zip e sem descompactar. Numa
  instalação que já existe, só o que falta é baixado, e a sua
  configuração, o registro de casos e os logs ficam.


O QUE ELE NÃO FAZ

  Não pede administrador, não mexe no registro do Windows e não envia
  nada para lugar nenhum. Esta máquina precisa de internet.
"@) -f (GBInteiro $script:DownloadGB))
    }
    return ((T @"
Este preparador roda UMA VEZ, nesta máquina, que precisa de internet.


O QUE ELE FAZ

  1. Baixa o Python portátil (não instala nada no Windows)
  2. Baixa as bibliotecas, em versões fixadas — cerca de 2,5 GB
  3. Baixa os pesos de todos os modelos — cerca de {0} GB
  4. Confere o Python e os pesos baixados: SHA-256 onde há soma
     conhecida, tamanho e CRC nos demais
  5. Pede o seu aceite das licenças, item a item
  6. Monta um pacote único, de cerca de {1} GB

  O pacote é sempre o completo: {2} tarefas do TotalSegmentator e {3}
  modelos de comparação, sem versão reduzida para escolher. Ele fica
  maior que o download porque as bibliotecas chegam compactadas e são
  instaladas: o torch sozinho ocupa 4,3 GB depois de instalado.


POR QUE PREPARO E INSTALAÇÃO SÃO SEPARADOS

  A estação de tratamento frequentemente não tem internet. Uma máquina
  com rede prepara; a estação recebe o pacote pronto. Se esta máquina
  for a própria estação, o preparo e a instalação acontecem aqui mesmo
  — é só responder abaixo.

  E há um segundo motivo, de licença: quem baixa os pesos dos modelos
  é você, direto da origem, aceitando os termos de quem os publica.
  Nós não redistribuímos esses arquivos.


O QUE ELE NÃO FAZ

  Não instala nada no Windows, não mexe no registro, não pede
  administrador e não envia nada para lugar nenhum. Tudo que ele produz
  fica na pasta que você escolher no passo 3.
"@) -f (GBInteiro $script:DownloadGB), (GBInteiro $script:PacoteGB),
        $script:NTarefas, $script:NModelos)
}
function SincronizarRota {
    if (ModoDireto) { $rbSim.Checked = $true }
    elseif ($script:Modo -eq '2') { $rbNao.Checked = $true }
    if ($script:Modo -eq '3') {
        $rbSim.Enabled = $false
        $rbNao.Enabled = $false
        $rot1.Text = (T 'Voce escolheu instalar um arquivo ja preparado — esta pergunta nao se aplica.')
        $bt1.Enabled = $true
    } else {
        $rbSim.Enabled = $true
        $rbNao.Enabled = $true
        if ($rbSim.Checked -or $rbNao.Checked) {
            $rot1.Text = ''
            $bt1.Enabled = $true
        } else {
            $rot1.Text = (T 'Responda a pergunta ao lado para continuar.')
            $bt1.Enabled = $false
        }
    }
    if ($script:Modo) {
        $pRota.Visible = $false
        $bt1.Enabled = $true
        $rot1.Text = ''
        $txt1.Text = (TextoDaAba1 $script:Modo)
    } else {
        $pRota.Visible = $true
        $rotRotaTit.Text = (T 'ESTA MÁQUINA É A ESTAÇÃO DE USO?')
        $rotRotaSub.Text = (T 'Ou seja: é aqui que os exames serão contornados, no dia a dia?')
        $txt1.Text = (TextoDaAba1 '')
    }
    LiberarLicencasSeOffline
}

function LiberarLicencasSeOffline {
    if ($null -eq $script:BtLicencas) { return }
    if ($script:Modo -eq '3') {
        $script:BtLicencas.Enabled = $true
        $script:RotLicencas.Text = (T 'Voce trouxe um arquivo ja preparado: o aceite viajou dentro dele. Siga para o passo 3.')
        $script:RotLicencas.ForeColor = $script:Cor.Ok
    } else {
        AtualizarBotaoLicencas
    }
}
$bt1.Add_Click({ $abas.SelectedTab = $aba2 })
$txt1.Text = (TextoDaAba1 $script:Modo)

$aba2 = NovaAba '2 · Licenças'

$aba2.Controls.Add((NovoRotulo 'Aceite todas de uma vez, ou marque uma a uma na lista abaixo. Cada licença aceita fica gravada, uma por uma.' 20 16 900 20 9 'Regular' $script:Cor.Fraco))

$aba2.Controls.Add((NovoRotulo 'A interface está traduzida; o texto das licenças vale no original. Tradução jurídica exige revisão humana, e enquanto não houver uma, o original é o que responde.' 20 34 900 18 8 'Regular' $script:Cor.Alerta))


$rolo2 = New-Object System.Windows.Forms.Panel
$rolo2.Location = New-Object System.Drawing.Point(20, 102)
$rolo2.Size = New-Object System.Drawing.Size(910, 318)
$rolo2.Anchor = 'Top,Left,Right,Bottom'
$rolo2.AutoScroll = $true
$rolo2.BackColor = $script:Cor.Fundo
$rolo2.Add_MouseEnter({ $this.Focus() | Out-Null })
$aba2.Controls.Add($rolo2)
$script:AceiteDeUmaVez = $false
$script:DicaDaLicenca = New-Object System.Windows.Forms.ToolTip
$script:DicaDaLicenca.AutoPopDelay = 20000
$script:LinhasDeLicenca = @()
$btTodas = NovoBotao 'Aceitar todas as licenças e continuar' 20 58 320 36 $script:Cor.Ok
$aba2.Controls.Add($btTodas)

$script:DeclFinalidade = $null
$script:CaixasLicenca = @()
$script:OpcoesLicenca = @()

$script:ColunasDaLicenca = @(
    @{ x = 8;   l = 296; texto = 'Componente do pacote' },
    @{ x = 310; l = 150; texto = 'Licença' },
    @{ x = 466; l = 196; texto = 'O que permite' },
    @{ x = 668; l = 200; texto = 'Origem' })

function AdicionarCabecalhoDasLicencas {
    $h = NovoPainel 0 0 872 22
    $h.BackColor = $script:Cor.Fundo
    foreach ($c in $script:ColunasDaLicenca) {
        $h.Controls.Add((NovoRotulo $c.texto $c.x 3 $c.l 18 8 'Bold' $script:Cor.Fraco))
    }
    $rolo2.Controls.Add($h)
    return 26
}

function TextoDaDicaDaLicenca {
    param([hashtable]$L)
    return ($L.componente + '  ' + $L.versao + "`r`n`r`n" + (T $L.resumo))
}

function AtualizarDicasDasLicencas {
    foreach ($ln in $script:LinhasDeLicenca) {
        try {
            $txt = TextoDaDicaDaLicenca $ln.L
            foreach ($c in $ln.Controles) { $script:DicaDaLicenca.SetToolTip($c, $txt) }
        } catch { }
    }
}

function AdicionarLicenca {
    param([hashtable]$L, [int]$Y)
    $col = $script:ColunasDaLicenca
    $g = $form.CreateGraphics()
    $alturaDoTexto = 0
    foreach ($par in @(@((T $L.componente), (Fonte 8 'Bold'), ($col[0].l - 22)),
                       @([string]$L.licenca, (Fonte 8), $col[1].l),
                       @((T $L.permite), (Fonte 8), $col[2].l),
                       @([string]$L.origem, (Fonte 8), $col[3].l))) {
        $h = [int][Math]::Ceiling($g.MeasureString($par[0], $par[1], [int]$par[2]).Height)
        if ($h -gt $alturaDoTexto) { $alturaDoTexto = $h }
    }
    $g.Dispose()
    $alturaDaLinha = [Math]::Max(44, $alturaDoTexto + 10)
    $altura = $(if ($L.restritiva) { $alturaDaLinha + 44 } else { $alturaDaLinha })
    $alturaDoRotulo = $alturaDaLinha - 6
    $p = NovoPainel 0 $Y 872 $altura
    $p.BackColor = if ($L.restritiva) { [System.Drawing.Color]::FromArgb(28, 22, 8) } else { $script:Cor.Painel }
    $corTit = if ($L.restritiva) { $script:Cor.Alerta } else { $script:Cor.Texto }
    $controles = @()

    if ($L.restritiva) {
        $nome = NovoRotulo $L.componente $col[0].x 4 $col[0].l $alturaDoRotulo 8 'Bold' $corTit
        $p.Controls.Add($nome)
        $controles += $nome
        $rbSim = New-Object System.Windows.Forms.RadioButton
        [void](Registrar-Texto $rbSim 'Sim — vou usar para pesquisa, ensino ou avaliação (recomendado)')
        $rbSim.Location = New-Object System.Drawing.Point(8, $alturaDaLinha)
        $rbSim.Size = New-Object System.Drawing.Size(640, 20)
        $rbSim.Font = Fonte 8 'Bold'
        $rbSim.ForeColor = $script:Cor.Ok
        $rbSim.Tag = $L
        $rbSim.Add_CheckedChanged({ AtualizarBotaoLicencas })
        $p.Controls.Add($rbSim)
        $rbNao = New-Object System.Windows.Forms.RadioButton
        [void](Registrar-Texto $rbNao 'Não — não instalar este modelo')
        $rbNao.Location = New-Object System.Drawing.Point(8, ($alturaDaLinha + 20))
        $rbNao.Size = New-Object System.Drawing.Size(640, 20)
        $rbNao.Font = Fonte 8 'Bold'
        $rbNao.ForeColor = $script:Cor.Fraco
        $rbNao.Tag = $L
        $rbNao.Add_CheckedChanged({ AtualizarBotaoLicencas })
        $p.Controls.Add($rbNao)
        $script:OpcoesLicenca += @{ L = $L; sim = $rbSim; nao = $rbNao }
    } else {
        $cx = New-Object System.Windows.Forms.CheckBox
        [void](Registrar-Texto $cx $L.componente)
        $cx.Location = New-Object System.Drawing.Point($col[0].x, 2)
        $cx.Size = New-Object System.Drawing.Size($col[0].l, ($alturaDaLinha - 4))
        $cx.Font = Fonte 8 'Bold'
        $cx.ForeColor = $corTit
        $cx.BackColor = [System.Drawing.Color]::Transparent
        $cx.CheckAlign = [System.Drawing.ContentAlignment]::MiddleLeft
        $cx.Tag = $L
        $cx.Add_CheckedChanged({ AtualizarBotaoLicencas })
        $p.Controls.Add($cx)
        $script:CaixasLicenca += $cx
        $controles += $cx
    }

    $lic = NovoRotulo $L.licenca $col[1].x 4 $col[1].l $alturaDoRotulo 8 'Regular' $script:Cor.Texto
    $p.Controls.Add($lic)
    $per = New-Object System.Windows.Forms.Label
    [void](Registrar-Texto $per $L.permite)
    $per.Location = New-Object System.Drawing.Point($col[2].x, 4)
    $per.Size = New-Object System.Drawing.Size($col[2].l, $alturaDoRotulo)
    $per.Font = Fonte 8
    $per.ForeColor = $(if ($L.restritiva) { $script:Cor.Alerta } else { $script:Cor.Fraco })
    $per.BackColor = [System.Drawing.Color]::Transparent
    $p.Controls.Add($per)

    $lnk = New-Object System.Windows.Forms.LinkLabel
    $lnk.Text = $L.origem
    $lnk.Location = New-Object System.Drawing.Point($col[3].x, 4)
    $lnk.Size = New-Object System.Drawing.Size($col[3].l, $alturaDoRotulo)
    $lnk.Font = Fonte 8
    $lnk.LinkColor = $script:Cor.Titulo
    $lnk.ActiveLinkColor = $script:Cor.Ok
    $lnk.VisitedLinkColor = $script:Cor.Titulo
    $lnk.BackColor = [System.Drawing.Color]::Transparent
    $lnk.Tag = $(if ($L.url) { $L.url } else { 'https://' + $L.origem })
    $lnk.Add_LinkClicked({
        param($sender, $e)
        try { Start-Process $sender.Tag } catch { }
    })
    $p.Controls.Add($lnk)
    $controles += @($lic, $per, $lnk)
    $script:LinhasDeLicenca += @{ L = $L; Controles = $controles; Painel = $p }
    $rolo2.Controls.Add($p)
    return ($Y + $altura + 4)
}

$bt2 = NovoBotao 'Continuar e escolher a pasta' 20 440 290 38 $script:Cor.Ok
$bt2.Anchor = 'Bottom,Left'
$bt2.Enabled = $false
$aba2.Controls.Add($bt2)
$rot2b = NovoRotulo '' 322 450 600 20 9 'Regular' $script:Cor.Fraco
$script:BtLicencas = $bt2
$script:RotLicencas = $rot2b
$rot2b.Anchor = 'Bottom,Left'
$aba2.Controls.Add($rot2b)

function FinalidadeDeclarada {
    if (-not $script:OpcoesLicenca) { return $null }
    if ($null -eq $script:DeclFinalidade) { return $null }
    return $script:DeclFinalidade.SelectedIndex
}

function AplicarFinalidade {
    $i = FinalidadeDeclarada
    if ($null -eq $i) { return }
    foreach ($o in $script:OpcoesLicenca) {
        if ($i -eq 1) {
            $o.sim.Enabled = $true
            $o.sim.Checked = $true
        } elseif ($i -eq 2) {
            $o.nao.Checked = $true
            $o.sim.Enabled = $false
        } else {
            $o.sim.Enabled = $true
        }
    }
    AtualizarBotaoLicencas
}

function AtualizarBotaoLicencas {
    if ($script:Modo -eq '3') { LiberarLicencasSeOffline; return }
    $faltam = @($script:CaixasLicenca | Where-Object { -not $_.Checked })
    $semResposta = @($script:OpcoesLicenca |
                     Where-Object { -not ($_.sim.Checked -or $_.nao.Checked) })
    $bt2.Enabled = (($faltam.Count -eq 0) -and ($semResposta.Count -eq 0))
    if ($faltam.Count -gt 0) {
        $rot2b.Text = (T 'Faltam {0} licença(s). Sem aceitar todas, o pacote não é montado.') -f $faltam.Count
        $rot2b.ForeColor = $script:Cor.Alerta
    } elseif ($semResposta.Count -gt 0) {
        $rot2b.Text = (T 'Responda sim ou não para os {0} modelo(s) de uso restrito.') -f $semResposta.Count
        $rot2b.ForeColor = $script:Cor.Alerta
    } else {
        $n = @($script:OpcoesLicenca).Count
        if ($n -eq 0) {
            $rot2b.Text = (T 'Nenhum componente de uso restrito neste pacote.')
        } else {
            $fora = @($script:OpcoesLicenca | Where-Object { $_.nao.Checked })
            if ($fora.Count -eq 0) {
                $rot2b.Text = (T 'Tudo respondido. {0} modelo(s) de uso restrito entram no pacote.') -f $n
            } elseif ($fora.Count -eq $n) {
                $rot2b.Text = (T 'Tudo respondido. Nenhum modelo de uso restrito será instalado.')
            } else {
                $rot2b.Text = (T 'Tudo respondido. {0} modelo(s) de uso restrito ficam de fora.') -f $fora.Count
            }
        }
        $rot2b.ForeColor = $script:Cor.Ok
    }
}
$bt2.Add_Click({ $abas.SelectedTab = $aba3 })

function AceitarTodasAsLicencas {
    # GUARDA: as caixas ficam marcadas NA TELA antes de seguir; o aceite
    # continua gravado uma licenca por linha no LICENCAS_ACEITAS.txt.
    foreach ($cx in $script:CaixasLicenca) { $cx.Checked = $true }
    $script:AceiteDeUmaVez = $true
    AtualizarBotaoLicencas
    $semResposta = @($script:OpcoesLicenca |
                     Where-Object { -not ($_.sim.Checked -or $_.nao.Checked) })
    if ($semResposta.Count -gt 0) {
        try {
            $rolo2.ScrollControlIntoView($semResposta[0].sim)
            $semResposta[0].sim.Focus() | Out-Null
        } catch { }
        return
    }
    try { $rolo2.Refresh() } catch { }
    $relogio = [System.Diagnostics.Stopwatch]::StartNew()
    while ($relogio.ElapsedMilliseconds -lt 600) { Start-Sleep -Milliseconds 50; Pump }
    $abas.SelectedTab = $aba3
}
$btTodas.Add_Click({ AceitarTodasAsLicencas })

$aba3 = NovaAba '3 · Preparar'

$script:RotuloPasta = NovoRotulo '' 20 18 700 20 9 'Bold' $script:Cor.Texto
$aba3.Controls.Add($script:RotuloPasta)
function AtualizarRotuloDaPasta {
    if (ModoDireto) {
        $script:RotuloPasta.Text = ((T 'Pasta do programa: instala direto aqui (precisa de cerca de {0} GB livres):') -f
                                    (GBnecessariosDireto ''))
    } else {
        $script:RotuloPasta.Text = ((T 'Pasta de trabalho (precisa de cerca de {0} GB livres):') -f
                                    (GBnecessarios))
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
    $d.Description = 'Onde montar o pacote'
    $d.ShowNewFolderButton = $true
    if (Test-Path -LiteralPath $cxPasta.Text) { $d.SelectedPath = $cxPasta.Text }
    if ($d.ShowDialog() -eq 'OK') { $cxPasta.Text = $d.SelectedPath }
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
        $cxPasta.Text = $script:PACOTE_SUGERIDO
        $rotPasta.Text = 'Máquina de passagem: o preparo fica no seu perfil, e o pacote sai daí para o pendrive. ' +
                         'Nada é criado em ' + $script:RAIZ_RT + ' nesta máquina.'
        $rotPasta.ForeColor = $script:Cor.Fraco
    }
}

$btRodar = NovoBotao 'Preparar o pacote' 20 116 220 36 $script:Cor.Ok
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

$btParar = NovoBotao 'Cancelar' 250 116 130 36 $script:Cor.Critico
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
$script:CaixaLog.Size = New-Object System.Drawing.Size(910, 274)
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
    if ($script:Modo -eq '3') {
        InstalarDeArquivo
        return
    }
    if (-not $script:Modo) {
        [System.Windows.Forms.MessageBox]::Show(
            (T 'Escolha primeiro o que voce vai fazer.'),
            (T '0 · O que voce vai fazer'), 'OK', 'Warning') | Out-Null
        $abas.SelectedTab = $aba0
        return
    }
    $faltam = @($script:CaixasLicenca | Where-Object { -not $_.Checked })
    if ($faltam.Count -gt 0) {
        [System.Windows.Forms.MessageBox]::Show(
            ((T 'Faltam {0} licença(s). Sem aceitar todas, o pacote não é montado.') -f $faltam.Count),
            (T '2 · Licenças'),
            'OK', 'Warning') | Out-Null
        $abas.SelectedTab = $aba2
        try {
            $rolo2.ScrollControlIntoView($faltam[0])
            $faltam[0].Focus() | Out-Null
        } catch { }
        return
    }
    if (-not (VersaoDeixaPreparar)) { return }
    Preparar
})

$aba4 = NovaAba '4 · Conclusão'

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

function LinhaDeArgumentos {
    param([string[]]$Lista)
    return (($Lista | ForEach-Object {
        '"' + ([string]$_ -replace '(\\+)$', '$1$1') + '"' }) -join ' ')
}

function AtualizarConclusao {
    param([string]$Pasta, [string]$Zip)
    $script:UltimaConclusao = @($Pasta, $Zip)
    if (-not $Pasta) {
        $txt4.Text = (T @"
Esta tela se preenche quando o preparo terminar.

Ela vai dizer o que fazer com o pacote — e o que ela diz depende da
resposta que você deu no passo 1: se esta é a estação de uso, ou se é
uma máquina de passagem.
"@)
        return
    }

    $comum = (T @"

O REGISTRO, PARA GUARDAR

  Dentro do pacote há dois arquivos que valem guardar junto da
  documentação do serviço:

    LICENÇAS_ACEITAS.txt   o que você aceitou, quando e em qual máquina
    MANIFESTO.txt          cada componente: versão, origem e SHA-256

  O MANIFESTO responde "qual versão está instalada" — e é ele que se
  guarda quando alguém perguntar o que exatamente estava rodando numa
  data. Ele traz versão, origem e SHA-256 de cada componente.


  Ferramenta de apoio. Não validada para uso clínico. Toda estrutura
  gerada sai como sugestão não aprovada: revisar e aprovar continua
  sendo ato médico, no sistema de planejamento.
"@)

    if ((Test-Path variable:script:AtualizouSoCodigo) -and $script:AtualizouSoCodigo) {
        $como = [string]$script:AtualizouSoCodigo[0]
        $de = [string]$script:AtualizouSoCodigo[1]
        if (-not $de) { $de = '?' }
        $para = [string]$script:AtualizouSoCodigo[2]
        $tit4 = $(if ($como -eq 'pacote') { T 'PRONTO — ATUALIZADO A PARTIR DO PACOTE QUE VOCÊ TROUXE' }
                  else { T 'PRONTO — APP ATUALIZADO NESTA MÁQUINA' })
        $como4 = $(if ($como -eq 'pacote') { T 'O pacote que você trouxe foi instalado por cima, sem internet.' }
                   else { T 'A impressão de requisitos bateu: só o código foi trocado, sem internet e sem baixar nada.' })
        $txt4.Text = $tit4 + "`r`n`r`n  " + $como4 + "`r`n`r`n  " +
            ((T 'Versão anterior: {0}. Versão instalada: {1}.') -f $de, $para) + "`r`n`r`n  " +
            (T 'O programa está em') + "`r`n`r`n      " + $script:PastaInstalada + "`r`n`r`n  " +
            (T 'A sua configuração, o registro de casos e os logs ficaram como estavam. Os atalhos da área de trabalho e do menu Iniciar foram refeitos.') +
            "`r`n`r`n  " + (T 'O botão verde abaixo fecha este instalador e abre o app.') +
            "`r`n`r`n`r`n  " + (T 'Ferramenta de apoio. Não validada para uso clínico.')
    } elseif ($script:Modo -eq '3') {
        $txt4.Text = @"
PRONTO — INSTALADO A PARTIR DO ARQUIVO QUE VOCÊ TROUXE

  Não há nada para levar: o pacote que você apontou já foi instalado
  nesta máquina.$(if ($script:ResultadoModo3) { "`r`n`r`n  " + $script:ResultadoModo3 })

  O programa está em

      $(if ($script:PastaInstalada) { $script:PastaInstalada } else { $script:PASTA_RT })

  Abra pelo botão abaixo, ou pelo atalho "Radioterapia.ai Local Suite"
  na área de trabalho e no menu Iniciar.


PRIMEIRO USO

  1. A tela inicial pede o idioma e o aceite dos termos.
  2. Logo depois, o primeiro uso pede a pasta favorita, que é
     opcional. A pasta que o turno varre se escolhe no ContourLab, em
     Rodar agora, Incluir Overnight Run: sem ela o vigia não varre
     nada. Os anéis saem no padrão Eclipse / Monaco; para Xio / Focal,
     Configurações, Geral.


  Ferramenta de apoio. Não validada para uso clínico. Toda estrutura
  gerada sai como sugestão não aprovada: revisar e aprovar continua
  sendo ato médico, no sistema de planejamento.
"@
    } elseif (ModoDireto) {
        $onde4 = $(if ($script:PastaInstalada) { $script:PastaInstalada } else { $script:PASTA_RT })
        $titulo4 = (T 'PRONTO — INSTALADO DIRETO NESTA MÁQUINA')
        $txt4.Text = $titulo4 + "`r`n`r`n  " + (T 'O programa está em') + "`r`n`r`n      " + $onde4 + "`r`n`r`n" + (T @"
  Sem pacote e sem descompactar: tudo foi baixado e montado na pasta
  final. A sua configuração, o registro de casos e os logs que já
  existiam ali ficaram como estavam.

  Abra pelo botão abaixo, ou pelo atalho "Radioterapia.ai Local Suite"
  na área de trabalho e no menu Iniciar.


PRIMEIRO USO

  1. A tela inicial pede o aceite dos termos.
  2. Logo depois, o primeiro uso pede a pasta favorita, que é opcional.
     A pasta que o turno varre se escolhe no ContourLab, em Rodar agora,
     Incluir Overnight Run. Os anéis saem no padrão Eclipse / Monaco;
     para Xio / Focal, Configurações, Geral.
  3. Em Configurações, Diagnósticos e Registros, clique em Diagnosticar:
     tem de dar 0 faltando.


O REGISTRO, PARA GUARDAR

  Na pasta do programa ficam o LICENCAS_ACEITAS.txt (o que você aceitou,
  quando e em qual máquina) e o MANIFESTO.txt (cada componente: versão,
  origem e soma). São eles que respondem "o que estava instalado".


  Ferramenta de apoio. Não validada para uso clínico.
"@)
    } elseif ($script:EstacaoFinal -eq $true) {
        $txt4.Text = @"
PRONTO — E ESTA É A ESTAÇÃO DE USO

  Você respondeu, no passo 1, que os exames serão contornados nesta
  máquina. Então acabou: não há nada para copiar e nada para levar.

  O programa está instalado em

      $(if ($script:PastaInstalada) { $script:PastaInstalada } else { $script:PASTA_RT })

  Abra pelo botão abaixo, ou pelo atalho "Radioterapia.ai Local
  Suite" na área de trabalho e no menu Iniciar.


PRIMEIRO USO

  1. A tela inicial pede o idioma e o aceite dos termos — os cartões
     só aparecem depois dele
  2. Logo depois, o primeiro uso pede a pasta favorita, que é
     opcional. A pasta que o turno varre se escolhe no ContourLab, em
     Rodar agora, Incluir Overnight Run: sem ela o vigia não varre
     nada. Os anéis saem no padrão Eclipse / Monaco; para Xio / Focal,
     Configurações, Geral
  3. Em Configurações, Diagnósticos e Registros, clique em
     Diagnosticar: tem de dar 0 faltando


SE PRECISAR INSTALAR EM OUTRA ESTAÇÃO DEPOIS

  O pacote continua na pasta de trabalho que você escolheu no passo 3,
  numa subpasta com o nome do projeto e a versão:

      $(NomeDoArquivo $Zip)

  Copie esse arquivo para a outra máquina, extraia e clique em
  INSTALL.cmd. Ele não precisa de internet nem de administrador.
$comum
"@
    } elseif (-not $Zip) {
        $txt4.Text = @"
PRONTO — MAS NAO CONSEGUI APONTAR O ARQUIVO

  O preparo terminou bem e o pacote foi conferido. O que falhou foi
  localizar o arquivo depois, para escrever o nome dele aqui.

  Ele esta embaixo da pasta de trabalho que voce escolheu no passo 3,
  numa subpasta com o nome do projeto e a versao. Procure pelo .zip
  maior que 1 GB: e ele.

  O log completo e o arquivo $(NomeDoArquivo $script:ArquivoLog), na mesma
  pasta de trabalho.
$comum
"@
    } else {
        $nomeZip = NomeDoArquivo $Zip
        $txt4.Text = @"
PRONTO — AGORA LEVE PARA A ESTAÇÃO

  Você respondeu, no passo 1, que esta é uma máquina de passagem. O
  pacote está montado e é isto que você leva:

      $nomeZip

  Ele está na pasta de trabalho que você escolheu no passo 3, numa
  subpasta com o nome do projeto e a versão. O botão "Abrir a pasta do
  pacote", abaixo, abre essa pasta com o arquivo já selecionado.


NA ESTAÇÃO — LEVE DOIS ARQUIVOS

  1. O pacote que acabou de sair:

         $nomeZip

  2. E o instalador, este mesmo que você está usando agora:

         RADIOTERAPIA_AI_LOCAL_SUITE_SETUP_LATEST.zip

  Na estação, abra o SETUP (o segundo). Ele pergunta o que fazer:
  escolha "Máquina offline: instalar de um pacote que eu trouxe", aponte o pacote, e
  escolha a pasta onde quer instalar.

  O pacote é carga: não abra, não clique nele. Quem faz tudo é o
  instalador, e ele é o único arquivo que você clica — aqui e lá.

  A estação NÃO precisa de internet e NÃO precisa de administrador.


SE OS SCRIPTS ESTIVEREM BLOQUEADOS NA ESTAÇÃO

  Algumas estações bloqueiam a execução de scripts. O INSTALL.cmd já
  pede a liberação apenas para o próprio processo, sem alterar a
  máquina — o que costuma bastar.

  Se ainda assim for bloqueado, a instalação vira uma cópia de pasta, e
  não precisa de script nenhum:

  1. Extraia o .zip
  2. Copie a pasta $($script:PROJETO_RT) de dentro dele para

         $($script:PASTA_RT)

     (crie as pastas se não existirem — isso não precisa de
     administrador)
  3. Dentro dela, dois cliques em

         $($script:LANCADORES[0])

     É esse o arquivo que abre o programa. Ele sobe o painel no
     navegador, em http://127.0.0.1:8777/

  4. Para ter o atalho na área de trabalho, clique com o botão direito
     nesse arquivo e escolha "Enviar para → Área de trabalho"

  Se preferir pedir liberação ao TI, o pedido que costuma passar não é
  "liberar scripts na máquina" — é liberar a pasta $($script:RAIZ_RT)
  para o usuário. É um escopo pequeno, de uma pasta que só existe para
  receber estes aplicativos.
$comum
"@
    }
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
    $l = New-Object System.Collections.Generic.List[string]
    $l.Add('LICENCAS ACEITAS')
    $l.Add('================================================================')
    $l.Add('')
    $l.Add('Este arquivo e a evidencia do aceite. Ele foi gravado no momento')
    $l.Add('da preparacao do pacote e viaja dentro dele; o instalador o exibe')
    $l.Add('de novo na estacao antes de instalar.')
    $l.Add('')
    $l.Add('Preparado por ....: ' + $env:USERNAME)
    $l.Add('Maquina ..........: ' + $env:COMPUTERNAME)
    $l.Add('Data e hora ......: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
    $l.Add('Preparador versao : ' + $script:VERSAO)
    $l.Add('Estacao de uso ...: ' + $(if ($script:EstacaoFinal) { 'sim - preparado e instalado nesta maquina' } else { 'nao - maquina de passagem' }))
    $deUmaVez = [bool](Get-Variable -Name AceiteDeUmaVez -Scope Script -ValueOnly -ErrorAction SilentlyContinue)
    $l.Add('Forma do aceite ..: ' + $(if ($deUmaVez) { 'todas de uma vez (botao Aceitar todas); cada licenca registrada abaixo' } else { 'uma a uma, na lista' }))
    $l.Add('')
    $l.Add('----------------------------------------------------------------')
    $l.Add('')
    $i = FinalidadeDeclarada
    if ($null -ne $i) {
        $decl = switch ($i) {
            1 { 'pesquisa, ensino ou avaliacao' }
            2 { 'outros casos - os modelos de uso restrito nao foram instalados' }
            default { 'NAO DECLARADA' }
        }
        $l.Add('FINALIDADE DE USO DECLARADA: ' + $decl)
        $l.Add('')
        $l.Add('----------------------------------------------------------------')
        $l.Add('')
    }
    foreach ($cx in $script:CaixasLicenca) {
        $t = $cx.Tag
        $marca = if ($cx.Checked) { '[ACEITA]  ' } else { '[RECUSADA]' }
        $l.Add($marca + ' ' + $t.componente)
        $l.Add('           versao ..: ' + $t.versao)
        $l.Add('           licenca .: ' + $t.licenca)
        $l.Add('           origem ..: ' + $t.origem)
        $l.Add('')
    }
    foreach ($o in $script:OpcoesLicenca) {
        $t = $o.L
        $marca = if ($o.sim.Checked) { '[ACEITA]  ' }
                 elseif ($o.nao.Checked) { '[DISPENSADO]' }
                 else { '[RECUSADA]' }
        $l.Add($marca + ' ' + $t.componente)
        $l.Add('           versao ..: ' + $t.versao)
        $l.Add('           licenca .: ' + $t.licenca)
        $l.Add('           origem ..: ' + $t.origem)
        $l.Add('           ATENCAO .: licenca com RESTRICAO DE USO')
        if ($o.nao.Checked) {
            $l.Add('           ESCOLHA .: nao instalar - o conjunto de estudo')
            $l.Add('                      deste modelo nao sera entregue')
        }
        $l.Add('')
    }
    $l.Add('----------------------------------------------------------------')
    $l.Add('')
    $l.Add('Os componentes obrigatorios precisam de aceite: sem eles nada e')
    $l.Add('montado e nada e instalado. Os dois modelos de USO RESTRITO sao')
    $l.Add('opcionais - dispensa-los tira o conjunto de estudo deles da')
    $l.Add('entrega, e a decisao pode ser mudada depois nas configuracoes.')
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
    param([string]$Pasta)
    foreach ($nome in @('python', 'py')) {
        try {
            $c = Get-Command $nome -ErrorAction Stop
            $v = & $c.Source -c "import sys;print('%d.%d'%sys.version_info[:2])" 2>$null
            if ($v -and [version]$v -ge [version]'3.9') {
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
          $Coletar = $null)
    $saida = $Proc.StandardOutput
    $erro  = $Proc.StandardError
    $tSaida = $saida.ReadLineAsync()
    $tErro  = $erro.ReadLineAsync()
    $fimSaida = $false
    $fimErro  = $false
    while (-not ($fimSaida -and $fimErro)) {
        $andou = $false
        if (-not $fimSaida -and $tSaida.IsCompleted) {
            $l = $tSaida.Result
            if ($null -eq $l) { $fimSaida = $true }
            else {
                Registrar ('  ' + $l)
                if ($null -ne $Coletar) { [void]$Coletar.Add($l) }
                $tSaida = $saida.ReadLineAsync()
                $andou = $true
            }
        }
        if (-not $fimErro -and $tErro.IsCompleted) {
            $l = $tErro.Result
            if ($null -eq $l) { $fimErro = $true }
            else {
                Registrar ('  ' + $l) 'erro'
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

function Preparar {
    if ($script:Ocupado) { return }
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
        $script:ArquivoLog = Join-Path $trab 'preparar_log.txt'

        Registrar '=== Radioterapia.ai Local Suite - preparador ===' 'titulo'
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
        $precisoGB = GBnecessarios
        if ($direto) { $precisoGB = GBnecessariosDireto $trab }
        $metade = GBInteiro $script:PacoteGB
        if ($direto) {
            Registrar ('espaco necessario: ' + $precisoGB +
                       ' GB (o programa montado direto na pasta final, sem .zip)')
        } else {
            Registrar ('espaco necessario: ' + $precisoGB +
                       ' GB (' + $metade + ' de montagem + ' + $metade +
                       ' do .zip, e o resto de folga)')
        }
        Registrar ('  tamanho do pacote de: ' + $script:TamanhoDeOnde)
        if ($livre -lt ($precisoGB * 1GB)) {
            Falhar ('Espaco insuficiente em ' + $unidade + ': ha ' +
                    [math]::Round($livre / 1GB, 1) + ' GB e sao necessarios cerca de ' +
                    $precisoGB + ' GB.' + [char]10 + [char]10 +
                    'A montagem intermediaria ocupa cerca de ' + $metade +
                    ' GB e o pacote final, outros ' + $metade + ' GB.')
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
        $py = AcharOuBaixarPython $pyDir
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

        Registrar ('  Pacote COMPLETO: runtime, ' + $script:NTarefas +
                   ' tarefas do TotalSegmentator e ' + $script:NModelos +
                   ' modelos de comparacao (~' + (GBInteiro $script:PacoteGB) +
                   ' GB). Nao ha versao reduzida.')
        Registrar ''

        $argumentos = @($motor, '--preparo', $trab)
        if ($direto) {
            $argumentos = @($motor, '--instalar', $trab)
        }
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
        if ($zip) { $script:PacoteFinal = $zip.FullName }
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
                  frase = ((T 'Nao consegui ler a versao deste pacote ({0}), e sem ela nao da para saber se este instalador o aceita. Monte um pacote novo com "Máquina com internet: montar um pacote para levar para a máquina offline".') -f
                           $(if ($Erro) { $Erro } else { 'VERSAO ausente' })) }
    }
    if ($Minimo -and (MaisNovaQue $Minimo $Pacote)) {
        return @{ acao = 'recusa'
                  frase = ((T 'Este pacote e da versao {0}; este instalador aceita pacote de transferencia da versao {1} ou superior. Monte um pacote novo com "Máquina com internet: montar um pacote para levar para a máquina offline".') -f
                           $Pacote, $Minimo) }
    }
    if ($Instalador -and (MaisNovaQue $Instalador $Pacote)) {
        return @{ acao = 'instala_e_atualiza'; frase = '' }
    }
    return @{ acao = 'instala'; frase = '' }
}

function AplicarCodigoPorCima {
    param([string]$VersaoPacote)
    $vY = $script:VERSAO_INSTALADOR
    if (-not $script:PastaInstalada) {
        $script:ResultadoModo3 = ('ATENÇÃO: a instalação do pacote v' + $VersaoPacote +
            ' não completou, e o código da v' + $vY + ' não foi aplicado. Veja o log.')
        Registrar ('  a instalacao do pacote v' + $VersaoPacote + ' nao completou; ' +
                   'o codigo da v' + $vY + ' nao foi aplicado') 'alerta'
        return
    }
    $vInst = VersaoDaPasta $script:PastaInstalada
    $naDoPacote = [bool]$vInst -and -not (MaisNovaQue $vInst $VersaoPacote) -and
                  -not (MaisNovaQue $VersaoPacote $vInst)
    if (-not $naDoPacote) {
        $vZ = $(if ($vInst) { 'v' + $vInst } else { 'versao desconhecida' })
        $tZ = $(if ($vInst) { 'v' + $vInst } else { 'versão desconhecida' })
        $jaNova = [bool]$vInst -and -not (MaisNovaQue $vY $vInst)
        $script:ResultadoModo3 = ('ATENÇÃO: o pacote v' + $VersaoPacote +
            ' não chegou à pasta instalada, que está na ' + $tZ +
            $(if ($jaNova) { ' (o instalador não retrocede uma instalação mais nova sem confirmação)' } else { '' }) +
            '. O código da v' + $vY + ' não foi aplicado por cima. Veja o log.')
        if ($jaNova) {
            Registrar ('  a pasta instalada ja esta na v' + $vInst + ': o pacote v' + $VersaoPacote +
                       ' nao chegou a ela, e nao ha codigo a aplicar por cima') 'alerta'
        } else {
            Registrar ('  a pasta instalada esta na ' + $vZ + ', e nao na v' + $VersaoPacote +
                       ' do pacote: o pacote nao chegou a ela, e o codigo da v' + $vY +
                       ' NAO foi aplicado (seria codigo novo sobre um runtime que nao e o do pacote)') 'alerta'
        }
        return
    }
    $ps = Join-Path $script:AQUI 'UPDATE.ps1'
    if (-not (Test-Path -LiteralPath $ps)) {
        $script:ResultadoModo3 = ('ATENÇÃO: o que está instalado é o pacote v' + $VersaoPacote +
            ', SEM o código da v' + $vY + ' -- não achei o UPDATE.ps1 ao lado do instalador.')
        Registrar ('  Nao achei o UPDATE.ps1 ao lado deste arquivo. O pacote v' + $VersaoPacote +
                   ' ficou instalado, SEM o codigo da v' + $vY + '.') 'erro'
        return
    }
    Registrar ''
    Registrar ('APLICANDO O CODIGO DA v' + $vY + ' POR CIMA DO PACOTE v' + $VersaoPacote) 'titulo'
    Registrar ('  o mesmo caminho do "Instalar / Atualizar app" quando a impressao bate: copia so o ' +
               'codigo, sem internet; configuracao, calibracao, registro e logs ficam')
    $psiA = New-Object System.Diagnostics.ProcessStartInfo
    $psiA.FileName = 'powershell.exe'
    $destA = ([string]$script:PastaInstalada).TrimEnd('\')
    $psiA.Arguments = ('-NoProfile -ExecutionPolicy Bypass -File "' + $ps +
                       '" -Destino "' + $destA + '" -SemPerguntar')
    $psiA.UseShellExecute = $false
    $psiA.RedirectStandardOutput = $true
    $psiA.RedirectStandardError = $true
    $psiA.CreateNoWindow = $true
    $prA = [System.Diagnostics.Process]::Start($psiA)
    $rcA = AcompanharProcesso $prA
    Registrar ''
    if ($rcA -eq 0) {
        $script:ResultadoModo3 = ('O pacote era da v' + $VersaoPacote + '; o código da v' + $vY +
                                  ' foi aplicado por cima dele.')
        Registrar ('pacote v' + $VersaoPacote + ' instalado e codigo atualizado para v' + $vY) 'ok'
        $script:Instalado = AcharInstalacao
        try { PintarEstado } catch { }
    } elseif ($rcA -eq 3) {
        $script:ResultadoModo3 = ('ATENÇÃO: o pacote é da v' + $VersaoPacote + ' e NÃO serve a esta ' +
            'versão (as bibliotecas ou os pesos mudaram). O que está instalado é a v' +
            $VersaoPacote + ', sem o código da v' + $vY + '. Monte um pacote novo com ' +
            '"Máquina com internet: montar um pacote para levar para a máquina offline".')
        Registrar ('O PACOTE v' + $VersaoPacote + ' NAO SERVE A ESTA VERSAO: as bibliotecas ou os ' +
                   'pesos mudaram (veja acima). Monte um pacote novo com "Maquina com internet: ' +
                   'montar um pacote para levar para a maquina offline". O que ficou instalado e a v' + $VersaoPacote +
                   ', sem o codigo da v' + $vY + '.') 'alerta'
    } else {
        $script:ResultadoModo3 = ('ATENÇÃO: o pacote v' + $VersaoPacote + ' foi instalado, mas o ' +
            'código da v' + $vY + ' não foi aplicado (código ' + $rcA + '). Veja o log.')
        Registrar ('O codigo da v' + $vY + ' nao foi aplicado (codigo ' + $rcA + '). O que ' +
                   'ficou instalado e o pacote v' + $VersaoPacote + '.') 'erro'
    }
}

function InstalarDeArquivo {
    $script:ResultadoModo3 = ''
    $dlg = New-Object System.Windows.Forms.OpenFileDialog
    $dlg.Title  = (T 'Escolha o arquivo que voce trouxe')
    $dlg.Filter = (T 'Pacote do Radioterapia.ai') + ' (*.zip)|*RADIOTERAPIA_AI*.zip;*AUTO_CONTORNO*.zip|' + (T 'Qualquer arquivo .zip') + ' (*.zip)|*.zip|' + (T 'Todos os arquivos') + ' (*.*)|*.*'
    $dlg.CheckFileExists = $true
    if ($dlg.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { return }
    $zip = $dlg.FileName
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
            (T 'Esse .zip nao tem o INSTALL.ps1 na raiz, entao ele nao e um pacote deste programa. Escolha o arquivo gerado por "Máquina com internet: montar um pacote para levar para a máquina offline".'),
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
            Registrar ('  o pacote e mais antigo que este instalador: depois de instala-lo, ' +
                       'o codigo da v' + $script:VERSAO_INSTALADOR + ' vai por cima')
        }
        try { AnotarPastaDoOperador $raizEscolhida '<pasta de destino>' } catch { }
        InstalarAqui $zip $raizEscolhida
        if ($dec.acao -eq 'instala_e_atualiza') { AplicarCodigoPorCima $vz.versao }
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
            (T 'Esse .zip nao tem o INSTALL.ps1 na raiz, entao ele nao e um pacote deste programa. Escolha o arquivo gerado por "Máquina com internet: montar um pacote para levar para a máquina offline".'),
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
            if ($dec.acao -eq 'instala_e_atualiza') { AplicarCodigoPorCima $vz.versao }
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
    }
    return $res
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
                $destino = Join-Path $tmp $ent.FullName
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
        $ps1 = Join-Path $tmp 'INSTALL.ps1'
        if (-not (Test-Path -LiteralPath $ps1)) {
            Registrar '  o pacote nao trouxe INSTALL.ps1 - instale a mao' 'alerta'
            return
        }
        Registrar '  rodando o instalador...'
        $env:RADAI_PASTA_PACOTE = $tmp
        $env:RADAI_LICENCAS_ACEITAS = 'S'
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
        $arqSaida = Join-Path $tmp '_instalador_saida.txt'
        $cmdFilho = ('[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false); ' +
                     "Get-Content -LiteralPath '$ps1' -Raw -Encoding UTF8 | Invoke-Expression")
        $saida = @()
        try {
            $pIns = Start-Process -FilePath 'powershell' -ArgumentList @(
                        '-NoProfile', '-ExecutionPolicy', 'Bypass',
                        '-Command', $cmdFilho) `
                    -RedirectStandardOutput $arqSaida -NoNewWindow -PassThru
            try { $null = $pIns.Handle } catch { }
            $lidas = 0
            while (-not $pIns.HasExited) {
                Start-Sleep -Milliseconds 120
                Pump
                try {
                    if (Test-Path -LiteralPath $arqSaida) {
                        $tudo = @(Get-Content -LiteralPath $arqSaida -Encoding UTF8 -ErrorAction SilentlyContinue)
                        while ($lidas -lt $tudo.Count) {
                            Registrar ('    ' + $tudo[$lidas]); $lidas++
                        }
                    }
                } catch { }
            }
            $pIns.WaitForExit()
            Pump
            try {
                $tudo = @(Get-Content -LiteralPath $arqSaida -Encoding UTF8 -ErrorAction SilentlyContinue)
                while ($lidas -lt $tudo.Count) {
                    Registrar ('    ' + $tudo[$lidas]); $lidas++
                }
            } catch { }
        } catch {
            Registrar ('  nao consegui rodar em processo proprio (' +
                       $_.Exception.Message + ') - a janela vai congelar') 'alerta'
            $saida = & powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-Content -LiteralPath '$ps1' -Raw -Encoding UTF8 | Invoke-Expression" 2>&1
        }
        $env:RADAI_RAIZ_INSTALACAO = $null
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
        foreach ($l in $saida) { Registrar ('    ' + $l) }
        if ($script:PastaInstalada) {
            Registrar ('  INSTALADO em ' + $script:PastaInstalada) 'ok'
        } else {
            Registrar '  a instalacao nao completou - veja o log acima' 'alerta'
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
    } finally {
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
    $env:RADAI_LICENCAS_ACEITAS = 'S'
    if ($idi) { $env:RADAI_IDIOMA = $idi }
    try {
        $cmdFilho = ('[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false); ' +
                     "Get-Content -LiteralPath '$ps1' -Raw -Encoding UTF8 | Invoke-Expression")
        $pIns = Start-Process -FilePath 'powershell' -ArgumentList @(
                    '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', $cmdFilho) `
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
        $env:RADAI_LICENCAS_ACEITAS = $null
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

$script:Licencas = @(
    @{ componente = 'Python'; versao = '3.10.11'; licenca = 'PSF License'; restritiva = $false
       permite = 'Uso comercial e redistribuição, sem restrição.'
       origem = 'python.org'; url = 'https://docs.python.org/3/license.html'
       resumo = 'Runtime portátil, sem instalação e sem administrador. Licença permissiva, sem restrição de uso.' }
    @{ componente = 'TotalSegmentator'; versao = '2.18.0'; licenca = 'Apache-2.0'; restritiva = $false
       permite = 'Uso comercial. O autor declara que não é dispositivo médico.'
       origem = 'github.com/wasserth/TotalSegmentator'; url = 'https://github.com/wasserth/TotalSegmentator/blob/master/LICENSE'
       resumo = 'É ele que reconhece os órgãos no fluxo principal. Licença permissiva. O próprio autor declara que NÃO é dispositivo médico.' }
    @{ componente = 'nnU-Net'; versao = '2.7.0'; licenca = 'Apache-2.0'; restritiva = $false
       permite = 'Uso comercial, com citação.'
       origem = 'github.com/MIC-DKFZ/nnUNet'; url = 'https://github.com/MIC-DKFZ/nnUNet/blob/master/LICENSE'
       resumo = 'A arquitetura sobre a qual o TotalSegmentator foi treinado. Os autores pedem que seja citada junto.' }
    @{ componente = 'PyTorch e bibliotecas de apoio'; versao = '2.5.1'; licenca = 'BSD-3-Clause, MIT, Apache-2.0'; restritiva = $false
       permite = 'Uso comercial liberado.'
       origem = 'pypi.org'; url = 'https://github.com/pytorch/pytorch/blob/main/LICENSE'
       resumo = 'SimpleITK, pydicom, rt-utils, nibabel, NumPy, SciPy, FastAPI, uvicorn. Todas permissivas.' }
    @{ componente = 'MONAI (código do bundle de inferência)'; versao = '1.4.0'; licenca = 'Apache-2.0'; restritiva = $false
       permite = 'Uso comercial liberado.'
       origem = 'github.com/Project-MONAI/VISTA'; url = 'https://github.com/Project-MONAI/VISTA/blob/main/LICENSE.txt'
       resumo = 'A biblioteca que executa o bundle, e o grafo de inferência que a NVIDIA não publica. É código permissivo; os PESOS vêm da NVIDIA, no item seguinte.' }
    @{ componente = 'NV-Segment-CT (NVIDIA) — PESOS'; versao = 'vista3d_pretrained_model'; licenca = 'NVIDIA Open Model License Agreement'; restritiva = $false
       permite = 'Uso comercial; a NVIDIA diz que não é para uso clínico.'
       origem = 'huggingface.co/nvidia/NV-Segment-CT'; url = 'https://huggingface.co/nvidia/NV-Segment-CT'
       resumo = ('Permite uso comercial: «Models are commercially usable» (LICENSE, linha 224). É o segundo motor, que grava um RTSTRUCT próprio para comparação.' + "`r`n" +
                 'O CAVEAT CLÍNICO NÃO VEM JUNTO COM O COMERCIAL: o cartão do modelo diz «for research purposes and not for clinical usage». Ler «comercialmente usável» como «liberado para rotina» é o erro que esta frase existe para impedir.') }
    @{ componente = 'CADS (variante open) — PESOS'; versao = 'Dataset556_GC256'; licenca = 'CC BY-SA 4.0'; restritiva = $false
       permite = 'Uso comercial; o ShareAlike vale só para o peso derivado.'
       origem = 'github.com/murong-xu/CADS'; url = 'https://github.com/murong-xu/CADS'
       resumo = 'Permite uso comercial. O ShareAlike só alcança obra derivada do peso, e não o contorno que sai dele.' }
    @{ componente = 'MOOSE (ENHANCE.PET) — PESOS'; versao = 'moosez-v.3.1.3'; licenca = 'CC BY 4.0'; restritiva = $false
       permite = 'Uso comercial, com atribuição.'
       origem = 'github.com/ENHANCE-PET/MOOSE'; url = 'https://github.com/ENHANCE-PET/MOOSE'
       resumo = 'Permite uso comercial, sem ShareAlike — e EXIGE atribuicao. Camaras cardiacas e composicao corporal, em arquivo proprio.' }
    @{ componente = 'Níveis linfonodais de cabeça e pescoço (Weissmann et al.)'; versao = 'Task110_HNLNFixed'; licenca = 'CC0-1.0'; restritiva = $false
       permite = 'Tudo, sem condição (domínio público).'
       origem = 'github.com/putzfn/HNLNL_autosegmentation_trained_models'; url = 'https://github.com/putzfn/HNLNL_autosegmentation_trained_models'
       resumo = 'Domínio público — a licença mais permissiva do pacote, sem exigir sequer atribuição, que damos assim mesmo. 20 níveis cervicais pelo consenso de Grégoire et al. (2013).' }
    @{ componente = 'CT Brain Segmentation Radiotherapy (Buti et al.) — PESOS'; versao = 'nnUNetTrainer__nnUNetPlans__3d_fullres'; licenca = 'MIT'; restritiva = $false
       permite = 'Uso comercial liberado.'
       origem = 'huggingface.co/GregoryButi/CT_Brain_Segmentation_Radiotherapy'; url = 'https://huggingface.co/GregoryButi/CT_Brain_Segmentation_Radiotherapy'
       resumo = 'Permite uso comercial. Tronco encefálico e quiasma em TC, que entram também no OAR; cerebelo, ventrículos e linha média só no FULL.' }
)

$y = AdicionarCabecalhoDasLicencas
foreach ($L in $script:Licencas) { $y = AdicionarLicenca $L $y }
AtualizarDicasDasLicencas
AtualizarBotaoLicencas
AtualizarConclusao '' ''

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

function _AutoClicar {
    param($Bt, [string]$Nome, [int]$Vive, [int]$Espera)
    $abas.SelectedIndex = $Vive
    [System.Windows.Forms.Application]::DoEvents()
    if ($Bt -and -not $Bt.Enabled) {
        [Console]::Out.WriteLine("CLIQUE`t" + $Nome +
                                 "`tDESABILITADO`tnada a medir")
        return
    }
    if (-not $Bt) { [Console]::Out.WriteLine("SEMBOTAO`t" + $Nome); return }
    $antes = $abas.SelectedIndex
    try {
        $Bt.PerformClick()
        $depois = $abas.SelectedIndex
        if ($depois -eq $Espera) {
            [Console]::Out.WriteLine("CLIQUE`t" + $Nome + "`tok`t" + $antes + ' -> ' + $depois)
        } else {
            [Console]::Out.WriteLine("CLIQUE`t" + $Nome + "`tNAOMUDOU`t" + $antes + ' -> ' +
                          $depois + ' (esperava ' + $Espera + ')')
        }
    } catch {
        [Console]::Out.WriteLine("CLIQUE`t" + $Nome + "`tERRO`t" + $_.Exception.Message)
    }
}

if ($env:RADAI_PREPARADOR_AUTOTESTE) {
    $form.Add_Shown({
        $baseFantomas = ''
        try {
            [Console]::Out.WriteLine("TELA`tform=" + $form.Size.ToString() +
                          " cliente=" + $form.ClientSize.ToString() +
                          " abas=" + $abas.Size.ToString())
            foreach ($fase in @('normal', 'maximizada')) {
                if ($fase -eq 'maximizada') {
                    $form.WindowState = [System.Windows.Forms.FormWindowState]::Maximized
                    [System.Windows.Forms.Application]::DoEvents()
                }
                for ($i = 0; $i -lt $abas.TabPages.Count; $i++) {
                    $abas.SelectedIndex = $i
                    [System.Windows.Forms.Application]::DoEvents()
                    $p = $abas.TabPages[$i]
                    [Console]::Out.WriteLine("ABA`t" + $fase + "`t" + $i + "`t" +
                                  ($p.Text.Trim()) + "`tcliente=" +
                                  $p.ClientRectangle.ToString())
                    _AutoMedir $p ('aba' + $i) $fase
                }
            }
            $form.WindowState = [System.Windows.Forms.FormWindowState]::Normal
            [System.Windows.Forms.Application]::DoEvents()

            if ($env:RADAI_PREPARADOR_CAPTURA) {
                foreach ($par in @(@(0, 'aba0_porta'), @(2, 'aba2_licencas'), @(3, 'aba3_preparar'))) {
                    try {
                        $abas.SelectedIndex = $par[0]
                        [System.Windows.Forms.Application]::DoEvents()
                        $bmp = New-Object System.Drawing.Bitmap($form.Width, $form.Height)
                        $form.DrawToBitmap($bmp, (New-Object System.Drawing.Rectangle(
                            0, 0, $form.Width, $form.Height)))
                        $png = Join-Path $env:RADAI_PREPARADOR_CAPTURA ('preparador_' + $par[1] + '.png')
                        $bmp.Save($png, [System.Drawing.Imaging.ImageFormat]::Png)
                        $bmp.Dispose()
                        [Console]::Out.WriteLine("CAPTURA`t" + $png)
                    } catch {
                        [Console]::Out.WriteLine("CAPTURA`tERRO`t" + $_.Exception.Message)
                    }
                }
            }

            foreach ($caso in @(
                    @{ n = 'ha versao nova'; ok = $true;  v = '99.0' },
                    @{ n = 'estou em dia';   ok = $true;  v = '0.1' },
                    @{ n = 'sem resposta';   ok = $false; v = '' })) {
                try {
                    $script:VersaoLa = @{
                        ok = $caso.ok; versao = $caso.v
                        url = 'https://exemplo/releases'
                        erro = $(if ($caso.ok) { '' } else { 'proxy recusou' }) }
                    $cf = ConferirMinhaVersao
                    [Console]::Out.WriteLine("AUTOCONF`t" + $caso.n + "`t" +
                                             $cf.estado + "`t" + $cf.frase)
                } catch {
                    [Console]::Out.WriteLine("AUTOCONF`t" + $caso.n +
                                             "`tERRO`t" + $_.Exception.Message)
                }
            }
            $urlAntes = $script:URL_RELEASES
            try {
                $script:VersaoLa = $null
                $script:URL_RELEASES = 'http://127.0.0.1:9/x'
                $cf = VersaoPublicada
                [Console]::Out.WriteLine("AUTOCONF`tsem rede`t" +
                    $(if ($cf.ok) { 'ok' } else { 'falhou' }) + "`t" +
                    [string]$cf.erro)
            } catch {
                [Console]::Out.WriteLine("AUTOCONF`tsem rede`tERRO`t" +
                                         $_.Exception.Message)
            } finally {
                $script:URL_RELEASES = $urlAntes
                $script:VersaoLa = $null
            }
            if ($env:RADAI_PREPARADOR_URL_NAO_ACHADA) {
                try {
                    $script:VersaoLa = $null
                    $script:URL_RELEASES = $env:RADAI_PREPARADOR_URL_NAO_ACHADA
                    $cf = VersaoPublicada
                    [Console]::Out.WriteLine("AUTOCONF`t404`t" +
                        $(if ($cf.ok) { 'ok' } else { 'falhou' }) + "`t" +
                        [string]$cf.erro)
                } catch {
                    [Console]::Out.WriteLine("AUTOCONF`t404`tERRO`t" +
                                             $_.Exception.Message)
                } finally {
                    $script:URL_RELEASES = $urlAntes
                    $script:VersaoLa = $null
                }
            }

            $titAbas = @()
            foreach ($tp in $abas.TabPages) { $titAbas += $tp.Text.Trim() }
            [Console]::Out.WriteLine("ABAS`t" + $titAbas.Count + "`t" +
                                     ($titAbas -join '|'))
            $porta = @($script:BotoesDaPorta | Sort-Object -Property Top, Left)
            [Console]::Out.WriteLine("ORDEM`t" +
                (($porta | ForEach-Object { $_.Text }) -join '|'))
            $porTab = @($aba0.Controls | Where-Object {
                          $_ -is [System.Windows.Forms.Button] } |
                        Sort-Object -Property TabIndex)
            [Console]::Out.WriteLine("ORDEMTAB`t" +
                (($porTab | ForEach-Object { $_.Text }) -join '|'))
            [Console]::Out.WriteLine("TAMANHO`t" + $script:PacoteGB + "`t" +
                $script:DiscoGB + "`t" + $script:DownloadGB + "`t" +
                $script:NTarefas + "`t" + $script:NModelos + "`t" +
                $script:TamanhoDeOnde)
            [Console]::Out.WriteLine("PASTA`t" + $script:RotuloPasta.Text)
            [Console]::Out.WriteLine("ABA1`t" +
                $(if ($txt1.Text.Contains('{')) { 'CHAVE CRUA' } else { 'ok' }) +
                "`t" + ($txt1.Text -replace "[`r`n]+", ' '))
            [Console]::Out.WriteLine("ICONE`t" + $script:IconeDaJanela)
            try {
                [Console]::Out.WriteLine("CABECALHO`t" + (MedirMarcaDoCabecalho))
            } catch {
                [Console]::Out.WriteLine("CABECALHO`tERRO`t" + $_.Exception.Message)
            }
            [Console]::Out.WriteLine("ABA0`t" + ((@($script:LegendasDaPorta | ForEach-Object { $_.Text })) -join ' | '))
            $okLinhas = ($btModo3.Top -eq $btModo2.Top) -and
                        ($btModo1.Bottom -lt $btModo3.Top) -and ($btModo3.Bottom -lt $btModo5.Top) -and
                        ($btModo3.Right -lt $btModo2.Left)
            $okDestaque = ($btModo1.Width -ge ($btModo2.Right - $btModo3.Left)) -and
                          ($btModo1.Height -gt $btModo3.Height) -and ($btModo3.Height -gt $btModo5.Height) -and
                          ($btModo1.Font.Size -gt $btModo3.Font.Size) -and ($btModo3.Font.Size -gt $btModo5.Font.Size) -and
                          $btModo1.Font.Bold -and (-not $btModo3.Font.Bold) -and (-not $btModo5.Font.Bold) -and
                          ($btModo1.BackColor.ToArgb() -eq $script:Cor.Ok.ToArgb())
            $okLeg = ($script:LegendasDaPorta.Count -eq $script:BotoesDaPorta.Count)
            foreach ($lg in $script:LegendasDaPorta) {
                $dono = @($script:BotoesDaPorta | Where-Object { $_.Left -eq $lg.Left -and $_.Bottom -le $lg.Top -and ($lg.Top - $_.Bottom) -le 6 })
                if ($dono.Count -ne 1) { $okLeg = $false }
                foreach ($outro in $script:BotoesDaPorta) {
                    if ($outro.Left -lt $lg.Right -and $outro.Right -gt $lg.Left -and
                        $outro.Top -lt $lg.Bottom -and $outro.Bottom -gt $lg.Top) { $okLeg = $false }
                }
            }
            [Console]::Out.WriteLine("LINHAS`t" + $(if ($okLinhas -and $okDestaque -and $okLeg) { 'ok' } else {
                'A PORTA NAO TEM O BOTAO UNICO EM DESTAQUE: linhas=' + $okLinhas + ' destaque=' + $okDestaque + ' legendas=' + $okLeg }))
            [Console]::Out.WriteLine("VERSOES`t" + $script:RotInstalador.Text + "`t" +
                                     $script:RotAceita.Text + "`t" + $script:BundleMinimoDeOnde)
            [Console]::Out.WriteLine("VERSOESPOS`t" +
                $(if (($pnEstado.Bottom -le $script:RotInstalador.Top) -and
                      ($script:RotInstalador.Bottom -le $script:RotAceita.Top) -and
                      ($script:RotAceita.Bottom -le $btModo1.Top) -and
                      $aba0.Controls.Contains($script:RotInstalador) -and
                      $aba0.Controls.Contains($script:RotAceita)) { 'ok' }
                  else { 'AS LINHAS DE VERSAO COBREM OUTRO CONTROLE: estado=' +
                         $pnEstado.Bottom + ' linhas=' + $script:RotInstalador.Top + '..' +
                         $script:RotAceita.Bottom + ' botao=' + $btModo1.Top }))

            [Console]::Out.WriteLine("PORTA`t" +
                $(if ($script:Instalado) { "instalado:" + $script:Instalado.pasta }
                  else { "nada instalado" }) + "`t" +
                "instalar_atualizar=" + $btModo1.Enabled + "`t" +
                "desinstalar=" + $btModo5.Enabled)
            [Console]::Out.WriteLine("PORTAOK`t" +
                $(if ($btModo1.Enabled -and ($btModo5.Enabled -eq [bool]$temInst)) { "ok" }
                  else { "INSTALAR / ATUALIZAR TEM DE NASCER ACESO; DESINSTALAR SO COM INSTALACAO DETECTADA" }))
            $script:CascataDoAutoteste = @()
            function script:IniciarAtualizarApp {
                param($Inst)
                $script:CascataDoAutoteste += [string]$Inst.pasta
                return 'autoteste'
            }
            $instDaMaquina = $script:Instalado
            $buscaDaMaquina = $env:RADAI_RAIZES_BUSCA
            $baseFantomas = Join-Path ([System.IO.Path]::GetTempPath()) ('radai_autoteste_porta_' + [guid]::NewGuid().ToString('N'))
            $fant = @{}
            foreach ($caso in @('vazio', 'quase', 'registro', 'marca')) {
                $fant[$caso] = Join-Path $baseFantomas $caso
                New-Item -ItemType Directory -Path $fant[$caso] -Force | Out-Null
            }
            $quase = Join-Path $fant['quase'] 'LOCAL_SUITE'
            New-Item -ItemType Directory -Path $quase -Force | Out-Null
            [System.IO.File]::WriteAllText((Join-Path $quase 'radai_watcher.py'), '#')
            [System.IO.File]::WriteAllText((Join-Path $fant['quase'] '_instalados.json'),
                ('{"LOCAL_SUITE": {"caminho": ' + (ConvertTo-Json (Join-Path $baseFantomas 'nao_existe\LOCAL_SUITE')) + '}}'))
            $longe = Join-Path $baseFantomas 'outro_disco\LOCAL_SUITE'
            $perto = Join-Path $fant['marca'] 'LOCAL_SUITE'
            foreach ($p in @($longe, $perto)) {
                New-Item -ItemType Directory -Path $p -Force | Out-Null
                [System.IO.File]::WriteAllText((Join-Path $p 'radai_watcher.py'), '#')
                [System.IO.File]::WriteAllText((Join-Path $p 'entrega.txt'), "PROJETO=LOCAL_SUITE`r`nVERSAO=8.5`r`n")
            }
            [System.IO.File]::WriteAllText((Join-Path $fant['registro'] '_instalados.json'),
                ('{"LOCAL_SUITE": {"caminho": ' + (ConvertTo-Json $longe) + ', "versao": "8.5"}}'))
            $env:RADAI_RAIZES_BUSCA = $fant['vazio']
            $script:Instalado = $null
            _AutoClicar $btModo1 'modo 1 (esta maquina e a estacao)' 0 1
            [Console]::Out.WriteLine("MODO`tdepois do botao 1`t" + $script:Modo)
            $esperadaDireto = $script:DESTINO_PADRAO
            if ($script:Instalado) {
                $esperadaDireto = [string]$script:Instalado.pasta
                $paiDoAchado = Split-Path -Parent $esperadaDireto
                if ($paiDoAchado -and (SobraDoPreparoAntigo $paiDoAchado)) { $esperadaDireto = Split-Path -Parent $paiDoAchado }
            }
            [Console]::Out.WriteLine("DIRETO`t" +
                $(if (($cxPasta.Text -eq $esperadaDireto) -and
                      (-not $cxPasta.Text.TrimEnd('\').EndsWith('\preparo')) -and
                      ($script:BtRodar.Text -eq (T 'Instalar agora')) -and
                      (ModoDireto)) { 'ok' } else { 'O MODO 1 NAO APONTA A PASTA FINAL' }) +
                "`t" + $cxPasta.Text + "`t" + $script:BtRodar.Text + "`t" + $script:RotuloPasta.Text)
            _AutoClicar $bt1 'Entendi - ver as licencas' 1 2
            foreach ($cx in $script:CaixasLicenca) { $cx.Checked = $true }
            [Console]::Out.WriteLine("FINALIDADE`tseletor=" +
                $(if ($script:DeclFinalidade) { 'presente' } else { 'ausente' }) +
                "`trestritas=" + $script:OpcoesLicenca.Count +
                "`tbotao=" + $bt2.Enabled)
            AtualizarBotaoLicencas
            foreach ($cx in $script:CaixasLicenca) { $cx.Checked = $false }
            AtualizarBotaoLicencas
            $marcadasAntes = @($script:CaixasLicenca | Where-Object { $_.Checked }).Count
            $abas.SelectedIndex = 2
            [System.Windows.Forms.Application]::DoEvents()
            $listaVisivel = $rolo2.Visible
            _AutoClicar $btTodas 'Aceitar todas as licencas' 2 3
            $todasMarcadas = (@($script:CaixasLicenca | Where-Object { -not $_.Checked }).Count -eq 0)
            [Console]::Out.WriteLine("TODAS`t" +
                $(if ($todasMarcadas -and $script:AceiteDeUmaVez -and ($marcadasAntes -eq 0) -and
                      $listaVisivel -and $bt2.Enabled -and ($script:CaixasLicenca.Count -gt 0)) { 'ok' }
                  else { 'ACEITAR TODAS NAO MARCOU AS CAIXAS NA TELA: marcadas=' + $todasMarcadas +
                         ' antes=' + $marcadasAntes + ' registro=' + $script:AceiteDeUmaVez +
                         ' lista_visivel=' + $listaVisivel }) +
                "`t" + $script:CaixasLicenca.Count)
            $abas.SelectedIndex = 2
            [System.Windows.Forms.Application]::DoEvents()
            $faltaLinha = @()
            foreach ($L in $script:Licencas) {
                $ln = @($script:LinhasDeLicenca | Where-Object { $_.L -eq $L })
                if ($ln.Count -ne 1) { $faltaLinha += ([string]$L.componente + ' (sem linha)'); continue }
                $c = $ln[0].Controles
                $temNome = @($c | Where-Object { [string]$_.Text -eq (T $L.componente) }).Count -eq 1
                $temLic = @($c | Where-Object { [string]$_.Text -eq [string]$L.licenca }).Count -eq 1
                $temPermite = [bool]$L.permite -and (@($c | Where-Object { [string]$_.Text -eq (T $L.permite) }).Count -eq 1)
                $lk = @($c | Where-Object { $_ -is [System.Windows.Forms.LinkLabel] })
                $temLink = ($lk.Count -eq 1) -and ([string]$lk[0].Tag).StartsWith('https://')
                $pai = $c[0].Parent
                $mesmaLinha = [bool]$pai -and (@($c | Where-Object { -not [object]::ReferenceEquals($_.Parent, $pai) }).Count -eq 0)
                if (-not ($temNome -and $temLic -and $temPermite -and $temLink -and $mesmaLinha)) {
                    $faltaLinha += ([string]$L.componente + ' nome=' + $temNome + ' licenca=' + $temLic +
                                    ' permite=' + $temPermite + ' link=' + $temLink + ' linha=' + $mesmaLinha)
                }
            }
            [Console]::Out.WriteLine("LINHASLIC`t" + $(if (($faltaLinha.Count -eq 0) -and
                    ($script:LinhasDeLicenca.Count -eq @($script:Licencas).Count)) { 'ok' }
                else { 'CADA COMPONENTE TEM DE TER UMA LINHA COM NOME, LICENCA, O QUE PERMITE E LINK: ' +
                       ($faltaLinha -join ' | ') }) + "`t" + $script:LinhasDeLicenca.Count)
            _AutoClicar $bt2 'Continuar e escolher a pasta' 2 3

            $rotUlt = @($aba3.Controls | Where-Object {
                $_ -is [System.Windows.Forms.Label] -and
                $_.Top -lt $script:CaixaLog.Top } |
                Sort-Object -Property Top -Descending | Select-Object -First 1)
            [Console]::Out.WriteLine("LOGY`t" +
                $(if ($rotUlt -and ($rotUlt[0].Bottom -le $script:CaixaLog.Top))
                  { 'ok' } else { 'A CAIXA DE LOG COMECA EM CIMA DO ROTULO' }) +
                "`tlog=" + $script:CaixaLog.Top +
                "`trotulo_fim=" + $(if ($rotUlt) { $rotUlt[0].Bottom } else { -1 }) +
                "`tbotao_fim=" + $btRodar.Bottom)

            $naAba0 = @($aba0.Controls | Where-Object {
                $_ -is [System.Windows.Forms.ComboBox] }).Count
            [Console]::Out.WriteLine("IDIOMA`tseletores=" +
                $script:SeletoresIdioma.Count + "`tcombo na aba 0=" + $naAba0)
            if ($script:SeletoresIdioma.Count -ge 2) {
                $a = $script:SeletoresIdioma[0]
                $b = $script:SeletoresIdioma[1]
                $instAntes = $script:Instalado
                $script:Instalado = @{ pasta = 'X:\fantoma_do_autoteste'; versao = '9.9' }
                PintarEstado
                $b.SelectedIndex = $(if ($b.SelectedIndex -eq 0) { 1 } else { 0 })
                [System.Windows.Forms.Application]::DoEvents()
                [Console]::Out.WriteLine("IDIOMASYNC`t" +
                    $(if ($a.SelectedIndex -eq $b.SelectedIndex) { "ok" }
                      else { "OS DOIS SELETORES DIVERGIRAM: " +
                             $a.SelectedIndex + " vs " + $b.SelectedIndex }))
                $fraseNova = (T 'Ja instalado nesta maquina')
                [Console]::Out.WriteLine("ESTADO`t" +
                    $(if (($script:RotOnde.Text -eq 'X:\fantoma_do_autoteste') -and
                          $script:RotEstado.Text.StartsWith($fraseNova) -and
                          ($fraseNova -ne 'Ja instalado nesta maquina')) { 'ok' }
                      else { 'O PAINEL NAO ACOMPANHOU A TROCA DE IDIOMA' }) +
                    "`t" + (Idioma-Atual) + "`t" + $script:RotEstado.Text +
                    "`t" + $script:RotOnde.Text)
                $chaveV = 'Aceita pacote de transferencia (bundle) versao {0} ou superior'
                $fraseV = (T $chaveV)
                [Console]::Out.WriteLine("VERSOESTROCA`t" +
                    $(if (($fraseV -ne $chaveV) -and
                          ($script:RotAceita.Text -eq ($fraseV -f $script:BUNDLE_MINIMO)) -and
                          ($script:RotInstalador.Text -eq ((T 'Instalador v{0}') -f $script:VERSAO_INSTALADOR)))
                      { 'ok' } else { 'AS LINHAS DE VERSAO NAO ACOMPANHARAM A TROCA DE IDIOMA' }) +
                    "`t" + (Idioma-Atual) + "`t" + $script:RotAceita.Text)
                $script:Instalado = $instAntes
                PintarEstado
                $b.SelectedIndex = 0
                [System.Windows.Forms.Application]::DoEvents()
            }

            foreach ($cx in $script:CaixasLicenca) { $cx.Checked = $false }
            AtualizarBotaoLicencas
            [System.Windows.Forms.Application]::DoEvents()
            [Console]::Out.WriteLine("MODO3ANTES`tlicencas=" + $bt2.Enabled +
                "`t(tem de ser False, senao a medida seguinte nao vale)")
            _AutoClicar $btModo3 'modo 3 (instalar de um arquivo)' 0 1
            [Console]::Out.WriteLine("MODO3`tradios=" +
                $rbSim.Enabled + "/" + $rbNao.Enabled +
                "`tlicencas=" + $bt2.Enabled +
                "`ttitulo=" + ($rotRotaTit.Text.Length -gt 0))
            [Console]::Out.WriteLine("MODO3OK`t" +
                $(if ((-not $rbSim.Enabled) -and $bt2.Enabled) { "ok" }
                  else { "O MODO 3 NAO LIBEROU A ABA 2 (bt2=" +
                         $bt2.Enabled + ")" }))
            if ($script:CaixasLicenca.Count -gt 0) {
                $script:CaixasLicenca[0].Checked = $false
                [System.Windows.Forms.Application]::DoEvents()
                [Console]::Out.WriteLine("MODO3CLIQUE`t" +
                    $(if ($bt2.Enabled) { "ok" }
                      else { "DESMARCAR UMA CAIXA TRAVOU A ABA 2 DE NOVO" }))
                $script:CaixasLicenca[0].Checked = $true
            }
            foreach ($cx in $script:CaixasLicenca) { $cx.Checked = $true }
            _AutoClicar $btModo1 'volta ao modo 1' 0 1
            [Console]::Out.WriteLine("VOLTA`tradios=" +
                $rbSim.Enabled + "/" + $rbNao.Enabled +
                "`taviso=" + $rot1.Text.Length +
                "`tbotao=" + $bt1.Enabled)
            [Console]::Out.WriteLine("VOLTAOK`t" +
                $(if ($rbSim.Enabled -and $rbNao.Enabled -and
                      $rot1.Text.Length -eq 0) { "ok" }
                  else { "A VOLTA DEIXOU O AVISO DO MODO 3 NA TELA" }))
            _AutoClicar $btModo2 'modo 2 (preparar um pacote para levar)' 0 1
            [Console]::Out.WriteLine("PACOTE`t" +
                $(if (($cxPasta.Text -eq $script:PACOTE_SUGERIDO) -and
                      (-not $cxPasta.Text.StartsWith($script:DESTINO_PADRAO, [System.StringComparison]::OrdinalIgnoreCase)) -and
                      ($script:BtRodar.Text -eq (T 'Preparar o pacote'))) { 'ok' }
                  else { 'O MODO 2 MONTA DENTRO DA PASTA DO PROGRAMA' }) + "`t" + $cxPasta.Text)
            $instAntes7 = $script:Instalado
            $script:Instalado = @{ pasta = 'X:\fantoma_modo7\LOCAL_SUITE'; versao = '8.3' }
            $abas.SelectedIndex = 0
            [System.Windows.Forms.Application]::DoEvents()
            MarcarModo '7'
            [System.Windows.Forms.Application]::DoEvents()
            [Console]::Out.WriteLine("MODO7`t" +
                $(if (($script:Modo -eq '7') -and ($cxPasta.Text -eq 'X:\fantoma_modo7\LOCAL_SUITE') -and
                      $cxPasta.ReadOnly -and ($script:BtRodar.Text -eq (T 'Atualizar tudo'))) { 'ok' }
                  else { 'O MODO 7 NAO FIXA A PASTA INSTALADA' }) + "`t" + $cxPasta.Text)
            $script:Instalado = $instAntes7
            _AutoClicar $btModo1 'volta ao modo 1 (pasta livre de novo)' 0 1
            $abas.SelectedIndex = 3
            [System.Windows.Forms.Application]::DoEvents()
            [Console]::Out.WriteLine("LIVRE`t" + $(if ((-not $cxPasta.ReadOnly) -and $btPasta.Visible) { 'ok' } else { 'A PASTA FICOU PRESA DEPOIS DO MODO 7' }))
            foreach ($caso in @('vazio', 'quase', 'registro', 'marca')) {
                $env:RADAI_RAIZES_BUSCA = $fant[$caso]
                $script:Instalado = $null
                $script:Modo = ''
                $script:CascataDoAutoteste = @()
                $abas.SelectedIndex = 0
                [System.Windows.Forms.Application]::DoEvents()
                $btModo1.PerformClick()
                [System.Windows.Forms.Application]::DoEvents()
                [Console]::Out.WriteLine("BOTAO`t" + $caso + "`tmodo=" + $script:Modo +
                    "`tcascata=" + ((@($script:CascataDoAutoteste) | ForEach-Object { $_.Replace($baseFantomas, '<base>') }) -join ';') +
                    "`tcomo=" + $(if ($script:Instalado) { [string]$script:Instalado.como } else { '-' }) +
                    "`taba=" + $abas.SelectedIndex + "`tdesinstalar=" + $btModo5.Enabled)
            }
            [Console]::Out.WriteLine("FIM")
        } catch {
            [Console]::Out.WriteLine("ERRO`t" + $_.Exception.Message)
        } finally {
            if ($baseFantomas) {
                $env:RADAI_RAIZES_BUSCA = $buscaDaMaquina
                $script:Instalado = $instDaMaquina
                Remove-Item -LiteralPath $baseFantomas -Recurse -Force -ErrorAction SilentlyContinue
            }
            $form.Close()
        }
    })
}

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
    $d.Text = 'Idioma / Language'
    $d.ClientSize = New-Object System.Drawing.Size(440, 240)
    $d.StartPosition = 'CenterScreen'
    $d.FormBorderStyle = 'FixedDialog'
    $d.MaximizeBox = $false
    $d.MinimizeBox = $false
    $d.BackColor = $script:Cor.Fundo
    try { if ($form.Icon) { $d.Icon = $form.Icon } } catch { }

    Sessao 'marca da splash: radioterapia.ai + LOCAL SUITE (sem imagem)'

    $tit = New-Object System.Windows.Forms.Panel
    $tit.Location = New-Object System.Drawing.Point(20, 28)
    $tit.Size = New-Object System.Drawing.Size(400, 50)
    $tit.BackColor = $script:Cor.Fundo
    $tit.Tag = @{
        Palavra  = 'radioterapia'
        Sufixo   = '.ai'
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
    $sub.Text = 'LOCAL SUITE'
    $sub.Location = New-Object System.Drawing.Point(20, 78)
    $sub.Size = New-Object System.Drawing.Size(400, 22)
    $sub.Font = Fonte 10 'Bold'
    $sub.ForeColor = $script:Cor.Fraco
    $sub.BackColor = [System.Drawing.Color]::Transparent
    $sub.TextAlign = [System.Drawing.ContentAlignment]::MiddleCenter
    $d.Controls.Add($sub)

    $t = New-Object System.Windows.Forms.Label
    $t.Text = 'Idioma  ·  Language  ·  Idioma  ·  Sprache  ·  Langue'
    $t.Location = New-Object System.Drawing.Point(30, 120)
    $t.Size = New-Object System.Drawing.Size(380, 24)
    $t.Font = Fonte 10 'Bold'
    $t.ForeColor = $script:Cor.Titulo
    $t.BackColor = [System.Drawing.Color]::Transparent
    $d.Controls.Add($t)

    $sel = Novo-SeletorIdioma 30 148 380 $form $script:AoTrocarIdioma
    if ($sel) { $d.Controls.Add($sel); $script:SeletoresIdioma += $sel }

    $ok = New-Object System.Windows.Forms.Button
    $ok.Text = 'OK'
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
            [Console]::Out.WriteLine("IDIOMAJANELA`t" + $d.Size.ToString() +
                                     "`tcontroles=" + $d.Controls.Count)
            try {
                [Console]::Out.WriteLine("MARCA`t" + (MedirMarcaDaSplash))
            } catch {
                [Console]::Out.WriteLine("MARCA`tERRO`t" + $_.Exception.Message)
            }
            if ($env:RADAI_PREPARADOR_CAPTURA) {
                try {
                    $bmpS = New-Object System.Drawing.Bitmap($d.Width, $d.Height)
                    $d.DrawToBitmap($bmpS, (New-Object System.Drawing.Rectangle(
                        0, 0, $d.Width, $d.Height)))
                    $pngS = Join-Path $env:RADAI_PREPARADOR_CAPTURA 'preparador_splash.png'
                    $bmpS.Save($pngS, [System.Drawing.Imaging.ImageFormat]::Png)
                    $bmpS.Dispose()
                    [Console]::Out.WriteLine("CAPTURA`t" + $pngS)
                } catch {
                    [Console]::Out.WriteLine("CAPTURA`tERRO`t" + $_.Exception.Message)
                }
            }
            $d.Close()
        })
    }
    [void]$d.ShowDialog()
}
if (-not $script:PastaDaCascata) {
    try { PerguntarIdioma } catch {
        [Console]::Out.WriteLine('AVISO: nao abri a escolha de idioma (' +
                                 $_.Exception.Message + ')')
    }
}
if ($script:PastaDaCascata -and -not $env:RADAI_PREPARADOR_AUTOTESTE) {
    $form.Add_Shown({ RetomarAtualizarApp })
}
if (-not $script:PastaDaCascata -and -not $env:RADAI_PREPARADOR_AUTOTESTE) {
    $form.Add_Shown({
        try { EncerrarAppNoArranque } catch {
            Sessao ('arranque: nao consegui conferir o app aberto (' + $_.Exception.Message + ')')
        }
    })
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
    Sessao ('  em: ' + $_.InvocationInfo.PositionMessage)
    $script:ErroJaNoLog = $true
    throw
}
Sessao 'janela fechada; fim normal'
