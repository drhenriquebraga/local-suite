# A interface e a montagem privada usam o mesmo critério de consentimento material.
function Hash-TextoTermos([string]$Texto) {
    $hash=[Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($hash.ComputeHash([Text.Encoding]::UTF8.GetBytes($Texto)))).Replace('-','').ToLowerInvariant() }
    finally { $hash.Dispose() }
}

function Ler-CatalogoSuite([string]$Arquivo,[string]$Perfil='full',[string[]]$Omitidos=@(),[string[]]$Recursos=@()) {
    if ($Perfil -notin @('full','lung-rt','plugin-neuro','plugin-lung')) { throw 'Perfil de instalação inválido.' }
    $doc=[IO.File]::ReadAllText($Arquivo,[Text.Encoding]::UTF8) | ConvertFrom-Json
    $arqPolitica=Join-Path (Split-Path -Parent $Arquivo) 'termos_instalador.json'
    if (-not [IO.File]::Exists($arqPolitica)) {
        $arqPolitica=Join-Path (Split-Path -Parent $PSScriptRoot) 'app/data/termos_instalador.json'
    }
    $politica=[IO.File]::ReadAllText($arqPolitica,[Text.Encoding]::UTF8) | ConvertFrom-Json
    if ($doc.schema -ne 'local-suite/termos/1' -or $politica.schema -ne 'local-suite/condicoes-instalador/1') { throw 'Catálogo de termos incompatível.' }
    $ids=@{}; $elegiveis=@{}; $exigidos=@{}; $condicoes=@{}; $opcionais=@{}
    $hash=[Security.Cryptography.SHA256]::Create()
    try { $sha=([BitConverter]::ToString($hash.ComputeHash([IO.File]::ReadAllBytes($Arquivo)))).Replace('-','').ToLowerInvariant() }
    finally { $hash.Dispose() }
    foreach ($item in $doc.itens) {
        $id=[string]$item.id; $grupo=[string]$item.ferramenta
        if (!$id -or $ids.ContainsKey($id) -or $item.sha256 -notmatch '^[0-9a-f]{64}$') { throw 'Componente inválido no catálogo.' }
        $ids[$id]=$item.sha256
        if (@($item.perfis) -notcontains $Perfil) { continue }
        if ($Recursos -and $item.PSObject.Properties['selecao_plugin'] -and $Recursos -notcontains $item.selecao_plugin) { continue }
        $elegiveis[$id]=$item
        if ($item.opcional) { $opcionais[$grupo]=$true } else { $exigidos[$id]=$item.sha256 }
        $def=$politica.condicoes.PSObject.Properties[$id]
        if ($def) {
            $d=$def.Value
            $texto=@($id,$item.licenca_codigo,$item.licenca_pesos,$d.revisao,$d.url,$d.en) -join [char]10
            $condicoes[$id]=@{item=$item; def=$d; hash=(Hash-TextoTermos $texto)}
        }
    }
    if (-not $elegiveis.Count) { throw 'Perfil de instalação vazio.' }
    return @{doc=$doc; politica=$politica; perfil=$Perfil; ids=$ids; exigidos=$exigidos; elegiveis=$elegiveis
        condicoes=$condicoes; opcionais=$opcionais; indisponiveis=@($Omitidos | Where-Object {$_ -and $opcionais.ContainsKey($_)})
        sha=$sha; arquivo=$Arquivo}
}

function UsuarioDosTermos { return [Security.Principal.WindowsIdentity]::GetCurrent().User.Value }

function Caminho-ReciboInstalador($Catalogo) {
    return Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) ('Radioterapia.AI\LocalSuite\Termos\instalador\'+$Catalogo.perfil+'\vigente\LICENCAS_COMPONENTES.json')
}

