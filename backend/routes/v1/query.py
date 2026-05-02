"""POST /api/v1/query — the benchmark's single conversational endpoint.

This handles three response_types in one call:
  - "answer"        — grounded answer from approved KB content
  - "clarification" — ask the user to disambiguate between subjects
  - "routing"       — point the user at an SME or admin

Closed-book guarantee: if the KB has zero approved entries we short-circuit
to "routing" without calling the LLM at all. This is the 10% benchmark slice
that punishes hallucination from training data.

Parametric leakage guarantee: even when entries exist, the SME agent prompt
forbids using training data, and we further filter at the response layer —
if the agent output looks like a refusal ("I don't have enough approved
knowledge to answer this") we convert it to a routing response so grounded=
false answers don't slip through as if they were grounded.
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import models
from database import get_db
from services import classifier, sessions
from services.token_tracker import TokenTracker
from agents import sme_agent

from ._common import DISCLAIMER, error, utc_now_iso

router = APIRouter(prefix="/api/v1", tags=["v1-query"])


HIGH_CONFIDENCE = 0.7
MIN_CONFIDENCE = 0.4
CLARIFY_GAP = 0.15


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    session_id: str | None = None


def _has_close_competitors(candidates: list[dict], top_confidence: float) -> bool:
    near = [c for c in candidates if c.get("confidence", 0.0) >= top_confidence - CLARIFY_GAP]
    return len(near) > 1


def _approved_entry_count(db: Session) -> int:
    """Count approved entries across BOTH the legacy KnowledgeEntry table and
    the V1 SME-pipeline table. Either is enough to disable the closed-book
    short-circuit."""
    legacy = db.query(models.KnowledgeEntry).filter(models.KnowledgeEntry.status == "approved").count()
    v1 = db.query(models.V1KnowledgeEntry).filter(models.V1KnowledgeEntry.status == "approved").count()
    return legacy + v1


def _sme_for_subject(db: Session, subject: models.Subject) -> models.Profile | None:
    return next(iter(subject.smes), None) if subject.smes else None


def _format_sources(chunks: list[dict], db: Session) -> list[dict]:
    """Turn raw retrieval chunks into the {entry_id, sme_name, topic} shape the
    benchmark expects.

    Chunks may come from either the legacy KnowledgeEntry table (metadata has
    `entry_id`/`title`) or the V1 SME pipeline (metadata has `v1_entry_id`/
    `topic` and points at V1SMEProfile). Branch on which key is present."""
    if not chunks:
        return []
    out: list[dict] = []
    seen: set = set()
    for c in chunks:
        meta = c.get("metadata") or {}
        v1_id = meta.get("v1_entry_id")
        if v1_id:
            if v1_id in seen:
                continue
            seen.add(v1_id)
            v1 = db.query(models.V1KnowledgeEntry).filter(
                models.V1KnowledgeEntry.entry_id == v1_id
            ).first()
            sme_name: str | None = None
            topic = (v1.topic if v1 else meta.get("topic"))
            if v1:
                sme = db.query(models.V1SMEProfile).filter(
                    models.V1SMEProfile.sme_id == v1.sme_id
                ).first()
                if sme:
                    sme_name = sme.name
            out.append({"entry_id": v1_id, "sme_name": sme_name, "topic": topic})
            continue

        entry_id = meta.get("entry_id")
        if entry_id is None or entry_id in seen:
            continue
        seen.add(entry_id)
        entry = db.query(models.KnowledgeEntry).filter(models.KnowledgeEntry.id == entry_id).first()
        sme_name = None
        topic = meta.get("title")
        if entry:
            topic = entry.title or topic
            if entry.contributor:
                sme_name = entry.contributor.name
        out.append({"entry_id": int(entry_id), "sme_name": sme_name, "topic": topic})
    return out


def _routing_admin_response(reason: str, session_id: str, usage: dict | None,
                            answer_text: str | None = None) -> dict:
    """Standard 'route to admin' shape — used for closed-book and for unknown
    questions that don't match any subject."""
    return {
        "answer": answer_text or "I don't have any approved knowledge to answer this question. Let me connect you with an administrator.",
        "grounded": False,
        "sources": [],
        "disclaimer": None,
        "session_id": session_id,
        "response_type": "routing",
        "routed_to": [
            {
                "type": "admin",
                "sme_name": None,
                "specialization": None,
                "reason": reason,
            }
        ],
        "timestamp": utc_now_iso(),
        "usage": usage,
    }


def _routing_sme_response(sme: models.Profile | None, subject: models.Subject,
                          reason: str, session_id: str, usage: dict | None) -> dict:
    sme_name = sme.name if sme else None
    specialization = (sme.expertise_area if sme and sme.expertise_area else subject.name)
    return {
        "answer": (
            f"I don't have approved knowledge on this yet, but {sme_name} is the SME for {subject.name}."
            if sme_name
            else f"I don't have approved knowledge on this yet. The relevant subject is {subject.name}."
        ),
        "grounded": False,
        "sources": [],
        "disclaimer": None,
        "session_id": session_id,
        "response_type": "routing",
        "routed_to": [
            {
                "type": "sme",
                "sme_name": sme_name,
                "specialization": specialization,
                "reason": reason,
            }
        ],
        "timestamp": utc_now_iso(),
        "usage": usage,
    }


