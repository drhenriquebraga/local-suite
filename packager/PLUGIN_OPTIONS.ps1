# Optional resources for the manual Local Suite installer. Dot-source only.
# The pinned catalog is generated from each plugin's canonical consent policy.
function Ler-CatalogoPluginsSuite {
    param([Parameter(Mandatory = $true)][string]$Caminho)
    $catalogo = [System.IO.File]::ReadAllText($Caminho, [System.Text.Encoding]::UTF8) | ConvertFrom-Json
    foreach ($id in @('neuro-rt', 'lung-rt')) {
        $politica = $catalogo.plugins.$id
        if (-not $politica -or -not $politica.title -or -not $politica.version -or
            ([string]$politica.digest -notmatch '^[0-9a-f]{64}$') -or
            @($politica.clauses).Count -eq 0 -or [long]$politica.disk_bytes_max -le 0) {
            throw (T 'O catálogo dos plugins está incompleto. A instalação da suíte permanece disponível.')
        }
    }
    return $catalogo
}

function Ler-PacotesSuite {
    param([Parameter(Mandatory = $true)][string[]]$Caminhos)
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $bases = @(); $plugins = @()
    foreach ($caminho in $Caminhos) {
        $zip = [System.IO.Compression.ZipFile]::OpenRead($caminho)
        try {
            $marca = $zip.GetEntry('entrega.txt')
            $base = $false
            if ($marca -and $marca.Length -le 65536 -and $zip.GetEntry('INSTALL.ps1')) {
                $leitor = New-Object System.IO.StreamReader($marca.Open())
                try { $texto = $leitor.ReadToEnd() } finally { $leitor.Dispose() }
                $base = $texto -match '(?im)^\s*PROJETO\s*=\s*(LOCAL_SUITE|AUTO_CONTORNO)\s*$'
            }
            if ($base) { $bases += $caminho } else { $plugins += $caminho }
        } finally { $zip.Dispose() }
    }
    if ($bases.Count -ne 1 -or $plugins.Count -gt 2) {
        throw (T 'Selecione um pacote da Local Suite e, se desejar, até dois pacotes dos plugins NEURO RT e LUNG RT.')
    }
    return @{ Base = $bases[0]; Plugins = $plugins }
}

function Novo-PlanoPluginsSuite {
    param([Parameter(Mandatory = $true)]$Catalogo,
          [Parameter(Mandatory = $true)][AllowEmptyCollection()][object[]]$Escolhas)
    $plugins = @()
    foreach ($escolha in $Escolhas) {
        $id = [string]$escolha.id
        if (@('neuro-rt', 'lung-rt') -notcontains $id -or
            @($plugins | Where-Object { $_.id -eq $id }).Count -gt 0) {
            throw (T 'A seleção dos plugins é inválida.')
        }
        $politica = $Catalogo.plugins.$id
        if (-not $politica -or $escolha.accepted -ne $true -or
            ([string]$politica.digest -notmatch '^[0-9a-f]{64}$')) {
            throw (T 'Leia e aceite os termos de cada plugin selecionado antes de instalar.')
        }
        $origem = ([string]$escolha.source).Trim()
        if ($origem -ne 'online') {
            if (-not [System.IO.Path]::IsPathRooted($origem) -or
                -not (Test-Path -LiteralPath $origem)) {
                throw (T 'Aponte um ZIP ou uma pasta existente para cada plugin offline.')
            }
            $origem = [System.IO.Path]::GetFullPath($origem)
            if ((Test-Path -LiteralPath $origem -PathType Leaf) -and
                [System.IO.Path]::GetExtension($origem) -ine '.zip') {
                throw (T 'O pacote offline deve ser um arquivo ZIP ou uma pasta extraída.')
            }
        }
        $plugins += [ordered]@{ id = $id; source = $origem; accepted = $true
            consent = [ordered]@{ accepted = $true; version = [string]$politica.version
                                  digest = [string]$politica.digest } }
    }
    return @{ plugins = @($plugins) }
}

