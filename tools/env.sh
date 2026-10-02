#!/usr/bin/env bash
# Veil environment for Git Bash, current shell only. Usage (from the repo root): source tools/env.sh
# Same rule as env.ps1 for the toolchain location: $VEIL_TOOLCHAIN, else <parent of repo>/toolchain
# if that path has no whitespace, else <drive>:\veil-toolchain.
# It never touches the registry, user/system environment variables or profile scripts.

_veil_src="${BASH_SOURCE[0]:-$0}"
_veil_repo_u="$(cd "$(dirname "$_veil_src")/.." && pwd)"
_veil_repo_w="$(cygpath -w "$_veil_repo_u")"

if [ -n "${VEIL_TOOLCHAIN:-}" ]; then
  _veil_tc_w="$(cygpath -w "$VEIL_TOOLCHAIN")"
else
  _veil_cand_w="$(cygpath -w "$(dirname "$_veil_repo_u")")\\toolchain"
  case "$_veil_cand_w" in
    *[[:space:]]*) _veil_tc_w="${_veil_repo_w:0:2}\\veil-toolchain" ;;
    *) _veil_tc_w="$_veil_cand_w" ;;
  esac
fi

case "$_veil_tc_w" in
  *[[:space:]]*)
    echo "Toolchain path must not contain spaces: $_veil_tc_w. Set VEIL_TOOLCHAIN to a path without spaces." >&2
    return 1 2>/dev/null || exit 1
    ;;
esac

_veil_tc_u="$(cygpath -u "$_veil_tc_w")"

export VEIL_TOOLCHAIN="$_veil_tc_w"
export VEIL_REPO="$_veil_repo_w"
export JAVA_HOME="$_veil_tc_w\\jdk17"
export ANDROID_HOME="$_veil_tc_w\\android-sdk"
export ANDROID_SDK_ROOT="$_veil_tc_w\\android-sdk"
export ADB="$_veil_tc_w\\android-sdk\\platform-tools\\adb.exe"
export GRADLE_USER_HOME="$_veil_tc_w\\cache\\gradle"
export PUB_CACHE="$_veil_tc_w\\cache\\pub"
export UV_CACHE_DIR="$_veil_tc_w\\cache\\uv"
export UV_PYTHON_INSTALL_DIR="$_veil_tc_w\\python"
export UV_PYTHON_PREFERENCE="only-managed"
export UV_PYTHON_INSTALL_BIN="0"
export UV_PYTHON_INSTALL_REGISTRY="0"
export UV_TOOL_DIR="$_veil_tc_w\\uv-tools"
export UV_TOOL_BIN_DIR="$_veil_tc_w\\uv-tools\\bin"
export PIP_CACHE_DIR="$_veil_tc_w\\cache\\pip"
export HF_HOME="$_veil_tc_w\\cache\\huggingface"
export TORCH_HOME="$_veil_tc_w\\cache\\torch"
export YOLO_CONFIG_DIR="$_veil_tc_w\\cache\\ultralytics"
export PRE_COMMIT_HOME="$_veil_tc_w\\cache\\pre-commit"
export PYTHONUTF8="1"
# Stop Git Bash from rewriting arguments such as /sdcard/... when it calls Windows programs.
export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL='*'

# Prepend the toolchain entries; drop any older toolchain entries first so re-sourcing is idempotent.
_veil_new="$_veil_tc_u/uv:$_veil_tc_u/jdk17/bin:$_veil_tc_u/android-sdk/platform-tools:$_veil_tc_u/android-sdk/cmdline-tools/latest/bin:$_veil_tc_u/flutter/bin:$_veil_tc_u/scrcpy:$_veil_tc_u/ffmpeg/bin:$_veil_tc_u/gradle/bin:$_veil_tc_u/uv-tools/bin"
_veil_kept=""
_veil_old_ifs="$IFS"
IFS=':'
for _veil_p in $PATH; do
  [ -z "$_veil_p" ] && continue
  case "$_veil_p" in
    "$_veil_tc_u"|"$_veil_tc_u"/*) continue ;;
  esac
  _veil_kept="${_veil_kept:+$_veil_kept:}$_veil_p"
done
IFS="$_veil_old_ifs"
export PATH="$_veil_new:$_veil_kept"

echo "Veil env: toolchain=$_veil_tc_w"
unset _veil_src _veil_repo_u _veil_repo_w _veil_cand_w _veil_tc_w _veil_tc_u _veil_new _veil_kept _veil_old_ifs _veil_p
