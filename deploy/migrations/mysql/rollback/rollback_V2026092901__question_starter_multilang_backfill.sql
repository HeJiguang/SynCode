-- Logical rollback of V2026092901__question_starter_multilang_backfill.
-- Only questions whose non-Java starters are still the untouched canonical templates are
-- restored to the legacy Java-only shape; rows where administrators authored real multi-language
-- starters after the migration cannot be restored automatically and are intentionally kept.
-- The answer_config_json language normalization is forward-only: reverting it would make the
-- bank metadata reject submissions the judge sandbox actually accepts.

UPDATE tb_question
SET starter_code_json = JSON_OBJECT(
    'java', COALESCE(
        NULLIF(CASE WHEN JSON_TYPE(JSON_EXTRACT(starter_code_json, '$.java')) = 'STRING'
                    THEN JSON_UNQUOTE(JSON_EXTRACT(starter_code_json, '$.java')) END, ''),
        NULLIF(default_code, ''),
        'import java.io.*;\nimport java.util.*;\n\npublic class Main {\n    public static void main(String[] args) throws Exception {\n        BufferedReader reader = new BufferedReader(new InputStreamReader(System.in));\n        // TODO: parse the input, implement the algorithm, and print the answer.\n    }\n}')
)
WHERE question_type = 'PROGRAMMING'
  AND starter_code_json IS NOT NULL
  AND JSON_VALID(starter_code_json)
  AND COALESCE(NULLIF(CASE WHEN JSON_TYPE(JSON_EXTRACT(starter_code_json, '$.cpp')) = 'STRING'
                           THEN JSON_UNQUOTE(JSON_EXTRACT(starter_code_json, '$.cpp')) END, ''),
      '#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    ios::sync_with_stdio(false);\n    cin.tie(nullptr);\n    // TODO: parse stdin, implement the algorithm, and print the answer.\n    return 0;\n}')
      = '#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    ios::sync_with_stdio(false);\n    cin.tie(nullptr);\n    // TODO: parse stdin, implement the algorithm, and print the answer.\n    return 0;\n}'
  AND COALESCE(NULLIF(CASE WHEN JSON_TYPE(JSON_EXTRACT(starter_code_json, '$.python')) = 'STRING'
                           THEN JSON_UNQUOTE(JSON_EXTRACT(starter_code_json, '$.python')) END, ''),
      'import sys\n\ndef solve():\n    # TODO: parse stdin, implement the algorithm, and print the answer.\n    pass\n\nif __name__ == "__main__":\n    solve()')
      = 'import sys\n\ndef solve():\n    # TODO: parse stdin, implement the algorithm, and print the answer.\n    pass\n\nif __name__ == "__main__":\n    solve()'
  AND COALESCE(NULLIF(CASE WHEN JSON_TYPE(JSON_EXTRACT(starter_code_json, '$.go')) = 'STRING'
                           THEN JSON_UNQUOTE(JSON_EXTRACT(starter_code_json, '$.go')) END, ''),
      'package main\n\nimport (\n    "bufio"\n    "fmt"\n    "os"\n)\n\nfunc main() {\n    in := bufio.NewReader(os.Stdin)\n    out := bufio.NewWriter(os.Stdout)\n    defer out.Flush()\n    _, _ = in, fmt.Fprint\n    // TODO: parse stdin, implement the algorithm, and print the answer.\n}')
      = 'package main\n\nimport (\n    "bufio"\n    "fmt"\n    "os"\n)\n\nfunc main() {\n    in := bufio.NewReader(os.Stdin)\n    out := bufio.NewWriter(os.Stdout)\n    defer out.Flush()\n    _, _ = in, fmt.Fprint\n    // TODO: parse stdin, implement the algorithm, and print the answer.\n}';
