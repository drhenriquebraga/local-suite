# Catálogo e recibo locais. O instalador e o aplicativo mantêm aceites independentes.
function Ler-CatalogoSuite([string]$Arquivo, [string]$Perfil = 'full', [string[]]$Omitidos = @()) {
    $doc = [IO.File]::ReadAllText($Arquivo, [Text.Encoding]::UTF8) | ConvertFrom-Json
    if ($doc.schema -ne 'local-suite/termos/1' -or @($doc.itens).Count -lt 1) { throw 'Catálogo de licenças inválido.' }
    $ids = @{}
    $escolhidos = @{}
    $obrigatorios = @{}
    foreach ($item in $doc.itens) {
        if (-not $item.id -or $ids.ContainsKey([string]$item.id) -or $item.sha256 -notmatch '^[0-9a-f]{64}$') { throw 'Componente sem identidade válida no catálogo.' }
        $ids[[string]$item.id] = [string]$item.sha256
        if (@($item.perfis) -contains $Perfil -and (-not $item.opcional -or $Omitidos -notcontains $item.ferramenta)) {
            $escolhidos[[string]$item.id] = [string]$item.sha256
            if (-not $item.opcional -or $Perfil.StartsWith('plugin-')) { $obrigatorios[[string]$item.id] = [string]$item.sha256 }
        }
    }
    if (-not $escolhidos.Count) { throw "Nenhum componente elegível no perfil $Perfil." }
    return @{doc=$doc; ids=$ids; elegiveis=$escolhidos; exigidos=$obrigatorios; perfil=$Perfil; sha=(Get-FileHash -LiteralPath $Arquivo -Algorithm SHA256).Hash.ToLowerInvariant()}
}

