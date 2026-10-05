$ErrorActionPreference = 'Stop'
$env:VEIL_ENV_QUIET = '1'; . "$PSScriptRoot\..\env.ps1"
$veil = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $veil
& powershell -NoProfile -ExecutionPolicy Bypass -File tools\gradle-locked.ps1 '-Pveil.brainOnly=true' :runtime:test
if ($LASTEXITCODE -ne 0) { Write-Host 'VERIFY 3.3.2: FAIL (gradle)'; exit 1 }
$files = Get-ChildItem guard\runtime\src -Recurse -Filter *.kt | ForEach-Object { $_.FullName }
& "$env:JAVA_HOME\bin\java.exe" -jar "$env:VEIL_TOOLCHAIN\ktlint\ktlint.jar" @files
if ($LASTEXITCODE -ne 0) { Write-Host 'VERIFY 3.3.2: FAIL (ktlint)'; exit 1 }
if (Select-String -Path guard\runtime\build.gradle.kts -Pattern 'com\.android|onnxruntime') { Write-Host 'VERIFY 3.3.2: FAIL (deps)'; exit 1 }
Write-Host 'VERIFY 3.3.2: PASS'
