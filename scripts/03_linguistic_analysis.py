#!/usr/bin/env python3
"""
Linguistic analysis of transcripts for code-switching and gender agreement.

For each transcript, produces a companion analysis file listing:
1. Segments where Whisper's language confidence dropped (candidate Bengali stretches)
2. Every past-tense verb and adjective-noun pair (agreement sites)
3. Every occurrence of "ne" (ergative marker — hardest agreement context)
4. Per-speaker counts: total words, estimated Bengali words, switch points

WARNING: This analysis is based on UNVERIFIED Whisper output. Whisper silently
"corrects" non-standard agreement — the very thing this study measures. All
flagged items must be verified against the audio by a human listener.

Usage:
  python3 scripts/03_linguistic_analysis.py <transcripts_dir> [analysis_dir]
"""

import sys
import os
import json
import re
from pathlib import Path

# ─── Hindi gender agreement lexicon ───
# Common Hindi adjectives that inflect for gender
# masculine -aa -> feminine -ii pattern
GENDERED_ADJECTIVES = {
    "अच्छा": ("m", "अच्छी"),
    "अच्छी": ("f", "अच्छा"),
    "बड़ा": ("m", "बड़ी"),
    "बड़ी": ("f", "बड़ा"),
    "छोटा": ("m", "छोटी"),
    "छोटी": ("f", "छोटा"),
    "काला": ("m", "काली"),
    "काली": ("f", "काला"),
    "गोरा": ("m", "गोरी"),
    "गोरी": ("f", "गोरा"),
    "पुराना": ("m", "पुरानी"),
    "पुरानी": ("f", "पुराना"),
    "नया": ("m", "नई"),
    "नई": ("f", "नया"),
    "लंबा": ("m", "लंबी"),
    "लंबी": ("f", "लंबा"),
    "मोटा": ("m", "मोटी"),
    "मोटी": ("f", "मोटा"),
    "पतला": ("m", "पतली"),
    "पतली": ("f", "पतला"),
    "गंदा": ("m", "गंदी"),
    "गंदी": ("f", "गंदा"),
    "साफ़": ("neutral", None),
    "ठंडा": ("m", "ठंडी"),
    "ठंडी": ("f", "ठंडा"),
    "गरम": ("neutral", None),
    "खराब": ("neutral", None),
}

# Roman transliteration equivalents for adjective matching
ROMAN_ADJECTIVES = {
    "accha": ("m", "acchi"), "achha": ("m", "achhi"),
    "acchi": ("f", "accha"), "achhi": ("f", "achha"),
    "bada": ("m", "badi"), "badi": ("f", "bada"),
    "chhota": ("m", "chhoti"), "chhoti": ("f", "chhota"),
    "kala": ("m", "kali"), "kali": ("f", "kala"),
    "purana": ("m", "purani"), "purani": ("f", "purana"),
    "naya": ("m", "nayi"), "nayi": ("f", "naya"),
    "nai": ("f", "naya"),
    "lamba": ("m", "lambi"), "lambi": ("f", "lamba"),
    "mota": ("m", "moti"), "moti": ("f", "mota"),
    "patla": ("m", "patli"), "patli": ("f", "patla"),
    "ganda": ("m", "gandi"), "gandi": ("f", "ganda"),
    "thanda": ("m", "thandi"), "thandi": ("f", "thanda"),
}

# Hindi past tense verb endings (perfective aspect)
# masculine: -aa/-e, feminine: -ii/-iin
PAST_TENSE_PATTERNS_DEVANAGARI = [
    # Perfective masculine singular: verb stem + aa
    (r"(किया|गया|आया|हुआ|लिया|दिया|खाया|पिया|गिरा|बोला|चला|रहा|बना|मारा|पढ़ा|लिखा|सुना|देखा|सोचा|समझा|बैठा|उठा|रुका|मिला|कहा|रखा|भेजा|खोला|बंद किया|तोड़ा|जोड़ा)", "m_sg"),
    # Perfective feminine singular
    (r"(की|गई|आई|हुई|ली|दी|खाई|पी|गिरी|बोली|चली|रही|बनी|मारी|पढ़ी|लिखी|सुनी|देखी|सोची|समझी|बैठी|उठी|रुकी|मिली|कही|रखी|भेजी|खोली|तोड़ी|जोड़ी)", "f_sg"),
    # Perfective masculine plural
    (r"(किए|गए|आए|हुए|लिए|दिए|खाए|पिए|गिरे|बोले|चले|रहे|बने|मारे|पढ़े|लिखे|सुने|देखे|सोचे|समझे|बैठे|उठे|रुके|मिले|कहे|रखे|भेजे|खोले|तोड़े|जोड़े)", "m_pl"),
]

