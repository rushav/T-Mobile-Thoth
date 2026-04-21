# Project Thoth — Claude Code Setup Guide

## What you need before starting

### 1. Install Claude Code
```bash
npm install -g @anthropic-ai/claude-code
```
Requires Node.js 18+. Run `claude` in your terminal to start.

### 2. Get an Anthropic API key
Go to https://console.anthropic.com → API Keys → Create key.
You'll need this for both Claude Code AND for Thoth's backend (the LLM calls).

### 3. Install Python 3.11+
Check with `python --version`. Install from python.org if needed.

### 4. Install Node.js 18+
Check with `node --version`. Install from nodejs.org if needed.

---

## Project setup

### Step 1: Create the project folder
```bash
mkdir project-thoth
cd project-thoth
```

### Step 2: Drop in the CLAUDE.md
Copy the provided `CLAUDE.md` file into this folder. This is what Claude Code reads every time you start a session — it's the project brain.

### Step 3: Drop in the PROMPTS.md
Copy `PROMPTS.md` into the same folder. Claude Code will reference this for all the LLM prompts.

### Step 4: Create .env
```bash
echo "ANTHROPIC_API_KEY=sk-ant-your-key-here" > .env
```

### Step 5: Start Claude Code
```bash
claude
```

---

## The prompt to give Claude Code

Copy and paste this entire prompt to kick off the build. Claude Code will read CLAUDE.md automatically and use it as context.

---

```
Build the Project Thoth PoC according to CLAUDE.md. Start with the backend, then the frontend.

## Phase 1: Backend skeleton
1. Create the project structure from CLAUDE.md
2. Set up SQLAlchemy with SQLite — create all tables from the schema in CLAUDE.md
3. Set up ChromaDB with persistent storage in data/chroma/
4. Create the FastAPI app with CORS (allow localhost:5173)
5. Implement the profiles routes (create, list, login — no real auth, just store current profile in memory or simple session)
6. Create a seed script that pre-loads 3 demo subjects: "HR Policies", "IT Support", "Finance & Expenses" — and creates 3 SME profiles, one for each

## Phase 2: Interview flow
1. Build the interviewer agent using the INTERVIEWER_PROMPT from PROMPTS.md
2. Implement /api/interviews/start — creates a new session, stores sme_id and subject_id
3. Implement /api/interviews/{id}/message — sends user message to Claude with the interviewer prompt + conversation history, returns Claude's response, appends both to the messages JSON
4. Implement /api/interviews/{id}/synthesize — takes the full conversation + any uploaded file text, sends to Claude with SYNTHESIS_PROMPT, stores the synthesis
5. Implement /api/interviews/{id}/review — SME can approve (status → approved, content added to ChromaDB collection for that subject), reject (status → rejected), or request changes (status → draft, Thoth revises)
6. Implement file upload: accept PDF/docx/txt, extract text using PyPDF2/python-docx, store file metadata and extracted text

## Phase 3: Query flow (the core demo)
1. Build the classifier using CLASSIFIER_PROMPT from PROMPTS.md
2. Build the SME agent using SME_AGENT_PROMPT — it takes the user question, retrieves top 5 relevant chunks from that subject's ChromaDB collection, and answers
3. Implement /api/query:
   - Receive user question
   - Call classifier to determine subject + confidence
   - If confidence >= 0.7: route to that subject's SME agent, return answer with subject label
   - If confidence 0.5-0.7: return a clarifying question (use CLARIFICATION_PROMPT)
   - If confidence < 0.5 or subject is null: create an escalation record, return "I'll connect you with an administrator"
4. Implement /api/query/history — return past Q&As for the current user

## Phase 4: Admin routes
1. GET /api/admin/pending — return all knowledge entries with status "pending"
2. POST /api/admin/approve/{id} — set status to "approved", add content to ChromaDB
3. GET /api/admin/escalations — return all open escalations
4. GET /api/admin/directory — return all SMEs grouped by subject

## Phase 5: Frontend (barebones)
Build a minimal but functional React frontend. No fancy styling — just clean, working pages.

1. LoginPage: three buttons (User, SME, Admin). Clicking one shows a list of profiles for that role. Click a name to "log in." Button to create a new profile.

2. UserChatPage: simple chat interface. Text input at bottom, messages above. When user sends a message, call /api/query. Show the response with a small badge indicating which subject agent answered. If escalated, show "Connecting to admin..." message. If clarifying, show Thoth's clarifying question.

3. SMEDashboardPage: two tabs or sections:
   - "Interview": start a new interview session. Chat interface with Thoth. Button to upload files. When interview is done, button to "Generate Summary." Shows the synthesis with Approve/Request Changes buttons.
   - "Pending Reviews": list of entries awaiting this SME's review.

4. AdminPage: two sections:
   - "Approval Queue": list of pending entries with Approve/Reject buttons and a preview of the content.
   - "Escalations": list of escalated user questions with the original query and a text field for admin to respond.
   - "SME Directory": simple list of SMEs grouped by subject.

Use React Router for navigation. Use Tailwind for basic styling. Every page should have a header showing current role/name and a logout button that returns to LoginPage.

## Phase 6: Demo data
Create a script that seeds the database with realistic demo data:
1. Three subjects: HR Policies, IT Support, Finance & Expenses
2. Three SME profiles (one per subject): "Karen Chen" (HR), "Mike Torres" (IT), "Sarah Kim" (Finance)
3. Two approved knowledge entries per subject with realistic content (e.g., HR: "How to request PTO", "Benefits enrollment process"; IT: "VPN setup guide", "Password reset process"; Finance: "Expense report submission", "Travel reimbursement policy")
4. Add the knowledge entry content to the appropriate ChromaDB collections
5. Two user profiles: "Alex Rivera", "Jordan Lee"
6. One admin profile: "Pat Morgan"

After seeding, the demo should work end-to-end: log in as Alex, ask "How do I submit an expense report?" and get an answer from the Finance agent.
```

