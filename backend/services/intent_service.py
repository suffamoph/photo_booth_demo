from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any
from urllib import error, request


@dataclass
class IntentResult:
    intent: str
    confidence: float
    reason: str
    source: str
    model: str = ""


# Hardcoded configuration
PROVIDER = "ollama"
MODEL = "qwen3.5:9b"
BASE_URL = "http://127.0.0.1:11434"
TIMEOUT_SECONDS = 20
TEMPERATURE = 0.0

VALID_INTENTS = {
    "chat",
    "id_photo",
    "portrait",
    "ip_group",
    "virtual_checkin",
}

SYSTEM_PROMPT = """
You are an intent classifier for an AI photo booth app. You will analyze the user input and classify their intent for photo-related tasks:
- id_photo: Standard identification photos such as one-inch, two-inch, or any specific size photos for visas, IDs, licenses, resumes, or other scenarios with standard requirements.
- portrait: Casual or aesthetic portrait photography.
- ip_group: When users want to take a photo with a specific or famous person, character, or celebrity.
- virtual_checkin: When users want to take a virtual photo as if they were in a certain place, attraction, famous building, venue, or other special locations.
- chat: If the input does not match any of the types above.

Return only JSON with keys: intent, confidence, reason.
- intent must be one of the allowed intents.
- confidence must be a float in [0, 1].
Allowed intents: {', '.join(sorted(VALID_INTENTS))}.
"""


def _load_intent_keywords() -> dict[str, list[str]]:
    """Load intent keywords from JSON configuration."""
    config_file = Path(__file__).parent.parent / "config" / "intent_keywords.json"
    with open(config_file, encoding="utf-8") as f:
        return json.load(f)


INTENT_KEYWORDS = _load_intent_keywords()


def _rule_based_detect(text: str) -> IntentResult:
    normalized = (text or "").strip().lower()

    if not normalized:
        return IntentResult(intent="chat", confidence=0.4, reason="empty input", source="rule", model="")

    for intent, words in INTENT_KEYWORDS.items():
        valid_words = [word.strip().lower() for word in words if isinstance(word, str) and word.strip()]
        if any(word in normalized for word in valid_words):
            return IntentResult(
                intent=intent,
                confidence=0.88,
                reason=f"matched keywords for {intent}",
                source="rule",
                model="",
            )

    return IntentResult(intent="chat", confidence=0.7, reason="fallback to chat", source="rule", model="")


def _read_json_from_text(text: str) -> dict[str, Any] | None:
    stripped = (text or "").strip()
    if not stripped:
        return None

    if stripped.startswith("```"):
        parts = stripped.split("```")
        for part in parts:
            chunk = part.strip()
            if not chunk:
                continue
            if chunk.startswith("json"):
                chunk = chunk[4:].strip()
            try:
                parsed = json.loads(chunk)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                continue

    left = stripped.find("{")
    right = stripped.rfind("}")
    if left >= 0 and right > left:
        try:
            parsed = json.loads(stripped[left : right + 1])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return None

    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        return None

    return None


def _build_messages(text: str) -> list[dict[str, str]]:
    user = f"User input: {text}"
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]



def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str], timeout_s: float) -> dict[str, Any]:
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with request.urlopen(req, timeout=timeout_s) as resp:  # nosec B310
        body = resp.read().decode("utf-8")
    parsed = json.loads(body)
    if not isinstance(parsed, dict):
        raise ValueError("LLM response is not a JSON object")
    return parsed


def _llm_detect(text: str) -> IntentResult | None:
    url = f"{BASE_URL}/api/chat"
    payload = {
        "model": MODEL,
        "stream": False,
        "format": "json",
        "messages": _build_messages(text),
        "options": {"temperature": TEMPERATURE},
    }
    headers = {"Content-Type": "application/json"}

    raw = _post_json(url, payload, headers, TIMEOUT_SECONDS)
    content = (raw.get("message") or {}).get("content", "")

    parsed = _read_json_from_text(content)
    if not parsed:
        return None

    intent = str(parsed.get("intent", "")).strip().lower()
    if intent not in VALID_INTENTS:
        return None

    confidence_raw = parsed.get("confidence", 0.6)
    try:
        confidence = float(confidence_raw)
    except (TypeError, ValueError):
        confidence = 0.6
    confidence = max(0.0, min(1.0, confidence))

    reason = str(parsed.get("reason", "llm classified")).strip() or "llm classified"
    return IntentResult(intent=intent, confidence=confidence, reason=reason, source="llm", model=MODEL)



def detect_intent(text: str) -> IntentResult:
    try:
        # Step 1: Try LLM-based detection
        llm_result = _llm_detect(text)
        if llm_result:
            return llm_result
    except (error.URLError, error.HTTPError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
        # Log LLM error and fallback to rule-based detection
        fallback = _rule_based_detect(text)
        fallback.reason = f"llm error: {exc}; {fallback.reason}"
        fallback.source = "rule_fallback"
        return fallback

    # Step 2: Fallback to rule-based detection if LLM fails silently
    rule_result = _rule_based_detect(text)
    if rule_result.intent != "chat":
        return rule_result

    # Step 3: Final fallback to chat intent
    return IntentResult(intent="chat", confidence=0.5, reason="fallback to chat intent", source="fallback", model= "")

