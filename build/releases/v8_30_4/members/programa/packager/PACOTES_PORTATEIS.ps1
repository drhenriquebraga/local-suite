# GUI de seleção exclusiva para o preparo de arquivos portáteis.
function Novo-FormPacotesPortateis {
    $janela = [Windows.Forms.Form]::new()
    $janela.Text = T 'Montar pacotes do app e dos plugins para levar'
    $janela.StartPosition = 'CenterParent'; $janela.FormBorderStyle = 'FixedDialog'
    $janela.MinimizeBox = $false; $janela.MaximizeBox = $false
    $janela.ClientSize = [Drawing.Size]::new(610,270)
    $janela.BackColor=$script:Cor.Painel; $janela.ForeColor=$script:Cor.Texto
    $itens=[ordered]@{'core'='Local Suite (Core)';'neuro-rt'='NEURO RT';'lung-rt'='LUNG RT';'coronarias'=(T 'Coronárias (ROCardS)')}
    $y=16; $campos=@()
    foreach ($id in $itens.Keys) {
        $selecionar=[Windows.Forms.CheckBox]::new()
        $selecionar.Text=$itens[$id]; $selecionar.Tag=$id; $selecionar.Checked=($id -eq 'core')
        $selecionar.SetBounds(22,$y,560,32); $y+=39
        $janela.Controls.Add($selecionar); $campos+=$selecionar
    }
    $pasta=NovoBotao 'Selecionar pasta de destino' 22 200 338 40 $script:Cor.Ok
    $pasta.DialogResult='OK'; $janela.Controls.Add($pasta)
    $sair=NovoBotao 'Cancelar' 387 200 190 40 $script:Cor.Fraco
    $sair.DialogResult='Cancel'; $janela.Controls.Add($sair); $janela.CancelButton=$sair
    $janela.Tag=@{campos=$campos;btn=$pasta}
    foreach ($campo in $campos) {
        $campo.add_CheckedChanged({param($sender,$evento)
            $s=$sender.FindForm().Tag
            $s.btn.Enabled=@($s.campos|Where-Object {$_.Checked}).Count -gt 0
        })
    }
    return $janela
}

function Selecionar-PacotesPortateis($Owner) {
    $janela=Novo-FormPacotesPortateis
    try {
        if ($janela.ShowDialog($Owner) -ne [Windows.Forms.DialogResult]::OK) { return }
        foreach ($campo in $janela.Tag.campos) { if ($campo.Checked) { $campo.Tag } }
    } finally { $janela.Dispose() }
}

function Montar-PluginsPortateis([string]$Saida,[string[]]$Plugins) {
    if (-not $Plugins.Count) { return }
    $python=$null
    if ($script:Instalado -and $script:Instalado.pasta) {
        $local=Join-Path $script:Instalado.pasta 'python/python.exe'
        if (Test-Path -LiteralPath $local -PathType Leaf) {
            $versao = & $local -B -c "import sys;print(sys.version_info[:2]==(3,10))"
            if ($LASTEXITCODE -eq 0 -and $versao -eq 'True') { $python=$local }
        }
    }
    if (-not $python) {
        $basePython=Join-Path ([IO.Path]::GetTempPath()) 'LocalSuite-PythonPreparo310'
        [void][IO.Directory]::CreateDirectory($basePython)
        $python=AcharOuBaixarPython $basePython -Exato310
    }
    if (-not $python) { throw (T 'Falha ao preparar o Python do pacote.') }
    $scriptPrep=Join-Path (Split-Path -Parent $script:AQUI) 'build/pacotes_portateis.py'
    $psi=[Diagnostics.ProcessStartInfo]::new()
    $psi.FileName=$python; $psi.Arguments=LinhaDeArgumentos (@('-B',$scriptPrep,'--saida',$Saida)+$Plugins)
    $psi.UseShellExecute=$false; $psi.CreateNoWindow=$true
    $psi.RedirectStandardOutput=$true; $psi.RedirectStandardError=$true
    $proc=[Diagnostics.Process]::Start($psi)
    try {
        if ((AcompanharProcesso -Proc $proc -Cancelavel) -ne 0) { throw (T 'Falha ao montar os pacotes selecionados.') }
    } finally { $proc.Dispose() }
}

function IniciarPacotePortatil {
    if ($script:Ocupado) { return }
    $selecao=@(Selecionar-PacotesPortateis $form)
    if (-not $selecao.Count) { return }
    $destino=[Windows.Forms.FolderBrowserDialog]::new()
    $destino.ShowNewFolderButton=$true
    $destino.Description=T 'Selecionar pasta de destino'
    try {
        if ($destino.ShowDialog($form) -ne [Windows.Forms.DialogResult]::OK) { return }
        $saida=$destino.SelectedPath
    } finally { $destino.Dispose() }
    $perfis=@{'neuro-rt'='plugin-neuro';'lung-rt'='plugin-lung';'coronarias'='plugin-coronarias'}
    $plugins=@($selecao | Where-Object {$_ -ne 'core'})
    foreach ($id in $plugins) {
        if (-not (Solicitar-TermosSuite $script:CatalogoDeTermos $perfis[$id])) { return }
    }
    $script:UltimaAcao='portatil'
    MarcarModo '2'
    $cxPasta.Text=$saida; $script:PastaEscolhida['2']=$saida
    $script:PluginsParaLevar=$plugins
    if ($selecao -contains 'core') { ContinuarComTermos 'preparar'; return }
    $script:Ocupado=$true; $script:Cancelar=$false; $script:BtParar.Enabled=$true
    $script:ArquivoLog=Join-Path $saida 'preparar_log.txt'
    try {
        Montar-PluginsPortateis $saida $plugins
        $script:Trabalho=$saida
        AtualizarConclusao $saida ''
        $txt4.Text=(T 'Pacotes preparados') + [Environment]::NewLine + ($plugins -join ', ') + [Environment]::NewLine + $saida
        $btAbrirPasta.Visible=$true; $btAbrirPasta.Enabled=$true; $abas.SelectedTab=$aba4
    } catch { Falhar $_.Exception.Message }
    finally { $script:Ocupado=$false; $script:BtParar.Enabled=$false; $script:Cancelar=$false }
}

