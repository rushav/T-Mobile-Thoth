# SME Review Continuation Design

**Date:** 2026-04-30  
**Scope:** InterviewTab flow only (`interviews.py`, `SMEDashboardPage.jsx`, `interviewer.py`)  
**Out of scope:** `review.py` (ReviewsTab), ChromaDB write logic, approval flow, `interviewer.synthesize()`

---

## Problem

When an SME clicks "Request Changes" during synthesis review, the feedback is fed directly to `interviewer.revise()` and a new synthesis is returned immediately. The SME's message never enters the interview transcript, Claude has no opportunity to ask follow-up questions, and the SME has no way to add more context before regeneration.

## Desired Flow

1. SME reviews synthesized summary
2. SME types a change request message and clicks "Request Changes"
3. That message is appended to the interview transcript as a new SME turn (tagged `post_review: true`)
4. Claude responds as the interviewer — asking follow-ups or acknowledging the addition
5. SME can continue the conversation via the chat window
6. When the SME is done, they click "Regenerate Summary"
7. The existing `synthesize` endpoint is called with the full updated transcript
8. A new synthesis replaces the previous draft; SME reviews again

---

## State Machine

### Frontend (`InterviewTab` status)

```
idle → chatting → reviewing → post_review_chatting → reviewing
                     ↓
               done_approved / done_rejected
```

`post_review_chatting` is entered when `request_changes` succeeds. It exits back to `reviewing` when "Regenerate Summary" is clicked and `synthesize` returns.

### Backend (`interview.synthesis_status`)

Existing values: `draft | pending_review | approved | rejected`  
New value: `post_review_chat`

No DB migration required — stored as a plain string in SQLite.

---

## Data Model

Each message in `interview.messages` (JSON array) gains an optional field:

```json
{"role": "user", "content": "...", "ts": "2026-04-30T12:00:00Z", "post_review": true}
```

`post_review` is `true` on all turns (both SME and Thoth) added after "Request Changes." Original interview turns have no `post_review` field (treated as `false`).

---

## Backend Changes

### `backend/routes/interviews.py`

**`review()` — `request_changes` branch**

Current: calls `interviewer.revise()`, writes new synthesis to DB, returns synthesis.

New:
1. Append SME feedback message to `interview.messages` with `post_review: true` and current UTC timestamp
2. Build full message history and call `interviewer.next_message()` (same call as `send_message`)
3. Append Claude's reply to `interview.messages` with `post_review: true`
4. Set `interview.synthesis_status = "post_review_chat"`
5. Commit, return:
   ```json
   {"status": "post_review_chat", "reply": "...", "messages": [...], "entry_id": 123}
   ```
   No synthesis in the response. Entry content and `entry_id` are untouched.

**`send_message()` endpoint**

When `interview.synthesis_status == "post_review_chat"`, add `"post_review": true` to both the incoming user message dict and the outgoing reply dict before appending to `interview.messages`. Otherwise unchanged.

**`synthesize()` endpoint**

No changes. Already reads `interview.messages` in full, calls `interviewer.synthesize()`, updates the linked entry, and sets `synthesis_status = "pending_review"`. Calling it from `post_review_chat` state works correctly — the full transcript including post-review turns is passed to synthesis.

### `backend/agents/interviewer.py`

**`transcript_from_messages()`**

```python
def transcript_from_messages(messages: list[dict]) -> str:
    lines = []
    for m in messages:
        role = "Thoth" if m.get("role") == "assistant" else "SME"
        if m.get("post_review"):
            role += " [post-review]"
        lines.append(f"{role}: {m.get('content', '')}")
    return "\n\n".join(lines)
```

No other changes to `interviewer.py`. `synthesize()`, `revise()`, and `next_message()` are untouched.

---

## Frontend Changes

### `frontend/src/pages/SMEDashboardPage.jsx`

**`requestChanges` handler**

Current: receives synthesis in response, sets it in state, stays in `reviewing`.

New:
```js
const requestChanges = async (feedback) => {
  setBusy(true)
  setErr('')
  try {
    const r = await reviewInterview(interviewId, 'request_changes', feedback)
    setMessages(r.messages)
    setStatus('post_review_chatting')
  } catch (e) { setErr(e.message) } finally { setBusy(false) }
}
```

**`regenerate` handler** (new)

```js
const regenerate = async () => {
  setSynthesizing(true)
  setErr('')
  try {
    const r = await synthesizeInterview(interviewId)
    setSynthesis(r.synthesis)
    setStatus('reviewing')
  } catch (e) { setErr(e.message) } finally { setSynthesizing(false) }
}
```

**`onSend` handler** — unchanged. Existing `sendInterviewMessage` call works; server tags turns based on `synthesis_status`.

**`ChatWindow` disabled guard**

```js
// Before
disabled={status !== 'chatting'}

// After
disabled={status !== 'chatting' && status !== 'post_review_chatting'}
```

**UI during `post_review_chatting`**

Same 2-column layout as `chatting`. Right column shows:
- A card with instructional text: "Add any missing context above, then regenerate when ready."
- "Regenerate Summary" button (calls `regenerate`, shows spinner while `synthesizing`)
- No `ReviewPanel` — synthesis is hidden until regeneration completes

`ReviewPanel` is only rendered when `status === 'reviewing'`. No change to that condition.

---

## What Is Not Changed

- `interviewer.synthesize()` — called identically, receives a richer transcript
- `interviewer.revise()` — no longer called from `interviews.py` review flow; still present for potential future use
- `review.py` — untouched
- ChromaDB write logic — untouched
- Approval flow (`approve` / `reject` branches, `knowledge_svc.submit_for_admin_review`) — untouched
- `KnowledgeEntry.status` — stays `pending` throughout; only `interview.synthesis_status` changes

---

## Files Changed

| File | Change |
|------|--------|
| `backend/routes/interviews.py` | `request_changes` branch rewritten; `send_message` tags post-review turns |
| `backend/agents/interviewer.py` | `transcript_from_messages` adds `[post-review]` label |
| `frontend/src/pages/SMEDashboardPage.jsx` | New state, new handler, updated `ChatWindow` guard, new right-column UI |
| `frontend/src/components/ReviewPanel.jsx` | No changes |
| `frontend/src/api.js` | No changes |
| `backend/models.py` | No changes |
