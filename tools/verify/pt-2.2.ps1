# PT-2.2 "Look timeline", machine part. Optional: -Session <x.session.json> -IdleStartMs A -IdleEndMs B
param([string]$Session = '', [int]$IdleStartMs = -1, [int]$IdleEndMs = -1)
$env:VEIL_ENV_QUIET = '1'
. "$PSScriptRoot\..\env.ps1"
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$a = @('run', 'python', '-m', 'workshop.twin.timeline', 'pt')
if ($Session) { $a += @('--session', $Session) }
if ($IdleStartMs -ge 0) { $a += @('--idle-start-ms', "$IdleStartMs", '--idle-end-ms', "$IdleEndMs") }
uv @a
exit $LASTEXITCODE
