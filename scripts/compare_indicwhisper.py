#!/usr/bin/env python3
"""
Compare ASR outputs: Corrected vs Whisper-large-v3 vs IndicWhisper (small & large).

Runs the MorphologyAwareAnalyzer on all four text sources and compares:
  - Word counts / coverage
  - Gender error detection
  - Code-switch detection
  - Bengali word recognition
  - Hallucination patterns
"""

import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from model.analyzer import MorphologyAwareAnalyzer, SPEAKER_GENDERS

TRANSCRIPT_DIR = "transcripts"
INDIC_SMALL_DIR = "transcripts/indicwhisper"
INDIC_LARGE_DIR = "transcripts/indicwhisper_large"
OUTPUT_DIR = "analysis"


def detect_hallucination(text: str, threshold: int = 5) -> dict:
    words = text.split()
    if len(words) < threshold * 2:
        return {"has_hallucination": False}
    for n in range(2, 6):
        ngrams = [" ".join(words[i:i+n]) for i in range(len(words) - n + 1)]
        counts = Counter(ngrams)
        most_common = counts.most_common(1)
        if most_common and most_common[0][1] >= threshold:
            return {
                "has_hallucination": True,
                "repeated_phrase": most_common[0][0],
                "repetitions": most_common[0][1],
                "ngram_size": n,
            }
    # Also check single-word repetition
    word_counts = Counter(words)
    most_common_word = word_counts.most_common(1)
    if most_common_word and most_common_word[0][1] >= threshold * 3:
        return {
            "has_hallucination": True,
            "repeated_phrase": most_common_word[0][0],
            "repetitions": most_common_word[0][1],
            "ngram_size": 1,
        }
    return {"has_hallucination": False}


def analyze_asr_file(analyzer, filepath, text_field="text"):
    with open(filepath) as f:
        data = json.load(f)

    speaker_code = data.get("speaker_code", "")
    total_words = 0
    gender_errors = 0
    code_switches = 0
    bengali_words = 0
    lang_counts = {}
    hallucinations = []

    for seg in data.get("segments", []):
        text = seg.get(text_field, "")
        if not text:
            continue

        hall = detect_hallucination(text)
        if hall["has_hallucination"]:
            hallucinations.append({"segment_id": seg.get("id"), **hall})

        seg_analysis = analyzer.analyze_segment(text, speaker_code, seg.get("id", 0))
        total_words += len(seg_analysis.word_annotations)
        gender_errors += len(seg_analysis.gender_errors)
        code_switches += len(seg_analysis.code_switches)

        for wa in seg_analysis.word_annotations:
            lang_counts[wa.language] = lang_counts.get(wa.language, 0) + 1
            if wa.language == "bengali":
                bengali_words += 1

    total_w = total_words or 1
    return {
        "speaker_code": speaker_code,
        "total_words": total_words,
        "total_segments": data.get("total_segments", 0),
        "duration_s": data.get("duration_s", 0),
        "gender_errors": gender_errors,
        "code_switches": code_switches,
        "bengali_words": bengali_words,
        "language_distribution": {k: round(v / total_w, 4) for k, v in lang_counts.items()},
        "hallucinations": hallucinations,
    }


