# Verify sub-phase 5.1.1 "Kotlin decision logic (gate, judge, cache)".
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify\5.1.1.ps1
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$script:failed = $false

function Step([string]$name, [scriptblock]$body, [int]$expect = 0) {
  & $body | Out-Host
  $code = $LASTEXITCODE
  if ($code -eq $expect) { Write-Host "ok    $name" }
  else { Write-Host "FAIL  $name (exit $code, wanted $expect)"; $script:failed = $true }
}

Step '0 ruff' { uv run --locked ruff check workshop/brain_ref/judge_ref.py workshop/brain_ref/cache_ref.py workshop/brain_ref/__init__.py; if ($LASTEXITCODE -eq 0) { uv run --locked ruff format --check workshop/brain_ref/judge_ref.py workshop/brain_ref/cache_ref.py } }
$fx = @('judge-golden.json', 'cache-golden.json') | ForEach-Object { "guard\brain\src\test\resources\$_" }
$before = $fx | ForEach-Object { (Get-FileHash $_ -Algorithm SHA256).Hash }
Step '1 regenerate judge fixture' { uv run --locked python -m workshop.brain_ref.judge_ref }
Step '2 regenerate cache fixture' { uv run --locked python -m workshop.brain_ref.cache_ref }
$after = $fx | ForEach-Object { (Get-FileHash $_ -Algorithm SHA256).Hash }
if (($before -join ',') -eq ($after -join ',')) { Write-Host 'ok    3 fixtures reproducible' }
else { Write-Host 'FAIL  3 fixtures changed on regeneration'; $script:failed = $true }

Push-Location "$repo\guard"
Step '4 gradle brain unit tests' { .\gradlew.bat --no-daemon "-Pveil.brainOnly=true" :brain:test --tests "com.veil.brain.unit.*" }
Pop-Location
Step '5 ktlint brain' { & "$env:JAVA_HOME\bin\java.exe" -jar "$env:VEIL_TOOLCHAIN\ktlint\ktlint.jar" "guard/brain/src/**/*.kt" }
if (Select-String -Path 'guard\brain\build.gradle.kts' -Pattern 'com\.android|androidx' -Quiet) { Write-Host 'FAIL  6 android in brain build'; $script:failed = $true }
else { Write-Host 'ok    6 brain build has no android' }

if ($script:failed) { Write-Host 'VERIFY 5.1.1: FAIL'; exit 1 }
Write-Host 'VERIFY 5.1.1: PASS'
