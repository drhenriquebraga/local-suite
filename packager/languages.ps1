# -*- coding: utf-8 -*-

$script:IdiomaAtual = $null
$script:Dicionario  = $null
$script:CodigosIdioma = @()
$script:Traduziveis = New-Object System.Collections.ArrayList

$script:ArquivoIdioma = Join-Path $env:APPDATA 'RadioterapiaAI\idioma.txt'


function Carregar-Idiomas {
  param([string]$Pasta)

  $script:CodigosIdioma = @('pt-BR')
  $script:Dicionario = @{}

  $j = Join-Path $Pasta 'languages.json'
  if (-not (Test-Path -LiteralPath $j)) { return $false }

  try {
    $bruto = Get-Content -LiteralPath $j -Raw -Encoding UTF8
    $o = $bruto | ConvertFrom-Json
  } catch {
    return $false
  }

  $script:CodigosIdioma = @($o.codigos)
  foreach ($p in $o.frases.PSObject.Properties) {
    $por = @{}
    foreach ($q in $p.Value.PSObject.Properties) { $por[$q.Name] = $q.Value }
    $script:Dicionario[$p.Name] = $por
  }
  return $true
}


$script:IdiomaInicialSemEscolha = 'en'

function Idioma-Atual {
  if ($script:IdiomaAtual) { return $script:IdiomaAtual }
  $script:IdiomaAtual = $script:IdiomaInicialSemEscolha
  try {
    if (Test-Path -LiteralPath $script:ArquivoIdioma) {
      $c = (Get-Content -LiteralPath $script:ArquivoIdioma -Raw -Encoding UTF8).Trim()
      if ($c -and ($script:CodigosIdioma -contains $c)) { $script:IdiomaAtual = $c }
    }
  } catch { }
  return $script:IdiomaAtual
}


function Idioma-Definir {
  param([string]$Codigo)
  if (-not ($script:CodigosIdioma -contains $Codigo)) { return }
  $script:IdiomaAtual = $Codigo
  try {
    $d = Split-Path -Parent $script:ArquivoIdioma
    if (-not (Test-Path -LiteralPath $d)) {
      New-Item -ItemType Directory -Path $d -Force | Out-Null
    }
    [System.IO.File]::WriteAllText($script:ArquivoIdioma, $Codigo,
      (New-Object System.Text.UTF8Encoding($false)))
  } catch { }
}


function T {
  param([Parameter(Mandatory=$true)][AllowEmptyString()][string]$Texto)

  if (-not $Texto) { return $Texto }
  $cod = Idioma-Atual
  if ($cod -eq 'pt-BR') { return $Texto }
  if (-not $script:Dicionario) { return $Texto }

  $nucleo = $Texto.Trim()
  if (-not $nucleo) { return $Texto }
  $i = $Texto.IndexOf($nucleo)
  $antes  = $Texto.Substring(0, $i)
  $depois = $Texto.Substring($i + $nucleo.Length)

  $chave = $nucleo -replace "`r`n", "`n"

  $e = $script:Dicionario[$chave]
  if ($e -and $e[$cod]) {
    return $antes + ([string]$e[$cod] -replace "`n", "`r`n" -replace "`r`r`n", "`r`n") + $depois
  }

  if ($nucleo -match "`n") {
    $ps = $nucleo -split "`r?`n"
    $fora = @()
    foreach ($p in $ps) {
      $t = $p.Trim()
      if (-not $t) { $fora += $p; continue }
      $x = $script:Dicionario[$t]
      if (-not ($x -and $x[$cod])) { return $Texto }
      $fora += [string]$x[$cod]
    }
    return $antes + ($fora -join "`r`n") + $depois
  }

  return $Texto
}


function Registrar-Texto {
  param($Controle, [string]$Texto, [string]$Antes = '', [string]$Depois = '')
  if (-not $Controle) { return $Controle }
  [void]$script:Traduziveis.Add(
    @{ Ctrl = $Controle; Pt = $Texto; Antes = $Antes; Depois = $Depois })
  $Controle.Text = $Antes + (T $Texto) + $Depois
  return $Controle
}


function Retraduzir {
  param($Formulario)

  if ($Formulario) {
    $rtl = if ((Idioma-Atual) -eq 'ar') { 'Yes' } else { 'No' }
    try {
      $Formulario.RightToLeft = $rtl
      $Formulario.RightToLeftLayout = ((Idioma-Atual) -eq 'ar')
    } catch { }
  }

  foreach ($it in $script:Traduziveis) {
    if (-not $it.Pt) { continue }
    try { $it.Ctrl.Text = $it.Antes + (T $it.Pt) + $it.Depois } catch { }
  }
  if ($Formulario) { $Formulario.Refresh() }
}


function Nomes-Idiomas {
  return [ordered]@{
    'de'    = 'Deutsch'
    'en'    = 'English'
    'es'    = 'Español'
    'fr'    = 'Français'
    'it'    = 'Italiano'
    'pl'    = 'Polski'
    'pt-BR' = 'Português (Brasil)'
    'ar'    = 'العربية'
    'bn'    = 'বাংলা'
    'ko'    = '한국어'
    'zh-CN' = '中文'
    'ja'    = '日本語'
  }
}


function Novo-SeletorIdioma {
  param($X, $Y, $Largura = 190, $Formulario = $null, $AoTrocar = $null)

  $cb = New-Object System.Windows.Forms.ComboBox
  $cb.DropDownStyle = 'DropDownList'
  $cb.Location = New-Object System.Drawing.Point($X, $Y)
  $cb.Size = New-Object System.Drawing.Size($Largura, 24)
  $cb.FlatStyle = 'Flat'
  $cb.BackColor = [System.Drawing.Color]::FromArgb(24, 34, 52)
  $cb.ForeColor = [System.Drawing.Color]::FromArgb(207, 224, 245)
  try { $cb.Font = New-Object System.Drawing.Font('Segoe UI', 9) } catch { }

  $nomes = Nomes-Idiomas
  $ordem = @()
  foreach ($c in $nomes.Keys) {
    if ($script:CodigosIdioma -contains $c) {
      $ordem += $c; [void]$cb.Items.Add($nomes[$c])
    }
  }
  $atual = Idioma-Atual
  $i = [array]::IndexOf($ordem, $atual)
  if ($i -lt 0) { $i = 0 }
  $cb.SelectedIndex = $i

  $cb.Tag = @{ Ordem = $ordem; Form = $Formulario; AoTrocar = $AoTrocar }
  $cb.Add_SelectedIndexChanged({
    $d = $this.Tag
    if (-not $d) { return }
    $novo = $d.Ordem[$this.SelectedIndex]
    if ($novo -and $novo -ne (Idioma-Atual)) {
      Idioma-Definir $novo
      Retraduzir $d.Form
      if ($d.AoTrocar) { & $d.AoTrocar }
    }
  })

  return $cb
}
