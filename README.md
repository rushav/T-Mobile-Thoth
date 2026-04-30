# Project Thoth

AI-powered SME knowledge capture and retrieval system for the GIX/T-Mobile hackathon. Demo deadline: May 4, 2026.

Thoth is the orchestrator — it classifies questions and routes them to subject-scoped LLM agents. Each agent answers only from its own approved knowledge, so domains never cross-contaminate.

See [CLAUDE.md](CLAUDE.md) for the architecture spec and [PROMPTS.md](PROMPTS.md) for every LLM prompt used.

---

## Prerequisites

- **Python 3.11+** (`python3 --version`)
- **Node.js 18+** (`node --version`)
- **An Anthropic API key** — get one at <https://console.anthropic.com>. It must start with `sk-ant-`. OpenRouter keys (`sk-or-…`) won't work; the backend uses the official `anthropic` SDK.
- SSH access to this repo (or swap `origin` to HTTPS — see git section).

## First-time setup

From the repo root (`Thoth/`):

```bash
# 1. Create your local .env
cp .env.example .env
# then edit .env and paste your ANTHROPIC_API_KEY

# 2. Backend — create venv + install deps + seed demo data
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r backend/requirements.txt
cd backend && python3 seed.py && cd ..

# 3. Frontend — install deps
cd frontend && npm install && cd ..
```

The `data/` directory (SQLite DB + ChromaDB persistent storage + uploads) is auto-created on first run and is gitignored. Each teammate has their own local copy.

## Running the app

Two terminals:

```bash
# Terminal 1 — backend (http://localhost:8000)
source .venv/bin/activate
cd backend && python3 -m uvicorn main:app --reload --port 8000
```

```bash
# Terminal 2 — frontend (http://localhost:5173)
cd frontend && npm run dev
```

Open <http://localhost:5173>. The Vite dev server proxies `/api` to the backend, so both have to be running.

### Demo login profiles (already seeded)

- **Users**: Alex Rivera, Jordan Lee
- **SMEs**: Lisa Li (Coffee), Mengting Li (Milk Tea), Rushav (Cars)
- **Admin**: Pat Morgan

### Resetting local data

If your DB gets into a weird state or the schema changed:

```bash
rm -f data/thoth.db
rm -rf data/chroma
cd backend && python3 seed.py
```

---

## Who owns what

### Lisa (Coffee SME / Designer) & Ting (Milk Tea SME / Designer)

You're driving the Figma design for the demo-ready UI polish. The current React app is intentionally barebones — clean structure, Tailwind utility classes, minimal styling — so it's easy to restyle without touching logic. When you're ready to hand off designs, Rushav and John will wire them into the existing components (`ChatWindow`, `MessageBubble`, `ReviewPanel`, pages).

During the demo, you'll also act as live SMEs: Lisa answers coffee questions through Thoth's interview flow, Ting does milk tea. Please do a practice interview in the SME dashboard before demo day so Thoth's questions feel natural to you.

### Rushav & John — dev split

To stay out of each other's way, own these areas. **Anything not on your list, coordinate before touching.**

**Rushav — the "Read" path (user + admin side):**
- `backend/agents/thoth.py` (orchestrator/router)
- `backend/agents/sme_agent.py` (RAG + answer generation)
- `backend/services/classifier.py`
- `backend/routes/query.py`, `backend/routes/admin.py`
- `frontend/src/pages/LoginPage.jsx`
- `frontend/src/pages/UserChatPage.jsx`
- `frontend/src/pages/AdminPage.jsx`
- Demo script + rehearsal
- Prompt tuning: `CLASSIFIER_PROMPT`, `SME_AGENT_PROMPT`, `CLARIFICATION_PROMPT`

