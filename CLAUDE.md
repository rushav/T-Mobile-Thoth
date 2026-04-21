# Project Thoth

## What this is
An AI-powered SME knowledge capture and retrieval system for a GIX/T-Mobile hackathon. 2-week PoC due May 4, 2026. Two software devs (John, Rushav), two designers working separately in Figma.

## Core architecture principle
Thoth is the ORCHESTRATOR. It NEVER answers user questions directly. Subject-specific LLM agents (same base model, scoped RAG context) handle all user-facing answers. This prevents cross-contamination between knowledge domains.

## Tech stack
- Backend: Python 3.11+, FastAPI, uvicorn
- Frontend: React (Vite), Tailwind CSS — barebones functional UI only, designers handle polish later
- Database: SQLite via SQLAlchemy (structured data: profiles, entries, approvals)
- Vector store: ChromaDB (RAG retrieval, one collection per subject)
- LLM: Anthropic Claude API via `anthropic` Python SDK, model `claude-sonnet-4-20250514`
- File parsing: PyPDF2, python-docx for uploaded files
- Embeddings: ChromaDB default (all-MiniLM-L6-v2) or `sentence-transformers`

## Project structure
```
project-thoth/
├── CLAUDE.md
├── backend/
│   ├── main.py                 # FastAPI app, CORS, startup
│   ├── config.py               # env vars, API keys
│   ├── database.py             # SQLAlchemy setup, SQLite
│   ├── models.py               # DB models (Profile, KnowledgeEntry, Subject, etc.)
│   ├── vector_store.py         # ChromaDB setup, one collection per subject
│   ├── seed.py                 # Demo data seeding script
│   ├── agents/
│   │   ├── thoth.py            # Orchestrator: classifier + router
│   │   ├── interviewer.py      # Conducts SME interviews, generates synthesis
│   │   ├── sme_agent.py        # Subject-specific agent (scoped system prompt + RAG)
│   │   └── prompts.py          # All system prompts in one place
│   ├── routes/
│   │   ├── profiles.py         # Create/list/select profiles (no auth)
│   │   ├── interviews.py       # Start interview, send messages, get synthesis
│   │   ├── review.py           # SME review/approve/reject synthesis
│   │   ├── query.py            # User asks question → Thoth routes → agent answers
│   │   ├── admin.py            # Approval queue, escalation inbox, SME directory
│   │   └── files.py            # Upload PDF/text, parse, store
│   ├── services/
│   │   ├── knowledge.py        # CRUD for knowledge entries
│   │   ├── file_parser.py      # Extract text from PDF/docx/txt
│   │   └── classifier.py       # Classify question → subject
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx             # Router
│   │   ├── api.js              # Fetch wrapper for backend
│   │   ├── pages/
│   │   │   ├── LoginPage.jsx       # Role picker + profile select
│   │   │   ├── UserChatPage.jsx    # User asks questions
│   │   │   ├── SMEDashboardPage.jsx # Interview + review dashboard
│   │   │   └── AdminPage.jsx       # Approval queue + escalations
│   │   └── components/
│   │       ├── ChatWindow.jsx      # Reusable chat component
│   │       ├── MessageBubble.jsx   # Single message with agent indicator
│   │       ├── ReviewPanel.jsx     # Approve/reject synthesis
│   │       └── SubjectBadge.jsx    # Shows which agent is active
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── data/
│   ├── chroma/                 # ChromaDB persistent storage
│   └── uploads/                # User-uploaded files
├── .env                        # ANTHROPIC_API_KEY
├── PROMPTS.md                  # LLM prompt reference
├── DEMO_SCRIPT.md              # Demo walkthrough for May 4
└── README.md
```

## Database schema (SQLite)
```sql
profiles (id, name, role [user|sme|admin], expertise_area, created_at)
subjects (id, name, description, created_at)
sme_subjects (profile_id FK, subject_id FK)
knowledge_entries (id, subject_id FK, contributor_id FK, title, content,
                   status [pending|approved|rejected], approved_by,
                   approved_at, review_date, created_at)
files (id, entry_id FK, filename, filepath, file_type, extracted_text, created_at)
interviews (id, sme_id FK, subject_id FK, messages JSON,
            synthesis TEXT, synthesis_status [draft|pending_review|approved|rejected],
            created_at)
escalations (id, user_query, user_id FK, reason, status [open|assigned|resolved],
             assigned_to FK, resolution TEXT, created_at)
```

## Demo data (seeded by seed.py)
- Subjects: Coffee, Milk Tea, Cars
- SMEs: Lisa Li (Coffee), Mengting Li (Milk Tea), Rushav (Cars)
- Users: Alex Rivera, Jordan Lee
- Admin: Pat Morgan
- 2 approved knowledge entries per subject pre-loaded into ChromaDB
- Test: John Huang will be added live as a new SME for "Climbing" during demo

## How the LLM agents work
Each subject gets its own agent. They are NOT separate models. They use the same Claude API with:
1. A scoped system prompt: "You are the {subject} knowledge agent. Only answer from {subject} knowledge."
2. Scoped RAG retrieval: query only the ChromaDB collection for that subject
3. If the agent can't answer confidently, it returns a low-confidence signal to Thoth

Thoth's classifier prompt: "Given these subjects: [{list}], which best matches: '{user_question}'? Return JSON: {subject, confidence}"

## API endpoints
```
POST   /api/profiles              # Create profile
GET    /api/profiles?role=sme     # List profiles by role
POST   /api/profiles/login        # Select profile (sets session)

POST   /api/interviews/start      # Start interview session (sme_id, subject)
POST   /api/interviews/{id}/message  # Send message in interview
POST   /api/interviews/{id}/synthesize  # Generate synthesis
POST   /api/interviews/{id}/review     # SME approve/reject/request-changes

POST   /api/query                 # User asks question → Thoth routes → agent answers
GET    /api/query/history         # Past questions for current user

GET    /api/admin/pending         # Pending approvals
POST   /api/admin/approve/{id}    # Approve entry
GET    /api/admin/escalations     # Escalated questions
GET    /api/admin/directory       # SME directory by subject

POST   /api/files/upload          # Upload file, parse, link to entry
GET    /api/subjects              # List all subjects
POST   /api/subjects              # Create new subject
```

## Key behaviors
- NEVER let Thoth answer user questions directly. It classifies and routes only.
- NEVER expose raw interview transcripts to users. Only approved summaries.
- NOTHING enters the active knowledge base without explicit SME approval.
- Each ChromaDB collection is named `subject_{subject_id}` and is only queried by its own agent.
- When no subject matches a question, escalate to admin — don't guess.
- Store conversation history as JSON in the interviews table.

## Code style
- Python: type hints, async where possible, Pydantic models for request/response
- React: functional components, hooks, minimal state management (useState/useContext)
- No class components, no Redux
- Use fetch() for API calls, not axios
- Error handling: try/except in Python, .catch() in JS
- Environment variables via python-dotenv, never hardcode API keys

## Commands
```bash
# Backend
cd backend && pip install -r requirements.txt
python seed.py                    # Seed demo data (run once)
uvicorn main:app --reload --port 8000

# Frontend
cd frontend && npm install
npm run dev                       # Runs on port 5173
```

## What NOT to build
- No real authentication (just name-based profiles)
- No WebSocket real-time chat (use polling or simple request/response)
- No production deployment config
- No CI/CD
- No comprehensive error pages
- No mobile responsiveness (desktop demo only)
