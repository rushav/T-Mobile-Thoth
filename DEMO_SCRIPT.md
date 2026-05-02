# Demo Script — Project Thoth

## Setup (do this before the demo)

```bash
# From the repo root, with the database freshly seeded
./launch.sh
```

Wait for the browser to open at `http://localhost:5173`. Confirm:
- Backend swagger loads at `http://localhost:8000/docs`
- A login screen appears showing **User / SME / Admin** role buttons.

If you need to reset between rehearsals:
```bash
rm data/thoth.db && rm -rf data/chroma/ && cd backend && python seed.py
```

## Demo flow (10 minutes)

### 1. The problem (30s)
> "T-Mobile has thousands of senior engineers and ops people. Their expertise is locked in their heads. Document-it-all approaches always fail — the docs are stale before they're written. Thoth flips the model: capture knowledge by interviewing the expert, then let users ask questions in natural language."

### 2. The user experience (90s)

Click **User** → click **Alex Rivera**. In the chat, ask:

> **"What score gives a restaurant an A grade?"**

Point out:
- The answer is grounded in approved knowledge (90-100 points).
- A subject pill ("Food Safety & Health Inspections") shows it routed to the right agent.
- A disclaimer notes the answer is from internal SME knowledge, not training data.

Then ask a question outside any subject:

> **"How do I train my dog?"**

→ Routes to admin escalation. Thoth refuses to make up an answer.

### 3. The closed-book guarantee (30s)

> "If we wipe the knowledge base, Thoth refuses every question. It never falls back to the LLM's training data."

(Skip the actual purge in the live demo unless asked — describe it. Or, if the demo allows: hit `POST /api/v1/system/purge` via curl, then re-ask the A-grade question, show the routing response.)

### 4. SME knowledge capture (3 min)

Open a new browser tab, sign out, sign in as **SME → Dr. Sarah Chen**.

- Click **Interview**, choose her subject (Food Safety), pick **Structured** mode, click **Start interview**.
- Thoth asks an opening question. Type a quick fact, e.g. *"Routine inspections are twice a year for full-service restaurants."*
- Send a couple more turns to show the back-and-forth.
- Click **Generate summary** — Thoth synthesizes a draft entry strictly from what Sarah said.
- Click **Approve** — entry status goes to `sme_approved`, queued for admin review.

> "Two key things just happened: the synthesizer is constrained to ONLY use what the SME actually said — no inference, no embellishment. And the entry needs a SECOND approval before it enters the live KB."

### 5. Admin approval (1 min)

Sign out. Sign in as **Admin → Pat Morgan**.

- The Approval Queue tab shows the SME-approved entry.
- Click **Approve** — status → `approved`, indexed in ChromaDB.
- (Or click **Reject** to show the other path.)

### 6. The new entry is live (30s)

Switch back to a User session and ask a question that the new entry covers — e.g. *"How often are routine restaurant inspections?"* — Thoth answers with the new content.

### 7. Multi-domain routing (60s)

Stay in the User chat. Ask:

> **"What's the Section 179 deduction limit for 2024?"**

→ Routes to the Tax SME (James Ortega), answers $1,160,000 from the seeded Tax knowledge.

> **"What is the EPA penalty for not having an EPA ID?"**

→ Routes to Dr. Nina Kowalski (Environmental Compliance), answers $37,500/day.

These are precise, specific facts. Point out: the LLM gets these wrong from training data alone. Thoth gets them right because it's reading from the approved KB.

### 8. The benchmark API (60s)

> "Beyond the demo UI, we ship a parallel `/api/v1` surface. It's the contract the evaluation harness exercises — Bearer-authenticated, lifecycle-tracked, token-tracked."

Show `benchmark/api-specification.md` and run the smoke suite:

```bash
./test_benchmark.sh
```

Show the running output: 36 tests, status codes, the `Total tokens consumed:` line at the end.

### 9. Closing (30s)

Open `ARCHITECTURE.md` to the capability-mapping table. Walk through how each of the 8 capabilities maps to a specific component.

> "Eight capabilities, each owned by a single component, each with a clear data contract. The system is built so you can replace a piece — swap ChromaDB for pgvector, swap Sonnet for a fine-tuned in-house model — without rearchitecting."

End on `PRODUCTION_RECOMMENDATIONS.md`:

> "Two weeks of work from here gets us to a deployable single-department service. SSO, Postgres, Redis sessions, cost dashboards. The PoC was designed to make that bridge short."

## Backup / talking points

- **"Is this just RAG?"** — RAG is the retrieval mechanism. The novel pieces are the closed-book guarantee, the per-subject agent isolation, and the two-stage approval that keeps the corpus trustworthy.
- **"Why two approvals?"** — SME approval = "I said this correctly." Admin approval = "this is fit for company-wide consumption." Different concerns; both must hold.
- **"Why Haiku for classification?"** — runs on every query, has to be fast and cheap. Sonnet would 5× our per-query cost for marginal accuracy gain.
- **"What stops the SME agent from hallucinating?"** — the prompt forbids training-data answers, retrieval is hard-scoped to the subject's collection, and the response layer downgrades any "I don't know" output to a routing response so we never falsely claim `grounded=true`.
