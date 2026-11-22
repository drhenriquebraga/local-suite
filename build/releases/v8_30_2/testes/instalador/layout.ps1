# Runs inside the private Windows Forms test copy, in its Shown event.
$abas.SelectedTab = $aba0
$titulosIniciais = @($aba0.Controls | Where-Object { $_ -is [Windows.Forms.Button] } | ForEach-Object Text)
if ($titulosIniciais.Count -ne 4 -or $titulosIniciais -match 'Pasta') { throw 'First-page folder buttons remain' }
if (@($aba0.Controls | Where-Object { $_ -is [Windows.Forms.Label] -and $_.Top -ge $btModo5.Bottom }).Count) { throw 'Uninstall caption remains' }
Write-Host 'PASS First page contains four actions and no uninstall caption'

$abas.SelectedTab = $aba3
$tamanhoOriginal = $form.Size
foreach ($size in @([Drawing.Size]::new(900,640), [Drawing.Size]::new(1000,740), [Drawing.Size]::new(1280,840))) {
    $form.Size = $size
    [Windows.Forms.Application]::DoEvents()
    $gap = $aba3.ClientSize.Width - $btParar.Right
    $bottom = $aba3.ClientSize.Height - $btParar.Bottom
    if ($gap -ne 20 -or $bottom -ne 16 -or $script:CaixaLog.Bottom -gt ($btParar.Top - 8)) {
        throw ("Cancel/log layout at " + $size + ", gap " + $gap + "x" + $bottom)
    }
}
EsconderPreparo
if ($script:CaixaLog.Bottom -gt ($btParar.Top - 8)) { throw 'Expanded log overlaps Cancel' }
MostrarPreparo
if ($script:CaixaLog.Bottom -gt ($btParar.Top - 8)) { throw 'Restored log overlaps Cancel' }
$form.Size = $tamanhoOriginal
Write-Host 'PASS Bottom-right Cancel, log spacing and resize at three window sizes'

Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class CancelFixturePicker {
    delegate bool EnumWindow(IntPtr handle, IntPtr arg);
    [DllImport("kernel32.dll")] static extern uint GetCurrentThreadId();
    [DllImport("user32.dll")] static extern bool EnumThreadWindows(uint thread, EnumWindow callback, IntPtr arg);
    [DllImport("user32.dll",CharSet=CharSet.Unicode)] static extern int GetWindowText(IntPtr h,StringBuilder b,int n);
    [DllImport("user32.dll",CharSet=CharSet.Unicode)] static extern int GetClassName(IntPtr h,StringBuilder b,int n);
    [DllImport("user32.dll")] static extern bool PostMessage(IntPtr h,uint msg,IntPtr w,IntPtr l);
    public static bool Close(string caption) {
        bool found = false;
        EnumThreadWindows(GetCurrentThreadId(), delegate(IntPtr h,IntPtr arg) {
            var text = new StringBuilder(512); var cls = new StringBuilder(80);
            GetWindowText(h,text,text.Capacity); GetClassName(h,cls,cls.Capacity);
            if (text.ToString()!=caption || cls.ToString()!="#32770") return true;
            found = PostMessage(h,0x10,IntPtr.Zero,IntPtr.Zero); return false;
        }, IntPtr.Zero);
        return found;
    }
}
'@
$script:tituloFixture = T 'Sem internet: escolha o .zip de um pacote completo que você trouxe'
$script:seletorFechado = $false
$timerChooser = New-Object Windows.Forms.Timer
$timerChooser.Interval = 100
$timerChooser.Add_Tick({
    if ([CancelFixturePicker]::Close($script:tituloFixture)) {
        $script:seletorFechado=$true
        $this.Stop()
    }
})
function HaRede { return $false }
$timerChooser.Start()
try { [void](InstalarOuAtualizar) } finally { $timerChooser.Dispose() }
if (-not $script:seletorFechado -or $abas.SelectedTab -ne $aba0 -or $script:AcaoDosTermos) {
    throw 'Canceling the auto-routed native file picker did not return directly to Start'
}
Write-Host 'PASS Automatic offline route opens one native package picker and cancellation returns to Start'
