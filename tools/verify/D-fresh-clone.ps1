$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot '..\..')
Set-Location $root
$env:VEIL_ENV_QUIET = '1'
. .\tools\env.ps1
$ok = $true
function Check($c, $m) { if (-not $c) { Write-Host "FAIL: $m"; $script:ok = $false } }
$py = 'workshop/hello.py', 'contracts/scripts/gen_python.py'

& uv run --locked ruff check @py
Check ($LASTEXITCODE -eq 0) 'ruff check'
& uv run --locked ruff format --check @py
Check ($LASTEXITCODE -eq 0) 'ruff format --check'

$out = (& uv run --locked python -m workshop.hello | Out-String)
Check ($LASTEXITCODE -eq 0) 'workshop.hello exit code'
Check ($out -match 'Veil workshop OK') 'hello output lacks "Veil workshop OK"'

& uv run --locked python contracts/scripts/gen_python.py --check
Check ($LASTEXITCODE -eq 0) 'gen_python.py --check'

& uv run --locked pytest contracts -q
Check ($LASTEXITCODE -eq 0) 'pytest contracts'

if ($ok) { 'VERIFY D-fresh-clone: PASS' } else { 'VERIFY D-fresh-clone: FAIL' }
