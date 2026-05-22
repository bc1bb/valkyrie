#!/usr/bin/env bash
# Bounded read-only launch + network syscall capture (E4 cheapest-first probe).
# Writes to analysis/raw/ (git-ignored). Hard-timed; safe to abandon.
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
STEAM="/home/agent/snap/steam/common/.local/share/Steam"
export STEAM_COMPAT_CLIENT_INSTALL_PATH="$STEAM"
export STEAM_COMPAT_DATA_PATH="$ROOT/analysis/compatdata"
mkdir -p "$STEAM_COMPAT_DATA_PATH" "$ROOT/analysis/raw"
PROTON="$STEAM/steamapps/common/Proton - Experimental/proton"
EXE="$ROOT/WindowsNoEditor/VkGame/Binaries/Win64/EVE Valkyrie - Warzone.exe"
OUT="$ROOT/analysis/raw/launch_strace.txt"
echo "[launch] $(date -Is)" > "$OUT"
timeout --kill-after=10 75 strace -f -e trace=network -e signal=none \
  python3 "$PROTON" run "$EXE" >> "$OUT" 2>&1
echo "[exit code $? @ $(date -Is)]" >> "$OUT"
