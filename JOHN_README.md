# JOHN_README.md

## ⚙️ For Claude Code — README management instructions

When John says "update my README" at the end of a session, do the following:
1. List every file that was created or modified during this session
2. Add a changelog entry for today using this exact format:
   ```
   [YYYY-MM-DD] [file1.py, file2.jsx] — Short description of what changed and why
   ```
3. If ANY shared file was modified (main.py, database.py, models.py, prompts.py, App.jsx, api.js), prefix the entry with ⚠️:
   ```
   ⚠️ [YYYY-MM-DD] [backend/models.py, backend/agents/prompts.py] — Changed synthesis prompt to be stricter. Rushav: check if sme_agent.py parsing still works with new format.
   ```
4. Update the status checklist: check off anything that's now working, add new items to "In progress" or "Blocked"
5. If something was added to "Blocked / waiting on Rushav", be specific about what's needed

When John starts a session and asks to read both READMEs, do the following:
1. Read RUSHAV_README.md changelog
2. Find any entries dated after John's last changelog entry
3. Report: "Rushav made X changes since your last session: [summary]. [N] affect shared files: [details]."
4. If Rushav has ⚠️ entries John hasn't seen, flag them clearly

---

## My ownership area: SME side + Knowledge pipeline + Database seeding

I own the "write path" — everything that gets knowledge into the system. Interviews, file uploads, synthesis, SME review flow, and the seed data.

---

## Files I own (don't edit these without telling me)

### Backend
```
backend/
├── agents/
│   ├── interviewer.py         # Conducts SME interviews, multi-turn conversation
│   └── prompts.py             # ALL prompts (shared file — coordinate with Rushav)
├── routes/
│   ├── interviews.py          # Start interview, send messages, generate synthesis
│   ├── review.py              # SME review/approve/reject/request-changes synthesis
│   ├── files.py               # Upload PDF/docx/txt, parse, store, link to entry
│   └── subjects.py            # Create/list subjects
├── services/
│   ├── knowledge.py           # CRUD for knowledge entries, add to ChromaDB on approval
│   └── file_parser.py         # Extract text from PDF/docx/txt files
├── models.py                  # DB models (shared — coordinate with Rushav on schema)
├── vector_store.py            # ChromaDB setup, collection management
├── seed.py                    # Demo data seeding script
└── database.py                # SQLAlchemy setup (shared — coordinate)
```

### Frontend
```
frontend/src/
├── App.jsx                    # Router (shared — coordinate)
├── api.js                     # Fetch wrapper (shared — coordinate)
├── pages/
│   └── SMEDashboardPage.jsx   # Interview chat + pending reviews + file upload
└── components/
    ├── ReviewPanel.jsx        # Approve/reject/request-changes synthesis
    ├── FileUpload.jsx         # File attachment component for interviews
    └── InterviewChat.jsx      # Interview-specific chat (if separated from generic)
```

### Shared files (both of us edit — always coordinate)
```
backend/main.py                # We both add routes here
backend/database.py            # Schema changes affect both of us
backend/models.py              # DB model changes affect both of us
backend/agents/prompts.py      # All prompts live here — tell each other before editing
frontend/src/App.jsx           # Route definitions
frontend/src/api.js            # API endpoint functions
```

---

## Current status

### Working
- [x] Interview start — creates session, links to SME and subject
- [x] Interview messaging — multi-turn conversation with Thoth, history persists
- [x] Interview structured mode — Thoth offers guided vs. freeform approach
- [x] Synthesis generation — produces summary from interview + uploaded files only
- [x] Synthesis revision — "request changes" actually revises and keeps conversation
- [x] SME approval — moves entry to "pending_admin_review" (not straight to KB)
- [x] File upload — PDF/docx/txt parsed and linked to interview
- [x] SME dashboard — interview chat, pending reviews, review requests from admin
- [x] SME subject scoping — SMEs only see their own subjects, not others'
- [x] Subject creation — new subjects immediately available for that SME
- [x] ChromaDB integration — approved entries added to subject-specific collections
- [x] Seed script — 3 subjects, 3 SMEs with expertise + contact info, 6 knowledge entries
- [x] Loading spinner during synthesis generation

### In progress

