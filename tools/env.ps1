# Veil environment for the CURRENT PowerShell session only.
# Usage (from the repo root):  . .\tools\env.ps1
# It never touches the registry, user/system environment variables or profile scripts.
$repo = Split-Path -Parent $PSScriptRoot
. "$PSScriptRoot\toolchain-dir.ps1"
$tc = Resolve-VeilToolchainDir -RepoRoot $repo

$env:VEIL_TOOLCHAIN = $tc
$env:VEIL_REPO = $repo
$env:JAVA_HOME = "$tc\jdk17"
$env:ANDROID_HOME = "$tc\android-sdk"
$env:ANDROID_SDK_ROOT = "$tc\android-sdk"
$env:ADB = "$tc\android-sdk\platform-tools\adb.exe"
$env:GRADLE_USER_HOME = "$tc\cache\gradle"
$env:PUB_CACHE = "$tc\cache\pub"
$env:UV_CACHE_DIR = "$tc\cache\uv"
$env:UV_PYTHON_INSTALL_DIR = "$tc\python"
$env:UV_PYTHON_PREFERENCE = 'only-managed'
$env:UV_PYTHON_INSTALL_BIN = '0'
$env:UV_PYTHON_INSTALL_REGISTRY = '0'
$env:UV_TOOL_DIR = "$tc\uv-tools"
$env:UV_TOOL_BIN_DIR = "$tc\uv-tools\bin"
$env:PIP_CACHE_DIR = "$tc\cache\pip"
$env:HF_HOME = "$tc\cache\huggingface"
$env:TORCH_HOME = "$tc\cache\torch"
$env:YOLO_CONFIG_DIR = "$tc\cache\ultralytics"
$env:PRE_COMMIT_HOME = "$tc\cache\pre-commit"
$env:PYTHONUTF8 = '1'

$veilPathEntries = @(
  "$tc\uv",
  "$tc\jdk17\bin",
  "$tc\android-sdk\platform-tools",
  "$tc\android-sdk\cmdline-tools\latest\bin",
  "$tc\flutter\bin",
  "$tc\scrcpy",
  "$tc\ffmpeg\bin",
  "$tc\gradle\bin",
  "$tc\uv-tools\bin"
)
$veilKept = @($env:PATH -split ';' | Where-Object {
    $_ -and -not $_.StartsWith($tc, [System.StringComparison]::OrdinalIgnoreCase)
  })
$env:PATH = (($veilPathEntries + $veilKept) -join ';')

if ($env:VEIL_ENV_QUIET -ne '1') { Write-Host "Veil env: toolchain=$tc" }
