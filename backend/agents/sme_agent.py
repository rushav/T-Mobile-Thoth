from sqlalchemy.orm import Session
import models
import vector_store
from llm import chat
from agents.prompts import SME_AGENT_PROMPT
from services.token_tracker import TokenTracker


# Phrases the SME agent emits when it has no grounding. We detect these to
# flag the response as not grounded so the /api/v1/query endpoint can convert
# them into routing responses instead of pretending to have answered.
NO_KNOWLEDGE_MARKERS = (
    "i don't have enough approved knowledge",
    "i don't have that information",
    "this question is outside my domain",
    "let me connect you with a specialist",
    "let me redirect you",
)


def format_context(chunks: list[dict]) -> str:
    if not chunks:
        return "(no approved knowledge found)"
    parts = []
    for i, c in enumerate(chunks, 1):
        title = (c.get("metadata") or {}).get("title", f"Entry {i}")
        doc = c.get("document", "")
        parts.append(f"[{i}] {title}\n{doc}")
    return "\n\n---\n\n".join(parts)


def expertise_for_subject(db: Session, subject_id: int) -> str:
    subject = db.query(models.Subject).filter(models.Subject.id == subject_id).first()
    if not subject:
        return ""
    seen: list[str] = []
    for sme in subject.smes:
        ea = (sme.expertise_area or "").strip()
        if ea and ea not in seen:
            seen.append(ea)
    return ", ".join(seen)


def is_refusal(text: str) -> bool:
    """True if the agent's text indicates it refused to answer for lack of knowledge."""
    t = (text or "").lower()
    return any(marker in t for marker in NO_KNOWLEDGE_MARKERS)


def answer(
    db: Session,
    subject_id: int,
    subject_name: str,
    question: str,
    n_results: int = 5,
    prior_exchange: tuple[str, str] | None = None,
    tracker: TokenTracker | None = None,
) -> dict:
    """Answer a question scoped to one subject, using only retrieved approved entries.

    Returns: {answer, sources, chunks, grounded}
      - grounded: True iff at least one chunk was retrieved AND the agent did
        not refuse. The /api/v1/query layer uses this to decide whether to
        return an "answer" response or convert to "routing".
    """
    retrieval_query = prior_exchange[0] if prior_exchange else question
    chunks = vector_store.query(subject_id, retrieval_query, n_results=n_results)

    # Hard short-circuit: if no chunks were retrieved at all for this subject,
    # don't burn tokens calling the LLM. This is the hot path for the
    # closed-book test on a per-subject basis.
    if not chunks:
        return {
            "answer": "I don't have enough approved knowledge to answer this.",
            "sources": [],
            "chunks": [],
            "grounded": False,
        }

    context = format_context(chunks)
    expertise = expertise_for_subject(db, subject_id)
    expertise_clause = f", specializing in {expertise}" if expertise else ""
    system = SME_AGENT_PROMPT.format(
        subject_name=subject_name,
        expertise_clause=expertise_clause,
        retrieved_context=context,
    )
    messages: list[dict] = []
    if prior_exchange:
        prev_q, prev_a = prior_exchange
        messages.append({"role": "user", "content": prev_q})
        messages.append({"role": "assistant", "content": prev_a})
    messages.append({"role": "user", "content": question})
    reply = chat(
        system=system,
        messages=messages,
        max_tokens=700,
        temperature=0.2,
        tier="fast",
        tracker=tracker,
    )

    grounded = bool(chunks) and not is_refusal(reply)

    return {
        "answer": reply,
        "sources": [
            {
                "entry_id": (c.get("metadata") or {}).get("entry_id"),
                "title": (c.get("metadata") or {}).get("title"),
                "subject_id": (c.get("metadata") or {}).get("subject_id"),
            }
            for c in chunks
        ],
        "chunks": chunks,
        "grounded": grounded,
    }
