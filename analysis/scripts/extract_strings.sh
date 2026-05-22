#!/usr/bin/env bash
# Reproducible string extraction for the Vk client binary.
# Writes raw dumps to analysis/raw/ (git-ignored). Distil findings into docs/.
# Usage: analysis/scripts/extract_strings.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
EXE="$ROOT/WindowsNoEditor/VkGame/Binaries/Win64/EVE Valkyrie - Warzone.exe"
OUT="$ROOT/analysis/raw"
mkdir -p "$OUT"
[ -f "$EXE" ] || { echo "client binary not found: $EXE" >&2; exit 1; }

# ASCII strings with file offsets, and a clean (offset-stripped) variant.
strings -n 6 -t x "$EXE" > "$OUT/strings_main.txt"
sed -E 's/^[0-9a-f]+ //' "$OUT/strings_main.txt" > "$OUT/strings_main_clean.txt"
# UTF-16LE strings (Windows often stores URLs/keys wide).
strings -e l -n 5 "$EXE" > "$OUT/strings_utf16.txt"
cat "$OUT/strings_main_clean.txt" "$OUT/strings_utf16.txt" > "$OUT/strings_all.txt"

echo "ascii : $(wc -l < "$OUT/strings_main.txt") lines"
echo "utf16 : $(wc -l < "$OUT/strings_utf16.txt") lines"
echo "Done. Raw dumps in $OUT (git-ignored)."