function Ler-DecisaoInstalador([string]$Arquivo,$Catalogo) {
    if (-not $Arquivo -or -not [IO.File]::Exists($Arquivo)) { return $null }
    try {
        $r=[IO.File]::ReadAllText($Arquivo,[Text.Encoding]::UTF8) | ConvertFrom-Json
        if ($r.contexto -cne 'instalador' -or $r.finalidade -cne 'ensino-pesquisa' -or
            $r.usuario_sid -cne (UsuarioDosTermos) -or $r.maquina -ne [Environment]::MachineName -or $r.perfil -ne $Catalogo.perfil) { return $null }
        $sel=@{}; $vistos=@{}
        foreach ($i in $r.itens) {
            if ($vistos.ContainsKey([string]$i.id) -or $i.sha256 -cnotmatch '^[0-9a-f]{64}$') { return $null }
            $vistos[[string]$i.id]=[string]$i.sha256
        }
        if ($r.schema -eq 'local-suite/aceite/2') {
            if ($r.revisao_finalidade -cne $Catalogo.politica.revisao_finalidade) { return $null }
            if (-not $r.PSObject.Properties['omitidos'] -or -not $r.PSObject.Properties['itens']) { return $null }
            $om=@{}
            foreach ($nome in $r.omitidos) {
                if (!$nome -or !$Catalogo.opcionais.ContainsKey($nome) -or $om.ContainsKey($nome)) { return $null }
                $om[$nome]=$true
            }
            return @{provas=$vistos; omitidos=@($r.omitidos); origem=$r.schema; utc=$r.utc}
        }
        if ($r.schema -ne 'local-suite/aceite/1' -or $r.catalogo_sha256 -cne $Catalogo.politica.catalogo_830) { return $null }
        if ($Catalogo.sha -ceq $r.catalogo_sha256) {
            foreach ($k in $Catalogo.exigidos.Keys) { if ($vistos[$k] -cne $Catalogo.ids[$k]) { return $null } }
            foreach ($k in $vistos.Keys) { if ($vistos[$k] -cne $Catalogo.ids[$k]) { return $null } }
        }
        $omitidos=@()
        foreach ($g in $Catalogo.opcionais.Keys) {
            $membros=@($Catalogo.elegiveis.Values | Where-Object {$_.ferramenta -eq $g})
            $marcados=@($membros | Where-Object {$vistos.ContainsKey([string]$_.id)})
            if (-not $marcados.Count) { $omitidos+=$g }
            elseif ($marcados.Count -ne $membros.Count) { return $null }
        }
        foreach ($id in $Catalogo.condicoes.Keys) {
            $d=$Catalogo.condicoes[$id].def
            if ($vistos[$id] -ceq $d.sha_item_830) { $sel[$id]=$d.condicao_830 }
        }
        return @{provas=$sel; omitidos=$omitidos; origem=$r.schema; utc=$r.utc}
    } catch { return $null }
}

function DecisaoAnteriorSuite($Catalogo) {
    $destino=Caminho-ReciboInstalador $Catalogo
    $atual=Ler-DecisaoInstalador $destino $Catalogo
    if ($atual) { return $atual }
    $pai=Split-Path -Parent (Split-Path -Parent $destino)
    $legado=Join-Path $pai ($Catalogo.politica.catalogo_830+'\LICENCAS_COMPONENTES.json')
    return (Ler-DecisaoInstalador $legado $Catalogo)
}

function PendenciasDosTermos($Catalogo,$Decisao,[string[]]$Omitidos=@()) {
    foreach ($id in $Catalogo.condicoes.Keys) {
        $c=$Catalogo.condicoes[$id]
        if (($Catalogo.indisponiveis -contains $c.item.ferramenta) -or ($Omitidos -contains $c.item.ferramenta)) { continue }
        if (-not $Decisao -or $Decisao.provas[$id] -cne $c.hash) { $id }
    }
}

function Testar-ReciboInstalador([string]$Arquivo,$Catalogo) {
    $decisao=Ler-DecisaoInstalador $Arquivo $Catalogo
    return [bool]($decisao -and @(PendenciasDosTermos $Catalogo $decisao $decisao.omitidos).Count -eq 0)
}

