# Verify sub-phase 6.2.3 "Topic packs".
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
  else { $out | Where-Object { $_ -match '^(spiders|needles|gore|alcohol|spoiler)' } | ForEach-Object { Write-Host "    $_" } }
  Write-Host ('{0}  {1}' -f $(if ($ok) { 'ok  ' } else { 'FAIL' }), $name)
  if (-not $ok) { $script:failed = $true }
}

function Run([string[]]$cmd) { powershell -NoProfile -ExecutionPolicy Bypass -File $w @cmd }

Check '(1) ruff' {
  Run @('uv', 'run', '--locked', 'ruff', 'check', 'workshop/packs')
  if ($LASTEXITCODE -eq 0) { Run @('uv', 'run', '--locked', 'ruff', 'format', '--check', 'workshop/packs') }
}
Check '(2) build + eval (cached)' {
  Run @('uv', 'run', '--locked', 'python', '-m', 'workshop.packs.build_packs')
  if ($LASTEXITCODE -eq 0) { Run @('uv', 'run', '--locked', 'python', '-m', 'workshop.packs.eval_packs', '--all', '--cached') }
}
Check '(3) pytest' { Run @('uv', 'run', '--locked', 'pytest', 'workshop/packs/tests', '-q') }

if ($script:failed) { Write-Host 'VERIFY 6.2.3: FAIL'; exit 1 }
Write-Host 'VERIFY 6.2.3: PASS'
