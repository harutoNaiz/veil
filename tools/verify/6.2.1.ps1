# Verify sub-phase 6.2.1 "Corrections".
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$script:failed = $false
$w = Join-Path $repo 'tools\with-env.ps1'
$g = Join-Path $repo 'tools\gradle-locked.ps1'

function Check([string]$name, [scriptblock]$body, [int[]]$okCodes = @(0)) {
  $out = @(& $body 2>&1 | ForEach-Object { "$_" })
  $ok = ($okCodes -contains $LASTEXITCODE)
  if (-not $ok) { $out | Select-Object -Last 25 | ForEach-Object { Write-Host "    $_" } }
  else { $out | Where-Object { $_ -match '^(fox|PENDING|wrote)' } | ForEach-Object { Write-Host "    $_" } }
  Write-Host ('{0}  {1}' -f $(if ($ok) { 'ok  ' } else { 'FAIL' }), $name)
  if (-not $ok) { $script:failed = $true }
}

function Run([string[]]$cmd) { powershell -NoProfile -ExecutionPolicy Bypass -File $w @cmd }
$py = @('workshop/twin/corrections.py', 'workshop/twin/fox_scenario.py', 'workshop/twin/tests/test_corrections.py')

Check '(1) ruff' {
  Run (@('uv', 'run', '--locked', 'ruff', 'check') + $py)
  if ($LASTEXITCODE -eq 0) { Run (@('uv', 'run', '--locked', 'ruff', 'format', '--check', '--line-length', '100') + $py) }
}
Check '(2) pytest' { Run @('uv', 'run', '--locked', 'pytest', 'workshop/twin/tests/test_corrections.py', '-q') }
Check '(3) fox scenario (3 = skipped, SigLIP2 cache absent)' { Run @('uv', 'run', '--locked', 'python', '-m', 'workshop.twin.fox_scenario') } @(0, 3)
Check '(4) gradle brain + teacher' {
  powershell -NoProfile -ExecutionPolicy Bypass -File $g :brain:test :teacher:test
}
Check '(5) no network import in learn/ or CorrectionStore' {
  $files = @(Get-ChildItem 'guard\brain\src\main\kotlin\com\veil\brain\learn' -Filter *.kt -Recurse) + @(Get-Item 'guard\teacher\src\main\kotlin\com\veil\teacher\CorrectionStore.kt')
  $hit = $files | Select-String -Pattern 'java\.net|okhttp'
  if ($hit) { $hit | ForEach-Object { "$_" }; cmd /c exit 1 } else { cmd /c exit 0 }
}

if ($script:failed) { Write-Host 'VERIFY 6.2.1: FAIL'; exit 1 }
Write-Host 'VERIFY 6.2.1: PASS'
