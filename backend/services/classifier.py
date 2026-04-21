import json
import re
from llm import complete
from agents.prompts import CLASSIFIER_PROMPT, CLARIFICATION_PROMPT


def classify(subjects: list[dict], question: str) -> dict:
    """subjects: [{id, name, description}]. Returns {subject, confidence, reasoning}."""
    subjects_list = "\n".join(
        f"- {s['name']}: {s.get('description') or ''}" for s in subjects
    ) or "(none)"
    prompt = CLASSIFIER_PROMPT.format(subjects_list=subjects_list, user_question=question)
    raw = complete(prompt, max_tokens=300, temperature=0.0)
    data = _extract_json(raw)
    if not isinstance(data, dict):
        return {"subject": None, "confidence": 0.0, "reasoning": "Could not parse classifier response"}
    # Normalize
    subject_name = data.get("subject")
    try:
        confidence = float(data.get("confidence") or 0.0)
    except (TypeError, ValueError):
        confidence = 0.0
    return {
        "subject": subject_name,
        "confidence": max(0.0, min(1.0, confidence)),
        "reasoning": data.get("reasoning") or "",
    }


def clarifying_question(question: str, possible_subjects: list[str]) -> str:
    prompt = CLARIFICATION_PROMPT.format(
        user_question=question,
        possible_subjects="\n".join(f"- {s}" for s in possible_subjects),
    )
    return complete(prompt, max_tokens=150, temperature=0.4)


def _extract_json(text: str):
    text = (text or "").strip()
    if not text:
        return None
    # Strip common code fences
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except Exception:
        pass
    # Find first {...} block
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None
