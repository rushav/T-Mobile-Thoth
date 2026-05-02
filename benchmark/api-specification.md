# Thoth Benchmark API — `/api/v1`

The `/api/v1` surface is the contract the evaluation harness exercises. It runs alongside the legacy `/api/...` surface (used by the frontend) but is independently authenticated and independently scoped.

## Authentication

Every `/api/v1/*` request must carry:

```
Authorization: Bearer <BENCHMARK_API_KEY>
```

The key is read from the `BENCHMARK_API_KEY` environment variable (or `.env`). Missing or wrong tokens return:

```json
HTTP 401  { "error": "Missing Bearer token", "code": "UNAUTHORIZED" }
HTTP 401  { "error": "Invalid API key",      "code": "UNAUTHORIZED" }
```

## Conventions

- All timestamps are ISO 8601 UTC, format `YYYY-MM-DDTHH:MM:SSZ`.
- IDs are namespaced strings: `sme_xxxxxxxx`, `int_xxxxxxxx`, `mat_xxxxxxxx`, `ke_xxxxxxxx`.
- Errors return the shape `{ "error": str, "code": str }`. Common codes: `UNAUTHORIZED`, `NOT_FOUND`, `INVALID_STATE_TRANSITION`, `INVALID_REQUEST`.
- Every LLM-invoking response includes a `usage: { input_tokens, output_tokens, total_tokens, ... }` block.

## Lifecycle of a knowledge entry

```
draft  ─[POST /knowledge/{id}/approve]──►  sme_approved
                                               │
                                       [POST /admin-approve]
                                               ▼
                                           approved   ── indexed in ChromaDB
                                               │
                                          [POST /reject]
                                               ▼
                                           rejected
```

## Endpoints

### Health
```
GET /api/v1/health
→ 200 { "status": "healthy", "timestamp": "<ISO>" }
```

### System
```
POST /api/v1/system/purge
→ 200 { "status": "purged" }      # wipes all SQL + ChromaDB state

POST /api/v1/system/reset
→ 200 { "status": "reset" }       # clears in-memory sessions; preserves KB
```

### SME profiles
```
POST /api/v1/smes
body: { name, specialization, sub_areas: [str], contact_email }
→ 201 { sme_id, name, specialization, sub_areas, contact_email, created_at }

GET  /api/v1/smes
→ 200 { smes: [...] }

GET  /api/v1/smes/{sme_id}
→ 200 { sme_id, ... }   |   404 NOT_FOUND
```

### Interviews
```
POST /api/v1/smes/{sme_id}/interviews
body: { topic }
→ 201 { interview_id, sme_id, topic, status: "in_progress", created_at }

POST /api/v1/interviews/{interview_id}/turns
body: { sme_response }
→ 200 { turn_number, sme_response, agent_follow_up, timestamp, usage }
→ 404 if interview_id not found

GET  /api/v1/interviews/{interview_id}
→ 200 { interview_id, sme_id, topic, status, turns: [...], created_at }

GET  /api/v1/smes/{sme_id}/interviews
→ 200 { interviews: [...] }
```

### Materials (file uploads)
```
POST /api/v1/smes/{sme_id}/materials   (multipart)
fields: file, title, description (optional)
constraints: file ≤ 10 MB; mime in { application/pdf, text/plain, text/markdown }
→ 201 { material_id, sme_id, title, file_type, status: "processed"|"failed", created_at }
→ 400 unsupported file type / file exceeds 10 MB limit

GET  /api/v1/smes/{sme_id}/materials
→ 200 { materials: [...] }
```

### Knowledge synthesis
```
POST /api/v1/smes/{sme_id}/knowledge/synthesize
body: { interview_ids: [str], material_ids: [str], topic }
→ 201 {
    entry_id, sme_id, topic, status: "draft", content, sources, created_at, updated_at,
    usage: { ... }
  }
```

### Knowledge entry lifecycle
```
PUT  /api/v1/knowledge/{entry_id}
body: { content }
→ 200 { entry_id, sme_id, topic, status, content, ... }   |   404 NOT_FOUND

POST /api/v1/knowledge/{entry_id}/approve         (SME approval: draft → sme_approved)
→ 200 { entry_id, status: "sme_approved", approved_at }
→ 409 INVALID_STATE_TRANSITION (entry not in draft)

POST /api/v1/knowledge/{entry_id}/admin-approve   (admin approval: sme_approved → approved)
→ 200 { entry_id, status: "approved", admin_approved_at }
→ 409 INVALID_STATE_TRANSITION (entry not in sme_approved)
NOTE: this endpoint accepts both V1 (ke_xxx) and legacy (integer) IDs.

POST /api/v1/knowledge/{entry_id}/reject
body (optional): { reason }
→ 200 { entry_id, status: "rejected", rejected_at }
→ 409 INVALID_STATE_TRANSITION (entry already rejected)

GET  /api/v1/knowledge?status=approved          (legacy list endpoint)
GET  /api/v1/knowledge/{entry_id}               (legacy by integer id)
```

### Query
```
POST /api/v1/query
body: { question: str, session_id?: str }
→ 200 {
    answer: str,
    grounded: bool,
    sources: [ { entry_id, sme_name, topic } ],
    disclaimer: str | null,
    session_id: str,
    response_type: "answer" | "clarification" | "routing",
    routed_to: [ { type: "sme"|"admin", sme_name, specialization, reason } ] | null,
    timestamp: ISO,
    usage: { ... } | null
  }
```

#### Response-type matrix

| Condition | response_type | grounded | disclaimer | sources |
|---|---|---|---|---|
| KB empty (closed-book) | `routing` (admin) | false | null | [] |
| Confidence ≥ 0.7, single subject, retrieval grounded | `answer` | true | present | ≥ 1 |
| Confidence 0.4-0.7 OR multiple close candidates | `clarification` | false | null | [] |
| Confidence < 0.4 | `routing` (admin) | false | null | [] |
| Subject matched but no relevant chunks | `routing` (sme for that subject) | false | null | [] |

#### Closed-book guarantee

When `count(approved entries) == 0`, the endpoint short-circuits to a `routing` response WITHOUT invoking the LLM. This is the parametric-leakage guard — no answers from training data, ever.

## Status codes the harness probes

| Status | When |
|---|---|
| 200 | Successful query / state read / state-changing op |
| 201 | Resource created (SME, interview, material, knowledge entry) |
| 400 | Invalid file type, oversized upload, bad request body |
| 401 | Missing or invalid Bearer token |
| 404 | Unknown SME / interview / knowledge entry |
| 409 | Invalid state transition (double approve, approve-without-SME, double reject) |

## Token telemetry

Every endpoint that calls the LLM returns a `usage` object:

```json
"usage": {
    "input_tokens":  1234,
    "output_tokens": 567,
    "cache_read_input_tokens":     0,
    "cache_creation_input_tokens": 0,
    "total_tokens":  1801
}
```

`null` is returned when no LLM call was made (closed-book short-circuit, simple state queries). The smoke suite (`test_benchmark.sh`) sums `total_tokens` across the run and prints `Total tokens consumed: <N>` at the end.

## Reference: `test_benchmark.sh`

The smoke suite at the repo root exercises the full surface end-to-end (36 tests), including auth, lifecycle, multi-turn, edge cases (404/409/400/401), and routing variants. Run it with the backend live:

```bash
./test_benchmark.sh
```
