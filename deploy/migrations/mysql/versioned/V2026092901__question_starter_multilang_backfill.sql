-- Purpose: backfill PROGRAMMING questions whose starter_code_json was persisted with only a
--   subset of the judge-pool languages (typically legacy {"java": ...} rows) so every question
--   exposes starter programs for java/cpp/python/go, and normalize answer_config_json.languages
--   to the full judge pool. Authored non-blank starters are always preserved; only missing,
--   blank, or non-string entries receive the canonical TODO templates from
--   MultiLanguageStarterCodes. JSON null members are treated as missing because
--   JSON_UNQUOTE(JSON null) yields the string 'null' instead of SQL NULL.
-- Compatibility: mirrors the runtime expansion in MultiLanguageStarterCodes.expandStarterMap and
--   oj-friend QuestionServiceImpl.parseStarterCode so the bank matches what reads return.
-- Lock risk: full-table UPDATEs on tb_question (small table); run outside active exams.
-- Rollback: see rollback_V2026092901__question_starter_multilang_backfill.sql.

-- 1. Rows without parsable starter JSON get the full template set, keeping the authored Java code.
UPDATE tb_question
SET starter_code_json = JSON_OBJECT(
    'java', COALESCE(NULLIF(default_code, ''),
        'import java.io.*;\nimport java.util.*;\n\npublic class Main {\n    public static void main(String[] args) throws Exception {\n        BufferedReader reader = new BufferedReader(new InputStreamReader(System.in));\n        // TODO: parse the input, implement the algorithm, and print the answer.\n    }\n}'),
    'cpp', '#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    ios::sync_with_stdio(false);\n    cin.tie(nullptr);\n    // TODO: parse stdin, implement the algorithm, and print the answer.\n    return 0;\n}',
    'python', 'import sys\n\ndef solve():\n    # TODO: parse stdin, implement the algorithm, and print the answer.\n    pass\n\nif __name__ == "__main__":\n    solve()',
    'go', 'package main\n\nimport (\n    "bufio"\n    "fmt"\n    "os"\n)\n\nfunc main() {\n    in := bufio.NewReader(os.Stdin)\n    out := bufio.NewWriter(os.Stdout)\n    defer out.Flush()\n    _, _ = in, fmt.Fprint\n    // TODO: parse stdin, implement the algorithm, and print the answer.\n}'
)
WHERE question_type = 'PROGRAMMING'
  AND (starter_code_json IS NULL OR NOT JSON_VALID(starter_code_json));

-- 2. Parsable starter JSON that lacks any judge-pool language (missing key, non-string member,
--    or blank value) is rebuilt from its authored entries with the canonical template per gap.
UPDATE tb_question
SET starter_code_json = JSON_OBJECT(
    'java', COALESCE(
        NULLIF(CASE WHEN JSON_TYPE(JSON_EXTRACT(starter_code_json, '$.java')) = 'STRING'
                    THEN JSON_UNQUOTE(JSON_EXTRACT(starter_code_json, '$.java')) END, ''),
        NULLIF(default_code, ''),
        'import java.io.*;\nimport java.util.*;\n\npublic class Main {\n    public static void main(String[] args) throws Exception {\n        BufferedReader reader = new BufferedReader(new InputStreamReader(System.in));\n        // TODO: parse the input, implement the algorithm, and print the answer.\n    }\n}'),
    'cpp', COALESCE(
        NULLIF(CASE WHEN JSON_TYPE(JSON_EXTRACT(starter_code_json, '$.cpp')) = 'STRING'
                    THEN JSON_UNQUOTE(JSON_EXTRACT(starter_code_json, '$.cpp')) END, ''),
        '#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    ios::sync_with_stdio(false);\n    cin.tie(nullptr);\n    // TODO: parse stdin, implement the algorithm, and print the answer.\n    return 0;\n}'),
    'python', COALESCE(
        NULLIF(CASE WHEN JSON_TYPE(JSON_EXTRACT(starter_code_json, '$.python')) = 'STRING'
                    THEN JSON_UNQUOTE(JSON_EXTRACT(starter_code_json, '$.python')) END, ''),
        'import sys\n\ndef solve():\n    # TODO: parse stdin, implement the algorithm, and print the answer.\n    pass\n\nif __name__ == "__main__":\n    solve()'),
    'go', COALESCE(
        NULLIF(CASE WHEN JSON_TYPE(JSON_EXTRACT(starter_code_json, '$.go')) = 'STRING'
                    THEN JSON_UNQUOTE(JSON_EXTRACT(starter_code_json, '$.go')) END, ''),
        'package main\n\nimport (\n    "bufio"\n    "fmt"\n    "os"\n)\n\nfunc main() {\n    in := bufio.NewReader(os.Stdin)\n    out := bufio.NewWriter(os.Stdout)\n    defer out.Flush()\n    _, _ = in, fmt.Fprint\n    // TODO: parse stdin, implement the algorithm, and print the answer.\n}')
)
WHERE question_type = 'PROGRAMMING'
  AND starter_code_json IS NOT NULL
  AND JSON_VALID(starter_code_json)
  AND (
      NULLIF(CASE WHEN JSON_TYPE(JSON_EXTRACT(starter_code_json, '$.java')) = 'STRING'
                  THEN JSON_UNQUOTE(JSON_EXTRACT(starter_code_json, '$.java')) END, '') IS NULL
      OR NULLIF(CASE WHEN JSON_TYPE(JSON_EXTRACT(starter_code_json, '$.cpp')) = 'STRING'
                     THEN JSON_UNQUOTE(JSON_EXTRACT(starter_code_json, '$.cpp')) END, '') IS NULL
      OR NULLIF(CASE WHEN JSON_TYPE(JSON_EXTRACT(starter_code_json, '$.python')) = 'STRING'
                     THEN JSON_UNQUOTE(JSON_EXTRACT(starter_code_json, '$.python')) END, '') IS NULL
      OR NULLIF(CASE WHEN JSON_TYPE(JSON_EXTRACT(starter_code_json, '$.go')) = 'STRING'
                     THEN JSON_UNQUOTE(JSON_EXTRACT(starter_code_json, '$.go')) END, '') IS NULL
  );

-- 3. answer_config_json that is missing, unparsable, or not an object gets the standard shape.
UPDATE tb_question
SET answer_config_json = JSON_OBJECT(
    'languages', JSON_ARRAY('java', 'cpp', 'python', 'go'),
    'entry', 'stdin-stdout'
)
WHERE question_type = 'PROGRAMMING'
  AND (answer_config_json IS NULL
       OR NOT JSON_VALID(answer_config_json)
       OR JSON_TYPE(answer_config_json) <> 'OBJECT');

-- 4. Valid answer_config_json objects whose declared languages miss part of the judge pool
--    (e.g. {"languages":["java"]}) are normalized; other members are preserved.
UPDATE tb_question
SET answer_config_json = JSON_SET(
    answer_config_json,
    '$.languages', JSON_ARRAY('java', 'cpp', 'python', 'go')
)
WHERE question_type = 'PROGRAMMING'
  AND answer_config_json IS NOT NULL
  AND JSON_VALID(answer_config_json)
  AND JSON_TYPE(answer_config_json) = 'OBJECT'
  AND (
      COALESCE(JSON_TYPE(JSON_EXTRACT(answer_config_json, '$.languages')), 'MISSING') <> 'ARRAY'
      OR JSON_LENGTH(JSON_EXTRACT(answer_config_json, '$.languages')) < 4
  );
