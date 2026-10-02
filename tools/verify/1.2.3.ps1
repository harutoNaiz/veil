# Verify sub-phase 1.2.3 "Split, freeze and score".
# Run from the repo root:  powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify\1.2.3.ps1
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$failed = $false

function Check([string]$name, [scriptblock]$body) {
  $out = & $body 2>&1 | ForEach-Object { "$_" }
  $ok = ($LASTEXITCODE -eq 0)
  if (-not $ok) { $out | Select-Object -Last 25 | ForEach-Object { Write-Host "    $_" } }
  Write-Host ("{0}  {1}" -f $(if ($ok) { 'ok  ' } else { 'FAIL' }), $name)
  if (-not $ok) { $script:failed = $true }
}

Check '(1) pytest workshop/eval: scorer, hand-worked case, dhash, split, freeze, counts' {
  uv run pytest workshop/eval -q
}

Check '(2) docs/datasets.md has the veil:testset block, seed 12, dHash 256 / 20 and the scoring rules' {
  $t = Get-Content -Raw 'docs\datasets.md'
  $need = @('<!-- veil:testset -->', '<!-- /veil:testset -->', 'checksum: PENDING-HUMAN', 'seed',
            '12', '256', 'distance 20', 'IoU >= 0.3', '0.7')
  $missing = @($need | Where-Object { -not $t.Contains($_) })
  if ($missing.Count -gt 0) { Write-Output "missing: $missing"; $global:LASTEXITCODE = 1 }
  else { $global:LASTEXITCODE = 0 }
}

Check '(3) ruff check workshop/eval' {
  uv run ruff check workshop/eval
}

if ($failed) { Write-Host 'VERIFY 1.2.3: FAIL'; exit 1 }
Write-Host 'VERIFY 1.2.3: PASS'
exit 0
