# Verify sub-phase 6.1.1 "Bridge to the Guard" (analyze + test only, no APK build).
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$script:failed = $false
$con = Join-Path $repo 'console'

function Check([string]$name, [scriptblock]$body) {
  $out = @(& $body 2>&1 | ForEach-Object { "$_" })
  $ok = ($LASTEXITCODE -eq 0)
  if (-not $ok) { $out | Select-Object -Last 25 | ForEach-Object { Write-Host "    $_" } }
  Write-Host ('{0}  {1}' -f $(if ($ok) { 'ok  ' } else { 'FAIL' }), $name)
  if (-not $ok) { $script:failed = $true }
}

$gen = @('lib/guard/generated/guard_api.g.dart', 'android/app/src/main/kotlin/com/veil/console/bridge/GuardApi.g.kt')
Check '(1) pigeon regen produces no diff' {
  Push-Location $con
  $before = $gen | ForEach-Object { (Get-FileHash $_).Hash }
  dart run pigeon --input pigeons/guard_api.dart
  $rc = $LASTEXITCODE
  $after = $gen | ForEach-Object { (Get-FileHash $_).Hash }
  Pop-Location
  if ($rc -ne 0) { cmd /c exit 1 } elseif (Compare-Object $before $after) { Write-Host 'generated files changed'; cmd /c exit 1 } else { cmd /c exit 0 }
}
Check '(2) flutter analyze lib/guard test/guard' { Push-Location $con; flutter analyze lib/guard test/guard; $c = $LASTEXITCODE; Pop-Location; cmd /c exit $c }
Check '(3) flutter test test/guard' { Push-Location $con; flutter test test/guard; $c = $LASTEXITCODE; Pop-Location; cmd /c exit $c }
Check '(4) no network in lib or manifest' {
  $hits = @(Get-ChildItem "$con\lib" -Recurse -Filter *.dart | Select-String -Pattern 'HttpClient|package:http|Socket|WebSocket')
  $hits += @(Select-String -Path "$con\android\app\src\main\AndroidManifest.xml" -Pattern 'android.permission.INTERNET')
  if ($hits.Count -gt 0) { $hits | ForEach-Object { Write-Host "    $_" }; cmd /c exit 1 } else { cmd /c exit 0 }
}
Check '(5) TaskQueue count equals HostApi method count' {
  $src = Get-Content "$con\pigeons\guard_api.dart" -Raw
  $hostBody = [regex]::Match($src, '@HostApi\(\)\s*abstract class GuardHostApi \{(.*?)\n\}', 'Singleline').Groups[1].Value
  $tq = ([regex]::Matches($hostBody, '@TaskQueue\(')).Count
  $m = ([regex]::Matches($hostBody, '\w+\([^)]*\);')).Count
  Write-Host "    TaskQueue=$tq methods=$m"
  if ($tq -eq $m -and $m -gt 0) { cmd /c exit 0 } else { cmd /c exit 1 }
}
if ($script:failed) { Write-Host 'VERIFY 6.1.1: FAIL'; exit 1 }
Write-Host 'VERIFY 6.1.1: PASS'
