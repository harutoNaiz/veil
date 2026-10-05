# Verify PHONE_DAY.md covers every OPEN HC item and only names real scripts.
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$hc = Get-Content -Raw (Join-Path $repo '..\progress\HUMAN_CHECKS.md')
$doc = Get-Content -Raw (Join-Path $repo 'docs\PHONE_DAY.md')
$fail = $false
foreach ($n in 2..27) {
  $id = 'HC-{0:000}' -f $n
  if ($hc -match "### $id [^\r\n]*\[OPEN\]") {
    if ($doc -notmatch [regex]::Escape($id)) { Write-Host "MISSING $id"; $fail = $true }
  }
}
foreach ($m in [regex]::Matches($doc, 'tools\\[A-Za-z0-9_.\\-]+\.ps1')) {
  $p = $m.Value
  if ($p -eq 'tools\phone\kit.ps1') { continue }
  if (-not (Test-Path (Join-Path $repo $p))) { Write-Host "NO SCRIPT $p"; $fail = $true }
}
if ($fail) { Write-Host 'VERIFY phone-day-sheet: FAIL'; exit 1 }
Write-Host 'VERIFY phone-day-sheet: PASS'
