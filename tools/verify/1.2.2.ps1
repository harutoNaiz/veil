# Verify sub-phase 1.2.2 "Label them". Run from D:\iqoo finale\veil:
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify\1.2.2.ps1
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$script:failed = $false

function Step([string]$name, [bool]$ok) {
    if ($ok) { Write-Host "PASS $name" } else { Write-Host "FAIL $name"; $script:failed = $true }
}

# 1. unit tests
uv run pytest workshop/labels -q
Step '1 pytest workshop/labels' ($LASTEXITCODE -eq 0)

# 2. Label Studio config matches the converter constants
uv run python -m workshop.labels.ls_convert check-config
Step '2 ls_config.xml matches constants' ($LASTEXITCODE -eq 0)

# 3. rules document has the required rules
$doc = Join-Path $repo 'docs\labelling-rules.md'
$ok3 = Test-Path $doc
if ($ok3) {
    $text = Get-Content -Raw $doc
    foreach ($needle in '30%', 'cat-emoji', 'cat-text', 'wholeElement') {
        if (-not $text.Contains($needle)) { $ok3 = $false; Write-Host "  missing '$needle'" }
    }
}
Step '3 docs/labelling-rules.md' $ok3

# 4. label-studio.ps1 parses (not run)
$ok4 = $true
try {
    [void][scriptblock]::Create((Get-Content -Raw (Join-Path $repo 'tools\label-studio.ps1')))
} catch { $ok4 = $false; Write-Host "  $($_.Exception.Message)" }
Step '4 tools/label-studio.ps1 parses' $ok4

# 5. ruff
uv run ruff check workshop/labels
Step '5 ruff' ($LASTEXITCODE -eq 0)

if ($script:failed) { Write-Host 'VERIFY 1.2.2: FAIL'; exit 1 }
Write-Host 'VERIFY 1.2.2: PASS'
exit 0