---

## How to use Claude Code effectively for this project

### Work in phases
Don't paste the entire prompt at once if Claude Code struggles. Break it into phases:
- Start with "Build Phase 1 from the prompt" 
- Test it works
- Then "Build Phase 2"
- And so on

### Key commands in Claude Code
- `/init` — generates initial CLAUDE.md (skip this, you already have one)
- `/clear` — clears context when things get confused
- Type your request naturally — "add a new endpoint for..." or "fix the error in..."
- If Claude Code makes a mistake, say "undo that" or "revert the last change"

### When something breaks
1. Copy the error message
2. Paste it to Claude Code: "I'm getting this error: [error]. Fix it."
3. Claude Code will read the relevant files and fix the issue

### Testing as you go
After each phase:
```bash
# Test backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

# In another terminal, test an endpoint
curl http://localhost:8000/api/subjects
```

---

## Recommended tools and extensions

### VS Code extensions
- **Python** (Microsoft) — Python language support
- **Pylance** — Python type checking
- **SQLite Viewer** — view your database without external tools
- **ES7+ React** — React snippets
- **Tailwind CSS IntelliSense** — autocomplete for Tailwind classes
- **REST Client** — test API endpoints from VS Code (alternative to curl/Postman)

### Python packages (in requirements.txt)
```
fastapi==0.115.0
uvicorn==0.32.0
sqlalchemy==2.0.36
anthropic==0.42.0
chromadb==0.5.23
python-multipart==0.0.12
python-dotenv==1.0.1
PyPDF2==3.0.1
python-docx==1.1.2
pydantic==2.10.0
```

### NPM packages (in package.json)
```
react
react-dom
react-router-dom
tailwindcss
@tailwindcss/vite
```

### Useful GitHub repos for reference
- **ChromaDB docs**: https://docs.trychroma.com — vector DB setup and querying
- **FastAPI docs**: https://fastapi.tiangolo.com — API framework
- **Anthropic Python SDK**: https://github.com/anthropics/anthropic-sdk-python — Claude API calls
- **Zlash65/rag-bot-fastapi**: https://github.com/Zlash65/rag-bot-fastapi — reference architecture for FastAPI + ChromaDB RAG chatbot (similar stack to yours)

### Things you do NOT need
- LangChain — adds unnecessary complexity for this PoC. Direct Claude API calls are simpler and more debuggable.
- Docker — run everything locally for the demo
- PostgreSQL — SQLite is zero-config and perfect for a PoC
- Redis — no caching layer needed
- Celery / background workers — everything can be synchronous for the demo

---

## Work split suggestion (John + Rushav)

### John: "Write path" (SME side)
- Backend Phases 1-2 (database, interviews, file upload, synthesis)
- Frontend: SME dashboard page
- Demo data seeding script

### Rushav: "Read path" (User + Admin side)  
- Backend Phases 3-4 (query routing, classifier, admin routes)
- Frontend: Login page, User chat page, Admin page
- Demo script and rehearsal

### Both together:
- First 2 days: align on schema, set up project, get skeleton running
- Integration testing mid-week
- Final dry run together

---

## Demo script (what to show judges)

Walk through this exact sequence on May 4th:

1. **Log in as SME "Karen Chen"** → show the SME dashboard
2. **Start an interview about a new topic** (e.g., "Parental Leave Policy") → have Thoth ask questions, answer 4-5 of them
3. **Upload a supporting document** → show file attachment
4. **Generate summary** → show the synthesis Thoth created
5. **Approve the summary** → show it entering the knowledge base
6. **Switch to Admin "Pat Morgan"** → show the approval queue, approve the entry
7. **Switch to User "Alex Rivera"** → ask "What is the parental leave policy?" → get answer from HR agent with attribution
8. **Ask a question the system can't answer** → show the escalation to admin
9. **Ask an ambiguous question** (something that could be HR or Finance) → show Thoth's clarifying question
10. **Show the architecture diagram** → explain the subject-isolated agent design

Total demo time: ~10 minutes. Practice at least twice.