function Gravar-DecisaoSuite($Catalogo,[string[]]$Omitidos=@(),$Anterior=$null,[switch]$Migrar) {
    $destino=Caminho-ReciboInstalador $Catalogo
    $provas=@{}
    if ($Anterior) { foreach ($id in $Anterior.provas.Keys) { $provas[$id]=$Anterior.provas[$id] } }
    if (-not $Migrar) {
        foreach ($id in $Catalogo.condicoes.Keys) {
            $c=$Catalogo.condicoes[$id]
            if ($Omitidos -notcontains $c.item.ferramenta -and $Catalogo.indisponiveis -notcontains $c.item.ferramenta) { $provas[$id]=$c.hash }
        }
    }
    $data=if ($Migrar) {$Anterior.utc} else {[DateTime]::UtcNow.ToString('o')}
    $registro=[ordered]@{schema='local-suite/aceite/2'; contexto='instalador'; finalidade='ensino-pesquisa'
        revisao_finalidade=$Catalogo.politica.revisao_finalidade; catalogo_sha256=$Catalogo.sha; perfil=$Catalogo.perfil
        usuario_sid=(UsuarioDosTermos); maquina=[Environment]::MachineName; utc=$data
        omitidos=@($Omitidos | Sort-Object -Unique)
        itens=@(foreach ($id in ($provas.Keys | Sort-Object)) { [ordered]@{id=$id;sha256=$provas[$id]} })}
    if ($Migrar) { $registro['origem']=$Anterior.origem }
    [void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($destino))
    $tmp=$destino+'.'+[Guid]::NewGuid().ToString('N')+'.tmp'
    try {
        [IO.File]::WriteAllText($tmp,($registro | ConvertTo-Json -Depth 5),[Text.UTF8Encoding]::new($false))
        if (-not (Testar-ReciboInstalador $tmp $Catalogo)) { throw 'Falha ao verificar os termos registrados.' }
        if ([IO.File]::Exists($destino)) {
            $bak=$tmp+'.bak'
            try { [IO.File]::Replace($tmp,$destino,$bak) } finally { if ([IO.File]::Exists($bak) -and [IO.File]::Exists($destino)) { [IO.File]::Delete($bak) } }
        } else {
            try { [IO.File]::Move($tmp,$destino) } catch [IO.IOException] {
                if (-not (Testar-ReciboInstalador $destino $Catalogo)) { throw }
            }
        }
    } finally { if ([IO.File]::Exists($tmp)) { [IO.File]::Delete($tmp) } }
    return $destino
}

function Obter-ReciboVigente([string]$Arquivo,[string]$Perfil='full',[string[]]$Omitidos=@(),[string[]]$Recursos=@()) {
    $c=Ler-CatalogoSuite $Arquivo $Perfil $Omitidos $Recursos
    $anterior=DecisaoAnteriorSuite $c
    if (-not $anterior -or @(PendenciasDosTermos $c $anterior $anterior.omitidos).Count) { return $null }
    if ($anterior.origem -eq 'local-suite/aceite/1') { return (Gravar-DecisaoSuite $c $anterior.omitidos $anterior -Migrar) }
    return (Caminho-ReciboInstalador $c)
}


function IdiomaDosTermos {
    if (Get-Command Idioma-Atual -ErrorAction SilentlyContinue) { return (Idioma-Atual) }
    if ($env:RADAI_IDIOMA) { return $env:RADAI_IDIOMA }
    return 'en'
}

function Desenhar-TermosSuite($Painel) {
    $s=$Painel.Tag
    $lingua=IdiomaDosTermos
    $trad=$s.cat.politica.ui.PSObject.Properties[$lingua]
    $ui=if ($trad) {$trad.Value} else {$s.cat.politica.ui.en}
    $s.btn.Text=$ui.aceitar; $s.opcoes.Text=$ui.opcoes; $s.titulo.Text=$ui.titulo
    $s.declaracao.Text=$ui.dec
    $omitidos=@($s.cat.indisponiveis)+@($s.menu.Items | Where-Object {-not $_.Checked} | ForEach-Object {$_.Tag})
    $s.omitidos=@($omitidos | Sort-Object -Unique)
    $pendentes=@(PendenciasDosTermos $s.cat $s.anterior $s.omitidos)
    $r=$s.texto; $r.Clear()
    $nl=[Environment]::NewLine
    if ($s.anterior -and $pendentes.Count) { $r.AppendText($ui.novos+$nl+$nl) }
    foreach ($grupo in @('infra','models','plugins')) {
        $ativos=@($s.cat.condicoes.Keys | Where-Object {
            $c=$s.cat.condicoes[$_]
            $c.def.grupo -eq $grupo -and $s.omitidos -notcontains $c.item.ferramenta -and
                (-not $s.anterior -or -not $pendentes.Count -or $pendentes -contains $_)
        } | Sort-Object)
        if (-not $ativos.Count) { continue }
        $r.SelectionColor=[Drawing.Color]::LightSkyBlue
        $r.SelectionFont=$s.negrito
        $r.AppendText($ui.$grupo+$nl)
        foreach ($id in $ativos) {
            $c=$s.cat.condicoes[$id]; $r.SelectionColor=[Drawing.Color]::White; $r.SelectionFont=$s.fonte
            $rotulo=if ($grupo -eq 'infra') { $c.item.licenca_codigo } else { $c.item.licenca_pesos }
            $r.AppendText($c.item.titulo+'  —  '+$rotulo+$nl)
            $obs=if ($lingua -eq 'pt-BR') { $c.def.pt } else { $c.def.en }
            if ($obs) { $r.AppendText($obs+$nl) }
            $r.AppendText($c.def.url+$nl+$nl)
        }
    }
    $r.SelectionColor=[Drawing.Color]::Silver
    $r.AppendText($ui.creditos+$nl)
    $r.SelectionStart=0; $r.SelectionLength=0; $r.ScrollToCaret()
}

