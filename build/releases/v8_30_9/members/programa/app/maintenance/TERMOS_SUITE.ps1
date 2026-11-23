# A interface e a montagem privada usam o mesmo critério de consentimento material.
function Hash-TextoTermos([string]$Texto) {
    $hash=[Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($hash.ComputeHash([Text.Encoding]::UTF8.GetBytes($Texto)))).Replace('-','').ToLowerInvariant() }
    finally { $hash.Dispose() }
}

function Ler-CatalogoSuite([string]$Arquivo,[string]$Perfil='full',[string[]]$Omitidos=@(),[string[]]$Recursos=@()) {
    if ($Perfil -notin @('full','lung-rt','plugin-neuro','plugin-lung','plugin-coronarias')) { throw 'Perfil de instalação inválido.' }
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
        # Antigos catálogos incluíam a DA clínica na base. A seleção de pesquisa é dedicada.
        if ($grupo -eq 'rocards_lad' -and $Perfil -ne 'plugin-coronarias') { $elegiveis.Remove($id); continue }
        if ($item.opcional -and $Perfil -notlike 'plugin-*') { $opcionais[$grupo]=$true } else { $exigidos[$id]=$item.sha256 }
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

# One decision can cover several packages. Receipts retain their original
# scope, so a packaging decision never activates a plugin at the destination.
function ContextosDosTermos([object[]]$Catalogos) {
    foreach ($cat in $Catalogos) {
        $anterior=DecisaoAnteriorSuite $cat
        $omitidos=@($cat.indisponiveis)
        if ($anterior) { $omitidos+=@($anterior.omitidos) }
        $omitidos=@($omitidos | Sort-Object -Unique)
        [pscustomobject]@{cat=$cat; anterior=$anterior; omitidos=$omitidos; recibo=''}
    }
}

function RecibosDosContextos([object[]]$Contextos,[switch]$Confirmado) {
    foreach ($ctx in $Contextos) {
        $c=$ctx.cat
        if ($c.perfil -like 'plugin-*' -and -not $c.condicoes.Count) { continue }
        $faltam=@(PendenciasDosTermos $c $ctx.anterior $ctx.omitidos)
        if (-not $Confirmado -and ($faltam.Count -or -not $ctx.anterior)) { return $false }
    }
    foreach ($ctx in $Contextos) {
        $c=$ctx.cat
        if ($c.perfil -like 'plugin-*' -and -not $c.condicoes.Count) { continue }
        if ($ctx.anterior -and $ctx.anterior.origem -eq 'local-suite/aceite/2' -and
            -not @(PendenciasDosTermos $c $ctx.anterior $ctx.omitidos).Count -and
            -not @(Compare-Object @($ctx.anterior.omitidos) @($ctx.omitidos)).Count) {
            $ctx.recibo=Caminho-ReciboInstalador $c
        } else {
            $ctx.recibo=Gravar-DecisaoSuite $c $ctx.omitidos $ctx.anterior -Migrar:(-not $Confirmado)
        }
    }
    return $true
}

function AtualizarBotaoTermos($Painel) {
    $s=$Painel.Tag
    $s.btn.Enabled=(-not $s.concluido -and -not @($s.caixas.Values | Where-Object {-not $_.Checked}).Count)
}

function Desenhar-TermosSuite($Painel) {
    $s=$Painel.Tag
    $lingua=IdiomaDosTermos
    $trad=$s.cat.politica.ui.PSObject.Properties[$lingua]
    $ui=if ($trad) {$trad.Value} else {$s.cat.politica.ui.en}
    $s.btn.Text=$ui.aceitar; $s.opcoes.Text=$ui.opcoes; $s.titulo.Text=$ui.titulo; $s.declaracao.Text=$ui.dec
    $anterior=@{}
    foreach ($id in $s.caixas.Keys) { $anterior[$id]=$s.caixas[$id].Checked }
    $s.caixas=@{}
    $lista=$s.lista
    $lista.SuspendLayout()
    try {
        while ($lista.Controls.Count) { $lista.Controls[0].Dispose() }
        $lista.RowCount=0
        $itens=@{}
        foreach ($ctx in $s.contextos) {
            if ($ctx.cat -eq $s.cat) {
                $omitidos=@($ctx.cat.indisponiveis)+@($s.menu.Items | Where-Object {-not $_.Checked} | ForEach-Object {$_.Tag})
                $ctx.omitidos=@($omitidos | Sort-Object -Unique)
            }
            foreach ($id in $ctx.cat.condicoes.Keys) {
                $c=$ctx.cat.condicoes[$id]
                if ($ctx.omitidos -notcontains $c.item.ferramenta) { $itens[$id]=$c }
            }
        }
        foreach ($grupo in @('infra','models','plugins')) {
            $ids=@($itens.Keys | Where-Object {$itens[$_].def.grupo -eq $grupo} | Sort-Object)
            if (-not $ids.Count) { continue }
            $cab=[Windows.Forms.Label]::new(); $cab.AutoSize=$true; $cab.Text=$ui.$grupo
            $cab.Font=$s.negrito; $cab.ForeColor=[Drawing.Color]::LightSkyBlue
            $cab.Margin=[Windows.Forms.Padding]::new(8,10,8,2); $lista.Controls.Add($cab)
            foreach ($id in $ids) {
                $c=$itens[$id]; $def=$c.def
                $nome=if ($def.PSObject.Properties['produto']) { $def.produto } else { $c.item.titulo }
                $licenca=if ($def.PSObject.Properties['licenca']) { $def.licenca } elseif ($grupo -eq 'infra') { $c.item.licenca_codigo } else { $c.item.licenca_pesos }
                $cb=[Windows.Forms.CheckBox]::new(); $cb.AutoSize=$true; $cb.Text=$nome+'  —  '+$licenca
                $cb.Font=$s.fonte; $cb.ForeColor=[Drawing.Color]::White; $cb.UseMnemonic=$false
                $cb.Margin=[Windows.Forms.Padding]::new(10,4,8,0)
                $cb.Checked=if ($anterior.ContainsKey($id)) { $anterior[$id] } else { $true }
                $cb.Tag=$Painel; $cb.add_CheckedChanged({ param($sender,$ev) AtualizarBotaoTermos $sender.Tag })
                $s.caixas[$id]=$cb; $lista.Controls.Add($cb)
                $obs=if ($lingua -eq 'pt-BR') { $def.pt } else { $def.en }
                if ($def.PSObject.Properties['trad'] -and $def.trad.PSObject.Properties[$lingua]) { $obs=$def.trad.PSObject.Properties[$lingua].Value }
                if ($obs) {
                    $nota=[Windows.Forms.Label]::new(); $nota.AutoSize=$true; $nota.Text=$obs
                    $nota.ForeColor=[Drawing.Color]::Gainsboro; $nota.Margin=[Windows.Forms.Padding]::new(32,2,8,0)
                    $lista.Controls.Add($nota)
                }
                $endereco=[uri]$def.url
                if ($endereco.Scheme -ne 'https') { throw 'Invalid terms URL.' }
                $link=[Windows.Forms.LinkLabel]::new(); $link.AutoSize=$true
                $link.Text=$endereco.Host; $link.Tag=$endereco; $link.AccessibleDescription=$endereco.AbsoluteUri
                $link.Margin=[Windows.Forms.Padding]::new(32,1,8,4); $link.LinkColor=[Drawing.Color]::LightSkyBlue
                $link.add_LinkClicked({param($sender,$ev) Start-Process -FilePath $sender.Tag.AbsoluteUri})
                $lista.Controls.Add($link)
            }
        }
    } finally { $lista.ResumeLayout($true) }
    AtualizarBotaoTermos $Painel
}

function Novo-PainelTermosSuite($Catalogo,[object[]]$Contextos=@()) {
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    if (-not $Contextos.Count) { $Contextos=@(ContextosDosTermos @($Catalogo)) }
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
    $rolagem=[Windows.Forms.Panel]::new(); $rolagem.Dock='Fill'; $rolagem.AutoScroll=$true
    $rolagem.BackColor=[Drawing.Color]::FromArgb(10,14,19); $rolagem.BorderStyle='FixedSingle'
    $lista=[Windows.Forms.TableLayoutPanel]::new(); $lista.Dock='Top'; $lista.AutoSize=$true
    $lista.AutoSizeMode='GrowAndShrink'; $lista.ColumnCount=1; $lista.GrowStyle='AddRows'
    [void]$lista.ColumnStyles.Add([Windows.Forms.ColumnStyle]::new('Percent',100))
    $lista.add_SizeChanged({param($sender,$ev)
        $largura=[Math]::Max(120,$sender.Width-52)
        foreach ($controle in $sender.Controls) {
            if ($controle.MaximumSize.Width -ne $largura) { $controle.MaximumSize=[Drawing.Size]::new($largura,0) }
        }
    })
    $rolagem.Controls.Add($lista); $painel.Controls.Add($rolagem,0,1)
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
        $a.CheckOnClick=$true; $a.Checked=$Contextos[0].omitidos -notcontains $g
        [void]$menu.Items.Add($a)
    }
    $ops.Tag=$menu; $ops.add_Click({param($s,$e) $s.Tag.Show($s,0,$s.Height)})
    $ops.Visible=($menu.Items.Count -gt 0); $acoes.Controls.Add($ops)
    $painel.Controls.Add($acoes,0,3)
    $painel.Tag=@{cat=$Catalogo;contextos=$Contextos;lista=$lista;caixas=@{};btn=$btn;titulo=$titulo;declaracao=$declaracao;opcoes=$ops;menu=$menu
        fonte=$fonte;negrito=$negrito;concluido=$false;recibo='';apos=$null}
    $btn.Tag=$painel; $menu.Tag=$painel
    foreach ($item in $menu.Items) { $item.add_CheckedChanged({param($s,$e) Desenhar-TermosSuite $s.Owner.Tag}) }
    $btn.add_Click({param($s,$e)
        $p=$s.Tag; $estado=$p.Tag
        if ($estado.concluido -or @($estado.caixas.Values | Where-Object {-not $_.Checked}).Count) { return }
        try {
            [void](RecibosDosContextos $estado.contextos -Confirmado)
            $estado.recibo=$estado.contextos[0].recibo
        } catch {
            [void][Windows.Forms.MessageBox]::Show($_.Exception.Message,'Local Suite')
            return
        }
        $estado.concluido=$true; AtualizarBotaoTermos $p; $estado.opcoes.Enabled=$false; $estado.lista.Enabled=$false
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
    $cat=Ler-CatalogoSuite $Arquivo $Perfil $Omitidos $Recursos
    if ($Perfil -like 'plugin-*' -and -not $cat.condicoes.Count) { return $null }
    if (-not $Revisar) {
        $recibo=Obter-ReciboVigente $Arquivo $Perfil $Omitidos $Recursos
        if ($recibo) { return $recibo }
    }
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

