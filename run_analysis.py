#!/usr/bin/env python3
"""
Run the full MorphologyAwareAnalyzer pipeline on the corpus.

Produces:
  analysis/model_output/         — per-speaker detailed JSON
  analysis/evaluation_report.txt — summary report
  analysis/asr_comparison.json   — corrected vs Whisper comparison
  analysis/section_labels.json   — segment-to-section mapping
  analysis/corpus_summary.json   — cross-speaker summary
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from model.analyzer import MorphologyAwareAnalyzer
from model.evaluate import Evaluator
from model.section_labeler import label_corpus

TRANSCRIPT_DIR = "transcripts"
OUTPUT_DIR = "analysis/model_output"


def run_full_pipeline():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    analyzer = MorphologyAwareAnalyzer()
    evaluator = Evaluator()

    # 1. Per-speaker detailed analysis
    print("=" * 50)
    print("1. Running per-speaker analysis...")
    print("=" * 50)

    transcript_files = sorted(
        f for f in os.listdir(TRANSCRIPT_DIR)
        if f.endswith("_transcript.json") and not f.startswith("transcription_")
    )

    corpus_summary = {
        "total_speakers": 0,
        "total_words": 0,
        "total_segments": 0,
        "total_gender_errors": 0,
        "total_code_switches": 0,
        "total_ergative_contexts": 0,
        "ergative_with_ne": 0,
        "language_distribution": {},
        "per_speaker": {},
    }

    for fname in transcript_files:
        fpath = os.path.join(TRANSCRIPT_DIR, fname)
        result = analyzer.analyze_transcript(fpath, use_corrected=True)

        # Save detailed output
        out_path = os.path.join(OUTPUT_DIR, fname.replace("_transcript.json", "_model_analysis.json"))
        with open(out_path, "w") as f:
            f.write(analyzer.to_json(result))

        # Accumulate summary
        corpus_summary["total_speakers"] += 1
        corpus_summary["total_words"] += result.total_words
        corpus_summary["total_segments"] += result.total_segments

        sp = result.speaker_code
        ge_count = sum(len(s.gender_errors) for s in result.segments)
        cs_count = sum(len(s.code_switches) for s in result.segments)
        bn_words = sum(
            1 for s in result.segments for wa in s.word_annotations
            if wa.language == "bengali"
        )
        erg_total = sum(len(s.ergative_annotations) for s in result.segments)
        erg_ne = sum(
            1 for s in result.segments for ea in s.ergative_annotations
            if ea.has_ne
        )

        corpus_summary["total_gender_errors"] += ge_count
        corpus_summary["total_code_switches"] += cs_count
        corpus_summary["total_ergative_contexts"] += erg_total
        corpus_summary["ergative_with_ne"] += erg_ne

        corpus_summary["per_speaker"][sp] = {
            "gender": result.speaker_gender,
            "words": result.total_words,
            "segments": result.total_segments,
            "gender_errors": ge_count,
            "code_switches": cs_count,
            "bengali_words": bn_words,
            "ergative_contexts": erg_total,
            "ergative_with_ne": erg_ne,
            "language_distribution": result.summary.get("language_distribution", {}),
        }

        print(f"  {sp} ({result.speaker_gender}): {result.total_words} words, "
              f"{ge_count} gender errors, {cs_count} code-switches, "
              f"{bn_words} Bengali words")

    # Overall language distribution
    lang_totals = {}
    for sp_data in corpus_summary["per_speaker"].values():
        for lang, frac in sp_data["language_distribution"].items():
            lang_totals[lang] = lang_totals.get(lang, 0) + frac * sp_data["words"]
    total_w = corpus_summary["total_words"] or 1
    corpus_summary["language_distribution"] = {
        k: round(v / total_w, 4) for k, v in lang_totals.items()
    }

    with open("analysis/corpus_summary.json", "w") as f:
        json.dump(corpus_summary, f, indent=2, ensure_ascii=False)

    print(f"\n  Total: {corpus_summary['total_words']} words, "
          f"{corpus_summary['total_gender_errors']} gender errors, "
          f"{corpus_summary['total_code_switches']} code-switches")

    # 2. Evaluation report
    print("\n" + "=" * 50)
    print("2. Generating evaluation report...")
    print("=" * 50)
    report = evaluator.generate_report(TRANSCRIPT_DIR, "analysis/evaluation_report.txt")
    print("  Saved to analysis/evaluation_report.txt")

    # 3. ASR comparison
    print("\n" + "=" * 50)
    print("3. ASR frontend comparison...")
    print("=" * 50)
    comparison = evaluator.compare_asr_frontends(TRANSCRIPT_DIR)
    with open("analysis/asr_comparison.json", "w") as f:
        json.dump(comparison, f, indent=2, ensure_ascii=False)
    print(f"  Gender errors: {comparison['corrected_text']['gender_errors_found']} (corrected) "
          f"vs {comparison['whisper_raw']['gender_errors_found']} (Whisper raw)")
    print(f"  Code-switches: {comparison['corrected_text']['code_switches_found']} (corrected) "
          f"vs {comparison['whisper_raw']['code_switches_found']} (Whisper raw)")

    # 4. Section labels
    print("\n" + "=" * 50)
    print("4. Section labeling...")
    print("=" * 50)
    labels = label_corpus(TRANSCRIPT_DIR, "analysis/section_labels.json")
    print("  Saved to analysis/section_labels.json")

    print("\n" + "=" * 50)
    print("PIPELINE COMPLETE")
    print("=" * 50)
    print(f"\nOutput files:")
    print(f"  analysis/model_output/    — {len(transcript_files)} per-speaker analyses")
    print(f"  analysis/corpus_summary.json")
    print(f"  analysis/evaluation_report.txt")
    print(f"  analysis/asr_comparison.json")
    print(f"  analysis/section_labels.json")


if __name__ == "__main__":
    run_full_pipeline()
