# Verify sub-phase 6.3.2 "Final evaluation".
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$script:failed = $false
$w = Join-Path $repo 'tools\with-env.ps1'

function Check([string]$name, [scriptblock]$body) {
  $out = @(& $body 2>&1 | ForEach-Object { "$_" })
  $ok = ($LASTEXITCODE -eq 0)
  if (-not $ok) { $out | Select-Object -Last 25 | ForEach-Object { Write-Host "    $_" } }
  Write-Host ('{0}  {1}' -f $(if ($ok) { 'ok  ' } else { 'FAIL' }), $name)
  if (-not $ok) { $script:failed = $true }
}

function Run([string[]]$cmd) { powershell -NoProfile -ExecutionPolicy Bypass -File $w @cmd }

Check '(1) ruff' {
  Run @('uv', 'run', '--locked', 'ruff', 'check', 'workshop/final')
  if ($LASTEXITCODE -eq 0) { Run @('uv', 'run', '--locked', 'ruff', 'format', '--check', 'workshop/final') }
}
Check '(2) pytest' { Run @('uv', 'run', '--locked', 'pytest', 'workshop/final/tests', '-q') }
Check '(3) final_report.ps1 (generate + lint)' { & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repo 'tools\final_report.ps1') }
Check '(4) content' {
  $t = Get-Content (Join-Path $repo 'docs\reports\final.md') -Raw
  if ($t.Contains('| F-01 |') -and $t.Contains('## Limits')) { $global:LASTEXITCODE = 0 } else { $global:LASTEXITCODE = 1 }
}

if ($script:failed) { Write-Host 'VERIFY 6.3.2: FAIL'; exit 1 }
Write-Host 'VERIFY 6.3.2: PASS'
