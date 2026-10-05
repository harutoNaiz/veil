# PENDING-HUMAN: needs the phone. Place box, scroll 30 s per app, write data/ch4/drift.md.
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
Set-Location (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
uv run --locked python -m workshop.overlay.glue_run
