from llm import chat
from agents.prompts import INTERVIEWER_PROMPT, SYNTHESIS_PROMPT


def next_message(sme_name: str, subject_name: str, messages: list[dict]) -> str:
    """Given conversation history, produce Thoth's next interviewer message.

    `messages` is the conversation from the SME's perspective (SME is the 'user'
    in the turn structure), but if the list is empty we prompt Thoth to open.
    """
    system = INTERVIEWER_PROMPT.format(sme_name=sme_name, subject_name=subject_name)
    api_messages = [{"role": m["role"], "content": m["content"]} for m in messages]
    if not api_messages:
        # Kick off — ask Thoth to start the interview.
        api_messages = [{"role": "user", "content": "Please begin the interview."}]
    return chat(system=system, messages=api_messages, max_tokens=600, temperature=0.7)


def synthesize(sme_name: str, subject_name: str, transcript: str, uploaded_text: str) -> str:
    prompt = SYNTHESIS_PROMPT.format(
        sme_name=sme_name,
        subject_name=subject_name,
        interview_transcript=transcript,
        uploaded_file_contents=uploaded_text or "(none)",
    )
    return chat(system="", messages=[{"role": "user", "content": prompt}],
                max_tokens=1500, temperature=0.3)


def transcript_from_messages(messages: list[dict]) -> str:
    lines = []
    for m in messages:
        role = "Thoth" if m.get("role") == "assistant" else "SME"
        lines.append(f"{role}: {m.get('content', '')}")
    return "\n\n".join(lines)
