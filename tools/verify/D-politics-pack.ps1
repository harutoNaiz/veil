# Verify D-politics-pack.
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
  else { $out | Where-Object { $_ -match '^politics' } | ForEach-Object { Write-Host "    $_" } }
  Write-Host ('{0}  {1}' -f $(if ($ok) { 'ok  ' } else { 'FAIL' }), $name)
  if (-not $ok) { $script:failed = $true }
}

function Run([string[]]$cmd) { powershell -NoProfile -ExecutionPolicy Bypass -File $w @cmd }

Check '(1) ruff' {
  Run @('uv', 'run', '--locked', 'ruff', 'check', 'workshop/packs')
  if ($LASTEXITCODE -eq 0) { Run @('uv', 'run', '--locked', 'ruff', 'format', '--check', 'workshop/packs') }
}
Check '(2) build + text eval' {
  Run @('uv', 'run', '--locked', 'python', '-m', 'workshop.packs.build_packs')
  if ($LASTEXITCODE -eq 0) { Run @('uv', 'run', '--locked', 'python', '-m', 'workshop.packs.eval_packs', '--pack', 'politics', '--cached') }
}
Check '(3) report + catalogue' {
  $ok = (Test-Path 'workshop\packs\reports\politics.json') -and (Select-String -Path 'workshop\packs\politics.json' -Pattern '"packId": "politics"' -Quiet)
  cmd /c $(if ($ok) { 'exit 0' } else { 'exit 1' })
}
Check '(4) pytest' { Run @('uv', 'run', '--locked', 'pytest', 'workshop/packs/tests', '-q') }

if ($script:failed) { Write-Host 'VERIFY D-politics-pack: FAIL'; exit 1 }
Write-Host 'VERIFY D-politics-pack: PASS'
