# Project Thoth

## What this is
An AI-powered SME knowledge capture and retrieval system for a GIX/T-Mobile hackathon. Two-week PoC. Two software devs (John, Rushav), two designers working in Figma.

The visual design language (T-Mobile magenta `#E20074`, white background, rounded cards) comes from the designers' Thothweb prototype and is applied to our minimal functional frontend.

---

## Core architecture principle
Thoth is the ORCHESTRATOR. It NEVER answers user questions directly. Subject-specific LLM agents (same base model, scoped RAG context) handle all user-facing answers. This prevents cross-contamination between knowledge domains.

## Tech stack
- Backend: Python 3.11+, FastAPI, uvicorn
- Frontend: React (Vite), Tailwind CSS — single-window, login-gated
- Database: SQLite via SQLAlchemy
- Vector store: ChromaDB (one collection per subject)
- LLM: Anthropic Claude API via `anthropic` Python SDK; Sonnet for synthesis/answers, Haiku for classification/follow-ups
- File parsing: PyPDF2, python-docx
- Embeddings: ChromaDB default (all-MiniLM-L6-v2)

## Project structure
```
project-thoth/
├── README.md                  # Submission-ready overview
├── ARCHITECTURE.md            # System diagrams + design rationale
├── PRODUCTION_RECOMMENDATIONS.md
├── DEMO_SCRIPT.md             # Live-demo runbook
├── CLAUDE.md                  # This file — project brain
├── PROMPTS.md                 # All LLM prompts
├── benchmark/
│   └── api-specification.md   # /api/v1 benchmark contract
├── backend/
│   ├── main.py                # FastAPI app, CORS, /api/v1 auth middleware
│   ├── config.py              # env vars, dirs
│   ├── database.py            # SQLAlchemy setup
│   ├── models.py              # Legacy + V1 ORM models
│   ├── vector_store.py        # ChromaDB collections + retrieval
│   ├── seed.py                # 5 SMEs, 10 approved entries, users + admin
│   ├── agents/
│   │   ├── thoth.py           # Orchestrator (legacy)
│   │   ├── interviewer.py / interviewer_v1.py
│   │   ├── sme_agent.py       # Subject-scoped answer agent
│   │   └── prompts.py
│   ├── routes/
│   │   ├── profiles.py / interviews.py / review.py / query.py
│   │   ├── admin.py / subjects.py / files.py
│   │   └── v1/                # Benchmark API surface
│   ├── services/
│   │   ├── classifier.py      # Subject + clarification classifier
│   │   ├── knowledge.py       # CRUD + ChromaDB indexing
│   │   ├── file_parser.py
│   │   ├── sessions.py        # In-memory session state
│   │   └── token_tracker.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # Routes + auth guard
│   │   ├── auth.js            # useAuth hook, single-key localStorage
│   │   ├── api.js             # fetch wrapper
│   │   ├── pages/
│   │   │   ├── LoginPage.jsx          # Role → profile picker
│   │   │   ├── UserChatPage.jsx
│   │   │   ├── SMEDashboardPage.jsx
│   │   │   └── AdminPage.jsx
│   │   └── components/
│   │       ├── TopBar.jsx             # Role + name + sign out
│   │       ├── ChatWindow.jsx
│   │       ├── MessageBubble.jsx
│   │       └── ReviewPanel.jsx
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── launch.sh / launch.bat
├── test_benchmark.sh
├── .env / .env.example
├── .gitignore
└── data/  (gitignored — SQLite DB + ChromaDB persistence)
```

## Database schema (SQLite)
Two parallel surfaces share the database:

**Legacy (frontend uses this):**
```
profiles (id, name, role [user|sme|admin], expertise_area, contact_info, ...)
subjects (id, name, description)
sme_subjects (profile_id, subject_id)
knowledge_entries (id, subject_id, contributor_id, title, content,
                   status [pending|pending_admin_review|approved|rejected], ...)
files / interviews / escalations / query_history
```

