param([Parameter(Mandatory = $true)][string]$Arquivo)

$ErrorActionPreference = 'Stop'

$erros = $null
$tk = $null
$arv = [System.Management.Automation.Language.Parser]::ParseFile(
    $Arquivo, [ref]$tk, [ref]$erros)
if ($erros -and $erros.Count -gt 0) {
    foreach ($e in $erros) {
        Write-Output ("SINTAXE`t{0}`t{1}`t{2}" -f $Arquivo,
                      $e.Extent.StartLineNumber, $e.Message)
    }
    exit 0
}

$auto = @('_', 'PSItem', 'args', 'this', 'true', 'false', 'null', 'input',
          'PSScriptRoot', 'PSCommandPath', 'MyInvocation', 'Host', 'Error',
          'ErrorActionPreference', 'PWD', 'HOME', 'PID', 'matches', 'LASTEXITCODE',
          'PSVersionTable', 'StackTrace', 'ExecutionContext', 'foreach', 'switch',
          'OFS', 'ConfirmPreference', 'VerbosePreference', 'DebugPreference',
          'WarningPreference', 'ProgressPreference', 'InformationPreference')

$blocos = $arv.FindAll({ param($n)
    $n -is [System.Management.Automation.Language.ScriptBlockAst] }, $true)

foreach ($b in $blocos) {
    $meus = $b.FindAll({ param($n) $true }, $false)

    $prim = @{}
    $leu  = @{}
    $params = @{}

    if ($b.ParamBlock) {
        foreach ($p in $b.ParamBlock.Parameters) {
            $params[$p.Name.VariablePath.UserPath.ToLower()] = $true
        }
    }
    if ($b.Parent -is [System.Management.Automation.Language.FunctionDefinitionAst] `
        -and $b.Parent.Parameters) {
        foreach ($p in $b.Parent.Parameters) {
            $params[$p.Name.VariablePath.UserPath.ToLower()] = $true
        }
    }

    $todos = $b.FindAll({ param($n) $true }, $true)
    foreach ($n in $todos) {
        $dono = $n.Parent
        $meu = $false
        while ($dono) {
            if ($dono -is [System.Management.Automation.Language.ScriptBlockAst]) {
                $meu = ($dono -eq $b); break
            }
            $dono = $dono.Parent
        }
        if (-not $meu) { continue }

        if ($n -is [System.Management.Automation.Language.AssignmentStatementAst]) {
            $alvo = $n.Left
            if ($alvo -is [System.Management.Automation.Language.VariableExpressionAst]) {
                $k = $alvo.VariablePath.UserPath.ToLower()
                $o = $n.Extent.StartOffset
                if (-not $prim.ContainsKey($k) -or $prim[$k] -gt $o) { $prim[$k] = $o }
            }
        }
        elseif ($n -is [System.Management.Automation.Language.ForEachStatementAst]) {
            $k = $n.Variable.VariablePath.UserPath.ToLower()
            $o = $n.Extent.StartOffset
            if (-not $prim.ContainsKey($k) -or $prim[$k] -gt $o) { $prim[$k] = $o }
        }
        elseif ($n -is [System.Management.Automation.Language.VariableExpressionAst]) {
            if ($n.Parent -is [System.Management.Automation.Language.ParameterAst]) {
                continue
            }
            $vp = $n.VariablePath
            if (-not $vp.IsUnqualified) { continue }
            $k = $vp.UserPath.ToLower()
            if ($auto -contains $vp.UserPath) { continue }
            if ($params.ContainsKey($k)) { continue }
            $o = $n.Extent.StartOffset
            if (-not $leu.ContainsKey($k) -or $leu[$k] -gt $o) { $leu[$k] = $o }
        }
    }

    foreach ($k in $leu.Keys) {
        if (-not $prim.ContainsKey($k)) { continue }
        if ($leu[$k] -lt $prim[$k]) {
            $ln = 0
            foreach ($n in $todos) {
                if ($n -is [System.Management.Automation.Language.VariableExpressionAst] `
                    -and $n.VariablePath.IsUnqualified `
                    -and $n.VariablePath.UserPath.ToLower() -eq $k `
                    -and $n.Extent.StartOffset -eq $leu[$k]) {
                    $ln = $n.Extent.StartLineNumber; break
                }
            }
            Write-Output ("LERANTES`t{0}`t{1}`t`${2}" -f
                          (Split-Path -Leaf $Arquivo), $ln, $k)
        }
    }
}
