"""Thoth — the orchestrator. Classifies and routes. NEVER answers directly."""
from sqlalchemy.orm import Session
import models
from services import classifier
from agents import sme_agent


HIGH_CONFIDENCE = 0.7   # >= → route to subject agent
MIN_CONFIDENCE = 0.4    # >= but < HIGH_CONFIDENCE → ask clarifying question
                        # <  → escalate to admin
CLARIFY_GAP = 0.15      # if top two candidates within this gap, treat as ambiguous


def _has_close_competitors(candidates: list[dict], top_confidence: float) -> bool:
    """True if more than one candidate is within CLARIFY_GAP of the top."""
    near = [c for c in candidates if c.get("confidence", 0.0) >= top_confidence - CLARIFY_GAP]
    return len(near) > 1


def handle_query(
    db: Session,
    question: str,
    user_id: int | None,
    extra_context: str | None = None,
) -> dict:
    """Route the user's question to a subject agent, ask a clarifying question, or escalate.

    `extra_context` (e.g. text extracted from an attached file) is appended to the
    question for both classification and the agent's answer, but the original
    `question` is what gets recorded in QueryHistory.
    """
    subjects = db.query(models.Subject).all()
    subject_dicts = [{"id": s.id, "name": s.name, "description": s.description} for s in subjects]

    augmented = question if not extra_context else f"{question}\n\n{extra_context}"

    result = classifier.classify(subject_dicts, augmented)
    subject_name = result.get("subject")
    confidence = result.get("confidence", 0.0)
    candidates = result.get("candidates") or []
    reasoning = result.get("reasoning", "")

    matched = None
    if subject_name:
        matched = next((s for s in subjects if s.name.lower() == str(subject_name).lower()), None)

    ambiguous = _has_close_competitors(candidates, confidence)

    # High confidence AND a clear winner → route to SME agent
    if matched and confidence >= HIGH_CONFIDENCE and not ambiguous:
        agent_reply = sme_agent.answer(db, matched.id, matched.name, augmented)
        record = models.QueryHistory(
            user_id=user_id,
            question=question,
            answer=agent_reply["answer"],
            subject_id=matched.id,
            status="answered",
            confidence=f"{confidence:.2f}",
        )
        db.add(record)
        db.commit()
        return {
            "status": "answered",
            "subject": matched.name,
            "subject_id": matched.id,
            "confidence": confidence,
            "answer": agent_reply["answer"],
            "sources": agent_reply["sources"],
            "reasoning": reasoning,
        }

    # Ambiguous OR mid-confidence → ask a clarifying question
    if confidence >= MIN_CONFIDENCE or ambiguous:
        # Prefer the candidates list when we have several plausible subjects.
        possibles = [c["subject"] for c in candidates if c.get("confidence", 0.0) >= MIN_CONFIDENCE]
        if not possibles:
            possibles = [s.name for s in subjects]
        # Deduplicate while preserving order.
        seen = set()
        possibles = [s for s in possibles if not (s in seen or seen.add(s))]
        clar = classifier.clarifying_question(question, possibles)
        record = models.QueryHistory(
            user_id=user_id,
            question=question,
            answer=clar,
            subject_id=matched.id if matched else None,
            status="clarifying",
            confidence=f"{confidence:.2f}",
        )
        db.add(record)
        db.commit()
        return {
            "status": "clarifying",
            "question": clar,
            "confidence": confidence,
            "candidates": candidates,
            "reasoning": reasoning,
        }

    # Low confidence everywhere → escalate
    reason = "No matching subject" if not candidates else "Low confidence across all subjects"
    esc = models.Escalation(
        user_query=question,
        user_id=user_id,
        reason=reasoning or reason,
        candidates=candidates,
        status="open",
    )
    db.add(esc)
    record = models.QueryHistory(
        user_id=user_id,
        question=question,
        answer="I'll connect you with an administrator.",
        subject_id=None,
        status="escalated",
        confidence=f"{confidence:.2f}",
    )
    db.add(record)
    db.commit()
    db.refresh(esc)
    return {
        "status": "escalated",
        "message": "I'll connect you with an administrator.",
        "escalation_id": esc.id,
        "confidence": confidence,
        "candidates": candidates,
        "reasoning": reasoning,
    }
