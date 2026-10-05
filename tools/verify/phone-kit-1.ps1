$env:VEIL_ENV_QUIET = '1'
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$kit = 'tools\phone\kit.ps1'; $fail = $false
$errs = $null; [void][System.Management.Automation.Language.Parser]::ParseFile((Resolve-Path $kit), [ref]$null, [ref]$errs)
if ($errs.Count -eq 0) { Write-Host 'ok    parse' } else { Write-Host 'FAIL  parse'; $fail = $true }
powershell -NoProfile -ExecutionPolicy Bypass -File $kit -DryRun | Out-Host
if ($LASTEXITCODE -eq 0) { Write-Host 'ok    dry-run' } else { Write-Host 'FAIL  dry-run'; $fail = $true }
powershell -NoProfile -ExecutionPolicy Bypass -File $kit | Out-Host
$n = @(Select-String -Path data\phone-kit\MANIFEST.txt -Pattern '\.apk  ').Count
if ($n -ge 4) { Write-Host "ok    manifest lists $n APKs" } else { Write-Host "FAIL  manifest APKs=$n"; $fail = $true }
powershell -NoProfile -ExecutionPolicy Bypass -File $kit -Push | Out-Host
if ($LASTEXITCODE -eq 2) { Write-Host 'ok    push no device -> 2' } else { Write-Host "FAIL  push exit $LASTEXITCODE (device attached?)"; $fail = $true }
if ($fail) { Write-Host 'VERIFY phone-kit-1: FAIL'; exit 1 } else { Write-Host 'VERIFY phone-kit-1: PASS' }
