# Project Thoth

## What this is
An AI-powered SME knowledge capture and retrieval system for a GIX/T-Mobile hackathon. 2-week PoC due May 4, 2026. Two software devs (John, Rushav), two designers working separately in Figma.

---

## DEVELOPER WORKFLOW (READ THIS FIRST)

This project has two developers. Each has their own README that tracks what they changed. Claude Code manages everything — the developer never manually edits changelogs.

### Starting a session
```
1. git pull
2. Open terminal in project root
3. Run: claude
4. First message to Claude Code every session:

   "Read CLAUDE.md, PROMPTS.md, and both developer READMEs (RUSHAV_README.md and JOHN_README.md). 
    I am [Rushav/John]. Check the other developer's changelog for any changes since my last session 
    and tell me if anything affects my files. Then I'll tell you what to work on."
```

Claude Code will:
- Read all context files
- Check the other dev's changelog for new entries
- Flag anything that touches shared files or integration points
- Wait for your instructions

### During a session
Just tell Claude Code what to build, fix, or change. Work normally.

### Ending a session
Before you push, tell Claude Code:

```
"Update my README (RUSHAV_README.md / JOHN_README.md). Log every file I changed this session 
 with today's date and a short description. Update the status checklist. If I changed any 
 shared files, flag it clearly in the changelog entry."
```

Claude Code will:
- Add dated changelog entries for everything that changed
- Update the status checklist (check off completed items, add new in-progress items)
- Flag shared file changes with a ⚠️ marker so the other dev sees it immediately
- You review the update, then push

### The full cycle
```
git pull                          # Get the other dev's latest changes
claude                            # Start Claude Code
"Read all files, I am Rushav"     # Claude reads context + flags changes
... work on your stuff ...        # Claude builds/fixes things
"Update my README"                # Claude logs what changed
git add . && git commit && git push   # Push everything including updated README
```

### Rules
- NEVER manually edit the other person's README
- ALWAYS start a session by reading both READMEs
- ALWAYS end a session by updating your own README
- If you change a shared file, Claude Code will mark it with ⚠️ in your changelog
- If the other dev's changelog has a ⚠️ entry you haven't seen, resolve it before writing new code

### Shared files (both devs edit — always coordinate)
```
backend/main.py               # Route registration
backend/database.py            # SQLAlchemy engine + session
backend/models.py              # DB models — schema changes affect everything
backend/agents/prompts.py      # All LLM prompts
frontend/src/App.jsx           # Route definitions
frontend/src/api.js            # API endpoint functions
```

---

## Core architecture principle
Thoth is the ORCHESTRATOR. It NEVER answers user questions directly. Subject-specific LLM agents (same base model, scoped RAG context) handle all user-facing answers. This prevents cross-contamination between knowledge domains.

## Tech stack
- Backend: Python 3.11+, FastAPI, uvicorn
- Frontend: React (Vite), Tailwind CSS — barebones functional UI only
- Database: SQLite via SQLAlchemy (structured data)
- Vector store: ChromaDB (RAG retrieval, one collection per subject)
- LLM: Anthropic Claude API via `anthropic` Python SDK, model `claude-sonnet-4-20250514`
- File parsing: PyPDF2, python-docx for uploaded files
- Embeddings: ChromaDB default (all-MiniLM-L6-v2)

## Project structure
```
project-thoth/
├── CLAUDE.md                   # This file — project brain, read every session
├── PROMPTS.md                  # All LLM prompts reference
├── RUSHAV_README.md            # Rushav's changelog + status + ownership
├── JOHN_README.md              # John's changelog + status + ownership
├── .env                        # ANTHROPIC_API_KEY (never commit this)
├── .gitignore
├── backend/
│   ├── main.py                 # FastAPI app, CORS, startup (SHARED)
│   ├── config.py               # env vars, API keys
│   ├── database.py             # SQLAlchemy setup (SHARED)
│   ├── models.py               # DB models (SHARED)
│   ├── vector_store.py         # ChromaDB setup [JOHN]
│   ├── seed.py                 # Demo data seeding [JOHN]
│   ├── agents/
│   │   ├── thoth.py            # Orchestrator: classifier + router [RUSHAV]
│   │   ├── interviewer.py      # SME interviews [JOHN]
│   │   ├── sme_agent.py        # Subject-specific agents [RUSHAV]
│   │   └── prompts.py          # All system prompts (SHARED)
│   ├── routes/
│   │   ├── profiles.py         # Profile CRUD [RUSHAV]
│   │   ├── interviews.py       # Interview flow [JOHN]
│   │   ├── review.py           # SME review/approve/reject [JOHN]
│   │   ├── query.py            # User query → route → answer [RUSHAV]
│   │   ├── admin.py            # Admin tools [RUSHAV]
│   │   ├── subjects.py         # Subject CRUD [JOHN]
│   │   └── files.py            # File upload + parse [JOHN]
│   ├── services/
│   │   ├── knowledge.py        # Knowledge entry CRUD [JOHN]
│   │   ├── file_parser.py      # Text extraction [JOHN]
│   │   └── classifier.py       # Question classifier [RUSHAV]
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx             # Router (SHARED)
│   │   ├── api.js              # Fetch wrapper (SHARED)
│   │   ├── pages/
│   │   │   ├── LandingPage.jsx     # Four-window launcher [RUSHAV]
│   │   │   ├── UserChatPage.jsx    # User questions + file attach [RUSHAV]
│   │   │   ├── SMEDashboardPage.jsx # Interview + reviews [JOHN]
│   │   │   └── AdminPage.jsx       # Approvals + escalations [RUSHAV]
│   │   └── components/
│   │       ├── ChatWindow.jsx      # Reusable chat [RUSHAV]
│   │       ├── MessageBubble.jsx   # Message + markdown [RUSHAV]
│   │       ├── ReviewPanel.jsx     # Approve/reject UI [JOHN]
│   │       ├── FileUpload.jsx      # File attachment [JOHN]
│   │       ├── InterviewChat.jsx   # Interview chat [JOHN]
│   │       └── SubjectBadge.jsx    # Agent indicator [RUSHAV]
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── data/
│   ├── chroma/                 # ChromaDB persistent storage
│   └── uploads/                # User-uploaded files
└── README.md
```

