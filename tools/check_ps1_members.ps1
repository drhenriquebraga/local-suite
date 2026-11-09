param([Parameter(Mandatory = $true)][string]$Arquivo)

$err = $null; $tok = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    $Arquivo, [ref]$tok, [ref]$err)
if ($err -and $err.Count) {
    foreach ($e in $err) {
        Write-Output ("PARSE`t" + $e.Extent.StartLineNumber + "`t" + $e.Message)
    }
    exit 2
}

$tabelas = @{}
$vazias  = New-Object System.Collections.Generic.HashSet[string] (
    [StringComparer]::OrdinalIgnoreCase)

$ast.FindAll({ param($n)
    $n -is [System.Management.Automation.Language.AssignmentStatementAst] }, $true) |
  ForEach-Object {
    $esq = $_.Left
    $dir = $_.Right
    if ($dir -is [System.Management.Automation.Language.CommandExpressionAst]) {
        $dir = $dir.Expression
    }
    if ($esq -is [System.Management.Automation.Language.VariableExpressionAst] -and
        $dir -is [System.Management.Automation.Language.ArrayExpressionAst]) {
        [void]$vazias.Add($esq.VariablePath.UserPath)
        return
    }
    if ($esq -is [System.Management.Automation.Language.VariableExpressionAst] -and
        $dir -is [System.Management.Automation.Language.HashtableAst]) {

        $nome = $esq.VariablePath.UserPath
        if ($dir.KeyValuePairs.Count -eq 0) { [void]$vazias.Add($nome); return }

        $chaves = New-Object System.Collections.Generic.HashSet[string] (
            [StringComparer]::OrdinalIgnoreCase)
        foreach ($par in $dir.KeyValuePairs) {
            $k = $par.Item1
            if ($k -is [System.Management.Automation.Language.StringConstantExpressionAst]) {
                [void]$chaves.Add($k.Value)
            } else {
                [void]$vazias.Add($nome)
            }
        }
        if (-not $tabelas.ContainsKey($nome)) { $tabelas[$nome] = $chaves }
        else { foreach ($c in $chaves) { [void]$tabelas[$nome].Add($c) } }
    }
  }

foreach ($n in ($tabelas.Keys | Sort-Object)) {
    if ($vazias.Contains($n)) { continue }
    Write-Output ("TABELA`t" + $n + "`t" + (($tabelas[$n] | Sort-Object) -join ','))
}


$achou = $false
$ast.FindAll({ param($n)
    $n -is [System.Management.Automation.Language.MemberExpressionAst] }, $true) |
  ForEach-Object {
    $alvo   = $_.Expression
    $membro = $_.Member
    if ($alvo -is [System.Management.Automation.Language.VariableExpressionAst] -and
        $membro -is [System.Management.Automation.Language.StringConstantExpressionAst]) {
        $nome = $alvo.VariablePath.UserPath
        $intrinsecos = @('Count','Length','Keys','Values','PSObject',
                         'GetEnumerator','ContainsKey','Contains','Item',
                         'Remove','Clear','Add','GetType')
        if ($tabelas.ContainsKey($nome) -and -not $vazias.Contains($nome) -and
            -not ($intrinsecos -contains $membro.Value) -and
            -not $tabelas[$nome].Contains($membro.Value)) {
            $script:achou = $true
            Write-Output ("FALTA`t" + $_.Extent.StartLineNumber + "`t" + $nome +
                          "." + $membro.Value + "`t" + $_.Extent.Text)
        }
    }
  }

if ($achou) { exit 1 }
exit 0
