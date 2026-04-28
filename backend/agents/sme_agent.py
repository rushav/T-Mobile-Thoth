from sqlalchemy.orm import Session
import models
import vector_store
from llm import chat
from agents.prompts import SME_AGENT_PROMPT


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
    """Join the distinct expertise areas of all SMEs assigned to this subject.

    Returns "" if no SME has an expertise_area set.
    """
    subject = db.query(models.Subject).filter(models.Subject.id == subject_id).first()
    if not subject:
        return ""
    seen: list[str] = []
    for sme in subject.smes:
        ea = (sme.expertise_area or "").strip()
        if ea and ea not in seen:
            seen.append(ea)
    return ", ".join(seen)


def answer(db: Session, subject_id: int, subject_name: str, question: str, n_results: int = 5) -> dict:
    chunks = vector_store.query(subject_id, question, n_results=n_results)
    context = format_context(chunks)
    expertise = expertise_for_subject(db, subject_id)
    expertise_clause = f", specializing in {expertise}" if expertise else ""
    system = SME_AGENT_PROMPT.format(
        subject_name=subject_name,
        expertise_clause=expertise_clause,
        retrieved_context=context,
    )
    reply = chat(
        system=system,
        messages=[{"role": "user", "content": question}],
        max_tokens=700,
        temperature=0.3,
    )
    return {
        "answer": reply,
        "sources": [
            {
                "entry_id": (c.get("metadata") or {}).get("entry_id"),
                "title": (c.get("metadata") or {}).get("title"),
            }
            for c in chunks
        ],
    }
