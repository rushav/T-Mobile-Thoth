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
}

call_noauth() {
    local method=$1 path=$2
    HTTP=$(curl -sS -o "$TMP_BODY" -w "%{http_code}" \
        -X "$method" "$BASE$path" 2>/dev/null) || HTTP="000"
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
step "POST /api/v1/smes — create SME profile"
call POST /api/v1/smes '{"name":"Dr. Test Bench","specialization":"Glormax Beetles","sub_areas":["Bioluminescence","Murmur Caves"],"contact_email":"bench@test.thoth.dev"}'
SME_ID="$(xpath "print(d.get('sme_id',''))")"
NAME="$(xpath "print(d.get('name',''))")"
if [[ "$HTTP" == "201" && -n "$SME_ID" && "$NAME" == "Dr. Test Bench" ]]; then
    pass "sme_id=$SME_ID"
else
    fail "create SME" "201 with sme_id" "$HTTP sme_id=$SME_ID name=$NAME"
fi

# ── 5. start interview ────────────────────────────────────────────────────────
step "POST /api/v1/smes/{sme_id}/interviews — start interview"
if [[ -n "$SME_ID" ]]; then
    call POST "/api/v1/smes/$SME_ID/interviews" '{"topic":"Glormax beetle slime"}'
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
    call POST "/api/v1/interviews/$INTERVIEW_ID/turns" '{"sme_response":"Glormax beetles produce a luminescent green slime when threatened. They live exclusively in the Murmur Caves at depths below 400 meters. The slime turns red after exactly 73 minutes of exposure to oxygen, and then becomes inert within another 12 minutes."}'
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
    call POST "/api/v1/smes/$SME_ID/knowledge/synthesize" "{\"interview_ids\":[\"$INTERVIEW_ID\"],\"material_ids\":[],\"topic\":\"Glormax beetle slime\"}"
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
call POST /api/v1/query '{"question":"How long does Glormax beetle slime stay green before turning red?"}'
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
call POST /api/v1/query '{"question":"What happens to Glormax beetle slime after exposure to oxygen?"}'
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
#                                 SUMMARY
# ──────────────────────────────────────────────────────────────────────────────
TOTAL=$((PASSED + FAILED))
printf "\n%s%d/%d tests passed%s" "$BOLD" "$PASSED" "$TOTAL" "$NC"
if [[ "$FAILED" -gt 0 ]]; then
    printf " %s(%d failed)%s\n" "$RED" "$FAILED" "$NC"
    exit 1
else
    printf " %sall green%s\n" "$GREEN" "$NC"
fi
