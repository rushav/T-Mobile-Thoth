#!/usr/bin/env bash
# test_benchmark.sh — end-to-end smoke test for the /api/v1 benchmark API.
#
# Runs 15 tests that exercise: health, auth, purge, closed-book, the SME
# pipeline (create SME → interview → turn → synthesize → SME approve →
# admin approve), grounded query, off-topic routing, reset/persistence,
# and 409 conflict on duplicate admin-approve.
#
# Requirements: curl, python3 (for JSON parsing — no jq needed).
# Run from the project root with the backend already serving.
#
# Usage:
#   ./test_benchmark.sh                  # uses BENCHMARK_API_KEY from .env
#   THOTH_BASE_URL=http://… ./test_benchmark.sh
#   BENCHMARK_API_KEY=xyz ./test_benchmark.sh
set -u  # not -e: we want to keep going even when individual tests fail
IFS=$'\n\t'

# ── Config ────────────────────────────────────────────────────────────────────
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$HERE/.env"

# Pull BENCHMARK_API_KEY out of .env without leaking ANTHROPIC_API_KEY into env
# any longer than necessary.
if [[ -f "$ENV_FILE" && -z "${BENCHMARK_API_KEY:-}" ]]; then
    BENCHMARK_API_KEY="$(grep -E '^BENCHMARK_API_KEY=' "$ENV_FILE" | tail -n1 | cut -d= -f2-)"
fi

API_KEY="${BENCHMARK_API_KEY:-thoth-benchmark-dev-key}"
BASE="${THOTH_BASE_URL:-http://localhost:8000}"
TMP_BODY="$(mktemp -t thoth_resp.XXXXXX)"
trap 'rm -f "$TMP_BODY"' EXIT

# ── Output helpers ────────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
    GREEN=$'\033[0;32m'; RED=$'\033[0;31m'; DIM=$'\033[2m'; BOLD=$'\033[1m'; NC=$'\033[0m'
else
    GREEN=""; RED=""; DIM=""; BOLD=""; NC=""
fi

PASSED=0
FAILED=0
TEST_NUM=0
TOTAL_TOKENS=0

step() {
    TEST_NUM=$((TEST_NUM + 1))
    printf "\n%s[%2d]%s %s\n" "$BOLD" "$TEST_NUM" "$NC" "$1"
}
pass() {
    PASSED=$((PASSED + 1))
    printf "     %sPASS%s — %s\n" "$GREEN" "$NC" "$1"
}
fail() {
    FAILED=$((FAILED + 1))
    printf "     %sFAIL%s — %s\n" "$RED" "$NC" "$1"
    if [[ -n "${2:-}" ]]; then
        printf "            %sexpected:%s %s\n" "$DIM" "$NC" "$2"
    fi
    if [[ -n "${3:-}" ]]; then
        printf "            %sgot:%s      %s\n" "$DIM" "$NC" "$3"
    fi
}

# ── HTTP helpers ──────────────────────────────────────────────────────────────
# After call() / call_noauth(), $HTTP holds the status code and "$TMP_BODY"
# holds the response body. Use xpath to extract fields.
call() {
    local method=$1 path=$2 body=${3:-}
    if [[ -n "$body" ]]; then
        HTTP=$(curl -sS -o "$TMP_BODY" -w "%{http_code}" \
            -X "$method" "$BASE$path" \
            -H "Authorization: Bearer $API_KEY" \
            -H "Content-Type: application/json" \
            -d "$body" 2>/dev/null) || HTTP="000"
    else
        HTTP=$(curl -sS -o "$TMP_BODY" -w "%{http_code}" \
            -X "$method" "$BASE$path" \
            -H "Authorization: Bearer $API_KEY" 2>/dev/null) || HTTP="000"
    fi
    _track_tokens
}

call_noauth() {
    local method=$1 path=$2
    HTTP=$(curl -sS -o "$TMP_BODY" -w "%{http_code}" \
        -X "$method" "$BASE$path" 2>/dev/null) || HTTP="000"
    _track_tokens
}