def _clarification_response(question: str, candidates: list[dict], session_id: str,
                            tracker: TokenTracker) -> dict:
    possibles = [c["subject"] for c in candidates if c.get("confidence", 0.0) >= MIN_CONFIDENCE]
    if not possibles:
        possibles = [c["subject"] for c in candidates]
    seen = set()
    possibles = [s for s in possibles if not (s in seen or seen.add(s))]

    clar = classifier.clarifying_question(question, possibles, tracker=tracker) if possibles \
        else "Could you give me a bit more detail about what you're asking?"

    return {
        "answer": clar,
        "grounded": False,
        "sources": [],
        "disclaimer": None,
        "session_id": session_id,
        "response_type": "clarification",
        "routed_to": None,
        "timestamp": utc_now_iso(),
        "usage": tracker.to_dict(),
    }


def _answer_response(question: str, subject: models.Subject, agent_reply: dict,
                     session_id: str, tracker: TokenTracker, db: Session) -> dict:
    sources = _format_sources(agent_reply.get("chunks") or [], db)
    return {
        "answer": agent_reply["answer"],
        "grounded": True,
        "sources": sources,
        "disclaimer": DISCLAIMER,
        "session_id": session_id,
        "response_type": "answer",
        "routed_to": None,
        "timestamp": utc_now_iso(),
        "usage": tracker.to_dict(),
    }


@router.post("/query")
def query_v1(payload: QueryRequest = Body(...), db: Session = Depends(get_db)):
    question = (payload.question or "").strip()
    if not question:
        return error(400, "INVALID_REQUEST", "question is required")

    session_id = payload.session_id or sessions.new_session_id()
    tracker = TokenTracker()

    # --- Closed-book short-circuit ---------------------------------------
    # If there is literally no approved knowledge, we MUST NOT call the LLM
    # to answer from its training data. Route to admin and return.
    if _approved_entry_count(db) == 0:
        sessions.set(session_id, last_response_type="routing")
        return _routing_admin_response(
            reason="No approved knowledge is available in the system.",
            session_id=session_id,
            usage=None,
        )

    # --- Multi-turn: prior turn was a clarification ----------------------
    state = sessions.get(session_id) or {}
    if state.get("last_response_type") == "clarification" and state.get("pending_question"):
        # Treat the new message as the clarifier for the original question.
        classify_input = (
            f"{state['pending_question']}\n\n"
            f"User clarified: {question}"
        )
    else:
        classify_input = question

    # --- Classify --------------------------------------------------------
    subjects = db.query(models.Subject).all()
    if not subjects:
        sessions.set(session_id, last_response_type="routing")
        return _routing_admin_response(
            reason="No subjects are configured in the system.",
            session_id=session_id,
            usage=tracker.to_dict(),
        )

    subject_dicts = [{"id": s.id, "name": s.name, "description": s.description} for s in subjects]
    cls = classifier.classify(subject_dicts, classify_input, tracker=tracker)
    confidence = cls.get("confidence", 0.0)
    candidates = cls.get("candidates") or []
    matched_name = cls.get("subject")
    matched: models.Subject | None = None
    if matched_name:
        wanted = str(matched_name).strip().strip('"').lower()
        matched = next(
            (s for s in subjects if s.name.lower() == wanted),
            None,
        )
        if not matched:
            # Tolerate the model returning "name — description" or "name:
            # description" by matching any subject whose name is a prefix of
            # the returned string.
            matched = next(
                (s for s in subjects if wanted.startswith(s.name.lower())),
                None,
            )

    ambiguous = _has_close_competitors(candidates, confidence)

    # --- Route: clear winner, high confidence ----------------------------
    if matched and confidence >= HIGH_CONFIDENCE and not ambiguous:
        agent_reply = sme_agent.answer(
            db, matched.id, matched.name, question, tracker=tracker
        )
        if agent_reply.get("grounded"):
            sessions.set(
                session_id,
                last_response_type="answer",
                last_subject_id=matched.id,
            )
            return _answer_response(question, matched, agent_reply, session_id, tracker, db)

        # Subject is correct but no chunks / agent refused — route to the SME
        # for that subject so the user can get help.
        sme = _sme_for_subject(db, matched)
        sessions.set(session_id, last_response_type="routing")
        return _routing_sme_response(
            sme,
            matched,
            reason=f"No approved knowledge entries cover this question yet. {matched.name} is the relevant subject.",
            session_id=session_id,
            usage=tracker.to_dict(),
        )

    # --- Clarify: mid confidence or ambiguous between multiple subjects --
    if confidence >= MIN_CONFIDENCE or ambiguous:
        # If we are ALREADY in a clarification turn, don't ask again — the user
        # already gave us their disambiguator. Route to whatever the best match
        # is, even if confidence is mid; otherwise we loop forever.
        if state.get("last_response_type") == "clarification":
            if matched:
                agent_reply = sme_agent.answer(
                    db, matched.id, matched.name, question, tracker=tracker
                )
                if agent_reply.get("grounded"):
                    sessions.set(
                        session_id,
                        last_response_type="answer",
                        last_subject_id=matched.id,
                    )
                    return _answer_response(question, matched, agent_reply, session_id, tracker, db)
                sme = _sme_for_subject(db, matched)
                sessions.set(session_id, last_response_type="routing")
                return _routing_sme_response(
                    sme,
                    matched,
                    reason=f"Best match after clarification: {matched.name}.",
                    session_id=session_id,
                    usage=tracker.to_dict(),
                )

        sessions.set(
            session_id,
            last_response_type="clarification",
            pending_question=question,
            pending_candidates=candidates,
        )
        return _clarification_response(question, candidates, session_id, tracker)

    # --- Low confidence: route to admin ----------------------------------
    sessions.set(session_id, last_response_type="routing")
    return _routing_admin_response(
        reason="The question doesn't match any subject in the system with sufficient confidence.",
        session_id=session_id,
        usage=tracker.to_dict(),
    )
