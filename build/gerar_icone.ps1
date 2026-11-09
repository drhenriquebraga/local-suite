
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

$AQUI  = Split-Path -Parent $MyInvocation.MyCommand.Path
$SAIDA = Join-Path (Split-Path -Parent $AQUI) 'app'
$LADO  = 1024

$corFundo1 = [System.Drawing.Color]::FromArgb(255, 13, 27, 42)
$corFundo2 = [System.Drawing.Color]::FromArgb(255,  5, 11, 20)
$corAnelA  = [System.Drawing.Color]::FromArgb(255,158, 205, 232)
$corAnelB  = [System.Drawing.Color]::FromArgb(255, 47, 110, 148)
$corAnelC  = [System.Drawing.Color]::FromArgb(255, 24,  62,  90)

$bmp = New-Object System.Drawing.Bitmap($LADO, $LADO)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode     = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
$g.PixelOffsetMode   = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality

$caminho = New-Object System.Drawing.Drawing2D.GraphicsPath
$caminho.AddEllipse([single](-$LADO * 0.2), [single](-$LADO * 0.2), [single]($LADO * 1.4), [single]($LADO * 1.4))
$fundo = New-Object System.Drawing.Drawing2D.PathGradientBrush($caminho)
$fundo.CenterPoint    = New-Object System.Drawing.PointF([single]($LADO * 0.45), [single]($LADO * 0.42))
$fundo.CenterColor    = $corFundo1
$fundo.SurroundColors = @($corFundo2)
$g.FillRectangle($fundo, 0, 0, $LADO, $LADO)

$cx = $LADO / 2.0
$cy = $LADO / 2.0

function Anel {
    param(
        [double]$Rx, [double]$Ry, [double]$Giro,
        [double]$Espessura, [System.Drawing.Color]$Cor, [int]$Alfa
    )
    $est = $g.Save()
    $g.TranslateTransform([single]$cx, [single]$cy)
    $g.RotateTransform([single]$Giro)
    $c = [System.Drawing.Color]::FromArgb($Alfa, $Cor.R, $Cor.G, $Cor.B)
    $caneta = New-Object System.Drawing.Pen($c, [single]$Espessura)
    $g.DrawEllipse($caneta, [single](-$Rx), [single](-$Ry), [single]($Rx * 2), [single]($Ry * 2))
    $caneta.Dispose()
    $g.Restore($est)
}

$equatoriais = @(
    @{ rx = 0.470; ry = 0.150 },
    @{ rx = 0.425; ry = 0.132 },
    @{ rx = 0.360; ry = 0.108 },
    @{ rx = 0.300; ry = 0.086 },
    @{ rx = 0.235; ry = 0.064 }
)
foreach ($e in $equatoriais) {
    Anel ($LADO * $e.rx) ($LADO * $e.ry) (-8) ($LADO * 0.030) $corAnelC 240
    Anel ($LADO * $e.rx) ($LADO * $e.ry) (-8) ($LADO * 0.014) $corAnelA 250
}

$meridianos = @(
    @{ rx = 0.395; ry = 0.400; giro =   0 },
    @{ rx = 0.240; ry = 0.395; giro = -14 },
    @{ rx = 0.320; ry = 0.360; giro =  22 },
    @{ rx = 0.150; ry = 0.300; giro =  -6 },
    @{ rx = 0.205; ry = 0.235; giro =  10 }
)
foreach ($m in $meridianos) {
    Anel ($LADO * $m.rx) ($LADO * $m.ry) ($m.giro) ($LADO * 0.028) $corAnelB 230
    Anel ($LADO * $m.rx) ($LADO * $m.ry) ($m.giro) ($LADO * 0.013) $corAnelA 245
}

$halos = @(
    @{ r = 0.115; a =  28 },
    @{ r = 0.082; a =  52 },
    @{ r = 0.055; a =  95 },
    @{ r = 0.034; a = 190 }
)
foreach ($h in $halos) {
    $r = $LADO * $h.r
    $b = New-Object System.Drawing.SolidBrush(
        [System.Drawing.Color]::FromArgb($h.a, 214, 238, 255))
    $g.FillEllipse($b, [single]($cx - $r), [single]($cy - $r), [single]($r * 2), [single]($r * 2))
    $b.Dispose()
}
$r = $LADO * 0.022
$b = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255, 255, 255, 255))
$g.FillEllipse($b, [single]($cx - $r), [single]($cy - $r), [single]($r * 2), [single]($r * 2))
$b.Dispose()

$g.Dispose()

$tamanhos = @(256, 128, 64, 48, 32, 24, 20, 16)
$tmp = Join-Path $env:TEMP ('radai_icone_' + [System.Guid]::NewGuid().ToString('N').Substring(0,8))
New-Item -ItemType Directory -Path $tmp -Force | Out-Null
$feitos = @()
foreach ($t in $tamanhos) {
    $m = New-Object System.Drawing.Bitmap($t, $t)
    $gg = [System.Drawing.Graphics]::FromImage($m)
    $gg.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $gg.SmoothingMode     = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $gg.PixelOffsetMode   = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
    $gg.DrawImage($bmp, 0, 0, $t, $t)
    $gg.Dispose()
    $arq = Join-Path $tmp ("icone_" + $t + ".png")
    $m.Save($arq, [System.Drawing.Imaging.ImageFormat]::Png)
    $m.Dispose()
    $feitos += $arq
}
$bmp.Dispose()

$grande = Join-Path $SAIDA 'radioterapia_ai.png'
Copy-Item -LiteralPath (Join-Path $tmp 'icone_256.png') -Destination $grande -Force

Write-Host ('  PNGs gerados em ' + $tmp)
Write-Host ('  previa: ' + $grande)
Write-Host ('  ' + $tmp)
