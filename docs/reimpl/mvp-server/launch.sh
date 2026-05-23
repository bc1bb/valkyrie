#!/bin/bash
# Diagnostic launch of the shipped client via Proton. Goal: find out how far it
# gets on this hardware (iGPU UHD630, headless X, no VR). -nullrhi skips the
# render device — the best shot at reaching networking on this box.
set -x
SR="/home/agent/snap/steam/common/.local/share/Steam"
GAME="$SR/steamapps/common/EVE Valkyrie - Warzone/WindowsNoEditor/VkGame/Binaries/Win64/EVE Valkyrie - Warzone.exe"
PROTON="$SR/steamapps/common/Proton - Experimental/proton"
export STEAM_COMPAT_DATA_PATH="$SR/steamapps/compatdata/688480"
export STEAM_COMPAT_CLIENT_INSTALL_PATH="$SR"
export PROTON_LOG=1
export PROTON_LOG_DIR=/home/agent/valkyrie-server/logs
export DISPLAY=:1
MODE="${1:-nullrhi}"
case "$MODE" in
  nullrhi) ARGS="-nullrhi -nosound -nosplash -unattended -log" ;;
  flat)    ARGS="-windowed -ResX=640 -ResY=480 -nosound -nosplash -nohmd -log" ;;
  *)       ARGS="$MODE" ;;
esac
echo "LAUNCH MODE=$MODE ARGS=$ARGS"
cd "$(dirname "$PROTON")"
timeout 120 python3 "$PROTON" run "$GAME" $ARGS
echo "EXIT=$? (124=timeout)"