function Selecionar-PluginsSuite {
    param([Parameter(Mandatory = $true)]$Catalogo,
          $Owner = $null, [switch]$Offline, [string[]]$PacotesOffline = @())
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    $janela = New-Object System.Windows.Forms.Form
    $janela.Name = 'plugin-options-suite'
    $janela.Text = (T 'Local Suite · plugins opcionais')
    $janela.ClientSize = New-Object System.Drawing.Size(900, 675)
    $janela.MinimumSize = New-Object System.Drawing.Size(916, 714)
    $janela.StartPosition = 'CenterParent'
    $janela.BackColor = [System.Drawing.Color]::FromArgb(10, 17, 32)
    $janela.ForeColor = [System.Drawing.Color]::FromArgb(230, 237, 247)
    $janela.Font = New-Object System.Drawing.Font('Segoe UI', 9)
    $janela.MaximizeBox = $false
    $janela.MinimizeBox = $false
    $janela.AutoScroll = $true
    $estado = @{ Plano = $null; Linhas = @() }
    $titulo = New-Object System.Windows.Forms.Label
    $titulo.Text = (T 'Instalar também os plugins nesta máquina?')
    $titulo.Font = New-Object System.Drawing.Font('Segoe UI', 14, [System.Drawing.FontStyle]::Bold)
    $titulo.SetBounds(20, 16, 860, 32); $janela.Controls.Add($titulo)
    $intro = New-Object System.Windows.Forms.Label
    $intro.Text = (T 'Opcional. O Python e os recursos já instalados são reutilizados. A suíte abre depois desta etapa.')
    $intro.SetBounds(20, 52, 860, 40); $janela.Controls.Add($intro)
    $n = 0
    foreach ($id in @('neuro-rt', 'lung-rt')) {
        $politica = $Catalogo.plugins.$id
        $grupo = New-Object System.Windows.Forms.GroupBox
        $grupo.Name = 'plugin-' + $id
        $grupo.Text = $(if ($id -eq 'neuro-rt') { 'NEURO RT' } else { 'LUNG RT' })
        $grupo.ForeColor = $janela.ForeColor
        $grupo.SetBounds((20 + $n * 440), 98, 420, 468); $janela.Controls.Add($grupo)
        $selecionado = New-Object System.Windows.Forms.CheckBox
        $selecionado.Name = 'selecionado'
        $selecionado.Text = (T 'Incluir este plugin')
        $selecionado.SetBounds(14, 25, 390, 26); $grupo.Controls.Add($selecionado)
        $tamanho = New-Object System.Windows.Forms.Label
        $tamanho.Text = ((T 'Até {0} GB adicionais no disco, incluindo cache; arquivos temporários podem exigir espaço extra.') -f
            ([math]::Round([long]$politica.disk_bytes_max / 1000000000, 2)))
        $tamanho.SetBounds(14, 58, 390, 48); $grupo.Controls.Add($tamanho)
        $modelos = New-Object System.Windows.Forms.TextBox
        $modelos.Multiline = $true; $modelos.ReadOnly = $true; $modelos.ScrollBars = 'Vertical'
        $modelos.BackColor = [System.Drawing.Color]::FromArgb(15, 23, 41)
        $modelos.ForeColor = $janela.ForeColor; $modelos.BorderStyle = 'FixedSingle'
        $modelos.Text = (T 'Modelos:') + ' ' + (@($politica.models) -join '; ')
        $modelos.SetBounds(14, 109, 390, 62); $grupo.Controls.Add($modelos)
        $origem = New-Object System.Windows.Forms.ComboBox
        $origem.Name = 'origem'
        $origem.DropDownStyle = 'DropDownList'
        $origem.FlatStyle = 'Flat'; $origem.BackColor = $modelos.BackColor
        $origem.ForeColor = $janela.ForeColor
        $origem.DrawMode = 'OwnerDrawFixed'
        $origem.Add_DrawItem({ param($controle, $ev)
            $fundo = New-Object System.Drawing.SolidBrush($controle.BackColor)
            try { $ev.Graphics.FillRectangle($fundo, $ev.Bounds) } finally { $fundo.Dispose() }
            if ($ev.Index -ge 0) {
                [System.Windows.Forms.TextRenderer]::DrawText($ev.Graphics,
                    [string]$controle.Items[$ev.Index], $controle.Font, $ev.Bounds,
                    $controle.ForeColor, [System.Windows.Forms.TextFormatFlags]::Left)
            }
            $ev.DrawFocusRectangle()
        })
        [void]$origem.Items.Add((T 'Internet · baixar apenas recursos ausentes'))
        [void]$origem.Items.Add((T 'Offline · usar um ZIP ou uma pasta'))
        $origem.SetBounds(14, 181, 390, 27); $grupo.Controls.Add($origem)
        $arquivo = New-Object System.Windows.Forms.TextBox
        $arquivo.Name = 'arquivo'
        $arquivo.BackColor = $modelos.BackColor; $arquivo.ForeColor = $janela.ForeColor
        $arquivo.SetBounds(14, 216, 288, 25); $grupo.Controls.Add($arquivo)
        $procurar = New-Object System.Windows.Forms.Button
        $procurar.Text = (T 'ZIP…'); $procurar.SetBounds(308, 214, 46, 28)
        $grupo.Controls.Add($procurar)
        $pasta = New-Object System.Windows.Forms.Button
        $pasta.Text = (T 'Pasta…'); $pasta.SetBounds(358, 214, 46, 28)
        $grupo.Controls.Add($pasta)
        foreach ($botao in @($procurar, $pasta)) {
            $botao.FlatStyle = 'Flat'; $botao.BackColor = $modelos.BackColor
            $botao.ForeColor = $janela.ForeColor
        }
        $termos = New-Object System.Windows.Forms.RichTextBox
        $termos.Name = 'termos'
        $termos.ReadOnly = $true; $termos.DetectUrls = $true
        $termos.BackColor = $modelos.BackColor; $termos.ForeColor = $janela.ForeColor
        $termos.BorderStyle = 'FixedSingle'; $termos.SetBounds(14, 254, 390, 145)
        $clausulas = @($politica.clauses | ForEach-Object {
            if ($_ -is [string]) { [string]$_ } else { [string]$_.text }
        })
        $termos.Text = [string]$politica.title + ' · v' + [string]$politica.version + "`r`n`r`n" +
            ($clausulas -join "`r`n`r`n") + "`r`n`r`nSHA-256: " + [string]$politica.digest
        if ($politica.PSObject.Properties['notes']) {
            $termos.AppendText("`r`n`r`n" + (@($politica.notes) -join "`r`n`r`n"))
        }
        $termos.Add_LinkClicked({ param($controle, $ev)
            if ($ev.LinkText -match '^https?://') { Start-Process $ev.LinkText }
        })
        $grupo.Controls.Add($termos)
        $aceite = New-Object System.Windows.Forms.CheckBox
        $aceite.Name = 'aceite'
        $aceite.Text = (T 'Li e aceito os termos e as licenças deste plugin.')
        $aceite.SetBounds(14, 407, 390, 42); $grupo.Controls.Add($aceite)
        $linha = @{ id = $id; Selecionado = $selecionado; Origem = $origem
            Arquivo = $arquivo; Procurar = $procurar; Pasta = $pasta; Aceite = $aceite }
        $estado.Linhas += $linha
        $alterar = { $Arquivo.Enabled = ($Origem.SelectedIndex -eq 1)
            $Procurar.Enabled = $Arquivo.Enabled; $Pasta.Enabled = $Arquivo.Enabled }.GetNewClosure()
        # Capture each row's controls, rather than the last loop iteration.
        $origem.Add_SelectedIndexChanged($alterar)
        $origem.SelectedIndex = $(if ($Offline) { 1 } else { 0 })
        $escolherZip = { $d = New-Object System.Windows.Forms.OpenFileDialog
            $d.Title = (T 'Escolha o pacote offline deste plugin')
            $d.Filter = 'ZIP (*.zip)|*.zip'; $d.CheckFileExists = $true
            if ($d.ShowDialog($janela) -eq 'OK') { $arquivo.Text = $d.FileName }
            $d.Dispose() }.GetNewClosure()
        $procurar.Add_Click($escolherZip)
        $escolherPasta = { $d = New-Object System.Windows.Forms.FolderBrowserDialog
            $d.Description = (T 'Escolha a pasta do pacote offline deste plugin')
            if ($d.ShowDialog($janela) -eq 'OK') { $arquivo.Text = $d.SelectedPath }
            $d.Dispose() }.GetNewClosure()
        $pasta.Add_Click($escolherPasta)
        foreach ($pacote in $PacotesOffline) {
            $nome = [System.IO.Path]::GetFileName($pacote)
            $padrao = $(if ($id -eq 'neuro-rt') { '(?i)NEURO[_ -]?RT' } else { '(?i)LUNG[_ -]?RT' })
            if ($nome -match $padrao) {
                $selecionado.Checked = $true; $origem.SelectedIndex = 1; $arquivo.Text = $pacote
            }
        }
        $n++
    }
    $nota = New-Object System.Windows.Forms.Label
    $nota.Text = (T 'Sem internet: selecione o pacote de cada plugin. Nenhum modelo é baixado sem seu aceite.')
    $nota.SetBounds(20, 578, 860, 40); $janela.Controls.Add($nota)
    $instalar = New-Object System.Windows.Forms.Button
    $instalar.Name = 'instalar-plugins'
    $instalar.Text = (T 'Instalar os selecionados')
    $instalar.SetBounds(635, 625, 245, 32); $instalar.FlatStyle = 'Flat'
    $instalar.BackColor = [System.Drawing.Color]::FromArgb(18, 135, 63)
    $instalar.ForeColor = [System.Drawing.Color]::White; $janela.Controls.Add($instalar)
    $pular = New-Object System.Windows.Forms.Button
    $pular.Text = (T 'Continuar somente com a suíte')
    $pular.SetBounds(320, 625, 300, 32); $pular.FlatStyle = 'Flat'
    $pular.BackColor = [System.Drawing.Color]::FromArgb(15, 23, 41)
    $pular.ForeColor = $janela.ForeColor; $janela.Controls.Add($pular)
    $pular.DialogResult = 'Cancel'; $janela.CancelButton = $pular
    $instalar.Add_Click({
        try {
            $escolhas = @($estado.Linhas | Where-Object { $_.Selecionado.Checked } | ForEach-Object {
                @{ id = $_.id; source = $(if ($_.Origem.SelectedIndex -eq 0) { 'online' } else { $_.Arquivo.Text })
                   accepted = [bool]$_.Aceite.Checked }
            })
            if (-not $escolhas.Count) { throw (T 'Selecione um plugin ou continue somente com a suíte.') }
            $estado.Plano = Novo-PlanoPluginsSuite -Catalogo $Catalogo -Escolhas $escolhas
            $janela.DialogResult = 'OK'; $janela.Close()
        } catch {
            [void][System.Windows.Forms.MessageBox]::Show($janela, $_.Exception.Message,
                (T 'Plugins opcionais'), 'OK', 'Warning')
        }
    }.GetNewClosure())
    try {
        if ($Owner) { $resultado = $janela.ShowDialog($Owner) }
        else { $resultado = $janela.ShowDialog() }
        if ($resultado -eq 'OK') { return $estado.Plano }
        return $null
    } finally { $janela.Dispose() }
}

