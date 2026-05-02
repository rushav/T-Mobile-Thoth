from llm import chat
from agents.prompts import (
    INTERVIEWER_PROMPT_STRUCTURED,
    INTERVIEWER_PROMPT_FREEFORM,
    SYNTHESIS_PROMPT,
    REVISION_PROMPT,
)


def _interviewer_system_prompt(sme_name: str, subject_name: str, mode: str) -> str:
    template = INTERVIEWER_PROMPT_FREEFORM if mode == "freeform" else INTERVIEWER_PROMPT_STRUCTURED
    return template.format(sme_name=sme_name, subject_name=subject_name)


def next_message(sme_name: str, subject_name: str, messages: list[dict], mode: str = "structured") -> str:
    """Given conversation history, produce Thoth's next interviewer message.
    Uses the `fast` tier — interviewer turns are short and don't need quality
    model reasoning."""
    system = _interviewer_system_prompt(sme_name, subject_name, mode)
    api_messages = [{"role": m["role"], "content": m["content"]} for m in messages]
    if not api_messages:
        api_messages = [{"role": "user", "content": "Please begin the interview."}]
    return chat(system=system, messages=api_messages, max_tokens=600, temperature=0.6, tier="fast")


def synthesize(sme_name: str, subject_name: str, transcript: str, uploaded_text: str, mode: str = "structured") -> str:
    """Synthesis is the highest-stakes call (it produces the document the SME
    will approve into the KB). Uses the `quality` tier."""
    prompt = SYNTHESIS_PROMPT.format(
        sme_name=sme_name,
        subject_name=subject_name,
        interview_transcript=transcript,
        uploaded_file_contents=uploaded_text or "(none)",
        mode=mode,
    )
    return chat(
        system="",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500,
        temperature=0.2,
        tier="quality",
    )


def revise(sme_name: str, subject_name: str, transcript: str, uploaded_text: str,
           previous_synthesis: str, feedback: str) -> str:
    """Re-generate the synthesis given SME feedback. Stays grounded in transcript.
    Uses the `quality` tier."""
    prompt = REVISION_PROMPT.format(
        feedback=feedback or "(no specific feedback — re-synthesize to be more accurate)",
        interview_transcript=transcript,
        uploaded_file_contents=uploaded_text or "(none)",
        previous_synthesis=previous_synthesis or "(none)",
    )
    return chat(
        system="",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500,
        temperature=0.2,
        tier="quality",
    )


def transcript_from_messages(messages: list[dict]) -> str:
    lines = []
    for m in messages:
        role = "Thoth" if m.get("role") == "assistant" else "SME"
        if m.get("post_review"):
            role += " [post-review]"
        lines.append(f"{role}: {m.get('content', '')}")
    return "\n\n".join(lines)
