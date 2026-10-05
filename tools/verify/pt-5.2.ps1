# Proof test 5.2 "The cat feed" (PENDING-HUMAN: needs 5.2-W live wiring + phone). See SPEC section 5.
# Steps: install Guard + Test Feed (Balanced); drive the known cat/spider/lookalike/clean feed with
# workshop/bench/drive.py; pull debug.jsonl + feedlog.jsonl; run the checker below.
param([string]$Debug = 'debug.jsonl', [string]$Feed = 'feedlog.jsonl')
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
if (-not ((Test-Path $Debug) -and (Test-Path $Feed))) { Write-Host 'PENDING-HUMAN: pull debug.jsonl and feedlog.jsonl from the phone first'; exit 2 }
uv run --locked python -m workshop.guardcheck.cat_feed $Debug $Feed
exit $LASTEXITCODE