**Critical — Fix Before Demo**
- [x] Add files to interview serialization — include `files` array in `_serialize_interview()` in `backend/routes/interviews.py` so uploaded files survive page refresh
- [x] Build interview history/resume tab — add a "My Interviews" tab to `SMEDashboardPage.jsx` that calls `listInterviews(me.id)` and lets you click any past interview to reload its messages, files, synthesis, and status back into the InterviewTab

**High — Broken Behavior**
- [x] Add "Request Changes" to ReviewsTab — the Pending Reviews tab only has Approve/Reject; wire in `ReviewPanel` and hook `request_changes` to `reviewInterview(id, 'request_changes', feedback)` via the linked interview id
- [x] Add `request_changes` support to `review.py` — only handles `approve` and `reject`; add `request_changes` action that looks up the entry's linked interview and delegates to `interviewer.revise()`
- [ ] Fix wrong "done" message after rejection — `setStatus('done')` fires for both approve and reject; differentiate so the done screen shows "rejected, no further action" instead of "queued for admin approval"
- [ ] Warn before switching profiles mid-interview — add a `window.confirm` guard if `interviewId !== null && status !== 'idle'` when the profile dropdown changes

**Medium — Missing Behavior the Spec Requires**
- [ ] Set `review_date` on submission — in `submit_for_admin_review()` in `knowledge.py`, set `entry.review_date = datetime.utcnow() + timedelta(days=180)` when moving to `pending_admin_review`
- [ ] Add `review_requested` boolean to `KnowledgeEntry` — CLAUDE.md spec lists this column; add to `models.py` and set `True` when admin triggers a review request on an entry
- [ ] Reconcile status value "pending" → "pending_review" — CLAUDE.md contract specifies `"pending_review"` not `"pending"`; align `knowledge.py`, `interviews.py`, and `review.py` (coordinate with Rushav first)
- [ ] Seed escalation demo data — add 2–3 realistic open escalations to `seed.py` so the admin escalations inbox isn't empty on first run
- [ ] Add `GET /api/interviews/{id}/files` endpoint — or fold files into the interview GET response so the frontend can restore the files sidebar without local state

**Low — Polish and Structure**
- [ ] Extract `FileUpload.jsx` component — pull inline file input + upload logic out of `SMEDashboardPage.jsx` into a proper component with its own loading state and file list
- [ ] Add file removal — once `FileUpload.jsx` exists, add a delete button per file that calls a new `DELETE /api/files/{id}` endpoint; remove the file record and clear `extracted_text`
- [ ] Detect active in-progress interviews on start — before starting a new interview, check `listInterviews(me.id)` for any with `synthesis_status === 'draft'`; show a warning banner ("You have an unfinished interview for X — resume it?")
- [ ] Add `rejection_reason` display to ReviewsTab — when an entry has `status === 'rejected'`, show the rejection reason inline so the contributor knows why
- [x] Update JOHN_README.md status checklist — tick all 13 already-implemented items in the Working section
- [ ] Add image file type handling — add graceful fallback in `file_parser.py` that returns `"[Image attached — content not extractable]"` so `.png`/`.jpg` uploads don't hard-fail
- [ ] Guard against double-synthesize — if the SME generates, requests changes, then clicks Generate again it clobbers the revision; remove or disable the button after first synthesis
- [ ] Add `extracted_chars: 0` guard in file upload UI — if a file parses to 0 characters (encrypted PDF, empty docx), show a warning in the file sidebar instead of silently succeeding

