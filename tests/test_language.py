from roadsaarthi.language import (
    DEVANAGARI, GURMUKHI, ROMAN, UNKNOWN, detect_script, resolve_language,
)


def test_indic_scripts_are_deterministic():
    assert detect_script("ਸੜਕ ਤੇ ਖੱਡਾ") == GURMUKHI
    assert detect_script("सड़क पर गड्ढा") == DEVANAGARI


def test_roman_requires_explicit_language():
    assert detect_script("sadak par gaddha") == ROMAN
    assert resolve_language("sadak par gaddha") is None
    assert resolve_language("sadak par gaddha", "Roman Punjabi") == "Roman Punjabi"


def test_mixed_or_inconclusive_script_requires_selection():
    assert detect_script("ਸੜਕ road") == UNKNOWN
    assert detect_script("123 !!!") == UNKNOWN
    assert resolve_language("123 !!!") is None
    assert resolve_language("ਸੜਕ road", "English") == "English"
