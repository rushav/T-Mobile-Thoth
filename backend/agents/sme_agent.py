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


def answer(subject_id: int, subject_name: str, question: str, n_results: int = 5) -> dict:
    chunks = vector_store.query(subject_id, question, n_results=n_results)
    context = format_context(chunks)
    system = SME_AGENT_PROMPT.format(subject_name=subject_name, retrieved_context=context)
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
