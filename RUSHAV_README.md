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
- [ ] Landing page with four-window launcher
- [ ] Profile selector dropdown per window
- [ ] Polling for real-time updates (admin + SME windows)

### In progress
- (update this as you work)

### Blocked / waiting on John
- (update this when you need something from John's side)

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

- When testing the classifier, use these exact queries:
  - Clear match: "How do I make pour-over coffee?" → Coffee, ~0.9
  - Ambiguous: "What should I drink today?" → clarification question
  - No match: "How do I file my taxes?" → escalation
- If classifier confidence seems off, the issue is usually in the CLASSIFIER_PROMPT, not the code
- react-markdown is installed for rendering responses — don't switch to dangerouslySetInnerHTML
- Polling interval is 5 seconds — can increase to 10 if it causes performance issues
- Admin escalation archive is just status="resolved" with a filter, not a separate table
