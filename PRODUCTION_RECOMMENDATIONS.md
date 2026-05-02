# From PoC to Production

This document is the bridge between the 2-week hackathon PoC and a deployable enterprise service. It calls out the gaps a real customer (T-Mobile, in our pilot framing) would close before exposing this to actual SMEs and end users.

## 1. Authentication & authorization

**Today (PoC):** the frontend has no auth — pick a profile, you're in. The `/api/v1` benchmark surface has a single shared Bearer key.

**Production:**
- **Federated SSO** via OAuth2 / SAML / OIDC (Okta or T-Mobile's identity provider). User identity comes from corporate directory — no in-app password store.
- **RBAC on the same tables** we already separate: `Profile.role` becomes a real authorization claim (User / SME / Admin / Auditor). Each route checks role + subject scope.
- **Per-subject SME ownership** — an SME can only synthesize/approve entries for subjects they own. The data model already supports this via `sme_subjects`; we just need the route guards.
- **Service-to-service auth** for the V1 benchmark surface should move from a static key to short-lived signed tokens (JWT) so we can revoke individual evaluator sessions without rotating a global secret.

## 2. Scale

**Today:** SQLite + ChromaDB on local disk, single-process FastAPI.

**Production:**
- **PostgreSQL** for the relational layer. SQLAlchemy abstracts this — no model changes needed. Add a connection pool (e.g., `pgbouncer`) and read replicas once read load justifies it.
- **Managed vector store** — ChromaDB is great for embedded use but doesn't scale horizontally. Pick one of: pgvector (lowest ops cost, lives in the same Postgres), Pinecone (managed, simple), or Weaviate (open-source with a hybrid lexical+vector option that helps for fact-heavy SME content).
- **Redis** for sessions and short-term caches: classifier results for repeated questions, in-flight clarification state. The current `services/sessions.py` is a process-local dict — move this to Redis on day 1 of horizontal scaling.
- **Stateless API workers** behind a load balancer (k8s + HPA, or AWS ECS). Once sessions live in Redis and the DBs are external, the API is naturally stateless.
- **Background workers** for synthesis + file parsing. Today these run synchronously in the request thread. Move to a queue (Celery / RQ / SQS) so the request returns a job ID and the UI polls — keeps p95 latency predictable.

## 3. Multi-tenancy

A T-Mobile rollout has multiple departments (retail ops, network engineering, customer support) who shouldn't see each other's knowledge.

- Add a `tenant_id` column to every table and every ChromaDB collection name (`tenant_{tid}_subject_{sid}`).
- The query path already isolates by subject; tenant becomes an extra coarser scope.
- One Anthropic API key per tenant is overkill — share at the platform level but tag each request with tenant for cost attribution.

## 4. Data sensitivity

- **Encryption at rest** for the relational store and the vector store. PostgreSQL native encryption + EBS/managed-disk encryption is enough for most enterprise risk profiles.
- **Encryption in transit** is table stakes — TLS terminating at the load balancer.
- **PII handling**: SME interviews may contain personal information that the SME mentions in passing. Add a PII-detection pass (regex + small classifier) to the synthesis output. Flag any draft that contains potential PII for admin review even if the SME didn't notice.
- **Audit logs**: every approve/reject/edit on a knowledge entry should be appended to an immutable audit log (separate Postgres table OR S3 + KMS). Today the `approved_at` / `approved_by` columns capture the latest state; we need full history for compliance.
- **Right-to-be-forgotten**: provide a tenant-admin endpoint to purge an SME's contributions. The vector store already has `remove_v1_entry`; wrap with an audit-logged tombstone.

## 5. Monitoring

- **Token cost dashboards**. Every LLM call already returns `usage`; ship to Datadog / CloudWatch / Grafana broken down by tenant, subject, and endpoint. Alert on day-over-day cost spikes.
- **Quality metrics**:
  - **Hallucination rate**: sample 1% of grounded answers for human review weekly. Compare against the source chunks.
  - **Refusal rate**: % of queries that route to admin instead of answering. Spike = a knowledge gap, not a system bug.
  - **Clarification yield**: of queries that hit clarification, what fraction resolve to a grounded answer in the next turn? Below ~70% suggests the classifier confidence thresholds need tuning.
- **Latency SLOs**: p50 / p95 / p99 for `POST /query`. Synthesis is allowed to be slow; query is not.
- **Approval-queue health**: time-to-admin-approval for SME-approved entries. If queues build up, knowledge goes stale.

## 6. Cost estimation

Approximations using current Anthropic pricing (Sonnet 4 ~$3/$15 per 1M in/out tokens, Haiku 4.5 ~$0.25/$1.25 per 1M).

| Volume | Daily cost | Notes |
|---|---|---|
| **100 queries/day** | ~$1-3 | Hackathon / pilot scale. Each query: classifier (Haiku, ~500 in / 50 out) + agent (Sonnet, ~2k in / 500 out). |
| **1,000 queries/day** | ~$15-30 | Departmental pilot. At this scale, prompt caching becomes worth wiring up — the per-subject system prompts repeat across queries. |
| **10,000 queries/day** | ~$150-300 | Full T-Mobile rollout for one business unit. At this point: enable prompt caching, batch-process the synthesis pipeline, and consider Haiku for "easy" classifications (top candidate already obvious from lexical match). |

Synthesis is rare — maybe 1-10 entries per SME per week. Even at 1k SMEs that's < 100 syntheses/day, ~$0.50/day total.

The dominant cost will be the per-query classifier+agent loop. Every dollar spent on prompt caching pays back within days at the 1k/day tier.

## 7. Knowledge maintenance

Knowledge rots. Today's "approved" entry is tomorrow's stale entry, and the system has no mechanism to surface that.

- **Automated review cycles** — every approved entry gets a `review_due_at` (90 days for fast-moving subjects, 365 for stable ones). When it lapses, the entry's SME gets a "please review" notification (the legacy schema already has `review_requested_at` infrastructure).
- **Drift detection** — compare each query's grounded chunks against the agent's answer. If the answer paraphrases beyond the chunk's literal claims, flag the chunk as "agent had to interpret". High-flag-count entries probably need an SME revisit.
- **Dead entries** — entries that haven't been retrieved in N months are candidates for archival. Don't delete; demote them out of the index but keep them queryable from the admin UI.
- **Conflict detection** — two entries on the same subject that contradict each other are the silent killer. Run nightly: pick pairs of entries from the same subject, ask Sonnet "do these contradict?" — surface conflicts to admin.

## 8. Onboarding flows the PoC doesn't have

- A real "new SME" wizard that walks through their first interview, materials upload, and first synthesis approval.
- A user search interface that's better than just a chat — many SME questions are well-suited to an autocomplete + suggested-questions model.
- An admin dashboard that surfaces: queue depth, time-to-approval per subject, top unanswered questions, top low-confidence routing destinations.

## What we'd build in the first sprint after handoff

1. Postgres migration + connection pool (a half-day, mostly migration scripts).
2. Move sessions to Redis (a few hours).
3. SSO via the customer's identity provider (1-2 days, depending on their setup).
4. Per-tenant scoping (1-2 days — schema migration + middleware injection).
5. Token-cost dashboard wired to the existing `usage` blocks (1 day).

That's two weeks of work to take the PoC from "it runs on my laptop" to "it serves a single department in production with cost visibility and access control."