**John — the "Write" path (SME side):**
- `backend/agents/interviewer.py` (interview + synthesis)
- `backend/routes/interviews.py`, `backend/routes/review.py`, `backend/routes/files.py`
- `backend/services/file_parser.py`, `backend/services/knowledge.py`
- `frontend/src/pages/SMEDashboardPage.jsx`
- `frontend/src/components/ReviewPanel.jsx`
- `backend/seed.py` (extend demo content)
- Prompt tuning: `INTERVIEWER_PROMPT`, `SYNTHESIS_PROMPT`

**Shared — coordinate on Slack/DM before editing:**
- `backend/models.py` (schema changes force everyone to re-seed)
- `backend/main.py` (route registration)
- `backend/requirements.txt` / `frontend/package.json`
- `frontend/src/App.jsx` (router)
- `frontend/src/api.js` (shared fetch wrapper)
- `frontend/src/components/ChatWindow.jsx`, `MessageBubble.jsx`, `SubjectBadge.jsx`
- `backend/agents/prompts.py` — we both edit this. Only touch **your** prompt constants; if you rearrange the file, tell the other person first.
- `CLAUDE.md`, `README.md`

---

## Git rules — please follow these so we don't clobber each other

### Branches

Never push directly to `main`. Create a feature branch per task:

```bash
git checkout main
git pull                                       # always start from latest main
git checkout -b yourname/short-description     # e.g. rushav/classifier-threshold
```

Good branch names: `rushav/admin-escalation-ui`, `john/interview-file-upload`, `rushav/demo-prompts`.

### Daily workflow

```bash
git pull --rebase origin main     # pull latest before you start (avoids merge commits)
# ... do work, commit often ...
git add <specific files>          # prefer this over `git add .`
git commit -m "short, imperative message — what and why"
git push -u origin yourname/feature
```

Then open a pull request on GitHub into `main`. The other dev reviews + merges. Delete the branch after merge.

### Do not

- **Do not** `git push --force` to `main`. Ever.
- **Do not** commit `.env`, `data/`, `.venv/`, `node_modules/`, `data/thoth.db`, or anything inside `data/chroma/`. The `.gitignore` covers them, but always check `git status` before you commit. If you see any of these staged, unstage them.
- **Do not** `git add .` or `git add -A` without reading `git status` first — one stray file in the wrong place and we're in trouble.
- **Do not** merge your own PR without a second pair of eyes, except for tiny doc-only fixes.
- **Do not** rewrite history on a pushed branch (`git rebase -i`, `commit --amend`) after someone else has pulled it.

### If something goes wrong

- **Merge conflict on pull**: resolve locally, test, then `git rebase --continue` or `git commit`. Don't panic; don't force anything.
- **Committed a secret by accident**: stop, tell the other dev immediately, and rotate the key. Rewriting history on a shared repo is messy; the faster path is usually to rotate the leaked credential.
- **Broken main**: revert the offending commit with `git revert <sha>` and push the revert through a PR. Don't force-push a fix.

### Switching `origin` to HTTPS (optional)

If SSH auth is annoying:

```bash
git remote set-url origin https://github.com/rushav/T-Mobile-Thoth.git
```

You'll need a GitHub personal access token as your password on first push.

---

## Testing as you go

Manual testing is fine for this PoC — no unit-test suite. After any backend change, hit a relevant endpoint:

```bash
# examples
curl http://localhost:8000/api/subjects
curl http://localhost:8000/api/admin/pending
curl -X POST http://localhost:8000/api/query \
  -H 'Content-Type: application/json' -H 'X-Profile-Id: 4' \
  -d '{"question":"How do I make pour-over coffee?"}'
```

The full demo flow (see [SETUP_GUIDE.md](SETUP_GUIDE.md) for the judges-day script):

1. Log in as an SME → run an interview → generate summary → approve.
2. Log in as admin (Pat Morgan) → approve the entry from the queue.
3. Log in as a user (Alex Rivera) → ask a question → see the right subject agent answer it.
4. Ask a question no subject matches → see it escalate to admin.
5. Ask an ambiguous question → see Thoth's clarifying question.