# Pull `usage.total_tokens` out of the most recent response body and add it to
# the cumulative counter. Silently does nothing if the body isn't JSON or the
# response carries no usage block.
_track_tokens() {
    local n
    n=$(python3 -c "
import json
try:
    d = json.load(open('$TMP_BODY'))
    u = d.get('usage') or {}
    v = u.get('total_tokens', 0) if u else 0
    print(int(v) if v else 0)
except Exception:
    print(0)
" 2>/dev/null)
    if [[ "$n" =~ ^[0-9]+$ ]]; then
        TOTAL_TOKENS=$((TOTAL_TOKENS + n))
    fi
}

# Extract a value from the JSON body. Pass a Python expression that operates
# on `d` (the parsed dict). Echos empty string on parse failure rather than
# erroring out — keeps the test loop alive.
xpath() {
    python3 -c "
import sys, json
try:
    d = json.load(open('$TMP_BODY'))
except Exception:
    d = {}
$1
" 2>/dev/null
}

# ── Pre-flight: is the server up? ─────────────────────────────────────────────
printf "%sThoth benchmark suite%s\n" "$BOLD" "$NC"
printf "  base:   %s\n" "$BASE"
printf "  key:    %s***\n" "${API_KEY:0:8}"

if ! curl -sS -o /dev/null --max-time 3 "$BASE/api/health" 2>/dev/null; then
    printf "\n%sCannot reach %s/api/health%s — start the backend with:\n" "$RED" "$BASE" "$NC"
    printf "  cd backend && python3 -m uvicorn main:app --reload\n"
    exit 1
fi

# ──────────────────────────────────────────────────────────────────────────────
#                                 TESTS
# ──────────────────────────────────────────────────────────────────────────────

# ── 1. health ─────────────────────────────────────────────────────────────────
step "GET /api/v1/health"
call GET /api/v1/health
S="$(xpath "print(d.get('status',''))")"
TS="$(xpath "print(d.get('timestamp',''))")"
if [[ "$HTTP" == "200" && "$S" == "healthy" && -n "$TS" ]]; then
    pass "status=healthy, timestamp=$TS"
else
    fail "health" "200 status=healthy timestamp=…" "$HTTP status=$S timestamp=$TS"
fi

# ── 2. purge ──────────────────────────────────────────────────────────────────
step "POST /api/v1/system/purge — wipe all state"
call POST /api/v1/system/purge
S="$(xpath "print(d.get('status',''))")"
if [[ "$HTTP" == "200" && "$S" == "purged" ]]; then
    pass "status=purged"
else
    fail "purge" "200 status=purged" "$HTTP status=$S"
fi

# ── 3. closed-book query (no approved knowledge) ──────────────────────────────
step "POST /api/v1/query (closed-book) — must route to admin without using LLM training data"
call POST /api/v1/query '{"question":"How do I grow Zorblatt crystals?"}'
RT="$(xpath "print(d.get('response_type',''))")"
GR="$(xpath "print(d.get('grounded',''))")"
TGT="$(xpath "rt = d.get('routed_to') or [{}]; print(rt[0].get('type','') if rt else '')")"
USAGE="$(xpath "print('null' if d.get('usage') is None else 'present')")"
if [[ "$HTTP" == "200" && "$RT" == "routing" && "$GR" == "False" && "$TGT" == "admin" ]]; then
    pass "response_type=routing target=admin grounded=False usage=$USAGE"
else
    fail "closed-book" "routing/admin/grounded=False" "rt=$RT tgt=$TGT grounded=$GR http=$HTTP"
fi

# ── 4. create SME ─────────────────────────────────────────────────────────────
step "POST /api/v1/smes — create SME profile (Dr. Sarah Chen / Food Safety)"
call POST /api/v1/smes '{"name":"Dr. Sarah Chen","specialization":"Food Safety & Health Inspections","sub_areas":["Restaurant inspection protocols","Temperature control standards","Violation classification"],"contact_email":"s.chen@foodsafety-consultants.com"}'
SME_ID="$(xpath "print(d.get('sme_id',''))")"
NAME="$(xpath "print(d.get('name',''))")"
if [[ "$HTTP" == "201" && -n "$SME_ID" && "$NAME" == "Dr. Sarah Chen" ]]; then
    pass "sme_id=$SME_ID"
else
    fail "create SME" "201 with sme_id" "$HTTP sme_id=$SME_ID name=$NAME"
fi

# ── 5. start interview ────────────────────────────────────────────────────────
step "POST /api/v1/smes/{sme_id}/interviews — start interview"
if [[ -n "$SME_ID" ]]; then
    call POST "/api/v1/smes/$SME_ID/interviews" '{"topic":"Restaurant Inspection Scoring System"}'
    INTERVIEW_ID="$(xpath "print(d.get('interview_id',''))")"
    STATUS="$(xpath "print(d.get('status',''))")"
    if [[ "$HTTP" == "201" && -n "$INTERVIEW_ID" && "$STATUS" == "in_progress" ]]; then
        pass "interview_id=$INTERVIEW_ID"
    else
        fail "start interview" "201 with interview_id, status=in_progress" "$HTTP interview_id=$INTERVIEW_ID status=$STATUS"
    fi
else
    INTERVIEW_ID=""
    fail "start interview" "needs sme_id from step 4" "skipped (no sme_id)"
fi

# ── 6. add turn ───────────────────────────────────────────────────────────────
step "POST /api/v1/interviews/{interview_id}/turns — add an SME response, get an agent follow-up"
if [[ -n "$INTERVIEW_ID" ]]; then
    call POST "/api/v1/interviews/$INTERVIEW_ID/turns" '{"sme_response":"The Municipal Food Safety Bureau uses a 100-point demerit system. A score of 90 to 100 is an A grade (green placard). 80 to 89 is B grade (yellow placard). 70 to 79 is C grade (orange placard). Below 70 triggers mandatory closure and reinspection within 72 hours. Critical violations deduct 5 points each, including food held in the temperature danger zone (41 to 135 degrees Fahrenheit) for more than 2 hours. First reinspection within 30 days is free, second costs 275 dollars, third costs 450 dollars."}'
    TN="$(xpath "print(d.get('turn_number',''))")"
    AFU="$(xpath "print('present' if d.get('agent_follow_up') else 'missing')")"
    USAGE_TOTAL="$(xpath "u = d.get('usage') or {}; print(u.get('total_tokens', 0))")"
    if [[ "$HTTP" == "200" && "$TN" == "1" && "$AFU" == "present" && "$USAGE_TOTAL" -gt 0 ]]; then
        pass "turn_number=1, agent_follow_up present, usage.total_tokens=$USAGE_TOTAL"
    else
        fail "add turn" "200 turn_number=1 agent_follow_up=present" "$HTTP turn=$TN follow_up=$AFU"
    fi
else
    fail "add turn" "needs interview_id from step 5" "skipped"
fi

# ── 7. synthesize ─────────────────────────────────────────────────────────────
step "POST /api/v1/smes/{sme_id}/knowledge/synthesize — synthesize knowledge entry"
if [[ -n "$SME_ID" && -n "$INTERVIEW_ID" ]]; then
    call POST "/api/v1/smes/$SME_ID/knowledge/synthesize" "{\"interview_ids\":[\"$INTERVIEW_ID\"],\"material_ids\":[],\"topic\":\"Restaurant Inspection Scoring System\"}"
    ENTRY_ID="$(xpath "print(d.get('entry_id',''))")"
    STATUS="$(xpath "print(d.get('status',''))")"
    USAGE_TOTAL="$(xpath "u = d.get('usage') or {}; print(u.get('total_tokens', 0))")"
    if [[ "$HTTP" == "201" && -n "$ENTRY_ID" && "$STATUS" == "draft" ]]; then
        pass "entry_id=$ENTRY_ID, status=draft, synthesis tokens=$USAGE_TOTAL"
    else
        fail "synthesize" "201 entry_id=… status=draft" "$HTTP entry_id=$ENTRY_ID status=$STATUS"
    fi
else
    ENTRY_ID=""
    fail "synthesize" "needs sme_id + interview_id" "skipped"
fi

# ── 8. SME approve ────────────────────────────────────────────────────────────
step "POST /api/v1/knowledge/{entry_id}/approve — SME-approves the draft (draft → sme_approved)"
if [[ -n "$ENTRY_ID" ]]; then
    call POST "/api/v1/knowledge/$ENTRY_ID/approve"
    STATUS="$(xpath "print(d.get('status',''))")"
    if [[ "$HTTP" == "200" && "$STATUS" == "sme_approved" ]]; then
        pass "status=sme_approved"
    else
        fail "SME approve" "200 status=sme_approved" "$HTTP status=$STATUS"
    fi
else
    fail "SME approve" "needs entry_id from step 7" "skipped"
fi

# ── 9. admin approve ──────────────────────────────────────────────────────────
step "POST /api/v1/knowledge/{entry_id}/admin-approve — admin approves (sme_approved → approved)"
if [[ -n "$ENTRY_ID" ]]; then
    call POST "/api/v1/knowledge/$ENTRY_ID/admin-approve"
    STATUS="$(xpath "print(d.get('status',''))")"
    APPROVED_AT="$(xpath "print(d.get('admin_approved_at') or '')")"
    if [[ "$HTTP" == "200" && "$STATUS" == "approved" && -n "$APPROVED_AT" ]]; then
        pass "status=approved, admin_approved_at=$APPROVED_AT"
    else
        BODY_PEEK="$(head -c 200 "$TMP_BODY" 2>/dev/null)"
        fail "admin approve" "200 status=approved" "$HTTP status=$STATUS body=${BODY_PEEK}"
    fi
else
    fail "admin approve" "needs entry_id from step 7" "skipped"
fi

# ── 10. grounded query about the synthesized topic ────────────────────────────
step "POST /api/v1/query (about the new approved knowledge) — must be grounded with disclaimer"
call POST /api/v1/query '{"question":"What score gives a restaurant an A grade in the Municipal Food Safety inspection?"}'
RT="$(xpath "print(d.get('response_type',''))")"
GR="$(xpath "print(d.get('grounded',''))")"
DISC="$(xpath "print('present' if d.get('disclaimer') else 'missing')")"
SRC_COUNT="$(xpath "print(len(d.get('sources') or []))")"
SESSION_ID_FROM_QUERY="$(xpath "print(d.get('session_id',''))")"
if [[ "$HTTP" == "200" && "$RT" == "answer" && "$GR" == "True" && "$DISC" == "present" && "${SRC_COUNT:-0}" -ge 1 ]]; then
    pass "response_type=answer, grounded=True, disclaimer=present, sources=$SRC_COUNT"
else
    fail "grounded query" "answer/grounded=True/disclaimer/sources>=1" "rt=$RT grounded=$GR disclaimer=$DISC sources=$SRC_COUNT http=$HTTP"
fi

# ── 11. off-topic query routes to admin ───────────────────────────────────────
step "POST /api/v1/query (off-topic) — must route to admin, NOT answer from training data"
call POST /api/v1/query '{"question":"How do I cook spaghetti carbonara?"}'
RT="$(xpath "print(d.get('response_type',''))")"
TGT="$(xpath "rt = d.get('routed_to') or [{}]; print(rt[0].get('type','') if rt else '')")"
GR="$(xpath "print(d.get('grounded',''))")"
if [[ "$HTTP" == "200" && "$RT" == "routing" && "$TGT" == "admin" && "$GR" == "False" ]]; then
    pass "response_type=routing, target=admin, grounded=False"
else
    fail "off-topic routing" "routing/admin/grounded=False" "rt=$RT tgt=$TGT grounded=$GR"
fi

# ── 12. reset session state (keep knowledge) ──────────────────────────────────
step "POST /api/v1/system/reset — clear sessions, preserve knowledge base"
call POST /api/v1/system/reset
S="$(xpath "print(d.get('status',''))")"
if [[ "$HTTP" == "200" && "$S" == "reset" ]]; then
    pass "status=reset"
else
    fail "reset" "200 status=reset" "$HTTP status=$S"
fi

# ── 13. query persistence after reset ─────────────────────────────────────────
step "POST /api/v1/query (after reset) — knowledge must persist across session reset"
call POST /api/v1/query '{"question":"What score range triggers a B grade on a restaurant inspection?"}'
RT="$(xpath "print(d.get('response_type',''))")"
GR="$(xpath "print(d.get('grounded',''))")"
SRC_COUNT="$(xpath "print(len(d.get('sources') or []))")"
if [[ "$HTTP" == "200" && "$RT" == "answer" && "$GR" == "True" && "${SRC_COUNT:-0}" -ge 1 ]]; then
    pass "knowledge persisted: response_type=answer, grounded=True"
else
    fail "persistence" "answer/grounded=True post-reset" "rt=$RT grounded=$GR sources=$SRC_COUNT http=$HTTP"
fi

# ── 14. 409 conflict on duplicate admin-approve ───────────────────────────────
step "POST /api/v1/knowledge/{entry_id}/admin-approve again — must return 409"
if [[ -n "$ENTRY_ID" ]]; then
    call POST "/api/v1/knowledge/$ENTRY_ID/admin-approve"
    CODE="$(xpath "print(d.get('code',''))")"
    if [[ "$HTTP" == "409" ]]; then
        pass "409 (code=$CODE)"
    else
        fail "duplicate admin-approve" "409 INVALID_STATE_TRANSITION" "$HTTP code=$CODE"
    fi
else
    fail "duplicate admin-approve" "needs entry_id from step 7" "skipped"
fi

# ── 15. auth: 401 without Bearer ──────────────────────────────────────────────
step "GET /api/v1/health without Authorization — must return 401"
call_noauth GET /api/v1/health
CODE="$(xpath "print(d.get('code',''))")"
if [[ "$HTTP" == "401" ]]; then
    pass "401 (code=$CODE)"
else
    fail "auth required" "401 UNAUTHORIZED" "$HTTP code=$CODE"
fi

# ──────────────────────────────────────────────────────────────────────────────
#                              EDGE CASES (16+)
# ──────────────────────────────────────────────────────────────────────────────
# The evaluator probes for these. Some will fail against the current API on
# purpose — that surfaces gaps to fix before submission.

# ── 16. wrong API key ─────────────────────────────────────────────────────────
step "GET /api/v1/health with wrong Bearer token — must return 401"
HTTP=$(curl -sS -o "$TMP_BODY" -w "%{http_code}" \
    -X GET "$BASE/api/v1/health" \
    -H "Authorization: Bearer not-a-real-key-xxx" 2>/dev/null) || HTTP="000"
CODE="$(xpath "print(d.get('code',''))")"
if [[ "$HTTP" == "401" ]]; then
    pass "401 (code=$CODE)"
else
    fail "wrong auth" "401 UNAUTHORIZED" "$HTTP code=$CODE"
fi

# ── 17. GET non-existent SME → 404 ────────────────────────────────────────────
step "GET /api/v1/smes/sme_doesnt_exist — must return 404"
call GET /api/v1/smes/sme_doesnt_exist
if [[ "$HTTP" == "404" ]]; then
    pass "404 not found"
else
    fail "missing SME" "404" "$HTTP"
fi

# ── 18. interview turn on non-existent interview → 404 ────────────────────────
step "POST /api/v1/interviews/int_nope/turns — must return 404"
call POST /api/v1/interviews/int_nope/turns '{"sme_response":"hello"}'
if [[ "$HTTP" == "404" ]]; then
    pass "404 not found"
else
    fail "missing interview" "404" "$HTTP"
fi

# ── 19. create SME with missing required fields → 400 ────────────────────────
step "POST /api/v1/smes with only {name:…} — evaluator expects 400 (FastAPI default is 422)"
call POST /api/v1/smes '{"name":"No Email Person"}'
if [[ "$HTTP" == "400" ]]; then
    pass "400 validation error"
else
    fail "missing fields" "400" "$HTTP — current API likely returns 422 (Pydantic)"
fi

# ── 20. synthesize with non-existent interview_id → 404 or 400 ────────────────
step "POST /api/v1/smes/{sme_id}/knowledge/synthesize with bogus interview_id — 404 or 400"
if [[ -n "$SME_ID" ]]; then
    call POST "/api/v1/smes/$SME_ID/knowledge/synthesize" '{"interview_ids":["int_bogus"],"material_ids":[],"topic":"Anything"}'
    if [[ "$HTTP" == "404" || "$HTTP" == "400" ]]; then
        pass "$HTTP error returned"
    else
        fail "synth missing interview" "404 or 400" "$HTTP — current API silently ignores missing IDs"
    fi
else
    fail "synth missing interview" "needs sme_id from earlier step" "skipped"
fi

# ── 21. query without session_id → 400 ────────────────────────────────────────
step "POST /api/v1/query without session_id — evaluator expects 400 (current API treats it as optional)"
call POST /api/v1/query '{"question":"Anything at all"}'
if [[ "$HTTP" == "400" ]]; then
    pass "400 (session_id required)"
else
    fail "missing session_id" "400" "$HTTP — current API allows it"
fi

# ── 22. multiple grounded queries — disclaimer + sources + usage on each ──────
step "Three grounded queries in a row — each must have disclaimer, sources, usage, correct SME"
ALL_OK="true"
DETAILS=""
for q in \
    "What score range gives a restaurant an A grade?" \
    "How much is the second reinspection fee?" \
    "What is the temperature danger zone for food in degrees Fahrenheit?"; do
    call POST /api/v1/query "{\"question\":\"$q\"}"
    GR="$(xpath "print(d.get('grounded',''))")"
    DISC="$(xpath "print('present' if d.get('disclaimer') else 'missing')")"
    SC="$(xpath "print(len(d.get('sources') or []))")"
    UO="$(xpath "print('present' if d.get('usage') else 'missing')")"
    SME_NAME="$(xpath "src = d.get('sources') or []; print(src[0].get('sme_name','') if src else '')")"
    if [[ "$GR" != "True" || "$DISC" != "present" || "$UO" != "present" || "${SC:-0}" -lt 1 || "$SME_NAME" != "Dr. Sarah Chen" ]]; then
        ALL_OK="false"
        DETAILS+="\n            grounded=$GR disclaimer=$DISC sources=$SC usage=$UO sme=$SME_NAME"
    fi
done
if [[ "$ALL_OK" == "true" ]]; then
    pass "all 3 grounded queries had disclaimer + sources + usage + correct SME"
else
    fail "multi-grounded" "every query grounded with disclaimer/sources/usage/correct sme_name" "$DETAILS"
fi

# ── 23. timestamps are ISO 8601 ────────────────────────────────────────────────
step "GET /api/v1/health timestamp must match ISO 8601 (YYYY-MM-DDTHH:MM:SSZ)"
call GET /api/v1/health
TS="$(xpath "print(d.get('timestamp',''))")"
ISO_OK="$(python3 -c "
import re
m = re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z\$', '$TS')
print('yes' if m else 'no')
" 2>/dev/null)"
if [[ "$ISO_OK" == "yes" ]]; then
    pass "ISO 8601: $TS"
else
    fail "iso 8601" "YYYY-MM-DDTHH:MM:SSZ" "$TS"
fi

# ── 24. approve already-approved entry → 409 ──────────────────────────────────
step "POST /api/v1/knowledge/{entry_id}/approve on already-approved entry — must return 409"
if [[ -n "$ENTRY_ID" ]]; then
    call POST "/api/v1/knowledge/$ENTRY_ID/approve"
    CODE="$(xpath "print(d.get('code',''))")"
    if [[ "$HTTP" == "409" ]]; then
        pass "409 (code=$CODE)"
    else
        fail "approve again" "409 INVALID_STATE_TRANSITION" "$HTTP code=$CODE"
    fi
else
    fail "approve again" "needs entry_id from earlier step" "skipped"
fi

# ── 25. PUT /knowledge/{id} update content, then query ────────────────────────
step "PUT /api/v1/knowledge/{entry_id} update content, then query — answer must reflect edit"
if [[ -n "$ENTRY_ID" ]]; then
    NEW_TEXT="UPDATED 2026: An A grade now requires a score of 95 to 100 (the threshold was raised from 90)."
    call PUT "/api/v1/knowledge/$ENTRY_ID" "{\"content\":\"$NEW_TEXT\"}"
    PUT_OK="$HTTP"
    UPDATED_CONTENT="$(xpath "print(d.get('content',''))")"
    call POST /api/v1/query '{"question":"What is the current minimum score for an A grade?"}'
    ANSWER="$(xpath "print(d.get('answer',''))")"
    if [[ "$PUT_OK" == "200" && "$UPDATED_CONTENT" == "$NEW_TEXT" && "$ANSWER" == *"95"* ]]; then
        pass "PUT accepted, query reflects new content"
    else
        fail "knowledge edit" "PUT 200 + query mentions '95'" "PUT=$PUT_OK content_match=$([[ "$UPDATED_CONTENT" == "$NEW_TEXT" ]] && echo yes || echo no) answer_has_95=$([[ "$ANSWER" == *"95"* ]] && echo yes || echo no)"
    fi
else
    fail "knowledge edit" "needs entry_id" "skipped"
fi

# ── 26. admin-approve a draft (skip SME approval) → 409 ───────────────────────
step "Create fresh draft entry, then POST /admin-approve directly — must return 409"
call POST /api/v1/smes '{"name":"Edge Case SME","specialization":"Skipworld Studies","sub_areas":["Test"],"contact_email":"edge@test.thoth.dev"}'
EDGE_SME="$(xpath "print(d.get('sme_id',''))")"
EDGE_ENTRY=""
if [[ -n "$EDGE_SME" ]]; then
    call POST "/api/v1/smes/$EDGE_SME/interviews" '{"topic":"Skipworld realm"}'
    EDGE_INT="$(xpath "print(d.get('interview_id',''))")"
    if [[ -n "$EDGE_INT" ]]; then
        call POST "/api/v1/interviews/$EDGE_INT/turns" '{"sme_response":"In Skipworld, the only known fact is that the sky is teal year-round."}'
        call POST "/api/v1/smes/$EDGE_SME/knowledge/synthesize" "{\"interview_ids\":[\"$EDGE_INT\"],\"material_ids\":[],\"topic\":\"Skipworld\"}"
        EDGE_ENTRY="$(xpath "print(d.get('entry_id',''))")"
    fi
fi
if [[ -n "$EDGE_ENTRY" ]]; then
    call POST "/api/v1/knowledge/$EDGE_ENTRY/admin-approve"
    CODE="$(xpath "print(d.get('code',''))")"
    if [[ "$HTTP" == "409" ]]; then
        pass "409 INVALID_STATE_TRANSITION (code=$CODE)"
    else
        fail "skip SME approval" "409" "$HTTP code=$CODE"
    fi
else
    fail "skip SME approval" "could not set up draft entry" "skipped"
fi

# ── 27. reject already-rejected → 409 ─────────────────────────────────────────
step "Reject the new draft, then reject again — second call must return 409"
if [[ -n "$EDGE_ENTRY" ]]; then
    call POST "/api/v1/knowledge/$EDGE_ENTRY/reject" '{"reason":"not useful"}'
    if [[ "$HTTP" != "200" ]]; then
        fail "reject again" "first reject 200" "$HTTP"
    else
        call POST "/api/v1/knowledge/$EDGE_ENTRY/reject" '{"reason":"again"}'
        CODE="$(xpath "print(d.get('code',''))")"
        if [[ "$HTTP" == "409" ]]; then
            pass "double-reject blocked (409, code=$CODE)"
        else
            fail "reject again" "409 INVALID_STATE_TRANSITION" "$HTTP code=$CODE"
        fi
    fi
else
    fail "reject again" "needs draft entry from previous test" "skipped"
fi

# ── 28. upload unsupported file type → 400 ────────────────────────────────────
step "POST /api/v1/smes/{sme_id}/materials with .xlsx — must return 400"
if [[ -n "$EDGE_SME" ]]; then
    XLSX_TMP="$(mktemp -t thoth_test.XXXXXX).xlsx"
    printf "fake xlsx contents" > "$XLSX_TMP"
    HTTP=$(curl -sS -o "$TMP_BODY" -w "%{http_code}" \
        -X POST "$BASE/api/v1/smes/$EDGE_SME/materials" \
        -H "Authorization: Bearer $API_KEY" \
        -F "title=Spreadsheet" \
        -F "file=@$XLSX_TMP;type=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" \
        2>/dev/null) || HTTP="000"
    rm -f "$XLSX_TMP"
    if [[ "$HTTP" == "400" ]]; then
        pass "400 unsupported type"
    else
        fail "bad mimetype" "400" "$HTTP"
    fi
else
    fail "bad mimetype" "needs sme_id" "skipped"
fi

# ── 29. upload >10MB file → 400 ───────────────────────────────────────────────
step "POST /api/v1/smes/{sme_id}/materials with 11MB plain-text file — must return 400"
if [[ -n "$EDGE_SME" ]]; then
    BIG_TMP="$(mktemp -t thoth_test.XXXXXX).txt"
    dd if=/dev/zero of="$BIG_TMP" bs=1024 count=11264 2>/dev/null
    HTTP=$(curl -sS -o "$TMP_BODY" -w "%{http_code}" \
        -X POST "$BASE/api/v1/smes/$EDGE_SME/materials" \
        -H "Authorization: Bearer $API_KEY" \
        -F "title=Big file" \
        -F "file=@$BIG_TMP;type=text/plain" \
        2>/dev/null) || HTTP="000"
    rm -f "$BIG_TMP"
    if [[ "$HTTP" == "400" ]]; then
        pass "400 file too large"
    else
        fail "oversized upload" "400" "$HTTP"
    fi
else
    fail "oversized upload" "needs sme_id" "skipped"
fi

# ── 30. multi-turn clarification flow ─────────────────────────────────────────
step "Vague question → clarification, then follow-up with SAME session_id → real answer"
call POST /api/v1/query '{"question":"How does it work?"}'
RT1="$(xpath "print(d.get('response_type',''))")"
SESS="$(xpath "print(d.get('session_id',''))")"
if [[ -n "$SESS" && "$RT1" == "clarification" ]]; then
    call POST /api/v1/query "{\"question\":\"I mean restaurant inspections\",\"session_id\":\"$SESS\"}"
    RT2="$(xpath "print(d.get('response_type',''))")"
    SESS2="$(xpath "print(d.get('session_id',''))")"
    if [[ "$SESS2" == "$SESS" && ( "$RT2" == "answer" || "$RT2" == "routing" ) ]]; then
        pass "session_id preserved across turns ($RT1 → $RT2)"
    else
        fail "multi-turn" "follow-up uses same session_id and resolves" "rt2=$RT2 sess2=$SESS2 first sess=$SESS"
    fi
else
    fail "multi-turn" "first turn 'clarification' with session_id" "rt=$RT1 sess=$SESS (classifier may not have produced a clarification given current state)"
fi

# ── 31. multi-SME overlapping; ambiguous query → clarify or multi-route ───────
step "Two SMEs with overlapping sub_areas; ambiguous query should clarify or list multiple targets"
call POST /api/v1/smes '{"name":"Coffee SME","specialization":"Coffee","sub_areas":["Brewing","Beans"],"contact_email":"c@test.thoth.dev"}'
call POST /api/v1/smes '{"name":"Tea SME","specialization":"Tea","sub_areas":["Brewing","Leaves"],"contact_email":"t@test.thoth.dev"}'
call POST /api/v1/query '{"question":"What is the right brewing temperature?"}'
RT="$(xpath "print(d.get('response_type',''))")"
ROUTED_COUNT="$(xpath "print(len(d.get('routed_to') or []))")"
if [[ "$RT" == "clarification" ]] || { [[ "$RT" == "routing" ]] && [[ "${ROUTED_COUNT:-0}" -ge 1 ]]; }; then
    pass "ambiguous query handled (rt=$RT, routed_to=$ROUTED_COUNT)"
else
    fail "multi-SME ambiguous" "clarification OR routing" "rt=$RT routed=$ROUTED_COUNT"
fi

# ── 32. two SMEs spanning topics → routed_to has BOTH ─────────────────────────
step "Query that spans both SME areas — routed_to should include BOTH SMEs"
call POST /api/v1/query '{"question":"Compare brewing methods across hot beverages"}'
RT="$(xpath "print(d.get('response_type',''))")"
ROUTED_COUNT="$(xpath "print(len(d.get('routed_to') or []))")"
if [[ "$RT" == "routing" && "${ROUTED_COUNT:-0}" -ge 2 ]]; then
    pass "routing with multiple targets ($ROUTED_COUNT)"
else
    fail "multi-SME routing" "routing with routed_to length >= 2" "rt=$RT routed=$ROUTED_COUNT — current API returns at most one target"
fi

# ── 33. multi-SME routing for "opening a restaurant" ─────────────────────────
step "Multi-SME query 'opening a restaurant' — should route or clarify (Food Safety + Tax + CRE relevant)"
# We already have Food Safety knowledge approved from earlier tests. Add bare
# Tax + CRE SME profiles so the system has multiple plausible targets for a
# question that spans regulations, leases, and taxes.
call POST /api/v1/smes '{"name":"James Ortega","specialization":"Small Business Tax Compliance","sub_areas":["Quarterly filing","Business deductions"],"contact_email":"j.ortega@taxnavigator.com"}'
call POST /api/v1/smes '{"name":"Marcus Williams","specialization":"Commercial Real Estate Leasing","sub_areas":["Lease negotiations","CAM charges"],"contact_email":"m.williams@cre-advisors.net"}'
call POST /api/v1/query '{"question":"I am opening a new restaurant — what do I need to know about food safety, my commercial lease, and small business taxes?"}'
RT="$(xpath "print(d.get('response_type',''))")"
ROUTED_COUNT="$(xpath "print(len(d.get('routed_to') or []))")"
GR="$(xpath "print(d.get('grounded',''))")"
SRC_COUNT="$(xpath "print(len(d.get('sources') or []))")"
# Reasonable: clarify across subjects, route somewhere, or grounded answer from
# Food Safety (the only approved KB content). Anything else is suspicious.
if [[ "$RT" == "clarification" ]] \
   || { [[ "$RT" == "routing" ]] && [[ "${ROUTED_COUNT:-0}" -ge 1 ]]; } \
   || { [[ "$RT" == "answer" ]] && [[ "$GR" == "True" ]] && [[ "${SRC_COUNT:-0}" -ge 1 ]]; }; then
    pass "multi-domain query handled (rt=$RT routed=$ROUTED_COUNT src=$SRC_COUNT)"
else
    fail "multi-SME restaurant query" "clarification, routing, or grounded answer" "rt=$RT routed=$ROUTED_COUNT grounded=$GR src=$SRC_COUNT"
fi

# ── 34. cross-topic: tax implications of CAM charges ─────────────────────────
step "Cross-topic query 'tax implications of CAM charges' — must NOT hallucinate from training data"
call POST /api/v1/query '{"question":"What are the tax implications of my commercial lease CAM charges?"}'
RT="$(xpath "print(d.get('response_type',''))")"
GR="$(xpath "print(d.get('grounded',''))")"
SRC_COUNT="$(xpath "print(len(d.get('sources') or []))")"
ANSWER="$(xpath "print((d.get('answer') or '')[:120].replace(chr(10), ' '))")"
# We have no approved Tax or CRE knowledge here, so the only acceptable
# behaviors are routing/clarification, OR a grounded answer with sources (if
# the classifier somehow matched Food Safety and grounded the answer there).
# A grounded=False answer or grounded=True with zero sources would mean leakage.
if [[ "$RT" == "routing" || "$RT" == "clarification" ]]; then
    pass "$RT (no leakage)"
elif [[ "$RT" == "answer" && "$GR" == "True" && "${SRC_COUNT:-0}" -ge 1 ]]; then
    pass "answer grounded with sources"
else
    fail "cross-topic CAM" "routing/clarification OR grounded answer with sources" "rt=$RT grounded=$GR src=$SRC_COUNT answer='${ANSWER}…'"
fi

# ── 35. purge then query → must refuse (closed-book) ──────────────────────────
step "POST /api/v1/system/purge then POST /api/v1/query — closed-book must route to admin"
call POST /api/v1/system/purge
PURGE_HTTP="$HTTP"
call POST /api/v1/query '{"question":"What does Glormax slime do?"}'
RT="$(xpath "print(d.get('response_type',''))")"
GR="$(xpath "print(d.get('grounded',''))")"
TGT="$(xpath "rt = d.get('routed_to') or [{}]; print(rt[0].get('type','') if rt else '')")"
if [[ "$PURGE_HTTP" == "200" && "$RT" == "routing" && "$GR" == "False" && "$TGT" == "admin" ]]; then
    pass "post-purge query refused (routing/admin/grounded=False)"
else
    fail "post-purge query" "purge=200 + routing/admin/grounded=False" "purge=$PURGE_HTTP rt=$RT grounded=$GR tgt=$TGT"
fi

# ── 36. after purge: /smes empty AND /knowledge empty ─────────────────────────
step "Verify GET /api/v1/smes and GET /api/v1/knowledge are empty after purge"
call GET /api/v1/smes
SME_COUNT="$(xpath "print(len(d.get('smes') or []))")"
call GET /api/v1/knowledge
KE_COUNT="$(xpath "print(len(d.get('entries') or []))")"
if [[ "${SME_COUNT:-1}" -eq 0 && "${KE_COUNT:-1}" -eq 0 ]]; then
    pass "/smes empty AND /knowledge empty"
else
    fail "post-purge cleanup" "both empty" "smes=$SME_COUNT entries=$KE_COUNT"
fi

# ──────────────────────────────────────────────────────────────────────────────
#                                 SUMMARY
# ──────────────────────────────────────────────────────────────────────────────
TOTAL=$((PASSED + FAILED))
printf "\n%s%d/%d tests passed%s" "$BOLD" "$PASSED" "$TOTAL" "$NC"
if [[ "$FAILED" -gt 0 ]]; then
    printf " %s(%d failed)%s\n" "$RED" "$FAILED" "$NC"
    EXIT_CODE=1
else
    printf " %sall green%s\n" "$GREEN" "$NC"
    EXIT_CODE=0
fi
printf "Total tokens consumed: %d\n" "$TOTAL_TOKENS"
exit $EXIT_CODE