function Novo-PainelTermosSuite($Catalogo) {
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    $anterior=DecisaoAnteriorSuite $Catalogo
    $painel=[Windows.Forms.TableLayoutPanel]::new()
    $painel.Dock='Fill'; $painel.Padding=[Windows.Forms.Padding]::new(16); $painel.BackColor=[Drawing.Color]::FromArgb(20,27,37)
    $painel.RowCount=4; $painel.ColumnCount=1
    foreach ($altura in @(35,0,49,46)) {
        $tipo=if ($altura) {'Absolute'} else {'Percent'}
        $valor=if ($altura) {$altura} else {100}
        [void]$painel.RowStyles.Add([Windows.Forms.RowStyle]::new($tipo,$valor))
    }
    $fonte=[Drawing.Font]::new('Segoe UI',10); $negrito=[Drawing.Font]::new('Segoe UI',11,[Drawing.FontStyle]::Bold)
    $titulo=[Windows.Forms.Label]::new(); $titulo.Dock='Fill'; $titulo.Font=$negrito; $titulo.ForeColor=[Drawing.Color]::White
    $painel.Controls.Add($titulo,0,0)
    $texto=[Windows.Forms.RichTextBox]::new(); $texto.Dock='Fill'; $texto.ReadOnly=$true; $texto.DetectUrls=$true
    $texto.Font=$fonte; $texto.ScrollBars='Vertical'; $texto.BackColor=[Drawing.Color]::FromArgb(10,14,19); $texto.ForeColor=[Drawing.Color]::White
    $texto.add_LinkClicked({param($sender,$evento)
        $endereco=$null
        if ([Uri]::TryCreate($evento.LinkText,[UriKind]::Absolute,[ref]$endereco) -and $endereco.Scheme -eq 'https') {
            Start-Process -FilePath $endereco.AbsoluteUri
        }
    })
    $painel.Controls.Add($texto,0,1)
    $declaracao=[Windows.Forms.Label]::new(); $declaracao.Dock='Fill'; $declaracao.TextAlign='MiddleLeft'
    $declaracao.Font=$fonte; $declaracao.ForeColor=[Drawing.Color]::White
    $painel.Controls.Add($declaracao,0,2)
    $acoes=[Windows.Forms.FlowLayoutPanel]::new(); $acoes.Dock='Fill'; $acoes.WrapContents=$false
    $btn=[Windows.Forms.Button]::new(); $btn.AutoSize=$true; $btn.MinimumSize=[Drawing.Size]::new(180,34)
    $btn.Padding=[Windows.Forms.Padding]::new(10,0,10,0); $btn.FlatStyle='Flat'; $btn.Font=$negrito
    $btn.BackColor=[Drawing.Color]::FromArgb(22,133,83); $btn.ForeColor=[Drawing.Color]::White
    $acoes.Controls.Add($btn)
    $ops=[Windows.Forms.Button]::new(); $ops.AutoSize=$true; $ops.Height=34; $ops.FlatStyle='Flat'; $ops.ForeColor=[Drawing.Color]::White
    $menu=[Windows.Forms.ContextMenuStrip]::new()
    foreach ($g in ($Catalogo.opcionais.Keys | Sort-Object)) {
        if ($Catalogo.indisponiveis -contains $g) { continue }
        $a=[Windows.Forms.ToolStripMenuItem]::new(); $a.Text=$Catalogo.elegiveis[$g].titulo; $a.Tag=$g
        $a.CheckOnClick=$true; $a.Checked=if ($anterior) {$anterior.omitidos -notcontains $g} else {$true}
        [void]$menu.Items.Add($a)
    }
    $ops.Tag=$menu; $ops.add_Click({param($s,$e) $s.Tag.Show($s,0,$s.Height)})
    $ops.Visible=($menu.Items.Count -gt 0); $acoes.Controls.Add($ops)
    $painel.Controls.Add($acoes,0,3)
    $painel.Tag=@{cat=$Catalogo;anterior=$anterior;texto=$texto;btn=$btn;titulo=$titulo;declaracao=$declaracao;opcoes=$ops;menu=$menu
        fonte=$fonte;negrito=$negrito;omitidos=@();recibo='';apos=$null}
    $btn.Tag=$painel; $menu.Tag=$painel
    foreach ($item in $menu.Items) { $item.add_CheckedChanged({param($s,$e) Desenhar-TermosSuite $s.Owner.Tag}) }
    $btn.add_Click({param($s,$e)
        $p=$s.Tag; $estado=$p.Tag
        try {
            $estado.recibo=Gravar-DecisaoSuite $estado.cat $estado.omitidos $estado.anterior
        } catch {
            [void][Windows.Forms.MessageBox]::Show($_.Exception.Message,'Local Suite')
            return
        }
        if ($estado.apos) { & $estado.apos $estado.recibo }
    })
    $painel.add_Disposed({param($s,$e)
        if ($s.Tag) { $s.Tag.menu.Dispose(); $s.Tag.fonte.Dispose(); $s.Tag.negrito.Dispose() }
    })
    Desenhar-TermosSuite $painel
    return $painel
}

