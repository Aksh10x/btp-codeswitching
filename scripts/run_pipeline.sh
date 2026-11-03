#!/usr/bin/env bash
# Master pipeline: extract audio -> transcribe -> analyze
#
# Usage:
#   ./scripts/run_pipeline.sh <data_root>
#   ./scripts/run_pipeline.sh "/Users/tusharsurwase/Desktop/BTP"
#
# This runs Steps 1-5 end-to-end. Each step is idempotent (skips already-done work).
# Total time estimate: ~45-90 minutes on CPU (mostly transcription).

set -euo pipefail

DATA_ROOT="${1:?Usage: $0 <data_root_dir>}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=============================================="
echo "BTP Code-Switching Analysis Pipeline"
echo "Data root: $DATA_ROOT"
echo "=============================================="
echo ""

# Step 1: Extract audio
echo ">>> STEP 1: Extracting 16kHz mono WAV audio..."
bash "$SCRIPT_DIR/01_extract_audio.sh" "$DATA_ROOT"
echo ""

# Step 2: Transcribe with faster-whisper large-v3
echo ">>> STEP 2: Transcribing all files (this will take a while on CPU)..."
python3 "$SCRIPT_DIR/02_transcribe_all.py" \
    "$DATA_ROOT/extracted_audio" \
    "$DATA_ROOT/transcripts"
echo ""

# Step 3-4: Already handled — transcribe_all does all files
echo ">>> STEP 3-4: Transcription complete."
echo ""

# Step 5: Linguistic analysis
echo ">>> STEP 5: Running linguistic analysis..."
python3 "$SCRIPT_DIR/03_linguistic_analysis.py" \
    "$DATA_ROOT/transcripts" \
    "$DATA_ROOT/analysis"
echo ""

# Copy analysis outputs to repo for commit
echo ">>> Copying results to repository..."
mkdir -p "$REPO_ROOT/transcripts" "$REPO_ROOT/analysis"

# Copy transcripts (text files only, not huge audio)
cp "$DATA_ROOT/transcripts/"*.txt "$REPO_ROOT/transcripts/" 2>/dev/null || true
cp "$DATA_ROOT/transcripts/"*.json "$REPO_ROOT/transcripts/" 2>/dev/null || true

# Copy analysis
cp "$DATA_ROOT/analysis/"*.txt "$REPO_ROOT/analysis/" 2>/dev/null || true
cp "$DATA_ROOT/analysis/"*.json "$REPO_ROOT/analysis/" 2>/dev/null || true

echo ""
echo "=============================================="
echo "PIPELINE COMPLETE"
echo "=============================================="
echo ""
echo "Outputs:"
echo "  Transcripts:  $DATA_ROOT/transcripts/"
echo "  Analysis:     $DATA_ROOT/analysis/"
echo "  Repo copies:  $REPO_ROOT/transcripts/ and $REPO_ROOT/analysis/"
echo ""
echo "IMPORTANT REMINDERS:"
echo "  1. All transcripts are UNVERIFIED drafts"
echo "  2. Whisper silently corrects agreement errors"
echo "  3. Whisper converts Bengali words to Hindi lookalikes"
echo "  4. Every segment must be checked against the audio"
echo ""
echo "Next: git add && git commit && git push from $REPO_ROOT"
