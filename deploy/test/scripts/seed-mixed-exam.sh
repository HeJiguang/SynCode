#!/usr/bin/env bash

set -euo pipefail

: "${TEST_BASE_URL:?TEST_BASE_URL is required}"
: "${TEST_QUESTION_ID:?TEST_QUESTION_ID is required}"

base_url="${TEST_BASE_URL%/}"
teacher_email="${SYNCODE_TEST_TEACHER_EMAIL:-teacher@syncode.test}"
student_email="${SYNCODE_TEST_STUDENT_EMAIL:-student@syncode.test}"
exam_title="SynCode 实验室招新混合题型测试卷"

api() {
  local response
  response="$(curl --silent --show-error --max-time 30 "$@")"
  if [[ "$(jq -r '.code // empty' <<<"$response")" != "1000" ]]; then
    jq 'if (.data | type) == "string" then .data = "<redacted>" else . end' <<<"$response" >&2
    return 1
  fi
  printf '%s' "$response"
}

teacher_login="$(api -H 'Content-Type: application/json' -d "$(jq -n --arg email "$teacher_email" '{email:$email}')" "$base_url/system/sysUser/test-login")"
teacher_token="$(jq -r '.data' <<<"$teacher_login")"
student_login="$(api -H 'Content-Type: application/json' -d "$(jq -n --arg email "$student_email" '{email:$email}')" "$base_url/friend/user/test-login")"
student_token="$(jq -r '.data' <<<"$student_login")"
student_detail="$(api -H "Authorization: Bearer $student_token" "$base_url/friend/user/detail")"
student_id="$(jq -r '.data.userId' <<<"$student_detail")"

ensure_question() {
  local title="$1" type="$2" answer_config="$3" grading_config="$4" content="$5"
  local listed question_id body
  listed="$(api -G -H "Authorization: Bearer $teacher_token" --data-urlencode 'pageNum=1' --data-urlencode 'pageSize=10' --data-urlencode "title=$title" "$base_url/system/question/list")"
  question_id="$(jq -r --arg title "$title" '.rows[]? | select(.title == $title) | .questionId' <<<"$listed" | head -1)"
  if [[ -z "$question_id" ]]; then
    body="$(jq -n --arg title "$title" --arg type "$type" --arg content "$content" \
      --arg answer "$answer_config" --arg grading "$grading_config" '{
        title:$title,difficulty:2,algorithmTag:"招新综合",knowledgeTags:"实验室招新",estimatedMinutes:8,
        trainingEnabled:0,questionType:$type,answerConfigJson:$answer,gradingConfigJson:$grading,
        timeLimit:1000,spaceLimit:262144,content:$content,questionCase:"[]",defaultCode:"",mainFuc:""
      }')"
    api -H 'Content-Type: application/json' -H "Authorization: Bearer $teacher_token" -d "$body" "$base_url/system/question/add" >/dev/null
    listed="$(api -G -H "Authorization: Bearer $teacher_token" --data-urlencode 'pageNum=1' --data-urlencode 'pageSize=10' --data-urlencode "title=$title" "$base_url/system/question/list")"
    question_id="$(jq -r --arg title "$title" '.rows[]? | select(.title == $title) | .questionId' <<<"$listed" | head -1)"
  fi
  [[ "$question_id" =~ ^[0-9]+$ ]] || { echo "[seed] cannot resolve question: $title" >&2; exit 1; }
  printf '%s' "$question_id"
}

single_id="$(ensure_question '[测试] Git 分支选择' SINGLE_CHOICE '{"options":[{"id":"A","label":"feature/login"},{"id":"B","label":"main"},{"id":"C","label":"release"}]}' '{"correctAnswers":["A"],"caseSensitive":true}' '开发登录功能时，最适合使用哪个分支名？')"
multiple_id="$(ensure_question '[测试] 可信考试措施' MULTIPLE_CHOICE '{"options":[{"id":"A","label":"服务端计时"},{"id":"B","label":"自动保存"},{"id":"C","label":"把答案写进日志"},{"id":"D","label":"操作审计"}]}' '{"correctAnswers":["A","B","D"],"caseSensitive":true}' '下列哪些措施有助于形成可信考试闭环？')"
true_id="$(ensure_question '[测试] 幂等性判断' TRUE_FALSE '{}' '{"correctAnswers":["true"],"caseSensitive":true}' '同一个幂等键重复提交相同请求，不应创建重复业务记录。')"
fill_id="$(ensure_question '[测试] 平台名称填空' FILL_BLANK '{"blankCount":2}' '{"correctAnswers":["SynCode","42"],"caseSensitive":false}' '请依次填写本平台名称，以及 6 乘 7 的结果。')"
short_id="$(ensure_question '[测试] 故障恢复简答' SHORT_ANSWER '{}' '{"rubric":"说明服务端权威时间、答案版本、断线恢复三个得分点。"}' '简述在线考试在网络中断后如何安全恢复作答。')"
sql_id="$(ensure_question '[测试] SQL 查询题' SQL '{}' '{"rubric":"查询 users 表，筛选 status=1，并按 create_time 降序；SQL 执行隔离器上线前由教师人工评分。"}' '编写 SQL：查询 users 表中状态为 1 的用户，并按创建时间倒序。')"
file_id="$(ensure_question '[测试] 设计文档提交' FILE '{"acceptedFormats":[".pdf",".txt"],"maxSizeKb":200}' '{"rubric":"文档结构、需求覆盖、风险分析各占三分之一。"}' '提交一份不超过 200KB 的设计说明文件。')"
project_id="$(ensure_question '[测试] 项目作品提交' PROJECT '{"requireRepositoryUrl":true}' '{"rubric":"仓库可访问、README 完整、核心功能可运行。"}' '提交代码仓库地址，并说明项目目标与个人贡献。')"

