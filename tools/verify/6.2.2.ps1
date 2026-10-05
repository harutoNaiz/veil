# Verify sub-phase 6.2.2 "Workshop server (Flask)".
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
  Run @('uv', 'run', '--locked', 'ruff', 'check', 'workshop/api')
  if ($LASTEXITCODE -eq 0) { Run @('uv', 'run', '--locked', 'ruff', 'format', '--check', 'workshop/api') }
}
Check '(2) pytest' { Run @('uv', 'run', '--locked', 'pytest', 'workshop/api/tests', '-q') }
Check '(3) live server + client' {
  $script = Join-Path $env:TEMP 'veil_622_live.py'
  @'
import subprocess, sys, time
from workshop.api import client
p = subprocess.Popen([sys.executable, "-m", "flask", "--app", "workshop.api.app:create_app", "run", "--port", "5622"])
try:
    time.sleep(5)
    cat = client.fetch_catalogue("http://127.0.0.1:5622")
    assert any(x["packId"] == "sensitive-bundle" for x in cat["packs"]), cat
    print("catalogue ok", len(cat["packs"]))
finally:
    p.terminate()
'@ | Set-Content -Encoding utf8 $script
  Run @('uv', 'run', '--locked', 'python', $script)
}

if ($script:failed) { Write-Host 'VERIFY 6.2.2: FAIL'; exit 1 }
Write-Host 'VERIFY 6.2.2: PASS'
