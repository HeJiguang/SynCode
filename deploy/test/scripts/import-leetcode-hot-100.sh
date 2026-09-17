#!/usr/bin/env bash

set -euo pipefail

: "${TEST_BASE_URL:?TEST_BASE_URL is required}"

base_url="${TEST_BASE_URL%/}"
teacher_email="${SYNCODE_TEST_TEACHER_EMAIL:-teacher@syncode.test}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
catalog_file="${SYNCODE_HOT100_CATALOG:-${script_dir}/../data/leetcode-hot-100-first-50.json}"
dry_run="${SYNCODE_IMPORT_DRY_RUN:-0}"

default_code='import java.io.*;
import java.util.*;

public class Main {
    public static void main(String[] args) throws Exception {
        BufferedReader reader = new BufferedReader(new InputStreamReader(System.in));
        // TODO: parse the input, implement the algorithm, and print the answer.
    }
}'

api() {
  local response
  response="$(curl --silent --show-error --max-time 30 "$@")"
  if [[ "$(jq -r '.code // empty' <<<"$response")" != "1000" ]]; then
    jq 'if (.data | type) == "string" then .data = "<redacted>" else . end' <<<"$response" >&2
    return 1
  fi
  printf '%s' "$response"
}

validate_catalog() {
  jq -e '
    length == 50
    and ([.[].rank] | sort == [range(1; 51)])
    and ([.[].rank] | length == (unique | length))
    and ([.[].sourceId] | length == (unique | length))
    and ([.[].slug] | length == (unique | length))
    and all(.[ ];
      (.sourceId | type == "number")
      and (.title | type == "string" and length > 0)
      and (.difficulty >= 1 and .difficulty <= 3)
      and (.algorithmTag | type == "string" and length > 0)
      and (.knowledgeTags | type == "string" and length > 0)
      and (.estimatedMinutes | type == "number" and . > 0)
      and (.statement | type == "string" and length > 0)
      and (.inputFormat | type == "string" and length > 0)
      and (.outputFormat | type == "string" and length > 0)
      and (.cases | type == "array" and length >= 2)
      and all(.cases[]; (.input | type == "string") and (.output | type == "string"))
    )
  ' "$catalog_file" >/dev/null
}

validate_catalog

if [[ "$dry_run" == "1" ]]; then
  echo "[hot100] catalog valid: 50 questions"
  exit 0
fi

teacher_login="$(api -H 'Content-Type: application/json' \
  -d "$(jq -n --arg email "$teacher_email" '{email:$email}')" \
  "$base_url/system/sysUser/test-login")"
teacher_token="$(jq -r '.data' <<<"$teacher_login")"

created=0
updated=0

while IFS= read -r entry; do
  rank="$(jq -r '.rank' <<<"$entry")"
  source_id="$(jq -r '.sourceId' <<<"$entry")"
  slug="$(jq -r '.slug' <<<"$entry")"
  short_title="$(jq -r '.title' <<<"$entry")"
  title="$(printf '[Hot100-%03d] %s' "$rank" "$short_title")"
  source_url="https://leetcode.cn/problems/${slug}/"
  content="$(jq -r --arg source_id "$source_id" --arg source_url "$source_url" '
    .statement
    + "\n\n输入格式：" + .inputFormat
    + "\n\n输出格式：" + .outputFormat
    + "\n\n来源参考：LeetCode #" + $source_id + " " + $source_url
    + "\n题面已按 SynCode 标准输入/输出判题模式重新编写。"
  ' <<<"$entry")"
  payload="$(jq -c \
    --arg title "$title" \
    --arg content "$content" \
    --arg default_code "$default_code" \
    --arg source_id "$source_id" \
    --arg source_url "$source_url" '
      {
        title: $title,
        difficulty: .difficulty,
        algorithmTag: .algorithmTag,
        knowledgeTags: .knowledgeTags,
        estimatedMinutes: .estimatedMinutes,
        trainingEnabled: 1,
        questionType: "PROGRAMMING",
        answerConfigJson: ({language:"java",entry:"stdin-stdout",sourceUrl:$source_url} | tojson),
        gradingConfigJson: ({mode:"STANDARD",source:"leetcode-hot-100",sourceId:$source_id} | tojson),
        timeLimit: 2000,
        spaceLimit: 262144,
        content: $content,
        questionCase: (.cases | tojson),
        defaultCode: $default_code,
        mainFuc: ""
      }
    ' <<<"$entry")"

  listed="$(api -G -H "Authorization: Bearer $teacher_token" \
    --data-urlencode 'pageNum=1' \
    --data-urlencode 'pageSize=10' \
    --data-urlencode "title=$title" \
    "$base_url/system/question/list")"
  question_id="$(jq -r --arg title "$title" '.rows[]? | select(.title == $title) | (.questionId | tostring)' <<<"$listed" | head -1)"

  if [[ -n "$question_id" ]]; then
    edit_payload="$(jq -c --arg question_id "$question_id" '. + {questionId:$question_id}' <<<"$payload")"
    api -X PUT -H 'Content-Type: application/json' -H "Authorization: Bearer $teacher_token" \
      -d "$edit_payload" "$base_url/system/question/edit" >/dev/null
    updated=$((updated + 1))
    echo "[hot100] updated ${rank}/50: ${title} (${question_id})"
  else
    api -H 'Content-Type: application/json' -H "Authorization: Bearer $teacher_token" \
      -d "$payload" "$base_url/system/question/add" >/dev/null
    created=$((created + 1))
    echo "[hot100] created ${rank}/50: ${title}"
  fi
done < <(jq -c 'sort_by(.rank)[]' "$catalog_file")

final_list="$(api -G -H "Authorization: Bearer $teacher_token" \
  --data-urlencode 'pageNum=1' \
  --data-urlencode 'pageSize=100' \
  --data-urlencode 'title=[Hot100-' \
  "$base_url/system/question/list")"
final_count="$(jq '[.rows[]? | select(.title | startswith("[Hot100-"))] | length' <<<"$final_list")"

if [[ "$final_count" != "50" ]]; then
  echo "[hot100] expected 50 imported questions, found ${final_count}" >&2
  exit 1
fi

echo "[hot100] import complete: created=${created} updated=${updated} total=${final_count}"
