$ErrorActionPreference = 'SilentlyContinue'
try {
    Add-Type -Name Janela -Namespace RadAI -MemberDefinition @'
[DllImport("kernel32.dll")]
public static extern System.IntPtr GetConsoleWindow();
[DllImport("user32.dll")]
public static extern bool ShowWindow(System.IntPtr hWnd, int nCmdShow);
'@
    $h = [RadAI.Janela]::GetConsoleWindow()
    if ($h -ne [System.IntPtr]::Zero) { [void][RadAI.Janela]::ShowWindow($h, 6) }
} catch { }
