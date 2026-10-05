# Verify sub-phase 5.2.2 "Pieces from three sources". Ends with VERIFY 5.2.2: PASS.
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$script:failed = $false

function Check([string]$name, [scriptblock]$body) {
  $out = @(& $body 2>&1 | ForEach-Object { "$_" })
  $ok = ($LASTEXITCODE -eq 0)
  if (-not $ok) { $out | Select-Object -Last 25 | ForEach-Object { Write-Host "    $_" } }
  Write-Host ('{0}  {1}' -f $(if ($ok) { 'ok  ' } else { 'FAIL' }), $name)
  if (-not $ok) { $script:failed = $true }
}
Check '(1) conductor regions tests' { powershell -NoProfile -ExecutionPolicy Bypass -File "$repo\tools\gradle-locked.ps1" '-Pveil.brainOnly=true' :conductor:test --tests "com.veil.conductor.regions.*" }
Check '(2) ktlint regions' { & "$env:JAVA_HOME\bin\java.exe" -jar "$env:VEIL_TOOLCHAIN\ktlint\ktlint.jar" "guard/conductor/src/**/regions/*.kt" }
Check '(3) pytest guardcheck' { uv run --locked pytest workshop/guardcheck -q }
Check '(4) ruff guardcheck' { uv run --locked ruff check workshop/guardcheck; if ($LASTEXITCODE -eq 0) { uv run --locked ruff format --check workshop/guardcheck } }
if ($script:failed) { Write-Host 'VERIFY 5.2.2: FAIL'; exit 1 }
Write-Host 'VERIFY 5.2.2: PASS'
