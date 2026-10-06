# Veil one-command setup. Installs a portable, project-local toolchain (no admin, no PATH or registry changes).
#   powershell -ExecutionPolicy Bypass -File tools\bootstrap.ps1
#   -ToolchainDir <path>  where to install (default rule: see tools\toolchain-dir.ps1; no spaces allowed)
#   -CheckOnly            only verify what is installed
#   -NoRepoSetup          skip "uv sync" and the pre-commit hook install
# Safe to run again: finished components are skipped. All pins live in tools\toolchain.json.
param([string]$ToolchainDir = "", [switch]$CheckOnly, [switch]$NoRepoSetup)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$repo = Split-Path -Parent $PSScriptRoot
. "$PSScriptRoot\toolchain-dir.ps1"
$tc = Resolve-VeilToolchainDir -RepoRoot $repo -Override $ToolchainDir
$env:VEIL_TOOLCHAIN = $tc

$dl = Join-Path $tc '_downloads'
foreach ($d in @($tc, $dl) + @('uv', 'pip', 'gradle', 'pub', 'huggingface', 'torch', 'ultralytics', 'pre-commit' | ForEach-Object { Join-Path $tc "cache\$_" })) {
  New-Item -ItemType Directory -Force -Path $d | Out-Null
}
$logFile = Join-Path $tc 'bootstrap.log'

function Write-Log([string]$Message) {
  $line = '[{0}] {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message
  Add-Content -LiteralPath $logFile -Value $line -Encoding UTF8
}
function Say([string]$Message) { Write-Host $Message; Write-Log $Message }

# Runs a native program, captures stdout+stderr, never throws on a non-zero exit code.
function Invoke-Native([string]$Exe, [string[]]$Arguments, [string]$StdinText = $null) {
  $saved = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  $global:LASTEXITCODE = $null
  $out = @()
  try {
    Write-Log ("RUN {0} {1}" -f $Exe, ($Arguments -join ' '))
    if ($StdinText) {
      $out = @($StdinText | & $Exe @Arguments 2>&1 | ForEach-Object { "$_" })
    } else {
      $out = @(& $Exe @Arguments 2>&1 | ForEach-Object { "$_" })
    }
  } catch {
    $out = @($out) + @("EXCEPTION: $($_.Exception.Message)")
  } finally {
    $ErrorActionPreference = $saved
  }
  $code = $global:LASTEXITCODE
  if ($null -eq $code) { $code = -1 }
  foreach ($l in $out) { Write-Log "  | $l" }
  Write-Log "  exit code $code"
  return [pscustomobject]@{ ExitCode = $code; Output = [string[]]$out }
}

