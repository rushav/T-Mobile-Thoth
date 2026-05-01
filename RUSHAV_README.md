# RUSHAV_README.md

## ⚙️ For Claude Code — README management instructions

When Rushav says "update my README" at the end of a session, do the following:
1. List every file that was created or modified during this session
2. Add a changelog entry for today using this exact format:
   ```
   [YYYY-MM-DD] [file1.py, file2.jsx] — Short description of what changed and why
   ```
3. If ANY shared file was modified (main.py, database.py, models.py, prompts.py, App.jsx, api.js), prefix the entry with ⚠️:
   ```
   ⚠️ [YYYY-MM-DD] [backend/models.py, backend/main.py] — Added new field X to profiles table. John: update your seed.py and any code that reads profiles.
   ```
4. Update the status checklist: check off anything that's now working, add new items to "In progress" or "Blocked"
5. If something was added to "Blocked / waiting on John", be specific about what's needed

When Rushav starts a session and asks to read both READMEs, do the following:
1. Read JOHN_README.md changelog
2. Find any entries dated after Rushav's last changelog entry
3. Report: "John made X changes since your last session: [summary]. [N] affect shared files: [details]."
4. If John has ⚠️ entries Rushav hasn't seen, flag them clearly

---

## My ownership area: User side + Admin side + Orchestration

I own the "read path" — everything that happens after knowledge is in the database. Plus the orchestrator (Thoth) that ties it all together, and the admin tools.

---

## Files I own (don't edit these without telling me)

### Backend
```
backend/
├── agents/
│   ├── thoth.py              # Orchestrator: classifier + router
│   ├── sme_agent.py          # Subject-specific agents (scoped RAG answers)
│   └── prompts.py            # ALL prompts (shared file — coordinate with John)
├── routes/
│   ├── query.py              # User asks question → classify → route → answer
│   ├── admin.py              # Approval queue, escalations, SME directory, review triggers
│   └── profiles.py           # Profile CRUD, listing by role
├── services/
│   └── classifier.py         # Classify question → subject + confidence
├── main.py                   # FastAPI app setup, CORS, startup (shared — coordinate)
├── config.py                 # Env vars, API key loading
└── database.py               # SQLAlchemy setup (shared — coordinate with John on schema)
```

### Frontend
```
frontend/src/
├── App.jsx                   # Router + landing page (shared — coordinate)
├── api.js                    # Fetch wrapper (shared — coordinate)
├── pages/
│   ├── UserChatPage.jsx      # User question interface + file attachments
│   ├── AdminPage.jsx         # Approval queue, escalations, directory, review triggers
│   └── LandingPage.jsx       # Four-window launcher
└── components/
    ├── ChatWindow.jsx        # Reusable chat component
    ├── MessageBubble.jsx     # Single message with markdown rendering + agent badge
    └── SubjectBadge.jsx      # Shows which agent is active
```

### Shared files (both of us edit — always coordinate)
```
backend/main.py               # We both add routes here
backend/database.py            # Schema changes affect both of us
backend/models.py              # DB model changes affect both of us
backend/agents/prompts.py      # All prompts live here — tell each other before editing
frontend/src/App.jsx           # Route definitions
frontend/src/api.js            # API endpoint functions
```

---

## Current status

### Working
- [ ] Classifier routes questions to correct subject agent
- [ ] Confidence thresholds: >=0.7 route, 0.4-0.7 clarify, <0.4 escalate
- [ ] SME agents answer from scoped ChromaDB collections only
- [ ] User chat page with markdown rendering
- [ ] User file attachments (PDF/docx/txt)
- [ ] Admin approval queue (receives entries after SME approves)
- [ ] Admin escalation inbox with detail view + archive
- [ ] Admin SME directory with contact info + expertise
- [ ] Admin review trigger button
- [x] Landing page with four-window launcher (now also has "Relaunch All Windows" button + launch.sh tip)
- [ ] Profile selector dropdown per window
- [ ] Polling for real-time updates (admin + SME windows)
- [x] Hallucination-proof seed data (Zorblatt / Flumgarten / Reverse Plumbing)
- [x] Single-command launcher (launch.sh + launch.bat) with 2x2 grid
- [x] Linux compatibility for launch.sh — prereq checks + python3/pip3/`python3 -m uvicorn`
- [x] TEST_QUERIES.md — 10 hallucination test queries version-controlled
- [x] launch.sh uses a venv (Ubuntu 24 / PEP 668 fix)
- [x] launch.sh Linux 2x2 grid via wmctrl + per-page document.title