function UsuarioDosTermos {
    return [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
}

function Caminho-ReciboInstalador($Catalogo) {
    return Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) ("Radioterapia.AI\LocalSuite\Termos\instalador\" + $Catalogo.perfil + "\" + $Catalogo.sha + "\LICENCAS_COMPONENTES.json")
}

function Testar-ReciboInstalador([string]$Arquivo, $Catalogo) {
    try {
        $r = [IO.File]::ReadAllText($Arquivo, [Text.Encoding]::UTF8) | ConvertFrom-Json
        if ($r.schema -ne 'local-suite/aceite/1' -or $r.catalogo_sha256 -cne $Catalogo.sha -or
            $r.finalidade -ne 'ensino-pesquisa' -or $r.contexto -ne 'instalador' -or
            $r.usuario_sid -ne (UsuarioDosTermos) -or $r.maquina -ne [Environment]::MachineName -or
            $r.perfil -ne $Catalogo.perfil) { return $false }
        $vistos = @{}
        foreach ($i in $r.itens) {
            $k = [string]$i.id
            if ($vistos.ContainsKey($k) -or -not $Catalogo.elegiveis.ContainsKey($k) -or $i.sha256 -cne $Catalogo.elegiveis[$k]) { return $false }
            $vistos[$k] = $true
        }
        foreach ($k in $Catalogo.exigidos.Keys) { if (-not $vistos.ContainsKey($k)) { return $false } }
        foreach ($g in ($Catalogo.doc.itens | Group-Object ferramenta)) {
            $elegiveis=@($g.Group | Where-Object {$Catalogo.elegiveis.ContainsKey([string]$_.id)})
            $aceitos=@($elegiveis | Where-Object {$vistos.ContainsKey([string]$_.id)})
            if ($aceitos.Count -and $aceitos.Count -ne $elegiveis.Count) { return $false }
        }
        return $true
    } catch { return $false }
}

function Salvar-ReciboInstalador($Catalogo, $Selecionados, [string]$Destino) {
    $itens = @($Selecionados | ForEach-Object { [ordered]@{id=[string]$_.id; sha256=[string]$_.sha256} })
    $registro = [ordered]@{schema='local-suite/aceite/1'; contexto='instalador'; finalidade='ensino-pesquisa'
        catalogo_sha256=$Catalogo.sha; perfil=$Catalogo.perfil; usuario_sid=(UsuarioDosTermos); maquina=[Environment]::MachineName
        utc=[DateTime]::UtcNow.ToString('o'); itens=$itens}
    [void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($Destino))
    $temp = $Destino + '.' + [Guid]::NewGuid().ToString('N') + '.tmp'
    try {
        [IO.File]::WriteAllText($temp, ($registro | ConvertTo-Json -Depth 6), [Text.UTF8Encoding]::new($false))
        if (-not (Testar-ReciboInstalador $temp $Catalogo)) { throw 'O recibo individual não confere com o catálogo.' }
        if ([IO.File]::Exists($Destino)) {
            $anterior=$temp + '.bak'
            try { [IO.File]::Replace($temp, $Destino, $anterior) }
            finally {
                if ([IO.File]::Exists($anterior)) {
                    if ([IO.File]::Exists($Destino)) { [IO.File]::Delete($anterior) }
                    else { [IO.File]::Move($anterior,$Destino) }
                }
            }
        }
        else {
            try { [IO.File]::Move($temp, $Destino) } catch [IO.IOException] {
                if (-not (Testar-ReciboInstalador $Destino $Catalogo)) { throw }
            }
        }
    } finally { if ([IO.File]::Exists($temp)) { [IO.File]::Delete($temp) } }
}

function Nova-JanelaTermosSuite($Catalogo) {
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    $form = [Windows.Forms.Form]::new()
    $form.Text = 'Local Suite | Termos de ensino e pesquisa'
    $form.StartPosition = 'CenterScreen'
    $form.ClientSize = [Drawing.Size]::new(960,640)
    $form.MinimumSize = [Drawing.Size]::new(775,540)
    $form.Font = [Drawing.Font]::new('Segoe UI',10)

    $intro = [Windows.Forms.Label]::new()
    $intro.SetBounds(16,10,920,63)
    $intro.Anchor = 'Top,Left,Right'
    $intro.Text = "A Local Suite destina-se ao ensino e à pesquisa. Cada ferramenta e cada modelo têm termos próprios. Marque as ferramentas selecionadas para este perfil após revisar seus componentes. Os links abrem no navegador somente por sua escolha."
    $form.Controls.Add($intro)
    $split = [Windows.Forms.SplitContainer]::new()
    $split.SetBounds(16,76,925,475)
    $split.Anchor = 'Top,Bottom,Left,Right'
    $split.SplitterDistance = 320
    $form.Controls.Add($split)

    $lista = [Windows.Forms.CheckedListBox]::new()
    $lista.Dock = 'Fill'
    $lista.CheckOnClick = $true
    $split.Panel1.Controls.Add($lista)
    $painel = [Windows.Forms.TableLayoutPanel]::new()
    $painel.Dock = 'Fill'
    $painel.RowCount=3; $painel.ColumnCount=1
    [void]$painel.RowStyles.Add([Windows.Forms.RowStyle]::new('Absolute',38))
    [void]$painel.RowStyles.Add([Windows.Forms.RowStyle]::new('Percent',100))
    [void]$painel.RowStyles.Add([Windows.Forms.RowStyle]::new('Absolute',90))
    $split.Panel2.Controls.Add($painel)
    $componentes = [Windows.Forms.ComboBox]::new()
    $componentes.DropDownStyle='DropDownList'; $componentes.Dock='Fill'
    $painel.Controls.Add($componentes,0,0)
    $detalhes = [Windows.Forms.TextBox]::new()
    $detalhes.Multiline=$true; $detalhes.ReadOnly=$true; $detalhes.ScrollBars='Vertical'; $detalhes.Dock='Fill'
    $painel.Controls.Add($detalhes,0,1)
    $links = [Windows.Forms.FlowLayoutPanel]::new()
    $links.AutoScroll=$true; $links.Dock='Fill'
    $painel.Controls.Add($links,0,2)

    $avancar = [Windows.Forms.Button]::new()
    $avancar.Text='Registrar os aceites'
    $avancar.Anchor='Bottom,Right'; $avancar.SetBounds(745,594,195,32)
    $avancar.Enabled=$false
    $avancar.DialogResult='OK'
    $form.Controls.Add($avancar)
    $cancelar=[Windows.Forms.Button]::new()
    $cancelar.Text='Cancelar'; $cancelar.Anchor='Bottom,Right'; $cancelar.SetBounds(630,594,108,32)
    $cancelar.DialogResult='Cancel'; $form.Controls.Add($cancelar); $form.CancelButton=$cancelar
    $progresso=[Windows.Forms.Label]::new()
    $progresso.Anchor='Bottom,Left'; $progresso.SetBounds(16,600,575,28)
    $form.Controls.Add($progresso)
    $uso = [Windows.Forms.CheckBox]::new()
    $uso.Anchor='Bottom,Left,Right'; $uso.SetBounds(16,556,910,34)
    $uso.Text='Usarei esta instalação para ensino e pesquisa, de acordo com os termos das ferramentas selecionadas.'
    $form.Controls.Add($uso)

    $grupos = @( $Catalogo.doc.itens | Group-Object ferramenta | Sort-Object Name )
    $obrigatorios = @{}
    $elegiveis = @{}
    for ($n=0; $n -lt $grupos.Count; $n++) {
        $linhas = @($grupos[$n].Group)
        $selecionados = @($linhas | Where-Object { $Catalogo.exigidos.ContainsKey([string]$_.id) })
        $possiveis = @($linhas | Where-Object { $Catalogo.elegiveis.ContainsKey([string]$_.id) })
        $rotulo = [string]$grupos[$n].Name
        $cabeca = @($linhas | Where-Object { $_.id -eq $grupos[$n].Name } | Select-Object -First 1)
        if ($cabeca.Count) { $rotulo=$cabeca[0].titulo }
        if ($possiveis.Count) { $elegiveis[$n]=$true }
        if ($selecionados.Count) { $obrigatorios[$n]=$true } elseif ($possiveis.Count) { $rotulo += ' (opcional)' } else { $rotulo += ' (consulta)' }
        [void]$lista.Items.Add($rotulo)
    }
    $estado = [pscustomobject]@{janela=$form; catalogo=$Catalogo; lista=$lista; grupos=$grupos; necessarios=$obrigatorios; disponiveis=$elegiveis
        componentes=$componentes; detalhes=$detalhes; links=$links; avancar=$avancar; progresso=$progresso; finalidade=$uso}
    $form.Tag=$estado; $lista.Tag=$estado; $componentes.Tag=$estado; $uso.Tag=$estado
    $uso.add_CheckedChanged({
        param($s,$e)
        $u=$s.Tag
        $faltam=@($u.necessarios.Keys | Where-Object {-not $u.lista.GetItemChecked([int]$_)})
        $u.avancar.Enabled=($s.Checked -and $faltam.Count -eq 0)
    })
    $progresso.Text = "0 de " + $obrigatorios.Count + " ferramentas aceitas"
    $lista.add_ItemCheck({
        param($s,$e)
        $u=$s.Tag
        if (-not $u.disponiveis.ContainsKey([int]$e.Index)) { $e.NewValue='Unchecked'; return }
        $total=0
        foreach ($i in $u.necessarios.Keys) {
            if ($i -eq $e.Index) { if ($e.NewValue -eq 'Checked') { $total++ } }
            elseif ($s.GetItemChecked([int]$i)) { $total++ }
        }
        $u.avancar.Enabled=($total -eq $u.necessarios.Count -and $u.finalidade.Checked)
        $u.progresso.Text="$total de " + $u.necessarios.Count + " ferramentas aceitas"
    })
    $lista.add_SelectedIndexChanged({
        param($s,$e)
        if ($s.SelectedIndex -lt 0) { return }
        $u=$s.Tag
        $u.componentes.Items.Clear()
        foreach ($item in $u.grupos[$s.SelectedIndex].Group) {
            $nota=if ($u.catalogo.elegiveis.ContainsKey([string]$item.id)) {''} else {' (consulta)'}
            [void]$u.componentes.Items.Add(([string]$item.titulo + $nota))
        }
        $u.componentes.SelectedIndex=0
    })
    $componentes.add_SelectedIndexChanged({
        param($s,$e)
        $u=$s.Tag
        if ($s.SelectedIndex -lt 0 -or $u.lista.SelectedIndex -lt 0) { return }
        $item=@($u.grupos[$u.lista.SelectedIndex].Group)[$s.SelectedIndex]
        $u.detalhes.Text=@(
            $item.titulo, $item.finalidade, '',
            ('Autoria: ' + $item.autoria), ('Integração: ' + $item.integracao), ('Origem: ' + $item.origem), '',
            ('Licença do código: ' + $item.licenca_codigo), ('Licença dos pesos: ' + $item.licenca_pesos),
            ('Versões: ' + (@($item.versoes) -join ', ')), $item.observacoes
        ) -join [Environment]::NewLine
        while ($u.links.Controls.Count) { $u.links.Controls[0].Dispose() }
        foreach ($fonte in $item.fontes) {
            $uri=$null
            if (-not [Uri]::TryCreate([string]$fonte.url,[UriKind]::Absolute,[ref]$uri) -or $uri.Scheme -notin @('https','http')) { continue }
            $link=[Windows.Forms.LinkLabel]::new()
            $link.AutoSize=$true; $link.Text=[string]$fonte.rotulo; $link.Tag=$uri.AbsoluteUri
            $link.add_LinkClicked({param($sender,$evt) Start-Process -FilePath ([string]$sender.Tag)})
            $u.links.Controls.Add($link)
        }
    })
    if ($lista.Items.Count) { $lista.SelectedIndex=0 }
    return $form
}

function Solicitar-TermosSuite([string]$Arquivo, [string]$Perfil = 'full', [switch]$Revisar, [string[]]$Omitidos = @()) {
    $cat = Ler-CatalogoSuite $Arquivo $Perfil $Omitidos
    $recibo = Caminho-ReciboInstalador $cat
    if (-not $Revisar -and (Testar-ReciboInstalador $recibo $cat)) { return $recibo }
    $f = Nova-JanelaTermosSuite $cat
    try {
        if ($f.ShowDialog() -ne [Windows.Forms.DialogResult]::OK) { return $null }
        $itens = foreach ($i in $f.Tag.lista.CheckedIndices) {
            $f.Tag.grupos[$i].Group | Where-Object { $cat.elegiveis.ContainsKey([string]$_.id) }
        }
        Salvar-ReciboInstalador $cat @($itens) $recibo
        return $recibo
    } finally { $f.Dispose() }
}

function Solicitar-TermosDoZip([string]$Zip) {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $origem = [IO.Compression.ZipFile]::OpenRead($Zip)
    $tmp = [IO.Path]::GetTempFileName()
    try {
        $entrada = $origem.GetEntry('LOCAL_SUITE/data/licencas_suite.json')
        if (-not $entrada -or $entrada.Length -gt 16MB) { throw 'O pacote não tem um catálogo de licenças válido.' }
        [IO.Compression.ZipFileExtensions]::ExtractToFile($entrada,$tmp,$true)
        $perfil = 'full'
        $p = $origem.GetEntry('LOCAL_SUITE/suite-profile.json')
        if ($p) {
            if ($p.Length -gt 64KB) { throw 'Perfil de pacote inválido.' }
            $reader = [IO.StreamReader]::new($p.Open())
            try { $perfil = ($reader.ReadToEnd() | ConvertFrom-Json).profile } finally { $reader.Dispose() }
        }
        $omitidos = @('cads_open','moose','nv_segment_ct' | Where-Object {
            $pre = 'LOCAL_SUITE/modelos/' + $_ + '/'
            -not ($origem.Entries | Where-Object { $_.FullName.StartsWith($pre, [StringComparison]::OrdinalIgnoreCase) } | Select-Object -First 1)
        })
        return (Solicitar-TermosSuite $tmp $perfil -Omitidos $omitidos)
    } finally {
        $origem.Dispose()
        [IO.File]::Delete($tmp)
    }
}


