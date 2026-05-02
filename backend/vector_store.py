import chromadb
from chromadb.config import Settings
from config import CHROMA_DIR

_client = chromadb.PersistentClient(
    path=str(CHROMA_DIR),
    settings=Settings(anonymized_telemetry=False),
)


def collection_name(subject_id: int) -> str:
    return f"subject_{subject_id}"


def get_collection(subject_id: int):
    return _client.get_or_create_collection(name=collection_name(subject_id))


def add_entry(subject_id: int, entry_id: int, title: str, content: str):
    coll = get_collection(subject_id)
    doc_id = f"entry_{entry_id}"
    # Upsert behavior: delete if it exists, then add
    try:
        coll.delete(ids=[doc_id])
    except Exception:
        pass
    coll.add(
        ids=[doc_id],
        documents=[f"{title}\n\n{content}"],
        metadatas=[{"entry_id": entry_id, "title": title, "subject_id": subject_id}],
    )


def query(subject_id: int, question: str, n_results: int = 5):
    coll = get_collection(subject_id)
    try:
        res = coll.query(query_texts=[question], n_results=n_results)
    except Exception:
        return []
    out = []
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]
    for i, doc in enumerate(docs):
        out.append({
            "document": doc,
            "metadata": metas[i] if i < len(metas) else {},
            "distance": dists[i] if i < len(dists) else None,
        })
    return out


def remove_entry(subject_id: int, entry_id: int):
    coll = get_collection(subject_id)
    try:
        coll.delete(ids=[f"entry_{entry_id}"])
    except Exception:
        pass


def add_v1_entry(subject_id: int, v1_entry_id: str, sme_id: str, topic: str, content: str):
    """Index a V1 SME-pipeline knowledge entry into the same Chroma collection
    we use for legacy entries. The metadata uses `v1_entry_id` (string) instead
    of the integer `entry_id` so the query layer can tell them apart."""
    coll = get_collection(subject_id)
    doc_id = f"v1_entry_{v1_entry_id}"
    try:
        coll.delete(ids=[doc_id])
    except Exception:
        pass
    coll.add(
        ids=[doc_id],
        documents=[f"{topic}\n\n{content}"],
        metadatas=[{
            "v1_entry_id": v1_entry_id,
            "topic": topic,
            "sme_id": sme_id,
            "subject_id": subject_id,
        }],
    )


def remove_v1_entry(subject_id: int, v1_entry_id: str):
    coll = get_collection(subject_id)
    try:
        coll.delete(ids=[f"v1_entry_{v1_entry_id}"])
    except Exception:
        pass
