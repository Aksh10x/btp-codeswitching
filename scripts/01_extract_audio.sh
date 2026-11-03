#!/usr/bin/env bash
# Extract 16kHz mono WAV from each media file for Whisper transcription.
# Usage: ./scripts/01_extract_audio.sh <data_root>
#
# Compatible with macOS bash 3.2 (no associative arrays).
# Handles flat folder or subfolder layouts.

set -euo pipefail

DATA_ROOT="${1:?Usage: $0 <data_root_dir>}"
OUT_DIR="${DATA_ROOT}/extracted_audio"
mkdir -p "$OUT_DIR"

extract_one() {
  local fname="$1"
  local dst="$2"
  local output="${OUT_DIR}/${dst}"

  if [ -f "$output" ]; then
    echo "[skip] $dst already exists"
    return 0
  fi

  # Search: flat directory first, then known subfolders
  local input=""
  for candidate in \
    "${DATA_ROOT}/${fname}" \
    "${DATA_ROOT}/BTP videos/${fname}" \
    "${DATA_ROOT}/BTP videos 2/${fname}" \
    "${DATA_ROOT}/BTP videos 3/${fname}"; do
    if [ -f "$candidate" ]; then
      input="$candidate"
      break
    fi
  done

  if [ -z "$input" ]; then
    echo "[WARN] Not found: $fname"
    return 0
  fi

  echo "[extracting] $fname -> $dst"
  ffmpeg -y -i "$input" \
    -vn -sn -dn \
    -ar 16000 -ac 1 -acodec pcm_s16le \
    "$output" 2>/dev/null
  echo "[done] $dst ($(du -h "$output" | cut -f1))"
}

extract_one "IMG_6647.MOV"          "S1_IMG_6647.wav"
extract_one "IMG_6648.MOV"          "S1_IMG_6648.wav"
extract_one "IMG_6651.MOV"          "S3_IMG_6651.wav"
extract_one "New Recording 7.m4a"   "S7_NewRecording7.wav"
extract_one "IMG_6652.MOV"          "S4_IMG_6652.wav"
extract_one "IMG_6660.MOV"          "S6_IMG_6660.wav"
extract_one "IMG_6645.MOV"          "S1_IMG_6645_preamble.wav"
extract_one "IMG_6650.MOV"          "S2_IMG_6650.wav"
extract_one "IMG_6654.MOV"          "S5_IMG_6654.wav"
extract_one "IMG_6664.MOV"          "S8_IMG_6664.wav"

echo ""
echo "All audio in: $OUT_DIR"
ls -lh "$OUT_DIR"
