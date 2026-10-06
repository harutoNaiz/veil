$ErrorActionPreference = 'Stop'
$p = Join-Path $PSScriptRoot '..\heavy\7.2-heavy.ps1'
$ok = $true
function Check($c, $m) { if (-not $c) { Write-Host "FAIL: $m"; $script:ok = $false } }
$errs = $null; $tok = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile((Resolve-Path $p), [ref]$tok, [ref]$errs)
Check ($errs.Count -eq 0) 'parse errors'
$a = $ast.Find({ param($n) $n -is [System.Management.Automation.Language.AssignmentStatementAst] -and $n.Left.Extent.Text -eq '$flags' }, $true)
Check ($null -ne $a) 'no $flags assignment'
if ($a) {
  $expr = $a.Right.Extent.Text
  foreach ($Mini in $true, $false) {
    Invoke-Expression "`$flags = $expr"
    $want = if ($Mini) { 1 } else { 0 }
    Check ($flags -is [array]) "flags not array (Mini=$Mini)"
    Check (@($flags).Count -eq $want) "count != $want (Mini=$Mini)"
    if ($Mini) {
      $sb = { param($f) & cmd /c echo @f }
      $out = (& $sb $flags | Out-String).Trim()
      Check ($out -eq '--mini') "splat gave '$out'"
    }
  }
}
if ($ok) { 'VERIFY D-72-flags: PASS' } else { 'VERIFY D-72-flags: FAIL' }