**V1 benchmark (`/api/v1/...` uses this):**
```
v1_sme_profiles (sme_id [str], name, specialization, sub_areas [JSON], contact_email)
v1_interviews (interview_id [str], sme_id, topic, status, turns [JSON])
v1_materials (material_id [str], sme_id, title, file_type, extracted_text, status)
v1_knowledge_entries (entry_id [str], sme_id, topic, status [draft|sme_approved|approved|rejected], content, sources [JSON])
```

## Approval flow
1. SME approves synthesis → status = "sme_approved" (V1) / "pending_admin_review" (legacy)
2. Entry appears in admin approval queue
3. Admin approves → status = "approved", content indexed in ChromaDB
4. Admin rejects → status = "rejected", entry removed from ChromaDB

## Demo data (seeded by `backend/seed.py`)
Five SMEs with realistic, fact-rich content (precise figures, fees, deadlines — designed to expose hallucination):

| SME | Specialization | Sample fact |
|---|---|---|
| Dr. Sarah Chen | Food Safety & Health Inspections | A grade = 90-100 points; reinspection #2 = $275 |
| Marcus Williams | Commercial Real Estate Leasing | Class A urban TIA: $45-$75/sf |
| Dr. Priya Patel | Workplace Ergonomics & Injury Prevention | Negative keyboard tilt cuts wrist strain 28% |
| James Ortega | Small Business Tax Compliance | Section 179 limit (2024): $1,160,000 |
| Dr. Nina Kowalski | Environmental Compliance for Small Businesses | No EPA ID penalty: $37,500/day |

Users: Alex Rivera, Jordan Lee. Admin: Pat Morgan.

## Integration contract (don't change without testing both surfaces)
```python
# Legacy knowledge entry statuses
LEGACY_STATUSES = ["pending", "pending_admin_review", "approved", "rejected"]
# V1 (benchmark) statuses
V1_STATUSES     = ["draft", "sme_approved", "approved", "rejected"]

# ChromaDB collection naming (both surfaces share collections)
COLLECTION_NAME = f"subject_{subject_id}"

# V1 chunk metadata
{ "v1_entry_id": "ke_xxx", "sme_id": "sme_xxx", "topic": "...", ... }

# Legacy chunk metadata
{ "entry_id": int, "title": "...", ... }
```

## Key behaviors (do not regress)
- Thoth never answers user questions directly — it classifies and routes only.
- No raw interview transcripts to users — only approved summaries.
- BOTH SME approval AND admin approval are required for an entry to enter the active KB.
- Each ChromaDB collection is per-subject and only queried by that subject's agent.
- Confidence ≥ 0.7 → route to agent. 0.4-0.7 → clarifying question. < 0.4 → escalate.
- SMEs only see their own subjects.
- Synthesis must only contain information the SME explicitly stated.
- All LLM responses rendered as markdown via react-markdown.
- Closed-book guarantee: with zero approved entries, the V1 query endpoint short-circuits to admin routing without invoking the LLM (no parametric leakage).
- Every grounded answer ships with a disclaimer + sources + token usage.

## How LLM agents work
Same base model, scoped system prompt + scoped RAG retrieval per subject. NOT separate models. See `PROMPTS.md` for prompt text.

## Frontend architecture (current)
- Single window. Routes: `/` (login), `/chat` (user), `/sme`, `/admin`.
- Login flow: pick role → list profiles for that role → click to "log in".
- Auth state: single localStorage key `thoth.user`, exposed via the `useAuth()` hook.
- `TopBar` shows current role + name + sign-out.
- No polling — refresh the page to pull fresh state.

## What NOT to build
- No real authentication (this is a PoC; the V1 benchmark surface uses a single Bearer key)
- No WebSocket real-time updates
- No production deployment / CI/CD
- No mobile responsiveness

## Commands
```bash
# First-time setup (Ubuntu 24+ / PEP 668)
python3 -m venv .venv
source .venv/bin/activate
cd backend && pip install -r requirements.txt
python seed.py

# Run
source .venv/bin/activate
cd backend && uvicorn main:app --reload --port 8000
cd frontend && npm install && npm run dev

# One-shot
./launch.sh

# Reset
rm data/thoth.db && rm -rf data/chroma/ && cd backend && python seed.py

# Benchmark smoke test (with backend running)
./test_benchmark.sh
```