function Texto-ProgressoPluginsSuite {
    param([AllowEmptyString()][string]$Linha)
    if (-not $Linha.StartsWith('{')) { return $Linha }
    try { $evento = $Linha | ConvertFrom-Json } catch { return $Linha }
    if (Get-Command Sessao -ErrorAction SilentlyContinue) { Sessao ('plugin: ' + $Linha) }
    $valores = @{}
    foreach ($prop in $evento.PSObject.Properties) { $valores[$prop.Name] = $prop.Value }
    if ($valores.ContainsKey('plugins')) {
        return (@($valores.plugins | ForEach-Object {
            $nome = $(if ($_.id -eq 'neuro-rt') { 'NEURO RT' } else { 'LUNG RT' })
            if ($_.ok) { $nome + ': ' + (T 'Preparo concluído.') }
            else { $nome + ': ' + (T 'Não foi possível concluir o preparo.') + ' ' + [string]$_.reason }
        }) -join ' | ')
    }
    $etapa = [string]$valores.stage
    if ($etapa -eq 'resources' -and $valores.resource_stage) { $etapa = [string]$valores.resource_stage }
    if ($valores.state -eq 'failed') { $etapa = 'failed' }
    $texto = switch ($etapa) {
        'checking' { T 'Conferindo o plugin e os recursos já instalados.' }
        'preparing' { T 'Preparando os recursos que faltam.' }
        'downloading' { T 'Baixando os recursos que faltam.' }
        'extracting' { T 'Extraindo os recursos do pacote.' }
        'verifying' { T 'Conferindo a integridade dos arquivos.' }
        'validating' { T 'Conferindo a integridade dos arquivos.' }
        'activating' { T 'Ativando o plugin nesta suíte.' }
        'complete' { T 'Preparo concluído.' }
        'failed' { T 'Não foi possível concluir o preparo.' }
        default { T 'Preparando o plugin e seus recursos.' }
    }
    $nome = switch ([string]$valores.plugin_id) { 'neuro-rt' { 'NEURO RT' }; 'lung-rt' { 'LUNG RT' }; default { 'Local Suite' } }
    $rotulo = [string]$valores.resource_label
    if (-not $rotulo) { $rotulo = [string]$valores.label }
    if (-not $rotulo) { $rotulo = [string]$valores.component }
    if ($rotulo) { $texto += ' ' + $rotulo }
    $total = $valores.total_bytes; $baixado = $valores.downloaded_bytes
    if ($valores.resource_total_bytes) { $total = $valores.resource_total_bytes; $baixado = $valores.resource_downloaded_bytes }
    if ($total) {
        $texto += ' ' + ((T '{0}/{1} MB') -f ([math]::Round([double]$baixado / 1000000, 1)),
            ([math]::Round([double]$total / 1000000, 1)))
    }
    $arquivos = $valores.total_files; $prontos = $valores.completed_files
    if ($valores.resource_total_files) { $arquivos = $valores.resource_total_files; $prontos = $valores.resource_completed_files }
    if ($arquivos) { $texto += ' ' + ((T '{0}/{1} arquivos') -f $prontos, $arquivos) }
    if ($valores.reason) { $texto += ' ' + [string]$valores.reason }
    return ($nome + ': ' + $texto)
}

