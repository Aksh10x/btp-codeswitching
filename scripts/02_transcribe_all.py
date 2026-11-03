#!/usr/bin/env python3
"""
Transcribe all extracted WAV files using faster-whisper large-v3.
Produces per-speaker JSON and TXT files with word-level timestamps.

Usage:
  python3 scripts/02_transcribe_all.py <extracted_audio_dir> [output_dir]

WARNING: Whisper output is a DRAFT — it will silently "correct" agreement
errors and convert Bengali words to similar-sounding Hindi. Every segment
must be verified against the audio by a human listener.
"""

import sys
import os
import json
import re
import wave
import numpy as np
from pathlib import Path
from datetime import timedelta


def fmt_ts(seconds):
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    ms = int((seconds - total_seconds) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}"


def load_wav_as_float32(path):
    with wave.open(path, "rb") as wf:
        assert wf.getsampwidth() == 2 and wf.getnchannels() == 1
        frames = wf.readframes(wf.getnframes())
    return np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0


def transcribe_file(model, audio_path, output_dir):
    fname = Path(audio_path).stem
    speaker_code = fname.split("_")[0]  # e.g. S1, S2, ...

    print(f"\n{'='*60}")
    print(f"Transcribing: {fname} (Speaker {speaker_code})")
    print(f"{'='*60}")

    audio_array = load_wav_as_float32(audio_path)
    segments, info = model.transcribe(
        audio_array,
        language="hi",
        task="transcribe",
        beam_size=5,
        best_of=5,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters=dict(
            min_silence_duration_ms=500,
            speech_pad_ms=200,
        ),
        condition_on_previous_text=True,
        initial_prompt=(
            "This is a Hindi interview with possible Bengali code-switching. "
            "The speaker may switch between Hindi and Bengali mid-sentence. "
            "Transcribe exactly what is said including hesitations, false starts, "
            "and repetitions. Do not correct grammar or normalize dialect forms."
        ),
    )

    print(f"  Detected language: {info.language} (prob: {info.language_probability:.3f})")
    print(f"  Duration: {info.duration:.1f}s")

    all_segments = []
    all_words = []
    full_text_lines = []

    for seg in segments:
        seg_data = {
            "id": seg.id,
            "start": round(seg.start, 3),
            "end": round(seg.end, 3),
            "text": seg.text.strip(),
            "avg_logprob": round(seg.avg_logprob, 4) if seg.avg_logprob else None,
            "no_speech_prob": round(seg.no_speech_prob, 4) if seg.no_speech_prob else None,
            "words": [],
        }

        if seg.words:
            for w in seg.words:
                word_data = {
                    "word": w.word.strip(),
                    "start": round(w.start, 3),
                    "end": round(w.end, 3),
                    "probability": round(w.probability, 4),
                }
                seg_data["words"].append(word_data)
                all_words.append(word_data)

        all_segments.append(seg_data)

        confidence_flag = ""
        if seg.avg_logprob and seg.avg_logprob < -1.0:
            confidence_flag = " [LOW CONFIDENCE]"
        if seg.no_speech_prob and seg.no_speech_prob > 0.5:
            confidence_flag += " [POSSIBLE NON-SPEECH]"

        line = f"[{fmt_ts(seg.start)} -> {fmt_ts(seg.end)}] {seg.text.strip()}{confidence_flag}"
        full_text_lines.append(line)
        print(f"  {line}")

    # Save JSON with all data
    json_out = {
        "file": fname,
        "speaker_code": speaker_code,
        "source_audio": str(audio_path),
        "whisper_model": "large-v3",
        "detected_language": info.language,
        "language_probability": round(info.language_probability, 4),
        "duration_s": round(info.duration, 2),
        "WARNING": (
            "This is an UNVERIFIED machine transcript. Whisper silently corrects "
            "agreement errors (e.g. 'kitab gira' -> 'kitab giri') and converts "
            "Bengali words to similar-sounding Hindi. Every segment MUST be checked "
            "against the audio by a human listener before use in analysis."
        ),
        "total_segments": len(all_segments),
        "total_words": len(all_words),
        "segments": all_segments,
    }

    json_path = os.path.join(output_dir, f"{fname}_transcript.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_out, f, ensure_ascii=False, indent=2)

    # Save readable TXT
    txt_path = os.path.join(output_dir, f"{fname}_transcript.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"DRAFT TRANSCRIPT — UNVERIFIED — {fname}\n")
        f.write(f"Speaker: {speaker_code}\n")
        f.write(f"Model: faster-whisper large-v3\n")
        f.write(f"Language detected: {info.language} (p={info.language_probability:.3f})\n")
        f.write(f"Duration: {info.duration:.1f}s\n")
        f.write("=" * 70 + "\n")
        f.write("WARNING: This transcript WILL contain errors. Whisper predicts the\n")
        f.write("most likely sentence and silently 'corrects' non-standard agreement,\n")
        f.write("converts Bengali words to Hindi lookalikes, and fills in unclear audio.\n")
        f.write("Every line must be verified against the recording.\n")
        f.write("=" * 70 + "\n\n")
        for line in full_text_lines:
            f.write(line + "\n")

    print(f"\n  Saved: {json_path}")
    print(f"  Saved: {txt_path}")

    return json_out


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 02_transcribe_all.py <extracted_audio_dir> [output_dir]")
        sys.exit(1)

    audio_dir = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        os.path.dirname(audio_dir), "transcripts"
    )
    os.makedirs(output_dir, exist_ok=True)

    wav_files = sorted(Path(audio_dir).glob("*.wav"))
    if not wav_files:
        print(f"No WAV files found in {audio_dir}")
        sys.exit(1)

    print(f"Found {len(wav_files)} WAV files to transcribe")
    print(f"Output directory: {output_dir}")

    # Load model
    print("\nLoading faster-whisper large-v3 model...")
    from faster_whisper import WhisperModel

    model = WhisperModel(
        "large-v3",
        device="cpu",
        compute_type="int8",
        cpu_threads=os.cpu_count() or 4,
    )
    print("Model loaded.")

    results = []
    for wav in wav_files:
        # Skip the preamble file
        if "preamble" in wav.stem.lower():
            print(f"\n[skip] {wav.name} (preamble/setup clip)")
            continue

        result = transcribe_file(model, str(wav), output_dir)
        results.append(result)

    # Summary
    summary_path = os.path.join(output_dir, "transcription_summary.json")
    summary = {
        "total_files": len(results),
        "model": "faster-whisper large-v3 (int8)",
        "files": [
            {
                "file": r["file"],
                "speaker": r["speaker_code"],
                "duration_s": r["duration_s"],
                "segments": r["total_segments"],
                "words": r["total_words"],
                "language": r["detected_language"],
                "language_prob": r["language_probability"],
            }
            for r in results
        ],
    }
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n\nAll transcriptions complete!")
    print(f"Summary saved to: {summary_path}")


if __name__ == "__main__":
    main()
