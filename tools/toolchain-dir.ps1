# Resolves where the Veil toolchain lives. Dot-source this file, then call Resolve-VeilToolchainDir.
# The path must not contain whitespace (Flutter and some Android tools break on it).
function Resolve-VeilToolchainDir {
  param([Parameter(Mandatory)][string]$RepoRoot, [string]$Override = "")
  # Order: $Override; $env:VEIL_TOOLCHAIN; "<parent of RepoRoot>\toolchain" if it has no whitespace;
  # otherwise "<drive root of RepoRoot>veil-toolchain" (e.g. D:\veil-toolchain).
  $repoFull = [System.IO.Path]::GetFullPath($RepoRoot).TrimEnd('\')
  if ($Override) {
    $p = $Override
  } elseif ($env:VEIL_TOOLCHAIN) {
    $p = $env:VEIL_TOOLCHAIN
  } else {
    $parent = Split-Path -Parent $repoFull
    $candidate = Join-Path $parent 'toolchain'
    if ($candidate -notmatch '\s') {
      $p = $candidate
    } else {
      $p = Join-Path ([System.IO.Path]::GetPathRoot($repoFull)) 'veil-toolchain'
    }
  }
  $p = [System.IO.Path]::GetFullPath($p).TrimEnd('\')
  if ($p -match '\s') {
    throw "Toolchain path must not contain spaces: $p. Set VEIL_TOOLCHAIN to a path without spaces."
  }
  return $p
}
