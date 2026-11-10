"""
Morphology-Aware Analyzer for Bengali-Hindi Code-Switched Speech.

Analyzes transcribed text (human-corrected or ASR output) for:
  1. Word-level language identification (Hindi / Bengali / English / Mixed)
  2. Gender agreement errors (noun-verb and subject-verb)
  3. Ergative 'ne' usage/avoidance
  4. Code-switch classification (tag-switch, intra-sentential, inter-sentential)

Operates on Roman transliteration. Designed for the IIT Kharagpur campus
staff corpus (Bengali L1, Hindi L2) but extensible to other L1-Hindi pairs.
"""

import json
import re
from dataclasses import dataclass, field, asdict
from typing import Optional

from .lexicons import (
    HINDI_FEMININE_NOUNS, HINDI_MASCULINE_NOUNS,
    BENGALI_WORDS, BENGALI_MARKERS,
    MASCULINE_VERB_PATTERNS, FEMININE_VERB_PATTERNS,
    PERFECTIVE_MARKERS, TRANSITIVE_VERBS_STEMS,
    ENGLISH_COMMON,
)
from .transliterate import devanagari_to_roman

# Speaker genders (from study metadata)
SPEAKER_GENDERS = {
    "S1": "M", "S2": "F", "S3": "F", "S4": "F",
    "S5": "M", "S6": "M", "S7": "M", "S8": "F",
}


@dataclass
class WordAnnotation:
    word: str
    language: str           # "hindi", "bengali", "english", "mixed", "unknown"
    bengali_info: Optional[dict] = None  # if Bengali: {hindi_equiv, meaning, domain}


@dataclass
class GenderError:
    error_type: str         # "noun_verb" or "subject_verb"
    rule_id: str            # "R1" or "R2"
    noun_or_subject: str
    verb_form: str
    expected_verb: str
    context: str            # surrounding text


@dataclass
class ErgativeAnnotation:
    verb_stem: str
    perfective_form: str
    has_ne: bool
    context: str


@dataclass
class CodeSwitch:
    switch_type: str        # "tag_switch", "intra_sentential", "inter_sentential", "three_way"
    rule_id: str            # "R4", "R5", "R6"
    bengali_span: str
    hindi_context: str
    details: str


@dataclass
class SegmentAnalysis:
    segment_id: int
    speaker: Optional[str]
    text: str
    word_annotations: list = field(default_factory=list)
    gender_errors: list = field(default_factory=list)
    ergative_annotations: list = field(default_factory=list)
    code_switches: list = field(default_factory=list)
    language_distribution: dict = field(default_factory=dict)


@dataclass
class TranscriptAnalysis:
    filename: str
    speaker_code: str
    speaker_gender: str
    total_segments: int
    total_words: int
    segments: list = field(default_factory=list)
    summary: dict = field(default_factory=dict)


