"""Rule-first category suggestions and bounded, optional model assistance."""

import time
from collections.abc import Callable

from roadsaarthi import config
from roadsaarthi.model_provider import call_model

RULES: dict[str, dict[str, tuple[str, ...]]] = {
    "Gurmukhi Punjabi": {
        "Pothole": ("ਟੋਇਆ", "ਖੱਡਾ", "ਖੱਡੇ"),
        "Broken Guardrail": ("ਰੇਲਿੰਗ ਟੁੱਟ", "ਗਾਰਡਰੇਲ"),
        "Missing / Damaged Sign": ("ਸਾਈਨ", "ਨਿਸ਼ਾਨ", "ਬੋਰਡ ਟੁੱਟ"),
        "Waterlogging / Flooding": ("ਪਾਣੀ ਭਰ", "ਹੜ੍ਹ", "ਜਲਭਰਾਅ"),
        "Road Debris": ("ਮਲਬਾ", "ਟਾਹਣੀ", "ਕੂੜਾ"),
        "Unmarked Speed Bump": ("ਸਪੀਡ ਬ੍ਰੇਕਰ", "ਬਿਨਾਂ ਨਿਸ਼ਾਨ"),
        "Damaged Road Surface": ("ਸੜਕ ਟੁੱਟ", "ਦਰਾਰ", "ਉਖੜੀ"),
        "Other": ("ਹੋਰ ਸਮੱਸਿਆ", "ਹੋਰ ਖਤਰਾ"),
    },
    "Devanagari Hindi": {
        "Pothole": ("गड्ढा", "गड्ढे"),
        "Broken Guardrail": ("रेलिंग टूटी", "गार्डरेल"),
        "Missing / Damaged Sign": ("साइन", "संकेत", "बोर्ड टूटा"),
        "Waterlogging / Flooding": ("पानी भर", "जलभराव", "बाढ़"),
        "Road Debris": ("मलबा", "टहनी", "कचरा"),
        "Unmarked Speed Bump": ("स्पीड ब्रेकर", "बिना निशान"),
        "Damaged Road Surface": ("सड़क टूटी", "दरार", "उखड़ी"),
        "Other": ("अन्य समस्या", "अन्य खतरा"),
    },
    "Roman Punjabi": {
        "Pothole": ("toya", "khadda", "khadde"),
        "Broken Guardrail": ("railing tut", "guardrail tut", "rail tut"),
        "Missing / Damaged Sign": ("sign gayab", "board tut", "nishan nahi"),
        "Waterlogging / Flooding": ("paani bhar", "pani khada", "harrh"),
        "Road Debris": ("malba", "tahni", "kachra"),
        "Unmarked Speed Bump": ("speed breaker bina", "bina nishan"),
        "Damaged Road Surface": ("sadak tut", "sarak tut", "daraar"),
        "Other": ("hor samasya", "hor khatra"),
    },
    "Roman Hindi": {
        "Pothole": ("gaddha", "gadde"),
        "Broken Guardrail": ("rail toot", "railing toot", "guardrail toot"),
        "Missing / Damaged Sign": ("sign gayab", "board toot", "sanket nahi"),
        "Waterlogging / Flooding": ("paani bhar", "jalbharav", "baadh"),
        "Road Debris": ("malba", "tahni", "kachra"),
        "Unmarked Speed Bump": ("speed breaker bina", "bina nishan"),
        "Damaged Road Surface": ("sadak toot", "darar", "ukhad"),
        "Other": ("anya samasya", "anya khatra"),
    },
    "English": {
        "Pothole": ("pothole", "road hole"),
        "Broken Guardrail": ("guardrail", "barrier broken", "railing broken"),
        "Missing / Damaged Sign": ("sign missing", "sign damaged", "signboard"),
        "Waterlogging / Flooding": ("waterlogged", "flood", "waterlogging"),
        "Road Debris": ("debris", "fallen branch", "rubble"),
        "Unmarked Speed Bump": ("unmarked speed bump", "unmarked speed breaker"),
        "Damaged Road Surface": ("cracked road", "road surface damaged", "road is broken"),
        "Other": ("other hazard", "other road issue", "other road hazard"),
    },
}

PUNJABI_LANGUAGES = {"Gurmukhi Punjabi", "Roman Punjabi"}
_last_call: dict[str, float] = {}


def suggest_from_rules(text: str, language: str) -> str | None:
    """Return the first fixed category with a matching language keyword."""
    folded = text.casefold()
    matches = [
        category
        for category, words in RULES.get(language, {}).items()
        if any(word.casefold() in folded for word in words)
    ]
    return matches[0] if len(matches) == 1 else None


def get_assistance(
    text: str,
    language: str,
    client: Callable[..., dict] = call_model,
    now: float | None = None,
) -> dict:
    """Apply rules, enforce limits, and call the provider only as needed."""
    if len(text) > config.ASSISTANCE_INPUT_LIMIT:
        return {"category": suggest_from_rules(text, language), "summary": None,
                "model": None, "error": "Input is too long for assistance."}
    category = suggest_from_rules(text, language)
    if language in PUNJABI_LANGUAGES:
        return {"category": category, "summary": None, "model": None, "error": None}
    if not config.ASSISTANCE_ENABLED:
        return {"category": category, "summary": None, "model": None, "error": None}
    clock = time.monotonic() if now is None else now
    if clock - _last_call.get("local", -1e12) < config.ASSISTANCE_RATE_LIMIT_SECONDS:
        return {"category": category, "summary": None, "model": None,
                "error": "Please wait before requesting assistance again."}
    _last_call["local"] = clock
    try:
        result = client(
            text=text,
            language=language,
            task="summary" if category is not None else "category_and_summary",
        )
    except Exception:
        return {"category": category, "summary": None, "model": None,
                "error": "Local assistance is unavailable. Continue manually."}
    model_category = result.get("category")
    if category is None and model_category in config.HAZARD_CATEGORIES:
        category = model_category
    summary = result.get("summary")
    if not isinstance(summary, str):
        summary = None
    if summary:
        summary = " ".join(summary.split())[:240]
    return {"category": category, "summary": summary, "model": result.get("model"),
            "error": None}
