# Heavy 7.2: select, fetch+embed, disjoint check, dev eval, test eval. Resumable.
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\heavy\7.2-heavy.ps1 [-Mini]
param([switch]$Mini)
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$name = if ($Mini) { 'mini' } else { 'v1' }
$dir = "data/bench/$name"
New-Item -ItemType Directory -Force $dir | Out-Null
$log = "data/bench/heavy-$name.log"
$failed = $false

function Run([string]$label, [scriptblock]$body) {
  "== $label $(Get-Date -Format s)" | Tee-Object -FilePath $log -Append | Out-Host
  & $body 2>&1 | Tee-Object -FilePath $log -Append | Out-Host
  if ($LASTEXITCODE -ne 0) { "FAILED $label" | Tee-Object -FilePath $log -Append | Out-Host; $script:failed = $true }
}

$flags = if ($Mini) { @('--mini') } else { @() }
if (-not (Test-Path "$dir/selection.json")) {
  Run 'select' { uv run --locked python -m workshop.twin.bench.select --out $dir @flags }
} else { "skip select (exists)" | Tee-Object -FilePath $log -Append | Out-Host }
if (-not $failed) { Run 'fetch_embed' { uv run --locked --with onnxruntime-directml python -m workshop.twin.bench.fetch_embed --out $dir --engine onnx --provider dml --threads 32 } }
if (-not $failed) { Run 'disjoint' { uv run --locked python -m workshop.twin.bench.disjoint --bench $dir --bank data/bank/v1 } }
if (-not $failed) { Run 'eval dev' { uv run --locked python -m workshop.twin.bench.evaluate --bench $dir --bank data/bank/v1 --split dev } }
if (-not $failed) {
  if ($Mini) { Run 'eval test (dry)' { uv run --locked python -m workshop.twin.bench.evaluate --bench $dir --bank data/bank/v1 --split test --dry } }
  else { Run 'eval test' { uv run --locked python -m workshop.twin.bench.evaluate --bench $dir --bank data/bank/v1 --split test --note baseline } }
}

$verdict = if ($failed) { 'HEAVY 7.2: FAIL' } else { 'HEAVY 7.2: PASS' }
$verdict | Tee-Object -FilePath $log -Append | Out-Host
if ($failed) { exit 1 }