### In progress
- Run the 10 hallucination test queries from TEST_QUERIES.md end-to-end after launching to verify the SME agents only answer from the fictional KB
- Live-test the follow-up routing: ask a normal question, then say "make that shorter" and confirm the SME agent rephrases (status="answered", `follow_up: true`) instead of escalating

### Blocked / waiting on John
- John: after pulling, verify that the interview flow works with the new fictional subjects. Run an interview as Dr. Helga Voss about Zorblatt Crystals. Say something minimal like "the crystals glow on day 10." The synthesis should ONLY mention the glow — it should NOT fill in details about 37.2°C or lunar sand from the existing knowledge entries. If it does, the synthesis prompt needs to be stricter about separating existing KB content from new interview content.

---

## Changelog

Claude Code manages this section. Rushav says "update my README" and Claude fills this in.
Never edit this manually.

```
Format:
[YYYY-MM-DD] [files] — What changed and why
⚠️ [YYYY-MM-DD] [shared files] — What changed + message to John about what to watch for
```

### Log

[2026-04-28] [initial setup] — Project created. All files listed above are my responsibility.

⚠️ [2026-04-29] [backend/seed.py, launch.sh, launch.bat, frontend/src/pages/LandingPage.jsx] — MAJOR CHANGE: Replaced all seed data with hallucination-proof fictional content (Zorblatt Crystals, Flumgarten Diplomacy, Reverse Plumbing). Old coffee/milk tea/car data is gone. Added launch.sh and launch.bat for single-command startup with 4-way split screen. John: you need to pull and re-seed. Your SMEDashboardPage and interview flow should work the same — only the test content changed. Run the 10 hallucination test queries in TEST_QUERIES.md to verify your interview synthesis also only uses SME-provided info and doesn't fabricate.

⚠️ [2026-04-29] [TEST_QUERIES.md, launch.sh, README.md, CLAUDE.md, SETUP_GUIDE.md, backend/seed.py] — Added TEST_QUERIES.md with the 10 hallucination test queries + expected answers (version-controlled now, anyone can run them). Linux compat pass on launch.sh: added prereq checks for python3/pip3/node/npm at the top, switched all calls to python3 / pip3 / `python3 -m uvicorn`. Same swap applied to command examples in README.md, CLAUDE.md, SETUP_GUIDE.md, and the seed.py docstring. launch.bat untouched (Windows uses `python`). John: if your local machine has both `python` and `python3`, both still work — but the docs and scripts now consistently call `python3` so they don't break on systems (like this Linux env) where bare `python` isn't installed.

[2026-04-29] [launch.sh] — Removed `2>/dev/null` from the `pip3 install` line so install errors actually surface (kept `-q` for quiet success output). Order was already correct: cd backend → pip3 install → seed-if-needed → uvicorn. No reorder was needed despite my read of the request — verified the file before editing.

⚠️ [2026-04-29] [launch.sh, CLAUDE.md] — Switched launch.sh to use a Python venv at project root (`.venv/`). Required on Ubuntu 24+ since PEP 668 blocks system-wide pip installs. launch.sh now creates `.venv` if missing, activates it, then runs `pip install` / `python seed.py` / `python -m uvicorn` inside the venv (plain `python`/`pip` because the venv maps them correctly). Updated CLAUDE.md Commands section to document `python3 -m venv .venv` + `source .venv/bin/activate` for first-time setup. `.venv/` was already in `.gitignore`. John: after pulling, your first `./launch.sh` will create the venv and install deps fresh — takes a minute. If you previously installed deps system-wide, the old install is unused now but harmless.

⚠️ [2026-04-29] [launch.sh, frontend/src/pages/UserChatPage.jsx, frontend/src/pages/SMEDashboardPage.jsx, frontend/src/pages/AdminPage.jsx, frontend/src/pages/SupportPage.jsx] — Fixed Linux 2x2 grid arrangement. Chrome's `--window-position` is ignored on most Linux WMs, so launch.sh now opens windows plain and arranges them with `wmctrl` after the fact, matching by `document.title`. Each page sets its own title via `useEffect` ("Thoth — User" / "SME" / "Admin" / "Support"). Also added Linux-only wmctrl prereq check at the top, browser detection (google-chrome → chromium-browser → chromium → firefox), and screen-size detection via `xdpyinfo` with a 1920x1080 fallback. macOS/Windows branches unchanged. **John: SMEDashboardPage.jsx is yours, but I added a 2-line `useEffect` setting `document.title` at the top of the component — purely cosmetic, no logic touched. If you'd rather move it elsewhere or set the title differently, go ahead, just keep the literal string `Thoth — SME` (em dash, not hyphen) so launch.sh can still find it.** New runtime dep on Linux: `wmctrl` (sudo apt install wmctrl). Optional: `x11-utils` for `xdpyinfo` — without it the script falls back to 1920x1080.

