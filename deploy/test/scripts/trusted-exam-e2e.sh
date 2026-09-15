#!/usr/bin/env bash

set -euo pipefail

required_variables=(
  TEST_BASE_URL
  TEST_ADMIN_ACCOUNT
  TEST_ADMIN_PASSWORD
  TEST_CANDIDATE_EMAIL
  TEST_CANDIDATE_CODE
  TEST_QUESTION_ID
)

for variable in "${required_variables[@]}"; do
  if [[ -z "${!variable:-}" ]]; then
    echo "[e2e] required variable is empty: ${variable}" >&2
    exit 1
  fi
done

for command in curl jq python3; do
  if ! command -v "$command" >/dev/null 2>&1; then
    echo "[e2e] required command is unavailable: ${command}" >&2
    exit 1
  fi
done

base_url="${TEST_BASE_URL%/}"
run_id="${GITHUB_RUN_ID:-$(date -u +%Y%m%d%H%M%S)}-${GITHUB_RUN_ATTEMPT:-1}"
session_id="acceptance-session-${run_id}"
candidate_email="${TEST_CANDIDATE_EMAIL%@*}+${run_id}@${TEST_CANDIDATE_EMAIL#*@}"

mapfile -t exam_times < <(python3 - <<'PY'
from datetime import datetime, timedelta, timezone

now = datetime.now(timezone.utc).replace(microsecond=0)
for seconds in (20, 60, 90):
    print((now + timedelta(seconds=seconds)).strftime("%Y-%m-%d %H:%M:%S"))
PY
)
start_time="${exam_times[0]}"
latest_start_time="${exam_times[1]}"
end_time="${exam_times[2]}"

redact_response() {
  jq 'if (.data | type) == "string" then .data = "<redacted>" else . end'
}

fail_response() {
  local step="$1"
  local response="$2"
  echo "[e2e] FAIL ${step}" >&2
  printf '%s' "$response" | redact_response >&2
  exit 1
}

expect_code() {
  local step="$1"
  local response="$2"
  local expected_code="$3"
  local actual_code
  actual_code="$(printf '%s' "$response" | jq -r '.code // empty')"
  if [[ "$actual_code" != "$expected_code" ]]; then
    fail_response "$step" "$response"
  fi
  echo "[e2e] PASS ${step}"
}

request() {
  curl --silent --show-error --max-time 20 "$@"
}

admin_login_body="$(jq -n \
  --arg userAccount "$TEST_ADMIN_ACCOUNT" \
  --arg password "$TEST_ADMIN_PASSWORD" \
  '{userAccount:$userAccount,password:$password}')"
admin_login="$(request -H 'Content-Type: application/json' -d "$admin_login_body" \
  "$base_url/system/sysUser/login")"
expect_code admin-login "$admin_login" 1000
admin_token="$(printf '%s' "$admin_login" | jq -r '.data')"

candidate_email_body="$(jq -n --arg email "$candidate_email" '{email:$email}')"
code_requested="$(request -H 'Content-Type: application/json' -d "$candidate_email_body" \
  "$base_url/friend/user/sendCode")"
expect_code candidate-code-request "$code_requested" 1000
candidate_login_body="$(jq -n --arg email "$candidate_email" --arg code "$TEST_CANDIDATE_CODE" \
  '{email:$email,code:$code}')"
candidate_login="$(request -H 'Content-Type: application/json' -d "$candidate_login_body" \
  "$base_url/friend/user/code/login")"
expect_code candidate-login "$candidate_login" 1000
candidate_token="$(printf '%s' "$candidate_login" | jq -r '.data')"
candidate_detail="$(request -H "Authorization: Bearer ${candidate_token}" \
  "$base_url/friend/user/detail")"
expect_code candidate-detail "$candidate_detail" 1000
candidate_user_id="$(printf '%s' "$candidate_detail" | jq -r '.data.userId')"
[[ "$candidate_user_id" =~ ^[0-9]+$ ]] || fail_response candidate-user-id "$candidate_detail"

exam_body="$(jq -n \
  --arg title "Phase 1 acceptance ${run_id}" \
  --arg start "$start_time" \
  --arg latest "$latest_start_time" \
  --arg endAt "$end_time" \
  '{
    title:$title,
    description:"Automated trusted exam acceptance",
    startTime:$start,
    latestStartTime:$latest,
    endTime:$endAt,
    durationMinutes:5,
    timezone:"Asia/Shanghai",
    maxFormalSubmissions:2,
    resultReleasePolicy:"MANUAL"
  }')"
