# Verify sub-phase 3.3.3 "Soak analysis, phone scripts and decision draft".
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$script:failed = $false
function Step([string]$name, [scriptblock]$body) {
  & $body | Out-Host
  if ($LASTEXITCODE -eq 0) { Write-Host "ok    $name" } else { Write-Host "FAIL  $name"; $script:failed = $true }
}
Step '1 gradle :soak:test' { & "$repo\tools\gradle-locked.ps1" '-Pveil.brainOnly=true' ':soak:test' }
Step '2 ktlint' {
  $files = @(Get-ChildItem guard\soak\src -Recurse -Filter *.kt | ForEach-Object { $_.FullName })
  & "$env:JAVA_HOME\bin\java.exe" -jar "$env:VEIL_TOOLCHAIN\ktlint\ktlint.jar" @files
}
Step '3 ruff check' { uv run --locked ruff check workshop/forge/phone }
Step '4 ruff format' { uv run --locked ruff format --check workshop/forge/phone }
Step '5 laptop_ref --limit 2' {
  uv run --locked python -m workshop.forge.phone.laptop_ref --limit 2
  if ($LASTEXITCODE -ne 0) { return }
  $rows = @(Get-Content data\ch3\phone\laptop-fp.csv | Select-Object -Skip 1)
  $ok = ($rows.Count -eq 2) -and (($rows | ForEach-Object { ($_ -split ',').Count - 1 }) -notcontains 0) -and ((($rows[0] -split ',').Count - 1) -eq 768)
  if (-not $ok) { Write-Host 'laptop-fp.csv wrong shape'; $global:LASTEXITCODE = 1 }
}
Step '5b manifests' {
  uv run --locked pytest workshop/forge/phone/test_manifests.py -q
  if ($LASTEXITCODE -ne 0) { return }
  uv run --locked python -m workshop.forge.phone.manifests
  if ($LASTEXITCODE -ne 0) { return }
  if (-not (Get-ChildItem dataorge -Recurse -Filter *.manifest.json)) { $global:LASTEXITCODE = 1 }
}
Step '6 phone scripts parse' {
  $bad = 0
  Get-ChildItem tools\phone\3.3\*.ps1 | ForEach-Object {
    $errs = $null
    [void][System.Management.Automation.Language.Parser]::ParseFile($_.FullName, [ref]$null, [ref]$errs)
    if ($errs.Count) { $errs | Out-Host; $bad++ }
  }
  $global:LASTEXITCODE = $bad
}
Step '7 bench -DryRun' {
  $o = powershell -NoProfile -ExecutionPolicy Bypass -File tools\phone\3.3\bench.ps1 -DryRun | Out-String
  $o | Out-Host
  $global:LASTEXITCODE = $(if ($o -match 'am instrument') { 0 } else { 1 })
}
if ($script:failed) { Write-Host 'VERIFY 3.3.3: FAIL'; exit 1 }
Write-Host 'VERIFY 3.3.3: PASS'