⚠️ [2026-04-30] [backend/agents/thoth.py, backend/agents/sme_agent.py, backend/agents/prompts.py] — Fixed follow-up handling in the query flow. Previously a message like "say that more concisely" got re-classified, scored < 0.4 confidence, and was escalated. Now `thoth.handle_query` looks up the user's most recent answered query (within 30 minutes) via `_last_answered_query`; if the classifier would otherwise escalate AND a recent answer exists, we route to the same subject and pass the prior Q&A into the SME agent as conversation history (new `prior_exchange` arg on `sme_agent.answer`). Retrieval on a follow-up uses the prior question, not the bare "shorter please" message, so RAG still pulls relevant chunks. Response includes `follow_up: true`. High-confidence and clarification paths are unchanged. Also added a 6th rule to `SME_AGENT_PROMPT` for conciseness (3-5 sentences, no question-restating, no unnecessary caveats) — this addresses verbose answers in general, not just follow-ups. **John: I edited the shared `prompts.py` but only added a new rule to `SME_AGENT_PROMPT`; the interviewer/synthesis/revision prompts you own are untouched. The new conciseness rule will affect tone of all SME-agent answers — if it conflicts with anything in your synthesis style, ping me.** New `follow_up` field on the query response is additive — UserChatPage doesn't need to handle it for the bug fix to work, but you can surface it later if you want a "follow-up" badge.

---

## Integration points with John

These are the places where my code depends on John's code or vice versa. When either of us changes something here, we need to tell the other.

### I depend on John for:
1. **Knowledge entries in the DB** — My query route reads approved entries. If John changes the `knowledge_entries` schema or the approval flow, my queries might break.
2. **ChromaDB collections** — John's interview/approval flow writes to ChromaDB. My agents read from it. We need to agree on: collection naming (`subject_{id}`), document format, and metadata fields.
3. **Interview synthesis format** — My SME agents parse the synthesis content for RAG. If John changes the synthesis structure, my retrieval quality changes.
4. **Subject creation** — When John's interview flow creates a new subject, my classifier needs to pick it up. Make sure new subjects are committed to the DB before the interview starts.

### John depends on me for:
1. **Profile routes** — John's interview flow uses `/api/profiles` to know which SME is logged in. If I change profile endpoints, his frontend breaks.
2. **Subject listing** — John's SME dashboard calls `/api/subjects` to show available subjects. I own this endpoint.
3. **Admin approval** — John's entries go to "pending_admin_review" status. I pick them up in the admin queue. We need the status values to match exactly.
4. **Prompts file** — We share `prompts.py`. Don't edit without telling me, I won't edit without telling you.

### Our contract (don't break these):
```python
# Knowledge entry statuses — both of us depend on these exact strings
STATUSES = ["draft", "pending_review", "pending_admin_review", "approved", "rejected"]

# ChromaDB collection naming
COLLECTION_NAME = f"subject_{subject_id}"

# ChromaDB document format when adding entries
{
    "documents": [entry.content],
    "metadatas": [{"entry_id": entry.id, "subject_id": entry.subject_id, "title": entry.title}],
    "ids": [f"entry_{entry.id}"]
}

# Profile response format
{
    "id": int,
    "name": str,
    "role": str,  # "user" | "sme" | "admin"
    "expertise_area": str | None,
    "contact_info": str | None
}
```

---

## Notes for future me

- When testing the classifier, use these exact queries (full set in TEST_QUERIES.md):
  - Clear match: "How do I grow Zorblatt Crystals?" → Zorblatt Crystals, ~0.9
  - Ambiguous: "What should I do about the gurgling sound?" → clarification question (could be Reverse Plumbing or out-of-scope)
  - No match: "How do I cook pasta?" → escalation
- If classifier confidence seems off, the issue is usually in the CLASSIFIER_PROMPT, not the code
- react-markdown is installed for rendering responses — don't switch to dangerouslySetInnerHTML
- Polling interval is 5 seconds — can increase to 10 if it causes performance issues
- Admin escalation archive is just status="resolved" with a filter, not a separate table