function Nova-JanelaTermosSuite($Catalogo) {
    $painel=Novo-PainelTermosSuite $Catalogo
    $form=[Windows.Forms.Form]::new(); $form.Text='Local Suite'; $form.StartPosition='CenterScreen'
    $form.ClientSize=[Drawing.Size]::new(860,550); $form.MinimumSize=[Drawing.Size]::new(590,360)
    $form.Controls.Add($painel); $form.Tag=$painel
    $painel.Tag.apos={param($recibo) $form.DialogResult='OK'}.GetNewClosure()
    return $form
}

function Solicitar-TermosSuite([string]$Arquivo,[string]$Perfil='full',[switch]$Revisar,[string[]]$Omitidos=@(),[string[]]$Recursos=@()) {
    if (-not $Revisar) {
        $recibo=Obter-ReciboVigente $Arquivo $Perfil $Omitidos $Recursos
        if ($recibo) { return $recibo }
    }
    $cat=Ler-CatalogoSuite $Arquivo $Perfil $Omitidos $Recursos
    $f=Nova-JanelaTermosSuite $cat
    try {
        if ($f.ShowDialog() -ne [Windows.Forms.DialogResult]::OK) { return $null }
        return $f.Tag.Tag.recibo
    } finally { $f.Dispose() }
}

function Ler-TermosDoZip([string]$Zip) {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $origem=[IO.Compression.ZipFile]::OpenRead($Zip)
    $pasta=Join-Path ([IO.Path]::GetTempPath()) ('suite-termos-'+[Guid]::NewGuid().ToString('N'))
    try {
        [void][IO.Directory]::CreateDirectory($pasta)
        foreach ($nome in @('licencas_suite.json','termos_instalador.json')) {
            $alvo=Join-Path $pasta $nome
            $entrada=$origem.GetEntry('LOCAL_SUITE/data/'+$nome)
            if (-not $entrada -and $nome -eq 'termos_instalador.json') {
                [IO.File]::Copy((Join-Path (Split-Path -Parent $PSScriptRoot) ('app/data/'+$nome)),$alvo)
            } else {
                if (-not $entrada -or $entrada.Length -gt 16MB) { throw 'Bundle sem catálogo de termos válido.' }
                [IO.Compression.ZipFileExtensions]::ExtractToFile($entrada,$alvo)
            }
        }
        $perfil='full'
        $p=$origem.GetEntry('LOCAL_SUITE/suite-profile.json')
        if ($p) {
            if ($p.Length -gt 64KB) { throw 'Perfil do pacote inválido.' }
            $rd=[IO.StreamReader]::new($p.Open())
            try { $perfil=($rd.ReadToEnd()|ConvertFrom-Json).profile } finally { $rd.Dispose() }
        }
        $tem=@{}
        foreach ($entry in $origem.Entries) { if ($entry.FullName -match '^LOCAL_SUITE/modelos/(cads_open|moose|nv_segment_ct)/') { $tem[$Matches[1]]=$true } }
        return @{pasta=$pasta; arquivo=(Join-Path $pasta 'licencas_suite.json');perfil=$perfil; omitidos=@('cads_open','moose','nv_segment_ct' | Where-Object {-not $tem.ContainsKey($_)})}
    } catch { [IO.Directory]::Delete($pasta,$true); throw } finally { $origem.Dispose() }
}

function Solicitar-TermosDoZip([string]$Zip) {
    $d=Ler-TermosDoZip $Zip
    try { return (Solicitar-TermosSuite $d.arquivo $d.perfil -Omitidos $d.omitidos) }
    finally { [IO.Directory]::Delete($d.pasta,$true) }
}

