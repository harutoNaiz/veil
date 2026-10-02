# PT-3.1 "Same answers, new engine" (machine part, HEAVY H4; run alone after H1-H3).
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify\pt-3.1.ps1
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$ErrorActionPreference = 'Continue'
$script:failed = $false
$pt = 'data/forge/pt-3.1'

function Step([string]$name, [scriptblock]$body, [int]$expect = 0) {
  & $body | Out-Host
  $code = $LASTEXITCODE
  if ($code -eq $expect) { Write-Host "ok    $name" }
  else { Write-Host "FAIL  $name (exit $code, wanted $expect)"; $script:failed = $true }
}
function OnnxHashes { Get-ChildItem data/forge -Recurse -Filter *.onnx | Sort-Object FullName | ForEach-Object { "$((Get-FileHash $_.FullName -Algorithm SHA256).Hash) $($_.FullName)" } }

Step '1 engine torch' { uv run --locked python -m workshop.forge.proof --engine torch --out "$pt/torch" --concepts cats,spiders }
Step '2 engine onnx' { uv run --locked python -m workshop.forge.proof --engine onnx --out "$pt/onnx" --concepts cats,spiders }
Step '3 compare (>= 98% same decisions)' { uv run --locked python -m workshop.forge.proof --compare "$pt/torch" "$pt/onnx" }

$before = OnnxHashes
foreach ($c in @('bicycles', 'dogs,flowers', 'cats,spiders')) {
  $tag = $c -replace ',', '+'
  Step "4 onnx list $c" { uv run --locked python -m workshop.forge.proof --engine onnx --out "$pt/lists/$tag" --concepts $c --no-gallery }
}
$after = OnnxHashes
if (($before -join "`n") -ne ($after -join "`n")) { Write-Host 'FAIL  4b onnx files changed'; $script:failed = $true } else { Write-Host 'ok    4b onnx files unchanged' }

Step '5 shapes over data/forge' { uv run --locked python -m workshop.forge.common shapes data/forge }

if ($script:failed) { Write-Host 'PT-3.1: FAIL'; exit 1 }
Write-Host 'PT-3.1: PASS'
Write-Host "galleries: $pt/torch/gallery/index.html  $pt/onnx/gallery/index.html"
Write-Host "diff: $pt/diff.md"
