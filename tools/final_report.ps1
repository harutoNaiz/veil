$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\env.ps1"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo
$w = Join-Path $repo 'tools\with-env.ps1'
& powershell -NoProfile -ExecutionPolicy Bypass -File $w uv run --locked python -m workshop.final.report --out docs/reports/final.md
if ($LASTEXITCODE -ne 0) { exit 1 }
& powershell -NoProfile -ExecutionPolicy Bypass -File $w uv run --locked python -m workshop.final.lint_report docs/reports/final.md
exit $LASTEXITCODE