class MorphologyAwareAnalyzer:
    """
    Text-based analyzer for Bengali-Hindi code-switched speech.

    Pipeline position: Audio -> ASR -> [this analyzer] -> Annotations
    Input: corrected_text field from transcript JSON (or raw Whisper text)
    Output: per-segment linguistic annotations
    """

    def __init__(self):
        self._build_lookup_tables()

    def _build_lookup_tables(self):
        self._bengali_words = set(BENGALI_WORDS.keys())
        self._bengali_markers = BENGALI_MARKERS
        self._hindi_fem = {w.lower() for w in HINDI_FEMININE_NOUNS}
        self._hindi_masc = {w.lower() for w in HINDI_MASCULINE_NOUNS}
        self._english = {w.lower() for w in ENGLISH_COMMON}
        self._masc_verbs = {v.lower() for v in MASCULINE_VERB_PATTERNS}
        self._fem_verbs = {v.lower() for v in FEMININE_VERB_PATTERNS}
        self._perfective = {v.lower() for v in PERFECTIVE_MARKERS}
        self._transitive_stems = {v.lower() for v in TRANSITIVE_VERBS_STEMS}

        # Build a set of all known Hindi words (nouns + verbs + common particles)
        self._hindi_particles = {
            # Auxiliaries / copula
            "hai", "tha", "thi", "the", "hain", "ho", "hu",
            "hota", "hoti", "hote",
            # Postpositions / case
            "ka", "ki", "ke", "ko", "se", "mein", "pe", "par", "ne",
            "tak", "liye", "saath", "wala", "wali", "wale",
            # Conjunctions / connectors
            "aur", "ya", "toh", "bhi", "nahi", "na", "mat", "bas",
            "jo", "jab", "tab", "fir", "phir", "toh", "isliye", "kyuki",
            "lekin", "magar", "agar", "jaise", "waise", "matlab",
            # Pronouns / deictics
            "yeh", "ye", "woh", "wo", "kya", "kaun", "kaha", "kab",
            "kaise", "kitna", "kitni", "kitne", "koi", "kuch",
            "mai", "main", "mein", "mera", "meri", "mere",
            "hum", "hamara", "hamari", "hamare",
            "tu", "tera", "teri", "tere", "tum", "tumhara",
            "aap", "aapka", "aapki", "aapke", "aapne", "aapko",
            "woh", "wo", "uska", "uski", "uske", "unka", "unki", "unke",
            "isko", "usko", "inko", "unko", "isme", "usme",
            "mujhe", "mujhko", "hume", "humko", "tujhe",
            "idhar", "udhar", "yaha", "waha", "yahi", "wohi",
            # Numbers
            "ek", "do", "teen", "chaar", "paanch", "che", "saat", "aath",
            "nau", "das", "gyarah", "baarah", "sau", "hazaar", "lakh",
            # Imperatives / common verbs
            "bol", "bolo", "batao", "dekho", "suno", "jao", "aao", "karo",
            "chalo", "lo", "do", "de", "le", "rakh", "rakhke",
            # Common adjectives / adverbs
            "accha", "acche", "theek", "sab", "bohot", "bahut", "bohut",
            "zyada", "thoda", "thodi", "bada", "badi", "bade",
            "chota", "choti", "chote", "naya", "nayi", "purana",
            "pura", "poora", "puri", "aisa", "aisi", "aise",
            "waisa", "pehle", "baad", "abhi",
            # Time / routine words
            "subah", "shaam", "dopahar", "raat", "din", "saal",
            "baje", "ghanta", "mahina", "hafta", "kal", "aaj",
            "kabhi", "kabhi", "hamesha", "roz",
            # Common nouns
            "ghar", "kaam", "time", "log", "baat", "cheez",
            "jagah", "tarah", "parivaar", "bachcha", "bachche",
            "khana", "paani", "doodh", "chai",
            "janam", "shaadi", "padhai",
            # Address / kinship
            "dada", "didi", "bhaiya", "sir", "madam", "uncle", "bhai",
            "behen", "pitaji", "mummy", "papa",
            # Affirmation / filler
            "haa", "nahi", "bilkul", "zarur", "shayad", "achha",
            "arrey", "dekh", "sun",
            # Verb roots commonly used bare
            "rehta", "rehti", "rehte", "padta", "padti", "lagta", "lagti",
            "aata", "aati", "jaata", "jaati", "karta", "karti",
            "raha", "rahi", "rahe",
            "gaya", "gayi", "gaye", "hua", "hui", "hue",
            "tha", "thi", "the", "thaa",
            # Miscellaneous high-frequency
            "samay", "dupahar", "paisa", "paise",
            "dheere", "jaldi", "andar", "bahar",
            "saare", "sara", "sari",
            "koi", "kuch", "kaafi",
            "mushkil", "pareshaani", "problem",
        }

        # Combine all Hindi-identifiable words
        self._all_hindi = (
            self._hindi_fem | self._hindi_masc |
            self._hindi_particles |
            {v.split()[0] for v in self._masc_verbs} |
            {v.split()[0] for v in self._fem_verbs}
        )

    # ── Language ID ──────────────────────────────────────────────

    def identify_language(self, word: str) -> WordAnnotation:
        w = word.lower().strip(".,!?;:'\"()-")
        if not w:
            return WordAnnotation(word=word, language="unknown")

        bengali_info = None
        if w in self._bengali_words:
            bengali_info = BENGALI_WORDS[w]
            return WordAnnotation(word=word, language="bengali", bengali_info=bengali_info)

        if w in self._bengali_markers:
            return WordAnnotation(word=word, language="bengali")

        # Check for Bengali verb suffixes
        for suffix in ("cchi", "cche", "che", "chi", "eche", "echi", "lam", "le", "lo"):
            if len(w) > len(suffix) + 1 and w.endswith(suffix):
                return WordAnnotation(word=word, language="bengali")

        if w in self._english:
            return WordAnnotation(word=word, language="english")

        if w in self._all_hindi:
            return WordAnnotation(word=word, language="hindi")

        # Check verb pattern membership
        if w in self._masc_verbs or w in self._fem_verbs or w in self._perfective:
            return WordAnnotation(word=word, language="hindi")

        # Default: if it uses common Hindi/Urdu endings, call it Hindi
        hindi_endings = ("ta", "ti", "te", "na", "ni", "ne", "ke", "ki", "ka")
        if any(w.endswith(e) for e in hindi_endings) and len(w) > 3:
            return WordAnnotation(word=word, language="hindi")

        return WordAnnotation(word=word, language="unknown")

    # ── Gender Error Detection ───────────────────────────────────

    def detect_gender_errors(self, text: str, speaker_code: str,
                             addressed: bool = False) -> list:
        errors = []
        words = text.lower().split()
        speaker_gender = SPEAKER_GENDERS.get(speaker_code, "")

        # R1: Feminine noun + masculine verb
        errors.extend(self._check_noun_verb_agreement(words, text))

        # R2: Female speaker + masculine self-reference verb
        if speaker_gender == "F":
            errors.extend(self._check_subject_verb_agreement(words, text, speaker_code, addressed))

        # Deduplicate R1/R2 overlap: if R2 verb overlaps with any R1 verb
        # (exact match or substring containment), keep only R1.
        # Also suppress R2 when 3+ R1 errors exist (listing/description task).
        r1_verbs = {e.verb_form for e in errors if e.rule_id == "R1"}
        r1_count = sum(1 for e in errors if e.rule_id == "R1")

        def r2_overlaps_r1(r2_verb):
            for r1v in r1_verbs:
                if r2_verb in r1v or r1v in r2_verb:
                    return True
            return False

        errors = [e for e in errors
                  if not (e.rule_id == "R2"
                          and (r2_overlaps_r1(e.verb_form) or r1_count >= 3))]

        return errors

    def _check_noun_verb_agreement(self, words: list, full_text: str) -> list:
        """
        R1: feminine noun + masculine verb.

        Only flag compound verb forms (tut gaya, ho gaya, khol raha, etc.)
        that are clearly associated with the noun. Single-word verb forms
        like "karta" are too ambiguous — they could agree with an implied
        subject rather than the nearest noun.
        """
        errors = []
        found_nouns = set()  # track which nouns already have an error

        # Sort compound patterns longest-first so we match the most specific
        compound_masc = sorted(
            [mv for mv in self._masc_verbs if len(mv.split()) >= 2],
            key=lambda x: (-len(x), x.startswith("raha")),
        )

        for i, w in enumerate(words):
            if w not in self._hindi_fem or w in found_nouns:
                continue
            window = words[i+1:i+6]
            window_text = " ".join(window)

            for mv in compound_masc:
                if mv in window_text:
                    expected = self._masculine_to_feminine(mv)
                    if expected:
                        found_nouns.add(w)
                        errors.append(GenderError(
                            error_type="noun_verb",
                            rule_id="R1",
                            noun_or_subject=w,
                            verb_form=mv,
                            expected_verb=expected,
                            context=full_text,
                        ))
                        break  # one error per noun occurrence
        return errors

    def _check_subject_verb_agreement(self, words: list, full_text: str,
                                       speaker_code: str,
                                       addressed: bool = False) -> list:
        """
        R2: female speaker using masculine verb for self-reference.

        Only flag when the verb is plausibly self-referential:
        - Preceded by first-person subject pronoun (mai, hum, khud)
        - Or a habitual/progressive about the speaker's own routine
          (no explicit third-person subject nearby)

        Skip when:
        - Describing a photo/picture (collector asks "kya kar raha hai")
        - Third-person subject present near the verb
        - Mixed-gender group subject (masculine default is correct)
        - Impersonal/generic construction (janam hua, X hota hai)
        """
        errors = []
        text_lower = " ".join(words)

        first_person_subject = {"mai", "main", "hum", "khud"}
        first_person_possessive = {"mera", "meri", "mere",
                                   "hamara", "hamari", "hamare",
                                   "apna", "apni", "apne"}
        first_person = first_person_subject | first_person_possessive

        third_person = {"woh", "wo", "yeh", "ye", "ladka", "ladki", "bachcha",
                        "bachche", "aadmi", "aurat", "banda", "student",
                        "students", "dada", "bhaiya", "sir", "madam",
                        "husband", "beta", "beti", "bhai", "behen",
                        "pitaji", "papa", "mummy", "uncle", "aunty",
                        "nana", "mama", "teacher", "doctor",
                        "lerka", "lerki"}

        photo_cues = {"photo", "picture", "iss photo", "yeh kya kar"}
        if any(cue in text_lower for cue in photo_cues):
            return errors

        # Mixed-gender group: masculine default is standard Hindi
        mixed_group = {"lerka lerki", "lerke lerkiyan", "ladka ladki",
                       "ladke ladkiyan"}
        if any(mg in text_lower for mg in mixed_group):
            return errors

        has_first_person = any(w in first_person for w in words)
        has_third_person = any(w in third_person for w in words)

        if has_third_person and not (has_first_person or addressed):
            return errors

        inanimate_subjects = (
            (self._hindi_fem | self._hindi_masc) - third_person
            - {"maa", "ma", "nani", "dadi", "mausi", "bahu", "didi", "bhabhi", "ladies", "baap"}
        ) | {"glass", "chair", "fan", "bottle", "plate", "kitaab", "paani"}

        # Track flagged word positions to avoid duplicate detections
        flagged_positions = set()

        # Sort longest-first so compound verbs take priority
        for mv in sorted(self._masc_verbs, key=lambda x: -len(x)):
            if mv not in text_lower:
                continue
            expected = self._masculine_to_feminine(mv)
            if not expected or expected in text_lower:
                continue

            mv_words = mv.split()
            try:
                if len(mv_words) == 1:
                    idx = words.index(mv_words[0])
                else:
                    idx = text_lower.index(mv)
                    idx = len(text_lower[:idx].split())
            except (ValueError, IndexError):
                continue

            # Skip if overlapping with an already-flagged verb
            verb_positions = set(range(idx, idx + len(mv_words)))
            if verb_positions & flagged_positions:
                continue

            window_start = max(0, idx - 6)
            preceding = words[window_start:idx]

            # Skip if a third-person subject is near this verb
            if any(w in third_person for w in preceding):
                continue

            # Skip impersonal "janam hua/ho gaya" constructions
            if any(w == "janam" for w in preceding):
                continue

            # For generic verbs (hota/hota hai), require strict subject proximity
            generic_verbs = {"hota", "hota hai", "hota tha"}
            if mv in generic_verbs:
                tight = words[max(0, idx - 2):idx]
                if not any(w in first_person_subject for w in tight):
                    continue

            # Inanimate noun directly before a perfective verb is its subject
            # ("glass gir gaya"), not the speaker.
            if mv.endswith(("gaya", "hua")):
                prev = words[idx - 1].strip(".,!?;:") if idx > 0 else ""
                if prev in inanimate_subjects:
                    continue

            following = words[idx + len(mv_words): idx + len(mv_words) + 6]
            if mv in generic_verbs or mv in {"aata", "ata", "hua", "jata", "chala"}:
                is_self_ref = any(w in first_person_subject for w in words[max(0, idx - 2):idx])
            else:
                is_self_ref = any(
                    w in first_person_subject for w in preceding + following
                )
            # Subjectless habitual counts as self-reference only when the
            # collector's question in this segment was addressed to the speaker.
            habitual_stems = {"karta", "bolta", "padhta", "banata", "sunta",
                              "dekhta", "seekhta"}
            is_subjectless_habitual = (
                mv.split()[0] in habitual_stems and addressed
                and not any(w in third_person for w in preceding)
            )

            if is_self_ref or is_subjectless_habitual:
                flagged_positions.update(verb_positions)
                errors.append(GenderError(
                    error_type="subject_verb",
                    rule_id="R2",
                    noun_or_subject=f"{speaker_code} (female speaker)",
                    verb_form=mv,
                    expected_verb=expected,
                    context=full_text,
                ))
        return errors

    def _masculine_to_feminine(self, masc_verb: str) -> Optional[str]:
        """Map a masculine verb form to its feminine equivalent."""
        mappings = {
            # Perfective -a -> -i
            "gaya": "gayi", "kiya": "ki", "liya": "li", "diya": "di",
            "hua": "hui", "aaya": "aayi", "khaya": "khayi",
            "bola": "boli", "chala": "chali", "gira": "giri", "pada": "padi",
            "baitha": "baithi", "utha": "uthi", "mara": "mari",
            "toda": "todi", "tuta": "tuti", "toota": "tooti",
            # Compound perfective
            "toot gaya": "toot gayi", "ho gaya": "ho gayi",
            "a gaya": "a gayi", "aa gaya": "aa gayi",
            "chala gaya": "chali gayi", "gir gaya": "gir gayi",
            "tut gaya": "tut gayi", "ghus gaya": "ghus gayi",
            "ulat gaya": "ulat gayi", "ulta ho gaya": "ulti ho gayi",
            "kharab ho gaya": "kharab ho gayi",
            "kharaab ho gaya": "kharaab ho gayi",
            # Habitual -ta -> -ti
            "karta": "karti", "bolta": "bolti", "padhta": "padhti",
            "banata": "banati", "sunta": "sunti", "dekhta": "dekhti",
            "khelta": "khelti", "sota": "soti", "rota": "roti",
            "hota": "hoti", "jata": "jati", "ata": "ati", "aata": "aati",
            "likhta": "likhti", "seekhta": "seekhti",
            "karta tha": "karti thi", "bolta tha": "bolti thi",
            "padhta tha": "padhti thi",
            # Progressive -raha -> -rahi
            "raha": "rahi", "raha hai": "rahi hai", "raha tha": "rahi thi",
            "kar raha": "kar rahi", "bol raha": "bol rahi",
            "padh raha": "padh rahi", "bana raha": "bana rahi",
            "sun raha": "sun rahi", "dekh raha": "dekh rahi",
            "khel raha": "khel rahi", "so raha": "so rahi",
            "kha raha": "kha rahi", "pi raha": "pi rahi",
            "seekh raha": "seekh rahi", "khol raha": "khol rahi",
            "dal raha": "dal rahi", "khul raha": "khul rahi",
        }
        return mappings.get(masc_verb)

    # ── Ergative 'ne' Detection ──────────────────────────────────

    def detect_ergative(self, text: str) -> list:
        annotations = []
        words = text.lower().split()

        for i, w in enumerate(words):
            if w in self._perfective:
                # Check if this is a transitive perfective context
                stem = None
                for s in self._transitive_stems:
                    if w.startswith(s):
                        stem = s
                        break

                if stem:
                    # Look backward for 'ne'
                    preceding = words[max(0, i-5):i]
                    has_ne = "ne" in preceding

                    annotations.append(ErgativeAnnotation(
                        verb_stem=stem,
                        perfective_form=w,
                        has_ne=has_ne,
                        context=text,
                    ))
        return annotations

    # ── Code-Switch Detection ────────────────────────────────────

    def detect_code_switches(self, text: str) -> list:
        switches = []
        words = text.lower().split()

        bengali_positions = []
        hindi_positions = []
        english_positions = []

        for i, w in enumerate(words):
            clean = w.strip(".,!?;:'\"()-")
            ann = self.identify_language(clean)
            if ann.language == "bengali":
                bengali_positions.append((i, clean, ann.bengali_info))
            elif ann.language == "hindi":
                hindi_positions.append(i)
            elif ann.language == "english":
                english_positions.append(i)

        if not bengali_positions:
            return switches

        # Classify the switches
        bengali_runs = self._find_runs(bengali_positions)

        for run in bengali_runs:
            start_idx = run[0][0]
            end_idx = run[-1][0]
            bengali_span = " ".join(words[start_idx:end_idx+1])
            run_length = len(run)

            # Check for three-way mixing (Bengali + English nearby)
            nearby_english = any(
                abs(ep - start_idx) <= 3 or abs(ep - end_idx) <= 3
                for ep in english_positions
            )

            if nearby_english and run_length <= 2:
                switches.append(CodeSwitch(
                    switch_type="three_way",
                    rule_id="R6",
                    bengali_span=bengali_span,
                    hindi_context=text,
                    details="Bengali + English elements in Hindi matrix",
                ))
            elif run_length == 1:
                info = run[0][2]
                detail = ""
                if info:
                    detail = f"{run[0][1]} (Bengali) = {info.get('hindi', '?')} (Hindi), domain: {info.get('domain', '?')}"
                switches.append(CodeSwitch(
                    switch_type="tag_switch",
                    rule_id="R4",
                    bengali_span=bengali_span,
                    hindi_context=text,
                    details=detail,
                ))
            elif run_length <= 3:
                switches.append(CodeSwitch(
                    switch_type="intra_sentential",
                    rule_id="R4",
                    bengali_span=bengali_span,
                    hindi_context=text,
                    details=f"{run_length} Bengali words in Hindi frame",
                ))
            else:
                switches.append(CodeSwitch(
                    switch_type="inter_sentential",
                    rule_id="R5",
                    bengali_span=bengali_span,
                    hindi_context=text,
                    details=f"Full Bengali clause ({run_length} words)",
                ))

        return switches

    def _find_runs(self, positions: list) -> list:
        """Group Bengali word positions into contiguous/near-contiguous runs."""
        if not positions:
            return []
        runs = []
        current_run = [positions[0]]
        for pos in positions[1:]:
            # Allow a gap of up to 2 words (articles, particles between Bengali words)
            if pos[0] - current_run[-1][0] <= 3:
                current_run.append(pos)
            else:
                runs.append(current_run)
                current_run = [pos]
        runs.append(current_run)
        return runs

    # ── Full Segment Analysis ────────────────────────────────────

    def analyze_segment(self, text: str, speaker_code: str, segment_id: int = 0) -> SegmentAnalysis:
        # Transliterate Devanagari to Roman if needed
        if any('ऀ' <= c <= 'ॿ' for c in text):
            text = devanagari_to_roman(text)

        # Strip speaker/collector prefixes for analysis
        analysis_text = text
        speaker = None
        lines = text.split("\n")

        # Extract speaker lines only (ignore collector lines for error analysis)
        speaker_lines = []
        addressed = False
        for line in lines:
            line = line.strip()
            if line.startswith("c:") and re.search(r"\baap\w*\b", line.lower()):
                addressed = True
            if line.startswith("s:"):
                speaker_lines.append(line[2:].strip())
                speaker = speaker_code
            elif line.startswith("c:"):
                continue
            else:
                speaker_lines.append(line)
                speaker = speaker_code

        analysis_text = " ".join(speaker_lines) if speaker_lines else text

        # Word-level language ID
        word_annotations = []
        lang_counts = {"hindi": 0, "bengali": 0, "english": 0, "mixed": 0, "unknown": 0}
        for w in analysis_text.split():
            ann = self.identify_language(w)
            word_annotations.append(ann)
            lang_counts[ann.language] = lang_counts.get(ann.language, 0) + 1

        total = sum(lang_counts.values()) or 1
        lang_dist = {k: round(v / total, 4) for k, v in lang_counts.items() if v > 0}

        # Gender errors
        gender_errors = self.detect_gender_errors(analysis_text, speaker_code, addressed)

        # Ergative
        ergative = self.detect_ergative(analysis_text)

        # Code-switches
        code_switches = self.detect_code_switches(analysis_text)

        return SegmentAnalysis(
            segment_id=segment_id,
            speaker=speaker,
            text=analysis_text,
            word_annotations=word_annotations,
            gender_errors=gender_errors,
            ergative_annotations=ergative,
            code_switches=code_switches,
            language_distribution=lang_dist,
        )

    # ── Full Transcript Analysis ─────────────────────────────────

    def analyze_transcript(self, filepath: str, use_corrected: bool = True) -> TranscriptAnalysis:
        with open(filepath) as f:
            data = json.load(f)

        speaker_code = data.get("speaker_code", "")
        speaker_gender = SPEAKER_GENDERS.get(speaker_code, "?")

        result = TranscriptAnalysis(
            filename=filepath,
            speaker_code=speaker_code,
            speaker_gender=speaker_gender,
            total_segments=0,
            total_words=0,
        )

        total_lang = {"hindi": 0, "bengali": 0, "english": 0, "mixed": 0, "unknown": 0}
        total_gender_errors = {"noun_verb": 0, "subject_verb": 0}
        total_ergative = {"with_ne": 0, "without_ne": 0}
        total_switches = {"tag_switch": 0, "intra_sentential": 0,
                          "inter_sentential": 0, "three_way": 0}

        for seg in data.get("segments", []):
            text_field = "corrected_text" if use_corrected else "text"
            text = seg.get(text_field, "")
            if not text:
                continue

            seg_analysis = self.analyze_segment(text, speaker_code, seg.get("id", 0))
            result.segments.append(seg_analysis)
            result.total_segments += 1
            result.total_words += len(seg_analysis.word_annotations)

            # Accumulate counts
            for lang, count_frac in seg_analysis.language_distribution.items():
                n_words = len(seg_analysis.word_annotations)
                total_lang[lang] = total_lang.get(lang, 0) + round(count_frac * n_words)

            for ge in seg_analysis.gender_errors:
                total_gender_errors[ge.error_type] = total_gender_errors.get(ge.error_type, 0) + 1

            for ea in seg_analysis.ergative_annotations:
                if ea.has_ne:
                    total_ergative["with_ne"] += 1
                else:
                    total_ergative["without_ne"] += 1

            for cs in seg_analysis.code_switches:
                total_switches[cs.switch_type] = total_switches.get(cs.switch_type, 0) + 1

        total_w = sum(total_lang.values()) or 1
        result.summary = {
            "language_distribution": {k: round(v / total_w, 4) for k, v in total_lang.items() if v > 0},
            "gender_errors": total_gender_errors,
            "ergative": total_ergative,
            "code_switches": total_switches,
        }
        return result

    # ── Batch Analysis ───────────────────────────────────────────

    def analyze_corpus(self, filepaths: list, use_corrected: bool = True) -> dict:
        results = {}
        for fp in filepaths:
            try:
                results[fp] = self.analyze_transcript(fp, use_corrected)
            except Exception as e:
                results[fp] = {"error": str(e)}
        return results

    # ── Serialization ────────────────────────────────────────────

    @staticmethod
    def to_json(analysis, indent=2) -> str:
        def convert(obj):
            if hasattr(obj, '__dataclass_fields__'):
                return asdict(obj)
            return str(obj)
        if isinstance(analysis, dict):
            return json.dumps(
                {k: convert(v) for k, v in analysis.items()},
                indent=indent, ensure_ascii=False, default=convert,
            )
        return json.dumps(convert(analysis), indent=indent, ensure_ascii=False, default=convert)
