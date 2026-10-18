"""Deterministic script detection for complaint language selection."""

from collections import Counter

GURMUKHI = "Gurmukhi Punjabi"
DEVANAGARI = "Devanagari Hindi"
ROMAN = "Roman script"
UNKNOWN = "Unknown script"
SUPPORTED_LANGUAGES = ("Gurmukhi Punjabi", "Devanagari Hindi", "Roman Punjabi", "Roman Hindi", "English")


def detect_script(text: str) -> str:
    """Classify by Unicode script ranges; never infer a Roman language."""
    scripts: Counter[str] = Counter()
    for char in text:
        code = ord(char)
        if 0x0A00 <= code <= 0x0A7F:
            scripts[GURMUKHI] += 1
        elif 0x0900 <= code <= 0x097F:
            scripts[DEVANAGARI] += 1
        elif char.isalpha() and char.isascii():
            scripts[ROMAN] += 1
    if not scripts:
        return UNKNOWN
    if len(scripts) != 1:
        return UNKNOWN
    return scripts.most_common(1)[0][0]


def resolve_language(text: str, roman_language: str | None = None) -> str | None:
    """Resolve Indic scripts directly and require explicit Roman selection."""
    script = detect_script(text)
    if script in (GURMUKHI, DEVANAGARI):
        return script
    if script == ROMAN and roman_language in (
        "Roman Punjabi", "Roman Hindi", "English"
    ):
        return roman_language
    if script == UNKNOWN and roman_language in SUPPORTED_LANGUAGES:
        return roman_language
    return None
