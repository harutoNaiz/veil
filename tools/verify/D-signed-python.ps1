# Verify D-signed-python. Run: powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify\D-signed-python.ps1
$ErrorActionPreference = 'Continue'
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$fail = $false
function Check([string]$n, [bool]$ok) { if ($ok) { Write-Host "ok    $n" } else { Write-Host "FAIL  $n"; $script:fail = $true } }

$pins = Get-Content -Raw "$repo\tools\toolchain.json" | ConvertFrom-Json
$py = $pins.archives | Where-Object { $_.name -eq 'python' }
Check 'toolchain.json python 3.11.9 nuget pin' ($py -and $py.version -eq '3.11.9' -and $py.url -like '*nuget.org*python/3.11.9' -and $py.sha256 -match '^[0-9a-f]{64}$' -and -not $pins.python)
Check '.python-version 3.11.9' ((Get-Content "$repo\.python-version" -Raw).Trim() -eq '3.11.9')
Check 'env.ps1 sets UV_PYTHON + downloads never' ((Get-Content "$repo\tools\env.ps1" -Raw) -match 'UV_PYTHON = .*python-3\.11\.9.*python\.exe' -and (Get-Content "$repo\tools\env.ps1" -Raw) -match "UV_PYTHON_DOWNLOADS = 'never'")
Check 'env.sh sets UV_PYTHON + downloads never' ((Get-Content "$repo\tools\env.sh" -Raw) -match 'UV_PYTHON=.*python-3\.11\.9' -and (Get-Content "$repo\tools\env.sh" -Raw) -match 'UV_PYTHON_DOWNLOADS="never"')
$errs = $null; $null = [System.Management.Automation.Language.Parser]::ParseFile("$repo\tools\bootstrap.ps1", [ref]$null, [ref]$errs)
Check 'bootstrap.ps1 parses' ($errs.Count -eq 0)
$b = Get-Content "$repo\tools\bootstrap.ps1" -Raw
Check 'bootstrap has no uv python install' ($b -notmatch "'python', 'install'")

$env:VEIL_ENV_QUIET = '1'
. "$repo\tools\env.ps1"
if (-not (Test-Path $env:UV_PYTHON)) {
  # same path bootstrap uses: download (hash-checked by bootstrap normally) + tar extract
  $dl = Join-Path $env:VEIL_TOOLCHAIN '_downloads\3.11.9'
  if (-not (Test-Path $dl)) { & "$env:SystemRoot\System32\curl.exe" -L --fail -sS -o $dl $py.url }
  Check 'nupkg sha256' ((Get-FileHash -Algorithm SHA256 $dl).Hash.ToLower() -eq $py.sha256)
  $dest = Join-Path $env:VEIL_TOOLCHAIN $py.dir
  New-Item -ItemType Directory -Force $dest | Out-Null
  & "$env:SystemRoot\System32\tar.exe" -xf $dl -C $dest
  Set-Content "$dest\.veil-pin" "$($py.version) $($py.sha256)" -Encoding ASCII
}
Check 'UV_PYTHON exists' (Test-Path $env:UV_PYTHON)
Set-Location $repo
$out = (uv run --locked python -c "import sys,numpy,onnxruntime;print(sys.version)" | Out-String).Trim()
Write-Host $out
Check 'uv run prints 3.11.9' ($LASTEXITCODE -eq 0 -and $out -match '^3\.11\.9 ')
if ($fail) { Write-Host 'VERIFY D-signed-python: FAIL'; exit 1 } else { Write-Host 'VERIFY D-signed-python: PASS' }
