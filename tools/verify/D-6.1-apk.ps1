# Verify D-6.1-apk: Pigeon outputs fresh, analyze, test; -Build also runs flutter build apk --debug.
param([switch]$Build)
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$con = Join-Path $repo 'console'
$ErrorActionPreference = 'Continue'
$script:failed = $false

function Check([string]$name, [scriptblock]$body) {
  $out = @(& $body 2>&1 | ForEach-Object { "$_" })
  $ok = ($LASTEXITCODE -eq 0)
  if (-not $ok) { $out | Select-Object -Last 30 | ForEach-Object { Write-Host "    $_" } }
  Write-Host ('{0}  {1}' -f $(if ($ok) { 'ok  ' } else { 'FAIL' }), $name)
  if (-not $ok) { $script:failed = $true }
}

$gen = 'lib/guard/generated/guard_api.g.dart', 'android/app/src/main/kotlin/com/veil/console/bridge/GuardApi.g.kt'
Push-Location $con
Check '(1) flutter pub get' { flutter pub get }
Check '(2) pigeon regen is fresh (no diff, CR-insensitive)' {
  dart run pigeon --input pigeons/guard_api.dart
  if ($LASTEXITCODE -eq 0) { dart format $gen[0] }
  if ($LASTEXITCODE -eq 0) { git diff --exit-code --ignore-cr-at-eol -- $gen }
}
Check '(3) flutter analyze' { flutter analyze }
Check '(4) flutter test' { flutter test }
if ($Build) { Check '(5) flutter build apk --debug' { flutter build apk --debug } }
Pop-Location

if ($script:failed) { Write-Host 'VERIFY D-6.1-apk: FAIL'; exit 1 }
Write-Host 'VERIFY D-6.1-apk: PASS'
exit 0
