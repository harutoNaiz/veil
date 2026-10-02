# Chapter 1 "SEE" one-command wrapper (sub-phase 1.3.3).
#   Report + calibration + decision:
#     powershell -NoProfile -ExecutionPolicy Bypass -File tools\ch1_see.ps1 [-Set synthetic|public|real] [-Test] [-NoCache]
#   Proof test on fresh screenshots (PT-1.3), makes a gallery and a tally.md template:
#     powershell -NoProfile -ExecutionPolicy Bypass -File tools\ch1_see.ps1 -Fresh <dir> -Concepts cats,spiders
# Sets: public = small real-photo sample (indicative baseline, NOT the frozen test set),
#       synthetic = 1.2's drawn shapes (pipeline check only), real = frozen real set (human run, uses 1 of 3 test runs with -Test).
param(
  [ValidateSet('synthetic', 'public', 'real')][string]$Set = 'synthetic',
  [switch]$Test,
  [switch]$NoCache,
  [string]$Fresh,
  [string]$Concepts = 'cats,spiders'
)
$repo = Split-Path -Parent $PSScriptRoot
$withEnv = Join-Path $PSScriptRoot 'with-env.ps1'
# Weights are fetched once by the orchestrator pre-step; a run never downloads anything.
if (-not $env:HF_HUB_OFFLINE) { $env:HF_HUB_OFFLINE = '1' }
$env:YOLO_AUTOINSTALL = 'False'

function Invoke-Py([string[]]$PyArgs) {
  & powershell -NoProfile -ExecutionPolicy Bypass -File $withEnv uv run python @PyArgs | Out-Host
  return $LASTEXITCODE
}

if ($Fresh) {
  $dir = if ([IO.Path]::IsPathRooted($Fresh)) { $Fresh } else { Join-Path $repo $Fresh }
  if (-not (Test-Path -LiteralPath $dir -PathType Container)) { Write-Host "no such folder: $dir"; exit 2 }
  $dir = (Resolve-Path -LiteralPath $dir).Path
  $run = 'fresh-' + (Split-Path $dir -Leaf) + '-' + ($Concepts -replace ',', '+')
  $started = Get-Date
  $code = Invoke-Py @('-m', 'workshop.twin.run', '--images', $dir, '--concepts', $Concepts, '--gallery', '--out', "data/ch1/runs/$run")
  if ($code -ne 0) { exit $code }
  $index = Join-Path $repo "data\ch1\gallery\$run\index.html"
  if (-not (Test-Path -LiteralPath $index)) {
    # The gallery folder name is chosen by run.py; fall back to the newest index.html written by this run.
    $found = Get-ChildItem -Path (Join-Path $repo 'data\ch1') -Recurse -Filter index.html -ErrorAction SilentlyContinue |
      Where-Object { $_.LastWriteTime -ge $started } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($found) { $index = $found.FullName }
  }
  if (-not (Test-Path -LiteralPath $index)) { Write-Host 'run finished but no index.html was found'; exit 1 }
  $shots = @(Get-ChildItem -LiteralPath $dir -File | Where-Object { $_.Extension -match '^\.(png|jpe?g)$' } | Sort-Object Name)
  $rows = foreach ($s in $shots) { "| $($s.Name) |  |  |  |" }
  $tally = @(
    "# PT-1.3 tally: $run",
    '',
    "Gallery: $index",
    "Concepts: $Concepts (green = label, red = hidden, orange = near miss).",
    'Fill one outcome per screenshot and concept: `covered correctly`, `wrong cover` or `missed`.',
    'Notes: small, cartoon, partly visible, dog/fox/"cat" text.',
    '',
    '| Screenshot | Concept | Outcome | Notes |',
    '| --- | --- | --- | --- |'
  ) + $rows + @('', 'Pass when: tally in line with AC-1.3-01..03 (small sample), no dog/fox/"cat"-text covers, and a new word (bicycles) needed no code or model change.')
  $tallyPath = Join-Path (Split-Path $index -Parent) 'tally.md'
  Set-Content -LiteralPath $tallyPath -Value $tally -Encoding utf8
  Write-Host "GALLERY: $index"
  Write-Host "TALLY: $tallyPath"
  exit 0
}

$py = @('-m', 'workshop.twin.report', '--set', $Set)
if ($Test) { $py += '--test' }
if ($NoCache) { $py += '--no-cache' }
if ($Concepts -ne 'cats,spiders') { $py += @('--concepts', $Concepts) }
exit (Invoke-Py $py)
