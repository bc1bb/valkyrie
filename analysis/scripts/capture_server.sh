#!/usr/bin/env bash
# Bounded headless dedicated-server launch + network capture (E4 probe).
# -server -nullrhi: no renderer/HMD. Synthesized battle args. Writes to
# analysis/raw/ (git-ignored). Hard-timed; safe to abandon.
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
STEAM="/home/agent/snap/steam/common/.local/share/Steam"
export STEAM_COMPAT_CLIENT_INSTALL_PATH="$STEAM"
export STEAM_COMPAT_DATA_PATH="$ROOT/analysis/compatdata"
mkdir -p "$STEAM_COMPAT_DATA_PATH" "$ROOT/analysis/raw"
PROTON="$STEAM/steamapps/common/Proton - Experimental/proton"
EXE="$ROOT/WindowsNoEditor/VkGame/Binaries/Win64/EVE Valkyrie - Warzone.exe"
OUT="$ROOT/analysis/raw/server_strace.txt"
echo "[server-probe $(date -Is)]" > "$OUT"
timeout --kill-after=10 70 strace -f -e trace=network -e signal=none \
  python3 "$PROTON" run "$EXE" \
    -server -nullrhi -nosound -unattended -nosteam \
    -BATTLEID=test-0001 -BATTLESERVER_URI=ws://127.0.0.1:7777 \
    -REGION=local -PUBLICIP=127.0.0.1 -gamemode=test \
  >> "$OUT" 2>&1
echo "[exit $? @ $(date -Is)]" >> "$OUT"
