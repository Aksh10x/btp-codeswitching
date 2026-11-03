#!/usr/bin/env bash
# Extract 16kHz mono WAV from each media file for Whisper transcription.
# Usage: ./scripts/01_extract_audio.sh <data_root>
#
# Handles two layouts:
#   1. Subfolders: <data_root>/BTP videos/, BTP videos 2/, BTP videos 3/
#   2. Flat folder: all .MOV/.m4a files directly in <data_root>/

set -euo pipefail

DATA_ROOT="${1:?Usage: $0 <data_root_dir>}"
OUT_DIR="${DATA_ROOT}/extracted_audio"
mkdir -p "$OUT_DIR"

# Filename -> speaker code + output name
declare -A SPEAKER_MAP=(
  ["IMG_6647.MOV"]="S1_IMG_6647.wav"
  ["IMG_6648.MOV"]="S1_IMG_6648.wav"
  ["IMG_6651.MOV"]="S3_IMG_6651.wav"
  ["New Recording 7.m4a"]="S7_NewRecording7.wav"
  ["IMG_6652.MOV"]="S4_IMG_6652.wav"
  ["IMG_6660.MOV"]="S6_IMG_6660.wav"
  ["IMG_6645.MOV"]="S1_IMG_6645_preamble.wav"
  ["IMG_6650.MOV"]="S2_IMG_6650.wav"
  ["IMG_6654.MOV"]="S5_IMG_6654.wav"
  ["IMG_6664.MOV"]="S8_IMG_6664.wav"
)

# Subfolder layout paths (tried first)
declare -A SUBFOLDER_PATHS=(
  ["IMG_6647.MOV"]="BTP videos/IMG_6647.MOV"
  ["IMG_6648.MOV"]="BTP videos/IMG_6648.MOV"
  ["IMG_6651.MOV"]="BTP videos/IMG_6651.MOV"
  ["New Recording 7.m4a"]="BTP videos/New Recording 7.m4a"
  ["IMG_6652.MOV"]="BTP videos 2/IMG_6652.MOV"
  ["IMG_6660.MOV"]="BTP videos 2/IMG_6660.MOV"
  ["IMG_6645.MOV"]="BTP videos 3/IMG_6645.MOV"
  ["IMG_6650.MOV"]="BTP videos 3/IMG_6650.MOV"
  ["IMG_6654.MOV"]="BTP videos 3/IMG_6654.MOV"
  ["IMG_6664.MOV"]="IMG_6664.MOV"
)

found=0
skipped=0

for fname in "${!SPEAKER_MAP[@]}"; do
  dst="${SPEAKER_MAP[$fname]}"
  output="${OUT_DIR}/${dst}"

  if [ -f "$output" ]; then
    echo "[skip] $dst already exists"
    skipped=$((skipped + 1))
    continue
  fi

  # Try subfolder path first, then flat
  subfolder="${SUBFOLDER_PATHS[$fname]:-}"
  input=""
  if [ -n "$subfolder" ] && [ -f "${DATA_ROOT}/${subfolder}" ]; then
    input="${DATA_ROOT}/${subfolder}"
  elif [ -f "${DATA_ROOT}/${fname}" ]; then
    input="${DATA_ROOT}/${fname}"
  fi

  if [ -z "$input" ]; then
    echo "[WARN] Not found: $fname (looked in subfolders and flat)"
    continue
  fi

  echo "[extracting] $fname -> $dst"
  ffmpeg -y -i "$input" \
    -vn -sn -dn \
    -ar 16000 -ac 1 -acodec pcm_s16le \
    "$output" 2>/dev/null

  echo "[done] $dst ($(du -h "$output" | cut -f1))"
  found=$((found + 1))
done

echo ""
echo "Extracted: $found new, $skipped skipped"
echo "All audio in: $OUT_DIR"
ls -lh "$OUT_DIR"
