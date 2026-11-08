#!/usr/bin/env python3
"""
Run IndicWhisper (AI4Bharat) on the collected audio files.

Run this on your M1 Max MacBook (not in the cloud container).

Setup:
  pip install torch torchaudio transformers accelerate
  # IndicWhisper uses the Whisper architecture, available via HuggingFace

Usage:
  python scripts/run_indicwhisper.py --audio-dir BTPVIDS/extracted_audio/ --output-dir transcripts/indicwhisper/

This will:
1. Load the AI4Bharat IndicWhisper model (ai4bharat/indicwhisper-hindi)
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
        import torchaudio
        from transformers import WhisperProcessor, WhisperForConditionalGeneration
    except ImportError:
        print("Missing dependencies. Install with:")
        print("  pip install torch torchaudio transformers accelerate")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    print(f"Loading model: {model_name}")
    print("(This may take a few minutes on first run — downloading ~1.5GB)")

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"Using device: {device}")

    processor = WhisperProcessor.from_pretrained(model_name)
    model = WhisperForConditionalGeneration.from_pretrained(model_name)
    model = model.to(device)

    # Force Hindi language and transcription task
    forced_decoder_ids = processor.get_decoder_prompt_ids(
        language="hi", task="transcribe"
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

        waveform, sample_rate = torchaudio.load(str(audio_path))

        # Resample to 16kHz if needed
        if sample_rate != 16000:
            resampler = torchaudio.transforms.Resample(sample_rate, 16000)
            waveform = resampler(waveform)

        # Mono
        if waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0, keepdim=True)

        # Process in chunks of 30 seconds (Whisper's window)
        chunk_size = 16000 * 30
        audio = waveform.squeeze().numpy()
        chunks = [audio[i:i+chunk_size] for i in range(0, len(audio), chunk_size)]

        segments = []
        full_text = []

        for idx, chunk in enumerate(chunks):
            inputs = processor(
                chunk, sampling_rate=16000, return_tensors="pt"
            ).input_features.to(device)

            with torch.no_grad():
                predicted_ids = model.generate(
                    inputs,
                    forced_decoder_ids=forced_decoder_ids,
                    max_new_tokens=448,
                )

            text = processor.batch_decode(
                predicted_ids, skip_special_tokens=True
            )[0].strip()

            if text:
                seg_start = idx * 30.0
                seg_end = min((idx + 1) * 30.0, len(audio) / 16000)
                segments.append({
                    "id": idx + 1,
                    "start": round(seg_start, 2),
                    "end": round(seg_end, 2),
                    "text": text,
                })
                full_text.append(text)

        elapsed = time.time() - start
        duration = len(audio) / 16000

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
            "full_text": " ".join(full_text),
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
