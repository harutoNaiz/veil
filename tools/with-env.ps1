$ErrorActionPreference = 'Stop'
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\env.ps1"
$repo = Split-Path -Parent $PSScriptRoot
$a = @($args)
if ($a.Count -ge 2 -and $a[0] -eq '--cd') { Set-Location (Join-Path $repo $a[1]); $a = @($a | Select-Object -Skip 2) } else { Set-Location $repo }
if ($a.Count -lt 1) { Write-Error 'usage: with-env.ps1 [--cd <dir>] <command> [args...]' }
$exe = $a[0]; $rest = @($a | Select-Object -Skip 1)
$ErrorActionPreference = 'Continue'
& $exe @rest
exit $LASTEXITCODE