created="$(request -H 'Content-Type: application/json' -H "Authorization: Bearer ${admin_token}" \
  -d "$exam_body" "$base_url/system/exam")"
expect_code create-draft "$created" 1000
exam_id="$(printf '%s' "$created" | jq -r '.data')"

composition="$(jq -n --argjson questionId "$TEST_QUESTION_ID" \
  '{questions:[{questionId:$questionId,questionOrder:1,score:100,required:true,questionType:"PROGRAMMING"}]}')"
composed="$(request -X PUT -H 'Content-Type: application/json' -H "Authorization: Bearer ${admin_token}" \
  -d "$composition" "$base_url/system/exam/$exam_id/questions")"
expect_code compose-paper "$composed" 1000

published="$(request -X POST -H "Authorization: Bearer ${admin_token}" \
  -H "Idempotency-Key: acceptance-publish-${run_id}" \
  -H "X-Request-ID: acceptance-publish-${run_id}" \
  "$base_url/system/exam/$exam_id/publish")"
expect_code publish-version "$published" 1000

authorization="$(jq -n --arg userId "$candidate_user_id" \
  '{userIds:[$userId],source:"MANUAL"}')"
authorized="$(request -X POST -H 'Content-Type: application/json' -H "Authorization: Bearer ${admin_token}" \
  -H "X-Request-ID: acceptance-authorize-${run_id}" -d "$authorization" \
  "$base_url/system/exam/$exam_id/candidates")"
expect_code authorize-candidate "$authorized" 1000
[[ "$(printf '%s' "$authorized" | jq -r '.data[0].authorized')" == true ]] \
  || fail_response candidate-authorization-state "$authorized"

for _ in $(seq 1 30); do
  access="$(request -H "Authorization: Bearer ${candidate_token}" \
    "$base_url/friend/exam/$exam_id/access")"
  expect_code access-check "$access" 1000 >/dev/null
  [[ "$(printf '%s' "$access" | jq -r '.data.canStart')" == true ]] && break
  sleep 2
done
[[ "$(printf '%s' "$access" | jq -r '.data.canStart')" == true ]] \
  || fail_response admission-window "$access"
echo "[e2e] PASS admission-window"

start_body="$(jq -n --arg sessionId "$session_id" \
  '{sessionId:$sessionId,client:{platform:"github-actions"}}')"
started="$(request -X POST -H 'Content-Type: application/json' \
  -H "Authorization: Bearer ${candidate_token}" \
  -H "Idempotency-Key: acceptance-start-${run_id}" \
  -H "X-Request-ID: acceptance-start-${run_id}" \
  -d "$start_body" "$base_url/friend/exam/$exam_id/attempts/start")"
expect_code start-attempt "$started" 1000
attempt_id="$(printf '%s' "$started" | jq -r '.data.attemptId')"
version_question_id="$(printf '%s' "$started" | jq -r '.data.questions[0].versionQuestionId')"
[[ "$(printf '%s' "$started" | jq -r '.data.questions | length')" == 1 ]] \
  || fail_response immutable-question-snapshot "$started"

integrity_body="$(jq -n --arg sessionId "$session_id" \
  '{sessionId:$sessionId,events:[{clientSequence:1,eventType:"FOCUS_LOST",metadata:{durationMs:250,visibilityState:"hidden",discarded:"must-not-persist"}}]}')"
integrity="$(request -X POST -H 'Content-Type: application/json' \
  -H "Authorization: Bearer ${candidate_token}" -d "$integrity_body" \
  "$base_url/friend/exam/attempts/$attempt_id/integrity-events")"
expect_code integrity-event "$integrity" 1000
[[ "$(printf '%s' "$integrity" | jq -r '.data.accepted')" == 1 ]] \
  || fail_response integrity-event-state "$integrity"

solution='import java.util.*; public class Main { public static void main(String[] args) { Scanner s = new Scanner(System.in); System.out.println(s.nextInt() + s.nextInt()); } }'
answer_body="$(jq -n --arg content "$solution" \
  '{expectedVersion:0,answerType:"CODE",language:"java",content:$content}')"
saved="$(request -X PUT -H 'Content-Type: application/json' \
  -H "Authorization: Bearer ${candidate_token}" -d "$answer_body" \
  "$base_url/friend/exam/attempts/$attempt_id/answers/$version_question_id")"
expect_code autosave-answer "$saved" 1000
answer_version="$(printf '%s' "$saved" | jq -r '.data.answerVersion')"

