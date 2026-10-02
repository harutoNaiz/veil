# Start Label Studio on demand (Human run only; Builders and agents never run this).
# Label Studio is NOT installed in the project environment: uvx fetches it into its own
# throwaway environment. The first launch downloads it (can take more than 5 minutes).
#
# Human steps (HC-1.2 item 2), run from the veil folder:
#   1. powershell -NoProfile -ExecutionPolicy Bypass -File tools\label-studio.ps1
#      then open http://localhost:8080 and create an account (local only).
#   2. Create a project. Under Labeling Interface > Code paste workshop\labels\ls_config.xml.
#   3. Settings > Cloud Storage > Add Source Storage > Local files, absolute path = <veil>\data\screens,
#      then Sync Storage (or import the tasks file from step 4 instead).
#   4. uv run python -m workshop.labels.ls_convert to-ls --screens data\screens
#        --url-prefix "/data/local-files/?d=screens/" --out data\labels\ls-tasks.json
#      and import data\labels\ls-tasks.json into the project.
#   5. Label every image per docs\labelling-rules.md (tick "clean" on clean ones).
#   6. Export > JSON (not JSON-MIN) to data\labels\ls-export.json, then
#        uv run python -m workshop.labels.ls_convert from-ls --export data\labels\ls-export.json
#          --screens data\screens --labeller labeller-a --out data\labels\screens.json
#        uv run python -m workshop.labels.check --labels data\labels\screens.json --screens data\screens

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$env:LABEL_STUDIO_BASE_DATA_DIR = Join-Path $repo 'data\label-studio'
$env:LABEL_STUDIO_LOCAL_FILES_SERVING_ENABLED = 'true'
$env:LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT = Join-Path $repo 'data'
New-Item -ItemType Directory -Force $env:LABEL_STUDIO_BASE_DATA_DIR | Out-Null
. "$PSScriptRoot\env.ps1"
Set-Location $repo
uvx --python 3.11 label-studio start --port 8080 --no-browser
