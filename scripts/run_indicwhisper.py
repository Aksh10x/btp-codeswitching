#!/usr/bin/env python3
"""
Run IndicWhisper (AI4Bharat) on the collected audio files.

Run this on your M1 Max MacBook (not in the cloud container).

Setup:
  pip install torch transformers accelerate soundfile numpy scipy

Usage:
  python scripts/run_indicwhisper.py --audio-dir BTPVIDS/extracted_audio/ --output-dir transcripts/indicwhisper/

This will:
1. Load the vasista22/whisper-hindi-small model via HuggingFace pipeline
2. Transcribe each .wav file
3. Save results as JSON files matching our transcript format
4. These can then be fed to the MorphologyAwareAnalyzer for comparison
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path


def transcribe_with_indicwhisper(audio_dir: str, output_dir: str, model_name: str):
    try:
        import torch
        import numpy as np
        import soundfile as sf
        from transformers import pipeline
    except ImportError:
        print("Missing dependencies. Install with:")
        print("  pip install torch transformers accelerate soundfile numpy scipy")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    print(f"Loading model: {model_name}")
    print("(This may take a few minutes on first run — downloading ~1.5GB)")

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"Using device: {device}")

    pipe = pipeline(
        "automatic-speech-recognition",
        model=model_name,
        device=device,
        chunk_length_s=30,
        return_timestamps=True,
    )

    audio_files = sorted(Path(audio_dir).glob("*.wav"))
    if not audio_files:
        print(f"No .wav files found in {audio_dir}")
        sys.exit(1)

    print(f"Found {len(audio_files)} audio files")

    for audio_path in audio_files:
        stem = audio_path.stem
        output_path = os.path.join(output_dir, f"{stem}_indicwhisper.json")

        if os.path.exists(output_path):
            print(f"  SKIP (exists): {stem}")
            continue

        print(f"  Transcribing: {stem}...", end=" ", flush=True)
        start = time.time()

        audio, sample_rate = sf.read(str(audio_path), dtype="float32")

        # Mono
        if audio.ndim > 1:
            audio = audio.mean(axis=1)

        # Resample to 16kHz if needed
        if sample_rate != 16000:
            import scipy.signal
            num_samples = int(len(audio) * 16000 / sample_rate)
            audio = scipy.signal.resample(audio, num_samples)
            sample_rate = 16000

        # Pipeline handles chunking, decoding, and language config internally
        output = pipe(
            {"raw": audio, "sampling_rate": 16000},
            generate_kwargs={"max_new_tokens": 440},
        )

        elapsed = time.time() - start
        duration = len(audio) / 16000

        # Build segments from pipeline output
        segments = []
        full_text_parts = []

        if "chunks" in output and output["chunks"]:
            for idx, chunk in enumerate(output["chunks"]):
                text = chunk["text"].strip()
                if not text:
                    continue
                ts = chunk.get("timestamp", (None, None))
                seg_start = ts[0] if ts[0] is not None else idx * 30.0
                seg_end = ts[1] if ts[1] is not None else min((idx + 1) * 30.0, duration)
                segments.append({
                    "id": len(segments) + 1,
                    "start": round(seg_start, 2),
                    "end": round(seg_end, 2),
                    "text": text,
                })
                full_text_parts.append(text)
        else:
            # Fallback: no chunks, just full text
            text = output.get("text", "").strip()
            if text:
                segments.append({
                    "id": 1,
                    "start": 0.0,
                    "end": round(duration, 2),
                    "text": text,
                })
                full_text_parts.append(text)

        # Extract speaker code from filename (S1_IMG_6647 -> S1)
        speaker_code = ""
        parts = stem.split("_")
        if parts and parts[0].startswith("S") and parts[0][1:].isdigit():
            speaker_code = parts[0]

        result = {
            "file": stem,
            "speaker_code": speaker_code,
            "source_audio": str(audio_path),
            "model": model_name,
            "detected_language": "hi",
            "duration_s": round(duration, 2),
            "processing_time_s": round(elapsed, 2),
            "total_segments": len(segments),
            "full_text": " ".join(full_text_parts),
            "segments": segments,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"done ({elapsed:.1f}s, {len(segments)} segments)")

    print(f"\nAll done. Results in {output_dir}/")
    print("Next: copy the output directory back to the repo and push.")


def main():
    parser = argparse.ArgumentParser(description="Run IndicWhisper on audio files")
    parser.add_argument("--audio-dir", required=True, help="Directory with .wav files")
    parser.add_argument("--output-dir", default="transcripts/indicwhisper/",
                        help="Output directory for JSON transcripts")
    parser.add_argument("--model", default="vasista22/whisper-hindi-small",
                        help="HuggingFace model name")
    args = parser.parse_args()

    transcribe_with_indicwhisper(args.audio_dir, args.output_dir, args.model)


if __name__ == "__main__":
    main()
