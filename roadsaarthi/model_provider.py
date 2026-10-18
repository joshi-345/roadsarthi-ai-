"""The single local model boundary; complaint text is never logged."""

import json
from urllib.request import Request, urlopen

from roadsaarthi import config


def call_model(text: str, language: str, task: str) -> dict:
    """Ask Ollama for a JSON category suggestion and English summary."""
    clipped = text[: config.ASSISTANCE_INPUT_LIMIT]
    category_instruction = (
        "Suggest one category from: " + ", ".join(config.HAZARD_CATEGORIES)
        if task != "summary"
        else "Set category to null."
    )
    prompt = (
        "Return only JSON with keys category and summary. " + category_instruction
        + " summary must be a short English summary using only facts explicitly "
          "present; do not add time, cause, location, or details. If unknown, use null. "
        f"Language: {language}. Task: {task}. Complaint: {clipped}"
    )
    body = json.dumps({
        "model": config.ASSISTANCE_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "think": False,
        "keep_alive": 0,
        "options": {"num_predict": 160},
    }).encode("utf-8")
    request = Request(
        f"{config.ASSISTANCE_BASE_URL}/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=config.ASSISTANCE_TIMEOUT_SECONDS) as response:
        payload = json.loads(response.read().decode("utf-8"))
    parsed = json.loads(payload.get("response", "{}"))
    return {
        "category": parsed.get("category"),
        "summary": parsed.get("summary"),
        "model": payload.get("model", config.ASSISTANCE_MODEL),
    }