def run_comparison():
    analyzer = MorphologyAwareAnalyzer()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    transcript_files = sorted(
        f for f in os.listdir(TRANSCRIPT_DIR)
        if f.endswith("_transcript.json") and not f.startswith("transcription_")
    )

    def load_indic_map(dirpath):
        if not os.path.isdir(dirpath):
            return {}
        return {
            f.replace("_indicwhisper.json", ""): f
            for f in os.listdir(dirpath)
            if f.endswith("_indicwhisper.json")
        }

    indic_small_files = load_indic_map(INDIC_SMALL_DIR)
    indic_large_files = load_indic_map(INDIC_LARGE_DIR)

    SOURCES = ["corrected", "whisper_raw", "indic_small", "indic_large"]
    per_speaker = {}
    totals = {s: {"total_words": 0, "gender_errors": 0, "code_switches": 0,
                   "bengali_words": 0, "hallucinations": 0} for s in SOURCES}

    for fname in transcript_files:
        fpath = os.path.join(TRANSCRIPT_DIR, fname)
        stem = fname.replace("_transcript.json", "")

        corrected = analyze_asr_file(analyzer, fpath, text_field="corrected_text")
        raw = analyze_asr_file(analyzer, fpath, text_field="text")

        sp = corrected["speaker_code"]
        entry = {
            "speaker": sp,
            "gender": SPEAKER_GENDERS.get(sp, "?"),
            "file": stem,
            "corrected": corrected,
            "whisper_raw": raw,
        }

        if stem in indic_small_files:
            entry["indic_small"] = analyze_asr_file(
                analyzer, os.path.join(INDIC_SMALL_DIR, indic_small_files[stem]))
        if stem in indic_large_files:
            entry["indic_large"] = analyze_asr_file(
                analyzer, os.path.join(INDIC_LARGE_DIR, indic_large_files[stem]))

        if sp not in per_speaker:
            per_speaker[sp] = []
        per_speaker[sp].append(entry)

        for src in SOURCES:
            data = entry.get(src)
            if not data:
                continue
            for key in ["total_words", "gender_errors", "code_switches", "bengali_words"]:
                totals[src][key] += data[key]
            totals[src]["hallucinations"] += len(data.get("hallucinations", []))

    # Save full JSON
    result = {"summary": {"totals": totals}, "per_speaker": per_speaker}
    out_path = os.path.join(OUTPUT_DIR, "indicwhisper_comparison.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    # Print report
    labels = {
        "corrected": "Corrected",
        "whisper_raw": "Whisper-v3",
        "indic_small": "Indic-small",
        "indic_large": "Indic-large",
    }

    print("=" * 80)
    print("ASR COMPARISON: Corrected vs Whisper-v3 vs IndicWhisper (small & large)")
    print("=" * 80)

    header = f"{'Metric':<30}"
    for s in SOURCES:
        header += f" {labels[s]:>12}"
    print(f"\n{header}")
    print("-" * 80)

    for metric, key in [("Total words", "total_words"), ("Gender errors", "gender_errors"),
                         ("Code-switches", "code_switches"), ("Bengali words", "bengali_words"),
                         ("Hallucination segments", "hallucinations")]:
        row = f"{metric:<30}"
        for s in SOURCES:
            val = totals[s][key]
            if metric == "Hallucination segments" and s in ("corrected", "whisper_raw"):
                row += f" {'---':>12}"
            else:
                row += f" {val:>12}"
        print(row)

    # Deltas
    print(f"\n{'--- Hidden by each ASR (vs Corrected) ---':^80}")
    c = totals["corrected"]
    for s in ["whisper_raw", "indic_small", "indic_large"]:
        t = totals[s]
        ge_hidden = c["gender_errors"] - t["gender_errors"]
        cs_hidden = c["code_switches"] - t["code_switches"]
        bn_hidden = c["bengali_words"] - t["bengali_words"]
        ge_pct = round(100 * ge_hidden / c["gender_errors"]) if c["gender_errors"] else 0
        cs_pct = round(100 * cs_hidden / c["code_switches"]) if c["code_switches"] else 0
        bn_pct = round(100 * bn_hidden / c["bengali_words"]) if c["bengali_words"] else 0
        print(f"\n  {labels[s]}:")
        print(f"    Gender errors hidden:    {ge_hidden:>4} / {c['gender_errors']} ({ge_pct}%)")
        print(f"    Code-switches flattened: {cs_hidden:>4} / {c['code_switches']} ({cs_pct}%)")
        print(f"    Bengali words lost:      {bn_hidden:>4} / {c['bengali_words']} ({bn_pct}%)")
        print(f"    Word count:              {t['total_words']:>4} vs {c['total_words']} corrected")

    # Per-speaker
    print(f"\n{'--- Per-Speaker Summary ---':^80}")
    print(f"{'Spkr':<5} {'G':<3} {'C.Wds':>6} {'W.Wds':>6} {'IS.Wd':>6} {'IL.Wd':>6} "
          f"{'C.GE':>5} {'W.GE':>5} {'IS.GE':>5} {'IL.GE':>5} "
          f"{'C.BN':>5} {'W.BN':>5} {'IS.BN':>5} {'IL.BN':>5}")
    print("-" * 80)

    for sp in sorted(per_speaker.keys()):
        entries = per_speaker[sp]
        vals = {}
        for s in SOURCES:
            vals[s] = {
                "w": sum(e[s]["total_words"] for e in entries if s in e),
                "ge": sum(e[s]["gender_errors"] for e in entries if s in e),
                "bn": sum(e[s]["bengali_words"] for e in entries if s in e),
            }
        g = SPEAKER_GENDERS.get(sp, "?")
        print(f"{sp:<5} {g:<3} "
              f"{vals['corrected']['w']:>6} {vals['whisper_raw']['w']:>6} "
              f"{vals['indic_small']['w']:>6} {vals['indic_large']['w']:>6} "
              f"{vals['corrected']['ge']:>5} {vals['whisper_raw']['ge']:>5} "
              f"{vals['indic_small']['ge']:>5} {vals['indic_large']['ge']:>5} "
              f"{vals['corrected']['bn']:>5} {vals['whisper_raw']['bn']:>5} "
              f"{vals['indic_small']['bn']:>5} {vals['indic_large']['bn']:>5}")

    # Hallucinations
    print(f"\n{'--- Hallucination Instances ---':^80}")
    hall_count = 0
    for sp, entries in sorted(per_speaker.items()):
        for e in entries:
            for src in ["indic_small", "indic_large"]:
                if src in e and e[src]["hallucinations"]:
                    for h in e[src]["hallucinations"]:
                        hall_count += 1
                        print(f"  {sp} {labels[src]} seg {h['segment_id']}: "
                              f"\"{h['repeated_phrase']}\" x{h['repetitions']}")
    if hall_count == 0:
        print("  (none)")

    print("\n" + "=" * 80)
    print(f"Saved: {out_path}")
    return result


if __name__ == "__main__":
    run_comparison()