## File ownership key
- `[RUSHAV]` — Rushav owns this file
- `[JOHN]` — John owns this file  
- `(SHARED)` — Both edit, always coordinate via changelogs

## Database schema (SQLite)
```sql
profiles (id, name, role [user|sme|admin], expertise_area, contact_info, created_at)
subjects (id, name, description, created_at)
sme_subjects (profile_id FK, subject_id FK, expertise TEXT)
knowledge_entries (id, subject_id FK, contributor_id FK, title, content,
                   status [draft|pending_review|pending_admin_review|approved|rejected],
                   approved_by, approved_at, review_date, review_requested BOOL,
                   created_at)
files (id, entry_id FK, filename, filepath, file_type, extracted_text, created_at)
interviews (id, sme_id FK, subject_id FK, messages JSON,
            synthesis TEXT, synthesis_status [draft|pending_review|approved|rejected],
            created_at)
escalations (id, user_query, user_id FK, reason, classifier_details JSON,
             status [open|assigned|resolved], assigned_to FK,
             resolution TEXT, resolved_at, created_at)
```

## Approval flow
1. SME approves synthesis → status = "pending_admin_review"
2. Entry appears in admin approval queue
3. Admin approves → status = "approved", content added to ChromaDB
4. Admin rejects → status = "rejected", SME notified

## Demo data (seeded by seed.py)
- Subjects: Coffee, Milk Tea, Cars
- SMEs: Lisa Li — Coffee (Brewing Methods), Mengting Li — Milk Tea (Boba & Tea Bases), Rushav — Cars (Maintenance & Buying)
- Users: Alex Rivera, Jordan Lee
- Admin: Pat Morgan
- 2 approved knowledge entries per subject pre-loaded into ChromaDB
- Live demo: John Huang added as new SME for "Climbing"

## Integration contract (NEVER change without telling the other dev)
```python
# Knowledge entry statuses
STATUSES = ["draft", "pending_review", "pending_admin_review", "approved", "rejected"]

# ChromaDB collection naming
COLLECTION_NAME = f"subject_{subject_id}"

# ChromaDB document format
{
    "documents": [entry.content],
    "metadatas": [{"entry_id": entry.id, "subject_id": entry.subject_id, "title": entry.title}],
    "ids": [f"entry_{entry.id}"]
}

# Profile response format
{"id": int, "name": str, "role": str, "expertise_area": str|None, "contact_info": str|None}
```

## Key behaviors
- NEVER let Thoth answer user questions directly. It classifies and routes only.
- NEVER expose raw interview transcripts to users. Only approved summaries.
- NOTHING enters the active knowledge base without BOTH SME approval AND admin approval.
- Each ChromaDB collection is named `subject_{subject_id}` and only queried by its own agent.
- Confidence >= 0.7 → route to agent. 0.4-0.7 → clarifying question. < 0.4 → escalate.
- SMEs only see their own subjects for interviews.
- Synthesis MUST only contain information the SME explicitly stated.
- Interview conversation history must persist — never clear it.
- Render all LLM responses as markdown in the frontend (react-markdown).
- Escalations store classifier details for admin context. Resolved ones go to archive.

## How LLM agents work
Same base model, scoped system prompt + scoped RAG retrieval per subject. NOT separate models. Classifier prompt determines routing. See PROMPTS.md for all prompt text.

## API endpoints
```
POST   /api/profiles              # Create profile [RUSHAV]
GET    /api/profiles?role=sme     # List by role [RUSHAV]

POST   /api/interviews/start      # Start interview [JOHN]
POST   /api/interviews/{id}/message  # Interview message [JOHN]
POST   /api/interviews/{id}/synthesize  # Generate synthesis [JOHN]
POST   /api/interviews/{id}/review     # SME review [JOHN]

POST   /api/query                 # User question [RUSHAV]
POST   /api/query/with-file       # User question + file [RUSHAV]
GET    /api/query/history         # Past questions [RUSHAV]

GET    /api/admin/pending         # Approval queue [RUSHAV]
POST   /api/admin/approve/{id}    # Approve entry [RUSHAV]
GET    /api/admin/escalations     # Escalation inbox [RUSHAV]
GET    /api/admin/directory       # SME directory [RUSHAV]
POST   /api/admin/request-review/{sme_id}  # Trigger review [RUSHAV]

POST   /api/files/upload          # Upload file [JOHN]
GET    /api/subjects              # List subjects [JOHN]
POST   /api/subjects              # Create subject [JOHN]
```

## Code style
- Python: type hints, async where possible, Pydantic models for request/response
- React: functional components, hooks, useState/useContext only
- No class components, no Redux, no axios
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

# Reset everything
rm data/thoth.db && rm -rf data/chroma/ && cd backend && python seed.py
```

## Frontend architecture
- Four separate windows via routes: /user, /sme, /admin, /support
- Landing page at / opens each in a new browser tab
- Each window has a colored header + profile selector dropdown for its role
- Polling every 5 seconds for admin and SME windows to see cross-window updates
- No WebSockets, no login/logout — role is determined by the route

## What NOT to build
- No real authentication
- No WebSocket real-time chat
- No production deployment
- No CI/CD
- No mobile responsiveness
