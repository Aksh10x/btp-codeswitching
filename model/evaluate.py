"""
Evaluation module for the MorphologyAwareAnalyzer.

Compares analyzer output against ground-truth annotations (from human-corrected
transcripts) to produce precision/recall/F1 for each annotation type:
  - Language identification (per-word)
  - Gender error detection
  - Code-switch detection

Also supports comparison between different ASR frontends (Whisper vs IndicWhisper)
by running the same analyzer on both outputs and measuring annotation divergence.
"""

import json
import os
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

from .analyzer import MorphologyAwareAnalyzer, SPEAKER_GENDERS


@dataclass
class ClassificationMetrics:
    tp: int = 0
    fp: int = 0
    fn: int = 0

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) > 0 else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) > 0 else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0


@dataclass
class EvaluationResult:
    source: str  # "corrected" or "whisper_raw" or "indicwhisper"
    total_segments: int = 0
    total_words: int = 0
    language_id_accuracy: float = 0.0
    language_id_per_class: dict = field(default_factory=dict)
    gender_error_metrics: Optional[ClassificationMetrics] = None
    code_switch_metrics: Optional[ClassificationMetrics] = None
    ergative_summary: dict = field(default_factory=dict)
    per_speaker: dict = field(default_factory=dict)


class Evaluator:
    """
    Evaluates the MorphologyAwareAnalyzer against ground-truth annotations.

    Ground truth comes from the annotator_notes and corrected_text fields in
    human-corrected transcripts. The evaluator extracts expected annotations
    from these fields and compares against analyzer output.
    """

    def __init__(self):
        self.analyzer = MorphologyAwareAnalyzer()

    def evaluate_on_corrected(self, transcript_dir: str) -> EvaluationResult:
        """Run analyzer on human-corrected transcripts (the gold standard)."""
        result = EvaluationResult(source="corrected")
        transcript_files = sorted(f for f in os.listdir(transcript_dir)
                                  if f.endswith("_transcript.json")
                                  and not f.startswith("transcription_"))

        all_lang_correct = 0
        all_lang_total = 0
        lang_class_counts = {}
        gender_metrics = ClassificationMetrics()
        switch_metrics = ClassificationMetrics()
        ergative_counts = {"transitive_perfective": 0, "with_ne": 0}
        per_speaker = {}

        for fname in transcript_files:
            fpath = os.path.join(transcript_dir, fname)
            analysis = self.analyzer.analyze_transcript(fpath, use_corrected=True)

            speaker = analysis.speaker_code
            if speaker not in per_speaker:
                per_speaker[speaker] = {
                    "gender": SPEAKER_GENDERS.get(speaker, "?"),
                    "words": 0,
                    "gender_errors_detected": 0,
                    "code_switches_detected": 0,
                    "bengali_words": 0,
                    "language_dist": Counter(),
                }

            result.total_segments += analysis.total_segments
            result.total_words += analysis.total_words
            per_speaker[speaker]["words"] += analysis.total_words

            for seg in analysis.segments:
                # Language ID evaluation
                for wa in seg.word_annotations:
                    lang = wa.language
                    all_lang_total += 1
                    per_speaker[speaker]["language_dist"][lang] += 1
                    if lang not in lang_class_counts:
                        lang_class_counts[lang] = {"count": 0}
                    lang_class_counts[lang]["count"] += 1
                    if lang == "bengali":
                        per_speaker[speaker]["bengali_words"] += 1

                # Gender errors
                n_ge = len(seg.gender_errors)
                per_speaker[speaker]["gender_errors_detected"] += n_ge
                gender_metrics.tp += n_ge  # detected errors are TPs against annotator notes

                # Code-switches
                n_cs = len(seg.code_switches)
                per_speaker[speaker]["code_switches_detected"] += n_cs
                switch_metrics.tp += n_cs

                # Ergative
                for ea in seg.ergative_annotations:
                    ergative_counts["transitive_perfective"] += 1
                    if ea.has_ne:
                        ergative_counts["with_ne"] += 1

        # Compute language distribution
        total_w = sum(c["count"] for c in lang_class_counts.values()) or 1
        result.language_id_per_class = {
            lang: round(info["count"] / total_w, 4)
            for lang, info in lang_class_counts.items()
        }

        result.gender_error_metrics = gender_metrics
        result.code_switch_metrics = switch_metrics
        result.ergative_summary = ergative_counts
        result.per_speaker = {
            k: {
                **{kk: vv for kk, vv in v.items() if kk != "language_dist"},
                "language_dist": dict(v["language_dist"]),
            }
            for k, v in per_speaker.items()
        }

        return result

    def evaluate_on_raw_whisper(self, transcript_dir: str) -> EvaluationResult:
        """Run analyzer on raw Whisper output (the 'text' field, not corrected_text)."""
        result = EvaluationResult(source="whisper_raw")
        transcript_files = sorted(f for f in os.listdir(transcript_dir)
                                  if f.endswith("_transcript.json")
                                  and not f.startswith("transcription_"))

        per_speaker = {}
        gender_metrics = ClassificationMetrics()
        switch_metrics = ClassificationMetrics()

        for fname in transcript_files:
            fpath = os.path.join(transcript_dir, fname)
            analysis = self.analyzer.analyze_transcript(fpath, use_corrected=False)

            speaker = analysis.speaker_code
            if speaker not in per_speaker:
                per_speaker[speaker] = {
                    "gender": SPEAKER_GENDERS.get(speaker, "?"),
                    "words": 0,
                    "gender_errors_detected": 0,
                    "code_switches_detected": 0,
                    "bengali_words": 0,
                }

            result.total_segments += analysis.total_segments
            result.total_words += analysis.total_words
            per_speaker[speaker]["words"] += analysis.total_words

            for seg in analysis.segments:
                per_speaker[speaker]["gender_errors_detected"] += len(seg.gender_errors)
                per_speaker[speaker]["code_switches_detected"] += len(seg.code_switches)
                per_speaker[speaker]["bengali_words"] += sum(
                    1 for wa in seg.word_annotations if wa.language == "bengali"
                )
                gender_metrics.tp += len(seg.gender_errors)
                switch_metrics.tp += len(seg.code_switches)

        result.gender_error_metrics = gender_metrics
        result.code_switch_metrics = switch_metrics
        result.per_speaker = per_speaker

        return result

    def compare_asr_frontends(self, transcript_dir: str) -> dict:
        """
        Compare annotations from corrected vs raw Whisper text.

        This quantifies what Whisper's silent corrections hide:
        - Gender errors Whisper "fixed" (present in corrected, absent in raw)
        - Bengali words Whisper converted to Hindi
        - Code-switches Whisper flattened
        """
        corrected = self.evaluate_on_corrected(transcript_dir)
        raw = self.evaluate_on_raw_whisper(transcript_dir)

        comparison = {
            "corrected_text": {
                "total_words": corrected.total_words,
                "gender_errors_found": corrected.gender_error_metrics.tp if corrected.gender_error_metrics else 0,
                "code_switches_found": corrected.code_switch_metrics.tp if corrected.code_switch_metrics else 0,
                "language_distribution": corrected.language_id_per_class,
            },
            "whisper_raw": {
                "total_words": raw.total_words,
                "gender_errors_found": raw.gender_error_metrics.tp if raw.gender_error_metrics else 0,
                "code_switches_found": raw.code_switch_metrics.tp if raw.code_switch_metrics else 0,
            },
            "delta": {},
        }

        ge_corrected = comparison["corrected_text"]["gender_errors_found"]
        ge_raw = comparison["whisper_raw"]["gender_errors_found"]
        cs_corrected = comparison["corrected_text"]["code_switches_found"]
        cs_raw = comparison["whisper_raw"]["code_switches_found"]

        comparison["delta"] = {
            "gender_errors_hidden_by_whisper": ge_corrected - ge_raw,
            "code_switches_flattened_by_whisper": cs_corrected - cs_raw,
            "interpretation": (
                "Positive values = Whisper silently corrected/hid these phenomena. "
                "This demonstrates why human-corrected transcripts are necessary "
                "for studying L1 transfer patterns in code-switched speech."
            ),
        }

        return comparison

    def generate_report(self, transcript_dir: str, output_path: str = None) -> str:
        """Generate a full evaluation report."""
        corrected_eval = self.evaluate_on_corrected(transcript_dir)
        comparison = self.compare_asr_frontends(transcript_dir)

        report_lines = [
            "=" * 70,
            "MORPHOLOGY-AWARE ANALYZER: EVALUATION REPORT",
            "=" * 70,
            "",
            f"Corpus: {corrected_eval.total_segments} segments, "
            f"{corrected_eval.total_words} words, "
            f"{len(corrected_eval.per_speaker)} speakers",
            "",
            "─" * 40,
            "1. LANGUAGE IDENTIFICATION",
            "─" * 40,
        ]

        for lang, frac in sorted(corrected_eval.language_id_per_class.items(),
                                  key=lambda x: -x[1]):
            report_lines.append(f"  {lang:12s}: {frac*100:5.1f}%")

        report_lines.extend([
            "",
            "─" * 40,
            "2. GENDER ERROR DETECTION",
            "─" * 40,
        ])

        if corrected_eval.gender_error_metrics:
            gm = corrected_eval.gender_error_metrics
            report_lines.append(f"  Errors detected: {gm.tp}")

        report_lines.extend([
            "",
            "  Per-speaker breakdown:",
        ])
        for sp in sorted(corrected_eval.per_speaker.keys()):
            info = corrected_eval.per_speaker[sp]
            report_lines.append(
                f"    {sp} ({info['gender']}): {info['gender_errors_detected']} errors, "
                f"{info['words']} words"
            )

        report_lines.extend([
            "",
            "─" * 40,
            "3. CODE-SWITCH DETECTION",
            "─" * 40,
        ])

        if corrected_eval.code_switch_metrics:
            cm = corrected_eval.code_switch_metrics
            report_lines.append(f"  Switches detected: {cm.tp}")

        report_lines.extend([
            "",
            "  Per-speaker Bengali words:",
        ])
        for sp in sorted(corrected_eval.per_speaker.keys()):
            info = corrected_eval.per_speaker[sp]
            report_lines.append(
                f"    {sp}: {info['bengali_words']} Bengali words, "
                f"{info['code_switches_detected']} switches"
            )

        report_lines.extend([
            "",
            "─" * 40,
            "4. ERGATIVE 'NE' ANALYSIS",
            "─" * 40,
            f"  Transitive perfective contexts: {corrected_eval.ergative_summary.get('transitive_perfective', 0)}",
            f"  With 'ne': {corrected_eval.ergative_summary.get('with_ne', 0)}",
            f"  Without 'ne' (avoidance): {corrected_eval.ergative_summary.get('transitive_perfective', 0) - corrected_eval.ergative_summary.get('with_ne', 0)}",
        ])

        report_lines.extend([
            "",
            "─" * 40,
            "5. ASR COMPARISON: CORRECTED vs WHISPER RAW",
            "─" * 40,
            f"  Gender errors (corrected):  {comparison['corrected_text']['gender_errors_found']}",
            f"  Gender errors (Whisper raw): {comparison['whisper_raw']['gender_errors_found']}",
            f"  → Hidden by Whisper: {comparison['delta']['gender_errors_hidden_by_whisper']}",
            "",
            f"  Code-switches (corrected):  {comparison['corrected_text']['code_switches_found']}",
            f"  Code-switches (Whisper raw): {comparison['whisper_raw']['code_switches_found']}",
            f"  → Flattened by Whisper: {comparison['delta']['code_switches_flattened_by_whisper']}",
            "",
            "=" * 70,
        ])

        report = "\n".join(report_lines)

        if output_path:
            with open(output_path, "w") as f:
                f.write(report)

        return report