submission_body="$(jq -n --arg versionQuestionId "$version_question_id" \
  --argjson answerVersion "$answer_version" \
  '{versionQuestionId:$versionQuestionId,answerVersion:$answerVersion,submitKind:"FORMAL"}')"
submitted="$(request -X POST -H 'Content-Type: application/json' \
  -H "Authorization: Bearer ${candidate_token}" \
  -H "Idempotency-Key: acceptance-submit-${run_id}" -d "$submission_body" \
  "$base_url/friend/exam/attempts/$attempt_id/submissions")"
expect_code submit-for-judge "$submitted" 1000

finalized="$(request -X POST -H "Authorization: Bearer ${candidate_token}" \
  -H "Idempotency-Key: acceptance-finalize-${run_id}" \
  -H "X-Request-ID: acceptance-finalize-${run_id}" \
  "$base_url/friend/exam/attempts/$attempt_id/finalize")"
expect_code finalize-attempt "$finalized" 1000
[[ "$(printf '%s' "$finalized" | jq -r '.data.status')" == SUBMITTED ]] \
  || fail_response finalize-state "$finalized"

for _ in $(seq 1 30); do
  receipt="$(request -H "Authorization: Bearer ${candidate_token}" \
    "$base_url/friend/exam/attempts/$attempt_id/receipt")"
  expect_code receipt "$receipt" 1000 >/dev/null
  [[ "$(printf '%s' "$receipt" | jq -r '.data.gradeStatus')" == READY ]] && break
  sleep 2
done
[[ "$(printf '%s' "$receipt" | jq -r '.data.gradeStatus')" == READY ]] \
  || fail_response grade-ready "$receipt"
echo "[e2e] PASS judge-and-grade-ready"

monitor="$(request -H "Authorization: Bearer ${admin_token}" \
  "$base_url/system/exam/$exam_id/monitor")"
expect_code admin-monitor "$monitor" 1000
[[ "$(printf '%s' "$monitor" | jq -r '.data.submitted')" == 1 ]] \
  || fail_response monitor-submitted-count "$monitor"

evidence="$(request -H "Authorization: Bearer ${admin_token}" \
  "$base_url/system/exam/$exam_id/attempts/$attempt_id/evidence")"
expect_code admin-evidence "$evidence" 1000
[[ "$(printf '%s' "$evidence" | jq -r '[.data[] | select(.category == "INTEGRITY" and .eventType == "FOCUS_LOST" and (.metadataJson | contains("must-not-persist") | not))] | length')" == 1 ]] \
  || fail_response integrity-evidence "$evidence"

grades="$(request -H "Authorization: Bearer ${admin_token}" \
  "$base_url/system/exam/$exam_id/grades")"
expect_code admin-grade-preview "$grades" 1000
[[ "$(printf '%s' "$grades" | jq -r '.data[0] | [.status,.totalScore,.maxScore] | join(":")')" == READY:100:100 ]] \
  || fail_response grade-preview "$grades"

hidden_result="$(request -H "Authorization: Bearer ${candidate_token}" \
  "$base_url/friend/exam/attempts/$attempt_id/result")"
expect_code result-hidden-before-release "$hidden_result" 3232

for _ in $(seq 1 60); do
  monitor="$(request -H "Authorization: Bearer ${admin_token}" \
    "$base_url/system/exam/$exam_id/monitor")"
  expect_code exam-finish-check "$monitor" 1000 >/dev/null
  [[ "$(printf '%s' "$monitor" | jq -r '.data.status')" == FINISHED ]] && break
  sleep 2
done
[[ "$(printf '%s' "$monitor" | jq -r '.data.status')" == FINISHED ]] \
  || fail_response exam-finished "$monitor"
echo "[e2e] PASS exam-finished"

released="$(request -X POST -H "Authorization: Bearer ${admin_token}" \
  -H "Idempotency-Key: acceptance-release-${run_id}" \
  -H "X-Request-ID: acceptance-release-${run_id}" \
  "$base_url/system/exam/$exam_id/results/release")"
expect_code release-results "$released" 1000

result="$(request -H "Authorization: Bearer ${candidate_token}" \
  "$base_url/friend/exam/attempts/$attempt_id/result")"
expect_code candidate-result "$result" 1000
[[ "$(printf '%s' "$result" | jq -r '.data | [.status,.totalScore,.maxScore,(.items | length)] | join(":")')" == RELEASED:100:100:1 ]] \
  || fail_response candidate-result-state "$result"

echo "[e2e] complete: examId=${exam_id}, attemptId=${attempt_id}, score=100/100"
