"""
Section Labeler: maps transcript segments to questionnaire sections.

Study design sections:
  A — Object naming (photos of household items)
  B — Adjective agreement (size/quality comparisons between photos)
  C — Object agreement / perfective (action descriptions from photos)
  D — Subject agreement / intransitive (descriptions of states/results)
  E — Conversation (free talk about work, daily life)
  F — Background (personal info: origin, languages, education)
"""

import json
import os
import re


SECTION_DEFINITIONS = {
    "A": {
        "name": "Object Naming",
        "description": "Speaker names household objects shown in photos",
        "cues": ["kya hai", "photo dikha", "batana hai ki woh kya hai",
                 "sabse pehle aaye", "dimaag mein pehle"],
        "content_cues": ["hai,", "door", "chair", "fan", "book", "house",
                         "window", "glass", "roti", "car", "key", "chaabi"],
    },
    "B": {
        "name": "Adjective Agreement",
        "description": "Speaker describes differences between photo pairs (big/small)",
        "cues": ["phark kya hai", "farak dikhta", "dono mein", "in dono"],
        "content_cues": ["bada", "chota", "big", "small", "same"],
    },
    "C": {
        "name": "Object Agreement / Perfective",
        "description": "Speaker describes actions in photos (eating, opening, reading, pouring)",
        "cues": ["kya kar raha", "kya kar rahi", "explain karna",
                 "iss photo mein", "kya kiya iss bande"],
        "content_cues": ["kha raha", "kha rahi", "khol raha", "khol rahi",
                         "padh raha", "padh rahi", "daal raha", "dal raha",
                         "gir gaya", "gir gayi", "tut gaya", "tut gayi",
                         "toot gaya", "bhenge", "kharab ho"],
    },
    "D": {
        "name": "Subject Agreement / Intransitive",
        "description": "Speaker describes results/states (broken chair, open window, fallen glass)",
        "cues": ["kya hua", "kya ho gaya"],
        "content_cues": ["tut gaya", "tut gayi", "bhenge", "kharab",
                         "ulta ho gaya", "ulti", "khula", "tuta", "toota"],
    },
    "E": {
        "name": "Conversation",
        "description": "Free conversation about work, daily routine, difficulties",
        "cues": ["students kaise", "mushkil", "pareshaani", "kitne ghante",
                 "routine batao", "subah se leke", "kya kya kiya",
                 "shift", "duty", "kaam", "job"],
        "content_cues": ["allotment", "hostel", "canteen", "mess",
                         "shift", "duty", "morning", "evening",
                         "problem", "mushkil", "pareshaani"],
    },
    "F": {
        "name": "Background",
        "description": "Personal background: birthplace, languages, education",
        "cues": ["kaha se ho", "background", "janam kaha", "ghar mein",
                 "konsi bhasha", "kitni languages", "kab tak padhe",
                 "school mein", "hindi kab", "bengali"],
        "content_cues": ["Kharagpur", "janam", "bengali", "hindi",
                         "school", "class", "padha", "seekha",
                         "language", "bhasha", "medium"],
    },
}


def label_segment(text: str, prev_section: str = None) -> str:
    """
    Assign a section label to a transcript segment.

    Uses collector cues (questions that mark section transitions) and
    content cues (vocabulary typical of each section). Falls back to
    the previous segment's section for continuations.
    """
    text_lower = text.lower()
    scores = {}

    for section, defn in SECTION_DEFINITIONS.items():
        score = 0
        # Collector cues are strong signals (they mark transitions)
        for cue in defn["cues"]:
            if cue in text_lower:
                score += 3

        # Content cues are weaker signals
        for cue in defn["content_cues"]:
            if cue in text_lower:
                score += 1

        scores[section] = score

    best = max(scores, key=scores.get)
    if scores[best] > 0:
        return best

    # No strong match — continue from previous section
    if prev_section:
        return prev_section

    return "E"  # default to conversation


def label_transcript(filepath: str) -> dict:
    """Label all segments in a transcript file."""
    with open(filepath) as f:
        data = json.load(f)

    prev_section = None
    labeled_segments = []

    for seg in data.get("segments", []):
        text = seg.get("corrected_text", seg.get("text", ""))
        section = label_segment(text, prev_section)
        prev_section = section

        labeled_segments.append({
            "id": seg.get("id"),
            "section": section,
            "section_name": SECTION_DEFINITIONS[section]["name"],
            "text_preview": text[:80] + "..." if len(text) > 80 else text,
        })

    return {
        "file": data.get("file", ""),
        "speaker_code": data.get("speaker_code", ""),
        "segments": labeled_segments,
        "section_counts": {
            s: sum(1 for seg in labeled_segments if seg["section"] == s)
            for s in SECTION_DEFINITIONS
        },
    }


def label_corpus(transcript_dir: str, output_path: str = None) -> dict:
    """Label all transcripts in a directory."""
    results = {}
    files = sorted(f for f in os.listdir(transcript_dir)
                   if f.endswith("_transcript.json")
                   and not f.startswith("transcription_"))

    for fname in files:
        fpath = os.path.join(transcript_dir, fname)
        results[fname] = label_transcript(fpath)

    if output_path:
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

    return results
