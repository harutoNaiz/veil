# Heavy 7.1: build the reference bank, check it, run the auto-threshold eval. Resumable.
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\heavy\7.1-heavy.ps1 [-Mini]
param([switch]$Mini)
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$name = if ($Mini) { 'mini-gpu' } else { 'v1' }
$dir = "data/bank/$name"
New-Item -ItemType Directory -Force "data/bank" | Out-Null
$log = "data/bank/heavy-$name.log"
$failed = $false

function Run([string]$label, [scriptblock]$body) {
  "== $label $(Get-Date -Format s)" | Tee-Object -FilePath $log -Append | Out-Host
  & $body 2>&1 | Tee-Object -FilePath $log -Append | Out-Host
  if ($LASTEXITCODE -ne 0) { "FAILED $label" | Tee-Object -FilePath $log -Append | Out-Host; $script:failed = $true }
}

if (-not (Test-Path "$dir/bank.bin") -or -not (Test-Path "$dir/vocab.bin")) {
  $lim, $ui, $voc = if ($Mini) { 1900, 100, 1000 } else { 28500, 1500, 5000 }
  Run 'build_bank' { uv run --locked --with onnxruntime-directml python -m workshop.twin.bank.build_bank --engine onnx --provider dml --out $dir --limit $lim --ui $ui --vocab-limit $voc }
} else { "skip build_bank (exists)" | Tee-Object -FilePath $log -Append | Out-Host }
if (-not $failed) { Run 'bank_check' { uv run --locked --with onnxruntime-directml python -m workshop.twin.bank.bank_check --engine onnx --provider dml --bank $dir --sample 64 } }
if (-not $failed) { Run 'autocal_eval' { uv run --locked python -m workshop.twin.autocal_eval --bank $dir } }

$verdict = if ($failed) { 'HEAVY 7.1: FAIL' } else { 'HEAVY 7.1: PASS' }
$verdict | Tee-Object -FilePath $log -Append | Out-Host
if ($failed) { exit 1 }
