"""V1 benchmark interviewer: turn generation (haiku) + synthesis (sonnet)."""
from llm import chat_v1
from config import MODELS
from services.token_tracker import TokenTracker

_TURN_SYSTEM = """You are Thoth, an AI knowledge-capture interviewer. You are capturing expert knowledge about: {topic}.

Your job: ask ONE focused follow-up question based on what the expert just shared.

Interview stage guide (follow in order, one stage per turn):
- Stage 1: Ask the expert to walk through the key steps or facts about this topic.
- Stage 2: Ask what common questions people have about this topic.
- Stage 3: Ask about edge cases, exceptions, or common mistakes.
- Stage 4: Ask when someone should escalate to a human expert instead of relying on documentation.
- Stage 5+: Ask one focused follow-up if anything in the previous answer was unclear or incomplete. If the expert seems done, generate a brief closing acknowledgment.

Current stage: {stage}

Rules:
- ONE question only, 1-2 sentences.
- Do NOT summarize what they said.
- Do NOT use filler phrases like "Great answer!" or "Wonderful!".
- Make the question specific to what they actually shared.
"""

_SYNTHESIS_SYSTEM = """You are creating a structured knowledge entry from an expert interview.

STRICT RULES — these override everything else:
1. ONLY include information explicitly stated by the expert in the transcript or uploaded materials.
2. NEVER add external knowledge, extrapolate, or fill in "common best practices."
3. If the expert gave a brief or vague answer, the entry must be brief and vague too.
4. If a section would be empty, write exactly: "Not covered in this interview."
5. Use the expert's own phrasing wherever possible.

Produce a markdown document with these sections:
1. **Topic** — one sentence drawn from what the expert said.
2. **Key Information** — bullet points of main facts the expert stated.
3. **Common Questions & Answers** — only Q&A pairs the expert explicitly mentioned. If none, write "Not covered in this interview."
4. **Edge Cases & Exceptions** — only what the expert flagged. If none, write "Not covered in this interview."
5. **When to Escalate** — only what the expert said qualifies for escalation. If none, write "Not covered in this interview."
"""


def _stage_label(turn_number: int) -> str:
    stages = {1: "Stage 1", 2: "Stage 2", 3: "Stage 3", 4: "Stage 4"}
    return stages.get(turn_number, f"Stage 5+ (turn {turn_number})")


def generate_follow_up(
    topic: str,
    turns: list[dict],
    tracker: TokenTracker,
) -> tuple[str, TokenTracker]:
    """Generate the next interviewer follow-up question using haiku.

    `turns` must already include the current sme_response (agent_follow_up=None),
    so len(turns) equals the current turn number.
    Returns (follow_up_text, updated_tracker).
    """
    turn_number = len(turns)
    system = _TURN_SYSTEM.format(topic=topic, stage=_stage_label(turn_number))

    messages: list[dict] = []
    for t in turns:
        messages.append({"role": "user", "content": t["sme_response"]})
        if t.get("agent_follow_up"):
            messages.append({"role": "assistant", "content": t["agent_follow_up"]})

    if not messages:
        messages = [{"role": "user", "content": "(beginning of interview — please start)"}]

    text, usage = chat_v1(
        system=system,
        messages=messages,
        model=MODELS["fast"],
        max_tokens=300,
        temperature=0.7,
    )
    tracker.add(usage)
    return text, tracker


def synthesize(
    topic: str,
    turns: list[dict],
    material_texts: list[str],
    tracker: TokenTracker,
) -> tuple[str, TokenTracker]:
    """Synthesize a knowledge entry from interview turns + material texts using sonnet.

    Returns (synthesis_text, updated_tracker).
    """
    transcript_lines = []
    for t in turns:
        transcript_lines.append(f"Expert: {t['sme_response']}")
        if t.get("agent_follow_up"):
            transcript_lines.append(f"Interviewer: {t['agent_follow_up']}")
    transcript = "\n\n".join(transcript_lines) or "(no interview turns recorded)"

    materials_block = "\n\n---\n\n".join(material_texts) if material_texts else "(none)"

    user_prompt = f"""Topic: {topic}

Interview transcript:
{transcript}

Uploaded materials:
{materials_block}

Create the structured knowledge entry now."""

    text, usage = chat_v1(
        system=_SYNTHESIS_SYSTEM,
        messages=[{"role": "user", "content": user_prompt}],
        model=MODELS["quality"],
        max_tokens=1500,
        temperature=0.2,
    )
    tracker.add(usage)
    return text, tracker
