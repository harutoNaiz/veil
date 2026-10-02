# Verify sub-phase 1.2.1 "Collect screenshots". Run from anywhere:
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify\1.2.1.ps1
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$script:failed = $false

function Step([string]$name, [scriptblock]$body, [int]$expect = 0) {
  & $body | Out-Host
  $code = $LASTEXITCODE
  if ($code -eq $expect) { Write-Host "ok    $name" }
  else { Write-Host "FAIL  $name (exit $code, wanted $expect)"; $script:failed = $true }
}

$synth = 'data/synth/1.2.1'

Step '1 pytest workshop/screens' { uv run pytest workshop/screens -q }
Step '2 synth CLI (75 + 2 near-dupes)' { uv run python -m workshop.screens.synth --out $synth --n 75 --near-dupes 2 }
Step '3 meta_check on the synthetic set' { uv run python -m workshop.screens.meta_check --screens $synth }

# 4 capture with no phone must exit 3. A stub adb that lists no device keeps this independent
# of whatever is plugged in (a real phone must never be driven by a verify run).
$stubDir = Join-Path $repo "$synth/_stub"
New-Item -ItemType Directory -Force $stubDir | Out-Null
Set-Content -Path "$stubDir/adb.cmd" -Value "@echo List of devices attached" -Encoding ascii
$realAdb = $env:ADB
$env:ADB = "$stubDir\adb.cmd"
Step '4 capture without a phone exits 3' {
  uv run python -m workshop.screens.capture --app instagram --surface explore --mode dark --source test-acct-A --count 3 --out "$synth/_nophone"
} 3
$env:ADB = $realAdb
Remove-Item -Recurse -Force $stubDir -ErrorAction SilentlyContinue
if (Test-Path "$synth/_nophone") { Write-Host 'FAIL  4b capture created files without a phone'; $script:failed = $true }

# 5 data/ is git-ignored and nothing but data/README.md is tracked
git check-ignore -q data/screens/x.png
if ($LASTEXITCODE -eq 0) { Write-Host 'ok    5a data/screens is git-ignored' }
else { Write-Host 'FAIL  5a data/screens is not git-ignored'; $script:failed = $true }
$tracked = @(git ls-files data)
if ($tracked.Count -eq 1 -and $tracked[0] -eq 'data/README.md') { Write-Host 'ok    5b git tracks only data/README.md' }
else { Write-Host "FAIL  5b tracked under data/: $($tracked -join ', ')"; $script:failed = $true }

Step '6 ruff' { uv run ruff check workshop/screens }

if ($script:failed) { Write-Host 'VERIFY 1.2.1: FAIL'; exit 1 }
Write-Host 'VERIFY 1.2.1: PASS'
exit 0
