"""Thoth — the orchestrator. Classifies and routes. NEVER answers directly."""
from sqlalchemy.orm import Session
import models
from services import classifier
from agents import sme_agent


HIGH_CONFIDENCE = 0.7
MIN_CONFIDENCE = 0.5


def handle_query(db: Session, question: str, user_id: int | None) -> dict:
    subjects = db.query(models.Subject).all()
    subject_dicts = [{"id": s.id, "name": s.name, "description": s.description} for s in subjects]

    result = classifier.classify(subject_dicts, question)
    subject_name = result.get("subject")
    confidence = result.get("confidence", 0.0)
    reasoning = result.get("reasoning", "")

    matched = None
    if subject_name:
        matched = next((s for s in subjects if s.name.lower() == str(subject_name).lower()), None)

    # High confidence: route to SME agent
    if matched and confidence >= HIGH_CONFIDENCE:
        agent_reply = sme_agent.answer(matched.id, matched.name, question)
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

    # Medium confidence: ask a clarifying question
    if confidence >= MIN_CONFIDENCE:
        possibles = [s.name for s in subjects]
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
            "reasoning": reasoning,
        }

    # Low confidence: escalate
    esc = models.Escalation(
        user_query=question,
        user_id=user_id,
        reason=reasoning or "No confident subject match",
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
        "reasoning": reasoning,
    }
