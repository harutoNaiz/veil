# Run one veil Gradle build at a time (7.4 GB laptop): waits on the machine-wide mutex
# Global\veil-gradle, then runs guard\gradlew.bat --no-daemon <args> with the veil environment.
# usage: powershell -NoProfile -ExecutionPolicy Bypass -File tools\gradle-locked.ps1 :app:testDebugUnitTest ...
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$GradleArgs)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'env.ps1')
$mutex = New-Object System.Threading.Mutex($false, 'Global\veil-gradle')
$held = $false
try {
  try { $held = $mutex.WaitOne([TimeSpan]::FromMinutes(45)) }
  catch [System.Threading.AbandonedMutexException] { $held = $true }
  if (-not $held) { Write-Host 'gradle-locked: timed out after 45 min waiting for Global\veil-gradle'; exit 75 }
  Push-Location (Join-Path $repo 'guard')
  try { & .\gradlew.bat --no-daemon @GradleArgs; $code = $LASTEXITCODE } finally { Pop-Location }
  exit $code
} finally {
  if ($held) { $mutex.ReleaseMutex() }
  $mutex.Dispose()
}