function Get-PinHash($a) { if ($a.sha256) { return $a.sha256 } else { return $a.sha1 } }
function Get-ArchiveDir($a) { return (Join-Path $tc ($a.dir -replace '/', '\')) }
function Test-ArchiveInstalled($a) {
  $marker = Join-Path (Get-ArchiveDir $a) '.veil-pin'
  if (-not (Test-Path -LiteralPath $marker)) { return $false }
  return ((Get-Content -LiteralPath $marker -Raw).Trim() -eq ('{0} {1}' -f $a.version, (Get-PinHash $a)))
}
function Test-FileHashMatches([string]$File, $a) {
  $algo = 'SHA256'
  if ($a.sha1) { $algo = 'SHA1' }
  return ((Get-FileHash -Algorithm $algo -LiteralPath $File).Hash.ToLower() -eq (Get-PinHash $a).ToLower())
}

function Get-Archive($a) {
  $name = [System.Uri]::UnescapeDataString(($a.url -split '/')[-1])
  $file = Join-Path $dl $name
  if ((Test-Path -LiteralPath $file) -and (Test-FileHashMatches $file $a)) {
    Say "  $name already downloaded and verified"
    return $file
  }
  if (Test-Path -LiteralPath $file) { Remove-Item -LiteralPath $file -Force }
  $part = "$file.part"
  $curl = Join-Path $env:SystemRoot 'System32\curl.exe'
  $curlArgs = @('-L', '--fail', '--retry', '5', '--retry-delay', '5', '-sS', '-o', $part, $a.url)
  $resumed = $false
  if (Test-Path -LiteralPath $part) { $curlArgs = @('-C', '-') + $curlArgs; $resumed = $true; Say "  resuming $name" }
  else { Say "  downloading $name" }
  $r = Invoke-Native $curl $curlArgs
  if ($r.ExitCode -ne 0 -and $resumed) {
    Remove-Item -LiteralPath $part -Force -ErrorAction SilentlyContinue
    Say "  resume failed, downloading $name again from the start"
    $r = Invoke-Native $curl @('-L', '--fail', '--retry', '5', '--retry-delay', '5', '-sS', '-o', $part, $a.url)
  }
  if ($r.ExitCode -ne 0) { throw "download failed (curl exit $($r.ExitCode)): $($a.url)" }
  Move-Item -LiteralPath $part -Destination $file -Force
  if (-not (Test-FileHashMatches $file $a)) {
    Remove-Item -LiteralPath $file -Force
    throw "checksum mismatch for $name (expected $(Get-PinHash $a)); file deleted"
  }
  return $file
}

function Install-Archive($a, [string]$file) {
  $dest = Get-ArchiveDir $a
  if (Test-Path -LiteralPath $dest) { Remove-Item -LiteralPath $dest -Recurse -Force }
  New-Item -ItemType Directory -Force -Path $dest | Out-Null
  if ($a.file) {
    Copy-Item -LiteralPath $file -Destination (Join-Path $dest $a.file) -Force
  } else {
    $tarArgs = @('-xf', $file, '-C', $dest)
    if ($a.strip -gt 0) { $tarArgs += @('--strip-components', "$($a.strip)") }
    $r = Invoke-Native (Join-Path $env:SystemRoot 'System32\tar.exe') $tarArgs
    if ($r.ExitCode -ne 0) { throw "extract failed for $($a.name) (tar exit $($r.ExitCode))" }
  }
  Set-Content -LiteralPath (Join-Path $dest '.veil-pin') -Value ('{0} {1}' -f $a.version, (Get-PinHash $a)) -Encoding ASCII
}

function Load-VeilEnv {
  $env:VEIL_ENV_QUIET = '1'
  . "$PSScriptRoot\env.ps1"
}

function Get-FirstSource([string]$Name) {
  $c = @(Get-Command $Name -ErrorAction SilentlyContinue)
  if ($c.Count -eq 0) { return '' }
  return [string]$c[0].Source
}
function Test-UnderToolchain([string]$Path) {
  return ($Path -and $Path.StartsWith($tc, [System.StringComparison]::OrdinalIgnoreCase))
}

Write-Log "=== bootstrap start $(Get-Date -Format 's') CheckOnly=$($CheckOnly.IsPresent) toolchain=$tc ==="
Say "Toolchain: $tc"

try {
  $pins = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'toolchain.json') | ConvertFrom-Json

  if (-not $CheckOnly) {
    # 1. free space (only when something has to be installed)
    $missing = @($pins.archives | Where-Object { -not (Test-ArchiveInstalled $_) })
    if ($missing.Count -gt 0) {
      $free = (New-Object System.IO.DriveInfo ($tc.Substring(0, 1))).AvailableFreeSpace
      if ($free -lt 15GB) { throw ('Not enough free space on drive {0}: {1:N1} GB free, 15 GB needed.' -f $tc.Substring(0, 1), ($free / 1GB)) }
    }

    # 2. archives
    foreach ($a in $pins.archives) {
      if (Test-ArchiveInstalled $a) { Say "$($a.name) $($a.version): already installed"; continue }
      Say "$($a.name) $($a.version): installing"
      $file = Get-Archive $a
      Install-Archive $a $file
      Say "$($a.name) $($a.version): installed"
    }

    # 3. environment for the rest of this run
    Load-VeilEnv

    # 4. Android SDK licences (accepted on the user's behalf; logged in bootstrap.log)
    $sdkm = Join-Path $env:ANDROID_HOME 'cmdline-tools\latest\bin\sdkmanager.bat'
    $sdkRoot = "--sdk_root=$env:ANDROID_HOME"
    $licFile = Join-Path $env:ANDROID_HOME 'licenses\android-sdk-license'
    Say 'Android SDK: accepting licences (see bootstrap.log)'
    # cmdline-tools 19.0: piping "y" into --licenses does not work (first prompt's reader swallows stdin), so
    # try once with empty stdin, then write the known hash of the accepted android-sdk-license text.
    $cmd = Join-Path $env:SystemRoot 'System32\cmd.exe'
    $null = Invoke-Native $cmd @('/c', "`"$sdkm`" $sdkRoot --licenses < NUL")
    if (-not (Test-Path -LiteralPath $licFile)) {
      New-Item -ItemType Directory -Force -Path (Split-Path $licFile) | Out-Null
      [System.IO.File]::WriteAllText($licFile, "`n24333f8a63b6825ea9c5514f83c2829b004d1fee")
      Write-Log 'licence: wrote licenses\android-sdk-license (hash 24333f8a63b6825ea9c5514f83c2829b004d1fee, accepted on the user''s behalf)'
    }

    # 5. Android SDK packages
    Say ('Android SDK: installing ' + ($pins.androidPackages -join ', '))
    $pkgList = (@($pins.androidPackages | ForEach-Object { '"' + $_ + '"' })) -join ' '
    $r = Invoke-Native $cmd @('/c', "`"$sdkm`" $sdkRoot --install $pkgList < NUL")
    if ($r.ExitCode -ne 0) { throw "sdkmanager --install failed (exit $($r.ExitCode)); see $logFile" }
    if (-not (Test-Path -LiteralPath $licFile)) { throw 'Android SDK licences were not accepted (licenses\android-sdk-license missing).' }
    Write-Log ('licence files: ' + ((Get-ChildItem -LiteralPath (Join-Path $env:ANDROID_HOME 'licenses') | ForEach-Object Name) -join ', '))

    # 6. Python: signed python.org 3.11.9 (NuGet package, installed with the archives above; Smart App Control blocks uv-managed builds)
    $pyExe = Join-Path $tc 'python-3.11.9\tools\python.exe'
    if (-not (Test-Path -LiteralPath $pyExe)) { throw "python 3.11.9 missing: $pyExe" }
    Say "Python: $pyExe"

    # 7. Flutter: first run fetches the Dart SDK; then Android artifacts. doctor is logged only.
    Say 'Flutter: first run (Dart SDK) and precache for Android'
    $flutter = Join-Path $tc 'flutter\bin\flutter.bat'
    $r = Invoke-Native $flutter @('--version')
    if ($r.ExitCode -ne 0) { throw "flutter --version failed (exit $($r.ExitCode)); see $logFile" }
    $r = Invoke-Native $flutter @('precache', '--android')
    if ($r.ExitCode -ne 0) { throw "flutter precache failed (exit $($r.ExitCode)); see $logFile" }
    $null = Invoke-Native $flutter @('doctor', '-v')

    # 8. repo setup
    if (-not $NoRepoSetup -and (Test-Path -LiteralPath (Join-Path $repo 'uv.lock'))) {
      Say 'Repo: uv sync --locked'
      Push-Location $repo
      try {
        $r = Invoke-Native 'uv' @('sync', '--locked')
        if ($r.ExitCode -ne 0) { throw "uv sync --locked failed (exit $($r.ExitCode)); see $logFile" }
        if ((Test-Path -LiteralPath (Join-Path $repo '.git')) -and (Test-Path -LiteralPath (Join-Path $repo '.pre-commit-config.yaml'))) {
          Say 'Repo: installing the pre-commit hook'
          $r = Invoke-Native 'uv' @('run', '--no-sync', 'pre-commit', 'install')
          if ($r.ExitCode -ne 0) { throw "pre-commit install failed (exit $($r.ExitCode)); see $logFile" }
        }
      } finally { Pop-Location }
    }
  }

  # 3. checks (always)
  Load-VeilEnv
  $rows = New-Object System.Collections.ArrayList
  function Add-Row([string]$Component, [string]$Expected, [string]$Found, [bool]$Ok) {
    [void]$rows.Add([pscustomobject]@{ Component = $Component; Expected = $Expected; Found = $Found; Ok = $Ok })
  }
  function First-Line($r) { return (@($r.Output | Where-Object { $_.Trim() }) | Select-Object -First 1) }

  # uv
  $r = Invoke-Native 'uv' @('--version'); $src = Get-FirstSource 'uv'; $line = First-Line $r
  $ver = if ($line -match '^uv (\S+)') { $Matches[1] } else { $line }
  Add-Row 'uv' '0.12.21 under toolchain' ("$ver @ $src") (($r.ExitCode -eq 0) -and ($line -match '0\.12\.21') -and (Test-UnderToolchain $src))
  # java
  $r = Invoke-Native 'java' @('-version'); $src = Get-FirstSource 'java'; $line = First-Line $r
  $ver = if ($line -match '"([^"]+)"') { $Matches[1] } else { $line }
  Add-Row 'java' '"17.0.20.1" under toolchain' ("$ver @ $src") (($r.ExitCode -eq 0) -and ((($r.Output -join "`n")) -match '"17\.0\.20\.1"') -and (Test-UnderToolchain $src))
  # gradle
  $r = Invoke-Native 'gradle' @('--version'); $txt = ($r.Output -join "`n")
  Add-Row 'gradle' 'Gradle 9.3.1' ($(if ($txt -match 'Gradle\s+(\S+)') { "Gradle $($Matches[1])" } else { 'not found' })) (($r.ExitCode -eq 0) -and ($txt -match 'Gradle 9\.3\.1'))
  # android-sdk
  $sdkm = Join-Path $env:ANDROID_HOME 'cmdline-tools\latest\bin\sdkmanager.bat'
  $r = Invoke-Native $sdkm @("--sdk_root=$env:ANDROID_HOME", '--list_installed'); $txt = ($r.Output -join "`n")
  $need = @('platforms;android-36', 'build-tools;36.0.0', 'ndk;28.2.13676358', 'platform-tools')
  # cmdline-tools 23.0 prints package ids with "/" (build-tools/36.0.0); older ones used ";".
  $have = @($need | Where-Object { $txt -match ([regex]::Escape($_) -replace ';', '[;/]') })
  Add-Row 'android-sdk' ($need -join ', ') ($have -join ', ') (($r.ExitCode -eq 0) -and ($have.Count -eq $need.Count))
  # adb
  $r = Invoke-Native 'adb' @('version'); $src = Get-FirstSource 'adb'; $line = First-Line $r
  $ver = if ((($r.Output -join "`n")) -match 'Version (\S+)') { "Android Debug Bridge $($Matches[1])" } else { $line }
  Add-Row 'adb' 'Android Debug Bridge under toolchain' ("$ver @ $src") (($r.ExitCode -eq 0) -and ($line -match 'Android Debug Bridge') -and (Test-UnderToolchain $src))
  # flutter
  $r = Invoke-Native (Join-Path $tc 'flutter\bin\flutter.bat') @('--version', '--machine'); $txt = ($r.Output -join "`n"); $fv = ''
  if ($txt -match '(?s)\{.*\}') { try { $fv = [string](($Matches[0] | ConvertFrom-Json).frameworkVersion) } catch { $fv = '' } }
  Add-Row 'flutter' 'frameworkVersion 3.47.6' ($(if ($fv) { $fv } else { 'unreadable' })) (($r.ExitCode -eq 0) -and ($fv -eq '3.47.6'))
  # scrcpy
  $r = Invoke-Native 'scrcpy' @('--version'); $line = First-Line $r
  Add-Row 'scrcpy' 'scrcpy 4.1' $line (($r.ExitCode -eq 0) -and ($line -match '^scrcpy 4\.1'))
  # ffmpeg
  $r = Invoke-Native 'ffmpeg' @('-version'); $line = First-Line $r
  Add-Row 'ffmpeg' '9.0.2' $line (($r.ExitCode -eq 0) -and ($line -match '9\.0\.2'))
  # ktlint
  $r = Invoke-Native 'java' @('-jar', (Join-Path $tc 'ktlint\ktlint.jar'), '--version'); $line = First-Line $r
  Add-Row 'ktlint' '1.8.0' $line (($r.ExitCode -eq 0) -and ($line -match '1\.8\.0'))
  # python
  # Run from the toolchain dir: inside the repo, "uv python find" would return the repo's .venv python.
  Push-Location $tc
  try { $r = Invoke-Native 'uv' @('python', 'find') } finally { Pop-Location }
  $line = First-Line $r
  Add-Row 'python' '3.11.9 under toolchain\python-3.11.9' $line (($r.ExitCode -eq 0) -and (Test-UnderToolchain $line) -and ($line -like "$tc\python-3.11.9\*"))
  # repo-venv
  if (Test-Path -LiteralPath (Join-Path $repo '.venv')) {
    Push-Location $repo
    try { $r = Invoke-Native (Join-Path $repo '.venv\Scripts\python.exe') @('--version') } finally { Pop-Location }
    $line = First-Line $r
    Add-Row 'repo-venv' 'Python 3.11.9' $line (($r.ExitCode -eq 0) -and ($line -match '^Python 3\.11\.9'))
  }

  Say ''
  Say ('{0,-11} | {1,-34} | {2,-60} | {3}' -f 'component', 'expected', 'found', 'status')
  foreach ($row in $rows) {
    $found = [string]$row.Found
    Say ('{0,-11} | {1,-34} | {2,-60} | {3}' -f $row.Component, $row.Expected, $found, $(if ($row.Ok) { 'OK' } else { 'FAIL' }))
  }
  $bad = @($rows | Where-Object { -not $_.Ok } | ForEach-Object { $_.Component })
  if ($bad.Count -eq 0) { Say 'BOOTSTRAP OK'; exit 0 }
  Say ('BOOTSTRAP FAILED: ' + ($bad -join ', '))
  exit 1
} catch {
  Say ('BOOTSTRAP FAILED: ' + $_.Exception.Message)
  Write-Log ($_ | Out-String)
  exit 1
}
