# PT-4.1 "Watch the watcher" (PHONE only). Installs the debug APK, runs the 5-min routine, checks the logs.
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$ev = Join-Path $repo '..\progress\ch4-plumbing\phase-4.1-screen-capture\evidence'
New-Item -ItemType Directory -Force $ev | Out-Null

& "$repo\guard\gradlew.bat" -p guard --no-daemon :app:installDebug
if ($LASTEXITCODE -ne 0) { Write-Host 'PT 4.1: FAIL (install)'; exit 1 }
adb shell am start -n com.veil.guard/com.veil.guard.capture.service.ConsentActivity
Read-Host 'Accept the consent dialog ("Entire screen"), then press Enter'
uv run python -m workshop.bench.capture_routine --minutes 5
if ($LASTEXITCODE -ne 0) { Write-Host 'PT 4.1: FAIL (routine)'; exit 1 }
$dir = Get-ChildItem (Join-Path $repo 'data\capture') -Directory | Sort-Object Name | Select-Object -Last 1
uv run python -m workshop.bench.capture_logs $dir.FullName --out (Join-Path $ev 'capture-report.json')
$rc = $LASTEXITCODE
Copy-Item "$($dir.FullName)\*" $ev -Force -ErrorAction SilentlyContinue
if ($rc -eq 0) { Write-Host 'PT 4.1: PASS' } else { Write-Host 'PT 4.1: FAIL'; exit 1 }