# Roman equivalents for common past tense verbs
PAST_TENSE_ROMAN = {
    "kiya": "m_sg", "gaya": "m_sg", "aaya": "m_sg", "hua": "m_sg",
    "liya": "m_sg", "diya": "m_sg", "khaya": "m_sg", "piya": "m_sg",
    "gira": "m_sg", "bola": "m_sg", "chala": "m_sg", "raha": "m_sg",
    "dekha": "m_sg", "suna": "m_sg", "padha": "m_sg", "likha": "m_sg",
    "mila": "m_sg", "kaha": "m_sg", "rakha": "m_sg", "bheja": "m_sg",
    "ki": "f_sg", "gayi": "f_sg", "aayi": "f_sg", "hui": "f_sg",
    "li": "f_sg", "di": "f_sg", "khai": "f_sg", "pi": "f_sg",
    "giri": "f_sg", "boli": "f_sg", "chali": "f_sg", "rahi": "f_sg",
    "dekhi": "f_sg", "suni": "f_sg", "padhi": "f_sg", "likhi": "f_sg",
    "mili": "f_sg", "kahi": "f_sg", "rakhi": "f_sg", "bheji": "f_sg",
    "kiye": "m_pl", "gaye": "m_pl", "aaye": "m_pl", "hue": "m_pl",
    "liye": "m_pl", "diye": "m_pl", "dekhe": "m_pl", "sune": "m_pl",
}

# Words that match verb/adjective patterns but are NOT verbs or adjectives
# Language names, nouns, etc. that happen to end in -ी/-ा/-े
NOT_VERBS = {
    "हिंदी", "बेंगॉली", "बेगोली", "बेंगली", "बेंगुली", "बांग्ला",
    "इंग्लिश", "इंग्रीश", "इंग्रीय",
    "नेगलीयस", "शर्षकीत", "पीएस", "थािंदी",
    "कहां", "कहाँ", "यहीं", "वहीं", "वहां", "यहां",
    "इसलिए", "इसीलिए",
    "बाकी", "सहब्दे", "नामिक", "उठागे",
}

# Ergative "ne" marker patterns
NE_PATTERN_DEVANAGARI = r'\bने\b'
NE_PATTERN_ROMAN = r'\bne\b'

# Common Bengali words/particles that might appear in Hindi speech
# (non-exhaustive — many words overlap between the two languages)
BENGALI_MARKERS = {
    # Bengali-specific particles and function words
    "আমি", "তুমি", "আপনি", "সে", "তারা", "আমরা",
    "কি", "কেন", "কোথায়", "কখন", "কীভাবে",
    "হ্যাঁ", "না", "আর", "কিন্তু", "তবে",
    "ভালো", "খারাপ", "বড়", "ছোট",
    "করি", "করো", "করে", "করেন", "করছি", "করছে", "করেছি", "করেছে",
    "হয়", "হচ্ছে", "হয়েছে", "হবে",
    "যাই", "যাও", "যায়", "যাচ্ছে", "গেছে", "গেছি",
    "আসি", "আসো", "আসে", "আসছে", "এসেছে",
    "দেখি", "দেখো", "দেখে", "দেখছে", "দেখেছে",
    "বলি", "বলো", "বলে", "বলছে", "বলেছে",
    "জানি", "জানো", "জানে", "জানতো",
    "এখানে", "ওখানে", "সেখানে",
    "এখন", "তখন", "আজ", "কাল",
    "একটু", "একটা", "সবকিছু",
    "তো", "নাকি", "কিনা",
}

