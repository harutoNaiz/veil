# Verify sub-phase 5.2.3 "Layer 1 and the text lane".
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$failed = $false
function Step([string]$name, [scriptblock]$body) {
  & $body | Out-Host
  if ($LASTEXITCODE -eq 0) { Write-Host "ok    $name" } else { Write-Host "FAIL  $name (exit $LASTEXITCODE)"; $script:failed = $true }
}
Step '1 conductor tests' { powershell -NoProfile -ExecutionPolicy Bypass -File tools\gradle-locked.ps1 '-Pveil.brainOnly=true' :conductor:test --tests "com.veil.conductor.layer1.*" --tests "com.veil.conductor.text.*" }
Step '2 app compile' { powershell -NoProfile -ExecutionPolicy Bypass -File tools\gradle-locked.ps1 :app:compileDebugKotlin }
Step '3 ktlint' { & "$env:JAVA_HOME\bin\java.exe" -jar "$env:VEIL_TOOLCHAIN\ktlint\ktlint.jar" -F "guard/conductor/src/main/kotlin/com/veil/conductor/layer1/*.kt" "guard/conductor/src/main/kotlin/com/veil/conductor/text/*.kt" "guard/conductor/src/test/kotlin/com/veil/conductor/layer1/*.kt" "guard/conductor/src/test/kotlin/com/veil/conductor/text/*.kt" "guard/app/src/main/java/com/veil/guard/wire/MlKitOcr.kt" }
if ($failed) { Write-Host 'VERIFY 5.2.3: FAIL'; exit 1 } else { Write-Host 'VERIFY 5.2.3: PASS' }
