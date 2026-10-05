# Verify sub-phase 5.1.2 "Golden tape tests". Ends with VERIFY 5.1.2: PASS.
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$script:failed = $false

function Check([string]$name, [scriptblock]$body) {
  $out = @(& $body 2>&1 | ForEach-Object { "$_" })
  $good = ($LASTEXITCODE -eq 0)
  if (-not $good) { $out | Select-Object -Last 25 | ForEach-Object { Write-Host "    $_" } }
  Write-Host ('{0}  {1}' -f $(if ($good) { 'ok  ' } else { 'FAIL' }), $name)
  if (-not $good) { $script:failed = $true }
}

Check '(1) gradle :brain:tapeTest prints TAPES 3/3 exact' {
  Push-Location guard
  $o = @(& .\gradlew.bat --no-daemon '-Pveil.brainOnly=true' :brain:tapeTest -i 2>&1 | ForEach-Object { "$_" })
  $ec = $LASTEXITCODE
  Pop-Location
  $o | Where-Object { $_ -match 'TAPES|MISMATCH|FAILED|error:' } | Select-Object -First 15 | ForEach-Object { Write-Host "    $_" }
  if ($ec -ne 0 -or -not ($o -match 'TAPES 3/3 exact')) { cmd /c exit 1 } else { cmd /c exit 0 }
}
Check '(2) ktlint guard/brain' {
  & "$env:JAVA_HOME\bin\java.exe" -jar "$env:VEIL_TOOLCHAIN\ktlint\ktlint.jar" "guard/brain/src/**/*.kt" "guard/app/src/androidTest/java/com/veil/guard/brain/**/*.kt"
}
Check '(3) workflow yaml parses' {
  uv run python -c "import yaml; d=yaml.safe_load(open('.github/workflows/brain-tapes.yml')); assert 'jobs' in d"
}
if ($script:failed) { Write-Host 'VERIFY 5.1.2: FAIL'; exit 1 }
Write-Host 'VERIFY 5.1.2: PASS'
