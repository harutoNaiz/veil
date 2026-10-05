# Verify sub-phase 6.3.1 "Hardening".
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
  if ($ok -and $name -like '*RECOVERY*' -and -not ($out -match 'RECOVERY crash=5/5 lock=5/5 kill=5/5')) { $ok = $false }
  if (-not $ok) { $out | Select-Object -Last 25 | ForEach-Object { Write-Host "    $_" } }
  Write-Host ('{0}  {1}' -f $(if ($ok) { 'ok  ' } else { 'FAIL' }), $name)
  if (-not $ok) { $script:failed = $true }
}

function Run([string[]]$cmd) { powershell -NoProfile -ExecutionPolicy Bypass -File $w @cmd }

Check '(1) flutter analyze' { Run @('--cd', 'console', 'flutter', 'analyze', 'lib/guard', 'lib/status', 'test/hardening') }
Check '(2) flutter test (RECOVERY line)' { Run @('--cd', 'console', 'flutter', 'test', 'test/hardening', 'test/onboarding') }
Check '(3) ruff' {
  Run @('uv', 'run', '--locked', 'ruff', 'check', 'workshop/harden')
  if ($LASTEXITCODE -eq 0) { Run @('uv', 'run', '--locked', 'ruff', 'format', '--check', 'workshop/harden') }
}
Check '(4) pytest' { Run @('uv', 'run', '--locked', 'pytest', 'workshop/harden/tests', '-q') }
Check '(5) edge-cases rows' {
  $t = Get-Content -Raw (Join-Path $repo 'docs\release\edge-cases.md')
  $all = $true
  foreach ($r in 'Rotation','Split screen','Keyboard open','Picture-in-picture','Notification shade','App switch mid-scroll','Netflix','heat run') { if ($t -notmatch [regex]::Escape($r)) { $all = $false } }
  if ($all) { $global:LASTEXITCODE = 0 } else { $global:LASTEXITCODE = 1 }
}

if ($script:failed) { Write-Host 'VERIFY 6.3.1: FAIL'; exit 1 }
Write-Host 'VERIFY 6.3.1: PASS'