function Instalar-PluginsSuite {
    param([Parameter(Mandatory = $true)][string]$SuiteRoot,
          [Parameter(Mandatory = $true)]$Plano)
    $python = Join-Path $SuiteRoot 'python\python.exe'
    $motor = Join-Path $SuiteRoot 'radai_plugin_bootstrap.py'
    if (-not (Test-Path -LiteralPath $motor -PathType Leaf)) {
        $motor = Join-Path $SuiteRoot 'app\radai_plugin_bootstrap.py'
    }
    if (-not (Test-Path -LiteralPath $python -PathType Leaf) -or
        -not (Test-Path -LiteralPath $motor -PathType Leaf)) {
        throw (T 'O preparo dos plugins não está disponível nesta instalação. A suíte pode ser aberta normalmente.')
    }
    $planoPath = Join-Path ([System.IO.Path]::GetTempPath()) ('radai-plugins-' + [guid]::NewGuid().ToString('N') + '.json')
    try {
        [System.IO.File]::WriteAllText($planoPath, ($Plano | ConvertTo-Json -Depth 8),
            (New-Object System.Text.UTF8Encoding($false)))
        $pi = New-Object System.Diagnostics.ProcessStartInfo
        $pi.FileName = $python
        $pi.Arguments = LinhaDeArgumentos @('-I', '-B', '-u', $motor, '--suite-root', $SuiteRoot, '--selection', $planoPath)
        $pi.WorkingDirectory = $SuiteRoot; $pi.UseShellExecute = $false; $pi.CreateNoWindow = $true
        $pi.RedirectStandardOutput = $true; $pi.RedirectStandardError = $true
        $pi.EnvironmentVariables['PYTHONIOENCODING'] = 'utf-8:replace'
        $pi.EnvironmentVariables['PYTHONUNBUFFERED'] = '1'
        $pi.StandardOutputEncoding = New-Object System.Text.UTF8Encoding($false)
        $pi.StandardErrorEncoding = New-Object System.Text.UTF8Encoding($false)
        $proc = New-Object System.Diagnostics.Process
        try {
            $proc.StartInfo = $pi; [void]$proc.Start()
            # Existing monitor streams both pipes while pumping the same PS UI.
            return (AcompanharProcesso -Proc $proc -FormatarLinha { param($linha) Texto-ProgressoPluginsSuite $linha })
        } finally { $proc.Dispose() }
    } finally {
        Remove-Item -LiteralPath $planoPath -Force -ErrorAction SilentlyContinue
    }
}
