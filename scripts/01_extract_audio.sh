#!/usr/bin/env bash
# Extract 16kHz mono WAV from each media file for Whisper transcription.
# Usage: ./scripts/01_extract_audio.sh <data_root>
# Example: ./scripts/01_extract_audio.sh "/Users/tusharsurwase/Desktop/BTP"
#
# Only processes the 8 substantive files (skips the 4 false-start snippets).

set -euo pipefail

DATA_ROOT="${1:?Usage: $0 <data_root_dir>}"
OUT_DIR="${DATA_ROOT}/extracted_audio"
mkdir -p "$OUT_DIR"

# Map of source files -> output WAV names (speaker codes from inventory)
declare -A FILES=(
  ["BTP videos/IMG_6647.MOV"]="S1_IMG_6647.wav"
  ["BTP videos/IMG_6648.MOV"]="S1_IMG_6648.wav"
  ["BTP videos/IMG_6651.MOV"]="S3_IMG_6651.wav"
  ["BTP videos/New Recording 7.m4a"]="S7_NewRecording7.wav"
  ["BTP videos 2/IMG_6652.MOV"]="S4_IMG_6652.wav"
  ["BTP videos 2/IMG_6660.MOV"]="S6_IMG_6660.wav"
  ["BTP videos 3/IMG_6645.MOV"]="S1_IMG_6645_preamble.wav"
  ["BTP videos 3/IMG_6650.MOV"]="S2_IMG_6650.wav"
  ["BTP videos 3/IMG_6654.MOV"]="S5_IMG_6654.wav"
)

for src in "${!FILES[@]}"; do
  dst="${FILES[$src]}"
  input="${DATA_ROOT}/${src}"
  output="${OUT_DIR}/${dst}"

  if [ -f "$output" ]; then
    echo "[skip] $dst already exists"
    continue
  fi

  if [ ! -f "$input" ]; then
    echo "[WARN] Source not found: $input"
    continue
  fi

  echo "[extracting] $src -> $dst"
  ffmpeg -y -i "$input" \
    -vn -sn -dn \
    -ar 16000 -ac 1 -acodec pcm_s16le \
    "$output" 2>/dev/null

  echo "[done] $dst ($(du -h "$output" | cut -f1))"
done

echo ""
echo "All audio extracted to: $OUT_DIR"
ls -lh "$OUT_DIR"
