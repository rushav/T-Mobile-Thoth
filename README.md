# Project Thoth

**AI-powered SME knowledge capture and retrieval — GIX × T-Mobile hackathon submission.**

Thoth is an orchestrator. It does not answer user questions directly. Instead, it classifies each question and routes it to a subject-scoped LLM agent that retrieves only from approved, SME-authored knowledge. Cross-domain contamination, parametric leakage from training data, and unverified content are all blocked at the architectural level.

---

## Why this exists

T-Mobile (and most large enterprises) have deep subject knowledge locked in the heads of senior employees. Capturing that knowledge as documentation is slow, lossy, and the result is rarely searchable in context. Thoth turns the capture step into a guided interview, the storage step into a per-subject vector index, and the retrieval step into scoped, grounded answers with mandatory citation and disclaimer.

## What ships in this PoC

- **Knowledge capture**: SMEs run AI-led structured or freeform interviews. Thoth synthesizes a draft entry strictly from what the SME said.
- **Two-stage approval**: SME approves their own synthesis → admin approves before content enters the live knowledge base.
- **Scoped retrieval**: each subject has its own ChromaDB collection; the answering agent only sees that collection.
- **Routing**: high-confidence questions → answer; mid-confidence → clarifying question; low-confidence → admin escalation.
- **Closed-book guarantee**: with zero approved entries, the query endpoint refuses to invoke the LLM. No training-data leakage.
- **Disclaimer on every grounded answer**: source IDs, SME name, and a "based on internal SME knowledge" notice.
- **Token telemetry**: every LLM call is tracked; the V1 query endpoint reports per-request usage.
- **/api/v1 benchmark surface**: a separate Bearer-authenticated API for the evaluation harness.

## Quick start

```bash
# One-shot (creates venv, installs deps, seeds DB on first run, opens browser)
./launch.sh

# Or manual
python3 -m venv .venv && source .venv/bin/activate
cd backend && pip install -r requirements.txt && python seed.py
uvicorn main:app --reload --port 8000

# In a second shell
cd frontend && npm install && npm run dev
```

Frontend: http://localhost:5173 · Backend: http://localhost:8000 · Swagger: http://localhost:8000/docs

### Sign in
Open the frontend, pick a role (User / SME / Admin), then click a seeded profile to "log in".
- **User**: Alex Rivera, Jordan Lee
- **SME**: Dr. Sarah Chen (Food Safety), Marcus Williams (CRE Leasing), Dr. Priya Patel (Ergonomics), James Ortega (Tax), Dr. Nina Kowalski (Environmental)
- **Admin**: Pat Morgan

### Try a query
Ask the User chat: "What score gives a restaurant an A grade?" → routes to Food Safety agent, answers from KB (90-100 points), shows the disclaimer and source.

Ask: "What's the Section 179 deduction limit?" → Tax agent answers $1,160,000.

Ask: "How do I train my dog?" → no matching subject, escalates to admin.

## Benchmark API

The `/api/v1/...` surface implements the evaluator's contract. See `benchmark/api-specification.md` for the full schema, and run the smoke suite with:

```bash
./test_benchmark.sh
```

Requires the backend running and a `BENCHMARK_API_KEY` in `.env`.

> **Deployed URL**: _to be filled in before submission_
> **Benchmark API key**: _to be filled in before submission_

## Architecture summary

| Layer | Component | Responsibility |
|---|---|---|
| Orchestration | `services/classifier.py` | Subject classification + clarifying questions |
| Routing | `routes/v1/query.py` | Confidence thresholds → answer / clarify / route |
| Retrieval | `vector_store.py` | Per-subject ChromaDB collections |
| Generation | `agents/sme_agent.py` | Subject-scoped answer with mandatory citation |
| Capture | `agents/interviewer_v1.py` | Interview turns + synthesis (Sonnet) |
| Lifecycle | `routes/v1/knowledge.py` | draft → sme_approved → approved |
| Guard | `main.py` middleware | Bearer auth on `/api/v1` |

See **[ARCHITECTURE.md](./ARCHITECTURE.md)** for diagrams, data model, and capability mapping. See **[PRODUCTION_RECOMMENDATIONS.md](./PRODUCTION_RECOMMENDATIONS.md)** for the path from PoC to deployable service. **[DEMO_SCRIPT.md](./DEMO_SCRIPT.md)** has the live-demo runbook.

## Tech stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy + SQLite, ChromaDB, `anthropic` SDK
- **Frontend**: React 18, Vite, Tailwind CSS, react-router-dom, react-markdown
- **LLM**: Claude Sonnet 4 for synthesis & answers, Haiku 4.5 for classification & follow-ups
- **Embeddings**: ChromaDB default (`all-MiniLM-L6-v2`)

## Team

- Rushav (backend, V1 benchmark, classifier, frontend integration)
- John (interview pipeline, knowledge service, file parsing)
- Lisa Li & Mengting Li (visual design, prototyped in Figma → Thothweb)

## Repository layout

```
backend/        FastAPI app, agents, routes, services, ORM, seed
frontend/       Vite/React single-window UI
benchmark/      api-specification.md (the V1 contract)
data/           Runtime artifacts (gitignored — SQLite + Chroma)
launch.sh       One-shot dev startup
test_benchmark.sh  Smoke + edge-case suite for /api/v1
```
