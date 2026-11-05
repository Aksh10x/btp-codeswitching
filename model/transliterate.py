"""
Basic Devanagari to Roman transliteration for Hindi.

Maps Devanagari characters to their common Roman equivalents as used in
informal Hindi romanization (the style our corrected transcripts use).
Not a rigorous IAST/ISO converter — optimized for matching against our
lexicon which uses colloquial Roman spellings.
"""

DEVANAGARI_MAP = {
    # Vowels
    'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo',
    'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au', 'ऋ': 'ri',
    # Vowel matras
    'ा': 'aa', 'ि': 'i', 'ी': 'ee', 'ु': 'u', 'ू': 'oo',
    'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au', 'ृ': 'ri',
    # Consonants
    'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'ng',
    'च': 'ch', 'छ': 'chh', 'ज': 'j', 'झ': 'jh', 'ञ': 'ny',
    'ट': 't', 'ठ': 'th', 'ड': 'd', 'ढ': 'dh', 'ण': 'n',
    'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
    'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm',
    'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v', 'w': 'w',
    'श': 'sh', 'ष': 'sh', 'स': 's', 'ह': 'h',
    # Nukta consonants
    'क़': 'q', 'ख़': 'kh', 'ग़': 'gh', 'ज़': 'z', 'फ़': 'f',
    'ड़': 'r', 'ढ़': 'rh',
    # Special
    'ं': 'n', 'ँ': 'n', 'ः': 'h',
    '्': '',  # halant / virama — suppresses inherent 'a'
    'ऽ': '',  # avagraha
    '़': '',  # nukta (handled via combined chars above)
}

# Punctuation passthrough
PASSTHROUGH = set('.,!?;:\'"()-/ 0123456789')


def devanagari_to_roman(text: str) -> str:
    """Convert Devanagari text to approximate Roman transliteration."""
    result = []
    i = 0
    chars = list(text)
    n = len(chars)

    while i < n:
        ch = chars[i]

        # ASCII passthrough
        if ch.isascii():
            result.append(ch)
            i += 1
            continue

        # Check for two-char sequences (nukta combinations)
        if i + 1 < n:
            pair = ch + chars[i + 1]
            if pair in DEVANAGARI_MAP:
                result.append(DEVANAGARI_MAP[pair])
                i += 2
                continue

        if ch in DEVANAGARI_MAP:
            val = DEVANAGARI_MAP[ch]

            # Halant: suppress the inherent 'a' of the previous consonant
            if ch == '्':
                # Remove trailing 'a' from the previous consonant if present
                if result and result[-1] == 'a':
                    result.pop()
                i += 1
                continue

            # Matra (vowel sign): replaces the inherent 'a'
            if ch in 'ािीुूेैोौृ':
                if result and result[-1] == 'a':
                    result.pop()
                result.append(val)
                i += 1
                continue

            # Regular consonant: add with inherent 'a'
            if ch not in 'अआइईउऊएऐओऔऋंँः' and val and val[0].isalpha():
                result.append(val)
                result.append('a')
            else:
                result.append(val)
            i += 1
        else:
            # Unknown character — pass through
            result.append(ch)
            i += 1

    # Clean up: remove trailing 'a' at word boundaries (schwa deletion)
    text_out = ''.join(result)
    # Simple schwa deletion: remove word-final 'a' (common in Hindi)
    words = text_out.split()
    cleaned = []
    for w in words:
        if len(w) > 2 and w[-1] == 'a' and w[-2].isalpha() and w[-2] not in 'aeiou':
            w = w[:-1]
        cleaned.append(w)

    return ' '.join(cleaned)