exam_list="$(api -G -H "Authorization: Bearer $teacher_token" --data-urlencode 'pageNum=1' --data-urlencode 'pageSize=20' --data-urlencode "title=$exam_title" "$base_url/system/exam/list")"
exam_id="$(jq -r --arg title "$exam_title" '.rows[]? | select(.title == $title) | .examId' <<<"$exam_list" | head -1)"
if [[ -z "$exam_id" ]]; then
  start_time="$(date -u -v+120S '+%Y-%m-%d %H:%M:%S' 2>/dev/null || date -u -d '+120 seconds' '+%Y-%m-%d %H:%M:%S')"
  body="$(jq -n --arg title "$exam_title" --arg start "$start_time" '{title:$title,description:"覆盖九种题型的实验室招新测试卷。客观题自动评分，主观题由教师阅卷。",startTime:$start,latestStartTime:"2029-12-30 00:00:00",endTime:"2029-12-31 00:00:00",durationMinutes:90,timezone:"Asia/Shanghai",maxFormalSubmissions:10,resultReleasePolicy:"MANUAL"}')"
  created="$(api -H 'Content-Type: application/json' -H "Authorization: Bearer $teacher_token" -d "$body" "$base_url/system/exam")"
  exam_id="$(jq -r '.data' <<<"$created")"
fi

detail="$(api -H "Authorization: Bearer $teacher_token" "$base_url/system/exam/$exam_id")"
if [[ "$(jq -r '.data.status' <<<"$detail")" == "0" ]]; then
  composition="$(jq -n --argjson programming "$TEST_QUESTION_ID" --argjson single "$single_id" --argjson multiple "$multiple_id" --argjson trueFalse "$true_id" --argjson fill "$fill_id" --argjson short "$short_id" --argjson sql "$sql_id" --argjson file "$file_id" --argjson project "$project_id" '{questions:[
    {questionId:$programming,questionOrder:1,score:25,required:true,questionType:"PROGRAMMING"},
    {questionId:$single,questionOrder:2,score:8,required:true,questionType:"SINGLE_CHOICE"},
    {questionId:$multiple,questionOrder:3,score:10,required:true,questionType:"MULTIPLE_CHOICE"},
    {questionId:$trueFalse,questionOrder:4,score:7,required:true,questionType:"TRUE_FALSE"},
    {questionId:$fill,questionOrder:5,score:10,required:true,questionType:"FILL_BLANK"},
    {questionId:$short,questionOrder:6,score:10,required:true,questionType:"SHORT_ANSWER"},
    {questionId:$sql,questionOrder:7,score:10,required:true,questionType:"SQL"},
    {questionId:$file,questionOrder:8,score:10,required:false,questionType:"FILE"},
    {questionId:$project,questionOrder:9,score:10,required:false,questionType:"PROJECT"}
  ]}')"
  api -X PUT -H 'Content-Type: application/json' -H "Authorization: Bearer $teacher_token" -d "$composition" "$base_url/system/exam/$exam_id/questions" >/dev/null
  api -X POST -H "Authorization: Bearer $teacher_token" -H 'Idempotency-Key: seed-mixed-exam-v1' "$base_url/system/exam/$exam_id/publish" >/dev/null
fi

authorization="$(jq -n --argjson userId "$student_id" '{userIds:[$userId],source:"MANUAL"}')"
api -X POST -H 'Content-Type: application/json' -H "Authorization: Bearer $teacher_token" -H 'X-Request-ID: seed-mixed-student-v1' -d "$authorization" "$base_url/system/exam/$exam_id/candidates" >/dev/null

echo "[seed] mixed exam ready: examId=$exam_id student=$student_email teacher=$teacher_email"