# Roman transliterations of common Bengali markers
BENGALI_ROMAN_MARKERS = {
    "ami", "tumi", "apni", "tara", "amra",
    "ki", "keno", "kothay", "kokhon", "kibhabe",
    "bhalo", "kharap",
    "kori", "koro", "kore", "koren", "korchi", "korche", "korechi", "koreche",
    "hoy", "hochhe", "hoyeche", "hobe",
    "jai", "jao", "jay", "jachhe", "geche", "gechi",
    "ashi", "asho", "ashe", "asche", "eseche",
    "dekhi", "dekho", "dekhe", "dekhche", "dekheche",
    "boli", "bolo", "bole", "bolche", "boleche",
    "jani", "jano", "jane", "janto",
    "ekhane", "okhane", "sekhane",
    "ekhon", "tokhon", "aaj", "kal",
    "ektu", "ekta", "shobkichu",
    "to", "naki", "kina",
    # Bengali verb endings
    "chi", "chhi", "che", "chhe", "lam", "len", "lo",
}


HALLUCINATION_PATTERNS = [
    re.compile(r"transcribe exactly what is said", re.IGNORECASE),
    re.compile(r"the speaker may switch between", re.IGNORECASE),
    re.compile(r"a lady and her husband", re.IGNORECASE),
    re.compile(r"she asks a man if he can", re.IGNORECASE),
    re.compile(r"hesitations,?\s*false starts", re.IGNORECASE),
    re.compile(r"सब्सक्राइब\s*(करें|करना|कर)", re.IGNORECASE),
]


def _is_hallucinated_segment(seg):
    text = seg.get("text", "").strip()
    for pat in HALLUCINATION_PATTERNS:
        if pat.search(text):
            return True
    ascii_chars = sum(1 for c in text if c.isascii() and c.isalpha())
    total_alpha = sum(1 for c in text if c.isalpha())
    if total_alpha > 0 and ascii_chars / total_alpha > 0.8 and total_alpha > 10:
        return True
    return False


