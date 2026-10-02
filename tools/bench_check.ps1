$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\env.ps1"
Set-Location (Split-Path -Parent $PSScriptRoot)
& uv run --locked python -m workshop.bench.bench_check @args
exit $LASTEXITCODE