### Blocked / waiting on Rushav
- (update this when you need something from Rushav's side)

---

## Changelog

Claude Code manages this section. John says "update my README" and Claude fills this in.
Never edit this manually.

```
Format:
[YYYY-MM-DD] [files] — What changed and why
⚠️ [YYYY-MM-DD] [shared files] — What changed + message to Rushav about what to watch for
```

### Log

[2026-04-29] [backend/routes/interviews.py, backend/routes/review.py, frontend/src/pages/SMEDashboardPage.jsx, john_readme.md] — Added interview file serialization so uploads survive refresh, built the SME "My Interviews" history/resume flow, added SME `request_changes` handling on the entry review route, and updated the README checklist to reflect completed work.

[2026-04-28] [initial setup] — Project created. All files listed above are my responsibility.

---

## Integration points with Rushav

These are the places where my code depends on Rushav's code or vice versa. When either of us changes something here, we need to tell the other.

### I depend on Rushav for:
1. **Profile endpoints** — My SME dashboard calls `/api/profiles?role=sme` to populate the header dropdown. If Rushav changes the response format, my dropdown breaks.
2. **Subject listing endpoint** — My interview start flow calls `/api/subjects` to show available subjects. Rushav owns this route.
3. **Admin approval completing the loop** — After I move entries to "pending_admin_review", Rushav's admin page approves them and adds to ChromaDB. If his approval logic changes, entries might not make it to the KB.
4. **Prompts file** — We share `prompts.py`. Don't edit without telling me, I won't edit without telling you.

### Rushav depends on me for:
1. **Knowledge entries in the DB** — Rushav's query route reads approved entries. If I change the schema or content format, his queries might break.
2. **ChromaDB collections** — I write to ChromaDB when admin approves. Rushav's agents read from it. We must match on collection naming, document format, and metadata.
3. **Synthesis format** — Rushav's SME agents use the synthesis content for RAG retrieval. If I change how the synthesis is structured, his retrieval quality changes.
4. **Subject creation** — When I create a new subject during an interview, Rushav's classifier needs to see it immediately. I commit to the DB before the interview begins.

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

# Interview session response format (my routes return this)
{
    "id": int,
    "sme_id": int,
    "subject_id": int,
    "messages": [{"role": "user"|"assistant", "content": str}],
    "synthesis": str | None,
    "synthesis_status": "draft" | "pending_review" | "approved" | "rejected"
}

# Knowledge entry format when moving to pending_admin_review
{
    "id": int,
    "subject_id": int,
    "contributor_id": int,
    "title": str,
    "content": str,           # The synthesis text
    "status": "pending_admin_review",
    "approved_by": None,      # Admin hasn't approved yet
    "review_date": str        # ISO date, 6 months from now
}
```

---

## Seed data details

The seed script (`seed.py`) creates:

```
Subjects:
  1. Coffee — "Coffee brewing, beans, equipment, drinks"
  2. Milk Tea — "Boba, tea types, toppings, preparation methods"
  3. Cars — "Vehicle maintenance, buying advice, common repairs"

SME Profiles:
  1. Lisa Li — Coffee (Brewing Methods) — lisa.li@gix.edu
  2. Mengting Li — Milk Tea (Boba & Tea Bases) — mengting.li@gix.edu
  3. Rushav — Cars (Maintenance & Buying) — rushav@gix.edu

User Profiles:
  1. Alex Rivera
  2. Jordan Lee

Admin Profile:
  1. Pat Morgan

Knowledge Entries (pre-approved, already in ChromaDB):
  Coffee:
    - "How to brew pour-over coffee" (by Lisa Li)
    - "Types of coffee beans and roast levels" (by Lisa Li)
  Milk Tea:
    - "How to make classic boba milk tea" (by Mengting Li)
    - "Tea types used in milk tea" (by Mengting Li)
  Cars:
    - "Basic car maintenance schedule" (by Rushav)
    - "What to check before buying a used car" (by Rushav)
```

If you need to reseed: delete `data/thoth.db` and `data/chroma/` folder, then run `python seed.py`.

---

## Synthesis rules (critical — don't break these)

The synthesis prompt has strict guardrails. These exist because during testing, the LLM was fabricating details the SME never mentioned.

1. ONLY include information the SME explicitly said in the interview
2. NEVER add external knowledge or extrapolate
3. If the SME gave a brief answer, the summary should be brief too
4. Empty sections should say "Not covered in this interview"
5. The revision flow must re-read the original transcript, not just edit the old synthesis

If you change SYNTHESIS_PROMPT or the revision logic, test with a deliberately minimal interview (say one vague sentence) and verify the synthesis doesn't magically expand into a detailed document.

---

## Notes for future me

- Interview conversation history is stored as JSON in the `messages` column. Never clear it — the SME needs to see their past conversation when they come back.
- When SME clicks "Request Changes", send the original transcript + feedback to Claude for revision, not just the old synthesis + feedback. This prevents drift from what was actually said.
- File text extraction: PyPDF2 for PDF, python-docx for docx, plain open() for txt. Images just get noted as "User attached an image" — no OCR.
- The structured interview framework asks: key facts → common questions → mistakes → escalation scenarios. This order matters because each question builds on the previous answers.
- Loading spinner: disable the "Generate Summary" button during API call. Don't let it fire twice.
- New subjects created during interview must be committed to the DB BEFORE the interview starts, so Rushav's classifier can see them if a user asks a question in another window at the same time.