def analyze_transcript(transcript_json_path, analysis_dir):
    with open(transcript_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    fname = data["file"]
    speaker = data["speaker_code"]
    segments = data["segments"]

    analysis = {
        "file": fname,
        "speaker_code": speaker,
        "source_transcript": str(transcript_json_path),
        "WARNING": (
            "Based on UNVERIFIED Whisper output. Whisper silently corrects "
            "agreement errors and converts Bengali to Hindi. Every flagged item "
            "MUST be verified against the audio."
        ),
        "low_confidence_segments": [],
        "candidate_bengali_stretches": [],
        "past_tense_verbs": [],
        "adjective_noun_pairs": [],
        "ne_occurrences": [],
        "summary": {},
    }

    total_words = 0
    low_conf_words = 0
    candidate_bengali_words = 0
    ne_count = 0
    past_tense_count = 0
    adj_count = 0
    switch_points = 0

    for seg in segments:
        if _is_hallucinated_segment(seg):
            continue

        text = seg["text"]
        start = seg["start"]
        end = seg["end"]
        words = seg.get("words", [])
        total_words += len(words)

        # 1. Low confidence segments (possible non-Hindi / unclear)
        avg_logprob = seg.get("avg_logprob")
        no_speech = seg.get("no_speech_prob", 0)

        if avg_logprob is not None and avg_logprob < -0.7:
            analysis["low_confidence_segments"].append({
                "start": start,
                "end": end,
                "text": text,
                "avg_logprob": avg_logprob,
                "no_speech_prob": no_speech,
                "note": "Low confidence — possible Bengali, unclear speech, or Whisper hallucination",
            })
            low_conf_words += len(words)

        # 2. Check for Bengali markers
        for w_data in words:
            word = w_data["word"].strip()
            word_lower = word.lower()
            prob = w_data.get("probability", 1.0)

            is_bengali_candidate = False

            if word in BENGALI_MARKERS:
                is_bengali_candidate = True
            elif word_lower in BENGALI_ROMAN_MARKERS:
                is_bengali_candidate = True
            elif prob < 0.4:
                # Low-prob words are candidates, but skip pure English words
                # (those are likely Whisper hallucinations, not Bengali)
                if not (word.isascii() and word.isalpha()):
                    is_bengali_candidate = True

            if is_bengali_candidate:
                candidate_bengali_words += 1
                analysis["candidate_bengali_stretches"].append({
                    "word": word,
                    "start": w_data["start"],
                    "end": w_data["end"],
                    "probability": prob,
                    "segment_text": text,
                    "note": "UNVERIFIED — may be Hindi homophone or Whisper substitution",
                })

        # 3. Past tense verbs
        for w_data in words:
            word = w_data["word"].strip()
            word_lower = word.lower()

            # Skip words that look like verbs but aren't
            word_clean = word.rstrip(".,!?;:")
            if word_clean in NOT_VERBS:
                continue

            # Check Devanagari patterns
            for pattern, gender in PAST_TENSE_PATTERNS_DEVANAGARI:
                if re.search(pattern, word):
                    past_tense_count += 1
                    analysis["past_tense_verbs"].append({
                        "verb": word,
                        "gender_form": gender,
                        "start": w_data["start"],
                        "end": w_data["end"],
                        "segment_text": text,
                        "note": "Agreement site — verify gender matches subject/object",
                    })
                    break

            # Check Roman
            if word_lower in PAST_TENSE_ROMAN:
                past_tense_count += 1
                analysis["past_tense_verbs"].append({
                    "verb": word,
                    "gender_form": PAST_TENSE_ROMAN[word_lower],
                    "start": w_data["start"],
                    "end": w_data["end"],
                    "segment_text": text,
                    "note": "Agreement site — verify gender matches subject/object",
                })

        # 4. Adjective-noun pairs
        for w_data in words:
            word = w_data["word"].strip()
            word_lower = word.lower()

            if word in GENDERED_ADJECTIVES:
                gender, alt = GENDERED_ADJECTIVES[word]
                adj_count += 1
                analysis["adjective_noun_pairs"].append({
                    "adjective": word,
                    "gender_form": gender,
                    "alternate_form": alt,
                    "start": w_data["start"],
                    "end": w_data["end"],
                    "segment_text": text,
                    "note": "Check if adjective agrees with following noun's grammatical gender",
                })

            if word_lower in ROMAN_ADJECTIVES:
                gender, alt = ROMAN_ADJECTIVES[word_lower]
                adj_count += 1
                analysis["adjective_noun_pairs"].append({
                    "adjective": word,
                    "gender_form": gender,
                    "alternate_form": alt,
                    "start": w_data["start"],
                    "end": w_data["end"],
                    "segment_text": text,
                    "note": "Check if adjective agrees with following noun's grammatical gender",
                })

        # 5. Ergative "ne" occurrences
        if re.search(NE_PATTERN_DEVANAGARI, text) or re.search(NE_PATTERN_ROMAN, text, re.IGNORECASE):
            for w_data in words:
                word = w_data["word"].strip()
                if word == "ने" or word.lower() == "ne":
                    ne_count += 1
                    analysis["ne_occurrences"].append({
                        "start": w_data["start"],
                        "end": w_data["end"],
                        "segment_text": text,
                        "note": (
                            "Ergative construction — verb should agree with OBJECT, "
                            "not subject. Bengali has no equivalent; this is where "
                            "L1 transfer is most likely to appear."
                        ),
                    })

    # Estimate switch points (transitions between low/high confidence regions)
    prev_low = False
    for seg in segments:
        curr_low = (seg.get("avg_logprob") or 0) < -0.7
        if curr_low != prev_low:
            switch_points += 1
        prev_low = curr_low

    analysis["summary"] = {
        "total_words": total_words,
        "total_segments": len(segments),
        "duration_s": data.get("duration_s", 0),
        "low_confidence_segments": len(analysis["low_confidence_segments"]),
        "low_confidence_words": low_conf_words,
        "candidate_bengali_words": candidate_bengali_words,
        "candidate_switch_points": switch_points,
        "past_tense_verbs_found": past_tense_count,
        "adjective_noun_pairs_found": adj_count,
        "ne_occurrences": ne_count,
        "note": (
            "All counts are from UNVERIFIED Whisper output. Actual counts will "
            "differ after human verification — likely more Bengali words (Whisper "
            "converts them to Hindi) and more agreement errors (Whisper corrects them)."
        ),
    }

    # Save analysis JSON
    out_path = os.path.join(analysis_dir, f"{fname}_analysis.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)

    # Save human-readable analysis TXT
    txt_path = os.path.join(analysis_dir, f"{fname}_analysis.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"LINGUISTIC ANALYSIS — {fname} (Speaker {speaker})\n")
        f.write("=" * 70 + "\n")
        f.write("WARNING: Based on unverified Whisper output. See JSON for details.\n")
        f.write("=" * 70 + "\n\n")

        f.write("--- SUMMARY ---\n")
        for k, v in analysis["summary"].items():
            if k != "note":
                f.write(f"  {k}: {v}\n")
        f.write(f"\n  NOTE: {analysis['summary']['note']}\n\n")

        f.write("--- LOW CONFIDENCE SEGMENTS (candidate Bengali/unclear) ---\n")
        for item in analysis["low_confidence_segments"]:
            f.write(f"  [{item['start']:.1f}s - {item['end']:.1f}s] "
                    f"logprob={item['avg_logprob']:.2f}: {item['text']}\n")

        f.write(f"\n--- CANDIDATE BENGALI WORDS ({candidate_bengali_words} found) ---\n")
        for item in analysis["candidate_bengali_stretches"][:50]:
            f.write(f"  [{item['start']:.1f}s] \"{item['word']}\" "
                    f"(prob={item['probability']:.2f}) in: {item['segment_text'][:60]}...\n")
        if candidate_bengali_words > 50:
            f.write(f"  ... and {candidate_bengali_words - 50} more (see JSON)\n")

        f.write(f"\n--- PAST TENSE VERBS ({past_tense_count} found) ---\n")
        for item in analysis["past_tense_verbs"][:30]:
            f.write(f"  [{item['start']:.1f}s] \"{item['verb']}\" ({item['gender_form']}) "
                    f"in: {item['segment_text'][:60]}...\n")

        f.write(f"\n--- ADJECTIVE-NOUN PAIRS ({adj_count} found) ---\n")
        for item in analysis["adjective_noun_pairs"][:30]:
            f.write(f"  [{item['start']:.1f}s] \"{item['adjective']}\" ({item['gender_form']}) "
                    f"in: {item['segment_text'][:60]}...\n")

        f.write(f"\n--- ERGATIVE 'ne' OCCURRENCES ({ne_count} found) ---\n")
        for item in analysis["ne_occurrences"]:
            f.write(f"  [{item['start']:.1f}s] in: {item['segment_text'][:80]}...\n")

    print(f"  Analysis saved: {out_path}")
    print(f"  Analysis saved: {txt_path}")

    return analysis


def generate_cross_speaker_summary(all_analyses, analysis_dir):
    summary = {
        "title": "Cross-Speaker Summary: Code-Switching and Gender Agreement",
        "WARNING": "All data from unverified Whisper output. Counts are lower bounds.",
        "speakers": [],
        "totals": {
            "total_words": 0,
            "total_duration_s": 0,
            "candidate_bengali_words": 0,
            "candidate_switch_points": 0,
            "past_tense_verbs": 0,
            "adjective_noun_pairs": 0,
            "ne_occurrences": 0,
        },
    }

    for a in all_analyses:
        s = a["summary"]
        speaker_row = {
            "speaker": a["speaker_code"],
            "file": a["file"],
            "duration_s": s["duration_s"],
            "total_words": s["total_words"],
            "candidate_bengali_words": s["candidate_bengali_words"],
            "bengali_word_pct": round(
                100 * s["candidate_bengali_words"] / max(s["total_words"], 1), 1
            ),
            "candidate_switch_points": s["candidate_switch_points"],
            "past_tense_verbs": s["past_tense_verbs_found"],
            "adjective_noun_pairs": s["adjective_noun_pairs_found"],
            "ne_occurrences": s["ne_occurrences"],
            "agreement_sites_total": (
                s["past_tense_verbs_found"]
                + s["adjective_noun_pairs_found"]
                + s["ne_occurrences"]
            ),
        }
        summary["speakers"].append(speaker_row)

        for key in summary["totals"]:
            if key in s:
                summary["totals"][key] += s[key]
            elif key == "past_tense_verbs":
                summary["totals"][key] += s.get("past_tense_verbs_found", 0)
            elif key == "adjective_noun_pairs":
                summary["totals"][key] += s.get("adjective_noun_pairs_found", 0)

    summary["totals"]["agreement_sites_total"] = (
        summary["totals"]["past_tense_verbs"]
        + summary["totals"]["adjective_noun_pairs"]
        + summary["totals"]["ne_occurrences"]
    )

    out_path = os.path.join(analysis_dir, "cross_speaker_summary.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # Human-readable version
    txt_path = os.path.join(analysis_dir, "cross_speaker_summary.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("CROSS-SPEAKER SUMMARY\n")
        f.write("Code-Switching and Gender Agreement in Hindi-Bengali Bilingual Speech\n")
        f.write("IIT Kharagpur Campus Staff Interviews\n")
        f.write("=" * 80 + "\n")
        f.write("WARNING: All counts from unverified Whisper output (lower bounds).\n")
        f.write("=" * 80 + "\n\n")

        header = (
            f"{'Speaker':<8} {'Duration':>8} {'Words':>6} {'Bengali':>8} "
            f"{'%Bengali':>8} {'Switches':>9} {'PastV':>6} {'Adj':>5} "
            f"{'ne':>4} {'AgrmtSites':>11}"
        )
        f.write(header + "\n")
        f.write("-" * len(header) + "\n")

        for sp in summary["speakers"]:
            f.write(
                f"{sp['speaker']:<8} {sp['duration_s']:>7.0f}s {sp['total_words']:>6} "
                f"{sp['candidate_bengali_words']:>8} {sp['bengali_word_pct']:>7.1f}% "
                f"{sp['candidate_switch_points']:>9} {sp['past_tense_verbs']:>6} "
                f"{sp['adjective_noun_pairs']:>5} {sp['ne_occurrences']:>4} "
                f"{sp['agreement_sites_total']:>11}\n"
            )

        t = summary["totals"]
        f.write("-" * len(header) + "\n")
        f.write(
            f"{'TOTAL':<8} {t['total_duration_s']:>7.0f}s {t['total_words']:>6} "
            f"{t['candidate_bengali_words']:>8} "
            f"{'':>8} "
            f"{t['candidate_switch_points']:>9} {t['past_tense_verbs']:>6} "
            f"{t['adjective_noun_pairs']:>5} {t['ne_occurrences']:>4} "
            f"{t['agreement_sites_total']:>11}\n"
        )

        f.write(f"\n\nDATA SUFFICIENCY ASSESSMENT\n")
        f.write("-" * 40 + "\n")
        total_agreement = t["agreement_sites_total"]
        total_bengali = t["candidate_bengali_words"]
        total_switches = t["candidate_switch_points"]
        n_speakers = len(summary["speakers"])

        f.write(f"  Speakers: {n_speakers}\n")
        f.write(f"  Total speech: {t['total_duration_s']/60:.1f} minutes\n")
        f.write(f"  Total words: {t['total_words']}\n")
        f.write(f"  Agreement sites: {total_agreement}\n")
        f.write(f"  Bengali candidate words: {total_bengali}\n")
        f.write(f"  Switch points: {total_switches}\n\n")

        if total_agreement < 20:
            f.write("  VERDICT: INSUFFICIENT agreement sites for quantitative analysis.\n")
            f.write("  Recommend collecting more data or shifting to qualitative case study.\n")
        elif total_agreement < 50:
            f.write("  VERDICT: MARGINAL — enough for descriptive analysis and case studies,\n")
            f.write("  not enough for statistical tests across speakers.\n")
        else:
            f.write("  VERDICT: SUFFICIENT for descriptive analysis. Statistical comparison\n")
            f.write("  across speakers possible if sites are distributed across speakers.\n")

        if total_switches < 10:
            f.write("\n  CODE-SWITCHING: Very few switch points detected. May reflect\n")
            f.write("  Whisper's tendency to normalize Bengali->Hindi, or genuinely\n")
            f.write("  limited switching in the data. Human verification critical.\n")

    print(f"\nCross-speaker summary saved to: {out_path}")
    print(f"Cross-speaker summary saved to: {txt_path}")

    return summary


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 03_linguistic_analysis.py <transcripts_dir> [analysis_dir]")
        sys.exit(1)

    transcripts_dir = sys.argv[1]
    analysis_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        os.path.dirname(transcripts_dir), "analysis"
    )
    os.makedirs(analysis_dir, exist_ok=True)

    transcript_files = sorted(Path(transcripts_dir).glob("*_transcript.json"))
    if not transcript_files:
        print(f"No transcript JSON files found in {transcripts_dir}")
        sys.exit(1)

    print(f"Found {len(transcript_files)} transcript files")
    print(f"Output directory: {analysis_dir}")

    all_analyses = []
    for tf in transcript_files:
        print(f"\nAnalyzing: {tf.name}")
        analysis = analyze_transcript(str(tf), analysis_dir)
        all_analyses.append(analysis)

    generate_cross_speaker_summary(all_analyses, analysis_dir)

    print("\n\nAll analyses complete!")


if __name__ == "__main__":
    main()
