#!/usr/bin/env bash
set -euo pipefail

base_url="${TEST_BASE_URL:?Set TEST_BASE_URL to the test stack URL}"
base_url="${base_url%/}"
question_id="${TEST_QUESTION_ID:?Set TEST_QUESTION_ID to a two-sum question ID}"
exam_id="${TEST_EXAM_ID:-}"
submissions="${SUBMISSIONS:-6}"
poll_attempts="${POLL_ATTEMPTS:-60}"
code_sleep_millis="${CODE_SLEEP_MILLIS:-0}"

if ! [[ "$submissions" =~ ^[1-9][0-9]*$ ]]; then
    echo "SUBMISSIONS must be a positive integer" >&2
    exit 1
fi
if ! [[ "$poll_attempts" =~ ^[1-9][0-9]*$ ]]; then
    echo "POLL_ATTEMPTS must be a positive integer" >&2
    exit 1
fi
if ! [[ "$code_sleep_millis" =~ ^[0-9]+$ ]]; then
    echo "CODE_SLEEP_MILLIS must be a non-negative integer" >&2
    exit 1
fi
if [[ -n "$exam_id" ]] && ! [[ "$exam_id" =~ ^[1-9][0-9]*$ ]]; then
    echo "TEST_EXAM_ID must be a positive integer when set" >&2
    exit 1
fi

code_template='import java.util.*;
public class Main {
    public static void main(String[] args) throws Exception {
        Thread.sleep(__CODE_SLEEP_MILLIS__L);
        Scanner s = new Scanner(System.in);
        int n = s.nextInt();
        int[] a = new int[n];
        for (int i = 0; i < n; i++) a[i] = s.nextInt();
        int target = s.nextInt();
        for (int i = 0; i < n; i++) {
            for (int j = i + 1; j < n; j++) {
                if (a[i] + a[j] == target) {
                    System.out.println(i + " " + j);
                    return;
                }
            }
        }
    }
}'
code="${code_template/__CODE_SLEEP_MILLIS__/$code_sleep_millis}"

login="$(curl --fail --silent --show-error --max-time 15 \
    -H 'Content-Type: application/json' \
    -d '{"email":"student@syncode.test"}' \
    "$base_url/friend/user/test-login")"
token="$(jq -er 'select(.code == 1000) | .data | select(type == "string" and length > 20)' <<<"$login")"
payload="$(jq -nc --arg questionId "$question_id" --arg examId "$exam_id" --arg userCode "$code" \
    '{questionId:$questionId,programType:0,userCode:$userCode}
     + if $examId == "" then {} else {examId:$examId} end')"

request_ids=()
for ((i = 0; i < submissions; i++)); do
    response="$(curl --fail --silent --show-error --max-time 15 \
        -H 'Content-Type: application/json' \
        -H "Authorization: Bearer $token" \
        -d "$payload" "$base_url/friend/user/question/rabbit/submit")"
    request_id="$(jq -er 'select(.code == 1000) | .data.requestId | select(type == "string" and length > 0)' <<<"$response")"
    request_ids+=("$request_id")
    echo "accepted $request_id"
done

for request_id in "${request_ids[@]}"; do
    finished=false
    for ((attempt = 0; attempt < poll_attempts; attempt++)); do
        result_query=(
            --data-urlencode "questionId=$question_id"
            --data-urlencode "requestId=$request_id"
        )
        if [[ -n "$exam_id" ]]; then
            result_query+=(--data-urlencode "examId=$exam_id")
        fi
        result="$(curl --fail --silent --show-error --max-time 15 -G \
            -H "Authorization: Bearer $token" \
            "${result_query[@]}" \
            "$base_url/friend/user/question/exe/result")"
        pass="$(jq -er 'select(.code == 1000) | .data.pass' <<<"$result")"
        if [[ "$pass" == "1" ]]; then
            echo "passed $request_id"
            finished=true
            break
        fi
        if [[ "$pass" == "0" ]]; then
            echo "failed $request_id: $(jq -r '.data.exeMessage // "unknown"' <<<"$result")" >&2
            exit 1
        fi
        sleep 1
    done
    if [[ "$finished" != true ]]; then
        echo "timed out $request_id" >&2
        exit 1
    fi
done
